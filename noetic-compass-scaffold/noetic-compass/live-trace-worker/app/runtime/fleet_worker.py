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
