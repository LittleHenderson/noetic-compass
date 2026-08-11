"""Directional hypothesis engine for WASTE.

This is not a trade authorization layer. It gives the AI a disciplined way to
say LONG, SHORT, or NO_TRADE from current candles and owner permissions. The
edge gate still decides whether a hypothesis may execute.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Optional

from cas_forex.ai_control_authority import AiControlAuthority, get_authority
from cas_forex.instruments import price_unit_size, round_price
from cas_forex.waste_loop import CandidateSetup

DIRECTIONAL_PROFILES = (
    "blend",
    "trend_follow",
    "range_fade",
    "breakout_continuation",
)


@dataclass(frozen=True)
class Candle:
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class DirectionalHypothesis:
    symbol: str
    timeframe: str
    action: str  # LONG | SHORT | NO_TRADE
    long_score: float
    short_score: float
    confidence: float
    regime: str
    reasons: tuple[str, ...]
    profile: str = "blend"

    @property
    def direction(self) -> Optional[str]:
        return self.action if self.action in {"LONG", "SHORT"} else None

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["direction"] = self.direction
        return out


def normalize_candles(raw: Iterable[Any]) -> list[Candle]:
    candles: list[Candle] = []
    for item in raw:
        if isinstance(item, Candle):
            candles.append(item)
            continue
        if isinstance(item, Mapping):
            candles.append(
                Candle(
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                )
            )
            continue
        o, h, l, c = item
        candles.append(Candle(open=float(o), high=float(h), low=float(l), close=float(c)))
    return candles


def score_direction(
    candles: Iterable[Any],
    *,
    symbol: str,
    timeframe: str = "M15",
    authority: Optional[AiControlAuthority] = None,
    min_confidence: float = 0.18,
    profile: str = "blend",
) -> DirectionalHypothesis:
    """Score current candles as LONG, SHORT, or NO_TRADE.

    The score intentionally produces a hypothesis, not an edge claim. It blends
    recent drift, broader drift, range extension, and volatility compression into
    long/short pressure. WASTE must still run the null edge test before execution.
    """
    authority = authority or get_authority()
    profile = _normalize_profile(profile)
    owner = authority.owner_envelope
    if symbol not in owner.allowed_symbols:
        return _no_trade(symbol, timeframe, f"{symbol} outside owner allowed_symbols", profile=profile)

    data = normalize_candles(candles)
    if len(data) < 30:
        return _no_trade(
            symbol,
            timeframe,
            "insufficient candles for directional read",
            profile=profile,
        )
    closes = [c.close for c in data]
    highs = [c.high for c in data]
    lows = [c.low for c in data]
    last = closes[-1]
    if last <= 0:
        return _no_trade(symbol, timeframe, "invalid last close", profile=profile)

    recent = _pct_change(closes[-6], last)
    broader = _pct_change(closes[-25], last)
    mean20 = sum(closes[-20:]) / 20.0
    std20 = _std(closes[-20:])
    z = (last - mean20) / std20 if std20 > 0 else 0.0
    atr14 = _atr(highs, lows, closes, 14)
    atr60 = _atr(highs, lows, closes, 60)
    vol_ratio = atr14 / atr60 if atr60 > 0 else 1.0

    trend_push = _squash((broader * 60.0) + (recent * 90.0))
    range_fade = _squash(-z / 2.0)
    compression_bonus = max(0.0, min(0.18, (1.0 - vol_ratio) * 0.18))

    long_score, short_score, profile_reason = _profile_scores(
        profile=profile,
        closes=closes,
        highs=highs,
        lows=lows,
        trend_push=trend_push,
        range_fade=range_fade,
        compression_bonus=compression_bonus,
        recent=recent,
        broader=broader,
        atr14=atr14,
    )
    long_score += compression_bonus if long_score > short_score else 0.0
    short_score += compression_bonus if short_score > long_score else 0.0
    long_score = round(float(long_score), 4)
    short_score = round(float(short_score), 4)

    action = "LONG" if long_score >= short_score else "SHORT"
    confidence = max(long_score, short_score)
    reasons = [
        f"profile={profile}",
        f"recent_change={recent:.5f}",
        f"broader_change={broader:.5f}",
        f"z20={z:.3f}",
        f"vol_ratio={vol_ratio:.3f}",
        profile_reason,
    ]
    if action == "LONG" and not owner.allow_long:
        return _no_trade(
            symbol,
            timeframe,
            "LONG pressure present but owner disabled LONG",
            long_score=long_score,
            short_score=short_score,
            regime=_regime(vol_ratio, z),
            reasons=reasons,
            profile=profile,
        )
    if action == "SHORT" and not owner.allow_short:
        return _no_trade(
            symbol,
            timeframe,
            "SHORT pressure present but owner disabled SHORT",
            long_score=long_score,
            short_score=short_score,
            regime=_regime(vol_ratio, z),
            reasons=reasons,
            profile=profile,
        )
    if confidence < min_confidence:
        return _no_trade(
            symbol,
            timeframe,
            f"directional confidence {confidence:.3f} below {min_confidence:.3f}",
            long_score=long_score,
            short_score=short_score,
            regime=_regime(vol_ratio, z),
            reasons=reasons,
            profile=profile,
        )
    return DirectionalHypothesis(
        symbol=symbol,
        timeframe=timeframe,
        action=action,
        long_score=long_score,
        short_score=short_score,
        confidence=round(float(confidence), 4),
        regime=_regime(vol_ratio, z),
        reasons=tuple(reasons),
        profile=profile,
    )


def candidate_from_hypothesis(
    hypothesis: DirectionalHypothesis,
    candles: Iterable[Any],
    *,
    entry_pairs: Optional[list[dict[str, float]]] = None,
) -> Optional[CandidateSetup]:
    """Turn a directional hypothesis into a WASTE candidate, or None."""
    if hypothesis.direction is None:
        return None
    data = normalize_candles(candles)
    if len(data) < 15:
        return None
    closes = [c.close for c in data]
    highs = [c.high for c in data]
    lows = [c.low for c in data]
    entry = closes[-1]
    atr = max(_atr(highs, lows, closes, 14), price_unit_size(hypothesis.symbol) * 5.0)
    if hypothesis.direction == "LONG":
        stop_loss = entry - 1.5 * atr
        take_profit = entry + 2.0 * atr
    else:
        stop_loss = entry + 1.5 * atr
        take_profit = entry - 2.0 * atr
    ref_src = (
        f"{hypothesis.symbol}|{hypothesis.timeframe}|{hypothesis.profile}|{hypothesis.direction}|"
        f"{len(data)}|{entry:.8f}|{hypothesis.confidence:.4f}"
    )
    signed_strength = (
        float(hypothesis.confidence)
        if hypothesis.direction == "LONG"
        else -float(hypothesis.confidence)
    )
    setup = CandidateSetup(
        symbol=hypothesis.symbol,
        timeframe=hypothesis.timeframe,
        direction=hypothesis.direction,
        entry=round_price(hypothesis.symbol, entry),
        stop_loss=round_price(hypothesis.symbol, stop_loss),
        take_profit=round_price(hypothesis.symbol, take_profit),
        signal_strength=signed_strength,
        regime=hypothesis.regime,
        decision_ref="waste-dir-" + hashlib.sha256(ref_src.encode("utf-8")).hexdigest()[:16],
    )
    setattr(setup, "entry_pairs", list(entry_pairs or []))
    setattr(setup, "directional_hypothesis", hypothesis.to_dict())
    return setup


def analyze_market_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Default WASTE analysis for states that carry candles."""
    candles = state.get("candles") or []
    symbol = str(state.get("symbol") or "")
    timeframe = str(state.get("timeframe") or "M15")
    try:
        min_confidence = float(get_authority().control.get("min_directional_confidence"))
    except Exception:
        min_confidence = 0.18
    firewall = _strategy_firewall_for_state(state, symbol, timeframe)
    if firewall and not bool(firewall.get("candidate_allowed", False)):
        hypothesis = _no_trade(
            symbol,
            timeframe,
            "strategy-ledger firewall blocked WASTE candidate formation",
            reasons=list(firewall.get("reasons") or [firewall.get("reason") or firewall.get("firewall_status")]),
        )
        return {
            "confidence": 0.0,
            "hypothesis": hypothesis.to_dict(),
            "reason": "; ".join(hypothesis.reasons),
            "strategy_firewall": firewall,
            "directional_floor": min_confidence,
            "directional_score": max(hypothesis.long_score, hypothesis.short_score),
            "candidate_formation_status": "BLOCKED_BY_STRATEGY_FIREWALL",
        }
    if not symbol or not candles:
        return {
            "confidence": 0.0,
            "hypothesis": None,
            "reason": "no candles in state",
            "directional_floor": min_confidence,
            "directional_score": 0.0,
            "candidate_formation_status": "NO_CANDLES",
        }
    profile = _profile_from_state(state)
    cas_block = _cas_route_block_reason(state)
    if cas_block:
        hypothesis = _no_trade(
            symbol,
            timeframe,
            cas_block,
            profile=profile,
        )
        return {
            "confidence": 0.0,
            "hypothesis": hypothesis.to_dict(),
            "reason": "; ".join(hypothesis.reasons),
            "strategy_firewall": firewall,
            "hypothesis_tuning": state.get("directional_hypothesis_tuning"),
            "cas_feature_map": state.get("cas_feature_map"),
            "directional_floor": min_confidence,
            "directional_score": max(hypothesis.long_score, hypothesis.short_score),
            "candidate_formation_status": "BLOCKED_BY_CAS_ROUTE_MAP",
        }
    hypothesis = score_direction(
        candles,
        symbol=symbol,
        timeframe=timeframe,
        profile=profile,
        min_confidence=min_confidence,
    )
    return {
        "confidence": hypothesis.confidence,
        "hypothesis": hypothesis.to_dict(),
        "reason": "; ".join(hypothesis.reasons),
        "directional_floor": min_confidence,
        "directional_score": max(hypothesis.long_score, hypothesis.short_score),
        "candidate_formation_status": (
            "CANDIDATE_FORMED"
            if hypothesis.direction is not None
            else (
                "BELOW_DIRECTIONAL_FLOOR"
                if "directional confidence" in str(hypothesis.reasons[0] if hypothesis.reasons else "")
                else "NO_DIRECTIONAL_CANDIDATE"
            )
        ),
        "strategy_firewall": firewall,
        "hypothesis_tuning": state.get("directional_hypothesis_tuning"),
        "cas_feature_map": state.get("cas_feature_map"),
    }


