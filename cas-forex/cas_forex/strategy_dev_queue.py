"""Strategy-development queue for the CAS Forex agent desk.

Research tasks explain what needs investigation. This module turns those tasks
and any closed-trade memory rows into concrete strategy-development work items:
patch candidates, replay requests, terminal joinback work, and promotion or
demotion reviews.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from cas_forex.agent_memory import AgentMemoryError, load_latest_agent_memory_report
from cas_forex.agent_research_queue import (
    AgentResearchQueueError,
    load_latest_agent_research_queue_report,
)
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "strategy_dev_queue"
REPORT_KIND = "cas_forex_strategy_dev_queue_report"
ITEM_SCHEMA = "cas_forex_strategy_dev_work_item.v1"
CLAIM_BOUNDARY = (
    "Strategy-development queue items organize paper/demo research tasks and "
    "closed-memory rows into replay, patch, promotion, and demotion work. They "
    "do not by themselves execute live broker orders, create broker ACCEPT, "
    "deposit, withdraw, move bank/card funds, or automate payouts."
)


class StrategyDevQueueError(ValueError):
    """Raised when the strategy-development queue cannot be built or loaded."""


def build_strategy_dev_queue_report(
    *,
    research_queue_report: Optional[Mapping[str, Any]] = None,
    research_queue_report_dir: Optional[Path | str] = None,
    memory_report: Optional[Mapping[str, Any]] = None,
    memory_report_dir: Optional[Path | str] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build and optionally persist strategy-development work items."""

    if research_queue_report is None:
        try:
            if research_queue_report_dir is None:
                research_queue_report = load_latest_agent_research_queue_report()
            else:
                research_queue_report = load_latest_agent_research_queue_report(research_queue_report_dir)
        except AgentResearchQueueError as exc:
            raise StrategyDevQueueError(str(exc)) from exc

    if memory_report is None:
        try:
            if memory_report_dir is None:
                memory_report = load_latest_agent_memory_report()
            else:
                memory_report = load_latest_agent_memory_report(memory_report_dir)
        except AgentMemoryError:
            memory_report = {"summary": {}, "memory_records": []}

    items = build_strategy_dev_work_items(research_queue_report, memory_report)
    summary = _summary(items, research_queue_report, memory_report)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "queue_status": _queue_status(items),
        "schema": ITEM_SCHEMA,
        "research_queue_report_path": research_queue_report.get("report_path")
        or (research_queue_report.get("artifact_paths") or {}).get("json"),
        "memory_report_path": memory_report.get("report_path")
        or (memory_report.get("artifact_paths") or {}).get("json"),
        "output_dir": str(Path(output_dir)),
        "summary": summary,
        "work_items": items,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        paths = write_strategy_dev_queue_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_strategy_dev_queue_report(report)
    return report


