"""Stage 2 unit tests for FisherRaoLoss.

Focused on metric-axiom invariants (identity, symmetry, non-negativity),
numerical safety at simplex-boundary regions (σ→1, σ→0), mask correctness,
finite gradients, and one explicit failure-mode test for mis-shaped or
bad simplex targets.
"""
from __future__ import annotations

import math
import pytest
import torch

from cas_native.training.fisher_rao_loss import FisherRaoLoss, FisherRaoLossConfig


NUM_STATES = 40


def _uniform(B: int = 2, L: int = 4) -> torch.Tensor:
    return torch.full((B, L, NUM_STATES), 1.0 / NUM_STATES)


def _delta_eps(state_idx: int, B: int = 2, L: int = 4, peak: float = 0.9) -> torch.Tensor:
    """Near-one-hot anchor point on Δ°₃₉."""
    eps = (1.0 - peak) / (NUM_STATES - 1)
    p = torch.full((B, L, NUM_STATES), eps)
    p[..., state_idx] = peak
    return p


# ---------------------------------------------------------------------------
# Metric-axiom invariants
# ---------------------------------------------------------------------------

def test_identity_distance_to_self_is_zero():
    loss = FisherRaoLoss()
    p = _delta_eps(7)
    val = loss(p, p, mask=torch.ones(p.shape[0], p.shape[1], dtype=torch.bool))
    # fp64 internal, fp32 output. With clamp, residual should be very small.
    assert val.item() < 1e-6, f"L_FR(p, p) should be 0, got {val.item()}"


def test_symmetry():
    loss = FisherRaoLoss()
    torch.manual_seed(0)
    p = _delta_eps(3)
    q = _delta_eps(11)
    m = torch.ones(p.shape[0], p.shape[1], dtype=torch.bool)
    a = loss(p, q, mask=m).item()
    b = loss(q, p, mask=m).item()
    assert math.isclose(a, b, abs_tol=1e-6), f"symmetry broken: {a} vs {b}"


def test_non_negativity():
    loss = FisherRaoLoss()
    torch.manual_seed(0)
    for _ in range(5):
        p = torch.rand(2, 3, NUM_STATES); p = p / p.sum(-1, keepdim=True)
        q = torch.rand(2, 3, NUM_STATES); q = q / q.sum(-1, keepdim=True)
        val = loss(p, q, mask=torch.ones(2, 3, dtype=torch.bool))
        assert val.item() >= 0.0


def test_antipode_distance_approaches_pi_squared():
    """Disjoint near-one-hots on different states should give d → π, hence d² → π²."""
    loss = FisherRaoLoss()
    # Use very-near-one-hot so σ → near 0
    cfg = FisherRaoLossConfig()
    cfg.sigma_clamp_high = 1.0 - 1e-7
    eps = 1e-5
    p = torch.full((1, 1, NUM_STATES), eps); p[0, 0, 0] = 1.0 - eps * (NUM_STATES - 1)
    q = torch.full((1, 1, NUM_STATES), eps); q[0, 0, 1] = 1.0 - eps * (NUM_STATES - 1)
    m = torch.ones(1, 1, dtype=torch.bool)
    val = loss(p, q, mask=m).item()
    # d ≈ π → d² ≈ π². Allow generous tolerance because eps>0 means we never
    # quite reach σ=0, so d² is slightly under π².
    assert val > (math.pi ** 2) * 0.95, f"antipode distance² should approach π² ≈ 9.87, got {val}"
    assert val <= (math.pi ** 2) + 1e-4


# ---------------------------------------------------------------------------
# Mask correctness — the key training-time property
# ---------------------------------------------------------------------------

def test_mask_zeros_non_anchor_contributions():
    """Two batches differing only at non-anchor positions must produce identical loss."""
    loss = FisherRaoLoss()
    p_a = _delta_eps(2, B=1, L=4)
    p_b = _delta_eps(2, B=1, L=4)
    # Mutate non-anchor positions only (mask says only position 0 is an anchor)
    p_b[0, 1] = torch.rand(NUM_STATES); p_b[0, 1] = p_b[0, 1] / p_b[0, 1].sum()
    p_b[0, 2] = torch.rand(NUM_STATES); p_b[0, 2] = p_b[0, 2] / p_b[0, 2].sum()
    p_b[0, 3] = torch.rand(NUM_STATES); p_b[0, 3] = p_b[0, 3] / p_b[0, 3].sum()
    q = _delta_eps(2, B=1, L=4)
    mask = torch.zeros(1, 4, dtype=torch.bool); mask[0, 0] = True
    val_a = loss(p_a, q, mask=mask).item()
    val_b = loss(p_b, q, mask=mask).item()
    assert math.isclose(val_a, val_b, abs_tol=1e-7), (
        f"mask not honored: non-anchor mutation changed loss {val_a} → {val_b}"
    )


