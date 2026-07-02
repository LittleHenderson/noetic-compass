from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import waste_loop_control as route_module
from cas_forex import waste_paper_sample_collector as collector_module
from cas_forex.waste_paper_sample_collector import (
    REPORT_KIND,
    SCAN_REPORT_KIND,
    SCHEDULER_REPORT_KIND,
    SCHEDULER_RUNNING,
    SCHEDULER_STOPPED,
    STATUS_AWAITING_PAPER_EXECUTION,
    STATUS_NEEDS_BROKER_GRADE_CANDLES,
    STATUS_NEEDS_PASS_TOKEN,
    STATUS_OUTCOMES_READY,
    WastePaperSampleCollectorScheduler,
    build_waste_paper_sample_collector,
    run_waste_paper_sample_collection_once,
)


def _runner(**overrides):
    payload = {
        "report_kind": "cas_forex_waste_runner",
        "status": "RUNNING",
        "running": True,
        "mode": "PAPER",
        "cycles_run": 12,
        "current_stage": "no_trade",
        "last_decision": "NO_TRADE",
    }
    payload.update(overrides)
    return payload


def _diagnostic(*, ready: bool = True):
    return {
        "report_kind": "cas_forex_mt5_market_data_diagnostic",
        "status": "MT5_MARKET_DATA_READY" if ready else "NO_MT5_MARKET_DATA_DIAGNOSTIC",
        "ready_symbol_count": 1 if ready else 0,
        "checked_symbol_count": 2 if ready else 0,
        "broker_touched": False,
    }


def _probe(*, broker_grade: bool = True, edge_status: str = "NO_TRADE_NULL_FAILED"):
    return {
        "report_kind": "cas_forex_waste_real_candle_probe",
        "status": "EDGE_PASS_UNREGISTERED" if edge_status == "PASS" else "EDGE_BLOCKED",
        "symbol": "NAS100",
        "timeframe": "D1",
        "broker_grade_market_truth": broker_grade,
        "fallback_used": False,
        "broker_touched": False,
        "candidate": {
            "symbol": "NAS100",
            "timeframe": "D1",
            "direction": "LONG",
            "decision_ref": "waste-test-1",
        },
        "edge": {
            "status": edge_status,
            "has_edge_token": edge_status == "PASS",
        },
    }


def _learning(*, confirmed: int = 0):
    return {
        "report_kind": "cas_forex_waste_direction_learning_ledger",
        "status": "WASTE_DIRECTION_LEARNING_ACTIVE",
        "direction_rows": max(confirmed, 1),
        "confirmed_direction_count": confirmed,
        "blocked_direction_count": 1,
        "learning_ready_for_adaptation": confirmed >= 5,
        "profile_recommendation": {
            "status": "PROFILE_DIRECTION_REVIEW_READY" if confirmed >= 5 else "INSUFFICIENT_CONFIRMED_EDGE",
            "min_confirmed_for_adaptation": 5,
        },
        "money_moved": False,
    }


def _outcome(*, confirmed: int = 0, executed: int = 0, bound: int = 0, ready: bool = False):
    return {
        "report_kind": "cas_forex_waste_direction_outcome_binding",
        "status": "WASTE_DIRECTION_OUTCOME_READY_FOR_PROMOTION_REVIEW" if ready else "WASTE_DIRECTION_OUTCOME_COLLECTING",
        "read_only": True,
        "dry_run": True,
        "paper_only": True,
        "outcome_ready_for_promotion": ready,
        "min_bound_outcomes_for_promotion": 5,
        "direction_rows": max(confirmed, 1),
        "confirmed_direction_count": confirmed,
        "executed_confirmed_count": executed,
        "closed_history_count": bound,
        "bound_outcome_count": bound,
        "bound_outcomes_needed": max(0, 5 - bound),
        "net_paper_pnl": 125.0 if ready else 0.0,
        "runtime_changed": False,
        "broker_touched": False,
        "money_moved": False,
    }


