from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import broker_emergency as broker_emergency_route
from cas_forex.broker_emergency import build_broker_emergency_status, run_broker_emergency_action
from cas_forex.emergency_controls import build_emergency_controls_report


REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeBridge:
    def __init__(self, *, connected: bool = True) -> None:
        self.connected = connected
        self.close_calls: list[int] = []
        self.cancel_calls: list[int] = []
        self.positions = [
            {
                "ticket": 101,
                "symbol": "US30",
                "type": "BUY",
                "volume": 0.01,
                "open_price": 100.0,
                "current_price": 105.0,
                "profit": 5.0,
                "comment": "CAS_WIN",
            },
            {
                "ticket": 102,
                "symbol": "NAS100",
                "type": "BUY",
                "volume": 0.01,
                "open_price": 100.0,
                "current_price": 95.0,
                "profit": -5.0,
                "comment": "CAS_LOSS",
            },
        ]
        self.pending = [
            {
                "ticket": 201,
                "symbol": "EURUSD",
                "type": "BUY_LIMIT",
                "volume": 0.01,
                "price_open": 1.08,
                "comment": "CAS_PENDING",
            }
        ]

    def is_connected(self) -> bool:
        return self.connected

    def will_execute_real_order(self) -> bool:
        return False

    def get_all_open_positions(self) -> list[dict[str, Any]]:
        return list(self.positions)

    def get_pending_orders(self) -> list[dict[str, Any]]:
        return list(self.pending)

    def close_position(self, ticket: int) -> bool:
        self.close_calls.append(ticket)
        self.positions = [row for row in self.positions if row["ticket"] != ticket]
        return True

    def cancel_pending_order(self, ticket: int) -> bool:
        self.cancel_calls.append(ticket)
        self.pending = [row for row in self.pending if row["ticket"] != ticket]
        return True


def test_broker_emergency_status_lists_positions_and_pending_orders():
    bridge = FakeBridge()

    status = build_broker_emergency_status(bridge=bridge)

    assert status["report_kind"] == "cas_forex_broker_emergency_status"
    assert status["status"] == "READY"
    assert status["open_position_count"] == 2
    assert status["pending_order_count"] == 1
    assert "close_all_positions" in status["supported_actions"]


def test_broker_emergency_close_all_is_dry_run_by_default(tmp_path):
    bridge = FakeBridge()

    result = run_broker_emergency_action(
        "close_all_positions",
        bridge=bridge,
        audit_path=tmp_path / "broker-emergency.jsonl",
    )

    assert result["status"] == "DRY_RUN"
    assert result["selected_position_count"] == 2
    assert result["broker_touched"] is False
    assert bridge.close_calls == []
    assert (tmp_path / "broker-emergency.jsonl").exists()


def test_broker_emergency_requires_confirmation_before_mutation(tmp_path):
    bridge = FakeBridge()

    result = run_broker_emergency_action(
        "close_all_positions",
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=False,
        audit_path=tmp_path / "broker-emergency.jsonl",
    )

    assert result["status"] == "CONFIRM_REQUIRED"
    assert result["broker_order_send_attempted"] is False
    assert bridge.close_calls == []


def test_broker_emergency_confirmed_close_and_cancel_mutate_selected_rows(tmp_path):
    bridge = FakeBridge()

    close_result = run_broker_emergency_action(
        "close_profitable_positions",
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=True,
        audit_path=tmp_path / "broker-emergency.jsonl",
    )
    cancel_result = run_broker_emergency_action(
        "cancel_pending_orders",
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=True,
        audit_path=tmp_path / "broker-emergency.jsonl",
    )

    assert close_result["status"] == "EXECUTED"
    assert bridge.close_calls == [101]
    assert close_result["closed_positions"][0]["action_status"] == "CLOSED"
    assert cancel_result["status"] == "EXECUTED"
    assert bridge.cancel_calls == [201]
    assert cancel_result["cancelled_orders"][0]["action_status"] == "CANCELLED"


def test_broker_emergency_disconnected_bridge_does_not_mutate(tmp_path):
    bridge = FakeBridge(connected=False)

    result = run_broker_emergency_action(
        "close_all_positions",
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=True,
        audit_path=tmp_path / "broker-emergency.jsonl",
    )

    assert result["status"] == "MT5_NOT_CONNECTED"
    assert result["broker_touched"] is False
    assert bridge.close_calls == []


def test_broker_emergency_routes_delegate_with_confirm_flags(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_run(action, *, dry_run, confirm_owner_action, reason):
        captured.update(
            {
                "action": action,
                "dry_run": dry_run,
                "confirm_owner_action": confirm_owner_action,
                "reason": reason,
            }
        )
        return {"report_kind": "cas_forex_broker_emergency_action", "status": "EXECUTED"}

    monkeypatch.setattr(broker_emergency_route, "run_broker_emergency_action", fake_run)

    blocked = asyncio.run(
        broker_emergency_route.close_all_positions(
            broker_emergency_route.BrokerEmergencyRequest(reason="OWNER_TEST"),
            dry_run=False,
            confirm_owner_action=True,
        )
    )

    assert blocked["status"] == "CONFIRM_REQUIRED"
    assert blocked["need_confirmation"] == broker_emergency_route.BROKER_EMERGENCY_CONFIRM_PHRASE
    assert captured == {}

    body = asyncio.run(
        broker_emergency_route.close_all_positions(
            broker_emergency_route.BrokerEmergencyRequest(reason="OWNER_TEST"),
            dry_run=False,
            confirm_owner_action=True,
            confirm_phrase=broker_emergency_route.BROKER_EMERGENCY_CONFIRM_PHRASE,
        )
    )

    assert body["status"] == "EXECUTED"
    assert captured == {
        "action": "close_all_positions",
        "dry_run": False,
        "confirm_owner_action": True,
        "reason": "OWNER_TEST",
    }


def test_broker_emergency_routes_are_registered_and_coverage_report_sees_them():
    report = build_emergency_controls_report(REPO_ROOT)
    controls = {control["key"]: control for control in report["controls"]}

    assert controls["broker_close_all_positions"]["status"] == "OK"
    assert controls["broker_cancel_pending_orders"]["status"] == "OK"
    assert controls["selective_close_profitable_positions"]["status"] == "OK"
    assert controls["selective_close_losing_positions"]["status"] == "OK"
    assert api_server.app is not None
