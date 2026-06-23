"""Daily CAS FOREX paper-proof bundle runner.

This orchestrates the three paper-only daily tracks for the active lead:
broker/demo receipt, route/no-trade decision, and risk-budget sizing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from cas_forex.config import config
from cas_forex.paper_broker_adapter import MT5DemoPaperReceiptAdapter
from cas_forex.paper_decision import (
    append_paper_route_decision,
    evaluate_paper_route_decision,
    summarize_paper_route_decisions,
    write_paper_route_decision_status,
)
from cas_forex.paper_proof import (
    BROKER_API_VERIFIED,
    PaperProofPlan,
    append_paper_proof_day,
    summarize_paper_proof,
    write_paper_proof_plan,
    write_paper_proof_status,
)
from cas_forex.paper_risk import (
    append_paper_risk_review,
    review_paper_risk_budget,
    summarize_paper_risk_reviews,
    write_paper_risk_status,
)
from cas_forex.time_utils import utc_now


DAILY_BUNDLE_CLAIM_BOUNDARY = (
    "Daily paper bundles are paper-proof orchestration only. "
    "They do not place trades, create broker ACCEPT, or authorize live money."
)


@dataclass(frozen=True)
class DailyBundleStep:
    name: str
    status: str
    detail: str
    artifact: Optional[str] = None
    reasons: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DailyPaperBundle:
    bundle_id: str
    plan_id: str
    lead_id: str
    strategy_setting: str
    date: str
    timeframe: str
    steps: List[DailyBundleStep]
    completed: bool
    latest_proof: Dict[str, Any]
    latest_decision: Dict[str, Any]
    latest_risk: Dict[str, Any]
    ui_ux_checkpoint: str
    claim_boundary: str = DAILY_BUNDLE_CLAIM_BOUNDARY


def run_daily_paper_bundle(
    plan: PaperProofPlan,
    output_dir: str | Path,
    *,
    trading_date: Optional[date] = None,
    append_records: bool = True,
    collect_mt5_receipt: bool = True,
    skip_existing: bool = True,
    account_equity: float = 5_000.0,
    max_risk_per_trade_pct: Optional[float] = None,
    daily_risk_budget_pct: float = 1.0,
    max_paper_attempts: Optional[int] = None,
    market_connector: Optional[Any] = None,
    macro_gate: Optional[Any] = None,
    candles_by_symbol: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    mt5_adapter: Optional[Any] = None,
) -> DailyPaperBundle:
    """Run or summarize the daily paper-proof bundle for one trading date."""

    if config.live_mode or not config.paper_trading:
        raise PermissionError("Daily paper bundles require paper_trading=True and live_mode=False.")

    day = trading_date or utc_now().date()
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_paper_proof_plan(plan, out_dir)
    steps: List[DailyBundleStep] = []

    receipt_step = _run_receipt_step(
        plan,
        out_dir,
        day,
        append_records=append_records,
        collect_mt5_receipt=collect_mt5_receipt,
        skip_existing=skip_existing,
        mt5_adapter=mt5_adapter,
    )
    steps.append(receipt_step)
    proof_report = summarize_paper_proof(plan, out_dir)
    proof_status_path = write_paper_proof_status(plan, out_dir, proof_report)

    decision_step = _run_decision_step(
        plan,
        out_dir,
        day,
        append_records=append_records,
        skip_existing=skip_existing,
        market_connector=market_connector,
        macro_gate=macro_gate,
        candles_by_symbol=candles_by_symbol,
    )
    steps.append(decision_step)
    decision_status_path = write_paper_route_decision_status(plan, out_dir)
    decision_summary = summarize_paper_route_decisions(plan, out_dir)

    risk_step = _run_risk_step(
        plan,
        out_dir,
        day,
        decision_summary,
        append_records=append_records,
        skip_existing=skip_existing,
        account_equity=account_equity,
        max_risk_per_trade_pct=max_risk_per_trade_pct,
        daily_risk_budget_pct=daily_risk_budget_pct,
        max_paper_attempts=max_paper_attempts,
    )
    steps.append(risk_step)
    risk_status_path = write_paper_risk_status(plan, out_dir)
    risk_summary = summarize_paper_risk_reviews(plan, out_dir)

    completed = all(step.status in {"APPENDED", "SKIPPED_EXISTING", "SKIPPED_DISABLED"} for step in steps)
    if not risk_summary.get("latest_review"):
        completed = False
    bundle = DailyPaperBundle(
        bundle_id=f"{plan.plan_id}-{day.isoformat()}-daily-bundle",
        plan_id=plan.plan_id,
        lead_id=plan.lead_id,
        strategy_setting=plan.strategy_setting,
        date=day.isoformat(),
        timeframe=plan.timeframe,
        steps=steps,
        completed=completed,
        latest_proof={
            "status_path": str(proof_status_path),
            "completed_trading_days": proof_report.completed_trading_days,
            "required_trading_days": proof_report.required_trading_days,
            "chain_verified": proof_report.chain_verified,
            "passed": proof_report.passed,
            "failure_reasons": list(proof_report.failure_reasons),
        },
        latest_decision={
            "status_path": str(decision_status_path),
            **decision_summary,
        },
        latest_risk={
            "status_path": str(risk_status_path),
            **risk_summary,
        },
        ui_ux_checkpoint=(
            "NOT_YET: wait for several daily bundles before building the proof cockpit."
        ),
    )
    write_daily_paper_bundle_status(plan, out_dir, bundle)
    return bundle


def write_daily_paper_bundle_status(
    plan: PaperProofPlan,
    output_dir: str | Path,
    bundle: DailyPaperBundle,
) -> Path:
    """Write the latest combined daily paper-proof bundle status."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{plan.plan_id}-daily-bundle-status.json"
    path.write_text(json.dumps(daily_bundle_payload(bundle), indent=2), encoding="utf-8")
    return path


