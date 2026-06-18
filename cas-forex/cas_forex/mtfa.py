"""Multi-Timeframe Analysis (MTFA) for CAS Forex.

Supports four trading styles with corresponding timeframes:
  SCALPING   M1, M5       seconds to minutes, requires split-second execution
  DAY        M15, M30, H1  minutes to hours, no overnight risk
  SWING      H4, D1        days to weeks, captures macro swings
  POSITION   W1, MN        weeks to months, fundamental-driven

MTFA workflow (professional standard):
  1. Trend timeframe (highest)  → "which way is the river flowing?"
  2. Signal timeframe (middle)  → "where is the pullback/setup?"
  3. Entry timeframe (lowest)   → "exactly when to pull the trigger?"
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from cas_forex.schemas.forecast import Direction


class TradingStyle(str, Enum):
    SCALPING = "SCALPING"
    DAY = "DAY"
    SWING = "SWING"
    POSITION = "POSITION"


class TFRole(str, Enum):
    TREND = "TREND"    # Highest TF — broad direction
    SIGNAL = "SIGNAL"  # Middle TF — setup/pullback
    ENTRY = "ENTRY"    # Lowest TF — exact trigger


# Timeframe hierarchy ordered short to long
TF_HIERARCHY = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN"]

# Each trading style uses 3 timeframes in MTFA
STYLE_TF_MAP: Dict[TradingStyle, Dict[TFRole, str]] = {
    TradingStyle.SCALPING: {
        TFRole.TREND: "M15",
        TFRole.SIGNAL: "M5",
        TFRole.ENTRY: "M1",
    },
    TradingStyle.DAY: {
        TFRole.TREND: "H4",
        TFRole.SIGNAL: "H1",
        TFRole.ENTRY: "M15",
    },
    TradingStyle.SWING: {
        TFRole.TREND: "D1",
        TFRole.SIGNAL: "H4",
        TFRole.ENTRY: "H1",
    },
    TradingStyle.POSITION: {
        TFRole.TREND: "W1",
        TFRole.SIGNAL: "D1",
        TFRole.ENTRY: "H4",
    },
}

# Risk parameters per style
STYLE_RISK: Dict[TradingStyle, dict] = {
    TradingStyle.SCALPING: {
        "max_position_lots": 0.05, "max_risk_per_trade_pct": 0.5,
        "min_rr_ratio": 1.5, "max_daily_dd_pct": 1.0,
        "hold_time_minutes": 5, "max_spread_pips": 2.0,
    },
    TradingStyle.DAY: {
        "max_position_lots": 0.1, "max_risk_per_trade_pct": 1.0,
        "min_rr_ratio": 2.0, "max_daily_dd_pct": 2.0,
        "hold_time_minutes": 240, "max_spread_pips": 3.0,
    },
    TradingStyle.SWING: {
        "max_position_lots": 0.2, "max_risk_per_trade_pct": 1.5,
        "min_rr_ratio": 2.0, "max_daily_dd_pct": 2.0,
        "hold_time_minutes": 2880, "max_spread_pips": 5.0,
    },
    TradingStyle.POSITION: {
        "max_position_lots": 0.5, "max_risk_per_trade_pct": 2.0,
        "min_rr_ratio": 3.0, "max_daily_dd_pct": 3.0,
        "hold_time_minutes": 10080, "max_spread_pips": 10.0,
    },
}


def tf_minutes(tf: str) -> int:
    """Convert timeframe string to minutes."""
    return {
        "M1": 1, "M5": 5, "M15": 15, "M30": 30,
        "H1": 60, "H4": 240, "D1": 1440, "W1": 10080, "MN": 43200,
    }.get(tf, 60)


def tf_higher(tf: str, steps: int = 1) -> str:
    """Return the timeframe N steps higher."""
    idx = TF_HIERARCHY.index(tf) if tf in TF_HIERARCHY else 4
    return TF_HIERARCHY[min(idx + steps, len(TF_HIERARCHY) - 1)]


def tf_lower(tf: str, steps: int = 1) -> str:
    """Return the timeframe N steps lower."""
    idx = TF_HIERARCHY.index(tf) if tf in TF_HIERARCHY else 4
    return TF_HIERARCHY[max(idx - steps, 0)]


@dataclass
class TFBar:
    """A single candle/bar on a specific timeframe."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    timeframe: str


@dataclass
class TFConsensus:
    """Result of multi-timeframe analysis for one symbol."""
    symbol: str
    style: TradingStyle
    trend_direction: Optional[Direction]  # from trend TF
    signal_direction: Optional[Direction]  # from signal TF
    entry_ready: bool  # signal TF confirms trend TF
    confidence: float  # 0-1, weighted by agreement
    trend_tf: str
    signal_tf: str
    entry_tf: str


