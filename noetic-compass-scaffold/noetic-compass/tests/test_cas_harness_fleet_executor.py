from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from api.middleware.auth import create_token
from api.services.cas_harness_distributed_audits import reset_distributed_audits_for_tests
from api.services.cas_harness_fleet_executor import (
    build_evidence_fragment_ref,
    list_workers,
    reset_fleet_executor_for_tests,
)


def setup_function() -> None:
    reset_fleet_executor_for_tests()
    reset_distributed_audits_for_tests()


@pytest.fixture
def auth_headers(request) -> dict[str, str]:
    token = create_token(
        sub=f"test-user-{request.node.name}",
        api_key=f"test-key-{request.node.nodeid}",
    )
    return {"Authorization": f"Bearer {token}"}


def _scale_payload(parameter_count_b: int = 20, num_layers: int = 8, **overrides) -> dict:
    payload = {
        "model_id": f"customer/open-weight-{parameter_count_b}b",
        "weight_access": "open_weight",
        "parameter_count_b": parameter_count_b,
        "num_layers": num_layers,
        "precision": "int4" if parameter_count_b == 300 else "bf16",
        "available_gpu_memory_gb": 80,
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


def _fragment_ref_for(audit: dict, job: dict, *, produced_outputs: list[str] | None = None) -> str:
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
    )


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


def test_worker_registration_job_lease_receipt_and_merge_path(client, auth_headers):
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
    assert verifier_body["proof_chip_gate"] == "blocked"
    assert "no explicit proof-chip verifier decision" in " ".join(verifier_body["blockers"])
    assert "FLAG FOR HUMAN REVIEW" in " ".join(verifier_body["next_actions"])


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
