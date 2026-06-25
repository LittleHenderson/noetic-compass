"""HTTP route for the autonomous loop health summary.

Thin wrapper around `cas_forex.autonomous_loop_health`. Uses the module's
own ``load_loop_health_inputs(repo_root)`` helper for disk I/O, then runs
the pure summariser, then JSON-encodes the result.

The route exists so the LLM bot can answer "is the autonomous loop alive?"
with a single capability call instead of assembling the answer from
multiple raw status endpoints.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter

from cas_forex.autonomous_loop_health import (
    AutonomousLoopHealth,
    load_loop_health_inputs,
    summarize_autonomous_loop_health,
)

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_loader() -> dict[str, Any]:
    return load_loop_health_inputs(REPO_ROOT)


_LOADER: Callable[[], dict[str, Any]] = _default_loader


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER
    _LOADER = loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader


def _health_to_payload(h: AutonomousLoopHealth) -> dict[str, Any]:
    """Convert the frozen dataclass to a JSON-serializable dict."""
    return asdict(h)


@router.get("/health")
async def get_loop_health() -> dict[str, Any]:
    """Return a snapshot of the autonomous loop's health.

    Status is one of ``running``, ``stalled``, ``never_started``,
    ``unknown``. ``diagnostic_hints`` is empty when running; otherwise
    actionable strings. The route never fabricates timestamps or counts.
    """
    inputs = _LOADER()
    health = summarize_autonomous_loop_health(**inputs)
    return _health_to_payload(health)
