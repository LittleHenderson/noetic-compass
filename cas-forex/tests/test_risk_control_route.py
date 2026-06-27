"""Tests for the /risk-control route — owner sets any cap, or removes it."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import risk_control as route_module
from cas_forex.risk_control import clear_risk_control_overrides


@pytest.fixture(autouse=True)
def _clear():
    clear_risk_control_overrides()
    yield
    clear_risk_control_overrides()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/risk-control")
    return TestClient(app)


def test_state_reports_caps():
    resp = _client().get("/api/forex/risk-control/state")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_risk_control"
    assert "max_concurrent_trades" in body
    assert "unlimited" in body


def test_set_concurrent_and_loss_cap():
    body = _client().post(
        "/api/forex/risk-control/update",
        json={"max_concurrent_trades": 50, "max_loss_cap_usd": 2500},
    ).json()
    assert body["max_concurrent_trades"] == 50
    assert body["max_loss_cap_usd"] == 2500


def test_unlimited_via_null():
    body = _client().post(
        "/api/forex/risk-control/update",
        json={"max_concurrent_trades": None, "max_total_exposure_lots": None},
    ).json()
    assert body["max_concurrent_trades"] is None
    assert body["unlimited"]["concurrent_trades"] is True
    assert body["unlimited"]["total_exposure_lots"] is True


def test_negative_rejected_422():
    resp = _client().post("/api/forex/risk-control/update", json={"max_loss_cap_usd": -10})
    assert resp.status_code == 422


def test_reset_reverts():
    client = _client()
    client.post("/api/forex/risk-control/update", json={"max_concurrent_trades": 99})
    body = client.post("/api/forex/risk-control/reset").json()
    # Back to config default (5 from the live ForexConfig, unless env overrides it).
    assert body["max_concurrent_trades"] != 99
