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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
