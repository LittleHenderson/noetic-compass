"""Distributed CAS Harness worker fleet executor.

This module sits one layer below the distributed audit control plane. The
control plane creates layer/shard assignments; the fleet executor proves those
assignments are backed by registered Probe Workers, leases jobs to those
workers, tracks heartbeats, accepts Evidence Packet fragment receipts, and
only then opens the merge gate for verifier review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import json
from typing import Any, Mapping, Literal

from api.services.cas_harness_distributed_audits import (
    DistributedAuditStateError,
    get_distributed_audit,
    merge_distributed_audit,
    record_worker_evidence,
)
from api.services.production.state_substrate import INTERIM_TENANT, LedgerMirror, StateStore


FleetWorkerStatus = Literal["active", "stale", "offline"]
FleetJobStatus = Literal["queued", "leased", "completed", "failed", "expired"]
FleetVerifierGateStatus = Literal[
    "not_prepared",
    "waiting_for_workers",
    "waiting_for_receipts",
    "blocked_failed_worker",
    "blocked_missing_outputs",
    "ready_for_verifier",
]
FleetReadinessStatus = Literal["blocked", "waiting", "ready"]

DEFAULT_MAX_HEARTBEAT_AGE_SECONDS = 120


class FleetExecutorStateError(ValueError):
    """Raised when a fleet transition would make the audit look more ready than it is."""


@dataclass
class FleetWorkerRecord:
    worker_id: str
    model_id: str
    worker_url: str
    gpu_type: str
    capacity: int
    supported_methods: tuple[str, ...]
    registered_at: str
    last_heartbeat_at: str
    # ``None`` keeps the historical single-tenant namespace. Service-auth workers bind to one
    # audit/fleet so identical public worker IDs in different tenants cannot touch each other.
    audit_id: str | None = None
    status: FleetWorkerStatus = "active"

    def to_dict(self) -> dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "model_id": self.model_id,
            "worker_url": self.worker_url,
            "gpu_type": self.gpu_type,
            "capacity": self.capacity,
            "supported_methods": list(self.supported_methods),
            "registered_at": self.registered_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "status": self.status,
        }


@dataclass
class FleetJobRecord:
    job_id: str
    audit_id: str
    assigned_worker_id: str
    layer_start: int
    layer_end: int
    shard_id: str
    assigned_methods: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    status: FleetJobStatus = "queued"
    lease_token: str | None = None
    lease_token_hash: str | None = None
    lease_expires_at: str | None = None
    evidence_packet_fragment_ref: str | None = None
    evidence_packet_fragment_payload: dict[str, Any] | None = None
    produced_outputs: tuple[str, ...] = ()
    missing_outputs: tuple[str, ...] = ()
    error_message: str | None = None
    updated_at: str = field(default_factory=lambda: _utc_now())

    def to_dict(self, *, include_lease_token: bool = False) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "audit_id": self.audit_id,
            "assigned_worker_id": self.assigned_worker_id,
            "layer_start": self.layer_start,
            "layer_end": self.layer_end,
            "shard_id": self.shard_id,
            "assigned_methods": list(self.assigned_methods),
            "expected_outputs": list(self.expected_outputs),
            "status": self.status,
            "lease_token": self.lease_token if include_lease_token else None,
            "lease_expires_at": self.lease_expires_at,
            "evidence_packet_fragment_ref": self.evidence_packet_fragment_ref,
            "evidence_packet_fragment_payload_sha256": _fragment_payload_sha256(
                self.evidence_packet_fragment_payload
            )
            if self.evidence_packet_fragment_payload is not None
            else None,
            "produced_outputs": list(self.produced_outputs),
            "missing_outputs": list(self.missing_outputs),
            "error_message": self.error_message,
            "updated_at": self.updated_at,
        }


@dataclass
class FleetRunRecord:
    audit_id: str
    status: Literal["PREPARED", "LEASING", "MERGE_PENDING", "COMPLETE", "FAILED"]
    verifier_gate_status: FleetVerifierGateStatus
    jobs: list[FleetJobRecord]
    created_at: str
    updated_at: str
    require_scoped_workers: bool = False
    merged_packet_trace_id: str | None = None
    merge_reason: str = "Fleet jobs prepared; waiting for registered workers and receipts."

    def to_dict(self) -> dict[str, object]:
        stale_workers = _stale_assigned_workers(self)
        completed = [job for job in self.jobs if job.status == "completed"]
        failed = [job for job in self.jobs if job.status == "failed"]
        leased = [job for job in self.jobs if job.status == "leased"]
        return {
            "audit_id": self.audit_id,
            "status": self.status,
            "verifier_gate_status": self.verifier_gate_status,
            "merged_packet_trace_id": self.merged_packet_trace_id,
            "merge_reason": self.merge_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_jobs": len(self.jobs),
            "leased_jobs": len(leased),
            "completed_fragments": len(completed),
            "failed_jobs": len(failed),
            "registered_workers": sum(
                1
                for job in self.jobs
                if _job_has_ready_worker(
                    job, require_scoped=self.require_scoped_workers
                )
            ),
            "stale_workers": stale_workers,
            "readiness": _readiness_payload(
                run=self,
                stale_workers=stale_workers,
                completed_jobs=completed,
                failed_jobs=failed,
                leased_jobs=leased,
            ),
            "jobs": [job.to_dict(include_lease_token=False) for job in self.jobs],
        }


_WORKERS: dict[str, FleetWorkerRecord] = {}
_FLEET_RUNS: dict[str, FleetRunRecord] = {}
_FRAGMENT_REFS: set[str] = set()

# --- durable state substrate mirror (docs 10 strangler-fig migration) ------
# Dark by default: with no mirror installed the _mirror_*/_shadow_* helpers are
# no-ops, so production and every existing test see zero behaviour change. The
# Phase 1/2 migration test installs an InMemoryStateStore-backed mirror to prove
# the ledger faithfully shadows _WORKERS / _FLEET_RUNS / _FRAGMENT_REFS.
#
# Phase-0 mapping decision (honest projection, not the rendered view): a record's
# to_dict() folds in DERIVED fields -- worker `status` is a function of
# (last_heartbeat_at, now); a run's verifier_gate_status / merge_reason / readiness /
# stale_workers are recomputed from jobs + workers + clock on every read. Storing a
# derived view in a durable ledger would be storing a stale snapshot. So the ledger
# keeps only durable STATE (the heartbeat fact, the run's own status, each job's own
# fields) and lets the views be recomputed at read time -- exactly what a Phase-3
# reload from the ledger would have to do. This also keeps dual-write tractable:
# read-triggered staleness marking no longer perturbs a record's stored payload.
_STATE_MIRROR: LedgerMirror | None = None
_WORKER_KIND = "worker"
_RUN_KIND = "fleet_run"
_FRAGMENT_KIND = "fragment_ref"
_MIRROR_SOURCE = "cas_harness_fleet_executor"


def set_state_mirror(mirror: LedgerMirror | None) -> None:
    """Install (or clear) the dual-write/shadow-read ledger mirror for this service."""
    global _STATE_MIRROR
    _STATE_MIRROR = mirror


def _worker_ledger_payload(worker: FleetWorkerRecord) -> dict[str, object]:
    """Durable worker STATE. `status` is a derived view of (last_heartbeat_at, now),
    recomputed on read, so it is deliberately excluded -- the ledger stores the
    heartbeat fact, not a staleness snapshot."""
    return {
        "worker_id": worker.worker_id,
        "audit_id": worker.audit_id,
        "model_id": worker.model_id,
        "worker_url": worker.worker_url,
        "gpu_type": worker.gpu_type,
        "capacity": worker.capacity,
        "supported_methods": list(worker.supported_methods),
        "registered_at": worker.registered_at,
        "last_heartbeat_at": worker.last_heartbeat_at,
    }


def _job_ledger_payload(job: FleetJobRecord) -> dict[str, object]:
    """Durable job STATE -- the stable projection a run row stores and a restart rebuilds.

    Two fields ``FleetJobRecord.to_dict`` renders are deliberately excluded because they
    are not durable state of the job:

    * ``lease_token`` -- a secret capability, never persisted (``to_dict`` already redacts
      it under ``include_lease_token=False``); a lease cannot survive a restart, so the
      token is not state to keep.
    * ``evidence_packet_fragment_payload_sha256`` -- a derived digest of the raw
      ``evidence_packet_fragment_payload``, which the ledger does NOT own. The durable,
      content-addressed handle is ``evidence_packet_fragment_ref`` (kept below); the raw
      payload lives in the WORM evidence store. A digest of bytes the run-ledger does not
      hold is a view, not state, so storing it would be storing something a cold reload
      cannot reproduce.

    Everything else is the job's own state and round-trips through rehydrate."""
    return {
        "job_id": job.job_id,
        "audit_id": job.audit_id,
        "assigned_worker_id": job.assigned_worker_id,
        "layer_start": job.layer_start,
        "layer_end": job.layer_end,
        "shard_id": job.shard_id,
        "assigned_methods": list(job.assigned_methods),
        "expected_outputs": list(job.expected_outputs),
        "status": job.status,
        "lease_expires_at": job.lease_expires_at,
        "evidence_packet_fragment_ref": job.evidence_packet_fragment_ref,
        "produced_outputs": list(job.produced_outputs),
        "missing_outputs": list(job.missing_outputs),
        "error_message": job.error_message,
        "updated_at": job.updated_at,
    }


