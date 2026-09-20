"""Finite call-program construction and independent substitution checks.

Construction examines public engineering development cases. Qualification uses
a distinct, fixed public panel, not secret custody or a general correctness
proof. The original checker evaluates a*(b*x+c)+d; it never solves for x.
All policy work counts are conservative accounting units, not measured FLOPs.
"""
from __future__ import annotations

import re

from .canonical import canonical_json, digest
from .model import ContractError
from .compound_program import (CallProgram, INPUT_NAMES, _primitive, _require,
                               enumerate_programs, execute_program, validate_inputs)
from .nested_verification import _add, _multiply, _parse_rational, _text
from .semantic_verification import resolve_memory as _protected_resolve_memory

CHECKER_ID = "cncm.compound-verifier/0.1"
REPORT_SCHEMA = "cncm.compound-verification/0.1"
CONSTRUCTION_SCHEMA = "cncm.compound-construction/0.1"
QUALIFICATION_SCHEMA = "cncm.compound-qualification/0.1"
MAX_REPORT_BYTES = 524288
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
# There are no fixture answer labels. Only independent original substitution
# judges a candidate's actual output. Development selection reads this panel.
_DEVELOPMENT = (
    ("2", "3", "5", "7", "35"),
    ("-3/2", "5/3", "-7/4", "11/5", "13/6"),
    ("7/5", "-2", "3/7", "-5/6", "19/4"),
    ("11", "7/3", "-13/5", "2/9", "-23/4"),
)
_QUALIFICATION = (
    ("3", "2", "4", "5", "47"),
    ("-2", "3", "-5", "7", "19"),
    ("2/3", "-5/7", "11/13", "-17/19", "23/29"),
    ("-7/11", "13/17", "-19/23", "29/31", "-37/41"),
    ("1", "-1", "0", "0", "9/7"),
    ("5/2", "7/3", "-11/5", "13/7", "0"),
    ("17", "19", "23", "29", "31"),
    ("-3/5", "-7/11", "13/17", "-19/23", "29/31"),
)
_DOMAIN = (
    ("0", "2", "3", "5", "7"),
    ("2", "0", "3", "5", "7"),
    ("0", "0", "3", "5", "7"),
    ("0", "-3/7", "0", "11/13", "11/13"),
)


def _inputs(values):
    return dict(zip(INPUT_NAMES, values, strict=True))


def _seal(body, field="report_digest"):
    result = {**body, field: digest(body)}
    _require(len(canonical_json(result).encode("utf-8")) <= MAX_REPORT_BYTES, "COMPOUND_REPORT_SIZE_LIMIT")
    return result


def _development_policy():
    # Deliberately excludes the qualification panel and its generator.
    return {"schema_version": "cncm.compound-development-policy/0.1",
            "grammar": "60_ONE_CALL_THEN_360_TWO_CALLS", "candidate_count": 420,
            "development": [_inputs(row) for row in _DEVELOPMENT],
            "per_case_policy_cost": {"instructions": 24, "checker_calls": 1},
            "claim_boundary": "FINITE_PUBLIC_ENGINEERING_CONSTRUCTION"}


def policy_document():
    return {**_development_policy(), "checker_id": CHECKER_ID,
            "qualification": [_inputs(row) for row in _QUALIFICATION],
            "domain": [_inputs(row) for row in _DOMAIN],
            "input_bits": 128, "intermediate_bits": 512,
            "default_budget": {"instructions": 100000, "checker_calls": 10000},
            "qualification_policy_cost": {"instructions": 288, "checker_calls": 12},
            "qualification_boundary": "FIXED_PUBLIC_PANEL_NOT_GENERAL_PROOF"}


def verify_original(inputs, x):
    """Evaluate the original expression only; no inverse or expected-x formula."""
    values = validate_inputs(inputs)
    parsed = {name: _parse_rational(values[name], 128, name) for name in INPUT_NAMES}
    candidate = None if x is None else _parse_rational(x, 512, "candidate output")
    lhs = None
    if not parsed["a"] or not parsed["b"]:
        status, reason = "DOMAIN_REJECTED", "ZERO_LEADING_COEFFICIENT"
    else:
        _require(candidate is not None, "CANDIDATE_OUTPUT_REQUIRED")
        try:
            inner = _add(_multiply(parsed["b"], candidate), parsed["c"])
            lhs_value = _add(_multiply(parsed["a"], inner), parsed["d"])
            lhs = _text(lhs_value)
            valid = lhs_value == parsed["e"]
            status, reason = ("CHECKED", "EXACT_ORIGINAL_SUBSTITUTION") if valid else (
                "REJECTED", "ORIGINAL_EQUATION_MISMATCH")
        except ContractError:
            status, reason = "ARITHMETIC_LIMIT", "ORIGINAL_INTERMEDIATE_LIMIT"
    return _seal({"schema_version": REPORT_SCHEMA, "checker_id": CHECKER_ID,
                  "claim": "ORIGINAL_EXPRESSION_SUBSTITUTION_ONLY", "inputs": values,
                  "output": x, "lhs": lhs, "rhs": values["e"], "status": status, "reason": reason})


