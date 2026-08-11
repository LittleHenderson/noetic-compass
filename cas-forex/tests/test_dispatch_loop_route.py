from __future__ import annotations

from urllib.parse import quote

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import dispatch_loop as route_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/dispatch-loop")
    return TestClient(app)


def test_status_refresh_does_not_wait_on_global_serial_cache_lane(monkeypatch):
    captured: dict[str, object] = {}

    def fake_cache_first_payload(key, **kwargs):
        captured["key"] = key
        captured.update(kwargs)
        return {"status": "RUNNING", "running": True}

    monkeypatch.setattr(route_module, "cache_first_payload", fake_cache_first_payload)

    response = _client().get("/api/forex/dispatch-loop/status")

    assert response.status_code == 200
    assert response.json()["status"] == "RUNNING"
    assert captured["key"] == "dispatch_loop_status"
    assert captured["serialize_refresh"] is False


def test_status_cache_fallback_uses_truthful_fast_scheduler_shell(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "loop_status_fast",
        lambda: {
            "report_kind": "cas_forex_dispatch_loop",
            "status_source": "FAST_IN_MEMORY_SHELL",
            "status": "RUNNING",
            "running": True,
            "execution_lane": "PAPER",
        },
    )

    status = route_module._dispatch_status_fast()

    assert status["status_source"] == "FAST_IN_MEMORY_SHELL"
    assert status["status"] == "RUNNING"
    assert status["running"] is True


def test_start_live_authorized_requires_typed_confirmation(monkeypatch):
    monkeypatch.setattr(route_module, "requested_mode", lambda: "LIVE")
    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda capability: capability == "live_trading")
    monkeypatch.setattr(
        route_module,
        "start_loop",
        lambda interval_seconds, symbols=None, sessions=None, position_scope=None, **kwargs: {
            "report_kind": "cas_forex_dispatch_loop",
            "status": "STARTED",
            "running": True,
            "interval_seconds": interval_seconds,
            "symbols": symbols or [],
            "sessions": sessions or [],
            "position_scope": position_scope,
        },
    )
    client = _client()

    boolean_only = client.post(
        "/api/forex/dispatch-loop/start?confirm=true",
        json={
            "interval_seconds": 60,
            "symbols": ["EUR/USD"],
            "sessions": ["London"],
            "position_scope": "ALL_ACCOUNT",
        },
    )
    assert boolean_only.status_code == 200
    assert boolean_only.json()["status"] == "CONFIRM_REQUIRED"
    assert boolean_only.json()["need_confirmation"] == route_module.LIVE_DISPATCH_LOOP_CONFIRM_PHRASE
    assert boolean_only.json()["running"] is False

    phrase = quote(route_module.LIVE_DISPATCH_LOOP_CONFIRM_PHRASE)
    confirmed = client.post(
        f"/api/forex/dispatch-loop/start?confirm=true&confirm_phrase={phrase}",
        json={
            "interval_seconds": 60,
            "symbols": ["EUR/USD"],
            "sessions": ["London"],
            "position_scope": "ALL_ACCOUNT",
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "STARTED"
    assert confirmed.json()["running"] is True
    assert confirmed.json()["position_scope"] == "ALL_ACCOUNT"


def test_position_scope_rejects_unknown_values(monkeypatch):
    monkeypatch.setattr(route_module, "requested_mode", lambda: "PAPER")
    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda _capability: False)
    client = _client()

    response = client.post(
        "/api/forex/dispatch-loop/start",
        json={"interval_seconds": 60, "position_scope": "IMPLICIT_EVERYTHING"},
    )

    assert response.status_code == 422


def test_start_live_requested_but_not_yet_authorized_still_requires_confirmation(monkeypatch):
    monkeypatch.setattr(route_module, "requested_mode", lambda: "LIVE")
    monkeypatch.setattr(route_module.runtime_gates, "is_authorized", lambda _capability: False)
    monkeypatch.setattr(
        route_module,
        "start_loop",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not start without phrase")),
    )
    client = _client()

    response = client.post(
        "/api/forex/dispatch-loop/start",
        json={"interval_seconds": 60, "symbols": ["EUR/USD"], "sessions": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CONFIRM_REQUIRED"
    assert body["requested_mode"] == "LIVE"
    assert body["live_trading_authorized"] is False
    assert body["need_confirmation"] == route_module.LIVE_DISPATCH_LOOP_CONFIRM_PHRASE
