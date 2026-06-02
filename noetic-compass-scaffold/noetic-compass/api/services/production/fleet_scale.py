"""Fleet-execution-at-scale seams (workstream 03, design-stage scaffold).

Import-isolated. Nothing here is wired into the live FastAPI app, the distributed
audit control plane (``cas_harness_distributed_audits``), or the in-process fleet
executor (``cas_harness_fleet_executor``). It exists so the blueprint in
``docs/working/production_readiness/03_fleet_execution_at_scale.md`` has concrete
Python seams the team can build against, plus one clearly-labeled in-memory stub
that lets the contract be exercised in a unit test without any real infra.

What this module is about
-------------------------
The shipped executor fans audit work out to at most ``MAX_WORKER_FANOUT == 512``
Probe Workers (``cas_harness_scale_planner.py:60``) and holds the whole fleet --
``_WORKERS`` / ``_FLEET_RUNS`` -- in process-global dicts
(``cas_harness_fleet_executor.py:159-161``). That is honest and correct for a
single-orchestrator, single-process run. It is *not* a fleet at scale: there is no
scheduler that places shards on capacity, no autoscaler, no backpressure, no
cross-process liveness, and no recovery of a run whose orchestrator process died.
This module defines the seams for those six capabilities.

Honesty rule (inherited from ``production/__init__.py``)
-------------------------------------------------------
A stub is a stub. No backend here may emit a ``*_VERIFIED`` / ``*_METERED`` /
``*_WORM_COMMITTED`` status, and nothing here may emit an audit ``ACCEPT``. The
scheduler/placement/backpressure/liveness/recovery seams only ever produce
*declared* / *observed* facts (a placement decision, a queue-depth reading, a
heartbeat-derived liveness state). Turning ``FLEET_PLACEMENT_DECLARED`` into
``FLEET_PLACEMENT_VERIFIED`` requires a real worker confirming it actually loaded
its assigned shard -- which only the worker tier can attest. The stub raises if you
ask it to mint a verified status, so a test cannot accidentally launder one.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Iterable, Literal, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Status vocabularies (declared-only at this tier; see module docstring)
# ---------------------------------------------------------------------------

# Placement is *declared* when the scheduler has chosen a worker for a shard; it is
# only *verified* once that worker confirms the shard actually resident. The stub
# never produces the VERIFIED rung.
FleetPlacementStatus = Literal[
    "FLEET_PLACEMENT_DECLARED",  # scheduler bound shard->worker (this tier may emit)
    "FLEET_PLACEMENT_VERIFIED",  # worker confirmed resident set (worker tier only)
    "FLEET_PLACEMENT_INFEASIBLE",  # no capacity slot can hold the shard
]

# Liveness is derived from heartbeats, mirroring FleetWorkerStatus in the executor
# (``cas_harness_fleet_executor.py:26``) but at fleet (cross-process) scope.
FleetLivenessStatus = Literal["live", "suspect", "lost"]

# Backpressure signal the scheduler emits upstream (to 04 queue, to the API admit
# gate, and to 05 observability). ADMIT/THROTTLE/SHED are advisory, never a verdict.
FleetAdmissionSignal = Literal["ADMIT", "THROTTLE", "SHED"]

# Scaling direction the autoscaler recommends. RECOMMEND-only at this tier: the stub
# computes a target worker count from observed demand but never claims it provisioned
# real hardware (that is a cloud-provider fact, declared->verified at the infra seam).
FleetScalingAction = Literal["SCALE_UP", "SCALE_DOWN", "HOLD"]


class FleetScaleStateError(ValueError):
    """Raised when a transition would make the fleet look more ready than it is."""


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkerSlot:
    """A unit of fleet capacity the scheduler can place a shard onto.

    ``free_capacity`` mirrors ``FleetWorkerRecord.capacity``
    (``cas_harness_fleet_executor.py:52``) but tracks *remaining* slots so the
    scheduler can bin-pack multiple shards onto one high-capacity worker.
    """

    worker_id: str
    model_id: str
    gpu_type: str
    usable_memory_gb: float
    free_capacity: int
    supported_methods: tuple[str, ...]
    tenant_id: str | None = None  # 06 partition key; None == default/single-tenant


@dataclass(frozen=True)
class ShardDemand:
    """One shard of audit work awaiting placement.

    Field names line up with ``WorkerAssignment`` (``cas_harness_scale_planner.py:152``)
    and ``FleetJobRecord`` (``cas_harness_fleet_executor.py:71``) so a real scheduler
    can be fed directly from a plan's ``worker_assignments``.
    """

    audit_id: str
    shard_id: str
    layer_start: int
    layer_end: int
    required_methods: tuple[str, ...]
    estimated_memory_gb: float
    tenant_id: str | None = None
    priority: int = 0  # higher first; ties broken by FIFO arrival


@dataclass(frozen=True)
class PlacementDecision:
    """The scheduler's binding of a shard to a worker slot (declared, not verified)."""

    audit_id: str
    shard_id: str
    worker_id: str
    status: FleetPlacementStatus
    reason: str
    decided_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        # Hard honesty guard: this tier may never mint a VERIFIED placement.
        if self.status == "FLEET_PLACEMENT_VERIFIED":
            raise FleetScaleStateError(
                "FLEET_PLACEMENT_VERIFIED is a worker-tier attestation; the scheduler "
                "may only declare a placement, never verify it."
            )


