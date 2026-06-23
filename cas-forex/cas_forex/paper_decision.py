"""Daily paper route/no-trade decisions for CAS FOREX.

This is the companion ledger to paper broker receipts. It records what CAS would
do in paper mode for a lead on a given day, without placing orders or creating
broker ACCEPT.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from cas_forex.condition_lab import (
    build_strategy_settings,
    default_real_period_for_timeframe,
    yfinance_interval_for_timeframe,
)
from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.event_context import EVENT_CONTEXT_NORMAL, normalize_event_context
from cas_forex.instruments import price_unit_size, round_price, yahoo_ticker
from cas_forex.market_data.connector import YFinanceConnector
from cas_forex.paper_proof import PaperProofPlan
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus
from cas_forex.schemas.forecast import ForecastProposal, ModelSource
from cas_forex.time_utils import utc_now
from cas_forex.verifier.macro_gate import MacroGate


PAPER_DECISION_CLAIM_BOUNDARY = (
    "Paper route decisions are research/paper-only. "
    "They do not place trades, create broker ACCEPT, or authorize live money."
)


@dataclass(frozen=True)
class PaperSymbolDecision:
    symbol: str
    action: str
    reason: str
    latest_close: Optional[float] = None
    direction: Optional[str] = None
    confidence: Optional[float] = None
    sl_mult: Optional[float] = None
    tp_mult: Optional[float] = None
    proposal: Optional[Dict[str, Any]] = None
    bars_used: int = 0


@dataclass(frozen=True)
class PaperRouteDecision:
    decision_id: str
    plan_id: str
    lead_id: str
    strategy_setting: str
    date: str
    timeframe: str
    route_action: str
    event_context: str
    macro_status: str
    macro_reason: str
    symbol_decisions: List[PaperSymbolDecision] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    claim_boundary: str = PAPER_DECISION_CLAIM_BOUNDARY


def paper_decision_store_path(plan: PaperProofPlan, output_dir: str | Path) -> Path:
    """Return the append-only daily paper-decision chain path."""

    return Path(output_dir) / f"{plan.plan_id}-paper-decisions.jsonl"


def evaluate_paper_route_decision(
    plan: PaperProofPlan,
    *,
    trading_date: Optional[date] = None,
    candles_by_symbol: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    market_connector: Optional[Any] = None,
    macro_gate: Optional[MacroGate] = None,
) -> PaperRouteDecision:
    """Evaluate the active strategy lead in paper mode for one trading date."""

    if config.live_mode or not config.paper_trading:
        raise PermissionError("Paper route decisions require paper_trading=True and live_mode=False.")

    day = trading_date or utc_now().date()
    setting = _strategy_setting(plan.strategy_setting)
    gate = macro_gate or MacroGate()
    decision_time = datetime.combine(day, time(21, 0), tzinfo=UTC)
    macro = gate.evaluate(at=decision_time)
    event_context = EVENT_CONTEXT_NORMAL
    if getattr(macro, "status", None) and str(macro.status).endswith("FAIL"):
        event_type = macro.evidence.get("event_type", "macro")
        event_context = normalize_event_context(f"pre_{event_type}")

    connector = market_connector or YFinanceConnector()
    symbol_decisions: List[PaperSymbolDecision] = []
    for symbol in plan.symbols:
        candles = list(candles_by_symbol.get(symbol, [])) if candles_by_symbol else []
        if not candles:
            candles = _fetch_historical_candles(
                symbol,
                bars=_minimum_bars(setting.params),
                timeframe=plan.timeframe,
                connector=connector,
            )
        symbol_decisions.append(_evaluate_symbol(symbol, plan, setting, candles))

    if str(macro.status).endswith("FAIL"):
        route_action = "NO_TRADE_MACRO_LOCK"
        notes = [f"Macro gate blocked paper route: {macro.reason}"]
    elif any(decision.action == "ROUTE_PAPER_SIGNAL" for decision in symbol_decisions):
        route_action = "ROUTE_PAPER_SIGNAL"
        notes = ["At least one symbol produced a paper signal; no broker order was placed."]
    elif any(decision.action == "UNAVAILABLE" for decision in symbol_decisions):
        route_action = "UNAVAILABLE"
        notes = ["Market data was unavailable for at least one symbol."]
    else:
        route_action = "NO_TRADE"
        notes = ["No symbol met the strategy signal requirements."]

    return PaperRouteDecision(
        decision_id=f"{plan.plan_id}-{day.isoformat()}-paper-decision",
        plan_id=plan.plan_id,
        lead_id=plan.lead_id,
        strategy_setting=plan.strategy_setting,
        date=day.isoformat(),
        timeframe=plan.timeframe,
        route_action=route_action,
        event_context=event_context,
        macro_status=str(macro.status.value if hasattr(macro.status, "value") else macro.status),
        macro_reason=str(macro.reason),
        symbol_decisions=symbol_decisions,
        notes=notes,
    )


def append_paper_route_decision(
    decision: PaperRouteDecision,
    output_dir: str | Path,
) -> Dict[str, Any]:
    """Append a paper route decision to its tamper-evident local chain."""

    if config.live_mode or not config.paper_trading:
        raise PermissionError("Paper route decisions require paper_trading=True and live_mode=False.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    store = EvidenceStore(
        paper_decision_store_path(
            PaperProofPlan(
                plan_id=decision.plan_id,
                lead_id=decision.lead_id,
                strategy_setting=decision.strategy_setting,
                symbols=[item.symbol for item in decision.symbol_decisions],
                timeframe=decision.timeframe,
            ),
            out_dir,
        ),
        run_id=f"{decision.plan_id}-paper-decisions",
    )
    payload = _decision_payload(decision)
    packet = ForexEvidencePacket(
        packet_id=str(uuid.uuid4()),
        trace_id=decision.decision_id,
        status=PacketStatus.SUPPRESSED,
        proposal=_first_proposal(decision),
        notes=[*decision.notes, PAPER_DECISION_CLAIM_BOUNDARY],
        close_outcome=payload,
    )
    packet.finalize()
    receipt = store.append(packet, source="paper-route-decision")
    return {"decision": payload, "receipt": receipt.model_dump(mode="json")}


def summarize_paper_route_decisions(plan: PaperProofPlan, output_dir: str | Path) -> Dict[str, Any]:
    """Summarize the paper-decision chain for proof UI and docs."""

    store = EvidenceStore(paper_decision_store_path(plan, output_dir), run_id=f"{plan.plan_id}-paper-decisions")
    decisions: List[Dict[str, Any]] = []
    for record in store._records():
        packet = record.get("packet") if isinstance(record, Mapping) else None
        if not isinstance(packet, Mapping):
            continue
        outcome = packet.get("close_outcome")
        if isinstance(outcome, Mapping):
            decisions.append(dict(outcome))
    route_counts: Dict[str, int] = {}
    for decision in decisions:
        action = str(decision.get("route_action", "UNKNOWN"))
        route_counts[action] = route_counts.get(action, 0) + 1
    return {
        "plan_id": plan.plan_id,
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "decision_count": len(decisions),
        "route_counts": route_counts,
        "chain_verified": store.verify_chain(),
        "latest_decision": decisions[-1] if decisions else None,
        "claim_boundary": PAPER_DECISION_CLAIM_BOUNDARY,
    }


def write_paper_route_decision_status(plan: PaperProofPlan, output_dir: str | Path) -> Path:
    """Write the latest route-decision status summary."""

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status = summarize_paper_route_decisions(plan, out_dir)
    path = out_dir / f"{plan.plan_id}-paper-decision-status.json"
    path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return path


def _evaluate_symbol(
    symbol: str,
    plan: PaperProofPlan,
    setting: Any,
    candles: Sequence[Mapping[str, Any]],
) -> PaperSymbolDecision:
    if len(candles) < _minimum_bars(setting.params):
        return PaperSymbolDecision(
            symbol=symbol,
            action="UNAVAILABLE",
            reason=f"Need at least {_minimum_bars(setting.params)} bars, got {len(candles)}.",
            bars_used=len(candles),
        )
    closes = [float(candle["close"]) for candle in candles if float(candle.get("close", 0) or 0) > 0]
    if len(closes) < _minimum_bars(setting.params):
        return PaperSymbolDecision(
            symbol=symbol,
            action="UNAVAILABLE",
            reason="Historical candles did not contain enough valid closes.",
            bars_used=len(closes),
        )
    signal = setting.make_signal()(closes)
    latest_close = closes[-1]
    if signal is None:
        return PaperSymbolDecision(
            symbol=symbol,
            action="NO_TRADE",
            reason="Strategy signal returned None.",
            latest_close=latest_close,
            bars_used=len(closes),
        )
    direction, confidence, *multiples = signal
    sl_mult = float(multiples[0]) if len(multiples) >= 1 else 2.0
    tp_mult = float(multiples[1]) if len(multiples) >= 2 else 4.0
    proposal = _proposal_from_signal(
        symbol=symbol,
        plan=plan,
        closes=closes,
        candles=candles,
        direction=direction,
        confidence=float(confidence),
        sl_mult=sl_mult,
        tp_mult=tp_mult,
    )
    return PaperSymbolDecision(
        symbol=symbol,
        action="ROUTE_PAPER_SIGNAL",
        reason="Strategy signal produced a paper route candidate.",
        latest_close=latest_close,
        direction=str(direction.value if hasattr(direction, "value") else direction),
        confidence=float(confidence),
        sl_mult=sl_mult,
        tp_mult=tp_mult,
        proposal=proposal.model_dump(mode="json"),
        bars_used=len(closes),
    )


def _proposal_from_signal(
    *,
    symbol: str,
    plan: PaperProofPlan,
    closes: Sequence[float],
    candles: Sequence[Mapping[str, Any]],
    direction: Any,
    confidence: float,
    sl_mult: float,
    tp_mult: float,
) -> ForecastProposal:
    entry = round_price(symbol, float(closes[-1]))
    atr = max(_atr(candles[-20:]), price_unit_size(symbol))
    risk = atr * sl_mult
    reward = atr * tp_mult
    if str(direction.value if hasattr(direction, "value") else direction) == "LONG":
        stop = round_price(symbol, entry - risk)
        target = round_price(symbol, entry + reward)
    else:
        stop = round_price(symbol, entry + risk)
        target = round_price(symbol, entry - reward)
    return ForecastProposal(
        proposal_id=f"{plan.plan_id}-{symbol}-{utc_now().strftime('%Y%m%d%H%M%S')}",
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
        confidence=confidence,
        model_source=ModelSource.TECHNICAL,
        model_version=f"paper-route:{plan.strategy_setting}",
        timeframe=plan.timeframe,
        horizon_minutes=1440,
        rationale=f"Paper-only route candidate from {plan.strategy_setting}; no broker order placed.",
    )


def _strategy_setting(name: str) -> Any:
    for setting in build_strategy_settings():
        if setting.name == name:
            return setting
    raise ValueError(f"Unknown strategy setting: {name}")


def _fetch_historical_candles(
    symbol: str,
    *,
    bars: int,
    timeframe: str,
    connector: Any,
) -> List[Dict[str, Any]]:
    interval = yfinance_interval_for_timeframe(timeframe)
    if interval:
        try:
            import yfinance as yf  # type: ignore

            ticker = yf.Ticker(yahoo_ticker(symbol))
            df = ticker.history(
                period=default_real_period_for_timeframe(timeframe),
                interval=interval,
                auto_adjust=False,
            )
            if df is not None and not df.empty:
                candles: List[Dict[str, Any]] = []
                for idx, row in df.tail(bars).iterrows():
                    candles.append(
                        {
                            "timestamp": idx.isoformat(),
                            "open": float(row["Open"]),
                            "high": float(row["High"]),
                            "low": float(row["Low"]),
                            "close": float(row["Close"]),
                            "volume": int(row.get("Volume", 0)),
                        }
                    )
                if candles:
                    return candles
        except Exception:
            pass
    return connector.fetch_historical(symbol, bars=bars, timeframe=timeframe)


def _minimum_bars(params: Mapping[str, Any]) -> int:
    values = [
        int(value)
        for key, value in params.items()
        if key.endswith("lookback") or key in {"lookback", "baseline"}
    ]
    return max(values or [120]) + 1


def _atr(candles: Sequence[Mapping[str, Any]]) -> float:
    if not candles:
        return 0.0
    true_ranges: List[float] = []
    prev_close: Optional[float] = None
    for candle in candles:
        high = float(candle.get("high", candle.get("close", 0)) or 0)
        low = float(candle.get("low", candle.get("close", 0)) or 0)
        close = float(candle.get("close", 0) or 0)
        if high <= 0 or low <= 0 or close <= 0:
            continue
        if prev_close is None:
            true_ranges.append(high - low)
        else:
            true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
        prev_close = close
    return max(sum(true_ranges) / len(true_ranges), 0.0) if true_ranges else 0.0


def _decision_payload(decision: PaperRouteDecision) -> Dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "plan_id": decision.plan_id,
        "lead_id": decision.lead_id,
        "strategy_setting": decision.strategy_setting,
        "date": decision.date,
        "timeframe": decision.timeframe,
        "route_action": decision.route_action,
        "event_context": decision.event_context,
        "macro_status": decision.macro_status,
        "macro_reason": decision.macro_reason,
        "symbol_decisions": [
            {
                "symbol": item.symbol,
                "action": item.action,
                "reason": item.reason,
                "latest_close": item.latest_close,
                "direction": item.direction,
                "confidence": item.confidence,
                "sl_mult": item.sl_mult,
                "tp_mult": item.tp_mult,
                "proposal": item.proposal,
                "bars_used": item.bars_used,
            }
            for item in decision.symbol_decisions
        ],
        "notes": list(decision.notes),
        "claim_boundary": decision.claim_boundary,
    }


def _first_proposal(decision: PaperRouteDecision) -> Optional[Dict[str, Any]]:
    for item in decision.symbol_decisions:
        if item.proposal:
            return item.proposal
    return None
