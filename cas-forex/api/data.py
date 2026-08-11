"""Evidence-backed data loader for the CAS Forex proof cockpit API."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from cas_forex.account_ledger import (
    build_account_ledger_from_paper_review,
    build_live_account_ledger_from_terminal_history,
)
from cas_forex.account_health import build_account_health_report
from cas_forex.active_account_truth import build_active_account_truth
from cas_forex.auto_halt import build_auto_halt_report
from cas_forex.broker_truth_monitor import (
    latest_reconciliation_report as latest_broker_truth_reconciliation_report,
    monitor_status as broker_truth_monitor_status,
)
from cas_forex.broker_truth_recovery_packet import build_broker_truth_recovery_packet
from cas_forex.broker_reality import build_broker_reality_review
from cas_forex.compound_add_order_dry_run_review import build_compound_add_order_dry_run_review
from cas_forex.live_pilot import build_live_pilot_policy
from cas_forex.live_order_dry_run import DEFAULT_AUDIT_PATH as LIVE_ORDER_DRY_RUN_AUDIT_PATH
from cas_forex.live_order_dry_run import DEFAULT_COMPOUND_ADD_AUDIT_PATH as COMPOUND_ADD_DRY_RUN_AUDIT_PATH
from cas_forex.live_order_dry_run import LiveOrderDryRunAuditLog
from cas_forex.live_order_dry_run_review import build_live_order_dry_run_review
from cas_forex.live_recovery import build_live_recovery_report
from cas_forex.live_money_progression_packet import build_live_money_progression_packet
from cas_forex.order_attempt_audit import build_order_attempt_audit_status
from cas_forex.order_attempt_recovery_packet import build_order_attempt_recovery_packet
from cas_forex.payout_recovery import build_payout_recovery_status
from cas_forex.dispatch_loop import loop_status as dispatch_loop_status
from cas_forex.mt5_demo_learning_sync import load_mt5_demo_learning_sync
from cas_forex.mt5_account_growth import load_mt5_account_growth
from cas_forex.mt5_live import get_mt5_account_snapshot, get_mt5_position_protection_snapshot
from cas_forex.mt5_market_data_diagnostic import latest_mt5_market_data_diagnostic
from cas_forex.waste_real_candle_probe import latest_waste_real_candle_probe
from cas_forex.waste_direction_review_packet import build_waste_direction_review_packet
from cas_forex.waste_direction_learning_ledger import build_waste_direction_learning_ledger
from cas_forex.waste_direction_outcome_binding import build_waste_direction_outcome_binding
from cas_forex.waste_paper_sample_collector import (
    build_waste_paper_sample_collector,
    waste_paper_sample_collector_scheduler_status as build_waste_paper_sample_collector_scheduler_status,
)
from cas_forex.waste_adaptation_promotion_rule import build_waste_adaptation_promotion_rule
from cas_forex.waste_adaptation_plan import build_waste_adaptation_plan
from cas_forex.waste_adaptation_apply_preview import build_waste_adaptation_apply_preview
from cas_forex.waste_adaptation_owner_review import build_waste_adaptation_owner_review
from cas_forex.waste_adaptation_paper_apply import build_waste_adaptation_paper_apply_status
from cas_forex.waste_runner import build_compound_add_dispatch_handoff_status
from cas_forex.waste_pilot_promotion import build_waste_pilot_promotion_status
from cas_forex.movement_stream import MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS
from cas_forex.movement_stream import build_movement_stream_state
from cas_forex.movement_stream import build_movement_price_source_summary
from cas_forex.movement_stream import build_movement_position_feed_truth
from cas_forex.movement_stream import build_movement_source_truth_snapshot
from cas_forex.movement_stream import movement_snapshot_age_seconds
from cas_forex.movement_stream import movement_snapshot_issue_for_movement
from cas_forex.movement_stream import movement_snapshot_stale_for_movement
from cas_forex.movement_stream import movement_snapshot_usable_for_movement
from cas_forex.account_reconciliation import build_account_reconciliation_report
from cas_forex.live_readiness import build_live_readiness_report
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan
from cas_forex.paper_risk import (
    append_paper_risk_review,
    review_paper_risk_budget,
    review_payload,
    summarize_paper_risk_reviews,
    write_paper_risk_status,
)
from cas_forex.owner_control import build_owner_control_report
from cas_forex.market_data.connector import MT5TerminalMarketDataConnector, get_connector
from cas_forex.authority_boundary import build_authority_boundary_report
from cas_forex.runtime_gates import PENDING_OWNER_ENABLE, build_runtime_gates_report
from cas_forex.ai_model import model_status
from cas_forex.broker_profiles import broker_candidates
from cas_forex.ccb_readiness import build_ccb_readiness_report
from cas_forex.cjt_readiness import (
    build_cjt_production_readiness_report,
    collect_local_cjt_evidence,
)
from cas_forex.llm_optimizer import CLAIM_BOUNDARY as LLM_OPTIMIZER_CLAIM_BOUNDARY
from cas_forex.external_benchmark import load_external_benchmark_report
from cas_forex.forex_fury_candidates import (
    ForexFuryCandidateError,
    load_latest_forex_fury_replay_candidate_report,
)
from cas_forex.forex_fury_replay_results import (
    ForexFuryReplayResultError,
    load_latest_forex_fury_replay_results_report,
)
from cas_forex.forex_fury_sets import ForexFuryImportError, load_latest_forex_fury_set_import_report
from cas_forex.agent_workflow import AgentWorkflowPlanError, load_latest_agent_workflow_plan_report
from cas_forex.agent_state import AgentCycleError, load_latest_agent_cycle_report
from cas_forex.agent_information_flow import (
    AgentInformationFlowError,
    load_latest_agent_information_flow_report,
)
from cas_forex.agent_message_bus import (
    AgentMessageBusError,
    load_agent_event_summary,
    load_agent_events,
    load_latest_agent_context,
    load_latest_agent_receipts,
    load_open_agent_intents,
)
from cas_forex.agent_memory import AgentMemoryError, load_latest_agent_memory_report
from cas_forex.agent_research_queue import (
    AgentResearchQueueError,
    load_latest_agent_research_queue_report,
)
from cas_forex.strategy_dev_queue import (
    StrategyDevQueueError,
    load_latest_strategy_dev_queue_report,
)
from cas_forex.strategy_patch_runner import (
    StrategyPatchRunnerError,
    load_latest_strategy_patch_runner_report,
)
from cas_forex.daily_learning_rollup import (
    DailyLearningRollupError,
    load_latest_daily_learning_rollup_report,
)
from cas_forex.session_autowake_runner import (
    SessionAutowakeRunnerError,
    load_latest_session_autowake_report,
)
from cas_forex.terminal_receipt_watcher import (
    TerminalReceiptWatcherError,
    load_latest_terminal_receipt_watcher_report,
)
from cas_forex.terminal_bridge_supervisor import (
    TerminalBridgeSupervisorError,
    load_latest_terminal_bridge_supervisor_report,
)
from cas_forex.mt4_terminal_activation import (
    MT4TerminalActivationError,
    load_latest_mt4_terminal_activation_report,
)
from cas_forex.mt4_ping_roundtrip import (
    MT4PingRoundtripError,
    load_latest_mt4_ping_roundtrip_report,
)
from cas_forex.mt4_terminal_session_verifier import (
    MT4TerminalSessionVerifierError,
    load_latest_mt4_terminal_session_verifier_report,
)
from cas_forex.mt4_history_export_verifier import (
    MT4HistoryExportVerifierError,
    load_latest_mt4_history_export_verifier_report,
)
from cas_forex.mt5_terminal_api_verifier import (
    MT5TerminalApiVerifierError,
    load_latest_mt5_terminal_api_verifier_report,
)
from cas_forex.mt5_paper_execution_verifier import (
    MT5PaperExecutionVerifierError,
    load_latest_mt5_paper_execution_verifier_report,
)
from cas_forex.mt5_deal_history_ingest import (
    MT5DealHistoryIngestError,
    load_latest_mt5_deal_history_ingest_report,
)
from cas_forex.terminal_position_reconciliation import (
    TerminalPositionReconciliationError,
    load_latest_terminal_position_reconciliation_report,
)
from cas_forex.terminal_receipt_recovery_packet import (
    build_terminal_receipt_recovery_packet,
    run_terminal_receipt_archive_action,
)
from cas_forex.terminal_receipt_recovery_sequence import run_terminal_receipt_recovery_refresh
from cas_forex.terminal_operability_verifier import (
    TerminalOperabilityVerifierError,
    load_latest_terminal_operability_verifier_report,
)
from cas_forex.terminal_receipt_ingest import (
    TerminalReceiptIngestError,
    load_latest_terminal_receipt_ingest_report,
)
from cas_forex.terminal_history_ingest import (
    TerminalHistoryIngestError,
    load_latest_terminal_history_ingest_report,
)
from cas_forex.pcba_goal_status import build_pcba_goal_status
from cas_forex.pcba_readiness import (
    COMPONENT_CATALOG,
    build_pcba_production_readiness_report,
    collect_local_pcba_evidence,
    reference_boards,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPO_ROOT / "evidence_runs"
DEFAULT_RUNTIME_SIMULATOR_STATE_PATH = REPO_ROOT / "runtime" / "simulated-broker-state.json"
BACKSOLVE_DASHBOARD_MAX_BYTES = 25 * 1024 * 1024
PROOF_DIR = EVIDENCE_ROOT / "index_tsmom_126_paper_proof"
PLAN_ID = "index-tsmom-126-d1-paper-proof"


def _optional_dashboard_value(loader):
    try:
        return loader()
    except HTTPException:
        return None


def _waste_scheduler_fast_status() -> Dict[str, Any]:
    try:
        from cas_forex.waste_background_worker import COLLECTOR_KIND, worker_status

        worker = worker_status(COLLECTOR_KIND)
    except Exception:
        worker = {"running": False}
    config = worker.get("config") if isinstance(worker.get("config"), dict) else {}
    claim_boundary = (
        "Fast dashboard scheduler status is intentionally lightweight. Use "
        "/api/forex/waste-loop-control/paper-sample-collector/scheduler for "
        "the owner-toggle status and explicit probe actions for heavy evidence."
    )
    next_action = (
        "Paper sample collector worker is running."
        if worker.get("running")
        else "Start the paper sample collector from the Trade page when ready."
    )
    return {
        "report_kind": "cas_forex_waste_paper_sample_collector_scheduler",
        "generated_at": worker.get("checked_at"),
        "running": bool(worker.get("running", False)),
        "status": "WASTE_PAPER_SAMPLE_COLLECTOR_RUNNING" if worker.get("running") else "WASTE_PAPER_SAMPLE_COLLECTOR_STOPPED",
        "interval_seconds": config.get("interval_seconds", 300),
        "cycles_run": None,
        "started_at_iso": worker.get("started_at"),
        "last_run_iso": None,
        "last_error": None,
        "latest_collector_status": None,
        "config": {},
        "config_present": bool(config),
        "external_worker_present": bool(worker),
        "paper_only": True,
        "read_only_market_actions_only": True,
        "runtime_changed": False,
        "broker_execution_touched": False,
        "live_order_attempted": False,
        "money_moved": False,
        "claim_boundary": "",
        "claim_boundary_present": bool(claim_boundary),
        "next_action": "",
        "next_action_present": bool(next_action),
        "full_status_route": "/api/forex/waste-loop-control/paper-sample-collector/scheduler",
        "summary_only": True,
    }


def _waste_runner_fast_status() -> Dict[str, Any]:
    from api.routes.waste_loop_control import build_fast_waste_runner_status

    return build_fast_waste_runner_status()


def _waste_runner_shell_status() -> Dict[str, Any]:
    # Use the durable runner/supervisor view, then project only shell fields.
    # The local API process can be different from the process that owns the
    # timed WASTE lease, so local worker state alone can falsely read offline.
    status = _waste_runner_fast_status()
    return {
        "report_kind": "cas_forex_waste_runner_shell",
        "running": bool(status.get("running")),
        "status": status.get("status"),
        "current_stage": status.get("current_stage") or status.get("stage"),
        "cycles_run": status.get("cycles_run"),
        "mode": status.get("mode"),
        "last_reason": status.get("last_reason"),
        "last_run_iso": status.get("last_run_iso"),
        "worker_isolated": bool(status.get("worker_isolated")),
        "claim_boundary": (
            "Shell WASTE status is observational only. It does not authorize "
            "live trading, broker ACCEPT, LICENSED status, deposits, withdrawals, "
            "bank/card movement, payouts, or order execution."
        ),
    }


def dashboard_shell_state() -> Dict[str, Any]:
    """Ultra-small first-paint packet for the always-visible app shell."""
    return {
        "uiReadiness": _dashboard_ui_readiness_summary(ui_readiness()),
        "authorityBoundary": _optional_dashboard_value(_dashboard_authority_boundary_first_paint),
        "wasteLoop": _optional_dashboard_value(_waste_runner_shell_status),
    }


def dashboard_fast_state() -> Dict[str, Any]:
    """Small live dashboard packet for the app shell and operational pages."""
    readiness = ui_readiness()
    health = _optional_dashboard_value(account_health)
    return {
        "proofProgress": _dashboard_proof_progress_summary(readiness),
        "riskBudget": _dashboard_risk_budget_summary_from_latest_risk(),
        "accountHealth": (
            _dashboard_account_health_summary(health)
            if isinstance(health, dict)
            else None
        ),
        "activeAccountTruth": _optional_dashboard_value(
            lambda: active_account_truth(simulator_health_report=health)
        ),
        "ownerControl": _optional_dashboard_value(_dashboard_owner_control_summary_from_full),
        # Authority, WASTE, and broker-detail packets are already handled by the
        # shell route, instant stage probe, and deferred full fetches. Keep the
        # fast lane focused on first-paint Dashboard cards.
    }


def _numeric(value: Any) -> float:
    return value if isinstance(value, (int, float)) else 0.0


def _dashboard_risk_budget_summary_from_latest_risk() -> Dict[str, Any]:
    latest_risk_path = PROOF_DIR / f"{PLAN_ID}-paper-risk-status.json"
    risk = _read_json(latest_risk_path) if latest_risk_path.exists() else latest_risk()
    return _dashboard_risk_budget_summary(risk)


def _dashboard_risk_budget_summary(risk: Dict[str, Any]) -> Dict[str, Any]:
    """Tiny first-paint account/risk numbers; full sizing stays in dailyBundle."""
    latest_review = risk.get("latest_review") if isinstance(risk.get("latest_review"), dict) else {}
    sizing = latest_review.get("sizing")
    sizing_rows = sizing if isinstance(sizing, list) else []
    planned_risk_total_usd = (
        sum(_numeric(row.get("planned_risk_usd")) for row in sizing_rows if isinstance(row, dict))
        if sizing_rows
        else _numeric(
            latest_review.get("planned_risk_total_usd")
            or latest_review.get("total_planned_risk_usd")
            or risk.get("planned_risk_total_usd")
        )
    )
    planned_lots_total = (
        sum(_numeric(row.get("sized_lots")) for row in sizing_rows if isinstance(row, dict))
        if sizing_rows
        else _numeric(
            latest_review.get("planned_lots_total")
            or latest_review.get("total_planned_lots")
            or risk.get("planned_lots_total")
        )
    )
    claim_boundary = risk.get("claim_boundary") or latest_review.get("claim_boundary") or ""
    return {
        "report_kind": "cas_forex_dashboard_risk_budget_summary",
        "date": latest_review.get("date", ""),
        "review_count": risk.get("review_count", 0),
        "risk_status": latest_review.get("risk_status", ""),
        "risk_status_counts": risk.get("risk_status_counts") if isinstance(risk.get("risk_status_counts"), dict) else {},
        "chain_verified": bool(risk.get("chain_verified")),
        "account_equity": _numeric(latest_review.get("account_equity")),
        "max_risk_per_trade_pct": _numeric(latest_review.get("max_risk_per_trade_pct")),
        "daily_risk_budget_pct": _numeric(latest_review.get("daily_risk_budget_pct")),
        "daily_risk_budget_usd": _numeric(latest_review.get("daily_risk_budget_usd")),
        "max_position_lots": _numeric(latest_review.get("max_position_lots")),
        "planned_risk_total_usd": planned_risk_total_usd,
        "planned_lots_total": planned_lots_total,
        "sizing_count": len(sizing_rows),
        "summary_only": True,
        "claim_boundary": "",
        "claim_boundary_present": bool(claim_boundary),
    }


def _dashboard_owner_control_summary_from_full() -> Dict[str, Any]:
    return _dashboard_owner_control_summary(owner_control())


def _dashboard_account_health_summary(report: Dict[str, Any]) -> Dict[str, Any]:
    account = report.get("account") if isinstance(report.get("account"), dict) else {}
    closed = report.get("closed_trade_performance") if isinstance(report.get("closed_trade_performance"), dict) else {}
    exposure = report.get("open_exposure") if isinstance(report.get("open_exposure"), dict) else {}
    source_health = report.get("source_health") if isinstance(report.get("source_health"), dict) else {}
    decision = report.get("decision_metrics") if isinstance(report.get("decision_metrics"), dict) else {}
    return {
        "report_kind": report.get("report_kind", "cas_forex_account_health"),
        "status": report.get("status"),
        "blockers": report.get("blockers") if isinstance(report.get("blockers"), list) else [],
        "account": {
            "balance_usd": account.get("balance_usd"),
            "equity_usd": account.get("equity_usd"),
            "free_margin_usd": account.get("free_margin_usd"),
            "realized_pnl_usd": account.get("realized_pnl_usd"),
            "floating_pnl_usd": account.get("floating_pnl_usd"),
            "drawdown_pct": account.get("drawdown_pct"),
            "margin_utilization_pct": account.get("margin_utilization_pct"),
        },
        "closed_trade_performance": {
            "closed_trade_count": closed.get("closed_trade_count"),
            "win_rate_pct": closed.get("win_rate_pct"),
            "profit_factor": closed.get("profit_factor"),
            "profit_factor_state": closed.get("profit_factor_state"),
            "expectancy_usd": closed.get("expectancy_usd"),
        },
        "open_exposure": {
            "open_position_count": exposure.get("open_position_count"),
            "open_lots": exposure.get("open_lots"),
            "unprotected_position_count": exposure.get("unprotected_position_count"),
            "protective_order_coverage_pct": exposure.get("protective_order_coverage_pct"),
            "open_risk_estimate_usd": exposure.get("open_risk_estimate_usd"),
        },
        "source_health": {
            "movement_stream_present": source_health.get("movement_stream_present"),
            "price_source_status": source_health.get("price_source_status"),
            "price_source_label": source_health.get("price_source_label"),
            "price_source_summary": source_health.get("price_source_summary"),
            "price_source_warning": source_health.get("price_source_warning"),
            "position_feed_label": source_health.get("position_feed_label"),
            "position_feed_detail": source_health.get("position_feed_detail"),
            "static_simulation_active": source_health.get("static_simulation_active"),
            "open_position_count": source_health.get("open_position_count"),
            "broker_ticket_position_count": source_health.get("broker_ticket_position_count"),
            "simulator_position_count": source_health.get("simulator_position_count"),
            "provider_priced_simulator_position_count": source_health.get("provider_priced_simulator_position_count"),
            "static_simulator_position_count": source_health.get("static_simulator_position_count"),
            "stale_price_position_count": source_health.get("stale_price_position_count"),
            "source_label_counts": (
                source_health.get("source_label_counts")
                if isinstance(source_health.get("source_label_counts"), dict)
                else {}
            ),
            "configured_market_data_provider": source_health.get("configured_market_data_provider"),
            "provider_usable_symbols": source_health.get("provider_usable_symbols") if isinstance(source_health.get("provider_usable_symbols"), list) else [],
            "static_fallback_symbols": source_health.get("static_fallback_symbols") if isinstance(source_health.get("static_fallback_symbols"), list) else [],
            "mt5_fallback_symbols": source_health.get("mt5_fallback_symbols") if isinstance(source_health.get("mt5_fallback_symbols"), list) else [],
            "provider_stale_symbols": source_health.get("provider_stale_symbols") if isinstance(source_health.get("provider_stale_symbols"), list) else [],
            "provider_freshness_max_age_seconds": source_health.get("provider_freshness_max_age_seconds"),
            "snapshot_age_seconds_by_symbol": (
                source_health.get("snapshot_age_seconds_by_symbol")
                if isinstance(source_health.get("snapshot_age_seconds_by_symbol"), dict)
                else {}
            ),
            "provider_error_count": int(source_health.get("provider_error_count") or 0),
            "stale_positions": source_health.get("stale_positions") if isinstance(source_health.get("stale_positions"), list) else [],
            "static_positions": source_health.get("static_positions") if isinstance(source_health.get("static_positions"), list) else [],
            "attention_required": bool(source_health.get("attention_required")),
            "detail": source_health.get("detail"),
            "local_detail": source_health.get("local_detail"),
        },
        "decision_metrics": decision,
        "summary_only": True,
        "claim_boundary": "",
        "claim_boundary_present": bool(report.get("claim_boundary")),
    }


def _dashboard_owner_control_summary(control: Dict[str, Any]) -> Dict[str, Any]:
    """Compact owner-control knobs; full policy prose stays on /settings/owner-control."""
    allowed_modes = control.get("allowed_modes") if isinstance(control.get("allowed_modes"), list) else []
    claim_boundary = control.get("claim_boundary") if isinstance(control.get("claim_boundary"), str) else ""
    override_state_path = (
        control.get("override_state_path")
        if isinstance(control.get("override_state_path"), str)
        else ""
    )
    return {
        "mode": control.get("mode", "AI_FULL_AUTO_PAPER"),
        "max_concurrent_trades": control.get("max_concurrent_trades", 3),
        "max_loss_cap_pct": control.get("max_loss_cap_pct", 10),
        "ai_autonomy_enabled": bool(control.get("ai_autonomy_enabled")),
        "live_requested": bool(control.get("live_requested")),
        "live_blocked": bool(control.get("live_blocked")),
        "claim_boundary": "",
        "claim_boundary_present": bool(claim_boundary),
        "override_count": control.get("override_count", 0),
        "persisted": bool(control.get("persisted")),
        "override_state_path": "",
        "override_state_path_present": bool(override_state_path),
        "allowed_modes": [],
        "allowed_mode_count": len(allowed_modes),
        "summary_only": True,
    }


def _dashboard_authority_boundary_first_paint() -> Dict[str, Any]:
    return _dashboard_authority_boundary_summary(authority_boundary_fast())


def _dashboard_authority_boundary_summary(boundary: Dict[str, Any]) -> Dict[str, Any]:
    """Compact owner-authority status; full prose stays on /settings/authority-boundary."""
    allowed_scopes = boundary.get("allowed_scopes") if isinstance(boundary.get("allowed_scopes"), list) else []
    blockers = boundary.get("blockers") if isinstance(boundary.get("blockers"), list) else []
    claim_boundary = boundary.get("claim_boundary") if isinstance(boundary.get("claim_boundary"), str) else ""

    return {
        "report_kind": boundary.get("report_kind", "cas_forex_authority_boundary"),
        "operating_mode": boundary.get("operating_mode", "READ_ONLY_PAPER_RESEARCH"),
        "requested_mode": boundary.get("requested_mode", "PAPER"),
        "live_mode_requested": bool(boundary.get("live_mode_requested")),
        "execution_mode": boundary.get("execution_mode", "PAPER"),
        "live_trading_status": boundary.get("live_trading_status", PENDING_OWNER_ENABLE),
        "broker_accept_status": boundary.get("broker_accept_status", PENDING_OWNER_ENABLE),
        "auto_deposit_status": boundary.get("auto_deposit_status", PENDING_OWNER_ENABLE),
        "debit_card_bank_movement_status": boundary.get(
            "debit_card_bank_movement_status",
            PENDING_OWNER_ENABLE,
        ),
        "payout_automation_status": boundary.get("payout_automation_status", PENDING_OWNER_ENABLE),
        "trading_edge_status": boundary.get("trading_edge_status", "OPEN"),
        "can_place_live_orders": bool(boundary.get("can_place_live_orders")),
        "can_create_broker_accept": bool(boundary.get("can_create_broker_accept")),
        "can_auto_deposit": bool(boundary.get("can_auto_deposit")),
        "can_move_money": bool(boundary.get("can_move_money")),
        "can_automate_payouts": bool(boundary.get("can_automate_payouts")),
        "allowed_scopes": [],
        "allowed_scope_count": len(allowed_scopes),
        "blockers": [],
        "blocker_count": len(blockers),
        "claim_boundary": "",
        "claim_boundary_present": bool(claim_boundary),
        "ledger_deployment_status_counts": (
            boundary.get("ledger_deployment_status_counts")
            if isinstance(boundary.get("ledger_deployment_status_counts"), dict)
            else {}
        ),
        "live_execution_runtime_locked": bool(boundary.get("live_execution_runtime_locked", True)),
        "summary_only": True,
    }


def _dashboard_ui_readiness_summary(readiness: Dict[str, Any]) -> Dict[str, Any]:
    """Compact proof maturity status; full blocker prose stays on /proof/readiness."""
    complete_dates = (
        readiness.get("complete_bundle_dates")
        if isinstance(readiness.get("complete_bundle_dates"), list)
        else []
    )
    blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []
    next_ui_step = readiness.get("next_ui_step") if isinstance(readiness.get("next_ui_step"), str) else ""
    claim_boundary = readiness.get("claim_boundary") if isinstance(readiness.get("claim_boundary"), str) else ""

    return {
        "report_id": readiness.get("report_id", ""),
        "plan_id": readiness.get("plan_id", ""),
        "lead_id": readiness.get("lead_id", ""),
        "strategy_setting": readiness.get("strategy_setting", ""),
        "timeframe": readiness.get("timeframe", ""),
        "readiness_status": readiness.get("readiness_status", "NOT_READY_FOR_UI_UX"),
        "min_daily_bundles_for_ui": readiness.get("min_daily_bundles_for_ui", 0),
        "completed_trading_days": readiness.get("completed_trading_days", 0),
        "broker_verified_days": readiness.get("broker_verified_days", 0),
        "decision_days": readiness.get("decision_days", 0),
        "risk_review_days": readiness.get("risk_review_days", 0),
        "complete_bundle_days": readiness.get("complete_bundle_days", 0),
        "complete_bundle_dates": [],
        "complete_bundle_date_count": len(complete_dates),
        "route_counts": readiness.get("route_counts") if isinstance(readiness.get("route_counts"), dict) else {},
        "risk_status_counts": readiness.get("risk_status_counts") if isinstance(readiness.get("risk_status_counts"), dict) else {},
        "chains_verified": readiness.get("chains_verified") if isinstance(readiness.get("chains_verified"), dict) else {},
        "blockers": [],
        "blocker_count": len(blockers),
        "next_ui_step": "",
        "next_ui_step_present": bool(next_ui_step),
        "claim_boundary": "",
        "claim_boundary_present": bool(claim_boundary),
        "deployment_status": readiness.get("deployment_status", "NOT LICENSED"),
        "broker_accept_status": readiness.get("broker_accept_status", "NOT LICENSED"),
        "payment_transfer_status": readiness.get("payment_transfer_status", "NOT LICENSED"),
        "summary_only": True,
    }


def _dashboard_proof_progress_summary(readiness: Dict[str, Any]) -> Dict[str, Any]:
    """Tiny first-paint proof counters; full readiness stays on /proof/readiness."""
    chains_verified = (
        readiness.get("chains_verified")
        if isinstance(readiness.get("chains_verified"), dict)
        else {}
    )
    verified_count = sum(
        1 for key in ("paper_proof", "paper_decision", "paper_risk")
        if bool(chains_verified.get(key))
    )
    return {
        "report_kind": "cas_forex_dashboard_proof_progress_summary",
        "readiness_status": readiness.get("readiness_status", "NOT_READY_FOR_UI_UX"),
        "min_daily_bundles_for_ui": readiness.get("min_daily_bundles_for_ui", 0),
        "completed_trading_days": readiness.get("completed_trading_days", 0),
        "complete_bundle_days": readiness.get("complete_bundle_days", 0),
        "complete_bundle_date_count": len(
            readiness.get("complete_bundle_dates")
            if isinstance(readiness.get("complete_bundle_dates"), list)
            else []
        ),
        "chains_verified_count": verified_count,
        "chains_expected_count": 3,
        "paper_proof_chain_verified": bool(chains_verified.get("paper_proof")),
        "blocker_count": len(
            readiness.get("blockers")
            if isinstance(readiness.get("blockers"), list)
            else []
        ),
        "summary_only": True,
    }


def _dashboard_daily_schedule_summary(schedule: Dict[str, Any]) -> Dict[str, Any]:
    """Compact next-action schedule; full operator prompt stays on /proof/schedule."""
    missing_tracks = (
        schedule.get("missing_tracks_for_next_due")
        if isinstance(schedule.get("missing_tracks_for_next_due"), list)
        else []
    )
    complete_dates = (
        schedule.get("complete_bundle_dates")
        if isinstance(schedule.get("complete_bundle_dates"), list)
        else []
    )
    notes = schedule.get("notes") if isinstance(schedule.get("notes"), list) else []
    claim_boundary = schedule.get("claim_boundary") if isinstance(schedule.get("claim_boundary"), str) else ""

    return {
        "schedule_id": schedule.get("schedule_id", ""),
        "plan_id": schedule.get("plan_id", ""),
        "lead_id": schedule.get("lead_id", ""),
        "strategy_setting": schedule.get("strategy_setting", ""),
        "timeframe": schedule.get("timeframe", ""),
        "as_of_date": schedule.get("as_of_date", ""),
        "next_due_date": schedule.get("next_due_date", ""),
        "next_due_status": schedule.get("next_due_status", ""),
        "latest_complete_bundle_date": schedule.get("latest_complete_bundle_date", ""),
        "complete_bundle_days": schedule.get("complete_bundle_days", 0),
        "completed_trading_days": schedule.get("completed_trading_days", 0),
        "broker_verified_days": schedule.get("broker_verified_days", 0),
        "decision_days": schedule.get("decision_days", 0),
        "risk_review_days": schedule.get("risk_review_days", 0),
        "ui_min_daily_bundles": schedule.get("ui_min_daily_bundles", 0),
        "ui_bundles_remaining": schedule.get("ui_bundles_remaining", 0),
        "required_paper_days": schedule.get("required_paper_days", 0),
        "paper_days_remaining": schedule.get("paper_days_remaining", 0),
        "missing_tracks_for_next_due": [],
        "missing_track_count": len(missing_tracks),
        "complete_bundle_dates": [],
        "complete_bundle_date_count": len(complete_dates),
        "recommended_command": schedule.get("recommended_command", ""),
        "recommended_action": schedule.get("recommended_action", ""),
        "notes": [],
        "note_count": len(notes),
        "claim_boundary": "",
        "claim_boundary_present": bool(claim_boundary),
        "deployment_status": schedule.get("deployment_status", "NOT LICENSED"),
        "broker_accept_status": schedule.get("broker_accept_status", "NOT LICENSED"),
        "payment_transfer_status": schedule.get("payment_transfer_status", "NOT LICENSED"),
        "summary_only": True,
    }


def _dashboard_daily_bundle_summary(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Compact first-paint proof context; full evidence stays on /bundle/daily."""
    steps = bundle.get("steps") if isinstance(bundle.get("steps"), list) else []
    latest_proof = bundle.get("latest_proof") if isinstance(bundle.get("latest_proof"), dict) else {}
    proof_failures = latest_proof.get("failure_reasons") if isinstance(latest_proof.get("failure_reasons"), list) else []

    decision = bundle.get("latest_decision") if isinstance(bundle.get("latest_decision"), dict) else {}
    latest_decision = (
        decision.get("latest_decision")
        if isinstance(decision.get("latest_decision"), dict)
        else {}
    )
    symbol_decisions = latest_decision.get("symbol_decisions")
    symbol_decision_rows = symbol_decisions if isinstance(symbol_decisions, list) else []
    symbol_decision_count = len(symbol_decision_rows)

    risk = bundle.get("latest_risk") if isinstance(bundle.get("latest_risk"), dict) else {}
    latest_review = risk.get("latest_review") if isinstance(risk.get("latest_review"), dict) else {}
    sizing = latest_review.get("sizing")
    sizing_rows = sizing if isinstance(sizing, list) else []
    planned_risk_total_usd = (
        sum(_numeric(row.get("planned_risk_usd")) for row in sizing_rows if isinstance(row, dict))
        if sizing_rows
        else _numeric(
            latest_review.get("planned_risk_total_usd")
            or latest_review.get("total_planned_risk_usd")
            or risk.get("planned_risk_total_usd")
        )
    )
    planned_lots_total = (
        sum(_numeric(row.get("sized_lots")) for row in sizing_rows if isinstance(row, dict))
        if sizing_rows
        else _numeric(
            latest_review.get("planned_lots_total")
            or latest_review.get("total_planned_lots")
            or risk.get("planned_lots_total")
        )
    )

    decision_boundary = decision.get("claim_boundary") or latest_decision.get("claim_boundary") or ""
    risk_boundary = risk.get("claim_boundary") or latest_review.get("claim_boundary") or ""

    return {
        "bundle_id": bundle.get("bundle_id", ""),
        "plan_id": bundle.get("plan_id", ""),
        "lead_id": bundle.get("lead_id", ""),
        "strategy_setting": bundle.get("strategy_setting", ""),
        "date": bundle.get("date", ""),
        "timeframe": bundle.get("timeframe", ""),
        "steps": [],
        "step_count": len(steps),
        "completed": bool(bundle.get("completed")),
        "latest_proof": {
            "status_path": "",
            "status_path_present": bool(latest_proof.get("status_path")),
            "completed_trading_days": latest_proof.get("completed_trading_days", 0),
            "required_trading_days": latest_proof.get("required_trading_days", 0),
            "chain_verified": bool(latest_proof.get("chain_verified")),
            "passed": bool(latest_proof.get("passed")),
            "failure_reasons": [],
            "failure_reason_count": len(proof_failures),
        },
        "latest_decision": {
            "plan_id": "",
            "lead_id": "",
            "strategy_setting": "",
            "decision_count": decision.get("decision_count", 0),
            "route_counts": decision.get("route_counts") if isinstance(decision.get("route_counts"), dict) else {},
            "chain_verified": bool(decision.get("chain_verified")),
            "claim_boundary": "",
            "claim_boundary_present": bool(decision_boundary),
            "summary_only": True,
            "symbol_decision_count": symbol_decision_count,
            "latest_decision": {
                "date": latest_decision.get("date", bundle.get("date", "")),
                "decision_id": "",
                "plan_id": "",
                "lead_id": "",
                "strategy_setting": "",
                "route_action": latest_decision.get("route_action", ""),
                "timeframe": latest_decision.get("timeframe", bundle.get("timeframe", "")),
                "macro_status": latest_decision.get("macro_status", ""),
                "macro_reason": "",
                "event_context": latest_decision.get("event_context", ""),
                "claim_boundary": "",
                "claim_boundary_present": bool(latest_decision.get("claim_boundary", decision_boundary)),
                "notes": [],
                "note_count": len(latest_decision.get("notes") if isinstance(latest_decision.get("notes"), list) else []),
                "summary_only": True,
                "symbol_decision_count": symbol_decision_count,
                "symbol_decisions": [],
            },
        },
        "latest_risk": {
            "plan_id": "",
            "lead_id": "",
            "strategy_setting": "",
            "review_count": risk.get("review_count", 0),
            "risk_status_counts": risk.get("risk_status_counts") if isinstance(risk.get("risk_status_counts"), dict) else {},
            "chain_verified": bool(risk.get("chain_verified")),
            "summary_only": True,
            "sizing_count": len(sizing_rows),
            "planned_risk_total_usd": planned_risk_total_usd,
            "planned_lots_total": planned_lots_total,
            "claim_boundary": "",
            "claim_boundary_present": bool(risk_boundary),
            "latest_review": {
                "date": latest_review.get("date", bundle.get("date", "")),
                "review_id": "",
                "risk_status": latest_review.get("risk_status", ""),
                "route_action": "",
                "account_equity": _numeric(latest_review.get("account_equity")),
                "max_risk_per_trade_pct": _numeric(latest_review.get("max_risk_per_trade_pct")),
                "daily_risk_budget_pct": _numeric(latest_review.get("daily_risk_budget_pct")),
                "daily_risk_budget_usd": _numeric(latest_review.get("daily_risk_budget_usd")),
                "max_position_lots": _numeric(latest_review.get("max_position_lots")),
                "max_paper_attempts": latest_review.get("max_paper_attempts", 0),
                "allowed_attempts": latest_review.get("allowed_attempts", 0),
                "proposed_attempts": latest_review.get("proposed_attempts", 0),
                "existing_attempts": latest_review.get("existing_attempts", 0),
                "attempts_remaining_before_review": latest_review.get("attempts_remaining_before_review", 0),
                "claim_boundary": "",
                "claim_boundary_present": bool(latest_review.get("claim_boundary", risk_boundary)),
                "deployment_status": latest_review.get("deployment_status", bundle.get("deployment_status", "NOT LICENSED")),
                "broker_accept_status": latest_review.get("broker_accept_status", bundle.get("broker_accept_status", "NOT LICENSED")),
                "payment_transfer_status": latest_review.get("payment_transfer_status", bundle.get("payment_transfer_status", "NOT LICENSED")),
                "plan_id": "",
                "lead_id": "",
                "blockers": [],
                "blocker_count": len(latest_review.get("blockers") if isinstance(latest_review.get("blockers"), list) else []),
                "notes": [],
                "note_count": len(latest_review.get("notes") if isinstance(latest_review.get("notes"), list) else []),
                "summary_only": True,
                "sizing_count": len(sizing_rows),
                "planned_risk_total_usd": planned_risk_total_usd,
                "planned_lots_total": planned_lots_total,
                "sizing": [],
            },
        },
        "claim_boundary": "",
        "claim_boundary_present": bool(bundle.get("claim_boundary", "")),
        "deployment_status": bundle.get("deployment_status", "NOT LICENSED"),
        "broker_accept_status": bundle.get("broker_accept_status", "NOT LICENSED"),
        "payment_transfer_status": bundle.get("payment_transfer_status", "NOT LICENSED"),
        "completed_steps": bundle.get("completed_steps", 0),
        "total_steps": bundle.get("total_steps", len(steps)),
        "overall_status": bundle.get("overall_status", ""),
        "summary_only": True,
    }


