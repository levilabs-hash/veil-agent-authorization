"""Request and decision shapes for the VEIL authorization gateway."""

from pydantic import BaseModel, Field

from app.core.classification import Classification
from app.core.decisions import Decision
from app.core.provenance import ProvenanceSource
from app.core.risk import RiskClassification


class Provenance(BaseModel):
    """Where an instruction or action originated. Assigned by VEIL, not the agent."""

    source: ProvenanceSource
    source_id: str | None = None


class UserPolicy(BaseModel):
    """Structured user policy. Evaluated in code, not by an LLM."""

    trusted_recipients: list[str] = Field(default_factory=list)
    send_requires_approval: bool = True
    statement: str = (
        "Read my emails and draft replies. Sending email requires my approval. "
        "Never disclose confidential files."
    )


class ActionContext(BaseModel):
    """Resource and request context stamped by the VEIL gateway."""

    recipient: str | None = None
    recipient_known: bool | None = None
    high_impact_recipient: bool = False
    resource_classification: Classification | None = None
    resource_registered: bool = True
    explicit_user_approval: bool = False


class ProposedAction(BaseModel):
    """A tool call after VEIL has stamped trusted provenance and resource metadata."""

    tool_name: str
    arguments: dict = Field(default_factory=dict)
    resource: str | None = None
    resource_id: str | None = None
    provenance: Provenance


class AuthorizationRequest(BaseModel):
    """Trusted authorization input. Build this only from VeilGateway."""

    user_policy: UserPolicy = Field(default_factory=UserPolicy)
    user_intent: str | None = None
    action: ProposedAction
    instruction_provenance: Provenance | None = None
    context: ActionContext = Field(default_factory=ActionContext)


class AuthorizationDecision(BaseModel):
    decision: Decision
    reason: str
    matched_policy_rule: str
    provenance: ProvenanceSource
    requested_action: str
    target_resource: str | None
    risk_classification: RiskClassification


class AgentToolProposal(BaseModel):
    """Untrusted agent proposal. Provenance and classification claims are ignored."""

    tool_name: str
    arguments: dict = Field(default_factory=dict)
    resource_id: str | None = None
    instruction_id: str | None = None
    recipient: str | None = None
    claimed_provenance: ProvenanceSource | None = None
    claimed_classification: Classification | None = None
    claimed_explicit_user_approval: bool = False
    claimed_recipient_known: bool | None = None


class UserToolProposal(BaseModel):
    """Trusted operator proposal. VEIL stamps USER provenance for this channel."""

    tool_name: str
    arguments: dict = Field(default_factory=dict)
    resource_id: str | None = None
    recipient: str | None = None
    explicit_user_approval: bool = False


class ToolExecutionResult(BaseModel):
    decision: AuthorizationDecision
    executed: bool


class AuditEvent(BaseModel):
    timestamp: str
    provenance: str
    action: str
    resource: str | None
    decision: str


class DemoRunResponse(BaseModel):
    scenario: str
    instruction: str
    action: str
    recipient: str | None
    resource: str | None
    resource_classification: str | None
    provenance: ProvenanceSource
    risk: RiskClassification
    decision: Decision
    reason: str
    matched_policy_rule: str
    executed: bool
    timestamp: str
