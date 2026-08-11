from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import live_order_dry_run as route_module
from cas_forex import (
    auto_halt,
    broker_reality,
    broker_truth_monitor,
    compound_add_order_dry_run_review,
    edge_authorization,
    live_pilot,
    live_recovery,
    order_attempt_audit,
)
from cas_forex.edge_gate import CandidateSetup, EdgeTestDecision, _now_iso, mint_token
from cas_forex.live_order_dry_run import (
    COMPOUND_ADD_REPORT_KIND,
    STATUS_BLOCKED,
    STATUS_PASS,
    CompoundAddDryRunRequest,
    LiveOrderDryRunAuditLog,
    LiveOrderDryRunRequest,
    build_compound_add_order_dry_run,
    build_live_order_dry_run,
)
from cas_forex import live_order_dry_run_review
from cas_forex.schemas.order import BrokerMode, OrderOutcome, OrderStatus


@pytest.fixture(autouse=True)
def _reset_edge_registry():
    edge_authorization.reset()
    yield
    edge_authorization.reset()


def _request(volume: float = 0.01) -> LiveOrderDryRunRequest:
    return LiveOrderDryRunRequest(
        order_id="dry-run-1",
        decision_ref="dry-ref-1",
        symbol="EUR/USD",
        direction="LONG",
        volume=volume,
        price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1100,
        expected_loss_usd=10.0,
    )


def _compound_cas_map() -> dict:
    return {
        "selected_rpm_action": "ROUTE",
        "selected_is_lacuna": False,
        "selected_cjt_region": "active",
        "cell_reliability": 0.85,
        "cascade_confidence": 0.80,
    }


def _compound_request(
    *,
    broker_grade_market_truth: bool = False,
    cas_feature_map: dict | None = None,
    current_price: float = 1.1050,
) -> CompoundAddDryRunRequest:
    return CompoundAddDryRunRequest(
        parent_order_id="parent-1",
        parent_decision_ref="parent-ref-1",
        broker_ticket="123456",
        symbol="EUR/USD",
        direction="LONG",
        add_order_id="add-1",
        add_decision_ref="add-ref-1",
        add_volume=0.01,
        price=current_price,
        stop_loss=1.0950,
        take_profit=1.1150,
        position_entry=1.1000,
        position_stop_loss=1.0900,
        current_price=current_price,
        current_units=1,
        max_units=4,
        broker_grade_market_truth=broker_grade_market_truth,
        cas_feature_map=cas_feature_map or {},
        expected_loss_usd=10.0,
    )


def _authorized_live_cfg() -> SimpleNamespace:
    return SimpleNamespace(
        owner_enable_live_trading=True,
        live_trading_licensed=True,
        mt5_login=12345,
        mt5_password="pw",
        mt5_server="HugosWay-Live",
        live_mode=True,
        prefer_mt5=True,
        mt5_path=None,
        personal_account_ack=True,
        no_pooled_capital_ack=True,
        account_type="personal",
        selected_broker_id="hugosway",
        broker_name="HUGOSWAY",
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
    )


def _risk_authorized_live_cfg() -> SimpleNamespace:
    cfg = _authorized_live_cfg()
    cfg.max_total_exposure_lots = 2.0
    cfg.max_open_positions = 7
    cfg.max_risk_per_trade_pct = 0.5
    cfg.max_margin_utilization_pct = 50.0
    return cfg


def _clean_live_truth() -> dict:
    from cas_forex.time_utils import utc_now

    return {
        "report_kind": "cas_forex_broker_truth_monitor",
        "generated_at": utc_now().isoformat(),
        "overall_status": "RECONCILED",
        "mt5_connected": True,
        "mt5_is_demo": False,
        "mt5_account": 101321,
        "mt5_account_server": "Risen-Trade",
        "mt5_expected_account": 101321,
        "mt5_expected_server": "Risen-Trade",
        "mt5_account_identity_matches_config": True,
        "mt5_open_position_count": 0,
        "terminal_unmatched_open_position_count": 0,
        "terminal_pending_receipt_count": 0,
        "terminal_receipt_mismatch_count": 0,
    }


def _open_live_truth() -> dict:
    report = _clean_live_truth()
    report.update(
        {
            "mt5_open_position_count": 1,
            "terminal_unmatched_open_position_count": 0,
            "terminal_pending_receipt_count": 0,
            "terminal_receipt_mismatch_count": 0,
        }
    )
    return report


class _FakePaperBridge:
    def __init__(self) -> None:
        self.calls: list = []

    def will_execute_real_order(self) -> bool:
        return False

    def execute_order(self, order):
        self.calls.append(order)
        return OrderOutcome(
            order_ref=order.order_id,
            broker_ticket=990001,
            status=OrderStatus.EXECUTED,
            filled_price=float(getattr(order, "price", 0.0) or 1.1050),
            broker_mode=BrokerMode.SIMULATED,
            is_real_broker=False,
        )


def _authorize_edge(req: LiveOrderDryRunRequest, *, config=None) -> None:
    evaluated_at = _now_iso()
    setup = CandidateSetup(
        symbol=req.symbol,
        timeframe="H1",
        direction=req.direction,
        entry=req.price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        signal_strength=1.0,
        regime="trend",
        decision_ref=req.decision_ref,
    )
    decision = EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.7,
        null_p95=0.2,
        threshold=0.65,
        edge_token=mint_token(setup, evaluated_at),
        evaluated_at=evaluated_at,
        reason="test edge PASS",
    )
    edge_authorization.authorize(
        req.decision_ref,
        decision,
        setup,
        config=config,
        is_real=bool(getattr(config, "live_mode", False)) if config is not None else None,
        volume=float(req.volume),
        order_type="MARKET",
        price=float(req.price),
    )


