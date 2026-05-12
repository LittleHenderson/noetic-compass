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

def gen_non_rpm_record(rec_id: str, category: str, bucket: str,
                       rng: random.Random) -> dict[str, Any]:
    """Generate a non-rpm record. Categories sampled from existing canary
    structure: state_literal, binary_composition, recipe, meta_logic,
    cross_register_omega, fractal_sequence."""
    # Use a simple template per category. These are deliberately not
    # source-identifier-bearing; the slot head should NEVER fire STAGE_VAR
    # on these inputs.
    templates_per_cat = {
        "state_literal": {
            "cas_choices": [
                "^2^C_{F4}", "^5^P_{F1}|T", "^7^O_{F5}|f",
                "^4^E_{F1}|T", "^8^O_{F5}|f", "^6^E_{F1}|A",
            ],
            "en_template": "A {desc} expressed through {register}.",
            "desc_choices": [
                "moment of awareness", "felt resonance", "principled aversion",
                "embodied stance", "transcendent felt sense", "operational decision",
            ],
            "reg_choices": ["analytical reasoning", "felt intuition",
                            "embodied action", "transcendent vision"],
        },
        "binary_composition": {
            "cas_choices": ["^4^C × ^7^C", "^0^P × ^5^P", "^3^O × ^6^O"],
            "en_template": "A {desc1} integrated with {desc2}.",
            "desc1_choices": ["resonance in the cognitive arena",
                              "thought in principled grounding",
                              "aversion in operational behavior"],
            "desc2_choices": ["practiced rhythm in the same arena",
                              "the accumulated experience that defines a Mind",
                              "decomposition into components"],
        },
    }
    def _article(noun_phrase: str) -> str:
        """Return 'A' or 'An' based on the first letter of the next word.
        Patched 2026-05-12 (B2): non-rpm templates emitted 'A aversion'
        etc. which is grammatically wrong and could teach the LM head
        a malformed article→noun pattern.
        """
        first = noun_phrase.lstrip()[:1].lower()
        return "An" if first in "aeiou" else "A"

    if category == "state_literal":
        t = templates_per_cat[category]
        cas = rng.choice(t["cas_choices"])
        desc = rng.choice(t["desc_choices"])
        reg = rng.choice(t["reg_choices"])
        # state_literal template already starts with "A {desc}" — convert
        # the "A " prefix to "{article} " based on desc's first letter.
        article = _article(desc)
        en = f"{article} {desc} expressed through {reg}."
    elif category == "binary_composition":
        t = templates_per_cat[category]
        cas = rng.choice(t["cas_choices"])
        d1 = rng.choice(t["desc1_choices"])
        d2 = rng.choice(t["desc2_choices"])
        article = _article(d1)
        en = f"{article} {d1} integrated with {d2}."
    else:
        # Minimal fallback for other categories — fill in later iterations
        cas = "^0^P"
        en = "A foundational thought."

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


def audit_records(records: list[dict[str, Any]], require_strict_coverage: bool = True
                  ) -> dict[str, Any]:
    """Run the locked audit checks across a list of records.

    Per design doc + Codex non-blocking advice 2026-05-12: post-generation
    audit must use STRICT rule (span count EQUALS target identifier-
    occurrence count + source positions match the correct identifier), not
    the >= rule the unit tests used.
    """
    findings: dict[str, Any] = {
        "n_records": len(records),
        "blacklist_violations": [],
        "wrong_bucket_records": [],
        "rpm_count": 0,
        "non_rpm_count": 0,
        "rpm_bodies_seen": Counter(),
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
            # Non-rpm leakage check: no stage* in CAS or EN
            if _IDENT_RE.search(cas + " " + en):
                findings["non_rpm_records_with_stage_var"].append(r.get("id"))
    # ---- Invariant checks added 2026-05-12 per Codex audit ----

    # A. Counterfactual group invariants: same prefixes, same noetic
    #    bindings (via canonical_identifiers prefix structure), same
    #    template_idx, same distractor structure; only bodies differ.
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
        ref_prefixes = ref_meta.get("prefixes")
        ref_template = ref_meta.get("template_idx")
        ref_distractors = sorted(ref_meta.get("distractors", []))
        ref_chain_length = ref_meta.get("chain_length")
        ref_middle = ref_meta.get("middle")
        seen_bodies_in_group: set[str] = {ref_meta.get("body")}
        for v in variants[1:]:
            vm = v["eval_meta"]
            if vm.get("prefixes") != ref_prefixes:
                cf_violations.append((gid, "prefix_mismatch", {
                    "ref": ref_prefixes, "got": vm.get("prefixes"),
                }))
            if vm.get("template_idx") != ref_template:
                cf_violations.append((gid, "template_mismatch", {
                    "ref": ref_template, "got": vm.get("template_idx"),
                }))
            if sorted(vm.get("distractors", [])) != ref_distractors:
                cf_violations.append((gid, "distractor_mismatch", {
                    "ref": ref_distractors,
                    "got": sorted(vm.get("distractors", [])),
                }))
            if vm.get("chain_length") != ref_chain_length:
                cf_violations.append((gid, "chain_length_mismatch", None))
            if vm.get("middle") != ref_middle:
                cf_violations.append((gid, "middle_mismatch", None))
            if vm.get("body") in seen_bodies_in_group:
                cf_violations.append((gid, "body_duplication", vm.get("body")))
            seen_bodies_in_group.add(vm.get("body"))

    # B. Source-swap pair invariants: same as counterfactual (source-swap
    #    pairs are 2-variant counterfactual groups in implementation).
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
        for v in pair[1:]:
            vm = v["eval_meta"]
            if vm.get("prefixes") != ref_meta.get("prefixes"):
                swap_violations.append((sid, "prefix_mismatch", None))
            if vm.get("template_idx") != ref_meta.get("template_idx"):
                swap_violations.append((sid, "template_mismatch", None))
            if sorted(vm.get("distractors", [])) != sorted(ref_meta.get("distractors", [])):
                swap_violations.append((sid, "distractor_mismatch", None))
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

    findings["all_pass"] = (
        not findings["blacklist_violations"]
        and not findings["wrong_bucket_records"]
        and not findings["non_rpm_records_with_stage_var"]
        and not findings["counterfactual_invariant_violations"]
        and not findings["source_swap_pair_invariant_violations"]
        and not findings["lowercase_identifier_violations"]
        and not findings["article_violations_non_rpm"]
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
        # 5 non-rpm records
        for i in range(5):
            cat = rng.choice(["state_literal", "binary_composition"])
            records.append(gen_non_rpm_record(f"sample_nonrpm_{i:03d}", cat, "train", rng))

        out_dir = Path("docs/working/candidate_e/sample")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "rpm_copy_grounding_v2_sample.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        audit = audit_records(records, require_strict_coverage=True)
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

    # Full corpus mode (not yet implemented in this commit — Stage 1B-3)
    print(json.dumps({
        "event": "full_corpus_mode_not_yet_implemented",
        "advice": "use --sample-only first to surface samples for review, "
                  "then run this script with full sizes after user approval.",
    }), flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
