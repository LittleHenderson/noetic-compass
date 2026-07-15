"""Authenticated creation/revocation and exact public reads of attestations."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from api.config import settings
from api.dependencies.authz import require_role
from api.services.human_attestations import (
    HumanAttestationInvalid,
    HumanAttestationNotFound,
    HumanAttestationStore,
    HumanAttestationUnavailable,
)


router = APIRouter(tags=["human_attestations"])
logger = logging.getLogger("noetic.human_attestations")
_MAX_REQUEST_BYTES = 32_768
_NO_STORE_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "X-Content-Type-Options": "nosniff",
}


class SupportingAttestationReference(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    role: str = Field(min_length=1, max_length=64)
    attestation_artifact_uri: str = Field(min_length=1, max_length=512)
    attestation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    attested_at_utc: str = Field(
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    )


class CreateHumanAttestationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    purpose: str = Field(min_length=1, max_length=64)
    gate: str = Field(min_length=1, max_length=64)
    attestation_role: str = Field(min_length=1, max_length=64)
    master_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    deploy_id: str = Field(pattern=r"^dep-[A-Za-z0-9]+$")
    evidence_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    supporting_attestations: list[SupportingAttestationReference] = Field(
        default_factory=list, max_length=8
    )


def _store(request: Request) -> HumanAttestationStore:
    store = getattr(request.app.state, "human_attestation_store", None)
    if not isinstance(store, HumanAttestationStore):
        raise HTTPException(
            status_code=503,
            detail="Human attestation storage is unavailable.",
            headers=_NO_STORE_HEADERS,
        )
    return store


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(_: str) -> None:
    raise ValueError("non-finite JSON number")


async def _decode_request(request: Request) -> CreateHumanAttestationRequest:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(415, "application/json is required.", headers=_NO_STORE_HEADERS)
    raw_buffer = bytearray()
    async for chunk in request.stream():
        if len(raw_buffer) + len(chunk) > _MAX_REQUEST_BYTES:
            raise HTTPException(
                422, "Request JSON is invalid.", headers=_NO_STORE_HEADERS
            )
        raw_buffer.extend(chunk)
    raw = bytes(raw_buffer)
    if not raw:
        raise HTTPException(422, "Request JSON is invalid.", headers=_NO_STORE_HEADERS)
    try:
        decoded = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
        if not isinstance(decoded, dict):
            raise ValueError("JSON root is not an object")
        return CreateHumanAttestationRequest.model_validate(decoded, strict=True)
    except (UnicodeDecodeError, ValueError, ValidationError):
        raise HTTPException(
            422, "Request JSON is invalid.", headers=_NO_STORE_HEADERS
        ) from None


@router.post("/accounts/human-attestations", status_code=201)
async def create_human_attestation(
    request: Request,
    account_role: str = Depends(require_role("owner", "admin", "operator", "support")),
) -> Response:
    body = await _decode_request(request)
    tenant_id = str(getattr(request.state, "tenant_id", "") or "")
    account_id = str(getattr(request.state, "account_id", "") or "")
    if tenant_id != settings.accounts_bootstrap_tenant_id or not account_id:
        raise HTTPException(
            403,
            "A primary-tenant authenticated account is required.",
            headers=_NO_STORE_HEADERS,
        )
    try:
        created = _store(request).create(
            actor_tenant_id=tenant_id,
            actor_account_id=account_id,
            actor_account_role=account_role,
            purpose=body.purpose,
            gate=body.gate,
            attestation_role=body.attestation_role,
            master_head_sha=body.master_head_sha,
            deploy_id=body.deploy_id,
            evidence_binding_sha256=body.evidence_binding_sha256,
            supporting_attestations=[item.model_dump() for item in body.supporting_attestations],
        )
    except (HumanAttestationInvalid, HumanAttestationNotFound) as exc:
        raise HTTPException(
            422, "Human attestation bindings are invalid.", headers=_NO_STORE_HEADERS
        ) from exc
    except HumanAttestationUnavailable as exc:
        logger.warning("human attestation create failed reason=%s", type(exc).__name__)
        raise HTTPException(
            503, "Human attestation storage is unavailable.", headers=_NO_STORE_HEADERS
        ) from exc
    return JSONResponse(
        status_code=201,
        content={
            "attestation_artifact_uri": created.uri,
            "attestation_sha256": created.sha256,
            "attested_at_utc": created.payload["attested_at_utc"],
        },
        headers=_NO_STORE_HEADERS,
    )


@router.post("/accounts/human-attestations/{attestation_sha256}/revoke")
async def revoke_human_attestation(
    attestation_sha256: str,
    request: Request,
    account_role: str = Depends(require_role("owner", "admin", "operator", "support")),
) -> Response:
    tenant_id = str(getattr(request.state, "tenant_id", "") or "")
    account_id = str(getattr(request.state, "account_id", "") or "")
    try:
        _store(request).revoke(
            attestation_sha256,
            actor_tenant_id=tenant_id,
            actor_account_id=account_id,
            actor_account_role=account_role,
        )
    except (HumanAttestationInvalid, HumanAttestationNotFound) as exc:
        raise HTTPException(
            404, "Human attestation is unavailable.", headers=_NO_STORE_HEADERS
        ) from exc
    except HumanAttestationUnavailable as exc:
        logger.warning("human attestation revoke failed reason=%s", type(exc).__name__)
        raise HTTPException(
            503, "Human attestation storage is unavailable.", headers=_NO_STORE_HEADERS
        ) from exc
    return JSONResponse({"revoked": True}, headers=_NO_STORE_HEADERS)


@router.get("/internal/human-attestations/{attestation_sha256}")
async def read_human_attestation(attestation_sha256: str, request: Request) -> Response:
    try:
        record = _store(request).load(attestation_sha256)
    except (HumanAttestationInvalid, HumanAttestationNotFound):
        return JSONResponse(
            status_code=404,
            content={"detail": "Human attestation is unavailable."},
            headers=_NO_STORE_HEADERS,
        )
    except HumanAttestationUnavailable as exc:
        logger.warning("human attestation read failed reason=%s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"detail": "Human attestation storage is unavailable."},
            headers=_NO_STORE_HEADERS,
        )
    return Response(
        content=record.body,
        media_type="application/json",
        headers={**_NO_STORE_HEADERS, "ETag": f'"sha256:{record.sha256}"'},
    )


__all__ = ["router"]
