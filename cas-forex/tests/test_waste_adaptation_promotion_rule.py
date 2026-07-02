"""WASTE adaptation promotion-rule coverage."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.waste_adaptation_promotion_rule import (
    STATUS_COLLECTING,
    STATUS_NO_EVIDENCE,
    STATUS_READY,
    build_waste_adaptation_promotion_rule,
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


def _outcome(*, confirmed: int = 0, bound: int = 0, ready: bool = False) -> dict:
    return {
        "report_kind": "cas_forex_waste_direction_outcome_binding",
        "status": "WASTE_DIRECTION_OUTCOME_READY_FOR_PROMOTION_REVIEW" if ready else "WASTE_DIRECTION_OUTCOME_COLLECTING",
        "dry_run": True,
        "read_only": True,
        "paper_only": True,
        "outcome_ready_for_promotion": ready,
        "min_bound_outcomes_for_promotion": 5,
        "confirmed_direction_count": confirmed,
        "executed_confirmed_count": confirmed,
        "closed_history_count": bound,
        "bound_outcome_count": bound,
        "bound_outcomes_needed": max(0, 5 - bound),
        "net_paper_pnl": 125.0 if ready else 0.0,
        "runtime_changed": False,
        "would_enable_live_trading": False,
        "money_moved": False,
        "next_action": "Outcome binding test fixture.",
    }


def test_promotion_rule_reports_no_evidence_without_side_effects():
    rule = build_waste_adaptation_promotion_rule(
        direction_learning=_learning(),
        direction_outcome_binding=_outcome(),
    )

    assert rule["report_kind"] == "cas_forex_waste_adaptation_promotion_rule"
    assert rule["status"] == STATUS_NO_EVIDENCE
    assert rule["promotion_ready_for_owner_review"] is False
    assert rule["confirmed_samples_needed"] == 5
    assert rule["read_only"] is True
    assert rule["dry_run"] is True
    assert rule["runtime_changed"] is False
    assert rule["would_apply_runtime_change"] is False
    assert rule["would_lower_edge_threshold"] is False
    assert rule["would_enable_live_trading"] is False
    assert rule["broker_touched"] is False
    assert rule["owner_accept_created"] is False
    assert rule["money_moved"] is False


def test_promotion_rule_counts_remaining_pass_token_samples():
    rule = build_waste_adaptation_promotion_rule(
        direction_learning=_learning(rows=7, confirmed=2, ready=False),
        direction_outcome_binding=_outcome(confirmed=2, bound=0, ready=False),
    )

    assert rule["status"] == STATUS_COLLECTING
    assert rule["promotion_ready_for_owner_review"] is False
    assert rule["confirmed_direction_count"] == 2
    assert rule["min_confirmed_for_adaptation"] == 5
    assert rule["confirmed_samples_needed"] == 3
    assert rule["dominant_group"]["direction"] == "LONG"


def test_promotion_rule_blocks_when_outcomes_are_not_bound():
    rule = build_waste_adaptation_promotion_rule(
        direction_learning=_learning(rows=8, confirmed=5, ready=True),
        direction_outcome_binding=_outcome(confirmed=5, bound=0, ready=False),
    )

    assert rule["status"] == STATUS_COLLECTING
    assert rule["promotion_ready_for_owner_review"] is False
    assert rule["learning_ready_for_adaptation"] is True
    assert rule["outcome_ready_for_promotion"] is False
    assert rule["confirmed_samples_needed"] == 0


def test_promotion_rule_ready_only_when_learning_and_outcomes_are_ready():
    rule = build_waste_adaptation_promotion_rule(
        direction_learning=_learning(rows=8, confirmed=5, ready=True),
        direction_outcome_binding=_outcome(confirmed=5, bound=5, ready=True),
    )

    assert rule["status"] == STATUS_READY
    assert rule["promotion_ready_for_owner_review"] is True
    assert rule["learning_ready_for_adaptation"] is True
    assert rule["outcome_ready_for_promotion"] is True
    assert rule["confirmed_samples_needed"] == 0
    assert rule["bound_outcome_count"] == 5
    assert rule["recommended_group"]["profile"] == "blend"
    assert rule["edge_token_minted"] is False
    assert rule["money_moved"] is False


def test_promotion_rule_route(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_waste_adaptation_promotion_rule",
        lambda: build_waste_adaptation_promotion_rule(
            direction_learning=_learning(rows=2, confirmed=0),
            direction_outcome_binding=_outcome(confirmed=0, bound=0, ready=False),
        ),
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/adaptation-promotion-rule")

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_waste_adaptation_promotion_rule"
    assert body["status"] == STATUS_COLLECTING
    assert body["broker_touched"] is False
    assert body["money_moved"] is False
