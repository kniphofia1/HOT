from functools import lru_cache
from os import getenv


class Settings:
    app_name = "Researcher Intelligence Radar"
    app_env = getenv("APP_ENV", "development")
    database_url = getenv(
        "DATABASE_URL",
        "postgresql+psycopg://radar:radar@localhost:5432/radar",
    )


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
