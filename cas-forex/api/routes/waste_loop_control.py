"""HTTP routes for the owner-controlled WASTE-loop runner.

``GET /status`` reports whether the runner is ticking + its last cycle; ``POST
/start`` starts it on a timer; ``POST /stop`` stops it. Paper-safe by default —
each tick runs the W->A->S->T->E loop whose EXECUTE branch is reachable only
through a fresh edge-gate PASS, dispatched through the same gated paper path the
manual button uses. If live trading is owner-authorized (so a tick could place
real orders), starting it requires an explicit ``?confirm=true``.

This mirrors ``dispatch_loop`` route conventions; the runner itself lives in
``cas_forex.waste_runner`` and owns the threading/heartbeat wiring.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ..route_cache import cache_first_payload
from cas_forex.waste_runner import (
    DEFAULT_INTERVAL_SECONDS,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    runner_status,
    start_runner,
    stop_runner,
)
from cas_forex.waste_cycle_audit import default_waste_cycle_audit_store
from cas_forex.waste_direction_review_packet import build_waste_direction_review_packet
from cas_forex.waste_direction_learning_ledger import build_waste_direction_learning_ledger
from cas_forex.waste_direction_outcome_binding import (
    build_waste_direction_outcome_binding,
    build_waste_learning_outcomes,
)
from cas_forex.waste_paper_sample_collector import (
    DEFAULT_SCHEDULER_INTERVAL_SECONDS,
    DEFAULT_SCAN_CANDIDATE_LIMIT,
    MAX_SCHEDULER_INTERVAL_SECONDS,
    MAX_SCAN_CANDIDATE_LIMIT,
    MIN_SCHEDULER_INTERVAL_SECONDS,
    build_waste_paper_sample_collector,
    run_waste_paper_sample_collector_scheduler_once,
    run_waste_paper_sample_collection_once,
    start_waste_paper_sample_collector_scheduler,
    stop_waste_paper_sample_collector_scheduler,
    waste_paper_sample_collector_scheduler_status,
)
from cas_forex.waste_adaptation_promotion_rule import build_waste_adaptation_promotion_rule
from cas_forex.waste_adaptation_plan import build_waste_adaptation_plan
from cas_forex.waste_adaptation_apply_preview import build_waste_adaptation_apply_preview
from cas_forex.waste_adaptation_owner_review import (
    WasteAdaptationOwnerReviewError,
    build_waste_adaptation_owner_review,
    record_waste_adaptation_owner_review,
    reset_waste_adaptation_owner_review,
)
from cas_forex.waste_adaptation_paper_apply import (
    WasteAdaptationPaperApplyError,
    build_waste_adaptation_paper_apply_status,
    record_waste_adaptation_paper_apply,
    reset_waste_adaptation_paper_apply,
)
from cas_forex.mt5_market_data_diagnostic import (
    latest_mt5_market_data_diagnostic,
    run_mt5_market_data_diagnostic,
)
from cas_forex.waste_real_candle_probe import (
    DEFAULT_WASTE_BARS,
    DEFAULT_WASTE_TIMEFRAME,
    WasteRealCandleProbeDryRunError,
    build_live_order_dry_run_from_latest_probe,
    latest_waste_real_candle_probe,
    run_waste_real_candle_probe,
)
from cas_forex.waste_runner_supervisor import (
    default_waste_runner_supervisor_store,
    process_owner_id,
)
from cas_forex.waste_background_worker import (
    RUNNER_KIND,
    start_paper_sample_collector_worker,
    start_waste_runner_worker,
    stop_paper_sample_collector_worker,
    stop_waste_runner_worker,
    use_in_process_workers_for_tests,
    worker_status,
)

router = APIRouter()


class StartRunner(BaseModel):
    interval_seconds: int = Field(
        default=DEFAULT_INTERVAL_SECONDS,
        ge=MIN_INTERVAL_SECONDS,
        le=MAX_INTERVAL_SECONDS,
    )
    # Owner scalp mode: run the full candle scan every tick (instead of the cheap
    # 5-minute-probe mirror) and optionally pin the watch timeframe (e.g. "M1").
    deep_watch: bool = False
    watch_timeframe: str | None = None


class RealCandleProbeRequest(BaseModel):
    symbol: str | None = None
    timeframe: str = Field(default=DEFAULT_WASTE_TIMEFRAME)
    bars: int = Field(default=DEFAULT_WASTE_BARS, ge=40, le=1000)
    max_pairs: int = Field(default=80, ge=8, le=500)


class RealCandleProbeDryRunRequest(BaseModel):
    volume: float = Field(default=0.01, gt=0)
    order_id: str | None = None
    expected_loss_usd: float | None = Field(default=None, ge=0)
    live_telemetry: dict[str, Any] | None = None
    account_snapshot: dict[str, Any] | None = None
    equity_peak: float | None = Field(default=None, gt=0)


class MT5MarketDataDiagnosticRequest(BaseModel):
    symbols: list[str] | None = None
    timeframe: str = Field(default=DEFAULT_WASTE_TIMEFRAME)
    bars: int = Field(default=DEFAULT_WASTE_BARS, ge=40, le=1000)


class PaperSampleCollectionRunRequest(BaseModel):
    run_market_diagnostic: bool = True
    run_real_candle_probe: bool = True
    run_deal_history_ingest: bool = True
    symbol: str | None = None
    timeframe: str | None = None
    bars: int = Field(default=DEFAULT_WASTE_BARS, ge=40, le=1000)
    max_pairs: int = Field(default=80, ge=8, le=500)
    scan_candidates: bool = True
    max_scan_candidates: int = Field(
        default=DEFAULT_SCAN_CANDIDATE_LIMIT,
        ge=1,
        le=MAX_SCAN_CANDIDATE_LIMIT,
    )


class PaperSampleCollectorSchedulerStartRequest(PaperSampleCollectionRunRequest):
    interval_seconds: int = Field(
        default=DEFAULT_SCHEDULER_INTERVAL_SECONDS,
        ge=MIN_SCHEDULER_INTERVAL_SECONDS,
        le=MAX_SCHEDULER_INTERVAL_SECONDS,
    )


class AdaptationOwnerReviewRequest(BaseModel):
    decision: str = Field(default="HOLD_PAPER_ONLY")
    notes: str | None = None


class AdaptationPaperApplyRequest(BaseModel):
    notes: str | None = None


def _cached_waste_report(
    key: str,
    *,
    builder: Callable[[], dict[str, Any]],
    report_kind: str,
    ttl_seconds: float = 45.0,
) -> dict[str, Any]:
    return cache_first_payload(
        key,
        builder=builder,
        fallback=lambda: _waste_warming_packet(report_kind),
        ttl_seconds=ttl_seconds,
    )


def _waste_warming_packet(report_kind: str) -> dict[str, Any]:
    return {
        "report_kind": report_kind,
        "status": "WARMING",
        "blocker_count": 0,
        "blockers": [],
        "next_action": "This WASTE evidence packet cache is warming.",
    }


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Current WASTE-runner status (running, interval, last decision, stage, mode)."""
    return await run_in_threadpool(runner_status)


