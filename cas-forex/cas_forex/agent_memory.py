"""Outcome-memory writer for the CAS Forex agent desk.

This module turns the append-only event journal into durable learning rows.
The rows join route intents, overseer decisions, terminal commands, and terminal
receipts so later agents can learn from what actually happened instead of only
remembering that a proposal was made.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from cas_forex.agent_message_bus import DEFAULT_EVENT_LOG_PATH, AgentEventStore, AgentMessageBusError
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "agent_memory"
REPORT_KIND = "cas_forex_agent_memory_report"
MEMORY_SCHEMA = "cas_forex_agent_outcome_memory.v1"
CLAIM_BOUNDARY = (
    "Agent outcome memory joins paper/demo route, decision, command, and "
    "receipt facts for future research. It does not by itself execute live "
    "broker orders, create broker ACCEPT, deposit, withdraw, move bank/card "
    "funds, or automate payouts. Live autonomous side effects only occur when "
    "approved intents continue through order_dispatch.py, execution_guard.py, "
    "broker/provider truth, risk, receipt, and kill-switch gates."
)


class AgentMemoryError(ValueError):
    """Raised when agent outcome memory cannot be built or loaded."""


def build_agent_memory_report(
    *,
    event_log_path: Path | str = DEFAULT_EVENT_LOG_PATH,
    terminal_history_report_dir: Optional[Path | str] = None,
    mt5_paper_execution_report_dir: Optional[Path | str] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build and optionally persist the current agent outcome-memory report."""

    store = AgentEventStore(event_log_path)
    try:
        events = store.read_events(limit=100000)
    except AgentMessageBusError as exc:
        raise AgentMemoryError(str(exc)) from exc

    records = build_agent_memory_records(events)
    records.extend(_load_mt5_paper_execution_memory_records(event_log_path, mt5_paper_execution_report_dir))
    terminal_history_updates = _load_terminal_history_updates(terminal_history_report_dir)
    if terminal_history_updates:
        _apply_terminal_history_updates(records, terminal_history_updates)
    summary = _summary(records, store.summary())
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "memory_status": "AGENT_MEMORY_BUILT",
        "schema": MEMORY_SCHEMA,
        "event_log_path": str(Path(event_log_path)),
        "output_dir": str(Path(output_dir)),
        "summary": summary,
        "memory_records": records,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        paths = write_agent_memory_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_agent_memory_report(report)
    return report


