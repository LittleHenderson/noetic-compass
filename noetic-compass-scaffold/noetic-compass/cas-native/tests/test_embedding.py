"""Tests for CognitiveStateEmbedding."""

import pytest
import torch

from cas_native.model.embedding import CognitiveStateEmbedding, NUM_COGNITIVE_STATES


@pytest.fixture
def embedding():
    return CognitiveStateEmbedding(d_model=64)


@pytest.fixture
def sample_input():
    """Sample token embeddings: (batch=2, seq=10, d_model=64)."""
    return torch.randn(2, 10, 64)


class TestCognitiveStateEmbedding:

    def test_output_shape(self, embedding, sample_input):
        """Verify output shape is (batch, seq, 40)."""
        output = embedding(sample_input)
        assert output.shape == (2, 10, NUM_COGNITIVE_STATES)

    def test_simplex_constraint(self, embedding, sample_input):
        """All outputs must sum to 1.0 (within tolerance) and all > 0."""
        output = embedding(sample_input)

        # All entries strictly positive
        assert (output > 0).all(), "All entries must be strictly positive"

        # Sum to 1.0 along last dimension
        sums = output.sum(dim=-1)
        assert torch.allclose(
            sums, torch.ones_like(sums), atol=1e-5
        ), f"Sums should be 1.0, got min={sums.min()}, max={sums.max()}"

    def test_simplex_constraint_varied_input(self, embedding):
        """Test simplex constraint with various input magnitudes."""
        for scale in [0.01, 1.0, 100.0]:
            x = torch.randn(4, 8, 64) * scale
            output = embedding(x)
            assert (output > 0).all()
            sums = output.sum(dim=-1)
            assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5)

    def test_validate_method_valid(self, embedding, sample_input):
        """validate() should return True for valid simplex vectors."""
        output = embedding(sample_input)
        assert CognitiveStateEmbedding.validate(output) is True

    def test_validate_method_catches_negative(self):
        """validate() should catch tensors with negative entries."""
        bad_tensor = torch.ones(1, 1, NUM_COGNITIVE_STATES) / NUM_COGNITIVE_STATES
        bad_tensor[0, 0, 0] = -0.1  # Violate positivity
        assert CognitiveStateEmbedding.validate(bad_tensor) is False

    def test_validate_method_catches_wrong_sum(self):
        """validate() should catch tensors that don't sum to 1."""
        bad_tensor = torch.ones(1, 1, NUM_COGNITIVE_STATES) * 0.5  # sum = 20, not 1
        assert CognitiveStateEmbedding.validate(bad_tensor) is False

    def test_validate_method_catches_wrong_dimension(self):
        """validate() should raise ValueError for wrong last dimension."""
        bad_tensor = torch.ones(1, 1, 10)
        with pytest.raises(ValueError, match="Expected last dimension"):
            CognitiveStateEmbedding.validate(bad_tensor)

    def test_gradient_flow(self, embedding, sample_input):
        """Ensure gradients flow through the embedding."""
        sample_input.requires_grad_(True)
        output = embedding(sample_input)
        loss = output.sum()
        loss.backward()
        assert sample_input.grad is not None
        assert not torch.all(sample_input.grad == 0)
