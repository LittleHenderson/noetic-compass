from __future__ import annotations

import dataclasses

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import broker_truth_monitor as route_module
from cas_forex import (
    auto_halt,
    broker_reality,
    broker_truth_monitor,
    broker_truth_monitor_supervisor,
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


def _live_mt5_snapshot(*, connected=True, is_demo=False, open_positions=0):
    return {
        "report_kind": "cas_forex_mt5_live_account",
        "connected": connected,
        "is_demo": is_demo,
        "open_position_count": open_positions,
    }


def _terminal_report(*, status="TERMINAL_POSITION_RECONCILIATION_READY_FLAT", unmatched=0):
    return {
        "report_kind": "cas_forex_terminal_position_reconciliation_report",
        "reconciliation_status": status,
        "summary": {
            "terminal_open_position_count": 0,
            "unmatched_open_position_count": unmatched,
            "pending_receipt_count": 0,
            "receipt_mismatch_count": 0,
            "account_snapshot_present": True,
        },
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


def test_runtime_gate_surfaces_broker_truth_freshness_as_advisory(tmp_path, monkeypatch):
    # Broker-truth monitor freshness is a continuous metric, and metrics are not
    # authority (see runtime_gates OWNER_AUTHORITY_BOUNDARY): a stale monitor is
    # surfaced as an ADVISORY, never an owner veto. The action-time freshness
    # requirement lives in the live-order dry-run review instead.
    monkeypatch.setattr(broker_truth_monitor, "DEFAULT_STATE_PATH", tmp_path / "broker-truth.json")
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)
    decision_without_monitor = runtime_gates.evaluate_live_trading(GateConfig())
    assert (
        "continuous broker-truth monitor is fresh and live-connected"
        in decision_without_monitor.advisory_requirements
    )
    assert (
        "continuous broker-truth monitor is fresh and live-connected"
        not in decision_without_monitor.satisfied_requirements
    )
    # Advisory alone never blocks: with every owner + action-time requirement
    # satisfied, the gate authorizes even while the monitor is stale.
    assert decision_without_monitor.authorized is True

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
    # A DEMO snapshot never counts as live broker truth: the freshness advisory
    # stays unsatisfied (and the hard owner/action-time requirements above keep
    # the gate closed on their own).
    assert (
        "continuous broker-truth monitor is fresh and live-connected"
        in decision.advisory_requirements
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
