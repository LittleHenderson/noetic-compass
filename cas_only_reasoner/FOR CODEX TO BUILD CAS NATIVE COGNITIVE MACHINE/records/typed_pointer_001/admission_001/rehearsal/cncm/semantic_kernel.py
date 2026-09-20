"""Governed sourced memory feeding the frozen nested equation coordinator.

The memory verifier checks source and substitution obligations; it does not
certify external facts. Only this coordinator writes memory or admits equations.
"""
from dataclasses import fields, replace

from .canonical import canonical_json, content_id, digest
from .kernel import TransactionCoordinator, _ValidatedIntent, boot_state
from .model import (ContractError, Intent, IntentType, MachineState, Provenance,
                    RejectionReason, TerminalStatus)
from .native_model import NativeBudget
from .nested_kernel import NestedCoordinator, nested_intent, require
from .nested_model import NestedIntentType, NestedProofStep
from .semantic_model import (SemanticProblem, SemanticState, SemanticRecord,
    SemanticIntentType, VERSION, CONSTITUTION, canonical_trusted_ingress)
from .semantic_profile import SemanticProfile, SEMANTIC_AUTHORITIES, SEMANTIC_WORK_COSTS
from .semantic_verification import validate_source_update, resolve_memory, verify_resolution

_TRUSTED_SEMANTIC_EPISODE = object()


def boot_semantic_state(problem, profile, trusted_ingress, previous_state=None, *,
                        previous_trusted_ingress=None, _trust_previous=None):
    require(type(problem) is SemanticProblem and type(profile) is SemanticProfile,
            "semantic boot requires exact typed contracts")
    ingress = canonical_trusted_ingress(trusted_ingress)
    ingress_hash = digest(list(ingress))
    if previous_state is not None:
        previous_ingress = canonical_trusted_ingress(
            ingress if previous_trusted_ingress is None else previous_trusted_ingress)
        require(_trust_previous is _TRUSTED_SEMANTIC_EPISODE,
                "external semantic snapshot import prohibited")
        require(type(previous_state) is SemanticState
                and previous_state.halt_status is not TerminalStatus.RUNNING
                and not previous_state.rpm_stack, "predecessor must be terminal and quiescent")
        require(previous_state.state_hash == previous_state.computed_hash()
                and previous_state.native_contract_digest == profile.profile_digest
                and previous_state.ingress_digest == digest(list(previous_ingress))
                and set(previous_ingress) <= set(ingress),
                "predecessor source/state/ingress mismatch")
    else:
        require(previous_trusted_ingress is None, "genesis cannot name predecessor ingress")
    base = boot_state(problem.reasoning)
    values = {field.name: getattr(base, field.name) for field in fields(MachineState)}
    prior = previous_state.state_hash if previous_state else None
    values.update(runtime_version=VERSION, constitution_revision=CONSTITUTION,
        run_id=content_id("semantic-run", {"problem": problem.input_hash,
            "profile": profile.profile_digest, "ingress": ingress_hash,
            "prior_episode_state_hash": prior}), state_hash="")
    return SemanticState(**values,
        procedural_artifacts=previous_state.procedural_artifacts if previous_state else (),
        procedure_heads=previous_state.procedure_heads if previous_state else (),
        native_records=previous_state.native_records if previous_state else (),
        native_calls=(), native_budget=problem.budget, native_contract_digest=profile.profile_digest,
        prior_episode_state_hash=prior,
        memory_statements=previous_state.memory_statements if previous_state else (),
        semantic_records=previous_state.semantic_records if previous_state else (),
        memory_bindings=(), memory_update_index=0, memory_failure=None,
        memory_resolution_digest=None, ingress_digest=ingress_hash).with_computed_hash()


def semantic_intent(coordinator, kind, mutation):
    require(type(kind) is SemanticIntentType, "semantic intent enum required")
    issuer, capability = SEMANTIC_AUTHORITIES[kind.value]
    state = coordinator.store.snapshot()
    return Intent.create(intent_type=kind, issuer_subsystem=issuer,
        required_capability=capability, target_scope="semantic_memory",
        branch_id="branch-main", goal_id=state.active_goal_id,
        precondition={"state_hash": state.state_hash}, proposed_mutation=mutation,
        created_at_tick=state.logical_tick,
        provenance=(Provenance("semantic_controller", "semantic-memory-0.4", "proposal only"),))


