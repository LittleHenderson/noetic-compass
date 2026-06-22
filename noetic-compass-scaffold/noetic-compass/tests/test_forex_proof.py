"""Read-only CAS Forex proof endpoints.

Verifies the endpoints serve the real day-1 evidence, keep the NOT LICENSED
boundary, and expose no write surface (GET-only; non-GET stays behind auth).
"""

from __future__ import annotations

import pytest

from api.routes import forex_proof


def test_forex_index_is_public_and_read_only(client):
    r = client.get("/forex")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "READ_ONLY"
    assert body["deployment_status"] == "NOT LICENSED"
    assert body["broker_accept_status"] == "NOT LICENSED"
    assert body["payment_transfer_status"] == "NOT LICENSED"
    assert "/forex/proof/paper" in body["endpoints"]


def test_paper_proof_endpoint_serves_real_day1_evidence(client):
    if not forex_proof.EVIDENCE_DIR.is_dir():
        pytest.skip("CAS Forex evidence dir not present in this checkout")
    r = client.get("/forex/proof/paper")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deployment_status"] == "NOT LICENSED"
    report = body["report"]
    assert report["completed_trading_days"] == 1
    assert report["required_trading_days"] == 30
    assert report["live_mode_used"] is False
    assert report["chain_verified"] is True


def test_ui_readiness_and_decision_endpoints(client):
    if not forex_proof.EVIDENCE_DIR.is_dir():
        pytest.skip("CAS Forex evidence dir not present in this checkout")

    r = client.get("/forex/proof/ui-readiness")
    assert r.status_code == 200, r.text
    assert r.json()["readiness_status"] == "NOT_READY_FOR_UI_UX"
    assert r.json()["complete_bundle_days"] == 1

    r = client.get("/forex/proof/decision")
    assert r.status_code == 200, r.text
    assert r.json()["latest_decision"]["route_action"] == "ROUTE_PAPER_SIGNAL"


def test_all_six_proof_endpoints_resolve(client):
    if not forex_proof.EVIDENCE_DIR.is_dir():
        pytest.skip("CAS Forex evidence dir not present in this checkout")
    for suffix in ("paper", "ui-readiness", "schedule", "decision", "risk", "bundle"):
        r = client.get(f"/forex/proof/{suffix}")
        assert r.status_code == 200, f"{suffix}: {r.text}"


def test_proof_endpoints_have_no_write_surface(client):
    # POST is not a GET, so the public-GET exemption does not apply and the
    # request is rejected (auth required / method not allowed). Either way there
    # is no write path.
    r = client.post("/forex/proof/paper", json={})
    assert r.status_code in (401, 404, 405), r.text
    assert r.status_code != 200


def test_missing_evidence_returns_404(client, monkeypatch, tmp_path):
    # Point at an empty dir: files are absent, so reads 404 (cockpit then falls
    # back to bundled fixtures) rather than 500 or a stack trace.
    monkeypatch.setattr(forex_proof, "EVIDENCE_DIR", tmp_path)
    r = client.get("/forex/proof/paper")
    assert r.status_code == 404, r.text
