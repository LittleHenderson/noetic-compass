"""Tests for the always-on operator scheduler (ai_operator_runner) + routes."""

from __future__ import annotations

import threading
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cas_forex import ai_operator_runner


def test_desired_state_persists_and_restores(tmp_path):
    ai_operator_runner.set_control_state_path_for_tests(tmp_path / "control.json")
    try:
        ai_operator_runner.set_desired_runner_state(1200, desired_running=True)
        control = ai_operator_runner.control_state()
        assert control["desired_running"] is True
        assert control["interval_seconds"] == 1200
    finally:
        ai_operator_runner.stop_runner(persist_desired=False)
        ai_operator_runner.set_control_state_path_for_tests(None)


def test_off_by_default_restore_does_not_start(tmp_path):
    ai_operator_runner.set_control_state_path_for_tests(tmp_path / "control.json")
    try:
        status = ai_operator_runner.restore_desired_state_on_startup()
        assert status["running"] is False
        assert status["desired_running"] is False
    finally:
        ai_operator_runner.set_control_state_path_for_tests(None)


def test_interval_is_clamped(tmp_path):
    ai_operator_runner.set_control_state_path_for_tests(tmp_path / "control.json")
    try:
        status = ai_operator_runner.set_desired_runner_state(5, desired_running=False)  # below min
        assert status["interval_seconds"] >= ai_operator_runner.MIN_INTERVAL_SECONDS
    finally:
        ai_operator_runner.set_control_state_path_for_tests(None)


def test_route_state_exposes_provider_and_actions(tmp_path):
    from api.routes import ai_operator as route

    ai_operator_runner.set_control_state_path_for_tests(tmp_path / "control.json")
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    client = TestClient(app)
    try:
        resp = client.get("/api/forex/ai-operator/state")
        assert resp.status_code == 200
        body = resp.json()
        assert body["report_kind"] == "cas_forex_ai_operator_runner"
        assert "model_provider" in body
        assert "recent_actions" in body
        assert "active_account_objective" in body
        assert "last_context_delivery" in body
        assert "professional_readiness" in body
        assert "last_entry_risk_feasibility" in body["execution_runtime"]
        assert "last_management_simulator_handoff_position_count" in body["execution_runtime"]
        assert "last_mt5_demo_learning_sync_status" in body["execution_runtime"]
        assert "last_mt5_demo_learning_group_learning_ready" in body["execution_runtime"]
        assert "last_mt5_demo_learning_overall_sample_ready" in body["execution_runtime"]
        assert body["execution_runtime"]["operator_trade_edge_prompt_version"] == "ai_operator_trade_edge.v11"
        assert "last_operator_trade_edge_status" in body["execution_runtime"]
        assert "last_operator_trade_edge" in body["execution_runtime"]
        assert body["execution_runtime"]["operator_position_edge_prompt_version"] == "ai_operator_position_edge.v14"
        assert "last_operator_position_edge_status" in body["execution_runtime"]
        assert "last_operator_position_edge" in body["execution_runtime"]
        assert "claim_boundary" in body
    finally:
        ai_operator_runner.set_control_state_path_for_tests(None)


