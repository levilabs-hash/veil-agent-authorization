"""VEIL gateway: the only trusted path from a proposed tool call to execution.

Trusted provenance originates here, not from agent-supplied fields.

Origins VEIL will stamp:
- USER: `submit_user` and `ingest_user_instruction` only
- SYSTEM_POLICY: `ingest_system_instruction` only
- EXTERNAL_EMAIL: `ingest_external_email` only
- EXTERNAL_WEBPAGE: `ingest_external_webpage` only
- AGENT: every `submit_agent` action; also the instruction provenance when
  the agent did not reference a VEIL-issued instruction id
- TOOL_RESULT: `ingest_tool_result` only

Agent-supplied claimed_provenance, claimed classification, claimed
recipient_known, and claimed user approval are discarded.
Review approval is only `resolve_review` on this gateway (trusted user channel).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.core.actions import canonicalize_action
from app.core.decisions import Decision
from app.core.provenance import ProvenanceSource
from app.core.risk import RiskClassification
from app.models.schemas import (
    ActionContext,
    AgentToolProposal,
    AuditEvent,
    AuthorizationDecision,
    AuthorizationRequest,
    ProposedAction,
    Provenance,
    ReviewSummary,
    ToolExecutionResult,
    UserPolicy,
    UserToolProposal,
)
from app.services.authorization import evaluate
from app.sim.environment import SimulatedEnvironment
from app.sim.instructions import InstructionLedger
from app.sim.resources import ResourceRegistry
from app.tools.executor import execute_tool


@dataclass
class _PendingReview:
    review_id: str
    tool_name: str
    arguments: dict
    resource_id: str | None
    recipient: str | None
    action_source: ProvenanceSource
    instruction_source: ProvenanceSource
    instruction_id: str | None
    original_reason: str
    status: str = "pending"


class VeilGateway:
    def __init__(
        self,
        *,
        policy: UserPolicy | None = None,
        registry: ResourceRegistry | None = None,
        ledger: InstructionLedger | None = None,
        environment: SimulatedEnvironment | None = None,
    ) -> None:
        self.policy = policy or UserPolicy(trusted_recipients=["alex@example.com"])
        self.registry = registry or ResourceRegistry()
        self.ledger = ledger or InstructionLedger()
        self.environment = environment or SimulatedEnvironment()
        self.events: list[AuditEvent] = []
        self._reviews: dict[str, _PendingReview] = {}

    def ingest_user_instruction(self, summary: str, source_id: str | None = None) -> str:
        return self.ledger.ingest(ProvenanceSource.USER, summary, source_id).instruction_id

    def ingest_system_instruction(self, summary: str) -> str:
        return self.ledger.ingest(ProvenanceSource.SYSTEM_POLICY, summary).instruction_id

    def ingest_external_email(self, summary: str, source_id: str | None = None) -> str:
        return self.ledger.ingest(
            ProvenanceSource.EXTERNAL_EMAIL, summary, source_id
        ).instruction_id

    def ingest_external_webpage(self, summary: str, source_id: str | None = None) -> str:
        return self.ledger.ingest(
            ProvenanceSource.EXTERNAL_WEBPAGE, summary, source_id
        ).instruction_id

    def ingest_tool_result(self, summary: str, source_id: str | None = None) -> str:
        return self.ledger.ingest(ProvenanceSource.TOOL_RESULT, summary, source_id).instruction_id

    def submit_agent(self, proposal: AgentToolProposal) -> ToolExecutionResult:
        """Agent channel. Action provenance is always AGENT. Claims are ignored."""
        instruction = self.ledger.get(proposal.instruction_id)
        instruction_source = (
            instruction.provenance if instruction else ProvenanceSource.AGENT
        )
        trusted = self._build_trusted_request(
            tool_name=proposal.tool_name,
            arguments=proposal.arguments,
            resource_id=proposal.resource_id,
            action_source=ProvenanceSource.AGENT,
            instruction_source=instruction_source,
            instruction_id=instruction.instruction_id if instruction else None,
            explicit_user_approval=False,
            recipient=proposal.recipient,
        )
        return self._authorize_and_maybe_execute(trusted)

    def submit_user(self, proposal: UserToolProposal) -> ToolExecutionResult:
        """Trusted user channel. VEIL stamps USER provenance here.

        `explicit_user_approval` on the proposal is ignored. Side-effecting
        actions that need approval must go through `resolve_review` with a
        pending review ID; this path cannot construct an approved send from
        arguments.
        """
        trusted = self._build_trusted_request(
            tool_name=proposal.tool_name,
            arguments=proposal.arguments,
            resource_id=proposal.resource_id,
            action_source=ProvenanceSource.USER,
            instruction_source=ProvenanceSource.USER,
            instruction_id=None,
            explicit_user_approval=False,
            recipient=proposal.recipient,
        )
        return self._authorize_and_maybe_execute(trusted)

    def resolve_review(self, review_id: str, *, approved: bool) -> ToolExecutionResult:
        """Trusted-user close-loop. Re-evaluates stored context; never takes new tool args."""
        pending = self._reviews.get((review_id or "").strip())
        if pending is None or pending.status != "pending":
            return self._invalid_resolution(review_id)
        if not approved:
            pending.status = "rejected"
            self._set_event_review_status(pending.review_id, "rejected")
            decision = AuthorizationDecision(
                decision=Decision.REVIEW,
                reason="Trusted user rejected the pending review. The tool was not executed.",
                matched_policy_rule="review_rejected",
                provenance=pending.instruction_source,
                requested_action=canonicalize_action(pending.tool_name),
                target_resource=self._display_resource(pending.resource_id),
                risk_classification=RiskClassification.MEDIUM,
            )
            return self._append_result(
                decision,
                executed=False,
                related_event_id=pending.review_id,
                review_status="rejected",
                approval_source=ProvenanceSource.USER,
                review_id=pending.review_id,
            )
        pending.status = "approved"
        self._set_event_review_status(pending.review_id, "approved")
        trusted = self._build_trusted_request(
            tool_name=pending.tool_name,
            arguments=pending.arguments,
            resource_id=pending.resource_id,
            action_source=pending.action_source,
            instruction_source=pending.instruction_source,
            instruction_id=pending.instruction_id,
            explicit_user_approval=True,
            recipient=pending.recipient,
            trusted_approval_source=ProvenanceSource.USER,
        )
        decision = evaluate(trusted)
        executed = execute_tool(
            decision.decision,
            canonicalize_action(trusted.action.tool_name),
            self.environment,
            trusted.action.arguments,
            trusted.action.resource_id,
        )
        return self._append_result(
            decision,
            executed=executed,
            related_event_id=pending.review_id,
            review_status="approved",
            approval_source=ProvenanceSource.USER,
            review_id=pending.review_id,
        )

    def pending_reviews(self) -> list[ReviewSummary]:
        summaries: list[ReviewSummary] = []
        for pending in self._reviews.values():
            if pending.status != "pending":
                continue
            summaries.append(
                ReviewSummary(
                    review_id=pending.review_id,
                    action=canonicalize_action(pending.tool_name),
                    resource=self._display_resource(pending.resource_id),
                    recipient=pending.recipient,
                    provenance=pending.instruction_source.value,
                    status=pending.status,
                    reason=pending.original_reason,
                )
            )
        return summaries

    def _build_trusted_request(
        self,
        *,
        tool_name: str,
        arguments: dict,
        resource_id: str | None,
        action_source: ProvenanceSource,
        instruction_source: ProvenanceSource,
        instruction_id: str | None,
        explicit_user_approval: bool,
        recipient: str | None,
        trusted_approval_source: ProvenanceSource | None = None,
    ) -> AuthorizationRequest:
        args = dict(arguments or {})
        rid = self._resolve_resource_id(resource_id, args)
        recipient_value = recipient or _arg_recipient(args)
        resource = self.registry.get(rid)
        registered = rid is None or resource is not None
        classification = resource.classification if resource else None
        display_name = resource.name if resource else rid
        known = self._recipient_is_known(recipient_value)
        return AuthorizationRequest(
            user_policy=self.policy,
            action=ProposedAction(
                tool_name=tool_name,
                arguments=args,
                resource=display_name,
                resource_id=rid,
                provenance=Provenance(source=action_source, source_id=instruction_id),
            ),
            instruction_provenance=Provenance(
                source=instruction_source, source_id=instruction_id
            ),
            context=ActionContext(
                recipient=recipient_value,
                recipient_known=None if recipient_value is None else known,
                high_impact_recipient=False,
                resource_classification=classification,
                resource_registered=registered,
                explicit_user_approval=explicit_user_approval,
                trusted_approval_source=trusted_approval_source,
            ),
        )

    def _recipient_is_known(self, recipient: str | None) -> bool:
        if not recipient:
            return False
        trusted = {item.strip().lower() for item in self.policy.trusted_recipients if item.strip()}
        return recipient.strip().lower() in trusted

    def _authorize_and_maybe_execute(
        self, request: AuthorizationRequest
    ) -> ToolExecutionResult:
        decision = evaluate(request)
        executed = execute_tool(
            decision.decision,
            canonicalize_action(request.action.tool_name),
            self.environment,
            request.action.arguments,
            request.action.resource_id,
        )
        event_id = str(uuid4())
        review_id = None
        review_status = None
        if decision.decision is Decision.REVIEW:
            review_id = event_id
            review_status = "pending"
            self._reviews[event_id] = _PendingReview(
                review_id=event_id,
                tool_name=request.action.tool_name,
                arguments=dict(request.action.arguments or {}),
                resource_id=request.action.resource_id,
                recipient=request.context.recipient,
                action_source=request.action.provenance.source,
                instruction_source=(
                    request.instruction_provenance.source
                    if request.instruction_provenance
                    else request.action.provenance.source
                ),
                instruction_id=(
                    request.instruction_provenance.source_id
                    if request.instruction_provenance
                    else request.action.provenance.source_id
                ),
                original_reason=decision.reason,
            )
        return self._append_result(
            decision,
            executed=executed,
            event_id=event_id,
            review_id=review_id,
            review_status=review_status,
        )

    def _invalid_resolution(self, review_id: str) -> ToolExecutionResult:
        decision = AuthorizationDecision(
            decision=Decision.BLOCK,
            reason="Review ID is missing, malformed, already resolved, or not pending.",
            matched_policy_rule="review_resolution_invalid",
            provenance=ProvenanceSource.USER,
            requested_action="resolve_review",
            target_resource=None,
            risk_classification=RiskClassification.MEDIUM,
        )
        return self._append_result(
            decision,
            executed=False,
            related_event_id=(review_id or "").strip() or None,
            review_status="invalid",
            approval_source=ProvenanceSource.USER,
        )

    def _append_result(
        self,
        decision: AuthorizationDecision,
        *,
        executed: bool,
        event_id: str | None = None,
        related_event_id: str | None = None,
        review_status: str | None = None,
        approval_source: ProvenanceSource | None = None,
        review_id: str | None = None,
    ) -> ToolExecutionResult:
        event = AuditEvent(
            event_id=event_id or str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=decision.requested_action,
            provenance=decision.provenance.value,
            resource=decision.target_resource,
            risk=decision.risk_classification.value,
            decision=decision.decision.value,
            matched_policy_rule=decision.matched_policy_rule,
            executed=executed,
            reason=decision.reason,
            related_event_id=related_event_id,
            review_status=review_status,
            approval_source=approval_source.value if approval_source else None,
        )
        self.events.append(event)
        return ToolExecutionResult(
            decision=decision,
            executed=executed,
            review_id=review_id,
            related_event_id=related_event_id,
        )

    def _set_event_review_status(self, review_id: str, status: str) -> None:
        for event in self.events:
            if event.event_id == review_id:
                event.review_status = status
                return

    def _display_resource(self, resource_id: str | None) -> str | None:
        resource = self.registry.get(resource_id)
        if resource:
            return resource.name
        return resource_id

    def execution_count(self) -> int:
        return len(self.environment.log)

    def _resolve_resource_id(self, resource_id: str | None, arguments: dict) -> str | None:
        candidates = [
            resource_id,
            arguments.get("resource_id"),
            arguments.get("file_id"),
            arguments.get("attachment"),
            arguments.get("filename"),
        ]
        for raw in candidates:
            if not isinstance(raw, str) or not raw.strip():
                continue
            value = raw.strip()
            by_id = self.registry.get(value)
            if by_id:
                return by_id.resource_id
            by_name = self.registry.find_by_name(value)
            if by_name:
                return by_name.resource_id
        return None


def _arg_recipient(arguments: dict) -> str | None:
    for key in ("recipient", "to", "email"):
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
