"""End-of-day operator report composer.

This module sits ABOVE the existing :mod:`cas_forex.daily_learning_rollup`
and aggregates everything that HAPPENED during a single trading day into
one observational report the operator can read in 30 seconds:

* cycles fired (and their outcomes)
* decisions made (and their overall status counts)
* executions completed and closed P&L
* strategy promotions / demotions / walk-forward verdicts
* peak risk concentration during the day
* uvicorn / autowake / MT5 uptime signals
* notable incidents (loop stalls, MT5 disconnects, validator REJECT spikes,
  dispatch failures)

Design contract:

* :func:`compose_daily_report` is a *pure* function. It does not touch the
  filesystem. Callers pass in already-parsed dicts (any may be ``None`` or
  empty); missing inputs become "no activity" sections, never fabricated.
* The composed text is strictly OBSERVATIONAL — it reports what happened
  and never advises trades or implies a better course of action. The list
  of forbidden advisory phrases is enforced by tests.
* :func:`load_daily_report_inputs` is the production disk loader. Tests
  should construct the input dicts directly.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence


__all__ = [
    "DailySection",
    "DailyReport",
    "compose_daily_report",
    "load_daily_report_inputs",
]


# Sections produced, in canonical display order.
SECTION_NAMES: tuple[str, ...] = (
    "cycles",
    "decisions",
    "executions",
    "strategies",
    "risk",
    "system",
    "incidents",
)


@dataclass(frozen=True)
class DailySection:
    """One observational section of the end-of-day operator report."""

    section_name: str
    headline: str
    detail: str
    metrics: Mapping[str, Any]
    notable_events: tuple[str, ...]


@dataclass(frozen=True)
class DailyReport:
    """Structured end-of-day operator report.

    Observational only. Never contains advisory phrasing.
    """

    report_date: str
    generated_at_iso: str
    overall_headline: str
    plain_english_summary: str
    sections: tuple[DailySection, ...]
    diagnostic_hints: tuple[str, ...]


# ---------------------------------------------------------------------------
# Public composer
# ---------------------------------------------------------------------------


def compose_daily_report(
    *,
    report_date: str,
    daily_rollup: Optional[Mapping[str, Any]] = None,
    cycle_reports: Optional[Sequence[Mapping[str, Any]]] = None,
    event_journal: Optional[Sequence[Mapping[str, Any]]] = None,
    live_telemetry_snapshots: Optional[Sequence[Mapping[str, Any]]] = None,
    risk_snapshots: Optional[Sequence[Mapping[str, Any]]] = None,
    system_health_snapshots: Optional[Sequence[Mapping[str, Any]]] = None,
    now: Optional[datetime] = None,
) -> DailyReport:
    """Compose a structured end-of-day report from already-parsed inputs.

    Any missing input → corresponding section reports "no activity" and
    metrics stay at zero. The function NEVER fabricates a count, status,
    or timestamp.
    """

    now_utc = _coerce_now(now)
    generated_at_iso = now_utc.isoformat()
    safe_date = _safe_date_string(report_date, now=now_utc)

    cycles = _normalize_seq(cycle_reports)
    events = _normalize_seq(event_journal)
    live_snaps = _normalize_seq(live_telemetry_snapshots)
    risk_snaps = _normalize_seq(risk_snapshots)
    sys_snaps = _normalize_seq(system_health_snapshots)

    cycles_section = _build_cycles_section(cycles)
    decisions_section, top_block_reason = _build_decisions_section(cycles)
    executions_section, exec_metrics = _build_executions_section(
        daily_rollup if isinstance(daily_rollup, Mapping) else None
    )
    strategies_section = _build_strategies_section(events)
    risk_section = _build_risk_section(live_snaps, risk_snaps)
    system_section, system_incidents = _build_system_section(sys_snaps, events)
    incidents_section = _build_incidents_section(events, system_incidents)

    sections: tuple[DailySection, ...] = (
        cycles_section,
        decisions_section,
        executions_section,
        strategies_section,
        risk_section,
        system_section,
        incidents_section,
    )

    diagnostic_hints = _build_diagnostic_hints(
        cycles_section=cycles_section,
        decisions_section=decisions_section,
        system_section=system_section,
        incidents_section=incidents_section,
        top_block_reason=top_block_reason,
    )

    overall_headline = _build_overall_headline(
        report_date=safe_date,
        cycles_section=cycles_section,
        executions_section=executions_section,
        exec_metrics=exec_metrics,
        incidents_section=incidents_section,
        system_section=system_section,
    )

    summary = _build_plain_english_summary(
        report_date=safe_date,
        cycles_section=cycles_section,
        decisions_section=decisions_section,
        executions_section=executions_section,
        exec_metrics=exec_metrics,
        strategies_section=strategies_section,
        risk_section=risk_section,
        system_section=system_section,
        incidents_section=incidents_section,
    )

    return DailyReport(
        report_date=safe_date,
        generated_at_iso=generated_at_iso,
        overall_headline=overall_headline,
        plain_english_summary=summary,
        sections=sections,
        diagnostic_hints=diagnostic_hints,
    )


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _build_cycles_section(cycles: Sequence[Mapping[str, Any]]) -> DailySection:
    total = len(cycles)
    outcomes: Counter[str] = Counter()
    consecutive_blocked_streaks: list[tuple[str, int]] = []
    current_streak = 0
    current_cycle_id: Optional[str] = None

    for cycle in cycles:
        outcome = _classify_cycle_outcome(cycle)
        outcomes[outcome] += 1

        intents_blocked = _count_blocked_intents(cycle)
        if intents_blocked >= 5:
            cid = str(cycle.get("cycle_id") or "")
            consecutive_blocked_streaks.append((cid, intents_blocked))

        # rolling "all blocked" streak
        if outcome == "blocked":
            current_streak += 1
            current_cycle_id = str(cycle.get("cycle_id") or current_cycle_id or "")
        else:
            current_streak = 0
            current_cycle_id = None

    notable: list[str] = []
    for cid, n in consecutive_blocked_streaks:
        notable.append(f"Cycle {cid or '<unknown>'} had {n} blocked intents.")

    metrics = {
        "total_cycles": total,
        "executed": int(outcomes.get("executed", 0)),
        "approved_not_executed": int(outcomes.get("approved_not_executed", 0)),
        "blocked": int(outcomes.get("blocked", 0)),
        "no_intent": int(outcomes.get("no_intent", 0)),
    }

    if total == 0:
        headline = "No cycles recorded today."
        detail = "The autonomous workflow produced no cycle reports for the day."
    else:
        headline = (
            f"{total} cycle(s) fired today "
            f"({metrics['executed']} executed, "
            f"{metrics['approved_not_executed']} approved, "
            f"{metrics['blocked']} blocked, "
            f"{metrics['no_intent']} no-intent)."
        )
        detail = (
            f"Across the day the workflow recorded {total} cycle(s). "
            f"{metrics['executed']} cycle(s) produced an execution path, "
            f"{metrics['approved_not_executed']} approved without execution, "
            f"{metrics['blocked']} were fully blocked, and "
            f"{metrics['no_intent']} produced no route intent."
        )

    return DailySection(
        section_name="cycles",
        headline=headline,
        detail=detail,
        metrics=metrics,
        notable_events=tuple(notable),
    )


def _build_decisions_section(
    cycles: Sequence[Mapping[str, Any]],
) -> tuple[DailySection, Optional[str]]:
    overall_counts: Counter[str] = Counter()
    block_reasons: Counter[str] = Counter()
    total_decisions = 0

    for cycle in cycles:
        decisions = cycle.get("overseer_decisions")
        if not isinstance(decisions, list):
            continue
        for decision in decisions:
            if not isinstance(decision, Mapping):
                continue
            total_decisions += 1
            status = str(decision.get("decision") or "UNKNOWN")
            overall_counts[status] += 1
            if not decision.get("approved", False):
                for reason in decision.get("reasons", []) or []:
                    block_reasons[str(reason)] += 1

    top_block_reason: Optional[str] = None
    if block_reasons:
        top_block_reason = block_reasons.most_common(1)[0][0]

    metrics = {
        "total_decisions": total_decisions,
        "by_status": dict(overall_counts),
        "top_blocking_reason": top_block_reason,
    }

    notable: list[str] = []
    if top_block_reason:
        notable.append(f"Top blocking reason observed: {top_block_reason}")

    if total_decisions == 0:
        headline = "No overseer decisions recorded today."
        detail = "No cycles produced overseer decisions for the day."
    else:
        top_status = overall_counts.most_common(1)[0][0] if overall_counts else "UNKNOWN"
        headline = (
            f"{total_decisions} decision(s) recorded; most common status: {top_status}."
        )
        detail = (
            f"The overseer recorded {total_decisions} decision(s) across the day's cycles. "
            f"The most frequent decision status was {top_status}."
        )

    return (
        DailySection(
            section_name="decisions",
            headline=headline,
            detail=detail,
            metrics=metrics,
            notable_events=tuple(notable),
        ),
        top_block_reason,
    )


def _build_executions_section(
    daily_rollup: Optional[Mapping[str, Any]],
) -> tuple[DailySection, dict[str, Any]]:
    total_executions = 0
    total_pnl = 0.0
    top_winning: Optional[tuple[str, float]] = None
    top_losing: Optional[tuple[str, float]] = None

    if isinstance(daily_rollup, Mapping):
        by_strategy = daily_rollup.get("by_strategy")
        if isinstance(by_strategy, list):
            for entry in by_strategy:
                if not isinstance(entry, Mapping):
                    continue
                closed_count = _safe_int(entry.get("closed_count"))
                pnl = _safe_float(entry.get("net_profit_loss_account"))
                total_executions += closed_count
                total_pnl += pnl
                key = str(entry.get("key") or "")
                if not key:
                    continue
                if pnl > 0 and (top_winning is None or pnl > top_winning[1]):
                    top_winning = (key, pnl)
                if pnl < 0 and (top_losing is None or pnl < top_losing[1]):
                    top_losing = (key, pnl)

    total_pnl = round(total_pnl, 2)

    metrics: dict[str, Any] = {
        "total_executions": total_executions,
        "net_pnl": total_pnl,
        "top_winning_strategy": top_winning[0] if top_winning else None,
        "top_winning_pnl": round(top_winning[1], 2) if top_winning else 0.0,
        "top_losing_strategy": top_losing[0] if top_losing else None,
        "top_losing_pnl": round(top_losing[1], 2) if top_losing else 0.0,
    }

    notable: list[str] = []
    if top_winning is not None:
        notable.append(
            f"Top winning strategy: {top_winning[0]} (+{top_winning[1]:.2f})."
        )
    if top_losing is not None:
        notable.append(
            f"Top losing strategy: {top_losing[0]} ({top_losing[1]:.2f})."
        )

    if total_executions == 0 and total_pnl == 0.0:
        headline = "No closed executions recorded today."
        detail = "No closed-trade activity is on record from the daily learning rollup."
    else:
        headline = (
            f"{total_executions} closed execution(s); net P&L {total_pnl:+.2f}."
        )
        detail = (
            f"The daily learning rollup recorded {total_executions} closed execution(s). "
            f"Net realized P&L from those executions stands at {total_pnl:+.2f}."
        )

    return (
        DailySection(
            section_name="executions",
            headline=headline,
            detail=detail,
            metrics=metrics,
            notable_events=tuple(notable),
        ),
        metrics,
    )


def _build_strategies_section(
    events: Sequence[Mapping[str, Any]],
) -> DailySection:
    promotions = 0
    demotions = 0
    walk_forward_verdicts: Counter[str] = Counter()
    notable: list[str] = []

    for event in events:
        etype = str(event.get("event_type") or "").upper()
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        if "PROMOTE" in etype or "PROMOTION" in etype:
            promotions += 1
            target = str(payload.get("strategy") or payload.get("name") or "")
            if target:
                notable.append(f"Strategy promoted: {target}.")
        elif "DEMOTE" in etype or "DEMOTION" in etype:
            demotions += 1
            target = str(payload.get("strategy") or payload.get("name") or "")
            if target:
                notable.append(f"Strategy demoted: {target}.")
        if "WALK_FORWARD" in etype or "WALKFORWARD" in etype:
            verdict = str(payload.get("verdict") or payload.get("status") or "UNKNOWN")
            walk_forward_verdicts[verdict] += 1

    metrics = {
        "promotions": promotions,
        "demotions": demotions,
        "walk_forward_verdicts": dict(walk_forward_verdicts),
    }

    total_movement = promotions + demotions + sum(walk_forward_verdicts.values())

    if total_movement == 0:
        headline = "No strategy promotions, demotions, or walk-forward verdicts today."
        detail = (
            "The event journal carried no strategy promotion, demotion, or "
            "walk-forward verdict messages for the day."
        )
    else:
        headline = (
            f"{promotions} promotion(s), {demotions} demotion(s), "
            f"{sum(walk_forward_verdicts.values())} walk-forward verdict(s)."
        )
        detail = (
            f"The event journal recorded {promotions} strategy promotion(s) and "
            f"{demotions} demotion(s), plus "
            f"{sum(walk_forward_verdicts.values())} walk-forward verdict event(s)."
        )

    return DailySection(
        section_name="strategies",
        headline=headline,
        detail=detail,
        metrics=metrics,
        notable_events=tuple(notable),
    )


def _build_risk_section(
    live_snaps: Sequence[Mapping[str, Any]],
    risk_snaps: Sequence[Mapping[str, Any]],
) -> DailySection:
    peak_concentration = 0.0
    peak_margin_util = 0.0
    max_float_loss = 0.0
    max_float_gain = 0.0
    samples_seen = 0

    for snap in live_snaps:
        if not isinstance(snap, Mapping):
            continue
        samples_seen += 1
        totals = snap.get("totals") if isinstance(snap.get("totals"), Mapping) else {}
        floating = _safe_float(totals.get("total_floating_pnl"))
        if floating < max_float_loss:
            max_float_loss = floating
        if floating > max_float_gain:
            max_float_gain = floating

    for snap in risk_snaps:
        if not isinstance(snap, Mapping):
            continue
        samples_seen += 1
        conc = _safe_float(snap.get("peak_concentration") or snap.get("concentration"))
        if conc > peak_concentration:
            peak_concentration = conc
        margin = _safe_float(
            snap.get("peak_margin_utilization") or snap.get("margin_utilization")
        )
        if margin > peak_margin_util:
            peak_margin_util = margin
        floating_loss = _safe_float(snap.get("max_floating_loss"))
        if floating_loss < max_float_loss:
            max_float_loss = floating_loss
        floating_gain = _safe_float(snap.get("max_floating_gain"))
        if floating_gain > max_float_gain:
            max_float_gain = floating_gain

    metrics = {
        "peak_concentration": round(peak_concentration, 4),
        "peak_margin_utilization": round(peak_margin_util, 4),
        "max_floating_loss": round(max_float_loss, 2),
        "max_floating_gain": round(max_float_gain, 2),
        "samples_observed": samples_seen,
    }

    if samples_seen == 0:
        headline = "No risk telemetry observed today."
        detail = "No live telemetry or risk-monitor snapshots were recorded for the day."
    else:
        headline = (
            f"Peak concentration {peak_concentration:.2f}; "
            f"peak margin utilization {peak_margin_util:.2f}; "
            f"floating P&L range {max_float_loss:+.2f}..{max_float_gain:+.2f}."
        )
        detail = (
            f"Across {samples_seen} telemetry sample(s) the peak position "
            f"concentration reached {peak_concentration:.2f} and the peak "
            f"margin utilization reached {peak_margin_util:.2f}. The floating "
            f"P&L observed swung between {max_float_loss:+.2f} and "
            f"{max_float_gain:+.2f}."
        )

    return DailySection(
        section_name="risk",
        headline=headline,
        detail=detail,
        metrics=metrics,
        notable_events=tuple(),
    )


def _build_system_section(
    sys_snaps: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
) -> tuple[DailySection, list[str]]:
    uvicorn_uptime_pct = 0.0
    autowake_uptime_pct = 0.0
    mt5_disconnect_events = 0
    samples = 0
    uvicorn_up = 0
    autowake_up = 0
    incidents: list[str] = []

    for snap in sys_snaps:
        if not isinstance(snap, Mapping):
            continue
        samples += 1
        if bool(snap.get("uvicorn_up") or snap.get("uvicorn_running")):
            uvicorn_up += 1
        if bool(snap.get("autowake_up") or snap.get("autowake_running")):
            autowake_up += 1
        if snap.get("mt5_disconnected") or snap.get("mt5_status") == "DISCONNECTED":
            mt5_disconnect_events += 1
            ts = snap.get("timestamp") or snap.get("captured_at")
            incidents.append(
                f"MT5 disconnected at {ts}."
                if ts
                else "MT5 disconnected during a system-health snapshot."
            )

    # Also surface explicit MT5 disconnect events from the event journal.
    for event in events:
        etype = str(event.get("event_type") or "").upper()
        if "MT5_DISCONNECT" in etype or "MT5_DISCONNECTED" in etype:
            mt5_disconnect_events += 1
            ts = event.get("created_at") or event.get("timestamp")
            incidents.append(
                f"MT5 disconnected event at {ts}." if ts else "MT5 disconnected event observed."
            )

    if samples > 0:
        uvicorn_uptime_pct = round(uvicorn_up / samples, 4)
        autowake_uptime_pct = round(autowake_up / samples, 4)

    metrics = {
        "samples_observed": samples,
        "uvicorn_uptime_pct": uvicorn_uptime_pct,
        "autowake_uptime_pct": autowake_uptime_pct,
        "mt5_disconnect_events": mt5_disconnect_events,
    }

    if samples == 0 and mt5_disconnect_events == 0:
        headline = "No system-health telemetry observed today."
        detail = "No system-health snapshots were recorded for the day."
    else:
        headline = (
            f"uvicorn uptime {uvicorn_uptime_pct * 100:.0f}%; "
            f"autowake uptime {autowake_uptime_pct * 100:.0f}%; "
            f"{mt5_disconnect_events} MT5 disconnect event(s)."
        )
        detail = (
            f"Across {samples} system-health sample(s), uvicorn was observed "
            f"running on {uvicorn_uptime_pct * 100:.0f}% of samples and the "
            f"autowake supervisor on {autowake_uptime_pct * 100:.0f}%. "
            f"{mt5_disconnect_events} MT5 disconnect event(s) were recorded."
        )

    return (
        DailySection(
            section_name="system",
            headline=headline,
            detail=detail,
            metrics=metrics,
            notable_events=tuple(),
        ),
        incidents,
    )


def _build_incidents_section(
    events: Sequence[Mapping[str, Any]],
    system_incidents: Sequence[str],
) -> DailySection:
    loop_stalls = 0
    validator_rejects = 0
    dispatch_failures = 0
    notable: list[str] = list(system_incidents)

    for event in events:
        etype = str(event.get("event_type") or "").upper()
        ts = event.get("created_at") or event.get("timestamp")
        if "LOOP_STALL" in etype or "LOOP_STALLED" in etype:
            loop_stalls += 1
            notable.append(
                f"Loop stall detected at {ts}." if ts else "Loop stall detected."
            )
        elif "VALIDATOR_REJECT" in etype or "VALIDATOR_REJECTED" in etype:
            validator_rejects += 1
        elif "DISPATCH_FAIL" in etype or "DISPATCH_FAILED" in etype:
            dispatch_failures += 1
            notable.append(
                f"Dispatch failure at {ts}." if ts else "Dispatch failure observed."
            )

    metrics = {
        "loop_stalls": loop_stalls,
        "validator_rejects": validator_rejects,
        "dispatch_failures": dispatch_failures,
        "mt5_incidents_observed": sum(
            1 for inc in system_incidents if "MT5" in inc.upper()
        ),
    }

    total_incidents = (
        loop_stalls
        + validator_rejects
        + dispatch_failures
        + len(system_incidents)
    )

    if total_incidents == 0:
        headline = "No notable incidents observed today."
        detail = (
            "No loop stalls, validator-REJECT spikes, dispatch failures, or "
            "MT5 disconnect incidents were recorded."
        )
    else:
        headline = (
            f"{loop_stalls} loop stall(s); {validator_rejects} validator REJECT(s); "
            f"{dispatch_failures} dispatch failure(s); "
            f"{metrics['mt5_incidents_observed']} MT5 incident(s)."
        )
        detail = (
            f"The event journal carried {loop_stalls} loop stall event(s), "
            f"{validator_rejects} validator REJECT event(s), and "
            f"{dispatch_failures} dispatch-failure event(s). "
            f"{metrics['mt5_incidents_observed']} MT5 incident(s) surfaced from system health."
        )

    return DailySection(
        section_name="incidents",
        headline=headline,
        detail=detail,
        metrics=metrics,
        notable_events=tuple(notable),
    )


# ---------------------------------------------------------------------------
# Headline + summary + hints
# ---------------------------------------------------------------------------


def _build_overall_headline(
    *,
    report_date: str,
    cycles_section: DailySection,
    executions_section: DailySection,
    exec_metrics: Mapping[str, Any],
    incidents_section: DailySection,
    system_section: DailySection,
) -> str:
    cm = cycles_section.metrics
    total_cycles = int(cm.get("total_cycles", 0))
    executions = int(exec_metrics.get("total_executions", 0))
    blocked = int(cm.get("blocked", 0))
    net_pnl = float(exec_metrics.get("net_pnl", 0.0))
    im = incidents_section.metrics
    incident_total = (
        int(im.get("loop_stalls", 0))
        + int(im.get("dispatch_failures", 0))
        + int(im.get("mt5_incidents_observed", 0))
    )
    if total_cycles == 0 and executions == 0 and incident_total == 0:
        health_phrase = "no activity recorded"
    elif incident_total == 0:
        health_phrase = "system healthy throughout"
    else:
        health_phrase = f"{incident_total} incident(s) recorded"
    return (
        f"{report_date}: {total_cycles} cycle(s), {executions} execution(s), "
        f"{blocked} blocked, net {net_pnl:+.2f} — {health_phrase}."
    )


def _build_plain_english_summary(
    *,
    report_date: str,
    cycles_section: DailySection,
    decisions_section: DailySection,
    executions_section: DailySection,
    exec_metrics: Mapping[str, Any],
    strategies_section: DailySection,
    risk_section: DailySection,
    system_section: DailySection,
    incidents_section: DailySection,
) -> str:
    cm = cycles_section.metrics
    dm = decisions_section.metrics
    rm = risk_section.metrics
    sm = system_section.metrics
    im = incidents_section.metrics
    stm = strategies_section.metrics

    sentences: list[str] = []

    sentences.append(
        f"On {report_date} the autonomous workflow ran "
        f"{int(cm.get('total_cycles', 0))} cycle(s)."
    )
    sentences.append(
        f"{int(dm.get('total_decisions', 0))} overseer decision(s) were recorded "
        f"across those cycles."
    )
    sentences.append(
        f"{int(exec_metrics.get('total_executions', 0))} closed execution(s) "
        f"produced a net P&L of {float(exec_metrics.get('net_pnl', 0.0)):+.2f}."
    )

    promotions = int(stm.get("promotions", 0))
    demotions = int(stm.get("demotions", 0))
    if promotions or demotions:
        sentences.append(
            f"Strategy roster activity: {promotions} promotion(s) and "
            f"{demotions} demotion(s)."
        )
    else:
        sentences.append("No strategy promotions or demotions were recorded.")

    sentences.append(
        f"Peak position concentration reached {float(rm.get('peak_concentration', 0.0)):.2f} "
        f"and floating P&L spanned "
        f"{float(rm.get('max_floating_loss', 0.0)):+.2f}..{float(rm.get('max_floating_gain', 0.0)):+.2f}."
    )

    samples = int(sm.get("samples_observed", 0))
    if samples > 0:
        sentences.append(
            f"System health was sampled {samples} time(s); uvicorn was up on "
            f"{float(sm.get('uvicorn_uptime_pct', 0.0)) * 100:.0f}% of samples."
        )
    else:
        sentences.append("No system-health samples were captured.")

    incident_total = (
        int(im.get("loop_stalls", 0))
        + int(im.get("dispatch_failures", 0))
        + int(im.get("mt5_incidents_observed", 0))
        + int(im.get("validator_rejects", 0))
    )
    if incident_total == 0:
        sentences.append("No notable incidents were observed.")
    else:
        sentences.append(
            f"{incident_total} notable event(s) surfaced in the incidents log "
            f"(loop stalls, validator REJECTs, dispatch failures, or MT5 disconnects)."
        )

    return " ".join(sentences)


def _build_diagnostic_hints(
    *,
    cycles_section: DailySection,
    decisions_section: DailySection,
    system_section: DailySection,
    incidents_section: DailySection,
    top_block_reason: Optional[str],
) -> tuple[str, ...]:
    hints: list[str] = []
    im = incidents_section.metrics
    sm = system_section.metrics

    loop_stalls = int(im.get("loop_stalls", 0))
    if loop_stalls > 0:
        hints.append(f"Loop stalled {loop_stalls} time(s) today.")

    mt5_events = int(sm.get("mt5_disconnect_events", 0))
    if mt5_events > 0:
        hints.append(f"MT5 disconnected {mt5_events} time(s) during the day.")

    validator_rejects = int(im.get("validator_rejects", 0))
    if validator_rejects >= 10:
        hint = f"Validator REJECTed {validator_rejects} intents today."
        if top_block_reason:
            hint += f" Top blocking reason: {top_block_reason}."
        hints.append(hint)

    dispatch_failures = int(im.get("dispatch_failures", 0))
    if dispatch_failures > 0:
        hints.append(
            f"Dispatch failures observed {dispatch_failures} time(s) today."
        )

    cm = cycles_section.metrics
    if int(cm.get("blocked", 0)) >= 5 and int(cm.get("executed", 0)) == 0:
        hints.append("All cycles today were blocked; no executions recorded.")

    return tuple(hints)


# ---------------------------------------------------------------------------
# Classifiers and helpers
# ---------------------------------------------------------------------------


def _classify_cycle_outcome(cycle: Mapping[str, Any]) -> str:
    """Return one of: executed | approved_not_executed | blocked | no_intent."""

    decisions = cycle.get("overseer_decisions")
    if not isinstance(decisions, list) or not decisions:
        return "no_intent"

    approved = [d for d in decisions if isinstance(d, Mapping) and d.get("approved")]
    rejected = [
        d
        for d in decisions
        if isinstance(d, Mapping) and not d.get("approved")
    ]
    command_ready = any(
        isinstance(d, Mapping) and d.get("command_ready") for d in decisions
    )

    if approved and command_ready:
        return "executed"
    if approved and not command_ready:
        return "approved_not_executed"
    if rejected and not approved:
        return "blocked"
    return "no_intent"


def _count_blocked_intents(cycle: Mapping[str, Any]) -> int:
    decisions = cycle.get("overseer_decisions")
    if not isinstance(decisions, list):
        return 0
    return sum(
        1
        for d in decisions
        if isinstance(d, Mapping) and not d.get("approved", False)
    )


def _normalize_seq(value: Any) -> Sequence[Mapping[str, Any]]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(v for v in value if isinstance(v, Mapping))


def _coerce_now(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _safe_date_string(value: Any, now: Optional[datetime] = None) -> str:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, date):
        return value.isoformat()
    # Fall back to the injected reference time (not real wall-clock today), so
    # the report date is deterministic for a given ``now``.
    return _coerce_now(now).strftime("%Y-%m-%d")


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
# Disk loader
# ---------------------------------------------------------------------------


def load_daily_report_inputs(
    repo_root: Path | str, report_date: str
) -> dict[str, Any]:
    """Load all evidence inputs scoped to ``report_date``.

    Missing artifacts become ``None`` or empty lists; this loader never
    raises. Tests should NOT use this helper; they should build the input
    dicts directly.

    Scanned locations (relative to ``repo_root``):

    * ``evidence_runs/daily_learning_rollup/daily-learning-rollup-<date>*.json``
      (latest match wins)
    * ``evidence_runs/agent_workflow_queue/agent-workflow-cycle-<date>*.json``
    * ``evidence_runs/agent_workflow_queue/agent-events.jsonl``
      (filtered to rows whose ``created_at`` / ``timestamp`` starts with the
      compact YYYYMMDD form of the date)
    * ``evidence_runs/live_telemetry/*<date>*.json``
    * ``evidence_runs/risk_monitoring/*<date>*.json``
    * ``evidence_runs/system_health/*<date>*.json``
    """

    root = Path(repo_root)
    compact = report_date.replace("-", "") if isinstance(report_date, str) else ""
    iso_prefix = report_date if isinstance(report_date, str) else ""

    daily_rollup = _read_first_json(
        root / "evidence_runs" / "daily_learning_rollup",
        f"daily-learning-rollup-{compact}*-report.json",
    )

    cycle_reports = list(
        _read_all_json(
            root / "evidence_runs" / "agent_workflow_queue",
            f"agent-workflow-cycle-{compact}*-report.json",
        )
    )

    event_journal = list(
        _read_jsonl_filtered_by_date(
            root / "evidence_runs" / "agent_workflow_queue" / "agent-events.jsonl",
            iso_prefix=iso_prefix,
            compact_prefix=compact,
        )
    )

    live_telemetry_snapshots = list(
        _read_all_json(
            root / "evidence_runs" / "live_telemetry",
            f"*{compact}*.json",
        )
    )

    risk_snapshots = list(
        _read_all_json(
            root / "evidence_runs" / "risk_monitoring",
            f"*{compact}*.json",
        )
    )

    system_health_snapshots = list(
        _read_all_json(
            root / "evidence_runs" / "system_health",
            f"*{compact}*.json",
        )
    )

    return {
        "daily_rollup": daily_rollup,
        "cycle_reports": cycle_reports,
        "event_journal": event_journal,
        "live_telemetry_snapshots": live_telemetry_snapshots,
        "risk_snapshots": risk_snapshots,
        "system_health_snapshots": system_health_snapshots,
    }


def _read_first_json(directory: Path, pattern: str) -> Optional[dict[str, Any]]:
    try:
        if not directory.exists():
            return None
        matches = sorted(directory.glob(pattern))
        for path in reversed(matches):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, Mapping):
                    return dict(data)
            except Exception:
                continue
    except Exception:
        return None
    return None


def _read_all_json(directory: Path, pattern: str) -> Iterable[dict[str, Any]]:
    try:
        if not directory.exists():
            return ()
        results: list[dict[str, Any]] = []
        for path in sorted(directory.glob(pattern)):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, Mapping):
                    results.append(dict(data))
            except Exception:
                continue
        return results
    except Exception:
        return ()


def _read_jsonl_filtered_by_date(
    path: Path, *, iso_prefix: str, compact_prefix: str
) -> Iterable[dict[str, Any]]:
    try:
        if not path.exists():
            return ()
        results: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if not isinstance(row, Mapping):
                    continue
                ts = str(row.get("created_at") or row.get("timestamp") or "")
                if iso_prefix and ts.startswith(iso_prefix):
                    results.append(dict(row))
                elif compact_prefix and compact_prefix in ts:
                    results.append(dict(row))
        return results
    except Exception:
        return ()
