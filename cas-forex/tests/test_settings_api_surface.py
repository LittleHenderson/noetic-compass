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
from api.server import app


REPO_ROOT = Path(__file__).resolve().parents[1]


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
    for shared_selector in (
        ".sweep-action-button",
        ".sweep-confirm-check",
        ".sweep-status-row",
    ):
        assert shared_selector in app_css


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
        ".quick-start-pwa-self-mark",
        ".quick-start-completion-banner",
    ):
        assert route_selector not in app_css
        assert route_selector in quick_start_css


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
    assert "Live dispatch blocked: paper/demo loop can keep running" in windows_page
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
        ".live-telemetry-empty",
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
    funding_panel = settings.split("function BrokerFundingHandoffPanel()", 1)[1].split(
        "function ControlField",
        1,
    )[0]

    assert "<BrokerFundingHandoffPanel />" in settings
    assert "https://app.hugosway.com" in settings
    assert "Open Broker Portal" in funding_panel
    assert "Sync Broker Snapshot" in funding_panel
    assert "fetchAccountReconciliation(true)" in funding_panel
    assert "NO RAW BANK/CARD STORAGE" in funding_panel
    assert "input" not in funding_panel
    assert "apiPost" not in funding_panel


def test_proof_page_exposes_broker_funding_route_at_live_controls():
    proof = (REPO_ROOT / "ui" / "src" / "pages" / "ProofPage.tsx").read_text(encoding="utf-8")
    funding_block = proof.split("<div className=\"go-live-group-title\">Broker Funding Route</div>", 1)[1].split(
        "<div className=\"not-licensed-grid\"",
        1,
    )[0]

    assert "https://app.hugosway.com" in proof
    assert "OPEN BROKER PORTAL" in funding_block
    assert "SYNC BROKER SNAPSHOT" in funding_block
    assert "fetchAccountReconciliation(true)" in proof
    assert "NO RAW BANK/CARD STORAGE" in funding_block
    assert "apiPost" not in funding_block
    assert "type=\"password\"" not in funding_block


def test_app_shell_share_page_config_and_single_active_route_renderer():
    app = (REPO_ROOT / "ui" / "src" / "App.tsx").read_text(encoding="utf-8")
    shell = (
        REPO_ROOT / "ui" / "src" / "components" / "Shell.tsx"
    ).read_text(encoding="utf-8")
    page_config = (REPO_ROOT / "ui" / "src" / "pageConfig.ts").read_text(encoding="utf-8")

    assert "from \"./pageConfig\"" in app
    assert "from \"../pageConfig\"" in shell
    assert "export const NAV_ITEMS" in page_config
    assert "type Page =" not in app
    assert "type Page =" not in shell
    assert "const NAV_ITEMS" not in shell
    assert "PAGE_COMPONENTS" in app
    assert "<ActivePage state={state} />" in app
    assert "page === \"quick-start\"" not in app
    assert "page === \"dashboard\" && <DashboardPage" not in app


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
    assert "? [rememberedBase, savedBase, DEFAULT_API_BASE]" in api_core
    assert ": [savedBase, rememberedBase, DEFAULT_API_BASE]" in api_core
    assert "rememberSuccessfulApiBase(base);" in api_core
    assert api_core.count("rememberSuccessfulApiBase(base);") >= 4
    assert "function readLastSuccessfulWasteStageApiBase(): string | null" in stage_probe
    assert "function rememberSuccessfulWasteStageApiBase(base: string): void" in stage_probe
    assert "const rememberedBase = readLastSuccessfulWasteStageApiBase();" in stage_probe
    assert "? [rememberedBase, savedBase, DEFAULT_API_BASE]" in stage_probe
    assert ": [savedBase, rememberedBase, DEFAULT_API_BASE]" in stage_probe
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

    assert '"**/*.{js,css,html,svg,png,ico,webmanifest,json}"' not in vite_config
    assert '"index.html"' in vite_config
    assert '"registerSW.js"' in vite_config
    assert '"manifest.webmanifest"' in vite_config
    assert '"assets/index-*.css"' in vite_config
    assert '"assets/index-*.js"' in vite_config
    assert '"assets/react-vendor-*.js"' in vite_config
    assert 'handler: "StaleWhileRevalidate"' in vite_config


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
    assert "const [dashboardHydratorMounted, setDashboardHydratorMounted] = useState(" in app
    assert '() => initialPageFromUrl() === "dashboard",' in app
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
        for index, key in enumerate(key for key in result if key not in {"operator_briefing", "stack_health_check"})
        if key not in {"operator_briefing", "stack_health_check"}
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
        "/api/forex/notifications/subscriptions",
        "/api/forex/webhook-notifications/subscriptions",
        "/api/forex/proof-control/state",
        "/api/forex/settings/authority-boundary",
        "/api/forex/settings/runtime-gates",
        "/api/forex/pcba/cockpit",
        "/api/forex/readiness/live",
        "/api/forex/live-enable/authorization",
        "/api/forex/live-enable/state",
        "/api/forex/waste-loop/stage",
        "/api/forex/dispatch-loop/status",
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
