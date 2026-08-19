"""Retrieval fusion math, tested without needing a live DB/embedding API."""
from app.retrieval.hybrid import RRF_K


def _rrf_score(vector_rank, bm25_rank):
    score = 0.0
    if vector_rank is not None:
        score += 1.0 / (RRF_K + vector_rank)
    if bm25_rank is not None:
        score += 1.0 / (RRF_K + bm25_rank)
    return score


def test_rrf_rewards_items_ranked_high_in_both_lists():
    both_high = _rrf_score(1, 1)
    one_high_one_low = _rrf_score(1, 50)
    assert both_high > one_high_one_low


def test_rrf_handles_missing_from_one_list():
    only_vector = _rrf_score(1, None)
    only_bm25 = _rrf_score(None, 1)
    assert only_vector == only_bm25 > 0
