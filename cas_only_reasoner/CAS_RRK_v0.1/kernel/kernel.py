"""The CAS-RRK kernel: the nine-step atomic transition protocol.

SNAPSHOT -> ENABLE -> SCHEDULE -> PROPOSE -> VALIDATE -> RESOLVE ->
STATE COMMIT -> TRACE -> HALT TEST, sealed every tick, with deterministic
replay from the sealed authorized intents.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional, Tuple

from . import CAS_RRK_VERSION
from .components import (
    ALL_COMPONENTS, BranchManager, CommitmentLatch, HaltingController,
    Reasoner, RPMStackComponent, Scheduler, WriteBackController,
)
from .schemas import GoalFrame, MachineState, Proposition, TraceEvent
from .state_store import ISSUER_PRIORITY, TransactionCoordinator, make_intent

DEFAULT_CONSTITUTION = {
    "revision": 1,
    "branch_budget": 64,
    "max_ticks": 200,
    "t_high": 0.7,
    "t_low": 0.4,
}


def build_initial_state(problem: Dict, constitution: Dict, run_id: str,
                        seed: int) -> MachineState:
    goal = problem["goal"]
    state = MachineState(
        runtime_version=CAS_RRK_VERSION,
        logical_tick=0,
        run_id=run_id,
        seed=seed,
        constitution_revision=constitution.get("revision", 1),
        foundation_state={"frozen": "TKS 7x4 ontology admitted as typed fields only"},
        drive_state={"frozen": "CAS drive rails F1..F7"},
        domain_power_state={"P_GOOD": True, "C_GOOD": True,
                            "E_GOOD": True, "O_ENABLED": True},
        global_workspace={
            "propositions": list(problem.get("propositions", [])),
            "rules": list(problem.get("rules", [])),
            "available_actions": problem.get("available_actions", {}),
            "constitution": constitution,
        },
        working_memory=[],
        episodic_memory_revision=0,
        active_goal_id=goal.get("goal_id"),
        rpm_stack=[GoalFrame.from_json(goal)],
        branch_table={},
        pending_intents=[],
        commitment_state={},
        learning_queue=[],
        halt_status=None,
        trace_head=0,
    )
    state.refresh_hash()
    return state


class CAS_RRK:
    """One deterministic reasoning episode over one problem packet."""

    def __init__(self, problem: Dict, constitution: Optional[Dict] = None,
                 run_id: str = "run_01", seed: int = 0) -> None:
        self.problem = problem
        self.constitution = dict(constitution or DEFAULT_CONSTITUTION)
        self.run_id = run_id
        self.seed = seed
        self.coordinator = TransactionCoordinator(problem)
        self.scheduler = Scheduler()
        self.branch_manager = BranchManager()
        self.reasoner = Reasoner()
        self.rpm_stack = RPMStackComponent()
        self.latch = CommitmentLatch()
        self.halting = HaltingController()
        self.write_back = WriteBackController()
        self.state = build_initial_state(problem, self.constitution,
                                         run_id, seed)
        self.trace: List[TraceEvent] = []
        self.sealed_halt = False

    # ------------------------------------------------------------------
    def _proposals(self, state: MachineState, tick: int,
                   scheduled: List[str]) -> List[Dict]:
        proposals: List[Dict] = self.scheduler.propose(state, scheduled, tick)
        if "branch_manager" in scheduled:
            proposals += self.branch_manager.propose(state, self.problem, tick)
        if "reasoning" in scheduled:
            proposals += self.reasoner.propose(state, self.problem, tick)
        if "rpm_stack" in scheduled:
            proposals += self.rpm_stack.propose(state, self.problem, tick)
        if "commitment_latch" in scheduled:
            proposals += self.latch.propose(state, tick)
        if "halting_controller" in scheduled:
            proposals += self.halting.propose(state, self.problem, tick)
        return proposals

    # ------------------------------------------------------------------
    def _tick(self) -> Tuple[TraceEvent, MachineState]:
        state = self.state
        tick = state.logical_tick
        pre_hash = state.state_hash

        if tick >= self.constitution.get("max_ticks", 200)                 and state.halt_status is None:
            scheduled = ["halting_controller"]
            proposals = [make_intent(
                f"halt_{tick}", "HaltIntent", "halting_controller", tick,
                mutation={"status": "LOOP_LIMIT_REACHED"},
                provenance={"phase": "HALT_TEST"})]
        elif state.halt_status is not None and self.sealed_halt:
            scheduled = ["write_back"]
            proposals = self.write_back.propose(state, self.problem, tick,
                                                trace_sealed=True)
        else:
            scheduled = self.scheduler.schedule(state)
            proposals = self._proposals(state, tick, scheduled)

        validated: List[Dict] = []
        rejected: List[Dict] = []
        reasons: List[str] = []
        ordered = sorted(proposals, key=lambda i: (
            ISSUER_PRIORITY.get(i.get("issuer_subsystem"), 99),
            i.get("intent_id", "")))
        for intent in ordered:
            ok, reason = self.coordinator.validate(intent, state)
            if ok:
                validated.append(intent)
            else:
                rejected.append(intent)
                reasons.append(f"{intent.get('intent_id')}: {reason}")

        authorized, conflicts, conflict_reasons = self.coordinator.resolve(validated)
        rejected.extend(conflicts)
        reasons.extend(conflict_reasons)

        new_state, mutations = self.coordinator.apply(state, authorized)
        if any("branch budget exceeded" in r for r in reasons):
            new_state.working_memory.append({"kind": "budget_exceeded"})
            # Seal the flag into the state hash: the trace must cover it.
            new_state.refresh_hash()

        event = TraceEvent(
            event_id=f"ev_{tick:04d}",
            logical_tick=tick,
            pre_state_hash=pre_hash,
            enabled_components=list(ALL_COMPONENTS),
            scheduled_components=list(scheduled),
            proposed_intents=list(proposals),
            authorized_intents=list(authorized),
            rejected_intents=list(rejected),
            rejection_reasons=list(reasons),
            committed_mutations=list(mutations),
            post_state_hash=new_state.state_hash,
            terminal_status=new_state.halt_status,
        )
        return event, new_state

    # ------------------------------------------------------------------
    def run(self) -> Dict:
        while True:
            event, new_state = self._tick()
            self.trace.append(event)
            self.state = new_state
            if self.state.halt_status is not None:
                if self.sealed_halt:
                    break
                self.sealed_halt = True
        return self.evidence_packet()

    # ------------------------------------------------------------------
    def evidence_packet(self) -> Dict:
        conclusion = None
        proof = None
        committed = self.state.commitment_state.get("committed_target")
        if committed:
            conclusion = committed
            target = Proposition.from_json(committed)
            from .cas_sem import prove
            p = prove(target, self.state.durable_propositions(),
                      self.state.durable_rules())
            proof = {"rules_used": p.rules_used,
                     "premises_used": [x.to_json() for x in p.premises_used]}
        trace_json = [e.to_json() for e in self.trace]
        digest = hashlib.sha256(
            json.dumps(trace_json, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return {
            "problem_id": self.problem.get("problem_id"),
            "terminal_status": self.state.halt_status,
            "conclusion": conclusion,
            "trace_digest": digest,
            "final_state_hash": self.state.state_hash,
            "trace": trace_json,
            "proof": proof,
        }


# --------------------------------------------------------------------------
def replay(problem: Dict, trace: List[Dict], run_id: str,
           seed: int) -> Tuple[bool, List[str], MachineState]:
    """Deterministic replay: re-apply the sealed authorized intents to a
    fresh state and require identical per-tick state hashes."""
    coordinator = TransactionCoordinator(problem)
    state = build_initial_state(problem, problem.get("constitution")
                                or DEFAULT_CONSTITUTION, run_id, seed)
    mismatches: List[str] = []
    for event in trace:
        authorized = event.get("authorized_intents", [])
        for intent in authorized:
            ok, reason = coordinator.validate(intent, state)
            if not ok:
                mismatches.append(
                    f"tick {event['logical_tick']} {intent.get('intent_id')}: {reason}")
        new_state, _ = coordinator.apply(state, authorized)
        if new_state.state_hash != event.get("post_state_hash"):
            mismatches.append(
                f"tick {event['logical_tick']}: hash {new_state.state_hash} "
                f"!= sealed {event.get('post_state_hash')}")
        state = new_state
    terminal_ok = (state.halt_status == trace[-1].get("terminal_status")
                   if trace else state.halt_status is None)
    if not terminal_ok:
        mismatches.append("terminal status mismatch on replay")
    return (not mismatches), mismatches, state
