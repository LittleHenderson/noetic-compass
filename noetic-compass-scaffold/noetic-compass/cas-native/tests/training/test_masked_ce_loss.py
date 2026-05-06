"""Tests for ``masked_cross_entropy``."""

from __future__ import annotations

import pytest
import torch
import torch.nn.functional as F

from cas_native.training.masked_ce_loss import masked_cross_entropy


def _logits(b: int, l: int, v: int, *, seed: int = 0) -> torch.Tensor:
    g = torch.Generator().manual_seed(int(seed))
    return torch.randn((b, l, v), generator=g)


def test_all_ones_mask_matches_standard_ce():
    """With every position valid, masked CE == F.cross_entropy."""
    b, l, v = 2, 5, 11
    logits = _logits(b, l, v, seed=1)
    targets = torch.randint(0, v, (b, l))
    mask = torch.ones((b, l), dtype=torch.bool)

    masked = masked_cross_entropy(logits, targets, mask, reduction="mean")
    standard = F.cross_entropy(logits.reshape(b * l, v), targets.reshape(b * l), reduction="mean")
    assert torch.isclose(masked, standard, atol=1e-6)


def test_ignore_index_skips_targets():
    """Targets equal to ignore_index do not contribute."""
    b, l, v = 2, 4, 7
    logits = _logits(b, l, v, seed=2)
    targets = torch.tensor([[0, 1, -100, -100], [3, 2, 1, -100]])

    masked = masked_cross_entropy(logits, targets, reduction="sum")
    # Manually compute over valid positions only
    valid_logits = torch.cat([
        logits[0, 0:2].reshape(-1, v),
        logits[1, 0:3].reshape(-1, v),
    ], dim=0)
    valid_targets = torch.tensor([0, 1, 3, 2, 1])
    expected = F.cross_entropy(valid_logits, valid_targets, reduction="sum")
    assert torch.isclose(masked, expected, atol=1e-5)


def test_all_zero_mask_returns_finite_zero():
    """An all-False mask must not return NaN — return 0 cleanly."""
    b, l, v = 2, 3, 5
    logits = _logits(b, l, v, seed=3)
    targets = torch.randint(0, v, (b, l))
    mask = torch.zeros((b, l), dtype=torch.bool)
    out = masked_cross_entropy(logits, targets, mask, reduction="mean")
    assert torch.isfinite(out).item()
    assert out.item() == 0.0


def test_label_smoothing_changes_loss():
    """label_smoothing > 0 produces a different loss than label_smoothing=0."""
    b, l, v = 1, 4, 9
    logits = _logits(b, l, v, seed=4)
    targets = torch.tensor([[0, 1, 2, 3]])
    mask = torch.ones((b, l), dtype=torch.bool)

    base = masked_cross_entropy(logits, targets, mask, label_smoothing=0.0)
    smoothed = masked_cross_entropy(logits, targets, mask, label_smoothing=0.1)
    assert not torch.isclose(base, smoothed)


def test_reduction_none_returns_per_position_tensor():
    """reduction='none' returns a (B, L) tensor with skipped positions == 0."""
    b, l, v = 2, 4, 7
    logits = _logits(b, l, v, seed=5)
    targets = torch.tensor([[0, 1, 2, 3], [4, 5, 6, 0]])
    mask = torch.tensor([[True, True, False, False], [True, True, True, True]])
    out = masked_cross_entropy(logits, targets, mask, reduction="none")
    assert out.shape == (b, l)
    # Skipped positions are zeroed
    assert out[0, 2].item() == 0.0
    assert out[0, 3].item() == 0.0
    # Included positions are positive (cross-entropy is non-negative)
    assert out[0, 0].item() > 0.0
    assert out[0, 1].item() > 0.0


def test_invalid_shape_raises():
    """Shape-mismatched inputs raise clearly at the boundary."""
    b, l, v = 2, 4, 7
    logits = _logits(b, l, v, seed=6)
    bad_targets = torch.randint(0, v, (b, l + 1))
    with pytest.raises(ValueError):
        masked_cross_entropy(logits, bad_targets)


def test_invalid_reduction_raises():
    b, l, v = 1, 2, 3
    logits = _logits(b, l, v)
    targets = torch.zeros((b, l), dtype=torch.long)
    with pytest.raises(ValueError):
        masked_cross_entropy(logits, targets, reduction="bogus")
