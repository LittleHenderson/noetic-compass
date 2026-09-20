"""Opt-in host for source-bound memory and conditional nested arithmetic.

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
from .semantic_kernel import (SemanticCoordinator, _TRUSTED_SEMANTIC_EPISODE,
                              boot_semantic_state)
from .semantic_model import (SemanticIntentType, SemanticProblem, SemanticState,
                             canonical_trusted_ingress, ingress_digest)
from .semantic_profile import (MAX_EPISODES, MAX_JOURNAL_BYTES, MAX_JOURNAL_EVENTS,
                               SemanticProfile, load_semantic_profile)

JOURNAL_SCHEMA = "cncm.semantic-journal/0.4"
EVIDENCE_SCHEMA = "cncm.semantic-evidence/0.4"
SUMMARY_SCHEMA = "cncm.semantic-run-summary/0.4"


@dataclass(frozen=True, slots=True)
class SemanticRunResult(NestedRunResult):
    problem: SemanticProblem
    source_profile: SemanticProfile
    final_state: SemanticState
    trusted_ingress_digest: str

    def __post_init__(self):
        if (type(self.problem) is not SemanticProblem or type(self.source_profile) is not SemanticProfile
                or type(self.final_state) is not SemanticState or type(self.trace) is not tuple):
            raise ContractError("semantic result requires typed coordinator snapshots")
        state = self.final_state
        if (state.state_hash != state.computed_hash()
                or state.native_contract_digest != self.source_profile.profile_digest
                or state.ingress_digest != self.trusted_ingress_digest
                or state.global_workspace.problem_id != self.problem.reasoning.problem_id):
            raise ContractError("semantic result state/profile/problem/ingress binding mismatch")
        previous_hash, previous_event_hash, previous_event_id = self.initial_state_hash, "", None
        for event in self.trace:
            if (type(event) is not TraceEvent or not event.sealed
                    or event.event_hash != event.computed_hash()
                    or event.pre_state_hash != previous_hash
                    or event.previous_event_hash != previous_event_hash
                    or event.parent_event_id != previous_event_id
                    or event.run_id != state.run_id):
                raise ContractError("semantic result trace binding mismatch")
            previous_hash, previous_event_hash, previous_event_id = (
                event.post_state_hash, event.event_hash, event.event_id)
        if state.state_hash != previous_hash or state.trace_head != previous_event_hash:
            raise ContractError("semantic result final trace/state binding mismatch")

    @property
    def evidence(self):
        body = NestedRunResult.evidence.fget(self)
        body.pop("evidence_digest")
        accepted = {kind.value: 0 for kind in SemanticIntentType}
        for event in self.trace:
            authorized = set(event.authorized_intent_ids)
            for intent in event.proposed_intents:
                if type(intent.intent_type) is SemanticIntentType and intent.intent_id in authorized:
                    accepted[intent.intent_type.value] += 1
        body.update(schema_version=EVIDENCE_SCHEMA,
            authorized_semantic_transitions=accepted,
            ingress_digest=self.trusted_ingress_digest,
            memory_failure=self.final_state.memory_failure,
            memory_resolution_digest=self.final_state.memory_resolution_digest,
            source_bindings=[row.to_dict() for row in self.final_state.memory_bindings],
            claim_status="CONDITIONAL_ON_RECORDED_SOURCE_BINDINGS",
            unconditional_world_truth=False)
        body["scope"].update(source_authority="caller_supplied_statement_digest_allowlist",
            external_source_authentication=False, external_fact_verification=False,
            answer_scope="arithmetic conditional on recorded source bindings")
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
    problem: SemanticProblem
    initial_state_hash: str
    coordinator: SemanticCoordinator


class SemanticMachine(NestedMachine):
    """Source-bound authority chain; no external registry or state import.

    The inherited ordinary reasoning helpers operate only after the semantic
    coordinator has checked memory resolution and completed the nested root.
    """

    def __init__(self, profile: SemanticProfile | None = None, *, trusted_ingress):
        selected = load_semantic_profile() if profile is None else profile
        if type(selected) is not SemanticProfile:
            raise ContractError("semantic machine requires a SemanticProfile")
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

    def start(self, semantic_problem, *, additional_trusted_ingress=()):
        additions = canonical_trusted_ingress(additional_trusted_ingress)
        if additions and not self._episodes:
            raise ContractError("genesis trust must be supplied to the host constructor")
        if set(additions) & set(self._trusted_ingress):
            raise ContractError("additional trusted ingress overlaps existing authority")
        next_ingress = canonical_trusted_ingress(self._trusted_ingress + additions)
        if self._episodes:
            if self.state.halt_status is TerminalStatus.RUNNING:
                raise ContractError("finish the current semantic episode before starting another")
            if self.state.rpm_stack:
                raise ContractError("unresolved nested frames prevent a new semantic episode")
        if len(self._episodes) >= MAX_EPISODES:
            raise ContractError("semantic episode limit exceeded")
        if type(semantic_problem) is SemanticProblem:
            packet = SemanticProblem.from_dict(semantic_problem.to_dict())
        elif type(semantic_problem) is dict:
            packet = SemanticProblem.from_dict(semantic_problem)
        else:
            raise ContractError("semantic start requires a SemanticProblem or its exact wire object")
        recorded = sum(len(row.coordinator.trace.events) for row in self._episodes)
        if recorded + packet.reasoning.budgets.max_ticks > MAX_JOURNAL_EVENTS:
            raise ContractError("episode tick allowance exceeds remaining semantic journal capacity")
        previous = self.state if self._episodes else None
        initial = boot_semantic_state(packet, self.profile, next_ingress,
            previous_state=previous,
            previous_trusted_ingress=self._trusted_ingress if previous is not None else None,
            _trust_previous=_TRUSTED_SEMANTIC_EPISODE if previous is not None else None)
        coordinator = SemanticCoordinator(store=StateStore(initial), trace=TraceFabric(),
            semantic_problem=packet, profile=self.profile, trusted_ingress=next_ingress)
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
            raise ContractError("semantic coordinator stopped before a quiescent root outcome")
        if root.status == "COMPLETE":
            self._finish_reasoning()
        elif root.status == "FAILED":
            self._execute(self.coordinator.failure_halt())
        else:
            raise ContractError("semantic coordinator stopped at an unfinished root")
        return self.state

    def run(self, semantic_problem=None, *, allow_acquisition=True, additional_trusted_ingress=()):
        if type(allow_acquisition) is not bool:
            raise ContractError("allow_acquisition must be a boolean")
        additions = canonical_trusted_ingress(additional_trusted_ingress)
        if additions and semantic_problem is None:
            raise ContractError("ingress extension requires a new semantic problem")
        if semantic_problem is not None:
            self.start(semantic_problem, additional_trusted_ingress=additions)
        return NestedMachine.run(self, allow_acquisition=allow_acquisition)

    def rollback(self):
        if self.state.memory_resolution_digest is None or self.state.memory_failure is not None:
            raise ContractError("semantic rollback requires checked memory resolution")
        return NestedMachine.rollback(self)

    def result(self):
        if not self._episodes:
            raise ContractError("semantic machine has not started an episode")
        row = self._episodes[-1]
        return SemanticRunResult(row.problem, row.initial_state_hash, self.profile,
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
            raise ContractError("semantic journal event limit exceeded")
        if len(canonical_json(result).encode("utf-8")) > MAX_JOURNAL_BYTES:
            raise ContractError("semantic journal byte limit exceeded")
        return result
