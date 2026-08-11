from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import data as api_data
from api.routes import account as account_route
from cas_forex.account_health import build_account_health_report
from cas_forex.account_ledger import AccountLedgerEvent, TerminalTradeRow, build_paper_account_ledger


def _event(event_type: str, amount: float, ts: str = "2026-07-08T10:00:00Z") -> AccountLedgerEvent:
    return AccountLedgerEvent(
        ledger_id=f"{event_type}-{amount}",
        event_type=event_type,
        timestamp=ts,
        amount_usd=abs(amount),
        balance_delta_usd=amount,
        equity_delta_usd=amount,
        evidence_packet_id="test-ledger",
    )


def _row(
    row_id: str,
    *,
    tab: str,
    symbol: str,
    side: str,
    lots: float,
    open_price: float,
    close_or_current_price: float | None,
    stop_loss: float | None,
    net_pnl: float,
    status: str,
) -> TerminalTradeRow:
    return TerminalTradeRow(
        row_id=row_id,
        tab=tab,
        symbol=symbol,
        side=side,
        lot_size=lots,
        open_price=open_price,
        close_or_current_price=close_or_current_price,
        stop_loss=stop_loss,
        take_profit=None,
        timestamp="2026-07-08T10:00:00Z",
        broker_ticket=None,
        simulator_ticket=f"sim-{row_id}",
        strategy_id="test-strategy",
        ai_action="TEST",
        evidence_packet_id="test-ledger",
        net_pnl_usd=net_pnl,
        status=status,
    )


def test_account_health_reports_decision_metrics_and_open_protection():
    ledger = build_paper_account_ledger(
        initial_investment_usd=1000.0,
        plan_id="plan-1",
        lead_id="lead-1",
        strategy_setting="setting-1",
        as_of_date="2026-07-08",
        planned_risk_usd=25.0,
        floating_pnl_usd=15.0,
        margin_used_usd=100.0,
        cashflow_events=(
            _event("realized_profit", 120.0),
            _event("realized_loss", -40.0),
        ),
        positions=(
            _row(
                "open-protected",
                tab="Positions",
                symbol="EUR/USD",
                side="LONG",
                lots=0.1,
                open_price=1.1000,
                close_or_current_price=1.1010,
                stop_loss=1.0950,
                net_pnl=10.0,
                status="PAPER_INTENT",
            ),
            _row(
                "open-unprotected",
                tab="Positions",
                symbol="NAS100",
                side="LONG",
                lots=0.02,
                open_price=20000.0,
                close_or_current_price=20010.0,
                stop_loss=None,
                net_pnl=5.0,
                status="PAPER_INTENT",
            ),
        ),
        deals=(
            _row(
                "deal-win",
                tab="Deals",
                symbol="EUR/USD",
                side="LONG",
                lots=0.1,
                open_price=1.1000,
                close_or_current_price=1.1100,
                stop_loss=1.0950,
                net_pnl=120.0,
                status="CLOSED",
            ),
            _row(
                "deal-loss",
                tab="Deals",
                symbol="EUR/USD",
                side="SHORT",
                lots=0.1,
                open_price=1.2000,
                close_or_current_price=1.2050,
                stop_loss=1.2100,
                net_pnl=-40.0,
                status="CLOSED",
            ),
        ),
    ).to_dict()

    report = build_account_health_report(ledger)

    assert report["report_kind"] == "cas_forex_account_health"
    assert report["status"] == "ATTENTION"
    assert report["account"]["realized_pnl_usd"] == 80.0
    assert report["daily"]["realized_pnl_usd"] == 80.0
    assert report["closed_trade_performance"]["closed_trade_count"] == 2
    assert report["closed_trade_performance"]["win_rate_pct"] == 50.0
    assert report["closed_trade_performance"]["profit_factor"] == 3.0
    assert report["closed_trade_performance"]["expectancy_usd"] == 40.0
    assert report["closed_trade_performance"]["average_r_multiple"] == 0.75
    assert report["open_exposure"]["open_position_count"] == 2
    assert report["open_exposure"]["open_lots"] == 0.12
    assert report["open_exposure"]["unprotected_position_count"] == 1
    assert report["open_exposure"]["protective_order_coverage_pct"] == 50.0
    assert report["open_exposure"]["open_risk_estimate_usd"] == 25.0
    assert report["decision_metrics"]["profit_factor"] == 3.0


