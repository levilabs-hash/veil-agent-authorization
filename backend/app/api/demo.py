"""Demo scenario HTTP adapters. Authorization still happens only in VeilGateway."""

from __future__ import annotations

from datetime import datetime, timezone

from app.agents.veil_llm_agent import VeilLlmAgent
from app.gateway.veil import VeilGateway
from app.models.schemas import DemoRunResponse
from app.sim.llm_scenarios import (
    run_draft_llm,
    run_malicious_llm,
    run_read_llm,
    run_unapproved_send_llm,
)
from app.sim.scenarios import ScenarioTrace


def run_demo(gateway: VeilGateway, scenario: str) -> DemoRunResponse:
    agent = VeilLlmAgent.from_env(gateway)
    runners = {
        "attack": run_malicious_llm,
        "read": run_read_llm,
        "draft": run_draft_llm,
        "unapproved-send": run_unapproved_send_llm,
    }
    runner = runners.get(scenario)
    if runner is None:
        raise ValueError(f"Unknown demo scenario: {scenario}")
    trace = runner(gateway, agent)
    return _to_response(gateway, scenario, trace)


def _to_response(gateway: VeilGateway, scenario: str, trace: ScenarioTrace) -> DemoRunResponse:
    decision = trace.decision
    attachment = trace.proposal.arguments.get("attachment")
    resource = decision.target_resource
    if isinstance(attachment, str) and attachment.strip():
        resource = attachment.strip()
    classified = None
    if isinstance(attachment, str):
        found = gateway.registry.find_by_name(attachment)
        classified = found.classification.value if found else None
        resource = resource or attachment
    elif trace.proposal.resource_id:
        found = gateway.registry.get(trace.proposal.resource_id)
        classified = found.classification.value if found else None
    if classified is None and resource:
        found = gateway.registry.find_by_name(resource)
        classified = found.classification.value if found else None
    recipient = trace.proposal.recipient or trace.proposal.arguments.get("recipient")
    if not isinstance(recipient, str):
        recipient = None
    return DemoRunResponse(
        scenario=scenario,
        instruction=trace.instruction,
        action=decision.requested_action,
        recipient=recipient,
        resource=resource,
        resource_classification=classified,
        provenance=decision.provenance,
        risk=decision.risk_classification,
        decision=decision.decision,
        reason=decision.reason,
        matched_policy_rule=decision.matched_policy_rule,
        executed=trace.executed,
        timestamp=datetime.now(timezone.utc).isoformat(),
        review_id=trace.result.review_id,
    )
