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
    control_state,
    restore_desired_runner,
    run_proof_day_now,
    runner_status,
    set_desired_runner_state,
    start_runner,
    stop_runner,
)
from cas_forex.waste_background_worker import (
    proof_auto_runner_worker_status,
    start_proof_auto_runner_worker,
    stop_proof_auto_runner_worker,
    use_in_process_workers_for_tests,
)
from api.route_cache import cache_first_payload

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
        "auto_runner": _auto_runner_status(),
        "claim_boundary": (
            "Paper proof advancement and thresholds only. Recording proof days "
            "does not place live orders, create broker ACCEPT, or move money."
        ),
    }


def _auto_runner_status() -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        return runner_status()
    return proof_auto_runner_worker_status()


def restore_desired_auto_runner() -> dict[str, Any]:
    """Re-arm owner-desired PAPER proof scheduling without blocking the API."""

    if use_in_process_workers_for_tests():
        return restore_desired_runner()
    desired = control_state()
    if not desired.get("desired_running"):
        status = proof_auto_runner_worker_status()
        status["restore_status"] = "NO_RESTORE_DESIRED"
        return status
    try:
        from cas_forex.config import config

        paper_safe = bool(config.paper_trading and not config.live_mode)
    except Exception:
        paper_safe = False
    if not paper_safe:
        status = proof_auto_runner_worker_status()
        status["restore_status"] = "RESTORE_BLOCKED_NOT_PAPER_MODE"
        status["restore_detail"] = (
            "Proof auto-runner desired state exists, but the app is not in "
            "paper mode. Owner must restore proof collection explicitly."
        )
        return status
    status = start_proof_auto_runner_worker(
        check_interval_seconds=int(
            desired.get("check_interval_seconds") or DEFAULT_CHECK_INTERVAL_SECONDS
        )
    )
    status["restore_status"] = "RESTORED_DESIRED_PAPER_PROOF_RUNNER"
    return status


@router.get("/state")
async def get_state() -> dict[str, Any]:
    """Live proof summary + profitability thresholds + auto-runner status."""
    return cache_first_payload(
        "proof_control_state",
        builder=_state_payload,
        fallback=_proof_state_warming,
        ttl_seconds=30.0,
    )


def _proof_state_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_proof_control",
        "status": "WARMING",
        "proof": {
            "required_trading_days": 30,
            "completed_trading_days": 0,
            "broker_verified_days": 0,
            "net_pnl_usd": 0,
            "max_drawdown_pct": 0,
            "days_with_trades": 0,
            "min_trade_days_required": 0,
            "profit_passed": False,
            "passed": False,
            "failure_reasons": ["Proof control state cache is warming."],
        },
        "thresholds": {},
        "auto_runner": {"running": False, "status": "WARMING"},
        "claim_boundary": (
            "Paper proof advancement and thresholds only. Recording proof days "
            "does not place live orders, create broker ACCEPT, or move money."
        ),
    }


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
    if use_in_process_workers_for_tests():
        start_runner(body.check_interval_seconds)
    else:
        set_desired_runner_state(body.check_interval_seconds, desired_running=True)
        start_proof_auto_runner_worker(check_interval_seconds=body.check_interval_seconds)
    return _state_payload()


@router.post("/auto/stop")
async def post_auto_stop() -> dict[str, Any]:
    """Stop the daily proof auto-runner."""
    if use_in_process_workers_for_tests():
        stop_runner()
    else:
        status = _auto_runner_status()
        set_desired_runner_state(
            int(status.get("check_interval_seconds") or DEFAULT_CHECK_INTERVAL_SECONDS),
            desired_running=False,
        )
        stop_proof_auto_runner_worker()
    return _state_payload()
