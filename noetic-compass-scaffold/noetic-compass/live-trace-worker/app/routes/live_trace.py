"""Live-trace session endpoints.

POST /sessions                  -> create session, returns id + events URL
GET  /sessions/{id}/events      -> SSE stream of LiveTraceEvent payloads
GET  /sessions/{id}/manifest    -> snapshot manifest (no streaming)
POST /sessions/dump             -> debug helper, returns full event list JSON

The dispatcher in runtime.event_stream.stream_trace picks real vs fake
based on whether get_loaded_model().is_real. Routes here don't care.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..runtime import get_loaded_model, get_manifest, stream_trace
from ..runtime.billing_receipt import (
    WorkerBillingReceiptConfig,
    WorkerBillingReceiptError,
    begin_cuda_measurement,
    finish_cuda_measurement_receipt,
)
from ..schemas.requests import CreateSessionRequest, CreateSessionResponse

router = APIRouter()


_SESSIONS: dict[str, CreateSessionRequest] = {}


# These headers are deliberately scoped to the worker's joined dump endpoint.
# They do not overlap the app-level ``X-Atlas-Worker-Token`` secret or the
# controller callback's ``X-CAS-Service-Nonce`` / lease headers.
JOINED_REQUEST_SHA256_HEADER = "X-CAS-Joined-Request-SHA256"
JOINED_REQUEST_BYTE_LENGTH_HEADER = "X-CAS-Joined-Request-Byte-Length"
JOINED_AUTHORIZATION_SHA256_HEADER = "X-CAS-Joined-Authorization-SHA256"
JOINED_RUN_ID_HEADER = "X-CAS-Joined-Run-ID"
JOINED_INVOCATION_ID_HEADER = "X-CAS-Joined-Invocation-ID"

JOINED_EXECUTION_BINDING_SCHEMA = (
    "cas_harness_live_worker.joined_execution_binding.v1"
)
JOINED_EXECUTION_BINDING_STATUS = "OBSERVED_REQUEST_AND_EVENTS_BOUND"
JOINED_EXECUTION_BINDING_AUTHORITY = "WORKER_PROCESS_OBSERVATION_ONLY"
JOINED_EXECUTION_BINDING_SCOPE = (
    "EXACT_REQUEST_BYTES_AND_CANONICAL_EVENTS_MEMBER_ONLY"
)
JOINED_EXECUTION_BINDING_DIGEST_PROFILE = (
    "UTF8_SORTED_KEYS_COMPACT_JSON_ENSURE_ASCII_FALSE_V1"
)
JOINED_EXECUTION_BINDING_NONCLAIM = (
    "NOT_A_SIGNATURE_OR_TRUSTED_EXECUTION_ATTESTATION"
)
JOINED_MAX_REQUEST_BYTES = 2_000_000

_UPPER_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_MACHINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_INVOCATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
_CANONICAL_LENGTH_RE = re.compile(r"^(?:0|[1-9][0-9]{0,7})$")
_JOINED_HEADERS = (
    JOINED_REQUEST_SHA256_HEADER,
    JOINED_REQUEST_BYTE_LENGTH_HEADER,
    JOINED_AUTHORIZATION_SHA256_HEADER,
    JOINED_RUN_ID_HEADER,
    JOINED_INVOCATION_ID_HEADER,
)


@dataclass(frozen=True, slots=True)
class _JoinedExecutionRequestBinding:
    request_sha256: str
    request_byte_length: int
    authorization_sha256: str
    prospective_run_id: str
    invocation_id_sha256: str


def _canonical_json_bytes(value: object) -> bytes:
    """Canonical bytes used only by the versioned joined-binding profile."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _uppercase_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _joined_header_values(request: Request, name: str) -> list[str]:
    # ``getlist`` keeps duplicate carriers visible. A comma-joined duplicate
    # also fails the field-specific canonical regex below.
    return list(request.headers.getlist(name))


def _load_joined_execution_request_binding(
    *,
    request: Request,
    raw_body: bytes,
    session_request: CreateSessionRequest,
) -> _JoinedExecutionRequestBinding | None:
    """Validate the all-or-none joined headers before any model operation.

    The invocation identifier is caller-generated and may be sensitive. Only
    its digest is retained in the response binding; the raw value is never
    echoed or included in an error.
    """

    carriers = {name: _joined_header_values(request, name) for name in _JOINED_HEADERS}
    present = {name for name, values in carriers.items() if values}
    if not present:
        return None
    if present != set(_JOINED_HEADERS) or any(
        len(carriers[name]) != 1 for name in _JOINED_HEADERS
    ):
        raise HTTPException(
            status_code=400,
            detail="Joined execution binding headers are incomplete or duplicated.",
        )

    request_sha256 = carriers[JOINED_REQUEST_SHA256_HEADER][0]
    byte_length_text = carriers[JOINED_REQUEST_BYTE_LENGTH_HEADER][0]
    authorization_sha256 = carriers[JOINED_AUTHORIZATION_SHA256_HEADER][0]
    prospective_run_id = carriers[JOINED_RUN_ID_HEADER][0]
    invocation_id = carriers[JOINED_INVOCATION_ID_HEADER][0]

    if (
        _UPPER_SHA256_RE.fullmatch(request_sha256) is None
        or _UPPER_SHA256_RE.fullmatch(authorization_sha256) is None
        or _CANONICAL_LENGTH_RE.fullmatch(byte_length_text) is None
        or _MACHINE_ID_RE.fullmatch(prospective_run_id) is None
        or _INVOCATION_ID_RE.fullmatch(invocation_id) is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Joined execution binding headers are invalid.",
        )

    request_byte_length = int(byte_length_text)
    if (
        not 1 <= request_byte_length <= JOINED_MAX_REQUEST_BYTES
        or request_byte_length != len(raw_body)
        or request_sha256 != _uppercase_sha256(raw_body)
    ):
        raise HTTPException(
            status_code=400,
            detail="Joined execution request carrier does not match its declared binding.",
        )

    billing_context = session_request.billing_measurement_context
    if billing_context is not None and billing_context.run_id != prospective_run_id:
        raise HTTPException(
            status_code=400,
            detail="Joined execution run identity conflicts with the request context.",
        )

    return _JoinedExecutionRequestBinding(
        request_sha256=request_sha256,
        request_byte_length=request_byte_length,
        authorization_sha256=authorization_sha256,
        prospective_run_id=prospective_run_id,
        invocation_id_sha256=_uppercase_sha256(invocation_id.encode("ascii")),
    )


