"""End-to-end paper demo: signal -> gate -> bridge -> ledger, then money split.

Runs the order dispatch loop against the paper broker (SimulatedBrokerBridge),
feeds the dispatch events into the paper account ledger, then runs the
money-movement engine's reinvest split. No real money, no live broker — this
proves the two engines end-to-end before any credentials are ever set.

    python scripts/run_paper_dispatch.py
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from cas_forex.account_ledger import build_paper_account_ledger
from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.money_movement import MovementEngine
from cas_forex.order_dispatch import (
    TradeIntent,
    dispatch_intents,
    dispatched_ledger_events,
)


def _demo_config() -> SimpleNamespace:
    # Paper mode, modest caps. Money gates left NOT LICENSED on purpose so the
    # demo shows the fail-closed money path too.
    return SimpleNamespace(
        live_mode=False,
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        owner_enable_auto_deposit=False,
        owner_enable_bank_card_movement=False,
        owner_enable_payout_automation=False,
        payment_provider="",
        payment_api_key=None,
        payout_destination_id=None,
        payout_destination_allowlisted=False,
    )


def main() -> None:
    config = _demo_config()
    bridge = SimulatedBrokerBridge()

    intents = [
        TradeIntent(
            order_id="demo-eurusd-1",
            decision_ref="demo-decision",
            symbol="EUR/USD",
            direction="LONG",
            volume=0.1,
            stop_loss=1.0900,
            take_profit=1.1100,
            strategy_id="demo-strategy",
        ),
        TradeIntent(
            order_id="demo-usdjpy-1",
            decision_ref="demo-decision",
            symbol="USD/JPY",
            direction="SHORT",
            volume=0.1,
            stop_loss=158.00,
            take_profit=154.00,
            strategy_id="demo-strategy",
        ),
        TradeIntent(  # deliberately oversized -> risk-blocked
            order_id="demo-toobig",
            decision_ref="demo-decision",
            symbol="EUR/USD",
            direction="LONG",
            volume=2.0,
            stop_loss=1.0900,
            take_profit=1.1100,
            strategy_id="demo-strategy",
        ),
    ]

    report = dispatch_intents(intents, bridge=bridge, config=config)
    print("=== ORDER DISPATCH (paper) ===")
    print(
        f"mode={report.mode} intents={report.intent_count} "
        f"executed={report.executed_count} blocked={report.blocked_count} "
        f"rejected={report.rejected_count} live_locked={report.live_execution_runtime_locked}"
    )
    for r in report.results:
        print(f"  - {r.order_id:16s} {r.status:18s} :: {r.reason}")

    # Feed the dispatch events into the paper account ledger.
    events = dispatched_ledger_events(report)
    ledger = build_paper_account_ledger(
        initial_investment_usd=5000.0,
        plan_id="demo-plan",
        lead_id="demo-lead",
        strategy_setting="demo-strategy",
        as_of_date="2026-06-26",
        cashflow_events=events,
    )
    print("\n=== ACCOUNT LEDGER (paper) ===")
    print(
        f"balance=${ledger.summary.balance_usd} equity=${ledger.summary.equity_usd} "
        f"events={ledger.summary.event_count} live_money_authorized={ledger.live_money_authorized}"
    )

    # Money-movement engine: reinvest split (gates NOT LICENSED -> external legs blocked).
    engine = MovementEngine(config=config)
    split = engine.reinvest_split(
        1000.0, reinvest_pct=50.0, savings_pct=40.0, tax_reserve_pct=10.0,
    )
    print("\n=== REINVEST SPLIT (money-movement engine) ===")
    print(
        f"profit=${split.realized_profit_usd} reinvest=${split.reinvest_usd} "
        f"savings=${split.savings_usd} tax=${split.tax_reserve_usd} "
        f"external_settled={split.external_movement_settled}"
    )
    for leg in split.legs:
        print(f"  - {leg.kind:10s} {leg.status:10s} :: {leg.reason}")

    # Agent-signal dispatch: a REAL RouteIntent (the shape the micro-scalp agent
    # emits) flows through the overseer into the same gated paper dispatch.
    from cas_forex.agent_dispatch import run_agent_dispatch_cycle
    from cas_forex.agent_state import RouteIntent
    from cas_forex.schemas.forecast import Direction
    from cas_forex.schemas.order import BrokerOrderRequest, OrderType

    demo_order = BrokerOrderRequest(
        order_id="agent-EURUSD-demo",
        decision_ref="micro_scalp_agent:demo",
        symbol="EUR/USD",
        order_type=OrderType.MARKET,
        direction=Direction.LONG,
        volume=0.1,
        price=0.0,
        stop_loss=1.0900,
        take_profit=1.1100,
        comment="CAS_MICRO_SCALP",
    )
    route_intent = RouteIntent(
        intent_id="intent-micro-eurusd-m5",
        agent_id="micro_scalp_agent",
        action="OPEN_MICRO_SCALP",
        symbol="EUR/USD",
        timeframe="M5",
        strategy_setting="range_scalper_12_80",
        direction=Direction.LONG.value,
        confidence=0.7,
        evidence_score=2.0,
        lot_size=0.1,
        entry_price=1.10,
        stop_loss=1.0900,
        take_profit=1.1100,
        reason="demo replay lead",
        evidence_refs=["demo-evidence-ref"],
        order_request=demo_order.model_dump(mode="json"),
    )
    agent_cycle = run_agent_dispatch_cycle(
        intents=[route_intent],
        bridge=SimulatedBrokerBridge(),
        config=config,
        enforce_receipt_gates=False,
    )
    print("\n=== AGENT-SIGNAL DISPATCH (real RouteIntent -> overseer -> gate) ===")
    print(
        f"route_intents={len(agent_cycle.route_intents)} approved={agent_cycle.approved_count} "
        f"executed={agent_cycle.dispatch_report.executed_count}"
    )
    for r in agent_cycle.dispatch_report.results:
        print(f"  - {r.order_id:20s} {r.status:18s} :: {r.reason}")

    print("\n(JSON dispatch report below)")
    print(json.dumps(report.to_dict(), indent=2)[:1200] + " ...")


if __name__ == "__main__":
    main()
