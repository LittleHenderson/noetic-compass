"""Strategy-development queue coverage."""

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
from cas_forex.strategy_dev_queue import (
    build_strategy_dev_queue_report,
    load_latest_strategy_dev_queue_report,
)


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


def test_strategy_dev_queue_builds_work_items_from_research_tasks(tmp_path):
    cycle = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=tmp_path / "mailbox")
    memory = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
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
    item_types = {item["item_type"] for item in queue["work_items"]}

    assert queue["queue_status"] == "STRATEGY_DEV_QUEUE_BUILT"
    assert "TERMINAL_JOINBACK_WORKFLOW" in item_types
    assert "OVERSEER_RULE_PATCH_CANDIDATE" in item_types
    assert "CONDITION_LAB_REPLAY_REQUEST" in item_types
    assert "WALK_FORWARD_TERMINAL_REPLAY_REQUEST" in item_types
    assert queue["summary"]["source_task_count"] == research["summary"]["task_count"]
    assert queue["summary"]["terminal_blocked_count"] >= 1
    assert queue["work_items"][0]["priority"] == 1
    assert "do not by themselves execute live broker orders" in queue["claim_boundary"]

    latest = load_latest_strategy_dev_queue_report(tmp_path / "strategy-dev-queue")
    assert latest["summary"]["item_count"] == queue["summary"]["item_count"]


def test_strategy_dev_queue_creates_reviews_from_closed_memory_rows(tmp_path):
    memory = {
        "summary": {
            "memory_record_count": 2,
            "pending_receipt_count": 0,
            "terminal_history_joined_count": 2,
            "closed_profit_count": 1,
            "closed_loss_count": 1,
        },
        "memory_records": [
            {
                "memory_id": "memory-profit-1",
                "outcome_label": "TRADE_CLOSED_PROFIT",
                "profit_loss_account": 42.5,
                "symbol": "AUD/CAD",
                "timeframe": "M5",
                "action": "OPEN_MICRO_SCALP",
                "agent_id": "micro_scalp_agent",
                "strategy_setting": "forex_fury_range_scalper",
                "source_refs": [],
            },
            {
                "memory_id": "memory-loss-1",
                "outcome_label": "TRADE_CLOSED_LOSS",
                "profit_loss_account": -11.0,
                "symbol": "AUD/CAD",
                "timeframe": "M5",
                "action": "OPEN_MICRO_SCALP",
                "agent_id": "micro_scalp_agent",
                "strategy_setting": "forex_fury_range_scalper",
                "source_refs": [],
            },
        ],
    }
    research = {
        "summary": {"task_count": 0},
        "research_tasks": [],
    }

    queue = build_strategy_dev_queue_report(
        research_queue_report=research,
        memory_report=memory,
        output_dir=tmp_path / "strategy-dev-queue",
    )
    item_types = {item["item_type"] for item in queue["work_items"]}

    assert "CLOSED_PROFIT_PROMOTION_REVIEW" in item_types
    assert "CLOSED_LOSS_DEMOTION_REVIEW" in item_types
    assert queue["summary"]["promotion_review_count"] == 1
    assert queue["summary"]["demotion_review_count"] == 1
    assert queue["summary"]["closed_profit_memory_count"] == 1
    assert queue["summary"]["closed_loss_memory_count"] == 1


def test_strategy_dev_queue_api_and_dashboard_surface_latest_report(tmp_path, monkeypatch):
    cycle = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=tmp_path / "mailbox")
    memory = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
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
    monkeypatch.setattr(api_data, "strategy_dev_queue_latest", lambda: queue)
    monkeypatch.setattr(strategy_routes, "strategy_dev_queue_latest", lambda: queue)

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/strategy-dev-queue/latest"))
    assert status == 200
    assert body["queue_status"] == "STRATEGY_DEV_QUEUE_BUILT"
    assert body["summary"]["item_count"] >= 4

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "strategyDevQueue" in dashboard
    assert dashboard["strategyDevQueue"]["summary"]["item_count"] >= 4
