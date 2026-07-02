"""WASTE adaptation paper-apply audit coverage."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.waste_adaptation_paper_apply import (
    STATUS_BLOCKED,
    STATUS_CURRENT,
    STATUS_READY,
    WasteAdaptationPaperApplyError,
    build_waste_adaptation_paper_apply_status,
    record_waste_adaptation_paper_apply,
    reset_waste_adaptation_paper_apply,
)


def _owner_review(*, accepted: bool = False, unsafe: bool = False) -> dict:
    fingerprint = "accepted-preview-fingerprint" if accepted else None
    return {
        "report_kind": "cas_forex_waste_adaptation_owner_review",
        "owner_review_status": "ACCEPT" if accepted else "OPEN",
        "owner_review_decision": "ACCEPT_PAPER_ONLY" if accepted else "HOLD_PAPER_ONLY",
        "accepted_fingerprint": fingerprint,
        "current_fingerprint": fingerprint or "current-preview-fingerprint",
        "paper_only_review_current": accepted,
        "paper_only_accept_current": accepted,
        "evidence_ready_for_owner_accept": accepted,
        "dry_run": True,
        "paper_only": True,
        "apply_allowed_now": False,
        "apply_endpoint_available": False,
        "runtime_changed": unsafe,
        "runtime_change_attempted": False,
        "would_apply_runtime_change": unsafe,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "would_raise_risk": False,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "preview_summary": {
            "status": "WASTE_ADAPTATION_APPLY_PREVIEW_READY_FOR_OWNER_REVIEW" if accepted else "WASTE_ADAPTATION_APPLY_PREVIEW_BLOCKED",
            "simulated_change_count": 2,
        },
        "next_action": "test owner review",
    }


def test_paper_apply_blocks_without_current_owner_accept(tmp_path):
    status = build_waste_adaptation_paper_apply_status(
        owner_review=_owner_review(accepted=False),
        state_path=tmp_path / "state.json",
    )

    assert status["report_kind"] == "cas_forex_waste_adaptation_paper_apply"
    assert status["status"] == STATUS_BLOCKED
    assert status["paper_apply_ready"] is False
    assert status["paper_apply_current"] is False
    assert "owner_paper_accept_current" in status["missing_requirements"]
    assert status["runtime_changed"] is False
    assert status["would_apply_runtime_change"] is False
    assert status["would_enable_live_trading"] is False
    assert status["broker_touched"] is False
    assert status["money_moved"] is False


def test_paper_apply_ready_with_safe_owner_accept(tmp_path):
    status = build_waste_adaptation_paper_apply_status(
        owner_review=_owner_review(accepted=True),
        state_path=tmp_path / "state.json",
    )

    assert status["status"] == STATUS_READY
    assert status["paper_apply_ready"] is True
    assert status["paper_apply_current"] is False
    assert status["missing_requirements"] == []
    assert status["paper_apply_effect"]["runtime_controls_changed"] is False


def test_paper_apply_requires_confirm_and_safe_review(tmp_path):
    with pytest.raises(WasteAdaptationPaperApplyError, match="confirm_owner_apply=true"):
        record_waste_adaptation_paper_apply(
            owner_review=_owner_review(accepted=True),
            state_path=tmp_path / "state.json",
            audit_path=tmp_path / "audit.jsonl",
        )

    with pytest.raises(WasteAdaptationPaperApplyError, match="Cannot record"):
        record_waste_adaptation_paper_apply(
            confirm_owner_apply=True,
            owner_review=_owner_review(accepted=True, unsafe=True),
            state_path=tmp_path / "state.json",
            audit_path=tmp_path / "audit.jsonl",
        )


def test_paper_apply_records_current_without_runtime_or_money(tmp_path):
    state = tmp_path / "state.json"
    audit = tmp_path / "audit.jsonl"
    status = record_waste_adaptation_paper_apply(
        notes="paper-only apply",
        confirm_owner_apply=True,
        owner_review=_owner_review(accepted=True),
        state_path=state,
        audit_path=audit,
    )

    assert status["status"] == STATUS_CURRENT
    assert status["paper_apply_ready"] is True
    assert status["paper_apply_current"] is True
    assert status["paper_apply_recorded"] is True
    assert status["runtime_changed"] is False
    assert status["would_apply_runtime_change"] is False
    assert status["would_lower_edge_threshold"] is False
    assert status["would_enable_live_trading"] is False
    assert status["owner_accept_created"] is False
    assert status["broker_touched"] is False
    assert status["money_moved"] is False
    assert "waste_adaptation_paper_apply_recorded" in audit.read_text(encoding="utf-8")


def test_paper_apply_reset(tmp_path):
    state = tmp_path / "state.json"
    audit = tmp_path / "audit.jsonl"
    record_waste_adaptation_paper_apply(
        confirm_owner_apply=True,
        owner_review=_owner_review(accepted=True),
        state_path=state,
        audit_path=audit,
    )

    status = reset_waste_adaptation_paper_apply(state_path=state, audit_path=audit)

    assert status["status"] == STATUS_BLOCKED
    assert status["paper_apply_current"] is False
    assert "waste_adaptation_paper_apply_reset" in audit.read_text(encoding="utf-8")


def test_paper_apply_routes(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_waste_adaptation_paper_apply_status",
        lambda: build_waste_adaptation_paper_apply_status(owner_review=_owner_review(accepted=False)),
    )
    monkeypatch.setattr(
        route_module,
        "record_waste_adaptation_paper_apply",
        lambda **kwargs: build_waste_adaptation_paper_apply_status(owner_review=_owner_review(accepted=False)),
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/adaptation-paper-apply")
    assert response.status_code == 200
    assert response.json()["report_kind"] == "cas_forex_waste_adaptation_paper_apply"

    response = client.post(
        "/api/forex/waste-loop-control/adaptation-paper-apply/record?confirm_owner_apply=true",
        json={"notes": "reviewed"},
    )
    assert response.status_code == 200
    assert response.json()["money_moved"] is False
