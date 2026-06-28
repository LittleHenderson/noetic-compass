"""Session autowake runner coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api import data as api_data
from api.routes import strategy as strategy_routes
from api.server import app
from cas_forex.agent_workflow import build_agent_workflow_plan
from cas_forex.session_autowake_runner import (
    build_session_autowake_report,
    load_latest_session_autowake_report,
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


def _rollup() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_daily_learning_rollup_report",
        "rollup_status": "DAILY_LEARNING_ROLLUP_BUILT_WAITING_FOR_CLOSED_PNL",
        "summary": {
            "route_count": 62,
            "pending_receipt_count": 28,
            "closed_count": 0,
            "readiness_label": "WAITING_FOR_TERMINAL_CLOSE_HISTORY",
        },
        "terminal_blockers": [
            {
                "blocker_id": "pending_terminal_receipts",
                "count": 28,
                "plain_english": "MT4/MT5 command rows are still waiting for terminal receipt JSON.",
            }
        ],
    }


def test_session_autowake_runner_marks_due_market_open_events(tmp_path):
    report = build_session_autowake_report(
        now="2026-06-24T13:00:00+00:00",
        workflow_plan=build_agent_workflow_plan(),
        daily_learning_rollup=_rollup(),
        output_dir=tmp_path / "autowake",
    )
    due_events = {event["event_id"]: event for event in report["event_evaluations"] if event["due"]}

    assert report["autowake_status"] == "SESSION_AUTOWAKE_READY"
    assert report["session_state"]["market_open"] is True
    assert report["session_state"]["active_session"] == "LONDON_NEW_YORK_OVERLAP"
    assert "MICRO_SCALP_LOOP" in due_events
    assert "HOURLY_INTRADAY_LOOP" in due_events
    assert due_events["MICRO_SCALP_LOOP"]["terminal_blocked"] is True
    assert report["summary"]["pending_receipt_count"] == 28
    assert "override terminal receipt/history blockers" in report["claim_boundary"]

    latest = load_latest_session_autowake_report(tmp_path / "autowake")
    assert latest["summary"]["due_event_count"] == report["summary"]["due_event_count"]


def test_session_autowake_runner_stands_by_when_market_closed(tmp_path):
    report = build_session_autowake_report(
        now="2026-06-27T13:00:00+00:00",
        workflow_plan=build_agent_workflow_plan(),
        daily_learning_rollup=_rollup(),
        output_dir=tmp_path / "autowake",
    )

    assert report["autowake_status"] == "SESSION_AUTOWAKE_STANDBY_MARKET_CLOSED"
    assert report["summary"]["market_open"] is False
    assert report["summary"]["due_event_count"] == 0
    assert all(event["status"] == "STANDBY_MARKET_CLOSED" for event in report["event_evaluations"])


def test_session_autowake_runner_can_execute_one_paper_cycle_with_injected_runner(tmp_path):
    def fake_cycle_runner(**kwargs):
        return {
            "cycle_id": "cycle-from-test",
            "execution_mode": "PAPER_MT4_COMMAND_INTENT",
            "summary": {"route_intent_count": 2, "terminal_command_count": 0},
            "artifact_paths": {"json": str(tmp_path / "cycle.json")},
            "state_path": str(tmp_path / "state.jsonl"),
        }

    report = build_session_autowake_report(
        now="2026-06-24T13:00:00+00:00",
        workflow_plan=build_agent_workflow_plan(),
        daily_learning_rollup=_rollup(),
        execute_cycle=True,
        write_terminal_commands=False,
        cycle_runner=fake_cycle_runner,
        output_dir=tmp_path / "autowake",
    )

    assert report["autowake_status"] == "SESSION_AUTOWAKE_CYCLE_EXECUTED"
    assert report["summary"]["executed_cycle_count"] == 1
    assert report["summary"]["executed_cycle_id"] == "cycle-from-test"
    assert report["executed_cycle"]["summary"]["terminal_command_count"] == 0


def test_session_autowake_runner_api_and_dashboard_surface_latest_report(tmp_path, monkeypatch):
    report = build_session_autowake_report(
        now="2026-06-24T13:00:00+00:00",
        workflow_plan=build_agent_workflow_plan(),
        daily_learning_rollup=_rollup(),
        output_dir=tmp_path / "autowake",
    )
    monkeypatch.setattr(api_data, "session_autowake_latest", lambda: report)
    monkeypatch.setattr(strategy_routes, "session_autowake_latest", lambda: report)

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/session-autowake/latest"))
    assert status == 200
    assert body["summary"]["due_event_count"] >= 2

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "sessionAutowake" in dashboard
    assert dashboard["sessionAutowake"]["session_state"]["market_open"] is True
