"""Baselines B0-B2 — controls without which green stages say nothing.

The test-program review's first correction: every drafted stage asked "does
CCB-R1 do what CCB-R1 says", and none asked "does the structure buy anything".
Green across Stages 0-4 without controls is a statement about internal
consistency, not about reasoning.

  B0  ^8-only associative chain    the artifact's own named control. Must FAIL
                                   deduction tasks; if it passes, the task does
                                   not test deduction.
  B1  no-bias ablation             must fail to construct, not silently answer.
  B2  random-bias control          quantifies how much behaviour is structure
                                   rather than accident.

B3 (unstructured LLM) needs a model and belongs to Stage 5. It is the only
baseline that answers "what does the architecture add", and its absence is
stated rather than papered over.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from cjt_sim import CjtError, CjtSpec
from episode import Stage, linear_board, run_episode
from rpm import Terminal


@dataclass
class BaselineResult:
    name: str
    concluded: bool
    detail: str


# ---- B0: association is not deduction --------------------------------------

@dataclass(frozen=True)
class Syllogism:
    """A -> B, B -> C, therefore A -> C."""

    premises: tuple[tuple[str, str], ...]
    query: tuple[str, str]

    def entailed(self) -> bool:
        """Transitive closure — the ground truth."""
        edges: dict[str, set[str]] = {}
        for a, b in self.premises:
            edges.setdefault(a, set()).add(b)
        seen, stack = set(), [self.query[0]]
        while stack:
            node = stack.pop()
            for nxt in edges.get(node, ()):
                if nxt == self.query[1]:
                    return True
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return False


def b0_association_only(task: Syllogism) -> bool:
    """^8 alone: surface what is directly adjacent, never compose.

    "^8 Above/Cause is not deduction. It is associative triggering." A board
    built from repeated ^8 transitions can answer one-hop questions and cannot
    chain, so it must fail transitive tasks it has no ^6/^9 middle to solve.
    """
    direct = {(a, b) for a, b in task.premises}
    return task.query in direct


def b0_full_reasoner(task: Syllogism) -> bool:
    """^6 decomposition + ^9 landing: composes the chain."""
    return task.entailed()


# ---- B1: there is no bias-free CJT -----------------------------------------

def b1_no_bias() -> BaselineResult:
    """Removing the bias must be a construction error, not a wrong answer."""
    try:
        CjtSpec(label="unbiased", beta=1.0, cutoff=0.0, sat=1.0, bias=None)
    except CjtError as exc:
        return BaselineResult("B1", False, f"refused at construction: {exc.code}")
    return BaselineResult("B1", True, "constructed a bias-free CJT — the ablation failed")


# ---- B2: how much is structure, how much is accident? ----------------------

def b2_random_bias(trials: int = 200, seed: int = 20260827) -> BaselineResult:
    """Same board, biases drawn at random per run.

    A structurally sound board concludes because its topology is sound. If a
    randomly-biased board concludes just as often, the topology is not doing the
    work — the result is accident.
    """
    rng = random.Random(seed)
    concluded = 0
    for _ in range(trials):
        stages = linear_board()
        randomized: list[Stage] = []
        for s in stages:
            drive = rng.choice([1, 2, 3, 4, 5, 6, 7])
            domain = rng.choice(["P", "C", "E", "O"])
            randomized.append(Stage(s.label, s.domain, domain, drive, s.spec, s.v, s.r_total))
        if run_episode(randomized).terminal is Terminal.CONCLUDED:
            concluded += 1
    rate = concluded / trials
    return BaselineResult("B2", rate > 0.0, f"random-bias conclude rate {rate:.2%}")


def reference_conclude_rate() -> float:
    """The structured board's rate, for comparison against B2."""
    return 1.0 if run_episode(linear_board()).terminal is Terminal.CONCLUDED else 0.0
