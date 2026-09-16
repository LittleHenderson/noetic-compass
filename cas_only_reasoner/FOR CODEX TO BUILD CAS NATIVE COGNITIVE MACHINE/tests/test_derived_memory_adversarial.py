"""Independent 0.6 boundary tests, using explicitly simulated source profiles.

These tests do not authenticate source assertions or establish world truth.
Any internal fault injection is named as such and is not an external entry path.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import fields, replace
import importlib.abc
import sys

import pytest


class _DenyExecutionImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in {
            "torch", "numpy", "transformers", "tensorflow", "jax",
            "boto3", "botocore", "openai", "anthropic",
        }:
            raise AssertionError("forbidden execution import: " + fullname)
        return None


@contextmanager
def _pure_imports():
    guard = _DenyExecutionImports()
    sys.meta_path.insert(0, guard)
    try:
        yield
    finally:
        sys.meta_path.remove(guard)


with _pure_imports():
    from cncm.canonical import canonical_json, digest
    from cncm.compound_kernel import boot_compound_state
    from cncm.compound_model import CompoundState, create_problem as compound_problem
    from cncm.compound_profile import CompoundProfile, SOURCE_FILES, authority_policy
    from cncm.derived_model import (
        CONSTITUTION, VERSION, DerivedDefinition, DerivedFrame, DerivedProblem,
        DerivedRecord, DerivedResultRef, DerivedState, create_problem,
    )
    from cncm.model import ContractError
    from cncm.semantic_model import MemoryRef, SourceStatement


@pytest.fixture(autouse=True)
def pure_execution_imports():
    # Remove our finder after each test, including failures, so it cannot change
    # unrelated tests in the full suite.
    with _pure_imports():
        yield


def definition(*, scope="adversarial", key="remembered-y", variable="y", **changes):
    args = dict(scope=scope, key=key, revision=1, supersedes=None, variable=variable,
                parameters=tuple(sorted(dict(a="1", b="2", c="1", d="0", e="11").items())))
    args.update(changes)
    return DerivedDefinition(**args)


def packet(**changes):
    return create_problem(dict(a="2", b="3", c=DerivedResultRef("adversarial", "remembered-y"),
                               d="7", e="35"), **changes)


def structural_state():
    """Build structure only; this fixture is never supplied as trusted history."""
    simulated = CompoundProfile(
        tuple((name, 1, digest({"simulated_adversarial_source": name})) for name in SOURCE_FILES),
        digest(authority_policy()),
    )
    old = boot_compound_state(compound_problem(dict(a="1", b="1", c="0", d="0", e="3")),
                              simulated, ())
    args = {field.name: getattr(old, field.name) for field in fields(CompoundState)}
    args.update(runtime_version=VERSION, constitution_revision=CONSTITUTION, state_hash="")
    return DerivedState(**args).with_computed_hash()


@pytest.mark.parametrize("constructor,value", [
    (DerivedResultRef.from_dict, DerivedResultRef("adversarial", "value").to_dict()),
    (DerivedDefinition.from_dict, definition().to_dict()),
    (DerivedProblem.from_dict, packet().to_dict()),
    (DerivedRecord.from_dict, DerivedRecord.create("INSPECTION", {"fixture": True}).to_dict()),
])
@pytest.mark.parametrize("attack", ["unknown-field", "missing-field", "wrong-schema", "tuple-wire"])
def test_public_contracts_refuse_open_or_non_json_wire(constructor, value, attack):
    body = deepcopy(value)
    if attack == "unknown-field":
        body["caller_authorized"] = True
    elif attack == "missing-field":
        body.pop("schema_version")
    elif attack == "wrong-schema":
        body["schema_version"] = "cncm.derived-other/0.6"
    else:
        body = tuple(body.items())
    with pytest.raises(ContractError):
        constructor(body)


@pytest.mark.parametrize("revision", [True, False, 1.0, "1", 0, 129])
def test_definition_revision_has_exact_bounded_integer_type(revision):
    body = definition().to_dict()
    body["revision"] = revision
    with pytest.raises(ContractError):
        DerivedDefinition.from_dict(body)


@pytest.mark.parametrize("value", [True, 1, 1.0, None, "2/2", "01", "1/0", str(2**128)])
def test_definition_scalar_requires_canonical_bounded_exact_rational(value):
    body = definition().to_dict()
    body["parameters"][0][1] = value
    with pytest.raises(ContractError):
        DerivedDefinition.from_dict(body)


@pytest.mark.parametrize("requirement", ["ATTESTED", "INDEPENDENTLY_VERIFIED", "VERIFIED", True, None])
def test_derived_evidence_cannot_be_retyped_as_world_fact(requirement):
    with pytest.raises(ContractError):
        DerivedResultRef("adversarial", "value", requirement)


def test_definition_identity_preserves_scope_variable_and_typed_dependency():
    base = definition()
    variants = (
        definition(scope="another-context"), definition(variable="z"),
        definition(parameters=tuple(sorted(dict(a="1", b="2", c="1", d="0",
                                                e=MemoryRef("adversarial", "rhs")).items()))),
        definition(parameters=tuple(sorted(dict(a="1", b="2", c="1", d="0",
                                                e=DerivedResultRef("adversarial", "rhs")).items()))),
        definition(revision=2, supersedes=base.definition_digest),
    )
    assert len({base.definition_digest, *(row.definition_digest for row in variants)}) == 6
    assert all(DerivedDefinition.from_dict(row.to_dict()) == row for row in (base, *variants))


def test_problem_cannot_carry_multiple_updates_for_same_scoped_definition():
    original = definition()
    revision = definition(revision=2, supersedes=original.definition_digest)
    with pytest.raises(ContractError):
        packet(definitions=(original, revision))
    assert len(packet(definitions=(original, definition(scope="another-context"))).definitions) == 2


@pytest.mark.parametrize("field,value", [
    ("definition_update_index", True), ("derived_stored", 1),
    ("derived_bindings", (("adversarial", "value", "not-a-digest"),)),
    ("rpm_stack", []),
])
def test_state_direct_constructor_refuses_type_aliases(field, value):
    with pytest.raises(ContractError):
        replace(structural_state(), **{field: value})


def test_extension_fields_are_hash_bound_and_roundtrip_exactly():
    original = structural_state()
    row = DerivedRecord.create("INSPECTION", {"fixture": True})
    changed = replace(original, derived_records=(row,)).with_computed_hash()
    assert changed.state_hash != original.state_hash
    assert canonical_json(DerivedState.from_dict(changed.to_dict()).to_dict()) == canonical_json(changed.to_dict())
    body = changed.to_dict()
    body["derived_stored"] = True
    with pytest.raises(ContractError):
        DerivedState.from_dict(body)


def test_record_json_depth_is_refused_as_contract_error_before_parser_recursion():
    # body_json is opaque to the outer wire scanner. The constructor must still
    # enforce its bounded contract without allowing Python's parser to escape.
    depth = sys.getrecursionlimit() + 100
    raw = '{"nested":' + '[' * depth + '0' + ']' * depth + '}'
    with pytest.raises(ContractError):
        DerivedRecord("INSPECTION", raw, "0" * 64)


def test_frame_binds_exact_reference_address_and_integer_depth():
    reference = DerivedResultRef("adversarial", "value")
    frame = DerivedFrame("frame-1", "child-1", "parent-1", "1" * 64, "2" * 64,
                         reference, "3" * 64, "derived:" + digest(reference.to_dict()),
                         "RESOLVE_COMPOUND_INPUTS", 1, 100, 10)
    assert DerivedFrame.from_dict(frame.to_dict()) == frame
    for changes in ({"reference": DerivedResultRef("other", "value")}, {"depth": True},
                    {"depth": 2}, {"resume_stage": "COMMIT"}, {"entry_checker_budget": -1}):
        with pytest.raises(ContractError):
            replace(frame, **changes)


def synthetic_proof_state():
    """Pure verifier fixture; deliberately not proof of coordinator admission."""
    from cncm.derived_verification import checked_proof, resolved_definition
    source = SourceStatement("adversarial", "rhs", "source-a", "11", "TEST_FIXTURE", "ASSERT", None,
                             "engineering-fixture:adversarial")
    defined = definition(parameters=tuple(sorted(dict(a="1", b="2", c="1", d="0",
                                                       e=MemoryRef("adversarial", "rhs")).items())))
    ingress = tuple(sorted((source.statement_digest, defined.definition_digest)))
    state = replace(structural_state(), memory_statements=(source,), derived_definitions=(defined,))
    profile_digest = state.native_contract_digest
    inputs, leaves, definitions = resolved_definition(state, defined, ingress, profile_digest)
    record = DerivedRecord.create("MEMORY", {
        "reference": defined.ref.to_dict(), "definition_digest": defined.definition_digest,
        "value": "5", "inputs": inputs, "source_bindings": leaves,
        "derived_dependencies": [], "definition_dependencies": definitions,
        "source_profile_digest": profile_digest,
        "proof": checked_proof(defined, inputs, "5", profile_digest),
        "verification_status": "CHECKED_FORMAL_DERIVATION", "unconditional_world_truth": False,
    })
    return replace(state, derived_records=(record,)).with_computed_hash(), source, defined, ingress, record


def test_pure_recheck_does_not_call_candidate_generation_or_solver(monkeypatch):
    import cncm.derived_verification as verifier
    import cncm.math_engine as math_engine
    state, _, defined, ingress, _ = synthetic_proof_state()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("candidate generation is not a retained-proof check")

    monkeypatch.setattr(verifier, "generate_candidate", forbidden)
    monkeypatch.setattr(math_engine, "solve_linear_statement", forbidden)
    monkeypatch.setattr(math_engine, "solve_linear_equation", forbidden)
    monkeypatch.setattr(math_engine, "verify_math_result", forbidden)
    result = verifier.inspect_memory(state, defined.ref, ingress, state.native_contract_digest)
    assert result["status"] == "VERIFIED" and result["checked_nodes"] == 1
    assert result["unconditional_world_truth"] is False


@pytest.mark.parametrize("attack,expected_status,expected_reason", [
    ("new-conflict", "CONTRADICTED", "SOURCE_CONFLICT"),
    ("new-agreement", "STALE", "STALE_ACTIVE_SOURCE_SET"),
    ("same-value-revision", "STALE", "STALE_ACTIVE_SOURCE_SET"),
    ("retracted", "STALE", "SOURCE_REVOKED"),
    ("definition-revision", "SUPERSEDED", "SUPERSEDED_DEFINITION"),
    ("checker-profile", "STALE", "STALE_CHECKER_PROFILE"),
])
def test_pure_freshness_rechecks_all_current_heads_not_only_retained_hashes(attack, expected_status, expected_reason):
    from cncm.derived_verification import inspect_memory
    state, source, defined, ingress, record = synthetic_proof_state()
    profile_digest = state.native_contract_digest
    if attack == "definition-revision":
        newer = replace(defined, revision=2, supersedes=defined.definition_digest)
        state = replace(state, derived_definitions=state.derived_definitions + (newer,))
        ingress = tuple(sorted((*ingress, newer.definition_digest)))
    elif attack == "checker-profile":
        profile_digest = "f" * 64
    else:
        changes = dict(source_id="source-b", value="17" if attack == "new-conflict" else "11")
        if attack in {"same-value-revision", "retracted"}:
            changes.update(source_id=source.source_id, previous_digest=source.statement_digest)
        if attack == "retracted":
            changes.update(action="RETRACT", value=None)
        update = replace(source, **changes)
        state = replace(state, memory_statements=(source, update))
        ingress = tuple(sorted((*ingress, update.statement_digest)))
    # Original proof and original source remain byte-for-byte in history.
    assert state.derived_records == (record,) and state.memory_statements[0] == source
    report = inspect_memory(state, defined.ref, ingress, profile_digest)
    assert report["status"] == expected_status
    assert expected_reason in report["reason"]


@pytest.mark.parametrize("attack", ["reference", "foreign-proof", "foreign-value", "world-truth", "profile"])
def test_resealed_record_cannot_borrow_valid_foreign_proof_or_context(attack):
    from cncm.derived_verification import checked_proof, inspect_memory
    state, _, defined, ingress, record = synthetic_proof_state()
    body = record.body_dict()
    if attack == "reference":
        body["reference"] = DerivedResultRef("foreign-scope", defined.key).to_dict()
    elif attack == "foreign-proof":
        foreign = replace(defined, scope="foreign-scope")
        body["proof"] = checked_proof(foreign, body["inputs"], body["value"], state.native_contract_digest)
    elif attack == "foreign-value":
        body["value"] = "6"
    elif attack == "world-truth":
        body["unconditional_world_truth"] = True
    else:
        body["source_profile_digest"] = "f" * 64
    forged = DerivedRecord.create("MEMORY", body)
    state = replace(state, derived_records=(forged,)).with_computed_hash()
    report = inspect_memory(state, defined.ref, ingress, state.native_contract_digest,
                            selected=forged.record_digest)
    assert report["status"] != "VERIFIED"
    assert report["memory_digest"] == forged.record_digest
    assert report["unconditional_world_truth"] is False


def test_proposed_memory_bounds_include_new_root_and_combined_dependency_graph():
    from cncm.derived_verification import validate_admission_dependencies
    # These records exercise the structural graph limiter only. They contain no
    # claim of proof validity, trusted admission, or actual runtime history.
    rows, roots = [], []
    for group in range(4):
        leaves = [DerivedRecord.create("MEMORY", {"fixture": f"leaf-{group}-{index}",
                                                  "derived_dependencies": []}) for index in range(4)]
        root = DerivedRecord.create("MEMORY", {"fixture": f"group-{group}",
                                                "derived_dependencies": [r.record_digest for r in leaves]})
        rows.extend((*leaves, root))
        roots.append(root)
    state = replace(structural_state(), derived_records=tuple(rows)).with_computed_hash()
    assert validate_admission_dependencies(state, tuple(roots[:3])) == 16
    with pytest.raises(ContractError, match="SUPPORT_NODE_BOUND_EXCEEDED"):
        validate_admission_dependencies(state, tuple(roots))


def test_proposed_memory_checks_longest_shared_path_after_short_path_was_visited():
    from cncm.derived_verification import validate_admission_dependencies
    rows = []
    for index in range(8):
        row = DerivedRecord.create("MEMORY", {"fixture": f"chain-{index}",
            "derived_dependencies": [rows[-1].record_digest] if rows else []})
        rows.append(row)
    state = replace(structural_state(), derived_records=tuple(rows)).with_computed_hash()
    assert validate_admission_dependencies(state, (rows[5], rows[6])) == 8
    with pytest.raises(ContractError, match="SUPPORT_DEPTH_EXHAUSTED"):
        validate_admission_dependencies(state, (rows[5], rows[7]))


def runtime_profile():
    from cncm.derived_profile import DerivedProfile, SOURCE_FILES, authority_policy
    return DerivedProfile(tuple((name, 1, digest({"simulated_adversarial_source": name})) for name in SOURCE_FILES),
                          digest(authority_policy()))


def runtime_machine(*definitions):
    from cncm.derived_engine import DerivedMachine
    return DerivedMachine(runtime_profile(), trusted_ingress=tuple(sorted(d.definition_digest for d in definitions)))


def runtime_parent(defined, *, register=False, name="adversarial-runtime", **options):
    return create_problem(dict(a="2", b="3", c=defined.ref, d="7", e="35"),
                          definitions=(defined,) if register else (), problem_id=name, **options)


def advance_until(machine, kind):
    from cncm.model import TerminalStatus
    for _ in range(100):
        proposal = machine.coordinator.next_intent()
        if proposal is not None and proposal.intent_type is kind:
            return proposal
        assert machine.state.halt_status is TerminalStatus.RUNNING
        machine.advance()
    pytest.fail("explicit derived stage not reached: " + kind.value)


def execute_proposal(machine, proposal):
    return machine.coordinator.execute(enabled_components=(proposal.issuer_subsystem,),
        scheduled_components=(proposal.issuer_subsystem,), intents=(proposal,))


def test_receiver_cannot_bind_requested_reference_to_another_valid_memory(monkeypatch):
    """Internal verifier fault injection, not an external mutation mechanism."""
    import cncm.derived_kernel as kernel
    from cncm.derived_model import DerivedIntentType as D
    from cncm.model import TerminalStatus
    local = definition()
    foreign = definition(scope="foreign-context", parameters=tuple(sorted(
        dict(a="1", b="2", c="1", d="0", e="17").items())))
    machine = runtime_machine(local, foreign)
    assert machine.run(runtime_parent(local, register=True, name="learn-local")).output == "3"
    assert machine.run(runtime_parent(foreign, register=True, name="learn-foreign")).output == "2"
    machine.start(runtime_parent(local, name="borrowed-proof-consumer"))
    proposal = advance_until(machine, D.INSPECT_DERIVED)
    real_inspect = kernel.inspect_memory

    def borrowed(state, _ref, ingress, profile_digest, **options):
        return real_inspect(state, foreign.ref, ingress, profile_digest, **options)

    monkeypatch.setattr(kernel, "inspect_memory", borrowed)
    execute_proposal(machine, proposal)
    result = machine.run(allow_generation=False, allow_acquisition=False)
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    assert machine.state.commitment_state.decision_status != "COMMITTED"


def test_independent_input_check_catches_faulty_derived_to_compound_translation(monkeypatch):
    """Fault inject the compiler helper; original typed input stays unchanged."""
    from cncm.model import TerminalStatus
    defined = definition()
    machine = runtime_machine(defined)
    assert machine.run(runtime_parent(defined, register=True, name="learn-for-compiler-check")).output == "3"
    machine.start(runtime_parent(defined, name="original-input-must-be-authoritative"))
    original_input = machine.problem.to_dict()
    real_translate = DerivedProblem.compound_packet

    def corrupted(self, *args, **kwargs):
        translated = real_translate(self, *args, **kwargs)
        wrong = dict(translated.parameters)
        wrong["e"] = "41"
        return replace(translated, parameters=tuple(sorted(wrong.items())))

    monkeypatch.setattr(DerivedProblem, "compound_packet", corrupted)
    result = machine.run(allow_generation=False, allow_acquisition=False)
    assert machine.problem.to_dict() == original_input
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    assert machine.state.commitment_state.decision_status != "COMMITTED"


def test_invalid_generated_candidate_cannot_be_admitted_and_failed_check_keeps_charge(monkeypatch):
    import cncm.derived_kernel as kernel
    from cncm.derived_model import DerivedIntentType as D
    from cncm.derived_profile import DERIVED_WORK_COSTS
    from cncm.native_model import NativeBudget
    defined = definition()
    machine = runtime_machine(defined)
    machine.start(runtime_parent(defined, register=True))
    advance_until(machine, D.GENERATE_DERIVED)
    monkeypatch.setattr(kernel, "generate_candidate", lambda _inputs: "6")
    machine.advance()
    proposal = advance_until(machine, D.CHECK_DERIVED)
    before = machine.state.native_budget
    cost = DERIVED_WORK_COSTS[D.CHECK_DERIVED.value]
    result = execute_proposal(machine, proposal)
    assert result.rejected_intents
    charged = NativeBudget(before.instructions_remaining - cost[0], before.checker_calls_remaining - cost[1])
    assert machine.state.native_budget == charged
    # A repeated occurrence has a stale envelope. It cannot refund or repeat
    # the already paid failed proof check.
    assert execute_proposal(machine, proposal).rejected_intents
    assert machine.state.native_budget == charged
    assert machine.run().output is None
    assert machine.state.native_budget == charged and not machine.state.rpm_stack
    assert not any(row.kind == "MEMORY" for row in machine.state.derived_records)


def test_one_short_proof_budget_unwinds_without_partial_admission_or_reset():
    from cncm.derived_model import DerivedIntentType as D
    from cncm.derived_profile import DERIVED_WORK_COSTS
    from cncm.native_model import NativeBudget
    from cncm.model import TerminalStatus
    defined = definition()
    prior_cost = sum(DERIVED_WORK_COSTS[name][0] for name in
                     ("REGISTER_DEFINITION", "INSPECT_DERIVED", "GENERATE_DERIVED"))
    available = DERIVED_WORK_COSTS["CHECK_DERIVED"][0] - 1
    machine = runtime_machine(defined)
    machine.start(runtime_parent(defined, register=True, budget=NativeBudget(prior_cost + available, 1000)))
    advance_until(machine, D.CHECK_DERIVED)
    before = machine.state.native_budget
    assert before.instructions_remaining == available
    result = machine.run()
    assert result.terminal_status is TerminalStatus.BUDGET_EXHAUSTED and result.output is None
    assert machine.state.native_budget == before and not machine.state.rpm_stack
    assert not any(row.kind == "MEMORY" for row in machine.state.derived_records)
    assert machine.state.compound_call is None


def test_postcommit_store_rejects_a_valid_proof_for_another_definition(monkeypatch):
    """A faulty proof producer must not create an admitted durable record."""
    import cncm.derived_kernel as kernel
    from cncm.derived_model import DerivedIntentType as D
    from cncm.derived_profile import DERIVED_WORK_COSTS
    from cncm.derived_verification import checked_proof as protected_check
    from cncm.native_model import NativeBudget
    parameters = dict(a="2", b="3", c="5", d="7", e="35")
    defined = definition(variable="x", parameters=tuple(sorted(parameters.items())))
    machine = runtime_machine(defined)
    machine.start(create_problem(parameters, definitions=(defined,), store_result=defined.ref,
                                 problem_id="postcommit-foreign-proof"))
    proposal = advance_until(machine, D.STORE_DERIVED)
    assert machine.state.commitment_state.decision_status == "COMMITTED"
    before = machine.state.native_budget
    cost = DERIVED_WORK_COSTS[D.STORE_DERIVED.value]

    def foreign_proof(definition, inputs, value, profile_digest):
        return protected_check(replace(definition, scope="foreign-context"), inputs, value, profile_digest)

    monkeypatch.setattr(kernel, "checked_proof", foreign_proof)
    outcome = execute_proposal(machine, proposal)
    assert outcome.rejected_intents
    assert machine.state.native_budget == NativeBudget(before.instructions_remaining - cost[0],
                                                        before.checker_calls_remaining - cost[1])
    assert not machine.state.derived_stored
    assert not any(row.kind == "MEMORY" for row in machine.state.derived_records)


def test_pending_frame_rejects_new_episode_and_new_authority_without_budget_reset():
    from cncm.derived_model import DerivedIntentType as D
    defined = definition()
    machine = runtime_machine(defined)
    machine.start(runtime_parent(defined, register=True))
    advance_until(machine, D.GENERATE_DERIVED)
    assert machine.state.rpm_stack
    before = machine.journal()
    extra = definition(scope="extra-authority")
    with pytest.raises(ContractError):
        machine.start(runtime_parent(extra, register=True, name="illegal-new-episode"),
                      additional_trusted_ingress=(extra.definition_digest,))
    assert machine.journal() == before


@pytest.mark.parametrize("changes", [
    {"issuer_subsystem": "candidate_generator"}, {"required_capability": "apply_checked_call_program"},
    {"target_scope": "semantic_memory"}, {"goal_id": "foreign-goal"}, {"branch_id": "foreign-branch"},
])
def test_resealed_definition_registration_cannot_bypass_transaction_authority(changes):
    from cncm.model import Intent
    defined = definition()
    machine = runtime_machine(defined)
    machine.start(runtime_parent(defined, register=True))
    good = machine.coordinator.next_intent()
    args = dict(intent_type=good.intent_type, issuer_subsystem=good.issuer_subsystem,
                required_capability=good.required_capability, target_scope=good.target_scope,
                branch_id=good.branch_id, goal_id=good.goal_id,
                precondition=good.precondition_dict(), proposed_mutation=good.mutation_dict(),
                created_at_tick=good.created_at_tick, provenance=good.provenance)
    args.update(changes)
    before = machine.state
    outcome = execute_proposal(machine, Intent.create(**args))
    assert outcome.rejected_intents
    assert machine.state.native_budget == before.native_budget
    assert machine.state.derived_definitions == before.derived_definitions
    assert machine.state.derived_records == before.derived_records
