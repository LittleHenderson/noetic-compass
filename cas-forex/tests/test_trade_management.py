"""Tests for cas_forex.trade_management — sizing math + breakeven principal-lock.

Uses real instrument economics (EUR/USD pip = $10/lot; NAS100 point = $1/lot)
so the sizing math is checked against true broker arithmetic, not a mock.
"""

from __future__ import annotations

import pytest

from cas_forex.trade_management import (
    breakeven_lock,
    expected_loss_usd,
    position_size,
    value_per_price_unit_per_lot,
)


# --- value_per_price_unit_per_lot -----------------------------------------

def test_value_per_price_unit_fx_eurusd():
    # 1 pip = 0.0001, $10/lot/pip -> $100,000/lot per 1.0 of raw price.
    assert value_per_price_unit_per_lot("EUR/USD", 1.10) == pytest.approx(100_000.0)


def test_value_per_price_unit_index_nas100():
    # 1 point = 1.0 raw price, $1/lot/point -> $1/lot per 1.0 of raw price.
    assert value_per_price_unit_per_lot("NAS100", 19_500.0) == pytest.approx(1.0)


# --- position_size: FX pair ------------------------------------------------

def test_position_size_eurusd_basic():
    # entry 1.1000, stop 1.0950 -> 50-pip (0.0050) stop. $10/pip/lot.
    # Risk $100 -> 100 / (0.0050 * 100_000) = 100 / 500 = 0.20 lots.
    lots = position_size(
        equity=5_000.0,
        risk_budget_usd=100.0,
        entry=1.1000,
        stop_loss=1.0950,
        symbol="EUR/USD",
    )
    assert lots == pytest.approx(0.20)


def test_position_size_eurusd_short_same_distance():
    # Direction-agnostic: distance is what matters, sign of stop offset does not.
    lots = position_size(
        equity=5_000.0,
        risk_budget_usd=100.0,
        entry=1.1000,
        stop_loss=1.1050,
        symbol="EUR/USD",
    )
    assert lots == pytest.approx(0.20)


# --- position_size: index --------------------------------------------------

def test_position_size_index_nas100():
    # entry 19500, stop 19400 -> 100-point distance. $1/point/lot.
    # Risk $200 -> 200 / (100 * 1) = 2.0 lots.
    lots = position_size(
        equity=10_000.0,
        risk_budget_usd=200.0,
        entry=19_500.0,
        stop_loss=19_400.0,
        symbol="NAS100",
    )
    assert lots == pytest.approx(2.0)


# --- guards ----------------------------------------------------------------

def test_position_size_zero_stop_distance_is_zero():
    assert position_size(5_000.0, 100.0, 1.1000, 1.1000, "EUR/USD") == 0.0


def test_position_size_non_positive_risk_or_equity_is_zero():
    assert position_size(5_000.0, 0.0, 1.10, 1.095, "EUR/USD") == 0.0
    assert position_size(5_000.0, -50.0, 1.10, 1.095, "EUR/USD") == 0.0
    assert position_size(0.0, 100.0, 1.10, 1.095, "EUR/USD") == 0.0


def test_position_size_never_negative():
    lots = position_size(5_000.0, 100.0, 1.10, 1.095, "EUR/USD")
    assert lots >= 0.0


def test_position_size_capped_by_max_lots():
    # Huge budget, tiny stop -> would size enormous; max_lots caps it.
    lots = position_size(
        equity=1_000_000.0,
        risk_budget_usd=1_000_000.0,
        entry=1.1000,
        stop_loss=1.0999,
        symbol="EUR/USD",
        max_lots=5.0,
    )
    assert lots == pytest.approx(5.0)


