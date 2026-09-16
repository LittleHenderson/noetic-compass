"""Shared hook boundaries only; these tests do not implement native procedures."""
from dataclasses import replace
from enum import Enum

import pytest

from cncm.engine import CognitiveMachine
from cncm.kernel import StateStore, TraceFabric, TransactionCoordinator, boot_state
from cncm.model import (EvidenceStatus, Intent, IntentType, ProblemPacket, ProofStep,
                        Provenance, RejectionReason, TerminalStatus)
from cncm.semantics import has_authoritative_support
from tests._support import execute, fixture_document, fixture_packet, make_intent


class FutureIntent(str, Enum):
    REQUEST_PROCEDURE_CALL = "REQUEST_PROCEDURE_CALL"
    PUSH_ACQUISITION = "PUSH_ACQUISITION"
    SELECT_PROCEDURE = "SELECT_PROCEDURE"
    INSTALL_PROCEDURE = "INSTALL_PROCEDURE"
    RETURN_ACQUISITION = "RETURN_ACQUISITION"
    APPLY_PROCEDURE = "APPLY_PROCEDURE"
    ROLLBACK_PROCEDURE = "ROLLBACK_PROCEDURE"


class FutureProof(str, Enum):
    NATIVE_PROCEDURE_RESULT = "NATIVE_PROCEDURE_RESULT"


def coordinator(cls=TransactionCoordinator, *, packet=None, state=None, **kwargs):
    packet = fixture_packet("deduction") if packet is None else packet
    state = boot_state(packet) if state is None else state
    return cls(store=StateStore(state), trace=TraceFabric(), problem=packet, **kwargs)


def decomposition_intent(c, *, invalid=False, issuer="reasoning_engine"):
    state = c.store.snapshot()
    branch = state.branch_map()["branch-main"]
    record = c._decompose_query(state, branch)
    if invalid:
        record = replace(record, unknowns=(*record.unknowns, "unreconstructible"))
    return make_intent(c, intent_type=IntentType.RECORD_DECOMPOSITION, issuer=issuer,
                       capability="decompose", scope="branch:branch-main",
                       branch_id="branch-main", mutation={"decomposition": record.to_dict()})


@pytest.mark.parametrize("kind", list(FutureIntent))
def test_default_v01_refuses_every_extension_enum_member(kind):
    c = coordinator()
    before = c.store.snapshot()
    intent = Intent.create(intent_type=kind, issuer_subsystem="procedure_controller",
        required_capability="apply_checked_procedure", target_scope="procedural_state",
        branch_id="branch-main", goal_id=before.active_goal_id,
        precondition={"state_hash": before.state_hash}, proposed_mutation={},
        created_at_tick=before.logical_tick)
    assert not c._is_intent_type(kind)
    result = execute(c, intent)
    assert not result.authorized_intents
    assert len(result.rejected_intents) == 1
    assert result.state.branch_table == before.branch_table
    assert result.state.budget.inference_steps_remaining == before.budget.inference_steps_remaining
    assert "kernel/validation_work" not in result.trace_event.committed_mutations


def test_default_v01_unknown_issuer_has_no_extension_capabilities():
    c = coordinator()
    result = execute(c, decomposition_intent(c, issuer="procedure_controller"))
    assert not result.authorized_intents
    assert result.rejected_intents[0].reason is RejectionReason.UNAUTHORIZED_ISSUER
    assert c._allowed_intents_for("procedure_controller") is None
    assert c._expected_capabilities_for("procedure_controller", FutureIntent.APPLY_PROCEDURE) == frozenset()


def native_root_branch(*, cited_assertion=False, hypothetical=False):
    packet = fixture_packet("deduction")
    state = boot_state(packet)
    branch = state.branch_map()["branch-main"]
    proposition = packet.query.with_status(
        EvidenceStatus.HYPOTHETICAL if hypothetical else EvidenceStatus.DERIVED,
        (Provenance("untrusted_native_marker", "untrusted", "not a checked root"),))
    proof = ProofStep.create(operation=FutureProof.NATIVE_PROCEDURE_RESULT,
        premise_keys=(packet.facts[0].key,) if cited_assertion else (), rule_id=None,
        conclusion=proposition, substitution={}, branch_id=branch.branch_id, verified=True,
        provenance=proposition.provenance)
    branch = replace(branch, propositions=(*branch.propositions, proposition), proof_steps=(proof,))
    state = replace(state, branch_table=(branch,)).with_computed_hash()
    return packet, state, branch, proposition


class ExplicitRoots(TransactionCoordinator):
    """Test seam for roots already validated elsewhere; not a math checker."""
    def __init__(self, *, roots_by_branch, **kwargs):
        super().__init__(**kwargs)
        self.roots_by_branch = roots_by_branch

    def _trusted_root_keys(self, state, branch):
        return self.roots_by_branch.get(branch.branch_id, frozenset())


