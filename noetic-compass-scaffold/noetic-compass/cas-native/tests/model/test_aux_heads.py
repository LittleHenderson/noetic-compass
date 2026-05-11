"""v1e Phase C unit tests for cas_native.model.aux_heads.

Coverage:
  - All 4 head shapes (output dims match design doc §2)
  - Weight init (xavier on Linear, zero bias)
  - AuxHeads forward returns the right dict keys + tensor shapes
  - build_aux_heads factory
  - Integration: CASNativeModel.attach_aux_heads + forward_with_aux
    smoke runs end-to-end on a tiny model + dummy batch
  - Default OFF guarantee: forward / forward_with_lm unchanged when
    aux_heads not attached (existing tests already cover this; we
    add an explicit attribute check)
"""
from __future__ import annotations

import pytest
import torch

from cas_native.model.aux_heads import (
    AuxHeads,
    AuxHeadsConfig,
    CardinalityHead,
    ClusterMembershipHead,
    DEFAULT_C_MAX,
    DEFAULT_K_MAX,
    NUM_NOETICS,
    PerPositionNoeticHead,
    StopCompleteHead,
    build_aux_heads,
)


# ---------------------------------------------------------------------------
# Per-head shape tests
# ---------------------------------------------------------------------------

def test_cardinality_head_shape():
    """H_card outputs (B, K_max + 1) logits."""
    cfg = AuxHeadsConfig(d_model=128, k_max=16)
    head = CardinalityHead(cfg)
    pooled = torch.randn(4, 128)
    out = head(pooled)
    assert out.shape == (4, 17)


def test_per_position_head_shape():
    """H_pos outputs (B, K_max, num_noetics) logits."""
    cfg = AuxHeadsConfig(d_model=128, k_max=8)
    head = PerPositionNoeticHead(cfg)
    pooled = torch.randn(3, 128)
    out = head(pooled)
    assert out.shape == (3, 8, NUM_NOETICS)


def test_stop_complete_head_shape():
    """H_stop outputs (B, L_dec, 2) logits per decoder position."""
    cfg = AuxHeadsConfig(d_model=128, stop_hidden=32)
    head = StopCompleteHead(cfg)
    decoder_hidden = torch.randn(2, 15, 128)
    out = head(decoder_hidden)
    assert out.shape == (2, 15, 2)


def test_cluster_membership_head_shape():
    """H_cluster outputs (B, C_max, num_noetics) logits."""
    cfg = AuxHeadsConfig(d_model=128, c_max=6)
    head = ClusterMembershipHead(cfg)
    pooled = torch.randn(5, 128)
    out = head(pooled)
    assert out.shape == (5, 6, NUM_NOETICS)


# ---------------------------------------------------------------------------
# Weight init
# ---------------------------------------------------------------------------

def test_aux_heads_xavier_init_linear_weights():
    """All Linear layers in AuxHeads receive Xavier init (non-zero
    weights, zero bias)."""
    aux = build_aux_heads(AuxHeadsConfig(d_model=64))
    linear_count = 0
    for module in aux.modules():
        if isinstance(module, torch.nn.Linear):
            linear_count += 1
            # Xavier init produces non-zero weights.
            assert not torch.allclose(module.weight, torch.zeros_like(module.weight))
            # Bias should be zero (matches model._init_weights style).
            if module.bias is not None:
                assert torch.allclose(module.bias, torch.zeros_like(module.bias))
    # 4 heads, several Linear each, expect >= 6 total.
    assert linear_count >= 6


# ---------------------------------------------------------------------------
# AuxHeads container forward
# ---------------------------------------------------------------------------

def test_aux_heads_forward_returns_all_4_outputs():
    """AuxHeads.forward returns a dict with all 4 logit keys when both
    pooled and decoder_hidden are provided."""
    cfg = AuxHeadsConfig(d_model=64, k_max=8, c_max=4)
    aux = AuxHeads(cfg)
    pooled = torch.randn(2, 64)
    decoder_hidden = torch.randn(2, 10, 64)
    out = aux(pooled=pooled, decoder_hidden=decoder_hidden)
    assert set(out.keys()) == {"card_logits", "pos_logits", "stop_logits", "cluster_logits"}
    assert out["card_logits"].shape == (2, 9)  # k_max + 1 = 9
    assert out["pos_logits"].shape == (2, 8, NUM_NOETICS)
    assert out["stop_logits"].shape == (2, 10, 2)
    assert out["cluster_logits"].shape == (2, 4, NUM_NOETICS)


def test_aux_heads_forward_decoder_optional():
    """When decoder_hidden is None, stop_logits is None but other heads
    still produce outputs."""
    cfg = AuxHeadsConfig(d_model=64)
    aux = AuxHeads(cfg)
    pooled = torch.randn(2, 64)
    out = aux(pooled=pooled, decoder_hidden=None)
    assert out["card_logits"] is not None
    assert out["pos_logits"] is not None
    assert out["cluster_logits"] is not None
    assert out["stop_logits"] is None


def test_aux_heads_forward_raises_without_pooled():
    """pooled is the required kwarg — missing it raises ValueError."""
    aux = AuxHeads(AuxHeadsConfig(d_model=32))
    with pytest.raises(ValueError, match="pooled"):
        aux()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def test_build_aux_heads_default_config():
    """Factory with no config uses the default d_model=512 / K_max=16 /
    C_max=6 matching v1c VALIDTOK 5ep checkpoint dims."""
    aux = build_aux_heads()
    assert aux.config.d_model == 512
    assert aux.config.k_max == DEFAULT_K_MAX
    assert aux.config.c_max == DEFAULT_C_MAX
    pooled = torch.randn(1, 512)
    out = aux.cardinality(pooled)
    assert out.shape == (1, DEFAULT_K_MAX + 1)


