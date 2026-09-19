"""Gate 4 demo: LLM (or fallback) proposes; VEIL authorizes."""

from __future__ import annotations

from app.agents.veil_llm_agent import VeilLlmAgent
from app.core.provenance import ProvenanceSource
from app.gateway.veil import VeilGateway
from app.sim.scenarios import (
    DRAFT_INSTRUCTION,
    MALICIOUS_EMAIL,
    READ_INSTRUCTION,
    ScenarioTrace,
    UNAPPROVED_SEND_INSTRUCTION,
)


def run_with_llm_agent(
    *,
    name: str,
    text: str,
    ingest: str,
    gateway: VeilGateway | None = None,
    agent: VeilLlmAgent | None = None,
) -> ScenarioTrace:
    gateway = gateway or VeilGateway()
    agent = agent or VeilLlmAgent.from_env(gateway)
    if ingest == "external":
        instruction_id = gateway.ingest_external_email(text, source_id="attacker@example.com")
        provenance = ProvenanceSource.EXTERNAL_EMAIL
    else:
        instruction_id = gateway.ingest_user_instruction(text, source_id="user")
        provenance = ProvenanceSource.USER
    proposal = agent.propose(instruction_id, text)
    result = agent.request_tool(proposal)
    return ScenarioTrace(
        name=name,
        policy=gateway.policy.statement,
        instruction=text,
        instruction_id=instruction_id,
        instruction_provenance=provenance,
        proposal=proposal,
        result=result,
    )


def run_malicious_llm(gateway: VeilGateway | None = None, agent: VeilLlmAgent | None = None) -> ScenarioTrace:
    return run_with_llm_agent(
        name="llm_malicious_external_email",
        text=MALICIOUS_EMAIL,
        ingest="external",
        gateway=gateway,
        agent=agent,
    )


def run_read_llm(gateway: VeilGateway | None = None, agent: VeilLlmAgent | None = None) -> ScenarioTrace:
    return run_with_llm_agent(
        name="llm_read_email",
        text=READ_INSTRUCTION,
        ingest="user",
        gateway=gateway,
        agent=agent,
    )


def run_draft_llm(gateway: VeilGateway | None = None, agent: VeilLlmAgent | None = None) -> ScenarioTrace:
    return run_with_llm_agent(
        name="llm_draft_email",
        text=DRAFT_INSTRUCTION,
        ingest="user",
        gateway=gateway,
        agent=agent,
    )


def run_unapproved_send_llm(
    gateway: VeilGateway | None = None, agent: VeilLlmAgent | None = None
) -> ScenarioTrace:
    return run_with_llm_agent(
        name="llm_unapproved_send",
        text=UNAPPROVED_SEND_INSTRUCTION,
        ingest="user",
        gateway=gateway,
        agent=agent,
    )


def main() -> None:
    gateway = VeilGateway()
    agent = VeilLlmAgent.from_env(gateway)
    mode = "openai" if agent._proposer is not None else "deterministic_fallback"
    print(f"PROPOSER: {mode}\n")
    for runner in (run_malicious_llm, run_read_llm, run_draft_llm, run_unapproved_send_llm):
        print(runner(gateway=VeilGateway(), agent=VeilLlmAgent.from_env(VeilGateway())).render())


if __name__ == "__main__":
    main()
