"""HTTP route for the agent decision explainer.

Thin wrapper around `cas_forex.agent_decision_explainer.explain_latest_agent_decision`.
Loads the latest cycle / memory / strategy / walk-forward / PCBA evidence
from disk, feeds it through the pure explainer, and returns the structured
``AgentDecisionExplanation`` as JSON.

The route exists so the LLM bot can call a single capability to answer
"why did the agent trade X?" — instead of assembling the answer from
multiple raw JSON endpoints.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter

from api import data as data_module
from cas_forex.agent_decision_explainer import (
    AgentDecisionExplanation,
    explain_latest_agent_decision,
)

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]


def _safe_load_latest(pattern: str) -> Optional[dict[str, Any]]:
    """Glob for the latest report matching ``pattern`` and load it as JSON.
    Returns ``None`` for any I/O or parse error so the explainer routes
    through its DEGRADED / missing-input paths."""
    candidates = sorted(REPO_ROOT.glob(pattern))
    if not candidates:
        return None
    try:
        return json.loads(candidates[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


_EVIDENCE_PATTERNS: dict[str, str] = {
    "agent_cycle_report": "evidence_runs/agent_workflow_queue/agent-workflow-cycle-*-report.json",
    "agent_cycle_mt4_report": "evidence_runs/agent_workflow_mt4_mailbox/agent-workflow-cycle-*-report.json",
    "agent_memory_report": "evidence_runs/agent_memory/agent-memory-*-report.json",
    "daily_learning_rollup": "evidence_runs/daily_learning_rollup/daily-learning-rollup-*-report.json",
    "strategy_dev_queue_report": "evidence_runs/strategy_dev_queue/strategy-dev-queue-*-report.json",
    "strategy_leads": "evidence_runs/strategy_leads/strategy-leads-*-report.json",
    "walk_forward_report": "evidence_runs/walk_forward/walk-forward-*-report.json",
    "pcba_report": "evidence_runs/pcba_goal_status/pcba-goal-status-*-report.json",
}


def _default_loader() -> dict[str, Any]:
    """Load every evidence input the explainer accepts. Missing artifacts
    are silently treated as ``None`` so the explainer's missing-input
    handling reports them with a structured ``status="missing"``."""
    cycle = _safe_load_latest(_EVIDENCE_PATTERNS["agent_cycle_report"])
    if cycle is None:
        cycle = _safe_load_latest(_EVIDENCE_PATTERNS["agent_cycle_mt4_report"])
    return {
        "agent_cycle_report": cycle,
        "agent_memory_report": _safe_load_latest(_EVIDENCE_PATTERNS["agent_memory_report"]),
        "daily_learning_rollup": _safe_load_latest(_EVIDENCE_PATTERNS["daily_learning_rollup"]),
        "strategy_dev_queue_report": _safe_load_latest(_EVIDENCE_PATTERNS["strategy_dev_queue_report"]),
        "strategy_leads": _safe_load_latest(_EVIDENCE_PATTERNS["strategy_leads"]),
        "walk_forward_report": _safe_load_latest(_EVIDENCE_PATTERNS["walk_forward_report"]),
        "pcba_report": _safe_load_latest(_EVIDENCE_PATTERNS["pcba_report"]),
    }


_LOADER: Callable[[], dict[str, Any]] = _default_loader


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER
    _LOADER = loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader


def _explanation_to_payload(exp: AgentDecisionExplanation) -> dict[str, Any]:
    """Convert the frozen dataclass tree into JSON-serializable dicts."""
    return {
        "cycle_id": exp.cycle_id,
        "overall_status": exp.overall_status,
        "plain_english_summary": exp.plain_english_summary,
        "chain": [asdict(step) for step in exp.chain],
        "next_action_hint": exp.next_action_hint,
        "movement_source_truth": dict(exp.movement_source_truth or {}) if exp.movement_source_truth else None,
        "version_trace": dict(exp.version_trace or {}),
    }


def _safe_current_movement_source_truth() -> dict[str, Any] | None:
    try:
        report = data_module.account_health()
    except Exception:
        return None
    if not isinstance(report, dict):
        return None
    source_health = report.get("source_health")
    if not isinstance(source_health, dict):
        return None
    return source_health


@router.get("/latest")
async def get_latest_agent_decision() -> dict[str, Any]:
    """Explain the agent's most recent decision.

    Returns an ``AgentDecisionExplanation`` payload. When no agent cycle
    report exists, ``overall_status`` is ``"no_recent_decision"`` and the
    chain explains which evidence is missing — the route never fabricates.
    """
    inputs = _LOADER()
    if "movement_source_truth" not in inputs and _LOADER is _default_loader:
        inputs["movement_source_truth"] = _safe_current_movement_source_truth()
    explanation = explain_latest_agent_decision(**inputs)
    return _explanation_to_payload(explanation)
