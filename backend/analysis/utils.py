import re
import pandas as pd
from typing import List, Dict, Any
import openai
import os
from openai import OpenAI
client = OpenAI()
openai.api_key = os.getenv("OPENAI_API_KEY")
# Columns we expect in the Excel (adjust to your actual file)
# For sample file, assume columns: 'year', 'area', 'price', 'demand', 'size'
EXPECTED_COLUMNS = ["year", "area", "price", "demand", "size"]

def read_excel_from_filelike(file_like):
    df = pd.read_excel(file_like, engine="openpyxl")

    df.columns = [c.strip().lower() for c in df.columns]

    # Map your columns to expected names
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
    Very simple area extraction:
    - looks for exact area names contained in the query (case-insensitive)
    - also supports queries like 'compare A and B' or 'A vs B' by capturing both
    """
    q = query.lower()
    found = []
    # attempt to catch formats like "compare X and Y" or "X vs Y"
    # but simplest robust approach: check each available area if it appears in query
    for area in available_areas:
        if area.lower() in q:
            found.append(area)
    # If none found, try to capture last word as area (fallback)
    if not found:
        # capture words with capitals or single words
        tokens = re.findall(r"[A-Za-z0-9\s\-]+", query)
        # pick token words longer than 2 chars
        candidate_words = [t.strip() for t in " ".join(tokens).split() if len(t.strip()) > 2]
        if candidate_words:
            # return first candidate as fallback
            return [candidate_words[-1]]
    return list(dict.fromkeys(found))  # unique preserve order

def prepare_chart_data(df: pd.DataFrame, areas: List[str]) -> Dict[str, Any]:
    """
    Returns JSON-ready chart data:
    {
      'price_trend': {'labels': [...years...], 'datasets': [{'area': 'X', 'values':[...]} , ...]},
      'demand_trend': { ... }
    }
    """
    chart = {"price_trend": {}, "demand_trend": {}}
    # ensure year is numeric
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
    years_sorted = sorted(df["year"].dropna().unique().astype(int).tolist())
    chart["price_trend"]["labels"] = years_sorted
    chart["demand_trend"]["labels"] = years_sorted

    price_datasets = []
    demand_datasets = []
    for area in areas:
        sub = df[df["area"].str.lower() == area.lower()]
        # group by year
        g = sub.groupby("year").agg({"price":"mean", "demand":"mean"}).reindex(years_sorted).fillna(0)
        price_values = [float(x) if not pd.isna(x) else 0.0 for x in g["price"].tolist()]
        demand_values = [float(x) if not pd.isna(x) else 0.0 for x in g["demand"].tolist()]
        price_datasets.append({"area": area, "values": price_values})
        demand_datasets.append({"area": area, "values": demand_values})

    chart["price_trend"]["datasets"] = price_datasets
    chart["demand_trend"]["datasets"] = demand_datasets
    return chart

def prepare_table_data(df: pd.DataFrame, areas: List[str], max_rows=100) -> List[Dict[str, Any]]:
    """
    Returns filtered table data as list of dicts (JSON-ready).
    """
    if areas:
        mask = df["area"].str.lower().isin([a.lower() for a in areas])
        filtered = df[mask]
    else:
        filtered = df
    # Convert to dicts; pick a few columns
    cols = [c for c in ["year", "area", "price", "demand", "size"] if c in filtered.columns]
    results = filtered[cols].head(max_rows).to_dict(orient="records")
    # ensure native Python types
    sanitized = []
    for r in results:
        s = {}
        for k, v in r.items():
            if pd.isna(v):
                s[k] = None
            elif isinstance(v, (pd.Timestamp,)):
                s[k] = str(v)
            else:
                try:
                    # convert numpy types to python native
                    s[k] = int(v) if (isinstance(v, float) and v.is_integer()) else (float(v) if isinstance(v, (float,)) else v)
                except Exception:
                    s[k] = v
        sanitized.append(s)
    return sanitized

def generate_llm_summary(df, areas):
    """
    Generate real summary using OpenAI API
    """
    try:
        # Prepare data statistics
        stats = []
        for area in areas:
            sub = df[df["area"].str.lower() == area.lower()]
            if not sub.empty:
                sub["year"] = pd.to_numeric(sub["year"], errors="coerce")
                sub["price"] = pd.to_numeric(sub["price"], errors="coerce")
                sub["demand"] = pd.to_numeric(sub["demand"], errors="coerce")
                
                grouped = sub.groupby("year").agg({
                    "price": "mean",
                    "demand": "mean"
                }).dropna()
                
                if not grouped.empty:
                    stats.append({
                        "area": area,
                        "year_range": f"{int(grouped.index.min())}-{int(grouped.index.max())}",
                        "avg_price": float(grouped["price"].mean()),
                        "price_trend": "increasing" if grouped["price"].iloc[-1] > grouped["price"].iloc[0] else "decreasing",
                        "avg_demand": float(grouped["demand"].mean())
                    })

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

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )

        return response["choices"][0]["message"]["content"].strip()
    
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Fallback to mock summary if API fails
        return generate_mock_summary(df, areas)

def generate_mock_summary(df, areas):
    """
    Safe summary generator that cannot crash due to formatting errors.
    """

    import numpy as np

    if not areas:
        return "No area detected in query."

    area = areas[0]

    sub = df[df["area"].str.lower() == area.lower()]

    if sub.empty:
        return f"No data found for area: {area}"

    # Ensure numeric columns
    sub["year"] = pd.to_numeric(sub["year"], errors="coerce")
    sub["price"] = pd.to_numeric(sub["price"], errors="coerce")

    # Drop invalid rows
    sub = sub.dropna(subset=["year", "price"])

    if sub.empty:
        return f"Not enough valid price data for {area}."

    grouped = sub.groupby("year")["price"].mean().dropna().sort_index()

    if grouped.empty:
        return f"No price trend data available for {area}."

    # Extract values safely
    try:
        first_year = int(grouped.index[0])
        last_year = int(grouped.index[-1])

        first_price = float(grouped.iloc[0])
        last_price = float(grouped.iloc[-1])

    except Exception:
        return f"Could not compute summary for {area} due to invalid numeric values."

    # Handle invalid prices
    if first_price == 0 or np.isnan(first_price) or np.isnan(last_price):
        return f"Price data for {area} is incomplete for trend analysis."

    pct_change = ((last_price - first_price) / first_price) * 100

    if pct_change > 0:
        trend = "increased"
    elif pct_change < 0:
        trend = "decreased"
    else:
        trend = "remained stable"

    # Safely format values (avoid format specifier errors)
    try:
        pc = round(abs(pct_change), 1)
        lp = round(last_price)
    except Exception:
        return f"{area} price trend shows inconsistent numeric values."

    return (
        f"Analysis for {area}: Prices have {trend} by {pc}% "
        f"from {first_year} to {last_year}. "
        f"Latest average price: {lp}."
    )

def parse_query_with_llm(query, available_areas):
    import json

    # Escape braces in the prompt for f-string
    escaped_json = """
{{
 "areas": [],
 "intent": "",
 "metrics": []
}}
"""

    prompt = f"""
You are a smart real-estate assistant.

User query: "{query}"

Available areas (choose only from this list):
{", ".join(available_areas)}

Your job:
1. Identify the areas mentioned by the user (if any).
2. Identify what user wants (trend, summary, comparison, price, demand, growth etc.)
3. Output JSON strictly like this:

{escaped_json}

Example:
Input: "Compare demand trend of Baner and Aundh"
Output:
{{
 "areas": ["Baner","Aundh"],
 "intent": "compare",
 "metrics": ["demand"]
 }}
"""

    # NEW API STYLE (v1.x)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt}
        ],
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    # Parse JSON output
    return json.loads(content)
