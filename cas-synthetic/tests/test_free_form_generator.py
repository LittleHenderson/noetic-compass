"""Tests for the Phase 3 free-form CAS surface generator.

Coverage (per Phase 3 task brief):

1. Lexicon well-formedness: each Noetic ^0-^9 has all five categories
   populated; no Noetic phrase set is empty; ^3 contains visceral
   vocabulary; ^2 contains attractive vocabulary; ^4 retains the
   etymological cognate.
2. Anti-drift: ^3 phrases never use audit/scrutinise/critique
   vocabulary; ^8 phrases never use deductive (therefore/thus/q.e.d.)
   vocabulary.
3. Determinism: same seed produces same output; different seeds
   produce different output.
4. Label preservation: all 12 prediction-label fields plus every
   sacred field are byte-identical between canonical and variant.
5. Compositional rendering: a co-presence expression contains
   vocabulary from BOTH constituent Noetics; an integration
   expression mentions an Omega gloss; a recipe expression mentions
   ingredient coefficients; a meta-logic expression names the
   relevant relation.
6. Robustness: empty / degenerate expressions don't crash.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from cas_synthetic.generator.free_form import (
    DOMAIN_FLAVOR,
    DRIVE_FLAVOR,
    NOETIC_LEXICON,
    REGISTER_FRAMES,
    expand_record,
    generate_free_form,
    parse_cas_expression,
)
from cas_synthetic.generator.free_form.surface_generator import (
    _AC_FORBIDDEN_RE,
    _NEG_FORBIDDEN_RE,
    SACRED_FIELDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _canonical_record(**overrides) -> dict:
    base = {
        "id": "l3conv-test-000000",
        "source_level2_id": "level2-000000",
        "bucket": "v75_register",
        "cas_expression": "^2^O_{F3}|T",
        "user_prompt": (
            "I am learning CAS. The target structure is families: "
            "state expression; states: Noetic ^2; domain O (operational); "
            "drive F3; register |T (meaning-level). What is the precise "
            "notation?"
        ),
        "natural_language_mapping": "Recoverable mapping reads ...",
        "assistant_response": "Use ^2^O_{F3}|T.",
        "follow_up_question": "Would you like a less formal phrasing?",
        "soft_operator_targets": [
            0.009091, 0.009091, 0.918182, 0.009091, 0.009091,
            0.009091, 0.009091, 0.009091, 0.009091, 0.00909,
        ],
        "soft_domain_targets": [0.009615, 0.009615, 0.009615, 0.971155],
        "tags": [
            "level3", "conversational", "v75_register",
            "recoverable_translation", "has_register",
        ],
        "provenance": {
            "level3_spec_version": "0.1.0",
            "generation_method": "deterministic_template",
            "seed": 42,
        },
        "turn_type": "ANSWER",
        "expression_family": "state_expression",
        "transition_kind": "none",
        "noetic": "2",
        "domain": "O",
        "drive": "F3",
        "register_mode": "single",
        "registers": ["T"],
        "authority": "canonical",
        "has_omega": False,
        "has_meta_logic": False,
        "meta_relations": [],
        "prior_cas_state": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Lexicon well-formedness
# ---------------------------------------------------------------------------


def test_every_noetic_has_all_five_lexicon_categories():
    expected_keys = {
        "base",
        "transcendent_modifier",
        "analytical_modifier",
        "felt_modifier",
        "embodied_modifier",
    }
    for noetic_code in (str(i) for i in range(10)):
        assert noetic_code in NOETIC_LEXICON, noetic_code
        bucket = NOETIC_LEXICON[noetic_code]
        assert expected_keys.issubset(set(bucket)), (
            f"Noetic ^{noetic_code} missing categories: "
            f"{expected_keys - set(bucket)}"
        )
        for cat, phrases in bucket.items():
            assert isinstance(phrases, tuple), (noetic_code, cat)
            assert len(phrases) >= 6, (
                f"^{noetic_code} '{cat}' has only {len(phrases)} phrases"
            )


def test_negative_lexicon_contains_visceral_vocabulary():
    """^3 base phrases must include the canonical visceral colloquialisms."""
    base = " | ".join(NOETIC_LEXICON["3"]["base"])
    visceral_anchors = ["stomach", "wrong way", "ten-foot pole", "skin"]
    hits = sum(1 for anchor in visceral_anchors if anchor in base)
    assert hits >= 3, (
        f"^3 base lexicon missing visceral anchors; saw only {hits}: "
        f"{base!r}"
    )


def test_positive_lexicon_contains_attraction_vocabulary():
    """^2 base phrases must include attraction colloquialisms."""
    base = " | ".join(NOETIC_LEXICON["2"]["base"])
    attractive_anchors = ["drawn", "speaks", "moth", "love", "leaning", "pulled"]
    hits = sum(1 for anchor in attractive_anchors if anchor in base)
    assert hits >= 3, (
        f"^2 base lexicon missing attraction anchors: {base!r}"
    )


def test_vibration_lexicon_retains_etymological_cognate():
    """^4 base phrases must mention the resonance / chord etymology."""
    base = " | ".join(NOETIC_LEXICON["4"]["base"])
    assert "chord" in base, "^4 lexicon missing 'chord' cognate"
    assert "resonate" in base or "resonates" in base, (
        "^4 lexicon missing 'resonate' cognate"
    )


def test_domain_and_drive_flavor_tables_are_populated():
    for code in ("P", "C", "E", "O"):
        assert code in DOMAIN_FLAVOR
        assert len(DOMAIN_FLAVOR[code]) >= 8, (code, len(DOMAIN_FLAVOR[code]))
    for code in (f"F{i}" for i in range(1, 8)):
        assert code in DRIVE_FLAVOR
        assert len(DRIVE_FLAVOR[code]) >= 6, (code, len(DRIVE_FLAVOR[code]))


def test_register_frames_present_for_all_four_registers():
    for register in ("T", "A", "f", "E"):
        assert register in REGISTER_FRAMES
        assert len(REGISTER_FRAMES[register]) >= 4


# ---------------------------------------------------------------------------
# 2. Anti-drift verification
# ---------------------------------------------------------------------------


def test_negative_lexicon_has_no_analytical_vocabulary():
    """^3 phrases must NEVER use audit/scrutinise/critique vocabulary."""
    for category, phrases in NOETIC_LEXICON["3"].items():
        for phrase in phrases:
            assert not _NEG_FORBIDDEN_RE.search(phrase), (
                f"^3 / {category!r} contains forbidden analytical "
                f"vocabulary: {phrase!r}"
            )


def test_above_cause_lexicon_has_no_deductive_vocabulary():
    """^8 phrases must NEVER use deductive vocabulary."""
    for category, phrases in NOETIC_LEXICON["8"].items():
        for phrase in phrases:
            assert not _AC_FORBIDDEN_RE.search(phrase), (
                f"^8 / {category!r} contains forbidden deductive "
                f"vocabulary: {phrase!r}"
            )


def test_negative_generated_surface_has_no_analytical_vocabulary():
    """End-to-end: a ^3 generated prompt must never trigger the guard."""
    expressions = [
        "^3^P_{F2}|f",
        "^3^E_{F4}|A",
        "^3^P_{F6}|T",
        "^3^O_{F3}|E",
    ]
    for expr in expressions:
        for seed in range(10):
            surface = generate_free_form(expr, seed=seed)
            assert not _NEG_FORBIDDEN_RE.search(surface), (expr, seed, surface)


def test_above_cause_generated_surface_has_no_deductive_vocabulary():
    """End-to-end: an ^8 generated prompt must never trigger the guard."""
    expressions = [
        "^8^C_{F2}|A",
        "^8^E_{F4}|f",
        "^8^P_{F6}|T",
        "^8^O_{F3}|E",
    ]
    for expr in expressions:
        for seed in range(10):
            surface = generate_free_form(expr, seed=seed)
            assert not _AC_FORBIDDEN_RE.search(surface), (expr, seed, surface)


# ---------------------------------------------------------------------------
# 3. Determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expr",
    [
        "^2^O_{F3}|T",
        "^3^E_{F2}|A",
        "^7^O_{F6}|E",
        "^4^C_{F2}|f",
        "^3^P|A + ^7^O|E",
        "(^1|E × ^1|A) = ^1|Omega_presence",
        "Theta(Omega_clarity) = 0.7*^6^C_{F2}|A + 1.4*^4^E_{F4}|f -> Omega_clarity",
        "StateCluster{^6^O} ∩ StateCluster{^6^O, ^4^P, ^8^C}",
    ],
)
def test_same_seed_gives_byte_identical_output(expr: str):
    a = generate_free_form(expr, seed=12345)
    b = generate_free_form(expr, seed=12345)
    assert a == b


def test_different_seeds_give_different_output_on_average():
    expr = "^2^O_{F3}|T"
    surfaces = {generate_free_form(expr, seed=s) for s in range(20)}
    # The lexicon is large enough that 20 seeds should produce at
    # least 5 distinct surfaces.
    assert len(surfaces) >= 5, surfaces


# ---------------------------------------------------------------------------
# 4. Label preservation
# ---------------------------------------------------------------------------


def test_expand_record_preserves_every_sacred_field():
    canonical = _canonical_record()
    variants = expand_record(canonical, k=3, seed=42)
    assert len(variants) == 3
    for variant in variants:
        for field in SACRED_FIELDS:
            if field in canonical:
                assert variant[field] == canonical[field], (
                    f"sacred field {field!r} was modified: "
                    f"{canonical[field]!r} -> {variant.get(field)!r}"
                )


def test_expand_record_only_touches_user_prompt_and_metadata():
    canonical = _canonical_record()
    variants = expand_record(canonical, k=2, seed=42)
    for variant in variants:
        diff_keys = {
            k
            for k in set(canonical) | set(variant)
            if canonical.get(k) != variant.get(k)
        }
        expected_changes = {
            "id",
            "user_prompt",
            "expansion_method",
            "seed_used",
            "provenance",
            "tags",
        }
        assert diff_keys.issubset(expected_changes), diff_keys


def test_expand_record_metadata_fields_added():
    canonical = _canonical_record()
    variants = expand_record(canonical, k=2, seed=42)
    for variant in variants:
        assert variant["expansion_method"] == "free_form_v1"
        assert isinstance(variant["seed_used"], int)
        assert "free_form" in variant["provenance"]
        assert variant["provenance"]["free_form"]["expansion_method"] == "free_form_v1"
        # CAS expression captured in provenance for diagnostic auditing.
        assert (
            variant["provenance"]["free_form"]["cas_expression_at_expansion"]
            == canonical["cas_expression"]
        )
        # Tags include phase3 / free_form_v1 markers.
        assert "phase3" in variant["tags"]
        assert "free_form_v1" in variant["tags"]


def test_expand_record_variants_have_distinct_user_prompts():
    canonical = _canonical_record()
    variants = expand_record(canonical, k=3, seed=42)
    prompts = [v["user_prompt"] for v in variants]
    assert len(set(prompts)) == 3, prompts


def test_expand_record_invalid_k_raises():
    with pytest.raises(ValueError):
        expand_record(_canonical_record(), k=0, seed=42)


# ---------------------------------------------------------------------------
# 5. Compositional rendering
# ---------------------------------------------------------------------------


def test_simple_state_renders_consistent_with_register():
    surface = generate_free_form("^2^P_{F2}|T", seed=7)
    # Transcendent register frames should appear among the openers.
    transcendent_anchors = [
        "level of meaning",
        "bigger picture",
        "whole arc",
        "deepest read",
        "matters",
        "from the meaning",
        "where I stand",
        "larger sense",
    ]
    hits = sum(1 for a in transcendent_anchors if a.lower() in surface.lower())
    assert hits >= 1, surface


def test_copresence_expression_contains_both_noetic_signatures():
    """A `^3^E|A + ^7^O|E` expression must surface both Noetic vocabularies."""
    expr = "^3^E|A + ^7^O|E"
    # Try a handful of seeds to confirm the property holds robustly.
    found_neg = False
    found_rhythm = False
    for seed in range(20):
        surface = generate_free_form(expr, seed=seed).lower()
        # ^3 signal: any aversive verb / phrase
        neg_anchors = [
            "no", "push back", "disagree", "tighten", "pull back", "say no",
            "rubs", "stomach", "skin", "leans away", "loathe", "hate",
            "off-putting", "no in", "bad taste", "no, the more", "unwilling",
        ]
        # ^7 signal: rhythm / practice / repeat / muscle memory
        rhythm_anchors = [
            "muscle memory", "practice", "every day", "routine", "rhythm",
            "drill", "groove", "loop", "cadence", "habit", "trained", "cycle",
            "rehears", "drumbeat", "drilled", "again and again",
            "over and over", "what i repeatedly",
        ]
        if any(a in surface for a in neg_anchors):
            found_neg = True
        if any(a in surface for a in rhythm_anchors):
            found_rhythm = True
        if found_neg and found_rhythm:
            break
    assert found_neg, "co-presence surface never expressed ^3 vocabulary"
    assert found_rhythm, "co-presence surface never expressed ^7 vocabulary"


def test_integration_expression_mentions_omega_gloss():
    expr = "(^1^E_{F3}|A × ^1^E_{F3}|f) = ^1^E|Omega_presence"
    saw_present = False
    for seed in range(10):
        surface = generate_free_form(expr, seed=seed).lower()
        if "present" in surface or "presence" in surface:
            saw_present = True
            break
    assert saw_present, "integration surface never mentioned the Omega gloss"


def test_recipe_expression_mentions_ingredient_coefficients():
    expr = (
        "Theta(Omega_grounded_creative_insight) = "
        "0.73*^8^C_{F3}|A + 1.42*^6^C_{F2}|A + 1.01*^4^E_{F4}|f -> "
        "Omega_grounded_creative_insight"
    )
    surface = generate_free_form(expr, seed=42)
    assert "0.73" in surface
    assert "1.42" in surface
    assert "1.01" in surface
    # Recipe opener phrase is always present:
    opener_anchors = [
        "goes into producing",
        "recipe",
        "ingredients",
        "to get to",
        "comes about by combining",
        "what it takes",
    ]
    assert any(a in surface.lower() for a in opener_anchors), surface


def test_meta_logic_expression_mentions_relation():
    expr = "StateCluster{^6^O} ∩ StateCluster{^6^O, ^4^P, ^8^C}"
    surface = generate_free_form(expr, seed=42).lower()
    relation_anchors = [
        "common", "overlap", "shared", "where they meet",
    ]
    assert any(a in surface for a in relation_anchors), surface


# ---------------------------------------------------------------------------
# 6. Robustness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expr",
    [
        "",
        "   ",
        "lol",
        "^",
        "^X^Y_{F0}|Z",
        "not a CAS expression at all",
    ],
)
def test_degenerate_expressions_do_not_crash(expr: str):
    out = generate_free_form(expr, seed=42)
    assert isinstance(out, str)
    assert len(out) > 0


def test_parser_classifies_each_shape():
    plans = {
        "simple": parse_cas_expression("^2^O_{F3}|T"),
        "copresence": parse_cas_expression("^3^P|A + ^7^O|E"),
        "integration": parse_cas_expression(
            "(^1^E|A × ^1^E|f) = ^1^E|Omega_presence"
        ),
        "recipe": parse_cas_expression(
            "Theta(Omega_clarity) = 0.7*^6^C_{F2}|A + 1.4*^4^E_{F4}|f -> Omega_clarity"
        ),
        "meta_logic": parse_cas_expression(
            "StateCluster{^6^O} ∩ StateCluster{^6^O, ^4^P, ^8^C}"
        ),
    }
    for expected, plan in plans.items():
        assert plan.shape == expected, (expected, plan.shape, plan.raw)


def test_full_corpus_smoke_does_not_crash():
    """Iterate a small slice of the canonical Level 3 corpus end-to-end."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    corpus = (
        repo_root
        / "cas-synthetic"
        / "data"
        / "level2_scaffold"
        / "level3_recoverable_full.jsonl"
    )
    if not corpus.exists():
        pytest.skip(f"canonical corpus not found at {corpus}")
    seen_buckets: set[str] = set()
    with open(corpus, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 30:  # tiny smoke
                break
            rec = json.loads(line)
            variants = expand_record(rec, k=2, seed=42)
            assert len(variants) == 2
            for variant in variants:
                assert variant["cas_expression"] == rec["cas_expression"]
                assert variant["user_prompt"] != rec["user_prompt"]
                seen_buckets.add(rec.get("bucket", "?"))
    assert seen_buckets, "no records read from canonical corpus"
