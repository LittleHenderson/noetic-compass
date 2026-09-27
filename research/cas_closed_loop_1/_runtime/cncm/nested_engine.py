"""Versioned host for the bounded nested-equation coordinator.

The host proposes one graph transition at a time. Only NestedCoordinator writes
state; no serialized state, external registry, dependency plan or answer is
accepted as a shortcut. Episode inheritance remains inside this authority chain.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import canonical_json, digest
from .engine import CognitiveMachine
from .kernel import StateStore, TraceFabric
from .model import BranchStatus, ContractError, IntentType, Provenance, TerminalStatus, TraceEvent
from .nested_kernel import NestedCoordinator, _TRUSTED_NESTED_EPISODE, boot_nested_state
from .nested_model import NestedIntentType, NestedProblem, NestedState
from .nested_profile import (MAX_EPISODES, MAX_JOURNAL_BYTES, MAX_JOURNAL_EVENTS,
                             NestedProfile, load_nested_profile)

JOURNAL_SCHEMA = "cncm.nested-journal/0.3"
EVIDENCE_SCHEMA = "cncm.nested-evidence/0.3"
SUMMARY_SCHEMA = "cncm.nested-run-summary/0.3"


@dataclass(frozen=True, slots=True)
class NestedRunResult:
    problem: NestedProblem
    initial_state_hash: str
    source_profile: NestedProfile
    final_state: NestedState
    trace: tuple[TraceEvent, ...]

    def __post_init__(self):
        if (type(self.problem) is not NestedProblem or type(self.source_profile) is not NestedProfile
                or type(self.final_state) is not NestedState or type(self.trace) is not tuple):
            raise ContractError("nested result requires typed coordinator snapshots")
        state = self.final_state
        if (state.state_hash != state.computed_hash()
                or state.native_contract_digest != self.source_profile.profile_digest
                or state.global_workspace.problem_id != self.problem.reasoning.problem_id):
            raise ContractError("nested result state/profile/problem binding mismatch")
        previous_hash, previous_event_hash, previous_event_id = self.initial_state_hash, "", None
        for event in self.trace:
            if (type(event) is not TraceEvent or not event.sealed
                    or event.event_hash != event.computed_hash()
                    or event.pre_state_hash != previous_hash
                    or event.previous_event_hash != previous_event_hash
                    or event.parent_event_id != previous_event_id
                    or event.run_id != state.run_id):
                raise ContractError("nested result trace binding mismatch")
            previous_hash, previous_event_hash, previous_event_id = (
                event.post_state_hash, event.event_hash, event.event_id)
        if state.state_hash != previous_hash or state.trace_head != previous_event_hash:
            raise ContractError("nested result final trace/state binding mismatch")

    @property
    def terminal_status(self):
        return self.final_state.halt_status

    @property
    def root_call(self):
        return next((call for call in self.final_state.native_calls
                     if call.goal_id == self.problem.reasoning.goal_id
                     and call.variable == self.problem.query_variable), None)

    @property
    def output(self):
        call = self.root_call
        return call.output if call is not None else None

    @property
    def trace_digest(self):
        return digest([event.to_dict() for event in self.trace])

    @property
    def evidence(self) -> dict[str, Any]:
        state = self.final_state
        accepted = {kind.value: 0 for kind in NestedIntentType}
        rejected = 0
        for event in self.trace:
            authorized = set(event.authorized_intent_ids)
            rejected += len(event.rejected_intents)
            for intent in event.proposed_intents:
                if type(intent.intent_type) is NestedIntentType and intent.intent_id in authorized:
                    accepted[intent.intent_type.value] += 1
        body = {
            "schema_version": EVIDENCE_SCHEMA, "problem_hash": self.problem.input_hash,
            "source_profile_digest": self.source_profile.profile_digest,
            "initial_state_hash": self.initial_state_hash,
            "prior_episode_state_hash": state.prior_episode_state_hash,
            "final_state_hash": state.state_hash, "trace_digest": self.trace_digest,
            "terminal_status": state.halt_status.value,
            "query_variable": self.problem.query_variable,
            "calls": [call.to_dict() for call in state.native_calls],
            "remaining_frames": [frame.to_dict() for frame in state.rpm_stack],
            "procedure_heads": [list(row) for row in state.procedure_heads],
            "authorized_nested_transitions": accepted, "rejected_intent_count": rejected,
            "conservative_policy_work_reserved": {
                "instructions": self.problem.budget.instructions_remaining - state.native_budget.instructions_remaining,
                "checker_calls": self.problem.budget.checker_calls_remaining - state.native_budget.checker_calls_remaining,
            },
            "remaining_native_budget": state.native_budget.to_dict(),
            "scope": {"dependency_source": "bounded_typed_equation_references",
                "procedure_source": "bounded_public_finite_grammar",
                "qualification": "public_fixed_engineering_panel",
                "neural_program_synthesis": False, "secret_evaluation_custody": False,
                "native_neural_flow": False, "external_actions": False},
        }
        return {**body, "evidence_digest": digest(body)}

    def summary(self):
        conclusion = self.final_state.commitment_state.conclusion
        return {"schema_version": SUMMARY_SCHEMA, "run_id": self.final_state.run_id,
                "problem_id": self.problem.reasoning.problem_id,
                "query_variable": self.problem.query_variable,
                "terminal_status": self.terminal_status.value, "procedure_output": self.output,
                "conclusion": conclusion.to_dict() if conclusion is not None else None,
                "logical_ticks": self.final_state.logical_tick,
                "final_state_hash": self.final_state.state_hash,
                "trace_head": self.final_state.trace_head, "trace_digest": self.trace_digest,
                "evidence_digest": self.evidence["evidence_digest"]}

    def to_dict(self):
        return {"summary": self.summary(), "final_state": self.final_state.to_dict(),
                "trace": [event.to_dict() for event in self.trace], "evidence": self.evidence}


@dataclass(frozen=True, slots=True)
class _Episode:
    problem: NestedProblem
    initial_state_hash: str
    coordinator: NestedCoordinator


class NestedMachine:
    """Trusted host for one persistent, opt-in native 0.3 authority chain."""

    def __init__(self, profile: NestedProfile | None = None):
        selected = load_nested_profile() if profile is None else profile
        if type(selected) is not NestedProfile:
            raise ContractError("nested machine requires a NestedProfile")
        self._profile = selected
        self._episodes: list[_Episode] = []
        self._reasoner = CognitiveMachine()

    @property
    def profile(self):
        return self._profile

    @property
    def coordinator(self):
        if not self._episodes:
            raise ContractError("nested machine has not started an episode")
        return self._episodes[-1].coordinator

    @property
    def state(self):
        return self.coordinator.store.snapshot()

    @property
    def problem(self):
        if not self._episodes:
            raise ContractError("nested machine has not started an episode")
        return self._episodes[-1].problem

    def start(self, nested_problem):
        if self._episodes:
            if self.state.halt_status is TerminalStatus.RUNNING:
                raise ContractError("finish the current nested episode before starting another")
            if self.state.rpm_stack:
                raise ContractError("unresolved nested frames prevent a new episode")
        if len(self._episodes) >= MAX_EPISODES:
            raise ContractError("nested episode limit exceeded")
        if type(nested_problem) is NestedProblem:
            packet = NestedProblem.from_dict(nested_problem.to_dict())
        elif type(nested_problem) is dict:
            packet = NestedProblem.from_dict(nested_problem)
        else:
            raise ContractError("nested start requires a NestedProblem or its exact wire object")
        recorded = sum(len(row.coordinator.trace.events) for row in self._episodes)
        if recorded + packet.reasoning.budgets.max_ticks > MAX_JOURNAL_EVENTS:
            raise ContractError("episode tick allowance exceeds remaining nested journal capacity")
        previous = self.state if self._episodes else None
        initial = boot_nested_state(packet, self.profile, previous_state=previous,
            _trust_previous=_TRUSTED_NESTED_EPISODE if previous is not None else None)
        coordinator = NestedCoordinator(store=StateStore(initial), trace=TraceFabric(),
            nested_problem=packet, profile=self.profile)
        self._episodes.append(_Episode(packet, initial.state_hash, coordinator))
        return self.state

    def advance(self, *, allow_acquisition=True):
        if type(allow_acquisition) is not bool:
            raise ContractError("allow_acquisition must be a boolean")
        if self.state.halt_status is not TerminalStatus.RUNNING:
            return self.state
        if self.state.commitment_state.decision_status == "COMMITTED":
            self._reasoner._halt(self.coordinator, TerminalStatus.CONCLUDED)
            return self.state
        if self._reserve_halt():
            return self.state
        # A rejected child transition is continued by the coordinator's explicit
        # failure/unwind intents. The host neither retries nor pops any frame.
        intent = self.coordinator.next_intent(allow_acquisition=allow_acquisition)
        if intent is not None:
            self._execute(intent)
            return self.state
        root = self.coordinator.root_call()
        if root is None or self.state.rpm_stack:
            raise ContractError("nested coordinator stopped before a quiescent root outcome")
        if root.status == "COMPLETE":
            self._finish_reasoning()
        elif root.status == "FAILED":
            self._execute(self.coordinator.failure_halt())
        else:
            raise ContractError("nested coordinator stopped at an unfinished root")
        return self.state

    def run(self, nested_problem=None, *, allow_acquisition=True):
        if type(allow_acquisition) is not bool:
            raise ContractError("allow_acquisition must be a boolean")
        if nested_problem is not None:
            self.start(nested_problem)
        while self.state.halt_status is TerminalStatus.RUNNING:
            before = self.state.state_hash
            self.advance(allow_acquisition=allow_acquisition)
            if self.state.state_hash == before:
                raise ContractError("nested engine made no kernel transition")
        return self.result()

    def rollback(self):
        if self.state.halt_status is not TerminalStatus.RUNNING or self.state.native_calls:
            raise ContractError("rollback requires a running episode before any equation request")
        if self.state.rpm_stack:
            raise ContractError("rollback requires a quiescent RPM stack")
        if not self._reserve_halt():
            self._execute(self.coordinator.rollback_intent())
        return self.state

    def result(self):
        if not self._episodes:
            raise ContractError("nested machine has not started an episode")
        row = self._episodes[-1]
        return NestedRunResult(row.problem, row.initial_state_hash, self.profile,
                               self.state, self.coordinator.trace.events)

    @property
    def evidence(self):
        return self.result().evidence

    def journal(self):
        episodes = []
        for row in self._episodes:
            state = row.coordinator.store.snapshot()
            episodes.append({"problem": row.problem.to_dict(),
                "initial_state_hash": row.initial_state_hash,
                "prior_episode_state_hash": state.prior_episode_state_hash,
                "source_profile_digest": self.profile.profile_digest,
                "trace": [event.to_dict() for event in row.coordinator.trace.events],
                "proposal_batches": row.coordinator.proposal_batches, "final_state": state.to_dict()})
        body = {"schema_version": JOURNAL_SCHEMA, "source_profile": self.profile.to_dict(),
                "episodes": episodes}
        result = {**body, "journal_digest": digest(body)}
        if sum(len(row["trace"]) for row in episodes) > MAX_JOURNAL_EVENTS:
            raise ContractError("nested journal event limit exceeded")
        if len(canonical_json(result).encode("utf-8")) > MAX_JOURNAL_BYTES:
            raise ContractError("nested journal byte limit exceeded")
        return result

    def _reserve_halt(self):
        if self._reasoner._must_reserve_halt(self.state):
            self._reasoner._halt(self.coordinator, TerminalStatus.BUDGET_EXHAUSTED,
                                 diagnostics=("tick budget exhausted",))
            return True
        return False

    def _execute(self, intent):
        return self._reasoner._execute_one(self.coordinator, intent.issuer_subsystem,
                                           intent, require_authorized=False)

    def _ordinary_refusal(self):
        if self.state.halt_status is TerminalStatus.RUNNING and not self._reserve_halt():
            self._reasoner._halt(self.coordinator, TerminalStatus.INADMISSIBLE,
                                 diagnostics=("ordinary reasoning transition rejected",))

    def _finish_reasoning(self):
        root = self.coordinator.root_call()
        if root is None or root.status != "COMPLETE" or self.state.rpm_stack:
            raise ContractError("ordinary reasoning requires completed root and empty stack")
        packet, coordinator, branch_id = self.problem.reasoning, self.coordinator, "branch-main"
        try:
            reports = self.state.global_workspace.comparison_reports
            if reports:
                winner = reports[-1].winner_branch_id
                if winner is not None and self.state.branch_map()[winner].status is not BranchStatus.SELECTED:
                    select = self._reasoner._intent(coordinator, intent_type=IntentType.SET_BRANCH_STATUS,
                        issuer="comparison_system", capability="report_selected_candidate",
                        scope=f"branch:{winner}", branch_id=winner, goal_id=packet.goal_id,
                        mutation={"status": BranchStatus.SELECTED.value},
                        provenance=(Provenance("comparison", reports[-1].report_id, "winner report only"),))
                    self._reasoner._execute_one(coordinator, "comparison_system", select)
            else:
                branch = self.state.branch_map()[branch_id]
                if branch.status is not BranchStatus.ADMISSIBLE:
                    if not branch.decompositions:
                        self._reasoner._record_decomposition(packet, branch_id, coordinator)
                    if self.state.halt_status is not TerminalStatus.RUNNING:
                        return
                    self._reasoner._derive_until_stable(packet, branch_id, coordinator, {})
                    if self.state.halt_status is not TerminalStatus.RUNNING:
                        return
                    self._reasoner._record_actual_contradictions(branch_id, coordinator)
                    if self.state.halt_status is not TerminalStatus.RUNNING:
                        return
                    branch = self.state.branch_map()[branch_id]
                    expected = coordinator._decompose_query(self.state, branch)
                    if len(branch.decompositions) < 2 or branch.decompositions[-1].to_dict() != expected.to_dict():
                        self._reasoner._record_decomposition(packet, branch_id, coordinator)
                    if self.state.halt_status is not TerminalStatus.RUNNING:
                        return
                winner = self._reasoner._classify_and_compare(packet, coordinator, (branch_id,))
            if self.state.halt_status is not TerminalStatus.RUNNING:
                return
            if winner is None:
                branch = self.state.branch_map()[branch_id]
                if branch.contradictions:
                    status, diagnostic = TerminalStatus.CONFLICT_UNRESOLVED, "explicit contradiction prevented commitment"
                elif branch.status is BranchStatus.BLOCKED:
                    status, diagnostic = TerminalStatus.NEEDS_INFORMATION, "no branch established every required premise"
                else:
                    status, diagnostic = TerminalStatus.INADMISSIBLE, "no admissible candidate survived shared-frame comparison"
                self._reasoner._halt(coordinator, status, lacunae=branch.unknowns, diagnostics=(diagnostic,))
            elif self._reasoner._commit_winner(packet, winner, coordinator):
                self._reasoner._halt(coordinator, TerminalStatus.CONCLUDED)
            elif self.state.halt_status is TerminalStatus.RUNNING:
                self._ordinary_refusal()
        except ContractError:
            if (self.state.halt_status is TerminalStatus.RUNNING and coordinator.trace.events
                    and coordinator.trace.events[-1].rejected_intents):
                self._ordinary_refusal()
            else:
                raise
