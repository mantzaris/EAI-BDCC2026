#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# main.tex contains the complete manuscript and bibliography.
latexmk -pdf main.tex
cp build/main.pdf semantic_structure_revision.pdf
