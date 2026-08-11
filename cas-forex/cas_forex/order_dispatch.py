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

from pathlib import Path
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping, Optional, Sequence

from cas_forex.account_ledger import AccountLedgerEvent, stable_ledger_id
from cas_forex.execution_guard import (
    ExecutionBlocked,
    LiveDispatchBlocked,
    require_trade_management_action_ready,
)
from cas_forex.execution_provenance import build_execution_provenance
from cas_forex.instruments import canonical_symbol as canonical_instrument_symbol
from cas_forex.pre_trade_money import build_pre_trade_money_estimate
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderOutcome, OrderType
from cas_forex.time_utils import ensure_utc, utc_now

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
STATUS_BLOCKED_EDGE_AUTHORIZATION = "BLOCKED_EDGE_AUTHORIZATION"  # no fresh matching PASS at the edge gate
STATUS_BLOCKED_COMPOUND_ADD_AUTHORIZATION = "BLOCKED_COMPOUND_ADD_AUTHORIZATION"
# Backward-compatible import alias for older evidence/tests. Normal autonomous
# operation now uses an exact one-shot Operator authorization, not per-add owner review.
STATUS_BLOCKED_COMPOUND_ADD_REVIEW = STATUS_BLOCKED_COMPOUND_ADD_AUTHORIZATION
STATUS_BLOCKED_MARKET = "BLOCKED_MARKET"  # explicit market/session/symbol availability block
STATUS_BLOCKED_EXECUTION_QUALITY = "BLOCKED_EXECUTION_QUALITY"  # spread/slippage outside owner broker tolerance
STATUS_BLOCKED_MACRO = "BLOCKED_MACRO"  # macro/news blackout active at dispatch time
STATUS_BLOCKED_ORDER_CONSTRAINTS = "BLOCKED_ORDER_CONSTRAINTS"  # volume or SL/TP geometry violates broker controls
STATUS_BLOCKED_RISK = "BLOCKED_RISK"  # pre-execution risk cap breach
STATUS_OVERSEER_REJECTED = "OVERSEER_REJECTED"  # agent overseer rejected before dispatch
STATUS_DISPATCH_ERROR = "DISPATCH_ERROR"  # bridge raised / unusable; never reached a fill
STATUS_DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"  # idempotency: exact order already dispatched


def dispatch_trade_management_action(
    action: Mapping[str, Any],
    *,
    bridge: Any,
    config: Any = None,
) -> dict[str, Any]:
    """Dispatch one existing-position action through the named order chokepoint.

    Entry orders and existing-position modifications have different schemas, but
    both broker-bound effects enter this module. The deterministic management
    guard runs immediately before the selected bridge method. Receipt
    reconciliation and durable action audit remain in the management executor.
    """

    method = str(action.get("broker_method") or "")
    ticket = action.get("broker_ticket")
    try:
        guard = require_trade_management_action_ready(
            action,
            config=config,
            bridge=bridge,
        )
    except Exception as exc:
        payload = {
            "report_kind": "cas_forex_trade_management_dispatch",
            "status": "EXECUTION_GUARD_BLOCKED",
            "broker_method": method,
            "broker_ticket": ticket,
            "broker_touched": False,
            "broker_method_called": False,
            "execution_guard": {
                "status": "BLOCKED",
                "error_type": type(exc).__name__,
                "detail": str(exc),
            },
            "broker_result": None,
        }
        return _with_trade_management_provenance(
            payload, action=action, bridge=bridge, config=config
        )

    try:
        ticket_number = int(str(ticket))
        reference_price = _management_optional_float(action.get("current_price"))
        reference_setter = getattr(bridge, "set_reference_price", None)
        if callable(reference_setter) and reference_price is not None:
            reference_setter(ticket_number, reference_price)
        if method == "modify_position":
            fn = getattr(bridge, "modify_position", None)
            if not callable(fn):
                broker_result = {
                    "accepted": False,
                    "method": method,
                    "ticket": ticket_number,
                    "status": "UNSUPPORTED",
                    "detail": "Bridge has no modify_position method.",
                }
            else:
                outcome = fn(
                    ticket_number,
                    stop_loss=float(action.get("stop_loss")),
                    take_profit=_management_optional_float(action.get("take_profit")),
                )
                outcome_payload = _management_outcome_payload(outcome)
                outcome_status = str(outcome_payload.get("status") or "UNKNOWN")
                broker_result = {
                    "accepted": outcome_status.upper().endswith("EXECUTED"),
                    "method": method,
                    "ticket": ticket_number,
                    "outcome": outcome_payload,
                    "status": outcome_status,
                }
        elif method == "close_position":
            fn = getattr(bridge, "close_position", None)
            if not callable(fn):
                broker_result = {
                    "accepted": False,
                    "method": method,
                    "ticket": ticket_number,
                    "status": "UNSUPPORTED",
                    "detail": "Bridge has no close_position method.",
                }
            else:
                volume = _management_optional_float(action.get("volume"))
                accepted = bool(fn(ticket_number, volume=volume))
                broker_result = {
                    "accepted": accepted,
                    "method": method,
                    "ticket": ticket_number,
                    "volume": volume,
                    "status": "EXECUTED" if accepted else "REJECTED",
                }
        else:
            broker_result = {
                "accepted": False,
                "method": method,
                "ticket": ticket_number,
                "status": "UNSUPPORTED",
                "detail": f"Unsupported broker method {method}.",
            }
    except Exception as exc:
        payload = {
            "report_kind": "cas_forex_trade_management_dispatch",
            "status": "BRIDGE_ERROR",
            "broker_method": method,
            "broker_ticket": ticket,
            "broker_touched": True,
            "broker_method_called": True,
            "execution_guard": guard,
            "broker_result": {
                "status": "ERROR",
                "error_type": type(exc).__name__,
                "detail": str(exc),
            },
        }
        return _with_trade_management_provenance(
            payload, action=action, bridge=bridge, config=config
        )

    payload = {
        "report_kind": "cas_forex_trade_management_dispatch",
        "status": "DISPATCHED" if broker_result.get("accepted") else "REJECTED",
        "broker_method": method,
        "broker_ticket": ticket_number,
        "broker_touched": True,
        "broker_method_called": True,
        "execution_guard": guard,
        "broker_result": broker_result,
        "claim_boundary": (
            "All existing-position broker effects enter order_dispatch.py, pass "
            "execution_guard.py, and then call the selected broker bridge."
        ),
    }
    return _with_trade_management_provenance(
        payload, action=action, bridge=bridge, config=config
    )


def _with_trade_management_provenance(
    payload: Mapping[str, Any],
    *,
    action: Mapping[str, Any],
    bridge: Any,
    config: Any = None,
) -> dict[str, Any]:
    prepared = dict(payload)
    proposed = dict(action)
    proposed.setdefault("direction", action.get("side"))
    proposed.setdefault("lots", action.get("volume") or action.get("original_volume"))
    proposed.setdefault("strategy_id", action.get("strategy") or action.get("strategy_id"))
    proposed.setdefault("ai_action", action.get("intent") or "POSITION_MANAGEMENT")
    broker_result = prepared.get("broker_result")
    broker_result = broker_result if isinstance(broker_result, Mapping) else {}
    outcome = broker_result.get("outcome")
    outcome = outcome if isinstance(outcome, Mapping) else broker_result
    outcome = dict(outcome)
    outcome.setdefault("is_real_broker", _bridge_reports_real_execution(bridge))
    demo_probe = getattr(bridge, "is_demo_account", None)
    if callable(demo_probe):
        try:
            outcome.setdefault("is_demo_account", bool(demo_probe()))
        except Exception:
            pass
    accepted = bool(broker_result.get("accepted"))
    touched = bool(prepared.get("broker_touched"))
    dispatch_status = str(prepared.get("status") or "")
    normalized_result = {
        "status": (
            "BROKER_EXECUTED"
            if accepted
            else (
                "BLOCKED_RISK"
                if dispatch_status == "EXECUTION_GUARD_BLOCKED"
                else "DISPATCH_ERROR" if dispatch_status == "BRIDGE_ERROR" else "BROKER_REJECTED"
            )
        ),
        "dispatched_to_bridge": touched,
        "executed": accepted,
        "reason": (
            (prepared.get("execution_guard") or {}).get("detail")
            if isinstance(prepared.get("execution_guard"), Mapping)
            else None
        ),
    }
    prepared["execution_provenance"] = _dispatch_provenance(
        proposed_intent=proposed,
        config=config,
        bridge=bridge,
        strategy_id=str(proposed.get("strategy_id") or "") or None,
        ai_action=str(proposed.get("ai_action") or "POSITION_MANAGEMENT"),
        outcome=outcome,
        source="order_dispatch.trade_management",
        dispatch_result=normalized_result,
        mode=_mode_from_config(config),
    )
    prepared["version_trace"] = prepared["execution_provenance"].get(
        "version_trace", {}
    )
    return prepared


