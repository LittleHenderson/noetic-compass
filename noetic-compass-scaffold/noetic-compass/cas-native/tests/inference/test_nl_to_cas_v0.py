"""Tests for the NL → CAS heuristic bridge v0.

Discipline pinned (mirrors plain_english.py "does not lie" rule):
- Pattern never invents a CAS expression. No match → None.
- Each match carries a confidence score and a human-readable
  matched_pattern description.
- The pattern table covers Codex's directive examples ("explain a
  thought becoming action", "turn anger into CAS", etc.).
"""
from __future__ import annotations

import pytest

from cas_native.inference.nl_to_cas_v0 import (
    NLMatchResult,
    list_supported_patterns,
    match_nl_to_cas,
)


# ---------------------------------------------------------------------------
# Empty / no-match → None (no fabrication)
# ---------------------------------------------------------------------------

def test_empty_string_returns_none():
    assert match_nl_to_cas("") is None
    assert match_nl_to_cas("   ") is None


def test_unmatched_freeform_returns_none():
    """REGRESSION PIN: arbitrary English that doesn't match any pattern
    returns None. The bridge never fabricates a CAS expression."""
    assert match_nl_to_cas("tell me about your weekend") is None
    assert match_nl_to_cas("what is the weather in Paris") is None
    assert match_nl_to_cas("the cat sat on the mat") is None


# ---------------------------------------------------------------------------
# Codex's directive examples — each must match
# ---------------------------------------------------------------------------

def test_thought_becoming_action_matches():
    result = match_nl_to_cas("explain a thought becoming action")
    assert result is not None
    assert result.cas_expression == "^9^O"
    assert result.matched_pattern == "thought becoming action"
    assert 0.0 < result.confidence <= 1.0


def test_chain_for_awareness_leading_to_action_matches():
    result = match_nl_to_cas(
        "give me a CAS chain for awareness leading to action"
    )
    assert result is not None
    assert result.cas_expression == "^1^C -> ^9^O"
    # Strongest signal — exact phrase match → confidence 1.0
    assert result.confidence == 1.0


def test_turn_anger_into_cas_matches():
    result = match_nl_to_cas("turn anger into CAS")
    assert result is not None
    assert result.cas_expression == "^3^E|f"
    assert result.confidence == 1.0


def test_explain_decision_in_cas_matches():
    result = match_nl_to_cas("explain a decision in CAS")
    assert result is not None
    assert result.cas_expression == "^8^P -> ^9^O"


def test_show_simple_cas_example_matches():
    result = match_nl_to_cas("show me a simple CAS example")
    assert result is not None
    # The simple-example mapping returns a canonical 2-stage chain
    assert "stageA0_4_857" in result.cas_expression
    assert "->" in result.cas_expression


def test_explain_feeling_in_cas_matches():
    result = match_nl_to_cas("explain a feeling in CAS")
    assert result is not None
    # Vibration in Evaluative, Affective register
    assert result.cas_expression == "^4^E|f"


# ---------------------------------------------------------------------------
# Match shape + confidence
# ---------------------------------------------------------------------------

def test_match_returns_nlmatchresult_dataclass():
    result = match_nl_to_cas("explain a thought becoming action")
    assert isinstance(result, NLMatchResult)
    # All four fields populated
    assert result.matched_pattern
    assert result.cas_expression
    assert result.rationale
    assert 0.0 < result.confidence <= 1.0


def test_rationale_is_plain_english_not_jargon():
    """REGRESSION PIN (mirrors plain_english anti-jargon discipline):
    rationale text uses canonical Noetic vocabulary (Idea / Mind /
    Operational / Affective / etc.) NOT engineering jargon."""
    forbidden = [
        "STAGE_VAR", "slot trace", "Δ°₃₉", "scheduled sampling",
        "p_copy", "lm_logits",
    ]
    for input_text in (
        "explain a thought becoming action",
        "turn anger into CAS",
        "give me a CAS chain for awareness leading to action",
        "show me a simple CAS example",
        "explain a feeling in CAS",
    ):
        result = match_nl_to_cas(input_text)
        assert result is not None
        for term in forbidden:
            assert term not in result.rationale, (
                f"rationale for {input_text!r} contains forbidden "
                f"jargon {term!r}"
            )


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------

def test_matches_are_case_insensitive():
    a = match_nl_to_cas("EXPLAIN A THOUGHT BECOMING ACTION")
    b = match_nl_to_cas("Explain A Thought Becoming Action")
    c = match_nl_to_cas("explain a thought becoming action")
    assert a is not None and b is not None and c is not None
    assert a.cas_expression == b.cas_expression == c.cas_expression


# ---------------------------------------------------------------------------
# Pattern priority — most specific matches first
# ---------------------------------------------------------------------------

def test_chain_phrase_beats_action_phrase():
    """The chain phrase 'awareness leading to action' is more specific
    than 'thought becoming action'. The chain pattern must win when
    both could theoretically match."""
    result = match_nl_to_cas(
        "give me a CAS chain for awareness leading to action"
    )
    assert result is not None
    # Chain mapping is `^1^C -> ^9^O`, NOT the simpler `^9^O`
    assert result.cas_expression == "^1^C -> ^9^O"


# ---------------------------------------------------------------------------
# list_supported_patterns
# ---------------------------------------------------------------------------

def test_list_supported_patterns_returns_unique_descriptions():
    patterns = list_supported_patterns()
    assert isinstance(patterns, list)
    assert len(patterns) >= 10, (
        f"v0 should have at least 10 distinct supported patterns; "
        f"got {len(patterns)}"
    )
    # No duplicates
    assert len(patterns) == len(set(patterns))


def test_list_supported_patterns_includes_codex_examples():
    """Codex's directive named these patterns specifically — each must
    appear in the supported list."""
    patterns_text = "\n".join(list_supported_patterns()).lower()
    # At least these named patterns from Codex's example set
    assert "thought becoming action" in patterns_text
    assert "anger" in patterns_text
    assert "decision in cas" in patterns_text
    assert "simple example" in patterns_text


# ---------------------------------------------------------------------------
# Confidence semantics
# ---------------------------------------------------------------------------

def test_exact_phrase_match_has_max_confidence():
    """Exact-phrase patterns should return confidence == 1.0; looser
    fuzzy matches lower."""
    exact = match_nl_to_cas("turn anger into CAS")
    assert exact is not None
    assert exact.confidence == 1.0


def test_fuzzy_phrase_match_has_lower_confidence():
    """Looser shapes return lower confidence so the UI can show the
    bridge was less sure."""
    fuzzy = match_nl_to_cas("explain anger")
    assert fuzzy is not None
    assert fuzzy.confidence < 1.0
