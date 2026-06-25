"""Autonomous loop health summary for the CAS Forex agent desk.

This module exposes a single pure primitive, :func:`summarize_autonomous_loop_health`,
that compresses four upstream evidence sources into a small, factual
:class:`AutonomousLoopHealth` record. The intended consumer is the operator-facing
LLM bot, which needs to answer "is the autonomous loop alive and producing
decisions?" in a single sentence without fabricating numbers.

Design contract:

* The summary function is *pure*. It does not touch the filesystem. Callers pass
  in already-parsed dicts (autowake report, latest cycle report, recent event
  journal entries, daily learning rollup); any may be ``None``.
* Missing inputs are never papered over. A missing ``last_cycle_at_iso`` keeps
  ``seconds_since_last_cycle`` at ``None`` rather than guessing.
* The bot is *health monitoring*, not trade advisory. The
  ``plain_english_summary`` deliberately avoids any phrasing that could be read
  as a trade recommendation ("buy now", "good entry", "should you trade").
* All wall-clock comparisons normalise to UTC so a caller passing a naive
  timestamp (assumed UTC) and a caller passing an aware ISO get the same answer.

A small helper :func:`load_loop_health_inputs` is provided for production
callers that *do* need to read the latest evidence files. Tests should not use
it; they should construct dicts directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence


__all__ = [
    "AutonomousLoopHealth",
    "summarize_autonomous_loop_health",
    "load_loop_health_inputs",
]


# Status strings — fixed vocabulary documented in the dataclass below.
STATUS_RUNNING = "running"
STATUS_STALLED = "stalled"
STATUS_NEVER_STARTED = "never_started"
STATUS_UNKNOWN = "unknown"


@dataclass(frozen=True)
class AutonomousLoopHealth:
    """Structured snapshot of autonomous-loop liveness.

    Attributes
    ----------
    overall_status:
        One of ``"running"``, ``"stalled"``, ``"never_started"``, ``"unknown"``.

        * ``"running"`` — a cycle report exists and was created within the
          configured threshold *OR* the autowake schedule names a future
          ``next_due_iso`` (the loop is paced and simply between fires).
        * ``"stalled"`` — at least one cycle report exists, the most recent is
          older than the threshold, and no future autowake fire is scheduled.
        * ``"never_started"`` — no cycle report has been provided at all.
        * ``"unknown"`` — none of the four input sources were provided. The
          caller could not produce evidence; the function refuses to fabricate.
    last_cycle_at_iso:
        UTC ISO 8601 timestamp of the most recent cycle (or ``None``).
    seconds_since_last_cycle:
        Seconds between ``now`` and the most recent cycle (or ``None``).
    cycles_today:
        Count of cycle reports whose ``created_at`` falls on the same UTC date
        as ``now``. Derived from the event journal when available; falls back
        to ``1`` if only the most recent cycle report is supplied and it is
        today.
    decisions_today:
        Sum of approved + rejected route intents recorded today (from event
        journal route-intent counts or the daily rollup summary).
    executions_today:
        Count of terminal command executions today.
    blocked_today:
        Validator REJECTs + PCBA blocks + confirm-declined entries today.
    autowake_present:
        ``True`` when an autowake report was supplied.
    autowake_next_due_iso:
        UTC ISO timestamp of the next scheduled wake (or ``None``). Only used
        for status classification when interpretable as a future timestamp.
    plain_english_summary:
        One to two sentences. Never references trade picks.
    diagnostic_hints:
        Actionable strings the LLM bot can echo. Empty tuple when status is
        ``"running"``.
    """

    overall_status: str
    last_cycle_at_iso: Optional[str]
    seconds_since_last_cycle: Optional[float]
    cycles_today: int
    decisions_today: int
    executions_today: int
    blocked_today: int
    autowake_present: bool
    autowake_next_due_iso: Optional[str]
    plain_english_summary: str
    diagnostic_hints: tuple[str, ...]


# ---------------------------------------------------------------------------
# Public summarise entrypoint
# ---------------------------------------------------------------------------


def summarize_autonomous_loop_health(
    *,
    autowake_report: Optional[Mapping[str, Any]] = None,
    latest_cycle_report: Optional[Mapping[str, Any]] = None,
    recent_event_journal: Optional[Sequence[Mapping[str, Any]]] = None,
    daily_rollup: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
    running_threshold_minutes: int = 60,
) -> AutonomousLoopHealth:
    """Compute an :class:`AutonomousLoopHealth` snapshot from parsed evidence."""

    now_utc = _coerce_now(now)

    # Inputs all None -> unknown (cannot evidence anything).
    if (
        autowake_report is None
        and latest_cycle_report is None
        and not recent_event_journal
        and daily_rollup is None
    ):
        return AutonomousLoopHealth(
            overall_status=STATUS_UNKNOWN,
            last_cycle_at_iso=None,
            seconds_since_last_cycle=None,
            cycles_today=0,
            decisions_today=0,
            executions_today=0,
            blocked_today=0,
            autowake_present=False,
            autowake_next_due_iso=None,
            plain_english_summary=(
                "Autonomous loop status is unknown — no autowake report, cycle "
                "report, event journal, or daily rollup was provided."
            ),
            diagnostic_hints=(
                "Provide at least one of: autowake report, latest cycle report, "
                "event journal, or daily learning rollup.",
            ),
        )

    last_cycle_dt, last_cycle_iso = _extract_last_cycle_at(
        latest_cycle_report, recent_event_journal
    )

    seconds_since = None
    if last_cycle_dt is not None:
        seconds_since = max(0.0, (now_utc - last_cycle_dt).total_seconds())

    autowake_present = autowake_report is not None
    autowake_next_due_iso, autowake_next_due_dt = _extract_autowake_next_due(
        autowake_report
    )

    cycles_today = _count_cycles_today(
        recent_event_journal, latest_cycle_report, now_utc, last_cycle_dt
    )
    decisions_today = _count_decisions_today(
        recent_event_journal, latest_cycle_report, daily_rollup, now_utc
    )
    executions_today = _count_executions_today(
        recent_event_journal, latest_cycle_report, now_utc
    )
    blocked_today = _count_blocked_today(
        recent_event_journal, latest_cycle_report, daily_rollup, now_utc
    )

    threshold_seconds = max(0, running_threshold_minutes) * 60.0

    overall_status = _classify_status(
        last_cycle_dt=last_cycle_dt,
        seconds_since=seconds_since,
        threshold_seconds=threshold_seconds,
        autowake_next_due_dt=autowake_next_due_dt,
        now_utc=now_utc,
    )

    diagnostic_hints = _diagnostic_hints(
        overall_status=overall_status,
        autowake_present=autowake_present,
        autowake_next_due_dt=autowake_next_due_dt,
        cycles_today=cycles_today,
        decisions_today=decisions_today,
        executions_today=executions_today,
        blocked_today=blocked_today,
        latest_cycle_report=latest_cycle_report,
        now_utc=now_utc,
    )

    plain_english_summary = _plain_english(
        overall_status=overall_status,
        seconds_since=seconds_since,
        cycles_today=cycles_today,
        decisions_today=decisions_today,
        executions_today=executions_today,
        autowake_next_due_iso=autowake_next_due_iso,
    )

    return AutonomousLoopHealth(
        overall_status=overall_status,
        last_cycle_at_iso=last_cycle_iso,
        seconds_since_last_cycle=seconds_since,
        cycles_today=cycles_today,
        decisions_today=decisions_today,
        executions_today=executions_today,
        blocked_today=blocked_today,
        autowake_present=autowake_present,
        autowake_next_due_iso=autowake_next_due_iso,
        plain_english_summary=plain_english_summary,
        diagnostic_hints=diagnostic_hints,
    )


# ---------------------------------------------------------------------------
# Classification + plain English
# ---------------------------------------------------------------------------


def _classify_status(
    *,
    last_cycle_dt: Optional[datetime],
    seconds_since: Optional[float],
    threshold_seconds: float,
    autowake_next_due_dt: Optional[datetime],
    now_utc: datetime,
) -> str:
    if last_cycle_dt is None:
        return STATUS_NEVER_STARTED

    if seconds_since is not None and seconds_since <= threshold_seconds:
        return STATUS_RUNNING

    # Older than threshold — if autowake has a future fire scheduled, the loop
    # is paced (just not currently mid-cycle).
    if autowake_next_due_dt is not None and autowake_next_due_dt > now_utc:
        return STATUS_RUNNING

    return STATUS_STALLED


def _plain_english(
    *,
    overall_status: str,
    seconds_since: Optional[float],
    cycles_today: int,
    decisions_today: int,
    executions_today: int,
    autowake_next_due_iso: Optional[str],
) -> str:
    if overall_status == STATUS_RUNNING:
        age = _format_age(seconds_since)
        next_due = (
            f" Next wake scheduled at {autowake_next_due_iso}."
            if autowake_next_due_iso
            else ""
        )
        return (
            f"Autonomous loop is running. Last cycle {age} ago; "
            f"{cycles_today} cycle(s), {decisions_today} decision(s), "
            f"{executions_today} execution(s) recorded today.{next_due}"
        )
    if overall_status == STATUS_STALLED:
        age = _format_age(seconds_since)
        return (
            f"Autonomous loop is stalled. Last cycle was {age} ago and no "
            f"future autowake fire is scheduled."
        )
    if overall_status == STATUS_NEVER_STARTED:
        return (
            "Autonomous loop has never started — no cycle reports exist in "
            "the supplied evidence."
        )
    return (
        "Autonomous loop status is unknown — no autowake report, cycle "
        "report, event journal, or daily rollup was provided."
    )


def _format_age(seconds_since: Optional[float]) -> str:
    if seconds_since is None:
        return "an unknown duration"
    if seconds_since < 60:
        return f"{int(seconds_since)} second(s)"
    if seconds_since < 3600:
        return f"{int(seconds_since // 60)} minute(s)"
    if seconds_since < 86400:
        return f"{int(seconds_since // 3600)} hour(s)"
    return f"{int(seconds_since // 86400)} day(s)"


def _diagnostic_hints(
    *,
    overall_status: str,
    autowake_present: bool,
    autowake_next_due_dt: Optional[datetime],
    cycles_today: int,
    decisions_today: int,
    executions_today: int,
    blocked_today: int,
    latest_cycle_report: Optional[Mapping[str, Any]],
    now_utc: datetime,
) -> tuple[str, ...]:
    if overall_status == STATUS_RUNNING:
        return ()

    hints: list[str] = []

    if overall_status == STATUS_NEVER_STARTED:
        hints.append(
            "No cycle reports found — start the agent loop (run a paper/demo "
            "agent cycle)."
        )
    elif overall_status == STATUS_STALLED:
        hints.append(
            "Most recent cycle is older than the running threshold and no "
            "future autowake fire is scheduled — restart the autowake runner."
        )

    if not autowake_present:
        hints.append("Autowake report missing — schedule a session.")
    elif autowake_next_due_dt is not None and autowake_next_due_dt <= now_utc:
        hints.append(
            "Autowake next-due timestamp is in the past — refresh the "
            "autowake schedule."
        )

    # MT5 cycle present but no executions today.
    if (
        latest_cycle_report is not None
        and cycles_today > 0
        and decisions_today > 0
        and executions_today == 0
    ):
        hints.append(
            "Cycle present but execution count 0 — check terminal "
            "AutoTrading."
        )

    # Validator rejections high.
    if decisions_today > 0 and blocked_today * 2 >= decisions_today:
        hints.append(
            f"Validator rejections high ({blocked_today}/{decisions_today} "
            f"today) — check runtime gates."
        )

    return tuple(hints)


# ---------------------------------------------------------------------------
# Extraction helpers (pure, defensive)
# ---------------------------------------------------------------------------


def _coerce_now(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _parse_iso_to_utc(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        # Accept trailing "Z".
        text = value.replace("Z", "+00:00") if value.endswith("Z") else value
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _to_utc_iso(value: Any) -> Optional[str]:
    parsed = _parse_iso_to_utc(value)
    if parsed is None:
        return None
    return parsed.isoformat()


def _extract_last_cycle_at(
    latest_cycle_report: Optional[Mapping[str, Any]],
    recent_event_journal: Optional[Sequence[Mapping[str, Any]]],
) -> tuple[Optional[datetime], Optional[str]]:
    """Return (parsed UTC datetime, normalised ISO string) for the most recent cycle."""

    candidates: list[tuple[datetime, str]] = []

    if isinstance(latest_cycle_report, Mapping):
        raw = latest_cycle_report.get("created_at") or latest_cycle_report.get(
            "as_of"
        )
        parsed = _parse_iso_to_utc(raw)
        if parsed is not None:
            candidates.append((parsed, parsed.isoformat()))

    if recent_event_journal:
        for event in recent_event_journal:
            if not isinstance(event, Mapping):
                continue
            event_type = str(event.get("event_type") or "")
            if event_type not in {
                "AGENT_CYCLE_STARTED",
                "AGENT_CYCLE_COMPLETED",
                "AGENT_CONTEXT_READY",
                "NEXT_CYCLE_ALLOWED",
            }:
                continue
            parsed = _parse_iso_to_utc(event.get("event_at") or event.get("created_at"))
            if parsed is not None:
                candidates.append((parsed, parsed.isoformat()))

    if not candidates:
        return None, None

    parsed, iso = max(candidates, key=lambda pair: pair[0])
    return parsed, iso


def _extract_autowake_next_due(
    autowake_report: Optional[Mapping[str, Any]],
) -> tuple[Optional[str], Optional[datetime]]:
    if not isinstance(autowake_report, Mapping):
        return None, None

    summary = autowake_report.get("summary") or {}

    # Preferred explicit field.
    for key in ("next_due_at", "next_due_iso", "next_due"):
        candidate = summary.get(key) if isinstance(summary, Mapping) else None
        parsed = _parse_iso_to_utc(candidate)
        if parsed is not None:
            return parsed.isoformat(), parsed

    # Top-level fallbacks the runner sometimes emits.
    for key in ("next_due_at", "next_due_iso", "next_due"):
        parsed = _parse_iso_to_utc(autowake_report.get(key))
        if parsed is not None:
            return parsed.isoformat(), parsed

    # Walk event_evaluations for a due_at on the first not-yet-fired event.
    for event in autowake_report.get("event_evaluations") or []:
        if not isinstance(event, Mapping):
            continue
        for key in ("due_at", "scheduled_at", "next_due_at"):
            parsed = _parse_iso_to_utc(event.get(key))
            if parsed is not None:
                return parsed.isoformat(), parsed

    return None, None


def _same_utc_date(value: datetime, now_utc: datetime) -> bool:
    return value.date() == now_utc.date()


def _count_cycles_today(
    recent_event_journal: Optional[Sequence[Mapping[str, Any]]],
    latest_cycle_report: Optional[Mapping[str, Any]],
    now_utc: datetime,
    last_cycle_dt: Optional[datetime],
) -> int:
    seen_cycle_ids: set[str] = set()
    count = 0

    if recent_event_journal:
        for event in recent_event_journal:
            if not isinstance(event, Mapping):
                continue
            if str(event.get("event_type") or "") != "AGENT_CYCLE_STARTED":
                continue
            parsed = _parse_iso_to_utc(event.get("event_at") or event.get("created_at"))
            if parsed is None or not _same_utc_date(parsed, now_utc):
                continue
            cycle_id = str(event.get("cycle_id") or f"_anon_{count}")
            if cycle_id in seen_cycle_ids:
                continue
            seen_cycle_ids.add(cycle_id)
            count += 1

    if count > 0:
        return count

    if (
        latest_cycle_report is not None
        and last_cycle_dt is not None
        and _same_utc_date(last_cycle_dt, now_utc)
    ):
        return 1
    return 0


def _journal_events_today(
    recent_event_journal: Optional[Sequence[Mapping[str, Any]]], now_utc: datetime
) -> Iterable[Mapping[str, Any]]:
    if not recent_event_journal:
        return ()
    out: list[Mapping[str, Any]] = []
    for event in recent_event_journal:
        if not isinstance(event, Mapping):
            continue
        parsed = _parse_iso_to_utc(event.get("event_at") or event.get("created_at"))
        if parsed is None or not _same_utc_date(parsed, now_utc):
            continue
        out.append(event)
    return out


def _count_decisions_today(
    recent_event_journal: Optional[Sequence[Mapping[str, Any]]],
    latest_cycle_report: Optional[Mapping[str, Any]],
    daily_rollup: Optional[Mapping[str, Any]],
    now_utc: datetime,
) -> int:
    journal_count = 0
    for event in _journal_events_today(recent_event_journal, now_utc):
        if str(event.get("event_type") or "") in {
            "ROUTE_INTENT_CREATED",
            "OVERSEER_DECISION_RECORDED",
        }:
            journal_count += 1
    if journal_count > 0:
        return journal_count

    if isinstance(daily_rollup, Mapping):
        summary = daily_rollup.get("summary") or {}
        approved = int(summary.get("approved_count") or 0)
        rejected = int(summary.get("rejected_count") or 0)
        if approved or rejected:
            return approved + rejected

    if isinstance(latest_cycle_report, Mapping):
        last_cycle_at = _parse_iso_to_utc(latest_cycle_report.get("created_at"))
        if last_cycle_at is not None and _same_utc_date(last_cycle_at, now_utc):
            summary = latest_cycle_report.get("summary") or {}
            approved = int(summary.get("approved_intent_count") or 0)
            rejected = int(summary.get("rejected_intent_count") or 0)
            return approved + rejected

    return 0


def _count_executions_today(
    recent_event_journal: Optional[Sequence[Mapping[str, Any]]],
    latest_cycle_report: Optional[Mapping[str, Any]],
    now_utc: datetime,
) -> int:
    count = 0
    for event in _journal_events_today(recent_event_journal, now_utc):
        if str(event.get("event_type") or "") in {
            "TERMINAL_COMMAND_DISPATCHED",
            "TERMINAL_RECEIPT_RECEIVED",
            "ORDER_EXECUTED",
        }:
            count += 1
    if count > 0:
        return count

    if isinstance(latest_cycle_report, Mapping):
        last_cycle_at = _parse_iso_to_utc(latest_cycle_report.get("created_at"))
        if last_cycle_at is not None and _same_utc_date(last_cycle_at, now_utc):
            summary = latest_cycle_report.get("summary") or {}
            return int(summary.get("terminal_command_count") or 0)

    return 0


def _count_blocked_today(
    recent_event_journal: Optional[Sequence[Mapping[str, Any]]],
    latest_cycle_report: Optional[Mapping[str, Any]],
    daily_rollup: Optional[Mapping[str, Any]],
    now_utc: datetime,
) -> int:
    blocked_event_types = {
        "VALIDATOR_REJECTED",
        "PCBA_BLOCKED",
        "CONFIRM_DECLINED",
        "OVERSEER_DECISION_REJECTED",
    }

    count = 0
    for event in _journal_events_today(recent_event_journal, now_utc):
        event_type = str(event.get("event_type") or "")
        status = str(event.get("status") or "")
        if event_type in blocked_event_types:
            count += 1
        elif event_type == "OVERSEER_DECISION_RECORDED" and status.upper() in {
            "REJECTED",
            "REJECT",
            "DECLINED",
        }:
            count += 1
        elif status.upper() in {"REJECTED", "REJECT", "DECLINED"} and (
            "VALIDATOR" in event_type or "PCBA" in event_type or "CONFIRM" in event_type
        ):
            count += 1
    if count > 0:
        return count

    if isinstance(daily_rollup, Mapping):
        summary = daily_rollup.get("summary") or {}
        rejected = int(summary.get("rejected_count") or 0)
        if rejected:
            return rejected

    if isinstance(latest_cycle_report, Mapping):
        last_cycle_at = _parse_iso_to_utc(latest_cycle_report.get("created_at"))
        if last_cycle_at is not None and _same_utc_date(last_cycle_at, now_utc):
            summary = latest_cycle_report.get("summary") or {}
            return int(summary.get("rejected_intent_count") or 0)

    return 0


# ---------------------------------------------------------------------------
# Optional I/O helper (kept separate so the summariser stays pure)
# ---------------------------------------------------------------------------


def load_loop_health_inputs(repo_root: Path | str) -> dict[str, Any]:
    """Load the latest evidence inputs for :func:`summarize_autonomous_loop_health`.

    This helper performs filesystem I/O. It is intentionally separate from the
    summariser so tests can construct dicts directly without going through
    disk. Missing or unreadable artifacts are silently treated as absent.
    """

    root = Path(repo_root)

    def _safe_load_latest(pattern: str) -> Optional[dict[str, Any]]:
        import json

        candidates = sorted(root.glob(pattern))
        if not candidates:
            return None
        try:
            return json.loads(candidates[-1].read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _safe_load_events(path: Path, limit: int = 1000) -> list[dict[str, Any]]:
        import json

        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return []
        for line in text.splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        return events

    autowake = _safe_load_latest(
        "evidence_runs/session_autowake_runner/session-autowake-*-report.json"
    )
    cycle = _safe_load_latest(
        "evidence_runs/agent_workflow_queue/agent-workflow-cycle-*-report.json"
    )
    if cycle is None:
        cycle = _safe_load_latest(
            "evidence_runs/agent_workflow_mt4_mailbox/agent-workflow-cycle-*-report.json"
        )
    rollup = _safe_load_latest(
        "evidence_runs/daily_learning_rollup/daily-learning-rollup-*-report.json"
    )
    events = _safe_load_events(
        root / "evidence_runs" / "agent_workflow_queue" / "agent-events.jsonl"
    )

    return {
        "autowake_report": autowake,
        "latest_cycle_report": cycle,
        "recent_event_journal": events,
        "daily_rollup": rollup,
    }
