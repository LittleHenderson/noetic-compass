"""Session autowake runner for the CAS Forex agent desk.

The workflow plan defines when the desk should wake. The daily rollup tells the
desk what state yesterday/current-day learning is in. This module joins those
two sources and decides whether CAS Forex should stand by, scout a session, run
micro-scalp/hourly loops, or write an end-of-day learning rollup.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from cas_forex.agent_state import (
    DEFAULT_MAILBOX_DIR,
    DEFAULT_OUTPUT_DIR as DEFAULT_CYCLE_OUTPUT_DIR,
    TERMINAL_LANE_MT4_MAILBOX,
)
from cas_forex.agent_workflow import (
    AgentWorkflowPlanError,
    build_agent_workflow_plan,
    load_latest_agent_workflow_plan_report,
)
from cas_forex.daily_learning_rollup import (
    DailyLearningRollupError,
    load_latest_daily_learning_rollup_report,
)
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "session_autowake_runner"
REPORT_KIND = "cas_forex_session_autowake_report"
EVENT_SCHEMA = "cas_forex_session_autowake_event.v1"
CLAIM_BOUNDARY = (
    "Session autowake runner decisions coordinate paper/demo market-session "
    "wakeups, agent-cycle requests, and loop cadence for CAS Forex. They do "
    "not by themselves execute live broker orders, create broker ACCEPT, "
    "deposit, withdraw, move bank/card funds, automate payouts, or override "
    "terminal receipt/history blockers."
)


class SessionAutowakeRunnerError(ValueError):
    """Raised when session autowake evidence cannot be built or loaded."""


def build_session_autowake_report(
    *,
    now: Optional[str | datetime] = None,
    workflow_plan: Optional[Mapping[str, Any]] = None,
    daily_learning_rollup: Optional[Mapping[str, Any]] = None,
    execute_cycle: bool = False,
    write_terminal_commands: bool = True,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    cycle_output_dir: Path | str = DEFAULT_CYCLE_OUTPUT_DIR,
    mailbox_dir: Path | str = DEFAULT_MAILBOX_DIR,
    terminal_lane: str = TERMINAL_LANE_MT4_MAILBOX,
    mt5_path: Optional[Path | str] = None,
    execute_mt5_demo_order: bool = False,
    confirm_mt5_demo_order: bool = False,
    run_mt5_deal_history: bool = True,
    mt5_future_minutes: int = 120,
    cycle_runner: Optional[Callable[..., Mapping[str, Any]]] = None,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Build and optionally persist one autowake evaluation."""

    plan = _load_workflow_plan(workflow_plan)
    rollup = _load_daily_rollup(daily_learning_rollup)
    now_dt = _parse_now(now)
    session = _session_state(now_dt)
    blockers = _terminal_blockers(rollup)
    events = build_autowake_events(plan, rollup, now_dt, session, blockers)
    executed_cycle = None
    if execute_cycle and _should_execute_cycle(events, session):
        executed_cycle = _run_cycle(
            cycle_runner=cycle_runner,
            output_dir=cycle_output_dir,
            mailbox_dir=mailbox_dir,
            write_terminal_commands=write_terminal_commands,
            terminal_lane=terminal_lane,
            mt5_path=mt5_path,
            execute_mt5_demo_order=execute_mt5_demo_order,
            confirm_mt5_demo_order=confirm_mt5_demo_order,
            run_mt5_deal_history=run_mt5_deal_history,
            mt5_future_minutes=mt5_future_minutes,
        )
    summary = _summary(events, session, blockers, rollup, executed_cycle)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "autowake_status": _autowake_status(summary, execute_cycle),
        "schema": EVENT_SCHEMA,
        "as_of": now_dt.isoformat(),
        "execution_mode": "AI_FULL_AUTO_PAPER",
        "workflow_plan_path": plan.get("report_path") or (plan.get("artifact_paths") or {}).get("json"),
        "daily_rollup_path": rollup.get("report_path") or (rollup.get("artifact_paths") or {}).get("json"),
        "output_dir": str(Path(output_dir)),
        "session_state": session,
        "summary": summary,
        "event_evaluations": events,
        "terminal_blockers": blockers,
        "executed_cycle": executed_cycle,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        paths = write_session_autowake_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_session_autowake_report(report)
    return report


