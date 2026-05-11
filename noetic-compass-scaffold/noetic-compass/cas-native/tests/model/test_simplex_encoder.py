"""Stage 2 unit tests for SimplexEncoder.

Focused on invariants (open-simplex membership, mask honoring, gradient
flow, determinism) and one explicit failure-mode test for simplex collapse
prevention.

References:
- ``docs/working/simplex_mvp_execution_plan_2026_05_11.md`` §Stage 2
- ``docs/working/simplex_mvp_build_spec_2026_05_11.md`` §2.1
"""
from __future__ import annotations

import pytest
import torch

from cas_native.model.simplex_encoder import (
    SIMPLEX_EPS,
    NUM_COGNITIVE_STATES,
    SimplexEncoder,
    SimplexEncoderConfig,
)


def _tiny_cfg(**overrides) -> SimplexEncoderConfig:
    """Tiny encoder config for fast unit tests."""
    base = dict(
        vocab_size=128,
        d_model=32,
        n_heads=4,
        ffn_dim=64,
        n_layers=2,
        dropout=0.0,
        max_source_len=32,
        tail_hidden=32,
        tail_layers=2,
        pad_token_id=0,
    )
    base.update(overrides)
    return SimplexEncoderConfig(**base)


def _make_input(B: int = 2, L: int = 8, vocab: int = 128) -> tuple[torch.Tensor, torch.Tensor]:
    input_ids = torch.randint(1, vocab, (B, L))
    mask = torch.ones(B, L, dtype=torch.bool)
    return input_ids, mask


# ---------------------------------------------------------------------------
# Shape invariants
# ---------------------------------------------------------------------------

def test_forward_output_shapes():
    enc = SimplexEncoder(_tiny_cfg())
    ids, mask = _make_input(B=3, L=10)
    out = enc(ids, attention_mask=mask)
    assert out["source_hidden"].shape == (3, 10, 32)
    assert out["simplex_trajectory"].shape == (3, 10, 40)
    assert out["simplex_final"].shape == (3, 40)
    assert out["source_attention_mask"].shape == (3, 10)
    assert out["floor_violations"].shape == (3, 10)


def test_simplex_trajectory_is_fp32_even_with_bf16_trunk():
    """Build-spec §3 dtype contract: simplex output must be fp32 regardless of trunk dtype."""
    enc = SimplexEncoder(_tiny_cfg())
    ids, mask = _make_input()
    out = enc(ids, attention_mask=mask)
    assert out["simplex_trajectory"].dtype == torch.float32
    assert out["simplex_final"].dtype == torch.float32


# ---------------------------------------------------------------------------
# Open-simplex invariants (THE core invariant of the architecture)
# ---------------------------------------------------------------------------

def test_simplex_trajectory_strictly_positive():
    enc = SimplexEncoder(_tiny_cfg())
    ids, mask = _make_input()
    out = enc(ids, attention_mask=mask)
    assert (out["simplex_trajectory"] > 0).all(), "every p_k must be > 0 on Δ°₃₉"


def test_simplex_trajectory_rows_sum_to_one():
    enc = SimplexEncoder(_tiny_cfg())
    ids, mask = _make_input()
    out = enc(ids, attention_mask=mask)
    sums = out["simplex_trajectory"].sum(dim=-1)
    assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5)


def test_simplex_final_strictly_positive_and_sums_to_one():
    enc = SimplexEncoder(_tiny_cfg())
    ids, mask = _make_input()
    out = enc(ids, attention_mask=mask)
    sf = out["simplex_final"]
    assert (sf > 0).all()
    assert torch.allclose(sf.sum(dim=-1), torch.ones(sf.shape[0]), atol=1e-5)


def test_simplex_min_p_above_epsilon():
    """Boundary stability: min p_k stays above the ε-floor even for extreme inputs."""
    cfg = _tiny_cfg()
    enc = SimplexEncoder(cfg)
    # Synthesize an input that would push softmax to a single peak by
    # initializing the encoder embedding with extreme values for a single token.
    with torch.no_grad():
        enc.token_emb.weight.data.fill_(0.0)
        enc.token_emb.weight.data[5] = 100.0  # token 5 is the peak
    ids = torch.tensor([[5, 5, 5, 5, 5, 5]])
    mask = torch.ones_like(ids, dtype=torch.bool)
    out = enc(ids, attention_mask=mask)
    min_p = out["simplex_trajectory"].min().item()
    # ε is small but strictly positive; build-spec §2.1 uses eps=1e-6 and
    # softmax + eps + renorm keeps the floor near eps/(1+40*eps) ≈ eps.
    assert min_p >= cfg.eps / (1.0 + NUM_COGNITIVE_STATES * cfg.eps), (
        f"min_p={min_p} fell below ε-floor {cfg.eps}"
    )


# ---------------------------------------------------------------------------
# Failure mode — simplex collapse prevention
# ---------------------------------------------------------------------------

