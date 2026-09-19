"""LLM agent bound to VeilGateway.

The model only proposes structured actions. VEIL authorizes and may execute.
If no OpenAI API key is configured (or the API call fails), a deterministic
SimulatedAgent produces the proposal instead.
"""

from __future__ import annotations

from app.agents.openai_proposer import ActionProposer, OpenAIActionProposer, draft_from_llm_payload
from app.agents.proposal_schema import LlmActionDraft
from app.agents.simulated_agent import SimulatedAgent
from app.gateway.veil import VeilGateway
from app.models.schemas import AgentToolProposal, ToolExecutionResult


class VeilLlmAgent:
    def __init__(
        self,
        gateway: VeilGateway,
        *,
        proposer: ActionProposer | None = None,
        fallback: SimulatedAgent | None = None,
    ) -> None:
        self._gateway = gateway
        self._proposer = proposer
        self._fallback = fallback or SimulatedAgent(gateway)
        self.used_fallback = False

    @classmethod
    def from_env(cls, gateway: VeilGateway) -> VeilLlmAgent:
        return cls(gateway, proposer=OpenAIActionProposer.from_env())

    def request_tool(self, proposal: AgentToolProposal) -> ToolExecutionResult:
        return self._gateway.submit_agent(proposal)

    def handle_instruction(self, instruction_id: str, text: str) -> ToolExecutionResult:
        proposal = self.propose(instruction_id, text)
        return self._gateway.submit_agent(proposal)

    def propose(self, instruction_id: str, text: str) -> AgentToolProposal:
        draft = self._draft_action(text)
        return self._to_proposal(instruction_id, draft)

    def _draft_action(self, text: str) -> LlmActionDraft:
        if self._proposer is None:
            self.used_fallback = True
            return self._fallback_draft(text)
        try:
            draft = self._proposer.propose_action(
                policy=self._gateway.policy.statement,
                instruction=text,
            )
            self.used_fallback = False
            return draft
        except Exception:
            self.used_fallback = True
            return self._fallback_draft(text)

    def _fallback_draft(self, text: str) -> LlmActionDraft:
        proposal = self._fallback.propose(instruction_id="unused", text=text)
        return LlmActionDraft(
            tool_name=proposal.tool_name,
            arguments=dict(proposal.arguments),
            resource_id=proposal.resource_id,
            recipient=proposal.recipient,
            rationale="deterministic_fallback",
        )

    def _to_proposal(self, instruction_id: str, draft: LlmActionDraft) -> AgentToolProposal:
        sanitized = draft_from_llm_payload(draft.model_dump())
        return AgentToolProposal(
            tool_name=sanitized.tool_name,
            arguments=dict(sanitized.arguments),
            resource_id=sanitized.resource_id,
            instruction_id=instruction_id,
            recipient=sanitized.recipient,
        )
