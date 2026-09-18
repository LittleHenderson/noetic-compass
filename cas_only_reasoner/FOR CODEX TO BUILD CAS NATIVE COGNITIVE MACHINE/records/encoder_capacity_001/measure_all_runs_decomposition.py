"""Does the decision-shape decomposition hold across ALL SIX runs, not just one?

Pure standard library. No torch, no device, no network, no target opened. Every number is read from
`result.json` and the scored rows that the worker already wrote.

Why this matters
----------------
The record's central measured claim — `DECISION_STRUCTURE_RESULT.md` — is that the recorded score
decomposes **exactly** by the shape of the decision each question kind requires:

    ONE DECISION                                 265 questions   11.32% -> 65.66%
    MANY INDEPENDENT DECISIONS ABOUT ONE ENTITY  299 questions    3.01% ->  5.02%

**That was measured on ONE run**: `receipt_20260919_m`. Every round since has carried the caveat
"one arm, one seed". The study ran **six** jobs — three model seeds by two arm conditions — and all
six receipts are on disk with their `initial_scoring.json` and `final_scoring.json` intact.

This script runs the same decomposition on all six and reports the spread. If the two shapes separate
the same way in every run, the claim stops being a single-run observation. If they do not, the claim
must be narrowed and this record has to say so.

The arm and seed of each receipt are read from its own `result.json`, not inferred from its name.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter

RECEIPTS = Path(__file__).resolve().parents[2] / "records/typed_matched_001"

#: Kinds whose answer is a single choice.
ONE_DECISION = ("reach", "analogy", "correspondence")

#: Kinds whose answer is one determined fact about one entity, spread over N per-slot decisions.
MANY_DECISIONS = ("edge_account", "role_set", "parts", "context", "definition")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summarise(rows: list) -> tuple:
    per_kind = Counter()
    correct = Counter()
    admissible = {}
    for row in rows:
        per_kind[row["kind"]] += 1
        correct[row["kind"]] += 1 if row["correct"] else 0
        admissible.setdefault(row["kind"], set()).add(row["admissible_answer_count"])
    return per_kind, correct, admissible


def main() -> int:
    receipts = sorted(
        directory for directory in RECEIPTS.iterdir()
        if directory.is_dir() and (directory / "collected/results/result.json").is_file()
    )
    print(f"receipts with a result.json: {len(receipts)}")
    print()

    runs = []
    for receipt in receipts:
        artifacts = receipt / "collected/results/artifacts"
        result = load(receipt / "collected/results/result.json")
        summary = result["summary"]
        initial = summarise(load(artifacts / "initial_scoring.json")["rows"])
        final = summarise(load(artifacts / "final_scoring.json")["rows"])
        retention_before = summarise(load(artifacts / "retention_before_scoring.json")["rows"])
        retention_after = summarise(load(artifacts / "retention_after_scoring.json")["rows"])
        runs.append({
            "name": receipt.name,
            "condition": summary["condition"],
            "seed": summary["model_seed"],
            "initial": initial,
            "final": final,
            "retention_before": retention_before,
            "retention_after": retention_after,
            "declared_initial": summary["initial_score"],
            "declared_final": summary["final_score"],
        })

    print("=" * 112)
    print("THE SIX RUNS")
    print("=" * 112)
    print()
    print(f"{'receipt':>22} {'condition':>24} {'seed':>10} {'initial':>10} {'final':>10} "
          f"{'declared match':>15}")
    print("-" * 112)
    for run in runs:
        per_kind, correct, _ = run["final"]
        total_kinds = sum(per_kind.values())
        total_correct = sum(correct.values())
        declared = run["declared_final"]
        matches = (total_correct == declared["correct"] and total_kinds == declared["total"])
        print(f"{run['name']:>22} {run['condition']:>24} {run['seed']:10d}"
              f" {run['declared_initial']['correct']:4d}/{run['declared_initial']['total']:<5d}"
              f" {total_correct:4d}/{total_kinds:<5d} {str(matches):>15}")
    print()

    print("=" * 112)
    print("THE DECOMPOSITION, RUN BY RUN")
    print("=" * 112)
    print()
    print(f"{'receipt':>22} {'seed':>9} {'arm':>4} | "
          f"{'ONE DECISION':>22} | {'MANY DECISIONS, ONE ENTITY':>28} | {'gap':>8}")
    print(f"{'':>22} {'':>9} {'':>4} | {'before':>10} {'after':>11} | "
          f"{'before':>12} {'after':>15} | {'after':>8}")
    print("-" * 112)
    summary_rows = []
    for run in runs:
        arm = "ALT" if run["condition"].startswith("ALT") else "MIX"
        cells = []
        for key in ("initial", "final"):
            per_kind, correct, _ = run[key]
            one_n = sum(per_kind[k] for k in ONE_DECISION)
            one_c = sum(correct[k] for k in ONE_DECISION)
            many_n = sum(per_kind[k] for k in MANY_DECISIONS)
            many_c = sum(correct[k] for k in MANY_DECISIONS)
            cells.append((one_c, one_n, many_c, many_n))
        (oi, on, mi, mn), (of, onf, mf, mnf) = cells
        one_before = oi / on if on else 0.0
        one_after = of / onf if onf else 0.0
        many_before = mi / mn if mn else 0.0
        many_after = mf / mnf if mnf else 0.0
        print(f"{run['name']:>22} {run['seed']:9d} {arm:>4} | "
              f"{100 * one_before:9.2f}% {100 * one_after:10.2f}% | "
              f"{100 * many_before:11.2f}% {100 * many_after:14.2f}% | "
              f"{100 * (one_after - many_after):7.2f}pp")
        summary_rows.append({
            "receipt": run["name"], "arm": arm, "seed": run["seed"],
            "one_before": one_before, "one_after": one_after,
            "many_before": many_before, "many_after": many_after,
        })
    print()

    print("=" * 112)
    print("ACROSS ALL SIX")
    print("=" * 112)
    print()
    one_afters = [row["one_after"] for row in summary_rows]
    many_afters = [row["many_after"] for row in summary_rows]
    gaps = [a - b for a, b in zip(one_afters, many_afters)]
    print(f"  one-decision  after : min {100 * min(one_afters):.2f}%   "
          f"max {100 * max(one_afters):.2f}%   "
          f"mean {100 * sum(one_afters) / len(one_afters):.2f}%")
    print(f"  many-decision after : min {100 * min(many_afters):.2f}%   "
          f"max {100 * max(many_afters):.2f}%   "
          f"mean {100 * sum(many_afters) / len(many_afters):.2f}%")
    print(f"  gap (one - many)    : min {100 * min(gaps):.2f}pp  max {100 * max(gaps):.2f}pp  "
          f"mean {100 * sum(gaps) / len(gaps):.2f}pp")
    print(f"  runs where one-decision exceeds many-decision: "
          f"{sum(1 for gap in gaps if gap > 0)} of {len(gaps)}")
    print()

    print("  every kind's after-rate, by run:")
    kinds = sorted({kind for run in runs for kind in run["final"][1]})
    header = f"{'kind':>15}" + "".join(f"{row['receipt'][-4:]:>10}" for row in summary_rows)
    print("  " + header)
    for kind in kinds:
        line = f"{kind:>15}"
        for run in runs:
            per_kind, correct, _ = run["final"]
            total = per_kind.get(kind, 0)
            line += f"{100 * correct.get(kind, 0) / total:9.2f}%" if total else f"{'-':>10}"
        marker = "  <- one decision" if kind in ONE_DECISION else "  <- many, one entity"
        print("  " + line + marker)
    print()

    print("=" * 112)
    print("READING")
    print("=" * 112)
    print()
    print(
        "The claim being tested is that the two shapes separate, in every run, by a wide margin.\n"
        "A single count of runs where the one-decision group leads is reported above, together with\n"
        "the worst case, because a claim that holds in six of six is a different kind of claim from\n"
        "one that holds in five."
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
