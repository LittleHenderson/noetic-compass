"""Pure grammar, pinning and bounded primitive-composition regressions."""
from copy import deepcopy
from dataclasses import replace
from itertools import permutations

import pytest

from cncm.canonical import digest
from cncm.model import ContractError
from cncm.procedural_substrate import make_candidate, ProcedureLimits
from cncm.compound_program import (CallStep, CallProgram, CompoundContractError, INPUT_NAMES,
                                   enumerate_programs, execute_program, validate_inputs)


PRIMITIVE = make_candidate()
INPUTS = dict(a="2", b="3", c="5", d="7", e="35")


def correct_program(primitive=PRIMITIVE):
    return CallProgram(primitive.artifact_sha256, (CallStep("a", "d", "e"), CallStep("b", "c", "r0")))


def reseal(wire):
    wire["program_digest"] = digest({k: v for k, v in wire.items() if k != "program_digest"})
    return wire


def test_complete_closed_grammar_has_exactly_60_plus_360_distinct_shapes():
    programs = enumerate_programs(PRIMITIVE)
    assert len(programs) == len({row.program_digest for row in programs}) == 420
    assert all(len(row.steps) == 1 for row in programs[:60])
    assert all(len(row.steps) == 2 for row in programs[60:])
    assert tuple(row.steps[0].references for row in programs[:60]) == tuple(permutations(INPUT_NAMES, 3))
    for row in programs[60:]:
        assert set(row.steps[1].references) == (set(INPUT_NAMES) - set(row.steps[0].references)) | {"r0"}
    keys = [(len(row.steps), tuple(step.references for step in row.steps)) for row in programs]
    assert keys == sorted(keys)
    assert correct_program() in programs


def test_every_artifact_roundtrips_and_digest_alias_binds_primitive_and_steps():
    for program in enumerate_programs(PRIMITIVE):
        assert CallProgram.from_dict(program.to_dict()) == program
        assert program.artifact_sha256 == program.program_digest
    assert correct_program(replace(PRIMITIVE, revision=2)).program_digest != correct_program().program_digest


@pytest.mark.parametrize("refs", [("a", "a", "b"), ("x", "a", "b"), ("1", "a", "b"),
                                   (True, "a", "b"), ("a", "b", "__import__")])
def test_step_rejects_duplicates_literals_unknown_refs_and_coercion(refs):
    with pytest.raises(CompoundContractError):
        CallStep(*refs)


@pytest.mark.parametrize("steps", [(), (CallStep("r0", "a", "b"),),
    (CallStep("a", "b", "c"), CallStep("a", "d", "r0")),
    (CallStep("a", "b", "c"), CallStep("c", "d", "e")),
    (CallStep("a", "b", "c"),) * 3, [CallStep("a", "b", "c")]])
def test_program_refuses_any_graph_outside_the_closed_grammar(steps):
    with pytest.raises(CompoundContractError):
        CallProgram(PRIMITIVE.artifact_sha256, steps)


@pytest.mark.parametrize("change", ["extra", "missing", "wrong_schema", "wrong_digest", "extra_step_field",
                                    "literal", "duplicate", "forward_ref", "second_coverage"])
def test_forged_even_resealed_wire_fails_closed(change):
    wire = deepcopy(correct_program().to_dict())
    if change == "extra": wire["answer"] = "3"
    elif change == "missing": wire.pop("primitive_sha256")
    elif change == "wrong_schema": wire["schema_version"] = "legacy"
    elif change == "wrong_digest": wire["program_digest"] = "0" * 64
    elif change == "extra_step_field": wire["steps"][0]["answer"] = "3"
    elif change == "literal": wire["steps"][0]["a_ref"] = "2"
    elif change == "duplicate": wire["steps"][0]["a_ref"] = "d"
    elif change == "forward_ref": wire["steps"][0]["a_ref"] = "r0"
    else: wire["steps"][1]["a_ref"] = "e"
    if change != "wrong_digest": reseal(wire)
    with pytest.raises(CompoundContractError):
        CallProgram.from_dict(wire)


