"""Simulated tool implementations. Invoked only after VEIL ALLOW."""

from __future__ import annotations

from app.sim.environment import ExecutionRecord, SimulatedEnvironment

HANDLERS = frozenset(
    {"read_email", "draft_email", "send_email", "access_file", "delete_file"}
)


def invoke_simulated_tool(
    tool_name: str,
    environment: SimulatedEnvironment,
    arguments: dict,
    resource_id: str | None,
) -> ExecutionRecord:
    if tool_name not in HANDLERS:
        raise ValueError(f"Unknown simulated tool: {tool_name}")
    return environment.run(tool_name, arguments, resource_id)