def _history(*, closed: int = 0):
    return {
        "report_kind": "cas_forex_mt5_deal_history_ingest_report",
        "ingest_status": "DEMO_DEAL_HISTORY_JOINED" if closed else "UNAVAILABLE",
        "account_mode": "demo",
        "history_records": [{} for _ in range(closed)],
        "summary": {
            "closed_position_count": closed,
            "history_record_count": closed,
            "net_profit_loss_account": 125.0 if closed else 0.0,
        },
    }


def test_collector_counts_isolated_waste_runner_worker_as_running(monkeypatch):
    monkeypatch.setattr(
        collector_module,
        "_external_waste_runner_worker_status",
        lambda: {
            "running": True,
            "status": "RUNNING",
            "pid": 12345,
            "started_at": "2026-07-01T00:00:00+00:00",
            "config": {"interval_seconds": 60},
        },
    )
    monkeypatch.setattr(
        "cas_forex.waste_runner.runner_status",
        lambda: _runner(running=False, status="STOPPED", cycles_run=0),
    )

    runner = collector_module._runner_status()
    report = build_waste_paper_sample_collector(
        runner=runner,
        mt5_market_data_diagnostic=_diagnostic(ready=True),
        real_candle_probe=_probe(edge_status="NO_TRADE_NULL_FAILED"),
        direction_learning=_learning(),
        direction_outcome_binding=_outcome(),
        mt5_deal_history_ingest=_history(),
    )

    assert runner["running"] is True
    assert runner["worker_isolated"] is True
    assert runner["external_worker"]["pid"] == 12345
    assert report["paper_runner_running"] is True
    paper_runner_check = next(check for check in report["checks"] if check["check_id"] == "paper_runner_running")
    assert paper_runner_check["passed"] is True
    assert paper_runner_check["evidence"]["running"] is True


def test_collector_blocks_until_broker_grade_market_data_exists():
    report = build_waste_paper_sample_collector(
        runner=_runner(),
        mt5_market_data_diagnostic=_diagnostic(ready=False),
        real_candle_probe={"report_kind": "cas_forex_waste_real_candle_probe", "status": "NO_PROBE_RECORDED"},
        direction_learning=_learning(),
        direction_outcome_binding=_outcome(),
        mt5_deal_history_ingest=_history(),
    )

    assert report["report_kind"] == REPORT_KIND
    assert report["status"] == STATUS_NEEDS_BROKER_GRADE_CANDLES
    assert report["paper_only"] is True
    assert report["broker_touched"] is False
    assert report["broker_execution_touched"] is False
    assert report["money_moved"] is False
    assert report["required_actions"][0]["action_id"] == "run_mt5_market_data_diagnostic"
    assert report["required_actions"][0]["can_move_money"] is False


def test_collector_keeps_probing_until_edge_pass_token_exists():
    report = build_waste_paper_sample_collector(
        runner=_runner(),
        mt5_market_data_diagnostic=_diagnostic(ready=True),
        real_candle_probe=_probe(edge_status="NO_TRADE_NULL_FAILED"),
        direction_learning=_learning(confirmed=0),
        direction_outcome_binding=_outcome(confirmed=0),
        mt5_deal_history_ingest=_history(),
    )

    assert report["status"] == STATUS_NEEDS_PASS_TOKEN
    assert report["market_data_ready"] is True
    assert report["probe_edge_status"] == "NO_TRADE_NULL_FAILED"
    assert any(action["action_id"] == "keep_probing_for_pass_token" for action in report["required_actions"])


def test_collector_awaits_paper_execution_after_confirmed_pass_sample():
    report = build_waste_paper_sample_collector(
        runner=_runner(),
        mt5_market_data_diagnostic=_diagnostic(ready=True),
        real_candle_probe=_probe(edge_status="PASS"),
        direction_learning=_learning(confirmed=1),
        direction_outcome_binding=_outcome(confirmed=1, executed=0, bound=0),
        mt5_deal_history_ingest=_history(),
    )

    assert report["status"] == STATUS_AWAITING_PAPER_EXECUTION
    assert report["confirmed_direction_count"] == 1
    assert report["executed_confirmed_count"] == 0
    assert any(action["action_id"] == "finalize_paper_execution_attempt" for action in report["required_actions"])


