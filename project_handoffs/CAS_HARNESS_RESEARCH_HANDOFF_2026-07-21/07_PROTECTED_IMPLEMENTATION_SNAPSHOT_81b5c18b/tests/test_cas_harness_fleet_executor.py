from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import base64
import hashlib
import json
import sys
import types

import pytest

from api.config import settings
from api.middleware.auth import create_token
from api.services.cas_harness_distributed_audits import reset_distributed_audits_for_tests
from api.services.cas_harness_fleet_executor import (
    build_evidence_fragment_ref,
    list_workers,
    reset_fleet_executor_for_tests,
)
from api.services.cas_harness_merged_evidence_packets import (
    load_merged_fleet_evidence_packet_payload,
    reset_merged_fleet_evidence_packets_for_tests,
)


def setup_function() -> None:
    reset_fleet_executor_for_tests()
    reset_distributed_audits_for_tests()


@pytest.fixture(autouse=True)
def _stable_object_lock_receipt_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings,
        "object_lock_receipt_attestation_key",
        "test-object-lock-receipt-key-32-bytes-minimum",
    )


@pytest.fixture
def auth_headers(request) -> dict[str, str]:
    token = create_token(
        sub=f"test-user-{request.node.name}",
        api_key=f"test-key-{request.node.nodeid}",
    )
    return {"Authorization": f"Bearer {token}"}


def _scale_payload(parameter_count_b: int = 20, num_layers: int = 8, **overrides) -> dict:
    # A fleet run is a real distributed run, so it must acknowledge the audit's data
    # capture (universal run-gate 8): every distributed run harvests the model's signal
    # to the immutable store regardless of size. The base body carries the ack; overrides
    # can still pop or flip it for tests that exercise a missing acknowledgment.
    payload = {
        "model_id": f"customer/open-weight-{parameter_count_b}b",
        "weight_access": "open_weight",
        "parameter_count_b": parameter_count_b,
        "num_layers": num_layers,
        "precision": "int4" if parameter_count_b == 300 else "bf16",
        "available_gpu_memory_gb": 80,
        "accept_audit_data_capture": True,
    }
    payload.update(overrides)
    return payload


def _create_dispatched_audit(client, auth_headers: dict[str, str], **overrides) -> dict:
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(**overrides),
        headers=auth_headers,
    )
    assert created.status_code == 200
    audit = created.json()
    dispatched = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/dispatch",
        headers=auth_headers,
    )
    assert dispatched.status_code == 200
    return dispatched.json()


def _worker_registration_payload(
    worker: dict,
    model_id: str = "customer/open-weight-20b",
) -> dict:
    return {
        "worker_id": worker["worker_id"],
        "model_id": model_id,
        "worker_url": f"https://{worker['worker_id']}.workers.example",
        "gpu_type": "H100-80GB",
        "capacity": 1,
        "supported_methods": worker["assigned_methods"],
    }


