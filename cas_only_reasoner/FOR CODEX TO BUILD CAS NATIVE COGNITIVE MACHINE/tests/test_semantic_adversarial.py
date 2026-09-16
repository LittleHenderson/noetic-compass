"""Independent semantic authority attacks and labeled internal fault injection."""
from dataclasses import replace

import pytest

from cncm.canonical import digest
from cncm.model import ContractError, Intent, IntentType, TerminalStatus
from cncm.semantic_engine import SemanticMachine
from cncm.semantic_model import (SourceStatement, MemoryRef, SemanticEquation, SemanticProblem,
                                 SemanticIntentType as Kind, create_problem)
from cncm.semantic_profile import SemanticProfile, SOURCE_FILES, authority_policy, SEMANTIC_AUTHORITIES
from cncm.semantic_verification import resolve_memory


@pytest.fixture
def profile():
    # This fixture tests runtime semantics, not a published source identity.
    return SemanticProfile(tuple((name, 1, "0" * 64) for name in SOURCE_FILES), digest(authority_policy()))


def source(value="5", *, previous=None, status="USER_ATTESTED"):
    return SourceStatement("shop", "fee", "owner", value, status, "ASSERT", previous, "urn:test:user-turn")


def task(*, updates=(), requirement="ATTESTED", problem_id="task"):
    return create_problem((SemanticEquation("x", "3", MemoryRef("shop", "fee", requirement), "26"),),
                          "x", updates=updates, problem_id=problem_id)


def start(profile, *rows, updates=None):
    machine = SemanticMachine(profile, trusted_ingress=tuple(sorted(row.statement_digest for row in rows)))
    machine.start(task(updates=tuple(rows) if updates is None else updates))
    return machine


def drive(machine, condition):
    for _ in range(120):
        if condition(machine):
            return machine
        assert machine.state.halt_status is TerminalStatus.RUNNING
        machine.advance()
    pytest.fail("test did not reach explicit stage")


def proposal(machine, kind, mutation, **changes):
    issuer, capability = SEMANTIC_AUTHORITIES[kind.value]
    arguments = dict(intent_type=kind, issuer_subsystem=issuer, required_capability=capability,
                     target_scope="semantic_memory", branch_id="branch-main", goal_id=machine.state.active_goal_id,
                     precondition={"state_hash": machine.state.state_hash}, proposed_mutation=mutation,
                     created_at_tick=machine.state.logical_tick, provenance=())
    arguments.update(changes)
    return Intent.create(**arguments)


def execute(machine, value, count=1):
    return machine.coordinator.execute(enabled_components=(value.issuer_subsystem,),
                                       scheduled_components=(value.issuer_subsystem,), intents=(value,) * count)


@pytest.mark.parametrize("attack", ["value", "status", "statement"])
def test_independent_resolution_rejects_wrong_binding_returned_by_recall_alias(profile, monkeypatch, attack):
    # A trusted producer is deliberately fault-injected here. Its false binding
    # and receipt are internally consistent and resealed, so only independent
    # reconstruction from source history can establish the counterfeit.
    row = source()
    machine = start(profile, row)

    def corrupted(*args, **kwargs):
        binding, receipt = resolve_memory(*args, **kwargs)
        changes = {"value": {"value": "99"}, "status": {"statuses": ("TEST_FIXTURE",)},
                   "statement": {"statement_digests": ("f" * 64,)}}[attack]
        forged = replace(binding, **changes)
        receipt["bindings"]["binding"] = {"ref": forged.ref.to_dict(), "value": forged.value,
            "statement_digests": list(forged.statement_digests), "statuses": list(forged.statuses)}
        receipt["bindings"]["active_values"] = [forged.value]
        receipt["support"] = forged.statuses[0]
        receipt["receipt_digest"] = digest({key: value for key, value in receipt.items() if key != "receipt_digest"})
        return replace(forged, receipt_digest=receipt["receipt_digest"]), receipt

    monkeypatch.setattr("cncm.semantic_kernel.resolve_memory", corrupted)
    result = machine.run()
    assert result.terminal_status is TerminalStatus.NEEDS_INFORMATION and result.output is None
    assert machine.state.memory_failure == "RECALL_BINDING_MISMATCH"
    assert machine.state.memory_resolution_digest is None and not machine.state.native_calls
    assert machine.state.native_budget.instructions_remaining == 512 - 12 - 12 - 16
    assert machine.state.native_budget.checker_calls_remaining == 128 - 3
    assert machine.state.memory_statements == (row,)
    assert machine.state.semantic_records[-1].body_dict()["receipt"]["status"] == "INVALID"


