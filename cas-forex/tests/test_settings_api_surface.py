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
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from api import server as api_server
from api.routes import pcba as pcba_route
from api.routes import readiness as readiness_route
from api.routes import reconciliation as reconciliation_route
from api.routes import settings as settings_route
from api.routes import stack_health as stack_health_route
from api.routes import mobile as mobile_route
from api.server import app


REPO_ROOT = Path(__file__).resolve().parents[1]


async def _asgi_request(
    path: str,
    *,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    sent: list[dict[str, Any]] = []
    request_body = (
        json.dumps(json_body).encode("utf-8") if json_body is not None else b""
    )

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": request_body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    request_headers = [(b"host", b"testserver"), (b"content-type", b"application/json")]
    for key, value in (headers or {}).items():
        request_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": request_headers,
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


async def _asgi_post(path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    return await _asgi_request(path, method="POST", json_body=body)


async def _asgi_post_with_headers(
    path: str,
    body: dict[str, Any],
    headers: dict[str, str],
) -> tuple[int, dict[str, Any]]:
    return await _asgi_request(path, method="POST", json_body=body, headers=headers)


def test_optimizer_agent_cycle_uses_conviction_not_fake_precision():
    conviction_helper = (REPO_ROOT / "ui" / "src" / "util" / "conviction.ts").read_text(encoding="utf-8")
    optimizer_page = (REPO_ROOT / "ui" / "src" / "pages" / "OptimizerPage.tsx").read_text(encoding="utf-8")
    assert "export const CONVICTION_SCORE_TITLE" in conviction_helper
    assert "export function formatConvictionScore" in conviction_helper
    assert 'const label = pct >= 75 ? "High" : pct >= 50 ? "Medium" : "Low";' in conviction_helper
    assert 'import { CONVICTION_SCORE_TITLE, formatConvictionScore } from "../util/conviction";' in optimizer_page
    assert "<th>Conviction</th>" in optimizer_page
    assert "formatConvictionScore(intent.confidence)" in optimizer_page
    assert "CONVICTION_SCORE_TITLE" in optimizer_page
    assert "intent.confidence.toFixed(4)" not in optimizer_page


def test_decision_surfaces_share_conviction_formatter():
    trade_page = (REPO_ROOT / "ui" / "src" / "pages" / "TradePage.tsx").read_text(encoding="utf-8")
    proof_page = (REPO_ROOT / "ui" / "src" / "pages" / "ProofPage.tsx").read_text(encoding="utf-8")
    audit_page = (REPO_ROOT / "ui" / "src" / "pages" / "AuditPage.tsx").read_text(encoding="utf-8")
    adaptive_page = (REPO_ROOT / "ui" / "src" / "pages" / "AdaptivePage.tsx").read_text(encoding="utf-8")
    dashboard_evidence = (REPO_ROOT / "ui" / "src" / "components" / "DashboardEvidencePanels.tsx").read_text(encoding="utf-8")

    for source in (trade_page, proof_page, audit_page, adaptive_page, dashboard_evidence):
        assert "CONVICTION_SCORE_TITLE" in source
        assert "formatConvictionScore" in source
        assert "Directional conviction score, not a win probability." not in source

    assert "conviction: {formatConvictionScore(activeDecision.confidence)}" in trade_page
    assert "conviction: {formatConvictionScore(d.confidence)}" in proof_page
    assert "<span className=\"field-label\">Conviction</span>" in audit_page
    assert "<th>Conviction</th>" in adaptive_page
    assert "<th>Conviction</th>" in dashboard_evidence


def test_settings_ai_dials_surface_impact_and_anti_impulse_state():
    api_types = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    owner_command_api = (REPO_ROOT / "ui" / "src" / "data" / "ownerCommandApi.ts").read_text(encoding="utf-8")
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    floating_assistant = (REPO_ROOT / "ui" / "src" / "components" / "FloatingAssistant.tsx").read_text(encoding="utf-8")
    operator_badge = (REPO_ROOT / "ui" / "src" / "components" / "OperatorBadge.tsx").read_text(encoding="utf-8")
    assert "dial_definitions?" in api_types
    assert "anti_impulse?" in api_types
    assert "export interface AiControlAdjustmentPreview" in api_types
    assert '"/ai-control-authority/preview"' in api_types
    assert "runtime_path?" in api_types
    assert "value_kind?" in api_types
    assert "contract_rows?" in owner_command_api
    assert "journal_required?" in owner_command_api
    assert "<th>Risk Posture</th>" in settings_page
    assert "Loosens 24h" in settings_page
    assert "definition.operational_effect" in settings_page
    assert "definition.enforced_by" in settings_page
    assert "definition.runtime_path" in settings_page
    assert "definition.units" in settings_page
    assert "preview.contract_rows" in floating_assistant
    assert "preview.journal_required" in floating_assistant
    assert "preview.contract_rows" in operator_badge
    assert "preview.journal_required" in operator_badge


def test_windows_positions_surface_age_and_static_stale_reason():
    evidence_types = (REPO_ROOT / "ui" / "src" / "types" / "evidence.ts").read_text(encoding="utf-8")
    windows_page = (REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.tsx").read_text(encoding="utf-8")
    trading_window = (REPO_ROOT / "ui" / "src" / "components" / "TradingWindow.tsx").read_text(encoding="utf-8")
    movement_helper = (REPO_ROOT / "ui" / "src" / "util" / "movementSource.ts").read_text(encoding="utf-8")
    assert "stale_reason?: string | null" in evidence_types
    assert "age_days?: number | null" in evidence_types
    assert "<th>Age</th>" in windows_page
    assert "formatMovementPositionAge(p)" in windows_page
    assert "movement?.movement_source_truth ?? movement ?? null" in windows_page
    assert "describeMovementPositionFeed(movementTruth, acct?.source)" in windows_page
    assert "position feed: <strong>{positionsSource}</strong>" in windows_page
    assert "paper/demo simulator proof rows with static stale pricing" in movement_helper
    assert "live MT5 broker positions" in movement_helper
    assert "SIM STATIC" in movement_helper
    assert "fetchMovementStream(true)" in windows_page
    assert "<th>Source</th>" in trading_window
    assert "formatMovementPositionSourceLabel" in trading_window
    assert "tw-source-pill" in trading_window
    assert "formatMovementPositionAge(p)" in trading_window
    assert "positionsDetail" in trading_window
    assert "tw-position-source-warning" in trading_window
    assert "Static simulator price:" in trading_window
    assert "isStaticMovementPosition(p)" in trading_window
    assert "export function isStaticMovementPosition" in movement_helper
    assert "export function formatMovementPositionAge" in movement_helper
    assert "export function describeMovementPositionFeed" in movement_helper
    windows_css = (REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.css").read_text(encoding="utf-8")
    assert ".tw-position-source-warning" in windows_css
    assert ".tw-source-pill.stale" in windows_css


def test_trading_window_surfaces_manual_order_explanation_card():
    trading_window = (REPO_ROOT / "ui" / "src" / "components" / "TradingWindow.tsx").read_text(encoding="utf-8")
    windows_css = (REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.css").read_text(encoding="utf-8")
    assert "latestOrderResult" in trading_window
    assert "<TradeExplanationCard result={latestOrderResult} />" in trading_window
    assert "trade_explanation_card" in trading_window
    assert "Gate trace" in trading_window
    assert "Bridge touched" in trading_window
    assert "Risk at SL" in trading_window
    assert "Initiator" in trading_window
    assert "Runtime lane" in trading_window
    assert "provenance:" in trading_window
    assert "Live readiness:" in trading_window
    assert "Live evidence" in trading_window
    assert "audit attempt" in trading_window
    assert ".tw-explanation-card" in windows_css
    assert ".tw-gate-trace" in windows_css


def test_live_recovery_ui_surfaces_selected_attempt_provenance():
    evidence_types = (REPO_ROOT / "ui" / "src" / "types" / "evidence.ts").read_text(encoding="utf-8")
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    assert "execution_provenance?: Record<string, unknown> | null;" in evidence_types
    assert "selectedAttemptProvenance" in settings_page
    assert "Runtime Lane" in settings_page
    assert "Provenance Hash" in settings_page
    assert "Config Hash" in settings_page


def test_agent_decision_ui_surfaces_version_trace():
    api_types = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    decision_card = (REPO_ROOT / "ui" / "src" / "components" / "AgentDecisionCard.tsx").read_text(encoding="utf-8")
    history_row = (REPO_ROOT / "ui" / "src" / "components" / "DecisionHistoryRow.tsx").read_text(encoding="utf-8")
    history_page = (REPO_ROOT / "ui" / "src" / "pages" / "DecisionHistoryPage.tsx").read_text(encoding="utf-8")
    movement_truth = (REPO_ROOT / "ui" / "src" / "components" / "DecisionMovementTruth.tsx").read_text(encoding="utf-8")
    version_trace = (REPO_ROOT / "ui" / "src" / "components" / "DecisionVersionTrace.tsx").read_text(encoding="utf-8")
    css = (REPO_ROOT / "ui" / "src" / "components" / "DecisionCardPrimitives.css").read_text(encoding="utf-8")
    assert "AgentDecisionVersionTrace" in api_types
    assert "version_trace?: AgentDecisionVersionTrace" in api_types
    assert "export interface MovementSourceTruthSnapshot" in api_types
    assert "movement_source_truth?: MovementSourceTruthSnapshot | null;" in api_types
    assert "<DecisionVersionTrace trace={data.version_trace} />" in decision_card
    assert "<DecisionMovementTruth truth={data.movement_source_truth} />" in decision_card
    assert "<DecisionVersionTrace trace={decision.version_trace} />" in history_row
    assert "response?.movement_source_truth" in history_page
    assert "DecisionMovementTruth" in movement_truth
    assert "Decision Pricing Truth" in movement_truth
    assert "Version trace" in version_trace
    assert "gaps:" in version_trace
    assert ".decision-version-grid" in css
    assert ".decision-movement-truth" in css


def test_account_ledger_types_and_pages_expose_movement_source_truth():
    evidence_types = (REPO_ROOT / "ui" / "src" / "types" / "evidence.ts").read_text(encoding="utf-8")
    history_page = (REPO_ROOT / "ui" / "src" / "pages" / "HistoryPage.tsx").read_text(encoding="utf-8")
    ledger_page = (REPO_ROOT / "ui" / "src" / "pages" / "LedgerPage.tsx").read_text(encoding="utf-8")
    assert "movement_stream_id?: string | null;" in evidence_types
    assert "movement_stream_timestamp?: string | null;" in evidence_types
    assert "movement_source_truth?:" in evidence_types
    assert "account?.movement_source_truth" in history_page
    assert "account?.movement_source_truth" in ledger_page


def test_account_reconciliation_types_expose_movement_source_truth():
    # The fixture-file assertions that used to live here were dropped along with
    # ui/src/data/fixtures.ts (2026-08-10). That file was imported by nothing, so
    # these checks guarded a payload no screen could ever render. The type and
    # helper contracts below are the part that actually binds the UI.
    evidence_types = (REPO_ROOT / "ui" / "src" / "types" / "evidence.ts").read_text(encoding="utf-8")
    movement_helper = (REPO_ROOT / "ui" / "src" / "util" / "movementSource.ts").read_text(encoding="utf-8")
    assert "movement_source_truth?: MovementSourceTruthSnapshot | null;" in evidence_types
    assert "movement_source_truth?: MovementSourceTruthSnapshot | null;" in movement_helper


def test_live_enable_ui_uses_typed_arm_confirmation():
    api_types = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    trade_page = (REPO_ROOT / "ui" / "src" / "pages" / "TradePage.tsx").read_text(encoding="utf-8")
    proof_page = (REPO_ROOT / "ui" / "src" / "pages" / "ProofPage.tsx").read_text(encoding="utf-8")
    assert "confirm?: string" in api_types
    assert "need_confirmation?: string" in api_types
    assert "latest_audit?: Record<string, unknown>" in api_types
    assert "armConfirmationForPatch" in settings_page
    assert "requestArmConfirmation" in settings_page
    assert "CONFIRM_REQUIRED" in settings_page
    assert "ARM REAL MONEY" in trade_page
    assert "patch.confirm = confirm" in trade_page
    assert "ARM REAL MONEY" in proof_page
    assert "patch.confirm = confirm" in proof_page


def test_money_movement_setup_ui_surfaces_runtime_scaffold_status():
    api_types = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    trade_page = (REPO_ROOT / "ui" / "src" / "pages" / "TradePage.tsx").read_text(encoding="utf-8")
    proof_page = (REPO_ROOT / "ui" / "src" / "pages" / "ProofPage.tsx").read_text(encoding="utf-8")
    status_component = (REPO_ROOT / "ui" / "src" / "components" / "MoneyMovementSetupStatus.tsx").read_text(encoding="utf-8")
    sweep_panel = (REPO_ROOT / "ui" / "src" / "components" / "DashboardSweepOpsPanel.tsx").read_text(encoding="utf-8")
    assert "runtime_provider_name?: string;" in api_types
    assert "runtime_status?: string;" in api_types
    assert "real_money_provider_ready?: boolean;" in api_types
    assert "export interface PaymentProviderRuntimeStatus" in api_types
    assert "provider_runtime: PaymentProviderRuntimeStatus;" in api_types
    assert "payout_runtime_ready: boolean;" in api_types
    assert "<MoneyMovementSetupStatus" in settings_page
    assert "<MoneyMovementSetupStatus" in trade_page
    assert "<MoneyMovementSetupStatus" in proof_page
    assert "Real-money rail" in status_component
    assert "SCAFFOLDED" in status_component
    assert "unsupported provider labels stay simulated at runtime" in settings_page
    assert "unsupported provider labels stay simulated at runtime" in trade_page
    assert "Saving a provider label does not make payouts live." in proof_page
    assert "PAYOUT SCAFFOLDED" in sweep_panel
    assert "const providerRuntime = currentSweep?.provider_runtime ?? null;" in sweep_panel
    assert "const payoutRuntimeReady = Boolean(currentSweep?.payout_runtime_ready);" in sweep_panel
    assert 'label={`RAIL ${payoutRuntimeStatus}`}' in sweep_panel
    assert "providerRuntime?.detail" in sweep_panel


def test_trade_page_surfaces_psychology_guard_panel():
    api_types = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    dashboard_page = (REPO_ROOT / "ui" / "src" / "pages" / "DashboardPage.tsx").read_text(encoding="utf-8")
    psychology_panel = (REPO_ROOT / "ui" / "src" / "components" / "PsychologyGuardPanel.tsx").read_text(encoding="utf-8")
    trade_page = (REPO_ROOT / "ui" / "src" / "pages" / "TradePage.tsx").read_text(encoding="utf-8")
    assert "anti_impulse_status?: {" in api_types
    assert "export function PsychologyGuardPanel" in psychology_panel
    assert 'title = "Psychology Guard"' in psychology_panel
    assert "AI Dial Cooldown" in psychology_panel
    assert "Risk-Cap Cooldown" in psychology_panel
    assert "Anti-Impulse Journal" in psychology_panel
    assert "fetchRiskControl()" in psychology_panel
    assert "fetchAiControlAuthority()" in psychology_panel
    assert "<PsychologyGuardPanel />" in trade_page
    assert "<PsychologyGuardPanel subtitle=" in dashboard_page


def test_legal_review_panel_surfaces_owner_record_workflow():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert "fetchLegalReviewControl" in settings_page
    assert "updateLegalReviewControl" in settings_page
    assert "resetLegalReviewControl" in settings_page
    assert "Counsel Record Control" in settings_page
    assert "Review Artifact Path" in settings_page
    assert "Artifact SHA-256" in settings_page
    assert "RECORD QUALIFIED COUNSEL REVIEW" in settings_page
    assert "LegalReviewControlReport" in api_client
    assert "LegalReviewControlUpdate" in api_client
    assert '"/settings/legal-review-control"' in api_client


def test_dashboard_surfaces_live_readiness_summary_panel():
    dashboard_page = (REPO_ROOT / "ui" / "src" / "pages" / "DashboardPage.tsx").read_text(encoding="utf-8")
    live_panel = (REPO_ROOT / "ui" / "src" / "components" / "LiveReadinessSummaryPanel.tsx").read_text(encoding="utf-8")

    assert "export function LiveReadinessSummaryPanel" in live_panel
    assert 'title="Live Gate Summary"' in live_panel
    assert "Top Blocking Checks" in live_panel
    assert "Next Actions" in live_panel
    assert "fetchLiveReadinessSummary" in live_panel
    assert "fetchAccountReconciliationSummary" in live_panel
    assert "fetchBrokerTruthSummary" in live_panel
    assert 'apiGet<LiveReadinessReport>("/readiness/live")' in live_panel
    assert 'apiGet<AccountReconciliationReport>("/reconciliation/account")' in live_panel
    assert 'apiGet<BrokerTruthMonitorStatus>("/broker-truth-monitor/status/fast")' in live_panel
    assert "position_protection_status" in live_panel
    assert "position_protection_unprotected_position_count" in live_panel
    assert "monitor_auto_halt_reason_ids" in live_panel
    assert "BROKER TRUTH PAPER FORCE" in live_panel
    assert "Truth Halt Reasons" in live_panel
    assert "Broker Truth Enforcement" in live_panel
    assert "Stop-Loss Protection" in live_panel
    assert "shortPositionProtectionStatus" in live_panel
    assert "<LiveReadinessSummaryPanel" in dashboard_page
    assert "initialLiveReadiness={state.liveReadiness ?? null}" in dashboard_page
    assert "initialAccountReconciliation={state.accountReconciliation ?? null}" in dashboard_page
    assert "initialBrokerTruthMonitor={state.brokerTruthMonitor ?? null}" in dashboard_page


def test_operator_badge_surfaces_cluster_signal_quality_metrics():
    operator_badge = (REPO_ROOT / "ui" / "src" / "components" / "OperatorBadge.tsx").read_text(encoding="utf-8")
    operator_badge_css = (REPO_ROOT / "ui" / "src" / "components" / "OperatorBadge.css").read_text(encoding="utf-8")
    floating_assistant = (REPO_ROOT / "ui" / "src" / "components" / "FloatingAssistant.tsx").read_text(encoding="utf-8")
    assert "Cluster inflation (raw/unique)" in operator_badge
    assert "Biggest copy stack" in operator_badge
    assert "Avg win/loss stack" in operator_badge
    assert "Blind stacking warning" in operator_badge
    assert "WATCHING + PAPER SIM" in operator_badge
    assert "WATCHING + MT5 DEMO" in operator_badge
    assert "MT5 DEMO + SIM HANDOFF" in operator_badge
    assert "MT5 demo learning:" in operator_badge
    assert ".operator-badge-profit-warning" in operator_badge_css


def test_operator_badge_extracts_structured_chat_failure_details():
    operator_badge = (REPO_ROOT / "ui" / "src" / "components" / "OperatorBadge.tsx").read_text(encoding="utf-8")
    operator_route = (REPO_ROOT / "api" / "routes" / "ai_operator.py").read_text(encoding="utf-8")
    ai_operator = (REPO_ROOT / "cas_forex" / "ai_operator.py").read_text(encoding="utf-8")

    assert "type ApiErrorLike = Error & { status?: number; payload?: unknown };" in operator_badge
    assert "function operatorApiFailureDetail" in operator_badge
    assert "payloadDetail?.money_impact" in operator_badge
    assert "operator_chat_unavailable|internal server error" in operator_badge
    assert "Operator backend failed before a reply:" in operator_badge
    assert '"error": "operator_chat_unavailable"' in operator_route
    assert '"money_impact": "No command ran and no dials changed."' in operator_route
    assert "CHAT_CLAIM_BOUNDARY" in ai_operator


def test_settings_owner_control_excludes_removed_hard_scope_fields():
    status, body = asyncio.run(_asgi_get("/api/forex/settings/owner-control"))
    assert status == 200
    assert "personal_utilization_only" not in body
    assert "account_scope" not in body
    assert "disallowed_scopes" not in body
    assert "owner-controlled" in body["claim_boundary"]
    assert body["allowed_modes"]
    assert body["override_state_path"]


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


def test_health_routes_are_available_for_ui_and_external_supervisors():
    for path in ("/health", "/api/forex/health"):
        status, body = asyncio.run(_asgi_get(path))
        assert status == 200
        assert body["status"] == "healthy"
        assert body["version"] == "0.1.0"


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
    assert "liveOrderDryRun" in body
    assert body["liveOrderDryRun"]["report_kind"] == "cas_forex_live_order_dry_run_latest"
    assert body["liveOrderDryRun"]["broker_touched"] is False
    assert "orderAttemptRecoveryPacket" in body
    assert body["orderAttemptRecoveryPacket"]["report_kind"] == "cas_forex_order_attempt_recovery_packet"
    assert body["orderAttemptRecoveryPacket"]["broker_touched"] is False
    assert body["orderAttemptRecoveryPacket"]["attempt_finalized"] is False
    assert "terminalReceiptRecoveryPacket" in body
    assert body["terminalReceiptRecoveryPacket"]["report_kind"] == "cas_forex_terminal_receipt_recovery_packet"
    assert body["terminalReceiptRecoveryPacket"]["broker_touched"] is False
    assert body["terminalReceiptRecoveryPacket"]["journal_rewritten"] is False
    assert "compoundAddOrderDryRun" in body
    assert body["compoundAddOrderDryRun"]["report_kind"] == "cas_forex_compound_add_order_dry_run_latest"
    assert body["compoundAddOrderDryRun"]["broker_touched"] is False
    assert "compoundAddOrderDryRunReview" in body
    assert body["compoundAddOrderDryRunReview"]["report_kind"] == "cas_forex_compound_add_order_dry_run_review"
    assert body["compoundAddOrderDryRunReview"]["compound_add_dry_run_review_clear_for_dispatch"] in {True, False}
    assert "compoundAddDispatchHandoff" in body
    assert body["compoundAddDispatchHandoff"]["report_kind"] == "cas_forex_waste_compound_add_dispatch_handoff"
    assert body["compoundAddDispatchHandoff"]["broker_touched"] is False
    assert body["compoundAddDispatchHandoff"]["dispatched_to_bridge"] is False
    assert "liveOrderDryRunReview" in body
    assert body["liveOrderDryRunReview"]["report_kind"] == "cas_forex_live_order_dry_run_review"
    assert body["liveOrderDryRunReview"]["dry_run_review_clear_for_live"] in {True, False}
    assert "wasteEntryPilotPromotion" in body
    assert body["wasteEntryPilotPromotion"]["report_kind"] == "cas_forex_waste_pilot_promotion"
    assert body["wasteEntryPilotPromotion"]["broker_touched"] is False
    assert body["wasteEntryPilotPromotion"]["dispatched_to_bridge"] is False
    assert "wasteDirectionReview" in body
    assert body["wasteDirectionReview"]["report_kind"] == "cas_forex_waste_direction_review_packet"
    assert body["wasteDirectionReview"]["broker_touched"] is False
    assert body["wasteDirectionReview"]["live_order_attempted"] is False
    assert body["wasteDirectionReview"]["money_moved"] is False
    assert "wasteDirectionLearning" in body
    assert body["wasteDirectionLearning"]["report_kind"] == "cas_forex_waste_direction_learning_ledger"
    assert body["wasteDirectionLearning"]["broker_touched"] is False
    assert body["wasteDirectionLearning"]["live_order_attempted"] is False
    assert body["wasteDirectionLearning"]["money_moved"] is False
    assert "wasteDirectionOutcomeBinding" in body
    assert body["wasteDirectionOutcomeBinding"]["report_kind"] == "cas_forex_waste_direction_outcome_binding"
    assert body["wasteDirectionOutcomeBinding"]["dry_run"] is True
    assert body["wasteDirectionOutcomeBinding"]["read_only"] is True
    assert body["wasteDirectionOutcomeBinding"]["paper_only"] is True
    assert body["wasteDirectionOutcomeBinding"]["runtime_changed"] is False
    assert body["wasteDirectionOutcomeBinding"]["would_apply_runtime_change"] is False
    assert body["wasteDirectionOutcomeBinding"]["would_lower_edge_threshold"] is False
    assert body["wasteDirectionOutcomeBinding"]["would_enable_live_trading"] is False
    assert body["wasteDirectionOutcomeBinding"]["broker_touched"] is False
    assert body["wasteDirectionOutcomeBinding"]["live_order_attempted"] is False
    assert body["wasteDirectionOutcomeBinding"]["owner_accept_created"] is False
    assert body["wasteDirectionOutcomeBinding"]["money_moved"] is False
    assert "wastePaperSampleCollector" in body
    assert body["wastePaperSampleCollector"]["report_kind"] == "cas_forex_waste_paper_sample_collector"
    assert body["wastePaperSampleCollector"]["dry_run"] is True
    assert body["wastePaperSampleCollector"]["read_only"] is True
    assert body["wastePaperSampleCollector"]["paper_only"] is True
    assert body["wastePaperSampleCollector"]["runtime_changed"] is False
    assert body["wastePaperSampleCollector"]["would_apply_runtime_change"] is False
    assert body["wastePaperSampleCollector"]["would_lower_edge_threshold"] is False
    assert body["wastePaperSampleCollector"]["would_enable_live_trading"] is False
    assert body["wastePaperSampleCollector"]["broker_touched"] is False
    assert body["wastePaperSampleCollector"]["broker_execution_touched"] is False
    assert body["wastePaperSampleCollector"]["live_order_attempted"] is False
    assert body["wastePaperSampleCollector"]["owner_accept_created"] is False
    assert body["wastePaperSampleCollector"]["money_moved"] is False
    assert "wastePaperSampleCollectorScheduler" in body
    assert body["wastePaperSampleCollectorScheduler"]["report_kind"] == "cas_forex_waste_paper_sample_collector_scheduler"
    assert body["wastePaperSampleCollectorScheduler"]["paper_only"] is True
    assert body["wastePaperSampleCollectorScheduler"]["read_only_market_actions_only"] is True
    assert body["wastePaperSampleCollectorScheduler"]["runtime_changed"] is False
    assert body["wastePaperSampleCollectorScheduler"]["would_apply_runtime_change"] is False
    assert body["wastePaperSampleCollectorScheduler"]["would_lower_edge_threshold"] is False
    assert body["wastePaperSampleCollectorScheduler"]["would_enable_live_trading"] is False
    assert body["wastePaperSampleCollectorScheduler"]["broker_touched"] is False
    assert body["wastePaperSampleCollectorScheduler"]["broker_execution_touched"] is False
    assert body["wastePaperSampleCollectorScheduler"]["live_order_attempted"] is False
    assert body["wastePaperSampleCollectorScheduler"]["owner_accept_created"] is False
    assert body["wastePaperSampleCollectorScheduler"]["money_moved"] is False
    assert "wasteAdaptationPromotionRule" in body
    assert body["wasteAdaptationPromotionRule"]["report_kind"] == "cas_forex_waste_adaptation_promotion_rule"
    assert body["wasteAdaptationPromotionRule"]["dry_run"] is True
    assert body["wasteAdaptationPromotionRule"]["read_only"] is True
    assert body["wasteAdaptationPromotionRule"]["runtime_changed"] is False
    assert body["wasteAdaptationPromotionRule"]["would_apply_runtime_change"] is False
    assert body["wasteAdaptationPromotionRule"]["would_lower_edge_threshold"] is False
    assert body["wasteAdaptationPromotionRule"]["would_enable_live_trading"] is False
    assert body["wasteAdaptationPromotionRule"]["broker_touched"] is False
    assert body["wasteAdaptationPromotionRule"]["live_order_attempted"] is False
    assert body["wasteAdaptationPromotionRule"]["owner_accept_created"] is False
    assert body["wasteAdaptationPromotionRule"]["money_moved"] is False
    assert "wasteAdaptationPlan" in body
    assert body["wasteAdaptationPlan"]["report_kind"] == "cas_forex_waste_adaptation_plan"
    assert body["wasteAdaptationPlan"]["dry_run"] is True
    assert body["wasteAdaptationPlan"]["runtime_changed"] is False
    assert body["wasteAdaptationPlan"]["broker_touched"] is False
    assert body["wasteAdaptationPlan"]["live_order_attempted"] is False
    assert body["wasteAdaptationPlan"]["money_moved"] is False
    assert "wasteAdaptationApplyPreview" in body
    assert body["wasteAdaptationApplyPreview"]["report_kind"] == "cas_forex_waste_adaptation_apply_preview"
    assert body["wasteAdaptationApplyPreview"]["dry_run"] is True
    assert body["wasteAdaptationApplyPreview"]["apply_allowed_now"] is False
    assert body["wasteAdaptationApplyPreview"]["runtime_changed"] is False
    assert body["wasteAdaptationApplyPreview"]["would_apply_runtime_change"] is False
    assert body["wasteAdaptationApplyPreview"]["would_lower_edge_threshold"] is False
    assert body["wasteAdaptationApplyPreview"]["would_enable_live_trading"] is False
    assert body["wasteAdaptationApplyPreview"]["broker_touched"] is False
    assert body["wasteAdaptationApplyPreview"]["live_order_attempted"] is False
    assert body["wasteAdaptationApplyPreview"]["owner_accept_created"] is False
    assert body["wasteAdaptationApplyPreview"]["money_moved"] is False
    assert "wasteAdaptationOwnerReview" in body
    assert body["wasteAdaptationOwnerReview"]["report_kind"] == "cas_forex_waste_adaptation_owner_review"
    assert body["wasteAdaptationOwnerReview"]["dry_run"] is True
    assert body["wasteAdaptationOwnerReview"]["paper_only"] is True
    assert body["wasteAdaptationOwnerReview"]["apply_allowed_now"] is False
    assert body["wasteAdaptationOwnerReview"]["runtime_changed"] is False
    assert body["wasteAdaptationOwnerReview"]["would_apply_runtime_change"] is False
    assert body["wasteAdaptationOwnerReview"]["would_lower_edge_threshold"] is False
    assert body["wasteAdaptationOwnerReview"]["would_enable_live_trading"] is False
    assert body["wasteAdaptationOwnerReview"]["broker_touched"] is False
    assert body["wasteAdaptationOwnerReview"]["live_order_attempted"] is False
    assert body["wasteAdaptationOwnerReview"]["owner_accept_created"] is False
    assert body["wasteAdaptationOwnerReview"]["money_moved"] is False
    assert "wasteAdaptationPaperApply" in body
    assert body["wasteAdaptationPaperApply"]["report_kind"] == "cas_forex_waste_adaptation_paper_apply"
    assert body["wasteAdaptationPaperApply"]["dry_run"] is True
    assert body["wasteAdaptationPaperApply"]["paper_only"] is True
    assert body["wasteAdaptationPaperApply"]["runtime_changed"] is False
    assert body["wasteAdaptationPaperApply"]["would_apply_runtime_change"] is False
    assert body["wasteAdaptationPaperApply"]["would_lower_edge_threshold"] is False
    assert body["wasteAdaptationPaperApply"]["would_enable_live_trading"] is False
    assert body["wasteAdaptationPaperApply"]["broker_touched"] is False
    assert body["wasteAdaptationPaperApply"]["live_order_attempted"] is False
    assert body["wasteAdaptationPaperApply"]["owner_accept_created"] is False
    assert body["wasteAdaptationPaperApply"]["money_moved"] is False
    assert "liveMoneyProgression" in body
    assert body["liveMoneyProgression"]["report_kind"] == "cas_forex_live_money_progression_packet"
    assert body["liveMoneyProgression"]["broker_touched"] is False
    assert body["liveMoneyProgression"]["live_order_attempted"] is False
    assert body["liveMoneyProgression"]["money_moved"] is False
    assert "mt5MarketDataDiagnostic" in body
    assert body["mt5MarketDataDiagnostic"]["report_kind"] == "cas_forex_mt5_market_data_diagnostic"
    assert body["mt5MarketDataDiagnostic"]["broker_touched"] is False
    assert "ownerPromotionReview" in body
    assert body["ownerPromotionReview"]["report_kind"] == "cas_forex_owner_promotion_review_summary"
    assert isinstance(body["ownerPromotionReview"]["strategy_edge_passed"], bool)
    assert any(check["gate_id"] == "owner_initial_investment" for check in body["liveReadiness"]["checks"])
    assert any(check["gate_id"] == "live_trading" for check in body["liveReadiness"]["checks"])
    assert body["mt5Receipt"]["receipt_validation_status"] == "BROKER_API_VERIFIED"
    assert body["mt5ProbeStatus"]["status"] in {"BROKER_API_VERIFIED", "UNAVAILABLE", "BLOCKED"}


def test_dashboard_cached_payload_overlays_live_scheduler_status():
    cached = {
        "agentWorkflowPlan": {"report_kind": "cached_full_payload"},
        "wastePaperSampleCollectorScheduler": {"running": False, "status": "STALE"},
        "wasteLoop": {"running": False, "status": "STALE"},
    }
    with api_server._dashboard_fast_cache_lock:
        api_server._dashboard_fast_cache.update(
            {
                "payload": {
                    "wastePaperSampleCollectorScheduler": {
                        "running": True,
                        "status": "WASTE_PAPER_SAMPLE_COLLECTOR_RUNNING",
                        "config": {"run_deal_history_ingest": True},
                    },
                    "wasteLoop": {
                        "running": True,
                        "status": "RUNNING",
                        "current_stage": "no_trade",
                        "cycles_run": 12,
                    },
                    "ownerControl": {"mode": "AI_FULL_AUTO_PAPER"},
                },
                "built_at": 123.0,
                "building": False,
                "error": None,
            }
        )

    packet = api_server._with_live_dashboard_overlays(cached)

    assert packet["agentWorkflowPlan"]["report_kind"] == "cached_full_payload"
    assert packet["wastePaperSampleCollectorScheduler"]["running"] is True
    assert packet["wastePaperSampleCollectorScheduler"]["config"]["run_deal_history_ingest"] is True
    assert packet["wasteLoop"]["running"] is True
    assert packet["wasteLoop"]["current_stage"] == "no_trade"
    assert packet["ownerControl"]["mode"] == "AI_FULL_AUTO_PAPER"


def test_dashboard_cached_payload_overlay_ignores_uncached_fast_builder(monkeypatch):
    cached = {
        "agentWorkflowPlan": {"report_kind": "cached_full_payload"},
        "wastePaperSampleCollectorScheduler": {"running": False, "status": "STALE"},
        "wasteLoop": {"running": False, "status": "STALE"},
    }
    with api_server._dashboard_fast_cache_lock:
        api_server._dashboard_fast_cache.update(
            {"payload": None, "built_at": 0.0, "building": False, "error": None}
        )
    monkeypatch.setattr(
        api_server,
        "dashboard_fast_state",
        lambda: {
            "wastePaperSampleCollectorScheduler": {
                "running": True,
                "status": "WASTE_PAPER_SAMPLE_COLLECTOR_RUNNING",
                "config": {"run_deal_history_ingest": True},
            },
            "wasteLoop": {
                "running": True,
                "status": "RUNNING",
                "current_stage": "no_trade",
                "cycles_run": 12,
            },
            "ownerControl": {"mode": "AI_FULL_AUTO_PAPER"},
        },
    )

    packet = api_server._with_live_dashboard_overlays(cached)

    assert packet["agentWorkflowPlan"]["report_kind"] == "cached_full_payload"
    assert packet["wastePaperSampleCollectorScheduler"]["status"] == "STALE"
    assert packet["wasteLoop"]["status"] == "STALE"
    assert "ownerControl" not in packet


def test_dashboard_shell_route_is_tiny_first_paint_packet():
    status, body = asyncio.run(_asgi_get("/api/forex/dashboard/shell"))
    assert status == 200
    assert body["dashboardMeta"]["kind"] == "shell"
    assert "uiReadiness" in body
    assert body["uiReadiness"]["summary_only"] is True
    assert body["uiReadiness"]["blockers"] == []
    assert body["uiReadiness"]["blocker_count"] > 0
    assert "authorityBoundary" in body
    authority = body["authorityBoundary"]
    assert authority["summary_only"] is True
    assert authority["allowed_scopes"] == []
    assert authority["allowed_scope_count"] > 0
    assert authority["blockers"] == []
    assert authority["blocker_count"] > 0
    assert authority["claim_boundary"] == ""
    assert authority["claim_boundary_present"] is True
    assert authority["can_place_live_orders"] is False
    assert "wasteLoop" in body
    assert body["wasteLoop"]["report_kind"] == "cas_forex_waste_runner_shell"
    assert "does not authorize live trading" in body["wasteLoop"]["claim_boundary"]
    assert "dailyBundle" not in body
    assert "dailySchedule" not in body
    assert "wastePaperSampleCollectorScheduler" not in body


def test_dashboard_fast_uses_tiny_proof_and_risk_summaries_with_full_reports_deferred():
    status, body = asyncio.run(_asgi_get("/api/forex/dashboard/fast"))
    assert status == 200
    assert body["dashboardMeta"]["kind"] == "fast"
    assert "uiReadiness" not in body
    proof_progress = body["proofProgress"]
    assert proof_progress["report_kind"] == "cas_forex_dashboard_proof_progress_summary"
    assert proof_progress["summary_only"] is True
    # Day counts track the LIVE proof ledger (the auto-runner advances them) —
    # assert self-consistency across the summary, not a frozen day number.
    completed_days = proof_progress["completed_trading_days"]
    assert completed_days >= 3
    assert proof_progress["complete_bundle_days"] == completed_days
    assert proof_progress["complete_bundle_date_count"] == completed_days
    assert proof_progress["min_daily_bundles_for_ui"] == 5
    assert proof_progress["chains_verified_count"] == completed_days
    assert proof_progress["chains_expected_count"] == completed_days
    assert proof_progress["paper_proof_chain_verified"] is True
    assert proof_progress["blocker_count"] > 0
    assert "authorityBoundary" not in body
    assert "movementStream" not in body
    assert "mt5Receipt" not in body
    assert "mt5ProbeStatus" not in body
    assert "wasteLoop" not in body
    owner = body["ownerControl"]
    assert owner["summary_only"] is True
    assert owner["claim_boundary"] == ""
    assert owner["claim_boundary_present"] is True
    assert owner["allowed_modes"] == []
    assert owner["allowed_mode_count"] > 0
    assert owner["override_state_path"] == ""
    assert owner["override_state_path_present"] is True
    assert "dailySchedule" not in body
    assert "dailyBundle" not in body
    assert "wastePaperSampleCollectorScheduler" not in body
    risk_budget = body["riskBudget"]
    assert risk_budget["report_kind"] == "cas_forex_dashboard_risk_budget_summary"
    assert risk_budget["summary_only"] is True
    assert risk_budget["claim_boundary"] == ""
    assert risk_budget["claim_boundary_present"] is True
    account_health = body["accountHealth"]
    assert account_health["report_kind"] == "cas_forex_account_health"
    assert account_health["summary_only"] is True
    assert "source_health" in account_health
    assert "price_source_status" in account_health["source_health"]
    assert "position_feed_detail" in account_health["source_health"]
    assert "static_positions" in account_health["source_health"]
    assert "stale_positions" in account_health["source_health"]
    # The sizing numbers summarize the LIVE risk-status evidence file — derive
    # the expectation from the same source instead of freezing values that
    # legitimately move with every sizing review.
    from api.data import PLAN_ID, PROOF_DIR

    risk_source = json.loads(
        (PROOF_DIR / f"{PLAN_ID}-paper-risk-status.json").read_text(encoding="utf-8")
    )
    latest_review = risk_source["latest_review"]
    sizing_rows = latest_review["sizing"]
    assert risk_budget["account_equity"] == latest_review["account_equity"]
    assert risk_budget["daily_risk_budget_usd"] == latest_review["daily_risk_budget_usd"]
    assert risk_budget["sizing_count"] == len(sizing_rows)
    expected_total = sum(row.get("planned_risk_usd", 0.0) for row in sizing_rows)
    assert round(risk_budget["planned_risk_total_usd"], 2) == round(expected_total, 2)
    assert risk_budget["planned_lots_total"] > 0

    status, readiness = asyncio.run(_asgi_get("/api/forex/proof/readiness"))
    assert status == 200
    assert readiness["claim_boundary"]
    assert readiness["complete_bundle_dates"]
    assert readiness["blockers"]
    assert readiness["next_ui_step"]

    status, full_authority = asyncio.run(_asgi_get("/api/forex/settings/authority-boundary"))
    assert status == 200
    assert full_authority["claim_boundary"]
    assert full_authority["allowed_scopes"]
    assert full_authority["blockers"]
    assert full_authority["can_place_live_orders"] is False

    status, full = asyncio.run(_asgi_get("/api/forex/bundle/daily"))
    assert status == 200
    assert full["claim_boundary"]
    assert full["latest_proof"]["status_path"]
    assert len(full["steps"]) == 3
    assert len(full["latest_proof"]["failure_reasons"]) > 0
    full_decision = full["latest_decision"]["latest_decision"]
    full_risk = full["latest_risk"]["latest_review"]
    assert full["latest_decision"]["claim_boundary"]
    assert full_decision["claim_boundary"]
    assert full["latest_decision"]["plan_id"]
    assert full["latest_decision"]["lead_id"]
    assert full["latest_decision"]["strategy_setting"]
    assert full_decision["decision_id"]
    assert full_decision["plan_id"]
    assert full_decision["lead_id"]
    assert full_decision["strategy_setting"]
    assert full_decision["macro_reason"]
    assert full["latest_risk"]["claim_boundary"]
    assert full_risk["claim_boundary"]
    assert full["latest_risk"]["plan_id"]
    assert full["latest_risk"]["lead_id"]
    assert full["latest_risk"]["strategy_setting"]
    assert full_risk["review_id"]
    assert full_risk["route_action"]
    assert full_risk["plan_id"]
    assert full_risk["lead_id"]
    assert len(full_decision["notes"]) > 0
    assert len(full_risk["notes"]) > 0
    assert len(full_decision["symbol_decisions"]) == 2
    assert len(full_risk["sizing"]) == risk_budget["sizing_count"]
    assert round(sum(row["planned_risk_usd"] for row in full_risk["sizing"]), 2) == round(
        risk_budget["planned_risk_total_usd"],
        2,
    )

    status, full_schedule = asyncio.run(_asgi_get("/api/forex/proof/schedule"))
    assert status == 200
    assert full_schedule.get("summary_only") is not True
    assert len(full_schedule["missing_tracks_for_next_due"]) == 3
    assert len(full_schedule["complete_bundle_dates"]) == 3
    assert len(full_schedule["notes"]) > 0
    assert full_schedule["recommended_command"].startswith("python scripts/run_daily_paper_bundle.py")
    assert full_schedule["claim_boundary"]

    status, full_readiness = asyncio.run(_asgi_get("/api/forex/proof/readiness"))
    assert status == 200
    assert len(full_readiness["complete_bundle_dates"]) == proof_progress["complete_bundle_date_count"]
    assert len(full_readiness["blockers"]) == proof_progress["blocker_count"]
    assert full_readiness["next_ui_step"]
    assert full_readiness["claim_boundary"]

    status, full_scheduler = asyncio.run(
        _asgi_get("/api/forex/waste-loop-control/paper-sample-collector/scheduler")
    )
    assert status == 200
    assert full_scheduler.get("summary_only") is not True
    assert full_scheduler["config"]
    assert full_scheduler["claim_boundary"]
    assert full_scheduler["next_action"]
    assert full_scheduler["paper_only"] is True
    assert full_scheduler["read_only_market_actions_only"] is True
    assert full_scheduler["runtime_changed"] is False
    assert full_scheduler["would_apply_runtime_change"] is False
    assert full_scheduler["would_lower_edge_threshold"] is False
    assert full_scheduler["would_enable_live_trading"] is False
    assert full_scheduler["broker_touched"] is False
    assert full_scheduler["broker_execution_touched"] is False
    assert full_scheduler["live_order_attempted"] is False
    assert full_scheduler["owner_accept_created"] is False
    assert full_scheduler["money_moved"] is False

    status, full_authority = asyncio.run(_asgi_get("/api/forex/settings/authority-boundary"))
    assert status == 200
    assert len(full_authority["allowed_scopes"]) > 0
    assert len(full_authority["blockers"]) > 0
    assert full_authority["claim_boundary"]
    assert "summary_only" not in full_authority

    status, full_owner = asyncio.run(_asgi_get("/api/forex/settings/owner-control"))
    assert status == 200
    assert full_owner["claim_boundary"]
    assert len(full_owner["allowed_modes"]) == owner["allowed_mode_count"]
    assert full_owner["override_state_path"]
    assert "summary_only" not in full_owner


def test_dashboard_evidence_panels_uses_central_daily_bundle_hydration():
    component = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardEvidencePanels.tsx"
    ).read_text(encoding="utf-8")
    hydrator = (
        REPO_ROOT / "ui" / "src" / "data" / "dashboardApi.ts"
    ).read_text(encoding="utf-8")

    assert "fetchDailyBundle" not in component
    assert "state.dailyBundle" in component
    assert "fetchDailyBundle" in hydrator
    assert "scheduleFullDailyBundleHydration" in hydrator


def test_dashboard_movement_panel_marks_static_fallback_explicitly():
    component = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardEvidencePanels.tsx"
    ).read_text(encoding="utf-8")
    movement_helper = (
        REPO_ROOT / "ui" / "src" / "util" / "movementSource.ts"
    ).read_text(encoding="utf-8")
    workbench = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardOperationsWorkbench.tsx"
    ).read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    deep_api_client = (REPO_ROOT / "ui" / "src" / "data" / "dashboardDeepApi.ts").read_text(encoding="utf-8")

    # Fixture-file assertions removed with ui/src/data/fixtures.ts (2026-08-10);
    # it was dead code imported by nothing. The component and helper assertions
    # below still cover the behaviour this test is named for.
    assert "Real-Time Movement Scaffold" not in component
    assert "Movement Source: Static Simulation" in movement_helper
    assert "summarizeMovementSource" in component
    assert "Static simulator rows are not being moved by usable provider/MT5 quotes right now" in movement_helper
    assert 'label={q.stale ? "STATIC" : "LIVE QUOTE"}' in component
    assert "fetchMovementStream(useProvider = true)" in api_client
    assert "fetchMovementStream(useProvider = true)" in deep_api_client
    assert "const suffix = useProvider ? \"\" : \"?use_provider=false\"" in api_client
    assert "fetchMovementStream(true)" in workbench


def test_settings_owner_control_shows_staged_autonomy_ladder():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    evidence_types = (REPO_ROOT / "ui" / "src" / "types" / "evidence.ts").read_text(encoding="utf-8")

    assert '{ value: "DENY", label: "Lockdown" }' in settings_page
    assert '{ value: "NOTIFY_ONLY", label: "Signal" }' in settings_page
    assert '{ value: "LIVE_AUTO", label: "Live Confirm" }' in settings_page
    assert "Live Autopilot Request" in settings_page
    assert "autonomyLadder.map" in settings_page
    assert "Staged autonomy ladder is loading." in settings_page
    assert "staged_autonomy_summary" in settings_page
    assert "OwnerAutonomyStage" in evidence_types
    assert "current_autonomy_stage" in evidence_types
    assert "owner_control_allows_live_trades" in evidence_types


def test_dashboard_deep_operations_staggers_core_panel_hydration():
    dashboard = (
        REPO_ROOT / "ui" / "src" / "pages" / "DashboardPage.tsx"
    ).read_text(encoding="utf-8")
    deep_operations_shell = REPO_ROOT / "ui" / "src" / "components" / "DashboardDeepOperations.tsx"
    component = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardOperationsWorkbench.tsx"
    ).read_text(encoding="utf-8")

    assert not deep_operations_shell.exists()
    assert 'lazy(() => import("../components/DashboardOperationsWorkbench")' in dashboard
    assert "DashboardDeepOperations" not in dashboard
    assert "DASHBOARD_DEEP_OPERATIONS_IDLE_TIMEOUT_MS = 1_600" in dashboard
    assert "requestIdleCallback" in dashboard
    assert "setDeepOperationsMounted(true)" in dashboard
    assert "<DashboardOperationsWorkbench state={state} />" in dashboard
    assert "DashboardDeferredSectionsNotice" in dashboard
    assert "dashboardDeepApiPromise" not in dashboard
    assert "function loadCorePanels" not in component
    assert "interface DashboardOperationsWorkbenchProps" in component
    assert "DashboardDeepOperationsProps" not in component
    assert "DASHBOARD_ACCOUNT_LEDGER_FIRST_LOAD_MS = 1_600" in component
    assert "DASHBOARD_MOVEMENT_FIRST_LOAD_MS = 2_100" in component
    assert "DASHBOARD_RECONCILIATION_FIRST_LOAD_MS = 2_600" in component
    assert "DASHBOARD_LIVE_READINESS_FIRST_LOAD_MS = 3_100" in component
    assert "DASHBOARD_CORE_POLL_MS = 30_000" in component
    assert "DASHBOARD_LOOP_CORE_POLL_MS = 15_000" in component
    assert "DASHBOARD_DEEP_CACHE_SNAPSHOT_IDLE_TIMEOUT_MS = 700" in component
    assert component.count("scheduleCorePoll(") == 4
    assert "DASHBOARD_SWEEP_WORKBENCH_IDLE_TIMEOUT_MS = 3_200" in component
    assert "DASHBOARD_EVIDENCE_PANELS_IDLE_TIMEOUT_MS = 2_400" in component
    assert "DASHBOARD_LIVE_OPERABILITY_IDLE_TIMEOUT_MS = 3_600" in component
    assert "DASHBOARD_COMPOUND_ADD_IDLE_TIMEOUT_MS = 4_000" in component
    assert "function scheduleDashboardIdleWork" in component
    assert "function scheduleDashboardRecurringWork" in component
    assert "requestIdleCallback" in component
    assert "const cancelDeepCacheSnapshot = scheduleDashboardIdleWork(() => {" in component
    assert "}, DASHBOARD_DEEP_CACHE_SNAPSHOT_IDLE_TIMEOUT_MS);" in component
    assert "cancelDeepCacheSnapshot();" in component
    assert "const cancelStrategyLeadsPoll = scheduleDashboardRecurringWork(" in component
    assert "cancelCorePolls.push(scheduleDashboardRecurringWork(load, firstDelayMs, DASHBOARD_CORE_POLL_MS));" in component
    assert "const cancelSweepPoll = scheduleDashboardRecurringWork(" in component
    assert "const cancelAutoHaltPoll = scheduleDashboardRecurringWork(" in component
    assert "const cancelLoopPolls: Array<() => void> = [];" in component
    assert "scheduleDashboardRecurringWork(loadLoopCore, DASHBOARD_LOOP_CORE_FIRST_LOAD_MS, DASHBOARD_LOOP_CORE_POLL_MS)" in component
    assert "scheduleDashboardRecurringWork(loadMarketEvidence, DASHBOARD_MARKET_EVIDENCE_FIRST_LOAD_MS, DASHBOARD_DEEP_EVIDENCE_POLL_MS)" in component
    assert "firstLoad = window.setTimeout" not in component
    assert "const coreFirstLoad = window.setTimeout" not in component
    assert "marketEvidenceFirstLoad = window.setTimeout" not in component
    assert "window.setInterval(load, DASHBOARD_CORE_POLL_MS)" not in component
    assert "const [sweepOpsPanelReady, setSweepOpsPanelReady]" in component
    assert "const [evidencePanelsReady, setEvidencePanelsReady]" in component
    assert "const [liveOperabilityPanelReady, setLiveOperabilityPanelReady]" in component
    assert "sweepOpsPanelReady ? (" in component
    assert "evidencePanelsReady ? (" in component
    assert "liveOperabilityPanelReady ? (" in component
    assert "<DashboardSweepOpsPanelFallback />" in component
    assert "<DashboardEvidencePanelsFallback />" in component
    assert "<LiveOperabilityPanelFallback />" in component
    assert "DASHBOARD_EVIDENCE_PANELS_IDLE_TIMEOUT_MS" in component.split("setEvidencePanelsReady(true)", 1)[1]
    assert "DASHBOARD_LIVE_OPERABILITY_IDLE_TIMEOUT_MS" in component.split("setLiveOperabilityPanelReady(true)", 1)[1]
    assert "operationsPanelReady" not in component


def test_dashboard_sweep_panel_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    panel = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardSweepOpsPanel.tsx"
    ).read_text(encoding="utf-8")
    panel_css = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardSweepOpsPanel.css"
    ).read_text(encoding="utf-8")

    assert 'import "./DashboardSweepOpsPanel.css"' in panel
    assert 'import { lazy, Suspense, useEffect, useState } from "react";' in panel
    assert "DASHBOARD_BROKER_TRUTH_PANEL_IDLE_TIMEOUT_MS = 1_200" in panel
    assert "function scheduleSweepIdleWork" in panel
    assert "requestIdleCallback" in panel
    assert "const [brokerTruthPanelReady, setBrokerTruthPanelReady] = useState(false);" in panel
    assert "setBrokerTruthPanelReady(true)" in panel
    assert "brokerTruthPanelReady ? (" in panel
    assert "<DashboardBrokerTruthOpsPanel ops={brokerTruthOps} />" in panel
    assert "<DashboardBrokerTruthOpsPanelFallback />" in panel
    assert 'payoutActionReady ? "Confirm Payout" : "Request Payout Setup"' in panel
    assert 'label={`RAIL ${payoutRuntimeStatus}`}' in panel
    assert "providerRuntime?.detail" in panel
    assert panel.index("brokerTruthPanelReady ? (") < panel.index(
        "<DashboardBrokerTruthOpsPanel ops={brokerTruthOps} />"
    )
    for lazy_panel_selector in (
        ".sweep-cockpit",
        ".sweep-control-grid",
        ".sweep-control-field",
        ".sweep-range",
        ".sweep-number",
        ".auto-halt-strip",
        ".auto-halt-check-grid",
        ".broker-truth-monitor-strip",
    ):
        assert lazy_panel_selector not in app_css
        assert lazy_panel_selector in panel_css