def strategize_market_state(
    state: Mapping[str, Any], analysis: Mapping[str, Any]
) -> Optional[CandidateSetup]:
    """Default WASTE strategizer for candle-backed state."""
    if _cas_route_block_reason(state):
        return None
    raw_h = analysis.get("hypothesis")
    if not isinstance(raw_h, Mapping):
        return None
    hypothesis = DirectionalHypothesis(
        symbol=str(raw_h.get("symbol") or state.get("symbol")),
        timeframe=str(raw_h.get("timeframe") or state.get("timeframe") or "M15"),
        action=str(raw_h.get("action") or "NO_TRADE"),
        long_score=float(raw_h.get("long_score") or 0.0),
        short_score=float(raw_h.get("short_score") or 0.0),
        confidence=float(raw_h.get("confidence") or 0.0),
        regime=str(raw_h.get("regime") or "unknown"),
        reasons=tuple(str(r) for r in raw_h.get("reasons", []) or []),
        profile=_normalize_profile(str(raw_h.get("profile") or _profile_from_state(state))),
    )
    firewall = _strategy_firewall_for_state(state, hypothesis.symbol, hypothesis.timeframe)
    if firewall and not bool(firewall.get("candidate_allowed", False)):
        return None
    setup = candidate_from_hypothesis(
        hypothesis,
        state.get("candles") or [],
        entry_pairs=list(state.get("entry_pairs") or []),
    )
    if setup is None:
        return None
    setattr(
        setup,
        "market_state_meta",
        {
            "report_kind": state.get("report_kind"),
            "source": state.get("source"),
            "feed_label": state.get("feed_label"),
            "live_feed": bool(state.get("live_feed", False)),
            "broker_grade_market_truth": bool(state.get("broker_grade_market_truth", False)),
            "quote": state.get("quote"),
            "entry_pair_report": _entry_pair_report_summary(state.get("entry_pair_report")),
            "strategy_firewall": firewall,
            "selected_directional_profile": state.get("selected_directional_profile"),
            "directional_hypothesis_tuning": state.get("directional_hypothesis_tuning"),
            "cas_feature_map": state.get("cas_feature_map"),
        },
    )
    setattr(setup, "strategy_firewall", firewall)
    return setup


