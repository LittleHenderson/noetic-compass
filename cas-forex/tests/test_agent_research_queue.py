"""Agent research queue coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api import data as api_data
from api.server import app
from api.routes import strategy as strategy_routes
from cas_forex.agent_memory import build_agent_memory_report
from cas_forex.agent_research_queue import (
    build_agent_research_queue_report,
    load_latest_agent_research_queue_report,
)
from cas_forex.agent_state import run_agent_workflow_cycle


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


def test_agent_research_queue_builds_tasks_from_memory(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle_dir = tmp_path / "cycles"
    cycle = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)
    memory = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "agent-memory",
    )

    queue = build_agent_research_queue_report(
        memory_report=memory,
        output_dir=tmp_path / "agent-research-queue",
    )
    task_types = {task["task_type"] for task in queue["research_tasks"]}

    assert queue["queue_status"] == "AGENT_RESEARCH_QUEUE_BUILT"
    assert "TERMINAL_RECEIPT_JOINBACK" in task_types
    assert "OVERSEER_CONFLICT_KEY_REFINEMENT" in task_types
    assert "CONDITION_LAB_REJECTION_ANALYSIS" in task_types
    assert "WALK_FORWARD_RECEIPT_REPLAY" in task_types
    assert queue["summary"]["source_memory_count"] == memory["summary"]["memory_record_count"]
    assert queue["summary"]["terminal_receipt_task_count"] == 1
    assert queue["research_tasks"][0]["priority"] == 1
    assert "do not by themselves execute live broker orders" in queue["claim_boundary"]
    assert "order_dispatch.py" in queue["claim_boundary"]

    latest = load_latest_agent_research_queue_report(tmp_path / "agent-research-queue")
    assert latest["summary"]["task_count"] == queue["summary"]["task_count"]


def test_agent_research_queue_api_and_dashboard_surface_latest_report(tmp_path, monkeypatch):
    mailbox_dir = tmp_path / "mailbox"
    cycle_dir = tmp_path / "cycles"
    cycle = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)
    memory = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "agent-memory",
    )
    queue = build_agent_research_queue_report(
        memory_report=memory,
        output_dir=tmp_path / "agent-research-queue",
    )
    monkeypatch.setattr(api_data, "agent_research_queue_latest", lambda: queue)
    monkeypatch.setattr(strategy_routes, "agent_research_queue_latest", lambda: queue)

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/agent-research-queue/latest"))
    assert status == 200
    assert body["queue_status"] == "AGENT_RESEARCH_QUEUE_BUILT"
    assert body["summary"]["task_count"] >= 4

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "agentResearchQueue" in dashboard
    assert dashboard["agentResearchQueue"]["summary"]["task_count"] >= 4