def _register_worker(
    client,
    auth_headers: dict[str, str],
    worker: dict,
    model_id: str = "customer/open-weight-20b",
) -> dict:
    resp = client.post(
        "/api/cas-harness/audit/distributed/fleet/worker/register",
        json=_worker_registration_payload(worker, model_id),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _fragment_ref_for(
    audit: dict,
    job: dict,
    *,
    produced_outputs: list[str] | None = None,
    evidence_packet_fragment_payload: dict | None = None,
) -> str:
    produced = produced_outputs or job["expected_outputs"]
    return build_evidence_fragment_ref(
        audit_id=audit["audit_id"],
        job_id=job["job_id"],
        worker_id=job["assigned_worker_id"],
        model_id=audit["plan"]["model_id"],
        layer_start=job["layer_start"],
        layer_end=job["layer_end"],
        shard_id=job["shard_id"],
        expected_outputs=job["expected_outputs"],
        produced_outputs=produced,
        evidence_packet_fragment_payload=evidence_packet_fragment_payload,
    )


def _stage19_stage20_verifier_fragment() -> dict:
    return {
        "schema_version": "cas_harness_evidence_fragment.v1",
        "provenance": {
            "source_reports": [
                "stage19_verification_stack_worker_fragment.json",
                "stage20_generation_readiness_worker_fragment.json",
            ],
        },
        "verification": {
            "accepted": True,
            "mode": "BALANCED",
            "mode_profile": {
                "accepted_accuracy": 0.91,
                "coverage": 0.74,
            },
            "proof_chips": [
                {"id": "model_proof", "status": "verified", "detail": "Model shard loaded."},
                {"id": "cas_readout", "status": "verified", "detail": "CAS readout present."},
                {"id": "causal_proof", "status": "verified", "detail": "Causal proof present."},
                {"id": "control_proof", "status": "verified", "detail": "Control proof present."},
                {"id": "output_proof", "status": "verified", "detail": "Output proof present."},
                {"id": "packet_proof", "status": "present", "detail": "Packet proof present."},
            ],
        },
        "generation_readiness": {
            "generation_readiness": "allow",
            "risk_score": 0.09,
            "policy_version": "stage20_worker_fragment_v1",
        },
    }


class _FakeS3Body:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class _FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.versions: dict[tuple[str, str], str] = {}
        self.object_locks: dict[tuple[str, str], dict] = {}
        self.put_calls: list[dict] = []
        self.get_calls: list[tuple[str, str]] = []
        self.head_calls: list[tuple[str, str]] = []

    def put_object(self, **kwargs) -> dict:
        self.put_calls.append(dict(kwargs))
        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        body = kwargs["Body"]
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.objects[(bucket, key)] = body
        version_id = f"version-{len(self.put_calls)}"
        self.versions[(bucket, key)] = version_id
        if kwargs.get("ObjectLockMode") and kwargs.get("ObjectLockRetainUntilDate"):
            self.object_locks[(bucket, key)] = {
                "ObjectLockMode": kwargs["ObjectLockMode"],
                "ObjectLockRetainUntilDate": kwargs["ObjectLockRetainUntilDate"],
                "Metadata": dict(kwargs.get("Metadata") or {}),
            }
        return {
            "ETag": f'"{hashlib.md5(body).hexdigest()}"',
            "VersionId": version_id,
        }

    def get_object(self, **kwargs) -> dict:
        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        assert kwargs.get("VersionId") == self.versions[(bucket, key)]
        self.get_calls.append((bucket, key))
        return {
            "Body": _FakeS3Body(self.objects[(bucket, key)]),
            "VersionId": self.versions[(bucket, key)],
        }

    def head_object(self, **kwargs) -> dict:
        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        assert kwargs.get("VersionId") == self.versions[(bucket, key)]
        self.head_calls.append((bucket, key))
        return {
            **self.object_locks.get((bucket, key), {}),
            "VersionId": self.versions[(bucket, key)],
        }


def test_fleet_routes_registered(client):
    openapi = client.get("/openapi.json").json()

    assert "/api/cas-harness/audit/distributed/fleet/worker/register" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}/fleet/prepare" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/lease" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}/fleet/job/{job_id}/receipt" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}/fleet/merge" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}/fleet/verifier" in openapi["paths"]


