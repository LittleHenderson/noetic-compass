"""HTTP routes for the owner-controlled paper dispatch loop.

``GET /status`` reports whether the loop is running + its last cycle; ``POST
/start`` starts it on a timer; ``POST /stop`` stops it. Paper-safe by default —
it runs the same gated cycle as the manual dispatch button. If live trading is
owner-authorized (so the loop could place real orders), starting it requires an
explicit ``?confirm=true``.
"""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from cas_forex import runtime_gates
from cas_forex.dispatch_loop import (
    DEFAULT_INTERVAL_SECONDS,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    loop_status,
    start_loop,
    stop_loop,
)

router = APIRouter()


class StartLoop(BaseModel):
    interval_seconds: int = Field(
        default=DEFAULT_INTERVAL_SECONDS,
        ge=MIN_INTERVAL_SECONDS,
        le=MAX_INTERVAL_SECONDS,
    )
    # Targeting. Omit (null) = leave unchanged; [] = clear the restriction
    # (trade everything / any session). Symbols restrict which pairs the loop
    # dispatches; sessions restrict which trading sessions it runs in.
    symbols: Optional[List[str]] = None
    sessions: Optional[List[str]] = None


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Current loop status."""
    return loop_status()


@router.post("/start")
async def post_start(body: StartLoop, confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Start the paper dispatch loop. Paper-safe by default; when live trading is
    owner-authorized this loop could place real orders, so require ?confirm=true."""
    if runtime_gates.is_authorized("live_trading") and not confirm:
        return {
            "report_kind": "cas_forex_dispatch_loop",
            "status": "CONFIRM_REQUIRED",
            "running": False,
            "detail": (
                "Live trading is owner-authorized; this loop could place real orders "
                "on a timer. Re-POST with ?confirm=true to start it."
            ),
        }
    return start_loop(body.interval_seconds, symbols=body.symbols, sessions=body.sessions)


@router.post("/stop")
async def post_stop() -> dict[str, Any]:
    """Stop the dispatch loop."""
    return stop_loop()
