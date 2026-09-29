"""Run the authorized minimum study sequentially, stopping on a failed gate.

Start only after the live development systems smoke test has passed. This script
does not change the configuration or create compute resources.
"""
import argparse
from pathlib import Path
import os
import shutil
import signal
import subprocess
import sys
import time

from temporal_evidence.io import append_jsonl, read_json, utc_now, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-server-pid", type=int, required=True)
    args = parser.parse_args()
    journal = Path("artifacts/manifests/execution_stages.jsonl")

    def stage(name, *command):
        event = {"stage": name, "started_at": utc_now(), "command": list(command)}
        append_jsonl(journal, {**event, "event": "started"})
        write_json("artifacts/manifests/execution_status.json", event)
        print(f"Starting {name}", flush=True)
        started = time.perf_counter()
        result = subprocess.run(command)
        event.update(finished_at=utc_now(), seconds=time.perf_counter()-started,
                     returncode=result.returncode, event="finished")
        append_jsonl(journal, event)
        write_json("artifacts/manifests/execution_status.json", event)
        if result.returncode:
            raise SystemExit(result.returncode)

    for method in ("M1", "B3"):
        result = read_json(f"artifacts/streaming/streaming_development_v2/{method}-20eps/summary.json")
        assert not result["errors"] and result["completed_explanations"] == 2

    def save_pilot_proofs(run_id):
        target = Path(f"artifacts/runs/{run_id}")
        for name in ("gpu_placement.json", "server_launch.json"):
            shutil.copyfile(Path("artifacts/manifests")/name, target/name)

    save_pilot_proofs("pilot_v3")
    command = [sys.executable, "-m", "temporal_evidence.cli"]
    stage("final_development_pilot", *command, "pilot", "--run-id", "pilot_v4")
    save_pilot_proofs("pilot_v4")
    stage("final_live_core_validation", *command, "validate-core", "--graph")
    stage("development_evaluation", *command, "evaluate", "--run-id", "pilot_v4")
    stage("protocol_freeze", *command, "freeze-manifest")
    stage("matched_held_out_run", *command, "run", "--resume")
    stage("independent_evaluation", *command, "evaluate")
    stage("paired_analysis", *command, "analyze")
    stage("isolated_streaming_benchmark", *command, "benchmark-streaming")

    # Stop only the primary API server explicitly supplied by the operator. Its
    # normal shutdown joins the GPU workers; never send a system-wide kill.
    process = Path(f"/proc/{args.primary_server_pid}")
    if process.exists():
        process_command = (process/"cmdline").read_bytes().replace(b"\0", b" ")
        assert b"vllm.entrypoints.openai.api_server" in process_command and b"Qwen3-8B" in process_command
        os.kill(args.primary_server_pid, signal.SIGTERM)
        for _ in range(60):
            if not process.exists():
                break
            time.sleep(1)
        else:
            raise RuntimeError("Primary model did not exit normally; inspect before loading the verifier")
    stage("automated_cuda_fidelity_audit", *command, "audit")
    write_json("artifacts/manifests/execution_status.json", {"stage": "experiments_complete", "finished_at": utc_now()})


if __name__ == "__main__":
    main()
