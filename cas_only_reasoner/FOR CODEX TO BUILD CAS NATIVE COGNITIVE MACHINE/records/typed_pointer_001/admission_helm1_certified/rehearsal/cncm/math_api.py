"""Stable host-facing CAS-Math v0.1 API."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .math_counterexample import (
    CounterexampleResult,
    search_math_counterexample,
    verify_counterexample_result,
)
from .math_engine import MathRunResult, solve_linear_equation, verify_math_result
from .math_kernel import check_math_step, verify_math_receipt
from .math_model import (
    CounterexampleBounds,
    MathClaim,
    MathContractError,
    MathParseLimits,
    MathStepProposal,
    MathStepReceipt,
)
from .math_parser import parse_math_expression, parse_math_statement
from .verification import VerificationReport


def solve_math(
    notation: str,
    variable: str,
    *,
    limits: MathParseLimits = MathParseLimits(),
) -> MathRunResult:
    return solve_linear_equation(notation, variable, limits=limits)


def find_math_counterexample(
    notation: str,
    bounds: Iterable[CounterexampleBounds | Mapping[str, Any]],
    *,
    guards: Iterable[str] = (),
    max_assignments: int = 4096,
) -> CounterexampleResult:
    normalized_bounds = tuple(
        item if isinstance(item, CounterexampleBounds) else CounterexampleBounds.from_dict(item)
        for item in bounds
    )
    variables = tuple(item.variable for item in normalized_bounds)
    statement = parse_math_statement(notation, declared_variables=variables)
    guard_statements = tuple(
        parse_math_statement(item, declared_variables=variables) for item in guards
    )
    return search_math_counterexample(
        statement,
        normalized_bounds,
        guards=guard_statements,
        max_assignments=max_assignments,
    )


def validate_math_notation(
    notation: str,
    *,
    declared_variables: Iterable[str] | None = None,
) -> VerificationReport:
    try:
        parse_math_statement(notation, declared_variables=declared_variables)
    except (MathContractError, TypeError, ValueError) as exc:
        return VerificationReport(False, (("math_notation", False),), (str(exc),))
    return VerificationReport(True, (("math_notation", True),), ())


__all__ = [
    "check_math_step",
    "find_math_counterexample",
    "parse_math_expression",
    "parse_math_statement",
    "solve_math",
    "validate_math_notation",
    "verify_math_receipt",
    "verify_math_result",
    "verify_counterexample_result",
    "MathClaim",
    "MathStepProposal",
    "MathStepReceipt",
]
