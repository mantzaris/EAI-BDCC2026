"""Pin and download the primary generator before pilot generation."""
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download
from temporal_evidence.io import digest_file, read_json, utc_now, write_json

manifest_path = Path("artifacts/manifests/model.json")
model_id = "Qwen/Qwen3-8B"
revision = read_json(manifest_path)["revision"] if manifest_path.exists() else HfApi().model_info(model_id).sha
write_json(manifest_path, {"model_id": model_id, "revision": revision, "resolved_at": utc_now(), "status": "downloading"})
location = snapshot_download(model_id, revision=revision,
                             allow_patterns=["*.safetensors", "*.json", "*.txt", "*.model", "*.jinja", "README.md"])
files = [{"name": p.name, "sha256": digest_file(p), "bytes": p.stat().st_size}
         for p in sorted(Path(location).iterdir()) if p.is_file()]
write_json(manifest_path, {"model_id": model_id, "revision": revision, "tokenizer_revision": revision,
                          "resolved_at": utc_now(), "status": "downloaded", "files": files,
                          "local_path": location})
print(f"Downloaded {model_id}@{revision}", flush=True)