@router.get("/status/fast")
async def get_fast_status() -> dict[str, Any]:
    """Small WASTE-runner status for dashboard polling.

    The full ``/status`` route keeps the complete durable cycle evidence for deep
    inspection. This route returns only the live-card fields the UI renders, so a
    dashboard refresh does not ship the entire market-state packet every poll.
    """
    return cache_first_payload(
        "waste_runner_status_fast",
        builder=build_fast_waste_runner_status,
        fallback=_waste_runner_fast_warming,
        ttl_seconds=5.0,
    )


def _waste_runner_fast_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_waste_runner_fast",
        "running": False,
        "status": "WARMING",
        "interval_seconds": None,
        "cycles_run": None,
        "last_decision": None,
        "last_reason": "WASTE runner fast status cache is warming.",
        "last_run_iso": None,
        "started_at_iso": None,
        "current_stage": "warming",
        "mode": "PAPER",
        "durable_cycle": None,
        "supervisor": None,
        "external_worker": None,
        "worker_isolated": False,
        "claim_boundary": (
            "Fast WASTE runner status is observational only. It does not authorize "
            "live trading, mint edge tokens, place orders, deposits, withdrawals, "
            "bank/card movement, payouts, broker ACCEPT, or LICENSED status."
        ),
    }


def build_fast_waste_runner_status() -> dict[str, Any]:
    """Return the compact WASTE-runner status without requiring an HTTP call."""
    if use_in_process_workers_for_tests():
        return _slim_waste_runner_status(runner_status())
    worker = worker_status(RUNNER_KIND)
    latest_cycle = default_waste_cycle_audit_store().latest_cycle()
    supervisor = default_waste_runner_supervisor_store().build_status(
        owner_id=process_owner_id(),
        local_running=False,
    )
    return _compose_fast_waste_runner_status(
        worker=worker,
        latest_cycle=latest_cycle if isinstance(latest_cycle, dict) else None,
        supervisor=supervisor,
    )


