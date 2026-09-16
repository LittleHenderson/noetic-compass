"""Pure source-memory shape and identity checks, not provenance authority."""
from dataclasses import FrozenInstanceError, fields, replace
import json

import pytest

from cncm.canonical import canonical_json, digest
from cncm.kernel import boot_state
from cncm.model import (CandidateSpec, ContractError, EvidenceStatus, InferenceOperation,
    MachineState, Proposition, Provenance, ResolverSpec, Rule)
from cncm.native_model import NativeBudget
from cncm.nested_model import (NESTED_CONSTITUTION_REVISION, NESTED_RUNTIME_VERSION,
    NestedState, NestedProblem)
from cncm.semantic_model import (CONSTITUTION, VERSION, MAX_SEMANTIC_RECORD_BYTES,
    MemoryRef, RecallBinding, SemanticEquation, SemanticIntentType, SemanticProblem,
    SemanticRecord, SemanticState, SourceStatement, canonical_trusted_ingress,
    create_problem, ingress_digest)


def statement(**changes):
    return SourceStatement(**{"scope": "example", "key": "rate", "source_id": "user-1",
        "value": "3", "status": "USER_ATTESTED", "action": "ASSERT", "previous_digest": None,
        "source_ref": "local:user-statement", **changes})


def binding(ref=None, **changes):
    return RecallBinding(**{"ref": MemoryRef("example", "rate") if ref is None else ref,
        "value": "3", "statement_digests": (statement().statement_digest,), "statuses": ("USER_ATTESTED",),
        "receipt_digest": "a" * 64, **changes})


def problem(**changes):
    return create_problem((SemanticEquation("y", "2", "1", terms=(("x", "1"),)),
                           SemanticEquation("x", MemoryRef("example", "rate"), "0", "9")), "y", **changes)


def state():
    packet = problem()
    base = boot_state(packet.placeholder_problem().reasoning)
    body = {field.name: getattr(base, field.name) for field in fields(MachineState)}
    body.update(runtime_version=VERSION, constitution_revision=CONSTITUTION, state_hash="")
    return SemanticState(**body, procedural_artifacts=(), procedure_heads=(), native_records=(),
        native_calls=(), native_budget=NativeBudget(), native_contract_digest="f" * 64,
        ingress_digest=ingress_digest(())).with_computed_hash()


def reseal(wire):
    wire["state_hash"] = digest({key: value for key, value in wire.items() if key not in {"state_hash", "trace_head"}})
    return wire


def test_source_statement_roundtrip_identity_and_frozen_provenance():
    original = statement()
    assert SourceStatement.from_dict(json.loads(canonical_json(original.to_dict()))) == original
    assert original.statement_digest == digest(original.to_dict())
    for changes in ({"value": "4"}, {"source_ref": "local:changed"}, {"status": "TEST_FIXTURE"},
                    {"source_id": "user-2"}, {"previous_digest": "b" * 64}, {"scope": "other"}):
        assert replace(original, **changes).statement_digest != original.statement_digest
    retraction = statement(action="RETRACT", value=None, previous_digest=original.statement_digest)
    assert SourceStatement.from_dict(retraction.to_dict()).value is None
    with pytest.raises(FrozenInstanceError):
        original.value = "99"
    copy = original.to_dict()
    copy["source_ref"] = "changed"
    assert original.source_ref == "local:user-statement"


@pytest.mark.parametrize("changes", [
    {"status": "VERIFIED"}, {"status": "INDEPENDENTLY_VERIFIED"}, {"status": True},
    {"action": "UPDATE"}, {"action": "RETRACT"}, {"value": None}, {"value": True},
    {"value": "2/4"}, {"value": "-0"}, {"value": str(2**128)}, {"value": "7" * 10000},
    {"scope": "bad scope"}, {"key": "x" * 129}, {"source_id": 1},
    {"source_ref": ""}, {"source_ref": "x" * 1025}, {"previous_digest": "fake"},
])
def test_source_statement_rejects_bad_values_and_manufactured_verification(changes):
    with pytest.raises(ContractError):
        statement(**changes)


