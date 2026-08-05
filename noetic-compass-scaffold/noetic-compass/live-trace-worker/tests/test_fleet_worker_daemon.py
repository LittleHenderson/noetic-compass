"""Worker-daemon tests for distributed CAS Harness fleet jobs."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

import httpx

from app.runtime.fleet_worker import (
    CommandFleetJobExecutor,
    DryRunFleetJobExecutor,
    FleetApiClient,
    FleetJob,
    FleetJobExecutionResult,
    FleetWorkerConfig,
    FleetWorkerDaemon,
    build_evidence_fragment_ref,
)


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
