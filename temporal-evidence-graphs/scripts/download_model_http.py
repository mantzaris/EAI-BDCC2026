"""Resumable public model download independent of the inference installation.

Range requests allow progress despite a poor single-connection path. No credentials
are sent; the exact public model revision and every completed file are recorded.
"""
import concurrent.futures
import argparse
import json
import os
from pathlib import Path
import shutil
import time
import urllib.request

from temporal_evidence.io import digest_file, read_json, utc_now, write_json

parser=argparse.ArgumentParser()
parser.add_argument("--model",default="Qwen/Qwen3-8B")
parser.add_argument("--manifest",default="artifacts/manifests/model.json")
args=parser.parse_args()
MODEL_ID = args.model
manifest = Path(args.manifest)
directory = Path(".runtime/models") / MODEL_ID.split("/")[-1]
directory.mkdir(parents=True, exist_ok=True)
with urllib.request.urlopen(f"https://huggingface.co/api/models/{MODEL_ID}", timeout=60) as response:
    info = json.load(response)
revision = read_json(manifest)["revision"] if manifest.exists() else info["sha"]
if manifest.exists():
    assert read_json(manifest)["model_id"]==MODEL_ID
with urllib.request.urlopen(f"https://huggingface.co/api/models/{MODEL_ID}/revision/{revision}",timeout=60) as response:
    info=json.load(response)
metadata = {"model_id": MODEL_ID, "revision": revision, "tokenizer_revision": revision,
            "resolved_at": utc_now(), "status": "downloading", "local_path": str(directory.resolve()), "files": []}
write_json(manifest, metadata)
names = [entry["rfilename"] for entry in info["siblings"]
         if entry["rfilename"].endswith((".json", ".safetensors", ".txt", ".model", ".jinja")) or entry["rfilename"] == "README.md"]


def part_download(url, start, stop, path):
    expected = stop - start + 1
    if path.exists() and path.stat().st_size == expected:
        return
    for attempt in range(8):
        temporary = path.with_suffix(".part")
        have = temporary.stat().st_size if temporary.exists() else 0
        if have == expected:
            temporary.rename(path)
            return
        try:
            request = urllib.request.Request(url, headers={"Range": f"bytes={start+have}-{stop}"})
            with urllib.request.urlopen(request, timeout=120) as response:
                if response.status != 206:
                    raise RuntimeError("Model CDN did not honor the range request")
                with temporary.open("ab") as stream:
                    while chunk := response.read(256 * 1024):
                        stream.write(chunk)
            if temporary.stat().st_size != expected:
                raise RuntimeError("Model range length mismatch")
            temporary.rename(path)
            return
        except Exception:
            if attempt == 7:
                raise
            time.sleep(min(2**attempt, 30))


for name in names:
    destination = directory / name
    url = f"https://huggingface.co/{MODEL_ID}/resolve/{revision}/{name}"
    if not destination.exists():
        if name.endswith(".safetensors"):
            request = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
            with urllib.request.urlopen(request, timeout=120) as response:
                size = int(response.headers["Content-Range"].split("/")[-1])
            chunks = directory / (name + ".chunks")
            chunks.mkdir(exist_ok=True)
            block = 16 * 1024 * 1024
            work = [(url, start, min(start+block, size)-1, chunks / f"{start:012d}") for start in range(0, size, block)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                futures = [executor.submit(part_download, *item) for item in work]
                for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    future.result()
                    if index % 10 == 0:
                        print(f"{name}: {index}/{len(work)} ranges complete", flush=True)
            temporary = destination.with_suffix(".part")
            with temporary.open("wb") as output:
                for _, _, _, part in work:
                    with part.open("rb") as source:
                        shutil.copyfileobj(source, output)
            assert temporary.stat().st_size == size
            temporary.rename(destination)
            shutil.rmtree(chunks)
        else:
            with urllib.request.urlopen(url, timeout=120) as response:
                temporary = destination.with_suffix(destination.suffix + ".part")
                temporary.write_bytes(response.read())
                temporary.rename(destination)
    metadata["files"].append({"name": name, "sha256": digest_file(destination), "bytes": destination.stat().st_size})
    write_json(manifest, metadata)
    print(f"Verified {name}", flush=True)
metadata["status"] = "downloaded"
write_json(manifest, metadata)
