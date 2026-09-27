"""Bounded procedure checking and finite selection; no native write authority.

Candidates produce x by executing their sealed bytes. The existing CAS-Math
checker tests that x by substitution into the original equation. Development
and qualification inputs are fixed, disjoint, public engineering fixtures;
they are not secret exams or a claim of independent empirical generalization.
Every later invocation still requires its own check. No solver produces x here.
"""
from __future__ import annotations

from itertools import permutations
import re

from .canonical import canonical_json, digest
from .math_kernel import check_math_step
from .math_model import (MATH_BRANCH_ID, MATH_CHECKER_VERSION, MATH_THEORY_ID,
                         MathClaim, MathClaimStatus, MathStepOperation,
                         MathStepProposal)
from .math_parser import parse_math_statement
from .model import Provenance
from .procedural_substrate import (ProcedureArtifact, ProcedureContractError,
                                   execute_procedure, make_candidate)

CHECKED_SCHEMA = "cncm.checked-procedure-execution/0.1"
QUALIFICATION_SCHEMA = "cncm.procedure-engineering-qualification/0.1"
SELECTION_SCHEMA = "cncm.finite-procedure-selection/0.1"
POLICY_REVISION = "cncm.linear-substitution-engineering-panel/0.1"
EXAMINER_ID = "protected-linear-substitution-checker"
BOUNDARY = "CHECKED_CANDIDATE_ONLY_NO_KERNEL_INSTALLATION"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_DEVELOPMENT = (("2", "3", "17"), ("-3", "8", "2"))
_QUALIFICATION = (("1", "0", "0"), ("-2", "5", "11"),
                  ("2/3", "-5/7", "11/13"), ("7/5", "13/11", "-17/3"),
                  ("-5/2", "0", "23/7"), ("11", "-19", "0"),
                  ("1/17", "1/19", "1/23"), ("101", "-103", "107"))
_REJECTIONS = (("0", "1", "2"), ("0", "0", "0"))


def _require(condition, reason):
    if not condition:
        raise ProcedureContractError(reason)


def _inputs(values):
    return dict(zip(("a", "b", "c"), values, strict=True))


def _seal(body):
    return {**body, "report_sha256": digest(body)}


def policy_document():
    """Return a fresh immutable-by-convention policy description, with no answers."""
    body = {"revision": POLICY_REVISION, "examiner_id": EXAMINER_ID,
            "checker_version": MATH_CHECKER_VERSION, "theory_id": MATH_THEORY_ID,
            "development": [_inputs(row) for row in _DEVELOPMENT],
            "qualification": [_inputs(row) for row in _QUALIFICATION],
            "rejections": [_inputs(row) for row in _REJECTIONS],
            "domain": "canonical bounded rationals a,b,c with a != 0",
            "candidate_grammar_size": 12,
            "claim_boundary": BOUNDARY,
            "fixture_custody": "public fixed engineering panel, not secret held-out evaluation"}
    return {**body, "policy_sha256": digest(body)}


def check_procedure_call(artifact, inputs, *, call_id, branch_id, instruction_budget=6):
    """Execute sealed candidate bytes and check the answer, without committing it.

The v0.1 math checker admits only its own fixed branch identifier. The outer
binding retains the actual caller branch; it does not relabel the inner proof.
"""
    for value in (call_id, branch_id):
        _require(type(value) is str and _ID.fullmatch(value), "CALL_BINDING_INVALID")
    _require(type(artifact) is ProcedureArtifact, "TYPED_ARTIFACT_REQUIRED")
    # Executor validation bounds canonical input text and arithmetic before any
    # parsing/checking below. Its returned candidate is the only source of x.
    execution = execute_procedure(artifact, inputs, instruction_budget=instruction_budget)
    binding = {"call_id": call_id, "branch_id": branch_id,
               "artifact_sha256": artifact.artifact_sha256,
               "inputs_sha256": execution.inputs_sha256,
               "checker_version": MATH_CHECKER_VERSION, "theory_id": MATH_THEORY_ID}
    given = proposal = receipt = None
    if inputs["a"] == "0":
        status = "DOMAIN_REJECTED"
    elif execution.status != "SUCCESS":
        status = "EXECUTION_REJECTED"
    else:
        a, b, c = (inputs[key] for key in ("a", "b", "c"))
        equation = parse_math_statement(f"({a}) * x + ({b}) = ({c})")
        given = MathClaim.create(statement=equation, status=MathClaimStatus.GIVEN,
            provenance=(Provenance("bound_procedure_call", call_id, digest(binding)),))
        proposal = MathStepProposal.create(operation=MathStepOperation.VERIFY_LINEAR_SOLUTION,
            premise_claim_ids=(given.claim_id,),
            proposed_conclusion=parse_math_statement(f"x = ({execution.output})"))
        receipt = check_math_step(proposal, (given,))
        status = "CHECKED" if receipt.accepted else "CHECKER_REJECTED"
    return _seal({"schema_version": CHECKED_SCHEMA, "binding": binding,
        "claim_boundary": BOUNDARY, "status": status, "execution": execution.to_dict(),
        "inputs": dict(inputs), "inner_math_branch_id": MATH_BRANCH_ID,
        "given": given.to_dict() if given else None,
        "proposal": proposal.to_dict() if proposal else None,
        "math_receipt": receipt.to_dict() if receipt else None,
        "cost": {"instructions_executed": execution.instructions_executed,
                 "checker_calls": int(receipt is not None)}})


