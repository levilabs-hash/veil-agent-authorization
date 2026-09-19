"""Gateway routes. Proposed tool calls enter VEIL before any simulated execution."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.demo import run_demo
from app.api.operator import require_demo_operator
from app.core.decisions import Decision
from app.gateway.veil import VeilGateway
from app.models.schemas import (
    AgentToolProposal,
    AuditEvent,
    DemoRunResponse,
    ReviewResolveRequest,
    ReviewSummary,
    ToolExecutionResult,
    UserToolProposal,
)

router = APIRouter()
gateway = VeilGateway()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "veil"}


@router.get("/decisions")
def decisions() -> dict[str, list[str]]:
    return {"decisions": [d.value for d in Decision]}


@router.get("/console")
def console_state() -> dict:
    return {
        "status": "ok",
        "protection": "PROTECTION ACTIVE",
        "policy_statement": gateway.policy.statement,
        "events": [event.model_dump() for event in gateway.events[-30:]],
    }


@router.get("/events", response_model=list[AuditEvent])
def events() -> list[AuditEvent]:
    return gateway.events[-30:]


@router.post("/demo/{scenario}", response_model=DemoRunResponse)
def demo(scenario: str) -> DemoRunResponse:
    try:
        return run_demo(gateway, scenario)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/agent/tools", response_model=ToolExecutionResult)
def agent_tools(proposal: AgentToolProposal) -> ToolExecutionResult:
    """Untrusted agent path. VEIL stamps AGENT provenance and ignores claims."""
    return gateway.submit_agent(proposal)


@router.post("/user/tools", response_model=ToolExecutionResult)
def user_tools(proposal: UserToolProposal) -> ToolExecutionResult:
    """Trusted user path. Stamps USER provenance. Cannot approve sends by arguments."""
    return gateway.submit_user(proposal)


@router.get("/reviews", response_model=list[ReviewSummary])
def reviews() -> list[ReviewSummary]:
    """Pending reviews. The console displays these; it does not authorize them."""
    return gateway.pending_reviews()


@router.post("/user/reviews/{review_id}/resolve", response_model=ToolExecutionResult)
def resolve_review(
    review_id: str,
    body: ReviewResolveRequest,
    _: None = Depends(require_demo_operator),
) -> ToolExecutionResult:
    """Operator-gated close-loop. Credential is checked before VEIL re-authorizes."""
    return gateway.resolve_review(review_id, approved=body.approved)
