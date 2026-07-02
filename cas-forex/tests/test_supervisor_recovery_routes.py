from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import broker_truth_monitor as broker_truth_route
from api.routes import waste_loop_control as waste_route
from cas_forex import waste_runner_supervisor
from cas_forex.broker_truth_monitor_supervisor import BrokerTruthMonitorSupervisorStore
from cas_forex.waste_runner_supervisor import WasteRunnerSupervisorStore


class _FakeWasteCycleStore:
    def latest_cycle(self):
        return {
            "report_kind": "cas_forex_waste_cycle_audit",
            "generated_at": "2026-06-30T22:37:01+00:00",
            "running": True,
            "interval_seconds": 5,
            "mode": "PAPER",
            "cycles_run": 12,
            "decision": "NO_TRADE",
            "reason": "edge gate did not authorize",
            "stage_trace": ["watch", "analyze", "strategize", "test", "no_trade"],
            "watch_state": {
                "broker_grade_market_truth": True,
                "source": "MT5TerminalMarketDataConnector",
                "candles_count": 180,
                "entry_pair_count": 38,
                "selected_directional_profile": "blend",
                "giant_unused_blob": "x" * 2000,
            },
            "analysis": {
                "confidence": 0.57,
                "hypothesis": {"direction": "LONG", "symbol": "US30", "timeframe": "D1"},
            },
            "candidate": {
                "symbol": "US30",
                "timeframe": "D1",
                "direction": "LONG",
                "entry_pair_count": 38,
                "market_state_meta": {
                    "broker_grade_market_truth": True,
                    "source": "MT5TerminalMarketDataConnector",
                    "selected_directional_profile": "blend",
                    "giant_unused_blob": "x" * 2000,
                },
            },
            "edge": {"status": "NO_TRADE_NULL_FAILED", "has_edge_token": False},
        }


