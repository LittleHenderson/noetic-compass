"""Paired-difference statistics — P4 of the kill-criteria margins.

M1 and M3 are margins over an unstructured baseline, and P4 pins how they are
judged:

> The 95% CI is on the paired per-item difference (board - baseline), not on
> each arm separately. Threshold judged on the lower bound. Pairing is the
> whole point of using the same items in both arms; intervals computed per-arm
> throw that power away.

Everything here is stdlib. The rest of the CCB-R1 harness has no third-party
dependency and CI runs it with a bare `python -m unittest`, so adding numpy or
scipy for a bootstrap and a binomial tail would be the single heaviest cost in
the programme for the least benefit.

Units: scores and thresholds are raw fractions. The M1 threshold of "20
percentage points" is 0.20 here; `points()` converts for reporting.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import NormalDist

__all__ = [
    "MIN_PAIRED_N",
    "Interval",
    "MarginVerdict",
    "points",
    "paired_difference",
    "mcnemar_exact",
    "wilson_interval",
    "judge_margin",
]

#: The pre-registered floor from the margins document. Below this a 20-point
#: gap sits inside ordinary sampling noise, so the criterion proves nothing.
MIN_PAIRED_N = 100


class StatsError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def points(fraction: float) -> float:
    """Fraction -> percentage points, for reporting only."""
    return fraction * 100.0


@dataclass(frozen=True)
class Interval:
    point: float
    low: float
    high: float
    confidence: float
    n: int

    def summary(self) -> str:
        return (
            f"{points(self.point):+.1f}pp "
            f"[{points(self.low):+.1f}, {points(self.high):+.1f}] "
            f"({self.confidence:.0%}, n={self.n})"
        )


def _aligned(board, baseline) -> list[float]:
    """Per-item differences, with alignment enforced rather than assumed.

    A silent length mismatch between arms is the kind of bug that produces a
    plausible number instead of an error, so it raises.
    """
    b = [float(x) for x in board]
    c = [float(x) for x in baseline]
    if len(b) != len(c):
        raise StatsError(
            "E-STAT-001", f"arms are not aligned: {len(b)} board vs {len(c)} baseline"
        )
    if not b:
        raise StatsError("E-STAT-002", "no items to compare")
    return [x - y for x, y in zip(b, c)]


def paired_difference(board, baseline, *, confidence: float = 0.95,
                      iterations: int = 10000, seed: int = 20260827) -> Interval:
    """Bootstrap CI on the mean paired difference (board - baseline).

    Resampling is over *items*, so the pairing is preserved in every resample —
    that is what makes this the paired interval rather than two independent
    ones. Percentile method; the seed is explicit so a reported interval can be
    reproduced exactly from the pre-registration.
    """
    if not 0.0 < confidence < 1.0:
        raise StatsError("E-STAT-003", "confidence must be strictly between 0 and 1")
    if iterations < 1000:
        raise StatsError(
            "E-STAT-004", "iterations must be >= 1000; a coarse bootstrap has coarse tails"
        )

    diffs = _aligned(board, baseline)
    n = len(diffs)
    observed = sum(diffs) / n

    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(iterations):
        total = 0.0
        for _ in range(n):
            total += diffs[rng.randrange(n)]
        means.append(total / n)
    means.sort()

    alpha = (1.0 - confidence) / 2.0
    lo = means[max(0, math.floor(alpha * iterations) - 1)]
    hi = means[min(iterations - 1, math.ceil((1.0 - alpha) * iterations) - 1)]
    return Interval(observed, lo, hi, confidence, n)


def mcnemar_exact(board, baseline) -> tuple[int, int, float]:
    """Exact McNemar test for paired binary outcomes.

    Returns (b, c, two-sided p) where b = board right / baseline wrong and
    c = board wrong / baseline right. Concordant items carry no information
    about which arm is better and are excluded by construction, which is why
    this is more sensitive than comparing two independent proportions.

    Offered as the pre-registerable primary test for the binary criteria; the
    bootstrap interval above remains what the margin threshold is judged on.
    """
    b_scores = [bool(x) for x in board]
    c_scores = [bool(x) for x in baseline]
    if len(b_scores) != len(c_scores):
        raise StatsError(
            "E-STAT-001",
            f"arms are not aligned: {len(b_scores)} board vs {len(c_scores)} baseline",
        )
    b = sum(1 for x, y in zip(b_scores, c_scores) if x and not y)
    c = sum(1 for x, y in zip(b_scores, c_scores) if y and not x)
    n = b + c
    if n == 0:
        return 0, 0, 1.0

    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return b, c, min(1.0, 2.0 * tail)


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> Interval:
    """Wilson score interval for a single proportion.

    For reporting each arm's own rate. Wilson rather than normal-approximation
    because these rates sit near 0 and 1 often enough that the naive interval
    runs outside [0, 1] and stops meaning anything.
    """
    if n < 1:
        raise StatsError("E-STAT-005", "n must be >= 1")
    if not 0 <= successes <= n:
        raise StatsError("E-STAT-006", f"successes {successes} outside 0..{n}")
    if not 0.0 < confidence < 1.0:
        raise StatsError("E-STAT-003", "confidence must be strictly between 0 and 1")

    z = NormalDist().inv_cdf(1.0 - (1.0 - confidence) / 2.0)
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return Interval(p, max(0.0, centre - half), min(1.0, centre + half), confidence, n)


@dataclass(frozen=True)
class MarginVerdict:
    name: str
    threshold: float
    interval: Interval
    sample_ok: bool

    @property
    def cleared(self) -> bool:
        """P4: judged on the lower bound, never the point estimate."""
        return self.sample_ok and self.interval.low >= self.threshold

    def summary(self) -> str:
        verdict = "CLEARED" if self.cleared else "NOT CLEARED"
        note = "" if self.sample_ok else f" [n < {MIN_PAIRED_N}: criterion void]"
        return (
            f"{self.name}: {verdict} — need lower bound >= {points(self.threshold):+.1f}pp, "
            f"got {self.interval.summary()}{note}"
        )


def judge_margin(name: str, board, baseline, threshold: float, *,
                 confidence: float = 0.95, iterations: int = 10000,
                 seed: int = 20260827, min_n: int = MIN_PAIRED_N) -> MarginVerdict:
    """Score one margin criterion end to end.

    An undersized sample does not fail the criterion — it *voids* it. Reporting
    "not cleared" for a run that was too small to say anything would read as
    evidence against the architecture when it is evidence of nothing.
    """
    interval = paired_difference(
        board, baseline, confidence=confidence, iterations=iterations, seed=seed
    )
    return MarginVerdict(name, threshold, interval, interval.n >= min_n)