def _slim_waste_runner_status(status: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_waste_runner_fast",
        "running": bool(status.get("running")),
        "status": status.get("status"),
        "interval_seconds": status.get("interval_seconds"),
        "cycles_run": status.get("cycles_run"),
        "last_decision": status.get("last_decision"),
        "last_reason": status.get("last_reason"),
        "last_run_iso": status.get("last_run_iso"),
        "started_at_iso": status.get("started_at_iso"),
        "current_stage": status.get("current_stage") or status.get("stage"),
        "mode": status.get("mode"),
        "durable_cycle": _compact_waste_cycle(status.get("durable_cycle")),
        "supervisor": status.get("supervisor"),
        "external_worker": _compact_worker_status(status.get("external_worker")),
        "worker_isolated": bool(status.get("worker_isolated")),
        "claim_boundary": (
            "Fast WASTE runner status is observational only. It does not authorize "
            "live trading, mint edge tokens, place orders, deposits, withdrawals, "
            "bank/card movement, payouts, broker ACCEPT, or LICENSED status."
        ),
    }


def _compose_fast_waste_runner_status(
    *,
    worker: dict[str, Any],
    latest_cycle: dict[str, Any] | None,
    supervisor: dict[str, Any],
) -> dict[str, Any]:
    lease = _mapping(supervisor.get("active_lease"))
    supervisor_running = bool(
        supervisor.get("desired_running")
        and supervisor.get("active_lease_is_fresh")
        and lease
    )
    running = bool(worker.get("running")) or supervisor_running
    cycle = latest_cycle or {}
    interval = _first_present(
        lease.get("interval_seconds"),
        _mapping(worker.get("config")).get("interval_seconds"),
        cycle.get("interval_seconds"),
    )
    stage = _latest_stage(cycle)
    return {
        "report_kind": "cas_forex_waste_runner_fast",
        "running": running,
        "status": "RUNNING" if running else "STOPPED",
        "interval_seconds": interval,
        "cycles_run": cycle.get("cycles_run"),
        "last_decision": cycle.get("decision"),
        "last_reason": cycle.get("reason"),
        "last_run_iso": cycle.get("generated_at"),
        "started_at_iso": _first_present(worker.get("started_at"), lease.get("acquired_at")),
        "current_stage": stage,
        "mode": _first_present(cycle.get("mode"), lease.get("mode"), "PAPER"),
        "durable_cycle": _compact_waste_cycle(cycle),
        "supervisor": supervisor,
        "external_worker": _compact_worker_status(worker),
        "worker_isolated": running,
        "claim_boundary": (
            "Fast WASTE runner status is observational only. It does not authorize "
            "live trading, mint edge tokens, place orders, deposits, withdrawals, "
            "bank/card movement, payouts, broker ACCEPT, or LICENSED status."
        ),
    }


def _compact_waste_cycle(cycle: Any) -> dict[str, Any] | None:
    if not isinstance(cycle, dict) or not cycle:
        return None
    watch = _mapping(cycle.get("watch_state"))
    analysis = _mapping(cycle.get("analysis"))
    candidate = _mapping(cycle.get("candidate"))
    candidate_meta = _mapping(candidate.get("market_state_meta"))
    return {
        "report_kind": cycle.get("report_kind"),
        "generated_at": cycle.get("generated_at"),
        "running": cycle.get("running"),
        "interval_seconds": cycle.get("interval_seconds"),
        "mode": cycle.get("mode"),
        "cycles_run": cycle.get("cycles_run"),
        "decision": cycle.get("decision"),
        "reason": cycle.get("reason"),
        "stage_trace": list(cycle.get("stage_trace") or []),
        "watch_state": _compact_market_state(watch),
        "analysis": {
            "confidence": analysis.get("confidence"),
            "hypothesis": _compact_hypothesis(_mapping(analysis.get("hypothesis"))),
            "strategy_firewall": _compact_strategy_firewall(_mapping(analysis.get("strategy_firewall"))),
        },
        "candidate": {
            "symbol": candidate.get("symbol"),
            "timeframe": candidate.get("timeframe"),
            "direction": candidate.get("direction"),
            "entry_pair_count": candidate.get("entry_pair_count"),
            "decision_ref": candidate.get("decision_ref"),
            "market_state_meta": _compact_market_state(candidate_meta),
        } if candidate else None,
        "edge": _compact_edge(_mapping(cycle.get("edge"))),
    }


