"""With the frozen input rule, can the brain name a failing leg — or does its own gate refuse?

WHY THIS EXISTS
---------------
Appendix A froze the input rule: each route leg is an ingredient, requirement exactly `1`, stock
exactly `1` if the leg exists and `0` if not, yield `stock / requirement`.

`RecipeBrain.readout` computes the best yield across recipes and then does this:

    best = max(values[r] for r in firing)
    if best == ZERO:
        return Readout(UNDETERMINED, "G2", None, values, None)

Zero stock gives zero yield, so a single missing leg drives the best yield to zero and the brain
answers **UNDETERMINED** instead of naming the leg. Appendix A already says nobody had measured
whether the brain can answer this task. This probe measures it.

It also asks the question that decides how much that matters: **what share of the runtime's own cases
have every leg present?** That share is the ceiling on how often the brain's two available answers
("a label", or "cannot be computed") could ever be right.

WHAT IT DOES NOT DO
-------------------
It does not propose a fix. It reports the gate's behaviour, whether any requirement value avoids it,
and the ceiling.

Usage:
    C:\\Python314\\python.exe -B probe_brain_gate_vs_task.py <v3-package-root> <r6-source-root>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

BRAIN_SIDE = """
import json
from rb.brain import RecipeBrain
from rb import common

def configured(req):
    b = RecipeBrain()
    b.allocated[0] = True
    b.a[0] = [req] * common.CELLS
    b.h[0] = [req] * common.CELLS
    b.beta[0] = "SOME_LABEL"
    b._invalidate()
    return b

report = {"recipes": common.RECIPES, "cells": common.CELLS, "trials": []}

# Trial 1: every leg present (all stock 1).
b = configured(1.0)
r = b.readout([1.0] * common.CELLS)
report["all_present"] = r.as_record()

# Trial 2: one leg missing (one stock 0), which is the ordinary case.
b = configured(1.0)
r = b.readout([1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0])
report["one_missing"] = r.as_record()

