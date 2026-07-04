from __future__ import annotations

import threading
import time
import os
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from .data import dashboard_fast_state, dashboard_shell_state, dashboard_state
from .route_cache import cached_payload_snapshot, run_serial_refresh, start_cache_refresh
from .routes import proof, bundle, strategy, adaptive, settings, mt, pcba, account, movement, reconciliation, readiness, timeframes, live_telemetry, agent_decision, agent_decision_history, autonomous_loop, notifications, forex_fury_promote, strategy_dev_actions, operator_briefing, risk_monitoring, webhook_notifications, system_health, strategy_comparison, daily_report, stack_health, operator_audit, order_dispatch, money_movement, broker_control, assistant, risk_control, live_enable, chart, dispatch_loop, mt5_live, proof_control, mt4_control, loop_stage, waste_loop_control, ai_control_authority, auto_halt, broker_truth_monitor, broker_reality, live_pilot, live_recovery, live_money, live_order_dry_run, ai_operator, owner_auth, owner_command

app = FastAPI(title="CAS Forex API", version="0.1.0")

_DASHBOARD_CACHE_TTL_SECONDS = 300.0
_DASHBOARD_SHELL_CACHE_TTL_SECONDS = 10.0
_DASHBOARD_FAST_CACHE_TTL_SECONDS = 30.0
_DASHBOARD_SHELL_CACHE_REFRESH_DELAY_SECONDS = 0.05
_DASHBOARD_FAST_CACHE_REFRESH_DELAY_SECONDS = 0.25
_DASHBOARD_FULL_CACHE_REFRESH_DELAY_SECONDS = 0.2
_STARTUP_ROUTE_CACHE_DELAY_SECONDS = 1.0
_STARTUP_ROUTE_CACHE_STAGGER_SECONDS = 0.1
_dashboard_cache_lock = threading.Lock()
_dashboard_cache: dict[str, Any] = {
    "payload": None,
    "built_at": 0.0,
    "building": False,
    "error": None,
}
_dashboard_shell_cache_lock = threading.Lock()
_dashboard_shell_cache: dict[str, Any] = {
    "payload": None,
    "built_at": 0.0,
    "building": False,
    "error": None,
}
_dashboard_fast_cache_lock = threading.Lock()
_dashboard_fast_cache: dict[str, Any] = {
    "payload": None,
    "built_at": 0.0,
    "building": False,
    "error": None,
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dashboard_cache_meta(
    kind: str,
    status: str,
    built_at: float | None = None,
    *,
    ttl_seconds: float | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "full_cache_status": status,
        "built_at_epoch": built_at,
        "generated_at_iso": _iso_now(),
        "ttl_seconds": _DASHBOARD_CACHE_TTL_SECONDS if ttl_seconds is None else ttl_seconds,
    }


def _with_dashboard_meta(payload: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    packet = dict(payload)
    packet["dashboardMeta"] = meta
    return packet


def _with_live_dashboard_overlays(payload: dict[str, Any]) -> dict[str, Any]:
    packet = dict(payload)
    try:
        live = _dashboard_fast_cache_payload()
    except Exception:
        return packet
    if not isinstance(live, dict):
        return packet
    for key in (
        "ownerControl",
        "movementStream",
        "mt5Receipt",
        "mt5ProbeStatus",
        "wasteLoop",
        "wastePaperSampleCollectorScheduler",
    ):
        if key in live:
            packet[key] = live[key]
    return packet


def _cached_fast_or_warming_dashboard(status: str) -> dict[str, Any]:
    fast = _dashboard_fast_cache_payload()
    if isinstance(fast, dict):
        return _with_dashboard_meta(
            fast,
            _dashboard_cache_meta(
                "fast",
                status,
                ttl_seconds=_DASHBOARD_FAST_CACHE_TTL_SECONDS,
            ),
        )
    _start_dashboard_fast_cache_refresh()
    return _with_dashboard_meta(
        _dashboard_fast_warming(),
        _dashboard_cache_meta(
            "fast",
            "warming",
            None,
            ttl_seconds=_DASHBOARD_FAST_CACHE_TTL_SECONDS,
        ),
    )


def _dashboard_shell_warming() -> dict[str, Any]:
    return {
        "wasteLoop": {
            "report_kind": "cas_forex_waste_runner_shell",
            "running": False,
            "status": "WARMING",
            "current_stage": "syncing",
            "cycles_run": None,
            "mode": None,
            "last_reason": "Dashboard shell status is warming.",
            "last_run_iso": None,
            "worker_isolated": False,
            "claim_boundary": (
                "Shell WASTE status is observational only. It does not authorize "
                "live trading, broker ACCEPT, LICENSED status, deposits, withdrawals, "
                "bank/card movement, payouts, or order execution."
            ),
        },
    }


def _dashboard_fast_warming() -> dict[str, Any]:
    return {
        "proofProgress": {
            "report_kind": "cas_forex_dashboard_proof_progress_summary",
            "readiness_status": "WARMING",
            "min_daily_bundles_for_ui": 0,
            "completed_trading_days": 0,
            "complete_bundle_days": 0,
            "complete_bundle_date_count": 0,
            "chains_verified_count": 0,
            "chains_expected_count": 3,
            "paper_proof_chain_verified": False,
            "blocker_count": 1,
            "summary_only": True,
        },
        "riskBudget": {
            "report_kind": "cas_forex_dashboard_risk_budget_summary",
            "date": "",
            "review_count": 0,
            "risk_status": "WARMING",
            "risk_status_counts": {},
            "chain_verified": False,
            "account_equity": 0,
            "max_risk_per_trade_pct": 0,
            "daily_risk_budget_pct": 0,
            "daily_risk_budget_usd": 0,
            "max_position_lots": 0,
            "planned_risk_total_usd": 0,
            "planned_lots_total": 0,
            "sizing_count": 0,
            "summary_only": True,
            "claim_boundary": "",
            "claim_boundary_present": False,
        },
    }


def _dashboard_cache_disabled_for_tests() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ


def _dashboard_shell_cache_payload(*, require_fresh: bool = False) -> dict[str, Any] | None:
    now = time.time()
    with _dashboard_shell_cache_lock:
        payload = _dashboard_shell_cache["payload"]
        built_at = float(_dashboard_shell_cache["built_at"] or 0.0)
    if not isinstance(payload, dict):
        return None
    if require_fresh and now - built_at > _DASHBOARD_SHELL_CACHE_TTL_SECONDS:
        return None
    return dict(payload)


def _refresh_dashboard_shell_cache_blocking() -> dict[str, Any]:
    try:
        payload = run_serial_refresh(dashboard_shell_state)
        built_at = time.time()
        with _dashboard_shell_cache_lock:
            _dashboard_shell_cache["payload"] = payload
            _dashboard_shell_cache["built_at"] = built_at
            _dashboard_shell_cache["building"] = False
            _dashboard_shell_cache["error"] = None
        return payload
    except Exception as exc:
        with _dashboard_shell_cache_lock:
            _dashboard_shell_cache["building"] = False
            _dashboard_shell_cache["error"] = f"{type(exc).__name__}: {exc}"
        raise


def _refresh_dashboard_shell_cache_background() -> None:
    try:
        _refresh_dashboard_shell_cache_blocking()
    except Exception as exc:  # pragma: no cover - defensive cache metadata only
        with _dashboard_shell_cache_lock:
            _dashboard_shell_cache["building"] = False
            _dashboard_shell_cache["error"] = f"{type(exc).__name__}: {exc}"


def _start_dashboard_shell_cache_refresh() -> bool:
    with _dashboard_shell_cache_lock:
        if _dashboard_shell_cache["building"]:
            return False
        _dashboard_shell_cache["building"] = True
    thread = threading.Timer(_DASHBOARD_SHELL_CACHE_REFRESH_DELAY_SECONDS, _refresh_dashboard_shell_cache_background)
    thread.name = "cas-forex-dashboard-shell-cache"
    thread.daemon = True
    thread.start()
    return True


def _dashboard_fast_cache_payload(*, require_fresh: bool = False) -> dict[str, Any] | None:
    now = time.time()
    with _dashboard_fast_cache_lock:
        payload = _dashboard_fast_cache["payload"]
        built_at = float(_dashboard_fast_cache["built_at"] or 0.0)
    if not isinstance(payload, dict):
        return None
    if require_fresh and now - built_at > _DASHBOARD_FAST_CACHE_TTL_SECONDS:
        return None
    return dict(payload)


def _refresh_dashboard_fast_cache_blocking() -> dict[str, Any]:
    try:
        payload = run_serial_refresh(dashboard_fast_state)
        built_at = time.time()
        with _dashboard_fast_cache_lock:
            _dashboard_fast_cache["payload"] = payload
            _dashboard_fast_cache["built_at"] = built_at
            _dashboard_fast_cache["building"] = False
            _dashboard_fast_cache["error"] = None
        return payload
    except Exception as exc:
        with _dashboard_fast_cache_lock:
            _dashboard_fast_cache["building"] = False
            _dashboard_fast_cache["error"] = f"{type(exc).__name__}: {exc}"
        raise


def _refresh_dashboard_fast_cache_background() -> None:
    try:
        _refresh_dashboard_fast_cache_blocking()
    except Exception as exc:  # pragma: no cover - defensive cache metadata only
        with _dashboard_fast_cache_lock:
            _dashboard_fast_cache["building"] = False
            _dashboard_fast_cache["error"] = f"{type(exc).__name__}: {exc}"


def _start_dashboard_fast_cache_refresh() -> bool:
    with _dashboard_fast_cache_lock:
        if _dashboard_fast_cache["building"]:
            return False
        _dashboard_fast_cache["building"] = True
    thread = threading.Timer(_DASHBOARD_FAST_CACHE_REFRESH_DELAY_SECONDS, _refresh_dashboard_fast_cache_background)
    thread.name = "cas-forex-dashboard-fast-cache"
    thread.daemon = True
    thread.start()
    return True


def _refresh_dashboard_cache_blocking() -> dict[str, Any]:
    try:
        payload = run_serial_refresh(dashboard_state)
        built_at = time.time()
        with _dashboard_cache_lock:
            _dashboard_cache["payload"] = payload
            _dashboard_cache["built_at"] = built_at
            _dashboard_cache["building"] = False
            _dashboard_cache["error"] = None
        return payload
    except Exception as exc:
        with _dashboard_cache_lock:
            _dashboard_cache["building"] = False
            _dashboard_cache["error"] = f"{type(exc).__name__}: {exc}"
        raise


def _refresh_dashboard_cache_background() -> None:
    try:
        _refresh_dashboard_cache_blocking()
    except Exception as exc:  # pragma: no cover - defensive cache metadata only
        with _dashboard_cache_lock:
            _dashboard_cache["building"] = False
            _dashboard_cache["error"] = f"{type(exc).__name__}: {exc}"


def _start_dashboard_cache_refresh() -> bool:
    with _dashboard_cache_lock:
        if _dashboard_cache["building"]:
            return False
        _dashboard_cache["building"] = True
    thread = threading.Timer(_DASHBOARD_FULL_CACHE_REFRESH_DELAY_SECONDS, _refresh_dashboard_cache_background)
    thread.name = "cas-forex-dashboard-full-cache"
    thread.daemon = True
    thread.start()
    return True

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=(
        r"^(https?://("
        r"localhost|127\.0\.0\.1|0\.0\.0\.0|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
        r")(:\d+)?|capacitor://localhost)$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def warm_dashboard_fast_cache() -> None:
    if not _dashboard_cache_disabled_for_tests():
        _restore_owner_runtime_switches()
        _start_dashboard_shell_cache_refresh()
        _start_dashboard_fast_cache_refresh()
        _start_startup_route_cache_refreshes()


def _start_startup_route_cache_refreshes() -> dict[str, bool]:
    """Prewarm hot read-only packets the cockpit asks for on shell/idle hydration."""

    starters = {
        "waste_loop_stage_runner": loop_stage.build_cached_runner_stage_payload,
        "proof_control_state": proof_control._state_payload,
        "waste_runner_status_fast": waste_loop_control.build_fast_waste_runner_status,
        "broker_truth_monitor_fast_status": broker_truth_monitor.broker_truth_fast_status,
        "dispatch_loop_status": dispatch_loop.loop_status,
        "live_telemetry": live_telemetry.collect_live_telemetry,
        "live_enable_authorization_report": live_enable.build_authorization_report,
        "live_enable_state_report": live_enable.build_live_enable_report,
        "settings_authority_boundary": settings.authority_boundary,
        "settings_runtime_gates": settings.runtime_gates_report,
        "pcba_cockpit": pcba.pcba_cockpit,
        "live_money_progression_packet_fast": live_money._build_fast_progression_packet,
        "live_readiness:False": lambda: readiness.live_readiness(sync_to_broker=False),
        "account_reconciliation:False": lambda: reconciliation.account_reconciliation(sync_to_broker=False),
        "auto_halt_status": lambda: auto_halt.auto_halt_status(persist=True),
        "verified_profit_sweep_policy": money_movement._verified_profit_sweep_policy_payload,
        "verified_profit_sweep_state": money_movement._verified_profit_sweep_state_payload,
        "verified_profit_sweep_payout_recovery": lambda: money_movement._attempt_store().build_status(),
        "live_recovery_status": live_recovery.build_live_recovery_report,
        "live_order_dry_run_latest": live_order_dry_run._latest_live_order_dry_run_payload,
        "live_order_dry_run_review": live_order_dry_run.build_live_order_dry_run_review,
        "waste_entry_dispatch_handoff": live_order_dry_run._waste_entry_handoff_payload,
        "waste_entry_pilot_promotion": live_order_dry_run._waste_entry_pilot_promotion_payload,
        "compound_add_order_dry_run_latest": live_order_dry_run._latest_compound_add_order_dry_run_payload,
        "compound_add_order_dry_run_review": live_order_dry_run.build_compound_add_order_dry_run_review,
        "compound_add_dispatch_handoff": live_order_dry_run._compound_add_handoff_payload,
        "mt5_market_data_diagnostic_latest": waste_loop_control.latest_mt5_market_data_diagnostic,
        "waste_real_candle_probe_latest": waste_loop_control.latest_waste_real_candle_probe,
    }
    results: dict[str, bool] = {}
    for index, (key, builder) in enumerate(starters.items()):
        try:
            results[key] = start_cache_refresh(
                key,
                builder,
                delay_seconds=(
                    _STARTUP_ROUTE_CACHE_DELAY_SECONDS
                    + index * _STARTUP_ROUTE_CACHE_STAGGER_SECONDS
                ),
            )
        except Exception:
            results[key] = False
    try:
        results["stack_health_check"] = stack_health.start_stack_health_cache_refresh()
    except Exception:
        results["stack_health_check"] = False
    try:
        results["operator_briefing"] = operator_briefing.start_operator_briefing_cache_refresh()
    except Exception:
        results["operator_briefing"] = False
    return results


_DASHBOARD_DEEP_CACHE_PACKETS: dict[str, tuple[str, str, float]] = {
    "accountReconciliation": ("account_reconciliation:False", "cas_forex_account_reconciliation", 10.0),
    "liveReadiness": ("live_readiness:False", "cas_forex_live_readiness", 60.0),
    "autoHalt": ("auto_halt_status", "cas_forex_auto_halt_status", 10.0),
    "brokerTruthMonitor": ("broker_truth_monitor_fast_status", "cas_forex_broker_truth_monitor_status_fast", 5.0),
    "wasteLoop": ("waste_runner_status_fast", "cas_forex_waste_runner_fast", 5.0),
    "verifiedProfitSweepPolicy": ("verified_profit_sweep_policy", "cas_forex_verified_profit_sweep_policy", 30.0),
    "verifiedProfitSweepState": ("verified_profit_sweep_state", "cas_forex_verified_profit_sweep_preview", 15.0),
    "payoutRecovery": ("verified_profit_sweep_payout_recovery", "cas_forex_payout_recovery", 15.0),
    "liveRecovery": ("live_recovery_status", "cas_forex_live_recovery_review", 10.0),
    "mt5MarketDataDiagnostic": ("mt5_market_data_diagnostic_latest", "cas_forex_mt5_market_data_diagnostic", 15.0),
    "wasteRealCandleProbe": ("waste_real_candle_probe_latest", "cas_forex_waste_real_candle_probe", 15.0),
    "liveOrderDryRun": ("live_order_dry_run_latest", "cas_forex_live_order_dry_run_latest", 10.0),
    "liveOrderDryRunReview": ("live_order_dry_run_review", "cas_forex_live_order_dry_run_review", 10.0),
    "wasteEntryDispatchHandoff": ("waste_entry_dispatch_handoff", "cas_forex_waste_entry_dispatch_handoff", 10.0),
    "wasteEntryPilotPromotion": ("waste_entry_pilot_promotion", "cas_forex_waste_pilot_promotion", 10.0),
    "compoundAddOrderDryRun": ("compound_add_order_dry_run_latest", "cas_forex_compound_add_order_dry_run_latest", 10.0),
    "compoundAddOrderDryRunReview": ("compound_add_order_dry_run_review", "cas_forex_compound_add_order_dry_run_review", 10.0),
    "compoundAddDispatchHandoff": ("compound_add_dispatch_handoff", "cas_forex_waste_compound_add_dispatch_handoff", 10.0),
}


def _dashboard_deep_warming_packet(report_kind: str) -> dict[str, Any]:
    return {
        "report_kind": report_kind,
        "status": "WARMING",
        "cache_status": "warming",
        "cache_built_at_epoch": None,
        "cache_age_seconds": None,
        "cache_stale": False,
        "cache_refreshing": True,
        "claim_boundary": (
            "Dashboard deep cache warming is observational only. It does not "
            "authorize live trading, create owner ACCEPT, place orders, deposit, "
            "withdraw, move bank/card funds, automate payouts, or alter funding custody."
        ),
    }


def _dashboard_deep_cache_snapshot() -> dict[str, Any]:
    packets: dict[str, Any] = {}
    warm_count = 0
    for field, (key, report_kind, ttl_seconds) in _DASHBOARD_DEEP_CACHE_PACKETS.items():
        packet = cached_payload_snapshot(key, ttl_seconds=ttl_seconds)
        if packet is None:
            packet = _dashboard_deep_warming_packet(report_kind)
        else:
            warm_count += 1
        packets[field] = packet
    return {
        "report_kind": "cas_forex_dashboard_deep_cache_snapshot",
        "generated_at_iso": _iso_now(),
        "status": "READY" if warm_count else "WARMING",
        "packet_count": len(packets),
        "warm_packet_count": warm_count,
        "packets": packets,
        "claim_boundary": (
            "Dashboard deep cache snapshot is read-only cache hydration. It does "
            "not run strategy builders inline, place orders, create owner ACCEPT, "
            "deposit, withdraw, move bank/card funds, automate payouts, or alter "
            "broker/funding custody."
        ),
    }


def _restore_owner_runtime_switches() -> None:
    """Restore owner-desired paper loops after API restart.

    These calls only restore persisted PAPER/read-only schedulers. The called
    modules fail closed if the runtime is not paper-safe.
    """
    try:
        from cas_forex.dispatch_loop import restore_desired_loop

        restore_desired_loop()
    except Exception:
        pass
    try:
        from api.routes.proof_control import restore_desired_auto_runner

        restore_desired_auto_runner()
    except Exception:
        pass
    try:
        from cas_forex.ai_operator_runner import restore_desired_state_on_startup

        restore_desired_state_on_startup()
    except Exception:
        pass


_REQUEST_TRACE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "runtime",
    "api-request-trace.jsonl",
)
_TRACE_SKIP_GET_PATHS = {
    "/health",
    "/api/forex/health",
    "/api/forex/dashboard",
    "/api/forex/dashboard/shell",
    "/api/forex/dashboard/fast",
    "/api/forex/dashboard/deep-cache",
    "/api/forex/live-telemetry",
    "/api/forex/agent-decision/latest",
    "/api/forex/mt/probe/latest",
    "/api/forex/risk-monitoring/portfolio",
    "/api/forex/autonomous-loop/health",
    "/api/forex/stack-health/check",
    "/api/forex/notifications/subscriptions",
    "/api/forex/webhook-notifications/subscriptions",
    "/api/forex/proof-control/state",
    "/api/forex/settings/authority-boundary",
    "/api/forex/settings/runtime-gates",
    "/api/forex/pcba/cockpit",
    "/api/forex/readiness/live",
    "/api/forex/live-enable/authorization",
    "/api/forex/live-enable/state",
    "/api/forex/waste-loop/stage",
    "/api/forex/dispatch-loop/status",
    "/api/forex/waste-loop-control/status/fast",
    "/api/forex/waste-loop-control/paper-sample-collector/scheduler",
    "/api/forex/broker-truth-monitor/status/fast",
    "/api/forex/operator-briefing",
    "/api/forex/account/ledger",
    "/api/forex/movement/snapshot",
    "/api/forex/reconciliation/account",
    "/api/forex/account/broker-sync-risk-preview",
    "/api/forex/money-movement/verified-profit-sweep/policy",
    "/api/forex/money-movement/verified-profit-sweep/state",
    "/api/forex/money-movement/verified-profit-sweep/payout-recovery",
    "/api/forex/live-money/progression-packet/fast",
    "/api/forex/live-recovery/status",
    "/api/forex/auto-halt/status",
    "/api/forex/waste-loop-control/mt5-market-data-diagnostic/latest",
    "/api/forex/waste-loop-control/real-candle-probe/latest",
    "/api/forex/live-order-dry-run/latest",
    "/api/forex/live-order-dry-run/review",
    "/api/forex/live-order-dry-run/waste-entry-order/dispatch-handoff",
    "/api/forex/live-order-dry-run/waste-entry-order/pilot-promotion",
    "/api/forex/live-order-dry-run/compound-add-order/latest",
    "/api/forex/live-order-dry-run/compound-add-order/review",
    "/api/forex/live-order-dry-run/compound-add-order/dispatch-handoff",
}
_TRACE_SKIP_GET_PREFIXES = (
    "/api/forex/timeframes/",
)


def _should_trace_request(method: str, path: str) -> bool:
    """Keep hot UI polling endpoints off the synchronous JSONL trace path."""
    if method.upper() not in {"GET", "OPTIONS"}:
        return True
    if path in _TRACE_SKIP_GET_PATHS:
        return False
    return not any(path.startswith(prefix) for prefix in _TRACE_SKIP_GET_PREFIXES)


def _trace_request_event(event: str, request: Request, extra: dict[str, Any] | None = None) -> None:
    try:
        os.makedirs(os.path.dirname(_REQUEST_TRACE_PATH), exist_ok=True)
        record = {
            "event": event,
            "at": _iso_now(),
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
        }
        if extra:
            record.update(extra)
        with open(_REQUEST_TRACE_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    except Exception:
        pass


def _owner_auth_enforced() -> bool:
    """Owner-auth is enforced in normal operation, and bypassed under pytest so
    the route test-suite (which speaks from a loopback-equivalent host anyway)
    stays green. Mirrors ``_dashboard_cache_disabled_for_tests``."""
    return not os.environ.get("PYTEST_CURRENT_TEST")


@app.middleware("http")
async def owner_auth_gate(request: Request, call_next):
    """WHO-may-drive gate: loopback (the owner's own PC) is always allowed;
    off-box requests need LAN mode ON + a valid owner token. See
    ``cas_forex.owner_auth``. This only decides admission — every route still
    carries its own trading/money gates behind it."""
    if _owner_auth_enforced():
        from cas_forex import owner_auth
        from fastapi.responses import JSONResponse

        decision = owner_auth.evaluate_request(
            method=request.method,
            client_host=request.client.host if request.client else None,
            path=request.url.path,
            headers=request.headers,
        )
        if not decision.allow:
            return JSONResponse(
                status_code=decision.status,
                content={
                    "error": "owner_auth_required",
                    "detail": decision.reason,
                    "report_kind": "cas_forex_owner_auth_denied",
                },
            )
    return await call_next(request)


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    if not _should_trace_request(request.method, request.url.path):
        return await call_next(request)

    _trace_request_event("start", request)
    started = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        _trace_request_event(
            "error",
            request,
            {"elapsed_ms": round((time.time() - started) * 1000, 2), "error": f"{type(exc).__name__}: {exc}"},
        )
        raise
    _trace_request_event(
        "end",
        request,
        {"elapsed_ms": round((time.time() - started) * 1000, 2), "status_code": response.status_code},
    )
    return response

app.include_router(proof.router, prefix="/api/forex/proof", tags=["proof"])
app.include_router(bundle.router, prefix="/api/forex/bundle", tags=["bundle"])
app.include_router(strategy.router, prefix="/api/forex/strategy", tags=["strategy"])
app.include_router(adaptive.router, prefix="/api/forex/adaptive", tags=["adaptive"])
app.include_router(settings.router, prefix="/api/forex/settings", tags=["settings"])
app.include_router(pcba.router, prefix="/api/forex/pcba", tags=["pcba"])
app.include_router(mt.router, prefix="/api/forex/mt", tags=["mt"])
app.include_router(account.router, prefix="/api/forex/account", tags=["account"])
app.include_router(movement.router, prefix="/api/forex/movement", tags=["movement"])
app.include_router(reconciliation.router, prefix="/api/forex/reconciliation", tags=["reconciliation"])
app.include_router(readiness.router, prefix="/api/forex/readiness", tags=["readiness"])
app.include_router(timeframes.router, prefix="/api/forex/timeframes", tags=["timeframes"])
app.include_router(live_telemetry.router, prefix="/api/forex/live-telemetry", tags=["live-telemetry"])
app.include_router(agent_decision.router, prefix="/api/forex/agent-decision", tags=["agent-decision"])
app.include_router(agent_decision_history.router, prefix="/api/forex/agent-decision", tags=["agent-decision"])
app.include_router(autonomous_loop.router, prefix="/api/forex/autonomous-loop", tags=["autonomous-loop"])
app.include_router(loop_stage.router, prefix="/api/forex/waste-loop", tags=["waste-loop"])
app.include_router(notifications.router, prefix="/api/forex/notifications", tags=["notifications"])
app.include_router(forex_fury_promote.router, prefix="/api/forex/forex-fury-promote", tags=["forex-fury-promote"])
app.include_router(strategy_dev_actions.router, prefix="/api/forex/strategy-dev-actions", tags=["strategy-dev-actions"])
app.include_router(operator_briefing.router, prefix="/api/forex/operator-briefing", tags=["operator-briefing"])
app.include_router(risk_monitoring.router, prefix="/api/forex/risk-monitoring", tags=["risk-monitoring"])
app.include_router(webhook_notifications.router, prefix="/api/forex/webhook-notifications", tags=["webhook-notifications"])
app.include_router(system_health.router, prefix="/api/forex/system-health", tags=["system-health"])
app.include_router(strategy_comparison.router, prefix="/api/forex/strategy-comparison", tags=["strategy-comparison"])
app.include_router(daily_report.router, prefix="/api/forex/daily-report", tags=["daily-report"])
app.include_router(stack_health.router, prefix="/api/forex/stack-health", tags=["stack-health"])
app.include_router(operator_audit.router, prefix="/api/forex/operator-audit", tags=["operator-audit"])
app.include_router(order_dispatch.router, prefix="/api/forex/order-dispatch", tags=["order-dispatch"])
app.include_router(money_movement.router, prefix="/api/forex/money-movement", tags=["money-movement"])
app.include_router(broker_control.router, prefix="/api/forex/broker-control", tags=["broker-control"])
app.include_router(assistant.router, prefix="/api/forex/assistant", tags=["assistant"])
app.include_router(risk_control.router, prefix="/api/forex/risk-control", tags=["risk-control"])
app.include_router(live_enable.router, prefix="/api/forex/live-enable", tags=["live-enable"])
app.include_router(chart.router, prefix="/api/forex/chart", tags=["chart"])
app.include_router(dispatch_loop.router, prefix="/api/forex/dispatch-loop", tags=["dispatch-loop"])
app.include_router(mt5_live.router, prefix="/api/forex/mt5", tags=["mt5-live"])
app.include_router(proof_control.router, prefix="/api/forex/proof-control", tags=["proof-control"])
app.include_router(mt4_control.router, prefix="/api/forex/mt4-bridge", tags=["mt4-bridge"])
app.include_router(waste_loop_control.router, prefix="/api/forex/waste-loop-control", tags=["waste-loop-control"])
app.include_router(ai_control_authority.router, prefix="/api/forex/ai-control-authority", tags=["ai-control-authority"])
app.include_router(auto_halt.router, prefix="/api/forex/auto-halt", tags=["auto-halt"])
app.include_router(broker_truth_monitor.router, prefix="/api/forex/broker-truth-monitor", tags=["broker-truth-monitor"])
app.include_router(broker_reality.router, prefix="/api/forex/broker-reality", tags=["broker-reality"])
app.include_router(live_pilot.router, prefix="/api/forex/live-pilot", tags=["live-pilot"])
app.include_router(live_recovery.router, prefix="/api/forex/live-recovery", tags=["live-recovery"])
app.include_router(live_money.router, prefix="/api/forex/live-money", tags=["live-money"])
app.include_router(live_order_dry_run.router, prefix="/api/forex/live-order-dry-run", tags=["live-order-dry-run"])
app.include_router(ai_operator.router, prefix="/api/forex/ai-operator", tags=["ai-operator"])
app.include_router(owner_auth.router, prefix="/api/forex/owner-auth", tags=["owner-auth"])
app.include_router(owner_command.router, prefix="/api/forex/owner-command", tags=["owner-command"])


@app.get("/api/forex/dashboard/shell")
async def get_dashboard_shell():
    """Tiny first-paint packet for shell controls while page panels hydrate."""
    if _dashboard_cache_disabled_for_tests():
        packet = await run_in_threadpool(dashboard_shell_state)
        return _with_dashboard_meta(
            packet,
            _dashboard_cache_meta(
                "shell",
                "test_bypass",
                ttl_seconds=_DASHBOARD_SHELL_CACHE_TTL_SECONDS,
            ),
        )

    now = time.time()
    with _dashboard_shell_cache_lock:
        cached = _dashboard_shell_cache["payload"]
        built_at = float(_dashboard_shell_cache["built_at"] or 0.0)
        building = bool(_dashboard_shell_cache["building"])
        error = _dashboard_shell_cache["error"]
        fresh = isinstance(cached, dict) and (now - built_at) <= _DASHBOARD_SHELL_CACHE_TTL_SECONDS

    if fresh and isinstance(cached, dict):
        return _with_dashboard_meta(
            dict(cached),
            _dashboard_cache_meta(
                "shell",
                "fresh",
                built_at,
                ttl_seconds=_DASHBOARD_SHELL_CACHE_TTL_SECONDS,
            ),
        )

    if isinstance(cached, dict):
        if not building:
            _start_dashboard_shell_cache_refresh()
        status = "refreshing_error" if error else "refreshing"
        return _with_dashboard_meta(
            dict(cached),
            _dashboard_cache_meta(
                "shell",
                status,
                built_at,
                ttl_seconds=_DASHBOARD_SHELL_CACHE_TTL_SECONDS,
            ),
        )

    _start_dashboard_shell_cache_refresh()
    packet = _dashboard_shell_warming()
    cache_status = "warming"
    built_at = None
    return _with_dashboard_meta(
        packet,
        _dashboard_cache_meta(
            "shell",
            cache_status,
            built_at,
            ttl_seconds=_DASHBOARD_SHELL_CACHE_TTL_SECONDS,
        ),
    )


@app.get("/api/forex/dashboard/fast")
async def get_dashboard_fast():
    """Small live packet for the shell while the full evidence dashboard warms."""
    if _dashboard_cache_disabled_for_tests():
        packet = await run_in_threadpool(dashboard_fast_state)
        return _with_dashboard_meta(
            packet,
            _dashboard_cache_meta(
                "fast",
                "test_bypass",
                ttl_seconds=_DASHBOARD_FAST_CACHE_TTL_SECONDS,
            ),
        )

    now = time.time()
    with _dashboard_fast_cache_lock:
        cached = _dashboard_fast_cache["payload"]
        built_at = float(_dashboard_fast_cache["built_at"] or 0.0)
        building = bool(_dashboard_fast_cache["building"])
        error = _dashboard_fast_cache["error"]
        fresh = isinstance(cached, dict) and (now - built_at) <= _DASHBOARD_FAST_CACHE_TTL_SECONDS

    if fresh and isinstance(cached, dict):
        return _with_dashboard_meta(
            dict(cached),
            _dashboard_cache_meta(
                "fast",
                "fresh",
                built_at,
                ttl_seconds=_DASHBOARD_FAST_CACHE_TTL_SECONDS,
            ),
        )

    if isinstance(cached, dict):
        if not building:
            _start_dashboard_fast_cache_refresh()
        status = "refreshing_error" if error else "refreshing"
        return _with_dashboard_meta(
            dict(cached),
            _dashboard_cache_meta(
                "fast",
                status,
                built_at,
                ttl_seconds=_DASHBOARD_FAST_CACHE_TTL_SECONDS,
            ),
        )

    _start_dashboard_fast_cache_refresh()
    packet = _dashboard_fast_warming()
    return _with_dashboard_meta(
        packet,
        _dashboard_cache_meta(
            "fast",
            "warming",
            None,
            ttl_seconds=_DASHBOARD_FAST_CACHE_TTL_SECONDS,
        ),
    )


@app.get("/api/forex/dashboard/deep-cache")
async def get_dashboard_deep_cache():
    """Read-only snapshot of startup-warmed deep dashboard packets."""
    return _dashboard_deep_cache_snapshot()


@app.get("/api/forex/dashboard")
async def get_dashboard(refresh: bool = False):
    """Aggregate full dashboard state, served from cache when available."""
    if _dashboard_cache_disabled_for_tests():
        packet = await run_in_threadpool(dashboard_state)
        return _with_dashboard_meta(packet, _dashboard_cache_meta("full", "test_bypass"))

    now = time.time()
    with _dashboard_cache_lock:
        cached = _dashboard_cache["payload"]
        built_at = float(_dashboard_cache["built_at"] or 0.0)
        building = bool(_dashboard_cache["building"])
        error = _dashboard_cache["error"]

    if cached is not None:
        age = now - built_at
        if age <= _DASHBOARD_CACHE_TTL_SECONDS:
            return _with_dashboard_meta(
                _with_live_dashboard_overlays(cached),
                _dashboard_cache_meta("full", "fresh", built_at),
            )
        if refresh and not building:
            _start_dashboard_cache_refresh()
        status = "refreshing" if refresh and not error else "stale"
        if error:
            status = "stale_error"
        return _with_dashboard_meta(
            _with_live_dashboard_overlays(cached),
            _dashboard_cache_meta("full", status, built_at),
        )

    if building:
        return _cached_fast_or_warming_dashboard("full_warming_fast_cache")

    if refresh:
        if os.environ.get("CAS_FOREX_ALLOW_FULL_DASHBOARD_REFRESH") == "1":
            _start_dashboard_cache_refresh()
            return _cached_fast_or_warming_dashboard("full_refreshing_fast_cache")
        return _cached_fast_or_warming_dashboard("full_refresh_disabled")

    return _cached_fast_or_warming_dashboard("cold_fast_cache")


@app.get("/health")
@app.get("/api/forex/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Optional single-container UI serving (cloud deploy). When CAS_FOREX_SERVE_UI=1
# and the built UI exists, mount it at "/" so ONE container serves both the API
# (/api/forex/*) and the cockpit — the phone/desktop hit one URL. Off by default
# so local dev (UI on its own dev server) is unchanged. Mounted LAST so every
# API route and @app.get above take precedence; html=True gives SPA fallback.
# ---------------------------------------------------------------------------
def _mount_ui_if_enabled() -> None:
    if os.environ.get("CAS_FOREX_SERVE_UI") != "1":
        return
    from pathlib import Path as _Path

    from fastapi.staticfiles import StaticFiles

    dist = _Path(os.environ.get("CAS_FOREX_UI_DIST") or (_Path(__file__).resolve().parents[1] / "ui" / "dist"))
    if dist.is_dir() and (dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")


_mount_ui_if_enabled()
