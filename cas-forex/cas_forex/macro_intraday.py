"""Intraday macro-surprise test — the post-release reaction at the scale it lives.

The daily macro-surprise test (``scripts/run_macro_surprise_real.py``) found a faint
sub-significance tilt with the correct learned sign, but a *daily* release-day return
dilutes the real macro reaction — which happens in the seconds-to-minutes after the
print — under ~23 hours of unrelated noise. This module resolves that test at the
scale the reaction actually occurs: the EUR/USD move in the **5–30 minutes after each
scheduled US release**, measured on 1-minute (M1) bars, run through the SAME leak-free
shuffled-surprise null core (``macro_surprise.evaluate_surprise_return_pairs``) that
has caught every fake edge this session.

THE TWO HONESTY RULES OF THIS MODULE
------------------------------------
1. NEVER fabricate market or macro data. The M1 bars come from a real broker-grade
   archive supplied by the operator (HistData ASCII M1); the surprises come from a
   real point-in-time economic calendar (Forex Factory: consensus Forecast + Actual +
   release date). The ``synthetic_*`` generators are HARNESS-VALIDATION-ONLY and are
   labelled as such — they prove the *pipeline* (loader + schedule + window + null) has
   power and discipline and aligns timezones correctly; a synthetic CANDIDATE_EDGE says
   nothing about markets.
2. The decision rule is fixed IN ADVANCE (see ``PRIMARY_SPEC``): a verdict of
   CANDIDATE_EDGE requires BOTH (a) beating the shuffled-surprise null's 95th percentile
   out-of-sample, AND (b) a positive net return after cost. The label-permutation null
   holds trading frequency (hence total cost) fixed, so gate (a) isolates *directional*
   skill while gate (b) is the cost gate — which is why PRIMARY carries a news-realistic
   cost (news spreads blow out; an optimistic cost would only weaken gate (b)). The
   pooled verdict is a MIXTURE dominated by the highest-volatility prints (NFP/CPI); the
   report carries a per-indicator decomposition so a reader can see whether any edge is
   broad or a single-indicator artifact. Secondary windows are exploratory robustness and
   never become the headline. We do not tune to pass.

THE TIMEZONE TRAP (the load-bearing correctness point)
------------------------------------------------------
HistData ASCII M1 timestamps are **Eastern Standard Time with NO daylight saving**
(a fixed UTC−5 year-round). US economic releases follow Eastern **clock** time **with**
daylight saving — so an 08:30 ET print is 12:30 UTC in summer (EDT) but 13:30 UTC in
winter (EST). If you naively aligned wall-clocks you would measure the wrong minute by
a full hour for ~8 months of the year. This module defeats the trap *structurally*:
both the bars and the release schedule are converted to true UTC before anything is
aligned. The bar loader adds a FIXED +5h (EST, no DST); the release schedule adds the
DST-correct +4h/+5h. They can only meet in UTC.

Anti-lookahead guarantees (inherited from the macro-surprise core, enforced here):
  * the surprise z-score for each release uses ONLY prior releases of that indicator;
  * the post-release move uses ONLY bars at/after the release instant;
  * the surprise->direction sign is learned on TRAIN releases only;
  * TEST releases are strictly later in time than TRAIN releases.
"""

from __future__ import annotations

import bisect
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from cas_forex.instruments import price_unit_size
from cas_forex.macro_surprise import (
    MACRO_CLAIM_BOUNDARY,
    _parse_time,
    evaluate_surprise_return_pairs,
)

INTRADAY_CLAIM_BOUNDARY = (
    "Intraday macro-surprise is research only. It is as real as its point-in-time data "
    "(consensus + actual + release date) and its broker-grade M1 bars; data is never "
    "fabricated. The verdict is the PRIMARY window only and is a POOLED mixture (NFP/CPI "
    "dominate by volatility — see the per-indicator decomposition). A positive result is "
    "a candidate edge to re-test on live broker spreads (news spreads blow out); live "
    "trading remains owner-gated."
)

# HistData generic ASCII M1 archives are stamped in EST (UTC-5) with NO DST.
HISTDATA_FIXED_OFFSET_HOURS = 5


