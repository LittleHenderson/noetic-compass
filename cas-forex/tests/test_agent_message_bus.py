"""CAS Forex append-only agent event journal coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import api.routes.strategy as strategy_routes
from api.server import app
from cas_forex.agent_message_bus import (
    AgentEventStore,
    EVENT_SCHEMA,
    load_agent_events,
    load_latest_agent_context,
    load_open_agent_intents,
    make_agent_event,
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


def test_agent_event_store_appends_and_filters_events(tmp_path):
    store = AgentEventStore(tmp_path / "agent-events.jsonl")
    event = make_agent_event(
        cycle_id="cycle-test",
        producer_agent_id="micro_scalp_agent",
        consumer_agent_ids=["overseer_agent"],
        event_type="ROUTE_INTENT_CREATED",
        subject="AUD/CAD",
        symbol="AUD/CAD",
        timeframe="M5",
        strategy_setting="range_scalper_12_80",
        payload={"intent_id": "intent-1", "action": "OPEN_MICRO_SCALP"},
        status="PROPOSED",
    )

    store.append_event(event)
    events = store.read_events(cycle_id="cycle-test")

    assert len(events) == 1
    assert events[0]["schema"] == EVENT_SCHEMA
    assert events[0]["event_type"] == "ROUTE_INTENT_CREATED"
    assert store.summary()["event_type_counts"]["ROUTE_INTENT_CREATED"] == 1
    assert store.open_intents()[0]["payload"]["intent_id"] == "intent-1"


def test_agent_workflow_cycle_writes_append_only_event_journal(tmp_path):
    report = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=tmp_path / "mailbox")
    event_journal = report["event_journal"]
    events_payload = load_agent_events(
        cycle_id=report["cycle_id"],
        event_log_path=event_journal["event_log_path"],
    )
    events = events_payload["events"]
    event_types = {event["event_type"] for event in events}

    assert event_journal["appended_event_count"] == len(events)
    assert "AGENT_CONTEXT_READY" in event_types
    assert "ROUTE_INTENT_CREATED" in event_types
    assert "OVERSEER_DECISION_CREATED" in event_types
    assert "TERMINAL_COMMAND_WRITTEN" in event_types
    assert "TERMINAL_RECEIPT_PENDING" in event_types
    assert event_journal["pending_receipt_count"] >= 1


def test_agent_message_bus_api_surfaces_summary_and_events(monkeypatch, tmp_path):
    report = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=tmp_path / "mailbox")
    event_log_path = report["event_journal"]["event_log_path"]
    monkeypatch.setattr(strategy_routes, "agent_message_bus_summary", lambda: report["event_journal"])
    monkeypatch.setattr(
        strategy_routes,
        "agent_workflow_events",
        lambda cycle_id=None, after_event_id=None, limit=500: load_agent_events(
            cycle_id=cycle_id,
            after_event_id=after_event_id,
            limit=limit,
            event_log_path=event_log_path,
        ),
    )
    monkeypatch.setattr(
        strategy_routes,
        "agent_workflow_context_latest",
        lambda: load_latest_agent_context(event_log_path=event_log_path),
    )
    monkeypatch.setattr(
        strategy_routes,
        "agent_workflow_intents_open",
        lambda: load_open_agent_intents(event_log_path=event_log_path),
    )

    status, summary = asyncio.run(_asgi_get("/api/forex/strategy/agent-workflow-events/summary"))
    assert status == 200
    assert summary["event_count"] >= report["event_journal"]["appended_event_count"]
    assert summary["pending_receipt_count"] >= 1

    status, events = asyncio.run(_asgi_get(f"/api/forex/strategy/agent-workflow-events?cycle_id={report['cycle_id']}"))
    assert status == 200
    assert events["events"]
    assert events["events"][0]["cycle_id"] == report["cycle_id"]

    status, context = asyncio.run(_asgi_get("/api/forex/strategy/agent-workflow-context/latest"))
    assert status == 200
    assert context["event"]["event_type"] == "AGENT_CONTEXT_READY"

    status, intents = asyncio.run(_asgi_get("/api/forex/strategy/agent-workflow-intents/open"))
    assert status == 200
    assert "open_intents" in intents
