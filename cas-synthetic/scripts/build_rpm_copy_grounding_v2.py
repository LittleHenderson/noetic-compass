"""Build rpm_copy_grounding_v2 — Candidate E Stage 1B SDG (2026-05-12).

Generates the 5 artifacts specified in
docs/working/simplex_mvp_candidate_e_design_2026_05_12.md:

  data/path_d/rpm_copy_grounding_v2_train.jsonl           (train suffixes)
  data/path_d/rpm_copy_grounding_v2_dev.jsonl             (dev suffixes)
  data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl (dev-bucket paired)
  data/path_d/rpm_copy_grounding_v2_test.jsonl            (test suffixes)
  data/eval/rpm_copy_grounding_v2_source_swap_eval.jsonl  (test-bucket paired)

Enforces the 7 structural properties + broader-B3 reserved-eval blacklist:

  1. Disjoint suffix partitions (train 0000-7999 / dev 8000-8999 /
     test 9000-9999, similar for 3- and 5-digit bodies).
  2. Counterfactual source pairs: groups of N>=3 parallel records
     sharing EN structure + meaning, differing only in identifiers.
  3. Hard negatives: each rpm CAS source contains 1-2 distractor
     identifiers NOT in the target reply (different suffix family).
  4. Template diversification: 8 distinct EN sentence templates,
     comparable frequency.
  5. Anti-loop examples: short 2-stage chains with concise replies +
     longer chains with explicit terminal connectives.
  6. Full-span labelling: relies on Stage 1A patches (find_all_sub-
     sequences + max_cas_prefix_len=192 plumbed through trainer).
  7. Cross-chain full coverage: every identifier occurrence in the
     target reply will be labelled by the post-Stage-1A collator
     (verified by audit pass after generation).

Per Stage 1A audit cleanup: every Candidate E launch must pass
--max-cas-prefix-len 192 (records assume ~110 source tokens; 32
default truncates W/P identifiers and breaks supervision).

Usage:
  python cas-synthetic/scripts/build_rpm_copy_grounding_v2.py \\
      --output-dir cas-synthetic/data \\
      --seed 12345 \\
      --train-rpm 2000 --train-non-rpm 1000 \\
      --dev 200 --test 200 \\
      --source-swap-dev 50 --source-swap-eval 50
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Broader-B3 reserved-eval blacklist (from frozen broader_b3_eval_pack_2026_05_12)
# ---------------------------------------------------------------------------

BROADER_B3_BLACKLIST: set[str] = {
    # 3-digit
    "707", "884", "932", "978",
    # 4-digit
    "5568", "6846", "8472", "8768", "9871",
    # 5-digit
    "19672", "77848", "79730", "81399", "87663", "94055",
}


# ---------------------------------------------------------------------------
# Suffix partition
# ---------------------------------------------------------------------------

SUFFIX_RANGES = {
    "train": {
        "3digit": (0, 800),     # 000-799
        "4digit": (0, 8000),    # 0000-7999
        "5digit": (0, 80000),   # 00000-79999
    },
    "dev": {
        "3digit": (800, 900),
        "4digit": (8000, 9000),
        "5digit": (80000, 90000),
    },
    "test": {
        "3digit": (900, 1000),
        "4digit": (9000, 10000),
        "5digit": (90000, 100000),
    },
}


def gen_body(bucket: str, digit_len: int, rng: random.Random,
             max_attempts: int = 500) -> str:
    """Generate a zero-padded identifier body in the given bucket + width,
    avoiding the broader-B3 blacklist."""
    if bucket not in SUFFIX_RANGES:
        raise ValueError(f"unknown bucket {bucket!r}")
    key = f"{digit_len}digit"
    if key not in SUFFIX_RANGES[bucket]:
        raise ValueError(f"unknown digit_len {digit_len} for bucket {bucket}")
    lo, hi = SUFFIX_RANGES[bucket][key]
    for _ in range(max_attempts):
        n = rng.randrange(lo, hi)
        body = str(n).zfill(digit_len)
        if body not in BROADER_B3_BLACKLIST:
            return body
    raise RuntimeError(
        f"could not generate fresh body in bucket={bucket} digit_len={digit_len} "
        f"after {max_attempts} attempts"
    )


# ---------------------------------------------------------------------------
# Identifier helpers
# ---------------------------------------------------------------------------

STAGE_LETTERS = ["A", "D", "W", "P"]
PREFIX_DIGITS = list(range(0, 8))  # A0 always; D/W/P 0-7


def make_identifier(letter: str, prefix_digit: int, middle: int, body: str) -> str:
    return f"stage{letter}{prefix_digit}_{middle}_{body}"


# ---------------------------------------------------------------------------
# Noetic bindings & their phrase fillers (reused from existing canary pack)
# ---------------------------------------------------------------------------

# Each entry: (noetic_cas, en_phrase, drive_or_register_optional)
NOETIC_BINDINGS: list[tuple[str, str]] = [
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


# ---------------------------------------------------------------------------
# 8 EN templates (audit-required Property 4)
# Each template takes a list of (identifier, phrase) tuples for the chain
# stages, and produces a reply string.
# Templates 1-8: short / declarative / set-up / definition / etc. Variant
# orderings break the "Let stage<X> name ..." prior.
# ---------------------------------------------------------------------------

def _cap_first(s: str) -> str:
    """Uppercase ONLY the first character; preserve case elsewhere.

    Patched 2026-05-12 (B1): replaces `.capitalize()` which lowercases the
    rest of the string and corrupts CAS identifiers (stageA0 → stagea0) +
    canonical capitalized terms (Mind → mind).
    """
    return s[:1].upper() + s[1:]


def template_1(stages: list[tuple[str, str]], rng: random.Random) -> str:
    parts = [f"{ident} name {phrase}" for ident, phrase in stages]
    return "Let " + ", ".join(parts) + "."


def template_2(stages: list[tuple[str, str]], rng: random.Random) -> str:
    parts = [f"define {ident} as {phrase}" for ident, phrase in stages]
    return _cap_first(parts[0]) + "; " + "; ".join(parts[1:]) + "."


def template_3(stages: list[tuple[str, str]], rng: random.Random) -> str:
    parts = [f"{ident} represents {phrase}" for ident, phrase in stages]
    if len(parts) > 1:
        return "In this chain, " + ", ".join(parts[:-1]) + ", and " + parts[-1] + "."
    return "In this chain, " + parts[0] + "."


def template_4(stages: list[tuple[str, str]], rng: random.Random) -> str:
    parts = [f"{phrase} is named {ident}" for ident, phrase in stages]
    return _cap_first(parts[0]) + ", while " + ", ".join(parts[1:]) + "."


def template_5(stages: list[tuple[str, str]], rng: random.Random) -> str:
    parts = [f"{ident} to {phrase}" for ident, phrase in stages]
    return "The expression binds " + " and ".join(parts) + "."


def template_6(stages: list[tuple[str, str]], rng: random.Random) -> str:
    parts = [f"Identify {ident}: {phrase}" for ident, phrase in stages]
    return ". ".join(parts) + "."


def template_7(stages: list[tuple[str, str]], rng: random.Random) -> str:
    parts = [f"{ident} stands for {phrase}" for ident, phrase in stages]
    return "; ".join(parts) + "."


def template_8(stages: list[tuple[str, str]], rng: random.Random) -> str:
    parts = [f"{ident} is {phrase}" for ident, phrase in stages]
    return "Where " + ", ".join(parts[:-1]) + (" and " + parts[-1] if len(parts) > 1 else "") + "."


TEMPLATES = [template_1, template_2, template_3, template_4,
             template_5, template_6, template_7, template_8]


# ---------------------------------------------------------------------------
# CAS expression construction (with optional hard-negative distractors)
# ---------------------------------------------------------------------------

def build_cas(stages: list[tuple[str, str, str]],
              distractors: list[str] | None = None,
              rng: random.Random | None = None) -> str:
    """Build a CAS expression from (identifier, noetic_rhs, _phrase) tuples.

    Distractors are placed between let-bindings of canonical stages, NOT
    clustered together. The distractor letters/digits are sampled to look
    like plausible identifiers but their bodies must NOT appear in target.
    """
    rng = rng or random.Random(0)
    parts = []
    distractor_inserted_after = set()
    if distractors:
        n_legit = len(stages)
        if n_legit > 1:
            insert_positions = rng.sample(
                range(n_legit), min(len(distractors), n_legit)
            )
            for pos, dist_ident in zip(insert_positions, distractors):
                distractor_inserted_after.add(pos)
        else:
            distractor_inserted_after = set()

    distractor_iter = iter(distractors or [])
    for i, (ident, rhs, _phrase) in enumerate(stages):
        parts.append(f"let {ident} = {rhs}")
        if i in distractor_inserted_after:
            try:
                dist = next(distractor_iter)
                # Distractor noetic binding sampled from same pool
                dist_rhs = (rng.choice(NOETIC_BINDINGS) if rng else NOETIC_BINDINGS[0])[0]
                parts.append(f"let {dist} = {dist_rhs}")
            except StopIteration:
                pass
    # Optional trailing connective (some chains end with W -> P or similar)
    if len(stages) >= 2 and rng.random() < 0.5:
        # Use last two canonical stages
        last_w = stages[-2][0]
        last_p = stages[-1][0]
        parts.append(f"{last_w} -> {last_p}")
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Record generation
# ---------------------------------------------------------------------------

def gen_rpm_record(
    rec_id: str,
    bucket: str,
    rng: random.Random,
    chain_length: int = 4,
    template_idx: int | None = None,
    body: str | None = None,
    middle: int | None = None,
    prefix_digits: list[int] | None = None,
    include_hard_negatives: bool = True,
    binding_indices: list[int] | None = None,
    digit_len: int | None = None,
    pair_id: str | None = None,
    shared_distractors: list[str] | None = None,
) -> dict[str, Any]:
    """Generate one rpm_chain record with full structural properties."""
    if chain_length < 2 or chain_length > 4:
        raise ValueError(f"chain_length must be 2-4; got {chain_length}")
    if digit_len is None:
        digit_len = rng.choice([3, 4, 5])
    if body is None:
        body = gen_body(bucket, digit_len, rng)
    if middle is None:
        middle = rng.randint(1, 9)
    if template_idx is None:
        template_idx = rng.randint(0, len(TEMPLATES) - 1)
    if prefix_digits is None:
        # Canonical RPM ordering A0 → Dn → Wn → Pn
        prefix_digits = [0, rng.randint(1, 7), rng.randint(1, 7), rng.randint(1, 7)]
        prefix_digits = prefix_digits[:chain_length]
    letters = STAGE_LETTERS[:chain_length]
    if binding_indices is None:
        binding_indices = rng.sample(range(len(NOETIC_BINDINGS)), chain_length)

    # Build the chain
    stages: list[tuple[str, str, str]] = []
    for letter, pd, b_idx in zip(letters, prefix_digits, binding_indices):
        ident = make_identifier(letter, pd, middle, body)
        rhs, phrase = NOETIC_BINDINGS[b_idx]
        stages.append((ident, rhs, phrase))

    # Distractor identifiers (Property 3: hard negatives).
    # Patched 2026-05-12 (B3/B4): if `shared_distractors` is provided
    # (e.g. by gen_counterfactual_group), use it verbatim so every
    # variant of a counterfactual / source-swap group has the same
    # distractor set. Otherwise generate per-record.
    distractors: list[str] = []
    if shared_distractors is not None:
        distractors = list(shared_distractors)
    elif include_hard_negatives and chain_length >= 2:
        n_distractors = rng.randint(1, 2)
        for _ in range(n_distractors):
            letter = rng.choice(STAGE_LETTERS)
            pd = rng.randint(0, 7)
            mid = rng.randint(1, 9)
            dist_body = gen_body(bucket, digit_len, rng, max_attempts=500)
            attempts = 0
            while dist_body == body and attempts < 50:
                dist_body = gen_body(bucket, digit_len, rng, max_attempts=500)
                attempts += 1
            distractors.append(make_identifier(letter, pd, mid, dist_body))

    cas = build_cas(stages, distractors=distractors, rng=rng)

    # EN reply via the selected template
    template_fn = TEMPLATES[template_idx]
    en_stages = [(ident, phrase) for ident, _rhs, phrase in stages]
    en = template_fn(en_stages, rng)

    # Anti-loop: optionally add a non-looping terminal connective for longer chains
    if chain_length >= 3 and rng.random() < 0.4:
        terminal = rng.choice([
            f" {stages[-2][0]} leads to {stages[-1][0]}.",
            f" That completes the chain.",
            f" Together these stages form the path.",
        ])
        en = en.rstrip(".") + "." + terminal

    return {
        "id": rec_id,
        "trace_id": f"trace_{rec_id}",
        "schema_version": "rpm_copy_grounding_v2.v1",
        "tier": "tier3",
        "prompt_text": "Explain this rpm chain expression.",
        "reply_text": en,
        "cas_expression": cas,
        "register": "A",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "rpm_chain",
        "eval_meta": {
            "suffix_bucket": bucket,
            "body": body,
            "digit_len": digit_len,
            "chain_length": chain_length,
            "middle": middle,
            "prefixes": [f"{l}{d}" for l, d in zip(letters, prefix_digits)],
            "template_idx": template_idx,
            "canonical_identifiers": [s[0] for s in stages],
            "n_distractors": len(distractors),
            "distractors": distractors,
            "source_swap_pair_id": pair_id,
        },
    }


# ---------------------------------------------------------------------------
# Counterfactual source pairs (Property 2): N parallel records sharing
# EN structure + meaning, differing only in identifiers.
# ---------------------------------------------------------------------------

def gen_counterfactual_group(group_id: str, bucket: str, rng: random.Random,
                              n_variants: int = 3, chain_length: int = 4
                              ) -> list[dict[str, Any]]:
    """Generate N records with identical EN template, identical noetic
    bindings, identical chain structure, **identical distractor set** —
    only the canonical identifier bodies differ across variants. Patched
    2026-05-12 (B3): variants previously rolled their own distractors,
    introducing an unintended axis of variability. Now the distractor list
    is generated once at group level and passed verbatim to each variant.
    """
    template_idx = rng.randint(0, len(TEMPLATES) - 1)
    digit_len = rng.choice([3, 4, 5])
    middle = rng.randint(1, 9)
    prefix_digits = [0, rng.randint(1, 7), rng.randint(1, 7), rng.randint(1, 7)][:chain_length]
    binding_indices = rng.sample(range(len(NOETIC_BINDINGS)), chain_length)

    # Reserve canonical bodies for variants up front so distractor
    # generation won't collide with any of them.
    seen_bodies: set[str] = set()
    variant_bodies: list[str] = []
    for _ in range(n_variants):
        for _attempt in range(200):
            body = gen_body(bucket, digit_len, rng)
            if body not in seen_bodies:
                seen_bodies.add(body)
                variant_bodies.append(body)
                break
        else:
            raise RuntimeError(
                f"could not generate distinct body for cf group {group_id} "
                f"(bucket={bucket}, digit_len={digit_len}, n_variants={n_variants})"
            )

    # Group-level distractor list: same identifier strings reused across
    # all variants. Distractor bodies must differ from every variant body.
    n_distractors = rng.randint(1, 2)
    shared_distractors: list[str] = []
    for _ in range(n_distractors):
        letter = rng.choice(STAGE_LETTERS)
        pd = rng.randint(0, 7)
        mid = rng.randint(1, 9)
        for _attempt in range(200):
            dist_body = gen_body(bucket, digit_len, rng)
            if dist_body not in seen_bodies:
                seen_bodies.add(dist_body)
                shared_distractors.append(make_identifier(letter, pd, mid, dist_body))
                break
        else:
            raise RuntimeError(
                f"could not generate distinct distractor body for cf group {group_id}"
            )

    # Group-level deterministic seed so each variant's internal random
    # choices (distractor positions, trailing arrow inclusion, terminal
    # connective decision) are IDENTICAL across variants. Only the body
    # differs. Patched 2026-05-12 (B3 invariance tightening).
    import hashlib
    group_seed = int.from_bytes(
        hashlib.md5(group_id.encode("utf-8")).digest()[:4], "big",
    )

    records = []
    for i, body in enumerate(variant_bodies):
        # Fresh rng with the SAME seed for every variant; build_cas and
        # the terminal-connective decision in gen_rpm_record both consume
        # from this rng, so all variants produce structurally identical
        # CAS expressions and EN replies modulo the body suffix.
        variant_rng = random.Random(group_seed)
        rec = gen_rpm_record(
            rec_id=f"{group_id}_v{i+1}",
            bucket=bucket,
            rng=variant_rng,
            chain_length=chain_length,
            template_idx=template_idx,
            body=body,
            middle=middle,
            prefix_digits=prefix_digits,
            include_hard_negatives=True,
            binding_indices=binding_indices,
            digit_len=digit_len,
            shared_distractors=shared_distractors,
        )
        rec["eval_meta"]["counterfactual_group_id"] = group_id
        rec["eval_meta"]["counterfactual_variant_idx"] = i
        records.append(rec)
    return records


# ---------------------------------------------------------------------------
# Source-swap pair generation
# ---------------------------------------------------------------------------

def gen_source_swap_pair(pair_id: str, bucket: str, rng: random.Random,
                         chain_length: int = 4) -> list[dict[str, Any]]:
    """Generate 2 records sharing EN template + bindings + distractor
    structure, with different identifier bodies. Stage 2b / 4 source-swap
    test: same EN target, swap source identifiers → output should swap.
    Tags both records with ``source_swap_pair_id`` so the invariant audit
    can verify pair semantics directly.
    """
    pair = gen_counterfactual_group(
        group_id=pair_id, bucket=bucket, rng=rng,
        n_variants=2, chain_length=chain_length,
    )
    for rec in pair:
        rec["eval_meta"]["source_swap_pair_id"] = pair_id
    return pair


# ---------------------------------------------------------------------------
# Non-rpm baseline (category balance — keeps the model exposed to non-rpm
# behavior so slot head doesn't over-fire on rpm). Minimal: reuse existing
# template patterns from canary categories. For Stage 1B we generate small
# samples; the full corpus is comparable size to train_rpm.
# ---------------------------------------------------------------------------

def _article(noun_phrase: str) -> str:
    """Return 'A' or 'An' based on the first letter of the next word.
    Patched 2026-05-12 (B2): non-rpm templates emitted 'A aversion'
    etc. which is grammatically wrong and could teach the LM head
    a malformed article→noun pattern.
    """
    first = noun_phrase.lstrip()[:1].lower()
    return "An" if first in "aeiou" else "A"


# All 6 non-rpm leakage-negative categories: full templates per category.
# No fallback to "A foundational thought.". Codex audit 2026-05-12 finding 4:
# previous fallback narrowed full-mode coverage to state_literal +
# binary_composition only and didn't exercise the meta_logic / recipe /
# cross_register_omega / fractal_sequence categories that need to teach the
# slot head NOT to fire STAGE_VAR on these distinct surfaces.
NON_RPM_CATEGORIES: tuple[str, ...] = (
    "state_literal",
    "binary_composition",
    "recipe",
    "meta_logic",
    "cross_register_omega",
    "fractal_sequence",
)


def gen_non_rpm_record(rec_id: str, category: str, bucket: str,
                       rng: random.Random) -> dict[str, Any]:
    """Generate a non-rpm record from one of 6 categories. Reply must
    contain NO stage_var identifiers — the slot head must learn NOT to
    fire STAGE_VAR on these surfaces. Audit verifies (a) no stage_var
    pattern in cas/reply, (b) collator emits zero STAGE_VAR target spans.
    """
    if category == "state_literal":
        cas_choices = [
            "^2^C_{F4}", "^5^P_{F1}|T", "^7^O_{F5}|f",
            "^4^E_{F1}|T", "^8^O_{F5}|f", "^6^E_{F1}|A",
        ]
        desc_choices = [
            "moment of awareness", "felt resonance", "principled aversion",
            "embodied stance", "transcendent felt sense", "operational decision",
        ]
        reg_choices = ["analytical reasoning", "felt intuition",
                       "embodied action", "transcendent vision"]
        cas = rng.choice(cas_choices)
        desc = rng.choice(desc_choices)
        reg = rng.choice(reg_choices)
        en = f"{_article(desc)} {desc} expressed through {reg}."
    elif category == "binary_composition":
        cas_choices = ["^4^C × ^7^C", "^0^P × ^5^P", "^3^O × ^6^O",
                       "^2^E × ^8^E", "^6^C × ^9^C"]
        d1_choices = ["resonance in the cognitive arena",
                      "thought in principled grounding",
                      "aversion in operational behavior",
                      "attraction in the evaluative arena",
                      "decomposition in the cognitive arena"]
        d2_choices = ["practiced rhythm in the same arena",
                      "the accumulated experience that defines a Mind",
                      "decomposition into components",
                      "triggering of an associated idea",
                      "the unified result that comes to Mind"]
        cas = rng.choice(cas_choices)
        d1 = rng.choice(d1_choices)
        d2 = rng.choice(d2_choices)
        en = f"{_article(d1)} {d1} integrated with {d2}."
    elif category == "recipe":
        # v7.6 recipe surface: Θ(Ω) = a·X + b·Y → Ω
        omega_choices = ["Ω_clarity", "Ω_focus", "Ω_resilience",
                         "Ω_decision", "Ω_alignment"]
        prereqs = [
            ("0.5", "^1^P", "awareness in principled grounding"),
            ("0.3", "^2^C_{F2}", "an attractive principle of wisdom"),
            ("0.4", "^7^C_{F5}", "practiced rhythm with agency"),
            ("0.2", "^6^P_{F2}", "decomposition under wisdom"),
            ("0.5", "^4^E", "evaluative resonance"),
            ("0.6", "^5^O", "accumulated operational experience"),
        ]
        omega = rng.choice(omega_choices)
        n_terms = rng.randint(2, 3)
        chosen = rng.sample(prereqs, n_terms)
        cas_terms = [f"{c}·{rhs}" for c, rhs, _ in chosen]
        cas = f"Θ({omega}) = {' + '.join(cas_terms)} → {omega}"
        en_terms = []
        for i, (coeff, _rhs, phrase) in enumerate(chosen):
            connector = "and " if i == len(chosen) - 1 and len(chosen) > 1 else ""
            en_terms.append(f"{connector}{coeff} parts {phrase}")
        en = f"A recipe for {omega.replace('Ω_', '')} requires {', '.join(en_terms)}."
    elif category == "meta_logic":
        # v7.7 register-set / co-presence / cross-register surface
        templates = [
            ("^3^P|⟨A,f,T⟩",
             "Principled aversion present across analytical, affective, and transcendent registers."),
            ("^2^C|A + ^2^C|f",
             "Cognitive attraction co-present in analytical and affective registers."),
            ("(^7^P|A × ^7^P|f) = ^7^P|Ω",
             "Practiced rhythm integrated across analytical and affective registers into a unified result."),
            ("^4^E|⟨T,A⟩",
             "Evaluative resonance present in transcendent and analytical registers."),
            ("^5^O|f + ^5^O|E",
             "Accumulated operational experience co-present in affective and embodied registers."),
        ]
        cas, en = rng.choice(templates)
    elif category == "cross_register_omega":
        # Cross-register integration with explicit Ω result
        templates = [
            ("(^1^P|A × ^1^P|T) = ^1^P|Ω_meta",
             "Awareness integrated across analytical and transcendent registers yields meta-awareness."),
            ("(^6^C|A × ^6^C|T) = ^6^C|Ω_synthesis",
             "Cognitive decomposition integrated across analytical and transcendent registers yields synthesis."),
            ("(^2^P|f × ^2^P|E) = ^2^P|Ω_commitment",
             "Principled attraction integrated across affective and embodied registers yields commitment."),
            ("(^8^E|A × ^8^E|f) = ^8^E|Ω_insight",
             "Evaluative triggering integrated across analytical and affective registers yields insight."),
        ]
        cas, en = rng.choice(templates)
    elif category == "fractal_sequence":
        # Cognitive Fractal ⟨k₁:k₂:⋯:kₙ⟩ surface
        depths = rng.choice([3, 4, 5])
        ks = [rng.randint(0, 9) for _ in range(depths)]
        cas = f"⟨{':'.join(str(k) for k in ks)}⟩"
        depth_word = {3: "three", 4: "four", 5: "five"}[depths]
        en = (f"A cognitive fractal of {depth_word} levels with Noetic depths "
              f"{', '.join(str(k) for k in ks)}.")
    else:
        raise ValueError(f"unknown non-rpm category: {category!r}")

    return {
        "id": rec_id,
        "trace_id": f"trace_{rec_id}",
        "schema_version": "rpm_copy_grounding_v2.v1",
        "tier": "tier3",
        "prompt_text": f"Describe this {category}.",
        "reply_text": en,
        "cas_expression": cas,
        "register": "T",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": category,
        "eval_meta": {
            "suffix_bucket": bucket,
            "category": category,
            "is_non_rpm_leakage_negative": True,
        },
    }


# ---------------------------------------------------------------------------
# Post-generation audit
# ---------------------------------------------------------------------------

_IDENT_RE = re.compile(r"stage[A-Z]\d+_\d+_\d+")
# Catches lowercase-letter-after-stage (Bug B1): `stagea0_...` instead of `stageA0_...`
_LOWERCASE_IDENT_RE = re.compile(r"\bstage[a-z]\d")
# Catches "A aeiou..." article-noun mismatches; "A " followed by a word starting
# with a vowel. (Bug B2 in non-rpm templates.)
_ARTICLE_A_VOWEL_RE = re.compile(r"\bA [aeiouAEIOU]")
_ARTICLE_AN_CONSONANT_RE = re.compile(
    r"\ban [b-df-hj-np-tv-z]", re.IGNORECASE,
)
# Normalize identifier body suffix for cross-variant invariant comparison.
# `stageA0_5_41250` -> `stageA0_5_<BODY>`. Within a counterfactual group all
# canonical stages share a body and distractors share a (separate) body, so
# this normalization collapses everything that legitimately differs between
# variants and preserves everything that must match.
_IDENT_BODY_SUB_RE = re.compile(r"(stage[A-Z]\d+_\d+)_\d+")


def _normalize_identifiers(s: str) -> str:
    """Replace `_\\d+` body suffix on every stage identifier with `_<BODY>`."""
    return _IDENT_BODY_SUB_RE.sub(r"\1_<BODY>", s)


def compute_strict_collator_coverage(
    records: list[dict[str, Any]],
    tokenizer: Any,
    max_cas_prefix_len: int = 192,
) -> dict[str, Any]:
    """Run the production SimplexCollator over each record and count target
    STAGE_VAR spans vs identifier occurrences in the reply.

    Codex audit finding 2 (2026-05-12, second audit): the previous audit
    declared 'all_pass' without actually invoking the collator. The strict
    coverage rule is the load-bearing one: it verifies that find_all_sub-
    sequences + max_cas_prefix_len=192 jointly label every identifier
    occurrence in every record's target. Returns per-record findings the
    caller can fold into the overall audit.
    """
    _ensure_cas_native_importable()
    import importlib
    sc_mod = importlib.import_module(
        "cas_native.training.datasets.simplex_collator"
    )
    SimplexCollator = sc_mod.SimplexCollator
    SLOT_STAGE_VAR = sc_mod.SLOT_STAGE_VAR

    coll = SimplexCollator(
        tokenizer,
        enable_simplex_aux=True,
        max_cas_prefix_len=max_cas_prefix_len,
    )

    rpm_audited = 0
    non_rpm_audited = 0
    total_target_identifier_occurrences = 0
    total_stage_var_spans = 0
    coverage_violations: list[dict[str, Any]] = []
    non_rpm_leakage_at_collator: list[str] = []
    rpm_full_coverage_count = 0

    for r in records:
        cat = r.get("v1mix_grammar_category_or_error_class")
        en = r.get("reply_text", "")
        # Count contiguous identifier occurrences in target reply
        target_occurrences = len(_IDENT_RE.findall(en))
        try:
            batch = coll([r], device="cpu")
        except Exception as exc:
            coverage_violations.append({
                "id": r.get("id"), "error": f"collator_failed: {exc!r}",
            })
            continue
        if batch is None:
            coverage_violations.append({
                "id": r.get("id"), "error": "collator_returned_none",
            })
            continue
        tsp = batch.get("typed_slot_positions")
        if tsp is None:
            coverage_violations.append({
                "id": r.get("id"), "error": "no_typed_slot_positions",
            })
            continue
        slot_argmax = tsp[0].argmax(dim=-1)
        # Count contiguous STAGE_VAR spans
        spans = 0
        in_span = False
        L = int(slot_argmax.shape[0])
        for k in range(L):
            is_sv = int(slot_argmax[k].item()) == SLOT_STAGE_VAR
            if is_sv and not in_span:
                spans += 1
                in_span = True
            elif not is_sv:
                in_span = False
        if cat == "rpm_chain":
            rpm_audited += 1
            total_target_identifier_occurrences += target_occurrences
            total_stage_var_spans += spans
            if spans == target_occurrences and target_occurrences > 0:
                rpm_full_coverage_count += 1
            else:
                coverage_violations.append({
                    "id": r.get("id"),
                    "target_identifier_occurrences": target_occurrences,
                    "stage_var_spans_in_target": spans,
                })
        else:
            non_rpm_audited += 1
            if spans > 0:
                non_rpm_leakage_at_collator.append(r.get("id"))
    return {
        "max_cas_prefix_len": max_cas_prefix_len,
        "rpm_records_audited": rpm_audited,
        "non_rpm_records_audited": non_rpm_audited,
        "total_target_identifier_occurrences": total_target_identifier_occurrences,
        "total_stage_var_spans": total_stage_var_spans,
        "rpm_records_with_full_coverage": rpm_full_coverage_count,
        "coverage_violations": coverage_violations,
        "non_rpm_leakage_at_collator": non_rpm_leakage_at_collator,
        "all_pass": (
            not coverage_violations
            and not non_rpm_leakage_at_collator
            and (total_stage_var_spans == total_target_identifier_occurrences)
        ),
    }


def _ensure_cas_native_importable() -> None:
    """Replicate the conftest.py import shim so this script can be invoked
    standalone (outside pytest). The package directory is ``cas-native/`` —
    Python can't import a hyphenated name, so the codebase aliases it to
    ``cas_native`` via the test conftest. We do the same thing here at
    import time so the strict coverage audit can find the production
    tokenizer + SimplexCollator modules.
    """
    import sys, types
    if "cas_native" in sys.modules:
        return
    project_root = Path(__file__).resolve().parents[2]
    package_root = (
        project_root
        / "noetic-compass-scaffold" / "noetic-compass" / "cas-native"
    )
    parent_root = package_root.parent
    if not package_root.is_dir():
        raise FileNotFoundError(
            f"expected cas-native package at {package_root}; not found"
        )
    if str(parent_root) not in sys.path:
        sys.path.insert(0, str(parent_root))
    package = types.ModuleType("cas_native")
    package.__file__ = str(package_root / "__init__.py")
    package.__path__ = [str(package_root)]
    sys.modules["cas_native"] = package


def _load_production_tokenizer() -> Any:
    """Load Stage 6 v6 tokenizer.json + english_bpe.json from project root.
    Raises if either is missing — Codex audit requires the audit refuses to
    pass silently when the production tokenizer isn't available."""
    project_root = Path(__file__).resolve().parents[2]
    tk_path = project_root / "stage6_v6_artifacts" / "tokenizer.json"
    bpe_path = project_root / "stage6_v6_artifacts" / "english_bpe.json"
    if not tk_path.exists() or not bpe_path.exists():
        raise FileNotFoundError(
            f"production tokenizer artifacts not found "
            f"(expected {tk_path} and {bpe_path}); strict coverage audit "
            f"requires them. Pass --skip-strict-coverage only for laptop "
            f"smoke runs in environments without the artifacts."
        )
    _ensure_cas_native_importable()
    import importlib
    tok_mod = importlib.import_module("cas_native.training.tokenizer")
    tok = tok_mod.HybridCASTokenizer.load(str(tk_path))
    tok = tok.with_english_bpe(str(bpe_path))
    return tok