def build_agent_memory_records(events: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Join route intents, decisions, commands, and receipts into memory rows."""

    event_list = list(events)
    intents: List[Mapping[str, Any]] = [event for event in event_list if event.get("event_type") == "ROUTE_INTENT_CREATED"]
    decisions = _latest_by_cycle_intent(
        event for event in event_list if event.get("event_type") == "OVERSEER_DECISION_CREATED"
    )
    commands = _latest_command_by_cycle_intent(
        event for event in event_list if event.get("event_type") == "TERMINAL_COMMAND_WRITTEN"
    )
    receipts = _latest_receipt_by_command(
        event
        for event in event_list
        if event.get("event_type") in {"TERMINAL_RECEIPT_RECEIVED", "TERMINAL_RECEIPT_MISMATCH"}
    )

    records: List[Dict[str, Any]] = []
    for intent_event in intents:
        intent = dict(intent_event.get("payload") or {})
        key = _cycle_intent_key(intent_event)
        decision_event = decisions.get(key)
        decision = dict((decision_event or {}).get("payload") or {})
        command_event = commands.get(key)
        command = dict((command_event or {}).get("payload") or {})
        receipt_event = receipts.get(str(command.get("command_id") or ""))
        receipt = dict((receipt_event or {}).get("payload") or {})
        record = _memory_record(intent_event, intent, decision_event, decision, command_event, command, receipt_event, receipt)
        validate_agent_memory_record(record)
        records.append(record)
    return records


def write_agent_memory_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    """Write report JSON/Markdown plus memory JSONL."""

    validate_agent_memory_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"agent-memory-{stamp}-report.json"
    md_path = target_dir / f"agent-memory-{stamp}-report.md"
    jsonl_path = target_dir / f"agent-memory-{stamp}.jsonl"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_agent_memory_markdown(report), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in report.get("memory_records") or []:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return {"json": json_path, "markdown": md_path, "jsonl": jsonl_path}


def load_latest_agent_memory_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("agent-memory-*-report.json"))
    if not files:
        raise AgentMemoryError(f"No agent memory reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_agent_memory_report(payload)
    return payload


def validate_agent_memory_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "memory_status",
        "schema",
        "event_log_path",
        "summary",
        "memory_records",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise AgentMemoryError(f"agent memory report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise AgentMemoryError("unexpected agent memory report_kind")
    if payload.get("schema") != MEMORY_SCHEMA:
        raise AgentMemoryError("unexpected agent memory schema")
    if "does not by itself execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise AgentMemoryError("agent memory claim boundary must preserve execution boundary")
    if not isinstance(payload.get("memory_records"), list):
        raise AgentMemoryError("memory_records must be a list")
    for record in payload.get("memory_records") or []:
        validate_agent_memory_record(record)


def validate_agent_memory_record(record: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "memory_id",
        "cycle_id",
        "intent_id",
        "agent_id",
        "symbol",
        "timeframe",
        "action",
        "decision",
        "decision_status",
        "outcome_label",
        "learning_status",
        "condition_snapshot_open",
        "condition_snapshot_close",
        "source_event_ids",
        "claim_boundary",
    }
    missing = required.difference(record)
    if missing:
        raise AgentMemoryError(f"agent memory record missing fields: {sorted(missing)}")
    if record.get("schema") != MEMORY_SCHEMA:
        raise AgentMemoryError("unexpected agent memory record schema")
    if "does not by itself execute live broker orders" not in str(record.get("claim_boundary", "")):
        raise AgentMemoryError("agent memory record claim boundary must preserve execution boundary")


def render_agent_memory_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Agent Outcome Memory",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('memory_status')}`",
        f"Event log: `{report.get('event_log_path')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Memory records: `{summary.get('memory_record_count')}`",
        f"- Approved routes: `{summary.get('approved_count')}`",
        f"- Rejected routes: `{summary.get('rejected_count')}`",
        f"- Commands joined: `{summary.get('command_joined_count')}`",
        f"- Receipts joined: `{summary.get('receipt_joined_count')}`",
        f"- Terminal history joined: `{summary.get('terminal_history_joined_count')}`",
        f"- Pending receipts: `{summary.get('pending_receipt_count')}`",
        f"- Closed wins/losses/flats: `{summary.get('closed_profit_count')}` / `{summary.get('closed_loss_count')}` / `{summary.get('closed_flat_count')}`",
        f"- Net closed PnL: `{summary.get('net_profit_loss_account')}`",
        f"- Outcome labels: `{summary.get('outcome_label_counts')}`",
        "",
        "## Records",
        "",
    ]
    for record in report.get("memory_records") or []:
        lines.append(
            "- "
            f"`{record.get('memory_id')}` `{record.get('symbol')}` `{record.get('timeframe')}` "
            f"decision `{record.get('decision')}` outcome `{record.get('outcome_label')}` "
            f"learning `{record.get('learning_status')}`"
        )
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _memory_record(
    intent_event: Mapping[str, Any],
    intent: Mapping[str, Any],
    decision_event: Optional[Mapping[str, Any]],
    decision: Mapping[str, Any],
    command_event: Optional[Mapping[str, Any]],
    command: Mapping[str, Any],
    receipt_event: Optional[Mapping[str, Any]],
    receipt: Mapping[str, Any],
) -> Dict[str, Any]:
    command_id = command.get("command_id")
    receipt_id = receipt.get("receipt_id")
    outcome_label, learning_status = _outcome_label(decision_event, decision, command, receipt)
    source_event_ids = [
        event.get("event_id")
        for event in (intent_event, decision_event, command_event, receipt_event)
        if event and event.get("event_id")
    ]
    condition_open = {
        "symbol": intent.get("symbol") or intent_event.get("symbol"),
        "timeframe": intent.get("timeframe") or intent_event.get("timeframe"),
        "strategy_setting": intent.get("strategy_setting") or intent_event.get("strategy_setting"),
        "direction": intent.get("direction"),
        "entry_price": intent.get("entry_price"),
        "stop_loss": intent.get("stop_loss"),
        "take_profit": intent.get("take_profit"),
        "lot_size": intent.get("lot_size"),
        "confidence": intent.get("confidence"),
        "evidence_score": intent.get("evidence_score"),
        "evidence_refs": intent.get("evidence_refs") or [],
        "order_request": intent.get("order_request") or {},
    }
    condition_close = {
        "receipt_id": receipt_id,
        "receipt_status": receipt.get("status"),
        "receipt_validation_status": receipt.get("receipt_validation_status") or receipt.get("lifecycle_status"),
        "reconcile_status": receipt.get("reconcile_status"),
        "next_cycle_status": receipt.get("next_cycle_status"),
        "account_snapshot": receipt.get("account_snapshot") or {},
    }
    demotion_flags: List[str] = []
    if outcome_label == "TERMINAL_RECEIPT_MISMATCH":
        demotion_flags.append("terminal_receipt_mismatch")
    if outcome_label == "AWAITING_TERMINAL_RECEIPT":
        demotion_flags.append("awaiting_terminal_receipt")
    if outcome_label == "ROUTE_REJECTED":
        demotion_flags.append("route_rejected")

    record = {
        "schema": MEMORY_SCHEMA,
        "memory_id": _memory_id(intent_event.get("cycle_id"), intent.get("intent_id"), command_id, receipt_id, outcome_label),
        "cycle_id": intent_event.get("cycle_id"),
        "intent_id": intent.get("intent_id"),
        "decision_id": decision.get("decision_id"),
        "command_id": command_id,
        "receipt_id": receipt_id,
        "agent_id": intent.get("agent_id"),
        "symbol": intent.get("symbol") or intent_event.get("symbol"),
        "timeframe": intent.get("timeframe") or intent_event.get("timeframe"),
        "strategy_setting": intent.get("strategy_setting") or intent_event.get("strategy_setting"),
        "action": intent.get("action"),
        "direction": intent.get("direction"),
        "decision": decision.get("decision") or "NO_DECISION",
        "decision_approved": bool(decision.get("approved", False)),
        "decision_status": (decision_event or {}).get("status") or "NO_DECISION",
        "decision_reasons": decision.get("reasons") or [],
        "broker_mode": command.get("broker_mode") or receipt.get("broker_mode"),
        "terminal_command_status": (command_event or {}).get("status") or "NO_COMMAND",
        "terminal_receipt_status": receipt.get("lifecycle_status") or receipt.get("receipt_validation_status") or "NO_RECEIPT",
        "reconcile_status": receipt.get("reconcile_status") or "NOT_RECONCILED",
        "next_cycle_status": receipt.get("next_cycle_status") or "WAITING",
        "broker_ticket": receipt.get("broker_ticket"),
        "filled_price": receipt.get("filled_price"),
        "filled_volume": receipt.get("filled_volume"),
        "slippage_pips": receipt.get("slippage_pips"),
        "commission": receipt.get("commission"),
        "swap": receipt.get("swap"),
        "profit_loss_account": None,
        "profit_loss_pips": None,
        "profit_loss_r": None,
        "mae": None,
        "mfe": None,
        "close_reason": None,
        "outcome_label": outcome_label,
        "learning_status": learning_status,
        "promotion_signal": _promotion_signal(outcome_label),
        "demotion_flags": demotion_flags,
        "condition_snapshot_open": condition_open,
        "condition_snapshot_close": condition_close,
        "source_event_ids": source_event_ids,
        "source_refs": _source_refs(intent_event, decision_event, command_event, receipt_event),
        "created_at": utc_now().isoformat(),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return record


def _load_terminal_history_updates(report_dir: Optional[Path | str]) -> Dict[str, Dict[str, Any]]:
    try:
        from cas_forex.terminal_history_ingest import (
            DEFAULT_OUTPUT_DIR as DEFAULT_TERMINAL_HISTORY_OUTPUT_DIR,
            load_latest_terminal_history_ingest_report,
        )

        report = load_latest_terminal_history_ingest_report(report_dir or DEFAULT_TERMINAL_HISTORY_OUTPUT_DIR)
    except Exception:
        return {}
    updates: Dict[str, Dict[str, Any]] = {}
    for update in report.get("memory_updates") or []:
        if isinstance(update, Mapping) and update.get("memory_id"):
            updates[str(update["memory_id"])] = dict(update)
    return updates


def _load_mt5_paper_execution_memory_records(
    event_log_path: Path | str,
    report_dir: Optional[Path | str],
) -> List[Dict[str, Any]]:
    try:
        default_event_log = Path(DEFAULT_EVENT_LOG_PATH).resolve()
        current_event_log = Path(event_log_path).resolve()
    except Exception:
        default_event_log = Path(DEFAULT_EVENT_LOG_PATH)
        current_event_log = Path(event_log_path)
    if report_dir is None and current_event_log != default_event_log:
        return []
    try:
        from cas_forex.mt5_paper_execution_verifier import (
            DEFAULT_OUTPUT_DIR as DEFAULT_MT5_PAPER_EXECUTION_OUTPUT_DIR,
            load_latest_mt5_paper_execution_verifier_report,
        )

        report = load_latest_mt5_paper_execution_verifier_report(report_dir or DEFAULT_MT5_PAPER_EXECUTION_OUTPUT_DIR)
    except Exception:
        return []
    record = _mt5_paper_execution_memory_record(report)
    return [record] if record is not None else []


def _mt5_paper_execution_memory_record(report: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    if summary.get("execution_status") not in {"ORDER_EXECUTED", "ORDER_PARTIAL"}:
        return None
    broker_ticket = summary.get("broker_ticket")
    if broker_ticket in {None, ""}:
        return None
    order = report.get("order") if isinstance(report.get("order"), Mapping) else {}
    controls = report.get("execution_controls") if isinstance(report.get("execution_controls"), Mapping) else {}
    memory_id = _memory_id(
        "mt5-paper-execution-verifier",
        order.get("order_id"),
        broker_ticket,
        summary.get("execution_status"),
    )
    direction = order.get("direction") or summary.get("direction")
    symbol = order.get("symbol") or summary.get("symbol")
    condition_open = {
        "symbol": symbol,
        "timeframe": "M1",
        "strategy_setting": "mt5_paper_execution_verifier",
        "direction": direction,
        "entry_price": summary.get("filled_price") or order.get("price"),
        "stop_loss": order.get("stop_loss"),
        "take_profit": order.get("take_profit"),
        "lot_size": summary.get("volume") or order.get("volume"),
        "confidence": None,
        "evidence_score": None,
        "evidence_refs": [report.get("report_path") or ((report.get("artifact_paths") or {}) or {}).get("json")],
        "order_request": dict(order),
    }
    condition_close = {
        "receipt_id": None,
        "receipt_status": summary.get("execution_status"),
        "receipt_validation_status": report.get("verifier_status"),
        "reconcile_status": "MT5_PAPER_EXECUTION_VERIFIED",
        "next_cycle_status": "WAITING_FOR_MT5_DEAL_HISTORY",
        "account_snapshot": {
            "balance": summary.get("account_balance"),
            "equity": summary.get("account_equity"),
            "currency": None,
            "server": summary.get("server"),
        },
        "close_attempted": summary.get("close_attempted"),
        "close_success": summary.get("close_success"),
        "raw_request_hash": summary.get("raw_request_hash"),
        "raw_response_hash": summary.get("raw_response_hash"),
    }
    record = {
        "schema": MEMORY_SCHEMA,
        "memory_id": memory_id,
        "cycle_id": "mt5-paper-execution-verifier",
        "intent_id": order.get("order_id") or "mt5-paper-execution-verifier",
        "decision_id": report.get("verifier_status"),
        "command_id": order.get("order_id"),
        "receipt_id": None,
        "agent_id": "mt5_paper_execution_verifier",
        "symbol": symbol,
        "timeframe": "M1",
        "strategy_setting": "mt5_paper_execution_verifier",
        "action": "OPEN_INITIAL",
        "direction": direction,
        "decision": "DEMO_VERIFIER_CONFIRMED",
        "decision_approved": bool(controls.get("execute_demo_order") and controls.get("confirm_demo_order")),
        "decision_status": report.get("verifier_status"),
        "decision_reasons": ["explicitly confirmed MT5 demo execution verifier trade"],
        "broker_mode": "PAPER_MT5",
        "terminal_command_status": "MT5_DEMO_ORDER_SENT",
        "terminal_receipt_status": report.get("verifier_status"),
        "reconcile_status": "MT5_PAPER_EXECUTION_VERIFIED",
        "next_cycle_status": "WAITING_FOR_MT5_DEAL_HISTORY",
        "broker_ticket": broker_ticket,
        "filled_price": summary.get("filled_price"),
        "filled_volume": summary.get("volume") or order.get("volume"),
        "slippage_pips": None,
        "commission": None,
        "swap": None,
        "profit_loss_account": None,
        "profit_loss_pips": None,
        "profit_loss_r": None,
        "mae": None,
        "mfe": None,
        "close_reason": None,
        "outcome_label": "TERMINAL_ACKNOWLEDGED",
        "learning_status": "READY_FOR_RESEARCH",
        "promotion_signal": "RECEIPT_CONFIRMED_NO_PNL_YET",
        "demotion_flags": [],
        "condition_snapshot_open": condition_open,
        "condition_snapshot_close": condition_close,
        "source_event_ids": [],
        "source_refs": [
            {
                "kind": "mt5_paper_execution_verifier",
                "report_path": report.get("report_path") or ((report.get("artifact_paths") or {}) or {}).get("json"),
                "raw_request_hash": summary.get("raw_request_hash"),
                "raw_response_hash": summary.get("raw_response_hash"),
            }
        ],
        "created_at": utc_now().isoformat(),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    validate_agent_memory_record(record)
    return record


def _apply_terminal_history_updates(
    records: List[Dict[str, Any]],
    terminal_history_updates: Mapping[str, Mapping[str, Any]],
) -> None:
    for record in records:
        update = terminal_history_updates.get(str(record.get("memory_id") or ""))
        if not update:
            continue
        close_snapshot = record.get("condition_snapshot_close")
        if not isinstance(close_snapshot, dict):
            close_snapshot = {}
        close_snapshot.update(
            {
                "terminal_history_id": update.get("history_id"),
                "terminal_history_status": update.get("terminal_history_status"),
                "closed_at": update.get("closed_at"),
                "exit_price": update.get("exit_price"),
                "close_reason": update.get("close_reason"),
                "profit_loss_account": update.get("profit_loss_account"),
                "profit_loss_pips": update.get("profit_loss_pips"),
                "profit_loss_r": update.get("profit_loss_r"),
                "mae": update.get("mae"),
                "mfe": update.get("mfe"),
                "commission": update.get("commission"),
                "swap": update.get("swap"),
                "terminal_history_source_path": update.get("source_path"),
                "terminal_history_source_sha256": update.get("source_sha256"),
            }
        )
        demotion_flags = list(record.get("demotion_flags") or [])
        for flag in update.get("demotion_flags") or []:
            if flag not in demotion_flags:
                demotion_flags.append(flag)
        source_refs = list(record.get("source_refs") or [])
        source_refs.append(
            {
                "kind": "terminal_history_ingest",
                "history_id": update.get("history_id"),
                "source_path": update.get("source_path"),
                "source_sha256": update.get("source_sha256"),
                "match_method": update.get("match_method"),
            }
        )
        record.update(
            {
                "terminal_history_id": update.get("history_id"),
                "terminal_history_status": update.get("terminal_history_status"),
                "profit_loss_account": update.get("profit_loss_account"),
                "profit_loss_pips": update.get("profit_loss_pips"),
                "profit_loss_r": update.get("profit_loss_r"),
                "mae": update.get("mae"),
                "mfe": update.get("mfe"),
                "close_reason": update.get("close_reason"),
                "closed_at": update.get("closed_at"),
                "exit_price": update.get("exit_price"),
                "commission": update.get("commission"),
                "swap": update.get("swap"),
                "outcome_label": update.get("outcome_label") or record.get("outcome_label"),
                "learning_status": "READY_FOR_RESEARCH",
                "promotion_signal": update.get("promotion_signal") or record.get("promotion_signal"),
                "demotion_flags": demotion_flags,
                "condition_snapshot_close": close_snapshot,
                "source_refs": source_refs,
            }
        )


def _outcome_label(
    decision_event: Optional[Mapping[str, Any]],
    decision: Mapping[str, Any],
    command: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> Tuple[str, str]:
    if decision_event is None:
        return "NO_DECISION", "INSUFFICIENT_FOR_LEARNING"
    if not bool(decision.get("approved", False)):
        return "ROUTE_REJECTED", "READY_FOR_RESEARCH"
    if not command:
        return "APPROVED_NO_COMMAND", "NEEDS_COMMAND_REVIEW"
    if not receipt:
        return "AWAITING_TERMINAL_RECEIPT", "WAITING_FOR_TERMINAL"
    lifecycle = str(receipt.get("lifecycle_status") or receipt.get("receipt_validation_status") or "")
    if lifecycle == "RECEIPT_VERIFIED":
        return "TERMINAL_ACKNOWLEDGED", "READY_FOR_RESEARCH"
    return "TERMINAL_RECEIPT_MISMATCH", "NEEDS_RECONCILIATION"


def _promotion_signal(outcome_label: str) -> str:
    if outcome_label == "TERMINAL_ACKNOWLEDGED":
        return "RECEIPT_CONFIRMED_NO_PNL_YET"
    if outcome_label == "ROUTE_REJECTED":
        return "LEARN_REJECTION_CONDITION"
    return "HOLD"


def _latest_by_cycle_intent(events: Iterable[Mapping[str, Any]]) -> Dict[Tuple[str, str], Mapping[str, Any]]:
    out: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for event in events:
        out[_cycle_intent_key(event)] = event
    return out


def _latest_command_by_cycle_intent(events: Iterable[Mapping[str, Any]]) -> Dict[Tuple[str, str], Mapping[str, Any]]:
    out: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for event in events:
        payload = event.get("payload") or {}
        key = (str(event.get("cycle_id") or ""), str(payload.get("intent_id") or ""))
        out[key] = event
    return out


def _latest_receipt_by_command(events: Iterable[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    out: Dict[str, Mapping[str, Any]] = {}
    for event in events:
        payload = event.get("payload") or {}
        command_id = str(payload.get("command_id") or "")
        if command_id:
            out[command_id] = event
    return out


def _cycle_intent_key(event: Mapping[str, Any]) -> Tuple[str, str]:
    payload = event.get("payload") or {}
    return (str(event.get("cycle_id") or ""), str(payload.get("intent_id") or ""))


def _source_refs(*events: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    for event in events:
        if not event:
            continue
        for ref in event.get("source_refs") or []:
            if isinstance(ref, Mapping):
                refs.append(dict(ref))
    return refs


def _summary(records: List[Mapping[str, Any]], event_summary: Mapping[str, Any]) -> Dict[str, Any]:
    labels = Counter(str(record.get("outcome_label")) for record in records)
    learning = Counter(str(record.get("learning_status")) for record in records)
    pnl_values = [
        float(record.get("profit_loss_account") or 0.0)
        for record in records
        if record.get("profit_loss_account") is not None
    ]
    return {
        "memory_record_count": len(records),
        "route_intent_count": len(records),
        "approved_count": sum(1 for record in records if record.get("decision_approved")),
        "rejected_count": sum(1 for record in records if not record.get("decision_approved")),
        "command_joined_count": sum(1 for record in records if record.get("command_id")),
        "receipt_joined_count": sum(1 for record in records if record.get("receipt_id")),
        "verified_receipt_count": labels.get("TERMINAL_ACKNOWLEDGED", 0),
        "receipt_mismatch_count": labels.get("TERMINAL_RECEIPT_MISMATCH", 0),
        "pending_receipt_count": labels.get("AWAITING_TERMINAL_RECEIPT", 0),
        "terminal_history_joined_count": sum(1 for record in records if record.get("terminal_history_status") == "CLOSED_HISTORY_JOINED"),
        "closed_trade_count": sum(1 for record in records if str(record.get("outcome_label", "")).startswith("TRADE_CLOSED_")),
        "closed_profit_count": labels.get("TRADE_CLOSED_PROFIT", 0),
        "closed_loss_count": labels.get("TRADE_CLOSED_LOSS", 0),
        "closed_flat_count": labels.get("TRADE_CLOSED_FLAT", 0),
        "net_profit_loss_account": round(sum(pnl_values), 6),
        "pnl_ready_memory_count": len(pnl_values),
        "mae_ready_count": sum(1 for record in records if record.get("mae") is not None),
        "mfe_ready_count": sum(1 for record in records if record.get("mfe") is not None),
        "outcome_label_counts": dict(labels),
        "learning_status_counts": dict(learning),
        "source_event_count": event_summary.get("event_count", 0),
        "source_cycle_count": event_summary.get("cycle_count", 0),
        "latest_cycle_id": event_summary.get("latest_cycle_id"),
        "event_log_pending_receipt_count": event_summary.get("pending_receipt_count", 0),
    }


def _next_action(summary: Mapping[str, Any]) -> str:
    if int(summary.get("terminal_history_joined_count", 0) or 0) > 0:
        return "Queue condition-lab, walk-forward replay, and strategy-development tasks from closed-trade PnL memory rows."
    if int(summary.get("receipt_joined_count", 0) or 0) == 0:
        return "Run/attach the MT4 EA so terminal receipts exist, then rerun agent memory to join receipts into learning rows."
    if int(summary.get("pending_receipt_count", 0) or 0) > 0:
        return "Keep processing terminal receipts until pending command memory rows are resolved."
    return "Queue condition-lab and walk-forward research tasks from READY_FOR_RESEARCH memory rows."


def _memory_id(*parts: object) -> str:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:16]
    return f"agent-memory-{digest}"
