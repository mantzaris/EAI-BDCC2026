#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
test -f generated/semantic/manifest.json
test -f generated/semantic/macros.tex
test -f generated/semantic/abstract.tex
latexmk -pdf main.tex
latexmk -pdf supplement.tex
cp build/main.pdf temporal_evidence_maintenance.pdf
cp build/main.pdf semantic_structure_revision.pdf
cp build/supplement.pdf semantic_structure_supplement.pdf
