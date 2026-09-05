"""Compiler admission tests; these do not execute or train neural weights."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path

import pytest

from cas_meta.compiler import (
    MAX_ALLOWANCE, MAX_AST_DEPTH, MAX_PROCEDURES, MAX_SOURCE_BYTES,
    MAX_STEPS_PER_PROCEDURE, MetaCompileError, compile_program,
)


def run(cjt="A", **extra):
    return {"kind": "run", "cjt": cjt, "operation": "^6", "expected": "L1", **extra}


def procedure(body=None, input_type="IDEA", allowed=None):
    return {
        "input_type": input_type, "output_type": "EFFECT",
        "allowed_cjts": ["A"] if allowed is None else allowed,
        "body": run() if body is None else body,
    }


def source(body=None):
    return {"version": "cas-meta/0.1", "entry": "main", "procedures": {"main": procedure(body)}}


def reject(value, code):
    with pytest.raises(MetaCompileError) as caught:
        compile_program(value)
    assert caught.value.code == code
    assert str(caught.value) == code


def test_minimal_program_is_immutable_and_detached():
    original = source()
    compiled = compile_program(original)
    original["procedures"]["main"]["allowed_cjts"].append("B")
    assert compiled.by_name["main"].allowed_cjts == ("A",)
    index = compiled.by_name
    index.clear()
    assert "main" in compiled.by_name
    with pytest.raises(FrozenInstanceError):
        compiled.entry = "other"
    with pytest.raises(FrozenInstanceError):
        compiled.by_name["main"].steps[0].operation = "^2"


def test_source_identity_is_canonical_and_round_trips():
    original = source()
    reversed_keys = dict(reversed(list(original.items())))
    compiled = compile_program(original)
    assert compiled == compile_program(json.dumps(reversed_keys, indent=4))
    assert compiled == compile_program(compiled.source_json)
    assert compiled.digest == hashlib.sha256(compiled.source_json.encode()).hexdigest()


def test_changes_to_source_change_identity():
    left = source()
    right = deepcopy(left)
    right["procedures"]["main"]["body"]["expected"] = "L2"
    assert compile_program(left).digest != compile_program(right).digest


def test_nested_sequences_flatten_but_calls_do_not():
    value = source({"kind": "sequence", "steps": [
        run(), {"kind": "sequence", "steps": [{"kind": "call", "procedure": "child", "allowance": 8}]},
    ]})
    value["procedures"]["child"] = procedure(input_type="EFFECT")
    compiled = compile_program(value)
    steps = compiled.by_name["main"].steps
    assert tuple(step.kind for step in steps) == ("run", "call")
    assert steps[1].procedure == "child"
    assert steps[1].allowance == 8
    assert steps[1].path == "procedures.main.body.steps[1].steps[0]"


def test_fixed_chain_fixture_compiles_with_real_child_calls():
    path = Path(__file__).resolve().parents[1] / "programs" / "fixed_chain.json"
    compiled = compile_program(path.read_text(encoding="utf-8"))
    assert set(compiled.by_name) == {"main", "worker", "repair_c"}
    assert compiled.by_name["main"].steps[1].kind == "call"
    assert compiled.by_name["worker"].steps[1].repair == "repair_c"
    assert compiled.by_name["repair_c"].input_type == "RPM_SUBGOAL"


@pytest.mark.parametrize("value", [None, [], 1, True, b"{}"])
def test_source_type_rejections(value):
    reject(value, "INVALID_SOURCE_TYPE")


@pytest.mark.parametrize("value", ["{", "", "not json", '{"version":'])
def test_invalid_json(value):
    reject(value, "INVALID_JSON")


def test_excessive_integer_parser_input_has_typed_error():
    reject('{"value":' + "1" * 10000 + "}", "INVALID_JSON")


@pytest.mark.parametrize("value", ['[]', 'null', '"text"'])
def test_json_root_must_be_object(value):
    reject(value, "INVALID_PROGRAM")


def test_duplicate_keys_rejected_at_every_depth():
    reject('{"entry":"main","entry":"other"}', "DUPLICATE_JSON_KEY")
    reject('{"nested":{"operation":"^6","operation":"^2"}}', "DUPLICATE_JSON_KEY")


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_nonfinite_json_rejected(token):
    reject('{"value":' + token + '}', "NONFINITE_NUMBER")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_dict_rejected(value):
    reject({"value": value}, "NONFINITE_NUMBER")


def test_cyclic_input_and_non_json_objects_rejected():
    value = source()
    value["self"] = value
    reject(value, "CYCLIC_SOURCE")
    reject({"value": object()}, "NON_JSON_VALUE")
    reject({1: "value"}, "NON_STRING_JSON_KEY")


def test_shared_acyclic_objects_are_allowed():
    value = source()
    value["procedures"]["other"] = value["procedures"]["main"]
    assert len(compile_program(value).procedures) == 2


@pytest.mark.parametrize("extra", ["foundation", "noetic_alias", "permissions", "weights"])
def test_no_unrecognized_program_authority_fields(extra):
    value = source()
    value[extra] = "new authority"
    reject(value, "UNKNOWN_FIELD")


@pytest.mark.parametrize("kind", ["within", "compose", "Within", "Compose", "learn", "noetic"])
def test_unsupported_language_is_rejected(kind):
    reject(source({"kind": kind}), "UNSUPPORTED_KIND")


@pytest.mark.parametrize("operation", ["^0", "^2", "^3", "^8", "6", 6, True, None, "^6 "])
def test_only_exact_admitted_operation(operation):
    reject(source(run(operation=operation)), "OPERATION_NOT_ADMITTED")


@pytest.mark.parametrize("allowance", [0, -1, True, False, 1.0, "8", None, MAX_ALLOWANCE + 1])
def test_allowance_is_bounded_positive_integer(allowance):
    value = source({"kind": "call", "procedure": "child", "allowance": allowance})
    value["procedures"]["child"] = procedure()
    reject(value, "INVALID_ALLOWANCE")


@pytest.mark.parametrize("allowance", [1, MAX_ALLOWANCE])
def test_allowance_endpoints(allowance):
    value = source({"kind": "call", "procedure": "child", "allowance": allowance})
    value["procedures"]["child"] = procedure()
    assert compile_program(value).by_name["main"].steps[0].allowance == allowance


@pytest.mark.parametrize("name", ["", " bad", "bad/name", "a" * 65, "^6", "1main"])
def test_invalid_names(name):
    value = source()
    value["entry"] = name
    reject(value, "INVALID_NAME")


@pytest.mark.parametrize("expected", [None, True, 1, "", " L1", "L1\n", "x" * 257])
def test_invalid_expected_symbols(expected):
    reject(source(run(expected=expected)), "INVALID_SYMBOL")


def test_missing_extra_and_wrong_fields_fail_closed():
    value = source()
    del value["version"]
    reject(value, "MISSING_FIELD")
    reject(source(run(extra="ignored?")), "UNKNOWN_FIELD")
    reject(source({"kind": None}), "INVALID_KIND")
    reject(source({"kind": "sequence", "steps": {}}), "EXPECTED_STEP_LIST")
    reject(source({"kind": "sequence", "steps": []}), "EMPTY_SEQUENCE")
    reject(source([]), "EXPECTED_OBJECT")


def test_version_and_entry_rejected():
    value = source()
    value["version"] = "cas-meta/0.2"
    reject(value, "UNSUPPORTED_VERSION")
    value = source()
    value["entry"] = "missing"
    reject(value, "UNKNOWN_ENTRY")


@pytest.mark.parametrize("input_type", [None, True, "RPM", "effect", [], "ANY"])
def test_invalid_input_types(input_type):
    value = source()
    value["procedures"]["main"]["input_type"] = input_type
    reject(value, "INVALID_INPUT_TYPE")


@pytest.mark.parametrize("output_type", [None, "IDEA", "RPM_SUBGOAL", "ANY", []])
def test_output_is_effect_only(output_type):
    value = source()
    value["procedures"]["main"]["output_type"] = output_type
    reject(value, "INVALID_OUTPUT_TYPE")


@pytest.mark.parametrize("scope", [None, [], "A", ["A"] * (MAX_PROCEDURES + 1)])
def test_scope_shape_and_size(scope):
    value = source()
    value["procedures"]["main"]["allowed_cjts"] = scope
    reject(value, "INVALID_CJT_SCOPE")


def test_duplicate_scope_and_outside_cjt_rejected():
    value = source()
    value["procedures"]["main"]["allowed_cjts"] = ["A", "A"]
    reject(value, "DUPLICATE_CJT_SCOPE")
    reject(source(run("B")), "CJT_SCOPE_VIOLATION")


@pytest.mark.parametrize("repair", [False, True])
def test_child_scope_cannot_expand(repair):
    value = source(run(repair="child", resume_expected="L1") if repair else
                   {"kind": "call", "procedure": "child", "allowance": 1})
    value["procedures"]["child"] = procedure(
        input_type="RPM_SUBGOAL" if repair else "IDEA", allowed=["A", "B"]
    )
    reject(value, "CHILD_SCOPE_ESCALATION")


@pytest.mark.parametrize("repair", [False, True])
def test_unknown_child_rejected(repair):
    value = source(run(repair="child", resume_expected="L1") if repair else
                   {"kind": "call", "procedure": "child", "allowance": 1})
    reject(value, "UNKNOWN_PROCEDURE")


@pytest.mark.parametrize("repair", [False, True])
def test_child_input_type_checked(repair):
    value = source(run(repair="child", resume_expected="L1") if repair else
                   {"kind": "call", "procedure": "child", "allowance": 1})
    value["procedures"]["child"] = procedure(input_type="EFFECT")
    reject(value, "TYPE_MISMATCH")


def test_type_state_advances_in_sequence():
    value = source({"kind": "sequence", "steps": [run(), {"kind": "call", "procedure": "child", "allowance": 1}]})
    value["procedures"]["child"] = procedure(input_type="IDEA")
    reject(value, "TYPE_MISMATCH")


@pytest.mark.parametrize("extra", [{"repair": "child"}, {"resume_expected": "L1"}])
def test_repair_and_resume_are_a_pair(extra):
    reject(source(run(**extra)), "REPAIR_RESUME_PAIR_REQUIRED")


def test_repair_input_is_subgoal_and_run_retains_resume_metadata():
    value = source(run(opposite="L2", repair="child", resume_expected="L2"))
    value["procedures"]["child"] = procedure(input_type="RPM_SUBGOAL")
    step = compile_program(value).by_name["main"].steps[0]
    assert (step.opposite, step.repair, step.resume_expected) == ("L2", "child", "L2")


def test_direct_call_cycle():
    value = source({"kind": "call", "procedure": "main", "allowance": 1})
    reject(value, "CALL_CYCLE")


def test_indirect_and_unreachable_call_cycles():
    value = source()
    value["procedures"]["x"] = procedure({"kind": "call", "procedure": "y", "allowance": 1})
    value["procedures"]["y"] = procedure({"kind": "call", "procedure": "x", "allowance": 1})
    reject(value, "CALL_CYCLE")


def test_repair_edges_also_count_as_cycles():
    value = source()
    value["procedures"]["main"]["input_type"] = "RPM_SUBGOAL"
    value["procedures"]["main"]["body"] = run(repair="main", resume_expected="L1")
    reject(value, "CALL_CYCLE")


def test_unreachable_experimental_procedure_is_not_laundered():
    value = source()
    value["procedures"]["unused"] = procedure(run(operation="^2"))
    reject(value, "OPERATION_NOT_ADMITTED")


def test_source_size_bound_and_invalid_unicode():
    reject(" " * (MAX_SOURCE_BYTES + 1), "SOURCE_SIZE_LIMIT")
    reject({"key": "x" * (MAX_SOURCE_BYTES + 1)}, "SOURCE_SIZE_LIMIT")
    reject({"key": "\ud800"}, "INVALID_UNICODE")


def test_procedure_limit():
    value = source()
    value["procedures"] = {}
    reject(value, "PROCEDURE_LIMIT")
    value["procedures"] = {f"p{i}": procedure() for i in range(MAX_PROCEDURES + 1)}
    reject(value, "PROCEDURE_LIMIT")


def test_step_limit_includes_nested_sequences():
    reject(source({"kind": "sequence", "steps": [run()] * (MAX_STEPS_PER_PROCEDURE + 1)}), "STEP_LIMIT")
    half = {"kind": "sequence", "steps": [run()] * (MAX_STEPS_PER_PROCEDURE // 2)}
    reject(source({"kind": "sequence", "steps": [half, half, run()]}), "STEP_LIMIT")


def test_ast_depth_limit():
    body = run()
    for _ in range(MAX_AST_DEPTH - 1):
        body = {"kind": "sequence", "steps": [body]}
    assert compile_program(source(body)).by_name["main"].steps[0].kind == "run"
    body = {"kind": "sequence", "steps": [body]}
    reject(source(body), "AST_DEPTH_LIMIT")


def test_ast_node_limit_across_procedures():
    value = source()
    body = {"kind": "sequence", "steps": [run()] * MAX_STEPS_PER_PROCEDURE}
    value["procedures"] = {f"p{i}": procedure(body) for i in range(5)}
    value["entry"] = "p0"
    reject(value, "AST_NODE_LIMIT")