class SemanticCoordinator(NestedCoordinator):
    def __init__(self, *, store, trace, semantic_problem, profile, trusted_ingress):
        ingress = canonical_trusted_ingress(trusted_ingress)
        state = store.snapshot()
        require(type(semantic_problem) is SemanticProblem and type(profile) is SemanticProfile,
                "typed semantic contracts required")
        require(type(state) is SemanticState and state.runtime_version == VERSION
                and state.native_contract_digest == profile.profile_digest
                and state.ingress_digest == digest(list(ingress))
                and state.state_hash == state.computed_hash(), "semantic state/profile/ingress mismatch")
        self.semantic_problem, self.profile, self.trusted_ingress = semantic_problem, profile, ingress
        self._work_cache = {}
        self._semantic_work = {}
        self._proposal_batches = []
        self._pending_proposal_batch = ()
        TransactionCoordinator.__init__(self, store=store, trace=trace, problem=semantic_problem.reasoning)

    @property
    def nested_problem(self):
        state = self.store.snapshot()
        if state.memory_resolution_digest is None:
            return self.semantic_problem.placeholder_problem()
        return self.semantic_problem.resolved_problem(state.memory_bindings)

    def _is_intent_type(self, value):
        return type(value) is SemanticIntentType or super()._is_intent_type(value)

    def _allowed_intents_for(self, issuer):
        return (super()._allowed_intents_for(issuer) or frozenset()) | frozenset(
            SemanticIntentType(name) for name, pair in SEMANTIC_AUTHORITIES.items() if pair[0] == issuer)

    def _expected_capabilities_for(self, issuer, kind):
        if type(kind) is SemanticIntentType:
            expected, capability = SEMANTIC_AUTHORITIES[kind.value]
            return frozenset((capability,)) if issuer == expected else frozenset()
        return super()._expected_capabilities_for(issuer, kind)

    @staticmethod
    def _scope(kind):
        return "semantic_memory" if type(kind) is SemanticIntentType else NestedCoordinator._scope(kind)

    def _memory_expected(self, state):
        if state.memory_failure is not None:
            return None
        index = state.memory_update_index
        if index < len(self.semantic_problem.updates):
            return SemanticIntentType.STORE_SOURCE, {
                "index": index, "statement": self.semantic_problem.updates[index].to_dict()}
        bound = {canonical_json(row.ref.to_dict()) for row in state.memory_bindings}
        for ref in self.semantic_problem.references:
            if canonical_json(ref.to_dict()) not in bound:
                return SemanticIntentType.RECALL_MEMORY, {"reference": ref.to_dict()}
        if state.memory_resolution_digest is None:
            return SemanticIntentType.CHECK_MEMORY_RESOLUTION, {
                "problem_hash": self.semantic_problem.input_hash,
                "resolved_problem_hash": self.semantic_problem.resolved_problem(state.memory_bindings).input_hash}
        return None

    def next_intent(self, *, allow_acquisition=True):
        require(type(allow_acquisition) is bool, "acquisition switch must be boolean")
        state = self.store.snapshot()
        if state.memory_failure is not None:
            return None
        expected = self._memory_expected(state)
        if expected is not None:
            return semantic_intent(self, *expected)
        return super().next_intent(allow_acquisition=allow_acquisition)

    def _check_memory(self, state, intent):
        require(state.halt_status is TerminalStatus.RUNNING
                and state.commitment_state.decision_status != "COMMITTED", "semantic episode is closed")
        require(not state.native_calls and not state.rpm_stack, "memory changes require pre-call quiescence")
        require(intent.target_scope == "semantic_memory" and intent.branch_id == "branch-main"
                and intent.goal_id == state.active_goal_id, "semantic target/goal/branch mismatch")
        require(len(state.semantic_records) <= 1020, "semantic record capacity exhausted")
        expected = self._memory_expected(state)
        require(expected is not None and intent.intent_type is expected[0]
                and intent.mutation_dict() == expected[1], "semantic transition does not reconstruct")

    def _semantic_record(self, state, kind, body):
        return SemanticRecord.create(kind, {"run_id": state.run_id, "tick": state.logical_tick, **body})

    def _prepare_validation_work(self, state, proposed, enabled, scheduled, *, excluded_ids):
        self._semantic_work = {}
        memory = [i for i in proposed if type(i.intent_type) is SemanticIntentType]
        if not memory:
            if (state.memory_resolution_digest is None or state.memory_failure is not None):
                blocked = [i for i in proposed if type(i.intent_type) is NestedIntentType]
                if blocked:
                    return state, {i.intent_id: self._reject(i, RejectionReason.BRANCH_NOT_WRITABLE,
                        "nested execution requires checked memory resolution") for i in blocked}
            return super()._prepare_validation_work(state, proposed, enabled, scheduled, excluded_ids=excluded_ids)
        if len(proposed) != 1:
            return state, {i.intent_id: self._reject(i, RejectionReason.INTENT_CONFLICT,
                "semantic transitions require one intent") for i in proposed}
        intent = memory[0]
        if intent.intent_id in excluded_ids or self._validate_envelope(state, intent, enabled, scheduled) is not None:
            return state, {}
        try:
            self._check_memory(state, intent)
        except (ContractError, KeyError, TypeError, ValueError) as error:
            return state, {intent.intent_id: self._reject(intent, RejectionReason.MALFORMED_MUTATION, str(error))}
        cost = SEMANTIC_WORK_COSTS[intent.intent_type.value]
        before = state.native_budget
        if before.instructions_remaining < cost[0] or before.checker_calls_remaining < cost[1]:
            record = self._semantic_record(state, "WORK_RESERVATION", {
                "intent_id": intent.intent_id, "operation": intent.intent_type.value,
                "before": before.to_dict(), "after": before.to_dict(),
                "instructions_allocated": 0, "checker_calls_allocated": 0,
                "failure": "BUDGET_EXHAUSTED", "receipt": None})
            return replace(state, memory_failure="BUDGET_EXHAUSTED",
                semantic_records=state.semantic_records + (record,)), {
                intent.intent_id: self._reject(intent, RejectionReason.INFERENCE_BUDGET_EXHAUSTED,
                                              "semantic work budget exhausted before checking")}
        after = NativeBudget(before.instructions_remaining - cost[0], before.checker_calls_remaining - cost[1])
        binding = None
        verifier_fault = None
        arguments = {"source_profile_digest": self.profile.profile_digest}
        try:
            if intent.intent_type is SemanticIntentType.STORE_SOURCE:
                statement = self.semantic_problem.updates[state.memory_update_index]
                receipt = validate_source_update(state.memory_statements, statement, self.trusted_ingress, **arguments)
            elif intent.intent_type is SemanticIntentType.RECALL_MEMORY:
                ref = next(ref for ref in self.semantic_problem.references
                           if ref.to_dict() == intent.mutation_dict()["reference"])
                binding, receipt = resolve_memory(state.memory_statements, ref, self.trusted_ingress, **arguments)
            else:
                resolved = self.semantic_problem.resolved_problem(state.memory_bindings)
                receipt = verify_resolution(self.semantic_problem, state.memory_bindings, resolved,
                                            state.memory_statements, self.trusted_ingress, **arguments)
            require(type(receipt) is dict and receipt.get("receipt_digest") == digest(
                {k:v for k,v in receipt.items() if k != "receipt_digest"}), "semantic verifier receipt malformed")
            failure = None if receipt["status"] == "VALID" else receipt["reason"]
            if intent.intent_type is SemanticIntentType.RECALL_MEMORY and failure is None:
                require(binding is not None and binding.receipt_digest == receipt["receipt_digest"],
                        "semantic verifier omitted exact recall binding")
                require(binding.ref == ref and receipt["bindings"]["binding"] == {
                    "ref":binding.ref.to_dict(), "value":binding.value,
                    "statement_digests":list(binding.statement_digests), "statuses":list(binding.statuses)},
                    "semantic recall binding/receipt/reference mismatch")
        except (ContractError, KeyError, TypeError, ValueError, StopIteration) as error:
            receipt = None
            verifier_fault = str(error)
            failure = "VERIFIER_FAULT"
        self._semantic_work[intent.intent_id] = {"receipt": receipt, "binding": binding, "failure": failure}
        record = self._semantic_record(state, "WORK_RESERVATION", {
            "intent_id": intent.intent_id, "operation": intent.intent_type.value,
            "before": before.to_dict(), "after": after.to_dict(),
            "instructions_allocated": cost[0], "checker_calls_allocated": cost[1],
            "failure": failure, "receipt": receipt, "verifier_fault": verifier_fault})
        return replace(state, native_budget=after, memory_failure=failure,
                       semantic_records=state.semantic_records + (record,)), {}

    def _validate_typed_mutation(self, state, intent):
        if type(intent.intent_type) is SemanticIntentType:
            self._check_memory(state, intent)
            cache = self._semantic_work.get(intent.intent_id)
            require(cache is not None, "semantic work was not reserved")
            if cache["failure"]:
                return self._reject(intent, RejectionReason.INVALID_PROOF, cache["failure"])
            return _ValidatedIntent(intent, "semantic_memory")
        if intent.intent_type is IntentType.HALT:
            diagnostics = intent.mutation_dict().get("diagnostics")
            if isinstance(diagnostics, list) and diagnostics[:1] == ["semantic_memory_failure"]:
                require(intent.mutation_dict() == self.failure_halt().mutation_dict(),
                        "semantic failure halt does not reconstruct")
                return _ValidatedIntent(intent, "halt_status")
        elif state.memory_resolution_digest is None or state.memory_failure is not None:
            return self._reject(intent, RejectionReason.BRANCH_NOT_WRITABLE,
                                "parent work waits for checked semantic resolution")
        return super()._validate_typed_mutation(state, intent)

    def _apply_intent(self, state, intent):
        if type(intent.intent_type) is not SemanticIntentType:
            return super()._apply_intent(state, intent)
        cache = self._semantic_work[intent.intent_id]
        receipt = cache["receipt"]
        if intent.intent_type is SemanticIntentType.STORE_SOURCE:
            statement = self.semantic_problem.updates[state.memory_update_index]
            record = self._semantic_record(state, "STORE", {
                "statement_digest": statement.statement_digest, "receipt": receipt})
            return replace(state, memory_statements=state.memory_statements + (statement,),
                memory_update_index=state.memory_update_index + 1,
                semantic_records=state.semantic_records + (record,))
        if intent.intent_type is SemanticIntentType.RECALL_MEMORY:
            binding = cache["binding"]
            record = self._semantic_record(state, "RECALL", {"binding": binding.to_dict(), "receipt": receipt})
            return replace(state, memory_bindings=state.memory_bindings + (binding,),
                           semantic_records=state.semantic_records + (record,))
        record = self._semantic_record(state, "RESOLUTION", {
            "problem_hash": self.semantic_problem.input_hash,
            "resolved_problem": self.semantic_problem.resolved_problem(state.memory_bindings).to_dict(),
            "receipt": receipt})
        return replace(state, memory_resolution_digest=receipt["receipt_digest"],
                       semantic_records=state.semantic_records + (record,))

    def _checked_proof(self, call, record):
        proof = super()._checked_proof(call, record)
        state = self.store.snapshot()
        require(state.memory_resolution_digest is not None, "checked result lacks memory resolution")
        provenance = proof.provenance + (Provenance("semantic_resolution", state.memory_resolution_digest,
            "arithmetic is conditional on recorded source attestations"),)
        conclusion = replace(proof.conclusion, provenance=provenance)
        return NestedProofStep.create_checked(conclusion=conclusion, branch_id="branch-main",
                                             execution_digest=record.record_digest, provenance=provenance)

    def failure_halt(self):
        state = self.store.snapshot()
        if state.memory_failure is None:
            return super().failure_halt()
        require(not state.native_calls and not state.rpm_stack, "memory failure must precede execution")
        status = TerminalStatus.BUDGET_EXHAUSTED if state.memory_failure == "BUDGET_EXHAUSTED" else TerminalStatus.NEEDS_INFORMATION
        return Intent.create(intent_type=IntentType.HALT, issuer_subsystem="halting_controller",
            required_capability="request_typed_halt", target_scope="halt_status", branch_id=None,
            goal_id=state.active_goal_id, precondition={"state_hash":state.state_hash},
            proposed_mutation={"status":status.value, "lacunae":["semantic_memory"],
                "diagnostics":["semantic_memory_failure", state.memory_failure]},
            created_at_tick=state.logical_tick, provenance=())
