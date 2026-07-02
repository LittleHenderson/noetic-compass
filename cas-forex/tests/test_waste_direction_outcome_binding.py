"""WASTE direction outcome-binding coverage."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex.waste_direction_outcome_binding import (
    STATUS_AWAITING_CLOSED_HISTORY,
    STATUS_COLLECTING,
    STATUS_NO_CONFIRMED_EDGE,
    STATUS_READY,
    build_waste_direction_outcome_binding,
)


def _cycle(idx: int, *, pass_edge: bool = True, direction: str = "LONG") -> dict:
    return {
        "cycle_id": f"cycle-{idx}",
        "generated_at": f"2026-06-30T15:{idx:02d}:00+00:00",
        "decision": "EXECUTE" if pass_edge else "NO_TRADE",
        "candidate": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "direction": direction,
            "decision_ref": f"decision-{idx}",
            "directional_hypothesis": {
                "direction": direction,
                "profile": "blend",
            },
        },
        "edge": {
            "status": "PASS" if pass_edge else "NO_TRADE_NULL_FAILED",
            "has_edge_token": pass_edge,
        },
        "execute_result": {
            "status": "EXECUTED" if pass_edge else "NO_TRADE",
            "broker_ticket": f"ticket-{idx}",
        },
    }


def _attempt(idx: int, *, executed: bool = True) -> dict:
    return {
        "attempt_id": f"attempt-{idx}",
        "status": "ATTEMPT_RECORDED",
        "mode": "PAPER",
        "order_id": f"waste-decision-{idx}",
        "decision_ref": f"decision-{idx}",
        "symbol": "NAS100",
        "direction": "LONG",
        "executed": executed,
        "result_finalized": True,
        "outcome": {"broker_ticket": f"ticket-{idx}", "broker_mode": "PAPER_MT5"},
    }


def _history(rows: int, *, net: float = 25.0) -> dict:
    return {
        "report_kind": "cas_forex_mt5_deal_history_ingest_report",
        "ingest_status": "MT5_DEAL_HISTORY_JOINED_TO_MEMORY",
        "account_mode": "demo",
        "history_records": [
            {
                "broker_ticket": f"ticket-{idx}",
                "ticket": f"ticket-{idx}",
                "symbol": "NAS100",
                "direction": "buy",
                "broker_mode": "PAPER_MT5",
                "profit": net,
                "gross_profit": net + 1.0,
                "commission": -1.0,
                "swap": 0.0,
                "open_time": f"2026-06-30T15:{idx:02d}:00+00:00",
                "close_time": f"2026-06-30T16:{idx:02d}:00+00:00",
            }
            for idx in range(1, rows + 1)
        ],
    }


def test_outcome_binding_reports_no_confirmed_edge_without_side_effects():
    report = build_waste_direction_outcome_binding(
        cycles=[_cycle(1, pass_edge=False)],
        attempts=[],
        history_report=_history(0),
    )

    assert report["report_kind"] == "cas_forex_waste_direction_outcome_binding"
    assert report["status"] == STATUS_NO_CONFIRMED_EDGE
    assert report["outcome_ready_for_promotion"] is False
    assert report["paper_only"] is True
    assert report["runtime_changed"] is False
    assert report["would_enable_live_trading"] is False
    assert report["broker_touched"] is False
    assert report["owner_accept_created"] is False
    assert report["money_moved"] is False


def test_outcome_binding_waits_for_closed_paper_history():
    report = build_waste_direction_outcome_binding(
        cycles=[_cycle(1, pass_edge=True)],
        attempts=[_attempt(1)],
        history_report=_history(0),
    )

    assert report["status"] == STATUS_AWAITING_CLOSED_HISTORY
    assert report["confirmed_direction_count"] == 1
    assert report["executed_confirmed_count"] == 1
    assert report["bound_outcome_count"] == 0
    assert report["unbound_confirmed_rows"][0]["missing"] == "closed_mt5_paper_history"


def test_outcome_binding_collects_until_minimum_bound_outcomes():
    report = build_waste_direction_outcome_binding(
        cycles=[_cycle(idx, pass_edge=True) for idx in range(1, 3)],
        attempts=[_attempt(idx) for idx in range(1, 3)],
        history_report=_history(2),
        min_bound_outcomes_for_promotion=5,
    )

    assert report["status"] == STATUS_COLLECTING
    assert report["bound_outcome_count"] == 2
    assert report["bound_outcomes_needed"] == 3
    assert report["net_paper_pnl"] == 50.0
    assert report["outcome_ready_for_promotion"] is False


def test_outcome_binding_ready_after_profitable_bound_paper_outcomes():
    report = build_waste_direction_outcome_binding(
        cycles=[_cycle(idx, pass_edge=True) for idx in range(1, 6)],
        attempts=[_attempt(idx) for idx in range(1, 6)],
        history_report=_history(5),
        min_bound_outcomes_for_promotion=5,
    )

    assert report["status"] == STATUS_READY
    assert report["outcome_ready_for_promotion"] is True
    assert report["bound_outcome_count"] == 5
    assert report["bound_outcomes_needed"] == 0
    assert report["profitable_bound_count"] == 5
    assert report["net_paper_pnl"] == 125.0


def test_outcome_binding_route(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_waste_direction_outcome_binding",
        lambda: build_waste_direction_outcome_binding(
            cycles=[_cycle(1, pass_edge=True)],
            attempts=[_attempt(1)],
            history_report=_history(1),
            min_bound_outcomes_for_promotion=5,
        ),
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    response = client.get("/api/forex/waste-loop-control/direction-outcome-binding")

    assert response.status_code == 200
    body = response.json()
    assert body["report_kind"] == "cas_forex_waste_direction_outcome_binding"
    assert body["broker_touched"] is False
    assert body["money_moved"] is False
