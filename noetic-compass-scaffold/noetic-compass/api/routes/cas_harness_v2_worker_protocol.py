"""Dark exact-byte HTTP boundary for the prospective Harness-v2 worker protocol.

The route layer authenticates and binds the server-observed HTTP intake, then
hands the *unchanged* request bytes to a lifespan-injected service.  It does not
load the research kernel, invent first-seen authority, authenticate model
execution, establish trusted time, or promote a result beyond
``OPEN / NOT LICENSED / HELD``.

Produced outputs use a separate exact retention envelope before the terminal
callback.  Consequently the terminal endpoint accepts only terminal-receipt
bytes: it never accepts a second authorization body and never supplies an empty
output map on behalf of a successful run.

The HTTP boundary deliberately treats every accepted body as opaque bytes.
Closed-schema, canonical-envelope, strict-carrier, and transitive artifact
validation belong exclusively to the injected adapter.  Main startup refuses
to enable this router without that admitted service boundary.
"""

from __future__ import annotations

import hashlib
import inspect
import logging
import re
from typing import Annotated, Any, Protocol

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import JSONResponse

from api.config import settings
from api.routes.cas_harness_v2_worker_protocol_dto import (
    AuthorizationRouteResultDTO,
    ConsumptionRouteResultDTO,
    EvidencePacketRouteResultDTO,
    NonreportingRouteResultDTO,
    OutputRetentionRouteResultDTO,
    ReconciliationRouteResultDTO,
    TerminalRouteResultDTO,
    WorkerProtocolResultDTOError,
    serialize_exact_route_result,
)
from api.services.fleet_service_auth import (
    FleetServiceAuthenticationError,
    FleetServiceAuthorizationError,
    FleetServiceAuthError,
    FleetServiceAuthStore,
    FleetServiceBoundIntakeReceipt,
    FleetServiceIntakeBinding,
)


router = APIRouter(
    prefix="/api/cas-harness/audit/distributed",
    tags=["cas-harness-v2-worker-protocol"],
    include_in_schema=False,
)
logger = logging.getLogger(__name__)

MAX_EXACT_BODY_BYTES = 2_000_000
MIN_LEASE_TOKEN_BYTES = 32
MAX_LEASE_TOKEN_BYTES = 256
ROUTE_ID_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
_UPPER_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")

ISSUE_REQUEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.worker-authorization-request+json"
)
OUTPUT_RETENTION_MEDIA_TYPE = (
    "application/vnd.cas-harness.output-retention+json"
)
CONSUMPTION_MEDIA_TYPE = "application/vnd.cas-harness.run-consumption+json"
TERMINAL_MEDIA_TYPE = (
    "application/vnd.cas-harness.worker-terminal-receipt+json"
)
EVIDENCE_PACKET_MEDIA_TYPE = "application/vnd.cas-harness.evidence-packet+json"
NONREPORTING_MEDIA_TYPE = "application/vnd.cas-harness.nonreporting-request+json"
RECONCILIATION_MEDIA_TYPE = "application/vnd.cas-harness.reconciliation-request+json"

_AUTHORITY = {
    "criteria_status": "OPEN",
    "execution_authentication": "NOT_ESTABLISHED",
    "trusted_time": "NOT_ESTABLISHED",
    "worm_authority": "NOT_ESTABLISHED",
    "independent_authority": "NOT_ESTABLISHED",
    "scientific_status": "NOT_ESTABLISHED",
    "product_status": "NOT_ESTABLISHED",
    "license_status": "NOT LICENSED",
    "disclosure_status": "HELD",
}


class HarnessV2WorkerProtocolRouteService(Protocol):
    """Lifespan-injected adapter; the underlying orchestrator may evolve."""

    def issue_authorization(self, **kwargs: Any) -> AuthorizationRouteResultDTO: ...

    def retain_output(self, **kwargs: Any) -> OutputRetentionRouteResultDTO: ...

    def consume_authorization(self, **kwargs: Any) -> ConsumptionRouteResultDTO: ...

    def accept_terminal(self, **kwargs: Any) -> TerminalRouteResultDTO: ...

    def attach_evidence_packet(self, **kwargs: Any) -> EvidencePacketRouteResultDTO: ...

    def record_nonreporting(self, **kwargs: Any) -> NonreportingRouteResultDTO: ...

    def reconcile_run(self, **kwargs: Any) -> ReconciliationRouteResultDTO: ...


