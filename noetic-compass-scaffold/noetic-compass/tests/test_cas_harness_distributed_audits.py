from __future__ import annotations

import pytest

from api.middleware.auth import create_token
from api.services.cas_harness_distributed_audits import reset_distributed_audits_for_tests
from api.services.cas_harness_tks_definition_lock import LOCKED_TKS_DEFINITION_SHA256


def setup_function() -> None:
    reset_distributed_audits_for_tests()


@pytest.fixture
def auth_headers(request) -> dict[str, str]:
    token = create_token(
        sub=f"test-user-{request.node.name}",
        api_key=f"test-key-{request.node.nodeid}",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def configured_retention_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Distributed-gate assertions use an explicit runtime Object Lock target."""

    monkeypatch.setenv(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE"
    )
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "31")


def _scale_payload(parameter_count_b: int = 100, num_layers: int = 20) -> dict:
    # Every distributed run -- frontier or not -- must acknowledge audit data capture
    # (universal run-gate 8), so the base body carries it. Tests that exercise a
    # *missing* data-capture ack pop ``accept_audit_data_capture`` back off.
    return {
        "model_id": f"customer/open-weight-{parameter_count_b}b",
        "weight_access": "open_weight",
        "parameter_count_b": parameter_count_b,
        "num_layers": num_layers,
        "precision": "int4" if parameter_count_b == 300 else "bf16",
        "available_gpu_memory_gb": 80,
        "accept_audit_data_capture": True,
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
    """A frontier-lane (300B-4T -> EXPERIMENTAL_NOT_VALIDATED) run request body.

    Bundles both frontier acknowledgement flags a real run needs: the gate-1 risk
    ack (``accept_experimental_frontier``) and the gate-4 cost ack
    (``accept_frontier_compute_cost``). A frontier run is refused without either, so
    a happy-path frontier body carries both. Tests that exercise a *missing* cost ack
    pop ``accept_frontier_compute_cost`` back off.
    """

    return {
        **_scale_payload(parameter_count_b, num_layers),
        "accept_experimental_frontier": True,
        "accept_frontier_compute_cost": True,
    }


def _architecture_payload(model_type: str = "llama") -> dict:
    """A model architecture declaration that resolves to a supported probe adapter.

    ``llama`` maps to the llama_like decoder family whose ``model.layers`` stack
    the probe worker can mechanically locate and whose ``.mlp`` submodule it hooks
    -- so a declared-only architecture lands at ARCHITECTURE_ADAPTER_AVAILABLE.
    """

    return {"model_type": model_type}


def _probe_payload(*, schema_version: str = "cas_probe_linear_v1") -> dict:
    """A CAS probe-readout specification the worker can structurally load.

    ``schema_version`` is the exact string compute_cas_axis_readout requires, the
    axes are non-empty, and feature_dimension is positive -- so a declared-only spec
    lands at PROBE_COMPATIBILITY_DECLARED (the real dimensional match is confirmed
    worker-side at readout time).
    """

    return {
        "schema_version": schema_version,
        "axes": ["F1", "F2", "F3"],
        "feature_dimension": 200,
        "probe_id": "cas-linear-probe-v1",
        "definition_sha256": LOCKED_TKS_DEFINITION_SHA256,
    }


def _compute_payload(*, accelerator_count: int = 64, accelerator_memory_gb: float = 80.0) -> dict:
    """A compute envelope that can physically hold the frontier plan's model.

    A 405B bf16 model needs ~956 GB of resident memory; 64 x 80 GB accelerators
    offer ``64 x 80 x 0.62 = 3174.4 GB`` usable, comfortably above the need -- so a
    declared-only envelope lands at COMPUTE_FEASIBILITY_DECLARED (the real
    resident-set fit is confirmed fleet-side). Overrides poke individual fields.
    """

    return {
        "accelerator_count": accelerator_count,
        "accelerator_memory_gb": accelerator_memory_gb,
        "accelerator_type": "H100-80GB",
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


# --- Run-gate (2): model-access modality (UNIVERSAL, not frontier-stricter) ---


@pytest.mark.parametrize("mode", ["hosted_api", "black_box", "output_only"])
def test_distributed_endpoint_rejects_non_mechanistic_access_modes(client, auth_headers, mode):
    # The distributed audit is a mechanistic probe (hook decoder layers -> pool
    # hidden states -> cas_axis_readout). A hosted/black-box/output-only target
    # exposes no hidden states, so it is refused for EVERY size, frontier or not.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            **_scale_payload(100, 20),
            "weight_access": mode,
        },
        headers=auth_headers,
    )

    assert resp.status_code == 422
    body = resp.text
    assert "open_weight" in body
    # The refusal points the caller at the behavioral fallback, not a dead end.
    assert "target/verify" in body


def test_distributed_open_weight_run_carries_declared_access_summary(client, auth_headers):
    # A below-frontier open-weight run still carries the honest access receipt:
    # DECLARED (enough to create a run), never VERIFIED at the API tier.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    access = resp.json()["access"]
    assert access is not None
    assert access["status"] == "MODEL_ACCESS_DECLARED"
    assert access["mechanistic_probe_supported"] is True
    # No weights are touched at the API tier, so loadability is never confirmed here.
    assert access["access_verified"] is False
    assert access["declared_mode"] == "open_weight"
    assert access["reasons"] == []


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
    # Gate 6: a frontier run also needs a probe-hookable architecture. A llama
    # declaration resolves to the llama_like adapter so the run can be created.
    payload["architecture"] = _architecture_payload("llama")
    # Gate 7: a frontier run also needs a structurally loadable CAS probe spec, or
    # the run's central CAS readout would come back missing. A good spec clears it.
    payload["probe"] = _probe_payload()
    # Gate 3: a frontier run also needs a compute envelope that can physically hold
    # the model. A 64 x 80 GB fleet clears the planner's own memory math.
    payload["compute"] = _compute_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"]["validation_status"] == "EXPERIMENTAL_NOT_VALIDATED"
    compute = body["compute"]
    # Honest: declared-only compute is DECLARED, never VERIFIED -- the real resident
    # set is sharded and confirmed fleet-side, not at the API tier.
    assert compute["status"] == "COMPUTE_FEASIBILITY_DECLARED"
    assert compute["memory_sufficient"] is True
    assert compute["fit_verified"] is False
    assert compute["effective_accelerator_count"] == 64
    assert compute["accelerators_required"] <= 64
    prov = body["provenance"]
    # Honest: a declared-only manifest never claims VERIFIED at the API tier.
    assert prov["status"] == "PROVENANCE_DECLARED_NOT_VERIFIED"
    assert prov["license_recognized"] is True
    assert prov["weight_file_count"] == 2
    assert prov["verified_file_count"] == 0
    assert prov["all_hashes_verified"] is False
    assert prov["manifest_content_digest"]
    arch = body["architecture"]
    # Honest: declared-only architecture is AVAILABLE, never VERIFIED -- the real
    # layout is confirmed worker-side at load time, not at the API tier.
    assert arch["status"] == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert arch["resolved_model_type"] == "llama"
    assert arch["adapter_family"] == "llama_like"
    assert arch["adapter_available"] is True
    probe = body["probe"]
    # Honest: declared-only probe is DECLARED, never VERIFIED -- the probe is
    # actually loaded and run worker-side, not at the API tier.
    assert probe["status"] == "PROBE_COMPATIBILITY_DECLARED"
    assert probe["schema_version"] == "cas_probe_linear_v1"
    assert probe["axis_count"] == 3
    assert probe["declared_feature_dimension"] == 200
    assert probe["definition_sha256"] == LOCKED_TKS_DEFINITION_SHA256
    assert probe["tks_definition_locked"] is True
    assert probe["probe_loadable"] is True
    assert probe["weights_hash_verified"] is False


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


def test_frontier_run_refused_without_architecture_declaration(client, auth_headers):
    # A valid provenance manifest clears gate 5 but a real frontier run also needs
    # a probe-hookable architecture (gate 6). With provenance valid and no
    # architecture declared, the 422 we assert is the architecture gate firing.
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "architecture" in resp.text.lower()


def test_frontier_run_rejects_unsupported_architecture(client, auth_headers):
    # mamba is a state-space architecture: the probe worker cannot locate a
    # transformer decoder stack at any of its four hardcoded attribute paths, so
    # it would raise rather than emit activations. Refuse the run honestly.
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("mamba")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "architecture" in resp.text.lower()


def test_frontier_run_supported_architecture_is_adapter_available(client, auth_headers):
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("qwen2")
    payload["probe"] = _probe_payload()
    payload["compute"] = _compute_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    arch = resp.json()["architecture"]
    assert arch["status"] == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert arch["resolved_model_type"] == "qwen2"
    assert arch["adapter_family"] == "llama_like"
    assert arch["adapter_available"] is True


def test_frontier_run_resolves_architecture_from_architectures_class(client, auth_headers):
    # A caller may pass only the HF architectures class (e.g. from config.json)
    # without an explicit model_type. The gate strips the ForCausalLM suffix and
    # resolves "LlamaForCausalLM" -> "llama" -> the llama_like adapter.
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = {"architectures": ["LlamaForCausalLM"]}
    payload["probe"] = _probe_payload()
    payload["compute"] = _compute_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    arch = resp.json()["architecture"]
    assert arch["status"] == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert arch["resolved_model_type"] == "llama"


def test_frontier_run_gpt_neox_architecture_is_empirically_validated(client, auth_headers):
    # gpt_neox is the reference family the readout was actually validated on, so
    # its adapter carries the stronger empirically_validated marker.
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("gpt_neox")
    payload["probe"] = _probe_payload()
    payload["compute"] = _compute_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    arch = resp.json()["architecture"]
    assert arch["status"] == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert arch["adapter_family"] == "gpt_neox"
    assert arch["adapter_validation"] == "empirically_validated"


def test_below_frontier_run_does_not_require_architecture(client, auth_headers):
    # A 100B run is ENGINEERED_NOT_VALIDATED, not frontier -- architecture is
    # optional there and its absence must never block the run.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["architecture"] is None


def test_below_frontier_run_records_optional_architecture_summary(client, auth_headers):
    # If a below-frontier caller volunteers an architecture, we record the honest
    # summary without gating on it.
    payload = _scale_payload(100, 20)
    payload["architecture"] = _architecture_payload("mistral")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    arch = resp.json()["architecture"]
    assert arch is not None
    assert arch["status"] == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert arch["resolved_model_type"] == "mistral"
    assert arch["adapter_family"] == "llama_like"


def test_below_frontier_run_records_unsupported_architecture_without_gating(client, auth_headers):
    # A volunteered but unsupported architecture below frontier is recorded as
    # UNSUPPORTED for traceability but does NOT block the run -- the gate only
    # refuses at frontier scale.
    payload = _scale_payload(100, 20)
    payload["architecture"] = _architecture_payload("mamba")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    arch = resp.json()["architecture"]
    assert arch is not None
    assert arch["status"] == "ARCHITECTURE_ADAPTER_UNSUPPORTED"
    assert arch["adapter_available"] is False


# --- Frontier run-gate (7): CAS probe-readout compatibility ---


def test_frontier_run_refused_without_probe_specification(client, auth_headers):
    # Provenance (gate 5) and a hookable architecture (gate 6) are cleared, but a
    # real frontier run also needs a loadable CAS probe (gate 7). The CAS axis
    # readout is the run's central deliverable; without a probe it would silently
    # come back missing, so refuse 422. With both prior gates satisfied, the 422
    # we assert is precisely the probe gate firing.
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("llama")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "probe" in resp.text.lower()


def test_frontier_run_rejects_incompatible_probe_schema(client, auth_headers):
    # The worker's compute_cas_axis_readout rejects any schema_version other than
    # 'cas_probe_linear_v1' with a RuntimeError, so a wrong-schema probe could
    # never produce the readout. Refuse the run honestly.
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("llama")
    payload["probe"] = _probe_payload(schema_version="cas_probe_linear_v2")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "probe" in resp.text.lower()
    assert "cas_probe_linear_v1" in resp.text


def test_frontier_run_rejects_probe_without_tks_definition_hash(client, auth_headers):
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("llama")
    payload["probe"] = _probe_payload()
    payload["probe"].pop("definition_sha256")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "definition_sha256" in resp.text
    assert LOCKED_TKS_DEFINITION_SHA256 in resp.text


def test_frontier_run_rejects_probe_with_wrong_tks_definition_hash(client, auth_headers):
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("llama")
    payload["probe"] = _probe_payload()
    payload["probe"]["definition_sha256"] = "0" * 64

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "definition_sha256" in resp.text
    assert LOCKED_TKS_DEFINITION_SHA256 in resp.text


def test_frontier_run_rejects_probe_dimension_mismatch(client, auth_headers):
    # If the caller declares the run's pooled-feature dimension and it disagrees
    # with the probe's per-axis vector length, the worker would raise
    # "incompatible hidden size" and abort the shard. Refuse now instead.
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("llama")
    payload["probe"] = {
        "schema_version": "cas_probe_linear_v1",
        "axes": ["F1", "F2"],
        "feature_dimension": 200,
        "definition_sha256": LOCKED_TKS_DEFINITION_SHA256,
        "expected_pooled_features": 384,
    }

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "incompatible hidden size" in resp.text


def test_frontier_run_with_loadable_probe_is_declared(client, auth_headers):
    payload = _frontier_payload(405, 120)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("llama")
    payload["probe"] = _probe_payload()
    payload["compute"] = _compute_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    probe = resp.json()["probe"]
    assert probe["status"] == "PROBE_COMPATIBILITY_DECLARED"
    assert probe["schema_version"] == "cas_probe_linear_v1"
    assert probe["axis_count"] == 3
    assert probe["definition_sha256"] == LOCKED_TKS_DEFINITION_SHA256
    assert probe["tks_definition_locked"] is True
    assert probe["probe_loadable"] is True
    # No declared pooled dimension -> the final match is confirmed worker-side.
    assert probe["dimension_consistent"] is None


def test_below_frontier_run_does_not_require_probe(client, auth_headers):
    # A 100B run is ENGINEERED_NOT_VALIDATED, not frontier -- a probe spec is
    # optional there and its absence must never block the run.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["probe"] is None


def test_below_frontier_run_records_optional_probe_summary(client, auth_headers):
    # If a below-frontier caller volunteers a probe, we record the honest summary
    # without gating on it.
    payload = _scale_payload(100, 20)
    payload["probe"] = _probe_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    probe = resp.json()["probe"]
    assert probe is not None
    assert probe["status"] == "PROBE_COMPATIBILITY_DECLARED"
    assert probe["probe_loadable"] is True


def test_below_frontier_run_records_unsupported_probe_without_gating(client, auth_headers):
    # A volunteered but unloadable probe below frontier is recorded as UNSUPPORTED
    # for traceability but does NOT block the run -- the gate only refuses at
    # frontier scale.
    payload = _scale_payload(100, 20)
    payload["probe"] = _probe_payload(schema_version="cas_probe_linear_v2")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    probe = resp.json()["probe"]
    assert probe is not None
    assert probe["status"] == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert probe["probe_loadable"] is False


# --- Frontier run-gate (3): compute feasibility ---


def _frontier_gated_payload(parameter_count_b: int = 405, num_layers: int = 120) -> dict:
    """A frontier payload with gates 5/6/7 already satisfied, ready for gate 3.

    Lets the compute-feasibility tests vary only the compute envelope, so the 422
    (or 200) they assert is unambiguously the gate-3 decision and not an earlier gate.
    """

    payload = _frontier_payload(parameter_count_b, num_layers)
    payload["provenance"] = _provenance_payload(payload["model_id"])
    payload["architecture"] = _architecture_payload("llama")
    payload["probe"] = _probe_payload()
    return payload


def test_frontier_run_refused_without_compute_envelope(client, auth_headers):
    # Provenance (5), architecture (6), and probe (7) are cleared, but a real
    # frontier run also needs a compute envelope that can physically hold the model.
    # With the three prior gates satisfied, the 422 we assert is the compute gate.
    payload = _frontier_gated_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "compute envelope" in resp.text.lower()


def test_frontier_run_rejects_insufficient_compute(client, auth_headers):
    # A 405B bf16 model needs ~956 GB resident; 4 x 80 GB offers only 198.4 GB
    # usable. The gate refuses and names the count the caller actually needs.
    payload = _frontier_gated_payload()
    payload["compute"] = _compute_payload(accelerator_count=4)

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "insufficient compute" in resp.text.lower()
    assert "Declare at least 20 accelerators" in resp.text


def test_frontier_run_rejects_per_accelerator_too_small_for_fanout_cap(client, auth_headers):
    # 2 GB cards can never hold this model no matter how many are declared: the
    # model needs more accelerators than the planner's worker fan-out cap, so the
    # planner would silently clamp and under-resource every shard. Distinct refusal.
    payload = _frontier_gated_payload()
    payload["compute"] = _compute_payload(accelerator_count=100_000, accelerator_memory_gb=2.0)

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "fan-out cap" in resp.text
    assert "Declare larger accelerators" in resp.text


def test_frontier_run_with_sufficient_compute_is_declared(client, auth_headers):
    payload = _frontier_gated_payload()
    payload["compute"] = _compute_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    compute = resp.json()["compute"]
    assert compute["status"] == "COMPUTE_FEASIBILITY_DECLARED"
    assert compute["memory_sufficient"] is True
    assert compute["effective_accelerator_count"] == 64
    assert compute["needed_runtime_gb"] == pytest.approx(955.8)
    assert compute["accelerators_required"] == 20
    # Honest: declared, never VERIFIED -- the resident set is confirmed fleet-side.
    assert compute["fit_verified"] is False


def test_below_frontier_run_does_not_require_compute(client, auth_headers):
    # A 100B run is ENGINEERED_NOT_VALIDATED, not frontier -- a compute envelope is
    # optional there and its absence must never block the run.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["compute"] is None


def test_below_frontier_run_records_optional_compute_summary(client, auth_headers):
    # If a below-frontier caller volunteers a sufficient envelope, we record the
    # honest summary without gating on it.
    payload = _scale_payload(100, 20)
    payload["compute"] = _compute_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    compute = resp.json()["compute"]
    assert compute is not None
    assert compute["status"] == "COMPUTE_FEASIBILITY_DECLARED"
    assert compute["memory_sufficient"] is True


def test_below_frontier_run_records_insufficient_compute_without_gating(client, auth_headers):
    # A volunteered but too-small envelope below frontier is recorded as
    # INSUFFICIENT for traceability but does NOT block the run -- the gate only
    # refuses at frontier scale.
    payload = _scale_payload(100, 20)
    payload["compute"] = _compute_payload(accelerator_count=1, accelerator_memory_gb=8.0)

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    compute = resp.json()["compute"]
    assert compute is not None
    assert compute["status"] == "COMPUTE_FEASIBILITY_INSUFFICIENT"
    assert compute["memory_sufficient"] is False


# --- Frontier run-gate (4): cost acknowledgment ---


def _frontier_costed_payload(parameter_count_b: int = 405, num_layers: int = 120) -> dict:
    """A frontier payload with gates 5/6/7/3 all cleared, ready for gate 4.

    Lets the cost-acknowledgment tests vary only the cost ack, so the 422 (or 200)
    they assert is unambiguously the gate-4 decision and not an earlier gate. The
    cost ack itself rides in from ``_frontier_payload``; tests that want it absent
    pop ``accept_frontier_compute_cost``.
    """

    payload = _frontier_gated_payload(parameter_count_b, num_layers)
    payload["compute"] = _compute_payload()
    return payload


def test_frontier_run_refused_without_cost_acknowledgment(client, auth_headers):
    # Provenance (5), architecture (6), probe (7), and compute (3) are all cleared,
    # but a real frontier run also needs the caller to acknowledge its caller-owned,
    # unquoted compute cost. With the four prior gates satisfied and the cost ack
    # removed, the 422 we assert is unambiguously the cost gate firing.
    payload = _frontier_costed_payload()
    payload.pop("accept_frontier_compute_cost")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    text = resp.text.lower()
    assert "cost not acknowledged" in text
    assert "accept_frontier_compute_cost" in resp.text
    # The refusal surfaces the real committed magnitude, never an invented price.
    assert "$" not in resp.text
    assert "per hour" not in text


def test_frontier_run_with_cost_acknowledgment_is_acknowledged(client, auth_headers):
    # The four prior gates are cleared and the cost ack rides in from
    # _frontier_payload, so the run is created and carries an honest cost receipt.
    payload = _frontier_costed_payload()

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    cost = resp.json()["cost"]
    assert cost is not None
    assert cost["status"] == "COST_ACKNOWLEDGED"
    assert cost["acknowledged"] is True
    # Honest: acknowledged is never METERED at the API tier -- real accelerator-hours
    # are metered fleet-side, where the compute actually runs.
    assert cost["cost_metered"] is False
    # The receipt surfaces real planner / gate-(3) magnitudes, none invented.
    assert cost["recommended_worker_count"] > 0
    assert cost["estimated_total_runtime_gb"] > 0
    assert cost["declared_accelerator_count"] == 64
    assert cost["declared_accelerator_memory_gb"] == 80.0
    assert cost["effective_accelerator_count"] == 64


def test_below_frontier_run_does_not_require_cost_acknowledgment(client, auth_headers):
    # A 100B run is ENGINEERED_NOT_VALIDATED, not frontier -- the committed fleet is
    # modest, so a cost ack is optional there and its absence must never block the run.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["cost"] is None


def test_below_frontier_run_records_optional_cost_acknowledgment(client, auth_headers):
    # If a below-frontier caller volunteers a cost ack, we record the honest receipt
    # for traceability without ever having required it.
    payload = _scale_payload(100, 20)
    payload["accept_frontier_compute_cost"] = True

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    cost = resp.json()["cost"]
    assert cost is not None
    assert cost["status"] == "COST_ACKNOWLEDGED"
    assert cost["acknowledged"] is True
    assert cost["cost_metered"] is False
    # Below frontier with no volunteered envelope, the fleet fields are honestly null
    # while the plan magnitudes stay real.
    assert cost["recommended_worker_count"] > 0
    assert cost["declared_accelerator_count"] is None


# --- Distributed run-gate (8): data-capture acknowledgment (UNIVERSAL) ---


def test_below_frontier_run_refused_without_data_capture_acknowledgment(client, auth_headers):
    # The universal-enforcement proof: gate (8) is NOT frontier-only. A 100B run is
    # ENGINEERED_NOT_VALIDATED -- below the frontier, so gates (3)-(7) never fire -- yet
    # it still harvests the model's real signal (I/O + pooled activations + readout +
    # verdict) exactly as a 1T run does. So the data-capture ack
    # is required here too; with it popped, the only remaining run gate is gate (8), so
    # the 422 we assert is unambiguously the data-capture gate firing on a small run.
    payload = _scale_payload(100, 20)
    payload.pop("accept_audit_data_capture")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    text = resp.text.lower()
    assert "data capture not acknowledged" in text
    assert "accept_audit_data_capture" in resp.text
    # The refusal names what is captured and the configured retention boundary.
    assert "activations" in text
    assert "object lock governance" in text
    assert "31 days" in text


def test_below_frontier_run_with_data_capture_ack_surfaces_real_scope(client, auth_headers):
    # With the data-capture ack present (it rides in from _scale_payload), the below-
    # frontier run is created and carries an honest capture receipt that surfaces the
    # REAL classes the audit harvests -- never an invented capture scope.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_scale_payload(100, 20),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data_capture = resp.json()["data_capture"]
    assert data_capture is not None
    assert data_capture["status"] == "DATA_CAPTURE_ACKNOWLEDGED"
    assert data_capture["acknowledged"] is True
    # Honest: acknowledged is never WORM_COMMITTED at the API tier; only an actual
    # re-read-verified fleet receipt can produce that status.
    assert data_capture["capture_committed"] is False
    # Every captured class is real signal the audit already produces.
    assert data_capture["captured_signal_classes"] == [
        "model_input_output",
        "pooled_hidden_state_activations",
        "cas_axis_readout",
        "audit_verdict",
    ]
    assert data_capture["retention_model"] == "s3_object_lock_governance_time_bounded"
    disclosure = data_capture["retention_disclosure"]
    assert disclosure["mode"] == "GOVERNANCE"
    assert disclosure["retention_days"] == 31
    assert disclosure["permanent_or_indefinite"] is False
    assert disclosure["privileged_operator_override_possible"] is True
    assert disclosure["tamper_evident_on_reverify"] is False
    assert disclosure["commit_status_requires_verified_receipt"] is True
    assert disclosure["receipt_verified"] is False
    assert data_capture["reuse_purpose"] == "cas_native_training_corpus"
    assert data_capture["reasons"] == []


def test_frontier_run_refused_without_data_capture_acknowledgment(client, auth_headers):
    # Gate (8) is universal, so it applies at the frontier exactly as below it. With
    # gates (2)/(5)/(6)/(7)/(3)/(4) all cleared and only the data-capture ack removed, the
    # 422 we assert is unambiguously gate (8) -- the last gate -- firing.
    payload = _frontier_costed_payload()
    payload.pop("accept_audit_data_capture")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "data capture not acknowledged" in resp.text.lower()
    assert "accept_audit_data_capture" in resp.text


def test_data_capture_gate_fires_last_after_the_cost_gate(client, auth_headers):
    # Gate-ordering proof: data capture (8) is the LAST gate, firing after cost (4). With
    # BOTH the cost ack and the data ack removed from an otherwise complete frontier run,
    # the gate that fires is cost (4), not data capture (8) -- so the refusal names cost
    # and stays silent about data capture, pinning gate (8) as the very last to run.
    payload = _frontier_costed_payload()
    payload.pop("accept_frontier_compute_cost")
    payload.pop("accept_audit_data_capture")

    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    text = resp.text.lower()
    assert "cost not acknowledged" in text
    assert "data capture not acknowledged" not in text


def test_frontier_run_with_all_gates_surfaces_data_capture_receipt(client, auth_headers):
    # A fully-gated frontier run (gates 2/5/6/7/3/4 cleared, data ack present) is created
    # and carries the same honest capture receipt -- the harvest is identical at the
    # frontier, never WORM_COMMITTED at the API tier where no model has executed yet.
    resp = client.post(
        "/api/cas-harness/audit/distributed/session",
        json=_frontier_costed_payload(),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data_capture = resp.json()["data_capture"]
    assert data_capture is not None
    assert data_capture["status"] == "DATA_CAPTURE_ACKNOWLEDGED"
    assert data_capture["acknowledged"] is True
    assert data_capture["capture_committed"] is False
    assert "pooled_hidden_state_activations" in data_capture["captured_signal_classes"]
    assert "cas_axis_readout" in data_capture["captured_signal_classes"]
