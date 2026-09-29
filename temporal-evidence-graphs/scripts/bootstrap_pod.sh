#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .runtime logs artifacts/manifests
export HF_HOME="$PWD/.runtime/huggingface"
if [ ! -f .venv/pyvenv.cfg ]; then
  uv venv --system-site-packages --python /usr/bin/python3 .venv
fi
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip check
mkdir -p .local
.venv/bin/python -m pip freeze > .local/requirements.reproduced.txt
bash scripts/setup_database.sh
.venv/bin/python scripts/download_model_http.py
.venv/bin/python scripts/download_model_http.py --model Qwen/Qwen2.5-3B-Instruct --manifest artifacts/manifests/audit_model.json
