"""HTTP routes for the small-controlled live pilot envelope."""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..live_money_cache import invalidate_live_money_gate_caches
from cas_forex.live_pilot import (
    LivePilotError,
    build_live_pilot_policy,
    reset_live_pilot_policy,
    update_live_pilot_policy,
)

router = APIRouter()


class LivePilotUpdate(BaseModel):
    allowed_symbols: Optional[List[str]] = None
    max_trade_lots: Optional[float] = Field(default=None, gt=0)
    max_open_live_lots: Optional[float] = Field(default=None, gt=0)
    max_live_trade_count: Optional[int] = Field(default=None, ge=1)
    max_daily_loss_usd: Optional[float] = Field(default=None, gt=0)
    max_total_loss_usd: Optional[float] = Field(default=None, gt=0)
    max_pilot_days: Optional[int] = Field(default=None, ge=1)
    notes: Optional[str] = None
    owner_understands_real_money_risk: Optional[bool] = None
    owner_confirms_small_amounts_only: Optional[bool] = None
    owner_confirms_no_scaling_without_review: Optional[bool] = None
    owner_confirms_emergency_stop_ready: Optional[bool] = None


@router.get("/policy")
async def get_policy() -> dict[str, Any]:
    """Return the owner-reviewed live pilot policy."""
    return build_live_pilot_policy()


@router.post("/policy")
async def post_policy(
    body: LivePilotUpdate,
    confirm_owner_accept: bool = Query(default=False),
) -> dict[str, Any]:
    """Save live pilot policy fields; ACCEPT only with explicit owner confirmation."""
    try:
        result = update_live_pilot_policy(
            body.model_dump(exclude_none=True),
            confirm_owner_accept=confirm_owner_accept,
        )
        invalidate_live_money_gate_caches()
        return result
    except LivePilotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reset")
async def post_reset() -> dict[str, Any]:
    """Reset the live pilot policy to OPEN."""
    result = reset_live_pilot_policy()
    invalidate_live_money_gate_caches()
    return result
