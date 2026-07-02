"""WASTE direction learning ledger coverage."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.waste_direction_learning_ledger import (
    STATUS_ACTIVE,
    STATUS_NO_EVIDENCE,
    build_waste_direction_learning_ledger,
)


def _cycle(
    idx: int,
    *,
    direction: str = "LONG",
    profile: str = "blend",
    pass_edge: bool = False,
) -> dict:
    return {
        "cycle_id": f"cycle-{idx}",
        "generated_at": f"2026-06-30T14:{idx:02d}:00+00:00",
        "decision": "EXECUTE" if pass_edge else "NO_TRADE",
        "candidate": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "direction": direction,
            "entry": 100.0,
            "stop_loss": 95.0 if direction == "LONG" else 105.0,
            "take_profit": 110.0 if direction == "LONG" else 90.0,
            "regime": "directional_pressure",
            "entry_pair_count": 40,
            "directional_hypothesis": {
                "direction": direction,
                "action": direction,
                "profile": profile,
                "long_score": 0.70 if direction == "LONG" else 0.20,
                "short_score": 0.20 if direction == "LONG" else 0.70,
                "confidence": 0.70,
                "regime": "directional_pressure",
            },
            "market_state_meta": {
                "broker_grade_market_truth": True,
                "cas_feature_map": {
                    "selected_profile": profile,
                    "selected_rpm_action": "ROUTE",
                    "selected_cjt_region": "active",
                    "selected_is_lacuna": False,
                    "cell_reliability": 0.8,
                },
                "directional_hypothesis_tuning": {
                    "no_lookahead": True,
                    "validation_pairs_holdout": True,
                },
            },
        },
        "edge": {
            "status": "PASS" if pass_edge else "NO_TRADE_NULL_FAILED",
            "has_edge_token": pass_edge,
            "measured_win_prob": 0.72 if pass_edge else 0.35,
            "threshold": 0.65,
            "null_p95": 0.01,
            "reason": "edge confirmed" if pass_edge else "did not beat null/costs",
        },
    }


def test_direction_learning_reports_no_evidence():
    ledger = build_waste_direction_learning_ledger(cycles=[])

    assert ledger["report_kind"] == "cas_forex_waste_direction_learning_ledger"
    assert ledger["status"] == STATUS_NO_EVIDENCE
    assert ledger["direction_rows"] == 0
    assert ledger["learning_ready_for_adaptation"] is False
    assert ledger["broker_touched"] is False
    assert ledger["live_order_attempted"] is False
    assert ledger["money_moved"] is False


def test_direction_learning_summarizes_blocked_long_short_outcomes():
    ledger = build_waste_direction_learning_ledger(
        cycles=[
            _cycle(1, direction="LONG", pass_edge=False),
            _cycle(2, direction="LONG", pass_edge=False),
            _cycle(3, direction="SHORT", profile="range_fade", pass_edge=False),
        ]
    )

    assert ledger["status"] == STATUS_ACTIVE
    assert ledger["direction_rows"] == 3
    assert ledger["confirmed_direction_count"] == 0
    assert ledger["blocked_direction_count"] == 3
    assert ledger["direction_counts"] == {"LONG": 2, "SHORT": 1}
    assert ledger["profile_recommendation"]["status"] == "INSUFFICIENT_CONFIRMED_EDGE"
    assert ledger["learning_ready_for_adaptation"] is False
    assert ledger["groups"][0]["cycles"] == 2


def test_direction_learning_becomes_ready_after_confirmed_edge_samples():
    cycles = [_cycle(i, direction="LONG", profile="trend_follow", pass_edge=True) for i in range(1, 6)]
    ledger = build_waste_direction_learning_ledger(
        cycles=cycles,
        min_confirmed_for_adaptation=5,
    )

    assert ledger["confirmed_direction_count"] == 5
    assert ledger["learning_ready_for_adaptation"] is True
    rec = ledger["profile_recommendation"]
    assert rec["status"] == "PROFILE_DIRECTION_REVIEW_READY"
    assert rec["recommended_group"]["profile"] == "trend_follow"
    assert rec["recommended_group"]["direction"] == "LONG"
    assert rec["recommended_group"]["confirmed_rate"] == 1.0


def test_direction_learning_route(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_waste_direction_learning_ledger",
        lambda: build_waste_direction_learning_ledger(cycles=[_cycle(1)]),
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/direction-learning")

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_waste_direction_learning_ledger"
    assert body["broker_touched"] is False
    assert body["money_moved"] is False
