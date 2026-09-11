import json
from io import BytesIO

import pandas as pd
import pytest
from rest_framework.test import APIClient

from analysis import utils


@pytest.fixture(autouse=True)
def no_openai_key(monkeypatch):
    # settings.py runs load_dotenv(), so a real key from .env may be in the
    # environment. Remove it and drop any memoized client so no test can
    # reach the network.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(utils, "_client", None)


def xlsx_bytes(df):
    """Write a DataFrame to an in-memory .xlsx file, rewound for reading."""
    buf = BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf


def test_read_excel_normalizes_igr_headers():
    source = pd.DataFrame(
        {
            " Final Location ": ["Wakad", "Aundh"],
            "Year": [2020, 2021],
            "Flat - Weighted Average Rate": [8450.5, 9100.0],
            "Total Units": [120, 95],
            "Total Carpet Area Supplied (sqft)": [65000.0, 48000.0],
            "Builder Remarks": ["ready", "under construction"],
        }
    )

    df = utils.read_excel_from_filelike(xlsx_bytes(source))

    assert set(utils.EXPECTED_COLUMNS) <= set(df.columns)
    assert df["area"].tolist() == ["Wakad", "Aundh"]
    assert df["year"].tolist() == [2020, 2021]
    assert df["price"].tolist() == [8450.5, 9100.0]
    assert df["demand"].tolist() == [120, 95]
    assert df["size"].tolist() == [65000.0, 48000.0]


def test_extract_areas_is_case_insensitive_deduplicated_and_ordered():
    available = ["Akurdi", "Aundh", "Wakad"]

    areas = utils.extract_areas_from_query(
        "compare WAKAD with aundh, then wakad again", available
    )
    assert areas == ["Wakad", "Aundh"]

    assert utils.extract_areas_from_query("show prices in Baner", available) == []


def test_chart_data_aligns_sparse_years_to_shared_axis():
    # Aundh has 2020-2022; Wakad has two rows, both in 2022.
    df = pd.DataFrame(
        {
            "area": ["Aundh", "Aundh", "Aundh", "Wakad", "Wakad"],
            "year": [2020, 2021, 2022, 2022, 2022],
            "price": [9000.0, 9500.0, 10000.0, 7000.0, 8000.0],
            "demand": [100, 110, 120, 40, 60],
        }
    )

    chart = utils.prepare_chart_data(df, ["Aundh", "Wakad"])

    labels = chart["price_trend"]["labels"]
    assert labels == [2020, 2021, 2022]
    assert all(isinstance(year, int) for year in labels)
    assert chart["demand_trend"]["labels"] == labels

    price = {d["area"]: d["values"] for d in chart["price_trend"]["datasets"]}
    demand = {d["area"]: d["values"] for d in chart["demand_trend"]["datasets"]}
    assert price["Aundh"] == [9000.0, 9500.0, 10000.0]
    assert price["Wakad"] == [None, None, 7500.0]
    assert demand["Wakad"] == [None, None, 50.0]

    for trend in ("price_trend", "demand_trend"):
        for dataset in chart[trend]["datasets"]:
            assert len(dataset["values"]) == len(labels)


def test_table_data_is_json_serializable():
    df = pd.DataFrame(
        {
            "year": [pd.Timestamp("2021-01-01"), pd.Timestamp("2022-01-01")],
            "area": ["Wakad", "Wakad"],
            "price": [8450.0, float("nan")],
            "demand": [120, 95],
            "size": [65000.5, 48000.0],
        }
    )

    rows = utils.prepare_table_data(df, ["Wakad"])

    # allow_nan=False: plain json.dumps would silently write NaN, which is
    # not valid JSON.
    json.dumps(rows, allow_nan=False)
    first, second = rows
    assert isinstance(first["year"], str)
    assert first["price"] == 8450 and isinstance(first["price"], int)
    assert second["price"] is None


def test_analyze_endpoint_works_end_to_end_without_openai_key():
    assert utils.get_openai_client() is None

    # No file, so the view falls back to the bundled data/sample.xlsx.
    response = APIClient().post(
        "/api/analyze/",
        {"query": "Compare demand trend of Wakad and Aundh"},
        format="multipart",
    )

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["areas_detected"]) == ["Aundh", "Wakad"]
    assert isinstance(body["summary"], str) and body["summary"].strip()
    assert "nan" not in body["summary"].lower()
    assert body["chart"]["price_trend"]["labels"]
    assert body["table"]
