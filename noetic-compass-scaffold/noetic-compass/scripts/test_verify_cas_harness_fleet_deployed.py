"""Unit tests for scripts/verify_cas_harness_fleet_deployed.py."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import verify_cas_harness_fleet_deployed as verifier  # noqa: E402


def test_fragment_ref_matches_fleet_executor_builder() -> None:
    from api.services.cas_harness_fleet_executor import build_evidence_fragment_ref

    payload = {
        "audit_id": "audit-123",
        "job_id": "fleet-job-abc",
        "worker_id": "worker-001",
        "model_id": "deploy-check/open-weight-300b",
        "layer_start": 0,
        "layer_end": 2,
        "shard_id": "shard-001",
        "expected_outputs": ["worker_evidence_manifest", "layer_probe_summary"],
        "produced_outputs": ["worker_evidence_manifest", "layer_probe_summary"],
        "missing_outputs": [],
    }

    assert verifier.build_evidence_fragment_ref(**payload) == build_evidence_fragment_ref(**payload)


def test_token_resolution_and_authorization_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(verifier.TOKEN_ENV_VAR, " env-token ")

    assert verifier.resolve_bearer_token(None) == "env-token"
    assert verifier.resolve_bearer_token(" cli-token ") == "cli-token"
    assert verifier.authorization_header("raw-token") == "Bearer raw-token"
    assert verifier.authorization_header("Bearer already-prefixed") == "Bearer already-prefixed"

    monkeypatch.delenv(verifier.TOKEN_ENV_VAR)
    assert verifier.resolve_bearer_token(None) is None
    assert verifier.authorization_header(None) is None


def test_non_lease_fleet_response_must_not_expose_lease_token() -> None:
    with pytest.raises(verifier.GateFailure, match="non-lease fleet response exposed lease_token"):
        verifier.require_no_lease_token_exposed(
            "prepare-fleet-jobs",
            {"jobs": [{"job_id": "fleet-job-abc", "lease_token": None}]},
        )


def test_main_sends_bearer_rejects_forged_ref_and_submits_valid_ref(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api = _FakeFleetApi()
    monkeypatch.setattr(verifier, "urlopen", api.urlopen)

    exit_code = verifier.main(
        [
            "--base-url",
            "https://api.example.test",
            "--workers",
            "2",
            "--bearer-token",
            "cli-token",
        ]
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Authorization: bearer token configured" in out
    assert "control-plane/fleet receipt path only" in out
    assert "no real 300B inference" in out
    assert all(headers.get("Authorization") == "Bearer cli-token" for headers in api.headers)
    assert api.receipt_refs[0] == f"deploy-check-fragment://{api.leased_job['job_id']}"
    assert api.receipt_refs[1] == api.expected_fragment_ref


class _FakeFleetApi:
    def __init__(self) -> None:
        self.audit_id = "audit-deploy-check"
        self.model_id = "deploy-check/open-weight-300b"
        self.registered_workers: set[str] = set()
        self.headers: list[dict[str, str]] = []
        self.receipt_refs: list[str] = []
        self.worker_assignments = [
            {
                "worker_id": "worker-001",
                "layer_start": 0,
                "layer_end": 1,
                "shard_id": "shard-001",
                "assigned_methods": ["foundation_probe"],
                "expected_outputs": ["worker_evidence_manifest"],
            },
            {
                "worker_id": "worker-002",
                "layer_start": 2,
                "layer_end": 2,
                "shard_id": "shard-002",
                "assigned_methods": ["targeted_ablation"],
                "expected_outputs": ["worker_evidence_manifest"],
            },
        ]
        self.leased_job = {
            "job_id": "fleet-job-001",
            "audit_id": self.audit_id,
            "assigned_worker_id": "worker-001",
            "layer_start": 0,
            "layer_end": 1,
            "shard_id": "shard-001",
            "assigned_methods": ["foundation_probe"],
            "expected_outputs": ["worker_evidence_manifest"],
            "status": "leased",
            "lease_token": "lease-token-001",
            "lease_expires_at": "2026-05-26T00:00:00+00:00",
            "evidence_packet_fragment_ref": None,
            "produced_outputs": [],
            "missing_outputs": [],
            "error_message": None,
            "updated_at": "2026-05-26T00:00:00+00:00",
        }
        self.expected_fragment_ref = verifier.build_evidence_fragment_ref(
            audit_id=self.audit_id,
            job_id=self.leased_job["job_id"],
            worker_id="worker-001",
            model_id=self.model_id,
            layer_start=self.leased_job["layer_start"],
            layer_end=self.leased_job["layer_end"],
            shard_id=self.leased_job["shard_id"],
            expected_outputs=self.leased_job["expected_outputs"],
            produced_outputs=self.leased_job["expected_outputs"],
            missing_outputs=[],
        )

    def urlopen(self, request, timeout: int):  # noqa: ANN001
        del timeout
        self.headers.append(dict(request.header_items()))
        path = urlparse(request.full_url).path
        payload = _request_payload(request)

        if path == "/api/cas-harness/audit/distributed/session":
            return _JsonResponse(
                {
                    "audit_id": self.audit_id,
                    "total_workers": 2,
                    "verdict": None,
                }
            )

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/dispatch":
            return _JsonResponse(
                {
                    "status": "DISPATCHED",
                    "plan": {"model_id": self.model_id},
                    "worker_evidence": self.worker_assignments,
                }
            )

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/fleet/prepare":
            return _JsonResponse(
                {
                    "total_jobs": 2,
                    "verifier_gate_status": "waiting_for_workers",
                    "jobs": [{"job_id": "fleet-job-001"}, {"job_id": "fleet-job-002"}],
                }
            )

        if path == "/api/cas-harness/audit/distributed/fleet/worker/register":
            assert payload is not None
            self.registered_workers.add(payload["worker_id"])
            return _JsonResponse(
                {
                    "worker_id": payload["worker_id"],
                    "model_id": payload["model_id"],
                    "worker_url": payload["worker_url"],
                    "gpu_type": payload["gpu_type"],
                    "capacity": payload["capacity"],
                    "supported_methods": payload["supported_methods"],
                    "registered_at": "2026-05-26T00:00:00+00:00",
                    "last_heartbeat_at": "2026-05-26T00:00:00+00:00",
                    "status": "active",
                }
            )

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/fleet/job/lease":
            assert payload is not None
            if payload["worker_id"] not in self.registered_workers:
                raise _http_error(request, 409, "Worker must register before leasing jobs.")
            return _JsonResponse(self.leased_job)

        receipt_path = (
            f"/api/cas-harness/audit/distributed/session/{self.audit_id}"
            f"/fleet/job/{self.leased_job['job_id']}/receipt"
        )
        if path == receipt_path:
            assert payload is not None
            fragment_ref = payload["evidence_packet_fragment_ref"]
            self.receipt_refs.append(fragment_ref)
            if fragment_ref != self.expected_fragment_ref:
                raise _http_error(
                    request,
                    409,
                    "Evidence Packet fragment ref failed hash/assignment validation for this audit job.",
                )
            return _JsonResponse(
                {
                    "completed_fragments": 1,
                    "verifier_gate_status": "waiting_for_workers",
                    "jobs": [{"job_id": self.leased_job["job_id"], "status": "completed"}],
                }
            )

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/fleet/merge":
            raise _http_error(
                request,
                409,
                "Fleet evidence cannot merge until every assigned job returns a receipt.",
            )

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/merge":
            return _JsonResponse({"verdict": None})

        raise AssertionError(f"unexpected POST {path}")


class _JsonResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_JsonResponse":
        return self

    def __exit__(self, *args) -> None:  # noqa: ANN002
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _request_payload(request) -> dict | None:  # noqa: ANN001
    if request.data is None:
        return None
    return json.loads(request.data.decode("utf-8"))


def _http_error(request, status_code: int, detail: str) -> HTTPError:  # noqa: ANN001
    body = io.BytesIO(json.dumps({"detail": detail}).encode("utf-8"))
    return HTTPError(request.full_url, status_code, "error", {}, body)
