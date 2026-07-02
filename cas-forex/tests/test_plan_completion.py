"""Plan-completion compliance tests for the CAS Forex hardening lanes."""

import json
import uuid
from datetime import datetime

import pytest

from cas_forex.backtest.engine import BacktestEngine
from cas_forex.broker.mt5_bridge import MT4EABridge, SimulatedBrokerBridge, get_bridge
from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.forecast.harness import ForecastHarness
from cas_forex.post_trade import PostTradeHarness
from cas_forex.schemas.decision import CASDecision, GateResult, GateStatus, Verdict
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus
from cas_forex.schemas.forecast import Direction, ForecastProposal, ModelSource
from cas_forex.schemas.forecast_harness import (
    ForecastHarnessVerdict,
    ForecastSignal,
    ForecastSignalStatus,
)
from cas_forex.schemas.live_lock import LiveLockReason
from cas_forex.schemas.macro import MacroEventState, MacroEventType
from cas_forex.schemas.order import (
    BrokerMode,
    BrokerOrderRequest,
    BrokerLockReason,
    OrderOutcome,
    OrderStatus,
)
from cas_forex.schemas.risk import RiskAssessment
from cas_forex.schemas.sweep import ProfitSweepPolicy, SweepMode, SweepStatus, TransferBoundary
from cas_forex.sweep.sweeper import ProfitSweeper
from cas_forex.verifier.live_lock import LiveLockController
from cas_forex.verifier.macro_gate import MacroGate, StaticMacroCalendarProvider


def _packet(trace_id="trace-001", status=PacketStatus.PROPOSED):
    packet = ForexEvidencePacket(
        packet_id=str(uuid.uuid4()),
        trace_id=trace_id,
        status=status,
        notes=["test packet"],
    )
    packet.finalize()
    return packet


def _proposal(direction=Direction.LONG, proposal_id="prop-001"):
    return ForecastProposal(
        proposal_id=proposal_id,
        symbol="EUR/USD",
        direction=direction,
        entry_price=1.1000,
        stop_loss=1.0950 if direction == Direction.LONG else 1.1050,
        take_profit=1.1100 if direction == Direction.LONG else 1.0900,
        confidence=0.8,
        model_source=ModelSource.ENSEMBLE,
    )


def _order(volume=0.05):
    return BrokerOrderRequest(
        order_id="ord-001",
        decision_ref="dec-001",
        symbol="EUR/USD",
        direction=Direction.LONG,
        volume=volume,
        price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
    )


def _write_mt4_heartbeat(mailbox_dir):
    mailbox_dir.mkdir(parents=True, exist_ok=True)
    (mailbox_dir / "heartbeat.json").write_text(
        json.dumps(
            {
                "schema": "cas_forex_mt4_mailbox_heartbeat.v1",
                "state": "RUNNING",
                "server": "DemoServer",
                "live_trading_allowed": False,
            }
        ),
        encoding="utf-8",
    )


def _risk(**overrides):
    data = {
        "assessment_id": "risk-001",
        "account_balance": 10000.0,
        "account_equity": 10000.0,
        "margin_free": 9000.0,
        "margin_level_pct": 500.0,
        "proposed_position_size_lots": 0.05,
        "risk_per_trade_pct": 0.25,
        "risk_score": 0.2,
    }
    data.update(overrides)
    return RiskAssessment(**data)


def _candles(count=6):
    return [
        {
            "timestamp": datetime(2026, 1, 1, 0, i).isoformat(),
            "open": 1.1000 + i * 0.0002,
            "high": 1.1020 + i * 0.0002,
            "low": 1.0980 + i * 0.0002,
            "close": 1.1000 + i * 0.0002,
            "volume": 1000,
        }
        for i in range(count)
    ]


class _FakeAuditor:
    def __init__(self, verdict):
        self.verdict = verdict

    def evaluate(self, proposal, snapshot, risk):
        status = GateStatus.PASS if self.verdict == Verdict.ACCEPT else GateStatus.FAIL
        return CASDecision(
            decision_id=f"dec-{proposal.proposal_id}",
            proposal_ref=proposal.proposal_id,
            symbol=proposal.symbol,
            verdict=self.verdict,
            gate_results=[GateResult(gate_name="fake", status=status, reason=self.verdict.value)],
            overriding_gate=None if self.verdict == Verdict.ACCEPT else "fake",
        )

    def build_order(self, proposal, risk, decision_ref):
        return _order(volume=risk.proposed_position_size_lots)