def test_account_health_marks_static_simulator_source_rows():
    ledger = build_paper_account_ledger(
        initial_investment_usd=1000.0,
        plan_id="plan-1",
        lead_id="lead-1",
        strategy_setting="setting-1",
        as_of_date="2026-07-08",
        positions=(
            _row(
                "static-row",
                tab="Positions",
                symbol="NAS100",
                side="LONG",
                lots=0.01,
                open_price=20000.0,
                close_or_current_price=20000.0,
                stop_loss=19800.0,
                net_pnl=0.0,
                status="PAPER_INTENT",
            ),
        ),
    ).to_dict()
    movement = {
        "price_source_status": "STATIC_SIMULATION_FALLBACK",
        "provider_usable_symbols": [],
        "static_fallback_symbols": ["NAS100"],
        "provider_stale_symbols": ["NAS100"],
        "provider_freshness_max_age_seconds": 900,
        "snapshot_age_seconds_by_symbol": {"NAS100": 960},
        "positions": [
            {
                "row_id": "static-row",
                "symbol": "NAS100",
                "side": "LONG",
                "lot_size": 0.01,
                "price_source": "paper_route_snapshot:static_simulation",
                "price_stale": True,
                "stale_reason": "Static paper-route snapshot: no usable provider or MT5 quote is pricing this simulator row.",
                "position_source_label": "PAPER_SIM_STATIC",
                "simulator_ticket": "sim-static-row",
            }
        ],
    }

    report = build_account_health_report(ledger, movement_stream=movement)

    assert report["status"] == "ATTENTION"
    assert report["source_health"]["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert report["source_health"]["price_source_label"] == "STATIC SIM"
    assert report["source_health"]["static_simulation_active"] is True
    assert "Static simulator rows are not being moved by usable provider/MT5 quotes right now" in report["source_health"]["price_source_warning"]
    assert report["source_health"]["position_feed_label"] == "SIM PROOF"
    assert "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions." in report["source_health"]["position_feed_detail"]
    assert "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)." in report["source_health"]["position_feed_detail"]
    assert report["source_health"]["detail"] == report["source_health"]["position_feed_detail"]
    assert "stale simulator telemetry" in report["source_health"]["local_detail"]
    assert report["source_health"]["simulator_position_count"] == 1
    assert report["source_health"]["static_simulator_position_count"] == 1
    assert report["source_health"]["stale_price_position_count"] == 1
    assert report["source_health"]["static_fallback_symbols"] == ["NAS100"]
    assert report["source_health"]["provider_stale_symbols"] == ["NAS100"]
    assert report["source_health"]["provider_freshness_max_age_seconds"] == 900
    assert report["source_health"]["snapshot_age_seconds_by_symbol"] == {"NAS100": 960}
    assert report["decision_metrics"]["stale_price_position_count"] == 1
    assert "stale/static simulator telemetry" in " ".join(report["blockers"])


def test_account_health_derives_position_feed_detail_when_movement_packet_omits_it():
    ledger = build_paper_account_ledger(
        initial_investment_usd=1000.0,
        plan_id="plan-1",
        lead_id="lead-1",
        strategy_setting="setting-1",
        as_of_date="2026-07-08",
        positions=(
            _row(
                "static-row",
                tab="Positions",
                symbol="NAS100",
                side="LONG",
                lots=0.01,
                open_price=20000.0,
                close_or_current_price=20000.0,
                stop_loss=19800.0,
                net_pnl=0.0,
                status="PAPER_INTENT",
            ),
        ),
    ).to_dict()
    movement = {
        "price_source_status": "STATIC_SIMULATION_FALLBACK",
        "market_data_provider_requested": True,
        "configured_market_data_provider": "Yahoo",
        "provider_usable_symbols": [],
        "static_fallback_symbols": ["NAS100"],
        "provider_stale_symbols": ["NAS100"],
        "provider_freshness_max_age_seconds": 900,
        "positions": [
            {
                "row_id": "static-row",
                "symbol": "NAS100",
                "side": "LONG",
                "lot_size": 0.01,
                "price_source": "paper_route_snapshot:static_simulation",
                "price_stale": True,
                "position_source_label": "PAPER_SIM_STATIC",
                "simulator_ticket": "sim-static-row",
            }
        ],
        "quotes": [],
    }

    report = build_account_health_report(ledger, movement_stream=movement)

    assert report["source_health"]["position_feed_label"] == "SIM PROOF"
    assert "Requested provider: Yahoo." in report["source_health"]["position_feed_detail"]
    assert "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)." in report["source_health"]["position_feed_detail"]
    assert report["source_health"]["detail"] == report["source_health"]["position_feed_detail"]


def test_account_health_prefers_canonical_movement_source_truth_when_present():
    ledger = build_paper_account_ledger(
        initial_investment_usd=1000.0,
        plan_id="plan-1",
        lead_id="lead-1",
        strategy_setting="setting-1",
        as_of_date="2026-07-08",
        positions=(
            _row(
                "static-row",
                tab="Positions",
                symbol="NAS100",
                side="LONG",
                lots=0.01,
                open_price=20000.0,
                close_or_current_price=20000.0,
                stop_loss=19800.0,
                net_pnl=0.0,
                status="PAPER_INTENT",
            ),
        ),
    ).to_dict()
    detail = (
        "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
        "Static simulator fallback is active for 1/1 row(s), so prices and floating P&L can remain at entry "
        "until usable provider or MT5 quotes arrive."
    )
    movement = {
        "price_source_status": "STATIC_SIMULATION_FALLBACK",
        "provider_usable_symbols": [],
        "static_fallback_symbols": ["NAS100"],
        "provider_stale_symbols": ["NAS100"],
        "positions": [
            {
                "row_id": "static-row",
                "symbol": "NAS100",
                "side": "LONG",
                "lot_size": 0.01,
                "price_source": "paper_route_snapshot:static_simulation",
                "price_stale": True,
                "position_source_label": "PAPER_SIM_STATIC",
                "simulator_ticket": "sim-static-row",
            }
        ],
        "movement_source_truth": {
            "movement_stream_present": True,
            "price_source_status": "STATIC_SIMULATION_FALLBACK",
            "price_source_label": "STATIC SIM",
            "price_source_summary": "Static simulation only.",
            "position_feed_label": "SIM PROOF",
            "position_feed_detail": detail,
            "static_simulation_active": True,
            "open_position_count": 1,
            "static_position_count": 1,
            "static_quote_count": 1,
            "closed_market_symbols": ["NAS100"],
            "closed_market_quote_count": 1,
            "unsupported_provider_symbols": ["NAS100"],
            "provider_freshness_max_age_seconds": 900,
            "detail": detail,
            "local_detail": detail,
        },
    }

    report = build_account_health_report(ledger, movement_stream=movement)

    assert report["source_health"]["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert report["source_health"]["static_quote_count"] == 1
    assert report["source_health"]["closed_market_symbols"] == ["NAS100"]
    assert report["source_health"]["closed_market_quote_count"] == 1
    assert report["source_health"]["unsupported_provider_symbols"] == ["NAS100"]
    assert report["source_health"]["detail"] == detail


def test_account_health_route_returns_report(monkeypatch):
    app = FastAPI()
    app.include_router(account_route.router, prefix="/api/forex/account")
    monkeypatch.setattr(
        account_route,
        "account_health",
        lambda initial_investment_usd=None: {
            "report_kind": "cas_forex_account_health",
            "status": "OBSERVING",
            "initial_investment": initial_investment_usd,
        },
    )

    body = TestClient(app).get("/api/forex/account/health?initial_investment=2500").json()

    assert body["report_kind"] == "cas_forex_account_health"
    assert body["status"] == "OBSERVING"
    assert body["initial_investment"] == 2500.0


def test_dashboard_fast_state_surfaces_account_health(monkeypatch):
    monkeypatch.setattr(api_data, "ui_readiness", lambda: {"completed_trading_days": 1, "chains_verified": {}})
    monkeypatch.setattr(api_data, "_dashboard_proof_progress_summary", lambda readiness: {"report_kind": "proof"})
    monkeypatch.setattr(api_data, "_dashboard_risk_budget_summary_from_latest_risk", lambda: {"report_kind": "risk"})
    monkeypatch.setattr(api_data, "_dashboard_owner_control_summary_from_full", lambda: {"mode": "paper"})
    monkeypatch.setattr(
        api_data,
        "account_health",
        lambda: {
            "report_kind": "cas_forex_account_health",
            "status": "OBSERVING",
            "blockers": [],
            "account": {"balance_usd": 1000.0, "equity_usd": 1010.0},
            "closed_trade_performance": {"closed_trade_count": 1, "profit_factor": 2.0},
            "open_exposure": {"open_position_count": 1, "protective_order_coverage_pct": 100.0},
            "source_health": {
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
                "price_source_label": "STATIC SIM",
                "price_source_summary": "Static simulation only: usable provider or MT5 quotes are not repricing paper/demo rows.",
                "price_source_warning": "Static simulator rows are not being moved by usable provider/MT5 quotes right now.",
                "position_feed_label": "SIM PROOF",
                "position_feed_detail": "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions.",
                "static_simulation_active": True,
                "open_position_count": 1,
                "static_simulator_position_count": 1,
                "stale_price_position_count": 1,
                "broker_ticket_position_count": 0,
                "simulator_position_count": 1,
                "source_label_counts": {"SIM TICKET STATIC": 1},
                "stale_positions": [{"symbol": "NAS100", "reason": "provider_stale"}],
                "static_positions": [{"symbol": "NAS100", "reason": "static_simulation"}],
                "attention_required": True,
                "detail": "Static simulator fallback.",
                "local_detail": "Local static telemetry fallback.",
            },
            "decision_metrics": {"profit_factor": 2.0},
            "claim_boundary": "read only",
        },
    )
    monkeypatch.setattr(
        api_data,
        "active_account_truth",
        lambda simulator_health_report=None: {
            "report_kind": "cas_forex_active_account_truth",
            "status": "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE",
            "authoritative_account_source": "mt5_account_snapshot",
            "source_label": "MT5 DEMO",
            "account": {"login": 1000694, "balance_usd": 44757.89},
            "secondary_health_seen": simulator_health_report is not None,
        },
    )

    packet = api_data.dashboard_fast_state()

    assert packet["accountHealth"]["report_kind"] == "cas_forex_account_health"
    assert packet["accountHealth"]["summary_only"] is True
    assert packet["accountHealth"]["decision_metrics"]["profit_factor"] == 2.0
    assert packet["accountHealth"]["source_health"]["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert packet["accountHealth"]["source_health"]["price_source_label"] == "STATIC SIM"
    assert packet["accountHealth"]["source_health"]["price_source_summary"].startswith("Static simulation only")
    assert packet["accountHealth"]["source_health"]["price_source_warning"].startswith("Static simulator rows")
    assert packet["accountHealth"]["source_health"]["position_feed_label"] == "SIM PROOF"
    assert packet["accountHealth"]["source_health"]["position_feed_detail"].startswith("Rows in this snapshot")
    assert packet["accountHealth"]["source_health"]["static_simulation_active"] is True
    assert packet["accountHealth"]["source_health"]["source_label_counts"] == {"SIM TICKET STATIC": 1}
    assert packet["accountHealth"]["source_health"]["stale_positions"] == [{"symbol": "NAS100", "reason": "provider_stale"}]
    assert packet["accountHealth"]["source_health"]["static_positions"] == [{"symbol": "NAS100", "reason": "static_simulation"}]
    assert packet["accountHealth"]["source_health"]["static_simulator_position_count"] == 1
    assert packet["accountHealth"]["source_health"]["local_detail"] == "Local static telemetry fallback."
    assert packet["activeAccountTruth"]["status"] == "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE"
    assert packet["activeAccountTruth"]["account"]["login"] == 1000694
    assert packet["activeAccountTruth"]["secondary_health_seen"] is True


def test_active_account_route_exposes_source_ranked_truth(monkeypatch):
    app = FastAPI()
    app.include_router(account_route.router, prefix="/api/forex/account")
    monkeypatch.setattr(
        account_route,
        "active_account_truth",
        lambda: {
            "report_kind": "cas_forex_active_account_truth",
            "status": "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE",
            "authoritative_account_source": "mt5_account_snapshot",
            "source_label": "MT5 DEMO",
            "account": {"login": 1000694, "balance_usd": 44757.89},
        },
    )

    body = TestClient(app).get("/api/forex/account/active").json()

    assert body["report_kind"] == "cas_forex_active_account_truth"
    assert body["authoritative_account_source"] == "mt5_account_snapshot"
    assert body["account"]["login"] == 1000694


def test_account_health_ui_panel_is_wired_on_dashboard_and_tracker():
    dashboard_page = (api_data.REPO_ROOT / "ui" / "src" / "pages" / "DashboardPage.tsx").read_text(encoding="utf-8")
    tracker_page = (api_data.REPO_ROOT / "ui" / "src" / "pages" / "TrackerPage.tsx").read_text(encoding="utf-8")
    component = (api_data.REPO_ROOT / "ui" / "src" / "components" / "AccountHealthPanel.tsx").read_text(encoding="utf-8")
    api_client = (api_data.REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert "function AccountHealthPanel" in component
    assert "Unprotected Positions" in component
    assert "Static / Stale Pricing Rows" in component
    assert "<AccountHealthPanel" in dashboard_page
    assert "report={accountHealth}" in dashboard_page
    assert 'title={activeMt5Account ? "Secondary Simulator Evidence"' in dashboard_page
    assert 'authorityLabel={activeMt5Account ? "SECONDARY - NOT ACTIVE ACCOUNT"' in dashboard_page
    assert 'title="Active Account"' in dashboard_page
    assert "<AccountHealthPanel" in tracker_page
    assert "fetchAccountHealth" in tracker_page
    assert "/account/health" in api_client
