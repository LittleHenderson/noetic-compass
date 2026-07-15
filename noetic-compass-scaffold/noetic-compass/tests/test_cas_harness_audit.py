from __future__ import annotations

from typing import get_args

import pytest

from api.config import settings
from api.routes import cas_harness_audit as audit_routes
from api.routes.cas_harness_audit import Verdict
from api.services.cas_harness_audit_sessions import reset_audit_sessions_for_tests
from api.services.cas_harness_harvest import iter_harvest_records
from api.services.cas_harness_merged_evidence_packets import (
    reset_merged_fleet_evidence_packets_for_tests,
)
from api.services.cas_harness_tks_definition_lock import LOCKED_TKS_DEFINITION_SHA256
from tests.object_lock_test_support import issue_test_object_lock_receipt


_TEST_WORM_RETAIN_UNTIL = "2099-06-28T00:00:00+00:00"
_TEST_WORM_REQUESTED_AT = "2026-01-01T00:00:00+00:00"


def setup_function() -> None:
    reset_audit_sessions_for_tests()


@pytest.fixture(autouse=True)
def _isolated_evidence_store(tmp_path, monkeypatch):
    """Pin the Evidence Packet store to an empty per-test dir.

    Without this, the route reads a developer machine's default temp store,
    so a previously run anchor (e.g. ``scripts.anchor_stage9_40e_packet``)
    would leak an anchored Stage-9 copy into these tests and flip packet_proof.
    """

    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("CAS_HARNESS_HARVEST_STORE_DIR", str(tmp_path / "harvest"))
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", raising=False)
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", raising=False)
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", raising=False)
    reset_merged_fleet_evidence_packets_for_tests()
    yield
    reset_merged_fleet_evidence_packets_for_tests()


def _valid_payload() -> dict:
    return {
        "model_id": "openai:gpt-4.1-mini",
        "audit_mode": "BALANCED",
        "prompt": "Assess whether this answer should be accepted or suppressed.",
        "selected_modules": ["cognitive_bias", "provenance_trace"],
        "license_key": "placeholder-license",
    }


class _PacketStub:
    def __init__(self, packet: dict):
        self._packet = packet

    def model_dump(self, *, mode: str = "json") -> dict:
        return self._packet


def _complete_stage21_packet(*, action: str = "allow", accepted: bool = True) -> dict:
    return {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": f"stage21-{action}-001",
        "model": {
            "model_key": "EleutherAI/pythia-160m",
            "name": "EleutherAI/pythia-160m",
        },
        "provenance": {
            "source_stage": "Stage 21A",
            "source_reports": [
                "stage19_verification_stack_report.json",
                "stage20_generation_readiness_report.json",
            ],
        },
        "readout": {"axis": "drive", "label": "F1", "confidence": 0.86},
        "ablation": {"status": "present", "effect": "targeted_drop"},
        "matched_controls": {"status": "present", "control": "random_same_rank"},
        "output": {"text": "Observed model output"},
        "verification": {
            "accepted": accepted,
            "mode": "BALANCED",
            "confidence_tier": "high",
            "mode_profile": {
                "accepted_accuracy": 0.9816,
                "coverage": 0.7173,
            },
            "suppression_reasons": [] if accepted else ["verification_stack_rejected"],
        },
        "generation_readiness": {
            "generation_readiness": action,
            "risk_score": 0.9 if action == "suppress" else 0.11,
            "policy_version": "stage20_v1",
            "reasons": [],
        },
    }


def _attach_worm_anchor(packet: dict) -> dict:
    key = f"cas-harness/evidence-anchors/{packet['trace_id']}/anchor.json"
    packet.setdefault("hashes", {})["external_anchor"] = {
        "status": "anchored",
        "mode": "s3",
        "anchor_uri": (
            "s3://cas-harness-runpod-92754088/cas-harness/evidence-anchors/"
            f"{packet['trace_id']}/anchor.json?versionId=version-test"
        ),
        "bucket": "cas-harness-runpod-92754088",
        "key": key,
        "version_id": "version-test",
        "manifest_sha256": "a" * 64,
        "object_lock_mode": "GOVERNANCE",
        "retention_requested_at": _TEST_WORM_REQUESTED_AT,
        "object_lock_retain_until": _TEST_WORM_RETAIN_UNTIL,
        "retention_days": 30,
    }
    return packet


def _worm_verify_hashes(trace_id: str) -> dict:
    key = f"cas-harness/evidence-anchors/{trace_id}/anchor.json"
    verification = issue_test_object_lock_receipt(
        expected={
            "bucket": "cas-harness-runpod-92754088",
            "key": key,
            "version_id": "version-test",
            "content_sha256": "a" * 64,
            "mode": "GOVERNANCE",
            "retention_days": 30,
            "requested_at": _TEST_WORM_REQUESTED_AT,
            "retain_until": _TEST_WORM_RETAIN_UNTIL,
        },
        observed={
            "bucket": "cas-harness-runpod-92754088",
            "key": key,
            "get_version_id": "version-test",
            "head_version_id": "version-test",
            "content_sha256": "a" * 64,
            "mode": "GOVERNANCE",
            "retain_until": _TEST_WORM_RETAIN_UNTIL,
            "reread_verified": True,
        },
    )
    return {
        "trace_id": trace_id,
        "overall": "all_match",
        "checks": [
            {
                "artifact": "merged_packet_external_anchor",
                "expected": "a" * 64,
                "actual": "a" * 64,
                "match": True,
                "notes": (
                    "display prose is not the WORM verification predicate"
                ),
                "object_lock_verification": verification.to_dict(),
            }
        ],
    }


def test_audit_session_route_registered(client):
    openapi = client.get("/openapi.json").json()

    assert "/api/cas-harness/audit/target/verify" in openapi["paths"]
    assert "/api/cas-harness/audit/scale-plan" in openapi["paths"]
    assert "/api/cas-harness/audit/session" in openapi["paths"]
    assert "/api/cas-harness/audit/session/{audit_id}/status" in openapi["paths"]
    assert "/api/cas-harness/audit/session/{audit_id}/run" in openapi["paths"]
    assert "/api/cas-harness/audit/sessions" in openapi["paths"]


def test_verify_reference_model_target_success_without_secret(client, auth_headers):
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={"target": {"kind": "demo_reference"}},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["connection_id"].startswith("cas-target-")
    assert body["connection_state"] == "CONNECTED"
    assert body["model_status"] == "CONNECTED"
    assert body["can_run_audit"] is True
    assert body["target"] == {
        "kind": "demo_reference",
        "provider": "cas_harness_reference",
        "model_id": "EleutherAI/gpt-neox-20b",
        "endpoint_url": None,
        "credential_mode": "none",
        "timeout_ms": 10000,
    }
    assert body["provenance_chip"]["id"] == "model_proof"
    assert body["provenance_chip"]["status"] == "present"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] is None
    assert (
        body["reference_evidence_packet_trace_id"]
        == "stage9-40e-original-baseline-readout-20260527"
    )
    assert body["atlas_deep_link"] is None
    assert "No external model call" in body["detail"]
    assert "Stage 9 40E scoped validation packet" in body["detail"]
    assert "not a per-customer production" in body["detail"]


