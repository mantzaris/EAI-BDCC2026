"""Final accounting and matched-input audit, with no outcome-based exclusions."""
from collections import Counter, defaultdict
from pathlib import Path
import json
from temporal_evidence.io import digest_object, read_json, read_journal, write_json
from temporal_evidence.study import verify_frozen


def audit_integrity():
    manifest = read_json("artifacts/manifests/minimum_run.json")
    protocol = dict(manifest)
    claimed_hash = protocol.pop("protocol_hash")
    assert digest_object(protocol) == claimed_hash
    verify_frozen(manifest)
    expected = {case["case_id"]:case for case in manifest["cases"]}
    paths = sorted(Path("artifacts/runs/minimum_v1/cases").glob("*.json"))
    assert {path.stem for path in paths} == set(expected)
    groups = defaultdict(list)
    counts = Counter()
    attempts = set()
    statuses = Counter()
    config = manifest["config"]
    allowed_payload = {"question","subject_id","target_interval","knowledge_time","evidence","previous_display"}
    for path in paths:
        output = read_json(path)
        case = output["case"]
        # Prepared-file pointers/hashes live in the manifest; verify_frozen
        # checks those files above. Every remaining case field must match exactly.
        planned = {key:value for key,value in expected[path.stem].items()
                   if key not in {"episode_path","episode_sha256"}}
        assert case == planned, (path.stem, "case metadata differs from manifest")
        payload = json.loads(output["initial"]["request"]["messages"][1]["content"])
        assert set(payload) <= allowed_payload
        assert payload["subject_id"] == case["subject"]
        assert all(record["subject_id"] == case["subject"] and record["ingested_at_seconds"] <= case["knowledge_time"]
                   for record in payload["evidence"])
        for call in (output["initial"], output["repair"]):
            if call is None:
                continue
            key = (call["case_id"], call["phase"])
            assert key not in attempts
            attempts.add(key)
            request = call["request"]
            assert request["model"] == config["model"]["name"]
            assert request["seed"] == config["generation_seed"]
            for name in ("temperature","top_p","top_k"):
                assert request[name] == config["model"][name]
            assert request["max_tokens"] == config["model"]["max_output_tokens"]
            assert request["chat_template_kwargs"] == {"enable_thinking":False}
        assert case["method"] != "B0" or output["repair"] is None
        group = (case["episode_id"],case["variant"],case["checkpoint"])
        groups[group].append((output["evidence_hash"],digest_object(output["initial"]["request"]["messages"])))
        counts[(case["dataset"],case["method"])] += 1
        statuses[output["status"]] += 1
        if output["status"] == "failed":
            assert output.get("failure_reason")
    assert len(groups) == 720
    assert all(len(rows) == 5 and len(set(rows)) == 1 for rows in groups.values())
    assert all(count == 240 for count in counts.values()) and len(counts) == 15
    journal = read_journal("artifacts/runs/minimum_v1/requests.jsonl")
    starts = Counter((row["case_id"],row["phase"]) for row in journal if row["event"] == "started")
    finishes = Counter((row["case_id"],row["phase"]) for row in journal if row["event"] == "finished")
    assert starts == finishes == Counter({key:1 for key in attempts}), "Missing or duplicate request journal events"
    result = {"passed":True,"protocol_hash":claimed_hash,"accounted_cases":len(paths),
              "matched_groups":len(groups),"matched_evidence_and_initial_prompts":True,
              "request_attempts":len(attempts),"all_requests_accounted":True,"statuses":dict(statuses),
              "source_method_counts":[{"dataset":source,"method":method,"cases":count} for (source,method),count in sorted(counts.items())],
              "scope":"Configuration, source/episode hashes, no future records in initial evidence, matched initial prompts, complete request accounting"}
    write_json("artifacts/analysis/minimum_v1/integrity.json",result)
    return result


if __name__ == "__main__":
    audit_integrity()