def _compact_market_state(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "broker_grade_market_truth": value.get("broker_grade_market_truth"),
        "fallback_used": value.get("fallback_used"),
        "source": value.get("source"),
        "symbol": value.get("symbol"),
        "timeframe": value.get("timeframe"),
        "candles_count": value.get("candles_count"),
        "entry_pair_count": value.get("entry_pair_count"),
        "selected_directional_profile": value.get("selected_directional_profile"),
        "strategy_firewall": _compact_strategy_firewall(_mapping(value.get("strategy_firewall"))),
    }


def _compact_hypothesis(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": value.get("symbol"),
        "timeframe": value.get("timeframe"),
        "direction": value.get("direction"),
        "action": value.get("action"),
        "confidence": value.get("confidence"),
        "profile": value.get("profile"),
        "regime": value.get("regime"),
    }


def _compact_strategy_firewall(value: dict[str, Any]) -> dict[str, Any] | None:
    if not value:
        return None
    return {
        "candidate_allowed": value.get("candidate_allowed"),
        "firewall_status": value.get("firewall_status"),
        "lead_id": value.get("lead_id"),
        "reason": value.get("reason"),
    }


def _compact_edge(value: dict[str, Any]) -> dict[str, Any] | None:
    if not value:
        return None
    return {
        "status": value.get("status"),
        "has_edge_token": value.get("has_edge_token"),
        "measured_win_prob": value.get("measured_win_prob"),
        "null_p95": value.get("null_p95"),
        "threshold": value.get("threshold"),
        "reason": value.get("reason"),
    }


def _compact_worker_status(value: Any) -> dict[str, Any]:
    worker = _mapping(value)
    config = _mapping(worker.get("config"))
    return {
        "kind": worker.get("kind"),
        "configured": worker.get("configured"),
        "running": worker.get("running"),
        "pid": worker.get("pid"),
        "status": worker.get("status"),
        "started_at": worker.get("started_at"),
        "checked_at": worker.get("checked_at"),
        "config": {
            "interval_seconds": config.get("interval_seconds"),
            "confirm": config.get("confirm"),
        } if config else None,
    }


def _latest_stage(cycle: dict[str, Any]) -> str:
    stage_trace = cycle.get("stage_trace")
    if isinstance(stage_trace, list) and stage_trace:
        return str(stage_trace[-1] or "idle").lower()
    decision = str(cycle.get("decision") or "").upper()
    if decision == "NO_TRADE":
        return "no_trade"
    if decision == "BLOCKED":
        return "blocked"
    if decision:
        return "execute"
    return "idle"


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


@router.get("/direction-review")
async def get_direction_review() -> dict[str, Any]:
    """Read-only review of the latest WASTE LONG/SHORT choice and edge result."""
    return _cached_waste_report(
        "waste_direction_review",
        builder=build_waste_direction_review_packet,
        report_kind="cas_forex_waste_direction_review_packet",
    )


@router.get("/direction-learning")
async def get_direction_learning() -> dict[str, Any]:
    """Read-only learning ledger over recent WASTE LONG/SHORT cycle outcomes."""
    return _cached_waste_report(
        "waste_direction_learning",
        builder=build_waste_direction_learning_ledger,
        report_kind="cas_forex_waste_direction_learning_ledger",
    )


@router.get("/direction-outcome-binding")
async def get_direction_outcome_binding() -> dict[str, Any]:
    """Read-only binding from PASS-token WASTE directions to closed paper outcomes."""
    return _cached_waste_report(
        "waste_direction_outcome_binding",
        builder=build_waste_direction_outcome_binding,
        report_kind="cas_forex_waste_direction_outcome_binding",
    )


