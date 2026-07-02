"""HTTP routes for the gated order / agent dispatch loop.

Thin wrappers around ``cas_forex.agent_dispatch``. ``GET /latest`` returns the
most recent gated dispatch cycle (read-only); ``POST /run`` runs one now,
pulling the agent cycle's real route intents through the overseer and the
live-trading + risk gate into the configured broker bridge (paper by default).

The route changes no real-money posture: with default config the broker is the
paper simulator and the live-trading gate stays NOT LICENSED, so a live order is
never placed unless the owner has authorized live trading + configured a broker.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..route_cache import cache_first_payload
from cas_forex import runtime_gates
from cas_forex.agent_dispatch import (
    DEFAULT_OUTPUT_DIR,
    run_agent_dispatch_cycle,
    write_agent_dispatch_cycle_report,
)
from cas_forex.broker_truth_monitor import load_latest_broker_truth_monitor_report
from cas_forex.order_attempt_audit import (
    OrderAttemptAuditError,
    build_order_attempt_audit_status,
    default_order_attempt_audit_store,
)
from cas_forex.order_attempt_recovery_packet import build_order_attempt_recovery_packet

router = APIRouter()


@router.get("/latest")
async def get_latest_dispatch_cycle() -> dict[str, Any]:
    """Return the most recent gated agent dispatch cycle report (read-only)."""
    candidates = sorted(DEFAULT_OUTPUT_DIR.glob("agent-dispatch-cycle-*-report.json"))
    if not candidates:
        return {
            "report_kind": "cas_forex_agent_dispatch_cycle",
            "status": "no_dispatch_cycle_yet",
            "detail": "No agent dispatch cycle has been run yet. POST /run to produce one.",
        }
    try:
        return json.loads(candidates[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "report_kind": "cas_forex_agent_dispatch_cycle",
            "status": "unreadable",
            "detail": str(exc),
        }


@router.get("/audit")
async def get_order_attempt_audit() -> dict[str, Any]:
    """Return durable order-attempt audit status (read-only)."""
    return cache_first_payload(
        "order_attempt_audit",
        builder=build_order_attempt_audit_status,
        fallback=_order_attempt_audit_warming,
        ttl_seconds=30.0,
    )


@router.get("/audit/recovery-packet")
async def get_order_attempt_recovery_packet() -> dict[str, Any]:
    """Return owner-action packet for unresolved real order attempts."""
    return cache_first_payload(
        "order_attempt_recovery_packet",
        builder=_build_order_attempt_recovery_packet_payload,
        fallback=_order_attempt_recovery_warming,
        ttl_seconds=30.0,
    )


def _build_order_attempt_recovery_packet_payload() -> dict[str, Any]:
    try:
        broker_truth = load_latest_broker_truth_monitor_report()
    except Exception:
        broker_truth = {}
    return build_order_attempt_recovery_packet(
        order_attempt_status=build_order_attempt_audit_status(),
        broker_truth_report=broker_truth,
    )


def _order_attempt_audit_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_order_attempt_audit",
        "status": "WARMING",
        "attempt_count": 0,
        "unresolved_real_attempt_count": 0,
        "synthetic_test_like_count": 0,
        "broker_review_required_count": 0,
        "next_action": "Order-attempt audit cache is warming.",
    }


def _order_attempt_recovery_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_order_attempt_recovery_packet",
        "status": "WARMING",
        "recovery_clear_for_live": False,
        "can_reconcile_unresolved_attempts": False,
        "unresolved_real_attempt_count": 0,
        "synthetic_test_like_count": 0,
        "broker_review_required_count": 0,
        "next_action": "Order-attempt recovery cache is warming.",
    }


@router.post("/run")
async def post_run_dispatch_cycle(confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Run one gated agent dispatch cycle now and return the report.

    Pulls the agent cycle's real route intents, runs them through the overseer
    and the live-trading + risk gate into the configured broker bridge, then
    writes a JSON artifact. The configured bridge is the paper simulator unless
    the owner has authorized live trading — the gates are enforced regardless.

    When live trading is owner-authorized (so this cycle could place real
    orders), an explicit ``?confirm=true`` is required; otherwise the run is
    paper and proceeds.
    """
    if runtime_gates.is_authorized("live_trading") and not confirm:
        return {
            "report_kind": "cas_forex_agent_dispatch_cycle",
            "status": "CONFIRM_REQUIRED",
            "detail": (
                "Live trading is owner-authorized; this run could place real "
                "orders. Re-POST with ?confirm=true to execute."
            ),
        }
    cycle = run_agent_dispatch_cycle(enforce_receipt_gates=True)
    paths = write_agent_dispatch_cycle_report(cycle)
    payload = cycle.to_dict()
    payload["artifact_path"] = str(paths["json"])
    return payload


