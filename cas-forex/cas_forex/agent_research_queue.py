"""Research-task queue builder for the CAS Forex agent desk.

This module turns agent outcome-memory rows into concrete research work for
condition lab, walk-forward, replay, strategy development, and terminal
joinback. It is the next step after memory: facts become tasks.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from cas_forex.agent_memory import AgentMemoryError, load_latest_agent_memory_report
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "agent_research_queue"
REPORT_KIND = "cas_forex_agent_research_queue_report"
TASK_SCHEMA = "cas_forex_research_task_packet.v1"
CLAIM_BOUNDARY = (
    "Agent research queue tasks organize paper/demo memory rows into research "
    "and strategy-development work. They do not by themselves execute live "
    "broker orders, create broker ACCEPT, deposit, withdraw, move bank/card "
    "funds, or automate payouts. Autonomous trading and money movement remain "
    "allowed elsewhere, but only through order_dispatch.py, execution_guard.py, "
    "broker/provider truth, risk, receipt, and kill-switch gates."
)


class AgentResearchQueueError(ValueError):
    """Raised when the agent research queue cannot be built or loaded."""


def build_agent_research_queue_report(
    *,
    memory_report: Optional[Mapping[str, Any]] = None,
    memory_report_dir: Optional[Path | str] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build and optionally persist research tasks from the latest memory."""

    if memory_report is None:
        try:
            if memory_report_dir is None:
                memory_report = load_latest_agent_memory_report()
            else:
                memory_report = load_latest_agent_memory_report(memory_report_dir)
        except AgentMemoryError as exc:
            raise AgentResearchQueueError(str(exc)) from exc

    tasks = build_research_tasks(memory_report)
    summary = _summary(tasks, memory_report)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "queue_status": _queue_status(tasks),
        "schema": TASK_SCHEMA,
        "memory_report_path": memory_report.get("report_path")
        or (memory_report.get("artifact_paths") or {}).get("json"),
        "output_dir": str(Path(output_dir)),
        "summary": summary,
        "research_tasks": tasks,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        paths = write_agent_research_queue_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_agent_research_queue_report(report)
    return report


