# Deployment

Two supported shapes: the **full local stack** (everything in Docker on your machine) and a
**public demo deploy**. They differ in one important way — see "What changes in the cloud".

## 1. Full local stack

Runs Postgres + backend + frontend with one command.

```bash
cd repopilot
cp backend/.env.example backend/.env   # then paste your GEMINI_API_KEY into it
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Postgres: `localhost:5433` (user/pass/db all `repopilot`)

The backend container runs `scripts/init_db.py` on start, so the pgvector extension and
tables are created automatically on first boot.

### Ingesting local repos from the container

Local-folder ingestion reads the **container's** filesystem, not your host's. `docker-compose.yml`
bind-mounts a host directory read-only at `/repos` inside the backend:

```yaml
- ${HOST_REPOS:-..}:/repos:ro
```

By default that's this repo's parent directory. To expose somewhere else:

```bash
HOST_REPOS=C:\Users\you\Documents\GitHub docker compose up --build
```

Then in the ingest UI use **Browse…** and navigate to `/repos`. Paths you type must also be
container paths (`/repos/my-project`), not host paths (`C:\...`).

If you'd rather not think about mounts, use the **Clone from URL** tab instead — it clones into
the container's own storage and works identically in both setups.

### Persistence

Two named volumes survive `docker compose down`:

- `repopilot_pgdata` — Postgres data (projects, chunks, traces, eval runs)
- `repopilot_data` — BM25 indexes and cloned repos

`docker compose down -v` deletes both. That's the clean-slate reset.

## 2. Public demo deploy

Anything that can run two Docker images plus a pgvector-capable Postgres works
(Render, Railway, Fly.io, Cloud Run, a VPS). The pieces you need:

| Piece | Requirement |
|---|---|
| Database | Postgres **with the `vector` extension available** — plain Postgres won't work. Verify your provider supports pgvector before committing to it. |
| Backend | The `backend/` image. Needs `DATABASE_URL` and `GEMINI_API_KEY`. |
| Frontend | The `frontend/` image. It's built with `VITE_API_BASE=/api` and nginx proxies `/api` to the backend, so it must be able to resolve a host named `backend` — if your platform names services differently, override `proxy_pass` in `frontend/nginx.conf`. |

### What changes in the cloud

**Turn off the folder browser.** `/api/fs/browse` lists the server's filesystem. That's
harmless on your laptop and an information-disclosure hole on a public URL. Set:

```
ENABLE_FS_BROWSER=false
```

The endpoint then 404s and the UI hides the **Browse…** button automatically. Ingestion still
works via **Clone from URL**.

**Local-folder ingestion is effectively gone.** A cloud container can't see your machine.
Clone-from-URL becomes the only practical path, so pre-seed a demo project (clone a
well-known public repo) before sharing the link.

**CORS is currently wide open.** `app/main.py` sets `allow_origins=["*"]`. Narrow it to your
frontend's origin before deploying:

```python
allow_origins=["https://your-frontend.example.com"],
```

**There is no authentication.** Anyone with the URL can ingest repos, run evals, and spend
your Gemini quota. For a portfolio demo that's usually acceptable if you keep the key on a
free tier — just know that's the trade.

**Free-tier Gemini limits bite.** `gemini-3.5-flash-lite` free tier allows ~15 requests/min
and a capped daily total. A single agent run can use up to `AGENT_MAX_STEPS` (default 6)
generation calls, and ingesting a mid-size repo takes hundreds of embedding calls. Ingest
your demo project once, then leave it — don't expect visitors to ingest their own.

### Cost

Roughly $0.0004–$0.002 per query on `gemini-3.5-flash-lite`, and embeddings are free/near-free
on current tiers. The dashboard tracks real per-query cost, so you can check rather than guess.
