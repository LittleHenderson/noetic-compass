"""Tests for cas_self_explainer — layered CAS self-explanation.

Discipline pinned by tests (per Codex 2026-05-13):
- Simple level always has a metaphor populated.
- Stakeholder level NEVER uses internal labels (STAGE_VAR, slot trace,
  Δ°₃₉, simplex, etc.) — same anti-jargon discipline as Plain English Mode.
- Technical level uses canonical CAS vocabulary verbatim from CLAUDE.md.
- Deeper/simpler pointers form a valid graph (simple → stakeholder →
  user → builder → technical → null; null → simple via simpler).
- explain_cas NEVER fabricates content on unknown inputs (raises).
"""
from __future__ import annotations

import pytest

from cas_native.inference.cas_self_explainer import (
    LEVELS,
    TOPICS,
    explain_cas,
    step_deeper,
    step_simpler,
)


# ---------------------------------------------------------------------------
# Graph structure
# ---------------------------------------------------------------------------

def test_levels_in_expected_order():
    """LEVELS goes from simplest to most technical, in this order."""
    assert LEVELS == ("simple", "stakeholder", "user", "builder", "technical")


def test_deeper_chain_terminates_at_technical():
    """Walking deeper from simple ends at technical with no further hop."""
    cur = "simple"
    seen = [cur]
    while True:
        nxt = step_deeper(cur)
        if nxt == cur:
            break
        seen.append(nxt)
        cur = nxt
    assert seen == list(LEVELS)
    assert cur == "technical"


def test_simpler_chain_terminates_at_simple():
    """Walking simpler from technical ends at simple with no further hop."""
    cur = "technical"
    seen = [cur]
    while True:
        nxt = step_simpler(cur)
        if nxt == cur:
            break
        seen.append(nxt)
        cur = nxt
    assert seen == list(reversed(LEVELS))
    assert cur == "simple"


def test_step_deeper_from_technical_stays():
    """Already at the deepest level — /deeper is a no-op."""
    assert step_deeper("technical") == "technical"


def test_step_simpler_from_simple_stays():
    """Already at the simplest level — /simpler is a no-op."""
    assert step_simpler("simple") == "simple"


# ---------------------------------------------------------------------------
# All (level, topic) pairs exist and have well-formed output
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("topic", TOPICS)
def test_every_level_topic_pair_returns_text(level, topic):
    """Every documented (level, topic) pair must produce a non-empty text
    field. Coverage gate — no holes in the content store."""
    out = explain_cas(level=level, topic=topic)
    assert out["level"] == level
    assert out["topic"] == topic
    assert isinstance(out["text"], str)
    assert out["text"].strip(), (
        f"Empty text for ({level}, {topic}) — content store has a hole"
    )


@pytest.mark.parametrize("level", LEVELS)
def test_every_level_has_consistent_deeper_simpler_pointers(level):
    """For each level, the deeper/simpler pointers must agree with the
    LEVELS graph."""
    out = explain_cas(level=level, topic="what")
    idx = LEVELS.index(level)
    expected_deeper = LEVELS[idx + 1] if idx + 1 < len(LEVELS) else None
    expected_simpler = LEVELS[idx - 1] if idx > 0 else None
    assert out["deeper"] == expected_deeper
    assert out["simpler"] == expected_simpler


# ---------------------------------------------------------------------------
# Discipline gates ("does not lie")
# ---------------------------------------------------------------------------

def test_simple_level_always_has_metaphor_or_text_concrete():
    """Simple level is the front door. It must include either a metaphor
    field OR a concrete text that itself contains a metaphor. The 'what'
    + 'metaphor' topics specifically must have a metaphor field set."""
    out_what = explain_cas(level="simple", topic="what")
    out_metaphor = explain_cas(level="simple", topic="metaphor")
    assert out_what["metaphor"] is not None and out_what["metaphor"].strip()
    assert out_metaphor["metaphor"] is not None and out_metaphor["metaphor"].strip()