def audit_records(records: list[dict[str, Any]],
                  require_strict_coverage: bool = True,
                  tokenizer: Any | None = None,
                  max_cas_prefix_len: int = 192,
                  ) -> dict[str, Any]:
    """Run the locked audit checks across a list of records.

    Per design doc + Codex audit 2026-05-12: post-generation audit MUST use
    STRICT rule (span count EQUALS target identifier-occurrence count +
    source positions match the correct identifier). When
    ``require_strict_coverage=True``, this function now actually invokes
    SimplexCollator (via ``compute_strict_collator_coverage``) and records
    per-record coverage findings — previous behavior accepted the parameter
    but did nothing with it.
    """
    findings: dict[str, Any] = {
        "n_records": len(records),
        "blacklist_violations": [],
        "wrong_bucket_records": [],
        "rpm_count": 0,
        "non_rpm_count": 0,
        "rpm_bodies_seen": Counter(),
        "non_rpm_category_distribution": Counter(),
        "non_rpm_records_with_stage_var": [],
        "all_pass": True,
    }
    for r in records:
        meta = r.get("eval_meta", {})
        bucket = meta.get("suffix_bucket")
        cat = r.get("v1mix_grammar_category_or_error_class")
        cas = r.get("cas_expression", "")
        en = r.get("reply_text", "")
        # Blacklist check
        for body in _IDENT_RE.findall(cas + " " + en):
            # Extract body suffix (last digit group)
            body_match = re.match(r"stage[A-Z]\d+_\d+_(\d+)", body)
            if body_match:
                body_str = body_match.group(1)
                if body_str in BROADER_B3_BLACKLIST:
                    findings["blacklist_violations"].append((r.get("id"), body_str))
        # Bucket check
        if cat == "rpm_chain":
            findings["rpm_count"] += 1
            body = meta.get("body")
            if body is not None:
                findings["rpm_bodies_seen"][len(body)] += 1
            # Verify the actual body in target matches the metadata bucket
            for m in _IDENT_RE.findall(en):
                bm = re.match(r"stage[A-Z]\d+_\d+_(\d+)", m)
                if bm:
                    b = bm.group(1)
                    digit_len = len(b)
                    lo, hi = SUFFIX_RANGES.get(bucket, {}).get(f"{digit_len}digit", (-1, -1))
                    if not (lo <= int(b) < hi):
                        findings["wrong_bucket_records"].append(
                            (r.get("id"), bucket, digit_len, b)
                        )
        else:
            findings["non_rpm_count"] += 1
            findings["non_rpm_category_distribution"][cat] += 1
            # Non-rpm leakage check: no stage* in CAS or EN
            if _IDENT_RE.search(cas + " " + en):
                findings["non_rpm_records_with_stage_var"].append(r.get("id"))
    # ---- Invariant checks added 2026-05-12 per Codex audit ----
    #
    # Codex finding 3 (2026-05-12, second audit): the prefix-only invariant
    # check failed to verify that noetic bindings / template fillers actually
    # matched across variants. A future generator bug could leave prefixes
    # identical while corrupting bindings or template output, and this audit
    # would miss it. Replaced with body-normalized cas_expression and
    # reply_text comparison: after replacing `stage<L><d>_<m>_<body>` with
    # `stage<L><d>_<m>_<BODY>`, the entire CAS and reply must match across
    # variants — which is true iff noetic RHS, template, distractors, ordering,
    # and trailing connectives all match.

    # A. Counterfactual group invariants (NORMALIZED-TEXT VERSION)
    cf_violations: list[tuple[str, str, Any]] = []
    cf_groups: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        gid = r.get("eval_meta", {}).get("counterfactual_group_id")
        if gid:
            cf_groups.setdefault(gid, []).append(r)
    for gid, variants in cf_groups.items():
        if len(variants) < 2:
            continue
        ref = variants[0]
        ref_meta = ref["eval_meta"]
        ref_cas_norm = _normalize_identifiers(ref.get("cas_expression", ""))
        ref_en_norm = _normalize_identifiers(ref.get("reply_text", ""))
        seen_bodies_in_group: set[str] = {ref_meta.get("body")}
        for v in variants[1:]:
            vm = v["eval_meta"]
            v_cas_norm = _normalize_identifiers(v.get("cas_expression", ""))
            v_en_norm = _normalize_identifiers(v.get("reply_text", ""))
            if v_cas_norm != ref_cas_norm:
                cf_violations.append((gid, "cas_normalized_mismatch", {
                    "ref_prefix": ref_cas_norm[:200],
                    "got_prefix": v_cas_norm[:200],
                }))
            if v_en_norm != ref_en_norm:
                cf_violations.append((gid, "reply_normalized_mismatch", {
                    "ref_prefix": ref_en_norm[:200],
                    "got_prefix": v_en_norm[:200],
                }))
            if vm.get("body") in seen_bodies_in_group:
                cf_violations.append((gid, "body_duplication", vm.get("body")))
            seen_bodies_in_group.add(vm.get("body"))

    # B. Source-swap pair invariants — same normalized comparison; swap-pairs
    # are 2-variant counterfactual groups by construction.
    swap_violations: list[tuple[str, str, Any]] = []
    swap_pairs: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        sid = r.get("eval_meta", {}).get("source_swap_pair_id")
        if sid:
            swap_pairs.setdefault(sid, []).append(r)
    for sid, pair in swap_pairs.items():
        if len(pair) < 2:
            swap_violations.append((sid, "pair_incomplete",
                                    {"members": len(pair)}))
            continue
        ref = pair[0]
        ref_meta = ref["eval_meta"]
        ref_cas_norm = _normalize_identifiers(ref.get("cas_expression", ""))
        ref_en_norm = _normalize_identifiers(ref.get("reply_text", ""))
        for v in pair[1:]:
            vm = v["eval_meta"]
            v_cas_norm = _normalize_identifiers(v.get("cas_expression", ""))
            v_en_norm = _normalize_identifiers(v.get("reply_text", ""))
            if v_cas_norm != ref_cas_norm:
                swap_violations.append((sid, "cas_normalized_mismatch", {
                    "ref_prefix": ref_cas_norm[:200],
                    "got_prefix": v_cas_norm[:200],
                }))
            if v_en_norm != ref_en_norm:
                swap_violations.append((sid, "reply_normalized_mismatch", {
                    "ref_prefix": ref_en_norm[:200],
                    "got_prefix": v_en_norm[:200],
                }))
            if vm.get("body") == ref_meta.get("body"):
                swap_violations.append((sid, "body_not_swapped", None))

    # C. No lowercase stage[a-z] identifiers anywhere in CAS or reply.
    lowercase_ident_records: list[tuple[str, str]] = []
    for r in records:
        for field in ("cas_expression", "reply_text"):
            v = r.get(field, "")
            m = _LOWERCASE_IDENT_RE.search(v)
            if m:
                lowercase_ident_records.append((r.get("id"), m.group(0)))

    # D. Non-rpm article errors: "A " followed by vowel, or "an " followed
    #    by consonant (rough heuristic; only fires when article-noun rules
    #    are clearly violated).
    article_violations: list[tuple[str, str]] = []
    for r in records:
        if r.get("v1mix_grammar_category_or_error_class") == "rpm_chain":
            continue
        en = r.get("reply_text", "")
        if _ARTICLE_A_VOWEL_RE.search(en):
            article_violations.append((r.get("id"), f"A+vowel: {en[:80]!r}"))
        if _ARTICLE_AN_CONSONANT_RE.search(en):
            article_violations.append((r.get("id"), f"an+consonant: {en[:80]!r}"))

    findings["counterfactual_invariant_violations"] = cf_violations
    findings["counterfactual_groups_audited"] = len(cf_groups)
    findings["source_swap_pair_invariant_violations"] = swap_violations
    findings["source_swap_pairs_audited"] = len(swap_pairs)
    findings["lowercase_identifier_violations"] = lowercase_ident_records
    findings["article_violations_non_rpm"] = article_violations

    # ---- Strict collator coverage (Codex audit blocker 2 fix) -----------
    if require_strict_coverage:
        if tokenizer is None:
            tokenizer = _load_production_tokenizer()
        cov = compute_strict_collator_coverage(
            records, tokenizer=tokenizer, max_cas_prefix_len=max_cas_prefix_len,
        )
        findings["strict_collator_coverage"] = cov
    else:
        findings["strict_collator_coverage"] = {
            "skipped": True,
            "reason": "require_strict_coverage=False",
        }

    findings["all_pass"] = (
        not findings["blacklist_violations"]
        and not findings["wrong_bucket_records"]
        and not findings["non_rpm_records_with_stage_var"]
        and not findings["counterfactual_invariant_violations"]
        and not findings["source_swap_pair_invariant_violations"]
        and not findings["lowercase_identifier_violations"]
        and not findings["article_violations_non_rpm"]
        and (
            findings["strict_collator_coverage"].get("skipped")
            or findings["strict_collator_coverage"].get("all_pass", False)
        )
    )
    return findings


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="cas-synthetic/data")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--train-rpm", type=int, default=2000)
    p.add_argument("--train-non-rpm", type=int, default=1000)
    p.add_argument("--dev", type=int, default=200)
    p.add_argument("--test", type=int, default=200)
    p.add_argument("--source-swap-dev", type=int, default=50,
                   help="number of source-swap PAIRS (each pair = 2 records)")
    p.add_argument("--source-swap-eval", type=int, default=50)
    p.add_argument("--sample-only", action="store_true",
                   help="Sample-mode: generate small batch for review only "
                        "(20 rpm + 5 cf-groups + 5 swap-pairs + 5 non-rpm). "
                        "Writes to docs/working/candidate_e/sample/ instead "
                        "of the production paths.")
    p.add_argument("--dry-run", action="store_true",
                   help="Full-corpus mode with tiny sizes (10 train rpm + "
                        "10 train non-rpm, 5 dev, 5 swap-dev pairs, 5 test, "
                        "5 swap-eval pairs). All 5 artifacts written + audited. "
                        "Per Codex audit 2026-05-12: run --dry-run before any "
                        "real full corpus generation.")
    p.add_argument("--skip-strict-coverage", action="store_true",
                   help="Skip the SimplexCollator strict coverage check. "
                        "Use ONLY when production tokenizer artifacts are not "
                        "available in the environment.")
    p.add_argument("--max-cas-prefix-len", type=int, default=192,
                   help="Source token cap for strict coverage audit "
                        "(default 192 = Candidate E spec).")
    args = p.parse_args(argv)

    rng = random.Random(args.seed)

    if args.sample_only:
        print(json.dumps({"event": "sample_mode_start"}), flush=True)
        records: list[dict[str, Any]] = []
        # 20 train rpm with varied templates + chain lengths
        for i in range(20):
            chain_len = rng.choice([2, 3, 4])
            rec = gen_rpm_record(
                f"sample_train_rpm_{i:03d}", "train", rng, chain_length=chain_len
            )
            records.append(rec)
        # 5 counterfactual groups (3 variants each = 15 records)
        for i in range(5):
            group = gen_counterfactual_group(
                f"sample_cf_{i:03d}", "train", rng, n_variants=3
            )
            records.extend(group)
        # 5 source-swap pairs (2 records each = 10). source_swap_pair_id
        # is set inside gen_source_swap_pair so the audit verifies the
        # function itself, not a redundant post-loop overwrite.
        for i in range(5):
            pair = gen_source_swap_pair(
                f"sample_swap_{i:03d}", "dev", rng
            )
            records.extend(pair)
        # Sample non-rpm records: cycle through all 6 categories so the
        # sample exercises every variant the full corpus will use.
        for i in range(5):
            cat = NON_RPM_CATEGORIES[i % len(NON_RPM_CATEGORIES)]
            records.append(gen_non_rpm_record(f"sample_nonrpm_{i:03d}", cat, "train", rng))

        out_dir = Path("docs/working/candidate_e/sample")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "rpm_copy_grounding_v2_sample.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        audit = audit_records(
            records,
            require_strict_coverage=not args.skip_strict_coverage,
            max_cas_prefix_len=args.max_cas_prefix_len,
        )
        audit_path = out_dir / "rpm_copy_grounding_v2_sample.audit.json"
        with audit_path.open("w", encoding="utf-8") as f:
            json.dump(audit, f, indent=2, default=str)
        print(json.dumps({
            "event": "sample_mode_done",
            "n_records": len(records),
            "output": str(out_path),
            "audit": str(audit_path),
            "all_pass": audit["all_pass"],
            "audit_summary": {k: v for k, v in audit.items() if not isinstance(v, Counter)},
        }, default=str), flush=True)
        return 0

    # ----------------------------------------------------------------------
    # Full-corpus mode (Codex audit 2026-05-12 blocker 1 resolution).
    #
    # Writes 5 artifacts and fail-hard on any per-artifact all_pass=False.
    # --dry-run uses tiny sizes; otherwise CLI defaults / overrides apply.
    # Each artifact gets its own audit.json file alongside it.
    # ----------------------------------------------------------------------

    if args.dry_run:
        sizes = {
            "train_rpm": 10, "train_non_rpm": 10,
            "dev_rpm": 5, "test_rpm": 5,
            "source_swap_dev_pairs": 5, "source_swap_eval_pairs": 5,
        }
        mode_tag = "dry_run"
    else:
        sizes = {
            "train_rpm": args.train_rpm,
            "train_non_rpm": args.train_non_rpm,
            "dev_rpm": args.dev,
            "test_rpm": args.test,
            "source_swap_dev_pairs": args.source_swap_dev,
            "source_swap_eval_pairs": args.source_swap_eval,
        }
        mode_tag = "full"

    output_root = Path(args.output_dir)
    path_d_dir = output_root / "path_d"
    eval_dir = output_root / "eval"
    path_d_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[tuple[str, Path, list[dict[str, Any]]]] = []

    # 1. train — rpm chains (with embedded counterfactual groups) + non-rpm
    train_records: list[dict[str, Any]] = []
    # Allocate ~1/8 of rpm budget to counterfactual groups (3 variants each)
    cf_train_records = max(sizes["train_rpm"] // 8, 0)
    cf_groups_train = cf_train_records // 3
    standalone_rpm = sizes["train_rpm"] - cf_groups_train * 3
    for i in range(cf_groups_train):
        train_records.extend(gen_counterfactual_group(
            f"train_cf_{i:05d}", "train", rng, n_variants=3,
            chain_length=rng.choice([2, 3, 4]),
        ))
    for i in range(standalone_rpm):
        train_records.append(gen_rpm_record(
            f"train_rpm_{i:05d}", "train", rng,
            chain_length=rng.choice([2, 3, 4]),
        ))
    for i in range(sizes["train_non_rpm"]):
        cat = NON_RPM_CATEGORIES[i % len(NON_RPM_CATEGORIES)]
        train_records.append(gen_non_rpm_record(
            f"train_nonrpm_{i:05d}", cat, "train", rng,
        ))
    rng_state_after_train = rng.getstate()
    rng.shuffle(train_records)
    rng.setstate(rng_state_after_train)
    artifacts.append((
        "train",
        path_d_dir / "rpm_copy_grounding_v2_train.jsonl",
        train_records,
    ))

    # 2. dev — rpm chains in dev bucket (no source-swap pairs here; those
    # go in their own artifact)
    dev_records: list[dict[str, Any]] = []
    for i in range(sizes["dev_rpm"]):
        dev_records.append(gen_rpm_record(
            f"dev_rpm_{i:05d}", "dev", rng,
            chain_length=rng.choice([2, 3, 4]),
        ))
    artifacts.append((
        "dev",
        path_d_dir / "rpm_copy_grounding_v2_dev.jsonl",
        dev_records,
    ))

    # 3. source_swap_dev — paired records in dev bucket
    swap_dev_records: list[dict[str, Any]] = []
    for i in range(sizes["source_swap_dev_pairs"]):
        swap_dev_records.extend(gen_source_swap_pair(
            f"swap_dev_{i:05d}", "dev", rng,
            chain_length=rng.choice([2, 3, 4]),
        ))
    artifacts.append((
        "source_swap_dev",
        path_d_dir / "rpm_copy_grounding_v2_source_swap_dev.jsonl",
        swap_dev_records,
    ))

    # 4. test — rpm chains in test bucket
    test_records: list[dict[str, Any]] = []
    for i in range(sizes["test_rpm"]):
        test_records.append(gen_rpm_record(
            f"test_rpm_{i:05d}", "test", rng,
            chain_length=rng.choice([2, 3, 4]),
        ))
    artifacts.append((
        "test",
        path_d_dir / "rpm_copy_grounding_v2_test.jsonl",
        test_records,
    ))

    # 5. source_swap_eval — paired records in test bucket; goes under
    # data/eval/ per spec (separate dir from the data/path_d/ training mix).
    swap_eval_records: list[dict[str, Any]] = []
    for i in range(sizes["source_swap_eval_pairs"]):
        swap_eval_records.extend(gen_source_swap_pair(
            f"swap_eval_{i:05d}", "test", rng,
            chain_length=rng.choice([2, 3, 4]),
        ))
    artifacts.append((
        "source_swap_eval",
        eval_dir / "rpm_copy_grounding_v2_source_swap_eval.jsonl",
        swap_eval_records,
    ))

    # Per-artifact write + audit. Fail-hard on any all_pass=False.
    print(json.dumps({
        "event": "full_mode_start",
        "mode": mode_tag,
        "sizes": sizes,
        "n_artifacts": len(artifacts),
    }), flush=True)

    # Load tokenizer once and reuse across all artifacts to amortise the
    # ~200ms load cost. None if skipping strict coverage.
    tokenizer = None
    if not args.skip_strict_coverage:
        tokenizer = _load_production_tokenizer()

    failed_artifacts: list[str] = []
    summaries: list[dict[str, Any]] = []
    for name, out_path, recs in artifacts:
        with out_path.open("w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        audit = audit_records(
            recs,
            require_strict_coverage=not args.skip_strict_coverage,
            tokenizer=tokenizer,
            max_cas_prefix_len=args.max_cas_prefix_len,
        )
        audit_path = out_path.with_suffix(".audit.json")
        with audit_path.open("w", encoding="utf-8") as f:
            json.dump(audit, f, indent=2, default=str)
        cov = audit.get("strict_collator_coverage", {})
        summary = {
            "artifact": name,
            "path": str(out_path),
            "audit_path": str(audit_path),
            "n_records": audit["n_records"],
            "rpm_count": audit["rpm_count"],
            "non_rpm_count": audit["non_rpm_count"],
            "non_rpm_category_distribution": dict(audit["non_rpm_category_distribution"]),
            "counterfactual_groups_audited": audit["counterfactual_groups_audited"],
            "source_swap_pairs_audited": audit["source_swap_pairs_audited"],
            "strict_coverage_pass": cov.get("skipped") or cov.get("all_pass", False),
            "rpm_records_with_full_coverage": cov.get("rpm_records_with_full_coverage"),
            "rpm_records_audited": cov.get("rpm_records_audited"),
            "all_pass": audit["all_pass"],
        }
        summaries.append(summary)
        print(json.dumps({"event": "artifact_done", **summary}, default=str), flush=True)
        if not audit["all_pass"]:
            failed_artifacts.append(name)

    print(json.dumps({
        "event": "full_mode_done",
        "mode": mode_tag,
        "n_artifacts": len(artifacts),
        "failed_artifacts": failed_artifacts,
        "all_pass": not failed_artifacts,
        "summaries": summaries,
    }, default=str), flush=True)

    if failed_artifacts:
        # Fail-hard per Codex audit requirement: if any artifact has
        # all_pass=False, exit non-zero so CI / shell scripts catch it.
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
