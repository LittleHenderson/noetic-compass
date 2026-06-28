"""Inter-agent information-flow blueprint for the CAS Forex agent desk."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "agent_information_flow"
CLAIM_BOUNDARY = (
    "Agent information-flow plans define message shapes, state transitions, "
    "storage paths, API surfaces, and agent responsibilities. They do not by "
    "themselves execute live broker orders, create broker ACCEPT, deposit, "
    "withdraw, move bank/card funds, or automate payouts."
)


class AgentInformationFlowError(ValueError):
    """Raised when the information-flow report is missing required structure."""


def _specialist_agent_reviews() -> list[dict[str, Any]]:
    return [
        {
            "agent": "Sagan",
            "focus": "information architecture and coordination channels",
            "verdict": (
                "Use a hybrid flow: append-only local event journal, durable "
                "evidence artifacts, read-only API projections, and MT4/MT5 "
                "mailbox files only for terminal command/receipt exchange."
            ),
            "plain_english": "Desk logbook first, cockpit display second, terminal outbox/inbox third.",
        },
        {
            "agent": "Mill",
            "focus": "execution lifecycle and terminal bridge control",
            "verdict": (
                "The command flow must become receipt/reconciliation-gated: "
                "approved routes write commands, commands wait for terminal "
                "receipts, receipts reconcile, then the next same-symbol cycle "
                "can proceed."
            ),
            "plain_english": "Do not fire another same-symbol open command until the previous command comes back with a usable receipt.",
        },
        {
            "agent": "Leibniz",
            "focus": "research memory and learning loop",
            "verdict": (
                "Close the learning loop by joining route intent, overseer "
                "decision, terminal command, receipt, close outcome, condition "
                "snapshot, and daily 30-day rollup."
            ),
            "plain_english": "Save what happened after the trade, not just why the trade idea was proposed.",
        },
    ]


def build_agent_information_flow_plan() -> Dict[str, Any]:
    """Return the recommended inter-agent information-flow plan."""

    packets = _canonical_packets()
    stages = _flow_stages()
    planes = _information_planes()
    report = {
        "report_kind": "cas_forex_agent_information_flow_plan",
        "created_at": datetime.now(UTC).isoformat(),
        "flow_status": "FLOW_BLUEPRINT_READY",
        "claim_boundary": CLAIM_BOUNDARY,
        "design_principle": (
            "Agents coordinate through an append-only event journal. API routes "
            "are read-only projections for the cockpit, and MT4/MT5 mailbox files "
            "are used only for terminal command and receipt exchange."
        ),
        "specialist_agent_reviews": _specialist_agent_reviews(),
        "agent_roles": _agent_roles(),
        "information_planes": planes,
        "event_envelope": _event_envelope(),
        "canonical_packets": packets,
        "flow_stages": stages,
        "state_machine": _state_machine(),
        "receipt_and_reconciliation_lifecycle": _receipt_and_reconciliation_lifecycle(),
        "learning_memory_contracts": _learning_memory_contracts(),
        "main_bottlenecks": _main_bottlenecks(),
        "storage_and_api_targets": _storage_and_api_targets(),
        "implementation_queue": _implementation_queue(),
        "summary": {
            "agent_count": 8,
            "information_plane_count": len(planes),
            "specialist_agent_count": 3,
            "canonical_packet_count": len(packets),
            "flow_stage_count": len(stages),
            "lifecycle_state_count": len(_receipt_and_reconciliation_lifecycle()),
            "must_have_next_file": "evidence_runs/daily_learning_rollup/daily-learning-rollup-*-report.json",
            "best_flow_form": "append-only event journal plus read-only API projections",
        },
    }
    validate_agent_information_flow_plan(report)
    return report


def write_agent_information_flow_report(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Path]:
    report = build_agent_information_flow_plan()
    target_dir = output_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"agent-information-flow-{stamp}-report.json"
    md_path = target_dir / f"agent-information-flow-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_agent_information_flow_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_agent_information_flow_report(report_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    payload = _read_latest(report_dir, "agent-information-flow-*-report.json")
    validate_agent_information_flow_plan(payload)
    return payload


def validate_agent_information_flow_plan(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "flow_status",
        "claim_boundary",
        "agent_roles",
        "information_planes",
        "event_envelope",
        "canonical_packets",
        "flow_stages",
        "state_machine",
        "receipt_and_reconciliation_lifecycle",
        "learning_memory_contracts",
        "storage_and_api_targets",
    }
    missing = required.difference(payload)
    if missing:
        raise AgentInformationFlowError(f"agent information-flow report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != "cas_forex_agent_information_flow_plan":
        raise AgentInformationFlowError("unexpected agent information-flow report_kind")
    packets = {packet.get("packet_name") for packet in payload.get("canonical_packets", [])}
    required_packets = {
        "AgentContextPacket",
        "RouteIntentPacket",
        "OverseerDecisionPacket",
        "TerminalCommandPacket",
        "TerminalReceiptPacket",
        "OutcomeMemoryPacket",
        "ResearchTaskPacket",
        "MT4TerminalActivationPacket",
        "MT4HistoryExporterPacket",
        "MT4HistoryExportVerifierPacket",
        "MT5TerminalApiVerifierPacket",
        "MT5PaperExecutionVerifierPacket",
        "TerminalPositionReconciliationPacket",
        "TerminalOperabilityVerifierPacket",
    }
    missing_packets = required_packets.difference(packets)
    if missing_packets:
        raise AgentInformationFlowError(f"missing canonical packets: {sorted(missing_packets)}")
    if "do not by themselves execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise AgentInformationFlowError("claim boundary must preserve execution limit")
    envelope_fields = set((payload.get("event_envelope") or {}).get("required_fields") or [])
    required_envelope_fields = {"event_id", "cycle_id", "producer_agent_id", "consumer_agent_ids", "event_type", "idempotency_key", "source_refs", "payload"}
    missing_envelope_fields = required_envelope_fields.difference(envelope_fields)
    if missing_envelope_fields:
        raise AgentInformationFlowError(f"missing event envelope fields: {sorted(missing_envelope_fields)}")
    lifecycle_states = {item.get("state") for item in payload.get("receipt_and_reconciliation_lifecycle", [])}
    required_states = {"COMMAND_WRITTEN", "RECEIPT_PENDING", "RECEIPT_VERIFIED", "RECONCILED", "NEXT_CYCLE_ALLOWED"}
    missing_states = required_states.difference(lifecycle_states)
    if missing_states:
        raise AgentInformationFlowError(f"missing receipt lifecycle states: {sorted(missing_states)}")


def render_agent_information_flow_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Agent Information-Flow Plan",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('flow_status')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Bottom Line",
        "",
        f"- Best flow form: `{summary.get('best_flow_form')}`",
        f"- Specialist agents consulted: `{summary.get('specialist_agent_count')}`",
        f"- Canonical packets: `{summary.get('canonical_packet_count')}`",
        f"- Flow stages: `{summary.get('flow_stage_count')}`",
        f"- Receipt lifecycle states: `{summary.get('lifecycle_state_count')}`",
        f"- Next file: `{summary.get('must_have_next_file')}`",
        "",
        "## Specialist Agent Verdicts",
        "",
    ]
    for review in report.get("specialist_agent_reviews") or []:
        lines.append(f"- `{review.get('agent')}`: {review.get('verdict')}")
    lines.extend([
        "",
        "## Event Envelope",
        "",
    ])
    envelope = report.get("event_envelope") or {}
    lines.append(f"- Schema: `{envelope.get('schema')}`")
    lines.append(f"- Required fields: `{', '.join(envelope.get('required_fields') or [])}`")
    lines.extend([
        "",
        "## Canonical Packets",
        "",
    ])
    for packet in report.get("canonical_packets") or []:
        lines.append(
            f"- `{packet.get('packet_name')}`: {packet.get('purpose')} "
            f"fields `{', '.join(packet.get('required_fields') or [])}`"
        )
    lines.extend(["", "## Flow Stages", ""])
    for stage in report.get("flow_stages") or []:
        lines.append(
            f"- `{stage.get('stage')}` `{stage.get('name')}`: "
            f"{stage.get('producer')} -> {stage.get('consumer')} via `{stage.get('packet')}`"
        )
    lines.extend(["", "## Receipt Lifecycle", ""])
    for state in report.get("receipt_and_reconciliation_lifecycle") or []:
        lines.append(f"- `{state.get('state')}`: {state.get('plain_english')}")
    lines.extend(["", "## Main Bottlenecks", ""])
    for bottleneck in report.get("main_bottlenecks") or []:
        lines.append(f"- `{bottleneck.get('bottleneck_id')}`: {bottleneck.get('plain_english')}")
    lines.extend(["", "## Implementation Queue", ""])
    for item in report.get("implementation_queue") or []:
        lines.append(f"- `{item.get('priority')}` `{item.get('target_file')}`: {item.get('plain_english')}")
    return "\n".join(lines) + "\n"


def _agent_roles() -> list[dict[str, Any]]:
    return [
        {"agent_id": "session_autowake_agent", "consumes": ["AgentContextPacket"], "produces": ["AgentContextPacket"], "cannot_produce": ["TerminalCommandPacket"]},
        {"agent_id": "micro_scalp_agent", "consumes": ["AgentContextPacket"], "produces": ["RouteIntentPacket"], "cannot_produce": ["OverseerDecisionPacket", "TerminalCommandPacket"]},
        {"agent_id": "hourly_intraday_agent", "consumes": ["AgentContextPacket"], "produces": ["RouteIntentPacket"], "cannot_produce": ["OverseerDecisionPacket", "TerminalCommandPacket"]},
        {"agent_id": "overseer_agent", "consumes": ["RouteIntentPacket", "AgentContextPacket"], "produces": ["OverseerDecisionPacket"], "cannot_produce": ["TerminalReceiptPacket"]},
        {"agent_id": "terminal_bridge_agent", "consumes": ["OverseerDecisionPacket"], "produces": ["TerminalCommandPacket", "TerminalReceiptPacket"], "cannot_produce": ["RouteIntentPacket"]},
        {"agent_id": "audit_memory_agent", "consumes": ["TerminalReceiptPacket", "OverseerDecisionPacket"], "produces": ["OutcomeMemoryPacket"], "cannot_produce": ["RouteIntentPacket"]},
        {"agent_id": "research_condition_agent", "consumes": ["OutcomeMemoryPacket"], "produces": ["ResearchTaskPacket"], "cannot_produce": ["TerminalCommandPacket"]},
        {"agent_id": "strategy_dev_agent", "consumes": ["ResearchTaskPacket", "OutcomeMemoryPacket"], "produces": ["StrategyUpdatePacket"], "cannot_produce": ["TerminalCommandPacket"]},
    ]


def _information_planes() -> list[dict[str, Any]]:
    return [
        {
            "plane": "event_journal",
            "purpose": "Canonical append-only desk log every agent writes to and replays from.",
            "primary_packet": "AgentEventEnvelope",
            "path": "evidence_runs/agent_workflow_queue/agent-events.jsonl",
        },
        {
            "plane": "evidence_artifacts",
            "purpose": "Durable report files that hold backtests, replay results, receipts, and rollups.",
            "primary_packet": "source_refs",
            "path": "evidence_runs/**/**/*-report.json",
        },
        {
            "plane": "api_projection",
            "purpose": "Read-only cockpit display and external process view.",
            "primary_packet": "latest-state projections",
            "path": "/api/forex/dashboard",
        },
        {
            "plane": "terminal_mailbox",
            "purpose": "MT4/MT5 command outbox and receipt inbox only.",
            "primary_packet": "TerminalCommandPacket + TerminalReceiptPacket",
            "path": "evidence_runs/agent_workflow_mt4_mailbox/{commands,receipts}",
        },
        {
            "plane": "learning_memory",
            "purpose": "Outcome facts that future cycles and research agents learn from.",
            "primary_packet": "OutcomeMemoryPacket",
            "path": "evidence_runs/agent_memory/*.jsonl",
        },
        {
            "plane": "research_queue",
            "purpose": "Work queue for condition lab, walk-forward, strategy variants, and promotion/demotion.",
            "primary_packet": "ResearchTaskPacket",
            "path": "evidence_runs/agent_research_queue/*.jsonl",
        },
        {
            "plane": "strategy_dev_queue",
            "purpose": "Concrete replay, patch, promotion, demotion, and terminal-joinback work items.",
            "primary_packet": "StrategyDevWorkItemPacket",
            "path": "evidence_runs/strategy_dev_queue/*.jsonl",
        },
        {
            "plane": "strategy_patch_runner",
            "purpose": "Patch candidates, replay jobs, promotion/demotion reviews, and terminal blockers produced from strategy-dev items.",
            "primary_packet": "StrategyPatchDecisionPacket",
            "path": "evidence_runs/strategy_patch_runner/*.jsonl",
        },
        {
            "plane": "daily_learning_rollup",
            "purpose": "One trading-day record for the 30-day improvement window by agent, symbol, strategy, condition, PnL, and queued follow-up work.",
            "primary_packet": "DailyLearningRollupPacket",
            "path": "evidence_runs/daily_learning_rollup/*.jsonl",
        },
        {
            "plane": "session_autowake_runner",
            "purpose": "Market/session wake decisions, due agent-loop events, optional paper/demo cycle execution, and terminal blocker state.",
            "primary_packet": "SessionAutowakeEventPacket",
            "path": "evidence_runs/session_autowake_runner/*.jsonl",
        },
        {
            "plane": "terminal_receipt_watcher",
            "purpose": "Receipt/history folder watcher that triggers the ingest, memory, queue, rollup, and autowake refresh chain when terminal files change.",
            "primary_packet": "TerminalReceiptWatcherPacket",
            "path": "evidence_runs/terminal_receipt_watcher/*.jsonl",
        },
        {
            "plane": "terminal_bridge_supervisor",
            "purpose": "Bridge health view for heartbeat, mailbox folders, receipt freshness, history freshness, account snapshots, and terminal-run alerts.",
            "primary_packet": "TerminalBridgeSupervisorPacket",
            "path": "evidence_runs/terminal_bridge_supervisor/*-report.json",
        },
        {
            "plane": "mt4_terminal_activation",
            "purpose": "MT4 terminal discovery, EA staging, mailbox path alignment, and operator activation manifest.",
            "primary_packet": "MT4TerminalActivationPacket",
            "path": "evidence_runs/mt4_terminal_activation/*-report.json",
        },
        {
            "plane": "mt4_ping_roundtrip",
            "purpose": "One-file proof that the activated MT4 EA can see CAS commands and answer with heartbeat plus receipt JSON.",
            "primary_packet": "MT4PingRoundtripPacket",
            "path": "evidence_runs/mt4_ping_roundtrip/*-report.json",
        },
        {
            "plane": "mt4_terminal_session_verifier",
            "purpose": "One operator-level report that runs activation, ping, supervisor, watcher, and downstream evidence refresh checks.",
            "primary_packet": "MT4TerminalSessionVerifierPacket",
            "path": "evidence_runs/mt4_terminal_session_verifier/*-report.json",
        },
        {
            "plane": "mt4_history_exporter",
            "purpose": "Terminal-side MT4 closed-history export files that feed terminal history ingest, memory, daily rollups, and strategy learning.",
            "primary_packet": "MT4HistoryExporterPacket",
            "path": "MQL4/Files/CASForexMailbox/history/cas_forex_closed_history.json",
        },
        {
            "plane": "mt4_history_export_verifier",
            "purpose": "Verifier report proving whether MT4 closed-history export files exist and are ingest-compatible.",
            "primary_packet": "MT4HistoryExportVerifierPacket",
            "path": "evidence_runs/mt4_history_export_verifier/*-report.json",
        },
        {
            "plane": "mt5_terminal_api_verifier",
            "purpose": "Read-only proof that the local MT5 terminal API can authenticate to the demo broker account and return account/position state.",
            "primary_packet": "MT5TerminalApiVerifierPacket",
            "path": "evidence_runs/mt5_terminal_api_verifier/*-report.json",
        },
        {
            "plane": "mt5_paper_execution_verifier",
            "purpose": "Layered proof that CAS Forex can build, check, and explicitly send a demo/paper MT5 order request through MT5Bridge.",
            "primary_packet": "MT5PaperExecutionVerifierPacket",
            "path": "evidence_runs/mt5_paper_execution_verifier/*-report.json",
        },
        {
            "plane": "mt5_deal_history_ingest",
            "purpose": "Read-only MT5 account-history pull that exports closed demo deals and joins them into terminal-history memory updates.",
            "primary_packet": "MT5DealHistoryIngestPacket",
            "path": "evidence_runs/mt5_deal_history_ingest/*-report.json",
        },
        {
            "plane": "terminal_position_reconciliation",
            "purpose": "Read-only reconciliation between CAS memory, terminal receipts, open positions, account snapshots, and closed-history ingest.",
            "primary_packet": "TerminalPositionReconciliationPacket",
            "path": "evidence_runs/terminal_position_reconciliation/*-report.json",
        },
        {
            "plane": "terminal_operability_verifier",
            "purpose": "Top-level go/no-go report bundling terminal session, heartbeat, receipts, history export, position reconciliation, runtime gates, and operator next actions.",
            "primary_packet": "TerminalOperabilityVerifierPacket",
            "path": "evidence_runs/terminal_operability_verifier/*-report.json",
        },
    ]


def _event_envelope() -> dict[str, Any]:
    return {
        "schema": "cas_forex_agent_event.v1",
        "path": "evidence_runs/agent_workflow_queue/agent-events.jsonl",
        "required_fields": [
            "schema",
            "event_id",
            "cycle_id",
            "parent_event_id",
            "created_at",
            "producer_agent_id",
            "consumer_agent_ids",
            "event_type",
            "subject",
            "symbol",
            "timeframe",
            "strategy_setting",
            "priority",
            "ttl_seconds",
            "idempotency_key",
            "correlation_id",
            "source_refs",
            "payload",
            "status",
            "claim_boundary",
        ],
        "example_event_types": [
            "AGENT_CONTEXT_READY",
            "ROUTE_INTENT_CREATED",
            "OVERSEER_DECISION_CREATED",
            "TERMINAL_COMMAND_WRITTEN",
            "TERMINAL_RECEIPT_RECEIVED",
            "OUTCOME_MEMORY_WRITTEN",
            "RESEARCH_TASK_QUEUED",
        ],
        "idempotency_rule": "producer_agent_id|symbol|timeframe|action|cycle_id",
        "plain_english": "Every message gets a timestamped wrapper so agents can replay who said what, when, why, and from which evidence.",
    }


def _canonical_packets() -> list[dict[str, Any]]:
    return [
        {
            "packet_name": "AgentContextPacket",
            "purpose": "One shared snapshot all agents read before producing anything.",
            "required_fields": ["cycle_id", "as_of", "session_state", "market_snapshot_ref", "account_snapshot_ref", "open_exposure", "runtime_gate_snapshot", "evidence_refs"],
            "storage_target": "evidence_runs/agent_workflow_queue/context/*.json",
        },
        {
            "packet_name": "RouteIntentPacket",
            "purpose": "A proposed trade or management action from a trading agent.",
            "required_fields": ["intent_id", "cycle_id", "agent_id", "symbol", "timeframe", "strategy_setting", "action", "direction", "lot_size", "entry_price", "stop_loss", "take_profit", "confidence", "evidence_score", "evidence_refs", "order_request", "conflict_key", "expires_at"],
            "storage_target": "evidence_runs/agent_workflow_queue/route_intents/*.json",
        },
        {
            "packet_name": "OverseerDecisionPacket",
            "purpose": "The only packet that can approve/reject/scale a route intent.",
            "required_fields": ["decision_id", "intent_id", "decision_state", "approved", "reasons", "approval_packet_id", "approval_packet_hash", "conflict_key", "blocking_command_id", "command_ready", "required_receipt_before_next_cycle"],
            "storage_target": "evidence_runs/agent_workflow_queue/overseer_decisions/*.json",
        },
        {
            "packet_name": "TerminalCommandPacket",
            "purpose": "Command written to MT4/MT5 bridge from an approved route.",
            "required_fields": ["command_id", "cycle_id", "intent_id", "decision_id", "approval_packet_hash", "broker_mode", "command_type", "order", "idempotency_key", "expires_at", "requires_receipt_by", "expected_receipt_schema", "runtime_gate_snapshot", "raw_request_hash"],
            "storage_target": "evidence_runs/agent_workflow_mt4_mailbox/commands/*.json",
        },
        {
            "packet_name": "TerminalReceiptPacket",
            "purpose": "What the terminal says happened after a command.",
            "required_fields": ["receipt_id", "command_id", "cycle_id", "intent_id", "decision_id", "status", "receipt_validation_status", "terminal_time", "terminal_name", "terminal_build", "account_id_hash", "server", "broker_mode", "live_mode", "live_trading_allowed", "raw_request_hash", "raw_response_hash", "broker_ticket", "filled_price", "filled_volume", "slippage_pips", "commission", "swap", "error_code", "account_snapshot", "reconcile_status"],
            "storage_target": "evidence_runs/agent_workflow_mt4_mailbox/receipts/*.json",
        },
        {
            "packet_name": "OutcomeMemoryPacket",
            "purpose": "Post-action memory record used by future trading and research cycles.",
            "required_fields": ["memory_id", "cycle_id", "intent_id", "decision_id", "command_id", "receipt_id", "symbol", "timeframe", "strategy_setting", "condition_snapshot_open", "condition_snapshot_close", "profit_loss_r", "profit_loss_pips", "mae", "mfe", "close_reason", "outcome_label", "promotion_signal", "demotion_flags"],
            "storage_target": "evidence_runs/agent_memory/*.jsonl",
        },
        {
            "packet_name": "ResearchTaskPacket",
            "purpose": "Task packet for condition lab, walk-forward, replay, and strategy-dev work.",
            "required_fields": ["task_id", "source_memory_ids", "research_question", "symbols", "timeframes", "families", "priority", "success_metric"],
            "storage_target": "evidence_runs/agent_research_queue/*.jsonl",
        },
        {
            "packet_name": "StrategyDevWorkItemPacket",
            "purpose": "Concrete replay, patch, promotion, demotion, and terminal-joinback work item for the strategy-development agent.",
            "required_fields": ["item_id", "item_type", "priority", "status", "source_task_ids", "source_memory_ids", "hypothesis", "proposed_change", "replay_request", "promotion_review", "acceptance_checks"],
            "storage_target": "evidence_runs/strategy_dev_queue/*.jsonl",
        },
        {
            "packet_name": "StrategyPatchDecisionPacket",
            "purpose": "Patch, replay, promotion, demotion, or terminal-input decision emitted from a strategy-development work item.",
            "required_fields": ["decision_id", "decision_type", "priority", "status", "source_item_id", "patch_target", "replay_job", "promotion_review", "blocked_by", "acceptance_checks"],
            "storage_target": "evidence_runs/strategy_patch_runner/*.jsonl",
        },
        {
            "packet_name": "DailyLearningRollupPacket",
            "purpose": "One 30-day-window daily learning record summarizing routes, PnL, blockers, decisions, and follow-up work.",
            "required_fields": ["trading_date", "day_index", "route_count", "win_count", "loss_count", "net_profit_loss_account", "by_agent", "by_symbol", "by_strategy", "by_condition_cell", "queued_follow_up_work", "terminal_blockers", "chain_verified"],
            "storage_target": "evidence_runs/daily_learning_rollup/*.jsonl",
        },
        {
            "packet_name": "SessionAutowakeEventPacket",
            "purpose": "One evaluated autowake event with due/not-due status, active session, terminal blockers, and paper/demo cycle request decision.",
            "required_fields": ["event_id", "action", "trigger", "due", "status", "decision", "requested_agent_cycle", "terminal_blocked", "active_session", "reasons"],
            "storage_target": "evidence_runs/session_autowake_runner/*.jsonl",
        },
        {
            "packet_name": "TerminalReceiptWatcherPacket",
            "purpose": "One watched terminal receipt/history file change plus the refresh-chain decision it triggered.",
            "required_fields": ["schema", "change_status", "file_role", "path", "sha256", "previous_sha256", "size_bytes", "modified_at"],
            "storage_target": "evidence_runs/terminal_receipt_watcher/*.jsonl",
        },
        {
            "packet_name": "TerminalBridgeSupervisorPacket",
            "purpose": "One bridge health report with heartbeat, mailbox, receipt, history, account snapshot, and alert state.",
            "required_fields": ["supervisor_status", "heartbeat", "mailbox", "commands", "receipts", "history", "event_journal", "account_snapshot", "alerts", "next_action"],
            "storage_target": "evidence_runs/terminal_bridge_supervisor/*-report.json",
        },
        {
            "packet_name": "MT4TerminalActivationPacket",
            "purpose": "One MT4 activation report with terminal candidates, EA install state, mailbox path alignment, settings, and next action.",
            "required_fields": ["activation_status", "ea_source", "candidate_terminals", "selected_terminal", "settings", "path_alignment", "summary", "next_action"],
            "storage_target": "evidence_runs/mt4_terminal_activation/*-report.json",
        },
        {
            "packet_name": "MT4PingRoundtripPacket",
            "purpose": "One ping report proving whether CAS wrote a ping command and MT4 answered with heartbeat plus receipt JSON.",
            "required_fields": ["roundtrip_status", "mailbox_dir", "command", "heartbeat", "receipt", "summary", "next_action"],
            "storage_target": "evidence_runs/mt4_ping_roundtrip/*-report.json",
        },
        {
            "packet_name": "MT4TerminalSessionVerifierPacket",
            "purpose": "One session report showing activation, ping, supervisor, watcher, refresh-chain, and next operator action.",
            "required_fields": ["session_status", "mailbox_dir", "step_results", "child_reports", "summary", "next_action"],
            "storage_target": "evidence_runs/mt4_terminal_session_verifier/*-report.json",
        },
        {
            "packet_name": "MT4HistoryExporterPacket",
            "purpose": "Closed MT4 account-history rows exported by CASForexHistoryExporterEA.mq4 for terminal-history ingest.",
            "required_fields": ["schema", "terminal", "account_id_hash", "broker_mode", "exported_at", "history_records", "summary", "claim_boundary"],
            "storage_target": "MQL4/Files/CASForexMailbox/history/cas_forex_closed_history.json",
        },
        {
            "packet_name": "MT4HistoryExportVerifierPacket",
            "purpose": "One report proving whether the MT4 history export exists, parses, matches schema, and feeds terminal_history_ingest.",
            "required_fields": ["verifier_status", "ea_source", "mailbox_dir", "history_export", "exporter_status", "ingest_report", "summary", "next_action"],
            "storage_target": "evidence_runs/mt4_history_export_verifier/*-report.json",
        },
        {
            "packet_name": "MT5TerminalApiVerifierPacket",
            "purpose": "One report proving whether the local MT5 Python API can see the broker/demo account snapshot, terminal connection, and open positions.",
            "required_fields": ["verifier_status", "trading_date", "mt5_path", "probe", "terminal_snapshot", "summary", "claim_boundary", "next_action"],
            "storage_target": "evidence_runs/mt5_terminal_api_verifier/*-report.json",
        },
        {
            "packet_name": "MT5PaperExecutionVerifierPacket",
            "purpose": "One report proving MT5 demo/paper request build, order_check, optional explicitly confirmed demo send, close attempt, and receipt facts.",
            "required_fields": ["verifier_status", "trading_date", "execution_controls", "api_verifier", "terminal_snapshot", "order", "mt5_request", "order_check", "execution_result", "summary", "claim_boundary", "next_action"],
            "storage_target": "evidence_runs/mt5_paper_execution_verifier/*-report.json",
        },
        {
            "packet_name": "MT5DealHistoryIngestPacket",
            "purpose": "One report proving closed MT5 demo deals were read from account history, exported to terminal history, and joined to CAS memory when a broker-ticket/command link exists.",
            "required_fields": ["ingest_status", "query", "terminal_snapshot", "history_export_path", "raw_deal_count", "history_records", "terminal_history_ingest", "summary", "claim_boundary", "next_action"],
            "storage_target": "evidence_runs/mt5_deal_history_ingest/*-report.json",
        },
        {
            "packet_name": "TerminalPositionReconciliationPacket",
            "purpose": "One report matching terminal open positions and closed-history rows against CAS memory, receipts, and account snapshots.",
            "required_fields": ["reconciliation_status", "source_reports", "summary", "terminal_open_positions", "cas_open_positions", "reconciled_open_positions", "unmatched_open_positions", "checks", "next_action"],
            "storage_target": "evidence_runs/terminal_position_reconciliation/*-report.json",
        },
        {
            "packet_name": "TerminalOperabilityVerifierPacket",
            "purpose": "One go/no-go report proving whether the terminal lane is operable and whether live-order, broker ACCEPT, and money-movement gates are authorized.",
            "required_fields": ["operability_status", "source_reports", "summary", "checks", "go_no_go", "runtime_gate_decisions", "next_action"],
            "storage_target": "evidence_runs/terminal_operability_verifier/*-report.json",
        },
    ]


def _flow_stages() -> list[dict[str, Any]]:
    return [
        {"stage": 1, "name": "wake", "producer": "session_autowake_agent", "consumer": "all_agents", "packet": "AgentContextPacket"},
        {"stage": 2, "name": "scalp_proposal", "producer": "micro_scalp_agent", "consumer": "overseer_agent", "packet": "RouteIntentPacket"},
        {"stage": 3, "name": "intraday_proposal", "producer": "hourly_intraday_agent", "consumer": "overseer_agent", "packet": "RouteIntentPacket"},
        {"stage": 4, "name": "approval", "producer": "overseer_agent", "consumer": "terminal_bridge_agent", "packet": "OverseerDecisionPacket"},
        {"stage": 5, "name": "terminal_command", "producer": "terminal_bridge_agent", "consumer": "mt4_or_mt5_terminal", "packet": "TerminalCommandPacket"},
        {"stage": 6, "name": "terminal_receipt", "producer": "mt4_or_mt5_terminal", "consumer": "terminal_bridge_agent", "packet": "TerminalReceiptPacket"},
        {"stage": 7, "name": "memory_write", "producer": "audit_memory_agent", "consumer": "research_and_trading_agents", "packet": "OutcomeMemoryPacket"},
        {"stage": 8, "name": "research_queue", "producer": "research_condition_agent", "consumer": "strategy_dev_agent", "packet": "ResearchTaskPacket"},
        {"stage": 9, "name": "strategy_dev_queue", "producer": "strategy_dev_agent", "consumer": "strategy_patch_runner", "packet": "StrategyDevWorkItemPacket"},
        {"stage": 10, "name": "strategy_patch_runner", "producer": "strategy_patch_runner", "consumer": "daily_learning_rollup", "packet": "StrategyPatchDecisionPacket"},
        {"stage": 11, "name": "daily_learning_rollup", "producer": "daily_learning_rollup", "consumer": "session_autowake_runner", "packet": "DailyLearningRollupPacket"},
        {"stage": 12, "name": "session_autowake", "producer": "session_autowake_runner", "consumer": "agent_workflow_cycle", "packet": "SessionAutowakeEventPacket"},
        {"stage": 13, "name": "terminal_receipt_watcher", "producer": "terminal_receipt_watcher", "consumer": "ingest_memory_learning_chain", "packet": "TerminalReceiptWatcherPacket"},
        {"stage": 14, "name": "terminal_bridge_supervisor", "producer": "terminal_bridge_supervisor", "consumer": "owner_operator_and_activation_runner", "packet": "TerminalBridgeSupervisorPacket"},
        {"stage": 15, "name": "mt4_terminal_activation", "producer": "mt4_terminal_activation", "consumer": "owner_operator_and_roundtrip_verifier", "packet": "MT4TerminalActivationPacket"},
        {"stage": 16, "name": "mt4_ping_roundtrip", "producer": "mt4_ping_roundtrip", "consumer": "supervisor_watcher_ingest_refresh_chain", "packet": "MT4PingRoundtripPacket"},
        {"stage": 17, "name": "mt4_terminal_session_verifier", "producer": "mt4_terminal_session_verifier", "consumer": "owner_operator_and_history_exporter", "packet": "MT4TerminalSessionVerifierPacket"},
        {"stage": 18, "name": "mt4_history_exporter", "producer": "CASForexHistoryExporterEA.mq4", "consumer": "terminal_history_ingest", "packet": "MT4HistoryExporterPacket"},
        {"stage": 19, "name": "mt4_history_export_verifier", "producer": "mt4_history_export_verifier", "consumer": "owner_operator_and_position_reconciliation", "packet": "MT4HistoryExportVerifierPacket"},
        {"stage": 20, "name": "terminal_position_reconciliation", "producer": "terminal_position_reconciliation", "consumer": "owner_operator_and_operability_verifier", "packet": "TerminalPositionReconciliationPacket"},
        {"stage": 21, "name": "mt5_terminal_api_verifier", "producer": "mt5_terminal_api_verifier", "consumer": "terminal_operability_verifier", "packet": "MT5TerminalApiVerifierPacket"},
        {"stage": 22, "name": "mt5_paper_execution_verifier", "producer": "mt5_paper_execution_verifier", "consumer": "mt5_deal_history_ingest", "packet": "MT5PaperExecutionVerifierPacket"},
        {"stage": 23, "name": "mt5_deal_history_ingest", "producer": "mt5_deal_history_ingest", "consumer": "agent_memory_daily_learning_and_operability", "packet": "MT5DealHistoryIngestPacket"},
        {"stage": 24, "name": "terminal_operability_verifier", "producer": "terminal_operability_verifier", "consumer": "owner_operator_and_live_gate_review", "packet": "TerminalOperabilityVerifierPacket"},
    ]


def _state_machine() -> list[dict[str, str]]:
    return [
        {"from": "CONTEXT_READY", "to": "INTENT_PROPOSED", "by": "micro_scalp_agent/hourly_intraday_agent"},
        {"from": "INTENT_PROPOSED", "to": "APPROVED_FOR_COMMAND", "by": "overseer_agent"},
        {"from": "INTENT_PROPOSED", "to": "QUEUED_AWAITING_RECEIPT", "by": "overseer_agent"},
        {"from": "INTENT_PROPOSED", "to": "REJECTED_UNSUPPORTED_OR_STALE", "by": "overseer_agent"},
        {"from": "APPROVED_FOR_COMMAND", "to": "COMMAND_WRITTEN", "by": "terminal_bridge_agent"},
        {"from": "COMMAND_WRITTEN", "to": "RECEIPT_PENDING", "by": "terminal_bridge_agent"},
        {"from": "RECEIPT_PENDING", "to": "RECEIPT_VERIFIED", "by": "terminal_bridge_agent"},
        {"from": "RECEIPT_VERIFIED", "to": "RECONCILED", "by": "account_reconciliation"},
        {"from": "RECONCILED", "to": "MEMORY_SAVED", "by": "audit_memory_agent"},
        {"from": "MEMORY_SAVED", "to": "RESEARCH_QUEUED", "by": "research_condition_agent"},
        {"from": "RESEARCH_QUEUED", "to": "STRATEGY_DEV_QUEUED", "by": "strategy_dev_agent"},
        {"from": "STRATEGY_DEV_QUEUED", "to": "PATCH_OR_REPLAY_REQUESTED", "by": "strategy_patch_runner"},
        {"from": "PATCH_OR_REPLAY_REQUESTED", "to": "PATCH_REPLAY_DECISION_WRITTEN", "by": "strategy_patch_runner"},
        {"from": "PATCH_REPLAY_DECISION_WRITTEN", "to": "DAILY_ROLLUP_WRITTEN", "by": "daily_learning_rollup"},
        {"from": "DAILY_ROLLUP_WRITTEN", "to": "SESSION_AUTOWAKE_READY", "by": "session_autowake_runner"},
        {"from": "SESSION_AUTOWAKE_READY", "to": "TERMINAL_WATCHER_READY", "by": "terminal_receipt_watcher"},
        {"from": "TERMINAL_FILE_CHANGED", "to": "EVIDENCE_REFRESH_CHAIN_RAN", "by": "terminal_receipt_watcher"},
        {"from": "TERMINAL_WATCHER_READY", "to": "TERMINAL_BRIDGE_SUPERVISED", "by": "terminal_bridge_supervisor"},
        {"from": "TERMINAL_BRIDGE_SUPERVISED", "to": "MT4_TERMINAL_ACTIVATION_STAGED", "by": "mt4_terminal_activation"},
        {"from": "MT4_TERMINAL_ACTIVATION_STAGED", "to": "MT4_PING_ROUNDTRIP_PROVEN", "by": "mt4_ping_roundtrip"},
        {"from": "MT4_PING_ROUNDTRIP_PROVEN", "to": "MT4_TERMINAL_SESSION_VERIFIED", "by": "mt4_terminal_session_verifier"},
        {"from": "MT4_TERMINAL_SESSION_VERIFIED", "to": "MT4_CLOSED_HISTORY_EXPORTED", "by": "CASForexHistoryExporterEA.mq4"},
        {"from": "MT4_CLOSED_HISTORY_EXPORTED", "to": "MT4_HISTORY_EXPORT_VERIFIED", "by": "mt4_history_export_verifier"},
        {"from": "MT4_HISTORY_EXPORT_VERIFIED", "to": "TERMINAL_POSITIONS_RECONCILED", "by": "terminal_position_reconciliation"},
        {"from": "TERMINAL_POSITIONS_RECONCILED", "to": "TERMINAL_OPERABILITY_VERIFIED", "by": "terminal_operability_verifier"},
        {"from": "RECEIPT_TIMEOUT", "to": "TERMINAL_LOCKED_FOR_SYMBOL", "by": "terminal_bridge_agent"},
        {"from": "RECONCILIATION_FAILED", "to": "TERMINAL_LOCKED_FOR_SYMBOL", "by": "account_reconciliation"},
    ]


def _receipt_and_reconciliation_lifecycle() -> list[dict[str, str]]:
    return [
        {"state": "APPROVED_FOR_COMMAND", "plain_english": "Overseer allowed the route to become a terminal command."},
        {"state": "COMMAND_WRITTEN", "plain_english": "The bridge wrote the command file into the MT4/MT5 mailbox."},
        {"state": "RECEIPT_PENDING", "plain_english": "CAS Forex is waiting for MetaTrader to answer what happened."},
        {"state": "RECEIPT_VERIFIED", "plain_english": "The receipt links back to the command and passes schema/hash/terminal checks."},
        {"state": "RECONCILED", "plain_english": "The receipt agrees with the internal ledger, account snapshot, symbol, order count, and position state."},
        {"state": "NEXT_CYCLE_ALLOWED", "plain_english": "The same conflict key can receive another open/add command."},
        {"state": "RECEIPT_TIMEOUT", "plain_english": "The terminal did not return a usable receipt before the deadline."},
        {"state": "RECEIPT_MISMATCH", "plain_english": "The terminal receipt does not match the command or account context."},
        {"state": "RECONCILIATION_FAILED", "plain_english": "The broker/terminal facts and internal ledger do not agree."},
        {"state": "TERMINAL_LOCKED_FOR_SYMBOL", "plain_english": "The affected symbol waits until the command/receipt mismatch is fixed."},
    ]


def _learning_memory_contracts() -> list[dict[str, Any]]:
    return [
        {
            "schema": "cas_forex_agent_outcome_memory.v1",
            "purpose": "Save each route proposal, approval/rejection, command linkage, available receipt linkage, and open/close snapshots into a reusable learning row.",
            "required_fields": [
                "memory_id",
                "cycle_id",
                "agent_id",
                "intent_id",
                "decision_id",
                "command_id",
                "receipt_id",
                "action",
                "decision",
                "decision_status",
                "symbol",
                "timeframe",
                "strategy_setting",
                "condition_snapshot_open",
                "condition_snapshot_close",
                "outcome_label",
                "learning_status",
                "source_event_ids",
            ],
        },
        {
            "schema": "cas_forex_trade_outcome_memory.v1",
            "purpose": "Save what happened after the route opened/closed so agents can improve future decisions.",
            "required_fields": [
                "trace_id",
                "intent_id",
                "decision_id",
                "command_id",
                "receipt_id",
                "broker_mode",
                "terminal_status",
                "broker_ticket",
                "opened_at",
                "closed_at",
                "fill_price",
                "exit_price",
                "profit_loss_account",
                "profit_loss_pips",
                "profit_loss_r",
                "spread_paid_pips",
                "slippage_pips",
                "max_favorable_excursion_pips",
                "max_adverse_excursion_pips",
                "close_reason",
                "outcome_label",
                "condition_snapshot_open",
                "condition_snapshot_close",
            ],
        },
        {
            "schema": "cas_forex_daily_learning_rollup.v1",
            "purpose": "Summarize the trading day and feed the 30-day improvement window.",
            "required_fields": [
                "date",
                "day_index",
                "route_count",
                "approved_count",
                "rejected_count",
                "executed_count",
                "closed_count",
                "win_count",
                "loss_count",
                "net_profit_r",
                "profit_factor",
                "expectancy_r",
                "max_drawdown_pct",
                "by_agent",
                "by_symbol",
                "by_strategy",
                "by_condition_cell",
                "promotion_candidates",
                "demotion_flags",
                "research_tasks",
                "strategy_dev_tasks",
                "chain_verified",
            ],
        },
        {
            "schema": "cas_forex_strategy_dev_work_item.v1",
            "purpose": "Turn research tasks and closed PnL memory into explicit replay, patch, promotion, demotion, or terminal-joinback work items.",
            "required_fields": [
                "item_id",
                "item_type",
                "priority",
                "status",
                "source_task_ids",
                "source_memory_ids",
                "hypothesis",
                "proposed_change",
                "replay_request",
                "promotion_review",
                "acceptance_checks",
            ],
        },
        {
            "schema": "cas_forex_strategy_patch_decision.v1",
            "purpose": "Turn strategy-dev work items into patch candidates, replay jobs, promotion/demotion reviews, or terminal-input blockers.",
            "required_fields": [
                "decision_id",
                "decision_type",
                "priority",
                "status",
                "source_item_id",
                "source_item_type",
                "patch_target",
                "replay_job",
                "promotion_review",
                "blocked_by",
                "acceptance_checks",
            ],
        },
        {
            "schema": "cas_forex_session_autowake_event.v1",
            "purpose": "Evaluate market/session time, daily rollup state, terminal blockers, and due agent-loop events before running a paper/demo cycle.",
            "required_fields": [
                "event_id",
                "action",
                "trigger",
                "due",
                "status",
                "decision",
                "requested_agent_cycle",
                "terminal_blocked",
                "active_session",
                "reasons",
            ],
        },
        {
            "schema": "cas_forex_terminal_file_fingerprint.v1",
            "purpose": "Detect new, changed, or deleted terminal receipt/history files and trigger the CAS Forex evidence refresh chain.",
            "required_fields": [
                "schema",
                "change_status",
                "file_role",
                "path",
                "sha256",
                "previous_sha256",
                "size_bytes",
                "modified_at",
            ],
        },
        {
            "schema": "cas_forex_terminal_bridge_supervisor.v1",
            "purpose": "Observe bridge heartbeat, mailbox health, receipt freshness, history freshness, account snapshots, and terminal-run alerts before terminal activation.",
            "required_fields": [
                "supervisor_status",
                "heartbeat",
                "mailbox",
                "commands",
                "receipts",
                "history",
                "event_journal",
                "account_snapshot",
                "alerts",
                "next_action",
            ],
        },
        {
            "schema": "cas_forex_mt4_terminal_activation.v1",
            "purpose": "Discover/stage MT4, copy the EA into MQL4/Experts, align the MT4 file sandbox mailbox, and write the operator manifest.",
            "required_fields": [
                "activation_status",
                "ea_source",
                "candidate_terminals",
                "selected_terminal",
                "settings",
                "path_alignment",
                "summary",
                "next_action",
            ],
        },
        {
            "schema": "cas_forex_mt4_ping_roundtrip.v1",
            "purpose": "Write or inspect one MT4 ping and prove whether heartbeat plus receipt JSON came back from the attached terminal.",
            "required_fields": [
                "roundtrip_status",
                "mailbox_dir",
                "command",
                "heartbeat",
                "receipt",
                "summary",
                "next_action",
            ],
        },
        {
            "schema": "cas_forex_mt4_terminal_session_verifier.v1",
            "purpose": "Run activation, ping, supervisor, watcher, and downstream refresh checks as one operator session report.",
            "required_fields": [
                "session_status",
                "step_results",
                "child_reports",
                "summary",
                "next_action",
            ],
        },
        {
            "schema": "cas_forex_mt4_closed_history_export.v1",
            "purpose": "Export closed MT4 Account History rows into a CAS-shaped file for terminal-history ingest and memory learning.",
            "required_fields": [
                "schema",
                "terminal",
                "account_id_hash",
                "broker_mode",
                "exported_at",
                "history_records",
                "summary",
                "claim_boundary",
            ],
        },
        {
            "schema": "cas_forex_mt4_history_export_verifier.v1",
            "purpose": "Verify MT4 closed-history export presence, schema, row count, status file, and terminal-history ingest compatibility.",
            "required_fields": [
                "verifier_status",
                "ea_source",
                "mailbox_dir",
                "history_export",
                "exporter_status",
                "ingest_report",
                "summary",
                "next_action",
            ],
        },
        {
            "schema": "cas_forex_mt5_terminal_api_verifier.v1",
            "purpose": "Verify local MT5 terminal API access to the broker/demo account snapshot, terminal status, and open-position state.",
            "required_fields": [
                "verifier_status",
                "trading_date",
                "mt5_path",
                "probe",
                "terminal_snapshot",
                "summary",
                "claim_boundary",
                "next_action",
            ],
        },
        {
            "schema": "cas_forex_mt5_paper_execution_verifier.v1",
            "purpose": "Verify MT5 demo/paper request build, order_check, optional explicitly confirmed demo send, close attempt, and receipt facts.",
            "required_fields": [
                "verifier_status",
                "trading_date",
                "execution_controls",
                "api_verifier",
                "terminal_snapshot",
                "order",
                "mt5_request",
                "order_check",
                "execution_result",
                "summary",
                "claim_boundary",
                "next_action",
            ],
        },
        {
            "schema": "cas_forex_mt5_deal_history_ingest.v1",
            "purpose": "Read closed MT5 demo account-history deals, export closed-position rows, and join them to CAS memory through terminal_history_ingest.",
            "required_fields": [
                "ingest_status",
                "query",
                "terminal_snapshot",
                "history_export_path",
                "raw_deal_count",
                "history_records",
                "terminal_history_ingest",
                "summary",
                "claim_boundary",
                "next_action",
            ],
        },
        {
            "schema": "cas_forex_terminal_position_reconciliation.v1",
            "purpose": "Compare CAS memory, terminal receipts, account snapshots, open positions, and closed-history rows before an operating session is trusted.",
            "required_fields": [
                "reconciliation_status",
                "source_reports",
                "summary",
                "terminal_open_positions",
                "cas_open_positions",
                "reconciled_open_positions",
                "unmatched_open_positions",
                "checks",
                "next_action",
            ],
        },
        {
            "schema": "cas_forex_terminal_operability_verifier.v1",
            "purpose": "Bundle MT4 session evidence, MT5 terminal API evidence, heartbeat, receipts, history export, position reconciliation, runtime gates, and operator next actions into one go/no-go report.",
            "required_fields": [
                "operability_status",
                "source_reports",
                "summary",
                "checks",
                "go_no_go",
                "runtime_gate_decisions",
                "next_action",
            ],
        },
    ]


def _main_bottlenecks() -> list[dict[str, str]]:
    return [
        {
            "bottleneck_id": "latest_only_cycle",
            "plain_english": "The event feed now exists; the next workers must consume it for receipt-gated replay instead of reading only latest reports.",
            "fix_target": "cas_forex/agent_message_bus.py",
        },
        {
            "bottleneck_id": "receipt_joinback",
            "plain_english": "Receipt ingest, overseer consumption, and MT4 EA receipt-writer source now exist; the remaining terminal work is compile/attach/run verification inside MT4 against the shared mailbox.",
            "fix_target": "mt4/Experts/CASForexBridgeEA.mq4",
        },
        {
            "bottleneck_id": "outcome_memory_gap",
            "plain_english": "MT5 demo deal-history ingest now joins one closed PnL row into memory; the remaining operational gap is making every agent workflow execution produce the same broker-ticket/history/memory chain automatically.",
            "fix_target": "cas_forex/agent_workflow.py",
        },
        {
            "bottleneck_id": "mt5_agent_execution_loop_gap",
            "plain_english": "The one-off MT5 demo execution and closed-deal memory chain is proven; the next gap is letting the scheduled agent workflow use that same MT5 path for future paper/demo route commands.",
            "fix_target": "cas_forex/agent_workflow.py",
        },
        {
            "bottleneck_id": "mt5_closed_deal_learning_gap",
            "plain_english": "The first MT5 closed deal is in memory and daily rollup; the next evidence gap is repeating that loop across real session windows and strategy-selected symbols instead of a single verifier trade.",
            "fix_target": "evidence_runs/daily_learning_rollup",
        },
        {
            "bottleneck_id": "coarse_conflict_key",
            "plain_english": "MT4 activation now stages/discovers the terminal folder; the remaining gap is proving a live heartbeat and ping receipt from the attached terminal.",
            "fix_target": "cas_forex/mt4_terminal_activation.py",
        },
        {
            "bottleneck_id": "heartbeat_roundtrip",
            "plain_english": "The ping verifier now exists; the remaining gap is an attached MT4 terminal that actually writes heartbeat and receipt JSON.",
            "fix_target": "evidence_runs/mt4_ping_roundtrip",
        },
        {
            "bottleneck_id": "closed_history_export_gap",
            "plain_english": "The MT4 closed-history exporter source and verifier now exist; the remaining gap is a real attached MT4 terminal producing closed-history exports.",
            "fix_target": "MQL4/Files/CASForexMailbox/history/cas_forex_closed_history.json",
        },
        {
            "bottleneck_id": "position_reconciliation_gap",
            "plain_english": "The terminal position reconciliation report now exists; the remaining gap is real attached-terminal evidence with heartbeat, receipt account snapshots, and open/closed position rows.",
            "fix_target": "cas_forex/terminal_position_reconciliation.py",
        },
        {
            "bottleneck_id": "terminal_operability_verifier_gap",
            "plain_english": "The terminal operability verifier now sees verified MT5 API evidence, but it still needs either a proven MT5 paper/demo execution lane or a live MT4 EA mailbox heartbeat/history lane before the terminal lane can be called fully operable.",
            "fix_target": "cas_forex/terminal_operability_verifier.py",
        },
        {
            "bottleneck_id": "real_mt4_terminal_evidence_gap",
            "plain_english": "CAS Forex still needs a real attached MT4 terminal to write heartbeat, receipt, account snapshot, open-position, and closed-history evidence into the mailbox.",
            "fix_target": "MQL4/Files/CASForexMailbox/{heartbeat.json,receipts,history}",
        },
        {
            "bottleneck_id": "dashboard_not_agent_bus",
            "plain_english": "Agents should not coordinate by scraping the dashboard; the dashboard should display API projections from the event journal.",
            "fix_target": "api/data.py",
        },
    ]


def _storage_and_api_targets() -> dict[str, Any]:
    return {
        "append_only_event_log": "evidence_runs/agent_workflow_queue/agent-events.jsonl",
        "latest_cycle_projection": "evidence_runs/agent_workflow_queue/agent-workflow-state.jsonl",
        "cycle_reports": "evidence_runs/agent_workflow_queue/agent-workflow-cycle-*-report.json",
        "mt4_mailbox": "evidence_runs/agent_workflow_mt4_mailbox/{commands,receipts}",
        "latest_api": "/api/forex/strategy/agent-workflow-cycle/latest",
        "flow_api": "/api/forex/strategy/agent-information-flow",
        "next_api_projections": [
            "/api/forex/strategy/agent-workflow-context/latest",
            "/api/forex/strategy/agent-workflow-events?cycle_id=&after_event_id=",
            "/api/forex/strategy/agent-workflow-intents/open",
            "/api/forex/strategy/agent-workflow-receipts/latest",
            "/api/forex/strategy/agent-memory/latest",
            "/api/forex/strategy/agent-research-queue/latest",
            "/api/forex/strategy/strategy-dev-queue/latest",
            "/api/forex/strategy/strategy-patch-runner/latest",
            "/api/forex/strategy/daily-learning-rollup/latest",
            "/api/forex/strategy/session-autowake/latest",
            "/api/forex/strategy/terminal-receipt-watcher/latest",
            "/api/forex/strategy/terminal-bridge-supervisor/latest",
            "/api/forex/strategy/mt4-terminal-activation/latest",
            "/api/forex/strategy/mt4-ping-roundtrip/latest",
            "/api/forex/strategy/mt4-terminal-session-verifier/latest",
            "/api/forex/strategy/mt4-history-export-verifier/latest",
            "/api/forex/strategy/mt5-terminal-api-verifier/latest",
            "/api/forex/strategy/mt5-paper-execution-verifier/latest",
            "/api/forex/strategy/mt5-deal-history-ingest/latest",
            "/api/forex/strategy/terminal-position-reconciliation/latest",
            "/api/forex/strategy/terminal-operability-verifier/latest",
            "/api/forex/strategy/terminal-history-ingest/latest",
            "/api/forex/terminal/mt4-mailbox/status",
            "/api/forex/reconciliation/terminal?cycle_id=",
        ],
        "dashboard_key": "agentInformationFlow",
        "ui_panel": "OptimizerPage Agentic Trading-Day Workflow",
    }


def _implementation_queue() -> list[dict[str, Any]]:
    return [
        {"priority": 1, "target_file": "cas_forex/agent_message_bus.py", "status": "COMPLETE", "plain_english": "Create typed append-only event journal helpers for every packet."},
        {"priority": 2, "target_file": "cas_forex/agent_context.py", "plain_english": "Build one context packet from market, account, runtime gates, open exposure, and evidence refs."},
        {"priority": 3, "target_file": "cas_forex/terminal_receipt_ingest.py", "status": "COMPLETE", "plain_english": "Read MT4/MT5 receipts and turn them into TerminalReceiptPacket records."},
        {"priority": 4, "target_file": "cas_forex/agent_overseer.py", "status": "COMPLETE", "plain_english": "Make duplicate opens wait for receipt/reconciliation instead of becoming another terminal command."},
        {"priority": 5, "target_file": "mt4/Experts/CASForexBridgeEA.mq4", "status": "SOURCE_READY_NEEDS_TERMINAL_VERIFY", "plain_english": "MT4 EA source reads command files and writes terminal receipt JSON; compile/attach/run it inside MT4 to verify terminal-side receipts."},
        {"priority": 6, "target_file": "cas_forex/agent_memory.py", "status": "COMPLETE_INITIAL", "plain_english": "Memory rows join route intent, overseer decision, terminal command, receipt facts, MT5 paper execution verifier seed rows, and terminal-history PnL updates."},
        {"priority": 7, "target_file": "cas_forex/agent_research_queue.py", "status": "COMPLETE", "plain_english": "Turn memory patterns into condition-lab, walk-forward, terminal-joinback, and strategy-development tasks."},
        {"priority": 8, "target_file": "cas_forex/terminal_history_ingest.py", "status": "COMPLETE_INITIAL", "plain_english": "Read MT4/MT5 exported close data so memory rows get PnL, pips, MAE/MFE, close reason, commission, and swap."},
        {"priority": 9, "target_file": "cas_forex/strategy_dev_queue.py", "status": "COMPLETE_INITIAL", "plain_english": "Turn completed research tasks and closed PnL memory rows into strategy patch candidates, replay requests, and promotion/demotion reviews."},
        {"priority": 10, "target_file": "cas_forex/strategy_patch_runner.py", "status": "COMPLETE_INITIAL", "plain_english": "Turn strategy-dev work items into patch candidates, replay jobs, promotion/demotion reviews, and terminal-input blockers."},
        {"priority": 11, "target_file": "cas_forex/daily_learning_rollup.py", "status": "COMPLETE_INITIAL", "plain_english": "Summarize each trading day into a 30-day improvement record by agent, symbol, strategy, condition, PnL, and queued follow-up work."},
        {"priority": 12, "target_file": "cas_forex/session_autowake_runner.py", "status": "COMPLETE_INITIAL", "plain_english": "Use the workflow plan and latest daily rollup to wake CAS Forex at market/session windows and optionally run one paper/demo agent cycle."},
        {"priority": 13, "target_file": "cas_forex/terminal_receipt_watcher.py", "status": "COMPLETE_INITIAL", "plain_english": "Watch terminal receipt/history folders and automatically rerun receipt ingest, history ingest, memory, queues, patch runner, rollup, and autowake reports when files arrive."},
        {"priority": 14, "target_file": "cas_forex/terminal_bridge_supervisor.py", "status": "COMPLETE_INITIAL", "plain_english": "Supervise MT4/MT5 bridge heartbeat, mailbox health, receipt freshness, history freshness, account snapshots, and terminal-run alerts."},
        {"priority": 15, "target_file": "cas_forex/mt4_terminal_activation.py", "status": "COMPLETE_INITIAL", "plain_english": "Discover/stage the actual MT4 terminal data folder, copy CASForexBridgeEA.mq4 to Experts, point MailboxRoot at the shared mailbox, and write an activation manifest/runbook."},
        {"priority": 16, "target_file": "cas_forex/mt4_ping_roundtrip.py", "status": "COMPLETE_INITIAL", "plain_english": "Write a ping into the activated MT4 mailbox, wait for heartbeat and receipt JSON, and report whether the EA is actually answering."},
        {"priority": 17, "target_file": "cas_forex/mt4_terminal_session_verifier.py", "status": "COMPLETE_INITIAL", "plain_english": "Bundle activation, ping, supervisor, watcher, receipt ingest, history ingest, memory, rollup, and autowake refresh into one operator session check."},
        {"priority": 18, "target_file": "mt4/Experts/CASForexHistoryExporterEA.mq4", "status": "SOURCE_READY_NEEDS_TERMINAL_ATTACH", "plain_english": "Export closed MT4 account-history rows into CAS Forex history files so memory and daily rollups can learn from completed PnL."},
        {"priority": 19, "target_file": "cas_forex/mt4_history_export_verifier.py", "status": "COMPLETE_INITIAL", "plain_english": "Verify that an attached MT4 terminal produced CASForexHistoryExporterEA.mq4 output in the activated mailbox history folder and that terminal_history_ingest can consume it."},
        {"priority": 20, "target_file": "cas_forex/mt5_terminal_api_verifier.py", "status": "COMPLETE_INITIAL", "plain_english": "Verify local MT5 Python API access to Hugosway-Demo account state, account snapshot, open positions, and broker receipt facts."},
        {"priority": 21, "target_file": "cas_forex/terminal_position_reconciliation.py", "status": "COMPLETE_INITIAL", "plain_english": "Match open terminal positions, CAS commands, receipts, closed-history rows, ledger state, and active exposure before any operating session can be trusted."},
        {"priority": 22, "target_file": "cas_forex/terminal_operability_verifier.py", "status": "COMPLETE_INITIAL", "plain_english": "Bundle MT4 session, MT5 API evidence, heartbeat, receipts, history export, position reconciliation, runtime gates, and operator next actions into one end-to-end operability report."},
        {"priority": 23, "target_file": "cas_forex/mt5_paper_execution_verifier.py", "status": "COMPLETE_INITIAL", "plain_english": "Build a gated MT5 paper/demo execution verifier that proves CAS can build/check a request and, only with explicit flags, submit and close one demo order through MT5Bridge."},
        {"priority": 24, "target_file": "cas_forex/mt5_deal_history_ingest.py", "status": "COMPLETE_INITIAL", "plain_english": "Read MT5 demo account history, export the closed deal to terminal history, and join it into CAS memory by broker ticket."},
        {"priority": 25, "target_file": "evidence_runs/mt5_deal_history_ingest/mt5-deal-history-ingest-*-report.json", "status": "DEMO_DEAL_HISTORY_JOINED", "plain_english": "Latest Hugosway-Demo EUR/USD ticket 45938644 deal history is joined to memory: 2 raw deals, 1 closed position, net P/L -0.13, commission -0.05, 0 unmatched."},
        {"priority": 26, "target_file": "cas_forex/agent_workflow.py", "status": "NEXT_BUILD_TARGET", "plain_english": "Route normal scheduled paper/demo agent commands through the proven MT5 execution and deal-history learning loop, not only the standalone verifier."},
        {"priority": 27, "target_file": "MQL4/Files/CASForexMailbox/heartbeat.json", "status": "EXTERNAL_MT4_REQUIRED", "plain_english": "If the MT4 EA mailbox path is still preferred, attach the MT4 bridge/history EAs to a real MT4 terminal so heartbeat, receipts, account snapshots, open positions, and closed-history files exist for the operability verifier."},
    ]


def _read_latest(report_dir: Path, pattern: str) -> Dict[str, Any]:
    files = sorted(report_dir.glob(pattern))
    if not files:
        raise AgentInformationFlowError(f"No reports found for {pattern} in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    return payload
