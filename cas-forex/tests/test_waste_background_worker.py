from __future__ import annotations

import json

from cas_forex import waste_background_worker as worker
from cas_forex import waste_runner_supervisor


def test_start_worker_replaces_running_worker_with_wrong_priority(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    logs = runtime / "worker-logs"
    state_path = runtime / "waste-background-workers.json"
    runtime.mkdir()
    state_path.write_text(
        json.dumps(
            {
                worker.COLLECTOR_KIND: {
                    "kind": worker.COLLECTOR_KIND,
                    "pid": 123,
                    "status": "RUNNING",
                    "config": {"interval_seconds": 300},
                    "command": ["old"],
                }
            }
        ),
        encoding="utf-8",
    )
    terminated: list[int] = []

    class FakeProcess:
        pid = 456

        def __init__(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr(worker, "RUNTIME_DIR", runtime)
    monkeypatch.setattr(worker, "LOG_DIR", logs)
    monkeypatch.setattr(worker, "STATE_PATH", state_path)
    monkeypatch.setattr(worker, "_worker_creationflags", lambda _kind: 0)
    monkeypatch.setattr(worker, "_worker_expected_priority_class", lambda _kind: 16384)
    monkeypatch.setattr(worker, "_pid_alive", lambda pid: pid in {123, 456})
    monkeypatch.setattr(worker, "_process_priority_class", lambda pid: 32 if pid == 123 else 16384)
    monkeypatch.setattr(worker, "_terminate_pid", lambda pid: terminated.append(pid))
    monkeypatch.setattr(worker.subprocess, "Popen", FakeProcess)

    status = worker._start_worker(
        worker.COLLECTOR_KIND,
        ["collector", "--config-json", "{}"],
        config={"interval_seconds": 300},
    )

    assert terminated == [123]
    assert status["pid"] == 456
    assert status["priority_class"] == 16384


def test_runner_worker_sets_scheduled_snapshot_watch_env(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    logs = runtime / "worker-logs"
    state_path = runtime / "waste-background-workers.json"
    runtime.mkdir()
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 456

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs["env"]

    monkeypatch.setattr(worker, "RUNTIME_DIR", runtime)
    monkeypatch.setattr(worker, "LOG_DIR", logs)
    monkeypatch.setattr(worker, "STATE_PATH", state_path)
    monkeypatch.setattr(worker, "_worker_creationflags", lambda _kind: 0)
    monkeypatch.setattr(worker, "_pid_alive", lambda pid: pid == 456)
    monkeypatch.setattr(worker, "_process_priority_class", lambda pid: 16384)
    monkeypatch.setattr(worker.subprocess, "Popen", FakeProcess)

    status = worker._start_worker(
        worker.RUNNER_KIND,
        ["runner", "--interval-seconds", "60"],
        config={"interval_seconds": 60},
    )

    env = captured["env"]
    assert status["pid"] == 456
    assert isinstance(env, dict)
    assert env["CAS_FOREX_BACKGROUND_WORKER"] == worker.RUNNER_KIND
    assert env["CAS_FOREX_WASTE_SCHEDULED_SNAPSHOT_WATCH"] == "1"


def test_waste_status_overlay_uses_fresh_supervisor_lease_when_worker_record_missing(monkeypatch):
    class FakeSupervisorStore:
        def build_status(self, *, owner_id, local_running):
            return {
                "desired_running": True,
                "active_lease_is_fresh": True,
                "active_lease": {
                    "owner_id": "worker-a",
                    "interval_seconds": 60,
                    "mode": "PAPER",
                    "acquired_at": "2026-07-01T06:40:00+00:00",
                },
                "local_owner_id": owner_id,
                "local_running": local_running,
            }

    monkeypatch.setattr(
        worker,
        "worker_status",
        lambda kind: {
            "kind": kind,
            "configured": False,
            "running": False,
            "pid": None,
        },
    )
    monkeypatch.setattr(
        waste_runner_supervisor,
        "default_waste_runner_supervisor_store",
        lambda: FakeSupervisorStore(),
    )
    monkeypatch.setattr(waste_runner_supervisor, "process_owner_id", lambda: "api-owner")

    status = worker.overlay_waste_runner_status(
        {
            "running": False,
            "status": "STOPPED",
            "interval_seconds": None,
            "current_stage": "stopped",
            "durable_cycle": {
                "cycles_run": 7,
                "decision": "NO_TRADE",
                "reason": "edge gate did not authorize",
                "generated_at": "2026-07-01T06:41:00+00:00",
                "stage_trace": ["watch", "analyze", "strategize", "test", "no_trade"],
            },
        }
    )

    assert status["running"] is True
    assert status["status"] == "RUNNING"
    assert status["worker_isolated"] is True
    assert status["interval_seconds"] == 60
    assert status["current_stage"] == "no_trade"
    assert status["started_at_iso"] == "2026-07-01T06:40:00+00:00"
    assert status["supervisor"]["desired_running"] is True


def test_proof_auto_runner_worker_uses_isolated_worker_command(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    logs = runtime / "worker-logs"
    state_path = runtime / "waste-background-workers.json"
    runtime.mkdir()
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 789

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs["env"]

    monkeypatch.setattr(worker, "RUNTIME_DIR", runtime)
    monkeypatch.setattr(worker, "LOG_DIR", logs)
    monkeypatch.setattr(worker, "STATE_PATH", state_path)
    monkeypatch.setattr(worker, "use_in_process_workers_for_tests", lambda: False)
    monkeypatch.setattr(worker, "_worker_creationflags", lambda kind: 16384 if kind == worker.PROOF_RUNNER_KIND else 0)
    monkeypatch.setattr(worker, "_pid_alive", lambda pid: pid == 789)
    monkeypatch.setattr(worker, "_process_priority_class", lambda pid: 16384)
    monkeypatch.setattr(worker.subprocess, "Popen", FakeProcess)

    status = worker.start_proof_auto_runner_worker(check_interval_seconds=3600)

    env = captured["env"]
    command = captured["command"]
    assert isinstance(env, dict)
    assert isinstance(command, list)
    assert env["CAS_FOREX_BACKGROUND_WORKER"] == worker.PROOF_RUNNER_KIND
    assert "proof-auto-runner" in command
    assert status["running"] is True
    assert status["worker_isolated"] is True
