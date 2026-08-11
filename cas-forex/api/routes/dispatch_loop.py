"""HTTP routes for the owner-controlled paper dispatch loop.

``GET /status`` reports whether the loop is running + its last cycle; ``POST
/start`` starts it on a timer; ``POST /stop`` stops it. Paper-safe by default —
it runs the same gated cycle as the manual dispatch button. If live trading is
owner-authorized (so the loop could place real orders), starting it requires an
explicit ``?confirm=true``.
"""

from __future__ import annotations

from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from cas_forex import runtime_gates
from cas_forex.dispatch_loop import (
    DEFAULT_INTERVAL_SECONDS,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    loop_status,
    loop_status_fast,
    requested_mode,
    start_loop,
    stop_loop,
)
from api.route_cache import cache_first_payload

router = APIRouter()
LIVE_DISPATCH_LOOP_CONFIRM_PHRASE = "CONFIRM LIVE DISPATCH LOOP"


def _live_loop_confirmation_matches(confirm_phrase: str) -> bool:
    return (confirm_phrase or "").strip() == LIVE_DISPATCH_LOOP_CONFIRM_PHRASE


def _live_loop_confirm_required(confirm: bool, confirm_phrase: str) -> Optional[dict[str, Any]]:
    live_requested = requested_mode() == "LIVE"
    live_authorized = runtime_gates.is_authorized("live_trading")
    if not live_requested and not live_authorized:
        return None
    if confirm and _live_loop_confirmation_matches(confirm_phrase):
        return None
    return {
        "report_kind": "cas_forex_dispatch_loop",
        "status": "CONFIRM_REQUIRED",
        "running": False,
        "requested_mode": "LIVE",
        "live_trading_authorized": live_authorized,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "need_confirmation": LIVE_DISPATCH_LOOP_CONFIRM_PHRASE,
        "confirm_phrase": LIVE_DISPATCH_LOOP_CONFIRM_PHRASE,
        "detail": (
            "Live mode is requested; once all runtime gates pass, this loop can "
            "place real orders on a timer. Re-POST with ?confirm=true and "
            f'confirm_phrase="{LIVE_DISPATCH_LOOP_CONFIRM_PHRASE}" to start it.'
        ),
    }


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
    position_scope: Optional[Literal["CAS_ONLY", "ALL_ACCOUNT"]] = None
    change_reason: str = Field(
        default="owner updated autonomous dispatch targeting",
        max_length=500,
    )


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Current loop status."""
    return cache_first_payload(
        "dispatch_loop_status",
        builder=loop_status,
        fallback=_dispatch_status_fast,
        ttl_seconds=5.0,
        # This is an operational heartbeat. Do not leave it queued behind
        # unrelated evidence packets on the shared serialized refresh lane.
        serialize_refresh=False,
    )


def _dispatch_status_fast() -> dict[str, Any]:
    return loop_status_fast()


@router.post("/start")
async def post_start(
    body: StartLoop,
    confirm: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Start the paper dispatch loop. Paper-safe by default; when live trading is
    owner-authorized this loop could place real orders, so require typed confirmation."""
    pending = _live_loop_confirm_required(confirm, confirm_phrase)
    if pending is not None:
        return pending
    return start_loop(
        body.interval_seconds,
        symbols=body.symbols,
        sessions=body.sessions,
        position_scope=body.position_scope,
        requested_by="owner_api",
        change_reason=body.change_reason,
    )


@router.post("/stop")
async def post_stop() -> dict[str, Any]:
    """Stop the dispatch loop."""
    return stop_loop(
        requested_by="owner_api",
        change_reason="owner stopped autonomous dispatch loop",
    )
