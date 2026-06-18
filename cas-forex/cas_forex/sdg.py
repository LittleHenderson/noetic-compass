"""CAS Forex synthetic data generation templates."""

from dataclasses import dataclass
from typing import Iterable, List

from cas_forex.compiler_bridge import (
    get_bridge,
    market_to_cas_recipe,
    market_to_cas_relation,
    market_to_cas_state,
)
from cas_forex.schemas.forecast import Direction, pip_multiplier
from cas_forex.schemas.market import MarketSnapshot


@dataclass(frozen=True)
class ForexScenarioTemplate:
    name: str
    symbol: str
    direction: Direction
    base_price: float
    drift_pips: float
    spread_pips: float = 1.0
    bars: int = 32
    confidence: float = 0.75
    expected_relation_valid: bool = True


DEFAULT_TEMPLATES = [
    ForexScenarioTemplate(
        name="eurusd_trend_long",
        symbol="EUR/USD",
        direction=Direction.LONG,
        base_price=1.1000,
        drift_pips=1.2,
    ),
    ForexScenarioTemplate(
        name="eurusd_trend_short",
        symbol="EUR/USD",
        direction=Direction.SHORT,
        base_price=1.1000,
        drift_pips=-1.2,
    ),
    ForexScenarioTemplate(
        name="usdjpy_trend_long",
        symbol="USD/JPY",
        direction=Direction.LONG,
        base_price=150.00,
        drift_pips=1.0,
    ),
    ForexScenarioTemplate(
        name="eurusd_wide_spread_guard",
        symbol="EUR/USD",
        direction=Direction.LONG,
        base_price=1.1000,
        drift_pips=0.2,
        spread_pips=8.0,
        confidence=0.45,
        expected_relation_valid=False,
    ),
]


def generate_candles(template: ForexScenarioTemplate) -> List[dict]:
    """Generate deterministic OHLC candles from a template."""
    pip_size = 1.0 / pip_multiplier(template.symbol)
    candles = []
    price = template.base_price
    for i in range(template.bars):
        open_price = price
        close = template.base_price + template.drift_pips * pip_size * i
        wiggle = pip_size * (1.0 + (i % 3) * 0.25)
        candles.append({
            "timestamp": f"2026-06-17T00:{i:02d}:00",
            "open": round(open_price, 5),
            "high": round(max(open_price, close) + wiggle, 5),
            "low": round(min(open_price, close) - wiggle, 5),
            "close": round(close, 5),
            "volume": 100 + i,
        })
        price = close
    return candles


def build_scenario(template: ForexScenarioTemplate) -> dict:
    """Build a CAS-compiled synthetic scenario packet."""
    candles = generate_candles(template)
    close = candles[-1]["close"]
    pip_size = 1.0 / pip_multiplier(template.symbol)
    half_spread = template.spread_pips * pip_size / 2.0
    snapshot = MarketSnapshot(
        symbol=template.symbol,
        bid=close - half_spread,
        ask=close + half_spread,
        spread=template.spread_pips,
        high=candles[-1]["high"],
        low=candles[-1]["low"],
        close=close,
        session="LONDON",
        is_market_open=True,
    )
    risk_pips = 20.0 if template.symbol != "USD/JPY" else 30.0
    if template.direction == Direction.LONG:
        stop_loss = close - risk_pips * pip_size
        take_profit = close + risk_pips * 2 * pip_size
    else:
        stop_loss = close + risk_pips * pip_size
        take_profit = close - risk_pips * 2 * pip_size

    cas_state = market_to_cas_state(snapshot, template.direction)
    cas_relation = market_to_cas_relation(
        snapshot,
        template.direction,
        close,
        stop_loss,
        take_profit,
    )
    cas_recipe = market_to_cas_recipe(
        snapshot,
        template.direction,
        template.confidence,
    )
    bridge = get_bridge()
    state_result = bridge.compile_expression(cas_state)
    relation_result = bridge.compile_expression(cas_relation)
    recipe_result = bridge.compile_expression(cas_recipe)

    return {
        "template": template.name,
        "symbol": template.symbol,
        "direction": template.direction.value,
        "candles": candles,
        "snapshot": snapshot.model_dump(mode="json"),
        "proposal": {
            "entry_price": round(close, 5),
            "stop_loss": round(stop_loss, 5),
            "take_profit": round(take_profit, 5),
            "confidence": template.confidence,
        },
        "cas_state": cas_state,
        "cas_relation": cas_relation,
        "cas_recipe": cas_recipe,
        "expected": {
            "relation_valid": template.expected_relation_valid,
            "trade_candidate": template.expected_relation_valid,
        },
        "compiler": {
            "state_valid": state_result.valid,
            "relation_valid": relation_result.valid,
            "relation_error": relation_result.error,
            "recipe_valid": recipe_result.valid,
            "recipe_error": recipe_result.error,
        },
    }


def generate_forex_scenarios(
    templates: Iterable[ForexScenarioTemplate] = DEFAULT_TEMPLATES,
) -> List[dict]:
    """Generate a deterministic batch of CAS Forex scenarios."""
    return [build_scenario(template) for template in templates]