def test_verify_hosted_open_weight_target_requires_exact_real_weight_authority(
    client, auth_headers, monkeypatch
):
    async def ready():
        return {
            "configured": True,
            "required": True,
            "status": "ok",
            "authority": "verified",
            "real_weights": True,
            "model_id": "EleutherAI/pythia-160m",
            "worker_version": "worker-test",
        }

    monkeypatch.setattr(audit_routes, "check_live_worker_readiness", ready)
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={
            "target": {
                "kind": "hosted_open_weight",
                "model_id": "EleutherAI/pythia-160m",
            }
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["target"] == {
        "kind": "hosted_open_weight",
        "provider": "cas_harness_live_worker",
        "model_id": "EleutherAI/pythia-160m",
        "endpoint_url": None,
        "credential_mode": "none",
        "timeout_ms": 10000,
    }
    assert body["connection_state"] == "CONNECTED"
    assert body["can_run_audit"] is True
    assert body["provenance_chip"]["status"] == "verified"
    assert body["reference_evidence_packet_trace_id"] is None
    assert "No inference" in body["detail"]


def test_verify_hosted_open_weight_target_fails_closed_when_worker_is_not_real(
    client, auth_headers, monkeypatch
):
    async def unavailable():
        return {
            "configured": True,
            "required": True,
            "status": "error",
            "reason": "realmode_contract_failed",
            "real_weights": False,
        }

    monkeypatch.setattr(audit_routes, "check_live_worker_readiness", unavailable)
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={"target": {"kind": "hosted_open_weight"}},
        headers=auth_headers,
    )

    assert resp.status_code == 503
    assert resp.json()["detail"] == {
        "code": "hosted_open_weight_unavailable",
        "status": "OPEN",
        "reason": "realmode_contract_failed",
    }


@pytest.mark.parametrize(
    "extra, detail",
    (
        ({"api_key": "should-not-leave-browser"}, "must not include credentials"),
        (
            {"model_id": "EleutherAI/gpt-neox-20b"},
            "only supports EleutherAI/pythia-160m",
        ),
        ({"allow_unauthenticated": True}, "server-held service authentication"),
    ),
)
def test_verify_hosted_open_weight_target_rejects_unsafe_overrides(
    client, auth_headers, extra, detail
):
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={"target": {"kind": "hosted_open_weight", **extra}},
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert detail in resp.text


