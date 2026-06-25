"""HTTP route for the portfolio risk monitoring snapshot.

Thin wrapper around `cas_forex.risk_monitoring.compose_portfolio_risk_snapshot`.
Reads the latest live telemetry payload (via the existing live-telemetry
collector) and the latest MT5 terminal API verifier report (for account
state). Both inputs are optional — if either is missing the snapshot
collapses to safe zeros and an explanatory plain-English summary.

This is OBSERVATIONAL telemetry. The endpoint never recommends an action.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from fastapi import APIRouter, HTTPException

from api import data as data_module
from api.routes import live_telemetry as live_telemetry_route
from cas_forex.risk_monitoring import (
    compose_portfolio_risk_snapshot,
    snapshot_to_payload,
)

router = APIRouter()


def _default_loader() -> dict[str, Any]:
    """Load live telemetry + account snapshot from disk-backed sources.

    Live telemetry comes from the existing `collect_live_telemetry()`
    aggregator (MT5 verifier → movement stream → empty), which is what the
    UI itself reads. The account snapshot is pulled from the MT5 terminal
    verifier report when present; missing → ``None``.
    """
    live_payload: Optional[Mapping[str, Any]]
    account_payload: Optional[Mapping[str, Any]]

    try:
        live_payload = live_telemetry_route.collect_live_telemetry()
    except Exception:
        live_payload = None

    try:
        report = data_module.mt5_terminal_api_verifier_latest()
    except HTTPException:
        report = None
    except Exception:
        report = None

    account_payload = report if isinstance(report, Mapping) else None

    return {
        "live_telemetry": live_payload,
        "account_snapshot": account_payload,
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


@router.get("/portfolio")
async def get_portfolio_risk() -> dict[str, Any]:
    """Return the current portfolio risk shape: per-symbol exposure,
    concentration, floating P/L envelope, margin utilization.

    Strictly observational; never proposes trades or position adjustments.
    """
    inputs = _LOADER()
    snapshot = compose_portfolio_risk_snapshot(
        live_telemetry=inputs.get("live_telemetry"),
        account_snapshot=inputs.get("account_snapshot"),
    )
    return snapshot_to_payload(snapshot)
