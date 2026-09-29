#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
test -f generated/manifest.json
test -f generated/macros.tex
test -f generated/abstract.tex
latexmk -pdf main.tex
cp build/main.pdf temporal_evidence_maintenance.pdf
