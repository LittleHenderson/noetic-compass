"""CAS-RR v0.1: the reasoning machine itself.

The runtime is a stateful cognitive virtual machine: a deterministic,
single-threaded scheduler that drives the CJTs, CMB, CDAB, RPM, commitment
controller, domain sequencer, and learning controller through the native
CAS reasoning cycle until the episode halts in one of seven typed states.

The board says what is connected; this runtime says what fires next.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .cjt import BiasRef, CJTConfig, ConstitutionError, transfer
from .candidates import CandidateGenerator, CandidateSet
from .commit import CommitmentController
from .compare import Tournament
from .domains import DomainDescent, DomainPowerState, PowerSequencer
from .foundations import FoundationEngineBank, GoalFrame
from .learning import LearningController
from .memory import CMB
from .ontology import TERMINAL
from .reasoning import ReasoningStage
from .rpm import RPMController
from .terms import Atom, Rule, instantiate, is_ground, unify_conclusion
from .trace import ProvenancePacket, Trace
from .world import WorldState


@dataclass
class Constitution:
    """The machine's worldview, knowledge, and drive configuration."""

    name: str
    version: str
    bias_bank: Dict[str, float]
    drive_supply: Dict[str, float]
    foundation_g: Dict[str, float]
    foundation_q: Dict[str, Dict[str, float]]
    acquisition: Dict[str, float]
    constraints: Dict[str, float] = field(default_factory=lambda: {
        "policy": 0.2, "context": 0.2, "resource": 0.2})
    principled_preds: Tuple[str, ...] = ("violates_charter",)
    eval_gain: float = 1.0
    candidate_gain: float = 1.5
    commit_gain: float = 2.0
    learn_gain: float = 0.05
    t_high: float = 0.7
    t_low: float = 0.4
    max_ticks: int = 200
    attention_budget: float = 10.0

    def validate(self) -> None:
        # Law 3 (gain is not truth) is enforced at boot: the evaluation gain
        # of any constitution must be exactly unity.
        if self.eval_gain != 1.0:
            raise ConstitutionError(
                f"constitution {self.name}: evaluation gain must be unity "
                f"(1.0), got {self.eval_gain} - gain is not truth")
        for key in ("memory_bias", "charter_bias", "goal_bias"):
            if key not in self.bias_bank:
                raise ConstitutionError(
                    f"constitution {self.name}: missing typed bias '{key}'")
        for m in range(1, 8):
            if f"F{m}" not in self.drive_supply:
                raise ConstitutionError(
                    f"constitution {self.name}: missing drive rail F{m}")
            for prefix in ("D", "W", "P"):
                if f"{prefix}{m}" not in self.acquisition:
                    raise ConstitutionError(
                        f"constitution {self.name}: missing acquisition {prefix}{m}")
        if "A_root" not in self.acquisition:
            raise ConstitutionError(
                f"constitution {self.name}: missing A_root acquisition")
        if not (0.0 < self.t_low < self.t_high <= 1.0):
            raise ConstitutionError(
                "constitution: need 0 < t_low < t_high <= 1")
        for m in range(1, 8):
            if f"TF{m}" not in self.foundation_g:
                raise ConstitutionError(
                    f"constitution {self.name}: missing foundation TF{m}")
            dist = self.foundation_q.get(f"TF{m}")
            if dist is None or abs(sum(dist.values()) - 1.0) > 1e-9:
                raise ConstitutionError(
                    f"constitution {self.name}: TF{m} world distribution "
                    "must sum to 1")


@dataclass
class Problem:
    """A CAS-encoded problem: premises, knowledge, hypothesis space, goal."""

    problem_id: str
    description: str
    facts: List[Atom]
    rules: List[Rule]
    alternatives: List[Atom]
    goal: GoalFrame
    authored_effects: Dict[str, Dict[str, float]] = field(default_factory=dict)
    available_actions: Dict[str, str] = field(default_factory=dict)
    world_actions: Dict[str, Dict] = field(default_factory=dict)
    action_prerequisites: Dict[str, Dict] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.problem_id:
            raise ValueError("problem needs an id")
        if self.goal is None:
            raise ValueError("problem needs a goal frame")
        for r in self.rules:
            if not r.rule_id:
                raise ValueError("rule without id")


