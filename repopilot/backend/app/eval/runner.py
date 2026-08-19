"""Evaluation harness: runs a golden Q&A set through the full retrieval + agent pipeline and
scores retrieval quality (precision@k, MRR) and answer quality (LLM-as-judge).

This is the piece most student projects skip entirely. Re-run this after any change to
chunking, retrieval, or prompts and diff the numbers — that before/after story is the whole
point of building an eval harness instead of eyeballing a few chat responses.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.loop import run_agent
from app.core.llm import judge_answer
from app.models.tables import EvalRun, Project
from app.retrieval.hybrid import hybrid_search


@dataclass
class ExampleResult:
    question: str
    reference_answer: str
    agent_answer: str
    retrieval_hit: bool
    reciprocal_rank: float
    judge_score: float
    latency_ms: float
    cost_usd: float


def load_golden_set(path: str) -> list[dict]:
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def _retrieval_metrics(db: Session, project_id: UUID, question: str, expected_substring: str) -> tuple[bool, float]:
    results = hybrid_search(db, project_id, question)
    for rank, r in enumerate(results, start=1):
        if expected_substring in r.file_path:
            return True, 1.0 / rank
    return False, 0.0


def run_eval(db: Session, project: Project, dataset_path: str, dataset_name: str) -> dict:
    examples = load_golden_set(dataset_path)
    results: list[ExampleResult] = []

    for ex in examples:
        question = ex["question"]
        reference_answer = ex.get("reference_answer", "")
        expected_substring = ex.get("expected_file_substring", "")

        hit, rr = _retrieval_metrics(db, project.id, question, expected_substring)

        start = time.perf_counter()
        gen = run_agent(db, project.id, project.source_path, question)
        agent_answer = ""
        total_cost = 0.0
        try:
            while True:
                step = next(gen)
                if step.step_type == "final_answer":
                    agent_answer = step.text or ""
                total_cost += step.cost_usd
        except StopIteration as stop:
            if stop.value is not None:
                agent_answer = stop.value.final_answer
                total_cost = stop.value.total_cost_usd
        latency_ms = (time.perf_counter() - start) * 1000

        judge_score = judge_answer(question, reference_answer, agent_answer) if reference_answer else 0.0

        results.append(ExampleResult(
            question=question, reference_answer=reference_answer, agent_answer=agent_answer,
            retrieval_hit=hit, reciprocal_rank=rr, judge_score=judge_score,
            latency_ms=latency_ms, cost_usd=total_cost,
        ))

    n = len(results) or 1
    precision_at_k = sum(1 for r in results if r.retrieval_hit) / n
    mrr = sum(r.reciprocal_rank for r in results) / n
    judge_score_avg = sum(r.judge_score for r in results) / n
    avg_latency_ms = sum(r.latency_ms for r in results) / n
    avg_cost_usd = sum(r.cost_usd for r in results) / n

    report = {
        "dataset_name": dataset_name,
        "num_examples": len(results),
        "precision_at_k": precision_at_k,
        "mrr": mrr,
        "judge_score_avg": judge_score_avg,
        "avg_latency_ms": avg_latency_ms,
        "avg_cost_usd": avg_cost_usd,
        "examples": [asdict(r) for r in results],
    }

    eval_run = EvalRun(
        project_id=project.id,
        dataset_name=dataset_name,
        num_examples=len(results),
        precision_at_k=precision_at_k,
        mrr=mrr,
        judge_score_avg=judge_score_avg,
        avg_latency_ms=avg_latency_ms,
        avg_cost_usd=avg_cost_usd,
        report_json=json.dumps(report),
    )
    db.add(eval_run)
    db.commit()

    return report
