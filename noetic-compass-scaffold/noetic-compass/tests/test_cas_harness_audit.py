from __future__ import annotations

from typing import get_args

from api.routes.cas_harness_audit import Verdict


def _valid_payload() -> dict:
    return {
        "model_id": "openai:gpt-4.1-mini",
        "audit_mode": "BALANCED",
        "prompt": "Assess whether this answer should be accepted or suppressed.",
        "selected_modules": ["cognitive_bias", "provenance_trace"],
        "license_key": "placeholder-license",
    }


def test_audit_session_route_registered(client):
    openapi = client.get("/openapi.json").json()

    assert "/api/cas-harness/audit/session" in openapi["paths"]
    assert "/api/cas-harness/audit/session/{audit_id}/status" in openapi["paths"]


def test_create_audit_session_returns_honest_pending_scaffold(client, auth_headers):
    resp = client.post(
        "/api/cas-harness/audit/session",
        json=_valid_payload(),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_id"].startswith("cas-audit-")
    assert body["status"] == "SCAFFOLD_PENDING_RUNNER"
    assert body["model_status"] == "NOT_CONNECTED_MOCK"
    assert body["verdict"] is None
    assert body["confidence"] is None
    assert body["evidence_packet_trace_id"] is None
    assert body["atlas_deep_link"] is None
    assert any("scaffold/mock" in chip["value"] for chip in body["provenance_chips"])


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
    assert resp.json()["status"] == "SCAFFOLD_PENDING_RUNNER"


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


def test_status_route_returns_deterministic_scaffold_state(client, auth_headers):
    audit_id = "cas-audit-fixture"

    first = client.get(
        f"/api/cas-harness/audit/session/{audit_id}/status",
        headers=auth_headers,
    )
    second = client.get(
        f"/api/cas-harness/audit/session/{audit_id}/status",
        headers=auth_headers,
    )

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["audit_id"] == audit_id
    assert first.json()["verdict"] is None
    assert first.json()["confidence"] is None