class WorkerProtocolRouteError(RuntimeError):
    """Base error an injected route adapter may expose safely by class."""


class WorkerProtocolRouteRejected(WorkerProtocolRouteError):
    """Exact scope, carrier, or lifecycle binding was rejected."""


class WorkerProtocolRouteConflict(WorkerProtocolRouteRejected):
    """An immutable fact or one-use transition conflicts."""


class WorkerProtocolRouteNotFound(WorkerProtocolRouteRejected):
    """A required prospective artifact or lifecycle does not exist."""


class WorkerProtocolRouteUnavailable(WorkerProtocolRouteError):
    """A required durable or immutable authority is unavailable."""


def prospective_run_id(job_id: str) -> str:
    """Return the registry's deterministic run identity for one job subject."""

    return "h2run_" + hashlib.sha256(job_id.encode("utf-8")).hexdigest()


def _route_service(request: Request) -> HarnessV2WorkerProtocolRouteService:
    if not settings.harness_v2_worker_protocol_enabled:
        # Stay indistinguishable from an unregistered route while dark.
        raise HTTPException(status_code=404, detail="Not Found")
    if not settings.accounts_enabled or not settings.fleet_service_auth_enabled:
        raise HTTPException(
            status_code=503,
            detail="Harness-v2 worker protocol prerequisites are unavailable.",
        )
    service = getattr(
        request.app.state, "cas_harness_v2_worker_protocol_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Harness-v2 worker protocol service is unavailable.",
        )
    return service


def _fleet_auth_store(request: Request) -> FleetServiceAuthStore:
    injected = getattr(request.app.state, "fleet_service_auth_store", None)
    if injected is not None:
        return injected
    shared_store = getattr(request.app.state, "shared_state_store", None)
    if shared_store is None:
        raise HTTPException(
            status_code=503,
            detail="Fleet service authentication is unavailable.",
        )
    try:
        return FleetServiceAuthStore(
            shared_store,
            pepper=settings.fleet_service_credential_pepper,
            max_clock_skew_seconds=settings.fleet_service_max_clock_skew_seconds,
        )
    except FleetServiceAuthError as exc:
        raise HTTPException(
            status_code=503,
            detail="Fleet service authentication is unavailable.",
        ) from exc


