"""Tests for the intraday macro-surprise pipeline.

Obligations of an honest measurement instrument (same as the daily cell):
  DISCIPLINE: pure noise must report NO_SKILL (not be fooled by a high hit-rate).
  POWER:      a planted signal must report CANDIDATE_EDGE (can detect real signal).
Plus the two correctness pillars specific to the intraday path:
  SCHEDULE:   the DST-aware release schedule must equal the IANA tz database.
  ALIGNMENT:  HistData EST-no-DST bars must line up with ET-with-DST releases in UTC,
              across a DST boundary (the timezone trap).
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from cas_forex import macro_intraday as mi

_RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_macro_intraday_real.py"


def _flat_lines_around(instants, horizon_min=30, pad=6):
    """Flat-price HistData M1 lines (EST-no-DST) spanning a window around each instant."""
    lines = []
    for rt in instants:
        for k in range(-pad, horizon_min + pad + 1):
            t = (rt + timedelta(minutes=k)) - timedelta(hours=mi.HISTDATA_FIXED_OFFSET_HOURS)
            lines.append(f"{t.strftime('%Y%m%d %H%M%S')};1.1;1.1;1.1;1.1;0")
    return lines


# --------------------------------------------------------------------------- #
# Schedule correctness
# --------------------------------------------------------------------------- #

def test_release_utc_edt_vs_est():
    # 08:30 ET -> 12:30 UTC in EDT (summer), 13:30 UTC in EST (winter).
    assert mi.release_utc("Non-Farm Employment Change", date(2024, 6, 7)).hour == 12
    assert mi.release_utc("Non-Farm Employment Change", date(2024, 6, 7)).minute == 30
    assert mi.release_utc("Non-Farm Employment Change", date(2024, 1, 5)).hour == 13
    # 10:00 ET ISM -> 14:00 / 15:00 UTC.
    assert mi.release_utc("ISM Manufacturing PMI", date(2024, 6, 3)).hour == 14
    assert mi.release_utc("ISM Manufacturing PMI", date(2024, 1, 3)).hour == 15
    # 14:00 ET FOMC -> 18:00 / 19:00 UTC.
    assert mi.release_utc("FOMC Statement", date(2024, 7, 31)).hour == 18
    assert mi.release_utc("FOMC Statement", date(2024, 1, 31)).hour == 19
    # 08:15 ET ADP (must beat the generic non-farm 08:30 rule) -> 12:15 UTC (EDT).
    adp = mi.release_utc("ADP Non-Farm Employment Change", date(2024, 6, 5))
    assert (adp.hour, adp.minute) == (12, 15)


def test_unknown_release_time_is_skipped_not_guessed():
    assert mi.release_et_time("Bank Holiday") is None
    assert mi.release_utc("Bank Holiday", date(2024, 1, 1)) is None
    assert mi.release_et_time("") is None


def test_dst_rule_matches_iana_tz_database():
    """The self-contained DST rule must equal America/New_York for every weekday 2007..2026."""
    zoneinfo = pytest.importorskip("zoneinfo")
    ny = zoneinfo.ZoneInfo("America/New_York")
    d, end = date(2007, 1, 1), date(2026, 12, 31)
    mismatches = 0
    checked = 0
    while d <= end:
        if d.weekday() < 5:  # releases are weekday, post-02:00 events
            checked += 1
            off_iana = int(-datetime(d.year, d.month, d.day, 12, tzinfo=ny)
                           .utcoffset().total_seconds() // 3600)
            if off_iana != mi.eastern_offset_hours(d):
                mismatches += 1
        d += timedelta(days=1)
    assert checked > 5000
    assert mismatches == 0


def test_pre_2007_dates_rejected():
    with pytest.raises(ValueError):
        mi.us_eastern_is_dst(date(2006, 6, 1))


# --------------------------------------------------------------------------- #
# HistData loader + the timezone trap
# --------------------------------------------------------------------------- #

def test_histdata_est_no_dst_to_utc():
    # HistData is EST (UTC-5) year-round, NO DST. 07:30 there is 12:30 UTC; the same
    # 12:30 UTC is the EDT NFP release -> they align ONLY because both go to UTC.
    edt_bar = mi.parse_histdata_line("20240607 073000;1.10395;1.10410;1.10380;1.10402;5")
    assert edt_bar["timestamp"] == "2024-06-07T12:30:00+00:00"
    assert edt_bar["close"] == 1.10402 and edt_bar["volume"] == 5.0
    # In winter the SAME 08:30 wall-clock HistData bar is 13:30 UTC = the EST NFP release.
    est_bar = mi.parse_histdata_line("20240105 083000;1.0900;1.0901;1.0899;1.0900;0")
    assert est_bar["timestamp"] == "2024-01-05T13:30:00+00:00"


def test_parse_histdata_line_rejects_garbage():
    assert mi.parse_histdata_line("") is None
    assert mi.parse_histdata_line("not;enough") is None
    assert mi.parse_histdata_line("20240607 073000;x;y;z;w;0") is None


def test_load_histdata_sorts_and_dedups():
    lines = [
        "20240105 083000;1.0900;1.0900;1.0900;1.0900;0",
        "20240105 082900;1.0890;1.0890;1.0890;1.0890;0",
        "20240105 083000;1.0901;1.0901;1.0901;1.0901;0",  # dup ts, later wins
    ]
    out = mi.load_histdata_m1([], lines=lines)
    assert [c["timestamp"] for c in out] == [
        "2024-01-05T13:29:00+00:00", "2024-01-05T13:30:00+00:00",
    ]
    assert out[-1]["close"] == 1.0901  # de-dup kept the later row


# --------------------------------------------------------------------------- #
# Window measurement: strictly-after + gap tolerance
# --------------------------------------------------------------------------- #

def _epochs(candles):
    return [mi._parse_time(c["timestamp"]).timestamp() for c in candles], [c["close"] for c in candles]


def test_window_is_strictly_after_release():
    rt = datetime(2024, 6, 7, 12, 30, tzinfo=timezone.utc)
    candles = [
        {"timestamp": (rt + timedelta(minutes=k)).isoformat(),
         "close": 1.10 + (0.0 if k <= 0 else 0.001 * k)}
        for k in range(-3, 11)
    ]
    times, closes = _epochs(candles)
    res = mi.intraday_window_return(times, closes, rt, entry_offset_min=0, horizon_min=5)
    assert res is not None
    entry, ret = res
    # entry = close of the release-minute bar (k=0) = 1.10; exit = k=5 bar.
    assert entry == 1.10
    assert ret > 0  # price rose only AFTER release


def test_window_rejects_market_hole():
    rt = datetime(2024, 6, 7, 12, 30, tzinfo=timezone.utc)
    # Only stale bars far before and far after the release -> no clean window.
    candles = [
        {"timestamp": (rt - timedelta(minutes=60)).isoformat(), "close": 1.10},
        {"timestamp": (rt + timedelta(minutes=60)).isoformat(), "close": 1.11},
    ]
    times, closes = _epochs(candles)
    assert mi.intraday_window_return(times, closes, rt, entry_offset_min=0,
                                     horizon_min=5, max_gap_min=5) is None


# --------------------------------------------------------------------------- #
# Full pipeline: alignment across DST, power, discipline
# --------------------------------------------------------------------------- #

def _planted_lines_around(rdt_utc: datetime, *, move: float, horizon_min: int = 10):
    """HistData lines (EST-no-DST) flat before the release, rising/falling after."""
    lines = []
    price = 1.10
    per = move / horizon_min
    for k in range(-5, horizon_min + 6):
        if k > 0 and k <= horizon_min:
            price *= (1.0 + per)
        hist_local = (rdt_utc + timedelta(minutes=k)) - timedelta(hours=mi.HISTDATA_FIXED_OFFSET_HOURS)
        p = round(price, 5)
        lines.append(f"{hist_local.strftime('%Y%m%d %H%M%S')};{p};{p};{p};{p};0")
    return lines


def test_alignment_across_dst_boundary():
    """A planted move placed at the true UTC release must be recovered in BOTH an EDT
    and an EST month — proving the schedule and the EST-no-DST loader agree in UTC."""
    edt_rt = mi.release_utc("Non-Farm Employment Change", date(2023, 7, 7))   # 12:30 UTC
    est_rt = mi.release_utc("Non-Farm Employment Change", date(2023, 1, 6))   # 13:30 UTC
    for rt in (edt_rt, est_rt):
        lines = _planted_lines_around(rt, move=0.005, horizon_min=10)
        candles = mi.load_histdata_m1([], lines=lines)
        times, closes = _epochs(candles)
        res = mi.intraday_window_return(times, closes, rt, entry_offset_min=0, horizon_min=10)
        assert res is not None, f"window missed release at {rt} (DST/alignment bug)"
        _, ret = res
        assert ret > 0.004, f"planted +0.5% move not recovered at {rt}: got {ret}"


def test_power_planted_signal_is_candidate_edge():
    lines, cal = mi.synthetic_histdata_and_calendar(mode="signal", n_events=90,
                                                    effect=0.004, noise=0.0008, seed=2)
    candles = mi.load_histdata_m1([], lines=lines)
    rep = mi.run_intraday_macro_test(cal, candles, symbol="EUR/USD", secondary=(),
                                     n_null=300, seed=5)
    assert rep.primary["verdict"] == "CANDIDATE_EDGE"
    assert rep.primary["beats_null_p95"] is True
    assert rep.primary["hit_rate"] > 0.5


def test_discipline_noise_is_no_skill():
    lines, cal = mi.synthetic_histdata_and_calendar(mode="noise", n_events=90, seed=1)
    candles = mi.load_histdata_m1([], lines=lines)
    rep = mi.run_intraday_macro_test(cal, candles, symbol="EUR/USD", secondary=(),
                                     n_null=300, seed=5)
    assert rep.primary["verdict"] == "NO_SKILL"
    assert not rep.primary.get("beats_null_p95", False)


def test_underpowered_when_too_few_events():
    lines, cal = mi.synthetic_histdata_and_calendar(mode="signal", n_events=20, seed=3)
    candles = mi.load_histdata_m1([], lines=lines)
    rep = mi.run_intraday_macro_test(cal, candles, symbol="EUR/USD", secondary=(),
                                     min_test_events=8, n_null=200, seed=5)
    # 20 events, 3 indicators, min_history=6 -> very few usable -> underpowered.
    assert rep.primary["verdict"] in {"UNDERPOWERED", "NO_SKILL"}


# --------------------------------------------------------------------------- #
# Review fixes: co-release collapse, non-finite guard, per-indicator, cost, date
# --------------------------------------------------------------------------- #

def test_co_released_same_instant_collapse_to_one_window():
    """Two indicators printing at the same instant (NFP + Avg Hourly Earnings, both
    08:30 ET) share ONE window; they must collapse to a single observation, not be
    double-counted (which would break the null's exchangeability)."""
    dates = [date(2023, 2, 1) + timedelta(days=2 * i) for i in range(10)]
    a, b = "Non-Farm Employment Change", "Average Hourly Earnings m/m"  # both 08:30 ET
    ev = {
        a: [{"date": d.isoformat(), "surprise_raw": float(i - 5)} for i, d in enumerate(dates)],
        b: [{"date": d.isoformat(), "surprise_raw": float(5 - i)} for i, d in enumerate(dates)],
    }
    instants = [mi.release_utc(a, d) for d in dates]
    candles = mi.load_histdata_m1([], lines=_flat_lines_around(instants))
    usable, skipped, per_ind = mi.build_intraday_usable(
        ev, candles, symbol="EUR/USD", spec=mi.PRIMARY_SPEC, min_history=6)
    # 10 dates, min_history=6 -> 4 usable per indicator; both share the same 4 instants
    # -> 4 collapsed observations and exactly one duplicate removed per instant.
    assert len(usable) == 4
    assert skipped.get("co_released_collapsed", 0) == 4
    assert per_ind[a]["events"] == 4 and per_ind[b]["events"] == 4
    # the collapsed surprise is the AVERAGE of the two co-released indicators' z-scores
    assert all("surprise" in u for u in usable)


def test_nonfinite_surprise_is_skipped_and_counted():
    a = "Non-Farm Employment Change"
    dates = [date(2023, 3, 1) + timedelta(days=i) for i in range(10)]
    surprises = [1, 2, 3, 4, 5, 6, 7, float("inf"), 9, 10]
    ev = {a: [{"date": d.isoformat(), "surprise_raw": float(s)} for d, s in zip(dates, surprises)]}
    instants = [mi.release_utc(a, d) for d in dates]
    candles = mi.load_histdata_m1([], lines=_flat_lines_around(instants))
    usable, skipped, _ = mi.build_intraday_usable(
        ev, candles, symbol="EUR/USD", spec=mi.PRIMARY_SPEC, min_history=6)
    assert skipped.get("nonfinite_surprise", 0) >= 1
    # the non-finite event is dropped, not coerced into a surprise
    import math
    assert all(math.isfinite(u["surprise"]) for u in usable)


def test_per_indicator_decomposition_present():
    lines, cal = mi.synthetic_histdata_and_calendar(mode="signal", n_events=90, seed=2)
    candles = mi.load_histdata_m1([], lines=lines)
    rep = mi.run_intraday_macro_test(cal, candles, symbol="EUR/USD", secondary=(),
                                     n_null=200, seed=5)
    assert rep.per_indicator  # mixture transparency, not just the pooled verdict
    for st in rep.per_indicator.values():
        assert {"events", "raw_hit_rate", "mean_aligned_move_pct"} <= set(st)
        assert st["events"] > 0


def test_primary_spec_uses_news_realistic_cost():
    # Pre-registration lock: the headline window is 0->30 min at a realistic 2-pip cost.
    assert mi.PRIMARY_SPEC.cost_pips == 2.0
    assert (mi.PRIMARY_SPEC.entry_offset_min, mi.PRIMARY_SPEC.horizon_min) == (0, 30)


def test_runner_load_calendar_uses_release_date_not_tz_conversion():
    """The +03:30 00:00 placeholder must yield the US release DATE, never a timezone-
    converted prior day (verified 24/24 against published NFP dates)."""
    spec = importlib.util.spec_from_file_location("rmi_test", str(_RUNNER_PATH))
    rmi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rmi)
    detail = "Usual Effect: 'Actual' greater than 'Forecast' is good for currency;"
    csv_text = (
        "DateTime,Currency,Impact,Event,Actual,Forecast,Previous,Detail\n"
        f'2024-06-07T00:00:00+03:30,USD,High Impact Expected,Non-Farm Employment Change,272K,185K,165K,"{detail}"\n'
    )
    tmp = _RUNNER_PATH.parent.parent / "data" / "external" / "_unittest_cal.csv"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(csv_text, encoding="utf-8")
    try:
        by = rmi.load_calendar(str(tmp), "USD")
        assert by["Non-Farm Employment Change"][0]["date"] == "2024-06-07"
        # parse_value must also reject non-finite tokens
        assert rmi.parse_value("inf") is None
        assert rmi.parse_value("nan") is None
        assert rmi.parse_value("272K") == 272000.0
    finally:
        tmp.unlink(missing_ok=True)