def test_build_aux_heads_custom_config():
    """Factory propagates a custom config."""
    cfg = AuxHeadsConfig(d_model=256, k_max=10, c_max=4)
    aux = build_aux_heads(cfg)
    assert aux.config is cfg
    assert aux.config.k_max == 10


# ---------------------------------------------------------------------------
# Integration: CASNativeModel.attach_aux_heads + forward_with_aux
# ---------------------------------------------------------------------------

def _build_tiny_model():
    """Construct a minimal CASNativeModel + NLGenerationHead + AuxHeads
    for end-to-end forward smoke tests. Dimensions kept small for speed."""
    from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
    from cas_native.model.nl_generation_head import (
        NLGenerationHead, NLGenerationHeadConfig,
    )

    vocab_size = 100
    d_model = 64
    cfg = CASNativeConfig(
        d_model=d_model, n_layers=2, n_heads=4, vocab_size=vocab_size,
    )
    model = CASNativeModel(cfg)
    head_cfg = NLGenerationHeadConfig(
        vocab_size=vocab_size, d_model=d_model, n_heads=4, n_layers=2,
    )
    head = NLGenerationHead(head_cfg)
    model.attach_nl_gen_head(head)

    aux_cfg = AuxHeadsConfig(d_model=d_model, k_max=4, c_max=3)
    aux = AuxHeads(aux_cfg)
    model.attach_aux_heads(aux)
    return model, vocab_size, d_model


def test_attach_aux_heads_smoke():
    """attach_aux_heads stores the module as an attribute that the
    forward_with_aux path can access."""
    model, _, _ = _build_tiny_model()
    assert model.aux_heads is not None
    assert isinstance(model.aux_heads, AuxHeads)


def test_forward_with_aux_returns_superset_of_forward_with_lm():
    """forward_with_aux returns all keys forward_with_lm produces plus
    the four aux logit tensors with the right shapes."""
    model, vocab_size, d_model = _build_tiny_model()
    batch_size = 2
    enc_seq_len = 8
    dec_seq_len = 6
    input_ids = torch.randint(1, vocab_size, (batch_size, enc_seq_len))
    decoder_input_ids = torch.randint(1, vocab_size, (batch_size, dec_seq_len))
    attention_mask = torch.ones(batch_size, enc_seq_len, dtype=torch.bool)
    register_id = torch.zeros(batch_size, dtype=torch.long)

    out = model.forward_with_aux(
        input_ids,
        decoder_input_ids,
        attention_mask=attention_mask,
        register_id=register_id,
    )
    # forward_with_lm keys must still be present.
    assert "lm_logits" in out
    assert "pooled_hidden_state" in out
    assert "hidden_states" in out
    # Aux logit keys must be present with right shapes.
    assert out["card_logits"].shape == (batch_size, 4 + 1)
    assert out["pos_logits"].shape == (batch_size, 4, NUM_NOETICS)
    # Stop logits shape matches decoder_input_ids seq len.
    assert out["stop_logits"].shape == (batch_size, dec_seq_len, 2)
    assert out["cluster_logits"].shape == (batch_size, 3, NUM_NOETICS)


def test_forward_with_aux_raises_without_aux_heads():
    """forward_with_aux raises RuntimeError when no aux heads are
    attached, mirroring forward_with_lm's behavior when no nl_gen_head
    is attached."""
    from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
    from cas_native.model.nl_generation_head import (
        NLGenerationHead, NLGenerationHeadConfig,
    )
    vocab_size = 50
    d_model = 32
    cfg = CASNativeConfig(d_model=d_model, n_layers=1, n_heads=2, vocab_size=vocab_size)
    model = CASNativeModel(cfg)
    head_cfg = NLGenerationHeadConfig(
        vocab_size=vocab_size, d_model=d_model, n_heads=2, n_layers=1,
    )
    model.attach_nl_gen_head(NLGenerationHead(head_cfg))
    # NOT calling attach_aux_heads.
    with pytest.raises(RuntimeError, match="aux_heads"):
        model.forward_with_aux(
            torch.randint(1, vocab_size, (1, 4)),
            torch.randint(1, vocab_size, (1, 3)),
        )


def test_forward_with_aux_gradients_flow_to_aux_heads():
    """A loss computed from any aux logit should backprop into the
    aux head's parameters. Smoke check that the aux head IS in the
    autograd graph."""
    model, vocab_size, _ = _build_tiny_model()
    out = model.forward_with_aux(
        torch.randint(1, vocab_size, (2, 6)),
        torch.randint(1, vocab_size, (2, 4)),
    )
    loss = out["card_logits"].sum()
    loss.backward()
    # Cardinality head's fc2.weight should have a non-zero grad.
    grad = model.aux_heads.cardinality.fc2.weight.grad
    assert grad is not None
    assert not torch.allclose(grad, torch.zeros_like(grad))


def test_default_aux_heads_attribute_is_none():
    """Models constructed without attach_aux_heads have aux_heads=None."""
    from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
    cfg = CASNativeConfig(d_model=32, n_layers=1, n_heads=2, vocab_size=50)
    model = CASNativeModel(cfg)
    assert model.aux_heads is None


# ---------------------------------------------------------------------------
# Param count sanity (rough — matches design doc §2.5 budget)
# ---------------------------------------------------------------------------

def test_aux_heads_param_count_under_budget():
    """At the v1c VALIDTOK dims (d_model=512, K_max=16, C_max=6), the
    total aux-head param count should be under 250k. Design budget
    is ~213k."""
    aux = build_aux_heads(AuxHeadsConfig(d_model=512, k_max=16, c_max=6))
    total = sum(p.numel() for p in aux.parameters())
    assert 100_000 < total < 250_000, f"unexpected aux param count: {total}"
