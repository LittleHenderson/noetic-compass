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
    verification: dict | None = None,
    evidence_packet_trace_id: str | None = None,
) -> dict:
    report = {
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
    if verification is not None:
        report["verification"] = verification
    if evidence_packet_trace_id is not None:
        report["evidence_packet_trace_id"] = evidence_packet_trace_id
    return report


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


# ---------------------------------------------------------------------------
# Canonical graph identity keys (Codex audit 7926698 — keys must live
# in the trace, not be UI-derived)
# ---------------------------------------------------------------------------

def test_each_flat_node_has_canonical_node_key():
    """REGRESSION PIN: every flat node carries a canonical `node_key`
    so the future Atlas can recognize the same idea across renders."""
    tree = build_thought_tree(_make_report(
        expected=["a"], emitted=["a"], copied=["a"], coverage=1.0,
    ))
    for node in tree["nodes"]:
        assert "node_key" in node, (
            "every flat node must carry a canonical node_key"
        )
        assert isinstance(node["node_key"], str)
        assert node["node_key"], "node_key must be non-empty"


def test_node_key_combines_kind_role_normalized_label_axis_attrs():
    """Canonical key shape per Codex f3f59fa:
    node_key = kind + role + normalized_label + axis_attrs.
    Pipe-separated."""
    tree = build_thought_tree(_make_report(
        expected=["stageA0_4_857"], emitted=["stageA0_4_857"],
        copied=["stageA0_4_857"], coverage=1.0,
    ))
    # The identifier_attempt node has axis_attrs and a role of 'copied'
    ident_node = next(
        n for n in tree["nodes"]
        if n["kind"] == "identifier_attempt"
    )
    key = ident_node["node_key"]
    parts = key.split("|")
    # 4 parts: kind, role, normalized_label, axis_attrs
    assert len(parts) == 4
    assert parts[0] == "identifier_attempt"
    assert parts[1] == "copied"
    # normalized_label is lowercased (per _node()) — that's the
    # canonical form so two nodes with the same identifier match
    # regardless of casing in the source.
    assert parts[2] == "stagea0_4_857"
    # axis_attrs includes input_position + output_position + status
    assert "input_position=" in parts[3]


def test_same_semantic_node_produces_same_key():
    """Two identifier_attempt nodes with the same identifier + status +
    positions produce the same canonical key. This is the property
    that lets the future Atlas dedupe the same idea seen in multiple
    turns."""
    rpt1 = _make_report(
        expected=["x"], emitted=["x"], copied=["x"], coverage=1.0,
    )
    rpt2 = _make_report(
        expected=["x"], emitted=["x"], copied=["x"], coverage=1.0,
    )
    t1 = build_thought_tree(rpt1)
    t2 = build_thought_tree(rpt2)
    ident1 = next(n for n in t1["nodes"] if n["kind"] == "identifier_attempt")
    ident2 = next(n for n in t2["nodes"] if n["kind"] == "identifier_attempt")
    assert ident1["node_key"] == ident2["node_key"]


def test_different_status_produces_different_key():
    """A copied identifier and a missed identifier with the same name
    produce DIFFERENT canonical keys — they are semantically
    different events."""
    t_copied = build_thought_tree(_make_report(
        expected=["x"], emitted=["x"], copied=["x"], coverage=1.0,
    ))
    t_missed = build_thought_tree(_make_report(
        expected=["x"], emitted=[], copied=[], coverage=0.0,
    ))
    ident_copied = next(
        n for n in t_copied["nodes"] if n["kind"] == "identifier_attempt"
    )
    ident_missed = next(
        n for n in t_missed["nodes"] if n["kind"] == "identifier_attempt"
    )
    assert ident_copied["node_key"] != ident_missed["node_key"]


def test_each_flat_edge_has_canonical_edge_key():
    """Every edge carries a canonical edge_key built from
    source_key + target_key + kind + label."""
    tree = build_thought_tree(_make_report(
        expected=["a"], emitted=["a"], copied=["a"], coverage=1.0,
    ))
    for edge in tree["edges"]:
        assert "edge_key" in edge
        assert "source_key" in edge
        assert "target_key" in edge
        assert isinstance(edge["edge_key"], str)
        assert edge["edge_key"], "edge_key must be non-empty"
        # The edge_key contains the source_key and target_key
        assert edge["source_key"] in edge["edge_key"]
        assert edge["target_key"] in edge["edge_key"]


def test_node_key_stamped_on_nested_view_too():
    """The id+node_key live in both flat AND nested views so the UI
    can use either consistently."""
    tree = build_thought_tree(_make_report())
    assert "node_key" in tree["root"]
    assert "id" in tree["root"]
    # Flat array's n0 has the same node_key as nested root
    flat_root = next(n for n in tree["nodes"] if n["id"] == tree["root"]["id"])
    assert flat_root["node_key"] == tree["root"]["node_key"]


# ---------------------------------------------------------------------------
# Stage 21C EvidencePacket producer linkage
# ---------------------------------------------------------------------------

def test_model_generation_node_carries_evidence_packet_trace_id():
    """Stage 21C: runtime verification metadata must reach the Atlas node.

    The drawer button only appears when selectedNode.verification carries
    evidence_packet_trace_id. The producer should attach that link without
    changing old traces or using oracle correctness labels.
    """
    rpt = _make_report(
        verification={
            "decision": "ACCEPT",
            "decision_tier": "high",
            "accepted": True,
            "ensemble_agreement": True,
        },
        evidence_packet_trace_id="stage21a_allow_qwen15b_000",
    )
    tree = build_thought_tree(rpt)
    nested_gen = tree["root"]["children"][0]
    flat_gen = next(n for n in tree["nodes"] if n["kind"] == "model_generation")

    for node in (nested_gen, flat_gen):
        assert node["verification"]["decision"] == "ACCEPT"
        assert node["verification"]["decision_tier"] == "high"
        assert (
            node["verification"]["evidence_packet_trace_id"]
            == "stage21a_allow_qwen15b_000"
        )


def test_verification_embedded_trace_id_is_preserved():
    rpt = _make_report(
        verification={
            "decision": "SUPPRESS",
            "decision_tier": "suppress",
            "suppression_reasons": ["factor_conflicted"],
            "evidence_packet_trace_id": "stage21a_suppress_olmo1b_054",
        }
    )
    tree = build_thought_tree(rpt)
    flat_gen = next(n for n in tree["nodes"] if n["kind"] == "model_generation")
    assert (
        flat_gen["verification"]["evidence_packet_trace_id"]
        == "stage21a_suppress_olmo1b_054"
    )
    assert flat_gen["verification"]["suppression_reasons"] == ["factor_conflicted"]


def test_no_verification_field_for_legacy_reports():
    tree = build_thought_tree(_make_report())
    flat_gen = next(n for n in tree["nodes"] if n["kind"] == "model_generation")
    assert "verification" not in flat_gen
    assert "verification" not in tree["root"]["children"][0]
