"""Tests for the /broker-control route — choose platform + loosen paper limits."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import broker_control as route_module
from cas_forex.broker_control import clear_broker_control_overrides


@pytest.fixture(autouse=True)
def _clear_overrides():
    clear_broker_control_overrides()
    yield
    clear_broker_control_overrides()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/broker-control")
    return TestClient(app)


def test_get_state_returns_control():
    resp = _client().get("/api/forex/broker-control/state")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_broker_control"
    assert "auto" in body["platform_options"]


def test_update_platform_and_loosen():
    resp = _client().post(
        "/api/forex/broker-control/update",
        json={"platform": "mt4", "max_spread_pips": 50, "min_stop_distance_pips": 0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["platform"] == "mt4"
    assert body["tolerances"]["max_spread_pips"] == 50
    assert body["loosened"] is True


def test_update_invalid_platform_returns_422():
    resp = _client().post("/api/forex/broker-control/update", json={"platform": "bogus"})
    assert resp.status_code == 422


def test_reset_reverts_to_config_default():
    client = _client()
    client.post("/api/forex/broker-control/update", json={"platform": "mt4"})
    resp = client.post("/api/forex/broker-control/reset")
    assert resp.status_code == 200
    assert resp.json()["platform"] == "auto"
