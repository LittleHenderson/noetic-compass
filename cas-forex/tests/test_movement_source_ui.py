from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_shared_movement_source_helper_defines_static_and_provider_classification():
    helper = (REPO_ROOT / "ui" / "src" / "util" / "movementSource.ts").read_text(encoding="utf-8")

    assert "export function summarizeMovementSource" in helper
    assert "export function describeMovementPositionFeed" in helper
    assert "export function describeReconciliationMovementTruth" in helper
    assert "export function formatMovementSourceStatus" in helper
    assert "export function formatMovementPositionSourceLabel" in helper
    assert "export function formatMovementPositionAge" in helper
    assert "export function isStaticMovementPosition" in helper
    assert "PositionFeedTruth" in helper
    assert "friendlyProviderName" in helper
    assert "STATIC_SIMULATION_FALLBACK" in helper
    assert "MIXED_PROVIDER_AND_STATIC_FALLBACK" in helper
    assert "PROVIDER_ACTIVE" in helper
    assert "price_source_summary" in helper
    assert "price_source_warning" in helper
    assert "static_simulation_active" in helper
    assert "position_feed_title" in helper
    assert "position_feed_count_label" in helper
    assert "position_feed_label" in helper
    assert "position_feed_detail" in helper
    assert "broker_ticket_position_count" in helper
    assert "static_position_count" in helper
    assert "static_quote_count" in helper
    assert "provider_stale_symbols" in helper
    assert "provider_freshness_max_age_seconds" in helper
    assert "snapshot_age_seconds_by_symbol" in helper
    assert 'return "SIM+MT5"' in helper
    assert "MT5 fallback" in helper
    assert "stale provider/MT5 snapshots rejected" in helper
    assert "live MT5 broker positions" in helper
    assert "paper/demo simulator proof rows with static stale pricing" in helper
    assert "Static simulator rows are not being moved by usable provider/MT5 quotes right now" in helper
    assert "movement_source_truth" in helper
    assert "backendLabel" in helper
    assert "backendDetail" in helper
    assert 'if (brokerTicket) return "MT5"' not in helper
    assert 'return "SIM TICKET STATIC"' in helper
    assert 'return "SIM TICKET+MT5"' in helper
    assert 'return "SIM TICKET+QUOTE"' in helper


