"""HTTP routes for owner-controlled proof advancement + profitability thresholds.

``GET /state`` returns the live proof summary (now profit-measured), the
owner-adjustable thresholds, and the auto-runner status. ``POST /run-now``
records today's proof day in-app (no command line). ``POST /auto/start`` and
``/auto/stop`` control the once-per-trading-day auto-runner. ``POST /thresholds``
tunes what counts as a passed, profitable proof.

All paper-only: nothing here authorizes live money. The run path refuses live
mode and is idempotent.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from cas_forex.paper_proof import (
    build_index_tsmom_126_paper_proof_plan,
    index_tsmom_126_proof_dir,
    summarize_paper_proof,
)
from cas_forex.proof_control import (
    build_profit_thresholds_report,
    clear_profit_threshold_overrides,
    set_profit_threshold_overrides,
)
from cas_forex.proof_runner import (
    DEFAULT_CHECK_INTERVAL_SECONDS,
    MAX_CHECK_INTERVAL_SECONDS,
    MIN_CHECK_INTERVAL_SECONDS,
    run_proof_day_now,
    runner_status,
    start_runner,
    stop_runner,
)

router = APIRouter()


class ThresholdUpdate(BaseModel):
    # Each field: set to change; omit (null) to leave unchanged.
    require_net_positive: Optional[bool] = None
    min_net_pnl_usd: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    min_trade_days_fraction: Optional[float] = None
    seed_capital_usd: Optional[float] = None


class AutoRunnerStart(BaseModel):
    check_interval_seconds: int = Field(
        default=DEFAULT_CHECK_INTERVAL_SECONDS,
        ge=MIN_CHECK_INTERVAL_SECONDS,
        le=MAX_CHECK_INTERVAL_SECONDS,
    )


def _proof_summary() -> dict[str, Any]:
    plan = build_index_tsmom_126_paper_proof_plan()
    report = summarize_paper_proof(plan, index_tsmom_126_proof_dir())
    return {
        "required_trading_days": report.required_trading_days,
        "completed_trading_days": report.completed_trading_days,
        "broker_verified_days": report.broker_verified_days,
        "net_pnl_usd": report.net_pnl_usd,
        "max_drawdown_pct": report.max_drawdown_pct,
        "days_with_trades": report.days_with_trades,
        "min_trade_days_required": report.min_trade_days_required,
        "profit_passed": report.profit_passed,
        "passed": report.passed,
        "failure_reasons": list(report.failure_reasons),
    }


def _state_payload() -> dict[str, Any]:
    plan = build_index_tsmom_126_paper_proof_plan()
    return {
        "report_kind": "cas_forex_proof_control",
        "proof": _proof_summary(),
        "thresholds": build_profit_thresholds_report(plan),
        "auto_runner": runner_status(),
        "claim_boundary": (
            "Paper proof advancement and thresholds only. Recording proof days "
            "does not place live orders, create broker ACCEPT, or move money."
        ),
    }


@router.get("/state")
async def get_state() -> dict[str, Any]:
    """Live proof summary + profitability thresholds + auto-runner status."""
    return _state_payload()


@router.post("/thresholds")
async def post_thresholds(body: ThresholdUpdate) -> dict[str, Any]:
    """Tune what counts as a passed, profitable proof. Returns full state."""
    provided = {key: getattr(body, key) for key in body.model_fields_set}
    if provided:
        try:
            set_profit_threshold_overrides(**provided)
        except ValueError as exc:
            return {"report_kind": "cas_forex_proof_control", "error": str(exc), **_state_payload()}
    return _state_payload()


@router.post("/thresholds/reset")
async def post_thresholds_reset() -> dict[str, Any]:
    """Revert thresholds to plan defaults."""
    clear_profit_threshold_overrides()
    return _state_payload()


@router.post("/run-now")
def post_run_now() -> dict[str, Any]:
    """Record today's proof day in-app (paper-only, idempotent). Sync = threadpooled."""
    result = run_proof_day_now()
    payload = _state_payload()
    payload["run_result"] = result
    return payload


@router.post("/auto/start")
async def post_auto_start(body: AutoRunnerStart) -> dict[str, Any]:
    """Start the daily proof auto-runner."""
    start_runner(body.check_interval_seconds)
    return _state_payload()


@router.post("/auto/stop")
async def post_auto_stop() -> dict[str, Any]:
    """Stop the daily proof auto-runner."""
    stop_runner()
    return _state_payload()
