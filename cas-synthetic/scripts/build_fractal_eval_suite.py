"""v1e Phase 1B Task #135 — build the expanded fractal eval suite.

Generates ``cas-synthetic/data/path_d/v1e_phase1b_eval_suite.jsonl``
with 35 stratified fractal sources + 7 non-fractal negative controls.

Stratification (per user audit 2026-05-10):
  - k=2..8 (one bucket per k)
  - repeated values, especially ^9, ^1, ^3
  - long k=7/8
  - shared-prefix / noetic phrase ambiguity (e.g. ``Φ<8:9>``)
  - low-prose-risk short sequences

Negative controls verify the source-shape gate prevents constrained
decode from firing on non-fractal sources (recipe, meta-logic,
rpm_chain, invalid_to_explanation, binary, state_literal, CRO).

Record schema (JSONL):
  - record_id: stable id (suite + k + variant + idx)
  - category: "fractal" or "negative"
  - subcategory: stratification key for grouping in eval reports
  - cas_expression: the source CAS string
  - expected_k_values: source-parsed k-sequence (fractals only)
  - notes: free-text description of why this record is in the suite
  - source_record_id: when sampled from v1_mix_nlgen_val.jsonl

Idempotent: re-running this script regenerates the same JSONL byte-
for-byte from the same v1_mix val file. Commit the output once and
the eval driver uses it as the frozen suite source.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
VAL_PATH = REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "v1_mix_nlgen_val.jsonl"
OUT_PATH = REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "v1e_phase1b_eval_suite.jsonl"


def _fractal_record(idx: int, k: int, subcategory: str, k_values: tuple[int, ...], notation: str, notes: str) -> dict:
    """Build one synthesized fractal record. ``notation`` is "Φ" or
    "Phi" — we use a 50/50 mix per k bucket to exercise both code paths
    in ``parse_fractal``."""
    body = ":".join(str(v) for v in k_values)
    cas = f"{notation}<{body}>"
    return {
        "record_id": f"v1e_eval_fractal_k{k}_{subcategory}_{idx:02d}",
        "category": "fractal",
        "subcategory": subcategory,
        "cas_expression": cas,
        "expected_k_values": list(k_values),
        "notes": notes,
        "source_record_id": None,
    }


# Curated suite. 5 records per k bucket × 7 buckets = 35 fractal records.
# Each k bucket has at least one entry from each variant where applicable:
#   - "diverse"       — all distinct k values, no repeats
#   - "one_repeat"    — exactly one pair of repeated k values
#   - "extreme_9"     — many consecutive ^9 (tests v1d Record 13 loop pattern)
#   - "extreme_1"     — many consecutive ^1 (paying attention chain)
#   - "extreme_3"     — many consecutive ^3 (aversion chain)
#   - "shared_prefix" — adjacent k values whose phrases share prefix tokens
#   - "regression_13" / "regression_15" — exact reproductions of v1d audit
#     records 13 and 15 to lock down regression risk on those.

FRACTAL_SPECS: list[tuple[int, str, tuple[int, ...], str, str]] = [
    # k=2 (low-prose-risk short)
    (2, "diverse", (3, 7), "Φ", "Record 14 canonical short fractal: negative -> rhythm"),
    (2, "shared_prefix", (8, 9), "Phi", "shared-prefix ambiguity: ^8 'memory trigger' vs ^9 'popped'"),
    (2, "shared_concept", (5, 6), "Φ", "abstract-concept ambiguity: ^5 'experience' vs ^6 'unpacking'"),
    (2, "diverse", (2, 3), "Phi", "involution pair: positive -> negative"),
    (2, "diverse", (0, 9), "Φ", "idea -> effect (associative chain)"),
    # k=3
    (3, "diverse", (1, 2, 3), "Φ", "mind -> positive -> negative"),
    (3, "extreme_9", (9, 9, 9), "Phi", "3-in-a-row ^9 (popped/clicked chain)"),
    (3, "extreme_1", (1, 1, 1), "Φ", "3-in-a-row ^1 (paying attention chain)"),
    (3, "extreme_3", (3, 3, 3), "Phi", "3-in-a-row ^3 (aversion chain)"),
    (3, "diverse", (8, 6, 9), "Φ", "cause -> male -> effect (analytical chain)"),
    # k=4
    (4, "diverse", (5, 6, 7, 8), "Φ", "v7.6 axes: female-male-rhythm-cause"),
    (4, "extreme_9", (9, 9, 9, 9), "Phi", "4-in-a-row ^9 (heavier loop test)"),
    (4, "diverse", (1, 2, 3, 4), "Φ", "sequential noetic chain"),
    (4, "one_repeat", (3, 5, 3, 5), "Phi", "alternating ^3/^5 (aversion/experience)"),
    (4, "diverse", (0, 1, 2, 3), "Φ", "idea-grounded sequential"),
    # k=5
    (5, "diverse", (1, 2, 3, 4, 5), "Φ", "5-step diverse sequential"),
    (5, "one_repeat", (9, 9, 5, 9, 9), "Phi", "^9 surrounding ^5 (anchored loop)"),
    (5, "one_repeat", (0, 0, 0, 1, 0), "Φ", "early-^0-dominant pattern"),
    (5, "extreme_5", (5, 5, 5, 5, 5), "Phi", "5-in-a-row ^5 (sum-of-experiences chain)"),
    (5, "diverse", (6, 7, 8, 9, 0), "Φ", "descending-to-zero sequential"),
    # k=6
    (6, "diverse", (1, 2, 3, 4, 5, 6), "Φ", "6-step diverse sequential"),
    (6, "extreme_5", (5, 5, 5, 5, 5, 5), "Phi", "6-in-a-row ^5"),
    (6, "extreme_9", (9, 9, 9, 9, 9, 9), "Φ", "6-in-a-row ^9 (canonical loop)"),
    (6, "alternating", (0, 9, 0, 9, 0, 9), "Phi", "alternating ^0/^9"),
    (6, "alternating", (3, 7, 3, 7, 3, 7), "Φ", "alternating ^3/^7 (Record 14 pattern x3)"),
    # k=7 (long)
    (7, "diverse", (1, 2, 3, 4, 5, 6, 7), "Φ", "7-step diverse sequential"),
    (7, "lead_9", (9, 1, 2, 3, 4, 5, 6), "Phi", "^9 lead, then descending diverse"),
    (7, "diverse", (8, 9, 7, 0, 9, 5, 2), "Φ", "smoke-style mixed-repeat n=7"),
    (7, "extreme_3", (3, 3, 3, 3, 3, 3, 3), "Phi", "7-in-a-row ^3 (heavy aversion test)"),
    (7, "extreme_0", (0, 0, 0, 0, 0, 0, 0), "Φ", "7-in-a-row ^0 (idea-anchored)"),
    # k=8 (long; includes regression checks on v1d Record 13/15)
    (8, "regression_13", (6, 9, 7, 0, 9, 5, 2, 0), "Phi", "v1d Record 13 exact regression check"),
    (8, "regression_15", (1, 0, 3, 3, 1, 1, 7, 5), "Φ", "v1d Record 15 exact regression check"),
    (8, "extreme_8", (8, 8, 8, 8, 8, 8, 8, 8), "Phi", "8-in-a-row ^8 (cause chain)"),
    (8, "diverse", (1, 2, 3, 4, 5, 6, 7, 8), "Φ", "8-step full sequential"),
    (8, "block_repeats", (9, 9, 9, 9, 1, 1, 1, 1), "Phi", "block repeats ^9 then ^1"),
]


def _load_negatives_from_val() -> list[dict]:
    """Pull one record per non-fractal category from v1_mix_nlgen_val.jsonl
    to use as negative controls. The eval driver verifies that
    apply_fractal_decoder=True produces byte-identical output to
    apply_fractal_decoder=False for these — source-shape gate must
    suppress the constrained path."""
    val_records: list[dict] = []
    if not VAL_PATH.exists():
        return val_records
    with VAL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                val_records.append(json.loads(line))

    # Target categories the source-shape gate must NOT fire on.
    # Pick the FIRST record encountered per category for determinism.
    target_categories = [
        ("cas_to_english", "state_literal"),
        ("cas_to_english", "binary_composition"),
        ("cas_to_english", "cross_register_omega"),
        ("cas_to_english", "recipe"),
        ("cas_to_english", "meta_logic_relation"),
        ("cas_to_english", "rpm_chain"),
        ("invalid_to_explanation", "rpm"),
    ]
    negatives: list[dict] = []
    for (task, cat) in target_categories:
        chosen = None
        for r in val_records:
            if (
                r.get("v1mix_task_type") == task
                and r.get("v1mix_grammar_category_or_error_class") == cat
            ):
                chosen = r
                break
        if chosen is None:
            print(f"[warn] no val record for {task}/{cat}; skipping negative control")
            continue
        negatives.append({
            "record_id": f"v1e_eval_negative_{cat}",
            "category": "negative",
            "subcategory": cat,
            "cas_expression": chosen["cas_expression"],
            "expected_k_values": None,
            "notes": f"negative control: {task}/{cat}; verifies source-shape gate",
            "source_record_id": chosen.get("id"),
        })
    return negatives


def main() -> int:
    out: list[dict] = []
    for i, (k, subcategory, k_values, notation, notes) in enumerate(FRACTAL_SPECS):
        out.append(_fractal_record(i, k, subcategory, k_values, notation, notes))
    negatives = _load_negatives_from_val()
    out.extend(negatives)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    fractal_count = sum(1 for r in out if r["category"] == "fractal")
    negative_count = sum(1 for r in out if r["category"] == "negative")
    print(f"wrote {OUT_PATH}")
    print(f"  fractal records:  {fractal_count}")
    print(f"  negative records: {negative_count}")
    print(f"  total:            {len(out)}")
    # Per-k distribution for fractals.
    by_k: dict[int, int] = {}
    for r in out:
        if r["category"] != "fractal":
            continue
        k = len(r["expected_k_values"])
        by_k[k] = by_k.get(k, 0) + 1
    print(f"  per-k fractal counts: {dict(sorted(by_k.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
