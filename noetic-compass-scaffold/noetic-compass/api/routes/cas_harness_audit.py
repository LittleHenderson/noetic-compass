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

from api.routes.evidence import build_packet_for_trace
from api.services.cas_harness_audit_sessions import (
    create_session,
    get_session,
    list_sessions,
    run_session,
)
from api.services.cas_harness_distributed_audits import (
    create_distributed_audit,
    dispatch_distributed_audit,
    get_distributed_audit,
    list_distributed_audits,
    mark_worker_running,
    merge_distributed_audit,
    record_worker_evidence,
)
from api.services.cas_harness_evidence_bridge import normalize_evidence_packet_for_audit
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
    if record is None:
        raise HTTPException(status_code=404, detail="Distributed audit session not found")
    return DistributedAuditResponse.model_validate(record.to_dict())


@router.post("/distributed/session/{audit_id}/merge", response_model=DistributedAuditResponse)
async def merge_distributed_audit_session(audit_id: str) -> DistributedAuditResponse:
    """Merge worker evidence receipts without fabricating ACCEPT."""
    record = merge_distributed_audit(audit_id)
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
        packet = build_packet_for_trace(trace_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Evidence Packet trace_id not found: {trace_id}")

    packet_payload = packet.model_dump(mode="json")
    bridge = normalize_evidence_packet_for_audit(packet_payload)
    payload: dict[str, object] = {
        "provenance_chips": [chip.to_dict() for chip in bridge.chips],
    }
    verifier_decision = verifier_decision_from_packet(packet_payload)
    if verifier_decision is not None:
        payload["verifier_decision"] = verifier_decision.to_dict()
    return payload


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