def verify_checked_call(artifact, inputs, report, *, call_id, branch_id, instruction_budget=6):
    """Re-execute against the caller's trusted binding, not report-supplied context."""
    if type(report) is not dict:
        return False
    try:
        rebuilt = check_procedure_call(artifact, inputs, call_id=call_id,
                    branch_id=branch_id, instruction_budget=instruction_budget)
        return canonical_json(report) == canonical_json(rebuilt)
    except (TypeError, ValueError, KeyError, OverflowError):
        return False


def qualify_procedure(artifact):
    """Rebuild a fixed engineering admission panel; no supplied receipt is trusted.

Role labels are not authentication. This rejects the obvious examiner-as-source
mislabel and uses a separate executable checker, but makes no human/external
exam custody claim. Native installation must reconstruct this result itself.
"""
    _require(type(artifact) is ProcedureArtifact, "TYPED_ARTIFACT_REQUIRED")
    _require(artifact.provenance.source_id != EXAMINER_ID, "PROPOSER_EXAMINER_CONFLICT")
    rows = []
    for i, values in enumerate(_QUALIFICATION):
        rows.append(check_procedure_call(artifact, _inputs(values),
                    call_id=f"qualification-{i}", branch_id="qualification-child"))
    rejections = []
    for i, values in enumerate(_REJECTIONS):
        report = check_procedure_call(artifact, _inputs(values),
                  call_id=f"rejection-{i}", branch_id="qualification-child")
        rejections.append(report)
    accepted = all(row["status"] == "CHECKED" for row in rows) and all(
        row["status"] == "DOMAIN_REJECTED" and
        row["execution"]["status"] == "DIVISION_BY_ZERO" for row in rejections)
    all_rows = rows + rejections
    return _seal({"schema_version": QUALIFICATION_SCHEMA,
        "policy_sha256": policy_document()["policy_sha256"],
        "artifact_sha256": artifact.artifact_sha256, "examiner_id": EXAMINER_ID,
        "status": "ENGINEERING_PANEL_PASSED" if accepted else "ENGINEERING_PANEL_FAILED",
        "claim_boundary": BOUNDARY, "qualification": rows, "rejections": rejections,
        "cost": {"instructions_executed": sum(row["cost"]["instructions_executed"] for row in all_rows),
                 "checker_calls": sum(row["cost"]["checker_calls"] for row in all_rows)},
        "universal_correctness_proven": False, "native_installation": False})


def verify_qualification(artifact, report):
    if type(report) is not dict:
        return False
    try:
        return canonical_json(report) == canonical_json(qualify_procedure(artifact))
    except (TypeError, ValueError, KeyError, OverflowError):
        return False


def select_finite_candidate():
    """Select among exactly 12 forms using development cases only.

No qualification inputs or expected answers enter the selection. Finite grammar
selection is not learned neural program synthesis. Qualification is a separate
call so a future coordinator can charge and govern it independently.
"""
    rows, accepted = [], []
    for order in permutations(("a", "b", "c")):
        for combine in ("ADD_EXACT", "SUBTRACT_EXACT"):
            artifact = make_candidate(order, combine)
            calls = [check_procedure_call(artifact, _inputs(values),
                     call_id=f"development-{i}", branch_id="development-child")
                     for i, values in enumerate(_DEVELOPMENT)]
            passed = all(call["status"] == "CHECKED" for call in calls)
            rows.append({"artifact": artifact.to_dict(), "passed": passed, "calls": calls})
            if passed:
                accepted.append(artifact)
    selected = accepted[0] if len(accepted) == 1 else None
    report = _seal({"schema_version": SELECTION_SCHEMA,
        "policy_sha256": policy_document()["policy_sha256"],
        "status": "UNIQUE_CANDIDATE_SELECTED" if selected else "NO_UNIQUE_CANDIDATE",
        "selected_artifact_sha256": selected.artifact_sha256 if selected else None,
        "claim_boundary": BOUNDARY, "candidates": rows,
        "cost": {"instructions_executed": sum(call["cost"]["instructions_executed"]
                                              for row in rows for call in row["calls"]),
                 "checker_calls": sum(call["cost"]["checker_calls"]
                                      for row in rows for call in row["calls"])},
        "qualification_executed": False, "neural_learning": False})
    return selected, report