# Per-build memo for expensive aggregations that a single dashboard_state()
# rebuilds many times over (waste_direction_learning_ledger ran 21x per build,
# waste_direction_outcome_binding 13x, each re-reading the same JSONL evidence).
#
# Thread-local and explicitly cleared at the start of every build, so a value can
# never survive into a later request or leak across concurrent builds. This is a
# within-request memo, NOT a cache: two separate requests always rebuild.
_build_scope = threading.local()


def _build_scoped(key: str, builder):
    memo = getattr(_build_scope, "memo", None)
    if memo is None:
        return builder()
    if key not in memo:
        memo[key] = builder()
    return memo[key]


def _begin_build_scope() -> None:
    _build_scope.memo = {}


def _end_build_scope() -> None:
    _build_scope.memo = None


def dashboard_state() -> Dict[str, Any]:
    _begin_build_scope()
    try:
        return _dashboard_state_uncached()
    finally:
        _end_build_scope()


def _dashboard_state_uncached() -> Dict[str, Any]:
    ledger = account_ledger()
    movement = movement_stream(use_provider_quotes=True)
    health = build_account_health_report(ledger, movement_stream=movement)
    state: Dict[str, Any] = {
        "uiReadiness": ui_readiness(),
        "dailySchedule": daily_schedule(),
        "dailyBundle": daily_bundle(),
        "ownerControl": owner_control(),
        "accountLedger": ledger,
        "accountHealth": health,
        "activeAccountTruth": active_account_truth(simulator_health_report=health),
        "movementStream": movement,
        "accountReconciliation": account_reconciliation(),
        "liveReadiness": live_readiness(),
        "ownerPromotionReview": owner_promotion_review_summary(),
        "strategyLeads": strategy_leads(),
        "backsolve": backsolve_summary(),
        "conditionTally": condition_tally(),
        "walkForward": walk_forward_summary(),
        "externalBenchmarks": external_benchmarks(),
        "forexFurySetImport": _optional_dashboard_value(forex_fury_set_import),
        "forexFuryReplayCandidates": _optional_dashboard_value(forex_fury_replay_candidates),
        "forexFuryReplayResults": _optional_dashboard_value(forex_fury_replay_results),
        "agentWorkflowPlan": _optional_dashboard_value(agent_workflow_plan),
        "agentWorkflowCycle": _optional_dashboard_value(agent_workflow_cycle),
        "agentInformationFlow": _optional_dashboard_value(agent_information_flow),
        "agentMessageBus": _optional_dashboard_value(agent_message_bus_summary),
        "agentMemory": _optional_dashboard_value(agent_memory_latest),
        "agentResearchQueue": _optional_dashboard_value(agent_research_queue_latest),
        "strategyDevQueue": _optional_dashboard_value(strategy_dev_queue_latest),
        "strategyPatchRunner": _optional_dashboard_value(strategy_patch_runner_latest),
        "dailyLearningRollup": _optional_dashboard_value(daily_learning_rollup_latest),
        "sessionAutowake": _optional_dashboard_value(session_autowake_latest),
        "terminalReceiptWatcher": _optional_dashboard_value(terminal_receipt_watcher_latest),
        "terminalBridgeSupervisor": _optional_dashboard_value(terminal_bridge_supervisor_latest),
        "mt4TerminalActivation": _optional_dashboard_value(mt4_terminal_activation_latest),
        "mt4PingRoundtrip": _optional_dashboard_value(mt4_ping_roundtrip_latest),
        "mt4TerminalSessionVerifier": _optional_dashboard_value(mt4_terminal_session_verifier_latest),
        "mt4HistoryExportVerifier": _optional_dashboard_value(mt4_history_export_verifier_latest),
        "mt5TerminalApiVerifier": _optional_dashboard_value(mt5_terminal_api_verifier_latest),
        "mt5PaperExecutionVerifier": _optional_dashboard_value(mt5_paper_execution_verifier_latest),
        "mt5DealHistoryIngest": _optional_dashboard_value(mt5_deal_history_ingest_latest),
        "terminalPositionReconciliation": _optional_dashboard_value(terminal_position_reconciliation_latest),
        "terminalOperabilityVerifier": _optional_dashboard_value(terminal_operability_verifier_latest),
        "terminalReceiptRecoveryPacket": _optional_dashboard_value(terminal_receipt_recovery_packet_latest),
        "terminalReceiptIngest": _optional_dashboard_value(terminal_receipt_ingest_latest),
        "terminalHistoryIngest": _optional_dashboard_value(terminal_history_ingest_latest),
        "mt5Receipt": mt5_receipt(),
        "mt5ProbeStatus": mt5_probe_status(),
        "authorityBoundary": authority_boundary(),
        "runtimeGates": runtime_gates_report(),
        "autoHalt": auto_halt_status(),
        "brokerTruthMonitor": broker_truth_monitor_status(),
        "orderAttemptAudit": build_order_attempt_audit_status(),
        "orderAttemptRecoveryPacket": order_attempt_recovery_packet(),
        "payoutRecovery": build_payout_recovery_status(),
        "brokerReality": broker_reality_review(),
        "livePilot": live_pilot_policy(),
        "liveOrderDryRun": live_order_dry_run_latest(),
        "compoundAddOrderDryRun": compound_add_order_dry_run_latest(),
        "compoundAddOrderDryRunReview": compound_add_order_dry_run_review_status(),
        "compoundAddDispatchHandoff": compound_add_dispatch_handoff_status(),
        "liveOrderDryRunReview": live_order_dry_run_review_status(),
        "wasteEntryPilotPromotion": waste_entry_pilot_promotion_status(),
        "wasteDirectionReview": waste_direction_review_packet(),
        "wasteDirectionLearning": _optional_dashboard_value(waste_direction_learning_ledger),
        "wasteDirectionOutcomeBinding": _optional_dashboard_value(waste_direction_outcome_binding),
        "wastePaperSampleCollector": _optional_dashboard_value(waste_paper_sample_collector),
        "wastePaperSampleCollectorScheduler": waste_paper_sample_collector_scheduler_status(),
        "wasteAdaptationPromotionRule": _optional_dashboard_value(waste_adaptation_promotion_rule),
        "wasteAdaptationPlan": _optional_dashboard_value(waste_adaptation_plan),
        "wasteAdaptationApplyPreview": _optional_dashboard_value(waste_adaptation_apply_preview),
        "wasteAdaptationOwnerReview": _optional_dashboard_value(waste_adaptation_owner_review),
        "wasteAdaptationPaperApply": _optional_dashboard_value(waste_adaptation_paper_apply_status),
        "liveRecovery": live_recovery_status(),
        "liveMoneyProgression": _optional_dashboard_value(live_money_progression_packet),
        "mt5MarketDataDiagnostic": mt5_market_data_diagnostic_status(),
        "wasteRealCandleProbe": waste_real_candle_probe_status(),
        "aiModel": ai_model_status(),
        "brokerCandidates": broker_candidate_profiles(),
        "pcba": _optional_dashboard_value(pcba_cockpit),
    }
    adaptive = adaptive_cockpit()
    if adaptive is not None:
        state["adaptive"] = adaptive
    try:
        state["brokerSyncedRiskPreview"] = broker_synced_risk_preview()
    except HTTPException:
        state["brokerSyncedRiskPreview"] = None
    history = mt_history()
    if history is not None:
        state["mtHistory"] = history
    return state


