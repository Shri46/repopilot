import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.eval.runner import run_eval
from app.models.tables import EvalRun, Project

router = APIRouter()

EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"


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


@router.get("/datasets", response_model=list[str])
def list_datasets():
    if not EVAL_DIR.exists():
        return []
    return sorted(p.name for p in EVAL_DIR.glob("*.jsonl"))


class RunEvalRequest(BaseModel):
    project_id: str
    dataset_name: str = "golden_demo.jsonl"


@router.post("/run", response_model=EvalRunOut)
def trigger_eval_run(req: RunEvalRequest, db: Session = Depends(get_db)):
    project = db.get(Project, req.project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    dataset_path = EVAL_DIR / req.dataset_name
    if not dataset_path.exists():
        raise HTTPException(400, f"Dataset not found: {req.dataset_name}")

    run_eval(db, project, str(dataset_path), dataset_name=req.dataset_name)

    row = db.execute(
        select(EvalRun)
        .where(EvalRun.project_id == req.project_id)
        .order_by(EvalRun.created_at.desc())
        .limit(1)
    ).scalar_one()
    return EvalRunOut(
        id=str(row.id), dataset_name=row.dataset_name, num_examples=row.num_examples,
        precision_at_k=row.precision_at_k, mrr=row.mrr, judge_score_avg=row.judge_score_avg,
        avg_latency_ms=row.avg_latency_ms, avg_cost_usd=row.avg_cost_usd,
        created_at=row.created_at.isoformat(),
    )
