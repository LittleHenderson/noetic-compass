"""CAS Harness audit API scaffold.

This route is intentionally a mock/scaffold until a real CAS audit runner is
wired behind it. It validates the front-door contract and returns honest
pending state instead of fabricated verdicts.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


router = APIRouter(prefix="/api/cas-harness/audit", tags=["cas_harness_audit"])

AuditMode = Literal["BALANCED", "HIGH_PRECISION", "MAX_COVERAGE_TRIAGE"]
AuditStatus = Literal["SCAFFOLD_PENDING_RUNNER"]
ModelStatus = Literal["NOT_CONNECTED_MOCK"]
Verdict = Literal["ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"]


class ProvenanceChip(BaseModel):
    label: str = Field(..., min_length=1, max_length=64)
    value: str = Field(..., min_length=1, max_length=160)


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
    verdict: Verdict | None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_packet_trace_id: str | None
    atlas_deep_link: str | None
    provenance_chips: list[ProvenanceChip]


def _provenance_chips() -> list[ProvenanceChip]:
    return [
        ProvenanceChip(label="runner", value="scaffold/mock: no CAS audit runner wired"),
        ProvenanceChip(label="verdict", value="not computed"),
        ProvenanceChip(label="license", value="placeholder only; JWT auth remains the gate"),
    ]


def _audit_id_for(req: AuditSessionRequest) -> str:
    payload = req.model_dump(mode="json", exclude={"license_key"})
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"cas-audit-{digest[:16]}"


def _mock_pending_response(audit_id: str) -> AuditSessionResponse:
    return AuditSessionResponse(
        audit_id=audit_id,
        status="SCAFFOLD_PENDING_RUNNER",
        model_status="NOT_CONNECTED_MOCK",
        verdict=None,
        confidence=None,
        evidence_packet_trace_id=None,
        atlas_deep_link=None,
        provenance_chips=_provenance_chips(),
    )


@router.post("/session", response_model=AuditSessionResponse)
async def create_audit_session(req: AuditSessionRequest) -> AuditSessionResponse:
    """Validate the CAS Harness audit contract and return pending scaffold state."""
    return _mock_pending_response(_audit_id_for(req))


@router.get("/session/{audit_id}/status", response_model=AuditSessionResponse)
async def get_audit_session_status(audit_id: str) -> AuditSessionResponse:
    """Return deterministic scaffold status until a real runner is connected."""
    return _mock_pending_response(audit_id)
