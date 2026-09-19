"""End-to-end Gate 3 path: untrusted instruction → agent → VEIL → gated tools."""

import inspect

from app.agents.simulated_agent import SimulatedAgent
from app.core.decisions import Decision
from app.core.provenance import ProvenanceSource
from app.gateway.veil import VeilGateway
from app.sim.scenarios import (
    MALICIOUS_EMAIL,
    run_draft_reply,
    run_malicious_external_email,
    run_read_email,
    run_unapproved_send,
)
from app.tools import executor as executor_mod


def test_malicious_external_instruction_block_no_execution():
    gateway = VeilGateway()
    trace = run_malicious_external_email(gateway)
    decision = trace.decision
    assert trace.proposal.tool_name == "send_email"
    assert trace.proposal.arguments["recipient"] == "attacker@example.com"
    assert trace.proposal.arguments["attachment"] == "confidential_report.pdf"
    assert decision.decision is Decision.BLOCK
    assert decision.requested_action == "send_email"
    assert decision.matched_policy_rule == "untrusted_prohibited_action"
    assert decision.provenance is ProvenanceSource.EXTERNAL_EMAIL
    assert decision.target_resource == "confidential report"
    assert decision.risk_classification.value == "CRITICAL"
    assert decision.reason
    assert trace.executed is False
    assert gateway.execution_count() == 0
    assert gateway.environment.sent_emails == []
    assert not gateway.environment.tool_executed("send_email")


def test_confidential_exfiltration_block_no_execution():
    gateway = VeilGateway()
    agent = SimulatedAgent(gateway)
    instruction_id = gateway.ingest_external_email(
        MALICIOUS_EMAIL, source_id="attacker@example.com"
    )
    result = agent.handle_instruction(instruction_id, MALICIOUS_EMAIL)
    assert result.decision.decision is Decision.BLOCK
    assert result.decision.target_resource == "confidential report"
    assert result.executed is False
    assert "send_email" not in [item.tool_name for item in gateway.environment.log]


def test_normal_read_allow_executes():
    gateway = VeilGateway()
    trace = run_read_email(gateway)
    assert trace.proposal.tool_name == "read_email"
    assert trace.decision.decision is Decision.ALLOW
    assert trace.decision.matched_policy_rule == "read_email_allowed"
    assert trace.executed is True
    assert gateway.environment.tool_executed("read_email")
    assert gateway.environment.log[0].tool_name == "read_email"


def test_draft_reply_allow_executes():
    gateway = VeilGateway()
    trace = run_draft_reply(gateway)
    assert trace.proposal.tool_name == "draft_email"
    assert trace.decision.decision is Decision.ALLOW
    assert trace.decision.matched_policy_rule == "draft_email_allowed"
    assert trace.executed is True
    assert gateway.environment.tool_executed("draft_email")


def test_unapproved_send_review_no_execution():
    gateway = VeilGateway()
    trace = run_unapproved_send(gateway)
    assert trace.proposal.tool_name == "send_email"
    assert trace.decision.decision is Decision.REVIEW
    assert trace.decision.matched_policy_rule in {
        "send_email_requires_approval",
        "unknown_or_high_impact_recipient",
    }
    assert trace.executed is False
    assert not gateway.environment.tool_executed("send_email")
    assert gateway.environment.sent_emails == []


def test_agent_has_no_direct_execution_path():
    source = inspect.getsource(SimulatedAgent)
    assert "submit_agent" in source
    assert "execute_tool" not in source
    assert "execute_if_allowed" not in source
    assert "environment.run" not in source
    assert "invoke_simulated_tool" not in source
    assert inspect.getsource(executor_mod.execute_tool)
    gateway_source = inspect.getsource(VeilGateway)
    assert "execute_tool(" in gateway_source
    assert "evaluate(" in gateway_source
