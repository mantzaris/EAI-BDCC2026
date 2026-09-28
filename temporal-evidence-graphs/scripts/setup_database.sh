#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .runtime logs artifacts/manifests
if [ ! -x .runtime/jre/bin/java ]; then
  curl --http1.1 -fL --retry 3 'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.8%2B9/OpenJDK21U-jre_x64_linux_hotspot_21.0.8_9.tar.gz' -o .runtime/jre.tar.gz
  mkdir -p .runtime/jre
  tar -xzf .runtime/jre.tar.gz -C .runtime/jre --strip-components=1
fi
export JAVA_HOME="$PWD/.runtime/jre"
if [ ! -d .runtime/neo4j-community-5.26.0 ]; then
  curl --http1.1 -fL --retry 3 https://dist.neo4j.org/neo4j-community-5.26.0-unix.tar.gz -o .runtime/neo4j.tar.gz
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
"$JAVA_HOME/bin/java" -version 2> artifacts/manifests/java_version.txt
