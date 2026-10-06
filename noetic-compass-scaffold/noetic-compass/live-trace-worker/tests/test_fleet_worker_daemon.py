"""Worker-daemon tests for distributed CAS Harness fleet jobs."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import httpx
import pytest

from app.runtime.fleet_worker import (
    CommandFleetJobExecutor,
    DryRunFleetJobExecutor,
    FleetApiClient,
    FleetJob,
    FleetJobExecutionResult,
    FleetWorkerError,
    FleetWorkerConfig,
    FleetWorkerDaemon,
    HarnessV2WorkerPostSendIndeterminate,
    HarnessV2WorkerPreSendFailure,
    HARNESS_V2_CONSUMPTION_MEDIA_TYPE,
    HARNESS_V2_CONSUMPTION_REQUEST_SCHEMA,
    HARNESS_V2_OUTPUT_RETENTION_MEDIA_TYPE,
    HARNESS_V2_OUTPUT_RETENTION_SCHEMA,
    HARNESS_V2_TERMINAL_MEDIA_TYPE,
    build_evidence_fragment_ref,
    build_harness_v2_consumption_request,
    build_harness_v2_output_retention_request,
)


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


def _config(tmp_path: Path) -> FleetWorkerConfig:
    return FleetWorkerConfig(
        api_base_url="https://api.example.test",
        audit_id="cas-dist-test",
        worker_id="probe-worker-001",
        model_id="open-cas/example-70b",
        worker_url="http://worker.local",
        gpu_type="A100-80GB",
        supported_methods=("foundation_probe", "targeted_ablation", "matched_controls"),
        bearer_token="test-token",
        evidence_dir=tmp_path,
        max_jobs=1,
        poll_interval_seconds=0,
    )


def _leased_job_payload(
    config: FleetWorkerConfig,
    *,
    bound: bool = False,
) -> dict[str, Any]:
    payload = {
        "job_id": "fleet-job-001",
        "audit_id": config.audit_id,
        "assigned_worker_id": config.worker_id,
        "layer_start": 0,
        "layer_end": 3,
        "shard_id": "layers-000-003",
        "assigned_methods": list(config.supported_methods),
        "expected_outputs": [
            "layer_activation_summary",
            "cas_axis_readout",
            "blindspot_overlay",
            "worker_evidence_manifest",
        ],
        "status": "leased",
        "lease_token": "lease-token-001",
        "model_id": config.model_id,
        "execution_mode": (
            "external_probe_command" if bound else "dry_run_control_plane"
        ),
        "lease_expires_at": "2026-05-26T00:00:00+00:00",
        "evidence_packet_fragment_ref": None,
        "produced_outputs": [],
        "missing_outputs": [],
        "error_message": None,
        "updated_at": "2026-05-26T00:00:00+00:00",
    }
    if bound:
        payload.update(
            {
                "model_revision": "a" * 40,
                "model_artifact_manifest_path": str(
                    (config.evidence_dir / "model-artifacts.json").resolve()
                ),
                "model_artifact_manifest_sha256": "b" * 64,
            }
        )
    return payload


def _harness_v2_route_response(
    request: httpx.Request,
    job: FleetJob,
    *,
    operation: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    credential = request.headers["authorization"][len("CAS-Service ") :]
    credential_id = credential[len("casfs_") :].split(".", 1)[0]
    callback_nonce = request.headers["x-cas-service-nonce"]
    return {
        "status": "ACCEPTED_RESEARCH_ONLY",
        "operation": operation,
        "audit_id": job.audit_id,
        "job_id": job.job_id,
        "run_id": "h2run_" + hashlib.sha256(job.job_id.encode("utf-8")).hexdigest(),
        "intake_receipt": {
            "nonce_id": "fsn_"
            + hashlib.sha256(
                f"{credential_id}:{callback_nonce}".encode("utf-8")
            ).hexdigest(),
            "carrier_sha256": hashlib.sha256(request.content).hexdigest().upper(),
            "carrier_byte_length": len(request.content),
            "scope": "SERVER_OBSERVED_HTTP_INTAKE_ONLY",
        },
        "result": result,
        "authority": dict(_HARNESS_V2_AUTHORITY),
    }


def _harness_v2_result(
    *,
    operation: str,
    receipt_id: str,
    receipt_sha256: str,
    idempotent_replay: bool = False,
    terminal_raw: bytes | None = None,
) -> dict[str, Any]:
    contracts = {
        "consume_authorization": (
            "cas_harness_v2.consumption_route_result.v1",
            "AUTHORIZATION_CONSUMPTION",
        ),
        "retain_output": (
            "cas_harness_v2.output_route_result.v1",
            "OUTPUT_RETENTION",
        ),
        "accept_terminal": (
            "cas_harness_v2.terminal_route_result.v1",
            "TERMINAL_ACCEPTANCE",
        ),
    }
    schema_version, result_kind = contracts[operation]
    result: dict[str, Any] = {
        "schema_version": schema_version,
        "result_kind": result_kind,
        "receipt_id": receipt_id,
        "receipt_sha256": receipt_sha256,
        "idempotent_replay": idempotent_replay,
    }
    if operation == "consume_authorization":
        result.update(
            {
                "started_at": "2026-08-05T08:35:00.000000Z",
                "time_assurance": "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED",
            }
        )
    elif operation == "accept_terminal":
        assert terminal_raw is not None
        terminal_status = {
            "COMPLETED": "SUCCESS",
            "FAILED": "FAILURE",
        }[json.loads(terminal_raw)["terminal"]["status"]]
        result.update(
            {
                "receipt_media_type": HARNESS_V2_TERMINAL_MEDIA_TYPE,
                "receipt_byte_length": len(terminal_raw),
                "terminal_status": terminal_status,
                "terminal_event_sha256": "E" * 64,
            }
        )
    return result


def _real_model_attestation(job: FleetJob) -> dict[str, Any]:
    artifacts = [
        {"path": "config.json", "sha256": "c" * 64, "byte_count": 1}
    ]
    artifact_set_sha256 = __import__("hashlib").sha256(
        json.dumps(
            artifacts,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "status": "real_model_forward_completed",
        "audit_id": job.audit_id,
        "job_id": job.job_id,
        "worker_id": job.assigned_worker_id,
        "model_id": job.model_id,
        "model_revision": job.model_revision,
        "shard_id": job.shard_id,
        "layer_start": job.layer_start,
        "layer_end": job.layer_end,
        "model_info": {
            "artifact_identity": {
                "manifest_path": job.model_artifact_manifest_path,
                "manifest_sha256": job.model_artifact_manifest_sha256,
                "artifact_count": len(artifacts),
                "artifact_set_sha256": artifact_set_sha256,
                "artifacts": artifacts,
                "all_artifacts_hash_verified": True,
                "post_load_reverified": True,
                "local_files_only": True,
                "trust_remote_code": False,
                "use_safetensors": True,
            }
        },
    }


def _worker_payload(config: FleetWorkerConfig) -> dict[str, Any]:
    return {
        "worker_id": config.worker_id,
        "model_id": config.model_id,
        "worker_url": config.worker_url,
        "gpu_type": config.gpu_type,
        "capacity": config.capacity,
        "supported_methods": list(config.supported_methods),
        "registered_at": "2026-05-26T00:00:00+00:00",
        "last_heartbeat_at": "2026-05-26T00:00:00+00:00",
        "status": "active",
    }


def test_daemon_leases_runs_writes_fragment_and_posts_receipt(tmp_path: Path):
    config = _config(tmp_path)
    leased_job = _leased_job_payload(config)
    seen: dict[str, Any] = {"paths": [], "receipt": None}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["paths"].append(request.url.path)
        assert request.headers["authorization"] == "Bearer test-token"
        if request.url.path == "/api/cas-harness/audit/distributed/fleet/worker/register":
            return httpx.Response(200, json=_worker_payload(config))
        if request.url.path == f"/api/cas-harness/audit/distributed/fleet/worker/{config.worker_id}/heartbeat":
            return httpx.Response(200, json=_worker_payload(config))
        if request.url.path == f"/api/cas-harness/audit/distributed/session/{config.audit_id}/fleet/job/lease":
            return httpx.Response(200, json=leased_job)
        if request.url.path == (
            f"/api/cas-harness/audit/distributed/session/{config.audit_id}"
            f"/fleet/job/{leased_job['job_id']}/receipt"
        ):
            payload = json.loads(request.content.decode("utf-8"))
            seen["receipt"] = payload
            expected_ref = build_evidence_fragment_ref(
                audit_id=config.audit_id,
                job_id=leased_job["job_id"],
                worker_id=config.worker_id,
                model_id=config.model_id,
                layer_start=leased_job["layer_start"],
                layer_end=leased_job["layer_end"],
                shard_id=leased_job["shard_id"],
                expected_outputs=leased_job["expected_outputs"],
                produced_outputs=leased_job["expected_outputs"],
                missing_outputs=[],
                execution_mode="dry_run_control_plane",
            )
            assert payload["evidence_packet_fragment_ref"] == expected_ref
            assert payload["job_status"] == "completed"
            assert payload["execution_mode"] == "dry_run_control_plane"
            return httpx.Response(200, json={"verifier_gate_status": "waiting_for_receipts"})
        raise AssertionError(f"unexpected path {request.url.path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = FleetApiClient(config, client=client)
    daemon = FleetWorkerDaemon(config, DryRunFleetJobExecutor(), api_client=api)

    result = asyncio.run(daemon.run_once())

    assert result.status == "completed"
    assert result.job_id == leased_job["job_id"]
    assert seen["receipt"]["lease_token"] == "lease-token-001"
    fragment_path = tmp_path / f"{leased_job['job_id']}.evidence-fragment.json"
    fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
    assert fragment["execution_mode"] == "dry_run_control_plane"
    assert fragment["fragment_ref"] == result.evidence_packet_fragment_ref


def test_fragment_ref_matches_api_fleet_executor_builder(tmp_path: Path):
    repo_app_root = Path(__file__).resolve().parents[2]
    if str(repo_app_root) not in sys.path:
        sys.path.insert(0, str(repo_app_root))
    from api.services.cas_harness_fleet_executor import build_evidence_fragment_ref as api_builder

    config = _config(tmp_path)
    job = _leased_job_payload(config)
    kwargs = {
        "audit_id": config.audit_id,
        "job_id": job["job_id"],
        "worker_id": config.worker_id,
        "model_id": config.model_id,
        "layer_start": job["layer_start"],
        "layer_end": job["layer_end"],
        "shard_id": job["shard_id"],
        "expected_outputs": job["expected_outputs"],
        "produced_outputs": job["expected_outputs"],
        "missing_outputs": [],
        "evidence_packet_fragment_payload": {
            "worker_receipt": {"status": "WORKER_EVIDENCE_UNVERIFIED"}
        },
        "execution_mode": "dry_run_control_plane",
    }

    assert build_evidence_fragment_ref(**kwargs) == api_builder(**kwargs)


def test_rich_evidence_payload_is_persisted_hashed_and_submitted_before_ack(tmp_path: Path):
    config = _config(tmp_path)
    leased_job = _leased_job_payload(config)
    evidence_payload = {
        "activation_summary": {"layer": 0, "mean": 0.125},
        "worker_receipt": {"status": "WORKER_EVIDENCE_UNVERIFIED"},
    }
    seen_receipt: dict[str, Any] = {}

    class _RichExecutor:
        execution_mode = "dry_run_control_plane"

        async def run(self, job, _config):
            return FleetJobExecutionResult(
                produced_outputs=job.expected_outputs,
                evidence_payload=evidence_payload,
            )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/cas-harness/audit/distributed/fleet/worker/register":
            return httpx.Response(200, json=_worker_payload(config))
        if request.url.path == f"/api/cas-harness/audit/distributed/fleet/worker/{config.worker_id}/heartbeat":
            return httpx.Response(200, json=_worker_payload(config))
        if request.url.path == f"/api/cas-harness/audit/distributed/session/{config.audit_id}/fleet/job/lease":
            return httpx.Response(200, json=leased_job)
        if request.url.path.endswith(f"/fleet/job/{leased_job['job_id']}/receipt"):
            # Persistence must precede acknowledgement.  The handler observes
            # the filesystem at the exact point the HTTP receipt is sent.
            fragment_path = tmp_path / f"{leased_job['job_id']}.evidence-fragment.json"
            assert fragment_path.is_file()
            persisted = json.loads(fragment_path.read_text(encoding="utf-8"))
            assert persisted["evidence_payload"] == evidence_payload
            seen_receipt.update(json.loads(request.content.decode("utf-8")))
            return httpx.Response(200, json={"verifier_gate_status": "waiting_for_receipts"})
        raise AssertionError(f"unexpected path {request.url.path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    daemon = FleetWorkerDaemon(
        config,
        _RichExecutor(),
        api_client=FleetApiClient(config, client=client),
    )
    result = asyncio.run(daemon.run_once())

    expected_ref = build_evidence_fragment_ref(
        audit_id=config.audit_id,
        job_id=leased_job["job_id"],
        worker_id=config.worker_id,
        model_id=config.model_id,
        layer_start=leased_job["layer_start"],
        layer_end=leased_job["layer_end"],
        shard_id=leased_job["shard_id"],
        expected_outputs=leased_job["expected_outputs"],
        produced_outputs=leased_job["expected_outputs"],
        missing_outputs=[],
        evidence_packet_fragment_payload=evidence_payload,
        execution_mode="dry_run_control_plane",
    )
    assert result.status == "completed"
    assert result.evidence_packet_fragment_ref == expected_ref
    assert seen_receipt["evidence_packet_fragment_ref"] == expected_ref
    assert seen_receipt["evidence_packet_fragment_payload"] == evidence_payload


def test_evidence_payload_one_bit_change_changes_fragment_ref(tmp_path: Path):
    config = _config(tmp_path)
    job = _leased_job_payload(config)
    common = {
        "audit_id": config.audit_id,
        "job_id": job["job_id"],
        "worker_id": config.worker_id,
        "model_id": config.model_id,
        "layer_start": job["layer_start"],
        "layer_end": job["layer_end"],
        "shard_id": job["shard_id"],
        "expected_outputs": job["expected_outputs"],
        "produced_outputs": job["expected_outputs"],
        "missing_outputs": [],
    }
    first = build_evidence_fragment_ref(
        **common,
        evidence_packet_fragment_payload={"value": 0},
    )
    second = build_evidence_fragment_ref(
        **common,
        evidence_packet_fragment_payload={"value": 1},
    )
    assert first != second


def test_duplicate_registration_heartbeats_existing_worker_and_idles(tmp_path: Path):
    config = _config(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/cas-harness/audit/distributed/fleet/worker/register":
            return httpx.Response(409, text="Worker ID is already registered; heartbeat the existing worker instead.")
        if request.url.path == f"/api/cas-harness/audit/distributed/fleet/worker/{config.worker_id}/heartbeat":
            return httpx.Response(200, json=_worker_payload(config))
        if request.url.path == f"/api/cas-harness/audit/distributed/session/{config.audit_id}/fleet/job/lease":
            return httpx.Response(200, json=None)
        raise AssertionError(f"unexpected path {request.url.path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    daemon = FleetWorkerDaemon(
        config,
        DryRunFleetJobExecutor(),
        api_client=FleetApiClient(config, client=client),
    )

    result = asyncio.run(daemon.run_once())

    assert result.status == "idle"


def test_service_credential_headers_are_scoped_and_use_fresh_nonces(tmp_path: Path):
    secret = "casfs_fsc_0123456789abcdef0123456789abcdef.worker-secret-material"
    config = replace(
        _config(tmp_path),
        bearer_token=None,
        tenant_id="tenant-a",
        service_credential=secret,
    )
    nonces: set[str] = set()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"CAS-Service {secret}"
        assert request.headers["x-cas-tenant-id"] == "tenant-a"
        assert request.headers["x-cas-audit-id"] == config.audit_id
        timestamp = int(request.headers["x-cas-service-timestamp"])
        assert abs(datetime.now(UTC).timestamp() - timestamp) < 10
        nonce = request.headers["x-cas-service-nonce"]
        assert len(nonce) >= 16
        assert nonce not in nonces
        nonces.add(nonce)
        if request.url.path == "/api/cas-harness/audit/distributed/fleet/worker/register":
            return httpx.Response(200, json=_worker_payload(config))
        if request.url.path == f"/api/cas-harness/audit/distributed/fleet/worker/{config.worker_id}/heartbeat":
            return httpx.Response(200, json=_worker_payload(config))
        if request.url.path == f"/api/cas-harness/audit/distributed/session/{config.audit_id}/fleet/job/lease":
            return httpx.Response(200, json=None)
        raise AssertionError(f"unexpected path {request.url.path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    daemon = FleetWorkerDaemon(
        config,
        DryRunFleetJobExecutor(),
        api_client=FleetApiClient(config, client=client),
    )
    result = asyncio.run(daemon.run_once())

    assert result.status == "idle"
    assert len(nonces) == 3
    assert secret not in repr(config)


def test_harness_v2_worker_calls_use_exact_carriers_headers_and_order(tmp_path: Path):
    credential = (
        "casfs_fsc_0123456789abcdef0123456789abcdef."
        "worker-secret-material-0123456789abcdef"
    )
    lease_token = "lease-token-" + ("l" * 40)
    authorization_sha256 = "A" * 64
    run_nonce = base64.urlsafe_b64encode(b"n" * 32).decode("ascii").rstrip("=")
    artifact_body = b'{"activation":1}'
    terminal_receipt_raw = (
        b'{"receipt_id":"worker-receipt-h2-001","schema_version":'
        b'"cas_harness_v2.worker_terminal_receipt.v1","terminal":'
        b'{"status":"COMPLETED"}}'
    )
    config = replace(
        _config(tmp_path),
        bearer_token=None,
        tenant_id="tenant-a",
        service_credential=credential,
    )
    job = replace(FleetJob.from_api(_leased_job_payload(config)), lease_token=lease_token)
    seen: list[httpx.Request] = []

    expected_paths = [
        f"/api/cas-harness/audit/distributed/session/{job.audit_id}"
        f"/fleet/v2/job/{job.job_id}/worker/{job.assigned_worker_id}/consume",
        f"/api/cas-harness/audit/distributed/session/{job.audit_id}"
        f"/fleet/v2/job/{job.job_id}/worker/{job.assigned_worker_id}/output",
        f"/api/cas-harness/audit/distributed/session/{job.audit_id}"
        f"/fleet/v2/job/{job.job_id}/worker/{job.assigned_worker_id}/terminal",
    ]
    expected_media_types = [
        HARNESS_V2_CONSUMPTION_MEDIA_TYPE,
        HARNESS_V2_OUTPUT_RETENTION_MEDIA_TYPE,
        HARNESS_V2_TERMINAL_MEDIA_TYPE,
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        index = len(seen)
        assert request.method == "POST"
        assert request.url.path == expected_paths[index]
        assert request.url.query == b""
        assert request.headers["authorization"] == f"CAS-Service {credential}"
        assert request.headers["content-type"] == expected_media_types[index]
        assert request.headers["content-length"] == str(len(request.content))
        assert request.headers["x-cas-tenant-id"] == "tenant-a"
        assert request.headers["x-cas-audit-id"] == job.audit_id
        assert request.headers["x-cas-authorization-sha256"] == authorization_sha256
        assert request.headers["x-cas-lease-token"] == lease_token
        assert abs(
            datetime.now(UTC).timestamp()
            - int(request.headers["x-cas-service-timestamp"])
        ) < 10
        seen.append(request)
        operation = ["consume_authorization", "retain_output", "accept_terminal"][
            index
        ]
        receipt_id = [
            "h2consumption_"
            + hashlib.sha256(job.job_id.encode("utf-8")).hexdigest(),
            "worker-output-shard-00",
            "worker-receipt-h2-001",
        ][index]
        receipt_sha256 = [
            "D" * 64,
            hashlib.sha256(artifact_body).hexdigest().upper(),
            hashlib.sha256(terminal_receipt_raw).hexdigest().upper(),
        ][index]
        return httpx.Response(
            200,
            json=_harness_v2_route_response(
                request,
                job,
                operation=operation,
                result=_harness_v2_result(
                    operation=operation,
                    receipt_id=receipt_id,
                    receipt_sha256=receipt_sha256,
                    terminal_raw=(
                        terminal_receipt_raw
                        if operation == "accept_terminal"
                        else None
                    ),
                ),
            ),
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = FleetApiClient(config, client=client)

    async def exercise() -> list[dict[str, Any]]:
        consumed = await api.consume_harness_v2_authorization(
            job,
            authorization_sha256=authorization_sha256,
            run_nonce_b64url=run_nonce,
        )
        retained = await api.retain_harness_v2_output(
            job,
            authorization_sha256=authorization_sha256,
            output_name="raw-outcomes",
            artifact_id="worker-output-shard-00",
            artifact_media_type="application/json",
            artifact_body=artifact_body,
        )
        terminal = await api.submit_harness_v2_terminal(
            job,
            authorization_sha256=authorization_sha256,
            terminal_receipt_raw=terminal_receipt_raw,
        )
        return [consumed, retained, terminal]

    results = asyncio.run(exercise())

    assert [result["operation"] for result in results] == [
        "consume_authorization",
        "retain_output",
        "accept_terminal",
    ]
    assert [result["result"]["receipt_id"] for result in results] == [
        "h2consumption_" + hashlib.sha256(job.job_id.encode("utf-8")).hexdigest(),
        "worker-output-shard-00",
        "worker-receipt-h2-001",
    ]
    assert [request.url.path for request in seen] == expected_paths
    assert len({request.headers["x-cas-service-nonce"] for request in seen}) == 3
    assert seen[0].content == (
        b'{"run_nonce_b64url":"'
        + run_nonce.encode("ascii")
        + b'","schema_version":"'
        + HARNESS_V2_CONSUMPTION_REQUEST_SCHEMA.encode("ascii")
        + b'"}'
    )
    output_envelope = json.loads(seen[1].content)
    assert seen[1].content == build_harness_v2_output_retention_request(
        output_name="raw-outcomes",
        artifact_id="worker-output-shard-00",
        artifact_media_type="application/json",
        artifact_body=artifact_body,
    )
    assert output_envelope == {
        "artifact": {
            "artifact_id": "worker-output-shard-00",
            "byte_length": len(artifact_body),
            "media_type": "application/json",
            "raw_base64": base64.b64encode(artifact_body).decode("ascii"),
            "sha256": hashlib.sha256(artifact_body).hexdigest().upper(),
        },
        "output_name": "raw-outcomes",
        "schema_version": HARNESS_V2_OUTPUT_RETENTION_SCHEMA,
    }
    assert output_envelope["artifact"]["sha256"].isupper()
    assert seen[2].content == terminal_receipt_raw
    assert all(f"/worker/{job.assigned_worker_id}/" in path for path in expected_paths)


def test_harness_v2_builders_are_canonical_and_reject_noncanonical_identity():
    run_nonce = base64.urlsafe_b64encode(b"r" * 32).decode("ascii").rstrip("=")

    assert (
        HARNESS_V2_CONSUMPTION_MEDIA_TYPE
        == "application/vnd.cas-harness.run-consumption+json"
    )
    assert (
        HARNESS_V2_OUTPUT_RETENTION_MEDIA_TYPE
        == "application/vnd.cas-harness.output-retention+json"
    )
    assert (
        HARNESS_V2_TERMINAL_MEDIA_TYPE
        == "application/vnd.cas-harness.worker-terminal-receipt+json"
    )
    assert (
        HARNESS_V2_CONSUMPTION_REQUEST_SCHEMA
        == "cas_harness_v2.route_consumption_request.v1"
    )
    assert HARNESS_V2_OUTPUT_RETENTION_SCHEMA == "cas_harness_v2.output_retention.v1"
    assert build_harness_v2_consumption_request(run_nonce) == (
        b'{"run_nonce_b64url":"'
        + run_nonce.encode("ascii")
        + b'","schema_version":"'
        + HARNESS_V2_CONSUMPTION_REQUEST_SCHEMA.encode("ascii")
        + b'"}'
    )
    with pytest.raises(FleetWorkerError, match="failed closed"):
        build_harness_v2_consumption_request(run_nonce + "=")
    with pytest.raises(FleetWorkerError, match="failed closed"):
        build_harness_v2_output_retention_request(
            output_name="raw outcomes",
            artifact_id="worker-output-01",
            artifact_media_type="application/json",
            artifact_body=b"output",
        )


def test_harness_v2_requires_service_identity_without_bearer_fallback(tmp_path: Path):
    config = _config(tmp_path)
    bearer_token = config.bearer_token or ""
    lease_token = "lease-token-" + ("q" * 40)
    run_nonce = base64.urlsafe_b64encode(b"s" * 32).decode("ascii").rstrip("=")
    job = replace(FleetJob.from_api(_leased_job_payload(config)), lease_token=lease_token)
    request_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json={})

    api = FleetApiClient(
        config,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(HarnessV2WorkerPreSendFailure) as captured:
        asyncio.run(
            api.consume_harness_v2_authorization(
                job,
                authorization_sha256="B" * 64,
                run_nonce_b64url=run_nonce,
            )
        )

    message = str(captured.value)
    assert request_count == 0
    assert captured.value.outcome_certainty == "DEFINITE_PRE_SEND_FAILURE"
    assert captured.value.reconcile_only is False
    assert captured.value.retry_allowed is False
    assert message == "Harness-v2 worker protocol request failed closed."
    assert bearer_token not in message
    assert lease_token not in message
    assert run_nonce not in message


def test_harness_v2_failure_is_single_attempt_and_does_not_echo_secrets(tmp_path: Path):
    credential = (
        "casfs_fsc_abcdef0123456789abcdef0123456789."
        "worker-secret-material-0123456789abcdef"
    )
    lease_token = "lease-token-" + ("z" * 40)
    authorization_sha256 = "C" * 64
    run_nonce = base64.urlsafe_b64encode(b"t" * 32).decode("ascii").rstrip("=")
    response_secret = "upstream-private-diagnostic"
    config = replace(
        _config(tmp_path),
        bearer_token=None,
        tenant_id="tenant-a",
        service_credential=credential,
    )
    job = replace(FleetJob.from_api(_leased_job_payload(config)), lease_token=lease_token)
    attempts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request.headers["x-cas-service-nonce"])
        return httpx.Response(
            503,
            text=f"{response_secret}:{credential}:{lease_token}:{run_nonce}",
        )

    api = FleetApiClient(
        config,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(HarnessV2WorkerPostSendIndeterminate) as captured:
        asyncio.run(
            api.consume_harness_v2_authorization(
                job,
                authorization_sha256=authorization_sha256,
                run_nonce_b64url=run_nonce,
            )
        )

    message = str(captured.value)
    assert len(attempts) == 1
    assert captured.value.outcome_certainty == "POST_SEND_INDETERMINATE"
    assert captured.value.reconcile_only is True
    assert captured.value.retry_allowed is False
    assert message == "Harness-v2 worker protocol request failed closed."
    for secret in (response_secret, credential, lease_token, run_nonce):
        assert secret not in message


def test_harness_v2_timeout_after_transport_entry_is_reconcile_only(tmp_path: Path):
    credential = (
        "casfs_fsc_abcdef0123456789abcdef0123456789."
        "worker-secret-material-0123456789abcdef"
    )
    config = replace(
        _config(tmp_path),
        bearer_token=None,
        tenant_id="tenant-a",
        service_credential=credential,
    )
    job = replace(
        FleetJob.from_api(_leased_job_payload(config)),
        lease_token="lease-token-" + ("t" * 40),
    )
    run_nonce = base64.urlsafe_b64encode(b"v" * 32).decode("ascii").rstrip("=")
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("ambiguous after send", request=request)

    api = FleetApiClient(
        config,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(HarnessV2WorkerPostSendIndeterminate) as captured:
        asyncio.run(
            api.consume_harness_v2_authorization(
                job,
                authorization_sha256="F" * 64,
                run_nonce_b64url=run_nonce,
            )
        )

    assert attempts == 1
    assert captured.value.reconcile_only is True
    assert captured.value.retry_allowed is False
    assert str(captured.value) == "Harness-v2 worker protocol request failed closed."


@pytest.mark.parametrize(
    "mutation",
    ("fake", "operation", "nonce", "carrier", "result_schema", "replay_type"),
)
def test_harness_v2_rejects_unbound_or_malformed_200_response(
    tmp_path: Path,
    mutation: str,
):
    config = replace(
        _config(tmp_path),
        bearer_token=None,
        tenant_id="tenant-a",
        service_credential=(
            "casfs_fsc_11111111111111111111111111111111."
            "response-binding-secret-0123456789abcdef"
        ),
    )
    job = replace(
        FleetJob.from_api(_leased_job_payload(config)),
        lease_token="lease-token-" + ("r" * 40),
    )
    run_nonce = base64.urlsafe_b64encode(b"w" * 32).decode("ascii").rstrip("=")
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if mutation == "fake":
            return httpx.Response(200, json={"accepted_step": 0})
        payload = _harness_v2_route_response(
            request,
            job,
            operation="consume_authorization",
            result=_harness_v2_result(
                operation="consume_authorization",
                receipt_id="h2consumption_"
                + hashlib.sha256(job.job_id.encode("utf-8")).hexdigest(),
                receipt_sha256="A" * 64,
            ),
        )
        if mutation == "operation":
            payload["operation"] = "retain_output"
        elif mutation == "nonce":
            payload["intake_receipt"]["nonce_id"] = "fsn_" + ("b" * 64)
        elif mutation == "carrier":
            payload["intake_receipt"]["carrier_sha256"] = "B" * 64
        elif mutation == "result_schema":
            payload["result"]["schema_version"] = (
                "cas_harness_v2.output_route_result.v1"
            )
        elif mutation == "replay_type":
            payload["result"]["idempotent_replay"] = 1
        return httpx.Response(200, json=payload)

    api = FleetApiClient(
        config,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(HarnessV2WorkerPostSendIndeterminate):
        asyncio.run(
            api.consume_harness_v2_authorization(
                job,
                authorization_sha256="A" * 64,
                run_nonce_b64url=run_nonce,
            )
        )
    assert attempts == 1


def test_harness_v2_terminal_exact_replay_requires_same_terminal_binding(tmp_path: Path):
    config = replace(
        _config(tmp_path),
        bearer_token=None,
        tenant_id="tenant-a",
        service_credential=(
            "casfs_fsc_22222222222222222222222222222222."
            "terminal-replay-secret-0123456789abcdef"
        ),
    )
    job = replace(
        FleetJob.from_api(_leased_job_payload(config)),
        lease_token="lease-token-" + ("y" * 40),
    )
    terminal_raw = (
        b'{"receipt_id":"worker-receipt-h2-001","schema_version":'
        b'"cas_harness_v2.worker_terminal_receipt.v1","terminal":'
        b'{"status":"COMPLETED"}}'
    )
    mismatch = False

    def handler(request: httpx.Request) -> httpx.Response:
        result = _harness_v2_result(
            operation="accept_terminal",
            receipt_id="worker-receipt-h2-001",
            receipt_sha256=hashlib.sha256(terminal_raw).hexdigest().upper(),
            idempotent_replay=True,
            terminal_raw=terminal_raw,
        )
        if mismatch:
            result["terminal_status"] = "FAILURE"
        return httpx.Response(
            200,
            json=_harness_v2_route_response(
                request,
                job,
                operation="accept_terminal",
                result=result,
            ),
        )

    api = FleetApiClient(
        config,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    accepted = asyncio.run(
        api.submit_harness_v2_terminal(
            job,
            authorization_sha256="A" * 64,
            terminal_receipt_raw=terminal_raw,
        )
    )
    assert accepted["result"]["idempotent_replay"] is True

    mismatch = True
    with pytest.raises(HarnessV2WorkerPostSendIndeterminate):
        asyncio.run(
            api.submit_harness_v2_terminal(
                job,
                authorization_sha256="A" * 64,
                terminal_receipt_raw=terminal_raw,
            )
        )


def test_harness_v2_rejects_lowercase_authorization_digest_before_http(tmp_path: Path):
    config = replace(
        _config(tmp_path),
        bearer_token=None,
        tenant_id="tenant-a",
        service_credential=(
            "casfs_fsc_33333333333333333333333333333333."
            "worker-secret-material-0123456789abcdef"
        ),
    )
    job = replace(
        FleetJob.from_api(_leased_job_payload(config)),
        lease_token="lease-token-" + ("m" * 40),
    )
    run_nonce = base64.urlsafe_b64encode(b"u" * 32).decode("ascii").rstrip("=")
    request_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json={})

    api = FleetApiClient(
        config,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(FleetWorkerError, match="failed closed"):
        asyncio.run(
            api.consume_harness_v2_authorization(
                job,
                authorization_sha256="d" * 64,
                run_nonce_b64url=run_nonce,
            )
        )
    assert request_count == 0


def test_command_executor_uses_only_lease_bound_identity_and_attested_result(
    monkeypatch,
    tmp_path: Path,
):
    config = _config(tmp_path)
    job = FleetJob.from_api(_leased_job_payload(config, bound=True))
    attestation = _real_model_attestation(job)
    result_payload = {
        "produced_outputs": ["layer_activation_summary"],
        "evidence_payload": attestation,
    }
    monkeypatch.setenv("CAS_FLEET_MODEL_ID", "attacker/model")
    monkeypatch.setenv("CAS_FLEET_MODEL_REVISION", "f" * 40)
    monkeypatch.setenv("CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH", "/attacker/manifest.json")
    monkeypatch.setenv("CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256", "f" * 64)
    monkeypatch.setenv("CAS_FLEET_TRUST_REMOTE_CODE", "true")
    command = (
        sys.executable,
        "-c",
        (
            "import json, os, pathlib; "
            "p=pathlib.Path(os.environ['CAS_FLEET_RESULT_PATH']); "
            "p.with_suffix('.env.json').write_text(json.dumps({k: os.environ[k] for k in "
            "['CAS_FLEET_MODEL_ID','CAS_FLEET_MODEL_REVISION',"
            "'CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH',"
            "'CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256','CAS_FLEET_TRUST_REMOTE_CODE']})); "
            f"p.write_text({json.dumps(json.dumps(result_payload))}, encoding='utf-8')"
        ),
    )
    executor = CommandFleetJobExecutor(command, timeout_seconds=20)

    result = asyncio.run(executor.run(job, config))

    assert result.status == "completed"
    assert result.produced_outputs == ("layer_activation_summary",)
    assert set(result.missing_outputs) == {
        "cas_axis_readout",
        "blindspot_overlay",
        "worker_evidence_manifest",
    }
    observed_env = json.loads(
        (tmp_path / "fleet-job-001.probe-result.env.json").read_text(encoding="utf-8")
    )
    assert observed_env == {
        "CAS_FLEET_MODEL_ID": config.model_id,
        "CAS_FLEET_MODEL_REVISION": job.model_revision,
        "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH": job.model_artifact_manifest_path,
        "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256": job.model_artifact_manifest_sha256,
        "CAS_FLEET_TRUST_REMOTE_CODE": "false",
    }


def test_command_executor_does_not_reuse_stale_result(tmp_path: Path):
    config = _config(tmp_path)
    job = FleetJob.from_api(_leased_job_payload(config, bound=True))
    stale_path = tmp_path / "fleet-job-001.probe-result.json"
    stale_path.write_text(
        json.dumps(
            {
                "produced_outputs": ["layer_activation_summary"],
                "evidence_payload": _real_model_attestation(job),
            }
        ),
        encoding="utf-8",
    )
    executor = CommandFleetJobExecutor((sys.executable, "-c", "pass"), timeout_seconds=20)

    result = asyncio.run(executor.run(job, config))

    assert result.status == "failed"
    assert result.error_message == "Probe command did not write CAS_FLEET_RESULT_PATH."
    assert not stale_path.exists()


def test_real_model_forward_status_without_artifact_attestation_is_rejected(
    tmp_path: Path,
):
    config = _config(tmp_path)
    job = FleetJob.from_api(_leased_job_payload(config, bound=True))
    result_path = tmp_path / "unattested-result.json"
    result_path.write_text(
        json.dumps(
            {
                "produced_outputs": ["layer_activation_summary"],
                "evidence_payload": {
                    "status": "real_model_forward_completed",
                    "audit_id": job.audit_id,
                    "job_id": job.job_id,
                },
            }
        ),
        encoding="utf-8",
    )

    from app.runtime.fleet_worker import _parse_command_result

    result = _parse_command_result(result_path, job)

    assert result.status == "failed"
    assert "attestation" in (result.error_message or "").lower()


def test_command_executor_rejects_unknown_outputs(tmp_path: Path):
    config = _config(tmp_path)
    job = FleetJob.from_api(_leased_job_payload(config))
    result_path = tmp_path / "bad-result.json"
    result_path.write_text(json.dumps({"produced_outputs": ["made_up_output"]}), encoding="utf-8")

    from app.runtime.fleet_worker import _parse_command_result

    result = _parse_command_result(result_path, job)

    assert result.status == "failed"
    assert "unknown outputs" in (result.error_message or "")
