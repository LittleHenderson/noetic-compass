"""HTTP routes for owner-confirmed broker emergency exposure controls."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from cas_forex.broker_emergency import (
    build_broker_emergency_status,
    run_broker_emergency_action,
)


router = APIRouter()
BROKER_EMERGENCY_CONFIRM_PHRASE = "CONFIRM BROKER EMERGENCY"


class BrokerEmergencyRequest(BaseModel):
    reason: str = Field(default="OWNER_BROKER_EMERGENCY", max_length=300)


def _broker_emergency_confirmation_matches(confirm_phrase: str) -> bool:
    if not isinstance(confirm_phrase, str):
        confirm_phrase = ""
    return (confirm_phrase or "").strip() == BROKER_EMERGENCY_CONFIRM_PHRASE


def _broker_emergency_confirm_required(
    action: str,
    *,
    dry_run: bool,
    confirm_owner_action: bool,
    confirm_phrase: str,
) -> dict[str, Any] | None:
    if dry_run:
        return None
    if confirm_owner_action and _broker_emergency_confirmation_matches(confirm_phrase):
        return None
    return {
        "report_kind": "cas_forex_broker_emergency_action",
        "action": action,
        "status": "CONFIRM_REQUIRED",
        "broker_touched": False,
        "broker_order_send_attempted": False,
        "external_money_movement": False,
        "need_confirmation": BROKER_EMERGENCY_CONFIRM_PHRASE,
        "confirm_phrase": BROKER_EMERGENCY_CONFIRM_PHRASE,
        "detail": (
            "This broker emergency action can close positions or cancel pending orders. "
            f'Set confirm_owner_action=true and confirm_phrase="{BROKER_EMERGENCY_CONFIRM_PHRASE}" to execute.'
        ),
    }


@router.get("/status")
async def get_broker_emergency_status() -> dict[str, Any]:
    """Read current MT5 positions/pending orders for emergency review."""
    return build_broker_emergency_status()


@router.post("/close-all")
async def close_all_positions(
    body: BrokerEmergencyRequest,
    dry_run: bool = Query(default=True),
    confirm_owner_action: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Close every MT5 open position after explicit owner confirmation."""
    pending = _broker_emergency_confirm_required(
        "close_all_positions",
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        confirm_phrase=confirm_phrase,
    )
    if pending is not None:
        return pending
    return run_broker_emergency_action(
        "close_all_positions",
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        reason=body.reason,
    )


@router.post("/close-profitable")
async def close_profitable_positions(
    body: BrokerEmergencyRequest,
    dry_run: bool = Query(default=True),
    confirm_owner_action: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Close only currently profitable MT5 positions after owner confirmation."""
    pending = _broker_emergency_confirm_required(
        "close_profitable_positions",
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        confirm_phrase=confirm_phrase,
    )
    if pending is not None:
        return pending
    return run_broker_emergency_action(
        "close_profitable_positions",
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        reason=body.reason,
    )


@router.post("/close-losing")
async def close_losing_positions(
    body: BrokerEmergencyRequest,
    dry_run: bool = Query(default=True),
    confirm_owner_action: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Close only currently losing MT5 positions after owner confirmation."""
    pending = _broker_emergency_confirm_required(
        "close_losing_positions",
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        confirm_phrase=confirm_phrase,
    )
    if pending is not None:
        return pending
    return run_broker_emergency_action(
        "close_losing_positions",
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        reason=body.reason,
    )


@router.post("/cancel-pending")
async def cancel_pending_orders(
    body: BrokerEmergencyRequest,
    dry_run: bool = Query(default=True),
    confirm_owner_action: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Cancel all MT5 pending orders after explicit owner confirmation."""
    pending = _broker_emergency_confirm_required(
        "cancel_pending_orders",
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        confirm_phrase=confirm_phrase,
    )
    if pending is not None:
        return pending
    return run_broker_emergency_action(
        "cancel_pending_orders",
        dry_run=dry_run,
        confirm_owner_action=confirm_owner_action,
        reason=body.reason,
    )
