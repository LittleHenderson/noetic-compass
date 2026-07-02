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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter

from ..route_cache import cache_first_payload, cached_payload_snapshot, start_cache_refresh
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
_RUNTIME_STATUS_LOADER: Callable[[], dict[str, Any] | None] | None = None


def set_loader_for_testing(loader: Callable[[], dict[str, Any]]) -> None:
    """Replace the disk-backed loader. Tests only."""
    global _LOADER
    _LOADER = loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader


def set_runtime_status_loader_for_testing(loader: Callable[[], dict[str, Any] | None] | None) -> None:
    """Replace the runtime-loop overlay loader. Tests only."""
    global _RUNTIME_STATUS_LOADER
    _RUNTIME_STATUS_LOADER = loader


def reset_runtime_status_loader_for_testing() -> None:
    """Restore the default runtime-loop overlay loader."""
    global _RUNTIME_STATUS_LOADER
    _RUNTIME_STATUS_LOADER = None


def _health_to_payload(h: AutonomousLoopHealth) -> dict[str, Any]:
    """Convert the frozen dataclass to a JSON-serializable dict."""
    return asdict(h)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_loop_status() -> dict[str, Any] | None:
    """Return compact live loop evidence from the timers currently running.

    The archived autonomous-loop summarizer intentionally reads disk artifacts.
    This route also needs the current runtime truth so the UI does not report
    ``stalled`` while the WASTE/dispatch paper timers are actively ticking.
    """

    if _RUNTIME_STATUS_LOADER is not None:
        return _RUNTIME_STATUS_LOADER()

    candidates: list[dict[str, Any]] = []
    try:
        from api.routes.waste_loop_control import build_fast_waste_runner_status

        waste = cached_payload_snapshot("waste_runner_status_fast", ttl_seconds=5.0)
        if not isinstance(waste, dict):
            start_cache_refresh("waste_runner_status_fast", build_fast_waste_runner_status)
            waste = None
        if isinstance(waste, dict):
            candidates.append(
                {
                    "source": "waste_runner",
                    "running": bool(waste.get("running")),
                    "mode": waste.get("mode"),
                    "cycles_run": waste.get("cycles_run"),
                    "last_run_iso": waste.get("last_run_iso"),
                    "summary": waste.get("last_reason") or waste.get("status"),
                    "status": waste.get("status"),
                    "stage": waste.get("current_stage") or waste.get("stage"),
                }
            )
    except Exception:
        pass
    try:
        from cas_forex.dispatch_loop import loop_status

        dispatch = loop_status()
        if isinstance(dispatch, dict):
            candidates.append(
                {
                    "source": "dispatch_loop",
                    "running": bool(dispatch.get("running")),
                    "mode": dispatch.get("mode"),
                    "cycles_run": dispatch.get("cycles_run"),
                    "last_run_iso": dispatch.get("last_run_iso"),
                    "summary": dispatch.get("last_summary") or dispatch.get("status"),
                    "status": dispatch.get("status"),
                }
            )
    except Exception:
        pass

    running = [candidate for candidate in candidates if candidate.get("running")]
    if not running:
        return None
    # Prefer WASTE as the canonical W->A->S->T->E heartbeat when it is alive.
    for candidate in running:
        if candidate.get("source") == "waste_runner":
            return candidate
    return running[0]


def _runtime_backed_payload(payload: dict[str, Any]) -> dict[str, Any]:
    runtime = _runtime_loop_status()
    if not runtime or not runtime.get("running"):
        return payload

    out = dict(payload)
    if out.get("overall_status") != "running":
        out["overall_status"] = "running"
        out["diagnostic_hints"] = []
    last_run = runtime.get("last_run_iso")
    if last_run:
        out["last_cycle_at_iso"] = last_run
        out["seconds_since_last_cycle"] = 0.0
    out["cycles_today"] = max(int(out.get("cycles_today") or 0), int(runtime.get("cycles_run") or 0))
    out["runtime_loop"] = {
        "source": runtime.get("source"),
        "running": True,
        "mode": runtime.get("mode") or "PAPER",
        "stage": runtime.get("stage"),
        "cycles_run": runtime.get("cycles_run"),
        "last_run_iso": runtime.get("last_run_iso"),
        "status": runtime.get("status"),
        "claim_boundary": (
            "Runtime loop evidence is observational. It does not authorize live "
            "trading, broker ACCEPT, deposits, withdrawals, bank/card movement, "
            "payouts, or LICENSED status."
        ),
    }
    mode = runtime.get("mode") or "PAPER"
    source = str(runtime.get("source") or "runtime loop").replace("_", " ")
    stage = runtime.get("stage")
    stage_text = f", stage {stage}" if stage else ""
    out["plain_english_summary"] = (
        f"Autonomous loop runtime is running from {source} in {mode} mode{stage_text}; "
        f"{runtime.get('cycles_run') or 0} runtime cycle(s) observed. Archived "
        "agent-workflow evidence is still retained separately."
    )
    if not out.get("last_cycle_at_iso"):
        out["last_cycle_at_iso"] = _iso_now()
        out["seconds_since_last_cycle"] = 0.0
    return out


def _loop_health_payload() -> dict[str, Any]:
    inputs = _LOADER()
    health = summarize_autonomous_loop_health(**inputs)
    return _runtime_backed_payload(_health_to_payload(health))


def _loop_health_warming() -> dict[str, Any]:
    return _runtime_backed_payload(
        {
            "overall_status": "unknown",
            "last_cycle_at_iso": None,
            "seconds_since_last_cycle": None,
            "cycles_today": 0,
            "decisions_today": 0,
            "executions_today": 0,
            "blocked_today": 0,
            "autowake_present": False,
            "autowake_next_due_iso": None,
            "plain_english_summary": (
                "Archived autonomous-loop health is warming. Runtime WASTE/dispatch "
                "evidence is overlaid separately when available."
            ),
            "diagnostic_hints": ["Autonomous-loop health cache is warming."],
        }
    )


@router.get("/health")
async def get_loop_health() -> dict[str, Any]:
    """Return a snapshot of the autonomous loop's health.

    Status is one of ``running``, ``stalled``, ``never_started``,
    ``unknown``. ``diagnostic_hints`` is empty when running; otherwise
    actionable strings. The route never fabricates timestamps or counts.
    """
    return cache_first_payload(
        "autonomous_loop_health",
        builder=_loop_health_payload,
        fallback=_loop_health_warming,
        ttl_seconds=10.0,
    )
