"""RPM planner — Recursive Prerequisite Mechanism.

Semantics from CAS_Ohm_Quantification_Guide p.15 ("RPM as a cognitive
troubleshooting circuit"):

    1. Define   name the Prime Desire and target Foundation
    2. Scan     assess D, W, P with card phase, decimal score, and trend
    3. Recurse  the first insufficient state becomes the next goal
    4. Act and ascend   execute a Noetic action, re-measure, return to parent

and from CAS PCBA Engineer, the chain and its one-directionality:

    "A0 -> Dn -> Wn -> Pn -> Outcome, each stage requiring the one before it"
    "(section-retraction) - Prerequisite satisfaction structured as a
     one-directional chain"

CORRECTION 2 (CLAUDE.md) is enforced here, not assumed: the RPM gate must NOT
assume reversibility, and initial satisfaction results are cached. Once a
prerequisite has been observed sufficient it stays sufficient for the episode —
re-measurement can only ever *raise* a prerequisite, never silently retract one.
Genuine capability loss is representable, but only through an explicit
`retract()` call that is recorded, never as a side effect of re-measuring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Prereq(str, Enum):
    """The RPM triad. Order is the scan order and is load-bearing."""

    D = "D"  # Desire   — do I genuinely want this outcome?
    W = "W"  # Wisdom   — do I know what is required and what is true?
    P = "P"  # Power    — do I have the capability and resources?


SCAN_ORDER: tuple[Prereq, ...] = (Prereq.D, Prereq.W, Prereq.P)


class Terminal(str, Enum):
    """How a reasoning episode ends.

    The audited artifact defined four terminal states and had no exit for a
    Desire block — a gap the audit recorded. NEEDS_DESIRE closes it, so every
    first-block outcome has a corresponding terminal.
    """

    CONCLUDED = "CONCLUDED"
    NEEDS_DESIRE = "NEEDS_DESIRE"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    NEEDS_CAPABILITY = "NEEDS_CAPABILITY"
    INADMISSIBLE = "INADMISSIBLE"
    NONTERMINATING = "NONTERMINATING"


BLOCK_TERMINAL = {
    Prereq.D: Terminal.NEEDS_DESIRE,
    Prereq.W: Terminal.NEEDS_INFORMATION,
    Prereq.P: Terminal.NEEDS_CAPABILITY,
}

# Guide p.15: "strong Desire, at least Understanding-level Wisdom, and mature
# Power as the reference condition" for stable manifestation.
DEFAULT_SUFFICIENCY = 5.0


class RpmError(RuntimeError):
    pass


@dataclass
class PrereqState:
    score: float
    threshold: float = DEFAULT_SUFFICIENCY
    #: Correction 2 — once observed sufficient, cached sufficient for the episode.
    _cached_sufficient: bool = field(default=False, repr=False)

    def sufficient(self) -> bool:
        if self._cached_sufficient:
            return True
        if self.score >= self.threshold:
            self._cached_sufficient = True
        return self._cached_sufficient


@dataclass
class Goal:
    """One node of the Desire Tree."""

    name: str
    d: PrereqState
    w: PrereqState
    p: PrereqState

    def state(self, prereq: Prereq) -> PrereqState:
        return {Prereq.D: self.d, Prereq.W: self.w, Prereq.P: self.p}[prereq]

    def first_block(self) -> Prereq | None:
        """"The first insufficient state becomes the next goal." Guide p.15.

        Scans in D, W, P order and short-circuits, matching the monadic
        short-circuit the chain describes. Returns None when all three hold.
        """
        for prereq in SCAN_ORDER:
            if not self.state(prereq).sufficient():
                return prereq
        return None


@dataclass
class ScanRecord:
    depth: int
    goal: str
    block: Prereq | None
    scores: dict[str, float]
    note: str = ""


@dataclass
class RpmResult:
    terminal: Terminal
    trace: list[ScanRecord]
    resolved: list[str]
    depth_reached: int

    @property
    def concluded(self) -> bool:
        return self.terminal is Terminal.CONCLUDED


class RpmPlanner:
    """Recursive first-unmet-prerequisite descent with a hard depth bound.

    The audit found the artifact's RPM had no depth or progress bound, so an
    infinite sub-goal regress was representable. `max_depth` closes that: the
    descent terminates in NONTERMINATING rather than running away, which is a
    reportable outcome instead of a hang.
    """

    def __init__(self, max_depth: int = 8) -> None:
        if max_depth < 1:
            raise ValueError("max_depth must be >= 1")
        self.max_depth = max_depth

    def run(
        self,
        root: Goal,
        subgoals: dict[tuple[str, Prereq], Goal] | None = None,
        *,
        admissible: bool = True,
    ) -> RpmResult:
        """Descend from `root`, resolving the first block at each level.

        `subgoals` maps (goal name, blocked prerequisite) to the sub-goal that
        acquiring it requires. A block with no registered sub-goal is a genuine
        stopping point and yields that prerequisite's terminal state.
        """
        if not admissible:
            return RpmResult(Terminal.INADMISSIBLE, [], [], 0)

        subgoals = subgoals or {}
        trace: list[ScanRecord] = []
        resolved: list[str] = []
        stack: list[Goal] = [root]
        seen: set[str] = set()

        while stack:
            depth = len(stack) - 1
            goal = stack[-1]

            if depth >= self.max_depth:
                trace.append(
                    ScanRecord(depth, goal.name, None, self._scores(goal), "depth bound reached")
                )
                return RpmResult(Terminal.NONTERMINATING, trace, resolved, depth)

            block = goal.first_block()
            trace.append(ScanRecord(depth, goal.name, block, self._scores(goal)))

            if block is None:
                # This goal is satisfied; ascend and credit the parent's prereq.
                stack.pop()
                resolved.append(goal.name)
                if stack:
                    parent = stack[-1]
                    parent_block = parent.first_block()
                    if parent_block is not None:
                        # "act -> re-measure -> ascend": the sub-goal's success
                        # raises the parent prerequisite that sent us down.
                        parent.state(parent_block)._cached_sufficient = True
                continue

            key = (goal.name, block)
            child = subgoals.get(key)
            if child is None:
                return RpmResult(BLOCK_TERMINAL[block], trace, resolved, depth)

            if child.name in seen:
                trace.append(
                    ScanRecord(depth, child.name, None, self._scores(child), "cycle detected")
                )
                return RpmResult(Terminal.NONTERMINATING, trace, resolved, depth)
            seen.add(child.name)
            stack.append(child)

        return RpmResult(Terminal.CONCLUDED, trace, resolved, 0)

    @staticmethod
    def _scores(goal: Goal) -> dict[str, float]:
        return {"D": goal.d.score, "W": goal.w.score, "P": goal.p.score}


def retract(state: PrereqState, new_score: float) -> None:
    """Explicitly lower a prerequisite, clearing its cached sufficiency.

    Correction 2 makes satisfaction one-directional, so nothing may quietly
    un-satisfy a prerequisite. Genuine capability loss is still real, so it gets
    an explicit, auditable call rather than being folded into re-measurement.
    """
    state.score = new_score
    state._cached_sufficient = False
