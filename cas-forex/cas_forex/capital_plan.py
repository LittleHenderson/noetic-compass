"""Capital, risk-budget, and profit-allocation planning for CAS Forex.

This module turns a money target into explicit math. It does not predict or
guarantee profit; it shows the required monthly return, flags unrealistic risk,
and builds a user-controlled sweep policy for realized profits.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict

from cas_forex.schemas.sweep import ProfitSweepPolicy, SweepMode, TransferBoundary


class GoalFeasibility(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    AGGRESSIVE = "AGGRESSIVE"
    EXTREME = "EXTREME"
    SURVIVAL_RISK = "SURVIVAL_RISK"


@dataclass(frozen=True)
class MonthlyGoalPlan:
    seed_capital: float
    monthly_income_target: float
    reinvest_pct: float
    payout_pct: float
    reserve_pct: float
    max_risk_per_trade_pct: float
    max_daily_drawdown_pct: float
    max_weekly_drawdown_pct: float
    max_open_positions: int
    required_monthly_return_pct: float
    feasibility: GoalFeasibility
    notes: tuple[str, ...]


def classify_monthly_return(required_monthly_return_pct: float) -> GoalFeasibility:
    if required_monthly_return_pct <= 5.0:
        return GoalFeasibility.CONSERVATIVE
    if required_monthly_return_pct <= 15.0:
        return GoalFeasibility.AGGRESSIVE
    if required_monthly_return_pct <= 50.0:
        return GoalFeasibility.EXTREME
    return GoalFeasibility.SURVIVAL_RISK


def build_monthly_goal_plan(
    *,
    seed_capital: float,
    monthly_income_target: float,
    reinvest_pct: float = 50.0,
    payout_pct: float = 40.0,
    reserve_pct: float = 10.0,
    max_risk_per_trade_pct: float = 0.5,
    max_daily_drawdown_pct: float = 2.0,
    max_weekly_drawdown_pct: float = 5.0,
    max_open_positions: int = 2,
) -> MonthlyGoalPlan:
    if seed_capital <= 0:
        raise ValueError("seed_capital must be positive")
    if monthly_income_target < 0:
        raise ValueError("monthly_income_target must be non-negative")
    allocation = reinvest_pct + payout_pct + reserve_pct
    if abs(allocation - 100.0) > 1e-6:
        raise ValueError("reinvest_pct + payout_pct + reserve_pct must equal 100")

    required_monthly_return_pct = monthly_income_target / seed_capital * 100.0
    feasibility = classify_monthly_return(required_monthly_return_pct)
    notes = []
    if feasibility == GoalFeasibility.SURVIVAL_RISK:
        notes.append(
            "Required return is above 50% per month; treat as survival-risk research, not a plan."
        )
    elif feasibility == GoalFeasibility.EXTREME:
        notes.append(
            "Required return is above 15% per month; paper proof and strict drawdown gates are mandatory."
        )
    notes.append("Live trading remains NOT LICENSED until broker/legal/paper-proof gates close.")
    return MonthlyGoalPlan(
        seed_capital=round(seed_capital, 2),
        monthly_income_target=round(monthly_income_target, 2),
        reinvest_pct=reinvest_pct,
        payout_pct=payout_pct,
        reserve_pct=reserve_pct,
        max_risk_per_trade_pct=max_risk_per_trade_pct,
        max_daily_drawdown_pct=max_daily_drawdown_pct,
        max_weekly_drawdown_pct=max_weekly_drawdown_pct,
        max_open_positions=max_open_positions,
        required_monthly_return_pct=round(required_monthly_return_pct, 4),
        feasibility=feasibility,
        notes=tuple(notes),
    )


def build_sweep_policy_from_goal(
    plan: MonthlyGoalPlan,
    *,
    mode: SweepMode = SweepMode.DRY_RUN,
    min_profit_threshold: float = 50.0,
    min_trading_balance: float | None = None,
    transfer_boundary: TransferBoundary = TransferBoundary.INTERNAL_LEDGER_ONLY,
    destination_allowlisted: bool = False,
    require_human_confirmation: bool = True,
) -> ProfitSweepPolicy:
    """Create a ProfitSweepPolicy matching the user's allocation choices."""
    return ProfitSweepPolicy(
        policy_id="goal-linked",
        mode=mode,
        min_profit_threshold=min_profit_threshold,
        min_trading_balance=min_trading_balance if min_trading_balance is not None else max(500.0, plan.seed_capital * 0.5),
        reinvest_pct=plan.reinvest_pct,
        savings_pct=plan.payout_pct,
        tax_reserve_pct=plan.reserve_pct,
        transfer_boundary=transfer_boundary,
        destination_allowlisted=destination_allowlisted,
        require_human_confirmation=require_human_confirmation,
    )


def seed_goal_grid(
    *,
    seed_min: float = 2_000.0,
    seed_max: float = 5_000.0,
    target_min: float = 5_000.0,
    target_max: float = 12_000.0,
) -> Dict[str, MonthlyGoalPlan]:
    """Four-corner feasibility grid for the user's stated funding/target range."""
    return {
        "low_seed_low_target": build_monthly_goal_plan(
            seed_capital=seed_min,
            monthly_income_target=target_min,
        ),
        "low_seed_high_target": build_monthly_goal_plan(
            seed_capital=seed_min,
            monthly_income_target=target_max,
        ),
        "high_seed_low_target": build_monthly_goal_plan(
            seed_capital=seed_max,
            monthly_income_target=target_min,
        ),
        "high_seed_high_target": build_monthly_goal_plan(
            seed_capital=seed_max,
            monthly_income_target=target_max,
        ),
    }
