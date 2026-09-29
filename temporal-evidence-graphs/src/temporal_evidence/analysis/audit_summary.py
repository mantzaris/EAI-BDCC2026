"""Describe every auxiliary annotation and disagreement without adjudicating it."""
from collections import Counter, defaultdict
from pathlib import Path
from temporal_evidence.io import read_json, write_json, digest_file


def summarize_audit(run_id="minimum_v1"):
    directory = Path(f"artifacts/audit/{run_id}")
    selection_path = directory / "selection.json"
    selection = read_json(selection_path)
    groups = defaultdict(list)
    disagreements = []
    inputs = [selection_path, directory / "summary.json"]
    confusion = Counter()
    for selected in selection["selected"]:
        path = directory / f"{selected['case_id']}.json"
        row = read_json(path)
        assert row["sha256"] == selected["sha256"] == digest_file(selected["path"])
        assert row["phase"] == "test_audit"
        annotation = row["parsed"]
        exact = row["exact_all_supported"]
        verdict = annotation["faithful"] if annotation is not None else None
        confusion[(exact, verdict)] += 1
        item = {"case_id": row["case_id"], "exact_all_claims_supported": exact,
                "automated_faithful": verdict, "annotation_path": str(path)}
        groups[(row["dataset"], row["method"])].append(item)
        if verdict is not None and verdict != exact:
            disagreements.append({**item, "automated_discrepancies": annotation["discrepancies"],
                                  "automated_rationale": annotation.get("rationale")})
        inputs.append(path)
    assert len(groups) == 15 and all(len(rows) == 4 for rows in groups.values())
    rows = []
    for (dataset, method), items in sorted(groups.items()):
        rows.append({"dataset": dataset, "method": method, "sampled": len(items),
                     "parsed": sum(r["automated_faithful"] is not None for r in items),
                     "flagged": sum(r["automated_faithful"] is False for r in items),
                     "exact_all_claims_supported": sum(r["exact_all_claims_supported"] for r in items),
                     "disagreements": sum(r["automated_faithful"] is not None and
                                          r["automated_faithful"] != r["exact_all_claims_supported"] for r in items)})
    result = {"selection_scope": selection["selection_scope"], "strata": rows,
              "cross_tabulation": [{"exact_all_claims_supported": key[0], "automated_faithful": key[1], "count": value}
                                   for key, value in confusion.items()],
              "disagreements": disagreements,
              "interpretation": "Neither agreement nor disagreement establishes a human gold label. Exact checks implement the numerical contract; the auxiliary model can also make errors.",
              "inputs": {str(path): digest_file(path) for path in inputs}, "script_sha256": digest_file(__file__)}
    write_json(f"artifacts/analysis/{run_id}/audit_details.json", result)
    return result


if __name__ == "__main__":
    summarize_audit()
