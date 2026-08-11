"""Tests for the WASTE learning-outcomes engine (learn-from-mistakes ledger).

Unlike the promotion-grade outcome binding (PASS-token edges only), this binds
EVERY closed paper trade — including the gloves-off learning trades that carry
no edge token — so the AI operator can see what is actually winning/losing on
paper. Proven here with injected cycles/attempts/history so it works the moment
real realized outcomes flow.
"""

from __future__ import annotations

from cas_forex.waste_direction_outcome_binding import build_waste_learning_outcomes


def _cycle(
    decision_ref,
    symbol,
    direction,
    profile,
    edge_status="NO_TRADE_NULL_FAILED",
    has_token=False,
    timeframe="M1",
):
    return {
        "cycle_id": f"cyc-{decision_ref}",
        "decision": "EXECUTE",
        "candidate": {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "decision_ref": decision_ref,
            "directional_hypothesis": {"profile": profile},
        },
        "edge": {"status": edge_status, "has_edge_token": has_token},
        "execute_result": {"order_id": f"waste-{decision_ref}", "dispatched_to_bridge": True},
    }


def _attempt(
    decision_ref,
    ticket,
    executed=True,
    volume=0.01,
    admission_risk_usd=1.0,
):
    row = {
        "decision_ref": decision_ref,
        "order_id": f"waste-{decision_ref}",
        "executed": executed,
        "status": "ATTEMPT_RECORDED",
        "mode": "PAPER",
        "volume": volume,
        "proposed_intent": {"lots": volume},
        "outcome": {"broker_ticket": ticket},
    }
    if admission_risk_usd is not None:
        row["pre_trade_estimate"] = {
            "entry_price": 100.0,
            "stop_loss": 99.0,
            "lots": volume,
            "risk_at_stop_usd": admission_risk_usd,
            "unit_value_source": "broker.trade_tick_value/trade_tick_size",
            "broker_unit_value_per_lot_usd": admission_risk_usd / volume,
            "broker_contract_constraints": {
                "tick_size": 0.01,
                "tick_value": admission_risk_usd / volume / 100.0,
                "tick_value_loss": admission_risk_usd / volume / 100.0,
            },
        }
    return row


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


def test_group_ranking_prefers_after_cost_growth_over_high_win_rate():
    high_win_loser = [1.0, 1.0, 1.0, 1.0, -10.0]
    lower_win_grower = [5.0, 5.0, -1.0, -1.0, -1.0]
    rows = [
        (f"proxy-{idx}", "NAS100", "LONG", "high_win_proxy", pnl)
        for idx, pnl in enumerate(high_win_loser)
    ] + [
        (f"growth-{idx}", "EUR/USD", "LONG", "after_cost_growth", pnl)
        for idx, pnl in enumerate(lower_win_grower)
    ]
    cycles = [_cycle(ref, symbol, direction, profile) for ref, symbol, direction, profile, _ in rows]
    attempts = [_attempt(ref, 12_000 + idx) for idx, (ref, *_rest) in enumerate(rows)]
    history = [
        _history(12_000 + idx, symbol, direction, pnl)
        for idx, (_ref, symbol, direction, _profile, pnl) in enumerate(rows)
    ]

    report = _run(cycles, attempts, history, min_samples_per_group=5)

    assert report["ranking_basis"] == (
        "after_cost_expectancy_r_then_per_1_lot_then_raw_expectancy_then_net_pnl"
    )
    assert report["best_groups"][0]["profile"] == "after_cost_growth"
    assert report["best_groups"][0]["win_rate"] == 0.4
    assert report["best_groups"][0]["net_pnl"] == 7.0
    assert report["worst_groups"][0]["profile"] == "high_win_proxy"
    assert report["worst_groups"][0]["win_rate"] == 0.8
    assert report["worst_groups"][0]["net_pnl"] == -6.0