@dataclass(frozen=True)
class ScalingRecommendation:
    """Autoscaler output: a *recommended* target, never a provisioning claim."""

    action: FleetScalingAction
    current_workers: int
    target_workers: int
    pending_shards: int
    reason: str
    # Honest ceiling: the recommendation is clamped to the planner's fan-out cap so
    # the autoscaler can never recommend a fleet the rest of the system refuses.
    fanout_cap: int


@dataclass(frozen=True)
class BackpressureReading:
    """A queue-depth/inflight snapshot driving the admission signal."""

    queue_depth: int
    inflight: int
    capacity: int
    signal: FleetAdmissionSignal
    reason: str


@dataclass
class HeartbeatState:
    """Cross-process liveness derived from the last heartbeat instant."""

    worker_id: str
    last_heartbeat_at: str
    liveness: FleetLivenessStatus = "live"


# ---------------------------------------------------------------------------
# Seams (Protocol / ABC the team builds real backends against)
# ---------------------------------------------------------------------------


@runtime_checkable
class FleetScheduler(Protocol):
    """Places pending shards onto worker capacity. Declared placements only."""

    def offer_capacity(self, slot: WorkerSlot) -> None: ...

    def submit_shard(self, shard: ShardDemand) -> None: ...

    def schedule_once(self) -> list[PlacementDecision]:
        """Bin-pack currently-pending shards onto currently-free slots.

        Returns one decision per shard considered: ``FLEET_PLACEMENT_DECLARED`` when a
        slot was bound, ``FLEET_PLACEMENT_INFEASIBLE`` when no slot can hold it. Never
        returns ``FLEET_PLACEMENT_VERIFIED`` (worker-tier only).
        """
        ...

    def pending_count(self) -> int: ...


@runtime_checkable
class FleetAutoscaler(Protocol):
    """Recommends a target worker count from observed demand. Recommend-only."""

    def recommend(self, *, pending_shards: int, current_workers: int) -> ScalingRecommendation: ...


@runtime_checkable
class FleetBackpressure(Protocol):
    """Turns queue depth + inflight into an advisory admission signal."""

    def observe(self, *, queue_depth: int, inflight: int) -> BackpressureReading: ...


@runtime_checkable
class FleetLivenessMonitor(Protocol):
    """Cross-process heartbeat tracking + liveness derivation.

    Generalizes the executor's in-process ``_mark_stale_worker_if_expired``
    (``cas_harness_fleet_executor.py:598-610``) to a fleet that spans hosts.
    """

    def heartbeat(self, worker_id: str) -> HeartbeatState: ...

    def evaluate(self, *, now: datetime | None = None) -> list[HeartbeatState]: ...

    def lost_workers(self) -> list[str]: ...


class FleetRecoveryCoordinator(ABC):
    """Re-places shards stranded by a lost worker or a dead orchestrator.

    ABC (not Protocol) because a real coordinator carries durable state (it must read
    the 04 queue's leased-but-unreceipted jobs and re-enqueue them idempotently). The
    abstract method is the seam; the stub gives an in-memory re-enqueue.
    """

    @abstractmethod
    def reclaim(self, *, lost_worker_id: str) -> list[ShardDemand]:
        """Return shards that must be re-scheduled because ``lost_worker_id`` is gone.

        MUST be idempotent: reclaiming the same lost worker twice yields the same
        shard set once, never double-enqueues. A real impl reconciles against the
        durable queue (04) rather than guessing.
        """
        ...


# ---------------------------------------------------------------------------
# In-memory stubs (clearly labeled; emit declared/observed facts only)
# ---------------------------------------------------------------------------


# Mirrors the executor default (``cas_harness_fleet_executor.py:38``).
DEFAULT_MAX_HEARTBEAT_AGE_SECONDS = 120
# Mirrors the planner cap (``cas_harness_scale_planner.py:60``). Duplicated as a
# module constant rather than imported so this scaffold stays import-isolated from
# the live service graph; the test asserts the two agree.
STUB_FANOUT_CAP = 512


