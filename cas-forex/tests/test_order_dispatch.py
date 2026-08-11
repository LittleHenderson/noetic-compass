"""Tests for the order dispatch loop — signal -> gate -> bridge -> ledger.

Exercises the paper path against SimulatedBrokerBridge end-to-end, plus the two
block paths (risk cap breach, live-trading gate) and the pre-check rejection.
"""

from __future__ import annotations

from datetime import timedelta
from itertools import count
from types import SimpleNamespace
from types import SimpleNamespace as NS

import cas_forex.order_dispatch as order_dispatch_module
import cas_forex.execution_guard as execution_guard
from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.order_dispatch import (
    STATUS_BLOCKED_COMPOUND_ADD_REVIEW,
    STATUS_BLOCKED_EDGE_AUTHORIZATION,
    STATUS_BLOCKED_EXECUTION_QUALITY,
    STATUS_BLOCKED_LIVE_GATE,
    STATUS_BLOCKED_MACRO,
    STATUS_BLOCKED_MARKET,
    STATUS_BLOCKED_ORDER_CONSTRAINTS,
    STATUS_BLOCKED_RISK,
    STATUS_DISPATCH_ERROR,
    STATUS_DUPLICATE_SUPPRESSED,
    STATUS_REJECTED_PRECHECK,
    TradeIntent,
    dispatch_intent,
    dispatch_intents,
    dispatch_trade_management_action,
    dispatched_ledger_events,
)
from cas_forex.schemas.order import BrokerMode, OrderOutcome, OrderStatus

import pytest

from cas_forex import (
    auto_halt,
    broker_reality,
    broker_truth_monitor,
    compound_add_order_dry_run_review,
    edge_authorization as _EA,
    live_order_dry_run_review,
    live_pilot,
    live_recovery,
)
from cas_forex.edge_gate import CandidateSetup, EdgeTestDecision, _now_iso, mint_token
from cas_forex.live_order_dry_run import (
    CompoundAddDryRunRequest,
    LiveOrderDryRunAuditLog,
    build_compound_add_order_dry_run,
)
from cas_forex.order_attempt_audit import OrderAttemptAuditStore


_ORDER_SEQ = count(1)


@pytest.fixture(autouse=True)
def _reset_edge_registry(tmp_path, monkeypatch):
    # The fail-closed edge gate (edge_authorization) is process-global; isolate it
    # per test so a live-dispatch registration never leaks into the paper-path tests.
    import cas_forex.order_attempt_audit as order_attempt_audit

    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_STATE_PATH", tmp_path / "default-order-attempts.json")
    monkeypatch.setattr(order_attempt_audit, "DEFAULT_AUDIT_PATH", tmp_path / "default-order-attempts-audit.jsonl")
    _EA.reset()
    yield
    _EA.reset()


def _authorize_intent(intent, *, config=None, is_real: bool | None = None) -> None:
    """Register a fresh edge PASS for an intent so it can clear the chokepoint's
    fail-closed edge gate (real-money / loop orders require a tested edge)."""
    evat = _now_iso()
    setup = CandidateSetup(
        symbol=intent.symbol, timeframe="H1", direction=intent.direction,
        entry=float(getattr(intent, "price", 0.0)) or 1.10,
        stop_loss=intent.stop_loss, take_profit=intent.take_profit,
        signal_strength=1.0, regime="trend", decision_ref=intent.decision_ref,
    )
    dec = EdgeTestDecision(
        status="PASS", measured_win_prob=0.70, null_p95=0.10, threshold=0.65,
        edge_token=mint_token(setup, evat), evaluated_at=evat, reason="authorized for test",
    )
    _EA.authorize(
        intent.decision_ref,
        dec,
        setup,
        config=config,
        is_real=(
            bool(getattr(config, "live_mode", False))
            if is_real is None and config is not None
            else is_real
        ),
        volume=float(getattr(intent, "volume", 0.0) or 0.0),
        order_type=str(getattr(intent, "order_type", "MARKET") or "MARKET"),
        price=float(getattr(intent, "price", 0.0) or 0.0),
        strategy_id=getattr(intent, "strategy_id", None),
    )


def _cfg(*, live_mode: bool = False, **overrides) -> SimpleNamespace:
    base = dict(
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        live_mode=live_mode,
        macro_blackout_enabled=False,
        blackout_before_nfp_minutes=15,
        blackout_after_nfp_minutes=15,
        blackout_before_fomc_minutes=15,
        blackout_after_fomc_minutes=15,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _authorized_live_cfg() -> SimpleNamespace:
    # Everything evaluate_live_trading requires, fully owner-authorized.
    return SimpleNamespace(
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        live_mode=True,
        owner_enable_live_trading=True,
        live_trading_licensed=True,
        mt5_login=12345,
        mt5_password="pw",
        mt5_server="HugosWay-Live",
        prefer_mt5=True,
        mt5_path=None,
        personal_account_ack=True,
        no_pooled_capital_ack=True,
        account_type="personal",
        selected_broker_id="hugosway",
    )


def _live_risk_telemetry() -> dict:
    return {
        "open_positions": [],
        "data_freshness": {"stale": False},
    }


def _live_account_snapshot() -> dict:
    return {
        "balance": 1000.0,
        "equity": 1000.0,
        "margin": 0.0,
        "free_margin": 1000.0,
    }


class _FakeRealBridge:
    """A bridge that reports it would place a REAL order (like a connected MT5)."""

    def __init__(self, outcome: OrderOutcome) -> None:
        self.outcome = outcome
        self.calls: list = []

    def will_execute_real_order(self) -> bool:
        return True

    def execute_order(self, order):
        self.calls.append(order)
        return self.outcome


class _FakeDemoBridge(_FakeRealBridge):
    def will_execute_real_order(self) -> bool:
        return False


def _executed_outcome(order_id: str) -> OrderOutcome:
    return OrderOutcome(
        order_ref=order_id,
        broker_ticket=999001,
        status=OrderStatus.EXECUTED,
        filled_price=1.1000,
        broker_mode=BrokerMode.LIVE_MT5,
        is_real_broker=True,
        is_demo_account=False,
    )


def _intent(order_id: str | None = None, volume: float = 0.1) -> TradeIntent:
    # EUR/USD LONG market: SL < TP required by the order schema.
    return TradeIntent(
        order_id=order_id or f"ord-{next(_ORDER_SEQ)}",
        decision_ref="dec-1",
        symbol="EUR/USD",
        direction="LONG",
        volume=volume,
        stop_loss=1.0900,
        take_profit=1.1100,
        strategy_id="strat-A",
    )


def _compound_add_request() -> CompoundAddDryRunRequest:
    return CompoundAddDryRunRequest(
        parent_order_id="parent-1",
        parent_decision_ref="parent-ref-1",
        broker_ticket="123456",
        symbol="EUR/USD",
        direction="LONG",
        add_order_id="compound-add-1",
        add_decision_ref="compound-add-ref-1",
        add_volume=0.01,
        price=1.1050,
        stop_loss=1.0950,
        take_profit=1.1150,
        position_entry=1.1000,
        position_stop_loss=1.0900,
        current_price=1.1050,
        current_units=1,
        max_units=4,
        broker_grade_market_truth=True,
        cas_feature_map={
            "selected_rpm_action": "ROUTE",
            "selected_is_lacuna": False,
            "selected_cjt_region": "active",
            "cell_reliability": 0.85,
            "cascade_confidence": 0.80,
        },
        expected_loss_usd=10.0,
    )


def _compound_add_intent(req: CompoundAddDryRunRequest, *, order_id: str | None = None) -> TradeIntent:
    return TradeIntent(
        order_id=order_id or req.add_order_id,
        decision_ref=req.add_decision_ref,
        symbol=req.symbol,
        direction=req.direction,
        volume=req.add_volume,
        price=req.price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        comment=req.comment,
        strategy_id="waste-compound",
        ai_action="COMPOUND_ADD",
        expected_loss_usd=req.expected_loss_usd,
    )


def _open_live_truth() -> dict:
    from cas_forex.time_utils import utc_now

    return {
        "report_kind": "cas_forex_broker_truth_monitor",
        "generated_at": utc_now().isoformat(),
        "overall_status": "RECONCILED",
        "mt5_connected": True,
        "mt5_is_demo": False,
        "mt5_account": 101321,
        "mt5_account_server": "Risen-Trade",
        "mt5_expected_account": 101321,
        "mt5_expected_server": "Risen-Trade",
        "mt5_account_identity_matches_config": True,
        "mt5_open_position_count": 1,
        "terminal_unmatched_open_position_count": 0,
        "terminal_pending_receipt_count": 0,
        "terminal_receipt_mismatch_count": 0,
    }


def _mt5_live_risk_snapshot() -> dict:
    return {
        "connected": True,
        "cached": False,
        "is_demo": False,
        "account": {
            "login": 12345,
            "server": "HugosWay-Live",
            "currency": "USD",
            "leverage": 500,
            "balance_usd": 1000.0,
            "equity_usd": 1000.0,
            "margin_used_usd": 0.0,
            "free_margin_usd": 1000.0,
        },
        "positions": [],
        "open_position_count": 0,
    }


def _mt5_permission_snapshot(
    *,
    connected: bool = True,
    is_demo: bool = False,
    login: int = 12345,
    server: str = "HugosWay-Live",
    can_submit_order_send: bool = True,
    blockers: list[str] | None = None,
    permission_status: str | None = None,
    permission_label: str | None = None,
    detail: str | None = None,
) -> dict:
    blocker_list = list(blockers or [])
    status = permission_status or (
        "MT5_ORDER_SEND_READY" if can_submit_order_send and not blocker_list else "MT5_ORDER_SEND_BLOCKED"
    )
    label = permission_label or ("MT5 READY" if can_submit_order_send and not blocker_list else "MT5 ORDER_SEND BLOCKED")
    plain = (
        "MT5 order_send is ready for the connected real account."
        if can_submit_order_send and not blocker_list
        else "MT5 order_send is blocked before CAS can submit: " + "; ".join(blocker_list or ["Unknown blocker"])
    )
    return {
        "connected": connected,
        "cached": False,
        "is_demo": is_demo,
        "account": {
            "login": login,
            "server": server,
            "currency": "USD",
        },
        "permission_state": {
            "status": status,
            "permission_label": label,
            "can_submit_order_send": can_submit_order_send,
            "blockers": blocker_list,
            "plain_english": plain,
        },
        "detail": detail or ("MT5 terminal permissions are ready." if can_submit_order_send else "MT5 terminal permissions are blocked."),
        "error": None,
    }


def _patch_live_order_gates(monkeypatch) -> None:
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_pilot, "require_live_pilot_intent", lambda *args, **kwargs: {})
    monkeypatch.setattr(live_pilot, "record_live_pilot_dispatch", lambda **kwargs: {})
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)
    monkeypatch.setattr(execution_guard, "_action_time_broker_truth_snapshot", lambda: _open_live_truth())
    monkeypatch.setattr(execution_guard, "_latest_mt5_live_risk_snapshot", lambda: {})
    monkeypatch.setattr(execution_guard, "_latest_mt5_permission_snapshot", lambda: _mt5_permission_snapshot())


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
    impact = result.to_dict()["money_impact"]
    assert impact["broker_bridge_touched"] is True
    assert impact["order_executed"] is True
    assert impact["real_broker"] is False
    assert impact["external_money_movement"] is False
    card = result.to_dict()["trade_explanation_card"]
    assert card["report_kind"] == "cas_forex_trade_explanation_card"
    assert card["protective_orders"]["status"] == "PROTECTED"
    assert card["money_impact"]["order_executed"] is True
    assert card["gate_trace"][-1]["status"] == "EXECUTED"
    provenance = result.to_dict()["execution_provenance"]
    assert provenance["report_kind"] == "cas_forex_execution_provenance"
    assert provenance["schema_version"] == "cas_forex_execution_provenance.v1"
    assert provenance["strategy"]["strategy_id"] == "strat-A"
    assert provenance["strategy"]["ai_action"] == "DISPATCH"
    assert provenance["risk_engine"]["pre_execution_risk_gate_version"] == "pre_execution_risk_gate.v1"
    assert provenance["model"]["ai_operator_prompt_hash"]
    assert provenance["initiator"]["kind"] == "AI_AUTOMATION"
    assert provenance["runtime_lane"]["effective_lane"] == "PAPER_SIMULATED"
    assert provenance["dispatch_path"]["terminal_stage"] == "broker_bridge"
    assert provenance["dispatch_path"]["bridge_touch_state"] == "TOUCHED_CONFIRMED"
    assert provenance["dispatch_path"]["gate_outcome"] == "EXECUTED"
    assert provenance["attempt_audit"]["status"] == "ATTEMPT_RECORDED"
    assert provenance["config_hash"]
    assert provenance["provenance_hash"]
    assert provenance["version_trace"]["dispatch_engine_version"] == "order_dispatch.v1"
    assert provenance["version_trace"]["config_hash"] == provenance["config_hash"]
    assert card["execution_provenance"]["provenance_hash"] == provenance["provenance_hash"]
    assert card["version_trace"]["config_hash"] == provenance["config_hash"]


