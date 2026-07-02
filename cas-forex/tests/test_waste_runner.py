"""Tests for the WASTE-loop runner — proves it is fail-closed and paper-safe.

The runner ticks ``WasteLoop`` and stamps the live heartbeat per stage. These
tests use fakes (a controllable ``test`` gate via monkeypatch, an injected
``strategize`` and ``dispatch`` sink) to prove the load-bearing invariants:

  * a tick records a heartbeat stage (the indicator pulses with the real stage);
  * a NON-PASS test => NO execution + the tick ends at ``no_trade``;
  * a PASS => ``edge_authorization.authorize`` is called AND dispatch is called;
  * daily-CAP-reached => no candidate => no new trades that day;
  * the runner CANNOT execute without a PASS (fail-closed, by construction).
"""

from __future__ import annotations

import pytest

from cas_forex import (
    auto_halt,
    broker_reality,
    broker_truth_monitor,
    edge_authorization,
    live_enable_control,
    live_order_dry_run_review,
    live_pilot,
    live_recovery,
    loop_heartbeat,
    waste_runner,
)
from cas_forex.ai_objective import ProfitObjective
from cas_forex.edge_gate import CandidateSetup as GateCandidateSetup
from cas_forex.edge_gate import EdgeTestDecision, _now_iso, mint_token
from cas_forex.live_order_dry_run import LiveOrderDryRunAuditLog, STATUS_PASS
from cas_forex.broker.mt5_bridge import SimulatedBrokerBridge
from cas_forex.order_attempt_audit import OrderAttemptAuditStore
from cas_forex.order_dispatch import STATUS_BLOCKED_COMPOUND_ADD_REVIEW
from cas_forex.schemas.order import BrokerMode, OrderOutcome, OrderStatus
from cas_forex.waste_cycle_audit import WasteCycleAuditStore
from cas_forex.waste_loop import CandidateSetup


def _setup() -> CandidateSetup:
    return CandidateSetup(
        symbol="EUR/USD",
        timeframe="H1",
        direction="LONG",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        signal_strength=0.8,
        regime="trend",
        decision_ref="dref-test-1",
    )


def _with_cas_meta(setup: CandidateSetup, *, broker_truth: bool = True) -> CandidateSetup:
    setattr(
        setup,
        "market_state_meta",
        {
            "source": "MT5TerminalMarketDataConnector",
            "live_feed": broker_truth,
            "broker_grade_market_truth": broker_truth,
            "cas_feature_map": {
                "report_kind": "cas_forex_waste_cas_feature_map",
                "selected_profile": "blend",
                "selected_rpm_action": "ROUTE",
                "selected_cjt_region": "active",
                "selected_is_lacuna": False,
                "cell_reliability": 0.9,
                "lacunarity_gap_fraction": 0.1,
                "rpm_route_count": 3,
            },
        },
    )
    return setup


def _pass_decision(setup: CandidateSetup) -> EdgeTestDecision:
    """A genuine PASS whose token is a valid HMAC over the gate setup, so
    ``edge_authorization.authorize`` accepts it."""
    from cas_forex.waste_runner import _to_gate_setup

    gate_setup = _to_gate_setup(setup)
    evaluated_at = _now_iso()
    token = mint_token(gate_setup, evaluated_at)
    return EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.72,
        null_p95=0.01,
        threshold=0.65,
        edge_token=token,
        evaluated_at=evaluated_at,
        reason="edge confirmed (test fixture)",
    )


def _authorize_add_edge(decision_ref: str, setup: CandidateSetup) -> None:
    evaluated_at = _now_iso()
    gate_setup = GateCandidateSetup(
        symbol=setup.symbol,
        timeframe=setup.timeframe,
        direction=setup.direction,
        entry=1.1060,
        stop_loss=setup.stop_loss,
        take_profit=setup.take_profit,
        signal_strength=setup.signal_strength,
        regime=setup.regime,
        decision_ref=decision_ref,
    )
    decision = EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.73,
        null_p95=0.10,
        threshold=0.65,
        edge_token=mint_token(gate_setup, evaluated_at),
        evaluated_at=evaluated_at,
        reason="fresh add edge PASS",
    )
    edge_authorization.authorize(decision_ref, decision, gate_setup)


def _authorized_live_cfg():
    from types import SimpleNamespace

    return SimpleNamespace(
        owner_enable_live_trading=True,
        live_trading_licensed=True,
        mt5_login=12345,
        mt5_password="pw",
        mt5_server="HugosWay-Live",
        live_mode=True,
        prefer_mt5=True,
        mt5_path=None,
        personal_account_ack=True,
        no_pooled_capital_ack=True,
        account_type="personal",
        selected_broker_id="hugosway",
        broker_name="HUGOSWAY",
        max_total_exposure_lots=0.5,
        max_open_positions=5,
        max_weekly_drawdown_pct=5.0,
    )


def _patch_global_config(monkeypatch, cfg) -> None:
    from cas_forex.config import config as global_config

    for name, value in vars(cfg).items():
        monkeypatch.setattr(global_config, name, value, raising=False)


def _patch_compound_add_dry_run_live_gates(monkeypatch) -> None:
    monkeypatch.setattr(auto_halt, "is_auto_halt_active", lambda: False)
    monkeypatch.setattr(broker_truth_monitor, "broker_truth_monitor_ready_for_live", lambda: True)
    monkeypatch.setattr(broker_reality, "is_broker_reality_accepted", lambda broker_id=None: True)
    monkeypatch.setattr(live_pilot, "is_live_pilot_available_for_live", lambda: True)
    monkeypatch.setattr(live_pilot, "require_live_pilot_intent", lambda *args, **kwargs: {})
    monkeypatch.setattr(live_pilot, "record_live_pilot_dispatch", lambda **kwargs: {})
    monkeypatch.setattr(live_recovery, "is_live_recovery_clear_for_live", lambda: True)
    monkeypatch.setattr(live_order_dry_run_review, "is_live_order_dry_run_review_clear_for_live", lambda: True)