def test_collector_ready_only_after_bound_profitable_outcomes():
    report = build_waste_paper_sample_collector(
        runner=_runner(),
        mt5_market_data_diagnostic=_diagnostic(ready=True),
        real_candle_probe=_probe(edge_status="PASS"),
        direction_learning=_learning(confirmed=5),
        direction_outcome_binding=_outcome(confirmed=5, executed=5, bound=5, ready=True),
        mt5_deal_history_ingest=_history(closed=5),
    )

    assert report["status"] == STATUS_OUTCOMES_READY
    assert report["sample_collection_complete"] is True
    assert report["bound_outcome_count"] == 5
    assert report["net_paper_pnl"] == 125.0
    assert report["would_enable_live_trading"] is False
    assert report["owner_accept_created"] is False


def test_collection_run_scans_eligible_candidates_until_pass(monkeypatch):
    monkeypatch.setattr(
        "cas_forex.waste_paper_sample_collector._waste_probe_scan_candidates",
        lambda **kwargs: [
            {"symbol": "NAS100", "timeframe": "D1", "lead_id": "lead-1", "source": "test"},
            {"symbol": "US30", "timeframe": "D1", "lead_id": "lead-2", "source": "test"},
            {"symbol": "XAU/USD", "timeframe": "H1", "lead_id": "lead-3", "source": "test"},
        ],
    )
    calls = []

    def fake_probe(**kwargs):
        calls.append((kwargs["symbol"], kwargs["timeframe"]))
        edge_status = "PASS" if kwargs["symbol"] == "US30" else "NO_TRADE_NULL_FAILED"
        return _probe(edge_status=edge_status) | {
            "symbol": kwargs["symbol"],
            "timeframe": kwargs["timeframe"],
            "edge": {
                "status": edge_status,
                "has_edge_token": edge_status == "PASS",
                "measured_win_prob": 0.82 if edge_status == "PASS" else 0.40,
            },
            "broker_grade_market_truth": True,
            "fallback_used": False,
            "candles_count": 180,
            "entry_pair_count": 40,
        }

    report = run_waste_paper_sample_collection_once(
        run_market_diagnostic=False,
        run_real_candle_probe=True,
        run_deal_history_ingest=False,
        real_candle_probe_fn=fake_probe,
        scan_candidates=True,
    )

    assert calls == [("NAS100", "D1"), ("US30", "D1")]
    assert report["paper_only"] is True
    assert report["broker_execution_touched"] is False
    assert report["money_moved"] is False
    assert report["probe_scan"]["report_kind"] == SCAN_REPORT_KIND
    assert report["probe_scan"]["status"] == "WASTE_PROBE_SCAN_PASS_FOUND"
    assert report["probe_scan"]["selected_symbol"] == "US30"
    assert report["probe_scan"]["edge_authorization_registered"] is False
    assert report["after"]["probe_edge_pass_unregistered"] is True


def test_collection_once_refreshes_demo_history_and_outcome_binding_by_default():
    calls = {}

    def fake_history(**kwargs):
        calls["history"] = kwargs
        return _history(closed=1) | {"ingest_status": "DEMO_DEAL_HISTORY_JOINED"}

    def fake_outcome(**kwargs):
        calls["outcome"] = kwargs
        return _outcome(confirmed=1, executed=1, bound=1)

    report = run_waste_paper_sample_collection_once(
        run_market_diagnostic=False,
        run_real_candle_probe=False,
        symbol="NAS100",
        deal_history_ingest_fn=fake_history,
        direction_outcome_binding_fn=fake_outcome,
    )

    assert calls["history"]["symbol"] == "NAS100"
    assert calls["outcome"]["history_report"]["ingest_status"] == "DEMO_DEAL_HISTORY_JOINED"
    assert [action["action_id"] for action in report["actions"]] == [
        "mt5_demo_deal_history_ingest",
        "waste_direction_outcome_binding",
    ]
    assert report["after"]["closed_history_count"] == 1
    assert report["after"]["bound_outcome_count"] == 1
    assert report["broker_execution_touched"] is False
    assert report["live_order_attempted"] is False
    assert report["money_moved"] is False


