"""Direct coordinator attacks with explicitly simulated source-profile identity.

These pure tests exercise real bounded selection/checking and transitions.
The profile fixture is deliberately not evidence of source custody or a cloud run.
"""
from copy import deepcopy
from dataclasses import replace
from enum import Enum
from unittest.mock import patch

import pytest

from cncm.canonical import digest
from cncm.engine import CognitiveMachine
from cncm.kernel import StateStore, TraceFabric
from cncm.model import (
    ContractError, EvidenceStatus, InferenceOperation, Intent, IntentType,
    ProofStep, Provenance, RejectionReason, Rule, TerminalStatus,
)
from cncm.native_kernel import (
    NativeCoordinator, boot_native_state, expected_acquisition_frame, native_intent,
)
from cncm.native_model import CAPABILITY, NativeBudget, NativeIntentType, NativeState
from cncm.native_profile import NativeProfile, SOURCE_FILES, authority_policy
from cncm.procedural_substrate import make_candidate
from tests.test_native_model import problem as model_problem


def simulated_profile():
    """Correct profile shape; each digest explicitly denotes a test simulation."""
    return NativeProfile(tuple((name, len(name), digest({
        "identity_kind": "SIMULATED_SOURCE_IDENTITY_FOR_PURE_TEST_ONLY", "path": name}))
        for name in SOURCE_FILES), digest(authority_policy()))


def native_problem(*, budget=None, asserted_done=False):
    packet = model_problem()
    source = Provenance("test", "native-kernel-engineering-fixture")
    checked = replace(packet.reasoning.query, predicate=packet.call.result_predicate)
    rule = Rule("checked-to-done", InferenceOperation.INFER_MODUS_PONENS,
                (checked,), packet.reasoning.query, (source,))
    facts = ((packet.reasoning.query.with_status(EvidenceStatus.ASSERTED, (source,)),)
             if asserted_done else ())
    return replace(packet, reasoning=replace(packet.reasoning, facts=facts, rules=(rule,)),
                   budget=NativeBudget() if budget is None else budget)


def coordinator(*, budget=None, asserted_done=False):
    packet = native_problem(budget=budget, asserted_done=asserted_done)
    profile = simulated_profile()
    return NativeCoordinator(store=StateStore(boot_native_state(packet, profile)),
        trace=TraceFabric(), native_problem=packet, profile=profile)


def execute(c, intent):
    return c.execute(enabled_components=(intent.issuer_subsystem,),
                     scheduled_components=(intent.issuer_subsystem,), intents=(intent,))


def send(c, kind, mutation):
    return execute(c, native_intent(c, kind, mutation))


def require_accepted(result):
    assert result.authorized_intents, [(r.reason.value, r.detail) for r in result.rejected_intents]
    assert not result.rejected_intents
    assert result.state.state_hash == result.state.computed_hash()
    assert result.trace_event.post_state_hash == result.state.state_hash
    assert result.trace_event.event_hash == result.state.trace_head
    return result


def request_and_push(c):
    spec = c.native_problem.call
    require_accepted(send(c, NativeIntentType.REQUEST_PROCEDURE_CALL, {"call": spec.to_dict()}))
    frame = expected_acquisition_frame(c.store.snapshot(), spec)
    require_accepted(send(c, NativeIntentType.PUSH_ACQUISITION,
        {"call_id": spec.call_id, "frame": frame.to_dict()}))
    return frame


def select(c):
    require_accepted(send(c, NativeIntentType.SELECT_PROCEDURE, {"call_id": c.native_problem.call.call_id}))
    return c.selected_artifact(c.native_problem.call.call_id)


def install(c, artifact=None, qualification_digest=None):
    return send(c, NativeIntentType.INSTALL_PROCEDURE, {
        "call_id": c.native_problem.call.call_id,
        "artifact": (artifact or make_candidate()).to_dict(),
        "qualification_digest": qualification_digest})


def acquire(c):
    frame = request_and_push(c)
    artifact = select(c)
    require_accepted(install(c, artifact))
    require_accepted(send(c, NativeIntentType.RETURN_ACQUISITION, {
        "call_id": c.native_problem.call.call_id, "frame_id": frame.frame_id,
        "artifact_sha256": artifact.artifact_sha256, "success": True, "failure": None}))
    return artifact


