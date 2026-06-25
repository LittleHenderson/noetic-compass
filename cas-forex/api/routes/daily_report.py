"""HTTP routes for the end-of-day operator report.

Thin wrappers around :mod:`cas_forex.daily_report_generator`. The disk
loader is the module's own ``load_daily_report_inputs(repo_root, date)``;
the pure composer is :func:`compose_daily_report`. Routes JSON-encode
the resulting :class:`DailyReport` dataclass.

The report is OBSERVATIONAL only — it reports what HAPPENED during a
given trading day and never advises trades.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, HTTPException

from cas_forex.daily_report_generator import (
    DailyReport,
    compose_daily_report,
    load_daily_report_inputs,
)


router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_loader(report_date: str) -> dict[str, Any]:
    return load_daily_report_inputs(REPO_ROOT, report_date)


_LOADER: Callable[[str], dict[str, Any]] = _default_loader


def set_loader_for_testing(loader: Callable[[str], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER
    _LOADER = loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader


def _report_to_payload(report: DailyReport) -> dict[str, Any]:
    payload = asdict(report)
    # Dataclass sections also serialize as dicts; tuples become lists.
    return payload


def _validate_date(report_date: str) -> str:
    try:
        datetime.strptime(report_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report_date {report_date!r}; expected YYYY-MM-DD.",
        )
    return report_date


@router.get("/today")
async def get_daily_report_today() -> dict[str, Any]:
    """Return today's end-of-day operator report (UTC date)."""
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    inputs = _LOADER(report_date)
    report = compose_daily_report(report_date=report_date, **inputs)
    return _report_to_payload(report)


@router.get("/{report_date}")
async def get_daily_report_for_date(report_date: str) -> dict[str, Any]:
    """Return the end-of-day operator report for a specific date (YYYY-MM-DD)."""
    safe_date = _validate_date(report_date)
    inputs = _LOADER(safe_date)
    report = compose_daily_report(report_date=safe_date, **inputs)
    return _report_to_payload(report)
