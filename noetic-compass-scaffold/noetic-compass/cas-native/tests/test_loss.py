"""Tests for CognitiveMetricLoss."""

import pytest
import torch

from cas_native.model.loss import CognitiveMetricLoss, fisher_rao_distance


@pytest.fixture
def loss_fn():
    return CognitiveMetricLoss()


def _make_simplex(batch: int = 2, dim: int = 40) -> torch.Tensor:
    """Create a random point on the open probability simplex."""
    raw = torch.rand(batch, dim) + 1e-4
    return raw / raw.sum(dim=-1, keepdim=True)


class TestFisherRaoDistance:

    def test_fisher_rao_identical(self):
        """d(p, p) = 0 for any p on the simplex."""
        p = _make_simplex(5, 40)
        dist = fisher_rao_distance(p, p)
        assert torch.allclose(dist, torch.zeros(5), atol=1e-5), \
            f"d(p,p) should be 0, got {dist}"

    def test_fisher_rao_symmetric(self):
        """d(p, q) = d(q, p) for any p, q on the simplex."""
        p = _make_simplex(10, 40)
        q = _make_simplex(10, 40)
        d_pq = fisher_rao_distance(p, q)
        d_qp = fisher_rao_distance(q, p)
        assert torch.allclose(d_pq, d_qp, atol=1e-6), \
            f"d(p,q) should equal d(q,p)"

    def test_fisher_rao_nonnegative(self):
        """d(p, q) >= 0 for any p, q."""
        p = _make_simplex(10, 40)
        q = _make_simplex(10, 40)
        dist = fisher_rao_distance(p, q)
        assert (dist >= -1e-6).all(), "Distance should be non-negative"

    def test_fisher_rao_triangle_inequality(self):
        """d(p, r) <= d(p, q) + d(q, r) for any p, q, r."""
        p = _make_simplex(5, 40)
        q = _make_simplex(5, 40)
        r = _make_simplex(5, 40)
        d_pr = fisher_rao_distance(p, r)
        d_pq = fisher_rao_distance(p, q)
        d_qr = fisher_rao_distance(q, r)
        assert (d_pr <= d_pq + d_qr + 1e-5).all(), "Triangle inequality violated"


class TestCognitiveMetricLoss:

    def test_total_loss_nonnegative(self, loss_fn):
        """Total loss should be >= 0."""
        batch, seq, vocab = 2, 10, 100
        logits = torch.randn(batch, seq, vocab)
        targets = torch.randint(0, vocab, (batch, seq))
        cog = _make_simplex(batch * seq, 40).view(batch, seq, 40)
        target_cog = _make_simplex(batch * seq, 40).view(batch, seq, 40)
        rpm_sat = {"a0": torch.rand(batch, seq, 64), "drive": torch.rand(batch, seq, 64)}
        inv_scores = torch.rand(batch, 7)

        total, components = loss_fn(
            logits, targets, cog, target_cog, rpm_sat, inv_scores
        )
        assert total.item() >= 0, f"Total loss should be >= 0, got {total.item()}"

    def test_lambda_scaling(self):
        """Doubling a lambda should double that component's contribution."""
        batch, seq, vocab = 2, 10, 100
        logits = torch.randn(batch, seq, vocab)
        targets = torch.randint(0, vocab, (batch, seq))
        cog = _make_simplex(batch * seq, 40).view(batch, seq, 40)
        target_cog = _make_simplex(batch * seq, 40).view(batch, seq, 40)
        rpm_sat = {"a0": torch.rand(batch, seq, 64)}
        inv_scores = torch.rand(batch, 7)

        # Loss with lambda=1
        loss1 = CognitiveMetricLoss(lambda_cognitive_drift=1.0)
        _, comp1 = loss1(logits, targets, cog, target_cog, rpm_sat, inv_scores)

        # Loss with lambda=2
        loss2 = CognitiveMetricLoss(lambda_cognitive_drift=2.0)
        _, comp2 = loss2(logits, targets, cog, target_cog, rpm_sat, inv_scores)

        # The cognitive drift component itself is the same
        assert torch.allclose(comp1["cognitive_drift"], comp2["cognitive_drift"], atol=1e-5)

        # But total should differ by approximately the drift component
        drift = comp1["cognitive_drift"].item()
        total_diff = comp2["total"].item() - comp1["total"].item()
        assert abs(total_diff - drift) < 1e-4, \
            f"Doubling lambda should add one more drift component, diff={total_diff}, drift={drift}"

    def test_all_components_present(self, loss_fn):
        """All expected loss components should be in the output dict."""
        batch, seq, vocab = 2, 10, 100
        logits = torch.randn(batch, seq, vocab)
        targets = torch.randint(0, vocab, (batch, seq))
        cog = _make_simplex(batch * seq, 40).view(batch, seq, 40)
        target_cog = _make_simplex(batch * seq, 40).view(batch, seq, 40)
        rpm_sat = {"a0": torch.rand(batch, seq, 64)}
        inv_scores = torch.rand(batch, 7)

        _, components = loss_fn(
            logits, targets, cog, target_cog, rpm_sat, inv_scores
        )

        expected_keys = {
            "lm_loss", "operator_balance", "domain_coherence",
            "rpm_satisfaction", "inversion_penalty", "cognitive_drift", "total",
        }
        assert set(components.keys()) == expected_keys

    def test_zero_inversions_zero_penalty(self, loss_fn):
        """Zero inversion scores should give zero inversion penalty."""
        inv_scores = torch.zeros(2, 7)
        penalty = loss_fn.compute_inversion_penalty(inv_scores)
        assert penalty.item() == 0.0
