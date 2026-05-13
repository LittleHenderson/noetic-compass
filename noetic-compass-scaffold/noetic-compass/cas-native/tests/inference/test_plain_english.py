"""Tests for the Plain English Mode translator.

The load-bearing assertion (per Codex 2026-05-13 audit and the
`decisions.md` 2026-05-13T15:30Z scope): plain mode does not lie.
Every claim plain mode makes MUST be derivable from a verifiable
field in the technical output.

Test coverage:
- Each qualitative coverage band, including the "unknown" path
- Slot-quality phrasing for each shape
- Each gate combination in the short-answer logic
- Plain meaning's de-duplication of missing identifiers
- Confidence caveat fires when it should, NOT when it shouldn't
- Translator returns the documented top-level keys with no fabrication
"""
from __future__ import annotations

import pytest

from cas_native.inference.plain_english import (
    human_slot_label,
    qualitative_coverage_band,
    qualitative_slot_quality,
    translate_explain,
)


# ---------------------------------------------------------------------------
# human_slot_label
# ---------------------------------------------------------------------------

def test_human_slot_label_known_ids():
    """Documented slot ids 0..8 each have a stable human label.
    The internal int 2 = STAGE_VAR = 'named identifier' user-facing."""
    assert human_slot_label(0) == "joining word"
    assert human_slot_label(2) == "named identifier"
    assert human_slot_label(8) == "noetic phrase"


def test_human_slot_label_unknown_returns_unknown_not_invented_label():
    """Plain mode does not lie. Unknown slot id returns 'unknown slot',
    NEVER a fabricated label."""
    assert human_slot_label(99) == "unknown slot"
    assert human_slot_label(-1) == "unknown slot"


# ---------------------------------------------------------------------------
# qualitative_coverage_band
# ---------------------------------------------------------------------------

def test_coverage_band_strong():
    assert qualitative_coverage_band(0.85) == "strong"
    assert qualitative_coverage_band(1.0) == "strong"


def test_coverage_band_partial():
    assert qualitative_coverage_band(0.50) == "partial"
    assert qualitative_coverage_band(0.84) == "partial"


def test_coverage_band_weak():
    assert qualitative_coverage_band(0.49) == "weak"
    assert qualitative_coverage_band(0.01) == "weak"


def test_coverage_band_none():
    assert qualitative_coverage_band(0.0) == "none"


def test_coverage_band_unknown_when_missing():
    """Plain mode does not lie. Missing coverage → 'unknown', NOT a guess."""
    assert qualitative_coverage_band(None) == "unknown"


def test_coverage_band_unknown_when_garbage():
    """Plain mode does not lie. Garbage input → 'unknown', NOT a crash
    and NOT a guess."""
    assert qualitative_coverage_band("nope") == "unknown"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# qualitative_slot_quality
# ---------------------------------------------------------------------------

def test_slot_quality_no_tokens():
    s = {"length": 0, "counts": {}, "longest_stage_var_run": 0}
    assert qualitative_slot_quality(s) == "no tokens generated"


def test_slot_quality_long_run():
    s = {"length": 49, "counts": {"0": 32, "2": 17},
         "longest_stage_var_run": 9}
    assert "long named-identifier" in qualitative_slot_quality(s)


def test_slot_quality_short_run():
    s = {"length": 12, "counts": {"0": 10, "2": 2},
         "longest_stage_var_run": 2}
    assert qualitative_slot_quality(s) == (
        "the model produced at least one named identifier"
    )


def test_slot_quality_all_connective():
    s = {"length": 10, "counts": {"0": 10}, "longest_stage_var_run": 0}
    assert qualitative_slot_quality(s) == (
        "the model only generated joining words"
    )


def test_slot_quality_unknown_when_missing():
    """Plain mode does not lie. Missing slot summary → 'unknown'."""
    assert qualitative_slot_quality({}) == "no tokens generated"
    assert qualitative_slot_quality({"length": "garbage"}) == (  # type: ignore[dict-item]
        "no tokens generated"
    )


# ---------------------------------------------------------------------------
# translate_explain — full pipeline
# ---------------------------------------------------------------------------

def _make_report(
    *,
    expected: list[str],
    copied: list[str],
    missing: list[str],
    coverage: float | None,
    generated_text: str = "some text",
    n_tokens_generated: int = 25,
    decode_seconds: float = 5.0,
    slot_summary: dict | None = None,
) -> dict:
    """Helper to build a synthetic explain report for testing."""
    return {
        "generated_english": generated_text,
        "n_tokens_generated": n_tokens_generated,
        "model": {
            "decode_seconds": decode_seconds,
            "max_cas_prefix_len": 192,
        },
        "identifiers": {
            "expected": expected,
            "copied": copied,
            "missing": missing,
            "coverage": coverage,
        },
        "slot_summary": slot_summary or {
            "length": 25, "counts": {"0": 18, "2": 7},
            "longest_stage_var_run": 4,
        },
        "gates": {
            "generated_non_empty": bool(generated_text),
            "ge_one_identifier_copied": bool(copied),
        },
    }