def apply(c, artifact):
    return send(c, NativeIntentType.APPLY_PROCEDURE, {
        "call_id": c.native_problem.call.call_id, "artifact_sha256": artifact.artifact_sha256})


def remake(intent, **changes):
    body = dict(intent_type=intent.intent_type, issuer_subsystem=intent.issuer_subsystem,
        required_capability=intent.required_capability, target_scope=intent.target_scope,
        branch_id=intent.branch_id, goal_id=intent.goal_id, precondition=intent.precondition_dict(),
        proposed_mutation=intent.mutation_dict(), created_at_tick=intent.created_at_tick,
        provenance=intent.provenance)
    body.update(changes)
    return Intent.create(**body)


def test_actual_acquire_apply_and_ordinary_reasoning_commit():
    c = coordinator()
    artifact = acquire(c)
    before_apply = c.store.snapshot()
    assert before_apply.native_budget == NativeBudget(308, 94)
    assert not before_apply.rpm_stack
    assert before_apply.active_goal_id == c.native_problem.call.goal_id
    assert before_apply.native_calls[0].status == "READY"
    require_accepted(apply(c, artifact))
    state = c.store.snapshot()
    assert state.native_calls[0].status == "COMPLETE"
    assert state.native_calls[0].output == "7"
    assert state.native_budget == NativeBudget(302, 93)
    assert c._has_authoritative_support(state, state.branch_table[0], c.native_problem.call.result_key)
    assert NativeState.from_dict(state.to_dict()).to_dict() == state.to_dict()
    # The existing reasoning engine still derives/selects/commits the parent query.
    reasoner = CognitiveMachine()
    packet = c.native_problem.reasoning
    reasoner._record_decomposition(packet, "branch-main", c)
    reasoner._derive_until_stable(packet, "branch-main", c, {})
    reasoner._record_decomposition(packet, "branch-main", c)
    winner = reasoner._classify_and_compare(packet, c, ("branch-main",))
    assert winner == "branch-main"
    assert reasoner._commit_winner(packet, winner, c)
    assert reasoner._halt(c, TerminalStatus.CONCLUDED)
    assert c.store.snapshot().commitment_state.conclusion.key == packet.query.key


def test_failed_wrong_add_qualification_before_selection_is_charged_and_retained():
    c = coordinator()
    request_and_push(c)
    before = c.store.snapshot()
    result = install(c, make_candidate(combine="ADD_EXACT"))
    assert not result.authorized_intents
    assert result.rejected_intents[0].reason is RejectionReason.INVALID_PROOF
    assert result.state.native_budget == NativeBudget(452, 118)
    assert result.state.procedural_artifacts == before.procedural_artifacts == ()
    assert result.state.procedure_heads == ()
    assert result.state.rpm_stack == before.rpm_stack
    record = result.state.native_records[-1]
    assert record.kind == "WORK_RESERVATION"
    assert record.body_dict()["failed_report"]["status"] == "ENGINEERING_PANEL_FAILED"
    assert record.body_dict()["instructions_allocated"] == 60
    assert record.body_dict()["checker_calls_allocated"] == 10
    assert "kernel/validation_work" in result.trace_event.committed_mutations


def test_forged_qualification_digest_is_charged_and_rejected():
    c = coordinator()
    request_and_push(c)
    result = install(c, qualification_digest="0" * 64)
    assert not result.authorized_intents
    assert "digest" in result.rejected_intents[0].detail
    assert result.state.native_budget == NativeBudget(452, 118)
    assert result.state.native_records[-1].body_dict()["failed_report"]["status"] == "ENGINEERING_PANEL_PASSED"
    assert not result.state.procedural_artifacts


def test_selected_candidate_substitution_rejected_before_qualification():
    c = coordinator()
    request_and_push(c)
    select(c)
    before = c.store.snapshot()
    with patch("cncm.native_kernel.qualify_procedure", side_effect=AssertionError("qualification ran")):
        result = install(c, make_candidate(combine="ADD_EXACT"))
    assert not result.authorized_intents
    assert "changed the selected" in result.rejected_intents[0].detail
    assert result.state.native_budget == before.native_budget
    assert result.state.native_records == before.native_records


@pytest.mark.parametrize("budget,kind", [(NativeBudget(59, 10), "INSTALL"), (NativeBudget(60, 9), "INSTALL"),
                                        (NativeBudget(143, 24), "SELECT"), (NativeBudget(144, 23), "SELECT")])