def test_evidence_store_hash_chain_detects_tamper_and_tail_deletion(tmp_path):
    path = tmp_path / "evidence.jsonl"
    store = EvidenceStore(path, run_id="run-1")
    receipt = store.append(_packet("trace-a"), source="test")
    store.append(_packet("trace-a", PacketStatus.ACCEPTED), source="test")

    assert receipt.event_seq == 0
    assert store.verify_chain()
    assert len(store.load_trace("trace-a")) == 2

    tampered = path.read_text(encoding="utf-8").replace("test packet", "changed packet", 1)
    path.write_text(tampered, encoding="utf-8")
    assert not store.verify_chain()

    path2 = tmp_path / "deleted.jsonl"
    store2 = EvidenceStore(path2, run_id="run-2")
    store2.append(_packet("trace-b"), source="test")
    store2.append(_packet("trace-b", PacketStatus.ACCEPTED), source="test")
    first_line = path2.read_text(encoding="utf-8").splitlines()[0]
    path2.write_text(first_line + "\n", encoding="utf-8")
    assert not store2.verify_chain()


def test_backtest_emits_suppressed_and_accepted_packet_sequences(tmp_path):
    suppress_store = EvidenceStore(tmp_path / "suppress.jsonl", run_id="suppress")
    suppress_engine = BacktestEngine(auditor=_FakeAuditor(Verdict.SUPPRESS), evidence_store=suppress_store)
    suppress_engine._generate_proposal = lambda symbol, candles, horizon, atr: _proposal(
        proposal_id=f"suppress-{len(candles)}"
    )
    suppressed = suppress_engine.run(_candles(), warmup_bars=1)
    suppress_statuses = [p.status for p in suppress_engine.packets]
    assert suppressed.suppressed_trades > 0
    assert PacketStatus.PROPOSED in suppress_statuses
    assert PacketStatus.SUPPRESSED in suppress_statuses
    assert suppressed.evidence_chain_verified

    accept_store = EvidenceStore(tmp_path / "accept.jsonl", run_id="accept")
    accept_engine = BacktestEngine(auditor=_FakeAuditor(Verdict.ACCEPT), evidence_store=accept_store)
    accept_engine._generate_proposal = lambda symbol, candles, horizon, atr: _proposal(
        proposal_id=f"accept-{len(candles)}"
    )
    accepted = accept_engine.run(_candles(), warmup_bars=1)
    accept_statuses = [p.status for p in accept_engine.packets]
    assert accepted.total_trades > 0
    assert PacketStatus.ACCEPTED in accept_statuses
    assert PacketStatus.EXECUTED in accept_statuses
    assert {PacketStatus.CLOSED_WIN, PacketStatus.CLOSED_LOSS} & set(accept_statuses)
    assert accepted.evidence_chain_verified


def _ok_signal(model, direction=Direction.LONG):
    return ForecastSignal(
        model=model,
        model_version="test",
        status=ForecastSignalStatus.OK,
        direction=direction,
        confidence=0.75,
        expected_move_pips=20.0,
        interval_low=1.095,
        interval_high=1.110,
    )


def test_forecast_harness_suppresses_single_model_and_passes_agreement(monkeypatch):
    harness = ForecastHarness(require_primary_models=False)
    monkeypatch.setattr(harness.technical, "predict", lambda *args, **kwargs: _proposal())
    monkeypatch.setattr(harness.timegpt, "predict", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        harness,
        "_chronos_signal",
        lambda symbol: ForecastSignal(
            model="chronos",
            status=ForecastSignalStatus.UNAVAILABLE,
            error="stubbed unavailable",
        ),
    )
    monkeypatch.setattr(
        harness,
        "_timesfm_signal",
        lambda symbol: ForecastSignal(
            model="timesfm",
            status=ForecastSignalStatus.UNAVAILABLE,
            error="stubbed unavailable",
        ),
    )
    proposal, report = harness.propose("EUR/USD", _candles(30))
    assert proposal is None
    assert report.verdict == ForecastHarnessVerdict.SUPPRESS
    assert "single_model_only" in report.reason_codes

    monkeypatch.setattr(harness, "_chronos_signal", lambda symbol: _ok_signal("chronos"))
    proposal, report = harness.propose("EUR/USD", _candles(30))
    assert proposal is not None
    assert report.verdict == ForecastHarnessVerdict.PASS


