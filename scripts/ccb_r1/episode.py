"""Reasoning episode controller — the board running end to end.

Brings the pieces together under the two rules the audit found the original
netlist violating:

  Domain descent   every stage transition must not ascend P > C > E > O.
  Bias firewall    "Ambition may choose the question. It must not choose the
                   answer." A goal-derived bias outside the Principled domain
                   may not sit on an evaluation or inference stage.

Both are enforced structurally, and both are measurable: `run_episode` reports
which rule stopped it. Every episode terminates in exactly one Terminal state —
the stop gate against rumination that the audited design called for but never
bounded.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cjt_sim import CjtSpec, Region, Scale, measure
from cmb import CognitiveMemoryBoard
from rpm import Goal, RpmPlanner, Terminal

DOMAIN_RANK = {"P": 0, "C": 1, "E": 2, "O": 3}
GOAL_DERIVED_DRIVES = {5, 7}
FIREWALLED = ("analyze", "evaluate", "infer", "conclude", "judge", "compare")


@dataclass(frozen=True)
class Stage:
    label: str
    domain: str
    bias_domain: str
    bias_drive: int
    spec: CjtSpec
    v: float
    r_total: float


@dataclass
class EpisodeResult:
    terminal: Terminal
    stages_run: list[str] = field(default_factory=list)
    regions: dict[str, Region] = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)
    ticks: int = 0
    lacunae_hit: tuple[str, ...] = ()

    @property
    def concluded(self) -> bool:
        return self.terminal is Terminal.CONCLUDED


def check_descent(stages: list[Stage]) -> list[str]:
    """Every consecutive transition must not ascend the precedence order."""
    problems: list[str] = []
    for prev, nxt in zip(stages, stages[1:]):
        if DOMAIN_RANK[nxt.domain] < DOMAIN_RANK[prev.domain]:
            problems.append(
                f"W-axis: {prev.label}->{nxt.label} ascends {prev.domain}->{nxt.domain}"
            )
    return problems


def check_firewall(stages: list[Stage]) -> list[str]:
    """No goal-derived bias outside the Principled domain on a judging stage.

    A Principled-domain bias carrying F7 Purpose is a charter — the legitimate
    governor of evaluation. The distinction is the domain coordinate, not the
    drive; keying on drive alone produces false positives.
    """
    problems: list[str] = []
    for stage in stages:
        if not any(tag in stage.label.lower() for tag in FIREWALLED):
            continue
        if stage.bias_drive in GOAL_DERIVED_DRIVES and stage.bias_domain != "P":
            problems.append(
                f"firewall: {stage.label} biased by F{stage.bias_drive} "
                f"in {stage.bias_domain}-domain; ambition must not choose the answer"
            )
    return problems


def run_episode(
    stages: list[Stage],
    *,
    memory: CognitiveMemoryBoard | None = None,
    required_recall: tuple[str, ...] = (),
    goal: Goal | None = None,
    subgoals: dict | None = None,
    admissible: bool = True,
    max_ticks: int = 64,
) -> EpisodeResult:
    """Run one reasoning episode to exactly one terminal state."""
    result = EpisodeResult(terminal=Terminal.CONCLUDED)

    if not admissible:
        result.terminal = Terminal.INADMISSIBLE
        return result

    structural = check_descent(stages) + check_firewall(stages)
    if structural:
        result.violations = structural
        result.terminal = Terminal.INADMISSIBLE
        return result

    # A lacuna is a typed prerequisite failure, not an invitation to guess.
    if memory is not None and required_recall:
        empty = tuple(k for k in required_recall if memory.recall(k).is_lacuna)
        if empty:
            result.lacunae_hit = empty
            result.terminal = Terminal.NEEDS_INFORMATION
            return result

    if goal is not None:
        rpm = RpmPlanner()
        rpm_result = rpm.run(goal, subgoals or {})
        if rpm_result.terminal is not Terminal.CONCLUDED:
            result.terminal = rpm_result.terminal
            result.ticks = len(rpm_result.trace)
            return result
        result.ticks += len(rpm_result.trace)

    for stage in stages:
        if result.ticks >= max_ticks:
            result.terminal = Terminal.NONTERMINATING
            return result
        result.ticks += 1
        reading = measure(stage.spec, v=stage.v, r_total=stage.r_total)
        result.stages_run.append(stage.label)
        result.regions[stage.label] = reading.region
        if reading.region is Region.CUTOFF:
            # A silent stage produces no effect; the episode cannot conclude.
            result.terminal = Terminal.NEEDS_CAPABILITY
            result.violations.append(f"{stage.label} is in cutoff and never fires")
            return result

    return result


def linear_board(scale: Scale = Scale.DESIGN) -> list[Stage]:
    """A conformant reference board: C -> E -> E -> O, charter-biased throughout."""

    def spec(label: str, beta: float) -> CjtSpec:
        return CjtSpec(
            label=label, beta=beta, cutoff=0.0, sat=100.0, bias="charter", scale=scale
        )

    return [
        Stage("intake", "C", "C", 2, spec("intake", 1.6), 6.0, 3.0),
        Stage("analyze", "E", "P", 7, spec("analyze", 1.0), 5.0, 5.0),
        Stage("infer", "E", "P", 7, spec("infer", 1.0), 4.0, 2.0),
        Stage("commit", "O", "P", 7, spec("commit", 2.4), 4.0, 2.0),
    ]