def test_wrong_recall_reference_is_a_charged_fault_without_retry_or_bad_binding(profile, monkeypatch):
    machine = start(profile, source())

    def wrong_scope(*args, **kwargs):
        binding, receipt = resolve_memory(*args, **kwargs)
        return replace(binding, ref=MemoryRef("other", "fee")), receipt

    monkeypatch.setattr("cncm.semantic_kernel.resolve_memory", wrong_scope)
    result = machine.run()
    assert result.terminal_status is TerminalStatus.NEEDS_INFORMATION and result.output is None
    assert machine.state.memory_failure == "VERIFIER_FAULT"
    assert not machine.state.memory_bindings and not machine.state.native_calls
    assert machine.state.native_budget.instructions_remaining == 512 - 24
    assert machine.state.native_budget.checker_calls_remaining == 128 - 2
    work = machine.state.semantic_records[-1].body_dict()
    assert work["receipt"] is None and work["verifier_fault"]


def test_independent_resolution_rejects_corrupted_compiler_scalar(profile, monkeypatch):
    row = source()
    machine = start(profile, row)
    drive(machine, lambda m: bool(m.state.memory_bindings))
    original = SemanticProblem.resolved_problem

    def corrupted(self, bindings):
        candidate = original(self, bindings)
        return replace(candidate, equations=(replace(candidate.equations[0], b="99"),))

    before = machine.state.native_budget
    with monkeypatch.context() as patch:
        patch.setattr(SemanticProblem, "resolved_problem", corrupted)
        machine.advance()
    assert machine.state.memory_failure == "RESOLVED_PROBLEM_MISMATCH"
    assert machine.state.native_budget.instructions_remaining == before.instructions_remaining - 16
    assert machine.state.native_budget.checker_calls_remaining == before.checker_calls_remaining - 1
    assert machine.state.memory_resolution_digest is None and not machine.state.native_calls
    assert machine.run().output is None


def test_direct_store_cannot_mutate_suspended_parent_inputs(profile, monkeypatch):
    old = source()
    correction = source("8", previous=old.statement_digest)
    machine = start(profile, old, correction, updates=(old,))
    drive(machine, lambda m: bool(m.state.rpm_stack))
    before = machine.state
    called = []
    monkeypatch.setattr("cncm.semantic_kernel.validate_source_update", lambda *_a, **_k: called.append(True))
    value = proposal(machine, Kind.STORE_SOURCE, {"index": 1, "statement": correction.to_dict()})
    outcome = execute(machine, value)
    assert outcome.rejected_intents and not outcome.trace_event.authorized_intent_ids
    assert machine.state.memory_statements == before.memory_statements
    assert machine.state.memory_bindings == before.memory_bindings
    assert machine.state.native_calls == before.native_calls
    assert machine.state.rpm_stack == before.rpm_stack
    assert machine.state.branch_table == before.branch_table
    assert machine.state.native_budget == before.native_budget and called == []


@pytest.mark.parametrize("stage,target,cost", [
    (0, "validate_source_update", 12), (1, "resolve_memory", 12), (2, "verify_resolution", 16),
])
def test_verifier_exception_is_charged_without_fabricating_a_common_receipt(profile, monkeypatch, stage, target, cost):
    machine = start(profile, source())
    for _ in range(stage):
        machine.advance()
    before = machine.state.native_budget

    def broken(*_args, **_kwargs):
        raise ContractError("injected verifier failure")

    monkeypatch.setattr("cncm.semantic_kernel." + target, broken)
    machine.advance()
    assert machine.state.memory_failure == "VERIFIER_FAULT"
    record = machine.state.semantic_records[-1].body_dict()
    assert record["receipt"] is None
    assert record["verifier_fault"] == "injected verifier failure"
    assert machine.state.native_budget.instructions_remaining == before.instructions_remaining - cost
    assert machine.state.native_budget.checker_calls_remaining == before.checker_calls_remaining - 1
    assert machine.state.memory_resolution_digest is None and not machine.state.native_calls
    assert machine.run().terminal_status is TerminalStatus.NEEDS_INFORMATION


