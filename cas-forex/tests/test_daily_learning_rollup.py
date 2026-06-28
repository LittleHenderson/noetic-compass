"""Daily learning rollup coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api import data as api_data
from api.routes import strategy as strategy_routes
from api.server import app
from cas_forex.agent_memory import build_agent_memory_report
from cas_forex.agent_research_queue import build_agent_research_queue_report
from cas_forex.agent_state import run_agent_workflow_cycle
from cas_forex.daily_learning_rollup import (
    build_daily_learning_rollup_report,
    load_latest_daily_learning_rollup_report,
)
from cas_forex.strategy_dev_queue import build_strategy_dev_queue_report
from cas_forex.strategy_patch_runner import build_strategy_patch_runner_report
from cas_forex.terminal_history_ingest import ingest_terminal_history


async def _asgi_get(path: str) -> tuple[int, dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return int(status), json.loads(body.decode("utf-8"))


def _build_chain(tmp_path):
    cycle = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=tmp_path / "mailbox")
    terminal_history = ingest_terminal_history(
        source_paths=[],
        memory_report={"memory_records": []},
        output_dir=tmp_path / "terminal-history",
    )
    memory = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
        terminal_history_report_dir=tmp_path / "terminal-history",
        output_dir=tmp_path / "agent-memory",
    )
    research = build_agent_research_queue_report(
        memory_report=memory,
        output_dir=tmp_path / "agent-research-queue",
    )
    queue = build_strategy_dev_queue_report(
        research_queue_report=research,
        memory_report=memory,
        output_dir=tmp_path / "strategy-dev-queue",
    )
    patch = build_strategy_patch_runner_report(
        strategy_dev_queue_report=queue,
        output_dir=tmp_path / "strategy-patch-runner",
    )
    return cycle, memory, terminal_history, research, queue, patch


def test_daily_learning_rollup_builds_from_agent_chain(tmp_path):
    cycle, memory, terminal_history, research, queue, patch = _build_chain(tmp_path)

    rollup = build_daily_learning_rollup_report(
        agent_cycle_report=cycle,
        memory_report=memory,
        terminal_history_report=terminal_history,
        research_queue_report=research,
        strategy_dev_queue_report=queue,
        strategy_patch_runner_report=patch,
        output_dir=tmp_path / "daily-learning-rollup",
    )

    assert rollup["rollup_status"] == "DAILY_LEARNING_ROLLUP_BUILT_WAITING_FOR_CLOSED_PNL"
    assert rollup["summary"]["route_count"] == memory["summary"]["route_intent_count"]
    assert rollup["summary"]["patch_decision_count"] == patch["summary"]["decision_count"]
    assert rollup["summary"]["pending_receipt_count"] >= 1
    assert rollup["summary"]["chain_verified"] is True
    assert rollup["terminal_blockers"]
    assert "claim live-income readiness" in rollup["claim_boundary"]

    latest = load_latest_daily_learning_rollup_report(tmp_path / "daily-learning-rollup")
    assert latest["summary"]["route_count"] == rollup["summary"]["route_count"]


def test_daily_learning_rollup_computes_closed_pnl_math(tmp_path):
    memory = {
        "report_kind": "cas_forex_agent_memory_report",
        "created_at": "2026-06-24T12:00:00+00:00",
        "summary": {
            "route_intent_count": 2,
            "approved_count": 2,
            "rejected_count": 0,
            "command_joined_count": 2,
            "pending_receipt_count": 0,
            "closed_trade_count": 2,
            "closed_profit_count": 1,
            "closed_loss_count": 1,
            "closed_flat_count": 0,
            "net_profit_loss_account": 31.5,
        },
        "memory_records": [
            {
                "memory_id": "profit-row",
                "created_at": "2026-06-24T12:00:00+00:00",
                "agent_id": "micro_scalp_agent",
                "symbol": "AUD/CAD",
                "timeframe": "M5",
                "strategy_setting": "range_scalper_12_80",
                "action": "OPEN_MICRO_SCALP",
                "decision_approved": True,
                "outcome_label": "TRADE_CLOSED_PROFIT",
                "profit_loss_account": 42.5,
                "promotion_signal": "PROMOTION_REVIEW",
                "demotion_flags": [],
            },
            {
                "memory_id": "loss-row",
                "created_at": "2026-06-24T12:05:00+00:00",
                "agent_id": "micro_scalp_agent",
                "symbol": "AUD/CAD",
                "timeframe": "M5",
                "strategy_setting": "range_scalper_12_80",
                "action": "OPEN_MICRO_SCALP",
                "decision_approved": True,
                "outcome_label": "TRADE_CLOSED_LOSS",
                "profit_loss_account": -11.0,
                "promotion_signal": "HOLD",
                "demotion_flags": ["loss_review"],
            },
        ],
    }
    patch = {
        "report_kind": "cas_forex_strategy_patch_runner_report",
        "summary": {"decision_count": 0},
        "decisions": [],
    }

    rollup = build_daily_learning_rollup_report(
        trading_date="2026-06-24",
        agent_cycle_report={"report_kind": "cas_forex_agent_workflow_cycle", "summary": {}},
        memory_report=memory,
        terminal_history_report={"report_kind": "cas_forex_terminal_history_ingest", "summary": {"history_record_count": 2}},
        research_queue_report={"report_kind": "cas_forex_agent_research_queue_report", "summary": {}, "research_tasks": []},
        strategy_dev_queue_report={"report_kind": "cas_forex_strategy_dev_queue_report", "summary": {}, "work_items": []},
        strategy_patch_runner_report=patch,
        output_dir=tmp_path / "daily-learning-rollup",
    )

    assert rollup["rollup_status"] == "DAILY_LEARNING_ROLLUP_BUILT"
    assert rollup["summary"]["net_profit_loss_account"] == 31.5
    assert rollup["summary"]["profit_factor"] == 3.863636
    assert rollup["summary"]["expectancy_account"] == 15.75
    assert rollup["by_agent"][0]["net_profit_loss_account"] == 31.5
    assert rollup["promotion_candidates"]
    assert rollup["demotion_flags"]


def test_daily_learning_rollup_api_and_dashboard_surface_latest_report(tmp_path, monkeypatch):
    cycle, memory, terminal_history, research, queue, patch = _build_chain(tmp_path)
    rollup = build_daily_learning_rollup_report(
        agent_cycle_report=cycle,
        memory_report=memory,
        terminal_history_report=terminal_history,
        research_queue_report=research,
        strategy_dev_queue_report=queue,
        strategy_patch_runner_report=patch,
        output_dir=tmp_path / "daily-learning-rollup",
    )
    monkeypatch.setattr(api_data, "daily_learning_rollup_latest", lambda: rollup)
    monkeypatch.setattr(strategy_routes, "daily_learning_rollup_latest", lambda: rollup)

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/daily-learning-rollup/latest"))
    assert status == 200
    assert body["summary"]["patch_decision_count"] == patch["summary"]["decision_count"]

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "dailyLearningRollup" in dashboard
    assert dashboard["dailyLearningRollup"]["summary"]["route_count"] == rollup["summary"]["route_count"]