def test_group_ranking_removes_historical_lot_size_as_false_edge():
    rows = [
        (f"large-{idx}", "NAS100", "large_lot_weak_edge", 1.0, 1.0)
        for idx in range(4)
    ] + [
        (f"small-{idx}", "EUR/USD", "small_lot_strong_edge", 0.2, 0.01)
        for idx in range(4)
    ]
    cycles = [
        _cycle(ref, symbol, "LONG", profile)
        for ref, symbol, profile, _pnl, _lots in rows
    ]
    attempts = [
        _attempt(ref, 14_000 + idx, volume=lots, admission_risk_usd=None)
        for idx, (ref, _symbol, _profile, _pnl, lots) in enumerate(rows)
    ]
    history = [
        _history(14_000 + idx, symbol, "LONG", pnl)
        for idx, (_ref, symbol, _profile, pnl, _lots) in enumerate(rows)
    ]

    report = _run(cycles, attempts, history, min_samples_per_group=4)

    assert report["best_groups"][0]["profile"] == "small_lot_strong_edge"
    assert report["best_groups"][0]["after_cost_expectancy"] == 0.2
    assert report["best_groups"][0]["after_cost_expectancy_per_1_lot_usd"] == 20.0
    assert report["best_groups"][1]["profile"] == "large_lot_weak_edge"
    assert report["best_groups"][1]["after_cost_expectancy"] == 1.0
    assert report["best_groups"][1]["after_cost_expectancy_per_1_lot_usd"] == 1.0
    assert report["group_stats"][0]["lot_normalized_evidence_complete"] is True


def test_group_ranking_prefers_after_cost_return_per_planned_risk_across_instruments():
    rows = [
        (f"large-contract-{idx}", "SPX500", "large_contract_weak_r", 4.0, 100.0)
        for idx in range(4)
    ] + [
        (f"efficient-{idx}", "EUR/USD", "small_dollar_strong_r", 1.0, 1.0)
        for idx in range(4)
    ]
    cycles = [
        _cycle(ref, symbol, "LONG", profile)
        for ref, symbol, profile, _pnl, _risk in rows
    ]
    attempts = [
        _attempt(ref, 15_000 + idx, admission_risk_usd=risk)
        for idx, (ref, _symbol, _profile, _pnl, risk) in enumerate(rows)
    ]
    history = [
        _history(15_000 + idx, symbol, "LONG", pnl)
        for idx, (_ref, symbol, _profile, pnl, _risk) in enumerate(rows)
    ]

    report = _run(cycles, attempts, history, min_samples_per_group=4)

    assert report["best_groups"][0]["profile"] == "small_dollar_strong_r"
    assert report["best_groups"][0]["after_cost_expectancy_r"] == 1.0
    assert report["best_groups"][1]["profile"] == "large_contract_weak_r"
    assert report["best_groups"][1]["after_cost_expectancy_r"] == 0.04
    assert report["overall"]["risk_normalized_evidence_complete"] is True


def test_old_stored_spx_risk_is_recomputed_from_broker_tick_contract():
    attempt = _attempt("spx-old-risk", 16_001, volume=0.01, admission_risk_usd=None)
    attempt["pre_trade_estimate"] = {
        "entry_price": 7549.45,
        "stop_loss": 7554.87,
        "lots": 0.01,
        "risk_at_stop_usd": 0.05,
        "broker_contract_constraints": {
            "tick_size": 0.01,
            "tick_value": 1.0,
        },
    }
    report = _run(
        [_cycle("spx-old-risk", "SPX500", "SHORT", "broker-candle")],
        [attempt],
        [_history(16_001, "SPX500", "SHORT", -6.73)],
        min_samples_per_group=1,
    )

    row = report["sample_bound_rows"][0]
    assert row["admission_stop_risk_usd"] == 5.42
    assert row["risk_recomputed_from_broker_contract"] is True
    assert row["stored_pre_trade_risk_mismatch_detected"] is True
    assert row["stored_pre_trade_risk_ratio_to_recomputed"] == 0.009225
    assert row["realized_after_cost_r_multiple"] == -1.241697
    assert report["overall"]["stored_pre_trade_risk_mismatch_count"] == 1


