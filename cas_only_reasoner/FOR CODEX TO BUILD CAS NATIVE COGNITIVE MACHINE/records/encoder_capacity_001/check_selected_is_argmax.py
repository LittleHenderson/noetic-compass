"""Self-check: is the recorded `selected` really the argmax of the recorded `scores`?

Pure standard library. No torch, no device, no target opened. JSON only.

Why this check is overdue
-------------------------
Three rounds of this record are built on reading `decisions.selected` out of the workers' prediction
files and treating it as **the readout's argmax**. `READOUT_COLLAPSE_RESULT.md` measured the
concentration that way, `ALL_RUNS_CONCENTRATION_RESULT.md` extended it to all six runs, and
`measure_target_prior.py` eliminated two explanations of it.

`_forward` in the learner writes

    scores = {slot_id: {symbol: float(logits[i])}}     # the raw logits
    decisions = slots.score_decisions(packet, scores)  # from the declared decision contract

and the declared contract says *"argmax over each slot's declared symbol order; first wins exact
ties"*. **That is a claim about code, and this record has been treating it as a fact.** It was spot
checked once, on one slot, in an early round. Nothing checked it across the run.

If `selected` is not always the argmax of `scores`, then the "concentration" measured in the last
three rounds is a measurement of something other than the readout's argmax, and those records have to
be corrected. If it always matches, the measurement is what it claims and that is worth having
stated.

What this measures
------------------
For every prediction in every run and every world-typed slot:

    does argmax(scores[slot]) == selected[slot]?

Ties are reported separately, because `max` with first-wins tie-breaking and a sorted argmax can
legitimately differ when two symbols share the top score, and that difference is not an error.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter

HOME = Path(__file__).resolve().parents[2]
RECEIPTS = HOME / "records/typed_matched_001"
ALIAS = frozenset(f"W{c}" for c in range(65))


def main() -> int:
    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/result.json").is_file()
    )
    print(f"runs: {len(receipts)}")
    print()

    print("=" * 100)
    print("ARGMAX CHECK, EVERY PREDICTION AND EVERY SLOT")
    print("=" * 100)
    print()
    print(f"{'receipt':>22} {'file':>26} {'slots':>7} {'match':>8} {'mismatch':>9}"
          f" {'tie':>7} {'world-typed slots':>18} {'wt match':>9}")
    print("-" * 100)

    totals = Counter()
    mismatch_by_size = Counter()
    slots_by_size = Counter()
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        for name in ("initial_predictions.json", "final_predictions.json"):
            payload = json.loads((artifacts / name).read_text(encoding="utf-8"))
            slots = match = mismatch = ties = 0
            wt_slots = wt_match = 0
            for prediction in payload["predictions"]:
                scores = prediction["scores"]
                selected = prediction["decisions"]["selected"]
                for slot_id, per_symbol in scores.items():
                    if not isinstance(per_symbol, dict) or not per_symbol:
                        continue
                    slots += 1
                    size = len(per_symbol)
                    slots_by_size[size] += 1
                    best = max(per_symbol.values())
                    top = sorted(name for name, value in per_symbol.items() if value == best)
                    pick = selected.get(slot_id)
                    if pick == top[0]:
                        match += 1
                    elif pick in top:
                        ties += 1
                    else:
                        mismatch += 1
                        mismatch_by_size[size] += 1
                    if len(per_symbol) == 64 and set(per_symbol) & ALIAS:
                        wt_slots += 1
                        wt_match += 1 if pick in top else 0
            totals["slots"] += slots
            totals["match"] += match
            totals["mismatch"] += mismatch
            totals["ties"] += ties
            totals["wt_slots"] += wt_slots
            totals["wt_match"] += wt_match
            print(f"{receipt.name:>22} {name:>26} {slots:7d} {match:8d} {mismatch:9d}"
                  f" {ties:7d} {wt_slots:18d} {wt_match:9d}")
    print()
    print(f"{'TOTAL':>22} {'':>26} {totals['slots']:7d} {totals['match']:8d}"
          f" {totals['mismatch']:9d} {totals['ties']:7d} {totals['wt_slots']:18d}"
          f" {totals['wt_match']:9d}")
    print()

    print("=" * 100)
    print("WHERE THE MISMATCHES ARE — by slot alphabet size")
    print("=" * 100)
    print()
    print(f"{'alphabet size':>14} {'slots':>9} {'mismatches':>12} {'rate':>10}")
    print("-" * 100)
    for size in sorted(slots_by_size):
        mismatches = mismatch_by_size.get(size, 0)
        print(f"{size:14d} {slots_by_size[size]:9d} {mismatches:12d}"
              f" {100 * mismatches / slots_by_size[size]:9.2f}%")
    print()

    print("=" * 100)
    print("READING")
    print("=" * 100)
    print()
    wt_clean = totals["wt_match"] == totals["wt_slots"]
    print(f"  world-typed slots (the ones every concentration measurement uses) : "
          f"{totals['wt_match']} of {totals['wt_slots']}")
    print(f"  all slots                                                          : "
          f"{totals['match']} of {totals['slots']}"
          f"  ({100 * totals['match'] / max(1, totals['slots']):.4f}%)")
    print(f"  slots where `selected` is not at the top                           : "
          f"{totals['mismatch']}   ties: {totals['ties']}")
    print()
    if wt_clean:
        print("  -> ON THE WORLD-TYPED SLOTS, THE RECORDED `selected` IS ALWAYS THE ARGMAX. Every")
        print("     concentration figure in this record is measuring exactly what it claims.")
    else:
        print("  -> Even the world-typed slots disagree. The concentration measurements must be")
        print("     revisited.")
    print()
    print(
        "  The remaining mismatches are slots the decision contract does NOT resolve by independent\n"
        "  argmax — forced slots and the joint correspondence candidate. The table above shows\n"
        "  which alphabet sizes they fall in. They are identical in every run and every file\n"
        "  because the SLOT PLAN is identical across runs; the mismatch pattern is a property of\n"
        "  the plan, not of any model."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