def test_fleet_prepare_requires_dispatched_distributed_audit(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
        headers=auth_headers,
    ).json()

    resp = client.post(
        f"/api/cas-harness/audit/distributed/session/{created['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )

    assert resp.status_code == 409
    assert "Dispatch the distributed audit" in resp.text


def test_worker_registration_job_lease_receipt_and_merge_path(client, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path))
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])

    prepared = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    assert prepared.status_code == 200
    prepared_body = prepared.json()
    assert prepared_body["verifier_gate_status"] == "waiting_for_receipts"
    assert prepared_body["readiness"]["status"] == "waiting"
    assert prepared_body["readiness"]["verifier_owned"] is True
    assert "fragment receipt" in " ".join(prepared_body["readiness"]["blockers"])
    assert prepared_body["registered_workers"] == 1
    assert prepared_body["total_jobs"] == 1
    assert all(job["lease_token"] is None for job in prepared_body["jobs"])

    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    )
    assert leased.status_code == 200
    leased_job = leased.json()
    assert leased_job["status"] == "leased"
    assert leased_job["lease_token"]
    fragment_ref = _fragment_ref_for(audit, leased_job)

    receipt = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased_job['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased_job["lease_token"],
            "produced_outputs": leased_job["expected_outputs"],
            "evidence_packet_fragment_ref": fragment_ref,
        },
        headers=auth_headers,
    )
    assert receipt.status_code == 200
    receipt_body = receipt.json()
    assert receipt_body["completed_fragments"] == 1
    assert receipt_body["verifier_gate_status"] == "ready_for_verifier"
    assert receipt_body["readiness"] == {
        "status": "ready",
        "headline": "Large-model worker receipts are complete; verifier review is unblocked.",
        "blockers": [],
        "next_actions": [
            "Merge fleet evidence into one distributed Evidence Packet.",
            "Then run the verifier decision layer; fleet merge alone cannot ACCEPT.",
        ],
        "verifier_owned": True,
    }
    assert all(job["lease_token"] is None for job in receipt_body["jobs"])

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/merge",
        headers=auth_headers,
    )
    assert merged.status_code == 200
    merged_body = merged.json()
    assert merged_body["status"] == "COMPLETE"
    assert merged_body["merged_packet_trace_id"] == f"{audit['audit_id']}-distributed-merge"
    assert "does not fabricate ACCEPT" in merged_body["merge_reason"]
    assert merged_body["readiness"]["status"] == "ready"
    assert merged_body["readiness"]["next_actions"] == [
        "Run the verifier decision layer over the merged Evidence Packet.",
    ]
    assert all(job["lease_token"] is None for job in merged_body["jobs"])

    verifier = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/verifier",
        headers=auth_headers,
    )
    assert verifier.status_code == 200
    verifier_body = verifier.json()
    assert verifier_body["audit_id"] == audit["audit_id"]
    assert verifier_body["merged_packet_trace_id"] == f"{audit['audit_id']}-distributed-merge"
    assert verifier_body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert verifier_body["confidence"] is None
    assert verifier_body["source"] == "fleet_packet_verifier"
    assert verifier_body["decision_scope"] == "distributed_fleet_merged_packet"
    assert verifier_body["coverage"] == {
        "basis": "fleet_worker_fragments",
        "total_jobs": 1,
        "completed_fragments": 1,
        "failed_jobs": 0,
        "missing_output_jobs": 0,
        "distributed_merge_status": "complete",
    }
    assert verifier_body["proof_chip_gate"] == "unavailable"
    assert "no explicit proof-chip verifier decision" in " ".join(verifier_body["blockers"])
    assert "FLAG FOR HUMAN REVIEW" in " ".join(verifier_body["next_actions"])

    packet = client.get(f"/evidence/{merged_body['merged_packet_trace_id']}", headers=auth_headers)
    assert packet.status_code == 200
    packet_body = packet.json()
    assert packet_body["schema_version"] == "cas_harness_evidence_packet_v1"
    assert packet_body["distributed_fleet"]["audit_id"] == audit["audit_id"]
    assert packet_body["distributed_fleet"]["total_jobs"] == 1
    assert packet_body["verification"]["proof_chips"]
    assert packet_body["verification"]["accepted"] is None
    assert packet_body["hashes"]["hash_log_entry_sha256"]
    assert packet_body["hashes"]["external_anchor"]["status"] == "disabled"

    reset_merged_fleet_evidence_packets_for_tests()
    reloaded = load_merged_fleet_evidence_packet_payload(merged_body["merged_packet_trace_id"])
    assert reloaded["trace_id"] == merged_body["merged_packet_trace_id"]

    verified = client.post(f"/evidence/{merged_body['merged_packet_trace_id']}/verify", headers=auth_headers)
    assert verified.status_code == 200
    verify_body = verified.json()
    assert verify_body["overall"] == "all_match"
    assert {
        check["artifact"]
        for check in verify_body["checks"]
    }.issuperset(
        {
            "merged_packet_payload",
            "merged_packet_hash_log",
            "merged_packet_hash_chain",
            "merged_packet_external_anchor",
        }
    )

    (tmp_path / "hash-log.jsonl").write_text(
        (tmp_path / "hash-log.jsonl").read_text(encoding="utf-8") + "not-json\n",
        encoding="utf-8",
    )
    tampered = client.post(f"/evidence/{merged_body['merged_packet_trace_id']}/verify", headers=auth_headers)
    assert tampered.status_code == 200
    tampered_body = tampered.json()
    assert tampered_body["overall"] == "partial_mismatch"
    assert any(
        check["artifact"] == "merged_packet_hash_chain" and check["match"] is False
        for check in tampered_body["checks"]
    )


