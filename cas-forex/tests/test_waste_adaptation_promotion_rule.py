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
    group = {
        "symbol": "NAS100",
        "timeframe": "D1",
        "profile": "blend",
        "direction": "LONG",
        "trades": bound,
        "wins": bound if ready else 0,
        "losses": 0 if ready else bound,
        "win_rate": 1.0 if ready else 0.0,
        "net_pnl": 125.0 if ready else 0.0,
        "after_cost_expectancy": 25.0 if ready else 0.0,
        "after_cost_expectancy_r": 0.5 if ready else 0.0,
        "risk_normalized_trade_count": bound,
        "risk_normalized_evidence_complete": bool(bound),
        "sample_ready": bound >= 5,
        "growth_positive_after_costs": ready,
        "growth_positive_after_costs_per_risk_dollar": ready,
        "outcome_ready_for_promotion": ready,
    }
    return {
        "report_kind": "cas_forex_waste_direction_outcome_binding",
        "status": "WASTE_DIRECTION_OUTCOME_READY_FOR_PROMOTION_REVIEW" if ready else "WASTE_DIRECTION_OUTCOME_COLLECTING",
        "dry_run": True,
        "read_only": True,
        "paper_only": True,
        "outcome_ready_for_promotion": ready,
        "outcome_ready_group_count": 1 if ready else 0,
        "grouping_basis": "symbol_x_timeframe_x_direction_x_profile",
        "ranking_basis": "after_cost_expectancy_r_then_per_1_lot_then_raw_expectancy_then_net_pnl",
        "pooled_profit_cannot_promote_group": True,
        "group_stats": [group] if bound else [],
        "recommended_growth_group": group if ready else None,
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
    assert rule["recommended_group_outcome"]["net_pnl"] == 125.0
    assert rule["selection_basis"] == (
        "exact_group_after_cost_expectancy_r_then_per_1_lot_then_raw_expectancy_then_net_pnl"
    )
    assert rule["risk_normalized_evidence_required_for_promotion"] is True
    assert rule["edge_token_minted"] is False
    assert rule["money_moved"] is False


def test_promotion_rule_matches_direction_proxy_to_supported_broker_alias_group():
    learning = _learning(rows=8, confirmed=5, ready=True)
    learning["profile_recommendation"]["recommended_group"]["symbol"] = "USTEC.cash"

    rule = build_waste_adaptation_promotion_rule(
        direction_learning=learning,
        direction_outcome_binding=_outcome(confirmed=5, bound=5, ready=True),
    )

    assert rule["status"] == STATUS_READY
    assert rule["directional_proxy_group_profitable"] is True
    assert rule["proxy_recommendation_overridden_by_growth"] is False
    assert rule["directional_proxy_group_outcome"]["symbol"] == "NAS100"


def test_promotion_rule_overrides_high_pass_proxy_with_profitable_exact_group():
    outcome = _outcome(confirmed=10, bound=10, ready=True)
    losing_proxy = {
        **outcome["group_stats"][0],
        "wins": 8,
        "losses": 2,
        "win_rate": 0.8,
        "net_pnl": -20.0,
        "after_cost_expectancy": -2.0,
        "after_cost_expectancy_r": -0.2,
        "growth_positive_after_costs": False,
        "outcome_ready_for_promotion": False,
    }
    profitable_growth = {
        **losing_proxy,
        "symbol": "EURUSD",
        "timeframe": "H1",
        "profile": "after_cost_growth",
        "wins": 4,
        "losses": 6,
        "win_rate": 0.4,
        "net_pnl": 30.0,
        "after_cost_expectancy": 3.0,
        "after_cost_expectancy_r": 0.3,
        "growth_positive_after_costs": True,
        "outcome_ready_for_promotion": True,
    }
    outcome["group_stats"] = [losing_proxy, profitable_growth]
    outcome["recommended_growth_group"] = profitable_growth
    outcome["outcome_ready_group_count"] = 1

    rule = build_waste_adaptation_promotion_rule(
        direction_learning=_learning(rows=12, confirmed=10, ready=True),
        direction_outcome_binding=outcome,
    )

    assert rule["status"] == STATUS_READY
    assert rule["promotion_ready_for_owner_review"] is True
    assert rule["directional_proxy_group_profitable"] is False
    assert rule["proxy_recommendation_overridden_by_growth"] is True
    assert rule["recommended_group"]["profile"] == "after_cost_growth"
    assert rule["recommended_group_outcome"]["net_pnl"] == 30.0


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
