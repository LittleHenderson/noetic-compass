"""CAS Harness audit API scaffold.

This route owns the M1 audit-session lifecycle contract. It stores sessions
in-process and advances state honestly, but it does not fabricate CAS verdicts
until a real audit runner is wired behind it.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, field_validator, model_validator

from api.routes.evidence import build_packet_for_trace, load_stage9_40e_packet_payload_for_trace
from api.services.cas_harness_audit_sessions import (
    create_session,
    get_session,
    list_sessions,
    run_session,
)
from api.services.cas_harness_distributed_audits import (
    DistributedAuditStateError,
    create_distributed_audit,
    dispatch_distributed_audit,
    get_distributed_audit,
    list_distributed_audits,
    mark_worker_running,
    merge_distributed_audit,
    record_worker_evidence,
)
from api.services.cas_harness_evidence_bridge import normalize_evidence_packet_for_audit
from api.services.cas_harness_fleet_executor import (
    FleetExecutorStateError,
    get_fleet_run,
    heartbeat_worker,
    lease_next_job,
    list_fleet_runs,
    list_workers,
    mark_stale_workers,
    merge_fleet_evidence,
    prepare_fleet_for_audit,
    register_worker,
    submit_job_receipt,
)
from api.services.cas_harness_fleet_verifier import (
    FleetVerifierStateError,
    verify_merged_fleet_packet,
)
from api.services.cas_harness_scale_planner import (
    ScalePlanRequest as PlannerScalePlanRequest,
    build_scale_plan,
)
from api.services.cas_harness_verifier_decision_adapter import verifier_decision_from_packet


router = APIRouter(prefix="/api/cas-harness/audit", tags=["cas_harness_audit"])

AuditMode = Literal["BALANCED", "HIGH_PRECISION", "MAX_COVERAGE_TRIAGE"]
ScalePlanPrecision = Literal["fp16", "bf16", "int8", "int4"]
ScalePlanAuditDepth = Literal["FULL_INTERNAL", "LAYER_SAMPLE"]
ScalePlanTier = Literal[
    "single_worker_open_weight",
    "small_distributed_open_weight",
    "distributed_open_weight",
    "enterprise_distributed_open_weight",
]
AuditStatus = Literal[
    "DRAFT",
    "VALIDATING",
    "RUNNING",
    "EVIDENCE_PENDING",
    "SCAFFOLD_PENDING_RUNNER",
    "EVIDENCE_READY",
    "COMPLETE",
    "FAILED",
]
ModelStatus = Literal["NOT_CONNECTED_MOCK"]
ModelTargetKind = Literal["demo_reference", "api_endpoint"]
ModelConnectionState = Literal["CONNECTED", "CONFIGURED"]
VerifiedModelStatus = Literal["CONNECTED", "READY"]
CredentialMode = Literal["none", "credential_ref", "ephemeral_secret"]
Verdict = Literal["ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"]
ProofChipId = Literal[
    "model_proof",
    "cas_readout",
    "causal_proof",
    "control_proof",
    "output_proof",
    "packet_proof",
]
ProofChipStatus = Literal["verified", "present", "missing", "failed", "unavailable"]

REFERENCE_TARGET_MODEL_ID = "EleutherAI/pythia-160m"
REFERENCE_TARGET_PROVIDER = "cas_harness_reference"
REFERENCE_TARGET_EVIDENCE_PACKET_TRACE_ID = "cas_harness_reference_accept_001"
_LOCAL_HTTP_HOSTS = {"localhost", "127.0.0.1", "::1"}


class ProvenanceChip(BaseModel):
    id: ProofChipId
    name: str = Field(..., min_length=1, max_length=64)
    status: ProofChipStatus
    detail: str = Field(..., min_length=1, max_length=1000)


class AuditLifecycleEvent(BaseModel):
    status: AuditStatus
    message: str = Field(..., min_length=1, max_length=240)
    timestamp: str


class VerifierDecision(BaseModel):
    verdict: Verdict
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: str = Field(..., min_length=1, max_length=160)
    reason: str = Field(..., min_length=1, max_length=500)
    decision_scope: str | None = Field(default=None, min_length=1, max_length=160)
    coverage: dict[str, object] | None = None


class ModelTargetConfig(BaseModel):
    """User-submitted model target config for the Audit Console connect step."""

    model_config = ConfigDict(extra="forbid")

    kind: ModelTargetKind = Field(
        default="api_endpoint",
        description="Use demo_reference for the built-in safe reference target; api_endpoint for customer targets.",
    )
    provider: str | None = Field(default=None, min_length=1, max_length=120)
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    endpoint_url: HttpUrl | None = None
    credential_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Reference to a server-side credential; raw secrets are not echoed or persisted.",
    )
    api_key: SecretStr | None = Field(
        default=None,
        min_length=1,
        max_length=4096,
        description="Optional one-request secret for future live probing; never returned by this endpoint.",
    )
    allow_unauthenticated: bool = Field(
        default=False,
        description="Set true only for public or locally controlled endpoints that do not require credentials.",
    )
    timeout_ms: int = Field(default=10_000, ge=100, le=60_000)

    @field_validator("provider", "model_id", "credential_ref")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("api_key")
    @classmethod
    def strip_optional_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        return value if value.get_secret_value().strip() else None

    @model_validator(mode="after")
    def validate_target_config(self) -> "ModelTargetConfig":
        if self.kind == "demo_reference":
            if self.endpoint_url is not None:
                raise ValueError("demo_reference target must not include endpoint_url")
            if self.credential_ref is not None or self.api_key is not None:
                raise ValueError("demo_reference target must not include credentials")
            if self.model_id and self.model_id != REFERENCE_TARGET_MODEL_ID:
                raise ValueError(
                    f"demo_reference target only supports {REFERENCE_TARGET_MODEL_ID}"
                )
            return self

        if self.endpoint_url is None:
            raise ValueError("api_endpoint target requires endpoint_url")
        if not self.model_id:
            raise ValueError("api_endpoint target requires model_id")
        if self.credential_ref is not None and self.api_key is not None:
            raise ValueError("Provide either credential_ref or api_key, not both")
        if (
            self.credential_ref is None
            and self.api_key is None
            and not self.allow_unauthenticated
        ):
            raise ValueError(
                "api_endpoint target requires credential_ref, api_key, "
                "or allow_unauthenticated=true"
            )
        if not _is_allowed_endpoint_url(str(self.endpoint_url)):
            raise ValueError("endpoint_url must use https unless it targets localhost")
        return self


class ModelTargetVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: ModelTargetConfig = Field(..., description="Model target to validate for CAS Harness.")


class VerifiedModelTarget(BaseModel):
    kind: ModelTargetKind
    provider: str
    model_id: str
    endpoint_url: str | None
    credential_mode: CredentialMode
    timeout_ms: int


class ModelTargetVerificationResponse(BaseModel):
    connection_id: str
    connection_state: ModelConnectionState
    model_status: VerifiedModelStatus
    can_run_audit: bool
    target: VerifiedModelTarget
    detail: str = Field(..., min_length=1, max_length=1000)
    checked_at: str
    provenance_chip: ProvenanceChip
    verdict: Verdict | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_packet_trace_id: str | None = None
    atlas_deep_link: str | None = None
    reference_evidence_packet_trace_id: str | None = None


class AuditSessionRequest(BaseModel):
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    endpoint_url: HttpUrl | None = None
    audit_mode: AuditMode = "BALANCED"
    prompt: str | None = Field(default=None, min_length=1, max_length=12000)
    scenario_text: str | None = Field(default=None, min_length=1, max_length=12000)
    selected_modules: list[str] = Field(..., min_length=1, max_length=24)
    evidence_packet_trace_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        description="Optional existing Evidence Packet trace ID to attach as proof-chip evidence.",
    )
    license_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Placeholder for future license validation; not billed or verified here.",
    )

    @field_validator("model_id", "prompt", "scenario_text", "evidence_packet_trace_id", "license_key")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("selected_modules")
    @classmethod
    def validate_selected_modules(cls, modules: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for module in modules:
            name = module.strip() if isinstance(module, str) else ""
            if not name:
                raise ValueError("selected_modules entries must be non-empty strings")
            if len(name) > 80:
                raise ValueError("selected_modules entries must be 80 characters or fewer")
            if name not in seen:
                cleaned.append(name)
                seen.add(name)
        return cleaned

    @model_validator(mode="after")
    def require_target_and_scenario(self) -> "AuditSessionRequest":
        if not self.model_id and not self.endpoint_url:
            raise ValueError("Either model_id or endpoint_url is required")
        if not self.prompt and not self.scenario_text:
            raise ValueError("Either prompt or scenario_text is required")
        return self


class AuditSessionResponse(BaseModel):
    audit_id: str
    status: AuditStatus
    model_status: ModelStatus
    model_id: str | None
    endpoint_url: str | None
    audit_mode: AuditMode
    prompt_summary: str | None
    scenario_summary: str | None
    selected_modules: list[str]
    created_at: str
    updated_at: str
    verdict: Verdict | None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_packet_trace_id: str | None
    atlas_deep_link: str | None
    provenance_chips: list[ProvenanceChip]
    verifier_decision: VerifierDecision | None = None
    lifecycle: list[AuditLifecycleEvent]


class AuditSessionListResponse(BaseModel):
    sessions: list[AuditSessionResponse]


class ScalePlanWorkerAssignment(BaseModel):
    worker_id: str
    layer_start: int
    layer_end: int
    shard_id: str
    assigned_methods: list[str]
    expected_outputs: list[str]


class ScalePlanMemoryEstimate(BaseModel):
    precision: ScalePlanPrecision
    total_weight_memory_gb: float
    activation_overhead_gb: float
    estimated_total_runtime_gb: float
    estimated_memory_per_worker_gb: float


class ScalePlanRequest(BaseModel):
    """Open-weight enterprise planning request.

    This endpoint creates a deployment plan only. It does not claim a verdict,
    run a customer model, or offer black-box/API-only auditing.
    """

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(..., min_length=1, max_length=200)
    weight_access: Literal["open_weight"] = Field(
        default="open_weight",
        description="CAS Harness beta enterprise planning is open-weight/internal-access only.",
    )
    parameter_count_b: float = Field(..., gt=0, le=300)
    num_layers: int | None = Field(default=None, gt=0, le=4096)
    precision: ScalePlanPrecision = "bf16"
    available_gpu_memory_gb: int | None = Field(default=None, gt=0, le=2048)
    audit_depth: ScalePlanAuditDepth = "FULL_INTERNAL"
    minimum_worker_count: int | None = Field(default=None, gt=0, le=512)

    @field_validator("model_id")
    @classmethod
    def strip_model_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("model_id is required")
        return stripped


class ScalePlanResponse(BaseModel):
    model_id: str
    weight_access: Literal["open_weight"]
    parameter_count_b: float
    num_layers: int
    scale_tier: ScalePlanTier
    recommended_worker_count: int
    orchestration_pattern: str
    worker_assignments: list[ScalePlanWorkerAssignment]
    memory_estimate: ScalePlanMemoryEstimate
    expected_capability: list[str]
    evidence_requirements: list[str]
    limitations: list[str]


class DistributedWorkerEvidenceResponse(BaseModel):
    worker_id: str
    layer_start: int
    layer_end: int
    shard_id: str
    assigned_methods: list[str]
    expected_outputs: list[str]
    worker_status: Literal["queued", "assigned", "running", "completed", "failed"]
    produced_outputs: list[str]
    missing_outputs: list[str]
    evidence_packet_ref: str | None = None
    error_message: str | None = None
    updated_at: str


class DistributedAuditResponse(BaseModel):
    audit_id: str
    plan_id: str
    status: Literal["PLANNED", "DISPATCHED", "RUNNING", "MERGE_PENDING", "COMPLETE", "FAILED"]
    merge_status: Literal["pending", "partial", "complete", "failed"]
    verdict: Verdict | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_packet_trace_id: str | None = None
    merge_reason: str
    created_at: str
    updated_at: str
    plan: ScalePlanResponse
    worker_evidence: list[DistributedWorkerEvidenceResponse]
    ready_workers: int
    failed_workers: int
    total_workers: int
    missing_outputs: list[str]


class DistributedAuditListResponse(BaseModel):
    audits: list[DistributedAuditResponse]


class DistributedWorkerEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produced_outputs: list[str] = Field(..., min_length=1, max_length=32)
    missing_outputs: list[str] = Field(default_factory=list, max_length=32)
    evidence_packet_ref: str | None = Field(default=None, min_length=1, max_length=240)
    error_message: str | None = Field(default=None, min_length=1, max_length=500)
    worker_status: Literal["completed", "failed"] = "completed"

    @field_validator("produced_outputs", "missing_outputs")
    @classmethod
    def clean_output_list(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            stripped = value.strip() if isinstance(value, str) else ""
            if not stripped:
                raise ValueError("output names must be non-empty strings")
            if len(stripped) > 120:
                raise ValueError("output names must be 120 characters or fewer")
            if stripped not in seen:
                cleaned.append(stripped)
                seen.add(stripped)
        return cleaned

    @field_validator("evidence_packet_ref", "error_message")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_receipt_shape(self) -> "DistributedWorkerEvidenceRequest":
        if self.worker_status == "completed" and not self.evidence_packet_ref:
            raise ValueError("completed worker evidence requires evidence_packet_ref")
        if self.worker_status == "failed" and not self.error_message:
            raise ValueError("failed worker evidence requires error_message")
        return self


class FleetWorkerRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=120)
    model_id: str = Field(..., min_length=1, max_length=200)
    worker_url: str = Field(..., min_length=1, max_length=500)
    gpu_type: str = Field(..., min_length=1, max_length=120)
    capacity: int = Field(default=1, gt=0, le=64)
    supported_methods: list[str] = Field(..., min_length=1, max_length=32)

    @field_validator("worker_id", "model_id", "worker_url", "gpu_type")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field must be non-empty")
        return stripped

    @field_validator("supported_methods")
    @classmethod
    def clean_supported_methods(cls, values: list[str]) -> list[str]:
        return _clean_string_list(values, field_name="supported_methods", max_length=120)


class FleetWorkerResponse(BaseModel):
    worker_id: str
    model_id: str
    worker_url: str
    gpu_type: str
    capacity: int
    supported_methods: list[str]
    registered_at: str
    last_heartbeat_at: str
    status: Literal["active", "stale", "offline"]


class FleetWorkerListResponse(BaseModel):
    workers: list[FleetWorkerResponse]


class FleetJobResponse(BaseModel):
    job_id: str
    audit_id: str
    assigned_worker_id: str
    layer_start: int
    layer_end: int
    shard_id: str
    assigned_methods: list[str]
    expected_outputs: list[str]
    status: Literal["queued", "leased", "completed", "failed", "expired"]
    lease_token: str | None = None
    lease_expires_at: str | None = None
    evidence_packet_fragment_ref: str | None = None
    produced_outputs: list[str]
    missing_outputs: list[str]
    error_message: str | None = None
    updated_at: str


class FleetReadinessResponse(BaseModel):
    status: Literal["blocked", "waiting", "ready"]
    headline: str = Field(..., min_length=1, max_length=240)
    blockers: list[str]
    next_actions: list[str]
    verifier_owned: bool


class FleetRunResponse(BaseModel):
    audit_id: str
    status: Literal["PREPARED", "LEASING", "MERGE_PENDING", "COMPLETE", "FAILED"]
    verifier_gate_status: Literal[
        "not_prepared",
        "waiting_for_workers",
        "waiting_for_receipts",
        "blocked_failed_worker",
        "blocked_missing_outputs",
        "ready_for_verifier",
    ]
    merged_packet_trace_id: str | None = None
    merge_reason: str
    created_at: str
    updated_at: str
    total_jobs: int
    leased_jobs: int
    completed_fragments: int
    failed_jobs: int
    registered_workers: int
    stale_workers: list[str]
    readiness: FleetReadinessResponse
    jobs: list[FleetJobResponse]


class FleetRunListResponse(BaseModel):
    runs: list[FleetRunResponse]


class FleetVerifierDecisionResponse(BaseModel):
    audit_id: str
    merged_packet_trace_id: str
    verdict: Verdict
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str = Field(..., min_length=1, max_length=160)
    reason: str = Field(..., min_length=1, max_length=1000)
    decision_scope: str = Field(..., min_length=1, max_length=160)
    coverage: dict[str, object]
    proof_chip_gate: Literal["passed", "blocked", "unavailable"]
    blockers: list[str]
    next_actions: list[str]
    created_at: str


class FleetLeaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=120)
    lease_seconds: int = Field(default=900, gt=0, le=86_400)

    @field_validator("worker_id")
    @classmethod
    def clean_worker_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("worker_id is required")
        return stripped


class FleetJobReceiptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=120)
    lease_token: str = Field(..., min_length=1, max_length=256)
    produced_outputs: list[str] = Field(default_factory=list, max_length=32)
    missing_outputs: list[str] = Field(default_factory=list, max_length=32)
    evidence_packet_fragment_ref: str | None = Field(default=None, min_length=1, max_length=240)
    error_message: str | None = Field(default=None, min_length=1, max_length=500)
    job_status: Literal["completed", "failed"] = "completed"

    @field_validator("worker_id", "lease_token")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field must be non-empty")
        return stripped

    @field_validator("produced_outputs", "missing_outputs")
    @classmethod
    def clean_outputs(cls, values: list[str]) -> list[str]:
        return _clean_string_list(values, field_name="output", max_length=120)

    @field_validator("evidence_packet_fragment_ref", "error_message")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_receipt_shape(self) -> "FleetJobReceiptRequest":
        if self.job_status == "completed" and not self.evidence_packet_fragment_ref:
            raise ValueError("completed fleet job receipt requires evidence_packet_fragment_ref")
        if self.job_status == "failed" and not self.error_message:
            raise ValueError("failed fleet job receipt requires error_message")
        overlap = set(self.produced_outputs).intersection(self.missing_outputs)
        if overlap:
            raise ValueError(f"produced_outputs and missing_outputs overlap: {', '.join(sorted(overlap))}")
        return self


class FleetStaleWorkerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_heartbeat_age_seconds: int = Field(default=120, gt=0, le=86_400)


@router.post("/target/verify", response_model=ModelTargetVerificationResponse)
async def verify_model_target(
    req: ModelTargetVerificationRequest,
) -> ModelTargetVerificationResponse:
    """Validate a model target without producing or implying an audit verdict."""
    target = req.target
    if target.kind == "demo_reference":
        return _reference_target_response(target)
    return _api_endpoint_target_response(target)


@router.post("/scale-plan", response_model=ScalePlanResponse)
async def create_scale_plan(req: ScalePlanRequest) -> ScalePlanResponse:
    """Return an open-weight distributed CAS Harness plan for 1B-300B models."""
    plan = build_scale_plan(
        PlannerScalePlanRequest(
            model_id=req.model_id,
            parameter_count_b=req.parameter_count_b,
            num_layers=req.num_layers,
            precision=req.precision,
            available_gpu_memory_gb=req.available_gpu_memory_gb,
            audit_depth=req.audit_depth,
            minimum_worker_count=req.minimum_worker_count,
        )
    )
    return ScalePlanResponse.model_validate(plan.to_dict())


@router.post("/distributed/session", response_model=DistributedAuditResponse)
async def create_distributed_audit_session(req: ScalePlanRequest) -> DistributedAuditResponse:
    """Create a real distributed audit control-plane run from an open-weight plan."""
    record = create_distributed_audit(
        PlannerScalePlanRequest(
            model_id=req.model_id,
            parameter_count_b=req.parameter_count_b,
            num_layers=req.num_layers,
            precision=req.precision,
            available_gpu_memory_gb=req.available_gpu_memory_gb,
            audit_depth=req.audit_depth,
            minimum_worker_count=req.minimum_worker_count,
        )
    )
    return DistributedAuditResponse.model_validate(record.to_dict())


@router.post("/distributed/session/{audit_id}/dispatch", response_model=DistributedAuditResponse)
async def dispatch_distributed_audit_session(audit_id: str) -> DistributedAuditResponse:
    """Mark planned Probe Worker assignments as dispatched."""
    record = dispatch_distributed_audit(audit_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Distributed audit session not found")
    return DistributedAuditResponse.model_validate(record.to_dict())


@router.post(
    "/distributed/session/{audit_id}/worker/{worker_id}/running",
    response_model=DistributedAuditResponse,
)
async def mark_distributed_worker_running(audit_id: str, worker_id: str) -> DistributedAuditResponse:
    """Mark one Probe Worker as running."""
    try:
        record = mark_worker_running(audit_id, worker_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Distributed worker assignment not found")
    except DistributedAuditStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if record is None:
        raise HTTPException(status_code=404, detail="Distributed audit session not found")
    return DistributedAuditResponse.model_validate(record.to_dict())


@router.post(
    "/distributed/session/{audit_id}/worker/{worker_id}/evidence",
    response_model=DistributedAuditResponse,
)
async def submit_distributed_worker_evidence(
    audit_id: str,
    worker_id: str,
    req: DistributedWorkerEvidenceRequest,
) -> DistributedAuditResponse:
    """Attach one Probe Worker's evidence receipt to the distributed audit."""
    if get_fleet_run(audit_id) is not None:
        raise HTTPException(
            status_code=409,
            detail="Fleet-backed distributed audits require leased fleet job receipts.",
        )
    try:
        record = record_worker_evidence(
            audit_id,
            worker_id,
            produced_outputs=req.produced_outputs,
            missing_outputs=req.missing_outputs,
            evidence_packet_ref=req.evidence_packet_ref,
            error_message=req.error_message,
            worker_status=req.worker_status,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Distributed worker assignment not found")
    except DistributedAuditStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if record is None:
        raise HTTPException(status_code=404, detail="Distributed audit session not found")
    return DistributedAuditResponse.model_validate(record.to_dict())


@router.post("/distributed/session/{audit_id}/merge", response_model=DistributedAuditResponse)
async def merge_distributed_audit_session(audit_id: str) -> DistributedAuditResponse:
    """Merge worker evidence receipts without fabricating ACCEPT."""
    try:
        record = merge_distributed_audit(audit_id)
    except DistributedAuditStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if record is None:
        raise HTTPException(status_code=404, detail="Distributed audit session not found")
    return DistributedAuditResponse.model_validate(record.to_dict())


@router.get("/distributed/session/{audit_id}", response_model=DistributedAuditResponse)
async def get_distributed_audit_session(audit_id: str) -> DistributedAuditResponse:
    """Return distributed audit worker and merge state."""
    record = get_distributed_audit(audit_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Distributed audit session not found")
    return DistributedAuditResponse.model_validate(record.to_dict())


@router.get("/distributed/sessions", response_model=DistributedAuditListResponse)
async def list_distributed_audit_sessions() -> DistributedAuditListResponse:
    """List distributed audit runs held by this API process."""
    return DistributedAuditListResponse(
        audits=[
            DistributedAuditResponse.model_validate(record.to_dict())
            for record in list_distributed_audits()
        ]
    )


@router.post("/distributed/fleet/worker/register", response_model=FleetWorkerResponse)
async def register_fleet_worker(req: FleetWorkerRegistrationRequest) -> FleetWorkerResponse:
    """Register one Probe Worker that can receive distributed audit jobs."""
    try:
        worker = register_worker(
            worker_id=req.worker_id,
            model_id=req.model_id,
            worker_url=req.worker_url,
            gpu_type=req.gpu_type,
            capacity=req.capacity,
            supported_methods=req.supported_methods,
        )
    except FleetExecutorStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return FleetWorkerResponse.model_validate(worker.to_dict())


@router.post("/distributed/fleet/worker/{worker_id}/heartbeat", response_model=FleetWorkerResponse)
async def heartbeat_fleet_worker(worker_id: str) -> FleetWorkerResponse:
    """Refresh one Probe Worker's heartbeat."""
    worker = heartbeat_worker(worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Fleet worker not found")
    return FleetWorkerResponse.model_validate(worker.to_dict())


@router.post("/distributed/fleet/workers/stale-scan", response_model=FleetWorkerListResponse)
async def scan_stale_fleet_workers(req: FleetStaleWorkerRequest) -> FleetWorkerListResponse:
    """Mark stale Probe Workers using the requested heartbeat age threshold."""
    try:
        workers = mark_stale_workers(max_heartbeat_age_seconds=req.max_heartbeat_age_seconds)
    except FleetExecutorStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return FleetWorkerListResponse(
        workers=[FleetWorkerResponse.model_validate(worker.to_dict()) for worker in workers]
    )


@router.get("/distributed/fleet/workers", response_model=FleetWorkerListResponse)
async def list_fleet_workers() -> FleetWorkerListResponse:
    """List registered Probe Workers."""
    return FleetWorkerListResponse(
        workers=[FleetWorkerResponse.model_validate(worker.to_dict()) for worker in list_workers()]
    )


@router.post("/distributed/session/{audit_id}/fleet/prepare", response_model=FleetRunResponse)
async def prepare_distributed_fleet_run(audit_id: str) -> FleetRunResponse:
    """Create fleet jobs from a dispatched distributed audit run."""
    try:
        run = prepare_fleet_for_audit(audit_id)
    except FleetExecutorStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if run is None:
        raise HTTPException(status_code=404, detail="Distributed audit session not found")
    return FleetRunResponse.model_validate(run.to_dict())


@router.post("/distributed/session/{audit_id}/fleet/job/lease", response_model=FleetJobResponse | None)
async def lease_distributed_fleet_job(
    audit_id: str,
    req: FleetLeaseRequest,
) -> FleetJobResponse | None:
    """Lease the next queued fleet job assigned to a registered Probe Worker."""
    try:
        job = lease_next_job(
            audit_id=audit_id,
            worker_id=req.worker_id,
            lease_seconds=req.lease_seconds,
        )
    except FleetExecutorStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if job is None:
        if get_fleet_run(audit_id) is None:
            raise HTTPException(status_code=404, detail="Fleet run not found")
        return None
    return FleetJobResponse.model_validate(job.to_dict(include_lease_token=True))


@router.post("/distributed/session/{audit_id}/fleet/job/{job_id}/receipt", response_model=FleetRunResponse)
async def submit_distributed_fleet_job_receipt(
    audit_id: str,
    job_id: str,
    req: FleetJobReceiptRequest,
) -> FleetRunResponse:
    """Submit one worker Evidence Packet fragment receipt for a leased job."""
    try:
        run = submit_job_receipt(
            audit_id=audit_id,
            job_id=job_id,
            worker_id=req.worker_id,
            lease_token=req.lease_token,
            produced_outputs=req.produced_outputs,
            missing_outputs=req.missing_outputs,
            evidence_packet_fragment_ref=req.evidence_packet_fragment_ref,
            error_message=req.error_message,
            job_status=req.job_status,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Fleet job not found")
    except (FleetExecutorStateError, DistributedAuditStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if run is None:
        raise HTTPException(status_code=404, detail="Fleet run not found")
    return FleetRunResponse.model_validate(run.to_dict())


@router.post("/distributed/session/{audit_id}/fleet/merge", response_model=FleetRunResponse)
async def merge_distributed_fleet_run(audit_id: str) -> FleetRunResponse:
    """Merge fleet Evidence Packet fragments only after all receipts arrive."""
    try:
        run = merge_fleet_evidence(audit_id)
    except (FleetExecutorStateError, DistributedAuditStateError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if run is None:
        raise HTTPException(status_code=404, detail="Fleet run not found")
    return FleetRunResponse.model_validate(run.to_dict())


@router.post(
    "/distributed/session/{audit_id}/fleet/verifier",
    response_model=FleetVerifierDecisionResponse,
)
async def verify_distributed_fleet_packet(audit_id: str) -> FleetVerifierDecisionResponse:
    """Run the verifier-owned decision gate over a merged fleet packet."""
    packet_decision = None
    packet_load_error = None
    run = get_fleet_run(audit_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Fleet run not found")
    if not run.merged_packet_trace_id:
        raise HTTPException(status_code=409, detail="Merge fleet evidence before verifier review.")

    try:
        packet_payload = _packet_payload_for_trace(run.merged_packet_trace_id)
    except FileNotFoundError as exc:
        packet_load_error = str(exc)
    else:
        packet_decision = verifier_decision_from_packet(packet_payload)

    try:
        decision = verify_merged_fleet_packet(
            audit_id,
            explicit_packet_decision=packet_decision,
            packet_load_error=packet_load_error,
        )
    except FleetVerifierStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if decision is None:
        raise HTTPException(status_code=404, detail="Fleet run not found")
    return FleetVerifierDecisionResponse.model_validate(decision.to_dict())


@router.get("/distributed/session/{audit_id}/fleet", response_model=FleetRunResponse)
async def get_distributed_fleet_run(audit_id: str) -> FleetRunResponse:
    """Return fleet executor state for one distributed audit."""
    run = get_fleet_run(audit_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Fleet run not found")
    return FleetRunResponse.model_validate(run.to_dict())


@router.get("/distributed/fleet/runs", response_model=FleetRunListResponse)
async def list_distributed_fleet_runs() -> FleetRunListResponse:
    """List fleet executor runs held by this API process."""
    return FleetRunListResponse(
        runs=[FleetRunResponse.model_validate(run.to_dict()) for run in list_fleet_runs()]
    )


@router.post("/session", response_model=AuditSessionResponse)
async def create_audit_session(req: AuditSessionRequest) -> AuditSessionResponse:
    """Validate the CAS Harness audit contract and create a stored M1 session."""
    payload = req.model_dump(mode="json")
    if req.evidence_packet_trace_id:
        payload.update(_audit_evidence_for_trace(req.evidence_packet_trace_id))
    return AuditSessionResponse.model_validate(create_session(payload).to_dict())


@router.get("/session/{audit_id}/status", response_model=AuditSessionResponse)
async def get_audit_session_status(audit_id: str) -> AuditSessionResponse:
    """Return the stored session state instead of fabricating by audit id."""
    record = get_session(audit_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Audit session not found")
    return AuditSessionResponse.model_validate(record.to_dict())


@router.post("/session/{audit_id}/run", response_model=AuditSessionResponse)
async def run_audit_session(audit_id: str) -> AuditSessionResponse:
    """Advance the M1 lifecycle without fabricating a final CAS verdict."""
    record = run_session(audit_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Audit session not found")
    return AuditSessionResponse.model_validate(record.to_dict())


@router.get("/sessions", response_model=AuditSessionListResponse)
async def list_audit_sessions() -> AuditSessionListResponse:
    """List in-process M1 audit sessions for the current API process."""
    sessions = [AuditSessionResponse.model_validate(record.to_dict()) for record in list_sessions()]
    return AuditSessionListResponse(sessions=sessions)


def _audit_evidence_for_trace(trace_id: str) -> dict[str, object]:
    try:
        packet_payload = _packet_payload_for_trace(trace_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence Packet trace_id not found: {trace_id}",
        )

    bridge = normalize_evidence_packet_for_audit(packet_payload)
    payload: dict[str, object] = {
        "provenance_chips": [chip.to_dict() for chip in bridge.chips],
    }
    verifier_decision = verifier_decision_from_packet(packet_payload)
    if verifier_decision is not None:
        payload["verifier_decision"] = verifier_decision.to_dict()
    return payload


def _packet_payload_for_trace(trace_id: str) -> dict[str, object]:
    try:
        packet = build_packet_for_trace(trace_id)
        return packet.model_dump(mode="json")
    except FileNotFoundError:
        try:
            return load_stage9_40e_packet_payload_for_trace(trace_id)
        except FileNotFoundError:
            raise FileNotFoundError(trace_id)


def _reference_target_response(target: ModelTargetConfig) -> ModelTargetVerificationResponse:
    verified = VerifiedModelTarget(
        kind="demo_reference",
        provider=REFERENCE_TARGET_PROVIDER,
        model_id=REFERENCE_TARGET_MODEL_ID,
        endpoint_url=None,
        credential_mode="none",
        timeout_ms=target.timeout_ms,
    )
    return ModelTargetVerificationResponse(
        connection_id=_connection_id_for(verified),
        connection_state="CONNECTED",
        model_status="CONNECTED",
        can_run_audit=True,
        target=verified,
        detail=(
            "CAS Harness reference target verified locally. No external model call, "
            "credential, or audit verdict was created. A bundled reference "
            "Evidence Packet is available for the beta run step."
        ),
        checked_at=_utc_now(),
        provenance_chip=ProvenanceChip(
            id="model_proof",
            name="Model proof",
            status="verified",
            detail=(
                f"Reference target {REFERENCE_TARGET_MODEL_ID} is available for "
                "non-secret Audit Console demos. This is target verification only."
            ),
        ),
        reference_evidence_packet_trace_id=REFERENCE_TARGET_EVIDENCE_PACKET_TRACE_ID,
    )


def _api_endpoint_target_response(target: ModelTargetConfig) -> ModelTargetVerificationResponse:
    verified = VerifiedModelTarget(
        kind="api_endpoint",
        provider=target.provider or "custom_api",
        model_id=target.model_id or "",
        endpoint_url=str(target.endpoint_url) if target.endpoint_url else None,
        credential_mode=_credential_mode_for(target),
        timeout_ms=target.timeout_ms,
    )
    return ModelTargetVerificationResponse(
        connection_id=_connection_id_for(verified),
        connection_state="CONFIGURED",
        model_status="READY",
        can_run_audit=True,
        target=verified,
        detail=(
            "Model target configuration is valid for CAS Harness beta. The backend "
            "did not call the model and did not compute a verdict or confidence."
        ),
        checked_at=_utc_now(),
        provenance_chip=ProvenanceChip(
            id="model_proof",
            name="Model proof",
            status="present",
            detail=(
                "Endpoint target configuration passed schema validation. Live model "
                "probing and Evidence Packet generation are separate audit-runner steps."
            ),
        ),
    )


def _credential_mode_for(target: ModelTargetConfig) -> CredentialMode:
    if target.credential_ref is not None:
        return "credential_ref"
    if target.api_key is not None:
        return "ephemeral_secret"
    return "none"


def _clean_string_list(values: list[str], *, field_name: str, max_length: int) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip() if isinstance(value, str) else ""
        if not stripped:
            raise ValueError(f"{field_name} entries must be non-empty strings")
        if len(stripped) > max_length:
            raise ValueError(f"{field_name} entries must be {max_length} characters or fewer")
        if stripped not in seen:
            cleaned.append(stripped)
            seen.add(stripped)
    return cleaned


def _connection_id_for(target: VerifiedModelTarget) -> str:
    payload = target.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"cas-target-{digest[:16]}"


def _is_allowed_endpoint_url(endpoint_url: str) -> bool:
    parsed = urlparse(endpoint_url)
    if parsed.scheme == "https":
        return True
    if parsed.scheme != "http":
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname in _LOCAL_HTTP_HOSTS or hostname.endswith(".localhost")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
