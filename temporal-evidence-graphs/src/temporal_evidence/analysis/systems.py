"""Descriptive systems reporting, including completion-time staleness.

This module does not change the frozen benchmark or its request-snapshot scores.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime
import json
import numpy as np
from temporal_evidence.io import read_json, read_jsonl, read_journal, write_json, digest_file
from temporal_evidence.evaluation.exact import score_claims, required_slots, agrees


def completion_adequacy(row, rate):
    """Reconstruct the separately specified two-operand symbolic workload."""
    payload = json.loads(row["result"]["initial"]["request"]["messages"][1]["content"])
    evidence = [{**record, "logical_id": "a" if record["record_id"].startswith("a/") else "b",
                 "record_type": "feature", "dataset_id": "synthetic", "session_id": "symbolic"}
                for record in payload["evidence"]]
    target = next(record for record in evidence if record["logical_id"] == "a")
    last_index = row["completed_after_event_index"]
    current_value = 4.0 if ((last_index+10)//20) % 2 else 2.0
    current = {**target, "record_id": f"a/v{last_index+1}", "version": last_index+1,
               "supersedes_id": f"a/v{last_index}", "value": current_value,
               "ingested_at_seconds": 100+last_index/rate}
    query = {"dataset_id": "synthetic", "session_id": "symbolic", "subject_id": payload["subject_id"],
             "event_start_seconds": payload["target_interval"][0], "event_end_seconds": payload["target_interval"][1],
             "knowledge_time": 100+last_index/rate, "family": "current_evidence"}
    events = evidence + ([current] if last_index != row["index"] else [])
    claims = (row["result"]["display"] or {}).get("claims", [])
    exact = score_claims(claims, events, query, remap_versions=True)
    slots = required_slots(events, query)
    adequate = all(any(score["valid"] and claim["quantity"] == slot["quantity"]
                       and agrees(claim["value"], slot["value"])
                       and claim["claim_type"] in (("comparison", "trend") if slot["kind"] == "difference"
                                                  else ("numeric_observation", "revision_effect"))
                       for claim, score in zip(claims, exact)) for slot in slots)
    return {"adequate_at_completion": adequate, "intervening_events": last_index-row["index"],
            "target_value_changed": not agrees(target["value"], current_value),
            "request_target_value": target["value"], "completion_target_value": current_value}


def analyze_streaming(run_id="streaming_v1"):
    directory = Path(f"artifacts/streaming/{run_id}")
    report = read_json(directory/"summary.json")
    cells = []
    details = []
    inputs = [directory/"summary.json"]
    for cell in report["cells"]:
        location = directory/cell["cell_id"]
        explanations = []
        display_statuses = Counter()
        single_numeric_only = 0
        difference_present = 0
        for path in sorted(location.glob("explanation-*.json")):
            row = read_json(path)
            display = row["result"]["display"] or {}
            claims = display.get("claims", [])
            display_statuses[display.get("answer_status", "no_display")] += 1
            single_numeric_only += len(claims) == 1 and claims[0]["claim_type"] == "numeric_observation"
            difference_present += any(claim["operator"] == "difference" for claim in claims)
            item = {"cell_id": cell["cell_id"], "index": row["index"], "kind": row["kind"],
                    "adequate_at_request": row["adequate"], **completion_adequacy(row, cell["offered_events_per_second"])}
            explanations.append(item); details.append(item); inputs.append(path)
        journals = read_journal(location/"requests.jsonl")
        finished = [row for row in journals if row["event"] == "finished"]
        assert len(finished) == cell["initial_gpu_calls"] + cell["validation_repairs"], "Unaccounted systems model calls"
        cells.append({**cell, "adequate_at_request": sum(r["adequate_at_request"] for r in explanations),
                      "usage_unavailable_requests": sum(not all(key in row.get("response", {}).get("usage", {})
                          for key in ("prompt_tokens", "completion_tokens")) for row in finished),
                      "adequate_at_completion": sum(r["adequate_at_completion"] for r in explanations),
                      "adequate_then_stale": sum(r["adequate_at_request"] and not r["adequate_at_completion"] for r in explanations),
                      "display_statuses": dict(display_statuses),
                      "single_numeric_only": single_numeric_only,
                      "difference_present": difference_present,
                      "target_changed_before_completion": sum(r["target_value_changed"] for r in explanations),
                      "completion_audited": len(explanations)})
    result = {"run_id": run_id, "cells": cells, "logical_parity": report["logical_parity"],
              "call_count": sum(c["initial_gpu_calls"]+c["validation_repairs"] for c in cells),
              "maximum_calls": report["config"]["maximum_total_gpu_calls"], "completion_checks": details,
              "completion_check_scope": "descriptive post-processing; remap citations to currently known versions and recheck numerical content",
              "inputs": {str(path): digest_file(path) for path in inputs}, "script_sha256": digest_file(__file__)}
    assert result["call_count"] <= result["maximum_calls"]
    write_json(f"artifacts/analysis/{run_id}/summary.json", result)
    return result


def resource_summary():
    telemetry_path = Path("artifacts/runs/resources.jsonl")
    stage_path = Path("artifacts/manifests/execution_stages.jsonl")
    telemetry = read_jsonl(telemetry_path)
    stages = [row for row in read_jsonl(stage_path) if row["event"] == "finished"]
    result = []
    for stage in stages:
        begin, end = datetime.fromisoformat(stage["started_at"]), datetime.fromisoformat(stage["finished_at"])
        samples = [r for r in telemetry if begin <= datetime.fromisoformat(r["time"]) <= end]
        result.append({"stage": stage["stage"], "wall_seconds": stage["seconds"], "telemetry_samples": len(samples),
                       "peak_gpu_memory_mib": max((r["memory_used_mib"] for r in samples), default=None),
                       "mean_gpu_utilization_percent": float(np.mean([r["gpu_utilization_percent"] for r in samples])) if samples else None,
                       "peak_host_cgroup_memory_bytes": max((r["host_cgroup_memory_bytes"] for r in samples if r["host_cgroup_memory_bytes"] is not None), default=None)})
    times = sorted(datetime.fromisoformat(row["time"]) for row in telemetry)
    report = {"stages": result, "hourly_price": None, "currency_cost": None,
              "telemetry_samples":len(telemetry),
              "telemetry_started_at":times[0].isoformat() if times else None,
              "telemetry_finished_at":times[-1].isoformat() if times else None,
              "telemetry_span_seconds":(times[-1]-times[0]).total_seconds() if times else None,
              "notes": ["Stage wall time includes host work and GPU idle gaps; it is not CUDA kernel time",
                        "One-second GPU telemetry can miss brief peaks",
                        "Cgroup memory includes the whole pod and file cache, not per-method private memory",
                        "Measured workload wall time excludes downloads, initial model-server compilation and unlogged gaps; it is not total billable pod time",
                        "No account hourly rate was supplied; no monetary cost estimated"],
              "inputs": {str(telemetry_path): digest_file(telemetry_path), str(stage_path): digest_file(stage_path)}}
    write_json("artifacts/analysis/resources.json", report)
    return report


if __name__ == "__main__":
    analyze_streaming()
    resource_summary()