def test_scheduler_run_once_records_read_only_state_and_audit(tmp_path):
    def fake_run_once(**kwargs):
        return {
            "report_kind": "cas_forex_waste_paper_sample_collection_run",
            "status": STATUS_NEEDS_PASS_TOKEN,
            "paper_only": True,
            "broker_touched": False,
            "broker_execution_touched": False,
            "money_moved": False,
            "after": build_waste_paper_sample_collector(
                runner=_runner(),
                mt5_market_data_diagnostic=_diagnostic(ready=True),
                real_candle_probe=_probe(edge_status="NO_TRADE_NULL_FAILED"),
                direction_learning=_learning(confirmed=0),
                direction_outcome_binding=_outcome(confirmed=0),
                mt5_deal_history_ingest=_history(),
            ),
            "kwargs": kwargs,
        }

    scheduler = WastePaperSampleCollectorScheduler(
        run_once_fn=fake_run_once,
        state_path=tmp_path / "sample-scheduler.json",
        audit_path=tmp_path / "sample-scheduler-audit.jsonl",
    )

    status = scheduler.run_once(symbol="NAS100", run_deal_history_ingest=False)

    assert status["report_kind"] == SCHEDULER_REPORT_KIND
    assert status["status"] == SCHEDULER_STOPPED
    assert status["cycles_run"] == 1
    assert status["latest_collector_status"] == STATUS_NEEDS_PASS_TOKEN
    assert status["config"]["scan_candidates"] is True
    assert status["broker_execution_touched"] is False
    assert status["money_moved"] is False
    assert (tmp_path / "sample-scheduler.json").exists()
    assert (tmp_path / "sample-scheduler-audit.jsonl").exists()


def test_scheduler_run_once_defaults_to_demo_history_ingest(tmp_path):
    def fake_run_once(**kwargs):
        return {
            "report_kind": "cas_forex_waste_paper_sample_collection_run",
            "status": STATUS_AWAITING_PAPER_EXECUTION,
            "paper_only": True,
            "broker_touched": False,
            "broker_execution_touched": False,
            "money_moved": False,
            "after": build_waste_paper_sample_collector(
                runner=_runner(),
                mt5_market_data_diagnostic=_diagnostic(ready=True),
                real_candle_probe=_probe(edge_status="PASS"),
                direction_learning=_learning(confirmed=1),
                direction_outcome_binding=_outcome(confirmed=1, executed=0, bound=0),
                mt5_deal_history_ingest=_history(),
            ),
            "kwargs": kwargs,
        }

    scheduler = WastePaperSampleCollectorScheduler(
        run_once_fn=fake_run_once,
        state_path=tmp_path / "sample-scheduler.json",
        audit_path=tmp_path / "sample-scheduler-audit.jsonl",
    )

    status = scheduler.run_once()

    assert status["config"]["run_deal_history_ingest"] is True
    assert status["latest_run"]["kwargs"]["run_deal_history_ingest"] is True
    assert status["broker_execution_touched"] is False
    assert status["money_moved"] is False


def test_scheduler_start_stop_are_owner_toggleable_without_money_side_effects(tmp_path):
    def fake_run_once(**kwargs):
        return {
            "report_kind": "cas_forex_waste_paper_sample_collection_run",
            "status": STATUS_NEEDS_PASS_TOKEN,
            "paper_only": True,
            "broker_touched": False,
            "broker_execution_touched": False,
            "money_moved": False,
            "after": {"status": STATUS_NEEDS_PASS_TOKEN, "market_data_ready": True},
        }

    scheduler = WastePaperSampleCollectorScheduler(
        run_once_fn=fake_run_once,
        state_path=tmp_path / "sample-scheduler.json",
        audit_path=tmp_path / "sample-scheduler-audit.jsonl",
    )

    started = scheduler.start(interval_seconds=5, symbol="NAS100")
    stopped = scheduler.stop()

    assert started["status"] == SCHEDULER_RUNNING
    assert started["running"] is True
    assert started["config"]["symbol"] == "NAS100"
    assert started["config"]["max_scan_candidates"] == 8
    assert started["would_enable_live_trading"] is False
    assert stopped["status"] == SCHEDULER_STOPPED
    assert stopped["money_moved"] is False