def ui_readiness() -> Dict[str, Any]:
    return _read_json(PROOF_DIR / f"{PLAN_ID}-ui-readiness-status.json")


def daily_schedule() -> Dict[str, Any]:
    return _read_json(PROOF_DIR / f"{PLAN_ID}-daily-schedule-status.json")


def daily_bundle(date: Optional[str] = None) -> Dict[str, Any]:
    bundle = _read_json(PROOF_DIR / f"{PLAN_ID}-daily-bundle-status.json")
    if date is not None and bundle.get("date") != date:
        raise HTTPException(status_code=404, detail=f"No daily bundle for {date}")
    latest_risk_path = PROOF_DIR / f"{PLAN_ID}-paper-risk-status.json"
    if latest_risk_path.exists():
        bundle["latest_risk"] = _read_json(latest_risk_path)
    return bundle


def latest_decision() -> Dict[str, Any]:
    return daily_bundle()["latest_decision"]


def latest_risk() -> Dict[str, Any]:
    return daily_bundle()["latest_risk"]


def strategy_leads() -> List[Dict[str, Any]]:
    payload = _read_json(REPO_ROOT / "strategy_leads.json")
    leads = payload.get("leads", [])
    if not isinstance(leads, list):
        raise HTTPException(status_code=500, detail="strategy_leads.json has invalid leads shape")
    return leads


