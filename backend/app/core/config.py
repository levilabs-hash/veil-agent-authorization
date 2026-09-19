"""Application configuration. Secrets come from the environment, never source."""

from __future__ import annotations

import os

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPERATOR_TOKEN_ENV = "VEIL_OPERATOR_TOKEN"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

_LOCAL_FRONTEND_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def cors_allow_origins() -> list[str]:
    origins: list[str] = []
    extra = os.environ.get("VEIL_CORS_ORIGINS", "")
    for item in (*_LOCAL_FRONTEND_ORIGINS, *extra.split(",")):
        cleaned = item.strip().rstrip("/")
        if cleaned and cleaned not in origins:
            origins.append(cleaned)
    return origins


def cors_allow_origin_regex() -> str | None:
    value = os.environ.get("VEIL_CORS_ORIGIN_REGEX", "").strip()
    return value or None


def operator_token() -> str:
    """Demo-operator secret. Empty means approval is unavailable (fail closed)."""
    return os.environ.get(OPERATOR_TOKEN_ENV, "").strip()
