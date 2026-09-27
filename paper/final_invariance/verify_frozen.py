"""
Read-only verification of every frozen record of the project (pre-submission invariance pass).

Checks every self-sealed JSON record, every sealed output manifest, the Stage 3 integrity chain,
the TASLP-upgrade plan, code freeze, freeze manifest and amendment, the R1-R3 plan and code freeze,
the R4 plan and code freeze (committed), and prints the frozen outcomes of every analysis.
Writes nothing. Exit status 1 if anything fails to verify.

    python paper/final_invariance/verify_frozen.py
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "paper" / d) for d in ["decoder_sensitivity", "reviewer_sensitivity", "taslp_upgrade"]] \
    + [str(ROOT / "paper")]

import os                                # noqa: E402
os.chdir(ROOT)

import run_stage3 as s3                  # noqa: E402
import upgrade_design as ud              # noqa: E402
import reviewer_design as rd             # noqa: E402
import r4_design as r4                   # noqa: E402


def body(rec: dict, key: str) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in rec.items() if k != key}, sort_keys=True).encode()).hexdigest()


def main() -> int:
    fails = []
    sealed = []
    for p in sorted(Path(".").rglob("*.json")):
        if ".git" in p.parts or "build" in p.parts:
            continue
        rec = json.loads(p.read_text())
        if isinstance(rec, dict) and rec:
            last = list(rec)[-1]
            if last.endswith("_sha256") and isinstance(rec[last], str):
                sealed.append(str(p))
                if rec[last] != body(rec, last):
                    fails.append(f"SEAL {p}")
    print(f"self-sealed records: {len(sealed)}")
    manifests = sorted(Path("results_paper").rglob("outputs_sha256.json"))
    for m in manifests:
        rec = s3.read_sealed(m, "outputs_sha256")
        for name, digest in rec["files"].items():
            if s3.file_sha256(m.parent / name) != digest:
                fails.append(f"MANIFEST {m.parent / name}")
    print(f"output manifests: {len(manifests)}")
    st = ud.stage3_integrity()
    print(f"Stage 3: spec {st['stage3_spec_sha256'][:12]}, decision {st['stage3_decision_sha256'][:12]} "
          f"({st['stage3_decision']})")
    spec, freeze = ud.require_code_freeze()
    fm = s3.read_sealed(ud.RESULTS / "freeze_manifest.json", "manifest_sha256")
    bad = [p for group in fm["files"].values() for p, h in group.items() if s3.file_sha256(Path(p)) != h]
    fails += [f"FREEZE MANIFEST {p}" for p in bad]
    for a in sorted(Path("paper/taslp_upgrade/amendments").glob("*.json")):
        s3.read_sealed(a, "amendment_sha256")
    print(f"TASLP upgrade: plan {spec['spec_sha256'][:12]}, code freeze {freeze['freeze_sha256'][:12]}, "
          f"freeze manifest {len(bad)} mismatches")
    level = s3.read_sealed(ud.RESULTS / "level" / "analysis" / "level_decision.json", "decision_sha256")
    sweep = s3.read_sealed(ud.RESULTS / "sweep" / "analysis" / "sweep_decision.json", "decision_sha256")
    print(f"  Addition A: {level['outcome']} | Addition B: {sweep['outcome']}")
    rspec, rfreeze = rd.require_code_freeze()
    rdec = s3.read_sealed(rd.RESULTS / "analysis" / "reviewer_decision.json", "decision_sha256")
    print(f"R1-R3: plan {rspec['spec_sha256'][:12]}, code freeze {rfreeze['freeze_sha256'][:12]}, "
          f"outcomes {json.dumps(rdec['outcomes'])}")
    if rdec["outcomes"]["R1"] != "STOPPED" or rdec["outcomes"]["R2"] != "STOPPED":
        fails.append("R1/R2 not STOPPED")
    r4spec, r4freeze = r4.require_code_freeze(committed=True)
    r4dec = s3.read_sealed(r4.RESULTS / "analysis" / "r4_decision.json", "decision_sha256")
    print(f"R4: plan {r4spec['spec_sha256'][:12]}, code freeze {r4freeze['freeze_sha256'][:12]}, outcomes "
          f"{json.dumps({m: c['outcome'] for m, c in r4dec['cells'].items()})}")
    print("RESULT:", "PASS" if not fails else f"{len(fails)} problem(s)")
    for f in fails:
        print(" -", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
