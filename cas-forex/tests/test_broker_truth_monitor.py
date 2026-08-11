from __future__ import annotations

import dataclasses

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import broker_truth_monitor as route_module
from cas_forex import (
    auto_halt,
    broker_reality,
    broker_truth_monitor,
    broker_truth_monitor_supervisor,
    critical_notifications,
    live_order_dry_run_review,
    live_pilot,
    live_recovery,
    runtime_gates,
)
from cas_forex.broker_truth_monitor_supervisor import (
    BrokerTruthMonitorSupervisorConflict,
    BrokerTruthMonitorSupervisorStore,
    STATUS_RECOVERY_CLEARED,
    STATUS_RECOVERY_REFUSED,
)
from cas_forex.config import config as runtime_config


@pytest.fixture(autouse=True)
def _trusted_mt5_identity(monkeypatch):
    monkeypatch.setattr(runtime_config, "mt5_login", 123)
    monkeypatch.setattr(runtime_config, "mt5_server", "Broker-Live")


def _live_mt5_snapshot(
    *,
    connected=True,
    is_demo=False,
    open_positions=0,
    unprotected=0,
    login=123,
    server="Broker-Live",
):
    return {
        "report_kind": "cas_forex_mt5_live_account",
        "connected": connected,
        "is_demo": is_demo,
        "account": {
            "login": login,
            "server": server,
            "currency": "USD",
            "balance_usd": 5_000.0,
            "equity_usd": 5_000.0,
            "margin_used_usd": 0.0,
            "free_margin_usd": 5_000.0,
        },
        "open_position_count": open_positions,
        "position_protection": {
            "report_kind": "cas_forex_position_protection_report",
            "status": "UNPROTECTED_POSITIONS" if unprotected > 0 else "ALL_POSITIONS_PROTECTED",
            "connected": connected,
            "open_position_count": open_positions,
            "protected_position_count": max(0, open_positions - unprotected),
            "unprotected_position_count": unprotected,
            "requires_owner_attention": unprotected > 0,
            "detail": (
                f"{unprotected} open position(s) have no broker-side stop loss visible in the latest snapshot."
                if unprotected > 0
                else "Every open position has a broker-side stop loss visible in the latest snapshot."
            ),
            "unprotected_positions": (
                [
                    {
                        "ticket": 22,
                        "symbol": "US30",
                        "side": "LONG",
                        "lots": 0.1,
                        "open_price": 52000.0,
                        "current_price": 52100.0,
                        "stop_loss": None,
                        "take_profit": 53000.0,
                        "floating_pnl_usd": 25.0,
                    }
                ]
                if unprotected > 0
                else []
            ),
        },
    }


def _terminal_report(*, status="TERMINAL_POSITION_RECONCILIATION_READY_FLAT", unmatched=0):
    return {
        "report_kind": "cas_forex_terminal_position_reconciliation_report",
        "reconciliation_status": status,
        "summary": {
            "terminal_open_position_count": 0,
            "unmatched_open_position_count": unmatched,
            "terminal_unattributed_open_position_count": unmatched,
            "terminal_memory_gap_open_position_count": 0,
            "cas_memory_only_open_position_count": 0,
            "cas_receipt_pending_open_position_count": 0,
            "pending_receipt_count": 0,
            "receipt_mismatch_count": 0,
            "account_snapshot_present": True,
        },
        "classified_unmatched_open_positions": (
            [
                {
                    "side": "terminal",
                    "reason": "no_matching_cas_memory_position",
                    "classification_status": "TERMINAL_UNATTRIBUTED_BROKER_POSITION",
                    "classification_detail": "Broker-visible position has no CAS command/receipt identity. It may be external/manual broker state or missing CAS memory.",
                    "position": {
                        "symbol": "EUR/USD",
                        "direction": "LONG",
                        "lots": 0.1,
                        "broker_ticket": "ticket-ext-1",
                    },
                }
            ]
            if unmatched
            else []
        ),
    }