def test_fleet_packet_local_anchor_is_verified_and_tamper_detected(client, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path / "packet-store"))
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "local")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_LOCAL_DIR", str(tmp_path / "anchor-store"))
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()
    receipt = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": _fragment_ref_for(audit, leased),
        },
        headers=auth_headers,
    )
    assert receipt.status_code == 200

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/merge",
        headers=auth_headers,
    )
    assert merged.status_code == 200
    trace_id = merged.json()["merged_packet_trace_id"]

    packet = client.get(f"/evidence/{trace_id}", headers=auth_headers).json()
    anchor = packet["hashes"]["external_anchor"]
    assert anchor["status"] == "anchored"
    assert anchor["mode"] == "local"
    assert Path(anchor["anchor_uri"]).is_file()

    verified = client.post(f"/evidence/{trace_id}/verify", headers=auth_headers).json()
    assert verified["overall"] == "all_match"
    assert any(
        check["artifact"] == "merged_packet_external_anchor" and check["match"] is True
        for check in verified["checks"]
    )

    Path(anchor["anchor_uri"]).write_text("{}", encoding="utf-8")
    tampered = client.post(f"/evidence/{trace_id}/verify", headers=auth_headers).json()
    assert tampered["overall"] == "partial_mismatch"
    assert any(
        check["artifact"] == "merged_packet_external_anchor" and check["match"] is False
        for check in tampered["checks"]
    )


def test_fleet_packet_s3_anchor_rereads_object_during_verify(client, auth_headers, monkeypatch, tmp_path):
    fake_s3 = _FakeS3Client()
    fake_boto3 = types.SimpleNamespace(client=lambda service, **kwargs: fake_s3)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path / "packet-store"))
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "cas-harness-test-anchor")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX", "test-prefix")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION", "us-east-1")

    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()
    receipt = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": _fragment_ref_for(audit, leased),
        },
        headers=auth_headers,
    )
    assert receipt.status_code == 200

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/merge",
        headers=auth_headers,
    )
    assert merged.status_code == 200
    trace_id = merged.json()["merged_packet_trace_id"]

    packet = client.get(f"/evidence/{trace_id}", headers=auth_headers).json()
    anchor = packet["hashes"]["external_anchor"]
    assert anchor["status"] == "anchored"
    assert anchor["mode"] == "s3"
    assert anchor["bucket"] == "cas-harness-test-anchor"
    assert (anchor["bucket"], anchor["key"]) in fake_s3.objects

    verified = client.post(f"/evidence/{trace_id}/verify", headers=auth_headers).json()
    assert verified["overall"] == "all_match"
    assert fake_s3.get_calls == [(anchor["bucket"], anchor["key"])]
    external_anchor_check = next(
        check for check in verified["checks"] if check["artifact"] == "merged_packet_external_anchor"
    )
    assert external_anchor_check["match"] is True
    assert "re-read" in external_anchor_check["notes"]


def test_s3_anchor_verify_detects_remote_object_tampering(client, auth_headers, monkeypatch, tmp_path):
    fake_s3 = _FakeS3Client()
    fake_boto3 = types.SimpleNamespace(client=lambda service, **kwargs: fake_s3)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path / "packet-store"))
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "cas-harness-test-anchor")

    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()
    receipt = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": _fragment_ref_for(audit, leased),
        },
        headers=auth_headers,
    )
    assert receipt.status_code == 200
    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/merge",
        headers=auth_headers,
    ).json()
    trace_id = merged["merged_packet_trace_id"]
    packet = client.get(f"/evidence/{trace_id}", headers=auth_headers).json()
    anchor = packet["hashes"]["external_anchor"]

    fake_s3.objects[(anchor["bucket"], anchor["key"])] = b'{"tampered":true}'
    verified = client.post(f"/evidence/{trace_id}/verify", headers=auth_headers).json()

    assert verified["overall"] == "partial_mismatch"
    assert any(
        check["artifact"] == "merged_packet_external_anchor"
        and check["match"] is False
        and "hash does not match" in check["notes"]
        for check in verified["checks"]
    )


