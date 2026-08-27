"""Stage 2 — fault injection, mapped to the shipped 7-axis inversion scanner.

The review's correction to the drafted Stage 2: "stage-localization accuracy" is
underspecified without a denominator and a false-positive arm. A scanner that
always reports "stage 3" scores well on stage-3 injections. So this module
reports a confusion matrix over (injected x detected), scores axis mapping
separately from stage localization, and includes an unfaulted control arm.

Axes are CLAUDE.md's, not invented here:
  N operator/noetic involution imbalance      W domain precedence violation
  F drive pair imbalance                      E state-vector entropy deficit
  S sub-drive cross-domain variance           A pathway RPM chain violation
  P compound (multiple axes at once)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum

from cjt_sim import CjtSpec
from episode import Stage, check_descent, check_firewall, run_episode
from rpm import Goal, PrereqState, RpmPlanner, Terminal


class Axis(str, Enum):
    N = "N"
    W = "W"
    F = "F"
    E = "E"
    S = "S"
    A = "A"
    P = "P"
    NONE = "none"


@dataclass(frozen=True)
class Fault:
    name: str
    expected_axis: Axis
    expected_stage: str | None
    apply: object  # Callable[[list[Stage]], list[Stage]]


@dataclass
class Detection:
    axis: Axis
    stage: str | None
    terminal: Terminal
    evidence: tuple[str, ...] = ()


@dataclass
class Scorecard:
    confusion: dict[tuple[str, str], int] = field(default_factory=dict)
    axis_correct: int = 0
    stage_correct: int = 0
    total: int = 0
    false_positives: int = 0
    control_runs: int = 0

    def record(self, expected: Axis, detected: Axis, stage_hit: bool) -> None:
        key = (expected.value, detected.value)
        self.confusion[key] = self.confusion.get(key, 0) + 1
        self.total += 1
        if expected is detected:
            self.axis_correct += 1
        if stage_hit:
            self.stage_correct += 1

    @property
    def axis_accuracy(self) -> float:
        return self.axis_correct / self.total if self.total else 0.0

    @property
    def stage_accuracy(self) -> float:
        return self.stage_correct / self.total if self.total else 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.false_positives / self.control_runs if self.control_runs else 0.0


def _respec(stage: Stage, **kw) -> Stage:
    base = dict(
        label=stage.spec.label,
        beta=stage.spec.beta,
        cutoff=stage.spec.cutoff,
        sat=stage.spec.sat,
        bias=stage.spec.bias,
        scale=stage.spec.scale,
    )
    base.update(kw)
    return Stage(
        stage.label, stage.domain, stage.bias_domain, stage.bias_drive,
        CjtSpec(**base), stage.v, stage.r_total,
    )


# ---- the fault library -----------------------------------------------------

def break_domain_descent(stages: list[Stage]) -> list[Stage]:
    """Make `infer` ascend E -> C. Should trip axis W."""
    out = copy.deepcopy(stages)
    for i, s in enumerate(out):
        if s.label == "infer":
            out[i] = Stage(s.label, "C", s.bias_domain, s.bias_drive, s.spec, s.v, s.r_total)
    return out


def wire_ambition_into_inference(stages: list[Stage]) -> list[Stage]:
    """Bias `infer` with F5 Agency in the Evaluative domain. Trips axis F."""
    out = copy.deepcopy(stages)
    for i, s in enumerate(out):
        if s.label == "infer":
            out[i] = Stage(s.label, s.domain, "E", 5, s.spec, s.v, s.r_total)
    return out


def starve_a_stage(stages: list[Stage]) -> list[Stage]:
    """Push `analyze` under its cutoff floor. Trips axis E (a dead region)."""
    out = copy.deepcopy(stages)
    for i, s in enumerate(out):
        if s.label == "analyze":
            out[i] = _respec(s, cutoff=99.0, sat=100.0)
    return out


def compound_fault(stages: list[Stage]) -> list[Stage]:
    """Descent break plus ambition bias. Trips axis P (compound)."""
    return wire_ambition_into_inference(break_domain_descent(stages))


FAULTS: tuple[Fault, ...] = (
    Fault("break_domain_descent", Axis.W, "infer", break_domain_descent),
    Fault("ambition_into_inference", Axis.F, "infer", wire_ambition_into_inference),
    Fault("starve_analyze", Axis.E, "analyze", starve_a_stage),
    Fault("compound", Axis.P, "infer", compound_fault),
)


# ---- detection -------------------------------------------------------------

def detect(stages: list[Stage]) -> Detection:
    """Localize the failed stage and name its axis.

    Order matters: a compound fault must report P, not whichever single axis
    happens to be checked first.
    """
    descent = check_descent(stages)
    firewall = check_firewall(stages)
    evidence = tuple(descent + firewall)

    if descent and firewall:
        stage = descent[0].split("->")[1].split(" ")[0]
        return Detection(Axis.P, stage, Terminal.INADMISSIBLE, evidence)
    if descent:
        stage = descent[0].split("->")[1].split(" ")[0]
        return Detection(Axis.W, stage, Terminal.INADMISSIBLE, evidence)
    if firewall:
        stage = firewall[0].split(":")[1].strip().split(" ")[0]
        return Detection(Axis.F, stage, Terminal.INADMISSIBLE, evidence)

    result = run_episode(stages)
    if result.terminal is Terminal.NEEDS_CAPABILITY and result.violations:
        stage = result.violations[0].split(" ")[0]
        return Detection(Axis.E, stage, result.terminal, tuple(result.violations))
    if result.terminal is not Terminal.CONCLUDED:
        return Detection(Axis.A, None, result.terminal, tuple(result.violations))
    return Detection(Axis.NONE, None, result.terminal)


def run_suite(reference: list[Stage], *, control_runs: int = 8) -> Scorecard:
    """Inject every fault, then run unfaulted controls to measure silence."""
    card = Scorecard()

    for fault in FAULTS:
        faulted = fault.apply(copy.deepcopy(reference))
        found = detect(faulted)
        card.record(fault.expected_axis, found.axis, found.stage == fault.expected_stage)

    for _ in range(control_runs):
        card.control_runs += 1
        if detect(copy.deepcopy(reference)).axis is not Axis.NONE:
            card.false_positives += 1

    return card


def rpm_chain_fault() -> Goal:
    """An RPM chain that cannot complete: Wisdom is unmet and has no sub-goal.

    Axis A is "Pathway RPM chain violation". This is exercised through
    `detect_rpm` below rather than left as an unwired declaration — the defect
    the audit found in the original netlist was exactly a declared protection
    that nothing invoked.
    """
    return Goal(name="blocked", d=PrereqState(9.0), w=PrereqState(1.0), p=PrereqState(9.0))


def detect_rpm(goal: Goal) -> Detection:
    """Localize an RPM chain failure and map it to axis A."""
    result = RpmPlanner().run(goal)
    if result.terminal is Terminal.CONCLUDED:
        return Detection(Axis.NONE, None, result.terminal)
    blocked = next((r for r in reversed(result.trace) if r.block is not None), None)
    return Detection(
        Axis.A,
        blocked.goal if blocked else None,
        result.terminal,
        (f"RPM chain halted at {blocked.block.value if blocked else '?'}",),
    )
