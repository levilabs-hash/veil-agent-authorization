"""Execute a simulated tool only after VEIL returns ALLOW.

The simulated agent must not import this module. Only VeilGateway may call
execute_tool after authorization.
"""

from app.core.decisions import Decision
from app.sim.environment import SimulatedEnvironment
from app.tools.simulated import invoke_simulated_tool


def execute_tool(
    decision: Decision,
    tool_name: str,
    environment: SimulatedEnvironment,
    arguments: dict,
    resource_id: str | None,
) -> bool:
    """Run the simulated tool only on ALLOW. BLOCK and REVIEW cannot execute."""
    if decision != Decision.ALLOW:
        return False
    invoke_simulated_tool(tool_name, environment, arguments, resource_id)
    return True


def execute_if_allowed(decision: Decision, tool_name: str) -> bool:
    """Predicate used by tests: execution is possible only for ALLOW."""
    del tool_name
    return decision == Decision.ALLOW
