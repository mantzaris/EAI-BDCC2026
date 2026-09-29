from pathlib import Path
from temporal_evidence.dashboard.review import ReviewWorkspace
from temporal_evidence.io import digest_file


def test_review_correction_preserves_alternative_and_restores_immutable_history(tmp_path):
    workspace = ReviewWorkspace(path=str(tmp_path/"review.sqlite"))
    workspace.seed_symbolic()
    before = workspace.history()[-1].to_dict()
    first = workspace.act("accept_correction", "a", "Scripted correction example", 4, actor="automated_demo")
    assert workspace.states()["direct_claim"] == "contradicted"
    assert workspace.states()["downstream_claim"] == "contradicted"
    assert workspace.states()["or_claim"] == "supported"
    assert workspace.states()["unaffected"] == "supported"
    graph = workspace.neighborhood_dot("a/review/v2")
    assert "3 synthetic_unit" in graph and "Recorded value: 1" in graph
    assert "target EDA median is 2" not in first["metadata"]["after"]
    assert "independent source supports 2" in first["metadata"]["after"]
    workspace.act("accept_correction", "a", "Restore original evidence", 2, actor="automated_demo")
    assert all(state == "supported" for state in workspace.states().values())
    assert workspace.history()[-1].metadata["display"]["explanation"] == before["metadata"]["display"]["explanation"]
    assert workspace.store.get(before["record_id"]).to_dict() == before
    assert len([r for r in workspace.records().values() if r.record_type == "review"]) == 2
    workspace.close()


def test_review_unresolved_retracts_only_selected_interpretation(tmp_path):
    workspace = ReviewWorkspace(path=str(tmp_path/"review.sqlite"))
    workspace.seed_symbolic()
    workspace.act("mark_unresolved", "or_claim", "Alternative source requires review", actor="automated_demo")
    states = workspace.states()
    assert "needs_review" in states.values()
    assert states["direct_claim"] == states["downstream_claim"] == states["unaffected"] == "supported"
    assert "independent source" not in workspace.history()[-1].metadata["display"]["explanation"]
    workspace.close()


def test_review_import_never_changes_saved_case(tmp_path):
    candidates = sorted(Path("artifacts/runs/pilot_v3/cases").glob("*-M1.json"))
    assert candidates
    path = candidates[0]
    original = digest_file(path)
    workspace = ReviewWorkspace("import-test", path=str(tmp_path/"review.sqlite"))
    workspace.seed_case(path)
    feature = next(r for r in workspace.latest().values() if r.record_type == "feature" and r.quantity == "eda_median")
    workspace.act("reject_evidence", feature.record_id, "Scripted isolated review", actor="automated_demo")
    assert digest_file(path) == original
    assert workspace.scope.startswith("review/")
    workspace.close()