def test_stakeholder_level_uses_no_internal_labels():
    """REGRESSION PIN: stakeholder-level content must NOT contain internal
    labels like STAGE_VAR, slot trace, Δ°₃₉, simplex, etc. The whole
    point of the stakeholder level is to be readable without engineering
    vocabulary.

    Per Codex audit framing: jargon hidden behind "show details," front
    door speaks in normal language.
    """
    forbidden = [
        "STAGE_VAR", "slot_trace", "slot trace", "Δ°₃₉", "Delta°",
        "scheduled sampling", "p_copy", "lm_logits", "Fisher-Rao",
        "admissibility relation", "max_cas_prefix_len", "PYTHONPATH",
        "SimplexCollator", "decode_canary_pack",
    ]
    for topic in TOPICS:
        out = explain_cas(level="stakeholder", topic=topic)
        for label in forbidden:
            assert label not in out["text"], (
                f"Stakeholder-level text for topic {topic!r} contains "
                f"forbidden internal label {label!r}: {out['text'][:200]!r}"
            )
            if out["metaphor"]:
                assert label not in out["metaphor"]
            if out["example"]:
                assert label not in out["example"]


def test_simple_level_uses_no_internal_labels():
    """Same anti-jargon discipline at the simple level. Stronger gate:
    simple level should also exclude technical terms like 'transformer'
    or 'parameter'."""
    forbidden = [
        "STAGE_VAR", "slot_trace", "Δ°₃₉", "scheduled sampling",
        "p_copy", "lm_logits", "Fisher-Rao", "admissibility",
        "transformer", "tokenizer", "checkpoint",
    ]
    for topic in TOPICS:
        out = explain_cas(level="simple", topic=topic)
        for label in forbidden:
            assert label not in out["text"], (
                f"Simple-level text for topic {topic!r} contains "
                f"forbidden term {label!r}"
            )


def test_technical_level_uses_canonical_vocabulary():
    """Technical level must use the canonical CAS vocabulary. At minimum
    the 'what' topic at technical level must name the framework
    primitives. This is the inverse of the anti-jargon discipline at
    stakeholder level — technical readers expect the precise terms."""
    out = explain_cas(level="technical", topic="what")
    # Some recognizable canonical-vocabulary tokens must appear
    canonical_signals = [
        "Cognitive Architecture",
        "Noetics",
        "Drives",
        "Registers",
        "Δ°₃₉",
    ]
    found = sum(1 for sig in canonical_signals if sig in out["text"])
    assert found >= 3, (
        f"Technical 'what' should use at least 3 canonical signals; "
        f"found {found}. Text: {out['text'][:300]!r}"
    )


def test_technical_level_corrections_referenced():
    """The 'why' topic at technical level must reference the four
    Mathematical Corrections from CLAUDE.md. This is the load-bearing
    technical claim — if the corrections aren't named, the structural
    guarantee is hand-wavy."""
    out = explain_cas(level="technical", topic="why")
    assert "Correction" in out["text"]


# ---------------------------------------------------------------------------
# explain_cas does not fabricate
# ---------------------------------------------------------------------------

def test_explain_cas_raises_on_unknown_level():
    with pytest.raises(ValueError, match=r"Unknown level"):
        explain_cas(level="grandmaster", topic="what")


def test_explain_cas_raises_on_unknown_topic():
    with pytest.raises(ValueError, match=r"Unknown topic"):
        explain_cas(level="simple", topic="favorite-color")


def test_step_deeper_unknown_level_returns_same():
    """An unknown current level — step_deeper does not crash, returns
    the same string (no fabricated graph traversal)."""
    assert step_deeper("nonexistent") == "nonexistent"


def test_step_simpler_unknown_level_returns_same():
    assert step_simpler("nonexistent") == "nonexistent"


# ---------------------------------------------------------------------------
# Default front-door behavior
# ---------------------------------------------------------------------------

def test_default_call_is_simple_what():
    """Calling explain_cas() with no args returns the simple/what entry —
    the front door for first-time users."""
    out = explain_cas()
    assert out["level"] == "simple"
    assert out["topic"] == "what"


def test_returned_dict_keys_are_documented():
    """The returned dict shape is part of the contract for the chat
    REPL consumer. Pin the keys."""
    out = explain_cas()
    expected = {"level", "topic", "text", "example", "metaphor",
                "deeper", "simpler"}
    assert set(out.keys()) == expected
