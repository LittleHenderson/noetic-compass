"""HTTP routes for observational strategy ranking + diffing.

GET /ranked?limit=N — load all three sources from disk, normalize, rank,
return the top N. GET /diff?strategy_id_a=X&strategy_id_b=Y — load all
sources, look up both ids, return a field-level + plain-English diff.

Both endpoints are GET-only and observational: they describe what the
evidence shows, never what the operator should do.

Loader injection (``set_loader_for_testing`` / ``reset_loader_for_testing``)
mirrors the pattern in ``api/routes/strategy_dev_actions.py`` so tests can
run without touching real ``evidence_runs/`` files.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from fastapi import APIRouter, HTTPException, Query

from cas_forex.performance_discipline import build_performance_discipline_report
from cas_forex.strategy_comparison import (
    StrategyComparisonRecord,
    diff_strategies,
    normalize_records,
    rank_strategies,
)


router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]
FURY_GLOB = "evidence_runs/forex_fury_replay_candidates/forex-fury-replay-candidates-*-report.json"
DEV_QUEUE_GLOB = "evidence_runs/strategy_dev_queue/strategy-dev-queue-*-report.json"
STRATEGY_LEADS_PATH = REPO_ROOT / "strategy_leads.json"


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _load_latest(glob: str) -> Optional[dict[str, Any]]:
    matches = sorted(REPO_ROOT.glob(glob), reverse=True)
    for candidate in matches:
        payload = _read_json(candidate)
        if payload is not None:
            return payload
    return None


def _default_sources_loader() -> dict[str, Any]:
    """Return parsed payloads keyed by source for the normalizer.

    All three keys are always present; values may be ``None`` when nothing
    is on disk. Schema:

    ``{
        "fury_candidates": Sequence[Mapping] | None,
        "fury_imported_at": str | None,
        "strategy_leads": Sequence[Mapping] | None,
        "leads_imported_at": str | None,
        "strategy_dev_queue_items": Sequence[Mapping] | None,
        "dev_queue_imported_at": str | None,
    }``
    """

    fury_report = _load_latest(FURY_GLOB) or {}
    leads_payload = _read_json(STRATEGY_LEADS_PATH) or {}
    dev_queue_report = _load_latest(DEV_QUEUE_GLOB) or {}

    fury_candidates = fury_report.get("candidates")
    leads = leads_payload.get("leads")
    dev_queue_items = dev_queue_report.get("work_items") or dev_queue_report.get("items")

    return {
        "fury_candidates": fury_candidates if isinstance(fury_candidates, list) else None,
        "fury_imported_at": fury_report.get("created_at"),
        "strategy_leads": leads if isinstance(leads, list) else None,
        "leads_imported_at": leads_payload.get("updated_at"),
        "strategy_dev_queue_items": dev_queue_items if isinstance(dev_queue_items, list) else None,
        "dev_queue_imported_at": dev_queue_report.get("created_at"),
    }


_LOADER: Callable[[], dict[str, Any]] = _default_sources_loader


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed sources loader. Tests only."""
    global _LOADER
    _LOADER = loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_sources_loader


def _record_to_dict(rec: StrategyComparisonRecord) -> dict[str, Any]:
    payload = asdict(rec)
    # Convert tuple of dicts → list for JSON friendliness; dataclasses already
    # stringify metric tuples, but make the surface explicit.
    payload["metrics"] = [dict(m) for m in payload.get("metrics") or []]
    return payload


def _normalize_from_loader(payload: Mapping[str, Any]) -> tuple[StrategyComparisonRecord, ...]:
    return normalize_records(
        fury_candidates=payload.get("fury_candidates"),
        strategy_leads=payload.get("strategy_leads"),
        strategy_dev_queue_items=payload.get("strategy_dev_queue_items"),
        fury_imported_at=payload.get("fury_imported_at"),
        leads_imported_at=payload.get("leads_imported_at"),
        dev_queue_imported_at=payload.get("dev_queue_imported_at"),
    )


@router.get("/ranked")
async def ranked(limit: int = Query(20, ge=1, le=200)) -> dict[str, Any]:
    """Return the top ``limit`` strategy records by composite score."""

    payload = _LOADER()
    records = _normalize_from_loader(payload)
    report = rank_strategies(records)
    top = report.records[:limit]
    return {
        "generated_at_iso": report.generated_at_iso,
        "record_count": report.record_count,
        "returned_count": len(top),
        "limit": limit,
        "records": [_record_to_dict(r) for r in top],
        "plain_english_summary": report.plain_english_summary,
        "diagnostic_hints": list(report.diagnostic_hints),
    }


@router.get("/performance-discipline")
async def performance_discipline(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    """Return performance-reporting coverage for loaded strategy evidence."""

    payload = _LOADER()
    return build_performance_discipline_report(
        fury_candidates=payload.get("fury_candidates"),
        strategy_leads=payload.get("strategy_leads"),
        strategy_dev_queue_items=payload.get("strategy_dev_queue_items"),
        limit=limit,
    )


def _find_record(
    records: Sequence[StrategyComparisonRecord], strategy_id: str
) -> Optional[StrategyComparisonRecord]:
    for rec in records:
        if rec.strategy_id == strategy_id:
            return rec
    return None


@router.get("/diff")
async def diff(
    strategy_id_a: str = Query(..., min_length=1),
    strategy_id_b: str = Query(..., min_length=1),
) -> dict[str, Any]:
    """Return a field-level + plain-English diff between two records."""

    payload = _LOADER()
    records = _normalize_from_loader(payload)
    rec_a = _find_record(records, strategy_id_a)
    rec_b = _find_record(records, strategy_id_b)
    missing: list[str] = []
    if rec_a is None:
        missing.append(strategy_id_a)
    if rec_b is None:
        missing.append(strategy_id_b)
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "strategy_id_not_found",
                "message": (
                    "The following strategy id(s) were not found in the loaded "
                    f"sources: {', '.join(missing)}."
                ),
                "missing_ids": missing,
            },
        )
    assert rec_a is not None and rec_b is not None
    diff_obj = diff_strategies(rec_a, rec_b)
    return {
        "strategy_id_a": diff_obj.strategy_id_a,
        "strategy_id_b": diff_obj.strategy_id_b,
        "symbol_match": diff_obj.symbol_match,
        "timeframe_match": diff_obj.timeframe_match,
        "family_match": diff_obj.family_match,
        "field_diffs": [dict(d) for d in diff_obj.field_diffs],
        "plain_english_diff": diff_obj.plain_english_diff,
    }