class _FakeRealBridge:
    def __init__(self, order_id: str) -> None:
        self.order_id = order_id
        self.calls: list = []

    def will_execute_real_order(self) -> bool:
        return True

    def execute_order(self, order):
        self.calls.append(order)
        return OrderOutcome(
            order_ref=self.order_id,
            broker_ticket=999001,
            status=OrderStatus.EXECUTED,
            filled_price=float(getattr(order, "price", 0.0) or 1.1060),
            broker_mode=BrokerMode.LIVE_MT5,
            is_real_broker=True,
        )


def _reconciled_position_report() -> dict:
    return {
        "report_kind": "cas_forex_terminal_position_reconciliation_report",
        "created_at": _now_iso(),
        "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS",
        "summary": {
            "unmatched_open_position_count": 0,
            "pending_receipt_count": 0,
            "receipt_mismatch_count": 0,
        },
        "reconciled_open_positions": [
            {
                "match_method": "broker_ticket",
                "cas_position": {
                    "symbol": "EUR/USD",
                    "direction": "LONG",
                    "lots": 0.01,
                    "open_price": 1.1000,
                    "current_price": 1.1060,
                    "stop_loss": 1.0950,
                    "take_profit": 1.1100,
                    "broker_ticket": "555",
                    "decision_ref": "dref-test-1",
                },
                "terminal_position": {
                    "symbol": "EUR/USD",
                    "direction": "LONG",
                    "lots": 0.01,
                    "open_price": 1.1000,
                    "current_price": 1.1060,
                    "stop_loss": 1.0950,
                    "take_profit": 1.1100,
                    "broker_ticket": "555",
                },
            }
        ],
    }


def _no_trade_decision() -> EdgeTestDecision:
    return EdgeTestDecision(
        status="NO_TRADE_NULL_FAILED",
        measured_win_prob=0.40,
        null_p95=0.02,
        threshold=0.65,
        edge_token=None,
        evaluated_at="2026-06-29T00:00:00+00:00",
        reason="did not beat null",
    )


def _runner(**kwargs) -> waste_runner.WasteRunner:
    kwargs.setdefault("watch_fn", lambda: {"report_kind": "offline_runner_test_state"})
    kwargs.setdefault("analyze_fn", lambda state: {"report_kind": "offline_runner_test_analysis"})
    return waste_runner.WasteRunner(**kwargs)


@pytest.fixture(autouse=True)
def _clean_state():
    loop_heartbeat.reset()
    edge_authorization.reset()
    yield
    loop_heartbeat.reset()
    edge_authorization.reset()


@pytest.fixture
def _isolated_live_enable_overrides(tmp_path):
    path = tmp_path / "live-enable-overrides.json"
    live_enable_control.set_live_enable_override_store_for_tests(path)
    live_enable_control.clear_live_enable_overrides()
    yield
    live_enable_control.clear_live_enable_overrides()
    live_enable_control.set_live_enable_override_store_for_tests(
        live_enable_control.DEFAULT_OVERRIDE_PATH
    )


# ---------------------------------------------------------------------------
# 1. A tick records a heartbeat stage.
# ---------------------------------------------------------------------------
def test_tick_records_heartbeat_stage():
    runner = _runner(strategize_fn=lambda s, a: None)
    runner.tick_once()
    snap = loop_heartbeat.snapshot()
    # The indicator is live and pulsing with a real stage (default => no_trade).
    assert snap["running"] is True
    assert snap["stage"] in waste_runner.loop_heartbeat.VALID_STAGES
    assert snap["stage"] == "no_trade"


# ---------------------------------------------------------------------------
# 2. A NON-PASS test => NO execution + stage no_trade.
# ---------------------------------------------------------------------------
def test_non_pass_test_means_no_execution(monkeypatch):
    dispatched: list = []
    authorized: list = []

    def fake_dispatch(**kwargs):
        dispatched.append(kwargs)
        return {"status": "EXECUTED"}

    monkeypatch.setattr(
        edge_authorization, "authorize", lambda *a, **k: authorized.append((a, k))
    )

    runner = _runner(
        strategize_fn=lambda s, a: _setup(),
        dispatch_fn=fake_dispatch,
    )
    # This test proves the FAIL-CLOSED path, so the owner's paper-learning dial
    # (default ON since 2026-07-01) is explicitly OFF here.
    runner.control.adjust("paper_learning_trades", 0)
    # Force the gate to a non-PASS verdict.
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _no_trade_decision()
    )

    result = runner.tick_once()

    assert result["decision"] == "NO_TRADE"
    assert dispatched == []        # the bridge was never touched
    assert authorized == []        # nothing was authorized
    assert loop_heartbeat.snapshot()["stage"] == "no_trade"


# ---------------------------------------------------------------------------
# 3. A PASS => authorize + dispatch are both called.
# ---------------------------------------------------------------------------
def test_pass_authorizes_and_dispatches(monkeypatch):
    dispatched: list = []

    def fake_dispatch(**kwargs):
        dispatched.append(kwargs)
        return {"status": "EXECUTED", "broker_ticket": 555, "fill_price": 1.1000}

    setup = _setup()
    runner = _runner(
        strategize_fn=lambda s, a: setup,
        dispatch_fn=fake_dispatch,
    )
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _pass_decision(setup)
    )

    result = runner.tick_once()

    assert result["decision"] == "EXECUTE"
    # dispatch was called exactly once, on the PASS branch.
    assert len(dispatched) == 1
    assert dispatched[0]["setup"].decision_ref == "dref-test-1"
    assert isinstance(dispatched[0]["token"], str) and dispatched[0]["token"]
    # The PASS was registered for the dispatch chokepoint to verify (fail-closed twice).
    assert edge_authorization.is_required("dref-test-1") is True
    assert loop_heartbeat.snapshot()["stage"] == "execute"  # tick settled on execute