def _supervisor_store(tmp_path, *, lease_seconds: int = 60) -> BrokerTruthMonitorSupervisorStore:
    return BrokerTruthMonitorSupervisorStore(
        tmp_path / "broker-truth-monitor-supervisor.json",
        tmp_path / "broker-truth-monitor-supervisor-audit.jsonl",
        lease_seconds=lease_seconds,
    )


@dataclasses.dataclass
class GateConfig:
    owner_enable_live_trading: bool = True
    live_trading_licensed: bool = True
    mt5_login: int = 123
    mt5_password: str = "secret"
    mt5_server: str = "Broker-Live"
    live_mode: bool = True
    prefer_mt5: bool = True
    mt5_path: str = ""
    personal_account_ack: bool = True
    no_pooled_capital_ack: bool = True
    account_type: str = "personal"
    selected_broker_id: str = "hugosway"
    broker_name: str = "HUGOSWAY"


def test_broker_truth_report_is_clear_when_live_mt5_and_terminal_reconcile(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "DEFAULT_STATE_PATH", tmp_path / "broker-truth.json")
    report = broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(open_positions=0),
        terminal_reconciliation_report=_terminal_report(),
        write_state=True,
        write_report=False,
    )

    assert report["overall_status"] == "RECONCILED"
    assert report["monitor_status"] == broker_truth_monitor.STATUS_RECONCILED
    assert broker_truth_monitor.broker_truth_monitor_ready_for_live() is True
    assert report["position_protection_status"] == "ALL_POSITIONS_PROTECTED"
    assert report["position_protection_unprotected_position_count"] == 0
    assert report["mt5_balance_usd"] == 5_000.0
    assert report["mt5_free_margin_usd"] == 5_000.0
    assert report["mt5_account_identity_matches_config"] is True


def test_wrong_hugo_demo_account_blocks_risen_truth_and_latches_auto_halt(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")
    monkeypatch.setattr(runtime_config, "mt5_login", 101321)
    monkeypatch.setattr(runtime_config, "mt5_server", "Risen-Trade")
    report = broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(
            is_demo=True,
            login=1000694,
            server="Hugosway-Demo",
        ),
        terminal_reconciliation_report=_terminal_report(),
        state_path=tmp_path / "broker-truth.json",
        write_state=True,
        write_report=False,
    )

    assert report["overall_status"] == "RECONCILIATION_FAILED"
    assert report["mt5_account_identity_matches_config"] is False
    assert report["mt5_account_identity_mismatch_fields"] == ["login", "server"]
    assert report["auto_halt_latched_from_monitor"] is True
    assert "mt5_account_identity_matches_config" in report["monitor_auto_halt_reason_ids"]
    assert "1000694" in report["next_action"]
    assert "101321" in report["next_action"]
    assert broker_truth_monitor.broker_truth_monitor_ready_for_live(
        state_path=tmp_path / "broker-truth.json"
    ) is False


def test_snapshot_cannot_spoof_the_configured_account_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")
    monkeypatch.setattr(runtime_config, "mt5_login", 101321)
    monkeypatch.setattr(runtime_config, "mt5_server", "Risen-Trade")
    snapshot = _live_mt5_snapshot(
        is_demo=False,
        login=777777,
        server="OtherBroker-Live",
    )
    snapshot["configured_account"] = {
        "login": 777777,
        "server": "OtherBroker-Live",
    }

    report = broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=snapshot,
        terminal_reconciliation_report=_terminal_report(),
        state_path=tmp_path / "broker-truth.json",
        write_state=True,
        write_report=False,
    )

    assert report["mt5_expected_account"] == 101321
    assert report["mt5_expected_server"] == "Risen-Trade"
    assert report["mt5_account_identity_matches_config"] is False
    assert report["mt5_account_identity_mismatch_fields"] == ["login", "server"]