def test_runner_status_uses_reconciled_account_growth(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    import cas_forex.mt5_account_growth as account_growth
    import cas_forex.mt5_live as mt5_live

    growth = {
        "status": "RECONCILED_CASHFLOW_ADJUSTED_GROWTH",
        "event_hash": "growth-ledger-1",
    }
    captured: dict[str, object] = {}

    monkeypatch.setattr(account_growth, "load_mt5_account_growth", lambda: growth)
    monkeypatch.setattr(mt5_live, "get_mt5_account_snapshot", lambda force=False: {})
    monkeypatch.setattr(ai_operator, "_compact_mt5_snapshot", lambda _snapshot: {})
    monkeypatch.setattr(dispatch_loop, "loop_status", lambda: {})

    def build_objective(**kwargs):
        captured.update(kwargs)
        return {"status": "TEST_ACTIVE_ACCOUNT_OBJECTIVE"}

    monkeypatch.setattr(ai_operator, "_active_account_objective_context", build_objective)

    status = ai_operator_runner.runner_status()

    assert status["active_account_objective"]["status"] == "TEST_ACTIVE_ACCOUNT_OBJECTIVE"
    assert captured["account_growth"] == growth


def test_rich_status_build_does_not_hold_scheduler_lock(monkeypatch):
    import cas_forex.ai_operator as ai_operator

    entered = threading.Event()
    release = threading.Event()

    def slow_readiness():
        entered.set()
        release.wait(timeout=5.0)
        return {"status": "TEST_READY"}

    monkeypatch.setattr(ai_operator, "_professional_readiness_context", slow_readiness)
    worker = threading.Thread(target=ai_operator_runner.runner_status, daemon=True)
    worker.start()
    assert entered.wait(timeout=5.0)
    assert ai_operator_runner._lock.acquire(timeout=0.5)  # noqa: SLF001 - lock contract regression test
    ai_operator_runner._lock.release()  # noqa: SLF001 - lock contract regression test
    release.set()
    worker.join(timeout=5.0)
    assert not worker.is_alive()


def test_route_state_returns_shell_while_rich_packet_warms(monkeypatch):
    from api import route_cache
    from api.routes import ai_operator as route

    started = threading.Event()
    release = threading.Event()

    def slow_rich_packet():
        started.set()
        release.wait(timeout=5.0)
        return {"report_kind": ai_operator_runner.REPORT_KIND, "marker": "RICH"}

    monkeypatch.setattr(route_cache, "under_pytest", lambda: False)
    monkeypatch.setattr(route, "build_operator_state", slow_rich_packet)
    monkeypatch.setattr(
        route,
        "build_operator_state_shell",
        lambda: {"report_kind": ai_operator_runner.REPORT_KIND, "marker": "SHELL"},
    )
    route_cache.invalidate_cache(route.OPERATOR_STATE_CACHE_KEY)

    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    client = TestClient(app)
    try:
        response = client.get("/api/forex/ai-operator/state")
        assert response.status_code == 200
        assert response.json()["marker"] == "SHELL"
        assert response.json()["cache_status"] == "warming"
        assert started.wait(timeout=2.0)
    finally:
        release.set()
        route_cache.invalidate_cache(route.OPERATOR_STATE_CACHE_KEY)


def test_chat_route_converts_operator_exception_to_bounded_reply(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    from api.routes import ai_operator as route

    class _BoomOperator:
        def chat(self, message: str) -> dict[str, object]:
            raise RuntimeError(f"chat bridge offline for {message}")

    monkeypatch.setattr(ai_operator, "AIOperator", _BoomOperator)

    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    client = TestClient(app)

    resp = client.post("/api/forex/ai-operator/chat", json={"message": "hello"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["chat_path_status"] == "MODEL_ERROR_LOCAL_FAST_FALLBACK"
    assert body["response_source"] == "LOCAL_FAST_FALLBACK"
    assert "bounded runtime answer is keeping the conversation alive" in body["reply"]
    assert body["diagnostic"] == (
        "operator_chat_backend_error:RuntimeError: chat bridge offline for hello"
    )
    assert body["dials_changed"] is False
    assert body["proposed_command"] is None


def test_chat_route_returns_bounded_generic_fallback(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    from api.routes import ai_operator as route

    class _SlowOperator:
        def chat(self, _message: str) -> dict[str, object]:
            time.sleep(0.2)
            return {"ok": True, "reply": "too late"}

    monkeypatch.setattr(ai_operator, "AIOperator", _SlowOperator)
    monkeypatch.setattr(route, "OPERATOR_CHAT_RESPONSE_BUDGET_SECONDS", 0.01)
    monkeypatch.setattr(route, "OPERATOR_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS", 0.01)
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "WATCHING_NO_ACTION",
        },
    )

    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    client = TestClient(app)
    response = client.post(
        "/api/forex/ai-operator/chat",
        json={"message": "Explain the current strategy state."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "MODEL_TIMEOUT_LOCAL_FAST_FALLBACK"
    assert body["response_source"] == "LOCAL_FAST_FALLBACK"
    assert "model/context path exceeded its response budget" in body["reply"]
    assert "dispatch running=True, lane=PAPER" in body["reply"]
    assert body["dials_changed"] is False


def test_chat_route_answers_compounding_from_live_fast_truth_without_model(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("known authority truth must not wait on a model")

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "WATCHING_NO_ACTION",
            "last_scale_in_status": "NO_SCALE_IN_CANDIDATE",
            "last_scale_in_action_count": 0,
            "last_scale_in_blockers": [
                {
                    "symbol": "NAS100",
                    "parent_broker_ticket": "45944855",
                    "reason": "open-position cap is already full (4 / 4)",
                }
            ],
        },
    )
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    response = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={"message": "Should you compound this winning position?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "LOCAL_COMPOUND_AUTHORITY_TRUTH"
    assert "autonomous scale-in authority" in body["reply"]
    assert "dispatch running=True, lane=PAPER" in body["reply"]
    assert "status=NO_SCALE_IN_CANDIDATE" in body["reply"]
    assert "open-position cap is already full (4 / 4)" in body["reply"]
    assert body["model_attempted"] is False
    assert body["response_source"] == "LOCAL_RUNTIME_TRUTH"
    assert body["error"] is None
    assert body["diagnostic"] == "model_not_needed_for_authority_truth"


def test_chat_route_answers_position_management_from_live_fast_truth_without_model(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("current position-management truth must not wait on a model")

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "WATCHING_NO_ACTION",
            "last_operator_discretionary_status": "OPERATOR_DISCRETIONARY_OPTIONS_READY",
            "last_operator_discretionary_option_count": 5,
            "last_operator_discretionary_position_count": 3,
            "last_operator_discretionary_blocked_option_count": 0,
            "last_operator_position_edge_status": "AI_OPERATOR_POSITION_STOOD_DOWN",
            "last_operator_position_edge_selected_count": 0,
            "last_operator_position_edge_stand_down_count": 3,
        },
    )
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    response = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={"message": "Why haven't you taken profit or closed a position?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "LOCAL_POSITION_MANAGEMENT_TRUTH"
    assert "exact options=5" in body["reply"]
    assert "positions represented=3" in body["reply"]
    assert "latest position-edge status=AI_OPERATOR_POSITION_STOOD_DOWN" in body["reply"]
    assert body["model_attempted"] is False
    assert body["response_source"] == "LOCAL_RUNTIME_TRUTH"
    assert body["error"] is None
    assert body["diagnostic"] == "model_not_needed_for_authority_truth"


def test_chat_route_answers_live_readiness_from_execution_gates_without_model(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.broker_truth_monitor as broker_truth_monitor
    import cas_forex.dispatch_loop as dispatch_loop
    import cas_forex.runtime_gates as runtime_gates
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("live-readiness truth must not wait on a model")

    class _GateDecision:
        def to_dict(self):
            return {
                "authorized": False,
                "status": "CURRENTLY NOT LICENSED",
                "missing_requirements": [
                    "continuous broker-truth monitor is fresh and live-connected",
                    "owner broker-reality review is ACCEPT for selected broker",
                ],
                "satisfied_requirements": [
                    "owner live-trading switches are ON",
                    "auto-halt circuit breaker is CLEAR",
                ],
            }

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(runtime_gates, "evaluate_live_trading", lambda **_kwargs: _GateDecision())
    monkeypatch.setattr(
        broker_truth_monitor,
        "monitor_status",
        lambda: {
            "running": False,
            "cycles_run": 0,
            "external_worker": {"running": True, "cycles_run": 46},
            "latest_report": {
                "mt5_account": 1000694,
                "mt5_is_demo": True,
                "overall_status": "RECONCILED_WITH_WARNINGS",
                "mt5_account_money_snapshot": {"server": "Hugosway-Demo"},
            },
        },
    )
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "ACTIONS_ATTEMPTED",
            "last_operator_trade_edge_status": "DAILY_REALIZED_LOSS_CAP_REACHED",
            "last_operator_trade_edge_summary": (
                "New exposure blocked: realized P&L today is $-55.68, at or below "
                "the -$50.00 daily loss boundary."
            ),
        },
    )
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    response = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={"message": "Are we authorized to trade real money right now? What gates block it?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "LOCAL_LIVE_READINESS_TRUTH"
    assert "Current real-money status=CURRENTLY NOT LICENSED" in body["reply"]
    assert "#1000694 on Hugosway-Demo, account type=DEMO" in body["reply"]
    assert "Broker-truth monitor running=True, cycles=46" in body["reply"]
    assert "owner live-trading switches are ON" in body["reply"]
    assert "daily loss boundary" in body["reply"]
    assert body["model_attempted"] is False
    assert body["response_source"] == "LOCAL_RUNTIME_TRUTH"
    assert body["error"] is None


def test_chat_route_answers_model_outage_from_fast_truth_without_model(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    import cas_forex.model_provider as model_provider
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("availability truth must not wait on a model")

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "WATCHING_NO_ACTION",
        },
    )
    monkeypatch.setattr(
        model_provider.get_model_provider(),
        "status",
        lambda: {
            "active_provider": "local-fallback",
            "active_provider_label": "Local model (llama3.1:70b-instruct)",
            "active_is_paid": False,
            "budget_remaining": 0,
            "budget_capped": True,
        },
    )
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    response = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={"message": "Why is the Operator not responding?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "LOCAL_MODEL_AVAILABILITY_TRUTH"
    assert "free local fallback is selected" in body["reply"]
    assert "dispatch running=True, lane=PAPER" in body["reply"]
    assert body["model_attempted"] is False
    assert body["response_source"] == "LOCAL_RUNTIME_TRUTH"
    assert body["error"] is None
    assert body["diagnostic"] == "model_not_needed_for_authority_truth"


def test_chat_route_treats_positive_response_status_as_grounded_truth(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    import cas_forex.model_provider as model_provider
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("response status must not wait on or trust a model")

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "WATCHING_NO_BROKER_POSITIONS",
        },
    )
    monkeypatch.setattr(
        model_provider.get_model_provider(),
        "status",
        lambda: {
            "active_provider": "local-fallback",
            "active_provider_label": "Local model (deepseek-r1:latest)",
            "active_is_paid": False,
            "budget_remaining": 0,
            "budget_capped": True,
        },
    )
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    response = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={
            "message": (
                "Are you responding now, and what is the current model and dispatch status?"
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "LOCAL_MODEL_AVAILABILITY_TRUTH"
    assert "free local fallback is selected" in body["reply"]
    assert "dispatch running=True, lane=PAPER" in body["reply"]
    assert body["model_attempted"] is False
    assert body["response_source"] == "LOCAL_RUNTIME_TRUTH"


def test_chat_route_answers_scalp_inactivity_from_live_fast_truth_without_model(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("current trade-path truth must not wait on a model")

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "AI_OPERATOR_STOOD_DOWN",
            "last_entry_timeframe": "M5",
            "last_entry_lane": "MICRO_SCALP",
            "last_symbol_targeting_status": "ENTRY_SYMBOLS_READY",
            "last_eligible_entry_symbols": ["EUR/USD", "NAS100", "XAU/USD"],
            "last_entry_risk_feasibility_status": "NO_OVERSEER_APPROVED_CANDIDATES",
            "last_entry_risk_candidate_count": 0,
            "last_entry_risk_feasible_count": 0,
            "last_entry_risk_blocked_count": 0,
            "last_entry_risk_operator_candidate_count": 0,
            "last_bridge_class": "MT5Bridge",
            "last_bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
        },
    )
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    response = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={"message": "WHY DONT YOU SCALP TRADE??"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "LOCAL_TRADE_PATH_TRUTH"
    assert "M5 MICRO_SCALP lane" in body["reply"]
    assert "scalp trading is enabled, not disabled" in body["reply"]
    assert "No entry candidate reached the Operator" in body["reply"]
    assert "entry preflight=NO_OVERSEER_APPROVED_CANDIDATES" in body["reply"]
    assert "bridge=MT5Bridge/PAPER_MT5_ORDER_SEND_READY" in body["reply"]
    assert body["model_attempted"] is False
    assert body["response_source"] == "LOCAL_RUNTIME_TRUTH"
    assert body["error"] is None
    assert body["diagnostic"] == "model_not_needed_for_authority_truth"


def test_chat_route_names_pre_operator_directional_floor_starvation(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    import cas_forex.live_candle_route_policy as live_policy
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("entry pipeline truth must not wait on a model")

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "AI_OPERATOR_STOOD_DOWN",
            "last_entry_timeframe": "M1",
            "last_entry_lane": "MICRO_SCALP",
            "last_symbol_targeting_status": "ENTRY_SYMBOLS_READY",
            "last_eligible_entry_symbols": ["EUR/USD", "NAS100"],
            "last_entry_risk_feasibility_status": "NO_OVERSEER_APPROVED_CANDIDATES",
            "last_entry_risk_candidate_count": 0,
            "last_entry_risk_feasible_count": 0,
            "last_entry_risk_blocked_count": 0,
            "last_entry_risk_operator_candidate_count": 0,
                "last_bridge_class": "MT5Bridge",
                "last_bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
                "last_entry_timeframe_scan": {
                    "status": "SCAN_THROTTLED_CACHE",
                    "cache_remaining_seconds": 20.0,
                },
            },
        )
    monkeypatch.setattr(
        live_policy,
        "live_candle_route_runtime_status",
        lambda: {
            "full_scan_lane_count": 4,
            "attempt_count": 68,
            "all_observed_lanes_below_directional_floor": True,
            "shadow_edge_status_counts": {
                "PASS": 1,
                "NO_TRADE_NULL_FAILED": 67,
            },
            "best_shadow_pass_lane": {
                "symbol": "EUR/USD",
                "timeframe": "H1",
                "direction": "SHORT",
                "directional_score": 0.29,
                "shadow_measured_win_prob": 0.8,
                "shadow_threshold": 0.65,
            },
            "strongest_rejected_lane": {
                "symbol": "NAS100",
                "timeframe": "M5",
                "direction": "LONG",
                "directional_score": 0.31,
                "directional_floor": 0.5,
            },
        },
    )
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")

    response = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={"message": "Why has the Operator not made any paper trades?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "LOCAL_TRADE_PATH_TRUTH"
    assert "68 symbol/timeframe attempts" in body["reply"]
    assert "score=0.31, floor=0.5" in body["reply"]
    assert "pre-Operator candidate starvation" in body["reply"]
    assert "prudently reviewed and rejected" in body["reply"]
    assert "Best read-only shadow PASS lane=EUR/USD H1 SHORT" in body["reply"]
    assert "minted no authorization token" in body["reply"]
    assert body["model_attempted"] is False


def test_chat_route_labels_cold_start_trade_telemetry_as_warming(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("cold-start trade truth must not wait on a model")

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "AI_OPERATOR_STOOD_DOWN",
            "last_bridge_class": "MT5Bridge",
            "last_bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
        },
    )
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    response = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={"message": "Why haven't you made a scalp trade?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "LOCAL_TRADE_PATH_TRUTH"
    assert "per-cycle scalp telemetry is still warming after startup" in body["reply"]
    assert "telemetry warm-up, not an AI stand-down" in body["reply"]
    assert "not reported not reported" not in body["reply"]


def test_chat_route_uses_same_rich_dispatch_snapshot_as_cockpit(monkeypatch):
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("current trade-path truth must not wait on a model")

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "WATCHING_NO_BROKER_POSITIONS",
            "last_bridge_class": "MT5Bridge",
            "last_bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
        },
    )
    monkeypatch.setattr(
        route,
        "cached_payload_snapshot",
        lambda _key, **_kwargs: {
            "running": True,
            "execution_lane": "PAPER",
            "last_entry_timeframe": "M15",
            "last_entry_lane": "INTRADAY",
            "last_symbol_targeting_status": "ENTRY_SYMBOLS_READY",
            "last_eligible_entry_symbols": ["EUR/USD", "NAS100", "XAU/USD"],
            "last_entry_risk_feasibility_status": "NO_OVERSEER_APPROVED_CANDIDATES",
            "last_entry_risk_candidate_count": 0,
            "last_entry_risk_feasible_count": 0,
            "last_entry_risk_blocked_count": 0,
            "last_entry_risk_operator_candidate_count": 0,
        },
    )
    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    body = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={"message": "WHY DONT YOU SCALP TRADE??"},
    ).json()

    assert "M15 INTRADAY lane" in body["reply"]
    assert "symbols=ENTRY_SYMBOLS_READY, eligible=3" in body["reply"]
    assert "still warming" not in body["reply"]
    assert "bridge=MT5Bridge/PAPER_MT5_ORDER_SEND_READY" in body["reply"]


def test_chat_route_answers_active_account_truth_without_waiting_on_model(monkeypatch):
    import api.data as api_data
    import cas_forex.ai_operator as ai_operator
    import cas_forex.dispatch_loop as dispatch_loop
    from api.routes import ai_operator as route

    class _MustNotRunOperator:
        def chat(self, _message: str) -> dict[str, object]:
            raise AssertionError("current account truth must not wait on a model")

    monkeypatch.setattr(ai_operator, "AIOperator", _MustNotRunOperator)
    monkeypatch.setattr(
        ai_operator,
        "_profit_and_balance",
        lambda: {
            "scope": "PAPER_SIMULATOR_PERFORMANCE",
            "honest_paper_balance_usd": 3040.87,
            "balance_growth_net_pnl_usd": 1040.87,
        },
    )
    monkeypatch.setattr(
        api_data,
        "active_account_truth",
        lambda: {
            "status": "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE",
            "objective_account_established": True,
            "authoritative_account_source": "mt5_account_snapshot",
            "account": {
                "login": 1000694,
                "server": "Hugosway-Demo",
                "is_demo": True,
                "balance_usd": 45080.90,
                "equity_usd": 45110.36,
            },
            "open_exposure": {"open_position_count": 6},
            "snapshot": {
                "observed_at": "2026-07-14T19:00:34+00:00",
                "age_seconds": 1.2,
                "fresh": True,
            },
            "growth_measurement": {
                "cashflow_adjusted_realized_growth_usd": -54919.10,
                "realized_today_usd": 39.41,
                "realized_month_usd": -54918.97,
                "net_external_capital_flow_usd": 100000.0,
                "account_growth_reconciliation": {"reconciled": True},
                "open_pnl_decomposition": {
                    "price_pnl_usd": 32.71,
                    "swap_or_carry_usd": -3.25,
                    "commission_usd": 0.0,
                    "account_net_open_pnl_usd": 29.46,
                    "unattributed_open_pnl_usd": 0.0,
                },
            },
            "secondary_simulator": {
                "scope": "SEPARATE_PAPER_SIMULATOR_EVIDENCE",
                "account": {"balance_usd": 5000.0},
            },
        },
    )
    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "AI_OPERATOR_STOOD_DOWN",
        },
    )
    monkeypatch.setattr(route, "cached_payload_snapshot", lambda *_args, **_kwargs: {})

    app = FastAPI()
    app.include_router(route.router, prefix="/api/forex/ai-operator")
    response = TestClient(app).post(
        "/api/forex/ai-operator/chat",
        json={"message": "What is our current account balance, P&L, and realized growth?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_path_status"] == "LOCAL_ACTIVE_ACCOUNT_TRUTH"
    assert body["model_attempted"] is False
    assert body["response_source"] == "LOCAL_RUNTIME_TRUTH"
    assert body["active_account_truth"]["account"]["login"] == 1000694
    assert body["active_account_truth"]["open_exposure"]["open_position_count"] == 6
    assert "Net open P&L after reported costs +$29.46" in body["reply"]
    assert "all time -$54,919.10" in body["reply"]
    assert "Neither is added to the active MT5 account" in body["reply"]
