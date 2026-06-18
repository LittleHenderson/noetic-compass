"""Worker-daemon tests for distributed CAS Harness fleet jobs."""

from __future__ import annotations

import asyncio
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


def _leased_job_payload(config: FleetWorkerConfig) -> dict[str, Any]:
    return {
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
        "lease_expires_at": "2026-05-26T00:00:00+00:00",
        "evidence_packet_fragment_ref": None,
        "produced_outputs": [],
        "missing_outputs": [],
        "error_message": None,
        "updated_at": "2026-05-26T00:00:00+00:00",
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
            )
            assert payload["evidence_packet_fragment_ref"] == expected_ref
            assert payload["job_status"] == "completed"
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


def test_daemon_posts_evidence_payload_under_fragment_hash(tmp_path: Path):
    config = _config(tmp_path)
    leased_job = _leased_job_payload(config)
    evidence_payload = {
        "schema_version": "cas_harness_open_weight_probe_shard.v1",
        "structural_monitoring": {
            "schema_version": "cas_harness_structural_monitoring.v0.shadow",
            "mode": "shadow",
            "status": "present",
            "verdict_effect": "none_shadow_only",
            "basis": "measured",
            "drift_score": 0.03,
            "drift_threshold": 0.2,
            "claim_ceiling": "Structural signal only; verdict_effect none_shadow_only.",
        },
    }
    seen: dict[str, Any] = {"receipt": None}

    class PayloadExecutor:
        execution_mode = "payload_probe"

        async def run(self, job: FleetJob, config: FleetWorkerConfig) -> FleetJobExecutionResult:
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
                evidence_packet_fragment_payload=evidence_payload,
            )
            assert payload["evidence_packet_fragment_ref"] == expected_ref
            assert payload["evidence_packet_fragment_payload"] == evidence_payload
            return httpx.Response(200, json={"verifier_gate_status": "waiting_for_receipts"})
        raise AssertionError(f"unexpected path {request.url.path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    daemon = FleetWorkerDaemon(
        config,
        PayloadExecutor(),
        api_client=FleetApiClient(config, client=client),
    )

    result = asyncio.run(daemon.run_once())

    assert result.status == "completed"
    assert seen["receipt"]["evidence_packet_fragment_payload"] == evidence_payload
    fragment = json.loads((tmp_path / f"{leased_job['job_id']}.evidence-fragment.json").read_text(encoding="utf-8"))
    assert fragment["evidence_payload"] == evidence_payload
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
    }

    assert build_evidence_fragment_ref(**kwargs) == api_builder(**kwargs)


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


def test_command_executor_uses_probe_command_result(tmp_path: Path):
    config = _config(tmp_path)
    job = FleetJob.from_api(_leased_job_payload(config))
    command = (
        sys.executable,
        "-c",
        (
            "import json, os, pathlib; "
            "pathlib.Path(os.environ['CAS_FLEET_RESULT_PATH']).write_text("
            "json.dumps({'produced_outputs': ['layer_activation_summary']}), encoding='utf-8')"
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


def test_command_executor_rejects_unknown_outputs(tmp_path: Path):
    config = _config(tmp_path)
    job = FleetJob.from_api(_leased_job_payload(config))
    result_path = tmp_path / "bad-result.json"
    result_path.write_text(json.dumps({"produced_outputs": ["made_up_output"]}), encoding="utf-8")

    from app.runtime.fleet_worker import _parse_command_result

    result = _parse_command_result(result_path, job)

    assert result.status == "failed"
    assert "unknown outputs" in (result.error_message or "")
