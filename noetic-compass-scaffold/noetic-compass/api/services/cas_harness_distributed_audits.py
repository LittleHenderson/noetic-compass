"""In-process distributed CAS Harness audit orchestration.

This is the first real control-plane layer beyond the scale planner. It
creates a run, assigns planned layer/shard work to probe workers, accepts
worker evidence receipts, and performs an evidence-gated merge. It does not
pretend to run a 100B/300B model locally and it does not return ACCEPT without
merged worker evidence plus a later verifier decision layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from typing import Literal
from uuid import uuid4

from api.services.cas_harness_architecture_adapter import (
    ArchitectureAdapterSummary,
    ModelArchitectureDeclaration,
    summarize_architecture_adapter,
    validate_frontier_architecture,
)
from api.services.cas_harness_model_provenance import (
    ModelProvenanceManifest,
    ProvenanceSummary,
    summarize_model_provenance,
    validate_frontier_provenance,
)
from api.services.cas_harness_probe_compatibility import (
    ProbeCompatibilitySummary,
    ProbeReadoutSpecification,
    summarize_probe_compatibility,
    validate_frontier_probe_compatibility,
)
from api.services.cas_harness_scale_planner import ScalePlan, ScalePlanRequest, build_scale_plan


DistributedAuditStatus = Literal[
    "PLANNED",
    "DISPATCHED",
    "RUNNING",
    "MERGE_PENDING",
    "COMPLETE",
    "FAILED",
]
DistributedWorkerStatus = Literal["queued", "assigned", "running", "completed", "failed"]
DistributedMergeStatus = Literal["pending", "partial", "complete", "failed"]
DistributedVerdict = Literal["ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"]


class DistributedAuditStateError(ValueError):
    """Raised when a distributed audit transition would overstate readiness."""


@dataclass
class WorkerEvidenceRecord:
    worker_id: str
    layer_start: int
    layer_end: int
    shard_id: str
    assigned_methods: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    worker_status: DistributedWorkerStatus = "queued"
    produced_outputs: tuple[str, ...] = ()
    missing_outputs: tuple[str, ...] = ()
    evidence_packet_ref: str | None = None
    error_message: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "layer_start": self.layer_start,
            "layer_end": self.layer_end,
            "shard_id": self.shard_id,
            "assigned_methods": list(self.assigned_methods),
            "expected_outputs": list(self.expected_outputs),
            "worker_status": self.worker_status,
            "produced_outputs": list(self.produced_outputs),
            "missing_outputs": list(self.missing_outputs),
            "evidence_packet_ref": self.evidence_packet_ref,
            "error_message": self.error_message,
            "updated_at": self.updated_at,
        }


@dataclass
class DistributedAuditRecord:
    audit_id: str
    plan_id: str
    plan: ScalePlan
    status: DistributedAuditStatus
    merge_status: DistributedMergeStatus
    worker_evidence: list[WorkerEvidenceRecord]
    created_at: str
    updated_at: str
    verdict: DistributedVerdict | None = None
    confidence: float | None = None
    evidence_packet_trace_id: str | None = None
    merge_reason: str = "Distributed audit planned; no worker evidence has been merged yet."
    provenance: ProvenanceSummary | None = None
    architecture: ArchitectureAdapterSummary | None = None
    probe: ProbeCompatibilitySummary | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "audit_id": self.audit_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "merge_status": self.merge_status,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "evidence_packet_trace_id": self.evidence_packet_trace_id,
            "merge_reason": self.merge_reason,
            "provenance": self.provenance.to_dict() if self.provenance is not None else None,
            "architecture": self.architecture.to_dict() if self.architecture is not None else None,
            "probe": self.probe.to_dict() if self.probe is not None else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "plan": self.plan.to_dict(),
            "worker_evidence": [worker.to_dict() for worker in self.worker_evidence],
            "ready_workers": sum(1 for worker in self.worker_evidence if worker.worker_status == "completed"),
            "failed_workers": sum(1 for worker in self.worker_evidence if worker.worker_status == "failed"),
            "total_workers": len(self.worker_evidence),
            "missing_outputs": _missing_outputs(self.worker_evidence),
        }


_DISTRIBUTED_AUDITS: dict[str, DistributedAuditRecord] = {}


def reset_distributed_audits_for_tests() -> None:
    _DISTRIBUTED_AUDITS.clear()


def create_distributed_audit(
    request: ScalePlanRequest,
    *,
    provenance: ModelProvenanceManifest | None = None,
    architecture: ModelArchitectureDeclaration | None = None,
    probe: ProbeReadoutSpecification | None = None,
) -> DistributedAuditRecord:
    plan = build_scale_plan(request)

    # Frontier run-gate (5): a real 300B-4T run (the EXPERIMENTAL_NOT_VALIDATED rung)
    # must carry a valid model provenance/license/weight-hash manifest, or it is
    # refused here (the caller converts this ValueError to HTTP 422). At create time
    # no weights are loaded in this tier, so a good manifest lands at
    # DECLARED_NOT_VERIFIED; the probe workers recompute the hashes downstream.
    # Below the frontier rung a manifest is optional -- if one is supplied we record
    # its honest summary, but we never block the validated/engineered lanes on it.
    provenance_summary: ProvenanceSummary | None = None
    if plan.validation_status == "EXPERIMENTAL_NOT_VALIDATED":
        provenance_summary = validate_frontier_provenance(
            expected_model_id=plan.model_id, manifest=provenance
        )
    elif provenance is not None:
        provenance_summary = summarize_model_provenance(
            manifest=provenance, expected_model_id=plan.model_id
        )

    # Frontier run-gate (6): a real 300B-4T run must declare an architecture whose
    # model_type resolves to a probe adapter the worker can mechanically hook (one of
    # the four decoder-stack paths in locate_transformer_layers). An architecture the
    # worker cannot locate would raise rather than produce activations, so it is refused
    # here (ValueError -> HTTP 422). At create time the declaration is checked against the
    # adapter registry only -- the real model layout is confirmed worker-side at load
    # time -- so a supported declaration lands at ARCHITECTURE_ADAPTER_AVAILABLE. Below the
    # frontier rung the declaration is optional and recorded, never a blocker.
    architecture_summary: ArchitectureAdapterSummary | None = None
    if plan.validation_status == "EXPERIMENTAL_NOT_VALIDATED":
        architecture_summary = validate_frontier_architecture(declaration=architecture)
    elif architecture is not None:
        architecture_summary = summarize_architecture_adapter(declaration=architecture)

    # Frontier run-gate (7): gate (6) confirmed the worker can *locate and hook* the
    # decoder stack; this gate confirms it can turn those activations into the CAS axis
    # readout -- the run's central deliverable, declared in every shard's expected_outputs.
    # The worker's compute_cas_axis_readout requires a probe whose schema_version is
    # 'cas_probe_linear_v1', a non-empty axis set, and per-axis vectors that match the
    # pooled-activation feature dimension; a missing probe makes the CAS readout come back
    # *missing* (dishonest by omission) and a malformed one aborts the whole shard. So a
    # real 300B-4T run is refused here (ValueError -> HTTP 422) without a structurally
    # loadable probe spec; a good spec lands at PROBE_COMPATIBILITY_DECLARED (the worker
    # confirms the final dimensional match at readout time). Below the frontier rung the
    # spec is optional and recorded, never a blocker.
    probe_summary: ProbeCompatibilitySummary | None = None
    if plan.validation_status == "EXPERIMENTAL_NOT_VALIDATED":
        probe_summary = validate_frontier_probe_compatibility(specification=probe)
    elif probe is not None:
        probe_summary = summarize_probe_compatibility(specification=probe)

    now = datetime.now(UTC).isoformat()
    audit_id = _audit_id_for(plan)

    worker_evidence = [
        WorkerEvidenceRecord(
            worker_id=assignment.worker_id,
            layer_start=assignment.layer_start,
            layer_end=assignment.layer_end,
            shard_id=assignment.shard_id,
            assigned_methods=tuple(assignment.assigned_methods),
            expected_outputs=tuple(assignment.expected_outputs),
        )
        for assignment in plan.worker_assignments
    ]
    record = DistributedAuditRecord(
        audit_id=audit_id,
        plan_id=f"cas-plan-{audit_id.removeprefix('cas-dist-')}",
        plan=plan,
        status="PLANNED",
        merge_status="pending",
        worker_evidence=worker_evidence,
        created_at=now,
        updated_at=now,
        provenance=provenance_summary,
        architecture=architecture_summary,
        probe=probe_summary,
    )
    _DISTRIBUTED_AUDITS[audit_id] = record
    return record


def get_distributed_audit(audit_id: str) -> DistributedAuditRecord | None:
    return _DISTRIBUTED_AUDITS.get(audit_id)


def list_distributed_audits() -> list[DistributedAuditRecord]:
    return list(_DISTRIBUTED_AUDITS.values())


def dispatch_distributed_audit(audit_id: str) -> DistributedAuditRecord | None:
    record = get_distributed_audit(audit_id)
    if record is None:
        return None
    if record.status == "PLANNED":
        now = datetime.now(UTC).isoformat()
        record.status = "DISPATCHED"
        record.merge_status = "pending"
        record.merge_reason = "Probe Worker assignments dispatched; waiting for worker evidence receipts."
        record.updated_at = now
        for worker in record.worker_evidence:
            if worker.worker_status == "queued":
                worker.worker_status = "assigned"
                worker.updated_at = now
    return record


def mark_worker_running(audit_id: str, worker_id: str) -> DistributedAuditRecord | None:
    record = get_distributed_audit(audit_id)
    if record is None:
        return None
    if record.status == "PLANNED":
        raise DistributedAuditStateError("Dispatch Probe Worker assignments before marking a worker running.")
    if record.status in {"COMPLETE", "FAILED"}:
        raise DistributedAuditStateError("Completed distributed audit sessions cannot be marked running.")
    worker = _worker(record, worker_id)
    if worker is None:
        raise KeyError(worker_id)
    if worker.worker_status == "queued":
        raise DistributedAuditStateError("Worker has not been assigned; dispatch the audit first.")
    worker.worker_status = "running"
    worker.updated_at = datetime.now(UTC).isoformat()
    record.status = "RUNNING"
    record.updated_at = worker.updated_at
    record.merge_reason = "At least one Probe Worker is running."
    return record


def record_worker_evidence(
    audit_id: str,
    worker_id: str,
    *,
    produced_outputs: list[str],
    missing_outputs: list[str] | None = None,
    evidence_packet_ref: str | None = None,
    error_message: str | None = None,
    worker_status: Literal["completed", "failed"] = "completed",
) -> DistributedAuditRecord | None:
    record = get_distributed_audit(audit_id)
    if record is None:
        return None
    if record.status == "PLANNED":
        raise DistributedAuditStateError("Dispatch Probe Worker assignments before accepting evidence receipts.")
    if record.status in {"COMPLETE", "FAILED"}:
        raise DistributedAuditStateError("Completed distributed audit sessions cannot accept new worker evidence.")
    worker = _worker(record, worker_id)
    if worker is None:
        raise KeyError(worker_id)
    if worker.worker_status == "queued":
        raise DistributedAuditStateError("Worker has not been assigned; dispatch the audit first.")
    if worker_status == "completed" and not (evidence_packet_ref or "").strip():
        raise DistributedAuditStateError("Completed worker evidence requires an evidence_packet_ref.")
    if worker_status == "failed" and not (error_message or "").strip():
        raise DistributedAuditStateError("Failed worker evidence requires an error_message.")

    produced = tuple(_dedupe_nonempty(produced_outputs))
    explicit_missing = set(_dedupe_nonempty(missing_outputs or []))
    expected_missing = set(worker.expected_outputs) - set(produced)
    missing = tuple(sorted(explicit_missing | expected_missing))
    now = datetime.now(UTC).isoformat()

    worker.produced_outputs = produced
    worker.missing_outputs = missing
    worker.evidence_packet_ref = evidence_packet_ref
    worker.error_message = error_message
    worker.worker_status = "failed" if worker_status == "failed" or error_message else "completed"
    worker.updated_at = now

    record.updated_at = now
    record.status = "MERGE_PENDING"
    record.merge_status = "partial"
    record.merge_reason = "Worker evidence receipt recorded; merge not finalized yet."
    return record


def merge_distributed_audit(audit_id: str) -> DistributedAuditRecord | None:
    record = get_distributed_audit(audit_id)
    if record is None:
        return None
    if record.status == "PLANNED":
        raise DistributedAuditStateError("Dispatch Probe Worker assignments before merging worker evidence.")

    now = datetime.now(UTC).isoformat()
    failed = [worker.worker_id for worker in record.worker_evidence if worker.worker_status == "failed"]
    incomplete = [
        worker.worker_id
        for worker in record.worker_evidence
        if worker.worker_status != "completed"
    ]
    missing = _missing_outputs(record.worker_evidence)
    missing_packet_refs = [
        worker.worker_id
        for worker in record.worker_evidence
        if worker.worker_status == "completed" and not worker.evidence_packet_ref
    ]

    record.updated_at = now
    if failed:
        record.status = "COMPLETE"
        record.merge_status = "failed"
        record.verdict = "FLAG_FOR_HUMAN_REVIEW"
        record.confidence = None
        record.merge_reason = f"Distributed audit has failed worker evidence: {', '.join(failed)}."
        return record
    if incomplete:
        record.status = "MERGE_PENDING"
        record.merge_status = "partial"
        record.verdict = None
        record.confidence = None
        record.merge_reason = f"Waiting for worker evidence from: {', '.join(incomplete)}."
        return record
    if missing_packet_refs:
        record.status = "COMPLETE"
        record.merge_status = "partial"
        record.verdict = "FLAG_FOR_HUMAN_REVIEW"
        record.confidence = None
        record.merge_reason = (
            "Distributed audit completed with worker receipts missing Evidence Packet refs; "
            f"cannot ACCEPT. Missing refs: {', '.join(missing_packet_refs)}."
        )
        return record
    if missing:
        record.status = "COMPLETE"
        record.merge_status = "partial"
        record.verdict = "FLAG_FOR_HUMAN_REVIEW"
        record.confidence = None
        record.merge_reason = (
            "Distributed audit completed with missing worker outputs; cannot ACCEPT. "
            f"Missing outputs: {', '.join(missing)}."
        )
        return record

    record.status = "COMPLETE"
    record.merge_status = "complete"
    record.verdict = "FLAG_FOR_HUMAN_REVIEW"
    record.confidence = None
    record.evidence_packet_trace_id = f"{record.audit_id}-distributed-merge"
    record.merge_reason = (
        "All distributed worker evidence receipts merged. Final ACCEPT/SUPPRESS still "
        "requires the verifier decision layer over the merged Evidence Packet."
    )
    return record


def _audit_id_for(plan: ScalePlan) -> str:
    payload = {
        "model_id": plan.model_id,
        "parameter_count_b": plan.parameter_count_b,
        "num_layers": plan.num_layers,
        "worker_count": plan.recommended_worker_count,
        "precision": plan.memory_estimate.precision,
        "run_nonce": uuid4().hex,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"cas-dist-{digest[:16]}"


def _worker(record: DistributedAuditRecord, worker_id: str) -> WorkerEvidenceRecord | None:
    for worker in record.worker_evidence:
        if worker.worker_id == worker_id:
            return worker
    return None


def _dedupe_nonempty(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if stripped and stripped not in seen:
            cleaned.append(stripped)
            seen.add(stripped)
    return cleaned


def _missing_outputs(workers: list[WorkerEvidenceRecord]) -> list[str]:
    missing: set[str] = set()
    for worker in workers:
        missing.update(worker.missing_outputs)
    return sorted(missing)
