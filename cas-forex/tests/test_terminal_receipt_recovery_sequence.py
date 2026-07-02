"""Terminal receipt recovery refresh action coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import api.routes.strategy as strategy_routes
from api.server import app
import cas_forex.terminal_receipt_recovery_sequence as sequence
from cas_forex.terminal_receipt_recovery_sequence import run_terminal_receipt_recovery_refresh


async def _asgi_post(path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    payload = json.dumps(body).encode("utf-8")
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    response_body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return int(status), json.loads(response_body.decode("utf-8"))


def test_recovery_refresh_requires_owner_confirmation_without_running(monkeypatch):
    def fail_if_called(**_: Any) -> dict[str, Any]:
        raise AssertionError("refresh chain must not run without owner confirmation")

    monkeypatch.setattr(sequence, "build_terminal_receipt_watcher_report", fail_if_called)

    action = run_terminal_receipt_recovery_refresh(
        execute=True,
        confirm_owner_refresh=False,
        current_recovery_packet={
            "report_kind": "cas_forex_terminal_receipt_recovery_packet",
            "status": "TERMINAL_RECEIPT_RECOVERY_WAITING_FOR_TERMINAL",
            "summary": {},
        },
        current_live_recovery={
            "report_kind": "cas_forex_live_recovery_review",
            "recovery_status": "OPEN",
            "summary": {},
        },
    )

    assert action["report_kind"] == "cas_forex_terminal_receipt_recovery_refresh"
    assert action["status"] == "TERMINAL_RECEIPT_RECOVERY_REFRESH_CONFIRM_REQUIRED"
    assert action["dry_run"] is True
    assert action["broker_touched"] is False
    assert action["live_order_attempted"] is False
    assert action["attempt_finalized"] is False
    assert action["money_moved"] is False
    assert [step["status"] for step in action["steps"]] == ["PLANNED"] * 4


def test_recovery_refresh_runs_local_steps_when_owner_confirmed(monkeypatch, tmp_path):
    calls: list[str] = []

    def watcher(**_: Any) -> dict[str, Any]:
        calls.append("watcher")
        return {
            "report_kind": "cas_forex_terminal_receipt_watcher_report",
            "watch_status": "WATCHER_FORCE_RAN",
            "summary": {"chain_step_complete_count": 7},
            "artifact_paths": {"json": str(tmp_path / "watcher.json")},
            "next_action": "Review chain output.",
        }

    def reconciliation(**_: Any) -> dict[str, Any]:
        calls.append("reconciliation")
        return {
            "report_kind": "cas_forex_terminal_position_reconciliation_report",
            "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_MISMATCH",
            "summary": {"pending_receipt_count": 1},
            "artifact_paths": {"json": str(tmp_path / "reconciliation.json")},
            "next_action": "Receipts pending.",
        }

    def packet(**_: Any) -> dict[str, Any]:
        calls.append("packet")
        return {
            "report_kind": "cas_forex_terminal_receipt_recovery_packet",
            "status": "TERMINAL_RECEIPT_RECOVERY_WAITING_FOR_TERMINAL",
            "summary": {},
            "next_action": "Wait for terminal receipts.",
        }

    def recovery() -> dict[str, Any]:
        calls.append("live_recovery")
        return {
            "report_kind": "cas_forex_live_recovery_review",
            "recovery_status": "OPEN",
            "summary": {},
            "next_action": "Recovery still open.",
        }

    monkeypatch.setattr(sequence, "build_terminal_receipt_watcher_report", watcher)
    monkeypatch.setattr(sequence, "build_terminal_position_reconciliation_report", reconciliation)
    monkeypatch.setattr(sequence, "build_terminal_receipt_recovery_packet", packet)
    monkeypatch.setattr(sequence, "build_live_recovery_report", recovery)

    action = run_terminal_receipt_recovery_refresh(
        execute=True,
        confirm_owner_refresh=True,
        notes="owner refresh",
    )

    assert action["status"] == "TERMINAL_RECEIPT_RECOVERY_REFRESH_RAN"
    assert action["dry_run"] is False
    assert action["broker_touched"] is False
    assert action["money_moved"] is False
    assert calls == ["watcher", "reconciliation", "packet", "live_recovery"]
    assert action["reports"]["terminal_receipt_watcher"]["status"] == "WATCHER_FORCE_RAN"
    assert action["reports"]["terminal_position_reconciliation"]["status"] == "TERMINAL_POSITION_RECONCILIATION_MISMATCH"
    assert action["reports"]["live_recovery"]["status"] == "OPEN"


def test_recovery_refresh_route_surface(monkeypatch):
    def refresh_action(**kwargs: Any) -> dict[str, Any]:
        return {
            "report_kind": "cas_forex_terminal_receipt_recovery_refresh",
            "generated_at": "2026-06-30T00:00:00+00:00",
            "status": "TERMINAL_RECEIPT_RECOVERY_REFRESH_DRY_RUN",
            "requested_execute": kwargs["execute"],
            "confirm_owner_refresh": kwargs["confirm_owner_refresh"],
            "dry_run": True,
            "broker_touched": False,
            "live_order_attempted": False,
            "attempt_finalized": False,
            "money_moved": False,
            "notes_recorded": kwargs["notes"],
            "steps": [],
            "reports": {},
            "claim_boundary": "local evidence refresh only",
            "next_action": "Review planned refresh.",
        }

    monkeypatch.setattr(strategy_routes, "terminal_receipt_recovery_refresh_action", refresh_action)

    status, body = asyncio.run(
        _asgi_post(
            "/api/forex/strategy/terminal-receipt-recovery-packet/refresh-chain",
            {"execute": False, "confirm_owner_refresh": False, "notes": "route smoke"},
        )
    )

    assert status == 200
    assert body["report_kind"] == "cas_forex_terminal_receipt_recovery_refresh"
    assert body["status"] == "TERMINAL_RECEIPT_RECOVERY_REFRESH_DRY_RUN"
    assert body["dry_run"] is True
    assert body["broker_touched"] is False
    assert body["money_moved"] is False
