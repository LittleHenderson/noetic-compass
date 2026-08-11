"""HTTP routes for the gated order / agent dispatch loop.

Thin wrappers around ``cas_forex.agent_dispatch``. ``GET /latest`` returns the
most recent gated dispatch cycle (read-only); ``POST /run`` runs one now,
pulling the agent cycle's real route intents through the overseer and the
live-trading + risk gate into the configured broker bridge (paper by default).

The route changes no real-money posture on its own: with default config the
broker is the paper simulator, and a live order is possible only after the
owner arms live trading and configures a live-capable bridge.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..route_cache import cache_first_payload
from cas_forex import runtime_gates
from cas_forex.agent_dispatch import (
    DEFAULT_OUTPUT_DIR,
    load_latest_agent_dispatch_cycle_report,
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
LIVE_ORDER_CONFIRM_PHRASE = "CONFIRM LIVE ORDER"
MANUAL_ORDER_JOURNAL_REASON_MIN_CHARS = 20
MANUAL_ORDER_JOURNAL_PROMPT = (
    "Before placing a manual order, record why this is not revenge trading, "
    "FOMO, overconfidence, or chasing losses; include the invalidation condition."
)
_COMMON_MT5_TERMINAL_PATHS = (
    r"C:\Program Files\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
)


def _discover_mt5_terminal_path() -> str | None:
    from cas_forex.config import config

    configured = str(getattr(config, "mt5_path", "") or "").strip()
    if configured and Path(configured).exists():
        return configured
    for candidate in _COMMON_MT5_TERMINAL_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def _mt5_market_truth_enabled(auto_path: str | None = None) -> bool:
    from cas_forex.config import config

    provider = str(getattr(config, "market_data_provider", "") or "").upper()
    if provider in {"MT5", "BROKER", "BROKER_MT5", "MT5_TERMINAL"}:
        return True
    if not bool(getattr(config, "prefer_mt5", True)):
        return False
    return bool(getattr(config, "mt5_login", 0) or getattr(config, "mt5_path", None) or auto_path)


def _has_connector_kind(candidates: list[Any], connector: Any) -> bool:
    return any(type(candidate) is type(connector) for candidate in candidates)


def _quote_connector_candidates() -> list[Any]:
    from cas_forex.market_data.connector import (
        MT5TerminalMarketDataConnector,
        YFinanceConnector,
        get_connector,
    )

    candidates: list[Any] = []
    primary = get_connector()
    candidates.append(primary)
    mt5_auto_path = _discover_mt5_terminal_path()
    if _mt5_market_truth_enabled(mt5_auto_path):
        mt5_connector = MT5TerminalMarketDataConnector(mt5_path=mt5_auto_path)
        if not _has_connector_kind(candidates, mt5_connector):
            candidates.append(mt5_connector)
    if not any(isinstance(candidate, YFinanceConnector) for candidate in candidates):
        candidates.append(YFinanceConnector())
    return candidates


def _quote_source_name(connector: Any | None) -> str | None:
    if connector is None:
        return None
    connector_name = type(connector).__name__.upper()
    if "MT5" in connector_name:
        return "mt5"
    if "YFINANCE" in connector_name:
        return "yfinance"
    if "OANDA" in connector_name:
        return "oanda"
    return connector_name.lower() or None


def _quote_feed_label(connector: Any | None, *, fallback_reason: str | None = None) -> str | None:
    if connector is None:
        return None
    if bool(getattr(connector, "broker_grade_market_truth", False)):
        label = "read-only MT5 broker-terminal quote"
    elif type(connector).__name__ == "YFinanceConnector":
        label = "near-real-time delayed quote"
    elif type(connector).__name__ == "OANDARestConnector":
        label = "account-scoped provider quote"
    else:
        label = "market data connector quote"
    if fallback_reason:
        return f"{label}; {fallback_reason}"
    return label


def _build_manual_quote_snapshot(symbol: str) -> dict[str, Any]:
    from cas_forex.instruments import default_mid

    attempts: list[dict[str, Any]] = []
    selected_connector: Any | None = None
    selected_snapshot: Any | None = None
    primary_connector_name = ""
    primary_failure = ""

    for index, connector in enumerate(_quote_connector_candidates()):
        connector_name = type(connector).__name__
        if index == 0:
            primary_connector_name = connector_name
        try:
            snapshot = connector.fetch_snapshot(symbol)
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            if index == 0:
                primary_failure = detail
            attempts.append(
                {
                    "connector": connector_name,
                    "status": "SNAPSHOT_ERROR",
                    "detail": detail,
                }
            )
            continue

        synthetic_fallback = bool(getattr(snapshot, "synthetic_fallback", False))
        detail = str(getattr(connector, "last_error", "") or "").strip() or None
        if index == 0 and detail:
            primary_failure = detail
        attempts.append(
            {
                "connector": connector_name,
                "status": "QUOTE_OK" if not synthetic_fallback else "SYNTHETIC_FALLBACK",
                "detail": detail,
                "synthetic_fallback": synthetic_fallback,
                "broker_grade_market_truth": bool(getattr(connector, "broker_grade_market_truth", False)),
                "is_market_open": bool(getattr(snapshot, "is_market_open", True)),
            }
        )
        if synthetic_fallback:
            continue
        selected_connector = connector
        selected_snapshot = snapshot
        break

    fallback_used = len(attempts) > 1
    if selected_snapshot is None:
        return {
            "mid": default_mid(symbol),
            "quote_snapshot": None,
            "quote_source": None,
            "quote_feed_label": "no usable connector quote",
            "quote_connector_attempts": attempts,
            "quote_fallback_used": fallback_used,
            "quote_error": primary_failure or "no connector produced a usable non-synthetic quote",
        }

    mid = (float(selected_snapshot.bid) + float(selected_snapshot.ask)) / 2.0
    fallback_reason = None
    if fallback_used and type(selected_connector).__name__ != primary_connector_name:
        fallback_reason = primary_failure or "configured primary provider could not serve this symbol"
    return {
        "mid": mid,
        "quote_snapshot": {
            "symbol": getattr(selected_snapshot, "symbol", symbol),
            "bid": float(getattr(selected_snapshot, "bid", 0.0)),
            "ask": float(getattr(selected_snapshot, "ask", 0.0)),
            "is_market_open": bool(getattr(selected_snapshot, "is_market_open", True)),
            "session": str(getattr(selected_snapshot, "session", "UNKNOWN")),
            "timestamp": str(getattr(selected_snapshot, "timestamp", "")),
            "source": "manual_order_quote",
            "quote_source": _quote_source_name(selected_connector),
            "broker_grade_market_truth": bool(getattr(selected_connector, "broker_grade_market_truth", False)),
        },
        "quote_source": _quote_source_name(selected_connector),
        "quote_feed_label": _quote_feed_label(selected_connector, fallback_reason=fallback_reason),
        "quote_connector_attempts": attempts,
        "quote_fallback_used": fallback_used,
        "quote_error": None,
    }


def _live_order_confirmation_matches(confirm_phrase: str) -> bool:
    return (confirm_phrase or "").strip() == LIVE_ORDER_CONFIRM_PHRASE


def _live_order_confirm_required(
    *,
    confirm: bool,
    confirm_phrase: str,
    report_kind: str,
    detail: str,
) -> Optional[dict[str, Any]]:
    if not runtime_gates.is_authorized("live_trading"):
        return None
    if confirm and _live_order_confirmation_matches(confirm_phrase):
        return None
    return {
        "report_kind": report_kind,
        "status": "CONFIRM_REQUIRED",
        "live_trading_authorized": True,
        "broker_touched": False,
        "dispatched_to_bridge": False,
        "need_confirmation": LIVE_ORDER_CONFIRM_PHRASE,
        "confirm_phrase": LIVE_ORDER_CONFIRM_PHRASE,
        "detail": (
            f"{detail} Re-POST with ?confirm=true and "
            f'confirm_phrase="{LIVE_ORDER_CONFIRM_PHRASE}" to execute.'
        ),
    }


def _manual_order_journal_review(reason: Any) -> dict[str, Any]:
    text = str(reason or "").strip()
    lowered = text.lower()
    blockers: list[str] = []
    if len(text) < MANUAL_ORDER_JOURNAL_REASON_MIN_CHARS:
        blockers.append(f"reason must be at least {MANUAL_ORDER_JOURNAL_REASON_MIN_CHARS} characters")
    if "no reason" in lowered:
        blockers.append("reason cannot say no reason was given")
    return {
        "report_kind": "cas_forex_manual_order_anti_impulse_journal",
        "required": True,
        "satisfied": not blockers,
        "reason_length": len(text),
        "minimum_reason_length": MANUAL_ORDER_JOURNAL_REASON_MIN_CHARS,
        "blockers": blockers,
        "prompt": MANUAL_ORDER_JOURNAL_PROMPT,
        "claim_boundary": (
            "Manual-order journaling gates owner-initiated manual dispatch only. "
            "It does not authorize live trading, place orders by itself, or prove edge."
        ),
    }


@router.get("/latest")
async def get_latest_dispatch_cycle() -> dict[str, Any]:
    """Return the most recent gated agent dispatch cycle report (read-only)."""
    payload = load_latest_agent_dispatch_cycle_report(output_dir=DEFAULT_OUTPUT_DIR)
    if payload is None:
        return {
            "report_kind": "cas_forex_agent_dispatch_cycle",
            "status": "no_dispatch_cycle_yet",
            "detail": (
                "No latest dispatch pointer exists yet. The next dispatch cycle will "
                "create it without scanning the immutable receipt archive."
            ),
        }
    return payload


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
        "real_attempt_count": 0,
        "unresolved_attempt_count": 0,
        "unresolved_real_attempt_count": 0,
        "executed_count": 0,
        "duplicate_suppressed_count": 0,
        "near_duplicate_suppressed_count": 0,
        "has_unresolved_real_attempt": False,
        "synthetic_test_like_count": 0,
        "broker_review_required_count": 0,
        "idempotency_policy": {
            "report_kind": "cas_forex_order_idempotency_policy",
            "exact_retry_key": "decision_ref|order_id",
            "near_duplicate_key": (
                "strategy_id|ai_action|symbol|direction|order_type|volume|price|stop_loss|take_profit"
            ),
            "near_duplicate_window_seconds": 600,
            "near_duplicate_scope": "automation_only",
            "manual_orders_excluded_from_near_duplicate_block": True,
            "compound_or_pyramid_adds_excluded_from_near_duplicate_block": True,
            "unresolved_real_attempt_policy": "block retry until owner reconciles against fresh broker truth",
        },
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
async def post_run_dispatch_cycle(
    confirm: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Run one gated agent dispatch cycle now and return the report.

    Pulls the agent cycle's real route intents, runs them through the overseer
    and the live-trading + risk gate into the configured broker bridge, then
    writes a JSON artifact. The configured bridge is the paper simulator unless
    the owner has authorized live trading — the gates are enforced regardless.

    When live trading is owner-authorized (so this cycle could place real
    orders), typed confirmation is required; otherwise the run is paper and
    proceeds.
    """
    pending = _live_order_confirm_required(
        confirm=confirm,
        confirm_phrase=confirm_phrase,
        report_kind="cas_forex_agent_dispatch_cycle",
        detail="Live trading is owner-authorized; this run could place real orders.",
    )
    if pending is not None:
        return pending
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
    journal_reason: Optional[str] = None


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
async def post_manual_order(
    body: ManualOrder,
    confirm: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Dispatch one owner-initiated order through the gated dispatch loop.

    Paper-safe by default. If live trading is owner-authorized, typed
    confirmation is required before a real order is dispatched.
    """
    from cas_forex.instruments import canonical_symbol, price_unit_size, round_price
    from cas_forex.order_dispatch import TradeIntent, dispatch_intents
    from cas_forex.time_utils import utc_now

    try:
        symbol = canonical_symbol(body.symbol)
    except ValueError:
        symbol = body.symbol.upper()
    direction = body.direction.upper()
    is_long = direction in {"BUY", "LONG"}

    journal = _manual_order_journal_review(body.journal_reason)
    if not journal["satisfied"]:
        return {
            "report_kind": "cas_forex_order_dispatch",
            "status": "JOURNAL_REQUIRED",
            "broker_touched": False,
            "dispatched_to_bridge": False,
            "manual_order_journal": journal,
            "need_journal_reason": True,
            "detail": "Manual order blocked until an anti-impulse journal reason is supplied.",
        }

    pending = _live_order_confirm_required(
        confirm=confirm,
        confirm_phrase=confirm_phrase,
        report_kind="cas_forex_order_dispatch",
        detail="Live trading is owner-authorized; this order could be placed for real.",
    )
    if pending is not None:
        return pending

    # Current price for market entry + auto SL/TP when the owner didn't set them.
    quote_context = _build_manual_quote_snapshot(symbol)
    quote_snapshot = quote_context.get("quote_snapshot") if isinstance(quote_context.get("quote_snapshot"), dict) else None
    mid = float(quote_context.get("mid"))

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
        manual_order_journal=journal,
    )
    live_telemetry = {"market_snapshot": quote_snapshot} if quote_snapshot is not None else None
    report = dispatch_intents([intent], live_telemetry=live_telemetry)
    payload = report.to_dict()
    payload["manual_order"] = {
        "symbol": symbol,
        "direction": "LONG" if is_long else "SHORT",
        "lots": float(body.lots),
        "stop_loss": float(sl),
        "take_profit": float(tp),
        "auto_sl": body.sl is None,
        "auto_tp": body.tp is None,
        "quote_market_open": quote_snapshot.get("is_market_open") if quote_snapshot else None,
        "quote_source": quote_context.get("quote_source"),
        "quote_feed_label": quote_context.get("quote_feed_label"),
        "quote_fallback_used": bool(quote_context.get("quote_fallback_used")),
        "quote_connector_attempts": list(quote_context.get("quote_connector_attempts") or []),
        "quote_error": quote_context.get("quote_error"),
    }
    payload["manual_order_journal"] = journal
    return payload
