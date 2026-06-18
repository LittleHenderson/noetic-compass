"""Execution Gate – validates broker order before transmission."""
from datetime import datetime, timedelta
from typing import List, Optional
from cas_forex.schemas.decision import GateResult, GateStatus
from cas_forex.schemas.order import BrokerOrderRequest
from cas_forex.schemas.forecast import Direction as Dir, pip_multiplier
from cas_forex.time_utils import ensure_utc, utc_now


class ExecutionGate:
    def __init__(self, max_slippage_points: int = 30, duplicate_window_seconds: int = 30,
                 min_stop_distance_pips: float = 5.0):
        self.max_slippage_points = max_slippage_points
        self.duplicate_window_seconds = duplicate_window_seconds
        self.min_stop_distance_pips = min_stop_distance_pips
        self._recent: List[BrokerOrderRequest] = []

    def evaluate(self, order: BrokerOrderRequest, current_price: Optional[float] = None,
                 market_open: bool = True) -> GateResult:
        failures: list[str] = []
        evidence: dict = {"order_id": order.order_id, "symbol": order.symbol,
                          "volume": order.volume, "slippage_setting": order.slippage}

        # Duplicate detection
        if self._is_duplicate(order):
            failures.append("Duplicate order detected")
            evidence["duplicate_detected"] = True
        else:
            evidence["duplicate_detected"] = False

        if not market_open:
            failures.append("Market closed")

        if order.slippage > self.max_slippage_points:
            failures.append(f"Slippage {order.slippage} > max {self.max_slippage_points}")

        # Price deviation
        if current_price is not None and current_price > 0 and order.price > 0:
            pips = abs(order.price - current_price) * pip_multiplier(order.symbol)
            evidence["price_diff_pips"] = round(pips, 2)
            if pips > self.max_slippage_points * 2:
                failures.append(f"Price diff {pips:.1f} pips too large")

        # Stop distance + full geometry check. Market orders need a live quote.
        effective_price = order.price if order.price > 0 else current_price
        if effective_price is None or effective_price <= 0:
            failures.append("Current price required for market order validation")
            evidence["effective_price"] = None
            sl_dist = 0.0
        elif order.direction == Dir.LONG:
            evidence["effective_price"] = round(effective_price, 5)
            sl_dist = (
                (effective_price - order.stop_loss) * pip_multiplier(order.symbol)
                if effective_price > order.stop_loss else 0
            )
            if not (order.stop_loss < effective_price < order.take_profit):
                failures.append(
                    f"LONG geometry requires stop_loss < price < take_profit "
                    f"({order.stop_loss} < {effective_price} < {order.take_profit})"
                )
        else:
            evidence["effective_price"] = round(effective_price, 5)
            sl_dist = (
                (order.stop_loss - effective_price) * pip_multiplier(order.symbol)
                if order.stop_loss > effective_price else 0
            )
            if not (order.take_profit < effective_price < order.stop_loss):
                failures.append(
                    f"SHORT geometry requires take_profit < price < stop_loss "
                    f"({order.take_profit} < {effective_price} < {order.stop_loss})"
                )
        evidence["sl_distance_pips"] = round(sl_dist, 2)
        if sl_dist < self.min_stop_distance_pips:
            failures.append(f"SL distance {sl_dist:.1f}p < min {self.min_stop_distance_pips}")

        if not failures:
            self._recent.append(order)
            self._prune()
            return GateResult(gate_name="execution", status=GateStatus.PASS,
                              confidence=0.95, reason="Order validated.", evidence=evidence)

        return GateResult(gate_name="execution", status=GateStatus.FAIL,
                          confidence=0.95, reason="; ".join(failures),
                          evidence=evidence, claim_ceiling="OPEN")

    def _is_duplicate(self, order: BrokerOrderRequest) -> bool:
        cutoff = utc_now() - timedelta(seconds=self.duplicate_window_seconds)
        self._prune()
        for r in self._recent:
            if (r.symbol == order.symbol and r.direction == order.direction
                    and abs(r.volume - order.volume) < 0.001
                    and abs(r.stop_loss - order.stop_loss) < 0.0001
                    and abs(r.take_profit - order.take_profit) < 0.0001
                    and ensure_utc(r.created_at) >= cutoff):
                return True
        return False

    def _prune(self):
        cutoff = utc_now() - timedelta(seconds=self.duplicate_window_seconds)
        self._recent = [o for o in self._recent if ensure_utc(o.created_at) >= cutoff]
