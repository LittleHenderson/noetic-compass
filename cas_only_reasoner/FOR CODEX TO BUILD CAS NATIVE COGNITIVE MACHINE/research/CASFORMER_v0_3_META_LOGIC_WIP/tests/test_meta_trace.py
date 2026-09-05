"""Pure record tests: no native runtime execution or neural training."""

from copy import deepcopy
from hashlib import sha256
import json

from jsonschema import Draft202012Validator
import pytest

from cas_meta.trace import META_EVENT_SCHEMA_PATH, MetaTraceError, validate_meta_events


HASH = "a" * 64
RUN_ID = "c" * 32
ROOT = f"sample:call:{RUN_ID}:1"
CHILD = f"sample:call:{RUN_ID}:2"


def seal(events):
    previous = None
    for index, event in enumerate(events):
        event.update(schema="cas-meta-event/0.1", seq=index, chain_id="sample",
                     program_digest=HASH, previous=previous)
        wire = {key: value for key, value in event.items() if key != "digest"}
        event["digest"] = sha256(json.dumps(
            wire, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        previous = event["digest"]
    return events


def samples():
    head = {"state_digest": HASH, "state_version": 1, "trace_digest": HASH,
            "model_digest": HASH, "commit_receipt_id": "receipt-1"}
    return seal([
        {"kind": "ENTER", "call_id": ROOT, "parent_id": None, "procedure": "main",
         "path": "entry", "return_pc": None, "allowance": 20},
        {"kind": "ENTER", "call_id": CHILD, "parent_id": ROOT, "procedure": "worker",
         "path": "procedures.main.body.steps[0]", "return_pc": 0, "allowance": 10},
        {"kind": "SUSPEND", "call_id": ROOT, "child_id": CHILD, "pc": 0},
        {"kind": "CHARGE", "call_id": CHILD, "units": 5, "plan_digest": HASH,
         "components": {"route_quanta": 1, "reasoning_step_quanta": 1, "branch_quanta": 1,
                        "memory_read_quanta": 1, "diagnostic_probe_quanta": 1}},
        {"kind": "NATIVE", "call_id": CHILD, "path": "procedures.worker.body",
         "cjt_id": "A", "tick": 1, "accepted": True, "receipt_id": "receipt-1",
         "trace_id": "trace-1", "effect_ids": ["effect-1"], "repair_id": None,
         "repair_outcome_id": None, "head": head},
        {"kind": "RETURN", "call_id": CHILD, "parent_id": ROOT, "return_pc": 0,
         "effect_id": "effect-1", "spent": 5},
        {"kind": "RESUME", "call_id": ROOT, "child_id": CHILD, "pc": 1},
        {"kind": "RETURN", "call_id": ROOT, "parent_id": None, "return_pc": None,
         "effect_id": "effect-1", "spent": 5},
    ])


def reject(events, code):
    with pytest.raises(MetaTraceError) as caught:
        validate_meta_events(events)
    assert caught.value.code == code
    assert str(caught.value) == code


def test_published_schema_is_valid_2020_12_and_accepts_all_event_kinds():
    schema = json.loads(META_EVENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    for event in samples():
        Draft202012Validator(schema).validate(event)
    assert validate_meta_events(samples()) is None


def test_empty_chain_is_not_an_execution_claim():
    assert validate_meta_events([]) is None


def test_validator_leaves_input_unchanged():
    events = samples()
    before = deepcopy(events)
    validate_meta_events(events)
    assert events == before


def test_optional_suspend_repair_id():
    events = samples()
    events[2]["repair_id"] = "repair-1"
    validate_meta_events(seal(events))


def test_call_id_without_run_identity_is_rejected():
    events = samples()
    events[0]["call_id"] = "sample:call:1"
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


def test_rejected_native_record_with_repair_metadata():
    events = samples()
    events[4].update(accepted=False, effect_ids=[], repair_id="repair-1")
    validate_meta_events(seal(events))


@pytest.mark.parametrize("index", range(8))
def test_unknown_property_is_rejected_for_every_kind(index):
    events = samples()
    events[index]["unexpected"] = "not ignored"
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


@pytest.mark.parametrize("index,field", [
    (0, "allowance"), (0, "parent_id"), (0, "path"), (0, "procedure"), (0, "return_pc"),
    (2, "pc"), (2, "child_id"), (3, "units"), (3, "components"), (3, "plan_digest"),
    (4, "head"), (4, "receipt_id"), (4, "effect_ids"), (4, "repair_id"),
    (4, "repair_outcome_id"), (4, "trace_id"), (4, "accepted"), (4, "tick"),
    (4, "cjt_id"), (5, "effect_id"), (5, "spent"), (6, "child_id"), (6, "pc"),
])
def test_missing_specific_fields_fail(index, field):
    events = samples()
    del events[index][field]
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


@pytest.mark.parametrize("field", ["schema", "seq", "chain_id", "program_digest", "kind", "previous", "digest", "call_id"])
def test_missing_common_fields_fail(field):
    events = samples()
    del events[0][field]
    reject(events, "META_TRACE_SCHEMA_INVALID")


@pytest.mark.parametrize("index,field,value", [
    (0, "allowance", -1), (0, "allowance", True), (0, "allowance", 1.0),
    (0, "parent_id", 7), (0, "return_pc", False), (0, "procedure", "bad/name"),
    (0, "path", ""), (0, "call_id", "not-a-call-id"),
    (2, "pc", -1), (2, "repair_id", None), (2, "child_id", ROOT + ":other"),
    (3, "units", True), (3, "units", -1), (3, "plan_digest", "bad"),
    (4, "accepted", "true"), (4, "accepted", 1), (4, "tick", 0),
    (4, "effect_ids", "effect-1"), (4, "effect_ids", ["e1", "e2"]),
    (4, "repair_id", []), (4, "receipt_id", ""), (4, "head", None),
    (5, "spent", -1), (5, "return_pc", 0.0), (6, "pc", "1"),
])
def test_wrong_type_or_value_fails(index, field, value):
    events = samples()
    events[index][field] = value
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


@pytest.mark.parametrize("index,field,value", [
    (0, "effect_id", "e1"), (2, "allowance", 10), (3, "pc", 1),
    (4, "procedure", "worker"), (5, "repair_id", "r1"), (6, "repair_id", "r1"),
])
def test_fields_from_other_kinds_cannot_leak_in(index, field, value):
    events = samples()
    events[index][field] = value
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


@pytest.mark.parametrize("component", [
    "route_quanta", "reasoning_step_quanta", "branch_quanta",
    "memory_read_quanta", "diagnostic_probe_quanta",
])
def test_all_five_charge_components_are_required(component):
    events = samples()
    del events[3]["components"][component]
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


@pytest.mark.parametrize("value", [-1, True, 1.0, None, "1"])
def test_charge_components_are_nonnegative_integer_values(value):
    events = samples()
    events[3]["components"]["route_quanta"] = value
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


def test_charge_components_have_no_extra_keys():
    events = samples()
    events[3]["components"]["free_compute"] = 100
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


def test_charge_total_must_equal_components_even_after_valid_rehash():
    events = samples()
    events[3]["units"] = 0
    reject(seal(events), "META_TRACE_CHARGE_MISMATCH")


@pytest.mark.parametrize("field", ["state_digest", "state_version", "trace_digest", "model_digest", "commit_receipt_id"])
def test_native_head_exact_fields_required(field):
    events = samples()
    del events[4]["head"][field]
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


@pytest.mark.parametrize("field,value", [
    ("state_digest", "bad"), ("state_version", True), ("state_version", -1),
    ("trace_digest", 1), ("model_digest", "bad"), ("commit_receipt_id", []),
    ("extra", "not ignored"),
])
def test_native_head_values_and_unknown_fields(field, value):
    events = samples()
    events[4]["head"][field] = value
    reject(seal(events), "META_TRACE_SCHEMA_INVALID")


@pytest.mark.parametrize("mutation", ["bad_digest", "bad_previous", "bad_sequence", "other_chain", "other_program", "other_call_chain"])
def test_hash_sequence_and_identity_checks(mutation):
    events = samples()
    if mutation == "bad_digest":
        events[3]["digest"] = "b" * 64
    elif mutation == "bad_previous":
        events[3]["previous"] = "b" * 64
    elif mutation == "bad_sequence":
        events[3]["seq"] = 30
    elif mutation == "other_chain":
        events[3]["chain_id"] = "other"
    elif mutation == "other_program":
        events[3]["program_digest"] = "b" * 64
    else:
        events[3]["call_id"] = f"other:call:{RUN_ID}:2"
        seal(events)
    reject(events, "META_TRACE_CHAIN_INVALID")


def test_tamper_without_rehash_is_rejected():
    events = samples()
    events[4]["accepted"] = False
    reject(events, "META_TRACE_CHAIN_INVALID")


def test_nonzero_first_sequence_or_previous_rejected():
    events = samples()
    events[0]["previous"] = HASH
    reject(events, "META_TRACE_CHAIN_INVALID")
    events = samples()
    events[0]["seq"] = 1
    reject(events, "META_TRACE_CHAIN_INVALID")


@pytest.mark.parametrize("value", [None, {}, "events", 1, [None], [True]])
def test_invalid_container_or_event(value):
    reject(value, "META_TRACE_SCHEMA_INVALID")


def test_boolean_and_float_sequence_numbers_rejected():
    for value in (False, 0.0):
        events = samples()
        events[0]["seq"] = value
        reject(events, "META_TRACE_SCHEMA_INVALID")
