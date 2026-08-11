"""Tests for the /api/forex/agent-decision/history route."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from urllib.parse import urlsplit

import pytest

from api.server import app
from api.routes import agent_decision_history as route_module


async def _asgi_get(path: str) -> tuple[int, Any]:
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
    payload = json.loads(body.decode("utf-8")) if body else None
    return int(status), payload


@pytest.fixture(autouse=True)
def _reset_loader_between_tests():
    route_module.reset_loader_for_testing()
    yield
    route_module.reset_loader_for_testing()


def _empty_context() -> dict[str, Any]:
    return {
        "agent_memory_report": None,
        "daily_learning_rollup": None,
        "strategy_dev_queue_report": None,
        "strategy_leads": None,
        "walk_forward_report": None,
        "pcba_report": None,
    }


def _make_cycle_report(cycle_id: str) -> dict[str, Any]:
    return {
        "cycle_id": cycle_id,
        "route_intents": [],
        "overseer_decisions": [],
        "terminal_commands": [],
    }


def test_history_no_cycle_reports_returns_empty_list_with_200():
    route_module.set_loader_for_testing(lambda: {
        "cycle_reports": [],
        "context": _empty_context(),
    })
    status, body = asyncio.run(_asgi_get("/api/forex/agent-decision/history"))
    assert status == 200
    assert body["count"] == 0
    assert body["decisions"] == []
    assert body["limit"] == 10


def test_history_returns_decisions_newest_first():
    reports = [
        ("evidence_runs/agent_workflow_queue/agent-workflow-cycle-c3-report.json",
         _make_cycle_report("c3")),
        ("evidence_runs/agent_workflow_queue/agent-workflow-cycle-c2-report.json",
         _make_cycle_report("c2")),
        ("evidence_runs/agent_workflow_queue/agent-workflow-cycle-c1-report.json",
         _make_cycle_report("c1")),
    ]
    route_module.set_loader_for_testing(lambda: {
        "cycle_reports": reports,
        "context": _empty_context(),
        "movement_source_truth": {
            "price_source_status": "STATIC_SIMULATION_FALLBACK",
            "position_feed_label": "SIM PROOF",
            "position_feed_detail": "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions.",
        },
    })
    status, body = asyncio.run(_asgi_get("/api/forex/agent-decision/history"))
    assert status == 200
    assert body["count"] == 3
    assert len(body["decisions"]) == 3
    ids = [d["cycle_id"] for d in body["decisions"]]
    assert ids == ["c3", "c2", "c1"]
    paths = [d["cycle_report_path"] for d in body["decisions"]]
    assert paths[0].endswith("agent-workflow-cycle-c3-report.json")
    assert body["decisions"][0]["version_trace"]["trace_source"] == "agent_cycle_report"
    assert "strategy_ref_not_attached" in body["decisions"][0]["version_trace"]["gaps"]
    assert body["movement_source_truth"]["position_feed_label"] == "SIM PROOF"
    assert body["decisions"][0]["movement_source_truth"]["price_source_status"] == "STATIC_SIMULATION_FALLBACK"


def test_history_respects_limit_parameter():
    reports = [
        (f"evidence_runs/agent_workflow_queue/agent-workflow-cycle-c{i}-report.json",
         _make_cycle_report(f"c{i}"))
        for i in range(5, 0, -1)  # c5 newest, c1 oldest
    ]
    route_module.set_loader_for_testing(lambda: {
        "cycle_reports": reports,
        "context": _empty_context(),
    })
    status, body = asyncio.run(_asgi_get("/api/forex/agent-decision/history?limit=2"))
    assert status == 200
    assert body["count"] == 2
    assert body["limit"] == 2
    ids = [d["cycle_id"] for d in body["decisions"]]
    assert ids == ["c5", "c4"]


def test_history_limit_zero_returns_400():
    route_module.set_loader_for_testing(lambda: {
        "cycle_reports": [],
        "context": _empty_context(),
    })
    status, body = asyncio.run(_asgi_get("/api/forex/agent-decision/history?limit=0"))
    assert status == 400
    assert body["error"] == "invalid_limit"
    assert "message" in body


def test_history_limit_above_max_returns_400():
    route_module.set_loader_for_testing(lambda: {
        "cycle_reports": [],
        "context": _empty_context(),
    })
    status, body = asyncio.run(_asgi_get("/api/forex/agent-decision/history?limit=51"))
    assert status == 400
    assert body["error"] == "invalid_limit"
    assert "message" in body


def test_history_summaries_never_advise_future_trade():
    reports = [
        (f"evidence_runs/agent_workflow_queue/agent-workflow-cycle-c{i}-report.json",
         _make_cycle_report(f"c{i}"))
        for i in range(3, 0, -1)
    ]
    route_module.set_loader_for_testing(lambda: {
        "cycle_reports": reports,
        "context": _empty_context(),
    })
    status, body = asyncio.run(_asgi_get("/api/forex/agent-decision/history?limit=3"))
    assert status == 200
    assert body["count"] == 3
    forbidden = ("buy now", "should you trade", "good entry", "what should i do")
    for decision in body["decisions"]:
        summary = decision["plain_english_summary"].lower()
        for phrase in forbidden:
            assert phrase not in summary, (
                f"forbidden trade-advisory phrase {phrase!r} in cycle {decision['cycle_id']}"
            )


def test_history_preserves_movement_source_truth_when_loader_supplies_it():
    reports = [
        ("evidence_runs/agent_workflow_queue/agent-workflow-cycle-c2-report.json",
         _make_cycle_report("c2")),
        ("evidence_runs/agent_workflow_queue/agent-workflow-cycle-c1-report.json",
         _make_cycle_report("c1")),
    ]
    route_module.set_loader_for_testing(lambda: {
        "cycle_reports": reports,
        "context": _empty_context(),
        "movement_source_truth": {
            "price_source_status": "STATIC_SIMULATION_FALLBACK",
            "price_source_label": "Static Simulation",
            "position_feed_label": "SIM PROOF",
            "position_feed_detail": (
                "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
                "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)."
            ),
            "static_simulator_position_count": 1,
            "stale_price_position_count": 1,
        },
    })
    status, body = asyncio.run(_asgi_get("/api/forex/agent-decision/history?limit=2"))
    assert status == 200
    truth = body["movement_source_truth"]
    assert truth["price_source_status"] == "STATIC_SIMULATION_FALLBACK"
    assert truth["position_feed_label"] == "SIM PROOF"
    assert truth["static_simulator_position_count"] == 1
    assert "Stale provider/MT5 snapshots were rejected for: NAS100 (max age 900s)." in truth["position_feed_detail"]
    assert body["decisions"][1]["movement_source_truth"]["stale_price_position_count"] == 1


def test_default_loader_limits_disk_reads_to_requested_newest_reports(tmp_path, monkeypatch):
    queue_dir = tmp_path / "evidence_runs" / "agent_workflow_queue"
    queue_dir.mkdir(parents=True)
    for idx in range(5):
        path = queue_dir / f"agent-workflow-cycle-c{idx}-report.json"
        path.write_text(json.dumps(_make_cycle_report(f"c{idx}")), encoding="utf-8")
        os.utime(path, (100 + idx, 100 + idx))

    loaded_names: list[str] = []
    original_safe_load_path = route_module._safe_load_path

    def spy_safe_load_path(path):
        loaded_names.append(path.name)
        return original_safe_load_path(path)

    monkeypatch.setattr(route_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(route_module, "_safe_load_path", spy_safe_load_path)

    loaded = route_module._default_loader(limit=2)
    reports = loaded["cycle_reports"]

    assert len(reports) == 2
    assert [report["cycle_id"] for _, report in reports] == ["c4", "c3"]
    assert loaded_names == [
        "agent-workflow-cycle-c4-report.json",
        "agent-workflow-cycle-c3-report.json",
    ]
