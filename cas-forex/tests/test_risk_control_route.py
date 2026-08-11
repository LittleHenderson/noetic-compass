"""Tests for the /risk-control route — owner sets any cap, or removes it."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import risk_control as route_module
from cas_forex import live_enable_control
from cas_forex.risk_control import RISK_LOOSEN_CONFIRM_PHRASE
from cas_forex.risk_control import DEFAULT_OVERRIDE_PATH
from cas_forex.risk_control import clear_risk_control_overrides
from cas_forex.risk_control import set_risk_control_audit_path_for_tests
from cas_forex.risk_control import set_risk_control_override_store_for_tests


@pytest.fixture(autouse=True)
def _clear(tmp_path):
    set_risk_control_override_store_for_tests(tmp_path / "risk-control-overrides.json")
    set_risk_control_audit_path_for_tests(tmp_path / "risk-control-audit.jsonl")
    clear_risk_control_overrides()
    yield
    clear_risk_control_overrides()
    set_risk_control_audit_path_for_tests(None)
    set_risk_control_override_store_for_tests(DEFAULT_OVERRIDE_PATH)


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
    assert body["anti_impulse_status"]["journal_required_on_loosen"] is True
    assert "cooldown" in body["anti_impulse_status"]
    assert body["override_persistence"]["status"] == "NO_EXPLICIT_OWNER_OVERRIDES"
    assert body["effective_dispatch_caps"]["precedence"].startswith("explicit owner")


def test_set_concurrent_and_loss_cap():
    client = _client()
    body = client.post(
        "/api/forex/risk-control/update",
        json={
            "max_concurrent_trades": 50,
            "max_loss_cap_usd": 2500,
            "journal_reason": "paper concurrency expansion test with rollback",
        },
    ).json()
    assert body["max_concurrent_trades"] == 50
    assert body["max_loss_cap_usd"] == 2500

    audit = client.get("/api/forex/risk-control/audit").json()
    assert audit["report_kind"] == "cas_forex_risk_control_audit"
    assert audit["rows"][0]["action"] == "RISK_CONTROL_UPDATE"
    assert audit["rows"][0]["source"] == "api.risk_control.update"
    changed = {row["key"]: row for row in audit["rows"][0]["changes"]}
    assert changed["max_concurrent_trades"]["after"] == 50
    assert changed["max_loss_cap_usd"]["after"] == 2500


def test_unlimited_via_null():
    body = _client().post(
        "/api/forex/risk-control/update",
        json={
            "max_concurrent_trades": None,
            "max_total_exposure_lots": None,
            "journal_reason": "paper loosening test with rollback on drawdown",
        },
    ).json()
    assert body["max_concurrent_trades"] is None
    assert body["unlimited"]["concurrent_trades"] is True
    assert body["unlimited"]["total_exposure_lots"] is True


def test_preview_reports_before_after_without_applying():
    client = _client()
    client.post("/api/forex/risk-control/update", json={"max_total_exposure_lots": 0.5})

    preview = client.post(
        "/api/forex/risk-control/preview",
        json={"max_total_exposure_lots": 2.0},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["report_kind"] == "cas_forex_risk_control_update_assessment"
    assert body["changes"][0]["key"] == "max_total_exposure_lots"
    assert body["changes"][0]["before"] == 0.5
    assert body["changes"][0]["after"] == 2.0
    assert body["changes"][0]["posture"] == "loosen"
    assert body["requires_journal_reason"] is True
    assert body["journal"]["satisfied"] is False

    state = client.get("/api/forex/risk-control/state").json()
    assert state["max_total_exposure_lots"] == 0.5


def test_preview_reset_reports_before_after_without_applying():
    client = _client()
    client.post("/api/forex/risk-control/update", json={"max_total_exposure_lots": 0.25})

    preview = client.post("/api/forex/risk-control/preview-reset", json={})
    assert preview.status_code == 200
    body = preview.json()
    assert body["report_kind"] == "cas_forex_risk_control_reset_assessment"
    exposure_change = next(change for change in body["changes"] if change["key"] == "max_total_exposure_lots")
    assert exposure_change["before"] == 0.25
    assert exposure_change["after"] == 0.5
    assert exposure_change["posture"] == "loosen"
    assert body["requires_journal_reason"] is True
    assert body["journal"]["satisfied"] is False

    state = client.get("/api/forex/risk-control/state").json()
    assert state["max_total_exposure_lots"] == 0.25


def test_risk_loosen_update_requires_journal_reason():
    client = _client()
    client.post("/api/forex/risk-control/update", json={"max_total_exposure_lots": 0.5})

    blocked = client.post("/api/forex/risk-control/update", json={"max_total_exposure_lots": None})

    assert blocked.status_code == 409
    detail = blocked.json()["detail"]
    assert detail["status"] == "JOURNAL_REQUIRED"
    assert detail["journal"]["required"] is True
    assert detail["journal"]["satisfied"] is False


def test_negative_rejected_422():
    resp = _client().post("/api/forex/risk-control/update", json={"max_loss_cap_usd": -10})
    assert resp.status_code == 422


def test_persistence_failure_returns_503_without_claiming_apply(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "set_risk_control_overrides",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    response = _client().post(
        "/api/forex/risk-control/update",
        json={"max_drawdown_pct": 4.0},
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "RISK_OVERRIDE_PERSISTENCE_FAILED"
    assert detail["money_impact"] == "No new owner risk override became active."


def test_reset_reverts():
    client = _client()
    client.post(
        "/api/forex/risk-control/update",
        json={
            "max_concurrent_trades": 20,
            "journal_reason": "temporary paper concurrency expansion before resetting to default",
        },
    )
    body = client.post("/api/forex/risk-control/reset", json={}).json()
    # Back to config default (5 from the live ForexConfig, unless env overrides it).
    assert body["max_concurrent_trades"] != 20
    audit = client.get("/api/forex/risk-control/audit").json()
    assert audit["rows"][0]["action"] == "RISK_CONTROL_RESET"


def test_live_armed_loosening_requires_confirmation(tmp_path):
    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        client = _client()
        client.post("/api/forex/risk-control/update", json={"max_total_exposure_lots": 0.5})

        blocked = client.post(
            "/api/forex/risk-control/update",
            json={
                "max_total_exposure_lots": None,
                "journal_reason": "live exposure cap removal test with rollback",
            },
        )
        assert blocked.status_code == 409
        detail = blocked.json()["detail"]
        assert detail["status"] == "CONFIRM_REQUIRED"
        assert detail["need_confirmation"] == RISK_LOOSEN_CONFIRM_PHRASE

        applied = client.post(
            "/api/forex/risk-control/update",
            json={
                "max_total_exposure_lots": None,
                "confirm": RISK_LOOSEN_CONFIRM_PHRASE,
                "journal_reason": "live exposure cap removal test with rollback",
            },
        )
        assert applied.status_code == 200
        assert applied.json()["max_total_exposure_lots"] is None
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)


def test_live_armed_repeated_loosening_hits_cooldown(tmp_path):
    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        client = _client()
        client.post("/api/forex/risk-control/update", json={"max_total_exposure_lots": 0.5})
        first = client.post(
            "/api/forex/risk-control/update",
            json={
                "max_total_exposure_lots": None,
                "confirm": RISK_LOOSEN_CONFIRM_PHRASE,
                "journal_reason": "first live loosening cooldown seed",
            },
        )
        assert first.status_code == 200

        preview = client.post(
            "/api/forex/risk-control/preview",
            json={
                "max_concurrent_trades": None,
                "journal_reason": "second live loosening should hit cooldown",
            },
        ).json()
        assert preview["requires_cooldown_clear"] is True
        assert preview["cooldown"]["active"] is True

        second = client.post(
            "/api/forex/risk-control/update",
            json={
                "max_concurrent_trades": None,
                "confirm": RISK_LOOSEN_CONFIRM_PHRASE,
                "journal_reason": "second live loosening should hit cooldown",
            },
        )
        assert second.status_code == 409
        detail = second.json()["detail"]
        assert detail["status"] == "COOLDOWN_ACTIVE"
        assert detail["cooldown"]["active"] is True
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)


def test_live_armed_reset_loosening_requires_confirmation(tmp_path):
    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        client = _client()
        client.post("/api/forex/risk-control/update", json={"max_total_exposure_lots": 0.25})

        blocked_for_journal = client.post("/api/forex/risk-control/reset", json={})
        assert blocked_for_journal.status_code == 409
        journal_detail = blocked_for_journal.json()["detail"]
        assert journal_detail["status"] == "JOURNAL_REQUIRED"
        assert journal_detail["assessment"]["report_kind"] == "cas_forex_risk_control_reset_assessment"

        blocked_for_confirm = client.post(
            "/api/forex/risk-control/reset",
            json={"journal_reason": "resetting to the default exposure cap after a paper-only tightening test"},
        )
        assert blocked_for_confirm.status_code == 409
        confirm_detail = blocked_for_confirm.json()["detail"]
        assert confirm_detail["status"] == "CONFIRM_REQUIRED"
        assert confirm_detail["need_confirmation"] == RISK_LOOSEN_CONFIRM_PHRASE

        applied = client.post(
            "/api/forex/risk-control/reset",
            json={
                "confirm": RISK_LOOSEN_CONFIRM_PHRASE,
                "journal_reason": "resetting to the default exposure cap after a paper-only tightening test",
            },
        )
        assert applied.status_code == 200
        assert applied.json()["max_total_exposure_lots"] == 0.5
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)


def test_live_armed_reset_loosening_hits_cooldown(tmp_path):
    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        client = _client()
        client.post("/api/forex/risk-control/update", json={"max_total_exposure_lots": 0.25})

        first = client.post(
            "/api/forex/risk-control/reset",
            json={
                "confirm": RISK_LOOSEN_CONFIRM_PHRASE,
                "journal_reason": "first reset back to the default exposure cap to seed the cooldown",
            },
        )
        assert first.status_code == 200

        client.post("/api/forex/risk-control/update", json={"max_total_exposure_lots": 0.25})

        preview = client.post(
            "/api/forex/risk-control/preview-reset",
            json={"journal_reason": "second reset should hit the live loosening cooldown"},
        ).json()
        assert preview["requires_cooldown_clear"] is True
        assert preview["cooldown"]["active"] is True

        second = client.post(
            "/api/forex/risk-control/reset",
            json={
                "confirm": RISK_LOOSEN_CONFIRM_PHRASE,
                "journal_reason": "second reset should hit the live loosening cooldown",
            },
        )
        assert second.status_code == 409
        detail = second.json()["detail"]
        assert detail["status"] == "COOLDOWN_ACTIVE"
        assert detail["cooldown"]["active"] is True
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)
