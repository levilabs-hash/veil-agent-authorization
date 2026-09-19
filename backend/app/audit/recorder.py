"""Write an audit record for every ALLOW / REVIEW / BLOCK decision."""

from app.core.decisions import Decision


def record_decision(decision: Decision, reason: str, details: dict | None = None) -> None:
    """Persist an audit record. SQLite writer will be implemented later."""
    del decision, reason, details
