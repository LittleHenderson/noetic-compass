"""Unit tests for scripts/verify_evidence_anchor_deployed.py."""

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

import verify_evidence_anchor_deployed as verifier  # noqa: E402


def test_fragment_ref_with_payload_matches_fleet_executor_builder() -> None:
    from api.services.cas_harness_fleet_executor import build_evidence_fragment_ref

    fragment_payload = verifier.stage19_stage20_verifier_fragment()
    payload = {
        "audit_id": "audit-123",
        "job_id": "fleet-job-abc",
        "worker_id": "worker-001",
        "model_id": "deploy-check/open-weight-anchor-smoke-1b",
        "layer_start": 0,
        "layer_end": 0,
        "shard_id": "shard-001",
        "expected_outputs": ["worker_evidence_manifest"],
        "produced_outputs": ["worker_evidence_manifest"],
        "missing_outputs": [],
        "evidence_packet_fragment_payload": fragment_payload,
    }

    assert verifier.build_evidence_fragment_ref(**payload) == build_evidence_fragment_ref(**payload)


def test_main_fetches_token_merges_packet_and_requires_s3(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    api = _FakeAnchorApi(anchor_status="anchored", anchor_mode="s3")
    monkeypatch.setattr(verifier, "urlopen", api.urlopen)

    exit_code = verifier.main(["--base-url", "https://api.example.test"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Authorization: bearer token from /auth/token" in output
    assert "verifier ACCEPT" in output
    assert "anchor status=anchored mode=s3" in output
    assert api.receipt_fragment_ref == api.expected_fragment_ref
    assert all(headers.get("Authorization") == "Bearer fetched-token" for headers in api.protected_headers)


def test_main_heartbeats_existing_worker_and_continues(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    api = _FakeAnchorApi(anchor_status="anchored", anchor_mode="s3", worker_already_registered=True)
    monkeypatch.setattr(verifier, "urlopen", api.urlopen)

    exit_code = verifier.main(["--base-url", "https://api.example.test", "--bearer-token", "cli-token"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert api.worker_heartbeat_count == 1
    assert "anchor status=anchored mode=s3" in output


def test_main_fails_when_s3_is_required_but_anchor_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _FakeAnchorApi(anchor_status="disabled", anchor_mode="disabled")
    monkeypatch.setattr(verifier, "urlopen", api.urlopen)

    with pytest.raises(verifier.AnchorSmokeFailure, match="expected anchor mode 's3'"):
        verifier.main(["--base-url", "https://api.example.test", "--bearer-token", "cli-token"])


class _FakeAnchorApi:
    def __init__(
        self,
        *,
        anchor_status: str,
        anchor_mode: str,
        worker_already_registered: bool = False,
    ) -> None:
        self.anchor_status = anchor_status
        self.anchor_mode = anchor_mode
        self.worker_already_registered = worker_already_registered
        self.worker_heartbeat_count = 0
        self.audit_id = "audit-anchor-smoke"
        self.trace_id = f"{self.audit_id}-distributed-merge"
        self.model_id = "deploy-check/open-weight-anchor-smoke-1b"
        self.protected_headers: list[dict[str, str]] = []
        self.receipt_fragment_ref: str | None = None
        self.worker = {
            "worker_id": "worker-anchor-001",
            "layer_start": 0,
            "layer_end": 0,
            "shard_id": "shard-001",
            "assigned_methods": ["foundation_probe"],
            "expected_outputs": ["worker_evidence_manifest"],
        }
        self.leased_job = {
            "job_id": "fleet-job-anchor-001",
            "audit_id": self.audit_id,
            "assigned_worker_id": self.worker["worker_id"],
            "layer_start": 0,
            "layer_end": 0,
            "shard_id": self.worker["shard_id"],
            "assigned_methods": ["foundation_probe"],
            "expected_outputs": ["worker_evidence_manifest"],
            "status": "leased",
            "lease_token": "lease-token-anchor",
            "lease_expires_at": "2026-05-28T00:00:00+00:00",
            "evidence_packet_fragment_ref": None,
            "produced_outputs": [],
            "missing_outputs": [],
            "error_message": None,
            "updated_at": "2026-05-28T00:00:00+00:00",
        }
        self.expected_fragment_ref = verifier.build_evidence_fragment_ref(
            audit_id=self.audit_id,
            job_id=self.leased_job["job_id"],
            worker_id=self.worker["worker_id"],
            model_id=self.model_id,
            layer_start=0,
            layer_end=0,
            shard_id=self.worker["shard_id"],
            expected_outputs=self.leased_job["expected_outputs"],
            produced_outputs=self.leased_job["expected_outputs"],
            missing_outputs=[],
            evidence_packet_fragment_payload=verifier.stage19_stage20_verifier_fragment(),
        )

    def urlopen(self, request, timeout: int):  # noqa: ANN001
        del timeout
        path = urlparse(request.full_url).path
        payload = _request_payload(request)
        headers = dict(request.header_items())
        if path != "/auth/token":
            self.protected_headers.append(headers)

        if path == "/auth/token":
            return _JsonResponse({"token": "fetched-token", "expires_in_minutes": 60})

        if path == "/api/cas-harness/audit/distributed/session":
            return _JsonResponse({"audit_id": self.audit_id, "total_workers": 1})

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/dispatch":
            return _JsonResponse(
                {
                    "status": "DISPATCHED",
                    "plan": {"model_id": self.model_id},
                    "worker_evidence": [self.worker],
                }
            )

        if path == "/api/cas-harness/audit/distributed/fleet/worker/register":
            assert payload is not None
            if self.worker_already_registered:
                raise _http_error(request, 409, "Worker ID is already registered; heartbeat the existing worker instead.")
            return _JsonResponse(
                {
                    "worker_id": payload["worker_id"],
                    "model_id": payload["model_id"],
                    "worker_url": payload["worker_url"],
                    "gpu_type": payload["gpu_type"],
                    "capacity": payload["capacity"],
                    "supported_methods": payload["supported_methods"],
                    "registered_at": "2026-05-28T00:00:00+00:00",
                    "last_heartbeat_at": "2026-05-28T00:00:00+00:00",
                    "status": "active",
                }
            )

        if path == f"/api/cas-harness/audit/distributed/fleet/worker/{self.worker['worker_id']}/heartbeat":
            self.worker_heartbeat_count += 1
            return _JsonResponse(
                {
                    "worker_id": self.worker["worker_id"],
                    "model_id": self.model_id,
                    "worker_url": f"https://{self.worker['worker_id']}.anchor-smoke.internal",
                    "gpu_type": "anchor-smoke",
                    "capacity": 1,
                    "supported_methods": self.worker["assigned_methods"],
                    "registered_at": "2026-05-28T00:00:00+00:00",
                    "last_heartbeat_at": "2026-05-28T00:00:01+00:00",
                    "status": "active",
                }
            )

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/fleet/prepare":
            return _JsonResponse({"total_jobs": 1, "verifier_gate_status": "waiting_for_receipts"})

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/fleet/job/lease":
            return _JsonResponse(self.leased_job)

        receipt_path = (
            f"/api/cas-harness/audit/distributed/session/{self.audit_id}"
            f"/fleet/job/{self.leased_job['job_id']}/receipt"
        )
        if path == receipt_path:
            assert payload is not None
            self.receipt_fragment_ref = payload["evidence_packet_fragment_ref"]
            if self.receipt_fragment_ref != self.expected_fragment_ref:
                raise _http_error(request, 409, "fragment ref failed hash/assignment validation")
            return _JsonResponse({"verifier_gate_status": "ready_for_verifier"})

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/fleet/merge":
            return _JsonResponse({"merged_packet_trace_id": self.trace_id})

        if path == f"/api/cas-harness/audit/distributed/session/{self.audit_id}/fleet/verifier":
            return _JsonResponse({"verdict": "ACCEPT"})

        if path == f"/evidence/{self.trace_id}" and request.get_method() == "GET":
            return _JsonResponse(
                {
                    "trace_id": self.trace_id,
                    "hashes": {
                        "external_anchor": {
                            "status": self.anchor_status,
                            "mode": self.anchor_mode,
                            "anchor_uri": (
                                "s3://cas-harness-anchor/smoke/entry.json"
                                if self.anchor_mode == "s3"
                                else None
                            ),
                            "bucket": "cas-harness-anchor" if self.anchor_mode == "s3" else None,
                            "key": "smoke/entry.json" if self.anchor_mode == "s3" else None,
                            "manifest_sha256": "a" * 64,
                        }
                    },
                }
            )

        if path == f"/evidence/{self.trace_id}/verify":
            return _JsonResponse(
                {
                    "overall": "all_match",
                    "checks": [
                        {
                            "artifact": "merged_packet_external_anchor",
                            "expected": "a" * 64,
                            "actual": "a" * 64,
                            "match": True,
                            "notes": "S3 anchor write receipt is present",
                        }
                    ],
                }
            )

        raise AssertionError(f"unexpected request {request.get_method()} {path}")


class _JsonResponse:
    def __init__(self, payload: dict[str, object]) -> None:
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
