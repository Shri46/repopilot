import json

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import run_in_threadpool

from app.agent.loop import run_agent
from app.core import limits
from app.core.config import get_settings
from app.core.db import get_db
from app.models.tables import Project, Query, TraceStep

settings = get_settings()

router = APIRouter()

_GENERATOR_DONE = object()


def _advance(gen):
    """Runs one `next(gen)` step, catching StopIteration here.

    StopIteration raised inside a function executed via run_in_threadpool doesn't
    propagate as a catchable StopIteration on the awaiting side (PEP 479 turns it into
    a RuntimeError once it crosses back into async/generator machinery), so it must be
    converted to a normal return value before crossing that boundary.
    """
    try:
        return next(gen), None
    except StopIteration as stop:
        return _GENERATOR_DONE, stop.value


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


@router.get("/stream")
async def query_stream(
    request: Request,
    project_id: str = QueryParam(...),
    question: str = QueryParam(...),
    db: Session = Depends(get_db),
):
    limits.enforce(request, "query", settings.rate_limit_query_per_hour)

    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    async def event_generator():
        gen = run_agent(db, project.id, project.source_path, question)
        collected_steps = []
        final_result = None
        while True:
            # Each step blocks on a Gemini call; run it in a worker thread so this
            # request doesn't freeze the event loop (and every other concurrent
            # request) for the full duration of the agent loop.
            step, final_result = await run_in_threadpool(_advance, gen)
            if step is _GENERATOR_DONE:
                break
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

        if final_result is not None:
            _persist_run(
                db, project.id, question, final_result.steps, final_result.final_answer,
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
