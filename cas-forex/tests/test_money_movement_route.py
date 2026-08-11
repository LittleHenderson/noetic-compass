"""Tests for the /money-movement route — HTTP face of the gated money engine.

With default config every money gate is NOT LICENSED, so each POST returns a
BLOCKED result surfacing the missing requirements and never moves money.
"""

from __future__ import annotations

import asyncio
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import money_movement as route_module
from api.routes.money_movement import VerifiedSweepPolicyUpdate
from cas_forex.money_movement import MovementEngine


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/money-movement")
    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_attempt_store(tmp_path, monkeypatch):
    monkeypatch.setattr(route_module, "DEFAULT_ATTEMPT_PATH", tmp_path / "attempts.json")
    monkeypatch.setattr(
        route_module,
        "DEFAULT_PAYOUT_RECOVERY_AUDIT_PATH",
        tmp_path / "attempts-audit.jsonl",
    )


def test_gates_default_not_authorized():
    resp = _client().get("/api/forex/money-movement/gates")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["gates"]) == {"auto_deposit", "bank_card_movement", "payout_automation"}
    assert body["all_authorized"] is False
    assert body["payment_provider_runtime"]["status"] == "NOT_CONFIGURED"
    assert body["real_money_provider_ready"] is False
    assert body["runtime_scaffolded"] is True
    assert "blocked until a supported broker funding rail is selected" in body["detail"].lower()
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
    assert pending.json()["need_confirmation"] == route_module.MONEY_MOVEMENT_CONFIRM_PHRASE

    # Boolean confirmation alone is not enough for authorized money movement.
    still_pending = client.post(
        "/api/forex/money-movement/payout?confirm=true",
        json={"amount_usd": 100, "destination_id": "dest-1"},
    )
    assert still_pending.json()["status"] == "CONFIRM_REQUIRED"

    # With confirm + typed phrase -> the (simulated) payout settles to the allowlisted dest.
    phrase = quote(route_module.MONEY_MOVEMENT_CONFIRM_PHRASE)
    settled = client.post(
        f"/api/forex/money-movement/payout?confirm=true&confirm_phrase={phrase}",
        json={"amount_usd": 100, "destination_id": "dest-1"},
    )
    assert settled.json()["status"] == "SETTLED"


def test_real_provider_manual_retry_requires_caller_idempotency_key(monkeypatch):
    class UntouchedRealProvider:
        name = "unit-real"
        is_real = True

        def deposit(self, *args, **kwargs):
            raise AssertionError("provider must not be touched")

        def withdraw(self, *args, **kwargs):
            raise AssertionError("provider must not be touched")

    monkeypatch.setattr(
        route_module,
        "_engine",
        lambda: MovementEngine(provider=UntouchedRealProvider()),
    )

    result = route_module._manual_movement_dispatch(
        kind="payout",
        amount_usd=100.0,
        destination_id="dest-1",
    )

    assert result["status"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert result["provider_touched"] is False


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
