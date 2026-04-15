"""Tests for CAS-Native lacunarity modules."""

import pytest
import torch

from model.lacunarity_gate import LacunarityGate
from model.lacunarity_head import LacunarityHead
from model.loss import LacunarityRegularizationLoss


class TestLacunarityGate:
    @pytest.fixture
    def gate(self):
        return LacunarityGate(num_slots=40, threshold=2.0, correction_strength=0.3)

    def test_output_shape(self, gate):
        x = torch.softmax(torch.randn(4, 40), dim=-1)
        corrected, lac = gate(x)
        assert corrected.shape == (4, 40)
        assert lac.shape == (4,)

    def test_preserves_simplex(self, gate):
        x = torch.softmax(torch.randn(4, 40), dim=-1)
        corrected, _ = gate(x)
        # All positive
        assert (corrected > 0).all()
        # Sums to 1
        sums = corrected.sum(dim=-1)
        assert torch.allclose(sums, torch.ones(4), atol=1e-4)

    def test_low_lacunarity_minimal_change(self, gate):
        # Uniform distribution = lacunarity near 0 = gate should barely change it
        x = torch.ones(2, 40) / 40.0
        corrected, lac = gate(x)
        # Lacunarity should be very low
        assert lac.mean() < 1.0

    def test_high_lacunarity_triggers_correction(self, gate):
        # Spike one slot — high lacunarity
        x = torch.full((2, 40), 0.001)
        x[:, 5] = 0.96
        x = x / x.sum(dim=-1, keepdim=True)
        corrected, lac = gate(x)
        # The spike should be dampened after correction
        assert corrected[:, 5].mean() < x[:, 5].mean()

    def test_handles_sequence_dimension(self, gate):
        x = torch.softmax(torch.randn(2, 10, 40), dim=-1)
        corrected, lac = gate(x)
        assert corrected.shape == (2, 10, 40)


class TestLacunarityHead:
    @pytest.fixture
    def head(self):
        return LacunarityHead(d_model=64)

    def test_output_keys(self, head):
        x = torch.randn(2, 64)
        out = head(x)
        assert "lacunarity" in out
        assert "gap_map" in out
        assert "domain_confidence" in out

    def test_lacunarity_shape(self, head):
        x = torch.randn(3, 64)
        out = head(x)
        assert out["lacunarity"].shape == (3, 5)

    def test_gap_map_shape_and_range(self, head):
        x = torch.randn(2, 64)
        out = head(x)
        assert out["gap_map"].shape == (2, 40)
        # Sigmoid output should be in [0, 1]
        assert (out["gap_map"] >= 0).all()
        assert (out["gap_map"] <= 1).all()

    def test_domain_confidence_shape_and_range(self, head):
        x = torch.randn(2, 64)
        out = head(x)
        assert out["domain_confidence"].shape == (2, 4)
        assert (out["domain_confidence"] >= 0).all()
        assert (out["domain_confidence"] <= 1).all()

    def test_handles_sequence_input(self, head):
        x = torch.randn(2, 10, 64)
        out = head(x)
        # Should pool across sequence and produce (batch, ...) outputs
        assert out["lacunarity"].shape == (2, 5)
        assert out["gap_map"].shape == (2, 40)


class TestLacunarityRegularizationLoss:
    @pytest.fixture
    def loss_fn(self):
        return LacunarityRegularizationLoss(alpha=0.1, target_lacunarity=0.5)

    def test_is_scalar(self, loss_fn):
        x = torch.softmax(torch.randn(4, 40), dim=-1)
        loss = loss_fn(x)
        assert loss.dim() == 0

    def test_uniform_input_low_loss(self, loss_fn):
        # Uniform distribution has lacunarity ~0, target is 0.5
        # Loss should be moderate (not zero, because 0 != 0.5)
        x = torch.ones(4, 40) / 40.0
        loss = loss_fn(x)
        assert loss.item() > 0  # Not at target

    def test_at_target_low_loss(self):
        # Custom target = 0.0, uniform input
        loss_fn = LacunarityRegularizationLoss(alpha=0.1, target_lacunarity=0.0)
        x = torch.ones(4, 40) / 40.0
        loss = loss_fn(x)
        assert loss.item() < 0.01  # Near target

    def test_extreme_concentration_high_loss(self, loss_fn):
        # Spike distribution — very high lacunarity, far from target
        x = torch.full((4, 40), 0.001)
        x[:, 0] = 0.96
        x = x / x.sum(dim=-1, keepdim=True)
        loss = loss_fn(x)
        assert loss.item() > 0.1  # Far from target
