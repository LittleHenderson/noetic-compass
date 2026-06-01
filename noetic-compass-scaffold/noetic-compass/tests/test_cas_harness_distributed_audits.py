from __future__ import annotations

import pytest

from api.middleware.auth import create_token
from api.services.cas_harness_distributed_audits import reset_distributed_audits_for_tests


def setup_function() -> None:
    reset_distributed_audits_for_tests()


@pytest.fixture
def auth_headers(request) -> dict[str, str]:
    token = create_token(
        sub=f"test-user-{request.node.name}",
        api_key=f"test-key-{request.node.nodeid}",
    )
    return {"Authorization": f"Bearer {token}"}


def _scale_payload(parameter_count_b: int = 100, num_layers: int = 20) -> dict:
    return {
        "model_id": f"customer/open-weight-{parameter_count_b}b",
        "weight_access": "open_weight",
        "parameter_count_b": parameter_count_b,
        "num_layers": num_layers,
        "precision": "int4" if parameter_count_b == 300 else "bf16",
        "available_gpu_memory_gb": 80,
    }


def _provenance_payload(model_id: str, *, license_id: str = "apache-2.0") -> dict:
    """A well-formed model provenance/license/weight-hash manifest body.

    ``model_id`` must match the run request's model_id or the gate rejects it.
    The SHA-256 values are well-formed but declared-only (no bytes on disk at
    the API tier), so a good manifest lands at PROVENANCE_DECLARED_NOT_VERIFIED.
    """

    return {
        "model_id": model_id,
        "source_uri": f"https://huggingface.co/{model_id}",
        "license_id": license_id,
        "weight_files": [
            {"path": "model-00001-of-00002.safetensors", "sha256": "a" * 64},
            {"path": "model-00002-of-00002.safetensors", "sha256": "b" * 64},
        ],
        "revision": "main",
    }


def _frontier_payload(parameter_count_b: int = 405, num_layers: int = 120) -> dict:
    """A frontier-lane (300B-4T -> EXPERIMENTAL_NOT_VALIDATED) run request body."""

    return {
        **_scale_payload(parameter_count_b, num_layers),
        "accept_experimental_frontier": True,
    }


def test_distributed_routes_registered(client):
    openapi = client.get("/openapi.json").json()

    assert "/api/cas-harness/audit/distributed/session" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}/dispatch" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}/merge" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}" in openapi["paths"]


def test_distributed_session_requires_auth(client):
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
    )

    assert resp.status_code == 401


def test_create_distributed_100b_audit_returns_worker_assignments(client, auth_headers):
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "PLANNED"
    assert body["merge_status"] == "pending"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert body["plan"]["scale_tier"] == "enterprise_distributed_open_weight"
    assert body["plan"]["weight_access"] == "open_weight"
    assert body["total_workers"] == len(body["worker_evidence"])
    assert body["total_workers"] >= 8
    assert body["worker_evidence"][0]["worker_status"] == "queued"
    assert body["worker_evidence"][0]["layer_start"] == 0
    assert body["worker_evidence"][-1]["layer_end"] == 19


def test_dispatch_marks_workers_assigned_without_claiming_verdict(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
        headers=auth_headers,
    ).json()

    dispatched = client.post(
        f"/api/cas-harness/audit/distributed/session/{created['audit_id']}/dispatch",
        headers=auth_headers,
    )

    assert dispatched.status_code == 200
    body = dispatched.json()
    assert body["status"] == "DISPATCHED"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert {worker["worker_status"] for worker in body["worker_evidence"]} == {"assigned"}


def test_merge_blocks_until_all_worker_receipts_exist(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
        headers=auth_headers,
    ).json()
    client.post(
        f"/api/cas-harness/audit/distributed/session/{created['audit_id']}/dispatch",
        headers=auth_headers,
    )

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{created['audit_id']}/merge",
        headers=auth_headers,
    )

    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "MERGE_PENDING"
    assert body["merge_status"] == "partial"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert "Waiting for worker evidence" in body["merge_reason"]


