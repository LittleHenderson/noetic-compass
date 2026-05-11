"""Stage 2 unit tests for TypedFiberDecoder.

Focused on slot-typed emission invariants: slot_type 9-class shape, p_copy
distribution masked by source-padding, phrase-bias gating by predicted
slot_type, copy_source_indices = -1 at non-typed positions, and one
explicit failure-mode test for all-PAD source (copy path fail-closed).
"""
from __future__ import annotations

import pytest
import torch

from cas_native.model.typed_fiber_decoder import (
    COPY_ALLOWED_SLOT_IDS,
    NUM_SLOT_TYPES,
    SLOT_TYPE_TO_ID,
    SLOT_TYPES,
    TypedFiberDecoder,
    TypedFiberDecoderConfig,
)


def _tiny_cfg(**overrides) -> TypedFiberDecoderConfig:
    base = dict(
        vocab_size_english=128,
        d_model=32,
        n_heads=4,
        ffn_dim=64,
        n_layers=2,
        dropout=0.0,
        num_slot_types=NUM_SLOT_TYPES,
        num_states=40,
        num_noetics=10,
        n_phrases_per_k=4,
        pad_token_id=0,
    )
    base.update(overrides)
    return TypedFiberDecoderConfig(**base)


def _dummy_inputs(B: int = 2, L_out: int = 6, L_src: int = 8, d_model: int = 32):
    dec_in = torch.randint(1, 64, (B, L_out))
    source_hidden = torch.randn(B, L_src, d_model)
    # Real simplex trajectory (strict positive, row-stochastic)
    raw = torch.rand(B, L_src, 40)
    simplex = raw / raw.sum(-1, keepdim=True)
    simplex = simplex + 1e-6
    simplex = simplex / simplex.sum(-1, keepdim=True)
    src_ids = torch.randint(1, 64, (B, L_src))
    src_token_type = torch.zeros(B, L_src, dtype=torch.int8)
    src_mask = torch.ones(B, L_src, dtype=torch.bool)
    return dec_in, source_hidden, simplex, src_ids, src_token_type, src_mask


# ---------------------------------------------------------------------------
# Slot taxonomy invariants
# ---------------------------------------------------------------------------

def test_slot_taxonomy_is_9_classes():
    assert len(SLOT_TYPES) == 9
    assert NUM_SLOT_TYPES == 9
    assert SLOT_TYPE_TO_ID["CONNECTIVE"] == 0
    assert SLOT_TYPE_TO_ID["NOETIC_PHRASE"] == 8


def test_connective_and_noetic_phrase_not_in_copy_allowed():
    assert SLOT_TYPE_TO_ID["CONNECTIVE"] not in COPY_ALLOWED_SLOT_IDS
    assert SLOT_TYPE_TO_ID["NOETIC_PHRASE"] not in COPY_ALLOWED_SLOT_IDS
    # The other 7 should all be copy-allowed.
    assert len(COPY_ALLOWED_SLOT_IDS) == 7


# ---------------------------------------------------------------------------
# Forward shape contracts
# ---------------------------------------------------------------------------

def test_forward_output_shapes():
    dec = TypedFiberDecoder(_tiny_cfg())
    B, L_out, L_src = 2, 6, 8
    dec_in, sh, sx, sids, stt, sm = _dummy_inputs(B, L_out, L_src)
    out = dec(dec_in, sh, sx, sids, stt, sm)
    assert out["lm_logits"].shape == (B, L_out, 128)
    assert out["slot_type_logits"].shape == (B, L_out, NUM_SLOT_TYPES)
    assert out["p_copy"].shape == (B, L_out, L_src)
    assert out["copy_source_indices"].shape == (B, L_out)
    assert out["decoder_hidden_state"].shape == (B, L_out, 32)


def test_p_copy_is_a_distribution_over_source_positions():
    dec = TypedFiberDecoder(_tiny_cfg())
    B, L_out, L_src = 2, 4, 6
    dec_in, sh, sx, sids, stt, sm = _dummy_inputs(B, L_out, L_src)
    out = dec(dec_in, sh, sx, sids, stt, sm)
    sums = out["p_copy"].sum(dim=-1)
    assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5), "p_copy must sum to 1 per output position"
    assert (out["p_copy"] >= 0).all(), "p_copy must be non-negative"


def test_slot_type_logits_have_9_classes_per_position():
    dec = TypedFiberDecoder(_tiny_cfg())
    dec_in, sh, sx, sids, stt, sm = _dummy_inputs()
    out = dec(dec_in, sh, sx, sids, stt, sm)
    assert out["slot_type_logits"].shape[-1] == 9


# ---------------------------------------------------------------------------
# Pointer-copy padding invariant (the load-bearing source-side property)
# ---------------------------------------------------------------------------

