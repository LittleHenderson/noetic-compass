"""MT4 closed-history export verifier coverage."""

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
from cas_forex.mt4_history_export_verifier import (
    build_mt4_history_export_verifier_report,
    load_latest_mt4_history_export_verifier_report,
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


def _write_ea_source(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("CASForexHistoryExporterEA source\nOrdersHistoryTotal()\n", encoding="utf-8")
    return path


def test_mt4_history_export_verifier_needs_mt4_terminal(tmp_path):
    report = build_mt4_history_export_verifier_report(
        ea_source_path=_write_ea_source(tmp_path / "mt4" / "Experts" / "CASForexHistoryExporterEA.mq4"),
        session_report={"session_status": "MT4_SESSION_NEEDS_MT4_TERMINAL", "mailbox_dir": None, "summary": {}},
        output_dir=tmp_path / "verifier",
        write_report=False,
    )

    assert report["verifier_status"] == "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL"
    assert report["summary"]["ea_source_present"] is True
    assert report["summary"]["mailbox_ready"] is False
    assert "Install/open MT4" in report["next_action"]


def test_mt4_history_export_verifier_reports_missing_export_file(tmp_path):
    mailbox = tmp_path / "terminal" / "MQL4" / "Files" / "CASForexMailbox"
    mailbox.mkdir(parents=True)

    report = build_mt4_history_export_verifier_report(
        mailbox_dir=mailbox,
        ea_source_path=_write_ea_source(tmp_path / "mt4" / "Experts" / "CASForexHistoryExporterEA.mq4"),
        output_dir=tmp_path / "verifier",
        write_report=False,
    )

    assert report["verifier_status"] == "MT4_HISTORY_EXPORT_FILE_MISSING"
    assert report["summary"]["mailbox_ready"] is True
    assert report["summary"]["history_export_present"] is False
    assert str(mailbox / "history" / "cas_forex_closed_history.json") in report["next_action"]


def test_mt4_history_export_verifier_ingests_exported_closed_history(tmp_path):
    mailbox = tmp_path / "terminal" / "MQL4" / "Files" / "CASForexMailbox"
    cycle = run_agent_workflow_cycle(output_dir=tmp_path / "cycles", mailbox_dir=tmp_path / "mailbox")
    command = cycle["terminal_commands"][0]
    command_payload = json.loads(Path(command["command_path"]).read_text(encoding="utf-8"))
    order = command_payload["order"]
    memory = build_agent_memory_report(
        event_log_path=cycle["event_journal"]["event_log_path"],
        output_dir=tmp_path / "memory",
    )
    history_path = mailbox / "history" / "cas_forex_closed_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    (mailbox / "status").mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(
            {
                "schema": "cas_forex_mt4_closed_history_export.v1",
                "terminal": "MetaTrader 4",
                "account_id_hash": "mt4-demo-hash",
                "broker_mode": "PAPER_MT4",
                "exported_at": "2026.06.24 11:00:00",
                "history_records": [
                    {
                        "ticket": "990001",
                        "broker_ticket": "990001",
                        "command_id": command["command_id"],
                        "receipt_id": f"receipt-{command['command_id']}",
                        "symbol": order["symbol"],
                        "direction": "buy",
                        "lots": order["volume"],
                        "open_time": "2026.06.24 10:00:00",
                        "close_time": "2026.06.24 10:04:00",
                        "open_price": 0.8990,
                        "close_price": 0.9002,
                        "stop_loss": order["stop_loss"],
                        "take_profit": order["take_profit"],
                        "profit_loss_account": 51.5,
                        "commission": -1.0,
                        "swap": 0.0,
                        "close_reason": "MT4_CLOSED_HISTORY",
                        "broker_mode": "PAPER_MT4",
                    }
                ],
                "summary": {"exported_order_count": 1},
            }
        ),
        encoding="utf-8",
    )
    (mailbox / "status" / "cas_forex_closed_history_status.json").write_text(
        json.dumps({"schema": "cas_forex_mt4_closed_history_status.v1", "export_status": "EXPORT_COMPLETE", "exported_order_count": 1}),
        encoding="utf-8",
    )

    report = build_mt4_history_export_verifier_report(
        mailbox_dir=mailbox,
        ea_source_path=_write_ea_source(tmp_path / "mt4" / "Experts" / "CASForexHistoryExporterEA.mq4"),
        memory_report=memory,
        output_dir=tmp_path / "verifier",
        ingest_output_dir=tmp_path / "ingest",
    )

    assert report["verifier_status"] == "MT4_HISTORY_EXPORT_INGEST_READY"
    assert report["summary"]["history_record_count"] == 1
    assert report["summary"]["memory_update_count"] == 1
    assert report["summary"]["net_profit_loss_account"] == pytest.approx(51.5)
    assert report["exporter_status"]["export_status"] == "EXPORT_COMPLETE"

    latest = load_latest_mt4_history_export_verifier_report(tmp_path / "verifier")
    assert latest["verifier_status"] == "MT4_HISTORY_EXPORT_INGEST_READY"


def test_mt4_history_export_verifier_api_and_dashboard_surface(monkeypatch, tmp_path):
    report = build_mt4_history_export_verifier_report(
        ea_source_path=_write_ea_source(tmp_path / "mt4" / "Experts" / "CASForexHistoryExporterEA.mq4"),
        session_report={"session_status": "MT4_SESSION_NEEDS_MT4_TERMINAL", "mailbox_dir": None, "summary": {}},
        output_dir=tmp_path / "verifier",
        write_report=False,
    )

    monkeypatch.setattr(strategy_routes, "mt4_history_export_verifier_latest", lambda: report)
    monkeypatch.setattr(api_server, "dashboard_state", lambda: {"mt4HistoryExportVerifier": report})

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/mt4-history-export-verifier/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_mt4_history_export_verifier_report"
    assert body["verifier_status"] == "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["mt4HistoryExportVerifier"]["verifier_status"] == "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL"