def test_partial_work_budget_does_not_run_executor_or_checker(budget, kind):
    c = coordinator(budget=budget)
    request_and_push(c)
    before = c.store.snapshot()
    with patch("cncm.native_kernel.qualify_procedure", side_effect=AssertionError("qualification ran")), \
         patch("cncm.native_kernel.select_finite_candidate", side_effect=AssertionError("selection ran")):
        result = (install(c) if kind == "INSTALL" else
                  send(c, NativeIntentType.SELECT_PROCEDURE, {"call_id": c.native_problem.call.call_id}))
    assert not result.authorized_intents
    assert result.rejected_intents[0].reason is RejectionReason.INFERENCE_BUDGET_EXHAUSTED
    assert result.state.native_budget == budget
    assert result.state.native_records == before.native_records


@pytest.mark.parametrize("changes", [{"branch_id": "branch-other"}, {"goal_id": "goal-other"},
                                      {"issuer_subsystem": "reasoning_engine"}, {"target_scope": "native_calls"}])
def test_wrong_envelope_denied_before_work(changes):
    c = coordinator()
    request_and_push(c)
    intent = native_intent(c, NativeIntentType.INSTALL_PROCEDURE,
        {"call_id": c.native_problem.call.call_id, "artifact": make_candidate().to_dict(), "qualification_digest": None})
    before = c.store.snapshot()
    with patch("cncm.native_kernel.qualify_procedure", side_effect=AssertionError("qualification ran")):
        result = execute(c, remake(intent, **changes))
    assert not result.authorized_intents
    assert result.state.native_budget == before.native_budget


def test_stale_intent_does_not_run_work():
    c = coordinator()
    request_and_push(c)
    stale = native_intent(c, NativeIntentType.INSTALL_PROCEDURE,
        {"call_id": c.native_problem.call.call_id, "artifact": make_candidate().to_dict(), "qualification_digest": None})
    select(c)
    before = c.store.snapshot()
    with patch("cncm.native_kernel.qualify_procedure", side_effect=AssertionError("qualification ran")):
        result = execute(c, stale)
    assert not result.authorized_intents
    assert result.rejected_intents[0].reason is RejectionReason.STALE_SNAPSHOT
    assert result.state.native_budget == before.native_budget


def test_unsupported_executor_version_is_rejected_before_work():
    c = coordinator()
    request_and_push(c)
    artifact = make_candidate().to_dict()
    artifact["executor_revision"] = "unreviewed-executor/99"
    with patch("cncm.native_kernel.qualify_procedure", side_effect=AssertionError("qualification ran")):
        result = send(c, NativeIntentType.INSTALL_PROCEDURE,
            {"call_id": c.native_problem.call.call_id, "artifact": artifact, "qualification_digest": None})
    assert not result.authorized_intents
    assert result.state.native_budget == c.native_problem.budget


def test_wrong_return_frame_does_not_resume_or_refill():
    c = coordinator()
    request_and_push(c)
    require_accepted(install(c))
    before = c.store.snapshot()
    result = send(c, NativeIntentType.RETURN_ACQUISITION, {
        "call_id": c.native_problem.call.call_id, "frame_id": "wrong-frame",
        "artifact_sha256": make_candidate().artifact_sha256, "success": True, "failure": None})
    assert not result.authorized_intents
    assert result.state.rpm_stack == before.rpm_stack
    assert result.state.active_goal_id == before.active_goal_id
    assert result.state.native_budget == before.native_budget


def test_suspended_parent_write_is_rejected():
    c = coordinator()
    request_and_push(c)
    state = c.store.snapshot()
    record = c._decompose_query(state, state.branch_table[0])
    intent = Intent.create(intent_type=IntentType.RECORD_DECOMPOSITION,
        issuer_subsystem="reasoning_engine", required_capability="decompose", target_scope="branch:branch-main",
        branch_id="branch-main", goal_id=state.active_goal_id, precondition={"state_hash": state.state_hash},
        proposed_mutation={"decomposition": record.to_dict()}, created_at_tick=state.logical_tick)
    result = execute(c, intent)
    assert not result.authorized_intents
    assert result.rejected_intents[0].reason is RejectionReason.STACK_FAULT
    assert result.state.branch_table == state.branch_table


