"""Remove redundant extracted pickles only after verifying the original archive.

The immutable original ZIP remains authoritative; adapters read its members directly
when the extraction cache is absent. This never deletes an original archive.
"""
import argparse
from pathlib import Path
from temporal_evidence.io import digest_file,read_json,write_json,utc_now

parser=argparse.ArgumentParser()
parser.add_argument("dataset",choices=["wesad","ppg_dalia"])
args=parser.parse_args()
manifest=read_json(f"artifacts/manifests/acquisition/{args.dataset}.json")
assert digest_file(manifest["archive"])==manifest["archive_sha256"]
root=Path(f"data/raw/{args.dataset}/recordings").resolve()
removed=[]
for entry in manifest["files"]:
    path=Path(entry["path"])
    if path.suffix!=".pkl" or not path.exists():
        continue
    assert root in path.resolve().parents
    assert digest_file(path)==entry["sha256"],f"Changed cache file: {path}"
    removed.append({"path":str(path),"bytes":path.stat().st_size,"sha256":entry["sha256"]})
    path.unlink()
write_json(f"artifacts/manifests/{args.dataset}_extraction_cache_pruned.json",
           {"pruned_at":utc_now(),"retained_archive":manifest["archive"],"removed_redundant_copies":removed})
print(f"Retained original archive; reclaimed {sum(row['bytes'] for row in removed)/2**30:.2f} GiB")
