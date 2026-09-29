"""Append-only review actions and explanation history, outside the experiment.

The default local store uses the same full dependency semantics as M1/B3. An
optional Neo4j store uses a dedicated review/ scope and never experiment scopes.
No review action launches model inference or edits a saved benchmark output.
"""
from dataclasses import replace
from pathlib import Path
import json
import math
from temporal_evidence.io import digest_object, read_json, utc_now
from temporal_evidence.schema import Record, Query
from temporal_evidence.storage.relational import RelationalStore
from temporal_evidence.synthetic.fixtures import correction_fixture
from temporal_evidence.replay.temporal import apply_revision, current_versions, support_state


def sentence(record):
    return record.metadata.get("claim", {}).get("sentence", record.metadata.get("sentence", record.record_id))


class ReviewWorkspace:
    def __init__(self, identifier="symbolic", path=".local/review.sqlite", backend="sqlite", uri="bolt://127.0.0.1:7687"):
        self.identifier = identifier
        self.scope = "review/" + identifier
        if backend == "neo4j":
            from temporal_evidence.storage.graph import GraphStore
            self.store = GraphStore(uri=uri, scope=self.scope)
        elif backend == "sqlite":
            if path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.store = RelationalStore(path, scope=self.scope)
        else:
            raise ValueError("Unknown review backend")

    def seed_symbolic(self):
        if self.store._records:
            return
        records, _ = correction_fixture()
        statements = {
            "direct_claim": "The target EDA median is 2 synthetic_unit.",
            "downstream_claim": "Target minus earlier EDA median is 1 synthetic_unit.",
            "or_claim": "At least one independent source supports 2 synthetic_unit.",
            "unaffected": "The earlier EDA median is 1 synthetic_unit.",
        }
        records = [replace(r, metadata={**r.metadata, "sentence": statements[r.record_id]})
                   if r.record_id in statements else r for r in records]
        self.store.put_many(records)
        self._recompose(10.0001, initial=True)

    def seed_case(self, path):
        if self.store._records:
            return
        from temporal_evidence.experiment import displayed_records
        output = read_json(path)
        if output["case"]["method"] == "B0":
            raise ValueError("Review imports checked outputs; raw B0 proposals remain available in diagnostics")
        episode_id = output["case"]["episode_id"]
        archived = path.parent.parent/"input_episodes"/f"{episode_id}.json"
        episode = read_json(archived if archived.exists() else f"artifacts/prepared/{episode_id}.json")
        events = episode["variants"][output["case"]["variant"]]["events"]
        query = Query(**output["query"])
        self.store.put_many(Record.from_dict(r) for r in events if r["ingested_at_seconds"] <= query.knowledge_time)
        self.store.put_many(displayed_records(output["display"], output["case"], query, self.store))

    def records(self):
        return self.store.snapshot(float("inf"))

    def latest(self):
        return current_versions(self.records())

    def states(self):
        records = self.records()
        return {r.record_id: ("needs_review" if r.metadata.get("review_unresolved")
                             else support_state(r.record_id, records)[0])
                for r in current_versions(records).values() if r.record_type == "claim"}

    def queue(self):
        records = self.records()
        latest = current_versions(records)
        states = self.states()
        rows = []
        for record in latest.values():
            if record.record_type not in {"claim", "feature"}:
                continue
            state = states.get(record.record_id, record.evidence_state)
            roots = [r.record_id for r in records.values() if r.logical_id == record.logical_id]
            impact = self.store.dependents_many(roots, float("inf"), True)
            claims = {records[key].logical_id for key in impact if records[key].record_type == "claim"}
            rows.append({"record_id": record.record_id, "kind": record.record_type,
                         "statement": sentence(record) if record.record_type == "claim" else record.quantity,
                         "state": state, "affected_claims": len(claims),
                         "explicit_problem": state in {"contradicted", "unsupported", "needs_review", "invalidated", "missing"}})
        return sorted(rows, key=lambda r: (-r["explicit_problem"], -r["affected_claims"], r["record_id"]))

    def history(self):
        return sorted((r for r in self.records().values() if r.record_type == "explanation" and "display" in r.metadata),
                      key=lambda r: (r.ingested_at_seconds, r.version, r.record_id))

    def _recompose(self, known_at, initial=False):
        records = self.records()
        latest = current_versions(records)
        states = self.states()
        changes = []
        # Preserve the original membership so restored support can restore text.
        roots = [r for r in records.values() if r.record_type == "explanation" and r.version == 1]
        for root in roots:
            previous = latest[root.logical_id]
            members = [latest[records[identifier].logical_id] for identifier in root.source_ids if identifier in records]
            kept = [r for r in members if states.get(r.record_id) == "supported"]
            display = {"explanation": " ".join(sentence(r) for r in kept),
                       "claims": [{"record_id": r.record_id, "sentence": sentence(r)} for r in kept],
                       "retained": len(kept), "total": len(members)}
            old_text = previous.metadata.get("display", {}).get("explanation")
            if old_text == display["explanation"] and not initial:
                continue
            version = previous.version + 1
            changes.append(replace(previous, record_id=f"{root.logical_id}/review/v{version}",
                                   version=version, ingested_at_seconds=known_at, supersedes_id=previous.record_id,
                                   source_ids=tuple(r.record_id for r in kept),
                                   metadata={"display": display, "review_workspace": self.scope,
                                             "maintenance_action": "retain_currently_supported_sentences"}))
        if changes:
            self.store.put_many(changes)
        return changes

    def act(self, action, record_id, rationale, value=None, actor="interactive_unverified_identity"):
        if not rationale.strip():
            raise ValueError("Add a reason for the review action")
        records = self.records()
        if record_id not in records:
            raise ValueError("Unknown review target")
        previous = current_versions(records)[records[record_id].logical_id]
        known_at = max(r.ingested_at_seconds for r in records.values()) + 1
        changes = {}
        if action == "reject_evidence" and previous.record_type == "feature":
            changes = {"evidence_state": "invalidated"}
        elif action == "accept_correction" and previous.record_type == "feature":
            if value is None or not math.isfinite(value):
                raise ValueError("A finite corrected value is required")
            changes = {"value": float(value), "evidence_state": "available"}
        elif action == "mark_unresolved" and previous.record_type == "claim":
            changes = {"evidence_state": "invalidated", "metadata": {**previous.metadata, "review_unresolved": True}}
        else:
            raise ValueError("This action does not apply to the selected item")
        before = self.history()
        before_text = before[-1].metadata["display"]["explanation"] if before else ""
        version = previous.version + 1
        revised = replace(previous, record_id=f"{previous.logical_id}/review/v{version}", version=version,
                          ingested_at_seconds=known_at, supersedes_id=previous.record_id, **changes)
        result = apply_revision(self.store, revised, "M1")
        explanations = self._recompose(known_at + .0001)
        event_id = "review-event/" + digest_object([self.scope, revised.record_id, action, rationale])[:20]
        event = Record(record_id=event_id, logical_id=event_id, record_type="review",
                       dataset_id=previous.dataset_id, subject_id=previous.subject_id, session_id=previous.session_id,
                       event_start_seconds=previous.event_start_seconds, event_end_seconds=previous.event_end_seconds,
                       ingested_at_seconds=known_at + .0002, source_ids=(previous.record_id, revised.record_id),
                       metadata={"action": action, "rationale": rationale, "actor": actor, "wall_time": utc_now(),
                                 "before": before_text,
                                 "after": self.history()[-1].metadata["display"]["explanation"] if self.history() else "",
                                 "changed_explanation_ids": [r.record_id for r in explanations],
                                 "affected_ids": result["affected"]})
        self.store.put(event)
        return event.to_dict()

    def neighborhood_dot(self, center, hops=2):
        records = self.records()
        latest = current_versions(records)
        selected = {center}
        edges = []
        for record in latest.values():
            if record.record_type in {"review", "subject", "sensor"}:
                continue
            for identifier in record.source_ids:
                if identifier in records:
                    target = latest[records[identifier].logical_id].record_id
                    edges.append((record.record_id, target))
        for _ in range(hops):
            neighbors = {target for source, target in edges if source in selected}
            neighbors |= {source for source, target in edges if target in selected}
            selected |= neighbors
        states = self.states()
        lines = ['digraph { rankdir=TB; nodesep=0.25; ranksep=0.4; node [shape=box,style="rounded,filled",fontname="Arial",fontsize=12]; edge [fontname="Arial",fontsize=10];']
        for identifier in sorted(selected):
            if identifier not in records:
                continue
            record = records[identifier]
            state = states.get(identifier, record.evidence_state)
            short_id = record.logical_id.rsplit("/", 1)[-1].replace("_", " ")
            if len(short_id) > 28:
                short_id = short_id[:25] + "…"
            label = f"{record.record_type.title()}: {short_id}\nv{record.version} · {state}"
            if record.value is not None:
                label += f"\n{record.value:.6g} {record.unit}"
            color = "#fae1db" if state in {"invalidated", "unsupported", "contradicted", "needs_review"} else "#e3f1ed"
            lines.append(f"{json.dumps(identifier)} [label={json.dumps(label,ensure_ascii=False)},fillcolor={json.dumps(color)},penwidth={2.5 if identifier == center else 1},tooltip={json.dumps(sentence(record),ensure_ascii=False)}];")
        for source, target in edges:
            if source in selected and target in selected:
                label = records[source].support_mode if records[source].record_type == "claim" else "requires"
                lines.append(f"{json.dumps(source)} -> {json.dumps(target)} [label={json.dumps(label)}];")
        return "\n".join(lines + ["}"])

    def close(self):
        self.store.close()
