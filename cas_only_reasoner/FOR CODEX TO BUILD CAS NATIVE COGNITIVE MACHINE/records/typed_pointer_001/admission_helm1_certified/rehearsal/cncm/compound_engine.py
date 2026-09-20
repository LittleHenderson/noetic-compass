"""Opt-in host for source-bound memory and conditional compound arithmetic.

Only the coordinator writes state. The host's source allowlist is external
authority, extended explicitly between episodes; journal data cannot expand it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .canonical import canonical_json, digest
from .engine import CognitiveMachine
from .kernel import StateStore, TraceFabric
from .model import ContractError, TerminalStatus, TraceEvent
from .nested_engine import NestedMachine, NestedRunResult
from .compound_kernel import (CompoundCoordinator, _TRUSTED_COMPOUND_EPISODE,
                              boot_compound_state)
from .compound_model import CompoundIntentType, CompoundProblem, CompoundState
from .semantic_model import SemanticIntentType, canonical_trusted_ingress, ingress_digest
from .compound_profile import (MAX_EPISODES, MAX_JOURNAL_BYTES, MAX_JOURNAL_EVENTS,
                               CompoundProfile, load_compound_profile)

JOURNAL_SCHEMA = "cncm.compound-journal/0.5"
EVIDENCE_SCHEMA = "cncm.compound-evidence/0.5"
SUMMARY_SCHEMA = "cncm.compound-run-summary/0.5"


@dataclass(frozen=True, slots=True)
class CompoundRunResult(NestedRunResult):
    problem: CompoundProblem
    source_profile: CompoundProfile
    final_state: CompoundState
    trusted_ingress_digest: str

    def __post_init__(self):
        if (type(self.problem) is not CompoundProblem or type(self.source_profile) is not CompoundProfile
                or type(self.final_state) is not CompoundState or type(self.trace) is not tuple):
            raise ContractError("compound result requires typed coordinator snapshots")
        state = self.final_state
        if (state.state_hash != state.computed_hash()
                or state.native_contract_digest != self.source_profile.profile_digest
                or state.ingress_digest != self.trusted_ingress_digest
                or state.global_workspace.problem_id != self.problem.reasoning.problem_id):
            raise ContractError("compound result state/profile/problem/ingress binding mismatch")
        previous_hash, previous_event_hash, previous_event_id = self.initial_state_hash, "", None
        for event in self.trace:
            if (type(event) is not TraceEvent or not event.sealed
                    or event.event_hash != event.computed_hash()
                    or event.pre_state_hash != previous_hash
                    or event.previous_event_hash != previous_event_hash
                    or event.parent_event_id != previous_event_id
                    or event.run_id != state.run_id):
                raise ContractError("compound result trace binding mismatch")
            previous_hash, previous_event_hash, previous_event_id = (
                event.post_state_hash, event.event_hash, event.event_id)
        if state.state_hash != previous_hash or state.trace_head != previous_event_hash:
            raise ContractError("compound result final trace/state binding mismatch")

    @property
    def root_call(self):
        return self.final_state.compound_call

    @property
    def evidence(self):
        state = self.final_state
        compound_counts = {kind.value: 0 for kind in CompoundIntentType}
        semantic_counts = {kind.value: 0 for kind in SemanticIntentType}
        rejected = 0
        for event in self.trace:
            authorized = set(event.authorized_intent_ids)
            rejected += len(event.rejected_intents)
            for intent in event.proposed_intents:
                if intent.intent_id in authorized:
                    if type(intent.intent_type) is CompoundIntentType:
                        compound_counts[intent.intent_type.value] += 1
                    elif type(intent.intent_type) is SemanticIntentType:
                        semantic_counts[intent.intent_type.value] += 1
        body = {
            "schema_version": EVIDENCE_SCHEMA, "problem_hash": self.problem.input_hash,
            "source_profile_digest": self.source_profile.profile_digest,
            "initial_state_hash": self.initial_state_hash,
            "prior_episode_state_hash": state.prior_episode_state_hash,
            "final_state_hash": state.state_hash, "trace_digest": self.trace_digest,
            "terminal_status": state.halt_status.value,
            "query_variable": self.problem.query_variable,
            "compound_call": self.root_call.to_dict() if self.root_call is not None else None,
            "remaining_frames": [frame.to_dict() for frame in state.rpm_stack],
            "compound_head": state.compound_head,
            "compound_artifacts": [artifact.to_dict() for artifact in state.compound_artifacts],
            "compound_records": [record.to_dict() for record in state.compound_records],
            "primitive_heads": [list(row) for row in state.procedure_heads],
            "primitive_artifact_digests": [artifact.artifact_sha256 for artifact in state.procedural_artifacts],
            "authorized_compound_transitions": compound_counts,
            "authorized_semantic_transitions": semantic_counts,
            "rejected_intent_count": rejected,
            "conservative_policy_work_reserved": {
                "instructions": self.problem.budget.instructions_remaining - state.native_budget.instructions_remaining,
                "checker_calls": self.problem.budget.checker_calls_remaining - state.native_budget.checker_calls_remaining},
            "remaining_native_budget": state.native_budget.to_dict(),
            "ingress_digest": self.trusted_ingress_digest,
            "memory_failure": state.memory_failure,
            "memory_resolution_digest": state.memory_resolution_digest,
            "source_bindings": [row.to_dict() for row in state.memory_bindings],
            "claim_status": "CONDITIONAL_ON_RECORDED_SOURCE_BINDINGS",
            "unconditional_world_truth": False,
            "scope": {"program_source": "bounded_one_or_two_call_constructor",
                "primitive_source": "bounded_public_finite_grammar",
                "qualification": "public_fixed_engineering_panel",
                "source_authority": "caller_supplied_statement_digest_allowlist",
                "external_source_authentication": False, "external_fact_verification": False,
                "neural_program_synthesis": False, "secret_evaluation_custody": False,
                "native_neural_flow": False, "external_actions": False,
                "answer_scope": "arithmetic conditional on recorded source bindings"},
        }
        return {**body, "evidence_digest": digest(body)}

    def summary(self):
        conclusion = self.final_state.commitment_state.conclusion
        return {"schema_version": SUMMARY_SCHEMA, "run_id": self.final_state.run_id,
            "problem_id": self.problem.reasoning.problem_id,
            "query_variable": self.problem.query_variable,
            "terminal_status": self.terminal_status.value,
            "conditional_output": self.output,
            "conditional_conclusion": conclusion.to_dict() if conclusion is not None else None,
            "claim_status": "CONDITIONAL_ON_RECORDED_SOURCE_BINDINGS",
            "unconditional_world_truth": False,
            "source_binding_statuses": [{"reference": row.ref.to_dict(),
                "statement_digests": list(row.statement_digests), "statuses": list(row.statuses)}
                for row in self.final_state.memory_bindings],
            "ingress_digest": self.trusted_ingress_digest,
            "memory_resolution_digest": self.final_state.memory_resolution_digest,
            "memory_failure": self.final_state.memory_failure,
            "logical_ticks": self.final_state.logical_tick,
            "final_state_hash": self.final_state.state_hash,
            "trace_head": self.final_state.trace_head, "trace_digest": self.trace_digest,
            "evidence_digest": self.evidence["evidence_digest"]}


@dataclass(frozen=True, slots=True)
class _Episode:
    problem: CompoundProblem
    initial_state_hash: str
    coordinator: CompoundCoordinator


class CompoundMachine(NestedMachine):
    """Source-bound authority chain; no external registry or state import.

    The inherited ordinary reasoning helpers operate only after the compound
    coordinator has checked memory resolution and completed the compound root.
    """

    def __init__(self, profile: CompoundProfile | None = None, *, trusted_ingress):
        selected = load_compound_profile() if profile is None else profile
        if type(selected) is not CompoundProfile:
            raise ContractError("compound machine requires a CompoundProfile")
        self._trusted_ingress = canonical_trusted_ingress(trusted_ingress)
        self._initial_trusted_ingress = self._trusted_ingress
        self._ingress_digest = ingress_digest(self._trusted_ingress)
        self._profile = selected
        self._episodes: list[_Episode] = []
        self._reasoner = CognitiveMachine()

    @property
    def trusted_ingress(self):
        return self._trusted_ingress

    @property
    def initial_trusted_ingress(self):
        return self._initial_trusted_ingress

    def start(self, compound_problem, *, additional_trusted_ingress=()):
        additions = canonical_trusted_ingress(additional_trusted_ingress)
        if additions and not self._episodes:
            raise ContractError("genesis trust must be supplied to the host constructor")
        if set(additions) & set(self._trusted_ingress):
            raise ContractError("additional trusted ingress overlaps existing authority")
        next_ingress = canonical_trusted_ingress(self._trusted_ingress + additions)
        if self._episodes:
            if self.state.halt_status is TerminalStatus.RUNNING:
                raise ContractError("finish the current compound episode before starting another")
            if self.state.rpm_stack:
                raise ContractError("unresolved compound frames prevent a new compound episode")
        if len(self._episodes) >= MAX_EPISODES:
            raise ContractError("compound episode limit exceeded")
        if type(compound_problem) is CompoundProblem:
            packet = CompoundProblem.from_dict(compound_problem.to_dict())
        elif type(compound_problem) is dict:
            packet = CompoundProblem.from_dict(compound_problem)
        else:
            raise ContractError("compound start requires a CompoundProblem or its exact wire object")
        recorded = sum(len(row.coordinator.trace.events) for row in self._episodes)
        if recorded + packet.reasoning.budgets.max_ticks > MAX_JOURNAL_EVENTS:
            raise ContractError("episode tick allowance exceeds remaining compound journal capacity")
        previous = self.state if self._episodes else None
        initial = boot_compound_state(packet, self.profile, next_ingress,
            previous_state=previous,
            previous_trusted_ingress=self._trusted_ingress if previous is not None else None,
            _trust_previous=_TRUSTED_COMPOUND_EPISODE if previous is not None else None)
        coordinator = CompoundCoordinator(store=StateStore(initial), trace=TraceFabric(),
            compound_problem=packet, profile=self.profile, trusted_ingress=next_ingress)
        self._trusted_ingress = next_ingress
        self._ingress_digest = ingress_digest(next_ingress)
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
        intent = self.coordinator.next_intent(allow_acquisition=allow_acquisition)
        if intent is not None:
            self._execute(intent)
            return self.state
        if self.state.memory_failure is not None:
            self._execute(self.coordinator.failure_halt())
            return self.state
        root = self.coordinator.root_call()
        if root is None or self.state.rpm_stack:
            raise ContractError("compound coordinator stopped before a quiescent root outcome")
        if root.status == "COMPLETE":
            self._finish_reasoning()
        elif root.status == "FAILED":
            self._execute(self.coordinator.failure_halt())
        else:
            raise ContractError("compound coordinator stopped at an unfinished root")
        return self.state

    def run(self, compound_problem=None, *, allow_acquisition=True, additional_trusted_ingress=()):
        if type(allow_acquisition) is not bool:
            raise ContractError("allow_acquisition must be a boolean")
        additions = canonical_trusted_ingress(additional_trusted_ingress)
        if additions and compound_problem is None:
            raise ContractError("ingress extension requires a new compound problem")
        if compound_problem is not None:
            self.start(compound_problem, additional_trusted_ingress=additions)
        return NestedMachine.run(self, allow_acquisition=allow_acquisition)

    def rollback(self, *, capability="compound"):
        if type(capability) is not str or capability not in {"compound", "primitive"}:
            raise ContractError("rollback capability must be compound or primitive")
        if self.state.memory_resolution_digest is None or self.state.memory_failure is not None:
            raise ContractError("compound rollback requires checked memory resolution")
        if self.state.halt_status is not TerminalStatus.RUNNING or self.state.compound_call is not None:
            raise ContractError("rollback requires a running episode before any compound request")
        if self.state.rpm_stack:
            raise ContractError("rollback requires a quiescent RPM stack")
        if not self._reserve_halt():
            self._execute(self.coordinator.rollback_intent(kind=capability.upper()))
        return self.state

    def result(self):
        if not self._episodes:
            raise ContractError("compound machine has not started an episode")
        row = self._episodes[-1]
        return CompoundRunResult(row.problem, row.initial_state_hash, self.profile,
            self.state, self.coordinator.trace.events, self._ingress_digest)

    def journal(self):
        episodes = []
        for row in self._episodes:
            state = row.coordinator.store.snapshot()
            episodes.append({"problem": row.problem.to_dict(),
                "initial_state_hash": row.initial_state_hash,
                "prior_episode_state_hash": state.prior_episode_state_hash,
                "source_profile_digest": self.profile.profile_digest,
                "ingress_digest": state.ingress_digest,
                "trace": [event.to_dict() for event in row.coordinator.trace.events],
                "proposal_batches": row.coordinator.proposal_batches, "final_state": state.to_dict()})
        body = {"schema_version": JOURNAL_SCHEMA, "source_profile": self.profile.to_dict(),
                "ingress_digest": self._ingress_digest, "episodes": episodes}
        result = {**body, "journal_digest": digest(body)}
        if sum(len(row["trace"]) for row in episodes) > MAX_JOURNAL_EVENTS:
            raise ContractError("compound journal event limit exceeded")
        if len(canonical_json(result).encode("utf-8")) > MAX_JOURNAL_BYTES:
            raise ContractError("compound journal byte limit exceeded")
        return result
