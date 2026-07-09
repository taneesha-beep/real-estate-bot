# Real Estate Analysis Bot (Django + React)

A full-stack application that turns raw real-estate spreadsheets into
natural-language insights and interactive charts. Ask a question in plain
English ("Compare demand trend of Baner and Aundh") and the app extracts the
relevant areas, computes price/demand trends, renders charts, and generates a
concise market summary.

---

## Overview

- **Django backend** — REST API, Excel parsing, and analysis logic.
- **React frontend** — chat-style UI with charts and data tables.
- **LLM-assisted parsing with graceful fallback** — natural-language queries are
  parsed by an LLM when an API key is configured, and automatically fall back to
  a deterministic parser (and a deterministic summary generator) when it isn't,
  so the app works end-to-end with or without an OpenAI key.

---

## Project Structure

```
realestate_bot/
├── backend/                 # Django project
│   ├── analysis/            # API app: views, serializers, utils (analysis logic)
│   ├── data/                # sample input files (sample.xlsx)
│   ├── requirements.txt
│   └── manage.py
└── frontend/                # React + Vite app
    ├── src/
    ├── public/
    ├── package.json
    └── vite.config.js
```

---

## Tech Stack

**Backend:** Python, Django, Django REST Framework, pandas, openpyxl, OpenAI SDK, SQLite
**Frontend:** React (Vite), Axios, Recharts, Bootstrap

---

## Getting Started

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Backend runs at `http://127.0.0.1:8000`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

---

## Environment Variables

Create a `.env` file in `backend/` (it is gitignored and must never be
committed). Generate a fresh secret key rather than reusing any example value.

```
SECRET_KEY=<your-generated-django-secret-key>
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
OPENAI_API_KEY=<your-openai-api-key>   # optional; the app falls back gracefully if unset
```

To generate a Django secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## API Endpoints

| Method | Endpoint         | Purpose                                                        |
| ------ | ---------------- | ------------------------------------------------------------- |
| POST   | `/api/analyze/`  | Analyze data for a query; returns summary, chart, and table.  |
| POST   | `/api/download/` | Download filtered results as `.xlsx` (default) or `.csv`.     |

**`/api/analyze/` request:** multipart form with `query` (required text) and an
optional `file` (Excel). If no file is provided, `backend/data/sample.xlsx` is
used.

**`/api/analyze/` response:**

```json
{
  "summary": "Analysis for Baner: Prices have increased by 12.4% from 2018 to 2023. Latest average price: 8450.",
  "areas_detected": ["Baner"],
  "intent": "trend",
  "metrics": ["price"],
  "chart": { "price_trend": {}, "demand_trend": {} },
  "table": []
}
```

**`/api/download/` request:** form with `query`, optional `file`, and optional
`format` (`excel` or `csv`).

---

## Features

- Natural-language query parsing (LLM-assisted, with a deterministic fallback).
- Automatic Excel header mapping to a normalized schema.
- Price and demand trend computation, grouped by year and area.
- Chart-ready and table-ready JSON output for the frontend.
- Export filtered data to Excel or CSV.
- Works with or without an OpenAI API key.

---

## Deployment

- **Frontend:** includes `vercel.json` for Vercel deployment.
- **Backend:** deployable to any Django-compatible host. For production, set
  `DEBUG=False`, a strong `SECRET_KEY`, and an explicit `ALLOWED_HOSTS`.