class InMemoryFleetScheduler:
    """STUB scheduler. Greedy first-fit bin-packing over in-memory slots.

    Honest by construction: it can only *declare* placements. It models capacity and
    method/model/tenant compatibility (the same predicates the executor's
    ``_assert_worker_can_run_job`` enforces, ``cas_harness_fleet_executor.py:549-559``)
    but never confirms a worker actually loaded a shard.
    """

    def __init__(self) -> None:
        self._slots: dict[str, WorkerSlot] = {}
        self._pending: deque[ShardDemand] = deque()

    def offer_capacity(self, slot: WorkerSlot) -> None:
        self._slots[slot.worker_id] = slot

    def submit_shard(self, shard: ShardDemand) -> None:
        self._pending.append(shard)

    def pending_count(self) -> int:
        return len(self._pending)

    def _eligible(self, shard: ShardDemand, slot: WorkerSlot) -> bool:
        if slot.free_capacity <= 0:
            return False
        # Tenant isolation (06 seam): a tenant-scoped shard may only land on a slot
        # of the same tenant (or an unpartitioned/default slot). A tenant-neutral
        # shard (tenant_id None) may land anywhere.
        if shard.tenant_id is not None and slot.tenant_id not in (None, shard.tenant_id):
            return False
        # Method compatibility -- same predicate as the executor's
        # _assert_worker_can_run_job (cas_harness_fleet_executor.py:555-559).
        if set(shard.required_methods) - set(slot.supported_methods):
            return False
        # Physical fit -- the shard's estimated resident memory must fit the slot's
        # usable memory (the per-shard analog of the compute-feasibility gate).
        if shard.estimated_memory_gb > slot.usable_memory_gb:
            return False
        return True

    def schedule_once(self) -> list[PlacementDecision]:
        decisions: list[PlacementDecision] = []
        # Priority high-to-low, then FIFO (stable on insertion order within a priority).
        ordered = sorted(self._pending, key=lambda s: -s.priority)
        remaining: deque[ShardDemand] = deque()
        # Mutable local view of free capacity so multiple shards can pack one worker.
        free = {wid: slot.free_capacity for wid, slot in self._slots.items()}
        for shard in ordered:
            placed = False
            for worker_id, slot in self._slots.items():
                if free[worker_id] <= 0:
                    continue
                # Re-evaluate eligibility with live free count.
                live_slot = WorkerSlot(
                    worker_id=slot.worker_id,
                    model_id=slot.model_id,
                    gpu_type=slot.gpu_type,
                    usable_memory_gb=slot.usable_memory_gb,
                    free_capacity=free[worker_id],
                    supported_methods=slot.supported_methods,
                    tenant_id=slot.tenant_id,
                )
                if self._eligible(shard, live_slot):
                    free[worker_id] -= 1
                    decisions.append(
                        PlacementDecision(
                            audit_id=shard.audit_id,
                            shard_id=shard.shard_id,
                            worker_id=worker_id,
                            status="FLEET_PLACEMENT_DECLARED",
                            reason="scheduler bound shard to a compatible free slot (DECLARED, not VERIFIED)",
                        )
                    )
                    placed = True
                    break
            if not placed:
                decisions.append(
                    PlacementDecision(
                        audit_id=shard.audit_id,
                        shard_id=shard.shard_id,
                        worker_id="",
                        status="FLEET_PLACEMENT_INFEASIBLE",
                        reason="no free, compatible worker slot can hold this shard right now",
                    )
                )
                remaining.append(shard)
        self._pending = remaining
        return decisions


class InMemoryFleetAutoscaler:
    """STUB autoscaler: when shards are pending, provision ``current + pending``
    workers (clamped to the fan-out cap) so the queue can drain; when nothing is
    pending, drain toward the floor (``min_workers``). The exact policy is
    illustrative only -- a real autoscaler (utilization targets, cooldown windows,
    predictive scaling) is future work and is NOT what this stub claims to be."""

    def __init__(self, *, fanout_cap: int = STUB_FANOUT_CAP, min_workers: int = 0) -> None:
        self._cap = fanout_cap
        self._min = min_workers

    def recommend(self, *, pending_shards: int, current_workers: int) -> ScalingRecommendation:
        if pending_shards < 0 or current_workers < 0:
            raise FleetScaleStateError("pending_shards and current_workers must be non-negative.")
        if pending_shards > 0:
            desired = min(self._cap, current_workers + pending_shards)
        else:
            desired = self._min
        desired = max(self._min, desired)
        if desired > current_workers:
            action: FleetScalingAction = "SCALE_UP"
            reason = f"{pending_shards} shard(s) pending; recommend {desired} workers (clamped to {self._cap})."
        elif desired < current_workers:
            action = "SCALE_DOWN"
            reason = f"no pending demand; recommend draining to {desired} workers."
        else:
            action = "HOLD"
            reason = "current worker count matches recommended target."
        return ScalingRecommendation(
            action=action,
            current_workers=current_workers,
            target_workers=desired,
            pending_shards=pending_shards,
            reason=reason,
            fanout_cap=self._cap,
        )


