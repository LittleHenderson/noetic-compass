"""Tests for ^4 Vibration scoring."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cas_native.belief import (
    DEFAULT_HALF_LIFE_DAYS,
    Observation,
    apply_decay,
    compute_vibration,
    reinforce,
)


def _t(year=2026, month=5, day=4, hour=12) -> datetime:
    return datetime(year, month, day, hour)


# ---------------------------------------------------------------------------
# reinforce
# ---------------------------------------------------------------------------


def test_reinforce_grows_from_zero():
    assert pytest.approx(reinforce(0.0, 0.5)) == 0.5


def test_reinforce_saturates_near_one():
    # Starting at 0.9, evidence 0.5 should bump by 0.5 * 0.1 = 0.05.
    assert pytest.approx(reinforce(0.9, 0.5)) == 0.95


def test_reinforce_caps_at_one():
    assert reinforce(0.99, 1.0) == 1.0


def test_reinforce_rejects_negative_evidence():
    with pytest.raises(ValueError):
        reinforce(0.5, -0.1)


def test_reinforce_rejects_zero_evidence():
    with pytest.raises(ValueError):
        reinforce(0.5, 0.0)


def test_reinforce_rejects_invalid_current():
    with pytest.raises(ValueError):
        reinforce(1.5, 0.5)


# ---------------------------------------------------------------------------
# apply_decay
# ---------------------------------------------------------------------------


def test_apply_decay_zero_elapsed_unchanged():
    assert apply_decay(0.5, timedelta(seconds=0)) == 0.5


def test_apply_decay_half_life_halves():
    out = apply_decay(0.8, timedelta(days=DEFAULT_HALF_LIFE_DAYS))
    assert out == pytest.approx(0.4, rel=1e-6)


def test_apply_decay_two_half_lives_quarters():
    out = apply_decay(
        0.8, timedelta(days=2 * DEFAULT_HALF_LIFE_DAYS)
    )
    assert out == pytest.approx(0.2, rel=1e-6)


def test_apply_decay_negative_elapsed_clamps():
    # Future timestamps must not increase vibration.
    out = apply_decay(0.5, timedelta(days=-10))
    assert out == 0.5


def test_apply_decay_rejects_zero_half_life():
    with pytest.raises(ValueError):
        apply_decay(0.5, timedelta(days=1), half_life_days=0.0)


# ---------------------------------------------------------------------------
# compute_vibration
# ---------------------------------------------------------------------------


def test_empty_observations_returns_zero():
    assert compute_vibration([], _t()) == 0.0


def test_single_observation_at_now_equals_evidence():
    t = _t()
    obs = [Observation(timestamp=t, evidence_strength=0.4)]
    assert compute_vibration(obs, t) == pytest.approx(0.4)


def test_three_observations_saturate_above_threshold():
    t = _t()
    obs = [
        Observation(timestamp=t, evidence_strength=0.5),
        Observation(timestamp=t + timedelta(minutes=1), evidence_strength=0.5),
        Observation(timestamp=t + timedelta(minutes=2), evidence_strength=0.5),
    ]
    out = compute_vibration(obs, t + timedelta(minutes=2))
    # 0 -> 0.5 -> 0.75 -> 0.875 (essentially no decay over 2 min).
    assert out > 0.7
    assert out < 1.0


def test_decay_drops_old_observation_below_threshold():
    t = _t()
    obs = [Observation(timestamp=t, evidence_strength=1.0)]
    later = t + timedelta(days=2 * DEFAULT_HALF_LIFE_DAYS)
    out = compute_vibration(obs, later)
    assert out == pytest.approx(0.25, rel=1e-6)


def test_observations_sorted_internally():
    """Order of observations should not matter; compute sorts."""
    t = _t()
    obs_in_order = [
        Observation(timestamp=t, evidence_strength=0.5),
        Observation(timestamp=t + timedelta(minutes=1), evidence_strength=0.5),
    ]
    obs_reversed = list(reversed(obs_in_order))
    a = compute_vibration(obs_in_order, t + timedelta(minutes=1))
    b = compute_vibration(obs_reversed, t + timedelta(minutes=1))
    assert a == pytest.approx(b)


def test_observation_rejects_zero_strength():
    with pytest.raises(ValueError):
        Observation(timestamp=_t(), evidence_strength=0.0)
