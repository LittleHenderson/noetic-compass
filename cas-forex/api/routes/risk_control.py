"""HTTP routes for owner risk control: set any concurrent-trade count / loss cap.

``GET /state`` reports the effective caps; ``POST /update`` sets them (a number =
a cap, ``null`` = UNLIMITED / remove the cap); ``POST /reset`` reverts to config
defaults. Only fields actually present in the request body are changed.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cas_forex.risk_control import (
    build_risk_control_report,
    clear_risk_control_overrides,
    set_risk_control_overrides,
)

router = APIRouter()


class RiskControlUpdate(BaseModel):
    # number = cap on that dimension; null = unlimited (no cap). Omit = leave as-is.
    max_concurrent_trades: Optional[int] = Field(default=None, ge=0)
    max_total_exposure_lots: Optional[float] = Field(default=None, ge=0)
    max_loss_cap_usd: Optional[float] = Field(default=None, ge=0)
    max_drawdown_pct: Optional[float] = Field(default=None, ge=0)


@router.get("/state")
async def get_risk_control() -> dict[str, Any]:
    """Effective caps (owner overrides over config) + what each means."""
    return build_risk_control_report()


@router.post("/update")
async def post_risk_control(body: RiskControlUpdate) -> dict[str, Any]:
    """Set caps. Field present with a number = cap; present with null = unlimited;
    omitted = unchanged."""
    provided = {key: getattr(body, key) for key in body.model_fields_set}
    if not provided:
        return build_risk_control_report()
    try:
        set_risk_control_overrides(**provided)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return build_risk_control_report()


@router.post("/reset")
async def post_reset_risk_control() -> dict[str, Any]:
    """Clear all overrides (revert to config defaults)."""
    clear_risk_control_overrides()
    return build_risk_control_report()
