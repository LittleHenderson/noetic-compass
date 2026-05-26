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
from api.services.cas_harness_evidence_bridge import normalize_evidence_packet_for_audit
from api.services.cas_harness_verifier_decision_adapter import verifier_decision_from_packet


router = APIRouter(prefix="/api/cas-harness/audit", tags=["cas_harness_audit"])

AuditMode = Literal["BALANCED", "HIGH_PRECISION", "MAX_COVERAGE_TRIAGE"]
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


@router.post("/target/verify", response_model=ModelTargetVerificationResponse)
async def verify_model_target(
    req: ModelTargetVerificationRequest,
) -> ModelTargetVerificationResponse:
    """Validate a model target without producing or implying an audit verdict."""
    target = req.target
    if target.kind == "demo_reference":
        return _reference_target_response(target)
    return _api_endpoint_target_response(target)


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
