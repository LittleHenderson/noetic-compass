"""In-process distributed CAS Harness audit orchestration.

This is the first real control-plane layer beyond the scale planner. It
creates a run, assigns planned layer/shard work to probe workers, accepts
worker evidence receipts, and performs an evidence-gated merge. It does not
pretend to run a 100B/300B model locally and it does not return ACCEPT without
merged worker evidence plus a later verifier decision layer.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from typing import Literal, Mapping
from uuid import uuid4

from api.services.cas_harness_architecture_adapter import (
    ArchitectureAdapterSummary,
    ModelArchitectureDeclaration,
    summarize_architecture_adapter,
    validate_frontier_architecture,
)
from api.services.cas_harness_compute_feasibility import (
    ComputeEnvelopeDeclaration,
    ComputeFeasibilitySummary,
    summarize_compute_feasibility,
    validate_frontier_compute_feasibility,
)
from api.services.cas_harness_cost_acknowledgment import (
    CostExposureSummary,
    summarize_cost_exposure,
    validate_frontier_cost_acknowledgment,
)
from api.services.cas_harness_data_governance import (
    DataCaptureSummary,
    validate_distributed_data_capture,
)
from api.services.cas_harness_model_access import (
    ModelAccessSummary,
    summarize_model_access,
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
from api.services.production.state_substrate import INTERIM_TENANT, LedgerMirror, StateStore


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

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "WorkerEvidenceRecord":
        """Exact inverse of :meth:`to_dict` -- rebuild a worker-evidence row from the
        ledger on restart (docs 10 rehydrate-on-startup). Unlike the immutable plan and
        summaries, this record IS mutated downstream (dispatch, evidence receipts, merge),
        so it must come back as a real typed dataclass, not a faithful re-server."""
        return cls(
            worker_id=payload["worker_id"],
            layer_start=payload["layer_start"],
            layer_end=payload["layer_end"],
            shard_id=payload["shard_id"],
            assigned_methods=tuple(payload["assigned_methods"]),
            expected_outputs=tuple(payload["expected_outputs"]),
            worker_status=payload["worker_status"],
            produced_outputs=tuple(payload["produced_outputs"]),
            missing_outputs=tuple(payload["missing_outputs"]),
            evidence_packet_ref=payload["evidence_packet_ref"],
            error_message=payload["error_message"],
            updated_at=payload["updated_at"],
        )


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
    access: ModelAccessSummary | None = None
    provenance: ProvenanceSummary | None = None
    architecture: ArchitectureAdapterSummary | None = None
    probe: ProbeCompatibilitySummary | None = None
    compute: ComputeFeasibilitySummary | None = None
    cost: CostExposureSummary | None = None
    data_capture: DataCaptureSummary | None = None

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
            "access": self.access.to_dict() if self.access is not None else None,
            "provenance": self.provenance.to_dict() if self.provenance is not None else None,
            "architecture": self.architecture.to_dict() if self.architecture is not None else None,
            "probe": self.probe.to_dict() if self.probe is not None else None,
            "compute": self.compute.to_dict() if self.compute is not None else None,
            "cost": self.cost.to_dict() if self.cost is not None else None,
            "data_capture": self.data_capture.to_dict() if self.data_capture is not None else None,
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

# --- durable state substrate mirror (docs 10 strangler-fig migration) ------
# Dark by default: with no mirror installed, _mirror_audit/_shadow_audit are
# no-ops, so production and every existing test see zero behaviour change. The
# Phase 1/2 migration test installs an InMemoryStateStore-backed mirror to prove
# the ledger faithfully shadows _DISTRIBUTED_AUDITS before any cutover. The
# record's audit_id doubles as the ledger trace_id -- it is the correlation id
# threading a distributed run's worker evidence together.
_STATE_MIRROR: LedgerMirror | None = None
_MIRROR_KIND = "distributed_audit"
_MIRROR_SOURCE = "cas_harness_distributed_audits"


def set_state_mirror(mirror: LedgerMirror | None) -> None:
    """Install (or clear) the dual-write/shadow-read ledger mirror for this service."""
    global _STATE_MIRROR
    _STATE_MIRROR = mirror


def _mirror_audit(record: DistributedAuditRecord) -> DistributedAuditRecord:
    """Phase 1 dual-write: shadow this audit into the ledger and return ``record`` so
    mutators can ``return _mirror_audit(record)`` at each exit. Non-authoritative -- a
    ledger failure is logged as a divergence inside the mirror, never raised here."""
    if _STATE_MIRROR is not None:
        _STATE_MIRROR.mirror_put(
            _MIRROR_KIND, record.audit_id, record.to_dict(),
            source=_MIRROR_SOURCE, trace_id=record.audit_id,
        )
    return record


def _shadow_audit(record: DistributedAuditRecord) -> DistributedAuditRecord:
    """Phase 2 shadow-read: compare the dict-served record against the ledger. Returns
    the SAME record object so in-place mutation by callers is preserved."""
    if _STATE_MIRROR is not None:
        _STATE_MIRROR.shadow_compare(_MIRROR_KIND, record.audit_id, record.to_dict())
    return record


def reset_distributed_audits_for_tests() -> None:
    _DISTRIBUTED_AUDITS.clear()
    # The mirror is test-only scaffolding; clearing it here keeps it from leaking
    # across tests via the shared reset fixture.
    set_state_mirror(None)


# --- rehydrate-on-startup (docs 10 Phase-3 prerequisite) -------------------
# A restart loses the in-RAM dicts -- the only thing the current single-process
# design keeps the state in. Before read-authority can move off the dicts, a
# restarted process must rebuild _DISTRIBUTED_AUDITS from the durable ledger and
# serve the same audits it served before. rehydrate_from_ledger does that read.
# It is the inverse of the dual-write in _mirror_audit: mirror_put wrote
# record.to_dict(); this reads those rows back and reconstructs the records.


@dataclass(frozen=True)
class _RehydratedSummary:
    """A faithfully reloaded immutable audit summary.

    The seven audit summaries (access / provenance / architecture / probe / compute /
    cost / data_capture) are DECLARED receipts computed once at create_distributed_audit
    time and never mutated afterwards. The only thing any downstream code ever does with
    them is re-serve them via ``to_dict()`` (the HTTP layer renders the record; nothing
    reads their typed fields). So the honest, highest-fidelity way to survive a restart
    is to reload the exact serialization the ledger holds and re-serve it verbatim -- NOT
    to recompute the summary (which could drift from what the original run actually
    recorded) and NOT to fabricate a richer typed object than the durable ledger stored.
    This carrier is that faithful re-server: it holds the stored dict and returns an
    independent copy of it, satisfying the same ``.to_dict()`` contract the real summary
    did, so :meth:`DistributedAuditRecord.to_dict` renders byte-identically after a
    restart. The payload is deep-copied so a mutation of a served dict can never reach
    back into the carrier (or, via an aliased in-memory ledger row, the store)."""

    _payload: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return copy.deepcopy(dict(self._payload))


def _rehydrated_summary(value: object) -> _RehydratedSummary | None:
    """Wrap a stored summary dict in a faithful re-server, or pass through ``None``."""
    if value is None:
        return None
    return _RehydratedSummary(copy.deepcopy(value))


def _audit_from_ledger_payload(payload: Mapping[str, object]) -> DistributedAuditRecord:
    """Reconstruct a :class:`DistributedAuditRecord` from its stored ledger payload.

    The stored payload is ``record.to_dict()``. Its scalar fields copy back directly;
    the plan is rebuilt via :meth:`ScalePlan.from_dict`; each worker-evidence row via
    :meth:`WorkerEvidenceRecord.from_dict`; the immutable summaries via the faithful
    re-server above. The derived aggregates ``to_dict`` folds in (``ready_workers``,
    ``failed_workers``, ``total_workers``, ``missing_outputs``) are deliberately ignored
    here: they are pure functions of ``worker_evidence`` and ``to_dict`` recomputes them,
    so reconstructing from the reconstructed worker_evidence reproduces them exactly."""
    return DistributedAuditRecord(
        audit_id=payload["audit_id"],
        plan_id=payload["plan_id"],
        plan=ScalePlan.from_dict(payload["plan"]),
        status=payload["status"],
        merge_status=payload["merge_status"],
        worker_evidence=[
            WorkerEvidenceRecord.from_dict(worker) for worker in payload["worker_evidence"]
        ],
        created_at=payload["created_at"],
        updated_at=payload["updated_at"],
        verdict=payload["verdict"],
        confidence=payload["confidence"],
        evidence_packet_trace_id=payload["evidence_packet_trace_id"],
        merge_reason=payload["merge_reason"],
        access=_rehydrated_summary(payload["access"]),
        provenance=_rehydrated_summary(payload["provenance"]),
        architecture=_rehydrated_summary(payload["architecture"]),
        probe=_rehydrated_summary(payload["probe"]),
        compute=_rehydrated_summary(payload["compute"]),
        cost=_rehydrated_summary(payload["cost"]),
        data_capture=_rehydrated_summary(payload["data_capture"]),
    )


def rehydrate_from_ledger(store: StateStore) -> int:
    """Rebuild ``_DISTRIBUTED_AUDITS`` from the durable ledger; return the count restored.

    Reads every ``distributed_audit`` row under :data:`INTERIM_TENANT` and reconstructs
    the in-RAM record for each. Unlike the non-authoritative mirror, this does NOT swallow
    backend errors: a failed rehydrate means we cannot honestly claim to have restored the
    pre-restart state, so the ``StateStoreError`` propagates and startup fails loudly rather
    than coming up with a silently empty view that looks authoritative. Reconstruction is
    done into a fresh dict and swapped in only once every row rebuilds, so a malformed row
    cannot leave the service half-populated.

    This is the read side of the docs-10 cutover prerequisite. It does not move read
    authority off the dicts -- it makes the dicts survivable so that a later, separately
    gated step can.
    """
    rebuilt: dict[str, DistributedAuditRecord] = {}
    for record in store.list(INTERIM_TENANT, _MIRROR_KIND):
        audit = _audit_from_ledger_payload(record.payload)
        rebuilt[audit.audit_id] = audit
    _DISTRIBUTED_AUDITS.clear()
    _DISTRIBUTED_AUDITS.update(rebuilt)
    return len(rebuilt)


def create_distributed_audit(
    request: ScalePlanRequest,
    *,
    provenance: ModelProvenanceManifest | None = None,
    architecture: ModelArchitectureDeclaration | None = None,
    probe: ProbeReadoutSpecification | None = None,
    compute: ComputeEnvelopeDeclaration | None = None,
    cost_acknowledged: bool = False,
    data_capture_acknowledged: bool = False,
) -> DistributedAuditRecord:
    plan = build_scale_plan(request)

    # Run-gate (2): build_scale_plan already refused any non-open-weight access mode
    # (the mechanistic probe cannot reach a hosted/black-box target at any size), so by
    # here the plan is open-weight by construction. Record the honest access receipt --
    # DECLARED, never VERIFIED at this tier -- so every run carries it for traceability.
    access_summary = summarize_model_access(declared_mode=plan.weight_access)

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

    # Frontier run-gate (3): gates (5)-(7) confirmed the *model* is auditable; this gate
    # confirms the declared *hardware* can physically hold it. The planner provisions only
    # USABLE_MEMORY_FRACTION of each accelerator and silently clamps the probe-worker
    # fan-out to MAX_WORKER_FANOUT, so a frontier model can get a plan that looks
    # schedulable while every shard is asked to hold more than one accelerator can fit. The
    # gate compares the plan's own estimated_total_runtime_gb against the capped fleet's
    # aggregate usable memory and refuses (ValueError -> HTTP 422) when the declared envelope
    # cannot cover it -- a too-small per-accelerator size (needs more than MAX_WORKER_FANOUT
    # workers) or simply too few accelerators. A sufficient envelope lands at
    # COMPUTE_FEASIBILITY_DECLARED (the real resident-set fit is confirmed fleet-side). Below
    # the frontier rung the envelope is optional and recorded, never a blocker.
    compute_summary: ComputeFeasibilitySummary | None = None
    if plan.validation_status == "EXPERIMENTAL_NOT_VALIDATED":
        compute_summary = validate_frontier_compute_feasibility(plan=plan, envelope=compute)
    elif compute is not None:
        compute_summary = summarize_compute_feasibility(plan=plan, envelope=compute)

    # Frontier run-gate (4): gates (5)-(7)+(3) confirmed the run *can* run; this gate
    # confirms the caller accepts what running it *costs*. A frontier run commits the
    # plan's recommended worker fleet to hold a 300B-4T model for a duration CAS Harness
    # does not estimate, at a dollar cost it does not quote, bill, or cap -- for a result
    # already labelled EXPERIMENTAL_NOT_VALIDATED. The gate refuses (ValueError -> HTTP 422)
    # unless the caller explicitly acknowledges that caller-owned, unquoted cost; it never
    # invents a price (the system models no duration or rate it could honestly quote). It
    # runs after compute so the receipt can surface the now-validated fleet's real size.
    # Below the frontier rung the committed fleet is modest, so a volunteered
    # acknowledgement is recorded for traceability, but its absence never blocks the run.
    cost_summary: CostExposureSummary | None = None
    if plan.validation_status == "EXPERIMENTAL_NOT_VALIDATED":
        cost_summary = validate_frontier_cost_acknowledgment(
            plan=plan, compute=compute_summary, acknowledged=cost_acknowledged
        )
    elif cost_acknowledged:
        cost_summary = summarize_cost_exposure(
            plan=plan, compute=compute_summary, acknowledged=cost_acknowledged
        )

    # Run-gate (8): every distributed run -- frontier or not -- is a data *harvest*. It
    # captures the target model's I/O, the pooled activations the probe hooks, the CAS
    # axis readout each shard emits, and the verdict, and commits them to an immutable
    # write-once store reused as CAS-Native training signal. This gate refuses
    # (ValueError -> HTTP 422) unless the caller acknowledges that capture, retention,
    # and reuse. It is UNIVERSAL, not frontier-only (mirroring gate (2)): the harvest is
    # intrinsic to the method and does not scale with model size, so the acknowledgment is
    # required for a 20B run exactly as for a 1T one. It runs last, after the frontier
    # gates, so a still-unmet earlier gate surfaces first; for a below-frontier run, where
    # none of the frontier gates fire, this is the one run gate that still applies. It is a
    # run gate, not a plan gate -- a planning-only /scale-plan preview captures nothing, so
    # it is never enforced there (build_scale_plan above does not run it).
    data_capture_summary = validate_distributed_data_capture(
        acknowledged=data_capture_acknowledged
    )

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
        access=access_summary,
        provenance=provenance_summary,
        architecture=architecture_summary,
        probe=probe_summary,
        cost=cost_summary,
        compute=compute_summary,
        data_capture=data_capture_summary,
    )
    _DISTRIBUTED_AUDITS[audit_id] = record
    return _mirror_audit(record)


def get_distributed_audit(audit_id: str) -> DistributedAuditRecord | None:
    record = _DISTRIBUTED_AUDITS.get(audit_id)
    return _shadow_audit(record) if record is not None else None


def list_distributed_audits() -> list[DistributedAuditRecord]:
    records = list(_DISTRIBUTED_AUDITS.values())
    if _STATE_MIRROR is not None:
        _STATE_MIRROR.shadow_compare_all(
            _MIRROR_KIND, {r.audit_id: r.to_dict() for r in records}
        )
    return records


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
        return _mirror_audit(record)
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
    return _mirror_audit(record)


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
    return _mirror_audit(record)


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
        return _mirror_audit(record)
    if incomplete:
        record.status = "MERGE_PENDING"
        record.merge_status = "partial"
        record.verdict = None
        record.confidence = None
        record.merge_reason = f"Waiting for worker evidence from: {', '.join(incomplete)}."
        return _mirror_audit(record)
    if missing_packet_refs:
        record.status = "COMPLETE"
        record.merge_status = "partial"
        record.verdict = "FLAG_FOR_HUMAN_REVIEW"
        record.confidence = None
        record.merge_reason = (
            "Distributed audit completed with worker receipts missing Evidence Packet refs; "
            f"cannot ACCEPT. Missing refs: {', '.join(missing_packet_refs)}."
        )
        return _mirror_audit(record)
    if missing:
        record.status = "COMPLETE"
        record.merge_status = "partial"
        record.verdict = "FLAG_FOR_HUMAN_REVIEW"
        record.confidence = None
        record.merge_reason = (
            "Distributed audit completed with missing worker outputs; cannot ACCEPT. "
            f"Missing outputs: {', '.join(missing)}."
        )
        return _mirror_audit(record)

    record.status = "COMPLETE"
    record.merge_status = "complete"
    record.verdict = "FLAG_FOR_HUMAN_REVIEW"
    record.confidence = None
    record.evidence_packet_trace_id = f"{record.audit_id}-distributed-merge"
    record.merge_reason = (
        "All distributed worker evidence receipts merged. Final ACCEPT/SUPPRESS still "
        "requires the verifier decision layer over the merged Evidence Packet."
    )
    return _mirror_audit(record)


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
