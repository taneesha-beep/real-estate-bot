# Real Estate Analysis Bot

Compare real-estate price and demand trends using natural-language queries and Excel data. A React interface displays the analysis as interactive charts, a summary, and downloadable results.

**[Live demo](https://real-estate-bot-black.vercel.app/)** · Frontend on Vercel · Django API on Render

Try **“Compare price and demand trends in Wakad and Aundh”** without uploading a file to use the bundled sample dataset.

## Features

- Upload an `.xlsx` workbook or explore the included sample data.
- Compare areas with price and demand charts, a filtered data table, and Excel/CSV exports.
- Use optional OpenAI integration for query interpretation and summaries, with deterministic fallbacks when the key is absent or a request fails.
- Get clear errors for invalid files, missing columns, and unmatched areas.

## Architecture

**React → Django REST API → Excel normalization → area matching → pandas aggregation → charts, table, and summary**

The backend computes the numeric results with pandas. The LLM interprets queries and summarizes computed statistics; it does not calculate chart values. Model-selected areas are validated against the dataset, and missing years remain gaps in charts rather than becoming zeroes.

| Layer | Stack |
| --- | --- |
| Frontend | React 19, Vite 7, Recharts, Axios, Bootstrap |
| Backend | Python 3.11, Django 5.2, Django REST Framework 3.16 |
| Data and AI | pandas, openpyxl, OpenAI API (`gpt-4o-mini`, optional) |
| Deployment | Vercel; Render with Gunicorn and WhiteNoise |

## Run locally

Requires **Python 3.11** and **Node.js 20.19+ or 22.12+**. Clone this repository, then run:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

In another terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The API runs at `http://localhost:8000`.

Configure these variables in `backend/.env`; keep credentials out of Git:

| Variable | Purpose / local value |
| --- | --- |
| `SECRET_KEY` | Your generated Django secret key |
| `DEBUG` | `True` locally; `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` |
| `OPENAI_API_KEY` | Optional; leave unset to use the fallback |

For a different backend, set `VITE_API_URL` in `frontend/.env` to its base URL, without `/api`. Production uses `https://real-estate-bot-cmd5.onrender.com`; Render's CORS allowlist must include the frontend origin.

## Data and API

Uploads must be **`.xlsx`, up to 5 MB**, with columns `year`, `area`, `price`, `demand`, and `size` (case-insensitive). IGR-style headers are also mapped automatically. The bundled [sample workbook](backend/data/sample.xlsx) contains four areas across 2020–2024.

| Endpoint | Request | Result |
| --- | --- | --- |
| `POST /api/analyze/` | `query` and optional `file` | Summary, detected areas, charts, and table |
| `POST /api/download/` | Same fields, plus `format`: `excel` or `csv` | Filtered workbook or CSV |

Send fields as multipart form data. Queries are limited to 500 characters.

## Validation

```bash
# backend/ — with the virtual environment active
pip install -r requirements-dev.txt
pytest -q

# frontend/
npm run lint
npm run build
```

Five backend regression tests cover header normalization, area matching, missing-year chart alignment, JSON-safe output, and the analysis endpoint without an OpenAI key.

## Scope

- Analyzes supplied historical data; it does not fetch live property listings or forecast prices.
- No saved query history or application-level dataset persistence.
- The fallback requires recognizable area names and produces price-focused summaries; demand charts remain available.
