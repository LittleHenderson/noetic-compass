"""Paper-only risk-budget sizing for daily CAS FOREX route decisions.

This module sits between a paper route/no-trade decision and any future paper
broker adapter. It answers: if CAS would route today, what paper size fits the
owner's risk budget? It never places orders and never creates broker ACCEPT.
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.instruments import get_instrument, pip_value_per_lot, price_unit_size
from cas_forex.paper_proof import PaperProofPlan
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus


PAPER_RISK_CLAIM_BOUNDARY = (
    "Paper risk reviews are sizing/accounting only. "
    "They do not place trades, create broker ACCEPT, or authorize live money."
)


@dataclass(frozen=True)
class PaperAttemptSizing:
    """Risk sizing result for one routed paper candidate."""

    symbol: str
    action: str
    reason: str
    attempt_status: str
    direction: Optional[str] = None
    confidence: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    stop_distance_units: float = 0.0
    unit_name: str = "unit"
    unit_value_per_lot_usd: float = 0.0
    risk_per_lot_usd: float = 0.0
    max_risk_usd: float = 0.0
    raw_lots: float = 0.0
    sized_lots: float = 0.0
    planned_risk_usd: float = 0.0
    planned_risk_pct: float = 0.0
    attempt_number: Optional[int] = None
    proposal_id: Optional[str] = None


@dataclass(frozen=True)
class PaperRiskReview:
    """Daily paper risk budget review for one route decision."""

    review_id: str
    plan_id: str
    lead_id: str
    strategy_setting: str
    date: str
    timeframe: str
    source_decision_id: Optional[str]
    route_action: str
    account_equity: float
    max_risk_per_trade_pct: float
    daily_risk_budget_pct: float
    daily_risk_budget_usd: float
    max_position_lots: float
    max_paper_attempts: int
    existing_attempts: int
    attempts_remaining_before_review: int
    proposed_attempts: int
    allowed_attempts: int
    suppressed_attempts: int
    total_planned_lots: float
    total_planned_risk_usd: float
    total_planned_risk_pct: float
    risk_status: str
    sizing: List[PaperAttemptSizing] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    claim_boundary: str = PAPER_RISK_CLAIM_BOUNDARY


def paper_risk_store_path(plan: PaperProofPlan, output_dir: str | Path) -> Path:
    """Return the append-only daily paper-risk review chain path."""

    return Path(output_dir) / f"{plan.plan_id}-paper-risk.jsonl"


def review_paper_risk_budget(
    plan: PaperProofPlan,
    latest_decision: Mapping[str, Any],
    *,
    account_equity: float = 5_000.0,
    max_risk_per_trade_pct: Optional[float] = None,
    daily_risk_budget_pct: float = 1.0,
    max_paper_attempts: Optional[int] = None,
    existing_attempts: int = 0,
    min_lot: float = 0.01,
    lot_step: float = 0.01,
    max_position_lots: Optional[float] = None,
) -> PaperRiskReview:
    """Build a paper-only risk review from the latest route/no-trade decision."""

    if config.live_mode or not config.paper_trading:
        raise PermissionError("Paper risk reviews require paper_trading=True and live_mode=False.")
    if account_equity <= 0:
        raise ValueError("account_equity must be positive.")
    if daily_risk_budget_pct <= 0:
        raise ValueError("daily_risk_budget_pct must be positive.")
    if min_lot <= 0 or lot_step <= 0:
        raise ValueError("min_lot and lot_step must be positive.")
    if existing_attempts < 0:
        raise ValueError("existing_attempts must be non-negative.")

    per_trade_pct = (
        float(max_risk_per_trade_pct)
        if max_risk_per_trade_pct is not None
        else float(config.max_risk_per_trade_pct)
    )
    if per_trade_pct <= 0:
        raise ValueError("max_risk_per_trade_pct must be positive.")
    attempt_limit = int(max_paper_attempts if max_paper_attempts is not None else plan.max_paper_trades_per_day)
    if attempt_limit < 0:
        raise ValueError("max_paper_attempts must be non-negative.")
    position_cap = float(max_position_lots if max_position_lots is not None else config.max_position_lots)
    if position_cap <= 0:
        raise ValueError("max_position_lots must be positive.")

    daily_budget_usd = account_equity * daily_risk_budget_pct / 100.0
    remaining_daily_risk_usd = daily_budget_usd
    attempts_remaining = max(attempt_limit - existing_attempts, 0)
    sizing: List[PaperAttemptSizing] = []

    symbol_decisions = latest_decision.get("symbol_decisions", [])
    if not isinstance(symbol_decisions, list):
        symbol_decisions = []
    route_action = str(latest_decision.get("route_action", "UNKNOWN"))
    proposed_attempts = 0
    allowed_attempts = 0
    total_lots = 0.0
    total_risk_usd = 0.0
    blockers: List[str] = []

    for item in symbol_decisions:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("action")) != "ROUTE_PAPER_SIGNAL":
            continue
        proposed_attempts += 1
        proposal = item.get("proposal")
        if not isinstance(proposal, Mapping):
            sizing.append(
                PaperAttemptSizing(
                    symbol=str(item.get("symbol", "UNKNOWN")),
                    action="ROUTE_PAPER_SIGNAL",
                    reason="Route candidate did not include a proposal payload.",
                    attempt_status="SUPPRESSED_INVALID_PROPOSAL",
                )
            )
            blockers.append("route candidate missing proposal payload")
            continue

        candidate = _size_candidate(
            proposal,
            account_equity=account_equity,
            per_trade_pct=per_trade_pct,
            remaining_daily_risk_usd=remaining_daily_risk_usd,
            attempts_remaining=attempts_remaining,
            min_lot=min_lot,
            lot_step=lot_step,
            max_position_lots=position_cap,
        )
        if candidate.attempt_status == "PAPER_ATTEMPT_ALLOWED":
            attempts_remaining -= 1
            allowed_attempts += 1
            remaining_daily_risk_usd -= candidate.planned_risk_usd
            total_lots += candidate.sized_lots
            total_risk_usd += candidate.planned_risk_usd
            candidate = PaperAttemptSizing(
                **{
                    **asdict(candidate),
                    "attempt_number": existing_attempts + allowed_attempts,
                }
            )
        else:
            blockers.append(candidate.reason)
        sizing.append(candidate)

    if proposed_attempts == 0:
        risk_status = "NO_PAPER_ATTEMPT"
        notes = ["No routed paper candidate needed risk sizing."]
    elif allowed_attempts == 0:
        risk_status = "PAPER_ATTEMPTS_SUPPRESSED"
        notes = ["Routed paper candidates existed, but risk budget suppressed all attempts."]
    elif allowed_attempts < proposed_attempts:
        risk_status = "PARTIAL_PAPER_ATTEMPTS_ALLOWED"
        notes = ["Some paper candidates fit the risk budget; some were suppressed."]
    else:
        risk_status = "PAPER_ATTEMPTS_ALLOWED"
        notes = ["All routed paper candidates fit the paper risk budget."]

    notes.append(PAPER_RISK_CLAIM_BOUNDARY)
    return PaperRiskReview(
        review_id=f"{plan.plan_id}-{latest_decision.get('date', 'unknown')}-paper-risk",
        plan_id=plan.plan_id,
        lead_id=plan.lead_id,
        strategy_setting=plan.strategy_setting,
        date=str(latest_decision.get("date", "")),
        timeframe=str(latest_decision.get("timeframe", plan.timeframe)),
        source_decision_id=(
            str(latest_decision.get("decision_id"))
            if latest_decision.get("decision_id") is not None
            else None
        ),
        route_action=route_action,
        account_equity=round(account_equity, 2),
        max_risk_per_trade_pct=round(per_trade_pct, 6),
        daily_risk_budget_pct=round(daily_risk_budget_pct, 6),
        daily_risk_budget_usd=round(daily_budget_usd, 2),
        max_position_lots=round(position_cap, 4),
        max_paper_attempts=attempt_limit,
        existing_attempts=existing_attempts,
        attempts_remaining_before_review=max(attempt_limit - existing_attempts, 0),
        proposed_attempts=proposed_attempts,
        allowed_attempts=allowed_attempts,
        suppressed_attempts=max(proposed_attempts - allowed_attempts, 0),
        total_planned_lots=round(total_lots, 4),
        total_planned_risk_usd=round(total_risk_usd, 2),
        total_planned_risk_pct=round(total_risk_usd / account_equity * 100.0, 4),
        risk_status=risk_status,
        sizing=sizing,
        blockers=sorted(set(blockers)),
        notes=notes,
    )


def append_paper_risk_review(review: PaperRiskReview, output_dir: str | Path) -> Dict[str, Any]:
    """Append a paper risk review to its tamper-evident local chain."""

    if config.live_mode or not config.paper_trading:
        raise PermissionError("Paper risk reviews require paper_trading=True and live_mode=False.")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = PaperProofPlan(
        plan_id=review.plan_id,
        lead_id=review.lead_id,
        strategy_setting=review.strategy_setting,
        symbols=[item.symbol for item in review.sizing] or [],
        timeframe=review.timeframe,
    )
    store = EvidenceStore(paper_risk_store_path(plan, out_dir), run_id=f"{review.plan_id}-paper-risk")
    payload = review_payload(review)
    packet = ForexEvidencePacket(
        packet_id=str(uuid.uuid4()),
        trace_id=review.review_id,
        status=PacketStatus.SUPPRESSED,
        proposal=_first_sized_proposal_stub(review),
        notes=[*review.notes, "No broker order was placed."],
        close_outcome=payload,
    )
    packet.finalize()
    receipt = store.append(packet, source="paper-risk-review")
    return {"review": payload, "receipt": receipt.model_dump(mode="json")}


def summarize_paper_risk_reviews(plan: PaperProofPlan, output_dir: str | Path) -> Dict[str, Any]:
    """Summarize the paper-risk chain for proof UI and docs."""

    store = EvidenceStore(paper_risk_store_path(plan, output_dir), run_id=f"{plan.plan_id}-paper-risk")
    reviews: List[Dict[str, Any]] = []
    for record in store._records():
        packet = record.get("packet") if isinstance(record, Mapping) else None
        if not isinstance(packet, Mapping):
            continue
        outcome = packet.get("close_outcome")
        if isinstance(outcome, Mapping):
            reviews.append(dict(outcome))
    status_counts: Dict[str, int] = {}
    for review in reviews:
        status = str(review.get("risk_status", "UNKNOWN"))
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "plan_id": plan.plan_id,
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "review_count": len(reviews),
        "risk_status_counts": status_counts,
        "chain_verified": store.verify_chain(),
        "latest_review": reviews[-1] if reviews else None,
        "claim_boundary": PAPER_RISK_CLAIM_BOUNDARY,
    }


def write_paper_risk_status(plan: PaperProofPlan, output_dir: str | Path) -> Path:
    """Write the latest paper-risk status summary."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status = summarize_paper_risk_reviews(plan, out_dir)
    path = out_dir / f"{plan.plan_id}-paper-risk-status.json"
    path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return path


