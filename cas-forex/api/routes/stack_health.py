"""HTTP route for the stack health one-screen check.

Thin wrapper around `cas_forex.stack_health_check.compose_stack_health_report`.
Loads the inputs from disk via the module's own loader, runs the pure
composer, returns the structured report as JSON.

The Stack Status UI page polls this endpoint every 30 seconds.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable

from fastapi import APIRouter

from ..route_cache import run_serial_refresh
from cas_forex.stack_health_check import (
    compose_stack_health_report,
    load_stack_health_inputs,
)

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]
_CACHE_TTL_SECONDS = 10.0
_CACHE_LOCK = threading.RLock()
_CACHE_PAYLOAD: dict[str, Any] | None = None
_CACHE_BUILT_AT = 0.0
_CACHE_BUILDING = False
_CACHE_ERROR: str | None = None


def _default_loader() -> dict[str, Any]:
    return load_stack_health_inputs(REPO_ROOT)


_LOADER: Callable[[], dict[str, Any]] = _default_loader


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER
    _LOADER = loader
    _clear_cache()


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader
    _clear_cache()


def _clear_cache() -> None:
    global _CACHE_PAYLOAD, _CACHE_BUILT_AT, _CACHE_BUILDING, _CACHE_ERROR
    with _CACHE_LOCK:
        _CACHE_PAYLOAD = None
        _CACHE_BUILT_AT = 0.0
        _CACHE_BUILDING = False
        _CACHE_ERROR = None


def _under_pytest() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _compose_payload() -> dict[str, Any]:
    inputs = _LOADER()
    return asdict(compose_stack_health_report(**inputs))


def _with_cache_meta(payload: dict[str, Any], status: str, built_at: float | None) -> dict[str, Any]:
    out = dict(payload)
    out["cache_status"] = status
    out["cache_ttl_seconds"] = _CACHE_TTL_SECONDS
    out["cache_built_at_epoch"] = built_at
    return out


def _warming_payload(status: str = "warming") -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "generated_at_iso": now_iso,
        "checks": [
            {
                "name": "stack-health-cache",
                "status": "UNKNOWN",
                "headline": "Stack health cache is warming.",
                "detail": (
                    "The API answered immediately and is composing the heavier "
                    "stack-health report in the background."
                ),
                "remediation": "Refresh after the cache warms.",
            }
        ],
        "overall_status": "UNKNOWN",
        "ok_count": 0,
        "degraded_count": 0,
        "missing_count": 0,
        "unknown_count": 1,
        "plain_english_summary": (
            "Stack health is warming cached diagnostics; controls can keep using "
            "the fast live state while this report finishes."
        ),
        "next_actions": ("Wait for the stack-health cache to warm.",),
        "cache_status": status,
        "cache_ttl_seconds": _CACHE_TTL_SECONDS,
        "cache_built_at_epoch": None,
        "cache_error": _CACHE_ERROR,
    }


def _refresh_cache_worker() -> None:
    global _CACHE_PAYLOAD, _CACHE_BUILT_AT, _CACHE_BUILDING, _CACHE_ERROR
    try:
        payload = run_serial_refresh(_compose_payload)
        with _CACHE_LOCK:
            _CACHE_PAYLOAD = payload
            _CACHE_BUILT_AT = time.time()
            _CACHE_ERROR = None
    except Exception as exc:  # pragma: no cover - defensive runtime guard.
        with _CACHE_LOCK:
            _CACHE_ERROR = f"{type(exc).__name__}: {exc}"
    finally:
        with _CACHE_LOCK:
            _CACHE_BUILDING = False


def _ensure_background_refresh() -> bool:
    global _CACHE_BUILDING
    with _CACHE_LOCK:
        if _CACHE_BUILDING:
            return False
        _CACHE_BUILDING = True
    thread = threading.Timer(0.2, _refresh_cache_worker)
    thread.name = "cas-forex-stack-health-cache"
    thread.daemon = True
    thread.start()
    return True


def start_stack_health_cache_refresh() -> bool:
    """Prewarm the stack-health cache before the browser opens the page."""

    return _ensure_background_refresh()


@router.get("/check")
async def get_stack_health_check() -> dict[str, Any]:
    """Compose and return the one-screen stack health report."""
    if _under_pytest():
        return _compose_payload()

    now = time.time()
    with _CACHE_LOCK:
        payload = _CACHE_PAYLOAD
        built_at = _CACHE_BUILT_AT
        building = _CACHE_BUILDING
        fresh = payload is not None and (now - built_at) <= _CACHE_TTL_SECONDS

    if fresh and payload is not None:
        return _with_cache_meta(payload, "fresh", built_at)

    if not building:
        _ensure_background_refresh()

    if payload is not None:
        return _with_cache_meta(payload, "refreshing", built_at)

    return _warming_payload()