def test_pass_default_paper_sink_records_order_attempt(tmp_path, monkeypatch):
    order_store = OrderAttemptAuditStore(
        tmp_path / "order-attempts.json",
        tmp_path / "order-attempts-audit.jsonl",
    )
    cycle_store = WasteCycleAuditStore(
        tmp_path / "waste-runner-state.json",
        tmp_path / "waste-runner-audit.jsonl",
    )
    setup = _setup()
    monkeypatch.setattr(
        waste_runner,
        "_default_waste_paper_bridge_factory",
        lambda: SimulatedBrokerBridge(min_stop_distance_pips=0.0),
    )
    monkeypatch.setattr(waste_runner, "position_size", lambda **kwargs: 0.01)
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _pass_decision(setup)
    )

    runner = _runner(
        strategize_fn=lambda s, a: setup,
        audit_store=cycle_store,
        order_attempt_audit_store=order_store,
    )

    result = runner.tick_once()

    assert result["decision"] == "EXECUTE"
    assert result["execute_result"].status == "BROKER_EXECUTED"
    assert result["execute_result"].executed is True
    latest_attempt = order_store.latest_attempt()
    assert latest_attempt["source"] == "waste_runner"
    assert latest_attempt["mode"] == "PAPER"
    assert latest_attempt["is_real_attempt"] is False
    assert latest_attempt["order_id"] == "waste-dref-test-1"
    assert latest_attempt["decision_ref"] == "dref-test-1"
    assert latest_attempt["dispatched_to_bridge"] is True
    assert latest_attempt["executed"] is True
    assert latest_attempt["outcome"]["broker_mode"] == "SIMULATED"
    assert latest_attempt["outcome"]["broker_ticket"] is not None
    latest_cycle = cycle_store.build_status()["latest_cycle"]
    assert latest_cycle["execute_result"]["audit_status"] == "ATTEMPT_RECORDED"
    assert latest_cycle["execute_result"]["outcome"]["broker_ticket"] == latest_attempt["outcome"]["broker_ticket"]


def test_waste_pass_execute_reaches_owner_authorized_live_bridge(
    tmp_path, monkeypatch, _isolated_live_enable_overrides
):
    _patch_compound_add_dry_run_live_gates(monkeypatch)
    static_cfg = _authorized_live_cfg()
    static_cfg.live_mode = False
    static_cfg.owner_enable_live_trading = False
    static_cfg.live_trading_licensed = False
    static_cfg.personal_account_ack = False
    static_cfg.no_pooled_capital_ack = False
    _patch_global_config(monkeypatch, static_cfg)
    live_enable_control.set_live_enable_overrides(
        personal_account_ack=True,
        no_pooled_capital_ack=True,
        live_mode=True,
        prefer_mt5=True,
        owner_enable_live_trading=True,
        live_trading_licensed=True,
    )
    order_store = OrderAttemptAuditStore(
        tmp_path / "waste-live-order-attempts.json",
        tmp_path / "waste-live-order-attempts-audit.jsonl",
    )
    setup = _setup()
    bridge = _FakeRealBridge("waste-dref-test-1")
    monkeypatch.setattr(waste_runner, "position_size", lambda **kwargs: 0.01)
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _pass_decision(setup)
    )

    runner = _runner(
        strategize_fn=lambda s, a: setup,
        bridge_factory=lambda: bridge,
        order_attempt_audit_store=order_store,
    )

    result = runner.tick_once()

    assert result["decision"] == "EXECUTE"
    assert result["stage_trace"] == ["watch", "analyze", "strategize", "test", "execute"]
    assert len(bridge.calls) == 1
    assert bridge.calls[0].order_id == "waste-dref-test-1"
    assert bridge.calls[0].decision_ref == setup.decision_ref
    execute_result = result["execute_result"]
    assert execute_result.status == "BROKER_EXECUTED"
    assert execute_result.dispatched_to_bridge is True
    assert execute_result.outcome is not None
    assert execute_result.outcome.is_real_broker is True
    latest_attempt = order_store.latest_attempt()
    assert latest_attempt["source"] == "waste_runner"
    assert latest_attempt["mode"] == "LIVE"
    assert latest_attempt["is_real_attempt"] is True
    assert latest_attempt["dispatched_to_bridge"] is True


# ---------------------------------------------------------------------------
# 4. Daily-CAP-reached => no new trades that day.
# ---------------------------------------------------------------------------
def test_daily_cap_reached_blocks_new_trades(monkeypatch):
    dispatched: list = []

    def fake_dispatch(**kwargs):
        dispatched.append(kwargs)
        return {"status": "EXECUTED"}

    setup = _setup()
    objective = ProfitObjective(daily_max_target=3500.0)
    runner = _runner(
        strategize_fn=lambda s, a: setup,           # would propose a candidate...
        dispatch_fn=fake_dispatch,
        objective=objective,
        today_realized_fn=lambda: 4000.0,           # ...but the cap is already hit.
    )
    # Even a PASS-able gate must not be reached: strategize returns None first.
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _pass_decision(setup)
    )

    result = runner.tick_once()

    assert result["decision"] == "NO_TRADE"
    assert dispatched == []
    assert loop_heartbeat.snapshot()["stage"] == "no_trade"


