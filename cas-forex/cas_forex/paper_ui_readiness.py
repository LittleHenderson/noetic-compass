"""Multi-day proof maturity gate for the CAS FOREX paper-proof cockpit.

This is a read-only status layer. It decides whether the backend has enough
real paper-bundle history for the proof cockpit to claim multi-day evidence.
It is not a blocker to starting a read-only UI shell.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Set

from cas_forex.evidence_store import EvidenceStore
from cas_forex.paper_decision import (
    paper_decision_store_path,
    summarize_paper_route_decisions,
)
from cas_forex.paper_proof import PaperProofPlan, summarize_paper_proof
from cas_forex.paper_risk import paper_risk_store_path, summarize_paper_risk_reviews


UI_READINESS_CLAIM_BOUNDARY = (
    "UI readiness is proof-cockpit evidence maturity only. "
    "It does not create broker ACCEPT, live trading permission, or payment-transfer permission."
)


@dataclass(frozen=True)
class PaperUIReadinessReport:
    report_id: str
    plan_id: str
    lead_id: str
    strategy_setting: str
    timeframe: str
    readiness_status: str
    min_daily_bundles_for_ui: int
    completed_trading_days: int
    broker_verified_days: int
    decision_days: int
    risk_review_days: int
    complete_bundle_days: int
    complete_bundle_dates: List[str]
    route_counts: Dict[str, int]
    risk_status_counts: Dict[str, int]
    chains_verified: Dict[str, bool]
    blockers: List[str] = field(default_factory=list)
    next_ui_step: str = ""
    claim_boundary: str = UI_READINESS_CLAIM_BOUNDARY
    deployment_status: str = "NOT LICENSED"
    broker_accept_status: str = "NOT LICENSED"
    payment_transfer_status: str = "NOT LICENSED"


def evaluate_paper_ui_readiness(
    plan: PaperProofPlan,
    output_dir: str | Path,
    *,
    min_daily_bundles_for_ui: int = 5,
) -> PaperUIReadinessReport:
    """Evaluate whether the backend has enough bundles for multi-day proof views."""

    if min_daily_bundles_for_ui <= 0:
        raise ValueError("min_daily_bundles_for_ui must be positive.")

    out_dir = Path(output_dir)
    proof_report = summarize_paper_proof(plan, out_dir)
    decision_summary = summarize_paper_route_decisions(plan, out_dir)
    risk_summary = summarize_paper_risk_reviews(plan, out_dir)

    proof_dates = {
        str(summary.get("date"))
        for summary in proof_report.daily_summaries
        if str(summary.get("date", "")).strip()
    }
    broker_verified_dates = {
        str(summary.get("date"))
        for summary in proof_report.daily_summaries
        if str(summary.get("date", "")).strip()
        and bool(summary.get("broker_source_verified"))
    }
    decision_dates = _chain_dates(
        paper_decision_store_path(plan, out_dir),
        outcome_key="date",
    )
    risk_dates = _chain_dates(
        paper_risk_store_path(plan, out_dir),
        outcome_key="date",
    )
    complete_dates = sorted(broker_verified_dates & decision_dates & risk_dates)
    chains_verified = {
        "paper_proof": bool(proof_report.chain_verified),
        "paper_decision": bool(decision_summary.get("chain_verified")),
        "paper_risk": bool(risk_summary.get("chain_verified")),
    }

    blockers: List[str] = []
    if len(complete_dates) < min_daily_bundles_for_ui:
        blockers.append(
            f"complete_bundle_days {len(complete_dates)} < required {min_daily_bundles_for_ui}"
        )
    if len(broker_verified_dates) < min_daily_bundles_for_ui:
        blockers.append(
            f"broker_verified_days {len(broker_verified_dates)} < required {min_daily_bundles_for_ui}"
        )
    if len(decision_dates) < min_daily_bundles_for_ui:
        blockers.append(
            f"decision_days {len(decision_dates)} < required {min_daily_bundles_for_ui}"
        )
    if len(risk_dates) < min_daily_bundles_for_ui:
        blockers.append(
            f"risk_review_days {len(risk_dates)} < required {min_daily_bundles_for_ui}"
        )
    for chain_name, verified in chains_verified.items():
        if not verified:
            blockers.append(f"{chain_name} chain did not verify")
    if proof_report.live_mode_used:
        blockers.append("Live mode appeared in paper-proof status.")
    if proof_report.daily_summaries and not proof_report.open_positions_reconciled:
        blockers.append("Open positions were not reconciled for every paper day.")

    readiness_status = "READY_FOR_PROOF_COCKPIT_UI_UX" if not blockers else "NOT_READY_FOR_UI_UX"
    if readiness_status == "READY_FOR_PROOF_COCKPIT_UI_UX":
        next_ui_step = (
            "Build a read-only proof cockpit showing paper proof, route/no-trade, "
            "risk budget, blockers, and NOT LICENSED boundaries."
        )
    else:
        next_ui_step = (
            "A read-only UI shell may start now, but must label multi-day proof as pending. "
            "Keep running scripts/run_daily_paper_bundle.py for each real trading day "
            "until the minimum complete daily bundle count is met."
        )

    return PaperUIReadinessReport(
        report_id=f"{plan.plan_id}-ui-readiness",
        plan_id=plan.plan_id,
        lead_id=plan.lead_id,
        strategy_setting=plan.strategy_setting,
        timeframe=plan.timeframe,
        readiness_status=readiness_status,
        min_daily_bundles_for_ui=min_daily_bundles_for_ui,
        completed_trading_days=len(proof_dates),
        broker_verified_days=len(broker_verified_dates),
        decision_days=len(decision_dates),
        risk_review_days=len(risk_dates),
        complete_bundle_days=len(complete_dates),
        complete_bundle_dates=complete_dates,
        route_counts=dict(decision_summary.get("route_counts", {})),
        risk_status_counts=dict(risk_summary.get("risk_status_counts", {})),
        chains_verified=chains_verified,
        blockers=blockers,
        next_ui_step=next_ui_step,
    )


def write_paper_ui_readiness_status(
    plan: PaperProofPlan,
    output_dir: str | Path,
    report: PaperUIReadinessReport,
) -> Path:
    """Write the latest proof-cockpit evidence maturity status JSON."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{plan.plan_id}-ui-readiness-status.json"
    path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    return path


def _chain_dates(path: Path, *, outcome_key: str) -> Set[str]:
    store = EvidenceStore(path, run_id=path.stem)
    dates: Set[str] = set()
    for record in store._records():
        packet = record.get("packet") if isinstance(record, Mapping) else None
        if not isinstance(packet, Mapping):
            continue
        outcome = packet.get("close_outcome")
        if not isinstance(outcome, Mapping):
            continue
        value = str(outcome.get(outcome_key, "")).strip()
        if value:
            dates.add(value)
    return dates
