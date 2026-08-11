from pathlib import Path

from cas_forex.live_readiness import (
    NOT_READY_FOR_LIVE,
    PASSED,
    assert_live_readiness_boundary,
    build_live_readiness_report,
)


def _runtime_gates():
    return {
        "all_real_money_authorized": False,
        "decisions": {
            "live_trading": {
                "authorized": False,
                "status": "CURRENTLY NOT LICENSED",
                "missing_requirements": ["owner_enable_live_trading flag is ON"],
                "satisfied_requirements": [],
                "next_action": "Set live-trading owner flags and broker credentials.",
            },
            "broker_accept": {
                "authorized": False,
                "status": "CURRENTLY NOT LICENSED",
                "missing_requirements": ["live trading is authorized"],
                "satisfied_requirements": [],
                "next_action": "Authorize live trading first.",
            },
            "auto_deposit": {
                "authorized": False,
                "status": "CURRENTLY NOT LICENSED",
                "missing_requirements": ["payment provider configured (payment_provider set)"],
                "satisfied_requirements": [],
                "next_action": "Configure payment provider.",
            },
            "bank_card_movement": {
                "authorized": False,
                "status": "CURRENTLY NOT LICENSED",
                "missing_requirements": ["payment provider credentials present (payment_api_key)"],
                "satisfied_requirements": [],
                "next_action": "Configure payment credentials.",
            },
            "payout_automation": {
                "authorized": False,
                "status": "CURRENTLY NOT LICENSED",
                "missing_requirements": ["payout destination allowlisted"],
                "satisfied_requirements": [],
                "next_action": "Allowlist payout destination.",
            },
        },
    }


def _report_inputs():
    return {
        "ui_readiness": {
            "complete_bundle_days": 1,
            "min_daily_bundles_for_ui": 5,
            "completed_trading_days": 1,
            "chains_verified": {"paper_proof": True, "paper_decision": True, "paper_risk": True},
        },
        "daily_bundle": {"latest_proof": {"completed_trading_days": 1, "required_trading_days": 30, "passed": False}},
        "account_ledger": {
            "summary": {
                "owner_selected_initial_investment_usd": 5000,
                "requires_new_risk_review_for_selected_investment": False,
            }
        },
        "movement_stream": {
            "account_streams": [
                "balance",
                "equity",
                "realized_pnl",
                "floating_pnl",
                "swap",
                "commission",
                "broker_fees",
                "margin",
                "free_margin",
                "drawdown",
                "deposit",
                "withdrawal",
                "payout",
                "open_position_count",
            ],
            "market_streams": [
                "bid",
                "ask",
                "mid",
                "spread",
                "synthetic_candle",
                "atr",
                "sl_distance",
                "tp_distance",
                "floating_pnl",
                "margin_estimate",
                "market_open",
                "session",
                "source",
            ],
            "quotes": [{"symbol": "US30"}],
            "positions": [{"symbol": "US30"}],
            "price_source_status": "PROVIDER_ACTIVE",
            "market_data_provider_requested": True,
            "configured_market_data_provider": "Yahoo",
            "provider_usable_symbols": ["US30"],
        },
        "account_reconciliation": {
            "overall_status": "RECONCILIATION_FAILED",
            "checks_ok": 6,
            "checks_mismatch": 1,
            "checks_unverifiable": 0,
        },
        "backsolve": {"viable_scenarios": 0},
        "walk_forward": {"research_grade": "NOT_PROMOTED"},
        "mt5_receipt": {
            "receipt_validation_status": "BROKER_API_VERIFIED",
            "chain_verified": True,
            "account_snapshot": {"balance": 100000.0, "equity": 100000.0},
        },
        "mt5_probe_status": {"status": "BROKER_API_VERIFIED", "account_snapshot_present": True},
        "runtime_gates": _runtime_gates(),
        "authority_boundary": {
            "can_place_live_orders": False,
            "can_move_money": False,
            "live_trading_status": "CURRENTLY NOT LICENSED",
            "broker_accept_status": "CURRENTLY NOT LICENSED",
            "auto_deposit_status": "CURRENTLY NOT LICENSED",
            "debit_card_bank_movement_status": "CURRENTLY NOT LICENSED",
            "payout_automation_status": "CURRENTLY NOT LICENSED",
        },
        "adaptive": {
            "adaptive_compounding": {
                "latest_review": {
                    "decisions": [{"symbol": "US30"}],
                    "memory_snapshots": [{"symbol": "US30"}],
                }
            }
        },
    }


