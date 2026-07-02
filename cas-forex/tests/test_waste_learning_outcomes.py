"""Tests for the WASTE learning-outcomes engine (learn-from-mistakes ledger).

Unlike the promotion-grade outcome binding (PASS-token edges only), this binds
EVERY closed paper trade — including the gloves-off learning trades that carry
no edge token — so the AI operator can see what is actually winning/losing on
paper. Proven here with injected cycles/attempts/history so it works the moment
real realized outcomes flow.
"""

from __future__ import annotations

from cas_forex.waste_direction_outcome_binding import build_waste_learning_outcomes


def _cycle(decision_ref, symbol, direction, profile, edge_status="NO_TRADE_NULL_FAILED", has_token=False):
    return {
        "cycle_id": f"cyc-{decision_ref}",
        "decision": "EXECUTE",
        "candidate": {
            "symbol": symbol,
            "timeframe": "M1",
            "direction": direction,
            "decision_ref": decision_ref,
            "directional_hypothesis": {"profile": profile},
        },
        "edge": {"status": edge_status, "has_edge_token": has_token},
        "execute_result": {"order_id": f"waste-{decision_ref}", "dispatched_to_bridge": True},
    }


def _attempt(decision_ref, ticket, executed=True):
    return {
        "decision_ref": decision_ref,
        "order_id": f"waste-{decision_ref}",
        "executed": executed,
        "status": "ATTEMPT_RECORDED",
        "mode": "PAPER",
        "outcome": {"broker_ticket": ticket},
    }


def _history(ticket, symbol, direction, profit):
    return {
        "broker_ticket": str(ticket),
        "symbol": symbol,
        "direction": direction,
        "broker_mode": "PAPER_MT5",
        "profit": profit,
        "gross_profit": profit,
        "commission": 0.0,
        "swap": 0.0,
    }


def _run(cycles, attempts, history_records, **kw):
    return build_waste_learning_outcomes(
        cycles=cycles,
        attempts=attempts,
        history_report={"ingest_status": "OK", "history_records": history_records},
        **kw,
    )


def test_binds_learning_trades_not_just_pass_edges():
    # Two NON-PASS learning trades (no edge token) must still bind + aggregate.
    cycles = [
        _cycle("d1", "NAS100", "SHORT", "trend"),
        _cycle("d2", "NAS100", "SHORT", "trend"),
    ]
    attempts = [_attempt("d1", 5001), _attempt("d2", 5002)]
    history = [_history(5001, "NAS100", "SHORT", -3.0), _history(5002, "NAS100", "SHORT", -2.0)]
    r = _run(cycles, attempts, history, min_samples_per_group=2)
    assert r["bound_trade_count"] == 2
    assert r["overall"]["losses"] == 2
    assert r["overall"]["net_pnl"] == -5.0


def test_worst_group_surfaces_a_losing_symbol_direction():
    # A losing SHORT NAS100 group vs a winning LONG EUR/USD group.
    cycles = (
        [_cycle(f"s{i}", "NAS100", "SHORT", "trend") for i in range(5)]
        + [_cycle(f"l{i}", "EUR/USD", "LONG", "range") for i in range(5)]
    )
    attempts = [_attempt(f"s{i}", 6000 + i) for i in range(5)] + [_attempt(f"l{i}", 7000 + i) for i in range(5)]
    history = (
        [_history(6000 + i, "NAS100", "SHORT", -4.0) for i in range(5)]
        + [_history(7000 + i, "EUR/USD", "LONG", 3.0) for i in range(5)]
    )
    r = _run(cycles, attempts, history, min_samples_per_group=3)
    worst = r["worst_groups"][0]
    best = r["best_groups"][0]
    assert worst["symbol"] == "NAS100" and worst["direction"] == "SHORT"
    assert worst["win_rate"] == 0.0 and worst["net_pnl"] == -20.0
    assert best["symbol"] == "EUR/USD" and best["direction"] == "LONG"
    assert best["win_rate"] == 1.0


def test_unclosed_trades_do_not_bind():
    # A dispatched trade with no matching closed history stays unbound.
    cycles = [_cycle("d1", "GBP/USD", "LONG", "trend")]
    attempts = [_attempt("d1", 8001)]
    r = _run(cycles, attempts, history_records=[])  # no closed history
    assert r["bound_trade_count"] == 0
    assert r["learning_ready"] is False


def test_pass_edge_trades_also_bind():
    # A genuine PASS-token edge closes too and is counted with the learning set.
    cycles = [_cycle("p1", "US30", "LONG", "trend", edge_status="PASS", has_token=True)]
    attempts = [_attempt("p1", 9001)]
    history = [_history(9001, "US30", "LONG", 5.5)]
    r = _run(cycles, attempts, history, min_samples_per_group=1)
    assert r["bound_trade_count"] == 1
    assert r["overall"]["wins"] == 1
    assert r["overall"]["net_pnl"] == 5.5


def test_never_touches_money_or_live():
    r = _run([], [], [])
    assert r["broker_touched"] is False
    assert r["money_moved"] is False
    assert r["edge_token_minted"] is False
    assert r["owner_accept_created"] is False
    assert "does not place orders" in r["claim_boundary"]
