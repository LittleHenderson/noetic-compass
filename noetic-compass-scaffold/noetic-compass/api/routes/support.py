"""Public support intake and authenticated ticket-lifecycle routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, StrictBool, StrictStr

from api.config import settings
from api.dependencies.authz import require_role_in_account_mode
from api.services.crm.abuse import PublicLeadAbuseGuard
from api.services.crm.privacy import (
    CRMPrivacyNoticeConfigError,
    CRMPrivacyNoticeContract,
)
from api.services.support_tickets import (
    InMemorySupportTicketStore,
    SupportTicket,
    SupportTicketService,
    SupportTicketValidationError,
)


router = APIRouter(prefix="/api/support", tags=["support"])
# Tickets are one platform-global queue containing customer PII. ``system`` is service-only and
# cannot be minted by any customer invite/provisioning route, so account-mode tenant roles (even
# owner/admin/support) cannot turn their tenant authority into access to this global queue.
_platform_support_gate = require_role_in_account_mode("system")
_FALLBACK_SERVICE: SupportTicketService | None = None
_FALLBACK_GUARD: PublicLeadAbuseGuard | None = None


def _service(request: Request) -> SupportTicketService:
    installed = getattr(request.app.state, "support_tickets", None)
    durable_required = settings.accounts_enabled or not settings.debug
    if isinstance(installed, SupportTicketService) and (
        installed.is_durable or not durable_required
    ):
        return installed
    if durable_required:
        raise HTTPException(
            status_code=503,
            detail="support ticket persistence is unavailable",
        )
    global _FALLBACK_SERVICE
    if _FALLBACK_SERVICE is None:
        _FALLBACK_SERVICE = SupportTicketService(InMemorySupportTicketStore())
    return _FALLBACK_SERVICE


def _guard(request: Request) -> PublicLeadAbuseGuard:
    installed = getattr(request.app.state, "support_public_abuse_guard", None)
    if installed is not None:
        return installed
    global _FALLBACK_GUARD
    if _FALLBACK_GUARD is None:
        _FALLBACK_GUARD = PublicLeadAbuseGuard(
            max_submissions=settings.support_public_ticket_rate_limit_max,
            window_seconds=settings.support_public_ticket_rate_limit_window_seconds,
        )
    return _FALLBACK_GUARD


def _privacy_notice_contract(request: Request) -> CRMPrivacyNoticeContract:
    """Return the installed server-owned notice, failing closed if unavailable."""

    contract = getattr(request.app.state, "crm_privacy_notice_contract", None)
    if not isinstance(contract, CRMPrivacyNoticeContract):
        raise CRMPrivacyNoticeConfigError(
            "server privacy notice contract is unavailable"
        )
    return contract.validated()


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for.strip():
        return forwarded_for.split(",", 1)[0].strip()
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def _not_found(ticket_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"support ticket {ticket_id!r} not found")


def _private_record(ticket: SupportTicket) -> dict[str, object]:
    record = ticket.to_dict()
    record["ack_sla_seconds"] = settings.support_ack_sla_seconds
    record["acknowledged_within_sla"] = ticket.acknowledged_within(
        settings.support_ack_sla_seconds
    )
    return record


class PublicTicketRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    name: str = Field(default="", max_length=200)
    organization: str = Field(default="", max_length=200)
    subject: str = Field(..., min_length=1, max_length=240)
    message: str = Field(..., min_length=1, max_length=8000)
    category: str = Field(default="support", min_length=1, max_length=80)
    source: str = Field(default="cascompass_contact", min_length=1, max_length=120)
    consent_to_contact: StrictBool
    privacy_notice_version: StrictStr | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
    )
    privacy_notice_content_sha256: StrictStr | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    website: str = Field(default="", max_length=500)


class PublicTicketReceipt(BaseModel):
    ticket_id: str
    received: bool
    status: str
    created_at_utc: str
    response_sla_seconds: int
    privacy_url: str
    privacy_notice_version: str
    privacy_notice_content_sha256: str
    privacy_notice_publication_status: str
    message: str


class RouteTicketRequest(BaseModel):
    owner: str = Field(..., min_length=1, max_length=200)


class ResolveTicketRequest(BaseModel):
    resolution_summary: str = Field(..., min_length=1, max_length=4000)


@router.post("/public/tickets", response_model=PublicTicketReceipt, status_code=201)
async def create_public_ticket(
    request: Request, payload: PublicTicketRequest, response: Response
) -> PublicTicketReceipt:
    try:
        notice = _privacy_notice_contract(request)
    except CRMPrivacyNoticeConfigError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "public support intake is unavailable because the server privacy "
                "notice contract is invalid or unavailable"
            ),
        ) from exc
    if not notice.permits_contact_capture:
        raise HTTPException(
            status_code=503,
            detail=(
                "public support intake is unavailable while privacy notice publication "
                f"status is {notice.publication_status}"
            ),
        )

    if (
        payload.privacy_notice_version is None
        or payload.privacy_notice_content_sha256 is None
        or payload.privacy_notice_version != notice.version
        or payload.privacy_notice_content_sha256 != notice.content_sha256
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "the submitted privacy notice acknowledgement is missing or stale; "
                "reload the form"
            ),
        )

    service = _service(request)

    decision = _guard(request).check(
        client_key=_client_key(request), honeypot_value=payload.website
    )
    if not decision.allowed:
        if decision.reason == "rate_limit":
            raise HTTPException(
                status_code=429,
                detail="too many support requests from this client; retry later",
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )
        raise HTTPException(status_code=400, detail="support request rejected by anti-abuse gate")
    try:
        ticket = service.receive(
            email=payload.email,
            name=payload.name,
            organization=payload.organization,
            subject=payload.subject,
            message=payload.message,
            category=payload.category,
            source=payload.source,
            consent_to_contact=payload.consent_to_contact,
            privacy_notice_version=notice.version,
            privacy_notice_content_sha256=notice.content_sha256,
            privacy_notice_publication_status=notice.publication_status,
            trace_id=getattr(request.state, "request_id", None),
        )
    except SupportTicketValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.headers["Cache-Control"] = "no-store"
    return PublicTicketReceipt(
        ticket_id=ticket.ticket_id,
        received=True,
        status=ticket.status,
        created_at_utc=ticket.created_at_utc,
        response_sla_seconds=settings.support_ack_sla_seconds,
        privacy_url=notice.url,
        privacy_notice_version=notice.version,
        privacy_notice_content_sha256=notice.content_sha256,
        privacy_notice_publication_status=notice.publication_status,
        message="Your request was received. Keep the ticket ID for follow-up.",
    )


@router.get("/tickets")
async def list_tickets(
    request: Request, _role: str | None = Depends(_platform_support_gate)
) -> dict[str, object]:
    tickets = _service(request).list_all()
    return {"count": len(tickets), "tickets": [_private_record(item) for item in tickets]}


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    request: Request,
    ticket_id: str,
    _role: str | None = Depends(_platform_support_gate),
) -> dict[str, object]:
    ticket = _service(request).get(ticket_id)
    if ticket is None:
        raise _not_found(ticket_id)
    return _private_record(ticket)


@router.post("/tickets/{ticket_id}/route")
async def route_ticket(
    request: Request,
    ticket_id: str,
    payload: RouteTicketRequest,
    _role: str | None = Depends(_platform_support_gate),
) -> dict[str, object]:
    try:
        ticket = _service(request).route(ticket_id, owner=payload.owner)
    except SupportTicketValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if ticket is None:
        raise _not_found(ticket_id)
    return _private_record(ticket)


@router.post("/tickets/{ticket_id}/acknowledge")
async def acknowledge_ticket(
    request: Request,
    ticket_id: str,
    _role: str | None = Depends(_platform_support_gate),
) -> dict[str, object]:
    actor = str(
        getattr(request.state, "account_id", None)
        or getattr(request.state, "user", "")
    ).strip()
    try:
        ticket = _service(request).acknowledge(ticket_id, actor=actor)
    except SupportTicketValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if ticket is None:
        raise _not_found(ticket_id)
    return _private_record(ticket)


@router.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(
    request: Request,
    ticket_id: str,
    payload: ResolveTicketRequest,
    _role: str | None = Depends(_platform_support_gate),
) -> dict[str, object]:
    actor = str(
        getattr(request.state, "account_id", None)
        or getattr(request.state, "user", "")
    ).strip()
    try:
        ticket = _service(request).resolve(
            ticket_id, actor=actor, summary=payload.resolution_summary
        )
    except SupportTicketValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if ticket is None:
        raise _not_found(ticket_id)
    return _private_record(ticket)