@router.get("/learning-outcomes")
async def get_learning_outcomes() -> dict[str, Any]:
    """Learn-from-mistakes ledger: realized paper win/loss per symbol x direction
    x profile across EVERY closed paper trade (learning trades included, not just
    PASS-token edges). Read-only PAPER/DEMO; never promotes to real money."""
    return _cached_waste_report(
        "waste_learning_outcomes",
        builder=build_waste_learning_outcomes,
        report_kind="cas_forex_waste_learning_outcomes",
    )


@router.get("/paper-outcomes/latest")
async def get_paper_outcomes_latest() -> dict[str, Any]:
    """The simulated paper-outcome ledger (realized P&L from real candles)."""
    from cas_forex.paper_outcome_sim import load_paper_outcome_history

    ledger = load_paper_outcome_history()
    records = ledger.get("history_records", [])
    return {
        "report_kind": ledger.get("report_kind"),
        "ingest_status": ledger.get("ingest_status"),
        "resolved_count": len(records),
        "unresolvable_count": len(ledger.get("unresolvable") or {}),
        "updated_at": ledger.get("updated_at"),
        "recent_records": records[-10:],
    }


@router.post("/paper-outcomes/run")
async def post_paper_outcomes_run() -> dict[str, Any]:
    """Resolve unresolved paper attempts against real candles now (idempotent)."""
    from cas_forex.paper_outcome_sim import resolve_paper_outcomes

    return resolve_paper_outcomes()


@router.get("/paper-sample-collector")
async def get_paper_sample_collector() -> dict[str, Any]:
    """Paper-only coordinator for broker-grade WASTE sample collection."""
    return _cached_waste_report(
        "waste_paper_sample_collector",
        builder=build_waste_paper_sample_collector,
        report_kind="cas_forex_waste_paper_sample_collector",
    )


@router.get("/paper-sample-collector/scheduler")
async def get_paper_sample_collector_scheduler() -> dict[str, Any]:
    """Owner-toggleable paper sample collector scheduler status."""
    return waste_paper_sample_collector_scheduler_status()


@router.post("/paper-sample-collector/run-once")
async def post_paper_sample_collector_run_once(body: PaperSampleCollectionRunRequest) -> dict[str, Any]:
    """Run one read-only WASTE sample collection pass.

    This can run market-data diagnostics, real-candle probes, and optional demo
    deal-history ingest. It never dispatches orders or changes live authority.
    """
    return run_waste_paper_sample_collection_once(
        run_market_diagnostic=body.run_market_diagnostic,
        run_real_candle_probe=body.run_real_candle_probe,
        run_deal_history_ingest=body.run_deal_history_ingest,
        symbol=body.symbol,
        timeframe=body.timeframe,
        bars=body.bars,
        max_pairs=body.max_pairs,
        scan_candidates=body.scan_candidates,
        max_scan_candidates=body.max_scan_candidates,
    )


@router.post("/paper-sample-collector/scheduler/run-once")
async def post_paper_sample_collector_scheduler_run_once(body: PaperSampleCollectionRunRequest) -> dict[str, Any]:
    """Run one scheduler-owned read-only paper sample collection pass."""
    return run_waste_paper_sample_collector_scheduler_once(
        run_market_diagnostic=body.run_market_diagnostic,
        run_real_candle_probe=body.run_real_candle_probe,
        run_deal_history_ingest=body.run_deal_history_ingest,
        symbol=body.symbol,
        timeframe=body.timeframe,
        bars=body.bars,
        max_pairs=body.max_pairs,
        scan_candidates=body.scan_candidates,
        max_scan_candidates=body.max_scan_candidates,
    )