def test_different_live_account_cannot_satisfy_configured_risen_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")
    monkeypatch.setattr(runtime_config, "mt5_login", 101321)
    monkeypatch.setattr(runtime_config, "mt5_server", "Risen-Trade")
    report = broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(
            is_demo=False,
            login=777777,
            server="Risen-Trade",
        ),
        terminal_reconciliation_report=_terminal_report(),
        state_path=tmp_path / "broker-truth.json",
        write_state=True,
        write_report=False,
    )

    assert report["mt5_account_identity_matches_config"] is False
    assert report["mt5_account_identity_mismatch_fields"] == ["login"]
    assert report["auto_halt_latched_from_monitor"] is True
    assert broker_truth_monitor.broker_truth_monitor_ready_for_live(
        state_path=tmp_path / "broker-truth.json"
    ) is False


def test_exact_risen_login_and_server_unlock_identity_check(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "DEFAULT_STATE_PATH", tmp_path / "broker-truth.json")
    monkeypatch.setattr(runtime_config, "mt5_login", 101321)
    monkeypatch.setattr(runtime_config, "mt5_server", "risen-trade")
    report = broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(
            is_demo=False,
            login=101321,
            server="Risen-Trade",
        ),
        terminal_reconciliation_report=_terminal_report(),
        write_state=True,
        write_report=False,
    )

    assert report["overall_status"] == "RECONCILED"
    assert report["mt5_account_identity_matches_config"] is True
    assert broker_truth_monitor.broker_truth_monitor_ready_for_live() is True


def test_broker_truth_report_fails_on_terminal_position_mismatch(tmp_path):
    report = broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(open_positions=1),
        terminal_reconciliation_report=_terminal_report(
            status="TERMINAL_POSITION_RECONCILIATION_MISMATCH",
            unmatched=1,
        ),
        state_path=tmp_path / "broker-truth.json",
        write_state=True,
        write_report=False,
    )

    assert report["overall_status"] == "RECONCILIATION_FAILED"
    assert report["checks_mismatch"] >= 1
    assert report["monitor_auto_halt_reason_ids"] == [
        "terminal_position_reconciliation",
        "live_open_positions_crosscheck",
    ]
    assert report["terminal_unattributed_open_position_count"] == 1
    assert report["terminal_unmatched_open_position_preview"][0]["classification_status"] == (
        "TERMINAL_UNATTRIBUTED_BROKER_POSITION"
    )
    assert "cannot attribute" in report["next_action"].lower()


def test_broker_truth_report_latches_auto_halt_on_live_terminal_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")

    report = broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(open_positions=1),
        terminal_reconciliation_report=_terminal_report(
            status="TERMINAL_POSITION_RECONCILIATION_MISMATCH",
            unmatched=1,
        ),
        state_path=tmp_path / "broker-truth.json",
        write_state=True,
        write_report=False,
    )

    assert report["overall_status"] == "RECONCILIATION_FAILED"
    assert report["auto_halt_latched_from_monitor"] is True
    assert "terminal_position_reconciliation" in report["monitor_auto_halt_reason_ids"]
    assert "live_open_positions_crosscheck" in report["monitor_auto_halt_reason_ids"]
    assert auto_halt.is_auto_halt_active() is True


def test_demo_broker_truth_mismatch_does_not_latch_auto_halt(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")

    report = broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(is_demo=True, open_positions=1),
        terminal_reconciliation_report=_terminal_report(
            status="TERMINAL_POSITION_RECONCILIATION_MISMATCH",
            unmatched=1,
        ),
        state_path=tmp_path / "broker-truth.json",
        write_state=True,
        write_report=False,
    )

    assert report["overall_status"] == "RECONCILIATION_FAILED"
    assert report["auto_halt_latched_from_monitor"] is False
    assert "terminal_position_reconciliation" in report["monitor_auto_halt_reason_ids"]
    assert auto_halt.is_auto_halt_active() is False