def _run_ledger_payload(run: FleetRunRecord) -> dict[str, object]:
    """Durable run STATE. verifier_gate_status / merge_reason and the to_dict()
    aggregates (readiness, stale_workers, registered_workers, counts) are all
    recomputed from jobs + workers + clock on read, so they are views, not state, and
    are excluded. Each job's own fields are kept via :func:`_job_ledger_payload` (which
    likewise drops the job's two derived/secret fields)."""
    return {
        "audit_id": run.audit_id,
        "status": run.status,
        "require_scoped_workers": run.require_scoped_workers,
        "merged_packet_trace_id": run.merged_packet_trace_id,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "jobs": [_job_ledger_payload(job) for job in run.jobs],
    }


# Phase 3 write-through (see _mirror_audit in the distributed-audits service for the
# full rationale): when a mirror is installed, each dual-write also (re)assigns the dict
# entry, so under read-authority -- where get_*/list_* return fresh ledger
# reconstructions rather than the dict instance -- the dict stays a faithful cache and
# rollback to dict-authority is always safe. Guarded by `_STATE_MIRROR is not None`, so
# production (no mirror) is byte-for-byte unchanged.
def _mirror_worker(worker: FleetWorkerRecord) -> FleetWorkerRecord:
    if _STATE_MIRROR is not None:
        record_id = _worker_key(worker.worker_id, worker.audit_id)
        _WORKERS[record_id] = worker
        _STATE_MIRROR.mirror_put(
            _WORKER_KIND, record_id, _worker_ledger_payload(worker),
            source=_MIRROR_SOURCE, trace_id=worker.worker_id,
        )
    return worker


def _mirror_run(run: FleetRunRecord) -> FleetRunRecord:
    if _STATE_MIRROR is not None:
        _FLEET_RUNS[run.audit_id] = run
        _STATE_MIRROR.mirror_put(
            _RUN_KIND, run.audit_id, _run_ledger_payload(run),
            source=_MIRROR_SOURCE, trace_id=run.audit_id, parent_ids=(run.audit_id,),
        )
    return run