def build_strategy_dev_work_items(
    research_queue_report: Mapping[str, Any],
    memory_report: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Return deterministic strategy-development items."""

    research_tasks = [
        dict(task)
        for task in research_queue_report.get("research_tasks") or []
        if isinstance(task, Mapping)
    ]
    memory_records = [
        dict(record)
        for record in (memory_report or {}).get("memory_records") or []
        if isinstance(record, Mapping)
    ]
    items = [_work_item_from_research_task(task) for task in research_tasks]
    items.extend(_closed_memory_work_items(memory_records))
    return sorted(items, key=lambda item: (int(item["priority"]), str(item["item_type"]), str(item["item_id"])))


def write_strategy_dev_queue_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    """Write report JSON/Markdown plus JSONL work items."""

    validate_strategy_dev_queue_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"strategy-dev-queue-{stamp}-report.json"
    md_path = target_dir / f"strategy-dev-queue-{stamp}-report.md"
    jsonl_path = target_dir / f"strategy-dev-queue-{stamp}.jsonl"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_strategy_dev_queue_markdown(report), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for item in report.get("work_items") or []:
            handle.write(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n")
    return {"json": json_path, "markdown": md_path, "jsonl": jsonl_path}


def load_latest_strategy_dev_queue_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("strategy-dev-queue-*-report.json"))
    if not files:
        raise StrategyDevQueueError(f"No strategy-development queue reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_strategy_dev_queue_report(payload)
    return payload


def validate_strategy_dev_queue_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "queue_status",
        "schema",
        "summary",
        "work_items",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise StrategyDevQueueError(f"strategy-development queue report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise StrategyDevQueueError("unexpected strategy-development queue report_kind")
    if payload.get("schema") != ITEM_SCHEMA:
        raise StrategyDevQueueError("unexpected strategy-development queue schema")
    if "do not by themselves execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise StrategyDevQueueError("strategy-development queue claim boundary must preserve execution boundary")
    if not isinstance(payload.get("work_items"), list):
        raise StrategyDevQueueError("work_items must be a list")
    for item in payload.get("work_items") or []:
        validate_strategy_dev_work_item(item)


def validate_strategy_dev_work_item(item: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "item_id",
        "item_type",
        "priority",
        "status",
        "source_task_ids",
        "source_memory_ids",
        "symbols",
        "timeframes",
        "hypothesis",
        "plain_english_goal",
        "proposed_change",
        "replay_request",
        "required_inputs",
        "blocked_by",
        "produces",
        "acceptance_checks",
        "claim_boundary",
    }
    missing = required.difference(item)
    if missing:
        raise StrategyDevQueueError(f"strategy-development work item missing fields: {sorted(missing)}")
    if item.get("schema") != ITEM_SCHEMA:
        raise StrategyDevQueueError("unexpected strategy-development work item schema")
    if "do not by themselves execute live broker orders" not in str(item.get("claim_boundary", "")):
        raise StrategyDevQueueError("strategy-development work item claim boundary must preserve execution boundary")


def render_strategy_dev_queue_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Strategy Development Queue",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('queue_status')}`",
        f"Research queue: `{report.get('research_queue_report_path')}`",
        f"Memory report: `{report.get('memory_report_path')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Work items: `{summary.get('item_count')}`",
        f"- Queued items: `{summary.get('queued_item_count')}`",
        f"- Blocked items: `{summary.get('blocked_item_count')}`",
        f"- Ready for replay: `{summary.get('ready_for_replay_count')}`",
        f"- Patch candidates: `{summary.get('patch_candidate_count')}`",
        f"- Promotion reviews: `{summary.get('promotion_review_count')}`",
        f"- Demotion reviews: `{summary.get('demotion_review_count')}`",
        f"- Item types: `{summary.get('item_type_counts')}`",
        "",
        "## Work Items",
        "",
    ]
    for item in report.get("work_items") or []:
        lines.append(
            "- "
            f"`P{item.get('priority')}` `{item.get('status')}` `{item.get('item_type')}` "
            f"`{item.get('item_id')}`: {item.get('plain_english_goal')}"
        )
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _work_item_from_research_task(task: Mapping[str, Any]) -> Dict[str, Any]:
    task_type = str(task.get("task_type") or "")
    mapping = _task_type_mapping(task_type)
    blocked_by = list(task.get("blocked_by") or [])
    status = mapping["status"]
    if blocked_by and status == "QUEUED_FOR_REPLAY":
        status = "BLOCKED_WAITING_FOR_INPUTS"
    item = {
        "schema": ITEM_SCHEMA,
        "item_id": _item_id(mapping["prefix"], [task.get("task_id")], task.get("source_memory_ids") or []),
        "item_type": mapping["item_type"],
        "priority": int(mapping.get("priority") or task.get("priority") or 3),
        "status": status,
        "source_task_ids": [str(task.get("task_id"))] if task.get("task_id") else [],
        "source_memory_ids": list(task.get("source_memory_ids") or []),
        "source_outcome_labels": list(task.get("source_outcome_labels") or []),
        "symbols": list(task.get("symbols") or []),
        "timeframes": list(task.get("timeframes") or []),
        "families": list(task.get("families") or []),
        "agents": list(task.get("agents") or []),
        "actions": list(task.get("actions") or []),
        "hypothesis": mapping["hypothesis"],
        "plain_english_goal": mapping["plain_english_goal"],
        "proposed_change": mapping["proposed_change"],
        "replay_request": _replay_request(task, mapping),
        "promotion_review": _promotion_review_from_task(task, mapping),
        "required_inputs": list(dict.fromkeys(list(task.get("required_inputs") or []) + mapping["required_inputs"])),
        "blocked_by": blocked_by,
        "produces": list(dict.fromkeys(list(task.get("produces") or []) + mapping["produces"])),
        "acceptance_checks": mapping["acceptance_checks"],
        "source_counts": dict(task.get("source_counts") or {}),
        "created_at": utc_now().isoformat(),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    validate_strategy_dev_work_item(item)
    return item


def _closed_memory_work_items(memory_records: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    closed = [
        record
        for record in memory_records
        if str(record.get("outcome_label") or "").startswith("TRADE_CLOSED_")
    ]
    items: List[Dict[str, Any]] = []
    for key, group in _group_records(closed, ("outcome_label", "symbol", "timeframe", "action")).items():
        outcome_label, symbol, timeframe, action = key
        mapping = _closed_memory_mapping(outcome_label)
        memory_ids = _sorted_unique(record.get("memory_id") for record in group)
        pnl = round(sum(float(record.get("profit_loss_account") or 0.0) for record in group), 6)
        item = {
            "schema": ITEM_SCHEMA,
            "item_id": _item_id(mapping["prefix"], [], memory_ids),
            "item_type": mapping["item_type"],
            "priority": mapping["priority"],
            "status": mapping["status"],
            "source_task_ids": [],
            "source_memory_ids": memory_ids,
            "source_outcome_labels": [outcome_label],
            "symbols": [symbol],
            "timeframes": [timeframe],
            "families": _families(group),
            "agents": _sorted_unique(record.get("agent_id") for record in group),
            "actions": [action],
            "hypothesis": mapping["hypothesis"],
            "plain_english_goal": mapping["plain_english_goal"],
            "proposed_change": mapping["proposed_change"],
            "replay_request": {
                "requested_runner": "walk_forward_receipt_replay",
                "symbols": [symbol],
                "timeframes": [timeframe],
                "source_memory_count": len(group),
                "net_profit_loss_account": pnl,
                "requires_terminal_history": False,
            },
            "promotion_review": {
                "review_type": mapping["review_type"],
                "source_memory_count": len(group),
                "net_profit_loss_account": pnl,
                "candidate_decision": mapping["candidate_decision"],
            },
            "required_inputs": [
                "closed-trade memory rows",
                "condition snapshot open/close",
                "walk-forward replay report",
            ],
            "blocked_by": [],
            "produces": mapping["produces"],
            "acceptance_checks": mapping["acceptance_checks"],
            "source_counts": {
                "memory_rows": len(group),
                "closed_profit_rows": sum(1 for record in group if record.get("outcome_label") == "TRADE_CLOSED_PROFIT"),
                "closed_loss_rows": sum(1 for record in group if record.get("outcome_label") == "TRADE_CLOSED_LOSS"),
                "closed_flat_rows": sum(1 for record in group if record.get("outcome_label") == "TRADE_CLOSED_FLAT"),
            },
            "created_at": utc_now().isoformat(),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        validate_strategy_dev_work_item(item)
        items.append(item)
    return items


def _task_type_mapping(task_type: str) -> Dict[str, Any]:
    defaults = {
        "prefix": task_type.lower() or "research_task",
        "item_type": "RESEARCH_TO_STRATEGY_WORK",
        "priority": 3,
        "status": "QUEUED_FOR_REVIEW",
        "hypothesis": "Research task may reveal a strategy improvement, hold decision, or demotion decision.",
        "plain_english_goal": "Convert the research task into a strategy-development decision.",
        "proposed_change": "Review the source task and produce a replay-backed patch, hold, or demotion candidate.",
        "required_inputs": ["source research task", "agent memory rows"],
        "produces": ["strategy_decision_note"],
        "acceptance_checks": ["decision names exact evidence used", "decision does not claim live execution authority"],
    }
    overrides: Dict[str, Dict[str, Any]] = {
        "TERMINAL_RECEIPT_JOINBACK": {
            "prefix": "terminal_joinback",
            "item_type": "TERMINAL_JOINBACK_WORKFLOW",
            "priority": 1,
            "status": "BLOCKED_WAITING_FOR_TERMINAL",
            "hypothesis": "Strategy work cannot score approved commands until MT4/MT5 receipts and close-history rows arrive.",
            "plain_english_goal": "Get terminal receipts/history into the learning loop before changing route sizing or compounding.",
            "proposed_change": "No strategy parameter change yet; run terminal receipt ingest, terminal history ingest, memory, then rebuild queues.",
            "required_inputs": ["terminal receipt JSON", "terminal close-history export"],
            "produces": ["terminal_joinback_run_request", "memory_rerun_request"],
            "acceptance_checks": ["pending command count decreases", "receipt/history rows join memory", "unmatched history rows are named"],
        },
        "TERMINAL_RECEIPT_RECONCILIATION": {
            "prefix": "terminal_reconciliation",
            "item_type": "TERMINAL_RECONCILIATION_PATCH_CANDIDATE",
            "priority": 1,
            "status": "QUEUED_FOR_PATCH_REVIEW",
            "hypothesis": "Receipt mismatches are caused by a specific command, hash, ticket, account, or symbol mapping error.",
            "plain_english_goal": "Name and fix the mismatch cause before the affected symbol keeps cycling.",
            "proposed_change": "Patch the receipt reconciliation mapping or keep the symbol explicitly locked with reason evidence.",
            "required_inputs": ["receipt JSON", "command JSON", "event journal"],
            "produces": ["reconciliation_patch_candidate", "symbol_unlock_or_lock_decision"],
            "acceptance_checks": ["mismatch reproduces in a test", "patch resolves the reproduced mismatch"],
        },
        "OVERSEER_CONFLICT_KEY_REFINEMENT": {
            "prefix": "overseer_conflict_key",
            "item_type": "OVERSEER_RULE_PATCH_CANDIDATE",
            "priority": 2,
            "status": "QUEUED_FOR_PATCH_REVIEW",
            "hypothesis": "The current same-symbol conflict key may block useful compounding or timeframe stacking.",
            "plain_english_goal": "Separate true duplicate spam from useful multi-agent trading opportunities.",
            "proposed_change": "Test a conflict key using symbol, side, strategy family, timeframe group, and receipt lifecycle state.",
            "required_inputs": ["rejected route memory rows", "pending receipt summary"],
            "produces": ["agent_overseer_patch_candidate", "overseer_regression_tests"],
            "acceptance_checks": ["duplicate same-route opens remain blocked", "opposite-side/timeframe cases are explicitly decided"],
        },
        "CONDITION_LAB_REJECTION_ANALYSIS": {
            "prefix": "condition_lab_replay",
            "item_type": "CONDITION_LAB_REPLAY_REQUEST",
            "priority": 2,
            "status": "QUEUED_FOR_REPLAY",
            "hypothesis": "Rejected route clusters can identify useful guardrails or missed opportunities.",
            "plain_english_goal": "Turn rejected route memory into sharper condition filters.",
            "proposed_change": "Replay the rejected condition bucket and classify it as guardrail, missed opportunity, or needs terminal data.",
            "required_inputs": ["condition tally report", "decision reasons"],
            "produces": ["condition_filter_patch_candidate", "condition_lab_report"],
            "acceptance_checks": ["bucket has named source rows", "classification has replay evidence"],
        },
        "WALK_FORWARD_RECEIPT_REPLAY": {
            "prefix": "walk_forward_terminal_replay",
            "item_type": "WALK_FORWARD_TERMINAL_REPLAY_REQUEST",
            "priority": 3,
            "status": "QUEUED_FOR_REPLAY",
            "hypothesis": "The route may change grade once fill/slippage/close facts are included.",
            "plain_english_goal": "Replay the route with terminal facts before scaling, holding, or demoting it.",
            "proposed_change": "Run walk-forward replay after receipt/history joinback and compare against current route grade.",
            "required_inputs": ["verified receipts", "terminal close-history export"],
            "produces": ["walk_forward_terminal_replay_report", "promotion_or_demotion_candidate"],
            "acceptance_checks": ["replay includes fill/slippage/close facts", "decision names promotion, hold, or demotion"],
        },
        "TERMINAL_HISTORY_PNL_SCHEMA": {
            "prefix": "terminal_history_contract",
            "item_type": "TERMINAL_HISTORY_CONTRACT_WORK",
            "priority": 2,
            "status": "BLOCKED_WAITING_FOR_TERMINAL_HISTORY",
            "hypothesis": "Closed-history export fields must be stable before PnL memory can drive strategy changes.",
            "plain_english_goal": "Lock the closed-trade fields needed for PnL learning.",
            "proposed_change": "Use terminal history ingest output to verify PnL, pips, R, MAE/MFE, commission, swap, and close reason fields.",
            "required_inputs": ["MT4/MT5 account history export"],
            "produces": ["terminal_history_contract_check", "agent_memory_close_field_check"],
            "acceptance_checks": ["history rows join memory", "closed PnL fields appear in agent memory"],
        },
        "STRATEGY_DEV_REPLAY": {
            "prefix": "strategy_replay",
            "item_type": "STRATEGY_REPLAY_REQUEST",
            "priority": 2,
            "status": "QUEUED_FOR_REPLAY",
            "hypothesis": "Verified terminal acknowledgements may support sizing, compounding, or exit-rule changes.",
            "plain_english_goal": "Replay verified routes and decide whether to scale, hold, or demote.",
            "proposed_change": "Run replay with terminal facts and produce a strategy change candidate.",
            "required_inputs": ["verified receipts", "terminal close-history export"],
            "produces": ["strategy_patch_candidate", "adaptive_compounding_review"],
            "acceptance_checks": ["replay includes terminal facts", "strategy decision is evidence-backed"],
        },
    }
    return {**defaults, **overrides.get(task_type, {})}


def _closed_memory_mapping(outcome_label: str) -> Dict[str, Any]:
    if outcome_label == "TRADE_CLOSED_PROFIT":
        return {
            "prefix": "closed_profit_promotion",
            "item_type": "CLOSED_PROFIT_PROMOTION_REVIEW",
            "priority": 1,
            "status": "READY_FOR_PROMOTION_REVIEW",
            "hypothesis": "Closed profitable routes may support tighter replay, compounding, or promotion review.",
            "plain_english_goal": "Use actual winning closes to decide whether a strategy variant earns more capital or more frequency.",
            "proposed_change": "Review compounding, lot sizing, exit timing, and same-condition replay for the profitable bucket.",
            "review_type": "PROMOTION",
            "candidate_decision": "PROMOTION_REVIEW_PENDING_REPLAY",
            "produces": ["promotion_review_candidate", "adaptive_compounding_review"],
            "acceptance_checks": ["profit survives replay", "drawdown and slippage are named", "condition cell remains positive"],
        }
    if outcome_label == "TRADE_CLOSED_LOSS":
        return {
            "prefix": "closed_loss_demotion",
            "item_type": "CLOSED_LOSS_DEMOTION_REVIEW",
            "priority": 1,
            "status": "QUEUED_FOR_PATCH_REVIEW",
            "hypothesis": "Closed losing routes may require filter, stop, timing, or demotion changes.",
            "plain_english_goal": "Use actual losing closes to reduce repeated losses in the same condition bucket.",
            "proposed_change": "Review stop distance, entry timing, spread/slippage, and disable/demotion rules for the losing bucket.",
            "review_type": "DEMOTION",
            "candidate_decision": "DEMOTION_REVIEW_PENDING_REPLAY",
            "produces": ["demotion_review_candidate", "risk_filter_patch_candidate"],
            "acceptance_checks": ["loss cause is named", "patch has replay coverage", "future route rule is explicit"],
        }
    return {
        "prefix": "closed_flat_exit",
        "item_type": "CLOSED_FLAT_EXIT_REVIEW",
        "priority": 3,
        "status": "QUEUED_FOR_REVIEW",
        "hypothesis": "Flat exits may reveal stale entries, weak momentum, or early exit opportunities.",
        "plain_english_goal": "Use flat closes to sharpen exit timing and avoid dead capital.",
        "proposed_change": "Review exit reason and condition state to decide hold, tighten, or skip.",
        "review_type": "FLAT_EXIT",
        "candidate_decision": "EXIT_REVIEW_PENDING",
        "produces": ["exit_rule_review_candidate"],
        "acceptance_checks": ["exit reason is present", "future hold/exit rule is named"],
    }


def _replay_request(task: Mapping[str, Any], mapping: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "requested_runner": _requested_runner(str(mapping.get("item_type") or "")),
        "symbols": list(task.get("symbols") or []),
        "timeframes": list(task.get("timeframes") or []),
        "source_task_id": task.get("task_id"),
        "source_memory_count": len(task.get("source_memory_ids") or []),
        "requires_terminal_receipt": "receipt" in " ".join(task.get("required_inputs") or []).lower(),
        "requires_terminal_history": "history" in " ".join(task.get("required_inputs") or []).lower(),
    }


def _promotion_review_from_task(task: Mapping[str, Any], mapping: Mapping[str, Any]) -> Dict[str, Any]:
    item_type = str(mapping.get("item_type") or "")
    if "PROMOTION" in item_type:
        review_type = "PROMOTION"
    elif "DEMOTION" in item_type:
        review_type = "DEMOTION"
    elif "WALK_FORWARD" in item_type or "STRATEGY_REPLAY" in item_type:
        review_type = "PROMOTION_OR_DEMOTION"
    else:
        review_type = "PATCH_OR_HOLD"
    return {
        "review_type": review_type,
        "candidate_decision": "PENDING_REPLAY_OR_PATCH_REVIEW",
        "source_task_type": task.get("task_type"),
        "source_task_priority": task.get("priority"),
    }


def _requested_runner(item_type: str) -> str:
    if item_type == "CONDITION_LAB_REPLAY_REQUEST":
        return "condition_lab"
    if item_type == "WALK_FORWARD_TERMINAL_REPLAY_REQUEST":
        return "walk_forward_receipt_replay"
    if item_type == "OVERSEER_RULE_PATCH_CANDIDATE":
        return "overseer_rule_regression"
    if item_type == "TERMINAL_JOINBACK_WORKFLOW":
        return "terminal_joinback_sequence"
    if item_type == "TERMINAL_HISTORY_CONTRACT_WORK":
        return "terminal_history_ingest"
    return "strategy_dev_review"


def _summary(
    items: Sequence[Mapping[str, Any]],
    research_queue_report: Mapping[str, Any],
    memory_report: Mapping[str, Any],
) -> Dict[str, Any]:
    type_counts = Counter(str(item.get("item_type")) for item in items)
    status_counts = Counter(str(item.get("status")) for item in items)
    priority_counts = Counter(str(item.get("priority")) for item in items)
    memory_summary = memory_report.get("summary") or {}
    research_summary = research_queue_report.get("summary") or {}
    return {
        "item_count": len(items),
        "queued_item_count": sum(count for status, count in status_counts.items() if status.startswith("QUEUED")),
        "blocked_item_count": sum(count for status, count in status_counts.items() if status.startswith("BLOCKED")),
        "ready_for_replay_count": sum(1 for item in items if "REPLAY" in str(item.get("item_type"))),
        "patch_candidate_count": sum(1 for item in items if "PATCH" in str(item.get("item_type"))),
        "promotion_review_count": type_counts.get("CLOSED_PROFIT_PROMOTION_REVIEW", 0),
        "demotion_review_count": type_counts.get("CLOSED_LOSS_DEMOTION_REVIEW", 0),
        "terminal_blocked_count": sum(
            1
            for item in items
            if "TERMINAL" in str(item.get("item_type")) and str(item.get("status")).startswith("BLOCKED")
        ),
        "item_type_counts": dict(type_counts),
        "status_counts": dict(status_counts),
        "priority_counts": dict(priority_counts),
        "source_task_count": int(research_summary.get("task_count", 0) or 0),
        "source_memory_count": int(memory_summary.get("memory_record_count", 0) or 0),
        "source_pending_receipt_count": int(memory_summary.get("pending_receipt_count", 0) or 0),
        "source_terminal_history_joined_count": int(memory_summary.get("terminal_history_joined_count", 0) or 0),
        "closed_profit_memory_count": int(memory_summary.get("closed_profit_count", 0) or 0),
        "closed_loss_memory_count": int(memory_summary.get("closed_loss_count", 0) or 0),
        "next_item_id": items[0].get("item_id") if items else None,
    }


def _next_action(summary: Mapping[str, Any]) -> str:
    if int(summary.get("terminal_blocked_count", 0) or 0) > 0:
        return "Resolve terminal receipt/history blockers first, then rerun memory, research queue, and strategy-development queue."
    if int(summary.get("promotion_review_count", 0) or 0) > 0:
        return "Run promotion replay reviews for closed profitable memory buckets."
    if int(summary.get("demotion_review_count", 0) or 0) > 0:
        return "Run demotion or filter reviews for closed losing memory buckets."
    if int(summary.get("patch_candidate_count", 0) or 0) > 0:
        return "Review patch candidates and add regression/replay coverage for accepted strategy changes."
    if int(summary.get("item_count", 0) or 0) > 0:
        return "Process queued strategy-development work items in priority order."
    return "No strategy-development work items are queued; rebuild research queue from fresh memory."


def _queue_status(items: Sequence[Mapping[str, Any]]) -> str:
    return "STRATEGY_DEV_QUEUE_BUILT" if items else "STRATEGY_DEV_QUEUE_EMPTY"


def _item_id(prefix: str, task_ids: Sequence[Any], memory_ids: Sequence[Any]) -> str:
    material = "|".join(_sorted_unique(task_ids) + _sorted_unique(memory_ids))
    digest = hashlib.sha256(f"{prefix}|{material}".encode("utf-8")).hexdigest()[:16]
    safe_prefix = "".join(ch if ch.isalnum() else "-" for ch in prefix.lower()).strip("-")
    return f"strategy-dev-{safe_prefix}-{digest}"


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
