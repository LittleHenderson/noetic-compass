"""HTTP routes for the always-on AI operator + model failover.

``GET /state`` returns the operator scheduler status, the active model provider
(Claude vs free local fallback), the token budget, and recent operator actions.
``POST /start`` `/stop` toggle the always-on loop; ``/run-now`` runs one tick.
``/config`` sets the interval. The ``/model-provider/*`` routes read failover
status, top up the paid token budget, and set the budget.

Boundary: these HTTP routes expose operator status, chat, config, and tick
control. They are not direct broker/provider execution surfaces. Autonomous AI
orders and configured money movement, when owner-armed, must execute through
the separate guarded dispatch/provider paths.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from api.route_cache import (
    cache_first_payload,
    cached_payload_snapshot,
    invalidate_cache,
    start_cache_refresh,
)
from cas_forex.account_chat_truth import (
    asks_active_account_truth,
    compose_active_account_chat_reply,
    project_active_account_chat_truth,
)
from cas_forex.ai_operator_runner import (
    DEFAULT_INTERVAL_SECONDS,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    run_operator_tick_now,
    runner_status,
    runner_status_fast,
    set_desired_runner_state,
    start_runner,
    stop_runner,
)
from cas_forex.model_provider import get_model_provider

router = APIRouter()

OPERATOR_STATE_CACHE_KEY = "ai_operator_state"
OPERATOR_STATE_CACHE_TTL_SECONDS = 5.0
# The browser waits 60 seconds. Keep five seconds for HTTP serialization and UI
# handling while allowing the local 16K-context model enough time to finish a
# grounded answer instead of abandoning an in-flight response at 24 seconds.
OPERATOR_CHAT_RESPONSE_BUDGET_SECONDS = 55.0
OPERATOR_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS = 55.0


def _asks_model_availability(message: str) -> bool:
    low = str(message or "").lower()
    return (
        "neither" in low and any(marker in low for marker in ("respond", "reply"))
    ) or any(
        marker in low
        for marker in (
            "are you responding",
            "are you replying",
            "are you online",
            "can you respond",
            "can you reply",
            "chat working",
            "chat route working",
            "not responding",
            "isn't responding",
            "isnt responding",
            "won't respond",
            "wont respond",
            "no reply",
            "request failed",
            "timed out",
            "model offline",
        )
    )


def _operator_chat_response_budget_seconds() -> float:
    budget = float(OPERATOR_CHAT_RESPONSE_BUDGET_SECONDS)
    try:
        provider_status = get_model_provider().status()
    except Exception:
        return min(budget, OPERATOR_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS)
    remaining = provider_status.get("budget_remaining")
    paid_ready = bool(provider_status.get("active_is_paid")) and not (
        remaining is not None and int(remaining) <= 0
    )
    if paid_ready:
        return budget
    return float(OPERATOR_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS)


def build_operator_state() -> dict[str, Any]:
    return runner_status()


def build_operator_state_shell() -> dict[str, Any]:
    dispatch_runtime = cached_payload_snapshot("dispatch_loop_status", ttl_seconds=5.0)
    return runner_status_fast(dispatch_runtime=dispatch_runtime)


def start_operator_state_cache_refresh() -> bool:
    return start_cache_refresh(
        OPERATOR_STATE_CACHE_KEY,
        build_operator_state,
        delay_seconds=0.2,
        serialize_refresh=False,
    )


class OperatorConfig(BaseModel):
    interval_seconds: int = Field(
        default=DEFAULT_INTERVAL_SECONDS,
        ge=MIN_INTERVAL_SECONDS,
        le=MAX_INTERVAL_SECONDS,
    )


class TopUp(BaseModel):
    tokens: int = Field(ge=0)


class SetKey(BaseModel):
    api_key: str = Field(default="")


class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class GuidanceNote(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class BudgetReset(BaseModel):
    budget_tokens: int = Field(ge=0)


def _asks_position_management(message: str) -> bool:
    normalized = message.lower()
    return any(
        marker in normalized
        for marker in (
            "take profit",
            "bank profit",
            "close the trade",
            "close trade",
            "close position",
            "close a position",
            "closed position",
            "closed a position",
            "partially close",
            "partially closed",
            "partial closing",
            "fully close",
            "fully closed",
            "full close",
            "hold position",
            "hold the position",
            "hold trade",
            "hold the trade",
            "profitable position",
            "winning position",
            "manage position",
            "manage trade",
            "trail stop",
            "trailing stop",
            "break even",
            "breakeven",
            "floating p&l",
            "floating pnl",
        )
    )


def _asks_trade_inactivity(message: str) -> bool:
    """Recognize current-path questions that runtime telemetry can answer exactly."""
    normalized = str(message or "").lower()
    action = any(
        marker in normalized
        for marker in (
            "trade",
            "trading",
            "scalp",
            "entry",
            "enter",
            "open a position",
            "open position",
        )
    )
    diagnostic = any(
        marker in normalized
        for marker in (
            "why",
            "hasn't",
            "hasnt",
            "haven't",
            "havent",
            "don't",
            "dont",
            "didn't",
            "didnt",
            "not trading",
            "no trade",
            "no trades",
            "quiet",
            "stalled",
        )
    )
    return action and diagnostic


def _asks_live_readiness(message: str) -> bool:
    normalized = str(message or "").lower()
    live_scope = any(
        marker in normalized
        for marker in (
            "real money",
            "live money",
            "live trading",
            "trade live",
            "go live",
            "live account",
        )
    )
    readiness = any(
        marker in normalized
        for marker in (
            "ready",
            "authorized",
            "authorised",
            "allowed",
            "can we",
            "can you",
            "blocker",
            "blocking",
            "what gate",
            "which gate",
            "why not",
        )
    )
    return live_scope and readiness


def _fast_chat_fallback(message: str, *, error: str) -> dict[str, Any]:
    from cas_forex.ai_operator import CHAT_CLAIM_BOUNDARY, _profit_and_balance
    from cas_forex.dispatch_loop import loop_status_fast
    from cas_forex.live_candle_route_policy import live_candle_route_runtime_status

    fast_dispatch = loop_status_fast()
    cached_dispatch = cached_payload_snapshot(
        "dispatch_loop_status",
        ttl_seconds=30.0,
    ) or {}
    # The cockpit's rich status cache carries completed-cycle evidence while
    # the lock-free shell carries the newest heartbeat. Merge them so chat and
    # the visible status panel cannot contradict each other after a restart.
    dispatch = dict(cached_dispatch)
    for key, value in fast_dispatch.items():
        if key not in dispatch:
            dispatch[key] = value
    for key in (
        "running",
        "desired_running",
        "execution_active",
        "execution_lane",
        "requested_mode",
        "mode",
        "last_management_status",
        "last_management_detail",
        "last_bridge_class",
        "last_bridge_selection_status",
    ):
        if key in fast_dispatch and fast_dispatch.get(key) is not None:
            dispatch[key] = fast_dispatch.get(key)
    running = bool(dispatch.get("running"))
    lane = str(dispatch.get("execution_lane") or "NONE")
    management = str(dispatch.get("last_management_status") or "not reported")
    embedded_entry_scan = dispatch.get("last_entry_timeframe_scan")
    entry_scan = (
        dict(embedded_entry_scan)
        if isinstance(embedded_entry_scan, dict)
        else {}
    )
    # Aggregate scan evidence is valid only when the same rich dispatch snapshot
    # carries a completed-cycle scan reference. Otherwise a stale disk artifact
    # could overwrite a newer cold-start or test/runtime heartbeat.
    if entry_scan:
        try:
            entry_scan_runtime = live_candle_route_runtime_status()
        except Exception:
            entry_scan_runtime = {}
    else:
        entry_scan_runtime = {}
    scale_in_status = str(dispatch.get("last_scale_in_status") or "not evaluated")
    scale_in_options = int(dispatch.get("last_scale_in_action_count") or 0)
    scale_in_blockers = [
        row
        for row in (dispatch.get("last_scale_in_blockers") or [])
        if isinstance(row, dict)
    ]
    asks_compound = any(
        marker in message.lower()
        for marker in ("compound", "scale in", "scale-in", "add to", "add another")
    )
    asks_position_management = _asks_position_management(message)
    asks_availability = _asks_model_availability(message)
    asks_trade_inactivity = _asks_trade_inactivity(message)
    asks_live_readiness = _asks_live_readiness(message)
    asks_account_truth = asks_active_account_truth(message)
    active_account_chat_truth: dict[str, Any] | None = None
    if asks_live_readiness:
        from cas_forex.broker_truth_monitor import monitor_status
        from cas_forex.runtime_gates import evaluate_live_trading
        from cas_forex.waste_background_worker import (
            overlay_broker_truth_monitor_status,
            use_in_process_workers_for_tests,
        )

        gate = evaluate_live_trading(require_dry_run_review=True).to_dict()
        monitor = monitor_status()
        if not use_in_process_workers_for_tests():
            monitor = overlay_broker_truth_monitor_status(monitor)
        latest = dict(monitor.get("latest_report") or {})
        external_worker = dict(monitor.get("external_worker") or {})
        monitor_running = bool(monitor.get("running") or external_worker.get("running"))
        account = latest.get("mt5_account")
        server = str((latest.get("mt5_account_money_snapshot") or {}).get("server") or "unknown")
        identity_match = latest.get("mt5_account_identity_matches_config")
        account_kind = "DEMO" if latest.get("mt5_is_demo") is True else (
            "LIVE" if latest.get("mt5_is_demo") is False and identity_match is True else
            "WRONG OR UNVERIFIED LIVE ACCOUNT" if latest.get("mt5_is_demo") is False else
            "UNKNOWN"
        )
        missing = [str(value) for value in (gate.get("missing_requirements") or [])]
        satisfied = [str(value) for value in (gate.get("satisfied_requirements") or [])]
        blocker_text = "; ".join(missing) if missing else "none"
        daily_status = str(dispatch.get("last_operator_trade_edge_status") or "")
        daily_detail = str(dispatch.get("last_operator_trade_edge_summary") or "").strip()
        paper_entry_text = ""
        if daily_status == "DAILY_REALIZED_LOSS_CAP_REACHED" and daily_detail:
            paper_entry_text = (
                " Current paper/demo new-entry gate is also closed for this UTC day: "
                f"{daily_detail}"
            )
        reply_text = (
            f"{'Yes' if gate.get('authorized') else 'No'}. Current real-money status="
            f"{gate.get('status') or 'UNKNOWN'}. Connected MT5 account="
            f"{('#' + str(account)) if account else 'unknown'} on {server}, account type="
            f"{account_kind}. Broker-truth monitor running={monitor_running}, cycles="
            f"{monitor.get('cycles_run') or external_worker.get('cycles_run') or 0}, "
            f"latest reconciliation={latest.get('overall_status') or 'unavailable'}. "
            f"Exact authorization blockers: {blocker_text}. Already satisfied: "
            f"{'; '.join(satisfied) if satisfied else 'none reported'}."
            f"{paper_entry_text} Every order must still pass its fresh edge, stop-risk, "
            "margin, exposure, market, broker-permission, and kill-switch checks at "
            "dispatch time. This chat did not place an order or change authority."
        )
        path_status = "LOCAL_LIVE_READINESS_TRUTH"
    elif asks_compound:
        scale_in_truth = (
            " Current compounding feasibility: "
            f"status={scale_in_status}, broker-grid options={scale_in_options}, "
            f"blocked parents={len(scale_in_blockers)}."
        )
        if scale_in_blockers:
            scale_in_truth += " Binding blockers: " + "; ".join(
                f"{row.get('symbol') or 'unknown'} ticket "
                f"{row.get('parent_broker_ticket') or 'unknown'}: "
                f"{row.get('reason') or 'unspecified blocker'}"
                for row in scale_in_blockers[:8]
            ) + "."
        reply_text = (
            "Yes. The Operator has autonomous scale-in authority inside the owner's "
            "limits. It may add to a broker-protected parent only when the position is "
            "fresh and net winning after reported costs, and the exact add passes stop-risk, "
            "margin, exposure, position-count, and broker lot-grid checks. A green floating "
            "P&L alone is not enough. Current runtime: "
            f"dispatch running={running}, lane={lane}, management={management}. "
            f"{scale_in_truth} "
            "This chat did not send an order; the management loop evaluates and dispatches "
            "any qualifying add through the guarded broker path."
        )
        path_status = "LOCAL_COMPOUND_AUTHORITY_TRUTH"
    elif asks_account_truth:
        try:
            from api.data import active_account_truth

            active_account_chat_truth = project_active_account_chat_truth(
                active_account_truth(),
                simulator_evidence=_profit_and_balance(),
            )
            reply_text = compose_active_account_chat_reply(active_account_chat_truth)
        except Exception as exc:
            active_account_chat_truth = project_active_account_chat_truth(None)
            reply_text = (
                "The active execution-account truth could not be collected, so I will "
                "not guess a balance, P&L, realized growth, or position count. "
                f"Diagnostic={type(exc).__name__}. No order ran, no dial changed, and "
                "no money moved from this chat."
            )
        path_status = "LOCAL_ACTIVE_ACCOUNT_TRUTH"
    elif asks_position_management:
        discretion_status = str(
            dispatch.get("last_operator_discretionary_status") or "not evaluated"
        )
        discretion_options = int(
            dispatch.get("last_operator_discretionary_option_count") or 0
        )
        discretion_positions = int(
            dispatch.get("last_operator_discretionary_position_count") or 0
        )
        discretion_blocked = int(
            dispatch.get("last_operator_discretionary_blocked_option_count") or 0
        )
        edge_status = str(
            dispatch.get("last_operator_position_edge_status") or "not evaluated"
        )
        selected = int(
            dispatch.get("last_operator_position_edge_selected_count") or 0
        )
        stood_down = int(
            dispatch.get("last_operator_position_edge_stand_down_count") or 0
        )
        reply_text = (
            "Yes. The Operator has autonomous authority to hold, take profit, close, "
            "partially close, move a stop to breakeven, or trail a stop when the exact "
            "action is available and passes the guarded broker path. It now receives "
            "an exact action menu for every fresh manageable position instead of only "
            "at fixed profit/loss thresholds. Current runtime: "
            f"dispatch running={running}, lane={lane}, management={management}; "
            f"position discretion={discretion_status}, exact options={discretion_options}, "
            f"positions represented={discretion_positions}, blocked options={discretion_blocked}; "
            f"latest position-edge status={edge_status}, selected={selected}, "
            f"stood down={stood_down}. A failed or unavailable model cannot choose an "
            "action; it leaves the position unchanged. This chat did not send an order."
        )
        path_status = "LOCAL_POSITION_MANAGEMENT_TRUTH"
    elif asks_availability:
        provider_status = get_model_provider().status()
        active_provider = str(provider_status.get("active_provider_label") or "unavailable")
        budget_remaining = provider_status.get("budget_remaining")
        budget_exhausted = budget_remaining is not None and int(budget_remaining) <= 0
        paid_ready = bool(provider_status.get("active_is_paid")) and not budget_exhausted
        active_id = str(provider_status.get("active_provider") or "")
        deepseek_selected = active_id.startswith("deepseek-")
        gemma_selected = active_id == "gemma4-backup"
        gemma_configured = bool(
            provider_status.get("gemma4_backup_configured")
        )
        local_selected = bool(active_id) and not bool(provider_status.get("active_is_paid"))
        provider_reachability = str(
            provider_status.get("provider_reachability") or "NOT_PROBED"
        ).upper()
        provider_error = str(provider_status.get("provider_last_error") or "").strip()
        if provider_reachability == "FAILED":
            model_state = (
                "the selected model FAILED its latest real generation request: "
                f"{provider_error or 'provider generation failed'}"
            )
        elif provider_reachability == "STALE":
            model_state = (
                "the selected model's last capability result is stale and must be verified "
                "by the next real request"
            )
        elif provider_reachability == "READY":
            model_state = "the selected model completed its latest generation request successfully"
        elif paid_ready:
            model_state = (
                f"{active_provider} is selected but has not completed a capability request "
                "in this health window"
            )
        elif local_selected:
            model_state = (
                "the free local fallback is selected but has not completed a capability request "
                "in this health window"
            )
        else:
            model_state = "no language-model provider is currently selected"
        reply_text = (
            "The Operator chat route is responding. Current runtime: "
            f"dispatch running={running}, lane={lane}, management={management}. "
            f"Selected model provider={active_provider}; legacy Claude budget "
            f"{'is exhausted' if budget_exhausted else 'is available or not applicable'}; "
            f"DeepSeek role routing={'active' if deepseek_selected else 'not selected'}; "
            f"Gemma 4 backup={'active' if gemma_selected else ('standing by' if gemma_configured else 'not configured')}; "
            f"{model_state}. "
            "Known authority and runtime questions answer locally without waiting for the "
            "model. No command ran, no dial changed, and this chat placed no order."
        )
        path_status = "LOCAL_MODEL_AVAILABILITY_TRUTH"
    elif asks_trade_inactivity:
        timeframe = str(dispatch.get("last_entry_timeframe") or "").strip()
        entry_lane = str(dispatch.get("last_entry_lane") or "").strip()
        targeting_status = str(
            dispatch.get("last_symbol_targeting_status") or "WARMING"
        )
        eligible_count = len(dispatch.get("last_eligible_entry_symbols") or [])
        preflight_status = str(
            dispatch.get("last_entry_risk_feasibility_status") or "not evaluated"
        )
        current_candidates = int(
            dispatch.get("last_entry_risk_candidate_count") or 0
        )
        feasible_candidates = int(
            dispatch.get("last_entry_risk_feasible_count") or 0
        )
        blocked_candidates = int(
            dispatch.get("last_entry_risk_blocked_count") or 0
        )
        operator_candidates = int(
            dispatch.get("last_entry_risk_operator_candidate_count") or 0
        )
        bridge = str(dispatch.get("last_bridge_class") or "not selected")
        bridge_status = str(
            dispatch.get("last_bridge_selection_status") or "not evaluated"
        )
        cycle_telemetry_ready = bool(
            timeframe
            or entry_lane
            or dispatch.get("last_entry_risk_feasibility_status")
            or dispatch.get("last_symbol_targeting_status")
        )
        all_below_floor = bool(
            entry_scan_runtime.get("all_observed_lanes_below_directional_floor")
        )
        current_scan_throttled = (
            str(entry_scan.get("status") or "") == "SCAN_THROTTLED_CACHE"
        )
        if all_below_floor:
            attempts = int(entry_scan_runtime.get("attempt_count") or 0)
            full_lanes = int(entry_scan_runtime.get("full_scan_lane_count") or 0)
            strongest = entry_scan_runtime.get("strongest_rejected_lane")
            strongest = strongest if isinstance(strongest, dict) else {}
            strongest_text = ""
            if strongest:
                strongest_text = (
                    " Strongest rejected lane="
                    f"{strongest.get('symbol') or 'unknown'} "
                    f"{strongest.get('timeframe') or 'unknown'} "
                    f"{strongest.get('direction') or 'unknown'}, score="
                    f"{strongest.get('directional_score')}, floor="
                    f"{strongest.get('directional_floor')}."
                )
            shadow_pass = entry_scan_runtime.get("best_shadow_pass_lane")
            shadow_pass = shadow_pass if isinstance(shadow_pass, dict) else {}
            shadow_text = ""
            if shadow_pass:
                shadow_text = (
                    " Best read-only shadow PASS lane="
                    f"{shadow_pass.get('symbol') or 'unknown'} "
                    f"{shadow_pass.get('timeframe') or 'unknown'} "
                    f"{shadow_pass.get('direction') or 'unknown'}, score="
                    f"{shadow_pass.get('directional_score')}, measured="
                    f"{shadow_pass.get('shadow_measured_win_prob')}, threshold="
                    f"{shadow_pass.get('shadow_threshold')}. This preview minted no "
                    "authorization token and placed no order."
                )
            elif entry_scan_runtime.get("shadow_edge_status_counts"):
                shadow_text = (
                    " Read-only shadow edge results="
                    f"{entry_scan_runtime.get('shadow_edge_status_counts')}; no shadow "
                    "PASS was observed."
                )
            scan_truth = (
                f"The runtime completed {full_lanes} timeframe scans covering "
                f"{attempts} symbol/timeframe attempts, and every observed lane stopped "
                f"below the configured directional floor.{strongest_text}{shadow_text}"
            )
            immediate_reason = (
                "This is pre-Operator candidate starvation, not evidence that the "
                "Operator prudently reviewed and rejected executable trades."
            )
        elif current_scan_throttled:
            remaining = entry_scan.get("cache_remaining_seconds")
            scan_truth = (
                f"The current {timeframe or 'configured'} {entry_lane or 'entry'} "
                "scheduler call was cache-throttled; it reused the latest scan result."
            )
            immediate_reason = (
                "No fresh market scan ran in this scheduler call"
                + (f"; the next rescan was about {remaining} seconds away." if remaining is not None else ".")
            )
        elif not cycle_telemetry_ready:
            scan_truth = (
                "The dispatch loop is running, but its per-cycle scalp telemetry is "
                "still warming after startup."
            )
            immediate_reason = (
                "No current-cycle candidate is reported yet; that is telemetry warm-up, "
                "not an AI stand-down or a permanent no-trade policy."
            )
        elif operator_candidates == 0:
            scan_truth = (
                f"The Operator is scanning the {timeframe or 'configured'} "
                f"{entry_lane or 'entry'} lane; scalp trading is enabled, not disabled."
            )
            immediate_reason = (
                "No entry candidate reached the Operator in the current completed cycle, "
                "so there was nothing to approve or dispatch."
            )
        elif feasible_candidates == 0:
            scan_truth = (
                f"The Operator is scanning the {timeframe or 'configured'} "
                f"{entry_lane or 'entry'} lane; scalp trading is enabled, not disabled."
            )
            immediate_reason = (
                "Candidates formed, but none had a broker-valid risk option for the "
                "Operator to select in the current completed cycle."
            )
        else:
            scan_truth = (
                f"The Operator is scanning the {timeframe or 'configured'} "
                f"{entry_lane or 'entry'} lane; scalp trading is enabled, not disabled."
            )
            immediate_reason = (
                "A candidate reached the Operator; the latest dispatch summary must be "
                "used to distinguish a stand-down from a broker execution."
            )
        reply_text = (
            f"{scan_truth} "
            f"{immediate_reason} Current runtime: dispatch running={running}, lane={lane}, "
            f"management={management}; symbols={targeting_status}, eligible={eligible_count}; "
            f"entry preflight={preflight_status}, candidates={current_candidates}, "
            f"feasible={feasible_candidates}, blocked={blocked_candidates}, "
            f"sent to Operator={operator_candidates}; bridge={bridge}/{bridge_status}. "
            "That is current execution evidence, not a claim that waiting always improves "
            "returns. This chat did not place an order or change a dial."
        )
        path_status = "LOCAL_TRADE_PATH_TRUTH"
    elif error == "operator_chat_response_budget_exceeded":
        reply_text = (
            "I received your message, but the model/context path exceeded its response "
            f"budget. Current runtime: dispatch running={running}, lane={lane}, "
            f"management={management}. No command ran and no dial changed."
        )
        path_status = "MODEL_TIMEOUT_LOCAL_FAST_FALLBACK"
    else:
        reply_text = (
            "I received your message. The primary Operator reply path failed, so this "
            "bounded runtime answer is keeping the conversation alive. Current runtime: "
            f"dispatch running={running}, lane={lane}, management={management}. "
            "No command ran and no dial changed. Send the question again if you need a "
            "model interpretation of the current evidence."
        )
        path_status = "MODEL_ERROR_LOCAL_FAST_FALLBACK"
    local_runtime_truth = path_status in {
        "LOCAL_COMPOUND_AUTHORITY_TRUTH",
        "LOCAL_ACTIVE_ACCOUNT_TRUTH",
        "LOCAL_POSITION_MANAGEMENT_TRUTH",
        "LOCAL_MODEL_AVAILABILITY_TRUTH",
        "LOCAL_TRADE_PATH_TRUTH",
        "LOCAL_LIVE_READINESS_TRUTH",
    }
    # The public error field is a STABLE code the cockpit can match on;
    # OperatorBadge.tsx keys its "backend failed before a reply" rendering off
    # "operator_chat_unavailable". The raw error (exception class, message)
    # stays in `diagnostic` for operators reading the wire. Without this
    # normalisation the UI saw only dynamic strings like
    # "operator_chat_backend_error:TypeError: ..." and could never show the
    # owner its structured failure explanation.
    public_error: str | None
    if local_runtime_truth:
        public_error = None
    elif error.startswith("operator_chat_backend_error"):
        public_error = "operator_chat_unavailable"
    else:
        public_error = error
    return {
        "ok": True,
        "model_ok": False,
        "fallback": True,
        "reply": reply_text,
        "provider": None,
        "provider_label": "Local bounded Operator",
        "paid": False,
        "error": public_error,
        "diagnostic": error,
        # Structured money-impact statement for the cockpit's failure banner.
        # Every fallback branch shares this truth: chat never dispatches.
        "money_impact": "No command ran and no dials changed.",
        "dials_changed": False,
        "proposed_command": None,
        "command_preview": None,
        "claim_boundary": CHAT_CLAIM_BOUNDARY,
        "chat_path_status": path_status,
        "model_attempted": not local_runtime_truth,
        "response_source": (
            "LOCAL_RUNTIME_TRUTH" if local_runtime_truth else "LOCAL_FAST_FALLBACK"
        ),
        "active_account_truth": active_account_chat_truth,
    }


@router.get("/state")
async def get_state() -> dict[str, Any]:
    return await run_in_threadpool(
        lambda: cache_first_payload(
            OPERATOR_STATE_CACHE_KEY,
            builder=build_operator_state,
            fallback=build_operator_state_shell,
            ttl_seconds=OPERATOR_STATE_CACHE_TTL_SECONDS,
            block_on_cold=False,
            serialize_refresh=False,
        )
    )


@router.post("/start")
async def post_start(body: OperatorConfig) -> dict[str, Any]:
    result = start_runner(body.interval_seconds)
    invalidate_cache(OPERATOR_STATE_CACHE_KEY)
    return result


@router.post("/stop")
async def post_stop() -> dict[str, Any]:
    result = stop_runner()
    invalidate_cache(OPERATOR_STATE_CACHE_KEY)
    return result


@router.post("/run-now")
async def post_run_now() -> dict[str, Any]:
    result = await run_in_threadpool(run_operator_tick_now)
    invalidate_cache(OPERATOR_STATE_CACHE_KEY)
    return result


@router.post("/config")
async def post_config(body: OperatorConfig) -> dict[str, Any]:
    # Persist the interval; re-arm only if the owner already had it running.
    status = runner_status_fast()
    if status.get("running"):
        result = start_runner(body.interval_seconds)
    else:
        result = set_desired_runner_state(body.interval_seconds, desired_running=False)
    invalidate_cache(OPERATOR_STATE_CACHE_KEY)
    return result


@router.get("/model-provider/state")
async def get_model_provider_state() -> dict[str, Any]:
    return get_model_provider().status()


@router.post("/model-provider/add-tokens")
async def post_add_tokens(body: TopUp) -> dict[str, Any]:
    return get_model_provider().top_up(body.tokens)


@router.post("/model-provider/reset-budget")
async def post_reset_budget(body: BudgetReset) -> dict[str, Any]:
    return get_model_provider().reset_budget(budget_tokens=body.budget_tokens)


@router.post("/chat")
async def post_chat(body: ChatMessage) -> dict[str, Any]:
    """Talk to the strategy desk. Conversational route only; no direct side effects here."""
    from cas_forex.ai_operator import AIOperator

    asks_compound = any(
        marker in body.message.lower()
        for marker in (
            "compound",
            "scale in",
            "scale-in",
            "add to",
            "add another",
        )
    )
    if (
        asks_compound
        or asks_active_account_truth(body.message)
        or _asks_position_management(body.message)
        or _asks_model_availability(body.message)
        or _asks_trade_inactivity(body.message)
        or _asks_live_readiness(body.message)
    ):
        return _fast_chat_fallback(body.message, error="model_not_needed_for_authority_truth")
    try:
        return await asyncio.wait_for(
            run_in_threadpool(AIOperator().chat, body.message),
            timeout=_operator_chat_response_budget_seconds(),
        )
    except TimeoutError:
        return _fast_chat_fallback(
            body.message,
            error="operator_chat_response_budget_exceeded",
        )
    except Exception as exc:
        # Conversation must fail soft. A constructor, threadpool, or unexpected
        # backend exception must still yield a bounded truthful reply instead of
        # dropping the owner's message as an HTTP 503.
        return _fast_chat_fallback(
            body.message,
            error=f"operator_chat_backend_error:{type(exc).__name__}: {exc}",
        )


@router.get("/guidance")
async def get_guidance() -> dict[str, Any]:
    from cas_forex.operator_guidance import CLAIM_BOUNDARY, list_notes

    return {"report_kind": "cas_forex_operator_guidance", "notes": list_notes(), "claim_boundary": CLAIM_BOUNDARY}


@router.get("/lessons")
async def get_lessons() -> dict[str, Any]:
    """The durable cross-operator lessons journal — what prior operators learned
    from the trades so future operators inherit it."""
    from cas_forex.operator_lessons import CLAIM_BOUNDARY, list_lessons

    return {"report_kind": "cas_forex_operator_lessons", "lessons": list_lessons(), "claim_boundary": CLAIM_BOUNDARY}


@router.post("/guidance")
async def post_guidance(body: GuidanceNote) -> dict[str, Any]:
    """Add a standing owner consideration the operator weighs on every tick."""
    from cas_forex.operator_guidance import add_note, list_notes

    note = add_note(body.text)
    return {"added": note, "notes": list_notes()}


@router.delete("/guidance/{note_id}")
async def delete_guidance(note_id: str) -> dict[str, Any]:
    from cas_forex.operator_guidance import list_notes, remove_note

    removed = remove_note(note_id)
    return {"removed": removed, "notes": list_notes()}


@router.post("/model-provider/set-key")
async def post_set_key(body: SetKey) -> dict[str, Any]:
    """Store (or, with an empty value, clear) the owner's Claude API key in the
    local git-ignored secret store. Takes effect on the next model call — no
    restart. The key is never logged or echoed; the response only confirms
    presence + a masked hint."""
    from cas_forex.operator_secrets import set_secret

    set_secret("primary_api_key", body.api_key.strip() or None)
    # Clear any primary cooldown so the freshly-set key is tried immediately.
    provider = get_model_provider()
    try:
        provider._state["primary_cooldown_until_epoch"] = 0.0  # noqa: SLF001 (same-package owner action)
        provider._save()
    except Exception:
        pass
    return provider.status()


@router.post("/model-provider/set-deepseek-key")
async def post_set_deepseek_key(body: SetKey) -> dict[str, Any]:
    """Store or clear the owner's DeepSeek API key without echoing it.

    A configured key activates Flash for continuous reasoning and Pro for the
    explicitly escalated request kinds. Ollama Cloud transport does not require
    this key; it requires an Ollama sign-in on the API host instead.
    """

    from cas_forex.operator_secrets import set_secret

    set_secret("deepseek_api_key", body.api_key.strip() or None)
    return get_model_provider().status()
