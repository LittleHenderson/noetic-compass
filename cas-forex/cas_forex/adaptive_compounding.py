"""Adaptive paper compounding manager for CAS Forex.

This module turns a paper route signal plus current open-paper-position state
into a read-only management recommendation. It can recommend adding to a
winner, tightening stops, taking partial profit, or closing a basket, but it
does not place broker orders and does not create broker ACCEPT.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from cas_forex.config import config as runtime_config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.instruments import pip_value_per_lot, price_unit_size, round_price
from cas_forex.paper_proof import PaperProofPlan
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus
from cas_forex.schemas.forecast import Direction
from cas_forex.time_utils import utc_now


ADAPTIVE_COMPOUNDING_CLAIM_BOUNDARY = (
    "Adaptive compounding is research/paper-only. It does not place trades, "
    "create broker ACCEPT, authorize live trading, or authorize payment movement."
)


class AdaptiveAction(str, Enum):
    OPEN_INITIAL = "OPEN_INITIAL"
    ADD_TO_WINNER = "ADD_TO_WINNER"
    HOLD = "HOLD"
    TIGHTEN_STOP = "TIGHTEN_STOP"
    PARTIAL_TAKE_PROFIT = "PARTIAL_TAKE_PROFIT"
    CLOSE_BASKET = "CLOSE_BASKET"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True)
class AdaptivePosition:
    position_id: str
    symbol: str
    direction: str
    entry_price: float
    current_price: float
    lots: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: Optional[str] = None
    strategy_setting: Optional[str] = None


@dataclass(frozen=True)
class AdaptiveCompoundingConfig:
    max_basket_positions: int = 15
    base_lot: float = 0.01
    compound_lot_multiplier: float = 1.0
    max_add_lot: float = 1.0
    min_compound_profit_r: float = 0.5
    partial_take_profit_r: float = 2.0
    close_basket_loss_r: float = -1.0
    min_add_confidence: float = 0.55
    min_hold_confidence: float = 0.35
    min_evidence_score: float = 0.5
    adaptive_sl_mult: float = 1.5
    adaptive_tp_mult: float = 3.0


@dataclass(frozen=True)
class EvidenceMatch:
    status: str
    score: float
    refs: List[str] = field(default_factory=list)
    bucket: Optional[Dict[str, Any]] = None
    imported_summary: Optional[Dict[str, Any]] = None
    reasons: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class BasketState:
    basket_id: str
    symbol: str
    direction: str
    open_positions: int
    total_lots: float
    average_entry: Optional[float]
    current_price: Optional[float]
    floating_profit_units: float
    floating_profit_usd: float
    floating_profit_r: float
    best_stop_loss: Optional[float]
    farthest_take_profit: Optional[float]


@dataclass(frozen=True)
class AdaptiveTradeDecision:
    symbol: str
    action: str
    reason: str
    direction: Optional[str] = None
    lot_size: float = 0.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: Optional[float] = None
    evidence_score: float = 0.0
    evidence_status: str = "NO_MATCH"
    evidence_refs: List[str] = field(default_factory=list)
    basket_id: Optional[str] = None
    source_proposal_id: Optional[str] = None


@dataclass(frozen=True)
class AdaptiveMemorySnapshot:
    snapshot_id: str
    snapshot_type: str
    symbol: str
    timeframe: str
    strategy_setting: str
    event_context: str
    regime: str
    action: str
    direction: Optional[str]
    confidence: Optional[float]
    evidence_score: float
    basket_profit_r: float
    basket_open_positions: int
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AdaptiveCompoundingReview:
    review_id: str
    plan_id: str
    lead_id: str
    strategy_setting: str
    date: str
    timeframe: str
    source_decision_id: Optional[str]
    route_action: str
    account_equity: float
    config: Dict[str, Any]
    baskets: List[BasketState]
    decisions: List[AdaptiveTradeDecision]
    memory_snapshots: List[AdaptiveMemorySnapshot]
    notes: List[str] = field(default_factory=list)
    claim_boundary: str = ADAPTIVE_COMPOUNDING_CLAIM_BOUNDARY
    deployment_status: str = "NOT LICENSED"
    broker_accept_status: str = "NOT LICENSED"
    payment_transfer_status: str = "NOT LICENSED"


def adaptive_compounding_store_path(plan: PaperProofPlan, output_dir: str | Path) -> Path:
    return Path(output_dir) / f"{plan.plan_id}-adaptive-compounding.jsonl"


def review_adaptive_compounding(
    plan: PaperProofPlan,
    latest_decision: Mapping[str, Any],
    *,
    active_positions: Sequence[Mapping[str, Any] | AdaptivePosition] = (),
    condition_tally: Optional[Mapping[str, Any]] = None,
    imported_history_summary: Optional[Mapping[str, Any]] = None,
    account_equity: float = 5_000.0,
    config: Optional[AdaptiveCompoundingConfig] = None,
    trading_date: Optional[date] = None,
) -> AdaptiveCompoundingReview:
    """Build a paper-only adaptive compounding recommendation."""

    if runtime_config.live_mode or not runtime_config.paper_trading:
        raise PermissionError("Adaptive compounding requires paper_trading=True and live_mode=False.")
    if account_equity <= 0:
        raise ValueError("account_equity must be positive.")

    cfg = config or AdaptiveCompoundingConfig()
    day = trading_date or _decision_date(latest_decision)
    normalized_positions = [_normalize_position(item) for item in active_positions]
    route_action = str(latest_decision.get("route_action", "UNKNOWN"))
    symbol_decisions = latest_decision.get("symbol_decisions", [])
    if not isinstance(symbol_decisions, list):
        symbol_decisions = []

    decisions: List[AdaptiveTradeDecision] = []
    snapshots: List[AdaptiveMemorySnapshot] = []
    baskets: List[BasketState] = []

    routed_symbols: set[str] = set()
    for item in symbol_decisions:
        if not isinstance(item, Mapping):
            continue
        symbol = str(item.get("symbol", "UNKNOWN"))
        if str(item.get("action")) != "ROUTE_PAPER_SIGNAL":
            continue
        routed_symbols.add(symbol)
        proposal = item.get("proposal")
        if not isinstance(proposal, Mapping):
            decisions.append(
                AdaptiveTradeDecision(
                    symbol=symbol,
                    action=AdaptiveAction.NO_TRADE.value,
                    reason="Route candidate did not include a proposal payload.",
                )
            )
            continue
        symbol_positions = [pos for pos in normalized_positions if pos.symbol == symbol]
        decision, basket, snapshot = _review_symbol_candidate(
            plan,
            latest_decision,
            item,
            proposal,
            symbol_positions,
            condition_tally=condition_tally,
            imported_history_summary=imported_history_summary,
            cfg=cfg,
        )
        decisions.append(decision)
        baskets.append(basket)
        snapshots.append(snapshot)

    unmanaged_symbols = sorted({pos.symbol for pos in normalized_positions} - routed_symbols)
    for symbol in unmanaged_symbols:
        symbol_positions = [pos for pos in normalized_positions if pos.symbol == symbol]
        basket = _basket_state(symbol, symbol_positions)
        baskets.append(basket)
        action = AdaptiveAction.TIGHTEN_STOP.value if basket.floating_profit_r > 0 else AdaptiveAction.CLOSE_BASKET.value
        reason = (
            "Existing basket has no fresh route signal; protect current profit."
            if basket.floating_profit_r > 0
            else "Existing basket has no fresh route signal and is not winning."
        )
        decisions.append(
            AdaptiveTradeDecision(
                symbol=symbol,
                action=action,
                reason=reason,
                direction=basket.direction,
                stop_loss=_protective_stop(symbol, basket.direction, basket.current_price, basket.average_entry, cfg),
                confidence=None,
                evidence_status="NO_FRESH_ROUTE",
                basket_id=basket.basket_id,
            )
        )
        snapshots.append(
            _memory_snapshot(
                plan=plan,
                latest_decision=latest_decision,
                symbol=symbol,
                action=action,
                direction=basket.direction,
                confidence=None,
                evidence_score=0.0,
                basket=basket,
                notes=[reason],
            )
        )

    if not decisions:
        decisions.append(
            AdaptiveTradeDecision(
                symbol="ALL",
                action=AdaptiveAction.NO_TRADE.value,
                reason="No routed paper signals and no active positions were supplied.",
            )
        )

    notes = [
        "Adaptive paper compounding review generated; no broker order was placed.",
        ADAPTIVE_COMPOUNDING_CLAIM_BOUNDARY,
    ]
    return AdaptiveCompoundingReview(
        review_id=f"{plan.plan_id}-{day.isoformat()}-adaptive-compounding",
        plan_id=plan.plan_id,
        lead_id=plan.lead_id,
        strategy_setting=plan.strategy_setting,
        date=day.isoformat(),
        timeframe=str(latest_decision.get("timeframe", plan.timeframe)),
        source_decision_id=_optional_str(latest_decision.get("decision_id")),
        route_action=route_action,
        account_equity=round(float(account_equity), 2),
        config=asdict(cfg),
        baskets=baskets,
        decisions=decisions,
        memory_snapshots=snapshots,
        notes=notes,
    )


def append_adaptive_compounding_review(
    review: AdaptiveCompoundingReview,
    output_dir: str | Path,
) -> Dict[str, Any]:
    if runtime_config.live_mode or not runtime_config.paper_trading:
        raise PermissionError("Adaptive compounding requires paper_trading=True and live_mode=False.")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = PaperProofPlan(
        plan_id=review.plan_id,
        lead_id=review.lead_id,
        strategy_setting=review.strategy_setting,
        symbols=[decision.symbol for decision in review.decisions if decision.symbol != "ALL"],
        timeframe=review.timeframe,
    )
    store = EvidenceStore(
        adaptive_compounding_store_path(plan, out_dir),
        run_id=f"{review.plan_id}-adaptive-compounding",
    )
    payload = adaptive_compounding_payload(review)
    packet = ForexEvidencePacket(
        packet_id=str(uuid.uuid4()),
        trace_id=review.review_id,
        status=PacketStatus.SUPPRESSED,
        proposal=_first_decision_stub(review),
        notes=[*review.notes, "Broker ACCEPT remains NOT LICENSED."],
        close_outcome=payload,
    )
    packet.finalize()
    receipt = store.append(packet, source="adaptive-compounding-review")
    return {"review": payload, "receipt": receipt.model_dump(mode="json")}


def summarize_adaptive_compounding_reviews(plan: PaperProofPlan, output_dir: str | Path) -> Dict[str, Any]:
    store = EvidenceStore(
        adaptive_compounding_store_path(plan, output_dir),
        run_id=f"{plan.plan_id}-adaptive-compounding",
    )
    reviews: List[Dict[str, Any]] = []
    for record in store._records():
        packet = record.get("packet") if isinstance(record, Mapping) else None
        if not isinstance(packet, Mapping):
            continue
        outcome = packet.get("close_outcome")
        if isinstance(outcome, Mapping):
            reviews.append(dict(outcome))
    action_counts: Dict[str, int] = {}
    for review in reviews:
        for decision in review.get("decisions", []):
            if not isinstance(decision, Mapping):
                continue
            action = str(decision.get("action", "UNKNOWN"))
            action_counts[action] = action_counts.get(action, 0) + 1
    return {
        "plan_id": plan.plan_id,
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "review_count": len(reviews),
        "action_counts": action_counts,
        "chain_verified": store.verify_chain(),
        "latest_review": reviews[-1] if reviews else None,
        "claim_boundary": ADAPTIVE_COMPOUNDING_CLAIM_BOUNDARY,
        "deployment_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "payment_transfer_status": "NOT LICENSED",
    }


def write_adaptive_compounding_status(plan: PaperProofPlan, output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status = summarize_adaptive_compounding_reviews(plan, out_dir)
    path = out_dir / f"{plan.plan_id}-adaptive-compounding-status.json"
    path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return path


def adaptive_compounding_payload(review: AdaptiveCompoundingReview) -> Dict[str, Any]:
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
        "config": dict(review.config),
        "baskets": [asdict(item) for item in review.baskets],
        "decisions": [asdict(item) for item in review.decisions],
        "memory_snapshots": [asdict(item) for item in review.memory_snapshots],
        "notes": list(review.notes),
        "claim_boundary": review.claim_boundary,
        "deployment_status": review.deployment_status,
        "broker_accept_status": review.broker_accept_status,
        "payment_transfer_status": review.payment_transfer_status,
    }


def _review_symbol_candidate(
    plan: PaperProofPlan,
    latest_decision: Mapping[str, Any],
    item: Mapping[str, Any],
    proposal: Mapping[str, Any],
    positions: Sequence[AdaptivePosition],
    *,
    condition_tally: Optional[Mapping[str, Any]],
    imported_history_summary: Optional[Mapping[str, Any]],
    cfg: AdaptiveCompoundingConfig,
) -> tuple[AdaptiveTradeDecision, BasketState, AdaptiveMemorySnapshot]:
    symbol = str(proposal.get("symbol", item.get("symbol", "UNKNOWN")))
    direction = _direction_value(proposal.get("direction", item.get("direction")))
    confidence = _float_or_none(proposal.get("confidence", item.get("confidence")))
    entry = float(proposal.get("entry_price", item.get("latest_close", 0.0)) or 0.0)
    stop = _float_or_none(proposal.get("stop_loss"))
    target = _float_or_none(proposal.get("take_profit"))
    basket = _basket_state(symbol, positions, fallback_direction=direction, fallback_price=entry)
    evidence = _match_evidence(
        symbol=symbol,
        timeframe=str(latest_decision.get("timeframe", plan.timeframe)),
        strategy_setting=plan.strategy_setting,
        event_context=str(latest_decision.get("event_context", "normal") or "normal"),
        condition_tally=condition_tally,
        imported_history_summary=imported_history_summary,
    )

    if not positions:
        decision = AdaptiveTradeDecision(
            symbol=symbol,
            action=AdaptiveAction.OPEN_INITIAL.value,
            reason="Fresh paper route signal with no existing basket.",
            direction=direction,
            lot_size=cfg.base_lot,
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            confidence=confidence,
            evidence_score=evidence.score,
            evidence_status=evidence.status,
            evidence_refs=evidence.refs,
            basket_id=basket.basket_id,
            source_proposal_id=_optional_str(proposal.get("proposal_id")),
        )
        snapshot = _memory_snapshot(
            plan=plan,
            latest_decision=latest_decision,
            symbol=symbol,
            action=decision.action,
            direction=direction,
            confidence=confidence,
            evidence_score=evidence.score,
            basket=basket,
            notes=["Initial route candidate saved for future analysis."],
        )
        return decision, basket, snapshot

    if basket.direction and direction and basket.direction != direction:
        decision = AdaptiveTradeDecision(
            symbol=symbol,
            action=AdaptiveAction.CLOSE_BASKET.value,
            reason="Fresh signal direction conflicts with the existing basket.",
            direction=basket.direction,
            confidence=confidence,
            evidence_score=evidence.score,
            evidence_status=evidence.status,
            evidence_refs=evidence.refs,
            basket_id=basket.basket_id,
            source_proposal_id=_optional_str(proposal.get("proposal_id")),
        )
        snapshot = _memory_snapshot(
            plan=plan,
            latest_decision=latest_decision,
            symbol=symbol,
            action=decision.action,
            direction=basket.direction,
            confidence=confidence,
            evidence_score=evidence.score,
            basket=basket,
            notes=[decision.reason],
        )
        return decision, basket, snapshot

    if basket.floating_profit_r <= cfg.close_basket_loss_r:
        action = AdaptiveAction.CLOSE_BASKET
        reason = "Basket hit the configured loss-R stop."
    elif basket.floating_profit_r >= cfg.partial_take_profit_r:
        action = AdaptiveAction.PARTIAL_TAKE_PROFIT
        reason = "Basket profit reached the partial take-profit R threshold."
    elif evidence.score < cfg.min_evidence_score or (confidence is not None and confidence < cfg.min_hold_confidence):
        action = AdaptiveAction.TIGHTEN_STOP
        reason = "Condition evidence or signal confidence weakened; protect the winner."
    elif (
        basket.floating_profit_r >= cfg.min_compound_profit_r
        and basket.open_positions < cfg.max_basket_positions
        and confidence is not None
        and confidence >= cfg.min_add_confidence
    ):
        action = AdaptiveAction.ADD_TO_WINNER
        reason = "Existing basket is winning and evidence still supports the route."
    elif basket.open_positions >= cfg.max_basket_positions:
        action = AdaptiveAction.HOLD
        reason = "Basket is winning but max basket position count is already reached."
    else:
        action = AdaptiveAction.HOLD
        reason = "Fresh route remains aligned, but compounding threshold is not met."

    managed_entry = basket.current_price or entry
    managed_stop = _managed_stop(symbol, direction, managed_entry, basket, cfg, proposal_stop=stop)
    managed_target = _managed_target(symbol, direction, managed_entry, cfg, proposal_target=target)
    lot_size = 0.0
    if action == AdaptiveAction.ADD_TO_WINNER:
        seed_lot = positions[-1].lots if positions else cfg.base_lot
        lot_size = min(max(seed_lot * cfg.compound_lot_multiplier, cfg.base_lot), cfg.max_add_lot)

    decision = AdaptiveTradeDecision(
        symbol=symbol,
        action=action.value,
        reason=reason,
        direction=direction or basket.direction,
        lot_size=round(lot_size, 4),
        entry_price=round_price(symbol, managed_entry) if managed_entry else None,
        stop_loss=managed_stop,
        take_profit=managed_target,
        confidence=confidence,
        evidence_score=evidence.score,
        evidence_status=evidence.status,
        evidence_refs=evidence.refs,
        basket_id=basket.basket_id,
        source_proposal_id=_optional_str(proposal.get("proposal_id")),
    )
    snapshot = _memory_snapshot(
        plan=plan,
        latest_decision=latest_decision,
        symbol=symbol,
        action=decision.action,
        direction=direction or basket.direction,
        confidence=confidence,
        evidence_score=evidence.score,
        basket=basket,
        notes=[reason, *evidence.reasons],
    )
    return decision, basket, snapshot


def _match_evidence(
    *,
    symbol: str,
    timeframe: str,
    strategy_setting: str,
    event_context: str,
    condition_tally: Optional[Mapping[str, Any]],
    imported_history_summary: Optional[Mapping[str, Any]],
) -> EvidenceMatch:
    refs: List[str] = []
    reasons: List[str] = []
    best_bucket = _best_condition_bucket(condition_tally, symbol, timeframe, strategy_setting, event_context)
    bucket_score = 0.0
    if best_bucket:
        refs.append(f"condition_tally:{best_bucket.get('key', symbol)}")
        routed = float(best_bucket.get("routed_windows", 0) or 0)
        positive_rate = float(best_bucket.get("positive_window_rate", 0.0) or 0.0)
        active_rate = float(best_bucket.get("active_window_rate", 0.0) or 0.0)
        mean_return = float(best_bucket.get("mean_return_pct", 0.0) or 0.0)
        return_component = min(max(mean_return, 0.0) / 2.0, 1.0)
        bucket_score = (
            0.45 * positive_rate
            + 0.20 * active_rate
            + 0.25 * return_component
            + (0.10 if routed >= 3 else 0.0)
        )
        reasons.append(
            f"Condition bucket positive_rate={positive_rate:.4f}, mean_return_pct={mean_return:.4f}."
        )

    imported = _history_symbol_summary(imported_history_summary, symbol)
    import_score = 0.0
    if imported:
        refs.append(f"imported_history:{symbol}")
        win_rate = float(imported.get("win_rate", 0.0) or 0.0)
        profit_factor = float(imported.get("profit_factor", 0.0) or 0.0)
        profit_factor_component = min(max((profit_factor - 1.0) / 2.0, 0.0), 1.0)
        import_score = 0.65 * win_rate + 0.35 * profit_factor_component
        reasons.append(f"Imported history win_rate={win_rate:.4f}, profit_factor={profit_factor:.4f}.")

    score = round(max(bucket_score, import_score, (bucket_score + import_score) / 2.0), 4)
    if score >= 0.5:
        status = "EVIDENCE_SUPPORTS_COMPOUNDING"
    elif refs:
        status = "EVIDENCE_WEAK_OR_MIXED"
    else:
        status = "NO_MATCH"
        reasons.append("No matching condition tally or imported history bucket.")
    return EvidenceMatch(
        status=status,
        score=score,
        refs=refs,
        bucket=dict(best_bucket) if best_bucket else None,
        imported_summary=dict(imported) if imported else None,
        reasons=reasons,
    )


def _best_condition_bucket(
    tally: Optional[Mapping[str, Any]],
    symbol: str,
    timeframe: str,
    strategy_setting: str,
    event_context: str,
) -> Optional[Mapping[str, Any]]:
    if not tally:
        return None
    buckets = tally.get("buckets", [])
    if not isinstance(buckets, list):
        return None
    candidates: List[Mapping[str, Any]] = []
    for bucket in buckets:
        if not isinstance(bucket, Mapping):
            continue
        axes = bucket.get("axes", {})
        if not isinstance(axes, Mapping):
            axes = {}
        if axes.get("symbol") not in (None, "unknown", symbol):
            continue
        if axes.get("timeframe") not in (None, "unknown", timeframe):
            continue
        if axes.get("setting") not in (None, "unknown", strategy_setting):
            continue
        axis_event = axes.get("test_event_context", axes.get("event_context"))
        if axis_event not in (None, "unknown", event_context):
            continue
        candidates.append(bucket)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda bucket: (
            int(bucket.get("routed_windows", 0) or 0),
            float(bucket.get("positive_window_rate", 0.0) or 0.0),
            float(bucket.get("mean_return_pct", 0.0) or 0.0),
            -float(bucket.get("max_drawdown_pct", 0.0) or 0.0),
        ),
    )


def _history_symbol_summary(summary: Optional[Mapping[str, Any]], symbol: str) -> Optional[Mapping[str, Any]]:
    if not summary:
        return None
    by_symbol = summary.get("by_symbol", {})
    if isinstance(by_symbol, Mapping) and symbol in by_symbol and isinstance(by_symbol[symbol], Mapping):
        return by_symbol[symbol]
    return None


def _basket_state(
    symbol: str,
    positions: Sequence[AdaptivePosition],
    *,
    fallback_direction: Optional[str] = None,
    fallback_price: Optional[float] = None,
) -> BasketState:
    direction = positions[0].direction if positions else (fallback_direction or "UNKNOWN")
    total_lots = sum(max(pos.lots, 0.0) for pos in positions)
    current_price = positions[-1].current_price if positions else fallback_price
    average_entry = (
        sum(pos.entry_price * pos.lots for pos in positions) / max(total_lots, 1e-9)
        if positions
        else fallback_price
    )
    floating_units = 0.0
    floating_usd = 0.0
    weighted_risk_units = 0.0
    best_stop = None
    farthest_target = None
    if positions:
        unit = price_unit_size(symbol)
        unit_value = pip_value_per_lot(symbol, current_price or average_entry or 1.0)
        for pos in positions:
            signed_units = _signed_profit_units(symbol, pos.direction, pos.entry_price, pos.current_price)
            floating_units += signed_units * pos.lots
            floating_usd += signed_units * unit_value * pos.lots
            if pos.stop_loss:
                weighted_risk_units += abs(pos.entry_price - pos.stop_loss) / unit * pos.lots
            if pos.stop_loss is not None:
                if best_stop is None:
                    best_stop = pos.stop_loss
                elif direction == Direction.LONG.value:
                    best_stop = max(best_stop, pos.stop_loss)
                elif direction == Direction.SHORT.value:
                    best_stop = min(best_stop, pos.stop_loss)
            if pos.take_profit is not None:
                if farthest_target is None:
                    farthest_target = pos.take_profit
                elif direction == Direction.LONG.value:
                    farthest_target = max(farthest_target, pos.take_profit)
                elif direction == Direction.SHORT.value:
                    farthest_target = min(farthest_target, pos.take_profit)
    profit_r = floating_units / max(weighted_risk_units, 1e-9) if weighted_risk_units else 0.0
    return BasketState(
        basket_id=f"{symbol}-{direction}-paper-basket",
        symbol=symbol,
        direction=direction,
        open_positions=len(positions),
        total_lots=round(total_lots, 4),
        average_entry=round_price(symbol, average_entry) if average_entry else None,
        current_price=round_price(symbol, current_price) if current_price else None,
        floating_profit_units=round(floating_units, 4),
        floating_profit_usd=round(floating_usd, 2),
        floating_profit_r=round(profit_r, 4),
        best_stop_loss=round_price(symbol, best_stop) if best_stop else None,
        farthest_take_profit=round_price(symbol, farthest_target) if farthest_target else None,
    )


def _managed_stop(
    symbol: str,
    direction: Optional[str],
    current_price: float,
    basket: BasketState,
    cfg: AdaptiveCompoundingConfig,
    *,
    proposal_stop: Optional[float],
) -> Optional[float]:
    if current_price <= 0 or direction not in {Direction.LONG.value, Direction.SHORT.value}:
        return proposal_stop
    distance = max(price_unit_size(symbol) * cfg.adaptive_sl_mult, price_unit_size(symbol))
    if direction == Direction.LONG.value:
        candidates = [current_price - distance]
        if proposal_stop is not None:
            candidates.append(proposal_stop)
        if basket.average_entry and basket.floating_profit_r > 0:
            candidates.append(basket.average_entry)
        return round_price(symbol, max(candidates))
    candidates = [current_price + distance]
    if proposal_stop is not None:
        candidates.append(proposal_stop)
    if basket.average_entry and basket.floating_profit_r > 0:
        candidates.append(basket.average_entry)
    return round_price(symbol, min(candidates))


def _managed_target(
    symbol: str,
    direction: Optional[str],
    current_price: float,
    cfg: AdaptiveCompoundingConfig,
    *,
    proposal_target: Optional[float],
) -> Optional[float]:
    if current_price <= 0 or direction not in {Direction.LONG.value, Direction.SHORT.value}:
        return proposal_target
    distance = max(price_unit_size(symbol) * cfg.adaptive_tp_mult, price_unit_size(symbol))
    if direction == Direction.LONG.value:
        candidates = [current_price + distance]
        if proposal_target is not None:
            candidates.append(proposal_target)
        return round_price(symbol, max(candidates))
    candidates = [current_price - distance]
    if proposal_target is not None:
        candidates.append(proposal_target)
    return round_price(symbol, min(candidates))


def _protective_stop(
    symbol: str,
    direction: str,
    current_price: Optional[float],
    average_entry: Optional[float],
    cfg: AdaptiveCompoundingConfig,
) -> Optional[float]:
    if current_price is None or direction not in {Direction.LONG.value, Direction.SHORT.value}:
        return None
    distance = max(price_unit_size(symbol) * cfg.adaptive_sl_mult, price_unit_size(symbol))
    if direction == Direction.LONG.value:
        return round_price(symbol, max(current_price - distance, average_entry or 0.0))
    return round_price(symbol, min(current_price + distance, average_entry or current_price + distance))


def _memory_snapshot(
    *,
    plan: PaperProofPlan,
    latest_decision: Mapping[str, Any],
    symbol: str,
    action: str,
    direction: Optional[str],
    confidence: Optional[float],
    evidence_score: float,
    basket: BasketState,
    notes: Sequence[str],
) -> AdaptiveMemorySnapshot:
    if basket.floating_profit_r > 0 and action in {
        AdaptiveAction.ADD_TO_WINNER.value,
        AdaptiveAction.PARTIAL_TAKE_PROFIT.value,
        AdaptiveAction.HOLD.value,
        AdaptiveAction.TIGHTEN_STOP.value,
    }:
        snapshot_type = "WINNING_CONDITION"
    elif basket.floating_profit_r < 0:
        snapshot_type = "LOSING_CONDITION"
    elif action == AdaptiveAction.OPEN_INITIAL.value:
        snapshot_type = "INITIAL_ROUTE_CONDITION"
    else:
        snapshot_type = "NEUTRAL_CONDITION"
    return AdaptiveMemorySnapshot(
        snapshot_id=f"{symbol}-{utc_now().strftime('%Y%m%d%H%M%S%f')}",
        snapshot_type=snapshot_type,
        symbol=symbol,
        timeframe=str(latest_decision.get("timeframe", plan.timeframe)),
        strategy_setting=plan.strategy_setting,
        event_context=str(latest_decision.get("event_context", "normal") or "normal"),
        regime=str(latest_decision.get("regime", "unknown") or "unknown"),
        action=action,
        direction=direction,
        confidence=confidence,
        evidence_score=evidence_score,
        basket_profit_r=basket.floating_profit_r,
        basket_open_positions=basket.open_positions,
        notes=list(notes),
    )


def _normalize_position(item: Mapping[str, Any] | AdaptivePosition) -> AdaptivePosition:
    if isinstance(item, AdaptivePosition):
        return item
    return AdaptivePosition(
        position_id=str(item.get("position_id", item.get("ticket", item.get("order_id", "paper-position")))),
        symbol=str(item.get("symbol", "UNKNOWN")),
        direction=_direction_value(item.get("direction", item.get("type"))) or "UNKNOWN",
        entry_price=float(item.get("entry_price", item.get("open_price", 0.0)) or 0.0),
        current_price=float(item.get("current_price", item.get("price", item.get("entry_price", 0.0))) or 0.0),
        lots=float(item.get("lots", item.get("volume", item.get("size", 0.0))) or 0.0),
        stop_loss=_float_or_none(item.get("stop_loss", item.get("sl"))),
        take_profit=_float_or_none(item.get("take_profit", item.get("tp"))),
        opened_at=_optional_str(item.get("opened_at", item.get("open_time"))),
        strategy_setting=_optional_str(item.get("strategy_setting")),
    )


def _signed_profit_units(symbol: str, direction: str, entry: float, current: float) -> float:
    unit = price_unit_size(symbol)
    if direction == Direction.LONG.value:
        return (current - entry) / unit
    if direction == Direction.SHORT.value:
        return (entry - current) / unit
    return 0.0


def _direction_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value.value if hasattr(value, "value") else value).strip().upper()
    if raw in {"LONG", "BUY"}:
        return Direction.LONG.value
    if raw in {"SHORT", "SELL"}:
        return Direction.SHORT.value
    return raw or None


def _decision_date(latest_decision: Mapping[str, Any]) -> date:
    value = latest_decision.get("date")
    if value:
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            pass
    return utc_now().date()


def _float_or_none(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _first_decision_stub(review: AdaptiveCompoundingReview) -> Optional[Dict[str, Any]]:
    for decision in review.decisions:
        if decision.symbol != "ALL":
            return {
                "proposal_id": decision.source_proposal_id or review.review_id,
                "symbol": decision.symbol,
                "direction": decision.direction,
                "entry_price": decision.entry_price,
                "stop_loss": decision.stop_loss,
                "take_profit": decision.take_profit,
                "timeframe": review.timeframe,
                "action": decision.action,
            }
    return None