def _joined_execution_response_binding(
    request_binding: _JoinedExecutionRequestBinding,
    *,
    events: list[dict],
) -> dict[str, object]:
    """Bind the canonical events member without hashing the enclosing object."""

    events_raw = _canonical_json_bytes(events)
    return {
        "schema_version": JOINED_EXECUTION_BINDING_SCHEMA,
        "status": JOINED_EXECUTION_BINDING_STATUS,
        "authority": JOINED_EXECUTION_BINDING_AUTHORITY,
        "authorization_sha256": request_binding.authorization_sha256,
        "prospective_run_id": request_binding.prospective_run_id,
        "invocation_id_sha256": request_binding.invocation_id_sha256,
        "request_sha256": request_binding.request_sha256,
        "request_byte_length": request_binding.request_byte_length,
        "events_sha256": _uppercase_sha256(events_raw),
        "events_byte_length": len(events_raw),
        "digest_profile": JOINED_EXECUTION_BINDING_DIGEST_PROFILE,
        "binding_scope": JOINED_EXECUTION_BINDING_SCOPE,
        "nonclaim": JOINED_EXECUTION_BINDING_NONCLAIM,
    }


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    try:
        get_manifest(req.model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_id = str(uuid.uuid4())
    _SESSIONS[session_id] = req
    return CreateSessionResponse(
        session_id=session_id,
        events_url=f"/sessions/{session_id}/events",
    )


@router.get("/sessions/{session_id}/manifest")
def session_manifest(session_id: str) -> dict:
    req = _SESSIONS.get(session_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")
    return get_manifest(req.model_id).model_dump()


async def _sse_iter(req: CreateSessionRequest) -> AsyncIterator[bytes]:
    async for event in stream_trace(req):
        payload = event.model_dump_json()
        yield f"event: {event.type}\ndata: {payload}\n\n".encode()


@router.get("/sessions/{session_id}/events")
async def session_events(session_id: str) -> StreamingResponse:
    req = _SESSIONS.get(session_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    return StreamingResponse(
        _sse_iter(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions/dump")
async def dump_session(request: Request, req: CreateSessionRequest) -> dict:
    """Return one non-SSE dump, optionally bound to joined request headers.

    With none of the joined headers, the legacy ``{"events": ...}`` contract
    remains unchanged. With the complete header set, the worker validates the
    exact raw request carrier before model access and returns a closed binding
    over that carrier and the canonical events member. The binding is a worker-
    process observation only, not a signature or trusted execution attestation.
    """
    raw_body = await request.body()
    joined_binding = _load_joined_execution_request_binding(
        request=request,
        raw_body=raw_body,
        session_request=req,
    )
    try:
        get_manifest(req.model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    measurement_clock = None
    receipt_config = None
    if req.billing_measurement_context is not None:
        try:
            receipt_config = WorkerBillingReceiptConfig.from_environment()
            measurement_clock = begin_cuda_measurement(get_loaded_model())
        except WorkerBillingReceiptError as exc:
            raise HTTPException(
                status_code=503,
                detail="Trusted CUDA usage measurement is unavailable.",
            ) from exc

    events: list[dict] = []
    async for event in stream_trace(req):
        events.append(json.loads(event.model_dump_json()))
    response: dict[str, object] = {"events": events}
    if joined_binding is not None:
        response["joined_execution_binding"] = _joined_execution_response_binding(
            joined_binding,
            events=events,
        )
    if measurement_clock is not None and receipt_config is not None:
        try:
            response["billing_measurement_receipt"] = (
                finish_cuda_measurement_receipt(
                    measurement_clock,
                    loaded_model=get_loaded_model(),
                    context=req.billing_measurement_context.model_dump(),
                    config=receipt_config,
                )
            )
        except WorkerBillingReceiptError as exc:
            raise HTTPException(
                status_code=503,
                detail="Trusted CUDA usage measurement is unavailable.",
            ) from exc
    return response