class ManualOrder(BaseModel):
    """An owner-initiated order from the Trading Windows cockpit.

    SL/TP are optional from the UI; when omitted they are auto-derived from the
    current quote so the order is always risk-bounded (the broker schema requires
    both). This routes through the SAME gated dispatch as every other order, so it
    is paper-safe by default and can only reach a live broker when the owner has
    authorized live trading.
    """

    symbol: str
    direction: str  # BUY/SELL or LONG/SHORT
    lots: float = Field(gt=0)
    sl: Optional[float] = Field(default=None, gt=0)
    tp: Optional[float] = Field(default=None, gt=0)


class ReconcileUnresolvedAttempt(BaseModel):
    attempt_id: str = Field(..., min_length=1)
    notes: Optional[str] = None
    broker_truth_report: Optional[dict[str, Any]] = None


@router.post("/audit/reconcile-unresolved")
async def post_reconcile_unresolved_attempt(
    body: ReconcileUnresolvedAttempt,
    confirm_owner_reconcile: bool = Query(default=False),
) -> dict[str, Any]:
    """Owner-reconcile one unresolved real order attempt against clean broker truth.

    This finalizes the audit record so recovery no longer treats it as an open
    crash-window attempt. It does not create a broker outcome, retry the order,
    place/close anything, or move money.
    """
    try:
        broker_truth = body.broker_truth_report or load_latest_broker_truth_monitor_report()
        return default_order_attempt_audit_store().reconcile_unresolved_real_attempt(
            body.attempt_id,
            broker_truth_report=broker_truth,
            notes=body.notes or "",
            confirm_owner_reconcile=confirm_owner_reconcile,
        )
    except Exception as exc:
        if isinstance(exc, OrderAttemptAuditError):
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reconcile unresolved real order attempt: {type(exc).__name__}: {exc}",
        ) from exc


@router.post("/manual")
async def post_manual_order(body: ManualOrder, confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Dispatch one owner-initiated order through the gated dispatch loop.

    Paper-safe by default. If live trading is owner-authorized, an explicit
    ``?confirm=true`` is required before a real order is dispatched.
    """
    from cas_forex.instruments import price_unit_size, round_price
    from cas_forex.market_data.connector import get_connector
    from cas_forex.order_dispatch import TradeIntent, dispatch_intents
    from cas_forex.time_utils import utc_now

    symbol = body.symbol.upper()
    direction = body.direction.upper()
    is_long = direction in {"BUY", "LONG"}

    if runtime_gates.is_authorized("live_trading") and not confirm:
        return {
            "report_kind": "cas_forex_order_dispatch",
            "status": "CONFIRM_REQUIRED",
            "detail": (
                "Live trading is owner-authorized; this order could be placed for "
                "real. Re-POST with ?confirm=true to execute."
            ),
        }

    # Current price for market entry + auto SL/TP when the owner didn't set them.
    try:
        snap = get_connector().fetch_snapshot(symbol)
        mid = (snap.bid + snap.ask) / 2.0
    except Exception:
        from cas_forex.instruments import default_mid

        mid = default_mid(symbol)

    unit = price_unit_size(symbol)
    # Default risk geometry: 50 units SL, 100 units TP, on the correct side.
    sl = body.sl
    tp = body.tp
    if sl is None:
        sl = round_price(symbol, mid - 50 * unit if is_long else mid + 50 * unit)
    if tp is None:
        tp = round_price(symbol, mid + 100 * unit if is_long else mid - 100 * unit)

    order_id = f"manual-{symbol.replace('/', '')}-{int(utc_now().timestamp())}"
    intent = TradeIntent(
        order_id=order_id,
        decision_ref=order_id,
        symbol=symbol,
        direction="LONG" if is_long else "SHORT",
        volume=float(body.lots),
        stop_loss=float(sl),
        take_profit=float(tp),
        comment="CAS_FOREX_MANUAL",
        ai_action="MANUAL",
    )
    report = dispatch_intents([intent])
    payload = report.to_dict()
    payload["manual_order"] = {
        "symbol": symbol,
        "direction": "LONG" if is_long else "SHORT",
        "lots": float(body.lots),
        "stop_loss": float(sl),
        "take_profit": float(tp),
        "auto_sl": body.sl is None,
        "auto_tp": body.tp is None,
    }
    return payload
