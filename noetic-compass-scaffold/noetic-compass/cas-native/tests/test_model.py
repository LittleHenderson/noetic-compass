"""Tests for the full CASNativeModel assembly."""

import pytest
import torch

from cas_native.model.cas_native_model import CASNativeModel, CASNativeConfig
from cas_native.model.embedding import CognitiveStateEmbedding


@pytest.fixture
def config():
    """Small config for fast testing."""
    return CASNativeConfig(
        d_model=64,
        n_layers=2,
        n_heads=4,
        vocab_size=1000,
        max_seq_len=128,
        fractal_depth=2,
        num_ethical_propositions=7,
    )


@pytest.fixture
def model(config):
    return CASNativeModel(config)


@pytest.fixture
def sample_input():
    """Sample token IDs: (batch=2, seq=40)."""
    return torch.randint(0, 1000, (2, 40))


class TestCASNativeModel:

    def test_forward_pass(self, model, sample_input):
        """Full model should produce valid output dict without errors."""
        with torch.no_grad():
            output = model(sample_input)
        assert isinstance(output, dict)

    def test_output_keys(self, model, sample_input):
        """Output dict should have all expected keys."""
        with torch.no_grad():
            output = model(sample_input)

        expected_keys = {
            "logits",
            "cognitive_state",
            "rpm_satisfaction",
            "inversion_flags",
            "topos_truth_values",
        }
        assert set(output.keys()) == expected_keys

    def test_logits_shape(self, model, config, sample_input):
        """Logits should be (batch, seq, vocab_size)."""
        with torch.no_grad():
            output = model(sample_input)
        assert output["logits"].shape == (2, 40, config.vocab_size)

    def test_cognitive_state_on_simplex(self, model, sample_input):
        """Cognitive state should be valid open simplex vectors."""
        with torch.no_grad():
            output = model(sample_input)

        cog_state = output["cognitive_state"]
        assert cog_state.shape == (2, 40, 40)

        # Validate simplex constraint
        assert CognitiveStateEmbedding.validate(cog_state)

    def test_inversion_flags_shape(self, model, sample_input):
        """Inversion flags should be (batch, 7)."""
        with torch.no_grad():
            output = model(sample_input)
        assert output["inversion_flags"].shape == (2, 7)

    def test_inversion_flags_range(self, model, sample_input):
        """Inversion flags should be in [0, 1]."""
        with torch.no_grad():
            output = model(sample_input)
        flags = output["inversion_flags"]
        assert (flags >= 0).all() and (flags <= 1).all()

    def test_topos_truth_values_shape(self, model, config, sample_input):
        """Topos truth values should be (batch, num_propositions, 3)."""
        with torch.no_grad():
            output = model(sample_input)
        assert output["topos_truth_values"].shape == (
            2, config.num_ethical_propositions, 3
        )

    def test_rpm_satisfaction_is_scalar(self, model, sample_input):
        """RPM satisfaction should be a scalar tensor."""
        with torch.no_grad():
            output = model(sample_input)
        rpm = output["rpm_satisfaction"]
        assert rpm.dim() == 0 or rpm.numel() == 1

    def test_attention_mask(self, model):
        """Model should handle attention masks properly."""
        input_ids = torch.randint(0, 1000, (2, 40))
        mask = torch.ones(2, 40, dtype=torch.long)
        mask[:, 30:] = 0  # Mask out last 10 positions

        with torch.no_grad():
            output = model(input_ids, attention_mask=mask)
        assert output["logits"].shape == (2, 40, 1000)

    def test_default_config(self):
        """Model should work with default config."""
        model = CASNativeModel()
        assert model.config.d_model == 512
        assert model.config.n_layers == 6

    def test_gradient_flow(self, model, sample_input):
        """Gradients should flow through the full model."""
        output = model(sample_input)
        loss = output["logits"].sum() + output["cognitive_state"].sum()
        loss.backward()

        # Check that at least some parameters have gradients
        has_grad = any(
            p.grad is not None and p.grad.abs().sum() > 0
            for p in model.parameters()
        )
        assert has_grad, "At least some parameters should have gradients"
