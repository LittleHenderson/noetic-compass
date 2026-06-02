"""Contract tests for the workstream-03 fleet-scale scaffold.

These exercise the in-memory STUBS in ``api/services/production/fleet_scale.py``.
They prove the *seams* behave and -- most importantly -- that the honesty guards
hold: a stub can never mint a VERIFIED placement, and the autoscaler can never
recommend past the planner's fan-out cap.

Run ONLY this file (per the workstream brief):
    C:/Python314/python.exe -m pytest tests/test_production_fleet_scale.py -q
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from api.services.cas_harness_scale_planner import MAX_WORKER_FANOUT
from api.services.production.fleet_scale import (
    DEFAULT_MAX_HEARTBEAT_AGE_SECONDS,
    STUB_FANOUT_CAP,
    BackpressureReading,
    FleetScaleStateError,
    InMemoryFleetAutoscaler,
    InMemoryFleetBackpressure,
    InMemoryFleetLivenessMonitor,
    InMemoryFleetRecoveryCoordinator,
    InMemoryFleetScheduler,
    PlacementDecision,
    ShardDemand,
    WorkerSlot,
)


def _slot(worker_id: str, *, free: int = 1, mem: float = 50.0, methods=("foundation_probe",), tenant=None) -> WorkerSlot:
    return WorkerSlot(
        worker_id=worker_id,
        model_id="customer/open-weight-20b",
        gpu_type="H100-80GB",
        usable_memory_gb=mem,
        free_capacity=free,
        supported_methods=tuple(methods),
        tenant_id=tenant,
    )


def _shard(shard_id: str, *, mem: float = 10.0, methods=("foundation_probe",), priority: int = 0, tenant=None) -> ShardDemand:
    return ShardDemand(
        audit_id="cas-dist-abc123",
        shard_id=shard_id,
        layer_start=0,
        layer_end=3,
        required_methods=tuple(methods),
        estimated_memory_gb=mem,
        tenant_id=tenant,
        priority=priority,
    )


# --- honesty guards --------------------------------------------------------


def test_stub_fanout_cap_agrees_with_planner_constant():
    # The scaffold duplicates the cap to stay import-isolated; it must not drift.
    assert STUB_FANOUT_CAP == MAX_WORKER_FANOUT == 512


def test_placement_decision_cannot_be_minted_verified():
    with pytest.raises(FleetScaleStateError, match="worker-tier attestation"):
        PlacementDecision(
            audit_id="cas-dist-abc123",
            shard_id="layers-000-003",
            worker_id="probe-worker-01",
            status="FLEET_PLACEMENT_VERIFIED",
            reason="attempting to launder a verified status from this tier",
        )


def test_scheduler_only_emits_declared_or_infeasible():
    sched = InMemoryFleetScheduler()
    sched.offer_capacity(_slot("probe-worker-01"))
    sched.submit_shard(_shard("layers-000-003"))
    decisions = sched.schedule_once()
    assert {d.status for d in decisions} <= {"FLEET_PLACEMENT_DECLARED", "FLEET_PLACEMENT_INFEASIBLE"}
    assert all(d.status != "FLEET_PLACEMENT_VERIFIED" for d in decisions)


# --- scheduler / placement -------------------------------------------------


def test_scheduler_places_compatible_shard():
    sched = InMemoryFleetScheduler()
    sched.offer_capacity(_slot("probe-worker-01"))
    sched.submit_shard(_shard("layers-000-003"))
    [decision] = sched.schedule_once()
    assert decision.status == "FLEET_PLACEMENT_DECLARED"
    assert decision.worker_id == "probe-worker-01"
    assert sched.pending_count() == 0


def test_scheduler_marks_infeasible_when_method_unsupported():
    sched = InMemoryFleetScheduler()
    sched.offer_capacity(_slot("probe-worker-01", methods=("foundation_probe",)))
    sched.submit_shard(_shard("layers-000-003", methods=("targeted_ablation",)))
    [decision] = sched.schedule_once()
    assert decision.status == "FLEET_PLACEMENT_INFEASIBLE"
    # Infeasible shard stays pending for a later pass (after autoscale/new capacity).
    assert sched.pending_count() == 1


def test_scheduler_marks_infeasible_when_shard_too_large():
    sched = InMemoryFleetScheduler()
    sched.offer_capacity(_slot("probe-worker-01", mem=8.0))
    sched.submit_shard(_shard("layers-000-003", mem=40.0))
    [decision] = sched.schedule_once()
    assert decision.status == "FLEET_PLACEMENT_INFEASIBLE"


def test_scheduler_bin_packs_two_shards_onto_one_high_capacity_worker():
    sched = InMemoryFleetScheduler()
    sched.offer_capacity(_slot("probe-worker-01", free=2))
    sched.submit_shard(_shard("layers-000-003"))
    sched.submit_shard(_shard("layers-004-007"))
    decisions = sched.schedule_once()
    assert all(d.status == "FLEET_PLACEMENT_DECLARED" for d in decisions)
    assert {d.worker_id for d in decisions} == {"probe-worker-01"}
    assert sched.pending_count() == 0


def test_scheduler_respects_priority_order():
    sched = InMemoryFleetScheduler()
    sched.offer_capacity(_slot("probe-worker-01", free=1))
    sched.submit_shard(_shard("low", priority=0))
    sched.submit_shard(_shard("high", priority=10))
    decisions = sched.schedule_once()
    placed = [d for d in decisions if d.status == "FLEET_PLACEMENT_DECLARED"]
    assert len(placed) == 1
    assert placed[0].shard_id == "high"


def test_scheduler_enforces_tenant_isolation():
    sched = InMemoryFleetScheduler()
    sched.offer_capacity(_slot("probe-worker-01", tenant="tenant-a"))
    sched.submit_shard(_shard("layers-000-003", tenant="tenant-b"))
    [decision] = sched.schedule_once()
    assert decision.status == "FLEET_PLACEMENT_INFEASIBLE"


# --- autoscaler ------------------------------------------------------------


def test_autoscaler_recommends_scale_up_for_pending_demand():
    auto = InMemoryFleetAutoscaler()
    rec = auto.recommend(pending_shards=5, current_workers=2)
    assert rec.action == "SCALE_UP"
    assert rec.target_workers == 7


def test_autoscaler_clamps_to_fanout_cap():
    auto = InMemoryFleetAutoscaler()
    rec = auto.recommend(pending_shards=10_000, current_workers=0)
    assert rec.target_workers == STUB_FANOUT_CAP == 512
    assert rec.fanout_cap == 512


def test_autoscaler_recommends_scale_down_when_idle():
    auto = InMemoryFleetAutoscaler(min_workers=0)
    rec = auto.recommend(pending_shards=0, current_workers=4)
    assert rec.action == "SCALE_DOWN"
    assert rec.target_workers == 0


def test_autoscaler_holds_when_balanced():
    auto = InMemoryFleetAutoscaler()
    rec = auto.recommend(pending_shards=0, current_workers=0)
    assert rec.action == "HOLD"


# --- backpressure ----------------------------------------------------------


def test_backpressure_admits_below_watermark():
    bp = InMemoryFleetBackpressure()
    reading = bp.observe(queue_depth=10, inflight=10, capacity=100)
    assert isinstance(reading, BackpressureReading)
    assert reading.signal == "ADMIT"


def test_backpressure_throttles_at_high_load():
    bp = InMemoryFleetBackpressure(throttle_ratio=0.8, shed_ratio=1.0)
    reading = bp.observe(queue_depth=50, inflight=35, capacity=100)
    assert reading.signal == "THROTTLE"


def test_backpressure_sheds_at_capacity():
    bp = InMemoryFleetBackpressure()
    reading = bp.observe(queue_depth=60, inflight=60, capacity=100)
    assert reading.signal == "SHED"


# --- liveness --------------------------------------------------------------


def test_liveness_fresh_heartbeat_is_live():
    mon = InMemoryFleetLivenessMonitor()
    mon.heartbeat("probe-worker-01")
    [state] = mon.evaluate()
    assert state.liveness == "live"
    assert mon.lost_workers() == []


def test_liveness_progresses_suspect_then_lost():
    mon = InMemoryFleetLivenessMonitor(suspect_after_seconds=60, lost_after_seconds=120)
    mon.heartbeat("probe-worker-01")
    now = datetime.now(UTC)

    [suspect] = mon.evaluate(now=now + timedelta(seconds=90))
    assert suspect.liveness == "suspect"
    assert mon.lost_workers() == []  # not yet reclaimable

    [lost] = mon.evaluate(now=now + timedelta(seconds=200))
    assert lost.liveness == "lost"
    assert mon.lost_workers() == ["probe-worker-01"]


def test_liveness_default_thresholds_match_executor_default():
    mon = InMemoryFleetLivenessMonitor()
    # suspect cutoff mirrors the executor's single stale cutoff
    assert mon._suspect == DEFAULT_MAX_HEARTBEAT_AGE_SECONDS == 120  # noqa: SLF001


# --- recovery (idempotency contract) ---------------------------------------


def test_recovery_returns_lost_worker_shards_once():
    coord = InMemoryFleetRecoveryCoordinator()
    shard = _shard("layers-000-003")
    coord.assign("probe-worker-01", shard)

    first = coord.reclaim(lost_worker_id="probe-worker-01")
    assert [s.shard_id for s in first] == ["layers-000-003"]

    # Idempotent: a second reclaim of the same worker must NOT double-enqueue.
    second = coord.reclaim(lost_worker_id="probe-worker-01")
    assert second == []


def test_recovery_unknown_worker_yields_nothing():
    coord = InMemoryFleetRecoveryCoordinator()
    assert coord.reclaim(lost_worker_id="never-seen") == []
