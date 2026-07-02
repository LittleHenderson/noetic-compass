"""Broker-truth recovery packet coverage."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import broker_truth_monitor as route_module
from cas_forex.account_reconciliation import RECONCILED, RECONCILED_WITH_WARNINGS
from cas_forex.broker_truth_recovery_packet import build_broker_truth_recovery_packet


def _monitor_state(
    *,
    ready_for_live: bool = False,
    overall_status: str = RECONCILED_WITH_WARNINGS,
    mt5_connected: bool = True,
    mt5_is_demo: bool = True,
    pending: int = 28,
    unmatched: int = 28,
    account_snapshot: bool = False,
) -> dict:
    return {
        "report_kind": "cas_forex_broker_truth_monitor_status",
        "running": False,
        "monitor_status": "BROKER_TRUTH_RECONCILED_WITH_WARNINGS",
        "ready_for_live": ready_for_live,
        "latest_report": {
            "report_kind": "cas_forex_broker_truth_monitor",
            "generated_at": "2026-06-30T00:00:00+00:00",
            "monitor_status": "BROKER_TRUTH_RECONCILED_WITH_WARNINGS",
            "overall_status": overall_status,
            "mt5_connected": mt5_connected,
            "mt5_is_demo": mt5_is_demo,
            "mt5_open_position_count": 0,
            "terminal_reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL",
            "terminal_pending_receipt_count": pending,
            "terminal_unmatched_open_position_count": unmatched,
            "terminal_receipt_mismatch_count": 0,
            "terminal_account_snapshot_present": account_snapshot,
            "checks": [],
            "claim_boundary": "Broker-truth monitor is read-only reconciliation and does not place orders.",
            "next_action": "Fix broker truth.",
        },
    }


def test_broker_truth_recovery_packet_blocks_demo_and_dirty_terminal_truth():
    packet = build_broker_truth_recovery_packet(monitor_state=_monitor_state())

    assert packet["report_kind"] == "cas_forex_broker_truth_recovery_packet"
    assert packet["status"] == "BROKER_TRUTH_RECOVERY_BLOCKED"
    assert packet["broker_truth_clear_for_live_recovery"] is False
    assert packet["broker_touched"] is False
    assert packet["live_order_attempted"] is False
    assert packet["attempt_finalized"] is False
    assert packet["money_moved"] is False
    blocker_ids = {blocker["blocker_id"] for blocker in packet["blockers"]}
    assert "mt5_live_account_visible" in blocker_ids
    assert "terminal_pending_receipts_clear" in blocker_ids
    assert "terminal_open_positions_match" in blocker_ids


def test_broker_truth_recovery_packet_clears_only_fully_live_reconciled_truth():
    packet = build_broker_truth_recovery_packet(
        monitor_state=_monitor_state(
            ready_for_live=True,
            overall_status=RECONCILED,
            mt5_is_demo=False,
            pending=0,
            unmatched=0,
            account_snapshot=True,
        )
    )

    assert packet["status"] == "BROKER_TRUTH_RECOVERY_CLEAR"
    assert packet["broker_truth_clear_for_live_recovery"] is True
    assert packet["blockers"] == []


def test_broker_truth_recovery_packet_route(monkeypatch):
    monkeypatch.setattr(route_module, "monitor_status", lambda: _monitor_state())
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/broker-truth-monitor")
    client = TestClient(app)

    response = client.get("/api/forex/broker-truth-monitor/recovery-packet")

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_broker_truth_recovery_packet"
    assert body["status"] == "BROKER_TRUTH_RECOVERY_BLOCKED"
    assert body["broker_touched"] is False
    assert body["money_moved"] is False
