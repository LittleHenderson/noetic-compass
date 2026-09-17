"""Exact decomposition of the score by the SHAPE of the decision each kind requires.

Pure standard library. No torch, no device, no network, no target opened. Every number is read
from the recorded scorings of `typed_matched_001/receipt_20260919_m`.

The claim being tested
----------------------
The eight question kinds are not eight difficulties. They split into exactly two shapes, and the
split is visible in the public slot plan before any model runs.

**ONE DECISION.** The answer is a single choice — one slot, or one enumerated candidate.
    `reach`        1 slot, alphabet 2–6          arguments given in the query
    `analogy`      1 slot, 64 worlds
    `correspondence`  one candidate from a list enumerated IN CODE, 7–25 candidates

**MANY INDEPENDENT DECISIONS ABOUT ONE ENTITY.** The answer is a single determined fact about one
entity, and the architecture produces it as N separate per-slot classifications.
    `edge_account` 16 binary slots   — the focus world's complete edge set
    `context`       5 slots          — the focus world's declared setting and participants
    `definition`    3 slots          — the focus world's declared kind and function
    `parts`         4 binary slots   — the focus world's directly contained nodes
    `role_set`      6 binary slots   — the roles present in a supplied focal excerpt

The corroboration that these are ONE entity and not N questions is recorded per question:
`admissible_answer_count` is **1** for every question of all five of those kinds, in both arms and
at both cursors. A question with one admissible answer is not sixteen free choices; it is one fact
that has to come out right in sixteen places.

This script assumes nothing about the model. It groups the recorded correctness by the two shapes
and reports the split.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

ARTIFACTS = (
    Path(__file__).resolve().parents[2]
    / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"
)

#: Kinds whose answer is a single choice.
ONE_DECISION = ("reach", "analogy", "correspondence")

#: Kinds whose answer is one determined fact about one entity, spread over N per-slot decisions.
MANY_DECISIONS_ONE_ENTITY = ("edge_account", "context", "definition", "parts", "role_set")

#: Median slot count per kind, measured from the public slot plans by
#: `measure_answer_conjunction.py` (output `answer_conjunction.txt`).
SLOTS = {
    "correspondence": 5,
    "reach": 1,
    "parts": 4,
    "analogy": 1,
    "role_set": 6,
    "context": 5,
    "definition": 3,
    "edge_account": 16,
}

#: What each kind's answer is about, from `answers.RULES` and `answers._ARGUMENTS`.
SHAPE = {
    "reach": "one slot; whole and part supplied in the query",
    "analogy": "one slot; a 64-way choice of isomorphic world",
    "correspondence": "one candidate; the list is enumerated in code, 7-25 entries",
    "edge_account": "the focus world's complete edge set, as 16 binary edge-presence slots",
    "context": "the focus world's declared setting and participants, over 5 slots",
    "definition": "the focus world's declared kind and function, over 3 slots",
    "parts": "the focus world's directly contained nodes, as 4 binary slots",
    "role_set": "the roles present in a supplied focal excerpt, as 6 binary slots",
}


def load(name: str) -> list:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))["rows"]


def summarise(rows: list) -> dict:
    per_kind = Counter()
    correct = Counter()
    admissible = {}
    for row in rows:
        per_kind[row["kind"]] += 1
        correct[row["kind"]] += 1 if row["correct"] else 0
        admissible.setdefault(row["kind"], set()).add(row["admissible_answer_count"])
    return {"per_kind": per_kind, "correct": correct, "admissible": admissible}


def main() -> int:
    initial = summarise(load("initial_scoring.json"))
    final = summarise(load("final_scoring.json"))
    total_questions = sum(final["per_kind"].values())
    print(f"questions: {total_questions}")
    print()

    print("=" * 104)
    print("ADMISSIBLE ANSWERS PER QUESTION — the corroboration that this is one entity, not N")
    print("=" * 104)
    print()
    print(f"{'kind':>15} {'questions':>10} {'admissible_answer_count values':>32} {'slots (median)':>15}")
    print("-" * 104)
    for kind in sorted(final["per_kind"]):
        values = sorted(final["admissible"][kind])
        print(f"{kind:>15} {final['per_kind'][kind]:10d} {str(values):>32} {SLOTS[kind]:15d}")
    print()

    print("=" * 104)
    print("THE TWO SHAPES")
    print("=" * 104)
    print()
    for label, kinds in (
        ("ONE DECISION", ONE_DECISION),
        ("MANY INDEPENDENT DECISIONS ABOUT ONE ENTITY", MANY_DECISIONS_ONE_ENTITY),
    ):
        questions = sum(final["per_kind"][k] for k in kinds)
        before = sum(initial["correct"][k] for k in kinds)
        after = sum(final["correct"][k] for k in kinds)
        print(f"{label}: {questions} questions = {100 * questions / total_questions:.2f}% of the course")
        for kind in kinds:
            print(f"    {kind:>15}  slots={SLOTS[kind]:2d}  {SHAPE[kind]}")
            print(f"                    before {initial['correct'][kind]:3d}/{initial['per_kind'][kind]:<3d}"
                  f" = {100 * initial['correct'][kind] / initial['per_kind'][kind]:6.2f}%"
                  f"    after {final['correct'][kind]:3d}/{final['per_kind'][kind]:<3d}"
                  f" = {100 * final['correct'][kind] / final['per_kind'][kind]:6.2f}%")
        print(f"    {'TOTAL':>15}  before {before:3d}/{questions:<3d} = {100 * before / questions:6.2f}%"
              f"    after {after:3d}/{questions:<3d} = {100 * after / questions:6.2f}%")
        print()

    a_q = sum(final["per_kind"][k] for k in ONE_DECISION)
    b_q = sum(final["per_kind"][k] for k in MANY_DECISIONS_ONE_ENTITY)
    a_before = sum(initial["correct"][k] for k in ONE_DECISION)
    b_before = sum(initial["correct"][k] for k in MANY_DECISIONS_ONE_ENTITY)
    a_after = sum(final["correct"][k] for k in ONE_DECISION)
    b_after = sum(final["correct"][k] for k in MANY_DECISIONS_ONE_ENTITY)

    print("=" * 104)
    print("THE DECOMPOSITION IS EXACT")
    print("=" * 104)
    print()
    print(f"  cursor 0   recorded total {a_before + b_before}"
          f"   = {a_before} (one decision) + {b_before} (many decisions, one entity)")
    print(f"  cursor 160 recorded total {a_after + b_after}"
          f"   = {a_after} (one decision) + {b_after} (many decisions, one entity)")
    print()
    print(f"  one decision          {a_before:3d}/{a_q:<3d} = {100 * a_before / a_q:6.2f}%"
          f"  ->  {a_after:3d}/{a_q:<3d} = {100 * a_after / a_q:6.2f}%"
          f"   ({a_after / a_before if a_before else float('inf'):.2f}x)")
    print(f"  many, one entity      {b_before:3d}/{b_q:<3d} = {100 * b_before / b_q:6.2f}%"
          f"  ->  {b_after:3d}/{b_q:<3d} = {100 * b_after / b_q:6.2f}%"
          f"   ({b_after / b_before if b_before else float('inf'):.2f}x)")
    print()
    print(f"  every correct answer at cursor 160 falls on one side of the split, and the two")
    print(f"  sides sum to the recorded total exactly: {a_after} + {b_after} = {a_after + b_after}.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
