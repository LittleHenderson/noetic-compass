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


def _cycle(
    idx: int,
    *,
    pass_edge: bool = True,
    direction: str = "LONG",
    regime: str = "directional_pressure",
) -> dict:
    return {
        "cycle_id": f"cycle-{idx}",
        "generated_at": f"2026-06-30T15:{idx:02d}:00+00:00",
        "decision": "EXECUTE" if pass_edge else "NO_TRADE",
        "candidate": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "direction": direction,
            "regime": regime,
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


def _attempt(idx: int, *, executed: bool = True, include_admission_risk: bool = True) -> dict:
    row = {
        "attempt_id": f"attempt-{idx}",
        "status": "ATTEMPT_RECORDED",
        "mode": "PAPER",
        "order_id": f"waste-decision-{idx}",
        "decision_ref": f"decision-{idx}",
        "symbol": "NAS100",
        "direction": "LONG",
        "volume": 0.01,
        "executed": executed,
        "result_finalized": True,
        "outcome": {"broker_ticket": f"ticket-{idx}", "broker_mode": "PAPER_MT5"},
    }
    if include_admission_risk:
        row["pre_trade_estimate"] = {
            "entry_price": 100.0,
            "stop_loss": 99.0,
            "lots": 0.01,
            "risk_at_stop_usd": 1.0,
            "unit_value_source": "broker.trade_tick_value/trade_tick_size",
            "broker_unit_value_per_lot_usd": 100.0,
            "broker_contract_constraints": {
                "tick_size": 0.01,
                "tick_value": 1.0,
                "tick_value_loss": 1.0,
            },
        }
    return row


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
    assert report["group_stats"][0]["risk_normalized_evidence_complete"] is True
    assert report["group_stats"][0]["after_cost_expectancy_r"] == 25.0


def test_outcome_binding_does_not_promote_single_best_trade_dependency():
    values = [84.86, -22.42, -7.94, 76.64, -17.92, -25.08, -12.60]
    history = _history(len(values))
    for row, value in zip(history["history_records"], values):
        row["profit"] = value
        row["gross_profit"] = value + 1.0

    report = build_waste_direction_outcome_binding(
        cycles=[_cycle(idx, pass_edge=True) for idx in range(1, len(values) + 1)],
        attempts=[_attempt(idx) for idx in range(1, len(values) + 1)],
        history_report=history,
        min_bound_outcomes_for_promotion=5,
    )

    group = report["group_stats"][0]
    assert group["net_pnl"] == 75.54
    assert group["growth_positive_after_costs"] is True
    assert group["largest_positive_outcome_pnl"] == 84.86
    assert group["leave_one_best_out_net_pnl"] == -9.32
    assert group["leave_one_best_out_after_cost_expectancy_r"] < 0.0
    assert group["recent_consecutive_losses"] == 3
    assert group["growth_robust_to_single_best_outcome"] is False
    assert group["outlier_dependency_status"] == (
        "POSITIVE_DEPENDS_ON_SINGLE_BEST_OUTCOME"
    )
    assert group["press_size_supported_by_robust_outcomes"] is False
    assert group["outcome_ready_for_promotion"] is False
    assert report["outcome_ready_for_promotion"] is False
    assert report["status"] == STATUS_COLLECTING


def test_outcome_binding_cannot_promote_with_incomplete_admission_risk():
    report = build_waste_direction_outcome_binding(
        cycles=[_cycle(idx, pass_edge=True) for idx in range(1, 6)],
        attempts=[
            _attempt(idx, include_admission_risk=False) for idx in range(1, 6)
        ],
        history_report=_history(5),
        min_bound_outcomes_for_promotion=5,
    )

    assert report["status"] == STATUS_COLLECTING
    assert report["outcome_ready_for_promotion"] is False
    assert report["risk_incomplete_sample_ready_group_count"] == 1
    group = report["group_stats"][0]
    assert group["sample_ready"] is True
    assert group["risk_normalized_evidence_complete"] is False
    assert group["promotion_blocked_by_incomplete_admission_risk"] is True
    assert "cannot be promoted" in report["next_action"]


def test_outcome_binding_does_not_pool_unrelated_profitable_groups():
    cycles = [_cycle(idx, pass_edge=True) for idx in range(1, 6)]
    for cycle in cycles[3:]:
        cycle["candidate"]["symbol"] = "EUR/USD"
        cycle["candidate"]["directional_hypothesis"]["profile"] = "range"
    history = _history(5)
    for idx, row in enumerate(history["history_records"]):
        if idx < 3:
            row["profit"] = 10.0
            row["gross_profit"] = 11.0
        else:
            row["symbol"] = "EUR/USD"
            row["profit"] = -1.0
            row["gross_profit"] = 0.0

    report = build_waste_direction_outcome_binding(
        cycles=cycles,
        attempts=[_attempt(idx) for idx in range(1, 6)],
        history_report=history,
        min_bound_outcomes_for_promotion=5,
    )

    assert report["bound_outcome_count"] == 5
    assert report["net_paper_pnl"] == 28.0
    assert report["outcome_ready_for_promotion"] is False
    assert report["outcome_ready_group_count"] == 0
    assert report["bound_outcomes_needed"] == 2
    assert report["pooled_profit_cannot_promote_group"] is True
    assert report["status"] == STATUS_COLLECTING


def test_outcome_binding_does_not_promote_pooled_profit_across_market_regimes():
    regimes = ["trend", "trend", "trend", "range", "range", "range"]
    report = build_waste_direction_outcome_binding(
        cycles=[
            _cycle(idx, pass_edge=True, regime=regime)
            for idx, regime in enumerate(regimes, start=1)
        ],
        attempts=[_attempt(idx) for idx in range(1, 7)],
        history_report=_history(6),
        min_bound_outcomes_for_promotion=5,
    )

    group = report["group_stats"][0]
    assert group["sample_ready"] is True
    assert group["growth_robust_to_single_best_outcome"] is True
    assert group["regime_count"] == 2
    assert group["regime_outcome_ready_for_promotion"] is False
    assert group["press_size_supported_by_robust_outcomes"] is False
    assert group["outcome_ready_for_promotion"] is False
    assert report["pooled_profit_cannot_promote_across_regimes"] is True
    assert report["outcome_ready_for_promotion"] is False
    assert report["status"] == STATUS_COLLECTING


def test_outcome_binding_promotes_only_after_one_regime_is_independently_ready():
    regimes = ["trend", "trend", "trend", "trend", "trend", "range"]
    report = build_waste_direction_outcome_binding(
        cycles=[
            _cycle(idx, pass_edge=True, regime=regime)
            for idx, regime in enumerate(regimes, start=1)
        ],
        attempts=[_attempt(idx) for idx in range(1, 7)],
        history_report=_history(6),
        min_bound_outcomes_for_promotion=5,
    )

    group = report["group_stats"][0]
    trend = next(
        row for row in group["regime_breakdown"] if row["market_regime"] == "TREND"
    )
    ranging = next(
        row for row in group["regime_breakdown"] if row["market_regime"] == "RANGE"
    )
    assert trend["trades"] == 5
    assert trend["outcome_ready_for_promotion"] is True
    assert ranging["trades"] == 1
    assert ranging["outcome_ready_for_promotion"] is False
    assert group["regime_outcome_ready_for_promotion"] is True
    assert group["outcome_ready_for_promotion"] is True
    assert report["outcome_ready_for_promotion"] is True
    assert report["status"] == STATUS_READY


def test_outcome_binding_pools_supported_broker_aliases_into_one_exact_market_group():
    cycles = [_cycle(idx, pass_edge=True) for idx in range(1, 6)]
    for cycle in cycles[1::2]:
        cycle["candidate"]["symbol"] = "USTEC.cash"
    history = _history(5)
    for idx, row in enumerate(history["history_records"]):
        row["symbol"] = "USTEC" if idx % 2 else "NAS100"

    report = build_waste_direction_outcome_binding(
        cycles=cycles,
        attempts=[_attempt(idx) for idx in range(1, 6)],
        history_report=history,
        min_bound_outcomes_for_promotion=5,
    )

    assert report["outcome_ready_for_promotion"] is True
    assert report["outcome_ready_group_count"] == 1
    assert len(report["group_stats"]) == 1
    group = report["group_stats"][0]
    assert group["symbol"] == "NAS100"
    assert group["observed_symbols"] == ["NAS100", "USTEC.cash"]
    assert group["trades"] == 5


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