def daily_bundle_payload(bundle: DailyPaperBundle) -> Dict[str, Any]:
    return {
        "bundle_id": bundle.bundle_id,
        "plan_id": bundle.plan_id,
        "lead_id": bundle.lead_id,
        "strategy_setting": bundle.strategy_setting,
        "date": bundle.date,
        "timeframe": bundle.timeframe,
        "steps": [asdict(step) for step in bundle.steps],
        "completed": bundle.completed,
        "latest_proof": bundle.latest_proof,
        "latest_decision": bundle.latest_decision,
        "latest_risk": bundle.latest_risk,
        "ui_ux_checkpoint": bundle.ui_ux_checkpoint,
        "claim_boundary": bundle.claim_boundary,
        "deployment_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "payment_transfer_status": "NOT LICENSED",
    }


def _run_receipt_step(
    plan: PaperProofPlan,
    out_dir: Path,
    day: date,
    *,
    append_records: bool,
    collect_mt5_receipt: bool,
    skip_existing: bool,
    mt5_adapter: Optional[Any],
) -> DailyBundleStep:
    if skip_existing and _proof_has_broker_verified_date(plan, out_dir, day):
        return DailyBundleStep(
            name="mt5_demo_receipt",
            status="SKIPPED_EXISTING",
            detail="Broker/API-verified paper receipt already exists for this date.",
        )
    if not collect_mt5_receipt:
        return DailyBundleStep(
            name="mt5_demo_receipt",
            status="SKIPPED_DISABLED",
            detail="MT5 demo receipt collection was disabled for this bundle run.",
        )
    adapter = mt5_adapter or MT5DemoPaperReceiptAdapter()
    probe = adapter.probe(plan, day)
    if probe.status == BROKER_API_VERIFIED and probe.receipt:
        if append_records:
            appended = append_paper_proof_day(
                plan,
                out_dir,
                trading_date=day,
                broker_receipt=probe.receipt,
                allow_api_verified_receipt=True,
            )
            return DailyBundleStep(
                name="mt5_demo_receipt",
                status="APPENDED",
                detail="Broker/API-verified paper receipt appended.",
                artifact=appended.get("receipt", {}).get("store_uri"),
            )
        return DailyBundleStep(
            name="mt5_demo_receipt",
            status="VERIFIED_NOT_APPENDED",
            detail="Broker/API-verified paper receipt collected but append_records=false.",
        )
    return DailyBundleStep(
        name="mt5_demo_receipt",
        status=str(probe.status),
        detail="MT5 demo receipt was not appended.",
        reasons=list(getattr(probe, "reasons", []) or []),
    )


