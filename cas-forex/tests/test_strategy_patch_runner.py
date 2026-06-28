"""Strategy patch-runner coverage."""

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
from cas_forex.strategy_dev_queue import build_strategy_dev_queue_report
from cas_forex.strategy_patch_runner import (
    build_strategy_patch_runner_report,
    load_latest_strategy_patch_runner_report,
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


def test_strategy_patch_runner_builds_decisions_from_strategy_dev_queue(tmp_path):
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

    runner = build_strategy_patch_runner_report(
        strategy_dev_queue_report=queue,
        output_dir=tmp_path / "strategy-patch-runner",
    )
    decision_types = {decision["decision_type"] for decision in runner["decisions"]}

    assert runner["runner_status"] == "STRATEGY_PATCH_RUNNER_READY"
    assert "PATCH_CANDIDATE" in decision_types
    assert "REPLAY_JOB" in decision_types
    assert "TERMINAL_INPUT_REQUIRED" in decision_types
    assert runner["summary"]["source_item_count"] == queue["summary"]["item_count"]
    assert runner["summary"]["patch_candidate_count"] >= 1
    assert runner["summary"]["replay_job_count"] >= 1
    assert runner["summary"]["blocked_decision_count"] >= 1
    assert "silently modify live strategy code" in runner["claim_boundary"]

    latest = load_latest_strategy_patch_runner_report(tmp_path / "strategy-patch-runner")
    assert latest["summary"]["decision_count"] == runner["summary"]["decision_count"]


def test_strategy_patch_runner_creates_promotion_and_demotion_decisions(tmp_path):
    queue = {
        "summary": {"item_count": 2, "blocked_item_count": 0, "patch_candidate_count": 0},
        "work_items": [
            {
                "item_id": "profit-review",
                "item_type": "CLOSED_PROFIT_PROMOTION_REVIEW",
                "priority": 1,
                "status": "READY_FOR_PROMOTION_REVIEW",
                "source_task_ids": [],
                "source_memory_ids": ["memory-profit-1"],
                "symbols": ["AUD/CAD"],
                "timeframes": ["M5"],
                "plain_english_goal": "Promote profitable bucket.",
                "proposed_change": "Review compounding and frequency.",
                "replay_request": {},
                "promotion_review": {"review_type": "PROMOTION"},
                "required_inputs": ["closed profit memory rows"],
                "blocked_by": [],
                "acceptance_checks": ["profit survives replay"],
                "source_counts": {},
            },
            {
                "item_id": "loss-review",
                "item_type": "CLOSED_LOSS_DEMOTION_REVIEW",
                "priority": 1,
                "status": "QUEUED_FOR_PATCH_REVIEW",
                "source_task_ids": [],
                "source_memory_ids": ["memory-loss-1"],
                "symbols": ["AUD/CAD"],
                "timeframes": ["M5"],
                "plain_english_goal": "Demote losing bucket.",
                "proposed_change": "Review stop and timing filters.",
                "replay_request": {},
                "promotion_review": {"review_type": "DEMOTION"},
                "required_inputs": ["closed loss memory rows"],
                "blocked_by": [],
                "acceptance_checks": ["loss cause is named"],
                "source_counts": {},
            },
        ],
    }

    runner = build_strategy_patch_runner_report(
        strategy_dev_queue_report=queue,
        output_dir=tmp_path / "strategy-patch-runner",
    )

    assert runner["summary"]["promotion_review_count"] == 1
    assert runner["summary"]["demotion_review_count"] == 1
    assert {decision["status"] for decision in runner["decisions"]} == {
        "PROMOTION_REVIEW_READY",
        "DEMOTION_REVIEW_READY",
    }


def test_strategy_patch_runner_api_and_dashboard_surface_latest_report(tmp_path, monkeypatch):
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
    runner = build_strategy_patch_runner_report(
        strategy_dev_queue_report=queue,
        output_dir=tmp_path / "strategy-patch-runner",
    )
    monkeypatch.setattr(api_data, "strategy_patch_runner_latest", lambda: runner)
    monkeypatch.setattr(strategy_routes, "strategy_patch_runner_latest", lambda: runner)

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/strategy-patch-runner/latest"))
    assert status == 200
    assert body["runner_status"] == "STRATEGY_PATCH_RUNNER_READY"
    assert body["summary"]["decision_count"] >= 4

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "strategyPatchRunner" in dashboard
    assert dashboard["strategyPatchRunner"]["summary"]["decision_count"] >= 4
