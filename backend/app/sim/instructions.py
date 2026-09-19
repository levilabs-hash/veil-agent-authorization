"""Trusted instruction ledger. VEIL assigns provenance at ingest time.

Agents cannot write USER or SYSTEM_POLICY records. They may only reference
instruction IDs that this ledger already contains.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.core.provenance import ProvenanceSource


@dataclass(frozen=True)
class InstructionRecord:
    instruction_id: str
    provenance: ProvenanceSource
    source_id: str | None
    summary: str


class InstructionLedger:
    def __init__(self) -> None:
        self._records: dict[str, InstructionRecord] = {}

    def ingest(self, provenance: ProvenanceSource, summary: str, source_id: str | None = None) -> InstructionRecord:
        record = InstructionRecord(
            instruction_id=str(uuid4()),
            provenance=provenance,
            source_id=source_id,
            summary=summary,
        )
        self._records[record.instruction_id] = record
        return record

    def get(self, instruction_id: str | None) -> InstructionRecord | None:
        if not instruction_id:
            return None
        return self._records.get(instruction_id)
