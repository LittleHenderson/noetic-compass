"""Order dispatch loop — the engine between a trade signal and a broker bridge.

This is the loop that was missing: the broker bridges (``MT5Bridge`` /
``SimulatedBrokerBridge`` / ``MT4EABridge``) define *how* to execute an order,
the gates (``runtime_gates`` + ``pre_execution_risk_gate``) define *whether* an
order is allowed, but nothing actually walked a signal through the gates and
into the bridge. ``dispatch_intents`` is that walk:

    TradeIntent -> BrokerOrderRequest (schema/geometry validation)
                -> execution_guard.guarded_place_order
                     (live-trading gate if live_mode, then pre-execution risk gate)
                -> bridge.execute_order
                -> AccountLedgerEvent

It is paper-first by design. With no bridge supplied it uses
``broker.get_bridge()``, which returns the configured paper bridge
(``SimulatedBrokerBridge`` by default) unless the owner has authorized live
trading and configured credentials. Going live is therefore a config/flag swap
on top of a loop that is already proven against the paper broker -- the same
gate chain runs in paper mode, so the safety path is exercised for real before
any real money is at risk.

The loop is non-raising at the per-intent level: each intent yields a
``DispatchResult`` with an explicit status, so a single blocked or rejected
order never aborts the batch. Every result carries the gate decision and the
broker outcome, so the whole path (signal -> gate -> dispatch -> fill -> ledger)
is traceable from the report alone.

Boundary: this engine can only ever dispatch an order the gates already allow.
In live mode the live-trading gate is re-asserted at the dispatch chokepoint, so
a real-money order can never be placed without explicit owner authorization +
credentials + broker config. In paper mode the same risk caps apply, so the
limits protect demo dispatch too.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping, Optional, Sequence

from cas_forex.account_ledger import AccountLedgerEvent, stable_ledger_id
from cas_forex.execution_guard import ExecutionBlocked
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderOutcome, OrderType
from cas_forex.time_utils import utc_now

CLAIM_BOUNDARY = (
    "The order dispatch loop walks a signal through the live-trading gate and "
    "the pre-execution risk gate, then into the configured broker bridge. By "
    "default it dispatches to the paper broker (SimulatedBrokerBridge); it can "
    "only reach a live broker after the owner-controlled live-trading gate is "
    "authorized (enable flag + credentials + broker config). Explicit compound/"
    "pyramid add intents also require a current owner ACCEPT for the exact "
    "compound-add dry-run fingerprint before any broker bridge is touched. It "
    "never sizes or picks trades on its own and enables no real-money capability "
    "by itself."
)

# Per-intent dispatch statuses.
STATUS_REJECTED_PRECHECK = "REJECTED_PRECHECK"  # order failed schema/geometry validation
STATUS_BLOCKED_LIVE_GATE = "BLOCKED_LIVE_GATE"  # live-trading gate not authorized
STATUS_BLOCKED_COMPOUND_ADD_REVIEW = "BLOCKED_COMPOUND_ADD_REVIEW"  # pyramid add owner review missing/mismatched
STATUS_BLOCKED_RISK = "BLOCKED_RISK"  # pre-execution risk cap breach
STATUS_OVERSEER_REJECTED = "OVERSEER_REJECTED"  # agent overseer rejected before dispatch
STATUS_DISPATCH_ERROR = "DISPATCH_ERROR"  # bridge raised / unusable; never reached a fill

COMPOUND_ADD_ACTIONS = frozenset(
    {
        "COMPOUND_ADD",
        "PYRAMID_ADD",
        "WASTE_COMPOUND_ADD",
        "WASTE_PYRAMID_ADD",
        "ADD_TO_WINNER",
        "CAS_FOREX_ADD",
        "CAS_FOREX_ADD_DRY_RUN",
    }
)


@dataclass(frozen=True)
class TradeIntent:
    """A normalized, broker-agnostic trade signal ready for dispatch.

    The fields are the minimum a broker order needs. SL/TP are required (the
    schema rejects an order without them), which keeps every dispatched order
    risk-bounded by construction.
    """

    order_id: str
    decision_ref: str
    symbol: str
    direction: str  # "LONG"/"SHORT" or "BUY"/"SELL"
    volume: float
    stop_loss: float
    take_profit: float
    price: float = 0.0  # 0.0 => market order
    order_type: str = "MARKET"
    comment: str = "CAS_FOREX_AUTO"
    strategy_id: Optional[str] = None
    ai_action: str = "DISPATCH"
    expected_loss_usd: Optional[float] = None

    def resolved_direction(self) -> Direction:
        token = str(self.direction).strip().upper()
        if token in {"LONG", "BUY"}:
            return Direction.LONG
        if token in {"SHORT", "SELL"}:
            return Direction.SHORT
        raise ValueError(f"Unrecognized direction {self.direction!r}")

    def to_order(self) -> BrokerOrderRequest:
        """Build the broker order. Raises on invalid geometry/schema."""
        return BrokerOrderRequest(
            order_id=self.order_id,
            decision_ref=self.decision_ref,
            symbol=self.symbol,
            order_type=OrderType(str(self.order_type).upper()),
            direction=self.resolved_direction(),
            volume=float(self.volume),
            price=float(self.price),
            stop_loss=float(self.stop_loss),
            take_profit=float(self.take_profit),
            comment=self.comment[:27],
        )

    def proposed_intent(self) -> dict[str, Any]:
        """The dict the pre-execution risk gate consumes."""
        intent: dict[str, Any] = {
            "symbol": self.symbol,
            "direction": str(self.direction).upper(),
            "lots": float(self.volume),
        }
        if self.expected_loss_usd is not None:
            intent["expected_loss_usd"] = float(self.expected_loss_usd)
        return intent


@dataclass(frozen=True)
class DispatchResult:
    """The outcome of dispatching a single intent through the full gate chain."""

    order_id: str
    decision_ref: str
    symbol: str
    direction: str
    volume: float
    status: str
    reason: str
    intent_summary: str
    dispatched_to_bridge: bool
    outcome: Optional[OrderOutcome] = None
    ledger_event: Optional[AccountLedgerEvent] = None
    risk_blocking_caps: tuple[str, ...] = ()
    audit_attempt_id: Optional[str] = None
    audit_status: Optional[str] = None
    audit_error: Optional[str] = None

    @property
    def executed(self) -> bool:
        return self.outcome is not None and self.outcome.status.value in {"EXECUTED", "PARTIAL"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "decision_ref": self.decision_ref,
            "symbol": self.symbol,
            "direction": self.direction,
            "volume": self.volume,
            "status": self.status,
            "reason": self.reason,
            "intent_summary": self.intent_summary,
            "dispatched_to_bridge": self.dispatched_to_bridge,
            "executed": self.executed,
            "outcome": self.outcome.model_dump(mode="json") if self.outcome is not None else None,
            "ledger_event": self.ledger_event.to_dict() if self.ledger_event is not None else None,
            "risk_blocking_caps": list(self.risk_blocking_caps),
            "audit_attempt_id": self.audit_attempt_id,
            "audit_status": self.audit_status,
            "audit_error": self.audit_error,
        }


@dataclass(frozen=True)
class DispatchReport:
    """The result of dispatching a batch of intents."""

    report_kind: str
    mode: str  # "PAPER" | "LIVE"
    generated_at: str
    results: tuple[DispatchResult, ...]
    intent_count: int
    executed_count: int
    blocked_count: int
    rejected_count: int
    pending_count: int
    live_execution_runtime_locked: bool
    claim_boundary: str = CLAIM_BOUNDARY
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": self.report_kind,
            "mode": self.mode,
            "generated_at": self.generated_at,
            "results": [r.to_dict() for r in self.results],
            "intent_count": self.intent_count,
            "executed_count": self.executed_count,
            "blocked_count": self.blocked_count,
            "rejected_count": self.rejected_count,
            "pending_count": self.pending_count,
            "live_execution_runtime_locked": self.live_execution_runtime_locked,
            "claim_boundary": self.claim_boundary,
            "notes": list(self.notes),
        }


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        base = config
    else:
        from cas_forex.config import config as default_config

        base = default_config

    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        return apply_live_enable_overrides(base)
    except Exception:  # pragma: no cover - dispatch stays fail-closed downstream
        return base


def _mode_from_config(config: Any = None) -> str:
    return "LIVE" if bool(getattr(_resolve_config(config), "live_mode", False)) else "PAPER"


def _bridge_reports_real_execution(bridge: Any) -> bool:
    probe = getattr(bridge, "will_execute_real_order", None)
    if not callable(probe):
        return False
    try:
        return bool(probe())
    except Exception:
        return True


def _is_compound_add_dispatch(
    *,
    order: Any,
    ai_action: str,
    proposed_intent: Optional[Mapping[str, Any]],
) -> bool:
    intent = dict(proposed_intent or {})
    if bool(intent.get("is_compound_add") or intent.get("compound_add")):
        return True
    values = [
        ai_action,
        getattr(order, "comment", ""),
        intent.get("ai_action"),
        intent.get("action"),
        intent.get("route_action"),
        intent.get("order_role"),
        intent.get("intent_role"),
    ]
    for value in values:
        token = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
        if token in COMPOUND_ADD_ACTIONS:
            return True
        if "ADD" in token and ("COMPOUND" in token or "PYRAMID" in token):
            return True
    return False


def _resolve_audit_store(audit_store: Any = None) -> Any:
    if audit_store is not None:
        return audit_store
    from cas_forex.order_attempt_audit import default_order_attempt_audit_store

    return default_order_attempt_audit_store()


def record_dispatch_result_to_audit(
    result: DispatchResult,
    *,
    audit_store: Any = None,
    started_attempt: Optional[Mapping[str, Any]] = None,
    order: Any = None,
    proposed_intent: Optional[Mapping[str, Any]] = None,
    config: Any = None,
    bridge: Any = None,
    is_real_attempt: Optional[bool] = None,
    source: str = "order_dispatch",
) -> DispatchResult:
    """Persist a dispatch result and attach audit metadata without raising."""
    try:
        store = _resolve_audit_store(audit_store)
        mode = _mode_from_config(config)
        real_attempt = (
            bool(is_real_attempt)
            if is_real_attempt is not None
            else mode == "LIVE" or bool(getattr(result.outcome, "is_real_broker", False))
        )
        record = store.record_result(
            result,
            started_attempt=started_attempt,
            order=order,
            proposed_intent=proposed_intent,
            mode=mode,
            is_real_attempt=real_attempt,
            bridge_name=bridge.__class__.__name__ if bridge is not None else "",
            source=source,
        )
        return replace(
            result,
            audit_attempt_id=str(record.get("attempt_id") or ""),
            audit_status=str(record.get("status") or ""),
            audit_error=None,
        )
    except Exception as exc:
        return replace(result, audit_error=str(exc))


def _ledger_event_from_order(
    order: BrokerOrderRequest,
    outcome: OrderOutcome,
    *,
    strategy_id: Optional[str] = None,
    ai_action: str = "DISPATCH",
) -> AccountLedgerEvent:
    """A balance-neutral dispatch record for the account ledger.

    Entry dispatch does not realize P/L, so this is a ``paper_order_intent``
    (neutral) event. It pins the broker ticket / fill price / status so the
    ledger row reconciles against the broker record later. It never claims
    external money movement.
    """
    return AccountLedgerEvent(
        ledger_id=stable_ledger_id(
            "dispatch", order.decision_ref, order.order_id, order.symbol, order.direction.value
        ),
        event_type="paper_order_intent",
        timestamp=utc_now().isoformat(),
        amount_usd=0.0,
        balance_delta_usd=0.0,
        equity_delta_usd=0.0,
        symbol=order.symbol,
        side=order.direction.value,
        lot_size=float(order.volume),
        price=outcome.filled_price if outcome.filled_price is not None else (order.price or None),
        sl=float(order.stop_loss),
        tp=float(order.take_profit),
        broker_ticket=str(outcome.broker_ticket) if outcome.broker_ticket is not None else None,
        strategy_id=strategy_id,
        ai_action=ai_action,
        evidence_packet_id=order.decision_ref,
        note=(
            f"Order dispatched to broker bridge; outcome={outcome.status.value} "
            f"mode={outcome.broker_mode.value} real_broker={outcome.is_real_broker}."
        ),
        external_money_movement=False,
    )


def dispatch_order(
    order: BrokerOrderRequest,
    bridge: Any,
    *,
    proposed_intent: Optional[Mapping[str, Any]] = None,
    strategy_id: Optional[str] = None,
    ai_action: str = "DISPATCH",
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    audit_store: Any = None,
    audit_source: str = "order_dispatch",
) -> DispatchResult:
    """Dispatch a pre-built broker order through the full gate chain. Never raises.

    This is the lower-level entry point. It takes an already-validated
    ``BrokerOrderRequest`` (e.g. one rebuilt from an agent RouteIntent's
    ``order_request``) and runs the live-trading gate (live mode only), then the
    pre-execution risk gate, and only then touches the bridge. ``proposed_intent``
    overrides the symbol/direction/lots inferred from ``order`` for the risk gate.
    """
    # Local import keeps the (heavy) broker module off the import path for
    # callers that only need the data types.
    from cas_forex.execution_guard import guarded_place_order

    direction = order.direction.value
    intent_summary = f"{direction} {order.symbol} {float(order.volume):.2f} lots"
    intent_dict = dict(proposed_intent) if proposed_intent else {
        "symbol": order.symbol,
        "direction": direction,
        "lots": float(order.volume),
    }
    mode = _mode_from_config(config)
    is_real_attempt = mode == "LIVE" or _bridge_reports_real_execution(bridge)
    resolved_audit_store = _resolve_audit_store(audit_store)
    audit_attempt: Optional[Mapping[str, Any]] = None
    try:
        audit_attempt = resolved_audit_store.record_started(
            order,
            proposed_intent=intent_dict,
            mode=mode,
            is_real_attempt=is_real_attempt,
            bridge_name=bridge.__class__.__name__,
            source=audit_source,
        )
    except Exception as exc:
        if is_real_attempt:
            return DispatchResult(
                order_id=order.order_id,
                decision_ref=order.decision_ref,
                symbol=order.symbol,
                direction=direction,
                volume=float(order.volume),
                status=STATUS_DISPATCH_ERROR,
                reason=f"Order audit unavailable before real dispatch: {exc}",
                intent_summary=intent_summary,
                dispatched_to_bridge=False,
                audit_status="AUDIT_UNAVAILABLE",
                audit_error=str(exc),
            )

    def _blocked(status: str, reason: str, *, caps: tuple[str, ...] = ()) -> DispatchResult:
        result = DispatchResult(
            order_id=order.order_id,
            decision_ref=order.decision_ref,
            symbol=order.symbol,
            direction=direction,
            volume=float(order.volume),
            status=status,
            reason=reason,
            intent_summary=intent_summary,
            dispatched_to_bridge=False,
            risk_blocking_caps=caps,
        )
        return record_dispatch_result_to_audit(
            result,
            audit_store=resolved_audit_store,
            started_attempt=audit_attempt,
            order=order,
            proposed_intent=intent_dict,
            config=config,
            bridge=bridge,
            is_real_attempt=is_real_attempt,
            source=audit_source,
        )

    if _is_compound_add_dispatch(order=order, ai_action=ai_action, proposed_intent=intent_dict):
        try:
            from cas_forex.compound_add_order_dry_run_review import (
                require_current_compound_add_order_dry_run_review,
            )

            require_current_compound_add_order_dry_run_review(order)
        except Exception as exc:
            return _blocked(STATUS_BLOCKED_COMPOUND_ADD_REVIEW, str(exc))

    try:
        outcome: OrderOutcome = guarded_place_order(
            bridge,
            order,
            proposed_intent=intent_dict,
            config=config,
            live_telemetry=live_telemetry,
            account_snapshot=account_snapshot,
            equity_peak=equity_peak,
        )
    except PermissionError as exc:
        return _blocked(STATUS_BLOCKED_LIVE_GATE, str(exc))
    except ExecutionBlocked as exc:
        return _blocked(
            STATUS_BLOCKED_RISK,
            exc.decision.plain_english_reason,
            caps=tuple(exc.decision.blocking_caps),
        )
    except Exception as exc:  # bridge unusable / execute_order raised
        # Preserve the "never raises" contract so one bad bridge call cannot
        # abort the whole batch; surface it as an explicit per-intent error.
        return _blocked(STATUS_DISPATCH_ERROR, f"Dispatch error: {exc}")

    ledger_event = _ledger_event_from_order(
        order, outcome, strategy_id=strategy_id, ai_action=ai_action
    )
    if bool(getattr(outcome, "is_real_broker", False)) and outcome.status.value in {"EXECUTED", "PARTIAL"}:
        try:
            from cas_forex.live_pilot import record_live_pilot_dispatch

            record_live_pilot_dispatch(
                order_id=order.order_id,
                symbol=order.symbol,
                lots=float(order.volume),
                outcome_status=outcome.status.value,
            )
        except Exception:
            # The order already reached the broker; never mask the broker result.
            # The broker-truth monitor and ledger reconciliation will still catch
            # the real position even if the pilot audit write failed.
            pass
    result = DispatchResult(
        order_id=order.order_id,
        decision_ref=order.decision_ref,
        symbol=order.symbol,
        direction=direction,
        volume=float(order.volume),
        status=f"BROKER_{outcome.status.value}",
        reason=outcome.error_message or f"Broker outcome: {outcome.status.value}",
        intent_summary=intent_summary,
        dispatched_to_bridge=True,
        outcome=outcome,
        ledger_event=ledger_event,
    )
    return record_dispatch_result_to_audit(
        result,
        audit_store=resolved_audit_store,
        started_attempt=audit_attempt,
        order=order,
        proposed_intent=intent_dict,
        config=config,
        bridge=bridge,
        is_real_attempt=is_real_attempt,
        source=audit_source,
    )


def dispatch_intent(
    intent: TradeIntent,
    bridge: Any,
    *,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    audit_store: Any = None,
    audit_source: str = "order_dispatch",
) -> DispatchResult:
    """Dispatch one normalized TradeIntent through the full gate chain. Never raises."""
    intent_summary = f"{str(intent.direction).upper()} {intent.symbol} {float(intent.volume):.2f} lots"

    # 1. Build + validate the broker order (schema + SL/TP geometry).
    try:
        order = intent.to_order()
    except Exception as exc:  # pydantic ValidationError or bad direction
        result = DispatchResult(
            order_id=intent.order_id,
            decision_ref=intent.decision_ref,
            symbol=intent.symbol,
            direction=str(intent.direction).upper(),
            volume=float(intent.volume),
            status=STATUS_REJECTED_PRECHECK,
            reason=f"Order rejected before dispatch: {exc}",
            intent_summary=intent_summary,
            dispatched_to_bridge=False,
        )
        return record_dispatch_result_to_audit(
            result,
            audit_store=audit_store,
            proposed_intent={
                "symbol": intent.symbol,
                "direction": str(intent.direction).upper(),
                "lots": float(intent.volume),
            },
            config=config,
            bridge=bridge,
            source=f"{audit_source}_precheck",
        )

    # 2-3. Gate chain + dispatch + ledger event (shared with the agent path).
    return dispatch_order(
        order,
        bridge,
        proposed_intent=intent.proposed_intent(),
        strategy_id=intent.strategy_id,
        ai_action=intent.ai_action,
        config=config,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        equity_peak=equity_peak,
        audit_store=audit_store,
        audit_source=audit_source,
    )


def build_dispatch_report(
    results: Sequence[DispatchResult], *, config: Any = None
) -> DispatchReport:
    """Assemble a DispatchReport from per-intent results, with summary counts.

    Shared by ``dispatch_intents`` and the agent dispatch path so both produce an
    identically-shaped, fully-traceable report.
    """
    config = _resolve_config(config)
    live_mode = bool(getattr(config, "live_mode", False))
    executed = sum(1 for r in results if r.executed)
    blocked = sum(
        1
        for r in results
        if r.status
        in {STATUS_BLOCKED_LIVE_GATE, STATUS_BLOCKED_COMPOUND_ADD_REVIEW, STATUS_BLOCKED_RISK}
    )
    rejected = sum(
        1
        for r in results
        if r.status in {STATUS_REJECTED_PRECHECK, STATUS_OVERSEER_REJECTED, STATUS_DISPATCH_ERROR}
        or (r.outcome is not None and r.outcome.status.value in {"REJECTED", "CANCELLED"})
    )
    # A queued-but-not-yet-filled order (e.g. MT4 mailbox lane returns PENDING)
    # is its own bucket so executed + blocked + rejected + pending == intent_count.
    pending = sum(
        1 for r in results if r.outcome is not None and r.outcome.status.value == "PENDING"
    )

    try:
        from cas_forex import runtime_gates

        live_locked = not runtime_gates.is_authorized("live_trading", config)
    except Exception:  # pragma: no cover - defensive
        live_locked = True

    return DispatchReport(
        report_kind="cas_forex_order_dispatch",
        mode="LIVE" if live_mode else "PAPER",
        generated_at=utc_now().isoformat(),
        results=tuple(results),
        intent_count=len(results),
        executed_count=executed,
        blocked_count=blocked,
        rejected_count=rejected,
        pending_count=pending,
        live_execution_runtime_locked=live_locked,
        notes=(
            "Each result carries its gate decision and broker outcome; the path "
            "signal -> gate -> dispatch -> fill -> ledger is traceable per intent.",
            "Ledger events are balance-neutral dispatch records (paper_order_intent); "
            "realized P/L is recorded when positions close, not at entry.",
        ),
    )


def dispatch_intents(
    intents: Iterable[TradeIntent],
    *,
    bridge: Any = None,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    audit_store: Any = None,
) -> DispatchReport:
    """Dispatch a batch of normalized intents through the gate chain into the broker.

    With ``bridge=None`` the configured bridge (``broker.get_bridge()``) is used,
    which is the paper broker unless the owner has authorized live trading.
    """
    config = _resolve_config(config)
    if bridge is None:
        # Honor the owner's platform choice + loosen settings.
        from cas_forex.broker_control import select_bridge

        bridge = select_bridge(config)

    results = [
        dispatch_intent(
            intent,
            bridge,
            config=config,
            live_telemetry=live_telemetry,
            account_snapshot=account_snapshot,
            equity_peak=equity_peak,
            audit_store=audit_store,
        )
        for intent in intents
    ]
    return build_dispatch_report(results, config=config)


def dispatched_ledger_events(report: DispatchReport) -> tuple[AccountLedgerEvent, ...]:
    """Collect the ledger events from every intent that reached the bridge."""
    return tuple(r.ledger_event for r in report.results if r.ledger_event is not None)
