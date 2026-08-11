from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import auto_halt as route_module
from cas_forex import auto_halt


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/auto-halt")
    return TestClient(app)


def test_auto_halt_status_route_returns_report(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "auto_halt_status",
        lambda persist=True: {
            "report_kind": "cas_forex_auto_halt",
            "status": auto_halt.STATUS_CLEAR,
            "halt_active": False,
            "persist": persist,
        },
    )

    response = _client().get("/api/forex/auto-halt/status")

    assert response.status_code == 200
    assert response.json()["report_kind"] == "cas_forex_auto_halt"
    assert response.json()["persist"] is True


def test_auto_halt_clear_requires_confirm_then_clears(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")
    monkeypatch.setattr(
        route_module,
        "auto_halt_status",
        lambda persist=True: {
            "report_kind": "cas_forex_auto_halt",
            "status": auto_halt.STATUS_CLEAR,
            "halt_active": False,
        },
    )
    auto_halt.activate_auto_halt(["TEST"], [{"check_id": "TEST"}])
    client = _client()

    missing_confirm = client.post("/api/forex/auto-halt/clear", json={"reason": "owner checked"})
    assert missing_confirm.status_code == 400

    cleared = client.post("/api/forex/auto-halt/clear?confirm_clear=true", json={"reason": "owner checked"})
    assert cleared.status_code == 200
    assert cleared.json()["clear_state"]["active"] is False
    assert auto_halt.is_auto_halt_active() is False


def test_emergency_stop_latches_auto_halt(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_halt, "DEFAULT_AUTO_HALT_STATE_PATH", tmp_path / "auto-halt.json")
    monkeypatch.setattr(
        route_module,
        "auto_halt_status",
        lambda persist=True: {
            "report_kind": "cas_forex_auto_halt",
            "status": auto_halt.STATUS_ACTIVE if auto_halt.is_auto_halt_active() else auto_halt.STATUS_CLEAR,
            "halt_active": auto_halt.is_auto_halt_active(),
        },
    )

    response = _client().post(
        "/api/forex/auto-halt/emergency-stop",
        json={"reason": "owner hit stop"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["emergency_stop_applied"] is True
    assert payload["halt_active"] is True
    assert payload["emergency_stop_state"]["active"] is True
    assert payload["emergency_stop_state"]["reasons"] == ["MANUAL_EMERGENCY_STOP"]
    assert auto_halt.is_auto_halt_active() is True
