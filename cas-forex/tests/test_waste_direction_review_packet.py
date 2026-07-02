"""WASTE direction review packet coverage."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.waste_direction_review_packet import (
    STATUS_BLOCKED,
    STATUS_CONFIRMED,
    STATUS_NO_CANDIDATE,
    build_waste_direction_review_packet,
)


def _cycle(*, edge_pass: bool = False, direction: str = "LONG") -> dict:
    entry = 100.0
    stop = 95.0 if direction == "LONG" else 105.0
    take_profit = 110.0 if direction == "LONG" else 90.0
    return {
        "report_kind": "cas_forex_waste_cycle_audit",
        "decision": "EXECUTE" if edge_pass else "NO_TRADE",
        "watch_state": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "broker_grade_market_truth": True,
            "entry_pair_count": 40,
            "selected_directional_profile": "blend",
            "directional_hypothesis_tuning": {
                "status": "SELECTED_CAUSAL_PROFILE",
                "no_lookahead": True,
                "validation_pairs_holdout": True,
            },
            "cas_feature_map": {
                "selected_profile": "blend",
                "selected_rpm_action": "ROUTE",
                "selected_cjt_region": "active",
                "selected_is_lacuna": False,
                "cell_reliability": 0.75,
            },
        },
        "analysis": {
            "hypothesis": {
                "symbol": "NAS100",
                "timeframe": "D1",
                "action": direction,
                "direction": direction,
                "long_score": 0.72 if direction == "LONG" else 0.18,
                "short_score": 0.18 if direction == "LONG" else 0.72,
                "confidence": 0.72,
                "regime": "directional_pressure",
                "profile": "blend",
            }
        },
        "candidate": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "direction": direction,
            "entry": entry,
            "stop_loss": stop,
            "take_profit": take_profit,
            "signal_strength": 0.72 if direction == "LONG" else -0.72,
            "regime": "directional_pressure",
            "decision_ref": "waste-dir-test",
            "entry_pair_count": 40,
            "directional_hypothesis": {
                "symbol": "NAS100",
                "timeframe": "D1",
                "action": direction,
                "direction": direction,
                "long_score": 0.72 if direction == "LONG" else 0.18,
                "short_score": 0.18 if direction == "LONG" else 0.72,
                "confidence": 0.72,
                "regime": "directional_pressure",
                "profile": "blend",
            },
            "market_state_meta": {
                "broker_grade_market_truth": True,
                "cas_feature_map": {
                    "selected_profile": "blend",
                    "selected_rpm_action": "ROUTE",
                    "selected_cjt_region": "active",
                    "selected_is_lacuna": False,
                    "cell_reliability": 0.75,
                },
                "directional_hypothesis_tuning": {
                    "status": "SELECTED_CAUSAL_PROFILE",
                    "no_lookahead": True,
                    "validation_pairs_holdout": True,
                },
            },
        },
        "edge": {
            "status": "PASS" if edge_pass else "NO_TRADE_NULL_FAILED",
            "measured_win_prob": 0.72 if edge_pass else 0.35,
            "threshold": 0.65,
            "null_p95": 0.01,
            "has_edge_token": edge_pass,
            "reason": "edge confirmed" if edge_pass else "did not beat null/costs",
        },
    }


def test_waste_direction_review_blocks_unconfirmed_direction():
    packet = build_waste_direction_review_packet(latest_cycle=_cycle(edge_pass=False))

    assert packet["report_kind"] == "cas_forex_waste_direction_review_packet"
    assert packet["status"] == STATUS_BLOCKED
    assert packet["direction_edge_confirmed"] is False
    assert packet["direction_summary"]["direction"] == "LONG"
    assert packet["direction_summary"]["opposite_direction"] == "SHORT"
    assert packet["direction_summary"]["chosen_score"] > packet["direction_summary"]["opposite_score"]
    assert packet["profit_box"]["valid"] is True
    assert packet["profit_box"]["reward_r"] == 2.0
    assert packet["broker_touched"] is False
    assert packet["live_order_attempted"] is False
    assert packet["money_moved"] is False
    blocker_ids = {blocker["blocker_id"] for blocker in packet["blockers"]}
    assert "edge_gate_passed_for_direction" in blocker_ids


def test_waste_direction_review_confirms_only_with_pass_token():
    packet = build_waste_direction_review_packet(latest_cycle=_cycle(edge_pass=True, direction="SHORT"))

    assert packet["status"] == STATUS_CONFIRMED
    assert packet["direction_edge_confirmed"] is True
    assert packet["direction_summary"]["direction"] == "SHORT"
    assert packet["direction_summary"]["opposite_direction"] == "LONG"
    assert packet["profit_box"]["valid"] is True
    assert packet["profit_box"]["reward_r"] == 2.0
    assert packet["blockers"] == []


def test_waste_direction_review_reports_no_candidate():
    packet = build_waste_direction_review_packet(
        latest_cycle={
            "report_kind": "cas_forex_waste_cycle_audit",
            "decision": "NO_TRADE",
            "candidate": None,
            "edge": None,
        }
    )

    assert packet["status"] == STATUS_NO_CANDIDATE
    assert packet["direction_edge_confirmed"] is False
    assert packet["blocker_count"] >= 1


def test_waste_direction_review_route(monkeypatch):
    monkeypatch.setattr(route_module, "build_waste_direction_review_packet", lambda: build_waste_direction_review_packet(latest_cycle=_cycle()))
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/direction-review")

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_waste_direction_review_packet"
    assert body["broker_touched"] is False
    assert body["money_moved"] is False