def test_s3_anchor_object_lock_is_verified(client, auth_headers, monkeypatch, tmp_path):
    fake_s3 = _FakeS3Client()
    fake_boto3 = types.SimpleNamespace(client=lambda service, **kwargs: fake_s3)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path / "packet-store"))
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "cas-harness-test-anchor")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "30")

    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()
    receipt = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": _fragment_ref_for(audit, leased),
        },
        headers=auth_headers,
    )
    assert receipt.status_code == 200
    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/merge",
        headers=auth_headers,
    ).json()
    trace_id = merged["merged_packet_trace_id"]
    packet = client.get(f"/evidence/{trace_id}", headers=auth_headers).json()
    anchor = packet["hashes"]["external_anchor"]

    assert anchor["status"] == "anchored"
    assert anchor["object_lock_mode"] == "GOVERNANCE"
    assert anchor["retention_days"] == 30
    assert anchor["object_lock_retain_until"]
    assert (anchor["bucket"], anchor["key"]) in fake_s3.object_locks
    expected_md5 = base64.b64encode(
        hashlib.md5(fake_s3.objects[(anchor["bucket"], anchor["key"])]).digest()
    ).decode("ascii")
    assert fake_s3.put_calls[0]["ContentMD5"] == expected_md5

    verified = client.post(f"/evidence/{trace_id}/verify", headers=auth_headers).json()

    assert verified["overall"] == "all_match"
    assert fake_s3.head_calls == [(anchor["bucket"], anchor["key"])]
    assert any(
        check["artifact"] == "merged_packet_external_anchor"
        and check["match"] is True
        and check["object_lock_verification"]["verified"] is True
        and check["object_lock_verification"]["expected"]["version_id"]
        == anchor["version_id"]
        and check["object_lock_verification"]["observed"]["get_version_id"]
        == anchor["version_id"]
        and check["object_lock_verification"]["observed"]["head_version_id"]
        == anchor["version_id"]
        for check in verified["checks"]
    )

    # Local packet fields are mutable storage, not the authority for the write
    # request.  S3 metadata remains original and both substitutions must fail.
    from api.services.cas_harness_evidence_anchor import verify_anchor

    for field, value in (
        ("retention_days", 1),
        ("retention_requested_at", "2026-01-01T00:00:00+00:00"),
    ):
        substituted = json.loads(json.dumps(packet))
        substituted["hashes"]["external_anchor"][field] = value
        check = verify_anchor(substituted)
        assert check["match"] is False
        assert "do not match authoritative S3" in check["notes"]
        assert check["object_lock_verification"]["verified"] is False
        assert check["object_lock_verification"]["issuer_attestation"] is None

    fragment = json.loads(json.dumps(packet))
    fragment["hashes"]["external_anchor"]["anchor_uri"] += "#ignored"
    fragment_check = verify_anchor(fragment)
    assert fragment_check["match"] is False
    assert "exact s3:// object-version receipt" in fragment_check["notes"]

    metadata = fake_s3.object_locks[(anchor["bucket"], anchor["key"])]["Metadata"]
    metadata["retention-requested-at"] = "2026-01-01T00:00:00"
    naive = verify_anchor(packet)
    assert naive["match"] is False
    assert "timezone-aware request boundary" in naive["notes"]


def test_s3_object_lock_anchor_refuses_write_without_stable_receipt_key(
    monkeypatch,
    tmp_path,
) -> None:
    from api.services.cas_harness_evidence_anchor import anchor_hash_log_entry

    fake_s3 = _FakeS3Client()
    monkeypatch.setitem(
        sys.modules,
        "boto3",
        types.SimpleNamespace(client=lambda service, **kwargs: fake_s3),
    )
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "cas-harness-test-anchor"
    )
    monkeypatch.setenv(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE"
    )
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "30")
    monkeypatch.setattr(settings, "object_lock_receipt_attestation_key", "")

    result = anchor_hash_log_entry(
        trace_id="trace-missing-receipt-key",
        hash_log_entry={
            "audit_id": "audit-missing-receipt-key",
            "packet_without_hashes_sha256": "a" * 64,
            "entry_sha256": "b" * 64,
            "previous_entry_sha256": None,
        },
        packet_path=tmp_path / "packet.json",
        hash_log_path=tmp_path / "hash-log.jsonl",
    )

    assert result["status"] == "failed"
    assert "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY" in result["reason"]
    assert fake_s3.put_calls == []


def test_s3_anchor_object_lock_metadata_missing_fails_verify(client, auth_headers, monkeypatch, tmp_path):
    fake_s3 = _FakeS3Client()
    fake_boto3 = types.SimpleNamespace(client=lambda service, **kwargs: fake_s3)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path / "packet-store"))
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "cas-harness-test-anchor")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "30")

    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()
    receipt = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": _fragment_ref_for(audit, leased),
        },
        headers=auth_headers,
    )
    assert receipt.status_code == 200
    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/merge",
        headers=auth_headers,
    ).json()
    trace_id = merged["merged_packet_trace_id"]
    anchor = client.get(f"/evidence/{trace_id}", headers=auth_headers).json()["hashes"]["external_anchor"]
    fake_s3.object_locks.pop((anchor["bucket"], anchor["key"]))

    verified = client.post(f"/evidence/{trace_id}/verify", headers=auth_headers).json()

    assert verified["overall"] == "partial_mismatch"
    assert any(
        check["artifact"] == "merged_packet_external_anchor"
        and check["match"] is False
        and check["object_lock_verification"]["verified"] is False
        and "Object Lock mode mismatch"
        in check["object_lock_verification"]["failure_reasons"]
        for check in verified["checks"]
    )


