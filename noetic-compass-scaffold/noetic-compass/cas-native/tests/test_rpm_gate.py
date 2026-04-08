"""Tests for PrerequisiteGateLayer."""

import pytest
import torch

from cas_native.model.rpm_gate import PrerequisiteGateLayer, SoftGate


@pytest.fixture
def gate():
    return PrerequisiteGateLayer(d_model=64, threshold=0.5)


@pytest.fixture
def sample_input():
    return torch.randn(2, 10, 64)


class TestSoftGate:

    def test_output_range(self):
        """Gate satisfaction scores must be in [0, 1]."""
        gate = SoftGate(d_model=64)
        x = torch.randn(4, 8, 64)
        gated, satisfaction = gate(x)
        assert (satisfaction >= 0).all()
        assert (satisfaction <= 1).all()

    def test_output_shape(self):
        """Output shapes must match input."""
        gate = SoftGate(d_model=64)
        x = torch.randn(4, 8, 64)
        gated, satisfaction = gate(x)
        assert gated.shape == x.shape
        assert satisfaction.shape == x.shape


class TestPrerequisiteGateLayer:

    def test_gate_output_range(self, gate, sample_input):
        """All gate satisfaction outputs must be in [0, 1]."""
        output, satisfaction_dict = gate(sample_input)
        for name, sat in satisfaction_dict.items():
            assert (sat >= 0).all(), f"Gate {name} has negative satisfaction"
            assert (sat <= 1).all(), f"Gate {name} has satisfaction > 1"

    def test_low_prerequisite_attenuates(self, gate):
        """Low input signals should be attenuated (output magnitude < input)."""
        # Use very negative input to push sigmoid toward 0
        x = torch.full((1, 1, 64), -10.0)
        output, satisfaction_dict = gate(x)

        # At least some gates should have low satisfaction
        mean_sat = torch.stack([s.mean() for s in satisfaction_dict.values()]).mean()
        # The output should be attenuated (smaller magnitude) compared to
        # what an identity pass-through would give
        assert output.abs().mean() < x.abs().mean(), \
            "Output should be attenuated for low prerequisite signals"

    def test_forward_shape(self, gate, sample_input):
        """Output shape must match input shape."""
        output, satisfaction_dict = gate(sample_input)
        assert output.shape == sample_input.shape

    def test_satisfaction_dict_keys(self, gate, sample_input):
        """Satisfaction dict should have all 4 gate keys."""
        _, satisfaction_dict = gate(sample_input)
        expected_keys = {"a0", "drive", "wisdom", "proficiency"}
        assert set(satisfaction_dict.keys()) == expected_keys

    def test_section_retraction_not_symmetric(self, gate):
        """eta followed by epsilon should NOT be identity (CORRECTION 2).

        epsilon . eta = id (approximately, via learned mapping)
        BUT eta . epsilon != id (information loss)
        """
        x = torch.randn(1, 5, 64)
        # Forward through eta then epsilon
        embedded = gate.eta(x)
        retracted = gate.epsilon(embedded)
        # These should be different from re-embedding
        re_embedded = gate.eta(retracted)
        # eta(epsilon(eta(x))) should NOT equal eta(x) in general
        # (information loss in the retraction)
        # We just check they're not identical (with random init they won't be)
        assert not torch.allclose(re_embedded, embedded, atol=1e-3), \
            "Section-retraction should not be symmetric"

    def test_cached_satisfaction(self, gate, sample_input):
        """After forward, cached satisfaction should be populated."""
        gate(sample_input)
        assert len(gate._cached_satisfaction) == 4
        for key in ["a0", "drive", "wisdom", "proficiency"]:
            assert key in gate._cached_satisfaction
            assert not gate._cached_satisfaction[key].requires_grad

    def test_gradient_flow(self, gate, sample_input):
        """Gradients should flow through the gate."""
        sample_input.requires_grad_(True)
        output, _ = gate(sample_input)
        loss = output.sum()
        loss.backward()
        assert sample_input.grad is not None
