"""Hybrid retrieval: vector similarity (pgvector) + BM25 keyword search, merged with
Reciprocal Rank Fusion (RRF).

Why hybrid: embeddings are great at semantic similarity ("how do we authenticate users") but
weak at exact identifier matches ("HYBRID_QUERY_PLANNER", "getUserById"). BM25 is the reverse.
RRF is a simple, well-established way to combine ranked lists without needing to calibrate
scores from two different systems onto the same scale.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.llm import embed_texts
from app.models.tables import Chunk

settings = get_settings()

RRF_K = 60  # standard RRF smoothing constant


@dataclass
class RetrievedChunk:
    chunk_id: str
    file_path: str
    symbol: str | None
    start_line: int
    end_line: int
    content: str
    vector_rank: int | None
    bm25_rank: int | None
    fused_score: float


def _load_bm25_index(project_id: UUID):
    index_path = Path(settings.bm25_index_dir) / f"{project_id}.pkl"
    if not index_path.exists():
        return None, None
    with open(index_path, "rb") as f:
        data = pickle.load(f)
    return data["bm25"], data["chunk_ids"]


def _vector_search(db: Session, project_id: UUID, query_embedding: list[float], top_k: int) -> list[str]:
    """Returns chunk ids ranked by cosine distance (pgvector <=> operator)."""
    stmt = (
        select(Chunk.id)
        .where(Chunk.project_id == project_id, Chunk.embedding.is_not(None))
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    rows = db.execute(stmt).all()
    return [str(r[0]) for r in rows]


def _bm25_search(project_id: UUID, query: str, top_k: int) -> list[str]:
    bm25, chunk_ids = _load_bm25_index(project_id)
    if bm25 is None:
        return []
    tokens = query.lower().split()
    scores = bm25.get_scores(tokens)
    ranked = sorted(zip(chunk_ids, scores), key=lambda x: x[1], reverse=True)
    return [cid for cid, score in ranked[:top_k] if score > 0]


def hybrid_search(db: Session, project_id: UUID, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    top_k = top_k or settings.retrieval_top_k
    candidate_pool = max(top_k * 3, 20)

    query_embedding = embed_texts([query])[0]

    vector_ids = _vector_search(db, project_id, query_embedding, candidate_pool)
    bm25_ids = _bm25_search(project_id, query, candidate_pool)

    vector_rank = {cid: i + 1 for i, cid in enumerate(vector_ids)}
    bm25_rank = {cid: i + 1 for i, cid in enumerate(bm25_ids)}

    all_ids = set(vector_ids) | set(bm25_ids)
    fused: dict[str, float] = {}
    for cid in all_ids:
        score = 0.0
        if cid in vector_rank:
            score += 1.0 / (RRF_K + vector_rank[cid])
        if cid in bm25_rank:
            score += 1.0 / (RRF_K + bm25_rank[cid])
        fused[cid] = score

    ranked_ids = sorted(fused.keys(), key=lambda cid: fused[cid], reverse=True)[:top_k]
    if not ranked_ids:
        return []

    chunks = db.execute(select(Chunk).where(Chunk.id.in_(ranked_ids))).scalars().all()
    chunks_by_id = {str(c.id): c for c in chunks}

    results = []
    for cid in ranked_ids:
        c = chunks_by_id.get(cid)
        if c is None:
            continue
        results.append(
            RetrievedChunk(
                chunk_id=cid,
                file_path=c.file_path,
                symbol=c.symbol,
                start_line=c.start_line,
                end_line=c.end_line,
                content=c.content,
                vector_rank=vector_rank.get(cid),
                bm25_rank=bm25_rank.get(cid),
                fused_score=fused[cid],
            )
        )
    return results
