"""Summaries for Forex Fury-derived CAS replay evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_DIR = REPO_ROOT / "evidence_runs" / "forex_fury_replay_candidates"
DEFAULT_CONDITION_DIR = REPO_ROOT / "evidence_runs" / "forex_fury_condition_replay"
DEFAULT_WALK_FORWARD_DIR = REPO_ROOT / "evidence_runs" / "forex_fury_walk_forward_replay"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "forex_fury_replay_results"
CLAIM_BOUNDARY = (
    "Forex Fury replay results are CAS research/backtest evidence only. They can "
    "promote candidates for adaptive review, but they do not execute EA binaries, "
    "place orders, create broker ACCEPT, deposit, withdraw, move bank/card funds, "
    "or automate payouts."
)


class ForexFuryReplayResultError(ValueError):
    """Raised when Forex Fury replay result evidence cannot be summarized."""


def build_forex_fury_replay_results(
    *,
    candidate_report: Optional[Mapping[str, Any]] = None,
    condition_report: Optional[Mapping[str, Any]] = None,
    walk_forward_report: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a compact summary from latest candidate, condition, and WF reports."""

    candidates = dict(candidate_report or _read_latest(DEFAULT_CANDIDATE_DIR, "forex-fury-replay-candidates-*-report.json"))
    condition = dict(condition_report or _read_latest(DEFAULT_CONDITION_DIR, "condition-lab-*-report.json"))
    walk_forward = dict(walk_forward_report or _read_latest(DEFAULT_WALK_FORWARD_DIR, "walk-forward-*-report.json"))
    _validate_inputs(candidates, condition, walk_forward)

    candidate_summary = candidates.get("summary") or {}
    condition_cells = [cell for cell in condition.get("cells", []) if isinstance(cell, dict)]
    routes = condition.get("rpm_routes") or {}
    if not isinstance(routes, dict):
        routes = {}
    top_cells = _top_condition_cells(condition_cells)
    wf_summary = walk_forward.get("combined_summary") or {}
    verdict = _replay_verdict(top_cells, wf_summary)

    payload = {
        "report_kind": "cas_forex_forex_fury_replay_results",
        "created_at": datetime.now(UTC).isoformat(),
        "claim_boundary": CLAIM_BOUNDARY,
        "source_reports": {
            "candidates": _source_ref(candidates),
            "condition_lab": _source_ref(condition),
            "walk_forward": _source_ref(walk_forward),
        },
        "candidate_summary": candidate_summary,
        "condition_summary": {
            "run_id": condition.get("run_id"),
            "source": condition.get("source"),
            "symbols": condition.get("symbols") or [],
            "timeframes": sorted({str(cell.get("timeframe")) for cell in condition_cells if cell.get("timeframe")}),
            "cell_count": len(condition_cells),
            "non_gap_cell_count": sum(1 for cell in condition_cells if not cell.get("is_gap")),
            "route_count": sum(1 for route in routes.values() if isinstance(route, dict) and route.get("action") == "ROUTE"),
            "no_trade_route_count": sum(1 for route in routes.values() if isinstance(route, dict) and route.get("action") == "NO_TRADE"),
            "overall_gap_fraction": (condition.get("nested_lacunarity") or {}).get("overall"),
            "top_condition_cells": top_cells,
        },
        "walk_forward_summary": {
            "run_id": walk_forward.get("run_id"),
            **wf_summary,
        },
        "replay_verdict": verdict,
        "adaptive_compounding_next_step": (
            "QUEUE_FOR_ADAPTIVE_COMPOUNDING_REVIEW"
            if verdict == "REPLAY_LEAD_FOR_ADAPTIVE_REVIEW"
            else "KEEP_IN_REPLAY_RESEARCH"
        ),
        "next_actions": _next_actions(verdict),
    }
    validate_forex_fury_replay_results_report(payload)
    return payload


