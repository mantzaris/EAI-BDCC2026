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


def with_entities(records):
    result={r.record_id:r for r in records}
    for record in list(result.values()):
        if record.record_type in {"subject","sensor"}:
            continue
        subject_id=f"{record.dataset_id}/{record.subject_id}/subject"
        common=dict(dataset_id=record.dataset_id,subject_id=record.subject_id,session_id=record.session_id,
                    event_start_seconds=0,event_end_seconds=0,ingested_at_seconds=0)
        result.setdefault(subject_id,Record(record_id=subject_id,logical_id=subject_id,record_type="subject",**common))
        if record.record_type=="observation" and "channel" in record.metadata:
            sensor_id=f"{record.dataset_id}/{record.subject_id}/{record.session_id}/{record.metadata['channel']}/sensor"
            result.setdefault(sensor_id,Record(record_id=sensor_id,logical_id=sensor_id,record_type="sensor",**common,
                              metadata={"channel":record.metadata["channel"]}))
    return list(result.values())


def record_relations(record):
    edges=[(record.record_id,source,"DEPENDS_ON") for source in record.source_ids]
    if record.supersedes_id:
        edges.append((record.record_id,record.supersedes_id,"SUPERSEDES"))
    if record.record_type!="subject":
        edges.append((record.record_id,f"{record.dataset_id}/{record.subject_id}/subject","FOR_SUBJECT"))
    if record.record_type=="observation" and "channel" in record.metadata:
        sensor=f"{record.dataset_id}/{record.subject_id}/{record.session_id}/{record.metadata['channel']}/sensor"
        edges.append((record.record_id,sensor,"OBSERVED_BY"))
    if record.record_type=="feature":
        edges.extend((record.record_id,source,"DERIVED_FROM") for source in record.source_ids)
    if record.record_type=="claim" and record.metadata.get("accepted"):
        edges.extend((source,record.record_id,"SUPPORTS") for source in record.source_ids)
    if record.record_type=="explanation":
        edges.extend((record.record_id,source,"CONTAINS") for source in record.source_ids)
    if record.record_type=="review":
        edges.extend((source,record.record_id,"REVIEWED_BY_EVENT") for source in record.source_ids)
    return edges
