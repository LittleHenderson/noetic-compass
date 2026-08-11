"""Single-call operator briefing for the CAS Forex LLM cockpit bot.

The autonomous-loop cockpit already exposes a half-dozen narrow status
endpoints (loop health, latest decision explainer, live telemetry, MT5
probe, live readiness). Today the LLM bot chains 3-5 of those calls to
answer "what's going on right now?" — expensive and fragile.

This module composes those existing dicts into one structured
:class:`OperatorBriefing` snapshot the bot can fetch and surface
verbatim. It is purely OBSERVATIONAL — it reports what the system did
and where it stands. It NEVER advises the operator about trades.

Design contract:

* :func:`compose_operator_briefing` is a *pure* function. It does not
  touch the filesystem. Callers pass in already-parsed dicts (any may
  be ``None``); missing inputs are reported as missing, never
  fabricated.
* The ``plain_english_briefing`` never contains advisory phrases:
  "buy now", "should you trade", "good entry", "place a trade",
  "what should i do", "you should sell", "now is the time" — these
  are explicitly tested.
* A small helper :func:`load_operator_briefing_inputs` is provided
  for production callers that need to read the latest evidence from
  disk; tests should construct dicts directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional


__all__ = [
    "OperatorBriefing",
    "compose_operator_briefing",
    "load_operator_briefing_inputs",
]


_LOOP_STATUS_VALUES = {"running", "stalled", "never_started", "unknown"}


@dataclass(frozen=True)
class OperatorBriefing:
    """Structured single-call snapshot for the operator cockpit bot.

    Every field is observational. ``plain_english_briefing`` is a
    3-5 sentence template the LLM bot can surface verbatim; it never
    advises a future trade.
    """

    generated_at_iso: str
    loop_health_status: str
    cycles_today: int
    decisions_today: int
    executions_today: int
    blocked_today: int
    latest_decision_summary: Optional[str]
    latest_decision_cycle_id: Optional[str]
    latest_decision_overall_status: Optional[str]
    open_position_count: int
    total_floating_pnl: float
    live_telemetry_source: str
    live_telemetry_stale: bool
    live_telemetry_last_update_iso: Optional[str]
    live_price_source_status: Optional[str]
    live_position_feed_label: str
    live_position_feed_detail: str
    live_movement_source_truth: dict[str, Any] | None
    mt5_terminal_connected: bool
    mt5_broker_api_verified: bool
    readiness_gates_open: int
    readiness_gates_total: int
    public_launch_gate_status: str
    public_launch_status: str
    live_money_production_status: str
    public_launch_gate_pass_count: int
    public_launch_gate_block_count: int
    public_launch_gate_blockers: tuple[str, ...]
    broker_truth_monitor_status: str
    broker_truth_ready_for_live: bool
    broker_truth_paper_force_latched: bool
    broker_truth_halt_reason_ids: tuple[str, ...]
    broker_truth_halt_reason_labels: tuple[str, ...]
    broker_truth_halt_reason_summary: str
    broker_truth_position_protection_status: str
    broker_truth_position_protection_label: str
    broker_truth_unprotected_position_count: int
    broker_truth_position_protection_detail: Optional[str]
    broker_truth_mt5_connected: Optional[bool]
    broker_truth_mt5_is_demo: Optional[bool]
    broker_truth_open_position_count: int
    autowake_present: bool
    autowake_next_due_iso: Optional[str]
    plain_english_briefing: str
    diagnostic_hints: tuple[str, ...]


# ---------------------------------------------------------------------------
# Public composer
# ---------------------------------------------------------------------------


def compose_operator_briefing(
    *,
    loop_health: Optional[Mapping[str, Any]] = None,
    latest_decision: Optional[Mapping[str, Any]] = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    mt5_probe: Optional[Mapping[str, Any]] = None,
    readiness: Optional[Mapping[str, Any]] = None,
    public_launch_gate: Optional[Mapping[str, Any]] = None,
    broker_truth_monitor: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
) -> OperatorBriefing:
    """Compose a structured operator briefing from already-parsed inputs.

    Any missing input → corresponding fields land on safe defaults
    (None / 0 / False). The function NEVER fabricates a count, status,
    or timestamp.
    """

    now_utc = _coerce_now(now)
    generated_at_iso = now_utc.isoformat()

    # ---- loop health
    loop_status, cycles_today, decisions_today, executions_today, blocked_today, \
        autowake_present, autowake_next_due_iso, loop_hints = _extract_loop_health(
            loop_health
        )

    # ---- latest decision
    latest_summary, latest_cycle_id, latest_overall_status = _extract_latest_decision(
        latest_decision
    )

    # ---- live telemetry
    (
        open_position_count,
        total_floating_pnl,
        live_telemetry_source,
        live_telemetry_stale,
        live_telemetry_last_update_iso,
        live_price_source_status,
        live_position_feed_label,
        live_position_feed_detail,
        live_movement_source_truth,
    ) = _extract_live_telemetry(live_telemetry)

    # ---- MT5 probe
    mt5_terminal_connected, mt5_broker_api_verified = _extract_mt5_probe(mt5_probe)

    # ---- readiness gates
    gates_open, gates_total, readiness_hints = _extract_readiness(readiness)

    # ---- public/live-production launch gate
    launch_status, public_status, live_prod_status, launch_pass_count, launch_block_count, launch_blockers = (
        _extract_public_launch_gate(public_launch_gate)
    )

    # ---- broker-truth monitor / continuous fail-closed state
    (
        broker_truth_monitor_status,
        broker_truth_ready_for_live,
        broker_truth_paper_force_latched,
        broker_truth_halt_reason_ids,
        broker_truth_halt_reason_labels,
        broker_truth_halt_reason_summary,
        broker_truth_position_protection_status,
        broker_truth_position_protection_label,
        broker_truth_unprotected_position_count,
        broker_truth_position_protection_detail,
        broker_truth_mt5_connected,
        broker_truth_mt5_is_demo,
        broker_truth_open_position_count,
        broker_truth_hints,
    ) = _extract_broker_truth_monitor(broker_truth_monitor)

    current_mt5_truth = _fresh_mt5_broker_truth_fields(
        live_telemetry=live_telemetry,
        source=live_telemetry_source,
        stale=live_telemetry_stale,
        count=open_position_count,
        movement_truth=live_movement_source_truth,
    )
    if current_mt5_truth:
        mt5_terminal_connected = True
        mt5_broker_api_verified = True
        broker_truth_mt5_connected = True
        broker_truth_mt5_is_demo = current_mt5_truth["is_demo"]
        broker_truth_open_position_count = current_mt5_truth["open_position_count"]
        if current_mt5_truth.get("position_protection_status"):
            broker_truth_position_protection_status = str(
                current_mt5_truth["position_protection_status"]
            )
            broker_truth_position_protection_label = _position_protection_label(
                broker_truth_position_protection_status
            )
            broker_truth_unprotected_position_count = _safe_int(
                current_mt5_truth.get("unprotected_position_count")
            )
            broker_truth_position_protection_detail = current_mt5_truth.get(
                "position_protection_detail"
            )

    # ---- diagnostic hints (loop + readiness, capped at 5)
    diagnostic_hints = _merge_hints(loop_hints, readiness_hints, broker_truth_hints, launch_blockers, limit=5)

    # ---- plain-English briefing
    plain_english_briefing = _build_plain_english_briefing(
        loop_status=loop_status,
        cycles_today=cycles_today,
        latest_summary=latest_summary,
        open_position_count=open_position_count,
        total_floating_pnl=total_floating_pnl,
        live_telemetry_source=live_telemetry_source,
        live_telemetry_stale=live_telemetry_stale,
        live_telemetry_last_update_iso=live_telemetry_last_update_iso,
        live_price_source_status=live_price_source_status,
        mt5_terminal_connected=mt5_terminal_connected,
        gates_open=gates_open,
        gates_total=gates_total,
        public_launch_gate_status=launch_status,
        public_launch_status=public_status,
        live_money_production_status=live_prod_status,
        public_launch_gate_block_count=launch_block_count,
        broker_truth_monitor_status=broker_truth_monitor_status,
        broker_truth_ready_for_live=broker_truth_ready_for_live,
        broker_truth_paper_force_latched=broker_truth_paper_force_latched,
        broker_truth_halt_reason_summary=broker_truth_halt_reason_summary,
        broker_truth_position_protection_label=broker_truth_position_protection_label,
        broker_truth_unprotected_position_count=broker_truth_unprotected_position_count,
        diagnostic_hints=diagnostic_hints,
        autowake_next_due_iso=autowake_next_due_iso,
    )

    return OperatorBriefing(
        generated_at_iso=generated_at_iso,
        loop_health_status=loop_status,
        cycles_today=cycles_today,
        decisions_today=decisions_today,
        executions_today=executions_today,
        blocked_today=blocked_today,
        latest_decision_summary=latest_summary,
        latest_decision_cycle_id=latest_cycle_id,
        latest_decision_overall_status=latest_overall_status,
        open_position_count=open_position_count,
        total_floating_pnl=total_floating_pnl,
        live_telemetry_source=live_telemetry_source,
        live_telemetry_stale=live_telemetry_stale,
        live_telemetry_last_update_iso=live_telemetry_last_update_iso,
        live_price_source_status=live_price_source_status,
        live_position_feed_label=live_position_feed_label,
        live_position_feed_detail=live_position_feed_detail,
        live_movement_source_truth=live_movement_source_truth,
        mt5_terminal_connected=mt5_terminal_connected,
        mt5_broker_api_verified=mt5_broker_api_verified,
        readiness_gates_open=gates_open,
        readiness_gates_total=gates_total,
        public_launch_gate_status=launch_status,
        public_launch_status=public_status,
        live_money_production_status=live_prod_status,
        public_launch_gate_pass_count=launch_pass_count,
        public_launch_gate_block_count=launch_block_count,
        public_launch_gate_blockers=launch_blockers,
        broker_truth_monitor_status=broker_truth_monitor_status,
        broker_truth_ready_for_live=broker_truth_ready_for_live,
        broker_truth_paper_force_latched=broker_truth_paper_force_latched,
        broker_truth_halt_reason_ids=broker_truth_halt_reason_ids,
        broker_truth_halt_reason_labels=broker_truth_halt_reason_labels,
        broker_truth_halt_reason_summary=broker_truth_halt_reason_summary,
        broker_truth_position_protection_status=broker_truth_position_protection_status,
        broker_truth_position_protection_label=broker_truth_position_protection_label,
        broker_truth_unprotected_position_count=broker_truth_unprotected_position_count,
        broker_truth_position_protection_detail=broker_truth_position_protection_detail,
        broker_truth_mt5_connected=broker_truth_mt5_connected,
        broker_truth_mt5_is_demo=broker_truth_mt5_is_demo,
        broker_truth_open_position_count=broker_truth_open_position_count,
        autowake_present=autowake_present,
        autowake_next_due_iso=autowake_next_due_iso,
        plain_english_briefing=plain_english_briefing,
        diagnostic_hints=diagnostic_hints,
    )


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------


def _extract_loop_health(
    loop_health: Optional[Mapping[str, Any]],
) -> tuple[str, int, int, int, int, bool, Optional[str], tuple[str, ...]]:
    if not isinstance(loop_health, Mapping):
        return "unknown", 0, 0, 0, 0, False, None, ()

    status = str(loop_health.get("overall_status") or "unknown")
    if status not in _LOOP_STATUS_VALUES:
        status = "unknown"
    cycles_today = _safe_int(loop_health.get("cycles_today"))
    decisions_today = _safe_int(loop_health.get("decisions_today"))
    executions_today = _safe_int(loop_health.get("executions_today"))
    blocked_today = _safe_int(loop_health.get("blocked_today"))
    autowake_present = bool(loop_health.get("autowake_present"))
    next_due_raw = loop_health.get("autowake_next_due_iso")
    autowake_next_due_iso = str(next_due_raw) if isinstance(next_due_raw, str) and next_due_raw else None

    raw_hints = loop_health.get("diagnostic_hints")
    hints: tuple[str, ...] = ()
    if isinstance(raw_hints, (list, tuple)):
        hints = tuple(str(h) for h in raw_hints if h)

    return (
        status,
        cycles_today,
        decisions_today,
        executions_today,
        blocked_today,
        autowake_present,
        autowake_next_due_iso,
        hints,
    )


def _extract_latest_decision(
    latest_decision: Optional[Mapping[str, Any]],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not isinstance(latest_decision, Mapping):
        return None, None, None
    summary = latest_decision.get("plain_english_summary")
    cycle_id = latest_decision.get("cycle_id")
    overall_status = latest_decision.get("overall_status")
    return (
        str(summary) if isinstance(summary, str) and summary else None,
        str(cycle_id) if cycle_id else None,
        str(overall_status) if isinstance(overall_status, str) and overall_status else None,
    )


def _extract_live_telemetry(
    live_telemetry: Optional[Mapping[str, Any]],
) -> tuple[int, float, str, bool, Optional[str], Optional[str], str, str, dict[str, Any]]:
    if not isinstance(live_telemetry, Mapping):
        detail = "No broker or paper/demo movement snapshot is reporting positions right now."
        return (
            0,
            0.0,
            "none",
            True,
            None,
            None,
            "NONE",
            detail,
            {
                "movement_stream_present": False,
                "telemetry_source": "none",
                "telemetry_stale": True,
                "telemetry_last_update_iso": None,
                "price_source_status": None,
                "price_source_label": None,
                "price_source_summary": None,
                "price_source_warning": None,
                "position_feed_label": "NONE",
                "position_feed_detail": detail,
                "static_simulation_active": False,
                "open_position_count": 0,
                "broker_ticket_position_count": 0,
                "simulator_position_count": 0,
                "provider_priced_simulator_position_count": 0,
                "static_simulator_position_count": 0,
                "stale_price_position_count": 0,
                "static_position_count": 0,
                "source_label_counts": {},
                "configured_market_data_provider": None,
                "provider_usable_symbols": [],
                "static_fallback_symbols": [],
                "mt5_fallback_symbols": [],
                "provider_stale_symbols": [],
                "provider_freshness_max_age_seconds": None,
                "provider_error_count": 0,
                "attention_required": False,
                "detail": detail,
                "local_detail": detail,
            },
        )
    totals = live_telemetry.get("totals")
    positions = live_telemetry.get("open_positions")
    has_position_shape = isinstance(totals, Mapping) or isinstance(positions, list)
    data_freshness = (
        live_telemetry.get("data_freshness")
        if isinstance(live_telemetry.get("data_freshness"), Mapping)
        else {}
    )
    raw_source = str(data_freshness.get("source") or "").strip()
    if raw_source in {
        "mt5_demo_account_snapshot",
        "mt5_live_account_snapshot",
        "mt5_terminal_api_verifier",
        "movement_stream",
        "none",
    }:
        source = raw_source
    else:
        source = "unknown" if has_position_shape else "none"
    stale = bool(data_freshness.get("stale")) if data_freshness else source == "none"
    last_update_iso = (
        str(data_freshness.get("last_update_iso"))
        if isinstance(data_freshness.get("last_update_iso"), str) and data_freshness.get("last_update_iso")
        else None
    )
    movement_source_truth = live_telemetry.get("movement_source_truth")
    movement_source = (
        movement_source_truth
        if isinstance(movement_source_truth, Mapping)
        else data_freshness.get("movement_source")
        if isinstance(data_freshness.get("movement_source"), Mapping)
        else {}
    )
    live_price_source_status = (
        str(movement_source.get("price_source_status"))
        if isinstance(movement_source.get("price_source_status"), str) and movement_source.get("price_source_status")
        else None
    )
    if isinstance(totals, Mapping):
        count = _safe_int(totals.get("open_position_count"))
        floating = _safe_float(totals.get("total_floating_pnl"))
    elif isinstance(positions, list):
        count = sum(1 for p in positions if isinstance(p, Mapping))
        floating = round(
            sum(
                _safe_float(p.get("floating_pnl"))
                for p in positions
                if isinstance(p, Mapping)
            ),
            2,
        )
    else:
        count = 0
        floating = 0.0
    label, detail = _resolve_live_position_feed(
        live_telemetry=live_telemetry,
        movement_source=movement_source,
        source=source,
        live_price_source_status=live_price_source_status,
        stale=stale,
    )
    return (
        count,
        floating,
        source,
        stale,
        last_update_iso,
        live_price_source_status,
        label,
        detail,
        _build_live_movement_source_truth(
            live_telemetry=live_telemetry,
            movement_source=movement_source,
            source=source,
            stale=stale,
            last_update_iso=last_update_iso,
            live_price_source_status=live_price_source_status,
            label=label,
            detail=detail,
            open_position_count=count,
        ),
    )


def _build_live_movement_source_truth(
    *,
    live_telemetry: Mapping[str, Any],
    movement_source: Mapping[str, Any],
    source: str,
    stale: bool,
    last_update_iso: Optional[str],
    live_price_source_status: Optional[str],
    label: str,
    detail: str,
    open_position_count: int,
) -> dict[str, Any]:
    positions = live_telemetry.get("open_positions") if isinstance(live_telemetry.get("open_positions"), list) else []
    broker_ticket_position_count = 0
    static_position_count = 0
    stale_price_position_count = 0
    provider_priced_simulator_position_count = 0
    source_label_counts: dict[str, int] = {}

    for row in positions:
        if not isinstance(row, Mapping):
            continue
        if row.get("broker_ticket") is not None:
            broker_ticket_position_count += 1
        source_label = str(row.get("position_source_label") or "").strip()
        if source_label:
            source_label_counts[source_label] = source_label_counts.get(source_label, 0) + 1
        price_source = str(row.get("price_source") or "")
        if price_source.startswith("provider_snapshot:") or price_source.startswith("operator_quote_override"):
            provider_priced_simulator_position_count += 1
        if bool(row.get("price_stale")):
            stale_price_position_count += 1
        if (
            bool(row.get("price_stale"))
            or price_source.startswith("paper_route_snapshot")
            or row.get("position_source_label") in {"PAPER_SIM_STATIC", "PAPER_SIM_BROKER_TICKET_STATIC"}
        ):
            static_position_count += 1

    if source == "movement_stream" and live_price_source_status == "STATIC_SIMULATION_FALLBACK" and positions:
        static_position_count = max(static_position_count, len(positions))

    configured_provider = str(
        movement_source.get("configured_market_data_provider")
        or movement_source.get("market_data_provider")
        or ""
    ).strip() or None
    provider_errors = (
        movement_source.get("provider_errors")
        if isinstance(movement_source.get("provider_errors"), Mapping)
        else None
    )
    provider_error_count = _safe_int(movement_source.get("provider_error_count"))
    if provider_error_count <= 0 and isinstance(provider_errors, Mapping):
        provider_error_count = len(provider_errors)

    truth: dict[str, Any] = dict(movement_source)
    truth.update({
        "movement_stream_present": source == "movement_stream",
        "telemetry_source": source,
        "telemetry_stale": stale,
        "telemetry_last_update_iso": last_update_iso,
        "price_source_status": live_price_source_status,
        "price_source_label": (
            str(movement_source.get("price_source_label"))
            if isinstance(movement_source.get("price_source_label"), str) and movement_source.get("price_source_label")
            else None
        ),
        "price_source_summary": (
            str(movement_source.get("price_source_summary"))
            if isinstance(movement_source.get("price_source_summary"), str) and movement_source.get("price_source_summary")
            else None
        ),
        "price_source_warning": (
            str(movement_source.get("price_source_warning"))
            if isinstance(movement_source.get("price_source_warning"), str) and movement_source.get("price_source_warning")
            else None
        ),
        "position_feed_label": label,
        "position_feed_detail": detail,
        "static_simulation_active": bool(movement_source.get("static_simulation_active")) or static_position_count > 0,
        "open_position_count": open_position_count,
        "broker_ticket_position_count": broker_ticket_position_count,
        "simulator_position_count": max(0, open_position_count - broker_ticket_position_count),
        "provider_priced_simulator_position_count": provider_priced_simulator_position_count,
        "static_simulator_position_count": static_position_count,
        "stale_price_position_count": stale_price_position_count,
        "static_position_count": static_position_count,
        "source_label_counts": source_label_counts,
        "configured_market_data_provider": configured_provider,
        "provider_usable_symbols": _string_list(movement_source.get("provider_usable_symbols")),
        "static_fallback_symbols": _string_list(movement_source.get("static_fallback_symbols")),
        "mt5_fallback_symbols": _string_list(movement_source.get("mt5_fallback_symbols")),
        "provider_stale_symbols": _string_list(movement_source.get("provider_stale_symbols")),
        "provider_freshness_max_age_seconds": movement_source.get("provider_freshness_max_age_seconds"),
        "provider_error_count": provider_error_count,
        "attention_required": bool(movement_source.get("attention_required")) or static_position_count > 0 or stale,
        "detail": detail,
        "local_detail": detail,
    })
    return truth


def _resolve_live_position_feed(
    *,
    live_telemetry: Mapping[str, Any],
    movement_source: Mapping[str, Any],
    source: str,
    live_price_source_status: Optional[str],
    stale: bool,
) -> tuple[str, str]:
    fallback_label, fallback_detail = _describe_live_position_feed(
        source=source,
        live_price_source_status=live_price_source_status,
        stale=stale,
    )
    top_level_label = str(live_telemetry.get("position_feed_label") or "").strip()
    top_level_detail = str(live_telemetry.get("position_feed_detail") or "").strip()
    nested_label = str(movement_source.get("position_feed_label") or "").strip()
    nested_detail = str(movement_source.get("position_feed_detail") or "").strip()

    if top_level_label or top_level_detail:
        return (
            top_level_label or nested_label or fallback_label,
            _append_stale_suffix(top_level_detail or nested_detail or fallback_detail, stale),
        )

    if nested_label or nested_detail:
        return (
            nested_label or fallback_label,
            _append_stale_suffix(nested_detail or fallback_detail, stale),
        )

    return fallback_label, fallback_detail


def _describe_live_position_feed(
    *,
    source: str,
    live_price_source_status: Optional[str],
    stale: bool,
) -> tuple[str, str]:
    if source == "mt5_demo_account_snapshot":
        detail = (
            "Position counts and floating P&L come from the current connected MT5 demo "
            "account snapshot and represent broker-side demo positions."
        )
        return "MT5 DEMO", _append_stale_suffix(detail, stale)

    if source == "mt5_live_account_snapshot":
        detail = (
            "Position counts and floating P&L come from the current connected MT5 live "
            "account snapshot and represent broker-side live positions."
        )
        return "MT5 LIVE", _append_stale_suffix(detail, stale)

    if source == "mt5_terminal_api_verifier":
        detail = (
            "Position counts and floating P&L come from the MT5 terminal mirror and "
            "represent broker-side positions."
        )
        return "LIVE MT5", _append_stale_suffix(detail, stale)

    if source == "movement_stream":
        if live_price_source_status == "STATIC_SIMULATION_FALLBACK":
            detail = (
                "Position counts and floating P&L come from paper/demo simulator proof rows "
                "with static simulation fallback; they are not live MT5 terminal positions and can stay "
                "flat at entry until provider/MT5 prices are usable."
            )
        elif live_price_source_status == "MIXED_PROVIDER_AND_STATIC_FALLBACK":
            detail = (
                "Position counts and floating P&L come from paper/demo simulator proof rows; "
                "some rows are repriced by provider/MT5 fallback and some remain static "
                "simulation. These are not live MT5 terminal positions."
            )
        elif live_price_source_status == "PROVIDER_ACTIVE":
            detail = (
                "Position counts and floating P&L come from paper/demo simulator proof rows "
                "repriced by provider/MT5 fallback where available; these are not live MT5 terminal positions."
            )
        elif live_price_source_status == "CACHE_WARMING":
            detail = (
                "Position counts and floating P&L come from the paper/demo movement stream "
                "while source truth is warming; these are not live MT5 terminal positions."
            )
        else:
            detail = (
                "Position counts and floating P&L come from paper/demo simulator proof rows, "
                "not live MT5 terminal positions."
            )
        return "SIM PROOF", _append_stale_suffix(detail, stale)

    if source == "unknown":
        detail = (
            "Position counts are present, but the telemetry source was not labeled, so this "
            "briefing cannot prove whether the rows are MT5 broker positions or simulator proof rows."
        )
        return "UNKNOWN", _append_stale_suffix(detail, stale)

    return "NONE", "No broker or paper/demo movement snapshot is reporting positions right now."


def _append_stale_suffix(detail: str, stale: bool) -> str:
    if not stale:
        return detail
    if "latest telemetry snapshot is marked stale" in detail.lower():
        return detail
    return detail + " The latest telemetry snapshot is marked stale."


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _extract_mt5_probe(
    mt5_probe: Optional[Mapping[str, Any]],
) -> tuple[bool, bool]:
    if not isinstance(mt5_probe, Mapping):
        return False, False

    # Several shapes are tolerated. The mt5_terminal_api_verifier report
    # commonly carries `summary.terminal_connected` and either
    # `summary.broker_source_verified` or `summary.broker_api_verified`;
    # the simpler `mt5_probe_status` shape uses `connected` at top level.
    summary = mt5_probe.get("summary") if isinstance(mt5_probe.get("summary"), Mapping) else None
    terminal_connected = False
    broker_api_verified = False

    if isinstance(summary, Mapping):
        terminal_connected = bool(summary.get("terminal_connected"))
        broker_api_verified = bool(
            summary.get("broker_api_verified")
            or summary.get("broker_source_verified")
        )

    if not terminal_connected:
        terminal_connected = bool(mt5_probe.get("terminal_connected") or mt5_probe.get("connected"))
    if not broker_api_verified:
        broker_api_verified = bool(
            mt5_probe.get("broker_api_verified")
            or mt5_probe.get("broker_source_verified")
        )
    return terminal_connected, broker_api_verified


def _extract_readiness(
    readiness: Optional[Mapping[str, Any]],
) -> tuple[int, int, tuple[str, ...]]:
    if not isinstance(readiness, Mapping):
        return 0, 0, ()

    gates_total = _safe_int(readiness.get("checks_total"))
    # "gates_open" in the briefing semantics = checks that PASSED (open
    # for live), matching the readiness report's `checks_passed`.
    gates_passed = _safe_int(readiness.get("checks_passed"))

    hints: list[str] = []
    next_actions = readiness.get("next_actions")
    if isinstance(next_actions, (list, tuple)):
        for item in next_actions:
            if item:
                hints.append(str(item))

    # Also surface blocked checks' next_action strings as hints when the
    # report includes a `checks` list.
    checks = readiness.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, Mapping):
                continue
            status = str(check.get("status") or "").upper()
            blocks_live = bool(check.get("blocks_live"))
            if blocks_live and status != "PASSED":
                next_action = check.get("next_action")
                if next_action and str(next_action) not in hints:
                    hints.append(str(next_action))

    return gates_passed, gates_total, tuple(hints)


def _extract_public_launch_gate(
    public_launch_gate: Optional[Mapping[str, Any]],
) -> tuple[str, str, str, int, int, tuple[str, ...]]:
    if not isinstance(public_launch_gate, Mapping):
        return "unknown", "unknown", "unknown", 0, 0, ()

    launch_status = str(public_launch_gate.get("launch_gate_status") or "unknown")
    public_status = str(public_launch_gate.get("public_launch_status") or "unknown")
    live_prod_status = str(public_launch_gate.get("live_money_production_status") or "unknown")
    pass_count = _safe_int(public_launch_gate.get("pass_count"))
    block_count = _safe_int(public_launch_gate.get("block_count"))
    blockers: list[str] = []

    raw_blockers = public_launch_gate.get("hard_blockers")
    if isinstance(raw_blockers, (list, tuple)):
        blockers.extend(str(item) for item in raw_blockers if item)

    gates = public_launch_gate.get("gates")
    if isinstance(gates, list):
        for gate in gates:
            if not isinstance(gate, Mapping):
                continue
            if str(gate.get("status") or "").upper() == "PASS":
                continue
            next_action = gate.get("next_action") or gate.get("detail")
            if next_action:
                text = str(next_action)
                if text not in blockers:
                    blockers.append(text)

    return launch_status, public_status, live_prod_status, pass_count, block_count, tuple(blockers)


def _extract_broker_truth_monitor(
    broker_truth_monitor: Optional[Mapping[str, Any]],
) -> tuple[
    str,
    bool,
    bool,
    tuple[str, ...],
    tuple[str, ...],
    str,
    str,
    str,
    int,
    Optional[str],
    Optional[bool],
    Optional[bool],
    int,
    tuple[str, ...],
]:
    if not isinstance(broker_truth_monitor, Mapping):
        return (
            "unavailable",
            False,
            False,
            (),
            (),
            "none",
            "POSITION_PROTECTION_UNAVAILABLE",
            "PROTECTION UNAVAILABLE",
            0,
            None,
            None,
            None,
            0,
            (),
        )

    latest_report = (
        broker_truth_monitor.get("latest_report")
        if isinstance(broker_truth_monitor.get("latest_report"), Mapping)
        else broker_truth_monitor
    )
    status = str(
        broker_truth_monitor.get("monitor_status")
        or latest_report.get("monitor_status")
        or "unavailable"
    )
    ready_for_live = bool(broker_truth_monitor.get("ready_for_live"))
    reason_ids = tuple(
        str(item).strip()
        for item in (latest_report.get("monitor_auto_halt_reason_ids") or broker_truth_monitor.get("monitor_auto_halt_reason_ids") or ())
        if str(item).strip()
    )
    reason_labels = tuple(_broker_truth_reason_label(item) for item in reason_ids)
    reason_summary = ", ".join(reason_labels) if reason_labels else "none"
    paper_force_latched = bool(
        latest_report.get("auto_halt_latched_from_monitor")
        or broker_truth_monitor.get("auto_halt_latched_from_monitor")
        or reason_ids
    )
    protection_status = str(
        latest_report.get("position_protection_status")
        or broker_truth_monitor.get("position_protection_status")
        or "POSITION_PROTECTION_UNAVAILABLE"
    )
    protection_label = _position_protection_label(protection_status)
    unprotected_count = _safe_int(
        latest_report.get("position_protection_unprotected_position_count")
        or broker_truth_monitor.get("position_protection_unprotected_position_count")
    )
    detail_raw = (
        latest_report.get("position_protection_detail")
        or broker_truth_monitor.get("position_protection_detail")
    )
    detail = str(detail_raw).strip() if detail_raw else None
    mt5_connected = _optional_bool(latest_report.get("mt5_connected"))
    mt5_is_demo = _optional_bool(latest_report.get("mt5_is_demo"))
    open_position_count = _safe_int(latest_report.get("mt5_open_position_count"))

    hints: list[str] = []
    if paper_force_latched:
        hints.append(f"Broker truth paper-force active: {reason_summary}.")
    if unprotected_count > 0:
        hints.append(detail or f"{unprotected_count} broker-visible live position(s) lack stop-loss protection.")
    next_action = latest_report.get("next_action") or broker_truth_monitor.get("next_action")
    if next_action:
        hints.append(str(next_action))

    return (
        status,
        ready_for_live,
        paper_force_latched,
        reason_ids,
        reason_labels,
        reason_summary,
        protection_status,
        protection_label,
        unprotected_count,
        detail,
        mt5_connected,
        mt5_is_demo,
        open_position_count,
        tuple(hints),
    )


def _fresh_mt5_broker_truth_fields(
    *,
    live_telemetry: Optional[Mapping[str, Any]],
    source: str,
    stale: bool,
    count: int,
    movement_truth: Mapping[str, Any],
) -> dict[str, Any]:
    """Return current broker fields only when telemetry is fresh MT5 truth."""

    if source not in {
        "mt5_demo_account_snapshot",
        "mt5_live_account_snapshot",
        "mt5_terminal_api_verifier",
    } or stale:
        return {}

    telemetry = live_telemetry if isinstance(live_telemetry, Mapping) else {}
    account_mode = str(
        movement_truth.get("account_mode")
        or telemetry.get("account_mode")
        or ""
    ).upper()
    is_demo = source == "mt5_demo_account_snapshot" or account_mode == "DEMO"
    protection = (
        telemetry.get("position_protection")
        if isinstance(telemetry.get("position_protection"), Mapping)
        else {}
    )
    detail_raw = protection.get("detail")
    return {
        "open_position_count": _safe_int(count),
        "is_demo": is_demo,
        "position_protection_status": protection.get("status"),
        "unprotected_position_count": _safe_int(
            protection.get("unprotected_position_count")
        ),
        "position_protection_detail": str(detail_raw).strip() if detail_raw else None,
    }


def _broker_truth_reason_label(value: str) -> str:
    labels = {
        "broker_truth_reconciliation": "Broker Truth",
        "terminal_position_reconciliation": "Terminal Reconciliation",
        "live_open_positions_crosscheck": "Open Position Crosscheck",
        "live_position_stop_loss_protection": "Stop-Loss Protection",
        "mt5_account_identity_matches_config": "MT5 Account Identity",
    }
    return labels.get(value, value.replace("_", " "))


def _position_protection_label(status: str) -> str:
    if status == "ALL_POSITIONS_PROTECTED":
        return "PROTECTION CLEAR"
    if status == "UNPROTECTED_POSITIONS":
        return "UNPROTECTED POSITIONS"
    if status == "POSITION_PROTECTION_UNAVAILABLE":
        return "PROTECTION UNAVAILABLE"
    return status.replace("_", " ")


def _merge_hints(
    *hint_sources: tuple[str, ...],
    limit: int,
) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for hints in hint_sources:
        for hint in hints:
            if not hint or hint in seen:
                continue
            merged.append(hint)
            seen.add(hint)
            if len(merged) >= limit:
                return tuple(merged)
    return tuple(merged)


# ---------------------------------------------------------------------------
# Plain-English briefing
# ---------------------------------------------------------------------------


def _build_plain_english_briefing(
    *,
    loop_status: str,
    cycles_today: int,
    latest_summary: Optional[str],
    open_position_count: int,
    total_floating_pnl: float,
    live_telemetry_source: str,
    live_telemetry_stale: bool,
    live_telemetry_last_update_iso: Optional[str],
    live_price_source_status: Optional[str],
    mt5_terminal_connected: bool,
    gates_open: int,
    gates_total: int,
    public_launch_gate_status: str,
    public_launch_status: str,
    live_money_production_status: str,
    public_launch_gate_block_count: int,
    broker_truth_monitor_status: str,
    broker_truth_ready_for_live: bool,
    broker_truth_paper_force_latched: bool,
    broker_truth_halt_reason_summary: str,
    broker_truth_position_protection_label: str,
    broker_truth_unprotected_position_count: int,
    diagnostic_hints: tuple[str, ...],
    autowake_next_due_iso: Optional[str],
) -> str:
    sentences: list[str] = []

    # Sentence 1 — loop status + cycles today + next-fire hint when known.
    if loop_status == "running":
        s1 = f"Autonomous loop is running with {cycles_today} cycle(s) recorded today."
    elif loop_status == "stalled":
        s1 = f"Autonomous loop is stalled; {cycles_today} cycle(s) recorded today."
    elif loop_status == "never_started":
        s1 = "Autonomous loop has not started yet; no cycles recorded today."
    else:
        s1 = "Autonomous loop status is unknown; no cycle evidence available."
    if autowake_next_due_iso:
        s1 += f" Next autowake fire scheduled at {autowake_next_due_iso}."
    sentences.append(s1)

    # Sentence 2 — latest decision headline.
    if latest_summary:
        sentences.append(f"Latest decision: {latest_summary}")
    else:
        sentences.append("No recent agent decision is on record.")

    # Sentence 3 — positions + floating P&L.
    sentences.append(
        _live_position_sentence(
            open_position_count=open_position_count,
            total_floating_pnl=total_floating_pnl,
            live_telemetry_source=live_telemetry_source,
            live_price_source_status=live_price_source_status,
        )
    )
    if live_telemetry_stale:
        if live_telemetry_last_update_iso:
            sentences.append(f"Live telemetry snapshot is stale as of {live_telemetry_last_update_iso}.")
        else:
            sentences.append("Live telemetry snapshot is stale.")

    # Sentence 4 — MT5 connection + readiness gates.
    mt5_phrase = (
        "MT5 terminal is connected" if mt5_terminal_connected else "MT5 terminal is not connected"
    )
    if gates_total > 0:
        sentences.append(
            f"{mt5_phrase}; {gates_open}/{gates_total} readiness gate(s) currently passing."
        )
    else:
        sentences.append(f"{mt5_phrase}; readiness gate status unavailable.")

    if public_launch_gate_status != "unknown":
        if public_launch_gate_status == "PASS":
            sentences.append("Public launch gate is PASS; public launch and live-money production are marked READY.")
        else:
            sentences.append(
                f"Public launch gate is {public_launch_gate_status}; public launch is "
                f"{public_launch_status} and live-money production is "
                f"{live_money_production_status}, with {public_launch_gate_block_count} blocker(s)."
            )

    if broker_truth_monitor_status != "unavailable":
        if broker_truth_paper_force_latched:
            sentences.append(
                f"Broker truth monitor is forcing paper mode; reasons: {broker_truth_halt_reason_summary}."
            )
        elif not broker_truth_ready_for_live:
            sentences.append(
                f"Broker truth monitor is not ready for live; status is {broker_truth_monitor_status}."
            )
        if broker_truth_unprotected_position_count > 0:
            sentences.append(
                f"Broker truth position protection is {broker_truth_position_protection_label}; "
                f"{broker_truth_unprotected_position_count} unprotected broker-visible live position(s)."
            )

    # Sentence 5 (optional) — top diagnostic hint.
    if diagnostic_hints:
        sentences.append(f"Top diagnostic hint: {diagnostic_hints[0]}")

    return " ".join(sentences)


def _live_position_sentence(
    *,
    open_position_count: int,
    total_floating_pnl: float,
    live_telemetry_source: str,
    live_price_source_status: Optional[str],
) -> str:
    pnl_text = (
        f"{total_floating_pnl:.2f} open P&L after reported carry/costs"
        if live_telemetry_source in {"mt5_demo_account_snapshot", "mt5_live_account_snapshot"}
        else f"{total_floating_pnl:.2f} floating P&L"
    )
    if live_telemetry_source == "mt5_demo_account_snapshot":
        if open_position_count > 0:
            return f"{open_position_count} active MT5 demo broker position(s) carrying {pnl_text}."
        return "No active MT5 demo broker positions."
    if live_telemetry_source == "mt5_live_account_snapshot":
        if open_position_count > 0:
            return f"{open_position_count} active MT5 live broker position(s) carrying {pnl_text}."
        return "No active MT5 live broker positions."
    if live_telemetry_source == "mt5_terminal_api_verifier":
        if open_position_count > 0:
            return f"{open_position_count} active MT5 broker position(s) carrying {pnl_text}."
        return "No active MT5 broker positions."
    if live_telemetry_source == "movement_stream":
        if open_position_count > 0:
            prefix = (
                f"{open_position_count} active paper/demo simulator proof row(s) carrying {pnl_text}."
            )
        else:
            prefix = "No active paper/demo simulator proof rows."
        if live_price_source_status == "STATIC_SIMULATION_FALLBACK":
            return prefix + " Source is static simulation, so prices can sit at entry until provider/MT5 quotes are usable."
        if live_price_source_status == "MIXED_PROVIDER_AND_STATIC_FALLBACK":
            return prefix + " Source is mixed: some rows are provider/MT5 repriced and some are still static simulation."
        if live_price_source_status == "PROVIDER_ACTIVE":
            return prefix + " Source is provider-backed paper/demo repricing, not live MT5 broker truth."
        if live_price_source_status == "CACHE_WARMING":
            return prefix + " Source truth is still warming, so treat this as paper/demo telemetry only."
        return prefix + " These rows are paper/demo telemetry, not MT5 broker positions."
    if live_telemetry_source == "unknown":
        if open_position_count > 0:
            return f"{open_position_count} active position(s) carrying {pnl_text}, but the telemetry source is unlabeled."
        return "No active positions and the telemetry source is unlabeled."
    return "No active positions and no broker or paper/demo movement source is reporting."


def refresh_operator_briefing_live_telemetry(
    payload: Mapping[str, Any],
    live_telemetry: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    """Overlay fast-changing account truth onto a cached briefing payload.

    Loop/readiness diagnostics can be cached, but broker position count, floating
    P&L, source identity, and snapshot age must follow the current MT5 mirror.
    """

    out = dict(payload)
    (
        count,
        floating,
        source,
        stale,
        last_update_iso,
        price_source_status,
        feed_label,
        feed_detail,
        movement_truth,
    ) = _extract_live_telemetry(live_telemetry)

    old_source = str(out.get("live_telemetry_source") or "none")
    old_count = _safe_int(out.get("open_position_count"))
    old_floating = _safe_float(out.get("total_floating_pnl"))
    old_price_status = (
        str(out.get("live_price_source_status"))
        if out.get("live_price_source_status") is not None
        else None
    )
    old_sentence = _live_position_sentence(
        open_position_count=old_count,
        total_floating_pnl=old_floating,
        live_telemetry_source=old_source,
        live_price_source_status=old_price_status,
    )
    new_sentence = _live_position_sentence(
        open_position_count=count,
        total_floating_pnl=floating,
        live_telemetry_source=source,
        live_price_source_status=price_source_status,
    )
    old_stale_sentence = _stale_telemetry_sentence(
        bool(out.get("live_telemetry_stale")),
        str(out.get("live_telemetry_last_update_iso") or "") or None,
    )
    new_stale_sentence = _stale_telemetry_sentence(stale, last_update_iso)
    old_block = " ".join(part for part in (old_sentence, old_stale_sentence) if part)
    new_block = " ".join(part for part in (new_sentence, new_stale_sentence) if part)
    briefing = str(out.get("plain_english_briefing") or "").strip()
    if old_block and old_block in briefing:
        briefing = briefing.replace(old_block, new_block, 1)
    elif old_sentence and old_sentence in briefing:
        briefing = briefing.replace(old_sentence, new_block, 1)
    elif new_block and new_block not in briefing:
        briefing = " ".join(part for part in (briefing, f"Current account telemetry: {new_block}") if part)

    current_mt5_truth = _fresh_mt5_broker_truth_fields(
        live_telemetry=live_telemetry,
        source=source,
        stale=stale,
        count=count,
        movement_truth=movement_truth,
    )
    refreshed_fields: dict[str, Any] = {
            "open_position_count": count,
            "total_floating_pnl": floating,
            "live_telemetry_source": source,
            "live_telemetry_stale": stale,
            "live_telemetry_last_update_iso": last_update_iso,
            "live_price_source_status": price_source_status,
            "live_position_feed_label": feed_label,
            "live_position_feed_detail": feed_detail,
            "live_movement_source_truth": movement_truth,
            "plain_english_briefing": briefing,
    }
    if current_mt5_truth:
        refreshed_fields.update(
            {
                "mt5_terminal_connected": True,
                "mt5_broker_api_verified": True,
                "broker_truth_mt5_connected": True,
                "broker_truth_mt5_is_demo": current_mt5_truth["is_demo"],
                "broker_truth_open_position_count": current_mt5_truth[
                    "open_position_count"
                ],
            }
        )
        if current_mt5_truth.get("position_protection_status"):
            protection_status = str(
                current_mt5_truth["position_protection_status"]
            )
            refreshed_fields.update(
                {
                    "broker_truth_position_protection_status": protection_status,
                    "broker_truth_position_protection_label": _position_protection_label(
                        protection_status
                    ),
                    "broker_truth_unprotected_position_count": _safe_int(
                        current_mt5_truth.get("unprotected_position_count")
                    ),
                    "broker_truth_position_protection_detail": current_mt5_truth.get(
                        "position_protection_detail"
                    ),
                }
            )
    out.update(refreshed_fields)
    return out


def _stale_telemetry_sentence(stale: bool, last_update_iso: Optional[str]) -> str:
    if not stale:
        return ""
    if last_update_iso:
        return f"Live telemetry snapshot is stale as of {last_update_iso}."
    return "Live telemetry snapshot is stale."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_now(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


# ---------------------------------------------------------------------------
# Optional I/O helper (kept separate so the composer stays pure)
# ---------------------------------------------------------------------------


def load_operator_briefing_inputs(repo_root: Path | str) -> dict[str, Any]:
    """Load the latest evidence inputs for :func:`compose_operator_briefing`.

    Each underlying loader is wrapped so a missing or unreadable artifact
    becomes ``None`` for that input. Tests should NOT use this helper —
    they should construct the input dicts directly.
    """

    root = Path(repo_root)

    loop_health: Optional[dict[str, Any]] = None
    try:
        from cas_forex.autonomous_loop_health import (
            load_loop_health_inputs,
            summarize_autonomous_loop_health,
        )
        from dataclasses import asdict as _asdict

        inputs = load_loop_health_inputs(root)
        summary = summarize_autonomous_loop_health(**inputs)
        loop_health = _asdict(summary)
    except Exception:
        loop_health = None

    latest_decision: Optional[dict[str, Any]] = None
    try:
        from cas_forex.agent_decision_explainer import explain_latest_agent_decision
        from dataclasses import asdict as _asdict

        # Reuse the loop-health loader's pattern to find evidence dicts.
        from cas_forex.autonomous_loop_health import load_loop_health_inputs

        loop_inputs = load_loop_health_inputs(root)
        explanation = explain_latest_agent_decision(
            agent_cycle_report=loop_inputs.get("latest_cycle_report"),
            daily_learning_rollup=loop_inputs.get("daily_rollup"),
        )
        latest_decision = _asdict(explanation)
    except Exception:
        latest_decision = None

    live_telemetry: Optional[dict[str, Any]] = None
    try:
        from api.routes.live_telemetry import collect_live_telemetry

        live_telemetry = collect_live_telemetry()
    except Exception:
        live_telemetry = None

    mt5_probe: Optional[dict[str, Any]] = None
    try:
        from cas_forex.mt5_live import get_mt5_account_snapshot

        current_mt5 = get_mt5_account_snapshot()
        mt5_probe = {
            "connected": bool(current_mt5.get("connected")),
            "broker_api_verified": bool(current_mt5.get("connected")),
            "snapshot_observed_at": current_mt5.get("snapshot_observed_at"),
        }
    except Exception:
        mt5_probe = None

    readiness: Optional[dict[str, Any]] = None
    try:
        from api import data as _data

        readiness = _data.live_readiness(sync_to_broker=False)
    except Exception:
        readiness = None

    public_launch_gate: Optional[dict[str, Any]] = None
    try:
        from cas_forex.public_launch_gate import build_public_launch_gate

        public_launch_gate = build_public_launch_gate(root)
    except Exception:
        public_launch_gate = None

    broker_truth_monitor: Optional[dict[str, Any]] = None
    try:
        from cas_forex.broker_truth_monitor import monitor_fast_status

        broker_truth_monitor = monitor_fast_status()
    except Exception:
        broker_truth_monitor = None

    return {
        "loop_health": loop_health,
        "latest_decision": latest_decision,
        "live_telemetry": live_telemetry,
        "mt5_probe": mt5_probe,
        "readiness": readiness,
        "public_launch_gate": public_launch_gate,
        "broker_truth_monitor": broker_truth_monitor,
    }
