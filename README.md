# Real Estate Analysis Bot (Django + React)

A full-stack application that turns raw real-estate spreadsheets into
natural-language insights and interactive charts. Ask a question in plain
English ("Compare demand trend of Wakad and Aundh") and the app extracts the
relevant areas, computes price/demand trends, renders charts, and generates a
concise market summary.

<!-- Live demo: add link after deployment -->

---

## Overview

- **Django backend** — REST API, Excel parsing, and analysis logic.
- **React frontend** — query box (with optional `.xlsx` upload) that shows the
  summary, trend charts, and a data table.
- **LLM-assisted parsing with graceful fallback** — natural-language queries are
  parsed by an LLM when an API key is configured, and automatically fall back to
  a deterministic parser (and a deterministic summary generator) when it isn't
  or the call fails, so the app works end-to-end with or without an OpenAI key.

---

## Project Structure

```
real-estate-bot/
├── backend/                 # Django project
│   ├── analysis/            # API app: views, serializers, utils (analysis logic)
│   ├── data/                # sample input files (sample.xlsx)
│   ├── realestate_bot/      # Django settings and root URLs
│   ├── tests/               # pytest suite
│   ├── .env.example
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   └── manage.py
└── frontend/                # React + Vite app
    ├── src/
    ├── public/
    ├── .env.example
    ├── package.json
    ├── vercel.json
    └── vite.config.js
```

---

## Tech Stack

**Backend:** Python 3.11, Django 4.2, Django REST Framework 3.14, pandas 2.1,
openpyxl 3.1, OpenAI SDK 1.51 (`gpt-4o-mini`), SQLite (Django's default
database; the app itself stores no data)

**Frontend:** React 19 (Vite 7), Axios 1.13, Recharts 3.5, Bootstrap 5.3

---

## Getting Started

### Prerequisites

- Python 3.11 (the version this project is tested with; `requirements-dev.txt`
  needs 3.10+)
- Node.js 20.19+ or 22.12+ (required by Vite 7)

### 1. Backend

From the repo root:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # see Environment Variables below
python manage.py migrate
python manage.py runserver
```

Backend runs at `http://127.0.0.1:8000`.

### 2. Frontend

In a second terminal, from the repo root:

```bash
cd frontend
npm install
cp .env.example .env             # optional; the API URL defaults to http://localhost:8000
npm run dev
```

Frontend runs at `http://localhost:5173`.

---

## Environment Variables

**Backend:** copy `backend/.env.example` to `backend/.env` (it is gitignored
and must never be committed). Generate a fresh secret key rather than reusing
any example value. For local use `SECRET_KEY` can stay empty: a random key is
then generated each time the server starts, with a warning.

```
SECRET_KEY=<your-generated-django-secret-key>
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
OPENAI_API_KEY=<your-openai-api-key>   # optional; the app falls back gracefully if unset
```

To generate a Django secret key (with the backend virtualenv active):

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Frontend (optional):** copy `frontend/.env.example` to `frontend/.env` to
point the app at a different backend. `VITE_API_URL` is the backend's base URL
without a trailing slash; it defaults to `http://localhost:8000`.

```
VITE_API_URL=http://localhost:8000
```

---

## API Endpoints

| Method | Endpoint         | Purpose                                                        |
| ------ | ---------------- | ------------------------------------------------------------- |
| POST   | `/api/analyze/`  | Analyze data for a query; returns summary, chart, and table.  |
| POST   | `/api/download/` | Download filtered results as `.xlsx` (default) or `.csv`.     |

**`/api/analyze/` request:** multipart form with `query` (required text, up to
500 characters) and an optional `file` (`.xlsx`, up to 5 MB). If no file is
provided, `backend/data/sample.xlsx` is used.

**`/api/analyze/` response** (real output for `Compare demand trend of Wakad
and Aundh` against the sample data with no OpenAI key; trimmed to the Wakad
dataset in each chart and the first of 10 table rows):

```json
{
  "summary": "Analysis for Wakad: Prices have increased by 12.7% from 2020 to 2024. Latest average price: 10278. Analysis for Aundh: Prices have increased by 32.5% from 2020 to 2024. Latest average price: 11774.",
  "areas_detected": ["Wakad", "Aundh"],
  "intent": "analysis",
  "metrics": ["price", "demand"],
  "chart": {
    "price_trend": {
      "labels": [2020, 2021, 2022, 2023, 2024],
      "datasets": [
        { "area": "Wakad", "values": [9116.946698520345, 9289.038931398418, 9734.906578864848, 9959.56636540962, 10277.82582611386] }
      ]
    },
    "demand_trend": {
      "labels": [2020, 2021, 2022, 2023, 2024],
      "datasets": [
        { "area": "Wakad", "values": [4325.0, 5030.0, 4397.0, 4471.0, 1814.0] }
      ]
    }
  },
  "table": [
    { "year": 2020, "area": "Aundh", "price": 8888.992344827586, "demand": 56, "size": 48071.37815999999 }
  ]
}
```

**`/api/download/` request:** form with `query`, optional `file`, and optional
`format` (`excel` or `csv`).

---

## Features

- Natural-language query parsing (LLM-assisted, with a deterministic fallback).
- Automatic mapping of IGR-style Excel headers (e.g. `Final Location`,
  `Flat - Weighted Average Rate`) to a normalized schema (`area`, `year`,
  `price`, `demand`, `size`); files that already use those names work as-is.
- Price and demand trend computation, grouped by year and area.
- Chart-ready and table-ready JSON output for the frontend.
- Export filtered data to Excel or CSV.
- Works with or without an OpenAI API key.

---

## Testing

From `backend/` with the virtualenv active:

```bash
pip install -r requirements-dev.txt
pytest -q
```

Expected result: `5 passed` (a `SECRET_KEY is not set` warning is expected
when `SECRET_KEY` is empty). The tests cover IGR header normalization, area
matching (case-insensitive, deduplicated, in query order), alignment of sparse
years on the chart axis (gaps are `null`), JSON-safe table rows, and an
end-to-end `/api/analyze/` call without an OpenAI key; they need no API key.

---

## Limitations

- Uploads must be `.xlsx` (max 5 MB) with either the IGR headers
  (`Final Location`, `Year`, `Flat - Weighted Average Rate`, `Total Units`,
  `Total Carpet Area Supplied (sqft)`) or the normalized names `Area`, `Year`,
  `Price`, `Demand`, `Size` (case-insensitive). Any other layout is rejected
  with a 400 that lists the missing columns.
- The bundled sample (`backend/data/sample.xlsx`) is 20 rows: 4 areas (Akurdi,
  Ambegaon Budruk, Aundh, Wakad) over 5 years (2020–2024).
- No persistence or query history: each query is analyzed from scratch and
  replaces the previous result on screen.
- The deterministic fallback parser matches area names as case-insensitive
  substrings of the query, so it won't catch misspellings.
- Without an OpenAI key, the summary describes price trends only, even for
  demand questions (demand still appears in the chart and table), and
  `intent`/`metrics` are always `analysis` / `["price", "demand"]`.

---

## Deployment

- **Frontend:** includes `frontend/vercel.json` for Vercel deployment.
- **Backend:** for production, set `DEBUG=False`, a strong `SECRET_KEY`, and an
  explicit `ALLOWED_HOSTS`.
