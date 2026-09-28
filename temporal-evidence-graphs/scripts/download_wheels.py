"""Fetch selected large wheels in validated ranges from official PyPI URLs."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

directory = Path(".runtime/wheels")
directory.mkdir(parents=True, exist_ok=True)
packages = {"vllm":"0.10.2", "cupy-cuda12x":"13.6.0"}


def download_part(url, path, start, end):
    if path.exists() and path.stat().st_size == end-start+1:
        return
    with urllib.request.urlopen(urllib.request.Request(url,headers={"Range":f"bytes={start}-{end}"}),timeout=120) as response:
        if response.status != 206:
            raise RuntimeError("PyPI did not honor Range")
        path.write_bytes(response.read())
    if path.stat().st_size != end-start+1:
        raise RuntimeError("Incomplete range")


for package,version in packages.items():
    with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/{version}/json",timeout=60) as response:
        metadata = json.load(response)
    wheels = [f for f in metadata["urls"] if "x86_64" in f["filename"] and
              ("abi3" in f["filename"] or "cp312" in f["filename"]) and "manylinux" in f["filename"]]
    if len(wheels)!=1:
        raise RuntimeError(f"Ambiguous wheel {package}")
    wheel = wheels[0]
    path = directory/wheel["filename"]
    if not path.exists():
        chunks = directory/(wheel["filename"]+".chunks")
        chunks.mkdir(exist_ok=True)
        block = 8*1024*1024
        work = [(wheel["url"],chunks/f"{start:012d}",start,min(start+block,wheel["size"])-1)
                for start in range(0,wheel["size"],block)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            list(executor.map(lambda item:download_part(*item),work))
        with path.open("wb") as output:
            for _,part,_,_ in work:
                with part.open("rb") as source:
                    shutil.copyfileobj(source,output)
        shutil.rmtree(chunks)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != wheel["digests"]["sha256"]:
        raise RuntimeError(f"PyPI hash mismatch: {path}")
    print(f"Verified {path.name} {digest}",flush=True)
