# 3-4 Week Roadmap

This scaffold gives you a working end-to-end system already: ingestion, hybrid retrieval, an
agent loop, an eval harness, and a chat + dashboard UI. Your job over the next few weeks is to
run it against a real repo, harden it, and add the depth that makes it yours in an interview.

## Week 1 — Get it running on a real repo, own the ingestion + retrieval layer
- Point `scripts/ingest.py` at 2-3 real open-source repos (pick ones with tests, e.g. a mid-size
  Python or JS library) and fix whatever breaks.
- Tune chunk size / overlap; compare retrieval quality before/after.
- Add a second language's chunker (e.g. JS/TS via a simple regex or `tree-sitter` if you want
  to go deeper — this is a great "I went beyond the scaffold" talking point).
- Write 15-25 golden Q&A pairs by hand for one repo (this *is* the differentiating work —
  don't skip it or delegate it to the model without checking).

## Week 2 — Make the agent actually agentic
- Add at least one more tool (e.g. `explain_diff`, `find_usages`, `run_linter`).
- Add a max-steps / max-cost guard and a "the agent gave up, here's what it tried" fallback —
  talk about this in interviews as "failure mode design," not just happy-path demos.
- Get SSE streaming working end-to-end in the UI so answers appear token-by-token with live
  tool-call status ("searching code...", "reading auth.py...").

## Week 3 — Evaluation and observability depth
- Run the eval suite, record baseline numbers, then deliberately try 2-3 retrieval strategies
  (chunk size, k, rerank vs no rerank) and show the eval numbers moving. This before/after eval
  story is the single most interview-differentiating artifact in this whole project.
- Add cost/latency tracking end-to-end and build the dashboard charts.
- Write up a short "eval report" (docs/EVAL_REPORT.md) with your numbers and what you learned —
  treat it like a mini design doc.

## Week 4 — Polish, deploy, tell the story
- Dockerize the full stack (`docker-compose.yml` already stubs the DB; extend it to backend +
  frontend) and deploy somewhere free (Render / Railway / Fly.io) so you have a live link.
- Record a 60-90s demo GIF/video for the README.
- Write the final README pass: problem, architecture diagram, eval numbers, live link, what
  you'd do with more time.
- Push to GitHub with clean commit history (not one giant commit — commit per milestone above).

## Draft resume bullets (edit once you have real numbers)

- Built RepoPilot, an agentic RAG system for codebase Q&A using FastAPI, PostgreSQL/pgvector,
  and the Gemini API, with hybrid (vector + BM25) retrieval and a five-tool agent loop for
  multi-step code search, file reading, and test execution.
- Designed and ran an evaluation harness (precision@k, MRR, LLM-as-judge) that measured
  retrieval and answer quality across N golden queries, improving [metric] by [X]% after
  tuning chunking strategy and retrieval fusion.
- Instrumented full request tracing (cost, latency, tool-call steps) and built an
  observability dashboard in React/Chart.js, reducing debugging time for failed agent runs.
- Streamed agent responses over Server-Sent Events for real-time multi-step tool-call visibility
  in the UI, mirroring production SSE patterns used at Beinex.

Only put numbers in bullets you can defend live in an interview — if asked "how did you measure
that 23%," you need a real answer.

## What NOT to do
- Don't skip the golden dataset. An eval harness with no real test cases is a demo prop, not a
  credential — interviewers will ask "how many queries, how'd you pick them."
- Don't over-scope the tool list. Five solid, well-tested tools beat fifteen flaky ones.
- Don't deploy with API keys committed. Use `.env` (already gitignored) and mention in the
  README that secrets are managed via environment variables — a small but real signal of
  engineering hygiene.