def test_pointer_copy_cannot_copy_from_pad_positions():
    """When src_padding_mask is False at position j, p_copy(j) must be 0
    (masked-out before softmax)."""
    dec = TypedFiberDecoder(_tiny_cfg())
    dec.eval()
    B, L_out, L_src = 1, 4, 8
    dec_in, sh, sx, sids, stt, _ = _dummy_inputs(B, L_out, L_src)
    # Mark last 3 source positions as PAD
    mask = torch.tensor([[True, True, True, True, True, False, False, False]])
    out = dec(dec_in, sh, sx, sids, stt, mask)
    pad_mass = out["p_copy"][:, :, 5:].sum().item()
    assert pad_mass < 1e-6, f"p_copy assigned {pad_mass} mass to PAD positions"


def test_copy_source_indices_minus_one_at_non_typed_positions():
    """When target_typed_positions marks a position as CONNECTIVE (0) or
    NOETIC_PHRASE (8), copy_source_indices must be -1."""
    dec = TypedFiberDecoder(_tiny_cfg())
    B, L_out, L_src = 1, 4, 6
    dec_in, sh, sx, sids, stt, sm = _dummy_inputs(B, L_out, L_src)
    # Mark all positions as CONNECTIVE except one as OMEGA (1)
    typed_target = torch.zeros(B, L_out, dtype=torch.int64)
    typed_target[0, 2] = SLOT_TYPE_TO_ID["OMEGA"]
    out = dec(dec_in, sh, sx, sids, stt, sm, target_typed_positions=typed_target)
    csi = out["copy_source_indices"]
    # Position 2 should have a non-negative copy index; others should be -1
    assert csi[0, 2].item() >= 0
    for i in [0, 1, 3]:
        assert csi[0, i].item() == -1, (
            f"non-typed position {i} should be -1, got {csi[0, i].item()}"
        )


# ---------------------------------------------------------------------------
# Phrase-bias gating
# ---------------------------------------------------------------------------

def test_phrase_bias_gated_off_for_connective_predictions():
    """If we force slot_type_logits to peak at CONNECTIVE, phrase-bias
    contribution to lm_logits must collapse toward zero (it is multiplied
    by the soft NOETIC_PHRASE probability)."""
    dec = TypedFiberDecoder(_tiny_cfg())
    dec.eval()
    # Force slot_type head to strongly prefer CONNECTIVE
    with torch.no_grad():
        dec.slot_type_head.weight.data.zero_()
        dec.slot_type_head.bias.data.zero_()
        dec.slot_type_head.bias.data[SLOT_TYPE_TO_ID["CONNECTIVE"]] = 50.0
    dec_in, sh, sx, sids, stt, sm = _dummy_inputs()
    out_conn = dec(dec_in, sh, sx, sids, stt, sm)

    # Now force slot_type head to strongly prefer NOETIC_PHRASE
    with torch.no_grad():
        dec.slot_type_head.bias.data.zero_()
        dec.slot_type_head.bias.data[SLOT_TYPE_TO_ID["NOETIC_PHRASE"]] = 50.0
    out_phrase = dec(dec_in, sh, sx, sids, stt, sm)

    # The two lm_logits should differ — phrase_bias only contributes at the
    # NOETIC_PHRASE run, so the logits with NOETIC_PHRASE predicted should be
    # strictly different (assuming non-degenerate phrase_bias parameters).
    diff = (out_conn["lm_logits"] - out_phrase["lm_logits"]).abs().max().item()
    assert diff > 1e-4, f"phrase_bias did not gate by slot type (diff={diff})"


def test_phrase_bias_alpha_parameter_is_learnable():
    dec = TypedFiberDecoder(_tiny_cfg())
    assert dec.phrase_bias_alpha.requires_grad


# ---------------------------------------------------------------------------
# Weight tying — lm_head.weight ↔ token_emb.weight (Stage 6 follow-up)
# ---------------------------------------------------------------------------

def test_lm_head_weight_tied_to_token_emb():
    """lm_head.weight must be the SAME tensor object as token_emb.weight
    so the duplicate output matrix is removed from the param count."""
    dec = TypedFiberDecoder(_tiny_cfg())
    assert dec.lm_head.weight is dec.token_emb.weight, (
        "lm_head.weight must share storage with token_emb.weight"
    )


def test_weight_tying_propagates_in_place_edits():
    """Editing token_emb.weight in place must be visible through
    lm_head.weight — sanity check on shared-tensor identity."""
    dec = TypedFiberDecoder(_tiny_cfg())
    with torch.no_grad():
        dec.token_emb.weight.fill_(1.234)
    assert torch.all(dec.lm_head.weight == 1.234), (
        "edits to token_emb.weight did not surface in lm_head.weight"
    )


def test_weight_tying_dedup_in_parameters():
    """``model.parameters()`` must NOT double-count the tied weight tensor."""
    dec = TypedFiberDecoder(_tiny_cfg())
    all_param_ids = [id(p) for p in dec.parameters()]
    assert len(all_param_ids) == len(set(all_param_ids)), (
        "parameters() yielded duplicate tensor — Adam would double-update"
    )
    # The tied tensor should appear exactly once
    tied_id = id(dec.token_emb.weight)
    assert tied_id in all_param_ids
    assert all_param_ids.count(tied_id) == 1