# ---------------------------------------------------------------------------
# US Eastern DST + canonical release schedule.
#
# Self-contained (no runtime tz dependency) and valid for the post-2007 US DST
# rule (2nd Sunday of March .. 1st Sunday of November), which covers the entire
# span of the economic calendar (2007+). A unit test proves this rule equals the
# IANA tz database (America/New_York) across a multi-year range, so the schedule
# is authoritative without importing zoneinfo at runtime.
# ---------------------------------------------------------------------------

def _nth_sunday(year: int, month: int, n: int) -> date:
    """The date of the n-th Sunday (n>=1) of ``month`` in ``year``."""
    first = date(year, month, 1)
    # weekday(): Mon=0..Sun=6; offset to the first Sunday.
    first_sunday = 1 + ((6 - first.weekday()) % 7)
    return date(year, month, first_sunday + 7 * (n - 1))


def us_eastern_is_dst(d: date) -> bool:
    """True if US Eastern is on daylight saving (EDT) for releases on date ``d``.

    DST runs from the 2nd Sunday of March (02:00) to the 1st Sunday of November
    (02:00). Releases are weekday, post-02:00 events, so a date-level test is exact
    for them (the transition Sundays are never release days).
    """
    if d.year < 2007:
        raise ValueError(
            f"us_eastern_is_dst: date {d} predates the 2007 US DST rule this module encodes"
        )
    start = _nth_sunday(d.year, 3, 2)   # 2nd Sunday of March
    end = _nth_sunday(d.year, 11, 1)    # 1st Sunday of November
    return start <= d < end


def eastern_offset_hours(d: date) -> int:
    """UTC offset magnitude for US Eastern on date ``d``: 4 (EDT) or 5 (EST)."""
    return 4 if us_eastern_is_dst(d) else 5


# Canonical US release clock-times in Eastern, matched by event-name substring.
# Order matters: more specific rules first (ADP contains "non-farm" but is 08:15).
_RELEASE_ET_RULES: List[Tuple[Tuple[str, ...], Tuple[int, int]]] = [
    (("adp",), (8, 15)),
    (("fomc", "federal funds", "fed funds", "interest rate", "rate decision",
      "fed interest", "fed chair"), (14, 0)),
    (("ism", "consumer confidence", "jolts", "new home sales", "existing home sales",
      "pending home sales", "factory orders", "wholesale inventories",
      "consumer sentiment", "uom", "michigan", "business inventories",
      "construction spending"), (10, 0)),
    (("non-farm", "nonfarm", "average hourly", "cpi", "ppi", "retail sales",
      "core pce", "pce price", "gdp", "durable goods", "trade balance",
      "unemployment claims", "jobless claims", "personal income", "personal spending",
      "import prices", "export prices", "housing starts", "building permits",
      "empire state", "philly fed", "philadelphia fed", "employment cost",
      "nonfarm payroll", "challenger", "productivity", "unit labor"), (8, 30)),
]


def release_et_time(event_name: str) -> Optional[Tuple[int, int]]:
    """Canonical Eastern release (hour, minute) for a known US indicator, else None.

    Returns None for events whose release clock-time we do not know reliably; the
    runner skips those (and reports the count) rather than guessing a time.
    """
    name = (event_name or "").strip().lower()
    for patterns, hm in _RELEASE_ET_RULES:
        if any(p in name for p in patterns):
            return hm
    return None


def release_utc(event_name: str, release_date: date) -> Optional[datetime]:
    """The release instant in true UTC, DST-correct, or None if the time is unknown.

    Eastern local time + offset = UTC (UTC = ET + offset, since ET = UTC - offset).
    08:30 ET -> 12:30 UTC in EDT (offset 4), 13:30 UTC in EST (offset 5).
    """
    hm = release_et_time(event_name)
    if hm is None:
        return None
    hour, minute = hm
    offset = eastern_offset_hours(release_date)
    naive = datetime(release_date.year, release_date.month, release_date.day, hour, minute)
    return (naive + timedelta(hours=offset)).replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# HistData ASCII M1 loader (EST-no-DST -> UTC).
# ---------------------------------------------------------------------------

