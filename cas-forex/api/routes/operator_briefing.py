"""HTTP route for the single-call operator briefing.

Thin wrapper around `cas_forex.operator_briefing`. Uses the module's
own ``load_operator_briefing_inputs(repo_root)`` helper for disk I/O,
then runs the pure composer, then JSON-encodes the result.

The route exists so the LLM cockpit bot can answer "what is going on
right now?" with a single capability call instead of chaining loop
health + latest decision + live telemetry + MT5 probe + readiness.
The briefing is OBSERVATIONAL only — it never advises trades.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter

from cas_forex.operator_briefing import (
    OperatorBriefing,
    compose_operator_briefing,
    load_operator_briefing_inputs,
)

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_loader() -> dict[str, Any]:
    return load_operator_briefing_inputs(REPO_ROOT)


_LOADER: Callable[[], dict[str, Any]] = _default_loader


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER
    _LOADER = loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader


def _briefing_to_payload(b: OperatorBriefing) -> dict[str, Any]:
    return asdict(b)


@router.get("")
@router.get("/")
async def get_operator_briefing() -> dict[str, Any]:
    """Return the single-call operator briefing.

    Aggregates loop health, latest decision summary, open positions,
    MT5 connection state, and readiness gate counts into one
    observational snapshot. Returns 200 even when all inputs are
    missing (briefing reports ``loop_health_status: "unknown"``).
    """
    inputs = _LOADER()
    briefing = compose_operator_briefing(**inputs)
    return _briefing_to_payload(briefing)