# ---------------------------------------------------------------------------
# 5. Fail-closed by construction: the runner cannot execute without a PASS even
#    when strategize hands a full candidate and the gate underpowers/refuses.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "status",
    ["NO_TRADE_NULL_FAILED", "NO_TRADE_UNDERPOWERED", "NO_TRADE_INSUFFICIENT_BARS"],
)
def test_cannot_execute_without_pass(monkeypatch, status):
    dispatched: list = []

    setup = _setup()
    runner = _runner(
        strategize_fn=lambda s, a: setup,
        dispatch_fn=lambda **k: dispatched.append(k),
    )
    # Fail-closed contract under test: learning dial explicitly OFF.
    runner.control.adjust("paper_learning_trades", 0)
    refused = EdgeTestDecision(
        status=status,
        measured_win_prob=0.0,
        null_p95=0.0,
        threshold=0.65,
        edge_token=None,
        evaluated_at="2026-06-29T00:00:00+00:00",
        reason=status,
    )
    monkeypatch.setattr(waste_runner, "evaluate_candidate", lambda *a, **k: refused)

    result = runner.tick_once()

    assert result["decision"] == "NO_TRADE"
    assert dispatched == []
    assert edge_authorization.is_required("dref-test-1") is False


# ---------------------------------------------------------------------------
# 6. A PASS with an EMPTY token is NOT a license to execute (token is the key).
# ---------------------------------------------------------------------------
def test_pass_with_empty_token_does_not_execute(monkeypatch):
    dispatched: list = []
    setup = _setup()
    runner = _runner(
        strategize_fn=lambda s, a: setup,
        dispatch_fn=lambda **k: dispatched.append(k),
    )
    # Fail-closed contract under test: learning dial explicitly OFF.
    runner.control.adjust("paper_learning_trades", 0)
    bad_pass = EdgeTestDecision(
        status="PASS",
        measured_win_prob=0.9,
        null_p95=0.0,
        threshold=0.65,
        edge_token="",          # empty token => not a real authorization
        evaluated_at="2026-06-29T00:00:00+00:00",
        reason="malformed PASS",
    )
    monkeypatch.setattr(waste_runner, "evaluate_candidate", lambda *a, **k: bad_pass)

    result = runner.tick_once()

    assert result["decision"] == "NO_TRADE"
    assert dispatched == []


def test_tick_persists_durable_cycle_audit(tmp_path, monkeypatch):
    store = WasteCycleAuditStore(
        tmp_path / "waste-runner-state.json",
        tmp_path / "waste-runner-audit.jsonl",
    )
    setup = _setup()
    runner = _runner(
        strategize_fn=lambda s, a: setup,
        audit_store=store,
    )
    # Fail-closed contract under test: learning dial explicitly OFF.
    runner.control.adjust("paper_learning_trades", 0)
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _no_trade_decision()
    )

    result = runner.tick_once()
    status = store.build_status()
    latest = status["latest_cycle"]

    assert result["decision"] == "NO_TRADE"
    assert status["has_latest_cycle"] is True
    assert latest["decision"] == "NO_TRADE"
    assert latest["candidate"]["symbol"] == "EUR/USD"
    assert latest["candidate"]["direction"] == "LONG"
    assert latest["edge"]["status"] == "NO_TRADE_NULL_FAILED"
    assert latest["edge"]["has_edge_token"] is False
    assert latest["running"] is False
    assert (tmp_path / "waste-runner-audit.jsonl").read_text(encoding="utf-8")


def test_runner_status_surfaces_durable_latest_cycle(tmp_path, monkeypatch):
    store = WasteCycleAuditStore(
        tmp_path / "waste-runner-state.json",
        tmp_path / "waste-runner-audit.jsonl",
    )
    setup = _setup()
    runner = _runner(
        strategize_fn=lambda s, a: setup,
        audit_store=store,
    )
    # Fail-closed contract under test: learning dial explicitly OFF.
    runner.control.adjust("paper_learning_trades", 0)
    monkeypatch.setattr(
        waste_runner, "evaluate_candidate", lambda *a, **k: _no_trade_decision()
    )

    runner.tick_once()
    status = runner.status()

    assert status["durable_cycle"]["decision"] == "NO_TRADE"
    assert status["durable_cycle"]["candidate"]["decision_ref"] == "dref-test-1"
    assert status["durable_cycle_status"]["report_kind"] == "cas_forex_waste_cycle_audit"