def test_program_executes_actual_pinned_primitive_twice_with_bound_intermediate():
    report = execute_program(correct_program(), PRIMITIVE, INPUTS)
    assert (report["status"], report["output"], report["instructions_executed"]) == ("SUCCESS", "3", 12)
    assert [row["inputs"] for row in report["subcalls"]] == [dict(a="2", b="7", c="35"), dict(a="3", b="5", c="14")]
    assert all(row["execution"]["artifact_sha256"] == PRIMITIVE.artifact_sha256 for row in report["subcalls"])
    assert report["report_digest"] == digest({k: v for k, v in report.items() if k != "report_digest"})


def test_single_call_is_substrate_success_without_a_correctness_claim():
    program = CallProgram(PRIMITIVE.artifact_sha256, (CallStep("a", "b", "c"),))
    report = execute_program(program, PRIMITIVE, INPUTS, instruction_budget=6)
    assert (report["status"], report["output"], report["instructions_executed"]) == ("SUCCESS", "1", 6)
    assert "CHECKED" not in report.values()


@pytest.mark.parametrize("budget", [0, 1, 6, 11])
def test_full_program_budget_is_required_before_first_call(budget, monkeypatch):
    import cncm.compound_program as substrate
    monkeypatch.setattr(substrate, "execute_procedure", lambda *a, **k: pytest.fail("primitive ran without reservation"))
    report = execute_program(correct_program(), PRIMITIVE, INPUTS, instruction_budget=budget)
    assert (report["status"], report["instructions_executed"], report["subcalls"]) == ("BUDGET_EXHAUSTED", 0, [])


@pytest.mark.parametrize("budget", [True, -1, 13, "12", 12.0])
def test_invalid_budget_is_not_coerced(budget):
    with pytest.raises(ContractError):
        execute_program(correct_program(), PRIMITIVE, INPUTS, instruction_budget=budget)


def test_changed_primitive_rejects_before_execution(monkeypatch):
    import cncm.compound_program as substrate
    monkeypatch.setattr(substrate, "execute_procedure", lambda *a, **k: pytest.fail("unpinned primitive ran"))
    with pytest.raises(ContractError, match="PINNED_PRIMITIVE"):
        execute_program(correct_program(), replace(PRIMITIVE, revision=2), INPUTS)


def test_composition_intermediate_input_bound_preserves_first_receipt_and_refuses_second():
    maximum = str((1 << 128) - 1)
    values = dict(a="1/" + maximum, b="3", c="5", d="0", e=maximum)
    report = execute_program(correct_program(), PRIMITIVE, values)
    assert report["status"] == "COMPOSITION_INPUT_LIMIT"
    assert report["output"] is None and report["instructions_executed"] == 6
    assert len(report["subcalls"]) == 1 and report["subcalls"][0]["execution"]["status"] == "SUCCESS"


def test_division_failure_keeps_actual_spent_instruction_count():
    report = execute_program(correct_program(), PRIMITIVE, {**INPUTS, "a": "0"})
    assert report["status"] == "DIVISION_BY_ZERO" and report["output"] is None
    assert report["instructions_executed"] == 5 and len(report["subcalls"]) == 1


@pytest.mark.parametrize("value", ["01", "-0", "2/2", "1/1", "1/0", "1.0", 2, True,
                                   "9" * 10000, str(1 << 128)])
def test_inputs_require_canonical_bounded_text_before_arithmetic(value):
    with pytest.raises(ContractError):
        execute_program(correct_program(), PRIMITIVE, {**INPUTS, "a": value})


@pytest.mark.parametrize("values", [{}, {**INPUTS, "x": "3"}, {k: v for k, v in INPUTS.items() if k != "a"}])
def test_no_answer_or_missing_original_parameter_is_admitted(values):
    with pytest.raises(ContractError):
        validate_inputs(values)


def test_smaller_primitive_limits_are_a_distinct_unsupported_composition_contract():
    with pytest.raises(ContractError, match="LIMITS_MISMATCH"):
        enumerate_programs(make_candidate(limits=ProcedureLimits(8, 128)))


def test_returned_wire_mutation_does_not_mutate_program():
    program = correct_program()
    before = program.program_digest
    wire = program.to_dict()
    wire["steps"][0]["a_ref"] = "e"
    assert program.program_digest == before and program.steps[0].a_ref == "a"
