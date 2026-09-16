"""Engineering admission and independent substitution checks, without tensors."""
from copy import deepcopy
from itertools import permutations
from unittest.mock import patch

import pytest

from cncm.canonical import digest
from cncm.procedural_qualification import (
    EXAMINER_ID, check_procedure_call, policy_document, qualify_procedure,
    select_finite_candidate, verify_checked_call, verify_qualification)
from cncm.procedural_substrate import (
    ProcedureContractError, ProposalProvenance, make_candidate)


def checked(artifact=None, inputs=None, **kwargs):
    return check_procedure_call(artifact or make_candidate(),
        inputs or {"a": "3", "b": "5", "c": "26"},
        call_id=kwargs.pop("call_id", "parent-call-1"),
        branch_id=kwargs.pop("branch_id", "branch-parent"), **kwargs)


@pytest.mark.parametrize("inputs,answer", [
    ({"a": "3", "b": "5", "c": "26"}, "7"),
    ({"a": "-4", "b": "7", "c": "13"}, "-3/2"),
    ({"a": "2/3", "b": "-5/7", "c": "11/13"}, "213/91")])
def test_candidate_produces_answer_and_separate_checker_accepts(inputs, answer):
    # The ordinary answer-producing solver is forbidden on this path.
    with patch("cncm.math_engine.solve_linear_equation", side_effect=AssertionError("solver used")):
        report = checked(inputs=inputs)
    assert report["status"] == "CHECKED"
    assert report["execution"]["outputs"] == {"x": answer}
    assert report["math_receipt"]["accepted"] is True
    assert report["proposal"]["operation"] == "VERIFY_LINEAR_SOLUTION"
    assert report["binding"]["branch_id"] == "branch-parent"
    assert report["proposal"]["branch_id"] == report["inner_math_branch_id"]
    assert report["cost"] == {"instructions_executed": 6, "checker_calls": 1}
    assert verify_checked_call(make_candidate(), inputs, report,
        call_id="parent-call-1", branch_id="branch-parent")


def test_wrong_candidate_can_execute_but_checker_refuses():
    report = checked(make_candidate(combine="ADD_EXACT"))
    assert report["execution"]["status"] == "SUCCESS"
    assert report["status"] == "CHECKER_REJECTED"
    assert report["math_receipt"]["accepted"] is False


@pytest.mark.parametrize("order,combine", [(order, combine)
    for order in permutations(("a", "b", "c"))
    for combine in ("ADD_EXACT", "SUBTRACT_EXACT")])
def test_only_correct_form_passes_entire_frozen_panel(order, combine):
    report = qualify_procedure(make_candidate(order, combine))
    expected = order == ("c", "b", "a") and combine == "SUBTRACT_EXACT"
    assert (report["status"] == "ENGINEERING_PANEL_PASSED") is expected
    assert report["native_installation"] is False
    assert report["universal_correctness_proven"] is False
    assert len(report["qualification"]) == 8
    assert len(report["rejections"]) == 2


def test_development_selection_does_not_run_qualification():
    with patch("cncm.procedural_qualification.qualify_procedure", side_effect=AssertionError("exam leaked")):
        artifact, report = select_finite_candidate()
    assert artifact is not None
    assert report["status"] == "UNIQUE_CANDIDATE_SELECTED"
    assert len(report["candidates"]) == 12
    assert report["qualification_executed"] is False
    assert report["neural_learning"] is False
    assert report["cost"] == {"instructions_executed": 144, "checker_calls": 24}
    assert qualify_procedure(artifact)["status"] == "ENGINEERING_PANEL_PASSED"


def test_panels_are_disjoint_and_exclude_integrated_episode_inputs():
    policy = policy_document()
    sets = [{tuple(row[key] for key in ("a", "b", "c")) for row in policy[name]}
            for name in ("development", "qualification", "rejections")]
    assert all(not (left & right) for i, left in enumerate(sets) for right in sets[i+1:])
    assert ("3", "5", "26") not in set.union(*sets)
    assert ("-4", "7", "13") not in set.union(*sets)
    policy["qualification"][0]["a"] = "999"
    assert policy != policy_document()


@pytest.mark.parametrize("context", [
    {"call_id": "different-call", "branch_id": "branch-parent"},
    {"call_id": "parent-call-1", "branch_id": "different-branch"}])
def test_replay_rejects_wrong_trusted_caller(context):
    assert not verify_checked_call(make_candidate(), {"a": "3", "b": "5", "c": "26"},
                                   checked(), **context)


def test_replay_rejects_changed_inputs_version_budget_and_resealed_output():
    artifact = make_candidate()
    inputs = {"a": "3", "b": "5", "c": "26"}
    report = checked()
    context = {"call_id": "parent-call-1", "branch_id": "branch-parent"}
    assert not verify_checked_call(artifact, {**inputs, "c": "29"}, report, **context)
    assert not verify_checked_call(make_candidate(revision=2), inputs, report, **context)
    assert not verify_checked_call(artifact, inputs, report, instruction_budget=5, **context)
    forged = deepcopy(report)
    forged["execution"]["outputs"]["x"] = "8"
    forged["execution"]["report_sha256"] = digest({k:v for k,v in forged["execution"].items() if k != "report_sha256"})
    forged["report_sha256"] = digest({k:v for k,v in forged.items() if k != "report_sha256"})
    assert not verify_checked_call(artifact, inputs, forged, **context)


def test_resealed_forged_qualification_cannot_install_wrong_candidate():
    wrong = make_candidate(combine="ADD_EXACT")
    report = qualify_procedure(wrong)
    report["status"] = "ENGINEERING_PANEL_PASSED"
    report["report_sha256"] = digest({k:v for k,v in report.items() if k != "report_sha256"})
    assert not verify_qualification(wrong, report)
    assert verify_qualification(make_candidate(), qualify_procedure(make_candidate()))


def test_obvious_proposer_examiner_role_conflict_refused():
    artifact = make_candidate(provenance=ProposalProvenance(source_id=EXAMINER_ID))
    with pytest.raises(ProcedureContractError, match="PROPOSER_EXAMINER_CONFLICT"):
        qualify_procedure(artifact)


@pytest.mark.parametrize("inputs", [
    {"a": "0", "b": "0", "c": "0"}, {"a": "0", "b": "1", "c": "2"}])
def test_zero_coefficient_never_passes_by_vacuous_equation(inputs):
    with patch("cncm.procedural_qualification.check_math_step", side_effect=AssertionError("checker called")):
        report = checked(inputs=inputs)
    assert report["status"] == "DOMAIN_REJECTED"
    assert report["math_receipt"] is None
    assert report["cost"]["checker_calls"] == 0


def test_budget_exhaustion_never_becomes_a_checked_answer():
    report = checked(instruction_budget=5)
    assert report["status"] == "EXECUTION_REJECTED"
    assert report["execution"]["status"] == "BUDGET_EXHAUSTED"
    assert report["cost"] == {"instructions_executed": 0, "checker_calls": 0}


@pytest.mark.parametrize("inputs", [
    {"a": "3", "b": "5", "c": "26", "x": "7"},
    {"a": 3, "b": "5", "c": "26"},
    {"a": "3", "b": "5", "c": "9" * 10000},
    {"a": "3", "b": "5", "c": "26;exec(code)"}])
def test_malformed_or_answer_bearing_inputs_refused_before_checker(inputs):
    with patch("cncm.procedural_qualification.check_math_step", side_effect=AssertionError("checker called")):
        with pytest.raises(ProcedureContractError):
            checked(inputs=inputs)
