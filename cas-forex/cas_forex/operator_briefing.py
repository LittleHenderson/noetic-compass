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
    mt5_terminal_connected: bool
    mt5_broker_api_verified: bool
    readiness_gates_open: int
    readiness_gates_total: int
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
    open_position_count, total_floating_pnl = _extract_live_telemetry(live_telemetry)

    # ---- MT5 probe
    mt5_terminal_connected, mt5_broker_api_verified = _extract_mt5_probe(mt5_probe)

    # ---- readiness gates
    gates_open, gates_total, readiness_hints = _extract_readiness(readiness)

    # ---- diagnostic hints (loop + readiness, capped at 5)
    diagnostic_hints = _merge_hints(loop_hints, readiness_hints, limit=5)

    # ---- plain-English briefing
    plain_english_briefing = _build_plain_english_briefing(
        loop_status=loop_status,
        cycles_today=cycles_today,
        latest_summary=latest_summary,
        open_position_count=open_position_count,
        total_floating_pnl=total_floating_pnl,
        mt5_terminal_connected=mt5_terminal_connected,
        gates_open=gates_open,
        gates_total=gates_total,
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
        mt5_terminal_connected=mt5_terminal_connected,
        mt5_broker_api_verified=mt5_broker_api_verified,
        readiness_gates_open=gates_open,
        readiness_gates_total=gates_total,
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
) -> tuple[int, float]:
    if not isinstance(live_telemetry, Mapping):
        return 0, 0.0
    totals = live_telemetry.get("totals")
    if isinstance(totals, Mapping):
        return (
            _safe_int(totals.get("open_position_count")),
            _safe_float(totals.get("total_floating_pnl")),
        )
    # Fall back to deriving from the open_positions list if no totals.
    positions = live_telemetry.get("open_positions")
    if isinstance(positions, list):
        count = sum(1 for p in positions if isinstance(p, Mapping))
        floating = sum(
            _safe_float(p.get("floating_pnl"))
            for p in positions
            if isinstance(p, Mapping)
        )
        return count, round(floating, 2)
    return 0, 0.0


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


def _merge_hints(
    loop_hints: tuple[str, ...],
    readiness_hints: tuple[str, ...],
    *,
    limit: int,
) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for hint in (*loop_hints, *readiness_hints):
        if not hint or hint in seen:
            continue
        merged.append(hint)
        seen.add(hint)
        if len(merged) >= limit:
            break
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
    mt5_terminal_connected: bool,
    gates_open: int,
    gates_total: int,
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
    if open_position_count > 0:
        sentences.append(
            f"{open_position_count} active position(s) carrying "
            f"{total_floating_pnl:.2f} floating P&L."
        )
    else:
        sentences.append("No active positions.")

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

    # Sentence 5 (optional) — top diagnostic hint.
    if diagnostic_hints:
        sentences.append(f"Top diagnostic hint: {diagnostic_hints[0]}")

    return " ".join(sentences)


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
        from api import data as _data

        mt5_probe = _data.mt5_terminal_api_verifier_latest()
    except Exception:
        mt5_probe = None

    readiness: Optional[dict[str, Any]] = None
    try:
        from api import data as _data

        readiness = _data.live_readiness(sync_to_broker=False)
    except Exception:
        readiness = None

    return {
        "loop_health": loop_health,
        "latest_decision": latest_decision,
        "live_telemetry": live_telemetry,
        "mt5_probe": mt5_probe,
        "readiness": readiness,
    }