def test_forged_native_proof_marker_is_not_ordinary_derivation_authority():
    c = coordinator()
    state = c.store.snapshot()
    class ForgedOperation(str, Enum):
        CHECKED_PROCEDURE = "CHECKED_PROCEDURE"
    forged = ProofStep.create(operation=ForgedOperation.CHECKED_PROCEDURE, premise_keys=(), rule_id=None,
        conclusion=replace(c.native_problem.reasoning.query, predicate=c.native_problem.call.result_predicate,
                           evidence_status=EvidenceStatus.DERIVED), substitution={}, branch_id="branch-main",
        verified=True, provenance=(Provenance("forged", "self-asserted"),))
    intent = Intent.create(intent_type=IntentType.DERIVE_PROPOSITION, issuer_subsystem="reasoning_engine",
        required_capability="derive_branch_local", target_scope="branch:branch-main", branch_id="branch-main",
        goal_id=state.active_goal_id, precondition={"state_hash": state.state_hash},
        proposed_mutation={"proof": forged.to_dict()}, created_at_tick=state.logical_tick)
    result = execute(c, intent)
    assert not result.authorized_intents
    assert result.state.branch_table == state.branch_table
    assert not c._has_authoritative_support(result.state, result.state.branch_table[0], c.native_problem.call.result_key)


def test_current_call_check_required_even_when_done_is_asserted():
    c = coordinator(asserted_done=True)
    reasoner = CognitiveMachine()
    packet = c.native_problem.reasoning
    reasoner._record_decomposition(packet, "branch-main", c)
    winner = reasoner._classify_and_compare(packet, c, ("branch-main",))
    assert winner == "branch-main"
    assert not reasoner._commit_winner(packet, winner, c)
    assert c.store.snapshot().commitment_state.decision_status == "UNCOMMITTED"
    assert "this call's checked" in c.trace.events[-1].rejected_intents[0].detail


def test_rpm_entry_budget_cannot_be_refilled_by_rehashed_state():
    c = coordinator()
    request_and_push(c)
    select(c)
    # Deliberately fabricated snapshot tests the coordinator gate; this is not a
    # permissible host recovery path or evidence of a real budget allocation.
    forged = replace(c.store.snapshot(), native_budget=NativeBudget(513, 129)).with_computed_hash()
    attacked = NativeCoordinator(store=StateStore(forged), trace=c.trace,
                                native_problem=c.native_problem, profile=c.profile)
    with patch("cncm.native_kernel.qualify_procedure", side_effect=AssertionError("qualification ran")):
        result = install(attacked)
    assert not result.authorized_intents
    assert "refill" in result.rejected_intents[0].detail
    assert result.state.native_budget == forged.native_budget


def test_rollback_requires_quiescence_and_recorded_ancestor_and_keeps_artifact():
    c = coordinator()
    artifact = acquire(c)
    mutation = {"capability": CAPABILITY, "expected_head": artifact.artifact_sha256,
                "target_installation_digest": None}
    denied = send(c, NativeIntentType.ROLLBACK_PROCEDURE, mutation)
    assert not denied.authorized_intents
    assert "quiescent" in denied.rejected_intents[0].detail
    require_accepted(apply(c, artifact))
    current_installation = c.current_installation_digest(CAPABILITY)
    for target in ("0" * 64, current_installation):
        denied = send(c, NativeIntentType.ROLLBACK_PROCEDURE, {**mutation, "target_installation_digest": target})
        assert not denied.authorized_intents
        assert "ancestor" in denied.rejected_intents[0].detail
    before = c.store.snapshot()
    result = require_accepted(send(c, NativeIntentType.ROLLBACK_PROCEDURE, mutation))
    assert not result.state.procedure_heads
    assert result.state.procedural_artifacts == before.procedural_artifacts == (artifact,)
    assert result.state.native_budget == before.native_budget
    assert result.state.native_records[-1].kind == "ROLLBACK"


def test_public_snapshot_import_is_rejected():
    c = coordinator()
    with pytest.raises(ContractError, match="external native snapshot"):
        boot_native_state(c.native_problem, c.profile, previous_state=c.store.snapshot())


def replay_machine(machine, journal=None, *, anchor=None, trusted_genesis=None):
    from cncm.native_recovery import replay_native_journal
    wire = machine.journal() if journal is None else journal
    return replay_native_journal(wire, trusted_genesis=native_problem() if trusted_genesis is None else trusted_genesis,
        profile=machine.profile,
        expected_journal_digest=wire["journal_digest"] if anchor is None else anchor)


