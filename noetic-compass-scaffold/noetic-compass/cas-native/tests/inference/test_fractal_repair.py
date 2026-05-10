"""Phase 1 tests for cas_native.inference.fractal_repair.

Coverage:
  - Parser: Φ<…>, Phi<…>, single-element, multi-element, no-fractal-no-op
  - Noetic extraction from rendered text: longest-match-wins, word
    boundaries, all 10 noetic indicators, mixed colloquialisms
  - Comparison: exact match, cardinality drift up/down, position drift,
    repeat run detection
  - Phase 1 invariant: verify_fractal_rendering NEVER mutates rendered
"""
from __future__ import annotations

from cas_native.inference.fractal_repair import (
    FractalRepairLog,
    FractalSequence,
    RepeatRun,
    extract_noetic_sequence,
    parse_fractal,
    verify_fractal_rendering,
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def test_parse_phi_unicode():
    seq = parse_fractal("Φ<6:9:7:0:9:5:2:0>")
    assert seq is not None
    assert seq.k_values == (6, 9, 7, 0, 9, 5, 2, 0)
    assert seq.notation == "Φ"


def test_parse_phi_ascii():
    seq = parse_fractal("Phi<3:7>")
    assert seq is not None
    assert seq.k_values == (3, 7)
    assert seq.notation == "Phi"


def test_parse_phi_with_whitespace():
    seq = parse_fractal("Phi< 1 : 0 : 3 >")
    assert seq is not None
    assert seq.k_values == (1, 0, 3)


def test_parse_returns_none_for_non_fractal_sources():
    """Structural gate: state literals, rpm_chains, recipes, meta-logic,
    CRO must all return None so Phase 1 no-ops on them."""
    assert parse_fractal("^0^P|A") is None
    assert parse_fractal("let stageA = ^0^P; stageA -> stageB") is None
    assert parse_fractal("Θ(Ω_x) = 1*^7^O + 2*^6^C → Ω_x") is None
    assert parse_fractal("PartitionOf(Noetics, NoeticCluster{^5})") is None
    assert parse_fractal("(^4^C|A × ^4^C|E) = ^4^C|Ω_clarity") is None


def test_parse_returns_none_for_malformed_fractal():
    """Defensive: Φ-like syntax that doesn't parse cleanly should
    return None rather than partial data."""
    assert parse_fractal("Φ<>") is None  # empty body
    assert parse_fractal("Phi<a:b>") is None  # non-numeric


# ---------------------------------------------------------------------------
# Noetic sequence extraction
# ---------------------------------------------------------------------------

def test_extract_single_noetic_phrase():
    """A single colloquialism produces a single-item sequence."""
    out = extract_noetic_sequence("Something that struck a chord.")
    assert out == [4]


def test_extract_multiple_noetics_in_order():
    """Sequence reflects rendered order, not source order."""
    out = extract_noetic_sequence(
        "Something that popped into mind, then struck a chord, "
        "and finally muscle memory."
    )
    # ^9 (popped), ^4 (struck), ^7 (muscle memory)
    assert out == [9, 4, 7]


def test_extract_longest_match_wins():
    """When 'popped into mind' and 'popped' both could match, the
    longer phrase wins; only one ^9 is recorded for the substring."""
    out = extract_noetic_sequence("It popped into mind suddenly.")
    assert out == [9]
    # Confirm the shorter "popped" alone also extracts as ^9 elsewhere.
    out2 = extract_noetic_sequence("It popped suddenly.")
    assert out2 == [9]


def test_extract_respects_word_boundaries():
    """'thoughtful' should NOT match the 'a thought' pattern; 'thought'
    inside a longer word doesn't count."""
    out = extract_noetic_sequence("She was thoughtful.")
    # No noetic detected — 'thoughtful' is not a colloquialism match.
    assert out == []


def test_extract_handles_case_insensitivity():
    out = extract_noetic_sequence("PRACTICE MAKES PERFECT in the gym.")
    assert out == [7]


def test_extract_returns_empty_for_empty_text():
    assert extract_noetic_sequence("") == []


def test_extract_returns_empty_when_no_indicators_present():
    out = extract_noetic_sequence("The quick brown fox jumped over.")
    assert out == []


# ---------------------------------------------------------------------------
# Abutting-same-Noetic dedup (smoke 2026-05-10 regression fix)
# ---------------------------------------------------------------------------

def test_abutting_who_one_is_shaped_by_experiences_counts_as_one_5():
    """'who one is' and 'shaped by experiences' both match ^5 and the
    smoke run found models rendering them as a single elaborated phrase.
    The dedup should treat that as ONE ^5 emission, not two."""
    out = extract_noetic_sequence("Who one is shaped by experiences.")
    assert out == [5]


def test_abutting_dedup_preserves_distant_same_noetic_repeat():
    """When the same noetic appears at clearly-separated positions
    (more than ~5 chars between them), both should emit. Source
    Φ<5:5> is a legitimate doubled k that the model must render
    as two distinct stages."""
    out = extract_noetic_sequence(
        "Who one is, then later who one is again."
    )
    # Two separate ^5 emissions: "who one is" + "who one is again"
    assert out == [5, 5]


def test_abutting_dedup_does_not_collapse_different_noetics():
    """Different noetics adjacent to each other must both emit."""
    out = extract_noetic_sequence(
        "Who one is then breaking it down then practiced rhythm."
    )
    assert out == [5, 6, 7]


def test_abutting_dedup_handles_three_same_noetic_indicators():
    """Three abutting ^5 indicators in one phrase still emit one ^5."""
    out = extract_noetic_sequence(
        "Who one is shaped by experiences who you are."
    )
    # All three are ^5 indicators packed together — emit once.
    assert out == [5]


# ---------------------------------------------------------------------------
# Comparison + log structure
# ---------------------------------------------------------------------------

def test_verify_no_op_for_non_fractal_source():
    rendered = "Something that struck a chord."
    out, log = verify_fractal_rendering(
        source_cas="^4^C|A", rendered=rendered,
    )
    assert out == rendered
    assert log.sequence_parsed is False


def test_verify_no_op_for_empty_rendered():
    out, log = verify_fractal_rendering(
        source_cas="Phi<3:7>", rendered="",
    )
    assert out == ""
    assert log.sequence_parsed is False


def test_verify_exact_sequence_match_logs_clean():
    """When rendered text exactly preserves the source sequence,
    sequence_matches=True and no mismatches logged."""
    out, log = verify_fractal_rendering(
        source_cas="Phi<3:7>",
        rendered=(
            "First, something that rubs the wrong way. "
            "Then, practice makes perfect."
        ),
    )
    assert log.sequence_parsed is True
    assert log.expected_k_values == [3, 7]
    assert log.found_k_sequence == [3, 7]
    assert log.cardinality_matches is True
    assert log.sequence_matches is True
    assert log.mismatch_positions == []


def test_verify_invariant_does_not_mutate_rendered():
    """Phase 1 invariant: rendered text is passed through verbatim
    even when significant drift is detected."""
    rendered = (
        "Something that struck a chord, then drawn to it, "
        "then breaking it down."
    )
    out, log = verify_fractal_rendering(
        source_cas="Phi<9:7>",  # expects ^9, ^7; rendered has ^4, ^2, ^6
        rendered=rendered,
    )
    assert out == rendered  # never mutated
    assert log.sequence_matches is False


def test_verify_cardinality_too_long_record_14_pattern():
    """Audit's record-14 finding: source Φ<3:7> (2 elements), rendered
    has 4 stages. Log should flag cardinality mismatch and identify
    extras at trailing positions."""
    out, log = verify_fractal_rendering(
        source_cas="Φ<3:7>",
        rendered=(
            "Something that struck a chord, drawn to it, "
            "triggered a memory, and muscle memory."
        ),
    )
    # Found: ^4, ^2, ^8, ^7 (4 noetics for a 2-element source).
    assert log.expected_k_count == 2
    assert log.found_k_count == 4
    assert log.cardinality_matches is False
    assert log.mismatch_positions == [2, 3]  # extras at positions 2, 3


def test_verify_cardinality_too_short():
    """When the model emits FEWER stages than the source, the missing
    positions are logged."""
    out, log = verify_fractal_rendering(
        source_cas="Phi<6:9:7:0:9:5:2:0>",  # 8 elements
        rendered="Just unpacking this idea, then it just clicked.",
        # Found: ^6, ^9 (only 2)
    )
    assert log.expected_k_count == 8
    assert log.found_k_count == 2
    assert log.cardinality_matches is False
    # Missing positions: 2, 3, 4, 5, 6, 7
    assert log.mismatch_positions == [2, 3, 4, 5, 6, 7]


def test_verify_position_drift_with_matching_cardinality():
    """When count matches but ordering is wrong, mismatch_positions
    flags the specific positions where source != found."""
    out, log = verify_fractal_rendering(
        source_cas="Phi<3:7>",
        # ^4 instead of ^3 at pos 0; ^7 at pos 1 (correct)
        rendered="Struck a chord, then practice makes perfect.",
    )
    assert log.cardinality_matches is True
    assert log.sequence_matches is False
    assert log.mismatch_positions == [0]


def test_verify_repeat_run_detection_record_15_pattern():
    """Audit's record-15 finding: long, repetitive output. The found
    sequence carries runs of repeated k-values; the log records
    every run of length >=2."""
    out, log = verify_fractal_rendering(
        source_cas="Phi<1:0:3:3:1:1:7:5>",
        rendered=(
            "Paying attention again, paying attention again, "
            "paying attention again, then practice makes perfect."
        ),
        # Found: ^1, ^1, ^1, ^7
    )
    assert log.found_k_sequence == [1, 1, 1, 7]
    assert len(log.repeat_runs) == 1
    assert log.repeat_runs[0].k_value == 1
    assert log.repeat_runs[0].length == 3
    assert log.repeat_runs[0].start_position == 0


def test_verify_multiple_repeat_runs():
    """A sequence with multiple repeat runs records each separately."""
    out, log = verify_fractal_rendering(
        source_cas="Phi<1:1:7:7:7>",
        rendered=(
            "Paying attention, paying attention, "
            "muscle memory, muscle memory, muscle memory."
        ),
    )
    assert log.found_k_sequence == [1, 1, 7, 7, 7]
    assert len(log.repeat_runs) == 2
    assert log.repeat_runs[0].k_value == 1
    assert log.repeat_runs[0].length == 2
    assert log.repeat_runs[1].k_value == 7
    assert log.repeat_runs[1].length == 3


# ---------------------------------------------------------------------------
# Log serialization
# ---------------------------------------------------------------------------

def test_log_to_dict_has_all_diagnostic_fields():
    out, log = verify_fractal_rendering(
        source_cas="Phi<3:7>",
        rendered="Struck a chord, then drawn to it.",
    )
    d = log.to_dict()
    for key in [
        "sequence_parsed", "notation",
        "expected_k_count", "expected_k_values",
        "found_k_count", "found_k_sequence",
        "cardinality_matches", "sequence_matches",
        "mismatch_positions",
        "n_repeat_runs", "repeat_runs",
        "notes",
    ]:
        assert key in d, key
    import json
    json.dumps(d)


def test_log_no_op_record_serializes_with_sequence_parsed_false():
    """For non-fractal sources, the log is a clean no-op shell."""
    _, log = verify_fractal_rendering(
        source_cas="^4^C|A", rendered="Something resonated.",
    )
    d = log.to_dict()
    assert d["sequence_parsed"] is False
    assert d["expected_k_count"] == 0
    assert d["found_k_count"] == 0
