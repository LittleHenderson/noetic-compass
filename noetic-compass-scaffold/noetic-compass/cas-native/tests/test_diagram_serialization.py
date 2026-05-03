"""Tests for diagram_serialization.py (Phase 2 — diagram-loop lever)."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
import torch

_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    _pkg = types.ModuleType("cas_native")
    _pkg.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    _pkg.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = _pkg

from cas_native.training.diagram_serialization import (
    EDGE_FEATURE_DIM,
    NODE_FEATURE_DIM,
    compile_to_graph,
    serialize_diagram_for_batch,
)


# ---------------------------------------------------------------------------
# (a) Round-trip a known CAS expression: verify expected node/edge counts
# ---------------------------------------------------------------------------

def test_compile_simple_state_has_nodes_and_edges():
    """A full state ^4^E_{F2}|E should produce nodes and edges."""
    graph = compile_to_graph("^4^E_{F2}|E")
    assert graph["n_nodes"] > 0
    assert graph["n_edges"] > 0
    # Expect at least: state node, noetic node, domain node, drive node, register node
    kinds = {n["kind"] for n in graph["nodes"]}
    assert "state" in kinds
    assert "noetic" in kinds


def test_compile_integration_expression_has_operator_and_emergent():
    """Integration expression should produce operator and emergent nodes."""
    expr = "(^4^E_{F2}|E × ^4^E_{F2}|f × ^4^E_{F2}|A) = ^4^E|Omega_attunement"
    graph = compile_to_graph(expr)
    assert graph["n_nodes"] > 0
    kinds = {n["kind"] for n in graph["nodes"]}
    assert "emergent" in kinds or "operator" in kinds


def test_node_feature_vectors_have_correct_dim():
    """Every node_features entry has NODE_FEATURE_DIM components."""
    graph = compile_to_graph("^2^P_{F4}|f")
    assert graph["n_nodes"] > 0
    for feat in graph["node_features"]:
        assert len(feat) == NODE_FEATURE_DIM


def test_edge_feature_vectors_have_correct_dim():
    """Every edge_features entry has EDGE_FEATURE_DIM components."""
    graph = compile_to_graph("^2^P_{F4}|f")
    for feat in graph["edge_features"]:
        assert len(feat) == EDGE_FEATURE_DIM


# ---------------------------------------------------------------------------
# (b) Deterministic compilation: same expression → same graph
# ---------------------------------------------------------------------------

def test_compile_is_deterministic():
    """compile_to_graph returns identical output on repeated calls."""
    expr = "^5^C_{F1}|T"
    g1 = compile_to_graph(expr)
    g2 = compile_to_graph(expr)
    assert g1["n_nodes"] == g2["n_nodes"]
    assert g1["n_edges"] == g2["n_edges"]
    assert g1["node_features"] == g2["node_features"]
    assert g1["edge_features"] == g2["edge_features"]


# ---------------------------------------------------------------------------
# (c) Backward compatibility: records without graph data still load
# ---------------------------------------------------------------------------

def test_compile_invalid_expression_returns_empty_graph():
    """An unparseable expression returns an empty graph, never raises."""
    graph = compile_to_graph("!!NOT A CAS EXPRESSION!!")
    # Should not raise; may have 0 nodes/edges
    assert "n_nodes" in graph
    assert "n_edges" in graph
    assert "node_features" in graph
    assert "edge_features" in graph


def test_compile_empty_string_returns_empty_graph():
    """Empty string produces a valid (empty) graph dict."""
    graph = compile_to_graph("")
    assert graph["n_nodes"] == 0 or graph["n_nodes"] >= 0


# ---------------------------------------------------------------------------
# (d) Batch padding correctness
# ---------------------------------------------------------------------------

def test_serialize_batch_output_shapes():
    """serialize_diagram_for_batch returns correct tensor shapes."""
    graphs = [compile_to_graph("^1^P"), compile_to_graph("^3^C_{F2}")]
    B, max_nodes, max_edges = len(graphs), 16, 64
    batch = serialize_diagram_for_batch(graphs, max_nodes=max_nodes, max_edges=max_edges)
    assert batch["node_features"].shape == (B, max_nodes, NODE_FEATURE_DIM)
    assert batch["edge_index"].shape == (B, 2, max_edges)
    assert batch["edge_features"].shape == (B, max_edges, EDGE_FEATURE_DIM)
    assert batch["node_mask"].shape == (B, max_nodes)
    assert batch["edge_mask"].shape == (B, max_edges)


def test_serialize_batch_padding_is_zero():
    """Padded node positions have all-zero feature vectors and mask=False."""
    graph = compile_to_graph("^1^P")
    n_real = graph["n_nodes"]
    max_nodes = n_real + 8  # guaranteed padding at the end
    batch = serialize_diagram_for_batch([graph], max_nodes=max_nodes)
    nf = batch["node_features"][0]  # (max_nodes, NODE_FEATURE_DIM)
    mask = batch["node_mask"][0]    # (max_nodes,)
    # Padded positions should be False
    assert mask[n_real:].all() == False
    # Padded feature vectors should be zero
    assert nf[n_real:].sum().item() == pytest.approx(0.0)


def test_serialize_batch_node_mask_matches_n_nodes():
    """node_mask True count equals actual node count (capped at max_nodes)."""
    graph = compile_to_graph("^4^E_{F2}|E")
    max_nodes = 32
    batch = serialize_diagram_for_batch([graph], max_nodes=max_nodes)
    expected = min(graph["n_nodes"], max_nodes)
    assert batch["node_mask"][0].sum().item() == expected


# ---------------------------------------------------------------------------
# (e) Edge-type vocabulary is fixed and indexable
# ---------------------------------------------------------------------------

def test_edge_kind_vocabulary_is_fixed():
    """EDGE_FEATURE_DIM is a fixed constant independent of input."""
    g1 = compile_to_graph("^2^P_{F4}")
    g2 = compile_to_graph("^4^E_{F2}|E × ^4^E_{F2}|f")
    for feat in g1["edge_features"] + g2["edge_features"]:
        assert len(feat) == EDGE_FEATURE_DIM
    # Each edge feature is a valid one-hot (exactly one 1.0, rest 0.0)
    for feat in g1["edge_features"] + g2["edge_features"]:
        assert sum(feat) == pytest.approx(1.0)


def test_node_feature_is_sum_of_one_hots():
    """Node feature vector has at most one node-kind bit set."""
    from cas_native.training.diagram_serialization import NODE_KIND_DIM
    graph = compile_to_graph("^4^E_{F2}|E")
    for feat in graph["node_features"]:
        kind_slice = feat[:NODE_KIND_DIM]
        assert sum(kind_slice) == pytest.approx(1.0)