def test_collector_routes_are_registered(monkeypatch):
    monkeypatch.setattr(
        route_module,
        "build_waste_paper_sample_collector",
        lambda: {
            "report_kind": REPORT_KIND,
            "status": STATUS_NEEDS_PASS_TOKEN,
            "paper_only": True,
            "broker_touched": False,
            "money_moved": False,
        },
    )
    monkeypatch.setattr(
        route_module,
        "run_waste_paper_sample_collection_once",
        lambda **kwargs: {
            "report_kind": "cas_forex_waste_paper_sample_collection_run",
            "status": STATUS_NEEDS_PASS_TOKEN,
            "paper_only": True,
            "broker_touched": False,
            "money_moved": False,
            "kwargs": kwargs,
        },
    )
    monkeypatch.setattr(
        route_module,
        "waste_paper_sample_collector_scheduler_status",
        lambda: {
            "report_kind": SCHEDULER_REPORT_KIND,
            "status": SCHEDULER_STOPPED,
            "running": False,
            "paper_only": True,
            "broker_execution_touched": False,
            "money_moved": False,
        },
    )
    monkeypatch.setattr(
        route_module,
        "run_waste_paper_sample_collector_scheduler_once",
        lambda **kwargs: {
            "report_kind": SCHEDULER_REPORT_KIND,
            "status": SCHEDULER_STOPPED,
            "running": False,
            "paper_only": True,
            "broker_execution_touched": False,
            "money_moved": False,
            "kwargs": kwargs,
        },
    )
    monkeypatch.setattr(
        route_module,
        "start_waste_paper_sample_collector_scheduler",
        lambda **kwargs: {
            "report_kind": SCHEDULER_REPORT_KIND,
            "status": SCHEDULER_RUNNING,
            "running": True,
            "paper_only": True,
            "broker_execution_touched": False,
            "money_moved": False,
            "kwargs": kwargs,
        },
    )
    monkeypatch.setattr(
        route_module,
        "stop_waste_paper_sample_collector_scheduler",
        lambda: {
            "report_kind": SCHEDULER_REPORT_KIND,
            "status": SCHEDULER_STOPPED,
            "running": False,
            "paper_only": True,
            "broker_execution_touched": False,
            "money_moved": False,
        },
    )
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/waste-loop-control")
    client = TestClient(app)

    get_response = client.get("/api/forex/waste-loop-control/paper-sample-collector")
    post_response = client.post(
        "/api/forex/waste-loop-control/paper-sample-collector/run-once",
        json={"symbol": "NAS100", "run_deal_history_ingest": False},
    )
    scheduler_response = client.get("/api/forex/waste-loop-control/paper-sample-collector/scheduler")
    scheduler_once_response = client.post(
        "/api/forex/waste-loop-control/paper-sample-collector/scheduler/run-once",
        json={"symbol": "NAS100", "run_deal_history_ingest": False},
    )
    scheduler_start_response = client.post(
        "/api/forex/waste-loop-control/paper-sample-collector/scheduler/start",
        json={"symbol": "NAS100", "interval_seconds": 30, "scan_candidates": False},
    )
    scheduler_stop_response = client.post("/api/forex/waste-loop-control/paper-sample-collector/scheduler/stop")

    assert get_response.status_code == 200
    assert get_response.json()["report_kind"] == REPORT_KIND
    assert post_response.status_code == 200
    assert post_response.json()["report_kind"] == "cas_forex_waste_paper_sample_collection_run"
    assert post_response.json()["kwargs"]["symbol"] == "NAS100"
    assert post_response.json()["kwargs"]["scan_candidates"] is True
    assert scheduler_response.status_code == 200
    assert scheduler_response.json()["report_kind"] == SCHEDULER_REPORT_KIND
    assert scheduler_once_response.status_code == 200
    assert scheduler_once_response.json()["kwargs"]["symbol"] == "NAS100"
    assert scheduler_once_response.json()["kwargs"]["max_scan_candidates"] == 8
    assert scheduler_start_response.status_code == 200
    assert scheduler_start_response.json()["running"] is True
    assert scheduler_start_response.json()["kwargs"]["scan_candidates"] is False
    assert scheduler_stop_response.status_code == 200
    assert scheduler_stop_response.json()["running"] is False
