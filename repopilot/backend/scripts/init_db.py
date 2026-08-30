"""Create the pgvector extension and all tables. Run once against a fresh database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.db import Base, engine
from app.models import tables  # noqa: F401  (import registers models with Base)

settings = get_settings()


def main() -> None:
    # Schema work needs a direct connection: a pooled endpoint (Neon's `-pooler` host,
    # PgBouncer in transaction mode) can't run session-level statements like
    # CREATE EXTENSION, and the failure never names pooling as the cause.
    if settings.database_url_unpooled:
        schema_engine = create_engine(settings.database_url_unpooled, pool_pre_ping=True)
        target = "direct (unpooled) connection"
    else:
        schema_engine = engine
        target = "DATABASE_URL"

    try:
        with schema_engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

        Base.metadata.create_all(bind=schema_engine)
    finally:
        if schema_engine is not engine:
            schema_engine.dispose()

    print(f"Database initialized via {target}: pgvector extension + tables created.")


if __name__ == "__main__":
    main()
