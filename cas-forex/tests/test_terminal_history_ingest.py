"""Terminal close-history ingest coverage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

import api.server as api_server
import api.routes.strategy as strategy_routes
from api.server import app
from cas_forex.agent_memory import build_agent_memory_report
from cas_forex.agent_state import run_agent_workflow_cycle
from cas_forex.terminal_history_ingest import (
    ingest_terminal_history,
    load_latest_terminal_history_ingest_report,
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


def test_terminal_history_ingest_joins_closed_trade_to_memory(tmp_path):
    mailbox_dir = tmp_path / "mailbox"
    cycle_dir = tmp_path / "cycles"
    cycle = run_agent_workflow_cycle(output_dir=cycle_dir, mailbox_dir=mailbox_dir)
    command = cycle["terminal_commands"][0]
    command_payload = json.loads(Path(command["command_path"]).read_text(encoding="utf-8"))
    order = command_payload["order"]

    memory = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "agent-memory-before-history",
    )
    source_path = tmp_path / "terminal-history" / "closed-trades.json"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        json.dumps(
            [
                {
                    "command_id": command["command_id"],
                    "ticket": "777001",
                    "symbol": order["symbol"],
                    "direction": "buy",
                    "lots": order["volume"],
                    "open_time": "2026-06-24T10:00:00Z",
                    "close_time": "2026-06-24T10:04:00Z",
                    "open_price": 0.8990,
                    "close_price": 0.9002,
                    "stop_loss": order["stop_loss"],
                    "take_profit": order["take_profit"],
                    "profit": 42.5,
                    "commission": -1.25,
                    "swap": 0.1,
                    "mae": 2.5,
                    "mfe": 14.8,
                    "close_reason": "TAKE_PROFIT_OR_AI_EXIT",
                    "broker_mode": "PAPER_MT4",
                }
            ]
        ),
        encoding="utf-8",
    )

    ingest = ingest_terminal_history(
        source_paths=[source_path],
        memory_report=memory,
        output_dir=tmp_path / "terminal-history-ingest",
    )
    update = ingest["memory_updates"][0]

    assert ingest["summary"]["memory_update_count"] == 1
    assert ingest["summary"]["closed_profit_count"] == 1
    assert update["match_method"] == "command_id"
    assert update["terminal_history_status"] == "CLOSED_HISTORY_JOINED"
    assert update["profit_loss_pips"] == pytest.approx(12.0)
    assert update["outcome_label"] == "TRADE_CLOSED_PROFIT"

    latest = load_latest_terminal_history_ingest_report(tmp_path / "terminal-history-ingest")
    assert latest["summary"]["memory_update_count"] == 1

    enriched = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
        terminal_history_report_dir=tmp_path / "terminal-history-ingest",
        output_dir=tmp_path / "agent-memory-after-history",
    )
    closed = [record for record in enriched["memory_records"] if record.get("terminal_history_status") == "CLOSED_HISTORY_JOINED"]

    assert enriched["summary"]["terminal_history_joined_count"] == 1
    assert enriched["summary"]["closed_profit_count"] == 1
    assert enriched["summary"]["net_profit_loss_account"] == pytest.approx(42.5)
    assert closed[0]["outcome_label"] == "TRADE_CLOSED_PROFIT"
    assert closed[0]["learning_status"] == "READY_FOR_RESEARCH"
    assert closed[0]["condition_snapshot_close"]["closed_at"] == "2026-06-24T10:04:00Z"
    assert closed[0]["condition_snapshot_close"]["profit_loss_pips"] == pytest.approx(12.0)


def test_terminal_history_ingest_api_and_dashboard_surface(monkeypatch, tmp_path):
    empty_dir = tmp_path / "empty-history"
    empty_dir.mkdir()
    report = ingest_terminal_history(
        source_paths=[empty_dir],
        memory_report={"summary": {}, "memory_records": []},
        output_dir=tmp_path / "terminal-history-ingest",
        write_report=False,
    )

    monkeypatch.setattr(strategy_routes, "terminal_history_ingest_latest", lambda: report)
    monkeypatch.setattr(api_server, "dashboard_state", lambda: {"terminalHistoryIngest": report})

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/terminal-history-ingest/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_terminal_history_ingest"
    assert body["ingest_status"] == "TERMINAL_HISTORY_EMPTY"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["terminalHistoryIngest"]["summary"]["history_record_count"] == 0
