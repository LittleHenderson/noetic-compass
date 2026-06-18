"""Regression tests for CAS recipe compilation and CAS-native gating."""

from cas_forex.compiler_bridge import get_bridge, market_to_cas_recipe
from cas_forex.forecast.cas_ensemble import CASNativeEnsemble
from cas_forex.forecast.integrity import ForecastIntegrityResult
from cas_forex.schemas.forecast import Direction, ForecastProposal, ModelSource
from cas_forex.schemas.market import MarketSnapshot


def _snapshot():
    return MarketSnapshot(
        symbol="EUR/USD",
        bid=1.1000,
        ask=1.1002,
        spread=2.0,
        close=1.1001,
        session="LONDON",
    )


def test_market_to_cas_recipe_uses_compilable_named_target():
    expr = market_to_cas_recipe(_snapshot(), Direction.LONG, 0.7)
    assert "Ω_trade_profit" in expr
    result = get_bridge().compile_expression(expr)
    assert result.valid, result.error


def test_cas_native_ensemble_rejects_failed_recipe_compile():
    class FakeModel:
        def predict(self, symbol, candles, horizon=60):
            return ForecastProposal(
                proposal_id="p-1",
                symbol=symbol,
                direction=Direction.LONG,
                entry_price=1.1000,
                stop_loss=1.0900,
                take_profit=1.1300,
                confidence=0.9,
                model_source=ModelSource.TECHNICAL,
                rationale="clean fake proposal",
            )

    class FakeResult:
        def __init__(self, valid, error=None):
            self.valid = valid
            self.error = error
            self.admissible = True
            self.domain_descent_ok = True
            self.relation = None

    class FakeBridge:
        def compile_expression(self, expression):
            if expression.startswith("Θ("):
                return FakeResult(False, "bad recipe")
            return FakeResult(True)

    class FakeIntegrity:
        def evaluate(self, *args, **kwargs):
            return ForecastIntegrityResult(
                rpm_chain_intact=True,
                lacunarity_score=1.0,
                leakage_detected=False,
            )

    ensemble = CASNativeEnsemble()
    ensemble.models = [FakeModel()]
    ensemble.bridge = FakeBridge()
    ensemble.integrity_gate = FakeIntegrity()

    best, reports = ensemble.propose(
        "EUR/USD",
        [{"close": 1.1} for _ in range(20)],
        snapshot=_snapshot(),
    )

    assert best is None
    assert reports[0]["status"] == "REJECTED_RECIPE_COMPILER"
    assert reports[0]["recipe_compiled"] is False
