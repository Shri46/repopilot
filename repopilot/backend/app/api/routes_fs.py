"""Server-side directory browser for the ingest UI's folder picker.

Browsers can't hand a web page an absolute local filesystem path (the File System Access
API only returns opaque handles), but ingestion needs one to walk with os.walk. Since this
is a local dev tool where the backend and the browser run on the same machine, browsing the
backend's own filesystem and returning real paths is the simplest correct approach — same
trust model as the rest of this app (no auth anywhere else either).
"""
import os
import string
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def _list_drives() -> list[dict]:
    return [
        {"name": f"{letter}:\\", "path": f"{letter}:\\", "type": "dir"}
        for letter in string.ascii_uppercase
        if os.path.exists(f"{letter}:\\")
    ]


@router.get("/browse")
def browse(path: str = Query("")):
    if not path:
        if os.name == "nt":
            return {"path": "", "parent": None, "entries": _list_drives()}
        path = "/"

    p = Path(path)
    if not p.exists() or not p.is_dir():
        raise HTTPException(400, f"Not a directory: {path}")

    try:
        entries = [
            {"name": child.name, "path": str(child), "type": "dir"}
            for child in sorted(p.iterdir(), key=lambda c: c.name.lower())
            if not child.name.startswith(".") and _safe_is_dir(child)
        ]
    except PermissionError as e:
        raise HTTPException(403, f"Permission denied: {path}") from e

    parent = None if p.parent == p else str(p.parent)
    if os.name == "nt" and str(p) == str(p.anchor):
        parent = ""  # drive root -> back to the drive list

    return {"path": str(p), "parent": parent, "entries": entries}


def _safe_is_dir(p: Path) -> bool:
    try:
        return p.is_dir()
    except OSError:
        return False
