"""HTTP routes for the gated order / agent dispatch loop.

Thin wrappers around ``cas_forex.agent_dispatch``. ``GET /latest`` returns the
most recent gated dispatch cycle (read-only); ``POST /run`` runs one now,
pulling the agent cycle's real route intents through the overseer and the
live-trading + risk gate into the configured broker bridge (paper by default).

The route changes no real-money posture: with default config the broker is the
paper simulator and the live-trading gate stays NOT LICENSED, so a live order is
never placed unless the owner has authorized live trading + configured a broker.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from cas_forex import runtime_gates
from cas_forex.agent_dispatch import (
    DEFAULT_OUTPUT_DIR,
    run_agent_dispatch_cycle,
    write_agent_dispatch_cycle_report,
)

router = APIRouter()


@router.get("/latest")
async def get_latest_dispatch_cycle() -> dict[str, Any]:
    """Return the most recent gated agent dispatch cycle report (read-only)."""
    candidates = sorted(DEFAULT_OUTPUT_DIR.glob("agent-dispatch-cycle-*-report.json"))
    if not candidates:
        return {
            "report_kind": "cas_forex_agent_dispatch_cycle",
            "status": "no_dispatch_cycle_yet",
            "detail": "No agent dispatch cycle has been run yet. POST /run to produce one.",
        }
    try:
        return json.loads(candidates[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "report_kind": "cas_forex_agent_dispatch_cycle",
            "status": "unreadable",
            "detail": str(exc),
        }


@router.post("/run")
async def post_run_dispatch_cycle(confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Run one gated agent dispatch cycle now and return the report.

    Pulls the agent cycle's real route intents, runs them through the overseer
    and the live-trading + risk gate into the configured broker bridge, then
    writes a JSON artifact. The configured bridge is the paper simulator unless
    the owner has authorized live trading — the gates are enforced regardless.

    When live trading is owner-authorized (so this cycle could place real
    orders), an explicit ``?confirm=true`` is required; otherwise the run is
    paper and proceeds.
    """
    if runtime_gates.is_authorized("live_trading") and not confirm:
        return {
            "report_kind": "cas_forex_agent_dispatch_cycle",
            "status": "CONFIRM_REQUIRED",
            "detail": (
                "Live trading is owner-authorized; this run could place real "
                "orders. Re-POST with ?confirm=true to execute."
            ),
        }
    cycle = run_agent_dispatch_cycle(enforce_receipt_gates=True)
    paths = write_agent_dispatch_cycle_report(cycle)
    payload = cycle.to_dict()
    payload["artifact_path"] = str(paths["json"])
    return payload
