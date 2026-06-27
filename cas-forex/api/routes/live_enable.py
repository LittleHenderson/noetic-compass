"""HTTP routes for owner live-enable control: turn the live-trading flags ON.

``GET /state`` reports the resolved flags + the live-trading gate readout (what
is still missing); ``POST /update`` flips one or more toggles; ``POST /reset``
reverts to config/env defaults. Only flags present in the request body change.

Every response re-evaluates ``runtime_gates`` so the UI always shows exactly
what is still required to actually go live.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from cas_forex.live_enable_control import (
    build_live_enable_report,
    clear_live_enable_overrides,
    set_live_enable_overrides,
)

router = APIRouter()


class LiveEnableUpdate(BaseModel):
    # Each flag: true/false to set; omit (or null) to leave unchanged.
    personal_account_ack: Optional[bool] = None
    no_pooled_capital_ack: Optional[bool] = None
    live_mode: Optional[bool] = None
    prefer_mt5: Optional[bool] = None
    owner_enable_live_trading: Optional[bool] = None
    live_trading_licensed: Optional[bool] = None


@router.get("/state")
async def get_live_enable() -> dict[str, Any]:
    """Resolved live-enable flags + the live-trading gate readout."""
    return build_live_enable_report()


@router.post("/update")
async def post_live_enable(body: LiveEnableUpdate) -> dict[str, Any]:
    """Flip toggles. Field present = set; omitted = unchanged. Returns the full
    report (incl. runtime_gates) so the UI shows what is still missing."""
    provided = {key: getattr(body, key) for key in body.model_fields_set}
    if provided:
        set_live_enable_overrides(**provided)
    return build_live_enable_report()


@router.post("/reset")
async def post_reset_live_enable() -> dict[str, Any]:
    """Clear all live-enable overrides (revert to config / env defaults)."""
    clear_live_enable_overrides()
    return build_live_enable_report()
