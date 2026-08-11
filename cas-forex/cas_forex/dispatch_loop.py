"""Owner-controlled autonomous dispatch loop.

The dispatch engine existed (``agent_dispatch.run_agent_dispatch_cycle``) but
nothing ran it on a schedule, so even with green gates the bot never acted on its
own — it only fired when the owner hit a button. This module is that missing
scheduler: a background daemon thread that runs the SAME gated cycle every N
seconds.

It calls the exact gated cycle the manual button calls. A requested but
unauthorized LIVE lane does not silence paper/demo learning: the loop uses a
final paper-only config until every live gate authorizes execution. The broker
bridge and execution guard still re-check LIVE authority at action time.

Owner-controlled: the owner starts/stops it and sets the interval from the app.
That desired switch is persisted, so a restarted API can re-arm the owner's
autonomous loop without another command. A single global loop (single-owner
cockpit); session counters reset on restart.
"""

from __future__ import annotations

import json
import hashlib
import os
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.dispatch_loop_supervisor import (
    DEFAULT_AUDIT_PATH as DEFAULT_SUPERVISOR_AUDIT_PATH,
    DEFAULT_LEASE_SECONDS as DEFAULT_SUPERVISOR_LEASE_SECONDS,
    DEFAULT_STATE_PATH as DEFAULT_SUPERVISOR_STATE_PATH,
    DispatchLoopSupervisorConflict,
    DispatchLoopSupervisorStore,
    process_owner_id,
)

# The owner drives — the interval can be anything from 1 second up to a day.
# (Very low intervals hammer the market-data feed + CPU; that's the owner's call,
# surfaced as an honest note in the UI, not blocked.)
MIN_INTERVAL_SECONDS = 1
DEFAULT_INTERVAL_SECONDS = 60
MAX_INTERVAL_SECONDS = 86_400
MT5_DEMO_LEARNING_PERIODIC_SYNC_SECONDS = 900
MT5_DEMO_LEARNING_ERROR_RETRY_SECONDS = 60
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTROL_STATE_PATH = REPO_ROOT / "runtime" / "dispatch-loop-control.json"
DEFAULT_CONTROL_AUDIT_PATH = REPO_ROOT / "runtime" / "dispatch-loop-control-audit.jsonl"
DEFAULT_SIMULATOR_HANDOFF_MANAGEMENT_STATE_PATH = (
    REPO_ROOT / "runtime" / "ai-hedge-management-simulator-handoff-state.json"
)
_CONTROL_STATE_PATH = DEFAULT_CONTROL_STATE_PATH
_CONTROL_AUDIT_PATH = DEFAULT_CONTROL_AUDIT_PATH
_SUPERVISOR_STATE_PATH = DEFAULT_SUPERVISOR_STATE_PATH
_SUPERVISOR_AUDIT_PATH = DEFAULT_SUPERVISOR_AUDIT_PATH


# Session names the owner can target. Overlap-inclusive (a cycle during the
# 12:00-16:00 UTC London/NY overlap counts as BOTH London and New York).
SESSION_NAMES = ("Asian", "London", "New York")
POSITION_SCOPES = ("CAS_ONLY", "ALL_ACCOUNT")


def active_sessions(now: Any = None) -> set[str]:
    """Which trading sessions are active at ``now`` (UTC)."""
    if now is None:
        from cas_forex.time_utils import utc_now

        now = utc_now()
    h = now.hour
    active = set()
    if h < 8 or h >= 21:
        active.add("Asian")
    if 8 <= h < 16:
        active.add("London")
    if 12 <= h < 21:
        active.add("New York")
    return active


class _LoopState:
    def __init__(self) -> None:
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.interval = DEFAULT_INTERVAL_SECONDS
        # Targeting (empty list / None => no restriction = everything).
        self.symbols: list[str] = []
        self.sessions: list[str] = []
        self.position_scope: str = ""
        self.cycles_run = 0
        self.cycles_idle = 0
        self.last_run_iso: str = ""
        self.last_summary: str = ""
        self.last_error: str = ""
        self.started_at_iso: str = ""
        self.last_collected_intent_count = 0
        self.last_filtered_intent_count = 0
        self.entry_dispatch_in_progress = False
        self.last_entry_progress_summary: str = ""
        self.last_available_intent_symbols: list[str] = []
        self.last_filtered_out_symbols: list[str] = []
        self.last_target_warning: str = ""
        self.last_symbol_targeting: dict[str, Any] = {}
        self.last_entry_timeframe_scan: dict[str, Any] = {}
        self.last_entry_risk_feasibility: dict[str, Any] = {}
        self.last_entry_capacity_pressure: dict[str, Any] = {}
        self.last_supervisor_event: str = ""
        self.last_blocking_detail: str = ""
        self.management_cycles_run = 0
        self.last_management_status: str = ""
        self.last_management_detail: str = ""
        self.last_management_draft_action_count = 0
        self.last_management_action_count = 0
        self.last_management_terminal_effect_count = 0
        self.last_management_broker_touched = False
        self.last_operator_discretionary_status: str = ""
        self.last_operator_discretionary_option_count = 0
        self.last_operator_discretionary_position_count = 0
        self.last_operator_discretionary_blocked_option_count = 0
        self.last_operator_discretionary_model_failure_policy: str = ""
        self.last_scale_in_status: str = ""
        self.last_scale_in_action_count = 0
        self.last_scale_in_parent_candidate_count = 0
        self.last_scale_in_blocker_count = 0
        self.last_scale_in_blockers: list[dict[str, Any]] = []
        self.last_scale_in_max_compound_units = 0
        self.last_scale_in_minimum_profit_r: float | None = None
        self.last_management_account_position_count = 0
        self.last_management_excluded_position_count = 0
        self.last_management_primary_position_count = 0
        self.last_management_simulator_handoff_position_count = 0
        self.last_management_sources: list[dict[str, Any]] = []
        self.last_primary_position_tickets: list[str] = []
        self.last_mt5_demo_learning_sync_status: str = ""
        self.last_mt5_demo_learning_sync_at: str = ""
        self.last_mt5_demo_learning_sync_started_at: str = ""
        self.last_mt5_demo_learning_sync_duration_seconds: float | None = None
        self.mt5_demo_learning_sync_in_progress = False
        self.last_mt5_demo_learning_sync_error: str = ""
        self.last_mt5_demo_learning_history_count = 0
        self.last_mt5_demo_learning_bound_trade_count = 0
        self.last_mt5_demo_learning_group_learning_ready: bool | None = None
        self.last_mt5_demo_learning_overall_sample_ready: bool | None = None
        self.last_mt5_demo_learning_ready_group_count = 0
        self.last_mt5_demo_learning_min_samples_per_group = 0
        self.last_operator_trade_edge_report: dict[str, Any] = {}
        self.last_operator_position_edge_report: dict[str, Any] = {}
        self._mt5_learning_bridge_active = False
        self._mt5_learning_position_signature: tuple[str, ...] = ()
        self._mt5_learning_last_attempt_monotonic = 0.0
        self._mt5_learning_last_success_monotonic = 0.0
        self._mt5_learning_sync_pending_after_dispatch = False
        self.last_effective_mode: str = ""
        self.last_execution_lane: str = ""
        self.last_bridge_class: str = ""
        self.last_bridge_selection_status: str = ""
        self.last_bridge_selection_detail: str = ""


_state = _LoopState()
_lock = threading.Lock()


def set_control_state_path_for_testing(path: str | Path) -> None:
    """Redirect durable desired-state writes in tests."""
    global _CONTROL_STATE_PATH, _CONTROL_AUDIT_PATH
    _CONTROL_STATE_PATH = Path(path)
    _CONTROL_AUDIT_PATH = _CONTROL_STATE_PATH.with_name(
        f"{_CONTROL_STATE_PATH.stem}-audit.jsonl"
    )


def reset_control_state_path_for_testing() -> None:
    """Restore the default desired-state path. Tests only."""
    global _CONTROL_STATE_PATH, _CONTROL_AUDIT_PATH
    _CONTROL_STATE_PATH = DEFAULT_CONTROL_STATE_PATH
    _CONTROL_AUDIT_PATH = DEFAULT_CONTROL_AUDIT_PATH


def set_supervisor_state_path_for_testing(path: str | Path, audit_path: str | Path | None = None) -> None:
    """Redirect durable cross-process lease writes in tests."""
    global _SUPERVISOR_STATE_PATH, _SUPERVISOR_AUDIT_PATH
    _SUPERVISOR_STATE_PATH = Path(path)
    _SUPERVISOR_AUDIT_PATH = Path(audit_path) if audit_path is not None else Path(path).with_suffix(".audit.jsonl")


def reset_supervisor_state_path_for_testing() -> None:
    """Restore the default dispatch-loop supervisor path. Tests only."""
    global _SUPERVISOR_STATE_PATH, _SUPERVISOR_AUDIT_PATH
    _SUPERVISOR_STATE_PATH = DEFAULT_SUPERVISOR_STATE_PATH
    _SUPERVISOR_AUDIT_PATH = DEFAULT_SUPERVISOR_AUDIT_PATH


def _persist_enabled() -> bool:
    return "PYTEST_CURRENT_TEST" not in os.environ or _CONTROL_STATE_PATH != DEFAULT_CONTROL_STATE_PATH


def _supervisor_enabled() -> bool:
    return "PYTEST_CURRENT_TEST" not in os.environ or _SUPERVISOR_STATE_PATH != DEFAULT_SUPERVISOR_STATE_PATH


def _lease_seconds_for_interval(interval_seconds: int) -> int:
    return max(DEFAULT_SUPERVISOR_LEASE_SECONDS, int(interval_seconds) * 3)


def _supervisor_store(interval_seconds: int | None = None) -> DispatchLoopSupervisorStore:
    interval = int(interval_seconds or _state.interval or DEFAULT_INTERVAL_SECONDS)
    return DispatchLoopSupervisorStore(
        _SUPERVISOR_STATE_PATH,
        _SUPERVISOR_AUDIT_PATH,
        lease_seconds=_lease_seconds_for_interval(interval),
    )


