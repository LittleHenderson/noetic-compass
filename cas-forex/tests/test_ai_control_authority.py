from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import ai_control_authority as route_module
from cas_forex.ai_control_authority import AiControlAuthority


def test_authority_persists_owner_envelope_and_ai_controls(tmp_path):
    path = tmp_path / "authority.json"
    auth = AiControlAuthority(path)

    auth.owner_update(
        allowed_symbols=["GBP/USD"],
        allow_short=False,
        max_risk_pct_per_trade=1.0,
        edge_threshold_min=0.60,
        edge_threshold_max=0.80,
    )
    risk = auth.ai_adjust("max_risk_pct_per_trade", 3.5, reason="behind pace")
    edge = auth.ai_adjust("edge_threshold", 0.90, reason="testing owner clamp")
    symbols = auth.ai_adjust("symbols", ["EUR/USD", "GBP/USD"], reason="focus")

    assert risk["new"] == 1.0
    assert risk["owner_clamped"] is True
    assert edge["new"] == 0.80
    assert symbols["new"] == ["GBP/USD"]
    assert path.exists()

    reloaded = AiControlAuthority(path)
    snap = reloaded.snapshot()
    assert snap["owner_envelope"]["allowed_symbols"] == ["GBP/USD"]
    assert snap["owner_envelope"]["allow_short"] is False
    assert snap["control_surface"]["values"]["max_risk_pct_per_trade"] == 1.0
    assert snap["control_surface"]["values"]["edge_threshold"] == 0.80


def test_owner_cannot_disable_both_directions(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    try:
        auth.owner_update(allow_long=False, allow_short=False)
    except ValueError as exc:
        assert "At least one direction" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_authority_objective_matches_owner_goal(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(monthly_profit_target_usd=5000, daily_profit_floor_usd=250)
    objective = auth.objective()
    status = objective.pace_status(
        realized_month_to_date=750,
        trading_day_index=3,
        today_realized=100,
    )
    assert status["target_to_date"] == 750
    assert status["needed_today"] == 150
    assert status["on_pace"] is True


def _client(auth: AiControlAuthority, monkeypatch) -> TestClient:
    monkeypatch.setattr(route_module, "get_authority", lambda: auth)
    monkeypatch.setattr(route_module, "reset_authority", lambda: auth)
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/ai-control-authority")
    return TestClient(app)


def test_ai_control_authority_route_updates_owner_and_ai(tmp_path, monkeypatch):
    auth = AiControlAuthority(tmp_path / "authority.json")
    client = _client(auth, monkeypatch)

    body = client.post(
        "/api/forex/ai-control-authority/owner-update",
        json={"allowed_symbols": ["GBP/USD"], "max_compound_units": 2},
    ).json()
    assert body["owner_envelope"]["allowed_symbols"] == ["GBP/USD"]

    adjusted = client.post(
        "/api/forex/ai-control-authority/ai-adjust",
        json={"lever": "max_compound_units", "value": 7, "reason": "green governors"},
    ).json()
    assert adjusted["new"] == 2
    assert adjusted["owner_clamped"] is True

    state = client.get("/api/forex/ai-control-authority/state").json()
    assert state["control_surface"]["values"]["max_compound_units"] == 2