async def _read_exact_body(request: Request, *, media_type: str) -> bytes:
    if request.url.query:
        raise HTTPException(status_code=400, detail="Query parameters are not accepted.")
    if request.headers.get("Content-Encoding", "").strip() not in {"", "identity"}:
        raise HTTPException(status_code=415, detail="Content encoding is not accepted.")
    if request.headers.get("Content-Type", "") != media_type:
        raise HTTPException(status_code=415, detail="Unsupported exact carrier media type.")

    declared_length = request.headers.get("Content-Length")
    if declared_length is not None:
        try:
            parsed_length = int(declared_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length.") from exc
        if parsed_length < 0:
            raise HTTPException(status_code=400, detail="Invalid Content-Length.")
        if parsed_length > MAX_EXACT_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Exact carrier exceeds 2,000,000 bytes.")

    captured = bytearray()
    async for chunk in request.stream():
        if len(captured) + len(chunk) > MAX_EXACT_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Exact carrier exceeds 2,000,000 bytes.")
        captured.extend(chunk)
    raw = bytes(captured)
    if not raw:
        raise HTTPException(status_code=422, detail="Exact carrier body is required.")
    if declared_length is not None and int(declared_length) != len(raw):
        raise HTTPException(
            status_code=400,
            detail="Content-Length does not match the exact body.",
        )
    return raw


def _authorization_digest(request: Request, *, required: bool) -> str | None:
    value = request.headers.get("X-CAS-Authorization-SHA256", "")
    if not required:
        if value:
            raise HTTPException(
                status_code=422,
                detail=(
                    "X-CAS-Authorization-SHA256 is forbidden before server-side "
                    "authorization issuance."
                ),
            )
        return None
    if not _UPPER_SHA256_RE.fullmatch(value):
        raise HTTPException(
            status_code=422,
            detail="X-CAS-Authorization-SHA256 must be uppercase SHA-256.",
        )
    return value


def _lease_token(
    request: Request,
    *,
    required: bool,
) -> tuple[str | None, str | None]:
    values = request.headers.getlist("X-CAS-Lease-Token")
    if not required:
        if values:
            raise HTTPException(
                status_code=422,
                detail="X-CAS-Lease-Token is forbidden on controller operations.",
            )
        return None, None
    if len(values) != 1:
        raise HTTPException(
            status_code=422,
            detail=(
                "X-CAS-Lease-Token must be one opaque 32-256 byte secret."
            ),
        )
    value = values[0]
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise HTTPException(
            status_code=422,
            detail=(
                "X-CAS-Lease-Token must be one opaque 32-256 byte secret."
            ),
        ) from None
    if (
        not MIN_LEASE_TOKEN_BYTES <= len(encoded) <= MAX_LEASE_TOKEN_BYTES
        or value != value.strip()
        or any(
            character.isspace()
            or ord(character) < 0x20
            or ord(character) == 0x7F
            for character in value
        )
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "X-CAS-Lease-Token must be one opaque 32-256 byte secret."
            ),
        )
    return value, hashlib.sha256(encoded).hexdigest().upper()


def _authenticate_intake(
    request: Request,
    *,
    audit_id: str,
    job_id: str,
    worker_id: str | None,
    capability: str,
    raw: bytes,
    authorization_sha256: str | None,
    lease_token_sha256: str | None,
) -> FleetServiceBoundIntakeReceipt:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("CAS-Service ") or not authorization[12:]:
        raise HTTPException(status_code=401, detail="Invalid fleet service credential.")
    if request.headers.get("X-CAS-Audit-ID", "") != audit_id:
        raise HTTPException(status_code=403, detail="Fleet service scope denied.")
    try:
        binding = FleetServiceIntakeBinding(
            http_method="POST",
            route_path=request.url.path,
            job_id=job_id,
            run_id=prospective_run_id(job_id),
            authorization_sha256=authorization_sha256,
            lease_token_sha256=lease_token_sha256,
            carrier_sha256=hashlib.sha256(raw).hexdigest().upper(),
            carrier_byte_length=len(raw),
        )
        auth_store = _fleet_auth_store(request)
        receipt = auth_store.authenticate_with_bound_intake_receipt(
            tenant_id=request.headers.get("X-CAS-Tenant-ID", ""),
            api_credential=authorization[len("CAS-Service ") :],
            timestamp=request.headers.get("X-CAS-Service-Timestamp", ""),
            nonce=request.headers.get("X-CAS-Service-Nonce", ""),
            required_capability=capability,
            audit_id=audit_id,
            fleet_id=audit_id,
            worker_id=worker_id,
            intake_binding=binding,
        )
        if type(receipt) is not FleetServiceBoundIntakeReceipt:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        verified = auth_store.verify_bound_intake_receipt(receipt)
        if verified is not receipt or receipt.intake_binding != binding:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
    except FleetServiceAuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Invalid fleet service credential.") from exc
    except FleetServiceAuthorizationError as exc:
        raise HTTPException(status_code=403, detail="Fleet service scope denied.") from exc
    except FleetServiceAuthError as exc:
        raise HTTPException(
            status_code=503,
            detail="Fleet service authentication is unavailable.",
        ) from exc
    return receipt


