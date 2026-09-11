import json
import logging
import os
import re
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from openai import OpenAI

logger = logging.getLogger(__name__)

# Canonical columns required after header mapping (see read_excel_from_filelike),
# in the order used for downloads.
EXPECTED_COLUMNS = ["year", "area", "price", "demand", "size"]

_client = None


class SpreadsheetError(ValueError):
    """A problem with the sheet's layout that the user can fix; the message is user-facing."""


def get_openai_client():
    """
    Lazily create and cache the OpenAI client.

    The client is created on first use rather than at import time so that
    importing this module never fails when OPENAI_API_KEY is unset. Returns
    None when no key is configured, letting callers fall back gracefully.
    """
    global _client
    if _client is not None:
        return _client
    if not os.getenv("OPENAI_API_KEY"):
        return None
    # Fail fast so a slow or unreachable API falls back instead of hanging
    # the request (the SDK default is a 600 s timeout with 2 retries).
    _client = OpenAI(timeout=15, max_retries=1)
    return _client


def read_excel_from_filelike(file_like):
    df = pd.read_excel(file_like, engine="openpyxl")

    # str() first: header cells can be numbers (e.g. a year used as a header).
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Map source spreadsheet headers to the names the app expects.
    column_map = {
        "final location": "area",
        "year": "year",
        "flat - weighted average rate": "price",
        "total units": "demand",
        "total carpet area supplied (sqft)": "size",
    }

    df.rename(columns=column_map, inplace=True)

    # e.g. both "Final Location" and "area": df["area"] would be ambiguous.
    duplicated = sorted(set(df.columns[df.columns.duplicated()]) & set(EXPECTED_COLUMNS))
    if duplicated:
        raise SpreadsheetError(
            "Duplicate columns after header mapping: "
            + ", ".join(duplicated)
            + ". Keep only one column for each."
        )

    if "area" in df.columns:
        # Uploaded area cells can be numbers or carry stray spaces; use trimmed
        # strings, and treat blank cells as missing (an empty name would
        # otherwise match every query).
        df["area"] = df["area"].map(
            lambda v: (str(v).strip() or None) if pd.notna(v) else None
        )

    return df


def extract_areas_from_query(query: str, available_areas: List[str]) -> List[str]:
    """
    Simple, dependency-free area extraction used as a fallback when the LLM
    is unavailable.

    - Matches any available area name contained in the query (case-insensitive).
    - Handles phrasings like "compare A and B" or "A vs B" implicitly, since
      each area is checked independently.
    - Returns areas in the order they are first mentioned in the query.
    - If nothing matches, returns an empty list (the caller reports the
      available areas instead of guessing one).
    """
    q = query.lower()
    positions = {}
    for area in available_areas:
        pos = q.find(area.lower())
        if pos != -1:
            positions[area] = pos

    return sorted(positions, key=positions.get)


def prepare_chart_data(df: pd.DataFrame, areas: List[str]) -> Dict[str, Any]:
    """
    Return JSON-ready chart data:

    {
      "price_trend":  {"labels": [...years...], "datasets": [{"area": "X", "values": [...]}, ...]},
      "demand_trend": {...},
    }

    Each values list has one entry per label; years with no data are None.
    """
    chart: Dict[str, Any] = {"price_trend": {}, "demand_trend": {}}

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")

    years_sorted = sorted(df["year"].dropna().unique().astype(int).tolist())
    chart["price_trend"]["labels"] = years_sorted
    chart["demand_trend"]["labels"] = years_sorted

    price_datasets = []
    demand_datasets = []
    for area in areas:
        sub = df[df["area"].str.lower() == area.lower()].copy()
        # Uploaded sheets may hold text in numeric columns; treat it as missing.
        sub["price"] = pd.to_numeric(sub["price"], errors="coerce")
        sub["demand"] = pd.to_numeric(sub["demand"], errors="coerce")
        grouped = (
            sub.groupby("year")
            .agg({"price": "mean", "demand": "mean"})
            .reindex(years_sorted)
        )
        # Years without data stay None (JSON null) so the chart shows a gap
        # instead of a misleading drop to 0.
        price_values = [
            float(x) if not pd.isna(x) else None for x in grouped["price"].tolist()
        ]
        demand_values = [
            float(x) if not pd.isna(x) else None for x in grouped["demand"].tolist()
        ]
        price_datasets.append({"area": area, "values": price_values})
        demand_datasets.append({"area": area, "values": demand_values})

    chart["price_trend"]["datasets"] = price_datasets
    chart["demand_trend"]["datasets"] = demand_datasets
    return chart


