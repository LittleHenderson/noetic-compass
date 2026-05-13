"""Tests for thought_tree builder.

Builds JSON-ready node-edge structures from synthetic cas-explain
reports. Pinned: node/edge counts for known inputs; canonical
graph-identity fields (kind + role + normalized_label); identifier
status correct; confidence node fires/skips on the right conditions.
"""
from __future__ import annotations

import json
import pytest

from cas_native.inference.thought_tree import (
    build_thought_tree,
    count_edges,
    count_nodes,
)


def _make_report(
    *,
    cas_expression: str = "let x = ^7^P_{F5}; x -> x",
    generated: str = "the model said something",
    expected: list[str] | None = None,
    emitted: list[str] | None = None,
    copied: list[str] | None = None,
    coverage: float | None = None,
    slot_summary: dict | None = None,
    plain: dict | None = None,
) -> dict:
    return {
        "input_cas_expression": cas_expression,
        "generated_english": generated,
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
    }


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------

def test_tree_has_documented_top_level_keys():
    """Per Codex audit 95fcecf: thought tree must include flat nodes
    and edges arrays alongside the nested root."""
    tree = build_thought_tree(_make_report())
    assert set(tree.keys()) == {
        "root", "nodes", "edges", "node_count", "edge_count",
    }


def test_tree_root_is_user_prompt():
    """Root is always the user_prompt node (the input CAS expression)."""
    tree = build_thought_tree(_make_report(cas_expression="^3^P|A"))
    assert tree["root"]["kind"] == "user_prompt"
    assert tree["root"]["role"] == "input"
    assert "^3^P|A" in tree["root"]["text"]


def test_root_has_model_generation_child():
    tree = build_thought_tree(_make_report())
    root = tree["root"]
    children = root.get("children", [])
    assert len(children) == 1
    assert children[0]["kind"] == "model_generation"


def test_canonical_graph_identity_fields_present():
    """Per cas_thought_tree_idea_atlas audit: every node carries
    kind + role + label + normalized_label. Pin all four on the root."""
    tree = build_thought_tree(_make_report())
    root = tree["root"]
    assert "kind" in root
    assert "role" in root
    assert "label" in root
    assert "normalized_label" in root


# ---------------------------------------------------------------------------
# Identifier attempts
# ---------------------------------------------------------------------------

def test_per_identifier_children_built():
    """Each expected identifier becomes a child of the model_generation
    node with status copied|missed."""
    rpt = _make_report(
        expected=["stageA0_4_857", "stageD3_4_857", "stageW6_4_857"],
        emitted=["stageA0_4_857", "stageD3_4_857"],
        copied=["stageA0_4_857", "stageD3_4_857"],
        coverage=0.667,
    )
    tree = build_thought_tree(rpt)
    gen = tree["root"]["children"][0]
    ident_nodes = [c for c in gen["children"] if c["kind"] == "identifier_attempt"]
    assert len(ident_nodes) == 3
    labels = {n["label"]: n["role"] for n in ident_nodes}
    assert labels["stageA0_4_857"] == "copied"
    assert labels["stageD3_4_857"] == "copied"
    assert labels["stageW6_4_857"] == "missed"


def test_identifier_positions_recorded():
    """input_position and output_position are populated for copied IDs."""
    rpt = _make_report(
        expected=["a", "b", "c"],
        emitted=["a", "c"],
        copied=["a", "c"],
        coverage=0.667,
    )
    tree = build_thought_tree(rpt)
    gen = tree["root"]["children"][0]
    by_label = {c["label"]: c for c in gen["children"]
                if c["kind"] == "identifier_attempt"}
    assert by_label["a"]["axis_attrs"]["input_position"] == 0
    assert by_label["a"]["axis_attrs"]["output_position"] == 0
    assert by_label["b"]["axis_attrs"]["input_position"] == 1
    assert by_label["b"]["axis_attrs"]["output_position"] is None
    assert by_label["c"]["axis_attrs"]["input_position"] == 2
    assert by_label["c"]["axis_attrs"]["output_position"] == 1


# ---------------------------------------------------------------------------
# Slot pattern node
# ---------------------------------------------------------------------------

def test_slot_pattern_node_present():
    tree = build_thought_tree(_make_report())
    gen = tree["root"]["children"][0]
    slot_nodes = [c for c in gen["children"] if c["kind"] == "slot_pattern"]
    assert len(slot_nodes) == 1


