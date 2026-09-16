"""Pure contract tests; successful decoding is never installation authority."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
import json

import pytest

from cncm.canonical import canonical_json, digest
from cncm.kernel import boot_state
from cncm.model import (
    BranchFrame, ContractError, EntityDecl, EvidenceStatus, InferenceOperation,
    IntentType, MachineState, PredicateDecl, ProblemPacket, ProofStep, Proposition,
    Provenance, Rule,
)
from cncm.native_model import (
    AcquisitionFrame, CAPABILITY, CallSpec, CallState, CanonicalRecord,
    MAX_RECORD_BYTES, NATIVE_CONSTITUTION_REVISION, NATIVE_PROBLEM_SCHEMA,
    NATIVE_RUNTIME_VERSION, NativeBranchFrame, NativeBudget, NativeInferenceOperation,
    NativeIntentType, NativeProblem, NativeProofStep, NativeState, OUTPUT_CONTRACT,
    RESULT_PREDICATE, native_branch_from_dict,
)
from cncm.procedural_substrate import execute_procedure, make_candidate


def problem():
    call = CallSpec.create(call_id="call-linear", goal_id="goal-linear",
                           inputs={"a": "3", "b": "5", "c": "26"})
    reasoning = ProblemPacket(
        schema_version="cncm.problem/0.1", problem_id="linear-parent", goal_id=call.goal_id,
        seed=20260916, entities=(EntityDecl(call.call_id, "call"),),
        predicates=(PredicateDecl(RESULT_PREDICATE, ("call",)), PredicateDecl("done", ("call",))),
        facts=(), rules=(), query=Proposition("done", (call.call_id,)))
    return NativeProblem(reasoning, call)


def state():
    packet = problem()
    base = boot_state(packet.reasoning)
    body = {field.name: getattr(base, field.name) for field in fields(MachineState)}
    body.update(runtime_version=NATIVE_RUNTIME_VERSION,
                constitution_revision=NATIVE_CONSTITUTION_REVISION, state_hash="")
    return NativeState(**body, procedural_artifacts=(), procedure_heads=(), native_records=(),
                       native_calls=(), native_budget=packet.budget,
                       native_contract_digest=digest({"trusted-profile": "test"})).with_computed_hash()


def proof():
    provenance = (Provenance("native_checked_call", "call-linear", "independent receipt"),)
    conclusion = Proposition(RESULT_PREDICATE, ("call-linear",),
                             evidence_status=EvidenceStatus.DERIVED, provenance=provenance)
    return NativeProofStep.create_checked(conclusion=conclusion, branch_id="branch-main",
                                          execution_digest="a" * 64, provenance=provenance)


def reseal_state(body):
    payload = {key: value for key, value in body.items() if key not in {"state_hash", "trace_head"}}
    body["state_hash"] = digest(payload)
    return body


def reseal_proof(body):
    body["step_id"] = "native-proof-" + digest({key: value for key, value in body.items() if key != "step_id"})
    return body


def test_native_problem_roundtrip_and_input_identity():
    packet = problem()
    decoded = NativeProblem.from_dict(json.loads(canonical_json(packet.to_dict())))
    assert decoded.to_dict() == packet.to_dict()
    assert decoded.input_hash == digest(packet.to_dict())
    assert decoded.call.inputs_digest == execute_procedure(make_candidate(), packet.call.inputs_dict()).inputs_sha256
    changed = replace(packet, call=CallSpec.create(call_id="call-linear", goal_id="goal-linear",
                                                inputs={"a": "3", "b": "5", "c": "29"}))
    assert changed.input_hash != packet.input_hash
    assert changed.call.inputs_digest != packet.call.inputs_digest
    assert decoded.call.result_key == "procedure_checked(call-linear)@global"
    external = decoded.call.inputs_dict()
    external["a"] = "999"
    assert decoded.call.inputs_dict()["a"] == "3"


@pytest.mark.parametrize("bad", [True, 1.0, "1", -1, 1_000_001])
def test_native_budget_rejects_noninteger_or_oversized_instruction_counters(bad):
    with pytest.raises(ContractError):
        NativeBudget(bad, 1)


@pytest.mark.parametrize("bad", [True, 1.0, "1", -1, 100_001])
def test_native_budget_rejects_noninteger_or_oversized_checker_counters(bad):
    with pytest.raises(ContractError):
        NativeBudget(1, bad)


@pytest.mark.parametrize("bad", [True, 3, "01", "+1", "-0", "2/4", "1/0", "1/-2", str(2**128), "9" * 10000])
def test_call_inputs_are_bounded_canonical_rationals(bad):
    with pytest.raises(ContractError):
        CallSpec.create(call_id="call-linear", goal_id="goal-linear", inputs={"a": bad, "b": "5", "c": "26"})


def test_zero_input_is_structurally_valid_for_later_domain_rejection():
    call = CallSpec.create(call_id="call-linear", goal_id="goal-linear", inputs={"a": "0", "b": "5", "c": "26"})
    assert call.inputs_dict()["a"] == "0"


def test_call_scope_matches_reasoning_query_and_result_identity():
    packet = problem()
    with pytest.raises(ContractError, match="scope"):
        replace(packet, reasoning=replace(packet.reasoning, query=replace(packet.reasoning.query, scope="case_scope")))
    packet = replace(packet, call=replace(packet.call, result_scope="case_scope"),
                     reasoning=replace(packet.reasoning, query=replace(packet.reasoning.query, scope="case_scope")))
    assert packet.call.result_key == "procedure_checked(call-linear)@case_scope"
    assert NativeProblem.from_dict(packet.to_dict()).to_dict() == packet.to_dict()


@pytest.mark.parametrize("field,value", [("schema_version", "cncm.problem/0.1"), ("extra", True)])
def test_native_problem_rejects_wrong_version_and_unknown_fields(field, value):
    wire = problem().to_dict()
    wire[field] = value
    with pytest.raises(ContractError):
        NativeProblem.from_dict(wire)


@pytest.mark.parametrize("field,value", [("capability", "other"), ("output_contract", "other"),
                                         ("branch_id", "branch-other"), ("result_predicate", "done"),
                                         ("goal_id", "other")])
def test_native_problem_rejects_contract_or_scope_substitution(field, value):
    wire = problem().to_dict()
    wire["call"][field] = value
    with pytest.raises(ContractError):
        NativeProblem.from_dict(wire)


def test_reserved_result_cannot_be_asserted_or_derived_by_input_rule():
    packet = problem()
    result = Proposition(RESULT_PREDICATE, (packet.call.call_id,),
                         evidence_status=EvidenceStatus.ASSERTED,
                         provenance=(Provenance("user", "example"),))
    with pytest.raises(ContractError, match="reserved"):
        replace(packet, reasoning=replace(packet.reasoning, facts=(result,)))
    rule = Rule("forge", InferenceOperation.INFER_MODUS_PONENS,
                (Proposition("done", (packet.call.call_id,)),), result,
                (Provenance("user", "example"),))
    with pytest.raises(ContractError, match="reserved"):
        replace(packet, reasoning=replace(packet.reasoning, rules=(rule,)))


def test_native_problem_rejects_declared_candidate_and_resolver():
    from cncm.model import CandidateSpec, ResolverSpec
    packet = problem()
    for kwargs in ({"candidates": (CandidateSpec("candidate"),)},
                   {"rpm_resolvers": (ResolverSpec(packet.reasoning.query, (), ()),)}):
        with pytest.raises(ContractError):
            replace(packet, reasoning=replace(packet.reasoning, **kwargs))


def test_native_enums_are_separate_and_closed():
    assert len(NativeIntentType) == 7
    assert len(NativeInferenceOperation) == 1
    assert set(item.value for item in NativeIntentType).isdisjoint(item.value for item in IntentType)
    with pytest.raises(ValueError):
        NativeIntentType("PROTECTED_PATCH")


def test_call_state_only_complete_can_carry_answer():
    for status in ("REQUESTED", "SUSPENDED", "READY", "FAILED"):
        with pytest.raises(ContractError):
            CallState("call-linear", status, "a" * 64, "b" * 64, "7")
    with pytest.raises(ContractError):
        CallState("call-linear", "READY")
    with pytest.raises(ContractError):
        CallState("call-linear", "COMPLETE", "a" * 64)
    done = CallState("call-linear", "COMPLETE", "a" * 64, "b" * 64, "-3/2")
    assert CallState.from_dict(done.to_dict()) == done
    with pytest.raises(FrozenInstanceError):
        done.output = "99"


def test_record_deep_immutability_and_digest_binding():
    source = {"nested": {"rows": [1, 2]}}
    record = CanonicalRecord.create("EXECUTION", source)
    source["nested"]["rows"][0] = 9
    copy = record.body_dict()
    copy["nested"]["rows"].append(3)
    assert record.body_dict() == {"nested": {"rows": [1, 2]}}
    assert CanonicalRecord.from_dict(record.to_dict()) == record
    with pytest.raises(ContractError):
        replace(record, kind="INSTALLATION")
    with pytest.raises(ContractError):
        replace(record, body_json='{"nested": {"rows": [1, 2]}}')


@pytest.mark.parametrize("body", [{"n": 1.0}, {"n": float("nan")}, {"n": 2**64}, {"n": (1, 2)},
                                   {"x": "x" * (MAX_RECORD_BYTES + 1)}])
def test_record_rejects_noncanonical_or_oversized_json(body):
    with pytest.raises(ContractError):
        CanonicalRecord.create("EXECUTION", body)


def test_record_accepts_actual_fixed_selection_report_under_declared_cap():
    from cncm.procedural_qualification import select_finite_candidate
    _, report = select_finite_candidate()
    record = CanonicalRecord.create("SELECTION", report)
    assert len(record.body_json.encode("utf-8")) < MAX_RECORD_BYTES


def test_native_proof_full_digest_and_union_branch_roundtrip():
    checked = proof()
    assert NativeProofStep.from_dict(checked.to_dict()) == checked
    assert len(checked.step_id) == len("native-proof-") + 64
    base = state().branch_table[0]
    branch = replace(base, propositions=(checked.conclusion,), proof_steps=(checked,))
    # A v0.1 decoder cannot silently reinterpret the extended proof.
    from cncm.native_model import native_branch_to_dict
    wire = native_branch_to_dict(branch)
    with pytest.raises(ContractError):
        BranchFrame.from_dict(wire)
    restored = native_branch_from_dict(wire)
    assert type(restored) is NativeBranchFrame
    assert type(restored.proof_steps[0]) is NativeProofStep
    assert restored.to_dict() == wire


@pytest.mark.parametrize("mutate", [
    lambda w: w.update(execution_digest="b" * 64),
    lambda w: w.update(verified=False),
    lambda w: w.update(verified=1),
    lambda w: w.update(schema_version="cncm.native-proof/0.1"),
    lambda w: w.update(premise_keys=["external-truth"]),
    lambda w: w["conclusion"].update(polarity=False),
    lambda w: w["conclusion"].update(evidence_status="asserted"),
])
def test_native_proof_rejects_tampering_even_when_shape_resealed(mutate):
    wire = proof().to_dict()
    mutate(wire)
    with pytest.raises(ContractError):
        NativeProofStep.from_dict(wire)
    if wire["execution_digest"] != "b" * 64:
        with pytest.raises(ContractError):
            NativeProofStep.from_dict(reseal_proof(wire))


def frame():
    return AcquisitionFrame(frame_id="frame-native", goal_id="goal-child", parent_goal_id="goal-linear",
        branch_id="branch-main", target_foundation=None, blocked_prerequisite=CAPABILITY,
        return_address="branch:branch-main:procedure:call-linear", resume_stage="PROCEDURE_CALL",
        expected_result_key=OUTPUT_CONTRACT, depth=1, call_id="call-linear", inputs_digest="a" * 64,
        parent_branch_digest="b" * 64, capability=CAPABILITY, output_contract=OUTPUT_CONTRACT,
        entry_instruction_budget=512, entry_checker_budget=128)


def test_acquisition_frame_roundtrip_and_bound_parent_scope():
    original = frame()
    assert AcquisitionFrame.from_dict(original.to_dict()) == original
    for field, value in (("branch_id", "other"), ("call_id", "other"), ("resume_stage", "INFERENCE"),
                         ("expected_result_key", "other"), ("entry_instruction_budget", True),
                         ("inputs_digest", "broken"), ("kind", "RPM"), ("goal_id", "goal-linear")):
        with pytest.raises(ContractError):
            AcquisitionFrame.from_dict({**original.to_dict(), field: value})


def test_native_state_roundtrip_includes_artifacts_native_proofs_and_frame():
    original = state()
    artifact = make_candidate()
    checked = proof()
    branch = replace(original.branch_table[0], propositions=(checked.conclusion,), proof_steps=(checked,))
    original = replace(original, procedural_artifacts=(artifact,), procedure_heads=((CAPABILITY, artifact.artifact_sha256),),
        native_calls=(CallState("call-linear", "COMPLETE", artifact.artifact_sha256, "a" * 64, "7"),),
        native_records=(CanonicalRecord.create("EXECUTION", {"receipt": "example"}),),
        branch_table=(branch,), rpm_stack=(frame(),), active_goal_id="goal-child").with_computed_hash()
    wire = original.to_dict()
    assert wire["procedural_artifacts"][0] == artifact.to_dict()
    restored = NativeState.from_dict(json.loads(canonical_json(wire)))
    assert restored.to_dict() == wire
    assert type(restored.rpm_stack[0]) is AcquisitionFrame
    assert type(restored.branch_table[0].proof_steps[0]) is NativeProofStep
    assert restored.state_hash == original.state_hash
    assert replace(original, native_budget=NativeBudget(511, 128)).computed_hash() != original.state_hash


@pytest.mark.parametrize("mutate", [
    lambda w: w.update(extra="ignored"),
    lambda w: w.update(runtime_version="0.1.0"),
    lambda w: w.update(constitution_revision="cncm-constitution/0.1"),
    lambda w: w.update(logical_tick=True),
    lambda w: w.update(seed=1.0),
    lambda w: w.update(episodic_memory_revision="0"),
    lambda w: w["budget"].update(ticks_remaining=True),
    lambda w: w["budget"].update(ticks_remaining="128"),
    lambda w: w["global_workspace"].update(recalled_memory_ids=[1]),
    lambda w: w["global_workspace"].update(extra=True),
    lambda w: w["commitment_state"].update(gate_results=[["gate", 1]]),
    lambda w: w["branch_table"][0].update(created_at_tick=True),
    lambda w: w.update(native_calls=[CallState("call-linear").to_dict()] * 9),
    lambda w: w.update(native_records=[CanonicalRecord.create("EXECUTION", {}).to_dict()] * 129),
    lambda w: w.update(procedure_heads=[[CAPABILITY, "a" * 64]]),
])
def test_native_state_rejects_rehashed_invalid_wire(mutate):
    wire = state().to_dict()
    mutate(wire)
    with pytest.raises(ContractError):
        NativeState.from_dict(reseal_state(wire))


def test_native_state_rejects_unrehashed_change_and_preserves_v1_hashing():
    original = state()
    wire = original.to_dict()
    wire["native_budget"]["instructions_remaining"] -= 1
    with pytest.raises(ContractError, match="hash mismatch"):
        NativeState.from_dict(wire)
    base = boot_state(problem().reasoning)
    old_wire = base.to_dict()
    assert MachineState.from_dict(old_wire).to_dict() == old_wire
    assert base.state_hash == base.computed_hash()
    assert "native_calls" not in old_wire


def test_legacy_proof_remains_decodable_inside_native_branch():
    base = state().branch_table[0]
    conclusion = Proposition("done", ("call-linear",), evidence_status=EvidenceStatus.DERIVED)
    ordinary = ProofStep.create(operation=InferenceOperation.INFER_MODUS_PONENS,
        premise_keys=("source(call-linear)@global",), rule_id="rule-one", conclusion=conclusion,
        substitution={}, branch_id=base.branch_id, verified=True, provenance=())
    branch = replace(base, proof_steps=(ordinary,))
    assert native_branch_from_dict(branch.to_dict()).proof_steps == (ordinary,)


def test_unknown_native_record_kind_is_rejected():
    with pytest.raises(ContractError, match="unsupported native record kind"):
        CanonicalRecord.create("IMPORT_AUTHORITY", {})


def test_duplicate_native_record_digest_is_rejected_even_when_state_rehashed():
    record = CanonicalRecord.create("EXECUTION", {"fixture_only": True})
    with pytest.raises(ContractError, match="duplicate native record"):
        replace(state(), native_records=(record, record))
    wire = state().to_dict()
    wire["native_records"] = [record.to_dict(), record.to_dict()]
    with pytest.raises(ContractError, match="duplicate native record"):
        NativeState.from_dict(reseal_state(wire))
