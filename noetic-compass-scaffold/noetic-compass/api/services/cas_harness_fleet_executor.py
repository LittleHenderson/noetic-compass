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
from typing import Literal

from api.services.cas_harness_distributed_audits import (
    DistributedAuditStateError,
    get_distributed_audit,
    merge_distributed_audit,
    record_worker_evidence,
)


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
    lease_expires_at: str | None = None
    evidence_packet_fragment_ref: str | None = None
    produced_outputs: tuple[str, ...] = ()
    missing_outputs: tuple[str, ...] = ()
    error_message: str | None = None
    updated_at: str = field(default_factory=lambda: _utc_now())

    def to_dict(self) -> dict[str, object]:
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
            "lease_token": self.lease_token,
            "lease_expires_at": self.lease_expires_at,
            "evidence_packet_fragment_ref": self.evidence_packet_fragment_ref,
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
            "registered_workers": sum(1 for job in self.jobs if job.assigned_worker_id in _WORKERS),
            "stale_workers": stale_workers,
            "jobs": [job.to_dict() for job in self.jobs],
        }


_WORKERS: dict[str, FleetWorkerRecord] = {}
_FLEET_RUNS: dict[str, FleetRunRecord] = {}


def reset_fleet_executor_for_tests() -> None:
    _WORKERS.clear()
    _FLEET_RUNS.clear()


def register_worker(
    *,
    worker_id: str,
    model_id: str,
    worker_url: str,
    gpu_type: str,
    supported_methods: list[str],
    capacity: int = 1,
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
    )
    _WORKERS[record.worker_id] = record
    return record


def heartbeat_worker(worker_id: str) -> FleetWorkerRecord | None:
    worker = _WORKERS.get(worker_id)
    if worker is None:
        return None
    worker.status = "active"
    worker.last_heartbeat_at = _utc_now()
    return worker


def list_workers() -> list[FleetWorkerRecord]:
    return list(_WORKERS.values())


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


def prepare_fleet_for_audit(audit_id: str) -> FleetRunRecord | None:
    audit = get_distributed_audit(audit_id)
    if audit is None:
        return None
    if audit.status == "PLANNED":
        raise FleetExecutorStateError("Dispatch the distributed audit before preparing fleet jobs.")

    existing = _FLEET_RUNS.get(audit_id)
    if existing is not None:
        return existing

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
    )
    _FLEET_RUNS[audit_id] = record
    _refresh_run_gate(record)
    return record


def get_fleet_run(audit_id: str) -> FleetRunRecord | None:
    run = _FLEET_RUNS.get(audit_id)
    if run is not None:
        _refresh_run_gate(run)
    return run


def list_fleet_runs() -> list[FleetRunRecord]:
    for run in _FLEET_RUNS.values():
        _refresh_run_gate(run)
    return list(_FLEET_RUNS.values())


def lease_next_job(
    *,
    audit_id: str,
    worker_id: str,
    lease_seconds: int = 900,
) -> FleetJobRecord | None:
    if lease_seconds <= 0:
        raise FleetExecutorStateError("lease_seconds must be positive.")
    run = _FLEET_RUNS.get(audit_id)
    if run is None:
        return None
    worker = _WORKERS.get(worker_id)
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
            job.lease_expires_at = (now + timedelta(seconds=lease_seconds)).isoformat()
            job.updated_at = now.isoformat()
            run.status = "LEASING"
            run.updated_at = job.updated_at
            _refresh_run_gate(run)
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
    missing_outputs: list[str] | None = None,
    error_message: str | None = None,
    job_status: Literal["completed", "failed"] = "completed",
) -> FleetRunRecord | None:
    run = _FLEET_RUNS.get(audit_id)
    if run is None:
        return None
    job = _job(run, job_id)
    if job is None:
        raise KeyError(job_id)
    if job.assigned_worker_id != worker_id:
        raise FleetExecutorStateError("Worker cannot submit a receipt for another worker's job.")
    worker = _WORKERS.get(worker_id)
    if worker is None:
        raise FleetExecutorStateError("Worker must register before submitting job receipts.")
    _mark_stale_worker_if_expired(worker)
    if worker.status != "active":
        raise FleetExecutorStateError("Worker heartbeat is not active; cannot submit job receipts.")
    if job.status != "leased":
        raise FleetExecutorStateError("Job receipt requires an active lease.")
    if job.lease_token != lease_token:
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

    now = _utc_now()
    job.produced_outputs = produced
    job.missing_outputs = missing
    job.evidence_packet_fragment_ref = evidence_packet_fragment_ref.strip() if evidence_packet_fragment_ref else None
    job.error_message = error_message.strip() if error_message else None
    job.status = "failed" if job_status == "failed" else "completed"
    job.updated_at = now

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
    return run


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
        run.updated_at = _utc_now()
        return run

    distributed = merge_distributed_audit(audit_id)
    run.status = "COMPLETE"
    run.merged_packet_trace_id = distributed.evidence_packet_trace_id if distributed else None
    run.merge_reason = (
        "All fleet job fragments are present. Merged Evidence Packet is ready for "
        "the verifier decision layer; fleet executor does not fabricate ACCEPT."
    )
    run.updated_at = _utc_now()
    return run


def _refresh_run_gate(run: FleetRunRecord) -> None:
    registered = {worker_id for worker_id in _WORKERS}
    unregistered_jobs = [job for job in run.jobs if job.assigned_worker_id not in registered]
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


def _assert_worker_can_run_job(worker: FleetWorkerRecord, job: FleetJobRecord) -> None:
    unsupported = set(job.assigned_methods) - set(worker.supported_methods)
    if unsupported:
        raise FleetExecutorStateError(
            f"Worker {worker.worker_id} does not support assigned methods: {', '.join(sorted(unsupported))}."
        )


def _expire_stale_leases(run: FleetRunRecord) -> None:
    now = datetime.now(UTC)
    for job in run.jobs:
        if job.status == "leased" and job.lease_expires_at and _parse_utc(job.lease_expires_at) < now:
            job.status = "expired"
            job.lease_token = None
            job.updated_at = now.isoformat()


def _stale_assigned_workers(run: FleetRunRecord) -> list[str]:
    stale: set[str] = set()
    for job in run.jobs:
        worker = _WORKERS.get(job.assigned_worker_id)
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
        worker.status = "stale"
        return True
    return worker.status == "stale"


def _job(run: FleetRunRecord, job_id: str) -> FleetJobRecord | None:
    for job in run.jobs:
        if job.job_id == job_id:
            return job
    return None


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
