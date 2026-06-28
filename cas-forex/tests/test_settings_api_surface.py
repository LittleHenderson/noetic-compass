"""Regression coverage for the CAS Forex settings/dashboard API surface.

These tests intentionally drive the FastAPI ASGI app directly instead of relying
on a live uvicorn process. They catch stale-route and stale-dashboard-shape
regressions like:
  * /settings/authority-boundary returning 404
  * /settings/runtime-gates returning 404
  * owner-control/dashboard reintroducing removed hard scope fields
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api.server import app


async def _asgi_request(path: str, *, method: str = "GET") -> tuple[int, dict[str, Any]]:
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
        "method": method,
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


async def _asgi_get(path: str) -> tuple[int, dict[str, Any]]:
    return await _asgi_request(path, method="GET")


def test_settings_owner_control_excludes_removed_hard_scope_fields():
    status, body = asyncio.run(_asgi_get("/api/forex/settings/owner-control"))
    assert status == 200
    assert "personal_utilization_only" not in body
    assert "account_scope" not in body
    assert "disallowed_scopes" not in body
    assert "owner-controlled" in body["claim_boundary"]


def test_settings_authority_and_runtime_gate_routes_are_registered():
    status, authority = asyncio.run(_asgi_get("/api/forex/settings/authority-boundary"))
    assert status == 200
    assert authority["live_trading_status"] in {"CURRENTLY NOT LICENSED", "AUTHORIZED"}
    assert authority["trading_edge_status"] == "OPEN"

    status, gates = asyncio.run(_asgi_get("/api/forex/settings/runtime-gates"))
    assert status == 200
    assert sorted(gates["decisions"]) == [
        "auto_deposit",
        "bank_card_movement",
        "broker_accept",
        "live_trading",
        "payout_automation",
    ]


def test_dashboard_contains_owner_control_without_removed_hard_scope_fields():
    status, body = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert "personal_utilization_only" not in body["ownerControl"]
    assert "account_scope" not in body["ownerControl"]
    assert "disallowed_scopes" not in body["ownerControl"]
    assert "runtimeGates" in body
    assert "authorityBoundary" in body
    assert "accountLedger" in body
    assert body["accountLedger"]["summary"]["initial_investment_usd"] > 0
    assert body["accountLedger"]["live_money_authorized"] is False
    assert body["accountLedger"]["payment_movement_authorized"] is False
    assert "movementStream" in body
    assert body["movementStream"]["account"]["equity_usd"] > 0
    assert body["movementStream"]["live_money_authorized"] is False
    assert body["movementStream"]["payment_movement_authorized"] is False
    assert "accountReconciliation" in body
    assert body["accountReconciliation"]["report_kind"] == "cas_forex_account_reconciliation"
    assert body["accountReconciliation"]["live_money_authorized"] is False
    assert body["accountReconciliation"]["payment_movement_authorized"] is False
    assert body["accountReconciliation"]["trading_edge_status"] == "OPEN"
    assert "account_snapshot" in body["mt5Receipt"]
    assert "mt5ProbeStatus" in body
    assert "liveReadiness" in body
    assert body["liveReadiness"]["report_kind"] == "cas_forex_live_readiness"
    assert body["liveReadiness"]["overall_status"] in {"NOT_READY_FOR_LIVE", "READY_FOR_LIVE_EXECUTION"}
    assert "ownerPromotionReview" in body
    assert body["ownerPromotionReview"]["report_kind"] == "cas_forex_owner_promotion_review_summary"
    assert isinstance(body["ownerPromotionReview"]["strategy_edge_passed"], bool)
    assert any(check["gate_id"] == "owner_initial_investment" for check in body["liveReadiness"]["checks"])
    assert any(check["gate_id"] == "live_trading" for check in body["liveReadiness"]["checks"])
    assert body["mt5Receipt"]["receipt_validation_status"] == "BROKER_API_VERIFIED"
    assert body["mt5ProbeStatus"]["status"] in {"BROKER_API_VERIFIED", "UNAVAILABLE", "BLOCKED"}


def test_account_ledger_route_accepts_owner_selected_positive_seed():
    status, body = asyncio.run(_asgi_get("/api/forex/account/ledger?initial_investment=2500"))
    assert status == 200
    assert body["summary"]["owner_selected_initial_investment_usd"] == 2500
    assert body["summary"]["requires_new_risk_review_for_selected_investment"] is True
    assert body["supported_history_tabs"] == ["Positions", "Orders", "Deals"]
    assert body["supported_time_filters"] == ["Seconds", "Minutes", "Hour", "Day", "Week", "Month", "Custom"]
    assert body["live_money_authorized"] is False
    assert body["payment_movement_authorized"] is False


def test_broker_synced_risk_preview_reruns_sizing_without_authority_or_append():
    status, body = asyncio.run(_asgi_get("/api/forex/account/broker-sync-risk-preview"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_broker_synced_risk_preview"
    assert body["mode"] == "BROKER_SYNCED_PAPER_RISK_PREVIEW"
    assert body["sync_to_broker_snapshot"] is True
    assert body["broker_snapshot_initial_investment_usd"] >= body["default_risk_review_account_equity_usd"]
    assert body["account_equity"] == body["broker_snapshot_initial_investment_usd"]
    assert body["would_append_evidence"] is False
    assert body["evidence_appended"] is False
    assert body["live_money_authorized"] is False
    assert body["payment_movement_authorized"] is False
    assert body["deployment_status"] == "NOT LICENSED"
    assert body["broker_accept_status"] == "NOT LICENSED"
    assert body["payment_transfer_status"] == "NOT LICENSED"
    assert body["total_planned_risk_usd"] >= body["default_total_planned_risk_usd"]
    assert body["total_planned_lots"] >= body["default_total_planned_lots"]
    if body["already_applied"]:
        assert body["delta_vs_default"]["account_equity_usd"] == 0
        assert "already the latest" in body["next_action"]
    else:
        assert body["delta_vs_default"]["account_equity_usd"] > 0
    assert "does not append evidence" in body["claim_boundary"]


def test_broker_synced_risk_apply_requires_explicit_confirmation():
    status, body = asyncio.run(_asgi_request("/api/forex/account/apply-broker-sync-risk-review", method="POST"))
    assert status == 400
    assert "confirm_apply=true" in body["detail"]


def test_movement_snapshot_route_exposes_account_and_market_streams():
    status, body = asyncio.run(_asgi_get("/api/forex/movement/snapshot"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_movement_stream"
    assert "balance" in body["account_streams"]
    assert "swap" in body["account_streams"]
    assert "commission" in body["account_streams"]
    assert "broker_fees" in body["account_streams"]
    assert "bid" in body["market_streams"]
    assert "floating_pnl" in body["market_streams"]
    assert "margin_estimate" in body["market_streams"]
    assert body["account"]["equity_usd"] > 0
    assert body["quotes"]
    assert body["positions"]
    assert body["live_money_authorized"] is False
    assert body["payment_movement_authorized"] is False
    assert body["trading_edge_status"] == "OPEN"


def test_reconciliation_route_exposes_checks_without_authority():
    status, body = asyncio.run(_asgi_get("/api/forex/reconciliation/account"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_account_reconciliation"
    assert body["checks_total"] >= 1
    assert isinstance(body["checks"], list) and body["checks"]
    assert body["overall_status"] in {"RECONCILED", "RECONCILED_WITH_WARNINGS", "RECONCILIATION_FAILED"}
    assert body["live_money_authorized"] is False
    assert body["payment_movement_authorized"] is False
    assert body["trading_edge_status"] == "OPEN"
    assert body["live_trading_status"] == "CURRENTLY NOT LICENSED"

def test_mt5_probe_status_route_distinguishes_latest_attempt_from_verified_receipt():
    status, receipt = asyncio.run(_asgi_get("/api/forex/mt/receipt/latest"))
    assert status == 200
    assert receipt["receipt_validation_status"] == "BROKER_API_VERIFIED"

    status, probe = asyncio.run(_asgi_get("/api/forex/mt/probe/latest"))
    assert status == 200
    assert probe["status"] in {"BROKER_API_VERIFIED", "UNAVAILABLE", "BLOCKED"}
    assert "has_receipt" in probe
    assert "account_snapshot_present" in probe
    assert "claim_boundary" in probe

def test_reconciliation_route_can_preview_broker_synced_accounting():
    status, body = asyncio.run(_asgi_get("/api/forex/reconciliation/account?sync_to_broker=true"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_account_reconciliation"
    assert "sync_to_broker_snapshot" in body
    assert body["live_money_authorized"] is False
    assert body["payment_movement_authorized"] is False
    assert body["trading_edge_status"] == "OPEN"

def test_live_readiness_route_exposes_plain_english_operability_checklist():
    status, body = asyncio.run(_asgi_get("/api/forex/readiness/live"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_live_readiness"
    assert body["mode"] == "LIVE_OPERABILITY_CHECKLIST"
    assert body["overall_status"] in {"NOT_READY_FOR_LIVE", "READY_FOR_LIVE_EXECUTION"}
    assert body["live_money_authorized"] is False
    assert body["payment_movement_authorized"] is False
    assert isinstance(body["checks"], list) and body["checks"]
    by_id = {check["gate_id"]: check for check in body["checks"]}
    assert "owner_initial_investment" in by_id
    assert "account_movement_tracking" in by_id
    assert "market_movement_tracking" in by_id
    assert "live_trading" in by_id
    assert by_id["live_trading"]["status"] in {"CURRENTLY NOT LICENSED", "PASSED"}

    status, synced = asyncio.run(_asgi_get("/api/forex/readiness/live?sync_to_broker=true"))
    assert status == 200
    assert synced["report_kind"] == "cas_forex_live_readiness"
    assert "sync_to_broker_snapshot" in synced
    assert synced["live_money_authorized"] is False
    assert synced["payment_movement_authorized"] is False
    if synced["sync_to_broker_snapshot"]:
        synced_by_id = {check["gate_id"]: check for check in synced["checks"]}
        assert synced_by_id["account_reconciliation"]["status"] == "PASSED"
