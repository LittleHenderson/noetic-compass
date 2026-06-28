"""Overseer policy for CAS Forex agent route intents."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from cas_forex.agent_message_bus import AgentEventStore, AgentMessageBusError
from cas_forex.agent_state import OverseerDecision, RouteIntent
from cas_forex.instruments import SUPPORTED_SYMBOLS
from cas_forex.time_utils import utc_now


RECEIPT_GATE_NO_PRIOR_COMMAND = "NO_PRIOR_COMMAND"
RECEIPT_GATE_AWAITING_RECEIPT = "AWAITING_TERMINAL_RECEIPT"
RECEIPT_GATE_LOCKED = "TERMINAL_LOCKED_FOR_SYMBOL"
RECEIPT_GATE_NEXT_ALLOWED = "NEXT_CYCLE_ALLOWED"
RECEIPT_GATE_UNAVAILABLE = "RECEIPT_GATE_UNAVAILABLE"


def review_route_intents(
    intents: Iterable[RouteIntent],
    *,
    event_log_path: Optional[Path | str] = None,
    enforce_receipt_gates: bool = True,
) -> List[OverseerDecision]:
    """Approve or reject route intents for paper/demo terminal command writing."""

    receipt_gates = receipt_gate_state_by_symbol(event_log_path) if enforce_receipt_gates else {}
    decisions: List[OverseerDecision] = []
    approved_symbols: set[str] = set()
    for intent in intents:
        reasons: List[str] = []
        approved = True
        if intent.symbol not in SUPPORTED_SYMBOLS:
            approved = False
            reasons.append("unsupported symbol")
        if not intent.order_request:
            approved = False
            reasons.append("missing BrokerOrderRequest payload")
        if not intent.evidence_refs:
            approved = False
            reasons.append("missing evidence refs")
        if intent.evidence_score < 1.0:
            approved = False
            reasons.append("evidence score below route threshold")
        if intent.confidence < 0.5:
            approved = False
            reasons.append("confidence below route threshold")
        if intent.symbol in approved_symbols:
            approved = False
            reasons.append("same-symbol route already approved this cycle; queue after first terminal receipt")
        gate_state = receipt_gates.get(intent.symbol) or receipt_gates.get("*")
        if approved and gate_state:
            gate_status = gate_state.get("status")
            if gate_status == RECEIPT_GATE_AWAITING_RECEIPT:
                approved = False
                reasons.append(
                    "same-symbol route is awaiting terminal receipt/reconciliation for command(s): "
                    + _format_command_ids(gate_state.get("blocking_command_ids") or [])
                )
            elif gate_status == RECEIPT_GATE_LOCKED:
                approved = False
                reasons.append(
                    "same-symbol route locked by terminal receipt mismatch for command(s): "
                    + _format_command_ids(gate_state.get("blocking_command_ids") or [])
                )
            elif gate_status == RECEIPT_GATE_NEXT_ALLOWED:
                reasons.append("receipt lifecycle allows next same-symbol cycle")
            elif gate_status == RECEIPT_GATE_UNAVAILABLE:
                approved = False
                reasons.append(str(gate_state.get("detail") or "receipt gate state unavailable"))

        if approved:
            approved_symbols.add(intent.symbol)
            decision = "APPROVE_ROUTE_INTENT"
            reasons.append("paper/demo route intent approved for terminal mailbox command")
        else:
            decision = "REJECT_ROUTE_INTENT"
        decisions.append(
            OverseerDecision(
                decision_id=f"overseer-{intent.intent_id}",
                intent_id=intent.intent_id,
                agent_id=intent.agent_id,
                decision=decision,
                approved=approved,
                reasons=reasons,
                command_ready=bool(approved and intent.order_request),
                timestamp=utc_now().isoformat(),
            )
        )
    return decisions


def receipt_gate_state_by_symbol(event_log_path: Optional[Path | str]) -> Dict[str, Dict[str, Any]]:
    """Project journal events into per-symbol receipt routing state."""

    if event_log_path is None:
        return {}
    store = AgentEventStore(event_log_path)
    try:
        events = store.read_events(limit=100000)
    except AgentMessageBusError as exc:
        if Path(event_log_path).exists():
            return {
                "*": {
                    "status": RECEIPT_GATE_UNAVAILABLE,
                    "detail": str(exc),
                    "blocking_command_ids": [],
                    "allowed_command_ids": [],
                }
            }
        return {}

    command_states: Dict[str, Dict[str, Any]] = {}
    for event in events:
        event_type = str(event.get("event_type"))
        payload = event.get("payload") or {}
        if not isinstance(payload, Mapping):
            continue
        command_id = payload.get("command_id")
        if not command_id:
            continue
        command_id = str(command_id)
        state = command_states.setdefault(command_id, {"command_id": command_id, "status": "UNKNOWN"})
        symbol = event.get("symbol") or payload.get("symbol") or state.get("symbol")
        if symbol:
            state["symbol"] = str(symbol)
        state["latest_event_id"] = event.get("event_id")
        state["latest_event_type"] = event_type
        state["latest_status"] = event.get("status")
        if event_type == "TERMINAL_COMMAND_WRITTEN":
            state["status"] = "COMMAND_WRITTEN"
        elif event_type == "TERMINAL_RECEIPT_PENDING":
            state["status"] = "RECEIPT_PENDING"
        elif event_type == "TERMINAL_RECEIPT_RECEIVED":
            state["status"] = str(event.get("status") or "RECEIPT_RECEIVED")
        elif event_type == "TERMINAL_RECEIPT_RECONCILED":
            state["status"] = "RECONCILED"
        elif event_type == "NEXT_CYCLE_ALLOWED":
            state["status"] = RECEIPT_GATE_NEXT_ALLOWED
        elif event_type == "TERMINAL_RECEIPT_MISMATCH":
            state["status"] = RECEIPT_GATE_LOCKED

    by_symbol: Dict[str, Dict[str, Any]] = {}
    for command_id, state in command_states.items():
        symbol = state.get("symbol")
        if not symbol:
            continue
        bucket = by_symbol.setdefault(
            str(symbol),
            {
                "symbol": str(symbol),
                "status": RECEIPT_GATE_NO_PRIOR_COMMAND,
                "blocking_command_ids": [],
                "allowed_command_ids": [],
                "command_states": [],
            },
        )
        bucket["command_states"].append(dict(state))
        status = str(state.get("status"))
        if status == RECEIPT_GATE_LOCKED:
            bucket["status"] = RECEIPT_GATE_LOCKED
            bucket["blocking_command_ids"].append(command_id)
        elif status == RECEIPT_GATE_NEXT_ALLOWED:
            bucket["allowed_command_ids"].append(command_id)
        elif status in {"COMMAND_WRITTEN", "RECEIPT_PENDING", "RECEIPT_VERIFIED", "RECONCILED", "RECEIPT_RECEIVED"}:
            if bucket["status"] != RECEIPT_GATE_LOCKED:
                bucket["status"] = RECEIPT_GATE_AWAITING_RECEIPT
            bucket["blocking_command_ids"].append(command_id)

    for bucket in by_symbol.values():
        if bucket["status"] == RECEIPT_GATE_NO_PRIOR_COMMAND and bucket["allowed_command_ids"]:
            bucket["status"] = RECEIPT_GATE_NEXT_ALLOWED
        bucket["blocking_command_ids"] = sorted(set(bucket["blocking_command_ids"]))
        bucket["allowed_command_ids"] = sorted(set(bucket["allowed_command_ids"]))
    return by_symbol


def _format_command_ids(command_ids: List[str], *, limit: int = 5) -> str:
    if not command_ids:
        return "none"
    sample = command_ids[:limit]
    extra = len(command_ids) - len(sample)
    suffix = f" (+{extra} more)" if extra > 0 else ""
    return ", ".join(sample) + suffix
