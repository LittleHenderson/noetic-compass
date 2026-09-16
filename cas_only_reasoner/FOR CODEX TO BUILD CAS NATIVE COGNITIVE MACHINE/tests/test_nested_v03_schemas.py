"""Closed v0.3 wire engineering checks; typed parsing/replay retain authority."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validators
from referencing import Registry, Resource

from cncm.canonical import digest
from cncm.model import ContractError, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.native_profile import load_native_profile
from cncm.nested_engine import NestedMachine
from cncm.nested_kernel import nested_intent
from cncm.nested_model import (Equation, NestedIntentType, NestedProblem, NestedProofStep,
    NestedState, NESTED_RECORD_KINDS, create_problem)
from cncm.nested_profile import NESTED_AUTHORITIES, NESTED_WORK_COSTS, SOURCE_FILES, load_nested_profile
from cncm.nested_recovery import recover_nested_journal
from cncm.procedural_substrate import make_candidate

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
NESTED = SCHEMAS / "nested_v0_3"
BASE = "https://cas.local/schemas/nested_v0_3/contracts.schema.json"
STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
    "integer", lambda checker, value: type(value) is int))


@lru_cache(maxsize=1)
def registry():
    documents = [json.loads(path.read_text()) for path in SCHEMAS.rglob("*.schema.json")]
    return Registry().with_resources((doc["$id"], Resource.from_contents(doc)) for doc in documents)


@lru_cache(maxsize=64)
def validator(kind):
    return STRICT({"$ref": BASE + "#/$defs/" + kind}, registry=registry())


def validate(kind, value):
    validator(kind).validate(value)


def decoded_bodies(state, checked=None):
    for record in state["native_records"]:
        key = (record["kind"], record["body_json"])
        if checked is None or key not in checked:
            validate("record_body_" + record["kind"], json.loads(record["body_json"]))
            if checked is not None:
                checked.add(key)


def graph():
    return create_problem((Equation("y", "2", "1", rhs_terms=(("x", "1"),)),
                           Equation("x", "3", "5", "26")), "y")


def machine_shapes(machine, checked=None):
    value = machine.state.to_dict()
    validate("problem", machine.problem.to_dict())
    validate("source_profile", machine.profile.to_dict())
    validate("state", value)
    decoded_bodies(value, checked)
    validate("evidence", machine.evidence)
    validate("journal", machine.journal())
    for frame in value["rpm_stack"]:
        validate("frame", frame)
    for event in machine.coordinator.trace.events:
        validate("trace", event.to_dict())
        for intent in event.proposed_intents:
            if type(intent.intent_type) is NestedIntentType and intent.intent_id in event.authorized_intent_ids:
                validate("accepted_intent", intent.to_dict())
    for branch in machine.state.branch_table:
        for proof in branch.proof_steps:
            if type(proof) is NestedProofStep:
                validate("proof", proof.to_dict())
    return {row["kind"] for row in value["native_records"]}


@pytest.fixture(scope="module")
def completed():
    machine = NestedMachine(load_nested_profile())
    result = machine.run(graph())
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output == "3"
    return machine


def test_new_schemas_are_valid_closed_and_source_bound_without_changing_v02():
    def objects(value):
        if type(value) is dict:
            yield value
            for child in value.values():
                yield from objects(child)
        elif type(value) is list:
            for child in value:
                yield from objects(child)
    paths = tuple(NESTED.glob("*.schema.json"))
    assert len(paths) == 9
    for path in paths:
        doc = json.loads(path.read_text())
        Draft202012Validator.check_schema(doc)
        for item in objects(doc):
            if item.get("type") == "object":
                assert item.get("additionalProperties") is False
    assert {path.relative_to(ROOT).as_posix() for path in paths} <= set(SOURCE_FILES)
    assert load_native_profile().profile_digest == "c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607"


def test_every_reference_resolves_offline():
    def references(value):
        if type(value) is dict:
            for key, child in value.items():
                if key == "$ref":
                    yield child
                yield from references(child)
        elif type(value) is list:
            for child in value:
                yield from references(child)
    for path in NESTED.glob("*.schema.json"):
        doc = json.loads(path.read_text())
        resolver = registry().resolver(doc["$id"])
        for reference in references(doc):
            assert resolver.lookup(reference).contents is not None


def test_every_live_stage_reuse_and_rollback_have_closed_wire_shapes():
    machine = NestedMachine(load_nested_profile())
    machine.start(graph())
    checked, kinds, stages = set(), set(), set()
    while machine.state.halt_status is TerminalStatus.RUNNING:
        kinds |= machine_shapes(machine, checked)
        stages.update(call.status for call in machine.state.native_calls)
        machine.advance()
    kinds |= machine_shapes(machine, checked)
    stages.update(call.status for call in machine.state.native_calls)
    assert {"NEW", "OPEN", "WAITING_DEPENDENCY", "BOUND", "WAITING_PROCEDURE", "READY", "COMPLETE"} <= stages
    reused = machine.run(create_problem((Equation("x", "-4", "7", "13"),), "x"), allow_acquisition=False)
    assert reused.output == "-3/2"
    kinds |= machine_shapes(machine, checked)
    machine.start(graph())
    machine.rollback()
    kinds |= machine_shapes(machine, checked)
    refused = machine.run(allow_acquisition=False)
    assert refused.output is None
    kinds |= machine_shapes(machine, checked)
    assert kinds == set(NESTED_RECORD_KINDS)


@pytest.mark.parametrize("packet,allow", [
    (create_problem((), "missing"), True),
    (create_problem((Equation("x", "1", "0", rhs_terms=(("x", "1"),)),), "x"), True),
    (create_problem((Equation("x", "0", "1", "1"),), "x"), True),
    (create_problem((Equation("x", "1", "0", "7"),), "x", budget=NativeBudget(20, 2)), True),
    (graph(), False),
    (create_problem((Equation("x", "1/" + str(2**127-1), "0", str(2**127-1)),
                     Equation("y", "1", "0", rhs_terms=(("x", "1"),))), "y"), True),
])
def test_actual_refusals_and_large_child_receipts_have_valid_shapes(packet, allow):
    machine = NestedMachine(load_nested_profile())
    result = machine.run(packet, allow_acquisition=allow)
    assert result.output is None
    machine_shapes(machine)


def test_actual_failed_qualification_and_return_shapes():
    machine = NestedMachine(load_nested_profile())
    machine.start(graph())
    for _ in range(16):
        intent = machine.coordinator.next_intent()
        if intent.intent_type is NestedIntentType.SELECT_PROCEDURE:
            break
        machine.advance()
    else:
        pytest.fail("acquisition did not reach candidate selection")
    mutation = {"call_id": intent.mutation_dict()["call_id"],
                "artifact": make_candidate(combine="ADD_EXACT").to_dict(), "qualification_digest": None}
    wrong = nested_intent(machine.coordinator, NestedIntentType.INSTALL_PROCEDURE, mutation)
    result = machine.coordinator.execute(enabled_components=(wrong.issuer_subsystem,),
        scheduled_components=(wrong.issuer_subsystem,), intents=(wrong,))
    assert result.rejected_intents
    machine_shapes(machine)
    machine.run()
    assert machine.result().output is None
    machine_shapes(machine)


@pytest.mark.parametrize("path,value", [(("schema_version",), "cncm.native-problem/0.2"),
    (("expected_answer",), "3"), (("plan_order",), ["x", "y"]),
    (("budget", "instructions_remaining"), True), (("budget", "instructions_remaining"), 512.0),
    (("equations", 0, "a"), 1), (("equations", 0, "a"), "01"),
    (("equations", 1, "rhs_terms"), [["x", "0"]]),
])
def test_problem_shape_rejects_plan_answer_version_and_raw_type_changes(path, value):
    wire = graph().to_dict()
    target = wire
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        validate("problem", wire)
    with pytest.raises(ContractError):
        NestedProblem.from_dict(wire)


def test_accepted_intent_matrix_is_closed_but_trace_retains_rejected_payload(completed):
    for event in completed.coordinator.trace.events:
        for proposal in event.proposed_intents:
            if type(proposal.intent_type) is not NestedIntentType or proposal.intent_id not in event.authorized_intent_ids:
                continue
            wire = proposal.to_dict()
            validate("accepted_intent", wire)
            for key, wrong in (("issuer_subsystem", "checker"), ("required_capability", "bypass"), ("target_scope", "outside")):
                with pytest.raises(ValidationError):
                    validate("accepted_intent", {**wire, key: wrong})
            wire["proposed_mutation"]["hidden_answer"] = "999"
            with pytest.raises(ValidationError):
                validate("accepted_intent", wire)
            validate("trace_intent", wire)


def test_record_body_annotation_requires_explicit_decoding(completed):
    record = deepcopy(completed.state.to_dict()["native_records"][0])
    body = json.loads(record["body_json"])
    body["trust_without_checking"] = True
    record["body_json"] = json.dumps(body, sort_keys=True, separators=(",", ":"))
    validate("record", record)
    with pytest.raises(ValidationError):
        validate("record_body_" + record["kind"], body)
    record["kind"] = "EXTERNAL_TOOL"
    with pytest.raises(ValidationError):
        validate("record", record)


def test_shape_success_cannot_replace_semantic_replay(completed):
    forged = deepcopy(completed.journal())
    forged["episodes"][0]["final_state"]["native_budget"]["instructions_remaining"] += 1
    validate("journal", forged)
    with pytest.raises(ContractError):
        recover_nested_journal(forged, trusted_genesis=completed.problem,
            expected_journal_digest=completed.journal()["journal_digest"], profile=completed.profile)
    with pytest.raises(ContractError):
        NestedState.from_dict(forged["episodes"][0]["final_state"])


def test_wrong_versions_and_unknowns_rejected_at_every_top_level(completed):
    values = {"problem": completed.problem.to_dict(), "state": completed.state.to_dict(),
              "evidence": completed.evidence, "journal": completed.journal(),
              "source_profile": completed.profile.to_dict()}
    for kind, original in values.items():
        validate(kind, original)
        with pytest.raises(ValidationError):
            validate(kind, {**original, "extra": True})
        with pytest.raises(ValidationError):
            validate(kind, {**original, "schema_version": "wrong/1"})
    state = completed.state.to_dict()
    state["native_calls"][0]["cached_answer"] = "3"
    with pytest.raises(ValidationError):
        validate("state", state)
    journal = completed.journal()
    journal["episodes"][0]["trusted_registry"] = {}
    with pytest.raises(ValidationError):
        validate("journal", journal)


def test_retained_state_and_proof_schemas_reject_new_runtime(completed):
    with pytest.raises(ValidationError):
        STRICT({'$ref':'https://cas.local/schemas/native_v0_2/state.schema.json'}, registry=registry()).validate(completed.state.to_dict())
    proof = next(row for branch in completed.state.branch_table for row in branch.proof_steps if type(row) is NestedProofStep)
    with pytest.raises(ValidationError):
        STRICT({'$ref':'https://cas.local/schemas/native_v0_2/proof.schema.json'}, registry=registry()).validate(proof.to_dict())
