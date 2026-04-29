from functools import lru_cache
from os import getenv
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_URL = f"sqlite:///{(BACKEND_DIR / 'dev-preview.db').as_posix()}"


class Settings:
    app_name = "Researcher Intelligence Radar"
    app_env = getenv("APP_ENV", "development")
    database_url = getenv(
        "DATABASE_URL",
        DEFAULT_SQLITE_URL,
    )
    ai_provider = getenv("AI_PROVIDER", "").strip()
    ai_model = getenv("AI_MODEL", "").strip()
    ai_api_key = getenv("AI_API_KEY", "").strip()
    ai_base_url = getenv("AI_BASE_URL", "https://api.openai.com/v1").strip()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
