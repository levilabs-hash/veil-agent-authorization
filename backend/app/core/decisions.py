"""Authorization outcomes. The engine must return exactly one of these."""

from enum import Enum


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"