@pytest.mark.parametrize("cited_assertion", [False, True])
def test_native_marker_never_becomes_root_from_flag_provenance_or_cited_fact(cited_assertion):
    packet, state, branch, proposition = native_root_branch(cited_assertion=cited_assertion)
    ordinary = coordinator(packet=packet, state=state)
    assert ordinary._trusted_root_keys(state, branch) == frozenset()
    assert not ordinary._has_authoritative_support(state, branch, proposition.key)
    assert not has_authoritative_support(branch, proposition.key)
    explicit = coordinator(ExplicitRoots, packet=packet, state=state,
                           roots_by_branch={branch.branch_id: frozenset({proposition.key})})
    assert explicit._has_authoritative_support(state, branch, proposition.key)


def test_explicit_roots_cannot_create_absent_or_hypothetical_branch_content():
    _, _, branch, proposition = native_root_branch(hypothetical=True)
    assert not has_authoritative_support(branch, proposition.key,
                                         trusted_root_keys=frozenset({proposition.key}))
    missing = "absent:proposition"
    assert not has_authoritative_support(branch, missing, trusted_root_keys=frozenset({missing}))


def test_roots_are_scoped_to_the_original_branch():
    packet, state, branch, proposition = native_root_branch()
    c = coordinator(ExplicitRoots, packet=packet, state=state,
                    roots_by_branch={"foreign-branch": frozenset({proposition.key})})
    assert not c._has_authoritative_support(state, branch, proposition.key)


def test_direct_decomposition_uses_explicit_roots_consistently():
    packet, state, branch, proposition = native_root_branch()
    # No ordinary rule is available to hide the missing source of authority.
    packet = replace(packet, rules=())
    ordinary = coordinator(packet=packet, state=state)
    assert proposition.key in ordinary._decompose_query(state, branch).unknowns
    explicit = coordinator(ExplicitRoots, packet=packet, state=state,
                           roots_by_branch={branch.branch_id: frozenset({proposition.key})})
    record = explicit._decompose_query(state, branch)
    assert record.unknowns == () and record.predicted_effects == (proposition.key,)
    intent = decomposition_intent(explicit)
    result = execute(explicit, intent)
    assert len(result.authorized_intents) == 1
    assert result.state.branch_map()[branch.branch_id].decompositions[-1] == record


def horn_packet():
    doc = fixture_document("deduction")
    doc["facts"] = []
    doc["entities"].append({"entity_id": "R", "entity_type": "symbol"})
    doc["query"]["arguments"] = ["R"]
    doc["rules"].append({"rule_id": "q_implies_r", "operation": "INFER_MODUS_PONENS",
        "antecedents": [{"predicate": "holds", "arguments": ["Q"], "polarity": True}],
        "consequent": {"predicate": "holds", "arguments": ["R"], "polarity": True},
        "provenance": [{"source_type": "fixture", "source_id": "hook_horn"}]})
    return ProblemPacket.from_dict(doc)


@pytest.mark.parametrize("trusted", [False, True])
def test_engine_horn_closure_and_decomposition_keep_explicit_root_boundary(trusted):
    packet = horn_packet()
    state = boot_state(packet)
    branch = state.branch_map()["branch-main"]
    root = replace(packet.query, arguments=("P",), evidence_status=EvidenceStatus.DERIVED)
    native = ProofStep.create(operation=FutureProof.NATIVE_PROCEDURE_RESULT,
        premise_keys=(), rule_id=None, conclusion=root, substitution={},
        branch_id=branch.branch_id, verified=True, provenance=())
    branch = replace(branch, propositions=(root,), proof_steps=(native,))
    state = replace(state, branch_table=(branch,)).with_computed_hash()
    roots = {branch.branch_id: frozenset({root.key})} if trusted else {}
    c = coordinator(ExplicitRoots, packet=packet, state=state, roots_by_branch=roots)
    machine = CognitiveMachine()
    assert not machine._derive_until_stable(packet, branch.branch_id, c, {})
    after = c.store.snapshot()
    final_branch = after.branch_map()[branch.branch_id]
    assert packet.query.key in final_branch.proposition_map()
    assert c._has_authoritative_support(after, final_branch, packet.query.key) is trusted
    assert len(final_branch.proof_steps) == 3
    assert c._applicable_proofs(after, final_branch) == ()
    machine._record_decomposition(packet, branch.branch_id, c)
    recorded = c.store.snapshot().branch_map()[branch.branch_id].decompositions[-1]
    assert recorded == c._decompose_query(c.store.snapshot(), c.store.snapshot().branch_map()[branch.branch_id])


