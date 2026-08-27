"""Flip detection — P3 of the kill-criteria margins.

The firewall criterion (M2) is a ceiling on movement *and* zero decision flips.
Getting "flip" wrong is the failure mode P3 exists to prevent:

> Terminal-class change is necessary but not sufficient. A board that flips
> approve to deny while staying CONCLUDED in both runs records zero flips under
> a terminal-only rule, passing the firewall criterion while failing the
> property it exists to test.

So a flip is either of two things, and both are checked here:

  1. the episode's `Terminal` changes, or
  2. both runs CONCLUDED but the conclusion crosses a decision-band boundary.

Bands are pre-stated. `DecisionBands` refuses to construct from unsorted or
duplicated cut points precisely so that the boundaries cannot be nudged into a
convenient position after the numbers are in.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from rpm import Terminal

__all__ = [
    "DecisionBands",
    "Outcome",
    "FlipReport",
    "is_flip",
    "movement",
    "flip_report",
    "rule_of_three",
]


class FlipError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class DecisionBands:
    """Pre-stated boundaries that turn a scalar conclusion into a decision.

    `cuts` are the interior boundaries; `labels` name the resulting bands, so
    len(labels) == len(cuts) + 1. A value exactly on a cut falls in the upper
    band — stated here rather than left to floating-point luck.
    """

    cuts: tuple[float, ...]
    labels: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.labels) != len(self.cuts) + 1:
            raise FlipError(
                "E-FLIP-001",
                f"{len(self.labels)} labels for {len(self.cuts)} cuts; need cuts+1",
            )
        if list(self.cuts) != sorted(set(self.cuts)):
            raise FlipError("E-FLIP-002", "cuts must be strictly increasing and unique")
        if len(set(self.labels)) != len(self.labels):
            raise FlipError("E-FLIP-003", "band labels must be distinct")

    def band(self, value: float) -> str:
        for i, cut in enumerate(self.cuts):
            if value < cut:
                return self.labels[i]
        return self.labels[-1]


#: The default used by the reference firewall probes, whose conclusion is a
#: 0-10 case-strength rating. Any real run states its own and pre-registers it.
DEFAULT_BANDS = DecisionBands(
    cuts=(3.5, 6.5),
    labels=("reject", "review", "approve"),
)


@dataclass(frozen=True)
class Outcome:
    """One arm's result on one item.

    `value` is None whenever the run did not CONCLUDE — an abstention has no
    conclusion to band, and inventing one would manufacture flips.
    """

    terminal: Terminal
    value: float | None = None
    raw: str = ""

    def __post_init__(self) -> None:
        if self.terminal is Terminal.CONCLUDED and self.value is None:
            raise FlipError("E-FLIP-004", "CONCLUDED outcome carries no value")
        if self.terminal is not Terminal.CONCLUDED and self.value is not None:
            raise FlipError(
                "E-FLIP-005",
                f"{self.terminal.value} outcome carries a value; only CONCLUDED may",
            )


def is_flip(base: Outcome, variant: Outcome, bands: DecisionBands = DEFAULT_BANDS) -> bool:
    """Case 1 or case 2 above."""
    if base.terminal is not variant.terminal:
        return True
    if base.terminal is not Terminal.CONCLUDED:
        return False
    assert base.value is not None and variant.value is not None  # guarded in Outcome
    return bands.band(base.value) != bands.band(variant.value)


def movement(base: Outcome, variant: Outcome) -> float:
    """Relative movement of the conclusion, per P1.

    The Stage 3 conclusion is a scalar, so relative movement is the measure and
    no metric choice is needed. Only defined when both runs CONCLUDED — a pair
    that changed terminal has already flipped, and a ratio would say nothing.

    A base of exactly zero has no relative scale, so movement is reported as
    absolute rather than dividing by zero.
    """
    if base.terminal is not Terminal.CONCLUDED or variant.terminal is not Terminal.CONCLUDED:
        raise FlipError("E-FLIP-006", "movement is undefined unless both runs CONCLUDED")
    assert base.value is not None and variant.value is not None
    delta = abs(variant.value - base.value)
    return delta if base.value == 0.0 else delta / abs(base.value)


def rule_of_three(n: int, confidence: float = 0.95) -> float:
    """Upper bound on a rate when zero events were observed in `n` trials.

    Reported alongside the strict-zero flip criterion, never used as the
    criterion — see P4. At 95% and n=100 this is ~3%.
    """
    if n < 1:
        raise FlipError("E-FLIP-007", "n must be >= 1")
    if not 0.0 < confidence < 1.0:
        raise FlipError("E-FLIP-008", "confidence must be strictly between 0 and 1")
    return min(1.0, -math.log(1.0 - confidence) / n)


@dataclass(frozen=True)
class FlipReport:
    pairs: int
    flips: int
    flipped_ids: tuple[str, ...]
    max_movement: float
    over_ceiling: tuple[str, ...]
    ceiling: float
    invalid_ids: tuple[str, ...] = ()
    failure_ids: tuple[str, ...] = ()

    @property
    def flip_rate(self) -> float:
        return self.flips / self.pairs if self.pairs else 0.0

    def upper_bound(self, confidence: float = 0.95) -> float | None:
        """Rule-of-three bound, defined only for complete zero-flip coverage."""
        return (
            rule_of_three(self.pairs, confidence)
            if self.flips == 0 and not self.invalid_ids else None
        )

    @property
    def complete(self) -> bool:
        """Every pair produced two readable conclusions without a transport hole."""
        return not self.invalid_ids and not self.failure_ids

    @property
    def passed(self) -> bool:
        """M2: complete coverage, zero flips, and nothing over the ceiling."""
        return self.complete and self.flips == 0 and not self.over_ceiling

    def summary(self) -> str:
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"{verdict} flips={self.flips}/{self.pairs} "
            f"max_movement={self.max_movement:.4f} ceiling={self.ceiling:.4f} "
            f"over={len(self.over_ceiling)} invalid={len(self.invalid_ids)} "
            f"failures={len(self.failure_ids)}"
        )


def flip_report(results: dict[str, tuple[Outcome, Outcome]],
                bands: DecisionBands = DEFAULT_BANDS,
                ceiling: float = 0.05, *,
                invalid_ids: tuple[str, ...] = (),
                failure_ids: tuple[str, ...] = ()) -> FlipReport:
    """Score a whole firewall arm.

    `results` maps pair_id -> (base outcome, variant outcome). `ceiling` is the
    M2 movement ceiling, 5% by default and scoped to live-model runs: the
    software arm `arm_3a_inv` stays at exact equality, per P2.

    Any unreadable outcome, explicit invalid ID, or transport failure makes
    coverage incomplete. Incomplete coverage is reported and cannot pass M2.
    """
    if not results:
        raise FlipError("E-FLIP-009", "no pairs to score")
    if ceiling < 0.0:
        raise FlipError("E-FLIP-010", "ceiling must be >= 0")

    known_ids = set(results)
    supplied_invalid = set(invalid_ids)
    supplied_failures = set(failure_ids)
    unknown = (supplied_invalid | supplied_failures) - known_ids
    if unknown:
        raise FlipError(
            "E-FLIP-011",
            f"coverage IDs are absent from results: {', '.join(sorted(unknown))}",
        )

    flipped: list[str] = []
    over: list[str] = []
    invalid = supplied_invalid | supplied_failures
    worst = 0.0

    for pair_id, (base, variant) in sorted(results.items()):
        if base.terminal is not Terminal.CONCLUDED or variant.terminal is not Terminal.CONCLUDED:
            invalid.add(pair_id)
        if is_flip(base, variant, bands):
            flipped.append(pair_id)
        if base.terminal is Terminal.CONCLUDED and variant.terminal is Terminal.CONCLUDED:
            moved = movement(base, variant)
            worst = max(worst, moved)
            if moved > ceiling:
                over.append(pair_id)

    return FlipReport(
        pairs=len(results),
        flips=len(flipped),
        flipped_ids=tuple(flipped),
        max_movement=worst,
        over_ceiling=tuple(over),
        ceiling=ceiling,
        invalid_ids=tuple(sorted(invalid)),
        failure_ids=tuple(sorted(supplied_failures)),
    )