@router.post("/paper-sample-collector/scheduler/start")
async def post_paper_sample_collector_scheduler_start(
    body: PaperSampleCollectorSchedulerStartRequest,
) -> dict[str, Any]:
    """Start paper-only sample collection on an owner-controlled timer."""
    if not use_in_process_workers_for_tests():
        return start_paper_sample_collector_worker(
            interval_seconds=body.interval_seconds,
            run_market_diagnostic=body.run_market_diagnostic,
            run_real_candle_probe=body.run_real_candle_probe,
            run_deal_history_ingest=body.run_deal_history_ingest,
            symbol=body.symbol,
            timeframe=body.timeframe,
            bars=body.bars,
            max_pairs=body.max_pairs,
            scan_candidates=body.scan_candidates,
            max_scan_candidates=body.max_scan_candidates,
        )
    return start_waste_paper_sample_collector_scheduler(
        interval_seconds=body.interval_seconds,
        run_market_diagnostic=body.run_market_diagnostic,
        run_real_candle_probe=body.run_real_candle_probe,
        run_deal_history_ingest=body.run_deal_history_ingest,
        symbol=body.symbol,
        timeframe=body.timeframe,
        bars=body.bars,
        max_pairs=body.max_pairs,
        scan_candidates=body.scan_candidates,
        max_scan_candidates=body.max_scan_candidates,
    )


@router.post("/paper-sample-collector/scheduler/stop")
async def post_paper_sample_collector_scheduler_stop() -> dict[str, Any]:
    """Stop paper-only sample collection scheduler."""
    if not use_in_process_workers_for_tests():
        return stop_paper_sample_collector_worker()
    return stop_waste_paper_sample_collector_scheduler()


@router.get("/adaptation-promotion-rule")
async def get_adaptation_promotion_rule() -> dict[str, Any]:
    """Read-only promotion threshold for WASTE adaptation owner review."""
    return _cached_waste_report(
        "waste_adaptation_promotion_rule",
        builder=build_waste_adaptation_promotion_rule,
        report_kind="cas_forex_waste_adaptation_promotion_rule",
    )


@router.get("/adaptation-plan")
async def get_adaptation_plan() -> dict[str, Any]:
    """Dry-run WASTE adaptation proposals from direction-learning evidence."""
    return _cached_waste_report(
        "waste_adaptation_plan",
        builder=build_waste_adaptation_plan,
        report_kind="cas_forex_waste_adaptation_plan",
    )


@router.get("/adaptation-apply-preview")
async def get_adaptation_apply_preview() -> dict[str, Any]:
    """Dry-run owner preview of what WASTE adaptation would alter."""
    return _cached_waste_report(
        "waste_adaptation_apply_preview",
        builder=build_waste_adaptation_apply_preview,
        report_kind="cas_forex_waste_adaptation_apply_preview",
    )


@router.get("/adaptation-owner-review")
async def get_adaptation_owner_review() -> dict[str, Any]:
    """Paper-only owner review audit status for WASTE adaptation preview."""
    return _cached_waste_report(
        "waste_adaptation_owner_review",
        builder=build_waste_adaptation_owner_review,
        report_kind="cas_forex_waste_adaptation_owner_review",
    )


@router.post("/adaptation-owner-review/record")
async def post_adaptation_owner_review_record(
    body: AdaptationOwnerReviewRequest,
    confirm_owner_review: bool = Query(default=False),
    confirm_owner_accept: bool = Query(default=False),
) -> dict[str, Any]:
    """Record an owner paper-only review decision for the current adaptation preview."""
    try:
        return record_waste_adaptation_owner_review(
            decision=body.decision,
            notes=body.notes or "",
            confirm_owner_review=confirm_owner_review,
            confirm_owner_accept=confirm_owner_accept,
        )
    except WasteAdaptationOwnerReviewError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/adaptation-owner-review/reset")
async def post_adaptation_owner_review_reset(reason: str = "OWNER_RESET") -> dict[str, Any]:
    """Reset WASTE adaptation owner review to OPEN."""
    return reset_waste_adaptation_owner_review(reason=reason)


@router.get("/adaptation-paper-apply")
async def get_adaptation_paper_apply() -> dict[str, Any]:
    """Paper-only apply audit status for owner-accepted WASTE adaptation."""
    return _cached_waste_report(
        "waste_adaptation_paper_apply",
        builder=build_waste_adaptation_paper_apply_status,
        report_kind="cas_forex_waste_adaptation_paper_apply",
    )


@router.post("/adaptation-paper-apply/record")
async def post_adaptation_paper_apply_record(
    body: AdaptationPaperApplyRequest,
    confirm_owner_apply: bool = Query(default=False),
) -> dict[str, Any]:
    """Record the owner-accepted adaptation preview to paper-only apply audit."""
    try:
        return record_waste_adaptation_paper_apply(
            notes=body.notes or "",
            confirm_owner_apply=confirm_owner_apply,
        )
    except WasteAdaptationPaperApplyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/adaptation-paper-apply/reset")
