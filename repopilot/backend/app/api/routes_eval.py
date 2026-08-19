import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.tables import EvalRun

router = APIRouter()


class EvalRunOut(BaseModel):
    id: str
    dataset_name: str
    num_examples: int
    precision_at_k: float
    mrr: float
    judge_score_avg: float
    avg_latency_ms: float
    avg_cost_usd: float
    created_at: str


@router.get("/runs", response_model=list[EvalRunOut])
def list_eval_runs(project_id: str, db: Session = Depends(get_db)):
    rows = db.execute(
        select(EvalRun).where(EvalRun.project_id == project_id).order_by(EvalRun.created_at.desc())
    ).scalars().all()
    return [
        EvalRunOut(
            id=str(r.id), dataset_name=r.dataset_name, num_examples=r.num_examples,
            precision_at_k=r.precision_at_k, mrr=r.mrr, judge_score_avg=r.judge_score_avg,
            avg_latency_ms=r.avg_latency_ms, avg_cost_usd=r.avg_cost_usd,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/runs/{run_id}/report")
def get_eval_report(run_id: str, db: Session = Depends(get_db)):
    row = db.get(EvalRun, run_id)
    if row is None:
        return {"error": "not found"}
    return json.loads(row.report_json)
