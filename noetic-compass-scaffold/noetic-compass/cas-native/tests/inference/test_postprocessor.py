"""Tests for the gated post-generation pipeline."""
from __future__ import annotations

import pytest

from cas_native.inference.postprocessor import (
    PostprocessResult,
    postprocess,
    count_adjacent_duplicate_words,
    count_hard_notation,
    count_jargon,
    count_repeated_phrase_windows,
)


# ---------------------------------------------------------------------------
# Quality-check primitives
# ---------------------------------------------------------------------------

def test_count_hard_notation_catches_state_literals() -> None:
    text = "Outcome called ^4^P|A reached"
    assert count_hard_notation(text) >= 1


def test_count_hard_notation_clean_text() -> None:
    text = "When something struck a chord, the outcome called alignment was reached."
    assert count_hard_notation(text) == 0


def test_count_jargon_catches_operator_word() -> None:
    text = "The operator combines two ideas into one."
    assert count_jargon(text) >= 1


def test_count_jargon_clean_text() -> None:
    text = "When you pay attention, two ideas integrate."
    assert count_jargon(text) == 0


def test_count_adjacent_duplicate_words_flags_visible_stutter() -> None:
    text = "The concept concept is broken."
    assert count_adjacent_duplicate_words(text) == 1


def test_count_adjacent_duplicate_words_clean_text() -> None:
    text = "The concept is clean."
    assert count_adjacent_duplicate_words(text) == 0


def test_count_repeated_phrase_windows_flags_looping_phrase() -> None:
    text = (
        "A memory or association appeared, memory or association returned, "
        "and memory or association stayed."
    )
    assert count_repeated_phrase_windows(text) >= 1


def test_count_repeated_phrase_windows_clean_text() -> None:
    assert count_repeated_phrase_windows("A clean short sentence.") == 0


# ---------------------------------------------------------------------------
# Postprocess — repair OFF (default)
# ---------------------------------------------------------------------------

def test_postprocess_default_no_repair() -> None:
    """By default, postprocess does NOT mutate the generation. It just
    routes, scores, and quality-checks."""
    result = postprocess(
        source_cas="Θ(Ω_decision_60) = 1*^3^P → Ω_decision_60",
        raw_gen="To produce the outcome called wrong_name, combine 1 of stuff.",
    )
    assert result.repair_applied is False
    assert result.repair_log is None
    assert result.final_text == result.raw_text
    # Recovery is scored but not used to mutate
    assert result.recovery_pre_repair is not None
    assert result.recovery_pre_repair.omega_recovered == 0
    assert result.recovery_pre_repair.omega_total == 1
    assert result.recovery_post_repair is None  # no repair → no post score


# ---------------------------------------------------------------------------
# Postprocess — repair ON
# ---------------------------------------------------------------------------

def test_postprocess_with_repair_recovers_omega() -> None:
    result = postprocess(
        source_cas="Θ(Ω_decision_60) = 1*^3^P → Ω_decision_60",
        raw_gen="To produce the outcome called wrong_name, combine 1 of stuff.",
        apply_repair=True,
    )
    assert result.repair_applied is True
    assert result.repair_log is not None
    assert ("wrong_name", "decision_60") in result.repair_log.omega_substitutions
    assert "decision_60" in result.final_text
    assert "wrong_name" not in result.final_text
    # Pre-repair score reflects the original gen
    assert result.recovery_pre_repair.omega_recovered == 0
    # Post-repair score reflects the fixed gen
    assert result.recovery_post_repair.omega_recovered == 1


def test_postprocess_with_repair_no_op_when_correct() -> None:
    """When the gen is already correct, repair is a no-op and repair_log
    has zero substitutions."""
    result = postprocess(
        source_cas="Θ(Ω_alignment) = 1*^4^P|A → Ω_alignment",
        raw_gen="To produce the outcome called alignment, combine 1 of struck a chord.",
        apply_repair=True,
    )
    assert result.repair_applied is True
    assert result.repair_log.total == 0
    assert result.final_text == result.raw_text


# ---------------------------------------------------------------------------
# Postprocess — routing
# ---------------------------------------------------------------------------

def test_postprocess_routes_valid_to_cas_to_english() -> None:
    result = postprocess(
        source_cas="^7^C_{F2}|T",
        raw_gen="Practice and muscle memory in cognitive thinking.",
    )
    assert result.routing.task_type == "cas_to_english"
    assert result.routing.compiled is True


def test_postprocess_routes_invalid_to_explanation() -> None:
    result = postprocess(
        source_cas="let X = ^0^P; X -> Y",  # Y undefined
        raw_gen="The destination doesn't exist.",
    )
    assert result.routing.task_type == "invalid_to_explanation"
    assert result.routing.compiled is False