async def post_adaptation_paper_apply_reset(reason: str = "OWNER_RESET") -> dict[str, Any]:
    """Reset WASTE adaptation paper-apply audit state."""
    return reset_waste_adaptation_paper_apply(reason=reason)


@router.post("/start")
async def post_start(body: StartRunner, confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Start the WASTE runner. Paper-safe by default; when live trading is
    owner-authorized this runner could place real orders, so require ?confirm=true."""
    if not use_in_process_workers_for_tests():
        return start_waste_runner_worker(
            interval_seconds=body.interval_seconds,
            confirm=confirm,
            deep_watch=body.deep_watch,
            watch_timeframe=body.watch_timeframe,
        )
    return start_runner(body.interval_seconds, confirm=confirm)


@router.post("/stop")
async def post_stop() -> dict[str, Any]:
    """Stop the WASTE runner (collapses the heartbeat to OFFLINE/idle)."""
    if not use_in_process_workers_for_tests():
        return stop_waste_runner_worker()
    return stop_runner()


@router.post("/supervisor/recover")
async def post_recover_supervisor(confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Clear a stale or stop-requested WASTE supervisor lease after owner confirm.

    Fresh active desired-running leases are refused; use /stop first. This does
    not authorize live trading or start a runner.
    """
    return default_waste_runner_supervisor_store().recover_stale_or_requested(
        requested_by=process_owner_id(),
        confirm=confirm,
    )


@router.get("/real-candle-probe/latest")
async def get_real_candle_probe_latest() -> dict[str, Any]:
    """Latest durable WASTE real-candle probe report."""
    return _cached_waste_report(
        "waste_real_candle_probe_latest",
        builder=latest_waste_real_candle_probe,
        report_kind="cas_forex_waste_real_candle_probe",
        ttl_seconds=15.0,
    )


@router.post("/real-candle-probe/run")
async def post_real_candle_probe_run(body: RealCandleProbeRequest) -> dict[str, Any]:
    """Run WATCH/ANALYZE/STRATEGIZE/TEST once on real connector candles.

    This never starts the timed runner, registers edge authorization, places an
    order, or touches a broker bridge.
    """
    return run_waste_real_candle_probe(
        symbol=body.symbol,
        timeframe=body.timeframe,
        bars=body.bars,
        max_pairs=body.max_pairs,
    )


@router.post("/real-candle-probe/dry-run")
async def post_real_candle_probe_dry_run(body: RealCandleProbeDryRunRequest) -> dict[str, Any]:
    """Build a live-order dry run only from the latest broker-grade WASTE probe.

    This refuses stale, fallback, non-broker-grade, or synthetic candidates before
    live dry-run evidence is recorded, and it never touches a broker bridge.
    """
    try:
        return build_live_order_dry_run_from_latest_probe(
            volume=body.volume,
            order_id=body.order_id,
            expected_loss_usd=body.expected_loss_usd,
            live_telemetry=body.live_telemetry,
            account_snapshot=body.account_snapshot,
            equity_peak=body.equity_peak,
        )
    except WasteRealCandleProbeDryRunError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mt5-market-data-diagnostic/latest")
async def get_mt5_market_data_diagnostic_latest() -> dict[str, Any]:
    """Latest durable read-only MT5 broker-market-data diagnostic."""
    return _cached_waste_report(
        "mt5_market_data_diagnostic_latest",
        builder=latest_mt5_market_data_diagnostic,
        report_kind="cas_forex_mt5_market_data_diagnostic",
        ttl_seconds=15.0,
    )


@router.post("/mt5-market-data-diagnostic/run")
async def post_mt5_market_data_diagnostic_run(body: MT5MarketDataDiagnosticRequest) -> dict[str, Any]:
    """Check whether MT5 can provide broker-grade candles/tick spread.

    This never starts WASTE, registers edge authorization, places orders, or
    touches a broker execution bridge.
    """
    return run_mt5_market_data_diagnostic(
        symbols=body.symbols,
        timeframe=body.timeframe,
        bars=body.bars,
    )
