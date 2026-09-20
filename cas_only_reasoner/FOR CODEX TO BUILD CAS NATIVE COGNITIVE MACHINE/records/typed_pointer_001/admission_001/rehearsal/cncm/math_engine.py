"""Bounded CCB-M1 math orchestration over the protected exact checker."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from .canonical import content_id, digest
from .math_kernel import check_math_step, issue_checked_math_claim
from .math_model import (
    ExactRational,
    MATH_CHECKER_VERSION,
    MATH_RESULT_SCHEMA_VERSION,
    MATH_THEORY_ID,
    MathCapabilityError,
    MathClaim,
    MathClaimStatus,
    MathContractError,
    MathGuardError,
    MathParseLimits,
    MathRelation,
    MathStatement,
    MathStepOperation,
    MathStepProposal,
    MathStepReceipt,
    Provenance,
    VariableExpression,
)
from .math_normalize import (
    LinearForm,
    canonicalize_linear_statement,
    expression_from_linear,
    normalize_linear,
    rational_expression,
)
from .math_parser import parse_math_statement
from .verification import VerificationReport


class MathTerminalStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNDERDETERMINED = "UNDERDETERMINED"
    NO_SOLUTION = "NO_SOLUTION"
    NEEDS_GUARD = "NEEDS_GUARD"
    NEEDS_CAPABILITY = "NEEDS_CAPABILITY"
    INVALID_PROOF = "INVALID_PROOF"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    FAULT = "FAULT"


@dataclass(frozen=True, slots=True)
class MathCheckedStep:
    index: int
    proposal: MathStepProposal
    receipt: MathStepReceipt
    resulting_claim: MathClaim | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "proposal": self.proposal.to_dict(),
            "receipt": self.receipt.to_dict(),
            "resulting_claim": (
                self.resulting_claim.to_dict() if self.resulting_claim is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class MathRunResult:
    problem_id: str
    theory_id: str
    input_statement: MathStatement
    solve_variable: str
    terminal_status: MathTerminalStatus
    solution: ExactRational | None
    claims: tuple[MathClaim, ...]
    checked_steps: tuple[MathCheckedStep, ...]
    first_failing_step: int | None
    detail: str

    @property
    def proof_digest(self) -> str:
        return digest([step.to_dict() for step in self.checked_steps])

    @property
    def final_claim(self) -> MathClaim | None:
        verified = [claim for claim in self.claims if claim.status is MathClaimStatus.VERIFIED]
        return verified[-1] if verified else None

    def evidence(self) -> dict[str, Any]:
        body = {
            "schema_version": "cncm.math-evidence/0.1",
            "problem_id": self.problem_id,
            "theory_id": self.theory_id,
            "checker_version": MATH_CHECKER_VERSION,
            "terminal_status": self.terminal_status.value,
            "proof_digest": self.proof_digest,
            "accepted_receipt_ids": [
                step.receipt.receipt_id for step in self.checked_steps if step.receipt.accepted
            ],
            "rejected_receipt_ids": [
                step.receipt.receipt_id for step in self.checked_steps if not step.receipt.accepted
            ],
            "final_claim_id": self.final_claim.claim_id if self.final_claim is not None else None,
            "verified": self.final_claim is not None,
            "first_failing_step": self.first_failing_step,
            "claim_boundary": {
                "exact_arithmetic_only": True,
                "proof_checker_protected": True,
                "candidate_self_verification": False,
                "bounded_counterexample_absence_is_proof": False,
                "approximation_used": False,
                "autonomous_axiom_change": False,
                "external_model_used": False,
            },
        }
        return {**body, "evidence_digest": digest(body)}

    def body(self) -> dict[str, Any]:
        return {
            "schema_version": MATH_RESULT_SCHEMA_VERSION,
            "problem_id": self.problem_id,
            "theory_id": self.theory_id,
            "checker_version": MATH_CHECKER_VERSION,
            "input_statement": self.input_statement.to_dict(),
            "solve_variable": self.solve_variable,
            "terminal_status": self.terminal_status.value,
            "solution": self.solution.to_dict() if self.solution is not None else None,
            "claims": [claim.to_dict() for claim in self.claims],
            "checked_steps": [step.to_dict() for step in self.checked_steps],
            "first_failing_step": self.first_failing_step,
            "detail": self.detail,
            "evidence": self.evidence(),
        }

    def to_dict(self) -> dict[str, Any]:
        body = self.body()
        return {**body, "result_digest": digest(body)}


class _ProofBuilder:
    def __init__(self, given: MathClaim) -> None:
        self.claims: dict[str, MathClaim] = {given.claim_id: given}
        self.derivations: dict[
            str, tuple[MathStepProposal, MathStepReceipt]
        ] = {}
        self.steps: list[MathCheckedStep] = []
        self.failed_at: int | None = None

    def step(
        self,
        *,
        operation: MathStepOperation,
        premise_claim_ids: Iterable[str],
        conclusion: MathStatement,
        parameter=None,
        status: MathClaimStatus = MathClaimStatus.DERIVED,
    ) -> MathClaim | None:
        proposal = MathStepProposal.create(
            operation=operation,
            premise_claim_ids=premise_claim_ids,
            proposed_conclusion=conclusion,
            parameter=parameter,
        )
        receipt = check_math_step(proposal, self.claims, self.derivations)
        claim = None
        if receipt.accepted and receipt.reconstructed_conclusion is not None:
            premise_assumptions = {
                assumption_id
                for premise_id in proposal.premise_claim_ids
                for assumption_id in self.claims[premise_id].assumption_claim_ids
            }
            premise_assumptions.update(
                premise_id
                for premise_id in proposal.premise_claim_ids
                if self.claims[premise_id].status is MathClaimStatus.ASSUMED
            )
            claim = issue_checked_math_claim(
                proposal=proposal,
                claims=self.claims,
                receipt=receipt,
                status=status,
                derivations=self.derivations,
                assumption_claim_ids=premise_assumptions,
                provenance=(
                    Provenance(
                        "math_rule",
                        operation.value,
                        operation.value,
                    ),
                ),
            )
            self.derivations[receipt.receipt_id] = (proposal, receipt)
            self.claims[claim.claim_id] = claim
        elif self.failed_at is None:
            self.failed_at = len(self.steps)
        self.steps.append(MathCheckedStep(len(self.steps), proposal, receipt, claim))
        return claim


def _problem_id(statement: MathStatement, variable: str, theory_id: str) -> str:
    return content_id(
        "math-problem",
        {
            "schema_version": "cncm.math-problem/0.1",
            "statement": statement.to_dict(),
            "solve_variable": variable,
            "theory_id": theory_id,
        },
    )


def _terminal_result(
    *,
    statement: MathStatement,
    variable: str,
    status: MathTerminalStatus,
    detail: str,
    given: MathClaim,
    builder: _ProofBuilder | None = None,
    solution: ExactRational | None = None,
) -> MathRunResult:
    claims = tuple((builder.claims if builder is not None else {given.claim_id: given}).values())
    steps = tuple(builder.steps) if builder is not None else ()
    return MathRunResult(
        problem_id=_problem_id(statement, variable, MATH_THEORY_ID),
        theory_id=MATH_THEORY_ID,
        input_statement=statement,
        solve_variable=variable,
        terminal_status=status,
        solution=solution,
        claims=claims,
        checked_steps=steps,
        first_failing_step=builder.failed_at if builder is not None else None,
        detail=detail,
    )


def solve_linear_statement(
    statement: MathStatement,
    variable: str,
) -> MathRunResult:
    """Propose and check an ordinary proof for one exact linear equation."""

    if not isinstance(variable, str) or not variable:
        raise MathContractError("solve variable must be a nonempty identifier")
    problem_id = _problem_id(statement, variable, MATH_THEORY_ID)
    given = MathClaim.create(
        statement=statement,
        status=MathClaimStatus.GIVEN,
        provenance=(Provenance("math_input", problem_id, "declared equation"),),
    )
    if statement.relation is not MathRelation.EQUAL:
        return _terminal_result(
            statement=statement,
            variable=variable,
            status=MathTerminalStatus.NEEDS_CAPABILITY,
            detail="linear solving currently accepts equality only",
            given=given,
        )

    try:
        left_form = normalize_linear(statement.left)
        right_form = normalize_linear(statement.right)
    except MathGuardError as exc:
        return _terminal_result(
            statement=statement,
            variable=variable,
            status=MathTerminalStatus.NEEDS_GUARD,
            detail=str(exc),
            given=given,
        )
    except MathCapabilityError as exc:
        return _terminal_result(
            statement=statement,
            variable=variable,
            status=MathTerminalStatus.NEEDS_CAPABILITY,
            detail=str(exc),
            given=given,
        )

    other_variables = (set(left_form.variables) | set(right_form.variables)) - {variable}
    if other_variables:
        return _terminal_result(
            statement=statement,
            variable=variable,
            status=MathTerminalStatus.NEEDS_CAPABILITY,
            detail=f"equation contains additional variables: {sorted(other_variables)}",
            given=given,
        )

    net_coefficient = left_form.coefficient(variable) - right_form.coefficient(variable)
    net_constant = right_form.constant - left_form.constant
    if net_coefficient.is_zero:
        status = (
            MathTerminalStatus.UNDERDETERMINED
            if net_constant.is_zero
            else MathTerminalStatus.NO_SOLUTION
        )
        detail = (
            "both sides normalize identically; every exact value satisfies the equation"
            if status is MathTerminalStatus.UNDERDETERMINED
            else "variable terms cancel but exact constants disagree"
        )
        return _terminal_result(
            statement=statement,
            variable=variable,
            status=status,
            detail=detail,
            given=given,
        )

    solution = net_constant / net_coefficient
    builder = _ProofBuilder(given)

    canonical = canonicalize_linear_statement(statement)
    current = builder.step(
        operation=MathStepOperation.SIMPLIFY_EXACT,
        premise_claim_ids=(given.claim_id,),
        conclusion=canonical,
    )
    if current is None:
        return _terminal_result(
            statement=statement,
            variable=variable,
            status=MathTerminalStatus.INVALID_PROOF,
            detail="protected checker rejected exact simplification",
            given=given,
            builder=builder,
        )

    current_left = normalize_linear(current.statement.left)
    current_right = normalize_linear(current.statement.right)
    right_coefficient = current_right.coefficient(variable)
    if not right_coefficient.is_zero:
        parameter = expression_from_linear(
            LinearForm.create(coefficients={variable: right_coefficient})
        )
        expected = MathStatement(
            expression_from_linear(current_left - LinearForm.create(coefficients={variable: right_coefficient})),
            MathRelation.EQUAL,
            expression_from_linear(current_right - LinearForm.create(coefficients={variable: right_coefficient})),
        )
        current = builder.step(
            operation=MathStepOperation.SUBTRACT_BOTH_SIDES,
            premise_claim_ids=(current.claim_id,),
            conclusion=expected,
            parameter=parameter,
        )
        if current is None:
            return _terminal_result(
                statement=statement,
                variable=variable,
                status=MathTerminalStatus.INVALID_PROOF,
                detail="protected checker rejected variable isolation",
                given=given,
                builder=builder,
            )
        current_left = normalize_linear(current.statement.left)
        current_right = normalize_linear(current.statement.right)

    if not current_left.constant.is_zero:
        parameter = rational_expression(current_left.constant)
        delta = LinearForm(current_left.constant)
        expected = MathStatement(
            expression_from_linear(current_left - delta),
            MathRelation.EQUAL,
            expression_from_linear(current_right - delta),
        )
        current = builder.step(
            operation=MathStepOperation.SUBTRACT_BOTH_SIDES,
            premise_claim_ids=(current.claim_id,),
            conclusion=expected,
            parameter=parameter,
        )
        if current is None:
            return _terminal_result(
                statement=statement,
                variable=variable,
                status=MathTerminalStatus.INVALID_PROOF,
                detail="protected checker rejected constant isolation",
                given=given,
                builder=builder,
            )
        current_left = normalize_linear(current.statement.left)
        current_right = normalize_linear(current.statement.right)

    coefficient = current_left.coefficient(variable)
    if coefficient != ExactRational(1):
        expected = MathStatement(
            VariableExpression(variable),
            MathRelation.EQUAL,
            rational_expression(solution),
        )
        current = builder.step(
            operation=MathStepOperation.DIVIDE_BOTH_SIDES,
            premise_claim_ids=(current.claim_id,),
            conclusion=expected,
            parameter=rational_expression(coefficient),
        )
        if current is None:
            return _terminal_result(
                statement=statement,
                variable=variable,
                status=MathTerminalStatus.INVALID_PROOF,
                detail="protected checker rejected nonzero coefficient division",
                given=given,
                builder=builder,
            )

    verified_statement = MathStatement(
        VariableExpression(variable),
        MathRelation.EQUAL,
        rational_expression(solution),
    )
    verified = builder.step(
        operation=MathStepOperation.VERIFY_LINEAR_SOLUTION,
        premise_claim_ids=(given.claim_id,),
        conclusion=verified_statement,
        status=MathClaimStatus.VERIFIED,
    )
    if verified is None:
        return _terminal_result(
            statement=statement,
            variable=variable,
            status=MathTerminalStatus.INVALID_PROOF,
            detail="protected checker rejected final exact substitution",
            given=given,
            builder=builder,
        )
    return _terminal_result(
        statement=statement,
        variable=variable,
        status=MathTerminalStatus.VERIFIED,
        detail="unique solution accepted after exact step reconstruction and substitution",
        given=given,
        builder=builder,
        solution=solution,
    )


def solve_linear_equation(
    notation: str,
    variable: str,
    *,
    limits: MathParseLimits = MathParseLimits(),
) -> MathRunResult:
    statement = parse_math_statement(
        notation,
        declared_variables=(variable,),
        limits=limits,
    )
    return solve_linear_statement(statement, variable)


def verify_math_result(bundle: Mapping[str, Any]) -> VerificationReport:
    """Re-execute a retained linear proof and require an exact bundle match."""

    try:
        required = {
            "schema_version",
            "problem_id",
            "theory_id",
            "checker_version",
            "input_statement",
            "solve_variable",
            "terminal_status",
            "solution",
            "claims",
            "checked_steps",
            "first_failing_step",
            "detail",
            "evidence",
            "result_digest",
        }
        if not isinstance(bundle, Mapping) or set(bundle) != required:
            raise MathContractError("math result fields do not match the frozen bundle shape")
        retained_body = dict(bundle)
        retained_digest = retained_body.pop("result_digest")
        if retained_digest != digest(retained_body):
            raise MathContractError("math result digest mismatch")
        statement = MathStatement.from_dict(bundle["input_statement"])
        variable = bundle["solve_variable"]
        if not isinstance(variable, str):
            raise MathContractError("solve_variable must be a string")
        rebuilt = solve_linear_statement(statement, variable).to_dict()
        if rebuilt != dict(bundle):
            raise MathContractError("semantic re-execution differs from retained math result")
    except (KeyError, MathContractError, TypeError, ValueError) as exc:
        return VerificationReport(False, (("math_semantic_reexecution", False),), (str(exc),))
    return VerificationReport(True, (("math_semantic_reexecution", True),), ())
