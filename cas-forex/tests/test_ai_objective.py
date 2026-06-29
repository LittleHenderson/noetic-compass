"""Tests for the OBJECTIVE + INCENTIVE modules.

These verify the scoreboard math, the trading-day counter, and the incentive
accrual — including the load-bearing honesty invariants (behind-pace never lowers
the bar; fee accrues only on non-negative verified profit).
"""

from datetime import date

from cas_forex.ai_objective import ProfitObjective, trading_day_index_of
from cas_forex.ai_incentive import IncentiveTerms


# --------------------------------------------------------------------------
# ProfitObjective.pace_status
# --------------------------------------------------------------------------

def test_pace_on_pace():
    obj = ProfitObjective()
    # Day 4: target = 4 * 250 = 1000; actual exactly on target.
    status = obj.pace_status(realized_month_to_date=1000.0, trading_day_index=4, today_realized=250.0)
    assert status["target_to_date"] == 1000.0
    assert status["actual_to_date"] == 1000.0
    assert status["ahead_behind"] == 0.0
    assert status["on_pace"] is True
    assert status["needed_today"] == 0.0
    assert status["pct_to_monthly"] == round(1000.0 / 5000.0, 6)


def test_pace_behind():
    obj = ProfitObjective()
    # Day 4: target 1000, only 400 realized -> 600 behind, not on pace.
    status = obj.pace_status(realized_month_to_date=400.0, trading_day_index=4, today_realized=100.0)
    assert status["target_to_date"] == 1000.0
    assert status["ahead_behind"] == -600.0
    assert status["on_pace"] is False
    # needed_today reports the gap to the DAILY target only, never an instruction.
    assert status["needed_today"] == 150.0


def test_pace_ahead():
    obj = ProfitObjective()
    # Day 2: target 500, 900 realized -> 400 ahead.
    status = obj.pace_status(realized_month_to_date=900.0, trading_day_index=2, today_realized=300.0)
    assert status["target_to_date"] == 500.0
    assert status["ahead_behind"] == 400.0
    assert status["on_pace"] is True
    # Already past daily target today -> needed_today clamps to 0.
    assert status["needed_today"] == 0.0


def test_pace_negative_day_and_negative_mtd():
    obj = ProfitObjective()
    # Losing day: today_realized negative -> needed_today exceeds daily target.
    status = obj.pace_status(realized_month_to_date=-200.0, trading_day_index=3, today_realized=-150.0)
    assert status["actual_to_date"] == -200.0
    assert status["target_to_date"] == 750.0
    assert status["ahead_behind"] == -950.0
    assert status["on_pace"] is False
    assert status["needed_today"] == 400.0  # 250 - (-150)
    assert status["pct_to_monthly"] == round(-200.0 / 5000.0, 6)


def test_pace_clamps_day_index():
    obj = ProfitObjective()
    # Index beyond trading_days clamps to 20.
    status = obj.pace_status(realized_month_to_date=5000.0, trading_day_index=99, today_realized=0.0)
    assert status["target_to_date"] == 5000.0  # 20 * 250
    # Negative index clamps to 0.
    status0 = obj.pace_status(realized_month_to_date=0.0, trading_day_index=-5, today_realized=0.0)
    assert status0["target_to_date"] == 0.0


def test_objective_does_not_expose_a_mutable_bar_lowering_path():
    # Honesty invariant: the edge threshold is a constant on the objective; pace
    # status output contains no field that lowers it. The dict keys are fixed.
    obj = ProfitObjective()
    assert obj.edge_threshold_default == 0.65
    status = obj.pace_status(realized_month_to_date=0.0, trading_day_index=10, today_realized=0.0)
    assert set(status.keys()) == {
        "target_to_date", "actual_to_date", "ahead_behind",
        "needed_today", "on_pace", "pct_to_monthly",
        # owner's daily profit band ($250 floor .. $3,500 cap) — none of these
        # touches the edge threshold; the cap only STOPS trading, never relaxes the bar.
        "daily_cap", "daily_cap_hit", "daily_cap_remaining",
    }
    # Being far behind does not change the bar.
    assert obj.edge_threshold_default == 0.65