def check_program_call(program, primitive, inputs, *, call_id, branch_id):
    _require(type(program) is CallProgram, "TYPED_CALL_PROGRAM_REQUIRED")
    CallProgram.from_dict(program.to_dict())
    _primitive(primitive)
    _require(program.primitive_sha256 == primitive.artifact_sha256, "PINNED_PRIMITIVE_MISMATCH")
    for value in (call_id, branch_id):
        _require(type(value) is str and _IDENTIFIER.fullmatch(value) is not None, "CALL_BINDING_INVALID")
    values = validate_inputs(inputs)
    execution, original, output = None, None, None
    if values["a"] == "0" or values["b"] == "0":
        original = verify_original(values, None)
        status = "DOMAIN_REJECTED"
    else:
        execution = execute_program(program, primitive, values)
        if execution["status"] != "SUCCESS":
            status = "EXECUTION_REJECTED"
        else:
            output = execution["output"]
            original = verify_original(values, output)
            status = "CHECKED" if original["status"] == "CHECKED" else "CHECKER_REJECTED"
    return _seal({"schema_version": REPORT_SCHEMA, "checker_id": CHECKER_ID,
                  "call_id": call_id, "branch_id": branch_id, "inputs": values,
                  "program_digest": program.program_digest, "primitive_sha256": primitive.artifact_sha256,
                  "status": status, "output": output, "execution": execution, "original_check": original,
                  "policy_cost": {"instructions": 24, "checker_calls": 1},
                  "actual_work": {"primitive_instructions": execution["instructions_executed"] if execution else 0,
                                  "original_checks": int(original is not None)}})


def _summary(report):
    return {"status": report["status"], "report_digest": report["report_digest"]}


def construct_program(primitive, *, candidate_limit=420):
    """Exhaust the requested canonical prefix; only a complete unique result selects.

    Every admitted candidate is checked on all four development inputs. This
    function never reads qualification/domain cases or invokes qualification.
    A prefix cannot establish uniqueness, even if it contains a survivor.
    """
    _require(type(candidate_limit) is int and 1 <= candidate_limit <= 420, "CANDIDATE_LIMIT_INVALID")
    programs = enumerate_programs(primitive)[:candidate_limit]
    candidates, survivors = [], []
    instructions = checks = 0
    for index, program in enumerate(programs):
        rows = []
        survives = True
        for case_index, values in enumerate(_DEVELOPMENT):
            report = check_program_call(program, primitive, _inputs(values),
                                        call_id=f"development-{index}-{case_index}", branch_id="construction")
            rows.append(_summary(report))
            survives = survives and report["status"] == "CHECKED"
            instructions += report["actual_work"]["primitive_instructions"]
            checks += report["actual_work"]["original_checks"]
        candidates.append({"program": program.to_dict(), "checks": rows})
        if survives:
            survivors.append(program)
    selected = survivors[0] if candidate_limit == 420 and len(survivors) == 1 else None
    status = "SEARCH_EXHAUSTED" if candidate_limit < 420 else "SELECTED" if selected else "NO_UNIQUE_CANDIDATE"
    body = {"schema_version": CONSTRUCTION_SCHEMA, "claim_boundary": "FINITE_PUBLIC_ENGINEERING_CONSTRUCTION",
            "development_policy_digest": digest(_development_policy()),
            "primitive_sha256": primitive.artifact_sha256,
            "candidate_limit": candidate_limit, "candidate_count": len(programs),
            "status": status, "selected_artifact": selected.to_dict() if selected else None,
            "survivor_digests": [row.program_digest for row in survivors], "candidates": candidates,
            "policy_cost": {"instructions": candidate_limit * 4 * 24, "checker_calls": candidate_limit * 4},
            "actual_work": {"primitive_instructions": instructions, "original_checks": checks}}
    return selected, _seal(body)


