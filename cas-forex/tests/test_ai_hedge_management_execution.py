from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from api import server as api_server
from api.routes import ai_hedge_management as ai_hedge_management_route
from cas_forex.ai_hedge_management_execution import (
    latest_ai_hedge_management_execution,
    run_ai_hedge_management_action,
)
from cas_forex.execution_guard import require_trade_management_action_ready
from cas_forex.schemas.order import OrderOutcome, OrderStatus


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_management_executor_has_no_direct_broker_modify_or_close_bypass():
    source = (REPO_ROOT / "cas_forex" / "ai_hedge_management_execution.py").read_text(
        encoding="utf-8"
    )

    assert "order_dispatch.dispatch_trade_management_action" in source
    assert 'getattr(bridge, "modify_position"' not in source
    assert 'getattr(bridge, "close_position"' not in source


class FakeBridge:
    def __init__(self, *, real: bool = False) -> None:
        self.real = real
        self.modify_calls: list[dict[str, Any]] = []
        self.close_calls: list[dict[str, Any]] = []
        self.positions: dict[int, dict[str, Any]] = {
            123456: {
                "ticket": 123456,
                "symbol": "US30",
                "type": "BUY",
                "volume": 0.04,
                "open_price": 90.0,
                "current_price": 120.0,
                "stop_loss": 80.0,
                "take_profit": 140.0,
                "profit": 12.0,
                "comment": "CAS_TEST",
            }
        }

    def is_connected(self) -> bool:
        return True

    def will_execute_real_order(self) -> bool:
        return self.real

    def modify_position(self, ticket: int, *, stop_loss: float, take_profit: float | None = None) -> OrderOutcome:
        self.modify_calls.append(
            {"ticket": ticket, "stop_loss": stop_loss, "take_profit": take_profit}
        )
        if ticket in self.positions:
            self.positions[ticket]["stop_loss"] = stop_loss
            if take_profit is not None:
                self.positions[ticket]["take_profit"] = take_profit
        return OrderOutcome(
            order_ref=f"modify-{ticket}",
            broker_ticket=ticket,
            status=OrderStatus.EXECUTED,
        )

    def close_position(self, ticket: int, volume: float | None = None) -> bool:
        self.close_calls.append({"ticket": ticket, "volume": volume})
        if ticket in self.positions:
            if volume is None:
                del self.positions[ticket]
            else:
                self.positions[ticket]["volume"] = round(
                    max(0.0, float(self.positions[ticket]["volume"]) - float(volume)),
                    2,
                )
                if self.positions[ticket]["volume"] <= 0:
                    del self.positions[ticket]
        return True

    def get_open_positions(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.positions.values()]


def _handoff(*, method: str = "modify_position") -> dict[str, Any]:
    action = {
        "action_id": f"ai-hedge-management:pos-1:{method}",
        "status": "READY_FOR_GUARDED_EXECUTION",
        "intent": "move_stop_to_breakeven" if method == "modify_position" else "close_partial",
        "symbol": "US30",
        "position_id": "pos-1",
        "side": "LONG",
        "current_price": 120.0,
        "previous_stop_loss": 80.0,
        "previous_take_profit": 140.0,
        "broker_method": method,
        "broker_ticket": 123456,
        "volume": None if method == "modify_position" else 0.02,
        "original_volume": None if method == "modify_position" else 0.04,
        "expected_remaining_volume": None if method == "modify_position" else 0.02,
        "stop_loss": 100.0 if method == "modify_position" else None,
        "take_profit": 140.0 if method == "modify_position" else None,
        "reason": "Position management draft.",
        "risk_effect": (
            "principal_lock"
            if method == "modify_position"
            else "exposure_reducing_partial_close"
        ),
        "requires_owner_confirmation": False,
        "requires_fresh_broker_truth": True,
        "requires_execution_guard": True,
        "dry_run_only": False,
        "broker_bound_action_authorized": False,
        "broker_touched": False,
        "orders_placed": False,
    }
    return {
        "report_kind": "cas_forex_ai_hedge_management_handoff",
        "status": "READY_FOR_GUARDED_EXECUTION",
        "movement_stream_id": "movement-1",
        "price_source_status": "PROVIDER_ACTIVE",
        "management_action_count": 1,
        "blocked_action_count": 0,
        "management_actions": [action],
        "blocked_actions": [],
    }