def _load_control_state() -> dict[str, Any]:
    if not _CONTROL_STATE_PATH.exists():
        return {}
    try:
        payload = json.loads(_CONTROL_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_control_state(
    *,
    desired_running: bool,
    requested_by: str = "owner_dispatch_control",
    change_reason: str = "dispatch loop control updated",
) -> None:
    if not _persist_enabled():
        return
    from cas_forex.time_utils import utc_now

    before = _load_control_state()
    try:
        revision = int(before.get("revision") or 0) + 1
    except (TypeError, ValueError):
        revision = 1
    updated_at = utc_now().isoformat()
    payload = {
        "report_kind": "cas_forex_dispatch_loop_control",
        "revision": revision,
        "updated_at": updated_at,
        "updated_by": str(requested_by or "owner_dispatch_control"),
        "change_reason": str(change_reason or "dispatch loop control updated"),
        "desired_running": bool(desired_running),
        "interval_seconds": int(_state.interval),
        "symbols": list(_state.symbols),
        "sessions": list(_state.sessions),
        "position_scope": _effective_management_position_scope(),
        "mode": _effective_mode(),
        "paper_safe_restore_only": False,
        "standing_authority_restore": True,
        "claim_boundary": (
            "Dispatch loop control records the owner-desired autonomous scheduler "
            "state for API restart recovery. Runtime mode, execution guard, risk, "
            "broker truth, and owner authority are re-evaluated every cycle. This "
            "file alone does not authorize live trading or money movement."
        ),
    }
    hash_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    payload["event_hash"] = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()
    _CONTROL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _CONTROL_STATE_PATH.with_suffix(
        f"{_CONTROL_STATE_PATH.suffix}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(_CONTROL_STATE_PATH)
    audit = {
        "report_kind": "cas_forex_dispatch_loop_control_audit",
        "at": updated_at,
        "revision": revision,
        "updated_by": payload["updated_by"],
        "change_reason": payload["change_reason"],
        "before": before,
        "after": payload,
        "event_hash": payload["event_hash"],
        "claim_boundary": payload["claim_boundary"],
    }
    _CONTROL_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _CONTROL_AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(audit, sort_keys=True, ensure_ascii=False) + "\n")


def _apply_control_state_to_running_loop() -> None:
    """Pick up owner targeting changes written through another API worker."""
    control = _load_control_state()
    if not control:
        return
    if control.get("desired_running") is False:
        _state.stop_event.set()
        return
    try:
        interval = int(control.get("interval_seconds") or _state.interval)
    except (TypeError, ValueError):
        interval = _state.interval
    _state.interval = max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, interval))
    if "symbols" in control:
        symbols = control.get("symbols") or []
        if isinstance(symbols, list):
            _state.symbols = [str(s) for s in symbols]
    if "sessions" in control:
        sessions = control.get("sessions") or []
        if isinstance(sessions, list):
            _state.sessions = [s for s in (str(x) for x in sessions) if s in SESSION_NAMES]
    if control.get("position_scope"):
        _state.position_scope = _normalize_position_scope(control.get("position_scope"))