def test_exact_mt5_stop_fill_reconstructs_missing_admission_risk():
    attempt = _attempt(
        "legacy-exact-stop",
        16_002,
        volume=0.01,
        admission_risk_usd=None,
    )
    attempt["pre_trade_estimate"] = {
        "entry_price": 29749.45,
        "stop_loss": 29777.83,
        "lots": 0.01,
    }
    history = _history(16_002, "NAS100", "SHORT", -28.43)
    history.update(
        {
            "gross_profit": -28.38,
            "commission": -0.05,
            "open_price": 29749.45,
            "close_price": 29777.83,
            "close_reason": "MT5_HISTORY_CLOSE:[sl 29777.83]",
        }
    )

    report = _run(
        [_cycle("legacy-exact-stop", "NAS100", "SHORT", "range_fade")],
        [attempt],
        [history],
        min_samples_per_group=1,
    )

    row = report["sample_bound_rows"][0]
    assert row["admission_stop_risk_usd"] == 28.38
    assert row["admission_risk_source"] == (
        "RECONSTRUCTED_EXACT_MT5_STOP_LOSS_FILL"
    )
    assert row["exact_mt5_stop_fill_observed"] is True
    assert row["risk_reconstructed_from_exact_mt5_stop_fill"] is True
    assert (
        row["legacy_missing_admission_risk_repaired_from_exact_mt5_stop_fill"]
        is True
    )
    assert row["risk_recomputed_from_broker_contract"] is False
    assert row["realized_after_cost_r_multiple"] == -1.001762
    assert row["exact_mt5_stop_fill_evidence"]["close_matches_intended_stop"] is True
    assert report["overall"]["risk_normalized_evidence_complete"] is True
    assert report["overall"]["exact_mt5_stop_fill_risk_reconstruction_count"] == 1
    assert report["overall"]["exact_mt5_stop_fill_risk_reconstruction_tickets"] == [
        "16002"
    ]
    assert report["overall"]["legacy_exact_mt5_stop_fill_risk_repair_count"] == 1
    assert report["overall"]["legacy_exact_mt5_stop_fill_risk_repair_tickets"] == [
        "16002"
    ]


def test_non_exact_or_non_mt5_stop_fill_cannot_reconstruct_admission_risk():
    cases = [
        ("PAPER_MT5", 29778.0),
        ("PAPER_SIM", 29777.83),
    ]
    for idx, (broker_mode, close_price) in enumerate(cases):
        decision_ref = f"legacy-untrusted-stop-{idx}"
        attempt = _attempt(
            decision_ref,
            16_100 + idx,
            volume=0.01,
            admission_risk_usd=None,
        )
        attempt["pre_trade_estimate"] = {
            "entry_price": 29749.45,
            "stop_loss": 29777.83,
            "lots": 0.01,
        }
        history = _history(16_100 + idx, "NAS100", "SHORT", -28.43)
        history.update(
            {
                "broker_mode": broker_mode,
                "gross_profit": -28.38,
                "open_price": 29749.45,
                "close_price": close_price,
                "close_reason": "MT5_HISTORY_CLOSE:[sl 29777.83]",
            }
        )

        report = _run(
            [_cycle(decision_ref, "NAS100", "SHORT", "range_fade")],
            [attempt],
            [history],
            min_samples_per_group=1,
        )

        row = report["sample_bound_rows"][0]
        assert row["admission_stop_risk_usd"] is None
        assert row["exact_mt5_stop_fill_observed"] is False
        assert row["risk_reconstructed_from_exact_mt5_stop_fill"] is False
        assert (
            row["legacy_missing_admission_risk_repaired_from_exact_mt5_stop_fill"]
            is False
        )
        assert row["realized_after_cost_r_multiple"] is None
        assert report["overall"]["risk_normalized_evidence_complete"] is False
        assert report["overall"]["exact_mt5_stop_fill_risk_reconstruction_count"] == 0
        assert report["overall"]["exact_mt5_stop_fill_risk_reconstruction_tickets"] == []
        assert report["overall"]["legacy_exact_mt5_stop_fill_risk_repair_count"] == 0
        assert report["overall"]["legacy_exact_mt5_stop_fill_risk_repair_tickets"] == []