def review_payload(review: PaperRiskReview) -> Dict[str, Any]:
    """Serialize a PaperRiskReview with stable primitive values."""

    return {
        "review_id": review.review_id,
        "plan_id": review.plan_id,
        "lead_id": review.lead_id,
        "strategy_setting": review.strategy_setting,
        "date": review.date,
        "timeframe": review.timeframe,
        "source_decision_id": review.source_decision_id,
        "route_action": review.route_action,
        "account_equity": review.account_equity,
        "max_risk_per_trade_pct": review.max_risk_per_trade_pct,
        "daily_risk_budget_pct": review.daily_risk_budget_pct,
        "daily_risk_budget_usd": review.daily_risk_budget_usd,
        "max_position_lots": review.max_position_lots,
        "max_paper_attempts": review.max_paper_attempts,
        "existing_attempts": review.existing_attempts,
        "attempts_remaining_before_review": review.attempts_remaining_before_review,
        "proposed_attempts": review.proposed_attempts,
        "allowed_attempts": review.allowed_attempts,
        "suppressed_attempts": review.suppressed_attempts,
        "total_planned_lots": review.total_planned_lots,
        "total_planned_risk_usd": review.total_planned_risk_usd,
        "total_planned_risk_pct": review.total_planned_risk_pct,
        "risk_status": review.risk_status,
        "sizing": [asdict(item) for item in review.sizing],
        "blockers": list(review.blockers),
        "notes": list(review.notes),
        "claim_boundary": review.claim_boundary,
        "deployment_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "payment_transfer_status": "NOT LICENSED",
    }


