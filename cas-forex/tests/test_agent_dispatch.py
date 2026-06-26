"""Tests for wiring real agent signals into the gated dispatch loop.

Covers: a real RouteIntent (built by the micro-scalp policy) flowing through the
overseer into the gated paper dispatch; overseer-rejected intents recorded but
not dispatched; live-gate block; and the end-to-end run_agent_dispatch_cycle.
"""

from __future__ import annotations

from types import SimpleNamespace

import json

from cas_forex.agent_dispatch import (
    AgentDispatchCycle,
    dispatch_route_intents,
    run_agent_dispatch_cycle,
    write_agent_dispatch_cycle_report,
)
from cas_forex.agent_state import RouteIntent
from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.order_dispatch import STATUS_BLOCKED_LIVE_GATE, STATUS_OVERSEER_REJECTED
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderType


def _cfg(*, live_mode: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        live_mode=live_mode,
    )


def _order(symbol: str = "EUR/USD", volume: float = 0.1) -> BrokerOrderRequest:
    return BrokerOrderRequest(
        order_id=f"agent-{symbol.replace('/', '')}-1",
        decision_ref="micro_scalp_agent:test",
        symbol=symbol,
        order_type=OrderType.MARKET,
        direction=Direction.LONG,
        volume=volume,
        price=0.0,
        stop_loss=1.0900,
        take_profit=1.1100,
        comment="CAS_MICRO_SCALP",
    )


def _route_intent(
    *,
    symbol: str = "EUR/USD",
    volume: float = 0.1,
    confidence: float = 0.7,
    evidence_score: float = 2.0,
    evidence_refs=("ref-1",),
    intent_id: str = "intent-1",
) -> RouteIntent:
    order = _order(symbol=symbol, volume=volume)
    return RouteIntent(
        intent_id=intent_id,
        agent_id="micro_scalp_agent",
        action="OPEN_MICRO_SCALP",
        symbol=symbol,
        timeframe="M5",
        strategy_setting="range_scalper_12_80",
        direction=Direction.LONG.value,
        confidence=confidence,
        evidence_score=evidence_score,
        lot_size=volume,
        entry_price=1.10,
        stop_loss=1.0900,
        take_profit=1.1100,
        reason="test route intent",
        evidence_refs=list(evidence_refs),
        order_request=order.model_dump(mode="json"),
    )


def test_real_route_intent_dispatches_through_overseer_and_gate():
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent()],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
    )
    assert isinstance(cycle, AgentDispatchCycle)
    assert cycle.approved_count == 1
    report = cycle.dispatch_report
    assert report.intent_count == 1
    assert report.executed_count == 1
    assert report.mode == "PAPER"
    # The dispatched order produced a paper ledger event.
    events = cycle.ledger_events()
    assert len(events) == 1
    assert events[0].event_type == "paper_order_intent"
    assert events[0].external_money_movement is False


def test_overseer_rejected_intent_is_recorded_not_dispatched():
    bridge = SimulatedBrokerBridge()
    # evidence_score below the overseer's 1.0 route threshold -> rejected.
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent(evidence_score=0.0)],
        bridge=bridge,
        config=_cfg(),
        enforce_receipt_gates=False,
    )
    assert cycle.approved_count == 0
    results = cycle.dispatch_report.results
    assert len(results) == 1
    assert results[0].status == STATUS_OVERSEER_REJECTED
    assert results[0].dispatched_to_bridge is False
    # Nothing reached the broker.
    assert bridge.get_open_positions() == []


def test_live_mode_blocks_approved_intent_at_gate():
    bridge = SimulatedBrokerBridge()
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent()],
        bridge=bridge,
        config=_cfg(live_mode=True),
        enforce_receipt_gates=False,
    )
    assert cycle.approved_count == 1  # overseer approves
    result = cycle.dispatch_report.results[0]
    assert result.status == STATUS_BLOCKED_LIVE_GATE  # but the live gate blocks dispatch
    assert result.dispatched_to_bridge is False
    assert bridge.get_open_positions() == []


def test_dispatch_route_intents_mixed_batch():
    bridge = SimulatedBrokerBridge()
    from cas_forex.agent_overseer import review_route_intents

    intents = [
        _route_intent(intent_id="ok", symbol="EUR/USD"),
        _route_intent(intent_id="bad", symbol="USD/JPY", evidence_score=0.0),
    ]
    decisions = review_route_intents(intents, enforce_receipt_gates=False)
    report = dispatch_route_intents(intents, decisions, bridge=bridge, config=_cfg())

    assert report.intent_count == 2
    assert report.executed_count == 1
    statuses = {r.status for r in report.results}
    assert STATUS_OVERSEER_REJECTED in statuses


def test_duplicate_intent_id_not_silently_dropped():
    # SF-1 regression: positional pairing represents every intent exactly once,
    # even when two intents share an intent_id (the old id-keyed dict dropped one).
    bridge = SimulatedBrokerBridge()
    from cas_forex.agent_overseer import review_route_intents

    intents = [
        _route_intent(intent_id="dup", symbol="EUR/USD"),
        _route_intent(intent_id="dup", symbol="USD/JPY"),
    ]
    decisions = review_route_intents(intents, enforce_receipt_gates=False)
    report = dispatch_route_intents(intents, decisions, bridge=bridge, config=_cfg())

    # Both intents are represented; none dropped from the report.
    assert report.intent_count == 2
    symbols = sorted(r.symbol for r in report.results)
    assert symbols == ["EUR/USD", "USD/JPY"]


def test_cycle_serializes_to_dict():
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent()],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
    )
    payload = cycle.to_dict()
    assert payload["report_kind"] == "cas_forex_agent_dispatch_cycle"
    assert payload["route_intent_count"] == 1
    assert payload["dispatch_report"]["report_kind"] == "cas_forex_order_dispatch"
    assert "does not pick or size trades" in payload["claim_boundary"]


def test_write_cycle_report_persists_json(tmp_path):
    cycle = run_agent_dispatch_cycle(
        intents=[_route_intent()],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        enforce_receipt_gates=False,
    )
    paths = write_agent_dispatch_cycle_report(cycle, output_dir=tmp_path)
    assert paths["json"].exists()
    loaded = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert loaded["report_kind"] == "cas_forex_agent_dispatch_cycle"
    assert loaded["dispatch_report"]["executed_count"] == 1
