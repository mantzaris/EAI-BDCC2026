"""Pure temporal semantics shared by the two storage implementations."""
from __future__ import annotations

from temporal_evidence.schema import Query, Record, dependency_order


def snapshot(events: list[Record], knowledge_time: float) -> dict[str, Record]:
    visible = {}
    for event in events:
        if event.ingested_at_seconds <= knowledge_time:
            if event.record_id in visible and visible[event.record_id] != event:
                raise ValueError("Conflicting duplicate event")
            visible[event.record_id] = event
    return visible


def current_versions(records: dict[str, Record]) -> dict[str, Record]:
    result = {}
    for record in records.values():
        old = result.get(record.logical_id)
        if old is None or (record.version, record.ingested_at_seconds, record.record_id) > (
                old.version, old.ingested_at_seconds, old.record_id):
            result[record.logical_id] = record
    return result


def admissible_evidence(events: list[Record], query: Query) -> list[Record]:
    current = current_versions(snapshot(events, query.knowledge_time))
    return sorted([record for record in current.values()
                   if record.record_type == "feature"
                   and (record.dataset_id, record.subject_id, record.session_id) ==
                   (query.dataset_id, query.subject_id, query.session_id)
                   and record.event_end_seconds <= query.event_end_seconds
                   and record.event_start_seconds >= query.event_start_seconds - 120
                   and (query.freshness_seconds is None or
                        query.event_end_seconds - record.event_end_seconds <= query.freshness_seconds)],
                  key=lambda record: record.record_id)


def resolve(record_id: str, records: dict[str, Record], current: dict[str, Record]) -> Record | None:
    record = records.get(record_id)
    return None if record is None else current.get(record.logical_id)


def support_state(identifier: str, records: dict[str, Record], memo=None, active=None) -> tuple[str, float | None]:
    """Re-evaluate DAG semantics; OR operands are checked individually."""
    memo = {} if memo is None else memo
    active = set() if active is None else active
    if identifier in memo:
        return memo[identifier]
    if identifier in active:
        return "needs_review", None
    active.add(identifier)
    current = current_versions(records)
    record = resolve(identifier, records, current)
    if record is None or record.evidence_state != "available":
        answer = ("unsupported", None)
    elif record.record_type == "claim" and "claim" in record.metadata:
        # Generated claims use the same published predicate at later knowledge times.
        # The independent evaluator never calls this runtime implementation.
        from dataclasses import replace
        from temporal_evidence.generation.contract import Answer
        from temporal_evidence.validation.checker import validate
        dependencies = record.metadata.get("claim_dependency_records", [])
        dependency_states = [support_state(source, records, memo, active)[0] for source in dependencies]
        proposal = dict(record.metadata["claim"])
        proposal["depends_on_claim_ids"] = []
        proposal["evidence_ids"] = [resolved.record_id if (resolved := resolve(source, records, current)) is not None else source
                                    for source in proposal["evidence_ids"]]
        query = Query(**record.metadata["query"])
        query = replace(query,knowledge_time=max(r.ingested_at_seconds for r in records.values()))
        response = Answer.model_validate({"claims":[proposal],"answer_status":"answered",
            "explanation":proposal["sentence"],"unresolved_evidence_ids":[]})
        decisions,_ = validate(response,records,query)
        if any(state != "supported" for state in dependency_states):
            answer = ("unsupported",record.value)
        elif decisions[0].state == "supported":
            answer = ("supported",record.value)
        else:
            contradicted = any(reason in {"wrong_numeric_value_or_interval","wrong_difference","evidence_is_available"}
                               for reason in decisions[0].reasons)
            answer = ("contradicted" if contradicted else "unsupported",record.value)
    elif not record.source_ids:
        answer = ("supported", record.value)
    else:
        operands = [support_state(source, records, memo, active) for source in record.source_ids]
        usable = [value for state, value in operands if state == "supported"]
        satisfied = len(usable) > 0 if record.support_mode == "OR" else len(usable) == len(operands)
        if not satisfied:
            answer = ("unsupported", None)
        elif record.operator == "difference":
            if len(usable) == 2 and None not in usable:
                difference = usable[0] - usable[1]
                if record.record_type == "claim":
                    correct = record.value is not None and abs(record.value-difference)<=max(1e-6,.01*abs(difference))
                    answer = ("supported" if correct else "contradicted",record.value)
                else:
                    answer = ("supported",difference)
            else:
                answer = ("unsupported",None)
        elif record.operator == "missing" and record.record_type == "claim":
            answer = ("supported" if all(value == 0 for value in usable) else "contradicted",None)
        elif record.record_type == "claim" and record.value is not None:
            tolerance = max(1e-6, 0.01 * abs(record.value))
            matches = [value is not None and abs(record.value - value) <= tolerance for value in usable]
            valid = any(matches) if record.support_mode == "OR" else all(matches)
            answer = ("supported" if valid else "contradicted", record.value)
        elif record.operator == "identity" and record.record_type == "feature":
            answer = ("supported", usable[0])
        else:
            answer = ("supported", record.value)
    active.remove(identifier)
    memo[identifier] = answer
    return answer


def apply_revision(store, revision: Record, method: str) -> dict:
    """Append a revision, then append assessments for exactly the enabled reach."""
    import time
    started = time.perf_counter()
    store.put(revision)
    if method == "B0" or revision.supersedes_id is None:
        return {"affected": [], "assessments": {}, "seconds": time.perf_counter() - started}
    transitive = method in {"M1", "B3"}
    records = store.snapshot(revision.ingested_at_seconds)
    # Citations remain immutable across multiple revisions. Revisit dependencies
    # on every earlier version, including claims that still cite v1 after v2.
    predecessors=[r.record_id for r in records.values() if r.logical_id==revision.logical_id
                  and r.version<revision.version]
    affected=set().union(*(store.dependents(identifier,revision.ingested_at_seconds,transitive)
                          for identifier in predecessors))
    assessments = {}
    for identifier in dependency_order(records, set(affected)):
        if records[identifier].record_type in {"claim", "explanation", "feature"}:
            state, value = support_state(identifier, records)
            store.assess(identifier, revision.ingested_at_seconds, state, value, revision.record_id)
            assessments[identifier] = {"state": state, "value": value}
    return {"affected": sorted(affected), "assessments": assessments,
            "seconds": time.perf_counter() - started}
