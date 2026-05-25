"""CAS Harness audit API scaffold.

This route owns the M1 audit-session lifecycle contract. It stores sessions
in-process and advances state honestly, but it does not fabricate CAS verdicts
until a real audit runner is wired behind it.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from api.services.cas_harness_audit_sessions import (
    create_session,
    get_session,
    list_sessions,
    run_session,
)


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
Verdict = Literal["ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"]


class ProvenanceChip(BaseModel):
    label: str = Field(..., min_length=1, max_length=64)
    value: str = Field(..., min_length=1, max_length=160)


class AuditLifecycleEvent(BaseModel):
    status: AuditStatus
    message: str = Field(..., min_length=1, max_length=240)
    timestamp: str


class AuditSessionRequest(BaseModel):
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    endpoint_url: HttpUrl | None = None
    audit_mode: AuditMode = "BALANCED"
    prompt: str | None = Field(default=None, min_length=1, max_length=12000)
    scenario_text: str | None = Field(default=None, min_length=1, max_length=12000)
    selected_modules: list[str] = Field(..., min_length=1, max_length=24)
    license_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Placeholder for future license validation; not billed or verified here.",
    )

    @field_validator("model_id", "prompt", "scenario_text", "license_key")
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
    lifecycle: list[AuditLifecycleEvent]


class AuditSessionListResponse(BaseModel):
    sessions: list[AuditSessionResponse]


@router.post("/session", response_model=AuditSessionResponse)
async def create_audit_session(req: AuditSessionRequest) -> AuditSessionResponse:
    """Validate the CAS Harness audit contract and create a stored M1 session."""
    payload = req.model_dump(mode="json")
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