def test_broker_truth_ui_surfaces_monitor_auto_halt_reasons_and_position_protection():
    evidence_types = (REPO_ROOT / "ui" / "src" / "types" / "evidence.ts").read_text(encoding="utf-8")
    broker_truth_panel = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardBrokerTruthOpsPanel.tsx"
    ).read_text(encoding="utf-8")
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")

    assert "position_protection_status?: string | null;" in evidence_types
    assert "position_protection_unprotected_position_count?: number;" in evidence_types
    assert "auto_halt_latched_from_monitor?: boolean;" in evidence_types
    assert "monitor_auto_halt_reason_ids?: string[];" in evidence_types
    assert "MONITOR PAPER FORCE" in broker_truth_panel
    assert "position_protection_detail" in broker_truth_panel
    assert "monitor_auto_halt_reason_ids" in broker_truth_panel
    assert "Truth Auto-Halt" in settings_page
    assert "Truth Halt Reasons" in settings_page
    assert "Position Protection" in settings_page
    assert "Unprotected Positions" in settings_page


def test_quick_start_page_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    quick_start_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "QuickStartPage.tsx"
    ).read_text(encoding="utf-8")
    quick_start_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "QuickStartPage.css"
    ).read_text(encoding="utf-8")

    assert 'import "./QuickStartPage.css"' in quick_start_page
    for route_selector in (
        ".quick-start-page",
        ".quick-start-controls",
        ".quick-start-list",
        ".quick-start-item",
        ".quick-start-pwa-actions",
        ".quick-start-pwa-self-mark",
        ".quick-start-launch-sequence",
        ".quick-start-completion-banner",
    ):
        assert route_selector not in app_css
        assert route_selector in quick_start_css