def test_execution_receipt_prefers_actual_operator_decision_over_static_model_config():
    intent = _intent()
    proposed = {
        "symbol": intent.symbol,
        "direction": intent.direction,
        "lots": float(intent.volume),
        "strategy_id": intent.strategy_id,
        "ai_action": intent.ai_action,
        "sizing_ref": "size-standard-002",
        "sizing_label": "STANDARD",
        "sizing_plan_hash": "plan-hash",
        "operator_event_hash": "operator-event-hash",
        "operator_prompt_version": "ai_operator_trade_edge.v11",
        "operator_decision_prompt_hash": "decision-prompt-hash",
        "operator_system_prompt_hash": "system-prompt-hash",
        "operator_provider": "local-fallback",
        "operator_provider_label": "Local model (deepseek-r1:latest)",
        "operator_model_ref": "deepseek-r1:latest",
        "operator_model_backend": "ollama",
        "operator_decision_context_hash": "context-hash",
        "operator_candidate_snapshot_hash": "candidate-snapshot-hash",
        "operator_candidate_hash": "candidate-hash",
        "operator_decision": "APPROVE",
        "operator_conviction": "MEDIUM",
        "operator_reason": "The exact bounded option has the strongest after-cost case.",
        "growth_evidence_state": "EXACT_GROUP_RISK_NORMALIZED_EDGE",
        "market_regime": "directional_pressure",
        "market_regime_source": "candidate_setup.regime",
        "regime_identity_available": True,
        "regime_comparable_outcome_count": 7,
        "all_regimes_growth_evidence_state": "EXACT_GROUP_POSITIVE_SAMPLE_READY",
        "sizing_options_offered": [
            {
                "sizing_ref": "size-probe-001",
                "label": "PROBE",
                "lots": 0.01,
            },
            {
                "sizing_ref": "size-standard-002",
                "label": "STANDARD",
                "lots": float(intent.volume),
            },
        ],
        "sizing_option_count": 2,
        "max_executable_lots": float(intent.volume),
        "sizing_limiting_source": "max_risk_per_trade_pct",
    }

    result = order_dispatch_module.dispatch_order(
        intent.to_order(),
        SimulatedBrokerBridge(),
        proposed_intent=proposed,
        strategy_id=intent.strategy_id,
        ai_action=intent.ai_action,
        config=_cfg(),
    )

    provenance = result.to_dict()["execution_provenance"]
    assert result.executed is True
    assert provenance["operator_decision"]["model_ref"] == "deepseek-r1:latest"
    assert provenance["operator_decision"]["provider"] == "local-fallback"
    assert provenance["operator_decision"]["candidate_hash"] == "candidate-hash"
    assert provenance["operator_decision"]["decision_context_hash"] == "context-hash"
    assert provenance["strategy"]["market_regime"] == "directional_pressure"
    assert provenance["strategy"]["market_regime_source"] == "candidate_setup.regime"
    assert provenance["strategy"]["strategy_version"] == "strategy_context.v2"
    assert provenance["operator_decision"]["regime_identity_available"] is True
    assert provenance["operator_decision"]["regime_comparable_outcome_count"] == 7
    assert provenance["sizing"]["sizing_ref"] == "size-standard-002"
    assert provenance["sizing"]["selected_lots"] == float(intent.volume)
    assert provenance["sizing"]["sizing_plan_hash"] == "plan-hash"
    assert provenance["sizing"]["offered_option_count"] == 2
    assert provenance["sizing"]["offered_options"][0]["sizing_ref"] == (
        "size-probe-001"
    )
    assert provenance["sizing"]["max_executable_lots"] == float(intent.volume)
    assert provenance["sizing"]["limiting_source"] == "max_risk_per_trade_pct"
    assert provenance["version_trace"]["model_ref"] == "deepseek-r1:latest"
    assert provenance["version_trace"]["model_provider"] == "local-fallback"
    assert provenance["version_trace"]["prompt_version"] == "ai_operator_trade_edge.v11"
    assert provenance["version_trace"]["prompt_hash"] == "decision-prompt-hash"
    assert provenance["version_trace"]["operator_event_hash"] == "operator-event-hash"
    assert provenance["version_trace"]["operator_candidate_hash"] == "candidate-hash"
    assert provenance["version_trace"]["sizing_ref"] == "size-standard-002"
    assert provenance["version_trace"]["sizing_plan_hash"] == "plan-hash"


def test_external_mt5_demo_fill_is_not_labeled_live_or_counted_as_live_pilot(monkeypatch):
    pilot_calls = []
    monkeypatch.setattr(
        live_pilot,
        "record_live_pilot_dispatch",
        lambda **kwargs: pilot_calls.append(kwargs),
    )
    outcome = OrderOutcome(
        order_ref="demo-order",
        broker_ticket=45944826,
        status=OrderStatus.EXECUTED,
        filled_price=1.1000,
        broker_mode=BrokerMode.PAPER_MT5,
        is_real_broker=True,
        is_demo_account=True,
    )
    result = dispatch_intent(
        _intent(order_id="demo-order"),
        _FakeDemoBridge(outcome),
        config=_cfg(),
    )

    impact = result.to_dict()["money_impact"]
    provenance = result.to_dict()["execution_provenance"]
    assert result.executed is True
    assert impact["external_broker_terminal"] is True
    assert impact["account_mode"] == "DEMO"
    assert impact["live_money_broker"] is False
    assert "no live money" in impact["summary"].lower()
    assert provenance["runtime_lane"]["effective_lane"] == "MT5_DEMO_BROKER"
    assert provenance["runtime_lane"]["account_mode"] == "DEMO"
    assert provenance["runtime_lane"]["live_money_broker_confirmed"] is False
    assert provenance["dispatch_path"]["account_mode"] == "DEMO"
    assert pilot_calls == []
    assert "account_mode=DEMO" in result.ledger_event.note
    assert "live_money=False" in result.ledger_event.note


def test_manual_trade_intent_carries_anti_impulse_journal_in_proposed_intent():
    intent = TradeIntent(
        order_id="manual-journal",
        decision_ref="manual-journal",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.01,
        stop_loss=1.0900,
        take_profit=1.1100,
        comment="CAS_FOREX_MANUAL",
        ai_action="MANUAL",
        manual_order_journal={
            "required": True,
            "satisfied": True,
            "reason_length": 52,
            "prompt": "record why this is not impulse trading",
        },
    )

    proposed = intent.proposed_intent()

    assert proposed["manual_order_journal"]["required"] is True
    assert proposed["manual_order_journal"]["satisfied"] is True
    assert proposed["manual_order_journal"]["prompt"] == "record why this is not impulse trading"


def test_dispatch_result_includes_pre_trade_money_estimate():
    bridge = SimulatedBrokerBridge()
    intent = TradeIntent(
        order_id="money-estimate-1",
        decision_ref="dec-money-1",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.1,
        price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1200,
        strategy_id="strat-A",
    )

    result = dispatch_intent(
        intent,
        bridge,
        config=_cfg(),
        account_snapshot={
            "balance": 1000.0,
            "equity": 1000.0,
            "margin": 0.0,
            "free_margin": 1000.0,
            "leverage": 100,
        },
    )

    payload = result.to_dict()
    estimate = payload["pre_trade_estimate"]
    assert estimate["report_kind"] == "cas_forex_pre_trade_money_estimate"
    assert estimate["risk_at_stop_usd"] == 100.0
    assert estimate["risk_at_stop_pct_equity"] == 10.0
    assert estimate["estimated_margin_required_usd"] == 110.0
    assert payload["trade_explanation_card"]["pre_trade_money"] == estimate


