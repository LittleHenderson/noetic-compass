"""Wave 8A Agent 38 — NullSpaceRegularizationLoss tests (ADR-03 follow-up).

Covers:
  - "origin" strategy pulls unused embeddings toward the zero vector
  - Zero loss when unused embeddings are already at the origin
  - Strategy validation: unknown strategy raises a clear ValueError
  - Gradient flow: gradient reaches unused registry slots
  - Gradient isolation: admitted (non-unused) slots receive zero gradient
  - Regularization strength scales the loss linearly
  - Numerical stability with very small and very large embedding norms
  - Empty-registry edge case (fully saturated registry) -> zero loss
  - Integration: ``OmegaRegistry.unused_slot_indices`` /
    ``unused_slot_embeddings`` helpers round-trip into the loss

Strategies under test:
  - ``"origin"``    — default; pulls toward zero vector (no extra params).
  - ``"learned_anchor"`` — requires d_model; owns a d_model anchor Parameter.
  - ``"mean_inactive"``  — collective centering via detached mean.

Reference: ``cas-native/model/loss.py:564`` + ADR-03 follow-up on
training signal for unused Omega_* registry slots.
"""

from __future__ import annotations

import pytest
import torch

from cas_native.model.emergent_register import (
    DEFAULT_D_MODEL,
    DEFAULT_REGISTRY_CAPACITY,
    OmegaRegistry,
)
from cas_native.model.loss import NullSpaceRegularizationLoss


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def d_model() -> int:
    return 32


@pytest.fixture
def capacity() -> int:
    return 8


@pytest.fixture
def registry(d_model, capacity) -> OmegaRegistry:
    """Fresh OmegaRegistry with 2 admitted slots and (capacity - 2) unused."""
    reg = OmegaRegistry(d_model=d_model, capacity=capacity)
    reg.add_omega("Omega_alpha", embedding=torch.randn(d_model))
    reg.add_omega("Omega_beta", embedding=torch.randn(d_model))
    return reg


@pytest.fixture
def origin_loss(d_model) -> NullSpaceRegularizationLoss:
    return NullSpaceRegularizationLoss(strategy="origin", lambda_null=0.01)


# ---------------------------------------------------------------------------
# Strategy "origin"
# ---------------------------------------------------------------------------


class TestOriginStrategy:

    def test_origin_pulls_toward_zero(self, origin_loss, d_model):
        """Origin strategy: loss = lambda * mean(||embedding||^2) over unused."""
        # Two unused embeddings with known squared norms.
        unused = torch.tensor(
            [[3.0] + [0.0] * (d_model - 1),
             [0.0, 4.0] + [0.0] * (d_model - 2)]
        )
        # ||e0||^2 = 9, ||e1||^2 = 16, mean = 12.5, times lambda=0.01 -> 0.125
        loss = origin_loss(unused)
        assert loss.ndim == 0
        assert float(loss.item()) == pytest.approx(0.01 * 12.5, rel=1e-6)

    def test_origin_zero_when_all_zero(self, origin_loss, d_model):
        """Zero embeddings already at origin -> exactly zero loss."""
        unused = torch.zeros(4, d_model)
        loss = origin_loss(unused)
        assert float(loss.item()) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Strategy validation
# ---------------------------------------------------------------------------


class TestStrategyValidation:

    def test_unknown_strategy_rejected(self):
        """Construction rejects any strategy not in the valid set."""
        with pytest.raises(ValueError, match="Unknown null-space strategy"):
            NullSpaceRegularizationLoss(strategy="bogus")

    def test_learned_anchor_requires_d_model(self):
        """'learned_anchor' needs d_model to size the anchor parameter."""
        with pytest.raises(ValueError, match="d_model"):
            NullSpaceRegularizationLoss(strategy="learned_anchor")

    def test_learned_anchor_owns_parameter(self, d_model):
        """'learned_anchor' adds exactly d_model parameters; others add zero."""
        anchor_loss = NullSpaceRegularizationLoss(
            strategy="learned_anchor", d_model=d_model
        )
        total = sum(p.numel() for p in anchor_loss.parameters())
        assert total == d_model

        origin_only = NullSpaceRegularizationLoss(strategy="origin")
        assert sum(p.numel() for p in origin_only.parameters()) == 0

        mean_only = NullSpaceRegularizationLoss(strategy="mean_inactive")
        assert sum(p.numel() for p in mean_only.parameters()) == 0


# ---------------------------------------------------------------------------
# Gradient flow + isolation
# ---------------------------------------------------------------------------


