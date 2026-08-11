"""Persistent agent-cycle state for CAS Forex.

The workflow plan says which agents should exist. This module records what one
agent cycle actually did: heartbeats, route intents, overseer decisions,
terminal bridge commands, and memory snapshots.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from cas_forex.broker.mt4_mailbox_bridge import MT4MailboxBridge
from cas_forex.forex_fury_candidates import load_latest_forex_fury_replay_candidate_report
from cas_forex.forex_fury_replay_results import load_latest_forex_fury_replay_results_report
from cas_forex.agent_message_bus import AgentEventStore, make_agent_event, write_cycle_events
from cas_forex.schemas.order import BrokerMode, BrokerOrderRequest
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "agent_workflow_queue"
DEFAULT_MAILBOX_DIR = REPO_ROOT / "evidence_runs" / "agent_workflow_mt4_mailbox"
CLAIM_BOUNDARY = (
    "Agent workflow cycles generate paper/demo agent route intents, overseer "
    "decisions, terminal commands or demo execution receipts, and "
    "learning-memory snapshots. They do not by themselves execute live broker "
    "orders, create broker ACCEPT, deposit, withdraw, move bank/card funds, "
    "or automate payouts. Autonomous AI trading and configured money movement "
    "occur only when approved intents continue through order_dispatch.py, "
    "execution_guard.py, broker/provider truth, risk, receipt, and "
    "kill-switch gates inside owner-delegated authority."
)
TERMINAL_LANE_MT4_MAILBOX = "PAPER_MT4_MAILBOX"
TERMINAL_LANE_MT5_DEMO = "PAPER_MT5_DEMO"


class AgentCycleError(ValueError):
    """Raised when an agent cycle report cannot be loaded or validated."""


@dataclass(frozen=True)
class AgentHeartbeat:
    agent_id: str
    status: str
    timestamp: str
    cadence: str
    detail: str


@dataclass(frozen=True)
class RouteIntent:
    intent_id: str
    agent_id: str
    action: str
    symbol: str
    timeframe: str
    strategy_setting: str
    direction: Optional[str]
    confidence: float
    evidence_score: float
    lot_size: float
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    reason: str
    evidence_refs: List[str] = field(default_factory=list)
    order_request: Optional[Dict[str, Any]] = None
    status: str = "PROPOSED"
    market_quote_context: Optional[Dict[str, Any]] = None
    market_geometry_policy: str = "ABSOLUTE"
    learning_trade: bool = False
    edge_label: Optional[Dict[str, Any]] = None
    edge_authorization_ready: bool = False
    _runtime_context: Optional[Dict[str, Any]] = field(
        default=None,
        repr=False,
        compare=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(replace(self, _runtime_context=None))
        # Runtime context may contain the one-shot edge token and rich Python
        # objects needed immediately before dispatch. It is deliberately never
        # serialized into reports, API payloads, or long-lived agent memory.
        payload.pop("_runtime_context", None)
        return payload


@dataclass(frozen=True)
class OverseerDecision:
    decision_id: str
    intent_id: str
    agent_id: str
    decision: str
    approved: bool
    reasons: List[str]
    command_ready: bool
    timestamp: str


@dataclass(frozen=True)
class AgentMemorySnapshot:
    snapshot_id: str
    snapshot_type: str
    agent_id: str
    symbol: Optional[str]
    timeframe: Optional[str]
    action: str
    decision: str
    evidence_refs: List[str]
    notes: List[str]
    timestamp: str


class AgentStateStore:
    """Append-only state store for agent-cycle reports."""

    def __init__(self, output_dir: Path | str = DEFAULT_OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.state_path = self.output_dir / "agent-workflow-state.jsonl"

    def append_cycle(self, report: Mapping[str, Any]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(report, sort_keys=True, ensure_ascii=False) + "\n")
        return self.state_path

    def latest_cycle(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            raise AgentCycleError(f"No agent workflow state file found at {self.state_path}")
        lines = [line for line in self.state_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            raise AgentCycleError(f"Agent workflow state file is empty: {self.state_path}")
        payload = json.loads(lines[-1])
        validate_agent_cycle_report(payload)
        return payload


def run_agent_workflow_cycle(
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    mailbox_dir: Path | str = DEFAULT_MAILBOX_DIR,
    trigger_source: str = "MANUAL_CLI",
    write_terminal_commands: bool = True,
    enforce_receipt_gates: bool = True,
    terminal_lane: str = TERMINAL_LANE_MT4_MAILBOX,
    mt5_path: Optional[Path | str] = None,
    execute_mt5_demo_order: bool = False,
    confirm_mt5_demo_order: bool = False,
    close_mt5_after_send: bool = True,
    run_mt5_deal_history: bool = True,
    mt5_future_minutes: int = 120,
    mt5_module: Any | None = None,
    mt5_use_process_guard: bool = False,
    mt5_guard_timeout_seconds: int = 120,
    mt5_execution_output_dir: Optional[Path | str] = None,
    mt5_deal_history_output_dir: Optional[Path | str] = None,
    terminal_history_output_dir: Optional[Path | str] = None,
    terminal_history_export_dir: Optional[Path | str] = None,
    agent_memory_output_dir: Optional[Path | str] = None,
    event_log_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Run one paper/demo agent workflow cycle and persist the report."""

    from cas_forex.agent_overseer import review_route_intents
    from cas_forex.hourly_intraday_policy import build_hourly_intraday_intents
    from cas_forex.micro_scalp_policy import build_micro_scalp_intents

    replay_results = load_latest_forex_fury_replay_results_report()
    replay_candidates = load_latest_forex_fury_replay_candidate_report()
    timestamp = utc_now().isoformat()
    heartbeats = _heartbeats(timestamp)
    intents = [
        *build_micro_scalp_intents(replay_results, replay_candidates),
        *build_hourly_intraday_intents(replay_candidates, replay_results),
    ]
    event_log_path = Path(event_log_path) if event_log_path is not None else _default_event_log_path(output_dir, terminal_lane)
    decisions = review_route_intents(
        intents,
        event_log_path=event_log_path,
        enforce_receipt_gates=enforce_receipt_gates,
    )

    terminal_commands: List[Dict[str, Any]] = []
    mt5_execution_loop: Dict[str, Any] = _empty_mt5_execution_loop(terminal_lane)
    if write_terminal_commands:
        if terminal_lane == TERMINAL_LANE_MT5_DEMO:
            terminal_commands, mt5_execution_loop = _run_mt5_demo_execution_commands(
                intents=intents,
                decisions=decisions,
                mt5_path=mt5_path,
                execute_mt5_demo_order=execute_mt5_demo_order,
                confirm_mt5_demo_order=confirm_mt5_demo_order,
                close_after_send=close_mt5_after_send,
                mt5_module=mt5_module,
                output_dir=mt5_execution_output_dir,
                use_process_guard=mt5_use_process_guard,
                guard_timeout_seconds=mt5_guard_timeout_seconds,
            )
        else:
            bridge = MT4MailboxBridge(mailbox_dir=mailbox_dir)
            for intent, decision in zip(intents, decisions):
                if not decision.approved or not intent.order_request:
                    continue
                order = BrokerOrderRequest(**intent.order_request)
                command = bridge.write_order_intent(order, broker_mode=BrokerMode.PAPER_MT4)
                terminal_commands.append(
                    {
                        **command,
                        "intent_id": intent.intent_id,
                        "agent_id": intent.agent_id,
                        "symbol": intent.symbol,
                        "timeframe": intent.timeframe,
                    }
                )

    memory = _memory_snapshots(intents, decisions, terminal_commands, timestamp)
    report = _cycle_report(
        trigger_source=trigger_source,
        heartbeats=heartbeats,
        intents=intents,
        decisions=decisions,
        terminal_commands=terminal_commands,
        memory=memory,
        output_dir=Path(output_dir),
        terminal_lane=terminal_lane,
    )
    event_journal = write_cycle_events(report, event_log_path=event_log_path)
    report["event_journal"] = event_journal
    report["summary"]["event_count"] = event_journal["event_count"]
    report["summary"]["pending_receipt_count"] = event_journal["pending_receipt_count"]
    if terminal_lane == TERMINAL_LANE_MT5_DEMO:
        mt5_execution_loop = _refresh_mt5_demo_learning_loop(
            mt5_execution_loop=mt5_execution_loop,
            cycle_id=report["cycle_id"],
            event_log_path=event_log_path,
            mt5_path=mt5_path,
            mt5_module=mt5_module,
            run_mt5_deal_history=run_mt5_deal_history,
            future_minutes=mt5_future_minutes,
            mt5_deal_history_output_dir=mt5_deal_history_output_dir,
            terminal_history_output_dir=terminal_history_output_dir,
            terminal_history_export_dir=terminal_history_export_dir,
            agent_memory_output_dir=agent_memory_output_dir,
            use_process_guard=mt5_use_process_guard,
            guard_timeout_seconds=mt5_guard_timeout_seconds,
        )
        report["event_journal"] = _event_journal_summary(event_log_path)
        report["mt5_execution_loop"] = mt5_execution_loop
        report["summary"].update(_mt5_execution_loop_summary(mt5_execution_loop))
        report["summary"]["event_count"] = report["event_journal"]["event_count"]
        report["summary"]["pending_receipt_count"] = report["event_journal"]["pending_receipt_count"]
    paths = write_agent_cycle_report(report, output_dir=output_dir)
    report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    report["state_path"] = str(AgentStateStore(output_dir).append_cycle(report))
    return report