# ---------------------------------------------------------------------------
# Postprocess — quality checks
# ---------------------------------------------------------------------------

def test_postprocess_flags_hard_notation_leak() -> None:
    result = postprocess(
        source_cas="^4^P|A",
        raw_gen="The outcome maps to ^4^P|A in cognitive thinking.",
    )
    assert result.quality_passed is False
    assert any("hard_notation_count" in f for f in result.quality_failures)


def test_postprocess_flags_jargon_leak() -> None:
    result = postprocess(
        source_cas="^4^P|A",
        raw_gen="This is a noetic operator that processes ideas.",
    )
    assert result.quality_passed is False
    assert any("jargon_count" in f for f in result.quality_failures)


def test_postprocess_flags_adjacent_duplicate_words() -> None:
    result = postprocess(
        source_cas="^1^P",
        raw_gen="The concept concept is visible.",
    )
    assert result.quality_passed is False
    assert result.adjacent_duplicate_count == 1
    assert any("adjacent_duplicate_count" in f for f in result.quality_failures)


def test_postprocess_flags_repeated_phrase_loop() -> None:
    result = postprocess(
        source_cas="^8^P",
        raw_gen=(
            "A memory or association appeared, memory or association returned, "
            "and memory or association stayed."
        ),
    )
    assert result.quality_passed is False
    assert result.repeated_phrase_count >= 1
    assert any("repeated_phrase_count" in f for f in result.quality_failures)


def test_postprocess_flags_truncation_when_eos_not_reached() -> None:
    """Reproduces the v1 PREFIX128 5ep records 7-8 failure pattern:
    generation hit max_new_tokens without emitting EOS, producing
    the same incomplete sentence. The truncated flag + quality
    failure must surface so callers can retry or display
    '[response truncated]'."""
    result = postprocess(
        source_cas="^4^P|A",
        raw_gen="When something struck a chord in a principled way, expressed analytically, and a careful reader would noti",
        stopped_on_eos=False,
    )
    assert result.truncated is True
    assert result.quality_passed is False
    assert "truncated_at_max_tokens" in result.quality_failures


def test_postprocess_does_not_flag_truncation_when_eos_reached() -> None:
    """Clean EOS termination must NOT surface a truncation flag
    even if the gen happens to be short."""
    result = postprocess(
        source_cas="^4^P|A",
        raw_gen="When something struck a chord in a principled way.",
        stopped_on_eos=True,
    )
    assert result.truncated is False
    assert "truncated_at_max_tokens" not in result.quality_failures


def test_postprocess_skips_truncation_check_when_signal_unknown() -> None:
    """When the caller doesn't pass stopped_on_eos (e.g. unit tests
    on raw text snippets), we don't flag truncation. The check
    requires explicit signal from the generation layer."""
    result = postprocess(
        source_cas="^4^P|A",
        raw_gen="When something struck a chord in a principled way, expressed analytically.",
        stopped_on_eos=None,
    )
    assert result.truncated is False
    assert "truncated_at_max_tokens" not in result.quality_failures


def test_postprocess_clean_text_passes_quality() -> None:
    result = postprocess(
        source_cas="^4^P|A",
        raw_gen="When something struck a chord in a principled way, expressed analytically.",
    )
    assert result.quality_passed is True
    assert result.quality_failures == []


def test_postprocess_quality_check_disabled() -> None:
    """When quality_check=False, hard/jargon counts are 0 and pass is True
    regardless of content."""
    result = postprocess(
        source_cas="^4^P|A",
        raw_gen="The operator ^4^P|A combines noetic operations.",  # all violations
        quality_check=False,
    )
    assert result.quality_passed is True
    assert result.hard_notation_count == 0
    assert result.jargon_count == 0


# ---------------------------------------------------------------------------
# Postprocess — to_dict serialization for trace logging
# ---------------------------------------------------------------------------

def test_postprocess_result_serializes_cleanly() -> None:
    result = postprocess(
        source_cas="Θ(Ω_decision_60) = 1*^3^P → Ω_decision_60",
        raw_gen="To produce the outcome called wrong_name, combine 1 of stuff.",
        apply_repair=True,
    )
    d = result.to_dict()
    # Critical fields preserved
    assert d["repair_applied"] is True
    assert d["routing"]["task_type"] == "cas_to_english"
    assert d["repair_log"]["total"] >= 1
    assert d["recovery_pre_repair"]["omega_recovered"] == 0
    assert d["recovery_post_repair"]["omega_recovered"] == 1