def test_completed_worker_receipts_merge_but_do_not_fabricate_accept(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
        headers=auth_headers,
    ).json()
    audit_id = created["audit_id"]
    created = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/dispatch",
        headers=auth_headers,
    ).json()
    expected_outputs = created["worker_evidence"][0]["expected_outputs"]

    for worker in created["worker_evidence"]:
        resp = client.post(
            f"/api/cas-harness/audit/distributed/session/{audit_id}/worker/{worker['worker_id']}/evidence",
            json={
                "produced_outputs": expected_outputs,
                "evidence_packet_ref": f"packet://{worker['worker_id']}",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/merge",
        headers=auth_headers,
    )

    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "COMPLETE"
    assert body["merge_status"] == "complete"
    assert body["ready_workers"] == body["total_workers"]
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] == f"{audit_id}-distributed-merge"
    assert "Final ACCEPT/SUPPRESS still requires the verifier decision layer" in body["merge_reason"]


def test_missing_worker_output_routes_to_human_review(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
        headers=auth_headers,
    ).json()
    audit_id = created["audit_id"]
    created = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/dispatch",
        headers=auth_headers,
    ).json()
    expected_outputs = created["worker_evidence"][0]["expected_outputs"]

    for index, worker in enumerate(created["worker_evidence"]):
        outputs = expected_outputs if index else expected_outputs[:-1]
        resp = client.post(
            f"/api/cas-harness/audit/distributed/session/{audit_id}/worker/{worker['worker_id']}/evidence",
            json={
                "produced_outputs": outputs,
                "evidence_packet_ref": f"packet://{worker['worker_id']}",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/merge",
        headers=auth_headers,
    )

    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "COMPLETE"
    assert body["merge_status"] == "partial"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["missing_outputs"] == ["worker_evidence_manifest"]
    assert "cannot ACCEPT" in body["merge_reason"]


def test_failed_worker_routes_to_human_review(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
        headers=auth_headers,
    ).json()
    audit_id = created["audit_id"]
    created = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/dispatch",
        headers=auth_headers,
    ).json()
    worker = created["worker_evidence"][0]

    resp = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/worker/{worker['worker_id']}/evidence",
        json={
            "produced_outputs": ["layer_activation_summary"],
            "worker_status": "failed",
            "error_message": "GPU worker lost model shard",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/merge",
        headers=auth_headers,
    )

    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "COMPLETE"
    assert body["merge_status"] == "failed"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["failed_workers"] == 1
    assert "failed worker evidence" in body["merge_reason"]


def test_300b_audit_requires_worker_fleet_receipts_before_completion(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(300, 160),
        headers=auth_headers,
    )

    assert created.status_code == 200
    body = created.json()
    assert body["plan"]["parameter_count_b"] == 300
    assert body["plan"]["scale_tier"] == "enterprise_distributed_open_weight"
    assert body["total_workers"] >= 25
    assert body["verdict"] is None

    premature_merge = client.post(
        f"/api/cas-harness/audit/distributed/session/{body['audit_id']}/merge",
        headers=auth_headers,
    )

    assert premature_merge.status_code == 409
    assert "Dispatch Probe Worker assignments" in premature_merge.text

    client.post(
        f"/api/cas-harness/audit/distributed/session/{body['audit_id']}/dispatch",
        headers=auth_headers,
    )

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{body['audit_id']}/merge",
        headers=auth_headers,
    ).json()

    assert merged["status"] == "MERGE_PENDING"
    assert merged["verdict"] is None
    assert "Waiting for worker evidence" in merged["merge_reason"]


