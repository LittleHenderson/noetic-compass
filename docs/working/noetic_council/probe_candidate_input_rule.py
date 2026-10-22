"""Does the candidate input rule in appendix F section 7 actually avoid the gate?

WHY THIS EXISTS
---------------
Appendix F section 7 proposes a repair: give the cells values that are never zero, so the brain's own
argmin finds the first missing leg instead of refusing on G2. That is a claim about arithmetic, and a
claim about arithmetic that has not been run is a guess. This runs it.

It tests ONLY the arithmetic of the candidate. It does NOT decide whether the candidate is allowed,
because the reference cell needs to know whether every leg is present, and whether that crosses the
`RT_SHIM_NO_MATH` line is a design question.

WHAT IT DOES NOT DO
-------------------
It does not import torch, and so cannot import the runtime's own oracle. The cases below are written
out by hand from the rule and checked against the candidate, not against `derive_answer`.

Usage:
    C:\\Python314\\python.exe -B probe_candidate_input_rule.py <v3-package-root>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

CELLS = 8
PADDING_STOCK = 3.0
LEG_PRESENT, LEG_MISSING, REF_ALL_PRESENT, REF_SOMETHING_MISSING = 2.0, 1.0, 1.0, 3.0

BODY = """
import json
from rb.brain import RecipeBrain
from rb import common

CELLS = common.CELLS
PAD, PRESENT, MISSING = 3.0, 2.0, 1.0
REF_ALL, REF_SOME = 1.0, 3.0


def build(route_len, present_flags):
    \"\"\"cells: 0 = reference, 1..route_len = legs, the rest padding.\"\"\"
    all_present = all(present_flags)
    x = [REF_ALL if all_present else REF_SOME]
    for ok in present_flags:
        x.append(PRESENT if ok else MISSING)
    x += [PAD] * (CELLS - len(x))
    return x


def brain(req=1.0):
    b = RecipeBrain()
    b.allocated[0] = True
    b.a[0] = [req] * CELLS
    b.h[0] = [req] * CELLS
    b.beta[0] = "CANDIDATE"
    b._invalidate()
    return b


rows = []
for n_legs in range(1, 8):
    for missing_at in [None] + list(range(n_legs)):
        flags = [True] * n_legs
        if missing_at is not None:
            flags[missing_at] = False
        x = build(n_legs, flags)
        r = brain().readout(x)
        expect = "ALL_LEGS_PRESENT" if missing_at is None else "LEG_%d" % missing_at
        got = ("ALL_LEGS_PRESENT" if r.limiting == 0 else
               ("LEG_%d" % (r.limiting - 1)) if r.limiting is not None else None)
        rows.append({"legs": n_legs, "missing_at": missing_at, "x": x, "label": r.label,
                     "gate": r.gate, "limiting_cell": r.limiting, "expect": expect, "got": got,
                     "agree": (r.gate is None and got == expect)})

# Padding-only probe: a route of one leg, so cells 2..7 are padding.
print(json.dumps({"rows": rows,
                  "n": len(rows),
                  "gated": sum(1 for r in rows if r["gate"] is not None),
                  "agree": sum(1 for r in rows if r["agree"])}))
"""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    v3 = os.path.abspath(sys.argv[1])
    if not os.path.isdir(os.path.join(v3, "rb")):
        print("REFUSED: no rb package under %s" % v3)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = v3
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(BODY)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env, timeout=600)
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        print("REFUSED: the brain side failed: %s" % (err[-1] if err else "no stderr"))
        return 1
    out = json.loads((proc.stdout or "").strip().splitlines()[-1])

    print("=" * 78)
    print("THE CANDIDATE INPUT RULE, RUN ON A LIVE BRAIN")
    print("=" * 78)
    print("  every route length from 1 to 7 legs, and every position of a single missing leg.")
    print()
    print("  %-5s %-11s %-6s %-14s %-14s %s" % ("legs", "missing_at", "cell", "expect", "got", "ok"))
    for r in out["rows"]:
        print("  %-5d %-11s %-6s %-14s %-14s %s"
              % (r["legs"], "none" if r["missing_at"] is None else r["missing_at"],
                 r["limiting_cell"], r["expect"], r["got"], "yes" if r["agree"] else "NO"))
    print()
    print("  cases checked      : %d" % out["n"])
    print("  cases gated        : %d" % out["gated"])
    print("  cases agreed       : %d" % out["agree"])
    print()
    print("=" * 78)
    ok = out["gated"] == 0 and out["agree"] == out["n"]
    print("RESULT: %s" % ("THE ARITHMETIC HOLDS on every case tried" if ok else
                          "THE ARITHMETIC DOES NOT HOLD"))
    if ok:
        print("  The candidate avoids G2 on all %d cases and the limiting cell names the answer."
              % out["n"])
        print("  This decides the ARITHMETIC only. Whether the reference cell is allowed under")
        print("  RT_SHIM_NO_MATH is a design question and is NOT decided here.")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
