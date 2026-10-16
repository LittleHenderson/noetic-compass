"""HELM-TKS-RPM-001 - THE single Noetic Council, driven by canonical RPM in a loop.

The loop, verbatim from the owner's directive:

  1. Target outcome          - What is HELM trying to accomplish?
  2. RPM diagnosis           - Determine which required conditions are satisfied, missing,
                               uncertain, or blocking the outcome.
  3. TKS Noetic Council      - The ten Noetic operations collaborate to investigate the
                               identified blocker. Each seat uses its canonical Noetic
                               operation, not an invented definition.
  4. Conditional Element     - Activate relevant TKS 40 Elements when deeper resolution is
     analysis                  needed.
  5. Resolve and verify      - Implement the appropriate operation, test its result, and
                               update the prerequisite state.
  RPM reevaluates the target. If another condition blocks it, the council investigates again.

There is ONE council. The ten members persist across tasks and across loop iterations.
They are not re-created per task and not duplicated per candidate. This module is the
machine that runs them; `target_*.py` modules supply the task.

WHAT THE SEATS ARE, AND WHAT THEY ARE NOT
-----------------------------------------
The seat operations below are the canonical Noetic definitions from the Tootra Math
Handbook (Clarification 1) turned into an instruction, one for one. A seat's operation is
its definition read as a directive and nothing else. Where an anti-drift annotation is
load-bearing it is carried on the seat and enforced by `check_seat_report`.

THE 40 ELEMENTS
---------------
10 Noetics x 4 Worlds = 40 Elements, per `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` line 343.
The 4-Worlds axis is reframed in CAS v7.5 as the 4 Registers (T, A, f, E) - Clarification 8
section 8. The Elements are NOT 10 Noetics x 4 Domains; the 40 Cognitive States are that
different cross-product. Activating the wrong one is exactly the substitution this project
has been bitten by before, so `ELEMENTS` is generated and assert-checked against 40 and
against its two axes.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

RPM_ROOT = r"C:\Users\wakil\Documents\Codex\2026-10-16"
if RPM_ROOT not in sys.path:
    sys.path.insert(0, RPM_ROOT)

from rpm_council import engine as rpm  # noqa: E402

JOURNAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal")

# ============================================================================ §3  the seats

SEATS: List[Dict[str, str]] = [
    {
        "noetic": "CO-0", "name": "Idea", "seat": 1,
        "definition": "All things in and outside the Mind.",
        "operation": "ENUMERATE WHAT THERE IS. Report the full set of Ideas in scope - inside "
                     "and outside the Mind - without selecting by relevance or by the outcome "
                     "already wanted.",
        "colloquialism": "It's all in your head.",
    },
    {
        "noetic": "CO-1", "name": "Mind", "seat": 2,
        "definition": "Various degrees of awareness that processes, stores, outputs, and "
                      "intakes Ideas.",
        "operation": "MAP AWARENESS. For the blocker, report what is processed, what is stored, "
                     "what is output and what is intaken - and the degree of awareness each "
                     "stands at.",
        "colloquialism": "Paying attention. / Making up your mind. / Using your head.",
    },
    {
        "noetic": "CO-2", "name": "Positive", "seat": 3,
        "definition": "An Idea the Mind has an affinity for and is attracted toward.",
        "operation": "FIND THE ATTRACTION. Report what the target has affinity for and is "
                     "attracted toward - what it is trying to reach.",
        "colloquialism": "Drawn to it like a moth to a flame. / Speaks to me. / Can't resist.",
    },
    {
        "noetic": "CO-3", "name": "Negative", "seat": 4,
        "definition": "An Idea the Mind is adverse to and repelled by.",
        "operation": "FIND THE REPULSION. Report what the target is adverse to and repelled by. "
                     "Report it as aversion, not as critique.",
        "colloquialism": "Can't stomach it. / Rubs me the wrong way. / Wouldn't touch it with a "
                         "ten-foot pole.",
    },
    {
        "noetic": "CO-4", "name": "Vibration", "seat": 5,
        "definition": "The degree to which an Idea resonates with the Mind, its impression.",
        "operation": "MEASURE THE IMPRESSION. Report the magnitude of the effect - how hard it "
                     "landed - not its direction. Cost, latency, size, count.",
        "colloquialism": "Hit me hard. / Struck a chord. / Resonated. / Made an impression.",
    },
    {
        "noetic": "CO-5", "name": "Female", "seat": 6,
        "definition": "A Mind impregnated with an Idea, the Ideas a Mind is composed of.",
        "operation": "READ THE ACCUMULATED SUBSTRATE. Report what the blocker is composed of and "
                     "what history it carries - what earlier work it is built out of.",
        "colloquialism": "We are the sum of our experiences. / It's who I am. / Part of what "
                         "makes me me.",
    },
    {
        "noetic": "CO-6", "name": "Male", "seat": 7,
        "definition": "An Idea impregnated with another Idea, the Ideas an Idea is composed of.",
        "operation": "DECOMPOSE. Take the blocker apart into the Ideas it is composed of, and "
                     "name which part owns which fault.",
        "colloquialism": "Unpacking an idea. / Breaking it down. / Looking at what's underneath. "
                         "/ Pulling apart the argument.",
    },
    {
        "noetic": "CO-7", "name": "Rhythm", "seat": 8,
        "definition": "The rate and pattern a Mind is exposed to an Idea, entraining/conditioning "
                      "it.",
        "operation": "READ THE EXPOSURE PATTERN. Report the rate and the repetition of the "
                     "failing exposure, and what the repetition has entrained.",
        "colloquialism": "Practice makes perfect. / You are what you repeatedly do. / Getting "
                         "into a groove. / Muscle memory.",
    },
    {
        "noetic": "CO-8", "name": "Above/Cause", "seat": 9,
        "definition": "An Idea that triggers a different Idea than itself to come to Mind.",
        "operation": "TRACE THE TRIGGER. Report which Idea brings which other Idea to Mind. "
                     "Report it as triggering, not as deduction.",
        "colloquialism": "That reminds me... / One thing leads to another. / Triggered a memory. "
                         "/ Made me think of...",
    },
    {
        "noetic": "CO-9", "name": "Below/Effect", "seat": 10,
        "definition": "The Idea brought to Mind by an Above/Cause trigger.",
        "operation": "REPORT WHAT LANDED. Name the terminal effect actually brought to Mind at "
                     "the end of the chain, with its measured value.",
        "colloquialism": "It just popped into my head. / Out of nowhere I thought of... / The "
                         "thought came to me. / It just clicked.",
    },
]

#: Fail loudly if a seat drifts from the canonical roster. Ten seats, CO-0 through CO-9.
assert len(SEATS) == 10, "the council is ten seats"
assert [s["noetic"] for s in SEATS] == ["CO-%d" % i for i in range(10)]

SEAT_BY_NOETIC = {s["noetic"]: s for s in SEATS}

#: Every seat's definition must match the engine's canonical table character for character.
for _s in SEATS:
    _canon = rpm.NOETICS[_s["noetic"]]
    assert _s["name"] == _canon["name"], _s["noetic"]
    assert _s["definition"] == _canon["definition"], _s["noetic"]


# ====================================================================== §4  the 40 Elements

#: The 4 Worlds, reframed in CAS v7.5 as the 4 Phenomenological Registers.
#: Clarification 8 section 2. This is NOT the 4 Domains (P/C/E/O).
WORLDS: Dict[str, Dict[str, str]] = {
    "T": {"register": "Transcendent",
          "definition": "high-abstraction, purpose-orienting, integrative-across-particulars"},
    "A": {"register": "Analytical",
          "definition": "explicit, sequential, logical, reason-based"},
    "f": {"register": "Affective",
          "definition": "value-laden, feeling-toned"},
    "E": {"register": "Embodied",
          "definition": "sensorimotor, concrete, direct engagement with material/physical "
                        "substrate"},
}

WORLD_ORDER: Tuple[str, ...] = ("T", "A", "f", "E")


def _element_id(noetic: str, world: str) -> str:
    """Canonical Element notation: ^n|R."""
    return "^%s|%s" % (noetic.split("-")[1], world)


ELEMENTS: List[Dict[str, str]] = [
    {
        "element": _element_id(s["noetic"], w),
        "noetic": s["noetic"],
        "noetic_name": s["name"],
        "world": w,
        "register": WORLDS[w]["register"],
        "register_definition": WORLDS[w]["definition"],
        "seat": s["seat"],
    }
    for s in SEATS
    for w in WORLD_ORDER
]

assert len(ELEMENTS) == 40, "10 Noetics x 4 Worlds = 40 Elements"
assert len({e["element"] for e in ELEMENTS}) == 40
assert {e["noetic"] for e in ELEMENTS} == {s["noetic"] for s in SEATS}


def elements_for(noetics: Sequence[str]) -> List[Dict[str, str]]:
    """The Elements activated by a set of Noetics: each Noetic across all four Worlds."""
    want = set(noetics)
    return [e for e in ELEMENTS if e["noetic"] in want]


# ============================================================== §2  readings and conditions


@dataclass(frozen=True)
class Reading:
    """One named, deterministic program reading.

    A reading is never prose and never a hand-typed number. `source` names the exact command,
    file or check that produced `value`. `ok` is tri-state on purpose: True measured-and-satisfied,
    False measured-and-not-satisfied, None could-not-read. None blocks the gate.
    """
    source: str
    ok: Optional[bool]
    detail: str

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("a Reading must name its source")


@dataclass
class RequiredCondition:
    """One required condition of the target outcome, carrying its canonical four-stage chain.

    Stage meanings are the engine's canonical ones (STAGE_MEANING):
      A0  does this condition need to exist for the target at all
      D   is the condition UNDERSTOOD and specified
      W   is there a committed MECHANISM that can satisfy it
      P   is it ESTABLISHED by evidence
    A0 is 1.0 for every declared condition; the condition was declared.
    """
    id: str
    statement: str
    understood: Reading
    mechanism: Reading
    established: Reading
    prerequisites: List[str] = field(default_factory=list)

    def readings(self) -> Dict[str, Reading]:
        return {"understood": self.understood, "mechanism": self.mechanism,
                "established": self.established}

    def score(self, stage: rpm.Stage) -> float:
        r = {"D": self.understood, "W": self.mechanism, "P": self.established}
        if stage is rpm.Stage.ASPIRATION:
            return 1.0
        return 1.0 if r[stage.value].ok is True else 0.0

    def evidence(self, stage: rpm.Stage) -> rpm.Evidence:
        if stage is rpm.Stage.ASPIRATION:
            return rpm.Evidence.ESTABLISHED
        r = {"D": self.understood, "W": self.mechanism, "P": self.established}[stage.value]
        if r.ok is True:
            return rpm.Evidence.ESTABLISHED
        if r.ok is False:
            return rpm.Evidence.REFUTED
        return rpm.Evidence.UNKNOWN


def build_graph(conditions: Sequence[RequiredCondition], target_id: str,
                target_statement: str) -> rpm.Graph:
    """Assemble the prerequisite graph the RPM diagnosis runs on."""
    known = {c.id for c in conditions}
    if target_id not in known:
        raise ValueError("target %r is not among the declared conditions" % target_id)
    g = rpm.Graph()
    for c in conditions:
        unknown = [p for p in c.prerequisites if p not in known]
        if unknown:
            raise ValueError(
                "condition %r names prerequisites that do not exist: %r. The engine crashes on "
                "this by its own defect; the loop declares all nodes so the diagnosis is about "
                "the task, not about the diagnoser." % (c.id, unknown))
        cond = rpm.Condition(
            id=c.id,
            statement=c.statement,
            scores={st: c.score(st) for st in rpm.STAGE_ORDER},
            evidence={st: c.evidence(st) for st in rpm.STAGE_ORDER},
            note={rpm.Stage.PROFICIENCY: c.established.detail},
            prerequisites=list(c.prerequisites),
            status=c.evidence(rpm.Stage.PROFICIENCY),
        )
        g.add(cond)
    return g


# ================================================================ §3/§4  activation, seats

#: The engine's canonical bridge from a blocked stage to the Noetics that activate.
STAGE_ACTIVATION = rpm.STAGE_ACTIVATION
STAGE_ITERATIVE = rpm.STAGE_ITERATIVE
STAGE_MEANING = rpm.STAGE_MEANING


def activated_seats(stage: rpm.Stage) -> List[Dict[str, str]]:
    """Which seats the canon activates for a stage blocked there."""
    return [{**SEAT_BY_NOETIC[code], "anti_drift": rpm.register_warning(code) or None}
            for code in STAGE_ACTIVATION[stage]]


def elements_needed(depth: int, blocker: rpm.Blocker, seen_before: bool) -> Tuple[bool, str]:
    """Step 4 fires only 'when deeper resolution is needed'. Say why, every time."""
    if blocker in (rpm.Blocker.UNKNOWN, rpm.Blocker.CIRCULAR, rpm.Blocker.DEPTH_EXCEEDED,
                   rpm.Blocker.DELIBERATION_EXHAUSTED):
        return True, "blocker %s is not a plain shortfall; the seats need the register axis" % (
            blocker.value,)
    if seen_before:
        return True, "this same condition blocked the target on an earlier iteration"
    if depth > 0:
        return True, "the blocker sits at recursion depth %d, below the target" % depth
    return False, "first sighting of a plain shortfall: the seats carry it without the Elements"


# ============================================================ anti-drift, made executable

#: Canonical anti-drift annotations, as machine checks. Each is a refusal, not a style note.
DRIFT_VOCABULARY = {
    "CO-3": {
        "words": ("audit", "scrutinis", "scrutiniz", "find-flaw", "find flaw", "critique",
                  "critical evaluation", "review for defects", "assess the quality"),
        "why": rpm.ANTI_DRIFT["CO-3"],
    },
    "CO-8": {
        # "follows logically" was added after a probe used the sentence "Therefore we deduce it
        # follows logically" and the rule returned 2 findings instead of 3: the list held
        # "logically follows" but not the far more common "it follows logically". A drift phrase
        # that only matches in one word order is a check that looks like a check. The probe was
        # re-run against that exact sentence to prove the repair fires.
        "words": ("deduc", "infer", "inference", "therefore", "logically follows",
                  "follows logically", "reason from", "causal analysis", "root-cause analysis"),
        "why": rpm.ANTI_DRIFT["CO-8"],
    },
}


def check_seat_report(noetic: str, text: str) -> List[str]:
    """Return drift findings for one seat's report. Empty list means no drift detected."""
    rule = DRIFT_VOCABULARY.get(noetic)
    if not rule:
        return []
    low = text.lower()
    return [w for w in rule["words"] if w in low]