# --------------------------------------------------------------------------
# trading_day_index_of
# --------------------------------------------------------------------------

def test_trading_day_counting_basic_week():
    # June 2026: 1st is a Monday.
    month_start = date(2026, 6, 1)
    assert trading_day_index_of(date(2026, 6, 1), month_start) == 1   # Mon
    assert trading_day_index_of(date(2026, 6, 2), month_start) == 2   # Tue
    assert trading_day_index_of(date(2026, 6, 5), month_start) == 5   # Fri
    # Sat/Sun do not advance the count.
    assert trading_day_index_of(date(2026, 6, 6), month_start) == 5   # Sat
    assert trading_day_index_of(date(2026, 6, 7), month_start) == 5   # Sun
    assert trading_day_index_of(date(2026, 6, 8), month_start) == 6   # next Mon


def test_trading_day_counting_with_holidays():
    month_start = date(2026, 6, 1)
    holidays = {date(2026, 6, 3)}  # skip Wednesday
    # Mon=1, Tue=2, Wed(holiday)=still 2, Thu=3.
    assert trading_day_index_of(date(2026, 6, 3), month_start, holidays) == 2
    assert trading_day_index_of(date(2026, 6, 4), month_start, holidays) == 3


def test_trading_day_before_month_start_is_zero():
    month_start = date(2026, 6, 1)
    assert trading_day_index_of(date(2026, 5, 31), month_start) == 0


def test_trading_day_full_20_day_month():
    # Count to the 20th trading day of June 2026.
    month_start = date(2026, 6, 1)
    # 4 full weeks (Mon Jun 1 .. Fri Jun 26) = 20 weekdays.
    assert trading_day_index_of(date(2026, 6, 26), month_start) == 20


# --------------------------------------------------------------------------
# IncentiveTerms.accrue
# --------------------------------------------------------------------------

def test_incentive_accrual_5000_yields_125():
    terms = IncentiveTerms()
    out = terms.accrue(5000.0)
    assert out["fee_earned"] == 125.0  # 0.025 * 5000
    assert out["milestones_hit"] == 1
    assert out["next_milestone"] == 10000.0


def test_incentive_milestone_math():
    terms = IncentiveTerms()
    # $12,500 verified -> 2 full milestones, next at 15000.
    out = terms.accrue(12500.0)
    assert out["milestones_hit"] == 2
    assert out["next_milestone"] == 15000.0
    assert out["fee_earned"] == round(0.025 * 12500.0, 2)


def test_incentive_zero_and_negative_profit_earns_nothing():
    terms = IncentiveTerms()
    for amount in (0.0, -1000.0):
        out = terms.accrue(amount)
        assert out["fee_earned"] == 0.0
        assert out["milestones_hit"] == 0
        assert out["next_milestone"] == 5000.0


def test_incentive_partial_milestone_not_counted():
    terms = IncentiveTerms()
    out = terms.accrue(4999.99)
    assert out["milestones_hit"] == 0
    assert out["next_milestone"] == 5000.0


# --------------------------------------------------------------------------
# IncentiveTerms.raise_review_due
# --------------------------------------------------------------------------

def test_raise_review_not_due_before_cadence():
    terms = IncentiveTerms()  # review_months=3
    start = date(2026, 6, 28)
    assert terms.raise_review_due(start, date(2026, 6, 28)) is False
    assert terms.raise_review_due(start, date(2026, 8, 28)) is False  # 2 months
    # One day short of 3 months.
    assert terms.raise_review_due(start, date(2026, 9, 27)) is False


def test_raise_review_due_at_cadence():
    terms = IncentiveTerms()
    start = date(2026, 6, 28)
    assert terms.raise_review_due(start, date(2026, 9, 28)) is True   # exactly 3 months
    assert terms.raise_review_due(start, date(2026, 12, 28)) is True  # 6 months
    assert terms.raise_review_due(start, date(2027, 1, 5)) is True


def test_raise_review_now_before_start_is_false():
    terms = IncentiveTerms()
    start = date(2026, 6, 28)
    assert terms.raise_review_due(start, date(2026, 1, 1)) is False
