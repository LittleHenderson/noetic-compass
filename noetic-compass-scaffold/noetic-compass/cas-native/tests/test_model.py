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
            "hidden_states",
            "pooled_hidden_state",
            "cognitive_state",
            "raw_cognitive_state",
            "rpm_satisfaction",
            "inversion_flags",
            "topos_truth_values",
            "lacunarity_scores",
            "lacunarity_meta",
        }
        assert set(output.keys()) == expected_keys

    def test_logits_shape(self, model, config, sample_input):
        """Logits should be (batch, seq, vocab_size)."""
        with torch.no_grad():
            output = model(sample_input)
        assert output["logits"].shape == (2, 40, config.vocab_size)

    def test_hidden_state_adapter_shapes(self, model, config, sample_input):
        """Forward exposes final hidden states for structured prediction."""
        with torch.no_grad():
            output = model(sample_input)

        assert output["hidden_states"].shape == (2, 40, config.d_model)
        assert output["pooled_hidden_state"].shape == (2, config.d_model)

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

    def test_padding_mask_invariance(self, model):
        """Masked suffix tokens should not change unmasked prefix outputs."""
        model.eval()
        prefix = torch.randint(0, 1000, (1, 30))
        padded = torch.cat([prefix, torch.randint(0, 1000, (1, 10))], dim=1)
        mask = torch.cat(
            [
                torch.ones(1, 30, dtype=torch.long),
                torch.zeros(1, 10, dtype=torch.long),
            ],
            dim=1,
        )

        with torch.no_grad():
            short_out = model(prefix)
            padded_out = model(padded, attention_mask=mask)

        assert torch.allclose(
            short_out["logits"],
            padded_out["logits"][:, :30, :],
            atol=1e-5,
        )
        assert torch.allclose(
            short_out["cognitive_state"],
            padded_out["cognitive_state"][:, :30, :],
            atol=1e-5,
        )

    def test_causal_lm_future_token_invariance(self):
        """Causal LM mode must not let suffix tokens affect prefix logits."""
        torch.manual_seed(0)
        config = CASNativeConfig(
            d_model=32,
            n_layers=1,
            n_heads=4,
            vocab_size=64,
            max_seq_len=16,
            fractal_depth=1,
            num_ethical_propositions=3,
            dropout=0.0,
            causal_lm=True,
        )
        model = CASNativeModel(config)
        model.eval()

        base = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]], dtype=torch.long)
        mutated = base.clone()
        mutated[:, 4:] = torch.tensor([[31, 32, 33, 34]], dtype=torch.long)

        with torch.no_grad():
            base_logits = model(base)["logits"][:, :4, :]
            mutated_logits = model(mutated)["logits"][:, :4, :]

        assert torch.allclose(base_logits, mutated_logits, atol=1e-5)

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