def machine_at(stage):
    from cncm.native_engine import NativeMachine
    machine = NativeMachine(simulated_profile())
    machine.start(native_problem())
    for _ in range(stage):
        machine.advance()
    return machine


def reseal_journal(journal):
    journal["journal_digest"] = digest({key: value for key, value in journal.items()
                                       if key != "journal_digest"})
    return journal


def test_recovery_reproduces_malformed_raw_intent_rejection():
    machine = machine_at(0)
    c = machine.coordinator
    intent = native_intent(c, NativeIntentType.REQUEST_PROCEDURE_CALL, {"call": machine.problem.call.to_dict()})
    result = execute(c, replace(intent, intent_type="MALFORMED_RAW_TYPE"))
    assert result.rejected_intents[0].reason is RejectionReason.MALFORMED_MUTATION
    recovered = replay_machine(machine)
    assert recovered.journal() == machine.journal()
    assert recovered.state.native_budget == machine.state.native_budget


def test_recovery_reproduces_duplicate_intent_group_rejection():
    machine = machine_at(0)
    c = machine.coordinator
    intent = native_intent(c, NativeIntentType.REQUEST_PROCEDURE_CALL, {"call": machine.problem.call.to_dict()})
    result = c.execute(enabled_components=(intent.issuer_subsystem,),
        scheduled_components=(intent.issuer_subsystem,), intents=(intent, intent))
    assert result.rejected_intents[0].reason is RejectionReason.DUPLICATE_ID
    recovered = replay_machine(machine)
    assert recovered.journal() == machine.journal()
    assert recovered.state.native_calls == ()


@pytest.mark.parametrize("corruption", ["content_id", "duplicate_mutation", "duplicate_precondition", "provenance_order", "float_mutation"])
def test_recovery_preserves_rejected_envelope_defects(corruption):
    machine = machine_at(0)
    intent = native_intent(machine.coordinator, NativeIntentType.REQUEST_PROCEDURE_CALL,
                           {"call": machine.problem.call.to_dict()})
    if corruption == "content_id":
        intent = replace(intent, intent_id="intent-" + "0" * 16)
    elif corruption == "duplicate_mutation":
        intent = replace(intent, proposed_mutation=intent.proposed_mutation + intent.proposed_mutation)
    elif corruption == "duplicate_precondition":
        intent = replace(intent, precondition=intent.precondition + intent.precondition)
    elif corruption == "provenance_order":
        intent = replace(intent, provenance=(Provenance("zzz", "last"), Provenance("aaa", "first")))
    else:
        mutation = intent.mutation_dict()
        mutation["call"]["inputs"]["a"] = 3.0
        intent = remake(intent, proposed_mutation=mutation)
    outcome = execute(machine.coordinator, intent)
    assert not outcome.authorized_intents
    assert outcome.rejected_intents[0].reason is RejectionReason.MALFORMED_MUTATION
    assert replay_machine(machine).journal() == machine.journal()


def test_recovery_preserves_mixed_occurrence_indices_and_duplicate_groups():
    machine = machine_at(0)
    intent = native_intent(machine.coordinator, NativeIntentType.REQUEST_PROCEDURE_CALL,
                           {"call": machine.problem.call.to_dict()})
    malformed = replace(intent, intent_type="RAW_INVALID")
    malformed_halt = replace(intent, intent_type=IntentType.HALT, intent_id="invalid")
    result = machine.coordinator.execute(enabled_components=(intent.issuer_subsystem, "halting_controller"),
        scheduled_components=(intent.issuer_subsystem, "halting_controller"),
        intents=(intent, malformed, intent, malformed_halt))
    assert not result.authorized_intents
    assert machine.state.native_calls == ()
    assert replay_machine(machine).journal() == machine.journal()


def test_native_proposal_occurrence_cap_does_not_partially_mutate_state():
    machine = machine_at(0)
    intent = native_intent(machine.coordinator, NativeIntentType.REQUEST_PROCEDURE_CALL,
                           {"call": machine.problem.call.to_dict()})
    before = machine.state.to_dict()
    with pytest.raises(ContractError):
        machine.coordinator.execute(enabled_components=(intent.issuer_subsystem,),
            scheduled_components=(intent.issuer_subsystem,), intents=(intent,) * 9)
    assert machine.state.to_dict() == before
    assert machine.coordinator.trace.events == ()
    assert machine.coordinator.proposal_batches == []