def test_broker_truth_report_fails_on_unprotected_live_positions_and_latches_auto_halt(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")
    critical_notifications.set_critical_notification_context_for_tests(
        audit_path=tmp_path / "critical-alerts.jsonl",
        store=None,
        transport=None,
    )
    try:
        report = broker_truth_monitor.run_broker_truth_check(
            mt5_snapshot=_live_mt5_snapshot(open_positions=1, unprotected=1),
            terminal_reconciliation_report=_terminal_report(),
            state_path=tmp_path / "broker-truth.json",
            write_state=True,
            write_report=False,
        )
    finally:
        critical_notifications.set_critical_notification_context_for_tests()

    assert report["overall_status"] == "RECONCILIATION_FAILED"
    assert report["position_protection_status"] == "UNPROTECTED_POSITIONS"
    assert report["position_protection_unprotected_position_count"] == 1
    assert report["auto_halt_latched_from_monitor"] is True
    assert report["position_protection_notification_emitted"] is True
    assert "stop loss" in report["next_action"].lower()
    protection_check = next(check for check in report["checks"] if check["check_id"] == "live_position_stop_loss_protection")
    assert protection_check["status"] == "MISMATCH"
    assert protection_check["trips_auto_halt"] is True
    assert auto_halt.is_auto_halt_active() is True


def test_broker_truth_report_emits_unprotected_position_alert_only_on_first_detection(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")
    critical_notifications.set_critical_notification_context_for_tests(
        audit_path=tmp_path / "critical-alerts.jsonl",
        store=None,
        transport=None,
    )
    try:
        first = broker_truth_monitor.run_broker_truth_check(
            mt5_snapshot=_live_mt5_snapshot(open_positions=1, unprotected=1),
            terminal_reconciliation_report=_terminal_report(),
            state_path=tmp_path / "broker-truth.json",
            write_state=True,
            write_report=False,
        )
        second = broker_truth_monitor.run_broker_truth_check(
            mt5_snapshot=_live_mt5_snapshot(open_positions=1, unprotected=1),
            terminal_reconciliation_report=_terminal_report(),
            state_path=tmp_path / "broker-truth.json",
            write_state=True,
            write_report=False,
        )
        audit = critical_notifications.build_critical_notification_report(limit=10)
    finally:
        critical_notifications.set_critical_notification_context_for_tests()

    assert first["position_protection_notification_emitted"] is True
    assert second["position_protection_notification_emitted"] is False
    rows = audit["rows"]
    assert len(rows) == 1
    assert rows[0]["event"]["event_kind"] == critical_notifications.EVENT_UNPROTECTED_POSITION


def test_broker_truth_report_surfaces_unattributed_closed_history_gap(tmp_path):
    report = broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(open_positions=0),
        terminal_reconciliation_report={
            "report_kind": "cas_forex_terminal_position_reconciliation_report",
            "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_MISMATCH",
            "summary": {
                "terminal_open_position_count": 0,
                "unmatched_open_position_count": 0,
                "terminal_unattributed_open_position_count": 0,
                "terminal_memory_gap_open_position_count": 0,
                "cas_memory_only_open_position_count": 0,
                "cas_receipt_pending_open_position_count": 0,
                "unmatched_history_count": 1,
                "unmatched_unattributed_history_count": 1,
                "unmatched_attributed_history_memory_gap_count": 0,
                "pending_receipt_count": 0,
                "receipt_mismatch_count": 0,
                "account_snapshot_present": True,
            },
            "classified_unmatched_history_records": [
                {
                    "classification_status": "TERMINAL_UNATTRIBUTED_BROKER_HISTORY",
                    "classification_detail": "Closed broker/terminal history row has no CAS command or receipt identity. It may be an external/manual broker close or a missing CAS comment/identity field.",
                    "symbol": "EUR/USD",
                    "direction": "LONG",
                    "lots": 0.1,
                    "profit_loss_account": 25.0,
                }
            ],
        },
        state_path=tmp_path / "broker-truth.json",
        write_state=True,
        write_report=False,
    )

    assert report["overall_status"] == "RECONCILIATION_FAILED"
    assert report["terminal_unmatched_history_count"] == 1
    assert report["terminal_unattributed_history_count"] == 1
    assert report["terminal_unmatched_history_preview"][0]["classification_status"] == (
        "TERMINAL_UNATTRIBUTED_BROKER_HISTORY"
    )
    assert "closed-history rows" in report["next_action"].lower()


def test_broker_truth_state_save_retries_transient_windows_replace_lock(tmp_path, monkeypatch):
    report = broker_truth_monitor.build_broker_truth_monitor_report(
        mt5_snapshot=_live_mt5_snapshot(open_positions=0),
        terminal_reconciliation_report=_terminal_report(),
    )
    real_replace = broker_truth_monitor.os.replace
    attempts: list[tuple[str, str]] = []

    def flaky_replace(source, target):
        attempts.append((str(source), str(target)))
        if len(attempts) == 1:
            raise PermissionError("temporary OneDrive lock")
        return real_replace(source, target)

    monkeypatch.setattr(broker_truth_monitor.os, "replace", flaky_replace)
    monkeypatch.setattr(broker_truth_monitor.time, "sleep", lambda _seconds: None)

    path = broker_truth_monitor.save_latest_broker_truth_monitor_report(
        report,
        state_path=tmp_path / "broker-truth.json",
    )

    assert path.exists()
    assert len(attempts) == 2
    assert broker_truth_monitor.load_latest_broker_truth_monitor_report(state_path=path)["report_kind"] == (
        broker_truth_monitor.REPORT_KIND
    )
    assert list(tmp_path.glob("*.tmp")) == []


def test_broker_truth_mt5_snapshot_uses_selected_python_command(monkeypatch):
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0
        stdout = '{"report_kind":"cas_forex_mt5_live_account","connected":true,"is_demo":true,"open_position_count":0}\n'
        stderr = ""

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return Completed()

    monkeypatch.setattr(broker_truth_monitor, "_mt5_snapshot_python_command", lambda: ["py", "-3.12"])
    monkeypatch.setattr(broker_truth_monitor.subprocess, "run", fake_run)

    snapshot = broker_truth_monitor._read_mt5_snapshot()

    assert captured["args"][:2] == ["py", "-3.12"]
    assert snapshot["connected"] is True
    assert snapshot["open_position_count"] == 0


def test_runtime_gate_blocks_when_broker_truth_is_stale(tmp_path, monkeypatch):
    # Broker-truth freshness is a hard live-dispatch prerequisite. Owner
    # authority can delegate autonomy, but stale broker truth still blocks.
    monkeypatch.setattr(broker_truth_monitor, "DEFAULT_STATE_PATH", tmp_path / "broker-truth.json")
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)
    decision_without_monitor = runtime_gates.evaluate_live_trading(GateConfig())
    assert (
        "continuous broker-truth monitor is fresh and live-connected"
        in decision_without_monitor.missing_requirements
    )
    assert (
        "continuous broker-truth monitor is fresh and live-connected"
        not in decision_without_monitor.satisfied_requirements
    )
    assert decision_without_monitor.authorized is False

    broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(),
        terminal_reconciliation_report=_terminal_report(),
        write_state=True,
        write_report=False,
    )

    decision_with_monitor = runtime_gates.evaluate_live_trading(GateConfig())
    assert decision_with_monitor.authorized is True
    assert (
        "continuous broker-truth monitor is fresh and live-connected"
        in decision_with_monitor.satisfied_requirements
    )
    assert decision_with_monitor.advisory_requirements == ()


