"""Tests for the AI control surface: typed dials with owner-set bounds.

Standalone -- only depends on cas_forex.ai_control_surface and the instruments
list it imports. No other in-flight modules required.
"""

from __future__ import annotations

import math

import pytest

from cas_forex.ai_control_surface import (
    LEVER_NAMES,
    SUPPORTED_SESSIONS,
    AiControlSurface,
)
from cas_forex.instruments import SUPPORTED_SYMBOLS


def test_defaults_correct():
    s = AiControlSurface()
    assert s.get("edge_threshold") == 0.65
    assert s.get("max_risk_pct_per_trade") == 0.5
    assert s.get("max_concurrent_trades") == 15
    assert s.get("daily_loss_cap_usd") == 0.0
    assert s.get("max_compound_units") == 4
    assert set(s.get("symbols")) == set(SUPPORTED_SYMBOLS)
    assert set(s.get("sessions")) == set(SUPPORTED_SESSIONS)


def test_adjust_within_bounds():
    s = AiControlSurface()
    res = s.adjust("edge_threshold", 0.72)
    assert res["ok"] is True
    assert res["clamped"] is False
    assert res["old"] == 0.65
    assert res["new"] == 0.72
    assert s.get("edge_threshold") == 0.72


def test_clamp_at_max_reports_clamped():
    s = AiControlSurface()
    res = s.adjust("max_risk_pct_per_trade", 99.0)
    assert res["ok"] is True
    assert res["clamped"] is True
    assert res["new"] == 5.0  # max bound
    assert s.get("max_risk_pct_per_trade") == 5.0


def test_clamp_at_min_reports_clamped():
    s = AiControlSurface()
    res = s.adjust("edge_threshold", 0.10)
    assert res["ok"] is True
    assert res["clamped"] is True
    assert res["new"] == 0.50  # min bound
    assert s.get("edge_threshold") == 0.50


def test_daily_loss_cap_clamps_negative_to_zero_and_allows_large():
    s = AiControlSurface()
    low = s.adjust("daily_loss_cap_usd", -100.0)
    assert low["clamped"] is True
    assert low["new"] == 0.0
    high = s.adjust("daily_loss_cap_usd", 1_000_000.0)
    assert high["clamped"] is False  # no upper guardrail
    assert s.get("daily_loss_cap_usd") == 1_000_000.0


def test_int_lever_coerces_and_clamps():
    s = AiControlSurface()
    res = s.adjust("max_concurrent_trades", 3.9)
    assert res["ok"] is True
    assert res["new"] == 4  # rounded int
    over = s.adjust("max_concurrent_trades", 500)
    assert over["clamped"] is True
    assert over["new"] == 50
    under = s.adjust("max_concurrent_trades", 0)
    assert under["clamped"] is True
    assert under["new"] == 1


def test_unknown_lever_rejected():
    s = AiControlSurface()
    res = s.adjust("go_live", True)
    assert res["ok"] is False
    assert res["clamped"] is False
    assert "Unknown lever" in res["reason"]
    # No new lever was created.
    assert "go_live" not in s.snapshot()["values"]


def test_get_unknown_lever_raises():
    s = AiControlSurface()
    with pytest.raises(KeyError):
        s.get("go_live")


def test_non_numeric_scalar_rejected_without_state_change():
    s = AiControlSurface()
    res = s.adjust("edge_threshold", "high")
    assert res["ok"] is False
    assert s.get("edge_threshold") == 0.65


def test_set_lever_subset_and_drop_reporting():
    s = AiControlSurface()
    symbol = sorted(SUPPORTED_SYMBOLS)[0]
    res = s.adjust("symbols", [symbol, "FAKE/PAIR"])
    assert res["ok"] is True
    assert res["clamped"] is True
    assert s.get("symbols") == [symbol]
    assert "FAKE/PAIR" in res["reason"]


def test_set_lever_all_invalid_refused():
    s = AiControlSurface()
    before = s.get("sessions")
    res = s.adjust("sessions", ["Mars", "Moon"])
    assert res["ok"] is False
    assert s.get("sessions") == before  # unchanged


def test_sessions_subset_accepted():
    s = AiControlSurface()
    res = s.adjust("sessions", ["London", "NewYork"])
    assert res["ok"] is True
    assert res["clamped"] is False
    assert s.get("sessions") == ["London", "NewYork"]


def test_snapshot_round_trips():
    s = AiControlSurface()
    s.adjust("edge_threshold", 0.80)
    s.adjust("max_compound_units", 7)
    snap = s.snapshot()
    assert snap["values"]["edge_threshold"] == 0.80
    assert snap["values"]["max_compound_units"] == 7
    # bounds present for every lever
    for name in LEVER_NAMES:
        assert name in snap["bounds"]
    # values are plain copies, not internal references
    snap["values"]["symbols"].append("MUTATED")
    assert "MUTATED" not in s.get("symbols")


def test_persist_hook_called_on_adjust():
    calls = []
    s = AiControlSurface(persist=lambda snap: calls.append(snap))
    s.adjust("edge_threshold", 0.70)
    assert len(calls) == 1
    assert calls[0]["values"]["edge_threshold"] == 0.70


def test_persist_hook_not_called_on_rejected_adjust():
    calls = []
    s = AiControlSurface(persist=lambda snap: calls.append(snap))
    s.adjust("unknown_lever", 1)
    assert calls == []


def test_persist_hook_failure_does_not_break_adjust():
    def boom(_snap):
        raise RuntimeError("storage down")

    s = AiControlSurface(persist=boom)
    res = s.adjust("edge_threshold", 0.70)
    assert res["ok"] is True
    assert s.get("edge_threshold") == 0.70


def test_reset_restores_defaults_and_fires_persist():
    calls = []
    s = AiControlSurface(persist=lambda snap: calls.append(snap))
    s.adjust("edge_threshold", 0.90)
    s.adjust("max_concurrent_trades", 2)
    calls.clear()
    snap = s.reset()
    assert snap["values"]["edge_threshold"] == 0.65
    assert s.get("max_concurrent_trades") == 15
    assert len(calls) == 1


def test_get_returns_copy_of_set_lever():
    s = AiControlSurface()
    got = s.get("symbols")
    got.append("MUTATED")
    assert "MUTATED" not in s.get("symbols")


def test_daily_loss_cap_max_is_inf():
    s = AiControlSurface()
    snap = s.snapshot()
    assert math.isinf(snap["bounds"]["daily_loss_cap_usd"]["max"])