def _mirror_fragment(fragment_ref: str, *, audit_id: str, job_id: str) -> None:
    if _STATE_MIRROR is not None:
        _FRAGMENT_REFS.add(fragment_ref)
        _STATE_MIRROR.mirror_put(
            _FRAGMENT_KIND, fragment_ref, {"fragment_ref": fragment_ref},
            source=_MIRROR_SOURCE, trace_id=audit_id, parent_ids=(audit_id, job_id),
        )


def _shadow_run(run: FleetRunRecord) -> FleetRunRecord:
    if _STATE_MIRROR is not None:
        _STATE_MIRROR.shadow_compare(_RUN_KIND, run.audit_id, _run_ledger_payload(run))
    return run


def reset_fleet_executor_for_tests() -> None:
    _WORKERS.clear()
    _FLEET_RUNS.clear()
    _FRAGMENT_REFS.clear()
    # The mirror is test-only scaffolding; clearing it here keeps it from leaking
    # across tests via the shared reset fixture.
    set_state_mirror(None)
    from api.services.cas_harness_merged_evidence_packets import (
        reset_merged_fleet_evidence_packets_for_tests,
    )

    reset_merged_fleet_evidence_packets_for_tests()


# --- rehydrate-on-startup (docs 10 Phase-3 prerequisite) -------------------
# A restart loses _WORKERS / _FLEET_RUNS / _FRAGMENT_REFS -- the only place this
# single-process design holds fleet state. Before read-authority can move off the
# dicts, a restarted process must rebuild them from the durable ledger. These are the
# read inverses of the dual-write projections (_worker_ledger_payload, _run_ledger_payload
# / _job_ledger_payload, and the fragment_ref rows).


def _worker_from_ledger_payload(
    payload: Mapping[str, object], *, cutoff: datetime
) -> FleetWorkerRecord:
    """Rebuild a worker from its durable row and RE-DERIVE its staleness view.

    ``status`` is a function of (last_heartbeat_at, now) and is excluded from the stored
    projection, so it is recomputed here exactly as :func:`_mark_stale_worker_if_expired`
    would -- but inline, without that helper's lease-expiry side effect (rehydrated leases
    are already dropped, see :func:`_job_from_ledger_payload`)."""
    worker = FleetWorkerRecord(
        worker_id=payload["worker_id"],
        model_id=payload["model_id"],
        worker_url=payload["worker_url"],
        gpu_type=payload["gpu_type"],
        capacity=payload["capacity"],
        supported_methods=tuple(payload["supported_methods"]),
        registered_at=payload["registered_at"],
        last_heartbeat_at=payload["last_heartbeat_at"],
        audit_id=payload.get("audit_id"),
    )
    worker.status = "stale" if _parse_utc(worker.last_heartbeat_at) < cutoff else "active"
    return worker


def _job_from_ledger_payload(payload: Mapping[str, object]) -> FleetJobRecord:
    """Rebuild a job from its durable row, honestly dropping any in-flight lease.

    The lease token was never persisted (it is a secret capability redacted from the
    projection), so a lease cannot survive a restart: a stored ``leased`` job comes back
    ``expired`` -- a worker must re-lease to resume it, and nothing is left looking held
    by a token no one has. The raw ``evidence_packet_fragment_payload`` is likewise not in
    the run ledger (only its content-addressed ref is), so it reloads as ``None``; the
    durable ``evidence_packet_fragment_ref`` is preserved."""
    stored_status = payload["status"]
    status = "expired" if stored_status == "leased" else stored_status
    return FleetJobRecord(
        job_id=payload["job_id"],
        audit_id=payload["audit_id"],
        assigned_worker_id=payload["assigned_worker_id"],
        layer_start=payload["layer_start"],
        layer_end=payload["layer_end"],
        shard_id=payload["shard_id"],
        assigned_methods=tuple(payload["assigned_methods"]),
        expected_outputs=tuple(payload["expected_outputs"]),
        status=status,
        lease_token=None,
        lease_token_hash=None,
        lease_expires_at=payload["lease_expires_at"],
        evidence_packet_fragment_ref=payload["evidence_packet_fragment_ref"],
        evidence_packet_fragment_payload=None,
        produced_outputs=tuple(payload["produced_outputs"]),
        missing_outputs=tuple(payload["missing_outputs"]),
        error_message=payload["error_message"],
        updated_at=payload["updated_at"],
    )


def _run_from_ledger_payload(payload: Mapping[str, object]) -> FleetRunRecord:
    """Rebuild a run shell from its durable row; gate views are re-derived afterwards.

    ``verifier_gate_status`` and ``merge_reason`` are recomputed views excluded from the
    stored projection, so a neutral placeholder is installed and :func:`_refresh_run_gate`
    re-derives both once the workers are back in ``_WORKERS``."""
    return FleetRunRecord(
        audit_id=payload["audit_id"],
        status=payload["status"],
        verifier_gate_status="waiting_for_workers",
        jobs=[_job_from_ledger_payload(job) for job in payload["jobs"]],
        created_at=payload["created_at"],
        updated_at=payload["updated_at"],
        require_scoped_workers=bool(payload.get("require_scoped_workers", False)),
        merged_packet_trace_id=payload["merged_packet_trace_id"],
    )


