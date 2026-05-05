"""Tests for the Belief dataclass."""

from __future__ import annotations

from datetime import datetime

import pytest

from cas_native.belief import Belief


def _now() -> datetime:
    return datetime(2026, 5, 4, 12, 0, 0)


def _build(**overrides) -> Belief:
    base = dict(
        claim_key="abc123",
        claim_text="practice makes perfect",
        cas_expression="^7^O",
        vibration=0.5,
        rhythm_count=2,
        rpm_chain_satisfied=True,
        rpm_chain_status={"stages": {}},
        inversion_scan_clean=True,
        inversion_scan_axes={"N": {"clean": True}},
        first_seen=_now(),
        last_reinforced=_now(),
        sources=["chat-session"],
        locked=False,
    )
    base.update(overrides)
    return Belief(**base)


def test_dataclass_constructs_with_defaults():
    b = _build()
    assert b.claim_key == "abc123"
    assert b.vibration == 0.5
    assert b.rhythm_count == 2
    assert b.locked is False
    assert b.sources == ["chat-session"]


def test_vibration_below_zero_rejected():
    with pytest.raises(ValueError, match="vibration"):
        _build(vibration=-0.01)


def test_vibration_above_one_rejected():
    with pytest.raises(ValueError, match="vibration"):
        _build(vibration=1.5)


def test_negative_rhythm_rejected():
    with pytest.raises(ValueError, match="rhythm_count"):
        _build(rhythm_count=-1)


def test_empty_claim_key_rejected():
    with pytest.raises(ValueError, match="claim_key"):
        _build(claim_key="")


def test_first_seen_must_be_datetime():
    with pytest.raises(TypeError, match="first_seen"):
        _build(first_seen="2026-05-04")


def test_last_reinforced_must_be_datetime():
    with pytest.raises(TypeError, match="last_reinforced"):
        _build(last_reinforced=12345)


def test_short_status_locked_renders_check():
    b = _build(
        vibration=0.82,
        rhythm_count=14,
        rpm_chain_satisfied=True,
        inversion_scan_clean=True,
        inversion_scan_axes={"N": {"clean": True}},
        locked=True,
    )
    s = b.short_status()
    assert "LOCKED" in s
    assert "^4=0.82" in s
    assert "^7=14" in s
    assert "RPM" in s and "Inv" in s


def test_short_status_open_with_axis_failure_marks_axis():
    b = _build(
        vibration=0.34,
        rhythm_count=2,
        rpm_chain_satisfied=True,
        inversion_scan_clean=False,
        inversion_scan_axes={
            "N": {"clean": True},
            "W": {"clean": False, "reason": "precedence violated"},
            "F": {"clean": True},
        },
        locked=False,
    )
    s = b.short_status()
    assert "open" in s
    assert "Inv" in s and "(W)" in s


def test_short_status_lists_multiple_failing_axes():
    b = _build(
        vibration=0.4,
        rhythm_count=1,
        inversion_scan_clean=False,
        inversion_scan_axes={
            "N": {"clean": False},
            "W": {"clean": False},
        },
    )
    s = b.short_status()
    assert "N" in s and "W" in s
