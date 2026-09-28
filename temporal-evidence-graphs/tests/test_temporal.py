from dataclasses import replace
import pytest

from temporal_evidence.schema import Query, dependency_order
from temporal_evidence.synthetic.fixtures import record, correction_fixture
from temporal_evidence.replay.temporal import snapshot, current_versions, admissible_evidence, support_state, apply_revision
from temporal_evidence.storage.relational import RelationalStore


def test_no_future_and_historical_versions():
    records, revision = correction_fixture()
    known = snapshot(records + [revision], 15)
    assert "a/v2" not in known
    assert current_versions(known)["a"].value == 2
    assert current_versions(snapshot(records + [revision], 20))["a"].value == 4
    assert support_state("downstream_claim", known)[0] == "supported"


@pytest.mark.parametrize("method,propagates", [("B0", False), ("B1", False), ("B2", False), ("M1", True), ("B3", True)])
def test_transitive_correction_and_alternative_support(method, propagates):
    store = RelationalStore()
    records, revision = correction_fixture()
    store.put_many(records)
    result = apply_revision(store, revision, method)
    assert ("downstream_claim" in result["assessments"]) == propagates
    if propagates:
        assert result["assessments"]["downstream_claim"]["state"] == "contradicted"
        assert result["assessments"]["difference"]["value"] == 3
        assert result["assessments"]["or_claim"]["state"] == "supported"
        assert "unaffected" not in result["affected"]
        assert result["assessments"]["explanation"]["state"] == "unsupported"


def test_or_support_survives_invalidation():
    records, revision = correction_fixture()
    revision = replace(revision, evidence_state="invalidated", value=None)
    known = snapshot(records + [revision], 20)
    assert support_state("or_claim", known)[0] == "supported"
    assert support_state("direct_claim", known)[0] == "unsupported"


def test_benign_revision_retains_claims():
    records, revision = correction_fixture()
    revision = replace(revision, value=2)
    known = snapshot(records + [revision], 20)
    assert support_state("explanation", known)[0] == "supported"


def test_out_of_order_duplicate_and_conflicting_revision():
    store = RelationalStore()
    records, revision = correction_fixture()
    store.put_many([revision] + records)
    store.put(revision)
    assert len([r for r in store.snapshot(20).values() if r.record_type!="subject"]) == len(records) + 1
    assert "a/v2" not in store.snapshot(19)
    with pytest.raises(ValueError, match="Immutable"):
        store.put(replace(revision, value=100))


def test_cycle_is_rejected_atomically():
    store = RelationalStore()
    with pytest.raises(ValueError, match="Cyclic"):
        store.put_many([record("x", sources=("y",)), record("y", sources=("x",))])
    assert store.snapshot(100) == {}


def test_future_intermediate_cannot_bridge_revision_traversal():
    store = RelationalStore()
    store.put_many([record("a", 1), record("future", 1, ("a",), time=50),
                    record("leaf", 1, ("future",), kind="claim")])
    assert store.dependents("a", 20) == set()


def test_current_freshness_does_not_invalidate_history():
    events = [record("old", 1)]
    query = Query("synthetic", "V101", "symbolic", 0, 100, 100, freshness_seconds=30)
    assert admissible_evidence(events, query) == []
    assert len(admissible_evidence(events, replace(query, event_end_seconds=10, knowledge_time=10))) == 1


def test_wrong_subject_is_not_runtime_evidence():
    events = [record("a", 1), replace(record("b", 2), subject_id="other")]
    query = Query("synthetic", "V101", "symbolic", 0, 10, 10)
    assert [r.record_id for r in admissible_evidence(events, query)] == ["a"]
