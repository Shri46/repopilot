FROM python:3.12-slim

# git is needed for git-blame metadata during ingestion (best-effort — the app degrades
# gracefully without it, but this keeps that feature working in the containerized build).
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Creates the pgvector extension + tables if they don't exist, then serves. $PORT is what
# Render (and most PaaS) inject; 8000 is the local/compose default.
CMD ["sh", "-c", "python scripts/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