def build_research_tasks(memory_report: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Return deterministic research tasks from memory rows."""

    records = [dict(record) for record in memory_report.get("memory_records") or []]
    if not records:
        return []

    tasks: List[Dict[str, Any]] = []
    pending = [record for record in records if record.get("outcome_label") == "AWAITING_TERMINAL_RECEIPT"]
    rejected = [record for record in records if record.get("outcome_label") == "ROUTE_REJECTED"]
    acknowledged = [record for record in records if record.get("outcome_label") == "TERMINAL_ACKNOWLEDGED"]
    mismatched = [record for record in records if record.get("outcome_label") == "TERMINAL_RECEIPT_MISMATCH"]

    receipt_task_id: Optional[str] = None
    if pending:
        receipt_task_id = _task_id("terminal_receipt_joinback", pending)
        tasks.append(
            _task(
                task_id=receipt_task_id,
                task_type="TERMINAL_RECEIPT_JOINBACK",
                priority=1,
                records=pending,
                research_question=(
                    "Which pending MT4 paper/demo command rows have terminal receipt, "
                    "fill, slippage, account snapshot, and close/history evidence?"
                ),
                plain_english_goal=(
                    "Finish the handoff from CAS command files back to terminal facts so "
                    "approved trade ideas stop sitting in limbo."
                ),
                success_metric=(
                    "Resolve every pending command memory row to a verified receipt, "
                    "explicit terminal failure, or documented missing-terminal reason."
                ),
                required_inputs=[
                    "MT4 mailbox receipt JSON files",
                    "CASForexBridgeEA.mq4 heartbeat JSON",
                    "terminal account snapshot",
                    "terminal close/history export when available",
                ],
                produces=[
                    "terminal_receipt_ingest_rerun",
                    "agent_memory_rerun",
                    "closed_trade_history_requirements",
                ],
                blocked_by=["MT4 terminal compile/attach/run verification"],
            )
        )

    if mismatched:
        tasks.append(
            _task(
                task_id=_task_id("terminal_receipt_reconcile", mismatched),
                task_type="TERMINAL_RECEIPT_RECONCILIATION",
                priority=1,
                records=mismatched,
                research_question="Which command/receipt fields disagree, and what terminal or CAS mapping caused the mismatch?",
                plain_english_goal="Fix receipt mismatches before the same symbol is allowed to continue cycling.",
                success_metric="Every mismatched receipt has a named cause and either reconciles or remains explicitly locked.",
                required_inputs=["receipt JSON", "matching command JSON", "event journal rows"],
                produces=["reconciliation_patch_candidate", "symbol_unlock_decision"],
            )
        )

    if rejected:
        tasks.append(
            _task(
                task_id=_task_id("conflict_key_refinement", rejected),
                task_type="OVERSEER_CONFLICT_KEY_REFINEMENT",
                priority=2,
                records=rejected,
                research_question=(
                    "Should same-symbol routing conflicts split by side, timeframe, strategy family, "
                    "or existing receipt state so valid compounding/intraday routes are not blocked unnecessarily?"
                ),
                plain_english_goal=(
                    "Keep the overseer from throwing away useful opportunities just because "
                    "another agent touched the same symbol."
                ),
                success_metric=(
                    "Produce a conflict-key rule that separates true duplicate spam from useful "
                    "multi-agent compounding or timeframe stacking."
                ),
                required_inputs=[
                    "rejected route memory rows",
                    "pending receipt state",
                    "strategy family and timeframe tags",
                ],
                produces=["agent_overseer_conflict_key_patch_candidate", "condition_lab_task_batch"],
            )
        )
        for key, group in _group_records(rejected, ("symbol", "timeframe", "action")).items():
            symbol, timeframe, action = key
            tasks.append(
                _task(
                    task_id=_task_id(f"condition_lab_{symbol}_{timeframe}_{action}", group),
                    task_type="CONDITION_LAB_REJECTION_ANALYSIS",
                    priority=2 if len(group) >= 5 else 3,
                    records=group,
                    research_question=(
                        f"What market/account/context conditions caused `{symbol}` `{timeframe}` "
                        f"`{action}` to be rejected, and were those rejections useful or too coarse?"
                    ),
                    plain_english_goal="Turn rejected routes into better filters instead of wasted log rows.",
                    success_metric=(
                        "Classify the rejection bucket as useful guardrail, missed opportunity, "
                        "or needs more terminal evidence."
                    ),
                    required_inputs=[
                        "condition_snapshot_open",
                        "decision_reasons",
                        "pending receipt state",
                        "condition tally report",
                    ],
                    produces=["condition_lab_bucket_review", "overseer_rule_candidate"],
                )
            )

    if pending:
        for key, group in _group_records(pending, ("symbol", "timeframe", "action")).items():
            symbol, timeframe, action = key
            tasks.append(
                _task(
                    task_id=_task_id(f"walk_forward_receipt_replay_{symbol}_{timeframe}_{action}", group),
                    task_type="WALK_FORWARD_RECEIPT_REPLAY",
                    priority=3,
                    records=group,
                    research_question=(
                        f"After receipts arrive, did `{symbol}` `{timeframe}` `{action}` "
                        "keep edge under spread, slippage, fill timing, and same-symbol exposure?"
                    ),
                    plain_english_goal=(
                        "Use the terminal facts to decide whether this route should keep running, "
                        "scale up, scale down, or change rules."
                    ),
                    success_metric=(
                        "A rerun produces realized fill/slippage/close facts and a promotion, hold, "
                        "or demotion decision for the route."
                    ),
                    required_inputs=[
                        "verified terminal receipts",
                        "terminal close/history export",
                        "walk-forward replay report",
                    ],
                    produces=["walk_forward_rerun_request", "strategy_promotion_review_candidate"],
                    blocked_by=[receipt_task_id] if receipt_task_id else [],
                )
            )

    if acknowledged:
        for key, group in _group_records(acknowledged, ("symbol", "timeframe", "action")).items():
            symbol, timeframe, action = key
            tasks.append(
                _task(
                    task_id=_task_id(f"strategy_dev_{symbol}_{timeframe}_{action}", group),
                    task_type="STRATEGY_DEV_REPLAY",
                    priority=2,
                    records=group,
                    research_question=(
                        f"Do verified `{symbol}` `{timeframe}` `{action}` receipts support compounding, "
                        "tighter exits, or timeframe-specific sizing?"
                    ),
                    plain_english_goal="Turn verified terminal acknowledgements into strategy updates.",
                    success_metric="Produce a replay-backed strategy change, hold decision, or demotion reason.",
                    required_inputs=["verified receipts", "close/history data", "Forex Fury replay result"],
                    produces=["strategy_dev_task", "adaptive_compounding_review"],
                )
            )

    if pending and not acknowledged:
        tasks.append(
            _task(
                task_id=_task_id("terminal_history_pnl_schema", pending),
                task_type="TERMINAL_HISTORY_PNL_SCHEMA",
                priority=2,
                records=pending,
                research_question=(
                    "What exact terminal history fields are needed to fill profit_loss_r, "
                    "profit_loss_pips, MAE, MFE, close_reason, commission, swap, and slippage?"
                ),
                plain_english_goal="Prepare the closed-trade learning schema before receipts arrive.",
                success_metric="Define and test the close/history ingest contract needed for full PnL memory.",
                required_inputs=["MT4 account history export shape", "receipt schema", "agent memory schema"],
                produces=["terminal_history_ingest_spec", "agent_memory_close_fields_patch_candidate"],
                blocked_by=["MT4 terminal history/export access"],
            )
        )

    return sorted(tasks, key=lambda task: (int(task["priority"]), str(task["task_type"]), str(task["task_id"])))


def write_agent_research_queue_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    """Write report JSON/Markdown plus queue JSONL."""

    validate_agent_research_queue_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"agent-research-queue-{stamp}-report.json"
    md_path = target_dir / f"agent-research-queue-{stamp}-report.md"
    jsonl_path = target_dir / f"agent-research-queue-{stamp}.jsonl"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_agent_research_queue_markdown(report), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for task in report.get("research_tasks") or []:
            handle.write(json.dumps(task, sort_keys=True, ensure_ascii=False) + "\n")
    return {"json": json_path, "markdown": md_path, "jsonl": jsonl_path}


def load_latest_agent_research_queue_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("agent-research-queue-*-report.json"))
    if not files:
        raise AgentResearchQueueError(f"No agent research queue reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_agent_research_queue_report(payload)
    return payload


def validate_agent_research_queue_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "queue_status",
        "schema",
        "summary",
        "research_tasks",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise AgentResearchQueueError(f"agent research queue report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise AgentResearchQueueError("unexpected agent research queue report_kind")
    if payload.get("schema") != TASK_SCHEMA:
        raise AgentResearchQueueError("unexpected agent research queue schema")
    if "do not by themselves execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise AgentResearchQueueError("agent research queue claim boundary must preserve execution boundary")
    if not isinstance(payload.get("research_tasks"), list):
        raise AgentResearchQueueError("research_tasks must be a list")
    for task in payload.get("research_tasks") or []:
        validate_research_task(task)


def validate_research_task(task: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "task_id",
        "task_type",
        "priority",
        "status",
        "source_memory_ids",
        "research_question",
        "symbols",
        "timeframes",
        "families",
        "success_metric",
        "claim_boundary",
    }
    missing = required.difference(task)
    if missing:
        raise AgentResearchQueueError(f"research task missing fields: {sorted(missing)}")
    if task.get("schema") != TASK_SCHEMA:
        raise AgentResearchQueueError("unexpected research task schema")
    if not isinstance(task.get("source_memory_ids"), list):
        raise AgentResearchQueueError("source_memory_ids must be a list")
    if "do not by themselves execute live broker orders" not in str(task.get("claim_boundary", "")):
        raise AgentResearchQueueError("research task claim boundary must preserve execution boundary")


def render_agent_research_queue_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Agent Research Queue",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('queue_status')}`",
        f"Memory report: `{report.get('memory_report_path')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Tasks: `{summary.get('task_count')}`",
        f"- High priority tasks: `{summary.get('high_priority_task_count')}`",
        f"- Source memory rows: `{summary.get('source_memory_count')}`",
        f"- Pending receipt rows: `{summary.get('source_pending_receipt_count')}`",
        f"- Ready-for-research rows: `{summary.get('source_ready_for_research_count')}`",
        f"- Task types: `{summary.get('task_type_counts')}`",
        "",
        "## Tasks",
        "",
    ]
    for task in report.get("research_tasks") or []:
        lines.append(
            "- "
            f"`P{task.get('priority')}` `{task.get('task_type')}` `{task.get('task_id')}`: "
            f"{task.get('research_question')}"
        )
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _task(
    *,
    task_id: str,
    task_type: str,
    priority: int,
    records: Sequence[Mapping[str, Any]],
    research_question: str,
    plain_english_goal: str,
    success_metric: str,
    required_inputs: Sequence[str],
    produces: Sequence[str],
    blocked_by: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    symbols = _sorted_unique(record.get("symbol") for record in records)
    timeframes = _sorted_unique(record.get("timeframe") for record in records)
    families = _families(records)
    agents = _sorted_unique(record.get("agent_id") for record in records)
    actions = _sorted_unique(record.get("action") for record in records)
    labels = _sorted_unique(record.get("outcome_label") for record in records)
    task = {
        "schema": TASK_SCHEMA,
        "task_id": task_id,
        "task_type": task_type,
        "priority": priority,
        "status": "QUEUED",
        "source_memory_ids": _sorted_unique(record.get("memory_id") for record in records),
        "source_outcome_labels": labels,
        "research_question": research_question,
        "plain_english_goal": plain_english_goal,
        "symbols": symbols,
        "timeframes": timeframes,
        "families": families,
        "agents": agents,
        "actions": actions,
        "success_metric": success_metric,
        "required_inputs": list(required_inputs),
        "produces": list(produces),
        "blocked_by": list(blocked_by or []),
        "source_counts": {
            "memory_rows": len(records),
            "pending_receipts": sum(1 for record in records if record.get("outcome_label") == "AWAITING_TERMINAL_RECEIPT"),
            "rejected_routes": sum(1 for record in records if record.get("outcome_label") == "ROUTE_REJECTED"),
            "verified_receipts": sum(1 for record in records if record.get("outcome_label") == "TERMINAL_ACKNOWLEDGED"),
            "receipt_mismatches": sum(1 for record in records if record.get("outcome_label") == "TERMINAL_RECEIPT_MISMATCH"),
        },
        "created_at": utc_now().isoformat(),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    validate_research_task(task)
    return task


def _summary(tasks: Sequence[Mapping[str, Any]], memory_report: Mapping[str, Any]) -> Dict[str, Any]:
    memory_summary = memory_report.get("summary") or {}
    type_counts = Counter(str(task.get("task_type")) for task in tasks)
    priority_counts = Counter(str(task.get("priority")) for task in tasks)
    status_counts = Counter(str(task.get("status")) for task in tasks)
    return {
        "task_count": len(tasks),
        "queued_task_count": status_counts.get("QUEUED", 0),
        "high_priority_task_count": sum(1 for task in tasks if int(task.get("priority", 99)) <= 2),
        "task_type_counts": dict(type_counts),
        "priority_counts": dict(priority_counts),
        "status_counts": dict(status_counts),
        "source_memory_count": int(memory_summary.get("memory_record_count", 0) or 0),
        "source_pending_receipt_count": int(memory_summary.get("pending_receipt_count", 0) or 0),
        "source_ready_for_research_count": int(
            (memory_summary.get("learning_status_counts") or {}).get("READY_FOR_RESEARCH", 0) or 0
        ),
        "source_receipt_joined_count": int(memory_summary.get("receipt_joined_count", 0) or 0),
        "source_latest_cycle_id": memory_summary.get("latest_cycle_id"),
        "terminal_receipt_task_count": type_counts.get("TERMINAL_RECEIPT_JOINBACK", 0),
        "condition_lab_task_count": type_counts.get("CONDITION_LAB_REJECTION_ANALYSIS", 0),
        "walk_forward_task_count": type_counts.get("WALK_FORWARD_RECEIPT_REPLAY", 0),
        "strategy_dev_task_count": type_counts.get("STRATEGY_DEV_REPLAY", 0),
        "next_task_id": tasks[0].get("task_id") if tasks else None,
    }


def _next_action(summary: Mapping[str, Any]) -> str:
    if int(summary.get("terminal_receipt_task_count", 0) or 0) > 0:
        return "Run the terminal receipt joinback task first, then rerun agent memory and this research queue."
    if int(summary.get("condition_lab_task_count", 0) or 0) > 0:
        return "Run condition-lab rejection analysis tasks, then feed useful rule changes back into the overseer."
    if int(summary.get("strategy_dev_task_count", 0) or 0) > 0:
        return "Run strategy-dev replay tasks and promote, hold, or demote the routed strategy variants."
    return "No research tasks are queued; build fresh memory rows from new agent workflow cycles."


def _queue_status(tasks: Sequence[Mapping[str, Any]]) -> str:
    return "AGENT_RESEARCH_QUEUE_BUILT" if tasks else "AGENT_RESEARCH_QUEUE_EMPTY"


def _task_id(prefix: str, records: Sequence[Mapping[str, Any]]) -> str:
    memory_ids = "|".join(_sorted_unique(record.get("memory_id") for record in records))
    digest = hashlib.sha256(f"{prefix}|{memory_ids}".encode("utf-8")).hexdigest()[:16]
    safe_prefix = "".join(ch if ch.isalnum() else "-" for ch in prefix.lower()).strip("-")
    return f"research-{safe_prefix}-{digest}"


def _group_records(records: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> Dict[Tuple[str, ...], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, ...], List[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[tuple(str(record.get(field) or "unknown") for field in fields)].append(record)
    return dict(grouped)


def _families(records: Sequence[Mapping[str, Any]]) -> List[str]:
    families = []
    for record in records:
        strategy = str(record.get("strategy_setting") or "")
        if "forex_fury" in strategy.lower() or any("forex_fury" in str(ref).lower() for ref in record.get("source_refs") or []):
            families.append("forex_fury")
        elif strategy:
            families.append(strategy.split("_")[0])
        else:
            families.append("unknown")
    return _sorted_unique(families)


def _sorted_unique(values: Iterable[Any]) -> List[str]:
    return sorted({str(value) for value in values if value not in (None, "")})
