"""Risk labels attached to every authorization decision."""

from enum import Enum


class RiskClassification(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
