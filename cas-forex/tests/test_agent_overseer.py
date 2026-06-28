"""Receipt-aware overseer routing coverage."""

from __future__ import annotations

from cas_forex.agent_message_bus import AgentEventStore, make_agent_event
from cas_forex.agent_overseer import (
    RECEIPT_GATE_AWAITING_RECEIPT,
    RECEIPT_GATE_LOCKED,
    RECEIPT_GATE_NEXT_ALLOWED,
    receipt_gate_state_by_symbol,
    review_route_intents,
)
from cas_forex.agent_state import RouteIntent


def _intent(symbol: str = "AUD/CAD") -> RouteIntent:
    return RouteIntent(
        intent_id=f"intent-{symbol.replace('/', '')}",
        agent_id="micro_scalp_agent",
        action="OPEN_MICRO_SCALP",
        symbol=symbol,
        timeframe="M5",
        strategy_setting="range_scalper_12_80",
        direction="LONG",
        confidence=0.91,
        evidence_score=5.0,
        lot_size=0.9,
        entry_price=1.0,
        stop_loss=0.99,
        take_profit=1.01,
        reason="test route",
        evidence_refs=["evidence_runs/test.json"],
        order_request={
            "order_id": "test-order",
            "decision_ref": "test-decision",
            "symbol": symbol,
            "direction": "LONG",
            "volume": 0.9,
            "price": 1.0,
            "stop_loss": 0.99,
            "take_profit": 1.01,
        },
    )


def _append_pending_command(event_log_path, *, command_id: str = "cmd-1", symbol: str = "AUD/CAD") -> None:
    store = AgentEventStore(event_log_path)
    store.append_event(
        make_agent_event(
            cycle_id="cycle-1",
            producer_agent_id="terminal_bridge_agent",
            consumer_agent_ids=["mt4_terminal"],
            event_type="TERMINAL_COMMAND_WRITTEN",
            subject=command_id,
            symbol=symbol,
            timeframe="M5",
            payload={"command_id": command_id, "symbol": symbol, "raw_request_hash": "hash-1"},
            status="COMMAND_WRITTEN",
            correlation_id=command_id,
        )
    )
    store.append_event(
        make_agent_event(
            cycle_id="cycle-1",
            producer_agent_id="terminal_bridge_agent",
            consumer_agent_ids=["overseer_agent"],
            event_type="TERMINAL_RECEIPT_PENDING",
            subject=command_id,
            symbol=symbol,
            timeframe="M5",
            payload={"command_id": command_id, "symbol": symbol, "raw_request_hash": "hash-1"},
            status="RECEIPT_PENDING",
            correlation_id=command_id,
        )
    )


def test_receipt_gate_blocks_same_symbol_when_command_is_pending(tmp_path):
    event_log_path = tmp_path / "agent-events.jsonl"
    _append_pending_command(event_log_path)

    gates = receipt_gate_state_by_symbol(event_log_path)
    decisions = review_route_intents([_intent()], event_log_path=event_log_path)

    assert gates["AUD/CAD"]["status"] == RECEIPT_GATE_AWAITING_RECEIPT
    assert decisions[0].approved is False
    assert decisions[0].decision == "REJECT_ROUTE_INTENT"
    assert "awaiting terminal receipt/reconciliation" in " ".join(decisions[0].reasons)


def test_receipt_gate_allows_same_symbol_after_next_cycle_allowed(tmp_path):
    event_log_path = tmp_path / "agent-events.jsonl"
    _append_pending_command(event_log_path)
    AgentEventStore(event_log_path).append_event(
        make_agent_event(
            cycle_id="cycle-1",
            producer_agent_id="overseer_agent",
            consumer_agent_ids=["micro_scalp_agent"],
            event_type="NEXT_CYCLE_ALLOWED",
            subject="AUD/CAD",
            symbol="AUD/CAD",
            timeframe="M5",
            payload={"command_id": "cmd-1", "symbol": "AUD/CAD", "receipt_id": "receipt-1"},
            status="NEXT_CYCLE_ALLOWED",
            correlation_id="cmd-1",
        )
    )

    gates = receipt_gate_state_by_symbol(event_log_path)
    decisions = review_route_intents([_intent()], event_log_path=event_log_path)

    assert gates["AUD/CAD"]["status"] == RECEIPT_GATE_NEXT_ALLOWED
    assert decisions[0].approved is True
    assert "receipt lifecycle allows next same-symbol cycle" in decisions[0].reasons


def test_receipt_gate_locks_same_symbol_after_terminal_mismatch(tmp_path):
    event_log_path = tmp_path / "agent-events.jsonl"
    _append_pending_command(event_log_path)
    AgentEventStore(event_log_path).append_event(
        make_agent_event(
            cycle_id="cycle-1",
            producer_agent_id="terminal_bridge_agent",
            consumer_agent_ids=["overseer_agent"],
            event_type="TERMINAL_RECEIPT_MISMATCH",
            subject="cmd-1",
            symbol="AUD/CAD",
            timeframe="M5",
            payload={"command_id": "cmd-1", "symbol": "AUD/CAD", "receipt_id": "receipt-bad"},
            status="TERMINAL_LOCKED_FOR_SYMBOL",
            correlation_id="cmd-1",
        )
    )

    gates = receipt_gate_state_by_symbol(event_log_path)
    decisions = review_route_intents([_intent()], event_log_path=event_log_path)

    assert gates["AUD/CAD"]["status"] == RECEIPT_GATE_LOCKED
    assert decisions[0].approved is False
    assert "locked by terminal receipt mismatch" in " ".join(decisions[0].reasons)