@pytest.mark.parametrize("status", ["USER_ATTESTED", "TEST_FIXTURE"])
def test_checked_arithmetic_never_upgrades_source_to_verified_world_fact(profile, status):
    row = source(status=status)
    machine = start(profile, row)
    result = machine.run()
    assert result.output == "7" and result.terminal_status is TerminalStatus.CONCLUDED
    assert machine.state.memory_statements == (row,)
    assert machine.state.memory_bindings[0].statuses == (status,)
    assert result.summary()["unconditional_world_truth"] is False
    assert result.summary()["claim_status"] == "CONDITIONAL_ON_RECORDED_SOURCE_BINDINGS"
    assert result.evidence["scope"]["external_fact_verification"] is False
    assert "arithmetic" in result.evidence["scope"]["answer_scope"]
    records = [record.body_dict() for record in machine.state.semantic_records]
    receipts = [body["receipt"] for body in records if body.get("receipt") is not None]
    assert receipts and all(receipt["factual_status"] == "NOT_INDEPENDENTLY_VERIFIED" for receipt in receipts)
    strong = task(requirement="INDEPENDENTLY_VERIFIED", problem_id="strong-evidence-demand")
    refused = machine.run(strong, allow_acquisition=False)
    assert refused.output is None and refused.terminal_status is TerminalStatus.NEEDS_INFORMATION
    assert machine.state.memory_failure == "INSUFFICIENT_EVIDENCE"


@pytest.mark.parametrize("changes", [
    {"issuer_subsystem": "candidate_generator"}, {"required_capability": "install_nested_procedure"},
    {"branch_id": "other-branch"}, {"target_scope": "procedural_memory"}, {"goal_id": "other-goal"},
])
def test_validly_hashed_store_envelope_does_not_bypass_source_authority(profile, monkeypatch, changes):
    row = source()
    machine = start(profile, row)
    called = []
    monkeypatch.setattr("cncm.semantic_kernel.validate_source_update", lambda *_a, **_k: called.append(True))
    value = proposal(machine, Kind.STORE_SOURCE, {"index": 0, "statement": row.to_dict()}, **changes)
    before = machine.state.native_budget
    outcome = execute(machine, value)
    assert outcome.rejected_intents and not outcome.trace_event.authorized_intent_ids
    assert machine.state.memory_statements == () and machine.state.native_budget == before
    assert called == []


def test_self_authorizing_update_is_refused_even_with_correct_issuer_and_hash(profile):
    row = source()
    machine = SemanticMachine(profile, trusted_ingress=())
    machine.start(task(updates=(row,)))
    outcome = execute(machine, proposal(machine, Kind.STORE_SOURCE, {"index": 0, "statement": row.to_dict()}))
    assert outcome.rejected_intents and not outcome.trace_event.authorized_intent_ids
    assert machine.state.memory_failure == "UNTRUSTED_INGRESS"
    assert machine.state.memory_statements == ()
    assert machine.state.native_budget.instructions_remaining == 500


def test_duplicate_store_occurrences_do_not_trigger_verifier_or_debit(profile, monkeypatch):
    row = source()
    machine = start(profile, row)
    called = []
    monkeypatch.setattr("cncm.semantic_kernel.validate_source_update", lambda *_a, **_k: called.append(True))
    value = proposal(machine, Kind.STORE_SOURCE, {"index": 0, "statement": row.to_dict()})
    before = machine.state.native_budget
    outcome = execute(machine, value, count=2)
    assert outcome.rejected_intents and not outcome.trace_event.authorized_intent_ids
    assert machine.state.memory_statements == () and machine.state.native_budget == before
    assert called == [] and len(machine.coordinator.proposal_batches[-1]) == 2
