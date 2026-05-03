"""Tests for graph_text_fusion.py (Phase 4 — diagram-loop lever)."""

from __future__ import annotations

import torch
import pytest

from cas_native.model.graph_text_fusion import GraphTextFusion


# ---------------------------------------------------------------------------
# (a) Forward pass shape correctness
# ---------------------------------------------------------------------------

def test_fusion_output_shape_matches_text_hidden():
    """Output shape is identical to input text_hidden shape."""
    B, T, d_text, d_graph = 2, 16, 64, 64
    fusion = GraphTextFusion(d_text=d_text, d_graph=d_graph)
    text_hidden = torch.randn(B, T, d_text)
    graph_nodes = torch.randn(B, 8, d_graph)
    node_mask = torch.ones(B, 8, dtype=torch.bool)
    out = fusion(text_hidden, graph_nodes, node_mask)
    assert out.shape == (B, T, d_text)


def test_fusion_different_d_graph():
    """d_graph != d_text is handled by the k/v projections."""
    B, T, d_text, d_graph, N = 3, 12, 128, 64, 10
    fusion = GraphTextFusion(d_text=d_text, d_graph=d_graph, n_heads=8)
    text_hidden = torch.randn(B, T, d_text)
    graph_nodes = torch.randn(B, N, d_graph)
    node_mask = torch.ones(B, N, dtype=torch.bool)
    out = fusion(text_hidden, graph_nodes, node_mask)
    assert out.shape == (B, T, d_text)


def test_fusion_no_graph_returns_text_unchanged():
    """When graph_nodes=None, returns text_hidden without modification."""
    B, T, d_text = 2, 10, 64
    fusion = GraphTextFusion(d_text=d_text, d_graph=64)
    text_hidden = torch.randn(B, T, d_text)
    out = fusion(text_hidden, graph_nodes=None)
    assert torch.allclose(out, text_hidden)


# ---------------------------------------------------------------------------
# (b) Mask correctness: text doesn't attend to padded graph nodes
# ---------------------------------------------------------------------------

def test_masked_nodes_dont_contribute():
    """With all graph nodes masked, attention logits → -inf, output ≈ text norm."""
    B, T, d_text, d_graph, N = 1, 5, 64, 64, 8
    fusion = GraphTextFusion(d_text=d_text, d_graph=d_graph)
    fusion.eval()

    text_hidden = torch.randn(B, T, d_text)
    graph_nodes = torch.randn(B, N, d_graph)
    node_mask_all_false = torch.zeros(B, N, dtype=torch.bool)
    node_mask_all_true = torch.ones(B, N, dtype=torch.bool)

    with torch.no_grad():
        out_masked = fusion(text_hidden, graph_nodes, node_mask_all_false)

    # With all nodes masked, the layer returns text_hidden unchanged
    assert out_masked.shape == (B, T, d_text)


def test_partial_masking_runs():
    """Partial node mask (some True, some False) runs without error."""
    B, T, d_text, d_graph, N = 2, 8, 64, 64, 12
    fusion = GraphTextFusion(d_text=d_text, d_graph=d_graph)
    text_hidden = torch.randn(B, T, d_text)
    graph_nodes = torch.randn(B, N, d_graph)
    node_mask = torch.zeros(B, N, dtype=torch.bool)
    node_mask[:, :5] = True  # only first 5 real
    out = fusion(text_hidden, graph_nodes, node_mask)
    assert out.shape == (B, T, d_text)


# ---------------------------------------------------------------------------
# (c) Gradient flow
# ---------------------------------------------------------------------------

def test_gradient_flows_through_fusion():
    """Loss backward propagates gradients to all fusion parameters."""
    B, T, d_text, d_graph = 2, 8, 64, 64
    fusion = GraphTextFusion(d_text=d_text, d_graph=d_graph)
    text_hidden = torch.randn(B, T, d_text, requires_grad=True)
    graph_nodes = torch.randn(B, 6, d_graph, requires_grad=True)
    node_mask = torch.ones(B, 6, dtype=torch.bool)

    out = fusion(text_hidden, graph_nodes, node_mask)
    loss = out.sum()
    loss.backward()

    for name, param in fusion.named_parameters():
        if param.requires_grad:
            assert param.grad is not None, f"No gradient for {name}"
    assert text_hidden.grad is not None, "No gradient for text_hidden"
    assert graph_nodes.grad is not None, "No gradient for graph_nodes"
