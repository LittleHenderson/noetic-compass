"""Strategy patch runner for the CAS Forex agent desk.

The strategy-development queue says what needs to be investigated. This module
turns those work items into concrete patch proposals, replay jobs, promotion
reviews, demotion reviews, or terminal-input blockers that the desk can track.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from cas_forex.strategy_dev_queue import (
    StrategyDevQueueError,
    load_latest_strategy_dev_queue_report,
)
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "strategy_patch_runner"
REPORT_KIND = "cas_forex_strategy_patch_runner_report"
DECISION_SCHEMA = "cas_forex_strategy_patch_decision.v1"
CLAIM_BOUNDARY = (
    "Strategy patch runner decisions organize paper/demo replay jobs, patch "
    "proposals, promotion reviews, demotion reviews, and terminal blockers. "
    "They do not by themselves execute live broker orders, create broker "
    "ACCEPT, deposit, withdraw, move bank/card funds, automate payouts, or "
    "silently modify live strategy code."
)


class StrategyPatchRunnerError(ValueError):
    """Raised when strategy patch-runner evidence cannot be built or loaded."""


def build_strategy_patch_runner_report(
    *,
    strategy_dev_queue_report: Optional[Mapping[str, Any]] = None,
    strategy_dev_queue_report_dir: Optional[Path | str] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build and optionally persist patch/replay decisions."""

    if strategy_dev_queue_report is None:
        try:
            if strategy_dev_queue_report_dir is None:
                strategy_dev_queue_report = load_latest_strategy_dev_queue_report()
            else:
                strategy_dev_queue_report = load_latest_strategy_dev_queue_report(strategy_dev_queue_report_dir)
        except StrategyDevQueueError as exc:
            raise StrategyPatchRunnerError(str(exc)) from exc

    decisions = build_strategy_patch_decisions(strategy_dev_queue_report)
    summary = _summary(decisions, strategy_dev_queue_report)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "runner_status": _runner_status(summary),
        "schema": DECISION_SCHEMA,
        "strategy_dev_queue_report_path": strategy_dev_queue_report.get("report_path")
        or (strategy_dev_queue_report.get("artifact_paths") or {}).get("json"),
        "output_dir": str(Path(output_dir)),
        "summary": summary,
        "decisions": decisions,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        paths = write_strategy_patch_runner_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_strategy_patch_runner_report(report)
    return report


