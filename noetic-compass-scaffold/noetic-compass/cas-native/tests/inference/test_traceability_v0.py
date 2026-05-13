"""Tests for Traceability v0.

Schema-pin tests for the trace dict that flows from cas-explain into
the UI consumer. Discipline (per Codex audit `95fcecf` 2026-05-13):
- Source tokens are indexed objects, NOT bare strings
- Repeated identifiers get separate per-identifier entries with
  distinct output positions (Nth occurrence in expected maps to Nth
  in emitted)
- Thought Tree includes flat nodes + edges arrays, not just nested
- Warning flags do NOT fire on identifier-free inputs (^3^P|A et al.)
- JSON round-trips cleanly
"""
from __future__ import annotations

import json
import pytest

from cas_native.inference.traceability_v0 import (
    SCHEMA_VERSION,
    build_v0_trace,
    trace_to_json,
)


def _make_report(
    *,
    cas_expression: str = "let stageA0_4_857 = ^7^P_{F5}; stageA0_4_857 -> stageA0_4_857",
    generated: str = "the model said something",
    expected: list[str] | None = None,
    emitted: list[str] | None = None,
    copied: list[str] | None = None,
    coverage: float | None = None,
    n_tokens: int = 15,
    decode_seconds: float = 5.0,
    slot_summary: dict | None = None,
    plain: dict | None = None,
    gates: dict | None = None,
) -> dict:
    return {
        "input_cas_expression": cas_expression,
        "generated_english": generated,
        "n_tokens_generated": n_tokens,
        "model": {
            "manifest_ablation_mode": "e3",
            "decode_seconds": decode_seconds,
            "max_cas_prefix_len": 192,
        },
        "identifiers": {
            "expected": expected or [],
            "emitted": emitted or [],
            "copied": copied or [],
            "missing": [i for i in (expected or []) if i not in (copied or [])],
            "coverage": coverage,
        },
        "slot_summary": slot_summary or {
            "length": 25, "counts": {"0": 18, "2": 7},
            "longest_stage_var_run": 4,
        },
        "plain_english": plain or {
            "short_answer": "stub answer",
            "plain_meaning": "stub meaning",
            "qualitative_coverage": "strong",
            "qualitative_slot_quality": "the model produced at least one named identifier",
            "confidence_caveat": None,
        },
        "gates": gates or {
            "no_crash": True,
            "generated_non_empty": True,
            "ge_one_identifier_copied": True,
        },
    }


# ---------------------------------------------------------------------------
# Top-level schema
# ---------------------------------------------------------------------------

def test_trace_has_documented_top_level_keys():
    trace = build_v0_trace(_make_report())
    expected = {
        "schema_version", "trace_id", "created_at",
        "input", "output", "copy", "slot_trace", "confidence",
        "thought_tree",
    }
    assert set(trace.keys()) == expected


def test_schema_version_is_pinned():
    trace = build_v0_trace(_make_report())
    assert trace["schema_version"] == "trace_v0"
    assert trace["schema_version"] == SCHEMA_VERSION


def test_trace_id_is_unique_per_build():
    """Every build gets a fresh trace_id — load-bearing for object
    traceability per memory `feedback_object_traceability_required.md`."""
    t1 = build_v0_trace(_make_report())
    t2 = build_v0_trace(_make_report())
    assert t1["trace_id"] != t2["trace_id"]


def test_created_at_is_iso8601_utc():
    trace = build_v0_trace(_make_report())
    # Format: 2026-05-13T17:30:00Z
    assert trace["created_at"].endswith("Z")
    assert "T" in trace["created_at"]
    assert len(trace["created_at"]) == len("2026-05-13T17:30:00Z")


# ---------------------------------------------------------------------------
# Source tokens — indexed objects (Codex audit fix)
# ---------------------------------------------------------------------------

def test_source_tokens_are_indexed_objects_not_strings():
    """REGRESSION PIN (Codex 95fcecf): source tokens need indexes so
    the UI can attribute output positions to specific source indexes.
    NOT bare strings."""
    trace = build_v0_trace(_make_report(
        cas_expression="let x = ^7^P_{F5}; x -> x"
    ))
    tokens = trace["input"]["source_tokens"]
    assert isinstance(tokens, list)
    assert tokens, "source_tokens must not be empty for a non-empty expression"
    for entry in tokens:
        assert isinstance(entry, dict), (
            "each source token is an indexed object, not a bare string"
        )
        assert "index" in entry and "token" in entry
        assert isinstance(entry["index"], int)
        assert isinstance(entry["token"], str)
    # Indexes are 0-based and contiguous
    assert [t["index"] for t in tokens] == list(range(len(tokens)))


def test_source_tokens_empty_for_empty_expression():
    trace = build_v0_trace(_make_report(cas_expression=""))
    assert trace["input"]["source_tokens"] == []


# ---------------------------------------------------------------------------
# Per-identifier entries — repeats get separate entries (Codex audit fix)
# ---------------------------------------------------------------------------