def _run_management_with_paper_handoff(
    *,
    primary_bridge: Any,
    runtime_config: Any,
    effective_mode: str,
    position_scope: str,
    management_runner: Any,
    simulator_handoff_selector: Any,
) -> dict[str, Any]:
    """Manage the primary bridge plus any pre-MT5 simulator positions.

    New entries continue through ``primary_bridge`` only. The secondary
    simulator pass exists solely so a bridge upgrade cannot orphan positions
    opened by the durable internal paper broker.
    """

    primary = dict(
        management_runner(
            bridge=primary_bridge,
            config=runtime_config,
            position_scope=position_scope,
            execute=True,
        )
        or {}
    )
    primary_count = int(primary.get("account_position_count") or 0)
    reports: list[tuple[str, Any, dict[str, Any], int]] = [
        ("PRIMARY", primary_bridge, primary, primary_count)
    ]

    if effective_mode != "LIVE" and type(primary_bridge).__name__ != "SimulatedBrokerBridge":
        simulator = simulator_handoff_selector(runtime_config)
        try:
            simulator_positions = list(simulator.get_open_positions() or [])
        except Exception as exc:
            raise RuntimeError(
                "Cannot inspect durable simulator positions during MT5 paper handoff: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if simulator_positions:
            handoff = dict(
                management_runner(
                    bridge=simulator,
                    config=runtime_config,
                    position_scope=position_scope,
                    execute=True,
                    state_path=DEFAULT_SIMULATOR_HANDOFF_MANAGEMENT_STATE_PATH,
                )
                or {}
            )
            handoff_count = int(
                handoff.get("account_position_count") or len(simulator_positions)
            )
            reports.append(("SIMULATOR_HANDOFF", simulator, handoff, handoff_count))

    return _combine_management_reports(reports)


def _combine_management_reports(
    reports: list[tuple[str, Any, dict[str, Any], int]],
) -> dict[str, Any]:
    primary = dict(reports[0][2])
    sources: list[dict[str, Any]] = []
    total_positions = 0
    total_excluded = 0
    total_attempted = 0
    total_effects = 0
    broker_touched = False
    details: list[str] = []
    statuses: list[str] = []
    handoff_positions = 0
    operator_position_reports: list[dict[str, Any]] = []
    scale_in_statuses: list[str] = []
    operator_discretionary_statuses: list[str] = []
    operator_discretionary_option_count = 0
    operator_discretionary_position_count = 0
    operator_discretionary_blocked_option_count = 0
    operator_discretionary_model_failure_policies: list[str] = []
    scale_in_action_count = 0
    scale_in_parent_candidate_count = 0
    scale_in_blockers: list[dict[str, Any]] = []
    scale_in_max_compound_units = 0
    scale_in_minimum_profit_r: float | None = None

    for role, bridge, report, fallback_count in reports:
        position_count = int(report.get("account_position_count") or fallback_count or 0)
        excluded_count = int(report.get("excluded_position_count") or 0)
        attempted = int(report.get("attempted_action_count") or 0)
        effects = int(report.get("terminal_effect_count") or 0)
        touched = bool(report.get("broker_touched"))
        status = str(report.get("status") or "UNKNOWN")
        detail = str(report.get("detail") or "")
        bridge_class = type(bridge).__name__
        scale_in_status = str(report.get("scale_in_status") or "")
        operator_discretionary_status = str(
            report.get("operator_discretionary_status") or ""
        )
        operator_discretionary_options = int(
            report.get("operator_discretionary_option_count") or 0
        )
        operator_discretionary_positions = int(
            report.get("operator_discretionary_position_count") or 0
        )
        operator_discretionary_blocked = int(
            report.get("operator_discretionary_blocked_option_count") or 0
        )
        operator_discretionary_failure_policy = str(
            report.get("operator_discretionary_model_failure_policy") or ""
        )
        if operator_discretionary_status:
            operator_discretionary_statuses.append(operator_discretionary_status)
        operator_discretionary_option_count += operator_discretionary_options
        operator_discretionary_position_count += operator_discretionary_positions
        operator_discretionary_blocked_option_count += operator_discretionary_blocked
        if operator_discretionary_failure_policy:
            operator_discretionary_model_failure_policies.append(
                operator_discretionary_failure_policy
            )
        scale_in_actions = int(report.get("scale_in_action_count") or 0)
        scale_in_parents = int(report.get("scale_in_parent_candidate_count") or 0)
        source_scale_in_blockers = [
            {
                **dict(row),
                "role": role,
                "bridge_class": bridge_class,
            }
            for row in (report.get("scale_in_blockers") or [])
            if isinstance(row, Mapping)
        ]
        if scale_in_status:
            scale_in_statuses.append(scale_in_status)
        scale_in_action_count += scale_in_actions
        scale_in_parent_candidate_count += scale_in_parents
        scale_in_blockers.extend(source_scale_in_blockers)
        scale_in_max_compound_units = max(
            scale_in_max_compound_units,
            int(report.get("scale_in_max_compound_units") or 0),
        )
        if scale_in_minimum_profit_r is None and report.get(
            "scale_in_minimum_profit_r"
        ) is not None:
            scale_in_minimum_profit_r = float(report["scale_in_minimum_profit_r"])
        total_positions += position_count
        total_excluded += excluded_count
        total_attempted += attempted
        total_effects += effects
        broker_touched = broker_touched or touched
        statuses.append(status)
        if role == "SIMULATOR_HANDOFF":
            handoff_positions += position_count
        sources.append(
            {
                "role": role,
                "bridge_class": bridge_class,
                "status": status,
                "position_count": position_count,
                "fresh_position_count": int(report.get("fresh_position_count") or 0),
                "stale_position_count": int(report.get("stale_position_count") or 0),
                "position_snapshot_status": report.get("position_snapshot_status"),
                "price_source_status": report.get("price_source_status"),
                "price_source_label": report.get("price_source_label"),
                "quote_attempts": [
                    dict(row)
                    for row in (report.get("quote_attempts") or [])
                    if isinstance(row, Mapping)
                ],
                "handoff_status": report.get("handoff_status"),
                "blocked_action_count": int(report.get("blocked_action_count") or 0),
                "blocked_actions": [
                    dict(row)
                    for row in (report.get("blocked_actions") or [])
                    if isinstance(row, Mapping)
                ],
                "attempted_action_count": attempted,
                "terminal_effect_count": effects,
                "broker_touched": touched,
                "operator_discretionary_status": operator_discretionary_status or None,
                "operator_discretionary_option_count": operator_discretionary_options,
                "operator_discretionary_position_count": operator_discretionary_positions,
                "operator_discretionary_blocked_option_count": operator_discretionary_blocked,
                "operator_discretionary_model_failure_policy": (
                    operator_discretionary_failure_policy or None
                ),
                "scale_in_status": scale_in_status or None,
                "scale_in_action_count": scale_in_actions,
                "scale_in_parent_candidate_count": scale_in_parents,
                "scale_in_blocker_count": len(source_scale_in_blockers),
                "scale_in_blockers": source_scale_in_blockers,
                "operator_position_edge_status": (
                    (report.get("operator_position_edge") or {}).get("status")
                    if isinstance(report.get("operator_position_edge"), Mapping)
                    else None
                ),
            }
        )
        position_edge = report.get("operator_position_edge")
        if isinstance(position_edge, Mapping) and position_edge.get("status"):
            operator_position_reports.append(dict(position_edge))
        if detail:
            label = "primary" if role == "PRIMARY" else "simulator handoff"
            details.append(f"{label} {bridge_class}: {detail}")

    priority = (
        "ACTIONS_EXECUTED",
        "ACTIONS_ATTEMPTED",
        "MANAGEMENT_BLOCKED",
        "ACTIONS_SUPPRESSED",
        "AI_OPERATOR_REVIEW_DEFERRED",
        "AI_OPERATOR_STOOD_DOWN",
        "WATCHING_MARKET_CLOSED",
        "WATCHING_NO_ACTION",
        "WATCHING_NO_BROKER_POSITIONS",
    )
    combined_status = next(
        (candidate for candidate in priority if candidate in statuses),
        statuses[0] if statuses else "UNKNOWN",
    )
    if total_positions > 0 and combined_status == "WATCHING_NO_BROKER_POSITIONS":
        combined_status = "WATCHING_NO_ACTION"
    combined_scale_in_status = (
        "SCALE_IN_OPTIONS_READY"
        if scale_in_action_count > 0
        else (
            "NO_SCALE_IN_CANDIDATE"
            if scale_in_blockers
            else (scale_in_statuses[0] if scale_in_statuses else "")
        )
    )
    combined_operator_discretionary_status = (
        "OPERATOR_DISCRETIONARY_OPTIONS_READY"
        if operator_discretionary_option_count > 0
        else (
            operator_discretionary_statuses[0]
            if operator_discretionary_statuses
            else ""
        )
    )

    primary.update(
        {
            "status": combined_status,
            "detail": " | ".join(details),
            "attempted_action_count": total_attempted,
            "terminal_effect_count": total_effects,
            "broker_touched": broker_touched,
            "account_position_count": total_positions,
            "excluded_position_count": total_excluded,
            "primary_position_count": int(reports[0][3] or 0),
            "simulator_handoff_position_count": handoff_positions,
            "simulator_handoff_active": handoff_positions > 0,
            "management_sources": sources,
            "operator_discretionary_status": (
                combined_operator_discretionary_status or None
            ),
            "operator_discretionary_option_count": (
                operator_discretionary_option_count
            ),
            "operator_discretionary_position_count": (
                operator_discretionary_position_count
            ),
            "operator_discretionary_blocked_option_count": (
                operator_discretionary_blocked_option_count
            ),
            "operator_discretionary_model_failure_policy": (
                operator_discretionary_model_failure_policies[0]
                if operator_discretionary_model_failure_policies
                else None
            ),
            "scale_in_status": combined_scale_in_status or None,
            "scale_in_action_count": scale_in_action_count,
            "scale_in_parent_candidate_count": scale_in_parent_candidate_count,
            "scale_in_blocker_count": len(scale_in_blockers),
            "scale_in_blockers": scale_in_blockers,
            "scale_in_max_compound_units": scale_in_max_compound_units,
            "scale_in_minimum_profit_r": scale_in_minimum_profit_r,
            "operator_position_edge_reports": operator_position_reports,
            "operator_position_edge": (
                operator_position_reports[-1]
                if operator_position_reports
                else dict(primary.get("operator_position_edge") or {})
            ),
        }
    )
    return primary


def resolve_entry_symbol_targeting(
    *,
    ai_symbols: list[str],
    scheduler_symbols: list[str],
    position_symbol_counts: Mapping[str, int],
    max_positions_per_symbol: int,
) -> dict[str, Any]:
    """Resolve one auditable entry universe before market-candidate ranking."""

    from cas_forex.instruments import canonical_symbol

    def canonical(values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            try:
                symbol = canonical_symbol(str(value))
            except Exception:
                symbol = str(value).strip()
            if symbol and symbol not in normalized:
                normalized.append(symbol)
        return normalized

    ai = canonical(ai_symbols)
    scheduler = canonical(scheduler_symbols)
    scheduler_set = set(scheduler)
    effective = [symbol for symbol in ai if not scheduler or symbol in scheduler_set]
    counts = {str(symbol): max(0, int(count or 0)) for symbol, count in position_symbol_counts.items()}
    cap = max(1, int(max_positions_per_symbol or 1))
    saturated = sorted(symbol for symbol in effective if counts.get(symbol, 0) >= cap)
    saturated_set = set(saturated)
    eligible = [symbol for symbol in effective if symbol not in saturated_set]

    if not ai:
        status = "AI_SYMBOL_DIAL_EMPTY"
        detail = "The AI symbol dial contains no markets, so no entry candidate can be formed."
    elif scheduler and not effective:
        status = "NO_SYMBOL_OVERLAP"
        detail = (
            "The scheduler restriction and AI symbol dial have no overlap; no entry "
            "candidate can reach the Operator."
        )
    elif effective and not eligible:
        status = "ALL_EFFECTIVE_SYMBOLS_AT_POSITION_CAP"
        detail = (
            f"Every effective symbol is already at the per-symbol position cap of {cap}; "
            "existing positions remain managed but new-entry scanning is paused for them."
        )
    elif scheduler:
        status = "SCHEDULER_RESTRICTION_ACTIVE"
        detail = (
            f"The scheduler narrows the AI symbol dial to {len(effective)} overlapping "
            f"market(s); {len(eligible)} remain eligible after position-cap checks."
        )
    else:
        status = "ENTRY_SYMBOLS_READY"
        detail = (
            f"The scheduler adds no extra symbol restriction; {len(eligible)} AI-selected "
            "market(s) remain eligible after position-cap checks."
        )

    return {
        "report_kind": "cas_forex_entry_symbol_targeting",
        "status": status,
        "ai_symbols": ai,
        "scheduler_symbols": scheduler,
        "effective_symbols": effective,
        "position_symbol_counts": counts,
        "max_positions_per_symbol": cap,
        "saturated_symbols": saturated,
        "eligible_symbols": eligible,
        "detail": detail,
        "claim_boundary": (
            "Entry-symbol targeting chooses which owner-allowed AI markets are worth "
            "scanning for a new candidate. Saturated symbols remain under autonomous "
            "position management. This prefilter cannot authorize an order, bypass the "
            "Operator, increase a risk cap, enable live trading, or move money."
        ),
    }


def _position_symbol_counts_for_targeting(
    *,
    primary_bridge: Any,
    runtime_config: Any,
    effective_mode: str,
    simulator_handoff_selector: Any,
) -> tuple[dict[str, int], list[str]]:
    from cas_forex.instruments import canonical_symbol

    bridges: list[tuple[str, Any]] = [("PRIMARY", primary_bridge)]
    if effective_mode != "LIVE" and type(primary_bridge).__name__ != "SimulatedBrokerBridge":
        try:
            bridges.append(("SIMULATOR_HANDOFF", simulator_handoff_selector(runtime_config)))
        except Exception as exc:
            return {}, [f"simulator handoff unavailable: {type(exc).__name__}: {exc}"]

    counts: dict[str, int] = {}
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for role, bridge in bridges:
        try:
            positions = list(bridge.get_open_positions() or [])
        except Exception as exc:
            errors.append(f"{role} position read failed: {type(exc).__name__}: {exc}")
            continue
        for index, position in enumerate(positions):
            if isinstance(position, Mapping):
                raw_symbol = position.get("symbol")
                ticket = position.get("ticket") or position.get("position_id") or index
            else:
                raw_symbol = getattr(position, "symbol", None)
                ticket = getattr(position, "ticket", None) or getattr(position, "position_id", None) or index
            if not raw_symbol:
                continue
            try:
                symbol = canonical_symbol(str(raw_symbol))
            except Exception:
                symbol = str(raw_symbol).strip()
            identity = (role, str(ticket), symbol)
            if not symbol or identity in seen:
                continue
            seen.add(identity)
            counts[symbol] = counts.get(symbol, 0) + 1
    return counts, errors


def _entry_symbol_targeting_for_cycle(
    *,
    primary_bridge: Any,
    runtime_config: Any,
    effective_mode: str,
    simulator_handoff_selector: Any,
) -> dict[str, Any]:
    from cas_forex.ai_control_authority import get_authority
    from cas_forex.execution_guard import caps_from_config

    authority = get_authority()
    ai_symbols = [str(value) for value in (authority.control.get("symbols") or [])]
    counts, errors = _position_symbol_counts_for_targeting(
        primary_bridge=primary_bridge,
        runtime_config=runtime_config,
        effective_mode=effective_mode,
        simulator_handoff_selector=simulator_handoff_selector,
    )
    targeting = resolve_entry_symbol_targeting(
        ai_symbols=ai_symbols,
        scheduler_symbols=list(_state.symbols),
        position_symbol_counts=counts,
        max_positions_per_symbol=int(caps_from_config(runtime_config).max_positions_per_symbol),
    )
    if errors:
        targeting["position_read_errors"] = errors
        targeting["detail"] += " Position-count diagnostics: " + "; ".join(errors)
    return targeting


def _maybe_sync_mt5_demo_learning(
    *,
    primary_bridge: Any,
    runtime_config: Any,
    effective_mode: str,
    management: Mapping[str, Any],
    sync_runner: Any,
    run_async: bool = False,
) -> None:
    from cas_forex.time_utils import utc_now

    paper_mt5 = (
        effective_mode != "LIVE"
        and "MT5" in type(primary_bridge).__name__.upper()
    )
    if not paper_mt5:
        _state._mt5_learning_bridge_active = False
        _state._mt5_learning_position_signature = ()
        if not _state.mt5_demo_learning_sync_in_progress:
            _state.last_mt5_demo_learning_sync_status = "WAITING_FOR_MT5_DEMO"
        _state.last_mt5_demo_learning_sync_error = ""
        _state.last_mt5_demo_learning_group_learning_ready = None
        _state.last_mt5_demo_learning_overall_sample_ready = None
        _state.last_mt5_demo_learning_ready_group_count = 0
        _state.last_mt5_demo_learning_min_samples_per_group = 0
        return

    if _state.mt5_demo_learning_sync_in_progress:
        return

    signature = tuple(
        sorted(
            str(value)
            for value in (management.get("position_tickets") or [])
            if value not in (None, "")
        )
    )
    now = time.monotonic()
    bridge_changed = not _state._mt5_learning_bridge_active
    positions_changed = signature != _state._mt5_learning_position_signature
    periodic_due = (
        _state._mt5_learning_last_success_monotonic <= 0
        or now - _state._mt5_learning_last_success_monotonic
        >= MT5_DEMO_LEARNING_PERIODIC_SYNC_SECONDS
    )
    current_utc_day = utc_now().date().isoformat()
    last_sync_utc_day = str(_state.last_mt5_demo_learning_sync_at or "")[:10]
    utc_day_rollover = bool(
        last_sync_utc_day and last_sync_utc_day != current_utc_day
    )
    retry_due = bool(_state.last_mt5_demo_learning_sync_error) and (
        now - _state._mt5_learning_last_attempt_monotonic
        >= MT5_DEMO_LEARNING_ERROR_RETRY_SECONDS
    )
    dispatch_due = _state._mt5_learning_sync_pending_after_dispatch
    if not (
        bridge_changed
        or positions_changed
        or periodic_due
        or retry_due
        or dispatch_due
        or utc_day_rollover
    ):
        return

    _state._mt5_learning_bridge_active = True
    _state._mt5_learning_position_signature = signature
    _state._mt5_learning_last_attempt_monotonic = now
    _state.last_mt5_demo_learning_sync_started_at = utc_now().isoformat()

    def apply_success(report: Mapping[str, Any], *, duration: float) -> None:
        _state._mt5_learning_last_success_monotonic = time.monotonic()
        _state.last_mt5_demo_learning_sync_duration_seconds = round(duration, 3)
        _state.last_mt5_demo_learning_sync_status = str(
            report.get("status") or "MT5_DEMO_LEARNING_SYNCED"
        )
        _state.last_mt5_demo_learning_sync_at = str(report.get("generated_at") or "")
        _state.last_mt5_demo_learning_sync_error = ""
        _state._mt5_learning_sync_pending_after_dispatch = False
        _state.last_mt5_demo_learning_history_count = int(
            report.get("history_record_count") or 0
        )
        _state.last_mt5_demo_learning_bound_trade_count = int(
            report.get("bound_trade_count") or 0
        )
        _state.last_mt5_demo_learning_group_learning_ready = bool(
            report.get("group_learning_ready")
        )
        _state.last_mt5_demo_learning_overall_sample_ready = bool(
            report.get("overall_sample_ready")
        )
        _state.last_mt5_demo_learning_ready_group_count = int(
            report.get("learning_ready_group_count") or 0
        )
        _state.last_mt5_demo_learning_min_samples_per_group = int(
            report.get("min_samples_per_group") or 0
        )

    def apply_error(exc: Exception, *, duration: float) -> None:
        _state.last_mt5_demo_learning_sync_duration_seconds = round(duration, 3)
        _state.last_mt5_demo_learning_sync_status = "MT5_DEMO_LEARNING_SYNC_ERROR"
        _state.last_mt5_demo_learning_sync_error = f"{type(exc).__name__}: {exc}"

    if run_async:
        _state.mt5_demo_learning_sync_in_progress = True

        def worker() -> None:
            started = time.monotonic()
            try:
                report = dict(
                    sync_runner(bridge=primary_bridge, config=runtime_config) or {}
                )
            except Exception as exc:
                with _lock:
                    apply_error(exc, duration=time.monotonic() - started)
                    _state.mt5_demo_learning_sync_in_progress = False
                return
            with _lock:
                apply_success(report, duration=time.monotonic() - started)
                _state.mt5_demo_learning_sync_in_progress = False

        try:
            threading.Thread(
                target=worker,
                name="cas-forex-mt5-learning-sync",
                daemon=True,
            ).start()
        except Exception as exc:
            _state.mt5_demo_learning_sync_in_progress = False
            apply_error(exc, duration=0.0)
        return

    started = time.monotonic()
    try:
        report = dict(sync_runner(bridge=primary_bridge, config=runtime_config) or {})
    except Exception as exc:
        apply_error(exc, duration=time.monotonic() - started)
        return

    apply_success(report, duration=time.monotonic() - started)


def _run(interval: int) -> None:
    from cas_forex.agent_dispatch import (
        collect_route_intents,
        entry_risk_feasibility_status,
        entry_timeframe_scan_status,
        run_agent_dispatch_cycle,
        write_agent_dispatch_cycle_report,
    )
    from cas_forex.time_utils import utc_now
    from cas_forex.ai_hedge_management_cycle import run_ai_hedge_management_cycle
    from cas_forex.mt5_demo_learning_sync import sync_mt5_demo_learning
    from cas_forex.entry_capacity_pressure import record_entry_capacity_observation
    from cas_forex.broker_control import (
        bridge_selection_report,
        select_bridge,
        select_durable_simulator_handoff_bridge,
        select_paper_learning_bridge,
    )

    owner_id = process_owner_id()
    while not _state.stop_event.is_set():
        if _supervisor_enabled():
            _apply_control_state_to_running_loop()
            if _state.stop_event.is_set():
                break
            store = _supervisor_store(_state.interval)
            if store.should_stop(owner_id=owner_id):
                _state.last_supervisor_event = "stop requested by supervisor"
                break
            renewed, supervisor_payload = store.renew(
                owner_id=owner_id,
                interval_seconds=_state.interval,
                mode=_effective_mode(),
            )
            if not renewed:
                _state.last_supervisor_event = "lease lost to another API worker"
                _state.last_error = "dispatch loop lease lost; duplicate worker stopped itself"
                break
            _state.last_supervisor_event = str(
                (supervisor_payload if isinstance(supervisor_payload, dict) else {}).get("status")
                or "LEASE_RENEWED"
            )
        try:
            effective_mode = _effective_mode()
            _state.last_effective_mode = effective_mode
            _state.entry_dispatch_in_progress = False
            if effective_mode == "LIVE_BLOCKED":
                decision = _live_gate_decision()
                missing = list(decision.get("missing_requirements") or [])
                _state.last_execution_lane = "NONE"
                _state.last_bridge_class = ""
                _state.last_bridge_selection_status = ""
                _state.last_bridge_selection_detail = ""
                _state.cycles_idle += 1
                _state.last_run_iso = utc_now().isoformat()
                _state.last_blocking_detail = str(
                    decision.get("next_action")
                    or "Live mode is requested, but the live runtime gates are not ready."
                )
                missing_text = "; ".join(str(item) for item in missing[:4])
                _state.last_summary = (
                    "LIVE requested; execution is armed but blocked before intent collection"
                    + (f". Missing: {missing_text}" if missing_text else ".")
                )
            else:
                runtime_config = _runtime_config_for_mode(effective_mode)
                # Management and entry dispatch share one bridge for this cycle,
                # preserving terminal identity while each action keeps its own
                # execution guard and receipt reconciliation.
                bridge = (
                    select_bridge(runtime_config)
                    if effective_mode == "LIVE"
                    else select_paper_learning_bridge(runtime_config)
                )
                selection = bridge_selection_report(bridge)
                _state.last_execution_lane = _execution_lane(effective_mode)
                _state.last_bridge_class = str(selection.get("bridge_class") or "")
                _state.last_bridge_selection_status = str(selection.get("status") or "")
                _state.last_bridge_selection_detail = str(selection.get("detail") or "")
                management = _run_management_with_paper_handoff(
                    primary_bridge=bridge,
                    runtime_config=runtime_config,
                    effective_mode=effective_mode,
                    position_scope=_effective_management_position_scope(runtime_config),
                    management_runner=run_ai_hedge_management_cycle,
                    simulator_handoff_selector=select_durable_simulator_handoff_bridge,
                )
                _state.management_cycles_run += 1
                _state.last_management_status = str(management.get("status") or "UNKNOWN")
                _state.last_management_detail = str(management.get("detail") or "")
                _state.last_management_draft_action_count = int(
                    management.get("draft_action_count") or 0
                )
                _state.last_management_action_count = int(
                    management.get("attempted_action_count") or 0
                )
                _state.last_management_terminal_effect_count = int(
                    management.get("terminal_effect_count") or 0
                )
                _state.last_management_broker_touched = bool(management.get("broker_touched"))
                _state.last_operator_discretionary_status = str(
                    management.get("operator_discretionary_status") or ""
                )
                _state.last_operator_discretionary_option_count = int(
                    management.get("operator_discretionary_option_count") or 0
                )
                _state.last_operator_discretionary_position_count = int(
                    management.get("operator_discretionary_position_count") or 0
                )
                _state.last_operator_discretionary_blocked_option_count = int(
                    management.get("operator_discretionary_blocked_option_count") or 0
                )
                _state.last_operator_discretionary_model_failure_policy = str(
                    management.get("operator_discretionary_model_failure_policy") or ""
                )
                _state.last_scale_in_status = str(management.get("scale_in_status") or "")
                _state.last_scale_in_action_count = int(
                    management.get("scale_in_action_count") or 0
                )
                _state.last_scale_in_parent_candidate_count = int(
                    management.get("scale_in_parent_candidate_count") or 0
                )
                _state.last_scale_in_blocker_count = int(
                    management.get("scale_in_blocker_count") or 0
                )
                _state.last_scale_in_blockers = [
                    dict(row)
                    for row in (management.get("scale_in_blockers") or [])
                    if isinstance(row, Mapping)
                ]
                _state.last_scale_in_max_compound_units = int(
                    management.get("scale_in_max_compound_units") or 0
                )
                _state.last_scale_in_minimum_profit_r = (
                    float(management["scale_in_minimum_profit_r"])
                    if management.get("scale_in_minimum_profit_r") is not None
                    else None
                )
                _state.last_management_account_position_count = int(
                    management.get("account_position_count") or 0
                )
                _state.last_management_excluded_position_count = int(
                    management.get("excluded_position_count") or 0
                )
                _state.last_management_primary_position_count = int(
                    management.get("primary_position_count") or 0
                )
                _state.last_management_simulator_handoff_position_count = int(
                    management.get("simulator_handoff_position_count") or 0
                )
                _state.last_management_sources = list(management.get("management_sources") or [])
                position_edge = management.get("operator_position_edge")
                if isinstance(position_edge, Mapping) and position_edge.get("status"):
                    _state.last_operator_position_edge_report = dict(position_edge)
                _state.last_primary_position_tickets = [
                    str(value)
                    for value in (management.get("position_tickets") or [])
                    if value not in (None, "")
                ]
                _maybe_sync_mt5_demo_learning(
                    primary_bridge=bridge,
                    runtime_config=runtime_config,
                    effective_mode=effective_mode,
                    management=management,
                    sync_runner=sync_mt5_demo_learning,
                    run_async=True,
                )

                # Session targets constrain new entries, not protection of an
                # already-open position. Management therefore runs first.
                if _state.sessions and not (active_sessions() & set(_state.sessions)):
                    _state.cycles_idle += 1
                    _state.last_run_iso = utc_now().isoformat()
                    _state.last_blocking_detail = ""
                    _state.last_summary = (
                        f"management={_state.last_management_status} "
                        f"effects={_state.last_management_terminal_effect_count}; "
                        f"entries idle outside target sessions {_state.sessions} "
                        f"(active now: {sorted(active_sessions()) or ['none']})"
                    )
                    _state.last_error = ""
                    _state.stop_event.wait(max(MIN_INTERVAL_SECONDS, _state.interval))
                    continue

                # Resolve the AI dial, optional scheduler restriction, and current
                # per-symbol position caps BEFORE market ranking. This prevents a
                # high-scoring but ineligible market from starving every other lane.
                symbol_targeting = _entry_symbol_targeting_for_cycle(
                    primary_bridge=bridge,
                    runtime_config=runtime_config,
                    effective_mode=effective_mode,
                    simulator_handoff_selector=select_durable_simulator_handoff_bridge,
                )
                _state.last_symbol_targeting = dict(symbol_targeting)
                eligible_symbols = list(symbol_targeting.get("eligible_symbols") or [])
                raw_intents = (
                    collect_route_intents(
                        config=runtime_config,
                        allowed_symbols=eligible_symbols,
                    )
                    if eligible_symbols
                    else []
                )
                _state.last_entry_timeframe_scan = (
                    entry_timeframe_scan_status()
                    if eligible_symbols
                    else {
                        "report_kind": "cas_forex_entry_timeframe_scan",
                        "status": "NO_ELIGIBLE_SYMBOLS",
                        "active_timeframes": [],
                        "selected_timeframe": None,
                        "fresh_intent_count": 0,
                    }
                )
                available_symbols = sorted({str(i.symbol) for i in raw_intents if getattr(i, "symbol", None)})
                target_symbols = set(eligible_symbols)
                intents = [i for i in raw_intents if i.symbol in target_symbols]
                filtered_out_symbols = sorted(set(available_symbols) - target_symbols)
                # Publish collection/targeting truth before dispatch or durable
                # evidence work can block. Owner surfaces must distinguish an
                # empty scan from a collected intent filtered by targeting even
                # while the rest of the cycle is still in flight.
                _state.last_collected_intent_count = len(raw_intents)
                _state.last_filtered_intent_count = len(intents)
                _state.last_available_intent_symbols = available_symbols
                _state.last_filtered_out_symbols = filtered_out_symbols
                _state.last_target_warning = ""
                if symbol_targeting.get("status") in {
                    "AI_SYMBOL_DIAL_EMPTY",
                    "NO_SYMBOL_OVERLAP",
                    "ALL_EFFECTIVE_SYMBOLS_AT_POSITION_CAP",
                }:
                    _state.last_target_warning = str(symbol_targeting.get("detail") or "")
                elif raw_intents and not intents:
                    _state.last_target_warning = (
                        "effective entry symbols filtered out every current route intent; "
                        f"current route symbols are {available_symbols}"
                    )
                entry_progress_summary = (
                    f"entry dispatch in progress collected={len(raw_intents)} "
                    f"filtered={len(intents)} targeting={symbol_targeting.get('status')}"
                )
                if _state.last_target_warning:
                    entry_progress_summary += f" warning={_state.last_target_warning}"
                _state.entry_dispatch_in_progress = True
                _state.last_entry_progress_summary = entry_progress_summary
                _state.last_summary = (
                    f"management={_state.last_management_status} "
                    f"effects={_state.last_management_terminal_effect_count}; "
                    f"{entry_progress_summary}"
                )
                cycle = run_agent_dispatch_cycle(
                    intents=intents,
                    bridge=bridge,
                    config=runtime_config,
                    enforce_receipt_gates=True,
                )
                _state.last_entry_risk_feasibility = dict(
                    getattr(cycle, "entry_risk_feasibility_report", None)
                    or entry_risk_feasibility_status()
                    or {}
                )
                try:
                    _state.last_entry_capacity_pressure = dict(
                        record_entry_capacity_observation(
                            _state.last_entry_risk_feasibility,
                            mode=effective_mode,
                        )
                        or {}
                    )
                except Exception as exc:
                    _state.last_entry_capacity_pressure = {
                        "report_kind": "cas_forex_entry_capacity_pressure",
                        "status": "CAPACITY_PRESSURE_EVIDENCE_UNAVAILABLE",
                        "error": f"{type(exc).__name__}: {exc}",
                        "broker_order_touched": False,
                        "orders_placed": False,
                        "money_moved": False,
                    }
                operator_trade_edge = dict(
                    getattr(cycle, "operator_trade_edge_report", None) or {}
                )
                if (
                    int(operator_trade_edge.get("overseer_approved_candidate_count") or 0) > 0
                    and str(operator_trade_edge.get("status") or "")
                    not in {"NO_OVERSEER_APPROVED_CANDIDATES", "NOT_ENABLED"}
                ):
                    _state.last_operator_trade_edge_report = operator_trade_edge
                try:
                    write_agent_dispatch_cycle_report(cycle)
                except Exception:  # artifact write is best-effort; never break the loop
                    pass
                rep = cycle.dispatch_report
                if (
                    effective_mode != "LIVE"
                    and "MT5" in type(bridge).__name__.upper()
                    and int(rep.executed_count or 0) > 0
                ):
                    _state._mt5_learning_sync_pending_after_dispatch = True
                _state.cycles_run += 1
                _state.last_run_iso = utc_now().isoformat()
                _state.entry_dispatch_in_progress = False
                _state.last_entry_progress_summary = (
                    f"entry dispatch complete intents={rep.intent_count} "
                    f"executed={rep.executed_count} blocked={rep.blocked_count} "
                    f"rejected={rep.rejected_count}"
                )
                target = f" eligible_symbols={len(eligible_symbols)}"
                if _state.symbols:
                    target += f" scheduler_symbols={_state.symbols}"
                _state.last_blocking_detail = ""
                _state.last_summary = (
                    f"lane={_state.last_execution_lane} mode={effective_mode} "
                    f"dispatch_mode={rep.mode} intents={rep.intent_count} executed={rep.executed_count} "
                    f"blocked={rep.blocked_count} rejected={rep.rejected_count}{target}; "
                    f"management={_state.last_management_status} "
                    f"attempted={_state.last_management_action_count} "
                    f"effects={_state.last_management_terminal_effect_count} "
                    f"position_discretion={_state.last_operator_discretionary_status or 'unknown'} "
                    f"position_options={_state.last_operator_discretionary_option_count} "
                    f"scale_in={_state.last_scale_in_status or 'unknown'} "
                    f"scale_options={_state.last_scale_in_action_count} "
                    f"scale_blocked={_state.last_scale_in_blocker_count} "
                    f"learning_sync={_state.last_mt5_demo_learning_sync_status or 'unknown'} "
                    f"entry_timeframe={_state.last_entry_timeframe_scan.get('selected_timeframe') or 'none'} "
                    f"entry_lane={_state.last_entry_timeframe_scan.get('entry_lane') or 'none'} "
                    f"entry_risk={_state.last_entry_risk_feasibility.get('status') or 'unknown'} "
                    f"risk_blocked={_state.last_entry_risk_feasibility.get('blocked_count', 0)} "
                    f"operator_candidates={_state.last_entry_risk_feasibility.get('operator_candidate_count', 0)} "
                    f"capacity_pressure={_state.last_entry_capacity_pressure.get('status') or 'unknown'} "
                    f"targeting={symbol_targeting.get('status')} "
                    f"saturated={symbol_targeting.get('saturated_symbols') or []}"
                )
                if operator_trade_edge.get("status") not in {
                    None,
                    "",
                    "NO_OVERSEER_APPROVED_CANDIDATES",
                    "NOT_ENABLED",
                }:
                    _state.last_summary += (
                        f" operator_edge={operator_trade_edge.get('status')}"
                        f" approved={operator_trade_edge.get('operator_approved_count', 0)}"
                        f" stood_down={operator_trade_edge.get('operator_stand_down_count', 0)}"
                    )
                if _state.last_target_warning:
                    _state.last_summary += f" warning={_state.last_target_warning}"
            _state.last_error = ""
        except Exception as exc:  # one bad cycle must never kill the loop thread
            _state.entry_dispatch_in_progress = False
            _state.last_error = f"{type(exc).__name__}: {exc}"
            _state.last_blocking_detail = str(exc)
        # Sleep the CURRENT interval (re-read each cycle so the owner can change it
        # live without restarting), but wake immediately if stop was requested.
        _state.stop_event.wait(max(MIN_INTERVAL_SECONDS, _state.interval))
    if _supervisor_enabled():
        try:
            _supervisor_store(_state.interval).release(owner_id=owner_id)
        except Exception:
            pass


def start_loop(
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    symbols: Optional[list[str]] = None,
    sessions: Optional[list[str]] = None,
    position_scope: Optional[str] = None,
    *,
    persist_desired: bool = True,
    requested_by: str = "owner_dispatch_control",
    change_reason: str = "dispatch loop started or updated",
) -> dict[str, Any]:
    """Start the autonomous dispatch loop if not already running. Idempotent.

    ``interval_seconds``, ``symbols`` (restrict dispatch to these), and
    ``sessions`` (only dispatch during these) all update live — re-calling while
    the loop runs applies the new targeting on the next cycle without a restart.
    Pass ``None`` to leave a field unchanged; pass ``[]`` to clear a restriction.
    """
    from cas_forex.time_utils import utc_now

    with _lock:
        interval = max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, int(interval_seconds)))
        _state.interval = interval
        if symbols is not None:
            _state.symbols = [str(s) for s in symbols]
        if sessions is not None:
            _state.sessions = [s for s in (str(x) for x in sessions) if s in SESSION_NAMES]
        if position_scope is not None:
            _state.position_scope = _normalize_position_scope(position_scope)
        if persist_desired:
            _save_control_state(
                desired_running=True,
                requested_by=requested_by,
                change_reason=change_reason,
            )
        if _state.thread and _state.thread.is_alive():
            return _status_locked()
        if _supervisor_enabled():
            try:
                lease = _supervisor_store(interval).acquire(
                    owner_id=process_owner_id(),
                    interval_seconds=interval,
                    mode=_effective_mode(),
                )
                _state.last_supervisor_event = str(lease.get("status") or "LEASE_ACQUIRED")
                _state.last_error = ""
            except DispatchLoopSupervisorConflict as exc:
                _state.last_supervisor_event = "active in another API worker"
                _state.last_error = str(exc)
                return _status_locked()
        _state.stop_event.clear()
        _state.started_at_iso = utc_now().isoformat()
        _state.thread = threading.Thread(
            target=_run, args=(interval,), name="cas-paper-dispatch-loop", daemon=True
        )
        _state.thread.start()
        return _status_locked()


