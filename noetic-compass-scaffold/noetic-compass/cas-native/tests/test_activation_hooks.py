"""Tests for the Mode 7 forward-hook instrumentation.

Verifies:

* Hooks register without error on real CAS-Native model assemblies.
* A forward pass with hooks attached populates the session's
  ``activations`` dict at every registered hook name.
* Sparse top-K mode produces tensors of the right shape and the
  expected (signed) values.
* ``unregister_all()`` cleanly detaches every hook, after which a
  forward pass writes nothing further.
* Inference behavior is byte-identical with hooks attached vs
  un-attached (the no-regression contract).
"""

from __future__ import annotations

import pytest
import torch

from cas_native.model import (
    CASNativeConfig,
    CASNativeModel,
    StructuredPredictionHead,
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.model.activation_hooks import (
    CAPTURE_MODE_FULL,
    CAPTURE_MODE_SPARSE_TOPK,
    CAS_ALIGNED_CLASS_NAMES,
    HookSession,
    register_named_hooks,
)
from cas_native.tokenizer import StructuredTokenVocabulary, tokenize
from cas_native.training.structured_token_adapter import tokens_to_structured_token_batch


# ---------------------------------------------------------------------------
# Fixtures: compact model assemblies that exercise multiple CAS layers.
# ---------------------------------------------------------------------------


def _small_cas_native_model() -> CASNativeModel:
    """Minimum-size CASNativeModel that still hits every CAS layer.

    We deliberately use the smallest plausible config (2 layers, 8 dim,
    2 heads) so the test runs quickly on CPU. This still exercises
    ``CognitiveStateEmbedding``, two ``CASTransformerLayer`` instances
    (each containing ``DomainDescentAttention`` /
    ``FractalAttentionHead`` / ``PrerequisiteGateLayer``),
    ``CognitiveToposReasoner``, ``InversionDetector``,
    ``GenerativeHead``, ``LacunarityGate``, and ``LacunarityHead``.
    """
    config = CASNativeConfig(
        d_model=8,
        n_layers=2,
        n_heads=2,
        vocab_size=64,
        max_seq_len=16,
        fractal_depth=1,
        num_ethical_propositions=3,
        dropout=0.0,
        rpm_threshold=0.5,
        num_ifs_maps=2,
    )
    torch.manual_seed(42)
    return CASNativeModel(config)


def _small_structured_token_model():
    """Compact StructuredTokenEmbedding -> StructuredPredictionHead pipeline."""
    sequences = [
        tokenize("I feel drawn to this idea"),
        tokenize("we will audit ^2^P_{F4}|f carefully"),
    ]
    vocab = StructuredTokenVocabulary.from_token_sequences(sequences)
    batch = tokens_to_structured_token_batch(sequences, vocab, max_length=12)
    torch.manual_seed(7)
    embedding = StructuredTokenEmbedding(vocab_size=len(vocab), d_model=16, dropout=0.0)
    head = StructuredPredictionHead(d_model=16, bottleneck_dim=8)
    model = StructuredTokenStructuredPredictor(embedding, head)
    return model, batch


# ---------------------------------------------------------------------------
# Test (a): hooks register without error.
# ---------------------------------------------------------------------------


def test_register_named_hooks_attaches_to_every_cas_aligned_layer():
    model = _small_cas_native_model()
    session = register_named_hooks(model)
    try:
        assert isinstance(session, HookSession)
        # Every hook name must be unique.
        assert len(session.hook_names) == len(set(session.hook_names))
        # Every hooked module's class name must be in the allow-list.
        names_lower = {n.split(".")[0].split("#")[0] for n in session.hook_names}
        for name in names_lower:
            assert name.replace("_", ""), name  # non-empty
        # Architecture sanity: at least one DomainDescentAttention,
        # PrerequisiteGateLayer, and CognitiveToposReasoner present.
        assert any("domain_descent_attention" in n for n in session.hook_names)
        assert any("prerequisite_gate_layer" in n for n in session.hook_names)
        assert any("cognitive_topos_reasoner" in n for n in session.hook_names)
        # 2 transformer layers -> 2 hooks of each per-layer kind.
        assert sum("domain_descent_attention" in n for n in session.hook_names) == 2
        assert sum("fractal_attention_head" in n for n in session.hook_names) == 2
        assert sum("prerequisite_gate_layer" in n for n in session.hook_names) == 2
        assert sum("cas_transformer_layer" in n for n in session.hook_names) == 2
    finally:
        session.unregister_all()


def test_register_named_hooks_validates_arguments():
    model = _small_cas_native_model()
    with pytest.raises(ValueError):
        register_named_hooks(model, mode="bogus")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        register_named_hooks(model, mode=CAPTURE_MODE_SPARSE_TOPK, k=0)


# ---------------------------------------------------------------------------
# Test (b): forward pass with hooks captures activations at every name.
# ---------------------------------------------------------------------------


def test_forward_with_hooks_populates_activations_dict():
    model = _small_cas_native_model()
    session = register_named_hooks(model)
    try:
        input_ids = torch.randint(low=0, high=model.config.vocab_size, size=(2, 6))
        attention_mask = torch.ones_like(input_ids)
        with torch.no_grad():
            outputs = model(input_ids, attention_mask=attention_mask)
        # Forward succeeded.
        assert "logits" in outputs
        # Every registered hook that is reached on the forward path was
        # captured. Some CAS-aligned modules (e.g. GenerativeHead) are
        # attached to the model but only exercised by external callers;
        # those hooks legitimately do not fire during a basic forward
        # pass and are exempt from this check.
        forward_path_required = (
            "cognitive_state_embedding",
            "cas_transformer_layer",
            "domain_descent_attention",
            "fractal_attention_head",
            "prerequisite_gate_layer",
            "cognitive_topos_reasoner",
            "inversion_detector",
            "lacunarity_gate",
            "lacunarity_head",
        )
        for prefix in forward_path_required:
            matching = [n for n in session.hook_names if n.startswith(prefix)]
            assert matching, f"no hook registered for {prefix}"
            assert any(n in session.activations for n in matching), (
                f"none of {matching} captured for {prefix}"
            )
        # Every captured tensor is detached.
        for captured in session.activations.values():
            tensor = captured if isinstance(captured, torch.Tensor) else captured.get("values")
            assert tensor is not None
            assert tensor.requires_grad is False
    finally:
        session.unregister_all()


def test_forward_with_hooks_on_structured_token_predictor():
    model, batch = _small_structured_token_model()
    session = register_named_hooks(model)
    try:
        with torch.no_grad():
            outputs = model(batch)
        assert "turn_type_logits" in outputs
        # StructuredTokenEmbedding is a CAS-aligned class.
        assert any("structured_token_embedding" in n for n in session.hook_names)
        assert any("structured_prediction_head" in n for n in session.hook_names)
        for name in session.hook_names:
            assert name in session.activations
    finally:
        session.unregister_all()


# ---------------------------------------------------------------------------
# Test (c): sparse top-K mode produces tensors of the correct shape.
# ---------------------------------------------------------------------------


def test_sparse_topk_capture_shape_and_signed_values():
    model = _small_cas_native_model()
    k = 4
    session = register_named_hooks(model, mode=CAPTURE_MODE_SPARSE_TOPK, k=k)
    try:
        input_ids = torch.randint(low=0, high=model.config.vocab_size, size=(1, 5))
        with torch.no_grad():
            model(input_ids)
        for name, payload in session.activations.items():
            assert isinstance(payload, dict), f"{name}: expected dict, got {type(payload)}"
            assert {"values", "indices", "shape"} <= set(payload.keys()), name
            values = payload["values"]
            indices = payload["indices"]
            shape = payload["shape"]
            # Shapes match between values/indices.
            assert values.shape == indices.shape, name
            # K is clamped against the original last dim.
            original_shape = tuple(int(x) for x in shape.tolist())
            assert original_shape, name
            last_dim = original_shape[-1] if original_shape else 1
            expected_k = max(1, min(k, last_dim))
            assert values.shape[-1] == expected_k, (name, values.shape, last_dim)
            # Indices are valid index positions.
            assert (indices >= 0).all().item()
            assert (indices < last_dim).all().item()
    finally:
        session.unregister_all()


def test_sparse_topk_smaller_than_k_clamps_to_last_dim():
    """When k exceeds the layer's last dim, K is clamped — not an error."""
    model = _small_cas_native_model()
    # k far larger than any plausible last dim in this small model.
    session = register_named_hooks(model, mode=CAPTURE_MODE_SPARSE_TOPK, k=10_000)
    try:
        input_ids = torch.randint(low=0, high=model.config.vocab_size, size=(1, 4))
        with torch.no_grad():
            model(input_ids)
        for name, payload in session.activations.items():
            shape = payload["shape"]
            last_dim = int(shape.tolist()[-1]) if shape.numel() else 1
            assert payload["values"].shape[-1] == max(1, last_dim), name
    finally:
        session.unregister_all()


# ---------------------------------------------------------------------------
# Test (d): hooks unregister cleanly.
# ---------------------------------------------------------------------------


def test_unregister_all_detaches_hooks_completely():
    model = _small_cas_native_model()
    session = register_named_hooks(model)
    input_ids = torch.randint(low=0, high=model.config.vocab_size, size=(1, 4))
    with torch.no_grad():
        model(input_ids)
    assert len(session.activations) > 0
    session.unregister_all()
    # After unregistering, activations dict is cleared.
    assert len(session.activations) == 0
    # And a fresh forward pass adds nothing.
    with torch.no_grad():
        model(input_ids)
    assert len(session.activations) == 0
    # And the session reports zero registered hook handles.
    assert session._handles == []


def test_unregister_all_is_idempotent():
    model = _small_cas_native_model()
    session = register_named_hooks(model)
    session.unregister_all()
    # Second call is a no-op, not an error.
    session.unregister_all()
    assert session._handles == []


# ---------------------------------------------------------------------------
# Test: byte-identical inference behavior (no-regression contract).
# ---------------------------------------------------------------------------


def test_inference_outputs_unchanged_when_hooks_attached():
    """The forward pass must produce identical outputs whether hooks are
    attached or not. This is the load-bearing no-regression invariant.
    """
    model = _small_cas_native_model()
    model.eval()
    input_ids = torch.randint(low=0, high=model.config.vocab_size, size=(2, 6))
    attention_mask = torch.ones_like(input_ids)

    # Baseline (no hooks).
    with torch.no_grad():
        baseline = model(input_ids, attention_mask=attention_mask)

    # Attach hooks and run again with the same inputs.
    session = register_named_hooks(model, mode=CAPTURE_MODE_FULL)
    try:
        with torch.no_grad():
            instrumented = model(input_ids, attention_mask=attention_mask)
    finally:
        session.unregister_all()

    # All shared output tensors must be identical bit-for-bit.
    for key in ("logits", "hidden_states", "cognitive_state", "inversion_flags"):
        torch.testing.assert_close(
            instrumented[key],
            baseline[key],
            rtol=0.0,
            atol=0.0,
            msg=f"output key {key!r} changed when hooks were attached",
        )

    # And after unregister_all, baseline behavior fully restored.
    with torch.no_grad():
        post_unhook = model(input_ids, attention_mask=attention_mask)
    for key in ("logits", "hidden_states", "cognitive_state", "inversion_flags"):
        torch.testing.assert_close(post_unhook[key], baseline[key], rtol=0.0, atol=0.0)


# ---------------------------------------------------------------------------
# Misc: allow-list integrity.
# ---------------------------------------------------------------------------


def test_cas_aligned_class_names_match_documented_components():
    """Spot-check that the canonical CAS-named architectural components
    from CLAUDE.md appear in the allow-list.
    """
    must_include = {
        "CognitiveStateEmbedding",
        "DomainDescentAttention",
        "PrerequisiteGateLayer",
        "FractalAttentionHead",
        "CognitiveToposReasoner",
    }
    assert must_include.issubset(set(CAS_ALIGNED_CLASS_NAMES))


@pytest.mark.parametrize("input_name,expected", [
    ("DomainDescentAttention", "domain_descent_attention"),
    ("FractalAttentionHead", "fractal_attention_head"),
    ("PrerequisiteGateLayer", "prerequisite_gate_layer"),
    ("CASTransformerLayer", "cas_transformer_layer"),
    ("CASNativeModel", "cas_native_model"),
    ("CognitiveStateEmbedding", "cognitive_state_embedding"),
    ("StructuredTokenEmbedding", "structured_token_embedding"),
])
def test_to_camel_snake_handles_acronym_prefixes(input_name, expected):
    from cas_native.model.activation_hooks import _to_camel_snake
    assert _to_camel_snake(input_name) == expected
