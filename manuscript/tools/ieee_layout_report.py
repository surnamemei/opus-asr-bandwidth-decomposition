"""Page and float report for an IEEE rendering made by tools/render_ieee.sh (read-only).

Reads <build>/floats.tsv (written by tools/ieee.lua), the IEEE-FLOAT lines of the LaTeX log
(written by tools/ieee-header.tex), the .aux labels (page of every float and section) and the
PDF, and prints the page count, the page on which each section starts, and every table and
figure with its placement, final width and effective text size.

    python tools/ieee_layout_report.py [build/ieee]
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

BUILD = Path(sys.argv[1] if len(sys.argv) > 1 else "build/ieee")
BASE = BUILD / "manuscript_ieee"
TABLE_PT = 8.0          # \footnotesize in a 10 pt IEEEtran document
FIGURE_PT = 8.0         # smallest text size in the figure files (matplotlib, drawn at print size)
ROMAN = {r: i for i, r in enumerate("I II III IV V VI VII VIII IX X XI XII XIII XIV XV".split(), 1)}

pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", f"{BASE}.pdf"], capture_output=True,
                                                          text=True, check=True).stdout).group(1))
labels = {m[0]: (m[1], int(m[2])) for m in re.findall(r"\\newlabel\{([^}]*)\}\{\{([^}]*)\}\{(\d+)\}",
                                                        Path(f"{BASE}.aux").read_text())}
log = Path(f"{BASE}.log").read_text(errors="ignore")
placed = {}
for line in re.findall(r"^IEEE-FLOAT (.*)$", log, flags=re.M):
    fields = dict(kv.split("=", 1) for kv in line.split())
    placed[fields["label"]] = fields
floats = list(csv.DictReader(open(BUILD / "floats.tsv"), delimiter="\t"))
overfull = re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)

sections = ["introduction", "related-work", "methods", "results", "discussion", "limitations", "conclusion",
            "reproducibility-statement", "references", "appendix-a.-supplementary-tables",
            "appendix-b.-amendments-and-deviations"]
print(f"# IEEE layout report: {BASE}.pdf\n")
print(f"- Total pages: **{pages}**")
refs = labels.get("references", (None, None))[1]
if refs:
    print(f"- References start on page {refs}; text before them ends on that page")
print(f"- Overfull lines: {len(overfull)}" + (f" (widest {max(map(float, overfull)):.1f} pt)" if overfull else ""))
print("\n| Section | Starts on page |\n|---|---|")
for s in sections:
    if s in labels:
        print(f"| {s} | {labels[s][1]} |")

print("\n| Float | Manuscript name | Placement | Natural width (pt) | Final width (pt) | Text size (pt) | Page |")
print("|---|---|---|---|---|---|---|")
for f in floats:
    lab = f["label"]
    p = placed.get(lab, {})
    num, page = labels.get(lab, ("?", "?"))
    natural = float(p.get("natural", "0pt")[:-2])
    if f["kind"] == "table":
        final = float(p.get("final", "0pt")[:-2])
        shown = min(final, float(p.get("text", "516pt")[:-2])) if p.get("placement") == "double-shrunk" else final
        size = TABLE_PT * (shown / final if final else 1)
        name = ("uncaptioned (Section 3.4)" if f["caption"] == "(uncaptioned)"
                else f"Table {ROMAN.get(num, num)}" if num in ROMAN else f"Table {num}")
    else:
        final = min(natural, float(p.get("text", "516pt")[:-2]))
        if "final" in p:                     # a figure scaled by a rendering option (supplement)
            final = float(p["final"][:-2])
        size = FIGURE_PT * final / natural if natural else FIGURE_PT
        name = f"Fig. {num}"
    print(f"| {lab} | {name}: {f['caption'][:48]} | {p.get('placement', '?')} | {natural:.0f} | {final:.0f} "
          f"| {size:.1f} | {page} |")
