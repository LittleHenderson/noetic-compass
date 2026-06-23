"""Owner-controlled promotion policy for CAS FOREX strategy candidates.

This is the switchboard after CAS-SDG, Condition Lab, walk-forward, and paper
proof produce enough wins. It can authorize notification or paper-mode attempts,
but it cannot create live broker authority or payment transfers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence


CLAIM_BOUNDARY = "Owner control policy is research/paper-only. Live trading remains NOT LICENSED."
MAX_OWNER_AUTO_TRADES = 15


class OwnerControlMode(str, Enum):
    DENY = "DENY"
    NOTIFY_ONLY = "NOTIFY_ONLY"
    LIMITED_PAPER = "LIMITED_PAPER"
    PAPER_AUTO = "PAPER_AUTO"
    AI_FULL_AUTO_PAPER = "AI_FULL_AUTO_PAPER"
    LIVE_AUTO = "LIVE_AUTO"
    AI_FULL_AUTO_LIVE_REQUESTED = "AI_FULL_AUTO_LIVE_REQUESTED"


class OwnerPromotionVerdict(str, Enum):
    DENIED = "DENIED"
    NOTIFY = "NOTIFY"
    LIMITED_PAPER_AUTHORIZED = "LIMITED_PAPER_AUTHORIZED"
    PAPER_AUTO_AUTHORIZED = "PAPER_AUTO_AUTHORIZED"
    AI_FULL_AUTO_PAPER_AUTHORIZED = "AI_FULL_AUTO_PAPER_AUTHORIZED"
    FLAG_FOR_HUMAN_REVIEW = "FLAG_FOR_HUMAN_REVIEW"
    LIVE_BLOCKED_NOT_LICENSED = "LIVE_BLOCKED_NOT_LICENSED"


@dataclass(frozen=True)
class PromotionThresholds:
    min_simulator_wins: int = 10
    min_walk_forward_windows: int = 10
    min_positive_routed_window_rate: float = 0.60
    min_mean_return_pct: float = 0.50
    max_drawdown_pct: float = 5.0
    min_trades: int = 30
    min_paper_days: int = 30
    require_paper_passed: bool = True


@dataclass
class StrategyPromotionCandidate:
    lead_id: str
    strategy_setting: str
    source: str
    simulator_wins: int = 0
    walk_forward_windows: int = 0
    positive_routed_window_rate: float = 0.0
    mean_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    trades: int = 0
    paper_days: int = 0
    paper_passed: bool = False
    evidence_refs: List[str] = field(default_factory=list)
    condition_contexts: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class OwnerPromotionDecision:
    verdict: OwnerPromotionVerdict
    reasons: List[str]
    owner_mode: OwnerControlMode
    max_paper_trades_authorized: int = 0
    notification_required: bool = True
    can_place_live_trades: bool = False
    can_transfer_money: bool = False
    claim_boundary: str = CLAIM_BOUNDARY


def review_owner_promotion(
    candidate: StrategyPromotionCandidate,
    *,
    owner_mode: OwnerControlMode = OwnerControlMode.NOTIFY_ONLY,
    thresholds: PromotionThresholds = PromotionThresholds(),
    max_paper_trades: int = 1,
) -> OwnerPromotionDecision:
    """Review whether a strategy candidate can move beyond research review."""
    if owner_mode == OwnerControlMode.DENY:
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.DENIED,
            reasons=["Owner mode is DENY."],
            owner_mode=owner_mode,
        )

    if owner_mode in {OwnerControlMode.LIVE_AUTO, OwnerControlMode.AI_FULL_AUTO_LIVE_REQUESTED}:
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.LIVE_BLOCKED_NOT_LICENSED,
            reasons=[
                f"Owner requested {owner_mode.value}, but live trading remains NOT LICENSED.",
                "Broker execution and payment transfers require separate legal/broker/paper-proof gates.",
            ],
            owner_mode=owner_mode,
        )

    blockers = _threshold_blockers(candidate, thresholds)
    if not candidate.evidence_refs:
        blockers.append("Candidate has no evidence_refs.")
    if not candidate.condition_contexts:
        blockers.append("Candidate has no condition_contexts.")

    if blockers:
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.NOTIFY,
            reasons=blockers,
            owner_mode=owner_mode,
        )

    if owner_mode == OwnerControlMode.NOTIFY_ONLY:
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.NOTIFY,
            reasons=["Candidate meets thresholds, but owner mode is NOTIFY_ONLY."],
            owner_mode=owner_mode,
        )

    if owner_mode == OwnerControlMode.LIMITED_PAPER:
        allowed = min(max(1, int(max_paper_trades)), MAX_OWNER_AUTO_TRADES)
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.LIMITED_PAPER_AUTHORIZED,
            reasons=[f"Candidate meets thresholds; limited paper attempts capped at {allowed}."],
            owner_mode=owner_mode,
            max_paper_trades_authorized=allowed,
        )

    if owner_mode == OwnerControlMode.PAPER_AUTO:
        allowed = min(max(1, int(max_paper_trades)), MAX_OWNER_AUTO_TRADES)
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.PAPER_AUTO_AUTHORIZED,
            reasons=[f"Candidate meets thresholds for paper-mode auto routing, capped at {allowed} trades."],
            owner_mode=owner_mode,
            max_paper_trades_authorized=allowed,
            notification_required=False,
        )

    if owner_mode == OwnerControlMode.AI_FULL_AUTO_PAPER:
        allowed = min(max(1, int(max_paper_trades)), MAX_OWNER_AUTO_TRADES)
        return OwnerPromotionDecision(
            verdict=OwnerPromotionVerdict.AI_FULL_AUTO_PAPER_AUTHORIZED,
            reasons=[
                "Owner authorized AI_FULL_AUTO_PAPER.",
                f"AI may choose paper-mode route/settings/risk within evidence gates, capped at {allowed} trades.",
            ],
            owner_mode=owner_mode,
            max_paper_trades_authorized=allowed,
            notification_required=False,
        )

    return OwnerPromotionDecision(
        verdict=OwnerPromotionVerdict.FLAG_FOR_HUMAN_REVIEW,
        reasons=[f"Unsupported owner mode: {owner_mode}"],
        owner_mode=owner_mode,
    )


def candidate_from_tally_bucket(
    bucket: Mapping[str, Any],
    *,
    lead_id: str,
    source: str,
    simulator_wins: int = 0,
    paper_days: int = 0,
    paper_passed: bool = False,
    evidence_refs: Optional[List[str]] = None,
) -> StrategyPromotionCandidate:
    """Build a promotion candidate from a condition-tally bucket."""
    axes: Mapping[str, Any] = bucket.get("axes", {}) if isinstance(bucket.get("axes"), Mapping) else {}
    setting = str(axes.get("setting") or bucket.get("setting") or "unknown")
    contexts = [
        str(value)
        for key, value in axes.items()
        if key in {"test_event_context", "event_context", "test_regime", "regime", "timeframe", "symbol"}
    ]
    return StrategyPromotionCandidate(
        lead_id=lead_id,
        strategy_setting=setting,
        source=source,
        simulator_wins=simulator_wins,
        walk_forward_windows=int(bucket.get("routed_windows", bucket.get("windows", 0)) or 0),
        positive_routed_window_rate=float(bucket.get("positive_window_rate", 0.0) or 0.0),
        mean_return_pct=float(bucket.get("mean_return_pct", 0.0) or 0.0),
        max_drawdown_pct=float(bucket.get("max_drawdown_pct", 0.0) or 0.0),
        trades=int(bucket.get("trades", 0) or 0),
        paper_days=paper_days,
        paper_passed=paper_passed,
        evidence_refs=list(evidence_refs or []),
        condition_contexts=contexts,
    )


def count_condition_lab_simulator_wins(
    cells: Sequence[Mapping[str, Any]],
    *,
    setting: Optional[str] = None,
    min_return_pct: float = 0.0,
    max_drawdown_pct: float = 20.0,
    min_trades: float = 1.0,
    require_non_gap: bool = True,
) -> int:
    """Count Condition Lab cells that qualify as simulator wins."""
    wins = 0
    for cell in cells:
        if setting and cell.get("setting") != setting:
            continue
        if require_non_gap and bool(cell.get("is_gap", True)):
            continue
        if float(cell.get("mean_return_pct", 0.0) or 0.0) < min_return_pct:
            continue
        if float(cell.get("mean_max_dd_pct", 0.0) or 0.0) > max_drawdown_pct:
            continue
        if float(cell.get("mean_trades", 0.0) or 0.0) < min_trades:
            continue
        wins += 1
    return wins


def _threshold_blockers(
    candidate: StrategyPromotionCandidate,
    thresholds: PromotionThresholds,
) -> List[str]:
    blockers: List[str] = []
    if candidate.simulator_wins < thresholds.min_simulator_wins:
        blockers.append(
            f"simulator_wins {candidate.simulator_wins} < required {thresholds.min_simulator_wins}"
        )
    if candidate.walk_forward_windows < thresholds.min_walk_forward_windows:
        blockers.append(
            f"walk_forward_windows {candidate.walk_forward_windows} < required {thresholds.min_walk_forward_windows}"
        )
    if candidate.positive_routed_window_rate < thresholds.min_positive_routed_window_rate:
        blockers.append(
            "positive_routed_window_rate "
            f"{candidate.positive_routed_window_rate:.4f} < required {thresholds.min_positive_routed_window_rate:.4f}"
        )
    if candidate.mean_return_pct < thresholds.min_mean_return_pct:
        blockers.append(
            f"mean_return_pct {candidate.mean_return_pct:.4f} < required {thresholds.min_mean_return_pct:.4f}"
        )
    if candidate.max_drawdown_pct > thresholds.max_drawdown_pct:
        blockers.append(
            f"max_drawdown_pct {candidate.max_drawdown_pct:.4f} > allowed {thresholds.max_drawdown_pct:.4f}"
        )
    if candidate.trades < thresholds.min_trades:
        blockers.append(f"trades {candidate.trades} < required {thresholds.min_trades}")
    if candidate.paper_days < thresholds.min_paper_days:
        blockers.append(f"paper_days {candidate.paper_days} < required {thresholds.min_paper_days}")
    if thresholds.require_paper_passed and not candidate.paper_passed:
        blockers.append("paper_passed is false.")
    return blockers
