"""Profit OBJECTIVE for the adaptive AI loop — the pace board, NOT a trade forcer.

The owner's goal is concrete: >= $5,000/month profit = $250/day across 20 forex
trading days. This module turns that goal into honest pace arithmetic so the loop
(and the cockpit UI) can always answer "are we ahead or behind, and by how much?".

THE CARDINAL HONESTY RULE OF THIS MODULE
----------------------------------------
Being behind pace is a REPORT, never an instruction. ``pace_status`` computes the
gap between where the month should be and where it actually is, and the dollar
amount that WOULD close today's gap — but it does NOT, and must NOT, lower the
edge threshold, widen risk, or otherwise pressure the test gate into trading. The
edge bar (``edge_threshold_default``) is a constant here; nothing in this module
touches it. A no-edge day is a legitimate $0 day with capital protected. The pace
board exists so the owner sees reality, not so the system rationalizes a bad trade.

Direction is never decided here. Win-probability is never decided here. This is
purely the scoreboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, Set


def trading_day_index_of(d: date, month_start: date, holidays: Set[date] = frozenset()) -> int:
    """Count weekday trading days from ``month_start`` up to and including ``d``.

    Mon-Fri count as trading days; Saturdays, Sundays, and any date in
    ``holidays`` are skipped. The result is 1-based on the first trading day of
    the window (so the first weekday non-holiday on/after ``month_start`` is 1).

    Returns 0 if ``d`` is before ``month_start``, or if ``d`` itself is a weekend
    or holiday and no trading day has occurred yet in the window. If ``d`` is a
    non-trading day but trading days have already passed, the count reflects the
    last trading day on/before ``d``.
    """
    if d < month_start:
        return 0
    holidays = set(holidays)
    count = 0
    cur = month_start
    while cur <= d:
        if cur.weekday() < 5 and cur not in holidays:
            count += 1
        cur = cur + timedelta(days=1)
    return count


@dataclass(frozen=True)
class ProfitObjective:
    """The owner's monetary objective, expressed as honest pace math.

    Defaults encode the agreed mission: $5,000/month over 20 trading days at a
    $250/day cadence, with a default win-probability bar of 0.65 for the null
    test gate. ``edge_threshold_default`` lives here as the OBJECTIVE's view of
    the bar; the actual gate owns the live, user-adjustable value. This module
    only reports against the goal — it never relaxes the bar to hit the number.
    """

    monthly_target: float = 5000.0
    daily_target: float = 250.0          # daily FLOOR / minimum target (the $5k/mo pace)
    daily_max_target: float = 3500.0     # daily CAP / max — once hit, STOP opening new trades that day
    trading_days: int = 20
    edge_threshold_default: float = 0.65

    def pace_status(
        self,
        realized_month_to_date: float,
        trading_day_index: int,
        today_realized: float,
    ) -> Dict[str, float]:
        """Where the month SHOULD be vs where it IS — a scoreboard, not an order.

        Parameters
        ----------
        realized_month_to_date:
            Broker-realized profit accumulated so far this month (may be negative).
        trading_day_index:
            1-based index of today within the trading month (see
            ``trading_day_index_of``). Clamped to [0, trading_days].
        today_realized:
            Broker-realized profit booked today (may be negative).

        Returns a dict with:
            target_to_date  -- daily_target * completed trading days so far
            actual_to_date  -- realized_month_to_date
            ahead_behind    -- actual_to_date - target_to_date (negative = behind)
            needed_today    -- dollars that WOULD bring today up to daily_target
                               (max(0, daily_target - today_realized)); purely
                               informational, never an instruction to force trades
            on_pace         -- bool: actual_to_date >= target_to_date
            pct_to_monthly  -- actual_to_date / monthly_target, in fraction form
        """
        idx = max(0, min(int(trading_day_index), int(self.trading_days)))
        target_to_date = round(self.daily_target * idx, 2)
        actual_to_date = round(float(realized_month_to_date), 2)
        ahead_behind = round(actual_to_date - target_to_date, 2)
        needed_today = round(max(0.0, self.daily_target - float(today_realized)), 2)
        pct_to_monthly = (
            round(actual_to_date / self.monthly_target, 6)
            if self.monthly_target
            else 0.0
        )
        return {
            "target_to_date": target_to_date,
            "actual_to_date": actual_to_date,
            "ahead_behind": ahead_behind,
            "needed_today": needed_today,
            "on_pace": actual_to_date >= target_to_date,
            "pct_to_monthly": pct_to_monthly,
            "daily_cap": self.daily_max_target,
            "daily_cap_hit": float(today_realized) >= self.daily_max_target,
            "daily_cap_remaining": round(max(0.0, self.daily_max_target - float(today_realized)), 2),
        }

    def daily_cap_reached(self, today_realized: float) -> bool:
        """True once today's realized profit has hit the daily CAP (``daily_max_target``).

        When True, the loop must STOP opening new trades for the day and protect the
        gains — a hard stop-for-the-day so a great day is never given back. The cap is
        an owner-set slider (default $3,500); this is risk discipline, not a forecast.
        """
        return float(today_realized) >= self.daily_max_target
