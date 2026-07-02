"""Null-discipline tests for the paper-outcome simulator.

A subtly-wrong P&L simulator fabricates fake edges, so every honesty rule is
proven here with hand-computed numbers on injected candles:
  * first-touch resolution (stop vs target, both directions)
  * ambiguous candle (spans both levels) resolves CONSERVATIVELY as a loss
  * full spread cost charged on every trade (winners shrink, losers grow)
  * exact P&L via the SAME money math sizing uses (value_per_price_unit_per_lot)
  * unresolved trades produce NO record; idempotency per ticket
  * real-money attempts are never eligible
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cas_forex.paper_outcome_sim import (
    load_paper_outcome_history,
    resolve_paper_outcomes,
)
from cas_forex.trade_management import value_per_price_unit_per_lot
from cas_forex.instruments import price_unit_size

T0 = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)


def _candle(minutes, high, low, close=None):
    return {
        "timestamp": (T0 + timedelta(minutes=minutes)).isoformat(),
        "high": high,
        "low": low,
        "close": close if close is not None else (high + low) / 2,
    }


def _attempt(ticket, *, direction="LONG", entry=1.1000, sl=1.0990, tp=1.1020, lots=0.10, symbol="EUR/USD", mode="PAPER"):
    return {
        "executed": True,
        "mode": mode,
        "created_at": T0.isoformat(),
        "decision_ref": f"d-{ticket}",
        "order_id": f"waste-d-{ticket}",
        "symbol": symbol,
        "direction": direction,
        "volume": lots,
        "order": {
            "symbol": symbol,
            "direction": direction,
            "price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "volume": lots,
        },
        "outcome": {"broker_ticket": ticket, "filled_price": entry, "broker_mode": "PAPER_MT5"},
    }


def _run(tmp_path, attempts, candles, **kw):
    return resolve_paper_outcomes(
        attempts=attempts,
        candles_by_symbol={"EUR/USD": candles},
        ledger_path=tmp_path / "paper-outcomes.json",
        **kw,
    )


def _expected_pnl(symbol, entry, exit_price, direction, lots, spread_units=1.5):
    sign = 1.0 if direction == "LONG" else -1.0
    vpu = value_per_price_unit_per_lot(symbol, entry)
    gross = (exit_price - entry) * sign * vpu * lots
    cost = spread_units * price_unit_size(symbol) * vpu * lots
    return round(gross - cost, 6)


def test_long_take_profit_first_touch_exact_pnl(tmp_path):
    candles = [
        _candle(1, high=1.1005, low=1.0998),   # touches nothing
        _candle(2, high=1.1021, low=1.1002),   # touches TP (1.1020), not SL
        _candle(3, high=1.1030, low=1.0980),   # would touch both — must not matter
    ]
    report = _run(tmp_path, [_attempt(101)], candles)
    assert report["newly_resolved"] == 1
    rec = load_paper_outcome_history(tmp_path / "paper-outcomes.json")["history_records"][0]
    assert rec["close_reason"] == "TAKE_PROFIT"
    assert rec["exit"] == 1.1020
    # Exact P&L: 20-pip win on 0.10 lots minus 1.5-pip spread cost.
    assert rec["profit"] == _expected_pnl("EUR/USD", 1.1000, 1.1020, "LONG", 0.10)
    assert rec["profit"] > 0
    assert rec["broker_mode"] == "PAPER_SIM"
    assert rec["outcome_source"] == "paper_simulated_first_touch"


def test_long_stop_loss_first_touch(tmp_path):
    candles = [
        _candle(1, high=1.1005, low=1.0989),   # touches SL (1.0990)
        _candle(2, high=1.1030, low=1.1010),   # later TP touch must not matter
    ]
    report = _run(tmp_path, [_attempt(102)], candles)
    assert report["newly_resolved_losses"] == 1
    rec = load_paper_outcome_history(tmp_path / "paper-outcomes.json")["history_records"][0]
    assert rec["close_reason"] == "STOP_LOSS"
    assert rec["profit"] == _expected_pnl("EUR/USD", 1.1000, 1.0990, "LONG", 0.10)
    assert rec["profit"] < 0


def test_ambiguous_candle_resolves_as_conservative_loss(tmp_path):
    # One candle spans BOTH the stop and the target: unknowable at M1 — must be
    # scored as a LOSS at the stop, never a win.
    candles = [_candle(1, high=1.1025, low=1.0985)]
    _run(tmp_path, [_attempt(103)], candles)
    rec = load_paper_outcome_history(tmp_path / "paper-outcomes.json")["history_records"][0]
    assert rec["close_reason"] == "AMBIGUOUS_CANDLE_CONSERVATIVE_SL"
    assert rec["exit"] == 1.0990
    assert rec["profit"] < 0


def test_short_direction_mirrors(tmp_path):
    # SHORT from 1.1000: SL above (1.1010), TP below (1.0980).
    att = _attempt(104, direction="SHORT", entry=1.1000, sl=1.1010, tp=1.0980)
    candles = [
        _candle(1, high=1.1005, low=1.0995),   # touches nothing
        _candle(2, high=1.1004, low=1.0979),   # touches TP for a short
    ]
    _run(tmp_path, [att], candles)
    rec = load_paper_outcome_history(tmp_path / "paper-outcomes.json")["history_records"][0]
    assert rec["close_reason"] == "TAKE_PROFIT"
    assert rec["profit"] == _expected_pnl("EUR/USD", 1.1000, 1.0980, "SHORT", 0.10)
    assert rec["profit"] > 0


def test_untouched_trade_stays_open_with_no_record(tmp_path):
    candles = [_candle(1, high=1.1005, low=1.0995), _candle(2, high=1.1008, low=1.0996)]
    report = _run(tmp_path, [_attempt(105)], candles)
    assert report["newly_resolved"] == 0
    assert report["still_open"] == 1
    assert load_paper_outcome_history(tmp_path / "paper-outcomes.json")["history_records"] == []


def test_idempotent_per_ticket(tmp_path):
    candles = [_candle(1, high=1.1021, low=1.1002)]
    first = _run(tmp_path, [_attempt(106)], candles)
    second = _run(tmp_path, [_attempt(106)], candles)
    assert first["newly_resolved"] == 1
    assert second["newly_resolved"] == 0
    assert second["already_resolved"] == 1
    assert len(load_paper_outcome_history(tmp_path / "paper-outcomes.json")["history_records"]) == 1


def test_candles_before_open_are_ignored(tmp_path):
    # A TP-touching candle BEFORE the open must not resolve the trade
    # (lookahead guard); only the post-open stop touch counts.
    pre_open = {
        "timestamp": (T0 - timedelta(minutes=5)).isoformat(),
        "high": 1.1050,
        "low": 1.1015,
        "close": 1.1020,
    }
    candles = [pre_open, _candle(1, high=1.1005, low=1.0989)]
    _run(tmp_path, [_attempt(107)], candles)
    rec = load_paper_outcome_history(tmp_path / "paper-outcomes.json")["history_records"][0]
    assert rec["close_reason"] == "STOP_LOSS"


def test_real_money_attempts_are_never_eligible(tmp_path):
    att = _attempt(108, mode="LIVE")
    att["outcome"]["broker_mode"] = "LIVE_MT5"
    report = _run(tmp_path, [att], [_candle(1, high=1.1021, low=1.1002)])
    assert report["eligible_attempts"] == 0
    assert report["newly_resolved"] == 0


def test_spread_cost_always_charged_even_on_wins(tmp_path):
    # A win's net must be strictly below its gross by the spread cost.
    candles = [_candle(1, high=1.1021, low=1.1002)]
    _run(tmp_path, [_attempt(109)], candles)
    rec = load_paper_outcome_history(tmp_path / "paper-outcomes.json")["history_records"][0]
    assert rec["profit"] < rec["gross_profit"]
    assert rec["commission"] < 0


def test_learning_engine_consumes_simulated_ledger(tmp_path):
    # End-to-end: resolve a trade, then feed the ledger into the learning engine
    # as its history report — the trade must bind and aggregate.
    from cas_forex.waste_direction_outcome_binding import build_waste_learning_outcomes

    candles = [_candle(1, high=1.1021, low=1.1002)]
    _run(tmp_path, [_attempt(110)], candles)
    ledger = load_paper_outcome_history(tmp_path / "paper-outcomes.json")
    cycles = [
        {
            "cycle_id": "cyc-110",
            "decision": "EXECUTE",
            "candidate": {
                "symbol": "EUR/USD",
                "timeframe": "M1",
                "direction": "LONG",
                "decision_ref": "d-110",
                "directional_hypothesis": {"profile": "trend"},
            },
            "edge": {"status": "NO_TRADE_NULL_FAILED", "has_edge_token": False},
            "execute_result": {"order_id": "waste-d-110"},
        }
    ]
    attempts = [
        {
            "decision_ref": "d-110",
            "order_id": "waste-d-110",
            "executed": True,
            "status": "ATTEMPT_RECORDED",
            "mode": "PAPER",
            "outcome": {"broker_ticket": "110"},
        }
    ]
    r = build_waste_learning_outcomes(
        cycles=cycles, attempts=attempts, history_report=ledger, min_samples_per_group=1
    )
    assert r["bound_trade_count"] == 1
    assert r["overall"]["wins"] == 1
