#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .runtime logs artifacts/manifests
export UV_CACHE_DIR="$PWD/.runtime/uv-cache"
export HF_HOME="$PWD/.runtime/huggingface"
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e '.[gpu,dashboard]'
.venv/bin/python -m pip --version >/dev/null 2>&1 || true
uv pip freeze --python .venv/bin/python > artifacts/manifests/requirements.actual.txt
uv pip compile pyproject.toml --extra gpu --extra dashboard --generate-hashes -o requirements.lock
if [ ! -x .runtime/jre/bin/java ]; then
  curl -fL --retry 3 'https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jre/hotspot/normal/eclipse' -o .runtime/jre.tar.gz
  mkdir -p .runtime/jre
  tar -xzf .runtime/jre.tar.gz -C .runtime/jre --strip-components=1
fi
export JAVA_HOME="$PWD/.runtime/jre"
if [ ! -d .runtime/neo4j-community-5.26.0 ]; then
  curl -fL --retry 3 https://dist.neo4j.org/neo4j-community-5.26.0-unix.tar.gz -o .runtime/neo4j.tar.gz
  tar -xzf .runtime/neo4j.tar.gz -C .runtime
  cat > .runtime/neo4j-community-5.26.0/conf/neo4j.conf <<'CONF'
server.default_listen_address=127.0.0.1
server.bolt.enabled=true
server.bolt.listen_address=127.0.0.1:7687
server.http.enabled=true
server.http.listen_address=127.0.0.1:7474
server.https.enabled=false
dbms.security.auth_enabled=false
server.memory.heap.initial_size=512m
server.memory.heap.max_size=2g
server.memory.pagecache.size=1g
CONF
fi
.runtime/neo4j-community-5.26.0/bin/neo4j start
sha256sum .runtime/jre.tar.gz .runtime/neo4j.tar.gz > artifacts/manifests/server_archives.sha256
.venv/bin/python scripts/prepare_model.py
