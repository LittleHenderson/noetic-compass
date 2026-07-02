"""HTTP route for live-order dry-run audits."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..live_money_cache import invalidate_live_money_gate_caches
from ..route_cache import cache_first_payload
from cas_forex import runtime_gates
from cas_forex.broker_control import select_bridge
from cas_forex.compound_add_order_dry_run_review import (
    CLAIM_BOUNDARY as COMPOUND_ADD_REVIEW_CLAIM_BOUNDARY,
    CompoundAddOrderDryRunReviewError,
    accept_compound_add_order_dry_run_review,
    build_compound_add_order_dry_run_review,
    reset_compound_add_order_dry_run_review,
)
from cas_forex.config import config as default_config
from cas_forex.live_order_dry_run import (
    CLAIM_BOUNDARY as LIVE_ORDER_DRY_RUN_CLAIM_BOUNDARY,
    COMPOUND_ADD_CLAIM_BOUNDARY,
    DEFAULT_AUDIT_PATH,
    DEFAULT_COMPOUND_ADD_AUDIT_PATH,
    LiveOrderDryRunAuditLog,
    build_compound_add_order_dry_run,
    build_live_order_dry_run,
    compound_add_request_from_mapping,
    request_from_mapping,
)
from cas_forex.live_order_dry_run_review import (
    CLAIM_BOUNDARY as LIVE_ORDER_REVIEW_CLAIM_BOUNDARY,
    LiveOrderDryRunReviewError,
    accept_live_order_dry_run_review,
    build_live_order_dry_run_review,
    reset_live_order_dry_run_review,
)
from cas_forex.waste_pilot_promotion import build_waste_pilot_promotion_status
from cas_forex.waste_runner import (
    COMPOUND_ADD_HANDOFF_CLAIM_BOUNDARY,
    COMPOUND_ADD_HANDOFF_REPORT_KIND,
    STATUS_COMPOUND_ADD_HANDOFF_BLOCKED,
    STATUS_WASTE_ENTRY_HANDOFF_BLOCKED,
    WASTE_ENTRY_HANDOFF_CLAIM_BOUNDARY,
    WASTE_ENTRY_HANDOFF_REPORT_KIND,
    build_compound_add_dispatch_handoff_status,
    build_waste_entry_dispatch_handoff_status,
    dispatch_compound_add_from_dry_run,
    dispatch_waste_entry_from_dry_run,
)

router = APIRouter()


def _latest_live_order_dry_run_payload() -> dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(DEFAULT_AUDIT_PATH).latest()
    if latest is None:
        return {
            "report_kind": "cas_forex_live_order_dry_run_latest",
            "status": "NO_DRY_RUN_AUDIT_YET",
            "broker_touched": False,
            "detail": "No live-order dry-run audit has been recorded yet.",
        }
    return {
        "report_kind": "cas_forex_live_order_dry_run_latest",
        "status": latest.get("status"),
        "broker_touched": False,
        "latest_audit": latest,
    }


def _latest_live_order_dry_run_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_live_order_dry_run_latest",
        "status": "WARMING",
        "broker_touched": False,
        "detail": "Live-order dry-run audit cache is warming; no broker was touched.",
        "claim_boundary": LIVE_ORDER_DRY_RUN_CLAIM_BOUNDARY,
    }


def _live_order_dry_run_review_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_live_order_dry_run_review",
        "generated_at": None,
        "review_status": "OPEN",
        "owner_review_status": "OPEN",
        "owner_accepted_at": None,
        "accepted_fingerprint": None,
        "current_fingerprint": "CACHE_WARMING",
        "dry_run_review_clear_for_live": False,
        "evidence_ready_for_owner_accept": False,
        "missing_requirements": ["LIVE_ORDER_DRY_RUN_REVIEW_CACHE_WARMING"],
        "checks": [],
        "latest_dry_run_summary": {},
        "broker_truth_summary": {},
        "claim_boundary": LIVE_ORDER_REVIEW_CLAIM_BOUNDARY,
        "next_action": "Live-order dry-run review cache is warming; dispatch remains blocked.",
    }


def _waste_entry_handoff_payload() -> dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(DEFAULT_AUDIT_PATH).latest()
    payload = latest.get("payload") if isinstance(latest, dict) else {}
    review = build_live_order_dry_run_review(dry_run_audit=latest or {})
    return build_waste_entry_dispatch_handoff_status(payload if isinstance(payload, dict) else {}, review=review)


def _waste_entry_handoff_warming() -> dict[str, Any]:
    return {
        "report_kind": WASTE_ENTRY_HANDOFF_REPORT_KIND,
        "status": STATUS_WASTE_ENTRY_HANDOFF_BLOCKED,
        "order_id": None,
        "decision_ref": None,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "dispatch_preview_only": True,
        "would_call_dispatch_if_owner_attempted": False,
        "missing_requirements": ["WASTE_ENTRY_HANDOFF_CACHE_WARMING"],
        "reason": "WASTE entry handoff cache is warming.",
        "claim_boundary": WASTE_ENTRY_HANDOFF_CLAIM_BOUNDARY,
        "next_action": "Wait for WASTE entry handoff evidence to refresh before attempting dispatch.",
    }


def _waste_entry_pilot_promotion_payload() -> dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(DEFAULT_AUDIT_PATH).latest()
    return build_waste_pilot_promotion_status(dry_run_audit=latest or {})


def _waste_entry_pilot_promotion_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_waste_pilot_promotion",
        "generated_at": None,
        "status": "WASTE_PILOT_WARMING",
        "ready_for_pilot_sequence": False,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "dispatch_attempted": False,
        "order_id": None,
        "decision_ref": None,
        "symbol": None,
        "direction": None,
        "lots": None,
        "entry_pair_count": 0,
        "missing_requirements": ["WASTE_PILOT_CACHE_WARMING"],
        "checks": [],
        "claim_boundary": (
            "WASTE pilot promotion cache warming is read-only. It does not place orders, "
            "touch a broker bridge, create ACCEPT, or authorize live trading."
        ),
        "next_action": "WASTE pilot promotion evidence cache is warming.",
    }


def _latest_compound_add_order_dry_run_payload() -> dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(DEFAULT_COMPOUND_ADD_AUDIT_PATH).latest()
    if latest is None:
        return {
            "report_kind": "cas_forex_compound_add_order_dry_run_latest",
            "status": "NO_COMPOUND_ADD_DRY_RUN_AUDIT_YET",
            "broker_touched": False,
            "detail": "No compound-add dry-run audit has been recorded yet.",
        }
    return {
        "report_kind": "cas_forex_compound_add_order_dry_run_latest",
        "status": latest.get("status"),
        "broker_touched": False,
        "latest_audit": latest,
    }


def _latest_compound_add_order_dry_run_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_compound_add_order_dry_run_latest",
        "status": "WARMING",
        "broker_touched": False,
        "detail": "Compound-add dry-run audit cache is warming; no broker was touched.",
        "claim_boundary": COMPOUND_ADD_CLAIM_BOUNDARY,
    }


def _compound_add_order_dry_run_review_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_compound_add_order_dry_run_review",
        "generated_at": None,
        "review_status": "OPEN",
        "owner_review_status": "OPEN",
        "owner_accepted_at": None,
        "accepted_fingerprint": None,
        "current_fingerprint": "CACHE_WARMING",
        "compound_add_dry_run_review_clear_for_dispatch": False,
        "evidence_ready_for_owner_accept": False,
        "missing_requirements": ["COMPOUND_ADD_REVIEW_CACHE_WARMING"],
        "checks": [],
        "latest_compound_add_summary": {},
        "broker_truth_summary": {},
        "claim_boundary": COMPOUND_ADD_REVIEW_CLAIM_BOUNDARY,
        "next_action": "Compound-add dry-run review cache is warming; dispatch remains blocked.",
    }


def _compound_add_handoff_payload() -> dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(DEFAULT_COMPOUND_ADD_AUDIT_PATH).latest()
    payload = latest.get("payload") if isinstance(latest, dict) else {}
    review = build_compound_add_order_dry_run_review(dry_run_audit=latest or {})
    return build_compound_add_dispatch_handoff_status(payload if isinstance(payload, dict) else {}, review=review)


def _compound_add_handoff_warming() -> dict[str, Any]:
    return {
        "report_kind": COMPOUND_ADD_HANDOFF_REPORT_KIND,
        "status": STATUS_COMPOUND_ADD_HANDOFF_BLOCKED,
        "order_id": None,
        "decision_ref": None,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "dispatch_preview_only": True,
        "would_call_dispatch_if_owner_attempted": False,
        "missing_requirements": ["COMPOUND_ADD_HANDOFF_CACHE_WARMING"],
        "reason": "Compound-add handoff cache is warming.",
        "claim_boundary": COMPOUND_ADD_HANDOFF_CLAIM_BOUNDARY,
        "next_action": "Wait for compound-add handoff evidence to refresh before attempting dispatch.",
    }


class LiveOrderDryRunBody(BaseModel):
    order_id: str = Field(..., min_length=1)
    decision_ref: Optional[str] = None
    symbol: str = Field(..., min_length=1)
    direction: str = Field(..., min_length=1)
    volume: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)
    price: float = Field(default=0.0, ge=0)
    expected_loss_usd: Optional[float] = Field(default=None, ge=0)
    comment: str = "CAS_FOREX_DRY_RUN"
    live_telemetry: Optional[dict[str, Any]] = None
    account_snapshot: Optional[dict[str, Any]] = None
    equity_peak: Optional[float] = Field(default=None, gt=0)


class CompoundAddDryRunBody(BaseModel):
    parent_order_id: Optional[str] = None
    parent_decision_ref: Optional[str] = None
    parent_position: Optional[dict[str, Any]] = None
    broker_ticket: Optional[str] = None
    symbol: str = Field(..., min_length=1)
    direction: str = Field(..., min_length=1)
    add_order_id: str = Field(..., min_length=1)
    add_decision_ref: Optional[str] = None
    add_volume: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)
    position_entry: float = Field(..., gt=0)
    position_stop_loss: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)
    current_units: int = Field(default=1, ge=0)
    max_units: int = Field(default=4, ge=1)
    broker_grade_market_truth: bool = False
    cas_feature_map: Optional[dict[str, Any]] = None
    expected_loss_usd: Optional[float] = Field(default=None, ge=0)
    comment: str = "CAS_FOREX_ADD_DRY_RUN"
    live_telemetry: Optional[dict[str, Any]] = None
    account_snapshot: Optional[dict[str, Any]] = None
    equity_peak: Optional[float] = Field(default=None, gt=0)


class LiveOrderDryRunReviewAccept(BaseModel):
    notes: Optional[str] = None


class CompoundAddDryRunReviewAccept(BaseModel):
    notes: Optional[str] = None


class CompoundAddDispatchHandoffDispatch(BaseModel):
    confirm_owner_dispatch: bool = False
    notes: Optional[str] = None


class WasteEntryDispatchHandoffDispatch(BaseModel):
    confirm_owner_dispatch: bool = False
    notes: Optional[str] = None


@router.post("/order")
async def post_live_order_dry_run(body: LiveOrderDryRunBody) -> dict[str, Any]:
    """Rehearse a proposed live order without touching a broker bridge."""
    try:
        request = request_from_mapping(body.model_dump())
        return build_live_order_dry_run(
            request,
            live_telemetry=body.live_telemetry,
            account_snapshot=body.account_snapshot,
            equity_peak=body.equity_peak,
            audit=LiveOrderDryRunAuditLog(DEFAULT_AUDIT_PATH),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/compound-add-order")
async def post_compound_add_order_dry_run(body: CompoundAddDryRunBody) -> dict[str, Any]:
    """Rehearse a pyramid/add order without touching a broker bridge."""
    try:
        request = compound_add_request_from_mapping(body.model_dump())
        return build_compound_add_order_dry_run(
            request,
            live_telemetry=body.live_telemetry,
            account_snapshot=body.account_snapshot,
            equity_peak=body.equity_peak,
            audit=LiveOrderDryRunAuditLog(DEFAULT_COMPOUND_ADD_AUDIT_PATH),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/latest")
async def get_latest_live_order_dry_run() -> dict[str, Any]:
    """Return the latest live-order dry-run audit row, if one exists."""
    return cache_first_payload(
        "live_order_dry_run_latest",
        builder=_latest_live_order_dry_run_payload,
        fallback=_latest_live_order_dry_run_warming,
        ttl_seconds=10.0,
    )


@router.get("/waste-entry-order/dispatch-handoff")
async def get_waste_entry_dispatch_handoff_status() -> dict[str, Any]:
    """Read-only status for the latest WASTE real-candle entry dispatch handoff."""
    return cache_first_payload(
        "waste_entry_dispatch_handoff",
        builder=_waste_entry_handoff_payload,
        fallback=_waste_entry_handoff_warming,
        ttl_seconds=10.0,
    )


@router.get("/waste-entry-order/pilot-promotion")
async def get_waste_entry_pilot_promotion_status() -> dict[str, Any]:
    """Read-only readiness gate for promoting WASTE evidence into a tiny pilot."""
    return cache_first_payload(
        "waste_entry_pilot_promotion",
        builder=_waste_entry_pilot_promotion_payload,
        fallback=_waste_entry_pilot_promotion_warming,
        ttl_seconds=10.0,
    )


@router.post("/waste-entry-order/dispatch-handoff/dispatch")
async def post_waste_entry_dispatch_handoff_dispatch(
    body: WasteEntryDispatchHandoffDispatch,
    confirm: bool = Query(default=False),
) -> dict[str, Any]:
    """Owner-confirmed attempt to hand an accepted WASTE entry intent to dispatch.

    This endpoint does not approve a trade by itself. It requires explicit owner
    dispatch confirmation, re-checks the current owner ACCEPT fingerprint,
    requires a second ``?confirm=true`` when live trading is authorized, then
    sends the exact WASTE dry-run intent through the normal dispatch chokepoint.
    Dispatch still enforces live, edge, pilot, risk, emergency-stop, audit, and
    broker-bridge gates.
    """
    if not body.confirm_owner_dispatch:
        raise HTTPException(
            status_code=400,
            detail="confirm_owner_dispatch=true is required before WASTE entry handoff dispatch",
        )

    latest = LiveOrderDryRunAuditLog(DEFAULT_AUDIT_PATH).latest()
    payload = latest.get("payload") if isinstance(latest, dict) else {}
    dry_run = payload if isinstance(payload, dict) else {}
    review = build_live_order_dry_run_review(dry_run_audit=latest or {})
    handoff = build_waste_entry_dispatch_handoff_status(dry_run, review=review)
    if not bool(handoff.get("would_call_dispatch_if_owner_attempted", False)):
        blocked = dict(handoff)
        blocked.update(
            {
                "dispatch_attempted": False,
                "owner_dispatch_confirmed": True,
                "notes": body.notes or "",
                "next_action": "Resolve the WASTE entry handoff blockers before attempting dispatch.",
            }
        )
        return blocked

    if runtime_gates.is_authorized("live_trading") and not confirm:
        return {
            "report_kind": "cas_forex_waste_entry_dispatch_handoff",
            "status": "CONFIRM_REQUIRED",
            "order_id": handoff.get("order_id"),
            "decision_ref": handoff.get("decision_ref"),
            "broker_touched": False,
            "dispatched_to_bridge": False,
            "dispatch_attempted": False,
            "owner_dispatch_confirmed": True,
            "live_trading_authorized": True,
            "handoff_status": handoff,
            "notes": body.notes or "",
            "detail": (
                "Live trading is owner-authorized; this WASTE entry handoff could "
                "place a real order. Re-POST with ?confirm=true to dispatch through "
                "the normal live, edge, pilot, risk, emergency-stop, audit, and broker gates."
            ),
        }

    result = dispatch_waste_entry_from_dry_run(
        dry_run,
        bridge_factory=lambda: select_bridge(default_config),
        config=default_config,
    )
    response = dict(result)
    response.update(
        {
            "dispatch_attempted": True,
            "owner_dispatch_confirmed": True,
            "live_trading_authorized": runtime_gates.is_authorized("live_trading"),
            "handoff_status": handoff,
            "notes": body.notes or "",
        }
    )
    return response


@router.get("/compound-add-order/latest")
async def get_latest_compound_add_order_dry_run() -> dict[str, Any]:
    """Return the latest compound-add dry-run audit row, if one exists."""
    return cache_first_payload(
        "compound_add_order_dry_run_latest",
        builder=_latest_compound_add_order_dry_run_payload,
        fallback=_latest_compound_add_order_dry_run_warming,
        ttl_seconds=10.0,
    )


@router.get("/compound-add-order/review")
async def get_compound_add_order_dry_run_review() -> dict[str, Any]:
    """Return owner review status for the latest passing compound-add dry-run evidence."""
    return cache_first_payload(
        "compound_add_order_dry_run_review",
        builder=build_compound_add_order_dry_run_review,
        fallback=_compound_add_order_dry_run_review_warming,
        ttl_seconds=10.0,
    )


@router.get("/compound-add-order/dispatch-handoff")
async def get_compound_add_dispatch_handoff_status() -> dict[str, Any]:
    """Read-only status for the latest WASTE compound-add dispatch handoff."""
    return cache_first_payload(
        "compound_add_dispatch_handoff",
        builder=_compound_add_handoff_payload,
        fallback=_compound_add_handoff_warming,
        ttl_seconds=10.0,
    )


@router.post("/compound-add-order/dispatch-handoff/dispatch")
async def post_compound_add_dispatch_handoff_dispatch(
    body: CompoundAddDispatchHandoffDispatch,
    confirm: bool = Query(default=False),
) -> dict[str, Any]:
    """Owner-confirmed attempt to hand the accepted compound-add intent to dispatch.

    This endpoint does not approve a trade by itself. It requires an explicit
    dispatch confirmation in the body, re-checks the current owner ACCEPT
    fingerprint, requires a second ``?confirm=true`` when live trading is
    authorized, then sends the exact dry-run intent through the normal dispatch
    chokepoint. Dispatch still enforces live, edge, pilot, risk, emergency-stop,
    audit, and broker-bridge gates.
    """
    if not body.confirm_owner_dispatch:
        raise HTTPException(
            status_code=400,
            detail="confirm_owner_dispatch=true is required before compound-add handoff dispatch",
        )

    latest = LiveOrderDryRunAuditLog(DEFAULT_COMPOUND_ADD_AUDIT_PATH).latest()
    payload = latest.get("payload") if isinstance(latest, dict) else {}
    add_dry_run = payload if isinstance(payload, dict) else {}
    review = build_compound_add_order_dry_run_review(dry_run_audit=latest or {})
    handoff = build_compound_add_dispatch_handoff_status(add_dry_run, review=review)
    if not bool(handoff.get("would_call_dispatch_if_owner_attempted", False)):
        blocked = dict(handoff)
        blocked.update(
            {
                "dispatch_attempted": False,
                "owner_dispatch_confirmed": True,
                "notes": body.notes or "",
                "next_action": (
                    "Resolve the compound-add handoff blockers before attempting dispatch."
                ),
            }
        )
        return blocked

    if runtime_gates.is_authorized("live_trading") and not confirm:
        return {
            "report_kind": "cas_forex_waste_compound_add_dispatch_handoff",
            "status": "CONFIRM_REQUIRED",
            "order_id": handoff.get("order_id"),
            "decision_ref": handoff.get("decision_ref"),
            "broker_touched": False,
            "dispatched_to_bridge": False,
            "dispatch_attempted": False,
            "owner_dispatch_confirmed": True,
            "live_trading_authorized": True,
            "handoff_status": handoff,
            "notes": body.notes or "",
            "detail": (
                "Live trading is owner-authorized; this compound-add handoff could "
                "place a real order. Re-POST with ?confirm=true to dispatch through "
                "the normal live, edge, pilot, risk, emergency-stop, audit, and broker gates."
            ),
        }

    result = dispatch_compound_add_from_dry_run(
        add_dry_run,
        bridge_factory=lambda: select_bridge(default_config),
        config=default_config,
    )
    response = dict(result)
    response.update(
        {
            "dispatch_attempted": True,
            "owner_dispatch_confirmed": True,
            "live_trading_authorized": runtime_gates.is_authorized("live_trading"),
            "handoff_status": handoff,
            "notes": body.notes or "",
        }
    )
    return response


@router.post("/compound-add-order/review/accept")
async def post_compound_add_order_dry_run_review_accept(
    body: CompoundAddDryRunReviewAccept,
    confirm_owner_accept: bool = False,
) -> dict[str, Any]:
    """Owner ACCEPT the current passing compound-add dry-run + broker-position fingerprint."""
    try:
        result = accept_compound_add_order_dry_run_review(
            notes=body.notes or "",
            confirm_owner_accept=confirm_owner_accept,
        )
        invalidate_live_money_gate_caches()
        return result
    except CompoundAddOrderDryRunReviewError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/compound-add-order/review/reset")
async def post_compound_add_order_dry_run_review_reset(reason: str = "OWNER_RESET") -> dict[str, Any]:
    """Reset compound-add dry-run review to OPEN."""
    result = reset_compound_add_order_dry_run_review(reason=reason)
    invalidate_live_money_gate_caches()
    return result


@router.get("/review")
async def get_live_order_dry_run_review() -> dict[str, Any]:
    """Return owner review status for the latest passing dry-run evidence."""
    return cache_first_payload(
        "live_order_dry_run_review",
        builder=build_live_order_dry_run_review,
        fallback=_live_order_dry_run_review_warming,
        ttl_seconds=10.0,
    )


@router.post("/review/accept")
async def post_live_order_dry_run_review_accept(
    body: LiveOrderDryRunReviewAccept,
    confirm_owner_accept: bool = False,
) -> dict[str, Any]:
    """Owner ACCEPT the current passing dry-run + broker-truth fingerprint."""
    try:
        result = accept_live_order_dry_run_review(
            notes=body.notes or "",
            confirm_owner_accept=confirm_owner_accept,
        )
        invalidate_live_money_gate_caches()
        return result
    except LiveOrderDryRunReviewError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/review/reset")
async def post_live_order_dry_run_review_reset(reason: str = "OWNER_RESET") -> dict[str, Any]:
    """Reset live-order dry-run review to OPEN."""
    result = reset_live_order_dry_run_review(reason=reason)
    invalidate_live_money_gate_caches()
    return result
