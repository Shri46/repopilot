import re
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.ingestion.ingest import ingest_repo
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


@router.post("/ingest", response_model=ProjectOut)
def ingest(req: IngestRequest, db: Session = Depends(get_db)):
    try:
        project = ingest_repo(db, project_name=req.name, repo_path=req.repo_path)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e)) from e
    chunk_count = db.execute(
        select(func.count(Chunk.id)).where(Chunk.project_id == project.id)
    ).scalar_one()
    return ProjectOut(id=str(project.id), name=project.name, source_path=project.source_path, chunk_count=chunk_count)


@router.post("/clone", response_model=ProjectOut)
def clone_and_ingest(req: CloneRequest, db: Session = Depends(get_db)):
    git_url = req.git_url.strip()
    # Reject option-injection attempts (a URL starting with "-" could be parsed by git as a
    # flag, e.g. --upload-pack=...) and anything that isn't a recognizable git transport.
    if git_url.startswith("-") or not git_url.startswith(_ALLOWED_URL_PREFIXES):
        raise HTTPException(400, "git_url must be a valid http(s)/git/ssh repository URL")

    CLONE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", req.name).strip("_") or "repo"
    dest = CLONE_DIR / safe_name
    if dest.exists():
        raise HTTPException(400, f"A clone already exists at {dest} — delete that project first or pick a different name.")

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--", git_url, str(dest)],
            capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired as e:
        raise HTTPException(504, "git clone timed out after 5 minutes") from e
    except FileNotFoundError as e:
        raise HTTPException(500, "git is not installed on the server") from e

    if result.returncode != 0:
        raise HTTPException(400, f"git clone failed: {result.stderr[-500:]}")

    try:
        project = ingest_repo(db, project_name=req.name, repo_path=str(dest))
    except FileNotFoundError as e:
        raise HTTPException(400, str(e)) from e

    chunk_count = db.execute(
        select(func.count(Chunk.id)).where(Chunk.project_id == project.id)
    ).scalar_one()
    return ProjectOut(id=str(project.id), name=project.name, source_path=project.source_path, chunk_count=chunk_count)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    db.delete(project)  # cascades to chunks, queries, trace_steps, eval_runs
    db.commit()

    bm25_path = Path(settings.bm25_index_dir) / f"{project_id}.pkl"
    bm25_path.unlink(missing_ok=True)
