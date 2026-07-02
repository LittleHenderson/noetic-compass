"""HTTP routes for live crash/disconnect recovery review."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..route_cache import cache_first_payload
from cas_forex.live_recovery import (
    CLAIM_BOUNDARY,
    LiveRecoveryError,
    accept_live_recovery_review,
    build_live_recovery_report,
    reset_live_recovery_review,
)

router = APIRouter()


class LiveRecoveryAccept(BaseModel):
    notes: Optional[str] = None


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Return live recovery status from latest broker truth + live pilot evidence."""
    return cache_first_payload(
        "live_recovery_status",
        builder=build_live_recovery_report,
        fallback=_live_recovery_warming,
        ttl_seconds=10.0,
    )


def _live_recovery_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_live_recovery_review",
        "generated_at": None,
        "recovery_status": "WARMING",
        "owner_recovery_status": "OPEN",
        "owner_accepted_at": None,
        "accepted_fingerprint": None,
        "current_fingerprint": "CACHE_WARMING",
        "recovery_clear_for_live": False,
        "requires_recovery_review": True,
        "evidence_ready_for_owner_accept": False,
        "missing_requirements": ["LIVE_RECOVERY_CACHE_WARMING"],
        "checks": [],
        "broker_truth_summary": {},
        "live_pilot_summary": {},
        "order_attempt_summary": {},
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": "Live recovery evidence cache is warming; live orders and payout movement remain blocked.",
    }


@router.post("/accept")
async def post_accept(
    body: LiveRecoveryAccept,
    confirm_owner_accept: bool = Query(default=False),
) -> dict[str, Any]:
    """Owner ACCEPT current recovery evidence before allowing more live orders."""
    try:
        return accept_live_recovery_review(
            notes=body.notes or "",
            confirm_owner_accept=confirm_owner_accept,
        )
    except LiveRecoveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reset")
async def post_reset(reason: str = "OWNER_RESET") -> dict[str, Any]:
    """Reset live recovery review to OPEN."""
    return reset_live_recovery_review(reason=reason)
