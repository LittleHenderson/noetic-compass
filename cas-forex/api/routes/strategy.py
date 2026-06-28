from typing import Optional

from fastapi import APIRouter, Query
from ..data import (
    agent_information_flow,
    agent_memory_latest,
    agent_research_queue_latest,
    agent_message_bus_summary,
    agent_workflow_context_latest,
    agent_workflow_cycle,
    agent_workflow_events,
    agent_workflow_intents_open,
    agent_workflow_plan,
    agent_workflow_receipts_latest,
    backsolve_summary,
    condition_tally,
    daily_learning_rollup_latest,
    external_benchmarks,
    forex_fury_replay_candidates,
    forex_fury_replay_results,
    forex_fury_set_import,
    session_autowake_latest,
    strategy_dev_queue_latest,
    strategy_patch_runner_latest,
    strategy_leads,
    terminal_history_ingest_latest,
    terminal_bridge_supervisor_latest,
    mt4_terminal_activation_latest,
    mt4_ping_roundtrip_latest,
    mt4_terminal_session_verifier_latest,
    mt4_history_export_verifier_latest,
    mt5_terminal_api_verifier_latest,
    mt5_paper_execution_verifier_latest,
    mt5_deal_history_ingest_latest,
    terminal_position_reconciliation_latest,
    terminal_operability_verifier_latest,
    terminal_receipt_watcher_latest,
    terminal_receipt_ingest_latest,
    walk_forward_summary,
)

router = APIRouter()


@router.get("/leads")
async def get_leads():
    """Returns all strategy leads."""
    return strategy_leads()


@router.get("/backsolve")
async def get_backsolve():
    """Returns latest leverage backsolve summary."""
    return backsolve_summary()


@router.get("/condition-tally")
async def get_condition_tally():
    """Returns condition tally buckets."""
    return condition_tally()


@router.get("/walk-forward")
async def get_walk_forward():
    """Returns latest walk-forward summary."""
    return walk_forward_summary()


@router.get("/external-benchmarks")
async def get_external_benchmarks():
    """Returns external strategy benchmark snapshots."""
    return external_benchmarks()


@router.get("/forex-fury-set-import")
async def get_forex_fury_set_import():
    """Returns latest owner-supplied Forex Fury set import report."""
    return forex_fury_set_import()


@router.get("/forex-fury-replay-candidates")
async def get_forex_fury_replay_candidates():
    """Returns latest CAS replay/backtest candidates derived from Forex Fury sets."""
    return forex_fury_replay_candidates()


@router.get("/forex-fury-replay-results")
async def get_forex_fury_replay_results():
    """Returns latest CAS replay/backtest results derived from Forex Fury candidates."""
    return forex_fury_replay_results()


@router.get("/agent-workflow-plan")
async def get_agent_workflow_plan():
    """Returns latest CAS Forex agentic trading-day workflow plan."""
    return agent_workflow_plan()


@router.get("/agent-workflow-cycle/latest")
async def get_agent_workflow_cycle():
    """Returns latest CAS Forex paper/demo agent workflow execution cycle."""
    return agent_workflow_cycle()


@router.get("/agent-information-flow")
async def get_agent_information_flow():
    """Returns latest CAS Forex inter-agent information-flow plan."""
    return agent_information_flow()


@router.get("/agent-workflow-events/summary")
async def get_agent_message_bus_summary():
    """Returns CAS Forex append-only agent event journal summary."""
    return agent_message_bus_summary()


@router.get("/agent-workflow-events")
async def get_agent_workflow_events(
    cycle_id: Optional[str] = None,
    after_event_id: Optional[str] = None,
    limit: int = Query(default=500, ge=1, le=5000),
):
    """Returns CAS Forex append-only agent events."""
    return agent_workflow_events(cycle_id=cycle_id, after_event_id=after_event_id, limit=limit)


@router.get("/agent-workflow-context/latest")
async def get_agent_workflow_context_latest():
    """Returns latest CAS Forex shared agent context event."""
    return agent_workflow_context_latest()


@router.get("/agent-workflow-intents/open")
async def get_agent_workflow_intents_open():
    """Returns open CAS Forex route-intent events."""
    return agent_workflow_intents_open()


