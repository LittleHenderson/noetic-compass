from __future__ import annotations

from urllib.parse import quote

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    return TestClient(app)


def test_start_live_authorized_requires_typed_confirmation(monkeypatch):
    monkeypatch.setattr(route_module, "_live_timer_confirmation_required", lambda: True)
    monkeypatch.setattr(route_module, "use_in_process_workers_for_tests", lambda: True)
    monkeypatch.setattr(
        route_module,
        "start_runner",
        lambda interval_seconds, confirm=False: {
            "report_kind": "cas_forex_waste_runner",
            "status": "STARTED",
            "running": True,
            "interval_seconds": interval_seconds,
            "confirm": confirm,
        },
    )
    client = _client()

    boolean_only = client.post(
        "/api/forex/waste-loop-control/start?confirm=true",
        json={"interval_seconds": 5},
    )
    assert boolean_only.status_code == 200
    assert boolean_only.json()["status"] == "CONFIRM_REQUIRED"
    assert boolean_only.json()["need_confirmation"] == route_module.LIVE_WASTE_LOOP_CONFIRM_PHRASE
    assert boolean_only.json()["running"] is False

    phrase = quote(route_module.LIVE_WASTE_LOOP_CONFIRM_PHRASE)
    confirmed = client.post(
        f"/api/forex/waste-loop-control/start?confirm=true&confirm_phrase={phrase}",
        json={"interval_seconds": 5},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "STARTED"
    assert confirmed.json()["running"] is True
    assert confirmed.json()["confirm"] is True
