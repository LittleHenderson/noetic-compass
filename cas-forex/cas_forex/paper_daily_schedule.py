"""Next-action schedule for CAS FOREX daily paper-proof bundles.

This module is intentionally read-only. It does not run MT5, place orders, or
append proof packets. It tells the operator which trading day is due next and
what evidence tracks are missing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Mapping, Set

from cas_forex.evidence_store import EvidenceStore
from cas_forex.paper_decision import paper_decision_store_path
from cas_forex.paper_proof import PaperProofPlan, summarize_paper_proof
from cas_forex.paper_risk import paper_risk_store_path
from cas_forex.time_utils import utc_now


PAPER_DAILY_SCHEDULE_CLAIM_BOUNDARY = (
    "Paper daily schedule is an operator prompt only. "
    "It does not place trades, create broker ACCEPT, or authorize live money."
)


@dataclass(frozen=True)
class PaperDailySchedule:
    schedule_id: str
    plan_id: str
    lead_id: str
    strategy_setting: str
    timeframe: str
    as_of_date: str
    next_due_date: str
    next_due_status: str
    latest_complete_bundle_date: str | None
    complete_bundle_days: int
    completed_trading_days: int
    broker_verified_days: int
    decision_days: int
    risk_review_days: int
    ui_min_daily_bundles: int
    ui_bundles_remaining: int
    required_paper_days: int
    paper_days_remaining: int
    missing_tracks_for_next_due: List[str]
    complete_bundle_dates: List[str]
    recommended_command: str
    notes: List[str] = field(default_factory=list)
    claim_boundary: str = PAPER_DAILY_SCHEDULE_CLAIM_BOUNDARY
    deployment_status: str = "NOT LICENSED"
    broker_accept_status: str = "NOT LICENSED"
    payment_transfer_status: str = "NOT LICENSED"


def evaluate_daily_paper_schedule(
    plan: PaperProofPlan,
    output_dir: str | Path,
    *,
    as_of_date: date | None = None,
    account_equity: float = 5_000.0,
    max_risk_pct: float = 0.5,
    daily_risk_pct: float = 1.0,
    ui_min_daily_bundles: int = 5,
) -> PaperDailySchedule:
    """Return the next due paper-bundle date and missing evidence tracks."""

    if ui_min_daily_bundles <= 0:
        raise ValueError("ui_min_daily_bundles must be positive.")
    day = as_of_date or utc_now().date()
    out_dir = Path(output_dir)
    proof_report = summarize_paper_proof(plan, out_dir)
    broker_verified_dates = {
        str(summary.get("date"))
        for summary in proof_report.daily_summaries
        if str(summary.get("date", "")).strip()
        and bool(summary.get("broker_source_verified"))
    }
    proof_dates = {
        str(summary.get("date"))
        for summary in proof_report.daily_summaries
        if str(summary.get("date", "")).strip()
    }
    decision_dates = _chain_dates(paper_decision_store_path(plan, out_dir))
    risk_dates = _chain_dates(paper_risk_store_path(plan, out_dir))
    complete_dates = sorted(broker_verified_dates & decision_dates & risk_dates)
    latest_complete = complete_dates[-1] if complete_dates else None

    next_due = _choose_next_due_date(day, complete_dates)
    missing = _missing_tracks(
        next_due.isoformat(),
        broker_verified_dates=broker_verified_dates,
        decision_dates=decision_dates,
        risk_dates=risk_dates,
    )
    if next_due.isoformat() in complete_dates:
        status = "COMPLETE_FOR_DATE"
    elif day.weekday() >= 5:
        status = "WAIT_NEXT_TRADING_DAY"
    elif next_due == day:
        status = "DUE_TODAY"
    else:
        status = "WAIT_NEXT_TRADING_DAY"

    ui_remaining = max(ui_min_daily_bundles - len(complete_dates), 0)
    paper_remaining = max(plan.required_trading_days - len(proof_dates), 0)
    notes = [
        "Run the recommended command on the next due trading day.",
        "A complete daily bundle requires broker/demo receipt, route/no-trade decision, and risk review.",
        PAPER_DAILY_SCHEDULE_CLAIM_BOUNDARY,
    ]
    if ui_remaining:
        notes.append(f"Proof cockpit UI/UX gate still needs {ui_remaining} more complete daily bundles.")
    if paper_remaining:
        notes.append(f"Full paper-proof gate still needs {paper_remaining} more paper trading days.")

    command = (
        "python scripts/run_daily_paper_bundle.py "
        f"--date {next_due.isoformat()} "
        f"--account-equity {account_equity:g} "
        f"--max-risk-pct {max_risk_pct:g} "
        f"--daily-risk-pct {daily_risk_pct:g} "
        "--output-dir evidence_runs/index_tsmom_126_paper_proof"
    )
    return PaperDailySchedule(
        schedule_id=f"{plan.plan_id}-{day.isoformat()}-daily-schedule",
        plan_id=plan.plan_id,
        lead_id=plan.lead_id,
        strategy_setting=plan.strategy_setting,
        timeframe=plan.timeframe,
        as_of_date=day.isoformat(),
        next_due_date=next_due.isoformat(),
        next_due_status=status,
        latest_complete_bundle_date=latest_complete,
        complete_bundle_days=len(complete_dates),
        completed_trading_days=len(proof_dates),
        broker_verified_days=len(broker_verified_dates),
        decision_days=len(decision_dates),
        risk_review_days=len(risk_dates),
        ui_min_daily_bundles=ui_min_daily_bundles,
        ui_bundles_remaining=ui_remaining,
        required_paper_days=plan.required_trading_days,
        paper_days_remaining=paper_remaining,
        missing_tracks_for_next_due=missing,
        complete_bundle_dates=complete_dates,
        recommended_command=command,
        notes=notes,
    )


def write_daily_paper_schedule_status(
    plan: PaperProofPlan,
    output_dir: str | Path,
    schedule: PaperDailySchedule,
) -> Path:
    """Write the latest paper daily schedule status JSON."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{plan.plan_id}-daily-schedule-status.json"
    path.write_text(json.dumps(asdict(schedule), indent=2), encoding="utf-8")
    return path


def _choose_next_due_date(day: date, complete_dates: List[str]) -> date:
    if day.weekday() >= 5:
        return _next_weekday(day)
    if day.isoformat() not in complete_dates:
        return day
    return _next_weekday(day + timedelta(days=1))


def _next_weekday(day: date) -> date:
    current = day
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def _missing_tracks(
    target_date: str,
    *,
    broker_verified_dates: Set[str],
    decision_dates: Set[str],
    risk_dates: Set[str],
) -> List[str]:
    missing: List[str] = []
    if target_date not in broker_verified_dates:
        missing.append("broker_verified_receipt")
    if target_date not in decision_dates:
        missing.append("paper_route_decision")
    if target_date not in risk_dates:
        missing.append("paper_risk_review")
    return missing


def _chain_dates(path: Path) -> Set[str]:
    store = EvidenceStore(path, run_id=path.stem)
    dates: Set[str] = set()
    for record in store._records():
        packet = record.get("packet") if isinstance(record, Mapping) else None
        if not isinstance(packet, Mapping):
            continue
        outcome = packet.get("close_outcome")
        if not isinstance(outcome, Mapping):
            continue
        value = str(outcome.get("date", "")).strip()
        if value:
            dates.add(value)
    return dates
