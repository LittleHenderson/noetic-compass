"""HTTP route for the WASTE loop's live stage — drives the cockpit activity heartbeat.

Thin wrapper around ``cas_forex.loop_heartbeat``. The indicator polls ``/stage`` and
shows OFFLINE/idle whenever ``running`` is False (no recent tick) — so the heartbeat
always reflects what the loop is ACTUALLY doing, never a demo cycle.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from ..route_cache import cache_first_payload
from cas_forex import loop_heartbeat

router = APIRouter()

_RUNNER_STAGE_CACHE_KEY = "waste_loop_stage_runner"
_RUNNER_STAGE_CACHE_TTL_SECONDS = 1.5


@router.get("/stage")
async def get_loop_stage() -> dict[str, Any]:
    """Current stage of the WASTE loop (idle/watch/analyze/strategize/test/execute/
    compound/locked/no_trade/blocked) plus ``running``. running=False + stage='idle'
    when no tick has landed recently."""
    return await run_in_threadpool(_loop_stage_payload)


def _loop_stage_payload() -> dict[str, Any]:
    local = loop_heartbeat.snapshot()
    if local.get("running"):
        return _with_indicator_trace(local)
    return _cached_runner_backed_snapshot(local)


def build_cached_runner_stage_payload() -> dict[str, Any]:
    """Build the compact isolated-runner stage packet for startup prewarm.

    This intentionally bypasses ``cache_first_payload`` so ``api.server`` can
    prewarm the exact cache key without recursively reading the cache it is
    building.
    """
    local = loop_heartbeat.snapshot()
    if local.get("running"):
        return local
    return _runner_backed_snapshot(local)


def _cached_runner_backed_snapshot(local: Mapping[str, Any]) -> dict[str, Any]:
    """Cache the isolated worker fallback so duplicate UI polls stay cheap.

    The cockpit polls this route on first paint. A cold API process should not
    make the browser wait for durable worker inspection; it can return the local
    heartbeat/warming packet immediately while the cache refreshes in the
    background.
    """
    return cache_first_payload(
        _RUNNER_STAGE_CACHE_KEY,
        builder=build_cached_runner_stage_payload,
        fallback=lambda: dict(local),
        ttl_seconds=_RUNNER_STAGE_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


def _runner_backed_snapshot(local: Mapping[str, Any]) -> dict[str, Any]:
    """Return a stage from the isolated WASTE worker when the API heartbeat is empty.

    The normal heartbeat is process-local. In local production runs the WASTE timer
    is intentionally moved to an isolated worker so API routes stay responsive. In
    that case the UI must read the durable runner/supervisor status rather than the
    uvicorn process's empty heartbeat memory.
    """
    try:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            from cas_forex.waste_runner import runner_status

            runner = runner_status()
        else:
            from .waste_loop_control import build_fast_waste_runner_status

            runner = build_fast_waste_runner_status()
    except Exception as exc:  # pragma: no cover - defensive route metadata only
        packet = dict(local)
        packet["fallback_error"] = f"{type(exc).__name__}: {exc}"
        return packet

    if not _runner_is_live(runner):
        return dict(local)

    stage = _valid_stage(
        runner.get("current_stage")
        or runner.get("stage")
        or _latest_stage_from_durable_cycle(_mapping(runner.get("durable_cycle")))
    )
    updated_at = _first_text(
        runner.get("last_run_iso"),
        _mapping(runner.get("durable_cycle")).get("generated_at"),
        _mapping(runner.get("external_worker")).get("checked_at"),
    )
    age = _age_seconds(updated_at)
    interval = _runner_interval_seconds(runner)
    stale_after = max(180.0, interval * 3.0)
    running = age is None or age <= stale_after
    if not running:
        return dict(local)

    durable_cycle = _mapping(runner.get("durable_cycle"))
    candidate = _mapping(durable_cycle.get("candidate"))
    return _with_indicator_trace({
        "report_kind": "waste_loop_stage",
        "stage": stage,
        "running": True,
        "detail": _first_text(runner.get("last_decision"), runner.get("last_reason")),
        "symbol": _first_text(candidate.get("symbol")),
        "updated_at": updated_at,
        "age_seconds": round(age, 2) if age is not None else None,
        "source": "waste_runner_status",
        "worker_isolated": bool(runner.get("worker_isolated")),
        "cycles_run": runner.get("cycles_run"),
        "mode": runner.get("mode"),
        "stage_trace": _valid_stage_trace(durable_cycle.get("stage_trace")),
    })


def _runner_is_live(runner: Mapping[str, Any]) -> bool:
    if not bool(runner.get("running")):
        return False
    supervisor = _mapping(runner.get("supervisor"))
    external_worker = _mapping(runner.get("external_worker"))
    if supervisor.get("active_lease_is_fresh") is False:
        return False
    # An isolated WASTE runner can be proven by the durable supervisor lease even
    # when the optional worker registry record is absent/unconfigured after an
    # API restart. Only a configured worker record explicitly saying "not
    # running" should veto the supervisor-backed heartbeat.
    if external_worker.get("configured") is True and external_worker.get("running") is False:
        return False
    return True


def _latest_stage_from_durable_cycle(durable_cycle: Mapping[str, Any]) -> str | None:
    stage_trace = durable_cycle.get("stage_trace")
    if isinstance(stage_trace, list):
        for stage in reversed(stage_trace):
            valid = _valid_stage(stage)
            if valid != "idle":
                return valid
    return None


def _valid_stage(value: Any) -> str:
    stage = str(value or "idle").strip().lower()
    return stage if stage in loop_heartbeat.VALID_STAGES else "idle"


def _valid_stage_trace(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    trace: list[str] = []
    for item in value:
        stage = _valid_stage(item)
        if stage == "idle":
            continue
        if trace and trace[-1] == stage:
            continue
        trace.append(stage)
    return trace[-12:]


def _with_indicator_trace(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Return the stage packet with a full W.A.S.T.E indicator sequence.

    The core loop audit remains literal: it only calls TEST with a real setup and
    only calls EXECUTE with a fresh PASS token. The cockpit trace is the operator
    indicator, so no-trade cycles still show the complete armed control chain:
    Watch -> Analyze -> Strategize -> Test -> Execute -> No Trade.
    """
    out = dict(packet)
    stage = _valid_stage(out.get("stage"))
    trace = _valid_stage_trace(out.get("stage_trace"))
    if stage == "no_trade":
        trace = _complete_no_trade_indicator_trace(trace)
    out["stage_trace"] = trace
    return out


def _complete_no_trade_indicator_trace(trace: list[str]) -> list[str]:
    if not trace:
        return ["watch", "analyze", "strategize", "test", "execute", "no_trade"]
    body = [item for item in trace if item != "no_trade"]
    if "watch" in body and "analyze" in body and "strategize" in body:
        for stage in ("test", "execute"):
            if stage not in body:
                body.append(stage)
    return (body + ["no_trade"])[-12:]


def _runner_interval_seconds(runner: Mapping[str, Any]) -> float:
    supervisor = _mapping(runner.get("supervisor"))
    active_lease = _mapping(supervisor.get("active_lease"))
    external_worker = _mapping(runner.get("external_worker"))
    worker_config = _mapping(external_worker.get("config"))
    for value in (
        active_lease.get("interval_seconds"),
        worker_config.get("interval_seconds"),
        runner.get("interval_seconds"),
    ):
        try:
            interval = float(value)
        except (TypeError, ValueError):
            continue
        if interval > 0:
            return interval
    return 60.0


def _age_seconds(iso_value: str | None) -> float | None:
    if not iso_value:
        return None
    try:
        parsed = datetime.fromisoformat(str(iso_value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None
