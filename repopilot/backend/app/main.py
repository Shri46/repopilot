from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_projects import router as projects_router
from app.api.routes_query import router as query_router
from app.api.routes_eval import router as eval_router

app = FastAPI(title="RepoPilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before deploying
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(query_router, prefix="/api/query", tags=["query"])
app.include_router(eval_router, prefix="/api/eval", tags=["eval"])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
