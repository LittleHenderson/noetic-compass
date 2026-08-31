"""run_surface_baselines.py -- compute B0 (class-blind floor) and B1 (full
surface parser, the task ceiling) on the materialized train/val candidate files
and freeze the numbers into SURFACE_BASELINES_CANDIDATE.json.

Owner audit 2026-08-31 sections 5-6: B1 is expected to be exactly 1.00 -- the
task is surface-solvable by construction, and saying so with a number is what
keeps any future neural result honestly bounded. Protected B0/B1 are computed
INSIDE the single Gate 1B protected pass, never here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG / "exec"))
from baselines import score_split  # noqa: E402


def main():
    out = {"baselines_id": "SURFACE_BASELINES_CANDIDATE",
           "law": ("B0 = registered class-blind co-occurrence floor; B1 = full "
                   "deterministic surface-grammar parser reading ONLY passage "
                   "text + question text = the TASK CEILING. Frozen before any "
                   "neural result exists; the status program consumes these."),
           "splits": {}}
    for split in ("train", "val"):
        records = [json.loads(x) for x in
                   (PKG / "data" / "candidate" / f"{split}.jsonl")
                   .read_text(encoding="utf-8").splitlines()]
        out["splits"][split] = {"B0": score_split(records, "B0"),
                                "B1": score_split(records, "B1")}
        b0, b1 = out["splits"][split]["B0"], out["splits"][split]["B1"]
        print(f"{split}: B0 {b0['correct']}/{b0['total']} = {b0['overall']:.4f} | "
              f"B1 {b1['correct']}/{b1['total']} = {b1['overall']:.4f}")
        for qt, q in b0["per_question_type"].items():
            print(f"    B0 {qt}: {q['correct']}/{q['total']} = {q['accuracy']:.4f}")
    (PKG / "SURFACE_BASELINES_CANDIDATE.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