def rehydrate_from_ledger(store: StateStore) -> dict[str, int]:
    """Rebuild _WORKERS / _FLEET_RUNS / _FRAGMENT_REFS from the durable ledger.

    Returns the count restored per kind. Like the distributed-audit rehydrate, this is the
    read inverse of the dual-write: it does NOT swallow backend errors (a half-restored
    fleet must fail loudly, not look authoritative) and it builds into fresh containers
    swapped in only once every row rebuilds.

    Order is load-bearing: workers first, then runs, then re-derive the run-gate views --
    because :func:`_refresh_run_gate` reads ``_WORKERS`` to decide each run's gate, the
    workers must be installed before the gate is computed. Two honest restart consequences
    are baked in: a worker's staleness is re-derived from its heartbeat (``status`` is not
    stored), and any in-flight lease is dropped (the token was never persisted), so a
    previously ``leased`` job returns ``expired``.

    This is the read side of the docs-10 cutover prerequisite. It makes the dicts
    survivable; it does not move read authority onto the ledger -- that is a later,
    separately gated step.
    """
    cutoff = datetime.now(UTC) - timedelta(seconds=DEFAULT_MAX_HEARTBEAT_AGE_SECONDS)

    workers: dict[str, FleetWorkerRecord] = {}
    for record in store.list(INTERIM_TENANT, _WORKER_KIND):
        worker = _worker_from_ledger_payload(record.payload, cutoff=cutoff)
        workers[_worker_key(worker.worker_id, worker.audit_id)] = worker

    runs: dict[str, FleetRunRecord] = {}
    for record in store.list(INTERIM_TENANT, _RUN_KIND):
        run = _run_from_ledger_payload(record.payload)
        runs[run.audit_id] = run

    fragments = {record.record_id for record in store.list(INTERIM_TENANT, _FRAGMENT_KIND)}

    _WORKERS.clear()
    _WORKERS.update(workers)
    _FLEET_RUNS.clear()
    _FLEET_RUNS.update(runs)
    _FRAGMENT_REFS.clear()
    _FRAGMENT_REFS.update(fragments)

    for run in _FLEET_RUNS.values():
        _refresh_run_gate(run)

    return {
        "workers": len(_WORKERS),
        "fleet_runs": len(_FLEET_RUNS),
        "fragment_refs": len(_FRAGMENT_REFS),
    }


def register_worker(
    *,
    worker_id: str,
    model_id: str,
    worker_url: str,
    gpu_type: str,
    supported_methods: list[str],
    capacity: int = 1,
    audit_id: str | None = None,
) -> FleetWorkerRecord:
    _require_nonempty(worker_id, "worker_id")
    _require_nonempty(model_id, "model_id")
    _require_nonempty(worker_url, "worker_url")
    _require_nonempty(gpu_type, "gpu_type")
    if capacity <= 0:
        raise FleetExecutorStateError("Worker capacity must be positive.")
    methods = tuple(_dedupe_nonempty(supported_methods))
    if not methods:
        raise FleetExecutorStateError("Worker registration requires at least one supported method.")
    scoped_audit_id = audit_id.strip() if audit_id is not None else None
    key = _worker_key(worker_id.strip(), scoped_audit_id)
    existing = _WORKERS.get(key)
    if existing is not None:
        raise FleetExecutorStateError("Worker ID is already registered; heartbeat the existing worker instead.")

    now = _utc_now()
    record = FleetWorkerRecord(
        worker_id=worker_id.strip(),
        model_id=model_id.strip(),
        worker_url=worker_url.strip(),
        gpu_type=gpu_type.strip(),
        capacity=capacity,
        supported_methods=methods,
        registered_at=now,
        last_heartbeat_at=now,
        audit_id=scoped_audit_id,
    )
    _WORKERS[key] = record
    return _mirror_worker(record)


def heartbeat_worker(worker_id: str, *, audit_id: str | None = None) -> FleetWorkerRecord | None:
    worker = _worker_for(audit_id, worker_id, legacy_fallback=audit_id is None)
    if worker is None:
        return None
    if _mark_stale_worker_if_expired(worker):
        _expire_worker_leases(worker.worker_id, audit_id=worker.audit_id)
    worker.status = "active"
    worker.last_heartbeat_at = _utc_now()
    return _mirror_worker(worker)


def list_workers(*, audit_id: str | None = None) -> list[FleetWorkerRecord]:
    # Phase 3 read-authority: reconstruct workers from the ledger, re-deriving each one's
    # staleness from its heartbeat against the same cutoff rehydrate uses (status is a
    # view, never stored). Dark by default (no mirror -> the dict path below).
    if _STATE_MIRROR is not None and _STATE_MIRROR.read_from_ledger:
        cutoff = datetime.now(UTC) - timedelta(seconds=DEFAULT_MAX_HEARTBEAT_AGE_SECONDS)
        payloads = _STATE_MIRROR.read_all_payloads(_WORKER_KIND)
        workers = [_worker_from_ledger_payload(payload, cutoff=cutoff) for payload in payloads.values()]
        return [worker for worker in workers if audit_id is None or worker.audit_id == audit_id]
    workers = [
        worker
        for worker in _WORKERS.values()
        if audit_id is None or worker.audit_id == audit_id
    ]
    if _STATE_MIRROR is not None:
        _STATE_MIRROR.shadow_compare_all(
            _WORKER_KIND,
            {_worker_key(w.worker_id, w.audit_id): _worker_ledger_payload(w) for w in workers},
        )
    return workers


def mark_stale_workers(*, max_heartbeat_age_seconds: int = DEFAULT_MAX_HEARTBEAT_AGE_SECONDS) -> list[FleetWorkerRecord]:
    if max_heartbeat_age_seconds <= 0:
        raise FleetExecutorStateError("max_heartbeat_age_seconds must be positive.")
    stale: list[FleetWorkerRecord] = []
    for worker in _WORKERS.values():
        if _mark_stale_worker_if_expired(
            worker,
            max_heartbeat_age_seconds=max_heartbeat_age_seconds,
        ):
            stale.append(worker)
    return stale


