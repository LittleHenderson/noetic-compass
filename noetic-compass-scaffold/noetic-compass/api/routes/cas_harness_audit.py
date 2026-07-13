"""CAS Harness audit API scaffold.

This route owns the M1 audit-session lifecycle contract. It stores sessions
in-process and advances state honestly, but it does not fabricate CAS verdicts
until a real audit runner is wired behind it.
"""

from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
import hashlib
import json
import logging
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, field_validator, model_validator

from api.config import settings

from api.routes.evidence import (
    _verify_packet_hashes,
    build_packet_for_trace,
    load_stage9_40e_packet_payload_for_trace,
)
from api.services.cas_harness_audit_sessions import (
    AuditRunInProgress,
    claim_run_attempt,
    attach_runner_evidence,
    create_session,
    fail_session,
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
from api.services.cas_harness_evidence_object_store import (
    EvidenceObjectStoreError,
    evidence_packet_storage_scope,
)
from api.services.evidence_ownership import (
    record_evidence_ownership,
    tenant_owns_trace,
)
from api.services.cas_harness_architecture_adapter import (
    ModelArchitectureDeclaration as ServiceModelArchitectureDeclaration,
)
from api.services.quotas import (
    QuotaExceeded,
    consume_audit_quota,
    current_monthly_period_key,
    get_quota_limit,
)
from api.services.cas_harness_probe_compatibility import (
    ProbeReadoutSpecification as ServiceProbeReadoutSpecification,
)
from api.services.cas_harness_compute_feasibility import (
    ComputeEnvelopeDeclaration as ServiceComputeEnvelopeDeclaration,
)
from api.services.cas_harness_model_access import (
    ModelAccessMode as ServiceModelAccessMode,
)
from api.services.cas_harness_model_provenance import (
    ModelProvenanceManifest as ServiceModelProvenanceManifest,
    WeightFileRef as ServiceWeightFileRef,
)
from api.services.cas_harness_static_evidence_anchor import (
    load_anchored_static_packet_payload,
    verify_anchored_static_packet,
)
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
from api.services.cas_harness_api_endpoint_runner import (
    API_ENDPOINT_PROVIDERS,
    ApiEndpointRunnerUnavailable,
    run_api_endpoint_audit,
)
from api.services.cas_harness_live_worker_runner import (
    HOSTED_OPEN_WEIGHT_MODEL_IDS,
    LiveAuditRunnerUnavailable,
    run_live_worker_audit,
)
from api.services.cas_harness_scale_planner import (
    ScalePlanRequest as PlannerScalePlanRequest,
    build_scale_plan,
)
from api.services.cas_harness_tks_definition_lock import (
    LOCKED_TKS_DEFINITION_SHA256,
    TKSDefinitionLockError,
    assert_tks_definition_lock_for_audit,
)
from api.services.cas_harness_verifier_decision_adapter import verifier_decision_from_packet


router = APIRouter(prefix="/api/cas-harness/audit", tags=["cas_harness_audit"])

logger = logging.getLogger(__name__)

AuditMode = Literal["BALANCED", "HIGH_PRECISION", "MAX_COVERAGE_TRIAGE"]
ScalePlanPrecision = Literal["fp16", "bf16", "int8", "int4"]
ScalePlanAuditDepth = Literal["FULL_INTERNAL", "LAYER_SAMPLE"]
ScalePlanTier = Literal[
    "single_worker_open_weight",
    "small_distributed_open_weight",
    "distributed_open_weight",
    "enterprise_distributed_open_weight",
    "frontier_experimental_open_weight",
]
ScalePlanValidationStatus = Literal[
    "EMPIRICALLY_VALIDATED",
    "ENGINEERED_NOT_VALIDATED",
    "EXPERIMENTAL_NOT_VALIDATED",
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

REFERENCE_TARGET_MODEL_ID = "EleutherAI/gpt-neox-20b"
REFERENCE_TARGET_PROVIDER = "cas_harness_reference"
REFERENCE_TARGET_EVIDENCE_PACKET_TRACE_ID = "stage9-40e-original-baseline-readout-20260527"
_LOCAL_HTTP_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _require_locked_tks_definitions() -> None:
    try:
        assert_tks_definition_lock_for_audit()
    except TKSDefinitionLockError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"TKS definition lock failed; audit creation is refused: {exc}",
        ) from exc


def _caller_identity(request: Request) -> tuple[str | None, str | None]:
    """Resolve the requesting identity (``sub``, ``api_key``) for tenant scoping.

    Phase-1 identity-scope stopgap. Owner identity is whatever the caller
    actually presents:

    1. If the JWT auth middleware already attached identity to ``request.state``
       (it does for protected paths), use that. This keeps the scoping correct
       for free if these audit-session routes are later moved off the public
       allowlist and behind the middleware.
    2. Otherwise — these session routes are currently on the auth middleware's
       PUBLIC_PATH allowlist, so it never decodes their token — best-effort
       decode the ``Authorization: Bearer`` JWT here using the same secret and
       algorithm. A missing / malformed / expired token is non-fatal and simply
       yields no identity.

    Fails CLOSED: when no usable identity can be resolved, returns ``(None,
    None)`` and the store collapses that to the anonymous-owned bucket, so the
    caller can never list or fetch another (identified) caller's sessions.

    Upgrades to a real ``tenant_id`` lookup when the account/tenant model lands.
    """
    state = request.state
    state_sub = getattr(state, "user", None)
    state_api_key = getattr(state, "api_key", None)
    if state_sub is not None or state_api_key is not None:
        return state_sub, state_api_key

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None
    token = auth_header[7:]
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        # Unverifiable token → no identity. Fail closed; never raise here, the
        # session routes stay reachable but the caller is treated as anonymous.
        return None, None
    return payload.get("sub"), payload.get("api_key")

def _audit_storage_scope(request: Request) -> dict[str, str]:
    """Route kwargs selecting durable tenant+account storage only in account mode."""
    if not settings.accounts_enabled:
        return {}
    tenant_id = str(getattr(request.state, "tenant_id", "") or "")
    account_id = str(getattr(request.state, "account_id", "") or "")
    if not tenant_id or not account_id:
        raise HTTPException(status_code=503, detail="Audit persistence identity is unavailable.")
    if _audit_evidence_state_store(request) is None:
        raise HTTPException(status_code=503, detail="Audit persistence is unavailable.")
    return {"tenant_id": tenant_id, "account_id": account_id}



def _audit_evidence_state_store(request: Request):
    """Return the durable ``StateStore`` the evidence-ownership ledger lives in, or ``None``.

    Resolved EXACTLY as ``api/routes/evidence.py``'s ``_evidence_state_store`` does: off
    ``request.app.state.state_ledger.store`` (a ``StateLedgerHandle`` stashed at startup; see
    ``api/state_ledger_bootstrap.py`` and ``api/main.py`` lifespan). Both getattrs are defensive so a
    TestClient that never ran the lifespan, or a deployment with the ledger dark, yields ``None``
    rather than raising. The caller decides what ``None`` means; here a missing store simply skips the
    ownership write (it never breaks an audit run).
    """
    shared = getattr(request.app.state, "shared_state_store", None)
    if shared is not None:
        return shared
    handle = getattr(request.app.state, "state_ledger", None)
    return getattr(handle, "store", None) if handle is not None else None


def _audit_evidence_storage_context(request: Request):
    """Carry server-derived tenant identity through packet/hash-log I/O."""
    if not settings.evidence_packet_object_store_enabled:
        return nullcontext()
    tenant_id = str(getattr(request.state, "tenant_id", "") or "")
    account_id = str(getattr(request.state, "account_id", "") or "")
    if not settings.accounts_enabled or not tenant_id or not account_id:
        raise HTTPException(
            status_code=503, detail="Shared Evidence Packet identity is unavailable."
        )
    return evidence_packet_storage_scope(
        tenant_id=tenant_id,
        account_id=account_id,
    )


def _record_audit_evidence_ownership(request: Request, trace_id: str | None) -> None:
    """Persist ownership in account mode; never report a successful run without it."""
    if not settings.accounts_enabled:
        return
    tenant_id = str(getattr(request.state, "tenant_id", "") or "")
    account_id = str(getattr(request.state, "account_id", "") or "")
    store = _audit_evidence_state_store(request)
    if not tenant_id or not account_id or store is None or not trace_id:
        raise HTTPException(
            status_code=503, detail="Evidence ownership persistence is unavailable."
        )
    try:
        record_evidence_ownership(
            store, tenant_id=tenant_id, account_id=account_id, trace_id=trace_id
        )
    except Exception as exc:
        logger.error("evidence ownership write failed", exc_info=True)
        raise HTTPException(
            status_code=503, detail="Evidence ownership persistence failed."
        ) from exc


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


class AuditScope(BaseModel):
    """Plain-language statement of how much access an audit actually had.

    Surfaced so the UI never implies internal inspection the audit did not do.
    """

    kind: str = Field(..., min_length=1, max_length=80)
    label: str = Field(..., min_length=1, max_length=240)
    internal_activation_access: bool
    verdict_disposition: str = Field(..., min_length=1, max_length=80)
    detail: str | None = Field(default=None, min_length=1, max_length=1000)


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
    provider: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Closed-API provider (openai, anthropic, google, ...) for customer-API audit runs.",
    )
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

    @field_validator(
        "model_id", "provider", "prompt", "scenario_text", "evidence_packet_trace_id", "license_key"
    )
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


