"""HTTP route for the stack health one-screen check.

Thin wrapper around `cas_forex.stack_health_check.compose_stack_health_report`.
Loads the inputs from disk via the module's own loader, runs the pure
composer, returns the structured report as JSON.

The Stack Status UI page polls this endpoint every 30 seconds.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter

from cas_forex.stack_health_check import (
    compose_stack_health_report,
    load_stack_health_inputs,
)

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_loader() -> dict[str, Any]:
    return load_stack_health_inputs(REPO_ROOT)


_LOADER: Callable[[], dict[str, Any]] = _default_loader


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER
    _LOADER = loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader


@router.get("/check")
async def get_stack_health_check() -> dict[str, Any]:
    """Compose and return the one-screen stack health report."""
    inputs = _LOADER()
    report = compose_stack_health_report(**inputs)
    return asdict(report)