def test_repeated_identifiers_get_separate_entries():
    """REGRESSION PIN (Codex 95fcecf): if `expected = ['a','a','b']`,
    the trace produces THREE per-identifier entries — one per
    occurrence — with distinct output positions for the Nth match in
    `emitted`."""
    rpt = _make_report(
        expected=["stageA0_4_857", "stageA0_4_857", "stageD3_4_857"],
        emitted=["stageA0_4_857", "stageD3_4_857"],
        copied=["stageA0_4_857", "stageD3_4_857"],
        coverage=2/3,
    )
    trace = build_v0_trace(rpt)
    entries = trace["copy"]["per_identifier"]
    assert len(entries) == 3, (
        f"expected 3 per-identifier entries (one per occurrence in input); "
        f"got {len(entries)}"
    )
    # First "stageA0_4_857" occurrence: copied at output position 0
    assert entries[0]["identifier"] == "stageA0_4_857"
    assert entries[0]["status"] == "copied"
    assert entries[0]["position_in_input"] == 0
    assert entries[0]["position_in_output"] == 0
    # Second "stageA0_4_857" occurrence: model only emitted one — missed
    assert entries[1]["identifier"] == "stageA0_4_857"
    assert entries[1]["status"] == "missed"
    assert entries[1]["position_in_input"] == 1
    assert entries[1]["position_in_output"] is None
    # But identifier_ever_copied flag is True for stageA0_4_857 since
    # it appeared somewhere in the output
    assert entries[1]["identifier_ever_copied"] is True
    # Third "stageD3_4_857": copied at output position 1
    assert entries[2]["identifier"] == "stageD3_4_857"
    assert entries[2]["status"] == "copied"
    assert entries[2]["position_in_output"] == 1


def test_per_identifier_handles_missed_identifier_never_emitted():
    rpt = _make_report(
        expected=["a", "b"], emitted=[], copied=[], coverage=0.0,
    )
    trace = build_v0_trace(rpt)
    entries = trace["copy"]["per_identifier"]
    assert len(entries) == 2
    for e in entries:
        assert e["status"] == "missed"
        assert e["position_in_output"] is None
        assert e["identifier_ever_copied"] is False


# ---------------------------------------------------------------------------
# Warning flags — do NOT fire on identifier-free inputs (Codex audit fix)
# ---------------------------------------------------------------------------

def test_no_warnings_when_expression_has_no_identifiers():
    """REGRESSION PIN (Codex 95fcecf): a bare state expression like
    `^3^P|A` has zero expected identifiers and must not produce
    identifier-related warning flags."""
    rpt = _make_report(
        cas_expression="^3^P|A",
        generated="A principled aversion expressed through analytical intuition.",
        expected=[],
        emitted=[],
        copied=[],
        coverage=None,
    )
    trace = build_v0_trace(rpt)
    flag_kinds = {f["kind"] for f in trace["confidence"]["warning_flags"]}
    # The identifier-related warnings MUST NOT fire
    assert "low_coverage" not in flag_kinds
    assert "no_identifiers_emitted" not in flag_kinds


def test_low_coverage_warning_fires_when_expected_has_identifiers():
    rpt = _make_report(
        expected=["a", "b", "c"], emitted=["a"], copied=["a"], coverage=0.333,
    )
    trace = build_v0_trace(rpt)
    flag_kinds = {f["kind"] for f in trace["confidence"]["warning_flags"]}
    assert "low_coverage" in flag_kinds


def test_no_identifiers_emitted_warning_fires_when_expected_nonempty():
    rpt = _make_report(
        expected=["a", "b"], emitted=[], copied=[], coverage=0.0,
    )
    trace = build_v0_trace(rpt)
    flag_kinds = {f["kind"] for f in trace["confidence"]["warning_flags"]}
    assert "no_identifiers_emitted" in flag_kinds


def test_slow_decode_warning_fires():
    rpt = _make_report(decode_seconds=15.0)
    trace = build_v0_trace(rpt)
    flag_kinds = {f["kind"] for f in trace["confidence"]["warning_flags"]}
    assert "slow_decode" in flag_kinds


def test_decode_crash_warning():
    rpt = _make_report(gates={
        "no_crash": False,
        "generated_non_empty": True,
        "ge_one_identifier_copied": False,
    })
    trace = build_v0_trace(rpt)
    flag_kinds = {f["kind"] for f in trace["confidence"]["warning_flags"]}
    assert "decode_crash" in flag_kinds


def test_empty_output_warning():
    rpt = _make_report(
        generated="",
        gates={
            "no_crash": True,
            "generated_non_empty": False,
            "ge_one_identifier_copied": False,
        },
    )
    trace = build_v0_trace(rpt)
    flag_kinds = {f["kind"] for f in trace["confidence"]["warning_flags"]}
    assert "empty_output" in flag_kinds