class RunAuditSessionRequest(BaseModel):
    """Optional run-time body for POST /session/{audit_id}/run.

    Carries the customer bring-your-own-key (BYOK) ephemeral secret. It is
    supplied per-run, used for that single connector call, and never persisted:
    it is not stored on the session record, the Evidence Packet, or the harvest.
    Sessions created without a server-side key can still run by supplying the
    key here at run time.
    """

    model_config = ConfigDict(extra="forbid")

    api_key: SecretStr | None = Field(
        default=None,
        min_length=1,
        max_length=4096,
        description="One-request customer API key; used only for this run and never persisted.",
    )

    @field_validator("api_key")
    @classmethod
    def strip_optional_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        return value if value.get_secret_value().strip() else None


class AuditSessionResponse(BaseModel):
    audit_id: str
    status: AuditStatus
    model_status: ModelStatus
    model_id: str | None
    endpoint_url: str | None
    provider: str | None = None
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
    audit_scope: AuditScope | None = None
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


class ModelProvenanceWeightFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., min_length=1, max_length=512)
    sha256: str = Field(..., min_length=1, max_length=256)
    size_bytes: int | None = Field(default=None, ge=0)


class ModelProvenanceManifestRequest(BaseModel):
    """Caller-supplied model provenance/license/weight-hash manifest.

    Required to create a real frontier-scale (300B-4T) distributed run. The gate
    refuses the run with HTTP 422 if this is missing, the model_id does not match
    the requested model, the license is not a recognized open-weight license, or a
    declared SHA-256 is malformed. Weight-hash *recompute* happens worker-side; at
    create time a well-formed manifest is recorded as DECLARED_NOT_VERIFIED.
    """

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(..., min_length=1, max_length=200)
    source_uri: str = Field(..., min_length=1, max_length=1024)
    license_id: str = Field(..., min_length=1, max_length=128)
    weight_files: list[ModelProvenanceWeightFileRequest] = Field(
        ..., min_length=1, max_length=4096
    )
    revision: str | None = Field(default=None, max_length=200)
    total_size_bytes: int | None = Field(default=None, ge=0)
    publisher: str | None = Field(default=None, max_length=200)
    signed_by: str | None = Field(default=None, max_length=200)

    def to_service_manifest(self) -> ServiceModelProvenanceManifest:
        return ServiceModelProvenanceManifest(
            model_id=self.model_id,
            source_uri=self.source_uri,
            license_id=self.license_id,
            weight_files=tuple(
                ServiceWeightFileRef(path=f.path, sha256=f.sha256, size_bytes=f.size_bytes)
                for f in self.weight_files
            ),
            revision=self.revision,
            total_size_bytes=self.total_size_bytes,
            publisher=self.publisher,
            signed_by=self.signed_by,
        )