def test_ai_hedge_management_execution_dry_run_does_not_call_bridge(tmp_path):
    bridge = FakeBridge()

    result = run_ai_hedge_management_action(
        handoff=_handoff(),
        bridge=bridge,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "DRY_RUN"
    assert result["broker_touched"] is False
    assert bridge.modify_calls == []
    assert (tmp_path / "audit.jsonl").exists()


def test_ai_hedge_management_execution_without_per_action_confirmation_calls_bridge(tmp_path, monkeypatch):
    bridge = FakeBridge()
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    result = run_ai_hedge_management_action(
        handoff=_handoff(),
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=False,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "EXECUTED_RECONCILED"
    assert result["per_action_owner_confirmation_required"] is False
    assert result["autonomous_execution_authority"] == "OWNER_DELEGATED_WITHIN_GATES"
    assert result["broker_touched"] is True
    assert bridge.modify_calls == [
        {"ticket": 123456, "stop_loss": 100.0, "take_profit": 140.0}
    ]


def test_ai_hedge_management_execution_confirmed_modify_calls_bridge(tmp_path, monkeypatch):
    bridge = FakeBridge()
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    result = run_ai_hedge_management_action(
        handoff=_handoff(),
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=False,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "EXECUTED_RECONCILED"
    assert result["broker_touched"] is True
    assert result["terminal_receipt_status"] == "RECONCILED"
    assert result["terminal_receipt"]["actual_stop_loss"] == 100.0
    assert bridge.modify_calls == [
        {"ticket": 123456, "stop_loss": 100.0, "take_profit": 140.0}
    ]
    latest = latest_ai_hedge_management_execution(tmp_path / "audit.jsonl")
    assert latest["status"] == "EXECUTED_RECONCILED"
    assert latest["broker_touched"] is True


def test_stale_modify_handoff_is_noop_when_target_already_present(tmp_path, monkeypatch):
    bridge = FakeBridge()
    bridge.positions[123456]["stop_loss"] = 100.0
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    result = run_ai_hedge_management_action(
        handoff=_handoff(),
        bridge=bridge,
        dry_run=False,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "ALREADY_APPLIED_RECONCILED"
    assert result["broker_touched"] is False
    assert bridge.modify_calls == []


def test_position_truth_preflight_blocks_take_profit_stop_smuggling(tmp_path, monkeypatch):
    bridge = FakeBridge()
    bridge.positions[123456]["stop_loss"] = 100.0
    bridge.positions[123456]["take_profit"] = 0.0
    handoff = _handoff()
    action = handoff["management_actions"][0]
    action.update(
        {
            "intent": "set_take_profit",
            "open_price": 90.0,
            "current_price": 120.0,
            "previous_stop_loss": 80.0,
            "stop_loss": 80.0,
            "previous_take_profit": 0.0,
            "take_profit": 140.0,
            "risk_effect": "bounded_profit_target",
        }
    )
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    result = run_ai_hedge_management_action(
        handoff=handoff,
        bridge=bridge,
        dry_run=False,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "POSITION_TRUTH_BLOCKED"
    assert "broker stop changed" in result["position_truth_preflight"]["reason"]
    assert bridge.modify_calls == []


def test_ai_hedge_management_execution_suppresses_repeated_one_shot_effect(tmp_path, monkeypatch):
    bridge = FakeBridge()
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )
    audit_path = tmp_path / "audit.jsonl"

    first = run_ai_hedge_management_action(
        handoff=_handoff(method="close_position"),
        bridge=bridge,
        dry_run=False,
        audit_path=audit_path,
    )
    repeated = run_ai_hedge_management_action(
        handoff=_handoff(method="close_position"),
        bridge=bridge,
        dry_run=False,
        audit_path=audit_path,
    )

    assert first["status"] == "EXECUTED_RECONCILED"
    assert repeated["status"] == "DUPLICATE_SUPPRESSED"
    assert repeated["broker_touched"] is False
    assert bridge.close_calls == [{"ticket": 123456, "volume": 0.02}]


def test_full_close_is_not_falsely_reconciled_when_ticket_remains(tmp_path, monkeypatch):
    class StickyBridge(FakeBridge):
        def close_position(self, ticket: int, volume: float | None = None) -> bool:
            self.close_calls.append({"ticket": ticket, "volume": volume})
            return True

    bridge = StickyBridge()
    handoff = _handoff(method="close_position")
    action = handoff["management_actions"][0]
    action.update(
        {
            "action_id": "ai-hedge-management:pos-1:close_full",
            "intent": "close_full",
            "volume": None,
            "expected_remaining_volume": 0.0,
            "risk_effect": "exposure_reducing_full_close",
        }
    )
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    result = run_ai_hedge_management_action(
        handoff=handoff,
        bridge=bridge,
        dry_run=False,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "EXECUTED_NOT_RECONCILED"
    assert result["terminal_receipt"]["status"] == "NOT_RECONCILED"
    assert result["terminal_receipt"]["actual_remaining_volume"] == 0.04


def test_ai_hedge_management_execution_refreshes_broker_truth_after_reconciled_execution(tmp_path, monkeypatch):
    bridge = FakeBridge()
    refresh_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    def refresh(payload):
        refresh_calls.append(dict(payload))
        return {
            "status": "REFRESH_RAN",
            "refreshed_packets": {"live_telemetry": {}, "account_reconciliation": {}},
            "error_count": 0,
        }

    result = run_ai_hedge_management_action(
        handoff=_handoff(),
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=False,
        audit_path=tmp_path / "audit.jsonl",
        post_execution_refresh=refresh,
    )

    assert result["status"] == "EXECUTED_RECONCILED"
    assert result["post_execution_refresh_status"] == "REFRESH_RAN"
    assert result["post_execution_refresh"]["error_count"] == 0
    assert refresh_calls[0]["status"] == "EXECUTED_RECONCILED"
    assert refresh_calls[0]["terminal_receipt_status"] == "RECONCILED"
    assert "post-execution broker/account refresh ran" in result["next_action"]
    latest = latest_ai_hedge_management_execution(tmp_path / "audit.jsonl")
    assert latest["latest"]["post_execution_refresh_status"] == "REFRESH_RAN"


def test_ai_hedge_management_execution_records_refresh_failure_without_hiding_receipt(tmp_path, monkeypatch):
    bridge = FakeBridge()
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    def refresh(_payload):
        raise RuntimeError("refresh backend unavailable")

    result = run_ai_hedge_management_action(
        handoff=_handoff(),
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=False,
        audit_path=tmp_path / "audit.jsonl",
        post_execution_refresh=refresh,
    )

    assert result["status"] == "EXECUTED_RECONCILED"
    assert result["terminal_receipt_status"] == "RECONCILED"
    assert result["post_execution_refresh_status"] == "REFRESH_FAILED"
    assert result["post_execution_refresh"]["detail"] == "refresh backend unavailable"
    assert "refresh failed" in result["next_action"]


def test_ai_hedge_management_execution_confirmed_partial_close_calls_bridge(tmp_path, monkeypatch):
    bridge = FakeBridge()
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    result = run_ai_hedge_management_action(
        handoff=_handoff(method="close_position"),
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=False,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "EXECUTED_RECONCILED"
    assert result["terminal_receipt_status"] == "RECONCILED"
    assert result["terminal_receipt"]["actual_remaining_volume"] == 0.02
    assert bridge.close_calls == [{"ticket": 123456, "volume": 0.02}]


def test_ai_hedge_management_execution_blocks_before_call_when_bridge_has_no_position_truth(tmp_path, monkeypatch):
    class NoReceiptBridge:
        def is_connected(self) -> bool:
            return True

        def will_execute_real_order(self) -> bool:
            return False

        def modify_position(self, ticket: int, *, stop_loss: float, take_profit: float | None = None) -> OrderOutcome:
            return OrderOutcome(
                order_ref=f"modify-{ticket}",
                broker_ticket=ticket,
                status=OrderStatus.EXECUTED,
            )

    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    result = run_ai_hedge_management_action(
        handoff=_handoff(),
        bridge=NoReceiptBridge(),
        dry_run=False,
        confirm_owner_action=False,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "POSITION_TRUTH_BLOCKED"
    assert result["broker_touched"] is False
    assert "get_all_open_positions" in result["position_truth_preflight"]["reason"]


def test_ai_hedge_management_execution_reports_not_reconciled_when_stop_does_not_move(tmp_path, monkeypatch):
    class StaleReceiptBridge(FakeBridge):
        def modify_position(self, ticket: int, *, stop_loss: float, take_profit: float | None = None) -> OrderOutcome:
            self.modify_calls.append(
                {"ticket": ticket, "stop_loss": stop_loss, "take_profit": take_profit}
            )
            return OrderOutcome(
                order_ref=f"modify-{ticket}",
                broker_ticket=ticket,
                status=OrderStatus.EXECUTED,
            )

    bridge = StaleReceiptBridge()
    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: {"status": "ACCEPT"},
    )

    result = run_ai_hedge_management_action(
        handoff=_handoff(),
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=False,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "EXECUTED_NOT_RECONCILED"
    assert result["terminal_receipt_status"] == "NOT_RECONCILED"
    assert result["terminal_receipt"]["actual_stop_loss"] == 80.0


def test_ai_hedge_management_execution_blocks_when_guard_blocks(tmp_path, monkeypatch):
    bridge = FakeBridge(real=True)

    def fake_guard(action, config=None, bridge=None):
        raise PermissionError("fresh broker truth required")

    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        fake_guard,
    )

    result = run_ai_hedge_management_action(
        handoff=_handoff(),
        bridge=bridge,
        dry_run=False,
        confirm_owner_action=False,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "EXECUTION_GUARD_BLOCKED"
    assert result["broker_touched"] is False
    assert bridge.modify_calls == []
    assert result["execution_guard"]["detail"] == "fresh broker truth required"


def test_trade_management_guard_requires_live_gate_and_broker_truth_for_real_bridge(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        "cas_forex.runtime_gates.require_authorized",
        lambda capability, config=None: calls.append(f"gate:{capability}"),
    )
    monkeypatch.setattr(
        "cas_forex.execution_guard._require_fresh_broker_truth_for_real_dispatch",
        lambda: calls.append("fresh_broker_truth"),
    )

    report = require_trade_management_action_ready(
        {
            "broker_method": "modify_position",
            "broker_ticket": 123456,
            "side": "LONG",
            "current_price": 120.0,
            "previous_stop_loss": 80.0,
            "stop_loss": 100.0,
            "previous_take_profit": 140.0,
            "take_profit": 140.0,
            "risk_effect": "principal_lock",
        },
        bridge=FakeBridge(real=True),
    )

    assert report["status"] == "ACCEPT"
    assert report["edge_pass_required"] is False
    assert report["fresh_broker_truth_required"] is True
    assert calls == ["gate:live_trading", "fresh_broker_truth"]


def test_trade_management_guard_rejects_stop_loosening():
    with pytest.raises(PermissionError, match="must tighten"):
        require_trade_management_action_ready(
            {
                "broker_method": "modify_position",
                "broker_ticket": 123456,
                "side": "LONG",
                "current_price": 120.0,
                "previous_stop_loss": 90.0,
                "stop_loss": 85.0,
                "previous_take_profit": 140.0,
                "take_profit": 140.0,
                "risk_effect": "risk_reducing_trail",
            },
            bridge=FakeBridge(),
        )


def test_trade_management_guard_rejects_partial_close_over_open_volume():
    with pytest.raises(PermissionError, match="no greater than the open volume"):
        require_trade_management_action_ready(
            {
                "broker_method": "close_position",
                "broker_ticket": 123456,
                "volume": 0.06,
                "original_volume": 0.04,
                "risk_effect": "exposure_reducing_partial_close",
            },
            bridge=FakeBridge(),
        )


def test_trade_management_guard_accepts_missing_stop_protection_and_rejects_crossing_market():
    accepted = require_trade_management_action_ready(
        {
            "broker_method": "modify_position",
            "broker_ticket": 123456,
            "side": "LONG",
            "open_price": 100.0,
            "current_price": 110.0,
            "previous_stop_loss": 0.0,
            "stop_loss": 80.0,
            "previous_take_profit": 140.0,
            "take_profit": 140.0,
            "risk_effect": "emergency_protective_stop",
        },
        bridge=FakeBridge(),
    )
    assert accepted["status"] == "ACCEPT"

    with pytest.raises(PermissionError, match="below current exit price"):
        require_trade_management_action_ready(
            {
                "broker_method": "modify_position",
                "broker_ticket": 123456,
                "side": "LONG",
                "open_price": 100.0,
                "current_price": 110.0,
                "previous_stop_loss": 0.0,
                "stop_loss": 111.0,
                "previous_take_profit": 140.0,
                "take_profit": 140.0,
                "risk_effect": "emergency_protective_stop",
            },
            bridge=FakeBridge(),
        )


def test_trade_management_guard_enforces_take_profit_policy_geometry():
    set_target = require_trade_management_action_ready(
        {
            "broker_method": "modify_position",
            "broker_ticket": 123456,
            "side": "LONG",
            "open_price": 100.0,
            "current_price": 112.0,
            "previous_stop_loss": 90.0,
            "stop_loss": 90.0,
            "previous_take_profit": 0.0,
            "take_profit": 120.0,
            "risk_effect": "bounded_profit_target",
        },
        bridge=FakeBridge(),
    )
    assert set_target["status"] == "ACCEPT"

    extension = require_trade_management_action_ready(
        {
            "broker_method": "modify_position",
            "broker_ticket": 123456,
            "side": "LONG",
            "open_price": 100.0,
            "current_price": 137.0,
            "previous_stop_loss": 100.0,
            "stop_loss": 100.0,
            "previous_take_profit": 140.0,
            "take_profit": 160.0,
            "risk_effect": "profit_extension_after_principal_lock",
        },
        bridge=FakeBridge(),
    )
    assert extension["status"] == "ACCEPT"

    with pytest.raises(PermissionError, match="cannot silently change the stop"):
        require_trade_management_action_ready(
            {
                "broker_method": "modify_position",
                "broker_ticket": 123456,
                "side": "LONG",
                "open_price": 100.0,
                "current_price": 112.0,
                "previous_stop_loss": 90.0,
                "stop_loss": 85.0,
                "previous_take_profit": 0.0,
                "take_profit": 120.0,
                "risk_effect": "bounded_profit_target",
            },
            bridge=FakeBridge(),
        )


def test_trade_management_guard_accepts_explicit_full_close_only_without_volume():
    report = require_trade_management_action_ready(
        {
            "broker_method": "close_position",
            "broker_ticket": 123456,
            "volume": None,
            "original_volume": 0.04,
            "risk_effect": "exposure_reducing_full_close",
        },
        bridge=FakeBridge(),
    )
    assert report["status"] == "ACCEPT"


def test_ai_hedge_management_route_ignores_legacy_confirmation_params(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return {"report_kind": "cas_forex_ai_hedge_management_execution", "status": "EXECUTED_RECONCILED"}

    monkeypatch.setattr(ai_hedge_management_route, "run_ai_hedge_management_action", fake_run)
    monkeypatch.setattr(
        ai_hedge_management_route,
        "prepare_current_ai_hedge_management",
        lambda: {
            "bridge": "active-bridge",
            "config": "active-config",
            "handoff": {"status": "READY_FOR_GUARDED_EXECUTION"},
        },
    )

    body = asyncio.run(
        ai_hedge_management_route.execute_ai_hedge_management_action(
            ai_hedge_management_route.AiHedgeManagementExecuteRequest(
                action_id="action-1",
                reason="OWNER_TEST",
            ),
            dry_run=False,
            confirm_owner_action=True,
            confirm_phrase="wrong legacy phrase ignored",
        )
    )
    assert body["status"] == "EXECUTED_RECONCILED"
    assert captured["action_id"] == "action-1"
    assert captured["dry_run"] is False
    assert captured["confirm_owner_action"] is True
    assert captured["bridge"] == "active-bridge"
    assert captured["config"] == "active-config"
    assert captured["handoff"]["status"] == "READY_FOR_GUARDED_EXECUTION"
    assert callable(captured["post_execution_refresh"])


def test_ai_hedge_management_post_execution_route_refresh_seeds_truth_caches(monkeypatch):
    invalidated: list[tuple[str, ...]] = []
    stored: dict[str, dict[str, Any]] = {}

    monkeypatch.setattr(
        ai_hedge_management_route,
        "invalidate_live_money_gate_caches",
        lambda *keys: invalidated.append(tuple(keys)),
    )
    monkeypatch.setattr(
        ai_hedge_management_route,
        "store_cache_payload",
        lambda key, payload: stored.__setitem__(key, dict(payload)),
    )
    monkeypatch.setattr(
        ai_hedge_management_route,
        "run_broker_truth_check",
        lambda: {
            "report_kind": "cas_forex_broker_truth_monitor",
            "monitor_status": "BROKER_TRUTH_OK",
            "overall_status": "OK",
            "mt5_open_position_count": 1,
        },
    )
    monkeypatch.setattr(
        ai_hedge_management_route,
        "monitor_fast_status",
        lambda: {
            "report_kind": "cas_forex_broker_truth_monitor_status_fast",
            "monitor_status": "BROKER_TRUTH_OK",
            "ready_for_live": True,
            "latest_report": {"mt5_open_position_count": 1},
        },
    )
    monkeypatch.setattr(
        ai_hedge_management_route,
        "collect_live_telemetry",
        lambda: {
            "as_of_iso": "2026-07-09T00:00:00+00:00",
            "telemetry_source": "mt5_terminal_api_verifier",
            "telemetry_stale": False,
            "totals": {"open_position_count": 1, "total_floating_pnl": 12.5},
        },
    )
    monkeypatch.setattr(
        ai_hedge_management_route.data_module,
        "account_reconciliation",
        lambda sync_to_broker=False: {
            "report_kind": "cas_forex_account_reconciliation",
            "overall_status": "OK",
            "sync_to_broker_snapshot": sync_to_broker,
        },
    )
    monkeypatch.setattr(
        ai_hedge_management_route.data_module,
        "movement_stream",
        lambda use_provider_quotes=False: {
            "report_kind": "cas_forex_movement_stream",
            "status": "OK",
            "position_count": 1,
            "market_data_provider_requested": use_provider_quotes,
        },
    )

    report = ai_hedge_management_route._post_execution_broker_truth_refresh(
        {
            "status": "EXECUTED_RECONCILED",
            "audit_id": "audit-1",
            "selected_action_id": "action-1",
        }
    )

    assert report["status"] == "REFRESH_RAN"
    assert report["error_count"] == 0
    assert invalidated
    assert "live_telemetry" in invalidated[0]
    assert stored["live_telemetry"]["telemetry_source"] == "mt5_terminal_api_verifier"
    assert stored["account_reconciliation:False"]["sync_to_broker_snapshot"] is False
    assert stored["account_reconciliation:True"]["sync_to_broker_snapshot"] is True
    assert stored["movement_snapshot:True"]["market_data_provider_requested"] is True
    assert report["refreshed_packets"]["live_telemetry"]["open_position_count"] == 1


def test_ai_hedge_management_execution_route_ui_and_server_are_wired():
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")

    assert "runAiHedgeManagementAction" in api_client
    assert "/ai-hedge-management/execute?" in api_client
    assert "CONFIRM AI EDGE MANAGEMENT" not in settings_page
    assert "Execute guarded draft" in settings_page
    assert "Receipt Reconciliation" in settings_page
    assert "Post-Execution Refresh" in settings_page
    assert "terminal_receipt_status" in api_client
    assert "post_execution_refresh_status" in api_client
    assert any(
        str(getattr(route, "path", "")) == "/api/forex/ai-hedge-management/execute"
        for route in api_server.app.routes
    )
