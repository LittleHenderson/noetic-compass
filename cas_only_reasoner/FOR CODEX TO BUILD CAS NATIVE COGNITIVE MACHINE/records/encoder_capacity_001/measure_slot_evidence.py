"""Is there any per-slot evidence in the readout, or only per-slot naming?

Pure standard library. No torch, no device, no packet rebuild. Two recorded JSON files only:
`final_predictions.json` for the scores, `final_scoring.json` for the kind of each record.

The mechanism this tests
-----------------------
`encoder.py` line 212 is the whole of the slot encoding:

    result = normalize((entry["vector"] + query) / math.sqrt(2.0))

`entry["vector"]` is one vector for the entire packet; `query` is one vector for the slot. The two
are **added**. `learner._forward` line 153 then reads out

    logits = readout_rows[indexes] @ vector

which is **linear** in that sum. So for two slots s and t of the same question, with a common
packet vector p and the common readout row r for a symbol:

    logit(s, PRESENT) - logit(s, ABSENT) = (1 / sqrt(2) ||v_s||) [ d.p + d.q(s) ]
    logit(t, PRESENT) - logit(t, ABSENT) = (1 / sqrt(2) ||v_t||) [ d.p + d.q(t) ]

with the same d = readout[PRESENT] - readout[ABSENT] and the same packet term d.p in both. The
only slot-varying part is d.q(slot), and `binding._query_spec` builds q out of

    kind, field, group, scope_alias, coordinates, symbols

-- the slot's NAME and its world's ALIAS. No declaration content enters. So everything the machine
knows about the focus world's declared edge set arrives as **one constant per question**, added
identically to every slot.

The recurrence is nonlinear, so it can in principle break that tie. How far it breaks it is the
measurement.

How the slots are identified without rebuilding packets
------------------------------------------------------
A set-valued binary slot is exactly a slot whose recorded symbol set is {ABSENT, PRESENT}; an
alias-valued slot (`context.setting_ref`, `definition.*`, `analogy.world_id`) has many symbols.
Grouping the {ABSENT, PRESENT} slots **within one record** therefore isolates that record's
many-decision content with no packet access at all.

What this measures
------------------
  - the mean within-question spread of the present-minus-absent margin, over the spread across all
    of that kind's slots: 0.0 means no slot-varying evidence whatever
  - how many distinct argmax symbols one question's slots take: 1 means a constant answer
  - how often the recorded prediction is in fact constant, and how often a constant was correct
  - the same on the initial cursor, to show whether training moved it
"""

from __future__ import annotations

import json
import pathlib
from collections import Counter

RECEIPTS = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
) / "records/typed_matched_001"

BINARY = ("edge_account", "parts", "role_set", "context", "definition")


def analyse(predictions, kinds, correct):
    per_kind = {}
    for prediction in predictions:
        record_id = prediction["record_id"]
        kind = kinds.get(record_id)
        if kind is None:
            continue
        if kind in BINARY:
            selected = prediction["decisions"]["selected"]
            by_slot = {}
            for slot_id, per_symbol in prediction["scores"].items():
                if not isinstance(per_symbol, dict) or set(per_symbol) != {"ABSENT", "PRESENT"}:
                    continue
                by_slot[slot_id] = (per_symbol["PRESENT"] - per_symbol["ABSENT"], selected.get(slot_id))
            if len(by_slot) < 2:
                continue
            margins = [row[0] for row in by_slot.values()]
            chosen = [row[1] for row in by_slot.values()]
            row = per_kind.setdefault(kind, {"questions": 0, "within": 0.0, "all": [],
                                             "distinct": Counter(), "const": 0, "const_ok": 0,
                                             "slots": 0})
            row["questions"] += 1
            row["slots"] += len(margins)
            row["within"] += max(margins) - min(margins)
            row["all"].extend(margins)
            row["distinct"][len(set(chosen))] += 1
            if len(set(chosen)) == 1:
                row["const"] += 1
                row["const_ok"] += 1 if correct.get(record_id) else 0
    return per_kind


def main() -> int:
    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/artifacts/final_predictions.json").is_file()
    )
    print(f"runs: {[row.name for row in receipts]}")
    print()

    combined = {}
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        scoring = json.loads((artifacts / "final_scoring.json").read_text(encoding="utf-8"))["rows"]
        kinds = {row["record_id"]: row["kind"] for row in scoring}
        correct = {row["record_id"]: row["correct"] for row in scoring}
        print("=" * 116)
        print(f"{receipt.name}")
        print("=" * 116)
        print()
        for label, name in (("FINAL", "final_predictions.json"), ("INITIAL", "initial_predictions.json")):
            path = artifacts / name
            if not path.is_file():
                continue
            predictions = json.loads(path.read_text(encoding="utf-8"))["predictions"]
            per_kind = analyse(predictions, kinds, correct)
            print(f"  {label} cursor")
            print(f"  {'kind':>15} {'q':>4} {'slots':>6} {'within/overall spread':>22}"
                  f" {'distinct argmax per q':>24} {'constant':>9} {'constant correct':>17}")
            print("  " + "-" * 112)
            for kind in BINARY:
                row = per_kind.get(kind)
                if not row:
                    continue
                overall = max(row["all"]) - min(row["all"])
                mean_within = row["within"] / row["questions"]
                ratio = mean_within / overall if overall else float("nan")
                print(f"  {kind:>15} {row['questions']:4d} {row['slots']:6d} {ratio:22.6f}"
                      f" {str(dict(sorted(row['distinct'].items()))):>24}"
                      f" {row['const'] / row['questions']:8.2%}"
                      f" {row['const_ok'] / row['const'] if row['const'] else float('nan'):16.2%}")
                if label == "FINAL":
                    agg = combined.setdefault(kind, {"questions": 0, "slots": 0, "within": 0.0,
                                                     "const": 0, "const_ok": 0})
                    agg["questions"] += row["questions"]
                    agg["slots"] += row["slots"]
                    agg["within"] += row["within"]
                    agg["const"] += row["const"]
                    agg["const_ok"] += row["const_ok"]
            print()

    print("=" * 116)
    print("ALL SIX RUNS, FINAL CURSOR")
    print("=" * 116)
    print()
    print(f"{'kind':>15} {'q':>5} {'slots':>7} {'spread per slot':>18} {'spread per question':>21}"
          f" {'constant':>10} {'constant correct':>17}")
    print("-" * 116)
    for kind in BINARY:
        row = combined.get(kind)
        if not row:
            continue
        print(f"{kind:>15} {row['questions']:5d} {row['slots']:7d}"
              f" {row['within'] / row['slots']:18.1f} {row['within'] / row['questions']:21.1f}"
              f" {row['const'] / row['questions']:9.2%}"
              f" {row['const_ok'] / row['const'] if row['const'] else float('nan'):16.2%}")
    print()
    print("'spread per question' is the mean, over questions, of max-minus-min of the")
    print("present-minus-absent margin across that question's own binary slots.")
    print("A machine with no slot-varying evidence would show 0.0 there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
