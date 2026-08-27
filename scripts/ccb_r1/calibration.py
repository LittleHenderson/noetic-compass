"""The M3 calibration gate — P5 of the kill-criteria margins.

M3 asks CCB-R1 to beat the unstructured baseline by 10 percentage points on
deduction. That criterion is untestable if the baseline is near ceiling: at 94%
a +10 margin is arithmetically impossible and M3 fails for reasons that have
nothing to do with the architecture. So the task set is calibrated first:

> B3 must score between 40% and 70% on the deduction task set. If it scores
> outside that band, the task set is rejected and rebuilt — the run does not
> count either way.

P5 constrains how that rebuild may happen:

> **Bounded:** at most 3 rebuild attempts. **Blind:** each rebuilt set is
> produced by a generation procedure stated *before the first attempt*, not
> assembled by hand between attempts. Only B3 runs during calibration —
> CCB-R1 never touches a candidate set before that set is accepted.

Both are enforced structurally rather than by discipline:

* `GenerationProcedure` holds the *entire* schedule of difficulty settings and
  seeds, is frozen, and fingerprints itself. Attempt 2's parameters are fixed
  before attempt 1 runs, so there is nothing to tune in between.
* `calibrate()` takes exactly one runner — the baseline. There is no parameter
  through which a board could be passed, so "CCB-R1 never touches a candidate
  set" is a property of the signature, not a promise.

One addition beyond the written gate. A baseline sitting at chance also lands
inside 40-70% on a balanced set, and beating a coin-flipper by 10 points says
nothing about deduction. So an accepted set must *also* show the baseline
significantly above chance. Without that check the band admits exactly the
uninformative case it was meant to exclude — which matters here, because small
base models like GPT-2 and Pythia-160M score at chance on multi-hop entailment
and would otherwise calibrate as "usefully hard".
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable

from stats import Interval, wilson_interval
from tasksets import DeductionItem, Difficulty, TaskSet, generate_deduction_set

__all__ = [
    "MAX_ATTEMPTS",
    "GenerationProcedure",
    "Attempt",
    "CalibrationResult",
    "calibrate",
    "default_procedure",
]

#: P5's bound. Past this the run is abandoned rather than re-rolled — an
#: unbounded loop is a way to fish for a set that gives the answer you want.
MAX_ATTEMPTS = 3

#: A baseline scorer: given one item, did it answer correctly?
BaselineScorer = Callable[[DeductionItem], bool]


class CalibrationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class GenerationProcedure:
    """The whole schedule, stated before the first attempt.

    `schedule` is (difficulty, seed) per attempt, in order. Declaring it up
    front is what makes the rebuild blind: there is no point at which a human
    chooses the next set having seen the last one's score.
    """

    name: str
    n: int
    schedule: tuple[tuple[Difficulty, int], ...]
    band: tuple[float, float] = (0.40, 0.70)
    chance: float = 0.5
    confidence: float = 0.95

    def __post_init__(self) -> None:
        if not self.schedule:
            raise CalibrationError("E-CAL-001", "schedule is empty")
        if len(self.schedule) > MAX_ATTEMPTS:
            raise CalibrationError(
                "E-CAL-002",
                f"{len(self.schedule)} attempts exceeds the P5 bound of {MAX_ATTEMPTS}",
            )
        lo, hi = self.band
        if not 0.0 < lo < hi < 1.0:
            raise CalibrationError("E-CAL-003", f"band {self.band} is not 0 < lo < hi < 1")
        if not 0.0 < self.chance < 1.0:
            raise CalibrationError("E-CAL-004", "chance must be strictly between 0 and 1")
        if self.chance >= hi:
            raise CalibrationError(
                "E-CAL-005",
                f"chance {self.chance} is at or above the band ceiling {hi}; "
                "no set could be both above chance and inside the band",
            )
        if self.n < 1:
            raise CalibrationError("E-CAL-006", "n must be >= 1")
        seeds = [s for _, s in self.schedule]
        if len(set(seeds)) != len(seeds):
            raise CalibrationError(
                "E-CAL-007",
                "attempts repeat a seed; a rebuild that regenerates the same set "
                "is not a rebuild",
            )

    def fingerprint(self) -> str:
        blob = json.dumps(
            {
                "name": self.name,
                "n": self.n,
                "schedule": [
                    {"hops": d.hops, "distractors": d.distractors,
                     "entailed_fraction": d.entailed_fraction, "seed": s}
                    for d, s in self.schedule
                ],
                "band": list(self.band),
                "chance": self.chance,
                "confidence": self.confidence,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def build(self, attempt: int) -> TaskSet:
        difficulty, seed = self.schedule[attempt]
        return generate_deduction_set(
            self.n, seed, difficulty, name=f"{self.name}-a{attempt + 1}"
        )


@dataclass(frozen=True)
class Attempt:
    index: int
    difficulty: Difficulty
    seed: int
    task_fingerprint: str
    correct: int
    n: int
    interval: Interval
    verdict: str

    @property
    def rate(self) -> float:
        return self.correct / self.n

    def summary(self) -> str:
        return (
            f"attempt {self.index + 1} [{self.difficulty.label()}] "
            f"{self.rate:.1%} {self.interval.summary()} -> {self.verdict}"
        )


@dataclass(frozen=True)
class CalibrationResult:
    procedure_fingerprint: str
    attempts: tuple[Attempt, ...]
    accepted: TaskSet | None

    @property
    def ok(self) -> bool:
        return self.accepted is not None

    @property
    def status(self) -> str:
        return self.attempts[-1].verdict if self.attempts else "NOT_RUN"

    def summary(self) -> str:
        head = "ACCEPTED" if self.ok else "ABANDONED"
        lines = [f"{head} after {len(self.attempts)} attempt(s)"]
        lines += ["  " + a.summary() for a in self.attempts]
        if self.ok:
            assert self.accepted is not None
            lines.append(f"  task set fingerprint {self.accepted.fingerprint()}")
        return "\n".join(lines)


def _verdict(correct: int, n: int, proc: GenerationProcedure) -> tuple[str, Interval]:
    interval = wilson_interval(correct, n, proc.confidence)
    lo, hi = proc.band
    rate = correct / n
    # Band first, so a floored or ceilinged baseline reports the actionable
    # diagnosis. A 0% baseline is not "at chance" — it is below it, and the
    # remedy is an easier set, which is what TOO_HARD says.
    if rate > hi:
        return "TOO_EASY", interval
    if rate < lo:
        return "TOO_HARD", interval
    if interval.low <= proc.chance:
        # Inside the band and still indistinguishable from guessing. A margin
        # over a coin-flipper measures nothing, so the band alone is not
        # enough to accept.
        return "AT_CHANCE", interval
    return "ACCEPTED", interval


def calibrate(procedure: GenerationProcedure, baseline: BaselineScorer) -> CalibrationResult:
    """Run the gate. Baseline only — there is no board parameter by design.

    Stops at the first accepted set. Otherwise walks the pre-stated schedule to
    its end and abandons; it never invents a fourth attempt.
    """
    attempts: list[Attempt] = []

    for index in range(len(procedure.schedule)):
        difficulty, seed = procedure.schedule[index]
        task_set = procedure.build(index)
        correct = sum(1 for item in task_set.items if baseline(item))
        verdict, interval = _verdict(correct, len(task_set), procedure)

        attempts.append(
            Attempt(
                index=index,
                difficulty=difficulty,
                seed=seed,
                task_fingerprint=task_set.fingerprint(),
                correct=correct,
                n=len(task_set),
                interval=interval,
                verdict=verdict,
            )
        )
        if verdict == "ACCEPTED":
            return CalibrationResult(procedure.fingerprint(), tuple(attempts), task_set)

    return CalibrationResult(procedure.fingerprint(), tuple(attempts), None)


def default_procedure(name: str = "deduction", n: int = 120) -> GenerationProcedure:
    """A three-attempt schedule that walks difficulty upward.

    Ordered easy-to-hard on purpose: a run that accepts at attempt 1 has used
    the gentlest set that still discriminates, which keeps the margin honest
    rather than inflated by a set the baseline cannot engage with at all.
    """
    return GenerationProcedure(
        name=name,
        n=n,
        schedule=(
            (Difficulty(hops=3, distractors=4), 20260827),
            (Difficulty(hops=4, distractors=6), 20260828),
            (Difficulty(hops=5, distractors=8), 20260829),
        ),
    )
