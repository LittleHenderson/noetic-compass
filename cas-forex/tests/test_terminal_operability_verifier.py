"""Terminal operability verifier coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import api.server as api_server
import api.routes.strategy as strategy_routes
from api.server import app
from cas_forex.terminal_operability_verifier import (
    build_terminal_operability_verifier_report,
    load_latest_terminal_operability_verifier_report,
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


def _runtime_gates(*, live_authorized: bool = False) -> dict[str, Any]:
    decisions = {
        "live_trading": {"authorized": live_authorized, "status": "AUTHORIZED" if live_authorized else "CURRENTLY NOT LICENSED"},
        "broker_accept": {"authorized": False, "status": "CURRENTLY NOT LICENSED"},
        "auto_deposit": {"authorized": False, "status": "CURRENTLY NOT LICENSED"},
        "bank_card_movement": {"authorized": False, "status": "CURRENTLY NOT LICENSED"},
        "payout_automation": {"authorized": False, "status": "CURRENTLY NOT LICENSED"},
    }
    return {
        "report_kind": "cas_forex_runtime_gates",
        "decisions": decisions,
        "all_real_money_authorized": False,
        "summary": "fixture runtime gates",
    }


def _mt5_api_unavailable() -> dict[str, Any]:
    return {"report_kind": "cas_forex_mt5_terminal_api_verifier_report", "verifier_status": "MT5_API_VERIFIER_UNAVAILABLE", "summary": {}}


def _mt5_execution_unavailable() -> dict[str, Any]:
    return {"report_kind": "cas_forex_mt5_paper_execution_verifier_report", "verifier_status": "MT5_PAPER_EXECUTION_BLOCKED_BY_API_VERIFIER", "summary": {}}


def test_terminal_operability_reports_current_mt4_terminal_gap(tmp_path):
    report = build_terminal_operability_verifier_report(
        session_report={
            "report_kind": "cas_forex_mt4_terminal_session_verifier_report",
            "session_status": "MT4_SESSION_NEEDS_MT4_TERMINAL",
            "summary": {"mailbox_ready": False, "heartbeat_present": False},
        },
        bridge_report={
            "report_kind": "cas_forex_terminal_bridge_supervisor_report",
            "supervisor_status": "TERMINAL_BRIDGE_HEARTBEAT_MISSING",
            "summary": {"heartbeat_status": "MISSING", "heartbeat_present": False},
        },
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "ingest_status": "RECEIPT_INGEST_COMPLETE", "summary": {"pending_receipt_count": 0, "receipt_mismatch_count": 0}},
        history_export_verifier_report={"report_kind": "cas_forex_mt4_history_export_verifier_report", "verifier_status": "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL", "summary": {"mailbox_ready": False}},
        mt5_terminal_api_verifier_report=_mt5_api_unavailable(),
        mt5_paper_execution_verifier_report=_mt5_execution_unavailable(),
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "ingest_status": "TERMINAL_HISTORY_EMPTY", "summary": {}},
        position_reconciliation_report={
            "report_kind": "cas_forex_terminal_position_reconciliation_report",
            "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL",
            "summary": {"heartbeat_status": "MISSING", "account_snapshot_present": False},
        },
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    assert report["operability_status"] == "TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL"
    assert report["go_no_go"]["terminal_lane_go"] is False
    assert report["go_no_go"]["live_order_go"] is False
    assert "Install/open MT4" in report["next_action"]
    assert "does not execute live broker orders" in report["claim_boundary"]


def test_terminal_operability_ready_flat_still_reports_runtime_gate_truth(tmp_path):
    report = build_terminal_operability_verifier_report(
        session_report={
            "report_kind": "cas_forex_mt4_terminal_session_verifier_report",
            "session_status": "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_RAN",
            "summary": {"mailbox_ready": True, "heartbeat_present": True, "receipt_present": True},
        },
        bridge_report={
            "report_kind": "cas_forex_terminal_bridge_supervisor_report",
            "supervisor_status": "TERMINAL_BRIDGE_READY",
            "summary": {"heartbeat_status": "FRESH", "heartbeat_present": True},
        },
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "ingest_status": "RECEIPT_INGEST_COMPLETE", "summary": {"pending_receipt_count": 0, "receipt_mismatch_count": 0}},
        history_export_verifier_report={
            "report_kind": "cas_forex_mt4_history_export_verifier_report",
            "verifier_status": "MT4_HISTORY_EXPORT_EMPTY",
            "summary": {"mailbox_ready": True, "history_export_present": True, "history_record_count": 0},
        },
        mt5_terminal_api_verifier_report=_mt5_api_unavailable(),
        mt5_paper_execution_verifier_report=_mt5_execution_unavailable(),
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "ingest_status": "TERMINAL_HISTORY_EMPTY", "summary": {"history_record_count": 0, "memory_update_count": 0}},
        position_reconciliation_report={
            "report_kind": "cas_forex_terminal_position_reconciliation_report",
            "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_READY_FLAT",
            "summary": {
                "heartbeat_status": "FRESH",
                "heartbeat_present": True,
                "account_snapshot_present": True,
                "pending_receipt_count": 0,
                "receipt_mismatch_count": 0,
                "cas_open_position_count": 0,
                "terminal_open_position_count": 0,
                "reconciled_open_position_count": 0,
                "unmatched_open_position_count": 0,
            },
        },
        runtime_gates_report=_runtime_gates(live_authorized=False),
        output_dir=tmp_path / "operability",
    )

    assert report["operability_status"] == "TERMINAL_OPERABILITY_READY_FLAT"
    assert report["go_no_go"]["terminal_lane_go"] is True
    assert report["go_no_go"]["live_order_go"] is False
    assert "live_trading CURRENTLY NOT LICENSED" in report["go_no_go"]["blocking_reasons"]
    assert report["summary"]["runtime_gate_pending_capabilities"]
    latest = load_latest_terminal_operability_verifier_report(tmp_path / "operability")
    assert latest["operability_status"] == "TERMINAL_OPERABILITY_READY_FLAT"


def test_terminal_operability_reports_mt5_api_verified_when_mt4_bridge_missing(tmp_path):
    report = build_terminal_operability_verifier_report(
        session_report={
            "report_kind": "cas_forex_mt4_terminal_session_verifier_report",
            "session_status": "MT4_SESSION_NEEDS_MT4_TERMINAL",
            "summary": {"mailbox_ready": False, "heartbeat_present": False},
        },
        bridge_report={
            "report_kind": "cas_forex_terminal_bridge_supervisor_report",
            "supervisor_status": "TERMINAL_BRIDGE_HEARTBEAT_MISSING",
            "summary": {"heartbeat_status": "MISSING", "heartbeat_present": False},
        },
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "ingest_status": "RECEIPT_INGEST_COMPLETE", "summary": {"pending_receipt_count": 0, "receipt_mismatch_count": 0}},
        history_export_verifier_report={"report_kind": "cas_forex_mt4_history_export_verifier_report", "verifier_status": "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL", "summary": {"mailbox_ready": False}},
        mt5_terminal_api_verifier_report={
            "report_kind": "cas_forex_mt5_terminal_api_verifier_report",
            "verifier_status": "MT5_API_VERIFIER_BROKER_API_VERIFIED",
            "summary": {
                "terminal_connected": True,
                "account_snapshot_present": True,
                "open_position_count": 0,
                "open_positions_reconciled": True,
                "server": "Hugosway-Demo",
                "account_balance": 100000.0,
                "account_equity": 100000.0,
            },
        },
        mt5_paper_execution_verifier_report=_mt5_execution_unavailable(),
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "ingest_status": "TERMINAL_HISTORY_EMPTY", "summary": {}},
        position_reconciliation_report={
            "report_kind": "cas_forex_terminal_position_reconciliation_report",
            "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL",
            "summary": {"heartbeat_status": "MISSING", "account_snapshot_present": False},
        },
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    assert report["operability_status"] == "TERMINAL_OPERABILITY_MT5_API_VERIFIED_MT4_BRIDGE_MISSING"
    assert report["summary"]["mt5_broker_api_verified"] is True
    assert report["go_no_go"]["terminal_lane_go"] is False
    assert "MT5 demo broker API is verified" in report["next_action"]


def test_terminal_operability_reports_mt5_dry_run_ready(tmp_path):
    report = build_terminal_operability_verifier_report(
        session_report={
            "report_kind": "cas_forex_mt4_terminal_session_verifier_report",
            "session_status": "MT4_SESSION_NEEDS_MT4_TERMINAL",
            "summary": {"mailbox_ready": False, "heartbeat_present": False},
        },
        bridge_report={"report_kind": "cas_forex_terminal_bridge_supervisor_report", "supervisor_status": "TERMINAL_BRIDGE_HEARTBEAT_MISSING", "summary": {"heartbeat_status": "MISSING"}},
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "ingest_status": "RECEIPT_INGEST_COMPLETE", "summary": {"pending_receipt_count": 0, "receipt_mismatch_count": 0}},
        history_export_verifier_report={"report_kind": "cas_forex_mt4_history_export_verifier_report", "verifier_status": "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL", "summary": {}},
        mt5_terminal_api_verifier_report={
            "report_kind": "cas_forex_mt5_terminal_api_verifier_report",
            "verifier_status": "MT5_API_VERIFIER_BROKER_API_VERIFIED",
            "summary": {"terminal_connected": True, "account_snapshot_present": True, "open_positions_reconciled": True},
        },
        mt5_paper_execution_verifier_report={
            "report_kind": "cas_forex_mt5_paper_execution_verifier_report",
            "verifier_status": "MT5_PAPER_EXECUTION_DRY_RUN_READY",
            "summary": {
                "order_request_built": True,
                "order_check_status": "ORDER_CHECK_OK",
                "execution_attempted": False,
                "execution_status": "DRY_RUN_NO_ORDER_SENT",
            },
        },
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "ingest_status": "TERMINAL_HISTORY_EMPTY", "summary": {}},
        position_reconciliation_report={"report_kind": "cas_forex_terminal_position_reconciliation_report", "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL", "summary": {}},
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    assert report["operability_status"] == "TERMINAL_OPERABILITY_MT5_DRY_RUN_READY_DEMO_SEND_REQUIRED"
    assert report["summary"]["mt5_paper_order_request_built"] is True
    assert report["go_no_go"]["terminal_lane_go"] is False
    assert "--execute-demo-order --confirm-demo-order" in report["next_action"]


def test_terminal_operability_reports_mt5_autotrading_disabled(tmp_path):
    report = build_terminal_operability_verifier_report(
        session_report={
            "report_kind": "cas_forex_mt4_terminal_session_verifier_report",
            "session_status": "MT4_SESSION_NEEDS_MT4_TERMINAL",
            "summary": {"mailbox_ready": False, "heartbeat_present": False},
        },
        bridge_report={"report_kind": "cas_forex_terminal_bridge_supervisor_report", "supervisor_status": "TERMINAL_BRIDGE_HEARTBEAT_MISSING", "summary": {"heartbeat_status": "MISSING"}},
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "ingest_status": "RECEIPT_INGEST_COMPLETE", "summary": {"pending_receipt_count": 0, "receipt_mismatch_count": 0}},
        history_export_verifier_report={"report_kind": "cas_forex_mt4_history_export_verifier_report", "verifier_status": "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL", "summary": {}},
        mt5_terminal_api_verifier_report={
            "report_kind": "cas_forex_mt5_terminal_api_verifier_report",
            "verifier_status": "MT5_API_VERIFIER_BROKER_API_VERIFIED",
            "summary": {"terminal_connected": True, "account_snapshot_present": True, "open_positions_reconciled": True},
        },
        mt5_paper_execution_verifier_report={
            "report_kind": "cas_forex_mt5_paper_execution_verifier_report",
            "verifier_status": "MT5_PAPER_EXECUTION_DEMO_ORDER_REJECTED",
            "summary": {
                "order_request_built": True,
                "order_check_status": "ORDER_CHECK_OK",
                "execution_attempted": True,
                "execution_status": "ORDER_REJECTED",
                "execution_error_message": "AutoTrading disabled by client: AutoTrading disabled by client",
                "terminal_trade_allowed": False,
                "raw_response_hash": "response-hash",
            },
        },
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "ingest_status": "TERMINAL_HISTORY_EMPTY", "summary": {}},
        position_reconciliation_report={"report_kind": "cas_forex_terminal_position_reconciliation_report", "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL", "summary": {}},
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    assert report["operability_status"] == "TERMINAL_OPERABILITY_MT5_AUTOTRADING_DISABLED"
    assert report["summary"]["mt5_paper_terminal_trade_allowed"] is False
    assert "AutoTrading disabled by client" in report["next_action"]
    assert report["go_no_go"]["terminal_lane_go"] is False


def test_terminal_operability_flags_position_mismatch(tmp_path):
    report = build_terminal_operability_verifier_report(
        session_report={"report_kind": "cas_forex_mt4_terminal_session_verifier_report", "session_status": "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_RAN", "summary": {"mailbox_ready": True}},
        bridge_report={"report_kind": "cas_forex_terminal_bridge_supervisor_report", "supervisor_status": "TERMINAL_BRIDGE_READY", "summary": {"heartbeat_status": "FRESH", "heartbeat_present": True}},
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "ingest_status": "RECEIPT_INGEST_COMPLETE", "summary": {"pending_receipt_count": 0, "receipt_mismatch_count": 0}},
        history_export_verifier_report={"report_kind": "cas_forex_mt4_history_export_verifier_report", "verifier_status": "MT4_HISTORY_EXPORT_EMPTY", "summary": {"mailbox_ready": True, "history_export_present": True}},
        mt5_terminal_api_verifier_report=_mt5_api_unavailable(),
        mt5_paper_execution_verifier_report=_mt5_execution_unavailable(),
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "ingest_status": "TERMINAL_HISTORY_EMPTY", "summary": {}},
        position_reconciliation_report={
            "report_kind": "cas_forex_terminal_position_reconciliation_report",
            "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_MISMATCH",
            "summary": {
                "heartbeat_status": "FRESH",
                "account_snapshot_present": True,
                "pending_receipt_count": 0,
                "receipt_mismatch_count": 0,
                "unmatched_open_position_count": 1,
            },
        },
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    assert report["operability_status"] == "TERMINAL_OPERABILITY_POSITION_MISMATCH"
    assert report["go_no_go"]["terminal_lane_go"] is False


def test_terminal_operability_api_and_dashboard_surface(monkeypatch, tmp_path):
    report = build_terminal_operability_verifier_report(
        session_report={"report_kind": "cas_forex_mt4_terminal_session_verifier_report", "session_status": "MT4_SESSION_NEEDS_MT4_TERMINAL", "summary": {}},
        bridge_report={"report_kind": "cas_forex_terminal_bridge_supervisor_report", "supervisor_status": "TERMINAL_BRIDGE_HEARTBEAT_MISSING", "summary": {"heartbeat_status": "MISSING"}},
        receipt_ingest_report={"report_kind": "cas_forex_terminal_receipt_ingest", "ingest_status": "RECEIPT_INGEST_COMPLETE", "summary": {}},
        history_export_verifier_report={"report_kind": "cas_forex_mt4_history_export_verifier_report", "verifier_status": "MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL", "summary": {}},
        mt5_terminal_api_verifier_report=_mt5_api_unavailable(),
        mt5_paper_execution_verifier_report=_mt5_execution_unavailable(),
        history_ingest_report={"report_kind": "cas_forex_terminal_history_ingest", "ingest_status": "TERMINAL_HISTORY_EMPTY", "summary": {}},
        position_reconciliation_report={"report_kind": "cas_forex_terminal_position_reconciliation_report", "reconciliation_status": "TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL", "summary": {}},
        runtime_gates_report=_runtime_gates(),
        output_dir=tmp_path / "operability",
        write_report=False,
    )

    monkeypatch.setattr(strategy_routes, "terminal_operability_verifier_latest", lambda: report)
    monkeypatch.setattr(api_server, "dashboard_state", lambda: {"terminalOperabilityVerifier": report})

    status, body = asyncio.run(_asgi_get("/api/forex/strategy/terminal-operability-verifier/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_terminal_operability_verifier_report"
    assert body["operability_status"] == "TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL"

    status, dashboard = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert dashboard["terminalOperabilityVerifier"]["go_no_go"]["terminal_lane_go"] is False