def test_reference_levels_are_requests_not_proof_statuses():
    ordinary = MemoryRef("scope", "key")
    stronger = replace(ordinary, evidence_requirement="INDEPENDENTLY_VERIFIED")
    assert ordinary != stronger and ordinary.ref_key == ("scope", "key", "ATTESTED")
    assert MemoryRef.from_dict(stronger.to_dict()) == stronger
    proposed = binding(stronger)
    assert proposed.statuses == ("USER_ATTESTED",)
    # A model can preserve an unmet demand; it cannot invent the evidence.
    with pytest.raises(ContractError):
        replace(proposed, statuses=("INDEPENDENTLY_VERIFIED",))
    with pytest.raises(ContractError):
        replace(ordinary, evidence_requirement="TRUST_ME")


@pytest.mark.parametrize("changes", [
    {"statement_digests": ()}, {"statement_digests": ("b" * 64, "a" * 64), "statuses": ("USER_ATTESTED",) * 2},
    {"statement_digests": ("a" * 64, "a" * 64), "statuses": ("USER_ATTESTED",) * 2},
    {"statement_digests": ("broken",)}, {"statuses": ()}, {"statuses": ("VERIFIED",)},
    {"receipt_digest": "bad"}, {"value": str(2**128)}, {"ref": {"scope": "example", "key": "rate"}},
])
def test_recall_binding_is_bounded_aligned_and_exact(changes):
    with pytest.raises(ContractError):
        binding(**changes)


def test_semantic_equation_has_refs_only_in_approved_scalar_positions():
    ref = MemoryRef("s", "k")
    equation = SemanticEquation("x", ref, "-3/2", ref, (("y", "2"),))
    wire = equation.to_dict()
    assert wire["a"] == ref.to_dict() and wire["constant"] == ref.to_dict()
    assert SemanticEquation.from_dict(wire) == equation
    assert equation.dependencies == ("y",)
    assert equation.placeholder_equation().a == "0"
    for changes in ({"terms": (("y", ref),)}, {"a": 3}, {"a": "01"},
                    {"terms": (("y", "0"),)}, {"terms": (("y", "1"), ("y", "2"))}):
        with pytest.raises(ContractError):
            replace(equation, **changes)


def test_reachable_refs_are_unique_sorted_and_include_evidence_level():
    a = MemoryRef("a", "k")
    strict_a = MemoryRef("a", "k", "INDEPENDENTLY_VERIFIED")
    b = MemoryRef("b", "k")
    ignored = MemoryRef("ignored", "k")
    packet = create_problem((SemanticEquation("unreachable", ignored, ignored, ignored),
        SemanticEquation("root", a, strict_a, b, (("leaf", "1"),)),
        SemanticEquation("leaf", a, "0", "1")), "root")
    assert packet.references == (a, strict_a, b)
    assert packet.reachable_variables() == frozenset({"root", "leaf"})
    assert SemanticProblem.from_dict(packet.to_dict()).references == packet.references
    cycle = create_problem((SemanticEquation("x", a, "0", "1", (("y", "1"),)),
                            SemanticEquation("y", b, "0", "1", (("x", "1"),))), "x")
    assert cycle.references == (a, b)
    missing = create_problem((SemanticEquation("x", a, "0", "1", (("missing", "1"),)),), "x")
    assert missing.references == (a,)
    assert create_problem((SemanticEquation("x", a, "0"),), "missing").references == ()


def test_resolved_problem_requires_all_reachable_bindings_and_drops_unreachable_templates():
    ref = MemoryRef("example", "rate")
    ignored = MemoryRef("other", "not-known")
    equations = (SemanticEquation("y", "2", "1", terms=(("x", "1"),)),
                 SemanticEquation("unused", ignored, "0", ref), SemanticEquation("x", ref, "0", "9"))
    packet = create_problem(equations, "y")
    resolved = packet.resolved_problem((binding(),))
    assert type(resolved) is NestedProblem
    assert tuple(row.variable for row in resolved.equations) == ("y", "x")
    assert resolved.equation_map()["x"].a == "3"
    assert resolved.reasoning == packet.reasoning and resolved.budget == packet.budget
    assert len(packet.equations) == 3 and packet.equations == equations
    assert packet.placeholder_problem().equation_map()["x"].a == "0"
    assert len(packet.placeholder_problem().equations) == 3
    for values in ((), (binding(), binding()), (binding(ignored),), (binding(), binding(ignored)), [binding()]):
        with pytest.raises(ContractError):
            packet.resolved_problem(values)
    assert packet.input_hash != replace(packet, equations=tuple(row for row in equations if row.variable != "unused")).input_hash


