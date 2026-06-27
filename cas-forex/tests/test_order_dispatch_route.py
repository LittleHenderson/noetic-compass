"""Tests for the /order-dispatch route — HTTP face of the gated dispatch loop."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import order_dispatch as route_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/order-dispatch")
    return TestClient(app)


def test_latest_returns_no_cycle_when_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(route_module, "DEFAULT_OUTPUT_DIR", tmp_path)
    resp = _client().get("/api/forex/order-dispatch/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_dispatch_cycle_yet"


def test_run_returns_gated_cycle_report(monkeypatch, tmp_path):
    # Redirect the artifact writer so the test does not touch the real evidence dir.
    monkeypatch.setattr(
        route_module,
        "write_agent_dispatch_cycle_report",
        lambda cycle, **kw: {"json": tmp_path / "report.json"},
    )
    resp = _client().post("/api/forex/order-dispatch/run")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_kind"] == "cas_forex_agent_dispatch_cycle"
    assert body["dispatch_report"]["report_kind"] == "cas_forex_order_dispatch"
    # Paper-first: live execution stays runtime-locked by default.
    assert body["dispatch_report"]["live_execution_runtime_locked"] is True
    assert "artifact_path" in body
