#!/usr/bin/env bash
# Render a manuscript file (default manuscript.md; e.g. taslp_submission.md) in IEEE journal format (IEEEtran, 10 pt, two columns, US letter) to
# build/ieee/manuscript_ieee.pdf, for a page-count and layout check of an IEEE/ACM TASLP
# submission (presentation only; the manuscript text is not changed).
# Needs pandoc >= 3 (set PANDOC=/path/to/pandoc if it is not on PATH), xelatex, latexmk and the
# IEEEtran class (TeX Live). References use the IEEE CSL style (tools/ieee.csl, CC BY-SA 3.0,
# citation-style-language/styles). Tables and figures are measured floats (tools/ieee.lua,
# tools/ieee-header.tex); tools/ieee_layout_report.py summarises pages and float placement.
set -euo pipefail
cd "$(dirname "$0")/.."
PANDOC="${PANDOC:-pandoc}"
INPUT="${1:-manuscript.md}"
OUT="${OUT:-build/ieee}"   # IEEE_DROP_SECTIONS="Title|Title" omits sections (what-if renderings)
mkdir -p "$OUT"
IEEE_FLOATS_TSV="$OUT/floats.tsv" "$PANDOC" "$INPUT" --standalone --citeproc --csl tools/ieee.csl \
  --lua-filter tools/ieee.lua -H tools/ieee-header.tex ${EXTRA_HEADER:+-H "$EXTRA_HEADER"} \
  -V documentclass=IEEEtran -V classoption=journal -V classoption=10pt -V papersize=letter \
  ${CLASSOPTION:+-V classoption=$CLASSOPTION} \
  -V colorlinks=true -V linkcolor=black -V urlcolor=black -V citecolor=black \
  -o "$OUT/manuscript_ieee.tex"
# Compile from manuscript/ so that figure paths resolve; three passes settle the float labels.
max_print_line=10000 latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir="$OUT" "$OUT/manuscript_ieee.tex" > "$OUT/latexmk.out"
echo "wrote $OUT/manuscript_ieee.pdf"