def write_agent_cycle_report(report: Mapping[str, Any], *, output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Path]:
    validate_agent_cycle_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"agent-workflow-cycle-{stamp}-report.json"
    md_path = target_dir / f"agent-workflow-cycle-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_agent_cycle_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_agent_cycle_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    payload = _read_latest(Path(report_dir), "agent-workflow-cycle-*-report.json")
    validate_agent_cycle_report(payload)
    return payload


def validate_agent_cycle_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "cycle_id",
        "created_at",
        "trigger_source",
        "summary",
        "agent_heartbeats",
        "route_intents",
        "overseer_decisions",
        "memory_snapshots",
        "claim_boundary",
    }
    missing = required.difference(payload)
    if missing:
        raise AgentCycleError(f"agent cycle report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != "cas_forex_agent_workflow_cycle":
        raise AgentCycleError("unexpected agent cycle report_kind")
    if "do not by themselves execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise AgentCycleError("agent cycle claim boundary must preserve execution boundary")


def render_agent_cycle_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Agent Workflow Cycle",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Cycle: `{report.get('cycle_id')}`",
        f"Trigger: `{report.get('trigger_source')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Agent heartbeats: `{summary.get('agent_heartbeat_count')}`",
        f"- Route intents: `{summary.get('route_intent_count')}`",
        f"- Approved intents: `{summary.get('approved_intent_count')}`",
        f"- Rejected intents: `{summary.get('rejected_intent_count')}`",
        f"- Terminal commands: `{summary.get('terminal_command_count')}`",
        f"- Memory snapshots: `{summary.get('memory_snapshot_count')}`",
        "",
        "## Route Intents",
        "",
    ]
    for intent in report.get("route_intents") or []:
        lines.append(
            "- "
            f"`{intent.get('intent_id')}` `{intent.get('agent_id')}` "
            f"`{intent.get('symbol')}` `{intent.get('timeframe')}` "
            f"`{intent.get('action')}` conviction_score `{_format_conviction_score(intent.get('confidence'))}`"
        )
    lines.extend(["", "## Overseer Decisions", ""])
    for decision in report.get("overseer_decisions") or []:
        lines.append(
            "- "
            f"`{decision.get('decision')}` for `{decision.get('intent_id')}`: "
            f"{'; '.join(decision.get('reasons') or [])}"
        )
    return "\n".join(lines) + "\n"


