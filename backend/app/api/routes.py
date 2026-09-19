"""Gateway routes. Proposed tool calls enter VEIL before any simulated execution."""

from fastapi import APIRouter, HTTPException

from app.api.demo import run_demo
from app.core.decisions import Decision
from app.gateway.veil import VeilGateway
from app.models.schemas import (
    AgentToolProposal,
    AuditEvent,
    DemoRunResponse,
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
    """Trusted user path. VEIL stamps USER provenance for this channel only."""
    return gateway.submit_user(proposal)