def test_scale_plan_returns_open_weight_enterprise_worker_plan(client):
    resp = client.post(
        "/api/cas-harness/audit/scale-plan",
        json={
            "model_id": "customer/open-100b",
            "weight_access": "open_weight",
            "parameter_count_b": 100,
            "num_layers": 120,
            "precision": "bf16",
            "available_gpu_memory_gb": 80,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["model_id"] == "customer/open-100b"
    assert body["weight_access"] == "open_weight"
    assert body["scale_tier"] == "enterprise_distributed_open_weight"
    assert body["recommended_worker_count"] >= 9
    assert body["worker_assignments"][0]["layer_start"] == 0
    assert body["worker_assignments"][-1]["layer_end"] == 119
    assert "CAS Orchestrator + distributed Probe Workers" in body["orchestration_pattern"]
    assert any("Evidence Packet" in item for item in body["expected_capability"])
    assert any("does not support black-box" in item for item in body["limitations"])


@pytest.mark.parametrize("mode", ["hosted_api", "black_box", "output_only"])
def test_scale_plan_rejects_non_mechanistic_access_modes(client, mode):
    # Run-gate (2) is universal: a hosted/black-box/output-only target exposes no
    # hidden states, so the mechanistic probe cannot reach it at ANY size. The
    # refusal names the open_weight remedy and points at the behavioral fallback.
    resp = client.post(
        "/api/cas-harness/audit/scale-plan",
        json={
            "model_id": "closed-api-only",
            "weight_access": mode,
            "parameter_count_b": 20,
        },
    )

    assert resp.status_code == 422
    assert "open_weight" in resp.text
    assert "target/verify" in resp.text


def test_scale_plan_exposes_validation_status_for_validated_lane(client):
    resp = client.post(
        "/api/cas-harness/audit/scale-plan",
        json={"model_id": "open-20b", "parameter_count_b": 20, "num_layers": 40},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["validation_status"] == "EMPIRICALLY_VALIDATED"
    assert "empirically validated" in body["validation_notice"].lower()


def test_scale_plan_refuses_frontier_model_without_experimental_ack(client):
    # 300B-4T is the experimental frontier lane; without the acknowledgement the
    # public API must refuse the request (422) instead of quietly planning it.
    resp = client.post(
        "/api/cas-harness/audit/scale-plan",
        json={"model_id": "frontier/open-405b", "parameter_count_b": 405},
    )

    assert resp.status_code == 422
    assert "accept_experimental_frontier" in resp.text


def test_scale_plan_allows_frontier_model_with_experimental_ack(client):
    resp = client.post(
        "/api/cas-harness/audit/scale-plan",
        json={
            "model_id": "frontier/open-405b",
            "parameter_count_b": 405,
            "accept_experimental_frontier": True,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["scale_tier"] == "frontier_experimental_open_weight"
    assert body["validation_status"] == "EXPERIMENTAL_NOT_VALIDATED"
    assert "customer risk" in body["validation_notice"].lower()
    assert any("EXPERIMENTAL_NOT_VALIDATED" in item for item in body["limitations"])


def test_scale_plan_hard_refuses_above_four_trillion(client):
    resp = client.post(
        "/api/cas-harness/audit/scale-plan",
        json={
            "model_id": "frontier/too-large",
            "parameter_count_b": 5000,
            "accept_experimental_frontier": True,
        },
    )

    assert resp.status_code == 422


def test_distributed_session_carries_the_frontier_gate(client, auth_headers):
    # The control-plane run path must honour the same experimental gate.
    # Unlike /scale-plan (a public demo prefix), /distributed/session is JWT
    # protected because it can register workers, lease jobs, and submit
    # evidence receipts -- so these calls carry auth_headers and the 422 we
    # assert is the frontier gate firing, not the auth layer.
    refused = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={"model_id": "frontier/open-1t", "parameter_count_b": 1000},
        headers=auth_headers,
    )
    assert refused.status_code == 422
    assert "accept_experimental_frontier" in refused.text

    # Accepting experimental risk unlocks the request path but is NOT enough on
    # its own: a real frontier run also needs a model provenance/license/hash
    # manifest (frontier run-gate 5). Without it the run is refused 422.
    refused_no_provenance = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "frontier/open-1t",
            "parameter_count_b": 1000,
            "accept_experimental_frontier": True,
        },
        headers=auth_headers,
    )
    assert refused_no_provenance.status_code == 422
    assert "provenance" in refused_no_provenance.text.lower()

    # A valid provenance manifest still is NOT enough on its own: a real frontier
    # run also needs a declared model architecture that resolves to a probe
    # adapter the worker can mechanically hook (frontier run-gate 6). The probe
    # worker can only locate decoder stacks at four hardcoded attribute paths, so
    # an unknown architecture would make it raise rather than emit activations.
    # Provenance is valid here, so the 422 we assert is the architecture gate.
    valid_provenance = {
        "model_id": "frontier/open-1t",
        "source_uri": "https://huggingface.co/frontier/open-1t",
        "license_id": "apache-2.0",
        "weight_files": [
            {"path": "model-00001-of-00002.safetensors", "sha256": "a" * 64},
            {"path": "model-00002-of-00002.safetensors", "sha256": "b" * 64},
        ],
        "revision": "main",
    }
    refused_no_architecture = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "frontier/open-1t",
            "parameter_count_b": 1000,
            "accept_experimental_frontier": True,
            "provenance": valid_provenance,
        },
        headers=auth_headers,
    )
    assert refused_no_architecture.status_code == 422
    assert "architecture" in refused_no_architecture.text.lower()

    # Provenance + a hookable architecture still is NOT enough on its own: a real
    # frontier run also needs a structurally loadable CAS probe-readout spec
    # (frontier run-gate 7). The CAS axis readout is the run's central deliverable
    # -- declared in every shard's expected_outputs -- so without a loadable probe
    # it would silently come back missing. The two prior gates are satisfied here,
    # so the 422 we assert is the probe gate firing.
    refused_no_probe = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "frontier/open-1t",
            "parameter_count_b": 1000,
            "accept_experimental_frontier": True,
            "provenance": valid_provenance,
            "architecture": {"model_type": "llama"},
        },
        headers=auth_headers,
    )
    assert refused_no_probe.status_code == 422
    assert "probe" in refused_no_probe.text.lower()

    # Provenance + architecture + a loadable probe still is NOT enough on its own:
    # a real frontier run also needs a compute envelope that can physically hold
    # the model (frontier run-gate 3). The planner silently provisions only 62% of
    # each accelerator and clamps worker fan-out to 512, so a 1T model can get a
    # plan that LOOKS schedulable while every shard is asked to hold more than one
    # accelerator can fit. Without a declared envelope the run is refused 422. The
    # three prior gates are satisfied here, so the 422 we assert is the compute gate.
    refused_no_compute = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "frontier/open-1t",
            "parameter_count_b": 1000,
            "accept_experimental_frontier": True,
            "provenance": valid_provenance,
            "architecture": {"model_type": "llama"},
            "probe": {
                "schema_version": "cas_probe_linear_v1",
                "axes": ["F1", "F2", "F3"],
                "feature_dimension": 200,
                "definition_sha256": LOCKED_TKS_DEFINITION_SHA256,
            },
        },
        headers=auth_headers,
    )
    assert refused_no_compute.status_code == 422
    assert "compute" in refused_no_compute.text.lower()

    # Provenance + architecture + probe + a sufficient compute envelope still is NOT
    # enough on its own: a real frontier run also needs the caller to acknowledge its
    # caller-owned, unquoted compute cost (frontier run-gate 4). The planner models no
    # duration, throughput, or dollar rate, so the gate quotes no price -- it surfaces
    # the real committed magnitude and requires explicit acknowledgement for an
    # EXPERIMENTAL_NOT_VALIDATED result. The four prior gates are satisfied here, so
    # the 422 we assert is the cost gate firing, and it never quotes a price.
    refused_no_cost = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "frontier/open-1t",
            "parameter_count_b": 1000,
            "accept_experimental_frontier": True,
            "provenance": valid_provenance,
            "architecture": {"model_type": "llama"},
            "probe": {
                "schema_version": "cas_probe_linear_v1",
                "axes": ["F1", "F2", "F3"],
                "feature_dimension": 200,
                "definition_sha256": LOCKED_TKS_DEFINITION_SHA256,
            },
            "compute": {
                "accelerator_count": 64,
                "accelerator_memory_gb": 80,
                "accelerator_type": "H100-80GB",
            },
        },
        headers=auth_headers,
    )
    assert refused_no_cost.status_code == 422
    assert "cost not acknowledged" in refused_no_cost.text.lower()
    assert "accept_frontier_compute_cost" in refused_no_cost.text
    assert "$" not in refused_no_cost.text

    # All five frontier gates cleared -- including the cost ack -- still is NOT enough on
    # its own: every distributed run is also a data *harvest* (run-gate 8, UNIVERSAL).
    # The audit captures the model's I/O, the pooled activations the probe hooks, the CAS
    # axis readout, and the verdict, and commits them to an immutable write-once store
    # reused as CAS-Native training signal. The caller must acknowledge that capture. Gate
    # (8) runs LAST, so with all earlier gates satisfied here the 422 we assert is
    # unambiguously the data-capture gate firing.
    refused_no_data = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "frontier/open-1t",
            "parameter_count_b": 1000,
            "accept_experimental_frontier": True,
            "accept_frontier_compute_cost": True,
            "provenance": valid_provenance,
            "architecture": {"model_type": "llama"},
            "probe": {
                "schema_version": "cas_probe_linear_v1",
                "axes": ["F1", "F2", "F3"],
                "feature_dimension": 200,
                "definition_sha256": LOCKED_TKS_DEFINITION_SHA256,
            },
            "compute": {
                "accelerator_count": 64,
                "accelerator_memory_gb": 80,
                "accelerator_type": "H100-80GB",
            },
        },
        headers=auth_headers,
    )
    assert refused_no_data.status_code == 422
    assert "data capture not acknowledged" in refused_no_data.text.lower()
    assert "accept_audit_data_capture" in refused_no_data.text

    # Ack + a well-formed, identity-matching, open-weight-licensed manifest + a
    # declared architecture that resolves to a supported probe adapter + a
    # structurally loadable CAS probe spec + a compute envelope that can physically
    # hold the model + an explicit cost acknowledgement + an explicit data-capture
    # acknowledgement is enough to CREATE the run.
    # The hashes are declared (not recomputed), the layout is confirmed worker-side at
    # load time, the probe is actually loaded and run worker-side, the fit is computed
    # from the planner's own memory math, the cost is acknowledged (never metered), and
    # the data capture is acknowledged (never WORM-committed) -- all at the API tier,
    # which touches no weights -- so the honest statuses are
    # PROVENANCE_DECLARED_NOT_VERIFIED + ARCHITECTURE_ADAPTER_AVAILABLE +
    # PROBE_COMPATIBILITY_DECLARED + COMPUTE_FEASIBILITY_DECLARED + COST_ACKNOWLEDGED +
    # DATA_CAPTURE_ACKNOWLEDGED -- never a verdict.
    allowed = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "frontier/open-1t",
            "parameter_count_b": 1000,
            "accept_experimental_frontier": True,
            "accept_frontier_compute_cost": True,
            "accept_audit_data_capture": True,
            "provenance": valid_provenance,
            "architecture": {"model_type": "llama"},
            "probe": {
                "schema_version": "cas_probe_linear_v1",
                "axes": ["F1", "F2", "F3"],
                "feature_dimension": 200,
                "definition_sha256": LOCKED_TKS_DEFINITION_SHA256,
            },
            "compute": {
                "accelerator_count": 64,
                "accelerator_memory_gb": 80,
                "accelerator_type": "H100-80GB",
            },
        },
        headers=auth_headers,
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["plan"]["validation_status"] == "EXPERIMENTAL_NOT_VALIDATED"
    assert body["provenance"]["status"] == "PROVENANCE_DECLARED_NOT_VERIFIED"
    assert body["provenance"]["license_recognized"] is True
    assert body["provenance"]["all_hashes_verified"] is False
    assert body["architecture"]["status"] == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert body["architecture"]["resolved_model_type"] == "llama"
    assert body["architecture"]["adapter_available"] is True
    assert body["probe"]["status"] == "PROBE_COMPATIBILITY_DECLARED"
    assert body["probe"]["probe_loadable"] is True
    assert body["probe"]["weights_hash_verified"] is False
    assert body["compute"]["status"] == "COMPUTE_FEASIBILITY_DECLARED"
    assert body["compute"]["memory_sufficient"] is True
    assert body["compute"]["fit_verified"] is False
    # Run-gate (4): the caller acknowledged the run's caller-owned, unquoted compute
    # cost. Acknowledged is enough to CREATE the run but is never METERED at the API
    # tier -- real accelerator-hours are metered fleet-side, where compute runs.
    assert body["cost"]["status"] == "COST_ACKNOWLEDGED"
    assert body["cost"]["acknowledged"] is True
    assert body["cost"]["cost_metered"] is False
    # Run-gate (8): the caller acknowledged the run's data capture. Acknowledged is enough
    # to CREATE the run but is never WORM_COMMITTED at the API tier -- the immutable write
    # happens fleet-side, when the workers run and the model actually executes. The receipt
    # surfaces the real captured-signal classes, never an invented capture scope.
    assert body["data_capture"]["status"] == "DATA_CAPTURE_ACKNOWLEDGED"
    assert body["data_capture"]["acknowledged"] is True
    assert body["data_capture"]["capture_committed"] is False
    assert "pooled_hidden_state_activations" in body["data_capture"]["captured_signal_classes"]
    # Run-gate (2) rides along on every distributed run: an open-weight target is
    # mechanistically reachable, so the access receipt is DECLARED -- never
    # VERIFIED at the API tier, which touches no weights.
    assert body["access"]["status"] == "MODEL_ACCESS_DECLARED"
    assert body["access"]["mechanistic_probe_supported"] is True
    assert body["access"]["access_verified"] is False


