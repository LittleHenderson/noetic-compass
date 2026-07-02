"""HTTP routes for owner-reviewed broker reality evidence."""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..live_money_cache import invalidate_live_money_gate_caches
from cas_forex.broker_reality import (
    BrokerRealityError,
    build_broker_reality_review,
    reset_broker_reality_review,
    update_broker_reality_review,
)

router = APIRouter()


class BrokerRealityUpdate(BaseModel):
    broker_id: Optional[str] = None
    broker_entity: Optional[str] = None
    withdrawal_minimum: Optional[str] = None
    withdrawal_timing: Optional[str] = None
    kyc_requirements: Optional[str] = None
    withdrawal_fees: Optional[str] = None
    currency_conversion: Optional[str] = None
    automation_tos: Optional[str] = None
    automation_allowed_by_owner_review: Optional[bool] = None
    source_urls: Optional[List[str]] = None
    notes: Optional[str] = None
    review_valid_days: Optional[int] = Field(default=None, ge=1, le=365)
    withdrawal_minimum_reviewed: Optional[bool] = None
    withdrawal_timing_reviewed: Optional[bool] = None
    kyc_requirements_reviewed: Optional[bool] = None
    withdrawal_fees_reviewed: Optional[bool] = None
    currency_conversion_reviewed: Optional[bool] = None
    automation_tos_reviewed: Optional[bool] = None
    broker_entity_reviewed: Optional[bool] = None
    owner_accepts_broker_terms: Optional[bool] = None


@router.get("/review")
async def get_review(broker_id: str | None = Query(default=None)) -> dict[str, Any]:
    """Return owner-reviewed broker reality evidence for the selected broker."""
    return build_broker_reality_review(broker_id)


@router.post("/review")
async def post_review(
    body: BrokerRealityUpdate,
    confirm_owner_accept: bool = Query(default=False),
) -> dict[str, Any]:
    """Save broker reality review fields; ACCEPT only with explicit owner confirmation."""
    try:
        result = update_broker_reality_review(
            body.model_dump(exclude_none=True),
            confirm_owner_accept=confirm_owner_accept,
        )
        invalidate_live_money_gate_caches()
        return result
    except BrokerRealityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reset")
async def post_reset(broker_id: str | None = Query(default=None)) -> dict[str, Any]:
    """Reset the broker reality review to OPEN for the selected broker."""
    result = reset_broker_reality_review(broker_id)
    invalidate_live_money_gate_caches()
    return result
