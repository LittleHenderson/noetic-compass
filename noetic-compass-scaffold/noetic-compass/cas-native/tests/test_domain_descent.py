"""Tests for DomainDescentAttention."""

import pytest
import torch

from cas_native.model.domain_descent import (
    DomainDescentAttention,
    build_domain_descent_mask,
    NUM_COGNITIVE_STATES,
)


@pytest.fixture
def mask():
    return build_domain_descent_mask()


@pytest.fixture
def attention():
    return DomainDescentAttention(d_model=64, n_heads=4)


class TestDomainDescentMask:

    def test_mask_shape(self, mask):
        """Mask should be (40, 40)."""
        assert mask.shape == (NUM_COGNITIVE_STATES, NUM_COGNITIVE_STATES)

    def test_p_only_attends_to_p(self, mask):
        """P (0-9) cannot see C, E, or O (10-39)."""
        # P -> C/E/O should be False (blocked)
        assert not mask[0:10, 10:].any(), "P should not attend to C/E/O"

    def test_p_attends_to_p(self, mask):
        """P (0-9) can attend to P (0-9)."""
        assert mask[0:10, 0:10].all(), "P should attend to P"

    def test_c_attends_to_p_and_c(self, mask):
        """C (10-19) can attend to P+C (0-19)."""
        assert mask[10:20, 0:20].all(), "C should attend to P+C"

    def test_c_cannot_see_e_or_o(self, mask):
        """C (10-19) cannot see E or O (20-39)."""
        assert not mask[10:20, 20:].any(), "C should not attend to E/O"

    def test_e_attends_to_p_c_e(self, mask):
        """E (20-29) can attend to P+C+E (0-29)."""
        assert mask[20:30, 0:30].all(), "E should attend to P+C+E"

    def test_e_cannot_see_o(self, mask):
        """E (20-29) cannot see O (30-39)."""
        assert not mask[20:30, 30:40].any(), "E should not attend to O"

    def test_o_attends_to_all(self, mask):
        """O (30-39) can attend to all positions (0-39)."""
        assert mask[30:40, 0:40].all(), "O should attend to all"

    def test_mask_is_boolean(self, mask):
        """Mask should be boolean dtype."""
        assert mask.dtype == torch.bool


class TestDomainDescentAttention:

    def test_forward_shape(self, attention):
        """Output shape should match input shape."""
        x = torch.randn(2, NUM_COGNITIVE_STATES, 64)
        output = attention(x)
        assert output.shape == x.shape

    def test_forward_short_sequence(self, attention):
        """Should handle sequences shorter than 40."""
        x = torch.randn(2, 10, 64)
        output = attention(x)
        assert output.shape == (2, 10, 64)

    def test_forward_long_sequence(self, attention):
        """Should handle sequences longer than 40."""
        x = torch.randn(1, 80, 64)
        output = attention(x)
        assert output.shape == (1, 80, 64)

    def test_gradient_flow(self, attention):
        """Ensure gradients flow through attention."""
        x = torch.randn(2, NUM_COGNITIVE_STATES, 64, requires_grad=True)
        output = attention(x)
        loss = output.sum()
        loss.backward()
        assert x.grad is not None
