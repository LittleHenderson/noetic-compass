"""Tests for the Stage 7 v7.1 damage detector — the 6 Phase-C signatures."""
from __future__ import annotations

import pytest

from cas_native.evaluation.damage_detector import (
    aggregate_pack_verdict,
    analyze_sample,
)


# ---------------------------------------------------------------------------
# 1. Repeated phrase loops
# ---------------------------------------------------------------------------

def test_clean_text_no_repeat():
    r = analyze_sample("This is a normal English sentence that does not repeat.")
    assert r.signatures["repeated_phrase_loop"]["found"] is False


def test_simple_word_repeat_loop():
    r = analyze_sample("the the the the cat sat")
    assert r.signatures["repeated_phrase_loop"]["found"] is True
    assert r.signatures["repeated_phrase_loop"]["count"] >= 3


def test_two_gram_repeat_loop():
    r = analyze_sample("foo bar foo bar foo bar baz")
    assert r.signatures["repeated_phrase_loop"]["found"] is True
    assert r.signatures["repeated_phrase_loop"]["n"] == 2


def test_legit_phrase_not_flagged_as_loop():
    # "the the" is not a real loop because it doesn't repeat 3+ times
    r = analyze_sample("the cat. the dog. the bird.")
    assert r.signatures["repeated_phrase_loop"]["found"] is False


# ---------------------------------------------------------------------------
# 2. Truncation / mid-clause cutoff
# ---------------------------------------------------------------------------

def test_truncation_on_function_word():
    r = analyze_sample("The expression names a foundational thought with")
    assert r.signatures["truncation"]["found"] is True
    assert r.signatures["truncation"]["reason"] == "ends_on_function_word"


def test_truncation_on_comma():
    r = analyze_sample("This expression contains a state literal, a drive,")
    assert r.signatures["truncation"]["found"] is True
    assert r.signatures["truncation"]["reason"] == "ends_on_comma"


def test_no_truncation_with_period():
    r = analyze_sample("This is a complete sentence ending in a period.")
    assert r.signatures["truncation"]["found"] is False


# ---------------------------------------------------------------------------
# 3. Stage variable corruption
# ---------------------------------------------------------------------------

def test_canonical_stage_var_clean():
    r = analyze_sample("Let stageA0_5_0296 name a foundational thought.")
    sig = r.signatures["stage_var_corruption"]
    assert sig["found"] is False
    assert sig["canonical_count"] >= 1


def test_stage_var_double_underscore():
    r = analyze_sample("Let stageA0__5_0296 name something.")
    sig = r.signatures["stage_var_corruption"]
    assert sig["found"] is True
    assert sig["double_underscore"]


def test_stage_var_missing_letter():
    r = analyze_sample("Let stage_5_0296 name something.")
    sig = r.signatures["stage_var_corruption"]
    assert sig["found"] is True
    assert sig["no_letter"]


def test_stage_var_bad_digits():
    # 6+ trailing digits = malformed
    r = analyze_sample("Let stageD3_3_0233333 name something.")
    sig = r.signatures["stage_var_corruption"]
    assert sig["found"] is True
    assert sig["bad_digits"]


# ---------------------------------------------------------------------------
# 4. Hard notation leak
# ---------------------------------------------------------------------------

def test_notation_leak_caret_in_prose():
    r = analyze_sample("The expression is ^P which is a foundational realm idea ^0.")
    sig = r.signatures["notation_leak"]
    assert sig["found"] is True


def test_notation_leak_pipe_letter():
    r = analyze_sample("Register is |T and applies to the cognitive arena.")
    sig = r.signatures["notation_leak"]
    assert sig["found"] is True


def test_no_notation_leak_in_plain_english():
    r = analyze_sample("The expression describes a cognitive state in the foundational realm.")
    sig = r.signatures["notation_leak"]
    assert sig["found"] is False


# ---------------------------------------------------------------------------
# 5. Generic prose collapse
# ---------------------------------------------------------------------------

def test_generic_collapse_short_output():
    r = analyze_sample(
        "This expression is valid.",
        target_text="A long expected reply with many specifics about the meaning of the expression that spans several clauses.",
    )
    sig = r.signatures["generic_collapse"]
    assert sig["found"] is True
    assert sig["is_too_short"] is True


def test_generic_collapse_generic_phrase():
    r = analyze_sample(
        "This expression is valid and means something specific.",
        target_text="The expression denotes a binary composition of two cognitive states.",
    )
    sig = r.signatures["generic_collapse"]
    assert sig["found"] is True


def test_no_generic_collapse_with_specific_content():
    r = analyze_sample(
        "The expression denotes a binary composition of cognitive states integrated together.",
        target_text="The expression denotes a binary composition of cognitive states integrated together.",
    )
    sig = r.signatures["generic_collapse"]
    assert sig["found"] is False


# ---------------------------------------------------------------------------
# 6. ABeing-style token boundary corruption
# ---------------------------------------------------------------------------

def test_abeing_style_fusion():
    r = analyze_sample("ABeing aThought aFeeling all merge inThe mind.")
    sig = r.signatures["camel_fusion"]
    assert sig["found"] is True
    assert sig["count"] >= 3


def test_single_camel_word_not_flagged():
    # iPhone-style legit camelcase shouldn't trip the gate by itself
    r = analyze_sample("The model trained on iPhone data for one example.")
    sig = r.signatures["camel_fusion"]
    # found may be True (count==1) but not severe; verdict shouldn't escalate
    assert sig["count"] <= 1


# ---------------------------------------------------------------------------
# Verdict bands
# ---------------------------------------------------------------------------

def test_clean_sample_clean_verdict():
    r = analyze_sample(
        "A thought in cognitive thinking, driven by a need for connection.",
        target_text="A thought in cognitive thinking, driven by a need for connection.",
    )
    assert r.verdict == "clean"


def test_severe_repeat_loop_kills():
    text = "the the the the the the the the the"
    r = analyze_sample(text)
    assert r.verdict == "kill"


def test_stage_var_corruption_kills():
    text = "Let stageA0__5_0296 name a thought, and stage_5_0296 name a feeling."
    r = analyze_sample(text)
    assert r.verdict == "kill"


def test_mild_truncation_warns_not_kills():
    r = analyze_sample(
        "This is a normal sentence that ends in a hanging the",
        target_text="A target reply about the cognitive state.",
    )
    # Truncation alone shouldn't kill (it's 0.5 severity)
    assert r.verdict in ("clean", "warn")


# ---------------------------------------------------------------------------
# Pack-level aggregation
# ---------------------------------------------------------------------------

def test_pack_verdict_one_kill_kills_pack():
    reports = [
        analyze_sample("This is a normal sentence.", target_text="This is a normal sentence."),
        analyze_sample("Let stageA0__5_0296 cause stage_5_0296 corruption everywhere here."),
    ]
    p = aggregate_pack_verdict(reports)
    assert p["verdict"] == "kill"


def test_pack_verdict_all_clean_is_clean():
    reports = [
        analyze_sample("A normal reply about cognitive states.", target_text="A normal reply about cognitive states."),
        analyze_sample("A second normal reply describing operations.", target_text="A second normal reply describing operations."),
    ]
    p = aggregate_pack_verdict(reports)
    assert p["verdict"] == "clean"


def test_pack_verdict_no_samples():
    p = aggregate_pack_verdict([])
    assert p["verdict"] == "no_samples"