def test_quick_start_exposes_professional_launch_sequence():
    quick_start_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "QuickStartPage.tsx"
    ).read_text(encoding="utf-8")
    assert "Professional Launch Sequence" in quick_start_page
    assert "buildLaunchSequence(milestones)" in quick_start_page
    assert "Observe mode online" in quick_start_page
    assert "Demo broker terminal connected" in quick_start_page
    assert "Risk profile and CAS dials reviewed" in quick_start_page
    assert "Paper or demo loop running" in quick_start_page
    assert "First AI decision reviewed" in quick_start_page
    assert "Live unlock reviewed last" in quick_start_page


def test_trading_windows_page_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    windows_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.tsx"
    ).read_text(encoding="utf-8")
    windows_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.css"
    ).read_text(encoding="utf-8")

    assert 'import "./WindowsPage.css"' in windows_page
    assert "TradingWindow" in windows_page
    for route_selector in (
        ".windows-grid",
        ".trading-window",
        ".trading-window-controls",
        ".tw-account-bar",
        ".tw-positions-table",
        ".tw-market-strip",
        ".tw-loop-bar",
        ".tw-loop-chip",
    ):
        assert route_selector not in app_css
        assert route_selector in windows_css


def test_auto_trade_loop_sanitizes_raw_live_gate_last_error():
    windows_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.tsx"
    ).read_text(encoding="utf-8")
    windows_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.css"
    ).read_text(encoding="utf-8")

    assert "formatDispatchLoopLastError(loop?.last_error)" in windows_page
    assert 'rawLower.includes("live_trading is currently not licensed")' in windows_page
    assert "Live mode is requested, but the live runtime gates are not ready" in windows_page
    assert "it will not collect or dispatch intents until those gates pass" in windows_page
    assert 'className="tw-loop-warning"' in windows_page
    assert "error: {loop.last_error}" not in windows_page
    assert ".tw-loop-warning" in windows_css


def test_decision_history_page_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    decision_history_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "DecisionHistoryPage.tsx"
    ).read_text(encoding="utf-8")
    decision_history_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "DecisionHistoryPage.css"
    ).read_text(encoding="utf-8")

    assert 'import "./DecisionHistoryPage.css"' in decision_history_page
    assert "DecisionHistoryRow" in decision_history_page
    for route_selector in (
        ".decision-history-page",
        ".decision-history-header",
        ".decision-history-controls",
        ".decision-history-list",
        ".decision-history-row",
        ".decision-summary-clamped",
        ".decision-chain-detail",
        ".decision-history-empty",
    ):
        assert route_selector not in app_css
        assert route_selector in decision_history_css


def test_strategy_comparison_page_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    strategy_comparison_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "StrategyComparisonPage.tsx"
    ).read_text(encoding="utf-8")
    strategy_comparison_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "StrategyComparisonPage.css"
    ).read_text(encoding="utf-8")

    assert 'import "./StrategyComparisonPage.css"' in strategy_comparison_page
    for route_selector in (
        ".strategy-comparison-page",
        ".comparison-mode-toggle",
        ".comparison-table",
        ".comparison-row",
        ".score-teal",
        ".score-yellow",
        ".score-muted",
        ".diff-panel",
        ".diff-controls",
    ):
        assert route_selector not in app_css
        assert route_selector in strategy_comparison_css
    assert ".limit-selector" in app_css
    assert 'className="limit-selector"' in strategy_comparison_page


def test_daily_report_page_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    daily_report_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "DailyReportPage.tsx"
    ).read_text(encoding="utf-8")
    daily_report_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "DailyReportPage.css"
    ).read_text(encoding="utf-8")

    assert 'import "./DailyReportPage.css"' in daily_report_page
    for route_selector in (
        ".daily-report-page",
        ".report-overall-headline",
        ".daily-section",
        ".daily-section-header",
        ".daily-section-metrics",
        ".daily-section-events",
        ".report-diagnostic-hints",
    ):
        assert route_selector not in app_css
        assert route_selector in daily_report_css
    for shared_selector in (
        ".stack-status-row",
        ".plain-english-block",
        ".limit-selector",
    ):
        assert shared_selector in app_css
        assert f'className="{shared_selector[1:]}"' in daily_report_page


def test_tracker_page_is_registered_and_css_is_lazy_not_root_first_paint():
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    page_config = (REPO_ROOT / "ui" / "src" / "pageConfig.ts").read_text(encoding="utf-8")
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    tracker_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "TrackerPage.tsx"
    ).read_text(encoding="utf-8")
    tracker_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "TrackerPage.css"
    ).read_text(encoding="utf-8")

    assert '{ id: "tracker", label: "Tracker", ready: true }' in page_config
    assert 'tracker: lazyPage(() => import("./pages/TrackerPage"), "TrackerPage")' in app
    assert 'import "./TrackerPage.css"' in tracker_page
    assert "fetchMobileProofSessionLatest" in tracker_page
    assert "fetchLiveReadiness" in tracker_page
    assert "fetchMovementStream(true)" in tracker_page
    assert "fetchAccountLedger" in tracker_page
    assert 'label="Price source"' in tracker_page
    assert 'label="Position feed"' in tracker_page
    assert 'label="Broker-ticket rows"' in tracker_page
    assert 'label="Static positions"' in tracker_page
    assert 'label="Provider-backed"' in tracker_page
    assert 'label="Static fallback"' in tracker_page
    assert "positionFeed.detail" in tracker_page
    assert "Static simulator rows are not being moved by usable provider/MT5 quotes" in tracker_page
    for route_selector in (
        ".tracker-page",
        ".tracker-grid",
        ".tracker-hero-grid",
        ".tracker-metric-grid",
        ".tracker-list-row",
        ".tracker-check-row",
        ".tracker-symbol-strip",
    ):
        assert route_selector not in app_css
        assert route_selector in tracker_css


def test_risk_disclosure_page_is_registered_and_surfaces_claim_boundaries():
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    page_config = (REPO_ROOT / "ui" / "src" / "pageConfig.ts").read_text(encoding="utf-8")
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    risk_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "RiskDisclosurePage.tsx"
    ).read_text(encoding="utf-8")
    terms_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "TermsPage.tsx"
    ).read_text(encoding="utf-8")
    privacy_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "PrivacyPage.tsx"
    ).read_text(encoding="utf-8")
    risk_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "RiskDisclosurePage.css"
    ).read_text(encoding="utf-8")

    assert '{ id: "risk", label: "Risk", ready: true }' in page_config
    assert '{ id: "terms", label: "Terms", ready: true }' in page_config
    assert '{ id: "privacy", label: "Privacy", ready: true }' in page_config
    assert 'risk: lazyPage(() => import("./pages/RiskDisclosurePage"), "RiskDisclosurePage")' in app
    assert 'terms: lazyPage(() => import("./pages/TermsPage"), "TermsPage")' in app
    assert 'privacy: lazyPage(() => import("./pages/PrivacyPage"), "PrivacyPage")' in app
    assert 'import "./RiskDisclosurePage.css"' in risk_page
    assert 'import "./RiskDisclosurePage.css"' in terms_page
    assert 'import "./RiskDisclosurePage.css"' in privacy_page
    assert "fetchProfessionalClaims" in risk_page
    assert "Risk Disclosure" in risk_page
    assert "No Profit Guarantee" in risk_page
    assert "AI Limitations" in risk_page
    assert "Broker Execution" in risk_page
    assert "Paper, Demo, and Live" in risk_page
    assert "forbidden_claim_types" in risk_page
    assert "preferred_language" in risk_page
    assert "minimum_copy" in risk_page
    assert "This page is disclosure visibility only" in risk_page
    assert "Terms of Service" in terms_page
    assert "REQUIRED BEFORE PUBLIC USE" in terms_page
    assert "No Profit Guarantee" in terms_page
    assert "Owner Responsibility" in terms_page
    assert "Privacy Policy" in privacy_page
    assert "Data CAS Forex May Store" in privacy_page
    assert "Secrets" in privacy_page
    assert "raw bank-card numbers" in privacy_page
    for route_selector in (
        ".risk-disclosure-page",
        ".risk-disclosure-status-grid",
        ".risk-disclosure-copy-grid",
        ".risk-disclosure-policy-grid",
        ".risk-disclosure-table",
        ".risk-disclosure-boundary",
    ):
        assert route_selector not in app_css
        assert route_selector in risk_css


def test_stack_status_page_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    stack_status_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "StackStatusPage.tsx"
    ).read_text(encoding="utf-8")
    stack_status_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "StackStatusPage.css"
    ).read_text(encoding="utf-8")

    assert 'import "./StackStatusPage.css"' in stack_status_page
    for route_selector in (
        ".stack-status-page",
        ".stack-status-table",
        ".stack-remediation-list",
    ):
        assert route_selector not in app_css
        assert route_selector in stack_status_css
    for shared_selector in (
        ".stack-status-row",
        ".plain-english-block",
    ):
        assert shared_selector in app_css
        assert f'className="{shared_selector[1:]}"' in stack_status_page


def test_proof_page_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    proof_page = (REPO_ROOT / "ui" / "src" / "pages" / "ProofPage.tsx").read_text(
        encoding="utf-8"
    )
    proof_css = (REPO_ROOT / "ui" / "src" / "pages" / "ProofPage.css").read_text(
        encoding="utf-8"
    )

    assert 'import "./ProofPage.css"' in proof_page
    for route_selector in (
        ".lead-grid",
        ".proof-grid-2col",
        ".progress-stack",
        ".hash-stack",
        ".hash-row",
        ".checklist-grid",
        ".route-list",
        ".route-card",
        ".sizing-grid",
        ".next-action",
        ".not-licensed-grid",
        ".lock-reason-list",
    ):
        assert route_selector not in app_css
        assert route_selector in proof_css
    for shared_selector in (
        ".lead-field",
        ".field-label",
        ".field-value",
        ".disabled-control",
        ".go-live-switch",
    ):
        assert shared_selector in app_css


def test_audit_page_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    audit_page = (REPO_ROOT / "ui" / "src" / "pages" / "AuditPage.tsx").read_text(
        encoding="utf-8"
    )
    audit_css = (REPO_ROOT / "ui" / "src" / "pages" / "AuditPage.css").read_text(
        encoding="utf-8"
    )

    assert 'import "./AuditPage.css"' in audit_page
    for route_selector in (
        ".pipeline",
        ".pipeline-stage",
        ".pipeline-card",
        ".evidence-summary",
        ".evidence-row",
        ".trace-detail",
        ".trace-grid",
        ".trace-rationale",
    ):
        assert route_selector not in app_css
        assert route_selector in audit_css


def test_pcba_page_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    pcba_page = (REPO_ROOT / "ui" / "src" / "pages" / "PcbaPage.tsx").read_text(
        encoding="utf-8"
    )
    pcba_css = (REPO_ROOT / "ui" / "src" / "pages" / "PcbaPage.css").read_text(
        encoding="utf-8"
    )

    assert 'import "./PcbaPage.css"' in pcba_page
    for route_selector in (
        ".pcba-boards-grid",
        ".pcba-board-card",
        ".pcba-board-header",
        ".pcba-component-chip",
        ".pcba-claim-note",
        ".cjt-features",
        ".cjt-feature-row",
        ".component-catalog-grid",
        ".event-context-grid",
        ".temporal-grid",
        ".temporal-cell",
        ".optimizer-detail",
    ):
        assert route_selector not in app_css
        assert route_selector in pcba_css


def test_strategy_review_route_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    strategy_dev_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "StrategyDevPage.tsx"
    ).read_text(encoding="utf-8")
    strategy_dev_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "StrategyDevPage.css"
    ).read_text(encoding="utf-8")
    forex_fury_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "ForexFuryPage.tsx"
    ).read_text(encoding="utf-8")
    forex_fury_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "ForexFuryPage.css"
    ).read_text(encoding="utf-8")
    shared_action_css = (
        REPO_ROOT / "ui" / "src" / "components" / "StrategyActionControls.css"
    ).read_text(encoding="utf-8")

    assert 'import "./StrategyDevPage.css"' in strategy_dev_page
    assert 'import "./ForexFuryPage.css"' in forex_fury_page
    assert 'import "../components/StrategyActionControls.css"' in strategy_dev_page
    assert 'import "../components/StrategyActionControls.css"' in forex_fury_page
    for route_selector in (
        ".strategy-dev-filter-row",
        ".strategy-dev-filter-select",
        ".strategy-dev-list",
        ".strategy-dev-row",
        ".strategy-dev-note-input",
        ".strategy-dev-action-buttons",
    ):
        assert route_selector not in app_css
        assert route_selector in strategy_dev_css
    for route_selector in (
        ".fury-candidates-table",
        ".fury-candidate-row",
        ".fury-row-action",
    ):
        assert route_selector not in app_css
        assert route_selector in forex_fury_css
    for shared_selector in (
        ".strategy-action-button",
        ".action-result-toast",
        ".action-result-ok",
        ".action-result-err",
    ):
        assert shared_selector not in app_css
        assert shared_selector in shared_action_css


def test_trade_page_and_selector_css_are_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    trade_page = (REPO_ROOT / "ui" / "src" / "pages" / "TradePage.tsx").read_text(
        encoding="utf-8"
    )
    trade_css = (REPO_ROOT / "ui" / "src" / "pages" / "TradePage.css").read_text(
        encoding="utf-8"
    )
    selector_css = (
        REPO_ROOT / "ui" / "src" / "components" / "SelectorChips.css"
    ).read_text(encoding="utf-8")
    mtf_component = (
        REPO_ROOT / "ui" / "src" / "components" / "MultiTimeframeSelector.tsx"
    ).read_text(encoding="utf-8")
    mtf_css = (
        REPO_ROOT / "ui" / "src" / "components" / "MultiTimeframeSelector.css"
    ).read_text(encoding="utf-8")
    condition_lab_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "ConditionLabPage.tsx"
    ).read_text(encoding="utf-8")
    settings_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx"
    ).read_text(encoding="utf-8")

    assert 'import "./TradePage.css"' in trade_page
    assert 'import "../components/SelectorChips.css"' in trade_page
    assert "fetchMovementStream(true)" in trade_page
    assert "Active Market Movement - Static Simulation" in trade_page
    assert "Static simulator pricing" in trade_page
    assert "Position Source" in trade_page
    assert "Opened" in trade_page
    assert "Age" in trade_page
    assert "formatMovementPositionAge(activePosition)" in trade_page
    assert 'label={`${movementSource.staticFallbackCount} STATIC`}' in trade_page
    assert 'import "../components/SelectorChips.css"' in condition_lab_page
    assert 'import "../components/SelectorChips.css"' in settings_page
    assert 'import "./SelectorChips.css"' in mtf_component
    assert 'import "./MultiTimeframeSelector.css"' in mtf_component
    for route_selector in (
        ".trade-selectors",
        ".selector-group",
        ".selector-label",
        ".trade-grid-2col",
        ".proposal-preview",
        ".proposal-header",
        ".proposal-prices",
        ".price-block",
        ".price-value",
        ".proposal-meta",
        ".meta-row",
        ".proposal-rationale",
        ".sizing-rationale",
        ".sizing-preview",
        ".sizing-preview-header",
        ".sizing-preview-grid",
        ".size-field",
        ".risk-budget-summary",
        ".budget-row",
        ".forecast-grid",
        ".forecast-model",
        ".forecast-model-header",
        ".forecast-model-name",
        ".forecast-model-detail",
        ".cas-expression",
        ".cas-expr-row",
        ".cas-expr-code",
        ".trade-action",
        ".trade-action-buttons",
        ".btn-paper",
        ".btn-send",
        ".trade-action-reasons",
        ".trade-action-status",
        ".lock-line",
        ".no-signal",
    ):
        assert route_selector not in app_css
        assert route_selector in trade_css
    for shared_selector in (
        ".selector-chips",
        ".selector-chip",
    ):
        assert shared_selector not in app_css
        assert shared_selector in selector_css
    for mtf_selector in (
        ".mtf-selector",
        ".mtf-chips",
        ".mtf-loading",
        ".mtf-error",
        ".mtf-summary",
    ):
        assert mtf_selector not in app_css
        assert mtf_selector in mtf_css
    assert ".placeholder-badge" in app_css


def test_adaptive_page_css_and_route_primitives_are_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    adaptive_page = (
        REPO_ROOT / "ui" / "src" / "pages" / "AdaptivePage.tsx"
    ).read_text(encoding="utf-8")
    adaptive_css = (
        REPO_ROOT / "ui" / "src" / "pages" / "AdaptivePage.css"
    ).read_text(encoding="utf-8")
    route_primitives_css = (
        REPO_ROOT / "ui" / "src" / "components" / "RoutePrimitives.css"
    ).read_text(encoding="utf-8")
    proof_css = (REPO_ROOT / "ui" / "src" / "pages" / "ProofPage.css").read_text(
        encoding="utf-8"
    )

    assert 'import "./AdaptivePage.css"' in adaptive_page
    assert 'import "../components/RoutePrimitives.css"' in adaptive_page
    for page_name in (
        "ConditionLabPage",
        "HistoryPage",
        "LedgerPage",
        "ProofPage",
        "TradePage",
    ):
        page = (REPO_ROOT / "ui" / "src" / "pages" / f"{page_name}.tsx").read_text(
            encoding="utf-8"
        )
        assert 'import "../components/RoutePrimitives.css"' in page
    for route_selector in (
        ".action-chips",
        ".adaptive-action-chip",
        ".basket-grid",
        ".basket-card",
        ".basket-card-header",
        ".basket-card-body",
        ".adaptive-decisions-table-wrap",
        ".memory-grid",
        ".memory-card",
        ".memory-card-header",
        ".memory-card-body",
    ):
        assert route_selector not in app_css
        assert route_selector in adaptive_css
    for shared_route_selector in (
        ".route-symbol",
        ".sizing-row",
    ):
        assert shared_route_selector not in app_css
        assert shared_route_selector not in proof_css
        assert shared_route_selector in route_primitives_css


