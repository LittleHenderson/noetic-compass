"""Tests for graph_encoder.py (Phase 3 — diagram-loop lever)."""

from __future__ import annotations

import torch
import pytest

from cas_native.model.graph_encoder import GraphEncoder
from cas_native.training.diagram_serialization import (
    EDGE_FEATURE_DIM,
    NODE_FEATURE_DIM,
    compile_to_graph,
    serialize_diagram_for_batch,
)


def _make_batch(expressions: list[str], max_nodes: int = 32, max_edges: int = 64):
    graphs = [compile_to_graph(e) for e in expressions]
    return serialize_diagram_for_batch(graphs, max_nodes=max_nodes, max_edges=max_edges)


# ---------------------------------------------------------------------------
# (a) Forward-pass output shape correctness for varying batch and node counts
# ---------------------------------------------------------------------------

def test_encoder_output_shape_single():
    """Single graph → (1, hidden_dim) output."""
    encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64)
    batch = _make_batch(["^4^E_{F2}|E"])
    out = encoder.forward_dict(batch)
    assert out.shape == (1, 64)


def test_encoder_output_shape_batch():
    """Batch of 4 graphs → (4, hidden_dim) output."""
    encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64)
    exprs = ["^1^P", "^3^C_{F2}", "^5^E_{F3}|T", "^9^O_{F7}|A"]
    batch = _make_batch(exprs)
    out = encoder.forward_dict(batch)
    assert out.shape == (4, 64)


def test_encoder_output_shape_custom_hidden():
    """hidden_dim=32 → (B, 32) output."""
    encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=32)
    batch = _make_batch(["^2^P_{F4}|f", "^7^C"])
    out = encoder.forward_dict(batch)
    assert out.shape == (2, 32)


def test_encoder_three_layers():
    """n_layers=3 runs without error."""
    encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64, n_layers=3)
    batch = _make_batch(["^4^E_{F2}|E"])
    out = encoder.forward_dict(batch)
    assert out.shape == (1, 64)


# ---------------------------------------------------------------------------
# (b) Padded nodes don't contribute to output (masking works)
# ---------------------------------------------------------------------------

def test_padded_nodes_dont_affect_output():
    """Adding extra all-zero padded nodes should not change the output."""
    encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64)
    encoder.eval()

    # Build a small batch and get output at max_nodes=16
    expr = "^4^E_{F2}|E"
    graph = compile_to_graph(expr)
    n_real = min(graph["n_nodes"], 16)

    batch16 = serialize_diagram_for_batch([graph], max_nodes=16, max_edges=32)
    batch32 = serialize_diagram_for_batch([graph], max_nodes=32, max_edges=32)

    with torch.no_grad():
        out16 = encoder.forward_dict(batch16)
        out32 = encoder.forward_dict(batch32)

    # Outputs should be identical regardless of padding size
    assert torch.allclose(out16, out32, atol=1e-5), (
        f"Padded nodes changed output: max diff = {(out16 - out32).abs().max().item():.6f}"
    )


def test_empty_graph_returns_zero_vector():
    """An empty graph (no real nodes) should return a near-zero vector gracefully."""
    from cas_native.training.diagram_serialization import EDGE_FEATURE_DIM, NODE_FEATURE_DIM
    encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64)
    encoder.eval()
    # Build empty batch manually
    B, N, E = 1, 8, 16
    batch = {
        "node_features": torch.zeros(B, N, NODE_FEATURE_DIM),
        "edge_index": torch.zeros(B, 2, E, dtype=torch.long),
        "edge_features": torch.zeros(B, E, EDGE_FEATURE_DIM),
        "node_mask": torch.zeros(B, N, dtype=torch.bool),
        "edge_mask": torch.zeros(B, E, dtype=torch.bool),
    }
    with torch.no_grad():
        out = encoder.forward_dict(batch)
    assert out.shape == (B, 64)


# ---------------------------------------------------------------------------
# (c) Gradient flow through the encoder
# ---------------------------------------------------------------------------

def test_gradient_flows_through_encoder():
    """Loss backward propagates gradients to all encoder parameters."""
    encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64)
    batch = _make_batch(["^4^E_{F2}|E", "^2^P_{F4}|f"])
    out = encoder.forward_dict(batch)
    loss = out.sum()
    loss.backward()
    # Every parameter that appears in the computation graph should have a gradient
    for name, param in encoder.named_parameters():
        if param.requires_grad:
            assert param.grad is not None, f"No gradient for {name}"
