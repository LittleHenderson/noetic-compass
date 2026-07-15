"""Owner-created, public-read publication-authorization records."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from api.config import settings
from api.dependencies.authz import require_role
from api.services.acceptance_publication_authorizations import (
    AcceptancePublicationAuthorizationInvalid,
    AcceptancePublicationAuthorizationNotFound,
    AcceptancePublicationAuthorizationStore,
    AcceptancePublicationAuthorizationUnavailable,
)


router = APIRouter(tags=["acceptance_publication_authorizations"])
logger = logging.getLogger("noetic.acceptance_publication_authorizations")

_MAX_REQUEST_BYTES = 8_192
_NO_STORE_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "X-Content-Type-Options": "nosniff",
}


class CreateAcceptancePublicationAuthorizationRequest(BaseModel):
    """Only exact operation bindings; no approval or evidence content."""

    model_config = ConfigDict(extra="forbid", strict=True)

    record_type: Literal["authority_operation"]
    action: Literal["AUTHORIZE"]
    gate: str = Field(min_length=1, max_length=64)
    master_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    deploy_id: str = Field(pattern=r"^dep-[A-Za-z0-9]+$")
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_head_version: int = Field(ge=0)
    expected_previous_evidence_sha256: str | None = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    reason: Literal["authorized_publication"]


def _store(request: Request) -> AcceptancePublicationAuthorizationStore:
    store = getattr(
        request.app.state, "acceptance_publication_authorization_store", None
    )
    if not isinstance(store, AcceptancePublicationAuthorizationStore):
        raise HTTPException(
            status_code=503,
            detail="Publication authorization storage is unavailable.",
            headers=_NO_STORE_HEADERS,
        )
    return store


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _reject_json_constant(_: str) -> None:
    raise ValueError("non-finite JSON number")


async def _decode_request(
    request: Request,
) -> CreateAcceptancePublicationAuthorizationRequest:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(
            status_code=415,
            detail="application/json is required.",
            headers=_NO_STORE_HEADERS,
        )
    body = await request.body()
    if not body or len(body) > _MAX_REQUEST_BYTES:
        raise HTTPException(
            status_code=422,
            detail="Request JSON is invalid.",
            headers=_NO_STORE_HEADERS,
        )
    try:
        decoded = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
        if not isinstance(decoded, dict):
            raise ValueError("JSON root is not an object")
        return CreateAcceptancePublicationAuthorizationRequest.model_validate(
            decoded, strict=True
        )
    except (UnicodeDecodeError, ValueError, ValidationError):
        # Keep duplicate/field diagnostics server-side so hostile callers do not
        # get a schema-enumeration oracle beyond the documented 422 boundary.
        raise HTTPException(
            status_code=422,
            detail="Request JSON is invalid.",
            headers=_NO_STORE_HEADERS,
        ) from None


@router.post("/accounts/acceptance-authorizations", status_code=201)
async def create_acceptance_publication_authorization(
    request: Request,
    _role: str = Depends(require_role("owner")),
) -> Response:
    """Create a fixed-TTL operation authorization as the primary tenant owner."""

    body = await _decode_request(request)
    actor_tenant_id = str(getattr(request.state, "tenant_id", "") or "")
    actor_account_id = str(getattr(request.state, "account_id", "") or "")
    if (
        actor_tenant_id != settings.accounts_bootstrap_tenant_id
        or not actor_account_id
    ):
        raise HTTPException(
            status_code=403,
            detail="A primary-tenant owner authorization is required.",
            headers=_NO_STORE_HEADERS,
        )
    try:
        created = _store(request).create(
            actor_tenant_id=actor_tenant_id,
            actor_account_id=actor_account_id,
            actor_role=_role,
            gate=body.gate,
            master_head_sha=body.master_head_sha,
            deploy_id=body.deploy_id,
            evidence_sha256=body.evidence_sha256,
            expected_head_version=body.expected_head_version,
            expected_previous_evidence_sha256=(
                body.expected_previous_evidence_sha256
            ),
            reason=body.reason,
        )
    except AcceptancePublicationAuthorizationInvalid as exc:
        raise HTTPException(
            status_code=422,
            detail="Publication authorization bindings are invalid.",
            headers=_NO_STORE_HEADERS,
        ) from exc
    except AcceptancePublicationAuthorizationUnavailable as exc:
        logger.warning(
            "publication authorization create failed reason=%s", type(exc).__name__
        )
        raise HTTPException(
            status_code=503,
            detail="Publication authorization storage is unavailable.",
            headers=_NO_STORE_HEADERS,
        ) from exc
    return JSONResponse(
        status_code=201,
        content={
            "authorization_artifact_uri": created.uri,
            "authorization_artifact_sha256": created.sha256,
            "expires_at_utc": created.payload["expires_at_utc"],
        },
        headers=_NO_STORE_HEADERS,
    )


@router.get("/internal/acceptance-authorizations/{authorization_sha256}")
async def read_acceptance_publication_authorization(
    authorization_sha256: str, request: Request
) -> Response:
    """Return one exact live canonical record; no query/list/head semantics."""

    try:
        record = _store(request).load(authorization_sha256)
    except (
        AcceptancePublicationAuthorizationInvalid,
        AcceptancePublicationAuthorizationNotFound,
    ):
        return JSONResponse(
            status_code=404,
            content={"detail": "Publication authorization is unavailable."},
            headers=_NO_STORE_HEADERS,
        )
    except AcceptancePublicationAuthorizationUnavailable as exc:
        logger.warning(
            "publication authorization read failed reason=%s", type(exc).__name__
        )
        return JSONResponse(
            status_code=503,
            content={"detail": "Publication authorization storage is unavailable."},
            headers=_NO_STORE_HEADERS,
        )
    return Response(
        content=record.body,
        status_code=200,
        media_type="application/json",
        headers={**_NO_STORE_HEADERS, "ETag": f'"sha256:{record.sha256}"'},
    )


__all__ = ["router"]
