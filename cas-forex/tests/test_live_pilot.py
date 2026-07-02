from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import live_pilot as route_module
from cas_forex import live_pilot


def _complete_patch():
    return {
        "allowed_symbols": ["EUR/USD", "NAS100"],
        "max_trade_lots": 0.01,
        "max_open_live_lots": 0.02,
        "max_live_trade_count": 2,
        "max_daily_loss_usd": 25.0,
        "max_total_loss_usd": 50.0,
        "max_pilot_days": 5,
        "notes": "Owner accepts first live trades only as a tiny pilot.",
        "owner_understands_real_money_risk": True,
        "owner_confirms_small_amounts_only": True,
        "owner_confirms_no_scaling_without_review": True,
        "owner_confirms_emergency_stop_ready": True,
    }


def test_live_pilot_default_is_open_and_not_live_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(live_pilot, "DEFAULT_POLICY_PATH", tmp_path / "pilot.json")
    policy = live_pilot.build_live_pilot_policy()

    assert policy["owner_pilot_status"] == live_pilot.STATUS_OPEN
    assert policy["ready_for_next_live_order"] is False
    assert "allowed_symbols" in policy["missing_requirements"]


def test_live_pilot_accept_requires_complete_owner_limits(tmp_path, monkeypatch):
    monkeypatch.setattr(live_pilot, "DEFAULT_POLICY_PATH", tmp_path / "pilot.json")

    try:
        live_pilot.update_live_pilot_policy({}, confirm_owner_accept=True)
    except live_pilot.LivePilotError as exc:
        assert "Cannot ACCEPT" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("incomplete live pilot policy should not ACCEPT")


def test_live_pilot_accept_enforces_intent_and_capacity(tmp_path, monkeypatch):
    monkeypatch.setattr(live_pilot, "DEFAULT_POLICY_PATH", tmp_path / "pilot.json")
    monkeypatch.setattr(live_pilot, "DEFAULT_AUDIT_PATH", tmp_path / "audit.jsonl")

    policy = live_pilot.update_live_pilot_policy(_complete_patch(), confirm_owner_accept=True)
    assert policy["owner_pilot_status"] == live_pilot.STATUS_ACCEPT
    assert policy["ready_for_next_live_order"] is True
    assert live_pilot.is_live_pilot_available_for_live() is True

    live_pilot.require_live_pilot_intent({"symbol": "EUR/USD", "lots": 0.01})

    try:
        live_pilot.require_live_pilot_intent({"symbol": "EUR/USD", "lots": 0.03})
    except live_pilot.LivePilotError as exc:
        assert "exceeds pilot max_trade_lots" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("oversized pilot order should be blocked")

    live_pilot.record_live_pilot_dispatch(
        order_id="ord-1",
        symbol="EUR/USD",
        lots=0.01,
        outcome_status="EXECUTED",
    )
    exhausted = live_pilot.record_live_pilot_dispatch(
        order_id="ord-2",
        symbol="EUR/USD",
        lots=0.01,
        outcome_status="EXECUTED",
    )
    assert exhausted["pilot_capacity_remaining"] == 0
    assert exhausted["ready_for_next_live_order"] is False
    assert "pilot live trade count reached" in exhausted["missing_requirements"]
    assert (tmp_path / "audit.jsonl").exists()


def test_live_pilot_route_accepts_complete_policy(tmp_path, monkeypatch):
    monkeypatch.setattr(live_pilot, "DEFAULT_POLICY_PATH", tmp_path / "pilot.json")
    monkeypatch.setattr(live_pilot, "DEFAULT_AUDIT_PATH", tmp_path / "audit.jsonl")
    invalidated: list[tuple] = []
    monkeypatch.setattr(
        route_module,
        "invalidate_live_money_gate_caches",
        lambda *keys: invalidated.append(keys),
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-pilot")
    client = TestClient(app)

    response = client.post(
        "/api/forex/live-pilot/policy?confirm_owner_accept=true",
        json=_complete_patch(),
    )

    assert response.status_code == 200
    assert response.json()["owner_pilot_status"] == live_pilot.STATUS_ACCEPT
    assert invalidated == [()]


def test_live_pilot_route_rejects_incomplete_accept(tmp_path, monkeypatch):
    monkeypatch.setattr(live_pilot, "DEFAULT_POLICY_PATH", tmp_path / "pilot.json")
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/live-pilot")
    client = TestClient(app)

    response = client.post(
        "/api/forex/live-pilot/policy?confirm_owner_accept=true",
        json={"allowed_symbols": ["EUR/USD"]},
    )

    assert response.status_code == 400
