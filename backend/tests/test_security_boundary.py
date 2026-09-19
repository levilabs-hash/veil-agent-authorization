"""Security-boundary tests for provenance stamping, classification, and execution."""

import inspect
from pathlib import Path

import app.tools as tools_pkg
from app.agents.simulated_agent import SimulatedAgent
from app.api import routes as api_routes
from app.core.classification import Classification
from app.core.decisions import Decision
from app.core.provenance import ProvenanceSource
from app.gateway.veil import VeilGateway
from app.models.schemas import AgentToolProposal, UserToolProposal
from app.sim.resources import ResourceRegistry, SimulatedResource


def test_agent_cannot_forge_user_provenance():
    gateway = VeilGateway()
    agent = SimulatedAgent(gateway)
    result = agent.request_tool(
        AgentToolProposal(
            tool_name="send_email",
            resource_id="reply-draft",
            recipient="alex@example.com",
            claimed_provenance=ProvenanceSource.USER,
            claimed_explicit_user_approval=True,
            claimed_recipient_known=True,
            claimed_classification=Classification.PUBLIC,
        )
    )
    assert result.decision.provenance is ProvenanceSource.AGENT
    assert result.decision.decision is Decision.REVIEW
    assert result.executed is False
    assert gateway.execution_count() == 0


def test_confidential_resource_blocked_even_if_filename_looks_harmless():
    gateway = VeilGateway()
    resource = gateway.registry.get("harmless-notes")
    assert resource is not None
    assert resource.name == "notes.txt"
    assert resource.classification is Classification.CONFIDENTIAL
    result = gateway.submit_user(
        UserToolProposal(
            tool_name="send_email",
            resource_id="harmless-notes",
            recipient="alex@example.com",
            explicit_user_approval=True,
        )
    )
    assert result.decision.decision is Decision.BLOCK
    assert result.decision.matched_policy_rule == "send_confidential_blocked"
    assert result.decision.target_resource == "notes.txt"
    assert result.executed is False


def test_public_resource_follows_normal_policy_despite_scary_filename():
    gateway = VeilGateway()
    resource = gateway.registry.get("looks-secret")
    assert resource is not None
    assert "confidential" in resource.name.lower()
    assert resource.classification is Classification.PUBLIC
    denied = gateway.submit_agent(
        AgentToolProposal(
            tool_name="send_email",
            resource_id="looks-secret",
            recipient="alex@example.com",
        )
    )
    assert denied.decision.decision is Decision.REVIEW
    assert denied.executed is False
    allowed = gateway.resolve_review(denied.review_id, approved=True)
    assert allowed.decision.decision is Decision.ALLOW
    assert allowed.executed is True


def test_block_prevents_execution():
    gateway = VeilGateway()
    result = gateway.submit_user(
        UserToolProposal(tool_name="delete_file", resource_id="notes-txt")
    )
    assert result.decision.decision is Decision.BLOCK
    assert result.executed is False
    assert gateway.execution_count() == 0


def test_review_prevents_execution():
    gateway = VeilGateway()
    result = gateway.submit_agent(
        AgentToolProposal(
            tool_name="send_email",
            resource_id="reply-draft",
            recipient="alex@example.com",
        )
    )
    assert result.decision.decision is Decision.REVIEW
    assert result.executed is False
    assert gateway.execution_count() == 0


def test_allow_permits_execution():
    gateway = VeilGateway()
    result = gateway.submit_user(UserToolProposal(tool_name="read_email", resource_id="inbox"))
    assert result.decision.decision is Decision.ALLOW
    assert result.executed is True
    assert gateway.execution_count() == 1
    assert gateway.environment.log[0].tool_name == "read_email"


def test_every_tool_execution_path_passes_through_veil():
    agent_source = inspect.getsource(SimulatedAgent)
    assert "submit_agent" in agent_source
    assert "environment.run" not in agent_source

    route_source = inspect.getsource(api_routes)
    assert "submit_agent" in route_source
    assert "submit_user" in route_source
    assert "evaluate(request)" not in route_source

    assert not hasattr(tools_pkg, "send_email")
    assert not hasattr(tools_pkg, "delete_file")
    assert not hasattr(tools_pkg, "run")

    gateway_file = Path(inspect.getsourcefile(VeilGateway)).read_text(encoding="utf-8")
    assert "evaluate(" in gateway_file
    assert "execute_tool(" in gateway_file

    registry = ResourceRegistry(
        {
            "public-doc": SimulatedResource(
                "public-doc", "public.txt", Classification.PUBLIC
            )
        }
    )
    gateway = VeilGateway(registry=registry)
    agent = SimulatedAgent(gateway)
    result = agent.request_tool(
        AgentToolProposal(tool_name="read_email", resource_id="inbox")
    )
    # inbox is not in this custom registry; read still goes through VEIL.
    assert result.decision.matched_policy_rule
    assert result.executed is (result.decision.decision is Decision.ALLOW)


def test_agent_claimed_classification_is_ignored():
    gateway = VeilGateway()
    result = gateway.submit_agent(
        AgentToolProposal(
            tool_name="send_email",
            resource_id="harmless-notes",
            recipient="alex@example.com",
            claimed_classification=Classification.PUBLIC,
            claimed_provenance=ProvenanceSource.USER,
            claimed_explicit_user_approval=True,
        )
    )
    assert result.decision.decision is Decision.BLOCK
    assert result.decision.matched_policy_rule in {
        "untrusted_prohibited_action",
        "send_confidential_blocked",
    }
    assert result.executed is False
