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


# ---------------------------------------------------------------------------
# Max Favorable Excursion + early-banking analysis (owner "bank big winners")
# ---------------------------------------------------------------------------
def test_mfe_recorded_on_a_winner(tmp_path):
    # LONG runs to 1.1030 (peak) then closes at TP 1.1020 — MFE must exceed exit.
    candles = [
        _candle(1, high=1.1030, low=1.1002),   # peak 1.1030
        _candle(2, high=1.1021, low=1.1002),   # touches TP 1.1020
    ]
    _run(tmp_path, [_attempt(201, tp=1.1020)], candles)
    rec = load_paper_outcome_history(tmp_path / "paper-outcomes.json")["history_records"][0]
    assert rec["mfe_price"] == 1.1030
    assert rec["mfe_pnl"] > rec["profit"]  # it was worth more at the peak than at close
    assert 0.0 < rec["captured_fraction_of_peak"] < 1.0  # gave some back
    assert rec["bars_to_peak"] == 1


def test_early_banking_analysis_prefers_banking_when_giveback_is_large(tmp_path):
    from cas_forex.paper_outcome_sim import build_early_banking_analysis

    # Build a set of winners that each ran far past their TP before closing at TP
    # (big give-back): peak ~1.1050, TP 1.1010. Early banking near the peak should
    # model a higher net than holding to TP.
    attempts = [_attempt(300 + i, tp=1.1010) for i in range(25)]
    candles = [_candle(1, high=1.1050, low=1.1002), _candle(2, high=1.1011, low=1.1002)]
    _run(tmp_path, attempts, candles)
    analysis = build_early_banking_analysis(ledger_path=tmp_path / "paper-outcomes.json", min_trades=10)
    assert analysis["enough_data"] is True
    assert analysis["resolved_trades_with_mfe"] == 25
    # Peak was worth far more than the TP close, so the best banking policy beats hold.
    assert analysis["best_policy"]["modeled_net_pnl"] > analysis["actual_net_pnl_hold_to_sl_tp"]
    assert analysis["avg_captured_fraction_of_peak"] < 0.6  # big give-back


def test_early_banking_never_rescues_a_loser(tmp_path):
    from cas_forex.paper_outcome_sim import build_early_banking_analysis

    # A pure loser (hits SL, never went favorable) must keep its loss under every
    # banking policy — early banking only ever changes WINNERS.
    candles = [_candle(1, high=1.1001, low=1.0989)]  # straight to SL, no favorable move
    _run(tmp_path, [_attempt(400, sl=1.0990)], candles)
    analysis = build_early_banking_analysis(ledger_path=tmp_path / "paper-outcomes.json", min_trades=1)
    for policy in analysis["policies"]:
        assert policy["modeled_net_pnl"] == analysis["actual_net_pnl_hold_to_sl_tp"]
        assert policy["trades_banked_early"] == 0


# ---------------------------------------------------------------------------
# Trailing-stop simulation (the implementable "bank winners early")
# ---------------------------------------------------------------------------
from cas_forex.paper_outcome_sim import simulate_trailing_stop, _candle_rows


def _attempt_obj(direction="LONG", entry=1.1000, sl=1.0990, tp=1.1100, lots=0.10, symbol="EUR/USD"):
    # A resolvable attempt as the simulator's internal dict (post-_eligible).
    return {
        "broker_ticket": "T", "symbol": symbol, "direction": direction,
        "entry": entry, "stop_loss": sl, "take_profit": tp, "lots": lots,
        "open_time": T0, "decision_ref": "d", "order_id": "o",
    }


def test_trailing_stop_locks_in_profit_on_pullback(tmp_path):
    # LONG runs up to 1.1050 (peak) then pulls back. A 0.5 trail locks in at
    # entry + 0.5*(peak-entry). With peak 1.1050, lock ≈ 1.1025. TP is 1.1100
    # (never hit). Trade should exit near the trailing level, in PROFIT — far
    # better than round-tripping back to the original SL.
    att = _attempt_obj(tp=1.1100)
    candles = _candle_rows([
        _candle(1, high=1.1030, low=1.1005),   # peak 1.1030 set (for next bar)
        _candle(2, high=1.1050, low=1.1028),   # peak 1.1050 (trail from prev peak 1.1030 => lock 1.1015, low 1.1028 doesn't hit)
        _candle(3, high=1.1040, low=1.1010),   # trail now from peak 1.1050 => lock 1.1025; low 1.1010 <= 1.1025 => exit
    ])
    pnl = simulate_trailing_stop(att, candles, trail_fraction=0.5)
    assert pnl is not None and pnl > 0  # banked a profit, not a round-trip loss


def test_trailing_stop_never_below_original_stop(tmp_path):
    # A trade that goes straight to the original SL exits there (trail can't be
    # worse than the original stop) — a loser stays a loser.
    att = _attempt_obj(sl=1.0990)
    candles = _candle_rows([_candle(1, high=1.1002, low=1.0989)])  # straight to SL
    pnl = simulate_trailing_stop(att, candles, trail_fraction=0.5)
    assert pnl is not None and pnl < 0


def test_trailing_stop_no_intrabar_lookahead(tmp_path):
    # In the SAME bar the price both sets a new high AND dips: the trailing level
    # must be based on the PRIOR bar's peak, so a first favorable bar cannot lock
    # in a level it only reached mid-bar. Here bar 1 is the first favorable move
    # (peak starts at entry), so its low cannot trigger a profit-locking trail.
    att = _attempt_obj(entry=1.1000, sl=1.0990, tp=1.1100)
    candles = _candle_rows([_candle(1, high=1.1050, low=1.0995)])  # big range, first bar
    pnl = simulate_trailing_stop(att, candles, trail_fraction=0.5)
    # Trail for bar 1 is based on peak=entry => lock=entry+0.5*0=entry, clamped to
    # orig SL 1.0990; low 1.0995 does not hit 1.0990 => not resolved this bar.
    assert pnl is None


def test_trailing_stop_analysis_aggregates_stored_values(tmp_path):
    from cas_forex.paper_outcome_sim import build_trailing_stop_analysis

    # Resolve real records (which now store trailing_pnl_by_fraction), then the
    # analysis must aggregate them and compare against actual hold-to-SL/TP net.
    attempts = [_attempt(500 + i, sl=1.0990, tp=1.1100) for i in range(22)]
    # The classic give-back: each trade runs to 1.1060, then round-trips all the
    # way back to the original SL (a LOSS if held). A trailing stop would have
    # banked profit near the peak instead — the whole point.
    candles = [
        _candle(1, high=1.1030, low=1.1005),
        _candle(2, high=1.1060, low=1.1028),
        _candle(3, high=1.1010, low=1.0985),  # pulls back through the trail AND the SL
    ]
    resolve_paper_outcomes(
        attempts=attempts, candles_by_symbol={"EUR/USD": candles},
        ledger_path=tmp_path / "paper-outcomes.json",
    )
    analysis = build_trailing_stop_analysis(ledger_path=tmp_path / "paper-outcomes.json", min_trades=10)
    assert analysis["enough_data"] is True
    assert analysis["resolved_trades_with_trailing"] == 22
    assert analysis["best_policy"] is not None
    # Held to SL/TP these are losers; a trailing stop banks the run — so the best
    # trailing policy must beat holding.
    assert analysis["best_policy"]["delta_vs_hold"] > 0
    assert "IMPLEMENTABLE" in analysis["note"]