def test_timeframes_cannot_pool_into_false_group_readiness():
    rows = [
        ("m1-a", "M1", 1.0),
        ("m1-b", "M1", 1.0),
        ("h1-a", "H1", 1.0),
        ("h1-b", "H1", 1.0),
    ]
    cycles = [
        _cycle(ref, "EUR/USD", "LONG", "shared_profile", timeframe=timeframe)
        for ref, timeframe, _ in rows
    ]
    attempts = [_attempt(ref, 13_000 + idx) for idx, (ref, *_rest) in enumerate(rows)]
    history = [
        _history(13_000 + idx, "EUR/USD", "LONG", pnl)
        for idx, (_ref, _timeframe, pnl) in enumerate(rows)
    ]

    report = _run(cycles, attempts, history, min_samples_per_group=4)

    assert report["overall_sample_ready"] is True
    assert report["group_learning_ready"] is False
    assert report["grouping_basis"] == "symbol_x_timeframe_x_direction_x_profile"
    assert {group["timeframe"] for group in report["group_stats"]} == {"M1", "H1"}


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


def test_overall_sample_count_does_not_fake_per_group_learning_readiness():
    rows = [
        ("a", "EUR/USD", "LONG", "trend", 1.0),
        ("b", "GBP/USD", "LONG", "breakout", -1.0),
        ("c", "USD/JPY", "SHORT", "range", 1.0),
        ("d", "NAS100", "SHORT", "momentum", -1.0),
    ]
    cycles = [_cycle(ref, symbol, direction, profile) for ref, symbol, direction, profile, _ in rows]
    attempts = [_attempt(ref, 10_000 + idx) for idx, (ref, *_rest) in enumerate(rows)]
    history = [
        _history(10_000 + idx, symbol, direction, profit)
        for idx, (_ref, symbol, direction, _profile, profit) in enumerate(rows)
    ]

    report = _run(cycles, attempts, history, min_samples_per_group=4)

    assert report["bound_trade_count"] == 4
    assert report["overall_sample_ready"] is True
    assert report["group_learning_ready"] is False
    assert report["learning_ready"] is False
    assert report["learning_ready_group_count"] == 0
    assert "no symbol x timeframe x direction x profile group" in report["next_action"]


def test_group_learning_ready_requires_threshold_inside_one_group():
    cycles = [_cycle(f"same-{idx}", "SPX500", "SHORT", "trend") for idx in range(4)]
    attempts = [_attempt(f"same-{idx}", 11_000 + idx) for idx in range(4)]
    history = [
        _history(11_000 + idx, "SPX500", "SHORT", 2.0 if idx == 0 else -1.0)
        for idx in range(4)
    ]

    report = _run(cycles, attempts, history, min_samples_per_group=4)

    assert report["overall_sample_ready"] is True
    assert report["group_learning_ready"] is True
    assert report["learning_ready"] is True
    assert report["learning_ready_group_count"] == 1
    assert report["group_stats"][0]["trades"] == 4


def test_operator_order_attempt_binds_without_legacy_waste_cycle():
    attempt = _attempt("operator-spx", 45944826)
    attempt.update(
        {
            "attempt_id": "attempt-operator-spx",
            "symbol": "SPX500",
            "direction": "SHORT",
            "bridge_name": "MT5Bridge",
            "execution_provenance": {
                "initiator": {"kind": "AI_AUTOMATION", "ai_action": "OPEN_LIVE_CANDLE_LEARNING"},
                "order_shape": {
                    "decision_ref": "operator-spx",
                    "order_id": "waste-operator-spx",
                    "symbol": "SPX500",
                    "direction": "SHORT",
                },
                "strategy": {
                    "ai_action": "OPEN_LIVE_CANDLE_LEARNING",
                    "strategy_id": "live_candle_broker-candle_h1",
                },
            },
        }
    )
    history = [_history(45944826, "SPX500", "sell", -6.73)]

    r = _run([], [attempt], history, min_samples_per_group=1)

    assert r["bound_trade_count"] == 1
    assert r["overall"]["losses"] == 1
    assert r["sample_bound_rows"][0]["origin_source"] == "ORDER_ATTEMPT_LEDGER"
    assert r["sample_bound_rows"][0]["attempt_id"] == "attempt-operator-spx"


def test_never_touches_money_or_live():
    r = _run([], [], [])
    assert r["broker_touched"] is False
    assert r["money_moved"] is False
    assert r["edge_token_minted"] is False
    assert r["owner_accept_created"] is False
    assert "does not place orders" in r["claim_boundary"]
