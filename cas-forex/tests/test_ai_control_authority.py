from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
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
    risk = auth.ai_adjust("max_risk_pct_per_trade", 3.5, reason="paper pace lag with capped account impact")
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


def test_operator_timeframe_dial_is_persisted_and_owner_fenced(tmp_path):
    path = tmp_path / "authority.json"
    auth = AiControlAuthority(path)

    auth.owner_update(allowed_timeframes=["M1", "M5"])
    result = auth.ai_adjust(
        "timeframes",
        ["M1", "H1"],
        reason="prefer fresh micro-scalp evidence while keeping the owner timeframe fence",
    )

    assert result["new"] == ["M1"]
    assert result["owner_clamped"] is True
    reloaded = AiControlAuthority(path).snapshot()
    assert reloaded["owner_envelope"]["allowed_timeframes"] == ["M1", "M5"]
    assert reloaded["control_surface"]["values"]["timeframes"] == ["M1"]
    definition = reloaded["control_surface"]["dial_definitions"]["timeframes"]
    assert "M1/M5" in definition["operational_effect"]
    assert definition["runtime_path"].endswith("values.timeframes")


def test_authority_audit_records_owner_and_ai_changes(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")

    auth.owner_update(source="test.owner", allowed_symbols=["GBP/USD"], max_compound_units=2)
    auth.ai_adjust(
        "max_compound_units",
        7,
        reason="test clamp with explicit owner-envelope review",
        source="test.ai",
    )

    rows = auth.recent_audit()
    assert rows[0]["action"] == "AI_DIAL_ADJUST"
    assert rows[0]["source"] == "test.ai"
    assert rows[0]["request"]["requested"] == 7
    assert rows[0]["result"]["new"] == 2
    assert rows[0]["result"]["owner_clamped"] is True
    assert rows[0]["external_money_movement"] is False
    assert rows[1]["action"] == "OWNER_ENVELOPE_UPDATE"
    assert rows[1]["source"] == "test.owner"
    assert any(change["key"] == "allowed_symbols" for change in rows[1]["changes"])


def test_authority_audit_labels_tighten_and_loosen_posture(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")

    loosened = auth.ai_adjust(
        "min_directional_confidence",
        0.10,
        reason="form more paper hypotheses",
        source="test.ai_loosen",
    )
    assert loosened["audit"]["changes"][0]["posture"] == "loosen"

    tightened = auth.ai_adjust(
        "max_total_exposure_lots",
        0.50,
        reason="reduce concentration",
        source="test.ai_tighten",
    )
    assert tightened["audit"]["changes"][0]["posture"] == "tighten"

    owner = auth.owner_update(
        source="test.owner_tighten",
        allowed_symbols=["GBP/USD"],
        allow_short=False,
    )
    changes = {change["key"]: change for change in owner["latest_audit"]["changes"]}
    assert changes["allowed_symbols"]["posture"] == "tighten"
    assert changes["allow_short"]["posture"] == "tighten"


def test_authority_exposes_dial_impact_preview_and_anti_impulse(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")

    snap = auth.snapshot()
    definitions = snap["control_surface"]["dial_definitions"]
    assert definitions["max_risk_pct_per_trade"]["loosens_when"] == "higher"
    assert "pre-execution risk gate" in definitions["max_total_exposure_lots"]["enforced_by"]
    assert snap["control_surface"]["anti_impulse"]["recent_loosen_count"] == 0

    preview = auth.preview_ai_adjust("max_risk_pct_per_trade", 2.0)
    assert preview["ready"] is False
    assert preview["posture"] == "loosen"
    assert preview["anti_impulse"]["projected_loosen_count"] == 1
    assert preview["anti_impulse"]["cooldown_active"] is False
    assert preview["requires_cooldown_clear"] is False
    assert preview["journal_prompt_required"] is True
    assert preview["anti_impulse_journal"]["required"] is True
    assert preview["anti_impulse_journal"]["satisfied"] is False
    assert any("reason must be at least" in blocker for blocker in preview["blockers"])
    assert any("widens trading latitude" in effect for effect in preview["effects"])
    assert preview["binding"]["runtime_path"] == "ai_control_authority.control_surface.values.max_risk_pct_per_trade"
    assert preview["binding"]["owner_bound"] == {"min": 0.0, "max": 5.0}
    assert preview["contract_rows"][0]["field"] == "max_risk_pct_per_trade"
    assert preview["contract_rows"][0]["before"] == 0.5
    assert preview["contract_rows"][0]["after"] == 2.0

    ready_preview = auth.preview_ai_adjust(
        "max_risk_pct_per_trade",
        2.0,
        reason="paper-only test loosen with rollback condition",
    )
    assert ready_preview["ready"] is True
    assert ready_preview["anti_impulse_journal"]["satisfied"] is True

    adjusted = auth.ai_adjust(
        "max_risk_pct_per_trade",
        2.0,
        reason="paper-only test loosen with rollback condition",
        source="test.ai",
    )
    assert adjusted["posture"] == "loosen"
    assert adjusted["anti_impulse"]["recent_loosen_count"] == 1
    assert adjusted["anti_impulse_journal"]["satisfied"] is True


def test_ai_dial_loosening_cooldown_blocks_repeated_widening(monkeypatch, tmp_path):
    import cas_forex.ai_control_authority as authority_module

    clock = {"now": datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(authority_module, "utc_now", lambda: clock["now"])

    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.ai_adjust(
        "max_risk_pct_per_trade",
        2.0,
        reason="first loosen with rollback trigger and capped account impact",
        source="test.ai",
    )

    blocked_preview = auth.preview_ai_adjust(
        "max_total_exposure_lots",
        3.0,
        reason="second loosen too soon after the first widening change",
    )
    assert blocked_preview["posture"] == "loosen"
    assert blocked_preview["ready"] is False
    assert blocked_preview["requires_cooldown_clear"] is True
    assert blocked_preview["anti_impulse"]["cooldown_active"] is True
    assert blocked_preview["blockers"]

    with pytest.raises(ValueError) as exc:
        auth.ai_adjust(
            "max_total_exposure_lots",
            3.0,
            reason="second loosen too soon after the first widening change",
            source="test.ai",
        )

    assert "cooling down" in str(exc.value).lower()

    tighten_preview = auth.preview_ai_adjust("max_risk_pct_per_trade", 0.5)
    assert tighten_preview["posture"] == "tighten"
    assert tighten_preview["ready"] is True
    assert tighten_preview["requires_cooldown_clear"] is False

    clock["now"] = clock["now"] + timedelta(
        seconds=authority_module.AI_DIAL_LOOSEN_COOLDOWN_SECONDS + 1
    )
    clear_preview = auth.preview_ai_adjust(
        "max_total_exposure_lots",
        3.0,
        reason="cooldown cleared and exposure increase is still bounded by owner limits",
    )
    assert clear_preview["ready"] is True
    assert clear_preview["requires_cooldown_clear"] is False

    resumed = auth.ai_adjust(
        "max_total_exposure_lots",
        3.0,
        reason="cooldown cleared and exposure increase is still bounded by owner limits",
        source="test.ai",
    )
    assert resumed["posture"] == "loosen"
    assert resumed["anti_impulse"]["cooldown_active"] is True


def test_loosened_ai_dial_requires_anti_impulse_journal_reason(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")

    with pytest.raises(ValueError) as exc:
        auth.ai_adjust("max_risk_pct_per_trade", 2.0, reason="fomo", source="test.ai")

    assert "anti-impulse journal reason" in str(exc.value)
    assert auth.snapshot()["control_surface"]["values"]["max_risk_pct_per_trade"] != 2.0

    with pytest.raises(ValueError) as exc_no_reason:
        auth.ai_adjust(
            "max_risk_pct_per_trade",
            2.0,
            reason="AI operator: no reason given",
            source="test.ai",
        )

    assert "no reason was given" in str(exc_no_reason.value)


def test_owner_cannot_disable_both_directions(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    try:
        auth.owner_update(allow_long=False, allow_short=False)
    except ValueError as exc:
        assert "At least one direction" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_owner_envelope_clamps_high_amplification_dials(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(
        daily_loss_cap_usd_max=75.0,
        max_positions_per_symbol=2,
        max_total_exposure_lots=1.25,
        min_directional_confidence_min=0.20,
        paper_learning_trades=0,
    )

    loss = auth.ai_adjust("daily_loss_cap_usd", 999999, reason="malicious widen blocked by owner max")
    per_symbol = auth.ai_adjust("max_positions_per_symbol", 50, reason="overstack blocked by owner cap")
    total_lots = auth.ai_adjust("max_total_exposure_lots", 100, reason="overexposure blocked by owner cap")
    confidence = auth.ai_adjust("min_directional_confidence", 0.0, reason="fomo test blocked by owner minimum")
    learning = auth.ai_adjust("paper_learning_trades", 1, reason="force learning trades blocked by owner")

    assert loss["new"] == 75.0
    assert per_symbol["new"] == 2
    assert total_lots["new"] == 1.25
    assert confidence["new"] == 0.20
    assert learning["new"] == 0
    assert all(
        item["owner_clamped"]
        for item in (loss, per_symbol, total_lots, confidence, learning)
    )


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

    preview = client.post(
        "/api/forex/ai-control-authority/preview",
        json={
            "lever": "max_risk_pct_per_trade",
            "value": 1.25,
            "reason": "bounded paper widen with rollback condition",
        },
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["ready"] is True
    assert preview_body["binding"]["runtime_path"] == "ai_control_authority.control_surface.values.max_risk_pct_per_trade"
    assert preview_body["contract_rows"][0]["after"] == 1.25

    body = client.post(
        "/api/forex/ai-control-authority/owner-update",
        json={"allowed_symbols": ["GBP/USD"], "max_compound_units": 2},
    ).json()
    assert body["owner_envelope"]["allowed_symbols"] == ["GBP/USD"]

    adjusted = client.post(
        "/api/forex/ai-control-authority/ai-adjust",
        json={"lever": "max_compound_units", "value": 7, "reason": "green governors with owner cap review"},
    ).json()
    assert adjusted["new"] == 2
    assert adjusted["owner_clamped"] is True

    state = client.get("/api/forex/ai-control-authority/state").json()
    assert state["control_surface"]["values"]["max_compound_units"] == 2

    audit = client.get("/api/forex/ai-control-authority/audit").json()
    assert audit["report_kind"] == "cas_forex_ai_control_authority_audit"


def test_ai_control_authority_route_blocks_loosening_during_cooldown(tmp_path, monkeypatch):
    import cas_forex.ai_control_authority as authority_module

    clock = {"now": datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(authority_module, "utc_now", lambda: clock["now"])

    auth = AiControlAuthority(tmp_path / "authority.json")
    client = _client(auth, monkeypatch)

    first = client.post(
        "/api/forex/ai-control-authority/ai-adjust",
        json={
            "lever": "max_risk_pct_per_trade",
            "value": 2.0,
            "reason": "first loosen with rollback trigger and bounded account impact",
        },
    )
    assert first.status_code == 200

    blocked = client.post(
        "/api/forex/ai-control-authority/ai-adjust",
        json={
            "lever": "max_total_exposure_lots",
            "value": 3.0,
            "reason": "second loosen too soon after the first widening change",
        },
    )
    assert blocked.status_code == 422
    assert "cooling down" in blocked.json()["detail"].lower()
    audit = client.get("/api/forex/ai-control-authority/audit").json()
    assert audit["rows"][0]["source"] == "api.ai_control_authority.ai_adjust"
