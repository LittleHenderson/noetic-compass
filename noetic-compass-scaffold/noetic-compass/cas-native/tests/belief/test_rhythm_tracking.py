"""Tests for ^7 Rhythm tracking."""

from __future__ import annotations

from datetime import datetime

import pytest

from cas_native.belief import (
    Belief,
    MIN_RHYTHM_FOR_LOCK,
    bump_rhythm,
    has_rhythm_for_lock,
)


def _build(rhythm_count: int = 0) -> Belief:
    t = datetime(2026, 5, 4, 12, 0, 0)
    return Belief(
        claim_key="k",
        claim_text="t",
        cas_expression="^4^P",
        vibration=0.0,
        rhythm_count=rhythm_count,
        rpm_chain_satisfied=False,
        rpm_chain_status={},
        inversion_scan_clean=True,
        inversion_scan_axes={},
        first_seen=t,
        last_reinforced=t,
    )


def test_bump_increments_count_by_one():
    b = _build(rhythm_count=2)
    out = bump_rhythm(b, 0.5)
    assert out.rhythm_count == 3


def test_bump_does_not_mutate_input():
    b = _build(rhythm_count=2)
    _ = bump_rhythm(b, 0.5)
    assert b.rhythm_count == 2


def test_bump_updates_last_reinforced():
    b = _build()
    new_now = datetime(2026, 6, 1, 12, 0, 0)
    out = bump_rhythm(b, 0.5, now=new_now)
    assert out.last_reinforced == new_now


def test_bump_rejects_zero_evidence():
    b = _build()
    with pytest.raises(ValueError):
        bump_rhythm(b, 0.0)


def test_bump_rejects_negative_evidence():
    b = _build()
    with pytest.raises(ValueError):
        bump_rhythm(b, -0.1)


def test_has_rhythm_for_lock_threshold():
    assert has_rhythm_for_lock(_build(rhythm_count=MIN_RHYTHM_FOR_LOCK))
    assert has_rhythm_for_lock(_build(rhythm_count=MIN_RHYTHM_FOR_LOCK + 5))


def test_has_rhythm_for_lock_below_threshold():
    assert not has_rhythm_for_lock(_build(rhythm_count=MIN_RHYTHM_FOR_LOCK - 1))


def test_min_rhythm_constant_is_at_least_three():
    # Lock rule contract: a single fluky observation must not lock.
    assert MIN_RHYTHM_FOR_LOCK >= 3
