"""Create the pgvector extension and all tables. Run once against a fresh database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.db import Base, engine
from app.models import tables  # noqa: F401  (import registers models with Base)


def main() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
    print("Database initialized: pgvector extension + tables created.")


if __name__ == "__main__":
    main()