def test_forecast_harness_disagreement_and_drift_live_lock(monkeypatch):
    harness = ForecastHarness()
    monkeypatch.setattr(harness.technical, "predict", lambda *args, **kwargs: _proposal(Direction.LONG))
    monkeypatch.setattr(harness.timegpt, "predict", lambda *args, **kwargs: None)
    monkeypatch.setattr(harness, "_chronos_signal", lambda symbol: _ok_signal("chronos", Direction.SHORT))
    monkeypatch.setattr(
        harness,
        "_timesfm_signal",
        lambda symbol: ForecastSignal(model="timesfm", status=ForecastSignalStatus.UNAVAILABLE),
    )
    proposal, report = harness.propose("EUR/USD", _candles(30))
    assert proposal is None
    assert report.verdict == ForecastHarnessVerdict.SUPPRESS
    assert "model_disagreement" in report.reason_codes

    drift = ForecastHarness(drift_breach=True)
    monkeypatch.setattr(drift.technical, "predict", lambda *args, **kwargs: _proposal(Direction.LONG))
    monkeypatch.setattr(drift.timegpt, "predict", lambda *args, **kwargs: None)
    monkeypatch.setattr(drift, "_chronos_signal", lambda symbol: _ok_signal("chronos", Direction.LONG))
    monkeypatch.setattr(
        drift,
        "_timesfm_signal",
        lambda symbol: ForecastSignal(model="timesfm", status=ForecastSignalStatus.UNAVAILABLE),
    )
    proposal, report = drift.propose("EUR/USD", _candles(30))
    assert proposal is None
    assert report.verdict == ForecastHarnessVerdict.LIVE_LOCKED
    assert "model_drift_breach" in report.reason_codes


def test_macro_gate_uses_15_minute_blackout_and_locks_on_shock():
    gate = MacroGate()
    assert gate.evaluate(datetime(2026, 6, 5, 12, 14)).status == GateStatus.PASS
    inside = gate.evaluate(datetime(2026, 6, 5, 12, 16))
    assert inside.status == GateStatus.FAIL
    assert "NFP" in inside.reason

    event = MacroEventState(
        event_id="shock",
        event_type=MacroEventType.CPI,
        currency="USD",
        scheduled_at_utc=datetime(2026, 6, 10, 12, 30),
        expected=1.0,
        actual=3.0,
        shock_threshold=1.0,
    )
    shock_gate = MacroGate(provider=StaticMacroCalendarProvider([event]))
    result = shock_gate.evaluate(datetime(2026, 6, 10, 12, 30))
    assert result.status == GateStatus.FAIL
    assert "LIVE_LOCKED" in result.reason
    assert result.evidence["lock_reason"] == LiveLockReason.MACRO_SHOCK.value


def test_live_lock_unlock_requires_receipts_and_position_override(tmp_path):
    controller = LiveLockController(tmp_path / "lock.json", tmp_path / "unlock.jsonl")
    controller.lock([LiveLockReason.MANUAL_OPERATOR_LOCK], details={"why": "test"})
    assert controller.is_locked()

    with pytest.raises(ValueError, match="closed positions"):
        controller.unlock(
            operator_id="operator",
            signed_reason="signed reason",
            evidence_receipt_hash="receipt-hash",
            risk_snapshot={"risk": "fresh"},
            next_session_id="session-2",
            open_positions_count=1,
        )

    receipt = controller.unlock(
        operator_id="operator",
        signed_reason="signed reason",
        evidence_receipt_hash="receipt-hash",
        risk_snapshot={"risk": "fresh"},
        next_session_id="session-2",
        open_positions_count=1,
        override_open_positions=True,
    )
    assert receipt.receipt_hash
    assert not controller.is_locked()


