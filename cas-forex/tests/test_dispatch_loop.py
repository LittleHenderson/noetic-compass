"""Tests for the owner-controlled paper dispatch loop scheduler.

The loop runs the gated dispatch cycle on a timer in a background thread. These
tests monkeypatch the (heavy, real) cycle with a fast fake so they exercise the
start/stop/status state machine without doing real dispatch work or sleeping for
the full interval.
"""

import json
import threading
import time
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from cas_forex import dispatch_loop
from cas_forex.time_utils import utc_now


class _FakeReport:
    mode = "PAPER"
    intent_count = 2
    executed_count = 1
    blocked_count = 0
    rejected_count = 1


class _FakeCycle:
    dispatch_report = _FakeReport()


@pytest.fixture(autouse=True)
def _clean_loop(monkeypatch):
    import cas_forex.agent_dispatch as ad
    import cas_forex.ai_hedge_management_cycle as management_cycle
    import cas_forex.broker_control as broker_control
    import cas_forex.mt5_demo_learning_sync as mt5_learning_sync

    monkeypatch.setattr(ad, "collect_route_intents", lambda *a, **k: [])
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", lambda **kw: _FakeCycle())
    monkeypatch.setattr(ad, "write_agent_dispatch_cycle_report", lambda cycle: {})
    monkeypatch.setattr(broker_control, "select_bridge", lambda config=None: object())
    monkeypatch.setattr(broker_control, "select_paper_learning_bridge", lambda config=None: object())
    monkeypatch.setattr(
        broker_control,
        "select_durable_simulator_handoff_bridge",
        lambda config=None: SimpleNamespace(get_open_positions=lambda: []),
    )
    monkeypatch.setattr(
        management_cycle,
        "run_ai_hedge_management_cycle",
        lambda **kw: {
            "status": "WATCHING_NO_BROKER_POSITIONS",
            "detail": "No broker positions in test.",
            "attempted_action_count": 0,
            "terminal_effect_count": 0,
            "broker_touched": False,
        },
    )
    monkeypatch.setattr(
        mt5_learning_sync,
        "sync_mt5_demo_learning",
        lambda **kwargs: {
            "status": "MT5_DEMO_LEARNING_SYNCED",
            "generated_at": utc_now().isoformat(),
            "history_record_count": 0,
            "bound_trade_count": 0,
        },
    )
    dispatch_loop.stop_loop()
    dispatch_loop._state.cycles_run = 0
    dispatch_loop._state.cycles_idle = 0
    dispatch_loop._state.symbols = []
    dispatch_loop._state.sessions = []
    dispatch_loop._state.position_scope = ""
    dispatch_loop._state.last_summary = ""
    dispatch_loop._state.last_error = ""
    dispatch_loop._state.last_collected_intent_count = 0
    dispatch_loop._state.last_filtered_intent_count = 0
    dispatch_loop._state.entry_dispatch_in_progress = False
    dispatch_loop._state.last_entry_progress_summary = ""
    dispatch_loop._state.last_available_intent_symbols = []
    dispatch_loop._state.last_filtered_out_symbols = []
    dispatch_loop._state.last_target_warning = ""
    dispatch_loop._state.last_symbol_targeting = {}
    dispatch_loop._state.last_entry_risk_feasibility = {}
    dispatch_loop._state.last_entry_timeframe_scan = {}
    dispatch_loop._state.last_supervisor_event = ""
    dispatch_loop._state.last_blocking_detail = ""
    dispatch_loop._state.management_cycles_run = 0
    dispatch_loop._state.last_management_status = ""
    dispatch_loop._state.last_management_detail = ""
    dispatch_loop._state.last_management_draft_action_count = 0
    dispatch_loop._state.last_management_action_count = 0
    dispatch_loop._state.last_management_terminal_effect_count = 0
    dispatch_loop._state.last_management_broker_touched = False
    dispatch_loop._state.last_operator_discretionary_status = ""
    dispatch_loop._state.last_operator_discretionary_option_count = 0
    dispatch_loop._state.last_operator_discretionary_position_count = 0
    dispatch_loop._state.last_operator_discretionary_blocked_option_count = 0
    dispatch_loop._state.last_operator_discretionary_model_failure_policy = ""
    dispatch_loop._state.last_scale_in_status = ""
    dispatch_loop._state.last_scale_in_action_count = 0
    dispatch_loop._state.last_scale_in_parent_candidate_count = 0
    dispatch_loop._state.last_scale_in_blocker_count = 0
    dispatch_loop._state.last_scale_in_blockers = []
    dispatch_loop._state.last_scale_in_max_compound_units = 0
    dispatch_loop._state.last_scale_in_minimum_profit_r = None
    dispatch_loop._state.last_management_account_position_count = 0
    dispatch_loop._state.last_management_excluded_position_count = 0
    dispatch_loop._state.last_management_primary_position_count = 0
    dispatch_loop._state.last_management_simulator_handoff_position_count = 0
    dispatch_loop._state.last_management_sources = []
    dispatch_loop._state.last_primary_position_tickets = []
    dispatch_loop._state.last_mt5_demo_learning_sync_status = ""
    dispatch_loop._state.last_mt5_demo_learning_sync_at = ""
    dispatch_loop._state.last_mt5_demo_learning_sync_started_at = ""
    dispatch_loop._state.last_mt5_demo_learning_sync_duration_seconds = None
    dispatch_loop._state.mt5_demo_learning_sync_in_progress = False
    dispatch_loop._state.last_mt5_demo_learning_sync_error = ""
    dispatch_loop._state.last_mt5_demo_learning_history_count = 0
    dispatch_loop._state.last_mt5_demo_learning_bound_trade_count = 0
    dispatch_loop._state.last_mt5_demo_learning_group_learning_ready = None
    dispatch_loop._state.last_mt5_demo_learning_overall_sample_ready = None
    dispatch_loop._state.last_mt5_demo_learning_ready_group_count = 0
    dispatch_loop._state.last_mt5_demo_learning_min_samples_per_group = 0
    dispatch_loop._state.last_operator_trade_edge_report = {}
    dispatch_loop._state.last_operator_position_edge_report = {}
    dispatch_loop._state._mt5_learning_bridge_active = False
    dispatch_loop._state._mt5_learning_position_signature = ()
    dispatch_loop._state._mt5_learning_last_attempt_monotonic = 0.0
    dispatch_loop._state._mt5_learning_last_success_monotonic = 0.0
    dispatch_loop._state._mt5_learning_sync_pending_after_dispatch = False
    dispatch_loop._state.last_effective_mode = ""
    dispatch_loop._state.last_execution_lane = ""
    dispatch_loop._state.last_bridge_class = ""
    dispatch_loop._state.last_bridge_selection_status = ""
    dispatch_loop._state.last_bridge_selection_detail = ""
    yield
    dispatch_loop.stop_loop()
    dispatch_loop.reset_control_state_path_for_testing()
    dispatch_loop.reset_supervisor_state_path_for_testing()