def test_live_readiness_rolls_operability_gates_into_plain_english_report():
    report = build_live_readiness_report(**_report_inputs())

    assert report.report_kind == "cas_forex_live_readiness"
    assert report.overall_status == NOT_READY_FOR_LIVE
    assert report.live_money_authorized is False
    assert report.payment_movement_authorized is False
    by_id = {check.gate_id: check for check in report.checks}
    assert by_id["owner_initial_investment"].status == PASSED
    assert by_id["account_movement_tracking"].status == PASSED
    assert by_id["market_movement_tracking"].status == PASSED
    assert by_id["movement_price_source_truth"].status == PASSED
    assert by_id["broker_demo_receipt"].status == PASSED
    assert by_id["broker_account_snapshot"].status == PASSED
    assert by_id["account_reconciliation"].status == "MISMATCH"
    assert by_id["paper_proof_maturity"].status == "OPEN"
    assert by_id["trading_edge"].status == "OPEN"
    assert by_id["live_trading"].status == "CURRENTLY NOT LICENSED"
    assert report.next_actions
    assert_live_readiness_boundary(report)


def test_live_readiness_exposes_missing_market_streams_as_open_gap():
    inputs = _report_inputs()
    inputs["movement_stream"] = {**inputs["movement_stream"], "market_streams": ["bid"], "quotes": [], "positions": []}
    report = build_live_readiness_report(**inputs)

    by_id = {check.gate_id: check for check in report.checks}
    assert by_id["market_movement_tracking"].status == "OPEN"
    assert by_id["market_movement_tracking"].blocks_live is True


def test_live_readiness_flags_static_simulation_as_live_blocking_price_truth_gap():
    inputs = _report_inputs()
    inputs["movement_stream"] = {
        **inputs["movement_stream"],
        "price_source_status": "STATIC_SIMULATION_FALLBACK",
        "provider_usable_symbols": [],
        "static_fallback_symbols": ["US30"],
        "provider_stale_symbols": ["US30"],
        "provider_freshness_max_age_seconds": 900,
        "position_feed_label": "SIM PROOF",
        "position_feed_detail": (
            "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
            "Static simulator fallback is active for 1/1 row(s), so prices and floating P&L can remain at entry "
            "until usable provider or MT5 quotes arrive. Requested provider: Yahoo. Static fallback symbols: US30. "
            "Stale provider/MT5 snapshots were rejected for: US30 (max age 900s)."
        ),
    }
    report = build_live_readiness_report(**inputs)

    by_id = {check.gate_id: check for check in report.checks}
    assert by_id["movement_price_source_truth"].status == "OPEN"
    assert by_id["movement_price_source_truth"].blocks_live is True
    assert "price_source_status=STATIC_SIMULATION_FALLBACK" in by_id["movement_price_source_truth"].evidence
    assert "Stale provider/MT5 snapshots were rejected for: US30 (max age 900s)." in " ".join(by_id["movement_price_source_truth"].evidence)


def test_live_readiness_can_pass_trading_edge_while_paper_maturity_stays_open():
    inputs = _report_inputs()
    inputs["owner_promotion"] = {
        "strategy_edge_passed": True,
        "best_strategy_edge_candidate": {
            "strategy_setting": "tsmom_126_250_2_10",
            "condition_contexts": ["normal", "D1"],
            "simulator_wins": 18,
            "walk_forward_windows": 5,
            "positive_routed_window_rate": 0.6,
            "mean_return_pct": 1.8932,
            "max_drawdown_pct": 7.0764,
            "trades": 76,
            "paper_proof_blockers": ["paper_days", "paper_passed"],
        },
    }
    report = build_live_readiness_report(**inputs)

    by_id = {check.gate_id: check for check in report.checks}
    assert by_id["trading_edge"].status == PASSED
    assert by_id["paper_proof_maturity"].status == "OPEN"
    assert "paper-proof maturity remains separate" in by_id["trading_edge"].plain_english


def test_live_readiness_summary_ui_preserves_movement_truth_detail():
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "ui" / "src" / "components" / "LiveReadinessSummaryPanel.tsx").read_text(encoding="utf-8")
    helper = (repo_root / "ui" / "src" / "util" / "movementSource.ts").read_text(encoding="utf-8")

    assert "detailEvidenceForLiveReadinessCheck" in helper
    assert 'check.gate_id !== "movement_price_source_truth"' in helper
    assert "check.plain_english" in source
    assert "detailEvidenceForLiveReadinessCheck(check)" in source