def prepare_table_data(
    df: pd.DataFrame, areas: List[str], max_rows: int = 100
) -> List[Dict[str, Any]]:
    """Return filtered table data as a list of JSON-ready dicts."""
    if areas:
        mask = df["area"].str.lower().isin([a.lower() for a in areas])
        filtered = df[mask]
    else:
        filtered = df

    cols = [c for c in ["year", "area", "price", "demand", "size"] if c in filtered.columns]
    results = filtered[cols].head(max_rows).to_dict(orient="records")

    sanitized = []
    for row in results:
        clean_row = {}
        for key, value in row.items():
            if pd.isna(value):
                clean_row[key] = None
            elif isinstance(value, pd.Timestamp):
                clean_row[key] = str(value)
            else:
                try:
                    if isinstance(value, float) and value.is_integer():
                        clean_row[key] = int(value)
                    elif isinstance(value, float):
                        clean_row[key] = float(value)
                    else:
                        clean_row[key] = value
                except Exception:
                    clean_row[key] = value
        sanitized.append(clean_row)
    return sanitized


def parse_query_with_llm(query: str, available_areas: List[str]) -> Dict[str, Any]:
    """
    Use the LLM to extract areas, intent, and metrics from a natural-language
    query. Areas are mapped onto the canonical names in available_areas and
    unknown ones are dropped. Raises if no client is configured, the response
    isn't a JSON object, or no known area remains; callers are expected to fall
    back to extract_areas_from_query.
    """
    client = get_openai_client()
    if client is None:
        raise RuntimeError("OpenAI client unavailable (OPENAI_API_KEY not set).")

    output_schema = '{\n "areas": [],\n "intent": "",\n "metrics": []\n}'

    prompt = f"""
You are a smart real-estate assistant.

User query: "{query}"

Available areas (choose only from this list):
{", ".join(available_areas)}

Your job:
1. Identify the areas mentioned by the user (if any).
2. Identify what the user wants (trend, summary, comparison, price, demand, growth, etc.).
3. Output JSON strictly in this shape:

{output_schema}

Example:
Input: "Compare demand trend of Baner and Aundh"
Output:
{{"areas": ["Baner", "Aundh"], "intent": "compare", "metrics": ["demand"]}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}],
        temperature=0,
    )

    content = (response.choices[0].message.content or "").strip()
    # Chat models often wrap JSON in a ```json ... ``` fence.
    fenced = re.match(r"^```[a-zA-Z]*\s*(.*?)\s*```$", content, re.DOTALL)
    if fenced:
        content = fenced.group(1)
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError(f"LLM returned {type(parsed).__name__}, expected an object")

    # Keep only areas that exist in the data, spelled as they are in the data.
    canonical = {a.lower(): a for a in available_areas}
    raw_areas = parsed.get("areas")
    if isinstance(raw_areas, str):
        raw_areas = [raw_areas]
    areas = []
    for name in raw_areas if isinstance(raw_areas, list) else []:
        match = canonical.get(str(name).strip().lower())
        if match and match not in areas:
            areas.append(match)
    if not areas:
        raise ValueError(f"LLM returned no known areas: {raw_areas!r}")

    intent = parsed.get("intent")
    metrics = parsed.get("metrics")
    if isinstance(metrics, str):
        metrics = [metrics]
    metrics = [m for m in metrics if isinstance(m, str)] if isinstance(metrics, list) else []
    return {
        "areas": areas,
        "intent": intent if isinstance(intent, str) and intent else "analysis",
        "metrics": metrics or ["price", "demand"],
    }


def generate_llm_summary(df: pd.DataFrame, areas: List[str]) -> str:
    """
    Generate a natural-language market summary via the LLM. Falls back to the
    deterministic mock summary if the client is unavailable or the call fails.
    """
    try:
        client = get_openai_client()
        if client is None:
            return generate_mock_summary(df, areas)

        stats = []
        for area in areas:
            sub = df[df["area"].str.lower() == area.lower()]
            if sub.empty:
                continue

            sub = sub.copy()
            sub["year"] = pd.to_numeric(sub["year"], errors="coerce")
            sub["price"] = pd.to_numeric(sub["price"], errors="coerce")
            sub["demand"] = pd.to_numeric(sub["demand"], errors="coerce")

            grouped = (
                sub.groupby("year").agg({"price": "mean", "demand": "mean"}).dropna()
            )
            if grouped.empty:
                continue

            stats.append(
                {
                    "area": area,
                    "year_range": f"{int(grouped.index.min())}-{int(grouped.index.max())}",
                    "avg_price": float(grouped["price"].mean()),
                    "price_trend": "increasing"
                    if grouped["price"].iloc[-1] > grouped["price"].iloc[0]
                    else "decreasing",
                    "avg_demand": float(grouped["demand"].mean()),
                }
            )

        if not stats:
            # Nothing numeric to ground the model on; don't let it invent figures.
            return generate_mock_summary(df, areas)

        prompt = f"""
