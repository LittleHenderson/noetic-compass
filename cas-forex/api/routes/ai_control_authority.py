"""HTTP route for CAS Forex AI Control Authority.

Owner update changes the fence. AI adjust moves a lever inside that fence. This
route does not enable live trading or money movement.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cas_forex.ai_control_authority import get_authority, reset_authority

router = APIRouter()


class OwnerEnvelopeUpdate(BaseModel):
    monthly_profit_target_usd: Optional[float] = Field(default=None, ge=0)
    daily_profit_floor_usd: Optional[float] = Field(default=None, ge=0)
    daily_profit_cap_usd: Optional[float] = Field(default=None, ge=0)
    ai_incentive_rate: Optional[float] = Field(default=None, ge=0)
    allowed_symbols: Optional[list[str]] = None
    allowed_sessions: Optional[list[str]] = None
    allow_long: Optional[bool] = None
    allow_short: Optional[bool] = None
    edge_threshold_min: Optional[float] = Field(default=None, ge=0)
    edge_threshold_max: Optional[float] = Field(default=None, ge=0)
    min_directional_confidence_min: Optional[float] = Field(default=None, ge=0)
    min_directional_confidence_max: Optional[float] = Field(default=None, ge=0)
    max_risk_pct_per_trade: Optional[float] = Field(default=None, ge=0)
    max_concurrent_trades: Optional[int] = Field(default=None, ge=1)
    max_positions_per_symbol: Optional[int] = Field(default=None, ge=1)
    max_total_exposure_lots: Optional[float] = Field(default=None, gt=0)
    daily_loss_cap_usd_max: Optional[float] = Field(default=None, ge=0)
    max_compound_units: Optional[int] = Field(default=None, ge=0)
    paper_learning_trades: Optional[int] = Field(default=None, ge=0, le=1)
    trailing_stop_enabled: Optional[int] = Field(default=None, ge=0, le=1)
    trailing_lock_fraction_min: Optional[float] = Field(default=None, ge=0)
    trailing_lock_fraction_max: Optional[float] = Field(default=None, ge=0)
    require_fresh_pass_for_entry: Optional[bool] = None
    require_fresh_pass_for_compound: Optional[bool] = None


class AiAdjustRequest(BaseModel):
    lever: str
    value: Any
    reason: str = ""


@router.get("/state")
async def get_state() -> dict[str, Any]:
    return get_authority().snapshot()


@router.get("/audit")
async def get_audit(limit: int = 25) -> dict[str, Any]:
    return get_authority().audit_report(limit)


@router.post("/preview")
async def post_preview(body: AiAdjustRequest) -> dict[str, Any]:
    try:
        return get_authority().preview_ai_adjust(body.lever, body.value, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/owner-update")
async def post_owner_update(body: OwnerEnvelopeUpdate) -> dict[str, Any]:
    changes = {
        key: getattr(body, key)
        for key in body.model_fields_set
        if getattr(body, key) is not None
    }
    try:
        return get_authority().owner_update(source="api.ai_control_authority.owner_update", **changes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/ai-adjust")
async def post_ai_adjust(body: AiAdjustRequest) -> dict[str, Any]:
    try:
        return get_authority().ai_adjust(
            body.lever,
            body.value,
            reason=body.reason,
            source="api.ai_control_authority.ai_adjust",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/reset")
async def post_reset() -> dict[str, Any]:
    return reset_authority().snapshot()
