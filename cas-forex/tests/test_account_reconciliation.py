from cas_forex.account_ledger import build_account_ledger_from_paper_review
from cas_forex.account_reconciliation import (
    RECONCILED_WITH_WARNINGS,
    RECONCILIATION_FAILED,
    STATUS_MISMATCH,
    STATUS_OK,
    STATUS_UNVERIFIABLE,
    assert_reconciliation_boundary,
    build_account_reconciliation_report,
)
from cas_forex.movement_stream import build_movement_stream_state


def _risk_review():
    return {
        "plan_id": "plan-1",
        "lead_id": "lead-1",
        "strategy_setting": "tsmom_126_250_2_10",
        "date": "2026-06-23",
        "review_id": "review-1",
        "account_equity": 5000.0,
        "route_action": "ROUTE_PAPER_SIGNAL",
        "total_planned_risk_usd": 25.30,
        "sizing": [
            {
                "symbol": "US30",
                "direction": "LONG",
                "entry_price": 51745.87,
                "stop_loss": 50485.56,
                "take_profit": 58047.44,
                "sized_lots": 0.01,
                "proposal_id": "proposal-us30",
                "attempt_status": "PAPER_ATTEMPT_ALLOWED",
            }
        ],
    }


def _valid_paper_receipt():
    return {
        "receipt_id": "receipt-1",
        "receipt_validation_status": "BROKER_API_VERIFIED",
        "broker_mode": "PAPER_MT5",
        "trading_date": "2026-06-23",
        "symbols": ["US30"],
        "orders_attempted": 0,
        "open_positions_reconciled": True,
        "live_mode": False,
        "chain_verified": True,
    }


def _ledger():
    return build_account_ledger_from_paper_review(_risk_review()).to_dict()


def test_reconciliation_passes_with_warnings_for_valid_paper_receipt():
    ledger = _ledger()
    movement = build_movement_stream_state(ledger, timestamp="2026-06-23T12:00:00Z").to_dict()
    report = build_account_reconciliation_report(ledger, _valid_paper_receipt(), movement_stream=movement)

    # Balance/equity is not provable from a paper receipt yet -> warning, not pass.
    assert report.overall_status == RECONCILED_WITH_WARNINGS
    assert report.checks_mismatch == 0
    assert report.checks_unverifiable >= 1
    by_id = {c.check_id: c for c in report.checks}
    assert by_id["broker_receipt_validated"].status == STATUS_OK
    assert by_id["broker_chain_verified"].status == STATUS_OK
    assert by_id["live_mode_consistency"].status == STATUS_OK
    assert by_id["symbol_coverage"].status == STATUS_OK
    assert by_id["balance_equity_reconciliation"].status == "UNVERIFIABLE"
    assert by_id["movement_internal_consistency"].status == STATUS_OK
    assert report.movement_stream_present is True
    assert report.movement_price_source_status == "UNKNOWN"
    assert report.movement_position_feed_label == "SIM PROOF"
    assert report.movement_position_feed_detail is not None
    assert report.movement_source_truth is not None
    assert report.movement_source_truth["movement_stream_present"] is True
    assert report.movement_source_truth["price_source_status"] == report.movement_price_source_status
    assert report.movement_source_truth["position_feed_label"] == "SIM PROOF"
    assert report.movement_source_truth["detail"] == report.movement_position_feed_detail
    assert "paper/demo proof rows, not MT5 broker-truth positions" in report.movement_position_feed_detail
    assert "Movement source truth: SIM PROOF" in by_id["movement_internal_consistency"].detail
    assert report.live_money_authorized is False
    assert report.payment_movement_authorized is False
    assert report.trading_edge_status == "OPEN"
    assert_reconciliation_boundary(report)


def test_reconciliation_fails_on_unvalidated_receipt():
    receipt = _valid_paper_receipt()
    receipt["receipt_validation_status"] = "UNVERIFIED"
    receipt["chain_verified"] = False
    report = build_account_reconciliation_report(_ledger(), receipt)

    assert report.overall_status == RECONCILIATION_FAILED
    assert report.checks_mismatch >= 2
    assert report.blockers


def test_reconciliation_flags_live_mode_safety_mismatch():
    receipt = _valid_paper_receipt()
    receipt["live_mode"] = True  # broker says live, internal ledger is paper-only
    report = build_account_reconciliation_report(_ledger(), receipt)

    by_id = {c.check_id: c for c in report.checks}
    assert by_id["live_mode_consistency"].status == STATUS_MISMATCH
    assert report.overall_status == RECONCILIATION_FAILED


def test_reconciliation_flags_symbol_coverage_mismatch():
    receipt = _valid_paper_receipt()
    receipt["symbols"] = ["NAS100"]  # internal has US30
    report = build_account_reconciliation_report(_ledger(), receipt)

    by_id = {c.check_id: c for c in report.checks}
    assert by_id["symbol_coverage"].status == STATUS_MISMATCH
    assert report.overall_status == RECONCILIATION_FAILED