def build_strategy_patch_decisions(strategy_dev_queue_report: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Return deterministic patch/replay decisions from strategy-dev work items."""

    work_items = [
        dict(item)
        for item in strategy_dev_queue_report.get("work_items") or []
        if isinstance(item, Mapping)
    ]
    decisions = [_decision_from_work_item(item) for item in work_items]
    return sorted(decisions, key=lambda item: (int(item["priority"]), str(item["decision_type"]), str(item["decision_id"])))


def write_strategy_patch_runner_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    """Write report JSON/Markdown plus JSONL decisions."""

    validate_strategy_patch_runner_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"strategy-patch-runner-{stamp}-report.json"
    md_path = target_dir / f"strategy-patch-runner-{stamp}-report.md"
    jsonl_path = target_dir / f"strategy-patch-runner-{stamp}.jsonl"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_strategy_patch_runner_markdown(report), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for decision in report.get("decisions") or []:
            handle.write(json.dumps(decision, sort_keys=True, ensure_ascii=False) + "\n")
    return {"json": json_path, "markdown": md_path, "jsonl": jsonl_path}


def load_latest_strategy_patch_runner_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("strategy-patch-runner-*-report.json"))
    if not files:
        raise StrategyPatchRunnerError(f"No strategy patch-runner reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_strategy_patch_runner_report(payload)
    return payload


def validate_strategy_patch_runner_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "runner_status",
        "schema",
        "summary",
        "decisions",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise StrategyPatchRunnerError(f"strategy patch-runner report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise StrategyPatchRunnerError("unexpected strategy patch-runner report_kind")
    if payload.get("schema") != DECISION_SCHEMA:
        raise StrategyPatchRunnerError("unexpected strategy patch-runner schema")
    boundary = str(payload.get("claim_boundary", ""))
    if "do not by themselves execute live broker orders" not in boundary:
        raise StrategyPatchRunnerError("strategy patch-runner claim boundary must preserve execution boundary")
    if "silently modify live strategy code" not in boundary:
        raise StrategyPatchRunnerError("strategy patch-runner claim boundary must preserve code-change boundary")
    if not isinstance(payload.get("decisions"), list):
        raise StrategyPatchRunnerError("decisions must be a list")
    for decision in payload.get("decisions") or []:
        validate_strategy_patch_decision(decision)


def validate_strategy_patch_decision(decision: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "decision_id",
        "decision_type",
        "priority",
        "status",
        "source_item_id",
        "source_item_type",
        "symbols",
        "timeframes",
        "plain_english_decision",
        "proposed_action",
        "patch_target",
        "replay_job",
        "promotion_review",
        "required_inputs",
        "blocked_by",
        "evidence_refs",
        "generated_artifacts",
        "acceptance_checks",
        "owner_review_required",
        "claim_boundary",
    }
    missing = required.difference(decision)
    if missing:
        raise StrategyPatchRunnerError(f"strategy patch decision missing fields: {sorted(missing)}")
    if decision.get("schema") != DECISION_SCHEMA:
        raise StrategyPatchRunnerError("unexpected strategy patch decision schema")
    if "do not by themselves execute live broker orders" not in str(decision.get("claim_boundary", "")):
        raise StrategyPatchRunnerError("strategy patch decision claim boundary must preserve execution boundary")


def render_strategy_patch_runner_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Strategy Patch Runner",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('runner_status')}`",
        f"Strategy-dev queue: `{report.get('strategy_dev_queue_report_path')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Decisions: `{summary.get('decision_count')}`",
        f"- Ready decisions: `{summary.get('ready_decision_count')}`",
        f"- Blocked decisions: `{summary.get('blocked_decision_count')}`",
        f"- Patch candidates: `{summary.get('patch_candidate_count')}`",
        f"- Replay jobs: `{summary.get('replay_job_count')}`",
        f"- Promotion reviews: `{summary.get('promotion_review_count')}`",
        f"- Demotion reviews: `{summary.get('demotion_review_count')}`",
        f"- Terminal input required: `{summary.get('terminal_input_required_count')}`",
        "",
        "## Decisions",
        "",
    ]
    for decision in report.get("decisions") or []:
        lines.append(
            "- "
            f"`P{decision.get('priority')}` `{decision.get('status')}` `{decision.get('decision_type')}` "
            f"`{decision.get('decision_id')}` -> `{decision.get('patch_target')}`: "
            f"{decision.get('plain_english_decision')}"
        )
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _decision_from_work_item(item: Mapping[str, Any]) -> Dict[str, Any]:
    mapping = _decision_mapping(item)
    blocked_by = _blocked_reasons(item, mapping)
    status = mapping["status"]
    if blocked_by and status in {"REPLAY_JOB_READY", "PATCH_CANDIDATE_READY", "PROMOTION_REVIEW_READY", "DEMOTION_REVIEW_READY"}:
        status = "BLOCKED_WAITING_FOR_INPUTS"
    decision = {
        "schema": DECISION_SCHEMA,
        "decision_id": _decision_id(mapping["prefix"], item),
        "decision_type": mapping["decision_type"],
        "priority": int(mapping.get("priority") or item.get("priority") or 3),
        "status": status,
        "source_item_id": item.get("item_id"),
        "source_item_type": item.get("item_type"),
        "source_task_ids": list(item.get("source_task_ids") or []),
        "source_memory_ids": list(item.get("source_memory_ids") or []),
        "symbols": list(item.get("symbols") or []),
        "timeframes": list(item.get("timeframes") or []),
        "plain_english_decision": mapping["plain_english_decision"],
        "proposed_action": item.get("proposed_change") or mapping["proposed_action"],
        "patch_target": mapping["patch_target"],
        "replay_job": _replay_job(item, mapping, blocked_by),
        "promotion_review": _promotion_review(item, mapping),
        "required_inputs": _unique([*list(item.get("required_inputs") or []), *mapping["required_inputs"]]),
        "blocked_by": blocked_by,
        "evidence_refs": _evidence_refs(item),
        "generated_artifacts": mapping["generated_artifacts"],
        "acceptance_checks": _unique([*list(item.get("acceptance_checks") or []), *mapping["acceptance_checks"]]),
        "owner_review_required": True,
        "created_at": utc_now().isoformat(),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    validate_strategy_patch_decision(decision)
    return decision


def _decision_mapping(item: Mapping[str, Any]) -> Dict[str, Any]:
    item_type = str(item.get("item_type") or "")
    defaults = {
        "prefix": "strategy_decision",
        "decision_type": "STRATEGY_DECISION_REVIEW",
        "status": "REVIEW_READY",
        "priority": int(item.get("priority") or 3),
        "plain_english_decision": "Review the strategy-development item and decide patch, replay, hold, promote, or demote.",
        "proposed_action": "Review the source item and write a named strategy decision.",
        "patch_target": "strategy_decision_note",
        "requested_runner": "manual_strategy_review",
        "required_inputs": ["strategy-development work item"],
        "generated_artifacts": ["strategy_decision_note"],
        "acceptance_checks": ["decision links back to source item", "decision names evidence used"],
    }
    overrides: Dict[str, Dict[str, Any]] = {
        "TERMINAL_JOINBACK_WORKFLOW": {
            "prefix": "terminal_joinback_blocker",
            "decision_type": "TERMINAL_INPUT_REQUIRED",
            "status": "BLOCKED_WAITING_FOR_TERMINAL_INPUTS",
            "plain_english_decision": "Do not change strategy parameters until terminal receipts and closed history enter memory.",
            "patch_target": "evidence_runs/agent_workflow_mt4_mailbox",
            "requested_runner": "terminal_joinback_sequence",
            "required_inputs": ["terminal receipt JSON", "terminal close-history export"],
            "generated_artifacts": ["terminal_receipt_ingest_rerun", "terminal_history_ingest_rerun", "agent_memory_rerun"],
            "acceptance_checks": ["pending receipt count decreases", "terminal history rows join memory"],
        },
        "TERMINAL_HISTORY_CONTRACT_WORK": {
            "prefix": "terminal_history_contract_blocker",
            "decision_type": "TERMINAL_INPUT_REQUIRED",
            "status": "BLOCKED_WAITING_FOR_TERMINAL_INPUTS",
            "plain_english_decision": "Hold strategy changes until exported close-history fields prove PnL memory is populated.",
            "patch_target": "evidence_runs/terminal_history_exports",
            "requested_runner": "terminal_history_ingest",
            "required_inputs": ["MT4/MT5 account history export"],
            "generated_artifacts": ["terminal_history_contract_check", "agent_memory_close_field_check"],
            "acceptance_checks": ["closed PnL fields appear in memory", "unmatched history rows are named"],
        },
        "TERMINAL_RECONCILIATION_PATCH_CANDIDATE": {
            "prefix": "terminal_reconciliation_patch",
            "decision_type": "PATCH_CANDIDATE",
            "status": "PATCH_CANDIDATE_READY",
            "plain_english_decision": "Prepare a reconciliation patch or keep the affected symbol locked with exact evidence.",
            "patch_target": "cas_forex/terminal_receipt_ingest.py",
            "requested_runner": "receipt_reconciliation_regression",
            "required_inputs": ["receipt JSON", "command JSON", "event journal"],
            "generated_artifacts": ["reconciliation_patch_candidate", "symbol_lock_or_unlock_decision"],
            "acceptance_checks": ["mismatch reproduces in a test", "patched mapping resolves the reproduced mismatch"],
        },
        "OVERSEER_RULE_PATCH_CANDIDATE": {
            "prefix": "overseer_rule_patch",
            "decision_type": "PATCH_CANDIDATE",
            "status": "PATCH_CANDIDATE_READY",
            "plain_english_decision": "Prepare an overseer conflict-key patch candidate and regression checks.",
            "patch_target": "cas_forex/agent_overseer.py",
            "requested_runner": "overseer_conflict_key_regression",
            "required_inputs": ["rejected route memory rows", "pending receipt summary"],
            "generated_artifacts": ["agent_overseer_patch_candidate", "overseer_regression_tests"],
            "acceptance_checks": ["duplicate same-route opens remain blocked", "useful timeframe/side stacking is explicitly decided"],
        },
        "CONDITION_LAB_REPLAY_REQUEST": {
            "prefix": "condition_lab_replay_job",
            "decision_type": "REPLAY_JOB",
            "status": "REPLAY_JOB_READY",
            "plain_english_decision": "Queue a condition-lab replay to classify the rejected bucket.",
            "patch_target": "condition_filter_patch_candidate",
            "requested_runner": "condition_lab",
            "required_inputs": ["condition tally report", "decision reasons"],
            "generated_artifacts": ["condition_replay_job", "condition_filter_patch_candidate"],
            "acceptance_checks": ["bucket has source rows", "classification has replay evidence"],
        },
        "WALK_FORWARD_TERMINAL_REPLAY_REQUEST": {
            "prefix": "walk_forward_terminal_replay_job",
            "decision_type": "REPLAY_JOB",
            "status": "REPLAY_JOB_READY",
            "plain_english_decision": "Queue a walk-forward replay that includes terminal fill and close facts.",
            "patch_target": "walk_forward_terminal_replay_report",
            "requested_runner": "walk_forward_receipt_replay",
            "required_inputs": ["verified receipts", "terminal close-history export"],
            "generated_artifacts": ["walk_forward_terminal_replay_job", "promotion_or_demotion_candidate"],
            "acceptance_checks": ["replay includes fill/slippage/close facts", "decision names promotion, hold, or demotion"],
        },
        "STRATEGY_REPLAY_REQUEST": {
            "prefix": "strategy_replay_job",
            "decision_type": "REPLAY_JOB",
            "status": "REPLAY_JOB_READY",
            "plain_english_decision": "Queue a strategy replay and produce a patch, hold, promotion, or demotion decision.",
            "patch_target": "strategy_patch_candidate",
            "requested_runner": "strategy_replay",
            "required_inputs": ["verified receipts", "terminal close-history export"],
            "generated_artifacts": ["strategy_replay_job", "strategy_patch_candidate"],
            "acceptance_checks": ["replay includes terminal facts", "strategy decision is evidence-backed"],
        },
        "CLOSED_PROFIT_PROMOTION_REVIEW": {
            "prefix": "closed_profit_promotion_decision",
            "decision_type": "PROMOTION_REVIEW",
            "status": "PROMOTION_REVIEW_READY",
            "plain_english_decision": "Review profitable closed-memory rows for compounding, lot, frequency, or exit improvement.",
            "patch_target": "adaptive_compounding_review",
            "requested_runner": "promotion_replay",
            "required_inputs": ["closed profit memory rows", "walk-forward replay report"],
            "generated_artifacts": ["promotion_review_decision", "adaptive_compounding_review"],
            "acceptance_checks": ["profit survives replay", "drawdown and slippage are named"],
        },
        "CLOSED_LOSS_DEMOTION_REVIEW": {
            "prefix": "closed_loss_demotion_decision",
            "decision_type": "DEMOTION_REVIEW",
            "status": "DEMOTION_REVIEW_READY",
            "plain_english_decision": "Review losing closed-memory rows for stop, filter, timing, disable, or demotion changes.",
            "patch_target": "risk_filter_patch_candidate",
            "requested_runner": "demotion_replay",
            "required_inputs": ["closed loss memory rows", "walk-forward replay report"],
            "generated_artifacts": ["demotion_review_decision", "risk_filter_patch_candidate"],
            "acceptance_checks": ["loss cause is named", "future route rule is explicit"],
        },
        "CLOSED_FLAT_EXIT_REVIEW": {
            "prefix": "closed_flat_exit_decision",
            "decision_type": "EXIT_RULE_REVIEW",
            "status": "REVIEW_READY",
            "plain_english_decision": "Review flat exits for stale-entry, dead-capital, or early-exit improvements.",
            "patch_target": "exit_rule_review_candidate",
            "requested_runner": "exit_rule_review",
            "required_inputs": ["closed flat memory rows", "exit reason"],
            "generated_artifacts": ["exit_rule_review_decision"],
            "acceptance_checks": ["exit reason is present", "future hold/exit rule is named"],
        },
    }
    return {**defaults, **overrides.get(item_type, {})}


def _replay_job(item: Mapping[str, Any], mapping: Mapping[str, Any], blocked_by: List[str]) -> Dict[str, Any]:
    request = item.get("replay_request") if isinstance(item.get("replay_request"), Mapping) else {}
    return {
        "runner": mapping["requested_runner"],
        "source_requested_runner": request.get("requested_runner"),
        "symbols": list(item.get("symbols") or []),
        "timeframes": list(item.get("timeframes") or []),
        "source_item_id": item.get("item_id"),
        "requires_terminal_receipt": bool(request.get("requires_terminal_receipt")) or _mentions(item, "receipt"),
        "requires_terminal_history": bool(request.get("requires_terminal_history")) or _mentions(item, "history"),
        "blocked": bool(blocked_by),
        "blocked_by": blocked_by,
    }


def _promotion_review(item: Mapping[str, Any], mapping: Mapping[str, Any]) -> Dict[str, Any]:
    review = item.get("promotion_review") if isinstance(item.get("promotion_review"), Mapping) else {}
    return {
        "review_type": review.get("review_type") or mapping["decision_type"],
        "candidate_decision": review.get("candidate_decision") or "PATCH_RUNNER_DECISION_PENDING",
        "source_item_id": item.get("item_id"),
        "source_memory_count": len(item.get("source_memory_ids") or []),
    }


def _blocked_reasons(item: Mapping[str, Any], mapping: Mapping[str, Any]) -> List[str]:
    blocked = list(item.get("blocked_by") or [])
    status = str(item.get("status") or "")
    if status.startswith("BLOCKED"):
        blocked.append(status)
    if mapping["decision_type"] == "TERMINAL_INPUT_REQUIRED":
        blocked.append("terminal receipt/history input required")
    return _unique(blocked)


def _evidence_refs(item: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "source_item_id": item.get("item_id"),
        "source_task_ids": list(item.get("source_task_ids") or []),
        "source_memory_ids": list(item.get("source_memory_ids") or []),
        "source_counts": dict(item.get("source_counts") or {}),
    }


def _summary(decisions: List[Mapping[str, Any]], strategy_dev_queue_report: Mapping[str, Any]) -> Dict[str, Any]:
    type_counts = Counter(str(decision.get("decision_type") or "") for decision in decisions)
    status_counts = Counter(str(decision.get("status") or "") for decision in decisions)
    priority_counts = Counter(str(decision.get("priority") or "") for decision in decisions)
    ready_statuses = {"PATCH_CANDIDATE_READY", "REPLAY_JOB_READY", "PROMOTION_REVIEW_READY", "DEMOTION_REVIEW_READY", "REVIEW_READY"}
    patch_targets = Counter(str(decision.get("patch_target") or "") for decision in decisions)
    return {
        "decision_count": len(decisions),
        "ready_decision_count": sum(1 for decision in decisions if decision.get("status") in ready_statuses),
        "blocked_decision_count": sum(1 for decision in decisions if str(decision.get("status") or "").startswith("BLOCKED")),
        "patch_candidate_count": type_counts.get("PATCH_CANDIDATE", 0),
        "replay_job_count": type_counts.get("REPLAY_JOB", 0),
        "promotion_review_count": type_counts.get("PROMOTION_REVIEW", 0),
        "demotion_review_count": type_counts.get("DEMOTION_REVIEW", 0),
        "terminal_input_required_count": type_counts.get("TERMINAL_INPUT_REQUIRED", 0),
        "owner_review_required_count": sum(1 for decision in decisions if decision.get("owner_review_required")),
        "decision_type_counts": dict(sorted(type_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "priority_counts": dict(sorted(priority_counts.items())),
        "patch_target_counts": dict(sorted(patch_targets.items())),
        "source_item_count": (strategy_dev_queue_report.get("summary") or {}).get("item_count", len(decisions)),
        "source_blocked_item_count": (strategy_dev_queue_report.get("summary") or {}).get("blocked_item_count", 0),
        "source_patch_candidate_count": (strategy_dev_queue_report.get("summary") or {}).get("patch_candidate_count", 0),
        "next_decision_id": decisions[0]["decision_id"] if decisions else None,
    }


def _runner_status(summary: Mapping[str, Any]) -> str:
    if not summary.get("decision_count"):
        return "STRATEGY_PATCH_RUNNER_EMPTY"
    if summary.get("ready_decision_count"):
        return "STRATEGY_PATCH_RUNNER_READY"
    return "STRATEGY_PATCH_RUNNER_BLOCKED"


def _next_action(summary: Mapping[str, Any]) -> str:
    if summary.get("patch_candidate_count"):
        return (
            "Review the ready patch candidate first, add regression coverage, then rerun the affected "
            "agent workflow / memory / queue chain before any promotion decision."
        )
    if summary.get("replay_job_count"):
        return "Run the ready replay jobs and feed their results back into memory and the strategy-development queue."
    if summary.get("terminal_input_required_count"):
        return "Compile/attach/run the MT4 bridge and export terminal history so blocked decisions can move."
    return "No strategy patch-runner decisions are ready."


def _decision_id(prefix: str, item: Mapping[str, Any]) -> str:
    raw = json.dumps(
        {
            "prefix": prefix,
            "item_id": item.get("item_id"),
            "item_type": item.get("item_type"),
            "source_task_ids": item.get("source_task_ids") or [],
            "source_memory_ids": item.get("source_memory_ids") or [],
        },
        sort_keys=True,
        default=str,
    )
    return f"strategy-patch-{prefix}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _mentions(item: Mapping[str, Any], needle: str) -> bool:
    haystack = " ".join(
        str(value)
        for value in [
            item.get("plain_english_goal"),
            item.get("proposed_change"),
            " ".join(item.get("required_inputs") or []),
            " ".join(item.get("blocked_by") or []),
        ]
    ).lower()
    return needle.lower() in haystack


def _unique(values: List[Any]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out