class InMemoryFleetBackpressure:
    """STUB backpressure. Watermark policy over capacity."""

    def __init__(self, *, throttle_ratio: float = 0.8, shed_ratio: float = 1.0) -> None:
        if not 0 < throttle_ratio <= shed_ratio:
            raise FleetScaleStateError("require 0 < throttle_ratio <= shed_ratio.")
        self._throttle = throttle_ratio
        self._shed = shed_ratio

    def observe(self, *, queue_depth: int, inflight: int, capacity: int = STUB_FANOUT_CAP) -> BackpressureReading:
        if capacity <= 0:
            raise FleetScaleStateError("capacity must be positive.")
        load = (inflight + queue_depth) / capacity
        if load >= self._shed:
            signal: FleetAdmissionSignal = "SHED"
            reason = f"load {load:.2f} >= shed watermark {self._shed:.2f}; reject new audits."
        elif load >= self._throttle:
            signal = "THROTTLE"
            reason = f"load {load:.2f} >= throttle watermark {self._throttle:.2f}; slow admission."
        else:
            signal = "ADMIT"
            reason = f"load {load:.2f} below throttle watermark {self._throttle:.2f}; admit."
        return BackpressureReading(
            queue_depth=queue_depth,
            inflight=inflight,
            capacity=capacity,
            signal=signal,
            reason=reason,
        )


class InMemoryFleetLivenessMonitor:
    """STUB liveness monitor. Heartbeat-age thresholds -> live/suspect/lost.

    Two thresholds so a brief miss is ``suspect`` (do not reclaim yet) before a hard
    ``lost`` (reclaim). This is the cross-process generalization of the executor's
    single stale cutoff (``cas_harness_fleet_executor.py:603-604``).
    """

    def __init__(
        self,
        *,
        suspect_after_seconds: int = DEFAULT_MAX_HEARTBEAT_AGE_SECONDS,
        lost_after_seconds: int = DEFAULT_MAX_HEARTBEAT_AGE_SECONDS * 2,
    ) -> None:
        if not 0 < suspect_after_seconds <= lost_after_seconds:
            raise FleetScaleStateError("require 0 < suspect_after_seconds <= lost_after_seconds.")
        self._suspect = suspect_after_seconds
        self._lost = lost_after_seconds
        self._states: dict[str, HeartbeatState] = {}

    def heartbeat(self, worker_id: str) -> HeartbeatState:
        if not worker_id.strip():
            raise FleetScaleStateError("worker_id is required.")
        state = HeartbeatState(
            worker_id=worker_id,
            last_heartbeat_at=datetime.now(UTC).isoformat(),
            liveness="live",
        )
        self._states[worker_id] = state
        return state

    def evaluate(self, *, now: datetime | None = None) -> list[HeartbeatState]:
        current = now or datetime.now(UTC)
        for state in self._states.values():
            age = (current - _parse_utc(state.last_heartbeat_at)).total_seconds()
            if age >= self._lost:
                state.liveness = "lost"
            elif age >= self._suspect:
                state.liveness = "suspect"
            else:
                state.liveness = "live"
        return list(self._states.values())

    def lost_workers(self) -> list[str]:
        return sorted(s.worker_id for s in self._states.values() if s.liveness == "lost")


class InMemoryFleetRecoveryCoordinator(FleetRecoveryCoordinator):
    """STUB recovery. Idempotent in-memory re-enqueue of a lost worker's shards.

    A real coordinator reconciles against the durable queue (04). This stub holds the
    shard->worker map in memory and proves the *idempotency contract*: reclaiming the
    same worker twice returns its shards once.
    """

    def __init__(self) -> None:
        self._assigned: dict[str, list[ShardDemand]] = {}
        self._reclaimed: set[str] = set()

    def assign(self, worker_id: str, shard: ShardDemand) -> None:
        self._assigned.setdefault(worker_id, []).append(shard)

    def reclaim(self, *, lost_worker_id: str) -> list[ShardDemand]:
        if lost_worker_id in self._reclaimed:
            return []  # idempotent: already reclaimed
        self._reclaimed.add(lost_worker_id)
        return list(self._assigned.get(lost_worker_id, []))


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