@pytest.mark.parametrize("stage", [0, 2, 3, 4, 5, 6])
def test_recovery_of_real_partial_execution_preserves_debits_and_continues(stage):
    machine = machine_at(stage)
    recovered = replay_machine(machine)
    assert recovered.state.to_dict() == machine.state.to_dict()
    assert recovered.run().output == "7"
    assert recovered.state.halt_status is TerminalStatus.CONCLUDED
    assert recovered.state.native_budget == NativeBudget(302, 93)


def test_recovery_keeps_failed_qualification_cost_and_does_not_install():
    machine = machine_at(2)
    result = install(machine.coordinator, make_candidate(combine="ADD_EXACT"))
    assert result.rejected_intents
    recovered = replay_machine(machine)
    assert recovered.state.native_budget == NativeBudget(452, 118)
    assert not recovered.state.procedure_heads
    recovered.run()
    assert recovered.state.halt_status is TerminalStatus.NEEDS_CAPABILITY
    assert recovered.state.native_calls[0].status == "FAILED"
    assert recovered.state.native_budget == NativeBudget(452, 118)


def test_recovery_rechecks_retained_qualification_instead_of_importing_head():
    machine = machine_at(4)
    import cncm.native_kernel as kernel
    original = kernel.qualify_procedure
    calls = []
    def no_longer_passes(artifact):
        calls.append(artifact.artifact_sha256)
        report = original(artifact)
        report["status"] = "ENGINEERING_PANEL_FAILED"
        return report
    with patch("cncm.native_kernel.qualify_procedure", side_effect=no_longer_passes):
        with pytest.raises(ContractError, match="transition"):
            replay_machine(machine)
    assert len(calls) == 1


def test_recovery_rejects_rehashed_imported_complete_call_root():
    machine = machine_at(0)
    completed = machine_at(6)
    journal = deepcopy(machine.journal())
    # This shape-valid imported state claims all installation/execution work while
    # the corresponding coordinator trace is empty. Even a newly supplied digest
    # cannot replace semantic transition replay from the trusted genesis.
    journal["episodes"][0]["final_state"] = completed.state.to_dict()
    assert NativeState.from_dict(journal["episodes"][0]["final_state"])
    with pytest.raises(ContractError, match="final state"):
        replay_machine(machine, reseal_journal(journal))


def test_external_anchor_rejects_valid_but_truncated_prefix():
    machine = machine_at(3)
    trusted_complete_anchor = machine.journal()["journal_digest"]
    prefix = machine_at(2).journal()
    with pytest.raises(ContractError, match="complete native journal digest"):
        replay_machine(machine, prefix, anchor=trusted_complete_anchor)


def test_retained_prior_call_cannot_supply_current_call_authority():
    from cncm.native_model import CallSpec
    machine = machine_at(6)
    machine.run()
    prior = machine.state
    packet = native_problem()
    changed = replace(packet, call=CallSpec.create(call_id=packet.call.call_id, goal_id=packet.call.goal_id,
        inputs={"a": "3", "b": "5", "c": "29"}))
    machine.start(changed)
    machine.advance()
    assert machine.state.native_calls[0].status == "READY"
    assert machine.coordinator._trusted_root_keys(machine.state, machine.state.branch_table[0]) == frozenset()
    # A fabricated in-memory merge is not a recovery path; test the authority
    # predicate itself rejects the prior run's receipt even for the same call ID.
    forged = replace(machine.state, native_calls=prior.native_calls, branch_table=prior.branch_table).with_computed_hash()
    with pytest.raises(ContractError, match="binding"):
        machine.coordinator._trusted_root_keys(forged, forged.branch_table[0])
    result = machine.run()
    assert result.output == "8"
    assert result.final_state.native_budget == NativeBudget(506, 127)
    assert replay_machine(machine).journal() == machine.journal()


