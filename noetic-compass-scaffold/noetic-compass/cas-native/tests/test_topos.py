"""Tests for CognitiveToposReasoner."""

import pytest
import torch

from cas_native.model.topos_reasoner import (
    CognitiveToposReasoner,
    NUM_TRUTH_VALUES,
)


@pytest.fixture
def reasoner():
    return CognitiveToposReasoner(d_model=64, num_propositions=7)


class TestCognitiveToposReasoner:

    def test_output_shape(self, reasoner):
        """Output should be (batch, num_propositions, 3)."""
        x = torch.randn(2, 10, 64)  # (batch, seq, d_model)
        output = reasoner(x)
        assert output.shape == (2, 7, NUM_TRUTH_VALUES)

    def test_output_shape_no_seq(self, reasoner):
        """Should also accept (batch, d_model) input."""
        x = torch.randn(2, 64)
        output = reasoner(x)
        assert output.shape == (2, 7, NUM_TRUTH_VALUES)

    def test_probabilities_sum_to_one(self, reasoner):
        """Each proposition's 3 truth values should sum to 1."""
        x = torch.randn(4, 10, 64)
        output = reasoner(x)

        sums = output.sum(dim=-1)  # (batch, num_propositions)
        assert torch.allclose(
            sums, torch.ones_like(sums), atol=1e-5
        ), f"Truth probabilities should sum to 1, got {sums}"

    def test_three_values(self, reasoner):
        """Output should have exactly 3 truth value classes."""
        x = torch.randn(2, 10, 64)
        output = reasoner(x)
        assert output.shape[-1] == 3

    def test_probabilities_nonnegative(self, reasoner):
        """All probability values should be >= 0."""
        x = torch.randn(2, 10, 64)
        output = reasoner(x)
        assert (output >= 0).all(), "All probabilities should be non-negative"

    def test_undetermined_is_valid(self, reasoner):
        """The 'undetermined' truth value should have nonzero probability."""
        # With random weights, undetermined should generally be nonzero
        x = torch.randn(10, 10, 64)
        output = reasoner(x)
        undetermined_probs = output[:, :, 2]  # Index 2 = undetermined
        # At least some propositions should have nonzero undetermined probability
        assert (undetermined_probs > 1e-6).any(), \
            "Undetermined should be a valid (nonzero) output"

    def test_gradient_flow(self, reasoner):
        """Gradients should flow through the reasoner."""
        x = torch.randn(2, 10, 64, requires_grad=True)
        output = reasoner(x)
        loss = output.sum()
        loss.backward()
        assert x.grad is not None