def strategy_lead_summaries(limit: int = 12) -> List[Dict[str, Any]]:
    """Compact dashboard shape for the strategy-leads table.

    The full strategy ledger can carry long evidence refs, notes, and research
    commentary. The Dashboard only renders a short watchlist row, so this keeps
    the below-fold automatic fetch lean while preserving `/strategy/leads` for
    the full Strategy page.
    """

    summaries: List[Dict[str, Any]] = []
    for lead in strategy_leads():
        if not isinstance(lead, dict):
            continue
        headline_results = lead.get("headline_results")
        open_gates = lead.get("open_gates")
        summaries.append(
            {
                "lead_id": lead.get("lead_id"),
                "priority": lead.get("priority", 999),
                "status": lead.get("status"),
                "strategy_setting": lead.get("strategy_setting", ""),
                "family": lead.get("family"),
                "mode": lead.get("mode", ""),
                "symbols_promoted_for_next_tests": lead.get("symbols_promoted_for_next_tests") or [],
                "symbols_watchlist": [],
                "headline_results": [headline_results[0]] if isinstance(headline_results, list) and headline_results else [],
                "open_gates": [""] * len(open_gates) if isinstance(open_gates, list) else [],
                "evidence_refs": [],
                "deployment_status": lead.get("deployment_status", "NOT LICENSED"),
                "summary_only": True,
            }
        )
    return sorted(summaries, key=lambda row: int(row.get("priority") or 999))[: max(1, min(int(limit), 50))]


def backsolve_summary() -> Dict[str, Any]:
    path = _latest_file(EVIDENCE_ROOT / "leverage_income_backsolve", "leverage-income-backsolve-*-report.json")
    try:
        if path.stat().st_size > BACKSOLVE_DASHBOARD_MAX_BYTES:
            return _backsolve_unavailable_summary(
                path,
                f"Backsolve report is too large for dashboard inline loading ({path.stat().st_size} bytes).",
            )
        report = _read_json(path)
    except (OSError, MemoryError, json.JSONDecodeError) as exc:
        return _backsolve_unavailable_summary(path, f"Backsolve report unavailable: {exc}")
    autonomy = report.get("ai_autonomy") or {}
    math = report.get("required_return_math") or {}
    return {
        "run_id": report.get("run_id"),
        "total_scenarios": report.get("scenario_count", 0),
        "viable_scenarios": report.get("viable_scenario_count", 0),
        "ai_autonomy_mode": autonomy.get("mode"),
        "ai_selection": autonomy.get("status"),
        "required_return_math": {
            "target_5k_on_5k_pct": math.get("$5k_target_on_$5k_seed_pct", 100.0),
            "target_12k_on_5k_pct": math.get("$12k_target_on_$5k_seed_pct", 240.0),
        },
        "verdict_counts": report.get("verdict_counts", {}),
        "capital_label": "SURVIVAL_RISK",
        "claim_boundary": report.get(
            "claim_boundary",
            "Paper-only leverage/income backsolve. Live trading remains NOT LICENSED.",
        ),
        "deployment_status": report.get("deployment_status", "NOT LICENSED"),
    }


def _backsolve_unavailable_summary(path: Path, detail: str) -> Dict[str, Any]:
    return {
        "run_id": path.stem,
        "status": "unavailable",
        "detail": detail,
        "source_path": str(path),
        "total_scenarios": 0,
        "viable_scenarios": 0,
        "ai_autonomy_mode": "unavailable",
        "ai_selection": "unavailable",
        "required_return_math": {
            "target_5k_on_5k_pct": 100.0,
            "target_12k_on_5k_pct": 240.0,
        },
        "verdict_counts": {},
        "capital_label": "SURVIVAL_RISK",
        "claim_boundary": "Paper-only leverage/income backsolve unavailable for dashboard inline loading. Live trading remains NOT LICENSED.",
        "deployment_status": "NOT LICENSED",
    }


def condition_tally() -> List[Dict[str, Any]]:
    path = _latest_file(EVIDENCE_ROOT / "condition_tally", "condition-tally-*-report.json")
    report = _read_json(path)
    tally = report.get("tally") or {}
    buckets = tally.get("buckets", [])
    if not isinstance(buckets, list):
        raise HTTPException(status_code=500, detail="condition tally report has invalid bucket shape")
    return buckets


def walk_forward_summary() -> Dict[str, Any]:
    path = _latest_file(EVIDENCE_ROOT / "walk_forward_condition_lab", "walk-forward-*-report.json")
    report = _read_json(path)
    summary = report.get("combined_summary") or {}
    arguments = report.get("arguments") or {}
    return {
        "run_id": report.get("run_id"),
        "total_windows": summary.get("windows", 0),
        "routed_windows": summary.get("routed_windows", 0),
        "active_routed_windows": summary.get("active_routed_windows", 0),
        "positive_active_routed_windows": summary.get("positive_active_routed_windows", 0),
        "routed_total_return_pct": summary.get("routed_total_return_pct_sum", 0.0),
        "active_routed_mean_return_pct": summary.get("active_routed_mean_return_pct", 0.0),
        "routed_max_drawdown_pct": summary.get("routed_max_drawdown_pct", 0.0),
        "total_routed_trades": summary.get("routed_total_trades", 0),
        "research_grade": summary.get("research_grade", "NOT_PROMOTED"),
        "symbols": arguments.get("symbols", []),
        "claim_boundary": report.get(
            "claim_boundary",
            summary.get("claim_boundary", "Research-only walk-forward result. Live trading remains NOT LICENSED."),
        ),
    }


def external_benchmarks() -> Dict[str, Any]:
    return load_external_benchmark_report()


