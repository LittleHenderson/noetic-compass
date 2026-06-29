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

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from cas_forex.waste_runner import (
    DEFAULT_INTERVAL_SECONDS,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    runner_status,
    start_runner,
    stop_runner,
)

router = APIRouter()


class StartRunner(BaseModel):
    interval_seconds: int = Field(
        default=DEFAULT_INTERVAL_SECONDS,
        ge=MIN_INTERVAL_SECONDS,
        le=MAX_INTERVAL_SECONDS,
    )


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Current WASTE-runner status (running, interval, last decision, stage, mode)."""
    return runner_status()


@router.post("/start")
async def post_start(body: StartRunner, confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Start the WASTE runner. Paper-safe by default; when live trading is
    owner-authorized this runner could place real orders, so require ?confirm=true."""
    return start_runner(body.interval_seconds, confirm=confirm)


@router.post("/stop")
async def post_stop() -> dict[str, Any]:
    """Stop the WASTE runner (collapses the heartbeat to OFFLINE/idle)."""
    return stop_runner()
