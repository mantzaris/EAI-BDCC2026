"""Save scripted interface examples; these are not human review observations."""
from temporal_evidence.dashboard.review import ReviewWorkspace
from temporal_evidence.io import write_json, digest_file

cases = [
    ("correction", "accept_correction", "a", 4.0, "Correct the target value; retract dependent old statements"),
    ("alternative_support", "reject_evidence", "a", None, "Invalidate one source while retaining independent OR support"),
    ("review_limitation", "reject_evidence", "b", None, "Deliberately mistaken rejection demonstrates that review actions can remove valid information"),
]
manifest = []
for identifier, action, target, value, reason in cases:
    workspace = ReviewWorkspace(identifier, path=":memory:")
    workspace.seed_symbolic()
    before = {"states": workspace.states(), "explanation": workspace.history()[-1].to_dict()}
    event = workspace.act(action, target, reason, value, actor="automated_demonstration")
    result = {"label": "scripted interface demonstration, not human annotation or a user study",
              "example": identifier, "before": before, "review_event": event,
              "after": {"states": workspace.states(), "explanation": workspace.history()[-1].to_dict()},
              "history": [r.to_dict() for r in workspace.history()],
              "records": [r.to_dict() for r in workspace.records().values()]}
    path = f"artifacts/review_examples/{identifier}.json"
    write_json(path, result)
    manifest.append({"path": path, "sha256": digest_file(path), "purpose": reason})
    workspace.close()
write_json("artifacts/review_examples/manifest.json", {"examples": manifest, "script": "scripts/make_review_examples.py"})
