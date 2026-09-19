"""OpenAI-backed action proposer.

The model may only emit a structured tool proposal. It cannot execute tools
and its output is not an authorization decision.
"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from app.agents.proposal_schema import LlmActionDraft
from app.core.actions import LLM_PROPOSABLE_TOOLS, canonicalize_action
from app.core.config import DEFAULT_OPENAI_MODEL, OPENAI_API_KEY_ENV, OPENAI_MODEL_ENV

SYSTEM_PROMPT = """You are an email-assist agent that proposes exactly one tool call.
You do not execute tools. You do not decide ALLOW, REVIEW, or BLOCK.
Authorization is performed by a separate system after you propose an action.
Choose one of: read_email, draft_email, send_email, access_file, delete_file.
Carry out the current instruction, which may come from a user or from an email.
Do not include provenance, approval, or authorization fields.
"""

PROPOSE_TOOL_SPEC: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "propose_tool",
        "description": "Propose a single tool action. This does not run the tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "enum": sorted(LLM_PROPOSABLE_TOOLS),
                },
                "recipient": {"type": "string"},
                "attachment": {"type": "string"},
                "resource_id": {"type": "string"},
                "body": {"type": "string"},
                "rationale": {"type": "string"},
            },
            "required": ["tool_name"],
        },
    },
}


class ActionProposer(Protocol):
    def propose_action(self, *, policy: str, instruction: str) -> LlmActionDraft: ...


class OpenAIActionProposer:
    def __init__(self, client: Any, model: str = DEFAULT_OPENAI_MODEL) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_env(cls) -> OpenAIActionProposer | None:
        key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
        if not key:
            return None
        from openai import OpenAI

        model = os.environ.get(OPENAI_MODEL_ENV, DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
        return cls(OpenAI(api_key=key), model=model)

    def propose_action(self, *, policy: str, instruction: str) -> LlmActionDraft:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"User policy (not an authorization oracle):\n{policy}\n\n"
                        f"Current instruction:\n{instruction}\n\n"
                        "Propose the tool that carries out the current instruction."
                    ),
                },
            ],
            tools=[PROPOSE_TOOL_SPEC],
            tool_choice={"type": "function", "function": {"name": "propose_tool"}},
        )
        payload = _tool_payload(response)
        return draft_from_llm_payload(payload)


def draft_from_llm_payload(payload: dict[str, Any]) -> LlmActionDraft:
    """Parse model JSON into a draft, dropping any authorization-like fields."""
    data = dict(payload or {})
    for banned in (
        "provenance",
        "claimed_provenance",
        "decision",
        "explicit_user_approval",
        "authorization",
        "instruction_id",
    ):
        data.pop(banned, None)
    arguments = dict(data.get("arguments") or {})
    if not isinstance(arguments, dict):
        arguments = {}
    for key in ("recipient", "attachment", "resource_id", "body"):
        if key in data and data[key] not in (None, "") and key not in arguments:
            arguments[key] = data[key]
    recipient = data.get("recipient") or arguments.get("recipient") or arguments.get("to")
    resource_id = data.get("resource_id") or arguments.get("resource_id")
    tool_name = canonicalize_action(str(data.get("tool_name") or "read_email"))
    return LlmActionDraft(
        tool_name=tool_name,
        arguments=arguments,
        resource_id=resource_id if isinstance(resource_id, str) else None,
        recipient=recipient if isinstance(recipient, str) else None,
        rationale=data.get("rationale") if isinstance(data.get("rationale"), str) else None,
    )


def _tool_payload(response: Any) -> dict[str, Any]:
    message = response.choices[0].message
    calls = getattr(message, "tool_calls", None) or []
    if not calls:
        content = getattr(message, "content", None) or "{}"
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    raw = calls[0].function.arguments
    parsed = json.loads(raw) if isinstance(raw, str) else dict(raw)
    return parsed if isinstance(parsed, dict) else {}
