#!/usr/bin/env python3
"""Relabel v77_rule_four records that are structurally v77_omega.

Rationale
---------

The v77_rule_four generator (pre-2026-05-02 fix) emitted two compliant
sub-arms:

  - `+` co-presence: same-Noetic register manifestations joined by `+`.
  - `×` with named emergent: `(X × Y × Z) = ^N|Ω_*`.

The second arm produces expressions structurally identical to v77_omega's
output. The recoverable Level 3 user_prompt is built from
``_formal_axis_reading(expression)``, which describes only structural
slots, so for these records the prompt carries no bucket-distinguishing
signal. Result: in the 85.1% checkpoint the model classified ALL 64
v77_rule_four records of this shape as v77_omega — and they ARE
v77_omega-shaped; the original bucket label was a generator-provenance
artifact, not a structural property.

Usage
-----

Before retraining on an existing Level 3 JSONL training file, run:

    python relabel_v77_overlap.py --in level3_train.jsonl --out level3_train_relabeled.jsonl

Records satisfying ALL of these are relabeled from ``v77_rule_four`` to
``v77_omega``:

  1. ``record["bucket"] == "v77_rule_four"``
  2. ``record["cas_expression"]`` matches ``(X × ... × Z) = ^N|Ω_*``
  3. Every ``×`` operand carries the SAME Noetic
  4. The LHS Noetic equals the RHS Noetic (i.e., it really is the same-
     Noetic ×=Ω pattern v77_omega can emit, not a different-Noetic
     integration)

A relabel-provenance field is added so the change is auditable:
``record["bucket_relabeled_from"] = "v77_rule_four"`` and
``record["bucket_relabel_reason"] = "structural_overlap_with_v77_omega"``.

The script is idempotent: running it twice on its own output is a no-op.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


# Match `(X × Y × ... × Z) = ^N[^D]|Ω_label` (or the omega_label can carry a
# domain prefix `^D|Ω_*`). Each operand of `×` is captured separately so
# the same-Noetic check can iterate them.
_OMEGA_EQ_RE = re.compile(
    r"^\s*\(\s*(?P<lhs>[^()]+?)\s*\)\s*=\s*\^(?P<rhs_noetic>[0-9])"
    r"(?:\^[PCEO])?\s*\|\s*(?:Omega|Ω)_[A-Za-z0-9_]+\s*$"
)
_OPERAND_NOETIC_RE = re.compile(r"\^([0-9])")


def _is_same_noetic_omega_emergent(expression: str) -> bool:
    """Return True iff the expression is `(X × ... × Z) = ^N|Ω_*` with
    every × operand carrying the same Noetic == RHS Noetic."""

    if "×" not in expression:
        return False
    match = _OMEGA_EQ_RE.match(expression.strip())
    if not match:
        return False
    rhs_noetic = match.group("rhs_noetic")
    lhs = match.group("lhs")

    # Split LHS on `×` (allowing flexible whitespace) and require ≥ 2 operands.
    operands = [op.strip() for op in lhs.split("×")]
    if len(operands) < 2:
        return False

    # Each operand must contain a Noetic and that Noetic must match RHS.
    for op in operands:
        m = _OPERAND_NOETIC_RE.search(op)
        if m is None or m.group(1) != rhs_noetic:
            return False
    return True


def relabel_record_if_overlap(record: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return (possibly_modified_record, was_relabeled)."""

    if record.get("bucket") != "v77_rule_four":
        return record, False
    if record.get("bucket_relabeled_from") == "v77_rule_four":
        # Already relabeled; idempotent guard.
        return record, False
    expression = str(record.get("cas_expression") or "")
    if not _is_same_noetic_omega_emergent(expression):
        return record, False

    out = dict(record)
    out["bucket"] = "v77_omega"
    out["bucket_relabeled_from"] = "v77_rule_four"
    out["bucket_relabel_reason"] = "structural_overlap_with_v77_omega"
    return out, True


def relabel_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Apply relabeling to a stream of records; return new list + counts."""

    out: list[dict[str, Any]] = []
    n_relabeled = 0
    n_v77_rule_four = 0
    for record in records:
        if record.get("bucket") == "v77_rule_four":
            n_v77_rule_four += 1
        new_record, was_relabeled = relabel_record_if_overlap(record)
        if was_relabeled:
            n_relabeled += 1
        out.append(new_record)
    return out, {
        "n_total": len(out),
        "n_v77_rule_four_input": n_v77_rule_four,
        "n_relabeled_to_v77_omega": n_relabeled,
        "n_v77_rule_four_remaining": n_v77_rule_four - n_relabeled,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="in_path", type=Path, required=True,
                        help="Input Level 3 JSONL.")
    parser.add_argument("--out", dest="out_path", type=Path, required=True,
                        help="Output JSONL with relabeling applied.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary; do not write output.")
    args = parser.parse_args(argv)

    if not args.in_path.exists():
        print(f"input not found: {args.in_path}", file=sys.stderr)
        return 2

    records: list[dict[str, Any]] = []
    with args.in_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    relabeled, counts = relabel_records(records)

    print(json.dumps({
        "in_path": str(args.in_path),
        "out_path": str(args.out_path) if not args.dry_run else None,
        "dry_run": args.dry_run,
        **counts,
    }, indent=2, sort_keys=True))

    if args.dry_run:
        return 0

    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    with args.out_path.open("w", encoding="utf-8") as f:
        for rec in relabeled:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
