from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import broker_reality as route_module
from cas_forex import broker_reality
from cas_forex.broker_profiles import selected_broker_profile


def _complete_patch():
    return {
        "broker_id": "hugosway",
        "broker_entity": "Owner-reviewed broker entity",
        "withdrawal_minimum": "Owner reviewed withdrawal minimum.",
        "withdrawal_timing": "Owner reviewed withdrawal timing.",
        "kyc_requirements": "Owner reviewed KYC requirements.",
        "withdrawal_fees": "Owner reviewed withdrawal fees.",
        "currency_conversion": "Owner reviewed currency conversion.",
        "automation_tos": "Owner reviewed automation terms.",
        "automation_allowed_by_owner_review": True,
        "source_urls": ["https://example.com/broker-terms"],
        "notes": "Owner reviewed current broker reality.",
        "withdrawal_minimum_reviewed": True,
        "withdrawal_timing_reviewed": True,
        "kyc_requirements_reviewed": True,
        "withdrawal_fees_reviewed": True,
        "currency_conversion_reviewed": True,
        "automation_tos_reviewed": True,
        "broker_entity_reviewed": True,
        "owner_accepts_broker_terms": True,
    }


def test_risenfx_profile_is_available_for_owner_selected_routing():
    profile = selected_broker_profile("RISENFX")

    assert profile is not None
    assert profile["display_name"] == "RisenFX"
    assert profile["website"] == "https://www.risenfx.com/"
    assert profile["configured_env_prefix"] == "CAS_FOREX_RISENFX_"
    assert "Risen-Trade" in profile["platform_notes"]


def test_broker_reality_draft_is_open(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "DEFAULT_REVIEW_PATH", tmp_path / "review.json")
    review = broker_reality.update_broker_reality_review(
        {"broker_id": "hugosway", "withdrawal_minimum": "unknown"},
        confirm_owner_accept=False,
    )

    assert review["owner_review_status"] == broker_reality.STATUS_OPEN
    assert review["accepted_for_live_and_payout"] is False
    assert "source_urls" in review["missing_requirements"]


def test_broker_reality_accept_requires_complete_owner_review(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "DEFAULT_REVIEW_PATH", tmp_path / "review.json")

    try:
        broker_reality.update_broker_reality_review({"broker_id": "hugosway"}, confirm_owner_accept=True)
    except broker_reality.BrokerRealityError as exc:
        assert "Cannot ACCEPT" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("incomplete broker reality review should not ACCEPT")


def test_broker_reality_accept_satisfies_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "DEFAULT_REVIEW_PATH", tmp_path / "review.json")
    monkeypatch.setattr(broker_reality, "DEFAULT_AUDIT_PATH", tmp_path / "audit.jsonl")

    review = broker_reality.update_broker_reality_review(_complete_patch(), confirm_owner_accept=True)

    assert review["owner_review_status"] == broker_reality.STATUS_ACCEPT
    assert review["accepted_for_live_and_payout"] is True
    assert broker_reality.is_broker_reality_accepted("hugosway") is True
    assert (tmp_path / "audit.jsonl").exists()


def test_broker_reality_route_accepts_complete_review(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "DEFAULT_REVIEW_PATH", tmp_path / "review.json")
    monkeypatch.setattr(broker_reality, "DEFAULT_AUDIT_PATH", tmp_path / "audit.jsonl")
    invalidated: list[tuple] = []
    monkeypatch.setattr(
        route_module,
        "invalidate_live_money_gate_caches",
        lambda *keys: invalidated.append(keys),
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/broker-reality")
    client = TestClient(app)

    response = client.post(
        "/api/forex/broker-reality/review?confirm_owner_accept=true",
        json=_complete_patch(),
    )

    assert response.status_code == 200
    assert response.json()["owner_review_status"] == broker_reality.STATUS_ACCEPT
    assert invalidated == [()]


def test_broker_reality_route_rejects_incomplete_accept(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "DEFAULT_REVIEW_PATH", tmp_path / "review.json")
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/broker-reality")
    client = TestClient(app)

    response = client.post(
        "/api/forex/broker-reality/review?confirm_owner_accept=true",
        json={"broker_id": "hugosway"},
    )

    assert response.status_code == 400