def test_live_component_css_is_lazy_not_root_first_paint():
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    live_telemetry = (
        REPO_ROOT / "ui" / "src" / "components" / "LiveTradesTelemetry.tsx"
    ).read_text(encoding="utf-8")
    portfolio = (
        REPO_ROOT / "ui" / "src" / "components" / "PortfolioRiskCard.tsx"
    ).read_text(encoding="utf-8")
    agent = (
        REPO_ROOT / "ui" / "src" / "components" / "AgentDecisionCard.tsx"
    ).read_text(encoding="utf-8")
    loop = (
        REPO_ROOT / "ui" / "src" / "components" / "AutonomousLoopCard.tsx"
    ).read_text(encoding="utf-8")
    operator = (
        REPO_ROOT / "ui" / "src" / "components" / "OperatorBriefingCard.tsx"
    ).read_text(encoding="utf-8")
    history_row = (
        REPO_ROOT / "ui" / "src" / "components" / "DecisionHistoryRow.tsx"
    ).read_text(encoding="utf-8")
    notifications = (
        REPO_ROOT / "ui" / "src" / "components" / "NotificationSubscriptionPanel.tsx"
    ).read_text(encoding="utf-8")
    webhook = (
        REPO_ROOT / "ui" / "src" / "components" / "WebhookSubscriptionPanel.tsx"
    ).read_text(encoding="utf-8")
    telemetry_css = (
        REPO_ROOT / "ui" / "src" / "components" / "LiveTelemetryTable.css"
    ).read_text(encoding="utf-8")
    decision_css = (
        REPO_ROOT / "ui" / "src" / "components" / "DecisionCardPrimitives.css"
    ).read_text(encoding="utf-8")
    portfolio_css = (
        REPO_ROOT / "ui" / "src" / "components" / "PortfolioRiskCard.css"
    ).read_text(encoding="utf-8")
    subscription_css = (
        REPO_ROOT / "ui" / "src" / "components" / "SubscriptionPanels.css"
    ).read_text(encoding="utf-8")

    assert 'import "./LiveTelemetryTable.css"' in live_telemetry
    assert 'import "./LiveTelemetryTable.css"' in portfolio
    assert 'import "./PortfolioRiskCard.css"' in portfolio
    assert 'import "./DecisionCardPrimitives.css"' in agent
    assert 'import "./DecisionCardPrimitives.css"' in loop
    assert 'import "./DecisionCardPrimitives.css"' in operator
    assert 'import "./DecisionCardPrimitives.css"' in history_row
    assert 'import "./LiveTelemetryTable.css"' in notifications
    assert 'import "./SubscriptionPanels.css"' in notifications
    assert 'import "./LiveTelemetryTable.css"' in webhook
    assert 'import "./SubscriptionPanels.css"' in webhook

    for telemetry_selector in (
        ".live-telemetry-header",
        ".live-telemetry-stat",
        ".live-telemetry-table-wrap",
        ".live-telemetry-table",
        ".live-telemetry-source",
        ".live-telemetry-empty",
        ".live-telemetry-boundary",
        ".live-telemetry-error",
    ):
        assert telemetry_selector not in app_css
        assert telemetry_selector in telemetry_css
    for decision_selector in (
        ".agent-decision-card",
        ".autonomous-loop-card",
        ".decision-status-row",
        ".decision-cycle-id",
        ".decision-summary",
        ".decision-empty",
        ".decision-next-action",
        ".decision-chain",
        ".loop-stats",
        ".loop-last-cycle",
        ".loop-last-cycle-iso",
        ".loop-next-due",
        ".loop-diagnostic",
        ".operator-briefing-card",
    ):
        assert decision_selector not in app_css
        assert decision_selector in decision_css
    for portfolio_selector in (
        ".portfolio-risk-card",
        ".portfolio-risk-header",
        ".risk-meter-row",
        ".risk-meter-header",
        ".risk-meter",
        ".risk-meter-fill",
        ".risk-symbol-table",
        ".portfolio-risk-hints",
    ):
        assert portfolio_selector not in app_css
        assert portfolio_selector in portfolio_css
    for subscription_selector in (
        ".notification-subscription-panel",
        ".notification-status-row",
        ".notification-button-row",
        ".notification-button",
        ".notification-status-chip",
        ".webhook-subscription-panel",
        ".webhook-add-form",
        ".webhook-row",
    ):
        assert subscription_selector not in app_css
        assert subscription_selector in subscription_css


def test_ai_activity_instant_badge_renders_stage_trace_without_fetching():
    instant_badge = (
        REPO_ROOT / "ui" / "src" / "components" / "AiActivityInstantBadge.tsx"
    ).read_text(encoding="utf-8")
    instant_css = (
        REPO_ROOT / "ui" / "src" / "components" / "AiActivityInstantBadge.css"
    ).read_text(encoding="utf-8")
    full_indicator = (
        REPO_ROOT / "ui" / "src" / "components" / "AiActivityIndicator.tsx"
    ).read_text(encoding="utf-8")
    full_css = (
        REPO_ROOT / "ui" / "src" / "components" / "AiActivityIndicator.css"
    ).read_text(encoding="utf-8")

    assert 'import "./AiActivityInstantBadge.css"' in instant_badge
    assert "AiActivityIndicator.css" not in instant_badge
    assert "ai-activity-trace" in instant_badge
    assert "stage_trace" in instant_badge
    assert "TRACE_LABELS" in instant_badge
    assert '"Test"' in instant_badge
    assert '"Execute"' in instant_badge
    assert "fetchWasteLoopStage" not in instant_badge
    assert "ai-activity-trace" in instant_css
    assert "ai-stage-execute" in instant_css
    assert "aifig-watch" not in instant_css
    assert "ai-flip" not in instant_css
    assert "wasteTraceLabels" in full_indicator
    assert "last_management_account_position_count" in full_indicator
    assert "paper lane scanning" in full_indicator
    assert "PAPER SIM" in full_indicator
    assert "simulator handoff" in full_indicator
    assert "const connLabel = presentation.badgeLabel;" in full_indicator
    assert 'lane ?? "LOOP"' in instant_badge
    assert 'import "./AiActivityIndicator.css"' in full_indicator
    assert "TRACE_LABEL.test" in full_indicator
    assert "TRACE_LABEL.execute" in full_indicator
    assert "aifig-watch" in full_css
    assert "ai-flip" in full_css


def test_shell_defers_full_ai_activity_indicator_until_idle():
    shell = (
        REPO_ROOT / "ui" / "src" / "components" / "Shell.tsx"
    ).read_text(encoding="utf-8")

    assert "AI_ACTIVITY_FULL_INDICATOR_IDLE_TIMEOUT_MS = 1_400" in shell
    assert "requestIdleCallback" in shell
    assert "fullActivityIndicatorMounted" in shell
    assert "setFullActivityIndicatorMounted(true)" in shell
    assert "fullActivityIndicatorMounted ? (" in shell
    assert "<AiActivityInstantBadge wasteLoop={wasteLoop} />" in shell
    assert "<AiActivityIndicator wasteLoop={wasteLoop} />" in shell
    assert shell.index("fullActivityIndicatorMounted ? (") < shell.index(
        "<AiActivityIndicator wasteLoop={wasteLoop} />",
    )


def test_mt4_bridge_panel_requires_heartbeat_before_demo_fill_claims():
    panel = (
        REPO_ROOT / "ui" / "src" / "components" / "Mt4BridgePanel.tsx"
    ).read_text(encoding="utf-8")

    assert "no demo fills can run until the EA heartbeat is live" in panel
    assert "Route ON only selects the path" in panel
    assert "not an active MT4 demo fill by itself" in panel


def test_settings_page_exposes_broker_funding_handoff_without_raw_payment_storage():
    settings = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    broker_portal = (REPO_ROOT / "ui" / "src" / "util" / "brokerPortal.ts").read_text(encoding="utf-8")
    funding_panel = settings.split("function BrokerFundingHandoffPanel(", 1)[1].split(
        "function ControlField",
        1,
    )[0]

    assert "<BrokerFundingHandoffPanel brokerReality={state.brokerReality} />" in settings
    assert "https://secure.risenfx.com/" in broker_portal
    assert "brokerPortal.url" in funding_panel
    assert "Open Broker Portal" in funding_panel
    assert "Sync Broker Snapshot" in funding_panel
    assert "fetchAccountReconciliation(true)" in funding_panel
    assert "NO RAW BANK/CARD STORAGE" in funding_panel
    assert "Movement Feed" in funding_panel
    assert "describeReconciliationMovementTruth(reconciliation)" in funding_panel
    assert "movementTruth.detail" in funding_panel
    assert "input" not in funding_panel
    assert "apiPost" not in funding_panel


def test_settings_live_recovery_exposes_order_idempotency_policy():
    settings = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    evidence_types = (REPO_ROOT / "ui" / "src" / "types" / "evidence.ts").read_text(encoding="utf-8")

    assert "Duplicate Suppressed" in settings
    assert "Shape Duplicates" in settings
    assert "Idempotency Window" in settings
    assert "Exact Retry Key" in settings
    assert "Near Duplicate Key" in settings
    assert "Latest Shape Key" in settings
    assert "manual and compound/pyramid adds are excluded" in settings.lower()
    assert "OrderIdempotencyPolicy" in evidence_types
    assert "near_duplicate_suppressed_count" in evidence_types
    assert "order_shape_key" in evidence_types


def test_proof_page_exposes_broker_funding_route_at_live_controls():
    proof = (REPO_ROOT / "ui" / "src" / "pages" / "ProofPage.tsx").read_text(encoding="utf-8")
    funding_block = proof.split("<div className=\"go-live-group-title\">Broker Funding Route</div>", 1)[1].split(
        "<div className=\"not-licensed-grid\"",
        1,
    )[0]

    assert "brokerPortal.url" in funding_block
    assert "OPEN BROKER PORTAL" in funding_block
    assert "SYNC BROKER SNAPSHOT" in funding_block
    assert "fetchAccountReconciliation(true)" in proof
    assert "NO RAW BANK/CARD STORAGE" in funding_block
    assert "Movement Feed" in funding_block
    assert "describeReconciliationMovementTruth(reconciliation)" in proof
    assert "movementTruth.detail" in funding_block
    assert "apiPost" not in funding_block
    assert "type=\"password\"" not in funding_block


def test_app_shell_share_page_config_and_single_active_route_renderer():
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    shell = (
        REPO_ROOT / "ui" / "src" / "components" / "Shell.tsx"
    ).read_text(encoding="utf-8")
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    page_config = (REPO_ROOT / "ui" / "src" / "pageConfig.ts").read_text(encoding="utf-8")

    assert "from \"./pageConfig\"" in app
    assert "from \"../pageConfig\"" in shell
    assert "export const NAV_ITEMS" in page_config
    assert "Tracker" in page_config
    assert '"tracker"' in page_config
    assert "type Page =" not in app
    assert "type Page =" not in shell
    assert "const NAV_ITEMS" not in shell
    assert "PAGE_COMPONENTS" in app
    assert "TrackerPage" in app
    assert "<ActivePage state={state} />" in app
    assert "page === \"quick-start\"" not in app
    assert "page === \"dashboard\" && <DashboardPage" not in app
    assert "const [navOverflowed, setNavOverflowed]" in shell
    assert "ResizeObserver" in shell
    assert "requiredLinkWidth > inlineAvailableWidth" in shell
    assert 'className={`shell-nav ${navOverflowed ? "overflowed" : ""}`}' in shell
    assert ".shell-nav.overflowed" in app_css
    assert ".shell-nav.overflowed .shell-nav-links.open" in app_css
    assert "max-height: 0" in app_css


def test_shell_surfaces_recent_critical_alerts_across_pages():
    shell = (
        REPO_ROOT / "ui" / "src" / "components" / "Shell.tsx"
    ).read_text(encoding="utf-8")
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    alert_strip = (
        REPO_ROOT / "ui" / "src" / "components" / "CriticalAlertStrip.tsx"
    ).read_text(encoding="utf-8")
    alert_css = (
        REPO_ROOT / "ui" / "src" / "components" / "CriticalAlertStrip.css"
    ).read_text(encoding="utf-8")

    assert 'import("./CriticalAlertStrip")' in shell
    assert '<CriticalAlertStrip onOpenAlerts={() => onNavigate("settings")} />' in shell
    assert "fetchCriticalNotificationAudit(5)" in alert_strip
    assert "visibleRows" in alert_strip
    assert 'severity === "alert" || severity === "warning"' in alert_strip
    assert 'aria-live="polite"' in alert_strip
    assert "Open alerts" in alert_strip
    assert 'import "./CriticalAlertStrip.css"' in alert_strip
    assert 'dispatchStatus === "DUPLICATE_SUPPRESSED"' in alert_strip
    for selector in (
        ".critical-alert-strip",
        ".critical-alert-strip-warning",
        ".critical-alert-strip-alert",
        ".critical-alert-button",
    ):
        assert selector not in app_css
        assert selector in alert_css


def test_dashboard_full_detail_hydration_is_spread_after_fast_packet():
    hydrator = (REPO_ROOT / "ui" / "src" / "data" / "dashboardApi.ts").read_text(encoding="utf-8")

    assert "DASHBOARD_FAST_FETCH_DEFER_MS = 350" in hydrator
    assert "DASHBOARD_FULL_AUTHORITY_BOUNDARY_DEFER_MS = 900" in hydrator
    assert "DASHBOARD_FULL_UI_READINESS_DEFER_MS = 1_500" in hydrator
    assert "DASHBOARD_FULL_DAILY_SCHEDULE_DEFER_MS = 2_100" in hydrator
    assert "DASHBOARD_FULL_DAILY_BUNDLE_DEFER_MS = 2_800" in hydrator
    assert "DASHBOARD_FULL_WASTE_SAMPLE_SCHEDULER_DEFER_MS = 6_500" in hydrator
    assert "DASHBOARD_FAST_RETRY_BASE_DELAY_MS = 1_500" in hydrator
    assert hydrator.index("DASHBOARD_FULL_DAILY_BUNDLE_DEFER_MS") < hydrator.index(
        "DASHBOARD_FULL_WASTE_SAMPLE_SCHEDULER_DEFER_MS",
    )
    assert "type DashboardHydrationWindow = Window &" in hydrator
    assert "requestIdleCallback?: (callback: () => void, options?: { timeout?: number })" in hydrator
    assert "function scheduleDashboardHydrationWork(callback: () => void, timeoutMs: number): void" in hydrator
    assert "hydrationWindow.requestIdleCallback(callback, { timeout: timeoutMs });" in hydrator
    assert "function scheduleDashboardRetryWork(callback: () => void, delayMs: number): void" in hydrator
    assert "scheduleDashboardHydrationWork(callback, delayMs);" in hydrator
    load_hydrator_body = hydrator.split("export async function loadDashboardState", 1)[1]
    assert load_hydrator_body.count("scheduleDashboardHydrationWork(() =>") == 5
    assert "scheduleDashboardRetryWork(() =>" in load_hydrator_body
    assert "DASHBOARD_FAST_RETRY_BASE_DELAY_MS * attempt" in load_hydrator_body
    authority_schedule = hydrator.split("const scheduleFullAuthorityBoundaryHydration = () => {", 1)[1].split(
        "let fullUiReadinessHydrationScheduled",
        1,
    )
    assert "scheduleDashboardHydrationWork(() =>" in authority_schedule[0]
    assert "DASHBOARD_FULL_AUTHORITY_BOUNDARY_DEFER_MS" in authority_schedule[0]


def test_dashboard_shell_fetch_does_not_block_fast_packet_timer():
    hydrator = (REPO_ROOT / "ui" / "src" / "data" / "dashboardApi.ts").read_text(encoding="utf-8")
    browser_branch = hydrator.split("if (typeof window === \"undefined\") {", 1)[1]
    browser_after_ssr = browser_branch.split("return;", 1)[1]

    assert "const fetchAndApplyDashboardShell = async () =>" in hydrator
    assert "void fetchAndApplyDashboardShell();" in hydrator
    assert "fastFetchDeferMs = Math.max(0, options.fastFetchDeferMs ?? DASHBOARD_FAST_FETCH_DEFER_MS)" in hydrator
    assert "await fetchAndApplyDashboardShell()" not in browser_after_ssr
    assert browser_after_ssr.index("void fetchAndApplyDashboardShell();") < browser_after_ssr.index(
        "window.setTimeout(() =>",
    )
    assert "}, fastFetchDeferMs);" in hydrator


def test_dashboard_api_reads_prefer_last_successful_base_before_default_retry():
    api_core = (REPO_ROOT / "ui" / "src" / "data" / "apiCore.ts").read_text(encoding="utf-8")
    stage_probe = (REPO_ROOT / "ui" / "src" / "data" / "wasteStageProbe.ts").read_text(encoding="utf-8")

    assert 'LAST_SUCCESSFUL_API_BASE_STORAGE_KEY = "cas_forex_last_successful_api_base"' in api_core
    assert 'LAST_SUCCESSFUL_API_BASE_STORAGE_KEY = "cas_forex_last_successful_api_base"' in stage_probe
    assert "clearRememberedApiBase();" in api_core
    assert "function readLastSuccessfulApiBase(): string | null" in api_core
    assert "function rememberSuccessfulApiBase(base: string): void" in api_core
    assert "function clearRememberedApiBase(): void" in api_core
    assert "const rememberedBase = readLastSuccessfulApiBase();" in api_core
    assert "const originBase = sameOriginApiBase();" in api_core
    assert "? [savedOverride, originBase, rememberedBase, DEFAULT_API_BASE]" in api_core
    assert ": [savedOverride, rememberedBase, originBase, DEFAULT_API_BASE]" in api_core
    assert "rememberSuccessfulApiBase(base);" in api_core
    assert api_core.count("rememberSuccessfulApiBase(base);") >= 4
    assert "function readLastSuccessfulWasteStageApiBase(): string | null" in stage_probe
    assert "function rememberSuccessfulWasteStageApiBase(base: string): void" in stage_probe
    assert "const rememberedBase = readLastSuccessfulWasteStageApiBase();" in stage_probe
    assert "const originBase = sameOriginApiBase();" in stage_probe
    assert "? [rememberedBase, savedBase, DEFAULT_API_BASE, originBase]" in stage_probe
    assert ": [savedOverride, rememberedBase, originBase, DEFAULT_API_BASE]" in stage_probe
    assert "rememberSuccessfulWasteStageApiBase(base);" in stage_probe
    assert "window.localStorage.setItem(LAST_SUCCESSFUL_API_BASE_STORAGE_KEY" in api_core
    assert "window.localStorage.setItem(LAST_SUCCESSFUL_API_BASE_STORAGE_KEY" in stage_probe


def test_dashboard_api_reads_cool_down_recently_failed_bases():
    api_core = (REPO_ROOT / "ui" / "src" / "data" / "apiCore.ts").read_text(encoding="utf-8")
    stage_probe = (REPO_ROOT / "ui" / "src" / "data" / "wasteStageProbe.ts").read_text(encoding="utf-8")

    assert "FAILED_API_BASE_COOLDOWN_MS = 15_000" in api_core
    assert "const failedApiBaseUntil = new Map<string, number>();" in api_core
    assert "function rememberFailedApiBase(base: string, error?: unknown): void" in api_core
    assert "function shouldCooldownApiBase(error: unknown): boolean" in api_core
    assert "function isApiBaseCoolingDown(base: string): boolean" in api_core
    assert "function availableApiBases(bases: Array<string | null | undefined>): string[]" in api_core
    assert "const active = normalized.filter((base) => !isApiBaseCoolingDown(base));" in api_core
    assert "return active.length ? active : normalized;" in api_core
    assert "failedApiBaseUntil.delete(lastSuccessfulApiBase);" in api_core
    assert api_core.count("rememberFailedApiBase(base, err);") >= 4
    assert "if (error instanceof TypeError) return true;" in api_core
    assert 'error.message.startsWith("API 404:")' in api_core
    assert 'error.name === "AbortError" || error.name === "TimeoutError"' in api_core
    assert "return availableApiBases(bases);" in api_core

    assert "FAILED_STAGE_API_BASE_COOLDOWN_MS = 15_000" in stage_probe
    assert "const failedWasteStageApiBaseUntil = new Map<string, number>();" in stage_probe
    assert "function rememberFailedWasteStageApiBase(base: string, error?: unknown): void" in stage_probe
    assert "function shouldCooldownWasteStageApiBase(error: unknown): boolean" in stage_probe
    assert "function availableWasteStageApiBases(bases: Array<string | null | undefined>): string[]" in stage_probe
    assert "const active = normalized.filter((base) => !isWasteStageApiBaseCoolingDown(base));" in stage_probe
    assert "return active.length ? active : normalized;" in stage_probe
    assert "failedWasteStageApiBaseUntil.delete(lastSuccessfulWasteStageApiBase);" in stage_probe
    assert "rememberFailedWasteStageApiBase(base, error);" in stage_probe
    assert "return availableWasteStageApiBases(bases);" in stage_probe


def test_dashboard_hydrator_api_omits_legacy_hook_and_full_aggregate_fetch():
    hydrator = (REPO_ROOT / "ui" / "src" / "data" / "dashboardApi.ts").read_text(encoding="utf-8")
    shared_api = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert "from \"react\"" not in hydrator
    for legacy_dashboard_symbol in (
        "UseDashboardResult",
        "useDashboard",
        "export async function fetchDashboard(",
    ):
        assert legacy_dashboard_symbol not in hydrator
        assert legacy_dashboard_symbol not in shared_api
    assert "\"/dashboard\"" not in hydrator
    for split_dashboard_symbol in ("fetchDashboardShell", "fetchDashboardFast"):
        assert split_dashboard_symbol in hydrator
        assert split_dashboard_symbol not in shared_api
    assert "\"/dashboard\"" not in shared_api
    assert "loadDashboardState" in hydrator


def test_dashboard_hydrator_lazy_loads_stale_cache_writer_after_packet_apply():
    hydrator = (REPO_ROOT / "ui" / "src" / "data" / "dashboardApi.ts").read_text(encoding="utf-8")
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")

    assert 'from "./data/dashboardStartupCache"' not in app
    assert "const startupState = useMemo(() => startupDashboardState(), []);" in app
    assert "DASHBOARD_STALE_CACHE_IDLE_TIMEOUT_MS = 650" in app
    assert "const cancelStaleCacheRead = scheduleAppIdleWork(() => {" in app
    assert 'void import("./data/dashboardStartupCache").then((cache) => {' in app
    assert "const stalePacket = cache.readStaleDashboardPacket();" in app
    assert "current === startupState" in app
    assert "cache.mergeStartupDashboardPacket(startupState, stalePacket)" in app
    assert "}, DASHBOARD_STALE_CACHE_IDLE_TIMEOUT_MS);" in app
    assert "cancelStaleCacheRead();" in app
    assert "readStaleDashboardPacket()" not in hydrator
    assert "import type { DashboardPacket } from \"./dashboardStartupCache\";" in hydrator
    assert 'from "./dashboardStartupCacheWriter"' not in hydrator
    assert 'import("./dashboardStartupCacheWriter")' in hydrator
    assert "DASHBOARD_STALE_CACHE_WRITE_IDLE_TIMEOUT_MS = 4_000" in hydrator
    assert "writeStaleDashboardPacketLater" in hydrator
    writer_body = hydrator.split("function writeStaleDashboardPacketLater", 1)[1].split(
        "export async function fetchDashboardShell",
        1,
    )[0]
    assert "scheduleDashboardHydrationWork(() =>" in writer_body
    assert 'dashboardCacheWriterPromise ??= import("./dashboardStartupCacheWriter")' in writer_body
    assert "DASHBOARD_STALE_CACHE_WRITE_IDLE_TIMEOUT_MS" in writer_body
    assert "handlers.setState((current) => mergeDashboardState(current ?? initialState, packet))" in hydrator
    assert hydrator.index("handlers.setState((current) => mergeDashboardState(current ?? initialState, packet))") < hydrator.index(
        "writeStaleDashboardPacketLater(shell)",
    )
    assert hydrator.index("handlers.setState((current) => mergeDashboardState(current ?? initialState, packet))") < hydrator.index(
        "writeStaleDashboardPacketLater(fast)",
    )


def test_dashboard_hydrator_skips_duplicate_waste_stage_probe_helper():
    hydrator = (REPO_ROOT / "ui" / "src" / "data" / "dashboardApi.ts").read_text(encoding="utf-8")
    shared_api = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")

    assert 'from "./wasteStageProbe"' not in hydrator
    assert "fetchWasteLoopStagePacket" not in hydrator
    assert "fetchAndApplyWasteLoopStage" not in hydrator
    assert "waste_stage_probe" not in hydrator
    assert "Fast WASTE stage probe" not in hydrator
    assert "await fetchAndApplyDashboardShell();" in hydrator
    assert "void fetchAndApplyDashboardShell();" in hydrator
    assert "void fetchInstantWasteStage().then" in app
    assert 'await import("./data/wasteStageProbe")' in app

    assert 'from "./wasteStageProbe"' not in shared_api
    assert 'type WasteStageProbeModule = typeof import("./wasteStageProbe")' in shared_api
    assert 'wasteStageProbePromise ??= import("./wasteStageProbe")' in shared_api
    assert "const { fetchWasteStageProbe } = await loadWasteStageProbe();" in shared_api


