#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .runtime logs artifacts/manifests
export UV_CACHE_DIR="$PWD/.runtime/uv-cache"
export HF_HOME="$PWD/.runtime/huggingface"
if [ ! -f .venv/pyvenv.cfg ]; then
  uv venv --system-site-packages --python /usr/bin/python3 .venv
fi
shopt -s nullglob
local_wheels=(.runtime/wheels/*.whl)
.venv/bin/python -m pip install "${local_wheels[@]}" -e '.[gpu,dashboard]'
.venv/bin/python -m pip freeze > artifacts/manifests/requirements.actual.txt
.venv/bin/python scripts/export_lock.py
bash scripts/setup_database.sh
if [ ! -f artifacts/manifests/model.json ]; then
  .venv/bin/python scripts/prepare_model.py
fi
