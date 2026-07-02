"""HTTP routes for the read-only broker-truth reconciliation monitor."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ..route_cache import cache_first_payload
from cas_forex.broker_truth_monitor import (
    CLAIM_BOUNDARY,
    DEFAULT_INTERVAL_SECONDS,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    monitor_fast_status,
    monitor_status,
    run_broker_truth_check,
    start_monitor,
    stop_monitor,
)
from cas_forex.waste_background_worker import (
    broker_truth_worker_fast_status,
    overlay_broker_truth_monitor_status,
    start_broker_truth_monitor_worker,
    stop_broker_truth_monitor_worker,
    use_in_process_workers_for_tests,
)
from cas_forex.broker_truth_recovery_packet import build_broker_truth_recovery_packet
from cas_forex.broker_truth_monitor_supervisor import (
    default_broker_truth_monitor_supervisor_store,
    process_owner_id,
)

router = APIRouter()


class StartBrokerTruthMonitor(BaseModel):
    interval_seconds: int = Field(
        default=DEFAULT_INTERVAL_SECONDS,
        ge=MIN_INTERVAL_SECONDS,
        le=MAX_INTERVAL_SECONDS,
    )


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Return the monitor state and latest broker-truth report."""
    if use_in_process_workers_for_tests():
        return monitor_status()
    return await run_in_threadpool(lambda: overlay_broker_truth_monitor_status(monitor_status()))


@router.get("/status/fast")
async def get_fast_status() -> dict[str, Any]:
    """Return compact monitor state for dashboard polling."""
    return cache_first_payload(
        "broker_truth_monitor_fast_status",
        builder=broker_truth_fast_status,
        fallback=_broker_truth_fast_warming,
        ttl_seconds=10.0,
        block_on_cold=False,
    )


def broker_truth_fast_status() -> dict[str, Any]:
    if use_in_process_workers_for_tests():
        return monitor_fast_status()
    return broker_truth_worker_fast_status()


def _broker_truth_fast_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_broker_truth_monitor_status_fast",
        "running": False,
        "status": "WARMING",
        "interval_seconds": None,
        "cycles_run": 0,
        "last_error": None,
        "started_at_iso": None,
        "monitor_status": "BROKER_TRUTH_MONITOR_WARMING",
        "ready_for_live": False,
        "latest_report": None,
        "supervisor": None,
        "claim_boundary": CLAIM_BOUNDARY,
    }


@router.post("/start")
async def post_start(body: StartBrokerTruthMonitor) -> dict[str, Any]:
    """Start read-only broker-truth monitoring on a timer."""
    if use_in_process_workers_for_tests():
        return start_monitor(body.interval_seconds)
    stop_monitor()
    return start_broker_truth_monitor_worker(interval_seconds=body.interval_seconds)


@router.post("/stop")
async def post_stop() -> dict[str, Any]:
    """Stop read-only broker-truth monitoring."""
    if use_in_process_workers_for_tests():
        return stop_monitor()
    return stop_broker_truth_monitor_worker()


@router.post("/run-once")
def post_run_once() -> dict[str, Any]:
    """Run one read-only broker-truth check now and persist the report."""
    run_broker_truth_check()
    return monitor_status()


@router.get("/recovery-packet")
async def get_recovery_packet() -> dict[str, Any]:
    """Return compact owner recovery blockers from the latest broker-truth report."""
    return build_broker_truth_recovery_packet(monitor_state=monitor_status())


@router.post("/supervisor/recover")
async def post_recover_supervisor(confirm: bool = False) -> dict[str, Any]:
    """Clear a stale or stop-requested monitor lease after owner confirm.

    Fresh active desired-running leases are refused; use /stop first. This does
    not read MT5, authorize live trading, or start the monitor.
    """
    return default_broker_truth_monitor_supervisor_store().recover_stale_or_requested(
        requested_by=process_owner_id(),
        confirm=confirm,
    )