def test_dashboard_startup_cache_writer_keeps_only_first_paint_fields():
    writer = (
        REPO_ROOT / "ui" / "src" / "data" / "dashboardStartupCacheWriter.ts"
    ).read_text(encoding="utf-8")
    cache_reader = (
        REPO_ROOT / "ui" / "src" / "data" / "dashboardStartupCache.ts"
    ).read_text(encoding="utf-8")

    assert "DASHBOARD_STALE_CACHE_MAX_AGE_MS" in writer
    assert "DASHBOARD_STALE_CACHE_MAX_BYTES" in writer
    assert "DASHBOARD_STALE_CACHE_MAX_BYTES = 80_000" in cache_reader
    assert "raw.length > DASHBOARD_STALE_CACHE_MAX_BYTES" in writer
    assert "raw.length > DASHBOARD_STALE_CACHE_MAX_BYTES" in cache_reader
    assert "const startupPacket: DashboardPacket = {};" in cache_reader
    assert "const startupPacket = { ...packet }" not in cache_reader
    assert "function trimDailyBundleForStartup" in cache_reader
    assert "steps: []" in cache_reader
    assert "failure_reasons: []" in cache_reader
    assert "symbol_decisions: []" in cache_reader
    assert "sizing: []" in cache_reader
    assert "function readExistingDashboardCachePacket()" in writer
    assert "function mergeDashboardCachePackets(" in writer
    assert "function preferredDashboardMeta(" in writer
    assert "function dashboardPacketRank(" in writer
    assert "mergeDashboardCachePackets(readExistingDashboardCachePacket(), cacheable)" in writer
    assert "return sanitizeDashboardPacketForCache(parsed.packet as DashboardPacket);" in writer
    assert "Date.now() - parsed.savedAt > DASHBOARD_STALE_CACHE_MAX_AGE_MS" in writer
    assert "...existing,\n    ...next," in writer
    assert "dashboardPacketRank(next.kind) >= dashboardPacketRank(existing.kind)" in writer
    for first_paint_field in (
        "uiReadiness",
        "proofProgress",
        "riskBudget",
        "dailySchedule",
        "dailyBundle",
        "wasteLoop",
    ):
        assert first_paint_field in writer
        assert first_paint_field in cache_reader
    for deep_field in (
        "runtimeGates",
        "autoHalt",
        "brokerTruthMonitor",
        "wasteRealCandleProbe",
        "copyDashboardCacheField",
    ):
        assert deep_field not in writer
        assert deep_field not in cache_reader


def test_dashboard_deep_operations_lazy_loads_deep_api_client():
    dashboard = (
        REPO_ROOT / "ui" / "src" / "pages" / "DashboardPage.tsx"
    ).read_text(encoding="utf-8")
    deep_operations_shell = REPO_ROOT / "ui" / "src" / "components" / "DashboardDeepOperations.tsx"
    workbench = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardOperationsWorkbench.tsx"
    ).read_text(encoding="utf-8")
    deep_api = (
        REPO_ROOT / "ui" / "src" / "data" / "dashboardDeepApi.ts"
    ).read_text(encoding="utf-8")

    assert not deep_operations_shell.exists()
    assert 'lazy(() => import("../components/DashboardOperationsWorkbench")' in dashboard
    assert "DashboardDeepOperations" not in dashboard
    assert "dashboardDeepApiPromise" not in dashboard
    assert "import {\n  acceptLiveOrderDryRunReview" not in workbench
    assert 'import { lazy, Suspense, useEffect, useRef, useState } from "react";' in workbench
    assert "type DashboardDeepApiModule = typeof import(\"../data/dashboardDeepApi\")" in workbench
    assert "dashboardDeepApiPromise ??= import(\"../data/dashboardDeepApi\")" in workbench
    assert "callDashboardDeepApi(\"fetchDashboardDeepCacheSnapshot\"" in workbench
    assert "callDashboardDeepApi(\"fetchWasteLoopStatus\"" in workbench
    assert "const cancelDeepCacheSnapshot = scheduleDashboardIdleWork(() => {" in workbench
    assert "fetchDashboardDeepCacheSnapshot().then" in workbench
    assert "cancelDeepCacheSnapshot();" in workbench
    assert "const deepCacheWarmFieldsRef = useRef<Set<string>>(new Set());" in workbench
    assert "function rememberDeepCachePacket<T>" in workbench
    assert 'rememberDeepCachePacket("wasteEntryDispatchHandoff", packets.wasteEntryDispatchHandoff)' in workbench
    assert 'consumeDeepCacheWarmField("wasteEntryDispatchHandoff")' in workbench
    assert "consumeAllDeepCacheWarmFields([" in workbench
    assert 'consumeDeepCacheWarmField("accountReconciliation")' in workbench
    assert workbench.index("const cancelDeepCacheSnapshot = scheduleDashboardIdleWork") < workbench.index(
        "fetchDashboardDeepCacheSnapshot().then",
    )
    assert workbench.index("fetchDashboardDeepCacheSnapshot().then") < workbench.index(
        "scheduleCorePoll(DASHBOARD_ACCOUNT_LEDGER_FIRST_LOAD_MS",
    )
    assert 'apiGet<DashboardDeepCacheSnapshot>("/dashboard/deep-cache")' in deep_api


def test_dashboard_page_defers_noncritical_support_cards_after_first_paint():
    dashboard = (REPO_ROOT / "ui" / "src" / "pages" / "DashboardPage.tsx").read_text(encoding="utf-8")

    assert "DASHBOARD_OPERATOR_BRIEFING_DEFER_MS = 900" in dashboard
    assert "DASHBOARD_OBJECTIVE_SUPPORT_DEFER_MS = 1_100" in dashboard
    assert "function scheduleDashboardIdleWork(callback: () => void, timeoutMs: number): () => void" in dashboard
    assert "idleWindow.requestIdleCallback(callback, { timeout: timeoutMs });" in dashboard
    assert "const id = window.setTimeout(callback, timeoutMs);" in dashboard
    assert "operatorBriefingMounted ? (" in dashboard
    assert "objectiveSupportMounted ? (" in dashboard
    assert "scheduleDashboardIdleWork(\n      () => setOperatorBriefingMounted(true)," in dashboard
    assert "scheduleDashboardIdleWork(\n      () => setObjectiveSupportMounted(true)," in dashboard
    assert "scheduleDashboardIdleWork(\n      () => setDeepOperationsMounted(true)," in dashboard
    assert "OperatorBriefingCardFallback" in dashboard
    assert "ObjectiveSupportCardsFallback" in dashboard


def test_vite_splits_react_vendor_out_of_cas_app_shell():
    vite_config = (REPO_ROOT / "ui" / "vite.config.ts").read_text(encoding="utf-8")

    assert 'return "react-vendor";' in vite_config
    assert 'id.includes("node_modules/react/")' in vite_config
    assert 'id.includes("node_modules/react-dom/")' in vite_config
    assert 'id.includes("node_modules/scheduler/")' in vite_config


def test_pwa_precache_is_limited_to_first_paint_app_shell():
    vite_config = (REPO_ROOT / "ui" / "vite.config.ts").read_text(encoding="utf-8")
    sw_register = (REPO_ROOT / "ui" / "src" / "registerServiceWorker.ts").read_text(encoding="utf-8")

    assert "selfDestroying: true" not in vite_config
    assert "registerType: \"autoUpdate\"" in vite_config
    assert "skipWaiting: true" in vite_config
    assert "clientsClaim: true" in vite_config
    assert '"**/*.{js,css,html,svg,png,ico,webmanifest,json}"' not in vite_config
    assert '"index.html"' in vite_config
    assert '"registerSW.js"' in vite_config
    assert '"manifest.webmanifest"' in vite_config
    assert '"assets/index-*.css"' in vite_config
    assert '"assets/index-*.js"' in vite_config
    assert '"assets/react-vendor-*.js"' in vite_config
    assert 'handler: "NetworkFirst"' in vite_config
    assert 'cacheName: "cas-forex-code-v2"' in vite_config
    assert 'handler: "StaleWhileRevalidate"' in vite_config
    assert "registration.update()" in sw_register
    assert "SKIP_WAITING" in sw_register
    assert "controllerchange" in sw_register
    assert "clearRuntimeCaches" in sw_register
    assert "'cas-forex-assets-'" in sw_register
    assert "'cas-forex-code-'" in sw_register
    assert "'workbox-precache'" in sw_register
    assert "staleBundleRecoveryKey" in sw_register
    assert "vite:preloadError" in sw_register
    assert "failed to fetch dynamically imported module" in sw_register
    assert "registration.unregister()" in sw_register
    assert "window.setInterval(requestUpdate, 60_000)" in sw_register
    assert "document.visibilityState === 'visible'" in sw_register
    assert "window.location.reload()" in sw_register