def test_broker_guards_mt4_mailbox_sim_reject_and_live_legal(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "mt4_enabled", True)
    monkeypatch.setattr(config, "mt4_mailbox_dir", str(tmp_path / "mt4"))
    monkeypatch.setattr(config, "paper_trading", True)
    monkeypatch.setattr(config, "live_mode", False)
    mt4 = MT4EABridge()
    no_heartbeat = mt4.execute_order(_order())
    assert no_heartbeat.status == OrderStatus.REJECTED
    assert "fresh EA heartbeat" in no_heartbeat.error_message
    _write_mt4_heartbeat(tmp_path / "mt4")
    outcome = mt4.execute_order(_order())
    assert outcome.status == OrderStatus.PENDING
    assert outcome.broker_mode == BrokerMode.PAPER_MT4
    assert (tmp_path / "mt4" / "orders.jsonl").exists()

    sim = SimulatedBrokerBridge()
    reject = sim.execute_order(_order(volume=0.001))
    assert reject.status == OrderStatus.REJECTED
    assert "min lot" in reject.error_message

    assert SimulatedBrokerBridge(market_open=False).execute_order(_order()).status == OrderStatus.REJECTED
    assert SimulatedBrokerBridge(disabled_symbols={"EUR/USD"}).execute_order(_order()).status == OrderStatus.REJECTED
    assert SimulatedBrokerBridge(current_spread_pips=9.0, max_spread_pips=5.0).execute_order(_order()).status == OrderStatus.REJECTED
    assert SimulatedBrokerBridge(simulated_slippage_pips=4.0, max_slippage_pips=3.0).execute_order(_order()).lock_reason == BrokerLockReason.FILL_PRICE_MISMATCH

    margin_sim = SimulatedBrokerBridge()
    margin_sim._equity = 1.0
    assert margin_sim.execute_order(_order()).lock_reason == BrokerLockReason.MARGIN_REJECT

    tight_stop = BrokerOrderRequest(
        order_id="ord-tight",
        decision_ref="dec-001",
        symbol="EUR/USD",
        direction=Direction.LONG,
        volume=0.05,
        price=1.1000,
        stop_loss=1.0999,
        take_profit=1.1100,
    )
    assert SimulatedBrokerBridge(min_stop_distance_pips=5.0).execute_order(tight_stop).status == OrderStatus.REJECTED

    partial = SimulatedBrokerBridge(max_lot=0.02).execute_order(_order(volume=0.05))
    assert partial.status == OrderStatus.PARTIAL

    monkeypatch.setattr(config, "live_mode", True)
    monkeypatch.setattr(config, "paper_trading", False)
    monkeypatch.setattr(config, "personal_account_ack", False)
    monkeypatch.setattr(config, "no_pooled_capital_ack", False)
    with pytest.raises(PermissionError, match="CURRENTLY NOT LICENSED"):
        get_bridge()


def test_post_trade_disconnect_with_open_position_locks_and_emits_evidence(tmp_path):
    class Broker:
        def is_connected(self):
            return False

        def get_open_positions(self):
            return [{"ticket": 123, "symbol": "EUR/USD", "volume": 0.05, "profit": -3.0}]

        def get_account_info(self):
            return {"margin_level": 450.0}

    store = EvidenceStore(tmp_path / "post.jsonl", run_id="post")
    controller = LiveLockController(tmp_path / "lock.json", tmp_path / "unlock.jsonl")
    harness = PostTradeHarness(Broker(), evidence_store=store, live_lock_controller=controller)
    outcome = OrderOutcome(order_ref="ord-001", broker_ticket=123, status=OrderStatus.EXECUTED)

    observation = harness.observe("trace-post", expected_order=_order(), outcome=outcome)
    assert observation.lock_reason == LiveLockReason.BROKER_DISCONNECT_OPEN_TRADE.value
    assert controller.is_locked()
    assert store.verify_chain()
    assert store.load_trace("trace-post")[0].status == PacketStatus.LIVE_LOCKED


