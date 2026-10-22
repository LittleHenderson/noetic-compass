"""Builder tool (NOT in the sealed package): write contract/DISJOINT_CHECK_TEACH2.json and FROZEN_TEACH2.json.

    python -X utf8 -B docs/working/helm_cube_oscillation_v1/teach2/disjoint_and_frozen_teach2.py [--pkg <folder>]

DISJOINT: the subject pools against every name in the brain's tables at the cut, every cube core name and node id
shipped in helm_now/'s cube store, and wave 7's twelve small-talk sentences (TEACH-1's rule, unchanged). Runs HELM from
the package's helm_now/ in a child process (switches OFF), with the package's wave-1 brain. FROZEN: every frozen number
of common_t2 (a package test checks equality).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_PKG = Path(r"C:\Users\wakil\Documents\Codex\2026-10-22\teach2\HELM_TEACH2_20261022")

CHILD = r'''
import contextlib, io, json, os, sys
sys.path.insert(0, sys.argv[1])
os.environ["HELM_SESSION_DIR"] = sys.argv[2]
os.environ["HELM_CANONICAL_BRAIN_DIR"] = sys.argv[3]
for k in ("HELM_MEMORY_COMPACT", "HELM_CUBE_OSC", "HELM_WIDE_BRAIN", "HELM_EYE_ACT"):
    os.environ.pop(k, None)
import helm_end_to_end_loop as e2e, helm_brain_wide as bw
with contextlib.redirect_stdout(io.StringIO()):
    loop = e2e.HELMEndToEndLoop()
b = loop.brain
names = list(b.ingredients) + list(b.products) + list(bw.unit_table()) + list(bw.named_factors())
cube = []
st = getattr(loop, "cube_store", None) or getattr(loop, "store", None)
for nid, node in (getattr(st, "nodes", {}) or {}).items():
    cube += [nid, getattr(node.core, "label", "")]
print(json.dumps({"brain": names, "cubes": cube}))
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", default=str(DEFAULT_PKG))
    a = ap.parse_args()
    pkg = Path(a.pkg)
    sys.path.insert(0, str(pkg))
    from teach2 import common_t2 as C
    from teach2 import worlds_t2 as W
    sess = pkg.parent / "_disjoint_sessions"
    out = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", CHILD, str(pkg / "helm_now"), str(sess),
                          str(C.brain_dir())], capture_output=True, text=True, check=True)
    got = json.loads(out.stdout.strip().splitlines()[-1])
    for p in (pkg / "helm_now" / "docs" / "working" / "noetic_council" / "cube_store").rglob("*.json"):
        got["cubes"].append(p.stem)
    chk = W.check_disjoint(got["brain"], got["cubes"])
    chk["brain_names_list"] = sorted({str(x) for x in got["brain"]})
    chk["cube_names_list"] = sorted({str(x) for x in got["cubes"]})
    chk["cut_commit"] = C.helm_cut()["commit"]
    C.write_json(pkg / "contract" / "DISJOINT_CHECK_TEACH2.json", chk)
    frozen = {k: getattr(C, k) for k in dir(C) if k.isupper() and k != "PKG"}
    frozen["schema"] = "helm.teach2.frozen/1"
    frozen["HELM_CUT_COMMIT"] = C.helm_cut()["commit"]
    C.write_json(pkg / "FROZEN_TEACH2.json", frozen)
    shutil.rmtree(sess, ignore_errors=True)
    print(json.dumps({"disjoint_ok": chk["ok"], "hits": chk["hits"], "brain_names": len(chk["brain_names_list"]),
                      "cube_names": len(chk["cube_names_list"]), "frozen_keys": len(frozen)}))


if __name__ == "__main__":
    main()
