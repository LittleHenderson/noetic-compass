"""Owner-controlled profitability thresholds for the paper-proof standard.

The 30-trading-day paper proof's pass criteria include real profitability gates:
net-positive realized P&L, max drawdown within a limit, and real trades on most
days. This module holds the owner's adjustable thresholds for those gates.

With no overrides set it returns sensible defaults derived from the proof plan's
own risk limits, so default/test behaviour is unchanged. The owner tunes these
from the app (no env vars, no restart). Overrides are process-global and reset
on restart - they only ever loosen/tighten what counts as a *passed* paper
proof; nothing here authorizes live money.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from typing import Any, Dict

# Defaults. Drawdown defaults to the proof plan's research gate (8%); seed
# capital defaults to the conservative low end of the plan's seed range so the
# drawdown percentage is measured against the smaller base.
_DEFAULT_REQUIRE_NET_POSITIVE = True
_DEFAULT_MIN_NET_PNL_USD = 0.0
_DEFAULT_MAX_DRAWDOWN_PCT = 8.0
_DEFAULT_MIN_TRADE_DAYS_FRACTION = 0.5  # "real trades on most days"
_DEFAULT_SEED_CAPITAL_USD = 2000.0

_FIELDS = (
    "require_net_positive",
    "min_net_pnl_usd",
    "max_drawdown_pct",
    "min_trade_days_fraction",
    "seed_capital_usd",
)

_OVERRIDES: Dict[str, Any] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class ProfitThresholds:
    """What counts as a profitable, passing paper proof."""

    require_net_positive: bool = _DEFAULT_REQUIRE_NET_POSITIVE
    min_net_pnl_usd: float = _DEFAULT_MIN_NET_PNL_USD
    max_drawdown_pct: float = _DEFAULT_MAX_DRAWDOWN_PCT
    min_trade_days_fraction: float = _DEFAULT_MIN_TRADE_DAYS_FRACTION
    seed_capital_usd: float = _DEFAULT_SEED_CAPITAL_USD

    def min_trade_days(self, required_trading_days: int) -> int:
        """How many proof days must have at least one real executed trade."""

        required = max(0, int(required_trading_days))
        days = math.ceil(required * float(self.min_trade_days_fraction))
        return max(0, min(days, required))


def _plan_defaults(plan: Any) -> Dict[str, Any]:
    """Derive default thresholds from a proof plan's own risk limits."""

    limits = getattr(plan, "risk_limits", {}) or {}
    out: Dict[str, Any] = {}
    dd = limits.get("max_drawdown_pct_research_gate")
    if dd is not None:
        try:
            out["max_drawdown_pct"] = float(dd)
        except (TypeError, ValueError):
            pass
    seed_range = limits.get("seed_capital_usd_range") or []
    if isinstance(seed_range, (list, tuple)) and seed_range:
        try:
            out["seed_capital_usd"] = float(min(seed_range))
        except (TypeError, ValueError):
            pass
    return out


def resolve_profit_thresholds(plan: Any = None) -> ProfitThresholds:
    """Resolve thresholds: defaults, overlaid by plan limits, overlaid by owner overrides."""

    values: Dict[str, Any] = {}
    if plan is not None:
        values.update(_plan_defaults(plan))
    with _lock:
        values.update({key: val for key, val in _OVERRIDES.items() if val is not None})
    base = ProfitThresholds()
    return ProfitThresholds(
        require_net_positive=bool(values.get("require_net_positive", base.require_net_positive)),
        min_net_pnl_usd=float(values.get("min_net_pnl_usd", base.min_net_pnl_usd)),
        max_drawdown_pct=float(values.get("max_drawdown_pct", base.max_drawdown_pct)),
        min_trade_days_fraction=float(
            values.get("min_trade_days_fraction", base.min_trade_days_fraction)
        ),
        seed_capital_usd=float(values.get("seed_capital_usd", base.seed_capital_usd)),
    )


def set_profit_threshold_overrides(**kwargs: Any) -> ProfitThresholds:
    """Set one or more owner threshold overrides. Unknown keys raise ValueError."""

    with _lock:
        for key, value in kwargs.items():
            if key not in _FIELDS:
                raise ValueError(f"Unknown profit threshold: {key}")
            if value is None:
                continue
            if key == "require_net_positive":
                _OVERRIDES[key] = bool(value)
            elif key == "min_trade_days_fraction":
                fraction = float(value)
                if not 0.0 <= fraction <= 1.0:
                    raise ValueError("min_trade_days_fraction must be between 0 and 1.")
                _OVERRIDES[key] = fraction
            elif key == "max_drawdown_pct":
                pct = float(value)
                if pct <= 0:
                    raise ValueError("max_drawdown_pct must be positive.")
                _OVERRIDES[key] = pct
            elif key == "seed_capital_usd":
                seed = float(value)
                if seed <= 0:
                    raise ValueError("seed_capital_usd must be positive.")
                _OVERRIDES[key] = seed
            else:  # min_net_pnl_usd
                _OVERRIDES[key] = float(value)
    return resolve_profit_thresholds()


def clear_profit_threshold_overrides() -> None:
    """Revert all owner threshold overrides to plan/defaults."""

    with _lock:
        _OVERRIDES.clear()


def build_profit_thresholds_report(plan: Any = None) -> Dict[str, Any]:
    """Owner-facing report of the current profitability thresholds."""

    thresholds = resolve_profit_thresholds(plan)
    with _lock:
        overridden = sorted(_OVERRIDES.keys())
    return {
        "report_kind": "cas_forex_proof_profit_thresholds",
        "require_net_positive": thresholds.require_net_positive,
        "min_net_pnl_usd": thresholds.min_net_pnl_usd,
        "max_drawdown_pct": thresholds.max_drawdown_pct,
        "min_trade_days_fraction": thresholds.min_trade_days_fraction,
        "seed_capital_usd": thresholds.seed_capital_usd,
        "overridden_fields": overridden,
        "note": (
            "A proof day counts toward profit only when it is broker-verified. "
            "'Passed' requires net-positive realized P&L, max drawdown within the "
            "limit, and real trades on most days. Adjust these from the app."
        ),
    }