def _paper_learning_active() -> bool:
    """Owner paper-learning mode (2026-07-01): True only when the owner dial is
    ON and live trading is NOT actually authorized. Errors read False."""
    try:
        authority = get_authority()
        if not bool(authority.control.get("paper_learning_trades")):
            return False
        from cas_forex import runtime_gates
        from cas_forex.config import config

        if getattr(config, "live_mode", False) and runtime_gates.is_authorized("live_trading"):
            return False
        return True
    except Exception:
        return False


def _cas_route_block_reason(state: Mapping[str, Any]) -> str | None:
    cas_map = state.get("cas_feature_map")
    if not isinstance(cas_map, Mapping):
        return None
    rpm_action = str(cas_map.get("selected_rpm_action") or "").upper()
    block: str | None = None
    if rpm_action and rpm_action != "ROUTE":
        block = "CAS lacunarity/RPM/CJT selected NO_TRADE for this profile"
    elif _bool_value(cas_map.get("selected_is_lacuna"), default=False):
        block = "CAS lacunarity/RPM/CJT selected cell is a lacuna"
    if block is None:
        return None
    # Owner paper-learning mode: a lacuna (unmeasured cell) is exactly where the
    # loop must gather outcomes — the CAS map rides along as a feature/label but
    # does not veto paper LEARNING candidates. Real-money authorization is
    # unaffected (the mode reads False whenever live trading is authorized).
    if _paper_learning_active():
        return None
    return block