def test_demo_mt5_monitor_does_not_unlock_live_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "DEFAULT_STATE_PATH", tmp_path / "broker-truth.json")
    broker_truth_monitor.run_broker_truth_check(
        mt5_snapshot=_live_mt5_snapshot(is_demo=True),
        terminal_reconciliation_report=_terminal_report(),
        write_state=True,
        write_report=False,
    )

    decision = runtime_gates.evaluate_live_trading(GateConfig())
    assert decision.authorized is False
    # A DEMO snapshot never counts as live broker truth, so the hard freshness
    # requirement stays unsatisfied.
    assert (
        "continuous broker-truth monitor is fresh and live-connected"
        in decision.missing_requirements
    )
    assert (
        "continuous broker-truth monitor is fresh and live-connected"
        not in decision.satisfied_requirements
    )


def test_broker_truth_monitor_route_status(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "monitor_status",
        lambda: {
            "report_kind": "cas_forex_broker_truth_monitor_status",
            "running": False,
            "monitor_status": broker_truth_monitor.STATUS_RECONCILED,
        },
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/broker-truth-monitor")
    client = TestClient(app)

    response = client.get("/api/forex/broker-truth-monitor/status")

    assert response.status_code == 200
    assert response.json()["monitor_status"] == broker_truth_monitor.STATUS_RECONCILED


def test_broker_truth_fast_status_compacts_latest_report(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_truth_monitor, "DEFAULT_STATE_PATH", tmp_path / "broker-truth.json")
    store = _supervisor_store(tmp_path)
    broker_truth_monitor.set_monitor_supervisor_for_tests(store, owner_id="api-owner")
    try:
        broker_truth_monitor.run_broker_truth_check(
            mt5_snapshot=_live_mt5_snapshot(open_positions=0),
            terminal_reconciliation_report=_terminal_report(),
            write_state=True,
            write_report=False,
        )
        status = broker_truth_monitor.monitor_fast_status()
    finally:
        broker_truth_monitor.set_monitor_supervisor_for_tests(None)

    assert status["report_kind"] == "cas_forex_broker_truth_monitor_status_fast"
    assert status["monitor_status"] == broker_truth_monitor.STATUS_RECONCILED
    assert status["ready_for_live"] is True
    assert status["latest_report"]["mt5_connected"] is True
    assert status["latest_report"]["terminal_account_snapshot_present"] is True
    assert "checks" not in status["latest_report"]
    assert "artifact_paths" not in status["latest_report"]


def test_broker_truth_monitor_fast_route_status(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "monitor_fast_status",
        lambda: {
            "report_kind": "cas_forex_broker_truth_monitor_status_fast",
            "running": False,
            "monitor_status": broker_truth_monitor.STATUS_RECONCILED,
            "latest_report": {"monitor_status": broker_truth_monitor.STATUS_RECONCILED},
        },
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/broker-truth-monitor")
    client = TestClient(app)

    response = client.get("/api/forex/broker-truth-monitor/status/fast")

    assert response.status_code == 200
    assert response.json()["report_kind"] == "cas_forex_broker_truth_monitor_status_fast"


def test_broker_truth_monitor_start_route_uses_isolated_worker_outside_pytest(monkeypatch):
    called: dict[str, object] = {}

    monkeypatch.setattr(route_module, "use_in_process_workers_for_tests", lambda: False)
    monkeypatch.setattr(route_module, "stop_monitor", lambda: called.setdefault("stopped_local", True))

    def fake_start_worker(*, interval_seconds: int):
        called["interval_seconds"] = interval_seconds
        return {
            "report_kind": "cas_forex_broker_truth_monitor_status",
            "running": True,
            "status": "RUNNING",
            "interval_seconds": interval_seconds,
            "worker_isolated": True,
            "ready_for_live": False,
            "claim_boundary": broker_truth_monitor.CLAIM_BOUNDARY,
        }

    monkeypatch.setattr(route_module, "start_broker_truth_monitor_worker", fake_start_worker)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/broker-truth-monitor")
    client = TestClient(app)

    response = client.post("/api/forex/broker-truth-monitor/start", json={"interval_seconds": 120})

    assert response.status_code == 200
    body = response.json()
    assert body["running"] is True
    assert body["worker_isolated"] is True
    assert body["ready_for_live"] is False
    assert called == {"stopped_local": True, "interval_seconds": 120}


def test_broker_truth_fast_route_uses_isolated_worker_fast_status(monkeypatch):
    monkeypatch.setattr(route_module, "use_in_process_workers_for_tests", lambda: False)
    monkeypatch.setattr(
        route_module,
        "broker_truth_worker_fast_status",
        lambda: {
            "report_kind": "cas_forex_broker_truth_monitor_status_fast",
            "running": True,
            "status": "RUNNING",
            "monitor_status": broker_truth_monitor.STATUS_WARNINGS,
            "ready_for_live": False,
            "latest_report": None,
            "worker_isolated": True,
            "external_worker": {"kind": "broker_truth_monitor", "running": True},
            "claim_boundary": broker_truth_monitor.CLAIM_BOUNDARY,
        },
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/broker-truth-monitor")
    client = TestClient(app)

    response = client.get("/api/forex/broker-truth-monitor/status/fast")

    assert response.status_code == 200
    body = response.json()
    assert body["running"] is True
    assert body["worker_isolated"] is True
    assert body["external_worker"]["kind"] == "broker_truth_monitor"


def test_broker_truth_fast_route_is_cache_first(monkeypatch):
    captured: dict[str, object] = {}
    monkeypatch.setattr(route_module, "use_in_process_workers_for_tests", lambda: False)

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "builder_callable": callable(builder),
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(route_module, "cache_first_payload", fake_cache_first_payload)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/broker-truth-monitor")
    client = TestClient(app)

    response = client.get("/api/forex/broker-truth-monitor/status/fast")

    assert response.status_code == 200
    assert captured == {
        "key": "broker_truth_monitor_fast_status",
        "builder_callable": True,
        "ttl_seconds": 10.0,
        "block_on_cold": False,
    }
    assert response.json()["monitor_status"] == "BROKER_TRUTH_MONITOR_WARMING"
    assert response.json()["ready_for_live"] is False


def test_broker_truth_monitor_supervisor_blocks_duplicate_fresh_owner(tmp_path):
    store = _supervisor_store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5)
    broker_truth_monitor.set_monitor_supervisor_for_tests(store, owner_id="worker-b")
    try:
        status = broker_truth_monitor.start_monitor(interval_seconds=5)
    finally:
        broker_truth_monitor.set_monitor_supervisor_for_tests(None)

    assert status["status"] == "SUPERVISOR_CONFLICT"
    assert status["running"] is False
    assert status["supervisor"]["active_lease"]["owner_id"] == "worker-a"
    assert status["supervisor"]["owned_by_this_process"] is False


def test_broker_truth_monitor_supervisor_store_raises_on_duplicate_owner(tmp_path):
    store = _supervisor_store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5)

    try:
        try:
            store.acquire(owner_id="worker-b", interval_seconds=5)
        except BrokerTruthMonitorSupervisorConflict as exc:
            assert exc.lease["owner_id"] == "worker-a"
        else:  # pragma: no cover - assertion clarity
            raise AssertionError("expected BrokerTruthMonitorSupervisorConflict")
    finally:
        broker_truth_monitor.set_monitor_supervisor_for_tests(None)


def test_stale_broker_truth_monitor_lease_can_be_taken_over(tmp_path):
    store = _supervisor_store(tmp_path, lease_seconds=0)
    store.acquire(owner_id="worker-a", interval_seconds=5)

    lease = store.acquire(owner_id="worker-b", interval_seconds=10)

    assert lease["owner_id"] == "worker-b"
    assert lease["interval_seconds"] == 10


def test_dead_broker_truth_monitor_pid_is_treated_as_stale(tmp_path, monkeypatch):
    store = _supervisor_store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5)
    monkeypatch.setattr(broker_truth_monitor_supervisor, "_process_is_alive", lambda _pid: False)

    status = store.recover_stale_or_requested(requested_by="owner", confirm=True)
    lease = store.acquire(owner_id="worker-b", interval_seconds=10)

    assert status["status"] == STATUS_RECOVERY_CLEARED
    assert lease["owner_id"] == "worker-b"
    assert lease["interval_seconds"] == 10


