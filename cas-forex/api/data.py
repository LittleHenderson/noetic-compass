"""Evidence-backed data loader for the CAS Forex proof cockpit API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from cas_forex.account_ledger import build_account_ledger_from_paper_review
from cas_forex.movement_stream import build_movement_stream_state
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
from cas_forex.market_data.connector import get_connector
from cas_forex.authority_boundary import build_authority_boundary_report
from cas_forex.runtime_gates import build_runtime_gates_report
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
PROOF_DIR = EVIDENCE_ROOT / "index_tsmom_126_paper_proof"
PLAN_ID = "index-tsmom-126-d1-paper-proof"


def dashboard_state() -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "uiReadiness": ui_readiness(),
        "dailySchedule": daily_schedule(),
        "dailyBundle": daily_bundle(),
        "ownerControl": owner_control(),
        "accountLedger": account_ledger(),
        "movementStream": movement_stream(),
        "accountReconciliation": account_reconciliation(),
        "liveReadiness": live_readiness(),
        "ownerPromotionReview": owner_promotion_review_summary(),
        "strategyLeads": strategy_leads(),
        "backsolve": backsolve_summary(),
        "conditionTally": condition_tally(),
        "walkForward": walk_forward_summary(),
        "externalBenchmarks": external_benchmarks(),
        "forexFurySetImport": None,
        "forexFuryReplayCandidates": None,
        "forexFuryReplayResults": None,
        "agentWorkflowPlan": None,
        "agentWorkflowCycle": None,
        "agentInformationFlow": None,
        "agentMessageBus": None,
        "agentMemory": None,
        "agentResearchQueue": None,
        "strategyDevQueue": None,
        "strategyPatchRunner": None,
        "dailyLearningRollup": None,
        "sessionAutowake": None,
        "terminalReceiptWatcher": None,
        "terminalBridgeSupervisor": None,
        "mt4TerminalActivation": None,
        "mt4PingRoundtrip": None,
        "mt4TerminalSessionVerifier": None,
        "mt4HistoryExportVerifier": None,
        "mt5TerminalApiVerifier": None,
        "mt5PaperExecutionVerifier": None,
        "mt5DealHistoryIngest": None,
        "terminalPositionReconciliation": None,
        "terminalOperabilityVerifier": None,
        "terminalReceiptIngest": None,
        "terminalHistoryIngest": None,
        "mt5Receipt": mt5_receipt(),
        "mt5ProbeStatus": mt5_probe_status(),
        "authorityBoundary": authority_boundary(),
        "runtimeGates": runtime_gates_report(),
        "aiModel": ai_model_status(),
        "brokerCandidates": broker_candidate_profiles(),
        "pcba": pcba_cockpit(),
    }
    try:
        state["forexFurySetImport"] = forex_fury_set_import()
    except HTTPException:
        state["forexFurySetImport"] = None
    try:
        state["forexFuryReplayCandidates"] = forex_fury_replay_candidates()
    except HTTPException:
        state["forexFuryReplayCandidates"] = None
    try:
        state["forexFuryReplayResults"] = forex_fury_replay_results()
    except HTTPException:
        state["forexFuryReplayResults"] = None
    try:
        state["agentWorkflowPlan"] = agent_workflow_plan()
    except HTTPException:
        state["agentWorkflowPlan"] = None
    try:
        state["agentWorkflowCycle"] = agent_workflow_cycle()
    except HTTPException:
        state["agentWorkflowCycle"] = None
    try:
        state["agentInformationFlow"] = agent_information_flow()
    except HTTPException:
        state["agentInformationFlow"] = None
    try:
        state["agentMessageBus"] = agent_message_bus_summary()
    except HTTPException:
        state["agentMessageBus"] = None
    try:
        state["agentMemory"] = agent_memory_latest()
    except HTTPException:
        state["agentMemory"] = None
    try:
        state["agentResearchQueue"] = agent_research_queue_latest()
    except HTTPException:
        state["agentResearchQueue"] = None
    try:
        state["strategyDevQueue"] = strategy_dev_queue_latest()
    except HTTPException:
        state["strategyDevQueue"] = None
    try:
        state["strategyPatchRunner"] = strategy_patch_runner_latest()
    except HTTPException:
        state["strategyPatchRunner"] = None
    try:
        state["dailyLearningRollup"] = daily_learning_rollup_latest()
    except HTTPException:
        state["dailyLearningRollup"] = None
    try:
        state["sessionAutowake"] = session_autowake_latest()
    except HTTPException:
        state["sessionAutowake"] = None
    try:
        state["terminalReceiptWatcher"] = terminal_receipt_watcher_latest()
    except HTTPException:
        state["terminalReceiptWatcher"] = None
    try:
        state["terminalBridgeSupervisor"] = terminal_bridge_supervisor_latest()
    except HTTPException:
        state["terminalBridgeSupervisor"] = None
    try:
        state["mt4TerminalActivation"] = mt4_terminal_activation_latest()
    except HTTPException:
        state["mt4TerminalActivation"] = None
    try:
        state["mt4PingRoundtrip"] = mt4_ping_roundtrip_latest()
    except HTTPException:
        state["mt4PingRoundtrip"] = None
    try:
        state["mt4TerminalSessionVerifier"] = mt4_terminal_session_verifier_latest()
    except HTTPException:
        state["mt4TerminalSessionVerifier"] = None
    try:
        state["mt4HistoryExportVerifier"] = mt4_history_export_verifier_latest()
    except HTTPException:
        state["mt4HistoryExportVerifier"] = None
    try:
        state["mt5TerminalApiVerifier"] = mt5_terminal_api_verifier_latest()
    except HTTPException:
        state["mt5TerminalApiVerifier"] = None
    try:
        state["mt5PaperExecutionVerifier"] = mt5_paper_execution_verifier_latest()
    except HTTPException:
        state["mt5PaperExecutionVerifier"] = None
    try:
        state["mt5DealHistoryIngest"] = mt5_deal_history_ingest_latest()
    except HTTPException:
        state["mt5DealHistoryIngest"] = None
    try:
        state["terminalPositionReconciliation"] = terminal_position_reconciliation_latest()
    except HTTPException:
        state["terminalPositionReconciliation"] = None
    try:
        state["terminalOperabilityVerifier"] = terminal_operability_verifier_latest()
    except HTTPException:
        state["terminalOperabilityVerifier"] = None
    try:
        state["terminalReceiptIngest"] = terminal_receipt_ingest_latest()
    except HTTPException:
        state["terminalReceiptIngest"] = None
    try:
        state["terminalHistoryIngest"] = terminal_history_ingest_latest()
    except HTTPException:
        state["terminalHistoryIngest"] = None
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


def backsolve_summary() -> Dict[str, Any]:
    path = _latest_file(EVIDENCE_ROOT / "leverage_income_backsolve", "leverage-income-backsolve-*-report.json")
    report = _read_json(path)
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
    return state.to_dict()


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
    ledger = account_ledger()
    snapshots: Dict[str, Any] = {}
    if use_provider_quotes:
        connector = get_connector()
        for row in ledger.get("positions", []):
            symbol = row.get("symbol")
            if not symbol or symbol in snapshots:
                continue
            try:
                snapshots[str(symbol)] = connector.fetch_snapshot(str(symbol))
            except Exception:
                # Fail soft: movement stream must remain available even when the
                # external provider is down or missing. The core builder falls
                # back to paper-route prices for any missing symbol.
                continue
    return build_movement_stream_state(ledger, market_snapshots=snapshots).to_dict()

def account_reconciliation(sync_to_broker: bool = False) -> Dict[str, Any]:
    receipt = mt5_receipt()
    initial = _broker_snapshot_initial_investment(receipt) if sync_to_broker else None
    ledger = account_ledger(initial_investment_usd=float(initial) if initial else None)
    movement = build_movement_stream_state(ledger).to_dict()
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
    movement = build_movement_stream_state(ledger).to_dict()
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
        adaptive=adaptive,
        owner_promotion=owner_promotion_review_summary(),
    ).to_dict()
    report["sync_to_broker_snapshot"] = bool(sync_to_broker and initial)
    report["broker_snapshot_initial_investment_usd"] = float(initial) if initial else None
    return report


def _broker_snapshot_initial_investment(receipt: Dict[str, Any]) -> float | None:
    account_snapshot = receipt.get("account_snapshot") or {}
    if not isinstance(account_snapshot, dict):
        account_snapshot = {}
    initial = receipt.get("balance") or account_snapshot.get("balance")
    return float(initial) if initial else None


def owner_control() -> Dict[str, Any]:
    return {
        "mode": "AI_FULL_AUTO_PAPER",
        "max_concurrent_trades": 15,
        "max_loss_cap_pct": 10,
        "ai_autonomy_enabled": True,
        "live_requested": False,
        "live_blocked": True,
        "claim_boundary": (
            "Owner control policy is owner-controlled: CAS Forex can run research/paper automation now. "
            "Live trading, broker ACCEPT, and payment movement require explicit owner enable flags, "
            "credentials/provider config, and gate clearance."
        ),
    }


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