def qualify_program(program, primitive):
    positive, domains = [], []
    instructions = checks = 0
    for category, cases, output in (("qualification", _QUALIFICATION, positive), ("domain", _DOMAIN, domains)):
        for index, values in enumerate(cases):
            report = check_program_call(program, primitive, _inputs(values),
                                        call_id=f"{category}-{index}", branch_id="qualification")
            output.append({"inputs": _inputs(values), **_summary(report)})
            instructions += report["actual_work"]["primitive_instructions"]
            checks += report["actual_work"]["original_checks"]
    valid = all(row["status"] == "CHECKED" for row in positive) and all(
        row["status"] == "DOMAIN_REJECTED" for row in domains)
    return _seal({"schema_version": QUALIFICATION_SCHEMA,
                  "claim_boundary": "FIXED_PUBLIC_PANEL_NOT_GENERAL_PROOF",
                  "program_digest": program.program_digest, "primitive_sha256": primitive.artifact_sha256,
                  "policy_digest": digest(policy_document()), "status": "QUALIFIED" if valid else "REJECTED",
                  "qualification_cases": positive, "domain_cases": domains,
                  "policy_cost": {"instructions": 288, "checker_calls": 12},
                  "actual_work": {"primitive_instructions": instructions, "original_checks": checks}})


def verify_input_resolution(problem, bindings, resolved_inputs, history, trusted_ingress, *, source_profile_digest):
    """Independently reconstruct all five scalars from exact admitted source heads.

    The model's resolved_inputs and references helpers are never invoked. A
    valid receipt establishes exact substitution, not factual verification.
    """
    from .compound_model import CompoundProblem
    from .semantic_model import MemoryRef, RecallBinding
    from .semantic_verification import _history, _typed_inputs

    trusted = _typed_inputs(history, trusted_ingress, source_profile_digest)
    _require(type(problem) is CompoundProblem, "TYPED_COMPOUND_PROBLEM_REQUIRED")
    CompoundProblem.from_dict(problem.to_dict())
    _require(type(bindings) is tuple and len(bindings) <= 5
             and all(type(row) is RecallBinding for row in bindings), "TYPED_COMPOUND_BINDINGS_REQUIRED")
    for binding in bindings:
        RecallBinding.from_dict(binding.to_dict())
    supplied_inputs = validate_inputs(resolved_inputs)
    payload = {"problem_digest": problem.input_hash, "history_digest": digest([row.to_dict() for row in history]),
               "history_count": len(history), "bindings": [row.to_dict() for row in bindings],
               "resolved_inputs": supplied_inputs}
    statuses = []

    def receipt(status, reason):
        kinds = set(statuses)
        support = "NONE" if not kinds else next(iter(kinds)) if len(kinds) == 1 else "MIXED_ATTESTATIONS"
        return _seal({"schema_version": "cncm.verifier-receipt/0.1", "checker_id": CHECKER_ID,
                      "source_profile_digest": source_profile_digest, "domain": "COMPOUND_INPUTS",
                      "claim": "EXACT_COMPOUND_INPUT_SUBSTITUTION", "status": status, "reason": reason,
                      "support": support, "factual_status": "NOT_INDEPENDENTLY_VERIFIED", "bindings": payload},
                     "receipt_digest")

    _, _, history_reason = _history(history, trusted)
    if history_reason:
        return receipt("INVALID", history_reason)
    if problem.updates and (len(history) < len(problem.updates)
                            or tuple(history[-len(problem.updates):]) != problem.updates):
        return receipt("INVALID", "PROBLEM_UPDATES_NOT_ADMITTED")
    parameters = dict(problem.parameters)
    key = lambda ref: (ref.scope, ref.key, ref.evidence_requirement)
    wanted = {key(value): value for value in parameters.values() if type(value) is MemoryRef}
    if tuple(key(row.ref) for row in bindings) != tuple(sorted(wanted)):
        return receipt("INVALID", "BINDING_SET_MISMATCH")
    recalled = {}
    for binding in bindings:
        expected, source_receipt = _protected_resolve_memory(
            history, wanted[key(binding.ref)], trusted_ingress, source_profile_digest=source_profile_digest)
        if expected is None:
            payload["recall_refusal"] = source_receipt
            return receipt(source_receipt["status"], source_receipt["reason"])
        if binding.to_dict() != expected.to_dict():
            return receipt("INVALID", "RECALL_BINDING_MISMATCH")
        recalled[key(binding.ref)] = expected.value
        statuses.extend(expected.statuses)
    expected_inputs = {name: recalled[key(value)] if type(value) is MemoryRef else value
                       for name, value in parameters.items()}
    if supplied_inputs != expected_inputs:
        return receipt("INVALID", "RESOLVED_INPUTS_MISMATCH")
    return receipt("VALID", "EXACT_COMPOUND_INPUT_SUBSTITUTION")