def test_default_runner_persists_real_candle_watch_source_evidence(tmp_path, monkeypatch):
    from cas_forex import directional_intelligence, waste_market_data

    calls: list[str] = []
    setup = _setup()
    setup.symbol = "NAS100"
    setup.timeframe = "D1"
    setattr(setup, "entry_pairs", [{"signal_strength": 0.8, "ret": 0.01, "cost_ret": 0.0001}])
    setattr(
        setup,
        "directional_hypothesis",
        {
            "symbol": "NAS100",
            "timeframe": "D1",
            "action": "LONG",
            "direction": "LONG",
            "confidence": 0.74,
            "profile": "trend_follow",
        },
    )
    setattr(
        setup,
        "market_state_meta",
        {
            "source": "MT5TerminalMarketDataConnector",
            "broker_grade_market_truth": True,
            "selected_directional_profile": "trend_follow",
        },
    )

    def fake_market_state():
        calls.append("watch")
        return {
            "report_kind": "cas_forex_waste_market_state",
            "symbol": "NAS100",
            "timeframe": "D1",
            "source": "MT5TerminalMarketDataConnector",
            "feed_label": "read-only MT5 broker-terminal candles and tick spread",
            "fallback_used": False,
            "broker_grade_market_truth": True,
            "read_only_market_data": True,
            "candles": [{"open": 1, "high": 2, "low": 1, "close": 2}] * 40,
            "entry_pairs": [{"signal_strength": 0.8, "ret": 0.01, "cost_ret": 0.0001}],
            "entry_pair_report": {"entry_pair_count": 1},
            "selected_directional_profile": "trend_follow",
            "strategy_firewall": {
                "candidate_allowed": True,
                "firewall_status": "ALLOW",
                "lead_id": "index_tsmom_126",
            },
            "directional_hypothesis_tuning": {
                "status": "SELECTED",
                "selected_profile": "trend_follow",
                "no_lookahead": True,
                "validation_pairs_holdout": True,
                "selection_window_count": 12,
                "validation_window_count": 10,
            },
            "cas_feature_map": {
                "selected_profile": "trend_follow",
                "selected_rpm_action": "ROUTE",
                "selected_cjt_region": "active",
                "selected_is_lacuna": False,
                "cell_reliability": 0.9,
            },
            "execution_costs": {"edge_cost_pips": 2.0, "spread_pips": 1.5},
            "connector_attempts": [{"connector": "MT5TerminalMarketDataConnector", "symbol": "NAS100", "status": "CANDLES_FETCHED", "candle_count": 40}],
            "waste_market_scan": {
                "status": "WASTE_MARKET_SCAN_NO_PASS",
                "attempt_count": 2,
                "selected_symbol": "NAS100",
                "selected_timeframe": "D1",
                "selected_edge_status": "NO_TRADE_NULL_FAILED",
                "selected_edge_has_token": False,
                "edge_authorization_registered": False,
                "broker_execution_touched": False,
                "money_moved": False,
                "attempts": [
                    {
                        "symbol": "US30",
                        "timeframe": "D1",
                        "edge_status": "NO_CANDIDATE",
                        "edge_has_token": False,
                        "candles_count": 40,
                        "entry_pair_count": 0,
                    },
                    {
                        "symbol": "NAS100",
                        "timeframe": "D1",
                        "edge_status": "NO_TRADE_NULL_FAILED",
                        "edge_has_token": False,
                        "candidate_direction": "LONG",
                        "broker_grade_market_truth": True,
                        "fallback_used": False,
                        "candles_count": 40,
                        "entry_pair_count": 1,
                    },
                ],
            },
            "market_data_claim_boundary": "read-only broker-grade market data",
        }

    monkeypatch.setattr(waste_market_data, "build_waste_market_state_scan", fake_market_state)
    monkeypatch.setattr(
        directional_intelligence,
        "analyze_market_state",
        lambda state: {
            "confidence": 0.74,
            "reason": "fixture directional read",
            "hypothesis": {
                "symbol": "NAS100",
                "timeframe": "D1",
                "action": "LONG",
                "direction": "LONG",
                "confidence": 0.74,
                "profile": "trend_follow",
            },
            "strategy_firewall": state["strategy_firewall"],
            "hypothesis_tuning": state["directional_hypothesis_tuning"],
            "cas_feature_map": state["cas_feature_map"],
        },
    )
    monkeypatch.setattr(
        directional_intelligence,
        "strategize_market_state",
        lambda state, analysis: setup,
    )
    monkeypatch.setattr(waste_runner, "evaluate_candidate", lambda *a, **k: _no_trade_decision())
    store = WasteCycleAuditStore(
        tmp_path / "waste-runner-state.json",
        tmp_path / "waste-runner-audit.jsonl",
    )
    runner = waste_runner.WasteRunner(audit_store=store)
    # Fail-closed contract under test: learning dial explicitly OFF.
    runner.control.adjust("paper_learning_trades", 0)

    result = runner.tick_once()
    latest = store.build_status()["latest_cycle"]

    assert calls == ["watch"]
    assert result["decision"] == "NO_TRADE"
    assert latest["watch_state"]["source"] == "MT5TerminalMarketDataConnector"
    assert latest["watch_state"]["broker_grade_market_truth"] is True
    assert latest["watch_state"]["read_only_market_data"] is True
    assert latest["watch_state"]["candles_count"] == 40
    assert latest["watch_state"]["entry_pair_count"] == 1
    assert latest["watch_state"]["waste_market_scan"]["status"] == "WASTE_MARKET_SCAN_NO_PASS"
    assert latest["watch_state"]["waste_market_scan"]["attempt_count"] == 2
    assert latest["watch_state"]["waste_market_scan"]["selected_symbol"] == "NAS100"
    assert latest["watch_state"]["waste_market_scan"]["edge_authorization_registered"] is False
    assert latest["watch_state"]["waste_market_scan"]["broker_execution_touched"] is False
    assert latest["watch_state"]["waste_market_scan"]["money_moved"] is False
    assert latest["watch_state"]["directional_hypothesis_tuning"]["no_lookahead"] is True
    assert latest["watch_state"]["strategy_firewall"]["candidate_allowed"] is True
    assert latest["analysis"]["hypothesis"]["direction"] == "LONG"
    assert latest["candidate"]["market_state_meta"]["broker_grade_market_truth"] is True
    assert latest["edge"]["status"] == "NO_TRADE_NULL_FAILED"


