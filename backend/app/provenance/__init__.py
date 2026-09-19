"""Instruction and action provenance. Required on every proposed action.

VEIL assigns provenance. Agent-supplied provenance values are not trusted.
See app.gateway.veil.VeilGateway for the stamp points.
"""

from app.core.provenance import (
    ProvenanceSource,
    can_grant_user_approval,
    is_untrusted,
)

__all__ = [
    "ProvenanceSource",
    "can_grant_user_approval",
    "is_untrusted",
]