def stop_loop(
    *,
    persist_desired: bool = True,
    requested_by: str = "owner_dispatch_control",
    change_reason: str = "dispatch loop stopped",
) -> dict[str, Any]:
    """Stop the loop and wait briefly for the current cycle to wind down."""
    with _lock:
        _state.stop_event.set()
        thread = _state.thread
        if persist_desired:
            _save_control_state(
                desired_running=False,
                requested_by=requested_by,
                change_reason=change_reason,
            )
        if _supervisor_enabled():
            try:
                _supervisor_store(_state.interval).request_stop(requested_by=process_owner_id())
                _state.last_supervisor_event = "STOP_REQUESTED"
            except Exception as exc:
                _state.last_supervisor_event = f"stop request failed: {type(exc).__name__}: {exc}"
    if thread and thread.is_alive():
        thread.join(timeout=3.0)
    with _lock:
        _state.thread = None
        return _status_locked()


def _resolved_runtime_config() -> Any:
    from cas_forex.config import config

    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        return apply_live_enable_overrides(config)
    except Exception:
        return config


def _normalize_position_scope(value: Any) -> str:
    scope = str(value or "CAS_ONLY").strip().upper()
    return scope if scope in POSITION_SCOPES else "CAS_ONLY"


def _effective_management_position_scope(runtime_config: Any = None) -> str:
    if _state.position_scope:
        return _normalize_position_scope(_state.position_scope)
    if runtime_config is None:
        runtime_config = _resolved_runtime_config()
    return _normalize_position_scope(
        getattr(runtime_config, "ai_hedge_position_scope", "CAS_ONLY")
    )