async def _invoke_service(
    service: HarnessV2WorkerProtocolRouteService,
    *,
    operation: str,
    optional: bool,
    receipt: FleetServiceBoundIntakeReceipt,
    audit_id: str,
    job_id: str,
    worker_id: str | None,
    raw: bytes,
    media_type: str,
    lease_token: str | None,
) -> dict[str, object]:
    handler = getattr(service, operation, None)
    if not callable(handler):
        status = 501 if optional else 503
        raise HTTPException(
            status_code=status,
            detail="Harness-v2 worker protocol operation is unavailable.",
        )
    principal = receipt.callback.principal
    try:
        service_kwargs: dict[str, Any] = {
            "tenant_id": principal.tenant_id,
            "account_id": principal.account_id,
            "audit_id": audit_id,
            "fleet_id": principal.fleet_id,
            "job_id": job_id,
            "run_id": prospective_run_id(job_id),
            "worker_id": worker_id,
            "raw_body": raw,
            "body_media_type": media_type,
            "authenticated_callback": receipt.callback,
            "bound_intake_receipt": receipt,
        }
        if lease_token is not None:
            # This is the sole raw-secret handoff.  It remains process-local and
            # is never placed in the bound receipt, route response, or a log.
            service_kwargs["lease_token"] = lease_token
        result = handler(
            **service_kwargs,
        )
        if inspect.isawaitable(result):
            result = await result
    except WorkerProtocolRouteNotFound:
        raise HTTPException(
            status_code=404,
            detail="Harness-v2 worker protocol resource was not found.",
        ) from None
    except (WorkerProtocolRouteConflict, WorkerProtocolRouteRejected):
        raise HTTPException(
            status_code=409,
            detail="Harness-v2 worker protocol request conflicts with current state.",
        ) from None
    except WorkerProtocolRouteUnavailable:
        raise HTTPException(
            status_code=503,
            detail="Harness-v2 worker protocol service is unavailable.",
        ) from None
    except Exception as exc:
        logger.error(
            "Harness-v2 worker protocol service failed closed operation=%s error_type=%s",
            operation,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Harness-v2 worker protocol service failed closed.",
        ) from None
    try:
        safe_result = serialize_exact_route_result(operation, result)
    except WorkerProtocolResultDTOError:
        raise HTTPException(
            status_code=503,
            detail="Harness-v2 worker protocol service returned an invalid result.",
        ) from None
    if lease_token is not None and any(
        isinstance(value, str) and lease_token in value
        for value in safe_result.values()
    ):
        raise HTTPException(
            status_code=503,
            detail="Harness-v2 worker protocol service returned an invalid result.",
        )
    return safe_result


async def _handle(
    request: Request,
    *,
    audit_id: str,
    job_id: str,
    worker_id: str | None,
    operation: str,
    capability: str,
    media_type: str,
    authorization_digest_required: bool,
    lease_token_required: bool,
    optional_operation: bool = False,
) -> JSONResponse:
    service = _route_service(request)
    raw = await _read_exact_body(request, media_type=media_type)
    authorization_sha256 = _authorization_digest(
        request, required=authorization_digest_required
    )
    lease_token, lease_token_sha256 = _lease_token(
        request, required=lease_token_required
    )
    receipt = _authenticate_intake(
        request,
        audit_id=audit_id,
        job_id=job_id,
        worker_id=worker_id,
        capability=capability,
        raw=raw,
        authorization_sha256=authorization_sha256,
        lease_token_sha256=lease_token_sha256,
    )
    result = await _invoke_service(
        service,
        operation=operation,
        optional=optional_operation,
        receipt=receipt,
        audit_id=audit_id,
        job_id=job_id,
        worker_id=worker_id,
        raw=raw,
        media_type=media_type,
        lease_token=lease_token,
    )
    binding = receipt.intake_binding
    return JSONResponse(
        status_code=200,
        headers={"Cache-Control": "no-store"},
        content={
            "status": "ACCEPTED_RESEARCH_ONLY",
            "operation": operation,
            "audit_id": audit_id,
            "job_id": job_id,
            "run_id": binding.run_id,
            "intake_receipt": {
                "nonce_id": receipt.callback.nonce_receipt.nonce_id,
                "carrier_sha256": binding.carrier_sha256,
                "carrier_byte_length": binding.carrier_byte_length,
                "scope": "SERVER_OBSERVED_HTTP_INTAKE_ONLY",
            },
            "result": result,
            "authority": dict(_AUTHORITY),
        },
    )


