"""Instruction and action provenance. Required on every proposed action.

Do not trust agent-supplied provenance. VEIL stamps values in VeilGateway:
USER and approvals from submit_user / ingest_user_instruction only;
EXTERNAL_* from ingest_external_* only; AGENT on submit_agent.
"""

from enum import Enum


class ProvenanceSource(str, Enum):
    USER = "USER"
    SYSTEM_POLICY = "SYSTEM_POLICY"
    AGENT = "AGENT"
    TOOL_RESULT = "TOOL_RESULT"
    EXTERNAL_EMAIL = "EXTERNAL_EMAIL"
    EXTERNAL_WEBPAGE = "EXTERNAL_WEBPAGE"


UNTRUSTED_SOURCES = frozenset(
    {ProvenanceSource.EXTERNAL_EMAIL, ProvenanceSource.EXTERNAL_WEBPAGE}
)

TRUSTED_APPROVAL_SOURCES = frozenset(
    {ProvenanceSource.USER, ProvenanceSource.SYSTEM_POLICY}
)


def is_untrusted(source: ProvenanceSource) -> bool:
    return source in UNTRUSTED_SOURCES


def can_grant_user_approval(source: ProvenanceSource) -> bool:
    return source in TRUSTED_APPROVAL_SOURCES
