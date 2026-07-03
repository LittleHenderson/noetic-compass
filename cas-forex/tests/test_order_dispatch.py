"""Tests for the order dispatch loop — signal -> gate -> bridge -> ledger.

Exercises the paper path against SimulatedBrokerBridge end-to-end, plus the two
block paths (risk cap breach, live-trading gate) and the pre-check rejection.
"""

from __future__ import annotations

from types import SimpleNamespace

from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.order_dispatch import (
    STATUS_BLOCKED_COMPOUND_ADD_REVIEW,
    STATUS_BLOCKED_LIVE_GATE,
    STATUS_BLOCKED_RISK,
    STATUS_DISPATCH_ERROR,
    STATUS_REJECTED_PRECHECK,
    TradeIntent,
    dispatch_intent,
    dispatch_intents,
    dispatched_ledger_events,
)
from cas_forex.schemas.order import BrokerMode, OrderOutcome, OrderStatus

import pytest

from cas_forex import (
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


@pytest.fixture(autouse=True)
def _reset_edge_registry():
    # The fail-closed edge gate (edge_authorization) is process-global; isolate it
    # per test so a live-dispatch registration never leaks into the paper-path tests.
    _EA.reset()
    yield
    _EA.reset()


def _authorize_intent(intent) -> None:
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
    _EA.authorize(intent.decision_ref, dec, setup)


def _cfg(*, live_mode: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
        live_mode=live_mode,
    )


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


def _executed_outcome(order_id: str) -> OrderOutcome:
    return OrderOutcome(
        order_ref=order_id,
        broker_ticket=999001,
        status=OrderStatus.EXECUTED,
        filled_price=1.1000,
        broker_mode=BrokerMode.LIVE_MT5,
        is_real_broker=True,
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
        "mt5_open_position_count": 1,
        "terminal_unmatched_open_position_count": 0,
        "terminal_pending_receipt_count": 0,
        "terminal_receipt_mismatch_count": 0,
    }


def _patch_live_order_gates(monkeypatch) -> None:
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_pilot, "require_live_pilot_intent", lambda *args, **kwargs: {})
    monkeypatch.setattr(live_pilot, "record_live_pilot_dispatch", lambda **kwargs: {})
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)


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
    # Started + result rows make crash/recovery visible.
    assert len((tmp_path / "order-attempts-audit.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_risk_cap_breach_blocks_before_bridge():
    bridge = SimulatedBrokerBridge()
    # 2.5 lots on an empty book exceeds the AI dial's 2.0-lot total-exposure cap.
    result = dispatch_intent(_intent(volume=2.5), bridge, config=_cfg())

    assert result.status == STATUS_BLOCKED_RISK
    assert result.dispatched_to_bridge is False
    assert result.outcome is None
    assert "max_total_exposure_lots" in result.risk_blocking_caps
    # The bridge must never have been reached.
    assert bridge.get_open_positions() == []


def test_risk_blocked_dispatch_is_still_audited(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "order-attempts.json",
        tmp_path / "order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    result = dispatch_intent(_intent(order_id="audit-risk", volume=2.5), bridge, config=_cfg(), audit_store=store)

    assert result.status == STATUS_BLOCKED_RISK
    assert result.audit_status == "ATTEMPT_RECORDED"
    latest = store.latest_attempt()
    assert latest["order_id"] == "audit-risk"
    assert latest["result_status"] == STATUS_BLOCKED_RISK
    assert latest["dispatched_to_bridge"] is False
    assert latest["risk_blocking_caps"] == ["max_total_exposure_lots"]


def test_live_mode_without_authorization_blocks_at_dispatch(tmp_path):
    store = OrderAttemptAuditStore(
        tmp_path / "live-gate-order-attempts.json",
        tmp_path / "live-gate-order-attempts-audit.jsonl",
    )
    bridge = SimulatedBrokerBridge()
    # live_mode=True with no enable flag / creds -> live-trading gate NOT LICENSED.
    result = dispatch_intent(
        _intent(),
        bridge,
        config=_cfg(live_mode=True),
        audit_store=store,
    )

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


def test_real_bridge_requires_live_gate_even_when_live_mode_off(tmp_path):
    # GB-1 regression: a bridge that would place a real order must require the
    # owner live-trading gate even with live_mode off (gate is NOT keyed only on
    # config.live_mode). No enable flags -> blocked at the dispatch chokepoint.
    bridge = _FakeRealBridge(_executed_outcome("ord-1"))
    store = OrderAttemptAuditStore(
        tmp_path / "real-bridge-gate-order-attempts.json",
        tmp_path / "real-bridge-gate-order-attempts-audit.jsonl",
    )
    result = dispatch_intent(
        _intent(),
        bridge,
        config=_cfg(live_mode=False),
        audit_store=store,
    )

    assert result.status == STATUS_BLOCKED_LIVE_GATE
    assert result.dispatched_to_bridge is False
    assert bridge.calls == []  # the real bridge was never touched


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
    # reaches the (fake) real bridge and the ledger note records real_broker=True.
    bridge = _FakeRealBridge(_executed_outcome("ord-1"))
    intent = _intent()
    _authorize_intent(intent)  # live dispatch now also requires a tested edge PASS
    store = OrderAttemptAuditStore(
        tmp_path / "authorized-live-order-attempts.json",
        tmp_path / "authorized-live-order-attempts-audit.jsonl",
    )
    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
        audit_store=store,
    )

    assert result.status == "BROKER_EXECUTED"
    assert result.dispatched_to_bridge is True
    assert len(bridge.calls) == 1
    assert result.ledger_event is not None
    assert "real_broker=True" in result.ledger_event.note


def test_compound_add_dispatch_blocks_without_owner_accepted_fingerprint(tmp_path, monkeypatch):
    _patch_live_order_gates(monkeypatch)
    bridge = _FakeRealBridge(_executed_outcome("compound-add-1"))
    req = _compound_add_request()
    intent = _compound_add_intent(req)
    _authorize_intent(intent)
    store = OrderAttemptAuditStore(
        tmp_path / "compound-add-blocked-order-attempts.json",
        tmp_path / "compound-add-blocked-order-attempts-audit.jsonl",
    )

    result = dispatch_intent(
        intent,
        bridge,
        config=_authorized_live_cfg(),
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
    _authorize_intent(dry_run_order)
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
    # MT4 mailbox is paper -> the live gate is not required to dispatch.
    assert bridge.will_execute_real_order() is False


def test_batch_report_counts_and_mode():
    bridge = SimulatedBrokerBridge()
    intents = [
        _intent(order_id="ok-1", volume=0.1),
        _intent(order_id="too-big", volume=2.5),  # risk-blocked (over the 2.0-lot dial)
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
