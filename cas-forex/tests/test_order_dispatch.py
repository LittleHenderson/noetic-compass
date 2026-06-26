"""Tests for the order dispatch loop — signal -> gate -> bridge -> ledger.

Exercises the paper path against SimulatedBrokerBridge end-to-end, plus the two
block paths (risk cap breach, live-trading gate) and the pre-check rejection.
"""

from __future__ import annotations

from types import SimpleNamespace

from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.order_dispatch import (
    STATUS_BLOCKED_LIVE_GATE,
    STATUS_BLOCKED_RISK,
    STATUS_REJECTED_PRECHECK,
    TradeIntent,
    dispatch_intent,
    dispatch_intents,
    dispatched_ledger_events,
)


def _cfg(*, live_mode: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        live_mode=live_mode,
    )


def _intent(order_id: str = "ord-1", volume: float = 0.1) -> TradeIntent:
    # EUR/USD LONG market: SL < TP required by the order schema.
    return TradeIntent(
        order_id=order_id,
        decision_ref="dec-1",
        symbol="EUR/USD",
        direction="LONG",
        volume=volume,
        stop_loss=1.0900,
        take_profit=1.1100,
        strategy_id="strat-A",
    )


def test_paper_dispatch_executes_through_simulated_bridge():
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(_intent(), bridge, config=_cfg())

    assert result.dispatched_to_bridge is True
    assert result.executed is True
    assert result.status == "BROKER_EXECUTED"
    assert result.outcome is not None
    assert result.outcome.broker_ticket is not None
    # A balance-neutral dispatch ledger event is produced and stays paper.
    assert result.ledger_event is not None
    assert result.ledger_event.event_type == "paper_order_intent"
    assert result.ledger_event.balance_delta_usd == 0.0
    assert result.ledger_event.external_money_movement is False
    assert result.ledger_event.broker_ticket == str(result.outcome.broker_ticket)


def test_risk_cap_breach_blocks_before_bridge():
    bridge = SimulatedBrokerBridge()
    # 1.0 lot on an empty book exceeds the 0.5-lot total-exposure cap.
    result = dispatch_intent(_intent(volume=1.0), bridge, config=_cfg())

    assert result.status == STATUS_BLOCKED_RISK
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert "max_total_exposure_lots" in result.risk_blocking_caps
    # The bridge must never have been reached.
    assert bridge.get_open_positions() == []


def test_live_mode_without_authorization_blocks_at_dispatch():
    bridge = SimulatedBrokerBridge()
    # live_mode=True with no enable flag / creds -> live-trading gate NOT LICENSED.
    result = dispatch_intent(_intent(), bridge, config=_cfg(live_mode=True))

    assert result.status == STATUS_BLOCKED_LIVE_GATE
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert bridge.get_open_positions() == []


def test_invalid_geometry_rejected_in_precheck():
    bridge = SimulatedBrokerBridge()
    bad = TradeIntent(
        order_id="ord-bad",
        decision_ref="dec-1",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.1,
        stop_loss=1.1100,  # SL above TP for a LONG -> invalid
        take_profit=1.0900,
    )
    result = dispatch_intent(bad, bridge, config=_cfg())

    assert result.status == STATUS_REJECTED_PRECHECK
    assert result.dispatched_to_bridge is False
    assert result.outcome is None


def test_batch_report_counts_and_mode():
    bridge = SimulatedBrokerBridge()
    intents = [
        _intent(order_id="ok-1", volume=0.1),
        _intent(order_id="too-big", volume=1.0),  # risk-blocked
    ]
    report = dispatch_intents(intents, bridge=bridge, config=_cfg())

    assert report.mode == "PAPER"
    assert report.intent_count == 2
    assert report.executed_count == 1
    assert report.blocked_count == 1
    assert report.live_execution_runtime_locked is True
    # Only the executed intent yields a ledger event.
    assert len(dispatched_ledger_events(report)) == 1
    # Report serializes cleanly.
    payload = report.to_dict()
    assert payload["report_kind"] == "cas_forex_order_dispatch"
    assert len(payload["results"]) == 2