def _size_candidate(
    proposal: Mapping[str, Any],
    *,
    account_equity: float,
    per_trade_pct: float,
    remaining_daily_risk_usd: float,
    attempts_remaining: int,
    min_lot: float,
    lot_step: float,
    max_position_lots: float,
) -> PaperAttemptSizing:
    symbol = str(proposal.get("symbol", "UNKNOWN"))
    try:
        entry = float(proposal["entry_price"])
        stop = float(proposal["stop_loss"])
        target = float(proposal["take_profit"])
        direction = str(proposal.get("direction", "UNKNOWN"))
        confidence = float(proposal.get("confidence", 0.0))
        spec = get_instrument(symbol)
        stop_distance_units = abs(entry - stop) / price_unit_size(symbol)
        unit_value = pip_value_per_lot(symbol, entry)
        risk_per_lot = stop_distance_units * unit_value
    except Exception as exc:
        return PaperAttemptSizing(
            symbol=symbol,
            action="ROUTE_PAPER_SIGNAL",
            reason=f"Could not compute paper risk sizing: {exc}",
            attempt_status="SUPPRESSED_INVALID_PROPOSAL",
            proposal_id=_optional_str(proposal.get("proposal_id")),
        )

    if attempts_remaining <= 0:
        return PaperAttemptSizing(
            symbol=symbol,
            action="ROUTE_PAPER_SIGNAL",
            reason="Daily paper attempt limit already reached.",
            attempt_status="SUPPRESSED_ATTEMPT_LIMIT",
            direction=direction,
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            stop_distance_units=round(stop_distance_units, 4),
            unit_name=spec.unit_name,
            unit_value_per_lot_usd=round(unit_value, 6),
            risk_per_lot_usd=round(risk_per_lot, 2),
            proposal_id=_optional_str(proposal.get("proposal_id")),
        )
    if risk_per_lot <= 0:
        return PaperAttemptSizing(
            symbol=symbol,
            action="ROUTE_PAPER_SIGNAL",
            reason="Stop distance produced zero or negative risk per lot.",
            attempt_status="SUPPRESSED_INVALID_RISK",
            direction=direction,
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            unit_name=spec.unit_name,
            proposal_id=_optional_str(proposal.get("proposal_id")),
        )

    max_risk_usd = min(account_equity * per_trade_pct / 100.0, remaining_daily_risk_usd)
    if max_risk_usd <= 0:
        return PaperAttemptSizing(
            symbol=symbol,
            action="ROUTE_PAPER_SIGNAL",
            reason="Daily risk budget has no remaining dollars.",
            attempt_status="SUPPRESSED_DAILY_RISK_CAP",
            direction=direction,
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            stop_distance_units=round(stop_distance_units, 4),
            unit_name=spec.unit_name,
            unit_value_per_lot_usd=round(unit_value, 6),
            risk_per_lot_usd=round(risk_per_lot, 2),
            proposal_id=_optional_str(proposal.get("proposal_id")),
        )

    raw_lots = min(max_risk_usd / risk_per_lot, max_position_lots)
    sized_lots = _round_lots_down(raw_lots, lot_step)
    if sized_lots < min_lot:
        return PaperAttemptSizing(
            symbol=symbol,
            action="ROUTE_PAPER_SIGNAL",
            reason=(
                f"Risk budget only supports {raw_lots:.4f} lots, below minimum paper lot "
                f"{min_lot:.4f}."
            ),
            attempt_status="SUPPRESSED_MIN_LOT_RISK",
            direction=direction,
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            stop_distance_units=round(stop_distance_units, 4),
            unit_name=spec.unit_name,
            unit_value_per_lot_usd=round(unit_value, 6),
            risk_per_lot_usd=round(risk_per_lot, 2),
            max_risk_usd=round(max_risk_usd, 2),
            raw_lots=round(raw_lots, 6),
            proposal_id=_optional_str(proposal.get("proposal_id")),
        )

    planned_risk = sized_lots * risk_per_lot
    return PaperAttemptSizing(
        symbol=symbol,
        action="ROUTE_PAPER_SIGNAL",
        reason="Paper candidate fits per-trade and daily risk budgets.",
        attempt_status="PAPER_ATTEMPT_ALLOWED",
        direction=direction,
        confidence=confidence,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
        stop_distance_units=round(stop_distance_units, 4),
        unit_name=spec.unit_name,
        unit_value_per_lot_usd=round(unit_value, 6),
        risk_per_lot_usd=round(risk_per_lot, 2),
        max_risk_usd=round(max_risk_usd, 2),
        raw_lots=round(raw_lots, 6),
        sized_lots=round(sized_lots, 4),
        planned_risk_usd=round(planned_risk, 2),
        planned_risk_pct=round(planned_risk / account_equity * 100.0, 4),
        proposal_id=_optional_str(proposal.get("proposal_id")),
    )


def _round_lots_down(value: float, step: float) -> float:
    return max(math.floor((value + 1e-12) / step) * step, 0.0)


def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _first_sized_proposal_stub(review: PaperRiskReview) -> Optional[Dict[str, Any]]:
    for item in review.sizing:
        if item.proposal_id:
            return {
                "proposal_id": item.proposal_id,
                "symbol": item.symbol,
                "direction": item.direction,
                "entry_price": item.entry_price,
                "stop_loss": item.stop_loss,
                "take_profit": item.take_profit,
                "timeframe": review.timeframe,
            }
    return None
