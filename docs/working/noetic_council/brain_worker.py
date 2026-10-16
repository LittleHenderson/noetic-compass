"""The brain's side of the process boundary: one JSON object per line, no torch ever.

WHY A SEPARATE PROCESS
----------------------
`rb/__init__.py` installs an import blocker whose `install()` raises if torch is already loaded, and
once installed the blocker refuses any later `import torch`. All four import orders were measured and
all four were refused (appendix E). So the brain and HELM's runtime cannot share an interpreter, and
the answer has to cross a boundary. This is that boundary's brain end.

THE PROTOCOL
------------
One JSON object per line in, one JSON object per line out. Nothing but the question and the answer
crosses, and process ids are not exchanged, so the client cannot pass an object the brain should not
hold.

  request   {"route": [0,1,2], "edges": [[0,1]]}
  reply     {"answer": "FIRST_UNSUPPORTED_LEG_1", "label_index": 1, "limiting_cell": 2,
             "gate": null, "label": "CANDIDATE"}

The reply's `label` field is the brain's own label string, reported for inspection only. The answer is
taken from the LIMITING CELL, never from the label, because the brain has four recipe slots and the
task has eight answers (appendix F section 5).

THE ENCODING, ONCE
------------------
Appendix F section 8, the spare-constant encoding. Leg cells hold `3` when the leg is present and `1`
when it is not; every cell after the last leg holds the constant `1.5`, which is strictly between the
two. The minimum is then `1.5` exactly when every leg is present, and `1` exactly when a leg is
missing, and the FIRST cell attaining the minimum names the answer. Nothing here computes the answer:
the brain's own argument of the minimum does, and this module only spells the result.

ONE BRAIN, REUSED
-----------------
`readout(x)` does not mutate the brain when `x` is given, so one brain serves every tick. The learned
state is never touched: `a` is set to `1` (the requirement) at startup and `beta` is a fixed string.

Usage:
    C:\\Python314\\python.exe -B brain_worker.py <v3-package-root>
It prints one `hello` line on startup and then serves requests until stdin closes.
"""
from __future__ import annotations

import json
import os
import sys

CELLS_FALLBACK = 8
SPARE = 1.5
LEG_MISSING, LEG_PRESENT = 1.0, 3.0
LABELS = tuple("FIRST_UNSUPPORTED_LEG_%d" % i for i in range(7)) + ("ALL_LEGS_PRESENT",)


def emit(obj) -> None:
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__ + "\n")
        return 2
    v3 = os.path.abspath(sys.argv[1])
    if not os.path.isdir(os.path.join(v3, "rb")):
        emit({"type": "fatal", "error": "no rb package under %s" % v3})
        return 1
    sys.path.insert(0, v3)

    # Import rb FIRST and nothing else that could pull torch in. `rb` installs its blocker here.
    from rb.brain import RecipeBrain
    from rb import common
    from rb import no_torch

    cells = getattr(common, "CELLS", CELLS_FALLBACK)

    brain = RecipeBrain()
    brain.allocated[0] = True
    brain.a[0] = [1.0] * cells          # the requirement is 1 for every ingredient
    brain.h[0] = [1.0] * cells
    brain.beta[0] = "CANDIDATE"         # a fixed string; the answer never comes from it
    brain._invalidate()

    state = no_torch.report()
    emit({"type": "hello", "cells": cells, "spare": SPARE,
          "leg_missing": LEG_MISSING, "leg_present": LEG_PRESENT,
          "labels": list(LABELS), "blocker": state,
          "torch_absent": "torch" not in sys.modules and "numpy" not in sys.modules})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError as error:
            emit({"type": "error", "error": "not JSON: %s" % error})
            continue
        if request.get("type") == "stop":
            emit({"type": "stopped"})
            return 0
        try:
            route = [int(v) for v in request["route"]]
            edges = {(int(a), int(b)) for a, b in request["edges"]}
            if len(route) < 2:
                raise ValueError("a route needs at least two nodes")
            legs = list(zip(route, route[1:]))
            if len(legs) > cells:
                raise ValueError("route has %d legs, the brain has %d cells" % (len(legs), cells))
            x = [LEG_PRESENT if pair in edges else LEG_MISSING for pair in legs]
            x += [SPARE] * (cells - len(x))
            readout = brain.readout(x)
            if readout.gate is not None or readout.limiting is None:
                emit({"type": "answer", "answer": "UNDETERMINED", "label_index": None,
                      "limiting_cell": None, "gate": readout.gate, "label": readout.label})
                continue
            cell = readout.limiting
            if cell == len(legs):
                answer, index = LABELS[-1], len(LABELS) - 1
            elif cell < len(legs):
                answer, index = LABELS[cell], cell
            else:
                answer, index = "UNDETERMINED", None
            emit({"type": "answer", "answer": answer, "label_index": index,
                  "limiting_cell": cell, "gate": None, "label": readout.label})
        except Exception as error:  # noqa: BLE001 - a refusal must be reported, not swallowed
            emit({"type": "error", "error": "%s: %s" % (type(error).__name__, error)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
