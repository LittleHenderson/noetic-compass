from __future__ import annotations

from typing import get_args

from api.routes.cas_harness_audit import Verdict
from api.services.cas_harness_audit_sessions import reset_audit_sessions_for_tests


def setup_function() -> None:
    reset_audit_sessions_for_tests()


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


def test_audit_session_route_registered(client):
    openapi = client.get("/openapi.json").json()

    assert "/api/cas-harness/audit/session" in openapi["paths"]
    assert "/api/cas-harness/audit/session/{audit_id}/status" in openapi["paths"]
    assert "/api/cas-harness/audit/session/{audit_id}/run" in openapi["paths"]
    assert "/api/cas-harness/audit/sessions" in openapi["paths"]


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


def test_run_route_accepts_only_when_complete_packet_has_explicit_verifier_decision(
    client,
    auth_headers,
    monkeypatch,
):
    packet = _complete_stage21_packet(action="allow", accepted=True)
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.build_packet_for_trace",
        lambda trace_id: _PacketStub(packet),
    )
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
    assert set(chips.values()) == {"present"}
    assert "explicit verifier decision" in body["lifecycle"][-1]["message"]


def test_run_route_suppresses_only_when_complete_packet_has_explicit_rejection(
    client,
    auth_headers,
    monkeypatch,
):
    packet = _complete_stage21_packet(action="suppress", accepted=False)
    monkeypatch.setattr(
        "api.routes.cas_harness_audit.build_packet_for_trace",
        lambda trace_id: _PacketStub(packet),
    )
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
