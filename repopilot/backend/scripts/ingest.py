"""CLI entrypoint: python scripts/ingest.py --repo /path/to/repo --project demo"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal
from app.ingestion.ingest import ingest_repo


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Path to the repo to ingest")
    parser.add_argument("--project", required=True, help="Project name (used to look it up later)")
    parser.add_argument(
        "--no-embed", action="store_true",
        help="Skip embedding calls (useful for a dry run / testing the chunker without an API key)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        ingest_repo(db, project_name=args.project, repo_path=args.repo, embed=not args.no_embed)
    finally:
        db.close()


if __name__ == "__main__":
    main()