def test_scheduled_runner_default_watch_uses_cached_probe_snapshot(monkeypatch):
    from cas_forex import waste_market_data, waste_real_candle_probe

    monkeypatch.setenv("CAS_FOREX_WASTE_SCHEDULED_SNAPSHOT_WATCH", "1")
    monkeypatch.setattr(
        waste_market_data,
        "build_waste_market_state_scan",
        lambda: (_ for _ in ()).throw(AssertionError("full scan should not run")),
    )
    monkeypatch.setattr(
        waste_real_candle_probe,
        "latest_waste_real_candle_probe",
        lambda: {
            "report_kind": "cas_forex_waste_real_candle_probe",
            "status": "EDGE_BLOCKED",
            "generated_at": "2026-07-01T00:00:00+00:00",
            "symbol": "NAS100",
            "timeframe": "D1",
            "source": "MT5TerminalMarketDataConnector",
            "fallback_used": False,
            "broker_grade_market_truth": True,
            "candles_count": 40,
            "entry_pair_count": 40,
            "broker_touched": False,
            "edge_authorization_registered": False,
            "candidate": {
                "symbol": "NAS100",
                "timeframe": "D1",
                "direction": "LONG",
                "entry_pair_count": 40,
                "directional_hypothesis": {
                    "symbol": "NAS100",
                    "timeframe": "D1",
                    "direction": "LONG",
                    "profile": "blend",
                    "confidence": 0.55,
                },
                "market_state_meta": {
                    "broker_grade_market_truth": True,
                    "cas_feature_map": {
                        "selected_profile": "blend",
                        "selected_rpm_action": "ROUTE",
                        "selected_cjt_region": "active",
                        "selected_is_lacuna": False,
                        "cell_reliability": 0.75,
                    },
                },
            },
            "analysis": {
                "hypothesis": {"direction": "LONG", "profile": "blend"},
                "hypothesis_tuning": {
                    "status": "SELECTED",
                    "selected_profile": "blend",
                    "no_lookahead": True,
                    "validation_pairs_holdout": True,
                },
            },
            "market_state": {
                "symbol": "NAS100",
                "timeframe": "D1",
                "source": "MT5TerminalMarketDataConnector",
                "broker_grade_market_truth": True,
                "fallback_used": False,
                "read_only_market_data": True,
                "entry_pair_report": {"entry_pair_count": 40},
                "strategy_firewall": {"candidate_allowed": True, "firewall_status": "ALLOW"},
            },
            "edge": {"status": "NO_TRADE_NULL_FAILED", "has_edge_token": False},
        },
    )

    state = waste_runner._default_watch()
    analysis = waste_runner._default_analyze(state)

    assert state["report_kind"] == "cas_forex_waste_scheduled_snapshot_watch"
    assert state["cached_snapshot_only"] is True
    assert state["candles"] == []
    assert state["entry_pairs"] == []
    assert state["directional_hypothesis"]["direction"] == "LONG"
    assert state["waste_market_scan"]["status"] == "WASTE_SCHEDULED_SNAPSHOT_ONLY"
    assert analysis["confidence"] == 0.0
    assert waste_runner._default_strategize(state, analysis) is None


def test_scheduled_runner_default_watch_fails_closed_without_probe(monkeypatch):
    from cas_forex import waste_real_candle_probe

    monkeypatch.setenv("CAS_FOREX_WASTE_SCHEDULED_SNAPSHOT_WATCH", "1")
    monkeypatch.setattr(
        waste_real_candle_probe,
        "latest_waste_real_candle_probe",
        lambda: {
            "report_kind": "cas_forex_waste_real_candle_probe",
            "status": "NO_PROBE_RECORDED",
            "broker_touched": False,
            "edge_authorization_registered": False,
        },
    )

    state = waste_runner._default_watch()

    assert state["report_kind"] == "cas_forex_waste_scheduled_snapshot_watch"
    assert state["status"] == "WASTE_SCHEDULED_SNAPSHOT_UNAVAILABLE"
    assert state["cached_snapshot_only"] is True
    assert state["candles"] == []
    assert state["entry_pairs"] == []
    assert state["waste_market_scan"]["status"] == "WASTE_SCHEDULED_SNAPSHOT_UNAVAILABLE"


def test_compound_holds_without_exact_add_gates_even_when_cas_green():
    setup = _with_cas_meta(_setup())
    runner = _runner()

    decision = runner._manage_stage(
        setup=setup,
        execute_result={"status": "EXECUTED", "filled_price": 1.1060},
        control={"max_compound_units": 4},
    )

    assert decision.action == "HOLD"
    assert decision.add_units == 0
    assert "exact add risk gate has not passed" in decision.reason


def test_compound_add_decision_requires_broker_truth_profit_risk_and_fresh_pass(tmp_path):
    setup = _with_cas_meta(_setup())
    runner = _runner(compound_add_dry_run_audit=LiveOrderDryRunAuditLog(tmp_path / "compound-add-audit.jsonl"))

    decision = runner._manage_stage(
        setup=setup,
        execute_result={"status": "EXECUTED", "filled_price": 1.1060},
        control={"max_compound_units": 4},
        current_units=1,
        add_risk_gate_passed=True,
        compound_edge=_pass_decision(setup),
    )

    assert decision.action == "ADD"
    assert decision.add_units >= 1
    assert "compound CAS review" in decision.reason
    assert "gated dispatch" in decision.reason
    assert decision.add_dry_run is not None
    assert decision.add_dry_run["status"] != STATUS_PASS
    assert decision.add_dry_run["broker_touched"] is False


def test_compound_add_manage_stage_emits_passing_dry_run_from_reconciled_position(tmp_path, monkeypatch):
    _patch_compound_add_dry_run_live_gates(monkeypatch)
    setup = _with_cas_meta(_setup())
    runner = _runner()
    add_decision_ref = "dref-test-1:compound-add:2"
    _authorize_add_edge(add_decision_ref, setup)
    audit = LiveOrderDryRunAuditLog(tmp_path / "compound-add-audit.jsonl")

    decision = runner._manage_stage(
        setup=setup,
        lots=0.01,
        execute_result={"status": "EXECUTED", "broker_ticket": 555, "filled_price": 1.1000, "current_price": 1.1060},
        control={"max_compound_units": 4},
        current_units=1,
        add_risk_gate_passed=True,
        compound_edge=_pass_decision(setup),
        terminal_position_reconciliation=_reconciled_position_report(),
        add_decision_ref=add_decision_ref,
        config=_authorized_live_cfg(),
        compound_add_dry_run_audit=audit,
    )

    assert decision.action == "ADD"
    assert decision.add_dry_run is not None
    assert decision.add_dry_run["status"] == STATUS_PASS
    assert decision.add_dry_run["broker_touched"] is False
    assert decision.add_dry_run["waste_manage_stage"]["source"] == "waste_runner.manage_stage"
    assert decision.add_dry_run["compound_context"]["broker_grade_market_truth"] is True
    latest = audit.latest()
    assert latest["status"] == STATUS_PASS
    assert latest["payload"]["waste_manage_stage"]["position_evidence_source"] == (
        "terminal_position_reconciliation.reconciled_open_positions"
    )