# ============================================================================ the loop

@dataclass
class WorkOrder:
    iteration: int
    target_id: str
    target_statement: str
    blocker: str
    condition: str
    condition_statement: str
    stage: str
    stage_meaning: str
    evidence_at_stage: str
    depth: int
    note: str
    iterative: bool
    seats: List[Dict[str, Any]]
    elements: List[Dict[str, str]]
    elements_reason: str
    children: List[Dict[str, Any]]
    frontier: List[Dict[str, Any]]
    frontier_seats: List[Dict[str, Any]]

    def to_json(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "target_id": self.target_id,
            "target_statement": self.target_statement,
            "blocker": self.blocker,
            "condition": self.condition,
            "condition_statement": self.condition_statement,
            "stage": self.stage,
            "stage_meaning": self.stage_meaning,
            "evidence_at_stage": self.evidence_at_stage,
            "depth": self.depth,
            "note": self.note,
            "iterative_not_counted_toward_depth": self.iterative,
            "activated_seats": [
                {"seat": s["seat"], "noetic": s["noetic"], "name": s["name"],
                 "definition": s["definition"], "operation": s["operation"],
                 "colloquialism": s["colloquialism"], "anti_drift": s["anti_drift"]}
                for s in self.seats
            ],
            "elements": [e["element"] for e in self.elements],
            "elements_detail": self.elements,
            "elements_reason": self.elements_reason,
            "children": self.children,
            "frontier": self.frontier,
            "frontier_seats": self.frontier_seats,
        }