class ModelArchitectureDeclarationRequest(BaseModel):
    """Caller-supplied model architecture declaration (frontier run-gate 6).

    Required to create a real frontier-scale (300B-4T) distributed run. The gate
    refuses the run with HTTP 422 if this is missing or its ``model_type`` (or an
    inferred architecture class) does not resolve to a probe adapter CAS Harness
    can mechanically hook -- the probe worker can only locate decoder stacks at
    ``gpt_neox.layers`` / ``model.layers`` / ``transformer.h`` / ``transformer.blocks``.
    The real model layout is confirmed worker-side at load time, so at create time
    a supported declaration is recorded as ARCHITECTURE_ADAPTER_AVAILABLE.
    """

    model_config = ConfigDict(extra="forbid")

    model_type: str | None = Field(default=None, max_length=128)
    architectures: list[str] = Field(default_factory=list, max_length=16)
    num_hidden_layers: int | None = Field(default=None, gt=0, le=4096)
    hidden_size: int | None = Field(default=None, gt=0, le=1_048_576)
    num_attention_heads: int | None = Field(default=None, gt=0, le=8192)

    def to_service_declaration(self) -> ServiceModelArchitectureDeclaration:
        return ServiceModelArchitectureDeclaration(
            model_type=self.model_type,
            architectures=tuple(self.architectures),
            num_hidden_layers=self.num_hidden_layers,
            hidden_size=self.hidden_size,
            num_attention_heads=self.num_attention_heads,
        )