def parse_histdata_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse one HistData generic-ASCII M1 row to a UTC candle dict, or None.

    Format: ``YYYYMMDD HHMMSS;OPEN;HIGH;LOW;CLOSE;VOLUME`` stamped in EST (UTC-5,
    no DST). The returned ``timestamp`` is true UTC ISO-8601.
    """
    line = line.strip()
    if not line:
        return None
    parts = line.split(";")
    if len(parts) < 5:
        return None
    try:
        naive = datetime.strptime(parts[0].strip(), "%Y%m%d %H%M%S")
        o, h, l, c = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
    except (ValueError, IndexError):
        return None
    vol = 0.0
    if len(parts) > 5:
        try:
            vol = float(parts[5])
        except ValueError:
            vol = 0.0
    ts_utc = (naive + timedelta(hours=HISTDATA_FIXED_OFFSET_HOURS)).replace(tzinfo=timezone.utc)
    return {
        "timestamp": ts_utc.isoformat(),
        "open": o, "high": h, "low": l, "close": c, "volume": vol,
    }


def load_histdata_m1(paths: Sequence[str], *, lines: Optional[Iterable[str]] = None) -> List[dict]:
    """Load + merge HistData M1 archives into a single UTC-sorted, de-duplicated list.

    Pass file ``paths`` (one per month/year), or ``lines`` directly (used by the
    harness-validation tests). Bars are converted from EST-no-DST to true UTC,
    sorted ascending, and de-duplicated on timestamp (later file wins on overlap).
    """
    by_ts: Dict[str, dict] = {}

    def _ingest(iterable: Iterable[str]) -> None:
        for raw in iterable:
            candle = parse_histdata_line(raw)
            if candle is not None:
                by_ts[candle["timestamp"]] = candle

    if lines is not None:
        _ingest(lines)
    for path in paths:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            _ingest(fh)
    return [by_ts[k] for k in sorted(by_ts)]


# ---------------------------------------------------------------------------
# Causal per-indicator surprise standardisation (prior-only, no lookahead).
# ---------------------------------------------------------------------------

def causal_zscore(values: Sequence[float], min_history: int = 6) -> List[Optional[float]]:
    """z-score each value using only the values strictly before it (expanding window).

    None for the first ``min_history`` values (insufficient history to standardise
    without peeking). No future value ever enters an earlier value's score.
    """
    out: List[Optional[float]] = []
    import numpy as np

    for i in range(len(values)):
        prior = values[:i]
        if len(prior) < min_history:
            out.append(None)
            continue
        mu = float(np.mean(prior))
        sd = float(np.std(prior))
        out.append((float(values[i]) - mu) / sd if sd > 0 else 0.0)
    return out


# ---------------------------------------------------------------------------
# Intraday post-release window measurement.
# ---------------------------------------------------------------------------

def intraday_window_return(
    times_sec: Sequence[float],
    closes: Sequence[float],
    release_dt: datetime,
    *,
    entry_offset_min: int,
    horizon_min: int,
    max_gap_min: int = 5,
) -> Optional[Tuple[float, float]]:
    """(entry_price, pct_return) for the M1 window after ``release_dt``, else None.

    ``times_sec`` is the candles' UTC epoch-seconds (ascending); ``closes`` the matching
    closes. Entry = the first bar at/after ``release_dt + entry_offset_min``; exit = the
    first bar at/after that entry's time + ``horizon_min``. Strictly causal (never a bar
    before the release). Returns None when the release or the exit falls in a market hole
    (no bar within ``max_gap_min`` of the target — weekend/holiday/illiquid gap).
    """
    entry_target = release_dt.timestamp() + entry_offset_min * 60
    i = bisect.bisect_left(times_sec, entry_target)
    if i >= len(times_sec) or (times_sec[i] - entry_target) > max_gap_min * 60:
        return None
    exit_target = times_sec[i] + horizon_min * 60
    j = bisect.bisect_left(times_sec, exit_target)
    if j >= len(times_sec) or (times_sec[j] - exit_target) > max_gap_min * 60:
        return None
    entry = float(closes[i])
    exit_ = float(closes[j])
    if entry <= 0:
        return None
    return entry, (exit_ / entry - 1.0)


# ---------------------------------------------------------------------------
# Pre-registered window specs. PRIMARY is the headline verdict; the others are
# exploratory robustness and never become the verdict (avoids tuning-to-pass).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WindowSpec:
    label: str
    entry_offset_min: int
    horizon_min: int
    cost_pips: float


# Primary: enter ~1 min after the print (first M1 bar at/after release), hold 30 min,
# at a NEWS-REALISTIC 2.0-pip round-trip cost. The cost gate is the only place an
# optimistic cost can bite (the label-permutation null holds cost fixed — see the
# decision-rule note in the module docstring), so the headline uses a realistic-to-
# conservative cost rather than the 1-pip optimistic floor.
PRIMARY_SPEC = WindowSpec(label="primary_0to30_2pip", entry_offset_min=0, horizon_min=30, cost_pips=2.0)

# Exploratory robustness (reported, never the headline): a cost ladder around the
# primary window (1 pip optimistic / comparable to the daily test, 3 pip stress), a
# shorter hold, and a retail-realistic 5-min entry delay (you cannot fill the
# first-minute spike).
SECONDARY_SPECS: Tuple[WindowSpec, ...] = (
    WindowSpec(label="explore_0to30_1pip", entry_offset_min=0, horizon_min=30, cost_pips=1.0),
    WindowSpec(label="explore_0to30_3pip", entry_offset_min=0, horizon_min=30, cost_pips=3.0),
    WindowSpec(label="explore_0to15_2pip", entry_offset_min=0, horizon_min=15, cost_pips=2.0),
    WindowSpec(label="explore_5to30_2pip", entry_offset_min=5, horizon_min=25, cost_pips=2.0),
)


def build_intraday_usable(
    events_by_indicator: Dict[str, List[Dict[str, Any]]],
    candles: Sequence[dict],
    *,
    symbol: str,
    spec: WindowSpec,
    min_history: int = 6,
    max_gap_min: int = 5,
) -> Tuple[List[Dict[str, float]], Dict[str, int], Dict[str, Dict[str, float]]]:
    """Build the time-ordered [{surprise, ret, cost_ret}] pairs for one window spec.

    ``events_by_indicator`` maps an indicator name to a list of
    ``{"date": "YYYY-MM-DD", "surprise_raw": float}`` rows. Each indicator is causally
    z-scored on its own history; each release is aligned to the M1 bars in true UTC and
    measured over the window.

    CO-RELEASE COLLAPSE (null-exchangeability fix): several indicators print at the
    SAME instant (NFP + Average Hourly Earnings at 08:30; CPI + Core CPI together), so
    they share ONE identical post-release window and an identical return. Counting them
    as separate "events" would duplicate that window and break the shuffled-null's
    exchangeability (biasing toward a false edge on exactly the high-volatility days).
    Events sharing a release instant are collapsed to ONE observation, with their
    per-indicator causal surprises AVERAGED into a single combined standardized surprise.

    Returns: (usable pairs sorted by release instant, skip/collapse counts, per-indicator
    in-sample descriptive stats for transparency — see the mixture caveat).
    """
    import numpy as np

    pip = price_unit_size(symbol)
    times_sec = [_parse_time(c["timestamp"]).timestamp() for c in candles]
    closes = [float(c["close"]) for c in candles]

    groups: Dict[datetime, List[Tuple[float, float, float]]] = defaultdict(list)
    per_indicator: Dict[str, Dict[str, float]] = {}
    skipped: Counter = Counter()
    for indicator, rows in events_by_indicator.items():
        rows = sorted(rows, key=lambda r: r["date"])
        # Drop non-finite/garbage surprises BEFORE standardising, so a single bad cell is
        # excluded AND cannot pollute the causal z-score of this indicator's later releases.
        clean: List[Tuple[Dict[str, Any], float]] = []
        for r in rows:
            try:
                sv = float(r["surprise_raw"])
            except (TypeError, ValueError):
                skipped["bad_surprise"] += 1
                continue
            if not np.isfinite(sv):
                skipped["nonfinite_surprise"] += 1
                continue
            clean.append((r, sv))
        zs = causal_zscore([sv for _, sv in clean], min_history=min_history)
        n_ev = aligned_sum = 0.0
        hits = 0
        for (row, _sv), z in zip(clean, zs):
            if z is None:
                skipped["insufficient_history"] += 1
                continue
            try:
                d = date.fromisoformat(row["date"])
            except (ValueError, TypeError):
                skipped["bad_date"] += 1
                continue
            rdt = release_utc(indicator, d)
            if rdt is None:
                skipped["unknown_release_time"] += 1
                continue
            win = intraday_window_return(
                times_sec, closes, rdt,
                entry_offset_min=spec.entry_offset_min,
                horizon_min=spec.horizon_min,
                max_gap_min=max_gap_min,
            )
            if win is None:
                skipped["no_m1_window"] += 1
                continue
            entry, ret = win
            if not np.isfinite(ret):
                skipped["nonfinite_return"] += 1
                continue
            cost_ret = (spec.cost_pips * pip) / entry if entry > 0 else 0.0
            groups[rdt].append((float(z), float(ret), float(cost_ret)))
            sgn = 1.0 if z >= 0 else -1.0
            n_ev += 1
            aligned_sum += sgn * ret
            hits += 1 if (sgn > 0) == (ret > 0) else 0
        if n_ev:
            per_indicator[indicator] = {
                "events": int(n_ev),
                "mean_aligned_move_pct": round(100.0 * aligned_sum / n_ev, 5),
                "raw_hit_rate": round(hits / n_ev, 4),
            }

    # Collapse co-released indicators (identical release instant) into one window.
    co_released = 0
    collapsed: List[Tuple[datetime, float, float, float]] = []
    for rdt in sorted(groups):
        items = groups[rdt]
        if len(items) > 1:
            co_released += len(items) - 1
        zbar = float(np.mean([z for z, _, _ in items]))
        _, ret0, cost0 = items[0]  # identical window -> identical ret/cost across items
        collapsed.append((rdt, zbar, ret0, cost0))
    if co_released:
        skipped["co_released_collapsed"] = co_released

    usable = [{"surprise": z, "ret": ret, "cost_ret": cr} for _, z, ret, cr in collapsed]
    return usable, dict(skipped), per_indicator


@dataclass
class IntradayMacroReport:
    symbol: str
    primary: Dict[str, Any] = field(default_factory=dict)
    secondary: List[Dict[str, Any]] = field(default_factory=list)
    skipped: Dict[str, int] = field(default_factory=dict)
    per_indicator: Dict[str, Dict[str, float]] = field(default_factory=dict)
    claim_boundary: str = INTRADAY_CLAIM_BOUNDARY


def run_intraday_macro_test(
    events_by_indicator: Dict[str, List[Dict[str, Any]]],
    candles: Sequence[dict],
    *,
    symbol: str = "EUR/USD",
    primary: WindowSpec = PRIMARY_SPEC,
    secondary: Sequence[WindowSpec] = SECONDARY_SPECS,
    min_history: int = 6,
    n_null: int = 500,
    min_test_events: int = 8,
    max_gap_min: int = 5,
    seed: int = 11,
) -> IntradayMacroReport:
    """Run the pre-registered primary window (headline verdict) + exploratory secondaries.

    Every window is scored by the same leak-free OOS + shuffled-surprise null core.
    The headline verdict is the PRIMARY window only; secondaries are robustness context.
    """
    def _run(spec: WindowSpec) -> Tuple[Dict[str, Any], Dict[str, Dict[str, float]]]:
        usable, skipped, per_ind = build_intraday_usable(
            events_by_indicator, candles, symbol=symbol, spec=spec,
            min_history=min_history, max_gap_min=max_gap_min,
        )
        rep = evaluate_surprise_return_pairs(
            usable, symbol=symbol, horizon_bars=spec.horizon_min, cost_pips=spec.cost_pips,
            n_null=n_null, min_test_events=min_test_events, min_history=min_history, seed=seed,
        )
        out = dict(rep.summary)
        out["window"] = {
            "label": spec.label, "entry_offset_min": spec.entry_offset_min,
            "horizon_min": spec.horizon_min, "cost_pips": spec.cost_pips,
        }
        out["skipped"] = dict(skipped)
        return out, per_ind

    primary_out, primary_per_ind = _run(primary)
    secondary_out = [_run(s)[0] for s in secondary]
    return IntradayMacroReport(
        symbol=symbol,
        primary=primary_out,
        secondary=secondary_out,
        skipped=primary_out.get("skipped", {}),
        per_indicator=primary_per_ind,
    )


# ---------------------------------------------------------------------------
# HARNESS-VALIDATION-ONLY synthetic generators.
# NOT REAL MARKET DATA. These build HistData-format M1 lines + a calendar so the
# whole pipeline (loader -> DST schedule -> window -> null core) can be proven to
# (a) detect a planted signal, (b) reject pure noise, and (c) align EST-no-DST bars
# with ET-with-DST releases across a DST boundary. A synthetic CANDIDATE_EDGE is a
# statement about the harness, never about markets.
# ---------------------------------------------------------------------------

_SYNTH_INDICATORS = (
    "Non-Farm Employment Change",   # 08:30 ET
    "ISM Manufacturing PMI",        # 10:00 ET
    "CPI m/m",                      # 08:30 ET
)


def _weekdays_from(start: date, n: int) -> List[date]:
    out: List[date] = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:  # Mon-Fri
            out.append(d)
        d += timedelta(days=1)
    return out


def synthetic_histdata_and_calendar(
    *,
    mode: str,
    n_events: int = 90,
    horizon_min: int = 30,
    effect: float = 0.004,
    noise: float = 0.0008,
    base: float = 1.10,
    seed: int = 3,
    start: date = date(2023, 1, 3),
) -> Tuple[List[str], Dict[str, List[Dict[str, Any]]]]:
    """Build HistData-format M1 lines + a calendar for HARNESS VALIDATION ONLY.

    Releases cycle through indicators with known ET times across a span that crosses
    the March DST boundary, so a passing power test also proves timezone alignment.
    mode='noise'  -> post-release move independent of surprise (instrument must say NO_SKILL).
    mode='signal' -> post-release move = sign(surprise)*effect + noise (must say CANDIDATE_EDGE).
    Bars are emitted ONLY around each release (release-5min .. release+horizon+5min) for
    efficiency; the gap-tolerant window measurement handles the gaps between releases.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    days = _weekdays_from(start, n_events)
    events_by_indicator: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    lines: List[str] = []

    for i, d in enumerate(days):
        indicator = _SYNTH_INDICATORS[i % len(_SYNTH_INDICATORS)]
        expected = 2.0
        actual = expected + float(rng.normal(0, 1.0))
        surprise = actual - expected
        events_by_indicator[indicator].append({"date": d.isoformat(), "surprise_raw": surprise})

        rdt = release_utc(indicator, d)  # the REAL schedule (ET + DST -> UTC)
        assert rdt is not None, f"synthetic indicator {indicator!r} must have a known release time"

        if mode == "signal":
            move = (1.0 if surprise >= 0 else -1.0) * effect + float(rng.normal(0, noise))
        else:
            move = float(rng.normal(0, effect))  # independent of surprise

        # Emit minute bars from release-5 .. release+horizon+5, flat before release,
        # then the planted move spread across the horizon after release.
        pre, post = 5, horizon_min + 5
        per = move / horizon_min
        price = base
        for k in range(-pre, post + 1):
            bar_utc = rdt + timedelta(minutes=k)
            if k > 0:
                price = price * (1.0 + per) if k <= horizon_min else price
            # Convert UTC bar instant to HistData EST-no-DST wall clock (UTC - 5h).
            hist_local = bar_utc - timedelta(hours=HISTDATA_FIXED_OFFSET_HOURS)
            stamp = hist_local.strftime("%Y%m%d %H%M%S")
            p = round(price, 5)
            lines.append(f"{stamp};{p};{p};{p};{p};0")

    return lines, dict(events_by_indicator)


def recipe_string() -> str:
    """The intraday cell as a CAS recipe (the open-cause ^8 ingredient, at M1 scale)."""
    return (
        "Theta(Omega_intraday_post_release_move) = "
        "w * macro_surprise|open_cause -> Omega_intraday_post_release_move"
    )