@router.get("/agent-workflow-receipts/latest")
async def get_agent_workflow_receipts_latest(
    command_id: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=500),
):
    """Returns latest CAS Forex terminal receipt events."""
    return agent_workflow_receipts_latest(command_id=command_id, limit=limit)


@router.get("/agent-memory/latest")
async def get_agent_memory_latest():
    """Returns latest CAS Forex agent outcome-memory report."""
    return agent_memory_latest()


@router.get("/agent-research-queue/latest")
async def get_agent_research_queue_latest():
    """Returns latest CAS Forex agent research queue report."""
    return agent_research_queue_latest()


@router.get("/strategy-dev-queue/latest")
async def get_strategy_dev_queue_latest():
    """Returns latest CAS Forex strategy-development queue report."""
    return strategy_dev_queue_latest()


@router.get("/strategy-patch-runner/latest")
async def get_strategy_patch_runner_latest():
    """Returns latest CAS Forex strategy patch/replay decision report."""
    return strategy_patch_runner_latest()


@router.get("/daily-learning-rollup/latest")
async def get_daily_learning_rollup_latest():
    """Returns latest CAS Forex daily 30-day-window learning rollup."""
    return daily_learning_rollup_latest()


@router.get("/session-autowake/latest")
async def get_session_autowake_latest():
    """Returns latest CAS Forex session autowake runner report."""
    return session_autowake_latest()


@router.get("/terminal-receipt-watcher/latest")
async def get_terminal_receipt_watcher_latest():
    """Returns latest CAS Forex terminal receipt/history watcher report."""
    return terminal_receipt_watcher_latest()


@router.get("/terminal-bridge-supervisor/latest")
async def get_terminal_bridge_supervisor_latest():
    """Returns latest CAS Forex terminal bridge supervisor report."""
    return terminal_bridge_supervisor_latest()


@router.get("/mt4-terminal-activation/latest")
async def get_mt4_terminal_activation_latest():
    """Returns latest CAS Forex MT4 terminal activation/staging report."""
    return mt4_terminal_activation_latest()


@router.get("/mt4-ping-roundtrip/latest")
async def get_mt4_ping_roundtrip_latest():
    """Returns latest CAS Forex MT4 ping heartbeat/receipt roundtrip report."""
    return mt4_ping_roundtrip_latest()


@router.get("/mt4-terminal-session-verifier/latest")
async def get_mt4_terminal_session_verifier_latest():
    """Returns latest CAS Forex MT4 terminal session verifier report."""
    return mt4_terminal_session_verifier_latest()


@router.get("/mt4-history-export-verifier/latest")
async def get_mt4_history_export_verifier_latest():
    """Returns latest CAS Forex MT4 closed-history export verifier report."""
    return mt4_history_export_verifier_latest()


@router.get("/mt5-terminal-api-verifier/latest")
async def get_mt5_terminal_api_verifier_latest():
    """Returns latest CAS Forex MT5 terminal API verifier report."""
    return mt5_terminal_api_verifier_latest()


@router.get("/mt5-paper-execution-verifier/latest")
async def get_mt5_paper_execution_verifier_latest():
    """Returns latest CAS Forex MT5 paper/demo execution verifier report."""
    return mt5_paper_execution_verifier_latest()


@router.get("/mt5-deal-history-ingest/latest")
async def get_mt5_deal_history_ingest_latest():
    """Returns latest CAS Forex MT5 closed-deal history ingest report."""
    return mt5_deal_history_ingest_latest()


@router.get("/terminal-position-reconciliation/latest")
async def get_terminal_position_reconciliation_latest():
    """Returns latest CAS Forex terminal position reconciliation report."""
    return terminal_position_reconciliation_latest()


@router.get("/terminal-operability-verifier/latest")
async def get_terminal_operability_verifier_latest():
    """Returns latest CAS Forex terminal operability go/no-go report."""
    return terminal_operability_verifier_latest()


@router.get("/terminal-receipt-ingest/latest")
async def get_terminal_receipt_ingest_latest():
    """Returns latest CAS Forex terminal receipt ingest report."""
    return terminal_receipt_ingest_latest()


@router.get("/terminal-history-ingest/latest")
async def get_terminal_history_ingest_latest():
    """Returns latest CAS Forex terminal close/history ingest report."""
    return terminal_history_ingest_latest()
