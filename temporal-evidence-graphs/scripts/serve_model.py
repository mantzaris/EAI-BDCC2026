"""Launch a pinned, CUDA-only, loopback inference server."""
import os
import subprocess
from pathlib import Path
from temporal_evidence.io import read_json,write_json,utc_now

manifest=read_json("artifacts/manifests/model.json")
assert manifest["status"]=="downloaded"
command=[str(Path(".venv/bin/vllm").resolve()),"serve",manifest["local_path"],
         "--served-model-name",manifest["model_id"],"--host","127.0.0.1","--port","8000",
         "--dtype","bfloat16","--max-model-len","4608","--max-num-seqs","4",
         "--gpu-memory-utilization","0.85","--cpu-offload-gb","0","--swap-space","0",
         "--enforce-eager","--seed","20260928","--generation-config","vllm",
         "--worker-cls","temporal_evidence.generation.gpu_guard.VerifiedGPUWorker"]
write_json("artifacts/manifests/server_launch.json",{"started_at":utc_now(),"command":command,
    "revision":manifest["revision"],"non_thinking":"per-request chat_template_kwargs.enable_thinking=false"})
os.environ["VLLM_USE_V1"]="1"
os.execv(command[0],command)