# ---------------------------------------------------------------------------
# Thought Tree embedding — flat nodes + edges (Codex audit fix)
# ---------------------------------------------------------------------------

def test_thought_tree_has_flat_nodes_array():
    """REGRESSION PIN (Codex 95fcecf): Thought Tree must include flat
    `nodes` and `edges` arrays alongside the nested `root`."""
    trace = build_v0_trace(_make_report(
        expected=["a", "b"], emitted=["a"], copied=["a"], coverage=0.5,
    ))
    tree = trace["thought_tree"]
    assert "nodes" in tree, "thought_tree must include flat nodes array"
    assert "edges" in tree, "thought_tree must include flat edges array"
    assert isinstance(tree["nodes"], list)
    assert isinstance(tree["edges"], list)


def test_flat_nodes_have_stable_ids():
    trace = build_v0_trace(_make_report(
        expected=["a"], emitted=["a"], copied=["a"], coverage=1.0,
    ))
    tree = trace["thought_tree"]
    ids = [n["id"] for n in tree["nodes"]]
    # IDs follow the documented pattern n0, n1, n2, ...
    assert ids == [f"n{i}" for i in range(len(ids))]
    # No duplicate IDs
    assert len(set(ids)) == len(ids)


def test_flat_edges_reference_real_node_ids():
    trace = build_v0_trace(_make_report(
        expected=["a", "b"], emitted=["a"], copied=["a"], coverage=0.5,
    ))
    tree = trace["thought_tree"]
    node_ids = {n["id"] for n in tree["nodes"]}
    for e in tree["edges"]:
        assert e["source"] in node_ids
        assert e["target"] in node_ids
        assert e["kind"] == "parent_child"


def test_edge_count_matches_nodes_minus_one():
    """For any tree, edges = nodes - 1."""
    trace = build_v0_trace(_make_report(
        expected=["a", "b", "c"], emitted=["a"], copied=["a"], coverage=0.333,
    ))
    tree = trace["thought_tree"]
    assert len(tree["edges"]) == len(tree["nodes"]) - 1


# ---------------------------------------------------------------------------
# Confidence layer
# ---------------------------------------------------------------------------

def test_confidence_layer_carries_qualitative_coverage():
    trace = build_v0_trace(_make_report())
    assert trace["confidence"]["qualitative_coverage"] == "strong"


def test_confidence_caveats_include_plain_english_caveat():
    rpt = _make_report(plain={
        "short_answer": "ok",
        "plain_meaning": "ok",
        "qualitative_coverage": "weak",
        "qualitative_slot_quality": "ok",
        "confidence_caveat": "the model was uncertain",
    })
    trace = build_v0_trace(rpt)
    assert "the model was uncertain" in trace["confidence"]["caveats"]


# ---------------------------------------------------------------------------
# Slot trace layer
# ---------------------------------------------------------------------------

def test_slot_counts_use_human_labels():
    """`slot_counts_by_label` translates raw slot ids to human labels.
    Slot id 2 = STAGE_VAR = 'named identifier' per the plain_english
    translator."""
    rpt = _make_report(slot_summary={
        "length": 25, "counts": {"0": 18, "2": 7},
        "longest_stage_var_run": 4,
    })
    trace = build_v0_trace(rpt)
    labels = trace["slot_trace"]["slot_counts_by_label"]
    assert "joining word" in labels
    assert "named identifier" in labels
    assert labels["joining word"] == 18
    assert labels["named identifier"] == 7


def test_slot_trace_carries_length_and_longest_run():
    rpt = _make_report(slot_summary={
        "length": 49, "counts": {"0": 32, "2": 17},
        "longest_stage_var_run": 9,
    })
    trace = build_v0_trace(rpt)
    assert trace["slot_trace"]["length"] == 49
    assert trace["slot_trace"]["longest_stage_var_run"] == 9


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

def test_trace_round_trips_through_json():
    trace = build_v0_trace(_make_report(
        expected=["stageA0_4_857"],
        emitted=["stageA0_4_857"],
        copied=["stageA0_4_857"],
        coverage=1.0,
    ))
    blob = trace_to_json(trace)
    reloaded = json.loads(blob)
    assert reloaded["schema_version"] == "trace_v0"
    assert reloaded["copy"]["copied_identifiers"] == ["stageA0_4_857"]
    assert reloaded["thought_tree"]["node_count"] == trace["thought_tree"]["node_count"]


def test_trace_to_json_returns_valid_json_string():
    trace = build_v0_trace(_make_report())
    s = trace_to_json(trace)
    parsed = json.loads(s)
    assert parsed["schema_version"] == "trace_v0"


# ---------------------------------------------------------------------------
# Output layer
# ---------------------------------------------------------------------------

def test_output_layer_carries_english_and_n_tokens():
    trace = build_v0_trace(_make_report(
        generated="hello world", n_tokens=42,
    ))
    assert trace["output"]["english"] == "hello world"
    assert trace["output"]["n_tokens"] == 42
