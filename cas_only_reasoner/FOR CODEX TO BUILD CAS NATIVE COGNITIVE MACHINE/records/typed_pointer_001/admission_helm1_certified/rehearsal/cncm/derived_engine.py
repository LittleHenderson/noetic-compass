"""Live 0.6 compound machine with checked result learning and exact RPM resume."""
from dataclasses import dataclass
from .canonical import canonical_json, digest
from .engine import CognitiveMachine
from .kernel import StateStore, TraceFabric
from .model import ContractError, TerminalStatus, TraceEvent, BranchStatus, IntentType, Provenance
from .compound_engine import CompoundMachine, CompoundRunResult
from .nested_engine import NestedMachine
from .semantic_model import canonical_trusted_ingress, ingress_digest
from .derived_model import DerivedProblem, DerivedState, DerivedIntentType, require
from .derived_profile import DerivedProfile, load_derived_profile, MAX_EPISODES, MAX_JOURNAL_EVENTS, MAX_JOURNAL_BYTES
from .derived_kernel import DerivedCoordinator, boot_derived_state, _TRUSTED_DERIVED_EPISODE

JOURNAL_SCHEMA = 'cncm.derived-journal/0.6'
EVIDENCE_SCHEMA = 'cncm.derived-evidence/0.6'


@dataclass(frozen=True, slots=True)
class DerivedRunResult(CompoundRunResult):
    problem: DerivedProblem
    source_profile: DerivedProfile
    final_state: DerivedState

    def __post_init__(self):
        require(type(self.problem) is DerivedProblem and type(self.source_profile) is DerivedProfile
                and type(self.final_state) is DerivedState and type(self.trace) is tuple, 'typed derived result required')
        state = self.final_state
        require(state.state_hash == state.computed_hash() and state.native_contract_digest == self.source_profile.profile_digest
                and state.ingress_digest == self.trusted_ingress_digest
                and state.global_workspace.problem_id == self.problem.reasoning.problem_id, 'derived result identity mismatch')
        previous, event_hash, parent = self.initial_state_hash, '', None
        for event in self.trace:
            require(type(event) is TraceEvent and event.sealed and event.event_hash == event.computed_hash()
                and event.pre_state_hash == previous and event.previous_event_hash == event_hash
                and event.parent_event_id == parent and event.run_id == state.run_id, 'derived result trace mismatch')
            previous,event_hash,parent = event.post_state_hash,event.event_hash,event.event_id
        require(state.state_hash == previous and state.trace_head == event_hash, 'derived final trace mismatch')

    @property
    def evidence(self):
        body = dict(CompoundRunResult.evidence.fget(self))
        body.pop('evidence_digest')
        counts = {k.value:0 for k in DerivedIntentType}
        for event in self.trace:
            for intent in event.proposed_intents:
                if type(intent.intent_type) is DerivedIntentType and intent.intent_id in event.authorized_intent_ids:
                    counts[intent.intent_type.value] += 1
        body.update(schema_version=EVIDENCE_SCHEMA, derived_records=[r.to_dict() for r in self.final_state.derived_records],
            derived_bindings=[list(r) for r in self.final_state.derived_bindings], derived_failure=self.final_state.derived_failure,
            derived_stored=self.final_state.derived_stored, authorized_derived_transitions=counts,
            claim_status='CHECKED_FORMAL_CONSEQUENCE_CONDITIONAL_ON_RECORDED_SUPPORT',
            world_fact_verification=False, generator_regeneration_is_verification=False)
        return {**body,'evidence_digest':digest(body)}

    def summary(self):
        body = dict(CompoundRunResult.summary(self))
        body.update(schema_version='cncm.derived-run-summary/0.6', derived_failure=self.final_state.derived_failure,
                    derived_stored=self.final_state.derived_stored,
                    claim_status='CHECKED_FORMAL_CONSEQUENCE_CONDITIONAL_ON_RECORDED_SUPPORT')
        return body


@dataclass(frozen=True, slots=True)
class _Episode:
    problem: DerivedProblem
    initial_state_hash: str
    coordinator: DerivedCoordinator


