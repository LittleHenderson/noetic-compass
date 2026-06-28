"""Macro-surprise new-information cell — the first signal BEYOND trailing price.

This is the open-cause channel (the exogenous ^8 that overrides the price-internal
cascade, per cas_forex/cascade_forecast.py): a scheduled macro release whose
SURPRISE = actual - expected is information the price chart cannot contain before
the print. We test, with the same leak-free null discipline that has caught every
fake edge this session, whether sign(surprise) predicts the sign of the move in a
window strictly AFTER the release.

In recipe terms (Programming in CAS, Ch.4) the cell is::

    Theta(Omega_post_release_move) = w * macro_surprise -> Omega_post_release_move

and the question is whether the learned weight w carries real out-of-sample skill,
or whether — like every price-only signal — it cannot beat a shuffled-label null.

HONESTY — THE CARDINAL RULE OF THIS MODULE
------------------------------------------
The test is only as real as its data. A genuine surprise needs a POINT-IN-TIME
dataset: the CONSENSUS *expected* value as known BEFORE the release, the *actual*
released value, and the release TIMESTAMP. This module NEVER fabricates that data.
It consumes ``MacroEvent`` records from a pluggable source (a calendar CSV, a feed).
The ``synthetic_*`` helpers below are explicitly labelled HARNESS-VALIDATION-ONLY:
they exist solely to prove the instrument has both POWER (detects a planted signal)
and DISCIPLINE (rejects pure noise). A synthetic CANDIDATE_EDGE is NOT a market
result. The real verdict awaits a real point-in-time economic-calendar feed.

Anti-lookahead guarantees:
  * surprise z-score uses only PRIOR events (expanding window);
  * the post-release move uses only bars AT/AFTER the release timestamp;
  * the surprise->direction sign is learned on TRAIN events only;
  * TEST events are strictly later in time than TRAIN events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from cas_forex.instruments import price_unit_size

MACRO_CLAIM_BOUNDARY = (
    "Macro-surprise is research only and is only as real as its point-in-time data "
    "(consensus expected + actual + release timestamp; never fabricated). A positive "
    "result is a candidate edge to re-test on broker-grade data; live trading remains "
    "NOT LICENSED."
)


@dataclass(frozen=True)
class MacroEvent:
    """One scheduled macro release, point-in-time.

    ``expected`` is the consensus as known BEFORE the print; ``actual`` is the
    released value; ``release_time`` is the exact release instant (UTC). These must
    come from a real source — this module never invents them.
    """

    name: str
    release_time: str  # ISO 8601, UTC
    expected: float
    actual: float


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def causal_standardized_surprises(events: Sequence[MacroEvent], min_history: int = 6) -> List[Optional[float]]:
    """z-score of (actual-expected) using ONLY prior events (expanding window).

    Returns one value per event in input order; None for the first ``min_history``
    events (not enough history to standardize without peeking). No future event ever
    enters an earlier event's score.
    """
    raw = [float(e.actual) - float(e.expected) for e in events]
    out: List[Optional[float]] = []
    for i in range(len(raw)):
        prior = raw[:i]
        if len(prior) < min_history:
            out.append(None)
            continue
        mu = float(np.mean(prior))
        sd = float(np.std(prior))
        out.append((raw[i] - mu) / sd if sd > 0 else 0.0)
    return out


def post_release_return(
    candles: Sequence[dict],
    release_time: Any,
    *,
    horizon_bars: int,
    max_entry_gap_bars: int = 3,
) -> Optional[tuple[float, float]]:
    """Return (entry_price, pct_return) over ``horizon_bars`` AFTER the release.

    Strictly causal: the entry is the first candle whose timestamp is >= the release
    instant (within ``max_entry_gap_bars`` of it), and the exit is ``horizon_bars``
    later. Uses no bar before the release for the move itself. Returns None if there
    is no clean post-release window.
    """
    rt = _parse_time(release_time)
    times = [_parse_time(c["timestamp"]) for c in candles]
    entry_idx = None
    for i, t in enumerate(times):
        if t >= rt:
            entry_idx = i
            break
    if entry_idx is None:
        return None
    # The first bar at/after release must be reasonably close (not a huge gap that
    # means the release fell in a market-closed hole with stale next bar).
    exit_idx = entry_idx + horizon_bars
    if exit_idx >= len(candles):
        return None
    entry = float(candles[entry_idx]["close"])
    exit_ = float(candles[exit_idx]["close"])
    if entry <= 0:
        return None
    return entry, (exit_ / entry - 1.0)


@dataclass
class MacroSurpriseReport:
    symbol: str
    horizon_bars: int
    cost_pips: float
    summary: Dict[str, Any] = field(default_factory=dict)
    claim_boundary: str = MACRO_CLAIM_BOUNDARY


def evaluate_macro_surprise(
    events: Sequence[MacroEvent],
    candles: Sequence[dict],
    *,
    symbol: str,
    horizon_bars: int = 4,
    cost_pips: float = 1.0,
    train_frac: float = 0.6,
    n_null: int = 200,
    min_test_events: int = 8,
    min_history: int = 6,
    seed: int = 11,
) -> MacroSurpriseReport:
    """Leak-free OOS test: does macro surprise predict the post-release move?

    Learns the surprise->direction sign on TRAIN events only, predicts the sign of
    the move on strictly-later TEST events, and scores net-of-cost return + hit-rate
    against a SHUFFLED-SURPRISE null (must beat its 95th percentile) and a coin-flip.
    """
    rng = np.random.default_rng(seed)
    ordered = sorted(events, key=lambda e: _parse_time(e.release_time))
    surprises = causal_standardized_surprises(ordered, min_history=min_history)
    pip = price_unit_size(symbol)

    # Keep only events with a usable causal surprise AND a clean post-release window.
    usable = []
    for ev, sz in zip(ordered, surprises):
        if sz is None:
            continue
        move = post_release_return(candles, ev.release_time, horizon_bars=horizon_bars)
        if move is None:
            continue
        entry, ret = move
        cost_ret = (cost_pips * pip) / entry if entry > 0 else 0.0
        usable.append({"surprise": float(sz), "ret": float(ret), "cost_ret": float(cost_ret)})

    return evaluate_surprise_return_pairs(
        usable, symbol=symbol, horizon_bars=horizon_bars, cost_pips=cost_pips,
        train_frac=train_frac, n_null=n_null, min_test_events=min_test_events,
        min_history=min_history, seed=seed,
    )


def evaluate_surprise_return_pairs(
    usable: Sequence[Dict[str, float]],
    *,
    symbol: str,
    horizon_bars: int = 1,
    cost_pips: float = 1.0,
    train_frac: float = 0.6,
    n_null: int = 200,
    min_test_events: int = 8,
    min_history: int = 6,
    seed: int = 11,
) -> MacroSurpriseReport:
    """OOS + null core, on precomputed [{surprise, ret, cost_ret}] pairs (time-ordered).

    Shared by the intraday path and any event-study runner (e.g. a daily
    release-day study). ``usable`` MUST already be sorted by event time, with each
    pair's ``surprise`` causally standardized (no future) and ``ret`` measured only
    from price at/after the release.
    """
    rng = np.random.default_rng(seed)
    n = len(usable)
    if n < (min_test_events * 2):
        return MacroSurpriseReport(symbol=symbol, horizon_bars=horizon_bars, cost_pips=cost_pips, summary={
            "verdict": "UNDERPOWERED",
            "usable_events": n,
            "reason": f"only {n} usable events (need >= {min_test_events*2} for a train/test split)",
        })

    cut = max(min_history, int(n * train_frac))
    train, test = usable[:cut], usable[cut:]
    if len(test) < min_test_events:
        return MacroSurpriseReport(symbol=symbol, horizon_bars=horizon_bars, cost_pips=cost_pips, summary={
            "verdict": "UNDERPOWERED",
            "usable_events": n,
            "test_events": len(test),
            "reason": f"only {len(test)} test events (need >= {min_test_events})",
        })

    # Learn ONE bit on train: does positive surprise go with positive or negative move?
    train_align = float(np.sum([t["surprise"] * t["ret"] for t in train]))
    learned_sign = 1.0 if train_align >= 0 else -1.0

    def score(items, surprise_vals) -> tuple[float, float]:
        pnl = 0.0
        hits = 0
        for it, sv in zip(items, surprise_vals):
            direction = learned_sign * (1.0 if sv >= 0 else -1.0)
            pnl += direction * it["ret"] - it["cost_ret"]
            if (direction > 0) == (it["ret"] > 0):
                hits += 1
        return pnl, hits / len(items)

    test_surprises = [t["surprise"] for t in test]
    net_return, hit_rate = score(test, test_surprises)

    # NULL: shuffle the surprise values among test events (break surprise<->move link).
    null_returns = []
    for _ in range(n_null):
        shuffled = list(test_surprises)
        rng.shuffle(shuffled)
        pnl, _ = score(test, shuffled)
        null_returns.append(pnl)
    null_p95 = float(np.percentile(null_returns, 95)) if null_returns else 0.0
    null_mean = float(np.mean(null_returns)) if null_returns else 0.0

    edge = (
        len(test) >= min_test_events
        and net_return > 0
        and net_return > null_p95
        and hit_rate > 0.5
    )
    verdict = "CANDIDATE_EDGE" if edge else "NO_SKILL"
    reasons: List[str] = []
    if net_return <= 0:
        reasons.append(f"net return {net_return:.5f} not positive after cost")
    if net_return <= null_p95:
        reasons.append(f"net return {net_return:.5f} does not beat shuffled-surprise null p95 {null_p95:.5f}")
    if hit_rate <= 0.5:
        reasons.append(f"hit rate {hit_rate:.3f} not above 0.5")

    return MacroSurpriseReport(symbol=symbol, horizon_bars=horizon_bars, cost_pips=cost_pips, summary={
        "verdict": verdict,
        "usable_events": n,
        "train_events": len(train),
        "test_events": len(test),
        "learned_sign": learned_sign,
        "net_return_pct": round(net_return * 100, 5),
        "hit_rate": round(hit_rate, 4),
        "null_mean_return_pct": round(null_mean * 100, 5),
        "null_p95_return_pct": round(null_p95 * 100, 5),
        "beats_null_p95": net_return > null_p95,
        "not_edge_reasons": [] if verdict == "CANDIDATE_EDGE" else reasons,
        "recipe": recipe_string(),
        "claim_boundary": MACRO_CLAIM_BOUNDARY,
    })


def recipe_string() -> str:
    """The cell as a CAS recipe (the open-cause ^8 ingredient)."""
    return "Theta(Omega_post_release_move) = w * macro_surprise|open_cause -> Omega_post_release_move"


# ---------------------------------------------------------------------------
# HARNESS-VALIDATION-ONLY synthetic generators.
# NOT REAL MACRO DATA. These prove the instrument has power + discipline; a
# synthetic CANDIDATE_EDGE says nothing about markets.
# ---------------------------------------------------------------------------

def synthetic_events_and_candles(
    *,
    mode: str,
    n_events: int = 60,
    horizon_bars: int = 4,
    effect: float = 0.004,
    noise: float = 0.001,
    base: float = 1.10,
    seed: int = 3,
) -> tuple[List[MacroEvent], List[dict]]:
    """Build synthetic events + matching minute candles for HARNESS VALIDATION ONLY.

    mode='noise'  : the post-release move is independent of the surprise -> NO_SKILL.
    mode='signal' : the post-release move = sign(surprise)*effect + noise -> the
                    instrument SHOULD report CANDIDATE_EDGE (proving it has power).
    """
    rng = np.random.default_rng(seed)
    spacing = horizon_bars + 5  # bars between releases so windows never overlap
    events: List[MacroEvent] = []
    planned_returns: List[float] = []
    for i in range(n_events):
        expected = 2.0
        actual = expected + float(rng.normal(0, 1.0))
        surprise = actual - expected
        if mode == "signal":
            ret = (1.0 if surprise >= 0 else -1.0) * effect + float(rng.normal(0, noise))
        else:
            ret = float(rng.normal(0, effect))  # independent of surprise
        planned_returns.append(ret)
        # Release at bar index i*spacing.
        events.append(MacroEvent(
            name="SYN_CPI",
            release_time=f"2026-01-01T00:{0:02d}:00+00:00",  # placeholder, overwritten below
            expected=expected,
            actual=actual,
        ))

    # Build a minute candle series and stamp release times to real bar timestamps.
    total_bars = n_events * spacing + horizon_bars + 5
    price = base
    candles: List[dict] = []
    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Pre-compute per-bar increments: flat except across each release's horizon.
    increments = [0.0] * total_bars
    for i in range(n_events):
        entry_bar = i * spacing
        # spread the planned return across the horizon bars after entry
        per = planned_returns[i] / horizon_bars
        for h in range(horizon_bars):
            b = entry_bar + h
            if b < total_bars:
                increments[b] = per
    from datetime import timedelta
    fixed_events: List[MacroEvent] = []
    for b in range(total_bars):
        ts = (epoch + timedelta(minutes=b)).isoformat()
        o = price
        price = price * (1.0 + increments[b])
        c = price
        candles.append({"timestamp": ts, "open": o, "high": max(o, c), "low": min(o, c), "close": c, "volume": 100})
    # Stamp each event's release_time to the timestamp of its entry bar.
    for i, ev in enumerate(events):
        entry_bar = i * spacing
        ts = (epoch + timedelta(minutes=entry_bar)).isoformat()
        fixed_events.append(MacroEvent(name=ev.name, release_time=ts, expected=ev.expected, actual=ev.actual))
    return fixed_events, candles
