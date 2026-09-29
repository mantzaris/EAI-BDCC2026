#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
test -f generated/semantic/manifest.json
test -f generated/semantic/macros.tex
test -f generated/semantic/abstract.tex
test -f generated/review_views/manifest.json
test -f generated/review_views/macros.tex
latexmk -pdf main.tex
cp build/main.pdf semantic_structure_revision.pdf