def _management_optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _management_outcome_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        try:
            return dict(value.model_dump(mode="json"))
        except TypeError:
            return dict(value.model_dump())
    if hasattr(value, "__dict__"):
        return {
            key: (item.value if hasattr(item, "value") else item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return {"status": str(value)}

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
    manual_order_journal: Optional[Mapping[str, Any]] = None

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
        if self.strategy_id:
            intent["strategy_id"] = str(self.strategy_id)
        if self.expected_loss_usd is not None:
            intent["expected_loss_usd"] = float(self.expected_loss_usd)
        if self.manual_order_journal is not None:
            intent["manual_order_journal"] = dict(self.manual_order_journal)
        return intent


def _outcome_account_mode(outcome: Any) -> str:
    if outcome is None or not bool(getattr(outcome, "is_real_broker", False)):
        return "SIMULATED"
    demo = getattr(outcome, "is_demo_account", None)
    if demo is True:
        return "DEMO"
    if demo is False:
        return "LIVE"
    return "UNKNOWN"


def _outcome_is_live_money(outcome: Any) -> bool:
    return _outcome_account_mode(outcome) == "LIVE"


def _outcome_requires_live_safety(outcome: Any) -> bool:
    """Unknown external accounts retain live-safety treatment until classified."""
    return bool(getattr(outcome, "is_real_broker", False)) and getattr(
        outcome, "is_demo_account", None
    ) is not True


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
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    outcome: Optional[OrderOutcome] = None
    ledger_event: Optional[AccountLedgerEvent] = None
    risk_blocking_caps: tuple[str, ...] = ()
    audit_attempt_id: Optional[str] = None
    audit_status: Optional[str] = None
    audit_error: Optional[str] = None
    execution_provenance: dict[str, Any] = field(default_factory=dict)
    pre_trade_estimate: dict[str, Any] = field(default_factory=dict)
    live_gate_report: dict[str, Any] = field(default_factory=dict)
    market_availability: dict[str, Any] = field(default_factory=dict)
    execution_quality: dict[str, Any] = field(default_factory=dict)
    macro_blackout: dict[str, Any] = field(default_factory=dict)
    order_constraints: dict[str, Any] = field(default_factory=dict)

    @property
    def executed(self) -> bool:
        return self.outcome is not None and self.outcome.status.value in {"EXECUTED", "PARTIAL"}

    def money_impact(self) -> dict[str, Any]:
        """Owner-facing impact summary for error/UI text.

        This answers the operational question first: did the request touch a
        broker bridge, did it execute, and could external money have moved?
        Ledger entry dispatches are balance-neutral; realized P/L is recorded
        when positions close.
        """
        external_broker = bool(getattr(self.outcome, "is_real_broker", False)) if self.outcome is not None else False
        demo_account = getattr(self.outcome, "is_demo_account", None) if self.outcome is not None else None
        account_mode = _outcome_account_mode(self.outcome)
        live_money_broker = _outcome_is_live_money(self.outcome)
        external_money = bool(
            self.ledger_event is not None and self.ledger_event.external_money_movement
        )
        if not self.dispatched_to_bridge:
            summary = "No broker bridge was touched; no order was placed."
        elif self.executed and account_mode == "DEMO":
            summary = (
                "External MT5 demo broker reported an executed/partial order; "
                "no live money was used."
            )
        elif self.executed and live_money_broker:
            summary = "Live-money broker reported an executed/partial order; reconcile terminal truth."
        elif self.executed and external_broker:
            summary = (
                "External broker reported an executed/partial order, but account mode is "
                "unknown; do not classify it as demo or live until reconciled."
            )
        elif self.executed:
            summary = "Paper/demo bridge reported an executed/partial order; no external money movement."
        elif self.outcome is not None:
            summary = f"Broker bridge returned {self.outcome.status.value}; execution is not confirmed."
        else:
            summary = "Broker bridge touch is unknown; inspect the dispatch reason and audit attempt."
        return {
            "broker_bridge_touched": bool(self.dispatched_to_bridge),
            "order_executed": bool(self.executed),
            "real_broker": external_broker,
            "external_broker_terminal": external_broker,
            "is_demo_account": demo_account,
            "account_mode": account_mode,
            "live_money_broker": live_money_broker,
            "external_money_movement": external_money,
            "summary": summary,
        }

    def trade_explanation_card(self) -> dict[str, Any]:
        """Structured owner-facing explanation for opened, blocked, or rejected trades."""
        if self.stop_loss is not None and self.take_profit is not None:
            protection_status = "PROTECTED"
            protection_detail = "Stop loss and take profit were attached to the dispatch request."
        else:
            protection_status = "UNKNOWN"
            protection_detail = "Stop loss / take profit were not attached to this result object."
        broker_status = "NOT_TOUCHED"
        if self.dispatched_to_bridge and self.outcome is not None:
            broker_status = self.outcome.status.value
        elif self.dispatched_to_bridge:
            broker_status = "TOUCHED_NO_OUTCOME"
        live_gate_checks = list((self.live_gate_report or {}).get("checks") or [])
        live_gate_by_stage = {
            str(item.get("stage")): item
            for item in live_gate_checks
            if isinstance(item, Mapping)
        }
        def _live_gate_stage(stage: str, fallback_detail: str) -> dict[str, Any]:
            item = dict(live_gate_by_stage.get(stage) or {})
            blocked = item.get("status") == "BLOCKED"
            return {
                "stage": stage,
                "status": "BLOCKED" if blocked else str(item.get("status") or "NOT_APPLICABLE"),
                "detail": str(item.get("detail") or fallback_detail),
                "missing_requirements": list(item.get("missing_requirements") or []),
                "evidence_snapshot": dict(item.get("evidence_snapshot") or {}),
                "next_action": str(item.get("next_action") or ""),
            }
        return {
            "report_kind": "cas_forex_trade_explanation_card",
            "order_id": self.order_id,
            "decision_ref": self.decision_ref,
            "symbol": self.symbol,
            "direction": self.direction,
            "volume": self.volume,
            "status": self.status,
            "executed": self.executed,
            "summary": self.reason,
            "intent_summary": self.intent_summary,
            "gate_trace": [
                {
                    "stage": "precheck",
                    "status": "BLOCKED" if self.status == STATUS_REJECTED_PRECHECK else "PASSED_OR_NOT_APPLICABLE",
                    "detail": self.reason if self.status == STATUS_REJECTED_PRECHECK else "Order reached dispatch result construction.",
                },
                {
                    "stage": "idempotency",
                    "status": "BLOCKED" if self.status == STATUS_DUPLICATE_SUPPRESSED else "PASSED_OR_NOT_APPLICABLE",
                    "detail": (
                        self.reason
                        if self.status == STATUS_DUPLICATE_SUPPRESSED
                        else "No prior exact retry or recent automation duplicate blocked this result."
                    ),
                },
                {
                    "stage": "market_availability",
                    "status": "BLOCKED" if self.status == STATUS_BLOCKED_MARKET else str(
                        (self.market_availability or {}).get("status") or "PASSED_OR_UNKNOWN"
                    ),
                    "detail": self.reason if self.status == STATUS_BLOCKED_MARKET else str(
                        (self.market_availability or {}).get("detail")
                        or "No explicit market/session closure evidence blocked this result."
                    ),
                    "blockers": list((self.market_availability or {}).get("blockers") or []),
                },
                {
                    **_live_gate_stage(
                        "live_gate",
                        "Live gate did not block this result.",
                    ),
                },
                {
                    **_live_gate_stage(
                        "auto_halt",
                        "Auto-halt did not block this result.",
                    ),
                },
                {
                    **_live_gate_stage(
                        "broker_truth",
                        "Fresh broker truth did not block this result.",
                    ),
                },
                {
                    **_live_gate_stage(
                        "mt5_terminal_permissions",
                        "Action-time MT5 terminal permissions did not block this result.",
                    ),
                },
                {
                    **_live_gate_stage(
                        "live_recovery",
                        "Live recovery review did not block this result.",
                    ),
                },
                {
                    **_live_gate_stage(
                        "live_order_dry_run_review",
                        "Live dry-run review did not block this result.",
                    ),
                },
                {
                    **_live_gate_stage(
                        "live_risk_snapshot",
                        "Live risk snapshot did not block this result.",
                    ),
                },
                {
                    **_live_gate_stage(
                        "live_pilot",
                        "Live pilot did not block this result.",
                    ),
                },
                {
                    "stage": "edge_authorization",
                    "status": "BLOCKED" if self.status == STATUS_BLOCKED_EDGE_AUTHORIZATION else "NOT_BLOCKING_THIS_RESULT",
                    "detail": (
                        self.reason
                        if self.status == STATUS_BLOCKED_EDGE_AUTHORIZATION
                        else "Edge authorization did not block this result."
                    ),
                },
                {
                    "stage": "execution_quality",
                    "status": "BLOCKED" if self.status == STATUS_BLOCKED_EXECUTION_QUALITY else str(
                        (self.execution_quality or {}).get("status") or "PASSED_OR_UNKNOWN"
                    ),
                    "detail": self.reason if self.status == STATUS_BLOCKED_EXECUTION_QUALITY else str(
                        (self.execution_quality or {}).get("detail")
                        or "No explicit spread/slippage evidence blocked this result."
                    ),
                    "blockers": list((self.execution_quality or {}).get("blockers") or []),
                },
                {
                    "stage": "macro_blackout",
                    "status": "BLOCKED" if self.status == STATUS_BLOCKED_MACRO else str(
                        (self.macro_blackout or {}).get("status") or "PASSED_OR_UNKNOWN"
                    ),
                    "detail": self.reason if self.status == STATUS_BLOCKED_MACRO else str(
                        (self.macro_blackout or {}).get("detail")
                        or "No active macro/news blackout blocked this result."
                    ),
                    "blockers": list((self.macro_blackout or {}).get("blockers") or []),
                },
                {
                    "stage": "order_constraints",
                    "status": "BLOCKED" if self.status == STATUS_BLOCKED_ORDER_CONSTRAINTS else str(
                        (self.order_constraints or {}).get("status") or "PASSED_OR_UNKNOWN"
                    ),
                    "detail": self.reason if self.status == STATUS_BLOCKED_ORDER_CONSTRAINTS else str(
                        (self.order_constraints or {}).get("detail")
                        or "No broker lot or stop-distance constraint blocked this result."
                    ),
                    "blockers": list((self.order_constraints or {}).get("blockers") or []),
                },
                {
                    "stage": "risk_engine",
                    "status": "BLOCKED" if self.status == STATUS_BLOCKED_RISK else "NOT_BLOCKING_THIS_RESULT",
                    "detail": self.reason if self.status == STATUS_BLOCKED_RISK else "Risk engine did not block this result.",
                    "blocking_caps": list(self.risk_blocking_caps),
                },
                {
                    "stage": "broker_bridge",
                    "status": broker_status,
                    "detail": self.money_impact()["summary"],
                },
            ],
            "protective_orders": {
                "status": protection_status,
                "stop_loss": self.stop_loss,
                "take_profit": self.take_profit,
                "detail": protection_detail,
            },
            "audit": {
                "attempt_id": self.audit_attempt_id,
                "status": self.audit_status,
                "error": self.audit_error,
            },
            "pre_trade_money": self.pre_trade_estimate,
            "live_gate_report": self.live_gate_report,
            "live_readiness_evidence": dict((self.live_gate_report or {}).get("evidence_snapshots") or {}),
            "execution_provenance": self.execution_provenance,
            "version_trace": (self.execution_provenance or {}).get("version_trace", {}),
            "money_impact": self.money_impact(),
            "market_availability": self.market_availability,
            "execution_quality": self.execution_quality,
            "macro_blackout": self.macro_blackout,
            "order_constraints": self.order_constraints,
            "claim_boundary": (
                "This card explains the dispatch result that already occurred. "
                "It is not a new trade signal and does not authorize another order."
            ),
        }

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
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "executed": self.executed,
            "outcome": self.outcome.model_dump(mode="json") if self.outcome is not None else None,
            "ledger_event": self.ledger_event.to_dict() if self.ledger_event is not None else None,
            "money_impact": self.money_impact(),
            "pre_trade_estimate": self.pre_trade_estimate,
            "live_gate_report": self.live_gate_report,
            "market_availability": self.market_availability,
            "execution_quality": self.execution_quality,
            "macro_blackout": self.macro_blackout,
            "order_constraints": self.order_constraints,
            "trade_explanation_card": self.trade_explanation_card(),
            "risk_blocking_caps": list(self.risk_blocking_caps),
            "audit_attempt_id": self.audit_attempt_id,
            "audit_status": self.audit_status,
            "audit_error": self.audit_error,
            "execution_provenance": self.execution_provenance,
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


_COMMON_MT5_TERMINAL_PATHS = (
    r"C:\Program Files\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
)


def _discover_mt5_terminal_path(config: Any = None) -> str | None:
    cfg = _resolve_config(config)
    configured = str(getattr(cfg, "mt5_path", "") or "").strip()
    if configured and Path(configured).exists():
        return configured
    for candidate in _COMMON_MT5_TERMINAL_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def _mt5_market_truth_enabled(config: Any = None, auto_path: str | None = None) -> bool:
    cfg = _resolve_config(config)
    provider = str(getattr(cfg, "market_data_provider", "") or "").upper()
    if provider in {"MT5", "BROKER", "BROKER_MT5", "MT5_TERMINAL"}:
        return True
    if not bool(getattr(cfg, "prefer_mt5", True)):
        return False
    return bool(getattr(cfg, "mt5_login", 0) or getattr(cfg, "mt5_path", None) or auto_path)


def _has_connector_kind(candidates: list[Any], connector: Any) -> bool:
    return any(type(candidate) is type(connector) for candidate in candidates)


def _quote_connector_candidates(config: Any = None, *, prefer_mt5: bool = False) -> list[Any]:
    from cas_forex.market_data.connector import (
        MT5TerminalMarketDataConnector,
        YFinanceConnector,
        get_connector,
    )

    candidates: list[Any] = []
    primary = get_connector()
    mt5_auto_path = _discover_mt5_terminal_path(config)
    mt5_connector = None
    if _mt5_market_truth_enabled(config, mt5_auto_path):
        mt5_connector = MT5TerminalMarketDataConnector(mt5_path=mt5_auto_path)
    if prefer_mt5 and mt5_connector is not None:
        candidates.append(mt5_connector)
    if not _has_connector_kind(candidates, primary):
        candidates.append(primary)
    if mt5_connector is not None and not _has_connector_kind(candidates, mt5_connector):
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


def _build_dispatch_quote_snapshot(
    symbol: str,
    *,
    config: Any = None,
    prefer_mt5: bool = False,
) -> dict[str, Any]:
    try:
        quote_symbol = canonical_instrument_symbol(symbol)
    except ValueError:
        quote_symbol = str(symbol or "").strip()
    attempts: list[dict[str, Any]] = []
    selected_connector: Any | None = None
    selected_snapshot: Any | None = None
    primary_connector_name = ""
    primary_failure = ""

    connector_candidates = (
        _quote_connector_candidates(config, prefer_mt5=True)
        if prefer_mt5
        else _quote_connector_candidates(config)
    )
    for index, connector in enumerate(connector_candidates):
        connector_name = type(connector).__name__
        if index == 0:
            primary_connector_name = connector_name
        try:
            snapshot = connector.fetch_snapshot(quote_symbol)
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
            "market_snapshot": None,
            "quote_source": None,
            "quote_feed_label": "no usable connector quote",
            "quote_connector_attempts": attempts,
            "quote_fallback_used": fallback_used,
            "quote_error": primary_failure or "no connector produced a usable non-synthetic quote",
        }

    fallback_reason = None
    if fallback_used and type(selected_connector).__name__ != primary_connector_name:
        fallback_reason = primary_failure or "configured primary provider could not serve this symbol"
    return {
        "market_snapshot": {
            "symbol": getattr(selected_snapshot, "symbol", quote_symbol),
            "bid": float(getattr(selected_snapshot, "bid", 0.0)),
            "ask": float(getattr(selected_snapshot, "ask", 0.0)),
            "spread": float(getattr(selected_snapshot, "spread", 0.0)),
            "spread_pips": float(getattr(selected_snapshot, "spread", 0.0)),
            "is_market_open": bool(getattr(selected_snapshot, "is_market_open", True)),
            "session": str(getattr(selected_snapshot, "session", "UNKNOWN")),
            "timestamp": str(getattr(selected_snapshot, "timestamp", "")),
            "source": "dispatch_quote_hydration",
            "quote_source": _quote_source_name(selected_connector),
            "quote_feed_label": _quote_feed_label(selected_connector, fallback_reason=fallback_reason),
            "quote_fallback_used": fallback_used,
            "quote_connector_attempts": attempts,
            "broker_grade_market_truth": bool(getattr(selected_connector, "broker_grade_market_truth", False)),
        },
        "quote_source": _quote_source_name(selected_connector),
        "quote_feed_label": _quote_feed_label(selected_connector, fallback_reason=fallback_reason),
        "quote_connector_attempts": attempts,
        "quote_fallback_used": fallback_used,
        "quote_error": None,
    }


def build_dispatch_quote_context(
    symbol: str,
    *,
    config: Any = None,
    prefer_mt5: bool = False,
) -> dict[str, Any]:
    """Return the shared symbol-capable quote packet used by dispatch runtimes.

    Agent/runtime callers use this public wrapper so quote-source fallback,
    synthetic-snapshot rejection, and source labels stay identical to the
    lower-level dispatch hydration path.
    """

    return _build_dispatch_quote_snapshot(
        symbol,
        config=config,
        prefer_mt5=prefer_mt5,
    )


def _positive_float_or_none(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None


def _bridge_reports_real_execution(bridge: Any) -> bool:
    probe = getattr(bridge, "will_execute_real_order", None)
    if not callable(probe):
        return False
    try:
        return bool(probe())
    except Exception:
        return True


def _dispatch_provenance(
    *,
    order: Any = None,
    proposed_intent: Optional[Mapping[str, Any]] = None,
    config: Any = None,
    bridge: Any = None,
    strategy_id: Optional[str] = None,
    ai_action: str = "DISPATCH",
    outcome: Any = None,
    source: str = "order_dispatch",
    dispatch_result: Any = None,
    mode: Optional[str] = None,
    audit: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    try:
        return build_execution_provenance(
            order=order,
            proposed_intent=proposed_intent,
            config=config,
            bridge=bridge,
            strategy_id=strategy_id,
            ai_action=ai_action,
            outcome=outcome,
            source=source,
            dispatch_result=dispatch_result,
            mode=mode,
            audit=audit,
        )
    except Exception as exc:
        return {
            "report_kind": "cas_forex_execution_provenance",
            "schema_version": "cas_forex_execution_provenance.v1",
            "source": str(source or "order_dispatch"),
            "provenance_error": str(exc),
        }


def _with_dispatch_provenance(
    result: DispatchResult,
    *,
    order: Any = None,
    proposed_intent: Optional[Mapping[str, Any]] = None,
    config: Any = None,
    bridge: Any = None,
    strategy_id: Optional[str] = None,
    ai_action: str = "DISPATCH",
    source: str = "order_dispatch",
    audit: Optional[Mapping[str, Any]] = None,
) -> DispatchResult:
    return replace(
        result,
        execution_provenance=_dispatch_provenance(
            order=order,
            proposed_intent=proposed_intent,
            config=config,
            bridge=bridge,
            strategy_id=strategy_id,
            ai_action=ai_action,
            outcome=result.outcome,
            source=source,
            dispatch_result=result,
            mode=_mode_from_config(config),
            audit=audit,
        ),
    )


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


_MARKET_BOOL_KEYS = frozenset(
    {
        "is_market_open",
        "market_open",
        "broker_market_open",
        "symbol_market_open",
        "session_open",
        "is_session_open",
        "tradable",
        "is_tradable",
        "can_trade",
        "trade_allowed",
        "trade_enabled",
        "symbol_trade_allowed",
        "order_send_allowed",
        "symbol_visible",
        "symbol_select",
    }
)
_MARKET_STATUS_KEYS = frozenset(
    {
        "availability",
        "market_status",
        "session_status",
        "symbol_status",
        "status",
        "trade_status",
        "trade_mode",
    }
)
_MARKET_FALSE_TOKENS = frozenset(
    {
        "0",
        "NO",
        "FALSE",
        "CLOSED",
        "MARKET_CLOSED",
        "SESSION_CLOSED",
        "UNAVAILABLE",
        "OFFLINE",
        "DISCONNECTED",
        "DISABLED",
        "HALTED",
        "SUSPENDED",
        "BLOCKED",
        "NOT_TRADABLE",
        "TRADE_DISABLED",
        "TRADING_DISABLED",
        "SYMBOL_TRADE_MODE_DISABLED",
        "SYMBOL_TRADE_MODE_CLOSEONLY",
        "CLOSEONLY",
        "CLOSE_ONLY",
    }
)
_MARKET_TRUE_TOKENS = frozenset(
    {
        "1",
        "YES",
        "TRUE",
        "OPEN",
        "MARKET_OPEN",
        "SESSION_OPEN",
        "AVAILABLE",
        "ONLINE",
        "ENABLED",
        "TRADABLE",
        "SYMBOL_TRADE_MODE_FULL",
        "FULL",
    }
)
_MARKET_NESTED_KEYS = frozenset(
    {
        "market",
        "market_state",
        "market_snapshot",
        "session",
        "session_state",
        "quote",
        "snapshot",
        "symbol",
        "symbol_info",
        "symbol_state",
        "symbol_status",
        "trade",
        "trading",
    }
)
_MARKET_SYMBOL_COLLECTION_KEYS = frozenset(
    {
        "markets",
        "quotes",
        "snapshots",
        "symbols",
        "symbol_info_by_symbol",
        "symbol_states",
        "symbol_statuses",
        "symbol_specs",
    }
)


def _canonical_symbol(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _symbol_matches(value: Any, target_symbol: str) -> bool:
    left = _canonical_symbol(value)
    right = _canonical_symbol(target_symbol)
    if not left or not right:
        return False
    return left == right or left.startswith(right) or right.startswith(left)


def _source_label_allows_generic_status(label: str) -> bool:
    token = label.lower()
    return any(part in token for part in ("market", "session", "quote", "symbol", "trade", "trading"))


def _live_telemetry_supports_quote_hydration(
    live_telemetry: Optional[Mapping[str, Any]],
) -> bool:
    if not isinstance(live_telemetry, Mapping):
        return False
    candidate_packets: list[Mapping[str, Any]] = [live_telemetry]
    movement_truth = live_telemetry.get("movement_source_truth")
    if isinstance(movement_truth, Mapping):
        candidate_packets.append(movement_truth)
    hydration_keys = {
        "market_snapshot",
        "symbols",
        "quotes",
        "snapshots",
        "price_source_status",
        "price_source_label",
        "price_source_truth",
        "price_source_summary",
        "static_fallback_symbols",
        "provider_usable_symbols",
        "movement_source_truth",
    }
    return any(any(key in packet for key in hydration_keys) for packet in candidate_packets)


def _mapping_matches_target_symbol(mapping: Mapping[str, Any], target_symbol: str) -> bool:
    symbol = mapping.get("symbol")
    if symbol in (None, ""):
        return True
    return _symbol_matches(symbol, target_symbol)


def _live_telemetry_has_market_quote(
    *,
    target_symbol: str,
    live_telemetry: Optional[Mapping[str, Any]],
) -> bool:
    if not isinstance(live_telemetry, Mapping):
        return False
    for _, mapping in _iter_market_evidence_sources(
        target_symbol=target_symbol,
        proposed_intent=None,
        live_telemetry=live_telemetry,
        account_snapshot=None,
    ):
        if not _mapping_matches_target_symbol(mapping, target_symbol):
            continue
        bid = _float_or_none(mapping.get("bid"))
        ask = _float_or_none(mapping.get("ask"))
        if bid is not None and ask is not None and ask >= bid:
            return True
        for key, value in mapping.items():
            if str(key or "").strip().lower() in _SPREAD_KEYS and _float_or_none(value) is not None:
                return True
    return False


def _hydrate_dispatch_live_telemetry(
    *,
    order: BrokerOrderRequest,
    live_telemetry: Optional[Mapping[str, Any]],
    config: Any = None,
) -> Optional[Mapping[str, Any]]:
    if not _live_telemetry_supports_quote_hydration(live_telemetry):
        return live_telemetry
    if _live_telemetry_has_market_quote(target_symbol=order.symbol, live_telemetry=live_telemetry):
        return live_telemetry
    quote_context = _build_dispatch_quote_snapshot(order.symbol, config=config)
    market_snapshot = quote_context.get("market_snapshot")
    if not isinstance(market_snapshot, Mapping):
        return live_telemetry
    prepared = dict(live_telemetry or {})
    prepared["market_snapshot"] = dict(market_snapshot)
    prepared["dispatch_quote_hydration"] = {
        "quote_source": quote_context.get("quote_source"),
        "quote_feed_label": quote_context.get("quote_feed_label"),
        "quote_fallback_used": bool(quote_context.get("quote_fallback_used")),
        "quote_connector_attempts": list(quote_context.get("quote_connector_attempts") or []),
        "quote_error": quote_context.get("quote_error"),
    }
    return prepared


def _availability_value_state(key: str, value: Any, direction: str = "") -> Optional[tuple[bool, str]]:
    """Return (is_available, normalized_detail) for explicit market availability evidence.

    None means the value is not availability evidence. False means dispatch must
    not touch a broker bridge.
    """
    key_token = str(key or "").strip().lower()
    direction_token = str(direction or "").strip().upper()
    if key_token in _MARKET_BOOL_KEYS:
        if isinstance(value, bool):
            return value, f"{key_token}={str(value).lower()}"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if int(value) == 0:
                return False, f"{key_token}=0"
            if int(value) == 1:
                return True, f"{key_token}=1"
        if isinstance(value, str):
            token = value.strip().upper().replace(" ", "_").replace("-", "_")
            if token in _MARKET_FALSE_TOKENS:
                return False, f"{key_token}={token}"
            if token in _MARKET_TRUE_TOKENS:
                return True, f"{key_token}={token}"
        return None

    if key_token == "trade_mode":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            mode = int(value)
            if mode in {0, 3}:
                return False, f"trade_mode={mode}"
            if mode in {1, 2}:
                if mode == 1 and direction_token in {"SHORT", "SELL"}:
                    return False, "trade_mode=LONGONLY blocks short entry"
                if mode == 2 and direction_token in {"LONG", "BUY"}:
                    return False, "trade_mode=SHORTONLY blocks long entry"
                return True, f"trade_mode={mode}"
            if mode == 4:
                return True, "trade_mode=4"

    if key_token in _MARKET_STATUS_KEYS and isinstance(value, str):
        token = value.strip().upper().replace(" ", "_").replace("-", "_")
        if token in _MARKET_FALSE_TOKENS:
            return False, f"{key_token}={token}"
        if token in _MARKET_TRUE_TOKENS:
            return True, f"{key_token}={token}"
        if key_token == "trade_mode":
            if token in {"LONGONLY", "LONG_ONLY", "SYMBOL_TRADE_MODE_LONGONLY"}:
                if direction_token in {"SHORT", "SELL"}:
                    return False, "trade_mode=LONGONLY blocks short entry"
                return True, f"{key_token}={token}"
            if token in {"SHORTONLY", "SHORT_ONLY", "SYMBOL_TRADE_MODE_SHORTONLY"}:
                if direction_token in {"LONG", "BUY"}:
                    return False, "trade_mode=SHORTONLY blocks long entry"
                return True, f"{key_token}={token}"
    return None


def _iter_market_evidence_sources(
    *,
    target_symbol: str,
    proposed_intent: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
) -> list[tuple[str, Mapping[str, Any]]]:
    sources: list[tuple[str, Mapping[str, Any]]] = []
    seen: set[int] = set()

    def add(label: str, value: Any, depth: int = 0) -> None:
        if not isinstance(value, Mapping):
            return
        ident = id(value)
        if ident in seen:
            return
        seen.add(ident)
        sources.append((label, value))
        if depth >= 2:
            return
        for key, nested in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            if isinstance(nested, Mapping):
                if key_lower in _MARKET_NESTED_KEYS:
                    add(f"{label}.{key_text}", nested, depth + 1)
                elif key_lower in _MARKET_SYMBOL_COLLECTION_KEYS:
                    for child_key, child_value in nested.items():
                        if _symbol_matches(child_key, target_symbol):
                            add(f"{label}.{key_text}.{child_key}", child_value, depth + 1)
            elif isinstance(nested, list) and key_lower in _MARKET_SYMBOL_COLLECTION_KEYS:
                for idx, item in enumerate(nested):
                    if isinstance(item, Mapping) and _symbol_matches(item.get("symbol"), target_symbol):
                        add(f"{label}.{key_text}[{idx}]", item, depth + 1)

    add("proposed_intent", proposed_intent or {})
    add("live_telemetry", live_telemetry or {})
    add("account_snapshot", account_snapshot or {})
    return sources


def _market_availability_report(
    *,
    order: BrokerOrderRequest,
    proposed_intent: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
    config: Any = None,
) -> dict[str, Any]:
    """Build a narrow pre-dispatch market/session availability report.

    The check is intentionally evidence-driven: explicit closed/unavailable
    evidence blocks. Missing evidence remains UNKNOWN so paper dispatch and
    legacy callers do not fail closed merely because they lack a market calendar.
    """
    direction = getattr(order.direction, "value", order.direction)
    blockers: list[str] = []
    positive: list[str] = []
    evidence: list[dict[str, Any]] = []
    for source, mapping in _iter_market_evidence_sources(
        target_symbol=order.symbol,
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
    ):
        freshness = _quote_freshness_evidence(source, mapping, config=config)
        if freshness is not None:
            evidence.append(freshness)
            if freshness["available"] is False:
                blockers.append(f"{source}.timestamp: {freshness['detail']}")
            else:
                positive.append(f"{source}.timestamp: {freshness['detail']}")
        scoped_for_generic_status = _source_label_allows_generic_status(source)
        for key, value in mapping.items():
            key_token = str(key or "").strip().lower()
            if key_token not in _MARKET_BOOL_KEYS and key_token not in _MARKET_STATUS_KEYS:
                continue
            if key_token == "status" and not scoped_for_generic_status:
                continue
            state = _availability_value_state(key_token, value, str(direction))
            if state is None:
                continue
            available, detail = state
            row = {
                "source": source,
                "key": key_token,
                "value": value,
                "available": available,
                "detail": detail,
            }
            evidence.append(row)
            if available is False:
                blockers.append(f"{source}.{key_token}: {detail}")
            else:
                positive.append(f"{source}.{key_token}: {detail}")

    status = "BLOCKED" if blockers else ("PASSED" if positive else "UNKNOWN")
    detail = (
        f"Market/session availability blocked {order.symbol}: " + "; ".join(blockers)
        if blockers
        else (
            f"Explicit market/session availability evidence permits {order.symbol}: "
            + "; ".join(positive[:4])
            if positive
            else f"No explicit market/session closure evidence was supplied for {order.symbol}."
        )
    )
    return {
        "report_kind": "cas_forex_market_availability_check",
        "status": status,
        "symbol": order.symbol,
        "direction": str(direction),
        "available": False if blockers else (True if positive else None),
        "block": bool(blockers),
        "blockers": blockers,
        "evidence": evidence,
        "detail": detail,
        "claim_boundary": (
            "This check only blocks when supplied evidence explicitly says a "
            "market/session/symbol is closed, unavailable, or trade-disabled. "
            "It does not create trades or prove a profitable opportunity."
        ),
    }


def _quote_freshness_evidence(
    source: str,
    mapping: Mapping[str, Any],
    *,
    config: Any = None,
) -> Optional[dict[str, Any]]:
    """Validate timestamp age for an explicit bid/ask market quote."""

    bid = _float_or_none(mapping.get("bid"))
    ask = _float_or_none(mapping.get("ask"))
    raw_timestamp = mapping.get("timestamp") or mapping.get("quote_timestamp")
    if bid is None or ask is None or ask < bid or raw_timestamp in (None, ""):
        return None
    try:
        parsed = ensure_utc(datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00")))
    except ValueError:
        return None
    age_seconds = (ensure_utc(utc_now()) - parsed).total_seconds()
    cfg = _resolve_config(config)
    try:
        max_age_seconds = max(
            1.0,
            float(getattr(cfg, "dispatch_quote_max_age_seconds", 120) or 120),
        )
    except (TypeError, ValueError):
        max_age_seconds = 120.0
    try:
        future_tolerance_seconds = max(
            0.0,
            float(getattr(cfg, "dispatch_quote_future_tolerance_seconds", 30) or 30),
        )
    except (TypeError, ValueError):
        future_tolerance_seconds = 30.0
    if age_seconds > max_age_seconds:
        available = False
        detail = (
            f"quote is stale ({age_seconds:.1f}s old > {max_age_seconds:.1f}s max)"
        )
    elif age_seconds < -future_tolerance_seconds:
        available = False
        detail = (
            "quote timestamp is materially ahead of the host clock "
            f"({abs(age_seconds):.1f}s > {future_tolerance_seconds:.1f}s tolerance)"
        )
    else:
        available = True
        detail = f"quote is fresh ({max(0.0, age_seconds):.1f}s old)"
    return {
        "source": source,
        "key": "timestamp",
        "value": str(raw_timestamp),
        "available": available,
        "age_seconds": round(age_seconds, 3),
        "max_age_seconds": max_age_seconds,
        "future_tolerance_seconds": future_tolerance_seconds,
        "detail": detail,
    }


_SPREAD_KEYS = frozenset(
    {
        "spread",
        "spread_pips",
        "spread_units",
        "current_spread",
        "current_spread_pips",
        "broker_spread_pips",
        "quote_spread_pips",
    }
)
_SLIPPAGE_KEYS = frozenset(
    {
        "slippage_pips",
        "expected_slippage_pips",
        "estimated_slippage_pips",
        "simulated_slippage_pips",
        "broker_slippage_pips",
        "quote_slippage_pips",
    }
)


def _float_or_none(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out


def _execution_quality_report(
    *,
    order: BrokerOrderRequest,
    proposed_intent: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
    config: Any = None,
) -> dict[str, Any]:
    """Block dispatch when explicit spread/slippage evidence exceeds owner tolerance."""
    try:
        from cas_forex.broker_control import resolve_broker_control

        ctrl = resolve_broker_control(config)
        max_spread = float(ctrl.max_spread_pips)
        max_slippage = float(ctrl.max_slippage_pips)
        strictness = ctrl.strictness
    except Exception:
        cfg = _resolve_config(config)
        max_spread = float(getattr(cfg, "broker_max_spread_pips", 5.0))
        max_slippage = float(getattr(cfg, "broker_max_slippage_pips", 3.0))
        strictness = str(getattr(cfg, "broker_strictness", "normal"))

    blockers: list[str] = []
    evidence: list[dict[str, Any]] = []

    def add_metric(source: str, metric: str, value: Any, limit: float) -> None:
        numeric = _float_or_none(value)
        if numeric is None:
            return
        row = {
            "source": source,
            "metric": metric,
            "value_pips": round(numeric, 5),
            "limit_pips": round(limit, 5),
            "within_tolerance": numeric <= limit,
        }
        evidence.append(row)
        if numeric > limit:
            blockers.append(f"{source}.{metric}={numeric:.2f} exceeds limit {limit:.2f}")

    for source, mapping in _iter_market_evidence_sources(
        target_symbol=order.symbol,
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
    ):
        for key, value in mapping.items():
            key_token = str(key or "").strip().lower()
            if key_token in _SPREAD_KEYS:
                add_metric(source, "spread_pips", value, max_spread)
            elif key_token in _SLIPPAGE_KEYS:
                add_metric(source, "slippage_pips", value, max_slippage)

        bid = _float_or_none(mapping.get("bid"))
        ask = _float_or_none(mapping.get("ask"))
        if bid is not None and ask is not None and ask >= bid:
            try:
                from cas_forex.instruments import price_unit_size

                unit = float(price_unit_size(order.symbol))
            except Exception:
                unit = 0.0001
            if unit > 0:
                add_metric(source, "spread_pips", (ask - bid) / unit, max_spread)

    status = "BLOCKED" if blockers else ("PASSED" if evidence else "UNKNOWN")
    detail = (
        f"Execution quality blocked {order.symbol}: " + "; ".join(blockers)
        if blockers
        else (
            f"Spread/slippage evidence is inside owner tolerance for {order.symbol}."
            if evidence
            else f"No explicit spread/slippage evidence was supplied for {order.symbol}."
        )
    )
    return {
        "report_kind": "cas_forex_execution_quality_check",
        "status": status,
        "symbol": order.symbol,
        "block": bool(blockers),
        "blockers": blockers,
        "evidence": evidence,
        "tolerances": {
            "max_spread_pips": max_spread,
            "max_slippage_pips": max_slippage,
            "strictness": strictness,
        },
        "detail": detail,
        "claim_boundary": (
            "This check enforces owner broker spread/slippage tolerances when "
            "quote or slippage evidence is supplied. Unknown evidence does not "
            "prove good execution quality and does not create a trade signal."
        ),
    }


_ENTRY_PRICE_KEYS = frozenset(
    {
        "entry",
        "entry_price",
        "intended_entry",
        "requested_price",
        "price",
        "current_price",
        "last",
        "last_price",
        "mid",
        "mark",
        "mark_price",
    }
)


def _order_entry_price_evidence(
    *,
    order: BrokerOrderRequest,
    proposed_intent: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    explicit = _float_or_none(getattr(order, "price", None))
    if explicit is not None and explicit > 0:
        return {
            "source": "order.price",
            "kind": "explicit_order_price",
            "entry_price": explicit,
        }

    direction = str(getattr(order.direction, "value", order.direction)).upper()
    generic_candidate: Optional[dict[str, Any]] = None
    for source, mapping in _iter_market_evidence_sources(
        target_symbol=order.symbol,
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
    ):
        bid = _float_or_none(mapping.get("bid"))
        ask = _float_or_none(mapping.get("ask"))
        if direction in {"LONG", "BUY"} and ask is not None and ask > 0:
            return {
                "source": f"{source}.ask",
                "kind": "quote_ask",
                "entry_price": ask,
            }
        if direction in {"SHORT", "SELL"} and bid is not None and bid > 0:
            return {
                "source": f"{source}.bid",
                "kind": "quote_bid",
                "entry_price": bid,
            }
        if generic_candidate is None:
            for key, value in mapping.items():
                if str(key or "").strip().lower() not in _ENTRY_PRICE_KEYS:
                    continue
                price = _float_or_none(value)
                if price is not None and price > 0:
                    generic_candidate = {
                        "source": f"{source}.{key}",
                        "kind": "generic_entry_price",
                        "entry_price": price,
                    }
                    break
    return generic_candidate


def _order_constraints_report(
    *,
    order: BrokerOrderRequest,
    proposed_intent: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
    bridge: Any = None,
    config: Any = None,
) -> dict[str, Any]:
    """Block dispatch when broker lot bounds or known stop distances are invalid."""
    try:
        from cas_forex.broker_control import resolve_broker_control

        ctrl = resolve_broker_control(config)
        min_lot = float(ctrl.min_lot)
        max_lot = float(ctrl.max_lot)
        min_stop_distance = float(ctrl.min_stop_distance_pips)
        strictness = ctrl.strictness
    except Exception:
        cfg = _resolve_config(config)
        min_lot = float(getattr(cfg, "broker_min_lot", 0.01))
        max_lot = float(getattr(cfg, "broker_max_lot", 1.0))
        min_stop_distance = float(getattr(cfg, "broker_min_stop_distance_pips", 5.0))
        strictness = str(getattr(cfg, "broker_strictness", "normal"))

    broker_symbol_contract = _broker_symbol_contract_report(
        order=order,
        bridge=bridge,
        config=config,
    )
    blockers: list[str] = []
    checks: list[dict[str, Any]] = []
    volume = float(order.volume)
    direction = str(getattr(order.direction, "value", order.direction)).upper()
    broker_constraints = dict(broker_symbol_contract.get("broker_contract_constraints") or {})
    broker_min_lot = _positive_float_or_none(broker_constraints.get("min_lot"))
    broker_max_lot = _positive_float_or_none(broker_constraints.get("max_lot"))
    broker_lot_step = _positive_float_or_none(broker_constraints.get("lot_step"))
    broker_min_stop_distance = _positive_float_or_none(
        broker_constraints.get("min_stop_distance_pips")
    )
    broker_contract_authoritative = _broker_contract_limits_are_authoritative(
        bridge=bridge,
        broker_symbol_contract=broker_symbol_contract,
    )
    if bool(broker_symbol_contract.get("block")):
        blockers.append(str(broker_symbol_contract.get("detail") or "Broker symbol/contract verification failed."))

    if broker_contract_authoritative:
        effective_min_lot = broker_min_lot if broker_min_lot is not None else min_lot
        positive_max_candidates = [
            value
            for value in (broker_max_lot if broker_max_lot is not None else max_lot,)
            if value is not None and value > 0
        ]
        effective_min_stop_distance = (
            broker_min_stop_distance
            if broker_min_stop_distance is not None
            else min_stop_distance
        )
    else:
        effective_min_lot = max(
            value for value in (min_lot, broker_min_lot) if value is not None
        ) if any(value is not None for value in (min_lot, broker_min_lot)) else None
        positive_max_candidates = [
            value
            for value in (max_lot, broker_max_lot)
            if value is not None and value > 0
        ]
        effective_min_stop_distance = max(
            value for value in (min_stop_distance, broker_min_stop_distance) if value is not None
        ) if any(value is not None for value in (min_stop_distance, broker_min_stop_distance)) else None
    effective_max_lot = min(positive_max_candidates) if positive_max_candidates else None

    lot_check = {
        "check": "lot_bounds",
        "volume_lots": volume,
        "min_lot": effective_min_lot,
        "max_lot": effective_max_lot,
        "configured_min_lot": min_lot,
        "configured_max_lot": max_lot,
        "broker_min_lot": broker_min_lot,
        "broker_max_lot": broker_max_lot,
        "lot_step": broker_lot_step,
        "configured_lot_bounds_apply": not broker_contract_authoritative,
        "lot_bound_authority": (
            "native_broker_contract"
            if broker_contract_authoritative
            else "configured_simulator_tolerance_and_available_contract"
        ),
        "selected_broker_symbol": broker_symbol_contract.get("selected_broker_symbol"),
        "status": "PASSED",
    }
    base_lot = effective_min_lot if effective_min_lot is not None else 0.0
    symbol_label = str(broker_symbol_contract.get("selected_broker_symbol") or order.symbol)
    if effective_max_lot is not None and effective_min_lot is not None and effective_min_lot > effective_max_lot:
        lot_check["status"] = "BLOCKED"
        lot_check["detail"] = (
            f"Effective broker max lot {effective_max_lot:g} is below effective min lot {effective_min_lot:g}."
        )
        blockers.append(str(lot_check["detail"]))
    elif effective_min_lot is not None and effective_min_lot > 0 and volume < effective_min_lot - 1e-9:
        lot_check["status"] = "BLOCKED"
        lot_check["detail"] = f"Order volume {volume:g} is below broker minimum {effective_min_lot:g} lots."
        blockers.append(str(lot_check["detail"]))
    elif effective_max_lot is not None and effective_max_lot > 0 and volume > effective_max_lot + 1e-9:
        lot_check["status"] = "BLOCKED"
        lot_check["detail"] = f"Order volume {volume:g} exceeds broker maximum {effective_max_lot:g} lots."
        blockers.append(str(lot_check["detail"]))
    elif broker_lot_step is not None and not _volume_matches_step(volume, base_lot, broker_lot_step):
        lot_check["status"] = "BLOCKED"
        lot_check["detail"] = (
            f"Order volume {volume:g} does not align with broker lot step {broker_lot_step:g} "
            f"for {symbol_label}."
        )
        blockers.append(str(lot_check["detail"]))
    else:
        lot_check["detail"] = "Order volume is inside broker lot bounds."
    checks.append(lot_check)

    entry = _order_entry_price_evidence(
        order=order,
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
    )
    if entry is None:
        checks.append(
            {
                "check": "minimum_stop_distance",
                "status": "UNKNOWN",
                "detail": (
                    "No explicit entry price or side-specific quote was supplied, "
                    "so dispatch could not verify broker minimum SL/TP distance."
                ),
                "configured_min_stop_distance_pips": min_stop_distance,
                "broker_min_stop_distance_pips": broker_min_stop_distance,
                "min_stop_distance_pips": effective_min_stop_distance,
                "selected_broker_symbol": broker_symbol_contract.get("selected_broker_symbol"),
            }
        )
    else:
        try:
            from cas_forex.instruments import price_unit_size

            unit = float(price_unit_size(order.symbol))
        except Exception:
            unit = 0.0001
        if unit <= 0:
            unit = 0.0001
        entry_price = float(entry["entry_price"])
        if direction in {"LONG", "BUY"}:
            sl_distance = (entry_price - float(order.stop_loss)) / unit
            tp_distance = (float(order.take_profit) - entry_price) / unit
        else:
            sl_distance = (float(order.stop_loss) - entry_price) / unit
            tp_distance = (entry_price - float(order.take_profit)) / unit
        stop_check = {
            "check": "minimum_stop_distance",
            "status": "PASSED",
            "entry_price": entry_price,
            "entry_source": entry.get("source"),
            "entry_kind": entry.get("kind"),
            "price_unit": unit,
            "stop_loss_distance_pips": round(sl_distance, 5),
            "take_profit_distance_pips": round(tp_distance, 5),
            "configured_min_stop_distance_pips": min_stop_distance,
            "broker_min_stop_distance_pips": broker_min_stop_distance,
            "min_stop_distance_pips": effective_min_stop_distance,
            "selected_broker_symbol": broker_symbol_contract.get("selected_broker_symbol"),
        }
        effective_distance = effective_min_stop_distance if effective_min_stop_distance is not None else 0.0

        distance_blockers: list[str] = []
        for label, distance in (("stop_loss", sl_distance), ("take_profit", tp_distance)):
            if distance <= 0:
                distance_blockers.append(
                    f"{label} is on the wrong side of entry {entry_price:g} for {direction}."
                )
            elif effective_distance > 0 and distance < effective_distance - 1e-9:
                distance_blockers.append(
                    f"{label} distance {distance:.2f} is below broker minimum {effective_distance:.2f} pips."
                )
        if distance_blockers:
            stop_check["status"] = "BLOCKED"
            stop_check["detail"] = "; ".join(distance_blockers)
            blockers.extend(distance_blockers)
        else:
            stop_check["detail"] = "Known entry price shows SL/TP distances meet configured broker constraints."
        checks.append(stop_check)

    checks.append(
        {
            "check": "broker_symbol_contract",
            "status": str(broker_symbol_contract.get("status") or "UNAVAILABLE"),
            "detail": str(
                broker_symbol_contract.get("detail")
                or "Broker symbol/contract metadata was unavailable at dispatch preflight."
            ),
            "selected_broker_symbol": broker_symbol_contract.get("selected_broker_symbol"),
            "resolution_source": broker_symbol_contract.get("resolution_source"),
            "resolution_status": broker_symbol_contract.get("resolution_status"),
            "metadata_available": bool(broker_symbol_contract.get("metadata_available")),
            "broker_contract_constraints": broker_constraints,
        }
    )

    unknown_checks = any(str(check.get("status")) == "UNKNOWN" for check in checks)
    status = "BLOCKED" if blockers else ("PARTIAL" if unknown_checks else "PASSED")
    if blockers:
        detail = f"Broker order constraints blocked {order.symbol}: " + "; ".join(blockers)
    elif unknown_checks:
        detail = (
            f"Broker lot bounds passed for {order.symbol}; stop distance could not be fully verified "
            "without explicit entry or quote evidence."
        )
    else:
        detail = f"Broker lot and known stop-distance constraints passed for {order.symbol}."

    return {
        "report_kind": "cas_forex_order_constraints_check",
        "status": status,
        "symbol": order.symbol,
        "direction": direction,
        "block": bool(blockers),
        "blockers": blockers,
        "selected_broker_symbol": broker_symbol_contract.get("selected_broker_symbol"),
        "broker_symbol_resolution": {
            "status": broker_symbol_contract.get("resolution_status"),
            "source": broker_symbol_contract.get("resolution_source"),
            "detail": broker_symbol_contract.get("resolution_detail"),
        },
        "broker_contract_constraints": broker_constraints,
        "checks": checks,
        "tolerances": {
            "min_lot": min_lot,
            "max_lot": max_lot,
            "min_stop_distance_pips": min_stop_distance,
            "strictness": strictness,
        },
        "detail": detail,
        "claim_boundary": (
            "This deterministic dispatch check enforces simulator lot tolerances "
            "for simulated execution, authoritative native broker contract bounds "
            "for connected MT5 execution, and verifies "
            "SL/TP distance when entry-price evidence is available. It does not "
            "choose symbols, size trades, or prove edge."
        ),
    }


def _broker_contract_limits_are_authoritative(
    *,
    bridge: Any,
    broker_symbol_contract: Mapping[str, Any],
) -> bool:
    """Use native MT5 contract limits instead of simulator tolerance defaults."""
    if bridge is None:
        return False
    if str(broker_symbol_contract.get("status") or "").upper() != "PASSED":
        return False
    if not broker_symbol_contract.get("selected_broker_symbol"):
        return False

    explicit = getattr(bridge, "broker_contract_limits_authoritative", None)
    if callable(explicit):
        try:
            return bool(explicit())
        except Exception:
            return False
    if explicit is not None:
        return bool(explicit)

    mt5 = getattr(bridge, "_mt5", None)
    return mt5 is not None and callable(getattr(mt5, "symbol_info", None))


def _broker_symbol_contract_report(
    *,
    order: BrokerOrderRequest,
    bridge: Any = None,
    config: Any = None,
) -> dict[str, Any]:
    report = {
        "report_kind": "cas_forex_broker_symbol_contract_check",
        "status": "UNAVAILABLE",
        "block": False,
        "detail": "",
        "metadata_available": False,
        "bridge_connected": None,
        "selected_broker_symbol": None,
        "resolution_source": None,
        "resolution_status": None,
        "resolution_detail": None,
        "broker_contract_constraints": {},
    }
    if bridge is None:
        report["detail"] = "No broker bridge was supplied for broker symbol/contract verification."
        return report

    broker_api, bridge_connected, connect_attempted = _broker_symbol_api(bridge)
    report["bridge_connected"] = bridge_connected
    report["connect_attempted"] = connect_attempted
    if broker_api is None:
        report["detail"] = "Bridge does not expose broker symbol metadata for contract verification."
        return report

    report["metadata_available"] = True
    try:
        from cas_forex.instruments import resolve_broker_symbol
    except Exception as exc:
        report["status"] = "BLOCKED"
        report["block"] = True
        report["detail"] = f"Broker symbol verification unavailable: {type(exc).__name__}: {exc}"
        return report

    cfg = _resolve_config(config)
    resolution = resolve_broker_symbol(
        order.symbol,
        broker=broker_api,
        overrides=getattr(cfg, "mt5_symbol_overrides", ""),
        select=bool(bridge_connected) if bridge_connected is not None else True,
    )
    report["selected_broker_symbol"] = resolution.selected_symbol
    report["resolution_source"] = resolution.resolution_source
    report["resolution_status"] = resolution.status
    report["resolution_detail"] = resolution.detail
    if resolution.status != "RESOLVED" or not resolution.selected_symbol:
        report["status"] = "BLOCKED"
        report["block"] = True
        report["detail"] = str(
            resolution.detail
            or f"Broker symbol could not be resolved for {order.symbol}."
        )
        return report

    info = _safe_symbol_info(broker_api, resolution.selected_symbol)
    contract = _contract_snapshot(info)
    constraints = _constraint_summary(contract, canonical_symbol=order.symbol)
    report["broker_contract_constraints"] = constraints
    trade_mode = contract.get("trade_mode")
    trade_mode_state = _availability_value_state(
        "trade_mode",
        trade_mode,
        str(getattr(order.direction, "value", order.direction)).upper(),
    )
    if trade_mode_state is not None and trade_mode_state[0] is False:
        report["status"] = "BLOCKED"
        report["block"] = True
        report["detail"] = (
            f"Broker symbol {resolution.selected_symbol} is not tradable for this order: "
            f"{trade_mode_state[1]}."
        )
        return report

    report["status"] = "PASSED"
    report["detail"] = (
        f"Broker symbol {resolution.selected_symbol} resolved with contract metadata ready for dispatch checks."
    )
    return report


def _broker_symbol_api(bridge: Any) -> tuple[Any, Optional[bool], bool]:
    connect_attempted = False
    broker_api = _extract_symbol_metadata_api(bridge)
    if broker_api is not None:
        return broker_api, _probe_bridge_connected(bridge), connect_attempted
    connect = getattr(bridge, "connect", None)
    if callable(connect):
        connect_attempted = True
        try:
            connect()
        except Exception:
            pass
    broker_api = _extract_symbol_metadata_api(bridge)
    return broker_api, _probe_bridge_connected(bridge), connect_attempted


def _extract_symbol_metadata_api(bridge: Any) -> Any:
    mt5 = getattr(bridge, "_mt5", None)
    if mt5 is not None and callable(getattr(mt5, "symbol_info", None)):
        return mt5
    if callable(getattr(bridge, "symbol_info", None)):
        return bridge
    return None


def _probe_bridge_connected(bridge: Any) -> Optional[bool]:
    is_connected = getattr(bridge, "is_connected", None)
    if callable(is_connected):
        try:
            return bool(is_connected())
        except Exception:
            return None
    return None


def _safe_symbol_info(broker: Any, symbol: Any) -> Any:
    if broker is None or not symbol:
        return None
    try:
        return broker.symbol_info(symbol)
    except Exception:
        return None


def _contract_snapshot(info: Any) -> dict[str, Any]:
    if info is None:
        return {}
    fields = (
        "trade_mode",
        "digits",
        "point",
        "volume_min",
        "volume_max",
        "volume_step",
        "trade_contract_size",
        "trade_tick_size",
        "trade_tick_value",
        "trade_stops_level",
        "trade_freeze_level",
    )
    out: dict[str, Any] = {}
    for field in fields:
        value = getattr(info, field, None)
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            out[field] = value
            continue
        try:
            out[field] = float(value)
        except (TypeError, ValueError):
            out[field] = str(value)
    return out


def _constraint_summary(contract: Mapping[str, Any], *, canonical_symbol: str) -> dict[str, Any]:
    point = _positive_float_or_none(contract.get("point"))
    try:
        from cas_forex.instruments import price_unit_size

        unit = float(price_unit_size(canonical_symbol))
    except Exception:
        unit = 0.0001
    if unit <= 0:
        unit = 0.0001
    stop_level_points = _positive_float_or_none(contract.get("trade_stops_level")) or 0.0
    freeze_level_points = _positive_float_or_none(contract.get("trade_freeze_level")) or 0.0
    min_stop_distance = None
    if point is not None:
        min_stop_distance = max(stop_level_points, freeze_level_points) * point / unit
    return {
        "min_lot": _positive_float_or_none(contract.get("volume_min")),
        "max_lot": _positive_float_or_none(contract.get("volume_max")),
        "lot_step": _positive_float_or_none(contract.get("volume_step")),
        "stop_level_points": stop_level_points or None,
        "freeze_level_points": freeze_level_points or None,
        "point": point,
        "digits": contract.get("digits"),
        "contract_size": _positive_float_or_none(contract.get("trade_contract_size")),
        "tick_size": _positive_float_or_none(contract.get("trade_tick_size")),
        "tick_value": _positive_float_or_none(contract.get("trade_tick_value")),
        "min_stop_distance_pips": min_stop_distance,
    }


def _volume_matches_step(volume: float, min_lot: float, step: float) -> bool:
    if step <= 0:
        return True
    base = min_lot if min_lot > 0 else 0.0
    if volume < base - 1e-9:
        return False
    steps = (volume - base) / step
    return abs(steps - round(steps)) <= 1e-8


_MACRO_BOOL_KEYS = frozenset(
    {
        "macro_blackout_active",
        "news_blackout_active",
        "blackout_active",
        "high_impact_news_active",
        "macro_shock_active",
        "news_event_active",
    }
)
_MACRO_STATUS_KEYS = frozenset(
    {
        "macro_status",
        "macro_gate_status",
        "news_status",
        "blackout_status",
        "calendar_status",
        "status",
    }
)
_MACRO_BLOCK_TOKENS = frozenset(
    {
        "FAIL",
        "FAILED",
        "BLOCK",
        "BLOCKED",
        "BLACKOUT",
        "MACRO_BLACKOUT",
        "NEWS_BLACKOUT",
        "ACTIVE",
        "LIVE_LOCKED",
        "LOCKED",
        "SHOCK",
        "MACRO_SHOCK",
    }
)
_MACRO_PASS_TOKENS = frozenset(
    {
        "PASS",
        "PASSED",
        "CLEAR",
        "CLEARED",
        "OK",
        "INACTIVE",
        "NO_BLACKOUT",
        "NO_MACRO_BLACKOUT",
    }
)
_MACRO_NESTED_KEYS = frozenset(
    {
        "macro",
        "macro_gate",
        "macro_blackout",
        "news",
        "news_gate",
        "economic_calendar",
        "calendar",
        "event",
        "event_context",
    }
)
_MACRO_EVENT_COLLECTION_KEYS = frozenset(
    {
        "events",
        "macro_events",
        "news_events",
        "economic_events",
        "calendar_events",
        "upcoming_events",
    }
)


def _iter_macro_evidence_sources(
    *,
    proposed_intent: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
) -> list[tuple[str, Mapping[str, Any]]]:
    sources: list[tuple[str, Mapping[str, Any]]] = []
    seen: set[int] = set()

    def add(label: str, value: Any, depth: int = 0) -> None:
        if not isinstance(value, Mapping):
            return
        ident = id(value)
        if ident in seen:
            return
        seen.add(ident)
        sources.append((label, value))
        if depth >= 3:
            return
        for key, nested in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            if isinstance(nested, Mapping) and key_lower in _MACRO_NESTED_KEYS:
                add(f"{label}.{key_text}", nested, depth + 1)
            elif isinstance(nested, list) and key_lower in _MACRO_EVENT_COLLECTION_KEYS:
                for idx, item in enumerate(nested):
                    if isinstance(item, Mapping):
                        add(f"{label}.{key_text}[{idx}]", item, depth + 1)

    add("proposed_intent", proposed_intent or {})
    add("live_telemetry", live_telemetry or {})
    add("account_snapshot", account_snapshot or {})
    return sources


def _macro_source_allows_generic_status(label: str) -> bool:
    token = label.lower()
    return any(part in token for part in ("macro", "news", "calendar", "event", "blackout"))


def _parse_iso_utc(value: Any) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return ensure_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        return None


def _macro_now_from_sources(sources: Sequence[tuple[str, Mapping[str, Any]]]) -> datetime:
    for _label, mapping in sources:
        for key in ("macro_now_iso", "news_now_iso", "now_iso", "checked_at", "as_of_iso"):
            parsed = _parse_iso_utc(mapping.get(key))
            if parsed is not None:
                return parsed
    return ensure_utc(utc_now())


def _macro_window_minutes(event: Mapping[str, Any], cfg: Any) -> tuple[int, int]:
    event_type = str(event.get("event_type") or event.get("type") or event.get("name") or "").upper()
    is_fomc = "FOMC" in event_type or "RATE_DECISION" in event_type or "FED" in event_type
    default_before = getattr(
        cfg,
        "blackout_before_fomc_minutes" if is_fomc else "blackout_before_nfp_minutes",
        15,
    )
    default_after = getattr(
        cfg,
        "blackout_after_fomc_minutes" if is_fomc else "blackout_after_nfp_minutes",
        15,
    )
    before = event.get("blackout_before_minutes", event.get("before_minutes", default_before))
    after = event.get("blackout_after_minutes", event.get("after_minutes", default_after))
    try:
        before_i = max(0, int(before))
    except (TypeError, ValueError):
        before_i = int(default_before or 15)
    try:
        after_i = max(0, int(after))
    except (TypeError, ValueError):
        after_i = int(default_after or 15)
    return before_i, after_i


def _macro_event_time(event: Mapping[str, Any]) -> Optional[datetime]:
    for key in ("scheduled_at_utc", "scheduled_at", "event_time_iso", "release_time", "release_time_utc", "time"):
        parsed = _parse_iso_utc(event.get(key))
        if parsed is not None:
            return parsed
    return None


def _macro_event_blocks(source: str, event: Mapping[str, Any], *, now: datetime, cfg: Any) -> Optional[dict[str, Any]]:
    scheduled = _macro_event_time(event)
    if scheduled is None:
        return None
    impact = str(event.get("impact") or event.get("importance") or "").upper()
    high_impact = impact in {"HIGH", "HIGH_IMPACT", "HIGH IMPACT", "HIGH IMPACT EXPECTED"} or bool(
        event.get("high_impact") is True
    )
    shock_active = bool(event.get("shock_active") or event.get("macro_shock_active"))
    if not high_impact and not shock_active:
        return None
    before, after = _macro_window_minutes(event, cfg)
    start = scheduled - timedelta(minutes=before)
    end = scheduled + timedelta(minutes=after)
    active = start <= now <= end
    event_type = str(event.get("event_type") or event.get("type") or event.get("name") or "macro_event")
    return {
        "source": source,
        "event_id": event.get("event_id") or event.get("id"),
        "event_type": event_type,
        "currency": event.get("currency"),
        "impact": impact or ("HIGH" if high_impact else ""),
        "scheduled_at_utc": scheduled.isoformat(),
        "blackout_start": start.isoformat(),
        "blackout_end": end.isoformat(),
        "active": active,
        "shock_active": shock_active,
        "detail": (
            f"{source}.{event_type} active {start.isoformat()}..{end.isoformat()}"
            if active
            else f"{source}.{event_type} outside blackout window"
        ),
    }


def _static_macro_blackout_evidence(*, now: datetime, cfg: Any, static_enabled: bool) -> Optional[dict[str, Any]]:
    if not static_enabled:
        return None
    try:
        from cas_forex.schemas.decision import GateStatus
        from cas_forex.verifier.macro_gate import MacroGate

        gate = MacroGate(
            blackout_before=int(getattr(cfg, "blackout_before_nfp_minutes", 15)),
            blackout_after=int(getattr(cfg, "blackout_after_nfp_minutes", 15)),
            fomc_before=int(getattr(cfg, "blackout_before_fomc_minutes", 15)),
            fomc_after=int(getattr(cfg, "blackout_after_fomc_minutes", 15)),
        )
        decision = gate.evaluate(now)
        failed = decision.status == GateStatus.FAIL or str(decision.status).upper().endswith("FAIL")
        return {
            "source": "static_macro_calendar",
            "active": bool(failed),
            "status": str(getattr(decision.status, "value", decision.status)),
            "reason": decision.reason,
            "evidence": dict(decision.evidence or {}),
        }
    except Exception as exc:
        return {
            "source": "static_macro_calendar",
            "active": False,
            "status": "UNAVAILABLE",
            "reason": f"Static macro calendar unavailable: {type(exc).__name__}: {exc}",
            "evidence": {},
        }


def _configured_economic_calendar_evidence(*, now: datetime, cfg: Any) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]], list[str]]:
    try:
        from cas_forex.economic_calendar_feed import economic_calendar_events_for_dispatch

        report = economic_calendar_events_for_dispatch(config=cfg, now=now)
    except Exception as exc:
        report = {
            "report_kind": "cas_forex_economic_calendar_feed",
            "status": "UNAVAILABLE",
            "configured": False,
            "event_count": 0,
            "events": [],
            "detail": f"Economic-calendar feed check failed: {type(exc).__name__}: {exc}",
            "error": f"{type(exc).__name__}: {exc}",
            "fail_closed_on_error": bool(getattr(cfg, "economic_calendar_fail_closed", False)),
            "claim_boundary": (
                "Economic calendar feed loading failed before dispatch. This row is "
                "diagnostic only and does not authorize trading."
            ),
        }

    evidence: list[dict[str, Any]] = []
    blockers: list[str] = []
    configured = bool(report.get("configured"))
    status = str(report.get("status") or "UNKNOWN").upper()
    if configured or status not in {"UNCONFIGURED"}:
        status_row = {
            "source": "economic_calendar_feed",
            "key": "economic_calendar_feed_status",
            "value": status,
            "active": False,
            "configured": configured,
            "event_count": int(report.get("event_count") or 0),
            "cache_age_seconds": report.get("cache_age_seconds"),
            "cache_stale": bool(report.get("cache_stale")),
            "detail": str(report.get("detail") or "Economic-calendar feed status recorded."),
        }
        evidence.append(status_row)
    if status in {"FETCH_FAILED", "UNAVAILABLE"} and bool(report.get("fail_closed_on_error")):
        detail = "economic_calendar_feed unavailable and fail-closed mode is enabled"
        blockers.append(detail)
        evidence.append(
            {
                "source": "economic_calendar_feed",
                "key": "economic_calendar_fail_closed",
                "value": status,
                "active": True,
                "detail": detail,
            }
        )
    for event in _rows(report.get("events")):
        event_row = _macro_event_blocks("economic_calendar_feed", event, now=now, cfg=cfg)
        if event_row is not None:
            evidence.append(event_row)
            if event_row.get("active"):
                blockers.append(str(event_row.get("detail") or "economic_calendar_feed event active"))
    return report, evidence, blockers


def _rows(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _macro_calendar_source_summary(evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    external_event_rows = [
        row
        for row in evidence
        if row.get("scheduled_at_utc") and str(row.get("source") or "") != "static_macro_calendar"
    ]
    static_rows = [row for row in evidence if str(row.get("source") or "") == "static_macro_calendar"]
    generic_rows = [
        row
        for row in evidence
        if str(row.get("key") or "") in _MACRO_BOOL_KEYS or str(row.get("key") or "") in _MACRO_STATUS_KEYS
    ]

    if external_event_rows:
        source_status = "EXTERNAL_EVENT_EVIDENCE"
        detail = (
            f"{len(external_event_rows)} external/live macro event payload(s) supplied; "
            "dispatch used event timestamps and configured blackout windows."
        )
    elif static_rows:
        source_status = "STATIC_SEED_CALENDAR"
        detail = (
            "No external/live economic-calendar event payload was supplied; dispatch used "
            "the static seed macro calendar plus any generic blackout/status flags present."
        )
    elif generic_rows:
        source_status = "GENERIC_STATUS_EVIDENCE"
        detail = (
            "Dispatch used generic macro/news blackout status flags only; no timestamped "
            "external event payload or static calendar evidence was available."
        )
    else:
        source_status = "NO_EVENT_EVIDENCE"
        detail = (
            "No macro/news blackout evidence was supplied. This is not proof that no "
            "market-moving event exists."
        )

    return {
        "calendar_source_status": source_status,
        "calendar_source_detail": detail,
        "external_event_count": len(external_event_rows),
        "static_seed_used": bool(static_rows),
        "generic_status_evidence_count": len(generic_rows),
    }


def _macro_blackout_report(
    *,
    order: BrokerOrderRequest,
    proposed_intent: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
    config: Any = None,
) -> dict[str, Any]:
    cfg = _resolve_config(config)
    enabled = bool(getattr(cfg, "macro_blackout_enabled", False))
    explicit_config_support = config is None or hasattr(config, "macro_blackout_enabled")
    sources = _iter_macro_evidence_sources(
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
    )
    now = _macro_now_from_sources(sources)
    blockers: list[str] = []
    evidence: list[dict[str, Any]] = []

    if not enabled:
        return {
            "report_kind": "cas_forex_macro_blackout_check",
            "status": "DISABLED",
            "symbol": order.symbol,
            "block": False,
            "checked_at_iso": now.isoformat(),
            "blockers": [],
            "evidence": [],
            "calendar_source_status": "DISABLED",
            "calendar_source_detail": "Macro/news blackout gate is disabled by config.",
            "external_event_count": 0,
            "static_seed_used": False,
            "generic_status_evidence_count": 0,
            "detail": "Macro/news blackout gate is disabled by config.",
            "claim_boundary": (
                "Macro blackout diagnostics are dispatch evidence only. They do not create trades, "
                "authorize live trading, or replace a real economic-calendar feed."
            ),
        }

    for source, mapping in sources:
        scoped_for_status = _macro_source_allows_generic_status(source)
        for key, value in mapping.items():
            key_token = str(key or "").strip().lower()
            if key_token in _MACRO_BOOL_KEYS and isinstance(value, bool):
                row = {
                    "source": source,
                    "key": key_token,
                    "value": value,
                    "active": value,
                    "detail": f"{source}.{key_token}={str(value).lower()}",
                }
                evidence.append(row)
                if value:
                    blockers.append(row["detail"])
            elif key_token in _MACRO_STATUS_KEYS and (key_token != "status" or scoped_for_status):
                token = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")
                if token in _MACRO_BLOCK_TOKENS or token.startswith("FAIL"):
                    row = {
                        "source": source,
                        "key": key_token,
                        "value": value,
                        "active": True,
                        "detail": f"{source}.{key_token}={token}",
                    }
                    evidence.append(row)
                    blockers.append(row["detail"])
                elif token in _MACRO_PASS_TOKENS:
                    evidence.append({
                        "source": source,
                        "key": key_token,
                        "value": value,
                        "active": False,
                        "detail": f"{source}.{key_token}={token}",
                    })

        event_row = _macro_event_blocks(source, mapping, now=now, cfg=cfg)
        if event_row is not None:
            evidence.append(event_row)
            if event_row.get("active"):
                blockers.append(str(event_row.get("detail") or source))

    economic_calendar_feed, feed_evidence, feed_blockers = _configured_economic_calendar_evidence(now=now, cfg=cfg)
    evidence.extend(feed_evidence)
    blockers.extend(feed_blockers)

    static_evidence = _static_macro_blackout_evidence(
        now=now,
        cfg=cfg,
        static_enabled=explicit_config_support,
    )
    if static_evidence is not None:
        evidence.append(static_evidence)
        if static_evidence.get("active"):
            blockers.append(str(static_evidence.get("reason") or "static macro blackout active"))

    status = "BLOCKED" if blockers else ("PASSED" if evidence else "UNKNOWN")
    detail = (
        f"Macro/news blackout blocked {order.symbol}: " + "; ".join(blockers)
        if blockers
        else (
            f"No active macro/news blackout for {order.symbol} at {now.isoformat()}."
            if evidence
            else f"No macro/news blackout evidence was supplied for {order.symbol}."
        )
    )
    source_summary = _macro_calendar_source_summary(evidence)
    return {
        "report_kind": "cas_forex_macro_blackout_check",
        "status": status,
        "symbol": order.symbol,
        "block": bool(blockers),
        "checked_at_iso": now.isoformat(),
        "blockers": blockers,
        "evidence": evidence,
        "economic_calendar_feed": economic_calendar_feed,
        **source_summary,
        "detail": detail,
        "claim_boundary": (
            "This check blocks dispatch during active macro/news blackout evidence. "
            "It does not create trades, authorize live trading, or replace a real "
            "economic-calendar feed."
        ),
    }


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
        updated = replace(
            result,
            audit_attempt_id=str(record.get("attempt_id") or ""),
            audit_status=str(record.get("status") or ""),
            audit_error=None,
            execution_provenance=dict(record.get("execution_provenance") or result.execution_provenance or {}),
        )
        _notify_dispatch_result(updated, source=source)
        return updated
    except Exception as exc:
        updated = replace(result, audit_error=str(exc))
        _notify_dispatch_result(updated, source=source)
        return updated


def record_unresolved_real_dispatch_error_to_audit(
    *,
    result: DispatchResult,
    audit_store: Any = None,
    started_attempt: Optional[Mapping[str, Any]] = None,
    order: Any = None,
    proposed_intent: Optional[Mapping[str, Any]] = None,
    config: Any = None,
    bridge: Any = None,
    source: str = "order_dispatch",
    error: Any = None,
) -> DispatchResult:
    """Persist a real-broker dispatch error as unresolved when touch is uncertain."""

    if not started_attempt:
        updated = result
        _notify_dispatch_result(updated, source=source)
        return updated
    try:
        store = _resolve_audit_store(audit_store)
        mode = _mode_from_config(config)
        record = store.record_bridge_touch_unknown_error(
            started_attempt=started_attempt,
            error=error,
            order=order,
            proposed_intent=proposed_intent,
            mode=mode,
            bridge_name=bridge.__class__.__name__ if bridge is not None else "",
            source=source,
            execution_provenance=result.execution_provenance,
        )
        updated = replace(
            result,
            audit_attempt_id=str(record.get("attempt_id") or ""),
            audit_status=str(record.get("status") or ""),
            audit_error=None,
            execution_provenance=dict(record.get("execution_provenance") or result.execution_provenance or {}),
        )
        _notify_dispatch_result(updated, source=source)
        return updated
    except Exception as exc:
        updated = replace(
            result,
            audit_attempt_id=str((started_attempt or {}).get("attempt_id") or ""),
            audit_status=str((started_attempt or {}).get("status") or ""),
            audit_error=str(exc),
        )
        _notify_dispatch_result(updated, source=source)
        return updated


def _notify_dispatch_result(result: DispatchResult, *, source: str) -> None:
    try:
        from cas_forex.critical_notifications import (
            build_dispatch_result_event,
            emit_critical_notification,
        )

        event = build_dispatch_result_event(result)
        if event is not None:
            emit_critical_notification(event, source=str(source or "order_dispatch"))
    except Exception:
        return


def _duplicate_suppression_reason(previous_attempt: Optional[Mapping[str, Any]]) -> str | None:
    if not previous_attempt:
        return None
    attempt_id = str(previous_attempt.get("attempt_id") or "unknown")
    if not bool(previous_attempt.get("result_finalized")):
        if bool(previous_attempt.get("is_real_attempt")):
            return (
                "Duplicate dispatch suppressed: an unresolved real broker attempt "
                f"already exists for this order (attempt_id={attempt_id}). "
                "Reconcile broker truth before retrying."
            )
        return None
    result_status = str(previous_attempt.get("result_status") or "")
    if bool(previous_attempt.get("dispatched_to_bridge")) and (
        bool(previous_attempt.get("executed"))
        or result_status in {"BROKER_EXECUTED", "BROKER_PARTIAL", "BROKER_PENDING"}
    ):
        outcome = previous_attempt.get("outcome") if isinstance(previous_attempt.get("outcome"), Mapping) else {}
        ticket = outcome.get("broker_ticket") if isinstance(outcome, Mapping) else None
        ticket_detail = f", broker_ticket={ticket}" if ticket not in {None, ""} else ""
        if str(previous_attempt.get("idempotency_match_type") or "") == "RECENT_AUTOMATION_ORDER_SHAPE":
            window = previous_attempt.get("near_duplicate_seconds")
            window_detail = f" within {window}s" if window not in {None, ""} else ""
            return (
                "Duplicate dispatch suppressed: a similar automation order shape "
                f"already reached the bridge{window_detail} "
                f"(attempt_id={attempt_id}{ticket_detail})."
            )
        return (
            "Duplicate dispatch suppressed: this exact order_id/decision_ref "
            f"already reached the bridge (attempt_id={attempt_id}{ticket_detail})."
        )
    return None


def attach_pre_trade_estimate_to_intent(
    intent: Mapping[str, Any],
    estimate: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach pre-trade money estimates to the risk-gate intent.

    The risk gate is still deterministic and server-side; these fields let it
    evaluate the proposed order's own margin and stop-risk impact instead of
    checking only the already-open book.
    """

    enriched = dict(intent)
    if not isinstance(estimate, Mapping):
        return enriched
    for key in (
        "estimated_margin_required_usd",
        "estimated_margin_after_usd",
        "estimated_free_margin_after_usd",
        "estimated_margin_utilization_after_pct",
        "risk_at_stop_usd",
        "risk_at_stop_pct_equity",
        "account_equity_usd",
        "unit_value_source",
    ):
        value = estimate.get(key)
        if value is not None:
            enriched[key] = value
    estimated_stop_risk = _positive_float_or_none(estimate.get("risk_at_stop_usd"))
    upstream_expected_loss = _positive_float_or_none(enriched.get("expected_loss_usd"))
    if estimated_stop_risk is not None:
        enriched["expected_loss_usd"] = max(
            value for value in (estimated_stop_risk, upstream_expected_loss) if value is not None
        )
    enriched["pre_trade_estimate_status"] = estimate.get("status")
    return enriched


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
            f"mode={outcome.broker_mode.value} external_broker={outcome.is_real_broker} "
            f"account_mode={_outcome_account_mode(outcome)} "
            f"live_money={_outcome_is_live_money(outcome)}."
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
    if strategy_id is not None and "strategy_id" not in intent_dict:
        intent_dict["strategy_id"] = strategy_id
    if "ai_action" not in intent_dict:
        intent_dict["ai_action"] = ai_action
    pre_trade_estimate = build_pre_trade_money_estimate(
        symbol=order.symbol,
        direction=direction,
        lots=float(order.volume),
        price=float(order.price),
        stop_loss=float(order.stop_loss),
        take_profit=float(order.take_profit),
        proposed_intent=intent_dict,
        account_snapshot=account_snapshot,
        bridge=bridge,
        config=config,
    )
    intent_dict = attach_pre_trade_estimate_to_intent(intent_dict, pre_trade_estimate)
    mode = _mode_from_config(config)
    is_real_attempt = mode == "LIVE" or _bridge_reports_real_execution(bridge)
    base_provenance = _dispatch_provenance(
        order=order,
        proposed_intent=intent_dict,
        config=config,
        bridge=bridge,
        strategy_id=strategy_id,
        ai_action=ai_action,
        source=audit_source,
    )
    resolved_audit_store = _resolve_audit_store(audit_store)
    try:
        duplicate_probe = getattr(resolved_audit_store, "blocking_attempt_for_order", None)
        previous_attempt = None
        if callable(duplicate_probe):
            try:
                duplicate_window = int(
                    getattr(_resolve_config(config), "order_shape_duplicate_window_seconds", 600)
                )
            except Exception:
                duplicate_window = 600
            try:
                previous_attempt = duplicate_probe(
                    order,
                    proposed_intent=intent_dict,
                    near_duplicate_seconds=duplicate_window,
                )
            except TypeError:
                previous_attempt = duplicate_probe(order)
    except Exception as exc:
        if is_real_attempt:
            return _with_dispatch_provenance(DispatchResult(
                order_id=order.order_id,
                decision_ref=order.decision_ref,
                symbol=order.symbol,
                direction=direction,
                volume=float(order.volume),
                status=STATUS_DISPATCH_ERROR,
                reason=f"Order audit unavailable before idempotency check: {exc}",
                intent_summary=intent_summary,
                dispatched_to_bridge=False,
                stop_loss=float(order.stop_loss),
                take_profit=float(order.take_profit),
                audit_status="AUDIT_UNAVAILABLE",
                audit_error=str(exc),
                pre_trade_estimate=pre_trade_estimate,
            ),
                order=order,
                proposed_intent=intent_dict,
                config=config,
                bridge=bridge,
                strategy_id=strategy_id,
                ai_action=ai_action,
                source=audit_source,
            )
        previous_attempt = None
    duplicate_reason = _duplicate_suppression_reason(previous_attempt)
    if duplicate_reason:
        result = _with_dispatch_provenance(DispatchResult(
            order_id=order.order_id,
            decision_ref=order.decision_ref,
            symbol=order.symbol,
            direction=direction,
            volume=float(order.volume),
            status=STATUS_DUPLICATE_SUPPRESSED,
            reason=duplicate_reason,
            intent_summary=intent_summary,
            dispatched_to_bridge=False,
            stop_loss=float(order.stop_loss),
            take_profit=float(order.take_profit),
            pre_trade_estimate=pre_trade_estimate,
        ),
            order=order,
            proposed_intent=intent_dict,
            config=config,
            bridge=bridge,
            strategy_id=strategy_id,
            ai_action=ai_action,
            source=f"{audit_source}_idempotency",
        )
        return record_dispatch_result_to_audit(
            result,
            audit_store=resolved_audit_store,
            order=order,
            proposed_intent=intent_dict,
            config=config,
            bridge=bridge,
            is_real_attempt=is_real_attempt,
            source=f"{audit_source}_idempotency",
        )

    audit_attempt: Optional[Mapping[str, Any]] = None
    try:
        audit_attempt = resolved_audit_store.record_started(
            order,
            proposed_intent=intent_dict,
            mode=mode,
            is_real_attempt=is_real_attempt,
            bridge_name=bridge.__class__.__name__,
            source=audit_source,
            execution_provenance=base_provenance,
        )
    except Exception as exc:
        if is_real_attempt:
            return _with_dispatch_provenance(DispatchResult(
                order_id=order.order_id,
                decision_ref=order.decision_ref,
                symbol=order.symbol,
                direction=direction,
                volume=float(order.volume),
                status=STATUS_DISPATCH_ERROR,
                reason=f"Order audit unavailable before real dispatch: {exc}",
                intent_summary=intent_summary,
                dispatched_to_bridge=False,
                stop_loss=float(order.stop_loss),
                take_profit=float(order.take_profit),
                audit_status="AUDIT_UNAVAILABLE",
                audit_error=str(exc),
                pre_trade_estimate=pre_trade_estimate,
            ),
                order=order,
                proposed_intent=intent_dict,
                config=config,
                bridge=bridge,
                strategy_id=strategy_id,
                ai_action=ai_action,
                source=audit_source,
            )

    if live_telemetry is not None or is_real_attempt:
        live_telemetry = _hydrate_dispatch_live_telemetry(
            order=order,
            live_telemetry=live_telemetry,
            config=config,
        )

    market_availability = _market_availability_report(
        order=order,
        proposed_intent=intent_dict,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        config=config,
    )
    execution_quality = _execution_quality_report(
        order=order,
        proposed_intent=intent_dict,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        config=config,
    )
    macro_blackout = _macro_blackout_report(
        order=order,
        proposed_intent=intent_dict,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        config=config,
    )
    order_constraints = _order_constraints_report(
        order=order,
        proposed_intent=intent_dict,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        bridge=bridge,
        config=config,
    )

    def _blocked(
        status: str,
        reason: str,
        *,
        caps: tuple[str, ...] = (),
        live_gate_report: Optional[Mapping[str, Any]] = None,
    ) -> DispatchResult:
        result = _with_dispatch_provenance(DispatchResult(
            order_id=order.order_id,
            decision_ref=order.decision_ref,
            symbol=order.symbol,
            direction=direction,
            volume=float(order.volume),
            status=status,
            reason=reason,
            intent_summary=intent_summary,
            dispatched_to_bridge=False,
            stop_loss=float(order.stop_loss),
            take_profit=float(order.take_profit),
            risk_blocking_caps=caps,
            pre_trade_estimate=pre_trade_estimate,
            live_gate_report=dict(live_gate_report or {}),
            market_availability=market_availability,
            execution_quality=execution_quality,
            macro_blackout=macro_blackout,
            order_constraints=order_constraints,
        ),
            order=order,
            proposed_intent=intent_dict,
            config=config,
            bridge=bridge,
            strategy_id=strategy_id,
            ai_action=ai_action,
            source=audit_source,
            audit=audit_attempt,
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
            from cas_forex import operator_scale_in_authorization

            if operator_scale_in_authorization.is_required(order.decision_ref):
                operator_scale_in_authorization.require(
                    order,
                    proposed_intent=intent_dict,
                    bridge=bridge,
                    config=config,
                )
            else:
                # Legacy owner-reviewed WASTE dry runs remain readable and
                # dispatchable, but they are no longer the normal AI path.
                from cas_forex.compound_add_order_dry_run_review import (
                    require_current_compound_add_order_dry_run_review,
                )

                require_current_compound_add_order_dry_run_review(order)
        except Exception as exc:
            return _blocked(STATUS_BLOCKED_COMPOUND_ADD_AUTHORIZATION, str(exc))

    if bool(market_availability.get("block")):
        return _blocked(STATUS_BLOCKED_MARKET, str(market_availability.get("detail") or "Market is unavailable."))
    if bool(macro_blackout.get("block")):
        return _blocked(STATUS_BLOCKED_MACRO, str(macro_blackout.get("detail") or "Macro/news blackout is active."))
    if bool(execution_quality.get("block")):
        return _blocked(
            STATUS_BLOCKED_EXECUTION_QUALITY,
            str(execution_quality.get("detail") or "Execution quality is outside owner tolerance."),
        )
    if bool(order_constraints.get("block")):
        return _blocked(
            STATUS_BLOCKED_ORDER_CONSTRAINTS,
            str(order_constraints.get("detail") or "Order violates configured broker constraints."),
        )

    try:
        from cas_forex.edge_authorization import EdgeNotAuthorized
    except Exception:  # pragma: no cover - defensive import path only
        class EdgeNotAuthorized(PermissionError):
            pass

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
    except EdgeNotAuthorized as exc:
        return _blocked(STATUS_BLOCKED_EDGE_AUTHORIZATION, str(exc))
    except LiveDispatchBlocked as exc:
        return _blocked(
            STATUS_BLOCKED_LIVE_GATE,
            str(exc),
            live_gate_report=dict(getattr(exc, "report", {}) or {}),
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
        reason = f"Dispatch error: {exc}"
        if is_real_attempt and audit_attempt is not None:
            uncertain = _with_dispatch_provenance(DispatchResult(
                order_id=order.order_id,
                decision_ref=order.decision_ref,
                symbol=order.symbol,
                direction=direction,
                volume=float(order.volume),
                status=STATUS_DISPATCH_ERROR,
                reason=(
                    f"{reason}. Broker bridge touch is unknown; reconcile fresh broker truth "
                    "before retrying this real order."
                ),
                intent_summary=intent_summary,
                dispatched_to_bridge=True,
                stop_loss=float(order.stop_loss),
                take_profit=float(order.take_profit),
                pre_trade_estimate=pre_trade_estimate,
                market_availability=market_availability,
                execution_quality=execution_quality,
                macro_blackout=macro_blackout,
                order_constraints=order_constraints,
            ),
                order=order,
                proposed_intent=intent_dict,
                config=config,
                bridge=bridge,
                strategy_id=strategy_id,
                ai_action=ai_action,
                source=f"{audit_source}_bridge_error",
                audit=audit_attempt,
            )
            return record_unresolved_real_dispatch_error_to_audit(
                result=uncertain,
                audit_store=resolved_audit_store,
                started_attempt=audit_attempt,
                order=order,
                proposed_intent=intent_dict,
                config=config,
                bridge=bridge,
                source=f"{audit_source}_bridge_error",
                error=reason,
            )
        # Preserve the "never raises" contract so one bad bridge call cannot
        # abort the whole batch; surface it as an explicit per-intent error.
        return _blocked(STATUS_DISPATCH_ERROR, reason)

    ledger_event = _ledger_event_from_order(
        order, outcome, strategy_id=strategy_id, ai_action=ai_action
    )
    if _outcome_requires_live_safety(outcome) and outcome.status.value in {"EXECUTED", "PARTIAL"}:
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
    result = _with_dispatch_provenance(DispatchResult(
        order_id=order.order_id,
        decision_ref=order.decision_ref,
        symbol=order.symbol,
        direction=direction,
        volume=float(order.volume),
        status=f"BROKER_{outcome.status.value}",
        reason=outcome.error_message or f"Broker outcome: {outcome.status.value}",
        intent_summary=intent_summary,
        dispatched_to_bridge=True,
        stop_loss=float(order.stop_loss),
        take_profit=float(order.take_profit),
        outcome=outcome,
        ledger_event=ledger_event,
        pre_trade_estimate=pre_trade_estimate,
        market_availability=market_availability,
        execution_quality=execution_quality,
        macro_blackout=macro_blackout,
        order_constraints=order_constraints,
    ),
        order=order,
        proposed_intent=intent_dict,
        config=config,
        bridge=bridge,
        strategy_id=strategy_id,
        ai_action=ai_action,
        source=audit_source,
        audit=audit_attempt,
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
    precheck_intent = {
        "symbol": intent.symbol,
        "direction": str(intent.direction).upper(),
        "lots": float(intent.volume),
        "decision_ref": intent.decision_ref,
        "order_id": intent.order_id,
        "strategy_id": intent.strategy_id,
        "ai_action": intent.ai_action,
    }

    # 1. Build + validate the broker order (schema + SL/TP geometry).
    try:
        order = intent.to_order()
    except Exception as exc:  # pydantic ValidationError or bad direction
        pre_trade_estimate = build_pre_trade_money_estimate(
            symbol=intent.symbol,
            direction=str(intent.direction).upper(),
            lots=float(intent.volume),
            price=float(intent.price),
            stop_loss=float(intent.stop_loss),
            take_profit=float(intent.take_profit),
            proposed_intent=precheck_intent,
            account_snapshot=account_snapshot,
            bridge=bridge,
            config=config,
        )
        result = _with_dispatch_provenance(DispatchResult(
            order_id=intent.order_id,
            decision_ref=intent.decision_ref,
            symbol=intent.symbol,
            direction=str(intent.direction).upper(),
            volume=float(intent.volume),
            status=STATUS_REJECTED_PRECHECK,
            reason=f"Order rejected before dispatch: {exc}",
            intent_summary=intent_summary,
            dispatched_to_bridge=False,
            stop_loss=_positive_float_or_none(intent.stop_loss),
            take_profit=_positive_float_or_none(intent.take_profit),
            pre_trade_estimate=pre_trade_estimate,
        ),
            proposed_intent=precheck_intent,
            config=config,
            bridge=bridge,
            strategy_id=intent.strategy_id,
            ai_action=intent.ai_action,
            source=f"{audit_source}_precheck",
        )
        return record_dispatch_result_to_audit(
            result,
            audit_store=audit_store,
            proposed_intent=precheck_intent,
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
        in {
            STATUS_BLOCKED_LIVE_GATE,
            STATUS_BLOCKED_EDGE_AUTHORIZATION,
            STATUS_BLOCKED_COMPOUND_ADD_REVIEW,
            STATUS_BLOCKED_MARKET,
            STATUS_BLOCKED_EXECUTION_QUALITY,
            STATUS_BLOCKED_MACRO,
            STATUS_BLOCKED_ORDER_CONSTRAINTS,
            STATUS_BLOCKED_RISK,
        }
    )
    rejected = sum(
        1
        for r in results
        if r.status in {STATUS_REJECTED_PRECHECK, STATUS_OVERSEER_REJECTED, STATUS_DISPATCH_ERROR, STATUS_DUPLICATE_SUPPRESSED}
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