def test_reconciliation_matches_broker_balance_when_present():
    receipt = _valid_paper_receipt()
    receipt["balance"] = 5000.0
    receipt["equity"] = 5000.0
    report = build_account_reconciliation_report(_ledger(), receipt)

    by_id = {c.check_id: c for c in report.checks}
    assert by_id["balance_equity_reconciliation"].status == STATUS_OK


def test_reconciliation_will_not_claim_full_match_from_a_partial_broker_receipt():
    """A field the broker never reported must not be counted as agreement.

    Previously an absent balance (or equity) short-circuited to "ok", so the
    check reported the full-scope claim "internal balance/equity matches
    broker-reported figures" after comparing only one of the two values.
    """
    for reported, missing in (("balance", "equity"), ("equity", "balance")):
        receipt = _valid_paper_receipt()
        receipt[reported] = 5000.0  # the other field is deliberately absent
        report = build_account_reconciliation_report(_ledger(), receipt)
        check = {c.check_id: c for c in report.checks}["balance_equity_reconciliation"]

        assert check.status == STATUS_UNVERIFIABLE, (
            f"only {reported} was comparable; status must not be OK"
        )
        assert missing in check.detail, "the unreconciled field must be named"
        assert "matches broker-reported figures" not in check.detail, (
            "must not emit the full-scope match claim from a partial comparison"
        )


def test_reconciliation_still_flags_a_real_mismatch_on_a_partial_receipt():
    receipt = _valid_paper_receipt()
    receipt["balance"] = 999_999.0  # disagrees with the ledger; equity absent
    report = build_account_reconciliation_report(_ledger(), receipt)
    check = {c.check_id: c for c in report.checks}["balance_equity_reconciliation"]

    assert check.status == STATUS_MISMATCH
    assert "balance" in check.detail


def test_reconciliation_matches_nested_account_snapshot_when_present():
    receipt = _valid_paper_receipt()
    receipt["account_snapshot"] = {"balance": 5000.0, "equity": 5000.0, "margin": 0.0, "margin_free": 5000.0}
    report = build_account_reconciliation_report(_ledger(), receipt)

    by_id = {c.check_id: c for c in report.checks}
    assert by_id["balance_equity_reconciliation"].status == STATUS_OK


def test_reconciliation_can_sync_to_broker_snapshot_only_when_requested():
    receipt = _valid_paper_receipt()
    receipt["account_snapshot"] = {"balance": 100000.0, "equity": 100000.0, "margin": 0.0, "margin_free": 100000.0}

    default_report = build_account_reconciliation_report(_ledger(), receipt)
    default_by_id = {c.check_id: c for c in default_report.checks}
    assert default_by_id["balance_equity_reconciliation"].status == STATUS_MISMATCH

    synced_ledger = build_account_ledger_from_paper_review(_risk_review(), initial_investment_usd=100000.0).to_dict()
    synced_report = build_account_reconciliation_report(synced_ledger, receipt)
    synced_by_id = {c.check_id: c for c in synced_report.checks}
    assert synced_by_id["balance_equity_reconciliation"].status == STATUS_OK


def test_reconciliation_derives_movement_position_feed_detail_when_missing():
    movement = {
        "account": {"balance_usd": 5000.0},
        "price_source_status": "STATIC_SIMULATION_FALLBACK",
        "market_data_provider_requested": True,
        "configured_market_data_provider": "Yahoo",
        "provider_usable_symbols": [],
        "static_fallback_symbols": ["US30"],
        "provider_stale_symbols": ["US30"],
        "provider_freshness_max_age_seconds": 900,
        "positions": [
            {
                "row_id": "paper-us30",
                "symbol": "US30",
                "side": "LONG",
                "lot_size": 0.01,
                "price_source": "paper_route_snapshot:static_simulation",
                "price_stale": True,
                "position_source_label": "PAPER_SIM_STATIC",
                "simulator_ticket": "sim-us30",
                "broker_ticket": None,
            }
        ],
        "quotes": [],
    }
    report = build_account_reconciliation_report(_ledger(), _valid_paper_receipt(), movement_stream=movement)
    by_id = {c.check_id: c for c in report.checks}

    assert report.movement_stream_present is True
    assert report.movement_position_feed_label == "SIM PROOF"
    assert report.movement_position_feed_detail is not None
    assert report.movement_source_truth is not None
    assert report.movement_source_truth["position_feed_label"] == "SIM PROOF"
    assert report.movement_source_truth["configured_market_data_provider"] == "Yahoo"
    assert report.movement_source_truth["provider_stale_symbols"] == ["US30"]
    assert "Requested provider: Yahoo." in report.movement_position_feed_detail
    assert "Stale provider/MT5 snapshots were rejected for: US30 (max age 900s)." in report.movement_position_feed_detail
    assert "Requested provider: Yahoo." in by_id["movement_internal_consistency"].detail
