"""Demo-operator credential check. Not a production identity system.

The token never enters the authorization engine or audit records.
"""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from app.core.config import operator_token


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return value.strip()


def require_demo_operator(authorization: str | None = Header(default=None)) -> None:
    expected = operator_token()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Operator approval is not configured.",
        )
    presented = _bearer_token(authorization)
    if not presented or len(presented) != len(expected):
        raise HTTPException(status_code=401, detail="Operator authorization failed.")
    if not hmac.compare_digest(presented, expected):
        raise HTTPException(status_code=401, detail="Operator authorization failed.")
