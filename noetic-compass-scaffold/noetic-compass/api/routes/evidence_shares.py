"""Account-mode lifecycle for expiring read-only Evidence Packet shares."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, NamedTuple

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from api.config import settings
from api.dependencies.authz import current_account, current_tenant, require_role
from api.services.evidence_shares import (
    EvidenceShare,
    EvidenceShareError,
    EvidenceShareNotFound,
    EvidenceShareService,
    EvidenceShareStorageError,
    EvidenceShareUnavailable,
)


router = APIRouter(prefix="/evidence", tags=["evidence-shares"])

_ALL_ACCOUNT_ROLES = ("member", "support", "operator", "admin", "owner")
_role_gate = require_role(*_ALL_ACCOUNT_ROLES)
_UNAVAILABLE_DETAIL = "Shared Evidence Packet is unavailable."
_NO_STORE_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


class CreateEvidenceShareRequest(BaseModel):
    expires_at: datetime = Field(
        description="Absolute, timezone-aware expiry; maximum 30 days from creation."
    )

    @field_validator("expires_at")
    @classmethod
    def require_absolute_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("expires_at must include a timezone")
        return value.astimezone(timezone.utc)


class EvidenceShareMetadataResponse(BaseModel):
    share_id: str
    trace_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    status: Literal["active", "expired", "revoked"]


class CreateEvidenceShareResponse(EvidenceShareMetadataResponse):
    share_token: str = Field(
        description="Returned once. The service never persists or returns it again."
    )
    anonymous_fetch_path: str = Field(
        description="Send share_token in X-Evidence-Share-Token; never put it in the URL."
    )


class _ShareIdentity(NamedTuple):
    tenant_id: str
    account_id: str
    role: str
    service: EvidenceShareService


def _account_share_identity(request: Request) -> _ShareIdentity:
    # This surface has no legacy shared-secret posture. Both gates must be
    # explicit before a role/tenant/account value is consumed.
    if not settings.accounts_enabled or not settings.evidence_shares_enabled:
        raise HTTPException(status_code=503, detail="Evidence Packet sharing is unavailable.")
    role = _role_gate(request)
    service = getattr(request.app.state, "evidence_share_service", None)
    if not isinstance(service, EvidenceShareService):
        raise HTTPException(status_code=503, detail="Evidence Packet sharing is unavailable.")
    return _ShareIdentity(
        tenant_id=current_tenant(request),
        account_id=current_account(request),
        role=role,
        service=service,
    )


def _metadata(share: EvidenceShare) -> EvidenceShareMetadataResponse:
    now = datetime.now(timezone.utc)
    return EvidenceShareMetadataResponse(
        share_id=share.share_id,
        trace_id=share.trace_id,
        created_at=share.created_at,
        expires_at=share.expires_at,
        revoked_at=share.revoked_at,
        status=share.status(now=now),
    )


def _set_no_store(response: Response) -> None:
    for key, value in _NO_STORE_HEADERS.items():
        response.headers[key] = value


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.post(
    "/{trace_id}/shares",
    response_model=CreateEvidenceShareResponse,
    status_code=201,
)
def create_evidence_share(
    trace_id: str,
    body: CreateEvidenceShareRequest,
    request: Request,
    response: Response,
) -> CreateEvidenceShareResponse:
    identity = _account_share_identity(request)
    try:
        created = identity.service.create_share(
            tenant_id=identity.tenant_id,
            account_id=identity.account_id,
            trace_id=trace_id,
            expires_at=body.expires_at,
            request_id=_request_id(request),
        )
    except EvidenceShareNotFound as exc:
        raise HTTPException(status_code=404, detail="Evidence Packet is unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EvidenceShareError as exc:
        raise HTTPException(
            status_code=503, detail="Evidence Packet sharing is unavailable."
        ) from exc
    _set_no_store(response)
    metadata = _metadata(created.share)
    return CreateEvidenceShareResponse(
        **metadata.model_dump(),
        share_token=created.token,
        anonymous_fetch_path=f"/evidence/shared/{created.share.share_id}",
    )


@router.get(
    "/shares/{share_id}",
    response_model=EvidenceShareMetadataResponse,
)
def get_evidence_share(
    share_id: str,
    request: Request,
    response: Response,
) -> EvidenceShareMetadataResponse:
    identity = _account_share_identity(request)
    try:
        share = identity.service.get_share(
            tenant_id=identity.tenant_id,
            account_id=identity.account_id,
            actor_role=identity.role,
            share_id=share_id,
        )
    except (EvidenceShareNotFound, EvidenceShareUnavailable) as exc:
        raise HTTPException(status_code=404, detail="Evidence share not found.") from exc
    except EvidenceShareError as exc:
        raise HTTPException(
            status_code=503, detail="Evidence Packet sharing is unavailable."
        ) from exc
    _set_no_store(response)
    return _metadata(share)


@router.delete(
    "/shares/{share_id}",
    response_model=EvidenceShareMetadataResponse,
)
def revoke_evidence_share(
    share_id: str,
    request: Request,
    response: Response,
) -> EvidenceShareMetadataResponse:
    identity = _account_share_identity(request)
    try:
        share = identity.service.revoke_share(
            tenant_id=identity.tenant_id,
            account_id=identity.account_id,
            actor_role=identity.role,
            share_id=share_id,
            request_id=_request_id(request),
        )
    except (EvidenceShareNotFound, EvidenceShareUnavailable) as exc:
        raise HTTPException(status_code=404, detail="Evidence share not found.") from exc
    except EvidenceShareStorageError as exc:
        raise HTTPException(
            status_code=503, detail="Evidence Packet sharing is unavailable."
        ) from exc
    _set_no_store(response)
    return _metadata(share)


@router.get("/shared/{share_id}")
def fetch_shared_evidence_packet(
    share_id: str,
    request: Request,
    share_token: str = Header(default="", alias="X-Evidence-Share-Token"),
) -> JSONResponse:
    """Anonymous packet fetch with one deliberately non-leaky negative response."""

    service = getattr(request.app.state, "evidence_share_service", None)
    if not settings.accounts_enabled or not settings.evidence_shares_enabled:
        return JSONResponse(
            status_code=404,
            content={"detail": _UNAVAILABLE_DETAIL},
            headers=_NO_STORE_HEADERS,
        )
    if not isinstance(service, EvidenceShareService):
        return JSONResponse(
            status_code=404,
            content={"detail": _UNAVAILABLE_DETAIL},
            headers=_NO_STORE_HEADERS,
        )
    try:
        packet = service.fetch_shared_packet(
            share_id=share_id,
            token=share_token,
            request_id=_request_id(request),
        )
    except Exception:
        # Do not log the exception: a lower-level message might include backend
        # details. Most importantly, the token is never interpolated anywhere.
        return JSONResponse(
            status_code=404,
            content={"detail": _UNAVAILABLE_DETAIL},
            headers=_NO_STORE_HEADERS,
        )
    return JSONResponse(content=packet, headers=_NO_STORE_HEADERS)


__all__ = ["router"]
