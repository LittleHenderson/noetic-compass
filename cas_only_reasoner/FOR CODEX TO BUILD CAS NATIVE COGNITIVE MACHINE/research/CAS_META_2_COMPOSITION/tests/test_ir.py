from copy import deepcopy
import hashlib
import json

import pytest

from cas_meta2.ir import IRValidationError, Limits, SCHEMA, canonical_program, expand_program, validate_program


pytestmark = pytest.mark.not_gpu


def sample():
    return {"schema": SCHEMA, "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A", "B"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v2"}], "return": "v1"},
        "p0": {"input": "arg", "allowed_cjts": ["B"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}


def test_stats_count_repeated_calls_as_real_work():
    stats = validate_program(sample())
    assert stats == {"procedure_count": 2, "instruction_count": 4,
                     "expanded_instruction_count": 5, "expanded_run_count": 3,
                     "max_call_depth": 2, "program_sha256": hashlib.sha256(canonical_program(sample())).hexdigest()}


def test_expansion_preserves_named_earlier_value_and_return():
    events = expand_program(sample())
    entries = [e for e in events if e["kind"] == "ENTER"]
    assert len(entries) == 3
    assert entries[1]["input_ref"] == entries[2]["input_ref"] == "entry:main/values/v0"
    assert entries[1]["frame_address"] != entries[2]["frame_address"]
    assert events[-1]["input_ref"] == "entry:main/values/v1"
    assert events[-1]["output_ref"] == "$result"
    assert len({e["address"] for e in events}) == len(events)


def test_canonical_bytes_and_input_immutability():
    program, before = sample(), sample()
    payload = canonical_program(program)
    assert validate_program(payload) == validate_program(program)
    assert validate_program(json.dumps(program, indent=4)) == validate_program(program)
    expand_program(program)
    assert program == before
    assert payload == canonical_program(json.loads(payload))


@pytest.mark.parametrize("path,value,code", [
    (("schema",), "cas-meta/0.1", "UNSUPPORTED_SCHEMA"),
    (("entry",), "missing", "UNKNOWN_ENTRY"),
    (("entry",), "../main", "INVALID_NAME"),
    (("procedures", "main", "return"), "missing", "UNDECLARED_RETURN"),
    (("procedures", "main", "steps", 0, "input"), "v1", "UNDECLARED_VALUE"),
    (("procedures", "main", "steps", 0, "output"), "arg", "DUPLICATE_VALUE"),
    (("procedures", "main", "steps", 1, "output"), "v0", "DUPLICATE_VALUE"),
    (("procedures", "main", "steps", 1, "procedure"), "missing", "UNKNOWN_PROCEDURE"),
    (("procedures", "main", "steps", 0, "kind"), "LEARN", "UNSUPPORTED_STEP"),
    (("procedures", "main", "steps", 0, "cjt_id"), "R", "CJT_SCOPE_DENIED"),
    (("procedures", "main", "allowed_cjts"), ["A", "A"], "DUPLICATE_CJT_SCOPE"),
    (("procedures", "main", "allowed_cjts"), ["A", "B", "X"], "INVALID_CJT_SCOPE"),
    (("procedures", "main", "steps"), [], "EMPTY_OR_INVALID_STEPS"),
])
def test_bad_program_rejected(path, value, code):
    program = sample()
    node = program
    for part in path[:-1]:
        node = node[part]
    node[path[-1]] = value
    with pytest.raises(IRValidationError, match=code):
        validate_program(program)


@pytest.mark.parametrize("location", [(), ("procedures", "main"), ("procedures", "main", "steps", 0)])
def test_unknown_fields_cannot_carry_authority(location):
    program = sample()
    node = program
    for part in location:
        node = node[part]
    node["grant_permission"] = "everything"
    with pytest.raises(IRValidationError, match="UNEXPECTED_FIELDS"):
        validate_program(program)


def test_child_scope_escalation_rejected():
    program = sample()
    program["procedures"]["p0"]["allowed_cjts"] = ["B", "R"]
    with pytest.raises(IRValidationError, match="CHILD_SCOPE_ESCALATION"):
        validate_program(program)


def test_cycles_rejected_before_expansion():
    program = sample()
    program["procedures"]["p0"]["steps"] = [{"kind": "CALL", "procedure": "p0", "input": "arg", "output": "v0"}]
    with pytest.raises(IRValidationError, match="CALL_CYCLE"):
        expand_program(program)


def test_unreachable_declaration_is_not_silently_ignored():
    program = sample()
    program["procedures"]["unused"] = deepcopy(program["procedures"]["p0"])
    with pytest.raises(IRValidationError, match="UNREACHABLE_PROCEDURE"):
        validate_program(program)


@pytest.mark.parametrize("limits,code", [
    (Limits(max_source_bytes=20), "SOURCE_SIZE_LIMIT"),
    (Limits(max_procedures=1), "PROCEDURE_LIMIT"),
    (Limits(max_instructions=3), "INSTRUCTION_LIMIT"),
    (Limits(max_expanded_instructions=4), "EXPANDED_INSTRUCTION_LIMIT"),
    (Limits(max_expanded_runs=2), "EXPANDED_RUN_LIMIT"),
    (Limits(max_call_depth=1), "CALL_DEPTH_LIMIT"),
])
def test_separate_admission_limits(limits, code):
    with pytest.raises(IRValidationError, match=code):
        validate_program(sample(), limits)


@pytest.mark.parametrize("value", [0, -1, True, 1.5, 100000000])
def test_invalid_limits(value):
    with pytest.raises(IRValidationError, match="INVALID_LIMIT"):
        Limits(max_call_depth=value)


def test_duplicate_json_keys_rejected():
    payload = canonical_program(sample()).decode().replace('"entry":"main"', '"entry":"main","entry":"main"')
    with pytest.raises(IRValidationError, match="DUPLICATE_JSON_KEY"):
        validate_program(payload)


def test_python_cycles_and_non_json_data_rejected():
    program = sample()
    program["loop"] = program
    with pytest.raises(IRValidationError, match="CYCLIC_SOURCE"):
        validate_program(program)
    program = sample()
    program["procedures"]["main"]["allowed_cjts"] = ("A", "B")
    with pytest.raises(IRValidationError, match="NON_STRING_SCALAR"):
        validate_program(program)


def test_structural_addresses_are_not_runtime_identity_claims():
    events = expand_program(sample())
    assert events == expand_program(sample())
    assert all("call_id" not in event and "accepted" not in event for event in events)
