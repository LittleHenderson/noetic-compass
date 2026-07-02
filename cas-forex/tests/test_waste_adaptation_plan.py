"""WASTE adaptation dry-run plan coverage."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.waste_adaptation_plan import (
    STATUS_COLLECTING,
    STATUS_NO_EVIDENCE,
    STATUS_READY,
    build_waste_adaptation_plan,
)


def _learning(*, rows: int = 0, confirmed: int = 0, ready: bool = False) -> dict:
    blocked = max(0, rows - confirmed)
    group_key = "recommended_group" if ready else "dominant_observed_group"
    return {
        "report_kind": "cas_forex_waste_direction_learning_ledger",
        "status": "WASTE_DIRECTION_LEARNING_ACTIVE" if rows else "WASTE_DIRECTION_LEARNING_NO_EVIDENCE",
        "direction_rows": rows,
        "confirmed_direction_count": confirmed,
        "blocked_direction_count": blocked,
        "learning_ready_for_adaptation": ready,
        "direction_counts": {"LONG": rows} if rows else {},
        "edge_status_counts": {"PASS": confirmed, "NO_TRADE_NULL_FAILED": blocked},
        "profile_recommendation": {
            "status": "PROFILE_DIRECTION_REVIEW_READY" if ready else "INSUFFICIENT_CONFIRMED_EDGE",
            "ready_for_adaptation": ready,
            "min_confirmed_for_adaptation": 5,
            group_key: {
                "symbol": "NAS100",
                "timeframe": "D1",
                "profile": "blend",
                "direction": "LONG",
                "cycles": rows,
                "confirmed_count": confirmed,
            },
        },
    }


def _review() -> dict:
    return {
        "report_kind": "cas_forex_waste_direction_review_packet",
        "status": "WASTE_DIRECTION_EDGE_BLOCKED",
        "direction_edge_confirmed": False,
        "direction_summary": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "direction": "LONG",
            "opposite_direction": "SHORT",
            "chosen_score": 0.55,
            "opposite_score": 0.10,
            "score_margin": 0.45,
        },
        "edge_gate_summary": {
            "status": "NO_TRADE_NULL_FAILED",
            "reason": "did not beat null/costs",
        },
    }


def _promotion(*, rows: int = 0, confirmed: int = 0, ready: bool = False, outcomes_ready: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_adaptation_promotion_rule",
        "status": "WASTE_ADAPTATION_PROMOTION_READY_FOR_OWNER_REVIEW" if ready and outcomes_ready else "WASTE_ADAPTATION_PROMOTION_COLLECTING",
        "dry_run": True,
        "read_only": True,
        "promotion_ready_for_owner_review": ready and outcomes_ready,
        "learning_ready_for_adaptation": ready,
        "outcome_ready_for_promotion": outcomes_ready,
        "min_confirmed_for_adaptation": 5,
        "confirmed_direction_count": confirmed,
        "confirmed_samples_needed": max(0, 5 - confirmed),
        "bound_outcome_count": 5 if outcomes_ready else 0,
        "bound_outcomes_needed": 0 if outcomes_ready else 5,
        "net_paper_pnl": 125.0 if outcomes_ready else 0.0,
        "blocked_direction_count": max(0, rows - confirmed),
        "direction_rows": rows,
        "dominant_group": {"symbol": "NAS100", "timeframe": "D1", "profile": "blend", "direction": "LONG"},
        "runtime_changed": False,
        "would_enable_live_trading": False,
        "money_moved": False,
        "next_action": "Promotion fixture.",
    }


def test_adaptation_plan_reports_no_evidence_without_side_effects():
    plan = build_waste_adaptation_plan(
        direction_learning=_learning(),
        direction_review=_review(),
        adaptation_promotion_rule=_promotion(),
    )

    assert plan["report_kind"] == "cas_forex_waste_adaptation_plan"
    assert plan["status"] == STATUS_NO_EVIDENCE
    assert plan["dry_run"] is True
    assert plan["runtime_changed"] is False
    assert plan["would_lower_edge_threshold"] is False
    assert plan["would_enable_live_trading"] is False
    assert plan["broker_touched"] is False
    assert plan["money_moved"] is False
    assert plan["promotion_rule_summary"]["promotion_ready_for_owner_review"] is False
    assert plan["promotion_rule_summary"]["confirmed_samples_needed"] == 5
    assert plan["proposals"][0]["proposal_type"] == "COLLECT_MORE_EVIDENCE"


def test_adaptation_plan_holds_no_trade_discipline_when_all_directions_blocked():
    plan = build_waste_adaptation_plan(
        direction_learning=_learning(rows=250, confirmed=0, ready=False),
        direction_review=_review(),
        adaptation_promotion_rule=_promotion(rows=250, confirmed=0, ready=False),
    )

    assert plan["status"] == STATUS_COLLECTING
    assert plan["adaptation_ready_for_owner_review"] is False
    proposal_types = {proposal["proposal_type"] for proposal in plan["proposals"]}
    assert "NO_TRADE_DISCIPLINE" in proposal_types
    assert "PROFILE_DIAGNOSTIC" in proposal_types
    assert all(proposal["would_apply_runtime_change"] is False for proposal in plan["proposals"])
    assert all(proposal["would_lower_edge_threshold"] is False for proposal in plan["proposals"])
    assert plan["promotion_rule_summary"]["status"] == "WASTE_ADAPTATION_PROMOTION_COLLECTING"
    assert plan["promotion_rule_summary"]["confirmed_samples_needed"] == 5


def test_adaptation_plan_ready_only_from_learning_and_outcome_evidence():
    plan = build_waste_adaptation_plan(
        direction_learning=_learning(rows=8, confirmed=5, ready=True),
        direction_review=_review(),
        adaptation_promotion_rule=_promotion(rows=8, confirmed=5, ready=True, outcomes_ready=True),
    )

    assert plan["status"] == STATUS_READY
    assert plan["adaptation_ready_for_owner_review"] is True
    proposal_types = {proposal["proposal_type"] for proposal in plan["proposals"]}
    assert "PROFILE_PRIORITY_REVIEW" in proposal_types
    assert "GATE_DISCIPLINE" in proposal_types
    assert plan["runtime_changed"] is False
    assert plan["owner_accept_created"] is False
    assert plan["promotion_rule_summary"]["promotion_ready_for_owner_review"] is True
    assert plan["promotion_rule_summary"]["confirmed_samples_needed"] == 0
    assert plan["promotion_rule_summary"]["outcome_ready_for_promotion"] is True
    assert plan["promotion_rule_summary"]["bound_outcome_count"] == 5


def test_adaptation_plan_blocks_ready_learning_without_bound_outcomes():
    plan = build_waste_adaptation_plan(
        direction_learning=_learning(rows=8, confirmed=5, ready=True),
        direction_review=_review(),
        adaptation_promotion_rule=_promotion(rows=8, confirmed=5, ready=True, outcomes_ready=False),
    )

    assert plan["status"] == STATUS_COLLECTING
    assert plan["adaptation_ready_for_owner_review"] is False
    assert plan["promotion_rule_summary"]["outcome_ready_for_promotion"] is False
    assert plan["promotion_rule_summary"]["bound_outcome_count"] == 0


def test_adaptation_plan_route(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_waste_adaptation_plan",
        lambda: build_waste_adaptation_plan(
            direction_learning=_learning(rows=2, confirmed=0),
            direction_review=_review(),
            adaptation_promotion_rule=_promotion(rows=2, confirmed=0),
        ),
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/adaptation-plan")

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_waste_adaptation_plan"
    assert body["dry_run"] is True
    assert body["runtime_changed"] is False
    assert body["money_moved"] is False
