"""Tests for the /order-dispatch route — HTTP face of the gated dispatch loop."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import order_dispatch as route_module
from cas_forex.order_attempt_audit import OrderAttemptAuditStore
from cas_forex.time_utils import utc_now


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/order-dispatch")
    return TestClient(app)


def _order() -> SimpleNamespace:
    return SimpleNamespace(
        order_id="live-attempt-1",
        decision_ref="live-attempt-ref-1",
        symbol="EUR/USD",
        direction="LONG",
        order_type="MARKET",
        volume=0.01,
        price=0.0,
        stop_loss=1.0900,
        take_profit=1.1100,
        comment="CAS_FOREX_AUTO",
        magic_number=20260601,
        created_at=utc_now(),
    )


def _clean_broker_truth() -> dict:
    return {
        "report_kind": "cas_forex_broker_truth_monitor",
        "generated_at": utc_now().isoformat(),
        "overall_status": "RECONCILED",
        "mt5_connected": True,
        "mt5_is_demo": False,
        "mt5_open_position_count": 0,
        "terminal_unmatched_open_position_count": 0,
        "terminal_pending_receipt_count": 0,
        "terminal_receipt_mismatch_count": 0,
    }


def test_latest_returns_no_cycle_when_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(route_module, "DEFAULT_OUTPUT_DIR", tmp_path)
    resp = _client().get("/api/forex/order-dispatch/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_dispatch_cycle_yet"


def test_run_returns_gated_cycle_report(monkeypatch, tmp_path):
    # Redirect the artifact writer so the test does not touch the real evidence dir.
    monkeypatch.setattr(
        route_module,
        "write_agent_dispatch_cycle_report",
        lambda cycle, **kw: {"json": tmp_path / "report.json"},
    )
    resp = _client().post("/api/forex/order-dispatch/run")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_agent_dispatch_cycle"
    assert body["dispatch_report"]["report_kind"] == "cas_forex_order_dispatch"
    # Paper-first: live execution stays runtime-locked by default.
    assert body["dispatch_report"]["live_execution_runtime_locked"] is True
    assert "artifact_path" in body


def test_audit_route_returns_order_attempt_status(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_order_attempt_audit_status",
        lambda: {
            "report_kind": "cas_forex_order_attempt_audit",
            "generated_at": "2026-06-30T00:00:00Z",
            "attempt_count": 0,
            "real_attempt_count": 0,
            "unresolved_attempt_count": 0,
            "unresolved_real_attempt_count": 0,
            "executed_count": 0,
            "latest_attempt": None,
            "has_unresolved_real_attempt": False,
            "claim_boundary": "test",
            "next_action": "No unresolved real order attempts are open.",
        },
    )
    resp = _client().get("/api/forex/order-dispatch/audit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_order_attempt_audit"
    assert body["has_unresolved_real_attempt"] is False


def test_recovery_packet_route_classifies_unresolved_attempts_and_requires_clean_truth(monkeypatch, tmp_path):
    store = OrderAttemptAuditStore(
        state_path=tmp_path / "attempts.json",
        audit_path=tmp_path / "attempts-audit.jsonl",
    )
    started = store.record_started(
        _order(),
        proposed_intent={"symbol": "EUR/USD", "direction": "LONG", "lots": 0.01},
        mode="LIVE",
        is_real_attempt=True,
        bridge_name="_FakeRealBridge",
        source="test_crash_window",
    )
    monkeypatch.setattr(route_module, "build_order_attempt_audit_status", lambda: store.build_status())
    monkeypatch.setattr(route_module, "load_latest_broker_truth_monitor_report", _clean_broker_truth)

    resp = _client().get("/api/forex/order-dispatch/audit/recovery-packet")

    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_order_attempt_recovery_packet"
    assert body["status"] == "READY_TO_RECONCILE_UNRESOLVED_ATTEMPTS"
    assert body["can_reconcile_unresolved_attempts"] is True
    assert body["broker_touched"] is False
    assert body["attempt_finalized"] is False
    assert body["unresolved_real_attempt_count"] == 1
    assert body["synthetic_test_like_count"] == 1
    assert body["unresolved_real_attempts"][0]["attempt_id"] == started["attempt_id"]
    assert body["unresolved_real_attempts"][0]["classification_status"] == "SYNTHETIC_TEST_LIKE"

    monkeypatch.setattr(
        route_module,
        "load_latest_broker_truth_monitor_report",
        lambda: {**_clean_broker_truth(), "terminal_pending_receipt_count": 1},
    )
    blocked = _client().get("/api/forex/order-dispatch/audit/recovery-packet")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "RECOVERY_PACKET_BLOCKED"
    assert blocked.json()["can_reconcile_unresolved_attempts"] is False
    assert "position_reconciliation_clean" in blocked.json()["missing_requirements"]


def test_reconcile_unresolved_attempt_route_requires_confirm_and_clean_broker_truth(monkeypatch, tmp_path):
    store = OrderAttemptAuditStore(
        state_path=tmp_path / "attempts.json",
        audit_path=tmp_path / "attempts-audit.jsonl",
    )
    started = store.record_started(
        _order(),
        proposed_intent={"symbol": "EUR/USD", "direction": "LONG", "lots": 0.01},
        mode="LIVE",
        is_real_attempt=True,
        bridge_name="MT5Bridge",
        source="test_crash_window",
    )
    monkeypatch.setattr(route_module, "default_order_attempt_audit_store", lambda: store)
    client = _client()

    missing_confirm = client.post(
        "/api/forex/order-dispatch/audit/reconcile-unresolved",
        json={"attempt_id": started["attempt_id"], "broker_truth_report": _clean_broker_truth()},
    )
    assert missing_confirm.status_code == 400
    assert "confirm_owner_reconcile=true" in missing_confirm.json()["detail"]
    assert store.build_status()["unresolved_real_attempt_count"] == 1
    assert store.build_status()["unresolved_real_attempts"][0]["attempt_id"] == started["attempt_id"]

    dirty_truth = {**_clean_broker_truth(), "terminal_unmatched_open_position_count": 1}
    dirty = client.post(
        "/api/forex/order-dispatch/audit/reconcile-unresolved?confirm_owner_reconcile=true",
        json={"attempt_id": started["attempt_id"], "broker_truth_report": dirty_truth},
    )
    assert dirty.status_code == 400
    assert "broker_truth_reconciled" in dirty.json()["detail"]
    assert store.build_status()["unresolved_real_attempt_count"] == 1

    reconciled = client.post(
        "/api/forex/order-dispatch/audit/reconcile-unresolved?confirm_owner_reconcile=true",
        json={
            "attempt_id": started["attempt_id"],
            "broker_truth_report": _clean_broker_truth(),
            "notes": "Owner matched terminal/broker truth after restart.",
        },
    )
    assert reconciled.status_code == 200
    body = reconciled.json()
    assert body["action"] == "ORDER_ATTEMPT_RECOVERY_RECONCILED"
    assert body["unresolved_real_attempt_count"] == 0
    assert body["unresolved_real_attempts"] == []
    assert body["has_unresolved_real_attempt"] is False
    assert body["reconciled_attempt"]["result_status"] == "RECOVERY_RECONCILED"
    assert body["reconciled_attempt"]["bridge_touch_unknown"] is True
