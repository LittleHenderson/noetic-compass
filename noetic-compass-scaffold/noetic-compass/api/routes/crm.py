"""CRM lead-capture routes — a public capture endpoint and authed sales views.

Three endpoints over :class:`~api.services.crm.service.CRMService`:

* ``POST /api/crm/public/leads`` — **public** (no auth). The seam an anonymous prospect's
  lead-capture form posts to. It is the only public CRM endpoint and lives under the
  ``/api/crm/public`` prefix that ``api/middleware/auth.py`` allow-lists. It captures the lead
  durably first, attempts sync, and returns an honest receipt — it never tells the prospect they
  are "in our CRM" unless a real provider actually landed them there.
* ``GET /api/crm/leads`` — **authed**. The sales-team list view (newest first).
* ``GET /api/crm/leads/{lead_id}`` — **authed**. One lead, or 404.

The service is built once at startup and stashed on ``app.state.crm`` (see ``api/main.py``). The
route reads it defensively: if the lifespan never ran (a minimal test client), it falls back to a
dark in-memory service so the endpoint degrades to capture-only rather than 500-ing. Capturing a
real prospect must never be the thing that breaks.
"""

from __future__ import annotations

from typing import Mapping

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.services.crm.abuse import PublicLeadAbuseGuard, build_public_lead_abuse_guard
from api.services.crm.models import LeadPipelineStatus, LeadSubmission, LeadValidationError
from api.services.crm.service import CRMService, build_dark_crm_service
from api.config import settings

router = APIRouter(prefix="/api/crm", tags=["crm"])

# Lazy dark fallback for environments where the lifespan never installed a service (e.g. a minimal
# test client). Built once on first use; in-memory and null-provider, so it captures but never
# claims a sync it cannot make.
_FALLBACK_SERVICE: CRMService | None = None
_FALLBACK_ABUSE_GUARD: PublicLeadAbuseGuard | None = None


def _service(request: Request) -> CRMService:
    """Return the installed CRM service, or a dark in-memory fallback if none was installed."""
    service = getattr(request.app.state, "crm", None)
    if service is not None:
        return service
    global _FALLBACK_SERVICE
    if _FALLBACK_SERVICE is None:
        _FALLBACK_SERVICE = build_dark_crm_service()
    return _FALLBACK_SERVICE


def _abuse_guard(request: Request) -> PublicLeadAbuseGuard:
    """Return the installed public-lead abuse guard, or a configured in-process fallback."""
    guard = getattr(request.app.state, "crm_public_abuse_guard", None)
    if guard is not None:
        return guard
    global _FALLBACK_ABUSE_GUARD
    if _FALLBACK_ABUSE_GUARD is None:
        _FALLBACK_ABUSE_GUARD = build_public_lead_abuse_guard(settings)
    return _FALLBACK_ABUSE_GUARD


def _client_key(request: Request) -> str:
    """Best-effort anonymous client key for public lead throttling."""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for.strip():
        return forwarded_for.split(",", 1)[0].strip()
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


class LeadSubmissionRequest(BaseModel):
    """The inbound public lead-capture payload. ``email`` is the only hard requirement.

    ``source`` defaults to a neutral public-form marker; a richer form may set it to name the exact
    page/campaign the lead came from (provenance, captured verbatim onto the lead).
    """

    email: str = Field(..., min_length=1, max_length=320)
    name: str = Field(default="", max_length=200)
    organization: str = Field(default="", max_length=200)
    message: str = Field(default="", max_length=4000)
    interest: str = Field(default="", max_length=120)
    source: str = Field(default="public_web_form", min_length=1, max_length=120)
    metadata: dict[str, str] = Field(default_factory=dict)
    # Hidden form field. Real users leave it blank; simple bots fill it and are rejected before
    # persistence. It is intentionally excluded from LeadSubmission.
    website: str = Field(default="", max_length=500)


class LeadCaptureResponse(BaseModel):
    """Honest receipt for a captured lead. ``synced`` is True only on a real external landing."""

    lead_id: str
    captured: bool
    sync_status: str
    synced: bool
    schema_version: str
    message: str


class LeadPipelineStatusUpdateRequest(BaseModel):
    """Authed sales-team update for the pipeline stage of one captured lead."""

    pipeline_status: LeadPipelineStatus


def _receipt_message(sync_status: str) -> str:
    """A prospect-facing message that never over-claims an external-CRM landing.

    Only ``synced`` says the lead reached the external CRM; every other status confirms receipt on
    our side without implying more than happened. Honesty applied to go-to-market.
    """
    if sync_status == "synced":
        return "Thanks — we've received your details and recorded them in our CRM."
    # captured / sync_pending / sync_failed all mean the same thing to the prospect: we have it.
    return "Thanks — we've received your details and someone will be in touch."


@router.post("/public/leads", response_model=LeadCaptureResponse)
async def capture_public_lead(request: Request, payload: LeadSubmissionRequest) -> LeadCaptureResponse:
    """Capture a lead from a public form. Public, no auth. Durable capture before any sync.

    Returns 422 if the email is unusable (we refuse to capture an uncontactable lead). The
    ``trace_id`` is the request's ``X-Request-ID`` so the captured lead walks back to this request.
    """
    decision = _abuse_guard(request).check(
        client_key=_client_key(request),
        honeypot_value=payload.website,
    )
    if not decision.allowed:
        if decision.reason == "rate_limit":
            raise HTTPException(
                status_code=429,
                detail="too many public lead submissions from this client; retry later",
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )
        raise HTTPException(status_code=400, detail="lead rejected by anti-abuse gate")

    service = _service(request)
    submission = LeadSubmission(
        email=payload.email,
        name=payload.name,
        organization=payload.organization,
        message=payload.message,
        interest=payload.interest,
        metadata=dict(payload.metadata),
    )
    trace_id = getattr(request.state, "request_id", None)
    try:
        lead = service.capture(submission, source=payload.source, trace_id=trace_id)
    except LeadValidationError as exc:
        # The prospect's input was unusable — a 4xx, not a captured junk record.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return LeadCaptureResponse(
        lead_id=lead.lead_id,
        captured=True,
        sync_status=lead.sync_status,
        synced=lead.sync_status == "synced",
        schema_version=lead.schema_version,
        message=_receipt_message(lead.sync_status),
    )


@router.get("/leads")
async def list_leads(request: Request) -> dict[str, object]:
    """List captured leads, newest first. Authed (sales view)."""
    service = _service(request)
    leads = service.list_leads()
    return {"count": len(leads), "leads": [lead.to_dict() for lead in leads]}


@router.get("/leads/{lead_id}")
async def get_lead(request: Request, lead_id: str) -> dict[str, object]:
    """Fetch one captured lead by id, or 404. Authed (sales view)."""
    service = _service(request)
    lead = service.get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail=f"lead {lead_id!r} not found")
    return lead.to_dict()


@router.patch("/leads/{lead_id}/pipeline-status")
async def update_lead_pipeline_status(
    request: Request,
    lead_id: str,
    payload: LeadPipelineStatusUpdateRequest,
) -> dict[str, object]:
    """Move one captured lead through the sales pipeline. Authed (sales view)."""
    service = _service(request)
    lead = service.update_pipeline_status(lead_id, payload.pipeline_status)
    if lead is None:
        raise HTTPException(status_code=404, detail=f"lead {lead_id!r} not found")
    return lead.to_dict()
