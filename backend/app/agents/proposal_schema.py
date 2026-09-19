"""Untrusted LLM action draft. Not an authorization decision."""

from pydantic import BaseModel, Field


class LlmActionDraft(BaseModel):
    """Structured tool proposal produced by an LLM or fallback parser.

    Extra fields such as provenance, decision, or approval are ignored when
    converting this into an AgentToolProposal.
    """

    tool_name: str
    arguments: dict = Field(default_factory=dict)
    resource_id: str | None = None
    recipient: str | None = None
    rationale: str | None = None