def test_active_execution_account_precedes_simulator_scoreboards_in_ui():
    windows_page = (REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.tsx").read_text(encoding="utf-8")
    operator_badge = (REPO_ROOT / "ui" / "src" / "components" / "OperatorBadge.tsx").read_text(encoding="utf-8")
    operator_api = (REPO_ROOT / "ui" / "src" / "data" / "operatorApi.ts").read_text(encoding="utf-8")

    assert "active account truth:" in windows_page
    assert "primaryMt5Account" in windows_page
    assert "activeBalance" in windows_page
    assert "Simulator balance and P&amp;L are never added to MT5 account totals." in windows_page
    assert "<Mt5LiveAccountPanel mt5={mt5} />" in windows_page
    assert "Active execution account" in operator_badge
    assert "Simulator ledger balance" in operator_badge
    assert "Secondary simulator evidence" in operator_badge
    assert "Daily profit objective (not a trade quota)" in operator_badge
    assert "Being behind this objective cannot create a setup" in operator_badge
    assert "active_account_objective?:" in operator_api


def test_movement_source_helper_is_wired_across_ui_surfaces():
    app_shell = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    dashboard_page = (REPO_ROOT / "ui" / "src" / "pages" / "DashboardPage.tsx").read_text(encoding="utf-8")
    dashboard_shell = (REPO_ROOT / "ui" / "src" / "components" / "DashboardInstantShell.tsx").read_text(encoding="utf-8")
    evidence_panels = (REPO_ROOT / "ui" / "src" / "components" / "DashboardEvidencePanels.tsx").read_text(encoding="utf-8")
    proof_page = (REPO_ROOT / "ui" / "src" / "pages" / "ProofPage.tsx").read_text(encoding="utf-8")
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    tracker_page = (REPO_ROOT / "ui" / "src" / "pages" / "TrackerPage.tsx").read_text(encoding="utf-8")
    trade_page = (REPO_ROOT / "ui" / "src" / "pages" / "TradePage.tsx").read_text(encoding="utf-8")
    daily_report_page = (REPO_ROOT / "ui" / "src" / "pages" / "DailyReportPage.tsx").read_text(encoding="utf-8")
    daily_report_css = (REPO_ROOT / "ui" / "src" / "pages" / "DailyReportPage.css").read_text(encoding="utf-8")
    history_page = (REPO_ROOT / "ui" / "src" / "pages" / "HistoryPage.tsx").read_text(encoding="utf-8")
    ledger_page = (REPO_ROOT / "ui" / "src" / "pages" / "LedgerPage.tsx").read_text(encoding="utf-8")
    decision_history_page = (REPO_ROOT / "ui" / "src" / "pages" / "DecisionHistoryPage.tsx").read_text(encoding="utf-8")
    decision_card = (REPO_ROOT / "ui" / "src" / "components" / "AgentDecisionCard.tsx").read_text(encoding="utf-8")
    decision_truth = (REPO_ROOT / "ui" / "src" / "components" / "DecisionMovementTruth.tsx").read_text(encoding="utf-8")
    decision_css = (REPO_ROOT / "ui" / "src" / "components" / "DecisionCardPrimitives.css").read_text(encoding="utf-8")
    windows_page = (REPO_ROOT / "ui" / "src" / "pages" / "WindowsPage.tsx").read_text(encoding="utf-8")
    trading_window = (REPO_ROOT / "ui" / "src" / "components" / "TradingWindow.tsx").read_text(encoding="utf-8")
    live_telemetry = (REPO_ROOT / "ui" / "src" / "components" / "LiveTradesTelemetry.tsx").read_text(encoding="utf-8")
    live_readiness = (REPO_ROOT / "ui" / "src" / "components" / "LiveReadinessSummaryPanel.tsx").read_text(encoding="utf-8")
    live_operability = (REPO_ROOT / "ui" / "src" / "components" / "LiveOperabilityPanel.tsx").read_text(encoding="utf-8")
    movement_truth_panel = (REPO_ROOT / "ui" / "src" / "components" / "MovementTruthPanel.tsx").read_text(encoding="utf-8")

    assert "DashboardInstantShell" in app_shell
    assert "formatMovementSourceStatus" not in dashboard_page
    assert "movementSourceStatusTone" not in dashboard_page
    assert "summarizeMovementSource" not in dashboard_page
    assert "function formatPriceSourceStatus" not in dashboard_page

    assert "formatMovementSourceStatus" in dashboard_shell
    assert "movementSourceStatusTone" in dashboard_shell
    assert "summarizeMovementSource" in dashboard_shell
    assert "sourceHealth?.detail || movementSource.warningText" in dashboard_shell
    assert "function priceSourceLabel" not in dashboard_shell

    assert "summarizeMovementSource" in evidence_panels
    assert "movementSource.warningText" in evidence_panels
    assert "describeReconciliationMovementTruth" in evidence_panels
    assert "reconMovementTruth.detail" in evidence_panels

    assert "describeReconciliationMovementTruth" in proof_page
    assert "Movement Feed" in proof_page
    assert "movementTruth.detail" in proof_page

    assert "describeReconciliationMovementTruth" in settings_page
    assert "Movement Feed" in settings_page
    assert "movementTruth.detail" in settings_page

    assert "summarizeMovementSource" in tracker_page
    assert "describeMovementPositionFeed" in tracker_page
    assert "isStaticMovementPosition" in tracker_page
    assert "movement?.movement_source_truth ?? movement ?? null" in tracker_page
    assert "movementTruth?.static_quote_count ?? movement?.static_quote_count ??" in tracker_page
    assert "movementTruth?.static_position_count" in tracker_page
    assert "movementTruth?.broker_ticket_position_count" in tracker_page
    assert "Broker-ticket rows" in tracker_page
    assert "Static positions" in tracker_page
    assert "detailEvidenceForLiveReadinessCheck" in tracker_page
    assert "followup && followup !== check.plain_english" in tracker_page
    assert "formatPriceSourceStatus" not in tracker_page
    assert "priceSourceTone" not in tracker_page

    assert "detailEvidenceForLiveReadinessCheck" in live_readiness
    assert "detailEvidenceForLiveReadinessCheck(check)" in live_readiness

    assert "detailEvidenceForLiveReadinessCheck" in live_operability
    assert "followup && followup !== check.plain_english" in live_operability

    assert "summarizeMovementSource" in trade_page
    assert "movement?.movement_source_truth ?? movement ?? null" in trade_page
    assert "formatMovementPositionAge" in trade_page
    assert "formatMovementPositionSourceLabel" in trade_page
    assert "isStaticMovementQuote" in trade_page
    assert "MT5 FALLBACK" in trade_page

    assert "DailyRiskTruthPanel" in daily_report_page
    assert "Daily Movement Source Truth" in daily_report_page
    assert "risk?.source_truth" in daily_report_page
    assert "source_truth_observation" in daily_report_page
    assert "latest_position_feed_detail" in daily_report_page
    assert "price_source_statuses_observed" in daily_report_page
    assert "position_feed_labels_observed" in daily_report_page
    assert "formatMovementSourceStatus" in daily_report_page
    assert "movementSourceStatusTone" in daily_report_page
    assert ".daily-truth-status-row" in daily_report_css
    assert ".daily-truth-grid" in daily_report_css
    assert ".daily-truth-detail" in daily_report_css

    assert "export function MovementTruthPanel" in movement_truth_panel
    assert "Position Feed" in movement_truth_panel
    assert "Price Source" in movement_truth_panel
    assert "Static Paper Rows" in movement_truth_panel
    assert "Stale Rows" in movement_truth_panel
    assert "position_feed_detail" in movement_truth_panel
    assert "price_source_warning" in movement_truth_panel

    assert "MovementTruthPanel" in history_page
    assert "fetchAccountHealth" in history_page
    assert "History Movement Source Truth" in history_page
    assert "account?.movement_source_truth" in history_page

    assert "MovementTruthPanel" in ledger_page
    assert "fetchAccountHealth" in ledger_page
    assert "Ledger Movement Source Truth" in ledger_page
    assert "account?.movement_source_truth" in ledger_page

    assert "DecisionMovementTruth" in decision_card
    assert "data.movement_source_truth" in decision_card

    assert "DecisionMovementTruth" in decision_history_page
    assert "response?.movement_source_truth" in decision_history_page
    assert "Decision History Pricing Truth" in decision_history_page

    assert "export function DecisionMovementTruth" in decision_truth
    assert "Decision Pricing Truth" in decision_truth
    assert "position_feed_detail" in decision_truth
    assert "static_simulator_position_count" in decision_truth
    assert "stale_price_position_count" in decision_truth
    assert "formatMovementSourceStatus" in decision_truth

    assert ".decision-movement-truth" in decision_css
    assert ".decision-movement-chips" in decision_css
    assert ".decision-movement-detail" in decision_css

    assert "summarizeMovementSource" in windows_page
    assert "movement?.movement_source_truth ?? movement ?? null" in windows_page
    assert "describeMovementPositionFeed" in windows_page
    assert "formatMovementPositionAge" in windows_page
    assert "formatMovementPositionSourceLabel" in windows_page
    assert "function formatPositionSourceLabel" not in windows_page
    assert "position feed:" in windows_page
    assert "mt5 fallback:" in windows_page

    assert "movement?.movement_source_truth ?? movement ?? null" in evidence_panels

    assert "formatMovementPositionAge" in trading_window
    assert "formatMovementPositionSourceLabel" in trading_window
    assert "isStaticMovementPosition" in trading_window
    assert "positionsDetail" in trading_window
    assert "function formatPositionSourceLabel" not in trading_window
    assert "snapshot?.movement_source_truth ?? snapshot?.data_freshness.movement_source" in live_telemetry
    assert "summarizeMovementSource(movementTruth)" in live_telemetry
    assert "describeMovementPositionFeed" in live_telemetry
    assert "formatMovementPositionSourceLabel" in live_telemetry
    assert "formatMovementPositionAge" in live_telemetry
    assert "snapshot?.telemetry_source" in live_telemetry
    assert "movementTruth?.position_feed_label" in live_telemetry
    assert "movementTruth?.position_feed_detail" in live_telemetry
    assert "Source update" in live_telemetry
    assert "Response built" in live_telemetry
    assert "Position feed" in live_telemetry
    assert "Static rows" in live_telemetry
    assert "Static simulation" in live_telemetry
    assert "Provider-backed paper" in live_telemetry
    assert "Current MT5 demo broker positions and floating P&L, polled every 2s" in live_telemetry
    assert "Current MT5 live broker positions and floating P&L, polled every 2s" in live_telemetry
    assert "Observational only - paper/demo simulator proof rows; static rows can stay at entry until provider/MT5 quotes are usable" in live_telemetry
    assert "Reported rows" in live_telemetry
    assert "No paper/demo simulator proof rows are currently reported." in live_telemetry
    assert "position feed:" in live_telemetry