You are a real estate market analyst. Based on the following data, provide a concise, professional analysis:

Areas analyzed: {', '.join(areas)}
Statistics: {stats}

Provide a 2-3 sentence summary covering:
1. Price trends and key observations
2. Demand patterns
3. Investment insights or recommendations

Keep it clear, data-driven, and actionable.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        logger.warning("OpenAI summary failed, using mock summary: %s", exc)
        return generate_mock_summary(df, areas)


def generate_mock_summary(df: pd.DataFrame, areas: List[str]) -> str:
    """Deterministic summary generator that cannot crash on formatting errors."""
    if not areas:
        return "No area detected in query."

    return " ".join(_summarize_area(df, area) for area in areas)


def _summarize_area(df: pd.DataFrame, area: str) -> str:
    """One-sentence price trend for a single area, guarded against bad data."""
    sub = df[df["area"].str.lower() == area.lower()]
    if sub.empty:
        return f"No data found for area: {area}"

    sub = sub.copy()
    sub["year"] = pd.to_numeric(sub["year"], errors="coerce")
    sub["price"] = pd.to_numeric(sub["price"], errors="coerce")
    sub = sub.dropna(subset=["year", "price"])
    if sub.empty:
        return f"Not enough valid price data for {area}."

    grouped = sub.groupby("year")["price"].mean().dropna().sort_index()
    if grouped.empty:
        return f"No price trend data available for {area}."

    try:
        first_year = int(grouped.index[0])
        last_year = int(grouped.index[-1])
        first_price = float(grouped.iloc[0])
        last_price = float(grouped.iloc[-1])
    except Exception:
        return f"Could not compute summary for {area} due to invalid numeric values."

    if first_price == 0 or np.isnan(first_price) or np.isnan(last_price):
        return f"Price data for {area} is incomplete for trend analysis."

    lp = round(last_price)
    if first_year == last_year:
        return (
            f"Analysis for {area}: Only {first_year} data is available. "
            f"Average price: {lp}."
        )

    pct_change = ((last_price - first_price) / first_price) * 100
    pc = round(abs(pct_change), 1)
    if pct_change > 0:
        trend = f"increased by {pc}%"
    elif pct_change < 0:
        trend = f"decreased by {pc}%"
    else:
        trend = "remained stable"

    return (
        f"Analysis for {area}: Prices have {trend} "
        f"from {first_year} to {last_year}. "
        f"Latest average price: {lp}."
    )