def _run_decision_step(
    plan: PaperProofPlan,
    out_dir: Path,
    day: date,
    *,
    append_records: bool,
    skip_existing: bool,
    market_connector: Optional[Any],
    macro_gate: Optional[Any],
    candles_by_symbol: Optional[Mapping[str, Sequence[Mapping[str, Any]]]],
) -> DailyBundleStep:
    if skip_existing and _decision_has_date(plan, out_dir, day):
        return DailyBundleStep(
            name="paper_route_decision",
            status="SKIPPED_EXISTING",
            detail="Paper route/no-trade decision already exists for this date.",
        )
    decision = evaluate_paper_route_decision(
        plan,
        trading_date=day,
        candles_by_symbol=candles_by_symbol,
        market_connector=market_connector,
        macro_gate=macro_gate,
    )
    if append_records:
        appended = append_paper_route_decision(decision, out_dir)
        return DailyBundleStep(
            name="paper_route_decision",
            status="APPENDED",
            detail=f"Paper route decision appended with action {decision.route_action}.",
            artifact=appended.get("receipt", {}).get("store_uri"),
        )
    return DailyBundleStep(
        name="paper_route_decision",
        status="EVALUATED_NOT_APPENDED",
        detail=f"Paper route decision evaluated with action {decision.route_action}.",
    )


def _run_risk_step(
    plan: PaperProofPlan,
    out_dir: Path,
    day: date,
    decision_summary: Mapping[str, Any],
    *,
    append_records: bool,
    skip_existing: bool,
    account_equity: float,
    max_risk_per_trade_pct: Optional[float],
    daily_risk_budget_pct: float,
    max_paper_attempts: Optional[int],
) -> DailyBundleStep:
    if skip_existing and _risk_has_date(plan, out_dir, day):
        return DailyBundleStep(
            name="paper_risk_review",
            status="SKIPPED_EXISTING",
            detail="Paper risk-budget review already exists for this date.",
        )
    latest_decision = decision_summary.get("latest_decision")
    if not isinstance(latest_decision, Mapping):
        return DailyBundleStep(
            name="paper_risk_review",
            status="BLOCKED_NO_DECISION",
            detail="No paper route decision was available for risk review.",
        )
    if str(latest_decision.get("date")) != day.isoformat():
        return DailyBundleStep(
            name="paper_risk_review",
            status="BLOCKED_DECISION_DATE_MISMATCH",
            detail=f"Latest paper decision date {latest_decision.get('date')} does not match {day.isoformat()}.",
        )
    review = review_paper_risk_budget(
        plan,
        latest_decision,
        account_equity=account_equity,
        max_risk_per_trade_pct=max_risk_per_trade_pct,
        daily_risk_budget_pct=daily_risk_budget_pct,
        max_paper_attempts=max_paper_attempts,
    )
    if append_records:
        appended = append_paper_risk_review(review, out_dir)
        return DailyBundleStep(
            name="paper_risk_review",
            status="APPENDED",
            detail=f"Paper risk review appended with status {review.risk_status}.",
            artifact=appended.get("receipt", {}).get("store_uri"),
        )
    return DailyBundleStep(
        name="paper_risk_review",
        status="EVALUATED_NOT_APPENDED",
        detail=f"Paper risk review evaluated with status {review.risk_status}.",
    )


def _proof_has_broker_verified_date(plan: PaperProofPlan, out_dir: Path, day: date) -> bool:
    report = summarize_paper_proof(plan, out_dir)
    return any(
        str(summary.get("date")) == day.isoformat()
        and bool(summary.get("broker_source_verified"))
        for summary in report.daily_summaries
    )


def _decision_has_date(plan: PaperProofPlan, out_dir: Path, day: date) -> bool:
    summary = summarize_paper_route_decisions(plan, out_dir)
    latest = summary.get("latest_decision")
    if isinstance(latest, Mapping) and str(latest.get("date")) == day.isoformat():
        return True
    return False


def _risk_has_date(plan: PaperProofPlan, out_dir: Path, day: date) -> bool:
    summary = summarize_paper_risk_reviews(plan, out_dir)
    latest = summary.get("latest_review")
    if isinstance(latest, Mapping) and str(latest.get("date")) == day.isoformat():
        return True
    return False