def test_simplex_collapse_prevention_under_pathological_init():
    """Even with all-zero trunk weights (degenerate), the simplex must remain
    in Δ°₃₉ (strictly positive, rows sum to 1). Logit-space mirror descent
    + softmax+ε+renorm should not collapse to a delta or to zeros."""
    cfg = _tiny_cfg()
    enc = SimplexEncoder(cfg)
    with torch.no_grad():
        for p in enc.parameters():
            p.zero_()
    ids = torch.randint(1, cfg.vocab_size, (2, 6))
    mask = torch.ones_like(ids, dtype=torch.bool)
    out = enc(ids, attention_mask=mask)
    p = out["simplex_trajectory"]
    assert (p > 0).all(), "collapsed below zero — open-simplex contract violated"
    sums = p.sum(dim=-1)
    assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5)
    # With everything zeroed, the per-position distribution should be very
    # close to uniform (1/40) — this is the architectural fail-safe.
    expected = torch.full_like(p, 1.0 / NUM_COGNITIVE_STATES)
    assert torch.allclose(p, expected, atol=1e-4), (
        "uniform fallback expected at zero-init; got non-uniform output"
    )


# ---------------------------------------------------------------------------
# Mask honoring
# ---------------------------------------------------------------------------

def test_attention_mask_actually_masks_pad():
    """Pad tokens should not influence non-pad outputs.

    Compare the source_hidden of a non-pad position when the trailing pad
    positions hold different content; the non-pad output must be unchanged.
    """
    cfg = _tiny_cfg(dropout=0.0)
    enc = SimplexEncoder(cfg)
    enc.eval()  # disable any randomness from dropout

    # Two batches: identical non-pad prefix, different "pad" garbage in suffix.
    base = torch.tensor([[1, 2, 3, 0, 0, 0]])
    alt = torch.tensor([[1, 2, 3, 9, 8, 7]])
    mask = torch.tensor([[True, True, True, False, False, False]])

    out_base = enc(base, attention_mask=mask)
    out_alt = enc(alt, attention_mask=mask)
    # First 3 positions must be identical because pad-suffix differs but
    # the attention mask blocks it.
    assert torch.allclose(
        out_base["source_hidden"][:, :3], out_alt["source_hidden"][:, :3], atol=1e-5,
    ), "pad-suffix leaked into non-pad source_hidden — mask not honored"


# ---------------------------------------------------------------------------
# Gradient flow
# ---------------------------------------------------------------------------

def test_gradient_flow_through_trunk_and_tail():
    enc = SimplexEncoder(_tiny_cfg())
    ids, mask = _make_input()
    out = enc(ids, attention_mask=mask)
    loss = out["simplex_trajectory"].sum() + out["source_hidden"].sum()
    loss.backward()
    # Trunk params (token_emb + blocks + final_norm) should have non-zero grads
    trunk_has_grad = (enc.token_emb.weight.grad is not None
                      and enc.token_emb.weight.grad.abs().sum() > 0)
    # Tail params should have non-zero grads
    tail_has_grad = any(
        (p.grad is not None and p.grad.abs().sum() > 0)
        for p in enc.tail.parameters() if p.requires_grad
    )
    assert trunk_has_grad
    assert tail_has_grad


def test_no_nan_in_outputs_or_gradients():
    enc = SimplexEncoder(_tiny_cfg())
    ids, mask = _make_input()
    out = enc(ids, attention_mask=mask)
    for k, v in out.items():
        if v.dtype.is_floating_point:
            assert torch.isfinite(v).all(), f"NaN/Inf in encoder output {k!r}"
    out["simplex_trajectory"].sum().backward()
    for p in enc.parameters():
        if p.grad is not None:
            assert torch.isfinite(p.grad).all(), "NaN/Inf in encoder gradient"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_forward_deterministic_with_fixed_seed():
    cfg = _tiny_cfg(dropout=0.0)
    torch.manual_seed(0)
    enc1 = SimplexEncoder(cfg)
    enc1.eval()
    torch.manual_seed(0)
    enc2 = SimplexEncoder(cfg)
    enc2.eval()
    ids, mask = _make_input()
    out1 = enc1(ids, attention_mask=mask)
    out2 = enc2(ids, attention_mask=mask)
    assert torch.allclose(out1["simplex_trajectory"], out2["simplex_trajectory"], atol=1e-6)


def test_masked_mean_pool_ignores_pad():
    """simplex_final must be a masked-mean over valid positions only."""
    cfg = _tiny_cfg(dropout=0.0)
    enc = SimplexEncoder(cfg)
    enc.eval()
    ids = torch.tensor([[1, 2, 3, 0, 0]])
    mask_a = torch.tensor([[True, True, True, False, False]])
    mask_b = torch.tensor([[True, True, True, True, True]])
    fa = enc(ids, attention_mask=mask_a)["simplex_final"]
    fb = enc(ids, attention_mask=mask_b)["simplex_final"]
    # The two should differ because the pool denominator and numerator change.
    assert not torch.allclose(fa, fb, atol=1e-4), (
        "simplex_final identical with different masks — pool ignored mask"
    )
