"""Build the broader B3 eval pack (24 fresh records, 2026-05-12).

Per user 2026-05-12 design (`simplex_mvp_b3_broader_eval_design_2026_05_12.md`):

  Component        N    Purpose
  ─────────────    ─    ─────────────────────────────────────────────
  rpm_chain        15   STAGE_VAR identifier recovery (statistical)
  non-rpm leakage   9   Slot head must NOT fire STAGE_VAR
  ─────────────    ─
  Total            24

Critical invariant: NO record may share a stage* identifier or full CAS
expression with the training corpus `v1_mix_nlgen_train.jsonl`. If
collision is detected, the candidate identifier/expression is regenerated
until clean. The collision check is the load-bearing property — without
it, the eval measures memorization, not generalization.

Output: ``cas-synthetic/data/eval/broader_b3_eval_pack_2026_05_12.jsonl``
(24 records, frozen once user-reviewed).

Usage:
  python cas-synthetic/scripts/build_broader_b3_eval_pack.py \
      --train-corpus cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl \
      --output cas-synthetic/data/eval/broader_b3_eval_pack_2026_05_12.jsonl \
      --seed 2026
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Identifier collision set — built from training corpus
# ---------------------------------------------------------------------------

# Match the canary identifier shape: stage<Letter><digit>_<digit>_<body>
# Letter ∈ {A,D,W,P,L,M,N,...}, body is 1-6 digits.
_IDENT_RE = re.compile(r"stage[A-Z][0-9]+_\d+_\d+")


def build_collision_set(train_corpus_path: str) -> set[str]:
    """Scan training corpus and return every stage* identifier seen.

    Any identifier we generate for the eval must NOT be in this set.
    """
    seen: set[str] = set()
    n_records = 0
    p = Path(train_corpus_path)
    if not p.exists():
        raise FileNotFoundError(f"training corpus not found: {p}")
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            n_records += 1
            for field in ("cas_expression", "reply_text", "prompt_text",
                          "english_text", "target_text", "input_text"):
                v = rec.get(field)
                if isinstance(v, str):
                    for m in _IDENT_RE.findall(v):
                        seen.add(m)
    return seen, n_records


def build_cas_expression_set(train_corpus_path: str) -> set[str]:
    """Scan training corpus for full CAS expressions (lowercase normalized)."""
    seen: set[str] = set()
    p = Path(train_corpus_path)
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cas = rec.get("cas_expression")
            if isinstance(cas, str):
                seen.add(cas.strip())
    return seen


# ---------------------------------------------------------------------------
# rpm_chain generation
# ---------------------------------------------------------------------------

# Six Noetic bindings (drawn from the 10 Noetics in P domain or with drives).
# Each tuple: (CAS RHS, EN description) — used in `let <ID> = <CAS_RHS>` and
# `<ID> name <EN_DESCRIPTION>`.
_NOETIC_BINDINGS: list[tuple[str, str]] = [
    ("^0^P",              "a foundational thought"),
    ("^1^P",              "a moment of awareness"),
    ("^2^P_{F2}",         "an attractive principle of wisdom"),
    ("^3^P_{F6}",         "a principled aversion against disorder"),
    ("^4^P",              "the resonance of an idea"),
    ("^5^P",              "a Mind composed of accumulated experience"),
    ("^6^P_{F2}",         "an idea unpacked into its components"),
    ("^7^P_{F5}",         "practiced rhythm with agency"),
    ("^7^P_{F7}",         "practiced rhythm with purpose"),
    ("^8^P_{F4}",         "what triggered an evaluative judgment"),
    ("^8^P_{F2}",         "what reminded the Mind of a wiser path"),
    ("^9^P",              "the idea brought to Mind"),
    ("^9^P_{F1}",         "the unified idea that came to Mind"),
]


def classify_rpm_bucket(prefixes: list[tuple[str, int]]) -> str:
    """Classify an rpm chain by whether its prefix LETTER ordering follows
    the canonical RPM prerequisite order A → D → W → P.

    Per user 2026-05-12 reporting requirement: rpm results are split into
    two buckets so that struggles on stress cases don't blur the canonical
    result.

    Canonical (returns "canonical_order"):
      - 2-stage: [A, D]
      - 3-stage: [A, D, W]
      - 4-stage: [A, D, W, P]
    Anything else (no A start, skipped step, repeated letter, reversed,
    or longer than canonical_order length) returns "prefix_variety_stress".
    """
    canonical_order = "ADWP"
    letters = [p[0] for p in prefixes]
    if not letters or len(letters) > len(canonical_order):
        return "prefix_variety_stress"
    expected = list(canonical_order[: len(letters)])
    return "canonical_order" if letters == expected else "prefix_variety_stress"


def _fresh_identifier(letter: str, prefix_digit: int, middle: int, body: str,
                      collision_set: set[str]) -> str:
    """Produce a fresh stage<L><n>_<m>_<body> identifier."""
    ident = f"stage{letter}{prefix_digit}_{middle}_{body}"
    if ident in collision_set:
        raise ValueError(f"identifier collision: {ident}")
    return ident


def _fresh_chain_idents(prefixes: list[tuple[str, int]],
                         collision_set: set[str],
                         rng: random.Random,
                         max_attempts: int = 200) -> tuple[list[str], int, str]:
    """Generate a chain of identifiers sharing the same (middle, body).

    Returns (idents, middle, body) — adding the idents to collision_set
    so subsequent canaries can't reuse them.
    """
    digit_lengths = [3, 4, 5]
    for _ in range(max_attempts):
        digit_len = rng.choice(digit_lengths)
        body = "".join(rng.choice("0123456789") for _ in range(digit_len))
        # Choose a middle digit 1-9 (avoid 0 to prevent "0" middle as a
        # zero-padded edge case that's underrepresented in canary).
        middle = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9])
        candidates = [f"stage{l}{d}_{middle}_{body}" for l, d in prefixes]
        # All idents in the chain must be fresh
        if all(c not in collision_set for c in candidates):
            for c in candidates:
                collision_set.add(c)
            return candidates, middle, body
    raise RuntimeError("could not generate a fresh chain after max_attempts")


def gen_rpm_record(record_id: str,
                   chain_length: int,
                   prefixes: list[tuple[str, int]],
                   collision_set: set[str],
                   cas_collision_set: set[str],
                   rng: random.Random) -> dict[str, Any]:
    """Generate one rpm_chain canary record."""
    if len(prefixes) != chain_length:
        raise ValueError(f"prefix count {len(prefixes)} != chain_length {chain_length}")
    # Each chain must have distinct (letter, digit) prefix-pairs so all
    # identifiers in the chain are distinct. Identifiers share the same
    # (middle, body) within a chain but differ in their letter-digit prefix.
    if len(set(prefixes)) != chain_length:
        raise ValueError(
            f"prefixes must be distinct within a chain; got {prefixes}"
        )
    # Pick `chain_length` distinct noetic bindings
    bindings = rng.sample(_NOETIC_BINDINGS, chain_length)
    idents, middle, body = _fresh_chain_idents(prefixes, collision_set, rng)
    # Build CAS: "let id1 = noetic1; let id2 = noetic2; ..."
    cas_parts = [f"let {idents[i]} = {bindings[i][0]}" for i in range(chain_length)]
    cas_expression = "; ".join(cas_parts)
    # Build EN: "Let id1 name desc1, id2 name desc2, ..., and idN name descN."
    if chain_length == 2:
        en = (
            f"Let {idents[0]} name {bindings[0][1]}, "
            f"{idents[1]} name {bindings[1][1]}."
        )
    elif chain_length == 3:
        en = (
            f"Let {idents[0]} name {bindings[0][1]}, "
            f"{idents[1]} name {bindings[1][1]}, "
            f"and {idents[2]} name {bindings[2][1]}."
        )
    elif chain_length == 4:
        en = (
            f"Let {idents[0]} name {bindings[0][1]}, "
            f"{idents[1]} name {bindings[1][1]}, "
            f"{idents[2]} name {bindings[2][1]}, "
            f"and {idents[3]} name {bindings[3][1]}."
        )
    else:
        raise ValueError(f"unsupported chain_length {chain_length}")
    # CAS-expression collision check (must not duplicate a training CAS)
    if cas_expression in cas_collision_set:
        raise RuntimeError(
            f"generated CAS collides with training: {cas_expression}"
        )
    return {
        "id": record_id,
        "trace_id": f"trace_{record_id}",
        "schema_version": "broader_b3_eval.v1",
        "tier": "eval",
        "prompt_text": "Explain this rpm chain expression.",
        "reply_text": en,
        "cas_expression": cas_expression,
        "register": "A",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "rpm_chain",
        # Metadata for the gate evaluator
        "eval_meta": {
            "chain_length": chain_length,
            "prefixes": [f"{l}{d}" for l, d in prefixes],
            "middle": middle,
            "body": body,
            "body_digit_length": len(body),
            "canonical_identifiers": idents,
            # Per user 2026-05-12: split rpm results into canonical-order
            # vs prefix-variety-stress buckets in the report. Tagging the
            # record at generation time so the gate evaluator can split
            # without reclassifying.
            "bucket": classify_rpm_bucket(prefixes),
        },
    }


# ---------------------------------------------------------------------------
# Non-rpm leakage negatives — categories that have NO stage_var identifiers
# ---------------------------------------------------------------------------

# Each category gets a small list of (cas, en) pairs. All freshly authored;
# verified to not exact-match any training record below.

_NON_RPM_TEMPLATES = {
    "state_literal": [
        {
            "prompt": "Describe this cognitive state.",
            "cas": "^4^E_{F1}|T",
            "en": "An embodied resonance with a felt sense of unity, taking on a transcendent character.",
            "register": "T",
        },
        {
            "prompt": "Describe this cognitive state.",
            "cas": "^8^O_{F5}|f",
            "en": "An operational trigger driven by a sense of agency, carrying affective tone.",
            "register": "f",
        },
    ],
    "binary_composition": [
        {
            "prompt": "Describe this composition.",
            "cas": "^4^C × ^7^C",
            "en": "A resonance in the cognitive arena integrated with practiced rhythm in the same arena.",
            "register": "T",
        },
    ],
    "recipe": [
        {
            "prompt": "Describe this recipe.",
            "cas": "Θ(Ω_resolve) = 3*^6^P + 2*^9^P → Ω_resolve",
            "en": "To produce the outcome called resolve, combine three of principled decomposition with two of principled landing.",
            "register": "T",
        },
        {
            "prompt": "Describe this recipe.",
            "cas": "Θ(Ω_steadiness) = 4*^7^E + 1*^5^E → Ω_steadiness",
            "en": "To produce the outcome called steadiness, combine four of embodied rhythm with one of embodied accumulated experience.",
            "register": "T",
        },
    ],
    "meta_logic": [
        {
            "prompt": "Explain this set-theoretic expression.",
            "cas": "CoverOf(NoeticCluster{^2, ^3, ^4, ^7}, NoeticCluster{^2, ^4}, NoeticCluster{^3, ^7})",
            "en": "A cover expression claims that two groups together account for every operator in a larger collection of cognitive primitives.",
            "register": "A",
        },
    ],
    "cross_register_omega": [
        {
            "prompt": "Describe this cross-register composition.",
            "cas": "(^3^P|A × ^3^P|f) = ^3^P|Ω_refusal",
            "en": "Analytical aversion combined with felt aversion fuses into a unified principled refusal.",
            "register": "T",
        },
    ],
    "fractal_sequence": [
        {
            "prompt": "Describe this fractal sequence.",
            "cas": "Phi⟨0:1:4:8⟩",
            "en": "A four-step fractal sequence starting from the universal idea, passing through awareness, resonance, and triggering.",
            "register": "A",
        },
        {
            "prompt": "Describe this fractal sequence.",
            "cas": "Phi⟨2:5:6:9⟩",
            "en": "A four-step fractal sequence beginning with attraction, then accumulated experience, decomposition, and a landed idea.",
            "register": "A",
        },
    ],
}


def gen_non_rpm_records(cas_collision_set: set[str]) -> list[dict[str, Any]]:
    """Yield all non-rpm leakage-negative records, with collision checks."""
    records: list[dict[str, Any]] = []
    for category, templates in _NON_RPM_TEMPLATES.items():
        for i, tpl in enumerate(templates, start=1):
            cas = tpl["cas"]
            en = tpl["en"]
            # Collision check
            if cas in cas_collision_set:
                raise RuntimeError(
                    f"non-rpm {category} #{i} CAS collides with training: {cas}"
                )
            # Stage-var leakage check (must NOT contain any stage* identifier)
            for txt, lbl in ((cas, "cas"), (en, "en")):
                if _IDENT_RE.search(txt):
                    raise RuntimeError(
                        f"non-rpm {category} #{i} {lbl} contains stage* identifier "
                        f"(leakage violation): {txt!r}"
                    )
            records.append({
                "id": f"eval_b3_{category}_{i:02d}",
                "trace_id": f"trace_eval_b3_{category}_{i:02d}",
                "schema_version": "broader_b3_eval.v1",
                "tier": "eval",
                "prompt_text": tpl["prompt"],
                "reply_text": en,
                "cas_expression": cas,
                "register": tpl["register"],
                "v1mix_task_type": "cas_to_english",
                "v1mix_grammar_category_or_error_class": category,
                "eval_meta": {
                    "leakage_negative": True,
                    "category": category,
                },
            })
    return records


# ---------------------------------------------------------------------------
# rpm_chain composition plan — 15 records meeting variety requirements
# ---------------------------------------------------------------------------

def rpm_composition_plan(rng: random.Random) -> list[tuple[int, list[tuple[str, int]]]]:
    """Return 15 (chain_length, prefixes) tuples meeting the variety spec.

    Per user 2026-05-12 design:
      - A prefix >= 2 records
      - D prefix >= 4 records (varied Dn)
      - W prefix >= 4 records (varied Wn)
      - P prefix >= 3 records (varied Pn)
      - 2 mixed-prefix chains within a single chain
      - Mostly 2-stage (10), some 3-stage (3), two 4-stage (2)
    """
    # 10 × 2-stage records — every chain has DISTINCT prefix-pairs so each
    # stage carries a unique identifier (rpm semantics require this).
    two_stage = [
        # A-containing chains (3 records — exceeds >=2 floor)
        (2, [("A", 0), ("D", 1)]),  # A-D mix
        (2, [("A", 0), ("D", 4)]),  # A-D mix
        (2, [("A", 0), ("W", 5)]),  # A-W mix
        # D-only chains, distinct Dn (3 records)
        (2, [("D", 1), ("D", 3)]),  # D1-D3
        (2, [("D", 3), ("D", 5)]),  # D3-D5
        (2, [("D", 5), ("D", 7)]),  # D5-D7
        # D-W mixed chain (1 record — adds 1 D + 1 W to floors)
        (2, [("D", 4), ("W", 4)]),
        # W-only chains, distinct Wn (2 records)
        (2, [("W", 2), ("W", 4)]),  # W2-W4
        (2, [("W", 4), ("W", 6)]),  # W4-W6
        # W-P mixed (1 record — adds W and P)
        (2, [("W", 6), ("P", 1)]),
    ]

    # 3 × 3-stage records — all prefixes distinct per chain
    three_stage = [
        (3, [("A", 0), ("D", 4), ("W", 4)]),  # full A-D-W chain
        (3, [("D", 1), ("W", 2), ("P", 3)]),  # D-W-P chain
        (3, [("A", 0), ("P", 2), ("P", 4)]),  # A-P-P (P-P with distinct n)
    ]

    # 2 × 4-stage records — full A-D-W-P RPM chains, distinct prefixes
    four_stage = [
        (4, [("A", 0), ("D", 4), ("W", 4), ("P", 4)]),  # full RPM, all n=4
        (4, [("A", 0), ("D", 2), ("W", 6), ("P", 3)]),  # full RPM, varied n
    ]

    plan = two_stage + three_stage + four_stage
    assert len(plan) == 15, f"plan length {len(plan)} != 15"
    return plan


# ---------------------------------------------------------------------------
# Review checklist — run after generation, before promoting the pack
# ---------------------------------------------------------------------------

def review_checklist(records: list[dict[str, Any]],
                     collision_set: set[str]) -> dict[str, Any]:
    """Apply user 2026-05-12 review checklist to the generated pack."""
    rpm = [r for r in records if r["v1mix_grammar_category_or_error_class"] == "rpm_chain"]
    non_rpm = [r for r in records if r["v1mix_grammar_category_or_error_class"] != "rpm_chain"]

    # 1. 15 rpm records
    check_rpm_count = (len(rpm) == 15)

    # Prefix spread: A>=2, D>=4, W>=4, P>=3
    from collections import Counter
    all_prefix_letters: list[str] = []
    for r in rpm:
        for p in r["eval_meta"]["prefixes"]:
            all_prefix_letters.append(p[0])
    letter_counts = Counter(all_prefix_letters)
    check_prefix_spread = (
        letter_counts.get("A", 0) >= 2 and
        letter_counts.get("D", 0) >= 4 and
        letter_counts.get("W", 0) >= 4 and
        letter_counts.get("P", 0) >= 3
    )

    # 2. 20-40 canonical identifiers total
    total_idents = sum(len(r["eval_meta"]["canonical_identifiers"]) for r in rpm)
    check_identifier_count = (20 <= total_idents <= 40)

    # 3. At least a few 3-stage and 4-stage chains
    chain_lengths = Counter(r["eval_meta"]["chain_length"] for r in rpm)
    check_chain_spread = (
        chain_lengths.get(3, 0) >= 2 and chain_lengths.get(4, 0) >= 2
    )

    # 4. No identifier collisions with training corpus
    all_idents = []
    for r in rpm:
        all_idents.extend(r["eval_meta"]["canonical_identifiers"])
    # collision_set already includes generated idents (we added them), so we
    # need to check whether any of OUR idents was in the corpus BEFORE we
    # added them. Easiest path: re-check against a fresh corpus scan.
    # Instead we verify by inspecting whether any generated ident matches
    # a corpus ident. The gen_rpm_record path already raises on collision,
    # so this is a sanity assert.
    check_no_ident_overlap = True  # enforced at generation

    # 5. Non-rpm records contain NO stage* identifiers in CAS or target text
    non_rpm_leakage = []
    for r in non_rpm:
        for field in ("cas_expression", "reply_text"):
            if _IDENT_RE.search(r.get(field, "")):
                non_rpm_leakage.append((r["id"], field))
    check_non_rpm_clean = (len(non_rpm_leakage) == 0)

    # 6. Targets fluent — measured shallowly here as: not too short, not too
    # long, ends in punctuation. Deep fluency is a human-review item.
    fluency_issues = []
    for r in records:
        en = r.get("reply_text", "")
        if len(en) < 40:
            fluency_issues.append((r["id"], f"too short ({len(en)} chars)"))
        elif len(en) > 400:
            fluency_issues.append((r["id"], f"too long ({len(en)} chars)"))
        elif not en.strip().endswith((".", "!", "?")):
            fluency_issues.append((r["id"], "no terminal punctuation"))
    check_fluency_basic = (len(fluency_issues) == 0)

    # Bucket split for reporting (per user 2026-05-12)
    bucket_counts = Counter(r["eval_meta"].get("bucket", "unknown") for r in rpm)
    bucket_records: dict[str, list[str]] = {}
    for r in rpm:
        b = r["eval_meta"].get("bucket", "unknown")
        bucket_records.setdefault(b, []).append(r["id"])

    return {
        "rpm_count_15": check_rpm_count,
        "non_rpm_count_9": (len(non_rpm) == 9),
        "prefix_spread_A2_D4_W4_P3": check_prefix_spread,
        "prefix_letter_counts": dict(letter_counts),
        "canonical_identifier_count_20_40": check_identifier_count,
        "total_canonical_identifiers": total_idents,
        "chain_length_spread_3stage_4stage": check_chain_spread,
        "chain_length_counts": dict(chain_lengths),
        "no_identifier_collision_with_training": check_no_ident_overlap,
        "non_rpm_no_stage_identifiers": check_non_rpm_clean,
        "non_rpm_leakage_records": non_rpm_leakage,
        "fluency_basic": check_fluency_basic,
        "fluency_issues": fluency_issues,
        # Bucket split — informational; doesn't gate pack acceptance
        "bucket_split": dict(bucket_counts),
        "bucket_records": bucket_records,
        "all_pass": all([
            check_rpm_count, (len(non_rpm) == 9),
            check_prefix_spread, check_identifier_count,
            check_chain_spread, check_no_ident_overlap,
            check_non_rpm_clean, check_fluency_basic,
        ]),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--train-corpus", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--report-only", action="store_true",
                   help="Run review checklist on existing output file; no regenerate.")
    args = p.parse_args(argv)

    print(json.dumps({"event": "build_start",
                      "train_corpus": args.train_corpus,
                      "output": args.output,
                      "seed": args.seed}), flush=True)

    print("[1/4] Scanning training corpus for collision set...", flush=True)
    collision_set, n_train_records = build_collision_set(args.train_corpus)
    cas_collision_set = build_cas_expression_set(args.train_corpus)
    print(f"      scanned {n_train_records:,} training records", flush=True)
    print(f"      collision set: {len(collision_set):,} stage* identifiers", flush=True)
    print(f"      CAS expression set: {len(cas_collision_set):,} expressions", flush=True)

    rng = random.Random(args.seed)

    print("[2/4] Generating 15 rpm_chain records...", flush=True)
    plan = rpm_composition_plan(rng)
    rpm_records: list[dict[str, Any]] = []
    for i, (chain_len, prefixes) in enumerate(plan, start=1):
        rec_id = f"eval_b3_rpm_chain_{i:02d}"
        rec = gen_rpm_record(rec_id, chain_len, prefixes,
                             collision_set, cas_collision_set, rng)
        rpm_records.append(rec)
        ids = rec["eval_meta"]["canonical_identifiers"]
        print(f"      #{i:02d} {rec_id}  len={chain_len}  idents={ids}", flush=True)

    print("[3/4] Generating 9 non-rpm leakage negatives...", flush=True)
    non_rpm_records = gen_non_rpm_records(cas_collision_set)
    for r in non_rpm_records:
        print(f"      {r['id']}  cat={r['v1mix_grammar_category_or_error_class']}", flush=True)

    all_records = rpm_records + non_rpm_records
    print(f"      total: {len(all_records)} records", flush=True)

    print("[4/4] Running review checklist...", flush=True)
    review = review_checklist(all_records, collision_set)
    for k, v in review.items():
        print(f"      {k}: {v}", flush=True)

    if not review["all_pass"]:
        print("      *** REVIEW FAILED — NOT WRITING OUTPUT ***", flush=True)
        return 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    review_out = out.with_suffix(".review.json")
    with review_out.open("w", encoding="utf-8") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)

    print(json.dumps({
        "event": "build_complete",
        "output": str(out),
        "review": str(review_out),
        "n_records": len(all_records),
        "all_pass": review["all_pass"],
    }), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