def test_dispatch_writes_durable_order_attempt_audit(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "order-attempts.json",
        tmp_path / "order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(_intent(order_id="audit-1"), bridge, config=_cfg(), audit_store=store)

    assert result.status == "BROKER_EXECUTED"
    assert result.audit_status == "ATTEMPT_RECORDED"
    assert result.audit_attempt_id
    status = store.build_status()
    assert status["attempt_count"] == 1
    assert status["executed_count"] == 1
    latest = status["latest_attempt"]
    assert latest["order_id"] == "audit-1"
    assert latest["result_finalized"] is True
    assert latest["dispatched_to_bridge"] is True
    assert latest["outcome"]["broker_mode"] == "SIMULATED"
    assert latest["execution_provenance"]["strategy"]["strategy_id"] == "strat-A"
    assert latest["execution_provenance"]["config_snapshot"]["live_mode"] is False
    assert latest["execution_provenance"]["attempt_audit"]["attempt_id"] == latest["attempt_id"]
    assert latest["execution_provenance"]["attempt_audit"]["status"] == "ATTEMPT_RECORDED"
    assert latest["execution_provenance"]["provenance_hash"]
    assert latest["pre_trade_estimate"]["report_kind"] == "cas_forex_pre_trade_money_estimate"
    # Started + result rows make crash/recovery visible.
    assert len((tmp_path / "order-attempts-audit.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_duplicate_order_id_decision_ref_is_suppressed_before_bridge(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "duplicate-order-attempts.json",
        tmp_path / "duplicate-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    intent = _intent(order_id="dup-order")

    first = dispatch_intent(intent, bridge, config=_cfg(), audit_store=store)
    second = dispatch_intent(intent, bridge, config=_cfg(), audit_store=store)

    assert first.status == "BROKER_EXECUTED"
    assert second.status == STATUS_DUPLICATE_SUPPRESSED
    assert second.dispatched_to_bridge is False
    assert second.outcome is None
    assert "already reached the bridge" in second.reason
    assert len(bridge.get_open_positions()) == 1
    assert store.latest_for_order(intent.to_order())["result_status"] == STATUS_DUPLICATE_SUPPRESSED


def test_recent_same_shape_automation_with_new_id_is_suppressed_before_bridge(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "shape-duplicate-order-attempts.json",
        tmp_path / "shape-duplicate-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    first_intent = _intent(order_id="shape-auto-1")
    second_intent = _intent(order_id="shape-auto-2")

    first = dispatch_intent(first_intent, bridge, config=_cfg(), audit_store=store)
    second = dispatch_intent(second_intent, bridge, config=_cfg(), audit_store=store)

    assert first.status == "BROKER_EXECUTED"
    assert second.status == STATUS_DUPLICATE_SUPPRESSED
    assert second.dispatched_to_bridge is False
    assert "similar automation order shape" in second.reason
    assert len(bridge.get_open_positions()) == 1
    status = store.build_status()
    assert status["duplicate_suppressed_count"] == 1
    assert status["near_duplicate_suppressed_count"] == 1
    assert status["idempotency_policy"]["near_duplicate_scope"] == "automation_only"


def test_recent_same_shape_manual_orders_are_not_near_duplicate_suppressed(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "manual-shape-order-attempts.json",
        tmp_path / "manual-shape-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    first_intent = TradeIntent(
        **{**_intent(order_id="manual-shape-1").__dict__, "ai_action": "MANUAL"}
    )
    second_intent = TradeIntent(
        **{**_intent(order_id="manual-shape-2").__dict__, "ai_action": "MANUAL"}
    )

    first = dispatch_intent(first_intent, bridge, config=_cfg(), audit_store=store)
    second = dispatch_intent(second_intent, bridge, config=_cfg(), audit_store=store)

    assert first.status == "BROKER_EXECUTED"
    assert second.status == "BROKER_EXECUTED"
    assert second.dispatched_to_bridge is True
    assert len(bridge.get_open_positions()) == 2
    assert store.build_status()["near_duplicate_suppressed_count"] == 0


def test_unresolved_real_attempt_suppresses_retry_before_real_bridge(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "unresolved-real-order-attempts.json",
        tmp_path / "unresolved-real-order-attempts-audit.jsonl",
    )
    intent = _intent(order_id="real-crash-window")
    order = intent.to_order()
    store.record_started(
        order,
        proposed_intent=intent.proposed_intent(),
        mode="LIVE",
        is_real_attempt=True,
        bridge_name="MT5Bridge",
        source="test_crash_window",
    )
    bridge = _FakeRealBridge(_executed_outcome("real-crash-window"))

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert result.status == STATUS_DUPLICATE_SUPPRESSED
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert "unresolved real broker attempt" in result.reason
    assert bridge.calls == []


def test_real_bridge_exception_stays_unresolved_and_blocks_retry(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    store = OrderAttemptAuditStore(
        tmp_path / "uncertain-real-order-attempts.json",
        tmp_path / "uncertain-real-order-attempts-audit.jsonl",
    )
    intent = _intent(order_id="real-uncertain-1")
    _authorize_intent(intent, config=_authorized_live_cfg())

    class _ThrowingRealBridge:
        def __init__(self) -> None:
            self.calls: list = []

        def will_execute_real_order(self) -> bool:
            return True

        def execute_order(self, order):
            self.calls.append(order)
            raise RuntimeError("mt5 ack timeout")

    throwing_bridge = _ThrowingRealBridge()
    failed = dispatch_intent(
        intent,
        throwing_bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert failed.status == STATUS_DISPATCH_ERROR
    assert failed.dispatched_to_bridge is True
    assert "Broker bridge touch is unknown" in failed.reason
    assert failed.audit_status == "ATTEMPT_BROKER_REVIEW_REQUIRED"
    assert len(throwing_bridge.calls) == 1

    audit = store.build_status()
    assert audit["unresolved_real_attempt_count"] == 1
    assert audit["has_unresolved_real_attempt"] is True
    unresolved = audit["unresolved_real_attempts"][0]
    assert unresolved["attempt_id"] == failed.audit_attempt_id
    assert unresolved["result_finalized"] is False
    assert unresolved["result_status"] == STATUS_DISPATCH_ERROR
    assert unresolved["bridge_touch_unknown"] is True
    assert unresolved["requires_owner_review_before_retry"] is True
    assert "mt5 ack timeout" in str(unresolved["last_dispatch_error"])
    assert failed.execution_provenance["dispatch_path"]["bridge_touch_state"] == "TOUCH_UNKNOWN"
    assert unresolved["execution_provenance"]["attempt_audit"]["status"] == "ATTEMPT_BROKER_REVIEW_REQUIRED"

    retry_bridge = _FakeRealBridge(_executed_outcome("real-uncertain-1"))
    retry = dispatch_intent(
        intent,
        retry_bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert retry.status == STATUS_DUPLICATE_SUPPRESSED
    assert retry.dispatched_to_bridge is False
    assert "unresolved real broker attempt" in retry.reason
    assert retry_bridge.calls == []


def test_risk_cap_breach_blocks_before_bridge():
    bridge = SimulatedBrokerBridge()
    # 2.5 lots on an empty book exceeds the AI dial's 2.0-lot total-exposure cap.
    result = dispatch_intent(_intent(volume=2.5), bridge, config=_cfg(broker_max_lot=10.0))

    assert result.status == STATUS_BLOCKED_RISK
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert "max_total_exposure_lots" in result.risk_blocking_caps
    impact = result.to_dict()["money_impact"]
    assert impact["broker_bridge_touched"] is False
    assert impact["order_executed"] is False
    assert impact["summary"] == "No broker bridge was touched; no order was placed."
    card = result.to_dict()["trade_explanation_card"]
    risk_stage = next(stage for stage in card["gate_trace"] if stage["stage"] == "risk_engine")
    assert risk_stage["status"] == "BLOCKED"
    assert risk_stage["blocking_caps"] == ["max_total_exposure_lots"]
    assert card["protective_orders"]["status"] == "PROTECTED"
    assert card["pre_trade_money"]["report_kind"] == "cas_forex_pre_trade_money_estimate"
    assert card["pre_trade_money"]["status"] == "PARTIAL"
    provenance = result.to_dict()["execution_provenance"]
    assert provenance["risk_engine"]["risk_control_version"] == "risk_control.v1"
    assert provenance["broker_bridge"]["bridge_name"] == "SimulatedBrokerBridge"
    assert provenance["order_shape"]["symbol"] == "EUR/USD"
    assert provenance["dispatch_path"]["terminal_stage"] == "risk_engine"
    assert provenance["dispatch_path"]["bridge_touch_state"] == "NOT_TOUCHED"
    assert provenance["dispatch_path"]["gate_outcome"] == "BLOCKED"
    # The bridge must never have been reached.
    assert bridge.get_open_positions() == []


def test_projected_margin_utilization_cap_blocks_before_bridge():
    bridge = SimulatedBrokerBridge()
    intent = TradeIntent(
        order_id="margin-cap-block",
        decision_ref="dec-margin-cap",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.1,
        price=1.1000,
        stop_loss=1.0995,
        take_profit=1.1100,
        strategy_id="strat-A",
    )

    result = dispatch_intent(
        intent,
        bridge,
        config=_cfg(max_margin_utilization_pct=70.0),
        account_snapshot={
            "balance": 1000.0,
            "equity": 1000.0,
            "margin": 600.0,
            "free_margin": 400.0,
            "leverage": 100.0,
        },
    )

    assert result.status == STATUS_BLOCKED_RISK
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert "max_margin_utilization_pct" in result.risk_blocking_caps
    assert "would become 71%" in result.reason
    assert result.pre_trade_estimate["estimated_margin_required_usd"] == 110.0
    assert result.pre_trade_estimate["estimated_margin_utilization_after_pct"] == 71.0
    assert bridge.get_open_positions() == []


def test_broker_aware_margin_block_rejects_when_free_margin_would_go_negative():
    class _BrokerAwarePaperBridge(SimulatedBrokerBridge):
        def symbol_info(self, symbol):
            if symbol != "EURUSD":
                return None
            return NS(
                point=0.00001,
                digits=5,
                volume_min=0.01,
                volume_max=10.0,
                volume_step=0.01,
                trade_contract_size=100000.0,
                trade_tick_size=0.00001,
                trade_tick_value=1.0,
                trade_stops_level=0,
                trade_freeze_level=0,
            )

        def symbols_get(self, pattern=None):
            return [NS(name="EURUSD")]

        def symbol_info_tick(self, symbol):
            return NS(ask=1.1000, bid=1.0999)

        def account_info(self):
            return NS(leverage=500)

        def order_calc_margin(self, order_type, symbol, volume, price):
            assert symbol == "EURUSD"
            assert volume == 0.1
            return 120.0

    bridge = _BrokerAwarePaperBridge()
    intent = TradeIntent(
        order_id="broker-margin-block",
        decision_ref="dec-broker-margin-block",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.1,
        stop_loss=1.0995,
        take_profit=1.1100,
        strategy_id="strat-A",
    )

    result = dispatch_intent(
        intent,
        bridge,
        config=_cfg(max_margin_utilization_pct=None),
        account_snapshot={
            "balance": 1000.0,
            "equity": 1000.0,
            "margin": 950.0,
            "free_margin": 50.0,
        },
    )

    assert result.status == STATUS_BLOCKED_RISK
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert "insufficient_free_margin" in result.risk_blocking_caps
    assert "free margin would become -$70.00 from $50.00" in result.reason
    assert result.pre_trade_estimate["margin_estimate_source"] == "broker.order_calc_margin"
    assert result.pre_trade_estimate["selected_broker_symbol"] == "EURUSD"
    assert result.pre_trade_estimate["estimated_margin_required_usd"] == 120.0
    assert result.pre_trade_estimate["estimated_free_margin_after_usd"] == -70.0
    assert bridge.get_open_positions() == []


class _IndexTickValuePaperBridge(SimulatedBrokerBridge):
    def symbol_info(self, symbol):
        if symbol != "US30":
            return None
        return NS(
            point=0.01,
            digits=2,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            trade_contract_size=1.0,
            trade_tick_size=0.01,
            trade_tick_value=1.0,
            trade_tick_value_loss=1.0,
            trade_tick_value_profit=1.0,
            trade_stops_level=0,
            trade_freeze_level=0,
        )

    def symbols_get(self, pattern=None):
        return [NS(name="US30")]

    def get_account_info(self):
        return {
            "balance": 44_779.12,
            "equity": 44_779.12,
            "margin": 0.0,
            "margin_free": 44_779.12,
            "leverage": 500,
        }


def test_broker_tick_value_stop_risk_cap_blocks_index_order_before_bridge():
    bridge = _IndexTickValuePaperBridge()
    intent = TradeIntent(
        order_id="index-risk-block",
        decision_ref="dec-index-risk-block",
        symbol="US30",
        direction="SHORT",
        volume=0.01,
        price=52_597.82,
        stop_loss=52_997.82,
        take_profit=52_374.18,
        strategy_id="index-risk-test",
        expected_loss_usd=1.0,
    )

    result = dispatch_intent(intent, bridge, config=_cfg())

    assert result.status == STATUS_BLOCKED_RISK
    assert result.dispatched_to_bridge is False
    assert result.risk_blocking_caps == ("max_risk_per_trade_pct",)
    assert result.pre_trade_estimate["broker_unit_value_per_lot_usd"] == 100.0
    assert result.pre_trade_estimate["risk_at_stop_usd"] == 400.0
    assert result.pre_trade_estimate["risk_source"].startswith("conservative_max(")
    assert result.pre_trade_estimate["risk_at_stop_pct_equity"] == 0.8933
    assert bridge.get_open_positions() == []


def test_risk_blocked_dispatch_is_still_audited(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "order-attempts.json",
        tmp_path / "order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="audit-risk", volume=2.5),
        bridge,
        config=_cfg(broker_max_lot=10.0),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_RISK
    assert result.audit_status == "ATTEMPT_RECORDED"
    latest = store.latest_attempt()
    assert latest["order_id"] == "audit-risk"
    assert latest["result_status"] == STATUS_BLOCKED_RISK
    assert latest["dispatched_to_bridge"] is False
    assert latest["risk_blocking_caps"] == ["max_total_exposure_lots"]
    assert latest["execution_provenance"]["strategy"]["strategy_id"] == "strat-A"
    assert latest["execution_provenance"]["provenance_hash"]
    assert latest["pre_trade_estimate"]["report_kind"] == "cas_forex_pre_trade_money_estimate"


def test_market_closed_blocks_before_bridge_and_is_audited(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "market-closed-order-attempts.json",
        tmp_path / "market-closed-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="market-closed"),
        bridge,
        config=_cfg(),
        live_telemetry={"is_market_open": False, "session_status": "CLOSED"},
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_MARKET
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert bridge.get_open_positions() == []
    payload = result.to_dict()
    assert payload["market_availability"]["status"] == "BLOCKED"
    assert payload["market_availability"]["block"] is True
    assert "is_market_open=false" in payload["reason"]
    market_stage = next(
        stage for stage in payload["trade_explanation_card"]["gate_trace"]
        if stage["stage"] == "market_availability"
    )
    assert market_stage["status"] == "BLOCKED"
    assert market_stage["blockers"]
    assert payload["money_impact"]["broker_bridge_touched"] is False
    latest = store.latest_attempt()
    assert latest["result_status"] == STATUS_BLOCKED_MARKET
    assert latest["dispatched_to_bridge"] is False
    assert latest["market_availability"]["status"] == "BLOCKED"
    assert latest["result"]["market_availability"]["status"] == "BLOCKED"


def test_stale_attached_quote_blocks_at_action_time_before_bridge():
    from cas_forex.time_utils import utc_now

    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="stale-action-time-quote"),
        bridge,
        config=_cfg(dispatch_quote_max_age_seconds=10),
        live_telemetry={
            "market_snapshot": {
                "symbol": "EUR/USD",
                "bid": 1.1000,
                "ask": 1.1001,
                "is_market_open": True,
                "timestamp": (utc_now() - timedelta(seconds=30)).isoformat(),
            }
        },
    )

    assert result.status == STATUS_BLOCKED_MARKET
    assert result.dispatched_to_bridge is False
    assert "quote is stale" in result.reason
    assert bridge.get_open_positions() == []


def test_materially_future_attached_quote_blocks_at_action_time_before_bridge():
    from cas_forex.time_utils import utc_now

    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="future-action-time-quote"),
        bridge,
        config=_cfg(dispatch_quote_future_tolerance_seconds=2),
        live_telemetry={
            "market_snapshot": {
                "symbol": "EUR/USD",
                "bid": 1.1000,
                "ask": 1.1001,
                "is_market_open": True,
                "timestamp": (utc_now() + timedelta(seconds=30)).isoformat(),
            }
        },
    )

    assert result.status == STATUS_BLOCKED_MARKET
    assert result.dispatched_to_bridge is False
    assert "ahead of the host clock" in result.reason
    assert bridge.get_open_positions() == []


def test_fresh_attached_quote_remains_dispatchable():
    from cas_forex.time_utils import utc_now

    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="fresh-action-time-quote"),
        bridge,
        config=_cfg(dispatch_quote_max_age_seconds=10),
        live_telemetry={
            "market_snapshot": {
                "symbol": "EUR/USD",
                "bid": 1.1000,
                "ask": 1.1001,
                "is_market_open": True,
                "timestamp": utc_now().isoformat(),
            }
        },
    )

    assert result.status == "BROKER_EXECUTED"
    assert result.dispatched_to_bridge is True
    assert result.market_availability["status"] == "PASSED"
    assert any(
        row.get("key") == "timestamp" and row.get("available") is True
        for row in result.market_availability["evidence"]
    )


def test_symbol_trade_mode_blocks_direction_incompatible_market_dispatch():
    bridge = SimulatedBrokerBridge()
    short_intent = TradeIntent(
        order_id="short-market-mode",
        decision_ref="dec-short-mode",
        symbol="EUR/USD",
        direction="SHORT",
        volume=0.1,
        stop_loss=1.1100,
        take_profit=1.0900,
        strategy_id="strat-A",
    )

    result = dispatch_intent(
        short_intent,
        bridge,
        config=_cfg(),
        live_telemetry={
            "symbols": {
                "EURUSDm": {
                    "symbol": "EURUSDm",
                    "trade_mode": "LONGONLY",
                    "is_market_open": True,
                }
            }
        },
    )

    assert result.status == STATUS_BLOCKED_MARKET
    assert result.dispatched_to_bridge is False
    assert "LONGONLY blocks short entry" in result.reason
    assert bridge.get_open_positions() == []


def test_wide_spread_blocks_before_bridge_and_is_audited(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "wide-spread-order-attempts.json",
        tmp_path / "wide-spread-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="wide-spread"),
        bridge,
        config=_cfg(),
        live_telemetry={
            "market_snapshot": {
                "symbol": "EUR/USD",
                "bid": 1.1000,
                "ask": 1.1010,
                "is_market_open": True,
            }
        },
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_EXECUTION_QUALITY
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert bridge.get_open_positions() == []
    payload = result.to_dict()
    assert payload["execution_quality"]["status"] == "BLOCKED"
    assert payload["execution_quality"]["block"] is True
    assert "spread_pips=10.00 exceeds limit 5.00" in payload["reason"]
    quality_stage = next(
        stage for stage in payload["trade_explanation_card"]["gate_trace"]
        if stage["stage"] == "execution_quality"
    )
    assert quality_stage["status"] == "BLOCKED"
    assert payload["money_impact"]["broker_bridge_touched"] is False
    latest = store.latest_attempt()
    assert latest["result_status"] == STATUS_BLOCKED_EXECUTION_QUALITY
    assert latest["execution_quality"]["status"] == "BLOCKED"
    assert latest["result"]["execution_quality"]["status"] == "BLOCKED"


def test_expected_slippage_blocks_before_bridge():
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="wide-slippage"),
        bridge,
        config=_cfg(),
        live_telemetry={
            "market_snapshot": {
                "symbol": "EUR/USD",
                "bid": 1.1000,
                "ask": 1.1001,
                "is_market_open": True,
                "expected_slippage_pips": 4.5,
            }
        },
    )

    assert result.status == STATUS_BLOCKED_EXECUTION_QUALITY
    assert result.dispatched_to_bridge is False
    assert "slippage_pips=4.50 exceeds limit 3.00" in result.reason
    assert bridge.get_open_positions() == []


def test_dispatch_hydrates_market_snapshot_and_blocks_on_wide_connector_spread(monkeypatch):
    from cas_forex.time_utils import utc_now

    class _WideSpreadConnector:
        last_error = ""
        broker_grade_market_truth = True

        def fetch_snapshot(self, symbol):
            return NS(
                symbol=symbol,
                bid=1.1000,
                ask=1.1010,
                spread=10.0,
                is_market_open=True,
                session="LONDON",
                    timestamp=utc_now().isoformat(),
                synthetic_fallback=False,
            )

    monkeypatch.setattr(order_dispatch_module, "_quote_connector_candidates", lambda config=None: [_WideSpreadConnector()])
    bridge = SimulatedBrokerBridge()

    result = dispatch_intent(
        _intent(order_id="hydrated-wide-spread"),
        bridge,
        config=_cfg(),
        live_telemetry={
            "price_source_status": "LIVE",
            "data_freshness": {"stale": False},
        },
    )

    assert result.status == STATUS_BLOCKED_EXECUTION_QUALITY
    assert "spread_pips=10.00 exceeds limit 5.00" in result.reason
    payload = result.to_dict()
    assert any(
        row["source"] == "live_telemetry.market_snapshot"
        for row in payload["execution_quality"]["evidence"]
    )
    assert bridge.get_open_positions() == []


def test_dispatch_skips_quote_hydration_when_explicit_market_snapshot_exists(monkeypatch):
    def _unexpected_quote_hydration(symbol: str, *, config=None):
        raise AssertionError("dispatch should not hydrate a connector quote when live_telemetry already has one")

    monkeypatch.setattr(order_dispatch_module, "_build_dispatch_quote_snapshot", _unexpected_quote_hydration)
    bridge = SimulatedBrokerBridge()

    result = dispatch_intent(
        _intent(order_id="explicit-market-snapshot"),
        bridge,
        config=_cfg(),
        live_telemetry={
            "market_snapshot": {
                "symbol": "EUR/USD",
                "bid": 1.1000,
                "ask": 1.1001,
                "is_market_open": True,
            }
        },
    )

    assert result.status == "BROKER_EXECUTED"
    assert result.dispatched_to_bridge is True
    assert bridge.get_open_positions() != []


def test_build_dispatch_quote_snapshot_falls_back_to_mt5_when_primary_provider_symbol_is_unsupported(monkeypatch):
    class _UnsupportedPrimary:
        broker_grade_market_truth = False
        last_error = "symbol NAS100 is not available on the configured OANDA account"

        def fetch_snapshot(self, symbol):
            return NS(
                symbol=symbol,
                bid=19999.0,
                ask=20001.0,
                spread=2.0,
                is_market_open=False,
                session="CLOSED",
                timestamp="2026-07-09T12:00:00+00:00",
                synthetic_fallback=True,
            )

    class _Mt5Fallback:
        broker_grade_market_truth = True
        last_error = ""

        def fetch_snapshot(self, symbol):
            return NS(
                symbol=symbol,
                bid=20100.0,
                ask=20101.0,
                spread=1.0,
                is_market_open=True,
                session="NEW_YORK",
                timestamp="2026-07-09T12:00:01+00:00",
                synthetic_fallback=False,
            )

    monkeypatch.setattr(
        order_dispatch_module,
        "_quote_connector_candidates",
        lambda config=None: [_UnsupportedPrimary(), _Mt5Fallback()],
    )

    quote_context = order_dispatch_module._build_dispatch_quote_snapshot("NAS100", config=_cfg())

    assert quote_context["quote_source"] == "mt5"
    assert quote_context["quote_fallback_used"] is True
    assert "configured OANDA account" in quote_context["quote_feed_label"]
    assert quote_context["market_snapshot"]["broker_grade_market_truth"] is True


def test_build_dispatch_quote_snapshot_canonicalizes_mt5_broker_symbol_alias(monkeypatch):
    seen_symbols: list[str] = []

    class _Mt5Quote:
        broker_grade_market_truth = True
        last_error = ""

        def fetch_snapshot(self, symbol):
            seen_symbols.append(symbol)
            return NS(
                symbol=symbol,
                bid=161.344,
                ask=161.348,
                spread=0.4,
                is_market_open=True,
                session="NEW_YORK",
                timestamp="2026-07-10T16:29:41+00:00",
                synthetic_fallback=False,
            )

    monkeypatch.setattr(
        order_dispatch_module,
        "_quote_connector_candidates",
        lambda config=None, **kwargs: [_Mt5Quote()],
    )

    quote_context = order_dispatch_module.build_dispatch_quote_context(
        "USDJPY",
        config=_cfg(),
        prefer_mt5=True,
    )

    assert seen_symbols == ["USD/JPY"]
    assert quote_context["quote_source"] == "mt5"
    assert quote_context["market_snapshot"]["symbol"] == "USD/JPY"
    assert quote_context["market_snapshot"]["broker_grade_market_truth"] is True


def test_order_volume_below_broker_min_blocks_before_bridge_and_is_audited(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "small-lot-order-attempts.json",
        tmp_path / "small-lot-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="small-lot", volume=0.001),
        bridge,
        config=_cfg(broker_min_lot=0.01),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_ORDER_CONSTRAINTS
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert bridge.get_open_positions() == []
    payload = result.to_dict()
    assert payload["order_constraints"]["status"] == "BLOCKED"
    assert payload["order_constraints"]["block"] is True
    assert "below broker minimum" in payload["reason"]
    constraint_stage = next(
        stage for stage in payload["trade_explanation_card"]["gate_trace"]
        if stage["stage"] == "order_constraints"
    )
    assert constraint_stage["status"] == "BLOCKED"
    assert payload["money_impact"]["broker_bridge_touched"] is False
    latest = store.latest_attempt()
    assert latest["result_status"] == STATUS_BLOCKED_ORDER_CONSTRAINTS
    assert latest["order_constraints"]["status"] == "BLOCKED"
    assert latest["result"]["order_constraints"]["status"] == "BLOCKED"


def test_order_volume_above_broker_max_blocks_before_risk_and_bridge():
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="large-lot-broker", volume=0.1),
        bridge,
        config=_cfg(max_total_exposure_lots=10.0, broker_max_lot=0.05),
    )

    assert result.status == STATUS_BLOCKED_ORDER_CONSTRAINTS
    assert result.dispatched_to_bridge is False
    assert "exceeds broker maximum" in result.reason
    assert bridge.get_open_positions() == []


def test_native_mt5_contract_replaces_generic_simulator_max_lot():
    class _NativeMetaTraderApi:
        def symbol_info(self, symbol):
            if symbol != "EURUSD":
                return None
            return NS(
                point=0.00001,
                digits=5,
                trade_mode=4,
                volume_min=0.01,
                volume_step=0.01,
                volume_max=1000.0,
                trade_stops_level=0,
                trade_freeze_level=0,
            )

        def symbols_get(self, pattern=None):
            return [NS(name="EURUSD")]

        def symbol_select(self, symbol, selected):
            return symbol == "EURUSD" and selected is True

    class _NativeMt5Bridge:
        def __init__(self):
            self._mt5 = _NativeMetaTraderApi()

        def is_connected(self):
            return True

    intent = _intent(order_id="native-mt5-large-lot", volume=1.09)
    report = order_dispatch_module._order_constraints_report(
        order=intent.to_order(),
        proposed_intent=intent.proposed_intent(),
        live_telemetry=None,
        account_snapshot=None,
        bridge=_NativeMt5Bridge(),
        config=_cfg(broker_max_lot=1.0),
    )

    lot_check = next(check for check in report["checks"] if check["check"] == "lot_bounds")
    assert report["status"] == "PARTIAL"
    assert report["block"] is False
    assert lot_check["status"] == "PASSED"
    assert lot_check["configured_max_lot"] == 1.0
    assert lot_check["max_lot"] == 1000.0
    assert lot_check["configured_lot_bounds_apply"] is False
    assert lot_check["lot_bound_authority"] == "native_broker_contract"


def test_explicit_price_tight_stop_distance_blocks_before_bridge():
    bridge = SimulatedBrokerBridge()
    intent = TradeIntent(
        order_id="tight-explicit-stop",
        decision_ref="dec-tight-explicit",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.1,
        price=1.1000,
        stop_loss=1.0998,
        take_profit=1.1010,
        strategy_id="strat-A",
    )
    result = dispatch_intent(
        intent,
        bridge,
        config=_cfg(broker_min_stop_distance_pips=5.0),
    )

    assert result.status == STATUS_BLOCKED_ORDER_CONSTRAINTS
    assert result.dispatched_to_bridge is False
    assert "stop_loss distance 2.00 is below broker minimum 5.00 pips" in result.reason
    assert bridge.get_open_positions() == []


def test_market_quote_tight_stop_distance_blocks_before_bridge():
    bridge = SimulatedBrokerBridge()
    intent = TradeIntent(
        order_id="tight-quote-stop",
        decision_ref="dec-tight-quote",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.1,
        stop_loss=1.0998,
        take_profit=1.1010,
        strategy_id="strat-A",
    )
    result = dispatch_intent(
        intent,
        bridge,
        config=_cfg(broker_min_stop_distance_pips=5.0),
        live_telemetry={
            "market_snapshot": {
                "symbol": "EUR/USD",
                "bid": 1.0999,
                "ask": 1.1000,
                "is_market_open": True,
            }
        },
    )

    assert result.status == STATUS_BLOCKED_ORDER_CONSTRAINTS
    assert result.dispatched_to_bridge is False
    assert result.to_dict()["order_constraints"]["checks"][1]["entry_source"] == "live_telemetry.market_snapshot.ask"
    assert bridge.get_open_positions() == []


def test_real_dispatch_blocks_when_broker_symbol_is_unresolved(tmp_path, monkeypatch):
    class _BrokerAwareRealBridge(_FakeRealBridge):
        def connect(self):
            return True

        def is_connected(self):
            return True

        def symbol_info(self, symbol):
            return None

        def symbols_get(self, pattern=None):
            return []

    _patch_live_order_gates(monkeypatch)
    bridge = _BrokerAwareRealBridge(_executed_outcome("ord-unresolved-symbol"))
    intent = _intent(order_id="ord-unresolved-symbol")
    cfg = _authorized_live_cfg()
    _authorize_intent(intent, config=cfg)
    store = OrderAttemptAuditStore(
        tmp_path / "unresolved-symbol-order-attempts.json",
        tmp_path / "unresolved-symbol-order-attempts-audit.jsonl",
    )

    result = dispatch_intent(
        intent,
        bridge,
        config=cfg,
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_ORDER_CONSTRAINTS
    assert "No visible MT5 symbol was found" in result.reason
    payload = result.to_dict()
    assert payload["order_constraints"]["broker_symbol_resolution"]["status"] == "UNRESOLVED"
    assert payload["order_constraints"]["selected_broker_symbol"] is None
    assert bridge.calls == []


def test_real_dispatch_blocks_when_volume_misses_broker_lot_step(tmp_path, monkeypatch):
    class _BrokerAwareRealBridge(_FakeRealBridge):
        def connect(self):
            return True

        def is_connected(self):
            return True

        def symbol_info(self, symbol):
            if symbol != "EURUSD":
                return None
            return NS(
                point=0.00001,
                digits=5,
                trade_mode=4,
                volume_min=0.1,
                volume_step=0.1,
                volume_max=10.0,
                trade_stops_level=0,
                trade_freeze_level=0,
            )

        def symbols_get(self, pattern=None):
            return [NS(name="EURUSD")]

    _patch_live_order_gates(monkeypatch)
    bridge = _BrokerAwareRealBridge(_executed_outcome("ord-broker-step"))
    intent = TradeIntent(
        order_id="ord-broker-step",
        decision_ref="dec-broker-step",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.15,
        stop_loss=1.0900,
        take_profit=1.1100,
        strategy_id="strat-A",
    )
    cfg = _authorized_live_cfg()
    _authorize_intent(intent, config=cfg)

    result = dispatch_intent(
        intent,
        bridge,
        config=cfg,
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
    )

    assert result.status == STATUS_BLOCKED_ORDER_CONSTRAINTS
    assert "broker lot step 0.1" in result.reason
    payload = result.to_dict()
    assert payload["order_constraints"]["selected_broker_symbol"] == "EURUSD"
    assert payload["order_constraints"]["broker_contract_constraints"]["lot_step"] == 0.1
    assert bridge.calls == []


def test_real_dispatch_uses_stricter_broker_stop_distance_when_available(tmp_path, monkeypatch):
    class _BrokerAwareRealBridge(_FakeRealBridge):
        def connect(self):
            return True

        def is_connected(self):
            return True

        def symbol_info(self, symbol):
            if symbol != "EURUSD":
                return None
            return NS(
                point=0.00001,
                digits=5,
                trade_mode=4,
                volume_min=0.01,
                volume_step=0.01,
                volume_max=10.0,
                trade_stops_level=80,
                trade_freeze_level=0,
            )

        def symbols_get(self, pattern=None):
            return [NS(name="EURUSD")]

    _patch_live_order_gates(monkeypatch)
    bridge = _BrokerAwareRealBridge(_executed_outcome("ord-broker-stops"))
    intent = TradeIntent(
        order_id="ord-broker-stops",
        decision_ref="dec-broker-stops",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.1,
        price=1.1000,
        stop_loss=1.0995,
        take_profit=1.1010,
        strategy_id="strat-A",
    )
    cfg = _authorized_live_cfg()
    _authorize_intent(intent, config=cfg)

    result = dispatch_intent(
        intent,
        bridge,
        config=cfg,
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
    )

    assert result.status == STATUS_BLOCKED_ORDER_CONSTRAINTS
    assert "below broker minimum 8.00 pips" in result.reason
    payload = result.to_dict()
    assert payload["order_constraints"]["broker_contract_constraints"]["min_stop_distance_pips"] == 8.0
    assert payload["order_constraints"]["selected_broker_symbol"] == "EURUSD"
    assert bridge.calls == []


def test_macro_blackout_blocks_before_bridge_and_is_audited(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "macro-blackout-order-attempts.json",
        tmp_path / "macro-blackout-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="macro-blackout"),
        bridge,
        config=_cfg(macro_blackout_enabled=True),
        live_telemetry={
            "macro_blackout_active": True,
            "macro_reason": "NFP blackout window active",
        },
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_MACRO
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert bridge.get_open_positions() == []
    payload = result.to_dict()
    assert payload["macro_blackout"]["status"] == "BLOCKED"
    assert payload["macro_blackout"]["block"] is True
    assert payload["macro_blackout"]["calendar_source_status"] == "STATIC_SEED_CALENDAR"
    assert payload["macro_blackout"]["static_seed_used"] is True
    assert payload["macro_blackout"]["generic_status_evidence_count"] >= 1
    assert "macro_blackout_active=true" in payload["reason"]
    macro_stage = next(
        stage for stage in payload["trade_explanation_card"]["gate_trace"]
        if stage["stage"] == "macro_blackout"
    )
    assert macro_stage["status"] == "BLOCKED"
    assert payload["money_impact"]["broker_bridge_touched"] is False
    latest = store.latest_attempt()
    assert latest["result_status"] == STATUS_BLOCKED_MACRO
    assert latest["macro_blackout"]["status"] == "BLOCKED"
    assert latest["result"]["macro_blackout"]["status"] == "BLOCKED"


def test_macro_calendar_event_window_blocks_before_bridge():
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="macro-event-window"),
        bridge,
        config=_cfg(macro_blackout_enabled=True, blackout_before_nfp_minutes=20, blackout_after_nfp_minutes=10),
        live_telemetry={
            "macro_now_iso": "2026-07-08T12:20:00+00:00",
            "macro_events": [
                {
                    "event_id": "nfp-test",
                    "event_type": "NFP",
                    "currency": "USD",
                    "impact": "HIGH",
                    "scheduled_at_utc": "2026-07-08T12:30:00+00:00",
                }
            ],
        },
    )

    assert result.status == STATUS_BLOCKED_MACRO
    assert result.dispatched_to_bridge is False
    assert "NFP active" in result.reason
    macro = result.to_dict()["macro_blackout"]
    assert macro["calendar_source_status"] == "EXTERNAL_EVENT_EVIDENCE"
    assert macro["external_event_count"] == 1
    assert macro["static_seed_used"] is True
    assert bridge.get_open_positions() == []


def test_configured_economic_calendar_feed_event_blocks_before_bridge(tmp_path):
    feed_path = tmp_path / "economic-calendar.json"
    feed_path.write_text(
        """
        {
          "events": [
            {
              "id": "external-nfp",
              "event": "Non Farm Payrolls",
              "currency": "USD",
              "impact": "HIGH",
              "scheduled_at_utc": "2026-07-08T12:30:00Z"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="macro-configured-feed"),
        bridge,
        config=_cfg(
            macro_blackout_enabled=True,
            blackout_before_nfp_minutes=20,
            blackout_after_nfp_minutes=10,
            economic_calendar_feed_path=str(feed_path),
            economic_calendar_cache_path=str(tmp_path / "calendar-cache.json"),
        ),
        live_telemetry={"macro_now_iso": "2026-07-08T12:20:00+00:00"},
    )

    assert result.status == STATUS_BLOCKED_MACRO
    assert result.dispatched_to_bridge is False
    assert bridge.get_open_positions() == []
    macro = result.to_dict()["macro_blackout"]
    assert macro["calendar_source_status"] == "EXTERNAL_EVENT_EVIDENCE"
    assert macro["economic_calendar_feed"]["status"] == "LOADED"
    assert macro["economic_calendar_feed"]["event_count"] == 1
    assert any(row["source"] == "economic_calendar_feed" and row.get("active") for row in macro["evidence"])
    assert "economic_calendar_feed.NFP active" in result.reason


def test_configured_economic_calendar_feed_can_fail_closed_before_bridge(tmp_path):
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="macro-feed-fail-closed"),
        bridge,
        config=_cfg(
            macro_blackout_enabled=True,
            economic_calendar_feed_path=str(tmp_path / "missing-calendar.json"),
            economic_calendar_cache_path=str(tmp_path / "calendar-cache.json"),
            economic_calendar_fail_closed=True,
        ),
        live_telemetry={"macro_now_iso": "2026-07-08T00:00:00+00:00"},
    )

    assert result.status == STATUS_BLOCKED_MACRO
    assert result.dispatched_to_bridge is False
    assert bridge.get_open_positions() == []
    macro = result.to_dict()["macro_blackout"]
    assert macro["economic_calendar_feed"]["status"] == "FETCH_FAILED"
    assert macro["economic_calendar_feed"]["fail_closed_on_error"] is True
    assert "fail-closed mode is enabled" in result.reason


def test_static_macro_seed_calendar_source_is_reported_when_no_external_events():
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="static-macro-source-clear"),
        bridge,
        config=_cfg(macro_blackout_enabled=True),
        live_telemetry={"macro_now_iso": "2026-07-08T00:00:00+00:00"},
    )

    payload = result.to_dict()
    assert result.status == "BROKER_EXECUTED"
    assert payload["macro_blackout"]["status"] == "PASSED"
    assert payload["macro_blackout"]["calendar_source_status"] == "STATIC_SEED_CALENDAR"
    assert payload["macro_blackout"]["external_event_count"] == 0
    assert payload["macro_blackout"]["static_seed_used"] is True
    assert "static seed macro calendar" in payload["macro_blackout"]["calendar_source_detail"]
    assert len(bridge.get_open_positions()) == 1


def test_macro_blackout_disabled_reports_disabled_and_does_not_block():
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(
        _intent(order_id="macro-disabled"),
        bridge,
        config=_cfg(macro_blackout_enabled=False),
        live_telemetry={"macro_blackout_active": True},
    )

    assert result.status == "BROKER_EXECUTED"
    assert result.dispatched_to_bridge is True
    assert result.to_dict()["macro_blackout"]["status"] == "DISABLED"
    assert result.to_dict()["macro_blackout"]["calendar_source_status"] == "DISABLED"
    assert len(bridge.get_open_positions()) == 1


def test_live_mode_without_authorization_blocks_at_dispatch(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "live-gate-order-attempts.json",
        tmp_path / "live-gate-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    intent = _intent()
    _authorize_intent(intent, config=_cfg(live_mode=True))
    # live_mode=True with no enable flag / creds -> live-trading gate NOT LICENSED.
    result = dispatch_intent(
        intent,
        bridge,
        config=_cfg(live_mode=True),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_LIVE_GATE
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert bridge.get_open_positions() == []
    gate_trace = result.to_dict()["trade_explanation_card"]["gate_trace"]
    live_gate = next(stage for stage in gate_trace if stage["stage"] == "live_gate")
    assert live_gate["status"] == "BLOCKED"
    assert result.to_dict()["execution_provenance"]["dispatch_path"]["terminal_stage"] == "live_gate"


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


def test_real_bridge_requires_live_gate_even_when_live_mode_off(tmp_path):
    # GB-1 regression: a bridge that would place a real order must require the
    # owner live-trading gate even with live_mode off (gate is NOT keyed only on
    # config.live_mode). No enable flags -> blocked at the dispatch chokepoint.
    bridge = _FakeRealBridge(_executed_outcome("ord-1"))
    store = OrderAttemptAuditStore(
        tmp_path / "real-bridge-gate-order-attempts.json",
        tmp_path / "real-bridge-gate-order-attempts-audit.jsonl",
    )
    intent = _intent()
    _authorize_intent(intent, config=_cfg(live_mode=False), is_real=True)
    result = dispatch_intent(
        intent,
        bridge,
        config=_cfg(live_mode=False),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_LIVE_GATE
    assert result.dispatched_to_bridge is False
    assert bridge.calls == []  # the real bridge was never touched


def test_real_dispatch_without_fresh_broker_truth_surfaces_broker_truth_stage(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: False)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_pilot, "require_live_pilot_intent", lambda *args, **kwargs: {})
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)
    monkeypatch.setattr(
        execution_guard,
        "_action_time_broker_truth_snapshot",
        lambda: {
            "overall_status": "RECONCILIATION_FAILED",
            "monitor_status": "STALE",
            "mt5_connected": False,
            "mt5_is_demo": False,
            "mt5_open_position_count": 0,
            "terminal_unmatched_open_position_count": 1,
            "terminal_unattributed_open_position_count": 1,
            "terminal_memory_gap_open_position_count": 0,
            "terminal_unmatched_history_count": 1,
            "terminal_unattributed_history_count": 1,
            "terminal_attributed_history_memory_gap_count": 0,
            "terminal_pending_receipt_count": 1,
            "terminal_receipt_mismatch_count": 0,
            "fresh_for_live_seconds": None,
            "next_action": "Run broker truth refresh before live dispatch.",
        },
    )
    bridge = _FakeRealBridge(_executed_outcome("ord-no-truth"))
    intent = _intent(order_id="ord-no-truth")
    _authorize_intent(intent, config=_authorized_live_cfg())

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=OrderAttemptAuditStore(
            tmp_path / "no-truth-attempts.json",
            tmp_path / "no-truth-attempts-audit.jsonl",
        ),
    )

    assert result.status == STATUS_BLOCKED_LIVE_GATE
    gate_trace = result.to_dict()["trade_explanation_card"]["gate_trace"]
    broker_truth = next(stage for stage in gate_trace if stage["stage"] == "broker_truth")
    live_gate = next(stage for stage in gate_trace if stage["stage"] == "live_gate")
    assert broker_truth["status"] == "BLOCKED"
    assert "fresh broker truth" in broker_truth["detail"].lower()
    assert broker_truth["evidence_snapshot"]["overall_status"] == "RECONCILIATION_FAILED"
    assert broker_truth["evidence_snapshot"]["terminal_unmatched_open_position_count"] == 1
    assert broker_truth["evidence_snapshot"]["terminal_unattributed_open_position_count"] == 1
    assert broker_truth["evidence_snapshot"]["terminal_unmatched_history_count"] == 1
    assert broker_truth["evidence_snapshot"]["terminal_unattributed_history_count"] == 1
    assert live_gate["status"] == "PASSED"
    assert result.to_dict()["trade_explanation_card"]["live_readiness_evidence"]["broker_truth"]
    assert result.execution_provenance["dispatch_path"]["terminal_stage"] == "broker_truth"
    assert bridge.calls == []


def test_real_dispatch_blocks_when_action_time_broker_truth_refresh_fails(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    monkeypatch.setattr(
        execution_guard,
        "_action_time_broker_truth_snapshot",
        lambda: {
            **_open_live_truth(),
            "action_time_refresh_performed": True,
            "action_time_refresh_error": "RuntimeError: MT5 refresh subprocess failed",
        },
    )
    bridge = _FakeRealBridge(_executed_outcome("ord-truth-refresh-failed"))
    intent = _intent(order_id="ord-truth-refresh-failed")
    _authorize_intent(intent, config=_authorized_live_cfg())

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=OrderAttemptAuditStore(
            tmp_path / "truth-refresh-failed-attempts.json",
            tmp_path / "truth-refresh-failed-attempts-audit.jsonl",
        ),
    )

    assert result.status == STATUS_BLOCKED_LIVE_GATE
    gate_trace = result.to_dict()["trade_explanation_card"]["gate_trace"]
    broker_truth = next(stage for stage in gate_trace if stage["stage"] == "broker_truth")
    assert broker_truth["status"] == "BLOCKED"
    assert "action-time broker-truth refresh failed" in broker_truth["detail"].lower()
    assert broker_truth["evidence_snapshot"]["action_time_refresh_error"] == "RuntimeError: MT5 refresh subprocess failed"
    assert result.execution_provenance["dispatch_path"]["terminal_stage"] == "broker_truth"
    assert bridge.calls == []


def test_real_dispatch_without_live_risk_snapshot_surfaces_snapshot_stage(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    bridge = _FakeRealBridge(_executed_outcome("ord-no-risk"))
    intent = _intent(order_id="ord-no-risk")
    _authorize_intent(intent, config=_authorized_live_cfg())

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry={"data_freshness": {"stale": True}},
        account_snapshot={"balance": 1000.0, "equity": 1000.0},
        audit_store=OrderAttemptAuditStore(
            tmp_path / "no-risk-attempts.json",
            tmp_path / "no-risk-attempts-audit.jsonl",
        ),
    )

    assert result.status == STATUS_BLOCKED_LIVE_GATE
    gate_trace = result.to_dict()["trade_explanation_card"]["gate_trace"]
    risk_snapshot = next(stage for stage in gate_trace if stage["stage"] == "live_risk_snapshot")
    assert risk_snapshot["status"] == "BLOCKED"
    assert "live risk telemetry" in risk_snapshot["detail"].lower()
    assert "non_stale_live_telemetry" in risk_snapshot["missing_requirements"]
    assert result.execution_provenance["dispatch_path"]["terminal_stage"] == "live_risk_snapshot"
    assert bridge.calls == []


def test_real_dispatch_accepts_fresh_action_time_broker_truth_even_if_cached_helper_is_false(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: False)
    bridge = _FakeRealBridge(_executed_outcome("ord-fresh-truth-wins"))
    intent = _intent(order_id="ord-fresh-truth-wins")
    _authorize_intent(intent, config=_authorized_live_cfg())

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=OrderAttemptAuditStore(
            tmp_path / "fresh-truth-wins-attempts.json",
            tmp_path / "fresh-truth-wins-attempts-audit.jsonl",
        ),
    )

    assert result.status == "BROKER_EXECUTED"
    assert result.dispatched_to_bridge is True
    assert bridge.calls


def test_real_dispatch_self_hydrates_missing_live_risk_snapshot_from_mt5(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    monkeypatch.setattr(execution_guard, "_latest_mt5_live_risk_snapshot", lambda: _mt5_live_risk_snapshot())
    bridge = _FakeRealBridge(_executed_outcome("ord-hydrated-risk"))
    intent = _intent(order_id="ord-hydrated-risk")
    _authorize_intent(intent, config=_authorized_live_cfg())

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=None,
        account_snapshot=None,
        audit_store=OrderAttemptAuditStore(
            tmp_path / "hydrated-risk-attempts.json",
            tmp_path / "hydrated-risk-attempts-audit.jsonl",
        ),
    )

    assert result.status == "BROKER_EXECUTED"
    assert result.dispatched_to_bridge is True
    assert bridge.calls


def test_real_dispatch_without_mt5_terminal_permissions_surfaces_terminal_stage(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    monkeypatch.setattr(
        execution_guard,
        "_latest_mt5_permission_snapshot",
        lambda: _mt5_permission_snapshot(
            can_submit_order_send=False,
            blockers=["MT5 Algo Trading is off in the terminal."],
            detail="Connected live account, but MT5 terminal trade permissions are off.",
        ),
    )
    bridge = _FakeRealBridge(_executed_outcome("ord-no-terminal"))
    intent = _intent(order_id="ord-no-terminal")
    _authorize_intent(intent, config=_authorized_live_cfg())

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=OrderAttemptAuditStore(
            tmp_path / "no-terminal-attempts.json",
            tmp_path / "no-terminal-attempts-audit.jsonl",
        ),
    )

    assert result.status == STATUS_BLOCKED_LIVE_GATE
    gate_trace = result.to_dict()["trade_explanation_card"]["gate_trace"]
    terminal_stage = next(stage for stage in gate_trace if stage["stage"] == "mt5_terminal_permissions")
    assert terminal_stage["status"] == "BLOCKED"
    assert "algo trading is off" in terminal_stage["detail"].lower()
    assert terminal_stage["evidence_snapshot"]["permission_state"]["can_submit_order_send"] is False
    evidence = result.to_dict()["trade_explanation_card"]["live_readiness_evidence"]
    assert evidence["mt5_terminal_permissions"]["permission_state"]["blockers"] == ["MT5 Algo Trading is off in the terminal."]
    assert result.execution_provenance["dispatch_path"]["terminal_stage"] == "mt5_terminal_permissions"
    assert bridge.calls == []


def test_real_dispatch_outside_live_pilot_surfaces_live_pilot_stage(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    monkeypatch.setattr(
        execution_guard,
        "_live_pilot_snapshot",
        lambda: {
            "owner_pilot_status": "ARMED",
            "ready_for_next_live_order": False,
            "pilot_capacity_remaining": 0,
            "live_trade_count": 1,
            "allowed_symbols": [],
            "max_trade_lots": 0.01,
            "max_open_live_lots": 0.01,
            "missing_requirements": ["allowed_symbols"],
            "next_action": "Add allowed symbols before the next live pilot order.",
        },
    )
    bridge = _FakeRealBridge(_executed_outcome("ord-pilot-block"))
    intent = _intent(order_id="ord-pilot-block")
    _authorize_intent(intent, config=_authorized_live_cfg())

    def _blocked_pilot(*args, **kwargs):
        raise live_pilot.LivePilotError("Live pilot blocks order: EUR/USD outside live pilot allowed_symbols")

    monkeypatch.setattr(live_pilot, "require_live_pilot_intent", _blocked_pilot)

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=OrderAttemptAuditStore(
            tmp_path / "pilot-block-attempts.json",
            tmp_path / "pilot-block-attempts-audit.jsonl",
        ),
    )

    assert result.status == STATUS_BLOCKED_LIVE_GATE
    gate_trace = result.to_dict()["trade_explanation_card"]["gate_trace"]
    live_pilot_stage = next(stage for stage in gate_trace if stage["stage"] == "live_pilot")
    assert live_pilot_stage["status"] == "BLOCKED"
    assert "outside live pilot allowed_symbols" in live_pilot_stage["detail"]
    assert result.to_dict()["trade_explanation_card"]["live_readiness_evidence"]["live_pilot"]["allowed_symbols"] == []
    assert result.execution_provenance["dispatch_path"]["terminal_stage"] == "live_pilot"
    assert bridge.calls == []


def test_real_dispatch_without_fresh_edge_reports_edge_block(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    bridge = _FakeRealBridge(_executed_outcome("ord-no-edge"))
    store = OrderAttemptAuditStore(
        tmp_path / "real-edge-block-order-attempts.json",
        tmp_path / "real-edge-block-order-attempts-audit.jsonl",
    )
    result = dispatch_intent(
        _intent(order_id="ord-no-edge"),
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_EDGE_AUTHORIZATION
    assert result.dispatched_to_bridge is False
    assert "edge authorization" in result.reason
    assert bridge.calls == []
    edge_stage = next(
        stage for stage in result.to_dict()["trade_explanation_card"]["gate_trace"]
        if stage["stage"] == "edge_authorization"
    )
    assert edge_stage["status"] == "BLOCKED"


def test_real_dispatch_with_changed_live_config_reports_edge_block(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    authorized_cfg = _authorized_live_cfg()
    intent = _intent(order_id="ord-config-drift")
    _authorize_intent(intent, config=authorized_cfg)
    changed_cfg = _authorized_live_cfg()
    changed_cfg.max_total_exposure_lots = 0.75
    bridge = _FakeRealBridge(_executed_outcome("ord-config-drift"))
    store = OrderAttemptAuditStore(
        tmp_path / "real-edge-config-drift-order-attempts.json",
        tmp_path / "real-edge-config-drift-order-attempts-audit.jsonl",
    )

    result = dispatch_intent(
        intent,
        bridge,
        config=changed_cfg,
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_EDGE_AUTHORIZATION
    assert "config snapshot changed" in result.reason
    assert result.dispatched_to_bridge is False
    assert bridge.calls == []


def test_real_dispatch_with_changed_order_type_reports_edge_block(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    authorized_cfg = _authorized_live_cfg()
    _authorize_intent(_intent(order_id="ord-shape"), config=authorized_cfg)
    tampered_intent = TradeIntent(
        order_id="ord-shape",
        decision_ref="dec-1",
        symbol="EUR/USD",
        direction="LONG",
        volume=0.1,
        price=1.1000,
        stop_loss=1.0900,
        take_profit=1.1100,
        order_type="LIMIT",
        strategy_id="strat-A",
    )
    bridge = _FakeRealBridge(_executed_outcome("ord-shape"))
    store = OrderAttemptAuditStore(
        tmp_path / "real-edge-shape-order-attempts.json",
        tmp_path / "real-edge-shape-order-attempts-audit.jsonl",
    )

    result = dispatch_intent(
        tampered_intent,
        bridge,
        config=authorized_cfg,
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_EDGE_AUTHORIZATION
    assert "order type mismatch" in result.reason
    assert result.dispatched_to_bridge is False
    assert bridge.calls == []


def test_real_dispatch_with_changed_strategy_reports_edge_block(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    authorized_cfg = _authorized_live_cfg()
    authorized_intent = _intent(order_id="ord-strategy")
    _authorize_intent(authorized_intent, config=authorized_cfg)
    tampered_intent = TradeIntent(
        order_id="ord-strategy",
        decision_ref=authorized_intent.decision_ref,
        symbol=authorized_intent.symbol,
        direction=authorized_intent.direction,
        volume=authorized_intent.volume,
        stop_loss=authorized_intent.stop_loss,
        take_profit=authorized_intent.take_profit,
        price=authorized_intent.price,
        order_type=authorized_intent.order_type,
        strategy_id="manual-override",
    )
    bridge = _FakeRealBridge(_executed_outcome("ord-strategy"))
    store = OrderAttemptAuditStore(
        tmp_path / "real-edge-strategy-order-attempts.json",
        tmp_path / "real-edge-strategy-order-attempts-audit.jsonl",
    )

    result = dispatch_intent(
        tampered_intent,
        bridge,
        config=authorized_cfg,
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_EDGE_AUTHORIZATION
    assert "strategy mismatch" in result.reason
    assert result.dispatched_to_bridge is False
    assert bridge.calls == []


def test_real_capable_dispatch_blocks_if_pre_bridge_audit_unavailable():
    class _BrokenAuditStore:
        def record_started(self, *args, **kwargs):
            raise OSError("disk unavailable")

    bridge = _FakeRealBridge(_executed_outcome("ord-1"))
    result = dispatch_intent(
        _intent(),
        bridge,
        config=_cfg(live_mode=False),
        audit_store=_BrokenAuditStore(),
    )

    assert result.status == STATUS_DISPATCH_ERROR
    assert "Order audit unavailable before real dispatch" in result.reason
    assert result.dispatched_to_bridge is False
    assert result.audit_status == "AUDIT_UNAVAILABLE"
    assert bridge.calls == []


def test_authorized_live_dispatch_reaches_real_bridge(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    # GAP 3: with live trading fully owner-authorized, an approved order actually
    # reaches the (fake) live-money bridge and the ledger note records the
    # external-broker and LIVE account classification separately.
    bridge = _FakeRealBridge(_executed_outcome("ord-1"))
    intent = _intent()
    _authorize_intent(intent, config=_authorized_live_cfg())  # live dispatch now also requires a tested edge PASS
    store = OrderAttemptAuditStore(
        tmp_path / "authorized-live-order-attempts.json",
        tmp_path / "authorized-live-order-attempts-audit.jsonl",
    )
    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert result.status == "BROKER_EXECUTED"
    assert result.dispatched_to_bridge is True
    assert len(bridge.calls) == 1
    assert result.ledger_event is not None
    assert "external_broker=True" in result.ledger_event.note
    assert "account_mode=LIVE" in result.ledger_event.note
    assert "live_money=True" in result.ledger_event.note


def test_compound_add_dispatch_blocks_without_owner_accepted_fingerprint(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    bridge = _FakeRealBridge(_executed_outcome("compound-add-1"))
    req = _compound_add_request()
    intent = _compound_add_intent(req)
    _authorize_intent(intent, config=_authorized_live_cfg())
    store = OrderAttemptAuditStore(
        tmp_path / "compound-add-blocked-order-attempts.json",
        tmp_path / "compound-add-blocked-order-attempts-audit.jsonl",
    )

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot=_live_account_snapshot(),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_COMPOUND_ADD_REVIEW
    assert "Compound-add owner ACCEPT is not current" in result.reason
    assert result.dispatched_to_bridge is False
    assert bridge.calls == []


def test_compound_add_dispatch_requires_exact_owner_accepted_fingerprint(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    audit_path = tmp_path / "compound-add-audit.jsonl"
    review_state = tmp_path / "compound-add-review.json"
    review_audit = tmp_path / "compound-add-review-audit.jsonl"
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_STATE_PATH", review_state)
    monkeypatch.setattr(compound_add_order_dry_run_review, "DEFAULT_AUDIT_PATH", review_audit)
    broker_truth = _open_live_truth()
    monkeypatch.setattr(compound_add_order_dry_run_review, "_latest_broker_truth", lambda: broker_truth)

    req = _compound_add_request()
    dry_run_order = req.to_live_order_request()
    _authorize_intent(dry_run_order, config=_authorized_live_cfg())
    dry_run = build_compound_add_order_dry_run(
        req,
        config=_authorized_live_cfg(),
        audit=LiveOrderDryRunAuditLog(audit_path),
    )
    accepted = compound_add_order_dry_run_review.accept_compound_add_order_dry_run_review(
        notes="Owner accepted exact compound add in dispatch test.",
        confirm_owner_accept=True,
        dry_run_audit=dry_run["audit"],
        broker_truth_report=broker_truth,
        state_path=review_state,
        audit_path=review_audit,
    )
    assert accepted["compound_add_dry_run_review_clear_for_dispatch"] is True

    bridge = _FakeRealBridge(_executed_outcome(req.add_order_id))
    intent = _compound_add_intent(req)
    store = OrderAttemptAuditStore(
        tmp_path / "compound-add-order-attempts.json",
        tmp_path / "compound-add-order-attempts-audit.jsonl",
    )
    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        live_telemetry=_live_risk_telemetry(),
        account_snapshot={
            "balance": 5_000.0,
            "equity": 5_000.0,
            "margin": 0.0,
            "free_margin": 5_000.0,
        },
        audit_store=store,
    )

    assert result.status == "BROKER_EXECUTED"
    assert result.dispatched_to_bridge is True
    assert len(bridge.calls) == 1

    changed_bridge = _FakeRealBridge(_executed_outcome("changed-add"))
    changed = dispatch_intent(
        _compound_add_intent(req, order_id="changed-add"),
        changed_bridge,
        config=_authorized_live_cfg(),
        audit_store=store,
    )

    assert changed.status == STATUS_BLOCKED_COMPOUND_ADD_REVIEW
    assert "does not match owner-accepted dry-run" in changed.reason
    assert changed.dispatched_to_bridge is False
    assert changed_bridge.calls == []


def test_pending_outcome_counted_in_pending_bucket():
    # OD-1: a queued (PENDING) outcome belongs to its own bucket so the counts
    # reconcile: executed + blocked + rejected + pending == intent_count.
    pending = OrderOutcome(
        order_ref="ord-1",
        broker_ticket=None,
        status=OrderStatus.PENDING,
        broker_mode=BrokerMode.PAPER_MT4,
        is_real_broker=False,
    )

    class _PendingBridge:
        def execute_order(self, order):
            return pending

    report = dispatch_intents([_intent()], bridge=_PendingBridge(), config=_cfg())
    assert report.pending_count == 1
    assert report.executed_count == 0
    total = (
        report.executed_count
        + report.blocked_count
        + report.rejected_count
        + report.pending_count
    )
    assert total == report.intent_count


def test_dispatch_error_does_not_raise_and_is_recorded():
    # OD-2: a bridge exposing neither execute_order nor place_order must not
    # break the "never raises" contract — it becomes a per-intent DISPATCH_ERROR.
    class _BrokenBridge:
        pass

    report = dispatch_intents([_intent()], bridge=_BrokenBridge(), config=_cfg())
    assert report.intent_count == 1
    assert report.results[0].status == STATUS_DISPATCH_ERROR
    assert report.results[0].dispatched_to_bridge is False
    assert report.rejected_count == 1


def test_bridge_exception_becomes_dispatch_error():
    class _ThrowingBridge:
        def execute_order(self, order):
            raise RuntimeError("broker socket closed")

    result = dispatch_intent(_intent(), _ThrowingBridge(), config=_cfg())
    assert result.status == STATUS_DISPATCH_ERROR
    assert "broker socket closed" in result.reason


def test_dispatch_works_through_mt4_mailbox_bridge(monkeypatch, tmp_path):
    # The gated dispatch loop is broker-agnostic: it drives the MT4 EA mailbox
    # bridge too. MT4 is paper/demo-only here. With a FRESH EA heartbeat the
    # order is written as a paper command intent (PAPER_MT4) and returns PENDING
    # (its own report bucket). Without one the mailbox is dead — the dispatch
    # must reject loudly instead of silently queueing a command no EA will read.
    from pathlib import Path

    from cas_forex.broker.mt5_bridge import MT4EABridge
    from cas_forex.config import config as global_config

    mailbox = str(tmp_path / "mt4")
    monkeypatch.setattr(global_config, "mt4_enabled", True)
    monkeypatch.setattr(global_config, "paper_trading", True)
    monkeypatch.setattr(global_config, "live_mode", False)
    monkeypatch.setattr(global_config, "mt4_mailbox_dir", mailbox)

    bridge = MT4EABridge(mailbox_dir=mailbox)

    # Dead mailbox (no EA heartbeat): fail loudly, never queue into the void.
    dead = dispatch_intent(_intent(order_id="mt4-dead"), bridge, config=_cfg())
    assert dead.status == "BROKER_REJECTED"

    # Fresh heartbeat: the EA link is alive, the command is written and PENDING.
    Path(mailbox).mkdir(parents=True, exist_ok=True)
    (Path(mailbox) / "heartbeat.json").write_text('{"state": "alive"}', encoding="utf-8")
    result = dispatch_intent(_intent(order_id="mt4-live"), bridge, config=_cfg())

    assert result.dispatched_to_bridge is True
    assert result.status == "BROKER_PENDING"
    assert result.outcome.broker_mode.value == "PAPER_MT4"
    assert result.outcome.is_real_broker is False
    # MT4 mailbox is paper -> the live gate is not required to dispatch.
    assert bridge.will_execute_real_order() is False


def test_batch_report_counts_and_mode():
    bridge = SimulatedBrokerBridge()
    intents = [
        _intent(order_id="ok-1", volume=0.1),
        _intent(order_id="too-big", volume=2.5),  # risk-blocked by exposure cap
    ]
    report = dispatch_intents(intents, bridge=bridge, config=_cfg(broker_max_lot=10.0))

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


def test_market_block_counts_as_blocked_not_rejected():
    report = dispatch_intents(
        [_intent(order_id="market-count")],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        live_telemetry={"market_status": "CLOSED"},
    )

    assert report.intent_count == 1
    assert report.blocked_count == 1
    assert report.rejected_count == 0
    assert report.results[0].status == STATUS_BLOCKED_MARKET


def test_execution_quality_block_counts_as_blocked_not_rejected():
    report = dispatch_intents(
        [_intent(order_id="quality-count")],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(),
        live_telemetry={
            "market_snapshot": {
                "symbol": "EUR/USD",
                "bid": 1.1000,
                "ask": 1.1010,
                "is_market_open": True,
            }
        },
    )

    assert report.intent_count == 1
    assert report.blocked_count == 1
    assert report.rejected_count == 0
    assert report.results[0].status == STATUS_BLOCKED_EXECUTION_QUALITY


def test_macro_block_counts_as_blocked_not_rejected():
    report = dispatch_intents(
        [_intent(order_id="macro-count")],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(macro_blackout_enabled=True),
        live_telemetry={"news_blackout_active": True},
    )

    assert report.intent_count == 1
    assert report.blocked_count == 1
    assert report.rejected_count == 0
    assert report.results[0].status == STATUS_BLOCKED_MACRO


def test_order_constraints_block_counts_as_blocked_not_rejected():
    report = dispatch_intents(
        [_intent(order_id="constraint-count", volume=0.001)],
        bridge=SimulatedBrokerBridge(),
        config=_cfg(broker_min_lot=0.01),
    )

    assert report.intent_count == 1
    assert report.blocked_count == 1
    assert report.rejected_count == 0
    assert report.results[0].status == STATUS_BLOCKED_ORDER_CONSTRAINTS


def test_management_effect_enters_order_dispatch_before_bridge(monkeypatch):
    calls: list[str] = []

    class Bridge:
        def modify_position(self, ticket, *, stop_loss, take_profit=None):
            calls.append(f"bridge:{ticket}:{stop_loss}:{take_profit}")
            return OrderOutcome(
                order_ref=f"modify-{ticket}",
                broker_ticket=ticket,
                status=OrderStatus.EXECUTED,
            )

    monkeypatch.setattr(
        order_dispatch_module,
        "require_trade_management_action_ready",
        lambda action, config=None, bridge=None: calls.append("guard") or {"status": "ACCEPT"},
    )
    action = {
        "broker_method": "modify_position",
        "broker_ticket": 123456,
        "stop_loss": 100.0,
        "take_profit": 140.0,
    }

    result = dispatch_trade_management_action(action, bridge=Bridge())

    assert result["status"] == "DISPATCHED"
    assert result["broker_result"]["accepted"] is True
    assert result["execution_provenance"]["report_kind"] == (
        "cas_forex_execution_provenance"
    )
    assert result["execution_provenance"]["source"] == (
        "order_dispatch.trade_management"
    )
    assert result["execution_provenance"]["dispatch_path"]["gate_outcome"] == (
        "EXECUTED"
    )
    assert calls == ["guard", "bridge:123456:100.0:140.0"]


def test_simulated_management_reference_price_is_set_after_guard_before_close(monkeypatch):
    calls: list[str] = []

    class Bridge:
        def set_reference_price(self, ticket, price):
            calls.append(f"price:{ticket}:{price}")
            return True

        def close_position(self, ticket, volume=None):
            calls.append(f"close:{ticket}:{volume}")
            return True

    monkeypatch.setattr(
        "cas_forex.order_dispatch.require_trade_management_action_ready",
        lambda action, config=None, bridge=None: calls.append("guard") or {"status": "ACCEPT"},
    )

    result = dispatch_trade_management_action(
        {
            "broker_method": "close_position",
            "broker_ticket": 123456,
            "current_price": 1.1015,
            "volume": 0.04,
        },
        bridge=Bridge(),
    )

    assert result["status"] == "DISPATCHED"
    assert calls == ["guard", "price:123456:1.1015", "close:123456:0.04"]


def test_management_order_dispatch_guard_block_never_calls_bridge(monkeypatch):
    class Bridge:
        def close_position(self, ticket, volume=None):
            raise AssertionError("bridge must not be called")

    def block(*_args, **_kwargs):
        raise PermissionError("management geometry rejected")

    monkeypatch.setattr(
        order_dispatch_module,
        "require_trade_management_action_ready",
        block,
    )

    result = dispatch_trade_management_action(
        {
            "broker_method": "close_position",
            "broker_ticket": 123456,
            "volume": None,
        },
        bridge=Bridge(),
    )

    assert result["status"] == "EXECUTION_GUARD_BLOCKED"
    assert result["broker_touched"] is False
    assert result["broker_method_called"] is False
