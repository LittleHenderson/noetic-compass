from __future__ import annotations

import pytest

from cas_forex import waste_runner
from cas_forex.waste_runner_supervisor import (
    STATUS_LEASE_ACQUIRED,
    STATUS_RECOVERY_CLEARED,
    STATUS_RECOVERY_REFUSED,
    WasteRunnerSupervisorConflict,
    WasteRunnerSupervisorStore,
)


def _store(tmp_path, *, lease_seconds: int = 60) -> WasteRunnerSupervisorStore:
    return WasteRunnerSupervisorStore(
        tmp_path / "waste-runner-supervisor.json",
        tmp_path / "waste-runner-supervisor-audit.jsonl",
        lease_seconds=lease_seconds,
    )


def test_supervisor_blocks_duplicate_fresh_waste_runner_owner(tmp_path):
    store = _store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")

    runner = waste_runner.WasteRunner(
        strategize_fn=lambda state, analysis: None,
        supervisor_store=store,
        supervisor_owner_id="worker-b",
    )
    status = runner.start(interval_seconds=5)

    assert status["status"] == "SUPERVISOR_CONFLICT"
    assert status["running"] is False
    assert status["supervisor"]["active_lease"]["owner_id"] == "worker-a"
    assert status["supervisor"]["owned_by_this_process"] is False


def test_supervisor_store_raises_on_duplicate_fresh_owner(tmp_path):
    store = _store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")

    with pytest.raises(WasteRunnerSupervisorConflict):
        store.acquire(owner_id="worker-b", interval_seconds=5, mode="PAPER")


def test_stale_waste_runner_lease_can_be_taken_over(tmp_path):
    store = _store(tmp_path, lease_seconds=0)
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")

    lease = store.acquire(owner_id="worker-b", interval_seconds=10, mode="PAPER")

    assert lease["status"] == STATUS_LEASE_ACQUIRED
    assert lease["owner_id"] == "worker-b"
    assert lease["interval_seconds"] == 10


def test_new_acquire_clears_stale_stop_request_fields(tmp_path):
    store = _store(tmp_path, lease_seconds=0)
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    store.request_stop(requested_by="worker-b")

    store.acquire(owner_id="worker-c", interval_seconds=5, mode="PAPER")
    status = store.build_status(owner_id="api", local_running=False)

    assert status["desired_running"] is True
    assert status["active_lease"]["owner_id"] == "worker-c"
    assert status["stop_requested_at"] is None
    assert status["stop_requested_by"] is None


def test_renew_clears_stale_stop_request_fields(tmp_path):
    store = _store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    store.request_stop(requested_by="worker-b")

    ok, _lease = store.renew(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    status = store.build_status(owner_id="api", local_running=False)

    assert ok is True
    assert status["desired_running"] is True
    assert status["stop_requested_at"] is None
    assert status["stop_requested_by"] is None


def test_stop_request_from_non_owner_is_durable(tmp_path):
    store = _store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")

    status = store.request_stop(requested_by="worker-b")

    assert status["desired_running"] is False
    assert status["active_lease"]["owner_id"] == "worker-a"
    assert status["stop_requested_by"] == "worker-b"
    assert store.should_stop(owner_id="worker-a") is True


def test_runner_status_surfaces_supervisor_state(tmp_path):
    store = _store(tmp_path)
    runner = waste_runner.WasteRunner(
        strategize_fn=lambda state, analysis: None,
        supervisor_store=store,
        supervisor_owner_id="worker-a",
    )

    status = runner.status()

    assert status["supervisor"]["report_kind"] == "cas_forex_waste_runner_supervisor"
    assert status["supervisor"]["local_owner_id"] == "worker-a"
    assert status["supervisor"]["local_running"] is False


def test_recover_stop_requested_waste_lease_requires_confirm(tmp_path):
    store = _store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    store.request_stop(requested_by="worker-b")

    status = store.recover_stale_or_requested(requested_by="owner", confirm=False)

    assert status["status"] == "CONFIRM_REQUIRED"
    assert status["recovery"]["can_clear"] is True
    assert status["active_lease"]["owner_id"] == "worker-a"


def test_recover_stop_requested_waste_lease_clears(tmp_path):
    store = _store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")
    store.request_stop(requested_by="worker-b")

    status = store.recover_stale_or_requested(requested_by="owner", confirm=True)

    assert status["status"] == STATUS_RECOVERY_CLEARED
    assert status["active_lease"] is None
    assert status["desired_running"] is False
    assert status["recovery"]["cleared_lease"]["owner_id"] == "worker-a"


def test_recover_fresh_desired_waste_lease_refuses(tmp_path):
    store = _store(tmp_path)
    store.acquire(owner_id="worker-a", interval_seconds=5, mode="PAPER")

    status = store.recover_stale_or_requested(requested_by="owner", confirm=True)

    assert status["status"] == STATUS_RECOVERY_REFUSED
    assert status["active_lease"]["owner_id"] == "worker-a"
    assert status["recovery"]["can_clear"] is False
