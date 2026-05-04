"""Regression tests for FractalAttentionHead construction across num_ifs_maps configs.

Bug history: prior to the fix in `cas_native.model.fractal_attention`,
`FractalAttentionHead.__init__` always passed length-4 ratio lists from the
hard-coded `cas_ratios` table to `HutchinsonOperator(num_maps=num_ifs_maps, ...)`.
`HutchinsonOperator` asserts `len(initial_ratios) == num_maps`, so any caller
with `num_ifs_maps != 4` (e.g. minimum-config tests) raised `AssertionError`
at construction. Surfaced 2026-05-04 by Mode 7 PR #25 minimum-config tests.

Fix: slice `cas_ratios[level]` to `[:num_ifs_maps]` at the call site so the
list passed in matches `num_maps`. The historical default (`num_ifs_maps=4`)
is byte-identical to the pre-fix branch — slicing a length-4 list with `[:4]`
returns the same list contents, and each `HutchinsonOperator` ends up with
exactly four `IFSContractionMap` children initialized from the same ratios as
before. See PR `fix(cas-native): FractalAttentionHead fails to construct when
num_ifs_maps != 4` for the historical context.
"""

from __future__ import annotations

import pytest
import torch

from cas_native.model.fractal_attention import FractalAttentionHead


@pytest.mark.parametrize("num_ifs_maps", [2, 3, 4, 5])
@pytest.mark.parametrize("fractal_depth", [1, 2, 3])
def test_construction_succeeds_across_num_ifs_maps_and_depth(
    num_ifs_maps: int, fractal_depth: int
) -> None:
    """Constructor must succeed for every supported (num_ifs_maps, fractal_depth) pair.

    The pre-fix branch raised AssertionError inside HutchinsonOperator whenever
    num_ifs_maps != 4. This test pins the contract that smaller and larger
    map counts construct cleanly.
    """
    head = FractalAttentionHead(
        d_model=16,
        n_heads=4,
        fractal_depth=fractal_depth,
        num_ifs_maps=num_ifs_maps,
    )

    assert len(head.hutchinson_ops) == fractal_depth
    for hutch in head.hutchinson_ops:
        assert len(hutch.maps) == num_ifs_maps


@pytest.mark.parametrize("num_ifs_maps", [2, 3, 4, 5])
@pytest.mark.parametrize("fractal_depth", [1, 2, 3])
def test_forward_pass_shape(num_ifs_maps: int, fractal_depth: int) -> None:
    """Forward pass on a small tensor must preserve (batch, seq, d_model)."""
    batch, seq, d_model, n_heads = 2, 3, 16, 4
    head = FractalAttentionHead(
        d_model=d_model,
        n_heads=n_heads,
        fractal_depth=fractal_depth,
        num_ifs_maps=num_ifs_maps,
    )

    x = torch.randn(batch, seq, d_model)
    out = head(x)

    assert out.shape == (batch, seq, d_model)
    assert torch.isfinite(out).all()


def test_default_num_ifs_maps_uses_full_cas_ratios() -> None:
    """Contract: when num_ifs_maps=4 (the historical default), each Hutchinson
    operator receives all four CAS ratios for its level. Slicing `[:4]` on the
    length-4 lists in `cas_ratios` is a no-op, so this branch is byte-identical
    to the pre-fix code path.
    """
    head = FractalAttentionHead(
        d_model=16,
        n_heads=4,
        fractal_depth=3,
        num_ifs_maps=4,
    )

    expected_ratios_per_level = [
        [0.3, 0.4, 0.5, 0.6],
        [0.2, 0.35, 0.45, 0.55],
        [0.15, 0.25, 0.35, 0.5],
    ]
    for level, hutch in enumerate(head.hutchinson_ops):
        assert len(hutch.maps) == 4
        for map_idx, contraction in enumerate(hutch.maps):
            ratio = float(contraction.ratio.detach())
            expected = expected_ratios_per_level[level][map_idx]
            # ratio = sigmoid(logit(initial_ratio)) -> initial_ratio
            assert ratio == pytest.approx(expected, abs=1e-5)


def test_extra_depth_levels_reuse_finest_ratios() -> None:
    """When fractal_depth exceeds the cas_ratios table length, extra levels
    reuse the finest ratios and slicing must still apply per level.
    """
    head = FractalAttentionHead(
        d_model=16,
        n_heads=4,
        fractal_depth=5,
        num_ifs_maps=2,
    )

    assert len(head.hutchinson_ops) == 5
    for hutch in head.hutchinson_ops:
        assert len(hutch.maps) == 2