def test_post_trade_evidence_write_failure_locks(tmp_path):
    class Broker:
        def is_connected(self):
            return True

        def get_open_positions(self):
            return []

        def get_account_info(self):
            return {"margin_level": 450.0}

    class FailingStore:
        def append(self, packet, source="runtime"):
            raise OSError("disk full")

    controller = LiveLockController(tmp_path / "lock.json", tmp_path / "unlock.jsonl")
    harness = PostTradeHarness(Broker(), evidence_store=FailingStore(), live_lock_controller=controller)
    harness.observe("trace-write-fail", expected_order=_order())
    state = controller.current()
    assert state is not None
    assert LiveLockReason.EVIDENCE_WRITE_FAILURE in state.reasons


def test_sweep_auto_provider_boundary_and_receipts(tmp_path):
    auto_internal = ProfitSweeper(
        ProfitSweepPolicy(mode=SweepMode.AUTO, min_profit_threshold=10.0)
    )
    blocked = auto_internal.execute_sweep(account_balance=10000.0, realized_profit=100.0)
    assert blocked.status == SweepStatus.BLOCKED
    assert "NOT LICENSED" in blocked.block_reason

    sweep_lock = LiveLockController(tmp_path / "sweep-lock.json", tmp_path / "sweep-unlock.jsonl")
    provider = ProfitSweeper(
        ProfitSweepPolicy(
            mode=SweepMode.AUTO,
            min_profit_threshold=10.0,
            transfer_boundary=TransferBoundary.PROVIDER_API,
            destination_allowlisted=True,
            require_human_confirmation=False,
        ),
        live_lock_controller=sweep_lock,
    )
    blocked_provider = provider.execute_sweep(account_balance=10000.0, realized_profit=100.0)
    assert blocked_provider.status == SweepStatus.BLOCKED
    assert "Payout automation" in blocked_provider.block_reason
    assert "NOT LICENSED" in blocked_provider.block_reason
    assert blocked_provider.live_lock_triggered is False
    assert not sweep_lock.is_locked()

    receipt_provider = ProfitSweeper(
        ProfitSweepPolicy(
            mode=SweepMode.AUTO,
            min_profit_threshold=10.0,
            transfer_boundary=TransferBoundary.PROVIDER_API,
            destination_allowlisted=True,
            require_human_confirmation=False,
        )
    )
    blocked_with_receipts = receipt_provider.execute_sweep(
        account_balance=10000.0,
        realized_profit=100.0,
        idempotency_key="idem-1",
        receipt_hash="receipt-1",
    )
    assert blocked_with_receipts.status == SweepStatus.BLOCKED
    assert blocked_with_receipts.transfer_boundary == TransferBoundary.PROVIDER_API
    assert blocked_with_receipts.receipt_hash is None
    assert "debit/card/bank movement" in blocked_with_receipts.block_reason
    assert receipt_provider.total_swept == 0.0


def test_sweep_auto_executes_when_owner_authorized(monkeypatch):
    from cas_forex import broker_reality
    from cas_forex.config import config as forex_config

    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(forex_config, "owner_enable_payout_automation", True)
    monkeypatch.setattr(forex_config, "payment_provider", "wise")
    monkeypatch.setattr(forex_config, "payment_api_key", "key")
    monkeypatch.setattr(forex_config, "payout_destination_id", "dest-1")
    monkeypatch.setattr(forex_config, "payout_destination_allowlisted", True)

    sweeper = ProfitSweeper(
        ProfitSweepPolicy(
            mode=SweepMode.AUTO,
            min_profit_threshold=10.0,
            transfer_boundary=TransferBoundary.PROVIDER_API,
            destination_allowlisted=True,
            require_human_confirmation=False,
        )
    )
    tx = sweeper.execute_sweep(
        account_balance=10000.0,
        realized_profit=100.0,
        idempotency_key="idem-2",
        receipt_hash="receipt-2",
    )
    assert tx.status == SweepStatus.EXECUTED
    assert tx.savings_amount == 40.0
    assert tx.tax_reserve_amount == 10.0
    assert tx.receipt_hash == "receipt-2"