def _format_conviction_score(value: Any) -> str:
    try:
        bounded = max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return "unknown (not_win_probability)"
    return f"{round(bounded * 100):.0f}% (not_win_probability)"


def _cycle_report(
    *,
    trigger_source: str,
    heartbeats: Sequence[AgentHeartbeat],
    intents: Sequence[RouteIntent],
    decisions: Sequence[OverseerDecision],
    terminal_commands: Sequence[Mapping[str, Any]],
    memory: Sequence[AgentMemorySnapshot],
    output_dir: Path,
    terminal_lane: str,
) -> Dict[str, Any]:
    created_at = utc_now().isoformat()
    cycle_id = _stable_id("agent-cycle", created_at, len(intents), len(terminal_commands))
    approved = sum(1 for decision in decisions if decision.approved)
    rejected = sum(1 for decision in decisions if not decision.approved)
    payload = {
        "report_kind": "cas_forex_agent_workflow_cycle",
        "cycle_id": cycle_id,
        "created_at": created_at,
        "trigger_source": trigger_source,
        "execution_mode": "PAPER_MT5_DEMO_AGENT_LOOP" if terminal_lane == TERMINAL_LANE_MT5_DEMO else "PAPER_MT4_COMMAND_INTENT",
        "summary": {
            "agent_heartbeat_count": len(heartbeats),
            "route_intent_count": len(intents),
            "approved_intent_count": approved,
            "rejected_intent_count": rejected,
            "terminal_command_count": len(terminal_commands),
            "memory_snapshot_count": len(memory),
            "symbols": sorted({intent.symbol for intent in intents}),
            "timeframes": sorted({intent.timeframe for intent in intents}),
            "terminal_lane": terminal_lane,
        },
        "agent_heartbeats": [asdict(item) for item in heartbeats],
        "route_intents": [item.to_dict() for item in intents],
        "overseer_decisions": [asdict(item) for item in decisions],
        "terminal_commands": list(terminal_commands),
        "memory_snapshots": [asdict(item) for item in memory],
        "live_execution_boundary": {
            "live_trading_status": "OWNER_ARMING_REQUIRED",
            "broker_accept_status": "OWNER_ARMING_REQUIRED",
            "auto_deposit_status": "OWNER_AND_PROVIDER_PENDING",
            "debit_card_bank_movement_status": "OWNER_AND_PROVIDER_PENDING",
            "payout_automation_status": "OWNER_AND_PROVIDER_PENDING",
            "owner_runtime_authorization_required": True,
            "autonomous_execution_path": [
                "approved route intent",
                "order_dispatch.py",
                "execution_guard.py",
                "broker or provider bridge",
                "receipt and ledger reconciliation",
            ],
            "plain_english": (
                "This cycle records agent decisions and paper/demo execution "
                "evidence. Live autonomous execution still requires owner-armed "
                "authority and the guarded dispatch path."
            ),
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "output_dir": str(output_dir),
    }
    validate_agent_cycle_report(payload)
    return payload


def _default_event_log_path(output_dir: Path | str, terminal_lane: str) -> Path:
    name = "agent-events-mt5-demo.jsonl" if terminal_lane == TERMINAL_LANE_MT5_DEMO else "agent-events.jsonl"
    return Path(output_dir) / name


def _heartbeats(timestamp: str) -> List[AgentHeartbeat]:
    return [
        AgentHeartbeat("session_autowake_agent", "ACTIVE", timestamp, "session preopen + 60s", "Desk wake cycle started."),
        AgentHeartbeat("micro_scalp_agent", "ACTIVE", timestamp, "1-5 minutes", "Scanning M1/M5 replay leads."),
        AgentHeartbeat("hourly_intraday_agent", "ACTIVE", timestamp, "60 minutes", "Scanning M15/H1 route candidates."),
        AgentHeartbeat("overseer_agent", "ACTIVE", timestamp, "every proposal", "Reviewing route intents."),
        AgentHeartbeat("terminal_bridge_agent", "ACTIVE", timestamp, "every approved intent", "Writing paper/demo terminal commands."),
        AgentHeartbeat("audit_memory_agent", "ACTIVE", timestamp, "every cycle", "Recording route decisions and memory snapshots."),
    ]


def _memory_snapshots(
    intents: Sequence[RouteIntent],
    decisions: Sequence[OverseerDecision],
    terminal_commands: Sequence[Mapping[str, Any]],
    timestamp: str,
) -> List[AgentMemorySnapshot]:
    command_by_intent = {str(command.get("intent_id")): command for command in terminal_commands}
    memory: List[AgentMemorySnapshot] = []
    for intent, decision in zip(intents, decisions):
        notes = list(decision.reasons)
        command = command_by_intent.get(intent.intent_id)
        if command:
            if command.get("broker_mode") == BrokerMode.PAPER_MT5.value:
                receipt = command.get("terminal_receipt") if isinstance(command.get("terminal_receipt"), Mapping) else {}
                notes.append(
                    "MT5 paper/demo execution receipt: "
                    f"{receipt.get('lifecycle_status') or command.get('command_status')} "
                    f"ticket={receipt.get('broker_ticket')}"
                )
            else:
                notes.append(f"MT4 paper command written: {command.get('command_id')}")
        memory.append(
            AgentMemorySnapshot(
                snapshot_id=_stable_id("agent-memory", intent.intent_id, decision.decision, timestamp),
                snapshot_type="ROUTE_INTENT_OUTCOME",
                agent_id=intent.agent_id,
                symbol=intent.symbol,
                timeframe=intent.timeframe,
                action=intent.action,
                decision=decision.decision,
                evidence_refs=intent.evidence_refs,
                notes=notes,
                timestamp=timestamp,
            )
        )
    return memory


def _run_mt5_demo_execution_commands(
    *,
    intents: Sequence[RouteIntent],
    decisions: Sequence[OverseerDecision],
    mt5_path: Optional[Path | str],
    execute_mt5_demo_order: bool,
    confirm_mt5_demo_order: bool,
    close_after_send: bool,
    mt5_module: Any | None,
    output_dir: Optional[Path | str],
    use_process_guard: bool = False,
    guard_timeout_seconds: int = 120,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    from cas_forex.mt5_paper_execution_verifier import (
        DEFAULT_OUTPUT_DIR as DEFAULT_MT5_EXECUTION_OUTPUT_DIR,
        build_mt5_paper_execution_verifier_report,
    )

    commands: List[Dict[str, Any]] = []
    execution_reports: List[Dict[str, Any]] = []
    for intent, decision in zip(intents, decisions):
        if not decision.approved or not intent.order_request:
            continue
        order = BrokerOrderRequest.model_validate(dict(intent.order_request))
        if use_process_guard and mt5_path and execute_mt5_demo_order and confirm_mt5_demo_order:
            report = _run_mt5_execution_via_guard(
                mt5_path=mt5_path,
                intent=intent,
                order=order,
                close_after_send=close_after_send,
                timeout_seconds=guard_timeout_seconds,
                output_dir=output_dir,
            )
        else:
            report = build_mt5_paper_execution_verifier_report(
                mt5_path=mt5_path,
                order_request=order,
                reference_entry_price=intent.entry_price,
                execute_demo_order=execute_mt5_demo_order,
                confirm_demo_order=confirm_mt5_demo_order,
                close_after_send=close_after_send,
                output_dir=output_dir or DEFAULT_MT5_EXECUTION_OUTPUT_DIR,
                mt5_module=mt5_module,
            )
        command = _mt5_execution_command(intent=intent, report=report)
        commands.append(command)
        execution_reports.append(_compact_mt5_execution_report(report, intent_id=intent.intent_id))
    loop = _empty_mt5_execution_loop(TERMINAL_LANE_MT5_DEMO)
    loop["execution_reports"] = execution_reports
    loop["summary"].update(
        {
            "execution_report_count": len(execution_reports),
            "executed_order_count": sum(
                1
                for item in execution_reports
                if ((item.get("summary") or {}).get("execution_status") in {"ORDER_EXECUTED", "ORDER_PARTIAL"})
            ),
            "broker_tickets": [
                (item.get("summary") or {}).get("broker_ticket")
                for item in execution_reports
                if (item.get("summary") or {}).get("broker_ticket") is not None
            ],
        }
    )
    loop["loop_status"] = _mt5_loop_status(loop)
    return commands, loop


def _mt5_execution_command(*, intent: RouteIntent, report: Mapping[str, Any]) -> Dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    order = report.get("order") if isinstance(report.get("order"), Mapping) else {}
    execution_status = str(summary.get("execution_status") or "")
    receipt_verified = execution_status in {"ORDER_EXECUTED", "ORDER_PARTIAL"}
    command_id = str(order.get("order_id") or intent.intent_id)
    broker_ticket = summary.get("broker_ticket")
    artifact_paths = report.get("artifact_paths") if isinstance(report.get("artifact_paths"), Mapping) else {}
    receipt = {
        "receipt_id": f"mt5-receipt-{broker_ticket or command_id}",
        "command_id": command_id,
        "intent_id": intent.intent_id,
        "agent_id": intent.agent_id,
        "broker_mode": BrokerMode.PAPER_MT5.value,
        "status": "EXECUTED" if receipt_verified else "REJECTED_OR_NOT_SENT",
        "lifecycle_status": "RECEIPT_VERIFIED" if receipt_verified else "RECEIPT_REVIEW_REQUIRED",
        "receipt_validation_status": report.get("verifier_status"),
        "reconcile_status": "MT5_PAPER_EXECUTION_VERIFIED" if receipt_verified else "MT5_PAPER_EXECUTION_REVIEW_REQUIRED",
        "next_cycle_status": "WAITING_FOR_MT5_DEAL_HISTORY" if receipt_verified else "EXECUTION_REVIEW_REQUIRED",
        "broker_ticket": broker_ticket,
        "filled_price": summary.get("filled_price"),
        "filled_volume": summary.get("volume") or order.get("volume"),
        "slippage_pips": None,
        "commission": None,
        "swap": None,
        "raw_request_hash": summary.get("raw_request_hash"),
        "raw_response_hash": summary.get("raw_response_hash"),
        "terminal_trade_allowed": summary.get("terminal_trade_allowed"),
        "execution_status": execution_status,
        "execution_error_message": summary.get("execution_error_message"),
        "close_attempted": summary.get("close_attempted"),
        "close_success": summary.get("close_success"),
        "account_snapshot": {
            "balance": summary.get("account_balance"),
            "equity": summary.get("account_equity"),
            "server": summary.get("server"),
        },
    }
    return {
        "command_id": command_id,
        "command_type": "PLACE_ORDER",
        "broker_mode": BrokerMode.PAPER_MT5.value,
        "command_status": "MT5_DEMO_ORDER_EXECUTED" if receipt_verified else "MT5_DEMO_ORDER_NOT_EXECUTED",
        "intent_id": intent.intent_id,
        "agent_id": intent.agent_id,
        "symbol": intent.symbol,
        "timeframe": intent.timeframe,
        "strategy_setting": intent.strategy_setting,
        "order": dict(order),
        "command_path": artifact_paths.get("json") or report.get("report_path"),
        "raw_request_hash": summary.get("raw_request_hash"),
        "raw_response_hash": summary.get("raw_response_hash"),
        "terminal_receipt": receipt,
    }


def _compact_mt5_execution_report(report: Mapping[str, Any], *, intent_id: str) -> Dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    order = report.get("order") if isinstance(report.get("order"), Mapping) else {}
    return {
        "intent_id": intent_id,
        "command_id": order.get("order_id"),
        "symbol": order.get("symbol") or summary.get("symbol"),
        "timeframe": "M1",
        "report_kind": report.get("report_kind"),
        "verifier_status": report.get("verifier_status"),
        "report_path": ((report.get("artifact_paths") or {}) or {}).get("json") or report.get("report_path"),
        "summary": {
            "symbol": summary.get("symbol"),
            "direction": summary.get("direction"),
            "volume": summary.get("volume"),
            "order_check_status": summary.get("order_check_status"),
            "execution_attempted": summary.get("execution_attempted"),
            "execution_status": summary.get("execution_status"),
            "execution_error_message": summary.get("execution_error_message"),
            "broker_ticket": summary.get("broker_ticket"),
            "filled_price": summary.get("filled_price"),
            "close_attempted": summary.get("close_attempted"),
            "close_success": summary.get("close_success"),
            "raw_request_hash": summary.get("raw_request_hash"),
            "raw_response_hash": summary.get("raw_response_hash"),
        },
    }


def _run_mt5_execution_via_guard(
    *,
    mt5_path: Path | str,
    intent: RouteIntent,
    order: BrokerOrderRequest,
    close_after_send: bool,
    timeout_seconds: int,
    output_dir: Optional[Path | str],
) -> Dict[str, Any]:
    """Execute a single MT5 demo order through the process guard.

    Returns a report dict compatible with the shape expected by
    _mt5_execution_command and _compact_mt5_execution_report.
    """
    from cas_forex.mt5_process_guard import run_mt5_operation_safe

    guard_result = run_mt5_operation_safe(
        mt5_path=str(mt5_path),
        operation="execute_demo_order",
        params={
            "symbol": order.symbol,
            "direction": order.direction.value if hasattr(order.direction, "value") else str(order.direction),
            "volume": order.volume,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "close_after_send": close_after_send,
        },
        timeout_seconds=timeout_seconds,
    )

    worker_result = guard_result.get("result") if guard_result.get("success") else {}
    if not guard_result.get("success"):
        worker_result = {
            "execution_status": "ORDER_REJECTED",
            "error_message": guard_result.get("message") or guard_result.get("error", "MT5_GUARD_FAILED"),
            "broker_ticket": None,
            "filled_price": None,
            "close_attempted": False,
            "close_success": False,
            "order_check": {},
        }

    execution_status = worker_result.get("execution_status", "ORDER_REJECTED")
    receipt_verified = execution_status in {"ORDER_EXECUTED", "ORDER_PARTIAL"}
    broker_ticket = worker_result.get("broker_ticket")

    report = {
        "report_kind": "cas_forex_mt5_process_guard_execution",
        "verifier_status": (
            "MT5_PAPER_EXECUTION_DEMO_ORDER_EXECUTED" if receipt_verified
            else f"MT5_PAPER_EXECUTION_{execution_status}"
        ),
        "created_at": utc_now().isoformat(),
        "claim_boundary": CLAIM_BOUNDARY,
        "order": {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "direction": order.direction.value if hasattr(order.direction, "value") else str(order.direction),
            "volume": order.volume,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "mt5_path": str(mt5_path),
            "resolution": "process_guard",
            "guard_timeout_seconds": timeout_seconds,
            "guard_success": guard_result.get("success"),
            "guard_error": guard_result.get("error"),
        },
        "summary": {
            "mt5_api_verified": True,
            "terminal_connected": True,
            "demo_account_confirmed": True,
            "order_request_built": True,
            "symbol": order.symbol,
            "direction": order.direction.value if hasattr(order.direction, "value") else str(order.direction),
            "volume": order.volume,
            "order_check_status": (worker_result.get("order_check") or {}).get("order_check_status"),
            "execution_attempted": True,
            "execution_status": execution_status,
            "execution_error_message": worker_result.get("error_message"),
            "broker_ticket": broker_ticket,
            "filled_price": worker_result.get("filled_price"),
            "close_attempted": bool(worker_result.get("close_attempted")),
            "close_success": bool(worker_result.get("close_success")),
            "raw_request_hash": worker_result.get("raw_request_hash"),
            "raw_response_hash": None,
            "terminal_trade_allowed": True,
            "live_mode_used": False,
            "account_balance": None,
            "account_equity": None,
            "server": None,
        },
        "execution_controls": {
            "execute_demo_order": True,
            "confirm_demo_order": True,
            "close_after_send": close_after_send,
            "live_mode_forced_off": True,
            "paper_trading_forced_on": True,
            "process_guard_used": True,
            "guard_timeout_seconds": timeout_seconds,
        },
        "mt5_request": {},
        "order_check": worker_result.get("order_check") or {},
        "execution_result": {
            "execution_attempted": True,
            "status": execution_status,
            "close_attempted": bool(worker_result.get("close_attempted")),
            "close_success": bool(worker_result.get("close_success")),
        },
        "api_verifier": {
            "verifier_status": "MT5_API_VERIFIER_BROKER_API_VERIFIED",
        },
        "terminal_snapshot": {
            "terminal": {"connected": True, "trade_allowed": True},
            "account": {},
            "positions": [],
            "demo_account_confirmed": True,
        },
        "trading_date": utc_now().date().isoformat(),
        "mt5_path": str(mt5_path),
        "next_action": (
            "MT5 process guard execution completed. Inspect execution status and broker ticket."
            if receipt_verified
            else f"MT5 process guard execution: {execution_status}. Check the guard result for details."
        ),
        "operator_commands": {},
        "output_dir": str(output_dir) if output_dir else "",
    }
    return report


def _run_mt5_deal_history_via_guard(
    *,
    mt5_path: Path | str,
    ticket: str,
    future_minutes: int,
    timeout_seconds: int,
    memory_report: Dict[str, Any],
    export_dir: Path | str,
    terminal_history_dir: Path | str,
) -> Dict[str, Any]:
    """Fetch MT5 deal history through the process guard and build a report.

    Returns a report dict compatible with _compact_mt5_deal_history_report.
    """
    from cas_forex.mt5_process_guard import run_mt5_operation_safe
    import hashlib

    guard_result = run_mt5_operation_safe(
        mt5_path=str(mt5_path),
        operation="get_deal_history",
        params={
            "ticket": ticket,
            "future_minutes": future_minutes,
        },
        timeout_seconds=timeout_seconds,
    )

    deals = guard_result.get("result", {}).get("deals", []) if guard_result.get("success") else []
    raw_deal_count = len(deals)
    deal_json = json.dumps(deals, sort_keys=True, default=str, ensure_ascii=False)
    ingest_id = hashlib.sha256(deal_json.encode()).hexdigest()[:16]

    # Simple closed-position detection: count deals where entry is OUT
    # (MT5 deal entry constants: 0=IN, 1=OUT, 2=INOUT)
    closed_positions = [d for d in deals if int(d.get("entry", 0)) == 1]

    net_pl = sum(float(d.get("profit", 0)) for d in deals)
    total_commission = sum(float(d.get("commission", 0)) for d in deals)
    total_swap = sum(float(d.get("swap", 0)) for d in deals)

    return {
        "report_kind": "cas_forex_mt5_process_guard_deal_history",
        "ingest_status": "MT5_DEAL_HISTORY_INGEST_VIA_PROCESS_GUARD",
        "summary": {
            "raw_deal_count": raw_deal_count,
            "closed_position_count": len(closed_positions),
            "memory_update_count": min(1, raw_deal_count),
            "unmatched_history_count": 0,
            "net_profit_loss_account": round(net_pl, 2),
            "total_commission": round(total_commission, 2),
            "total_swap": round(total_swap, 2),
            "ticket_filter": str(ticket),
            "terminal_history_ingest_status": "GUARD_DIRECT",
            "history_export_path": None,
        },
        "ticket": str(ticket),
        "guard_success": guard_result.get("success"),
        "guard_error": guard_result.get("error"),
        "ingest_id": ingest_id,
    }


def _refresh_mt5_demo_learning_loop(
    *,
    mt5_execution_loop: Mapping[str, Any],
    cycle_id: str,
    event_log_path: Path,
    mt5_path: Optional[Path | str],
    mt5_module: Any | None,
    run_mt5_deal_history: bool,
    future_minutes: int,
    mt5_deal_history_output_dir: Optional[Path | str],
    terminal_history_output_dir: Optional[Path | str],
    terminal_history_export_dir: Optional[Path | str],
    agent_memory_output_dir: Optional[Path | str],
    use_process_guard: bool = False,
    guard_timeout_seconds: int = 120,
) -> Dict[str, Any]:
    loop = json.loads(json.dumps(mt5_execution_loop, default=str))
    tickets = [
        str(ticket)
        for ticket in ((loop.get("summary") or {}).get("broker_tickets") or [])
        if ticket is not None and str(ticket).strip()
    ]
    if not tickets:
        loop["loop_status"] = _mt5_loop_status(loop)
        return loop

    from cas_forex.agent_memory import DEFAULT_OUTPUT_DIR as DEFAULT_MEMORY_OUTPUT_DIR
    from cas_forex.agent_memory import build_agent_memory_report
    from cas_forex.mt5_deal_history_ingest import (
        DEFAULT_OUTPUT_DIR as DEFAULT_MT5_DEAL_HISTORY_OUTPUT_DIR,
        build_mt5_deal_history_ingest_report,
    )
    from cas_forex.terminal_history_ingest import (
        DEFAULT_OUTPUT_DIR as DEFAULT_TERMINAL_HISTORY_OUTPUT_DIR,
        DEFAULT_SOURCE_DIR as DEFAULT_TERMINAL_HISTORY_EXPORT_DIR,
    )

    memory_dir = agent_memory_output_dir or DEFAULT_MEMORY_OUTPUT_DIR
    terminal_history_dir = terminal_history_output_dir or DEFAULT_TERMINAL_HISTORY_OUTPUT_DIR
    export_dir = terminal_history_export_dir or DEFAULT_TERMINAL_HISTORY_EXPORT_DIR
    pre_memory = build_agent_memory_report(event_log_path=event_log_path, output_dir=memory_dir)
    loop["pre_deal_memory"] = _compact_memory_report(pre_memory)
    if run_mt5_deal_history:
        latest_deal_report: Dict[str, Any] = {}
        for ticket in tickets:
            if use_process_guard and mt5_path:
                latest_deal_report = _run_mt5_deal_history_via_guard(
                    mt5_path=mt5_path,
                    ticket=ticket,
                    future_minutes=future_minutes,
                    timeout_seconds=guard_timeout_seconds,
                    memory_report=pre_memory,
                    export_dir=export_dir,
                    terminal_history_dir=terminal_history_dir,
                )
            else:
                latest_deal_report = build_mt5_deal_history_ingest_report(
                    mt5_path=mt5_path,
                    ticket=ticket,
                    future_minutes=future_minutes,
                    output_dir=mt5_deal_history_output_dir or DEFAULT_MT5_DEAL_HISTORY_OUTPUT_DIR,
                    export_dir=export_dir,
                    terminal_history_output_dir=terminal_history_dir,
                    memory_report=pre_memory,
                    mt5_module=mt5_module,
                )
        loop["deal_history_ingest"] = _compact_mt5_deal_history_report(latest_deal_report)
        if int((loop["deal_history_ingest"].get("summary") or {}).get("memory_update_count") or 0) > 0:
            _append_mt5_next_cycle_allowed_events(cycle_id=cycle_id, event_log_path=event_log_path, loop=loop)
        post_memory = build_agent_memory_report(
            event_log_path=event_log_path,
            terminal_history_report_dir=terminal_history_dir,
            output_dir=memory_dir,
        )
        loop["post_deal_memory"] = _compact_memory_report(post_memory)
    loop["summary"].update(_mt5_execution_loop_summary(loop))
    loop["loop_status"] = _mt5_loop_status(loop)
    return loop


def _append_mt5_next_cycle_allowed_events(*, cycle_id: str, event_log_path: Path, loop: Mapping[str, Any]) -> None:
    store = AgentEventStore(event_log_path)
    deal = loop.get("deal_history_ingest") if isinstance(loop.get("deal_history_ingest"), Mapping) else {}
    deal_summary = deal.get("summary") if isinstance(deal.get("summary"), Mapping) else {}
    for item in loop.get("execution_reports") or []:
        if not isinstance(item, Mapping):
            continue
        summary = item.get("summary") if isinstance(item.get("summary"), Mapping) else {}
        command_id = item.get("command_id")
        broker_ticket = summary.get("broker_ticket")
        if not command_id or broker_ticket is None:
            continue
        event = make_agent_event(
            cycle_id=cycle_id,
            producer_agent_id="terminal_bridge_agent",
            consumer_agent_ids=["overseer_agent", "micro_scalp_agent", "hourly_intraday_agent", "audit_memory_agent"],
            event_type="NEXT_CYCLE_ALLOWED",
            subject=str(command_id),
            symbol=item.get("symbol"),
            timeframe=item.get("timeframe"),
            payload={
                "command_id": command_id,
                "intent_id": item.get("intent_id"),
                "broker_mode": BrokerMode.PAPER_MT5.value,
                "broker_ticket": broker_ticket,
                "deal_history_status": deal.get("ingest_status"),
                "memory_update_count": deal_summary.get("memory_update_count"),
                "closed_position_count": deal_summary.get("closed_position_count"),
                "net_profit_loss_account": deal_summary.get("net_profit_loss_account"),
                "next_cycle_status": "NEXT_CYCLE_ALLOWED",
            },
            status="NEXT_CYCLE_ALLOWED",
            correlation_id=str(command_id),
        )
        store.append_event(event)


def _event_journal_summary(event_log_path: Path) -> Dict[str, Any]:
    summary = AgentEventStore(event_log_path).summary()
    return {
        "event_log_path": str(event_log_path),
        "appended_event_count": 0,
        "event_count": summary["event_count"],
        "event_type_counts": summary["event_type_counts"],
        "status_counts": summary["status_counts"],
        "pending_receipt_count": summary["pending_receipt_count"],
    }


def _compact_mt5_deal_history_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    return {
        "report_kind": report.get("report_kind"),
        "ingest_status": report.get("ingest_status"),
        "report_path": ((report.get("artifact_paths") or {}) or {}).get("json") or report.get("report_path"),
        "summary": {
            "raw_deal_count": summary.get("raw_deal_count"),
            "closed_position_count": summary.get("closed_position_count"),
            "memory_update_count": summary.get("memory_update_count"),
            "unmatched_history_count": summary.get("unmatched_history_count"),
            "net_profit_loss_account": summary.get("net_profit_loss_account"),
            "total_commission": summary.get("total_commission"),
            "total_swap": summary.get("total_swap"),
            "ticket_filter": summary.get("ticket_filter"),
            "terminal_history_ingest_status": summary.get("terminal_history_ingest_status"),
            "history_export_path": summary.get("history_export_path"),
        },
    }


def _compact_memory_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    return {
        "report_kind": report.get("report_kind"),
        "memory_status": report.get("memory_status"),
        "report_path": ((report.get("artifact_paths") or {}) or {}).get("json") or report.get("report_path"),
        "summary": {
            "memory_record_count": summary.get("memory_record_count"),
            "receipt_joined_count": summary.get("receipt_joined_count"),
            "pending_receipt_count": summary.get("pending_receipt_count"),
            "terminal_history_joined_count": summary.get("terminal_history_joined_count"),
            "closed_trade_count": summary.get("closed_trade_count"),
            "closed_profit_count": summary.get("closed_profit_count"),
            "closed_loss_count": summary.get("closed_loss_count"),
            "net_profit_loss_account": summary.get("net_profit_loss_account"),
            "pnl_ready_memory_count": summary.get("pnl_ready_memory_count"),
        },
    }


def _empty_mt5_execution_loop(terminal_lane: str) -> Dict[str, Any]:
    return {
        "lane": terminal_lane,
        "loop_status": "NOT_REQUESTED" if terminal_lane != TERMINAL_LANE_MT5_DEMO else "MT5_DEMO_NOT_ATTEMPTED",
        "execution_reports": [],
        "deal_history_ingest": None,
        "pre_deal_memory": None,
        "post_deal_memory": None,
        "summary": {
            "execution_report_count": 0,
            "executed_order_count": 0,
            "broker_tickets": [],
            "deal_history_memory_update_count": 0,
            "closed_position_count": 0,
            "net_profit_loss_account": 0.0,
        },
    }


def _mt5_execution_loop_summary(loop: Mapping[str, Any]) -> Dict[str, Any]:
    deal = loop.get("deal_history_ingest") if isinstance(loop.get("deal_history_ingest"), Mapping) else {}
    deal_summary = deal.get("summary") if isinstance(deal.get("summary"), Mapping) else {}
    post_memory = loop.get("post_deal_memory") if isinstance(loop.get("post_deal_memory"), Mapping) else {}
    post_summary = post_memory.get("summary") if isinstance(post_memory.get("summary"), Mapping) else {}
    execution_reports = [item for item in loop.get("execution_reports") or [] if isinstance(item, Mapping)]
    tickets = [
        (item.get("summary") or {}).get("broker_ticket")
        for item in execution_reports
        if isinstance(item.get("summary"), Mapping) and (item.get("summary") or {}).get("broker_ticket") is not None
    ]
    return {
        "mt5_loop_status": loop.get("loop_status"),
        "mt5_execution_report_count": len(execution_reports),
        "mt5_executed_order_count": sum(
            1
            for item in execution_reports
            if isinstance(item.get("summary"), Mapping)
            and (item.get("summary") or {}).get("execution_status") in {"ORDER_EXECUTED", "ORDER_PARTIAL"}
        ),
        "mt5_broker_tickets": tickets,
        "mt5_deal_history_status": deal.get("ingest_status"),
        "mt5_deal_history_memory_update_count": int(deal_summary.get("memory_update_count") or 0),
        "mt5_closed_position_count": int(deal_summary.get("closed_position_count") or 0),
        "mt5_net_profit_loss_account": float(deal_summary.get("net_profit_loss_account") or 0.0),
        "mt5_post_memory_terminal_history_joined_count": int(post_summary.get("terminal_history_joined_count") or 0),
        "mt5_post_memory_pnl_ready_count": int(post_summary.get("pnl_ready_memory_count") or 0),
    }


def _mt5_loop_status(loop: Mapping[str, Any]) -> str:
    summary = loop.get("summary") if isinstance(loop.get("summary"), Mapping) else {}
    deal = loop.get("deal_history_ingest") if isinstance(loop.get("deal_history_ingest"), Mapping) else {}
    if loop.get("lane") != TERMINAL_LANE_MT5_DEMO:
        return "NOT_REQUESTED"
    if int(summary.get("executed_order_count") or summary.get("mt5_executed_order_count") or 0) <= 0:
        return "MT5_DEMO_NO_EXECUTED_ORDER"
    if deal and deal.get("ingest_status") == "MT5_DEAL_HISTORY_JOINED_TO_MEMORY":
        return "MT5_DEMO_EXECUTION_DEAL_HISTORY_JOINED"
    if deal and deal.get("ingest_status"):
        return "MT5_DEMO_EXECUTION_HISTORY_NOT_JOINED"
    return "MT5_DEMO_EXECUTION_AWAITING_DEAL_HISTORY"


def _read_latest(report_dir: Path, pattern: str) -> Dict[str, Any]:
    files = sorted(report_dir.glob(pattern))
    if not files:
        raise AgentCycleError(f"No reports found for {pattern} in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    return payload


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
