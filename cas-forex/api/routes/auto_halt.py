"""HTTP routes for CAS Forex auto-halt circuit breakers."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..route_cache import cache_first_payload
from api.data import auto_halt_status
from cas_forex.auto_halt import CLAIM_BOUNDARY, AutoHaltSettings, clear_auto_halt

router = APIRouter()


class ClearAutoHaltRequest(BaseModel):
    reason: str = Field(default="OWNER_CLEAR", max_length=200)


@router.get("/status")
async def get_auto_halt_status() -> dict[str, Any]:
    """Evaluate current broker/account evidence and return the auto-halt state."""
    return cache_first_payload(
        "auto_halt_status",
        builder=lambda: auto_halt_status(persist=True),
        fallback=_auto_halt_warming,
        ttl_seconds=10.0,
    )


def _auto_halt_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_auto_halt",
        "status": "WARMING",
        "halt_active": False,
        "force_paper_mode": True,
        "settings": AutoHaltSettings().to_dict(),
        "checks": [],
        "triggered_checks": [],
        "active_state": {"active": False, "force_paper_mode": True, "reasons": ["AUTO_HALT_CACHE_WARMING"]},
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": "Auto-halt evidence cache is warming; keep live authority fail-closed until refreshed.",
    }


@router.post("/clear")
async def post_clear_auto_halt(
    body: ClearAutoHaltRequest,
    confirm_clear: bool = Query(default=False),
) -> dict[str, Any]:
    """Clear the auto-halt latch after explicit owner confirmation."""
    try:
        state = clear_auto_halt(confirm_clear=confirm_clear, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report = auto_halt_status(persist=False)
    report["clear_state"] = state
    return report
