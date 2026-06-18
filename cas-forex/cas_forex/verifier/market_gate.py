"""Market Gate – validates current market conditions for a trade proposal."""
from typing import Optional
from cas_forex.schemas.decision import GateResult, GateStatus
from cas_forex.schemas.forecast import Direction
from cas_forex.schemas.forecast import pip_multiplier as _pip_for
from cas_forex.schemas.market import MarketSnapshot


class MarketGate:
    def __init__(self, max_spread_pips: float = 5.0, max_atr_multiple: float = 3.0,
                 allow_asian: bool = True, min_volume: int = 0):
        self.max_spread_pips = max_spread_pips
        self.max_atr_multiple = max_atr_multiple
        self.allow_asian = allow_asian
        self.min_volume = min_volume

    def evaluate(self, snapshot: MarketSnapshot, direction: Direction,
                 entry_price: float, atr_14: Optional[float] = None) -> GateResult:
        failures: list[str] = []
        evidence: dict = {}

        if not snapshot.is_market_open:
            failures.append("Market is closed")
            evidence["market_open"] = False

        spread_pips = (snapshot.spread if snapshot.spread > 0
                       else (snapshot.ask - snapshot.bid) * _pip_for(snapshot.symbol))
        evidence["spread_pips"] = round(spread_pips, 2)
        if spread_pips > self.max_spread_pips:
            failures.append(f"Spread {spread_pips:.2f}p > max {self.max_spread_pips}")

        evidence["session"] = snapshot.session
        evidence["direction"] = direction.value

        mid = snapshot.mid
        price_deviation = abs(entry_price - mid) / mid * 100
        evidence["price_deviation_pct"] = round(price_deviation, 4)
        if price_deviation > 0.5:
            failures.append(f"Entry deviates {price_deviation:.2f}% from market mid")

        if atr_14 is not None and atr_14 > 0 and snapshot.high and snapshot.low:
            atr_pips = atr_14 * _pip_for(snapshot.symbol)
            evidence["atr_14_pips"] = round(atr_pips, 2)
            price_range = abs(snapshot.high - snapshot.low)
            if price_range > self.max_atr_multiple * atr_14:
                failures.append(
                    f"Range {price_range:.5f} > {self.max_atr_multiple}x ATR {atr_14:.5f}"
                )

        if not failures:
            return GateResult(gate_name="market", status=GateStatus.PASS,
                              confidence=0.95, reason="Market acceptable.", evidence=evidence)

        return GateResult(gate_name="market", status=GateStatus.FAIL,
                          confidence=0.95, reason="; ".join(failures),
                          evidence=evidence, claim_ceiling="OPEN")