def requested_mode() -> str:
    """Return the owner's requested lane after persisted in-app overrides."""

    return "LIVE" if bool(getattr(_resolved_runtime_config(), "live_mode", False)) else "PAPER"


def _paper_lane_available() -> bool:
    return bool(getattr(_resolved_runtime_config(), "paper_trading", False))


def _paper_runtime_config() -> Any:
    """Final paper-only view; downstream owner-override resolution cannot undo it."""

    from cas_forex.live_enable_control import build_final_runtime_config_view

    return build_final_runtime_config_view(
        _resolved_runtime_config(),
        live_mode=False,
        paper_trading=True,
    )


def _runtime_config_for_mode(mode: str) -> Any:
    return _resolved_runtime_config() if mode == "LIVE" else _paper_runtime_config()


def resolve_active_management_runtime() -> dict[str, Any]:
    """Resolve the same bridge/config lane used by the autonomous scheduler.

    Read and manual-management API surfaces use this helper so they cannot
    silently inspect the static simulator while the scheduler is supervising an
    MT5 demo or live account.  The returned ``bridge`` and ``runtime_config`` are
    internal objects; callers must never serialize them directly.
    """

    effective_mode = _effective_mode()
    execution_lane = _execution_lane(effective_mode)
    position_scope = _effective_management_position_scope()
    base = {
        "report_kind": "cas_forex_active_management_runtime",
        "effective_mode": effective_mode,
        "execution_lane": execution_lane,
        "position_scope": position_scope,
        "bridge": None,
        "runtime_config": None,
        "bridge_selection": {},
        "claim_boundary": (
            "This internal resolver selects the scheduler's active management "
            "lane. It does not read positions, call a broker method, authorize an "
            "action, or move money."
        ),
    }
    if effective_mode == "LIVE_BLOCKED":
        return {
            **base,
            "status": "LIVE_BLOCKED",
            "detail": "Live is requested, paper fallback is unavailable, and the live runtime gate is not authorized.",
        }

    try:
        from cas_forex.broker_control import (
            bridge_selection_report,
            select_bridge,
            select_paper_learning_bridge,
        )

        runtime_config = _runtime_config_for_mode(effective_mode)
        bridge = (
            select_bridge(runtime_config)
            if effective_mode == "LIVE"
            else select_paper_learning_bridge(runtime_config)
        )
        selection = bridge_selection_report(bridge)
    except Exception as exc:
        return {
            **base,
            "status": "BRIDGE_UNAVAILABLE",
            "detail": f"Active management bridge resolution failed: {type(exc).__name__}: {exc}",
        }

    return {
        **base,
        "status": "READY",
        "runtime_config": runtime_config,
        "bridge": bridge,
        "bridge_selection": selection,
        "detail": str(selection.get("detail") or "Active scheduler management lane resolved."),
    }


