from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.ingestion.ingest import ingest_repo
from app.models.tables import Chunk, Project

router = APIRouter()


class ProjectOut(BaseModel):
    id: str
    name: str
    source_path: str
    chunk_count: int


class IngestRequest(BaseModel):
    name: str
    repo_path: str


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
    project = ingest_repo(db, project_name=req.name, repo_path=req.repo_path)
    chunk_count = db.execute(
        select(func.count(Chunk.id)).where(Chunk.project_id == project.id)
    ).scalar_one()
    return ProjectOut(id=str(project.id), name=project.name, source_path=project.source_path, chunk_count=chunk_count)
