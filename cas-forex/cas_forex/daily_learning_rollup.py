"""Daily learning rollup for the CAS Forex agent desk.

The agent desk now writes route memory, research tasks, strategy work items,
and patch/replay decisions. This module compresses one trading day into a
single learning record for the 30-day improvement window.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from cas_forex.agent_memory import AgentMemoryError, load_latest_agent_memory_report
from cas_forex.agent_research_queue import (
    AgentResearchQueueError,
    load_latest_agent_research_queue_report,
)
from cas_forex.agent_state import AgentCycleError, load_latest_agent_cycle_report
from cas_forex.strategy_dev_queue import StrategyDevQueueError, load_latest_strategy_dev_queue_report
from cas_forex.strategy_patch_runner import (
    StrategyPatchRunnerError,
    load_latest_strategy_patch_runner_report,
)
from cas_forex.terminal_history_ingest import (
    TerminalHistoryIngestError,
    load_latest_terminal_history_ingest_report,
)
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "daily_learning_rollup"
REPORT_KIND = "cas_forex_daily_learning_rollup_report"
ROLLUP_SCHEMA = "cas_forex_daily_learning_rollup.v1"
CLAIM_BOUNDARY = (
    "Daily learning rollups summarize paper/demo agent cycles, memory, terminal "
    "history, research queues, strategy-development queues, and patch-runner "
    "decisions for the 30-day improvement window. They do not by themselves "
    "execute live broker orders, create broker ACCEPT, deposit, withdraw, move "
    "bank/card funds, automate payouts, or claim live-income readiness."
)


class DailyLearningRollupError(ValueError):
    """Raised when a daily learning rollup cannot be built or loaded."""


def build_daily_learning_rollup_report(
    *,
    trading_date: Optional[str] = None,
    day_index: Optional[int] = None,
    agent_cycle_report: Optional[Mapping[str, Any]] = None,
    memory_report: Optional[Mapping[str, Any]] = None,
    terminal_history_report: Optional[Mapping[str, Any]] = None,
    research_queue_report: Optional[Mapping[str, Any]] = None,
    strategy_dev_queue_report: Optional[Mapping[str, Any]] = None,
    strategy_patch_runner_report: Optional[Mapping[str, Any]] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build and optionally persist the daily 30-day-window rollup."""

    sources = _load_sources(
        agent_cycle_report=agent_cycle_report,
        memory_report=memory_report,
        terminal_history_report=terminal_history_report,
        research_queue_report=research_queue_report,
        strategy_dev_queue_report=strategy_dev_queue_report,
        strategy_patch_runner_report=strategy_patch_runner_report,
    )
    rollup_date = trading_date or _infer_trading_date(sources)
    records = [
        dict(record)
        for record in (sources["memory"].get("memory_records") or [])
        if isinstance(record, Mapping) and _record_is_for_date(record, rollup_date)
    ]
    # If the latest memory rows do not carry same-day timestamps, keep the
    # latest report intact instead of emitting an empty day.
    if not records:
        records = [
            dict(record)
            for record in (sources["memory"].get("memory_records") or [])
            if isinstance(record, Mapping)
        ]

    patch_decisions = [
        dict(decision)
        for decision in (sources["patch"].get("decisions") or [])
        if isinstance(decision, Mapping)
    ]
    research_tasks = [
        dict(task)
        for task in (sources["research"].get("research_tasks") or [])
        if isinstance(task, Mapping)
    ]
    strategy_items = [
        dict(item)
        for item in (sources["strategy_dev"].get("work_items") or [])
        if isinstance(item, Mapping)
    ]
    terminal_history_updates = [
        dict(update)
        for update in (sources["terminal_history"].get("memory_updates") or [])
        if isinstance(update, Mapping)
    ]

    summary = _summary(
        records=records,
        patch_decisions=patch_decisions,
        research_tasks=research_tasks,
        strategy_items=strategy_items,
        terminal_history_updates=terminal_history_updates,
        sources=sources,
    )
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "rollup_status": _rollup_status(summary),
        "schema": ROLLUP_SCHEMA,
        "trading_date": rollup_date,
        "day_index": int(day_index or 1),
        "window_days": 30,
        "source_reports": _source_reports(sources),
        "output_dir": str(Path(output_dir)),
        "summary": summary,
        "by_agent": _aggregate(records, "agent_id"),
        "by_symbol": _aggregate(records, "symbol"),
        "by_strategy": _aggregate(records, "strategy_setting"),
        "by_condition_cell": _aggregate_condition_cells(records),
        "promotion_candidates": _promotion_candidates(patch_decisions, records),
        "demotion_flags": _demotion_flags(patch_decisions, records),
        "queued_follow_up_work": _queued_follow_up_work(research_tasks, strategy_items, patch_decisions),
        "terminal_blockers": _terminal_blockers(summary, patch_decisions, sources),
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        paths = write_daily_learning_rollup_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_daily_learning_rollup_report(report)
    return report


