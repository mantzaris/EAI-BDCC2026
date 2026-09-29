"""Identical prompts across conditions; only admissible records are serialized."""
from temporal_evidence.io import canonical

SYSTEM = """You describe recorded physiological signal features, not diagnoses or causes.
Use only supplied evidence from the requested subject and interval. A feature's value
describes the available recording, not hidden physiological truth. Motion alone does
not prove failure or stress. Invalidated or missing values cannot support a number.
Return JSON matching the supplied schema, with at most 3 concise claims. Never invent
IDs. Include explicit evidence_ids for numbers; claim dependencies must point only to
earlier claims in this response. Do not refer to invisible updates or reference labels.
The top-level JSON object has exactly four required keys, in this order: claims,
answer_status, explanation, unresolved_evidence_ids. After closing the claims array,
write the remaining three keys. answer_status is answered, partially_answered, or
insufficient_evidence; explanation is a string; unresolved_evidence_ids is an array
of unavailable evidence IDs, or []. Each claim has all of these fields: claim_id,
claim_type, subject_id, quantity, event_start_seconds, event_end_seconds, operator,
value, unit, evidence_ids, depends_on_claim_ids, sentence. Never pad with whitespace.
For numeric_observation use approximately_equal; for trend/comparison use difference
(target minus earlier baseline) and cite both operands; for missing_evidence use
missing and value null. Describe uncertainty when appropriate. Each sentence must
include its stated numeric value and unit, without additional interpretations.
The explanation must be exactly the claim sentences joined by single spaces.
Keep every claim's event_start_seconds and event_end_seconds equal to the requested
target interval, including comparisons whose earlier operand covers another interval.
Report only requested facts; the baseline is an operand, not an additional claim.
Use one short sentence per claim and compact JSON. Round reported numbers to six
significant digits. A revision_effect claim uses revised for an explicitly revised
feature; an unchanged feature can be reported as an ordinary numeric_observation.
depends_on_claim_ids contains only claim_id values of earlier claims, never evidence IDs.
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
