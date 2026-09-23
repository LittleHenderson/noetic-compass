"""Deterministic launch/provenance tests. Fake workers never execute a model."""
import json
from pathlib import Path
import subprocess

import pytest

import q4_smoke_job as job


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    plan = {"output": str(tmp_path / "output"), "device": "cuda:0", "max_wall_seconds": 30,
            "max_updates": 2}
    path = tmp_path / "plan.json"
    path.write_bytes(job.canonical(plan))
    receipt = {"mode": "EXPLICIT_USER_CONVERSATION", "record_sha256": "a" * 64,
               "plan_sha256": job.digest(job.canonical(plan))}
    monkeypatch.setattr(job, "validate_plan", lambda value: value)
    monkeypatch.setattr(job, "_authorization_receipt", lambda *args, **kw: receipt)
    monkeypatch.setattr(job, "_device_lock_path", lambda device: tmp_path / "device.lock")
    monkeypatch.setattr(job, "_check_device_idle", lambda device: None)
    return plan, path, receipt


def test_conversation_mode_propagates_to_owned_worker_and_receipts(fixture, monkeypatch, tmp_path):
    plan, path, receipt = fixture
    calls = []

    class FakeProcess:
        def __init__(self, command, **kwargs):
            calls.append(command)
            job._write_json(Path(plan["output"]) / "result.json",
                            {"plan_sha256": receipt["plan_sha256"], "actual_updates": 2})
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def wait(self, timeout):
            return 0
        def kill(self):
            pytest.fail("completed worker killed")

    monkeypatch.setattr(job.subprocess, "Popen", FakeProcess)
    auth = tmp_path / "auth.json"
    out = job.execute_plan(path, conversation_authorization=auth, conversation_sha256="a" * 64)
    command = calls[0]
    assert "--conversation-authorization" in command and str(auth) in command
    assert "--conversation-sha256" in command and "--trusted-public-key" not in command
    claim = job._read_json(out / "claim.json")
    assert claim["authorization_receipt_sha256"] == job.digest(job.canonical(receipt))
    assert job._read_json(out / "authorization_receipt.json") == receipt
    assert job._read_json(out / "supervisor.json")["authorization"] == receipt


@pytest.mark.parametrize("arguments", [
    {}, {"conversation_authorization": "a"}, {"conversation_sha256": "a" * 64},
    {"authorization": "signed", "conversation_authorization": "chat", "conversation_sha256": "a" * 64},
    {"trusted_public_key": "key", "conversation_authorization": "chat", "conversation_sha256": "a" * 64},
])
def test_incomplete_or_mixed_modes_cannot_create_output(tmp_path, monkeypatch, arguments):
    plan = {"output": str(tmp_path / "output")}
    path = tmp_path / "plan.json"
    path.write_bytes(job.canonical(plan))
    monkeypatch.setattr(job, "validate_plan", lambda value: value)
    monkeypatch.setattr(job.subprocess, "Popen", lambda *a, **kw: pytest.fail("invalid launch"))
    with pytest.raises(job.JobError):
        job.execute_plan(path, **arguments)
    assert not Path(plan["output"]).exists()


def test_worker_rejects_changed_authorization_before_loading_model(fixture, monkeypatch):
    plan, path, receipt = fixture
    out = Path(plan["output"])
    out.mkdir()
    monkeypatch.setenv("HELM_Q4_WORKER_NONCE", "test-nonce")
    job._write_json(out / "claim.json", {"plan_sha256": receipt["plan_sha256"],
                    "worker_nonce_sha256": job.digest(b"test-nonce"),
                    "authorization_receipt_sha256": "f" * 64})
    with pytest.raises(job.JobError, match="WORKER_NOT_OWNED"):
        job._worker(path, conversation_authorization="auth", conversation_sha256="a" * 64)
    assert not (out / "worker_started.json").exists()


def test_shared_gpu_thermal_failure_stops_only_owned_worker(fixture, monkeypatch):
    import q4_device_capacity as capacity
    plan, path, receipt = fixture
    plan["device_policy"] = {"TEST_ONLY": True}
    path.write_bytes(job.canonical(plan))
    events = []

    class FakeProcess:
        def __init__(self, *args, **kwargs):
            events.append("launch")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def wait(self, timeout):
            assert "kill-owned-worker" in events
            return -9
        def kill(self):
            events.append("kill-owned-worker")

    monkeypatch.setattr(capacity, "check_prelaunch", lambda *args: {"TEST_ONLY": "shared"})
    def too_hot(*args):
        raise capacity.CapacityError("THERMAL_STOP_TEST_ONLY")
    monkeypatch.setattr(capacity, "check_running", too_hot)
    monkeypatch.setattr(job.subprocess, "Popen", FakeProcess)
    with pytest.raises(capacity.CapacityError, match="THERMAL_STOP"):
        job.execute_plan(path, conversation_authorization="auth", conversation_sha256="a" * 64)
    assert events == ["launch", "kill-owned-worker"]
    supervisor = job._read_json(Path(plan["output"]) / "supervisor.json")
    assert supervisor["status"] == "FAILED" and supervisor["automatic_retries"] == 0
    assert supervisor["failure"]["type"] == "CapacityError"
    assert not job._device_lock_path(plan["device"]).exists()


def test_shared_gpu_wait_keeps_samples_until_owned_worker_finishes(tmp_path, monkeypatch):
    import q4_device_capacity as capacity
    monkeypatch.setattr(capacity, "check_running", lambda *args: {"temperature_c": 60})
    calls = []
    class FakeProcess:
        def wait(self, timeout):
            calls.append(timeout)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired("TEST_ONLY", timeout)
            return 0
    plan = {"max_wall_seconds": 30, "device_policy": {}, "device": "cuda:0"}
    assert job._wait_for_worker(FakeProcess(), plan, job.time.monotonic(), tmp_path) == 0
    rows = [json.loads(line) for line in (tmp_path / "device_monitor.jsonl").read_text().splitlines()]
    assert len(rows) == 2 and max(calls) <= 2


def test_shared_gpu_telemetry_cannot_accept_late_completion(tmp_path, monkeypatch):
    import q4_device_capacity as capacity
    clock = [0.0]
    monkeypatch.setattr(job.time, "monotonic", lambda: clock[0])
    def late_query(*args):
        clock[0] = 31.0
        return {"temperature_c": 60}
    monkeypatch.setattr(capacity, "check_running", late_query)
    class FakeProcess:
        def wait(self, timeout):
            pytest.fail("accepted worker completion after deadline")
    plan = {"max_wall_seconds": 30, "device_policy": {}, "device": "cuda:0"}
    with pytest.raises(subprocess.TimeoutExpired):
        job._wait_for_worker(FakeProcess(), plan, 0.0, tmp_path)


def test_shared_gpu_reserves_time_for_bounded_telemetry(tmp_path, monkeypatch):
    import q4_device_capacity as capacity
    monkeypatch.setattr(capacity, "check_running", lambda *args: pytest.fail("query exceeds remaining budget"))
    monkeypatch.setattr(job.time, "monotonic", lambda: 25.0)
    plan = {"max_wall_seconds": 30, "device_policy": {}, "device": "cuda:0"}
    with pytest.raises(subprocess.TimeoutExpired):
        job._wait_for_worker(None, plan, 0.0, tmp_path)
