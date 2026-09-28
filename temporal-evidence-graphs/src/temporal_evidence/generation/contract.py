from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    claim_type: Literal["numeric_observation", "trend", "comparison", "evidence_conflict", "missing_evidence", "revision_effect"]
    subject_id: str
    quantity: str
    event_start_seconds: float
    event_end_seconds: float
    operator: Literal["approximately_equal", "difference", "greater_than", "less_than", "missing", "disagrees", "remains_supported", "revised"]
    value: float | None
    unit: str
    evidence_ids: list[str]
    depends_on_claim_ids: list[str]
    sentence: str


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[Claim] = Field(max_length=6)
    answer_status: Literal["answered", "partially_answered", "insufficient_evidence"]
    explanation: str
    unresolved_evidence_ids: list[str]