def test_verify_reference_model_target_public_for_alpha_console(client):
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={"target": {"kind": "demo_reference"}},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["target"]["model_id"] == "EleutherAI/gpt-neox-20b"
    assert (
        body["reference_evidence_packet_trace_id"]
        == "stage9-40e-original-baseline-readout-20260527"
    )
    assert body["verdict"] is None
    assert body["confidence"] is None


def test_verify_api_endpoint_target_success_does_not_echo_secret_or_verdict(
    client,
    auth_headers,
):
    secret = "sk-test-secret-should-not-echo"
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={
            "target": {
                "kind": "api_endpoint",
                "provider": "openai",
                "model_id": "gpt-4.1-mini",
                "endpoint_url": "https://model.example/v1/chat/completions",
                "api_key": secret,
            }
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert secret not in resp.text
    body = resp.json()
    assert body["connection_state"] == "CONFIGURED"
    assert body["model_status"] == "READY"
    assert body["target"]["credential_mode"] == "ephemeral_secret"
    assert body["target"]["endpoint_url"] == "https://model.example/v1/chat/completions"
    assert body["provenance_chip"]["status"] == "present"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert "did not call the model" in body["detail"]


def test_verify_reference_model_target_rejects_credentials(client, auth_headers):
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={
            "target": {
                "kind": "demo_reference",
                "credential_ref": "prod-openai-key",
            }
        },
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "demo_reference target must not include credentials" in resp.text


def test_verify_model_target_requires_target(client, auth_headers):
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={},
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "target" in resp.text


def test_verify_model_target_rejects_bad_endpoint_url(client, auth_headers):
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={
            "target": {
                "kind": "api_endpoint",
                "model_id": "custom-model",
                "endpoint_url": "ftp://model.example/v1/chat/completions",
                "allow_unauthenticated": True,
            }
        },
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "endpoint_url" in resp.text


def test_verify_model_target_rejects_incomplete_endpoint_config(client, auth_headers):
    resp = client.post(
        "/api/cas-harness/audit/target/verify",
        json={
            "target": {
                "kind": "api_endpoint",
                "model_id": "custom-model",
                "endpoint_url": "https://model.example/v1/chat/completions",
            }
        },
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "credential_ref, api_key, or allow_unauthenticated=true" in resp.text


def test_create_audit_session_returns_stored_draft_without_fake_result(client, auth_headers):
    resp = client.post(
        "/api/cas-harness/audit/session",
        json=_valid_payload(),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_id"].startswith("cas-audit-")
    assert body["status"] == "DRAFT"
    assert body["model_status"] == "NOT_CONNECTED_MOCK"
    assert body["model_id"] == "openai:gpt-4.1-mini"
    assert body["endpoint_url"] is None
    assert body["audit_mode"] == "BALANCED"
    assert body["prompt_summary"] == "Assess whether this answer should be accepted or suppressed."
    assert body["scenario_summary"] is None
    assert body["selected_modules"] == ["cognitive_bias", "provenance_trace"]
    assert body["created_at"]
    assert body["updated_at"]
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] is None
    assert body["atlas_deep_link"] is None
    assert [chip["id"] for chip in body["provenance_chips"]] == [
        "model_proof",
        "cas_readout",
        "causal_proof",
        "control_proof",
        "output_proof",
        "packet_proof",
    ]
    assert body["provenance_chips"][0]["status"] == "missing"
    assert body["provenance_chips"][-1]["status"] == "missing"
    assert body["lifecycle"][0]["status"] == "DRAFT"


def test_audit_session_requires_model_target(client, auth_headers):
    payload = _valid_payload()
    payload.pop("model_id")

    resp = client.post(
        "/api/cas-harness/audit/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "Either model_id or endpoint_url is required" in resp.text


def test_audit_session_accepts_endpoint_url_and_scenario_text(client, auth_headers):
    payload = {
        "endpoint_url": "https://model.example/v1/chat/completions",
        "audit_mode": "MAX_COVERAGE_TRIAGE",
        "scenario_text": "The model is asked to triage a risky medical instruction.",
        "selected_modules": ["safety_triage"],
    }

    resp = client.post(
        "/api/cas-harness/audit/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "DRAFT"
    assert body["endpoint_url"] == "https://model.example/v1/chat/completions"
    assert body["scenario_summary"] == "The model is asked to triage a risky medical instruction."


def test_audit_session_can_attach_existing_evidence_packet(client, auth_headers):
    payload = {
        **_valid_payload(),
        "evidence_packet_trace_id": "dev_example_001",
    }

    resp = client.post(
        "/api/cas-harness/audit/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    chips = {chip["id"]: chip for chip in body["provenance_chips"]}

    assert body["evidence_packet_trace_id"] == "dev_example_001"
    assert body["atlas_deep_link"] == "/cockpit?trace_id=dev_example_001"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert chips["packet_proof"]["status"] == "present"
    assert chips["output_proof"]["status"] == "present"
    assert chips["cas_readout"]["status"] in {"present", "missing"}
    assert "Evidence Packet dev_example_001" in body["lifecycle"][0]["message"]


def test_audit_session_rejects_missing_evidence_packet(client, auth_headers):
    payload = {
        **_valid_payload(),
        "evidence_packet_trace_id": "missing-trace-id",
    }

    resp = client.post(
        "/api/cas-harness/audit/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 404
    assert "Evidence Packet trace_id not found" in resp.json()["detail"]


def test_audit_session_rejects_invalid_mode_and_empty_modules(client, auth_headers):
    payload = _valid_payload()
    payload["audit_mode"] = "FAST"
    payload["selected_modules"] = []

    resp = client.post(
        "/api/cas-harness/audit/session",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422
    assert "BALANCED" in resp.text
    assert "selected_modules" in resp.text


def test_verdict_vocabulary_is_limited_to_public_contract():
    assert set(get_args(Verdict)) == {
        "ACCEPT",
        "SUPPRESS",
        "FLAG_FOR_HUMAN_REVIEW",
    }


def test_status_route_returns_stored_session_state(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/session",
        json=_valid_payload(),
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]

    status = client.get(
        f"/api/cas-harness/audit/session/{audit_id}/status",
        headers=auth_headers,
    )

    assert status.status_code == 200
    assert status.json() == created.json()
    assert status.json()["audit_id"] == audit_id
    assert status.json()["verdict"] is None
    assert status.json()["confidence"] is None


def test_status_route_rejects_unknown_session(client, auth_headers):
    resp = client.get(
        "/api/cas-harness/audit/session/cas-audit-missing/status",
        headers=auth_headers,
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Audit session not found"


def test_run_route_advances_lifecycle_without_inventing_verdict(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/session",
        json=_valid_payload(),
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    assert body["status"] == "SCAFFOLD_PENDING_RUNNER"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] is None
    assert body["atlas_deep_link"] is None
    assert [event["status"] for event in body["lifecycle"]] == [
        "DRAFT",
        "VALIDATING",
        "RUNNING",
        "SCAFFOLD_PENDING_RUNNER",
    ]
    assert "no verdict or confidence" in body["lifecycle"][-1]["message"]

    status = client.get(
        f"/api/cas-harness/audit/session/{audit_id}/status",
        headers=auth_headers,
    )
    assert status.json() == body


def test_run_route_calls_live_worker_for_hosted_pythia_and_routes_to_review(
    client,
    auth_headers,
    monkeypatch,
):
    async def fake_live_worker_audit(**kwargs):
        assert kwargs["model_id"] == "EleutherAI/pythia-160m"
        assert kwargs["prompt"] == "Audit this live prompt."
        return type(
            "LiveResult",
            (),
            {
                "trace_id": "cas-live-test-001",
                "proof_chips": [
                    {
                        "id": "model_proof",
                        "name": "Model proof",
                        "status": "present",
                        "detail": "Hosted open-weight live worker ran model target EleutherAI/pythia-160m.",
                    },
                    {
                        "id": "cas_readout",
                        "name": "CAS readout",
                        "status": "present",
                        "detail": "Live worker emitted token-level activation/readout events.",
                    },
                    {
                        "id": "causal_proof",
                        "name": "Causal proof",
                        "status": "unavailable",
                        "detail": "No ablation/intervention proof was run in this live-worker slice.",
                    },
                    {
                        "id": "control_proof",
                        "name": "Control proof",
                        "status": "unavailable",
                        "detail": "No matched-control proof was run in this live-worker slice.",
                    },
                    {
                        "id": "output_proof",
                        "name": "Output proof",
                        "status": "present",
                        "detail": "Live worker output text is recorded in the Evidence Packet.",
                    },
                    {
                        "id": "packet_proof",
                        "name": "Packet proof",
                        "status": "present",
                        "detail": "Live Evidence Packet cas-live-test-001 was written.",
                    },
                ],
                "verifier_decision": None,
                "audit_scope": {
                    "kind": "open_weight_live_trace",
                    "label": (
                        "Open-weight live trace · activations + readout captured · "
                        "causal/control not yet run · verdict held for review"
                    ),
                    "internal_activation_access": True,
                    "verdict_disposition": "held_for_human_review",
                },
                "message": "Live hosted open-weight worker ran and wrote an Evidence Packet.",
            },
        )()

    monkeypatch.setattr(
        "api.routes.cas_harness_audit.run_live_worker_audit",
        fake_live_worker_audit,
    )
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            "model_id": "EleutherAI/pythia-160m",
            "audit_mode": "BALANCED",
            "prompt": "Audit this live prompt.",
            "selected_modules": ["active_trace", "confidence_margin"],
        },
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    chips = {chip["id"]: chip["status"] for chip in body["provenance_chips"]}
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] == "cas-live-test-001"
    assert body["atlas_deep_link"] == "/cockpit?trace_id=cas-live-test-001"
    assert body["audit_scope"]["kind"] == "open_weight_live_trace"
    assert body["audit_scope"]["internal_activation_access"] is True
    assert chips == {
        "model_proof": "present",
        "cas_readout": "present",
        "causal_proof": "unavailable",
        "control_proof": "unavailable",
        "output_proof": "present",
        "packet_proof": "present",
    }
    assert [event["status"] for event in body["lifecycle"]] == [
        "DRAFT",
        "EVIDENCE_READY",
        "VALIDATING",
        "RUNNING",
        "COMPLETE",
    ]
    assert "missing required proof" in body["lifecycle"][-1]["message"]


def test_run_route_rejects_demo_worker_dump_without_persisting_evidence(
    client, auth_headers, tmp_path, monkeypatch
):
    async def fake_dump(_worker_base, _payload):
        return {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "is_real_model": False,
                    },
                },
                {"type": "token", "token_index": 0, "token": " synthetic"},
                {"type": "complete", "total_tokens": 1},
            ]
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(settings, "atlas_live_worker_token", "test-worker-token")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump", fake_dump
    )
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            "model_id": "EleutherAI/pythia-160m",
            "audit_mode": "BALANCED",
            "prompt": "Reject demo output.",
            "selected_modules": ["active_trace"],
        },
        headers=auth_headers,
    )

    ran = client.post(
        f"/api/cas-harness/audit/session/{created.json()['audit_id']}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    assert body["status"] == "FAILED"
    assert body["verdict"] is None
    assert body["evidence_packet_trace_id"] is None
    assert "did not prove real model weights" in body["lifecycle"][-1]["message"]
    assert list(iter_harvest_records()) == []
    assert list(tmp_path.rglob("*.json")) == []
    assert list(tmp_path.rglob("*.jsonl")) == []


def test_run_route_calls_customer_api_and_routes_to_review(
    client,
    auth_headers,
    tmp_path,
    monkeypatch,
):
    # End-to-end through the real mock connector: a closed-API audit captures
    # model I/O but no activations, so it must honestly land at human review.
    monkeypatch.setenv("CAS_HARNESS_HARVEST_STORE_DIR", str(tmp_path / "harvest"))
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            "model_id": "mock-cas-v1",
            "provider": "mock",
            "endpoint_url": "https://api.example.com/v1/chat",
            "audit_mode": "BALANCED",
            "prompt": "Audit this customer model output.",
            "selected_modules": ["active_trace", "confidence_margin"],
        },
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]
    assert created.json()["provider"] == "mock"

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    chips = {chip["id"]: chip["status"] for chip in body["provenance_chips"]}
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"].startswith("cas-api-")
    assert body["audit_scope"]["kind"] == "output_only_api_harvest"
    assert body["audit_scope"]["internal_activation_access"] is False
    assert "Output-only harvest" in body["audit_scope"]["label"]
    assert chips == {
        "model_proof": "present",
        "cas_readout": "unavailable",
        "causal_proof": "unavailable",
        "control_proof": "unavailable",
        "output_proof": "present",
        "packet_proof": "present",
    }
    assert [event["status"] for event in body["lifecycle"]] == [
        "DRAFT",
        "EVIDENCE_READY",
        "VALIDATING",
        "RUNNING",
        "COMPLETE",
    ]


