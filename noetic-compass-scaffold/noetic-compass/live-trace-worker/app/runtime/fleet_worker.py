"""CAS Harness fleet worker daemon.

This module is the worker-side bridge for enterprise distributed audits. It
does not plan audits and it does not fabricate verifier decisions. Its job is
small and strict:

1. register this worker with the noetic-compass-api control plane;
2. heartbeat and lease an assigned layer/shard job;
3. run the configured probe executor for that job;
4. write a local Evidence Packet fragment payload;
5. post the content-addressed receipt back to the API.

The dry-run executor exists only for deployment/control-plane verification.
Production workers should use ``CommandFleetJobExecutor`` to call the actual
model/probe command for the assigned shard.
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any, Literal, Protocol

import httpx


FleetJobStatus = Literal["queued", "leased", "completed", "failed", "expired"]
FleetWorkerResultStatus = Literal["idle", "completed", "failed"]

HARNESS_V2_CONSUMPTION_REQUEST_SCHEMA = (
    "cas_harness_v2.route_consumption_request.v1"
)
HARNESS_V2_OUTPUT_RETENTION_SCHEMA = "cas_harness_v2.output_retention.v1"
HARNESS_V2_CONSUMPTION_MEDIA_TYPE = (
    "application/vnd.cas-harness.run-consumption+json"
)
HARNESS_V2_OUTPUT_RETENTION_MEDIA_TYPE = (
    "application/vnd.cas-harness.output-retention+json"
)
HARNESS_V2_TERMINAL_MEDIA_TYPE = (
    "application/vnd.cas-harness.worker-terminal-receipt+json"
)

_HARNESS_V2_ROUTE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_HARNESS_V2_RUN_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_HARNESS_V2_UPPER_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_HARNESS_V2_CREDENTIAL_ID_RE = re.compile(r"^fsc_[0-9a-f]{32}$")
_HARNESS_V2_MAX_EXACT_BODY_BYTES = 2_000_000
_HARNESS_V2_MAX_ARTIFACT_BYTES = 1_500_000
_HARNESS_V2_MAX_MEDIA_TYPE_BYTES = 255
_HARNESS_V2_MAX_RESPONSE_BYTES = 128_000
_HARNESS_V2_FAILURE = "Harness-v2 worker protocol request failed closed."
_HARNESS_V2_AUTHORITY = {
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

_HARNESS_V2_RESPONSE_OPERATIONS = {
    "consume": "consume_authorization",
    "output": "retain_output",
    "terminal": "accept_terminal",
}

_HARNESS_V2_RESULT_CONTRACTS = {
    "consume": (
        "cas_harness_v2.consumption_route_result.v1",
        "AUTHORIZATION_CONSUMPTION",
    ),
    "output": (
        "cas_harness_v2.output_route_result.v1",
        "OUTPUT_RETENTION",
    ),
    "terminal": (
        "cas_harness_v2.terminal_route_result.v1",
        "TERMINAL_ACCEPTANCE",
    ),
}

_BOUND_MODEL_ENV_KEYS = frozenset(
    {
        "CAS_FLEET_MODEL_ID",
        "CAS_FLEET_MODEL_REVISION",
        "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH",
        "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256",
        "CAS_FLEET_TRUST_REMOTE_CODE",
    }
)


class FleetWorkerError(RuntimeError):
    """Raised when the worker cannot complete a fleet protocol step."""


class HarnessV2WorkerPreSendFailure(FleetWorkerError):
    """Local validation failed before any Harness-v2 HTTP attempt began."""

    outcome_certainty = "DEFINITE_PRE_SEND_FAILURE"
    reconcile_only = False
    retry_allowed = False


class HarnessV2WorkerPostSendIndeterminate(FleetWorkerError):
    """An entered Harness-v2 HTTP attempt has no fully bound success receipt."""

    outcome_certainty = "POST_SEND_INDETERMINATE"
    reconcile_only = True
    retry_allowed = False


class _HarnessV2ResponseError(ValueError):
    """Private response-contract failure; never surface its detail to callers."""


@dataclass(frozen=True, slots=True)
class _HarnessV2ExpectedResult:
    receipt_id: str | None = None
    receipt_sha256: str | None = None
    receipt_media_type: str | None = None
    receipt_byte_length: int | None = None
    terminal_status: str | None = None


@dataclass(frozen=True)
class FleetWorkerConfig:
    """Runtime settings for one Probe Worker daemon."""

    api_base_url: str
    audit_id: str
    worker_id: str
    model_id: str
    worker_url: str
    gpu_type: str
    supported_methods: tuple[str, ...]
    # Account-mode machine identity. The API returns this value once at issuance; keep it in the
    # worker secret store, never a browser or customer JWT. ``bearer_token`` is legacy/dark mode.
    tenant_id: str | None = None
    service_credential: str | None = field(default=None, repr=False)
    bearer_token: str | None = field(default=None, repr=False)
    capacity: int = 1
    lease_seconds: int = 900
    poll_interval_seconds: float = 5.0
    max_jobs: int | None = None
    evidence_dir: Path = field(default_factory=lambda: Path("fleet-evidence"))

    def __post_init__(self) -> None:
        if not self.api_base_url.strip():
            raise ValueError("api_base_url is required")
        if not self.audit_id.strip():
            raise ValueError("audit_id is required")
        if not self.worker_id.strip():
            raise ValueError("worker_id is required")
        if not self.model_id.strip():
            raise ValueError("model_id is required")
        if not self.worker_url.strip():
            raise ValueError("worker_url is required")
        if not self.gpu_type.strip():
            raise ValueError("gpu_type is required")
        if not self.supported_methods:
            raise ValueError("supported_methods must not be empty")
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if self.lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        if self.poll_interval_seconds < 0:
            raise ValueError("poll_interval_seconds must be non-negative")
        if self.service_credential and not (self.tenant_id or "").strip():
            raise ValueError("tenant_id is required with service_credential")
        if self.tenant_id and not (self.service_credential or "").strip():
            raise ValueError("service_credential is required with tenant_id")
        if self.service_credential and self.bearer_token:
            raise ValueError("choose service_credential or legacy bearer_token, not both")

    @property
    def base_url(self) -> str:
        return self.api_base_url.rstrip("/")


@dataclass(frozen=True)
class FleetJob:
    job_id: str
    audit_id: str
    assigned_worker_id: str
    layer_start: int
    layer_end: int
    shard_id: str
    assigned_methods: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    lease_token: str
    model_id: str | None = None
    model_revision: str | None = None
    model_artifact_manifest_path: str | None = None
    model_artifact_manifest_sha256: str | None = None
    execution_mode: str | None = None
    status: FleetJobStatus = "leased"

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "FleetJob":
        lease_token = str(payload.get("lease_token") or "").strip()
        if not lease_token:
            raise FleetWorkerError("Lease response did not include a lease_token.")
        return cls(
            job_id=str(payload["job_id"]),
            audit_id=str(payload["audit_id"]),
            assigned_worker_id=str(payload["assigned_worker_id"]),
            layer_start=int(payload["layer_start"]),
            layer_end=int(payload["layer_end"]),
            shard_id=str(payload["shard_id"]),
            assigned_methods=tuple(str(item) for item in payload["assigned_methods"]),
            expected_outputs=tuple(str(item) for item in payload["expected_outputs"]),
            lease_token=lease_token,
            model_id=_optional_clean_text(payload.get("model_id")),
            model_revision=_optional_clean_text(payload.get("model_revision")),
            model_artifact_manifest_path=_optional_clean_text(
                payload.get("model_artifact_manifest_path")
            ),
            model_artifact_manifest_sha256=_optional_clean_text(
                payload.get("model_artifact_manifest_sha256")
            ),
            execution_mode=_optional_clean_text(payload.get("execution_mode")),
            status=payload.get("status", "leased"),
        )


@dataclass(frozen=True)
class FleetJobExecutionResult:
    produced_outputs: tuple[str, ...]
    missing_outputs: tuple[str, ...] = ()
    error_message: str | None = None
    evidence_payload: dict[str, Any] | None = None

    @property
    def status(self) -> Literal["completed", "failed"]:
        return "failed" if self.error_message else "completed"


@dataclass(frozen=True)
class FleetWorkerRunResult:
    status: FleetWorkerResultStatus
    job_id: str | None = None
    evidence_packet_fragment_ref: str | None = None
    error_message: str | None = None


class FleetJobExecutor(Protocol):
    execution_mode: str

    async def run(self, job: FleetJob, config: FleetWorkerConfig) -> FleetJobExecutionResult:
        """Execute a leased job and return the produced/missing outputs."""


class DryRunFleetJobExecutor:
    """Control-plane verification executor.

    This intentionally does not claim model inference. It is useful for
    verifying registration, leasing, receipt, hash, and merge gates on a
    deployment before real model workers are attached.
    """

    execution_mode = "dry_run_control_plane"

    async def run(self, job: FleetJob, config: FleetWorkerConfig) -> FleetJobExecutionResult:
        return FleetJobExecutionResult(produced_outputs=job.expected_outputs)


class CommandFleetJobExecutor:
    """Run a real probe command for a leased shard.

    The command is executed without a shell. It receives job metadata through
    environment variables and must write JSON to ``CAS_FLEET_RESULT_PATH``:

    ``{"produced_outputs": [...], "missing_outputs": [...], "error_message": null}``
    """

    execution_mode = "external_probe_command"

    def __init__(self, command: tuple[str, ...], *, timeout_seconds: int = 3600) -> None:
        if not command:
            raise ValueError("command must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.command = command
        self.timeout_seconds = timeout_seconds

    async def run(self, job: FleetJob, config: FleetWorkerConfig) -> FleetJobExecutionResult:
        config.evidence_dir.mkdir(parents=True, exist_ok=True)
        result_path = config.evidence_dir / f"{job.job_id}.probe-result.json"
        try:
            model_id, revision, manifest_path, manifest_sha256 = _bound_model_identity(
                job,
                config,
            )
        except FleetWorkerError as exc:
            return FleetJobExecutionResult(
                produced_outputs=(),
                missing_outputs=job.expected_outputs,
                error_message=str(exc),
            )
        try:
            result_path.unlink(missing_ok=True)
        except OSError as exc:
            return FleetJobExecutionResult(
                produced_outputs=(),
                missing_outputs=job.expected_outputs,
                error_message=f"Could not clear stale probe result before execution: {exc}",
            )
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper() not in _BOUND_MODEL_ENV_KEYS
        }
        env.update(
            {
                "CAS_FLEET_AUDIT_ID": job.audit_id,
                "CAS_FLEET_JOB_ID": job.job_id,
                "CAS_FLEET_WORKER_ID": config.worker_id,
                "CAS_FLEET_MODEL_ID": model_id,
                "CAS_FLEET_MODEL_REVISION": revision,
                "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH": manifest_path,
                "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256": manifest_sha256,
                "CAS_FLEET_TRUST_REMOTE_CODE": "false",
                "CAS_FLEET_LAYER_START": str(job.layer_start),
                "CAS_FLEET_LAYER_END": str(job.layer_end),
                "CAS_FLEET_SHARD_ID": job.shard_id,
                "CAS_FLEET_ASSIGNED_METHODS_JSON": json.dumps(list(job.assigned_methods)),
                "CAS_FLEET_EXPECTED_OUTPUTS_JSON": json.dumps(list(job.expected_outputs)),
                "CAS_FLEET_RESULT_PATH": str(result_path),
            }
        )
        process = await asyncio.create_subprocess_exec(
            *self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout_seconds)
        except TimeoutError:
            process.kill()
            await process.communicate()
            return FleetJobExecutionResult(
                produced_outputs=(),
                missing_outputs=job.expected_outputs,
                error_message=f"Probe command timed out after {self.timeout_seconds} seconds.",
            )
        if process.returncode != 0:
            return FleetJobExecutionResult(
                produced_outputs=(),
                missing_outputs=job.expected_outputs,
                error_message=_truncate_text(
                    stderr.decode("utf-8", errors="replace") or stdout.decode("utf-8", errors="replace")
                ),
            )
        if not result_path.exists():
            return FleetJobExecutionResult(
                produced_outputs=(),
                missing_outputs=job.expected_outputs,
                error_message="Probe command did not write CAS_FLEET_RESULT_PATH.",
            )
        return _parse_command_result(result_path, job)


class FleetApiClient:
    """Small async client for the noetic-compass-api fleet endpoints."""

    def __init__(
        self,
        config: FleetWorkerConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=60.0)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def register_worker(self) -> dict[str, Any]:
        payload = {
            "worker_id": self.config.worker_id,
            "model_id": self.config.model_id,
            "worker_url": self.config.worker_url,
            "gpu_type": self.config.gpu_type,
            "capacity": self.config.capacity,
            "supported_methods": list(self.config.supported_methods),
        }
        try:
            return await self._post("/api/cas-harness/audit/distributed/fleet/worker/register", payload)
        except FleetWorkerError as exc:
            if "already registered" not in str(exc):
                raise
            return await self.heartbeat()

    async def heartbeat(self) -> dict[str, Any]:
        return await self._post(
            f"/api/cas-harness/audit/distributed/fleet/worker/{self.config.worker_id}/heartbeat",
            None,
        )

    async def lease_job(self) -> FleetJob | None:
        payload = {
            "worker_id": self.config.worker_id,
            "lease_seconds": self.config.lease_seconds,
        }
        response = await self._post(
            f"/api/cas-harness/audit/distributed/session/{self.config.audit_id}/fleet/job/lease",
            payload,
        )
        if response is None:
            return None
        return FleetJob.from_api(response)

    async def submit_receipt(
        self,
        job: FleetJob,
        result: FleetJobExecutionResult,
        *,
        evidence_packet_fragment_ref: str | None,
        execution_mode: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "worker_id": self.config.worker_id,
            "lease_token": job.lease_token,
            "produced_outputs": list(result.produced_outputs),
            "missing_outputs": list(result.missing_outputs),
            "job_status": result.status,
            "execution_mode": execution_mode,
        }
        if result.status == "completed":
            payload["evidence_packet_fragment_ref"] = evidence_packet_fragment_ref
            if result.evidence_payload is not None:
                # The API independently recomputes the fragment ref with these
                # bytes included.  Omitting this field would let a rich local
                # fragment collapse to an assignment-only receipt.
                payload["evidence_packet_fragment_payload"] = result.evidence_payload
        else:
            payload["error_message"] = result.error_message or "Probe worker failed."
        return await self._post(
            f"/api/cas-harness/audit/distributed/session/{self.config.audit_id}/fleet/job/{job.job_id}/receipt",
            payload,
        )

    async def consume_harness_v2_authorization(
        self,
        job: FleetJob,
        *,
        authorization_sha256: str,
        run_nonce_b64url: str,
    ) -> dict[str, Any]:
        """Consume one authorization before any Harness-v2 model execution."""

        raw = build_harness_v2_consumption_request(run_nonce_b64url)
        return await self._post_harness_v2_worker_exact(
            job,
            operation="consume",
            raw=raw,
            media_type=HARNESS_V2_CONSUMPTION_MEDIA_TYPE,
            authorization_sha256=authorization_sha256,
            expected_result=_HarnessV2ExpectedResult(
                receipt_id=_harness_v2_operation_id("consumption", job.job_id),
            ),
        )

    async def retain_harness_v2_output(
        self,
        job: FleetJob,
        *,
        authorization_sha256: str,
        output_name: str,
        artifact_id: str,
        artifact_media_type: str,
        artifact_body: bytes | bytearray | memoryview,
    ) -> dict[str, Any]:
        """Retain one exact output after consumption and before terminal submission."""

        raw = build_harness_v2_output_retention_request(
            output_name=output_name,
            artifact_id=artifact_id,
            artifact_media_type=artifact_media_type,
            artifact_body=artifact_body,
        )
        return await self._post_harness_v2_worker_exact(
            job,
            operation="output",
            raw=raw,
            media_type=HARNESS_V2_OUTPUT_RETENTION_MEDIA_TYPE,
            authorization_sha256=authorization_sha256,
            expected_result=_HarnessV2ExpectedResult(
                receipt_id=artifact_id,
                receipt_sha256=hashlib.sha256(bytes(artifact_body)).hexdigest().upper(),
            ),
        )

    async def submit_harness_v2_terminal(
        self,
        job: FleetJob,
        *,
        authorization_sha256: str,
        terminal_receipt_raw: bytes | bytearray | memoryview,
    ) -> dict[str, Any]:
        """Submit exact terminal-receipt bytes after all outputs are retained."""

        raw = _snapshot_harness_v2_exact_body(terminal_receipt_raw)
        receipt_id, terminal_status = _terminal_result_binding(raw)
        return await self._post_harness_v2_worker_exact(
            job,
            operation="terminal",
            raw=raw,
            media_type=HARNESS_V2_TERMINAL_MEDIA_TYPE,
            authorization_sha256=authorization_sha256,
            expected_result=_HarnessV2ExpectedResult(
                receipt_id=receipt_id,
                receipt_sha256=hashlib.sha256(raw).hexdigest().upper(),
                receipt_media_type=HARNESS_V2_TERMINAL_MEDIA_TYPE,
                receipt_byte_length=len(raw),
                terminal_status=terminal_status,
            ),
        )

    async def _post_harness_v2_worker_exact(
        self,
        job: FleetJob,
        *,
        operation: Literal["consume", "output", "terminal"],
        raw: bytes,
        media_type: str,
        authorization_sha256: str,
        expected_result: _HarnessV2ExpectedResult,
    ) -> dict[str, Any]:
        """Perform one exact worker-scoped attempt with no automatic retry."""

        tenant_id, service_credential, credential_id = (
            self._harness_v2_service_identity()
        )
        path, lease_token = self._harness_v2_worker_path(job, operation=operation)
        if (
            type(authorization_sha256) is not str
            or not _HARNESS_V2_UPPER_SHA256_RE.fullmatch(authorization_sha256)
        ):
            raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
        raw = _snapshot_harness_v2_exact_body(raw)
        request_sha256 = hashlib.sha256(raw).hexdigest().upper()
        callback_nonce = secrets.token_urlsafe(24)
        expected_nonce_id = "fsn_" + hashlib.sha256(
            f"{credential_id}:{callback_nonce}".encode("utf-8")
        ).hexdigest()
        headers = {
            "Authorization": f"CAS-Service {service_credential}",
            "Content-Type": media_type,
            "X-CAS-Tenant-ID": tenant_id,
            "X-CAS-Audit-ID": job.audit_id,
            "X-CAS-Service-Timestamp": str(int(datetime.now(UTC).timestamp())),
            "X-CAS-Service-Nonce": callback_nonce,
            "X-CAS-Authorization-SHA256": authorization_sha256,
            "X-CAS-Lease-Token": lease_token,
        }
        try:
            # Entering the transport is the certainty boundary. Any exception,
            # non-200, or malformed/mismatched success after this point may
            # follow a committed server-side transition. It is therefore
            # reconcile-only and never an automatic retry signal.
            async with self._client.stream(
                "POST",
                f"{self.config.base_url}{path}",
                content=raw,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    raise _HarnessV2ResponseError("non-success status")
                response_raw = await _read_harness_v2_response(response)
            payload = _load_harness_v2_json_object(response_raw)
            _validate_harness_v2_worker_response(
                payload,
                operation=operation,
                job=job,
                request_sha256=request_sha256,
                request_byte_length=len(raw),
                expected_nonce_id=expected_nonce_id,
                expected_result=expected_result,
            )
        except asyncio.CancelledError:
            raise HarnessV2WorkerPostSendIndeterminate(_HARNESS_V2_FAILURE) from None
        except Exception:
            raise HarnessV2WorkerPostSendIndeterminate(_HARNESS_V2_FAILURE) from None
        return payload

    def _harness_v2_service_identity(self) -> tuple[str, str, str]:
        tenant_id = (self.config.tenant_id or "").strip()
        service_credential = (self.config.service_credential or "").strip()
        credential_id = None
        if service_credential.startswith("casfs_") and "." in service_credential:
            head, secret = service_credential[len("casfs_") :].split(".", 1)
            if _HARNESS_V2_CREDENTIAL_ID_RE.fullmatch(head) and len(secret) >= 32:
                credential_id = head
        if (
            not _HARNESS_V2_ROUTE_ID_RE.fullmatch(tenant_id)
            or credential_id is None
            or not service_credential.isascii()
            or any(
                character.isspace()
                or ord(character) < 0x20
                or ord(character) == 0x7F
                for character in service_credential
            )
        ):
            # Harness-v2 never falls back to a customer/bearer credential.
            raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
        return tenant_id, service_credential, credential_id

    def _harness_v2_worker_path(
        self,
        job: FleetJob,
        *,
        operation: Literal["consume", "output", "terminal"],
    ) -> tuple[str, str]:
        ids = (job.audit_id, job.job_id, job.assigned_worker_id)
        lease_token = job.lease_token
        if type(lease_token) is not str:
            raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
        try:
            lease_bytes = lease_token.encode("utf-8")
        except UnicodeEncodeError:
            raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE) from None
        if (
            job.status != "leased"
            or job.audit_id != self.config.audit_id
            or job.assigned_worker_id != self.config.worker_id
            or any(
                type(value) is not str
                or not _HARNESS_V2_ROUTE_ID_RE.fullmatch(value)
                for value in ids
            )
            or not 32 <= len(lease_bytes) <= 256
            or lease_token != lease_token.strip()
            or any(
                character.isspace()
                or ord(character) < 0x20
                or ord(character) == 0x7F
                for character in lease_token
            )
        ):
            raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
        path = (
            "/api/cas-harness/audit/distributed/session/"
            f"{job.audit_id}/fleet/v2/job/{job.job_id}/worker/"
            f"{job.assigned_worker_id}/{operation}"
        )
        return path, lease_token

    async def _post(self, path: str, payload: dict[str, Any] | None) -> Any:
        headers = {"Content-Type": "application/json"}
        service_credential = (self.config.service_credential or "").strip()
        if service_credential:
            headers.update(
                {
                    "Authorization": f"CAS-Service {service_credential}",
                    "X-CAS-Tenant-ID": str(self.config.tenant_id),
                    "X-CAS-Audit-ID": self.config.audit_id,
                    "X-CAS-Service-Timestamp": str(int(datetime.now(UTC).timestamp())),
                    # A fresh high-entropy nonce for every HTTP attempt. The API consumes it in
                    # the durable ledger, so a copied callback loses a cross-replica CAS race.
                    "X-CAS-Service-Nonce": secrets.token_urlsafe(24),
                }
            )
        else:
            token = (self.config.bearer_token or "").strip()
            if token:
                headers["Authorization"] = (
                    token if token.lower().startswith("bearer ") else f"Bearer {token}"
                )
        response = await self._client.post(
            f"{self.config.base_url}{path}",
            json=payload,
            headers=headers,
        )
        if response.status_code >= 400:
            raise FleetWorkerError(f"API POST {path} failed {response.status_code}: {response.text}")
        if not response.content:
            return None
        return response.json()


def build_harness_v2_consumption_request(run_nonce_b64url: str) -> bytes:
    """Build the exact canonical one-use consumption carrier."""

    if type(run_nonce_b64url) is not str or not _HARNESS_V2_RUN_NONCE_RE.fullmatch(
        run_nonce_b64url
    ):
        raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
    try:
        nonce_bytes = base64.b64decode(
            run_nonce_b64url + "=", altchars=b"-_", validate=True
        )
    except (ValueError, TypeError):
        raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE) from None
    if (
        len(nonce_bytes) != 32
        or base64.urlsafe_b64encode(nonce_bytes).decode("ascii").rstrip("=")
        != run_nonce_b64url
    ):
        raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
    return _canonical_harness_v2_json_bytes(
        {
            "schema_version": HARNESS_V2_CONSUMPTION_REQUEST_SCHEMA,
            "run_nonce_b64url": run_nonce_b64url,
        }
    )


def build_harness_v2_output_retention_request(
    *,
    output_name: str,
    artifact_id: str,
    artifact_media_type: str,
    artifact_body: bytes | bytearray | memoryview,
) -> bytes:
    """Build one canonical exact-output retention envelope."""

    if (
        type(output_name) is not str
        or not _HARNESS_V2_ROUTE_ID_RE.fullmatch(output_name)
        or type(artifact_id) is not str
        or not _HARNESS_V2_ROUTE_ID_RE.fullmatch(artifact_id)
        or not _valid_harness_v2_media_type(artifact_media_type)
        or type(artifact_body) not in (bytes, bytearray, memoryview)
    ):
        raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
    body = bytes(artifact_body)
    if not 1 <= len(body) <= _HARNESS_V2_MAX_ARTIFACT_BYTES:
        raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
    raw = _canonical_harness_v2_json_bytes(
        {
            "schema_version": HARNESS_V2_OUTPUT_RETENTION_SCHEMA,
            "output_name": output_name,
            "artifact": {
                "artifact_id": artifact_id,
                "media_type": artifact_media_type,
                "sha256": hashlib.sha256(body).hexdigest().upper(),
                "byte_length": len(body),
                "raw_base64": base64.b64encode(body).decode("ascii"),
            },
        }
    )
    return _snapshot_harness_v2_exact_body(raw)


def _valid_harness_v2_media_type(value: object) -> bool:
    if type(value) is not str or not value or value != value.strip():
        return False
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return (
        len(encoded) <= _HARNESS_V2_MAX_MEDIA_TYPE_BYTES
        and not any(character.isspace() for character in value)
        and "/" in value
    )


def _canonical_harness_v2_json_bytes(value: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError):
        raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE) from None


def _snapshot_harness_v2_exact_body(
    raw: bytes | bytearray | memoryview,
) -> bytes:
    if type(raw) not in (bytes, bytearray, memoryview):
        raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
    snapshot = bytes(raw)
    if not snapshot or len(snapshot) > _HARNESS_V2_MAX_EXACT_BODY_BYTES:
        raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE)
    return snapshot


async def _read_harness_v2_response(response: httpx.Response) -> bytes:
    content_types = response.headers.get_list("Content-Type")
    if len(content_types) != 1 or content_types[0] != "application/json":
        raise _HarnessV2ResponseError("invalid response media type")
    length_values = response.headers.get_list("Content-Length")
    if len(length_values) > 1:
        raise _HarnessV2ResponseError("duplicate response length")
    if length_values:
        try:
            declared_length = int(length_values[0])
        except ValueError as exc:
            raise _HarnessV2ResponseError("invalid response length") from exc
        if not 1 <= declared_length <= _HARNESS_V2_MAX_RESPONSE_BYTES:
            raise _HarnessV2ResponseError("response exceeds bound")
    else:
        declared_length = None
    captured = bytearray()
    async for chunk in response.aiter_bytes():
        if len(captured) + len(chunk) > _HARNESS_V2_MAX_RESPONSE_BYTES:
            raise _HarnessV2ResponseError("response exceeds bound")
        captured.extend(chunk)
    raw = bytes(captured)
    if not raw or (declared_length is not None and declared_length != len(raw)):
        raise _HarnessV2ResponseError("response length differs")
    return raw


def _load_harness_v2_json_object(raw: bytes) -> dict[str, Any]:
    def reject_constant(_value: str) -> None:
        raise _HarnessV2ResponseError("non-finite JSON value")

    def exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _HarnessV2ResponseError("duplicate JSON key")
            result[key] = value
        return result

    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=exact_object,
            parse_constant=reject_constant,
        )
    except _HarnessV2ResponseError:
        raise
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise _HarnessV2ResponseError("invalid JSON response") from exc
    if type(value) is not dict:
        raise _HarnessV2ResponseError("response must be an object")
    return value


def _terminal_result_binding(raw: bytes) -> tuple[str, str]:
    try:
        value = _load_harness_v2_json_object(raw)
        receipt_id = value.get("receipt_id")
        terminal = value.get("terminal")
        if (
            value.get("schema_version")
            != "cas_harness_v2.worker_terminal_receipt.v1"
            or type(receipt_id) is not str
            or not _HARNESS_V2_ROUTE_ID_RE.fullmatch(receipt_id)
            or type(terminal) is not dict
        ):
            raise _HarnessV2ResponseError("terminal receipt binding is unavailable")
        terminal_status = {"COMPLETED": "SUCCESS", "FAILED": "FAILURE"}.get(
            terminal.get("status")
        )
        if terminal_status is None:
            raise _HarnessV2ResponseError("terminal status is unavailable")
        return receipt_id, terminal_status
    except Exception:
        raise HarnessV2WorkerPreSendFailure(_HARNESS_V2_FAILURE) from None


def _harness_v2_operation_id(prefix: str, *values: str) -> str:
    digest = hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest()
    return f"h2{prefix}_{digest}"


def _validate_harness_v2_worker_response(
    payload: dict[str, Any],
    *,
    operation: Literal["consume", "output", "terminal"],
    job: FleetJob,
    request_sha256: str,
    request_byte_length: int,
    expected_nonce_id: str,
    expected_result: _HarnessV2ExpectedResult,
) -> None:
    _expect_harness_v2_keys(
        payload,
        {
            "status",
            "operation",
            "audit_id",
            "job_id",
            "run_id",
            "intake_receipt",
            "result",
            "authority",
        },
    )
    expected_run_id = "h2run_" + hashlib.sha256(
        job.job_id.encode("utf-8")
    ).hexdigest()
    if (
        payload["status"] != "ACCEPTED_RESEARCH_ONLY"
        or payload["operation"] != _HARNESS_V2_RESPONSE_OPERATIONS[operation]
        or payload["audit_id"] != job.audit_id
        or payload["job_id"] != job.job_id
        or payload["run_id"] != expected_run_id
        or payload["authority"] != _HARNESS_V2_AUTHORITY
    ):
        raise _HarnessV2ResponseError("response scope differs")

    intake = payload["intake_receipt"]
    if type(intake) is not dict:
        raise _HarnessV2ResponseError("intake receipt is invalid")
    _expect_harness_v2_keys(
        intake,
        {"nonce_id", "carrier_sha256", "carrier_byte_length", "scope"},
    )
    if (
        intake["nonce_id"] != expected_nonce_id
        or intake["carrier_sha256"] != request_sha256
        or type(intake["carrier_byte_length"]) is not int
        or isinstance(intake["carrier_byte_length"], bool)
        or intake["carrier_byte_length"] != request_byte_length
        or intake["scope"] != "SERVER_OBSERVED_HTTP_INTAKE_ONLY"
    ):
        raise _HarnessV2ResponseError("intake binding differs")

    result = payload["result"]
    if type(result) is not dict:
        raise _HarnessV2ResponseError("result is invalid")
    common_keys = {
        "schema_version",
        "result_kind",
        "receipt_id",
        "receipt_sha256",
        "idempotent_replay",
    }
    operation_keys = {
        "consume": {"started_at", "time_assurance"},
        "output": set(),
        "terminal": {
            "receipt_media_type",
            "receipt_byte_length",
            "terminal_status",
            "terminal_event_sha256",
        },
    }[operation]
    _expect_harness_v2_keys(result, common_keys | operation_keys)
    expected_schema, expected_kind = _HARNESS_V2_RESULT_CONTRACTS[operation]
    if (
        result["schema_version"] != expected_schema
        or result["result_kind"] != expected_kind
        or type(result["receipt_id"]) is not str
        or not _HARNESS_V2_ROUTE_ID_RE.fullmatch(result["receipt_id"])
        or type(result["receipt_sha256"]) is not str
        or not _HARNESS_V2_UPPER_SHA256_RE.fullmatch(result["receipt_sha256"])
        or type(result["idempotent_replay"]) is not bool
    ):
        raise _HarnessV2ResponseError("result contract differs")
    if (
        expected_result.receipt_id is not None
        and result["receipt_id"] != expected_result.receipt_id
    ) or (
        expected_result.receipt_sha256 is not None
        and result["receipt_sha256"] != expected_result.receipt_sha256
    ):
        raise _HarnessV2ResponseError("result artifact differs")

    if operation == "consume":
        if (
            not _canonical_harness_v2_utc_time(result["started_at"])
            or result["time_assurance"]
            != "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"
        ):
            raise _HarnessV2ResponseError("consumption result differs")
    elif operation == "terminal":
        if (
            result["receipt_media_type"] != expected_result.receipt_media_type
            or type(result["receipt_byte_length"]) is not int
            or isinstance(result["receipt_byte_length"], bool)
            or result["receipt_byte_length"] != expected_result.receipt_byte_length
            or result["terminal_status"] != expected_result.terminal_status
            or type(result["terminal_event_sha256"]) is not str
            or not _HARNESS_V2_UPPER_SHA256_RE.fullmatch(
                result["terminal_event_sha256"]
            )
        ):
            raise _HarnessV2ResponseError("terminal result differs")


def _canonical_harness_v2_utc_time(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        return False
    canonical = parsed.astimezone(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    return value == canonical


def _expect_harness_v2_keys(value: dict[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise _HarnessV2ResponseError("response fields differ")


class FleetWorkerDaemon:
    """One worker process attached to one distributed audit."""

    def __init__(
        self,
        config: FleetWorkerConfig,
        executor: FleetJobExecutor,
        *,
        api_client: FleetApiClient | None = None,
    ) -> None:
        self.config = config
        self.executor = executor
        self.api = api_client or FleetApiClient(config)

    async def close(self) -> None:
        await self.api.close()

    async def run_once(self) -> FleetWorkerRunResult:
        await self.api.register_worker()
        await self.api.heartbeat()
        job = await self.api.lease_job()
        if job is None:
            return FleetWorkerRunResult(status="idle")
        try:
            result = await self.executor.run(job, self.config)
            fragment_ref = None
            if result.status == "completed":
                fragment_ref = write_evidence_fragment(
                    job,
                    self.config,
                    result,
                    execution_mode=self.executor.execution_mode,
                )
            await self.api.submit_receipt(
                job,
                result,
                evidence_packet_fragment_ref=fragment_ref,
                execution_mode=self.executor.execution_mode,
            )
            return FleetWorkerRunResult(
                status=result.status,
                job_id=job.job_id,
                evidence_packet_fragment_ref=fragment_ref,
                error_message=result.error_message,
            )
        except Exception as exc:
            failure = FleetJobExecutionResult(
                produced_outputs=(),
                missing_outputs=job.expected_outputs,
                error_message=_truncate_text(str(exc)),
            )
            await self.api.submit_receipt(
                job,
                failure,
                evidence_packet_fragment_ref=None,
                execution_mode=self.executor.execution_mode,
            )
            return FleetWorkerRunResult(status="failed", job_id=job.job_id, error_message=failure.error_message)

    async def run_loop(self) -> list[FleetWorkerRunResult]:
        results: list[FleetWorkerRunResult] = []
        completed_jobs = 0
        while self.config.max_jobs is None or completed_jobs < self.config.max_jobs:
            result = await self.run_once()
            results.append(result)
            if result.status == "idle":
                await asyncio.sleep(self.config.poll_interval_seconds)
                continue
            completed_jobs += 1
        return results


def write_evidence_fragment(
    job: FleetJob,
    config: FleetWorkerConfig,
    result: FleetJobExecutionResult,
    *,
    execution_mode: str,
) -> str:
    """Write local fragment payload and return the API-validated fragment ref."""

    config.evidence_dir.mkdir(parents=True, exist_ok=True)
    fragment_ref = build_evidence_fragment_ref(
        audit_id=job.audit_id,
        job_id=job.job_id,
        worker_id=config.worker_id,
        model_id=config.model_id,
        layer_start=job.layer_start,
        layer_end=job.layer_end,
        shard_id=job.shard_id,
        expected_outputs=job.expected_outputs,
        produced_outputs=result.produced_outputs,
        missing_outputs=result.missing_outputs,
        evidence_packet_fragment_payload=result.evidence_payload,
        execution_mode=execution_mode,
    )
    payload = {
        "schema_version": "cas_harness_worker_evidence_fragment.v1",
        "fragment_ref": fragment_ref,
        "execution_mode": execution_mode,
        "created_at": datetime.now(UTC).isoformat(),
        "audit_id": job.audit_id,
        "job_id": job.job_id,
        "worker_id": config.worker_id,
        "model_id": config.model_id,
        "layer_start": job.layer_start,
        "layer_end": job.layer_end,
        "shard_id": job.shard_id,
        "assigned_methods": list(job.assigned_methods),
        "expected_outputs": list(job.expected_outputs),
        "produced_outputs": list(result.produced_outputs),
        "missing_outputs": list(result.missing_outputs),
    }
    if result.evidence_payload is not None:
        payload["evidence_payload"] = result.evidence_payload
    path = config.evidence_dir / f"{job.job_id}.evidence-fragment.json"
    _write_json_atomically(path, payload)
    return fragment_ref


def build_evidence_fragment_ref(
    *,
    audit_id: str,
    job_id: str,
    worker_id: str,
    model_id: str,
    layer_start: int,
    layer_end: int,
    shard_id: str,
    expected_outputs: tuple[str, ...] | list[str],
    produced_outputs: tuple[str, ...] | list[str],
    missing_outputs: tuple[str, ...] | list[str] = (),
    evidence_packet_fragment_payload: dict[str, Any] | None = None,
    execution_mode: str | None = None,
) -> str:
    payload = {
        "schema_version": "cas_harness_evidence_fragment.v1",
        "audit_id": audit_id,
        "job_id": job_id,
        "worker_id": worker_id,
        "model_id": model_id,
        "layer_start": layer_start,
        "layer_end": layer_end,
        "shard_id": shard_id,
        "expected_outputs": list(expected_outputs),
        "produced_outputs": list(produced_outputs),
        "missing_outputs": list(missing_outputs),
    }
    if evidence_packet_fragment_payload is not None:
        payload["fragment_payload_sha256"] = hashlib.sha256(
            json.dumps(
                evidence_packet_fragment_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
    if execution_mode is not None:
        payload["execution_mode"] = execution_mode
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"cas-fragment://{audit_id}/{job_id}/{worker_id}/{shard_id}/sha256:{digest}"


def _write_json_atomically(path: Path, payload: dict[str, Any]) -> None:
    """Durably replace a fragment only after all bytes reach the local file.

    The receipt is submitted only after this returns.  A process failure while
    writing therefore leaves either the previous complete fragment or a
    separately named temporary file, never a truncated acknowledged fragment.
    """

    encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    temp_path = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    )
    try:
        with temp_path.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _parse_command_result(path: Path, job: FleetJob) -> FleetJobExecutionResult:
    payload = json.loads(path.read_text(encoding="utf-8"))
    produced = tuple(_clean_list(payload.get("produced_outputs", [])))
    missing = tuple(_clean_list(payload.get("missing_outputs", [])))
    evidence_payload = payload.get("evidence_payload") if isinstance(payload.get("evidence_payload"), dict) else None
    error = payload.get("error_message")
    error_message = str(error).strip() if error is not None and str(error).strip() else None
    if error_message:
        return FleetJobExecutionResult(
            produced_outputs=produced,
            missing_outputs=missing or tuple(item for item in job.expected_outputs if item not in produced),
            error_message=error_message,
            evidence_payload=evidence_payload,
        )
    if not produced:
        return FleetJobExecutionResult(
            produced_outputs=(),
            missing_outputs=job.expected_outputs,
            error_message="Probe command produced no outputs.",
        )
    unknown = set(produced) - set(job.expected_outputs)
    if unknown:
        return FleetJobExecutionResult(
            produced_outputs=(),
            missing_outputs=job.expected_outputs,
            error_message=f"Probe command produced unknown outputs: {', '.join(sorted(unknown))}.",
        )
    try:
        _validate_command_model_attestation(evidence_payload, job)
    except FleetWorkerError as exc:
        return FleetJobExecutionResult(
            produced_outputs=(),
            missing_outputs=job.expected_outputs,
            error_message=str(exc),
            evidence_payload=evidence_payload,
        )
    return FleetJobExecutionResult(
        produced_outputs=produced,
        missing_outputs=missing or tuple(item for item in job.expected_outputs if item not in produced),
        evidence_payload=evidence_payload,
    )


def _optional_clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise FleetWorkerError("Lease model identity fields must be canonical non-empty strings.")
    return value


def _bound_model_identity(
    job: FleetJob,
    config: FleetWorkerConfig,
) -> tuple[str, str, str, str]:
    identity = (
        job.model_id,
        job.model_revision,
        job.model_artifact_manifest_path,
        job.model_artifact_manifest_sha256,
    )
    if any(value is None for value in identity):
        raise FleetWorkerError(
            "External probe execution requires the lease-bound model ID, revision, "
            "artifact manifest path, and artifact manifest SHA-256."
        )
    model_id, revision, manifest_path, manifest_sha256 = identity
    assert model_id is not None
    assert revision is not None
    assert manifest_path is not None
    assert manifest_sha256 is not None
    if model_id != config.model_id:
        raise FleetWorkerError("Lease-bound model_id does not match this worker configuration.")
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise FleetWorkerError(
            "Lease-bound model_revision must be a full 40-character lowercase commit SHA."
        )
    is_posix_absolute = manifest_path.startswith("/")
    is_windows_absolute = re.match(r"^[A-Za-z]:[\\/]", manifest_path) is not None
    if "\x00" in manifest_path or not (is_posix_absolute or is_windows_absolute):
        raise FleetWorkerError(
            "Lease-bound model artifact manifest path must be absolute on this worker."
        )
    if re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) is None:
        raise FleetWorkerError(
            "Lease-bound model artifact manifest SHA-256 must be 64 lowercase hexadecimal characters."
        )
    if job.execution_mode not in {None, "external_probe_command"}:
        raise FleetWorkerError(
            "Lease execution_mode is incompatible with external probe execution."
        )
    return model_id, revision, manifest_path, manifest_sha256


def _validate_command_model_attestation(
    evidence_payload: dict[str, Any] | None,
    job: FleetJob,
) -> None:
    if not isinstance(evidence_payload, dict):
        raise FleetWorkerError(
            "External probe completion requires a real-model artifact attestation."
        )
    expected_fields = {
        "status": "real_model_forward_completed",
        "audit_id": job.audit_id,
        "job_id": job.job_id,
        "worker_id": job.assigned_worker_id,
        "model_id": job.model_id,
        "model_revision": job.model_revision,
        "shard_id": job.shard_id,
        "layer_start": job.layer_start,
        "layer_end": job.layer_end,
    }
    for field_name, expected in expected_fields.items():
        if evidence_payload.get(field_name) != expected:
            raise FleetWorkerError(
                f"Real-model attestation {field_name} does not match the leased job."
            )
    model_info = evidence_payload.get("model_info")
    artifact_identity = (
        model_info.get("artifact_identity") if isinstance(model_info, dict) else None
    )
    if not isinstance(artifact_identity, dict):
        raise FleetWorkerError(
            "Real-model completion requires model_info.artifact_identity."
        )
    if artifact_identity.get("manifest_path") != job.model_artifact_manifest_path:
        raise FleetWorkerError(
            "Real-model attestation manifest path does not match the leased job."
        )
    if artifact_identity.get("manifest_sha256") != job.model_artifact_manifest_sha256:
        raise FleetWorkerError(
            "Real-model attestation manifest SHA-256 does not match the leased job."
        )
    required_flags = {
        "all_artifacts_hash_verified": True,
        "post_load_reverified": True,
        "local_files_only": True,
        "trust_remote_code": False,
        "use_safetensors": True,
    }
    for field_name, expected in required_flags.items():
        if artifact_identity.get(field_name) is not expected:
            raise FleetWorkerError(
                f"Real-model artifact attestation requires {field_name}={expected!r}."
            )
    _validate_exact_artifact_evidence(artifact_identity)


def _validate_exact_artifact_evidence(artifact_identity: dict[str, Any]) -> None:
    artifacts = artifact_identity.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise FleetWorkerError(
            "Real-model artifact attestation requires a non-empty exact artifact list."
        )
    canonical: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict) or set(artifact) != {
            "path",
            "sha256",
            "byte_count",
        }:
            raise FleetWorkerError(
                f"Real-model artifact attestation entry {index} has invalid fields."
            )
        artifact_path = artifact.get("path")
        digest = artifact.get("sha256")
        byte_count = artifact.get("byte_count")
        if (
            not isinstance(artifact_path, str)
            or not artifact_path
            or artifact_path in seen
        ):
            raise FleetWorkerError(
                "Real-model artifact paths must be unique non-empty strings."
            )
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise FleetWorkerError("Real-model artifact SHA-256 is malformed.")
        if type(byte_count) is not int or byte_count < 1:
            raise FleetWorkerError("Real-model artifact byte_count is malformed.")
        seen.add(artifact_path)
        canonical.append(
            {"path": artifact_path, "sha256": digest, "byte_count": byte_count}
        )
    canonical.sort(key=lambda item: item["path"])
    if artifact_identity.get("artifact_count") != len(canonical):
        raise FleetWorkerError(
            "Real-model artifact_count does not match the exact artifact list."
        )
    artifact_set_sha256 = hashlib.sha256(
        json.dumps(
            canonical,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if artifact_identity.get("artifact_set_sha256") != artifact_set_sha256:
        raise FleetWorkerError(
            "Real-model artifact_set_sha256 does not match the exact artifact list."
        )


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if text and text not in seen:
            cleaned.append(text)
            seen.add(text)
    return cleaned


def _truncate_text(value: str, *, limit: int = 480) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text or "Probe worker failed."
    return text[: limit - 3] + "..."