def _execution_lane(mode: str) -> str:
    if mode == "LIVE":
        return "LIVE"
    if mode in {"PAPER", "PAPER_FALLBACK"}:
        return "PAPER"
    return "NONE"


def _live_gate_decision() -> dict[str, Any]:
    if requested_mode() != "LIVE":
        return {
            "capability": "live_trading",
            "authorized": False,
            "status": "NOT_REQUESTED",
            "missing_requirements": [],
            "satisfied_requirements": [],
            "next_action": "",
        }
    try:
        from cas_forex import runtime_gates

        return runtime_gates.evaluate_live_trading(_resolved_runtime_config()).to_dict()
    except Exception as exc:
        return {
            "capability": "live_trading",
            "authorized": False,
            "status": "UNAVAILABLE",
            "missing_requirements": ["live runtime gate decision unavailable"],
            "satisfied_requirements": [],
            "next_action": f"Refresh live runtime gates: {type(exc).__name__}: {exc}",
        }


def _effective_mode() -> str:
    if requested_mode() != "LIVE":
        return "PAPER"
    try:
        if bool(_live_gate_decision().get("authorized")):
            return "LIVE"
    except Exception:  # pragma: no cover - defensive
        return "PAPER_FALLBACK" if _paper_lane_available() else "LIVE_BLOCKED"
    return "PAPER_FALLBACK" if _paper_lane_available() else "LIVE_BLOCKED"