def prepare_fleet_for_audit(
    audit_id: str, *, require_scoped_workers: bool = False
) -> FleetRunRecord | None:
    audit = get_distributed_audit(audit_id)
    if audit is None:
        return None
    if audit.status == "PLANNED":
        raise FleetExecutorStateError("Dispatch the distributed audit before preparing fleet jobs.")

    existing = _FLEET_RUNS.get(audit_id)
    if existing is not None:
        return _shadow_run(existing)

    now = _utc_now()
    jobs = [
        FleetJobRecord(
            job_id=_job_id_for(audit_id, worker.worker_id, worker.shard_id),
            audit_id=audit_id,
            assigned_worker_id=worker.worker_id,
            layer_start=worker.layer_start,
            layer_end=worker.layer_end,
            shard_id=worker.shard_id,
            assigned_methods=worker.assigned_methods,
            expected_outputs=worker.expected_outputs,
            updated_at=now,
        )
        for worker in audit.worker_evidence
    ]
    record = FleetRunRecord(
        audit_id=audit_id,
        status="PREPARED",
        verifier_gate_status="waiting_for_workers",
        jobs=jobs,
        created_at=now,
        updated_at=now,
        require_scoped_workers=require_scoped_workers,
    )
    _FLEET_RUNS[audit_id] = record
    _refresh_run_gate(record)
    return _mirror_run(record)


def get_fleet_run(audit_id: str) -> FleetRunRecord | None:
    # Phase 3 read-authority: reconstruct the run's STORED state (status, jobs,
    # timestamps) from the ledger, then re-derive its gate exactly as the dict path does
    # -- _refresh_run_gate reads the worker cache, which the write-through keeps identical
    # to the ledger (zero divergence). The gate is a derived view in BOTH modes; this flip
    # moves authority for stored state, not the ACCEPT-gating logic. Dark by default.
    if _STATE_MIRROR is not None and _STATE_MIRROR.read_from_ledger:
        payload = _STATE_MIRROR.read_payload(_RUN_KIND, audit_id)
        if payload is None:
            return None
        run = _run_from_ledger_payload(payload)
        _refresh_run_gate(run)
        return run
    run = _FLEET_RUNS.get(audit_id)
    if run is not None:
        _refresh_run_gate(run)
        return _shadow_run(run)
    return None


def list_fleet_runs() -> list[FleetRunRecord]:
    if _STATE_MIRROR is not None and _STATE_MIRROR.read_from_ledger:
        payloads = _STATE_MIRROR.read_all_payloads(_RUN_KIND)
        runs = [_run_from_ledger_payload(payload) for payload in payloads.values()]
        for run in runs:
            _refresh_run_gate(run)
        return runs
    runs = list(_FLEET_RUNS.values())
    for run in runs:
        _refresh_run_gate(run)
    if _STATE_MIRROR is not None:
        _STATE_MIRROR.shadow_compare_all(
            _RUN_KIND, {r.audit_id: _run_ledger_payload(r) for r in runs}
        )
    return runs


def lease_next_job(
    *,
    audit_id: str,
    worker_id: str,
    lease_seconds: int = 900,
    require_scoped_worker: bool = False,
) -> FleetJobRecord | None:
    if lease_seconds <= 0:
        raise FleetExecutorStateError("lease_seconds must be positive.")
    run = _FLEET_RUNS.get(audit_id)
    if run is None:
        return None
    worker = _worker_for(
        audit_id, worker_id, legacy_fallback=not require_scoped_worker
    )
    if worker is None:
        raise FleetExecutorStateError("Worker must register before leasing jobs.")
    _mark_stale_worker_if_expired(worker)
    if worker.status != "active":
        raise FleetExecutorStateError("Worker heartbeat is not active; cannot lease jobs.")

    _expire_stale_leases(run)
    for job in run.jobs:
        if job.assigned_worker_id == worker_id and job.status in {"queued", "expired"}:
            _assert_worker_can_run_job(worker, job)
            now = datetime.now(UTC)
            job.status = "leased"
            job.lease_token = _lease_token_for(job, now)
            job.lease_token_hash = _hash_token(job.lease_token)
            job.lease_expires_at = (now + timedelta(seconds=lease_seconds)).isoformat()
            job.updated_at = now.isoformat()
            run.status = "LEASING"
            run.updated_at = job.updated_at
            _refresh_run_gate(run)
            _mirror_run(run)
            return job
    return None