RouteId = Annotated[str, Path(pattern=f"^{ROUTE_ID_PATTERN}$")]


@router.post("/session/{audit_id}/fleet/v2/job/{job_id}/authorization")
async def issue_authorization(
    request: Request, audit_id: RouteId, job_id: RouteId
) -> JSONResponse:
    return await _handle(
        request,
        audit_id=audit_id,
        job_id=job_id,
        worker_id=None,
        operation="issue_authorization",
        capability="merge_fleet",
        media_type=ISSUE_REQUEST_MEDIA_TYPE,
        authorization_digest_required=False,
        lease_token_required=False,
    )


@router.post("/session/{audit_id}/fleet/v2/job/{job_id}/worker/{worker_id}/output")
async def retain_output(
    request: Request, audit_id: RouteId, job_id: RouteId, worker_id: RouteId
) -> JSONResponse:
    return await _handle(
        request,
        audit_id=audit_id,
        job_id=job_id,
        worker_id=worker_id,
        operation="retain_output",
        capability="submit_evidence",
        media_type=OUTPUT_RETENTION_MEDIA_TYPE,
        authorization_digest_required=True,
        lease_token_required=True,
    )


@router.post("/session/{audit_id}/fleet/v2/job/{job_id}/worker/{worker_id}/consume")
async def consume_authorization(
    request: Request, audit_id: RouteId, job_id: RouteId, worker_id: RouteId
) -> JSONResponse:
    return await _handle(
        request,
        audit_id=audit_id,
        job_id=job_id,
        worker_id=worker_id,
        operation="consume_authorization",
        capability="lease_job",
        media_type=CONSUMPTION_MEDIA_TYPE,
        authorization_digest_required=True,
        lease_token_required=True,
    )


@router.post("/session/{audit_id}/fleet/v2/job/{job_id}/worker/{worker_id}/terminal")
async def accept_terminal(
    request: Request, audit_id: RouteId, job_id: RouteId, worker_id: RouteId
) -> JSONResponse:
    return await _handle(
        request,
        audit_id=audit_id,
        job_id=job_id,
        worker_id=worker_id,
        operation="accept_terminal",
        capability="submit_receipt",
        media_type=TERMINAL_MEDIA_TYPE,
        authorization_digest_required=True,
        lease_token_required=True,
    )


@router.post("/session/{audit_id}/fleet/v2/job/{job_id}/packet")
async def attach_evidence_packet(
    request: Request, audit_id: RouteId, job_id: RouteId
) -> JSONResponse:
    return await _handle(
        request,
        audit_id=audit_id,
        job_id=job_id,
        worker_id=None,
        operation="attach_evidence_packet",
        capability="merge_fleet",
        media_type=EVIDENCE_PACKET_MEDIA_TYPE,
        authorization_digest_required=True,
        lease_token_required=False,
        optional_operation=True,
    )


@router.post("/session/{audit_id}/fleet/v2/job/{job_id}/nonreporting")
async def record_nonreporting(
    request: Request, audit_id: RouteId, job_id: RouteId
) -> JSONResponse:
    return await _handle(
        request,
        audit_id=audit_id,
        job_id=job_id,
        worker_id=None,
        operation="record_nonreporting",
        capability="merge_fleet",
        media_type=NONREPORTING_MEDIA_TYPE,
        authorization_digest_required=True,
        lease_token_required=False,
        optional_operation=True,
    )


@router.post("/session/{audit_id}/fleet/v2/job/{job_id}/reconcile")
async def reconcile_run(
    request: Request, audit_id: RouteId, job_id: RouteId
) -> JSONResponse:
    return await _handle(
        request,
        audit_id=audit_id,
        job_id=job_id,
        worker_id=None,
        operation="reconcile_run",
        capability="verify_fleet",
        media_type=RECONCILIATION_MEDIA_TYPE,
        authorization_digest_required=True,
        lease_token_required=False,
        optional_operation=True,
    )