def test_windows_mt5_account_panel_explains_terminal_mirror_not_account_lock():
    windows_page = (REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.tsx").read_text(encoding="utf-8")
    mt5_live = (REPO_ROOT / "cas_forex" / "mt5_live.py").read_text(encoding="utf-8")
    api_types = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert "Live, read-only, straight from your MT5 terminal" not in windows_page
    assert "subtitle={subtitle}" in windows_page
    assert "DEMO - PAPER / MT5 BRIDGE" in windows_page
    assert "LIVE MONEY ACCOUNT" in windows_page
    assert "TERMINAL MIRROR" in windows_page
    assert "MT5_READ_ONLY_MIRROR_TOOLTIP" in windows_page
    assert "READ-ONLY MIRROR" in windows_page
    assert "const readOnlyBoundary = mt5?.claim_boundary" in windows_page
    assert "const mirrorScope = mt5?.mirror_scope" in windows_page
    assert "const mirrorLabel = mt5?.mirror_label" in windows_page
    assert "const readOnlyLabel = mt5?.read_only_label" in windows_page
    assert "const writesFromPanel = mt5?.writes_from_panel" in windows_page
    assert "const executionPathNote = mt5?.execution_path_note" in windows_page
    assert "scope: <strong>{mirrorScope}</strong>" in windows_page
    assert "writes: <strong>{writesFromPanel}</strong>" in windows_page
    assert "execution: <strong>{executionPathNote}</strong>" in windows_page
    assert "StatusChip label={mirrorLabel}" in windows_page
    assert "StatusChip label={readOnlyLabel}" in windows_page
    assert "CAS AI and automation still open, close, and manage trades" in windows_page
    assert "protected order-dispatch path for real money" in windows_page
    assert "observe-only from this panel" in windows_page
    assert "MT5_TERMINAL_ALGO_TOOLTIP" in windows_page
    assert "It does not disable CAS AI execution" in windows_page
    assert "ALGO ON" in windows_page
    assert "ALGO OFF" in windows_page
    assert "permission_state" in windows_page
    assert "MT5 permissions: terminal algo" in windows_page
    assert "position_protection" in windows_page
    assert "Position protection:" in windows_page
    assert "STOPS PROTECTED" in windows_page
    assert "UNPROTECTED" in windows_page
    assert "ENTRY RISK > CAP" in windows_page
    assert "Entry risk at SL" in windows_page
    assert "positionRisk.risk_cap_pct" in windows_page
    assert "this comparison alone does not force-close an existing trade" in windows_page
    assert "place and manage paper/demo trades through the MT5 bridge/verifier path" in windows_page
    assert "place and manage real-money trades through the protected order-dispatch path" in windows_page
    assert "claim_boundary?: string;" in api_types
    assert "mirror_scope?: string;" in api_types
    assert "mirror_label?: string;" in api_types
    assert "read_only_label?: string;" in api_types
    assert "writes_from_panel?: string;" in api_types
    assert "observational_only?: boolean;" in api_types
    assert "execution_path_note?: string;" in api_types
    assert "risk_at_stop_usd?: number | null;" in api_types
    assert "risk_cap_breached?: boolean | null;" in api_types
    assert "position_risk?: Mt5PositionRiskSummary;" in api_types
    assert "_CLAIM_BOUNDARY" in mt5_live
    assert "_MIRROR_SCOPE" in mt5_live
    assert "_MIRROR_LABEL" in mt5_live
    assert "_READ_ONLY_LABEL" in mt5_live
    assert "_WRITES_FROM_PANEL" in mt5_live
    assert "_mirror_surface_contract" in mt5_live
    assert "_GENERIC_EXECUTION_PATH_NOTE" in mt5_live
    assert "permission_state" in mt5_live
    assert "build_mt5_permission_state" in mt5_live
    assert "build_open_position_stop_risk" in mt5_live
    assert "summarize_open_position_stop_risk" in mt5_live
    assert "Terminal mirror from your MetaTrader 5 account." in mt5_live
    assert "This panel is observational only." in mt5_live
    assert "CAS AI and automation handle demo/paper trade actions through the MT5 bridge/verifier path." in mt5_live


def test_mobile_preview_serves_installable_build_with_api_proxy():
    package_json = (REPO_ROOT / "ui" / "package.json").read_text(encoding="utf-8")
    vite_config = (REPO_ROOT / "ui" / "vite.config.ts").read_text(encoding="utf-8")
    mobile_doc = (REPO_ROOT / "docs" / "MOBILE_APP.md").read_text(encoding="utf-8")
    quick_start = (REPO_ROOT / "ui" / "src" / "pages" / "QuickStartPage.tsx").read_text(encoding="utf-8")
    quick_start_css = (REPO_ROOT / "ui" / "src" / "pages" / "QuickStartPage.css").read_text(encoding="utf-8")
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    operator_badge = (REPO_ROOT / "ui" / "src" / "components" / "OperatorBadge.tsx").read_text(encoding="utf-8")
    operator_badge_css = (REPO_ROOT / "ui" / "src" / "components" / "OperatorBadge.css").read_text(encoding="utf-8")
    floating_assistant = (REPO_ROOT / "ui" / "src" / "components" / "FloatingAssistant.tsx").read_text(encoding="utf-8")
    operator_api = (REPO_ROOT / "ui" / "src" / "data" / "operatorApi.ts").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    api_core = (REPO_ROOT / "ui" / "src" / "data" / "apiCore.ts").read_text(encoding="utf-8")
    owner_auth_api = (REPO_ROOT / "ui" / "src" / "data" / "ownerAuthApi.ts").read_text(encoding="utf-8")
    api_server_file = (REPO_ROOT / "api" / "server.py").read_text(encoding="utf-8")
    mobile_route = (REPO_ROOT / "api" / "routes" / "mobile.py").read_text(encoding="utf-8")
    assistant_route = (REPO_ROOT / "api" / "routes" / "assistant.py").read_text(encoding="utf-8")
    lan_launcher = (REPO_ROOT / "START_CAS_FOREX_LAN.bat").read_text(encoding="utf-8")
    mobile_stack_runner = (REPO_ROOT / "cas_forex" / "mobile_stack_runner.py").read_text(encoding="utf-8")
    mobile_proof_session = (REPO_ROOT / "cas_forex" / "mobile_proof_session.py").read_text(encoding="utf-8")
    phone_release_bundle = (REPO_ROOT / "cas_forex" / "phone_release_bundle.py").read_text(encoding="utf-8")
    release_bundle_script = (REPO_ROOT / "scripts" / "build_web_phone_release_bundle.py").read_text(encoding="utf-8")
    api_server_script = (REPO_ROOT / "scripts" / "run_api_server.py").read_text(encoding="utf-8")

    assert '"mobile:preview": "vite preview --host 0.0.0.0 --port 4173"' in package_json
    assert "scripts/run_android_gradle.py assembleDebug" in package_json
    assert "scripts/run_android_gradle.py assembleRelease" in package_json
    assert "preview: {" in vite_config
    assert "port: 4173" in vite_config
    assert '"/api/forex": {' in vite_config
    assert 'target: "http://127.0.0.1:8765"' in vite_config
    assert "xfwd: true" in vite_config
    assert "http://<YOUR-PC-LAN-IP>:4173" in mobile_doc
    assert "does **not** need a separate API URL" in mobile_doc
    assert "Allow `8765` only when" in mobile_doc
    assert "expose the API directly" in mobile_doc
    assert "scripts/build_web_phone_release_bundle.py" in mobile_doc
    assert "evidence_runs/web_phone_release/latest/" in mobile_doc
    assert "install-test required artifacts" in mobile_doc
    assert "signed distribution artifact" in mobile_doc
    assert "signed_release_apk_present" in mobile_doc
    assert "scripts/run_mobile_stack_readiness.py" in mobile_doc
    assert "direct phone Quick" in mobile_doc
    assert "Start URL" in mobile_doc
    assert "evidence_runs/mobile_stack/latest/" in mobile_doc
    assert "proof-session" in mobile_doc
    assert "pairing URLs are redacted evidence" in mobile_doc
    assert "without injecting token-shaped pairing URLs" in mobile_doc
    assert "prompt" in mobile_doc
    assert "evidence_runs/mobile_phone_proof/latest/phone_runtime_proof.json" in mobile_doc
    assert "phone_browser_verified=true" in mobile_doc
    assert "non-localhost client/proxy evidence" in mobile_doc
    assert "Fresh phone proof is overlaid" in mobile_doc
    assert "stale browser/PWA phone-proof gate" in mobile_doc
    assert "wrapped manual-copy text" in mobile_doc
    assert "phone_quick_start_url" in mobile_doc
    assert "X-Forwarded-For" in mobile_doc
    assert "uses that forwarded address for owner-auth decisions" in mobile_doc
    assert "loopback-only and are blocked for proxied phone clients" in mobile_doc
    assert "Phone pairing link" in mobile_doc
    assert "#cas_owner_token=" in mobile_doc
    assert "cas_api_base" in mobile_doc
    assert "fresh phone does not" in mobile_doc
    assert "not sent in the HTTP request" in mobile_doc
    assert "run_mobile_stack_readiness.py" in lan_launcher
    assert "mobile_release_readiness.json" in lan_launcher
    assert "CAS_FOREX_PHONE_QUICK_START" in lan_launcher
    assert "%CAS_FOREX_PHONE_QUICK_START%" in lan_launcher
    assert "phone_quick_start_url" in lan_launcher
    assert "watch_mobile_phone_proof.py --timeout-seconds 600" in lan_launcher
    assert "CAS Forex Phone Proof Watcher" in lan_launcher
    assert "http://localhost:4173/?page=quick-start" in lan_launcher
    assert "pairing link" in lan_launcher
    assert "--api-workers" in (REPO_ROOT / "scripts" / "run_mobile_stack_readiness.py").read_text(encoding="utf-8")
    assert "--workers" in api_server_script
    assert "CAS_FOREX_API_WORKERS" in api_server_script
    assert "phone_quick_start_url" in mobile_stack_runner
    assert "Phone Quick Start URL:" in mobile_stack_runner
    assert "api_workers: int = 1" in mobile_stack_runner
    assert '"--workers"' in mobile_stack_runner
    assert "tested_quick_start_url" in phone_release_bundle
    assert '"phone_quick_start_url"' in phone_release_bundle
    assert '"android_adb_path"' in phone_release_bundle
    assert '"apk_install_pairing_attempt_status"' in phone_release_bundle
    assert '"docker_engine_status"' in phone_release_bundle
    assert "Tested Quick Start URL" in phone_release_bundle
    assert "Phone-reachable Quick Start URL" in phone_release_bundle
    assert "INSTALL_TEST_REQUIRED_ARTIFACT_IDS" in phone_release_bundle
    assert "missing_install_test_required_artifacts" in phone_release_bundle
    assert "signed_release_apk_present" in phone_release_bundle
    assert "Signed release APK:" in phone_release_bundle
    assert "Phone Quick Start URL:" in release_bundle_script
    assert "APK install-pair attempt:" in release_bundle_script
    assert "Docker Engine:" in release_bundle_script
    assert "http://<your-LAN-IP>:4173" in quick_start
    assert "beforeinstallprompt" in quick_start
    assert "appinstalled" in quick_start
    assert "isStandalonePwa()" in quick_start
    assert "display-mode: standalone" in quick_start
    assert "standaloneNavigator.standalone" in quick_start
    assert "installPrompt.prompt()" in quick_start
    assert "choice.outcome === \"accepted\"" in quick_start
    assert "Install app" in quick_start
    assert "quick-start-pwa-actions" in quick_start
    assert "quick-start-pwa-button primary" in quick_start
    assert "fetchMobileReadinessLatest" in quick_start
    assert "fetchMobileProofSessionLatest" in quick_start
    assert "fetchMobileVerificationSessionLatest" in quick_start
    assert "refreshMobileVerificationSession" in quick_start
    assert "fetchOwnerPairing" in quick_start
    assert "isLoopbackHost()" in quick_start
    assert 'host.startsWith("127.")' in owner_auth_api
    assert "const [phonePairingUrl, setPhonePairingUrl]" in quick_start
    assert "const [nativePairingUrl, setNativePairingUrl]" in quick_start
    assert "const [phonePairingLanModeEnabled, setPhonePairingLanModeEnabled]" in quick_start
    assert "const loadOwnerPairing = useCallback" in quick_start
    assert "const retryDelays = [0, 1_500, 5_000, 10_000]" in quick_start
    assert "setNativePairingUrl(nativeUrl)" in quick_start
    assert "setPhonePairingLanModeEnabled(pairing?.lan_mode_enabled ?? null)" in quick_start
    assert "postMobilePhoneProof" in quick_start
    assert "buildPhoneProofPayload()" in quick_start
    assert "type PhoneProofSubmitStatus" in quick_start
    assert "const [phoneProofSubmit, setPhoneProofSubmit]" in quick_start
    assert "const [mobileProofSession, setMobileProofSession]" in quick_start
    assert "const [mobileVerificationSession, setMobileVerificationSession]" in quick_start
    assert "function mobileEvidenceShowsInstalledMode" in quick_start
    assert "recordFlag(verificationSession?.proof_state, \"installed_mode_detected\")" in quick_start
    assert "recordFlag(proofSession?.phone_watch_status, \"installed_mode_detected\")" in quick_start
    assert "const mobileInstalledModeOk = mobileEvidenceShowsInstalledMode" in quick_start
    assert "pwaInstalled || isStandalonePwa() || mobileInstalledModeOk" in quick_start
    assert "Installed-app/PWA mode is already present in the current mobile evidence." in quick_start
    assert "function shouldSubmitPhoneProof" in quick_start
    assert "setPhoneProofSubmit({ status: \"skipped\", detail: \"Desktop QA\" });" in quick_start
    assert "status: \"submitting\"" in quick_start
    assert "status: \"recorded\"" in quick_start
    assert "status: \"failed\", detail: \"Submit failed\"" in quick_start
    assert "payload.app_surface === \"apk\"" in quick_start
    assert "[\"mobile\", \"iphone\", \"ipod\", \"android\"]" in quick_start
    assert "phone_browser_observed" in api_client
    assert "phone_browser_verified" in api_client
    assert "phone_proof_fresh?: boolean" in api_client
    assert "phone_proof_age_seconds?: number | null" in api_client
    assert "phone_proof_expires_at?: string | null" in api_client
    assert "phone_observation_fresh?: boolean" in api_client
    assert "phone_observation_age_seconds?: number | null" in api_client
    assert "phone_observation_expires_at?: string | null" in api_client
    assert "phone_quick_start_url?: string | null" in api_client
    assert "verification_commands?: MobileVerificationCommands | null" in api_client
    assert "next_verification_actions?: MobileNextVerificationAction[]" in api_client
    assert "export interface MobileVerificationCommands" in api_client
    assert "mobile_final_verification_watch_all_live_links?: string" in api_client
    assert "export interface MobileNextVerificationAction" in api_client
    assert "export interface MobilePhoneVerificationSession" in api_client
    assert "export interface MobileProofGate" in api_client
    assert "export interface MobileProofSession" in api_client
    assert "report_kind: \"cas_forex_mobile_external_proof_session\"" in api_client
    assert "phone_proof_target_url?: string | null" in api_client
    assert "phone_proof_target_kind?: string" in api_client
    assert "phone_pairing_handoff?: string | null" in api_client
    assert "proof_state?: Record<string, unknown>" in api_client
    assert "release_artifact_summary?: Record<string, unknown>" in api_client
    assert "gates: MobileProofGate[]" in api_client
    assert "default_output_paths?: MobilePhoneVerificationSessionPaths" in api_client
    assert "written_paths?: MobilePhoneVerificationSessionPaths" in api_client
    assert "phone_browser_verified?: boolean" in api_client
    assert "apk_runtime_status?: string | null" in api_client
    assert "apk_install_pairing_attempt_status?: string | null" in api_client
    assert "apk_install_pairing_attempt_current_apk_sha256?: string | null" in api_client
    assert "android_device_ready?: boolean" in api_client
    assert "docker_engine_status?: string | null" in api_client
    assert "docker_desktop_install_command?: string | null" in api_client
    assert "docker_desktop_install_attempt_status?: string | null" in api_client
    assert "docker_desktop_install_attempt_admin_elevation_required?: boolean" in api_client
    assert "docker_wsl_warnings?: string[]" in api_client
    assert "secondary_commands?: string[]" in api_client
    assert "blocks_completion: boolean" in api_client
    assert "phone_proof_watcher: string" in api_client
    assert "phone_verification_session: string" in api_client
    assert "mobile_proof_session?: string" in api_client
    assert "mobile_stack: string" in api_client
    assert "release_bundle: string" in api_client
    assert "apk_release_build: string" in api_client
    assert "apk_build_all?: string" in api_client
    assert "apk_device_list: string" in api_client
    assert "apk_wait_install_pair?: string" in api_client
    assert "docker_engine_diagnose?: string" in api_client
    assert "docker_desktop_install?: string" in api_client
    assert "docker_engine_check: string" in api_client
    assert "docker_compose_build: string" in api_client
    assert "saved proof-session" in mobile_proof_session
    assert "pairing URLs are redacted by design" in mobile_proof_session
    assert "phone_proof_target_kind" in mobile_proof_session
    assert "pwa_pairing_context_available" in assistant_route
    assert "native_pairing_context_available" in assistant_route
    assert "docker_desktop_elevated_install_command" in assistant_route
    assert "secondary_commands=" in assistant_route
    assert "phone_observation_local_runtime_only" in api_client
    assert "apk_install_pairing_proof" in api_client
    assert "apk_install_pairing_verified" in api_client
    assert "apk_install_pairing_generated_at" in api_client
    assert "apk_install_pairing_current_apk_sha256?: string | null" in api_client
    assert "apk_install_pairing_apk_matches_current_artifact?: boolean | null" in api_client
    assert "apk_runtime_status?: string | null" in api_client
    assert "apk_runtime_observed?: boolean" in api_client
    assert "apk_runtime_verified?: boolean" in api_client
    assert "apk_runtime_api_base_network_path?: string | null" in api_client
    assert "apk_install_pairing_attempt" in api_client
    assert "apk_install_pairing_attempt_status?: string | null" in api_client
    assert "apk_install_pairing_attempt_apk_sha256?: string | null" in api_client
    assert "apk_install_pairing_attempt_current_apk_sha256?: string | null" in api_client
    assert "apk_install_pairing_attempt_apk_matches_current_artifact?: boolean | null" in api_client
    assert "apk_install_pairing_attempt_message?: string | null" in api_client
    assert "MobileAndroidReleaseSigning" in api_client
    assert "android_release_signing?: MobileAndroidReleaseSigning | null" in api_client
    assert "android_release_signing_ready?: boolean" in api_client
    assert "android_release_signing_status?: string | null" in api_client
    assert "android_release_signing_detail?: string | null" in api_client
    assert "android_release_apk_exists?: boolean" in api_client
    assert "android_device_ready?: boolean" in api_client
    assert "android_device_count?: number" in api_client
    assert "android_device_ready_count?: number" in api_client
    assert "android_device_detail?: string | null" in api_client
    assert "android_adb_path?: string | null" in api_client
    assert "docker_engine_status?: string | null" in api_client
    assert "docker_engine_detail?: string | null" in api_client
    assert "docker_server_version?: string | null" in api_client
    assert "docker_wsl_checked?: boolean" in api_client
    assert "docker_desktop_winget_available?: boolean" in api_client
    assert "docker_desktop_elevated_install_command?: string | null" in api_client
    assert "docker_desktop_install_attempt_returncode?: number | null" in api_client
    assert "docker_desktop_install_attempt_installer_exit_code?: number | null" in api_client
    assert "attempts?: number" in api_client
    assert "MobileDebugApkArtifact" in api_client
    assert "MobileReleaseApkArtifact" in api_client
    assert "apk_artifact" in api_client
    assert "release_apk_artifact" in api_client
    assert "fetchMobileDebugApkArtifact" in api_client
    assert "fetchMobileReleaseApkArtifact" in api_client
    assert "downloadMobileDebugApk" in api_client
    assert "downloadMobileReleaseApk" in api_client
    assert "apiDownloadBlob" in (REPO_ROOT / "ui" / "src" / "data" / "apiCore.ts").read_text(encoding="utf-8")
    assert "MobilePhoneProofPayload" in api_client
    assert '"/mobile/phone-proof"' in api_client
    assert "fetchMobileVerificationSessionLatest" in api_client
    assert "fetchMobileProofSessionLatest" in api_client
    assert "MobileVerificationPlan" in api_client
    assert "fetchMobileVerificationPlanLatest" in api_client
    assert "refreshMobileVerificationPlan" in api_client
    assert "MobileFinalVerification" in api_client
    assert "fetchMobileFinalVerificationLatest" in api_client
    assert "refreshMobileFinalVerification" in api_client
    assert "default_output_paths?: MobilePhoneVerificationSessionPaths" in api_client
    assert "written_paths?: MobilePhoneVerificationSessionPaths" in api_client
    assert '"/mobile/readiness/latest", 45_000' in api_client
    assert '"/mobile/verification-session/latest", 45_000' in api_client
    assert '"/mobile/proof-session/latest", 45_000' in api_client
    assert '"/mobile/verification-plan/latest", 45_000' in api_client
    assert '"/mobile/verification-plan/refresh"' in api_client
    assert '"/mobile/final-verification/latest", 45_000' in api_client
    assert '"/mobile/final-verification/refresh"' in api_client
    assert "refreshMobileVerificationSession" in api_client
    assert '"/mobile/verification-session/latest"' in api_client
    assert '"/mobile/proof-session/latest"' in api_client
    assert '"/mobile/verification-session/refresh"' in api_client
    assert "Phone/Web Readiness Evidence" in quick_start
    assert "package_ready_for_phone_install" in quick_start
    assert "Phone runtime proof" in quick_start
    assert "phoneFreshnessMetricLabel" in quick_start
    assert "Phone proof freshness" in quick_start
    assert "Phone observation freshness" in quick_start
    assert "formatPhoneProofFreshness" in quick_start
    assert "Stale proof" in quick_start
    assert "This device proof" in quick_start
    assert "Phone network proof" in quick_start
    assert "Debug APK" in quick_start
    assert "Release APK" in quick_start
    assert "Android device" in quick_start
    assert "formatAndroidDeviceState" in quick_start
    assert "No device, adb ready" in quick_start
    assert "Android APK proof" in quick_start
    assert "APK runtime" in quick_start
    assert "formatApkRuntimeState" in quick_start
    assert "Local only" in quick_start
    assert "APK last attempt" in quick_start
    assert "formatApkAttemptState" in quick_start
    assert "Stale APK build" in quick_start
    assert "apk_install_pairing_attempt_current_apk_sha256" in quick_start
    assert "compactMetricText" in quick_start
    assert "formatDockerEngineState" in quick_start
    assert "CLI missing" in quick_start
    assert "Engine down" in quick_start
    assert "Docker install attempt" in quick_start
    assert "formatDockerInstallAttemptState" in quick_start
    assert "Needs admin elevation" in quick_start
    assert "UAC prompt launched" in quick_start
    assert "docker_desktop_install_attempt_installer_exit_code" in quick_start
    assert "commands?.docker_desktop_install" in quick_start
    assert "commands?.docker_desktop_install_elevated" in quick_start
    assert "Copy elevated Docker install" in quick_start
    assert "Copy verification plan" in quick_start
    assert "Copy finish" in quick_start
    assert "Copy finish watcher" in quick_start
    assert "Copy live watcher" in quick_start
    assert "finalVerificationWatchAllLiveLinksCommand" in quick_start
    assert "Final verification watch all with live links" in quick_start
    assert "Refresh plan" in quick_start
    assert "Refresh final" in quick_start
    assert "Final verification" in quick_start
    assert "formatFinalVerificationState" in quick_start
    assert "Submit device proof" in quick_start
    assert "submitCurrentDeviceProof" in quick_start
    assert "onSubmitDeviceProof" in quick_start
    assert "buildVerificationPlanText" in quick_start
    assert "fetchMobileVerificationPlanLatest" in quick_start
    assert "refreshMobileVerificationPlan" in quick_start
    assert "fetchMobileFinalVerificationLatest" in quick_start
    assert "refreshMobileFinalVerification" in quick_start
    assert "refreshFinalVerificationAction" in quick_start
    assert "Final refreshed" in quick_start
    assert "finalVerificationWatchAllCommand" in quick_start
    assert "refreshVerificationPlanAction" in quick_start
    assert "Plan refreshed" in quick_start
    assert "verificationPlan?.text" in quick_start
    assert "Live desktop copy context:" in quick_start
    assert "Secondary commands:" in quick_start
    assert "Docker elevated install:" in quick_start
    assert "Proof session" in quick_start
    assert "formatProofSessionState" in quick_start
    assert "Verify session" in quick_start
    assert "formatVerificationSessionState" in quick_start
    assert "APK stale" in quick_start
    assert "Android not ready" in quick_start
    assert "Docker ${dockerStatus.replace" in quick_start
    assert "Download debug APK" in quick_start
    assert "Download release APK" in quick_start
    assert "downloadMobileDebugApk" in quick_start
    assert "downloadMobileReleaseApk" in quick_start
    assert "startBrowserDownload" in quick_start
    assert "apkPairingVerified" in quick_start
    assert "Copy phone URL" in quick_start
    assert "const phoneQuickStartUrl = readiness?.phone_quick_start_url || quickStartUrl(phoneWebBase)" in quick_start
    assert "const phoneProofUrl = phonePairingUrl || phoneQuickStartUrl" in quick_start
    assert "const phoneProofUrlMode = phonePairingUrl ? \"pairing\" : \"quick-start\"" in quick_start
    assert "url={phoneProofUrl}" in quick_start
    assert "mode={phoneProofUrlMode}" in quick_start
    assert "fallbackUrl={phoneQuickStartUrl}" in quick_start
    assert "pairingNeedsLan={pairingNeedsLan}" in quick_start
    assert 'mode="apk-pairing"' in quick_start
    assert "Copy APK pairing URL" in quick_start
    assert "APK pairing QR" in quick_start
    assert "Scan after APK install" in quick_start
    assert "Opens the installed Android app with owner token" in quick_start
    assert "phoneProofCopyLabel" in quick_start
    assert "Copy pairing URL" in quick_start
    assert "phoneProofCopyStatusLabel" in quick_start
    assert "phoneProofUrlMode={phoneProofUrlMode}" in quick_start
    assert "phonePairingLanModeEnabled={phonePairingLanModeEnabled}" in quick_start
    assert "const lanAccessValue = phonePairingLanModeEnabled === null" in quick_start
    assert "const pairingNeedsLan = phoneProofUrlMode === \"pairing\" && phonePairingLanModeEnabled === false" in quick_start
    assert "LAN access" in quick_start
    assert "Turn LAN access ON in Owner Access before scanning from the phone" in quick_start
    assert "LAN access is OFF, so a paired phone cannot submit owner-authenticated proof yet." in quick_start
    assert "quick-start-phone-qr-warning" in quick_start
    assert "Scan/copy the pairing proof URL" in quick_start
    assert "const nextActions = readiness?.next_verification_actions ?? []" in quick_start
    assert "function NextVerificationActions" in quick_start
    assert "function NextVerificationActionRow" in quick_start
    assert "Next verification actions" in quick_start
    assert "Copy command" in quick_start
    assert "function PhoneProofQrCode" in quick_start
    assert 'await import("qrcode")' in quick_start
    assert "QRCode.toDataURL(url" in quick_start
    assert "function redactSensitiveDisplayValue" in quick_start
    assert "cas_owner_token=)[^&#\\s]+" in quick_start
    assert "{redactSensitiveDisplayValue(targetUrl)}" in quick_start
    assert "{redactSensitiveDisplayValue(url)}" in quick_start
    assert "setManualCopyValue(redactSensitiveDisplayValue(value))" in quick_start
    assert "Scan phone proof URL" in quick_start
    assert "Phone pairing QR" in quick_start
    assert "Scan pairing proof URL" in quick_start
    assert "Pairs a fresh phone" in quick_start
    assert "api.qrserver.com" not in quick_start
    assert "const commands = readiness?.verification_commands ?? null" in quick_start
    assert "commands?.mobile_proof_session" in quick_start
    assert "commands?.phone_verification_session" in quick_start
    assert "commands?.phone_proof_watcher" in quick_start
    assert "commands?.mobile_readiness" in quick_start
    assert "commands?.apk_release_build" in quick_start
    assert "commands?.apk_build_all" in quick_start
    assert "commands?.apk_device_list" in quick_start
    assert "commands?.apk_install_pair" in quick_start
    assert "commands?.apk_wait_install_pair" in quick_start
    assert "commands?.docker_engine_diagnose" in quick_start
    assert "commands?.docker_desktop_install" in quick_start
    assert "commands?.docker_desktop_install_elevated" in quick_start
    assert "commands?.docker_engine_check" in quick_start
    assert "readiness?.phone_quick_start_url" in quick_start
    assert "copyAction(phoneProofCopyStatusLabel, phoneProofUrl)" in quick_start
    assert "function quickStartUrl(webBase: string)" in quick_start
    assert "?page=quick-start" in quick_start
    assert "Copy phone proof" in quick_start
    assert "Refresh session" in quick_start
    assert "Copy proof session" in quick_start
    assert "Copy verify session" in quick_start
    assert "Copy APK build all" in quick_start
    assert "Copy readiness check" in quick_start
    assert "Copy release build" in quick_start
    assert "Copy Android devices" in quick_start
    assert "Copy APK proof" in quick_start
    assert "Copy Docker diagnosis" in quick_start
    assert "Copy Docker install" in quick_start
    assert "quick-start-mobile-readiness-actions" in quick_start
    assert "quick-start-readiness-manual-copy" in quick_start
    assert "navigator.clipboard.writeText" in quick_start
    assert 'document.execCommand("copy")' in quick_start
    assert "Phone-like observed" in quick_start
    assert "Localhost only" in quick_start
    assert "Installed app mode" in quick_start
    assert "Release signing" in quick_start
    assert "formatAndroidReleaseSigningState" in quick_start
    assert "remaining_external_gates.map" in quick_start
    assert ".slice(0, 2)" not in quick_start
    assert "quick-start-mobile-readiness-grid" in quick_start_css
    assert "quick-start-mobile-readiness-actions" in quick_start_css
    assert "quick-start-next-actions" in quick_start_css
    assert "quick-start-next-action-controls" in quick_start_css
    assert "quick-start-readiness-action" in quick_start_css
    assert "quick-start-readiness-manual-copy" in quick_start_css
    assert "quick-start-phone-qr-warning" in quick_start_css
    assert ".quick-start-pwa-actions" in quick_start_css
    assert ".quick-start-pwa-button.primary" in quick_start_css
    assert ".shell-nav-links" in app_css
    assert "min-width: 0;" in app_css
    assert "overflow-x: auto;" in app_css
    assert ".shell-nav {" in app_css
    assert "overflow: visible;" in app_css
    assert "operator-badge--open" in operator_badge
    assert 'import { createPortal } from "react-dom"' in operator_badge
    assert "chipRef" in operator_badge
    assert "--operator-panel-top" in operator_badge
    assert "createPortal((" in operator_badge
    assert ".operator-badge--open" in operator_badge_css
    assert "position: fixed;" in operator_badge_css
    assert "z-index: 5000;" in operator_badge_css
    assert "max-height: min(34rem, calc(100vh - var(--operator-panel-top, 4.5rem) - 8px));" in operator_badge_css
    assert "overflow-y: auto;" in operator_badge_css
    assert '"/ai-operator/chat", { message }, 60_000' in operator_api
    assert "chat_path_status" in operator_api
    assert "operator-badge-chat-responder" in operator_badge
    assert "Answered by" in operator_badge
    assert "CAS runtime truth" in operator_badge
    assert "Answered by:" in floating_assistant
    assert "CAS runtime truth" in floating_assistant
    assert "Local AI" in floating_assistant
    assert "export async function fetchMobileReadinessLatest" in api_client
    assert '"/mobile/readiness/latest"' in api_client
    assert '"/mobile/apk/debug/metadata"' in api_client
    assert '"/mobile/apk/debug/download"' in api_client
    assert "mobile.router" in api_server_file
    owner_auth_policy = (REPO_ROOT / "cas_forex" / "owner_auth.py").read_text(encoding="utf-8")
    assert "effective_client_host" in owner_auth_policy
    assert "extract_forwarded_client_host" in owner_auth_policy
    assert "Trust forwarded client headers only when" in owner_auth_policy
    assert '@router.get("/readiness/latest")' in mobile_route
    assert "_MOBILE_EVIDENCE_CACHE_TTL_SECONDS" in mobile_route
    assert "_cached_mobile_payload" in mobile_route
    assert '@router.get("/verification-session/latest")' in mobile_route
    assert '@router.get("/verification-plan/latest")' in mobile_route
    assert '@router.post("/verification-plan/refresh")' in mobile_route
    assert '@router.get("/final-verification/latest")' in mobile_route
    assert '@router.post("/final-verification/refresh")' in mobile_route
    assert '@router.post("/verification-session/refresh")' in mobile_route
    assert "build_phone_verification_session" in mobile_route
    assert "build_mobile_verification_plan" in mobile_route
    assert "write_mobile_verification_plan" in mobile_route
    assert "build_mobile_final_verification" in mobile_route
    assert "write_mobile_final_verification" in mobile_route
    assert "write_phone_verification_session" in mobile_route
    assert "redact_phone_verification_session" in mobile_route
    assert '@router.get("/apk/debug/metadata")' in mobile_route
    assert '@router.get("/apk/debug/download")' in mobile_route
    assert "FileResponse" in mobile_route
    assert '@router.post("/phone-proof")' in mobile_route
    assert "record_phone_runtime_proof" in mobile_route
    assert 'request.headers.get("x-cas-client-api-base")' in mobile_route
    assert "latest_phone_runtime_proof" in mobile_route
    assert "X-CAS-Client-API-Base" in api_core
    assert "headers: authHeaders(undefined, base)" in api_core
    assert 'api_base: str | None = Field(default=None, max_length=240)' in mobile_route
    assert "phone_proof_api_base_network_path" in api_client
    assert "phone_observation_api_base_network_path" in api_client
    assert "apk_runtime_api_base_network_path" in api_client
    assert "Phone API route" in quick_start
    assert "formatPhoneApiRoute" in quick_start
    assert "Paired API bases" in quick_start
    assert "Probe attempts" in quick_start
    assert "formatProbeAttemptSummary" in quick_start
    assert "readinessChecksSucceeded" in quick_start
    assert '"web_phone_smoke"' in quick_start
    assert '"owner_pairing_payload"' in quick_start
    assert '"paired_api_bases"' in quick_start
    assert "paired_api_bases_reachable" in api_client
    assert "paired_api_bases_status?: string | null" in api_client
    assert "paired_api_bases_detail?: string | null" in api_client
    assert "Paired API bases" in mobile_doc
    mobile_readiness_latest = (REPO_ROOT / "cas_forex" / "mobile_readiness_latest.py").read_text(encoding="utf-8")
    assert "_current_remaining_gates" in mobile_readiness_latest
    assert "debug_apk_artifact_metadata" in mobile_readiness_latest
    assert "_phone_api_base_fields" in mobile_readiness_latest
    assert "_paired_api_base_fields" in mobile_readiness_latest
    assert "_phone_freshness_fields" in mobile_readiness_latest
    assert "_android_device_probe_fields" in mobile_readiness_latest
    assert "_android_release_signing_fields" in mobile_readiness_latest
    assert "_docker_check_fields" in mobile_readiness_latest
    assert "Debug APK" in mobile_doc
    assert "Release APK" in mobile_doc
    assert "Download debug APK" in mobile_doc
    assert "Download release APK" in mobile_doc
    assert "/api/forex/mobile/apk/debug/download" in mobile_doc
    assert "/api/forex/mobile/apk/release/download" in mobile_doc


def test_mobile_readiness_latest_route_is_registered():
    status, body = asyncio.run(_asgi_get("/api/forex/mobile/readiness/latest"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_mobile_readiness_latest"
    assert "package_ready_for_phone_install" in body
    assert "physical_phone_verified" in body
    assert "phone_browser_observed" in body
    assert "phone_browser_verified" in body
    assert "phone_proof_fresh" in body
    assert "phone_proof_age_seconds" in body
    assert "phone_proof_expires_at" in body
    assert "phone_observation_fresh" in body
    assert "phone_observation_age_seconds" in body
    assert "phone_observation_expires_at" in body
    assert "phone_proof_installed_mode" in body
    assert "phone_observation_local_runtime_only" in body
    assert "apk_runtime_status" in body
    assert "apk_runtime_observed" in body
    assert "apk_runtime_verified" in body
    assert "apk_runtime_fresh" in body
    assert "apk_install_pairing_verified" in body
    assert "apk_install_pairing_attempt_status" in body
    assert "android_release_signing_ready" in body
    assert "android_release_signing_status" in body
    assert "android_release_apk_exists" in body
    assert "paired_api_bases_reachable" in body
    assert "paired_api_bases_status" in body
    assert "paired_api_bases_detail" in body
    assert "android_device_ready" in body
    assert "android_device_count" in body
    assert "docker_available" in body
    assert "docker_engine_detail" in body
    assert "docker_desktop_install_attempt_status" in body
    assert "docker_desktop_install_attempt_installer_exit_code" in body
    rendered = json.dumps(body)
    assert "cas_owner_token=REDACTED" in rendered or "cas_owner_token=" not in rendered


def test_mobile_phone_proof_route_accepts_flat_payload_and_rejects_unknown_fields(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_record_phone_runtime_proof(
        body,
        *,
        client_host=None,
        forwarded_for=None,
        real_ip=None,
        request_user_agent=None,
        client_api_base=None,
    ):
        captured["body"] = body
        captured["client_host"] = client_host
        captured["forwarded_for"] = forwarded_for
        captured["real_ip"] = real_ip
        captured["request_user_agent"] = request_user_agent
        captured["client_api_base"] = client_api_base
        return {
            "report_kind": "cas_forex_phone_runtime_proof",
            "phone_browser_verified": True,
            "device_class": "phone",
        }

    monkeypatch.setattr(
        mobile_route,
        "record_phone_runtime_proof",
        fake_record_phone_runtime_proof,
    )
    payload = {
        "source": "quick-start",
        "app_surface": "pwa",
        "url_origin": "http://10.0.0.6:4173",
        "url_path": "/",
        "api_base": "http://10.0.0.6:4173/api/forex",
        "display_mode": "standalone",
        "standalone_pwa": True,
        "user_agent": "Mozilla/5.0 (iPhone) Mobile Safari/604.1",
        "platform": "iPhone",
        "language": "en-US",
        "timezone": "America/Los_Angeles",
        "viewport_width": 390,
        "viewport_height": 844,
        "screen_width": 390,
        "screen_height": 844,
        "device_pixel_ratio": 3,
        "max_touch_points": 5,
        "online": True,
    }

    status, body = asyncio.run(
        _asgi_post_with_headers(
            "/api/forex/mobile/phone-proof",
            payload,
            {
                "x-forwarded-for": "10.0.0.55",
                "x-real-ip": "10.0.0.55",
                "x-cas-client-api-base": "http://10.0.0.6:4173/api/forex",
            },
        )
    )

    assert status == 200
    assert body["phone_browser_verified"] is True
    assert captured["body"]["viewport_width"] == 390
    assert captured["body"]["max_touch_points"] == 5
    assert captured["body"]["api_base"] == "http://10.0.0.6:4173/api/forex"
    assert captured["client_host"] == "127.0.0.1"
    assert captured["forwarded_for"] == "10.0.0.55"
    assert captured["real_ip"] == "10.0.0.55"
    assert captured["client_api_base"] == "http://10.0.0.6:4173/api/forex"

    status, body = asyncio.run(
        _asgi_post(
            "/api/forex/mobile/phone-proof",
            payload | {"viewport": {"width": 390}, "touch": {"max_touch_points": 5}},
        )
    )

    assert status == 422
    rendered = json.dumps(body)
    assert "extra_forbidden" in rendered
    assert captured["body"]["viewport_width"] == 390


def test_mobile_phone_proof_route_dry_run_does_not_record(monkeypatch):
    calls: dict[str, int] = {"build": 0, "record": 0}

    def fake_build_phone_runtime_proof(
        body,
        *,
        client_host=None,
        forwarded_for=None,
        real_ip=None,
        request_user_agent=None,
        client_api_base=None,
    ):
        calls["build"] += 1
        assert body["source"] == "web-phone-smoke"
        assert "dry_run" not in body
        assert client_host == "127.0.0.1"
        assert forwarded_for == "10.0.0.55"
        assert real_ip == "10.0.0.55"
        assert client_api_base == "http://10.0.0.6:4173/api/forex"
        return {
            "report_kind": "cas_forex_phone_runtime_proof",
            "phone_browser_verified": True,
            "device_class": "phone",
            "client_host_source": "x-forwarded-for",
            "effective_client_host": "10.0.0.55",
            "api_base_network_path": "same_origin_proxy",
        }

    def fake_record_phone_runtime_proof(*args, **kwargs):
        calls["record"] += 1
        raise AssertionError("dry-run phone proof must not write evidence")

    monkeypatch.setattr(
        mobile_route,
        "build_phone_runtime_proof",
        fake_build_phone_runtime_proof,
    )
    monkeypatch.setattr(
        mobile_route,
        "record_phone_runtime_proof",
        fake_record_phone_runtime_proof,
    )
    payload = {
        "source": "web-phone-smoke",
        "app_surface": "pwa",
        "url_origin": "http://10.0.0.6:4173",
        "url_path": "/?page=quick-start",
        "api_base": "http://10.0.0.6:4173/api/forex",
        "display_mode": "standalone",
        "standalone_pwa": True,
        "user_agent": "Mozilla/5.0 (iPhone) Mobile Safari/604.1",
        "platform": "iPhone",
        "viewport_width": 390,
        "screen_width": 390,
        "max_touch_points": 5,
        "dry_run": True,
    }

    status, body = asyncio.run(
        _asgi_post_with_headers(
            "/api/forex/mobile/phone-proof",
            payload,
            {
                "x-forwarded-for": "10.0.0.55",
                "x-real-ip": "10.0.0.55",
                "x-cas-client-api-base": "http://10.0.0.6:4173/api/forex",
            },
        )
    )

    assert status == 200
    assert body["dry_run"] is True
    assert body["status"] == "DRY_RUN_NOT_RECORDED"
    assert body["phone_browser_verified"] is True
    assert calls == {"build": 1, "record": 0}


def test_android_project_is_trackable_and_release_signing_is_explicit():
    root_gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    android_gitignore = (REPO_ROOT / "ui" / "android" / ".gitignore").read_text(encoding="utf-8")
    package_json = (REPO_ROOT / "ui" / "package.json").read_text(encoding="utf-8")
    app_gradle = (REPO_ROOT / "ui" / "android" / "app" / "build.gradle").read_text(encoding="utf-8")
    example = (REPO_ROOT / "ui" / "android" / "keystore.properties.example").read_text(encoding="utf-8")
    mobile_doc = (REPO_ROOT / "docs" / "MOBILE_APP.md").read_text(encoding="utf-8")
    install_script = (REPO_ROOT / "scripts" / "install_android_debug_apk.py").read_text(encoding="utf-8")
    final_verification_script = (REPO_ROOT / "scripts" / "run_mobile_final_verification.py").read_text(encoding="utf-8")
    phone_proof_script = (REPO_ROOT / "scripts" / "watch_mobile_phone_proof.py").read_text(encoding="utf-8")
    phone_proof_verifier = (REPO_ROOT / "cas_forex" / "mobile_phone_verifier.py").read_text(encoding="utf-8")
    apk_proof = (REPO_ROOT / "cas_forex" / "mobile_apk_proof.py").read_text(encoding="utf-8")

    assert "\nui/android/\n" not in root_gitignore
    assert "ui/android/" in dockerignore
    assert "ui/ios/" in dockerignore
    assert "local.properties" in android_gitignore
    assert "app/src/main/assets/public" in android_gitignore
    assert "keystore.properties" not in root_gitignore
    assert '"mobile:apk:release":' in package_json
    assert '"mobile:apk:build-all":' in package_json
    assert "scripts/build_android_apks.py" in package_json
    assert "casReleaseSigningReady" in app_gradle
    assert "keystore.properties" in app_gradle
    assert "CAS_FOREX_ANDROID_STOREFILE" in app_gradle
    assert "CAS Forex release signing is not configured" in app_gradle
    assert "storeFile=cas-forex-release.jks" in example
    assert "Signed release APK" in mobile_doc
    assert "npm --prefix ui run mobile:apk:release" in mobile_doc
    assert "npm --prefix ui run mobile:apk:build-all" in mobile_doc
    assert "Build both debug and signed release APKs serially" in mobile_doc
    assert '"mobile:apk:devices":' in package_json
    assert '"mobile:apk:install":' in package_json
    assert '"mobile:apk:pair":' in package_json
    assert '"mobile:apk:install-pair":' in package_json
    assert '"mobile:apk:wait-install-pair":' in package_json
    assert '"@capacitor/app":' in package_json
    assert "npm --prefix ui run mobile:apk:install" in mobile_doc
    assert "npm --prefix ui run mobile:apk:wait-install-pair" in mobile_doc
    assert "npm --prefix ui run mobile:apk:install-pair" in mobile_doc
    assert "npm --prefix ui run mobile:apk:pair" in mobile_doc
    assert "evidence_runs/mobile_apk_proof/latest/android_apk_install_pairing_proof.json" in mobile_doc
    assert "Android APK/native-pairing" in mobile_doc
    assert "gate without waiting for a full release-bundle regeneration" in mobile_doc
    assert "android_adb_path" in mobile_doc
    assert "No device, adb ready" in mobile_doc
    assert "local.properties" in mobile_doc
    assert '"mobile:readiness":' in package_json
    assert '"mobile:stack":' in package_json
    assert '"mobile:verify-session":' in package_json
    assert '"mobile:proof-session":' in package_json
    assert '"mobile:verification-plan":' in package_json
    assert '"mobile:finish":' in package_json
    assert '"mobile:phone-proof":' in package_json
    assert '"mobile:docker-check":' in package_json
    assert '"mobile:docker-install":' in package_json
    assert '"mobile:docker-install-elevated":' in package_json
    assert "run_mobile_release_readiness.py" in mobile_doc
    assert "run_mobile_stack_readiness.py" in mobile_doc
    assert "run_phone_verification_session.py" in package_json
    assert "run_mobile_proof_session.py" in package_json
    assert "run_mobile_verification_plan.py" in package_json
    assert "run_mobile_final_verification.py" in package_json
    assert "--watch-all" in final_verification_script
    assert "--run-apk-pairing" in final_verification_script
    assert "DEFAULT_WATCH_ALL_PHONE_TIMEOUT_SECONDS = 900.0" in final_verification_script
    assert "--print-live-pairing-links" in final_verification_script
    assert "terminal only; not written to evidence" in final_verification_script
    assert "install_android_debug_apk" in final_verification_script
    assert "watch_mobile_phone_proof.py" in package_json
    assert "npm --prefix ui run mobile:phone-proof" in mobile_doc
    assert "prints an initial phone handoff" in mobile_doc
    assert "JSON mode stays machine-readable" in mobile_doc
    assert "npm --prefix ui run mobile:proof-session" in mobile_doc
    assert "npm --prefix ui run mobile:verification-plan" in mobile_doc
    assert "npm --prefix ui run mobile:finish" in mobile_doc
    assert "npm --prefix ui run mobile:finish -- --watch-all" in mobile_doc
    assert "900-second default window" in mobile_doc
    assert "-- --print-live-pairing-links" in mobile_doc
    assert "Copy live watcher" in mobile_doc
    assert "written into `mobile_final_verification.json`" in mobile_doc
    assert "npm --prefix ui run mobile:verify-session" in mobile_doc
    assert "npm --prefix ui run mobile:readiness" in mobile_doc
    assert "npm --prefix ui run mobile:stack" in mobile_doc
    assert "npm --prefix ui run mobile:docker-check" in mobile_doc
    assert "npm --prefix ui run mobile:docker-install" in mobile_doc
    assert "npm --prefix ui run mobile:docker-install-elevated" in mobile_doc
    assert "docker_desktop_install_attempt.json" in mobile_doc
    assert "GET /api/forex/mobile/proof-session/latest" in mobile_doc
    assert "GET /api/forex/mobile/verification-plan/latest" in mobile_doc
    assert "POST /api/forex/mobile/verification-plan/refresh" in mobile_doc
    assert "GET /api/forex/mobile/final-verification/latest" in mobile_doc
    assert "POST /api/forex/mobile/final-verification/refresh" in mobile_doc
    assert "evidence_runs/mobile_verification_plan/latest/" in mobile_doc
    assert "evidence_runs/mobile_final_verification/latest/" in mobile_doc
    assert "Copy Docker diagnosis" in mobile_doc
    assert "Copy elevated Docker install" in mobile_doc
    assert "Copy verification plan" in mobile_doc
    assert "wait_for_phone_proof" in phone_proof_script
    assert "--exit-code-on-missing" in phone_proof_script
    assert "Initial phone proof status:" in phone_proof_script
    assert "Final phone proof status:" in phone_proof_script
    assert "Waiting up to " in phone_proof_script
    assert "Phone Quick Start URL:" in phone_proof_verifier
    assert "Tested Quick Start URL:" in phone_proof_verifier
    assert "LOCAL_DESKTOP_ONLY" in phone_proof_verifier
    assert "Watch phone proof:" in phone_proof_verifier
    assert "Refresh readiness:" in phone_proof_verifier
    assert "LOCAL_DESKTOP_ONLY" in mobile_doc
    assert "CAS_FOREX_ADB" in install_script
    assert "--launch-native-pairing" in install_script
    assert "--launch-only" in install_script
    assert "--wait-for-device" in install_script
    assert "--wait-timeout-seconds" in install_script
    assert "record_android_apk_install_pairing_proof" in install_script
    assert "android_apk_install_pairing_verified" in apk_proof
    assert "latest_android_apk_install_pairing_proof" in apk_proof
    assert "APK/dev-server direct API base" in mobile_doc
    assert "casforex://pair" in mobile_doc
    assert "VITE_CAS_FOREX_API_BASE" in mobile_doc


def test_android_apk_accepts_native_pairing_deep_link():
    manifest = (REPO_ROOT / "ui" / "android" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
    strings = (REPO_ROOT / "ui" / "android" / "app" / "src" / "main" / "res" / "values" / "strings.xml").read_text(encoding="utf-8")
    plugins = (REPO_ROOT / "ui" / "android" / "app" / "src" / "main" / "assets" / "capacitor.plugins.json").read_text(encoding="utf-8")
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    api_core = (REPO_ROOT / "ui" / "src" / "data" / "apiCore.ts").read_text(encoding="utf-8")
    owner_badge = (REPO_ROOT / "ui" / "src" / "components" / "OwnerAccessBadge.tsx").read_text(encoding="utf-8")
    owner_auth_api = (REPO_ROOT / "ui" / "src" / "data" / "ownerAuthApi.ts").read_text(encoding="utf-8")

    assert 'android:name="android.intent.action.VIEW"' in manifest
    assert 'android:name="android.intent.category.BROWSABLE"' in manifest
    assert 'android:scheme="casforex"' in manifest
    assert 'android:host="pair"' in manifest
    assert "<string name=\"custom_url_scheme\">casforex</string>" in strings
    assert '"pkg": "@capacitor/app"' in plugins
    assert '"classpath": "com.capacitorjs.plugins.app.AppPlugin"' in plugins
    assert 'import("@capacitor/app")' in app
    assert "CapacitorApp.getLaunchUrl()" in app
    assert 'CapacitorApp.addListener("appUrlOpen"' in app
    assert "consumeOwnerPairingFromUrl(url)" in app
    assert "setPage(result.page)" in app
    assert "export function consumeOwnerPairingFromUrl(" in api_core
    assert "parsed.searchParams.get(OWNER_TOKEN_HASH_KEY)" in api_core
    assert "parsed.searchParams.get(API_BASE_HASH_KEY)" in api_core
    assert "isTrustedPairingApiBase(apiBase)" in api_core
    assert "scrubPairingStateFromCurrentLocation()" in api_core
    assert "native_pairing_urls?: string[]" in owner_auth_api
    assert "Android app pairing link" in owner_badge
    assert "nativePairingUrls[0]" in owner_badge


def test_phone_browser_prefers_same_origin_api_proxy_without_saved_override():
    api_core = (REPO_ROOT / "ui" / "src" / "data" / "apiCore.ts").read_text(encoding="utf-8")
    waste_probe = (REPO_ROOT / "ui" / "src" / "data" / "wasteStageProbe.ts").read_text(encoding="utf-8")

    assert "function sameOriginApiBase(): string | null" in api_core
    assert "function isCapacitorShell(): boolean" in api_core
    assert "if (isCapacitorShell()) return null;" in api_core
    assert "const isCapacitor = isCapacitorShell();" in api_core
    assert "const isLocalBrowser = !isCapacitor && (" in api_core
    assert "function readSavedApiBaseOverride(): string | null" in api_core
    assert ": [savedOverride, rememberedBase, originBase, DEFAULT_API_BASE]" in api_core
    assert "function sameOriginApiBase(): string | null" in waste_probe
    assert "function isCapacitorShell(): boolean" in waste_probe
    assert "if (isCapacitorShell()) return null;" in waste_probe
    assert "function readSavedApiBaseOverride(): string | null" in waste_probe
    assert ": [savedOverride, rememberedBase, originBase, DEFAULT_API_BASE]" in waste_probe


def test_phone_pairing_link_uses_hash_token_and_is_consumed_on_startup():
    api_core = (REPO_ROOT / "ui" / "src" / "data" / "apiCore.ts").read_text(encoding="utf-8")
    owner_auth_api = (REPO_ROOT / "ui" / "src" / "data" / "ownerAuthApi.ts").read_text(encoding="utf-8")
    owner_badge = (REPO_ROOT / "ui" / "src" / "components" / "OwnerAccessBadge.tsx").read_text(encoding="utf-8")
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    package_json = (REPO_ROOT / "ui" / "package.json").read_text(encoding="utf-8")
    mobile_doc = (REPO_ROOT / "docs" / "MOBILE_APP.md").read_text(encoding="utf-8")

    assert 'OWNER_TOKEN_HASH_KEY = "cas_owner_token"' in api_core
    assert 'API_BASE_HASH_KEY = "cas_api_base"' in api_core
    assert "function consumeOwnerTokenFromLocation(): boolean" in api_core
    assert "consumeOwnerPairingFromUrl(window.location.href" in api_core
    assert "new URLSearchParams(hash)" in api_core
    assert "hashParams.get(OWNER_TOKEN_HASH_KEY)" in api_core
    assert "hashParams.get(API_BASE_HASH_KEY)" in api_core
    assert "setOwnerToken(token);" in api_core
    assert "setApiBase(apiBase);" in api_core
    assert "function isTrustedPairingApiBase(value: string): boolean" in api_core
    assert '["http:", "https:"].includes(parsed.protocol)' in api_core
    assert "parsed.username || parsed.password || parsed.search || parsed.hash" in api_core
    assert 'parsed.pathname.replace(/\\/+$/, "") !== "/api/forex"' in api_core
    assert "function isPrivateIpv4Host(host: string): boolean" in api_core
    assert 'host.endsWith(".local")' in api_core
    assert "params.delete(OWNER_TOKEN_HASH_KEY);" in api_core
    assert "params.delete(API_BASE_HASH_KEY);" in api_core
    assert "window.history.replaceState(null, \"\", next.toString());" in api_core
    assert "consumeOwnerTokenFromLocation" in owner_auth_api
    assert "consumeOwnerPairingFromUrl" in app
    assert "consumeOwnerPairingFromUrl(window.location.href, { scrubCurrentLocation: true })" in app
    assert 'const raw = pairing.page ?? new URLSearchParams(window.location.search).get("page");' in app
    assert "pairing_urls?: string[]" in owner_auth_api
    assert "pairing_api_bases?: string[]" in owner_auth_api
    assert "direct_api_bases?: string[]" in owner_auth_api
    assert "Phone pairing link" in owner_badge
    assert "Phone PWA API base" in owner_badge
    assert "APK/dev-server direct API base" in owner_badge
    assert "Copy APK API base" in owner_badge
    assert "Android wait/install-pair command" in owner_badge
    assert "Copy install-pair" in owner_badge
    assert "manualCopyValue" in owner_badge
    assert "navigator.clipboard.writeText" in owner_badge
    assert 'document.execCommand("copy")' in owner_badge
    assert "Copy unavailable; use the text below." in owner_badge
    assert "pairingUrls[0]" in owner_badge
    assert "pairingApiBases[0]" in owner_badge
    assert "directApiBases[0]" in owner_badge
    assert "nativePairingUrls[0]" in owner_badge
    assert "Owner Access copy buttons use a checked clipboard path" in mobile_doc
    assert "APK/direct" in mobile_doc
    assert '"qrcode"' in package_json
    assert '"@types/qrcode"' in package_json
    assert 'import QRCode from "qrcode";' not in owner_badge
    assert 'await import("qrcode")' in owner_badge
    assert "QRCode.toDataURL(url" in owner_badge
    assert "Scan to pair phone PWA" in owner_badge
    assert "Scan after APK install" in owner_badge
    assert "api.qrserver.com" not in owner_badge
    assert "generated locally in the browser" in mobile_doc


def test_dashboard_route_fallback_uses_instant_live_cockpit_shell():
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    app_css = (REPO_ROOT / "ui" / "src" / "App.css").read_text(encoding="utf-8")
    instant_shell = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardInstantShell.tsx"
    ).read_text(encoding="utf-8")

    assert 'import { DashboardInstantShell } from "./components/DashboardInstantShell";' in app
    assert 'page === "dashboard" ? <DashboardInstantShell state={state} />' in app
    assert "DashboardBootFallback" not in app
    assert "WASTE LOOP LIVE" in instant_shell
    assert 'className="glass-panel"' in instant_shell
    assert 'className="dashboard-grid-3col"' in instant_shell
    assert 'label="Account"' in instant_shell
    assert 'label="Risk Budget"' in instant_shell
    assert 'label="Proof"' in instant_shell
    assert "dashboard-instant" not in instant_shell
    assert ".dashboard-instant" not in app_css


def test_app_defers_root_waste_probe_helper_until_after_mount():
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    root_imports = app.split("function lazyPage", 1)[0]
    instant_probe = app.split("async function fetchInstantWasteStage()", 1)[1].split(
        "export function App()",
        1,
    )[0]

    assert "wasteStageProbe" not in root_imports
    assert 'await import("./data/wasteStageProbe")' in instant_probe
    assert "fetchWasteStageProbe({ timeoutMs: 1_500, maxAgeMs: 1_000 })" in instant_probe
    assert "wasteLoopFromStagePayload(payload" in instant_probe
    assert "void fetchInstantWasteStage().then" in app


def test_dashboard_route_mounts_hydrator_without_startup_delay():
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    hydrator = (
        REPO_ROOT / "ui" / "src" / "components" / "DashboardStateHydrator.tsx"
    ).read_text(encoding="utf-8")
    hydrator_effect = app.split('if (page === "dashboard") {', 1)[1].split("}, [page]);", 1)[0]

    assert 'if (page === "dashboard") {' in app
    assert "const [initialPage] = useState<Page>(() => initialPageFromUrl());" in app
    assert "const [page, setPageState] = useState<Page>(initialPage);" in app
    assert "const [dashboardHydratorMounted, setDashboardHydratorMounted] = useState(" in app
    assert '() => initialPage === "dashboard",' in app
    assert "setDashboardHydratorMounted(true);" in app
    assert "DASHBOARD_FAST_LANE_FETCH_DELAY_MS = 50" in app
    assert "BACKGROUND_DASHBOARD_HYDRATOR_IDLE_TIMEOUT_MS = 2_200" in app
    assert "FLOATING_ASSISTANT_IDLE_TIMEOUT_MS = 1_200" in app
    assert "function scheduleAppIdleWork(callback: () => void, timeoutMs: number): () => void" in app
    assert "scheduleAppIdleWork(\n      () => setAssistantMounted(true)," in app
    assert "requestIdleCallback" in app
    assert "cancelIdleCallback" in app
    assert 'fastFetchDeferMs={page === "dashboard" ? DASHBOARD_FAST_LANE_FETCH_DELAY_MS : undefined}' in app
    assert "}, [page]);" in app
    assert "setDashboardHydratorMounted(true);" in hydrator_effect
    assert hydrator_effect.index("setDashboardHydratorMounted(true);") < hydrator_effect.index(
        "requestIdleCallback",
    )
    assert "BACKGROUND_DASHBOARD_HYDRATOR_IDLE_TIMEOUT_MS" in hydrator_effect
    assert "window.setTimeout(" in hydrator_effect
    assert "fastFetchDeferMs?: number" in hydrator
    assert 'from "../data/dashboardApi"' not in hydrator
    assert 'import("../data/dashboardApi")' in hydrator
    assert ".then(({ loadDashboardState }) =>" in hydrator
    assert "if (cancelled) return undefined;" in hydrator
    assert "return loadDashboardState(initialState, {" in hydrator
    assert "}, { fastFetchDeferMs });" in hydrator
    assert ".catch(() => {" in hydrator
    assert "[fastFetchDeferMs, initialState, onError, onState]" in hydrator


def test_dashboard_shell_cold_cache_returns_warming_without_blocking(monkeypatch):
    with api_server._dashboard_shell_cache_lock:
        api_server._dashboard_shell_cache.update(
            {"payload": None, "built_at": 0.0, "building": False, "error": None}
        )
    started: list[bool] = []
    monkeypatch.setattr(api_server, "_dashboard_cache_disabled_for_tests", lambda: False)
    monkeypatch.setattr(
        api_server,
        "dashboard_shell_state",
        lambda: (_ for _ in ()).throw(AssertionError("shell route blocked on cold cache")),
    )
    monkeypatch.setattr(api_server, "_start_dashboard_shell_cache_refresh", lambda: started.append(True) or True)

    status, body = asyncio.run(_asgi_get("/api/forex/dashboard/shell"))

    assert status == 200
    assert started == [True]
    assert body["dashboardMeta"]["kind"] == "shell"
    assert body["dashboardMeta"]["full_cache_status"] == "warming"
    assert body["wasteLoop"]["status"] == "WARMING"
    assert "uiReadiness" not in body


def test_dashboard_fast_cold_cache_returns_warming_without_blocking(monkeypatch):
    with api_server._dashboard_fast_cache_lock:
        api_server._dashboard_fast_cache.update(
            {"payload": None, "built_at": 0.0, "building": False, "error": None}
        )
    started: list[bool] = []
    monkeypatch.setattr(api_server, "_dashboard_cache_disabled_for_tests", lambda: False)
    monkeypatch.setattr(
        api_server,
        "dashboard_fast_state",
        lambda: (_ for _ in ()).throw(AssertionError("fast route blocked on cold cache")),
    )
    monkeypatch.setattr(api_server, "_start_dashboard_fast_cache_refresh", lambda: started.append(True) or True)

    status, body = asyncio.run(_asgi_get("/api/forex/dashboard/fast"))

    assert status == 200
    assert started == [True]
    assert body["dashboardMeta"]["kind"] == "fast"
    assert body["dashboardMeta"]["full_cache_status"] == "warming"
    assert body["proofProgress"]["readiness_status"] == "WARMING"
    assert body["riskBudget"]["risk_status"] == "WARMING"
    assert "authorityBoundary" not in body
    assert "wasteLoop" not in body
    assert "dailyBundle" not in body


def test_dashboard_startup_prewarms_shell_and_fast_caches(monkeypatch):
    started: list[str] = []
    monkeypatch.setattr(api_server, "_dashboard_cache_disabled_for_tests", lambda: False)
    monkeypatch.setattr(api_server.runtime_topology_core, "require_runtime_owner", lambda: None)
    monkeypatch.setattr(api_server.runtime_topology_core, "write_runtime_topology_status", lambda: None)
    monkeypatch.setattr(api_server, "_restore_owner_runtime_switches", lambda: started.append("restore"))
    monkeypatch.setattr(api_server, "_start_dashboard_shell_cache_refresh", lambda: started.append("shell") or True)
    monkeypatch.setattr(api_server, "_start_dashboard_fast_cache_refresh", lambda: started.append("fast") or True)
    monkeypatch.setattr(api_server, "_start_startup_route_cache_refreshes", lambda: started.append("routes") or {})

    asyncio.run(api_server.warm_dashboard_fast_cache())

    assert started == ["restore", "shell", "fast", "routes"]


def test_dashboard_shell_cache_timer_starts_before_fast_cache(monkeypatch):
    captured: list[tuple[float, str]] = []

    class FakeTimer:
        def __init__(self, delay: float, callback) -> None:
            captured.append((delay, callback.__name__))
            self.name = ""
            self.daemon = False

        def start(self) -> None:
            return None

    monkeypatch.setattr(api_server.threading, "Timer", FakeTimer)
    with api_server._dashboard_shell_cache_lock:
        api_server._dashboard_shell_cache.update({"building": False})
    with api_server._dashboard_fast_cache_lock:
        api_server._dashboard_fast_cache.update({"building": False})

    try:
        assert api_server._start_dashboard_shell_cache_refresh() is True
        assert api_server._start_dashboard_fast_cache_refresh() is True
    finally:
        with api_server._dashboard_shell_cache_lock:
            api_server._dashboard_shell_cache.update({"building": False})
        with api_server._dashboard_fast_cache_lock:
            api_server._dashboard_fast_cache.update({"building": False})

    assert captured == [
        (
            api_server._DASHBOARD_SHELL_CACHE_REFRESH_DELAY_SECONDS,
            "_refresh_dashboard_shell_cache_background",
        ),
        (
            api_server._DASHBOARD_FAST_CACHE_REFRESH_DELAY_SECONDS,
            "_refresh_dashboard_fast_cache_background",
        ),
    ]
    assert api_server._DASHBOARD_SHELL_CACHE_REFRESH_DELAY_SECONDS < api_server._DASHBOARD_FAST_CACHE_REFRESH_DELAY_SECONDS


def test_startup_route_cache_refreshes_hot_read_only_packets(monkeypatch):
    captured: list[tuple[str, bool, float]] = []
    monkeypatch.setattr(
        api_server,
        "start_cache_refresh",
        lambda key, builder, *, delay_seconds=0.2: captured.append((key, callable(builder), delay_seconds)) or True,
    )
    monkeypatch.setattr(
        api_server.operator_briefing,
        "start_operator_briefing_cache_refresh",
        lambda: True,
    )
    monkeypatch.setattr(
        api_server.stack_health,
        "start_stack_health_cache_refresh",
        lambda: True,
    )

    result = api_server._start_startup_route_cache_refreshes()

    assert result == {
        "proof_control_state": True,
        "waste_runner_status_fast": True,
        "broker_truth_monitor_fast_status": True,
        "dispatch_loop_status": True,
        "live_telemetry": True,
        "live_enable_authorization_report": True,
        "live_enable_state_report": True,
        "settings_authority_boundary": True,
        "settings_runtime_gates": True,
        "pcba_cockpit": True,
        "live_money_progression_packet_fast": True,
        "waste_loop_stage_runner": True,
        "live_readiness:False": True,
        "account_reconciliation:False": True,
        "auto_halt_status": True,
        "verified_profit_sweep_policy": True,
        "verified_profit_sweep_state": True,
        "verified_profit_sweep_payout_recovery": True,
        "live_recovery_status": True,
        "live_order_dry_run_latest": True,
        "live_order_dry_run_review": True,
        "waste_entry_dispatch_handoff": True,
        "waste_entry_pilot_promotion": True,
        "compound_add_order_dry_run_latest": True,
        "compound_add_order_dry_run_review": True,
        "compound_add_dispatch_handoff": True,
        "mt5_market_data_diagnostic_latest": True,
        "waste_real_candle_probe_latest": True,
        "stack_health_check": True,
        "operator_briefing": True,
        "ai_operator_state": True,
    }
    assert "_STARTUP_ROUTE_CACHE_DELAY_SECONDS = 1.0" in (
        REPO_ROOT / "api" / "server.py"
    ).read_text(encoding="utf-8")
    assert "_STARTUP_ROUTE_CACHE_STAGGER_SECONDS = 0.1" in (
        REPO_ROOT / "api" / "server.py"
    ).read_text(encoding="utf-8")
    assert captured == [
        (
            key,
            True,
            api_server._STARTUP_ROUTE_CACHE_DELAY_SECONDS
            + index * api_server._STARTUP_ROUTE_CACHE_STAGGER_SECONDS,
        )
            for index, key in enumerate(
                key
                for key in result
                if key not in {"operator_briefing", "stack_health_check", "ai_operator_state"}
            )
            if key not in {"operator_briefing", "stack_health_check", "ai_operator_state"}
        ]
    captured_delays = [delay for _, _, delay in captured]
    assert captured_delays == sorted(captured_delays)
    assert captured_delays[0] == api_server._STARTUP_ROUTE_CACHE_DELAY_SECONDS
    assert captured_delays[-1] > captured_delays[0]


def test_stack_health_startup_prewarm_uses_background_cache(monkeypatch):
    stack_health_route._clear_cache()
    started: list[tuple[str, tuple[Any, ...]]] = []

    class FakeTimer:
        def __init__(self, delay: float, callback, args: tuple[Any, ...] = ()) -> None:
            started.append((callback.__name__, args))
            self.name = ""
            self.daemon = False

        def start(self) -> None:
            return None

    monkeypatch.setattr(stack_health_route.threading, "Timer", FakeTimer)

    assert stack_health_route.start_stack_health_cache_refresh() is True
    assert stack_health_route.start_stack_health_cache_refresh() is False
    assert started == [("_refresh_cache_worker", ())]
    stack_health_route._clear_cache()


def test_dashboard_deep_cache_snapshot_reads_route_cache_without_inline_build(monkeypatch):
    captured: list[tuple[str, float]] = []

    def fake_cached_payload_snapshot(key: str, *, ttl_seconds: float):
        captured.append((key, ttl_seconds))
        if key == "account_reconciliation:False":
            return {
                "report_kind": "cas_forex_account_reconciliation",
                "overall_status": "RECONCILED",
                "checks": [{"check_id": "seed"}],
                "cache_status": "fresh",
            }
        if key == "waste_runner_status_fast":
            return {
                "report_kind": "cas_forex_waste_runner_fast",
                "status": "RUNNING",
                "cache_status": "fresh",
            }
        return None

    monkeypatch.setattr(api_server, "cached_payload_snapshot", fake_cached_payload_snapshot)

    status, body = asyncio.run(_asgi_get("/api/forex/dashboard/deep-cache"))

    assert status == 200
    assert body["report_kind"] == "cas_forex_dashboard_deep_cache_snapshot"
    assert body["packet_count"] == len(api_server._DASHBOARD_DEEP_CACHE_PACKETS)
    assert body["warm_packet_count"] == 2
    assert body["packets"]["accountReconciliation"]["overall_status"] == "RECONCILED"
    assert body["packets"]["wasteLoop"]["status"] == "RUNNING"
    assert body["packets"]["liveReadiness"]["cache_status"] == "warming"
    assert body["packets"]["liveReadiness"]["report_kind"] == "cas_forex_live_readiness"
    assert [key for key, _ in captured] == [
        spec[0] for spec in api_server._DASHBOARD_DEEP_CACHE_PACKETS.values()
    ]


def test_dashboard_full_refresh_returns_fast_packet_without_inline_aggregate(monkeypatch):
    with api_server._dashboard_cache_lock:
        api_server._dashboard_cache.update(
            {"payload": None, "built_at": 0.0, "building": False, "error": None}
        )
    with api_server._dashboard_fast_cache_lock:
        api_server._dashboard_fast_cache.update(
            {
                "payload": {
                    "uiReadiness": {"report_kind": "cached_fast_packet"},
                    "wasteLoop": {"status": "RUNNING"},
                },
                "built_at": 123.0,
                "building": False,
                "error": None,
            }
        )
    started: list[bool] = []
    monkeypatch.setenv("CAS_FOREX_ALLOW_FULL_DASHBOARD_REFRESH", "1")
    monkeypatch.setattr(api_server, "_dashboard_cache_disabled_for_tests", lambda: False)
    monkeypatch.setattr(
        api_server,
        "dashboard_state",
        lambda: (_ for _ in ()).throw(AssertionError("dashboard route called full aggregate inline")),
    )
    monkeypatch.setattr(api_server, "_start_dashboard_cache_refresh", lambda: started.append(True) or True)

    status, body = asyncio.run(_asgi_get("/api/forex/dashboard?refresh=true"))

    assert status == 200
    assert started == [True]
    assert body["dashboardMeta"]["kind"] == "fast"
    assert body["dashboardMeta"]["full_cache_status"] == "full_refreshing_fast_cache"
    assert body["uiReadiness"]["report_kind"] == "cached_fast_packet"
    assert body["wasteLoop"]["status"] == "RUNNING"


def test_dashboard_refresh_builders_share_serial_refresh_guard(monkeypatch):
    calls: list[str] = []

    def fake_run_serial_refresh(builder):
        calls.append(builder.__name__)
        return builder()

    def fake_shell_state():
        return {"report_kind": "shell"}

    def fake_fast_state():
        return {"report_kind": "fast"}

    def fake_full_state():
        return {"report_kind": "full"}

    monkeypatch.setattr(api_server, "run_serial_refresh", fake_run_serial_refresh)
    monkeypatch.setattr(api_server, "dashboard_shell_state", fake_shell_state)
    monkeypatch.setattr(api_server, "dashboard_fast_state", fake_fast_state)
    monkeypatch.setattr(api_server, "dashboard_state", fake_full_state)

    assert api_server._refresh_dashboard_shell_cache_blocking()["report_kind"] == "shell"
    assert api_server._refresh_dashboard_fast_cache_blocking()["report_kind"] == "fast"
    assert api_server._refresh_dashboard_cache_blocking()["report_kind"] == "full"
    assert calls == ["fake_shell_state", "fake_fast_state", "fake_full_state"]


def test_hot_polling_get_routes_skip_synchronous_request_trace():
    hot_paths = {
        "/health",
        "/api/forex/health",
        "/api/forex/dashboard",
        "/api/forex/dashboard/shell",
        "/api/forex/dashboard/fast",
        "/api/forex/dashboard/deep-cache",
        "/api/forex/live-telemetry",
        "/api/forex/agent-decision/latest",
        "/api/forex/mt/probe/latest",
        "/api/forex/risk-monitoring/portfolio",
        "/api/forex/timeframes/NAS100",
        "/api/forex/autonomous-loop/health",
        "/api/forex/stack-health/check",
        "/api/forex/notifications/backend",
        "/api/forex/notifications/subscriptions",
        "/api/forex/webhook-notifications/subscriptions",
        "/api/forex/webhook-notifications/critical-readiness",
        "/api/forex/proof-control/state",
        "/api/forex/settings/authority-boundary",
        "/api/forex/settings/runtime-gates",
        "/api/forex/settings/security-posture",
        "/api/forex/settings/professional-claims",
        "/api/forex/settings/spec-context",
        "/api/forex/settings/legal-review-readiness",
        "/api/forex/settings/legal-review-control",
        "/api/forex/settings/professional-readiness",
        "/api/forex/settings/public-launch-gate",
        "/api/forex/settings/bypass-launch-gate",
        "/api/forex/settings/ui-layout-contract",
        "/api/forex/settings/economic-calendar",
        "/api/forex/pcba/cockpit",
        "/api/forex/readiness/live",
        "/api/forex/live-enable/authorization",
        "/api/forex/live-enable/state",
        "/api/forex/waste-loop/stage",
        "/api/forex/dispatch-loop/status",
        "/api/forex/mt5/account",
        "/api/forex/ai-operator/state",
        "/api/forex/owner-auth/state",
        "/api/forex/strategy/leads",
        "/api/forex/strategy/forex-fury-replay-candidates",
        "/api/forex/webhook-notifications/critical-audit",
        "/api/forex/chart/window",
        "/api/forex/waste-loop-control/status/fast",
        "/api/forex/waste-loop-control/paper-sample-collector/scheduler",
        "/api/forex/broker-truth-monitor/status/fast",
        "/api/forex/operator-briefing",
        "/api/forex/account/ledger",
        "/api/forex/movement/snapshot",
        "/api/forex/reconciliation/account",
        "/api/forex/account/broker-sync-risk-preview",
        "/api/forex/money-movement/verified-profit-sweep/policy",
        "/api/forex/money-movement/verified-profit-sweep/state",
        "/api/forex/money-movement/verified-profit-sweep/payout-recovery",
        "/api/forex/live-money/progression-packet/fast",
        "/api/forex/live-recovery/status",
        "/api/forex/auto-halt/status",
        "/api/forex/waste-loop-control/mt5-market-data-diagnostic/latest",
        "/api/forex/waste-loop-control/real-candle-probe/latest",
        "/api/forex/live-order-dry-run/latest",
        "/api/forex/live-order-dry-run/review",
        "/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff",
        "/api/forex/live-order-dry-run/waste-entry-order/pilot-promotion",
        "/api/forex/live-order-dry-run/compound-add-order/latest",
        "/api/forex/live-order-dry-run/compound-add-order/review",
        "/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff",
    }

    for path in hot_paths:
        assert api_server._should_trace_request("GET", path) is False
        assert api_server._should_trace_request("OPTIONS", path) is False
        assert api_server._should_trace_request("POST", path) is True

    assert api_server._should_trace_request("GET", "/api/forex/order-dispatch/dispatch") is True


def test_settings_authority_and_runtime_routes_are_cache_first_fail_closed(monkeypatch):
    captured: list[dict[str, Any]] = []

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.append(
            {
                "key": key,
                "builder_callable": callable(builder),
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(settings_route, "cache_first_payload", fake_cache_first_payload)

    authority = asyncio.run(settings_route.get_authority_boundary())
    gates = asyncio.run(settings_route.get_runtime_gates())

    assert captured == [
        {
            "key": "settings_authority_boundary",
            "builder_callable": True,
            "ttl_seconds": 30.0,
            "block_on_cold": False,
        },
        {
            "key": "settings_runtime_gates",
            "builder_callable": True,
            "ttl_seconds": 30.0,
            "block_on_cold": False,
        },
    ]
    assert authority["live_trading_status"] == "CURRENTLY NOT LICENSED"
    assert authority["can_place_live_orders"] is False
    assert gates["all_real_money_authorized"] is False
    assert gates["decisions"]["live_trading"]["status"] == "CURRENTLY NOT LICENSED"


def test_pcba_cockpit_route_returns_warming_packet_without_blocking(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "builder_callable": callable(builder),
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(pcba_route, "cache_first_payload", fake_cache_first_payload)

    body = asyncio.run(pcba_route.get_pcba_cockpit())

    assert captured == {
        "key": "pcba_cockpit",
        "builder_callable": True,
        "ttl_seconds": 300.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_pcba_cockpit"
    assert body["source"] == "warming"
    assert body["summary"]["current_boundary_honest"] is True
    assert body["optimizer_guard"]["can_create_broker_accept"] is False
    assert body["optimizer_guard"]["can_unlock_live_trading"] is False


def test_live_readiness_route_returns_warming_without_blocking(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
                "builder_callable": callable(builder),
            }
        )
        return fallback()

    monkeypatch.setattr(readiness_route, "cache_first_payload", fake_cache_first_payload)

    status, body = asyncio.run(_asgi_get("/api/forex/readiness/live"))

    assert status == 200
    assert captured["key"] == "live_readiness:False"
    assert captured["block_on_cold"] is False
    assert captured["builder_callable"] is True
    assert body["report_kind"] == "cas_forex_live_readiness"
    assert body["readiness_status"] == "WARMING"
    assert body["live_money_authorized"] is False
    assert body["payment_movement_authorized"] is False


def test_broker_sync_readiness_blocks_on_cold_for_real_preview(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
                "builder_callable": callable(builder),
            }
        )
        return {
            "report_kind": "cas_forex_live_readiness",
            "sync_to_broker_snapshot": True,
            "checks_total": 19,
            "checks_passed": 9,
            "payment_movement_authorized": False,
            "live_money_authorized": False,
        }

    monkeypatch.setattr(readiness_route, "cache_first_payload", fake_cache_first_payload)

    body = asyncio.run(readiness_route.get_live_readiness(sync_to_broker=True))

    assert captured == {
        "key": "live_readiness:True",
        "ttl_seconds": 60.0,
        "block_on_cold": True,
        "builder_callable": True,
    }
    assert body["sync_to_broker_snapshot"] is True
    assert body["checks_total"] == 19


def test_broker_sync_reconciliation_blocks_on_cold_for_real_preview(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
                "builder_callable": callable(builder),
            }
        )
        return {
            "report_kind": "cas_forex_account_reconciliation",
            "sync_to_broker_snapshot": True,
            "overall_status": "RECONCILED",
            "checks_total": 7,
            "checks_ok": 7,
        }

    monkeypatch.setattr(reconciliation_route, "cache_first_payload", fake_cache_first_payload)

    body = asyncio.run(reconciliation_route.get_account_reconciliation(sync_to_broker=True))

    assert captured == {
        "key": "account_reconciliation:True",
        "ttl_seconds": 10.0,
        "block_on_cold": True,
        "builder_callable": True,
    }
    assert body["sync_to_broker_snapshot"] is True
    assert body["overall_status"] == "RECONCILED"


def test_account_ledger_route_accepts_owner_selected_positive_seed():
    status, body = asyncio.run(_asgi_get("/api/forex/account/ledger?initial_investment=2500"))
    assert status == 200
    assert body["summary"]["owner_selected_initial_investment_usd"] == 2500
    assert body["summary"]["requires_new_risk_review_for_selected_investment"] is True
    assert body["supported_history_tabs"] == ["Positions", "Orders", "Deals"]
    assert body["supported_time_filters"] == ["Seconds", "Minutes", "Hour", "Day", "Week", "Month", "Custom"]
    assert body["live_money_authorized"] is False
    assert body["payment_movement_authorized"] is False
    assert isinstance(body.get("movement_source_truth"), dict)
    assert body["movement_source_truth"]["price_source_status"] in {
        "STATIC_SIMULATION_FALLBACK",
        "MIXED_PROVIDER_AND_STATIC_FALLBACK",
        "PROVIDER_ACTIVE",
        "CACHE_WARMING",
        "WARMING",
    }
    assert isinstance(body["movement_source_truth"].get("position_feed_detail"), str)


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
    assert body["market_data_provider_requested"] is True
    assert body["market_data_provider"] != "none"
    assert body["price_source_status"] in {
        "PROVIDER_ACTIVE",
        "MIXED_PROVIDER_AND_STATIC_FALLBACK",
        "STATIC_SIMULATION_FALLBACK",
        "CACHE_WARMING",
    }
    assert "static_fallback_symbols" in body
    assert isinstance(body.get("movement_source_truth"), dict)
    assert body["movement_source_truth"]["movement_stream_present"] is True
    assert body["movement_source_truth"]["price_source_status"] in {
        "PROVIDER_ACTIVE",
        "MIXED_PROVIDER_AND_STATIC_FALLBACK",
        "STATIC_SIMULATION_FALLBACK",
        "CACHE_WARMING",
    }
    assert isinstance(body["movement_source_truth"].get("position_feed_detail"), str)

    static_status, static_body = asyncio.run(_asgi_get("/api/forex/movement/snapshot?use_provider=false"))
    assert static_status == 200
    assert static_body["market_data_provider_requested"] is False
    assert static_body["market_data_provider"] == "none"
    assert static_body["price_source_status"] in {"STATIC_SIMULATION_FALLBACK", "CACHE_WARMING"}
    assert isinstance(static_body.get("movement_source_truth"), dict)
    assert static_body["movement_source_truth"]["movement_stream_present"] is True
    assert static_body["movement_source_truth"]["price_source_status"] in {
        "STATIC_SIMULATION_FALLBACK",
        "CACHE_WARMING",
    }


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
    assert isinstance(body.get("movement_source_truth"), dict)
    assert body["movement_source_truth"]["movement_stream_present"] in {True, False}
    assert body["movement_source_truth"]["price_source_status"] in {
        "STATIC_SIMULATION_FALLBACK",
        "MIXED_PROVIDER_AND_STATIC_FALLBACK",
        "PROVIDER_ACTIVE",
        "CACHE_WARMING",
        "LEDGER_ONLY",
        "UNKNOWN",
        None,
    }

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
    assert isinstance(body.get("movement_source_truth"), dict)
    assert isinstance(body["movement_source_truth"].get("detail"), (str, type(None)))
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


def test_live_telemetry_client_and_ui_expose_position_source_truth():
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    live_telemetry = (
        REPO_ROOT / "ui" / "src" / "components" / "LiveTradesTelemetry.tsx"
    ).read_text(encoding="utf-8")

    assert "price_source?: string | null;" in api_client
    assert "price_stale?: boolean;" in api_client
    assert "stale_reason?: string | null;" in api_client
    assert "age_seconds?: number | null;" in api_client
    assert "age_days?: number | null;" in api_client
    assert "position_source_label?: string | null;" in api_client
    assert 'telemetry_source?: "mt5_demo_account_snapshot" | "mt5_live_account_snapshot" | "mt5_terminal_api_verifier" | "movement_stream" | "none";' in api_client
    assert "telemetry_stale?: boolean;" in api_client
    assert "telemetry_last_update_iso?: string | null;" in api_client
    assert "price_source_status?: string | null;" in api_client
    assert "position_feed_label?: string;" in api_client
    assert "position_feed_detail?: string;" in api_client
    assert "broker_ticket_position_count?: number;" in api_client
    assert "static_position_count?: number;" in api_client
    assert "movement_source_truth?: MovementSourceTruthSnapshot | null;" in api_client

    assert "Source update" in live_telemetry
    assert "Response built" in live_telemetry
    assert "Position feed" in live_telemetry
    assert "Broker-ticket rows" in live_telemetry
    assert "Static rows" in live_telemetry
    assert "snapshot?.movement_source_truth ?? snapshot?.data_freshness.movement_source" in live_telemetry
    assert "movementTruth?.position_feed_label" in live_telemetry
    assert "movementTruth?.position_feed_detail" in live_telemetry
    assert "snapshot?.broker_ticket_position_count" in live_telemetry
    assert "snapshot?.static_position_count" in live_telemetry
    assert "Reported rows" in live_telemetry
    assert "No MT5 broker positions are currently reported." in live_telemetry
    assert "No paper/demo simulator proof rows are currently reported." in live_telemetry
    assert "position feed:" in live_telemetry
    assert "No broker or paper/demo movement snapshot is feeding this panel right now" in live_telemetry


def test_money_affecting_failure_messages_state_when_nothing_changed():
    trade_page = (REPO_ROOT / "ui" / "src" / "pages" / "TradePage.tsx").read_text(encoding="utf-8")
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    live_operability = (
        REPO_ROOT / "ui" / "src" / "components" / "LiveOperabilityPanel.tsx"
    ).read_text(encoding="utf-8")

    assert "Provider settings were not saved. Withdrawal and payout configuration remains unchanged" in trade_page
    assert "Owner switch save failed. Live, broker, and payment authority remains at its prior state" in trade_page
    assert "Broker emergency request failed before execution confirmation. No broker emergency action was confirmed through this app" in settings_page
    assert "Broker sync preview unavailable; using the default readiness report only." in live_operability


def test_operator_briefing_surface_marks_simulator_vs_mt5_position_truth():
    operator_api = (REPO_ROOT / "ui" / "src" / "data" / "operatorBriefingApi.ts").read_text(encoding="utf-8")
    shared_api = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    operator_card = (
        REPO_ROOT / "ui" / "src" / "components" / "OperatorBriefingCard.tsx"
    ).read_text(encoding="utf-8")

    for text in (
        "live_telemetry_source?: string;",
        "live_telemetry_stale?: boolean;",
        "live_telemetry_last_update_iso?: string | null;",
        "live_price_source_status?: string | null;",
        "live_position_feed_label?: string;",
        "live_position_feed_detail?: string;",
        "live_movement_source_truth?: MovementSourceTruthSnapshot | null;",
        "broker_truth_monitor_status?: string;",
        "broker_truth_ready_for_live?: boolean;",
        "broker_truth_paper_force_latched?: boolean;",
        "broker_truth_halt_reason_labels?: string[];",
        "broker_truth_halt_reason_summary?: string;",
        "broker_truth_position_protection_label?: string;",
        "broker_truth_unprotected_position_count?: number;",
        "broker_truth_position_protection_detail?: string | null;",
    ):
        assert text in operator_api
        assert text in shared_api

    assert "formatMovementSourceStatus" in operator_card
    assert "movementSourceStatusTone" in operator_card
    assert "live_movement_source_truth" in operator_card
    assert "brokerTruthVariant" in operator_card
    assert "positionProtectionVariant" in operator_card
    assert "position feed:" in operator_card
    assert "telemetry source:" in operator_card
    assert "broker truth:" in operator_card
    assert "halt reasons:" in operator_card
    assert "Broker truth enforcement" in operator_card
    assert "Paper-force is latched by broker truth" in operator_card
    assert "Position protection:" in operator_card
    assert "Position feed boundary" in operator_card


def test_portfolio_risk_surface_marks_simulator_vs_mt5_position_truth():
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    portfolio_card = (
        REPO_ROOT / "ui" / "src" / "components" / "PortfolioRiskCard.tsx"
    ).read_text(encoding="utf-8")

    for text in (
        "telemetry_source: string;",
        "telemetry_stale: boolean;",
        "telemetry_last_update_iso: string | null;",
        "price_source_status: string | null;",
        "position_feed_label: string;",
        "position_feed_detail: string;",
        "broker_ticket_position_count: number;",
        "static_position_count: number;",
        "movement_source_truth?: MovementSourceTruthSnapshot | null;",
    ):
        assert text in api_client

    assert 'import { StatusChip } from "./StatusChip"' in portfolio_card
    assert "formatMovementSourceStatus" in portfolio_card
    assert "movementSourceStatusTone" in portfolio_card
    assert "movement_source_truth" in portfolio_card
    assert "Position Feed" in portfolio_card
    assert "Price Source" in portfolio_card
    assert "position feed:" in portfolio_card
    assert "telemetry source:" in portfolio_card


def test_runtime_topology_is_exposed_in_settings_and_api_client():
    api_types = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    server = (REPO_ROOT / "api" / "server.py").read_text(encoding="utf-8")
    launcher = (REPO_ROOT / "scripts" / "run_api_server.py").read_text(encoding="utf-8")

    assert "export interface RuntimeTopologyStatus" in api_types
    assert 'apiGet<RuntimeTopologyStatus>("/runtime-topology")' in api_types
    assert "<RuntimeTopologyPanel />" in settings_page
    assert 'title="Runtime Process Topology"' in settings_page
    assert 'label="API Workers"' in settings_page
    assert 'prefix="/api/forex/runtime-topology"' in server
    assert "validate_api_worker_count" in launcher
    assert "requires exactly one stateful API worker" in (
        REPO_ROOT / "cas_forex" / "runtime_topology.py"
    ).read_text(encoding="utf-8")
