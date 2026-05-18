from functools import lru_cache
import os
from os import getenv
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_URL = f"sqlite:///{(BACKEND_DIR / 'dev-preview.db').as_posix()}"
LOCAL_ENV_KEYS = {
    "AI_PROVIDER",
    "AI_MODEL",
    "AI_FAST_MODEL",
    "AI_HIGH_MODEL",
    "AI_API_KEY",
    "AI_BASE_URL",
    "X_BEARER_TOKEN",
}


def _load_local_ai_env() -> None:
    if any("pytest" in Path(argument).name for argument in sys.argv):
        return
    for env_path in (BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if key not in LOCAL_ENV_KEYS or os.environ.get(key):
                continue
            os.environ[key] = value.strip().strip('"').strip("'")


_load_local_ai_env()


class Settings:
    app_name = "Researcher Intelligence Radar"
    app_env = getenv("APP_ENV", "development")
    database_url = getenv(
        "DATABASE_URL",
        DEFAULT_SQLITE_URL,
    )
    ai_provider = getenv("AI_PROVIDER", "").strip()
    ai_model = getenv("AI_MODEL", "").strip()
    ai_fast_model = getenv("AI_FAST_MODEL", "").strip()
    ai_high_model = getenv("AI_HIGH_MODEL", "").strip()
    ai_api_key = getenv("AI_API_KEY", "").strip()
    ai_base_url = getenv("AI_BASE_URL", "https://api.openai.com/v1").strip()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
