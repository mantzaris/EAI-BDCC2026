"""Post-hoc description of off-target numerical background statements.

Primary frozen scores remain unchanged. This count asks whether a direct
off-target statement passes the existing exact checks at its own stated interval.
It is not a replacement metric or a human assessment of prose faithfulness.
"""
from collections import Counter
from pathlib import Path
from temporal_evidence.evaluation.exact import score_claims
from temporal_evidence.io import read_json, write_json, digest_file


def summarize_scope(run_id="minimum_v1"):
    counts = Counter()
    examples = {}
    episodes = {}
    details = []
    inputs = {}
    for path in sorted(Path(f"artifacts/runs/{run_id}/cases").glob("*.json")):
        output = read_json(path)
        scored_path = Path(f"artifacts/evaluation/{run_id}/cases") / path.name
        scored = read_json(scored_path)
        inputs[str(path)] = digest_file(path)
        inputs[str(scored_path)] = digest_file(scored_path)
        claims = (output["display"] or {}).get("claims", [])
        assert [claim["claim_id"] for claim in claims] == [row["claim_id"] for row in scored["claims"]]
        key = (output["case"]["dataset"], output["case"]["method"])
        for claim, result in zip(claims, scored["claims"]):
            counts[(*key, "contract_invalid")] += not result["valid"]
            if set(result["reasons"]) != {"wrong_time", "numeric_or_interval"}:
                continue
            if claim["claim_type"] != "numeric_observation" or claim["depends_on_claim_ids"]:
                continue
            episode_id = output["case"]["episode_id"]
            episode_path = Path(f"artifacts/prepared/{episode_id}.json")
            if episode_id not in episodes:
                episodes[episode_id] = read_json(episode_path)
                inputs[str(episode_path)] = digest_file(episode_path)
            events = episodes[episode_id]["variants"][output["case"]["variant"]]["events"]
            local_query = {**output["query"], **{field: claim[field] for field in
                           ("event_start_seconds", "event_end_seconds")}}
            local_result = score_claims([claim], events, local_query)[0]
            if not local_result["valid"]:
                continue
            counts[(*key, "off_target_locally_supported")] += 1
            detail = {"case_id": path.stem, "claim_id": claim["claim_id"],
                      "sentence": claim["sentence"], "contract_reasons": result["reasons"],
                      "claim_interval": [local_query["event_start_seconds"], local_query["event_end_seconds"]],
                      "query_interval": [output["query"]["event_start_seconds"], output["query"]["event_end_seconds"]]}
            details.append(detail)
            examples.setdefault(key[0], detail)
    report = {"label": "post-hoc descriptive breakdown; primary scores unchanged",
              "definition": "Direct numerical observations with only wrong_time/numeric_or_interval errors that pass the existing exact checks at their own stated interval and the original knowledge time",
              "rows": [{"dataset": source, "method": method,
                        **{name: counts[(source, method, name)] for name in
                           ("contract_invalid", "off_target_locally_supported")}}
                       for source in ("synthetic", "wesad", "ppg_dalia")
                       for method in ("B0", "B1", "B2", "M1", "B3")],
              "examples": examples, "claims": details, "inputs": inputs,
              "script_sha256": digest_file(__file__)}
    write_json(f"artifacts/analysis/{run_id}/contract_scope.json", report)
    return report


if __name__ == "__main__":
    summarize_scope()