def _no_trade(
    symbol: str,
    timeframe: str,
    reason: str,
    *,
    long_score: float = 0.0,
    short_score: float = 0.0,
    regime: str = "unknown",
    reasons: Optional[list[str]] = None,
    profile: str = "blend",
) -> DirectionalHypothesis:
    return DirectionalHypothesis(
        symbol=symbol,
        timeframe=timeframe,
        action="NO_TRADE",
        long_score=round(float(long_score), 4),
        short_score=round(float(short_score), 4),
        confidence=0.0,
        regime=regime,
        reasons=tuple([reason] + list(reasons or [])),
        profile=_normalize_profile(profile),
    )


def _bool_value(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _normalize_profile(profile: str) -> str:
    value = str(profile or "blend").strip().lower()
    return value if value in DIRECTIONAL_PROFILES else "blend"


def _profile_scores(
    *,
    profile: str,
    closes: list[float],
    highs: list[float],
    lows: list[float],
    trend_push: float,
    range_fade: float,
    compression_bonus: float,
    recent: float,
    broader: float,
    atr14: float,
) -> tuple[float, float, str]:
    recent_push = _squash(recent * 120.0)
    previous_high = max(highs[-21:-1]) if len(highs) >= 21 else max(highs[:-1])
    previous_low = min(lows[-21:-1]) if len(lows) >= 21 else min(lows[:-1])
    last = closes[-1]
    breakout_up = _squash((last - previous_high) / atr14) if atr14 > 0 else 0.0
    breakout_down = _squash((previous_low - last) / atr14) if atr14 > 0 else 0.0

    if profile == "trend_follow":
        long_score = 0.78 * max(trend_push, 0.0) + 0.12 * max(recent_push, 0.0)
        short_score = 0.78 * max(-trend_push, 0.0) + 0.12 * max(-recent_push, 0.0)
        reason = f"lens=trend_follow trend_push={trend_push:.3f}"
    elif profile == "range_fade":
        long_score = 0.76 * max(range_fade, 0.0) + 0.10 * max(-trend_push, 0.0)
        short_score = 0.76 * max(-range_fade, 0.0) + 0.10 * max(trend_push, 0.0)
        long_score += 0.06 * compression_bonus if range_fade > 0 else 0.0
        short_score += 0.06 * compression_bonus if range_fade < 0 else 0.0
        reason = f"lens=range_fade range_fade={range_fade:.3f}"
    elif profile == "breakout_continuation":
        long_score = 0.80 * max(breakout_up, 0.0) + 0.10 * max(trend_push, 0.0)
        short_score = 0.80 * max(breakout_down, 0.0) + 0.10 * max(-trend_push, 0.0)
        reason = (
            "lens=breakout_continuation "
            f"breakout_up={breakout_up:.3f} breakout_down={breakout_down:.3f}"
        )
    else:
        long_score = 0.55 * max(trend_push, 0.0) + 0.35 * max(range_fade, 0.0)
        short_score = 0.55 * max(-trend_push, 0.0) + 0.35 * max(-range_fade, 0.0)
        reason = f"lens=blend trend_push={trend_push:.3f} range_fade={range_fade:.3f}"

    return float(long_score), float(short_score), reason


def _pct_change(old: float, new: float) -> float:
    return (new / old - 1.0) if old else 0.0


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return var ** 0.5


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> float:
    if len(closes) < 2:
        return 0.0
    start = max(1, len(closes) - period)
    trs = []
    for i in range(start, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    return sum(trs) / len(trs) if trs else 0.0


def _squash(value: float) -> float:
    if value > 1.0:
        return 1.0
    if value < -1.0:
        return -1.0
    return float(value)


def _regime(vol_ratio: float, z: float) -> str:
    if vol_ratio < 0.75 and abs(z) >= 1.0:
        return "compressed_range_extension"
    if vol_ratio > 1.35:
        return "high_volatility"
    if abs(z) < 0.5:
        return "balanced"
    return "directional_pressure"


def _strategy_firewall_for_state(
    state: Mapping[str, Any],
    symbol: str,
    timeframe: str,
) -> Optional[dict[str, Any]]:
    raw = state.get("strategy_firewall")
    if isinstance(raw, Mapping):
        return dict(raw)
    if not symbol:
        return None
    try:
        from cas_forex.waste_strategy_firewall import evaluate_waste_strategy_firewall

        return evaluate_waste_strategy_firewall(symbol, timeframe).to_dict()
    except Exception as exc:
        return {
            "report_kind": "cas_forex_waste_strategy_firewall",
            "symbol": symbol,
            "timeframe": str(timeframe or "").upper(),
            "candidate_allowed": False,
            "firewall_status": "NO_TRADE_LEDGER_UNAVAILABLE",
            "reason": f"strategy ledger unavailable: {type(exc).__name__}: {exc}",
            "reasons": [f"strategy ledger unavailable: {type(exc).__name__}: {exc}"],
        }


def _entry_pair_report_summary(report: Any) -> Any:
    if not isinstance(report, Mapping):
        return report
    return {
        "evaluated_windows": report.get("evaluated_windows"),
        "skipped_no_trade": report.get("skipped_no_trade"),
        "horizon_bars": report.get("horizon_bars"),
        "cost_pips": report.get("cost_pips"),
        "entry_pair_count": len(report.get("entry_pairs") or []),
        "selected_profile": report.get("selected_profile"),
        "selection_status": (report.get("hypothesis_tuning") or {}).get("status")
        if isinstance(report.get("hypothesis_tuning"), Mapping)
        else None,
    }


def _profile_from_state(state: Mapping[str, Any]) -> str:
    profile = state.get("selected_directional_profile")
    if not profile and isinstance(state.get("entry_pair_report"), Mapping):
        profile = state["entry_pair_report"].get("selected_profile")
    return _normalize_profile(str(profile or "blend"))
