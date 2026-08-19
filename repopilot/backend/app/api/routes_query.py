import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.agent.loop import run_agent
from app.core.db import get_db
from app.models.tables import Project, Query, TraceStep

router = APIRouter()


class QueryRequest(BaseModel):
    project_id: str
    question: str


def _persist_run(db: Session, project_id: str, question: str, steps, final_answer, total_latency_ms, total_cost_usd):
    query_row = Query(
        project_id=project_id,
        question=question,
        final_answer=final_answer,
        total_latency_ms=total_latency_ms,
        total_cost_usd=total_cost_usd,
    )
    db.add(query_row)
    db.flush()

    for s in steps:
        db.add(TraceStep(
            query_id=query_row.id,
            step_index=s.step_index,
            step_type=s.step_type,
            tool_name=s.tool_name,
            tool_input=json.dumps(s.tool_input) if s.tool_input else None,
            tool_output=s.tool_output,
            latency_ms=s.latency_ms,
            tokens_in=s.tokens_in,
            tokens_out=s.tokens_out,
        ))
    db.commit()
    return query_row


@router.post("/stream")
async def query_stream(req: QueryRequest, db: Session = Depends(get_db)):
    project = db.get(Project, req.project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    async def event_generator():
        gen = run_agent(db, project.id, project.source_path, req.question)
        collected_steps = []
        final_result = None
        try:
            while True:
                step = next(gen)
                collected_steps.append(step)
                yield {
                    "event": "step",
                    "data": json.dumps({
                        "step_index": step.step_index,
                        "step_type": step.step_type,
                        "tool_name": step.tool_name,
                        "tool_input": step.tool_input,
                        "tool_output": step.tool_output,
                        "text": step.text,
                    }),
                }
        except StopIteration as stop:
            final_result = stop.value

        if final_result is not None:
            _persist_run(
                db, project.id, req.question, final_result.steps, final_result.final_answer,
                final_result.total_latency_ms, final_result.total_cost_usd,
            )
            yield {
                "event": "done",
                "data": json.dumps({
                    "final_answer": final_result.final_answer,
                    "total_latency_ms": final_result.total_latency_ms,
                    "total_cost_usd": final_result.total_cost_usd,
                }),
            }

    return EventSourceResponse(event_generator())