def test_s3_anchor_partial_object_lock_config_fails_loudly(client, auth_headers, monkeypatch, tmp_path):
    fake_s3 = _FakeS3Client()
    fake_boto3 = types.SimpleNamespace(client=lambda service, **kwargs: fake_s3)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path / "packet-store"))
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "cas-harness-test-anchor")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE")

    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()
    receipt = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": _fragment_ref_for(audit, leased),
        },
        headers=auth_headers,
    )
    assert receipt.status_code == 200
    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/merge",
        headers=auth_headers,
    ).json()
    trace_id = merged["merged_packet_trace_id"]
    anchor = client.get(f"/evidence/{trace_id}", headers=auth_headers).json()["hashes"]["external_anchor"]

    assert anchor["status"] == "failed"
    assert anchor["mode"] == "s3"
    assert "RETENTION_DAYS must be a positive integer" in anchor["reason"]


def test_fleet_verifier_requires_merged_packet(client, auth_headers):
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    prepared = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    assert prepared.status_code == 200

    verifier = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/verifier",
        headers=auth_headers,
    )

    assert verifier.status_code == 409
    assert "Merge fleet evidence before verifier review" in verifier.text


def test_fleet_verifier_accepts_only_with_stage19_stage20_fragment_payload(
    client,
    auth_headers,
    monkeypatch,
    tmp_path,
):
    fake_s3 = _FakeS3Client()
    fake_boto3 = types.SimpleNamespace(client=lambda service, **kwargs: fake_s3)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path / "packet-store"))
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "cas-harness-test-anchor")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "30")
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()
    verifier_fragment = _stage19_stage20_verifier_fragment()
    fragment_ref = _fragment_ref_for(
        audit,
        leased,
        evidence_packet_fragment_payload=verifier_fragment,
    )

    receipt = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": fragment_ref,
            "evidence_packet_fragment_payload": verifier_fragment,
        },
        headers=auth_headers,
    )
    assert receipt.status_code == 200

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/merge",
        headers=auth_headers,
    )
    assert merged.status_code == 200
    trace_id = merged.json()["merged_packet_trace_id"]

    verifier = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/verifier",
        headers=auth_headers,
    )
    assert verifier.status_code == 200
    verifier_body = verifier.json()
    assert verifier_body["verdict"] == "ACCEPT"
    assert verifier_body["confidence"] == 0.91
    assert verifier_body["proof_chip_gate"] == "passed"
    assert verifier_body["source"] == "stage19_verification_stack+stage20_generation_readiness"

    packet = client.get(f"/evidence/{trace_id}", headers=auth_headers)
    assert packet.status_code == 200
    packet_body = packet.json()
    assert packet_body["verification"]["accepted"] is True
    assert packet_body["generation_readiness"]["generation_readiness"] == "allow"
    assert packet_body["distributed_fleet"]["jobs"][0]["evidence_packet_fragment_payload_sha256"]


def test_fleet_receipt_rejects_payload_when_fragment_ref_omits_payload_hash(client, auth_headers):
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()
    verifier_fragment = _stage19_stage20_verifier_fragment()
    fragment_ref_without_payload_hash = _fragment_ref_for(audit, leased)

    receipt = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
            "evidence_packet_fragment_ref": fragment_ref_without_payload_hash,
            "evidence_packet_fragment_payload": verifier_fragment,
        },
        headers=auth_headers,
    )

    assert receipt.status_code == 409
    assert "fragment ref failed hash/assignment validation" in receipt.text


def test_duplicate_worker_registration_is_rejected(client, auth_headers):
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])

    duplicate = client.post(
        "/api/cas-harness/audit/distributed/fleet/worker/register",
        json=_worker_registration_payload(worker_assignment, audit["plan"]["model_id"]),
        headers=auth_headers,
    )

    assert duplicate.status_code == 409
    assert "already registered" in duplicate.text