def test_run_route_threads_byok_key_to_connector_and_never_echoes_it(
    client,
    auth_headers,
    tmp_path,
    monkeypatch,
):
    # BYOK: the customer supplies their own API key on the run call. It must
    # reach the connector for that one run but never be persisted or echoed.
    from api.llm_connectors.mock_connector import MockLLMConnector

    captured: dict[str, object] = {}

    def fake_get_connector(provider, model=None, *, api_key_override=None):
        captured["provider"] = provider
        captured["api_key_override"] = api_key_override
        return MockLLMConnector()

    monkeypatch.setenv("CAS_HARNESS_HARVEST_STORE_DIR", str(tmp_path / "harvest"))
    monkeypatch.setattr(
        "api.services.cas_harness_api_endpoint_runner.get_connector",
        fake_get_connector,
    )

    secret = "sk-customer-byok-route-do-not-store-7q7q"
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            "model_id": "gpt-4",
            "provider": "openai",
            "endpoint_url": "https://api.example.com/v1/chat",
            "audit_mode": "BALANCED",
            "prompt": "Audit this customer model output.",
            "selected_modules": ["active_trace"],
        },
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]
    # The create-session call carried no key — nothing to leak there.
    assert secret not in created.text

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        json={"api_key": secret},
        headers=auth_headers,
    )
    assert ran.status_code == 200
    body = ran.json()
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"

    # The ephemeral key reached the connector...
    assert captured["api_key_override"] == secret
    assert captured["provider"] == "openai"

    # ...but is never echoed in the run response or the stored session status.
    assert secret not in ran.text
    status = client.get(
        f"/api/cas-harness/audit/session/{audit_id}/status",
        headers=auth_headers,
    )
    assert secret not in status.text