def _status_locked() -> dict[str, Any]:
    local_running = bool(_state.thread and _state.thread.is_alive())
    supervisor = (
        _supervisor_store(_state.interval).build_status(
            owner_id=process_owner_id(),
            local_running=local_running,
        )
        if _supervisor_enabled()
        else None
    )
    active_elsewhere = bool(
        supervisor
        and supervisor.get("active_lease_is_fresh")
        and not supervisor.get("owned_by_this_process")
    )
    running = local_running or active_elsewhere
    control = _load_control_state()
    operator_trade_edge = dict(_state.last_operator_trade_edge_report)
    if not operator_trade_edge:
        try:
            from cas_forex.ai_operator_trade_edge import latest_operator_trade_edge_decision

            operator_trade_edge = latest_operator_trade_edge_decision()
        except Exception:
            operator_trade_edge = {}
    try:
        from cas_forex.ai_operator_trade_edge import PROMPT_VERSION as operator_trade_edge_prompt_version
    except Exception:
        operator_trade_edge_prompt_version = "unavailable"
    operator_position_edge = dict(_state.last_operator_position_edge_report)
    if not operator_position_edge:
        try:
            from cas_forex.ai_operator_position_edge import latest_operator_position_edge_decision

            operator_position_edge = latest_operator_position_edge_decision()
        except Exception:
            operator_position_edge = {}
    try:
        from cas_forex.ai_operator_position_edge import (
            PROMPT_VERSION as operator_position_edge_prompt_version,
        )
    except Exception:
        operator_position_edge_prompt_version = "unavailable"
    local_last_error = _state.last_error or None
    public_last_error = local_last_error
    if (
        active_elsewhere
        and local_last_error
        and "Dispatch loop lease is held" in local_last_error
    ):
        public_last_error = None
    effective_mode = _effective_mode()
    requested = requested_mode()
    live_gate = _live_gate_decision() if requested == "LIVE" else None
    execution_lane = _execution_lane(effective_mode)
    live_authorized = bool(live_gate and live_gate.get("authorized"))
    paper_fallback = effective_mode == "PAPER_FALLBACK"
    execution_active = bool(
        running and effective_mode in {"PAPER", "PAPER_FALLBACK", "LIVE"}
    )
    status = (
        "LIVE_BLOCKED"
        if effective_mode == "LIVE_BLOCKED"
        else ("RUNNING" if running else "STOPPED")
    )
    blocking_detail = (
        (_state.last_blocking_detail or None)
        if effective_mode == "LIVE_BLOCKED" or _state.last_error
        else None
    )
    live_blocking_detail = None
    if requested == "LIVE" and not live_authorized and live_gate:
        missing = [str(item) for item in (live_gate.get("missing_requirements") or [])]
        visible = "; ".join(missing[:4])
        remaining = max(0, len(missing) - 4)
        live_blocking_detail = str(live_gate.get("next_action") or "").strip() or (
            "Live execution pending: "
            + (visible or "runtime gate evidence is incomplete")
            + (f"; plus {remaining} more requirement(s)" if remaining else "")
            + "."
        )
    if blocking_detail is None and effective_mode == "LIVE_BLOCKED" and live_gate:
        blocking_detail = live_blocking_detail
    return {
        "report_kind": "cas_forex_dispatch_loop",
        "status_source": "FULL_DIAGNOSTIC_STATUS",
        "status": status,
        "running": running,
        "execution_active": execution_active,
        "execution_lane": execution_lane,
        "paper_learning_active": bool(execution_active and execution_lane == "PAPER"),
        "paper_fallback_active": bool(execution_active and paper_fallback),
        "paper_fallback_available": _paper_lane_available(),
        "live_execution_active": bool(execution_active and execution_lane == "LIVE"),
        "live_execution_authorized": live_authorized,
        "live_execution_status": (
            "ACTIVE" if execution_lane == "LIVE" and execution_active
            else (str((live_gate or {}).get("status") or "PENDING") if requested == "LIVE" else "NOT_REQUESTED")
        ),
        "local_running": local_running,
        "dispatch_loop_active_elsewhere": active_elsewhere,
        "desired_running": bool(control.get("desired_running", running)),
        "durable_control_state_path": str(_CONTROL_STATE_PATH),
        "durable_control_audit_path": str(_CONTROL_AUDIT_PATH),
        "control_revision": control.get("revision"),
        "control_updated_at": control.get("updated_at"),
        "control_updated_by": control.get("updated_by"),
        "control_change_reason": control.get("change_reason"),
        "control_event_hash": control.get("event_hash"),
        "supervisor": supervisor,
        "last_supervisor_event": _state.last_supervisor_event or None,
        "interval_seconds": _state.interval,
        "symbols": list(_state.symbols),
        "sessions": list(_state.sessions),
        "position_scope": _effective_management_position_scope(),
        "position_scope_label": (
            "CAS-tagged positions only"
            if _effective_management_position_scope() == "CAS_ONLY"
            else "Every open position on the account"
        ),
        "active_sessions": sorted(active_sessions()),
        "cycles_run": _state.cycles_run,
        "cycles_idle": _state.cycles_idle,
        "management_cycles_run": _state.management_cycles_run,
        "last_management_status": _state.last_management_status or None,
        "last_management_detail": _state.last_management_detail or None,
        "last_management_draft_action_count": _state.last_management_draft_action_count,
        "last_management_action_count": _state.last_management_action_count,
        "last_management_terminal_effect_count": _state.last_management_terminal_effect_count,
        "last_management_broker_touched": _state.last_management_broker_touched,
        "last_operator_discretionary_status": (
            _state.last_operator_discretionary_status or None
        ),
        "last_operator_discretionary_option_count": (
            _state.last_operator_discretionary_option_count
        ),
        "last_operator_discretionary_position_count": (
            _state.last_operator_discretionary_position_count
        ),
        "last_operator_discretionary_blocked_option_count": (
            _state.last_operator_discretionary_blocked_option_count
        ),
        "last_operator_discretionary_model_failure_policy": (
            _state.last_operator_discretionary_model_failure_policy or None
        ),
        "last_scale_in_status": _state.last_scale_in_status or None,
        "last_scale_in_action_count": _state.last_scale_in_action_count,
        "last_scale_in_parent_candidate_count": (
            _state.last_scale_in_parent_candidate_count
        ),
        "last_scale_in_blocker_count": _state.last_scale_in_blocker_count,
        "last_scale_in_blockers": list(_state.last_scale_in_blockers),
        "last_scale_in_max_compound_units": _state.last_scale_in_max_compound_units,
        "last_scale_in_minimum_profit_r": _state.last_scale_in_minimum_profit_r,
        "last_management_account_position_count": _state.last_management_account_position_count,
        "last_management_excluded_position_count": _state.last_management_excluded_position_count,
        "last_management_primary_position_count": _state.last_management_primary_position_count,
        "last_management_simulator_handoff_position_count": (
            _state.last_management_simulator_handoff_position_count
        ),
        "last_management_sources": list(_state.last_management_sources),
        "last_primary_position_tickets": list(_state.last_primary_position_tickets),
        "last_mt5_demo_learning_sync_status": (
            _state.last_mt5_demo_learning_sync_status or None
        ),
        "last_mt5_demo_learning_sync_at": _state.last_mt5_demo_learning_sync_at or None,
        "last_mt5_demo_learning_sync_started_at": (
            _state.last_mt5_demo_learning_sync_started_at or None
        ),
        "last_mt5_demo_learning_sync_duration_seconds": (
            _state.last_mt5_demo_learning_sync_duration_seconds
        ),
        "mt5_demo_learning_sync_in_progress": bool(
            _state.mt5_demo_learning_sync_in_progress
        ),
        "last_mt5_demo_learning_sync_error": (
            _state.last_mt5_demo_learning_sync_error or None
        ),
        "last_mt5_demo_learning_history_count": _state.last_mt5_demo_learning_history_count,
        "last_mt5_demo_learning_bound_trade_count": (
            _state.last_mt5_demo_learning_bound_trade_count
        ),
        "last_mt5_demo_learning_group_learning_ready": (
            _state.last_mt5_demo_learning_group_learning_ready
        ),
        "last_mt5_demo_learning_overall_sample_ready": (
            _state.last_mt5_demo_learning_overall_sample_ready
        ),
        "last_mt5_demo_learning_ready_group_count": (
            _state.last_mt5_demo_learning_ready_group_count
        ),
        "last_mt5_demo_learning_min_samples_per_group": (
            _state.last_mt5_demo_learning_min_samples_per_group
        ),
        "last_operator_trade_edge": operator_trade_edge,
        "operator_trade_edge_prompt_version": operator_trade_edge_prompt_version,
        "last_operator_trade_edge_status": operator_trade_edge.get("status"),
        "last_operator_trade_edge_at": operator_trade_edge.get("generated_at"),
        "last_operator_trade_edge_provider": operator_trade_edge.get("provider"),
        "last_operator_trade_edge_summary": operator_trade_edge.get("summary"),
        "last_operator_trade_edge_candidate_count": operator_trade_edge.get(
            "overseer_approved_candidate_count"
        ),
        "last_operator_trade_edge_approved_count": operator_trade_edge.get(
            "operator_approved_count"
        ),
        "last_operator_trade_edge_stand_down_count": operator_trade_edge.get(
            "operator_stand_down_count"
        ),
        "last_operator_position_edge": operator_position_edge,
        "operator_position_edge_prompt_version": operator_position_edge_prompt_version,
        "last_operator_position_edge_status": operator_position_edge.get("status"),
        "last_operator_position_edge_at": operator_position_edge.get("generated_at"),
        "last_operator_position_edge_provider": operator_position_edge.get("provider"),
        "last_operator_position_edge_summary": operator_position_edge.get("summary"),
        "last_operator_position_edge_candidate_count": operator_position_edge.get(
            "action_candidate_count"
        ),
        "last_operator_position_edge_selected_count": operator_position_edge.get(
            "selected_action_count"
        ),
        "last_operator_position_edge_stand_down_count": operator_position_edge.get(
            "operator_stand_down_count"
        ),
        "last_operator_position_edge_hard_policy_count": operator_position_edge.get(
            "hard_policy_selected_count"
        ),
        "last_run_iso": _state.last_run_iso or None,
        "last_summary": _state.last_summary or None,
        "last_error": public_last_error,
        "last_local_error": local_last_error,
        "started_at_iso": _state.started_at_iso or None,
        "last_collected_intent_count": _state.last_collected_intent_count,
        "last_filtered_intent_count": _state.last_filtered_intent_count,
        "entry_dispatch_in_progress": _state.entry_dispatch_in_progress,
        "last_entry_progress_summary": _state.last_entry_progress_summary or None,
        "last_available_intent_symbols": list(_state.last_available_intent_symbols),
        "last_filtered_out_symbols": list(_state.last_filtered_out_symbols),
        "last_symbol_targeting": dict(_state.last_symbol_targeting),
        "last_entry_timeframe_scan": dict(_state.last_entry_timeframe_scan),
        "last_entry_risk_feasibility": dict(_state.last_entry_risk_feasibility),
        "last_entry_capacity_pressure": dict(_state.last_entry_capacity_pressure),
        "last_entry_capacity_pressure_status": _state.last_entry_capacity_pressure.get(
            "status"
        ),
        "last_entry_risk_feasibility_status": _state.last_entry_risk_feasibility.get(
            "status"
        ),
        "last_entry_risk_candidate_count": _state.last_entry_risk_feasibility.get(
            "candidate_count"
        ),
        "last_entry_risk_feasible_count": _state.last_entry_risk_feasibility.get(
            "feasible_count"
        ),
        "last_entry_risk_blocked_count": _state.last_entry_risk_feasibility.get(
            "blocked_count"
        ),
        "last_entry_risk_unknown_count": _state.last_entry_risk_feasibility.get(
            "unknown_count"
        ),
        "last_entry_risk_operator_candidate_count": _state.last_entry_risk_feasibility.get(
            "operator_candidate_count"
        ),
        "active_entry_timeframes": list(
            _state.last_entry_timeframe_scan.get("active_timeframes") or []
        ),
        "last_entry_timeframe": _state.last_entry_timeframe_scan.get(
            "selected_timeframe"
        ),
        "last_entry_lane": _state.last_entry_timeframe_scan.get("entry_lane"),
        "last_symbol_targeting_status": _state.last_symbol_targeting.get("status"),
        "last_effective_entry_symbols": list(
            _state.last_symbol_targeting.get("effective_symbols") or []
        ),
        "last_eligible_entry_symbols": list(
            _state.last_symbol_targeting.get("eligible_symbols") or []
        ),
        "last_saturated_entry_symbols": list(
            _state.last_symbol_targeting.get("saturated_symbols") or []
        ),
        "last_target_warning": _state.last_target_warning or None,
        "last_blocking_detail": blocking_detail,
        "live_blocking_detail": live_blocking_detail,
        "last_execution_lane": _state.last_execution_lane or None,
        "last_bridge_class": _state.last_bridge_class or None,
        "last_bridge_selection_status": _state.last_bridge_selection_status or None,
        "last_bridge_selection_detail": _state.last_bridge_selection_detail or None,
        "requested_mode": requested,
        "mode": effective_mode,
        "live_gate_decision": live_gate,
        "note": (
            "Runs guarded AI position management and the same gated entry-dispatch "
            "cycle as the manual button on a timer. Existing-position management "
            "continues outside entry-target sessions. "
            "CAS_ONLY manages CAS-tagged positions; ALL_ACCOUNT deliberately "
            "extends autonomous management to every open account position. "
            "PAPER executes only in the paper lane. PAPER_FALLBACK means LIVE is "
            "requested but not authorized, so autonomous paper learning continues "
            "through a final paper-only config. LIVE_BLOCKED occurs only when LIVE "
            "is pending and no paper lane is enabled. LIVE means the armed live lane is active. "
            "An empty scheduler symbol list adds no restriction beyond the owner-fenced "
            "AI symbol dial. Entry scanning removes markets already at the per-symbol "
            "position cap; their existing positions remain managed. Empty sessions means "
            "no session restriction."
        ),
    }


