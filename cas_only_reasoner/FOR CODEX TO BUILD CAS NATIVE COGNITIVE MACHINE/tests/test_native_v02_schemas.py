"""Closed wire shapes plus explicit decoded-record checks, never proof authority."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validators
from referencing import Registry, Resource

from cncm.canonical import digest
from cncm.model import ContractError
from cncm.native_engine import NativeMachine
from cncm.native_kernel import native_intent
from cncm.native_model import CAPABILITY, CallSpec, NativeIntentType, NativeProblem, NativeProofStep, NativeState
from cncm.native_profile import NATIVE_AUTHORITIES, NATIVE_WORK_COSTS, SOURCE_FILES
from cncm.native_recovery import replay_native_journal
from cncm.procedural_substrate import make_candidate
from tests.test_native_kernel import native_problem, simulated_profile

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
NATIVE = SCHEMAS / "native_v0_2"
BASE = "https://cas.local/schemas/native_v0_2/contracts.schema.json"
STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
    "integer", lambda checker, value: type(value) is int))


def registry():
    docs = [json.loads(path.read_text()) for path in [*SCHEMAS.glob("*.schema.json"), *NATIVE.glob("*.schema.json")]]
    return Registry().with_resources((doc["$id"], Resource.from_contents(doc)) for doc in docs)


def validate(kind, document):
    STRICT({"$ref": BASE + "#/$defs/" + kind}, registry=registry()).validate(document)


def validate_bodies(state):
    for record in state["native_records"]:
        # JSON Schema contentSchema alone is not an assertion. Never skip this
        # decoding layer when checking accepted native-state wire data.
        validate("record_body_" + record["kind"], json.loads(record["body_json"]))


@pytest.fixture(scope="module")
def run():
    machine = NativeMachine(profile=simulated_profile())
    result = machine.run(native_problem())
    return machine, result


def test_schema_documents_are_valid_and_default_manifest_is_unchanged():
    for path in NATIVE.glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    manifest = json.loads((ROOT / "authority/native_procedures_v0.2/manifest.json").read_text())
    import hashlib
    assert manifest["opt_in"] is True
    assert manifest["acceptance_status"] == "EVIDENCE_REQUIRED_PER_SOURCE_PROFILE"
    assert manifest["live_runtime_gates"]["invokes_json_schema_validator"] is False
    assert manifest["engineering_wire_validation_recipe"]
    assert "validation_layers" not in manifest
    assert manifest["preserved_default_manifest"]["sha256"] == hashlib.sha256((ROOT / "AUTHORITY_MANIFEST.yaml").read_bytes()).hexdigest()
    assert manifest["default_runtime_unchanged"] == "0.1.0"
    assert {key: (row["issuer"], row["capability"]) for key, row in manifest["issuer_matrix"].items()} == NATIVE_AUTHORITIES
    assert {key: (row["instructions"], row["checker_calls"]) for key, row in manifest["work_allocations"].items()} == NATIVE_WORK_COSTS
    expected = {path.relative_to(ROOT).as_posix() for path in NATIVE.glob("*.schema.json")}
    expected.add("authority/native_procedures_v0.2/manifest.json")
    assert expected <= set(SOURCE_FILES)


def test_every_versioned_schema_reference_resolves_offline():
    def references(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "$ref":
                    yield child
                yield from references(child)
        elif isinstance(value, list):
            for child in value:
                yield from references(child)
    resources = registry()
    for path in NATIVE.glob("*.schema.json"):
        document = json.loads(path.read_text())
        resolver = resources.resolver(document["$id"])
        for reference in references(document):
            assert resolver.lookup(reference).contents is not None


def test_real_bounded_execution_matches_all_new_shapes(run):
    machine, result = run
    validate("problem", machine.problem.to_dict())
    validate("source_profile", machine.profile.to_dict())
    validate("state", result.final_state.to_dict())
    validate_bodies(result.final_state.to_dict())
    validate("evidence", result.evidence)
    journal = machine.journal()
    validate("journal", journal)
    assert len(journal["episodes"][0]["proposal_batches"]) == len(result.trace)
    for event in result.trace:
        validate("trace", event.to_dict())
        for intent in event.proposed_intents:
            if intent.intent_type.value in NATIVE_AUTHORITIES and intent.intent_id in event.authorized_intent_ids:
                validate("accepted_intent", intent.to_dict())
    proofs = [p for b in result.final_state.branch_table for p in b.proof_steps if type(p) is NativeProofStep]
    assert proofs
    for proof in proofs:
        validate("proof", proof.to_dict())


@pytest.mark.parametrize("path,value", [(("training",), True), (("budget", "instructions_remaining"), True),
    (("budget", "instructions_remaining"), 512.0), (("budget", "checker_calls_remaining"), 100001),
    (("call", "inputs", "expected_x"), "7"), (("call", "inputs", "a"), 3),
    (("call", "inputs", "a"), "01"), (("call", "inputs", "a"), "1/-2"),
    (("call", "output_contract"), "arbitrary-code"), (("schema_version",), "cncm.native-problem/9")])
def test_problem_rejects_unknowns_raw_type_changes_and_unbounded_values(path, value):
    wire = native_problem().to_dict()
    target = wire
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        validate("problem", wire)
    with pytest.raises(ContractError):
        NativeProblem.from_dict(wire)


def test_accepted_native_intent_is_closed_but_rejection_trace_can_retain_it(run):
    machine, result = run
    intent = next(intent.to_dict() for event in result.trace for intent in event.proposed_intents
                  if intent.intent_type.value == "INSTALL_PROCEDURE")
    validate("accepted_intent", intent)
    for key, value in (("issuer_subsystem", "math_checker"), ("required_capability", "arbitrary_code")):
        forged = deepcopy(intent); forged[key] = value
        with pytest.raises(ValidationError):
            validate("accepted_intent", forged)
    intent["proposed_mutation"]["trusted"] = True
    with pytest.raises(ValidationError):
        validate("accepted_intent", intent)
    validate("trace_intent", intent)


def test_json_shape_is_not_semantic_replay_or_digest_authority(run):
    machine, result = run
    fake = deepcopy(machine.journal())
    fake["episodes"][0]["final_state"]["native_budget"]["instructions_remaining"] += 1
    # Same shape, false content: integrity/replay is a separate mandatory gate.
    validate("journal", fake)
    with pytest.raises(ContractError):
        replay_native_journal(fake, trusted_genesis=machine.problem,
            expected_journal_digest=machine.journal()["journal_digest"], profile=machine.profile)


def test_opaque_record_body_requires_explicit_closed_body_validation(run):
    record = deepcopy(run[1].final_state.to_dict()["native_records"][0])
    body = json.loads(record["body_json"])
    body["install_without_checking"] = True
    record["body_json"] = json.dumps(body, separators=(",", ":"), sort_keys=True)
    validate("record", record)  # Annotation-only contentSchema cannot grant acceptance.
    with pytest.raises(ValidationError):
        validate("record_body_" + record["kind"], body)
    record["kind"] = "EXTERNAL_TOOL"
    with pytest.raises(ValidationError):
        validate("record", record)


def test_old_default_schemas_reject_native_state_and_intents(run):
    old_state = json.loads((SCHEMAS / "machine_state.schema.json").read_text())
    with pytest.raises(ValidationError):
        STRICT(old_state, registry=registry()).validate(run[1].final_state.to_dict())
    old_intent = json.loads((SCHEMAS / "intent.schema.json").read_text())
    native = next(intent.to_dict() for event in run[1].trace for intent in event.proposed_intents
                  if intent.intent_type.value in NATIVE_AUTHORITIES)
    with pytest.raises(ValidationError):
        STRICT(old_intent, registry=registry()).validate(native)


def test_journal_and_state_boundaries_are_closed(run):
    machine, result = run
    journal = machine.journal()
    journal["episodes"][0]["trusted_registry"] = {}
    with pytest.raises(ValidationError):
        validate("journal", journal)
    state = result.final_state.to_dict()
    state["native_calls"][0]["hidden_answer"] = "7"
    with pytest.raises(ValidationError):
        validate("state", state)


@pytest.mark.parametrize("domain_failure", [False, True])
def test_failed_or_disabled_acquisition_has_accepted_evidence_shape(domain_failure):
    packet = native_problem()
    if domain_failure:
        packet = replace(packet, call=CallSpec.create(call_id=packet.call.call_id,
            goal_id=packet.call.goal_id, inputs={"a": "0", "b": "5", "c": "26"}))
    machine = NativeMachine(profile=simulated_profile())
    result = machine.run(packet, allow_acquisition=domain_failure)
    assert result.output is None
    validate("state", result.final_state.to_dict())
    validate_bodies(result.final_state.to_dict())
    validate("evidence", result.evidence)
    validate("journal", machine.journal())


def check_machine_shapes(machine):
    state = machine.state.to_dict()
    validate("state", state)
    validate_bodies(state)
    validate("journal", machine.journal())
    validate("evidence", machine.evidence)
    return {record["kind"] for record in state["native_records"]}


def test_each_native_stage_qualification_failure_return_reuse_and_rollback():
    kinds = set()
    machine = NativeMachine(profile=simulated_profile())
    machine.start(native_problem())
    # Request, suspend, finite selection, installation, exact return, application.
    for index in range(6):
        machine.advance()
        kinds |= check_machine_shapes(machine)
        if index == 1:
            validate("acquisition", machine.state.to_dict()["rpm_stack"][-1])
    machine.run()
    packet = native_problem()
    packet = replace(packet, call=CallSpec.create(call_id=packet.call.call_id,
        goal_id=packet.call.goal_id, inputs={"a": "-4", "b": "7", "c": "13"}))
    reused = machine.run(packet, allow_acquisition=False)
    assert reused.output == "-3/2"
    kinds |= check_machine_shapes(machine)
    machine.start(native_problem())
    machine.rollback(CAPABILITY)
    kinds |= check_machine_shapes(machine)
    refused = machine.run(allow_acquisition=False)
    assert refused.output is None
    kinds |= check_machine_shapes(machine)

    failed = NativeMachine(profile=simulated_profile())
    failed.start(native_problem())
    failed.advance(); failed.advance()
    intent = native_intent(failed.coordinator, NativeIntentType.INSTALL_PROCEDURE, {
        "call_id": failed.problem.call.call_id,
        "artifact": make_candidate(combine="ADD_EXACT").to_dict(), "qualification_digest": None})
    outcome = failed.coordinator.execute(enabled_components=(intent.issuer_subsystem,),
        scheduled_components=(intent.issuer_subsystem,), intents=(intent,))
    assert outcome.rejected_intents
    kinds |= check_machine_shapes(failed)
    failed.advance()  # Exact failure return and typed terminal refusal.
    kinds |= check_machine_shapes(failed)
    assert kinds == {"WORK_RESERVATION", "SELECTION", "QUALIFICATION", "INSTALLATION",
                     "EXECUTION", "FAILURE", "ROLLBACK"}
