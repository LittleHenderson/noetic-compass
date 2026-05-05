"""Live PyTorch hook capture tests for Mode 7.

These exercise the REAL forward-hook path (``capture_live_trace``) on a
real ``StructuredTokenStructuredPredictor`` instance. No checkpoint is
loaded — the model is constructed in-process with random init so the
tests stay hermetic and fast — but the wire-up (hooks fire, attribution
flows, JSON serialization works, hooks are cleaned up) is identical to
what runs at inference time against the K=9 baseline checkpoint.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from cas_native.model import (
    StructuredPredictionHead,
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.tokenizer import StructuredTokenVocabulary, tokenize
from cas_native.trace.live_capture import (
    HEAD_ATTR_NAMES,
    LiveTrace,
    capture_live_trace,
)
from cas_native.training.structured_token_adapter import (
    tokens_to_structured_token_batch,
)


# ---------------------------------------------------------------------------
# Test fixtures: small in-process model + batch
# ---------------------------------------------------------------------------


def _build_model_and_batch(*, d_model: int = 32, bottleneck_dim: int = 16):
    sequences = [
        tokenize("I feel drawn to the idea of structure"),
    ]
    vocab = StructuredTokenVocabulary.from_token_sequences(sequences)
    batch = tokens_to_structured_token_batch(sequences, vocab, max_length=24)
    embedding = StructuredTokenEmbedding(
        vocab_size=len(vocab), d_model=d_model, dropout=0.0
    )
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)
    model = StructuredTokenStructuredPredictor(embedding, head)
    model.eval()
    return model, batch, vocab


# ---------------------------------------------------------------------------
# 1. Hooks register and clean up
# ---------------------------------------------------------------------------


def test_hooks_register_and_cleanup():
    """Hooks must be added to the model before the forward and removed after.

    We snapshot ``len(module._forward_hooks)`` for the bottleneck, every head,
    and the embedding before, during, and after; the post-forward count must
    equal the pre-forward count for every hooked module.
    """
    model, batch, _ = _build_model_and_batch()

    head_module = model.head
    targets = [
        ("backbone", head_module.backbone),
        ("embedding", model.embedding),
    ]
    for attr in HEAD_ATTR_NAMES:
        sub = getattr(head_module, attr, None)
        if sub is not None:
            targets.append((attr, sub))

    pre_counts = {name: len(mod._forward_hooks) for name, mod in targets}

    outputs, trace = capture_live_trace(
        model, batch, input_text="hooks-test", top_k=4
    )

    post_counts = {name: len(mod._forward_hooks) for name, mod in targets}
    for name in pre_counts:
        assert post_counts[name] == pre_counts[name], (
            f"hook leak on module {name!r}: pre={pre_counts[name]} "
            f"post={post_counts[name]}"
        )

    # And evidence that the hooks fired during the call.
    assert isinstance(trace, LiveTrace)
    assert trace.hook_status.get("bottleneck") is True, (
        f"expected bottleneck hook to fire; status={trace.hook_status!r}"
    )
    assert any(
        trace.hook_status.get(f"head:{n}") for n in
        ("turn_type", "noetic", "domain")
    ), f"expected at least one head hook to fire; status={trace.hook_status!r}"


def test_hooks_cleaned_up_on_exception():
    """If the forward pass raises, hooks must still be removed."""
    model, batch, _ = _build_model_and_batch()
    head_module = model.head

    pre_counts = {
        "backbone": len(head_module.backbone._forward_hooks),
        "embedding": len(model.embedding._forward_hooks),
    }

    # Force an exception by passing a malformed batch (None).
    with pytest.raises((TypeError, AttributeError, ValueError, RuntimeError)):
        capture_live_trace(model, None, input_text="should-fail")

    post_counts = {
        "backbone": len(head_module.backbone._forward_hooks),
        "embedding": len(model.embedding._forward_hooks),
    }
    for name in pre_counts:
        assert post_counts[name] == pre_counts[name], (
            f"hook leaked on exception path for {name!r}: "
            f"pre={pre_counts[name]} post={post_counts[name]}"
        )


# ---------------------------------------------------------------------------
# 2. Live activations captured during prediction
# ---------------------------------------------------------------------------


def test_live_activations_captured_during_prediction():
    """``capture_live_trace`` returns non-empty per-layer activations on a
    real forward pass."""
    model, batch, _ = _build_model_and_batch()

    outputs, trace = capture_live_trace(
        model, batch, input_text="activations-test", top_k=3
    )

    # The bottleneck and at least the embedding output must be captured.
    layer_names = {la.name for la in trace.layer_activations}
    assert "bottleneck" in layer_names, layer_names
    assert "embedding_output" in layer_names, layer_names

    # Each captured layer must have non-zero magnitude on a real init.
    for la in trace.layer_activations:
        assert la.shape, f"layer {la.name} has empty shape"
        assert la.l2_norm > 0.0, f"layer {la.name} l2_norm == 0 (capture failed?)"
        assert la.flat_preview, f"layer {la.name} preview empty"

    # Bottleneck top-K must be populated and ordered by |activation|.
    assert trace.bottleneck_top_k, "bottleneck_top_k empty"
    abs_acts = [abs(v) for _, v in trace.bottleneck_top_k]
    assert abs_acts == sorted(abs_acts, reverse=True)

    # All 12 heads must be present with finite confidence.
    assert len(trace.heads) == 12, f"expected 12 heads, got {len(trace.heads)}"
    for h in trace.heads:
        assert 0.0 <= h.confidence <= 1.0
        assert h.raw_logits, f"head {h.name} logits empty"


# ---------------------------------------------------------------------------
# 3. Attribution returns top-K dims per head
# ---------------------------------------------------------------------------


def test_attribution_returns_top_k_per_head():
    model, batch, _ = _build_model_and_batch(bottleneck_dim=16)
    K = 3
    _, trace = capture_live_trace(
        model, batch, input_text="attribution-test", top_k=K
    )
    assert len(trace.heads) == 12
    for h in trace.heads:
        assert len(h.top_k_attribution) == K, (
            f"head {h.name!r} attribution length {len(h.top_k_attribution)} != {K}"
        )
        # Indices are valid bottleneck dims.
        for dim, _score in h.top_k_attribution:
            assert 0 <= dim < 16, (
                f"head {h.name!r} attribution dim {dim} out of range"
            )
        # Sorted by |score| descending.
        abs_scores = [abs(s) for _, s in h.top_k_attribution]
        assert abs_scores == sorted(abs_scores, reverse=True), (
            f"head {h.name!r} attribution not sorted: {h.top_k_attribution!r}"
        )


# ---------------------------------------------------------------------------
# 4. Predictor with_trace=False returns no trace
# ---------------------------------------------------------------------------


def test_no_trace_when_disabled():
    """``Predictor.__call__`` returns prediction-only when ``with_trace=False``."""
    from cas_native.inference.predict_cas import Predictor
    from cas_native.tokenizer.lexicon.schema import load_seed_lexicon

    model, _, vocab = _build_model_and_batch()
    predictor = Predictor(
        model=model,
        vocabulary=vocab,
        lexicon=load_seed_lexicon(),
        device=torch.device("cpu"),
        max_length=24,
    )

    # with_trace defaults to False
    result = predictor("test input without trace")
    assert isinstance(result, dict), (
        f"expected dict-only return, got {type(result).__name__}"
    )
    assert "turn_type" in result

    # with_trace=True returns a tuple
    result_traced = predictor("test input with trace", with_trace=True)
    assert isinstance(result_traced, tuple)
    assert len(result_traced) == 2
    pred, trace = result_traced
    assert isinstance(pred, dict)
    assert isinstance(trace, LiveTrace)


# ---------------------------------------------------------------------------
# 5. Trace serializable to JSON
# ---------------------------------------------------------------------------


def test_trace_serializable_to_json():
    model, batch, _ = _build_model_and_batch()
    _, trace = capture_live_trace(
        model, batch, input_text="json-serialization-test", top_k=3
    )

    payload = trace.to_dict()
    s = json.dumps(payload)
    assert len(s) > 200
    reloaded = json.loads(s)
    assert reloaded["schema_version"] == "live_trace.v1"
    assert reloaded["input_text"] == "json-serialization-test"
    assert isinstance(reloaded["heads"], list)
    assert len(reloaded["heads"]) == 12
    for h in reloaded["heads"]:
        assert "name" in h
        assert "argmax_index" in h
        assert "confidence" in h
        assert "top_k_attribution" in h


# ---------------------------------------------------------------------------
# 6. REPL /trace command outputs summary
# ---------------------------------------------------------------------------


def test_repl_trace_command_outputs_summary():
    """chat.py defines /trace and the rendering helpers; verify by source."""
    repo_root = Path(__file__).resolve().parents[3]
    chat_path = repo_root / "cas-native" / "inference" / "chat.py"
    assert chat_path.exists()
    source = chat_path.read_text(encoding="utf-8")
    # Command tokens defined.
    assert '"/trace"' in source, "chat.py missing /trace command token"
    # Helper functions present.
    assert "def _show_trace(" in source, "chat.py missing _show_trace helper"
    assert "def _do_trace_raw(" in source or "--raw" in source, (
        "chat.py missing /trace --raw handling"
    )
    # State tracking — the REPL must remember the most recent trace.
    assert "last_trace" in source, "chat.py missing last_trace state variable"
    # Belief commands MUST still be present (no regression).
    assert '"/beliefs"' in source
    assert '"/why"' in source
    assert '"/forget"' in source


def test_show_trace_renders_summary_plaintext():
    """``_show_trace(console=None, trace=...)`` writes a summary to stdout."""
    import io
    import sys

    from cas_native.inference import chat as chat_mod

    model, batch, _ = _build_model_and_batch()
    _, trace = capture_live_trace(
        model, batch, input_text="plaintext-trace-test", top_k=3
    )

    saved_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        chat_mod._show_trace(trace, console=None, raw=False)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = saved_stdout

    assert "TRACE" in output.upper()
    # Mentions at least a couple of the heads.
    head_names_seen = sum(
        1 for n in ("turn_type", "noetic", "domain", "drive") if n in output
    )
    assert head_names_seen >= 2, (
        f"expected per-head summary, got: {output!r}"
    )


# ---------------------------------------------------------------------------
# 7. Two consecutive predictions don't leak hooks
# ---------------------------------------------------------------------------


def test_two_consecutive_predictions_dont_leak_hooks():
    model, batch, _ = _build_model_and_batch()
    head_module = model.head

    pre = {
        "backbone": len(head_module.backbone._forward_hooks),
        "embedding": len(model.embedding._forward_hooks),
        "turn_type_head": len(head_module.turn_type_head._forward_hooks),
    }
    # Run capture five times to confirm no growing state.
    for i in range(5):
        _, trace = capture_live_trace(
            model, batch, input_text=f"call-{i}", top_k=3
        )
        assert isinstance(trace, LiveTrace)
        # After each call, the forward-hooks dict must be back to its
        # baseline length on every hooked module.
        assert (
            len(head_module.backbone._forward_hooks) == pre["backbone"]
        ), f"call {i}: backbone hooks={len(head_module.backbone._forward_hooks)}"
        assert (
            len(model.embedding._forward_hooks) == pre["embedding"]
        ), f"call {i}: embedding hooks={len(model.embedding._forward_hooks)}"
        assert (
            len(head_module.turn_type_head._forward_hooks)
            == pre["turn_type_head"]
        ), f"call {i}: turn_type_head hooks unbalanced"


# ---------------------------------------------------------------------------
# 8. Attribution correlates with argmax change on perturbed input
# ---------------------------------------------------------------------------


def test_attribution_correlates_with_argmax_change():
    """Perturbing the input should shift attribution scores.

    Two captures on different inputs against the same model: the per-head
    top-K attribution dims (or scores) must differ on at least one head.
    This is a weak test (different inputs -> different bottleneck z ->
    different grad×z) but it catches the case where attribution is being
    computed against a frozen / ignored gradient path.
    """
    model, batch_a, vocab = _build_model_and_batch()
    sequences_b = [tokenize("audit the principle structure")]
    batch_b = tokens_to_structured_token_batch(
        sequences_b, vocab, max_length=24
    )

    _, trace_a = capture_live_trace(
        model, batch_a, input_text="attribution-A", top_k=3
    )
    _, trace_b = capture_live_trace(
        model, batch_b, input_text="attribution-B", top_k=3
    )

    # At least one head's top-K dims OR scores must differ.
    differed_dims = False
    differed_scores = False
    for h_a, h_b in zip(trace_a.heads, trace_b.heads):
        dims_a = [d for d, _ in h_a.top_k_attribution]
        dims_b = [d for d, _ in h_b.top_k_attribution]
        scores_a = [round(s, 6) for _, s in h_a.top_k_attribution]
        scores_b = [round(s, 6) for _, s in h_b.top_k_attribution]
        if dims_a != dims_b:
            differed_dims = True
        if scores_a != scores_b:
            differed_scores = True

    assert differed_dims or differed_scores, (
        "attribution did not respond to input perturbation; "
        f"trace_a heads={[(h.name, h.top_k_attribution) for h in trace_a.heads]} "
        f"trace_b heads={[(h.name, h.top_k_attribution) for h in trace_b.heads]}"
    )


# ---------------------------------------------------------------------------
# Bonus tests beyond the 8 required
# ---------------------------------------------------------------------------


def test_trace_diagnostics_field_is_list():
    model, batch, _ = _build_model_and_batch()
    _, trace = capture_live_trace(
        model, batch, input_text="diagnostics-shape", top_k=3
    )
    assert isinstance(trace.diagnostics, list)


def test_trace_timing_populated():
    model, batch, _ = _build_model_and_batch()
    _, trace = capture_live_trace(
        model, batch, input_text="timing-test", top_k=3
    )
    assert "forward_ms" in trace.timing
    assert trace.timing["forward_ms"] >= 0.0
    assert "attribution_ms" in trace.timing
    assert trace.timing["attribution_ms"] >= 0.0


def test_attention_entropy_summary_populated():
    model, batch, _ = _build_model_and_batch()
    _, trace = capture_live_trace(
        model, batch, input_text="entropy-test", top_k=3
    )
    s = trace.attention_entropy_summary
    for key in ("mean", "min", "max", "entropy", "token_count"):
        assert key in s, f"missing key {key!r} in entropy summary"
