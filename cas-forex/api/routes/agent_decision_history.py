"""HTTP route for the agent decision history (last N decisions).

Returns the last N agent decisions explained by the pure
`cas_forex.agent_decision_explainer.explain_latest_agent_decision`.

The shared context (memory / strategy / walk-forward / PCBA) is loaded ONCE
at the route boundary; the explainer is then re-run for each cycle report
individually. This is intentional: the explainer walks reasoning AS OF a
cycle, and the same most-recent context is the best available snapshot for
each historical cycle without fabricating per-cycle context that does not
exist.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from cas_forex.agent_decision_explainer import (
    AgentDecisionExplanation,
    explain_latest_agent_decision,
)

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]

_PRIMARY_CYCLE_GLOB = (
    "evidence_runs/agent_workflow_queue/agent-workflow-cycle-*-report.json"
)
_FALLBACK_CYCLE_GLOB = (
    "evidence_runs/agent_workflow_mt4_mailbox/agent-workflow-cycle-*-report.json"
)

_CONTEXT_PATTERNS: dict[str, str] = {
    "agent_memory_report": "evidence_runs/agent_memory/agent-memory-*-report.json",
    "daily_learning_rollup": "evidence_runs/daily_learning_rollup/daily-learning-rollup-*-report.json",
    "strategy_dev_queue_report": "evidence_runs/strategy_dev_queue/strategy-dev-queue-*-report.json",
    "strategy_leads": "evidence_runs/strategy_leads/strategy-leads-*-report.json",
    "walk_forward_report": "evidence_runs/walk_forward/walk-forward-*-report.json",
    "pcba_report": "evidence_runs/pcba_goal_status/pcba-goal-status-*-report.json",
}


def _safe_load_latest(pattern: str) -> Optional[dict[str, Any]]:
    """Glob for the latest report matching ``pattern`` and load it as JSON."""
    candidates = sorted(REPO_ROOT.glob(pattern))
    if not candidates:
        return None
    try:
        return json.loads(candidates[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _safe_load_path(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _list_cycle_reports(limit: int | None = None) -> list[Tuple[str, dict[str, Any]]]:
    """List (relative_path, parsed_json) for all cycle reports, NEWEST FIRST.

    Primary set is the agent_workflow_queue glob. If empty, fall back to
    agent_workflow_mt4_mailbox. We do NOT mix the two sets — primary wins
    in full if any primary file exists. (Per-file fallback is preserved
    only at the empty-primary boundary; this matches the latest route's
    behaviour of preferring the primary glob.)
    """
    primary = sorted(REPO_ROOT.glob(_PRIMARY_CYCLE_GLOB))
    if primary:
        paths = primary
    else:
        paths = sorted(REPO_ROOT.glob(_FALLBACK_CYCLE_GLOB))
    if not paths:
        return []
    # Sort by mtime DESCENDING (newest first).
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if limit is not None:
        paths = paths[: max(0, limit)]
    out: list[Tuple[str, dict[str, Any]]] = []
    for p in paths:
        data = _safe_load_path(p)
        if data is None:
            continue
        try:
            rel = p.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = p.as_posix()
        out.append((rel, data))
    return out


def _default_loader(limit: int | None = None) -> dict[str, Any]:
    """Load all cycle reports and the shared context. Tests can replace.

    Returns ``{"cycle_reports": [(path_str, dict), ...], "context": {...}}``.
    The context dict's keys match the explainer's context kwargs (i.e.
    everything except ``agent_cycle_report``).
    """
    cycle_reports = _list_cycle_reports(limit=limit)
    context = {
        key: _safe_load_latest(pattern) for key, pattern in _CONTEXT_PATTERNS.items()
    }
    return {"cycle_reports": cycle_reports, "context": context}


_LOADER: Callable[[int | None], dict[str, Any]] = _default_loader


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER

    def _wrapped_loader(limit: int | None = None) -> dict[str, Any]:
        return loader()

    _LOADER = _wrapped_loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader


def _explanation_to_payload(
    exp: AgentDecisionExplanation, cycle_report_path: str
) -> dict[str, Any]:
    return {
        "cycle_id": exp.cycle_id,
        "overall_status": exp.overall_status,
        "plain_english_summary": exp.plain_english_summary,
        "chain": [asdict(step) for step in exp.chain],
        "next_action_hint": exp.next_action_hint,
        "cycle_report_path": cycle_report_path,
    }


@router.get("/history")
async def get_agent_decision_history(limit: int = 10) -> Any:
    """Explain the agent's last ``limit`` decisions, newest first.

    The shared context (memory / strategy / walk-forward / PCBA) is loaded
    once and re-applied as each cycle report is fed through the explainer.
    """
    if limit < 1 or limit > 50:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_limit",
                "message": "limit must be between 1 and 50 inclusive",
            },
        )

    loaded = _LOADER(limit)
    cycle_reports: list[Tuple[str, dict[str, Any]]] = loaded.get(
        "cycle_reports", []
    ) or []
    context: dict[str, Any] = loaded.get("context", {}) or {}

    selected = cycle_reports[:limit]
    decisions: list[dict[str, Any]] = []
    for path_str, cycle_dict in selected:
        explanation = explain_latest_agent_decision(
            agent_cycle_report=cycle_dict, **context
        )
        decisions.append(_explanation_to_payload(explanation, path_str))

    return {
        "count": len(decisions),
        "limit": limit,
        "decisions": decisions,
    }
