"""Hourly intraday paper route policy for the CAS Forex agent desk."""

from __future__ import annotations

from typing import Any, Mapping

from cas_forex.agent_state import RouteIntent
from cas_forex.instruments import default_mid, price_unit_size, round_price
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.order import BrokerOrderRequest, OrderType
from cas_forex.time_utils import utc_now


def build_hourly_intraday_intents(
    replay_candidates: Mapping[str, Any],
    replay_results: Mapping[str, Any],
) -> list[RouteIntent]:
    """Build the top H1/M15 intraday route intent from the replay queue."""

    candidate = _top_intraday_candidate(replay_candidates)
    if not candidate:
        return []
    symbol = str(candidate.get("cas_symbol") or "AUD/CAD")
    timeframe = str(candidate.get("timeframe") or "H1")
    setting = _setting_from_candidate(candidate)
    risk = candidate.get("risk_shape") if isinstance(candidate, Mapping) else {}
    lot_size = float((risk or {}).get("lot_size") or 0.01)
    take_profit_units = _intraday_units((risk or {}).get("take_profit"), default=12.0, max_units=200.0)
    stop_loss_units = _intraday_units((risk or {}).get("stop_loss"), default=36.0, max_units=500.0)
    unit = price_unit_size(symbol)
    entry = round_price(symbol, default_mid(symbol))
    stop_loss = round_price(symbol, entry - stop_loss_units * unit)
    take_profit = round_price(symbol, entry + take_profit_units * unit)
    score = float(candidate.get("score") or 0.0)
    confidence = min(0.88, max(0.5, score / 400.0))
    evidence_refs = _evidence_refs(replay_candidates, replay_results)
    order = BrokerOrderRequest(
        order_id=f"agent-hourly-{symbol.replace('/', '')}-{utc_now().strftime('%Y%m%d%H%M%S')}",
        decision_ref="hourly_intraday_agent:forex_fury_replay_candidates",
        symbol=symbol,
        order_type=OrderType.MARKET,
        direction=Direction.LONG,
        volume=lot_size,
        price=0.0,
        stop_loss=stop_loss,
        take_profit=take_profit,
        comment="CAS_HOURLY",
        magic_number=20260625,
    )
    return [
        RouteIntent(
            intent_id=f"intent-hourly-{symbol.replace('/', '').lower()}-{timeframe.lower()}",
            agent_id="hourly_intraday_agent",
            action="OPEN_INTRADAY_ROUTE",
            symbol=symbol,
            timeframe=timeframe,
            strategy_setting=setting,
            direction=Direction.LONG.value,
            confidence=round(confidence, 4),
            evidence_score=round(score, 4),
            lot_size=round(lot_size, 4),
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason="Top H1/M15 replay candidate is queued for intraday paper route review.",
            evidence_refs=_dedupe(evidence_refs),
            order_request=order.model_dump(mode="json"),
            market_geometry_policy="REPLAY_TEMPLATE_REQUIRES_CURRENT_DIRECTION",
        )
    ]


def _top_intraday_candidate(replay_candidates: Mapping[str, Any]) -> Mapping[str, Any]:
    candidates = [
        candidate
        for candidate in replay_candidates.get("candidates") or []
        if isinstance(candidate, Mapping) and candidate.get("timeframe") in {"M15", "H1"}
    ]
    if not candidates:
        return {}
    return max(candidates, key=lambda item: float(item.get("score") or 0.0))


def _setting_from_candidate(candidate: Mapping[str, Any]) -> str:
    family = str(candidate.get("family") or "intraday")
    timeframe = str(candidate.get("timeframe") or "H1")
    raw_symbol = str(candidate.get("raw_symbol") or candidate.get("cas_symbol") or "symbol")
    return f"forex_fury_{family}_{raw_symbol}_{timeframe}".lower().replace("/", "")


def _evidence_refs(replay_candidates: Mapping[str, Any], replay_results: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    if replay_candidates.get("report_path"):
        refs.append(str(replay_candidates["report_path"]))
    if replay_results.get("report_path"):
        refs.append(str(replay_results["report_path"]))
    return refs


def _intraday_units(value: object, *, default: float, max_units: float) -> float:
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