def default_constitution() -> Constitution:
    return Constitution(
        name="cas_rr_default_v0.1",
        version="0.1.0",
        bias_bank={"memory_bias": 0.7, "charter_bias": 0.9, "goal_bias": 0.6},
        drive_supply={f"F{m}": 0.8 for m in range(1, 8)},
        foundation_g={f"TF{m}": 0.7 for m in range(1, 8)},
        foundation_q={f"TF{m}": {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
                      for m in range(1, 8)},
        acquisition={
            "A_root": 1.0,
            **{f"D{m}": 0.8 for m in range(1, 8)},
            **{f"W{m}": 0.8 for m in range(1, 8)},
            **{f"P{m}": 0.8 for m in range(1, 8)},
        },
    )


ATTENTION_COST_PER_CYCLE = 1.0


class CASRuntime:
    """The CAS Reasoning Runtime - a native CAS reasoning machine."""

    def __init__(self, constitution: Constitution, problem: Problem) -> None:
        constitution.validate()
        problem.validate()
        self.constitution = constitution
        self.problem = problem

        self.bank = FoundationEngineBank(
            constitution.foundation_g, constitution.foundation_q,
            constitution.acquisition)
        self.cmb = CMB()
        self.cmb.load_problem_knowledge(
            problem.facts, problem.rules, f"problem:{problem.problem_id}")
        self.world = WorldState(set(problem.facts), problem.world_actions)

        self.trace = Trace()
        self.tick = 0
        self.status = "UNBOOTED"
        self.allocated = 0.0

        self.domains = DomainPowerState()
        self.learning = LearningController(episodic_enabled=True)
        self.descent = DomainDescent(self.domains, self.learning)
        self.rpm = RPMController()
        self.gen = CandidateGenerator(constitution.bias_bank, self._now)
        self.reasoner = ReasoningStage(constitution.bias_bank, self._now)
        self.commit = CommitmentController(constitution.t_high, constitution.t_low)

        # Live object maps (logic) ...
        self.decompositions: Dict[str, Any] = {}
        self.inferences: Dict[str, Any] = {}
        self.effects: List[Any] = []
        # ... and their cumulative JSON records (provenance).
        self.record_memory: List[Dict] = []
        self.record_candidates: List[Dict] = []
        self.record_decompositions: Dict[str, Dict] = {}
        self.record_inferences: Dict[str, Dict] = {}
        self.record_effects: List[Dict] = []
        self.record_comparisons: List[Dict] = []
        self.record_decision: Optional[Dict] = None
        self.record_learning: List[Dict] = []
        self.record_output: Optional[Dict] = None

    def _now(self) -> int:
        return self.tick

    def _facts(self) -> List[Atom]:
        merged = set(self.cmb.all_facts()) | set(self.world.sorted_facts())
        return sorted(merged, key=str)

    def _rules(self) -> List[Rule]:
        return self.cmb.all_rules()

    def _query_atoms(self, goal: GoalFrame,
                     alternatives: List[Atom]) -> List[Atom]:
        queries: List[Atom] = []
        ground = [a for a in ([goal.desired_outcome] + alternatives) if is_ground(a)]
        for a in ground:
            queries.append(a)
            for rule in self._rules():
                b = unify_conclusion(rule.conclusion, a)
                if b is not None:
                    for prem in rule.premises:
                        queries.append(instantiate(prem, b))
        deduped: List[Atom] = []
        for q in queries:
            if q not in deduped:
                deduped.append(q)
        return deduped

    # ------------------------------------------------------------------
    def boot(self) -> None:
        self.status = "BOOTING"
        for record in PowerSequencer.boot(self.domains):
            self.trace.record(self.tick, "BOOT", "POWER", **record)
        self.rpm.push(self.problem.goal)
        self.trace.record(self.tick, "BOOT", "GOAL_PUSHED",
                          goal=self.problem.goal.to_dict())
        self.status = "RUNNING"

    def run(self) -> Dict[str, Any]:
        self.boot()
        while self.status not in TERMINAL:
            if self.tick >= self.constitution.max_ticks:
                self.status = "LOOP_LIMIT_REACHED"
                self.trace.record(self.tick, "HALT", "LOOP_LIMIT_REACHED",
                                  reason="max_ticks exhausted - rumination stop gate")
                break
            self.tick += 1
            goal = self.rpm.top()
            if goal is None:
                self.status = "CONCLUDED"
                break
            self._cycle(goal)
        return ProvenancePacket(self).assemble()

    # ------------------------------------------------------------------
    def _cycle(self, goal: GoalFrame) -> None:
        t = self.tick

        # Phase 1: Foundation arbitration - the active goal frame.
        self.trace.record(t, "1_FOUNDATION", "GOAL_ACTIVE", goal=goal.to_dict())

        # Phase 2: Attention allocation (Ohm-shaped consistency check).
        budget = self.bank.allocate(goal, self.constitution.drive_supply,
                                    self.constitution.constraints)
        cost = ATTENTION_COST_PER_CYCLE
        if self.allocated + cost > self.constitution.attention_budget:
            self.status = "RESOURCE_EXHAUSTED"
            self.trace.record(t, "2_ATTENTION", "RESOURCE_EXHAUSTED",
                              allocated=self.allocated, cost=cost,
                              budget=self.constitution.attention_budget)
            self.trace.record(t, "HALT", "RESOURCE_EXHAUSTED")
            return
        self.allocated += cost
        budget.actual_runtime_allocation = cost
        self.trace.record(t, "2_ATTENTION", "BUDGET", budget=budget.to_dict())

        # Phase 3: Memory retrieval (CMB structural query + lacunae).
        if goal.kind == "subgoal":
            alts = ([Atom("action_executable", (goal.subgoal_action,))]
                    if goal.subgoal_action else [])
            authored = {str(a): {} for a in alts}
        else:
            alts = list(self.problem.alternatives)
            authored = self.problem.authored_effects
        queries = self._query_atoms(goal, alts)
        mem = self.cmb.retrieve(queries, query_label=f"goal {goal.goal_id}")
        self.record_memory.append(mem.to_dict())
        self.trace.record(t, "3_MEMORY", "RETRIEVED",
                          selected=[i.item_id for i in mem.selected],
                          lacunae=[l.to_dict() for l in mem.lacunae])

        # Phase 4: ^8 candidate generation (moderate gain).
        cands = self.gen.generate(alts, self.problem.problem_id, mem, goal,
                                  self._rules(), authored)
        self.record_candidates.append(cands.to_dict())
        self.trace.record(t, "4_CANDIDATES", "GENERATED",
                          candidate_ids=[c.candidate_id for c in cands.candidates],
                          reason_single=cands.reason_single)

        # Phases 5-6: ^6 decomposition and ^9 inference at unity gain.
        facts, rules = self._facts(), self._rules()
        for c in cands.candidates:
            drec = self.reasoner.decompose(c, facts, rules, t)
            irec = self.reasoner.infer(c, drec, facts, rules, t)
            self.decompositions[c.candidate_id] = drec
            self.inferences[c.candidate_id] = irec
            self.record_decompositions[c.candidate_id] = drec.to_dict()
            self.record_inferences[c.candidate_id] = irec.to_dict()
            self.trace.record(t, "5_DECOMPOSE", "DECOMPOSED",
                              candidate=c.candidate_id,
                              unknowns=len(drec.unknowns),
                              support=drec.support_fraction)
            self.trace.record(t, "6_INFER", "INFERRED",
                              candidate=c.candidate_id,
                              success=irec.success,
                              rules_used=irec.rules_used,
                              contradiction=irec.contradiction_status)

        # Phase 7: 28-channel foundation evaluation.
        for c in cands.candidates:
            report = self.bank.evaluate(c.candidate_id, c.authored_effects)
            self.effects.append(report)
            self.record_effects.append(report.to_dict())

        # Phase 8: CDAB comparison under shared bias and matched gain.
        tour = Tournament().run(cands.candidates, goal, self.decompositions,
                                self.inferences, self.effects)
        self.record_comparisons.append(tour)
        winner_id = tour["winner"]
        self.trace.record(t, "8_COMPARE", "TOURNAMENT",
                          winner=winner_id,
                          eliminated=tour["eliminated"])

        # Phase 9: RPM D -> W -> P scan; recurse on the first unmet.
        # Recursion is to arbitrary depth: any goal - including a subgoal
        # whose resolving action has its own prerequisites - may descend.
        proof_complete = bool(winner_id and self.inferences[winner_id].success)
        if goal.goal_id not in self.rpm.cache:
            outcome = self.rpm.initial_scan(
                goal, self.bank, self.world, proof_complete)
        else:
            outcome = self.rpm.re_measure(
                goal, self.bank, self.world, proof_complete)
        unmet = outcome.first_unmet
        self.trace.record(t, "9_RPM", "SCAN", goal=goal.goal_id,
                          D_ok=outcome.D_ok, W_ok=outcome.W_ok,
                          P_ok=outcome.P_ok, first_unmet=unmet,
                          missing_token=outcome.missing_token)

        if unmet is not None:
            action = self.problem.available_actions.get(outcome.missing_token)
            if goal.kind == "subgoal" and action is None:
                # A leaf subgoal with no resolving action halts typed.
                terminal = {
                    "KNOWLEDGE": "NEEDS_INFORMATION",
                    "CAPABILITY": "NEEDS_CAPABILITY",
                    "DESIRE": "CONFLICT_UNRESOLVED",
                }[goal.subgoal_type or "DESIRE"]
                self.status = terminal
                self.trace.record(t, "9_RPM", "HALT", status=terminal,
                                  reason=f"subgoal {goal.goal_id} cannot "
                                         f"resolve blocked {unmet}")
                self.trace.record(t, "HALT", terminal)
                return
            prerequisites = self.problem.action_prerequisites.get(action or "", {})
            sub = self.rpm.descend(goal, unmet, action, prerequisites)
            self.rpm.push(sub)
            self.trace.record(t, "9_RPM", "SUBGOAL_CREATED",
                              **self.rpm.subgoal_events[-1])
            return

        # Phase 10: Commitment - Schmitt hysteresis over typed gates.
        winner = next((c for c in cands.candidates
                       if c.candidate_id == winner_id), None)
        confidence = (self.inferences[winner_id].confidence if winner else 0.0)
        commit_cfg = CJTConfig(
            label="commit_stage", noetic="^4", domain="E", drive="F5",
            register="A", role="commit", beta=self.constitution.commit_gain,
            cutoff=0.2, sat=0.95, breakdown=1.5,
            bias=BiasRef("goal_bias", "^5", "E", "F5", "A"))
        cres = transfer(cause=confidence,
                        bias=self.constitution.bias_bank.get("goal_bias", 0.6),
                        cfg=commit_cfg, tick=t)
        if cres.region == "breakdown":
            self.trace.record(t, "10_COMMIT", "FAULT",
                              note="commit junction in breakdown region")
        level = cres.value

        decision = self.commit.decide(
            winner_id, winner.target if winner else None, tour, unmet,
            self.domains, self.constitution, self.world, goal,
            self.inferences, level)
        self.record_decision = decision.to_dict()
        self.trace.record(t, "10_COMMIT", "DECISION",
                          decision=decision.to_dict())

        if decision.terminal_status is not None:
            self.status = decision.terminal_status
            self.trace.record(t, "HALT", decision.terminal_status,
                              reason=str(decision.to_dict()["gates"]))
            return
        if not decision.committed:
            self.trace.record(t, "10_COMMIT", "HOLD", state=decision.state,
                              level=level)
            return

        # Phase 11: Domain descent P -> C -> E -> O and ACT.
        if goal.kind == "subgoal":
            action = goal.subgoal_action
            spec = self.world.apply_action(action)
            for k, v in spec.get("acquisition", {}).items():
                self.bank.acquisition[k] = v
            self.rpm.resolve(goal)
            self.rpm.pop()
            self.trace.record(t, "11_ACT", "SUBGOAL_RESOLVED",
                              subgoal=goal.goal_id, action=action)
            disposition = self.learning.dispose(
                f"resolved {goal.goal_id} via {action}")
            self.record_learning.append(disposition.to_dict())
            return

        conversion = self.descent.descend(
            winner.target if winner else Atom("none"), goal.kind)
        self.record_output = {
            "goal": goal.goal_id,
            "conclusion": str(winner.target) if winner else None,
            "conversion": conversion,
        }
        self.trace.record(t, "11_ACT", "OUTPUT", output=self.record_output)

        # Phase 12: Episodic store + learning disposition.
        packet = ProvenancePacket(self).assemble()
        self.cmb.store_episode(packet)
        disposition = self.learning.dispose(
            f"episode {self.problem.problem_id} concluded", packet)
        self.record_learning.append(disposition.to_dict())
        self.trace.record(t, "12_LEARN", "DISPOSITION",
                          disposition=disposition.to_dict())

        self.status = "CONCLUDED"
        self.trace.record(t, "HALT", "CONCLUDED")
