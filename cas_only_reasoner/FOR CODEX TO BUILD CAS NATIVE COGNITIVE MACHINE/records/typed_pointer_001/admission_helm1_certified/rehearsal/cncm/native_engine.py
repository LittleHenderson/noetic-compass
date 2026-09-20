"""Persistent host for the opt-in, checked native-procedure runtime.

This driver proposes transitions; only NativeCoordinator may change state.
It neither imports registry snapshots nor supplies arithmetic answers. A fresh
episode may inherit the registry only from this machine's own terminal episode.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import canonical_json, digest
from .engine import CognitiveMachine
from .kernel import StateStore, TraceFabric
from .model import BranchStatus, ContractError, IntentType, Provenance, TerminalStatus, TraceEvent
from .native_kernel import (
    NativeCoordinator,
    _TRUSTED_NATIVE_EPISODE,
    boot_native_state,
    expected_acquisition_frame,
    native_intent,
)
from .native_model import NativeIntentType, NativeProblem, NativeState
from .native_profile import (
    MAX_EPISODES,
    MAX_JOURNAL_BYTES,
    MAX_JOURNAL_EVENTS,
    NativeProfile,
    load_native_profile,
)


JOURNAL_SCHEMA = "cncm.native-journal/0.2"
EVIDENCE_SCHEMA = "cncm.native-evidence/0.2"
SUMMARY_SCHEMA = "cncm.native-run-summary/0.2"


@dataclass(frozen=True, slots=True)
class NativeRunResult:
    """A snapshot; its evidence is derived, never accepted as caller input."""

    problem: NativeProblem
    initial_state_hash: str
    source_profile: NativeProfile
    final_state: NativeState
    trace: tuple[TraceEvent, ...]

    def __post_init__(self) -> None:
        if (type(self.problem) is not NativeProblem or type(self.source_profile) is not NativeProfile
                or type(self.final_state) is not NativeState or type(self.trace) is not tuple):
            raise ContractError("native result requires typed coordinator snapshots")
        state = self.final_state
        if (state.state_hash != state.computed_hash()
                or state.native_contract_digest != self.source_profile.profile_digest
                or state.global_workspace.problem_id != self.problem.reasoning.problem_id):
            raise ContractError("native result state/profile/problem binding mismatch")
        previous_hash, previous_event_hash, previous_event_id = self.initial_state_hash, "", None
        for event in self.trace:
            if (type(event) is not TraceEvent or not event.sealed
                    or event.event_hash != event.computed_hash()
                    or event.pre_state_hash != previous_hash
                    or event.previous_event_hash != previous_event_hash
                    or event.parent_event_id != previous_event_id
                    or event.run_id != state.run_id):
                raise ContractError("native result trace binding mismatch")
            previous_hash, previous_event_hash, previous_event_id = (
                event.post_state_hash, event.event_hash, event.event_id)
        if state.state_hash != previous_hash or state.trace_head != previous_event_hash:
            raise ContractError("native result final trace/state binding mismatch")

    @property
    def terminal_status(self) -> TerminalStatus:
        return self.final_state.halt_status

    @property
    def trace_digest(self) -> str:
        return digest([event.to_dict() for event in self.trace])

    @property
    def output(self) -> str | None:
        call = next((item for item in self.final_state.native_calls
                     if item.call_id == self.problem.call.call_id), None)
        return call.output if call is not None else None

    @property
    def evidence(self) -> dict[str, Any]:
        state = self.final_state
        accepted = {kind.value: 0 for kind in NativeIntentType}
        rejected = 0
        for event in self.trace:
            authorized = set(event.authorized_intent_ids)
            rejected += len(event.rejected_intents)
            for intent in event.proposed_intents:
                if type(intent.intent_type) is NativeIntentType and intent.intent_id in authorized:
                    accepted[intent.intent_type.value] += 1
        body = {
            "schema_version": EVIDENCE_SCHEMA,
            "problem_hash": self.problem.input_hash,
            "source_profile_digest": self.source_profile.profile_digest,
            "initial_state_hash": self.initial_state_hash,
            "prior_episode_state_hash": state.prior_episode_state_hash,
            "final_state_hash": state.state_hash,
            "trace_digest": self.trace_digest,
            "terminal_status": state.halt_status.value,
            "calls": [call.to_dict() for call in state.native_calls],
            "procedure_heads": [list(item) for item in state.procedure_heads],
            "authorized_native_transitions": accepted,
            "rejected_intent_count": rejected,
            "conservative_policy_work_reserved": {
                "instructions": (self.problem.budget.instructions_remaining
                                 - state.native_budget.instructions_remaining),
                "checker_calls": (self.problem.budget.checker_calls_remaining
                                  - state.native_budget.checker_calls_remaining),
            },
            "remaining_native_budget": state.native_budget.to_dict(),
            "scope": {
                "procedure_source": "bounded_public_finite_grammar",
                "qualification": "public_fixed_engineering_panel",
                "neural_program_synthesis": False,
                "secret_evaluation_custody": False,
                "native_neural_flow": False,
            },
        }
        return {**body, "evidence_digest": digest(body)}

    def summary(self) -> dict[str, Any]:
        conclusion = self.final_state.commitment_state.conclusion
        return {
            "schema_version": SUMMARY_SCHEMA,
            "run_id": self.final_state.run_id,
            "problem_id": self.problem.reasoning.problem_id,
            "call_id": self.problem.call.call_id,
            "terminal_status": self.terminal_status.value,
            "procedure_output": self.output,
            "conclusion": conclusion.to_dict() if conclusion is not None else None,
            "logical_ticks": self.final_state.logical_tick,
            "final_state_hash": self.final_state.state_hash,
            "trace_head": self.final_state.trace_head,
            "trace_digest": self.trace_digest,
            "evidence_digest": self.evidence["evidence_digest"],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "final_state": self.final_state.to_dict(),
            "trace": [event.to_dict() for event in self.trace],
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class _Episode:
    problem: NativeProblem
    initial_state_hash: str
    coordinator: NativeCoordinator


class NativeMachine:
    """One persistent authority chain, with a fresh budget for each new run.

    Construction accepts a source profile, never state or a registry. The public
    journal is evidence for semantic replay, not an importable learning store.
    Python host code is trusted, as in the reference v0.1 host.
    """

    def __init__(self, profile: NativeProfile | None = None) -> None:
        selected = load_native_profile() if profile is None else profile
        if type(selected) is not NativeProfile:
            raise ContractError("native machine requires a NativeProfile")
        self._profile = selected
        self._episodes: list[_Episode] = []
        self._reasoner = CognitiveMachine()

    @property
    def profile(self) -> NativeProfile:
        return self._profile

    @property
    def coordinator(self) -> NativeCoordinator:
        if not self._episodes:
            raise ContractError("native machine has not started an episode")
        return self._episodes[-1].coordinator

    @property
    def state(self) -> NativeState:
        return self.coordinator.store.snapshot()

    @property
    def problem(self) -> NativeProblem:
        if not self._episodes:
            raise ContractError("native machine has not started an episode")
        return self._episodes[-1].problem

    def start(self, native_problem: NativeProblem | dict[str, Any]) -> NativeState:
        if self._episodes and self.state.halt_status is TerminalStatus.RUNNING:
            raise ContractError("finish the current native episode before starting another")
        if len(self._episodes) >= MAX_EPISODES:
            raise ContractError("native episode limit exceeded")
        if type(native_problem) is NativeProblem:
            packet = NativeProblem.from_dict(native_problem.to_dict())
        elif type(native_problem) is dict:
            packet = NativeProblem.from_dict(native_problem)
        else:
            raise ContractError("native start requires a NativeProblem or its exact wire object")
        recorded_events = sum(len(item.coordinator.trace.events) for item in self._episodes)
        if recorded_events + packet.reasoning.budgets.max_ticks > MAX_JOURNAL_EVENTS:
            raise ContractError("episode tick allowance exceeds remaining native journal capacity")
        previous = self.state if self._episodes else None
        initial = boot_native_state(
            packet, self.profile, previous_state=previous,
            _trust_previous=_TRUSTED_NATIVE_EPISODE if previous is not None else None,
        )
        coordinator = NativeCoordinator(
            store=StateStore(initial), trace=TraceFabric(),
            native_problem=packet, profile=self.profile,
        )
        self._episodes.append(_Episode(packet, initial.state_hash, coordinator))
        return self.state

    def advance(self, *, allow_acquisition: bool = True) -> NativeState:
        """Advance a native stage; completion runs the ordinary reasoning gates.

        The flag controls entry to acquisition. It does not abandon a caller
        whose acquisition frame is already active.
        """
        if type(allow_acquisition) is not bool:
            raise ContractError("allow_acquisition must be a boolean")
        if self.state.halt_status is not TerminalStatus.RUNNING:
            return self.state
        if self.state.commitment_state.decision_status == "COMMITTED":
            self._reasoner._halt(self.coordinator, TerminalStatus.CONCLUDED)
            return self.state
        if self.coordinator.trace.events and self.coordinator.trace.events[-1].rejected_intents:
            self._stop_after_rejection()
            return self.state
        if self._reserve_halt():
            return self.state
        spec = self.problem.call
        call = self._call()
        if call is None:
            self._execute_native(NativeIntentType.REQUEST_PROCEDURE_CALL,
                                 {"call": spec.to_dict()})
        elif call.status == "REQUESTED":
            if not allow_acquisition:
                self._native_failure_halt("ACQUISITION_DISABLED")
            else:
                frame = expected_acquisition_frame(self.state, spec)
                self._execute_native(NativeIntentType.PUSH_ACQUISITION,
                                     {"call_id": spec.call_id, "frame": frame.to_dict()})
        elif call.status == "SUSPENDED":
            if call.artifact_sha256 is not None:
                frame = self._active_frame()
                self._execute_native(NativeIntentType.RETURN_ACQUISITION, {
                    "call_id": spec.call_id, "frame_id": frame.frame_id,
                    "artifact_sha256": call.artifact_sha256,
                    "success": True, "failure": None,
                })
            else:
                selected = self.coordinator.selected_artifact(spec.call_id)
                if selected is None:
                    self._execute_native(NativeIntentType.SELECT_PROCEDURE,
                                         {"call_id": spec.call_id})
                else:
                    self._execute_native(NativeIntentType.INSTALL_PROCEDURE, {
                        "call_id": spec.call_id, "artifact": selected.to_dict(),
                        "qualification_digest": None,
                    })
        elif call.status == "READY":
            self._execute_native(NativeIntentType.APPLY_PROCEDURE, {
                "call_id": spec.call_id, "artifact_sha256": call.artifact_sha256,
            })
        elif call.status == "FAILED":
            self._native_failure_halt("NATIVE_TRANSITION_REJECTED")
        elif call.status == "COMPLETE":
            self._finish_reasoning()
        else:
            raise ContractError("unsupported native call stage")
        return self.state

    def run(self, native_problem: NativeProblem | dict[str, Any] | None = None,
            *, allow_acquisition: bool = True) -> NativeRunResult:
        if type(allow_acquisition) is not bool:
            raise ContractError("allow_acquisition must be a boolean")
        if native_problem is not None:
            self.start(native_problem)
        while self.state.halt_status is TerminalStatus.RUNNING:
            before = self.state.state_hash
            self.advance(allow_acquisition=allow_acquisition)
            if self.state.state_hash == before:
                raise ContractError("native engine made no kernel transition")
        return self.result()

    def rollback(self, capability: str, *, target_installation_digest: str | None = None) -> NativeState:
        """Request lineage rollback before this episode's procedure call starts."""
        if type(capability) is not str or (target_installation_digest is not None
                                           and type(target_installation_digest) is not str):
            raise ContractError("rollback capability and target must be strings (or a null target)")
        if self.state.halt_status is not TerminalStatus.RUNNING or self.state.native_calls:
            raise ContractError("rollback requires a running episode before any procedure request")
        if self.state.rpm_stack:
            raise ContractError("rollback requires a quiescent RPM stack")
        current = dict(self.state.procedure_heads).get(capability)
        target = (self.coordinator.previous_installation_digest(capability)
                  if target_installation_digest is None else target_installation_digest)
        if self._reserve_halt():
            return self.state
        self._execute_native(NativeIntentType.ROLLBACK_PROCEDURE, {
            "capability": capability, "expected_head": current,
            "target_installation_digest": target,
        })
        return self.state

    def result(self) -> NativeRunResult:
        episode = self._episodes[-1] if self._episodes else None
        if episode is None:
            raise ContractError("native machine has not started an episode")
        return NativeRunResult(
            problem=episode.problem, initial_state_hash=episode.initial_state_hash,
            source_profile=self.profile, final_state=self.state,
            trace=self.coordinator.trace.events,
        )

    @property
    def evidence(self) -> dict[str, Any]:
        return self.result().evidence

    def journal(self) -> dict[str, Any]:
        """Return independent pure data, including a partial active episode."""
        episodes = []
        for episode in self._episodes:
            state = episode.coordinator.store.snapshot()
            episodes.append({
                "problem": episode.problem.to_dict(),
                "initial_state_hash": episode.initial_state_hash,
                "prior_episode_state_hash": state.prior_episode_state_hash,
                "source_profile_digest": self.profile.profile_digest,
                "trace": [event.to_dict() for event in episode.coordinator.trace.events],
                "proposal_batches": episode.coordinator.proposal_batches,
                "final_state": state.to_dict(),
            })
        body = {"schema_version": JOURNAL_SCHEMA,
                "source_profile": self.profile.to_dict(), "episodes": episodes}
        result = {**body, "journal_digest": digest(body)}
        if sum(len(item["trace"]) for item in episodes) > MAX_JOURNAL_EVENTS:
            raise ContractError("native journal event limit exceeded")
        if len(canonical_json(result).encode("utf-8")) > MAX_JOURNAL_BYTES:
            raise ContractError("native journal byte limit exceeded")
        return result

    def _call(self):
        return next((item for item in self.state.native_calls
                     if item.call_id == self.problem.call.call_id), None)

    def _active_frame(self):
        if not self.state.rpm_stack or self.state.rpm_stack[-1].call_id != self.problem.call.call_id:
            raise ContractError("native caller has no matching active acquisition frame")
        return self.state.rpm_stack[-1]

    def _reserve_halt(self) -> bool:
        if self._reasoner._must_reserve_halt(self.state):
            self._reasoner._halt(self.coordinator, TerminalStatus.BUDGET_EXHAUSTED,
                                 diagnostics=("tick budget exhausted",))
            return True
        return False

    def _execute_native(self, kind: NativeIntentType, mutation: dict[str, Any]) -> None:
        intent = native_intent(self.coordinator, kind, mutation)
        result = self._reasoner._execute_one(
            self.coordinator, intent.issuer_subsystem, intent, require_authorized=False,
        )
        if result.rejected_intents and self.state.halt_status is TerminalStatus.RUNNING:
            self._stop_after_rejection()

    def _native_failure_halt(self, reason: str) -> None:
        if self.state.halt_status is not TerminalStatus.RUNNING:
            return
        intent = self.coordinator.native_failure_halt(reason, call_id=self.problem.call.call_id)
        self._reasoner._execute_one(self.coordinator, intent.issuer_subsystem, intent)

    def _stop_after_rejection(self) -> None:
        # Do not retry a rejected selection, installation, application or rollback.
        if self._reserve_halt():
            return
        call = self._call()
        if call is not None and call.status == "SUSPENDED" and self.state.rpm_stack:
            frame = self._active_frame()
            failure = native_intent(self.coordinator, NativeIntentType.RETURN_ACQUISITION, {
                "call_id": call.call_id, "frame_id": frame.frame_id,
                "artifact_sha256": None, "success": False,
                "failure": "NATIVE_TRANSITION_REJECTED",
            })
            self._reasoner._execute_one(self.coordinator, failure.issuer_subsystem, failure)
        if self.state.halt_status is TerminalStatus.RUNNING:
            self._native_failure_halt("NATIVE_TRANSITION_REJECTED")

    def _finish_reasoning(self) -> None:
        packet, coordinator = self.problem.reasoning, self.coordinator
        branch_id = self.problem.call.branch_id
        try:
            # All continuation decisions derive from the live replayed state.
            # A crash after comparison or commitment must not repeat that write.
            reports = self.state.global_workspace.comparison_reports
            if reports:
                winner = reports[-1].winner_branch_id
                if winner is not None and self.state.branch_map()[winner].status is not BranchStatus.SELECTED:
                    select = self._reasoner._intent(
                        coordinator, intent_type=IntentType.SET_BRANCH_STATUS,
                        issuer="comparison_system", capability="report_selected_candidate",
                        scope=f"branch:{winner}", branch_id=winner, goal_id=packet.goal_id,
                        mutation={"status": BranchStatus.SELECTED.value},
                        provenance=(Provenance("comparison", reports[-1].report_id, "winner report only"),),
                    )
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
                    status = TerminalStatus.CONFLICT_UNRESOLVED
                    diagnostic = "explicit contradiction prevented commitment"
                elif branch.status is BranchStatus.BLOCKED:
                    status = TerminalStatus.NEEDS_INFORMATION
                    diagnostic = "no branch established every required premise"
                else:
                    status = TerminalStatus.INADMISSIBLE
                    diagnostic = "no admissible candidate survived shared-frame comparison"
                self._reasoner._halt(coordinator, status, lacunae=branch.unknowns,
                                     diagnostics=(diagnostic,))
            elif self._reasoner._commit_winner(packet, winner, coordinator):
                self._reasoner._halt(coordinator, TerminalStatus.CONCLUDED)
            elif self.state.halt_status is TerminalStatus.RUNNING:
                self._stop_after_rejection()
        except ContractError:
            if (self.state.halt_status is TerminalStatus.RUNNING and coordinator.trace.events
                    and coordinator.trace.events[-1].rejected_intents):
                self._stop_after_rejection()
            else:
                raise