def build_autowake_events(
    workflow_plan: Mapping[str, Any],
    daily_learning_rollup: Mapping[str, Any],
    now_dt: datetime,
    session: Mapping[str, Any],
    terminal_blockers: List[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Evaluate each workflow-plan wake event against the current session."""

    events: List[Dict[str, Any]] = []
    for event in (workflow_plan.get("autowake_schedule") or {}).get("events") or []:
        item = _evaluate_event(dict(event), daily_learning_rollup, now_dt, session, terminal_blockers)
        validate_session_autowake_event(item)
        events.append(item)
    return events


def write_session_autowake_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    """Write report JSON/Markdown plus JSONL event evaluations."""

    validate_session_autowake_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"session-autowake-{stamp}-report.json"
    md_path = target_dir / f"session-autowake-{stamp}-report.md"
    jsonl_path = target_dir / f"session-autowake-{stamp}.jsonl"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_session_autowake_markdown(report), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for event in report.get("event_evaluations") or []:
            handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
    return {"json": json_path, "markdown": md_path, "jsonl": jsonl_path}


def load_latest_session_autowake_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("session-autowake-*-report.json"))
    if not files:
        raise SessionAutowakeRunnerError(f"No session autowake reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_session_autowake_report(payload)
    return payload


def run_session_autowake_loop(
    *,
    iterations: int,
    interval_seconds: float,
    execute_cycle: bool = False,
    write_terminal_commands: bool = True,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    cycle_output_dir: Path | str = DEFAULT_CYCLE_OUTPUT_DIR,
    mailbox_dir: Path | str = DEFAULT_MAILBOX_DIR,
    terminal_lane: str = TERMINAL_LANE_MT4_MAILBOX,
    mt5_path: Optional[Path | str] = None,
    execute_mt5_demo_order: bool = False,
    confirm_mt5_demo_order: bool = False,
    run_mt5_deal_history: bool = True,
    mt5_future_minutes: int = 120,
) -> List[Dict[str, Any]]:
    """Run a bounded loop for schedulers/tests; callers can repeat externally."""

    if iterations < 1:
        raise SessionAutowakeRunnerError("iterations must be >= 1")
    reports: List[Dict[str, Any]] = []
    for index in range(iterations):
        reports.append(
            build_session_autowake_report(
                execute_cycle=execute_cycle,
                write_terminal_commands=write_terminal_commands,
                output_dir=output_dir,
                cycle_output_dir=cycle_output_dir,
                mailbox_dir=mailbox_dir,
                terminal_lane=terminal_lane,
                mt5_path=mt5_path,
                execute_mt5_demo_order=execute_mt5_demo_order,
                confirm_mt5_demo_order=confirm_mt5_demo_order,
                run_mt5_deal_history=run_mt5_deal_history,
                mt5_future_minutes=mt5_future_minutes,
            )
        )
        if index < iterations - 1:
            time.sleep(interval_seconds)
    return reports


def validate_session_autowake_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "autowake_status",
        "schema",
        "as_of",
        "execution_mode",
        "session_state",
        "summary",
        "event_evaluations",
        "terminal_blockers",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise SessionAutowakeRunnerError(f"session autowake report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise SessionAutowakeRunnerError("unexpected session autowake report_kind")
    if payload.get("schema") != EVENT_SCHEMA:
        raise SessionAutowakeRunnerError("unexpected session autowake schema")
    boundary = str(payload.get("claim_boundary", ""))
    if "do not by themselves execute live broker orders" not in boundary:
        raise SessionAutowakeRunnerError("session autowake claim boundary must preserve execution boundary")
    if "override terminal receipt/history blockers" not in boundary:
        raise SessionAutowakeRunnerError("session autowake claim boundary must preserve blocker boundary")
    if not isinstance(payload.get("event_evaluations"), list):
        raise SessionAutowakeRunnerError("event_evaluations must be a list")
    for event in payload.get("event_evaluations") or []:
        validate_session_autowake_event(event)


def validate_session_autowake_event(event: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "event_id",
        "action",
        "trigger",
        "purpose",
        "due",
        "status",
        "decision",
        "requested_agent_cycle",
        "terminal_blocked",
        "reasons",
        "claim_boundary",
    }
    missing = required.difference(event)
    if missing:
        raise SessionAutowakeRunnerError(f"session autowake event missing fields: {sorted(missing)}")
    if event.get("schema") != EVENT_SCHEMA:
        raise SessionAutowakeRunnerError("unexpected session autowake event schema")
    if "do not by themselves execute live broker orders" not in str(event.get("claim_boundary", "")):
        raise SessionAutowakeRunnerError("session autowake event claim boundary must preserve execution boundary")


def render_session_autowake_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    session = report.get("session_state") or {}
    lines = [
        "# CAS Forex Session Autowake Runner",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('autowake_status')}`",
        f"As of: `{report.get('as_of')}`",
        f"Session: `{session.get('active_session')}` market open `{session.get('market_open')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Events: `{summary.get('event_count')}`",
        f"- Due events: `{summary.get('due_event_count')}`",
        f"- Executable events: `{summary.get('executable_event_count')}`",
        f"- Executed cycles: `{summary.get('executed_cycle_count')}`",
        f"- Terminal blockers: `{summary.get('terminal_blocker_count')}`",
        f"- Pending receipts: `{summary.get('pending_receipt_count')}`",
        f"- Latest daily rollup readiness: `{summary.get('daily_rollup_readiness_label')}`",
        "",
        "## Events",
        "",
    ]
    for event in report.get("event_evaluations") or []:
        lines.append(
            "- "
            f"`{event.get('event_id')}` `{event.get('status')}`: "
            f"{event.get('decision')}"
        )
    lines.extend(["", "## Terminal Blockers", ""])
    for blocker in report.get("terminal_blockers") or []:
        lines.append(f"- `{blocker.get('blocker_id')}`: {blocker.get('plain_english')}")
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _evaluate_event(
    event: Mapping[str, Any],
    daily_learning_rollup: Mapping[str, Any],
    now_dt: datetime,
    session: Mapping[str, Any],
    terminal_blockers: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    event_id = str(event.get("event_id") or "")
    market_open = bool(session.get("market_open"))
    due = _event_due(event_id, now_dt, session)
    terminal_blocked = bool(terminal_blockers) and event_id in {
        "MICRO_SCALP_LOOP",
        "HOURLY_INTRADAY_LOOP",
        "END_OF_DAY_MEMORY_ROLLUP",
    }
    reasons = _event_reasons(event_id, due, market_open, session, terminal_blocked, daily_learning_rollup)
    if not market_open:
        status = "STANDBY_MARKET_CLOSED"
        decision = "Do not run trading agents while the FX market window is closed."
    elif not due:
        status = "STANDBY_NOT_DUE"
        decision = "No wake action is due in this minute."
    elif terminal_blocked and event_id in {"MICRO_SCALP_LOOP", "HOURLY_INTRADAY_LOOP"}:
        status = "DUE_WITH_TERMINAL_BLOCKERS"
        decision = "Wake the desk, but expect overseer/terminal blockers to prevent duplicate command expansion."
    else:
        status = "DUE_FOR_PAPER_AGENT_CYCLE"
        decision = "Wake CAS Forex and run the paper/demo agent loop cadence for this event."
    return {
        "schema": EVENT_SCHEMA,
        "event_id": event_id,
        "action": event.get("action"),
        "trigger": event.get("trigger"),
        "purpose": event.get("purpose"),
        "due": due,
        "status": status,
        "decision": decision,
        "requested_agent_cycle": bool(market_open and due),
        "terminal_blocked": terminal_blocked,
        "active_session": session.get("active_session"),
        "as_of": now_dt.isoformat(),
        "daily_rollup_status": daily_learning_rollup.get("rollup_status"),
        "reasons": reasons,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _event_due(event_id: str, now_dt: datetime, session: Mapping[str, Any]) -> bool:
    if not session.get("market_open"):
        return False
    minute = now_dt.minute
    hour = now_dt.hour
    weekday = now_dt.weekday()
    active_session = str(session.get("active_session") or "")
    if event_id == "FX_WEEK_OPEN_PRECHECK":
        return weekday == 6 and hour == 21 and minute >= 55
    if event_id == "SYDNEY_TOKYO_SESSION_SCOUT":
        return active_session == "ASIAN" and minute < 15
    if event_id == "LONDON_PREOPEN_SCOUT":
        return hour == 6 and minute >= 45
    if event_id == "NEW_YORK_PREOPEN_SCOUT":
        return hour == 12 and minute < 15
    if event_id == "MICRO_SCALP_LOOP":
        return minute % 5 == 0
    if event_id == "HOURLY_INTRADAY_LOOP":
        return minute == 0
    if event_id == "END_OF_DAY_MEMORY_ROLLUP":
        return hour == 21 and minute >= 50
    return False


def _event_reasons(
    event_id: str,
    due: bool,
    market_open: bool,
    session: Mapping[str, Any],
    terminal_blocked: bool,
    daily_learning_rollup: Mapping[str, Any],
) -> List[str]:
    reasons = [f"active_session={session.get('active_session')}", f"market_open={market_open}"]
    if due:
        reasons.append(f"{event_id} is due for this timestamp")
    else:
        reasons.append(f"{event_id} is not due for this timestamp")
    if terminal_blocked:
        reasons.append("latest daily rollup names terminal receipt/history blockers")
    readiness = (daily_learning_rollup.get("summary") or {}).get("readiness_label")
    if readiness:
        reasons.append(f"daily_rollup_readiness={readiness}")
    return reasons


def _session_state(now_dt: datetime) -> Dict[str, Any]:
    market_open = _market_is_open(now_dt)
    active_session = _active_session(now_dt) if market_open else "MARKET_CLOSED"
    return {
        "market_open": market_open,
        "active_session": active_session,
        "weekday": now_dt.strftime("%A").upper(),
        "utc_hour": now_dt.hour,
        "utc_minute": now_dt.minute,
        "timezone": "UTC",
        "market_week_reference": "Sunday 22:00 UTC through Friday 22:00 UTC",
    }


def _market_is_open(now_dt: datetime) -> bool:
    weekday = now_dt.weekday()
    hour = now_dt.hour
    if weekday == 5:
        return False
    if weekday == 6:
        return hour >= 22
    if weekday == 4:
        return hour < 22
    return True


def _active_session(now_dt: datetime) -> str:
    hour = now_dt.hour
    if 12 <= hour < 16:
        return "LONDON_NEW_YORK_OVERLAP"
    if 7 <= hour < 12:
        return "LONDON"
    if 16 <= hour < 21:
        return "NEW_YORK"
    if hour >= 22 or hour < 7:
        return "ASIAN"
    return "TRANSITION"


def _terminal_blockers(daily_learning_rollup: Mapping[str, Any]) -> List[Dict[str, Any]]:
    blockers = [
        dict(blocker)
        for blocker in daily_learning_rollup.get("terminal_blockers") or []
        if isinstance(blocker, Mapping)
    ]
    summary = daily_learning_rollup.get("summary") or {}
    if int(summary.get("pending_receipt_count") or 0) > 0 and not any(
        blocker.get("blocker_id") == "pending_terminal_receipts" for blocker in blockers
    ):
        blockers.append(
            {
                "blocker_id": "pending_terminal_receipts",
                "count": summary.get("pending_receipt_count"),
                "plain_english": "MT4/MT5 command rows are still waiting for terminal receipt JSON.",
            }
        )
    return blockers


def _should_execute_cycle(events: Iterable[Mapping[str, Any]], session: Mapping[str, Any]) -> bool:
    return bool(session.get("market_open")) and any(event.get("requested_agent_cycle") for event in events)


def _run_cycle(
    *,
    cycle_runner: Optional[Callable[..., Mapping[str, Any]]],
    output_dir: Path | str,
    mailbox_dir: Path | str,
    write_terminal_commands: bool,
    terminal_lane: str,
    mt5_path: Optional[Path | str],
    execute_mt5_demo_order: bool,
    confirm_mt5_demo_order: bool,
    run_mt5_deal_history: bool,
    mt5_future_minutes: int,
) -> Dict[str, Any]:
    runner = cycle_runner
    if runner is None:
        from cas_forex.agent_state import run_agent_workflow_cycle

        runner = run_agent_workflow_cycle
    cycle = dict(
        runner(
            output_dir=output_dir,
            mailbox_dir=mailbox_dir,
            trigger_source="SESSION_AUTOWAKE_RUNNER",
            write_terminal_commands=write_terminal_commands,
            terminal_lane=terminal_lane,
            mt5_path=mt5_path,
            execute_mt5_demo_order=execute_mt5_demo_order,
            confirm_mt5_demo_order=confirm_mt5_demo_order,
            run_mt5_deal_history=run_mt5_deal_history,
            mt5_future_minutes=mt5_future_minutes,
        )
    )
    return {
        "cycle_id": cycle.get("cycle_id"),
        "execution_mode": cycle.get("execution_mode"),
        "summary": cycle.get("summary"),
        "mt5_execution_loop": cycle.get("mt5_execution_loop"),
        "artifact_paths": cycle.get("artifact_paths"),
        "state_path": cycle.get("state_path"),
    }


def _summary(
    events: List[Mapping[str, Any]],
    session: Mapping[str, Any],
    terminal_blockers: List[Mapping[str, Any]],
    daily_learning_rollup: Mapping[str, Any],
    executed_cycle: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    due_events = [event for event in events if event.get("due")]
    executable_events = [event for event in due_events if event.get("requested_agent_cycle")]
    rollup_summary = daily_learning_rollup.get("summary") or {}
    return {
        "event_count": len(events),
        "due_event_count": len(due_events),
        "executable_event_count": len(executable_events),
        "executed_cycle_count": 1 if executed_cycle else 0,
        "market_open": bool(session.get("market_open")),
        "active_session": session.get("active_session"),
        "terminal_blocker_count": len(terminal_blockers),
        "pending_receipt_count": int(rollup_summary.get("pending_receipt_count") or 0),
        "closed_count": int(rollup_summary.get("closed_count") or 0),
        "daily_rollup_status": daily_learning_rollup.get("rollup_status"),
        "daily_rollup_readiness_label": rollup_summary.get("readiness_label"),
        "next_due_event_id": due_events[0].get("event_id") if due_events else None,
        "executed_cycle_id": executed_cycle.get("cycle_id") if executed_cycle else None,
        "executed_cycle_execution_mode": executed_cycle.get("execution_mode") if executed_cycle else None,
        "executed_cycle_mt5_loop_status": ((executed_cycle.get("mt5_execution_loop") or {}) or {}).get("loop_status") if executed_cycle else None,
        "executed_cycle_mt5_deal_history_status": ((((executed_cycle.get("mt5_execution_loop") or {}) or {}).get("deal_history_ingest") or {}) or {}).get("ingest_status") if executed_cycle else None,
        "executed_cycle_mt5_memory_update_count": int(
            (((((executed_cycle.get("mt5_execution_loop") or {}) or {}).get("deal_history_ingest") or {}) or {}).get("summary") or {}).get("memory_update_count") or 0
        ) if executed_cycle else 0,
    }


def _autowake_status(summary: Mapping[str, Any], execute_cycle: bool) -> str:
    if not summary.get("market_open"):
        return "SESSION_AUTOWAKE_STANDBY_MARKET_CLOSED"
    if execute_cycle and summary.get("executed_cycle_count"):
        return "SESSION_AUTOWAKE_CYCLE_EXECUTED"
    if summary.get("due_event_count"):
        return "SESSION_AUTOWAKE_READY"
    return "SESSION_AUTOWAKE_STANDBY_NOT_DUE"


def _next_action(summary: Mapping[str, Any]) -> str:
    if not summary.get("market_open"):
        return "Wait for the next FX market/session window, then rerun the autowake runner."
    if summary.get("pending_receipt_count"):
        return "Run the paper/demo cycle cadence, but resolve terminal receipts/history so repeated same-symbol commands can reconcile."
    if summary.get("executed_cycle_mt5_loop_status") == "MT5_DEMO_EXECUTION_DEAL_HISTORY_JOINED":
        return "Scheduled MT5 demo cycle executed and closed-deal history joined memory; keep the autowake loop active for the next session event."
    if summary.get("due_event_count"):
        return "Run the due paper/demo agent cycle and then rerun memory, queues, patch runner, daily rollup, and autowake."
    return "Keep the autowake loop active until the next micro-scalp, hourly, session, or end-of-day event is due."


def _load_workflow_plan(workflow_plan: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if workflow_plan is not None:
        return dict(workflow_plan)
    try:
        return load_latest_agent_workflow_plan_report()
    except AgentWorkflowPlanError:
        return build_agent_workflow_plan()


def _load_daily_rollup(daily_learning_rollup: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if daily_learning_rollup is not None:
        return dict(daily_learning_rollup)
    try:
        return load_latest_daily_learning_rollup_report()
    except DailyLearningRollupError:
        return {"summary": {}, "terminal_blockers": []}


def _parse_now(now: Optional[str | datetime]) -> datetime:
    if now is None:
        return utc_now()
    if isinstance(now, datetime):
        dt = now
    else:
        dt = datetime.fromisoformat(str(now).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