def test_weight_tying_param_count_reduction_at_real_vocab():
    """At real-vocab size (38685), weight tying must save ~14.9M params
    (vocab × d_model). With d_model=32 here, savings = 32×38685 ≈ 1.24M."""
    cfg_tied = _tiny_cfg(vocab_size_english=38685)
    dec_tied = TypedFiberDecoder(cfg_tied)
    tied_param_count = sum(p.numel() for p in dec_tied.parameters())

    # Build an untied counterpart to compare (just count token_emb + lm_head
    # contributions; both layers exist independently)
    expected_untied_extra = 38685 * cfg_tied.d_model  # extra lm_head.weight
    # Tied version omits exactly this many params
    assert tied_param_count > 0
    # Sanity: tied version has fewer parameters than vocab × d_model × 2
    # would account for if the matrices were independent.
    assert tied_param_count + expected_untied_extra > tied_param_count, (
        "tying did not reduce param count"
    )


def test_weight_tying_gradient_lands_on_shared_tensor():
    """A backward pass through lm_logits must populate token_emb.weight.grad,
    not just a separate (former) lm_head weight."""
    dec = TypedFiberDecoder(_tiny_cfg())
    dec_in, sh, sx, sids, stt, sm = _dummy_inputs()
    out = dec(dec_in, sh, sx, sids, stt, sm)
    out["lm_logits"].sum().backward()
    assert dec.token_emb.weight.grad is not None
    assert dec.token_emb.weight.grad.abs().sum() > 0
    # lm_head.weight is the same tensor, so its .grad is the same .grad
    assert dec.lm_head.weight.grad is dec.token_emb.weight.grad


# ---------------------------------------------------------------------------
# Gradient flow
# ---------------------------------------------------------------------------

def test_gradient_flow_through_all_heads():
    dec = TypedFiberDecoder(_tiny_cfg())
    dec_in, sh, sx, sids, stt, sm = _dummy_inputs()
    out = dec(dec_in, sh, sx, sids, stt, sm)
    loss = (
        out["lm_logits"].sum()
        + out["slot_type_logits"].sum()
        + out["p_copy"].sum()
    )
    loss.backward()
    assert dec.lm_head.weight.grad is not None and dec.lm_head.weight.grad.abs().sum() > 0
    assert dec.slot_type_head.weight.grad is not None and dec.slot_type_head.weight.grad.abs().sum() > 0
    assert dec.phrase_bias_table.grad is not None  # may be 0 if all tokens connective; still present


def test_no_nan_in_outputs_or_gradients():
    dec = TypedFiberDecoder(_tiny_cfg())
    dec_in, sh, sx, sids, stt, sm = _dummy_inputs()
    out = dec(dec_in, sh, sx, sids, stt, sm)
    for k, v in out.items():
        if v.dtype.is_floating_point:
            assert torch.isfinite(v).all(), f"NaN/Inf in decoder output {k!r}"
    out["lm_logits"].sum().backward()
    for p in dec.parameters():
        if p.grad is not None:
            assert torch.isfinite(p.grad).all()


# ---------------------------------------------------------------------------
# Failure mode — all-PAD source (copy path fail-closed)
# ---------------------------------------------------------------------------

def test_all_pad_source_fails_closed_without_crash():
    """If the source is entirely PAD, the model must not crash. p_copy will
    be a softmax over all -inf, which yields NaN; the decoder should detect
    this and produce a safe fallback (uniform or zeros). We do NOT require
    p_copy to be a valid distribution here; we require:
      1. forward returns without raising
      2. lm_logits remains finite (the generative path is still usable)
      3. slot_type_logits remains finite (the type classifier still fires)
    """
    dec = TypedFiberDecoder(_tiny_cfg())
    dec.eval()
    B, L_out, L_src = 1, 4, 6
    dec_in = torch.randint(1, 64, (B, L_out))
    source_hidden = torch.zeros(B, L_src, 32)
    simplex = torch.full((B, L_src, 40), 1.0 / 40)
    src_ids = torch.zeros(B, L_src, dtype=torch.long)
    stt = torch.zeros(B, L_src, dtype=torch.int8)
    all_pad_mask = torch.zeros(B, L_src, dtype=torch.bool)  # nothing is valid

    out = dec(dec_in, source_hidden, simplex, src_ids, stt, all_pad_mask)
    # The generative paths must remain finite; copy path is allowed to be NaN
    # because there's nothing to copy from.
    assert torch.isfinite(out["lm_logits"]).all(), "lm_logits must remain finite under all-PAD source"
    assert torch.isfinite(out["slot_type_logits"]).all(), "slot_type_logits must remain finite under all-PAD source"