# Trial 3: does ANY requirement value avoid the zero-yield gate? Stock is frozen at 0 or 1, so
# only the requirement is free. Sweep it across the brain's own allowed bounds.
for req in (0.05, 0.25, 1.0, 2.0, 20.0):
    b = configured(req)
    r = b.readout([1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    report["trials"].append({"requirement": req, "label": r.label, "gate": r.gate,
                             "winner": r.winner, "limiting_cell": r.limiting})

# Trial 4: a second allocated recipe, to see whether the active set can exclude the missing cell
# WITHOUT already knowing which cell is missing.
b = RecipeBrain()
for k, req in enumerate((1.0, 1.0)):
    b.allocated[k] = True
    b.a[k] = [req] * common.CELLS
    b.h[k] = [req] * common.CELLS
    b.beta[k] = "LABEL_%d" % k
b._invalidate()
r = b.readout([1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
report["two_recipes_one_missing"] = r.as_record()
report["two_recipes_active_sets"] = [b.active(0), b.active(1)]

print(json.dumps(report))
"""

RUNTIME_SIDE = """
import json
import native_task

# The return shape is {"cases": ..., "answers": ..., "manifest": ...}. The first version of this
# probe guessed a "splits" key that does not exist; it refused rather than reporting a number it had
# not read, which is the intended behaviour.
data = native_task.generate_dataset()
labels = list(native_task.ANSWER_LABELS)
all_present = labels[-1]

counts = {}
for split, cases in data["cases"].items():
    n = len(cases)
    by_answer = {}
    for c in cases:
        a = native_task.derive_answer(c)
        by_answer[a] = by_answer.get(a, 0) + 1
    counts[split] = {"cases": n, "all_legs_present": by_answer.get(all_present, 0),
                     "per_answer": by_answer}

base = {k: v for k, v in data["cases"].items() if k != "heldout_twins"}
total = sum(len(v) for v in base.values())
total_present = sum(sum(1 for c in v if native_task.derive_answer(c) == all_present)
                    for v in base.values())
print(json.dumps({"splits": counts, "total_cases": total,
                  "total_all_legs_present": total_present,
                  "all_present_label": all_present,
                  "n_answer_labels": len(labels),
                  "split_counts": data["manifest"]["split_counts"]}))
"""


def _run(body: str, env_extra: dict) -> dict:
    env = dict(os.environ)
    env.update(env_extra)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(body)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env, timeout=1800)
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        return {"_failed": True, "_error": err[-1] if err else "no stderr"}
    return json.loads((proc.stdout or "").strip().splitlines()[-1])


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    v3, r6 = (os.path.abspath(p) for p in sys.argv[1:3])
    for path, why in ((os.path.join(v3, "rb"), "rb package"), (os.path.join(r6, "native_task.py"),
                                                              "native_task.py")):
        if not os.path.exists(path):
            print("REFUSED: no %s under %s" % (why, path))
            return 1

    brain = _run(BRAIN_SIDE, {"PYTHONPATH": v3})
    runtime = _run(RUNTIME_SIDE, {"PYTHONPATH": os.pathsep.join([r6, v3])})

    print("=" * 78)
    print("THE FROZEN INPUT RULE AGAINST THE BRAIN'S OWN GATE")
    print("=" * 78)
    if brain.get("_failed") or runtime.get("_failed"):
        print("  the brain side   : %s" % (brain.get("_error") or "ok"))
        print("  the runtime side : %s" % (runtime.get("_error") or "ok"))
        print("REFUSED: one side could not be read, so no comparison is made.")
        return 1

    ap = brain["all_present"]
    om = brain["one_missing"]
    print("  every leg present, requirement 1, stock all 1:")
    print("    label %r  gate %r  winner %r  limiting %r" % (ap["label"], ap["gate"],
                                                             ap["winner"], ap["limiting_cell"]))
    print("  one leg missing, requirement 1, stock 0 at one cell:")
    print("    label %r  gate %r  winner %r  limiting %r" % (om["label"], om["gate"],
                                                             om["winner"], om["limiting_cell"]))
    print()
    print("  sweeping the requirement across the brain's own allowed bounds, one leg missing:")
    for t in brain["trials"]:
        print("    requirement %-6s -> label %-14r gate %r  limiting %r"
              % (t["requirement"], t["label"], t["gate"], t["limiting_cell"]))
    print()
    print("  two allocated recipes, one leg missing:")
    tp = brain["two_recipes_one_missing"]
    print("    label %r  gate %r  winner %r  limiting %r"
          % (tp["label"], tp["gate"], tp["winner"], tp["limiting_cell"]))
    print("    active sets: %s" % brain["two_recipes_active_sets"])
    print()
    print("  the runtime's own dataset, by split:")
    for split, v in runtime["splits"].items():
        print("    %-14s %4d cases, %4d with every leg present"
              % (split, v["cases"], v["all_legs_present"]))
    print("    %-14s %4d cases, %4d with every leg present"
          % ("TOTAL", runtime["total_cases"], runtime["total_all_legs_present"]))

    gate_fires = (om["gate"] is not None and om["label"] == "UNDETERMINED")
    all_avoided = all(t["gate"] is not None for t in brain["trials"])
    two_fires = (tp["gate"] is not None)
    ceiling = runtime["total_all_legs_present"]

    print()
    print("=" * 78)
    print("RESULT")
    print("  a missing leg drives the best yield to zero              : %s"
          % ("YES" if gate_fires else "NO"))
    print("  the brain then answers UNDETERMINED on gate G2            : %s"
          % ("YES" if gate_fires else "NO"))
    print("  any requirement value avoids it                           : %s"
          % ("NO" if all_avoided else "SOMETHING AVOIDED IT -- investigate"))
    print("  a second allocated recipe avoids it                       : %s"
          % ("NO" if two_fires else "SOMETHING AVOIDED IT -- investigate"))
    print()
    print("  So with the frozen input rule the brain has exactly two answers: a label when every")
    print("  leg is present, and UNDETERMINED when any leg is missing. It never names the leg.")
    print()
    print("  That caps it at the cases where every leg is present:")
    print("    %d of %d cases = %s"
          % (ceiling, runtime["total_cases"],
             ("%.6f" % (ceiling / runtime["total_cases"])) if runtime["total_cases"] else "n/a"))
    print("  and on the rest its answer is UNDETERMINED, which the project's own scoring counts")
    print("  as not-wrong, not as right.")
    print("=" * 78)
    print(json.dumps({"brain": brain, "runtime": runtime, "ceiling_cases": ceiling,
                      "total_cases": runtime["total_cases"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