def loop_status_fast() -> dict[str, Any]:
    """Return truthful scheduler telemetry without waiting on the loop lock.

    The rich status builder intentionally resolves supervisor, Operator, runtime
    gate, and durable evidence. During startup or a slow evidence read that work
    may hold ``_lock``. This shell reads only small in-memory scheduler fields
    plus the durable owner control file, so polling cannot misreport a live
    thread as stopped merely because rich diagnostics are still refreshing.
    """

    thread = _state.thread
    local_running = bool(thread and thread.is_alive())
    control = _load_control_state()
    desired_running = bool(control.get("desired_running", local_running))
    effective_mode = str(_state.last_effective_mode or "").upper()
    execution_lane = str(_state.last_execution_lane or "NONE").upper()
    if not effective_mode:
        effective_mode = (
            "LIVE" if execution_lane == "LIVE"
            else ("PAPER" if execution_lane == "PAPER" else "STARTING")
        )
    execution_active = bool(
        local_running
        and execution_lane in {"PAPER", "LIVE"}
        and effective_mode != "LIVE_BLOCKED"
    )
    if effective_mode == "LIVE_BLOCKED":
        status = "LIVE_BLOCKED"
    elif local_running and execution_lane == "NONE":
        status = "STARTING"
    elif local_running:
        status = "RUNNING"
    elif desired_running:
        status = "RESTORE_PENDING"
    else:
        status = "STOPPED"

    position_scope = _normalize_position_scope(
        _state.position_scope or control.get("position_scope") or "CAS_ONLY"
    )
    requested = (
        "LIVE"
        if effective_mode in {"LIVE", "LIVE_BLOCKED", "PAPER_FALLBACK"}
        else ("PAPER" if effective_mode == "PAPER" else "UNKNOWN")
    )
    return {
        "report_kind": "cas_forex_dispatch_loop",
        "status_source": "FAST_IN_MEMORY_SHELL",
        "diagnostic_evidence_status": "BACKGROUND_REFRESH_PENDING",
        "status": status,
        "running": local_running,
        "local_running": local_running,
        "dispatch_loop_active_elsewhere": False,
        "execution_active": execution_active,
        "execution_lane": execution_lane,
        "paper_learning_active": bool(execution_active and execution_lane == "PAPER"),
        "paper_fallback_active": bool(
            execution_active and effective_mode == "PAPER_FALLBACK"
        ),
        "live_execution_active": bool(execution_active and execution_lane == "LIVE"),
        "desired_running": desired_running,
        "durable_control_state_path": str(_CONTROL_STATE_PATH),
        "durable_control_audit_path": str(_CONTROL_AUDIT_PATH),
        "control_revision": control.get("revision"),
        "control_updated_at": control.get("updated_at"),
        "control_updated_by": control.get("updated_by"),
        "control_change_reason": control.get("change_reason"),
        "control_event_hash": control.get("event_hash"),
        "interval_seconds": int(_state.interval),
        "symbols": list(_state.symbols),
        "sessions": list(_state.sessions),
        "position_scope": position_scope,
        "position_scope_label": (
            "CAS-tagged positions only"
            if position_scope == "CAS_ONLY"
            else "Every open position on the account"
        ),
        "active_sessions": sorted(active_sessions()),
        "cycles_run": int(_state.cycles_run),
        "cycles_idle": int(_state.cycles_idle),
        "management_cycles_run": int(_state.management_cycles_run),
        "last_management_status": _state.last_management_status or None,
        "last_management_detail": _state.last_management_detail or None,
        "last_management_draft_action_count": int(
            _state.last_management_draft_action_count
        ),
        "last_management_action_count": int(_state.last_management_action_count),
        "last_management_terminal_effect_count": int(
            _state.last_management_terminal_effect_count
        ),
        "last_management_broker_touched": bool(_state.last_management_broker_touched),
        "last_operator_discretionary_status": (
            _state.last_operator_discretionary_status or None
        ),
        "last_operator_discretionary_option_count": int(
            _state.last_operator_discretionary_option_count
        ),
        "last_operator_discretionary_position_count": int(
            _state.last_operator_discretionary_position_count
        ),
        "last_operator_discretionary_blocked_option_count": int(
            _state.last_operator_discretionary_blocked_option_count
        ),
        "last_operator_discretionary_model_failure_policy": (
            _state.last_operator_discretionary_model_failure_policy or None
        ),
        "last_scale_in_status": _state.last_scale_in_status or None,
        "last_scale_in_action_count": int(_state.last_scale_in_action_count),
        "last_scale_in_parent_candidate_count": int(
            _state.last_scale_in_parent_candidate_count
        ),
        "last_scale_in_blocker_count": int(_state.last_scale_in_blocker_count),
        "last_scale_in_blockers": list(_state.last_scale_in_blockers),
        "last_scale_in_max_compound_units": int(
            _state.last_scale_in_max_compound_units
        ),
        "last_scale_in_minimum_profit_r": _state.last_scale_in_minimum_profit_r,
        "last_management_account_position_count": int(
            _state.last_management_account_position_count
        ),
        "last_mt5_demo_learning_sync_status": (
            _state.last_mt5_demo_learning_sync_status or None
        ),
        "last_mt5_demo_learning_sync_at": _state.last_mt5_demo_learning_sync_at or None,
        "last_mt5_demo_learning_sync_started_at": (
            _state.last_mt5_demo_learning_sync_started_at or None
        ),
        "last_mt5_demo_learning_sync_duration_seconds": (
            _state.last_mt5_demo_learning_sync_duration_seconds
        ),
        "mt5_demo_learning_sync_in_progress": bool(
            _state.mt5_demo_learning_sync_in_progress
        ),
        "last_mt5_demo_learning_sync_error": (
            _state.last_mt5_demo_learning_sync_error or None
        ),
        "last_collected_intent_count": int(_state.last_collected_intent_count),
        "last_filtered_intent_count": int(_state.last_filtered_intent_count),
        "entry_dispatch_in_progress": bool(_state.entry_dispatch_in_progress),
        "last_entry_progress_summary": _state.last_entry_progress_summary or None,
        "last_entry_risk_candidate_count": int(
            _state.last_entry_risk_feasibility.get("candidate_count") or 0
        ),
        "last_entry_risk_operator_candidate_count": int(
            _state.last_entry_risk_feasibility.get("operator_candidate_count") or 0
        ),
        "last_entry_capacity_pressure": dict(_state.last_entry_capacity_pressure),
        "last_entry_capacity_pressure_status": _state.last_entry_capacity_pressure.get(
            "status"
        ),
        "active_entry_timeframes": list(
            _state.last_entry_timeframe_scan.get("active_timeframes") or []
        ),
        "last_entry_timeframe": _state.last_entry_timeframe_scan.get(
            "selected_timeframe"
        ),
        "last_entry_lane": _state.last_entry_timeframe_scan.get("entry_lane"),
        "last_run_iso": _state.last_run_iso or None,
        "last_summary": _state.last_summary or (
            "Dispatch loop thread is starting; rich diagnostics are refreshing."
            if local_running
            else "Dispatch loop is not running in this API process."
        ),
        "last_error": _state.last_error or None,
        "last_local_error": _state.last_error or None,
        "last_blocking_detail": _state.last_blocking_detail or None,
        "last_supervisor_event": _state.last_supervisor_event or None,
        "started_at_iso": _state.started_at_iso or None,
        "last_execution_lane": _state.last_execution_lane or None,
        "last_bridge_class": _state.last_bridge_class or None,
        "last_bridge_selection_status": _state.last_bridge_selection_status or None,
        "last_bridge_selection_detail": _state.last_bridge_selection_detail or None,
        "requested_mode": requested,
        "mode": effective_mode,
        "note": (
            "Fast observational scheduler shell. It reports local thread and last-cycle "
            "truth while rich Operator, supervisor, and runtime-gate evidence refreshes "
            "in the background. It does not authorize or dispatch an order."
        ),
    }


def loop_status() -> dict[str, Any]:
    """Current loop status (running, interval, cycles run, last result, mode)."""
    with _lock:
        return _status_locked()


def restore_desired_loop() -> dict[str, Any]:
    """Re-arm the owner-desired autonomous loop after an API restart."""
    desired = _load_control_state()
    if not desired.get("desired_running"):
        status = loop_status()
        status["restore_status"] = "NO_RESTORE_DESIRED"
        return status
    if _effective_mode() == "LIVE_BLOCKED":
        status = loop_status()
        status["restore_status"] = "RESTORE_BLOCKED_LIVE_CONFIRM_REQUIRED"
        status["restore_detail"] = (
            "Dispatch loop desired state exists, but LIVE is pending and the "
            "paper lane is disabled. Enable paper trading or complete LIVE gates."
        )
        return status
    status = start_loop(
        int(desired.get("interval_seconds") or DEFAULT_INTERVAL_SECONDS),
        symbols=list(desired.get("symbols") or []),
        sessions=list(desired.get("sessions") or []),
        position_scope=str(desired.get("position_scope") or "CAS_ONLY"),
        persist_desired=False,
    )
    if status.get("local_running"):
        if status.get("mode") == "PAPER_FALLBACK":
            status["restore_status"] = "RESTORED_DESIRED_PAPER_FALLBACK_LOOP"
        elif status.get("mode") == "PAPER":
            status["restore_status"] = "RESTORED_DESIRED_PAPER_LOOP"
        else:
            status["restore_status"] = "RESTORED_DESIRED_LIVE_LOOP"
    else:
        status["restore_status"] = "RESTORE_ALREADY_ACTIVE_ELSEWHERE"
    return status
