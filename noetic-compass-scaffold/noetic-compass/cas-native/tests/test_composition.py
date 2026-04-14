"""Tests for the CAS generative composition module."""

import pytest
import torch

from model.composition import COMPOSE_TABLE, CompositionHead, GenerativeHead, composition_loss


class TestComposeTable:
    def test_identity(self):
        """CO-0 is the identity: CO-0 × anything = anything."""
        for j in range(10):
            assert COMPOSE_TABLE[0][j].item() == j
            assert COMPOSE_TABLE[j][0].item() == j

    def test_monoid_closure(self):
        """All results are in [0, 9]."""
        for i in range(10):
            for j in range(10):
                assert 0 <= COMPOSE_TABLE[i][j].item() <= 9

    def test_commutativity(self):
        """Composition is commutative: a × b = b × a."""
        for i in range(10):
            for j in range(10):
                assert COMPOSE_TABLE[i][j] == COMPOSE_TABLE[j][i]

    def test_specific_values(self):
        """Check known compositions."""
        assert COMPOSE_TABLE[3][8].item() == 1  # (3+8) mod 10 = 1
        assert COMPOSE_TABLE[5][5].item() == 0  # (5+5) mod 10 = 0
        assert COMPOSE_TABLE[7][7].item() == 4  # (7+7) mod 10 = 4


class TestCompositionHead:
    @pytest.fixture
    def head(self):
        return CompositionHead(d_model=64)

    def test_output_shape(self, head):
        a = torch.randn(4, 64)
        b = torch.randn(4, 64)
        result = head(a, b)
        assert result.shape == (4, 10)

    def test_output_is_distribution(self, head):
        a = torch.randn(2, 64)
        b = torch.randn(2, 64)
        result = head(a, b)
        # Should sum to approximately 1 (it's a weighted sum of softmax outputs)
        sums = result.sum(dim=-1)
        assert torch.allclose(sums, torch.ones_like(sums), atol=0.01)


class TestGenerativeHead:
    @pytest.fixture
    def head(self):
        return GenerativeHead(d_model=64)

    def test_output_keys(self, head):
        a = torch.randn(2, 64)
        b = torch.randn(2, 64)
        out = head(a, b)
        assert "emergent_state" in out
        assert "operator_composition" in out

    def test_emergent_state_shape(self, head):
        a = torch.randn(3, 64)
        b = torch.randn(3, 64)
        out = head(a, b)
        assert out["emergent_state"].shape == (3, 40)

    def test_emergent_state_is_simplex(self, head):
        a = torch.randn(2, 64)
        b = torch.randn(2, 64)
        out = head(a, b)
        sums = out["emergent_state"].sum(dim=-1)
        assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5)

    def test_operator_composition_shape(self, head):
        a = torch.randn(2, 64)
        b = torch.randn(2, 64)
        out = head(a, b)
        assert out["operator_composition"].shape == (2, 10)


class TestCompositionLoss:
    def test_perfect_prediction(self):
        """When predicted exactly matches monoid, loss should be low."""
        batch = 8
        op_a = torch.randint(0, 10, (batch,))
        op_b = torch.randint(0, 10, (batch,))
        target = (op_a + op_b) % 10

        # Create one-hot prediction matching target
        predicted = torch.zeros(batch, 10)
        predicted.scatter_(1, target.unsqueeze(1), 10.0)  # strong logits at correct position

        loss = composition_loss(predicted, op_a, op_b)
        assert loss.item() < 0.1  # should be near zero

    def test_wrong_prediction_penalized(self):
        """When predicted is wrong, loss should be high."""
        batch = 8
        op_a = torch.zeros(batch, dtype=torch.long)
        op_b = torch.ones(batch, dtype=torch.long)  # target = 1

        # Predict CO-5 (wrong)
        predicted = torch.zeros(batch, 10)
        predicted[:, 5] = 10.0

        loss = composition_loss(predicted, op_a, op_b)
        assert loss.item() > 1.0  # should be high

    def test_loss_is_scalar(self):
        predicted = torch.randn(4, 10)
        op_a = torch.randint(0, 10, (4,))
        op_b = torch.randint(0, 10, (4,))
        loss = composition_loss(predicted, op_a, op_b)
        assert loss.dim() == 0  # scalar