def submit_job_receipt(
    *,
    audit_id: str,
    job_id: str,
    worker_id: str,
    lease_token: str,
    produced_outputs: list[str],
    evidence_packet_fragment_ref: str | None = None,
    evidence_packet_fragment_payload: dict[str, Any] | None = None,
    missing_outputs: list[str] | None = None,
    error_message: str | None = None,
    job_status: Literal["completed", "failed"] = "completed",
    require_scoped_worker: bool = False,
) -> FleetRunRecord | None:
    run = _FLEET_RUNS.get(audit_id)
    if run is None:
        return None
    job = _job(run, job_id)
    if job is None:
        raise KeyError(job_id)
    if job.assigned_worker_id != worker_id:
        raise FleetExecutorStateError("Worker cannot submit a receipt for another worker's job.")
    worker = _worker_for(
        audit_id, worker_id, legacy_fallback=not require_scoped_worker
    )
    if worker is None:
        raise FleetExecutorStateError("Worker must register before submitting job receipts.")
    _mark_stale_worker_if_expired(worker)
    if worker.status != "active":
        raise FleetExecutorStateError("Worker heartbeat is not active; cannot submit job receipts.")
    if job.status != "leased":
        raise FleetExecutorStateError("Job receipt requires an active lease.")
    if job.lease_token != lease_token:
        raise FleetExecutorStateError("Job receipt lease_token does not match the active lease.")
    if job.lease_token_hash != _hash_token(lease_token):
        raise FleetExecutorStateError("Job receipt lease_token does not match the active lease.")
    if job_status == "completed" and not (evidence_packet_fragment_ref or "").strip():
        raise FleetExecutorStateError("Completed job receipts require evidence_packet_fragment_ref.")
    if job_status == "failed" and not (error_message or "").strip():
        raise FleetExecutorStateError("Failed job receipts require error_message.")

    produced = tuple(_dedupe_nonempty(produced_outputs))
    explicit_missing = set(_dedupe_nonempty(missing_outputs or []))
    expected_missing = set(job.expected_outputs) - set(produced)
    missing = tuple(sorted(explicit_missing | expected_missing))
    overlap = set(produced).intersection(missing)
    if overlap:
        raise FleetExecutorStateError(f"Produced and missing outputs overlap: {', '.join(sorted(overlap))}.")
    fragment_ref = (evidence_packet_fragment_ref or "").strip()
    if job_status == "completed":
        _validate_fragment_ref(
            run=run,
            job=job,
            worker=worker,
            produced_outputs=produced,
            missing_outputs=missing,
            evidence_packet_fragment_payload=evidence_packet_fragment_payload,
            fragment_ref=fragment_ref,
        )

    now = _utc_now()
    job.produced_outputs = produced
    job.missing_outputs = missing
    job.evidence_packet_fragment_ref = fragment_ref if fragment_ref else None
    job.evidence_packet_fragment_payload = evidence_packet_fragment_payload if fragment_ref else None
    job.error_message = error_message.strip() if error_message else None
    job.status = "failed" if job_status == "failed" else "completed"
    job.lease_token = None
    job.lease_token_hash = None
    job.updated_at = now
    if job.evidence_packet_fragment_ref:
        _FRAGMENT_REFS.add(job.evidence_packet_fragment_ref)
        _mirror_fragment(job.evidence_packet_fragment_ref, audit_id=audit_id, job_id=job.job_id)

    record_worker_evidence(
        audit_id,
        worker_id,
        produced_outputs=list(produced),
        missing_outputs=list(missing),
        evidence_packet_ref=job.evidence_packet_fragment_ref,
        error_message=job.error_message,
        worker_status="failed" if job.status == "failed" else "completed",
    )
    run.status = "MERGE_PENDING"
    run.updated_at = now
    _refresh_run_gate(run)
    return _mirror_run(run)


def merge_fleet_evidence(audit_id: str) -> FleetRunRecord | None:
    run = _FLEET_RUNS.get(audit_id)
    if run is None:
        return None
    _refresh_run_gate(run)
    if run.verifier_gate_status in {"waiting_for_workers", "waiting_for_receipts"}:
        raise FleetExecutorStateError("Fleet evidence cannot merge until every assigned job returns a receipt.")
    if run.verifier_gate_status in {"blocked_failed_worker", "blocked_missing_outputs"}:
        distributed = merge_distributed_audit(audit_id)
        run.status = "FAILED" if run.verifier_gate_status == "blocked_failed_worker" else "COMPLETE"
        run.merged_packet_trace_id = distributed.evidence_packet_trace_id if distributed else None
        if distributed is not None and run.merged_packet_trace_id:
            from api.services.cas_harness_merged_evidence_packets import (
                write_merged_fleet_evidence_packet,
            )

            write_merged_fleet_evidence_packet(run=run, distributed=distributed)
        run.updated_at = _utc_now()
        return _mirror_run(run)

    distributed = merge_distributed_audit(audit_id)
    run.status = "COMPLETE"
    run.merged_packet_trace_id = distributed.evidence_packet_trace_id if distributed else None
    if distributed is not None and run.merged_packet_trace_id:
        from api.services.cas_harness_merged_evidence_packets import (
            write_merged_fleet_evidence_packet,
        )

        write_merged_fleet_evidence_packet(run=run, distributed=distributed)
    run.merge_reason = (
        "All fleet job fragments are present. Merged Evidence Packet is ready for "
        "the verifier decision layer; fleet executor does not fabricate ACCEPT."
    )
    run.updated_at = _utc_now()
    return _mirror_run(run)


def _refresh_run_gate(run: FleetRunRecord) -> None:
    unregistered_jobs = [
        job
        for job in run.jobs
        if not _job_has_ready_worker(
            job, require_scoped=run.require_scoped_workers
        )
    ]
    failed_jobs = [job for job in run.jobs if job.status == "failed"]
    incomplete_jobs = [job for job in run.jobs if job.status not in {"completed", "failed"}]
    missing_jobs = [job for job in run.jobs if job.missing_outputs]
    stale = _stale_assigned_workers(run)

    if unregistered_jobs or stale:
        run.verifier_gate_status = "waiting_for_workers"
        run.merge_reason = "Waiting for registered, active Probe Workers for every assigned job."
    elif failed_jobs:
        run.verifier_gate_status = "blocked_failed_worker"
        run.merge_reason = "At least one fleet job failed; cannot ACCEPT without rerun or human review."
    elif incomplete_jobs:
        run.verifier_gate_status = "waiting_for_receipts"
        run.merge_reason = "Waiting for worker Evidence Packet fragment receipts."
    elif missing_jobs:
        run.verifier_gate_status = "blocked_missing_outputs"
        run.merge_reason = "At least one worker receipt is missing required outputs; cannot ACCEPT."
    else:
        run.verifier_gate_status = "ready_for_verifier"
        run.merge_reason = (
            "All worker receipts are present; merge can assemble the distributed "
            "Evidence Packet for verifier review."
        )


