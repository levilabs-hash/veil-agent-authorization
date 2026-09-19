"""Deterministic authorization engine.

The LLM is not consulted. Rules are ordered, first match wins, and the result
is always exactly one of ALLOW, REVIEW, or BLOCK.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.core.actions import (
    ACCESS_FILE,
    DELETE_FILE,
    DRAFT_EMAIL,
    OVERRIDE_POLICY,
    PROHIBITED_FOR_UNTRUSTED,
    READ_EMAIL,
    SEND_EMAIL,
    canonicalize_action,
)
from app.core.classification import Classification
from app.core.decisions import Decision
from app.core.provenance import ProvenanceSource, can_grant_user_approval, is_untrusted
from app.core.risk import RiskClassification
from app.models.schemas import (
    ActionContext,
    AuthorizationDecision,
    AuthorizationRequest,
    Provenance,
    UserPolicy,
)

OVERRIDE_ARGUMENT_FLAGS = (
    "override_policy",
    "ignore_policy",
    "ignore_user_policy",
    "bypass_policy",
    "bypass_veil",
)


@dataclass(frozen=True)
class _Normalized:
    action: str
    resource: str | None
    provenance: ProvenanceSource
    policy: UserPolicy
    context: ActionContext
    arguments: dict
    confidential: bool
    unknown_or_high_impact_recipient: bool
    user_approved: bool
    unregistered_resource: bool


def evaluate(request: AuthorizationRequest) -> AuthorizationDecision:
    """Evaluate a proposed tool call. Never calls an LLM."""
    normalized = _normalize(request)
    for rule_id, decision, risk, matches, reason in _RULES:
        if matches(normalized):
            return AuthorizationDecision(
                decision=decision,
                reason=reason(normalized),
                matched_policy_rule=rule_id,
                provenance=normalized.provenance,
                requested_action=normalized.action,
                target_resource=normalized.resource,
                risk_classification=risk,
            )
    return AuthorizationDecision(
        decision=Decision.REVIEW,
        reason="No specific policy rule matched; defaulting to REVIEW.",
        matched_policy_rule="default_review",
        provenance=normalized.provenance,
        requested_action=normalized.action,
        target_resource=normalized.resource,
        risk_classification=RiskClassification.MEDIUM,
    )


def _normalize(request: AuthorizationRequest) -> _Normalized:
    instruction = request.instruction_provenance or request.action.provenance
    source = instruction.source
    action = canonicalize_action(request.action.tool_name)
    resource = request.action.resource
    context = request.context
    arguments = request.action.arguments or {}
    confidential = context.resource_classification is Classification.CONFIDENTIAL
    unknown = _is_unknown_or_high_impact_recipient(
        action, context, arguments, request.user_policy
    )
    claimed_approval = context.explicit_user_approval
    user_approved = bool(claimed_approval) and can_grant_user_approval(source)
    unregistered = (request.action.resource_id is not None) and not context.resource_registered
    return _Normalized(
        action=action,
        resource=resource,
        provenance=source,
        policy=request.user_policy,
        context=context,
        arguments=arguments,
        confidential=confidential,
        unknown_or_high_impact_recipient=unknown,
        user_approved=user_approved,
        unregistered_resource=unregistered,
    )


def _recipient(context: ActionContext, arguments: dict) -> str | None:
    for key in ("recipient", "to", "email"):
        value = context.recipient if key == "recipient" else arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if context.recipient and context.recipient.strip():
        return context.recipient.strip()
    return None


def _is_unknown_or_high_impact_recipient(
    action: str,
    context: ActionContext,
    arguments: dict,
    policy: UserPolicy,
) -> bool:
    if action != SEND_EMAIL:
        return False
    if context.high_impact_recipient:
        return True
    if context.recipient_known is False:
        return True
    if context.recipient_known is True:
        return False
    recipient = _recipient(context, arguments)
    if not recipient:
        return True
    trusted = {item.strip().lower() for item in policy.trusted_recipients if item.strip()}
    if not trusted:
        return True
    return recipient.lower() not in trusted


def _has_override_attempt(normalized: _Normalized) -> bool:
    if normalized.action == OVERRIDE_POLICY:
        return True
    for flag in OVERRIDE_ARGUMENT_FLAGS:
        if normalized.arguments.get(flag) is True:
            return True
    return False


def _untrusted_prohibited(normalized: _Normalized) -> bool:
    return is_untrusted(normalized.provenance) and (
        normalized.action in PROHIBITED_FOR_UNTRUSTED or normalized.confidential
    )


def _rule_untrusted_prohibited(n: _Normalized) -> str:
    return (
        "Untrusted external instruction attempted a prohibited or side-effecting "
        f"action '{n.action}'."
    )


def _rule_agent_override(n: _Normalized) -> str:
    return "Agent attempted to override or bypass the user's policy."


def _rule_delete(n: _Normalized) -> str:
    return f"Action '{n.action}' is blocked by policy."


def _rule_confidential(n: _Normalized) -> str:
    target = n.resource or "confidential resource"
    return f"Sending confidential file '{target}' is blocked."


def _rule_unknown_recipient(n: _Normalized) -> str:
    return "Recipient is unknown or high-impact; send requires review."


def _rule_send_review(n: _Normalized) -> str:
    return "Sending email requires explicit user approval."


def _rule_send_allow(n: _Normalized) -> str:
    return "User explicitly approved sending an ordinary email to a known recipient."


def _rule_read(n: _Normalized) -> str:
    return "Reading email is allowed."


def _rule_draft(n: _Normalized) -> str:
    return "Drafting email is allowed."


def _rule_access(n: _Normalized) -> str:
    return "Accessing the requested file is allowed."


# First matching rule wins. BLOCK rules are listed before REVIEW and ALLOW.
_RULES: list[
    tuple[
        str,
        Decision,
        RiskClassification,
        Callable[[_Normalized], bool],
        Callable[[_Normalized], str],
    ]
] = [
    (
        "untrusted_prohibited_action",
        Decision.BLOCK,
        RiskClassification.CRITICAL,
        _untrusted_prohibited,
        _rule_untrusted_prohibited,
    ),
    (
        "agent_policy_override",
        Decision.BLOCK,
        RiskClassification.CRITICAL,
        lambda n: n.provenance == ProvenanceSource.AGENT and _has_override_attempt(n),
        _rule_agent_override,
    ),
    (
        "policy_override_blocked",
        Decision.BLOCK,
        RiskClassification.CRITICAL,
        _has_override_attempt,
        lambda n: "Runtime policy override is not permitted.",
    ),
    (
        "unregistered_resource_blocked",
        Decision.BLOCK,
        RiskClassification.HIGH,
        lambda n: n.unregistered_resource and n.action in {SEND_EMAIL, DELETE_FILE},
        lambda n: f"Resource '{n.resource}' is not registered with a security classification.",
    ),
    (
        "delete_file_blocked",
        Decision.BLOCK,
        RiskClassification.HIGH,
        lambda n: n.action == DELETE_FILE,
        _rule_delete,
    ),
    (
        "send_confidential_blocked",
        Decision.BLOCK,
        RiskClassification.HIGH,
        lambda n: n.action == SEND_EMAIL and n.confidential,
        _rule_confidential,
    ),
    (
        "unknown_or_high_impact_recipient",
        Decision.REVIEW,
        RiskClassification.MEDIUM,
        lambda n: n.action == SEND_EMAIL and n.unknown_or_high_impact_recipient,
        _rule_unknown_recipient,
    ),
    (
        "send_email_requires_approval",
        Decision.REVIEW,
        RiskClassification.MEDIUM,
        lambda n: n.action == SEND_EMAIL
        and n.policy.send_requires_approval
        and not n.user_approved,
        _rule_send_review,
    ),
    (
        "send_email_user_approved",
        Decision.ALLOW,
        RiskClassification.LOW,
        lambda n: n.action == SEND_EMAIL and n.user_approved and not n.confidential,
        _rule_send_allow,
    ),
    (
        "read_email_allowed",
        Decision.ALLOW,
        RiskClassification.LOW,
        lambda n: n.action == READ_EMAIL,
        _rule_read,
    ),
    (
        "draft_email_allowed",
        Decision.ALLOW,
        RiskClassification.LOW,
        lambda n: n.action == DRAFT_EMAIL,
        _rule_draft,
    ),
    (
        "access_file_allowed",
        Decision.ALLOW,
        RiskClassification.LOW,
        lambda n: n.action == ACCESS_FILE,
        _rule_access,
    ),
]


def provenance(source: ProvenanceSource, source_id: str | None = None) -> Provenance:
    return Provenance(source=source, source_id=source_id)