def test_300b_audit_can_request_larger_worker_fleet(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            **_scale_payload(300, 160),
            "minimum_worker_count": 300,
        },
        headers=auth_headers,
    )

    assert created.status_code == 200
    body = created.json()
    assert body["total_workers"] == 300
    assert body["plan"]["recommended_worker_count"] == 300
    assert body["worker_evidence"][0]["shard_id"].startswith("layer-")
    assert body["worker_evidence"][0]["layer_start"] == body["worker_evidence"][0]["layer_end"]


def test_worker_receipts_are_rejected_before_dispatch(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
        headers=auth_headers,
    ).json()
    worker = created["worker_evidence"][0]

    resp = client.post(
        f"/api/cas-harness/audit/distributed/session/{created['audit_id']}/worker/{worker['worker_id']}/evidence",
        json={
            "produced_outputs": worker["expected_outputs"],
            "evidence_packet_ref": f"packet://{worker['worker_id']}",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 409
    assert "Dispatch Probe Worker assignments" in resp.text


def test_completed_worker_receipt_requires_evidence_packet_ref(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
        headers=auth_headers,
    ).json()
    audit_id = created["audit_id"]
    created = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/dispatch",
        headers=auth_headers,
    ).json()
    worker = created["worker_evidence"][0]

    resp = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/worker/{worker['worker_id']}/evidence",
        json={"produced_outputs": worker["expected_outputs"]},
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "evidence_packet_ref" in resp.text


def test_distributed_endpoint_rejects_black_box_customer_models(client, auth_headers):
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            **_scale_payload(100, 20),
            "weight_access": "black_box",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "open_weight" in resp.text


# --- Frontier run-gate (5): model provenance / license / weight-hash manifest ---


def test_frontier_run_refused_without_provenance_manifest(client, auth_headers):
    # Accepting experimental risk is necessary but not sufficient: a real
    # frontier run also needs a provenance manifest. Without one, refuse 422.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_frontier_payload(405, 120),
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "provenance" in resp.text.lower()


def test_frontier_run_with_valid_provenance_is_declared_not_verified(client, auth_headers):
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"]["validation_status"] == "EXPERIMENTAL_NOT_VALIDATED"
    prov = body["provenance"]
    # Honest: a declared-only manifest never claims VERIFIED at the API tier.
    assert prov["status"] == "PROVENANCE_DECLARED_NOT_VERIFIED"
    assert prov["license_recognized"] is True
    assert prov["weight_file_count"] == 2
    assert prov["verified_file_count"] == 0
    assert prov["all_hashes_verified"] is False
    assert prov["manifest_content_digest"]


def test_frontier_run_rejects_provenance_with_mismatched_model_id(client, auth_headers):
    payload = _frontier_payload(405, 120)
    # Manifest is for a different model than the one being audited.
    payload["provenance"] = _provenance_payload("someone-else/other-405b")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "does not match the requested" in resp.text


def test_frontier_run_rejects_unrecognized_license(client, auth_headers):
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(
        payload["model_id"], license_id="proprietary-closed-weights"
    )

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "open-weight" in resp.text.lower()


def test_frontier_run_rejects_malformed_weight_hash(client, auth_headers):
    payload = _frontier_payload(405, 120)
    provenance = _provenance_payload(payload["model_id"])
    provenance["weight_files"][0]["sha256"] = "not-a-valid-sha256"
    payload["provenance"] = provenance

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "SHA-256" in resp.text


def test_below_frontier_run_does_not_require_provenance(client, auth_headers):
    # A 100B run is ENGINEERED_NOT_VALIDATED, not frontier -- provenance is
    # optional there and its absence must never block the run.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["provenance"] is None


def test_below_frontier_run_records_optional_provenance_summary(client, auth_headers):
    # If a below-frontier caller volunteers a manifest, we record the honest
    # summary without gating on it.
    payload = _scale_payload(100, 20)
    payload["provenance"] = _provenance_payload(payload["model_id"])

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    prov = resp.json()["provenance"]
    assert prov is not None
    assert prov["status"] == "PROVENANCE_DECLARED_NOT_VERIFIED"
    assert prov["license_recognized"] is True