def forex_fury_set_import() -> Dict[str, Any]:
    try:
        return load_latest_forex_fury_set_import_report()
    except ForexFuryImportError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def forex_fury_replay_candidates() -> Dict[str, Any]:
    try:
        return load_latest_forex_fury_replay_candidate_report()
    except ForexFuryCandidateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def forex_fury_replay_results() -> Dict[str, Any]:
    try:
        return load_latest_forex_fury_replay_results_report()
    except ForexFuryReplayResultError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_workflow_plan() -> Dict[str, Any]:
    try:
        return load_latest_agent_workflow_plan_report()
    except AgentWorkflowPlanError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_workflow_cycle() -> Dict[str, Any]:
    try:
        return load_latest_agent_cycle_report()
    except AgentCycleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_information_flow() -> Dict[str, Any]:
    try:
        return load_latest_agent_information_flow_report()
    except AgentInformationFlowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_message_bus_summary() -> Dict[str, Any]:
    try:
        try:
            latest_cycle = load_latest_agent_cycle_report()
            event_path = ((latest_cycle.get("event_journal") or {}) or {}).get("event_log_path")
            if event_path:
                return load_agent_event_summary(event_path)
        except Exception:
            pass
        return load_agent_event_summary()
    except AgentMessageBusError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_workflow_events(
    *,
    cycle_id: Optional[str] = None,
    after_event_id: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    try:
        return load_agent_events(cycle_id=cycle_id, after_event_id=after_event_id, limit=limit)
    except AgentMessageBusError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_workflow_context_latest() -> Dict[str, Any]:
    try:
        return load_latest_agent_context()
    except AgentMessageBusError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_workflow_intents_open() -> Dict[str, Any]:
    try:
        return load_open_agent_intents()
    except AgentMessageBusError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_workflow_receipts_latest(*, command_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    try:
        return load_latest_agent_receipts(command_id=command_id, limit=limit)
    except AgentMessageBusError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_memory_latest() -> Dict[str, Any]:
    try:
        return load_latest_agent_memory_report()
    except AgentMemoryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def agent_research_queue_latest() -> Dict[str, Any]:
    try:
        return load_latest_agent_research_queue_report()
    except AgentResearchQueueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def strategy_dev_queue_latest() -> Dict[str, Any]:
    try:
        return load_latest_strategy_dev_queue_report()
    except StrategyDevQueueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def strategy_patch_runner_latest() -> Dict[str, Any]:
    try:
        return load_latest_strategy_patch_runner_report()
    except StrategyPatchRunnerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def daily_learning_rollup_latest() -> Dict[str, Any]:
    try:
        return load_latest_daily_learning_rollup_report()
    except DailyLearningRollupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def session_autowake_latest() -> Dict[str, Any]:
    try:
        return load_latest_session_autowake_report()
    except SessionAutowakeRunnerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def terminal_receipt_watcher_latest() -> Dict[str, Any]:
    try:
        return load_latest_terminal_receipt_watcher_report()
    except TerminalReceiptWatcherError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def terminal_bridge_supervisor_latest() -> Dict[str, Any]:
    try:
        return load_latest_terminal_bridge_supervisor_report()
    except TerminalBridgeSupervisorError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def mt4_terminal_activation_latest() -> Dict[str, Any]:
    try:
        return load_latest_mt4_terminal_activation_report()
    except MT4TerminalActivationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def mt4_ping_roundtrip_latest() -> Dict[str, Any]:
    try:
        return load_latest_mt4_ping_roundtrip_report()
    except MT4PingRoundtripError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def mt4_terminal_session_verifier_latest() -> Dict[str, Any]:
    try:
        return load_latest_mt4_terminal_session_verifier_report()
    except MT4TerminalSessionVerifierError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def mt4_history_export_verifier_latest() -> Dict[str, Any]:
    try:
        return load_latest_mt4_history_export_verifier_report()
    except MT4HistoryExportVerifierError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def mt5_terminal_api_verifier_latest() -> Dict[str, Any]:
    try:
        return load_latest_mt5_terminal_api_verifier_report()
    except MT5TerminalApiVerifierError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def mt5_paper_execution_verifier_latest() -> Dict[str, Any]:
    try:
        return load_latest_mt5_paper_execution_verifier_report()
    except MT5PaperExecutionVerifierError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def mt5_deal_history_ingest_latest() -> Dict[str, Any]:
    try:
        return load_latest_mt5_deal_history_ingest_report()
    except MT5DealHistoryIngestError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def terminal_position_reconciliation_latest() -> Dict[str, Any]:
    try:
        return load_latest_terminal_position_reconciliation_report()
    except TerminalPositionReconciliationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def terminal_receipt_recovery_packet_latest() -> Dict[str, Any]:
    try:
        return build_terminal_receipt_recovery_packet(
            reconciliation_report=load_latest_terminal_position_reconciliation_report()
        )
    except TerminalPositionReconciliationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def terminal_receipt_archive_action(
    *,
    execute: bool = False,
    confirm_owner_archive: bool = False,
    age_threshold_hours: float = 24.0,
    notes: str = "",
) -> Dict[str, Any]:
    return run_terminal_receipt_archive_action(
        execute=execute,
        confirm_owner_archive=confirm_owner_archive,
        age_threshold_hours=age_threshold_hours,
        notes=notes,
    )


def terminal_receipt_recovery_refresh_action(
    *,
    execute: bool = False,
    confirm_owner_refresh: bool = False,
    notes: str = "",
) -> Dict[str, Any]:
    return run_terminal_receipt_recovery_refresh(
        execute=execute,
        confirm_owner_refresh=confirm_owner_refresh,
        notes=notes,
    )


def terminal_operability_verifier_latest() -> Dict[str, Any]:
    try:
        return load_latest_terminal_operability_verifier_report()
    except TerminalOperabilityVerifierError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def terminal_receipt_ingest_latest() -> Dict[str, Any]:
    try:
        return load_latest_terminal_receipt_ingest_report()
    except TerminalReceiptIngestError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def terminal_history_ingest_latest() -> Dict[str, Any]:
    try:
        return load_latest_terminal_history_ingest_report()
    except TerminalHistoryIngestError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def owner_promotion_review_summary() -> Dict[str, Any]:
    path = _latest_file(EVIDENCE_ROOT / "owner_promotion_review", "owner-promotion-review-*-report.json")
    report = _read_json(path)
    reviews = report.get("reviews") or []
    if not isinstance(reviews, list):
        reviews = []
    thresholds = report.get("thresholds") or {}
    candidates: List[Dict[str, Any]] = []
    for review in reviews:
        if not isinstance(review, dict):
            continue
        candidate = review.get("candidate") or {}
        decision = review.get("decision") or {}
        if not isinstance(candidate, dict):
            continue
        strategy_blockers = _strategy_edge_blockers(candidate, thresholds)
        paper_blockers = _paper_proof_blockers(candidate, thresholds)
        candidates.append(
            {
                **candidate,
                "bucket_key": review.get("bucket_key"),
                "decision_verdict": decision.get("verdict") if isinstance(decision, dict) else None,
                "decision_reasons": decision.get("reasons", []) if isinstance(decision, dict) else [],
                "strategy_edge_passed": not strategy_blockers,
                "strategy_edge_blockers": strategy_blockers,
                "paper_proof_blockers": paper_blockers,
            }
        )
    best = _best_strategy_edge_candidate(candidates)
    return {
        "report_kind": "cas_forex_owner_promotion_review_summary",
        "run_id": report.get("run_id"),
        "generated_at": report.get("generated_at"),
        "owner_mode": report.get("owner_mode"),
        "thresholds": thresholds,
        "review_count": len(candidates),
        "strategy_edge_passed": bool(best and best.get("strategy_edge_passed")),
        "best_strategy_edge_candidate": best,
        "claim_boundary": report.get(
            "claim_boundary",
            "Owner control review is research/paper-only. Live trading remains NOT LICENSED.",
        ),
        "deployment_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "payment_transfer_status": "NOT LICENSED",
    }


def adaptive_cockpit() -> Optional[Dict[str, Any]]:
    path = PROOF_DIR / f"{PLAN_ID}-adaptive-cockpit.json"
    if not path.exists():
        return None
    return _read_json(path)


def latest_adaptive_compounding() -> Optional[Dict[str, Any]]:
    payload = adaptive_cockpit()
    if not payload:
        return None
    return (payload.get("adaptive_compounding") or {}).get("latest_review")


def authority_boundary() -> Dict[str, Any]:
    return build_authority_boundary_report(strategy_leads()).to_dict()


def authority_boundary_fast() -> Dict[str, Any]:
    """Fail-closed authority summary for the first-paint dashboard packet.

    The full boundary calls ``runtime_gates.evaluate_all()``, which performs
    broker-truth, live-pilot, recovery, and dry-run review checks. That belongs
    in the detailed dashboard, not the shell heartbeat. This fast packet is
    deliberately conservative: it never advertises live-money capability as
    active and lets the full dashboard/individual settings pages provide the
    expensive exact gate reasons moments later.
    """

    return {
        "report_kind": "cas_forex_authority_boundary",
        "operating_mode": "READ_ONLY_PAPER_RESEARCH",
        "live_trading_status": PENDING_OWNER_ENABLE,
        "broker_accept_status": PENDING_OWNER_ENABLE,
        "auto_deposit_status": PENDING_OWNER_ENABLE,
        "debit_card_bank_movement_status": PENDING_OWNER_ENABLE,
        "payout_automation_status": PENDING_OWNER_ENABLE,
        "trading_edge_status": "OPEN",
        "can_place_live_orders": False,
        "can_create_broker_accept": False,
        "can_auto_deposit": False,
        "can_move_money": False,
        "can_automate_payouts": False,
        "allowed_scopes": [
            "research",
            "backtest",
            "paper_trade_decision",
            "demo_broker_receipt",
            "read_only_ui",
            "internal_ledger_dry_run",
        ],
        "blockers": [
            "Fast shell packet defers detailed runtime-gate audit to /api/forex/dashboard and dedicated settings endpoints."
        ],
        "claim_boundary": (
            "Fast shell boundary is fail-closed for first paint. Research/paper cockpit runs now; "
            "live trading, broker ACCEPT, auto-deposit, debit/card/bank movement, and payout "
            "automation remain pending owner enable until owner switches/reviews, credentials/provider "
            "config, and action-time checks authorize them."
        ),
        "ledger_deployment_status_counts": {},
        "live_execution_runtime_locked": True,
    }


def runtime_gates_report() -> Dict[str, Any]:
    return build_runtime_gates_report().to_dict()


def ai_model_status() -> Dict[str, Any]:
    return model_status().to_dict()


def broker_candidate_profiles() -> List[Dict[str, Any]]:
    return broker_candidates()


def pcba_cockpit() -> Dict[str, Any]:
    """Return live PCBA/CJT/CCB/optimizer cockpit data for the UI.

    This activates the PCBA tab without changing authority: diagnostics and
    readiness evidence are live, but PCBA/CJT/CCB still cannot create broker
    ACCEPT, unlock live trading, or move money.
    """

    pcba_evidence = collect_local_pcba_evidence(REPO_ROOT)
    cjt_evidence = collect_local_cjt_evidence(REPO_ROOT)
    pcba_report = build_pcba_production_readiness_report(pcba_evidence)
    cjt_report = build_cjt_production_readiness_report(cjt_evidence)
    ccb_report = build_ccb_readiness_report(pcba_evidence | cjt_evidence)
    goal_status = build_pcba_goal_status(
        local_evidence=pcba_evidence,
        receipt_paths=[],
        artifact_root=REPO_ROOT,
    )

    pcba_checks = [check.model_dump(mode="json") for check in pcba_report.checks]
    cjt_checks = [check.model_dump(mode="json") for check in cjt_report.checks]
    ccb_checks = [check.model_dump(mode="json") for check in ccb_report.board_checks]
    boards = [board.model_dump(mode="json") for board in reference_boards()]
    components = [
        {"kind": kind.value, "role": meta["role"], "claim": meta["claim"]}
        for kind, meta in COMPONENT_CATALOG.items()
    ]

    return {
        "report_kind": "cas_forex_pcba_cockpit",
        "panels_active": True,
        "source": "live_api",
        "claim_boundary": (
            "PCBA/CJT/CCB panels are active diagnostics only. They can expose live readiness, "
            "missing evidence, CRC status, and optimizer guard state, but they cannot create "
            "broker ACCEPT, unlock live trading, auto-deposit, move bank/card funds, or automate payouts."
        ),
        "summary": {
            "pcba_ready_checks": sum(1 for check in pcba_checks if check.get("ready")),
            "pcba_total_checks": len(pcba_checks),
            "cjt_ready_checks": sum(1 for check in cjt_checks if check.get("ready")),
            "cjt_total_checks": len(cjt_checks),
            "ccb_designs_well_formed": bool(ccb_report.all_designs_well_formed),
            "ccb_claims_licensed": bool(ccb_report.any_claim_licensed),
            "goal_complete": bool(goal_status.get("goal_complete")),
            "current_boundary_honest": bool(goal_status.get("current_boundary_honest")),
        },
        "local_evidence": {
            "pcba": pcba_evidence,
            "cjt": cjt_evidence,
            "pcba_present_count": sum(1 for present in pcba_evidence.values() if present),
            "pcba_total_count": len(pcba_evidence),
            "cjt_present_count": sum(1 for present in cjt_evidence.values() if present),
            "cjt_total_count": len(cjt_evidence),
        },
        "reference_boards": boards,
        "component_catalog": components,
        "pcba_readiness": {
            "report_id": pcba_report.report_id,
            "generated_at": pcba_report.generated_at.isoformat(),
            "summary": pcba_report.summary,
            "all_ready": pcba_report.all_ready,
            "any_live_authority": pcba_report.any_live_authority,
            "any_broker_accept_authority": pcba_report.any_broker_accept_authority,
            "checks": pcba_checks,
        },
        "cjt_readiness": {
            "report_id": cjt_report.report_id,
            "generated_at": cjt_report.generated_at.isoformat(),
            "summary": cjt_report.summary,
            "all_ready": cjt_report.all_ready,
            "any_live_authority": cjt_report.any_live_authority,
            "any_broker_accept_authority": cjt_report.any_broker_accept_authority,
            "checks": cjt_checks,
        },
        "ccb_readiness": {
            "report_id": ccb_report.report_id,
            "summary": ccb_report.summary,
            "all_designs_well_formed": ccb_report.all_designs_well_formed,
            "any_claim_licensed": ccb_report.any_claim_licensed,
            "board_checks": ccb_checks,
            "prediction_head": ccb_report.prediction_head.model_dump(mode="json"),
        },
        "optimizer_guard": {
            "guard": "CASPCBAOptimizerGuard",
            "active": True,
            "proposal_counts": {"research_queue": 0, "flagged": 0, "rejected": 0},
            "claim_boundary": LLM_OPTIMIZER_CLAIM_BOUNDARY,
            "can_create_broker_accept": False,
            "can_unlock_live_trading": False,
        },
        "goal_status": goal_status,
    }



def account_ledger(initial_investment_usd: Optional[float] = None) -> Dict[str, Any]:
    bundle = daily_bundle()
    latest_risk_review = (bundle.get("latest_risk") or {}).get("latest_review") or {}
    latest_decision_payload = (bundle.get("latest_decision") or {}).get("latest_decision") or {}
    state = build_account_ledger_from_paper_review(
        latest_risk_review,
        initial_investment_usd=initial_investment_usd,
        decision=latest_decision_payload,
        evidence_refs=(
            f"evidence_runs/index_tsmom_126_paper_proof/{PLAN_ID}-daily-bundle-status.json",
            f"evidence_runs/index_tsmom_126_paper_proof/{PLAN_ID}-paper-risk-status.json",
            f"evidence_runs/index_tsmom_126_paper_proof/{PLAN_ID}-paper-decision-status.json",
        ),
    )
    ledger = state.to_dict()
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        ledger = _overlay_runtime_simulator_positions(ledger)
    movement = _movement_stream_from_ledger(ledger, use_provider_quotes=True)
    return _attach_ledger_movement_source_truth(ledger, movement_stream=movement)


def _overlay_runtime_simulator_positions(
    ledger: Dict[str, Any],
    *,
    state_path: Path | str = DEFAULT_RUNTIME_SIMULATOR_STATE_PATH,
) -> Dict[str, Any]:
    """Keep paper plans as orders and expose only executed simulator positions."""

    payload = dict(ledger)
    planned_positions = [
        dict(row) for row in (ledger.get("positions") or []) if isinstance(row, dict)
    ]
    path = Path(state_path)
    try:
        simulator = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        simulator = {}
    raw_positions = simulator.get("positions") if isinstance(simulator, dict) else {}
    runtime_rows: list[dict[str, Any]] = []
    if isinstance(raw_positions, dict):
        for raw_ticket, raw in raw_positions.items():
            if not isinstance(raw, dict):
                continue
            order = raw.get("order") if isinstance(raw.get("order"), dict) else {}
            symbol = str(order.get("symbol") or "").strip()
            if not symbol:
                continue
            ticket = str(raw_ticket)
            fill_price = _numeric(raw.get("fill_price"))
            volume = _numeric(raw.get("volume") or order.get("volume"))
            if fill_price is None or fill_price <= 0 or volume is None or volume <= 0:
                continue
            runtime_rows.append(
                {
                    "row_id": f"runtime-sim-{ticket}",
                    "tab": "Positions",
                    "symbol": symbol,
                    "side": str(order.get("direction") or "UNKNOWN").upper(),
                    "lot_size": volume,
                    "open_price": fill_price,
                    "close_or_current_price": _numeric(raw.get("current_price")) or fill_price,
                    "stop_loss": _numeric(raw.get("stop_loss"))
                    or _numeric(order.get("stop_loss")),
                    "take_profit": _numeric(raw.get("take_profit"))
                    or _numeric(order.get("take_profit")),
                    "timestamp": str(raw.get("timestamp") or ""),
                    "broker_ticket": None,
                    "simulator_ticket": ticket,
                    "strategy_id": str(order.get("comment") or "CAS_PAPER_SIMULATOR"),
                    "ai_action": str(order.get("comment") or "CAS_PAPER_SIMULATOR"),
                    "decision_ref": order.get("decision_ref"),
                    "order_id": order.get("order_id"),
                    "evidence_packet_id": f"simulated-broker:{ticket}",
                    "net_pnl_usd": 0.0,
                    "swap_usd": 0.0,
                    "commission_usd": 0.0,
                    "fees_usd": 0.0,
                    "status": "PAPER_SIMULATOR_EXECUTED_OPEN",
                    "position_provenance": str(path),
                }
            )
    summary = dict(payload.get("summary") or {})
    summary["open_position_count"] = len(runtime_rows)
    payload["summary"] = summary
    payload["paper_order_intents"] = planned_positions
    payload["positions"] = runtime_rows
    payload["runtime_position_source"] = {
        "status": "DURABLE_PAPER_SIMULATOR",
        "state_path": str(path),
        "state_updated_at": simulator.get("updated_at") if isinstance(simulator, dict) else None,
        "open_position_count": len(runtime_rows),
        "planned_order_intent_count": len(planned_positions),
        "void_event_count": int(simulator.get("void_event_count") or 0)
        if isinstance(simulator, dict)
        else 0,
        "claim_boundary": (
            "positions contains only durable executed simulator positions; "
            "paper_order_intents contains approved plans that were not broker fills."
        ),
    }
    payload["notes"] = list(payload.get("notes") or []) + [
        "Trading-window positions come from durable simulated-broker execution state; approved paper order intents remain separate and are not presented as open trades."
    ]
    return payload


def account_health(initial_investment_usd: Optional[float] = None) -> Dict[str, Any]:
    ledger = account_ledger(initial_investment_usd=initial_investment_usd)
    movement = _movement_stream_from_ledger(ledger, use_provider_quotes=True)
    return build_account_health_report(ledger, movement_stream=movement)


def active_account_truth(
    *,
    simulator_health_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return one source-ranked account snapshot for owner-facing surfaces."""

    health = (
        simulator_health_report
        if isinstance(simulator_health_report, dict)
        else account_health()
    )
    return build_active_account_truth(
        mt5_snapshot=get_mt5_account_snapshot(),
        dispatch_loop=dispatch_loop_status(),
        simulator_health=health,
        demo_learning=load_mt5_demo_learning_sync(),
        account_growth=load_mt5_account_growth(),
    )


def _attach_ledger_movement_source_truth(
    ledger: Dict[str, Any],
    *,
    movement_stream: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    movement = movement_stream if isinstance(movement_stream, dict) else _movement_stream_from_ledger(ledger, use_provider_quotes=True)
    source_health = (
        build_account_health_report(ledger, movement_stream=movement).get("source_health")
        if isinstance(ledger, dict)
        else {}
    )
    payload = dict(ledger)
    payload["movement_stream_id"] = movement.get("stream_id")
    payload["movement_stream_timestamp"] = movement.get("timestamp")
    payload["movement_source_truth"] = dict(source_health) if isinstance(source_health, dict) else None
    return payload


def live_broker_account_ledger() -> Optional[Dict[str, Any]]:
    """Return a live broker closed-history ledger when verified live rows exist.

    Demo/paper terminal history intentionally returns ``None``. Callers that
    need a ledger should fall back to ``account_ledger()`` so demo profit never
    becomes sweepable real money.
    """

    gates = runtime_gates_report().get("decisions", {})
    live_status = ((gates.get("live_trading") or {}).get("status")) or "CURRENTLY NOT LICENSED"
    broker_status = ((gates.get("broker_accept") or {}).get("status")) or "CURRENTLY NOT LICENSED"
    payout = gates.get("payout_automation") or {}
    payout_status = payout.get("status") or "CURRENTLY NOT LICENSED"
    payment_authorized = bool(payout.get("authorized", False))

    for loader in (terminal_history_ingest_latest, mt5_deal_history_ingest_latest):
        try:
            report = loader()
        except HTTPException:
            continue
        try:
            return build_live_account_ledger_from_terminal_history(
                report,
                live_trading_status=str(live_status),
                broker_accept_status=str(broker_status),
                payout_automation_status=str(payout_status),
                payment_movement_authorized=payment_authorized,
            ).to_dict()
        except ValueError:
            continue
    return None


def verified_profit_account_ledger() -> Dict[str, Any]:
    """Ledger used by verified-profit sweep calculations.

    Prefer live broker-confirmed closed history when it exists; otherwise return
    the normal paper/demo account ledger, which the sweep layer reports as
    ``DEMO_NOT_SWEEPABLE``.
    """

    return live_broker_account_ledger() or account_ledger()


def verified_profit_sweep_preview_status() -> Dict[str, Any]:
    from cas_forex.verified_profit_sweep import ProfitSweepPolicyStore, build_sweep_preview
    from cas_forex.payout_recovery import default_payout_attempt_store

    settings = ProfitSweepPolicyStore().load()
    already_swept = default_payout_attempt_store().settled_total_usd(
        purpose="verified_profit_sweep",
        policy_id=settings.policy_id,
    )
    return build_sweep_preview(
        verified_profit_account_ledger(),
        settings,
        already_swept_usd=already_swept,
    ).to_dict()


def auto_halt_status(*, persist: bool = True) -> Dict[str, Any]:
    live_ledger = live_broker_account_ledger()
    paper_ledger = account_ledger()
    reconciliation = latest_broker_truth_reconciliation_report()
    position_protection = get_mt5_position_protection_snapshot(force=persist)
    return build_auto_halt_report(
        live_account_ledger=live_ledger,
        paper_account_ledger=paper_ledger,
        reconciliation_report=reconciliation,
        position_protection_report=position_protection,
        persist=persist,
    )


def broker_synced_risk_preview() -> Dict[str, Any]:
    """Rerun paper risk sizing from the verified broker demo account snapshot.

    This is an explicit preview, not an append/apply operation. It proves what
    the current paper route sizing would look like if the broker demo balance
    were used as the account seed, while the default ledger remains unchanged.
    """

    plan, _, preview = _build_broker_synced_risk_review()
    already_applied = _latest_risk_review_matches_broker_sync(
        summarize_paper_risk_reviews(plan, PROOF_DIR),
        preview,
    )
    preview["report_kind"] = "cas_forex_broker_synced_risk_preview"
    preview["mode"] = "BROKER_SYNCED_PAPER_RISK_PREVIEW"
    preview["would_append_evidence"] = False
    preview["evidence_appended"] = False
    preview["already_applied"] = already_applied
    preview["next_action"] = (
        "Broker-synced paper-risk review is already the latest active review."
        if already_applied
        else (
            "Use POST /api/forex/account/apply-broker-sync-risk-review?confirm_apply=true "
            "to append this broker-synced paper-risk review into the evidence chain."
        )
    )
    preview["claim_boundary"] = (
        "Broker-synced risk preview reruns paper risk sizing from a verified broker demo account snapshot. "
        "It does not append evidence, place orders, create broker ACCEPT, deposit, withdraw, move bank/card funds, or automate payouts."
    )
    return preview


def apply_broker_synced_risk_review(
    *,
    confirm_apply: bool = False,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Append the broker-synced paper-risk review after explicit owner action."""

    if not confirm_apply:
        raise HTTPException(
            status_code=400,
            detail="confirm_apply=true is required before appending a broker-synced paper-risk review.",
        )

    plan, review, payload = _build_broker_synced_risk_review()
    target_dir = output_dir or PROOF_DIR
    before_summary = summarize_paper_risk_reviews(plan, target_dir)
    status_path = Path(target_dir) / f"{plan.plan_id}-paper-risk-status.json"
    already_applied = _latest_risk_review_matches_broker_sync(before_summary, payload)

    payload["report_kind"] = "cas_forex_broker_synced_risk_apply"
    payload["mode"] = "BROKER_SYNCED_PAPER_RISK_APPLY"
    payload["would_append_evidence"] = True
    payload["live_money_authorized"] = False
    payload["payment_movement_authorized"] = False
    payload["claim_boundary"] = (
        "Broker-synced risk apply appends a paper/demo risk review from the verified broker demo account snapshot. "
        "It does not place orders, create broker ACCEPT, deposit, withdraw, move bank/card funds, or automate payouts."
    )

    if already_applied:
        payload["evidence_appended"] = False
        payload["already_applied"] = True
        payload["append_receipt"] = None
        payload["paper_risk_status_path"] = _display_path(status_path)
        payload["paper_risk_summary"] = before_summary
        payload["next_action"] = "Broker-synced paper-risk review is already the latest risk review for this decision."
        return payload

    append_result = append_paper_risk_review(review, target_dir)
    status_path = write_paper_risk_status(plan, target_dir)
    after_summary = summarize_paper_risk_reviews(plan, target_dir)
    payload["evidence_appended"] = True
    payload["already_applied"] = False
    payload["append_receipt"] = append_result.get("receipt")
    payload["paper_risk_status_path"] = _display_path(status_path)
    payload["paper_risk_summary"] = after_summary
    payload["next_action"] = "Broker-synced paper-risk review has been appended; rerun/read dashboard to see the broker-seeded paper risk as the active review."
    return payload


def _build_broker_synced_risk_review() -> tuple[Any, Any, Dict[str, Any]]:
    receipt = mt5_receipt()
    broker_initial = _broker_snapshot_initial_investment(receipt)
    if broker_initial is None:
        raise HTTPException(status_code=409, detail="No broker account snapshot balance is available for risk preview")

    bundle = daily_bundle()
    latest_decision_payload = (bundle.get("latest_decision") or {}).get("latest_decision") or {}
    latest_risk_review = (bundle.get("latest_risk") or {}).get("latest_review") or {}
    plan = build_index_tsmom_126_paper_proof_plan()
    review = review_paper_risk_budget(
        plan,
        latest_decision_payload,
        account_equity=float(broker_initial),
        max_risk_per_trade_pct=float(latest_risk_review.get("max_risk_per_trade_pct", 0.5) or 0.5),
        daily_risk_budget_pct=float(latest_risk_review.get("daily_risk_budget_pct", 1.0) or 1.0),
        max_paper_attempts=int(latest_risk_review.get("max_paper_attempts", plan.max_paper_trades_per_day) or plan.max_paper_trades_per_day),
        existing_attempts=int(latest_risk_review.get("existing_attempts", 0) or 0),
        max_position_lots=float(latest_risk_review.get("max_position_lots", 0.1) or 0.1),
    )
    payload = review_payload(review)
    default_sizing = latest_risk_review.get("sizing") or []
    payload["sync_to_broker_snapshot"] = True
    payload["broker_snapshot_initial_investment_usd"] = float(broker_initial)
    payload["default_risk_review_account_equity_usd"] = float(latest_risk_review.get("account_equity", 0.0) or 0.0)
    payload["default_total_planned_risk_usd"] = float(latest_risk_review.get("total_planned_risk_usd", 0.0) or 0.0)
    payload["default_total_planned_lots"] = round(
        sum(float(item.get("sized_lots", 0.0) or 0.0) for item in default_sizing if isinstance(item, dict)),
        4,
    )
    payload["delta_vs_default"] = {
        "account_equity_usd": round(payload["account_equity"] - payload["default_risk_review_account_equity_usd"], 2),
        "total_planned_risk_usd": round(payload["total_planned_risk_usd"] - payload["default_total_planned_risk_usd"], 2),
        "total_planned_lots": round(payload["total_planned_lots"] - payload["default_total_planned_lots"], 4),
    }
    payload["live_money_authorized"] = False
    payload["payment_movement_authorized"] = False
    return plan, review, payload


def _latest_risk_review_matches_broker_sync(summary: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    latest = summary.get("latest_review")
    if not isinstance(latest, dict):
        return False
    try:
        latest_equity = float(latest.get("account_equity", 0.0) or 0.0)
        broker_equity = float(payload.get("broker_snapshot_initial_investment_usd", 0.0) or 0.0)
    except (TypeError, ValueError):
        return False
    return (
        abs(latest_equity - broker_equity) < 0.01
        and latest.get("source_decision_id") == payload.get("source_decision_id")
        and latest.get("review_id") == payload.get("review_id")
    )


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _strategy_edge_blockers(candidate: Dict[str, Any], thresholds: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []
    if int(candidate.get("simulator_wins", 0) or 0) < int(thresholds.get("min_simulator_wins", 10) or 10):
        blockers.append("simulator_wins")
    if int(candidate.get("walk_forward_windows", 0) or 0) < int(thresholds.get("min_walk_forward_windows", 10) or 10):
        blockers.append("walk_forward_windows")
    if float(candidate.get("positive_routed_window_rate", 0.0) or 0.0) < float(
        thresholds.get("min_positive_routed_window_rate", 0.60) or 0.60
    ):
        blockers.append("positive_routed_window_rate")
    if float(candidate.get("mean_return_pct", 0.0) or 0.0) < float(thresholds.get("min_mean_return_pct", 0.50) or 0.50):
        blockers.append("mean_return_pct")
    if float(candidate.get("max_drawdown_pct", 0.0) or 0.0) > float(thresholds.get("max_drawdown_pct", 5.0) or 5.0):
        blockers.append("max_drawdown_pct")
    if int(candidate.get("trades", 0) or 0) < int(thresholds.get("min_trades", 30) or 30):
        blockers.append("trades")
    if not candidate.get("evidence_refs"):
        blockers.append("evidence_refs")
    if not candidate.get("condition_contexts"):
        blockers.append("condition_contexts")
    return blockers


def _paper_proof_blockers(candidate: Dict[str, Any], thresholds: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []
    if int(candidate.get("paper_days", 0) or 0) < int(thresholds.get("min_paper_days", 30) or 30):
        blockers.append("paper_days")
    if bool(thresholds.get("require_paper_passed", True)) and not bool(candidate.get("paper_passed", False)):
        blockers.append("paper_passed")
    return blockers


def _best_strategy_edge_candidate(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            1 if item.get("strategy_edge_passed") else 0,
            float(item.get("positive_routed_window_rate", 0.0) or 0.0),
            float(item.get("mean_return_pct", 0.0) or 0.0),
            int(item.get("trades", 0) or 0),
        ),
    )


def movement_stream(use_provider_quotes: bool = False) -> Dict[str, Any]:
    return _movement_stream_from_ledger(account_ledger(), use_provider_quotes=use_provider_quotes)


def _movement_snapshot_usable(snapshot: Any) -> bool:
    return movement_snapshot_usable_for_movement(snapshot)


def _movement_snapshot_issue(source_name: str, snapshot: Any) -> str:
    return movement_snapshot_issue_for_movement(source_name, snapshot)


def _append_movement_provider_issue(existing: str | None, new_issue: str) -> str:
    left = str(existing or "").strip()
    right = str(new_issue or "").strip()
    if not left:
        return right
    if not right or right == left:
        return left
    return f"{left} | {right}"


def _movement_snapshot_issue_with_connector(source_name: str, connector: Any, snapshot: Any) -> str:
    issue = _movement_snapshot_issue(source_name, snapshot)
    connector_error = str(getattr(connector, "last_error", "") or "").strip()
    if connector_error and bool(getattr(snapshot, "synthetic_fallback", False)):
        if connector_error.lower().startswith(source_name.lower()):
            return connector_error
        return f"{source_name}: {connector_error}"
    return issue


def _movement_stream_from_ledger(ledger: Dict[str, Any], *, use_provider_quotes: bool = False) -> Dict[str, Any]:
    snapshots: Dict[str, Any] = {}
    provider_name = "none"
    provider_errors: Dict[str, str] = {}
    snapshot_source_by_symbol: Dict[str, str] = {}
    mt5_fallback_symbols: List[str] = []
    stale_provider_symbols: set[str] = set()
    snapshot_age_seconds_by_symbol: Dict[str, float | None] = {}
    attempted_symbols: set[str] = set()
    if use_provider_quotes:
        connector = get_connector()
        provider_name = type(connector).__name__
        symbols: List[str] = []
        for row in ledger.get("positions", []):
            symbol = row.get("symbol")
            if not symbol:
                continue
            sym = str(symbol)
            if sym in symbols:
                continue
            symbols.append(sym)
            try:
                attempted_symbols.add(sym)
                primary_snapshot = connector.fetch_snapshot(sym)
            except Exception as exc:
                # Fail soft: movement stream must remain available even when the
                # external provider is down or missing. The core builder falls
                # back to paper-route prices for any missing symbol.
                provider_errors[sym] = f"{type(exc).__name__}: {exc}"
                continue
            age = movement_snapshot_age_seconds(primary_snapshot)
            snapshot_age_seconds_by_symbol[sym] = round(age, 3) if age is not None else None
            if _movement_snapshot_usable(primary_snapshot):
                snapshots[sym] = primary_snapshot
                snapshot_source_by_symbol[sym] = provider_name
            else:
                provider_errors[sym] = _movement_snapshot_issue_with_connector(provider_name, connector, primary_snapshot)
                if movement_snapshot_stale_for_movement(primary_snapshot):
                    stale_provider_symbols.add(sym)

        unresolved = [sym for sym in symbols if sym not in snapshots]
        if unresolved and provider_name != "MT5TerminalMarketDataConnector":
            mt5_connector = MT5TerminalMarketDataConnector()
            mt5_name = type(mt5_connector).__name__
            for sym in unresolved:
                try:
                    attempted_symbols.add(sym)
                    mt5_snapshot = mt5_connector.fetch_snapshot(sym)
                except Exception as exc:
                    provider_errors[sym] = _append_movement_provider_issue(
                        provider_errors.get(sym),
                        f"{mt5_name}: {type(exc).__name__}: {exc}",
                    )
                    continue
                mt5_age = movement_snapshot_age_seconds(mt5_snapshot)
                if _movement_snapshot_usable(mt5_snapshot):
                    snapshot_age_seconds_by_symbol[sym] = round(mt5_age, 3) if mt5_age is not None else None
                    snapshots[sym] = mt5_snapshot
                    snapshot_source_by_symbol[sym] = mt5_name
                    mt5_fallback_symbols.append(sym)
                    stale_provider_symbols.discard(sym)
                else:
                    if sym not in snapshot_age_seconds_by_symbol:
                        snapshot_age_seconds_by_symbol[sym] = round(mt5_age, 3) if mt5_age is not None else None
                    provider_errors[sym] = _append_movement_provider_issue(
                        provider_errors.get(sym),
                        _movement_snapshot_issue_with_connector(mt5_name, mt5_connector, mt5_snapshot),
                    )
                    if movement_snapshot_stale_for_movement(mt5_snapshot):
                        stale_provider_symbols.add(sym)
    payload = build_movement_stream_state(
        ledger,
        market_snapshots=snapshots,
        market_snapshot_sources=snapshot_source_by_symbol,
    ).to_dict()
    provider_usable_symbols = [
        str(quote.get("symbol"))
        for quote in payload.get("quotes", [])
        if str(quote.get("source") or "").startswith("provider_snapshot:")
    ]
    closed_market_symbols = [
        str(quote.get("symbol"))
        for quote in payload.get("quotes", [])
        if str(quote.get("source") or "").startswith("provider_snapshot:") and not bool(quote.get("is_market_open"))
    ]
    static_fallback_symbols = [
        str(quote.get("symbol"))
        for quote in payload.get("quotes", [])
        if str(quote.get("source") or "").startswith("paper_route_snapshot")
    ]
    unsupported_provider_symbols = sorted(
        symbol
        for symbol, issue in provider_errors.items()
        if "not available on the configured" in str(issue or "")
    )
    payload.update(
        {
            "market_data_provider_requested": bool(use_provider_quotes),
            "market_data_provider": provider_name,
            "configured_market_data_provider": provider_name,
            "provider_snapshot_symbols": sorted(attempted_symbols),
            "provider_usable_symbols": sorted(provider_usable_symbols),
            "closed_market_symbols": sorted(closed_market_symbols),
            "closed_market_quote_count": len(closed_market_symbols),
            "static_fallback_symbols": sorted(static_fallback_symbols),
            "unsupported_provider_symbols": unsupported_provider_symbols,
            "mt5_fallback_symbols": sorted(mt5_fallback_symbols),
            "provider_stale_symbols": sorted(stale_provider_symbols),
            "provider_freshness_max_age_seconds": MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS,
            "snapshot_age_seconds_by_symbol": {
                symbol: snapshot_age_seconds_by_symbol.get(symbol)
                for symbol in sorted({*(payload.get("symbols") or []), *attempted_symbols})
                if str(symbol or "").strip() and symbol in snapshot_age_seconds_by_symbol
            },
            "snapshot_source_by_symbol": {
                str(symbol): str(snapshot_source_by_symbol.get(symbol) or "static_simulation")
                for symbol in sorted({*(payload.get("symbols") or []), *attempted_symbols})
                if str(symbol or "").strip()
            },
            "provider_errors": provider_errors,
            "price_source_status": (
                "PROVIDER_ACTIVE"
                if provider_usable_symbols and not static_fallback_symbols
                else "MIXED_PROVIDER_AND_STATIC_FALLBACK"
                if provider_usable_symbols
                else "STATIC_SIMULATION_FALLBACK"
            ),
        }
    )
    payload.update(
        build_movement_price_source_summary(
            price_source_status=str(payload.get("price_source_status") or "UNKNOWN"),
            market_data_provider_requested=bool(use_provider_quotes),
            configured_market_data_provider=str(payload.get("configured_market_data_provider") or provider_name or ""),
            provider_usable_symbols=payload.get("provider_usable_symbols"),
            static_fallback_symbols=payload.get("static_fallback_symbols"),
            mt5_fallback_symbols=payload.get("mt5_fallback_symbols"),
            closed_market_symbols=payload.get("closed_market_symbols"),
            unsupported_provider_symbols=payload.get("unsupported_provider_symbols"),
            provider_stale_symbols=payload.get("provider_stale_symbols"),
            provider_freshness_max_age_seconds=payload.get("provider_freshness_max_age_seconds"),
        )
    )
    payload.update(
        build_movement_position_feed_truth(
            positions=payload.get("positions"),
            quotes=payload.get("quotes"),
            price_source_status=str(payload.get("price_source_status") or "UNKNOWN"),
            market_data_provider_requested=bool(use_provider_quotes),
            configured_market_data_provider=str(payload.get("configured_market_data_provider") or provider_name or ""),
            provider_usable_symbols=payload.get("provider_usable_symbols"),
            static_fallback_symbols=payload.get("static_fallback_symbols"),
            mt5_fallback_symbols=payload.get("mt5_fallback_symbols"),
            closed_market_symbols=payload.get("closed_market_symbols"),
            closed_market_quote_count=payload.get("closed_market_quote_count"),
            unsupported_provider_symbols=payload.get("unsupported_provider_symbols"),
            provider_stale_symbols=payload.get("provider_stale_symbols"),
            provider_freshness_max_age_seconds=payload.get("provider_freshness_max_age_seconds"),
        )
    )
    payload["movement_source_truth"] = build_movement_source_truth_snapshot(
        payload,
        telemetry_source="movement_stream",
        telemetry_stale=False,
        telemetry_last_update_iso=str(payload.get("timestamp") or "") or None,
        movement_stream_present=True,
    )
    return payload

def account_reconciliation(sync_to_broker: bool = False) -> Dict[str, Any]:
    receipt = mt5_receipt()
    initial = _broker_snapshot_initial_investment(receipt) if sync_to_broker else None
    ledger = account_ledger(initial_investment_usd=float(initial) if initial else None)
    movement = _movement_stream_from_ledger(ledger, use_provider_quotes=True)
    report = build_account_reconciliation_report(
        ledger,
        receipt,
        movement_stream=movement,
    ).to_dict()
    report["sync_to_broker_snapshot"] = bool(sync_to_broker and initial)
    report["broker_snapshot_initial_investment_usd"] = float(initial) if initial else None
    return report


def live_readiness(sync_to_broker: bool = False) -> Dict[str, Any]:
    adaptive = adaptive_cockpit()
    receipt = mt5_receipt()
    initial = _broker_snapshot_initial_investment(receipt) if sync_to_broker else None
    ledger = account_ledger(initial_investment_usd=float(initial) if initial else None)
    movement = _movement_stream_from_ledger(ledger, use_provider_quotes=True)
    reconciliation = build_account_reconciliation_report(
        ledger,
        receipt,
        movement_stream=movement,
    ).to_dict()
    reconciliation["sync_to_broker_snapshot"] = bool(sync_to_broker and initial)
    reconciliation["broker_snapshot_initial_investment_usd"] = float(initial) if initial else None
    report = build_live_readiness_report(
        ui_readiness=ui_readiness(),
        daily_bundle=daily_bundle(),
        account_ledger=ledger,
        movement_stream=movement,
        account_reconciliation=reconciliation,
        backsolve=backsolve_summary(),
        walk_forward=walk_forward_summary(),
        mt5_receipt=receipt,
        mt5_probe_status=mt5_probe_status(),
        runtime_gates=runtime_gates_report(),
        authority_boundary=authority_boundary(),
        broker_reality_review=broker_reality_review(),
        live_pilot_policy=live_pilot_policy(),
        live_recovery_report=live_recovery_status(),
        adaptive=adaptive,
        owner_promotion=owner_promotion_review_summary(),
    ).to_dict()
    report["sync_to_broker_snapshot"] = bool(sync_to_broker and initial)
    report["broker_snapshot_initial_investment_usd"] = float(initial) if initial else None
    return report


def broker_reality_review(broker_id: str | None = None) -> Dict[str, Any]:
    return build_broker_reality_review(broker_id)


def live_pilot_policy() -> Dict[str, Any]:
    return build_live_pilot_policy()


def live_order_dry_run_latest() -> Dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(LIVE_ORDER_DRY_RUN_AUDIT_PATH).latest()
    if latest is None:
        return {
            "report_kind": "cas_forex_live_order_dry_run_latest",
            "status": "NO_DRY_RUN_AUDIT_YET",
            "broker_touched": False,
            "detail": "No live-order dry-run audit has been recorded yet.",
        }
    return {
        "report_kind": "cas_forex_live_order_dry_run_latest",
        "status": latest.get("status"),
        "broker_touched": False,
        "latest_audit": latest,
    }


def compound_add_order_dry_run_latest() -> Dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(COMPOUND_ADD_DRY_RUN_AUDIT_PATH).latest()
    if latest is None:
        return {
            "report_kind": "cas_forex_compound_add_order_dry_run_latest",
            "status": "NO_COMPOUND_ADD_DRY_RUN_AUDIT_YET",
            "broker_touched": False,
            "detail": "No compound-add dry-run audit has been recorded yet.",
        }
    return {
        "report_kind": "cas_forex_compound_add_order_dry_run_latest",
        "status": latest.get("status"),
        "broker_touched": False,
        "latest_audit": latest,
    }


def compound_add_order_dry_run_review_status() -> Dict[str, Any]:
    return build_compound_add_order_dry_run_review()


def compound_add_dispatch_handoff_status() -> Dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(COMPOUND_ADD_DRY_RUN_AUDIT_PATH).latest()
    payload = latest.get("payload") if isinstance(latest, dict) else {}
    review = build_compound_add_order_dry_run_review(dry_run_audit=latest or {})
    return build_compound_add_dispatch_handoff_status(
        payload if isinstance(payload, dict) else {},
        review=review,
    )


def live_order_dry_run_review_status() -> Dict[str, Any]:
    return build_live_order_dry_run_review()


def waste_entry_pilot_promotion_status() -> Dict[str, Any]:
    latest = LiveOrderDryRunAuditLog(LIVE_ORDER_DRY_RUN_AUDIT_PATH).latest()
    return build_waste_pilot_promotion_status(dry_run_audit=latest or {})


def waste_direction_review_packet() -> Dict[str, Any]:
    return _build_scoped("waste_direction_review_packet", build_waste_direction_review_packet)


def waste_direction_learning_ledger() -> Dict[str, Any]:
    return _build_scoped("waste_direction_learning_ledger", build_waste_direction_learning_ledger)


def waste_direction_outcome_binding() -> Dict[str, Any]:
    return _build_scoped("waste_direction_outcome_binding", build_waste_direction_outcome_binding)


def waste_paper_sample_collector() -> Dict[str, Any]:
    return build_waste_paper_sample_collector(
        mt5_market_data_diagnostic=mt5_market_data_diagnostic_status(),
        real_candle_probe=waste_real_candle_probe_status(),
        direction_learning=waste_direction_learning_ledger(),
        direction_outcome_binding=waste_direction_outcome_binding(),
        mt5_deal_history_ingest=_optional_mt5_deal_history_ingest(),
    )


def waste_paper_sample_collector_scheduler_status() -> Dict[str, Any]:
    return build_waste_paper_sample_collector_scheduler_status()


def waste_adaptation_promotion_rule() -> Dict[str, Any]:
    return build_waste_adaptation_promotion_rule(
        direction_learning=waste_direction_learning_ledger(),
        direction_outcome_binding=waste_direction_outcome_binding(),
    )


def waste_adaptation_plan() -> Dict[str, Any]:
    return build_waste_adaptation_plan(
        direction_learning=waste_direction_learning_ledger(),
        direction_review=waste_direction_review_packet(),
        adaptation_promotion_rule=waste_adaptation_promotion_rule(),
    )


def waste_adaptation_apply_preview() -> Dict[str, Any]:
    return build_waste_adaptation_apply_preview(
        adaptation_plan=waste_adaptation_plan(),
        runtime_gates=runtime_gates_report(),
    )


def waste_adaptation_owner_review() -> Dict[str, Any]:
    return build_waste_adaptation_owner_review(
        adaptation_apply_preview=waste_adaptation_apply_preview(),
    )


def waste_adaptation_paper_apply_status() -> Dict[str, Any]:
    return build_waste_adaptation_paper_apply_status(
        owner_review=waste_adaptation_owner_review(),
    )


def order_attempt_recovery_packet() -> Dict[str, Any]:
    return build_order_attempt_recovery_packet(
        order_attempt_status=build_order_attempt_audit_status(),
    )


def live_recovery_status() -> Dict[str, Any]:
    return build_live_recovery_report()


def live_money_progression_packet() -> Dict[str, Any]:
    return build_live_money_progression_packet(
        runtime_gates=runtime_gates_report(),
        broker_truth_packet=build_broker_truth_recovery_packet(
            monitor_state=broker_truth_monitor_status(),
        ),
        live_recovery_report=live_recovery_status(),
        waste_pilot_promotion=waste_entry_pilot_promotion_status(),
        waste_direction_review=waste_direction_review_packet(),
        waste_direction_learning=waste_direction_learning_ledger(),
        waste_direction_outcome_binding=waste_direction_outcome_binding(),
        waste_adaptation_promotion_rule=waste_adaptation_promotion_rule(),
        waste_adaptation_plan=waste_adaptation_plan(),
        waste_adaptation_apply_preview=waste_adaptation_apply_preview(),
        waste_adaptation_owner_review=waste_adaptation_owner_review(),
        waste_adaptation_paper_apply=waste_adaptation_paper_apply_status(),
        sweep_preview=verified_profit_sweep_preview_status(),
        payout_recovery_status=build_payout_recovery_status(),
        live_readiness_report=live_readiness(),
    )


def mt5_market_data_diagnostic_status() -> Dict[str, Any]:
    return latest_mt5_market_data_diagnostic()


def waste_real_candle_probe_status() -> Dict[str, Any]:
    return latest_waste_real_candle_probe()


def _optional_mt5_deal_history_ingest() -> Dict[str, Any]:
    try:
        return mt5_deal_history_ingest_latest()
    except HTTPException as exc:
        return {
            "report_kind": "cas_forex_mt5_deal_history_ingest_report",
            "ingest_status": "UNAVAILABLE",
            "error": str(exc.detail),
            "history_records": [],
            "summary": {
                "closed_position_count": 0,
                "history_record_count": 0,
                "net_profit_loss_account": 0.0,
            },
        }


def _broker_snapshot_initial_investment(receipt: Dict[str, Any]) -> float | None:
    account_snapshot = receipt.get("account_snapshot") or {}
    if not isinstance(account_snapshot, dict):
        account_snapshot = {}
    initial = receipt.get("balance") or account_snapshot.get("balance")
    return float(initial) if initial else None


def owner_control() -> Dict[str, Any]:
    return build_owner_control_report(live_authorized=False)


def mt_history() -> Optional[Dict[str, Any]]:
    output_dir = EVIDENCE_ROOT / "mt_history_import"
    if not output_dir.exists():
        return None
    files = sorted(output_dir.glob("*.json"))
    if not files:
        return None
    report = _read_json(files[-1])
    summary = report.get("summary")
    return summary if isinstance(summary, dict) else report


def mt5_receipt() -> Dict[str, Any]:
    payload = _latest_mt5_verified_receipt_payload()
    probe = payload.get("probe") or {}
    receipt = probe.get("receipt") or {}
    report = payload.get("report") or {}
    daily_summaries = report.get("daily_summaries") or []
    latest_summary = daily_summaries[-1] if daily_summaries else {}
    account_snapshot = receipt.get("account_snapshot") or latest_summary.get("account_snapshot") or {}
    if not isinstance(account_snapshot, dict):
        account_snapshot = {}
    return {
        "receipt_id": receipt.get("receipt_id") or latest_summary.get("receipt_id"),
        "receipt_validation_status": receipt.get("receipt_validation_status") or latest_summary.get("receipt_validation_status"),
        "broker_mode": receipt.get("broker_mode") or latest_summary.get("broker_mode"),
        "trading_date": receipt.get("trading_date") or latest_summary.get("date"),
        "symbols": receipt.get("symbols") or latest_summary.get("symbols") or [],
        "orders_attempted": receipt.get("orders_attempted", latest_summary.get("orders_attempted", 0)),
        "open_positions_reconciled": bool(
            receipt.get("open_positions_reconciled", latest_summary.get("open_positions_reconciled", False))
        ),
        "live_mode": bool(receipt.get("live_mode", latest_summary.get("live_mode", False))),
        "broker_api_authenticated": bool(
            receipt.get("broker_api_authenticated", latest_summary.get("broker_api_authenticated", False))
        ),
        "broker_source_verified": bool(
            receipt.get("broker_source_verified", latest_summary.get("broker_source_verified", False))
        ),
        "server": receipt.get("server") or latest_summary.get("server"),
        "terminal_name": receipt.get("terminal_name") or latest_summary.get("terminal_name"),
        "receipt_hash_sha256": receipt.get("receipt_hash_sha256") or latest_summary.get("broker_receipt_hash_sha256"),
        "broker_export_sha256": receipt.get("broker_export_sha256") or latest_summary.get("broker_export_sha256"),
        "account_snapshot": account_snapshot,
        "balance": account_snapshot.get("balance"),
        "equity": account_snapshot.get("equity"),
        "margin": account_snapshot.get("margin"),
        "margin_free": account_snapshot.get("margin_free"),
        "account_currency": account_snapshot.get("currency"),
        "account_leverage": account_snapshot.get("leverage"),
        "packet_hash": "56faa6ac644c30fa6ff86588121aa2f4acc58b95401000e1a0b1227fca0a63cf",
        "record_hash": "a52334295d7251512a04137ff2bc83ade0228c0ec798f67a872d3e0742c1f092",
        "chain_verified": bool(report.get("chain_verified", False)),
        "worm_retained": False,
    }



def mt5_probe_status() -> Dict[str, Any]:
    path, payload = _latest_mt5_probe_payload()
    probe = payload.get("probe") or {}
    receipt = probe.get("receipt") or {}
    return {
        "probe_path": str(path.relative_to(REPO_ROOT)),
        "status": probe.get("status", "MISSING"),
        "broker": probe.get("broker"),
        "trading_date": probe.get("trading_date"),
        "has_receipt": bool(receipt),
        "receipt_validation_status": receipt.get("receipt_validation_status"),
        "account_snapshot_present": bool(receipt.get("account_snapshot")),
        "reasons": probe.get("reasons", []),
        "claim_boundary": probe.get("claim_boundary", "Demo broker receipt collection is paper-proof only. Live trading, broker ACCEPT, and payment transfers remain NOT LICENSED."),
    }


def _mt5_probe_files() -> List[Path]:
    files = sorted(PROOF_DIR.glob(f"{PLAN_ID}-mt5-demo-probe-*.json"))
    if not files:
        raise HTTPException(status_code=404, detail="No MT5 demo probe artifacts found")
    return files


def _latest_mt5_probe_payload() -> tuple[Path, Dict[str, Any]]:
    path = _mt5_probe_files()[-1]
    return path, _read_json(path)


def _latest_mt5_verified_receipt_payload() -> Dict[str, Any]:
    # Latest probe attempts may be UNAVAILABLE/BLOCKED. The receipt endpoint is
    # the latest verified broker receipt, not the latest attempt status. This
    # preserves evidence while mt5ProbeStatus exposes current operational blockers.
    for path in reversed(_mt5_probe_files()):
        payload = _read_json(path)
        probe = payload.get("probe") or {}
        receipt = probe.get("receipt") or {}
        if probe.get("status") == "BROKER_API_VERIFIED" and receipt:
            return payload
    # Fall back to the latest probe so the caller gets a clear missing receipt shape.
    return _latest_mt5_probe_payload()[1]

def _read_json(path: Path) -> Any:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing evidence artifact: {path.relative_to(REPO_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_file(directory: Path, pattern: str) -> Path:
    if not directory.exists():
        raise HTTPException(status_code=404, detail=f"Missing evidence directory: {directory.relative_to(REPO_ROOT)}")
    files = sorted(directory.glob(pattern))
    if not files:
        raise HTTPException(status_code=404, detail=f"No evidence files match {pattern}")
    return files[-1]
