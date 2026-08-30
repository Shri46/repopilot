from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    database_url: str = "postgresql+psycopg://repopilot:repopilot@localhost:5433/repopilot"

    agent_max_steps: int = 6
    agent_model: str = "gemini-3.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    retrieval_top_k: int = 8

    bm25_index_dir: str = "data/bm25_index"

    # The folder picker exposes the server's filesystem to whoever can reach the API.
    # That's fine for the local single-user setup this is designed for, but it's an
    # information-disclosure hole on anything public — set ENABLE_FS_BROWSER=false when
    # deploying, and ingest via the clone-from-URL path instead.
    enable_fs_browser: bool = True

    # Comma-separated allowed browser origins, e.g. "https://repopilot.onrender.com".
    # "*" (the default) is fine locally but should be narrowed on a real deployment,
    # where the frontend is served from a different origin than the API.
    cors_origins: str = "*"

    # --- Public-deployment guardrails -------------------------------------------------
    # All default to "off" so local single-user use is unrestricted. Turn them on for any
    # deployment strangers can reach, where the real risk isn't malice so much as one
    # person ingesting a huge repo and burning the whole day's Gemini quota.
    #
    # 0 means unlimited.
    max_ingest_chunks: int = 0      # reject a repo before embedding if it chunks to more
    max_projects: int = 0           # cap total ingested projects
    rate_limit_enabled: bool = False
    rate_limit_ingest_per_hour: int = 3
    rate_limit_query_per_hour: int = 30
    rate_limit_eval_per_hour: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
