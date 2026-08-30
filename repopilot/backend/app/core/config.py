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


@lru_cache
def get_settings() -> Settings:
    return Settings()
