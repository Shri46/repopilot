import re
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import limits
from app.core.config import get_settings
from app.core.db import get_db
from app.ingestion.ingest import IngestEmptyError, IngestTooLargeError, ingest_repo
from app.models.tables import Chunk, Project

settings = get_settings()

router = APIRouter()

CLONE_DIR = Path(__file__).resolve().parents[2] / "data" / "clones"
_ALLOWED_URL_PREFIXES = ("http://", "https://", "git://", "git@", "ssh://")


class ProjectOut(BaseModel):
    id: str
    name: str
    source_path: str
    chunk_count: int


class IngestRequest(BaseModel):
    name: str
    repo_path: str


class CloneRequest(BaseModel):
    name: str
    git_url: str


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Project, func.count(Chunk.id))
        .join(Chunk, Chunk.project_id == Project.id, isouter=True)
        .group_by(Project.id)
    ).all()
    return [
        ProjectOut(id=str(p.id), name=p.name, source_path=p.source_path, chunk_count=count)
        for p, count in rows
    ]


def _check_project_cap(db: Session, name: str) -> None:
    """Caps total projects on public deployments. Re-ingesting an existing name is exempt."""
    if not settings.max_projects:
        return
    if db.query(Project).filter_by(name=name).first() is not None:
        return
    count = db.execute(select(func.count(Project.id))).scalar_one()
    if count >= settings.max_projects:
        raise HTTPException(
            409,
            f"This server is capped at {settings.max_projects} projects and is currently full. "
            "Delete one first.",
        )


def _ingest_or_400(db: Session, name: str, repo_path: str) -> Project:
    try:
        return ingest_repo(db, project_name=name, repo_path=repo_path)
    except (FileNotFoundError, IngestTooLargeError, IngestEmptyError) as e:
        raise HTTPException(400, str(e)) from e


def _project_out(db: Session, project: Project) -> ProjectOut:
    chunk_count = db.execute(
        select(func.count(Chunk.id)).where(Chunk.project_id == project.id)
    ).scalar_one()
    return ProjectOut(
        id=str(project.id), name=project.name,
        source_path=project.source_path, chunk_count=chunk_count,
    )


@router.post("/ingest", response_model=ProjectOut)
def ingest(req: IngestRequest, request: Request, db: Session = Depends(get_db)):
    limits.enforce(request, "ingest", settings.rate_limit_ingest_per_hour)
    _check_project_cap(db, req.name)
    project = _ingest_or_400(db, req.name, req.repo_path)
    return _project_out(db, project)


@router.post("/clone", response_model=ProjectOut)
def clone_and_ingest(req: CloneRequest, request: Request, db: Session = Depends(get_db)):
    limits.enforce(request, "ingest", settings.rate_limit_ingest_per_hour)

    git_url = req.git_url.strip()
    # Reject option-injection attempts (a URL starting with "-" could be parsed by git as a
    # flag, e.g. --upload-pack=...) and anything that isn't a recognizable git transport.
    if git_url.startswith("-") or not git_url.startswith(_ALLOWED_URL_PREFIXES):
        raise HTTPException(400, "git_url must be a valid http(s)/git/ssh repository URL")

    _check_project_cap(db, req.name)

    CLONE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", req.name).strip("_") or "repo"
    dest = CLONE_DIR / safe_name
    if dest.exists():
        raise HTTPException(
            400,
            f"A clone already exists for '{req.name}' — delete that project first or pick a different name.",
        )

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--", git_url, str(dest)],
            capture_output=True, text=True, timeout=300,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired as e:
        shutil.rmtree(dest, ignore_errors=True)
        raise HTTPException(504, "git clone timed out after 5 minutes") from e
    except FileNotFoundError as e:
        raise HTTPException(500, "git is not installed on the server") from e

    if result.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        raise HTTPException(400, f"git clone failed: {(result.stderr or '')[-500:]}")

    # Without this, a failed ingest (too large, quota exhausted, ...) leaves the cloned
    # directory behind, and the dest.exists() check above then blocks every retry.
    try:
        project = _ingest_or_400(db, req.name, str(dest))
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise

    return _project_out(db, project)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    source_path = project.source_path

    db.delete(project)  # cascades to chunks, queries, trace_steps, eval_runs
    db.commit()

    bm25_path = Path(settings.bm25_index_dir) / f"{project_id}.pkl"
    bm25_path.unlink(missing_ok=True)

    # If this project came from the clone flow, drop the cloned checkout too. Leaving it
    # behind would make the dest.exists() guard in /clone reject re-cloning the same name.
    # Guard on CLONE_DIR so we never touch a user's own directory from the local-path flow.
    try:
        resolved = Path(source_path).resolve()
        if resolved.is_relative_to(CLONE_DIR.resolve()) and resolved != CLONE_DIR.resolve():
            shutil.rmtree(resolved, ignore_errors=True)
    except (OSError, ValueError):
        pass
