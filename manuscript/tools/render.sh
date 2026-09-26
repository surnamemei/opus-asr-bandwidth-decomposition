#!/usr/bin/env bash
# Render manuscript.md to build/manuscript.pdf (presentation only).
# Needs pandoc >= 3 (set PANDOC=/path/to/pandoc if it is not on PATH) and xelatex.
set -euo pipefail
cd "$(dirname "$0")/.."
PANDOC="${PANDOC:-pandoc}"
mkdir -p build
# Text and maths fonts (STIX Two), table floats and caption style come from
# tools/render-header.tex and tools/tables.lua.
"$PANDOC" manuscript.md --citeproc --pdf-engine=xelatex \
  -H tools/render-header.tex --lua-filter tools/tables.lua \
  -V papersize=a4 -V geometry:margin=2.5cm -V fontsize=11pt \
  -V sansfont="DejaVu Sans" -V monofont="DejaVu Sans Mono" \
  -V colorlinks=true -V linkcolor=blue -V urlcolor=blue -V citecolor=blue \
  -o build/manuscript.pdf "$@"
echo "wrote build/manuscript.pdf"
