from __future__ import annotations

from api.services.cas_harness_distributed_audits import reset_distributed_audits_for_tests


def setup_function() -> None:
    reset_distributed_audits_for_tests()


def _scale_payload(parameter_count_b: int = 100, num_layers: int = 20) -> dict:
    return {
        "model_id": f"customer/open-weight-{parameter_count_b}b",
        "weight_access": "open_weight",
        "parameter_count_b": parameter_count_b,
        "num_layers": num_layers,
        "precision": "int4" if parameter_count_b == 300 else "bf16",
        "available_gpu_memory_gb": 80,
    }


def test_distributed_routes_registered(client):
    openapi = client.get("/openapi.json").json()

    assert "/api/cas-harness/audit/distributed/session" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}/dispatch" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}/merge" in openapi["paths"]
    assert "/api/cas-harness/audit/distributed/session/{audit_id}" in openapi["paths"]


def test_create_distributed_100b_audit_returns_worker_assignments(client):
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
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


def test_dispatch_marks_workers_assigned_without_claiming_verdict(client):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
    ).json()

    dispatched = client.post(
        f"/api/cas-harness/audit/distributed/session/{created['audit_id']}/dispatch",
    )

    assert dispatched.status_code == 200
    body = dispatched.json()
    assert body["status"] == "DISPATCHED"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert {worker["worker_status"] for worker in body["worker_evidence"]} == {"assigned"}


def test_merge_blocks_until_all_worker_receipts_exist(client):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
    ).json()

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{created['audit_id']}/merge",
    )

    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "MERGE_PENDING"
    assert body["merge_status"] == "partial"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert "Waiting for worker evidence" in body["merge_reason"]


def test_completed_worker_receipts_merge_but_do_not_fabricate_accept(client):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
    ).json()
    audit_id = created["audit_id"]
    expected_outputs = created["worker_evidence"][0]["expected_outputs"]

    for worker in created["worker_evidence"]:
        resp = client.post(
            f"/api/cas-harness/audit/distributed/session/{audit_id}/worker/{worker['worker_id']}/evidence",
            json={
                "produced_outputs": expected_outputs,
                "evidence_packet_ref": f"packet://{worker['worker_id']}",
            },
        )
        assert resp.status_code == 200

    merged = client.post(f"/api/cas-harness/audit/distributed/session/{audit_id}/merge")

    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "COMPLETE"
    assert body["merge_status"] == "complete"
    assert body["ready_workers"] == body["total_workers"]
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] == f"{audit_id}-distributed-merge"
    assert "Final ACCEPT/SUPPRESS still requires the verifier decision layer" in body["merge_reason"]


def test_missing_worker_output_routes_to_human_review(client):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
    ).json()
    audit_id = created["audit_id"]
    expected_outputs = created["worker_evidence"][0]["expected_outputs"]

    for index, worker in enumerate(created["worker_evidence"]):
        outputs = expected_outputs if index else expected_outputs[:-1]
        resp = client.post(
            f"/api/cas-harness/audit/distributed/session/{audit_id}/worker/{worker['worker_id']}/evidence",
            json={
                "produced_outputs": outputs,
                "evidence_packet_ref": f"packet://{worker['worker_id']}",
            },
        )
        assert resp.status_code == 200

    merged = client.post(f"/api/cas-harness/audit/distributed/session/{audit_id}/merge")

    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "COMPLETE"
    assert body["merge_status"] == "partial"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["missing_outputs"] == ["worker_evidence_manifest"]
    assert "cannot ACCEPT" in body["merge_reason"]


def test_failed_worker_routes_to_human_review(client):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(20, 8),
    ).json()
    audit_id = created["audit_id"]
    worker = created["worker_evidence"][0]

    resp = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit_id}/worker/{worker['worker_id']}/evidence",
        json={
            "produced_outputs": ["layer_activation_summary"],
            "worker_status": "failed",
            "error_message": "GPU worker lost model shard",
        },
    )
    assert resp.status_code == 200

    merged = client.post(f"/api/cas-harness/audit/distributed/session/{audit_id}/merge")

    assert merged.status_code == 200
    body = merged.json()
    assert body["status"] == "COMPLETE"
    assert body["merge_status"] == "failed"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["failed_workers"] == 1
    assert "failed worker evidence" in body["merge_reason"]


def test_300b_audit_requires_worker_fleet_receipts_before_completion(client):
    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(300, 160),
    )

    assert created.status_code == 200
    body = created.json()
    assert body["plan"]["parameter_count_b"] == 300
    assert body["plan"]["scale_tier"] == "enterprise_distributed_open_weight"
    assert body["total_workers"] >= 25
    assert body["verdict"] is None

    merged = client.post(
        f"/api/cas-harness/audit/distributed/session/{body['audit_id']}/merge",
    ).json()

    assert merged["status"] == "MERGE_PENDING"
    assert merged["verdict"] is None
    assert "Waiting for worker evidence" in merged["merge_reason"]


def test_distributed_endpoint_rejects_black_box_customer_models(client):
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            **_scale_payload(100, 20),
            "weight_access": "black_box",
        },
    )

    assert resp.status_code == 422
    assert "open_weight" in resp.text
