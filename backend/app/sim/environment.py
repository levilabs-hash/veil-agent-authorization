"""In-memory simulated environment. No real external actions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionRecord:
    tool_name: str
    resource_id: str | None
    arguments: dict


@dataclass
class SimulatedEnvironment:
    log: list[ExecutionRecord] = field(default_factory=list)
    sent_emails: list[ExecutionRecord] = field(default_factory=list)

    def run(self, tool_name: str, arguments: dict, resource_id: str | None) -> ExecutionRecord:
        record = ExecutionRecord(
            tool_name=tool_name,
            resource_id=resource_id,
            arguments=dict(arguments),
        )
        self.log.append(record)
        if tool_name == "send_email":
            self.sent_emails.append(record)
        return record

    def tool_executed(self, tool_name: str) -> bool:
        return any(item.tool_name == tool_name for item in self.log)
