"""WASTE adaptation owner-review audit coverage."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.waste_adaptation_owner_review import (
    DECISION_ACCEPT,
    DECISION_HOLD,
    DECISION_MORE_EVIDENCE,
    STATUS_ACCEPT,
    STATUS_OPEN,
    WasteAdaptationOwnerReviewError,
    build_waste_adaptation_owner_review,
    record_waste_adaptation_owner_review,
    reset_waste_adaptation_owner_review,
)


def _preview(*, ready: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_adaptation_apply_preview",
        "status": "WASTE_ADAPTATION_APPLY_PREVIEW_READY_FOR_OWNER_REVIEW" if ready else "WASTE_ADAPTATION_APPLY_PREVIEW_BLOCKED",
        "dry_run": True,
        "preview_ready_for_owner_review": ready,
        "apply_allowed_now": False,
        "apply_endpoint_available": False,
        "runtime_changed": False,
        "runtime_change_attempted": False,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "would_raise_risk": False,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "adaptation_plan_summary": {
            "status": "WASTE_ADAPTATION_PLAN_READY_FOR_OWNER_REVIEW" if ready else "WASTE_ADAPTATION_PLAN_COLLECTING",
            "adaptation_ready_for_owner_review": ready,
        },
        "current_controls": {"edge_threshold": 0.65},
        "owner_envelope_summary": {"daily_profit_floor_usd": 250.0},
        "simulated_change_count": 2,
        "simulated_changes": [
            {
                "proposal_id": "review_profile_direction_priority",
                "change_type": "PAPER_PROFILE_PRIORITY_HINT",
                "would_apply_runtime_change": False,
            }
        ],
        "blocker_count": 0 if ready else 1,
        "blockers": [] if ready else [{"blocker_id": "adaptation_ready_for_owner_review"}],
        "next_action": "test preview",
    }


def test_owner_review_open_for_blocked_preview_without_side_effects(tmp_path):
    report = build_waste_adaptation_owner_review(
        adaptation_apply_preview=_preview(ready=False),
        state_path=tmp_path / "state.json",
    )

    assert report["report_kind"] == "cas_forex_waste_adaptation_owner_review"
    assert report["owner_review_status"] == STATUS_OPEN
    assert report["paper_only_review_current"] is False
    assert report["paper_only_accept_current"] is False
    assert report["evidence_ready_for_owner_accept"] is False
    assert "preview_ready_for_owner_review" in report["missing_requirements"]
    assert report["apply_allowed_now"] is False
    assert report["runtime_changed"] is False
    assert report["would_apply_runtime_change"] is False
    assert report["would_enable_live_trading"] is False
    assert report["broker_touched"] is False
    assert report["owner_accept_created"] is False
    assert report["money_moved"] is False


def test_owner_review_hold_records_current_paper_review(tmp_path):
    state = tmp_path / "state.json"
    audit = tmp_path / "audit.jsonl"
    report = record_waste_adaptation_owner_review(
        decision=DECISION_HOLD,
        notes="owner wants more proof",
        confirm_owner_review=True,
        adaptation_apply_preview=_preview(ready=False),
        state_path=state,
        audit_path=audit,
    )

    assert report["owner_review_status"] == STATUS_OPEN
    assert report["owner_review_decision"] == DECISION_HOLD
    assert report["paper_only_review_current"] is True
    assert report["paper_only_accept_current"] is False
    assert report["owner_accept_created"] is False
    assert report["money_moved"] is False
    assert "waste_adaptation_owner_review_recorded" in audit.read_text(encoding="utf-8")


def test_owner_review_accept_requires_confirm_and_ready_preview(tmp_path):
    with pytest.raises(WasteAdaptationOwnerReviewError, match="confirm_owner_review=true"):
        record_waste_adaptation_owner_review(
            decision=DECISION_MORE_EVIDENCE,
            adaptation_apply_preview=_preview(ready=False),
            state_path=tmp_path / "state.json",
            audit_path=tmp_path / "audit.jsonl",
        )

    with pytest.raises(WasteAdaptationOwnerReviewError, match="Cannot ACCEPT"):
        record_waste_adaptation_owner_review(
            decision=DECISION_ACCEPT,
            confirm_owner_review=True,
            confirm_owner_accept=True,
            adaptation_apply_preview=_preview(ready=False),
            state_path=tmp_path / "state.json",
            audit_path=tmp_path / "audit.jsonl",
        )


def test_owner_review_accept_ready_preview_still_does_not_apply(tmp_path):
    report = record_waste_adaptation_owner_review(
        decision=DECISION_ACCEPT,
        notes="paper-only review accepted",
        confirm_owner_review=True,
        confirm_owner_accept=True,
        adaptation_apply_preview=_preview(ready=True),
        state_path=tmp_path / "state.json",
        audit_path=tmp_path / "audit.jsonl",
    )

    assert report["owner_review_status"] == STATUS_ACCEPT
    assert report["owner_review_decision"] == DECISION_ACCEPT
    assert report["paper_only_review_current"] is True
    assert report["paper_only_accept_current"] is True
    assert report["evidence_ready_for_owner_accept"] is True
    assert report["apply_allowed_now"] is False
    assert report["apply_endpoint_available"] is False
    assert report["runtime_changed"] is False
    assert report["would_apply_runtime_change"] is False
    assert report["would_lower_edge_threshold"] is False
    assert report["would_enable_live_trading"] is False
    assert report["owner_accept_created"] is False
    assert report["broker_touched"] is False
    assert report["money_moved"] is False


def test_owner_review_reset(tmp_path):
    state = tmp_path / "state.json"
    audit = tmp_path / "audit.jsonl"
    record_waste_adaptation_owner_review(
        decision=DECISION_HOLD,
        confirm_owner_review=True,
        adaptation_apply_preview=_preview(ready=False),
        state_path=state,
        audit_path=audit,
    )

    report = reset_waste_adaptation_owner_review(state_path=state, audit_path=audit)

    assert report["owner_review_status"] == STATUS_OPEN
    assert report["owner_review_decision"] == ""
    assert report["paper_only_review_current"] is False
    assert "waste_adaptation_owner_review_reset" in audit.read_text(encoding="utf-8")


def test_owner_review_routes(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_waste_adaptation_owner_review",
        lambda: build_waste_adaptation_owner_review(adaptation_apply_preview=_preview(ready=False)),
    )
    monkeypatch.setattr(
        route_module,
        "record_waste_adaptation_owner_review",
        lambda **kwargs: build_waste_adaptation_owner_review(adaptation_apply_preview=_preview(ready=False)),
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/adaptation-owner-review")
    assert response.status_code == 200
    assert response.json()["report_kind"] == "cas_forex_waste_adaptation_owner_review"

    response = client.post(
        "/api/forex/waste-loop-control/adaptation-owner-review/record?confirm_owner_review=true",
        json={"decision": DECISION_HOLD, "notes": "reviewed"},
    )
    assert response.status_code == 200
    assert response.json()["owner_accept_created"] is False
