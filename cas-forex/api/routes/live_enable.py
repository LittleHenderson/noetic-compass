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
    build_authorization_report,
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


class AuthorizationUpdate(BaseModel):
    # Downstream capability owner-enable toggles (booleans).
    owner_enable_live_trading: Optional[bool] = None
    live_trading_licensed: Optional[bool] = None
    owner_enable_broker_accept: Optional[bool] = None
    owner_enable_auto_deposit: Optional[bool] = None
    owner_enable_bank_card_movement: Optional[bool] = None
    owner_enable_payout_automation: Optional[bool] = None
    payout_destination_allowlisted: Optional[bool] = None
    # Shared payment-provider config. payment_api_key is a secret the owner sets;
    # it is stored but never returned by any report.
    payment_provider: Optional[str] = None
    payment_api_key: Optional[str] = None
    payout_destination_id: Optional[str] = None


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


@router.get("/authorization")
async def get_authorization() -> dict[str, Any]:
    """Unified report for all 5 owner-controlled capabilities + provider config."""
    return build_authorization_report()


@router.post("/authorization/update")
async def post_authorization(body: AuthorizationUpdate) -> dict[str, Any]:
    """Set any capability toggle / provider field. Returns the full authorization
    report (per-capability gate status + what is still missing)."""
    provided = {key: getattr(body, key) for key in body.model_fields_set}
    if provided:
        set_live_enable_overrides(**provided)
    return build_authorization_report()


@router.post("/reset")
async def post_reset_live_enable() -> dict[str, Any]:
    """Clear all owner authorization overrides (revert to config / env defaults)."""
    clear_live_enable_overrides()
    return build_live_enable_report()