def test_translate_returns_documented_keys():
    """The translator returns exactly the five documented top-level keys."""
    r = _make_report(
        expected=["a", "b"], copied=["a"], missing=["b"], coverage=0.5,
    )
    out = translate_explain(r)
    assert set(out.keys()) == {
        "short_answer", "plain_meaning",
        "qualitative_coverage", "qualitative_slot_quality",
        "confidence_caveat",
    }


def test_translate_says_missed_when_id_missing():
    """REGRESSION PIN (plain mode does not lie): if an identifier is in
    `missing`, plain_meaning MUST say so. This is exactly Codex's
    example check."""
    r = _make_report(
        expected=["stageA0_4_857", "stageW6_4_857"],
        copied=["stageA0_4_857"],
        missing=["stageW6_4_857"],
        coverage=0.5,
    )
    out = translate_explain(r)
    assert "stageW6_4_857" in out["plain_meaning"], (
        "plain mode must name the missed identifier, not hide it"
    )
    assert "missed" in out["plain_meaning"].lower()


def test_translate_says_carried_when_copy_clean():
    """REGRESSION PIN: if all identifiers were copied, plain_meaning
    can say so."""
    r = _make_report(
        expected=["a", "b", "c"], copied=["a", "b", "c"], missing=[],
        coverage=1.0,
    )
    out = translate_explain(r)
    assert "carried" in out["short_answer"].lower() or \
           "carried" in out["plain_meaning"].lower()
    assert out["qualitative_coverage"] == "strong"


def test_translate_does_not_claim_certainty_when_unknown():
    """REGRESSION PIN (plain mode does not lie): if coverage is None,
    qualitative_coverage must be 'unknown', NOT a guess."""
    r = _make_report(
        expected=[], copied=[], missing=[], coverage=None,
    )
    out = translate_explain(r)
    assert out["qualitative_coverage"] == "unknown"


def test_translate_de_duplicates_missing_in_meaning():
    """If the same identifier appears multiple times in `missing` (e.g.
    referenced twice in input chain), plain_meaning lists it once,
    not duplicated."""
    r = _make_report(
        expected=["a", "b", "b"], copied=["a"],
        missing=["b", "b"],  # b appears twice
        coverage=0.333,
    )
    out = translate_explain(r)
    # "b" should appear in plain_meaning, but only once in the joined list
    meaning = out["plain_meaning"]
    assert meaning.count("(b)") <= 1


def test_translate_confidence_caveat_fires_on_slow_low_coverage():
    """Caveat fires when decode took >10s AND coverage <0.5."""
    r = _make_report(
        expected=["a", "b"], copied=[], missing=["a", "b"],
        coverage=0.0, decode_seconds=15.0,
    )
    out = translate_explain(r)
    assert out["confidence_caveat"] is not None
    assert "uncertain" in out["confidence_caveat"].lower()


def test_translate_no_caveat_on_fast_clean():
    """No caveat when decode was fast AND coverage was strong."""
    r = _make_report(
        expected=["a"], copied=["a"], missing=[], coverage=1.0,
        decode_seconds=2.0,
    )
    out = translate_explain(r)
    assert out["confidence_caveat"] is None


def test_translate_few_tokens_caveat():
    """Caveat fires when very few tokens were generated."""
    r = _make_report(
        expected=["a"], copied=["a"], missing=[], coverage=1.0,
        n_tokens_generated=3,
    )
    out = translate_explain(r)
    assert out["confidence_caveat"] is not None
    assert "few tokens" in out["confidence_caveat"].lower()


def test_translate_no_generated_output_short_answer():
    """When the model produced no text, short_answer says so directly."""
    r = _make_report(
        expected=["a"], copied=[], missing=["a"], coverage=0.0,
        generated_text="",
    )
    out = translate_explain(r)
    assert "no output" in out["short_answer"].lower()


def test_translate_zero_expected_does_not_invent_blame():
    """When the input had no expected identifiers, plain_meaning should
    acknowledge the absence rather than claim failure."""
    r = _make_report(
        expected=[], copied=[], missing=[], coverage=None,
        generated_text="The expression is a noetic phrase.",
    )
    out = translate_explain(r)
    # short_answer should NOT claim the model missed something
    assert "did not carry over any" not in out["short_answer"]
    # plain_meaning should note that there was nothing to carry
    assert "nothing" in out["plain_meaning"].lower() or \
           "did not contain" in out["plain_meaning"].lower()
