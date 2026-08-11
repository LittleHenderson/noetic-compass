from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "redteam_operator_outlier_edge_robustness.py"
)
SPEC = importlib.util.spec_from_file_location(
    "redteam_operator_outlier_edge_robustness",
    SCRIPT_PATH,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_outlier_dependent_group_is_evidence_not_press_authority() -> None:
    group = {
        "symbol": "NAS100",
        "timeframe": "M15",
        "direction": "SHORT",
        "profile": "range_fade",
        "trades": 8,
        "wins": 2,
        "losses": 6,
        "net_pnl": 70.24,
        "after_cost_expectancy_r": 0.088365,
        "largest_positive_outcome_pnl": 84.86,
        "largest_win_share_of_gross_profit": 0.525449,
        "leave_one_best_out_removed_broker_ticket": "45945252",
        "leave_one_best_out_trades": 7,
        "leave_one_best_out_net_pnl": -14.62,
        "leave_one_best_out_after_cost_expectancy_r": -0.012564,
        "leave_one_best_out_growth_positive_after_costs": False,
        "recent_consecutive_losses": 4,
        "sample_ready": True,
        "growth_positive_after_costs": True,
        "growth_robust_to_single_best_outcome": False,
        "outlier_dependency_status": "POSITIVE_DEPENDS_ON_SINGLE_BEST_OUTCOME",
        "press_size_supported_by_robust_outcomes": False,
        "outcome_ready_for_promotion": False,
    }
    report = MODULE.build_report(
        learning={
            "generated_at": "2026-07-14T06:36:00+00:00",
            "grouping_basis": "symbol_x_timeframe_x_direction_x_profile",
            "ranking_basis": (
                "after_cost_expectancy_r_then_per_1_lot_then_raw_expectancy_then_net_pnl"
            ),
            "overall": {"trades": 8, "net_pnl": 70.24},
            "group_stats": [group],
        }
    )

    assert report["status"] == "PASS_NO_TOUCH_OUTLIER_EDGE_ROBUSTNESS"
    assert report["focus_group"]["leave_one_best_out_net_pnl"] == -14.62
    assert report["focus_group"]["press_size_supported_by_robust_outcomes"] is False
    assert report["operator_policy_effect"]["paper_learning_remains_autonomous"] is True
    assert report["broker_touched"] is False
    assert report["money_moved"] is False
    assert len(report["event_hash"]) == 64