def write_daily_learning_rollup_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    """Write rollup JSON, Markdown, and JSONL summary rows."""

    validate_daily_learning_rollup_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"daily-learning-rollup-{stamp}-report.json"
    md_path = target_dir / f"daily-learning-rollup-{stamp}-report.md"
    jsonl_path = target_dir / f"daily-learning-rollup-{stamp}.jsonl"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_daily_learning_rollup_markdown(report), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(_jsonl_record(report), sort_keys=True, ensure_ascii=False) + "\n")
    return {"json": json_path, "markdown": md_path, "jsonl": jsonl_path}


def load_latest_daily_learning_rollup_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("daily-learning-rollup-*-report.json"))
    if not files:
        raise DailyLearningRollupError(f"No daily learning rollup reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_daily_learning_rollup_report(payload)
    return payload


def validate_daily_learning_rollup_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "rollup_status",
        "schema",
        "trading_date",
        "day_index",
        "window_days",
        "source_reports",
        "summary",
        "by_agent",
        "by_symbol",
        "by_strategy",
        "by_condition_cell",
        "promotion_candidates",
        "demotion_flags",
        "queued_follow_up_work",
        "terminal_blockers",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise DailyLearningRollupError(f"daily learning rollup missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise DailyLearningRollupError("unexpected daily learning rollup report_kind")
    if payload.get("schema") != ROLLUP_SCHEMA:
        raise DailyLearningRollupError("unexpected daily learning rollup schema")
    boundary = str(payload.get("claim_boundary", ""))
    if "do not by themselves execute live broker orders" not in boundary:
        raise DailyLearningRollupError("daily learning rollup claim boundary must preserve execution boundary")
    if "claim live-income readiness" not in boundary:
        raise DailyLearningRollupError("daily learning rollup claim boundary must preserve income-claim boundary")


def render_daily_learning_rollup_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Daily Learning Rollup",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('rollup_status')}`",
        f"Trading date: `{report.get('trading_date')}`",
        f"30-day window day: `{report.get('day_index')}` / `{report.get('window_days')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Routes: `{summary.get('route_count')}`",
        f"- Approved/rejected: `{summary.get('approved_count')}` / `{summary.get('rejected_count')}`",
        f"- Commands/receipts pending: `{summary.get('executed_count')}` / `{summary.get('pending_receipt_count')}`",
        f"- Closed wins/losses/flats: `{summary.get('win_count')}` / `{summary.get('loss_count')}` / `{summary.get('flat_count')}`",
        f"- Net PnL: `{summary.get('net_profit_loss_account')}`",
        f"- Profit factor: `{summary.get('profit_factor')}`",
        f"- Expectancy: `{summary.get('expectancy_account')}`",
        f"- Patch/replay decisions: `{summary.get('patch_candidate_count')}` / `{summary.get('replay_job_count')}`",
        f"- Chain verified: `{summary.get('chain_verified')}`",
        "",
        "## Follow-Up Work",
        "",
    ]
    for item in report.get("queued_follow_up_work") or []:
        lines.append(
            "- "
            f"`{item.get('work_type')}` `{item.get('status')}` "
            f"`{item.get('source_id')}`: {item.get('plain_english')}"
        )
    lines.extend(["", "## Terminal Blockers", ""])
    for blocker in report.get("terminal_blockers") or []:
        lines.append(f"- `{blocker.get('blocker_id')}`: {blocker.get('plain_english')}")
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _load_sources(
    *,
    agent_cycle_report: Optional[Mapping[str, Any]],
    memory_report: Optional[Mapping[str, Any]],
    terminal_history_report: Optional[Mapping[str, Any]],
    research_queue_report: Optional[Mapping[str, Any]],
    strategy_dev_queue_report: Optional[Mapping[str, Any]],
    strategy_patch_runner_report: Optional[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    return {
        "cycle": _load_or_empty(agent_cycle_report, load_latest_agent_cycle_report, AgentCycleError),
        "memory": _load_or_empty(memory_report, load_latest_agent_memory_report, AgentMemoryError),
        "terminal_history": _load_or_empty(
            terminal_history_report,
            load_latest_terminal_history_ingest_report,
            TerminalHistoryIngestError,
        ),
        "research": _load_or_empty(research_queue_report, load_latest_agent_research_queue_report, AgentResearchQueueError),
        "strategy_dev": _load_or_empty(strategy_dev_queue_report, load_latest_strategy_dev_queue_report, StrategyDevQueueError),
        "patch": _load_or_empty(strategy_patch_runner_report, load_latest_strategy_patch_runner_report, StrategyPatchRunnerError),
    }


def _load_or_empty(
    provided: Optional[Mapping[str, Any]],
    loader: Any,
    expected_error: type[Exception],
) -> Dict[str, Any]:
    if provided is not None:
        return dict(provided)
    try:
        return dict(loader())
    except expected_error:
        return {"summary": {}}


def _infer_trading_date(sources: Mapping[str, Mapping[str, Any]]) -> str:
    for key in ("memory", "cycle", "terminal_history", "patch"):
        value = str(sources.get(key, {}).get("created_at") or "")
        if len(value) >= 10:
            return value[:10]
    return date.today().isoformat()


def _record_is_for_date(record: Mapping[str, Any], trading_date: str) -> bool:
    created = str(record.get("created_at") or "")
    if len(created) >= 10:
        return created[:10] == trading_date
    return False


def _summary(
    *,
    records: List[Mapping[str, Any]],
    patch_decisions: List[Mapping[str, Any]],
    research_tasks: List[Mapping[str, Any]],
    strategy_items: List[Mapping[str, Any]],
    terminal_history_updates: List[Mapping[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    memory_summary = sources["memory"].get("summary") or {}
    cycle_summary = sources["cycle"].get("summary") or {}
    terminal_summary = sources["terminal_history"].get("summary") or {}
    patch_summary = sources["patch"].get("summary") or {}
    research_summary = sources["research"].get("summary") or {}
    strategy_summary = sources["strategy_dev"].get("summary") or {}
    pnl_values = [
        float(record.get("profit_loss_account") or 0.0)
        for record in records
        if record.get("profit_loss_account") is not None
    ]
    gross_profit = round(sum(value for value in pnl_values if value > 0), 6)
    gross_loss = round(abs(sum(value for value in pnl_values if value < 0)), 6)
    closed_count = _count_closed(records, memory_summary, terminal_summary)
    return {
        "route_count": int(memory_summary.get("route_intent_count") or cycle_summary.get("route_intent_count") or len(records)),
        "approved_count": int(memory_summary.get("approved_count") or cycle_summary.get("approved_intent_count") or 0),
        "rejected_count": int(memory_summary.get("rejected_count") or cycle_summary.get("rejected_intent_count") or 0),
        "executed_count": int(memory_summary.get("command_joined_count") or cycle_summary.get("terminal_command_count") or 0),
        "receipt_joined_count": int(memory_summary.get("receipt_joined_count") or 0),
        "pending_receipt_count": int(memory_summary.get("pending_receipt_count") or cycle_summary.get("pending_receipt_count") or 0),
        "terminal_history_joined_count": int(memory_summary.get("terminal_history_joined_count") or 0),
        "terminal_history_update_count": int(terminal_summary.get("memory_update_count") or len(terminal_history_updates)),
        "closed_count": closed_count,
        "win_count": int(memory_summary.get("closed_profit_count") or terminal_summary.get("closed_profit_count") or 0),
        "loss_count": int(memory_summary.get("closed_loss_count") or terminal_summary.get("closed_loss_count") or 0),
        "flat_count": int(memory_summary.get("closed_flat_count") or 0),
        "gross_profit_account": gross_profit,
        "gross_loss_account": gross_loss,
        "net_profit_loss_account": round(sum(pnl_values) if pnl_values else float(memory_summary.get("net_profit_loss_account") or terminal_summary.get("net_profit_loss_account") or 0.0), 6),
        "profit_factor": _profit_factor(gross_profit, gross_loss, closed_count),
        "expectancy_account": _expectancy(pnl_values, closed_count),
        "max_drawdown_pct": None,
        "research_task_count": int(research_summary.get("task_count") or len(research_tasks)),
        "strategy_item_count": int(strategy_summary.get("item_count") or len(strategy_items)),
        "patch_decision_count": int(patch_summary.get("decision_count") or len(patch_decisions)),
        "patch_candidate_count": int(patch_summary.get("patch_candidate_count") or _count_type(patch_decisions, "PATCH_CANDIDATE")),
        "replay_job_count": int(patch_summary.get("replay_job_count") or _count_type(patch_decisions, "REPLAY_JOB")),
        "promotion_candidate_count": int(patch_summary.get("promotion_review_count") or _count_type(patch_decisions, "PROMOTION_REVIEW")),
        "demotion_flag_count": int(patch_summary.get("demotion_review_count") or _count_type(patch_decisions, "DEMOTION_REVIEW")),
        "terminal_input_required_count": int(patch_summary.get("terminal_input_required_count") or _count_type(patch_decisions, "TERMINAL_INPUT_REQUIRED")),
        "source_report_count": sum(1 for source in sources.values() if source.get("report_kind")),
        "chain_verified": _chain_verified(sources),
        "readiness_label": _readiness_label(memory_summary, terminal_summary, patch_summary),
    }


def _aggregate(records: Iterable[Mapping[str, Any]], key: str) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record.get(key) or "UNKNOWN")].append(record)
    return [_aggregate_group(name, group) for name, group in sorted(groups.items())]


def _aggregate_condition_cells(records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        key = "|".join(
            [
                str(record.get("symbol") or "UNKNOWN"),
                str(record.get("timeframe") or "UNKNOWN"),
                str(record.get("strategy_setting") or "UNKNOWN"),
                str(record.get("action") or "UNKNOWN"),
            ]
        )
        groups[key].append(record)
    return [_aggregate_group(name, group) for name, group in sorted(groups.items())]


def _aggregate_group(name: str, group: List[Mapping[str, Any]]) -> Dict[str, Any]:
    pnl = [float(record.get("profit_loss_account") or 0.0) for record in group if record.get("profit_loss_account") is not None]
    labels = Counter(str(record.get("outcome_label") or "UNKNOWN") for record in group)
    return {
        "key": name,
        "route_count": len(group),
        "approved_count": sum(1 for record in group if record.get("decision_approved")),
        "rejected_count": sum(1 for record in group if not record.get("decision_approved")),
        "closed_count": sum(1 for record in group if str(record.get("outcome_label") or "").startswith("TRADE_CLOSED_")),
        "net_profit_loss_account": round(sum(pnl), 6),
        "outcome_label_counts": dict(sorted(labels.items())),
    }


def _promotion_candidates(patch_decisions: List[Mapping[str, Any]], records: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    items = [
        _decision_candidate(decision)
        for decision in patch_decisions
        if str(decision.get("decision_type") or "") == "PROMOTION_REVIEW"
    ]
    for record in records:
        if record.get("promotion_signal") not in {None, "", "HOLD"}:
            items.append(
                {
                    "candidate_id": record.get("memory_id"),
                    "source": "agent_memory",
                    "candidate_type": record.get("promotion_signal"),
                    "symbols": [record.get("symbol")],
                    "plain_english": "Memory row carries a promotion signal.",
                }
            )
    return items


def _demotion_flags(patch_decisions: List[Mapping[str, Any]], records: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    flags = [
        _decision_candidate(decision)
        for decision in patch_decisions
        if str(decision.get("decision_type") or "") == "DEMOTION_REVIEW"
    ]
    counts = Counter()
    for record in records:
        for flag in record.get("demotion_flags") or []:
            counts[str(flag)] += 1
    flags.extend(
        {
            "candidate_id": flag,
            "source": "agent_memory",
            "candidate_type": "DEMOTION_FLAG",
            "count": count,
            "plain_english": "Memory rows carry this demotion or hold-back flag.",
        }
        for flag, count in sorted(counts.items())
    )
    return flags


def _queued_follow_up_work(
    research_tasks: List[Mapping[str, Any]],
    strategy_items: List[Mapping[str, Any]],
    patch_decisions: List[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for task in research_tasks:
        out.append(
            {
                "work_type": "RESEARCH_TASK",
                "source_id": task.get("task_id"),
                "status": task.get("status", "QUEUED"),
                "priority": task.get("priority"),
                "plain_english": task.get("research_question") or task.get("plain_english_goal"),
            }
        )
    for item in strategy_items:
        out.append(
            {
                "work_type": "STRATEGY_DEV_ITEM",
                "source_id": item.get("item_id"),
                "status": item.get("status"),
                "priority": item.get("priority"),
                "plain_english": item.get("plain_english_goal"),
            }
        )
    for decision in patch_decisions:
        out.append(
            {
                "work_type": "PATCH_RUNNER_DECISION",
                "source_id": decision.get("decision_id"),
                "status": decision.get("status"),
                "priority": decision.get("priority"),
                "plain_english": decision.get("plain_english_decision"),
            }
        )
    return sorted(out, key=lambda item: (int(item.get("priority") or 99), str(item.get("work_type")), str(item.get("source_id"))))


def _terminal_blockers(
    summary: Mapping[str, Any],
    patch_decisions: List[Mapping[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []
    if int(summary.get("pending_receipt_count") or 0) > 0:
        blockers.append(
            {
                "blocker_id": "pending_terminal_receipts",
                "count": summary.get("pending_receipt_count"),
                "plain_english": "MT4/MT5 command rows are still waiting for terminal receipt JSON.",
            }
        )
    terminal_history = sources["terminal_history"].get("summary") or {}
    if int(terminal_history.get("history_record_count") or 0) == 0:
        blockers.append(
            {
                "blocker_id": "missing_terminal_close_history",
                "count": 0,
                "plain_english": "No exported terminal close-history rows have joined memory yet.",
            }
        )
    for decision in patch_decisions:
        if str(decision.get("status") or "").startswith("BLOCKED"):
            blockers.append(
                {
                    "blocker_id": decision.get("decision_id"),
                    "count": 1,
                    "plain_english": decision.get("plain_english_decision"),
                }
            )
    return blockers


def _source_reports(sources: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        key: {
            "report_kind": source.get("report_kind"),
            "report_path": source.get("report_path") or (source.get("artifact_paths") or {}).get("json"),
            "created_at": source.get("created_at"),
            "status": source.get("memory_status")
            or source.get("ingest_status")
            or source.get("queue_status")
            or source.get("runner_status")
            or source.get("workflow_status")
            or source.get("execution_mode"),
        }
        for key, source in sources.items()
    }


def _jsonl_record(report: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema": report.get("schema"),
        "trading_date": report.get("trading_date"),
        "day_index": report.get("day_index"),
        "rollup_status": report.get("rollup_status"),
        "summary": report.get("summary"),
        "claim_boundary": report.get("claim_boundary"),
    }


def _decision_candidate(decision: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": decision.get("decision_id"),
        "source": "strategy_patch_runner",
        "candidate_type": decision.get("decision_type"),
        "symbols": list(decision.get("symbols") or []),
        "plain_english": decision.get("plain_english_decision"),
    }


def _count_closed(records: List[Mapping[str, Any]], memory_summary: Mapping[str, Any], terminal_summary: Mapping[str, Any]) -> int:
    return int(
        memory_summary.get("closed_trade_count")
        or terminal_summary.get("closed_trade_count")
        or sum(1 for record in records if str(record.get("outcome_label") or "").startswith("TRADE_CLOSED_"))
    )


def _profit_factor(gross_profit: float, gross_loss: float, closed_count: int) -> Optional[float]:
    if closed_count == 0:
        return None
    if gross_loss == 0:
        return None if gross_profit == 0 else round(gross_profit, 6)
    return round(gross_profit / gross_loss, 6)


def _expectancy(pnl_values: List[float], closed_count: int) -> Optional[float]:
    if closed_count == 0:
        return None
    return round(sum(pnl_values) / closed_count, 6)


def _count_type(items: Iterable[Mapping[str, Any]], item_type: str) -> int:
    return sum(1 for item in items if item.get("decision_type") == item_type)


def _chain_verified(sources: Mapping[str, Mapping[str, Any]]) -> bool:
    required = {"memory", "research", "strategy_dev", "patch"}
    return all(bool(sources[key].get("report_kind")) for key in required)


def _readiness_label(
    memory_summary: Mapping[str, Any],
    terminal_summary: Mapping[str, Any],
    patch_summary: Mapping[str, Any],
) -> str:
    if int(memory_summary.get("closed_trade_count") or 0) > 0:
        return "DAILY_LEARNING_HAS_CLOSED_PNL"
    if int(terminal_summary.get("history_record_count") or 0) == 0:
        return "WAITING_FOR_TERMINAL_CLOSE_HISTORY"
    if int(patch_summary.get("terminal_input_required_count") or 0) > 0:
        return "WAITING_FOR_TERMINAL_INPUTS"
    return "DAILY_LEARNING_READY_FOR_REPLAY"


def _rollup_status(summary: Mapping[str, Any]) -> str:
    if not summary.get("chain_verified"):
        return "DAILY_LEARNING_ROLLUP_PARTIAL"
    if int(summary.get("closed_count") or 0) == 0:
        return "DAILY_LEARNING_ROLLUP_BUILT_WAITING_FOR_CLOSED_PNL"
    return "DAILY_LEARNING_ROLLUP_BUILT"


def _next_action(summary: Mapping[str, Any]) -> str:
    if int(summary.get("closed_count") or 0) == 0:
        return "Generate terminal receipts and closed-history exports, then rerun memory, queues, patch runner, and daily rollup."
    if int(summary.get("patch_candidate_count") or 0) > 0:
        return "Review patch candidates and replay jobs, then carry accepted decisions into the next session plan."
    return "Use the rollup to tune the next autowake trading session and 30-day improvement window."
