"""Create a bounded-time snapshot of completed artifacts during or after a run.

Append-only JSONL files are copied through their last complete newline. Atomic
JSON files and immutable case files are read once. This never edits the run.
"""
import argparse
from pathlib import Path
import io
import json
import tarfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    parser.add_argument("--include", nargs="+", default=["artifacts/runs/minimum_v1", "artifacts/manifests/execution_status.json",
                        "artifacts/manifests/execution_stages.jsonl", "artifacts/runs/resources.jsonl"])
    args = parser.parse_args()
    paths = set()
    for name in args.include:
        path = Path(name)
        if path.is_dir():
            paths.update(p for p in path.rglob("*") if p.is_file() and p.suffix != ".tmp")
        elif path.is_file():
            paths.add(path)
    with tarfile.open(args.destination, "w:gz") as archive:
        for path in sorted(paths):
            data = path.read_bytes()
            if path.suffix == ".jsonl":
                last = data.rfind(b"\n")
                data = data[:last+1]
            elif path.suffix == ".json":
                json.loads(data)
            item = tarfile.TarInfo(str(path))
            item.size = len(data); item.mtime = int(time.time()); item.mode = 0o644
            archive.addfile(item, io.BytesIO(data))
    print(f"Backed up {len(paths)} artifact files to {args.destination}")


if __name__ == "__main__":
    main()
