"""Pure v0.3 structure/identity tests; decoded records confer no authority."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
import json

import pytest

from cncm.canonical import canonical_json, digest
from cncm.kernel import boot_state
from cncm.model import (BranchFrame, CandidateSpec, ContractError, EvidenceStatus,
    InferenceOperation, MachineState, Proposition, Provenance, ResolverSpec, Rule)
from cncm.native_model import (NativeBudget, NativeProblem, NativeProofStep,
    NativeState, CanonicalRecord)
from cncm.nested_model import (
    CAPABILITY, Equation, GraphCall, MAX_RECORD_BYTES, MAX_STATE_BYTES,
    NESTED_CONSTITUTION_REVISION, NESTED_RUNTIME_VERSION, NestedBranchFrame,
    NestedFrame, NestedInferenceOperation, NestedIntentType, NestedProblem,
    NestedProofStep, NestedRecord, NestedState, RESULT_PREDICATE, create_problem,
    nested_branch_from_dict,
)
from cncm.procedural_substrate import execute_procedure, make_candidate
from cncm.procedural_qualification import check_procedure_call


def problem():
    return create_problem((Equation("y", "2", "1", rhs_terms=(("x", "1"),)),
                           Equation("x", "3", "5", "26")), "y")


def state():
    packet = problem()
    base = boot_state(packet.reasoning)
    values = {field.name: getattr(base, field.name) for field in fields(MachineState)}
    values.update(runtime_version=NESTED_RUNTIME_VERSION, constitution_revision=NESTED_CONSTITUTION_REVISION,
                  state_hash="")
    return NestedState(**values, procedural_artifacts=(), procedure_heads=(), native_records=(),
        native_calls=(), native_budget=packet.budget,
        native_contract_digest=digest({"test-profile": "structural fixture only"})).with_computed_hash()


def call(status="OPEN", **changes):
    return GraphCall(**{"call_id": "call-y", "goal_id": "goal-y", "variable": "y",
                        "status": status, **changes})


def bound(status="BOUND", **changes):
    values = {"planned_dependencies": ("x",), "dependency_records": (("x", "a" * 64),),
              "inputs": (("a", "2"), ("b", "1"), ("c", "7")), **changes}
    if status in ("READY", "COMPLETE"):
        values.setdefault("artifact_sha256", make_candidate().artifact_sha256)
    if status == "COMPLETE":
        values.setdefault("execution_digest", "b" * 64)
        values.setdefault("output", "3")
    return call(status, **values)


def frame(kind="DEPENDENCY"):
    dependency = kind == "DEPENDENCY"
    return NestedFrame(frame_id="frame-y", goal_id="goal-child", parent_goal_id="goal-y",
        branch_id="branch-main", target_foundation=None, blocked_prerequisite="x" if dependency else CAPABILITY,
        return_address="call:call-y:dependencies" if dependency else "call:call-y:procedure",
        resume_stage="DEPENDENCY_BIND" if dependency else "PROCEDURE_APPLY",
        expected_result_key="checked-child", depth=1, kind=kind, call_id="call-y",
        child_call_id="call-x" if dependency else None, dependency_variable="x" if dependency else None,
        parent_call_digest="a" * 64, parent_branch_digest="b" * 64,
        entry_instruction_budget=512, entry_checker_budget=128)


def proof():
    provenance = (Provenance("nested_execution", "record-fixture", "structural fixture"),)
    conclusion = Proposition(RESULT_PREDICATE, ("y",), evidence_status=EvidenceStatus.DERIVED,
                             provenance=provenance)
    return NestedProofStep.create_checked(conclusion=conclusion, branch_id="branch-main",
                                         execution_digest="a" * 64, provenance=provenance)


def reseal_state(wire):
    wire["state_hash"] = digest({key: value for key, value in wire.items() if key not in {"state_hash", "trace_head"}})
    return wire


def test_equations_describe_dependencies_without_a_caller_plan():
    packet = problem()
    assert packet.equation_map()["y"].dependencies == ("x",)
    assert packet.reasoning.facts == packet.reasoning.rules == packet.reasoning.candidates == packet.reasoning.rpm_resolvers == ()
    assert packet.result_key == "nested_checked(y)@global"
    assert packet.input_hash == NestedProblem.from_dict(json.loads(canonical_json(packet.to_dict()))).input_hash
    reordered = replace(packet, equations=tuple(reversed(packet.equations)))
    assert reordered.to_dict() == packet.to_dict() and reordered.input_hash == packet.input_hash
    assert {row.entity_id for row in packet.reasoning.entities} == {"x", "y"}
    assert "expected_answer" not in canonical_json(packet.to_dict())


def test_missing_query_reference_cycle_and_zero_slope_remain_diagnosable():
    assert create_problem((), "missing").equation_map() == {}
    dangling = create_problem((Equation("y", "0", "1", rhs_terms=(("missing", "2"),)),), "y")
    assert {row.entity_id for row in dangling.reasoning.entities} == {"missing", "y"}
    self_cycle = create_problem((Equation("x", "1", "0", rhs_terms=(("x", "1"),)),), "x")
    assert self_cycle.equation_map()["x"].dependencies == ("x",)
    cycle = create_problem((Equation("x", "1", "0", rhs_terms=(("y", "1"),)),
                            Equation("y", "1", "0", rhs_terms=(("x", "1"),))), "x")
    assert NestedProblem.from_dict(cycle.to_dict()).to_dict() == cycle.to_dict()


@pytest.mark.parametrize("bad", [True, 1, "01", "-0", "+1", "2/4", "1/0", "1/-2", str(2**128), "1" * 10000])
def test_equation_rationals_are_exact_canonical_and_bounded(bad):
    with pytest.raises(ContractError):
        Equation("x", bad, "0")


@pytest.mark.parametrize("terms", [(('x', '0'),), (("y", "1"), ("x", "1")),
    (("x", "1"), ("x", "2")), tuple((f"x{i}", "1") for i in range(5)),
    [["x", "1"]], (("x", 1),)])
def test_equation_terms_are_sorted_unique_nonzero_and_bounded(terms):
    with pytest.raises(ContractError):
        Equation("z", "1", "0", rhs_terms=terms)


def test_problem_caps_versions_and_reserved_authority():
    with pytest.raises(ContractError):
        create_problem(tuple(Equation(f"x{i}", "1", "0") for i in range(17)), "x0")
    with pytest.raises(ContractError, match="duplicate"):
        create_problem((Equation("x", "1", "0"), Equation("x", "2", "0")), "x")
    packet = problem()
    forged = Proposition(RESULT_PREDICATE, ("y",), evidence_status=EvidenceStatus.ASSERTED,
                         provenance=(Provenance("user", "forgery"),))
    with pytest.raises(ContractError, match="reserved"):
        replace(packet, reasoning=replace(packet.reasoning, facts=(forged,)))
    rule = Rule("forgery", InferenceOperation.INFER_MODUS_PONENS, (packet.reasoning.query,),
                packet.reasoning.query, (Provenance("user", "forgery"),))
    with pytest.raises(ContractError, match="reserved"):
        replace(packet, reasoning=replace(packet.reasoning, rules=(rule,)))
    for changes in ({"candidates": (CandidateSpec("supplied-plan"),)},
                    {"rpm_resolvers": (ResolverSpec(packet.reasoning.query, (), ()),)}):
        with pytest.raises(ContractError, match="forbid"):
            replace(packet, reasoning=replace(packet.reasoning, **changes))
    for changes in ({"schema_version": "cncm.native-problem/0.2"}, {"plan_order": ["x", "y"]}):
        with pytest.raises(ContractError):
            NestedProblem.from_dict({**packet.to_dict(), **changes})
    with pytest.raises(ContractError):
        NativeProblem.from_dict(packet.to_dict())


@pytest.mark.parametrize("changes", [{"max_ticks": True}, {"max_ticks": 1025}, {"max_ticks": 1},
    {"rpm_depth_limit": True}, {"rpm_depth_limit": 9}, {"rpm_depth_limit": 0}, {"budget": {}}])
def test_problem_budget_inputs_reject_bool_overflow_and_untyped(changes):
    with pytest.raises(ContractError):
        create_problem((), "x", **changes)


def test_call_lifecycle_preserves_bindings_and_hides_incomplete_answers():
    for original in (call("NEW"), call(), call("WAITING_DEPENDENCY", planned_dependencies=("x",)),
                     bound(), bound("READY"), bound("WAITING_PROCEDURE"), bound("COMPLETE"),
                     bound("FAILED", failure="INPUT_BOUND_EXCEEDED"), call("FAILED", failure="MISSING_INFORMATION")):
        assert GraphCall.from_dict(original.to_dict()) == original
        assert original.call_digest == digest(original.to_dict())
    ready = bound("READY")
    assert ready.inputs_digest == execute_procedure(make_candidate(), ready.inputs_dict()).inputs_sha256
    external = ready.inputs_dict()
    external["a"] = "999"
    assert ready.inputs_dict()["a"] == "2"
    with pytest.raises(FrozenInstanceError):
        ready.output = "3"
    for status in ("NEW", "OPEN", "WAITING_DEPENDENCY", "WAITING_PROCEDURE", "BOUND", "READY", "FAILED"):
        with pytest.raises(ContractError):
            replace(bound("COMPLETE"), status=status)


@pytest.mark.parametrize("changes", [
    {"status": "COMPLETE"}, {"status": "READY"}, {"status": "BOUND"}, {"status": "WAITING_PROCEDURE"},
    {"status": "WAITING_DEPENDENCY"}, {"status": "FAILED"}, {"status": "OTHER"},
    {"status": "NEW", "planned_dependencies": ("x",)},
    {"dependency_records": (("x", "a" * 64),)},
    {"inputs": (("a", "1"), ("b", "2"), ("c", "3"))},
    {"artifact_sha256": "a" * 64}, {"failure": "FAILURE"},
])
def test_call_rejects_inconsistent_lifecycle(changes):
    with pytest.raises(ContractError):
        call(**changes)


def test_call_complete_output_has_separate_512_bit_bound():
    large = str(2**256)
    done = bound("COMPLETE", output=large)
    assert GraphCall.from_dict(done.to_dict()).output == large
    with pytest.raises(ContractError):
        bound("COMPLETE", output=str(2**512))
    with pytest.raises(ContractError):
        bound(inputs=(("a", "1"), ("b", "0"), ("c", large)))
    with pytest.raises(ContractError):
        bound(dependency_records=())


def test_nested_frames_bind_parent_and_have_distinct_return_stages():
    for kind in ("DEPENDENCY", "PROCEDURE_ACQUISITION"):
        original = frame(kind)
        assert NestedFrame.from_dict(original.to_dict()) == original
        assert original.parent_call_digest == "a" * 64
    for changes in ({"kind": "RPM"}, {"branch_id": "other"}, {"goal_id": "goal-y"},
        {"call_id": "changed"}, {"child_call_id": "call-y"}, {"child_call_id": None},
        {"dependency_variable": None}, {"parent_call_digest": "bad"}, {"depth": True}, {"depth": 9},
        {"entry_instruction_budget": True}, {"entry_checker_budget": -1}, {"resume_stage": "PROCEDURE_APPLY"}):
        with pytest.raises(ContractError):
            replace(frame(), **changes)
    with pytest.raises(ContractError):
        replace(frame("PROCEDURE_ACQUISITION"), child_call_id="foreign")


def test_records_are_deeply_immutable_and_schema_bound():
    body = {"rows": [{"call": "x"}], "cost": 6}
    record = NestedRecord.create("EXECUTION", body)
    body["rows"][0]["call"] = "mutated"
    external = record.body_dict()
    external["rows"].append({})
    assert record.body_dict() == {"rows": [{"call": "x"}], "cost": 6}
    assert NestedRecord.from_dict(record.to_dict()) == record
    assert CanonicalRecord.create("EXECUTION", record.body_dict()).record_digest != record.record_digest
    for changes in ({"kind": "UNKNOWN"}, {"kind": "RETURN"}, {"record_digest": "f" * 64},
                    {"body_json": '{"cost":6,"rows": [{"call":"x"}]}'},
                    {"body_json": '{"a":1,"a":2}'}, {"body_json": '{"a":NaN}'},
                    {"body_json": '[]'}):
        with pytest.raises(ContractError):
            replace(record, **changes)
    for body in ({"x": 1.0}, {"x": (1, 2)}, {"x": 2**512}, {"x": "x" * MAX_RECORD_BYTES}):
        with pytest.raises(ContractError):
            NestedRecord.create("RETURN", body)


def test_real_large_exact_math_receipt_is_recordable_without_widening_counters():
    value = 2**127 - 1
    report = check_procedure_call(make_candidate(), {"a": "1/" + str(value), "b": "0", "c": str(value)},
                                 call_id="large-call", branch_id="branch-main")
    assert report["status"] == "CHECKED"
    assert int(report["execution"]["outputs"]["x"]).bit_length() == 254
    record = NestedRecord.create("EXECUTION", {"report": report})
    assert NestedRecord.from_dict(record.to_dict()).body_dict() == {"report": report}
    retained = replace(state(), native_records=(record,)).with_computed_hash()
    assert NestedState.from_dict(retained.to_dict()).state_hash == retained.state_hash
    with pytest.raises(ContractError):
        NativeBudget(2**64, 1)
    with pytest.raises(ContractError):
        NestedRecord.create("EXECUTION", {"integer": -(2**512)})


def test_aggregate_record_limit_precedes_serialization(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("oversized aggregate reached serialization")
    monkeypatch.setattr("cncm.nested_model.canonical_json", forbidden)
    with pytest.raises(ContractError, match="aggregate text"):
        NestedRecord.create("EXECUTION", {"a": "a" * 140000, "b": "b" * 140000})


def test_nested_proof_is_own_version_and_every_field_is_bound():
    checked = proof()
    assert NestedProofStep.from_dict(checked.to_dict()) == checked
    assert checked.operation is NestedInferenceOperation.CHECKED_NESTED_EQUATION
    assert checked.step_id == "nested-proof-" + digest({key: value for key, value in checked.to_dict().items() if key != "step_id"})
    with pytest.raises(ContractError):
        NativeProofStep.from_dict(checked.to_dict())
    for changes in ({"verified": 1}, {"verified": False}, {"schema_version": "cncm.native-proof/0.2"},
                    {"execution_digest": "b" * 64}, {"premise_keys": ["external"]}, {"step_id": "forged"}):
        with pytest.raises(ContractError):
            NestedProofStep.from_dict({**checked.to_dict(), **changes})
    bad = checked.to_dict()
    bad["conclusion"]["predicate"] = "procedure_checked"
    bad["step_id"] = "nested-proof-" + digest({key: value for key, value in bad.items() if key != "step_id"})
    with pytest.raises(ContractError):
        NestedProofStep.from_dict(bad)


def test_state_roundtrip_keeps_typed_frames_records_calls_and_proofs():
    original = state()
    artifact, checked = make_candidate(), proof()
    base = original.branch_table[0]
    values = {field.name: getattr(base, field.name) for field in fields(BranchFrame)}
    values.update(propositions=(checked.conclusion,), proof_steps=(checked,))
    branch = NestedBranchFrame(**values)
    assert nested_branch_from_dict(branch.to_dict()).to_dict() == branch.to_dict()
    original = replace(original, procedural_artifacts=(artifact,),
        procedure_heads=((CAPABILITY, artifact.artifact_sha256),), native_calls=(bound("COMPLETE"),),
        native_records=(NestedRecord.create("EXECUTION", {"fixture": "structure only"}),),
        branch_table=(branch,), rpm_stack=(frame(),), active_goal_id="goal-child").with_computed_hash()
    wire = original.to_dict()
    restored = NestedState.from_dict(json.loads(canonical_json(wire)))
    assert restored.to_dict() == wire and restored.state_hash == original.state_hash
    assert type(restored.rpm_stack[0]) is NestedFrame
    assert type(restored.native_calls[0]) is GraphCall
    assert type(restored.branch_table[0].proof_steps[0]) is NestedProofStep
    assert replace(restored, native_budget=NativeBudget(511, 128)).computed_hash() != restored.state_hash
    with pytest.raises(ContractError):
        NativeState.from_dict(wire)


@pytest.mark.parametrize("mutate", [
    lambda w: w.update(schema_version="cncm.nested-state/0.2"),
    lambda w: w.update(runtime_version="0.2.0"),
    lambda w: w.update(constitution_revision="cncm-constitution/0.2"),
    lambda w: w.update(logical_tick=True), lambda w: w.update(seed=1.0),
    lambda w: w.update(episodic_memory_revision="0"), lambda w: w.update(extra="ignored"),
    lambda w: w["budget"].update(ticks_remaining=True),
    lambda w: w["native_budget"].update(instructions_remaining=True),
    lambda w: w["native_budget"].update(checker_calls_remaining=100001),
    lambda w: w.update(prior_episode_state_hash="bad"),
    lambda w: w.update(native_contract_digest="bad"),
    lambda w: w.update(pending_intents=[True]),
    lambda w: w.update(procedure_heads=[[CAPABILITY, "a" * 64]]),
    lambda w: w.update(rpm_stack=[{}]),
    lambda w: w.update(branch_table=w["branch_table"] * 2),
])
def test_state_rejects_malformed_wire_even_after_resealing(mutate):
    wire = state().to_dict()
    mutate(wire)
    with pytest.raises(ContractError):
        NestedState.from_dict(reseal_state(wire))


def test_state_rejects_duplicates_caps_stale_hash_and_mutable_values():
    original = state()
    record = NestedRecord.create("RETURN", {"x": "fixture"})
    for changes in ({"native_records": (record, record)}, {"native_calls": (call(), call())},
                    {"native_calls": tuple(GraphCall(f"c{i}", f"g{i}", f"x{i}") for i in range(17))},
                    {"procedural_artifacts": (make_candidate(), make_candidate())},
                    {"native_records": (record,) * 513}, {"native_calls": [call()]},
                    {"native_calls": (bound("READY"),)}):
        with pytest.raises(ContractError):
            replace(original, **changes)
    stale = original.to_dict()
    stale["native_budget"]["instructions_remaining"] -= 1
    with pytest.raises(ContractError, match="hash mismatch"):
        NestedState.from_dict(stale)


def test_state_aggregate_record_bound_precedes_serialization(monkeypatch):
    original = state()
    records = tuple(NestedRecord.create("DECOMPOSITION", {"index": index, "text": "x" * 240000})
                    for index in range(35))
    def forbidden(*args, **kwargs):
        pytest.fail("oversized state reached JSON serialization")
    monkeypatch.setattr("cncm.nested_model.canonical_json", forbidden)
    with pytest.raises(ContractError, match="before serialization"):
        replace(original, native_records=records)


def test_state_exact_byte_bound_counts_escaped_record_content():
    original = state()
    records = tuple(NestedRecord.create("DECOMPOSITION", {"index": index, "text": '"' * 110000})
                    for index in range(20))
    assert sum(len(row.body_json) for row in records) < MAX_STATE_BYTES
    with pytest.raises(ContractError, match="nested state byte bound"):
        replace(original, native_records=records)


def test_all_new_wire_decoders_reject_unknown_fields_bool_and_container_coercion():
    for original in (Equation("x", "1", "0"), problem(), call(), frame(),
                     NestedRecord.create("RETURN", {}), proof(), state()):
        with pytest.raises(ContractError):
            type(original).from_dict({**original.to_dict(), "extra": True})
    wire = Equation("x", "1", "0", rhs_terms=(("y", "1"),)).to_dict()
    wire["rhs_terms"] = (("y", "1"),)
    with pytest.raises(ContractError):
        Equation.from_dict(wire)
    wire = bound().to_dict()
    wire["inputs"]["a"] = True
    with pytest.raises(ContractError):
        GraphCall.from_dict(wire)
    assert len(NestedIntentType) == 12
    with pytest.raises(ValueError):
        NestedIntentType("PROTECTED_PATCH")