def test_waste_fast_status_route_returns_compact_worker_snapshot(monkeypatch, tmp_path):
    store = WasteRunnerSupervisorStore(
        tmp_path / "waste-supervisor.json",
        tmp_path / "waste-supervisor-audit.jsonl",
    )
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    monkeypatch.setattr(waste_route, "use_in_process_workers_for_tests", lambda: False)
    monkeypatch.setattr(waste_route, "default_waste_runner_supervisor_store", lambda: store)
    monkeypatch.setattr(waste_route, "default_waste_cycle_audit_store", lambda: _FakeWasteCycleStore())
    monkeypatch.setattr(waste_route, "process_owner_id", lambda: "api-owner")
    monkeypatch.setattr(
        waste_route,
        "worker_status",
        lambda kind: {
            "kind": kind,
            "configured": True,
            "running": True,
            "pid": 12345,
            "status": "RUNNING",
            "started_at": "2026-06-30T22:36:43+00:00",
            "checked_at": "2026-06-30T22:37:03+00:00",
            "command": ["python", "-m", "cas_forex.waste_background_worker"],
            "log_path": "huge-log-path-not-needed",
            "config": {"interval_seconds": 5, "confirm": True},
        },
    )

    app = FastAPI()
    app.include_router(waste_route.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/status/fast")

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_waste_runner_fast"
    assert body["running"] is True
    assert body["cycles_run"] == 12
    assert body["current_stage"] == "no_trade"
    assert body["durable_cycle"]["watch_state"]["source"] == "MT5TerminalMarketDataConnector"
    assert body["durable_cycle"]["analysis"]["hypothesis"]["direction"] == "LONG"
    assert "giant_unused_blob" not in body["durable_cycle"]["watch_state"]
    assert "command" not in body["external_worker"]


def test_waste_fast_status_uses_fresh_supervisor_lease_when_worker_record_missing(monkeypatch, tmp_path):
    store = WasteRunnerSupervisorStore(
        tmp_path / "waste-supervisor.json",
        tmp_path / "waste-supervisor-audit.jsonl",
    )
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    monkeypatch.setattr(waste_route, "use_in_process_workers_for_tests", lambda: False)
    monkeypatch.setattr(waste_route, "default_waste_runner_supervisor_store", lambda: store)
    monkeypatch.setattr(waste_route, "default_waste_cycle_audit_store", lambda: _FakeWasteCycleStore())
    monkeypatch.setattr(waste_route, "process_owner_id", lambda: "api-owner")
    monkeypatch.setattr(
        waste_route,
        "worker_status",
        lambda kind: {
            "kind": kind,
            "configured": False,
            "running": False,
            "pid": None,
            "state_path": "missing-worker-record.json",
        },
    )

    app = FastAPI()
    app.include_router(waste_route.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/status/fast")

    assert response.status_code == 200
    body = response.json()
    assert body["running"] is True
    assert body["status"] == "RUNNING"
    assert body["interval_seconds"] == 5
    assert body["worker_isolated"] is True
    assert body["supervisor"]["desired_running"] is True
    assert body["supervisor"]["active_lease_is_fresh"] is True


def test_waste_supervisor_recover_route_clears_stop_requested_lease(monkeypatch, tmp_path):
    store = WasteRunnerSupervisorStore(
        tmp_path / "waste-supervisor.json",
        tmp_path / "waste-supervisor-audit.jsonl",
    )
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    store.request_stop(requested_by="worker-b")
    monkeypatch.setattr(waste_route, "default_waste_runner_supervisor_store", lambda: store)
    monkeypatch.setattr(waste_route, "process_owner_id", lambda: "owner")

    app = FastAPI()
    app.include_router(waste_route.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.post("/api/forex/waste-loop-control/supervisor/recover?confirm=true")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RECOVERY_CLEARED"
    assert body["active_lease"] is None


def test_waste_supervisor_recover_route_requires_confirm(monkeypatch, tmp_path):
    store = WasteRunnerSupervisorStore(
        tmp_path / "waste-supervisor.json",
        tmp_path / "waste-supervisor-audit.jsonl",
    )
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    store.request_stop(requested_by="worker-b")
    monkeypatch.setattr(waste_route, "default_waste_runner_supervisor_store", lambda: store)
    monkeypatch.setattr(waste_route, "process_owner_id", lambda: "owner")

    app = FastAPI()
    app.include_router(waste_route.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.post("/api/forex/waste-loop-control/supervisor/recover")

    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRM_REQUIRED"


def test_dead_waste_runner_pid_is_treated_as_stale(monkeypatch, tmp_path):
    store = WasteRunnerSupervisorStore(
        tmp_path / "waste-supervisor.json",
        tmp_path / "waste-supervisor-audit.jsonl",
    )
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    monkeypatch.setattr(waste_runner_supervisor, "_process_is_alive", lambda _pid: False)

    status = store.recover_stale_or_requested(requested_by="owner", confirm=True)
    lease = store.acquire(owner_id="worker-b", interval_seconds=10, mode="PAPER")

    assert status["status"] == "RECOVERY_CLEARED"
    assert lease["owner_id"] == "worker-b"
    assert lease["interval_seconds"] == 10


def test_broker_truth_supervisor_recover_route_clears_stop_requested_lease(monkeypatch, tmp_path):
    store = BrokerTruthMonitorSupervisorStore(
        tmp_path / "broker-truth-supervisor.json",
        tmp_path / "broker-truth-supervisor-audit.jsonl",
    )
    store.acquire(owner_id="worker-a", interval_seconds=5)
    store.request_stop(requested_by="worker-b")
    monkeypatch.setattr(broker_truth_route, "default_broker_truth_monitor_supervisor_store", lambda: store)
    monkeypatch.setattr(broker_truth_route, "process_owner_id", lambda: "owner")

    app = FastAPI()
    app.include_router(broker_truth_route.router, prefix="/api/forex/broker-truth-monitor")
    client = TestClient(app)

    response = client.post("/api/forex/broker-truth-monitor/supervisor/recover?confirm=true")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RECOVERY_CLEARED"
    assert body["active_lease"] is None


def test_broker_truth_supervisor_recover_route_refuses_fresh_active_lease(monkeypatch, tmp_path):
    store = BrokerTruthMonitorSupervisorStore(
        tmp_path / "broker-truth-supervisor.json",
        tmp_path / "broker-truth-supervisor-audit.jsonl",
    )
    store.acquire(owner_id="worker-a", interval_seconds=5)
    monkeypatch.setattr(broker_truth_route, "default_broker_truth_monitor_supervisor_store", lambda: store)
    monkeypatch.setattr(broker_truth_route, "process_owner_id", lambda: "owner")

    app = FastAPI()
    app.include_router(broker_truth_route.router, prefix="/api/forex/broker-truth-monitor")
    client = TestClient(app)

    response = client.post("/api/forex/broker-truth-monitor/supervisor/recover?confirm=true")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RECOVERY_REFUSED"
    assert body["active_lease"]["owner_id"] == "worker-a"
