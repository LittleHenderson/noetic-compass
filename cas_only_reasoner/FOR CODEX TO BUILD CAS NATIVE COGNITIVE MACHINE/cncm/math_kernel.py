"""Protected, pure CAS-Math step reconstruction and verification.

This module accepts no mutable authority and performs no state writes.  It
reconstructs each admitted transformation from cited claims and frozen rules.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from .math_model import (
    AddExpression,
    ExactRational,
    MathCapabilityError,
    MathClaim,
    MathClaimStatus,
    MathContractError,
    MathExpression,
    MathGuardError,
    MATH_MAX_DERIVATION_DEPTH,
    MATH_MAX_RECEIPT_RECHECKS,
    MathRejectionCode,
    MathRelation,
    MathStatement,
    MathStepOperation,
    MathStepProposal,
    MathStepReceipt,
    MultiplyExpression,
    NegateExpression,
    Provenance,
    VariableExpression,
)
from .math_normalize import (
    ONE,
    ZERO,
    canonicalize_linear_statement,
    evaluate_statement,
    normalize_linear,
    same_linear_expression,
    same_linear_statement,
    substitute_statement,
)


_ADMISSIBLE_SUPPORT = {
    MathClaimStatus.GIVEN,
    MathClaimStatus.ASSUMED,
    MathClaimStatus.DERIVED,
    MathClaimStatus.VERIFIED,
}


def _reject(
    proposal: MathStepProposal,
    code: MathRejectionCode,
    detail: str,
) -> MathStepReceipt:
    return MathStepReceipt.create(
        proposal=proposal,
        accepted=False,
        reconstructed_conclusion=None,
        rejection_code=code,
        detail=detail,
    )


def _accept(
    proposal: MathStepProposal,
    conclusion: MathStatement,
    *guards: str,
) -> MathStepReceipt:
    return MathStepReceipt.create(
        proposal=proposal,
        accepted=True,
        reconstructed_conclusion=conclusion,
        discharged_guards=guards,
    )


def _same_expression(left: MathExpression, right: MathExpression) -> bool:
    # The frozen theory is exact Q-linear arithmetic.  Unsupported or
    # undefined expressions must fail closed instead of gaining authority from
    # a structural-text fallback.
    return same_linear_expression(left, right)


def _same_statement(left: MathStatement, right: MathStatement) -> bool:
    if left.relation is not right.relation:
        return False
    return same_linear_statement(left, right)


def _canonical(statement: MathStatement) -> MathStatement:
    try:
        return canonicalize_linear_statement(statement)
    except MathCapabilityError:
        return statement


def _constant(expression: MathExpression) -> ExactRational:
    normalized = normalize_linear(expression)
    if not normalized.is_constant:
        raise MathCapabilityError("operation parameter must be an exact constant")
    return normalized.constant


def _scaled_statement(
    premise: MathStatement,
    parameter: MathExpression,
    *,
    divide: bool,
) -> tuple[MathStatement, tuple[str, ...]]:
    scalar = _constant(parameter)
    guards: list[str] = []
    if scalar.is_zero:
        raise MathGuardError("scale must be nonzero")
    if divide:
        scalar = ONE / scalar
        guards.append("divisor_nonzero")
    else:
        guards.append("scale_nonzero")

    factor = parameter
    if divide:
        from .math_model import DivideExpression, IntegerExpression

        def transform(value: MathExpression) -> MathExpression:
            return DivideExpression(value, factor)
    else:
        def transform(value: MathExpression) -> MathExpression:
            return MultiplyExpression((value, factor))

    left = transform(premise.left)
    right = transform(premise.right)
    if premise.relation is MathRelation.LESS_THAN:
        if scalar.sign < 0:
            left, right = right, left
            guards.append("negative_scale_reverses_inequality")
        else:
            guards.append("positive_scale_preserves_inequality")
    return _canonical(MathStatement(left, premise.relation, right)), tuple(guards)


def _transitive_equal(premises: tuple[MathClaim, ...]) -> MathStatement | None:
    first, second = premises
    if (
        first.statement.relation is not MathRelation.EQUAL
        or second.statement.relation is not MathRelation.EQUAL
    ):
        return None
    orientations = lambda statement: (
        (statement.left, statement.right),
        (statement.right, statement.left),
    )
    for left_start, left_middle in orientations(first.statement):
        for right_middle, right_end in orientations(second.statement):
            if _same_expression(left_middle, right_middle):
                return _canonical(
                    MathStatement(left_start, MathRelation.EQUAL, right_end)
                )
    return None


def _transitive_less_than(premises: tuple[MathClaim, ...]) -> MathStatement | None:
    first, second = premises
    if (
        first.statement.relation is not MathRelation.LESS_THAN
        or second.statement.relation is not MathRelation.LESS_THAN
    ):
        return None
    if _same_expression(first.statement.right, second.statement.left):
        return _canonical(
            MathStatement(first.statement.left, MathRelation.LESS_THAN, second.statement.right)
        )
    if _same_expression(second.statement.right, first.statement.left):
        return _canonical(
            MathStatement(second.statement.left, MathRelation.LESS_THAN, first.statement.right)
        )
    return None


def _substitution_is_supported(
    variable: str,
    replacement: MathExpression,
    equality_claims: Iterable[MathClaim],
) -> bool:
    symbol = VariableExpression(variable)
    for claim in equality_claims:
        statement = claim.statement
        if statement.relation is not MathRelation.EQUAL:
            continue
        if _same_expression(statement.left, symbol) and _same_expression(
            statement.right, replacement
        ):
            return True
        if _same_expression(statement.right, symbol) and _same_expression(
            statement.left, replacement
        ):
            return True
    return False


def _linear_solution(
    premise: MathStatement,
    conclusion: MathStatement,
) -> tuple[str, ExactRational] | None:
    if (
        premise.relation is not MathRelation.EQUAL
        or conclusion.relation is not MathRelation.EQUAL
    ):
        return None
    candidates = (
        (conclusion.left, conclusion.right),
        (conclusion.right, conclusion.left),
    )
    for possible_variable, possible_value in candidates:
        if not isinstance(possible_variable, VariableExpression):
            continue
        value_form = normalize_linear(possible_value)
        if not value_form.is_constant:
            continue
        if possible_variable.name not in premise.variables:
            continue
        left_form = normalize_linear(premise.left)
        right_form = normalize_linear(premise.right)
        all_variables = set(left_form.variables) | set(right_form.variables)
        if all_variables != {possible_variable.name}:
            continue
        net_coefficient = left_form.coefficient(
            possible_variable.name
        ) - right_form.coefficient(possible_variable.name)
        if net_coefficient.is_zero:
            continue
        exact_solution = (right_form.constant - left_form.constant) / net_coefficient
        if value_form.constant != exact_solution:
            continue
        return possible_variable.name, exact_solution
    return None


def _check_math_step(
    proposal: MathStepProposal,
    claims: Mapping[str, MathClaim] | Iterable[MathClaim],
    derivations: Mapping[
        str, tuple[MathStepProposal, MathStepReceipt]
    ] | None = None,
    *,
    _validating_receipts: frozenset[str],
    _remaining_rechecks: list[int],
) -> MathStepReceipt:
    """Reconstruct one step.  Caller fields never determine acceptance."""

    if not isinstance(proposal, MathStepProposal):
        raise MathContractError("proposal must be a typed MathStepProposal")
    if _remaining_rechecks[0] <= 0:
        return _reject(
            proposal,
            MathRejectionCode.BUDGET_EXHAUSTED,
            "derivation receipt recheck budget exhausted",
        )
    _remaining_rechecks[0] -= 1
    if len(_validating_receipts) >= MATH_MAX_DERIVATION_DEPTH:
        return _reject(
            proposal,
            MathRejectionCode.BUDGET_EXHAUSTED,
            "derivation depth limit exhausted",
        )
    if isinstance(claims, Mapping):
        claim_map = dict(claims)
        if any(
            not isinstance(key, str)
            or not isinstance(claim, MathClaim)
            or key != claim.claim_id
            for key, claim in claim_map.items()
        ):
            return _reject(
                proposal,
                MathRejectionCode.UNVERIFIED_PREMISE,
                "claim mapping keys must equal the content-derived claim identifiers",
            )
    else:
        claim_values = tuple(claims)
        if any(not isinstance(item, MathClaim) for item in claim_values):
            return _reject(
                proposal,
                MathRejectionCode.UNVERIFIED_PREMISE,
                "all cited premises must be typed MathClaim objects",
            )
        claim_map = {item.claim_id: item for item in claim_values}
        if len(claim_map) != len(claim_values):
            return _reject(
                proposal,
                MathRejectionCode.UNVERIFIED_PREMISE,
                "premise collection contains duplicate claim identifiers",
            )
    try:
        premises = tuple(claim_map[claim_id] for claim_id in proposal.premise_claim_ids)
    except KeyError as exc:
        return _reject(
            proposal,
            MathRejectionCode.UNKNOWN_PREMISE,
            f"unknown premise claim: {exc.args[0]}",
        )
    if any(claim.theory_id != proposal.theory_id for claim in premises):
        return _reject(
            proposal,
            MathRejectionCode.THEORY_MISMATCH,
            "premise and proposal theory identities differ",
        )
    for claim in premises:
        if claim.status not in {MathClaimStatus.DERIVED, MathClaimStatus.VERIFIED}:
            continue
        receipt_id = claim.derivation_receipt_id
        if receipt_id is None or derivations is None or receipt_id not in derivations:
            return _reject(
                proposal,
                MathRejectionCode.UNVERIFIED_PREMISE,
                "derived or verified premise lacks its independently checked derivation",
            )
        if receipt_id in _validating_receipts:
            return _reject(
                proposal,
                MathRejectionCode.UNVERIFIED_PREMISE,
                "cyclic derivation receipt dependency",
            )
        derivation = derivations[receipt_id]
        if (
            not isinstance(derivation, tuple)
            or len(derivation) != 2
            or not isinstance(derivation[0], MathStepProposal)
            or not isinstance(derivation[1], MathStepReceipt)
        ):
            return _reject(
                proposal,
                MathRejectionCode.UNVERIFIED_PREMISE,
                "derivation registry entry is malformed",
            )
        derivation_proposal, retained_receipt = derivation
        if (
            claim.status is MathClaimStatus.VERIFIED
            and derivation_proposal.operation
            not in {
                MathStepOperation.EVALUATE_EXACT,
                MathStepOperation.VERIFY_LINEAR_SOLUTION,
            }
        ):
            return _reject(
                proposal,
                MathRejectionCode.UNVERIFIED_PREMISE,
                "VERIFIED status is not authorized by the cited checker operation",
            )
        expected_assumptions: set[str] = set()
        for derivation_premise_id in derivation_proposal.premise_claim_ids:
            derivation_premise = claim_map.get(derivation_premise_id)
            if derivation_premise is None:
                return _reject(
                    proposal,
                    MathRejectionCode.UNVERIFIED_PREMISE,
                    "derivation registry cites an unavailable premise",
                )
            expected_assumptions.update(derivation_premise.assumption_claim_ids)
            if derivation_premise.status is MathClaimStatus.ASSUMED:
                expected_assumptions.add(derivation_premise.claim_id)
        if claim.assumption_claim_ids != tuple(sorted(expected_assumptions)):
            return _reject(
                proposal,
                MathRejectionCode.UNVERIFIED_PREMISE,
                "derived claim assumption closure does not match its receipt premises",
            )
        rebuilt_receipt = _check_math_step(
            derivation_proposal,
            claim_map,
            derivations,
            _validating_receipts=_validating_receipts | {receipt_id},
            _remaining_rechecks=_remaining_rechecks,
        )
        if rebuilt_receipt.rejection_code is MathRejectionCode.BUDGET_EXHAUSTED:
            return _reject(
                proposal,
                MathRejectionCode.BUDGET_EXHAUSTED,
                rebuilt_receipt.detail,
            )
        if (
            retained_receipt.receipt_id != receipt_id
            or rebuilt_receipt.to_dict() != retained_receipt.to_dict()
            or not retained_receipt.accepted
            or retained_receipt.reconstructed_conclusion is None
            or retained_receipt.reconstructed_conclusion.to_dict()
            != claim.statement.to_dict()
            or retained_receipt.theory_id != claim.theory_id
        ):
            return _reject(
                proposal,
                MathRejectionCode.UNVERIFIED_PREMISE,
                "derived premise does not match a semantically rechecked receipt",
            )
    if any(claim.status not in _ADMISSIBLE_SUPPORT for claim in premises):
        return _reject(
            proposal,
            MathRejectionCode.INVALID_TRANSFORMATION,
            "conjectured, disproved, or unknown claims cannot support a proof step",
        )

    operation = proposal.operation
    expected_count = {
        MathStepOperation.EVALUATE_EXACT: 0,
        MathStepOperation.SIMPLIFY_EXACT: 1,
        MathStepOperation.ADD_BOTH_SIDES: 1,
        MathStepOperation.SUBTRACT_BOTH_SIDES: 1,
        MathStepOperation.MULTIPLY_BOTH_SIDES: 1,
        MathStepOperation.DIVIDE_BOTH_SIDES: 1,
        MathStepOperation.VERIFY_LINEAR_SOLUTION: 1,
        MathStepOperation.TRANSITIVE_EQUAL: 2,
        MathStepOperation.TRANSITIVE_LESS_THAN: 2,
    }.get(operation)
    if expected_count is not None and len(premises) != expected_count:
        return _reject(
            proposal,
            MathRejectionCode.WRONG_PREMISE_COUNT,
            f"{operation.value} requires {expected_count} premise(s)",
        )
    if operation is MathStepOperation.SUBSTITUTE and len(premises) < 2:
        return _reject(
            proposal,
            MathRejectionCode.WRONG_PREMISE_COUNT,
            "SUBSTITUTE requires a target claim and at least one equality claim",
        )

    try:
        if operation is MathStepOperation.EVALUATE_EXACT:
            if proposal.parameter is not None or proposal.substitutions:
                return _reject(
                    proposal,
                    MathRejectionCode.MALFORMED_PARAMETER,
                    "EVALUATE_EXACT accepts no parameter or substitutions",
                )
            if proposal.proposed_conclusion.variables:
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "EVALUATE_EXACT requires a closed statement",
                )
            valid, _, _ = evaluate_statement(proposal.proposed_conclusion, {})
            if not valid:
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "closed exact statement evaluates false",
                )
            return _accept(proposal, _canonical(proposal.proposed_conclusion), "exact_evaluation")

        if operation is MathStepOperation.SIMPLIFY_EXACT:
            expected = canonicalize_linear_statement(premises[0].statement)
            if not _same_statement(expected, proposal.proposed_conclusion):
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "proposed statement is not the exact linear normal form",
                )
            return _accept(proposal, expected, "exact_normalization")

        if operation in {
            MathStepOperation.ADD_BOTH_SIDES,
            MathStepOperation.SUBTRACT_BOTH_SIDES,
        }:
            if proposal.parameter is None or proposal.substitutions:
                return _reject(
                    proposal,
                    MathRejectionCode.MALFORMED_PARAMETER,
                    f"{operation.value} requires exactly one expression parameter",
                )
            parameter: MathExpression = proposal.parameter
            if operation is MathStepOperation.SUBTRACT_BOTH_SIDES:
                parameter = NegateExpression(parameter)
            premise = premises[0].statement
            expected = _canonical(
                MathStatement(
                    AddExpression((premise.left, parameter)),
                    premise.relation,
                    AddExpression((premise.right, parameter)),
                )
            )
            if not _same_statement(expected, proposal.proposed_conclusion):
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "the same expression was not applied to both sides",
                )
            return _accept(proposal, expected, "same_expression_both_sides")

        if operation in {
            MathStepOperation.MULTIPLY_BOTH_SIDES,
            MathStepOperation.DIVIDE_BOTH_SIDES,
        }:
            if proposal.parameter is None or proposal.substitutions:
                return _reject(
                    proposal,
                    MathRejectionCode.MALFORMED_PARAMETER,
                    f"{operation.value} requires exactly one exact scalar parameter",
                )
            expected, guards = _scaled_statement(
                premises[0].statement,
                proposal.parameter,
                divide=operation is MathStepOperation.DIVIDE_BOTH_SIDES,
            )
            if not _same_statement(expected, proposal.proposed_conclusion):
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "proposed scaling does not preserve the relation",
                )
            return _accept(proposal, expected, *guards)

        if operation is MathStepOperation.TRANSITIVE_EQUAL:
            expected = _transitive_equal(premises)
            if expected is None or not _same_statement(expected, proposal.proposed_conclusion):
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "equality middle terms do not form the proposed transitive conclusion",
                )
            return _accept(proposal, expected, "shared_middle_term")

        if operation is MathStepOperation.TRANSITIVE_LESS_THAN:
            expected = _transitive_less_than(premises)
            if expected is None or not _same_statement(expected, proposal.proposed_conclusion):
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "less-than middle terms do not form the proposed transitive conclusion",
                )
            return _accept(proposal, expected, "shared_middle_term")

        if operation is MathStepOperation.SUBSTITUTE:
            substitutions = dict(proposal.substitutions)
            if proposal.parameter is not None or not substitutions:
                return _reject(
                    proposal,
                    MathRejectionCode.MALFORMED_PARAMETER,
                    "SUBSTITUTE requires one or more typed substitutions and no scalar parameter",
                )
            target = premises[0].statement
            equality_claims = premises[1:]
            for variable, replacement in substitutions.items():
                if not _substitution_is_supported(variable, replacement, equality_claims):
                    return _reject(
                        proposal,
                        MathRejectionCode.INVALID_TRANSFORMATION,
                        f"no cited equality supports substitution for {variable}",
                    )
            expected = _canonical(substitute_statement(target, substitutions))
            if not _same_statement(expected, proposal.proposed_conclusion):
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "proposed conclusion does not match simultaneous substitution",
                )
            return _accept(proposal, expected, "cited_equality_substitution")

        if operation is MathStepOperation.VERIFY_LINEAR_SOLUTION:
            if proposal.parameter is not None or proposal.substitutions:
                return _reject(
                    proposal,
                    MathRejectionCode.MALFORMED_PARAMETER,
                    "VERIFY_LINEAR_SOLUTION accepts no parameter or substitutions",
                )
            solution = _linear_solution(premises[0].statement, proposal.proposed_conclusion)
            if solution is None:
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "proposed conclusion is not one exact solution binding",
                )
            variable, value = solution
            valid, _, _ = evaluate_statement(
                premises[0].statement,
                {variable: value},
            )
            if not valid:
                return _reject(
                    proposal,
                    MathRejectionCode.INVALID_TRANSFORMATION,
                    "substituting the proposed value does not satisfy the original equation",
                )
            expected = _canonical(proposal.proposed_conclusion)
            return _accept(proposal, expected, "exact_solution_substitution")

        return _reject(
            proposal,
            MathRejectionCode.NEEDS_CAPABILITY,
            f"unsupported math operation: {operation.value}",
        )
    except MathGuardError as exc:
        return _reject(proposal, MathRejectionCode.UNDISCHARGED_GUARD, str(exc))
    except MathCapabilityError as exc:
        return _reject(proposal, MathRejectionCode.NEEDS_CAPABILITY, str(exc))
    except MathContractError as exc:
        return _reject(proposal, MathRejectionCode.INVALID_TRANSFORMATION, str(exc))


def check_math_step(
    proposal: MathStepProposal,
    claims: Mapping[str, MathClaim] | Iterable[MathClaim],
    derivations: Mapping[
        str, tuple[MathStepProposal, MathStepReceipt]
    ] | None = None,
) -> MathStepReceipt:
    """Public fail-closed entry point with a fresh derivation-check budget."""

    return _check_math_step(
        proposal,
        claims,
        derivations,
        _validating_receipts=frozenset(),
        _remaining_rechecks=[MATH_MAX_RECEIPT_RECHECKS],
    )


def verify_math_receipt(
    proposal: MathStepProposal,
    claims: Mapping[str, MathClaim] | Iterable[MathClaim],
    receipt: MathStepReceipt,
    derivations: Mapping[
        str, tuple[MathStepProposal, MathStepReceipt]
    ] | None = None,
) -> bool:
    """Independently rebuild a receipt and require byte-identical content."""

    if not isinstance(receipt, MathStepReceipt):
        return False
    return check_math_step(proposal, claims, derivations).to_dict() == receipt.to_dict()


def issue_checked_math_claim(
    *,
    proposal: MathStepProposal,
    claims: Mapping[str, MathClaim] | Iterable[MathClaim],
    receipt: MathStepReceipt,
    status: MathClaimStatus,
    derivations: Mapping[
        str, tuple[MathStepProposal, MathStepReceipt]
    ] | None = None,
    assumption_claim_ids: Iterable[str] = (),
    provenance: Iterable[Provenance] = (),
) -> MathClaim:
    """Issue a checked-status claim only after semantic receipt re-execution."""

    if status not in {MathClaimStatus.DERIVED, MathClaimStatus.VERIFIED}:
        raise MathContractError("checked claim issuance requires DERIVED or VERIFIED status")
    if (
        status is MathClaimStatus.VERIFIED
        and proposal.operation
        not in {
            MathStepOperation.EVALUATE_EXACT,
            MathStepOperation.VERIFY_LINEAR_SOLUTION,
        }
    ):
        raise MathContractError(
            "VERIFIED status requires an exact evaluation or final linear-solution rule"
        )
    claim_source: Mapping[str, MathClaim] | tuple[MathClaim, ...]
    claim_source = claims if isinstance(claims, Mapping) else tuple(claims)
    if not verify_math_receipt(proposal, claim_source, receipt, derivations):
        raise MathContractError("receipt failed semantic re-execution")
    if not receipt.accepted or receipt.reconstructed_conclusion is None:
        raise MathContractError("rejected receipt cannot issue a checked claim")
    claim_map = (
        dict(claim_source)
        if isinstance(claim_source, Mapping)
        else {claim.claim_id: claim for claim in claim_source}
    )
    expected_assumptions: set[str] = set()
    for premise_id in proposal.premise_claim_ids:
        premise = claim_map[premise_id]
        expected_assumptions.update(premise.assumption_claim_ids)
        if premise.status is MathClaimStatus.ASSUMED:
            expected_assumptions.add(premise.claim_id)
    supplied_assumptions = tuple(sorted(set(assumption_claim_ids)))
    if supplied_assumptions != tuple(sorted(expected_assumptions)):
        raise MathContractError(
            "checked claim assumption closure must match its receipt premises"
        )
    return MathClaim._from_checked_receipt(
        receipt=receipt,
        status=status,
        assumption_claim_ids=supplied_assumptions,
        provenance=provenance,
    )