class TestGradientFlow:

    def test_grad_reaches_unused_embeddings(self, registry, origin_loss):
        """Gradient from loss reaches the unused rows of the registry Parameter."""
        registry.zero_grad(set_to_none=True)
        unused = registry.unused_slot_embeddings()
        loss = origin_loss(unused)
        loss.backward()
        # The registry Parameter should have a grad shaped (capacity, d_model).
        assert registry.registry.grad is not None
        assert registry.registry.grad.shape == registry.registry.shape

    def test_admitted_slots_receive_zero_grad(self, registry, origin_loss):
        """Admitted (non-unused) slots must have zero gradient from this loss."""
        registry.zero_grad(set_to_none=True)
        unused = registry.unused_slot_embeddings()
        loss = origin_loss(unused)
        loss.backward()
        grad = registry.registry.grad
        assert grad is not None
        # First `active_size` rows are admitted -> zero gradient.
        admitted_grad = grad[: registry.active_size]
        assert torch.allclose(
            admitted_grad, torch.zeros_like(admitted_grad)
        )
        # Unused rows should have nonzero gradient (registry was randn-init).
        unused_grad = grad[registry.active_size :]
        assert unused_grad.abs().sum().item() > 0.0


# ---------------------------------------------------------------------------
# Regularization strength
# ---------------------------------------------------------------------------


class TestLambdaScaling:

    def test_lambda_scales_loss_linearly(self, d_model):
        """Doubling lambda_null scales the loss by exactly 2x."""
        torch.manual_seed(0)
        unused = torch.randn(5, d_model)
        weak = NullSpaceRegularizationLoss(strategy="origin", lambda_null=0.01)
        strong = NullSpaceRegularizationLoss(strategy="origin", lambda_null=0.1)
        l_weak = float(weak(unused).item())
        l_strong = float(strong(unused).item())
        # 0.1 / 0.01 = 10x
        assert l_strong == pytest.approx(10.0 * l_weak, rel=1e-6)

    def test_zero_lambda_produces_zero_loss(self, d_model):
        """lambda_null=0 collapses the loss to zero regardless of inputs."""
        unused = torch.randn(3, d_model)
        loss_fn = NullSpaceRegularizationLoss(
            strategy="origin", lambda_null=0.0
        )
        assert float(loss_fn(unused).item()) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Numerical stability
# ---------------------------------------------------------------------------


class TestNumericalStability:

    def test_very_small_norms_finite(self, origin_loss, d_model):
        """Tiny (1e-8-scale) embeddings produce finite, non-NaN loss."""
        unused = torch.full((4, d_model), 1e-8)
        loss = origin_loss(unused)
        assert torch.isfinite(loss)
        # Loss ~ lambda * d_model * (1e-8)^2 -> very small but finite.
        assert float(loss.item()) >= 0.0

    def test_very_large_norms_finite(self, origin_loss, d_model):
        """Large (1e+4-scale) embeddings do not overflow."""
        unused = torch.full((4, d_model), 1e4)
        loss = origin_loss(unused)
        assert torch.isfinite(loss)
        # Loss scales with squared norm; should be positive and bounded in fp32.
        assert float(loss.item()) > 0.0


# ---------------------------------------------------------------------------
# Empty-registry edge case
# ---------------------------------------------------------------------------


class TestEmptyRegistry:

    def test_saturated_registry_zero_loss(self, origin_loss, d_model):
        """Fully-saturated registry (unused_count == 0) -> zero-loss tensor."""
        reg = OmegaRegistry(d_model=d_model, capacity=2)
        reg.add_omega("Omega_a", embedding=torch.randn(d_model))
        reg.add_omega("Omega_b", embedding=torch.randn(d_model))
        unused = reg.unused_slot_embeddings()
        assert unused.shape == (0, d_model)
        loss = origin_loss(unused)
        assert loss.ndim == 0
        assert float(loss.item()) == pytest.approx(0.0)

    def test_saturated_mean_inactive_zero_loss(self, d_model):
        """'mean_inactive' on an empty unused set also returns zero cleanly."""
        reg = OmegaRegistry(d_model=d_model, capacity=1)
        reg.add_omega("Omega_only", embedding=torch.randn(d_model))
        unused = reg.unused_slot_embeddings()
        loss_fn = NullSpaceRegularizationLoss(strategy="mean_inactive")
        loss = loss_fn(unused)
        assert float(loss.item()) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Integration — registry helpers -> loss
# ---------------------------------------------------------------------------


class TestHelperIntegration:

    def test_unused_slot_indices_match_helper(self, registry, capacity):
        """``unused_slot_indices`` covers [active_size, capacity)."""
        idx = registry.unused_slot_indices()
        expected = torch.arange(registry.active_size, capacity)
        assert torch.equal(idx, expected)

    def test_helper_embeddings_feed_loss(self, registry, origin_loss):
        """Loss computed via helpers matches manual registry slice loss."""
        helper_unused = registry.unused_slot_embeddings()
        manual_unused = registry.registry[registry.active_size :]
        loss_helper = origin_loss(helper_unused)
        loss_manual = origin_loss(manual_unused)
        assert float(loss_helper.item()) == pytest.approx(
            float(loss_manual.item()), rel=1e-6
        )
