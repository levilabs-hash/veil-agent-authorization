"""Simulated resource registry with explicit security classifications."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.classification import Classification


@dataclass(frozen=True)
class SimulatedResource:
    resource_id: str
    name: str
    classification: Classification
    aliases: tuple[str, ...] = field(default_factory=tuple)


def default_resources() -> dict[str, SimulatedResource]:
    items = [
        SimulatedResource("inbox", "inbox", Classification.INTERNAL),
        SimulatedResource("thread-12", "thread-12", Classification.INTERNAL),
        SimulatedResource("reply-draft", "reply-draft", Classification.INTERNAL),
        SimulatedResource("harmless-notes", "notes.txt", Classification.CONFIDENTIAL),
        SimulatedResource(
            "looks-secret",
            "q3-confidential-report.pdf",
            Classification.PUBLIC,
        ),
        SimulatedResource("q3-report", "Q3-report.pdf", Classification.CONFIDENTIAL),
        SimulatedResource("notes-txt", "notes.txt", Classification.INTERNAL),
        SimulatedResource(
            "public-doc",
            "public document",
            Classification.PUBLIC,
            aliases=("public_document.txt", "public document"),
        ),
        SimulatedResource(
            "internal-doc",
            "internal document",
            Classification.INTERNAL,
            aliases=("internal_document.txt", "internal document"),
        ),
        SimulatedResource(
            "confidential-report",
            "confidential report",
            Classification.CONFIDENTIAL,
            aliases=("confidential_report.pdf", "confidential report"),
        ),
    ]
    return {item.resource_id: item for item in items}


class ResourceRegistry:
    def __init__(self, resources: dict[str, SimulatedResource] | None = None) -> None:
        self._resources = dict(resources or default_resources())

    def get(self, resource_id: str | None) -> SimulatedResource | None:
        if not resource_id:
            return None
        return self._resources.get(resource_id)

    def find_by_name(self, label: str | None) -> SimulatedResource | None:
        if not label:
            return None
        needle = label.strip().lower()
        for resource in self._resources.values():
            names = {resource.resource_id.lower(), resource.name.lower()}
            names.update(alias.lower() for alias in resource.aliases)
            if needle in names:
                return resource
        return None
