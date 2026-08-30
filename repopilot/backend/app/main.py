import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_projects import router as projects_router
from app.api.routes_query import router as query_router
from app.api.routes_eval import router as eval_router
from app.api.routes_fs import router as fs_router
from app.core.config import get_settings

logger = logging.getLogger("repopilot")

settings = get_settings()

app = FastAPI(title="RepoPilot API", version="0.1.0")

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

# An empty CORS_ORIGINS (set in a dashboard but left blank, or trimmed to nothing) parses
# to an empty allow-list, which blocks every browser request while every server-side call
# still works — a failure that looks like "the frontend is broken" and gives no hint why.
# Nobody means "allow nothing", so treat it as unset and say so loudly.
if not _origins:
    logger.warning(
        "CORS_ORIGINS resolved to an empty list (raw value: %r); falling back to '*'. "
        "Set it to your frontend's exact origin, e.g. https://your-app.onrender.com",
        settings.cors_origins,
    )
    _origins = ["*"]

logger.info("CORS allowed origins: %s", _origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(query_router, prefix="/api/query", tags=["query"])
app.include_router(eval_router, prefix="/api/eval", tags=["eval"])
app.include_router(fs_router, prefix="/api/fs", tags=["fs"])


@app.get("/api/health")
def health() -> dict:
    # cors_origins is echoed back because a misconfigured allow-list is otherwise
    # invisible from outside: the browser just reports a CORS failure with no way to
    # see what the server actually has. These are public URLs, not secrets.
    return {
        "status": "ok",
        "cors_origins": _origins,
        "fs_browser_enabled": settings.enable_fs_browser,
    }
