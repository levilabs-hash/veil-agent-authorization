"""SQLite connection helpers. Simulated environment only; no real external accounts."""

from app.core.config import DATABASE_PATH


def database_path() -> str:
    return str(DATABASE_PATH)