class DerivedMachine(CompoundMachine):
    def __init__(self, profile=None, *, trusted_ingress):
        self._profile = load_derived_profile() if profile is None else profile
        require(type(self._profile) is DerivedProfile, 'typed derived source profile required')
        self._trusted_ingress = canonical_trusted_ingress(trusted_ingress)
        self._initial_trusted_ingress = self._trusted_ingress
        self._ingress_digest = ingress_digest(self._trusted_ingress)
        self._episodes = []
        self._reasoner = CognitiveMachine()

    def start(self, derived_problem, *, additional_trusted_ingress=()):
        additions = canonical_trusted_ingress(additional_trusted_ingress)
        require(not additions or self._episodes, 'genesis trust belongs in host constructor')
        require(not set(additions) & set(self._trusted_ingress), 'additional ingress overlaps existing authority')
        ingress = canonical_trusted_ingress(self._trusted_ingress+additions)
        if self._episodes:
            require(self.state.halt_status is not TerminalStatus.RUNNING and not self.state.rpm_stack,
                    'finish current episode and return every saved parent before starting another')
        require(len(self._episodes) < MAX_EPISODES, 'derived episode limit exceeded')
        packet = DerivedProblem.from_dict(derived_problem.to_dict() if type(derived_problem) is DerivedProblem else derived_problem)
        count = sum(len(e.coordinator.trace.events) for e in self._episodes)
        require(count+packet.reasoning.budgets.max_ticks <= MAX_JOURNAL_EVENTS, 'derived journal tick capacity exceeded')
        previous = self.state if self._episodes else None
        initial = boot_derived_state(packet,self.profile,ingress,previous_state=previous,
            previous_trusted_ingress=self._trusted_ingress if previous else None,
            _trust_previous=_TRUSTED_DERIVED_EPISODE if previous else None)
        coordinator = DerivedCoordinator(store=StateStore(initial),trace=TraceFabric(),derived_problem=packet,
            profile=self.profile,trusted_ingress=ingress)
        self._trusted_ingress,self._ingress_digest = ingress,ingress_digest(ingress)
        self._episodes.append(_Episode(packet,initial.state_hash,coordinator))
        return self.state

    def advance(self, *, allow_acquisition=True, allow_generation=True):
        require(type(allow_acquisition) is bool and type(allow_generation) is bool, 'policy switches must be boolean')
        if self.state.halt_status is not TerminalStatus.RUNNING: return self.state
        if self._reserve_halt(): return self.state
        intent = self.coordinator.next_intent(allow_acquisition=allow_acquisition,allow_generation=allow_generation)
        if intent is not None:
            self._execute(intent)
            return self.state
        if self.state.derived_failure is not None or self.state.memory_failure is not None:
            self._execute(self.coordinator.failure_halt())
            return self.state
        if self.state.commitment_state.decision_status == 'COMMITTED':
            self._reasoner._halt(self.coordinator,TerminalStatus.CONCLUDED)
            return self.state
        root = self.coordinator.root_call()
        require(root is not None and not self.state.rpm_stack, 'derived coordinator stopped before quiescent compound outcome')
        if root.status == 'COMPLETE': self._finish_reasoning()
        elif root.status == 'FAILED': self._execute(self.coordinator.failure_halt())
        else: raise ContractError('derived coordinator stopped at unfinished compound root')
        return self.state

    def run(self, derived_problem=None, *, allow_acquisition=True, allow_generation=True, additional_trusted_ingress=()):
        require(type(allow_acquisition) is bool and type(allow_generation) is bool, 'policy switches must be boolean')
        require(derived_problem is not None or not additional_trusted_ingress, 'ingress extension requires a new episode')
        if derived_problem is not None: self.start(derived_problem,additional_trusted_ingress=additional_trusted_ingress)
        require(self._episodes, 'derived machine not started')
        while self.state.halt_status is TerminalStatus.RUNNING:
            before = self.state.state_hash
            self.advance(allow_acquisition=allow_acquisition,allow_generation=allow_generation)
            require(self.state.state_hash != before, 'derived machine made no transition')
        return self.result()

    def result(self):
        require(self._episodes, 'derived machine not started')
        row = self._episodes[-1]
        return DerivedRunResult(row.problem,row.initial_state_hash,self.profile,self.state,self.coordinator.trace.events,self._ingress_digest)

    def journal(self):
        episodes = []
        for row in self._episodes:
            state = row.coordinator.store.snapshot()
            episodes.append({'problem':row.problem.to_dict(),'initial_state_hash':row.initial_state_hash,
                'prior_episode_state_hash':state.prior_episode_state_hash,'source_profile_digest':self.profile.profile_digest,
                'ingress_digest':state.ingress_digest,'trace':[e.to_dict() for e in row.coordinator.trace.events],
                'proposal_batches':row.coordinator.proposal_batches,'final_state':state.to_dict()})
        body = {'schema_version':JOURNAL_SCHEMA,'source_profile':self.profile.to_dict(),'ingress_digest':self._ingress_digest,'episodes':episodes}
        result = {**body,'journal_digest':digest(body)}
        require(sum(len(r['trace']) for r in episodes) <= MAX_JOURNAL_EVENTS and len(canonical_json(result).encode()) <= MAX_JOURNAL_BYTES,
                'derived journal bound exceeded')
        return result

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
                return
            elif self.state.halt_status is TerminalStatus.RUNNING:
                self._ordinary_refusal()
        except ContractError:
            if (self.state.halt_status is TerminalStatus.RUNNING and coordinator.trace.events
                    and coordinator.trace.events[-1].rejected_intents):
                self._ordinary_refusal()
            else:
                raise
