"""HTTP route for the system-health snapshot.

Thin wrapper around `cas_forex.system_health_monitor`. Uses the module's
own ``load_system_health_inputs(repo_root)`` helper for disk I/O, then
runs the pure composer, then JSON-encodes the result.

Observational only — the route never advises operator action; it
describes WHAT IS.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter

from cas_forex.system_health_monitor import (
    SystemHealthSnapshot,
    compose_system_health,
    load_system_health_inputs,
)

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_loader() -> dict[str, Any]:
    return load_system_health_inputs(REPO_ROOT)


_LOADER: Callable[[], dict[str, Any]] = _default_loader


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER
    _LOADER = loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader


def _snapshot_to_payload(s: SystemHealthSnapshot) -> dict[str, Any]:
    return asdict(s)


@router.get("/snapshot")
async def get_system_health_snapshot() -> dict[str, Any]:
    """Return a snapshot of overall system health.

    ``overall_status`` is one of ``healthy``, ``degraded``, ``stale``,
    ``unknown``. ``diagnostic_hints`` is a tuple of factual observations
    (missing processes, stale artifacts, low disk) and never carries
    imperative operator instructions.
    """
    inputs = _LOADER()
    snapshot = compose_system_health(**inputs)
    return _snapshot_to_payload(snapshot)