def _readiness_payload(
    *,
    run: FleetRunRecord,
    stale_workers: list[str],
    completed_jobs: list[FleetJobRecord],
    failed_jobs: list[FleetJobRecord],
    leased_jobs: list[FleetJobRecord],
) -> dict[str, object]:
    total_jobs = len(run.jobs)
    ready_workers = sum(
        1
        for job in run.jobs
        if _job_has_ready_worker(job, require_scoped=run.require_scoped_workers)
    )
    missing_ready_workers = max(total_jobs - ready_workers, 0)
    incomplete_jobs = [job for job in run.jobs if job.status not in {"completed", "failed"}]
    missing_output_jobs = [job for job in run.jobs if job.missing_outputs]

    blockers: list[str] = []
    next_actions: list[str] = []
    status: FleetReadinessStatus = "waiting"

    if total_jobs == 0:
        status = "blocked"
        blockers.append("No fleet jobs exist for this distributed audit.")
        next_actions.append("Dispatch the distributed audit, then prepare fleet jobs.")
    elif missing_ready_workers or stale_workers:
        status = "waiting"
        if missing_ready_workers:
            blockers.append(
                f"{missing_ready_workers} assigned worker job(s) still need a registered, compatible, fresh-heartbeat worker."
            )
        if stale_workers:
            blockers.append(f"{len(stale_workers)} assigned worker(s) have stale heartbeats.")
        next_actions.append("Register or heartbeat every assigned Probe Worker.")
        next_actions.append("Verify each worker model_id and supported methods match its assigned job.")
    elif failed_jobs:
        status = "blocked"
        blockers.append(f"{len(failed_jobs)} worker job(s) failed.")
        next_actions.append("Rerun failed jobs or route the merged packet to human review.")
    elif incomplete_jobs:
        status = "waiting"
        receipt_gap = total_jobs - len(completed_jobs) - len(failed_jobs)
        blockers.append(f"{receipt_gap} Evidence Packet fragment receipt(s) are still missing.")
        if leased_jobs:
            next_actions.append("Submit signed fragment receipts for the currently leased jobs.")
        else:
            next_actions.append("Lease queued jobs to their registered workers.")
        next_actions.append("Each receipt must include the canonical content-addressed fragment ref.")
    elif missing_output_jobs:
        status = "blocked"
        blockers.append(f"{len(missing_output_jobs)} completed receipt(s) are missing required outputs.")
        next_actions.append("Rerun incomplete jobs with all expected outputs or route to human review.")
    elif run.merged_packet_trace_id:
        status = "ready"
        next_actions.append("Run the verifier decision layer over the merged Evidence Packet.")
    else:
        status = "ready"
        next_actions.append("Merge fleet evidence into one distributed Evidence Packet.")
        next_actions.append("Then run the verifier decision layer; fleet merge alone cannot ACCEPT.")

    if not blockers and status == "ready":
        headline = "Large-model worker receipts are complete; verifier review is unblocked."
    elif status == "blocked":
        headline = "Large-model eval is blocked; the run cannot support ACCEPT."
    else:
        headline = "Large-model eval is waiting on workers or fragment receipts."

    return {
        "status": status,
        "headline": headline,
        "blockers": blockers,
        "next_actions": next_actions,
        "verifier_owned": True,
    }


def _assert_worker_can_run_job(worker: FleetWorkerRecord, job: FleetJobRecord) -> None:
    audit = get_distributed_audit(job.audit_id)
    if audit is None:
        raise FleetExecutorStateError("Distributed audit session not found for fleet job.")
    if worker.model_id != audit.plan.model_id:
        raise FleetExecutorStateError("Worker model_id does not match the distributed audit model.")
    unsupported = set(job.assigned_methods) - set(worker.supported_methods)
    if unsupported:
        raise FleetExecutorStateError(
            f"Worker {worker.worker_id} does not support assigned methods: {', '.join(sorted(unsupported))}."
        )


def _expire_stale_leases(run: FleetRunRecord) -> None:
    now = datetime.now(UTC)
    changed = False
    for job in run.jobs:
        if job.status == "leased" and job.lease_expires_at and _parse_utc(job.lease_expires_at) < now:
            job.status = "expired"
            job.lease_token = None
            job.lease_token_hash = None
            job.updated_at = now.isoformat()
            changed = True
    if changed:
        # Clock-triggered job-state change outside the run's own mutators: re-mirror so
        # the shadow ledger does not go stale against the dict.
        _mirror_run(run)


def _expire_worker_leases(worker_id: str, *, audit_id: str | None = None) -> None:
    now = _utc_now()
    for run in _FLEET_RUNS.values():
        if audit_id is not None and run.audit_id != audit_id:
            continue
        changed = False
        for job in run.jobs:
            if job.assigned_worker_id == worker_id and job.status == "leased":
                job.status = "expired"
                job.lease_token = None
                job.lease_token_hash = None
                job.updated_at = now
                changed = True
        if changed:
            run.updated_at = now
            # Heartbeat/staleness can expire leases across any run; re-mirror each one.
            _mirror_run(run)


def _stale_assigned_workers(run: FleetRunRecord) -> list[str]:
    stale: set[str] = set()
    for job in run.jobs:
        worker = _worker_for(
            run.audit_id,
            job.assigned_worker_id,
            legacy_fallback=not run.require_scoped_workers,
        )
        if worker is not None:
            _mark_stale_worker_if_expired(worker)
            if worker.status != "active":
                stale.add(worker.worker_id)
    return sorted(stale)


