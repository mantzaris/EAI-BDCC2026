"""Deterministic checks; free text receives limited lexical checks plus later audit."""
from __future__ import annotations

import re
from dataclasses import dataclass
from temporal_evidence.generation.contract import Answer
from temporal_evidence.replay.temporal import current_versions


def close(value, reference):
    return value is not None and reference is not None and abs(value-reference) <= max(1e-6, .01*abs(reference))


@dataclass
class Decision:
    claim_id: str
    state: str
    reasons: list[str]

    def to_dict(self):
        return {"claim_id": self.claim_id, "state": self.state, "reasons": self.reasons}


def validate(answer: Answer, records: dict, query) -> tuple[list[Decision], list[str]]:
    current = current_versions(records)
    decisions, accepted = [], {}
    seen = set()
    for claim in answer.claims:
        errors = []
        if claim.claim_id in seen:
            errors.append("duplicate_claim_id")
        seen.add(claim.claim_id)
        if claim.subject_id != query.subject_id:
            errors.append("wrong_subject")
        if (claim.event_start_seconds, claim.event_end_seconds) != (query.event_start_seconds, query.event_end_seconds):
            errors.append("wrong_time")
        evidence = []
        for identifier in claim.evidence_ids:
            record = records.get(identifier)
            if record is None or record.ingested_at_seconds > query.knowledge_time:
                errors.append("missing_reference")
                continue
            if (record.dataset_id, record.subject_id, record.session_id) != (query.dataset_id, query.subject_id, query.session_id):
                errors.append("wrong_reference_scope")
            if current[record.logical_id].record_id != record.record_id:
                errors.append("superseded_reference")
            if record.record_type != "feature":
                errors.append("reference_not_feature")
            evidence.append(record)
        if any(dependency not in accepted or accepted[dependency] != "supported" for dependency in claim.depends_on_claim_ids):
            errors.append("unsupported_or_cyclic_dependency")
        if claim.claim_type == "missing_evidence":
            if claim.value is not None or claim.operator != "missing":
                errors.append("invalid_missing_semantics")
            matching = [r for r in current.values() if r.quantity == claim.quantity
                        and r.subject_id == query.subject_id and r.dataset_id == query.dataset_id
                        and r.session_id == query.session_id
                        and (r.event_start_seconds,r.event_end_seconds) == (query.event_start_seconds,query.event_end_seconds)]
            if any(r.evidence_state == "available" and r.value is not None for r in matching):
                errors.append("evidence_is_available")
        elif claim.claim_type in {"numeric_observation", "trend", "comparison", "evidence_conflict", "revision_effect"}:
            if not evidence:
                errors.append("no_support")
            if any(r.evidence_state != "available" or r.value is None for r in evidence):
                errors.append("unavailable_evidence")
            if any(r.unit != claim.unit or r.quantity != claim.quantity for r in evidence):
                errors.append("wrong_quantity_or_unit")
            if claim.claim_type in {"numeric_observation", "revision_effect"}:
                if not any(close(claim.value, r.value) and (r.event_start_seconds,r.event_end_seconds) ==
                           (claim.event_start_seconds,claim.event_end_seconds) for r in evidence):
                    errors.append("wrong_numeric_value_or_interval")
                if claim.claim_type == "revision_effect" and not any(r.supersedes_id for r in evidence):
                    errors.append("no_observable_revision")
            else:
                target = [r for r in evidence if (r.event_start_seconds,r.event_end_seconds) ==
                          (query.event_start_seconds,query.event_end_seconds)]
                prior = [r for r in evidence if r.event_end_seconds == query.event_start_seconds
                         and r.event_start_seconds == query.event_start_seconds-120]
                if claim.claim_type == "evidence_conflict":
                    comparable = [r for r in target if r.value is not None]
                    if len(comparable) < 2 or close(comparable[0].value, comparable[1].value):
                        errors.append("no_measurable_conflict")
                elif not target or not prior or target[0].value is None or prior[0].value is None:
                    errors.append("missing_comparison_operand")
                elif not close(claim.value, target[0].value-prior[0].value):
                    errors.append("wrong_difference")
        if re.search(r"\b(caus(?:e|es|ed|al)|diagnos\w*|stress(?:ed)?|readiness|disease)\b", claim.sentence, re.I):
            errors.append("unsupported_interpretation")
        if claim.value is not None:
            numbers = [float(x) for x in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", claim.sentence)]
            if not any(close(number, claim.value) for number in numbers):
                errors.append("sentence_numeric_discrepancy")
            if claim.unit and claim.unit.lower() not in claim.sentence.lower():
                errors.append("sentence_unit_unverified")
        decision = Decision(claim.claim_id, "supported" if not errors else "needs_review", sorted(set(errors)))
        decisions.append(decision)
        accepted[claim.claim_id] = decision.state
    paragraph_errors = []
    if answer.explanation.strip() != " ".join(claim.sentence for claim in answer.claims).strip():
        paragraph_errors.append("explanation_not_equal_to_claim_sentences")
    return decisions, paragraph_errors


def safe_display(answer: Answer, decisions: list[Decision]) -> dict:
    accepted = {d.claim_id for d in decisions if d.state == "supported"}
    claims = [c.model_dump() for c in answer.claims if c.claim_id in accepted]
    return {"claims": claims, "answer_status": "insufficient_evidence" if not claims else
            (answer.answer_status if len(claims) == len(answer.claims) else "partially_answered"),
            "explanation": " ".join(c["sentence"] for c in claims),
            "unresolved_evidence_ids": answer.unresolved_evidence_ids}