def test_empty_mask_returns_zero():
    """If no positions are anchors, loss should be 0 (denominator clamped to 1)."""
    loss = FisherRaoLoss()
    p = _delta_eps(0); q = _delta_eps(5)
    mask = torch.zeros(p.shape[0], p.shape[1], dtype=torch.bool)
    val = loss(p, q, mask=mask).item()
    assert val == 0.0


def test_anchor_count_metric():
    loss = FisherRaoLoss()
    p = _delta_eps(0); q = _delta_eps(0)
    mask = torch.zeros(2, 4, dtype=torch.bool)
    mask[0, 0] = True; mask[0, 2] = True; mask[1, 1] = True
    _ = loss(p, q, mask=mask)
    assert loss.last_metrics["loss_fr_anchor_count"].item() == 3.0


# ---------------------------------------------------------------------------
# Numerical safety at simplex-boundary regions
# ---------------------------------------------------------------------------

def test_no_nan_when_sigma_near_one():
    """Distance near σ=1 (p ≈ q) should NOT NaN — arccos′ is unbounded there
    but the squared-distance form suppresses the gradient blowup."""
    loss = FisherRaoLoss()
    p = _delta_eps(5)
    q = _delta_eps(5)  # same point → σ=1
    mask = torch.ones(p.shape[0], p.shape[1], dtype=torch.bool)
    val = loss(p, q, mask=mask)
    assert torch.isfinite(val).all()
    # Backward also must not produce NaN
    p2 = p.clone().requires_grad_(True)
    val2 = loss(p2, q, mask=mask)
    val2.backward()
    assert torch.isfinite(p2.grad).all(), "NaN gradient at σ≈1 — clamp not effective"


def test_no_nan_when_sigma_near_zero():
    """Antipode distance: σ → 0 means d → π. Must not NaN."""
    loss = FisherRaoLoss()
    eps = 1e-4
    p = torch.full((1, 1, NUM_STATES), eps); p[0, 0, 0] = 1.0 - eps * (NUM_STATES - 1)
    q = torch.full((1, 1, NUM_STATES), eps); q[0, 0, 1] = 1.0 - eps * (NUM_STATES - 1)
    mask = torch.ones(1, 1, dtype=torch.bool)
    val = loss(p, q, mask=mask)
    assert torch.isfinite(val).all()


def test_finite_gradients_under_extreme_inputs():
    loss = FisherRaoLoss()
    eps = 1e-5
    p = torch.full((1, 1, NUM_STATES), eps)
    p[0, 0, 0] = 1.0 - eps * (NUM_STATES - 1)
    p = p.clone().requires_grad_(True)
    q = torch.full((1, 1, NUM_STATES), 1.0 / NUM_STATES)
    mask = torch.ones(1, 1, dtype=torch.bool)
    val = loss(p, q, mask=mask)
    val.backward()
    assert torch.isfinite(p.grad).all()


# ---------------------------------------------------------------------------
# Internal-dtype contract
# ---------------------------------------------------------------------------

def test_fp64_internal_cast_preserved():
    """Internal compute should be fp64; output scalar should match input dtype."""
    loss = FisherRaoLoss()
    p = _delta_eps(0).to(dtype=torch.float32)
    q = _delta_eps(5).to(dtype=torch.float32)
    mask = torch.ones(p.shape[0], p.shape[1], dtype=torch.bool)
    val = loss(p, q, mask=mask)
    assert val.dtype == torch.float32, f"output dtype must match input fp32, got {val.dtype}"


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------

def test_shape_mismatch_raises():
    loss = FisherRaoLoss()
    p = torch.rand(2, 3, NUM_STATES); p = p / p.sum(-1, keepdim=True)
    q = torch.rand(2, 4, NUM_STATES); q = q / q.sum(-1, keepdim=True)
    with pytest.raises(ValueError, match="same shape"):
        loss(p, q)


def test_wrong_last_dim_raises():
    loss = FisherRaoLoss()
    p = torch.rand(2, 3, 39); p = p / p.sum(-1, keepdim=True)
    q = torch.rand(2, 3, 39); q = q / q.sum(-1, keepdim=True)
    with pytest.raises(ValueError, match="Last dim"):
        loss(p, q)


def test_bad_simplex_target_with_zeros_does_not_nan():
    """Failure-mode: target q has a zero entry (violates open-simplex strict
    positivity). The clamp_min(eps_for_sqrt) before sqrt should defend
    against this without NaN-ing; the loss should be finite, even if the
    'right' answer is undefined."""
    loss = FisherRaoLoss()
    p = _delta_eps(0)
    q = _delta_eps(5).clone()
    q[..., 0] = 0.0  # invalid: violates open-simplex
    # Renormalize so it's still row-stochastic (but no longer strict positive)
    q = q / q.sum(-1, keepdim=True)
    mask = torch.ones(p.shape[0], p.shape[1], dtype=torch.bool)
    val = loss(p, q, mask=mask)
    assert torch.isfinite(val).all(), "bad target with zero entry should not NaN"
