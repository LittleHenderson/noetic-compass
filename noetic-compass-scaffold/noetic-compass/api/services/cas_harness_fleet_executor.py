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
import hmac
import json
import re
import secrets
from typing import Any, Mapping, Literal

from api.services.cas_harness_distributed_audits import (
    DistributedAuditStateError,
    get_distributed_audit,
    merge_distributed_audit,
    record_worker_evidence,
)
from api.services.cas_harness_v2_worker_bridge import (
    FleetJobSnapshot,
    ResearchWorkerBridgeBindingError,
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
    "blocked_unattested_model",
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
    model_id: str | None = None
    model_revision: str | None = None
    model_artifact_manifest_path: str | None = None
    model_artifact_manifest_sha256: str | None = None
    execution_mode: str | None = None
    # Runtime proof that the raw attestation was validated in this process. The
    # run ledger stores only the fragment ref, not the payload, so completed jobs
    # rehydrated without WORM payload retrieval must be quarantined.
    model_attestation_replayable: bool = False
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
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "model_artifact_manifest_path": self.model_artifact_manifest_path,
            "model_artifact_manifest_sha256": self.model_artifact_manifest_sha256,
            "execution_mode": self.execution_mode,
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


@dataclass(frozen=True, slots=True)
class ActiveFleetJobLease:
    """Redacted process-local lease observation for the dark v2 lifecycle.

    This carrier never exposes the lease token and does not promote the legacy
    in-process fleet dictionaries into a durable or multi-replica authority.
    """

    snapshot: FleetJobSnapshot
    lease_generation_id: str
    lease_token_sha256: str
    lease_expires_at: str
    state_authority: str = "PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE"
    trusted_time: str = "NOT_ESTABLISHED"


@dataclass(frozen=True, slots=True)
class HarnessV2ConfiguredFleetInventory:
    """Redacted process-local configuration inventory for later reconciliation.

    ``tenant_id`` must come from the authenticated service boundary. The legacy
    fleet executor does not retain tenant ownership, so this carrier deliberately
    records that limitation instead of pretending the in-process dictionaries are
    a tenant or durable authority. ``jobs`` contains no lease capability, receipt
    payload, output body, or worker error text.
    """

    tenant_id: str
    audit_id: str
    fleet_id: str
    jobs: tuple[FleetJobSnapshot, ...]
    state_authority: str = "PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE"
    tenant_scope_authority: str = (
        "AUTHENTICATED_SCOPE_REQUIRED_NOT_RETAINED_BY_FLEET_EXECUTOR"
    )

    def __post_init__(self) -> None:
        tenant = _harness_v2_scope_text(self.tenant_id, "inventory tenant_id")
        audit = _harness_v2_scope_text(self.audit_id, "inventory audit_id")
        fleet = _harness_v2_scope_text(self.fleet_id, "inventory fleet_id")
        if audit != fleet:
            raise FleetExecutorStateError(
                "Harness-v2 inventory fleet_id must exactly equal audit_id."
            )
        if type(self.jobs) is not tuple or not self.jobs:
            raise FleetExecutorStateError(
                "Harness-v2 inventory requires a non-empty exact snapshot tuple."
            )
        if any(type(job) is not FleetJobSnapshot for job in self.jobs):
            raise FleetExecutorStateError(
                "Harness-v2 inventory contains a non-snapshot job."
            )
        job_ids = tuple(job.job_id for job in self.jobs)
        if len(set(job_ids)) != len(job_ids):
            raise FleetExecutorStateError(
                "Harness-v2 inventory contains duplicate job identities."
            )
        if any(job.audit_id != audit or job.fleet_id != fleet for job in self.jobs):
            raise FleetExecutorStateError(
                "Harness-v2 inventory contains a cross-scope job."
            )
        if (
            tenant != self.tenant_id
            or self.state_authority != "PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE"
            or self.tenant_scope_authority
            != "AUTHENTICATED_SCOPE_REQUIRED_NOT_RETAINED_BY_FLEET_EXECUTOR"
        ):
            raise FleetExecutorStateError(
                "Harness-v2 inventory authority limitations drifted."
            )

    @property
    def job_ids(self) -> tuple[str, ...]:
        return tuple(job.job_id for job in self.jobs)


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
        "model_id": job.model_id,
        "model_revision": job.model_revision,
        "model_artifact_manifest_path": job.model_artifact_manifest_path,
        "model_artifact_manifest_sha256": job.model_artifact_manifest_sha256,
        "execution_mode": job.execution_mode,
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
        model_id=payload.get("model_id"),
        model_revision=payload.get("model_revision"),
        model_artifact_manifest_path=payload.get("model_artifact_manifest_path"),
        model_artifact_manifest_sha256=payload.get("model_artifact_manifest_sha256"),
        execution_mode=payload.get("execution_mode"),
        model_attestation_replayable=stored_status != "completed",
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


def mark_stale_workers(
    *,
    max_heartbeat_age_seconds: int = DEFAULT_MAX_HEARTBEAT_AGE_SECONDS,
    worker_scopes: set[tuple[str | None, str]] | None = None,
) -> list[FleetWorkerRecord]:
    """Mark expired workers, optionally within an exact audit/worker scope set.

    ``None`` preserves the legacy global scan. Account-mode callers must pass the
    tenant-derived scopes so marking a worker stale cannot expire another tenant's
    leases before the route filters its response.
    """
    if max_heartbeat_age_seconds <= 0:
        raise FleetExecutorStateError("max_heartbeat_age_seconds must be positive.")
    stale: list[FleetWorkerRecord] = []
    for worker in _WORKERS.values():
        if (
            worker_scopes is not None
            and (worker.audit_id, worker.worker_id) not in worker_scopes
        ):
            continue
        if _mark_stale_worker_if_expired(
            worker,
            max_heartbeat_age_seconds=max_heartbeat_age_seconds,
        ):
            stale.append(worker)
    return stale


def prepare_fleet_for_audit(
    audit_id: str,
    *,
    model_revision: str | None = None,
    model_artifact_manifest_path: str | None = None,
    model_artifact_manifest_sha256: str | None = None,
    require_scoped_workers: bool = False,
) -> FleetRunRecord | None:
    audit = get_distributed_audit(audit_id)
    if audit is None:
        return None
    if audit.status == "PLANNED":
        raise FleetExecutorStateError("Dispatch the distributed audit before preparing fleet jobs.")

    model_revision, model_artifact_manifest_path, model_artifact_manifest_sha256 = (
        _validate_optional_model_identity_binding(
            model_revision=model_revision,
            model_artifact_manifest_path=model_artifact_manifest_path,
            model_artifact_manifest_sha256=model_artifact_manifest_sha256,
        )
    )
    if model_revision is not None:
        provenance_payload = (
            audit.provenance.to_dict() if audit.provenance is not None else None
        )
        provenance_revision = (
            provenance_payload.get("revision")
            if isinstance(provenance_payload, Mapping)
            else None
        )
        if (
            not isinstance(provenance_revision, str)
            or re.fullmatch(r"[0-9a-f]{40}", provenance_revision) is None
        ):
            raise FleetExecutorStateError(
                "Real-model fleet preparation requires an audit provenance manifest "
                "with a full 40-character lowercase commit revision."
            )
        if provenance_revision != model_revision:
            raise FleetExecutorStateError(
                "Fleet model_revision does not match the distributed audit provenance revision."
            )

    existing = _FLEET_RUNS.get(audit_id)
    if existing is not None:
        requested_identity = (
            model_revision,
            model_artifact_manifest_path,
            model_artifact_manifest_sha256,
        )
        existing_identities = {
            (
                job.model_revision,
                job.model_artifact_manifest_path,
                job.model_artifact_manifest_sha256,
            )
            for job in existing.jobs
        }
        if existing_identities != {requested_identity}:
            raise FleetExecutorStateError(
                "Fleet run already exists with a different model artifact identity binding."
            )
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
            model_id=audit.plan.model_id,
            model_revision=model_revision,
            model_artifact_manifest_path=model_artifact_manifest_path,
            model_artifact_manifest_sha256=model_artifact_manifest_sha256,
            execution_mode=(
                "external_probe_command"
                if model_revision is not None
                else "dry_run_control_plane"
            ),
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


def enumerate_harness_v2_configured_fleet(
    *,
    tenant_id: str,
    audit_id: str,
    fleet_id: str,
) -> HarnessV2ConfiguredFleetInventory:
    """Return the exact configured job mappings without any runtime secrets.

    This reads only the current process-local fleet dictionaries. The caller must
    already have authenticated ``tenant_id`` and established that the tenant owns
    ``audit_id``; tenant ownership is not stored by this legacy executor.
    """

    inventory, _ = _harness_v2_configured_fleet(
        tenant_id=tenant_id,
        audit_id=audit_id,
        fleet_id=fleet_id,
    )
    return inventory


def load_harness_v2_fleet_job_snapshot_for_issuance(
    *,
    tenant_id: str,
    audit_id: str,
    fleet_id: str,
    job_id: str,
) -> FleetJobSnapshot:
    """Load one server-derived preterminal job mapping without a lease secret.

    The returned snapshot can bind prospective Harness-v2 authorization issuance.
    It does not prove tenant ownership, execution, active lease possession, durable
    state, trusted time, or scientific validity. Active execution must separately
    pass :func:`validate_active_fleet_job_lease`.
    """

    requested_job_id = _harness_v2_scope_text(job_id, "job_id")
    inventory, run = _harness_v2_configured_fleet(
        tenant_id=tenant_id,
        audit_id=audit_id,
        fleet_id=fleet_id,
    )
    matches = tuple(job for job in run.jobs if job.job_id == requested_job_id)
    if len(matches) != 1:
        raise FleetExecutorStateError(
            "Harness-v2 fleet job must be configured exactly once for issuance."
        )
    job = matches[0]
    if run.status in {"COMPLETE", "FAILED"} or job.status not in {
        "queued",
        "leased",
        "expired",
    }:
        raise FleetExecutorStateError(
            "Harness-v2 authorization issuance requires a preterminal fleet job."
        )
    snapshots = tuple(
        snapshot for snapshot in inventory.jobs if snapshot.job_id == requested_job_id
    )
    if len(snapshots) != 1:
        raise FleetExecutorStateError(
            "Harness-v2 redacted fleet inventory lost the requested job identity."
        )
    return snapshots[0]


def load_harness_v2_fleet_job_snapshot_current(
    *,
    tenant_id: str,
    audit_id: str,
    fleet_id: str,
    job_id: str,
) -> FleetJobSnapshot:
    """Load one exact current configured mapping, including terminal state.

    This seam exists for replay and reconciliation after the legacy Fleet run
    has advanced beyond issuance.  It preserves the same authenticated-scope,
    unique-job, redaction, and process-local-authority limits as the issuance
    loader, but deliberately does not require a preterminal status.  It is not
    permission to issue a new authorization or proof of execution.
    """

    requested_job_id = _harness_v2_scope_text(job_id, "job_id")
    inventory, run = _harness_v2_configured_fleet(
        tenant_id=tenant_id,
        audit_id=audit_id,
        fleet_id=fleet_id,
    )
    matches = tuple(job for job in run.jobs if job.job_id == requested_job_id)
    if len(matches) != 1:
        raise FleetExecutorStateError(
            "Harness-v2 fleet job must be configured exactly once for replay."
        )
    snapshots = tuple(
        snapshot for snapshot in inventory.jobs if snapshot.job_id == requested_job_id
    )
    if len(snapshots) != 1:
        raise FleetExecutorStateError(
            "Harness-v2 redacted fleet inventory lost the requested job identity."
        )
    return snapshots[0]


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


def validate_active_fleet_job_lease(
    *,
    audit_id: str,
    job_id: str,
    worker_id: str,
    lease_token: str,
    require_scoped_worker: bool = True,
    now: datetime | None = None,
) -> ActiveFleetJobLease:
    """Fail closed unless the exact current process-local lease is executable.

    The returned digest/generation can be bound into the prospective lifecycle,
    but this read-only seam cannot establish restart or host-loss durability.
    """

    _require_nonempty(audit_id, "audit_id")
    _require_nonempty(job_id, "job_id")
    _require_nonempty(worker_id, "worker_id")
    _require_nonempty(lease_token, "lease_token")
    audit = audit_id.strip()
    job_key = job_id.strip()
    worker_key = worker_id.strip()
    secret = lease_token.strip()
    run = _FLEET_RUNS.get(audit)
    if run is None:
        raise FleetExecutorStateError("Fleet run is unavailable for active-lease validation.")
    job = _job(run, job_key)
    if job is None:
        raise FleetExecutorStateError("Fleet job is unavailable for active-lease validation.")
    if job.assigned_worker_id != worker_key:
        raise FleetExecutorStateError("Active fleet lease belongs to another worker.")
    worker = _worker_for(
        audit,
        worker_key,
        legacy_fallback=not require_scoped_worker,
    )
    if worker is None:
        raise FleetExecutorStateError("Active fleet lease worker is unavailable.")
    stamp = now or datetime.now(UTC)
    if job.status != "leased":
        raise FleetExecutorStateError("Fleet job does not have an active lease.")
    supplied_hash = _hash_token(secret)
    if (
        job.lease_token is None
        or job.lease_token_hash is None
        or not hmac.compare_digest(job.lease_token, secret)
        or not hmac.compare_digest(job.lease_token_hash, supplied_hash)
    ):
        raise FleetExecutorStateError("Fleet job lease token does not match the active lease.")
    if not job.lease_expires_at:
        raise FleetExecutorStateError("Fleet job lease expiry is unavailable.")
    try:
        expiry = _parse_utc(job.lease_expires_at)
    except (TypeError, ValueError) as exc:
        raise FleetExecutorStateError("Fleet job lease expiry is invalid.") from exc
    if stamp >= expiry:
        raise FleetExecutorStateError("Fleet job lease has expired.")
    heartbeat_cutoff = stamp - timedelta(seconds=DEFAULT_MAX_HEARTBEAT_AGE_SECONDS)
    if worker.status != "active" or _parse_utc(worker.last_heartbeat_at) < heartbeat_cutoff:
        raise FleetExecutorStateError("Active fleet lease worker heartbeat is not current.")
    model_fields = {
        "model_id": job.model_id,
        "model_revision": job.model_revision,
        "model_artifact_manifest_path": job.model_artifact_manifest_path,
        "model_artifact_manifest_sha256": job.model_artifact_manifest_sha256,
        "execution_mode": job.execution_mode,
    }
    if any(not isinstance(value, str) or not value.strip() for value in model_fields.values()):
        raise FleetExecutorStateError(
            "Active fleet lease lacks the exact model artifact identity required by v2."
        )
    snapshot = FleetJobSnapshot(
        fleet_id=audit,
        job_id=job.job_id,
        audit_id=audit,
        assigned_worker_id=job.assigned_worker_id,
        layer_start=job.layer_start,
        layer_end=job.layer_end,
        shard_id=job.shard_id,
        assigned_methods=job.assigned_methods,
        expected_outputs=job.expected_outputs,
        model_id=str(job.model_id),
        model_revision=str(job.model_revision),
        model_artifact_manifest_path=str(job.model_artifact_manifest_path),
        model_artifact_manifest_sha256=str(job.model_artifact_manifest_sha256),
        execution_mode=str(job.execution_mode),
    )
    lease_generation_id = "flg_" + hashlib.sha256(
        (
            f"{audit}:{job.job_id}:{job.assigned_worker_id}:"
            f"{job.lease_token_hash}:{job.lease_expires_at}:{job.updated_at}"
        ).encode("utf-8")
    ).hexdigest()
    return ActiveFleetJobLease(
        snapshot=snapshot,
        lease_generation_id=lease_generation_id,
        lease_token_sha256=supplied_hash,
        lease_expires_at=job.lease_expires_at,
    )


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
    execution_mode: str | None = None,
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
    if execution_mode not in {None, "dry_run_control_plane", "external_probe_command"}:
        raise FleetExecutorStateError("Unsupported fleet job execution_mode.")

    produced = tuple(_dedupe_nonempty(produced_outputs))
    explicit_missing = set(_dedupe_nonempty(missing_outputs or []))
    expected_missing = set(job.expected_outputs) - set(produced)
    missing = tuple(sorted(explicit_missing | expected_missing))
    overlap = set(produced).intersection(missing)
    if overlap:
        raise FleetExecutorStateError(f"Produced and missing outputs overlap: {', '.join(sorted(overlap))}.")
    fragment_ref = (evidence_packet_fragment_ref or "").strip()
    if job_status == "completed":
        _validate_model_execution_attestation(
            job=job,
            worker=worker,
            evidence_packet_fragment_payload=evidence_packet_fragment_payload,
            execution_mode=execution_mode,
        )
        _validate_fragment_ref(
            run=run,
            job=job,
            worker=worker,
            produced_outputs=produced,
            missing_outputs=missing,
            evidence_packet_fragment_payload=evidence_packet_fragment_payload,
            execution_mode=execution_mode,
            fragment_ref=fragment_ref,
        )

    now = _utc_now()
    job.produced_outputs = produced
    job.missing_outputs = missing
    job.evidence_packet_fragment_ref = fragment_ref if fragment_ref else None
    job.evidence_packet_fragment_payload = evidence_packet_fragment_payload if fragment_ref else None
    job.model_attestation_replayable = bool(
        job_status == "completed"
        and execution_mode == "external_probe_command"
        and evidence_packet_fragment_payload is not None
    )
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
    if run.verifier_gate_status == "blocked_unattested_model":
        raise FleetExecutorStateError(
            "Fleet evidence cannot merge from dry-run or legacy unattested model jobs."
        )
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


def _job_has_replayable_model_attestation(
    job: FleetJobRecord,
    *,
    require_scoped: bool,
) -> bool:
    """Replay the in-memory attestation before any verifier-ready view."""

    if (
        job.execution_mode != "external_probe_command"
        or not job.model_attestation_replayable
        or not isinstance(job.evidence_packet_fragment_payload, Mapping)
    ):
        return False
    worker = _worker_for(
        job.audit_id,
        job.assigned_worker_id,
        legacy_fallback=not require_scoped,
    )
    if worker is None:
        return False
    try:
        _validate_model_execution_attestation(
            job=job,
            worker=worker,
            evidence_packet_fragment_payload=job.evidence_packet_fragment_payload,
            execution_mode=job.execution_mode,
        )
    except FleetExecutorStateError:
        return False
    return True


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
    unattested_jobs = [
        job
        for job in run.jobs
        if job.status == "completed"
        and not _job_has_replayable_model_attestation(
            job,
            require_scoped=run.require_scoped_workers,
        )
    ]
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
    elif unattested_jobs:
        run.verifier_gate_status = "blocked_unattested_model"
        run.merge_reason = (
            "Dry-run or legacy completed receipts do not attest an exact model artifact "
            "identity and can never reach verifier ACCEPT."
        )
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
    unattested_jobs = [
        job
        for job in completed_jobs
        if not _job_has_replayable_model_attestation(
            job,
            require_scoped=run.require_scoped_workers,
        )
    ]

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
    elif unattested_jobs:
        status = "blocked"
        blockers.append(
            f"{len(unattested_jobs)} completed receipt(s) are dry-run or legacy model-unattested."
        )
        next_actions.append(
            "Prepare a new identity-bound fleet and run the external open-weight probe command."
        )
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


def _harness_v2_configured_fleet(
    *,
    tenant_id: str,
    audit_id: str,
    fleet_id: str,
) -> tuple[HarnessV2ConfiguredFleetInventory, FleetRunRecord]:
    tenant = _harness_v2_scope_text(tenant_id, "tenant_id")
    audit_key = _harness_v2_scope_text(audit_id, "audit_id")
    fleet_key = _harness_v2_scope_text(fleet_id, "fleet_id")
    if audit_key != fleet_key:
        raise FleetExecutorStateError(
            "Harness-v2 fleet_id must exactly equal the authenticated audit_id."
        )
    run = _FLEET_RUNS.get(audit_key)
    if run is None:
        raise FleetExecutorStateError(
            "Harness-v2 configured fleet is unavailable in process-local state."
        )
    if run.audit_id != audit_key:
        raise FleetExecutorStateError(
            "Harness-v2 configured fleet audit scope drifted from its process-local key."
        )
    if type(run.jobs) is not list or not run.jobs:
        raise FleetExecutorStateError(
            "Harness-v2 configured fleet has no job inventory."
        )

    audit = get_distributed_audit(audit_key)
    if audit is None or audit.audit_id != audit_key:
        raise FleetExecutorStateError(
            "Harness-v2 configured fleet lacks its distributed-audit source."
        )

    seen_job_ids: set[str] = set()
    snapshots: list[FleetJobSnapshot] = []
    for job in run.jobs:
        job_key = _harness_v2_scope_text(job.job_id, "configured job_id")
        if job_key in seen_job_ids:
            raise FleetExecutorStateError(
                "Harness-v2 configured fleet contains a duplicate job_id."
            )
        seen_job_ids.add(job_key)
        if job.audit_id != audit_key:
            raise FleetExecutorStateError(
                "Harness-v2 configured job crossed its audit/fleet scope."
            )
        if job.status not in {"queued", "leased", "completed", "failed", "expired"}:
            raise FleetExecutorStateError(
                "Harness-v2 configured job has an unknown lifecycle status."
            )
        snapshots.append(
            _harness_v2_snapshot_from_configured_job(
                fleet_id=fleet_key,
                audit=audit,
                job=job,
            )
        )

    identities = {
        (
            snapshot.model_id,
            snapshot.model_revision,
            snapshot.model_artifact_manifest_path,
            snapshot.model_artifact_manifest_sha256,
            snapshot.execution_mode,
        )
        for snapshot in snapshots
    }
    if len(identities) != 1:
        raise FleetExecutorStateError(
            "Harness-v2 configured jobs contain drifted model identity bindings."
        )
    model_id, revision, _manifest_path, _manifest_sha256, execution_mode = next(
        iter(identities)
    )
    if model_id != audit.plan.model_id:
        raise FleetExecutorStateError(
            "Harness-v2 configured model_id drifted from the distributed audit plan."
        )
    provenance = audit.provenance.to_dict() if audit.provenance is not None else None
    if (
        not isinstance(provenance, Mapping)
        or provenance.get("revision") != revision
    ):
        raise FleetExecutorStateError(
            "Harness-v2 configured model revision drifted from audit provenance."
        )
    if execution_mode != "external_probe_command":
        raise FleetExecutorStateError(
            "Harness-v2 configured fleet is not identity-bound to external probe execution."
        )

    inventory = HarnessV2ConfiguredFleetInventory(
        tenant_id=tenant,
        audit_id=audit_key,
        fleet_id=fleet_key,
        jobs=tuple(sorted(snapshots, key=lambda snapshot: snapshot.job_id)),
    )
    return inventory, run


def _harness_v2_snapshot_from_configured_job(
    *,
    fleet_id: str,
    audit: Any,
    job: FleetJobRecord,
) -> FleetJobSnapshot:
    model_id = _harness_v2_scope_text(job.model_id, "configured model_id")
    execution_mode = _harness_v2_scope_text(
        job.execution_mode, "configured execution_mode"
    )
    try:
        revision, manifest_path, manifest_sha256 = (
            _validate_optional_model_identity_binding(
                model_revision=job.model_revision,
                model_artifact_manifest_path=job.model_artifact_manifest_path,
                model_artifact_manifest_sha256=job.model_artifact_manifest_sha256,
            )
        )
    except FleetExecutorStateError as exc:
        raise FleetExecutorStateError(
            "Harness-v2 configured job has an invalid model identity binding."
        ) from exc
    if revision is None or manifest_path is None or manifest_sha256 is None:
        raise FleetExecutorStateError(
            "Harness-v2 configured job lacks its full model identity binding."
        )

    assignment_matches = [
        assignment
        for assignment in audit.worker_evidence
        if assignment.worker_id == job.assigned_worker_id
        and assignment.shard_id == job.shard_id
    ]
    if len(assignment_matches) != 1:
        raise FleetExecutorStateError(
            "Harness-v2 configured job is missing or duplicated in the audit assignment plan."
        )
    assignment = assignment_matches[0]
    expected_job_id = _job_id_for(
        job.audit_id,
        assignment.worker_id,
        assignment.shard_id,
    )
    if (
        job.job_id != expected_job_id
        or job.layer_start != assignment.layer_start
        or job.layer_end != assignment.layer_end
        or job.assigned_methods != assignment.assigned_methods
        or job.expected_outputs != assignment.expected_outputs
    ):
        raise FleetExecutorStateError(
            "Harness-v2 configured job drifted from its audit assignment plan."
        )

    try:
        return FleetJobSnapshot(
            fleet_id=fleet_id,
            job_id=job.job_id,
            audit_id=job.audit_id,
            assigned_worker_id=job.assigned_worker_id,
            layer_start=job.layer_start,
            layer_end=job.layer_end,
            shard_id=job.shard_id,
            assigned_methods=job.assigned_methods,
            expected_outputs=job.expected_outputs,
            model_id=model_id,
            model_revision=revision,
            model_artifact_manifest_path=manifest_path,
            model_artifact_manifest_sha256=manifest_sha256,
            execution_mode=execution_mode,
        )
    except ResearchWorkerBridgeBindingError as exc:
        raise FleetExecutorStateError(
            "Harness-v2 configured job cannot form a strict redacted snapshot."
        ) from exc


def _harness_v2_scope_text(value: object, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 256
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise FleetExecutorStateError(
            f"Harness-v2 {field_name} must be exact non-empty bounded text."
        )
    return value


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


def _lease_token_for(_job: FleetJobRecord, _leased_at: datetime) -> str:
    """Mint an opaque 256-bit lease capability from the OS CSPRNG.

    Audit, job, worker, and timestamp fields are observable and therefore must
    not be used to derive the bearer token.  They remain bound separately by
    the lease record and its token digest.
    """

    return secrets.token_hex(32)


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
    execution_mode: str | None = None,
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
        execution_mode=execution_mode,
    )
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"cas-fragment://{audit_id}/{job_id}/{worker_id}/{shard_id}/sha256:{digest}"


def _validate_model_execution_attestation(
    *,
    job: FleetJobRecord,
    worker: FleetWorkerRecord,
    evidence_packet_fragment_payload: Mapping[str, Any] | None,
    execution_mode: str | None,
) -> None:
    claims_real = _payload_claims_real_model(evidence_packet_fragment_payload)
    bound_identity = (
        job.model_revision,
        job.model_artifact_manifest_path,
        job.model_artifact_manifest_sha256,
    )
    identity_bound = all(value is not None for value in bound_identity)
    if any(value is None for value in bound_identity) and any(
        value is not None for value in bound_identity
    ):
        raise FleetExecutorStateError("Fleet job contains a partial model identity binding.")
    if not identity_bound:
        if job.execution_mode not in {None, "dry_run_control_plane"}:
            raise FleetExecutorStateError(
                "Unbound fleet job has an invalid control-plane execution binding."
            )
        if execution_mode not in {None, "dry_run_control_plane"} or claims_real:
            raise FleetExecutorStateError(
                "Real-model completion is forbidden for a fleet job without a bound model identity."
            )
        return
    if job.execution_mode != "external_probe_command":
        raise FleetExecutorStateError(
            "Identity-bound fleet job is not bound to external_probe_command execution."
        )
    if execution_mode != "external_probe_command":
        raise FleetExecutorStateError(
            "Identity-bound fleet jobs require execution_mode=external_probe_command."
        )
    if not claims_real or not isinstance(evidence_packet_fragment_payload, Mapping):
        raise FleetExecutorStateError(
            "External probe completion requires a real-model artifact attestation."
        )
    if job.model_id is None:
        raise FleetExecutorStateError("Identity-bound fleet job is missing model_id.")
    if worker.model_id != job.model_id:
        raise FleetExecutorStateError(
            "Receipt worker model_id does not match the identity-bound fleet job."
        )
    if evidence_packet_fragment_payload.get("status") != "real_model_forward_completed":
        raise FleetExecutorStateError(
            "External probe completion requires status=real_model_forward_completed."
        )
    if evidence_packet_fragment_payload.get("audit_id") != job.audit_id:
        raise FleetExecutorStateError("Real-model attestation audit_id does not match the fleet job.")
    if evidence_packet_fragment_payload.get("job_id") != job.job_id:
        raise FleetExecutorStateError("Real-model attestation job_id does not match the fleet job.")
    if evidence_packet_fragment_payload.get("worker_id") != worker.worker_id:
        raise FleetExecutorStateError("Real-model attestation worker_id does not match the fleet job.")
    if evidence_packet_fragment_payload.get("model_id") != job.model_id:
        raise FleetExecutorStateError("Real-model attestation model_id does not match the fleet job.")
    if evidence_packet_fragment_payload.get("model_revision") != job.model_revision:
        raise FleetExecutorStateError(
            "Real-model attestation revision does not match the fleet job binding."
        )
    if evidence_packet_fragment_payload.get("shard_id") != job.shard_id:
        raise FleetExecutorStateError("Real-model attestation shard_id does not match the fleet job.")
    if evidence_packet_fragment_payload.get("layer_start") != job.layer_start:
        raise FleetExecutorStateError("Real-model attestation layer_start does not match the fleet job.")
    if evidence_packet_fragment_payload.get("layer_end") != job.layer_end:
        raise FleetExecutorStateError("Real-model attestation layer_end does not match the fleet job.")

    model_info = evidence_packet_fragment_payload.get("model_info")
    artifact_identity = model_info.get("artifact_identity") if isinstance(model_info, Mapping) else None
    if not isinstance(artifact_identity, Mapping):
        raise FleetExecutorStateError(
            "Real-model completion requires model_info.artifact_identity."
        )
    if artifact_identity.get("manifest_path") != job.model_artifact_manifest_path:
        raise FleetExecutorStateError(
            "Real-model attestation manifest path does not match the fleet job binding."
        )
    if artifact_identity.get("manifest_sha256") != job.model_artifact_manifest_sha256:
        raise FleetExecutorStateError(
            "Real-model attestation manifest SHA-256 does not match the fleet job binding."
        )
    required_flags = {
        "all_artifacts_hash_verified": True,
        "post_load_reverified": True,
        "local_files_only": True,
        "trust_remote_code": False,
        "use_safetensors": True,
    }
    for field_name, expected in required_flags.items():
        if artifact_identity.get(field_name) is not expected:
            raise FleetExecutorStateError(
                f"Real-model artifact attestation requires {field_name}={expected!r}."
            )
    _validate_exact_artifact_evidence(artifact_identity)


def _payload_claims_real_model(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload, Mapping):
        return False
    status = payload.get("status")
    if isinstance(status, str) and (
        status.startswith("real_model_forward")
        or status.startswith("PROBE_PREDICTED_")
    ):
        return True
    model_info = payload.get("model_info")
    return isinstance(model_info, Mapping) and isinstance(
        model_info.get("artifact_identity"), Mapping
    )


def _validate_exact_artifact_evidence(artifact_identity: Mapping[str, Any]) -> None:
    artifacts = artifact_identity.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise FleetExecutorStateError(
            "Real-model artifact attestation requires a non-empty exact artifact list."
        )
    canonical: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping) or set(artifact) != {"path", "sha256", "byte_count"}:
            raise FleetExecutorStateError(
                f"Real-model artifact attestation entry {index} has invalid fields."
            )
        path = artifact.get("path")
        digest = artifact.get("sha256")
        byte_count = artifact.get("byte_count")
        if not isinstance(path, str) or not path or path in seen:
            raise FleetExecutorStateError("Real-model artifact paths must be unique non-empty strings.")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise FleetExecutorStateError("Real-model artifact SHA-256 is malformed.")
        if type(byte_count) is not int or byte_count < 1:
            raise FleetExecutorStateError("Real-model artifact byte_count is malformed.")
        seen.add(path)
        canonical.append({"path": path, "sha256": digest, "byte_count": byte_count})
    canonical.sort(key=lambda item: item["path"])
    if artifact_identity.get("artifact_count") != len(canonical):
        raise FleetExecutorStateError("Real-model artifact_count does not match the exact list.")
    artifact_set_sha256 = hashlib.sha256(
        json.dumps(
            canonical,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if artifact_identity.get("artifact_set_sha256") != artifact_set_sha256:
        raise FleetExecutorStateError("Real-model artifact_set_sha256 does not match the exact list.")


def _validate_fragment_ref(
    *,
    run: FleetRunRecord,
    job: FleetJobRecord,
    worker: FleetWorkerRecord,
    produced_outputs: tuple[str, ...],
    missing_outputs: tuple[str, ...],
    evidence_packet_fragment_payload: dict[str, Any] | None,
    execution_mode: str | None,
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
        execution_mode=execution_mode,
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
    execution_mode: str | None = None,
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
    if execution_mode is not None:
        payload["execution_mode"] = execution_mode
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


def _validate_optional_model_identity_binding(
    *,
    model_revision: str | None,
    model_artifact_manifest_path: str | None,
    model_artifact_manifest_sha256: str | None,
) -> tuple[str | None, str | None, str | None]:
    values = (
        model_revision,
        model_artifact_manifest_path,
        model_artifact_manifest_sha256,
    )
    if all(value is None for value in values):
        return None, None, None
    if any(value is None for value in values):
        raise FleetExecutorStateError(
            "Real-model fleet identity requires revision, artifact manifest path, and manifest SHA-256 together."
        )
    assert model_revision is not None
    assert model_artifact_manifest_path is not None
    assert model_artifact_manifest_sha256 is not None
    if re.fullmatch(r"[0-9a-f]{40}", model_revision) is None:
        raise FleetExecutorStateError(
            "Fleet model_revision must be a full 40-character lowercase commit SHA."
        )
    if (
        model_artifact_manifest_path != model_artifact_manifest_path.strip()
        or not model_artifact_manifest_path
        or len(model_artifact_manifest_path) > 2_048
    ):
        raise FleetExecutorStateError(
            "Fleet model_artifact_manifest_path must be a non-empty canonical worker path."
        )
    is_posix_absolute = model_artifact_manifest_path.startswith("/")
    is_windows_absolute = re.match(
        r"^[A-Za-z]:[\\/]",
        model_artifact_manifest_path,
    ) is not None
    if not (is_posix_absolute or is_windows_absolute):
        raise FleetExecutorStateError(
            "Fleet model_artifact_manifest_path must be absolute on the target worker."
        )
    if re.fullmatch(r"[0-9a-f]{64}", model_artifact_manifest_sha256) is None:
        raise FleetExecutorStateError(
            "Fleet model_artifact_manifest_sha256 must be 64 lowercase hexadecimal characters."
        )
    return (
        model_revision,
        model_artifact_manifest_path,
        model_artifact_manifest_sha256,
    )


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
