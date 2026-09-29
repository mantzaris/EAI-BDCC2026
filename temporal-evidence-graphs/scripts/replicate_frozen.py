"""Run an additional, separately named replication of the frozen model protocol.

This launches new CUDA requests only when explicitly executed. It is not part of
the completed minimum-study budget, and it never overwrites minimum_v1 outputs.
"""
import argparse
import asyncio
from pathlib import Path
import re
from temporal_evidence.io import digest_object, read_json, write_json, utc_now
from temporal_evidence.study import verify_frozen
from temporal_evidence.experiment import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"replication_[a-z0-9_]+", args.run_id):
        parser.error("Use a new identifier beginning with replication_")
    path = Path("artifacts/manifests")/f"{args.run_id}.json"
    if path.exists() and not args.resume:
        parser.error("Existing replication requires --resume")
    if path.exists():
        manifest = read_json(path)
    else:
        manifest = read_json("artifacts/manifests/minimum_run.json")
        verify_frozen(manifest)
        manifest["source_protocol_hash"] = manifest.pop("protocol_hash")
        manifest["run_id"] = args.run_id
        manifest["replication_created_at"] = utc_now()
        manifest["replication_server_launch"] = read_json("artifacts/manifests/server_launch.json")
        manifest["replication_gpu_placement"] = read_json("artifacts/manifests/gpu_placement.json")
        manifest["replication_note"] = "Same source, inputs and model configuration; new run namespace and recorded runtime placement. Repeated calls are not additional participants."
        manifest["protocol_hash"] = digest_object(manifest)
        write_json(path, manifest)
    verify_frozen(manifest)
    print(asyncio.run(run(str(path))))


if __name__ == "__main__":
    main()
