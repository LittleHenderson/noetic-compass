"""Micro-scalp paper route policy for the CAS Forex agent desk."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from cas_forex.agent_state import RouteIntent
from cas_forex.instruments import default_mid, price_unit_size, round_price
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderType
from cas_forex.time_utils import utc_now


def build_micro_scalp_intents(
    replay_results: Mapping[str, Any],
    replay_candidates: Optional[Mapping[str, Any]] = None,
) -> list[RouteIntent]:
    """Build M1/M5 small-profit route intents from the latest replay lead."""

    if replay_results.get("replay_verdict") != "REPLAY_LEAD_FOR_ADAPTIVE_REVIEW":
        return []
    cell = _top_cell(replay_results)
    if not cell:
        return []
    symbol = str(cell.get("symbol") or "AUD/CAD")
    timeframe = str(cell.get("timeframe") or "M5")
    setting = str(cell.get("setting") or "range_scalper_12_80")
    candidate = _candidate_for(replay_candidates or {}, symbol=symbol, timeframe=timeframe)
    risk = candidate.get("risk_shape") if isinstance(candidate, Mapping) else {}
    lot_size = float((risk or {}).get("lot_size") or 0.01)
    take_profit_units = _micro_units((risk or {}).get("take_profit"), default=5.0, max_units=25.0)
    stop_loss_units = _micro_units((risk or {}).get("stop_loss"), default=29.0, max_units=50.0)
    unit = price_unit_size(symbol)
    entry = round_price(symbol, default_mid(symbol))
    stop_loss = round_price(symbol, entry - stop_loss_units * unit)
    take_profit = round_price(symbol, entry + take_profit_units * unit)
    confidence = min(0.99, max(0.55, float(cell.get("win_rate") or 0.62)))
    evidence_score = float(cell.get("score") or 0.0)
    evidence_refs = _evidence_refs(replay_results, replay_candidates)
    order = BrokerOrderRequest(
        order_id=f"agent-micro-{symbol.replace('/', '')}-{utc_now().strftime('%Y%m%d%H%M%S')}",
        decision_ref="micro_scalp_agent:forex_fury_replay_results",
        symbol=symbol,
        order_type=OrderType.MARKET,
        direction=Direction.LONG,
        volume=lot_size,
        price=0.0,
        stop_loss=stop_loss,
        take_profit=take_profit,
        comment="CAS_MICRO_SCALP",
        magic_number=20260624,
    )
    return [
        RouteIntent(
            intent_id=f"intent-micro-{symbol.replace('/', '').lower()}-{timeframe.lower()}",
            agent_id="micro_scalp_agent",
            action="OPEN_MICRO_SCALP",
            symbol=symbol,
            timeframe=timeframe,
            strategy_setting=setting,
            direction=Direction.LONG.value,
            confidence=round(confidence, 4),
            evidence_score=round(evidence_score, 4),
            lot_size=round(lot_size, 4),
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=(
                "Forex Fury replay lead supports a short-timeframe small-profit route; "
                "paper MT4 command intent can be written after overseer approval."
            ),
            evidence_refs=_dedupe(evidence_refs),
            order_request=order.model_dump(mode="json"),
            market_geometry_policy="REPLAY_TEMPLATE_REQUIRES_CURRENT_DIRECTION",
        )
    ]


def _top_cell(replay_results: Mapping[str, Any]) -> Mapping[str, Any]:
    condition = replay_results.get("condition_summary") or {}
    if not isinstance(condition, Mapping):
        return {}
    cells = condition.get("top_condition_cells") or []
    for cell in cells:
        if isinstance(cell, Mapping) and str(cell.get("timeframe")) in {"M1", "M5"}:
            return cell
    return cells[0] if cells and isinstance(cells[0], Mapping) else {}


def _candidate_for(candidates: Mapping[str, Any], *, symbol: str, timeframe: str) -> Mapping[str, Any]:
    for candidate in candidates.get("candidates") or []:
        if not isinstance(candidate, Mapping):
            continue
        if candidate.get("cas_symbol") == symbol and candidate.get("timeframe") == timeframe:
            return candidate
    return {}


def _evidence_refs(replay_results: Mapping[str, Any], replay_candidates: Optional[Mapping[str, Any]]) -> list[str]:
    refs: list[str] = []
    if replay_results.get("report_path"):
        refs.append(str(replay_results["report_path"]))
    if replay_candidates and replay_candidates.get("report_path"):
        refs.append(str(replay_candidates["report_path"]))
    sources = replay_results.get("source_reports") or {}
    if isinstance(sources, Mapping):
        for source in sources.values():
            if isinstance(source, Mapping) and source.get("path"):
                refs.append(str(source["path"]))
    return refs


def _micro_units(value: object, *, default: float, max_units: float) -> float:
    try:
        parsed = float(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    if parsed <= 0 or parsed > max_units:
        return default
    return parsed


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
