"""Tests for CAS Forex synthetic scenario templates."""

from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.market import MarketSnapshot
from cas_forex.sdg import DEFAULT_TEMPLATES, generate_forex_scenarios
from cas_forex.verifier.market_gate import MarketGate


def test_sdg_generates_compiler_clean_forex_scenarios():
    scenarios = generate_forex_scenarios()

    assert len(scenarios) == len(DEFAULT_TEMPLATES)
    assert {s["symbol"] for s in scenarios} >= {"EUR/USD", "USD/JPY"}
    for scenario in scenarios:
        assert scenario["candles"]
        assert scenario["compiler"]["state_valid"] is True
        assert scenario["compiler"]["relation_valid"] is scenario["expected"]["relation_valid"]
        assert scenario["compiler"]["recipe_valid"] is True
        assert "Ω_trade_profit" in scenario["cas_recipe"]

    trade_candidates = [s for s in scenarios if s["expected"]["trade_candidate"]]
    assert trade_candidates
    assert all(s["compiler"]["relation_valid"] is True for s in trade_candidates)


def test_sdg_preserves_template_guard_conditions():
    scenarios = {s["template"]: s for s in generate_forex_scenarios()}

    wide_spread = scenarios["eurusd_wide_spread_guard"]
    assert wide_spread["snapshot"]["spread"] == 8.0
    assert wide_spread["expected"]["relation_valid"] is False
    assert wide_spread["compiler"]["relation_valid"] is False
    result = MarketGate().evaluate(
        MarketSnapshot.model_validate(wide_spread["snapshot"]),
        Direction(wide_spread["direction"]),
        wide_spread["proposal"]["entry_price"],
    )
    assert result.status.value == "FAIL"
    assert "Spread" in result.reason
    assert scenarios["usdjpy_trend_long"]["proposal"]["entry_price"] > 100