def _mark_stale_worker_if_expired(
    worker: FleetWorkerRecord,
    *,
    max_heartbeat_age_seconds: int = DEFAULT_MAX_HEARTBEAT_AGE_SECONDS,
) -> bool:
    cutoff = datetime.now(UTC) - timedelta(seconds=max_heartbeat_age_seconds)
    if _parse_utc(worker.last_heartbeat_at) < cutoff:
        was_active = worker.status == "active"
        worker.status = "stale"
        if was_active:
            _expire_worker_leases(worker.worker_id, audit_id=worker.audit_id)
        return True
    return worker.status == "stale"


def _job_has_ready_worker(
    job: FleetJobRecord, *, require_scoped: bool = False
) -> bool:
    worker = _worker_for(
        job.audit_id,
        job.assigned_worker_id,
        legacy_fallback=not require_scoped,
    )
    if worker is None or worker.status != "active":
        return False
    try:
        _assert_worker_can_run_job(worker, job)
    except FleetExecutorStateError:
        return False
    return True


def _job(run: FleetRunRecord, job_id: str) -> FleetJobRecord | None:
    for job in run.jobs:
        if job.job_id == job_id:
            return job
    return None


def _worker_key(worker_id: str, audit_id: str | None) -> str:
    """Internal key; legacy workers retain their historical unscoped key."""
    return worker_id if audit_id is None else f"{audit_id}\x1f{worker_id}"


def _worker_for(
    audit_id: str | None,
    worker_id: str,
    *,
    legacy_fallback: bool = True,
) -> FleetWorkerRecord | None:
    if audit_id is not None:
        scoped = _WORKERS.get(_worker_key(worker_id, audit_id))
        if scoped is not None:
            return scoped
    return _WORKERS.get(worker_id) if legacy_fallback else None


def _job_id_for(audit_id: str, worker_id: str, shard_id: str) -> str:
    digest = hashlib.sha256(f"{audit_id}:{worker_id}:{shard_id}".encode("utf-8")).hexdigest()
    return f"fleet-job-{digest[:16]}"


def _lease_token_for(job: FleetJobRecord, leased_at: datetime) -> str:
    payload = {
        "audit_id": job.audit_id,
        "job_id": job.job_id,
        "worker_id": job.assigned_worker_id,
        "leased_at": leased_at.isoformat(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _hash_token(token: str | None) -> str | None:
    if token is None:
        return None
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_evidence_fragment_ref(
    *,
    audit_id: str,
    job_id: str,
    worker_id: str,
    model_id: str,
    layer_start: int,
    layer_end: int,
    shard_id: str,
    expected_outputs: list[str] | tuple[str, ...],
    produced_outputs: list[str] | tuple[str, ...],
    missing_outputs: list[str] | tuple[str, ...] = (),
    evidence_packet_fragment_payload: Mapping[str, Any] | None = None,
) -> str:
    payload = _canonical_fragment_payload(
        audit_id=audit_id,
        job_id=job_id,
        worker_id=worker_id,
        model_id=model_id,
        layer_start=layer_start,
        layer_end=layer_end,
        shard_id=shard_id,
        expected_outputs=tuple(expected_outputs),
        produced_outputs=tuple(produced_outputs),
        missing_outputs=tuple(missing_outputs),
        evidence_packet_fragment_payload=evidence_packet_fragment_payload,
    )
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"cas-fragment://{audit_id}/{job_id}/{worker_id}/{shard_id}/sha256:{digest}"


def _validate_fragment_ref(
    *,
    run: FleetRunRecord,
    job: FleetJobRecord,
    worker: FleetWorkerRecord,
    produced_outputs: tuple[str, ...],
    missing_outputs: tuple[str, ...],
    evidence_packet_fragment_payload: dict[str, Any] | None,
    fragment_ref: str,
) -> None:
    expected = build_evidence_fragment_ref(
        audit_id=run.audit_id,
        job_id=job.job_id,
        worker_id=worker.worker_id,
        model_id=worker.model_id,
        layer_start=job.layer_start,
        layer_end=job.layer_end,
        shard_id=job.shard_id,
        expected_outputs=job.expected_outputs,
        produced_outputs=produced_outputs,
        missing_outputs=missing_outputs,
        evidence_packet_fragment_payload=evidence_packet_fragment_payload,
    )
    if fragment_ref != expected:
        raise FleetExecutorStateError(
            "Evidence Packet fragment ref failed hash/assignment validation for this audit job."
        )
    if fragment_ref in _FRAGMENT_REFS:
        raise FleetExecutorStateError("Evidence Packet fragment ref was already submitted.")


def _canonical_fragment_payload(
    *,
    audit_id: str,
    job_id: str,
    worker_id: str,
    model_id: str,
    layer_start: int,
    layer_end: int,
    shard_id: str,
    expected_outputs: tuple[str, ...],
    produced_outputs: tuple[str, ...],
    missing_outputs: tuple[str, ...],
    evidence_packet_fragment_payload: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "cas_harness_evidence_fragment.v1",
        "audit_id": audit_id,
        "job_id": job_id,
        "worker_id": worker_id,
        "model_id": model_id,
        "layer_start": layer_start,
        "layer_end": layer_end,
        "shard_id": shard_id,
        "expected_outputs": list(expected_outputs),
        "produced_outputs": list(produced_outputs),
        "missing_outputs": list(missing_outputs),
    }
    payload_sha = _fragment_payload_sha256(evidence_packet_fragment_payload)
    if payload_sha is not None:
        payload["fragment_payload_sha256"] = payload_sha
    return payload


def _fragment_payload_sha256(payload: Mapping[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _dedupe_nonempty(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip() if isinstance(value, str) else ""
        if stripped and stripped not in seen:
            cleaned.append(stripped)
            seen.add(stripped)
    return cleaned


def _require_nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise FleetExecutorStateError(f"{field_name} is required.")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