def test_position_size_floors_to_lot_step():
    # Choose inputs whose exact lot count is not on the 0.01 grid; result floors.
    lots = position_size(
        equity=5_000.0,
        risk_budget_usd=77.0,
        entry=1.1000,
        stop_loss=1.0950,
        symbol="EUR/USD",
    )
    # raw = 77 / 500 = 0.154 -> floored to 0.15
    assert lots == pytest.approx(0.15)
    # Floored size never risks MORE than the budget.
    assert expected_loss_usd(lots, 1.1000, 1.0950, "EUR/USD") <= 77.0 + 1e-9


# --- expected_loss_usd truthfulness ---------------------------------------

def test_expected_loss_matches_budget_when_on_grid():
    # 0.20 lots * 0.0050 * 100_000 = $100 — sizing was exact, loss equals budget.
    lots = position_size(5_000.0, 100.0, 1.1000, 1.0950, "EUR/USD")
    assert expected_loss_usd(lots, 1.1000, 1.0950, "EUR/USD") == pytest.approx(100.0)


def test_expected_loss_index():
    # 2.0 lots * 100 points * $1 = $200.
    assert expected_loss_usd(2.0, 19_500.0, 19_400.0, "NAS100") == pytest.approx(200.0)


def test_expected_loss_zero_for_zero_lots_or_zero_distance():
    assert expected_loss_usd(0.0, 1.10, 1.095, "EUR/USD") == 0.0
    assert expected_loss_usd(0.20, 1.10, 1.10, "EUR/USD") == 0.0


def test_expected_loss_non_negative():
    assert expected_loss_usd(0.20, 1.0950, 1.1000, "EUR/USD") >= 0.0


# --- breakeven_lock --------------------------------------------------------

def test_breakeven_long_triggers_at_1r():
    # entry 1.1000, stop 1.0950 -> R = 0.0050. +1R target price = 1.1050.
    entry, stop = 1.1000, 1.0950
    # Just below +1R: no lock yet.
    assert breakeven_lock(entry, 1.1049, "LONG", stop) is None
    # Exactly +1R: lock to entry.
    locked = breakeven_lock(entry, 1.1050, "LONG", stop)
    assert locked == pytest.approx(entry)
    # Beyond +1R: still locked to entry.
    assert breakeven_lock(entry, 1.1100, "LONG", stop) == pytest.approx(entry)


def test_breakeven_short_triggers_at_1r():
    # entry 1.1000, stop 1.1050 -> R = 0.0050. SHORT +1R target = 1.0950.
    entry, stop = 1.1000, 1.1050
    assert breakeven_lock(entry, 1.0951, "SHORT", stop) is None
    locked = breakeven_lock(entry, 1.0950, "SHORT", stop)
    assert locked == pytest.approx(entry)
    assert breakeven_lock(entry, 1.0900, "SHORT", stop) == pytest.approx(entry)


def test_breakeven_not_before_trigger_when_underwater():
    # Trade in the red -> never lock.
    assert breakeven_lock(1.1000, 1.0980, "LONG", 1.0950) is None
    assert breakeven_lock(1.1000, 1.1020, "SHORT", 1.1050) is None


def test_breakeven_custom_trigger_r():
    # Require +2R before locking.
    entry, stop = 1.1000, 1.0950  # R = 0.0050
    # +1R (1.1050) is not enough now.
    assert breakeven_lock(entry, 1.1050, "LONG", stop, lock_trigger_r=2.0) is None
    # +2R (1.1100) locks.
    assert breakeven_lock(entry, 1.1100, "LONG", stop, lock_trigger_r=2.0) == pytest.approx(entry)


def test_breakeven_zero_initial_risk_returns_none():
    assert breakeven_lock(1.1000, 1.1200, "LONG", 1.1000) is None


def test_breakeven_unknown_direction_returns_none():
    assert breakeven_lock(1.1000, 1.1100, "SIDEWAYS", 1.0950) is None


def test_breakeven_accepts_buy_sell_aliases():
    assert breakeven_lock(1.1000, 1.1050, "buy", 1.0950) == pytest.approx(1.1000)
    assert breakeven_lock(1.1000, 1.0950, "sell", 1.1050) == pytest.approx(1.1000)