def test_run_route_flags_attached_packet_when_required_proof_is_incomplete(client, auth_headers):
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "evidence_packet_trace_id": "dev_example_001",
        },
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] == "dev_example_001"
    assert body["atlas_deep_link"] == "/cockpit?trace_id=dev_example_001"
    assert [event["status"] for event in body["lifecycle"]] == [
        "DRAFT",
        "VALIDATING",
        "RUNNING",
        "COMPLETE",
    ]
    assert "missing required proof" in body["lifecycle"][-1]["message"]


def test_reference_target_trace_routes_to_review_without_worm_retention(client, auth_headers):
    verified = client.post(
        "/api/cas-harness/audit/target/verify",
        json={"target": {"kind": "demo_reference"}},
        headers=auth_headers,
    )
    assert verified.status_code == 200
    trace_id = verified.json()["reference_evidence_packet_trace_id"]

    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "model_id": "EleutherAI/gpt-neox-20b",
            "evidence_packet_trace_id": trace_id,
        },
        headers=auth_headers,
    )
    assert created.status_code == 200
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    chips = {chip["id"]: chip["status"] for chip in body["provenance_chips"]}
    assert body["status"] == "COMPLETE"
    # The real Stage 9 40E packet carries a genuine scoped-validation ACCEPT
    # decision, but with no WORM/S3 anchor the runner correctly withholds the
    # final ACCEPT and routes to human review.
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] == "stage9-40e-original-baseline-readout-20260527"
    assert (
        body["atlas_deep_link"]
        == "/cockpit?trace_id=stage9-40e-original-baseline-readout-20260527"
    )
    assert body["verifier_decision"] == {
        "verdict": "ACCEPT",
        "confidence": 0.95625,
        "source": "stage9_40e_packet_verifier",
        "reason": "all_stage9_40e_validation_gates_passed",
        "decision_scope": "stage9_40e_validation_packet",
        "coverage": {
            "basis": "stage9_40e_validation_cases",
            "case_count": 80,
            "class_count": 40,
        },
    }
    assert chips == {
        "model_proof": "present",
        "cas_readout": "verified",
        "causal_proof": "verified",
        "control_proof": "verified",
        "output_proof": "verified",
        "packet_proof": "present",
    }
    assert [event["status"] for event in body["lifecycle"]] == [
        "DRAFT",
        "VALIDATING",
        "RUNNING",
        "COMPLETE",
    ]
    assert "WORM-retained Evidence Packet" in body["lifecycle"][-1]["message"]


def test_reference_target_trace_from_public_alpha_console_stays_review_only_without_worm(client):
    verified = client.post(
        "/api/cas-harness/audit/target/verify",
        json={"target": {"kind": "demo_reference"}},
    )
    trace_id = verified.json()["reference_evidence_packet_trace_id"]

    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "model_id": "EleutherAI/gpt-neox-20b",
            "evidence_packet_trace_id": trace_id,
        },
    )
    audit_id = created.json()["audit_id"]
    ran = client.post(f"/api/cas-harness/audit/session/{audit_id}/run")

    assert verified.status_code == 200
    assert created.status_code == 200
    assert ran.status_code == 200
    assert ran.json()["verdict"] == "FLAG_FOR_HUMAN_REVIEW"