def test_problem_hash_binds_update_content_and_order_without_answers_or_execution_order():
    first = statement()
    correction = statement(value="4", previous_digest=first.statement_digest, source_ref="local:correction")
    packet = problem(updates=(first, correction))
    assert SemanticProblem.from_dict(packet.to_dict()).to_dict() == packet.to_dict()
    assert packet.input_hash != problem().input_hash
    assert packet.input_hash != replace(packet, updates=(correction, first)).input_hash
    assert packet.input_hash == replace(packet, equations=tuple(reversed(packet.equations))).input_hash
    assert packet.result_key == "nested_checked(y)@global"
    assert packet.reasoning.facts == packet.reasoning.rules == ()
    for changes in ({"updates": (first, first)}, {"updates": [first]},
                    {"equations": packet.equations * 2}):
        with pytest.raises(ContractError):
            replace(packet, **changes)
    for changes in ({"expected_answer": "1"}, {"execution_order": ["x", "y"]},
                    {"schema_version": "cncm.nested-problem/0.3"}):
        with pytest.raises(ContractError):
            SemanticProblem.from_dict({**packet.to_dict(), **changes})


def test_problem_retains_reserved_result_and_declared_plan_guards():
    packet = problem()
    query = packet.reasoning.query
    fact = replace(query, evidence_status=EvidenceStatus.ASSERTED, provenance=(Provenance("user", "fake"),))
    rule = Rule("fake", InferenceOperation.INFER_MODUS_PONENS, (query,), query, (Provenance("user", "fake"),))
    for changes in ({"facts": (fact,)}, {"rules": (rule,)}, {"candidates": (CandidateSpec("caller-plan"),)},
                    {"rpm_resolvers": (ResolverSpec(query, (), ()),)}):
        with pytest.raises(ContractError):
            replace(packet, reasoning=replace(packet.reasoning, **changes))


def test_trusted_ingress_canonicalization_is_external_input_not_a_fabricated_receipt():
    values = ("b" * 64, "a" * 64)
    assert canonical_trusted_ingress(values) == tuple(sorted(values))
    assert ingress_digest(values) == digest(list(sorted(values)))
    for bad in (["a" * 64], ("a" * 64, "a" * 64), ("bad",), (True,), tuple(f"{i:064x}" for i in range(257))):
        with pytest.raises(ContractError):
            canonical_trusted_ingress(bad)


def test_semantic_record_is_deeply_immutable_and_closed():
    source = {"receipt": {"status": "ATTESTED", "ids": ["source"]}}
    record = SemanticRecord.create("RECALL", source)
    source["receipt"]["ids"].append("mutated")
    copy = record.body_dict()
    copy["receipt"]["status"] = "VERIFIED"
    assert record.body_dict() == {"receipt": {"status": "ATTESTED", "ids": ["source"]}}
    assert SemanticRecord.from_dict(record.to_dict()) == record
    for changes in ({"kind": "INSTALL"}, {"kind": "STORE"}, {"record_digest": "b" * 64},
                    {"body_json": '{"a":1,"a":2}'}, {"body_json": '{"x":NaN}'}):
        with pytest.raises(ContractError):
            replace(record, **changes)
    for body in ({"x": "x" * MAX_SEMANTIC_RECORD_BYTES}, {"x": 1.0}, {"x": (1,)}, {"x": 2**512}):
        with pytest.raises(ContractError):
            SemanticRecord.create("STORE", body)