class ProbeReadoutSpecificationRequest(BaseModel):
    """Caller-supplied CAS probe-readout specification (frontier run-gate 7).

    Required to create a real frontier-scale (300B-4T) distributed run. The CAS axis
    readout is the run's central deliverable -- every shard declares it in
    ``expected_outputs`` -- and the probe worker can only produce it from a probe whose
    ``schema_version`` is ``'cas_probe_linear_v1'``, with a non-empty ``axes`` set and
    per-axis vectors of length ``feature_dimension``. The gate refuses the run with HTTP
    422 if this is missing or malformed: a missing probe makes the CAS readout come back
    *missing* (dishonest by omission) and a malformed one aborts the shard. The probe is
    actually loaded and run worker-side, so at create time a loadable spec is recorded as
    PROBE_COMPATIBILITY_DECLARED. ``expected_pooled_features`` is optional: supply it (the
    run's ``scenarios x assigned-layers x top_k``) to run the worker's exact dimensional
    check now instead of letting a shard abort. ``definition_sha256`` is mandatory for
    platform audits: it must equal the locked owner-provided TKS definitions hash.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., min_length=1, max_length=128)
    axes: list[str] = Field(default_factory=list, max_length=256)
    feature_dimension: int | None = Field(default=None, gt=0, le=8_388_608)
    probe_id: str | None = Field(default=None, max_length=200)
    weights_sha256: str | None = Field(default=None, min_length=1, max_length=128)
    definition_sha256: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description=(
            "SHA-256 of the TKS definition source used to train/evaluate this probe. "
            f"Must equal {LOCKED_TKS_DEFINITION_SHA256}; alternate definitions are refused."
        ),
    )
    expected_pooled_features: int | None = Field(default=None, gt=0, le=8_388_608)

    def to_service_specification(self) -> ServiceProbeReadoutSpecification:
        return ServiceProbeReadoutSpecification(
            schema_version=self.schema_version,
            axes=tuple(self.axes),
            feature_dimension=self.feature_dimension,
            probe_id=self.probe_id,
            weights_sha256=self.weights_sha256,
            definition_sha256=self.definition_sha256,
            expected_pooled_features=self.expected_pooled_features,
        )


class ComputeEnvelopeDeclarationRequest(BaseModel):
    """Caller-supplied compute envelope (frontier run-gate 3).

    Required to create a real frontier-scale (300B-4T) distributed run. The planner
    provisions only a fraction of each accelerator's memory and silently clamps the
    probe-worker fan-out, so a frontier model can be handed a plan that *looks*
    schedulable while every shard is asked to hold more than one accelerator can fit.
    The gate refuses the run with HTTP 422 unless the declared fleet -- accelerator
    count (capped at the planner's fan-out) times per-accelerator memory times the
    usable fraction -- can cover the plan's estimated runtime memory. The real
    resident-set fit is confirmed fleet-side, so at create time a sufficient envelope
    is recorded as COMPUTE_FEASIBILITY_DECLARED. ``accelerator_type`` is a free-form
    label carried for traceability only; the gate never infers memory from the name.
    """

    model_config = ConfigDict(extra="forbid")

    accelerator_count: int = Field(..., gt=0, le=1_000_000)
    accelerator_memory_gb: float = Field(..., gt=0, le=8192)
    accelerator_type: str | None = Field(default=None, max_length=128)

    def to_service_declaration(self) -> ServiceComputeEnvelopeDeclaration:
        return ServiceComputeEnvelopeDeclaration(
            accelerator_count=self.accelerator_count,
            accelerator_memory_gb=self.accelerator_memory_gb,
            accelerator_type=self.accelerator_type,
        )


class ScalePlanRequest(BaseModel):
    """Open-weight enterprise planning request.

    This endpoint creates a deployment plan only. It does not claim a verdict,
    run a customer model, or offer black-box/API-only auditing.
    """

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(..., min_length=1, max_length=200)
    weight_access: ServiceModelAccessMode = Field(
        default="open_weight",
        description=(
            "Model access modality. The distributed CAS Harness audit is a mechanistic probe: "
            "it hooks the model's decoder layers and pools hidden-state activations to compute "
            "the CAS axis readout, so it requires open-weight (locally loadable) access. A "
            "hosted_api / black_box / output_only target exposes no hidden states, so it is "
            "refused with HTTP 422 and an explanation pointing at the behavioral target/verify "
            "path. Universal run-gate (2): enforced at every size, not just the frontier, "
            "because mechanistic reachability is a precondition of the method itself."
        ),
    )
    parameter_count_b: float = Field(..., gt=0, le=4000)
    num_layers: int | None = Field(default=None, gt=0, le=4096)
    precision: ScalePlanPrecision = "bf16"
    available_gpu_memory_gb: int | None = Field(default=None, gt=0, le=2048)
    audit_depth: ScalePlanAuditDepth = "FULL_INTERNAL"
    minimum_worker_count: int | None = Field(default=None, gt=0, le=512)
    accept_experimental_frontier: bool = Field(
        default=False,
        description=(
            "Required to plan a 300B-4T frontier-scale model. Those runs are "
            "EXPERIMENTAL_NOT_VALIDATED: architected frontier-lane support only, offered "
            "at customer risk with no warranty of correctness or completeness. Without "
            "this acknowledgement a >300B request is refused with HTTP 422. This flag only "
            "unlocks the request path; it does not by itself guarantee compute, adapter, "
            "probe, provenance, or data-handling readiness for the run."
        ),
    )
    accept_frontier_compute_cost: bool = Field(
        default=False,
        description=(
            "Required to CREATE a real frontier-scale (300B-4T) distributed run via "
            "/distributed/session. A frontier run commits the plan's recommended worker "
            "fleet to hold a model of this size for a duration CAS Harness does NOT "
            "estimate, at a dollar cost it does NOT quote, bill, meter, or cap -- the "
            "compute is entirely the caller's, for a result already labelled "
            "EXPERIMENTAL_NOT_VALIDATED. This acknowledges that caller-owned, unquoted "
            "cost; CAS Harness never invents a price. Ignored by the planning-only "
            "/scale-plan endpoint. Frontier run-gate (4)."
        ),
    )
    accept_audit_data_capture: bool = Field(
        default=False,
        description=(
            "Required to CREATE *any* real distributed run via /distributed/session, "
            "frontier or not. Every distributed audit captures the target model's "
            "inputs/outputs, the pooled hidden-state activations the probe hooks, the CAS "
            "axis readout each shard emits, and the verdict, and commits them to an "
            "immutable write-once store reused as CAS-Native training signal. This "
            "acknowledges that capture, indefinite WORM retention, and reuse. It is "
            "universal (not frontier-only): the harvest is intrinsic to the method and "
            "does not scale with model size, so a 20B run requires it exactly as a 1T one. "
            "Ignored by the planning-only /scale-plan endpoint, which captures nothing. "
            "Run-gate (8)."
        ),
    )
    provenance: ModelProvenanceManifestRequest | None = Field(
        default=None,
        description=(
            "Model provenance/license/weight-hash manifest. Required to CREATE a real "
            "frontier-scale (300B-4T) distributed run via /distributed/session; ignored by "
            "the planning-only /scale-plan endpoint. Frontier run-gate (5)."
        ),
    )
    architecture: ModelArchitectureDeclarationRequest | None = Field(
        default=None,
        description=(
            "Model architecture declaration (model_type / architectures / dims). Required "
            "to CREATE a real frontier-scale (300B-4T) distributed run via "
            "/distributed/session -- the run is refused unless the architecture resolves to "
            "a probe adapter the worker can mechanically hook. Ignored by the planning-only "
            "/scale-plan endpoint. Frontier run-gate (6)."
        ),
    )
    probe: ProbeReadoutSpecificationRequest | None = Field(
        default=None,
        description=(
            "CAS probe-readout specification (schema_version / axes / feature_dimension). "
            "Required to CREATE a real frontier-scale (300B-4T) distributed run via "
            "/distributed/session -- the run is refused unless the probe is structurally "
            "loadable, because the CAS axis readout is the run's central deliverable. "
            "Ignored by the planning-only /scale-plan endpoint. Frontier run-gate (7)."
        ),
    )
    compute: ComputeEnvelopeDeclarationRequest | None = Field(
        default=None,
        description=(
            "Compute envelope (accelerator_count / accelerator_memory_gb). Required to "
            "CREATE a real frontier-scale (300B-4T) distributed run via /distributed/session "
            "-- the run is refused unless the declared hardware can physically hold the "
            "model under the planner's own memory model and worker fan-out cap. Ignored by "
            "the planning-only /scale-plan endpoint. Frontier run-gate (3)."
        ),
    )

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
    validation_status: ScalePlanValidationStatus
    validation_notice: str
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


class ModelProvenanceFileVerificationResponse(BaseModel):
    path: str
    declared_sha256: str
    verified: bool
    recomputed_sha256: str | None = None
    note: str


class ModelProvenanceSummaryResponse(BaseModel):
    status: Literal[
        "PROVENANCE_VERIFIED",
        "PROVENANCE_DECLARED_NOT_VERIFIED",
        "PROVENANCE_REJECTED",
    ]
    model_id: str | None = None
    license_id: str | None = None
    license_recognized: bool
    source_uri: str | None = None
    revision: str | None = None
    weight_file_count: int
    verified_file_count: int
    all_hashes_verified: bool
    manifest_content_digest: str | None = None
    notice: str
    reasons: list[str]
    file_verifications: list[ModelProvenanceFileVerificationResponse]


class ModelArchitectureAdapterSummaryResponse(BaseModel):
    status: Literal[
        "ARCHITECTURE_ADAPTER_VERIFIED",
        "ARCHITECTURE_ADAPTER_AVAILABLE",
        "ARCHITECTURE_ADAPTER_UNSUPPORTED",
    ]
    declared_model_type: str | None = None
    declared_architectures: list[str]
    resolved_model_type: str | None = None
    adapter_family: str | None = None
    layer_stack_attr: str | None = None
    hook_submodule: str | None = None
    adapter_validation: str | None = None
    adapter_available: bool
    notice: str
    reasons: list[str]
    declared_num_hidden_layers: int | None = None
    declared_hidden_size: int | None = None
    declared_num_attention_heads: int | None = None


class ProbeCompatibilitySummaryResponse(BaseModel):
    status: Literal[
        "PROBE_COMPATIBILITY_VERIFIED",
        "PROBE_COMPATIBILITY_DECLARED",
        "PROBE_COMPATIBILITY_UNSUPPORTED",
    ]
    schema_version: str | None = None
    probe_id: str | None = None
    axis_count: int
    axes: list[str]
    declared_feature_dimension: int | None = None
    expected_pooled_features: int | None = None
    dimension_consistent: bool | None = None
    weights_sha256: str | None = None
    definition_sha256: str | None = None
    tks_definition_locked: bool
    weights_hash_verified: bool
    probe_loadable: bool
    notice: str
    reasons: list[str]


class ComputeFeasibilitySummaryResponse(BaseModel):
    status: Literal[
        "COMPUTE_FEASIBILITY_VERIFIED",
        "COMPUTE_FEASIBILITY_DECLARED",
        "COMPUTE_FEASIBILITY_INSUFFICIENT",
    ]
    accelerator_type: str | None = None
    declared_accelerator_count: int | None = None
    declared_accelerator_memory_gb: float | None = None
    usable_memory_fraction: float
    fanout_cap: int
    per_accelerator_usable_gb: float | None = None
    effective_accelerator_count: int | None = None
    fanout_capped: bool
    needed_runtime_gb: float
    available_aggregate_gb: float | None = None
    memory_headroom_gb: float | None = None
    accelerators_required: int | None = None
    memory_sufficient: bool | None = None
    fit_verified: bool
    notice: str
    reasons: list[str]


class ModelAccessSummaryResponse(BaseModel):
    status: Literal[
        "MODEL_ACCESS_VERIFIED",
        "MODEL_ACCESS_DECLARED",
        "MODEL_ACCESS_UNSUPPORTED",
    ]
    declared_mode: str
    mechanistic_probe_supported: bool
    access_verified: bool
    notice: str
    reasons: list[str]


class CostExposureSummaryResponse(BaseModel):
    status: Literal[
        "COST_METERED",
        "COST_ACKNOWLEDGED",
        "COST_NOT_ACKNOWLEDGED",
    ]
    acknowledged: bool
    cost_metered: bool
    recommended_worker_count: int | None = None
    estimated_total_runtime_gb: float | None = None
    declared_accelerator_count: int | None = None
    declared_accelerator_memory_gb: float | None = None
    effective_accelerator_count: int | None = None
    notice: str
    reasons: list[str]


class DataCaptureSummaryResponse(BaseModel):
    status: Literal[
        "DATA_CAPTURE_WORM_COMMITTED",
        "DATA_CAPTURE_ACKNOWLEDGED",
        "DATA_CAPTURE_NOT_ACKNOWLEDGED",
    ]
    acknowledged: bool
    capture_committed: bool
    captured_signal_classes: list[str]
    retention_model: str
    reuse_purpose: str
    notice: str
    reasons: list[str]


class DistributedAuditResponse(BaseModel):
    audit_id: str
    plan_id: str
    status: Literal["PLANNED", "DISPATCHED", "RUNNING", "MERGE_PENDING", "COMPLETE", "FAILED"]
    merge_status: Literal["pending", "partial", "complete", "failed"]
    verdict: Verdict | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_packet_trace_id: str | None = None
    merge_reason: str
    access: ModelAccessSummaryResponse | None = None
    provenance: ModelProvenanceSummaryResponse | None = None
    architecture: ModelArchitectureAdapterSummaryResponse | None = None
    probe: ProbeCompatibilitySummaryResponse | None = None
    compute: ComputeFeasibilitySummaryResponse | None = None
    cost: CostExposureSummaryResponse | None = None
    data_capture: DataCaptureSummaryResponse | None = None
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
    evidence_packet_fragment_payload_sha256: str | None = None
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
    evidence_packet_fragment_payload: dict[str, object] | None = None
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
    """Return an open-weight distributed CAS Harness plan for 1B-4T models.

    300B-4T is the EXPERIMENTAL_NOT_VALIDATED frontier lane and is refused with
    HTTP 422 unless ``accept_experimental_frontier`` is set; >4T is always refused.
    """
    try:
        plan = build_scale_plan(
            PlannerScalePlanRequest(
                model_id=req.model_id,
                weight_access=req.weight_access,
                parameter_count_b=req.parameter_count_b,
                num_layers=req.num_layers,
                precision=req.precision,
                available_gpu_memory_gb=req.available_gpu_memory_gb,
                audit_depth=req.audit_depth,
                minimum_worker_count=req.minimum_worker_count,
                accept_experimental_frontier=req.accept_experimental_frontier,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ScalePlanResponse.model_validate(plan.to_dict())


@router.post("/distributed/session", response_model=DistributedAuditResponse)
async def create_distributed_audit_session(req: ScalePlanRequest) -> DistributedAuditResponse:
    """Create a real distributed audit control-plane run from an open-weight plan.

    Carries the same frontier gates as ``/scale-plan`` and more: a 300B-4T run is
    refused 422 unless ``accept_experimental_frontier`` is set, unless a valid model
    provenance manifest is attached (gate 5), unless the declared architecture resolves
    to a probe adapter the worker can hook (gate 6), unless a structurally loadable
    CAS probe-readout specification is attached (gate 7), unless the declared compute
    envelope can physically hold the model (gate 3), and unless the caller acknowledges
    the run's caller-owned, unquoted compute cost (gate 4). Two gates apply at every
    size: a non-open-weight access mode is refused (gate 2), and *any* run is refused
    unless the caller acknowledges that the audit captures the model's signal to an
    immutable store reused as CAS-Native training data (gate 8). >4T is always refused.
    """
    _require_locked_tks_definitions()
    try:
        record = create_distributed_audit(
            PlannerScalePlanRequest(
                model_id=req.model_id,
                weight_access=req.weight_access,
                parameter_count_b=req.parameter_count_b,
                num_layers=req.num_layers,
                precision=req.precision,
                available_gpu_memory_gb=req.available_gpu_memory_gb,
                audit_depth=req.audit_depth,
                minimum_worker_count=req.minimum_worker_count,
                accept_experimental_frontier=req.accept_experimental_frontier,
            ),
            provenance=req.provenance.to_service_manifest()
            if req.provenance is not None
            else None,
            architecture=req.architecture.to_service_declaration()
            if req.architecture is not None
            else None,
            probe=req.probe.to_service_specification()
            if req.probe is not None
            else None,
            compute=req.compute.to_service_declaration()
            if req.compute is not None
            else None,
            cost_acknowledged=req.accept_frontier_compute_cost,
            data_capture_acknowledged=req.accept_audit_data_capture,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
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
            evidence_packet_fragment_payload=req.evidence_packet_fragment_payload,
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
    packet_proof_chips = None
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
        packet_proof_chips = [
            chip.to_dict()
            for chip in normalize_evidence_packet_for_audit(
                packet_payload,
                verify_hashes=_verify_hashes_for_trace(run.merged_packet_trace_id),
            ).chips
        ]

    try:
        decision = verify_merged_fleet_packet(
            audit_id,
            explicit_packet_decision=packet_decision,
            proof_chips=packet_proof_chips,
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
async def create_audit_session(req: AuditSessionRequest, request: Request) -> AuditSessionResponse:
    """Validate the CAS Harness audit contract and create a stored M1 session."""
    _require_locked_tks_definitions()
    owner_sub, owner_api_key = _caller_identity(request)
    payload = req.model_dump(mode="json")
    if req.evidence_packet_trace_id:
        if settings.accounts_enabled:
            tenant_id = str(getattr(request.state, "tenant_id", "") or "")
            account_id = str(getattr(request.state, "account_id", "") or "")
            store = _audit_evidence_state_store(request)
            if not tenant_id or not account_id or store is None:
                raise HTTPException(
                    status_code=503, detail="Evidence ownership persistence is unavailable."
                )
            if req.evidence_packet_trace_id == REFERENCE_TARGET_EVIDENCE_PACKET_TRACE_ID:
                record_evidence_ownership(
                    store,
                    tenant_id=tenant_id,
                    account_id=account_id,
                    trace_id=req.evidence_packet_trace_id,
                )
            elif not tenant_owns_trace(
                store, tenant_id=tenant_id, trace_id=req.evidence_packet_trace_id
            ):
                raise HTTPException(status_code=404, detail="trace_id not found")
        try:
            with _audit_evidence_storage_context(request):
                payload.update(_audit_evidence_for_trace(req.evidence_packet_trace_id))
        except EvidenceObjectStoreError as exc:
            raise HTTPException(
                status_code=503, detail="Evidence Packet storage is unavailable."
            ) from exc
    record = create_session(
        payload, owner_sub=owner_sub, owner_api_key=owner_api_key, **_audit_storage_scope(request)
    )
    return AuditSessionResponse.model_validate(record.to_dict())


@router.get("/session/{audit_id}/status", response_model=AuditSessionResponse)
async def get_audit_session_status(audit_id: str, request: Request) -> AuditSessionResponse:
    """Return the stored session state instead of fabricating by audit id.

    Phase-1 identity-scope stopgap: a caller can only read a session they own;
    another caller's session reads as 404, never disclosed.
    """
    owner_sub, owner_api_key = _caller_identity(request)
    record = get_session(
        audit_id, owner_sub=owner_sub, owner_api_key=owner_api_key, **_audit_storage_scope(request)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Audit session not found")
    return AuditSessionResponse.model_validate(record.to_dict())


@router.post("/session/{audit_id}/run", response_model=AuditSessionResponse)
async def run_audit_session(
    audit_id: str,
    request: Request,
    req: RunAuditSessionRequest | None = None,
) -> AuditSessionResponse:
    """Run live worker evidence when available, then apply the verdict gate.

    An optional body may carry a customer bring-your-own-key (BYOK) ephemeral
    secret used only for this run (closed-API targets) and never persisted.

    Phase-1 identity-scope stopgap: the run is gated on ownership — a caller
    cannot run (or even confirm) another caller's session.
    """
    _require_locked_tks_definitions()
    owner_sub, owner_api_key = _caller_identity(request)
    # Per-tenant evidence ownership is now WIRED (see _record_audit_evidence_ownership, called at each
    # RUN-point below once the evidence trace_id is known). In account mode these routes have left the
    # auth allowlist, so the middleware decoded the jti token and set request.state.tenant_id/
    # account_id — a SERVER-derived identity, not a guess — which the ownership write keys on. In dark
    # mode (the default) the write is a complete no-op. Wired at the RUN point (not at create_session)
    # because the trace is produced HERE by attach_runner_evidence(...); create_session only attaches a
    # pre-existing evidence_packet_trace_id supplied by the caller and produces no new trace to own.
    storage_scope = _audit_storage_scope(request)
    existing = get_session(
        audit_id, owner_sub=owner_sub, owner_api_key=owner_api_key, **storage_scope
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Audit session not found")
    if settings.accounts_enabled:
        tenant_id = str(getattr(request.state, "tenant_id", "") or "")
        store = _audit_evidence_state_store(request)
        if not tenant_id or store is None:
            raise HTTPException(
                status_code=503, detail="Evidence ownership persistence is unavailable."
            )
        if existing.evidence_packet_trace_id and not tenant_owns_trace(
            store, tenant_id=tenant_id, trace_id=existing.evidence_packet_trace_id
        ):
            raise HTTPException(status_code=404, detail="trace_id not found")

    # A retried request after completion/failure must never call an external model or consume a
    # second month's quota. Quota idempotency is period-scoped, so this terminal-state return must
    # precede selection of the current execution period.
    if existing.status == "FAILED" or existing.evidence_packet_trace_id:
        completed = run_session(audit_id, **storage_scope)
        if completed is None:
            raise HTTPException(status_code=404, detail="Audit session not found")
        return AuditSessionResponse.model_validate(completed.to_dict())

    if settings.quotas_enabled:
        tenant_id = str(getattr(request.state, "tenant_id", "") or "")
        store = _audit_evidence_state_store(request)
        if not tenant_id or store is None:
            raise HTTPException(status_code=503, detail="Quota persistence is unavailable.")
        # Charge the month in which execution is attempted, not the month in which the draft
        # session was created. Otherwise a tenant could bank unused drafts in an earlier month and
        # burst them later without consuming the current execution month's allowance.
        period = current_monthly_period_key()
        try:
            consume_audit_quota(
                store,
                tenant_id=tenant_id,
                period_key=period,
                audit_id=audit_id,
                limit=get_quota_limit(),
            )
        except QuotaExceeded as exc:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "audit_quota_exceeded",
                    "limit": exc.limit,
                    "count": exc.count,
                    "period": period,
                },
            ) from exc

    run_attempt_id: str | None = None
    if _should_run_hosted_open_weight(existing) or _should_run_api_endpoint(existing):
        try:
            run_attempt_id = claim_run_attempt(audit_id, **storage_scope)
        except AuditRunInProgress as exc:
            raise HTTPException(status_code=409, detail="Audit run already in progress.") from exc
        if run_attempt_id is None:
            raise HTTPException(status_code=404, detail="Audit session not found")

    ephemeral_api_key = (
        req.api_key.get_secret_value() if req is not None and req.api_key is not None else None
    )
    if _should_run_hosted_open_weight(existing):
        prompt = existing.prompt_text or existing.scenario_text or ""
        try:
            with _audit_evidence_storage_context(request):
                live_result = await run_live_worker_audit(
                    audit_id=audit_id,
                    model_id=existing.model_id or "",
                    prompt=prompt,
                    audit_mode=existing.audit_mode,
                    selected_modules=existing.selected_modules,
                )
        except (LiveAuditRunnerUnavailable, EvidenceObjectStoreError) as exc:
            failed = fail_session(
                audit_id,
                message=f"Live hosted open-weight runner failed: {exc}",
                **storage_scope,
                run_attempt_id=run_attempt_id,
            )
            if failed is None:
                raise HTTPException(status_code=404, detail="Audit session not found")
            return AuditSessionResponse.model_validate(failed.to_dict())
        try:
            _record_audit_evidence_ownership(request, live_result.trace_id)
            attached = attach_runner_evidence(
                audit_id,
                evidence_packet_trace_id=live_result.trace_id,
                proof_chips=live_result.proof_chips,
                verifier_decision=live_result.verifier_decision,
                audit_scope=live_result.audit_scope,
                message=live_result.message,
                run_attempt_id=run_attempt_id,
                **storage_scope,
            )
        except HTTPException:
            fail_session(
                audit_id,
                message="Live audit result persistence failed after execution.",
                run_attempt_id=run_attempt_id,
                **storage_scope,
            )
            raise
        except Exception as exc:
            fail_session(
                audit_id,
                message="Live audit result persistence failed after execution.",
                run_attempt_id=run_attempt_id,
                **storage_scope,
            )
            raise HTTPException(
                status_code=503, detail="Audit result persistence is unavailable."
            ) from exc
        if attached is None:
            fail_session(
                audit_id,
                message="Live audit result could not be attached.",
                run_attempt_id=run_attempt_id,
                **storage_scope,
            )
            raise HTTPException(status_code=404, detail="Audit session not found")
    elif _should_run_api_endpoint(existing):
        prompt = existing.prompt_text or existing.scenario_text or ""
        try:
            with _audit_evidence_storage_context(request):
                api_result = await run_api_endpoint_audit(
                    audit_id=audit_id,
                    provider=existing.provider or "",
                    model_id=existing.model_id or "",
                    prompt=prompt,
                    audit_mode=existing.audit_mode,
                    selected_modules=existing.selected_modules,
                    endpoint_url=existing.endpoint_url,
                    api_key=ephemeral_api_key,
                )
        except (ApiEndpointRunnerUnavailable, EvidenceObjectStoreError) as exc:
            failed = fail_session(
                audit_id,
                message=f"Customer-API runner failed: {exc}",
                **storage_scope,
                run_attempt_id=run_attempt_id,
            )
            if failed is None:
                raise HTTPException(status_code=404, detail="Audit session not found")
            return AuditSessionResponse.model_validate(failed.to_dict())
        try:
            _record_audit_evidence_ownership(request, api_result.trace_id)
            attached = attach_runner_evidence(
                audit_id,
                evidence_packet_trace_id=api_result.trace_id,
                proof_chips=api_result.proof_chips,
                verifier_decision=api_result.verifier_decision,
                audit_scope=api_result.audit_scope,
                message=api_result.message,
                run_attempt_id=run_attempt_id,
                **storage_scope,
            )
        except HTTPException:
            fail_session(
                audit_id,
                message="Customer-API result persistence failed after execution.",
                run_attempt_id=run_attempt_id,
                **storage_scope,
            )
            raise
        except Exception as exc:
            fail_session(
                audit_id,
                message="Customer-API result persistence failed after execution.",
                run_attempt_id=run_attempt_id,
                **storage_scope,
            )
            raise HTTPException(
                status_code=503, detail="Audit result persistence is unavailable."
            ) from exc
        if attached is None:
            fail_session(
                audit_id,
                message="Customer-API result could not be attached.",
                run_attempt_id=run_attempt_id,
                **storage_scope,
            )
            raise HTTPException(status_code=404, detail="Audit session not found")

    record = run_session(audit_id, **storage_scope)
    if record is None:
        raise HTTPException(status_code=404, detail="Audit session not found")
    return AuditSessionResponse.model_validate(record.to_dict())


@router.get("/sessions", response_model=AuditSessionListResponse)
async def list_audit_sessions(request: Request) -> AuditSessionListResponse:
    """List the in-process M1 audit sessions owned by the requesting caller.

    Phase-1 identity-scope stopgap: scoped to the caller identity so one beta
    user cannot enumerate another user's audit sessions. Fails closed — a caller
    with no identity sees only the anonymous-owned bucket, never every session.
    """
    owner_sub, owner_api_key = _caller_identity(request)
    storage_scope = _audit_storage_scope(request)
    sessions = [
        AuditSessionResponse.model_validate(record.to_dict())
        for record in list_sessions(
            owner_sub=owner_sub, owner_api_key=owner_api_key, **storage_scope
        )
    ]
    return AuditSessionListResponse(sessions=sessions)


def _should_run_hosted_open_weight(record) -> bool:
    if record.status in {"SCAFFOLD_PENDING_RUNNER", "COMPLETE", "FAILED"}:
        return False
    if record.evidence_packet_trace_id:
        return False
    if record.endpoint_url:
        return False
    return record.model_id in HOSTED_OPEN_WEIGHT_MODEL_IDS


def _should_run_api_endpoint(record) -> bool:
    if record.status in {"SCAFFOLD_PENDING_RUNNER", "COMPLETE", "FAILED"}:
        return False
    if record.evidence_packet_trace_id:
        return False
    if not getattr(record, "provider", None):
        return False
    return record.provider in API_ENDPOINT_PROVIDERS


def _audit_evidence_for_trace(trace_id: str) -> dict[str, object]:
    try:
        packet_payload = _packet_payload_for_trace(trace_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence Packet trace_id not found: {trace_id}",
        )

    bridge = normalize_evidence_packet_for_audit(
        packet_payload,
        verify_hashes=_verify_hashes_for_trace(trace_id),
    )
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
        anchored = load_anchored_static_packet_payload(trace_id)
        if anchored is not None and _has_external_anchor(anchored):
            return anchored
        try:
            return load_stage9_40e_packet_payload_for_trace(trace_id)
        except FileNotFoundError:
            raise FileNotFoundError(trace_id)


def _verify_hashes_for_trace(trace_id: str) -> dict[str, object] | None:
    try:
        packet = build_packet_for_trace(trace_id)
    except FileNotFoundError:
        anchored = load_anchored_static_packet_payload(trace_id)
        if anchored is not None and _has_external_anchor(anchored):
            return verify_anchored_static_packet(anchored)
        return None
    hashes = getattr(packet, "hashes", None)
    if not isinstance(hashes, dict) or not isinstance(hashes.get("external_anchor"), dict):
        return None
    try:
        return _verify_packet_hashes(packet).model_dump(mode="json")
    except AttributeError:
        return None


def _has_external_anchor(packet: dict[str, object]) -> bool:
    hashes = packet.get("hashes")
    return isinstance(hashes, dict) and isinstance(hashes.get("external_anchor"), dict)


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
            "CAS Harness reference target verified locally against the bundled "
            "Stage 9 40E scoped validation packet (EleutherAI/gpt-neox-20b). No "
            "external model call, credential, or audit verdict was created. This is "
            "a scoped project validation record, not a per-customer production "
            "ACCEPT. The pre-computed Evidence Packet is available for the beta run step."
        ),
        checked_at=_utc_now(),
        provenance_chip=ProvenanceChip(
            id="model_proof",
            name="Model proof",
            status="present",
            detail=(
                f"Reference target {REFERENCE_TARGET_MODEL_ID} maps to the bundled "
                "Stage 9 40E scoped validation packet. This is target verification "
                "only: no live model call and no weight-hash verification."
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