def test_waste_compound_add_dry_run_reaches_dashboard_owner_review_surface(tmp_path, monkeypatch):
    _patch_compound_add_dry_run_live_gates(monkeypatch)

    from fastapi.testclient import TestClient

    from api import data as api_data
    from api.server import app
    from cas_forex import compound_add_order_dry_run_review as review_module

    audit_path = tmp_path / "compound-add-audit.jsonl"
    review_state_path = tmp_path / "compound-add-review.json"
    monkeypatch.setattr(api_data, "COMPOUND_ADD_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(review_module, "DEFAULT_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(review_module, "DEFAULT_STATE_PATH", review_state_path)
    monkeypatch.setattr(
        review_module,
        "_latest_broker_truth",
        lambda: {
            "report_kind": "cas_forex_broker_truth_monitor",
            "generated_at": _now_iso(),
            "overall_status": "BROKER_TRUTH_READY",
            "mt5_connected": True,
            "mt5_is_demo": False,
            "mt5_open_position_count": 1,
            "terminal_unmatched_open_position_count": 0,
            "terminal_pending_receipt_count": 0,
            "terminal_receipt_mismatch_count": 0,
        },
    )

    setup = _with_cas_meta(_setup())
    runner = _runner()
    add_decision_ref = "dref-test-1:compound-add:2"
    _authorize_add_edge(add_decision_ref, setup)
    audit = LiveOrderDryRunAuditLog(audit_path)

    decision = runner._manage_stage(
        setup=setup,
        lots=0.01,
        execute_result={"status": "EXECUTED", "broker_ticket": 555, "filled_price": 1.1000, "current_price": 1.1060},
        control={"max_compound_units": 4},
        current_units=1,
        add_risk_gate_passed=True,
        compound_edge=_pass_decision(setup),
        terminal_position_reconciliation=_reconciled_position_report(),
        add_decision_ref=add_decision_ref,
        config=_authorized_live_cfg(),
        compound_add_dry_run_audit=audit,
    )
    assert decision.add_dry_run is not None
    assert decision.add_dry_run["status"] == STATUS_PASS
    assert decision.add_dry_run["broker_touched"] is False

    response = TestClient(app).get("/api/forex/dashboard")
    assert response.status_code == 200
    body = response.json()
    latest = body["compoundAddOrderDryRun"]
    review = body["compoundAddOrderDryRunReview"]

    assert latest["report_kind"] == "cas_forex_compound_add_order_dry_run_latest"
    assert latest["status"] == STATUS_PASS
    assert latest["broker_touched"] is False
    assert latest["latest_audit"]["order_id"] == decision.add_dry_run["order_id"]
    assert latest["latest_audit"]["payload"]["waste_manage_stage"]["source"] == "waste_runner.manage_stage"
    assert review["report_kind"] == "cas_forex_compound_add_order_dry_run_review"
    assert review["owner_review_status"] == "OPEN"
    assert review["evidence_ready_for_owner_accept"] is True
    assert review["compound_add_dry_run_review_clear_for_dispatch"] is False
    assert review["latest_compound_add_summary"]["decision_ref"] == add_decision_ref
    assert review["latest_compound_add_summary"]["broker_touched"] is False
    assert "does not place add orders" in review["claim_boundary"]


def test_waste_compound_add_dispatch_handoff_blocks_without_owner_accept(tmp_path, monkeypatch):
    _patch_compound_add_dry_run_live_gates(monkeypatch)

    from cas_forex import compound_add_order_dry_run_review as review_module

    audit_path = tmp_path / "compound-add-audit.jsonl"
    monkeypatch.setattr(review_module, "DEFAULT_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(review_module, "DEFAULT_STATE_PATH", tmp_path / "compound-add-review.json")
    setup = _with_cas_meta(_setup())
    add_decision_ref = "dref-test-1:compound-add:2"
    _authorize_add_edge(add_decision_ref, setup)
    bridge = _FakeRealBridge("waste-add-dref-test-1-2")
    order_store = OrderAttemptAuditStore(
        tmp_path / "compound-add-blocked-order-attempts.json",
        tmp_path / "compound-add-blocked-order-attempts-audit.jsonl",
    )

    decision = _runner(bridge_factory=lambda: bridge)._manage_stage(
        setup=setup,
        lots=0.01,
        execute_result={"status": "EXECUTED", "broker_ticket": 555, "filled_price": 1.1000, "current_price": 1.1060},
        control={"max_compound_units": 4},
        current_units=1,
        add_risk_gate_passed=True,
        compound_edge=_pass_decision(setup),
        terminal_position_reconciliation=_reconciled_position_report(),
        add_decision_ref=add_decision_ref,
        config=_authorized_live_cfg(),
        compound_add_dry_run_audit=LiveOrderDryRunAuditLog(audit_path),
        compound_add_dispatch_audit_store=order_store,
        attempt_compound_add_dispatch=True,
    )

    assert decision.action == "ADD"
    assert decision.add_dry_run is not None
    assert decision.add_dry_run["status"] == STATUS_PASS
    assert decision.add_dispatch_intent is not None
    assert decision.add_dispatch_intent["ai_action"] == "COMPOUND_ADD"
    assert decision.add_dispatch_result is not None
    assert decision.add_dispatch_result["status"] == STATUS_BLOCKED_COMPOUND_ADD_REVIEW
    assert decision.add_dispatch_result["dispatched_to_bridge"] is False
    assert decision.add_dispatch_result["broker_touched"] is False
    assert bridge.calls == []


def test_waste_compound_add_dispatch_handoff_reaches_bridge_after_owner_accept(tmp_path, monkeypatch):
    _patch_compound_add_dry_run_live_gates(monkeypatch)

    from cas_forex import compound_add_order_dry_run_review as review_module

    audit_path = tmp_path / "compound-add-audit.jsonl"
    review_state_path = tmp_path / "compound-add-review.json"
    review_audit_path = tmp_path / "compound-add-review-audit.jsonl"
    broker_truth = {
        "report_kind": "cas_forex_broker_truth_monitor",
        "generated_at": _now_iso(),
        "overall_status": "BROKER_TRUTH_READY",
        "mt5_connected": True,
        "mt5_is_demo": False,
        "mt5_open_position_count": 1,
        "terminal_unmatched_open_position_count": 0,
        "terminal_pending_receipt_count": 0,
        "terminal_receipt_mismatch_count": 0,
    }
    monkeypatch.setattr(review_module, "DEFAULT_DRY_RUN_AUDIT_PATH", audit_path)
    monkeypatch.setattr(review_module, "DEFAULT_STATE_PATH", review_state_path)
    monkeypatch.setattr(review_module, "DEFAULT_AUDIT_PATH", review_audit_path)
    monkeypatch.setattr(review_module, "_latest_broker_truth", lambda: broker_truth)

    setup = _with_cas_meta(_setup())
    add_decision_ref = "dref-test-1:compound-add:2"
    _authorize_add_edge(add_decision_ref, setup)
    audit = LiveOrderDryRunAuditLog(audit_path)
    dry_decision = _runner()._manage_stage(
        setup=setup,
        lots=0.01,
        execute_result={"status": "EXECUTED", "broker_ticket": 555, "filled_price": 1.1000, "current_price": 1.1060},
        control={"max_compound_units": 4},
        current_units=1,
        add_risk_gate_passed=True,
        compound_edge=_pass_decision(setup),
        terminal_position_reconciliation=_reconciled_position_report(),
        add_decision_ref=add_decision_ref,
        config=_authorized_live_cfg(),
        compound_add_dry_run_audit=audit,
    )
    assert dry_decision.add_dry_run is not None
    accepted = review_module.accept_compound_add_order_dry_run_review(
        notes="Owner accepted exact WASTE compound add handoff in test.",
        confirm_owner_accept=True,
        dry_run_audit=dry_decision.add_dry_run["audit"],
        broker_truth_report=broker_truth,
        state_path=review_state_path,
        audit_path=review_audit_path,
    )
    assert accepted["compound_add_dry_run_review_clear_for_dispatch"] is True

    bridge = _FakeRealBridge(dry_decision.add_dry_run["order_id"])
    order_store = OrderAttemptAuditStore(
        tmp_path / "compound-add-handoff-order-attempts.json",
        tmp_path / "compound-add-handoff-order-attempts-audit.jsonl",
    )
    handoff = waste_runner.dispatch_compound_add_from_dry_run(
        dry_decision.add_dry_run,
        bridge=bridge,
        config=_authorized_live_cfg(),
        audit_store=order_store,
    )

    assert handoff["status"] == "BROKER_EXECUTED"
    assert handoff["broker_touched"] is True
    assert handoff["dispatched_to_bridge"] is True
    assert len(bridge.calls) == 1
    assert bridge.calls[0].order_id == dry_decision.add_dry_run["order_id"]
    assert bridge.calls[0].decision_ref == add_decision_ref


def test_compound_holds_without_broker_grade_market_truth():
    setup = _with_cas_meta(_setup(), broker_truth=False)
    runner = _runner()

    decision = runner._manage_stage(
        setup=setup,
        execute_result={"status": "EXECUTED", "filled_price": 1.1060},
        control={"max_compound_units": 4},
        current_units=1,
        add_risk_gate_passed=True,
        compound_edge=_pass_decision(setup),
    )

    assert decision.action == "HOLD"
    assert "broker-grade market truth is required" in decision.reason


# ---------------------------------------------------------------------------
# Paper LEARNING trades (owner decision 2026-07-01)
# ---------------------------------------------------------------------------
def test_learning_execute_with_empty_token_skips_edge_registration(monkeypatch):
    """A token-less learning dispatch must NEVER register an edge authorization
    (that would fabricate a PASS). It dispatches through the legacy paper path."""
    dispatched = {}

    def fake_dispatch(*, setup, lots, token):
        dispatched["setup"] = setup
        dispatched["lots"] = lots
        dispatched["token"] = token
        return {"status": "BROKER_CONFIRMED"}

    def exploding_authorize(*args, **kwargs):
        raise AssertionError("edge_authorization.authorize must not run for learning trades")

    monkeypatch.setattr(edge_authorization, "authorize", exploding_authorize)
    runner = _runner(dispatch_fn=fake_dispatch)

    setup = _setup()
    result = runner._execute_stage(setup, 0.05, "")

    assert result == {"status": "BROKER_CONFIRMED"}
    assert dispatched["token"] == ""
    assert dispatched["lots"] == 0.05


def test_paper_learning_allowed_only_in_paper_mode(monkeypatch):
    runner = _runner()
    runner.control.adjust("paper_learning_trades", 1)

    monkeypatch.setattr(waste_runner, "_effective_mode", lambda: "PAPER")
    assert runner._paper_learning_allowed() is True

    monkeypatch.setattr(waste_runner, "_effective_mode", lambda: "LIVE")
    assert runner._paper_learning_allowed() is False


def test_paper_learning_dial_off_disables_learning_trades(monkeypatch):
    runner = _runner()
    monkeypatch.setattr(waste_runner, "_effective_mode", lambda: "PAPER")
    runner.control.adjust("paper_learning_trades", 0)
    assert runner._paper_learning_allowed() is False
    runner.control.adjust("paper_learning_trades", 1)
    assert runner._paper_learning_allowed() is True
