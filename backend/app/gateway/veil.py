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
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.core.actions import canonicalize_action
from app.core.provenance import ProvenanceSource
from app.models.schemas import (
    ActionContext,
    AgentToolProposal,
    AuditEvent,
    AuthorizationRequest,
    ProposedAction,
    Provenance,
    ToolExecutionResult,
    UserPolicy,
    UserToolProposal,
)
from app.services.authorization import evaluate
from app.sim.environment import SimulatedEnvironment
from app.sim.instructions import InstructionLedger
from app.sim.resources import ResourceRegistry
from app.tools.executor import execute_tool


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
        """Trusted user channel. VEIL stamps USER provenance and approval here."""
        trusted = self._build_trusted_request(
            tool_name=proposal.tool_name,
            arguments=proposal.arguments,
            resource_id=proposal.resource_id,
            action_source=ProvenanceSource.USER,
            instruction_source=ProvenanceSource.USER,
            instruction_id=None,
            explicit_user_approval=proposal.explicit_user_approval,
            recipient=proposal.recipient,
        )
        return self._authorize_and_maybe_execute(trusted)

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
        self.events.append(
            AuditEvent(
                event_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=decision.requested_action,
                provenance=decision.provenance.value,
                resource=decision.target_resource,
                risk=decision.risk_classification.value,
                decision=decision.decision.value,
                matched_policy_rule=decision.matched_policy_rule,
                executed=executed,
                reason=decision.reason,
            )
        )
        return ToolExecutionResult(decision=decision, executed=executed)

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