def test_semantic_state_checks_inherited_contract_and_own_complete_hash():
    source, recalled = statement(), binding()
    record = SemanticRecord.create("RECALL", {"fixture": "structure only"})
    original = replace(state(), memory_statements=(source,), memory_bindings=(recalled,),
        memory_update_index=1, ingress_digest=ingress_digest((source.statement_digest,)),
        semantic_records=(record,), memory_resolution_digest="c" * 64).with_computed_hash()
    wire = original.to_dict()
    restored = SemanticState.from_dict(json.loads(canonical_json(wire)))
    assert restored.to_dict() == wire and restored.state_hash == original.state_hash
    assert type(restored.memory_statements[0]) is SourceStatement
    assert type(restored.memory_bindings[0]) is RecallBinding
    assert replace(original, memory_resolution_digest=None).computed_hash() != original.state_hash
    assert replace(original, memory_statements=(replace(source, source_ref="changed"),)).computed_hash() != original.state_hash
    with pytest.raises(ContractError):
        NestedState.from_dict(wire)
    with pytest.raises(FrozenInstanceError):
        original.memory_update_index = 2


@pytest.mark.parametrize("mutate", [
    lambda w: w.update(runtime_version=NESTED_RUNTIME_VERSION),
    lambda w: w.update(constitution_revision=NESTED_CONSTITUTION_REVISION),
    lambda w: w.update(schema_version="cncm.nested-state/0.3"),
    lambda w: w.update(memory_update_index=True), lambda w: w.update(memory_update_index=257),
    lambda w: w.update(memory_failure=True), lambda w: w.update(ingress_digest="bad"),
    lambda w: w.update(memory_resolution_digest="bad"), lambda w: w.update(extra="ignored"),
    lambda w: w["budget"].update(ticks_remaining=True),
    lambda w: w["native_budget"].update(checker_calls_remaining=True),
    lambda w: w.update(logical_tick=True), lambda w: w.update(branch_table=w["branch_table"] * 2),
    lambda w: w.update(memory_statements=[{**statement().to_dict(), "status": "VERIFIED"}]),
    lambda w: w.update(memory_bindings=[{**binding().to_dict(), "statuses": ["VERIFIED"]}]),
])
def test_semantic_state_rejects_malformed_wire_even_if_resealed(mutate):
    wire = state().to_dict()
    mutate(wire)
    with pytest.raises(ContractError):
        SemanticState.from_dict(reseal(wire))


def test_semantic_state_caps_duplicates_and_original_hash_are_not_lost_by_temporary_decode():
    original = state()
    source = statement()
    record = SemanticRecord.create("STORE", {})
    for changes in ({"memory_statements": (source,) * 2}, {"memory_statements": (source,) * 257},
                    {"memory_bindings": (binding(),) * 2}, {"memory_bindings": (binding(),) * 49},
                    {"semantic_records": (record,) * 2}, {"semantic_records": (record,) * 1025},
                    {"memory_statements": [source]}):
        with pytest.raises(ContractError):
            replace(original, **changes)
    wire = original.to_dict()
    wire["memory_update_index"] = 1
    with pytest.raises(ContractError, match="hash mismatch"):
        SemanticState.from_dict(wire)
    wire = original.to_dict()
    wire["native_budget"]["instructions_remaining"] -= 1
    with pytest.raises(ContractError, match="hash mismatch"):
        SemanticState.from_dict(wire)


def test_all_own_wire_types_reject_unknown_keys_and_mutable_container_coercion():
    instances = (statement(), MemoryRef("s", "k"), binding(), problem(),
                 SemanticEquation("x", "1", "0"), SemanticRecord.create("STORE", {}), state())
    for original in instances:
        with pytest.raises(ContractError):
            type(original).from_dict({**original.to_dict(), "extra": True})
    wire = binding().to_dict()
    wire["statuses"] = ("USER_ATTESTED",)
    with pytest.raises(ContractError):
        RecallBinding.from_dict(wire)
    wire = problem().to_dict()
    wire["equations"] = tuple(wire["equations"])
    with pytest.raises(ContractError):
        SemanticProblem.from_dict(wire)
    assert {kind.value for kind in SemanticIntentType} == {"STORE_SOURCE", "RECALL_MEMORY", "CHECK_MEMORY_RESOLUTION"}
