"""CAS Forex agentic trading-day workflow coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api.server import app
from cas_forex.agent_workflow import build_agent_workflow_plan


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


def test_agent_workflow_defines_autowake_scalp_hourly_and_research_agents():
    report = build_agent_workflow_plan(
        forex_fury_replay_results={
            "report_kind": "cas_forex_forex_fury_replay_results",
            "replay_verdict": "REPLAY_LEAD_FOR_ADAPTIVE_REVIEW",
            "adaptive_compounding_next_step": "QUEUE_FOR_ADAPTIVE_COMPOUNDING_REVIEW",
            "condition_summary": {
                "top_condition_cells": [
                    {
                        "symbol": "AUD/CAD",
                        "timeframe": "M5",
                        "setting": "range_scalper_12_80",
                        "mean_return_pct": 1.2845,
                        "profit_factor": 20.7614,
                        "win_rate": 0.9722,
                    }
                ]
            },
        }
    )

    agent_ids = {agent["agent_id"] for agent in report["agent_roster"]}
    assert "session_autowake_agent" in agent_ids
    assert "micro_scalp_agent" in agent_ids
    assert "hourly_intraday_agent" in agent_ids
    assert "overseer_agent" in agent_ids
    assert "research_condition_agent" in agent_ids
    assert "audit_memory_agent" in agent_ids
    assert report["summary"]["primary_replay_lead"] == "AUD/CAD M5 range_scalper_12_80"
    assert report["summary"]["micro_scalp_cadence_minutes"] == "1-5"
    assert report["summary"]["hourly_intraday_cadence_minutes"] == 60
    assert any(event["event_id"] == "FX_WEEK_OPEN_PRECHECK" for event in report["autowake_schedule"]["events"])
    assert any(event["event_id"] == "MICRO_SCALP_LOOP" for event in report["autowake_schedule"]["events"])


def test_agent_workflow_has_shared_knowledge_pack_and_live_boundary():
    report = build_agent_workflow_plan()
    paths = {item["path"] for item in report["knowledge_pack"]}
    assert "strategy_leads.json" in paths
    assert any("forex_fury_replay_results" in path for path in paths)
    assert any("cas_harness_production_todo.md" in path for path in paths)
    assert "does not by itself execute live broker orders" in report["claim_boundary"]
    assert "order_dispatch.py" in report["claim_boundary"]
    assert report["live_execution_boundary"]["live_trading_status"] == "OWNER_ARMING_REQUIRED"
    overseer = next(agent for agent in report["agent_roster"] if agent["agent_id"] == "overseer_agent")
    assert "proposal conflicts with current exposure" in overseer["must_reject_conditions"]
    assert "APPROVE_ROUTE_INTENT" in overseer["decision_outputs"]


def test_agent_workflow_route_and_dashboard_surface_latest_report():
    status, body = asyncio.run(_asgi_get("/api/forex/strategy/agent-workflow-plan"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_agent_workflow_plan"
    assert body["summary"]["agent_count"] >= 8
    assert body["summary"]["micro_scalp_cadence_minutes"] == "1-5"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "agentWorkflowPlan" in dashboard
    assert dashboard["agentWorkflowPlan"]["workflow_status"] == "AGENT_DESK_PLAN_READY"
