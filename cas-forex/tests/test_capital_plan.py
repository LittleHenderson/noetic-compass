import pytest

from cas_forex.capital_plan import (
    GoalFeasibility,
    build_monthly_goal_plan,
    build_sweep_policy_from_goal,
    seed_goal_grid,
)
from cas_forex.schemas.sweep import SweepMode, TransferBoundary


def test_monthly_goal_plan_flags_seed_target_as_survival_risk():
    plan = build_monthly_goal_plan(seed_capital=2_000, monthly_income_target=5_000)

    assert plan.required_monthly_return_pct == pytest.approx(250.0)
    assert plan.feasibility == GoalFeasibility.SURVIVAL_RISK
    assert any("survival-risk" in note for note in plan.notes)


def test_monthly_goal_plan_requires_allocation_sum_to_100():
    with pytest.raises(ValueError, match="must equal 100"):
        build_monthly_goal_plan(
            seed_capital=5_000,
            monthly_income_target=500,
            reinvest_pct=50,
            payout_pct=50,
            reserve_pct=50,
        )


def test_sweep_policy_from_goal_keeps_provider_transfers_disabled_by_default():
    plan = build_monthly_goal_plan(seed_capital=5_000, monthly_income_target=500)
    policy = build_sweep_policy_from_goal(plan)

    assert policy.mode == SweepMode.DRY_RUN
    assert policy.transfer_boundary == TransferBoundary.INTERNAL_LEDGER_ONLY
    assert policy.require_human_confirmation is True
    assert policy.reinvest_pct == plan.reinvest_pct
    assert policy.savings_pct == plan.payout_pct


def test_seed_goal_grid_covers_user_range():
    grid = seed_goal_grid()

    assert grid["low_seed_high_target"].required_monthly_return_pct == pytest.approx(600.0)
    assert grid["high_seed_low_target"].required_monthly_return_pct == pytest.approx(100.0)
    assert all(plan.feasibility == GoalFeasibility.SURVIVAL_RISK for plan in grid.values())
