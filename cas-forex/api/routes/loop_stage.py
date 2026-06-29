"""HTTP route for the WASTE loop's live stage — drives the cockpit activity heartbeat.

Thin wrapper around ``cas_forex.loop_heartbeat``. The indicator polls ``/stage`` and
shows OFFLINE/idle whenever ``running`` is False (no recent tick) — so the heartbeat
always reflects what the loop is ACTUALLY doing, never a demo cycle.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from cas_forex import loop_heartbeat

router = APIRouter()


@router.get("/stage")
async def get_loop_stage() -> dict[str, Any]:
    """Current stage of the WASTE loop (idle/watch/analyze/strategize/test/execute/
    compound/locked/no_trade/blocked) plus ``running``. running=False + stage='idle'
    when no tick has landed recently."""
    return loop_heartbeat.snapshot()
