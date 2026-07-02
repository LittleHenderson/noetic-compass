from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cas_forex.owner_control import clear_owner_control_overrides, set_owner_control_overrides
from ..route_cache import cache_first_payload
from ..data import (
    authority_boundary,
    authority_boundary_fast,
    owner_control,
    runtime_gates_report,
    ai_model_status,
    broker_candidate_profiles,
)

router = APIRouter()
_SETTINGS_CACHE_TTL_SECONDS = 30.0


class OwnerControlUpdate(BaseModel):
    mode: Optional[str] = None
    max_concurrent_trades: Optional[int] = Field(default=None, ge=1)
    max_loss_cap_pct: Optional[float] = Field(default=None, ge=0)
    ai_autonomy_enabled: Optional[bool] = None


@router.get("/owner-control")
async def get_owner_control():
    """Returns owner control state."""
    return owner_control()


@router.post("/owner-control/update")
async def post_owner_control(body: OwnerControlUpdate) -> dict[str, Any]:
    """Persist owner-control mode/risk/autonomy overrides for the cockpit."""
    changes = {
        key: getattr(body, key)
        for key in body.model_fields_set
        if getattr(body, key) is not None
    }
    if not changes:
        return owner_control()
    try:
        set_owner_control_overrides(**changes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return owner_control()


@router.post("/owner-control/reset")
async def post_owner_control_reset() -> dict[str, Any]:
    """Clear owner-control overrides and return to the default paper policy."""
    clear_owner_control_overrides()
    return owner_control()


@router.get("/authority-boundary")
async def get_authority_boundary():
    """Returns the current owner-controlled live-money authority boundary."""
    return cache_first_payload(
        "settings_authority_boundary",
        builder=authority_boundary,
        fallback=authority_boundary_fast,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/runtime-gates")
async def get_runtime_gates():
    """Returns each real-money capability gate: authorized vs pending owner enable,
    with the exact requirements still missing for each."""
    return cache_first_payload(
        "settings_runtime_gates",
        builder=runtime_gates_report,
        fallback=_runtime_gates_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/ai-model")
async def get_ai_model():
    """Returns the open-weight AI research-model status (advisory only)."""
    return ai_model_status()


@router.get("/broker-candidates")
async def get_broker_candidates():
    """Returns owner-requested broker candidates and verification status."""
    return broker_candidate_profiles()


def _runtime_gates_warming() -> dict[str, Any]:
    capabilities = (
        "live_trading",
        "broker_accept",
        "auto_deposit",
        "bank_card_movement",
        "payout_automation",
    )
    decisions = {
        capability: {
            "capability": capability,
            "authorized": False,
            "status": "CURRENTLY NOT LICENSED",
            "missing_requirements": ["Detailed runtime gate audit is warming."],
            "satisfied_requirements": [],
            "next_action": "Wait for the cached runtime gate report to refresh.",
        }
        for capability in capabilities
    }
    return {
        "report_kind": "cas_forex_runtime_gates",
        "decisions": decisions,
        "all_real_money_authorized": False,
        "summary": "Runtime gates are warming and fail closed as CURRENTLY NOT LICENSED.",
        "claim_boundary": (
            "Warming runtime-gates packet is read-only and fail-closed. It does not "
            "authorize live trading, broker ACCEPT, deposits, withdrawals, bank/card "
            "movement, payouts, or order execution."
        ),
    }