class MultiTimeframeAnalyzer:
    """Analyzes a symbol across multiple timeframes to produce trade consensus.

    Implements the professional MTFA workflow:
      1. Check trend TF for broad direction
      2. Check signal TF for pullback/setup alignment
      3. Signal entry readiness when all three align
    """

    def __init__(self, style: TradingStyle = TradingStyle.SWING):
        self.style = style
        self.tfs = STYLE_TF_MAP[style]

    def analyze(
        self,
        symbol: str,
        candles: Dict[str, List[dict]],
    ) -> TFConsensus:
        """Run MTFA across all three timeframes.

        Args:
            symbol: Forex pair.
            candles: Dict mapping timeframe string → list of OHLCV dicts.
                    Must contain at least the 3 TFs for this style.
        """
        trend_tf = self.tfs[TFRole.TREND]
        signal_tf = self.tfs[TFRole.SIGNAL]
        entry_tf = self.tfs[TFRole.ENTRY]

        trend_dir = self._detect_direction(candles.get(trend_tf, []), trend_tf)
        signal_dir = self._detect_direction(candles.get(signal_tf, []), signal_tf)

        # Entry is "ready" when trend and signal align and we have enough data
        entry_ready = (
            trend_dir is not None
            and signal_dir is not None
            and trend_dir == signal_dir
            and len(candles.get(entry_tf, [])) >= 5
        )

        confidence = self._compute_confidence(candles, trend_dir, signal_dir)

        return TFConsensus(
            symbol=symbol,
            style=self.style,
            trend_direction=trend_dir,
            signal_direction=signal_dir,
            entry_ready=entry_ready,
            confidence=round(confidence, 4),
            trend_tf=trend_tf,
            signal_tf=signal_tf,
            entry_tf=entry_tf,
        )

    def _detect_direction(
        self, candles: List[dict], tf: str,
    ) -> Optional[Direction]:
        """Detect trend direction on a single timeframe."""
        if len(candles) < 10:
            return None

        closes = [c["close"] for c in candles]
        current = closes[-1]

        sma_fast = float(np.mean(closes[-min(5, len(closes)):]))
        sma_slow = float(np.mean(closes[-min(20, len(closes)):]))

        # Also check slope of recent prices
        if len(closes) >= 10:
            x = np.arange(min(10, len(closes)))
            y = np.array(closes[-10:])
            slope = np.polyfit(x, y, 1)[0]
        else:
            slope = 0

        # Trend score
        score = 0
        if sma_fast > sma_slow:
            score += 1
        if slope > 0:
            score += 1
        if len(closes) >= 5 and closes[-1] > closes[-5]:
            score += 1

        if score >= 2:
            return Direction.LONG
        elif score <= 0:
            return Direction.SHORT
        return None

    def _compute_confidence(
        self,
        candles: Dict[str, List[dict]],
        trend_dir: Optional[Direction],
        signal_dir: Optional[Direction],
    ) -> float:
        """Compute MTFA confidence score weighted by TF agreement."""
        trend_tf = self.tfs[TFRole.TREND]
        signal_tf = self.tfs[TFRole.SIGNAL]
        entry_tf = self.tfs[TFRole.ENTRY]

        base = 0.3

        # Trend TF weight: 50%
        if trend_dir is not None:
            trend_candles = candles.get(trend_tf, [])
            if len(trend_candles) >= 20:
                trend_strength = self._trend_strength(trend_candles)
                base += 0.5 * trend_strength

        # Signal TF weight: 30%
        if signal_dir is not None and signal_dir == trend_dir:
            signal_candles = candles.get(signal_tf, [])
            if len(signal_candles) >= 5:
                signal_strength = self._trend_strength(signal_candles)
                base += 0.3 * signal_strength

        # Entry TF weight: 20% — alignment of short-term
        entry_candles = candles.get(entry_tf, [])
        if len(entry_candles) >= 5:
            entry_dir = self._detect_direction(entry_candles, entry_tf)
            if entry_dir == trend_dir:
                base += 0.2

        return min(max(base, 0.1), 0.95)

    @staticmethod
    def _trend_strength(candles: List[dict]) -> float:
        """How strongly trending is this set of candles? 0=weak, 1=strong."""
        closes = [c["close"] for c in candles]
        if len(closes) < 5:
            return 0.1
        # Measure how many closes are above their predecessor
        up_count = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i - 1])
        return min(up_count / max(len(closes) - 1, 1), 1.0)


# ---- Factory ----


def mtfa_for_style(style: TradingStyle) -> MultiTimeframeAnalyzer:
    """Create an MTFA analyzer configured for a specific trading style."""
    return MultiTimeframeAnalyzer(style=style)


def default_mtfa() -> MultiTimeframeAnalyzer:
    return MultiTimeframeAnalyzer(style=TradingStyle.SWING)
