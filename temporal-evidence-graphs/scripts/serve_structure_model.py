"""Separate launcher; never overwrite minimum_v1 placement or launch manifests."""
import os
from pathlib import Path
from temporal_evidence.io import read_json,write_json,utc_now

manifest=read_json("artifacts/manifests/model.json")
command=[str(Path(".venv/bin/vllm").resolve()),"serve",manifest["local_path"],"--served-model-name",manifest["model_id"],
    "--host","127.0.0.1","--port","8000","--dtype","bfloat16","--max-model-len","12288","--max-num-seqs","4",
    "--gpu-memory-utilization","0.85","--cpu-offload-gb","0","--swap-space","0","--enforce-eager","--seed","20260929",
    "--generation-config","vllm","--guided-decoding-backend","xgrammar","--guided-decoding-disable-any-whitespace",
    "--worker-cls","temporal_evidence.structure.gpu_worker.StructureGPUWorker"]
write_json("artifacts/runs/structure_study_v1/server_launch.json",{"started_at":utc_now(),"command":command,"revision":manifest["revision"]})
os.environ["VLLM_USE_V1"]="1"; os.execv(command[0],command)