def test_run_route_accepts_only_when_complete_packet_has_explicit_verifier_decision_and_worm(
    client,
    auth_headers,
    monkeypatch,
):
    packet = _attach_worm_anchor(_complete_stage21_packet(action="allow", accepted=True))
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.build_packet_for_trace",
        lambda trace_id: _PacketStub(packet),
    )
    monkeypatch.setattr("api.routes.cas_harness_audit._verify_hashes_for_trace", _worm_verify_hashes)
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "evidence_packet_trace_id": "stage21-allow-001",
        },
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    chips = {chip["id"]: chip["status"] for chip in body["provenance_chips"]}
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "ACCEPT"
    assert body["confidence"] == 0.9816
    assert body["verifier_decision"] == {
        "verdict": "ACCEPT",
        "confidence": 0.9816,
        "source": "stage19_verification_stack+stage20_generation_readiness",
        "reason": "Stage 19 accepted the row and Stage 20 readiness action is allow.",
        "decision_scope": None,
        "coverage": None,
    }
    assert set(chips.values()).issubset({"present", "verified"})
    assert chips["packet_proof"] == "verified"
    assert "explicit verifier decision" in body["lifecycle"][-1]["message"]


def test_run_route_uses_s7_f28_packet_as_conservative_human_review(client, auth_headers):
    trace_id = "s7-f28-balanced-bridge-gpt-neox-20b-20260526"
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "model_id": "EleutherAI/gpt-neox-20b",
            "evidence_packet_trace_id": trace_id,
        },
        headers=auth_headers,
    )
    assert created.status_code == 200, created.text
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    chips = {chip["id"]: chip["status"] for chip in body["provenance_chips"]}
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] == 0.803571
    assert body["evidence_packet_trace_id"] == trace_id
    assert body["atlas_deep_link"] == f"/cockpit?trace_id={trace_id}"
    assert body["verifier_decision"]["source"] == "S7-F28-BALANCED-BRIDGE"
    assert set(chips.values()).issubset({"verified", "present"})
    assert "explicit verifier decision" in body["lifecycle"][-1]["message"]


def test_run_route_uses_stage9_40e_packet_as_review_only_without_worm_anchor(client, auth_headers):
    trace_id = "stage9-40e-original-baseline-readout-20260527"
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "model_id": "EleutherAI/gpt-neox-20b",
            "evidence_packet_trace_id": trace_id,
        },
        headers=auth_headers,
    )
    assert created.status_code == 200, created.text
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    chips = {chip["id"]: chip["status"] for chip in body["provenance_chips"]}
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] == trace_id
    assert body["atlas_deep_link"] == f"/cockpit?trace_id={trace_id}"
    assert body["verifier_decision"] == {
        "verdict": "ACCEPT",
        "confidence": 0.95625,
        "source": "stage9_40e_packet_verifier",
        "reason": "all_stage9_40e_validation_gates_passed",
        "decision_scope": "stage9_40e_validation_packet",
        "coverage": {
            "basis": "stage9_40e_validation_cases",
            "case_count": 80,
            "class_count": 40,
        },
    }
    assert chips == {
        "model_proof": "present",
        "cas_readout": "verified",
        "causal_proof": "verified",
        "control_proof": "verified",
        "output_proof": "verified",
        "packet_proof": "present",
    }
    assert "WORM-retained Evidence Packet" in body["lifecycle"][-1]["message"]


def test_run_route_accepts_stage9_40e_packet_once_worm_anchored(client, auth_headers, monkeypatch):
    from api.routes.evidence import load_stage9_40e_packet_payload_for_trace

    trace_id = "stage9-40e-original-baseline-readout-20260527"
    anchored = _attach_worm_anchor(load_stage9_40e_packet_payload_for_trace(trace_id))
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.load_anchored_static_packet_payload",
        lambda tid: anchored if tid == trace_id else None,
    )
    monkeypatch.setattr(
        "api.routes.cas_harness_audit._verify_hashes_for_trace",
        lambda tid: _worm_verify_hashes(tid) if tid == trace_id else None,
    )

    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "model_id": "EleutherAI/gpt-neox-20b",
            "evidence_packet_trace_id": trace_id,
        },
        headers=auth_headers,
    )
    assert created.status_code == 200, created.text
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    chips = {chip["id"]: chip["status"] for chip in body["provenance_chips"]}
    # With a real WORM/S3 object-lock anchor re-read, the Stage 9 40E scoped
    # validation packet's explicit ACCEPT is no longer withheld.
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "ACCEPT"
    assert body["confidence"] == 0.95625
    assert body["evidence_packet_trace_id"] == trace_id
    assert chips["packet_proof"] == "verified"
    assert set(chips.values()).issubset({"present", "verified"})
    assert "explicit verifier decision" in body["lifecycle"][-1]["message"]


def test_run_route_suppresses_only_when_complete_packet_has_explicit_rejection(
    client,
    auth_headers,
    monkeypatch,
):
    packet = _attach_worm_anchor(_complete_stage21_packet(action="suppress", accepted=False))
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.build_packet_for_trace",
        lambda trace_id: _PacketStub(packet),
    )
    monkeypatch.setattr("api.routes.cas_harness_audit._verify_hashes_for_trace", _worm_verify_hashes)
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "evidence_packet_trace_id": "stage21-suppress-001",
        },
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "SUPPRESS"
    assert body["confidence"] == 0.9
    assert body["verifier_decision"] == {
        "verdict": "SUPPRESS",
        "confidence": 0.9,
        "source": "stage19_verification_stack+stage20_generation_readiness",
        "reason": "Stage 19 rejected the row and Stage 20 readiness action is suppress.",
        "decision_scope": None,
        "coverage": None,
    }


def test_run_route_blocks_explicit_verifier_decision_when_required_proof_is_incomplete(
    client,
    auth_headers,
    monkeypatch,
):
    packet = _complete_stage21_packet(action="allow", accepted=True)
    packet.pop("matched_controls")
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.build_packet_for_trace",
        lambda trace_id: _PacketStub(packet),
    )
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "evidence_packet_trace_id": "stage21-missing-control-001",
        },
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    chips = {chip["id"]: chip["status"] for chip in body["provenance_chips"]}
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["verifier_decision"]["verdict"] == "ACCEPT"
    assert chips["control_proof"] == "missing"
    assert "missing required proof" in body["lifecycle"][-1]["message"]


def test_run_route_flags_complete_packet_without_stage19_stage20_verifier_sources(
    client,
    auth_headers,
    monkeypatch,
):
    packet = _complete_stage21_packet(action="allow", accepted=True)
    packet["provenance"]["source_reports"] = ["stage21_packet_builder_report.json"]
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.build_packet_for_trace",
        lambda trace_id: _PacketStub(packet),
    )
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            **_valid_payload(),
            "evidence_packet_trace_id": "stage21-no-verifier-sources-001",
        },
        headers=auth_headers,
    )
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )

    assert ran.status_code == 200
    body = ran.json()
    chips = {chip["id"]: chip["status"] for chip in body["provenance_chips"]}
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["confidence"] is None
    assert body["verifier_decision"] is None
    assert set(chips.values()) == {"present"}
    assert "no explicit Stage 19/20/21 verifier decision" in body["lifecycle"][-1]["message"]


