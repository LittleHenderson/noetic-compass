"""HTTP routes for owner broker control: choose platform + loosen paper limits.

``GET /state`` reports the effective control; ``POST /update`` sets runtime
overrides for the platform and the paper execution tolerances; ``POST /reset``
clears them. Only the safe controls (platform + paper tolerances) are settable
here — the real-money loosen (``mt5_treat_account_as_demo``) and the per-transfer
cap stay env-only.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cas_forex.broker_control import (
    build_broker_control_report,
    clear_broker_control_overrides,
    set_broker_control_overrides,
)

router = APIRouter()


class BrokerControlUpdate(BaseModel):
    platform: Optional[str] = Field(default=None, description="auto | mt5 | mt4 | simulated")
    max_spread_pips: Optional[float] = Field(default=None, ge=0)
    max_slippage_pips: Optional[float] = Field(default=None, ge=0)
    min_lot: Optional[float] = Field(default=None, ge=0)
    max_lot: Optional[float] = Field(default=None, ge=0)
    min_stop_distance_pips: Optional[float] = Field(default=None, ge=0)


@router.get("/state")
async def get_broker_control() -> dict[str, Any]:
    """Return the effective broker control (platform + paper tolerances) and how
    to change each knob."""
    return build_broker_control_report()


@router.post("/update")
async def post_broker_control(body: BrokerControlUpdate) -> dict[str, Any]:
    """Set runtime overrides for the platform choice and paper tolerances."""
    try:
        set_broker_control_overrides(**body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return build_broker_control_report()


@router.post("/reset")
async def post_reset_broker_control() -> dict[str, Any]:
    """Clear all runtime overrides (revert to config/env)."""
    clear_broker_control_overrides()
    return build_broker_control_report()
