"""Unit tests for probe_runner — the pure-functional pieces that don't need
torch. These guarantees survive across milestones because the schema +
math here are the cockpit's contract, not the runtime's."""

from __future__ import annotations

from app.runtime.probe_runner import (
    CaptureState,
    _mode7_edges_from_attentions,
    _softmax_margin,
    _top_k_neurons,
    resolve_probes,
    summarise,
)


def test_resolve_probes_empty_defaults_to_full_pipeline():
    out = resolve_probes([])
    assert "active_trace" in out
    assert "blindspot_covers" in out
    assert "mode7_attribution" in out
    assert "confidence_margin" in out


def test_resolve_probes_preserves_user_order_and_dedupes():
    out = resolve_probes(["mode7_attribution", "active_trace", "active_trace"])
    assert out == ("mode7_attribution", "active_trace")


def test_resolve_probes_accepts_legacy_blindspots_f1_alias():
    out = resolve_probes(["blindspots_f1", "blindspot_covers"])
    assert out == ("blindspot_covers",)


def test_top_k_returns_signed_activations_sorted_by_magnitude():
    state = CaptureState()
    # Layer 0 has a strong negative + a small positive; layer 1 has a
    # strong positive. Top-2 should be the two strongest by magnitude
    # regardless of sign.
    state.mlp_post = {
        0: [-0.9, 0.05, 0.01],
        1: [0.8, 0.02, -0.03],
    }
    out = _top_k_neurons(state, k=2)
    assert len(out) == 2
    # Signed values preserved in the output.
    activations = [(e["layer"], e["index"], e["activation"]) for e in out]
    assert (0, 0, -0.9) in activations
    assert (1, 0, 0.8) in activations


def test_top_k_handles_empty_state():
    assert _top_k_neurons(CaptureState(), k=8) == []


def test_top_k_honors_layer_filter():
    state = CaptureState()
    state.mlp_post = {
        0: [9.0],
        5: [0.5, -0.4],
    }
    out = _top_k_neurons(state, k=4, layer_filter={5})
    assert out == [
        {"layer": 5, "index": 0, "activation": 0.5},
        {"layer": 5, "index": 1, "activation": -0.4},
    ]


def test_softmax_margin_none_logits_is_none():
    assert _softmax_margin(None) is None
    assert _softmax_margin([]) is None


def test_softmax_margin_saturates_at_one():
    # Logit margin >> MARGIN_SAT (6.0) -> confidence 1.0.
    assert _softmax_margin([10.0, 0.0, -5.0]) == 1.0


def test_softmax_margin_scales_linearly_below_saturation():
    # margin = 3.0 -> 3.0 / 6.0 = 0.5
    assert _softmax_margin([4.0, 1.0, 0.0]) == 0.5
    # margin = 0.6 -> 0.1
    assert _softmax_margin([1.6, 1.0]) == 0.1


def test_softmax_margin_clamps_at_zero():
    # Degenerate tie -> 0.0 confidence.
    assert _softmax_margin([5.0, 5.0]) == 0.0


def test_mode7_edges_first_token_is_self_edge_from_none():
    edges = _mode7_edges_from_attentions(None, token_index=0)
    assert edges == [{"from_token_index": None, "to_token_index": 0, "weight": 1.0}]


def test_mode7_edges_empty_attentions_after_first_token_returns_empty():
    assert _mode7_edges_from_attentions(None, token_index=3) == []
    assert _mode7_edges_from_attentions([], token_index=3) == []


def test_summarise_assembles_full_token_payload():
    # Smoke: with empty capture state we still get a well-typed result.
    out = summarise(CaptureState(), token_index=0, attentions=None, top_k=4)
    assert out.top_activated_neurons == []
    assert out.mode7_edges == [{"from_token_index": None, "to_token_index": 0, "weight": 1.0}]
    assert out.confidence is None
