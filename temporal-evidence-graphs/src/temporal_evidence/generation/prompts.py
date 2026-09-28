"""Identical prompts across conditions; only admissible records are serialized."""
from temporal_evidence.io import canonical

SYSTEM = """You describe recorded physiological signal features, not diagnoses or causes.
Use only supplied evidence from the requested subject and interval. A feature's value
describes the available recording, not hidden physiological truth. Motion alone does
not prove failure or stress. Invalidated or missing values cannot support a number.
Return JSON matching the supplied schema, with at most 3 concise claims. Never invent
IDs. Include explicit evidence_ids for numbers; claim dependencies must point only to
earlier claims in this response. Do not refer to invisible updates or reference labels.
For numeric_observation use approximately_equal; for trend/comparison use difference
(target minus earlier baseline) and cite both operands; for missing_evidence use
missing and value null. Describe uncertainty when appropriate. Each sentence must
include its stated numeric value and unit, without additional interpretations.
The explanation must be exactly the claim sentences joined by single spaces.
Use partially_answered or insufficient_evidence when required information is absent.
"""


def messages(query, evidence, previous=None):
    # A strict allowlist prevents source file metadata or hidden annotations escaping.
    records = [{key: record.to_dict()[key] for key in (
        "record_id", "subject_id", "event_start_seconds", "event_end_seconds", "ingested_at_seconds",
        "quantity", "value", "unit", "evidence_state", "version", "supersedes_id")}
        for record in evidence]
    payload = {"question": query.question, "subject_id": query.subject_id,
               "target_interval": [query.event_start_seconds, query.event_end_seconds],
               "knowledge_time": query.knowledge_time, "evidence": records}
    if previous is not None:
        payload["previous_display"] = previous
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": canonical(payload)}]