def test_broker_truth_monitor_stop_request_is_durable(tmp_path):
    store = _supervisor_store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5)

    status = store.request_stop(requested_by="worker-b")

    assert status["desired_running"] is False
    assert status["active_lease"]["owner_id"] == "worker-a"
    assert status["stop_requested_by"] == "worker-b"
    assert store.should_stop(owner_id="worker-a") is True


def test_new_broker_truth_acquire_clears_stale_stop_request_fields(tmp_path):
    store = _supervisor_store(tmp_path, lease_seconds=0)
    store.acquire(owner_id="worker-a", interval_seconds=5)
    store.request_stop(requested_by="worker-b")

    store.acquire(owner_id="worker-c", interval_seconds=5)
    status = store.build_status(owner_id="api", local_running=False)

    assert status["desired_running"] is True
    assert status["active_lease"]["owner_id"] == "worker-c"
    assert status["stop_requested_at"] is None
    assert status["stop_requested_by"] is None


def test_broker_truth_renew_clears_stale_stop_request_fields(tmp_path):
    store = _supervisor_store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5)
    store.request_stop(requested_by="worker-b")

    ok, _lease = store.renew(owner_id="worker-a", interval_seconds=5)
    status = store.build_status(owner_id="api", local_running=False)

    assert ok is True
    assert status["desired_running"] is True
    assert status["active_lease"]["owner_id"] == "worker-a"
    assert status["stop_requested_at"] is None
    assert status["stop_requested_by"] is None


