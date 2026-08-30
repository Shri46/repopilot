"""Core ingestion logic: walk a repo, chunk files, embed, persist to Postgres + BM25 index."""
from __future__ import annotations

import os
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from tqdm import tqdm

from app.core.config import get_settings
from app.core.llm import embed_texts
from app.ingestion.chunker import MAX_FILE_BYTES, chunk_file, should_skip_path
from app.ingestion.git_meta import blame_for_range, get_repo
from app.models.tables import Chunk, Project

settings = get_settings()

EMBED_BATCH_SIZE = 32


class IngestTooLargeError(Exception):
    """Raised when a repo exceeds MAX_INGEST_CHUNKS, before any embedding calls are spent."""


class IngestEmptyError(Exception):
    """Raised when a path contains no chunkable source files."""


def _iter_source_files(repo_path: Path):
    for root, dirs, files in os.walk(repo_path):
        rel_parts = Path(root).relative_to(repo_path).parts
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", "venv", ".venv"}]
        for filename in files:
            if should_skip_path(list(rel_parts), filename):
                continue
            full_path = Path(root) / filename
            try:
                if full_path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield full_path


def ingest_repo(db: Session, project_name: str, repo_path: str, embed: bool = True) -> Project:
    repo_path_obj = Path(repo_path).resolve()
    if not repo_path_obj.exists():
        raise FileNotFoundError(f"repo path does not exist: {repo_path}")

    git_repo = get_repo(str(repo_path_obj))

    # Everything up to the project row is deliberately side-effect free. Scanning, the size
    # check, and embedding all happen first so that a repo that's too large — or an
    # embedding call that runs out of quota partway through — leaves no half-created,
    # zero-chunk project behind for someone to clean up by hand.
    raw_chunks = []
    for file_path in tqdm(list(_iter_source_files(repo_path_obj)), desc="scanning files"):
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not text.strip():
            continue
        rel_path = str(file_path.relative_to(repo_path_obj))
        raw_chunks.extend(chunk_file(text, rel_path))

    if not raw_chunks:
        raise IngestEmptyError(
            "No chunkable source files found — check the path and that it contains code."
        )

    if settings.max_ingest_chunks and len(raw_chunks) > settings.max_ingest_chunks:
        raise IngestTooLargeError(
            f"This repo produces {len(raw_chunks)} chunks, over the {settings.max_ingest_chunks} "
            f"limit configured on this server. Try a smaller repo."
        )

    texts = [c.content for c in raw_chunks]
    embeddings: list[list[float] | None] = [None] * len(texts)

    if embed:
        for i in tqdm(range(0, len(texts), EMBED_BATCH_SIZE), desc="embedding"):
            batch = texts[i:i + EMBED_BATCH_SIZE]
            batch_embeddings = embed_texts(batch)
            for j, emb in enumerate(batch_embeddings):
                embeddings[i + j] = emb

    # The expensive work succeeded — now it's safe to write.
    project = db.query(Project).filter_by(name=project_name).first()
    if project is None:
        project = Project(name=project_name, source_path=str(repo_path_obj))
        db.add(project)
        db.commit()
        db.refresh(project)
    else:
        # Re-ingest: wipe old chunks for a clean rebuild.
        db.query(Chunk).filter_by(project_id=project.id).delete()
        db.commit()

    bm25_corpus_tokens = []
    chunk_rows = []
    blame_cache: dict = {}  # one git blame per file, not per chunk
    for idx, rc in enumerate(tqdm(raw_chunks, desc="persisting chunks")):
        author, modified = (None, None)
        if git_repo is not None:
            author, modified = blame_for_range(
                git_repo, rc.file_path, rc.start_line, rc.end_line, cache=blame_cache
            )

        chunk = Chunk(
            project_id=project.id,
            file_path=rc.file_path,
            symbol=rc.symbol,
            start_line=rc.start_line,
            end_line=rc.end_line,
            content=rc.content,
            git_author=author,
            git_last_modified=modified,
            embedding=embeddings[idx],
        )
        db.add(chunk)
        chunk_rows.append(chunk)
        bm25_corpus_tokens.append(rc.content.lower().split())

    db.commit()

    _persist_bm25_index(project.id, chunk_rows, bm25_corpus_tokens)

    print(f"Ingested {len(chunk_rows)} chunks for project '{project_name}'.")
    return project


def _persist_bm25_index(project_id, chunk_rows, corpus_tokens) -> None:
    Path(settings.bm25_index_dir).mkdir(parents=True, exist_ok=True)
    index_path = Path(settings.bm25_index_dir) / f"{project_id}.pkl"

    bm25 = BM25Okapi(corpus_tokens)
    chunk_ids = [str(c.id) for c in chunk_rows]

    with open(index_path, "wb") as f:
        pickle.dump({"bm25": bm25, "chunk_ids": chunk_ids}, f)