def _waste_real_candle_source() -> dict:
    return {
        "report_kind": "cas_forex_waste_real_candle_dry_run_source",
        "status": "WASTE_PROBE_DRY_RUN_HANDOFF_READY",
        "probe_status": "EDGE_PASS_UNREGISTERED",
        "symbol": "EUR/USD",
        "timeframe": "H1",
        "direction": "LONG",
        "decision_ref": "dry-ref-1",
        "source": "MT5TerminalMarketDataConnector",
        "broker_grade_market_truth": True,
        "entry_pair_count": 24,
        "edge_status": "PASS",
        "edge_has_token": True,
        "checks": [{"check_id": "broker_grade_market_truth", "passed": True}],
        "claim_boundary": "test WASTE source; not LICENSED",
    }


def _passing_waste_entry_dry_run(tmp_path, monkeypatch, audit_path) -> dict:
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    _accept_live_pilot(tmp_path, monkeypatch)
    req = _request()
    _authorize_edge(req, config=_authorized_live_cfg())
    report = build_live_order_dry_run(req, config=_authorized_live_cfg(), audit=None)
    report["waste_real_candle_source"] = _waste_real_candle_source()
    report["audit"] = LiveOrderDryRunAuditLog(audit_path).append(report)
    return report


def _accept_live_pilot(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(live_pilot, "DEFAULT_POLICY_PATH", tmp_path / "pilot.json")
    monkeypatch.setattr(live_pilot, "DEFAULT_AUDIT_PATH", tmp_path / "pilot-audit.jsonl")
    live_pilot.update_live_pilot_policy(
        {
            "allowed_symbols": ["EUR/USD"],
            "sizing_mode": live_pilot.SIZING_MODE_ABSOLUTE_LOTS,
            "continuous_authority": False,
            "max_trade_lots": 0.01,
            "max_open_live_lots": 0.02,
            "max_live_trade_count": 2,
            "max_daily_loss_usd": 25.0,
            "max_total_loss_usd": 50.0,
            "max_pilot_days": 5,
            "owner_understands_real_money_risk": True,
            "owner_confirms_risk_denominated_sizing": True,
            "owner_confirms_autonomous_scaling_within_envelope": True,
            "owner_confirms_emergency_stop_ready": True,
        },
        confirm_owner_accept=True,
    )


def _accept_risk_denominated_live_authority(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(live_pilot, "DEFAULT_POLICY_PATH", tmp_path / "risk-authority.json")
    monkeypatch.setattr(live_pilot, "DEFAULT_AUDIT_PATH", tmp_path / "risk-authority-audit.jsonl")
    live_pilot.update_live_pilot_policy(
        {
            "allowed_symbols": ["EUR/USD"],
            "sizing_mode": live_pilot.SIZING_MODE_RISK_DENOMINATED,
            "continuous_authority": True,
            "max_trade_risk_pct_equity": 0.5,
            "max_live_trade_count": 10,
            "max_daily_loss_usd": 25.0,
            "max_total_loss_usd": 50.0,
            "max_pilot_days": 5,
            "owner_understands_real_money_risk": True,
            "owner_confirms_risk_denominated_sizing": True,
            "owner_confirms_autonomous_scaling_within_envelope": True,
            "owner_confirms_emergency_stop_ready": True,
        },
        confirm_owner_accept=True,
    )


def test_live_order_dry_run_blocks_by_default_and_audits(tmp_path):
    audit = LiveOrderDryRunAuditLog(tmp_path / "dry-run-audit.jsonl")

    report = build_live_order_dry_run(_request(), config=SimpleNamespace(), audit=audit)

    assert report["status"] == STATUS_BLOCKED
    assert report["would_reach_broker_if_executed"] is False
    assert report["broker_touched"] is False
    assert any(check["check_id"] == "live_trading_gate" and not check["passed"] for check in report["checks"])
    assert any(check["check_id"] == "edge_pass_token" and not check["passed"] for check in report["checks"])
    assert audit.latest()["status"] == STATUS_BLOCKED


def test_live_order_dry_run_passes_only_when_all_live_gates_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    _accept_live_pilot(tmp_path, monkeypatch)
    req = _request()
    _authorize_edge(req, config=_authorized_live_cfg())

    report = build_live_order_dry_run(req, config=_authorized_live_cfg())

    assert report["status"] == STATUS_PASS
    assert report["would_reach_broker_if_executed"] is True
    assert report["broker_touched"] is False
    assert all(check["passed"] for check in report["checks"])
    assert "does not place orders" in report["claim_boundary"]


def test_risk_denominated_dry_run_allows_1_09_lots_only_when_stop_risk_fits(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr("cas_forex.execution_guard._ai_dial", lambda name: None)
    _accept_risk_denominated_live_authority(tmp_path, monkeypatch)
    cfg = _risk_authorized_live_cfg()
    account = {
        "balance": 50_000.0,
        "equity": 50_000.0,
        "margin": 1_000.0,
        "margin_free": 49_000.0,
        "leverage": 500,
    }

    qualified = LiveOrderDryRunRequest(
        order_id="risk-sized-1-09-pass",
        decision_ref="risk-sized-1-09-pass-ref",
        symbol="EUR/USD",
        direction="LONG",
        volume=1.09,
        price=1.1000,
        stop_loss=1.0990,
        take_profit=1.1020,
    )
    _authorize_edge(qualified, config=cfg)
    qualified_report = build_live_order_dry_run(
        qualified,
        config=cfg,
        account_snapshot=account,
        live_telemetry={"positions": []},
    )

    assert qualified_report["status"] == STATUS_PASS
    assert qualified_report["pre_trade_estimate"]["risk_at_stop_usd"] == pytest.approx(109.0)
    assert qualified_report["pre_trade_estimate"]["risk_at_stop_pct_equity"] == pytest.approx(0.218)
    assert next(
        check for check in qualified_report["checks"] if check["check_id"] == "small_live_pilot"
    )["passed"] is True

    excessive = LiveOrderDryRunRequest(
        order_id="risk-sized-1-09-block",
        decision_ref="risk-sized-1-09-block-ref",
        symbol="EUR/USD",
        direction="LONG",
        volume=1.09,
        price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
    )
    _authorize_edge(excessive, config=cfg)
    excessive_report = build_live_order_dry_run(
        excessive,
        config=cfg,
        account_snapshot=account,
        live_telemetry={"positions": []},
    )

    assert excessive_report["status"] == STATUS_BLOCKED
    assert excessive_report["pre_trade_estimate"]["risk_at_stop_usd"] == pytest.approx(545.0)
    assert excessive_report["pre_trade_estimate"]["risk_at_stop_pct_equity"] == pytest.approx(1.09)
    pilot_check = next(
        check for check in excessive_report["checks"] if check["check_id"] == "small_live_pilot"
    )
    assert pilot_check["passed"] is False
    assert "exceeds live authority max_trade_risk_pct_equity" in pilot_check["detail"]


def test_live_order_dry_run_blocks_on_bound_price_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    _accept_live_pilot(tmp_path, monkeypatch)
    req = _request()
    _authorize_edge(req, config=_authorized_live_cfg())
    drifted = LiveOrderDryRunRequest(
        order_id=req.order_id,
        decision_ref=req.decision_ref,
        symbol=req.symbol,
        direction=req.direction,
        volume=req.volume,
        price=1.1010,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        expected_loss_usd=req.expected_loss_usd,
    )

    report = build_live_order_dry_run(drifted, config=_authorized_live_cfg())

    assert report["status"] == STATUS_BLOCKED
    edge_check = next(check for check in report["checks"] if check["check_id"] == "edge_pass_token")
    assert edge_check["passed"] is False
    assert "price mismatch" in edge_check["detail"]


def test_compound_add_dry_run_blocks_by_default_and_audits(tmp_path):
    audit = LiveOrderDryRunAuditLog(tmp_path / "compound-add-audit.jsonl")

    report = build_compound_add_order_dry_run(_compound_request(), config=SimpleNamespace(), audit=audit)

    assert report["status"] == STATUS_BLOCKED
    assert report["report_kind"] == COMPOUND_ADD_REPORT_KIND
    assert report["would_reach_broker_if_executed"] is False
    assert report["broker_touched"] is False
    assert any(check["check_id"] == "broker_truth_position" and not check["passed"] for check in report["checks"])
    assert any(check["check_id"] == "edge_pass_token" and not check["passed"] for check in report["checks"])
    latest = audit.latest()
    assert latest["status"] == STATUS_BLOCKED
    assert latest["action"] == "COMPOUND_ADD_ORDER_DRY_RUN"


def test_compound_add_dry_run_passes_only_when_all_add_gates_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    _accept_live_pilot(tmp_path, monkeypatch)
    req = _compound_request(
        broker_grade_market_truth=True,
        cas_feature_map=_compound_cas_map(),
    )
    _authorize_edge(req.to_live_order_request(), config=_authorized_live_cfg())

    report = build_compound_add_order_dry_run(req, config=_authorized_live_cfg())

    assert report["status"] == STATUS_PASS
    assert report["would_reach_broker_if_executed"] is True
    assert report["broker_touched"] is False
    assert report["compound_context"]["compound_decision"]["action"] == "ADD"
    assert all(check["passed"] for check in report["checks"])
    assert "does not place add orders" in report["claim_boundary"]


def test_compound_add_dry_run_review_accepts_current_pass_fingerprint(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    _accept_live_pilot(tmp_path, monkeypatch)
    req = _compound_request(
        broker_grade_market_truth=True,
        cas_feature_map=_compound_cas_map(),
    )
    _authorize_edge(req.to_live_order_request(), config=_authorized_live_cfg())
    dry_run = build_compound_add_order_dry_run(
        req,
        config=_authorized_live_cfg(),
        audit=LiveOrderDryRunAuditLog(tmp_path / "compound-add-audit.jsonl"),
    )

    accepted = compound_add_order_dry_run_review.accept_compound_add_order_dry_run_review(
        notes="Owner reviewed exact compound add before any pyramid dispatch.",
        confirm_owner_accept=True,
        dry_run_audit=dry_run["audit"],
        broker_truth_report=_open_live_truth(),
        state_path=tmp_path / "compound-add-review.json",
        audit_path=tmp_path / "compound-add-review-audit.jsonl",
    )

    assert accepted["owner_review_status"] == compound_add_order_dry_run_review.STATUS_ACCEPT
    assert accepted["compound_add_dry_run_review_clear_for_dispatch"] is True
    assert accepted["accepted_fingerprint"] == accepted["current_fingerprint"]
    assert accepted["latest_compound_add_summary"]["broker_ticket"] == "123456"
    assert (tmp_path / "compound-add-review-audit.jsonl").exists()

    changed = compound_add_order_dry_run_review.build_compound_add_order_dry_run_review(
        dry_run_audit={
            **dry_run["audit"],
            "payload": {**dry_run["audit"]["payload"], "order_id": "different-add-order"},
        },
        broker_truth_report=_open_live_truth(),
        state_path=tmp_path / "compound-add-review.json",
    )
    assert changed["compound_add_dry_run_review_clear_for_dispatch"] is False


def test_compound_add_dry_run_review_rejects_without_pass(tmp_path):
    blocked_audit = {
        "audit_id": "blocked-compound-add",
        "timestamp": "2026-06-30T12:00:00+00:00",
        "status": STATUS_BLOCKED,
        "payload": {
            "report_kind": COMPOUND_ADD_REPORT_KIND,
            "generated_at": "2026-06-30T12:00:00+00:00",
            "status": STATUS_BLOCKED,
            "broker_touched": False,
            "checks": [],
        },
    }

    with pytest.raises(compound_add_order_dry_run_review.CompoundAddOrderDryRunReviewError):
        compound_add_order_dry_run_review.accept_compound_add_order_dry_run_review(
            confirm_owner_accept=True,
            dry_run_audit=blocked_audit,
            broker_truth_report=_open_live_truth(),
            state_path=tmp_path / "compound-add-review.json",
            audit_path=tmp_path / "compound-add-review-audit.jsonl",
        )


def test_live_order_dry_run_route_records_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(route_module, "DEFAULT_AUDIT_PATH", tmp_path / "dry-route-audit.jsonl")
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-order-dry-run")
    client = TestClient(app)

    response = client.post(
        "/api/forex/live-order-dry-run/order",
        json={
            "order_id": "route-dry-1",
            "symbol": "EUR/USD",
            "direction": "LONG",
            "volume": 0.01,
            "price": 1.1000,
            "stop_loss": 1.0900,
            "take_profit": 1.1100,
        },
    )
    latest = client.get("/api/forex/live-order-dry-run/latest")

    assert response.status_code == 200
    assert response.json()["status"] == STATUS_BLOCKED
    assert response.json()["broker_touched"] is False
    assert latest.status_code == 200
    assert latest.json()["status"] == STATUS_BLOCKED
    assert latest.json()["latest_audit"]["order_id"] == "route-dry-1"


def test_compound_add_dry_run_route_records_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(route_module, "DEFAULT_COMPOUND_ADD_AUDIT_PATH", tmp_path / "compound-route-audit.jsonl")
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-order-dry-run")
    client = TestClient(app)

    response = client.post(
        "/api/forex/live-order-dry-run/compound-add-order",
        json={
            "parent_order_id": "parent-route-1",
            "parent_decision_ref": "parent-route-ref-1",
            "broker_ticket": "654321",
            "symbol": "EUR/USD",
            "direction": "LONG",
            "add_order_id": "route-add-1",
            "add_decision_ref": "route-add-ref-1",
            "add_volume": 0.01,
            "price": 1.1050,
            "stop_loss": 1.0950,
            "take_profit": 1.1150,
            "position_entry": 1.1000,
            "position_stop_loss": 1.0900,
            "current_price": 1.1050,
        },
    )
    latest = client.get("/api/forex/live-order-dry-run/compound-add-order/latest")

    assert response.status_code == 200
    assert response.json()["status"] == STATUS_BLOCKED
    assert response.json()["report_kind"] == COMPOUND_ADD_REPORT_KIND
    assert response.json()["broker_touched"] is False
    assert latest.status_code == 200
    assert latest.json()["status"] == STATUS_BLOCKED
    assert latest.json()["latest_audit"]["order_id"] == "route-add-1"


def test_compound_add_dispatch_handoff_route_is_read_only_status(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    _accept_live_pilot(tmp_path, monkeypatch)
    audit_path = tmp_path / "compound-route-audit.jsonl"
    review_state = tmp_path / "compound-review.json"
    review_audit = tmp_path / "compound-review-audit.jsonl"
    monkeypatch.setattr(route_module, "DEFAULT_COMPOUND_ADD_AUDIT_PATH", audit_path)
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_STATE_PATH", review_state)
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_AUDIT_PATH", review_audit)
    broker_truth = _open_live_truth()
    monkeypatch.setattr(compound_add_order_dry_run_review, "_latest_broker_truth", lambda: broker_truth)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-order-dry-run")
    client = TestClient(app)

    empty = client.get("/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff")
    assert empty.status_code == 200
    assert empty.json()["broker_touched"] is False
    assert empty.json()["dispatch_preview_only"] is True
    assert empty.json()["would_call_dispatch_if_owner_attempted"] is False

    req = _compound_request(
        broker_grade_market_truth=True,
        cas_feature_map=_compound_cas_map(),
    )
    _authorize_edge(req.to_live_order_request(), config=_authorized_live_cfg())
    dry_run = build_compound_add_order_dry_run(
        req,
        config=_authorized_live_cfg(),
        audit=LiveOrderDryRunAuditLog(audit_path),
    )
    blocked = client.get("/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "COMPOUND_ADD_HANDOFF_REVIEW_BLOCKED"
    assert blocked.json()["intent"]["ai_action"] == "COMPOUND_ADD"
    assert blocked.json()["order_id"] == req.add_order_id
    assert blocked.json()["broker_touched"] is False

    compound_add_order_dry_run_review.accept_compound_add_order_dry_run_review(
        notes="Owner accepted exact compound add for handoff status.",
        confirm_owner_accept=True,
        dry_run_audit=dry_run["audit"],
        broker_truth_report=broker_truth,
        state_path=review_state,
        audit_path=review_audit,
    )
    ready = client.get("/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff")
    assert ready.status_code == 200
    assert ready.json()["status"] == "COMPOUND_ADD_HANDOFF_REVIEW_READY"
    assert ready.json()["compound_add_dry_run_review_clear_for_dispatch"] is True
    assert ready.json()["would_call_dispatch_if_owner_attempted"] is True
    assert ready.json()["dispatched_to_bridge"] is False
    assert ready.json()["broker_touched"] is False


def test_live_handoff_confirm_helper_requires_typed_phrase(monkeypatch):
    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda capability: capability == "live_trading")

    pending = route_module._live_handoff_confirm_required(
        confirm=True,
        confirm_phrase="",
        payload={"report_kind": "unit", "owner_dispatch_confirmed": True},
        detail="unit live handoff",
    )
    assert pending is not None
    assert pending["status"] == "CONFIRM_REQUIRED"
    assert pending["need_confirmation"] == route_module.LIVE_HANDOFF_CONFIRM_PHRASE

    released = route_module._live_handoff_confirm_required(
        confirm=True,
        confirm_phrase=route_module.LIVE_HANDOFF_CONFIRM_PHRASE,
        payload={"report_kind": "unit", "owner_dispatch_confirmed": True},
        detail="unit live handoff",
    )
    assert released is None


def test_compound_add_dispatch_handoff_dispatch_route_requires_confirm_and_current_accept(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    _accept_live_pilot(tmp_path, monkeypatch)
    audit_path = tmp_path / "compound-route-audit.jsonl"
    review_state = tmp_path / "compound-review.json"
    review_audit = tmp_path / "compound-review-audit.jsonl"
    monkeypatch.setattr(route_module, "DEFAULT_COMPOUND_ADD_AUDIT_PATH", audit_path)
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_STATE_PATH", review_state)
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_AUDIT_PATH", review_audit)
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_STATE_PATH", tmp_path / "order-attempts.json")
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_AUDIT_PATH", tmp_path / "order-attempts-audit.jsonl")
    broker_truth = _open_live_truth()
    monkeypatch.setattr(compound_add_order_dry_run_review, "_latest_broker_truth", lambda: broker_truth)
    bridge = _FakePaperBridge()
    monkeypatch.setattr(route_module, "select_bridge", lambda config=None: bridge)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-order-dry-run")
    client = TestClient(app)

    no_confirm = client.post(
        "/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff/dispatch",
        json={"notes": "missing explicit dispatch confirmation"},
    )
    assert no_confirm.status_code == 400
    assert "confirm_owner_dispatch=true" in no_confirm.json()["detail"]
    assert bridge.calls == []

    req = _compound_request(
        broker_grade_market_truth=True,
        cas_feature_map=_compound_cas_map(),
    )
    _authorize_edge(req.to_live_order_request(), config=_authorized_live_cfg())
    dry_run = build_compound_add_order_dry_run(
        req,
        config=_authorized_live_cfg(),
        audit=LiveOrderDryRunAuditLog(audit_path),
    )
    blocked = client.post(
        "/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff/dispatch",
        json={"confirm_owner_dispatch": True, "notes": "owner requested handoff"},
    )
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "COMPOUND_ADD_HANDOFF_REVIEW_BLOCKED"
    assert blocked.json()["dispatch_attempted"] is False
    assert blocked.json()["broker_touched"] is False
    assert bridge.calls == []

    compound_add_order_dry_run_review.accept_compound_add_order_dry_run_review(
        notes="Owner accepted exact compound add before dispatch handoff.",
        confirm_owner_accept=True,
        dry_run_audit=dry_run["audit"],
        broker_truth_report=broker_truth,
        state_path=review_state,
        audit_path=review_audit,
    )

    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda capability: True)
    confirm_required = client.post(
        "/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff/dispatch",
        json={"confirm_owner_dispatch": True, "notes": "live posture needs second confirm"},
    )
    assert confirm_required.status_code == 200
    assert confirm_required.json()["status"] == "CONFIRM_REQUIRED"
    assert confirm_required.json()["need_confirmation"] == route_module.LIVE_HANDOFF_CONFIRM_PHRASE
    assert confirm_required.json()["dispatch_attempted"] is False
    assert confirm_required.json()["broker_touched"] is False
    assert bridge.calls == []

    boolean_only = client.post(
        "/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff/dispatch?confirm=true",
        json={"confirm_owner_dispatch": True, "notes": "boolean-only live posture confirm"},
    )
    assert boolean_only.status_code == 200
    assert boolean_only.json()["status"] == "CONFIRM_REQUIRED"
    assert boolean_only.json()["need_confirmation"] == route_module.LIVE_HANDOFF_CONFIRM_PHRASE
    assert boolean_only.json()["dispatch_attempted"] is False
    assert boolean_only.json()["broker_touched"] is False
    assert bridge.calls == []

    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda capability: False)
    dispatched = client.post(
        "/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff/dispatch",
        json={"confirm_owner_dispatch": True, "notes": "owner dispatches paper-safe handoff"},
    )
    assert dispatched.status_code == 200
    body = dispatched.json()
    assert body["status"] == "BROKER_EXECUTED"
    assert body["dispatch_attempted"] is True
    assert body["owner_dispatch_confirmed"] is True
    assert body["broker_touched"] is True
    assert body["dispatched_to_bridge"] is True
    assert body["dispatch_result"]["audit_attempt_id"]
    assert len(bridge.calls) == 1
    assert bridge.calls[0].order_id == req.add_order_id
    assert bridge.calls[0].decision_ref == req.add_decision_ref


def test_waste_entry_dispatch_handoff_status_route_requires_source_and_owner_accept(tmp_path, monkeypatch):
    audit_path = tmp_path / "waste-entry-dry-run-audit.jsonl"
    review_state = tmp_path / "waste-entry-review.json"
    review_audit = tmp_path / "waste-entry-review-audit.jsonl"
    monkeypatch.setattr(route_module, "DEFAULT_AUDIT_PATH", audit_path)
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_STATE_PATH", review_state)
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_AUDIT_PATH", review_audit)
    broker_truth = _clean_live_truth()
    monkeypatch.setattr(live_order_dry_run_review, "_latest_broker_truth", lambda: broker_truth)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-order-dry-run")
    client = TestClient(app)

    empty = client.get("/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff")
    assert empty.status_code == 200
    assert empty.json()["status"] == "BLOCKED_WASTE_ENTRY_DISPATCH_HANDOFF"
    assert empty.json()["broker_touched"] is False
    assert empty.json()["would_call_dispatch_if_owner_attempted"] is False

    _passing_waste_entry_dry_run(tmp_path, monkeypatch, audit_path)
    blocked = client.get("/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "WASTE_ENTRY_HANDOFF_REVIEW_BLOCKED"
    assert blocked.json()["intent"]["ai_action"] == "WASTE_ENTRY"
    assert blocked.json()["broker_touched"] is False
    assert blocked.json()["dispatch_preview_only"] is True

    latest = LiveOrderDryRunAuditLog(audit_path).latest()
    accepted = live_order_dry_run_review.accept_live_order_dry_run_review(
        notes="Owner accepted exact WASTE entry before handoff.",
        confirm_owner_accept=True,
        dry_run_audit=latest or {},
        broker_truth_report=broker_truth,
        state_path=review_state,
        audit_path=review_audit,
    )
    assert accepted["dry_run_review_clear_for_live"] is True

    ready = client.get("/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff")
    assert ready.status_code == 200
    assert ready.json()["status"] == "WASTE_ENTRY_HANDOFF_REVIEW_READY"
    assert ready.json()["dry_run_review_clear_for_live"] is True
    assert ready.json()["would_call_dispatch_if_owner_attempted"] is True
    assert ready.json()["dispatched_to_bridge"] is False
    assert ready.json()["broker_touched"] is False


def test_waste_entry_pilot_promotion_route_requires_owner_review_pilot_and_recovery(tmp_path, monkeypatch):
    audit_path = tmp_path / "waste-entry-pilot-dry-run-audit.jsonl"
    review_state = tmp_path / "waste-entry-pilot-review.json"
    review_audit = tmp_path / "waste-entry-pilot-review-audit.jsonl"
    monkeypatch.setattr(route_module, "DEFAULT_AUDIT_PATH", audit_path)
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_STATE_PATH", review_state)
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_AUDIT_PATH", review_audit)
    monkeypatch.setattr(live_recovery, "DEFAULT_STATE_PATH", tmp_path / "live-recovery.json")
    monkeypatch.setattr(live_recovery, "DEFAULT_AUDIT_PATH", tmp_path / "live-recovery-audit.jsonl")
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_STATE_PATH", tmp_path / "order-attempts.json")
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_AUDIT_PATH", tmp_path / "order-attempts-audit.jsonl")
    broker_truth = _clean_live_truth()
    monkeypatch.setattr(live_order_dry_run_review, "_latest_broker_truth", lambda: broker_truth)
    monkeypatch.setattr(live_recovery, "_latest_broker_truth", lambda: broker_truth)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-order-dry-run")
    client = TestClient(app)

    empty = client.get("/api/forex/live-order-dry-run/waste-entry-order/pilot-promotion")
    assert empty.status_code == 200
    assert empty.json()["status"] == "WASTE_PILOT_BLOCKED"
    assert empty.json()["ready_for_pilot_sequence"] is False
    assert empty.json()["broker_touched"] is False
    assert empty.json()["dispatch_attempted"] is False

    dry_run = _passing_waste_entry_dry_run(tmp_path, monkeypatch, audit_path)
    blocked = client.get("/api/forex/live-order-dry-run/waste-entry-order/pilot-promotion")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "WASTE_PILOT_BLOCKED"
    assert "owner_dry_run_accept_current" in blocked.json()["missing_requirements"]
    assert blocked.json()["broker_touched"] is False

    live_order_dry_run_review.accept_live_order_dry_run_review(
        notes="Owner accepted exact WASTE entry before pilot promotion.",
        confirm_owner_accept=True,
        dry_run_audit=dry_run["audit"],
        broker_truth_report=broker_truth,
        state_path=review_state,
        audit_path=review_audit,
    )

    ready = client.get("/api/forex/live-order-dry-run/waste-entry-order/pilot-promotion")
    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "WASTE_PILOT_READY"
    assert body["ready_for_pilot_sequence"] is True
    assert body["symbol"] == "EUR/USD"
    assert body["direction"] == "LONG"
    assert body["entry_pair_count"] == 24
    assert body["broker_touched"] is False
    assert body["dispatched_to_bridge"] is False
    assert body["dispatch_attempted"] is False
    assert all(check["status"] == "OK" for check in body["checks"])


def test_waste_entry_dispatch_handoff_dispatch_route_requires_confirm_and_current_accept(tmp_path, monkeypatch):
    audit_path = tmp_path / "waste-entry-dispatch-audit.jsonl"
    review_state = tmp_path / "waste-entry-dispatch-review.json"
    review_audit = tmp_path / "waste-entry-dispatch-review-audit.jsonl"
    monkeypatch.setattr(route_module, "DEFAULT_AUDIT_PATH", audit_path)
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_STATE_PATH", review_state)
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_AUDIT_PATH", review_audit)
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_STATE_PATH", tmp_path / "order-attempts.json")
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_AUDIT_PATH", tmp_path / "order-attempts-audit.jsonl")
    broker_truth = _clean_live_truth()
    monkeypatch.setattr(live_order_dry_run_review, "_latest_broker_truth", lambda: broker_truth)
    bridge = _FakePaperBridge()
    monkeypatch.setattr(route_module, "select_bridge", lambda config=None: bridge)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-order-dry-run")
    client = TestClient(app)

    no_confirm = client.post(
        "/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff/dispatch",
        json={"notes": "missing explicit owner dispatch confirmation"},
    )
    assert no_confirm.status_code == 400
    assert "confirm_owner_dispatch=true" in no_confirm.json()["detail"]
    assert bridge.calls == []

    dry_run = _passing_waste_entry_dry_run(tmp_path, monkeypatch, audit_path)
    blocked = client.post(
        "/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff/dispatch",
        json={"confirm_owner_dispatch": True, "notes": "owner requested handoff"},
    )
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "WASTE_ENTRY_HANDOFF_REVIEW_BLOCKED"
    assert blocked.json()["dispatch_attempted"] is False
    assert blocked.json()["broker_touched"] is False
    assert bridge.calls == []

    live_order_dry_run_review.accept_live_order_dry_run_review(
        notes="Owner accepted exact WASTE entry before dispatch handoff.",
        confirm_owner_accept=True,
        dry_run_audit=dry_run["audit"],
        broker_truth_report=broker_truth,
        state_path=review_state,
        audit_path=review_audit,
    )

    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda capability: True)
    confirm_required = client.post(
        "/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff/dispatch",
        json={"confirm_owner_dispatch": True, "notes": "live posture needs second confirm"},
    )
    assert confirm_required.status_code == 200
    assert confirm_required.json()["status"] == "CONFIRM_REQUIRED"
    assert confirm_required.json()["need_confirmation"] == route_module.LIVE_HANDOFF_CONFIRM_PHRASE
    assert confirm_required.json()["dispatch_attempted"] is False
    assert confirm_required.json()["broker_touched"] is False
    assert bridge.calls == []

    boolean_only = client.post(
        "/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff/dispatch?confirm=true",
        json={"confirm_owner_dispatch": True, "notes": "boolean-only live posture confirm"},
    )
    assert boolean_only.status_code == 200
    assert boolean_only.json()["status"] == "CONFIRM_REQUIRED"
    assert boolean_only.json()["need_confirmation"] == route_module.LIVE_HANDOFF_CONFIRM_PHRASE
    assert boolean_only.json()["dispatch_attempted"] is False
    assert boolean_only.json()["broker_touched"] is False
    assert bridge.calls == []

    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda capability: False)
    dispatched = client.post(
        "/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff/dispatch",
        json={"confirm_owner_dispatch": True, "notes": "owner dispatches paper-safe WASTE handoff"},
    )
    assert dispatched.status_code == 200
    body = dispatched.json()
    assert body["status"] == "BROKER_EXECUTED"
    assert body["dispatch_attempted"] is True
    assert body["owner_dispatch_confirmed"] is True
    assert body["broker_touched"] is True
    assert body["dispatched_to_bridge"] is True
    assert body["dispatch_result"]["audit_attempt_id"]
    assert body["handoff_status"]["status"] == "WASTE_ENTRY_HANDOFF_REVIEW_READY"
    assert len(bridge.calls) == 1
    assert bridge.calls[0].order_id == "dry-run-1"
    assert bridge.calls[0].decision_ref == "dry-ref-1"


def test_live_order_dry_run_route_is_registered_on_api_server(tmp_path, monkeypatch):
    from api.server import app

    monkeypatch.setattr(route_module, "DEFAULT_AUDIT_PATH", tmp_path / "server-dry-run-audit.jsonl")
    client = TestClient(app)

    response = client.post(
        "/api/forex/live-order-dry-run/order",
        json={
            "order_id": "server-dry-1",
            "symbol": "EUR/USD",
            "direction": "LONG",
            "volume": 0.01,
            "price": 1.1000,
            "stop_loss": 1.0900,
            "take_profit": 1.1100,
        },
    )

    assert response.status_code == 200
    assert response.json()["report_kind"] == "cas_forex_live_order_dry_run"
    assert response.json()["broker_touched"] is False


def test_dry_run_review_accepts_current_pass_fingerprint(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    _accept_live_pilot(tmp_path, monkeypatch)
    req = _request()
    _authorize_edge(req, config=_authorized_live_cfg())
    dry_run = build_live_order_dry_run(
        req,
        config=_authorized_live_cfg(),
        audit=LiveOrderDryRunAuditLog(tmp_path / "dry-run-audit.jsonl"),
    )

    accepted = live_order_dry_run_review.accept_live_order_dry_run_review(
        notes="Owner reviewed passing dry-run before tiny live pilot.",
        confirm_owner_accept=True,
        dry_run_audit=dry_run["audit"],
        broker_truth_report=_clean_live_truth(),
        state_path=tmp_path / "review.json",
        audit_path=tmp_path / "review-audit.jsonl",
    )

    assert accepted["owner_review_status"] == live_order_dry_run_review.STATUS_ACCEPT
    assert accepted["dry_run_review_clear_for_live"] is True
    assert accepted["accepted_fingerprint"] == accepted["current_fingerprint"]
    assert (tmp_path / "review-audit.jsonl").exists()

    changed = live_order_dry_run_review.build_live_order_dry_run_review(
        dry_run_audit={
            **dry_run["audit"],
            "payload": {**dry_run["audit"]["payload"], "order_id": "different-order"},
        },
        broker_truth_report=_clean_live_truth(),
        state_path=tmp_path / "review.json",
    )
    assert changed["dry_run_review_clear_for_live"] is False


def test_dry_run_review_rejects_accept_without_pass(tmp_path):
    blocked_audit = {
        "audit_id": "blocked",
        "timestamp": "2026-06-30T12:00:00+00:00",
        "status": STATUS_BLOCKED,
        "payload": {
            "report_kind": "cas_forex_live_order_dry_run",
            "generated_at": "2026-06-30T12:00:00+00:00",
            "status": STATUS_BLOCKED,
            "broker_touched": False,
            "checks": [],
        },
    }

    with pytest.raises(live_order_dry_run_review.LiveOrderDryRunReviewError):
        live_order_dry_run_review.accept_live_order_dry_run_review(
            confirm_owner_accept=True,
            dry_run_audit=blocked_audit,
            broker_truth_report=_clean_live_truth(),
            state_path=tmp_path / "review.json",
            audit_path=tmp_path / "review-audit.jsonl",
        )


def test_dry_run_review_rejects_wrong_live_account_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    _accept_live_pilot(tmp_path, monkeypatch)
    req = _request()
    _authorize_edge(req, config=_authorized_live_cfg())
    dry_run = build_live_order_dry_run(
        req,
        config=_authorized_live_cfg(),
        audit=LiveOrderDryRunAuditLog(tmp_path / "wrong-account-dry-run.jsonl"),
    )
    wrong_truth = {
        **_clean_live_truth(),
        "mt5_account": 777777,
        "mt5_account_identity_matches_config": False,
    }

    with pytest.raises(live_order_dry_run_review.LiveOrderDryRunReviewError):
        live_order_dry_run_review.accept_live_order_dry_run_review(
            confirm_owner_accept=True,
            dry_run_audit=dry_run["audit"],
            broker_truth_report=wrong_truth,
            state_path=tmp_path / "wrong-account-review.json",
            audit_path=tmp_path / "wrong-account-review-audit.jsonl",
        )


def test_dry_run_review_route_requires_confirm(tmp_path, monkeypatch):
    monkeypatch.setattr(route_module, "DEFAULT_AUDIT_PATH", tmp_path / "dry-route-audit.jsonl")
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_STATE_PATH", tmp_path / "review.json")
    monkeypatch.setattr(live_order_dry_run_review, "DEFAULT_AUDIT_PATH", tmp_path / "review-audit.jsonl")
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-order-dry-run")
    client = TestClient(app)

    response = client.post("/api/forex/live-order-dry-run/review/accept", json={"notes": "not confirmed"})

    assert response.status_code == 400
    assert "confirm_owner_accept=true" in response.json()["detail"]


def test_dry_run_review_accept_route_invalidates_dependent_caches(monkeypatch):
    captured: dict[str, object] = {}

    def fake_accept_live_order_dry_run_review(*, notes: str, confirm_owner_accept: bool):
        captured["notes"] = notes
        captured["confirm_owner_accept"] = confirm_owner_accept
        return {
            "report_kind": "cas_forex_live_order_dry_run_review",
            "owner_review_status": "ACCEPT",
            "dry_run_review_clear_for_live": True,
        }

    def fake_invalidate_live_money_gate_caches(*keys: str):
        captured["invalidated"] = keys

    monkeypatch.setattr(
        route_module,
        "accept_live_order_dry_run_review",
        fake_accept_live_order_dry_run_review,
    )
    monkeypatch.setattr(
        route_module,
        "invalidate_live_money_gate_caches",
        fake_invalidate_live_money_gate_caches,
    )

    body = route_module.LiveOrderDryRunReviewAccept(notes="owner accepted latest dry run")
    response = asyncio.run(
        route_module.post_live_order_dry_run_review_accept(
            body,
            confirm_owner_accept=True,
        )
    )

    assert response["owner_review_status"] == "ACCEPT"
    assert captured["notes"] == "owner accepted latest dry run"
    assert captured["confirm_owner_accept"] is True
    assert captured["invalidated"] == ()


def test_compound_add_dry_run_review_route_requires_confirm(tmp_path, monkeypatch):
    monkeypatch.setattr(route_module, "DEFAULT_COMPOUND_ADD_AUDIT_PATH", tmp_path / "compound-route-audit.jsonl")
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_STATE_PATH", tmp_path / "compound-review.json")
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_AUDIT_PATH", tmp_path / "compound-review-audit.jsonl")
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-order-dry-run")
    client = TestClient(app)

    response = client.post(
        "/api/forex/live-order-dry-run/compound-add-order/review/accept",
        json={"notes": "not confirmed"},
    )

    assert response.status_code == 400
    assert "confirm_owner_accept=true" in response.json()["detail"]
