import json
import logging
import os
import re
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from openai import OpenAI

logger = logging.getLogger(__name__)

# Columns we expect in the Excel (adjust to your actual file).
# For the sample file, assume columns: 'year', 'area', 'price', 'demand', 'size'.
EXPECTED_COLUMNS = ["year", "area", "price", "demand", "size"]

_client = None


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
    _client = OpenAI()
    return _client


def read_excel_from_filelike(file_like):
    df = pd.read_excel(file_like, engine="openpyxl")

    df.columns = [c.strip().lower() for c in df.columns]

    # Map source spreadsheet headers to the names the app expects.
    column_map = {
        "final location": "area",
        "year": "year",
        "flat - weighted average rate": "price",
        "total units": "demand",
        "total carpet area supplied (sqft)": "size",
    }

    df.rename(columns=column_map, inplace=True)

    return df


def extract_areas_from_query(query: str, available_areas: List[str]) -> List[str]:
    """
    Simple, dependency-free area extraction used as a fallback when the LLM
    is unavailable.

    - Matches any available area name contained in the query (case-insensitive).
    - Handles phrasings like "compare A and B" or "A vs B" implicitly, since
      each area is checked independently.
    - If nothing matches, falls back to the last word-like token in the query.
    """
    q = query.lower()
    found = []
    for area in available_areas:
        if area.lower() in q:
            found.append(area)

    if not found:
        tokens = re.findall(r"[A-Za-z0-9\s\-]+", query)
        candidate_words = [
            t.strip() for t in " ".join(tokens).split() if len(t.strip()) > 2
        ]
        if candidate_words:
            return [candidate_words[-1]]

    return list(dict.fromkeys(found))  # unique, order-preserving


def prepare_chart_data(df: pd.DataFrame, areas: List[str]) -> Dict[str, Any]:
    """
    Return JSON-ready chart data:

    {
      "price_trend":  {"labels": [...years...], "datasets": [{"area": "X", "values": [...]}, ...]},
      "demand_trend": {...},
    }
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
        sub = df[df["area"].str.lower() == area.lower()]
        grouped = (
            sub.groupby("year")
            .agg({"price": "mean", "demand": "mean"})
            .reindex(years_sorted)
            .fillna(0)
        )
        price_values = [
            float(x) if not pd.isna(x) else 0.0 for x in grouped["price"].tolist()
        ]
        demand_values = [
            float(x) if not pd.isna(x) else 0.0 for x in grouped["demand"].tolist()
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
    query. Raises if no client is configured or the response isn't valid JSON;
    callers are expected to fall back to extract_areas_from_query.
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

    content = response.choices[0].message.content.strip()
    return json.loads(content)


def generate_llm_summary(df: pd.DataFrame, areas: List[str]) -> str:
    """
    Generate a natural-language market summary via the LLM. Falls back to the
    deterministic mock summary if the client is unavailable or the call fails.
    """
    client = get_openai_client()
    if client is None:
        return generate_mock_summary(df, areas)

    try:
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

    area = areas[0]
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

    pct_change = ((last_price - first_price) / first_price) * 100
    if pct_change > 0:
        trend = "increased"
    elif pct_change < 0:
        trend = "decreased"
    else:
        trend = "remained stable"

    pc = round(abs(pct_change), 1)
    lp = round(last_price)

    return (
        f"Analysis for {area}: Prices have {trend} by {pc}% "
        f"from {first_year} to {last_year}. "
        f"Latest average price: {lp}."
    )