class ValidationDebitProbe(TransactionCoordinator):
    """Test-only debit using an existing counter, not native procedure execution."""
    def __init__(self, *, deny=False, **kwargs):
        super().__init__(**kwargs)
        self.observed = []
        self.excluded = frozenset()
        self.work_count = 0
        self.deny = deny

    def _prepare_validation_work(self, state, proposed, enabled, scheduled, *, excluded_ids):
        self.observed.append(("prepare", state.state_hash))
        self.excluded = excluded_ids
        work_state, denials = state, {}
        for intent in proposed:
            if intent.intent_id in excluded_ids:
                continue
            cheap_failure = self._validate_envelope(state, intent, enabled, scheduled)
            if cheap_failure is not None:
                denials[intent.intent_id] = cheap_failure
                continue
            if set(intent.mutation_dict()) != {"decomposition"}:
                denials[intent.intent_id] = self._reject(intent, RejectionReason.MALFORMED_MUTATION,
                                                         "test cheap typed shape failed")
                continue
            if self.deny:
                denials[intent.intent_id] = self._reject(intent, RejectionReason.INFERENCE_BUDGET_EXHAUSTED,
                                                         "test reservation refusal")
                continue
            self.work_count += 1
            work_state = replace(work_state, budget=replace(work_state.budget,
                inference_steps_remaining=work_state.budget.inference_steps_remaining - 2)).with_computed_hash()
            self.observed.append(("reserved", work_state.state_hash))
        return work_state, denials

    def _validate_typed_mutation(self, state, intent):
        self.observed.append(("typed", state.state_hash))
        return super()._validate_typed_mutation(state, intent)


@pytest.mark.parametrize("semantic_reject", [False, True])
def test_debit_precedes_typed_check_preserves_original_binding_and_survives_refusal(semantic_reject):
    c = coordinator(ValidationDebitProbe)
    before = c.store.snapshot()
    result = execute(c, decomposition_intent(c, invalid=semantic_reject))
    assert [name for name, _ in c.observed] == ["prepare", "reserved", "typed"]
    assert c.observed[0][1] == c.observed[2][1] == before.state_hash
    assert c.observed[1][1] != before.state_hash
    assert bool(result.authorized_intents) is (not semantic_reject)
    assert result.state.budget.inference_steps_remaining == before.budget.inference_steps_remaining - 2
    assert result.state.budget.ticks_remaining == before.budget.ticks_remaining - 1
    assert "kernel/validation_work" in result.trace_event.committed_mutations
    assert result.trace_event.pre_state_hash == before.state_hash
    assert result.trace_event.post_state_hash == result.state.state_hash
    assert result.state.computed_hash() == result.state.state_hash
    if semantic_reject:
        assert result.state.branch_table == before.branch_table


def test_work_denial_short_circuits_typed_semantic_check():
    c = coordinator(ValidationDebitProbe, deny=True)
    before = c.store.snapshot()
    result = execute(c, decomposition_intent(c))
    assert [name for name, _ in c.observed] == ["prepare"]
    assert c.work_count == 0
    assert result.rejected_intents[0].reason is RejectionReason.INFERENCE_BUDGET_EXHAUSTED
    assert result.state.budget.inference_steps_remaining == before.budget.inference_steps_remaining
    assert "kernel/validation_work" not in result.trace_event.committed_mutations


@pytest.mark.parametrize("fault", ["malformed", "duplicate", "final_tick", "unknown_issuer", "stale_hash", "typed_shape"])
def test_excluded_or_cheap_invalid_requests_never_reach_reserved_work(fault):
    c = coordinator(ValidationDebitProbe)
    if fault == "final_tick":
        original = c.store.snapshot()
        initial = replace(original, budget=replace(original.budget, ticks_remaining=1)).with_computed_hash()
        c = coordinator(ValidationDebitProbe, state=initial)
    before = c.store.snapshot()
    intent = decomposition_intent(c, issuer="unregistered" if fault == "unknown_issuer" else "reasoning_engine")
    if fault == "malformed":
        intent = replace(intent, intent_id="not-a-content-id")
    elif fault in ("stale_hash", "typed_shape"):
        intent = Intent.create(intent_type=intent.intent_type, issuer_subsystem=intent.issuer_subsystem,
            required_capability=intent.required_capability, target_scope=intent.target_scope,
            branch_id=intent.branch_id, goal_id=intent.goal_id,
            precondition={"state_hash": "0" * 64 if fault == "stale_hash" else before.state_hash},
            proposed_mutation={} if fault == "typed_shape" else intent.mutation_dict(),
            created_at_tick=intent.created_at_tick)
    result = execute(c, intent, intent) if fault == "duplicate" else execute(c, intent)
    assert not result.authorized_intents
    assert c.work_count == 0
    assert all(name not in {"reserved", "typed"} for name, _ in c.observed)
    assert result.state.budget.inference_steps_remaining == before.budget.inference_steps_remaining
    assert "kernel/validation_work" not in result.trace_event.committed_mutations
    if fault in ("malformed", "duplicate", "final_tick"):
        assert c.excluded
    if fault == "final_tick":
        assert result.state.halt_status is TerminalStatus.FAULT


def test_default_hook_has_no_debit_or_validation_marker():
    c = coordinator()
    before = c.store.snapshot()
    intent = decomposition_intent(c)
    prepared, denials = c._prepare_validation_work(before, (intent,), frozenset(),
                                                   frozenset(), excluded_ids=frozenset())
    assert prepared is before and denials == {}
    result = execute(c, intent)
    assert result.state.budget.inference_steps_remaining == before.budget.inference_steps_remaining
    assert "kernel/validation_work" not in result.trace_event.committed_mutations