def test_list_route_returns_in_process_sessions(client, auth_headers):
    first_payload = _valid_payload()
    second_payload = {
        **_valid_payload(),
        "prompt": "Second audit scenario.",
        "selected_modules": ["verification_stack"],
    }
    first = client.post(
        "/api/cas-harness/audit/session",
        json=first_payload,
        headers=auth_headers,
    ).json()
    second = client.post(
        "/api/cas-harness/audit/session",
        json=second_payload,
        headers=auth_headers,
    ).json()

    listed = client.get("/api/cas-harness/audit/sessions", headers=auth_headers)

    assert listed.status_code == 200
    audit_ids = [session["audit_id"] for session in listed.json()["sessions"]]
    assert audit_ids == [first["audit_id"], second["audit_id"]]


def test_duplicate_payload_reuses_existing_deterministic_session(client, auth_headers):
    first = client.post(
        "/api/cas-harness/audit/session",
        json=_valid_payload(),
        headers=auth_headers,
    ).json()
    second = client.post(
        "/api/cas-harness/audit/session",
        json=_valid_payload(),
        headers=auth_headers,
    ).json()

    assert second == first


# --------------------------------------------------------------------------- #
# Phase-1 tenant-scope isolation (close the cross-tenant audit-session leak)
# --------------------------------------------------------------------------- #


def _headers_for(sub: str, api_key: str) -> dict[str, str]:
    """Auth headers for a specific caller identity (sub + api_key)."""
    from api.middleware.auth import create_token

    return {"Authorization": f"Bearer {create_token(sub=sub, api_key=api_key)}"}


def test_list_sessions_scoped_to_caller_identity(client):
    # Caller A creates a session; caller B creates their own. Each /sessions
    # listing must return ONLY that caller's own session, never the other's.
    headers_a = _headers_for("caller-a", "key-a")
    headers_b = _headers_for("caller-b", "key-b")

    a_created = client.post(
        "/api/cas-harness/audit/session", json=_valid_payload(), headers=headers_a
    ).json()
    b_created = client.post(
        "/api/cas-harness/audit/session",
        json={**_valid_payload(), "prompt": "Caller B private scenario."},
        headers=headers_b,
    ).json()

    a_list = client.get("/api/cas-harness/audit/sessions", headers=headers_a)
    b_list = client.get("/api/cas-harness/audit/sessions", headers=headers_b)

    assert a_list.status_code == 200
    assert b_list.status_code == 200
    a_ids = {s["audit_id"] for s in a_list.json()["sessions"]}
    b_ids = {s["audit_id"] for s in b_list.json()["sessions"]}

    # A sees only A's session; B sees only B's. Neither sees the other's.
    assert a_ids == {a_created["audit_id"]}
    assert b_ids == {b_created["audit_id"]}
    assert b_created["audit_id"] not in a_ids
    assert a_created["audit_id"] not in b_ids


def test_get_session_status_denied_across_callers(client):
    # Caller B must not be able to fetch caller A's session by id: it reads as
    # 404 (fail closed), indistinguishable from a session that does not exist.
    headers_a = _headers_for("caller-a", "key-a")
    headers_b = _headers_for("caller-b", "key-b")

    a_created = client.post(
        "/api/cas-harness/audit/session", json=_valid_payload(), headers=headers_a
    ).json()
    audit_id = a_created["audit_id"]

    # The owner can read their own session.
    owner_view = client.get(
        f"/api/cas-harness/audit/session/{audit_id}/status", headers=headers_a
    )
    assert owner_view.status_code == 200
    assert owner_view.json()["audit_id"] == audit_id

    # A different caller cannot.
    cross = client.get(
        f"/api/cas-harness/audit/session/{audit_id}/status", headers=headers_b
    )
    assert cross.status_code == 404
    assert cross.json()["detail"] == "Audit session not found"


def test_run_session_denied_across_callers(client):
    # Caller B must not be able to run caller A's session by id.
    headers_a = _headers_for("caller-a", "key-a")
    headers_b = _headers_for("caller-b", "key-b")

    a_created = client.post(
        "/api/cas-harness/audit/session", json=_valid_payload(), headers=headers_a
    ).json()
    audit_id = a_created["audit_id"]

    cross_run = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run", headers=headers_b
    )
    assert cross_run.status_code == 404
    assert cross_run.json()["detail"] == "Audit session not found"


def test_unauthenticated_caller_cannot_see_authenticated_sessions(client):
    # An identity-less caller must NOT see an authenticated caller's sessions,
    # and must not be able to fetch one by id. Fail closed.
    headers_a = _headers_for("caller-a", "key-a")

    a_created = client.post(
        "/api/cas-harness/audit/session", json=_valid_payload(), headers=headers_a
    ).json()
    audit_id = a_created["audit_id"]

    # No Authorization header at all.
    anon_list = client.get("/api/cas-harness/audit/sessions")
    assert anon_list.status_code == 200
    anon_ids = {s["audit_id"] for s in anon_list.json()["sessions"]}
    assert audit_id not in anon_ids
    assert anon_ids == set()

    anon_get = client.get(f"/api/cas-harness/audit/session/{audit_id}/status")
    assert anon_get.status_code == 404


def test_anonymous_callers_share_only_the_anonymous_bucket(client):
    # Two identity-less callers both land in the anonymous-owned bucket, so an
    # anonymous list returns anonymous-created sessions (own-only) but still
    # never an authenticated caller's session.
    headers_a = _headers_for("caller-a", "key-a")

    anon_created = client.post(
        "/api/cas-harness/audit/session", json=_valid_payload()
    ).json()
    auth_created = client.post(
        "/api/cas-harness/audit/session",
        json={**_valid_payload(), "prompt": "Authenticated-only scenario."},
        headers=headers_a,
    ).json()

    anon_list = client.get("/api/cas-harness/audit/sessions")
    assert anon_list.status_code == 200
    anon_ids = {s["audit_id"] for s in anon_list.json()["sessions"]}

    assert anon_created["audit_id"] in anon_ids
    assert auth_created["audit_id"] not in anon_ids


def test_audit_session_response_never_leaks_owner_identity(client):
    # The owner identity is an internal access-control field and must never
    # appear in the public audit-session response payload.
    headers_a = _headers_for("caller-a", "key-a")
    created = client.post(
        "/api/cas-harness/audit/session", json=_valid_payload(), headers=headers_a
    )
    assert created.status_code == 200
    body = created.json()
    assert "owner_sub" not in body
    assert "owner_api_key" not in body
    assert "caller-a" not in created.text
    assert "key-a" not in created.text