def write_forex_fury_replay_results_report(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Path]:
    """Write JSON and Markdown summary reports for latest replay evidence."""

    report = build_forex_fury_replay_results()
    target_dir = output_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"forex-fury-replay-results-{stamp}-report.json"
    md_path = target_dir / f"forex-fury-replay-results-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_forex_fury_replay_results_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_forex_fury_replay_results_report(report_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """Load newest generated Forex Fury replay-results report."""

    payload = _read_latest(report_dir, "forex-fury-replay-results-*-report.json")
    validate_forex_fury_replay_results_report(payload)
    return payload


def validate_forex_fury_replay_results_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "claim_boundary",
        "candidate_summary",
        "condition_summary",
        "walk_forward_summary",
        "replay_verdict",
    }
    missing = required.difference(payload)
    if missing:
        raise ForexFuryReplayResultError(f"Forex Fury replay-results report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != "cas_forex_forex_fury_replay_results":
        raise ForexFuryReplayResultError("unexpected Forex Fury replay-results report_kind")
    if "do not execute EA binaries" not in str(payload.get("claim_boundary", "")):
        raise ForexFuryReplayResultError("Forex Fury replay-results claim boundary must preserve execution limit")


def render_forex_fury_replay_results_markdown(report: Mapping[str, Any]) -> str:
    condition = report.get("condition_summary") or {}
    wf = report.get("walk_forward_summary") or {}
    lines = [
        "# CAS Forex Forex Fury Replay Results",
        "",
        f"Created: `{report.get('created_at')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Verdict",
        "",
        f"- Replay verdict: `{report.get('replay_verdict')}`",
        f"- Adaptive next step: `{report.get('adaptive_compounding_next_step')}`",
        "",
        "## Condition Replay",
        "",
        f"- Run: `{condition.get('run_id')}`",
        f"- Cells: `{condition.get('cell_count')}`",
        f"- Non-gap cells: `{condition.get('non_gap_cell_count')}`",
        f"- Routes: `{condition.get('route_count')}`",
        f"- Overall gap fraction: `{condition.get('overall_gap_fraction')}`",
        "",
        "## Walk Forward",
        "",
        f"- Run: `{wf.get('run_id')}`",
        f"- Windows: `{wf.get('windows')}`",
        f"- Routed windows: `{wf.get('routed_windows')}`",
        f"- Positive routed windows: `{wf.get('positive_routed_windows')}`",
        f"- Positive routed window rate: `{wf.get('positive_routed_window_rate')}`",
        f"- Routed max drawdown: `{wf.get('routed_max_drawdown_pct')}`",
        f"- Trades: `{wf.get('routed_total_trades')}`",
        f"- Grade: `{wf.get('research_grade')}`",
        "",
        "## Top Condition Cells",
        "",
    ]
    for cell in condition.get("top_condition_cells", [])[:8]:
        lines.append(
            "- "
            f"`{cell.get('source')}` `{cell.get('symbol')}` `{cell.get('timeframe')}` "
            f"`{cell.get('regime')}` `{cell.get('setting')}` "
            f"return `{cell.get('mean_return_pct')}` dd `{cell.get('mean_max_dd_pct')}` "
            f"score `{cell.get('score')}`"
        )
    lines.extend(["", "## Next Actions", ""])
    for action in report.get("next_actions") or []:
        lines.append(f"- {action}")
    return "\n".join(lines) + "\n"


def _validate_inputs(candidates: Mapping[str, Any], condition: Mapping[str, Any], walk_forward: Mapping[str, Any]) -> None:
    if candidates.get("report_kind") != "cas_forex_forex_fury_replay_candidates":
        raise ForexFuryReplayResultError("candidate report must be a Forex Fury replay-candidates report")
    if not str(condition.get("run_id", "")).startswith("condition-lab-"):
        raise ForexFuryReplayResultError("condition report must be a condition-lab report")
    if not str(walk_forward.get("run_id", "")).startswith("walk-forward-"):
        raise ForexFuryReplayResultError("walk-forward report must be a walk-forward report")


def _read_latest(report_dir: Path, pattern: str) -> Dict[str, Any]:
    files = sorted(report_dir.glob(pattern))
    if not files:
        raise ForexFuryReplayResultError(f"No reports found for {pattern} in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    return payload


def _source_ref(report: Mapping[str, Any]) -> Dict[str, Any]:
    path = report.get("report_path")
    return {
        "run_id": report.get("run_id"),
        "report_kind": report.get("report_kind"),
        "path": path,
        "sha256": _file_sha256(path),
    }


def _top_condition_cells(cells: List[Mapping[str, Any]], limit: int = 12) -> List[Dict[str, Any]]:
    ranked = sorted(
        [cell for cell in cells if not cell.get("is_gap")],
        key=lambda cell: float(cell.get("score") or 0.0),
        reverse=True,
    )
    keys = (
        "source",
        "symbol",
        "timeframe",
        "event_context",
        "regime",
        "vol_mult",
        "setting",
        "family",
        "mean_return_pct",
        "mean_max_dd_pct",
        "mean_trades",
        "win_rate",
        "profit_factor",
        "region",
        "beta",
        "score",
    )
    return [{key: cell.get(key) for key in keys} for cell in ranked[:limit]]


def _replay_verdict(top_cells: List[Mapping[str, Any]], wf_summary: Mapping[str, Any]) -> str:
    has_positive_real_cell = any(
        cell.get("source") == "real" and float(cell.get("mean_return_pct") or 0.0) > 0
        for cell in top_cells
    )
    if (
        wf_summary.get("research_grade") == "WALK_FORWARD_LEAD"
        and float(wf_summary.get("positive_routed_window_rate") or 0.0) >= 0.5
        and float(wf_summary.get("routed_max_drawdown_pct") or 999.0) <= 5.0
        and int(wf_summary.get("routed_total_trades") or 0) >= 50
        and has_positive_real_cell
    ):
        return "REPLAY_LEAD_FOR_ADAPTIVE_REVIEW"
    return "REPLAY_NOT_PROMOTED"


def _next_actions(verdict: str) -> List[str]:
    if verdict == "REPLAY_LEAD_FOR_ADAPTIVE_REVIEW":
        return [
            "Create an adaptive compounding review that compares the top AUD/CAD M5 replay routes against current basket rules.",
            "Run the same replay summary for the next ranked Forex Fury candidates before promoting a single profile.",
            "Attach MT4 paper/demo receipts before any live execution claim.",
        ]
    return [
        "Keep the candidate in replay research.",
        "Run additional symbols/timeframes from the Forex Fury replay queue.",
        "Do not feed this candidate into adaptive compounding until replay evidence improves.",
    ]


def _file_sha256(path_value: object) -> Optional[str]:
    if not path_value:
        return None
    path = Path(str(path_value))
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