def test_broker_truth_monitor_status_surfaces_supervisor_state(tmp_path):
    store = _supervisor_store(tmp_path)
    broker_truth_monitor.set_monitor_supervisor_for_tests(store, owner_id="worker-a")
    try:
        status = broker_truth_monitor.monitor_status()
    finally:
        broker_truth_monitor.set_monitor_supervisor_for_tests(None)

    assert status["supervisor"]["report_kind"] == "cas_forex_broker_truth_monitor_supervisor"
    assert status["supervisor"]["local_owner_id"] == "worker-a"
    assert status["supervisor"]["local_running"] is False


def test_recover_stop_requested_broker_truth_lease_requires_confirm(tmp_path):
    store = _supervisor_store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5)
    store.request_stop(requested_by="worker-b")

    status = store.recover_stale_or_requested(requested_by="owner", confirm=False)

    assert status["status"] == "CONFIRM_REQUIRED"
    assert status["recovery"]["can_clear"] is True
    assert status["active_lease"]["owner_id"] == "worker-a"


def test_recover_stop_requested_broker_truth_lease_clears(tmp_path):
    store = _supervisor_store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5)
    store.request_stop(requested_by="worker-b")

    status = store.recover_stale_or_requested(requested_by="owner", confirm=True)

    assert status["status"] == STATUS_RECOVERY_CLEARED
    assert status["active_lease"] is None
    assert status["desired_running"] is False
    assert status["recovery"]["cleared_lease"]["owner_id"] == "worker-a"


def test_recover_fresh_desired_broker_truth_lease_refuses(tmp_path):
    store = _supervisor_store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5)

    status = store.recover_stale_or_requested(requested_by="owner", confirm=True)

    assert status["status"] == STATUS_RECOVERY_REFUSED
    assert status["active_lease"]["owner_id"] == "worker-a"
    assert status["recovery"]["can_clear"] is False
