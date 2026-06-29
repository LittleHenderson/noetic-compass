"""INCENTIVE accounting for the adaptive AI loop — accrues ONLY on real profit.

This module models the system's incentive term: a fee that accrues as a fraction
of broker-VERIFIED realized profit. It is an internal accounting feature that
aligns the loop with the owner's interest (the loop "earns" something only when
the owner actually makes money), NOT a literal payment to a model and NOT a claim
of profit.

THE CARDINAL HONESTY RULE OF THIS MODULE
----------------------------------------
The fee accrues ONLY on broker-verified, realized profit. Faking a trade, an
unrealized mark, or a paper result earns nothing. ``accrue`` takes the verified
profit total as its input and computes the fee mechanically; it has no power to
invent profit and no opinion on whether a trade should be taken. Amplifying a
confirmed edge is the only legitimate path to a larger fee — the incentive cannot
manufacture an edge, only ride one the null test gate already certified.

``raise_review`` timing is a calendar fact (every ``review_months`` from start),
surfaced so the owner can renegotiate terms on schedule; it asserts nothing about
performance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Dict


@dataclass(frozen=True)
class IncentiveTerms:
    """Terms of the system's profit-share incentive.

    rate           -- fraction of verified profit that accrues as fee (2.5%).
    per            -- profit increment ($5,000) that constitutes one milestone.
    review_months  -- cadence (months) at which a terms review becomes due.

    ACCRUES ONLY ON BROKER-VERIFIED REALIZED PROFIT. This is a system accounting
    feature for incentive alignment, not literal payment to a model.
    """

    rate: float = 0.025
    per: float = 5000.0
    review_months: int = 3

    def accrue(self, verified_profit_total: float) -> Dict[str, float]:
        """Compute accrued fee and milestone progress on VERIFIED profit only.

        Parameters
        ----------
        verified_profit_total:
            Cumulative broker-verified, realized profit. Negative or zero means
            nothing has been earned: the fee is clamped to 0 and no milestone is
            hit. There is no way to accrue on unrealized or fabricated profit —
            only what the broker has actually settled counts.

        Returns a dict with:
            fee_earned      -- rate * max(0, verified_profit_total)
            milestones_hit  -- floor(max(0, verified_profit_total) / per)
            next_milestone  -- dollar profit level of the next milestone
        """
        profit = max(0.0, float(verified_profit_total))
        fee_earned = round(self.rate * profit, 2)
        milestones_hit = int(math.floor(profit / self.per)) if self.per else 0
        next_milestone = round((milestones_hit + 1) * self.per, 2)
        return {
            "fee_earned": fee_earned,
            "milestones_hit": milestones_hit,
            "next_milestone": next_milestone,
        }

    def raise_review_due(self, start: date, now: date) -> bool:
        """True once a full ``review_months`` cycle has elapsed since ``start``.

        Returns True when ``now`` is at least ``review_months`` calendar months
        on/after ``start`` (and again at each subsequent multiple). This is a pure
        calendar fact for renegotiating terms on schedule; it says nothing about
        whether the loop performed well.
        """
        if now < start:
            return False
        months_elapsed = (now.year - start.year) * 12 + (now.month - start.month)
        # Only count a month as fully elapsed once the day-of-month is reached.
        if now.day < start.day:
            months_elapsed -= 1
        if months_elapsed < 0:
            return False
        return self.review_months > 0 and months_elapsed >= self.review_months