def test_slot_pattern_describes_long_run():
    """Longest run >= 5 yields the 'long identifier sequence' description."""
    rpt = _make_report(slot_summary={
        "length": 49, "counts": {"0": 32, "2": 17},
        "longest_stage_var_run": 9,
    })
    tree = build_thought_tree(rpt)
    slot_node = [c for c in tree["root"]["children"][0]["children"]
                 if c["kind"] == "slot_pattern"][0]
    assert "long identifier" in slot_node["label"]


def test_slot_pattern_zero_tokens():
    rpt = _make_report(slot_summary={"length": 0, "counts": {},
                                      "longest_stage_var_run": 0})
    tree = build_thought_tree(rpt)
    slot_node = [c for c in tree["root"]["children"][0]["children"]
                 if c["kind"] == "slot_pattern"][0]
    assert slot_node["label"] == "no tokens generated"


# ---------------------------------------------------------------------------
# Confidence node
# ---------------------------------------------------------------------------

def test_confidence_node_skipped_when_strong_and_no_caveat():
    """No confidence marker when coverage is strong and no caveat —
    don't clutter the tree with 'we're confident' nodes."""
    rpt = _make_report(plain={
        "short_answer": "ok",
        "plain_meaning": "ok",
        "qualitative_coverage": "strong",
        "qualitative_slot_quality": "ok",
        "confidence_caveat": None,
    })
    tree = build_thought_tree(rpt)
    gen = tree["root"]["children"][0]
    conf_nodes = [c for c in gen["children"] if c["kind"] == "confidence_marker"]
    assert conf_nodes == []


def test_confidence_node_fires_on_weak_coverage():
    rpt = _make_report(plain={
        "short_answer": "ok",
        "plain_meaning": "ok",
        "qualitative_coverage": "weak",
        "qualitative_slot_quality": "ok",
        "confidence_caveat": None,
    })
    tree = build_thought_tree(rpt)
    gen = tree["root"]["children"][0]
    conf_nodes = [c for c in gen["children"] if c["kind"] == "confidence_marker"]
    assert len(conf_nodes) == 1
    assert conf_nodes[0]["role"] == "weak"


def test_confidence_node_fires_on_caveat():
    rpt = _make_report(plain={
        "short_answer": "ok",
        "plain_meaning": "ok",
        "qualitative_coverage": "strong",
        "qualitative_slot_quality": "ok",
        "confidence_caveat": "the model was uncertain",
    })
    tree = build_thought_tree(rpt)
    gen = tree["root"]["children"][0]
    conf_nodes = [c for c in gen["children"] if c["kind"] == "confidence_marker"]
    assert len(conf_nodes) == 1


# ---------------------------------------------------------------------------
# Node + edge counts
# ---------------------------------------------------------------------------

def test_node_count_zero_identifiers():
    """3 nodes: user_prompt + model_generation + slot_pattern."""
    rpt = _make_report(expected=[], emitted=[], copied=[])
    tree = build_thought_tree(rpt)
    assert tree["node_count"] == 3
    assert tree["edge_count"] == 2  # root→gen, gen→slot


def test_node_count_with_3_identifiers_and_caveat():
    """user_prompt + model_generation + 3 identifier_attempt + slot_pattern
    + confidence_marker = 7 nodes."""
    rpt = _make_report(
        expected=["a", "b", "c"], emitted=["a"], copied=["a"], coverage=0.333,
        plain={
            "short_answer": "ok", "plain_meaning": "ok",
            "qualitative_coverage": "weak",
            "qualitative_slot_quality": "ok",
            "confidence_caveat": "low coverage",
        },
    )
    tree = build_thought_tree(rpt)
    assert tree["node_count"] == 7
    # edges: root→gen (1) + gen→[3 idents + slot + confidence] (5) = 6
    assert tree["edge_count"] == 6


def test_count_nodes_handles_empty_dict():
    assert count_nodes({}) == 1
    assert count_nodes({"children": []}) == 1


def test_count_edges_handles_leaf():
    assert count_edges({"children": []}) == 0


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

def test_tree_round_trips_through_json():
    tree = build_thought_tree(_make_report(
        expected=["stageA0_4_857"],
        emitted=["stageA0_4_857"],
        copied=["stageA0_4_857"],
        coverage=1.0,
    ))
    blob = json.dumps(tree, default=str)
    reloaded = json.loads(blob)
    assert reloaded["node_count"] == tree["node_count"]
    assert reloaded["root"]["kind"] == "user_prompt"