def test_wrong_model_worker_cannot_lease_assigned_job(client, auth_headers):
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id="customer/wrong-open-weight-1b")

    prepared = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    assert prepared.status_code == 200
    assert prepared.json()["verifier_gate_status"] == "waiting_for_workers"

    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    )

    assert leased.status_code == 409
    assert "model_id does not match" in leased.text


def test_non_lease_fleet_state_responses_do_not_expose_lease_token(client, auth_headers):
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])

    prepared = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    ).json()
    assert all(job["lease_token"] is None for job in prepared["jobs"])

    fetched = client.get(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet",
        headers=auth_headers,
    ).json()
    assert all(job["lease_token"] is None for job in fetched["jobs"])

    runs = client.get(
        "/api/cas-harness/audit/distributed/fleet/runs",
        headers=auth_headers,
    ).json()
    assert all(job["lease_token"] is None for run in runs["runs"] for job in run["jobs"])


def test_job_receipt_requires_active_lease_and_packet_fragment(client, auth_headers):
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    prepared = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    ).json()
    job = prepared["jobs"][0]

    no_lease = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{job['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": "not-active",
            "produced_outputs": job["expected_outputs"],
            "evidence_packet_fragment_ref": f"packet-fragment://{job['job_id']}",
        },
        headers=auth_headers,
    )
    assert no_lease.status_code == 409
    assert "active lease" in no_lease.text

    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()
    missing_fragment = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "produced_outputs": leased["expected_outputs"],
        },
        headers=auth_headers,
    )
    assert missing_fragment.status_code == 422
    assert "evidence_packet_fragment_ref" in missing_fragment.text


def test_failed_job_receipt_can_return_no_outputs_if_error_is_present(client, auth_headers):
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    leased = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/lease",
        json={"worker_id": worker_assignment["worker_id"]},
        headers=auth_headers,
    ).json()

    failed = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/job/{leased['job_id']}/receipt",
        json={
            "worker_id": worker_assignment["worker_id"],
            "lease_token": leased["lease_token"],
            "job_status": "failed",
            "error_message": "GPU shard crashed before producing outputs",
        },
        headers=auth_headers,
    )

    assert failed.status_code == 200
    body = failed.json()
    assert body["verifier_gate_status"] == "blocked_failed_worker"
    assert body["readiness"]["status"] == "blocked"
    assert "cannot support ACCEPT" in body["readiness"]["headline"]
    assert body["failed_jobs"] == 1


def test_300b_fleet_merge_blocks_until_every_assigned_job_has_receipt(client, auth_headers):
    audit = _create_dispatched_audit(
        client,
        auth_headers,
        parameter_count_b=300,
        num_layers=3,
        minimum_worker_count=25,
    )
    assert audit["total_workers"] == 25
    _register_worker(client, auth_headers, audit["worker_evidence"][0], model_id=audit["plan"]["model_id"])

    prepared = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    assert prepared.status_code == 200
    body = prepared.json()
    assert body["verifier_gate_status"] == "waiting_for_workers"
    assert body["readiness"]["status"] == "waiting"
    assert "registered, compatible, fresh-heartbeat worker" in " ".join(body["readiness"]["blockers"])
    assert body["registered_workers"] == 1
    assert body["total_jobs"] == 25

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/merge",
        headers=auth_headers,
    )
    assert merged.status_code == 409
    assert "every assigned job returns a receipt" in merged.text


def test_stale_worker_blocks_verifier_gate(client, auth_headers):
    audit = _create_dispatched_audit(client, auth_headers, parameter_count_b=1, num_layers=1)
    worker_assignment = audit["worker_evidence"][0]
    _register_worker(client, auth_headers, worker_assignment, model_id=audit["plan"]["model_id"])
    client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/prepare",
        headers=auth_headers,
    )
    worker = list_workers()[0]
    worker.last_heartbeat_at = (datetime.now(UTC) - timedelta(seconds=5)).isoformat()

    stale_scan = client.post(
        "/api/cas-harness/audit/distributed/fleet/workers/stale-scan",
        json={"max_heartbeat_age_seconds": 1},
        headers=auth_headers,
    )
    assert stale_scan.status_code == 200

    run = client.get(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet",
        headers=auth_headers,
    ).json()
    assert run["verifier_gate_status"] == "waiting_for_workers"
    assert run["readiness"]["status"] == "waiting"
    assert "stale heartbeat" in " ".join(run["readiness"]["blockers"])
