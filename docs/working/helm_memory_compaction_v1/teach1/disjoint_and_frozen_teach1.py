"""Builder tool (NOT in the sealed package): write contract/DISJOINT_CHECK_TEACH1.json and FROZEN_TEACH1.json.

    python -X utf8 -B disjoint_and_frozen_teach1.py

DISJOINT: the subject pools (worlds_t1.PERSONS + PLACES) against every name in the brain's tables at the cut (the
reference brain's ingredients and products, the wide brain's unit words and named factors), every cube core name and
node id shipped in helm_now/'s cube store, and wave 7's twelve small-talk sentences; exact match, lower case. Runs HELM
from helm_now/ in a child process (switch OFF). FROZEN: every frozen number of common_t1 (a package test checks equality).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE / "HELM_TEACH1_20261021"
sys.path.insert(0, str(PKG))
from teach1 import common_t1 as C      # noqa: E402
from teach1 import worlds_t1 as W      # noqa: E402

CHILD = r'''
import contextlib, io, json, os, sys
sys.path.insert(0, sys.argv[1])
os.environ["HELM_SESSION_DIR"] = sys.argv[2]
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
    out = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", CHILD, str(PKG / "helm_now"),
                          str(HERE / "_disjoint_sessions")], capture_output=True, text=True, check=True)
    got = json.loads(out.stdout.strip().splitlines()[-1])
    # the shipped cube store has no seed nodes; any *.json node file under helm_now's cube_store is read too
    for p in (PKG / "helm_now" / "docs" / "working" / "noetic_council" / "cube_store").rglob("*.json"):
        got["cubes"].append(p.stem)
    chk = W.check_disjoint(got["brain"], got["cubes"])
    chk["brain_names_list"] = sorted({str(x) for x in got["brain"]})
    chk["cube_names_list"] = sorted({str(x) for x in got["cubes"]})
    chk["cut_commit"] = C.helm_cut()["commit"]
    C.write_json(PKG / "contract" / "DISJOINT_CHECK_TEACH1.json", chk)
    frozen = {k: getattr(C, k) for k in dir(C) if k.isupper() and k != "PKG"}   # PKG is a machine path, never frozen
    frozen["schema"] = "helm.teach1.frozen/1"
    frozen["HELM_CUT_COMMIT"] = C.helm_cut()["commit"]
    C.write_json(PKG / "FROZEN_TEACH1.json", frozen)
    print(json.dumps({"disjoint_ok": chk["ok"], "hits": chk["hits"], "brain_names": len(chk["brain_names_list"]),
                      "cube_names": len(chk["cube_names_list"]), "frozen_keys": len(frozen)}))
    import shutil
    shutil.rmtree(HERE / "_disjoint_sessions", ignore_errors=True)


if __name__ == "__main__":
    main()