def _child_summary(children: Sequence[rpm.Diagnosis]) -> List[Dict[str, Any]]:
    out = []
    for c in children:
        out.append({"condition": c.condition, "stage": c.stage.value,
                    "blocker": c.blocker.value, "depth": c.depth})
        out.extend(_child_summary(c.children))
    return out


def _frontier(children: Sequence[rpm.Diagnosis]) -> List[Dict[str, Any]]:
    """The leaves of the diagnosis tree: the conditions that actually failed, deepest first.

    The root's own blocker is what the canon activates the council on. The frontier is where
    the failure physically is. A council given only the root is told 'the target is blocked at
    D' and has to guess; given the frontier it is told which named check failed.
    """
    out: List[Dict[str, Any]] = []
    for c in children:
        if c.children:
            out.extend(_frontier(c.children))
        else:
            out.append({"condition": c.condition, "statement": c.statement,
                        "stage": c.stage.value, "blocker": c.blocker.value, "depth": c.depth,
                        "note": c.note})
    out.sort(key=lambda r: (-r["depth"], r["condition"]))
    return out


def frontier_seat_groups(frontier: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The seats the canon activates for each distinct stage blocked on the frontier.

    The canon names which Noetics activate per blocked stage. The root diagnosis names the
    stage that obstructs the target; the frontier names the stage that physically failed.
    When those differ, both sets of seats are canonically live, so both are reported.
    """
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for f in frontier:
        st = rpm.Stage(f["stage"])
        if st in seen:
            continue
        seen.add(st)
        group = activated_seats(st)
        out.append({"stage": st.value, "stage_meaning": STAGE_MEANING[st],
                    "iterative_not_counted_toward_depth": STAGE_ITERATIVE[st],
                    "noetics": [s["noetic"] for s in group], "seats": group})
    return out


def run_iteration(task: Dict[str, Any], iteration: int,
                  prior_blockers: Sequence[str] = ()) -> Tuple[WorkOrder, rpm.Diagnosis]:
    """One turn of the loop. Diagnose the target and emit the council's work order."""
    conditions: List[RequiredCondition] = task["conditions"]()
    target_id: str = task["target_id"]
    target_statement: str = task["target_statement"]
    threshold: float = task.get("threshold", 0.5)

    graph = build_graph(conditions, target_id, target_statement)
    d = rpm.diagnose(graph, target_id, threshold=threshold)

    frontier = _frontier(d.children)
    groups = frontier_seat_groups(frontier)

    seat_list: List[Dict[str, Any]] = []
    element_list: List[Dict[str, str]] = []
    reason = "not needed: the target is satisfied"

    if d.blocker is not rpm.Blocker.SATISFIED:
        seat_list = activated_seats(d.stage)
        need, reason = elements_needed(d.depth, d.blocker, d.condition in set(prior_blockers))
        if need:
            noetics = {s["noetic"] for s in seat_list}
            for g in groups:
                noetics.update(g["noetics"])
            element_list = elements_for(sorted(noetics))

    order = WorkOrder(
        iteration=iteration,
        target_id=target_id,
        target_statement=target_statement,
        blocker=d.blocker.value,
        condition=d.condition,
        condition_statement=d.statement,
        stage=d.stage.value,
        stage_meaning=d.stage_meaning,
        evidence_at_stage=d.evidence_at_stage.value,
        depth=d.depth,
        note=d.note,
        iterative=STAGE_ITERATIVE[d.stage],
        seats=seat_list,
        elements=element_list,
        elements_reason=reason,
        children=_child_summary(d.children),
        frontier=frontier,
        frontier_seats=groups,
    )
    return order, d


def write_iteration(order: WorkOrder, diagnosis: rpm.Diagnosis,
                    engine_sha: Optional[str] = None) -> str:
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    payload = {
        "iteration": order.iteration,
        "engine_sha256": engine_sha,
        "work_order": order.to_json(),
        "diagnosis_json": diagnosis.to_json(),
        "safeguards_fired": list(diagnosis.safeguards_fired),
        "graph_cycles": getattr(diagnosis, "graph_cycles", None),
        "contradictions": getattr(diagnosis, "contradictions", None),
    }
    path = os.path.join(JOURNAL_DIR, "LOOP_ITERATION_%03d.json" % order.iteration)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False)
    jl = os.path.join(JOURNAL_DIR, "LOOP_JOURNAL.jsonl")
    with open(jl, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "iteration": order.iteration,
            "engine_sha256": engine_sha,
            "blocker": order.blocker,
            "condition": order.condition,
            "stage": order.stage,
            "depth": order.depth,
            "seats": [s["noetic"] for s in order.seats],
            "elements": len(order.elements),
            "elements_reason": order.elements_reason,
        }) + "\n")
    return path


def prior_blockers_from_journal() -> List[str]:
    jl = os.path.join(JOURNAL_DIR, "LOOP_JOURNAL.jsonl")
    out: List[str] = []
    if not os.path.exists(jl):
        return out
    with open(jl, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            out.append(rec.get("condition", ""))
    return out


def next_iteration_number() -> int:
    return len([p for p in prior_blockers_from_journal()]) + 1
