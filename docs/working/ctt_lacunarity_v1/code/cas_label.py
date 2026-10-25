"""CAS structural labeller (v1) — recipe ingredients and RPM chain labels for CAS rows.

What it does, plainly: reads a row's gold token sequence (and the CAS source when present) and writes down
  * which cells the row needs (Noetic x Domain),
  * a recipe entry per cell (declared requirement 1.0, marked as a DESIGN VALUE, not measured),
  * an RPM chain when the source really has A0 -> D -> W -> P stages, and "not_applicable" otherwise.

It never invents a requirement coefficient and never guesses a chain. Anything it cannot derive is written as null
with a reason string, so downstream code can exclude it instead of silently treating "unknown" as "zero".

    python cas_label.py --in data/notation_new100.jsonl --out data/labels_notation.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NOETIC = tuple("^%d" % i for i in range(10))
DOMAIN = ("^P", "^C", "^E", "^O")
OPS = ("×", "→", "∘", "+")
STAGE = re.compile(r"stage([ADWP])(\d)_\d+_(\d+)")
SRC_CELL = re.compile(r"\^(\d)\^([PCEO])")
LABELS_VERSION = "cas-label-v1"


def cells_from_tokens(tokens):
    """Pair each Noetic with the domain marker that follows it. Unpaired Noetics are reported, not guessed."""
    cells, unpaired = [], []
    for i, tok in enumerate(tokens):
        if tok in NOETIC:
            dom = tokens[i + 1] if i + 1 < len(tokens) else None
            if dom in DOMAIN:
                cells.append(tok + dom)
            else:
                unpaired.append(tok)
    return cells, unpaired


def recipe_for(cells):
    if not cells:
        return {"applicable": False, "reason": "no cell found"}
    return {
        "applicable": True,
        "ingredients": {c: 1.0 for c in cells},
        "coefficient_source": "design_value",     # the RPU Recipe marks its coefficients as design values
        "Y_T": None,                              # needs a state vector x_i; none is supplied here
        "limiting": None,
        "reason": "requirements are 1.0 per declared cell; no measured coefficients exist",
    }


def rpm_for(source):
    if not source:
        return {"applicable": False, "reason": "no CAS source text on the row"}
    stages = STAGE.findall(source)
    if not stages:
        return {"applicable": False, "reason": "source has no A0->D->W->P stage names"}
    chain, seen = [], set()
    for kind, m, _row in stages:
        name = kind + m
        if name not in seen:
            seen.add(name)
            chain.append(name)
    missing = [s for s in ("A0", "D", "W", "P") if not any(c.startswith(s[0]) and (s != "A0" or c == "A0") for c in chain)]
    return {"applicable": True, "chain": chain, "missing_stage_kinds": missing,
            "reason": "stage names read from the source; no prerequisite success/failure labels exist"}


def label_row(row):
    tokens = row.get("target") or []
    cells, unpaired = cells_from_tokens(tokens)
    if not cells and row.get("source"):
        cells = ["^%s^%s" % (n, d) for n, d in SRC_CELL.findall(row["source"])]
    ops = [t for t in tokens if t in OPS]
    out = {
        "labels_version": LABELS_VERSION,
        "text": row.get("text", ""),
        "cells": cells,
        "noetics": sorted({c[:2] for c in cells}),
        "operators": ops,
        "recipe": recipe_for(cells),
        "rpm": rpm_for(row.get("source")),
    }
    if unpaired:
        out["unpaired_noetics"] = unpaired
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rows = [json.loads(l) for l in open(a.src, encoding="utf-8") if l.strip()]
    labelled = [label_row(r) for r in rows]
    with open(a.out, "w", encoding="utf-8") as fh:
        for r in labelled:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_cells = sum(1 for r in labelled if r["cells"])
    n_rpm = sum(1 for r in labelled if r["rpm"]["applicable"])
    n_unpaired = sum(1 for r in labelled if r.get("unpaired_noetics"))
    print(json.dumps({"rows": len(labelled), "rows_with_cells": n_cells, "rows_with_rpm_chain": n_rpm,
                      "rows_with_unpaired_noetics": n_unpaired, "out": a.out}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