def _wait_for(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_loop_starts_runs_a_cycle_and_stops():
    assert dispatch_loop.loop_status()["running"] is False
    started = dispatch_loop.start_loop(10)
    assert started["running"] is True
    # The loop runs a cycle immediately, before waiting the interval.
    assert _wait_for(lambda: dispatch_loop.loop_status()["cycles_run"] >= 1)
    status = dispatch_loop.loop_status()
    assert "mode=PAPER" in (status["last_summary"] or "")
    assert status["last_error"] is None
    stopped = dispatch_loop.stop_loop()
    assert stopped["running"] is False


def test_fast_status_reports_running_thread_without_taking_loop_lock(tmp_path):
    dispatch_loop.set_control_state_path_for_testing(tmp_path / "dispatch-control.json")
    dispatch_loop._state.interval = 7
    dispatch_loop._state.position_scope = "ALL_ACCOUNT"
    dispatch_loop._state.last_effective_mode = "PAPER_FALLBACK"
    dispatch_loop._state.last_execution_lane = "PAPER"
    dispatch_loop._state.last_summary = "lane=PAPER mode=PAPER_FALLBACK"
    dispatch_loop._state.last_collected_intent_count = 3
    dispatch_loop._state.last_filtered_intent_count = 1
    dispatch_loop._state.entry_dispatch_in_progress = True
    dispatch_loop._state.last_entry_progress_summary = "entry dispatch in progress"
    dispatch_loop._state.last_entry_risk_feasibility = {
        "candidate_count": 2,
        "operator_candidate_count": 1,
    }
    dispatch_loop._state.last_entry_timeframe_scan = {
        "active_timeframes": ["M1", "M5", "M15", "H1"],
        "selected_timeframe": "M5",
        "entry_lane": "MICRO_SCALP",
    }
    dispatch_loop._state.thread = SimpleNamespace(is_alive=lambda: True)

    status = dispatch_loop.loop_status_fast()

    assert status["status_source"] == "FAST_IN_MEMORY_SHELL"
    assert status["status"] == "RUNNING"
    assert status["running"] is True
    assert status["execution_active"] is True
    assert status["mode"] == "PAPER_FALLBACK"
    assert status["requested_mode"] == "LIVE"
    assert status["position_scope"] == "ALL_ACCOUNT"
    assert status["interval_seconds"] == 7
    assert status["last_collected_intent_count"] == 3
    assert status["last_filtered_intent_count"] == 1
    assert status["entry_dispatch_in_progress"] is True
    assert status["last_entry_progress_summary"] == "entry dispatch in progress"
    assert status["last_entry_risk_candidate_count"] == 2
    assert status["last_entry_risk_operator_candidate_count"] == 1
    assert status["active_entry_timeframes"] == ["M1", "M5", "M15", "H1"]
    assert status["last_entry_timeframe"] == "M5"
    assert status["last_entry_lane"] == "MICRO_SCALP"

    dispatch_loop._state.thread = None


def test_start_is_idempotent():
    dispatch_loop.start_loop(15)
    again = dispatch_loop.start_loop(15)
    # Still one running loop (no second thread); interval reflected.
    assert again["running"] is True
    assert again["interval_seconds"] == 15
    dispatch_loop.stop_loop()


def test_owner_position_scope_is_explicit_and_persisted(tmp_path):
    dispatch_loop.set_control_state_path_for_testing(tmp_path / "dispatch-control.json")

    started = dispatch_loop.start_loop(15, position_scope="ALL_ACCOUNT")

    assert started["position_scope"] == "ALL_ACCOUNT"
    assert started["position_scope_label"] == "Every open position on the account"
    persisted = dispatch_loop._load_control_state()
    assert persisted["position_scope"] == "ALL_ACCOUNT"


def test_supervisor_blocks_duplicate_dispatch_loop_worker(tmp_path):
    from cas_forex.dispatch_loop_supervisor import DispatchLoopSupervisorStore

    state_path = tmp_path / "dispatch-loop-supervisor.json"
    audit_path = tmp_path / "dispatch-loop-supervisor-audit.jsonl"
    dispatch_loop.set_supervisor_state_path_for_testing(state_path, audit_path)
    foreign = DispatchLoopSupervisorStore(state_path, audit_path, lease_seconds=60)
    foreign.acquire(owner_id="foreign-api-worker", interval_seconds=10, mode="PAPER")

    status = dispatch_loop.start_loop(10)

    assert status["running"] is True
    assert status["local_running"] is False
    assert status["dispatch_loop_active_elsewhere"] is True
    assert status["supervisor"]["owned_by_this_process"] is False
    assert status["last_supervisor_event"] == "active in another API worker"
    assert status["last_error"] is None
    assert "Dispatch loop lease is held" in (status["last_local_error"] or "")
    assert dispatch_loop._state.thread is None or not dispatch_loop._state.thread.is_alive()


def test_interval_is_clamped():
    s = dispatch_loop.start_loop(0)  # below MIN -> clamped up to MIN (1)
    assert s["interval_seconds"] == dispatch_loop.MIN_INTERVAL_SECONDS
    dispatch_loop.stop_loop()
    s2 = dispatch_loop.start_loop(9_999_999)  # above MAX -> clamped down to MAX
    assert s2["interval_seconds"] == dispatch_loop.MAX_INTERVAL_SECONDS
    dispatch_loop.stop_loop()


def test_owner_can_set_sub_60s_interval():
    # The owner drives: anything from 1s up is honored, including below the old 60s/10s floors.
    for want in (1, 3, 5, 30):
        s = dispatch_loop.start_loop(want)
        assert s["interval_seconds"] == want
        dispatch_loop.stop_loop()


def test_interval_change_while_running_is_applied_live():
    dispatch_loop.start_loop(45)
    assert dispatch_loop.loop_status()["interval_seconds"] == 45
    # Re-calling start while running updates the interval without spawning a 2nd loop.
    again = dispatch_loop.start_loop(3)
    assert again["running"] is True
    assert again["interval_seconds"] == 3
    dispatch_loop.stop_loop()


def test_active_sessions_by_hour():
    import datetime as _dt

    def at(h):
        return _dt.datetime(2026, 6, 24, h, 0, tzinfo=_dt.timezone.utc)

    assert dispatch_loop.active_sessions(at(3)) == {"Asian"}
    assert dispatch_loop.active_sessions(at(9)) == {"London"}
    assert dispatch_loop.active_sessions(at(14)) == {"London", "New York"}  # overlap
    assert dispatch_loop.active_sessions(at(18)) == {"New York"}
    assert dispatch_loop.active_sessions(at(23)) == {"Asian"}


def test_symbol_targeting_filters_dispatched_intents(monkeypatch):
    import cas_forex.agent_dispatch as ad

    class _I:
        def __init__(self, symbol):
            self.symbol = symbol

    captured = {}

    def _capture_cycle(**kw):
        captured["intents"] = list(kw.get("intents") or [])
        return _FakeCycle()

    monkeypatch.setattr(ad, "collect_route_intents", lambda *a, **k: [_I("EUR/USD"), _I("US30"), _I("NAS100")])
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", _capture_cycle)

    dispatch_loop.start_loop(10, symbols=["US30"])
    assert _wait_for(lambda: "intents" in captured)
    assert [i.symbol for i in captured["intents"]] == ["US30"]
    dispatch_loop.stop_loop()


def test_symbol_targeting_reports_when_all_current_intents_are_filtered(monkeypatch):
    import cas_forex.agent_dispatch as ad

    class _I:
        def __init__(self, symbol):
            self.symbol = symbol

    captured = {}

    def _capture_cycle(**kw):
        captured["intents"] = list(kw.get("intents") or [])
        return _FakeCycle()

    monkeypatch.setattr(ad, "collect_route_intents", lambda *a, **k: [_I("AUD/CAD")])
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", _capture_cycle)

    dispatch_loop.start_loop(10, symbols=["NAS100", "US30"])
    assert _wait_for(lambda: "intents" in captured)
    status = dispatch_loop.loop_status()
    assert captured["intents"] == []
    assert status["last_collected_intent_count"] == 1
    assert status["last_filtered_intent_count"] == 0
    assert status["last_available_intent_symbols"] == ["AUD/CAD"]
    assert status["last_filtered_out_symbols"] == ["AUD/CAD"]
    assert "effective entry symbols filtered out every current route intent" in status["last_target_warning"]
    assert "warning=effective entry symbols filtered out every current route intent" in status["last_summary"]
    dispatch_loop.stop_loop()


def test_entry_symbol_targeting_removes_saturated_markets_before_scanning():
    resolved = dispatch_loop.resolve_entry_symbol_targeting(
        ai_symbols=["NAS100", "US30", "EUR/USD"],
        scheduler_symbols=[],
        position_symbol_counts={"NAS100": 1, "US30": 1},
        max_positions_per_symbol=1,
    )

    assert resolved["status"] == "ENTRY_SYMBOLS_READY"
    assert resolved["saturated_symbols"] == ["NAS100", "US30"]
    assert resolved["eligible_symbols"] == ["EUR/USD"]


def test_entry_symbol_targeting_reports_split_brain_no_overlap():
    resolved = dispatch_loop.resolve_entry_symbol_targeting(
        ai_symbols=["EUR/USD", "USD/JPY"],
        scheduler_symbols=["NAS100", "US30"],
        position_symbol_counts={},
        max_positions_per_symbol=1,
    )

    assert resolved["status"] == "NO_SYMBOL_OVERLAP"
    assert resolved["effective_symbols"] == []
    assert resolved["eligible_symbols"] == []


def test_session_targeting_idles_outside_target_sessions(monkeypatch):
    import cas_forex.agent_dispatch as ad

    called = {"dispatch": 0}

    def _count(**kw):
        called["dispatch"] += 1
        return _FakeCycle()

    monkeypatch.setattr(ad, "collect_route_intents", lambda *a, **k: [])
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", _count)
    # Pretend it's the Asian session, but the owner targets London only.
    monkeypatch.setattr(dispatch_loop, "active_sessions", lambda now=None: {"Asian"})

    dispatch_loop.start_loop(10, sessions=["London"])
    assert _wait_for(lambda: dispatch_loop.loop_status()["cycles_idle"] >= 1)
    assert called["dispatch"] == 0  # never dispatched off-session
    assert "entries idle outside target sessions" in (dispatch_loop.loop_status()["last_summary"] or "")
    dispatch_loop.stop_loop()


def test_management_and_entry_dispatch_share_one_bridge(monkeypatch):
    import cas_forex.agent_dispatch as ad
    import cas_forex.ai_hedge_management_cycle as management_cycle
    import cas_forex.broker_control as broker_control

    shared_bridge = object()
    captured: dict[str, Any] = {}

    monkeypatch.setattr(broker_control, "select_paper_learning_bridge", lambda config=None: shared_bridge)

    def manage(**kwargs):
        captured["management_bridge"] = kwargs.get("bridge")
        return {
            "status": "WATCHING_NO_ACTION",
            "detail": "No management change.",
            "draft_action_count": 1,
            "attempted_action_count": 0,
            "terminal_effect_count": 0,
            "broker_touched": False,
            "operator_discretionary_status": "OPERATOR_DISCRETIONARY_OPTIONS_READY",
            "operator_discretionary_option_count": 3,
            "operator_discretionary_position_count": 1,
            "operator_discretionary_blocked_option_count": 0,
            "operator_discretionary_model_failure_policy": "STAND_DOWN",
            "scale_in_status": "NO_SCALE_IN_CANDIDATE",
            "scale_in_action_count": 0,
            "scale_in_parent_candidate_count": 0,
            "scale_in_blocker_count": 1,
            "scale_in_blockers": [
                {
                    "parent_broker_ticket": "123456",
                    "symbol": "US30",
                    "reason": "open-position cap is already full (4 / 4)",
                }
            ],
            "scale_in_max_compound_units": 4,
            "scale_in_minimum_profit_r": 0.5,
            "operator_position_edge": {
                "report_kind": "cas_forex_ai_operator_position_edge",
                "status": "AI_OPERATOR_POSITION_DECIDED",
                "prompt_version": "ai_operator_position_edge.v14",
                "generated_at": "2026-07-10T15:00:00+00:00",
                "provider": "claude",
                "summary": "Selected one exact trailing action.",
                "action_candidate_count": 2,
                "selected_action_count": 1,
                "operator_stand_down_count": 0,
                "hard_policy_selected_count": 0,
            },
        }

    def dispatch(**kwargs):
        captured["dispatch_bridge"] = kwargs.get("bridge")
        return _FakeCycle()

    monkeypatch.setattr(management_cycle, "run_ai_hedge_management_cycle", manage)
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", dispatch)

    dispatch_loop.start_loop(10)
    assert _wait_for(lambda: "dispatch_bridge" in captured)
    status = dispatch_loop.loop_status()

    assert captured["management_bridge"] is shared_bridge
    assert captured["dispatch_bridge"] is shared_bridge
    assert status["management_cycles_run"] >= 1
    assert status["last_management_status"] == "WATCHING_NO_ACTION"
    assert status["last_management_draft_action_count"] == 1
    assert status["last_scale_in_status"] == "NO_SCALE_IN_CANDIDATE"
    assert status["last_operator_discretionary_status"] == (
        "OPERATOR_DISCRETIONARY_OPTIONS_READY"
    )
    assert status["last_operator_discretionary_option_count"] == 3
    assert status["last_operator_discretionary_position_count"] == 1
    assert status["last_operator_discretionary_model_failure_policy"] == "STAND_DOWN"
    assert status["last_scale_in_blocker_count"] == 1
    assert "open-position cap" in status["last_scale_in_blockers"][0]["reason"]
    assert status["operator_position_edge_prompt_version"] == "ai_operator_position_edge.v14"
    assert status["last_operator_position_edge_status"] == "AI_OPERATOR_POSITION_DECIDED"
    assert status["last_operator_position_edge_selected_count"] == 1
    assert status["last_operator_position_edge_provider"] == "claude"
    assert "management=WATCHING_NO_ACTION" in (status["last_summary"] or "")
    dispatch_loop.stop_loop()


def test_mt5_paper_primary_keeps_legacy_simulator_positions_managed(monkeypatch):
    import cas_forex.agent_dispatch as ad
    import cas_forex.ai_hedge_management_cycle as management_cycle
    import cas_forex.broker_control as broker_control

    class _PaperMt5Bridge:
        pass

    class _LegacySimulator:
        def get_open_positions(self):
            return [{"ticket": 923871908, "symbol": "US30", "volume": 0.01}]

    primary = _PaperMt5Bridge()
    legacy = _LegacySimulator()
    managed: list[dict[str, Any]] = []
    dispatched: list[Any] = []

    monkeypatch.setattr(broker_control, "select_paper_learning_bridge", lambda config=None: primary)
    monkeypatch.setattr(
        broker_control,
        "select_durable_simulator_handoff_bridge",
        lambda config=None: legacy,
    )

    def manage(**kwargs):
        managed.append(dict(kwargs))
        is_legacy = kwargs.get("bridge") is legacy
        return {
            "status": "WATCHING_NO_ACTION" if is_legacy else "WATCHING_NO_BROKER_POSITIONS",
            "detail": "Legacy simulator position supervised." if is_legacy else "No MT5 demo positions.",
            "attempted_action_count": 0,
            "terminal_effect_count": 0,
            "broker_touched": False,
            "account_position_count": 1 if is_legacy else 0,
            "excluded_position_count": 0,
            "fresh_position_count": 1 if is_legacy else 0,
            "stale_position_count": 0,
            "position_snapshot_status": "FRESH",
            "price_source_status": "PROVIDER_ACTIVE" if is_legacy else "NO_OPEN_POSITIONS",
            "price_source_label": "FRESH QUOTE" if is_legacy else "NO POSITIONS",
            "quote_attempts": (
                [{"symbol": "US30", "usable": True, "quote_source": "test"}]
                if is_legacy
                else []
            ),
            "handoff_status": "READY_FOR_GUARDED_EXECUTION" if is_legacy else "NO_OPEN_POSITIONS",
            "blocked_action_count": 0,
            "blocked_actions": [],
        }

    def dispatch(**kwargs):
        dispatched.append(kwargs.get("bridge"))
        return _FakeCycle()

    monkeypatch.setattr(management_cycle, "run_ai_hedge_management_cycle", manage)
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", dispatch)

    dispatch_loop.start_loop(10)
    assert _wait_for(lambda: bool(dispatched))
    status = dispatch_loop.loop_status()
    dispatch_loop.stop_loop()

    assert any(row.get("bridge") is primary for row in managed)
    handoff_rows = [row for row in managed if row.get("bridge") is legacy]
    assert handoff_rows
    assert handoff_rows[0]["state_path"] == dispatch_loop.DEFAULT_SIMULATOR_HANDOFF_MANAGEMENT_STATE_PATH
    assert dispatched[0] is primary
    assert status["last_management_account_position_count"] == 1
    assert status["last_management_primary_position_count"] == 0
    assert status["last_management_simulator_handoff_position_count"] == 1
    assert status["last_management_status"] == "WATCHING_NO_ACTION"
    assert {row["role"] for row in status["last_management_sources"]} == {
        "PRIMARY",
        "SIMULATOR_HANDOFF",
    }
    simulator_source = next(
        row for row in status["last_management_sources"]
        if row["role"] == "SIMULATOR_HANDOFF"
    )
    assert simulator_source["fresh_position_count"] == 1
    assert simulator_source["quote_attempts"][0]["symbol"] == "US30"


def test_mt5_demo_learning_sync_runs_on_bridge_or_position_change():
    class _MT5Bridge:
        pass

    calls: list[dict[str, Any]] = []

    def sync_runner(**kwargs):
        calls.append(dict(kwargs))
        return {
            "status": "MT5_DEMO_LEARNING_SYNCED",
            "generated_at": utc_now().isoformat(),
            "history_record_count": 3,
            "bound_trade_count": 2,
            "group_learning_ready": False,
            "overall_sample_ready": True,
            "learning_ready_group_count": 0,
            "min_samples_per_group": 4,
        }

    bridge = _MT5Bridge()
    config = SimpleNamespace(live_mode=False, paper_trading=True)
    dispatch_loop._maybe_sync_mt5_demo_learning(
        primary_bridge=bridge,
        runtime_config=config,
        effective_mode="PAPER",
        management={"position_tickets": ["7001"]},
        sync_runner=sync_runner,
    )
    dispatch_loop._state._mt5_learning_sync_pending_after_dispatch = True
    dispatch_loop._maybe_sync_mt5_demo_learning(
        primary_bridge=bridge,
        runtime_config=config,
        effective_mode="PAPER",
        management={"position_tickets": ["7001"]},
        sync_runner=sync_runner,
    )
    dispatch_loop._maybe_sync_mt5_demo_learning(
        primary_bridge=bridge,
        runtime_config=config,
        effective_mode="PAPER",
        management={"position_tickets": ["7001"]},
        sync_runner=sync_runner,
    )
    dispatch_loop._maybe_sync_mt5_demo_learning(
        primary_bridge=bridge,
        runtime_config=config,
        effective_mode="PAPER",
        management={"position_tickets": []},
        sync_runner=sync_runner,
    )

    assert len(calls) == 3
    assert dispatch_loop._state._mt5_learning_sync_pending_after_dispatch is False
    assert dispatch_loop._state.last_mt5_demo_learning_sync_status == "MT5_DEMO_LEARNING_SYNCED"
    assert dispatch_loop._state.last_mt5_demo_learning_history_count == 3
    assert dispatch_loop._state.last_mt5_demo_learning_bound_trade_count == 2
    assert dispatch_loop._state.last_mt5_demo_learning_group_learning_ready is False
    assert dispatch_loop._state.last_mt5_demo_learning_overall_sample_ready is True
    assert dispatch_loop._state.last_mt5_demo_learning_ready_group_count == 0
    assert dispatch_loop._state.last_mt5_demo_learning_min_samples_per_group == 4


def test_mt5_demo_learning_sync_runs_immediately_on_utc_day_rollover():
    class _MT5Bridge:
        pass

    calls: list[dict[str, Any]] = []
    current = utc_now()
    dispatch_loop._state._mt5_learning_bridge_active = True
    dispatch_loop._state._mt5_learning_position_signature = ("7001",)
    dispatch_loop._state._mt5_learning_last_success_monotonic = time.monotonic()
    dispatch_loop._state.last_mt5_demo_learning_sync_at = (
        (current - timedelta(days=1)).isoformat()
    )

    def sync_runner(**kwargs):
        calls.append(dict(kwargs))
        return {
            "status": "MT5_DEMO_LEARNING_SYNCED",
            "generated_at": current.isoformat(),
        }

    dispatch_loop._maybe_sync_mt5_demo_learning(
        primary_bridge=_MT5Bridge(),
        runtime_config=SimpleNamespace(live_mode=False, paper_trading=True),
        effective_mode="PAPER",
        management={"position_tickets": ["7001"]},
        sync_runner=sync_runner,
    )

    assert len(calls) == 1
    assert dispatch_loop._state.last_mt5_demo_learning_sync_at == current.isoformat()


def test_mt5_demo_learning_sync_can_run_in_background_without_blocking_loop():
    class _MT5Bridge:
        pass

    started = threading.Event()
    release = threading.Event()
    completed_at = utc_now().isoformat()
    calls = []

    def slow_sync(**kwargs):
        calls.append(dict(kwargs))
        started.set()
        assert release.wait(timeout=3)
        return {
            "status": "MT5_DEMO_LEARNING_SYNCED",
            "generated_at": completed_at,
            "history_record_count": 3,
            "bound_trade_count": 2,
        }

    began = time.monotonic()
    dispatch_loop._maybe_sync_mt5_demo_learning(
        primary_bridge=_MT5Bridge(),
        runtime_config=SimpleNamespace(live_mode=False, paper_trading=True),
        effective_mode="PAPER",
        management={"position_tickets": ["7001"]},
        sync_runner=slow_sync,
        run_async=True,
    )

    assert time.monotonic() - began < 0.5
    assert started.wait(timeout=1)
    assert dispatch_loop._state.mt5_demo_learning_sync_in_progress is True
    dispatch_loop._maybe_sync_mt5_demo_learning(
        primary_bridge=_MT5Bridge(),
        runtime_config=SimpleNamespace(live_mode=False, paper_trading=True),
        effective_mode="PAPER",
        management={"position_tickets": ["7001"]},
        sync_runner=slow_sync,
        run_async=True,
    )
    assert len(calls) == 1

    release.set()
    deadline = time.monotonic() + 2
    while dispatch_loop._state.mt5_demo_learning_sync_in_progress and time.monotonic() < deadline:
        time.sleep(0.01)

    assert dispatch_loop._state.mt5_demo_learning_sync_in_progress is False
    assert dispatch_loop._state.last_mt5_demo_learning_sync_status == (
        "MT5_DEMO_LEARNING_SYNCED"
    )
    assert dispatch_loop._state.last_mt5_demo_learning_sync_at == completed_at
    assert dispatch_loop._state.last_mt5_demo_learning_sync_duration_seconds is not None


def test_one_bad_cycle_does_not_kill_the_loop(monkeypatch):
    import cas_forex.agent_dispatch as ad

    def _boom(**kw):
        raise RuntimeError("simulated cycle failure")

    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", _boom)
    dispatch_loop.start_loop(10)
    assert _wait_for(lambda: dispatch_loop.loop_status()["last_error"] is not None)
    # Loop is still running despite the cycle error.
    assert dispatch_loop.loop_status()["running"] is True
    assert "simulated cycle failure" in dispatch_loop.loop_status()["last_error"]
    dispatch_loop.stop_loop()


def test_live_requested_but_unready_keeps_paper_learning_active(monkeypatch):
    import cas_forex.agent_dispatch as ad

    called = {"collect": 0, "dispatch": 0}

    def collect(*_args, **_kwargs):
        called["collect"] += 1
        return []

    def dispatch(**_kwargs):
        called["dispatch"] += 1
        return _FakeCycle()

    monkeypatch.setattr(ad, "collect_route_intents", collect)
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", dispatch)
    monkeypatch.setattr(
        dispatch_loop,
        "_resolved_runtime_config",
        lambda: SimpleNamespace(live_mode=True, paper_trading=True, ai_hedge_position_scope="CAS_ONLY"),
    )
    monkeypatch.setattr(dispatch_loop, "requested_mode", lambda: "LIVE")
    monkeypatch.setattr(
        dispatch_loop,
        "_live_gate_decision",
        lambda: {
            "capability": "live_trading",
            "authorized": False,
            "status": "PENDING_OWNER_ENABLE",
            "missing_requirements": ["fresh broker truth", "passing live-order dry run"],
            "satisfied_requirements": ["owner live switch is ON"],
            "next_action": "Refresh broker truth and complete the live-order dry run.",
        },
    )

    dispatch_loop.start_loop(10)
    assert _wait_for(lambda: dispatch_loop.loop_status()["cycles_run"] >= 1)
    status = dispatch_loop.loop_status()

    assert status["status"] == "RUNNING"
    assert status["requested_mode"] == "LIVE"
    assert status["mode"] == "PAPER_FALLBACK"
    assert status["execution_lane"] == "PAPER"
    assert status["execution_active"] is True
    assert status["paper_learning_active"] is True
    assert status["paper_fallback_active"] is True
    assert status["live_execution_active"] is False
    assert status["live_execution_authorized"] is False
    assert status["running"] is True
    assert status["last_error"] is None
    assert "lane=PAPER mode=PAPER_FALLBACK" in status["last_summary"]
    assert status["last_blocking_detail"] is None
    assert status["live_blocking_detail"] == "Refresh broker truth and complete the live-order dry run."
    assert called == {"collect": 1, "dispatch": 1}
    dispatch_loop.stop_loop()


def test_paper_fallback_config_stays_paper_through_bridge_and_dispatch(monkeypatch):
    import cas_forex.agent_dispatch as ad
    import cas_forex.ai_hedge_management_cycle as management_cycle
    import cas_forex.broker_control as broker_control

    seen: dict[str, Any] = {}

    def select_paper(config=None):
        seen["bridge_config"] = config
        return object()

    def manage(**kwargs):
        seen["management_config"] = kwargs.get("config")
        return {
            "status": "WATCHING_NO_BROKER_POSITIONS",
            "detail": "No broker positions in test.",
            "attempted_action_count": 0,
            "terminal_effect_count": 0,
            "broker_touched": False,
        }

    def dispatch(**kwargs):
        seen["dispatch_config"] = kwargs.get("config")
        return _FakeCycle()

    monkeypatch.setattr(broker_control, "select_paper_learning_bridge", select_paper)
    monkeypatch.setattr(management_cycle, "run_ai_hedge_management_cycle", manage)
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", dispatch)
    monkeypatch.setattr(
        dispatch_loop,
        "_resolved_runtime_config",
        lambda: SimpleNamespace(live_mode=True, paper_trading=True, ai_hedge_position_scope="CAS_ONLY"),
    )
    monkeypatch.setattr(dispatch_loop, "requested_mode", lambda: "LIVE")
    monkeypatch.setattr(dispatch_loop, "_paper_lane_available", lambda: True)
    monkeypatch.setattr(dispatch_loop, "_live_gate_decision", lambda: {"authorized": False, "status": "PENDING"})

    dispatch_loop.start_loop(10)
    assert _wait_for(lambda: "dispatch_config" in seen)

    for key in ("bridge_config", "management_config", "dispatch_config"):
        assert seen[key].live_mode is False
        assert seen[key].paper_trading is True
    assert dispatch_loop.loop_status()["mode"] == "PAPER_FALLBACK"
    dispatch_loop.stop_loop()


def test_authorized_live_lane_does_not_use_paper_bridge(monkeypatch):
    import cas_forex.broker_control as broker_control

    seen: dict[str, Any] = {"paper_called": False}

    def select_live(config=None):
        seen["live_config"] = config
        return object()

    def select_paper(config=None):
        seen["paper_called"] = True
        return object()

    monkeypatch.setattr(broker_control, "select_bridge", select_live)
    monkeypatch.setattr(broker_control, "select_paper_learning_bridge", select_paper)
    monkeypatch.setattr(
        dispatch_loop,
        "_resolved_runtime_config",
        lambda: SimpleNamespace(live_mode=True, paper_trading=True, ai_hedge_position_scope="CAS_ONLY"),
    )
    monkeypatch.setattr(dispatch_loop, "requested_mode", lambda: "LIVE")
    monkeypatch.setattr(dispatch_loop, "_live_gate_decision", lambda: {"authorized": True, "status": "AUTHORIZED"})

    dispatch_loop.start_loop(10)
    assert _wait_for(lambda: "live_config" in seen)

    assert seen["live_config"].live_mode is True
    assert seen["paper_called"] is False
    assert dispatch_loop.loop_status()["mode"] == "LIVE"
    assert dispatch_loop.loop_status()["execution_lane"] == "LIVE"
    dispatch_loop.stop_loop()


def test_live_requested_without_any_paper_lane_remains_blocked(monkeypatch):
    import cas_forex.agent_dispatch as ad

    called = {"collect": 0, "dispatch": 0}
    monkeypatch.setattr(ad, "collect_route_intents", lambda *_a, **_k: called.__setitem__("collect", called["collect"] + 1) or [])
    monkeypatch.setattr(ad, "run_agent_dispatch_cycle", lambda **_k: called.__setitem__("dispatch", called["dispatch"] + 1) or _FakeCycle())
    monkeypatch.setattr(dispatch_loop, "requested_mode", lambda: "LIVE")
    monkeypatch.setattr(dispatch_loop, "_paper_lane_available", lambda: False)
    monkeypatch.setattr(
        dispatch_loop,
        "_live_gate_decision",
        lambda: {
            "authorized": False,
            "status": "PENDING_OWNER_ENABLE",
            "missing_requirements": ["live gate"],
            "next_action": "Complete live authorization.",
        },
    )

    dispatch_loop.start_loop(10)
    assert _wait_for(lambda: dispatch_loop.loop_status()["cycles_idle"] >= 1)
    status = dispatch_loop.loop_status()

    assert status["status"] == "LIVE_BLOCKED"
    assert status["mode"] == "LIVE_BLOCKED"
    assert status["execution_lane"] == "NONE"
    assert status["execution_active"] is False
    assert status["paper_fallback_available"] is False
    assert called == {"collect": 0, "dispatch": 0}
    dispatch_loop.stop_loop()


def test_desired_loop_restores_paper_fallback_while_live_is_pending(monkeypatch, tmp_path):
    dispatch_loop.set_control_state_path_for_testing(tmp_path / "dispatch-loop-control.json")
    dispatch_loop.start_loop(12, symbols=["NAS100"])
    dispatch_loop.stop_loop(persist_desired=False)
    monkeypatch.setattr(dispatch_loop, "requested_mode", lambda: "LIVE")
    monkeypatch.setattr(dispatch_loop, "_paper_lane_available", lambda: True)
    monkeypatch.setattr(dispatch_loop, "_live_gate_decision", lambda: {"authorized": False, "status": "PENDING"})

    restored = dispatch_loop.restore_desired_loop()

    assert restored["restore_status"] == "RESTORED_DESIRED_PAPER_FALLBACK_LOOP"
    assert restored["running"] is True
    assert restored["mode"] == "PAPER_FALLBACK"
    assert restored["execution_lane"] == "PAPER"
    assert restored["symbols"] == ["NAS100"]


def test_desired_dispatch_loop_restores_after_process_restart(tmp_path):
    dispatch_loop.set_control_state_path_for_testing(tmp_path / "dispatch-loop-control.json")
    dispatch_loop.start_loop(30, symbols=["NAS100", "US30"], sessions=["Asian"])
    # Simulate process teardown: stop the in-memory thread but keep owner desired state.
    dispatch_loop.stop_loop(persist_desired=False)

    restored = dispatch_loop.restore_desired_loop()

    assert restored["restore_status"] == "RESTORED_DESIRED_PAPER_LOOP"
    assert restored["running"] is True
    assert restored["interval_seconds"] == 30
    assert restored["symbols"] == ["NAS100", "US30"]
    assert restored["sessions"] == ["Asian"]


def test_dispatch_loop_control_records_actor_reason_revision_and_hash(tmp_path):
    state_path = tmp_path / "dispatch-loop-control.json"
    dispatch_loop.set_control_state_path_for_testing(state_path)

    dispatch_loop.start_loop(
        30,
        symbols=[],
        requested_by="test-owner",
        change_reason="remove stale scheduler subset",
    )
    dispatch_loop.stop_loop(persist_desired=False)

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    audit_path = tmp_path / "dispatch-loop-control-audit.jsonl"
    audit = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert payload["revision"] == 1
    assert payload["updated_by"] == "test-owner"
    assert payload["change_reason"] == "remove stale scheduler subset"
    assert len(payload["event_hash"]) == 64
    assert audit["after"]["event_hash"] == payload["event_hash"]


def test_owner_stop_persists_dispatch_loop_off(tmp_path):
    dispatch_loop.set_control_state_path_for_testing(tmp_path / "dispatch-loop-control.json")
    dispatch_loop.start_loop(30, symbols=["NAS100"])
    dispatch_loop.stop_loop()

    restored = dispatch_loop.restore_desired_loop()

    assert restored["restore_status"] == "NO_RESTORE_DESIRED"
    assert restored["running"] is False
