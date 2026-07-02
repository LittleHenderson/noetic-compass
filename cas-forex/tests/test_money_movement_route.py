"""Tests for the /money-movement route — HTTP face of the gated money engine.

With default config every money gate is NOT LICENSED, so each POST returns a
BLOCKED result surfacing the missing requirements and never moves money.
"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import money_movement as route_module
from api.routes.money_movement import VerifiedSweepPolicyUpdate


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/money-movement")
    return TestClient(app)


def test_gates_default_not_authorized():
    resp = _client().get("/api/forex/money-movement/gates")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["gates"]) == {"auto_deposit", "bank_card_movement", "payout_automation"}
    assert body["all_authorized"] is False
    # Each gate lists what is still required.
    assert body["gates"]["payout_automation"]["missing_requirements"]


def test_deposit_blocked_by_default_surfaces_missing_requirements():
    resp = _client().post("/api/forex/money-movement/deposit", json={"amount_usd": 500})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "BLOCKED"
    assert body["authorized"] is False
    assert body["missing_requirements"]
    assert body["provider_receipt"] is None  # provider never called


def test_payout_blocked_by_default():
    resp = _client().post(
        "/api/forex/money-movement/payout",
        json={"amount_usd": 200, "destination_id": "dest-x"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "BLOCKED"


def test_reinvest_split_bad_percentages_returns_422():
    resp = _client().post(
        "/api/forex/money-movement/reinvest-split",
        json={
            "realized_profit_usd": 100,
            "reinvest_pct": 50,
            "savings_pct": 40,
            "tax_reserve_pct": 5,  # sums to 95, not 100
        },
    )
    assert resp.status_code == 422


def test_deposit_rejects_non_positive_amount():
    resp = _client().post("/api/forex/money-movement/deposit", json={"amount_usd": 0})
    assert resp.status_code == 422  # pydantic gt=0


def test_authorized_payout_requires_confirm_then_settles(monkeypatch):
    # Authorize payout on the GLOBAL config (simulated provider -> no real money).
    from cas_forex import broker_reality, live_enable_control
    from cas_forex.config import config as gc

    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_enable_control, "apply_live_enable_overrides", lambda cfg: cfg)
    monkeypatch.setattr(gc, "owner_enable_payout_automation", True)
    monkeypatch.setattr(gc, "payment_provider", "simulated")
    monkeypatch.setattr(gc, "payment_api_key", "k")
    monkeypatch.setattr(gc, "payout_destination_id", "dest-1")
    monkeypatch.setattr(gc, "payout_destination_allowlisted", True)

    client = _client()
    # Without confirm -> second layer kicks in, nothing executes.
    pending = client.post(
        "/api/forex/money-movement/payout", json={"amount_usd": 100, "destination_id": "dest-1"}
    )
    assert pending.json()["status"] == "CONFIRM_REQUIRED"

    # With confirm -> the (simulated) payout settles to the allowlisted dest.
    settled = client.post(
        "/api/forex/money-movement/payout?confirm=true",
        json={"amount_usd": 100, "destination_id": "dest-1"},
    )
    assert settled.json()["status"] == "SETTLED"


def test_verified_profit_sweep_policy_update_invalidates_dependent_caches(monkeypatch):
    captured: dict[str, object] = {}

    class FakeSettings:
        def __init__(self):
            self.sweep_pct = 40.0
            self.tax_reserve_pct = 20.0
            self.min_sweep_usd = 25.0
            self.destination_id = "dest-1"
            self.allow_principal_sweep = False
            self.policy_id = "unit"

    class FakePolicyStore:
        def update(self, **changes):
            captured["changes"] = changes
            return FakeSettings()

        def load(self):
            return FakeSettings()

    class FakeAuditLog:
        def append(self, action, payload):
            captured["audit_action"] = action
            captured["audit_payload"] = payload
            return {"audit_id": "unit-audit"}

    def fake_invalidate_live_money_gate_caches(*keys: str):
        captured["invalidated"] = keys

    monkeypatch.setattr(route_module, "_policy_store", lambda: FakePolicyStore())
    monkeypatch.setattr(route_module, "_audit_log", lambda: FakeAuditLog())
    monkeypatch.setattr(route_module, "invalidate_live_money_gate_caches", fake_invalidate_live_money_gate_caches)

    body = VerifiedSweepPolicyUpdate(sweep_pct=40.0, destination_id="dest-1")
    packet = asyncio.run(route_module.post_verified_profit_sweep_policy(body))

    assert packet["report_kind"] == "cas_forex_verified_profit_sweep_policy"
    assert captured["changes"] == {"sweep_pct": 40.0, "destination_id": "dest-1"}
    assert captured["invalidated"] == ()
