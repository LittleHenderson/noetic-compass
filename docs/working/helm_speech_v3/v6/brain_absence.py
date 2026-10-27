"""Brain-side absence: what is missing, and which absence is worth raising.

The recipe brain already refuses when prerequisites are absent (G-ABSENT). But it lists *all* missing ingredients at once
— for a two-ingredient request it named 21. A mouth that reads that list aloud is unusable. This module turns the
receipt into one question, using an explicit worth-raising rule, and generates training rows whose absence labels come
from the brain rather than from a human guess.

    python brain_absence.py            # prints the rule's behaviour on sample receipts
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from helm_brain_22x40 import HELMRecipeBrain22x40   # noqa: E402

OUT = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\lacunarity_e1\data\mouth_train_brain_absence.jsonl")

# Which absences are worth a question, in priority order.
# 1. An ingredient the user named in their request but gave no amount for (a real gap in what they asked).
# 2. A staple whose absence stops the batch (Flour, Water).
# 3. Anything else the brain flags — asked about only if nothing above applies.
STAPLES = ("Flour", "Water")
PHRASING = {
    "not_on_file": [
        "I don't have a {ing} count on file — how much {ing} is there?",
        "There's no {ing} on file for this batch. How much do you have?",
        "I'm missing the {ing}. What quantity should I use?",
    ],
    "zero": [
        "You said no {ing}, and the batch needs it. Can we add some?",
        "{ing} is at zero, so the batch stops there. Is any available?",
        "Without {ing} this can't run — can we get some?",
    ],
}

SCENARIOS = [
    ("Can we bake a batch with 10 Flour and 8 Water?", {"Flour": 10, "Water": 8}, ["Sugar", "Egg"]),
    ("I've got 10 Flour but no Water — can we bake?", {"Flour": 10, "Water": 0}, ["Water"]),
    ("Can we make a batch with just 10 Flour?", {"Flour": 10}, ["Water", "Sugar"]),
    ("We have 8 Water and 10 Flour, what can we make?", {"Flour": 10, "Water": 8}, ["Sugar"]),
    ("Bake a batch from 10 Flour and 8 Water.", {"Flour": 10, "Water": 8}, ["Sugar", "Egg"]),
    ("Can we bake with 10 Flour and zero Water?", {"Flour": 10, "Water": 0}, ["Water"]),
    ("We're out of Water but have 10 Flour.", {"Flour": 10, "Water": 0}, ["Water"]),
    ("There's no Sugar left, but we have 10 Flour and 8 Water.", {"Flour": 10, "Water": 8, "Sugar": 0}, ["Sugar"]),
    ("Can we bake a batch?", {}, ["Flour"]),
    ("What can we make with 10 Flour and 8 Water?", {"Flour": 10, "Water": 8}, ["Sugar"]),
]


def ledger(brain, inputs):
    """Call the brain and normalise what it says is missing."""
    r = brain.evaluate(inputs)
    absent = []
    if r.get("status") == "UNDETERMINED" and r.get("gate_code") == "G-ABSENT":
        reason = r.get("refusal_reason") or ""
        # "Missing prerequisite ingredients: ['Water', 'Sugar', ...]"
        if "[" in reason:
            try:
                inner = reason.split("[", 1)[1].rsplit("]", 1)[0].replace("'", '"')
                absent = json.loads("[" + inner + "]")
            except Exception:
                absent = []
    return {"status": r.get("status"), "gate": r.get("gate_code"), "absent": absent,
            "limiting": r.get("limiting_reagent")}


def worth_raising(inputs, absent, requested):
    """One absence per turn, chosen by a stated rule. Returns (ingredient, kind) or None."""
    if not absent:
        return None
    # 1. a named ingredient that has no amount (not merely zero)
    for ing in requested:
        if ing in absent:
            kind = "zero" if inputs.get(ing) is not None else "not_on_file"
            return ing, kind
    # 2. a staple
    for ing in STAPLES:
        if ing in absent:
            kind = "zero" if inputs.get(ing) is not None else "not_on_file"
            return ing, kind
    # 3. the brain's own first choice
    ing = absent[0]
    return ing, ("zero" if inputs.get(ing) is not None else "not_on_file")


def rows():
    brain = HELMRecipeBrain22x40()
    rng = random.Random(20261026)
    out = []
    for user, inputs, requested in SCENARIOS:
        led = ledger(brain, inputs)
        pick = worth_raising(inputs, led["absent"], requested)
        if not pick:
            continue
        ing, kind = pick
        for i in range(6):
            target = rng.choice(PHRASING[kind]).format(ing=ing)
            out.append({"situation": "clarify 1.0", "tone": ["^1", "|f"] if i % 2 else ["^1", "|A"],
                        "input_text": user, "target": target, "style": None, "context": None,
                        "absence": ing, "absence_kind": kind, "source": "brain_absence",
                        "brain_status": led["status"], "brain_gate": led["gate"],
                        "brain_listed": led["absent"]})
    return out


def main() -> int:
    rows_ = rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows_), encoding="utf-8")
    print(json.dumps({"rows": len(rows_), "file": str(OUT)}, indent=1))
    for r in rows_[:6]:
        print("\nUSER:", r["input_text"])
        print("  brain:", r["brain_status"], r["brain_gate"], "listed", len(r["brain_listed"]))
        print("  raises:", r["absence"], r["absence_kind"], "->", r["target"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
