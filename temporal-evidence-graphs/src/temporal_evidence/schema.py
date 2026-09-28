"""Runtime records contain observations only, never evaluator labels."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any

KINDS = {"subject", "sensor", "observation", "feature", "claim", "explanation", "review"}
RELATIONS = {"OBSERVED_BY", "FOR_SUBJECT", "DERIVED_FROM", "SUPPORTS", "CONTRADICTS",
             "DEPENDS_ON", "SUPERSEDES", "CONTAINS", "REVIEWED_BY_EVENT"}


@dataclass(frozen=True)
class Record:
    record_id: str
    logical_id: str
    record_type: str
    dataset_id: str
    subject_id: str
    session_id: str
    event_start_seconds: float
    event_end_seconds: float
    ingested_at_seconds: float
    version: int = 1
    quantity: str = ""
    value: float | None = None
    unit: str = ""
    evidence_state: str = "available"
    source_ids: tuple[str, ...] = ()
    supersedes_id: str | None = None
    support_mode: str = "AND"
    operator: str = "identity"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.record_type not in KINDS:
            raise ValueError(f"Unknown record kind {self.record_type}")
        if self.event_end_seconds < self.event_start_seconds or self.version < 1:
            raise ValueError("Invalid interval or version")
        if self.evidence_state not in {"available", "invalidated", "missing"}:
            raise ValueError("Invalid evidence state")
        if self.support_mode not in {"AND", "OR"}:
            raise ValueError("Invalid support expression")
        if self.value is not None and not isfinite(self.value):
            raise ValueError("Nonfinite values must be represented as missing")
        if self.record_id in self.source_ids:
            raise ValueError("Self dependency")
        # Tuples ensure callers cannot mutate dependency lists after creation.
        object.__setattr__(self, "source_ids", tuple(self.source_ids))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "Record":
        return cls(**value)


@dataclass(frozen=True)
class Query:
    dataset_id: str
    subject_id: str
    session_id: str
    event_start_seconds: float
    event_end_seconds: float
    knowledge_time: float
    family: str = "current_evidence"
    freshness_seconds: float | None = None
    question: str = ""


def dependency_order(records: dict[str, Record], identifiers: set[str]) -> list[str]:
    ordered, visiting, visited = [], set(), set()

    def visit(identifier):
        if identifier in visiting:
            raise ValueError("Cyclic dependency proposal")
        if identifier in visited:
            return
        visiting.add(identifier)
        if identifier in records:
            for source in records[identifier].source_ids:
                if source in identifiers:
                    visit(source)
        visiting.remove(identifier)
        visited.add(identifier)
        ordered.append(identifier)

    for identifier in sorted(identifiers):
        visit(identifier)
    return ordered