@pytest.mark.parametrize("case,inputs,expected_report,expected_execution", [
    ("zero_coefficient", {"a": "0", "b": "5", "c": "26"}, "DOMAIN_REJECTED", "DIVISION_BY_ZERO"),
    ("arithmetic_limit", {"a": "1", "b": str(-(2**127 - 1)), "c": str(2**127 - 1)},
     "EXECUTION_REJECTED", "ARITHMETIC_LIMIT"),
])
def test_failed_native_application_is_charged_replayed_and_never_retried(case, inputs, expected_report, expected_execution):
    from cncm.native_engine import NativeMachine
    from cncm.native_model import CallSpec
    from cncm.procedural_substrate import ProcedureLimits
    packet = native_problem()
    packet = replace(packet, call=CallSpec.create(call_id=packet.call.call_id,
                     goal_id=packet.call.goal_id, inputs=inputs))
    machine = NativeMachine(simulated_profile())
    machine.start(packet)
    c = machine.coordinator
    frame = request_and_push(c)
    # The default512-bit artifact safely covers this grammar's128-bit inputs.
    # A stricter128-bit artifact passes the fixed engineering panel, while this
    # fresh legal input deliberately exceeds its declared intermediate bound.
    artifact = make_candidate(limits=ProcedureLimits(intermediate_bits=128)) if case == "arithmetic_limit" else make_candidate()
    require_accepted(install(c, artifact))
    require_accepted(send(c, NativeIntentType.RETURN_ACQUISITION, {
        "call_id": packet.call.call_id, "frame_id": frame.frame_id,
        "artifact_sha256": artifact.artifact_sha256, "success": True, "failure": None}))
    before = machine.state.native_budget
    result = apply(c, artifact)
    assert not result.authorized_intents
    assert result.rejected_intents[0].reason is RejectionReason.INVALID_PROOF
    assert result.state.native_budget == NativeBudget(before.instructions_remaining - 6,
                                                      before.checker_calls_remaining - 1)
    work = result.state.native_records[-1].body_dict()
    assert work["operation"] == "APPLY_PROCEDURE"
    assert work["failed_report"]["status"] == expected_report
    assert work["failed_report"]["execution"]["status"] == expected_execution
    assert work["failed_report"]["execution"]["outputs"] == {}
    assert work["failed_report"]["cost"]["checker_calls"] == 0
    assert result.state.native_calls[0].output is None
    assert result.state.native_calls[0].execution_digest is None
    assert result.state.commitment_state.decision_status == "UNCOMMITTED"
    assert not c._trusted_root_keys(result.state, result.state.branch_table[0])
    recovered = replay_machine(machine, trusted_genesis=packet)
    assert recovered.state.to_dict() == result.state.to_dict()
    with patch("cncm.native_kernel.check_procedure_call", side_effect=AssertionError("failed application retried")):
        terminal = recovered.run()
        again = recovered.run()
    assert terminal.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert terminal.output is None
    assert terminal.final_state.commitment_state.decision_status == "UNCOMMITTED"
    assert terminal.final_state.native_budget == result.state.native_budget
    assert again.final_state.to_dict() == terminal.final_state.to_dict()
    applies = [row for row in terminal.final_state.native_records if row.kind == "WORK_RESERVATION"
               and row.body_dict()["operation"] == "APPLY_PROCEDURE"]
    assert len(applies) == 1
    assert replay_machine(recovered, trusted_genesis=packet).journal() == recovered.journal()


def test_proposer_examiner_conflict_install_is_charged_rejected_and_replayed():
    from cncm.procedural_qualification import EXAMINER_ID
    from cncm.procedural_substrate import ProposalProvenance
    machine = machine_at(2)
    # This checks the explicit self-described role-label conflict. It does not
    # claim that a different proposer label authenticates an independent person.
    artifact = make_candidate(provenance=ProposalProvenance(EXAMINER_ID, "0.1"))
    result = install(machine.coordinator, artifact)
    assert not result.authorized_intents
    assert result.rejected_intents[0].reason is RejectionReason.INVALID_PROOF
    assert result.state.native_budget == NativeBudget(452, 118)
    assert not result.state.procedural_artifacts and not result.state.procedure_heads
    work = result.state.native_records[-1].body_dict()
    assert work["failure"] == "PROPOSER_EXAMINER_CONFLICT"
    assert work["failed_report"] is None
    recovered = replay_machine(machine)
    with patch("cncm.native_kernel.qualify_procedure", side_effect=AssertionError("conflicting installation retried")):
        terminal = recovered.run()
    assert terminal.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert terminal.final_state.native_calls[0].status == "FAILED"
    assert terminal.output is None
    assert terminal.final_state.commitment_state.decision_status == "UNCOMMITTED"
    assert terminal.final_state.native_budget == NativeBudget(452, 118)
