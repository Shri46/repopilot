# Setup

## Prerequisites
- Python 3.11+
- Node 18+
- Docker (for Postgres + pgvector) — or a local Postgres with the `vector` extension installed
- A Gemini API key: https://aistudio.google.com/apikey (free tier is enough to build and demo this)

## 1. Database

```bash
docker compose up -d db
```

This starts Postgres with the pgvector extension on port 5432 (user/pass/db: `repopilot`).

## 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or use your preferred env tool
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your GEMINI_API_KEY

python scripts/init_db.py
```

### Ingest a codebase

You can point this at any local repo — including this one, which doubles as a working demo
(the golden dataset in `backend/eval/golden_demo.jsonl` is written against RepoPilot's own
backend code):

```bash
python scripts/ingest.py --repo ../backend --project demo
```

For a bigger, more realistic demo, ingest a real open-source repo:

```bash
git clone https://github.com/psf/requests /tmp/requests
python scripts/ingest.py --repo /tmp/requests --project requests
```

### Run the API

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/api/health` to confirm it's up, and `http://localhost:8000/docs`
for the interactive API docs (FastAPI's built-in Swagger UI).

### Run the eval suite

```bash
python scripts/run_eval.py --project demo --dataset eval/golden_demo.jsonl
```

Prints precision@k, MRR, judge score, latency, and cost, and writes a full JSON report to
`eval_report_latest.json` and to the `eval_runs` table (which the dashboard reads).

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed localhost URL. The dev server proxies `/api` to `http://localhost:8000`
(see `vite.config.js`), so the backend must be running first.

## Troubleshooting

- **"GEMINI_API_KEY is not set"** — you skipped `.env` setup in the backend, or it's not in the
  directory `uvicorn`/the scripts are run from.
- **pgvector errors on init_db** — make sure you're using the `ankane/pgvector` image (already
  set in `docker-compose.yml`), not a plain `postgres` image.
- **No results from search_code** — check that ingestion actually ran (`chunk_count` in
  `GET /api/projects` should be > 0) and that `--no-embed` wasn't passed.
- **Frontend shows no projects** — the frontend calls `GET /api/projects`; confirm the backend
  is running and reachable at `localhost:8000` and that you've ingested at least one project.
