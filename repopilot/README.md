# RepoPilot — Agentic Codebase Assistant with Evals & Observability

RepoPilot is an AI agent that answers questions about a codebase, takes actions inside it
(search, read files, grep, run tests, git blame), and — the part almost nobody builds — ships
with an **evaluation harness** and an **observability dashboard** so you can prove the system
actually works, and keep proving it as you change it.

It's the "why should we trust this LLM system" story, told in code, not in a slide.

## Why this project

Most student LLM projects stop at "I called the Gemini API and it worked once." Interviewers at
AI-forward companies now specifically probe for three things almost no bootcamp project has:

1. **Retrieval quality measurement** — not just "does the chatbot answer," but precision@k,
   MRR, and whether the right chunks were even retrieved.
2. **Agentic tool use** — multi-step reasoning where the model decides which tool to call next,
   not a single prompt-response round trip.
3. **Production observability** — cost per query, latency breakdown, and traces you can debug
   with, the same way you'd instrument any backend service.

This project builds all three, on a stack you already know (Python, FastAPI, PostgreSQL,
React, Gemini) so you can extend it fast and explain every line in an interview.

See `docs/ARCHITECTURE.md` for the system design and `docs/ROADMAP.md` for the week-by-week
build plan and draft resume bullets.

## Quick start

```bash
cp backend/.env.example backend/.env   # add your GEMINI_API_KEY
docker compose up -d db                # Postgres + pgvector
cd backend
pip install -r requirements.txt
python scripts/init_db.py
python scripts/ingest.py --repo /path/to/some/repo --project demo
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend, pick the `demo` project, and ask it a question about the ingested repo.

Run the eval suite:

```bash
cd backend
python scripts/run_eval.py --project demo --dataset eval/golden_demo.jsonl
```

Full details in `docs/SETUP.md`.
