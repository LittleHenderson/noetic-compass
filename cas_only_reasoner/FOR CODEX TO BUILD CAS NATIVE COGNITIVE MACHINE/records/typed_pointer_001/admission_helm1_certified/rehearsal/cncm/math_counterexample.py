"""Deterministic bounded-integer counterexample search for CAS-Math."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Iterator, Mapping

from .canonical import digest
from .math_model import (
    CounterexampleBounds,
    ExactRational,
    MATH_CHECKER_VERSION,
    MATH_THEORY_ID,
    MathContractError,
    MathGuardError,
    MathStatement,
)
from .math_normalize import evaluate_statement
from .verification import VerificationReport


class CounterexampleStatus(str, Enum):
    FOUND = "FOUND"
    NONE_WITHIN_BOUNDS = "NONE_WITHIN_BOUNDS"
    NEEDS_GUARD = "NEEDS_GUARD"
    UNSUPPORTED_EXPRESSION = "UNSUPPORTED_EXPRESSION"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class CounterexampleResult:
    schema_version: str
    status: CounterexampleStatus
    statement: MathStatement
    guards: tuple[MathStatement, ...]
    bounds: tuple[CounterexampleBounds, ...]
    tested_assignments: int
    max_assignments: int
    assignment: tuple[tuple[str, int], ...]
    exact_left: ExactRational | None
    exact_right: ExactRational | None
    theory_id: str
    checker_version: str
    detail: str
    result_digest: str

    @classmethod
    def create(
        cls,
        *,
        status: CounterexampleStatus,
        statement: MathStatement,
        guards: Iterable[MathStatement],
        bounds: Iterable[CounterexampleBounds],
        tested_assignments: int,
        max_assignments: int,
        assignment: Iterable[tuple[str, int]] = (),
        exact_left: ExactRational | None = None,
        exact_right: ExactRational | None = None,
        detail: str = "",
        theory_id: str = MATH_THEORY_ID,
    ) -> "CounterexampleResult":
        if theory_id != MATH_THEORY_ID:
            raise MathContractError(
                f"CAS-Math v0.1 only admits theory_id {MATH_THEORY_ID!r}"
            )
        if not isinstance(status, CounterexampleStatus):
            raise MathContractError("counterexample status must be typed")
        guard_values = tuple(guards)
        bound_values = tuple(bounds)
        assignment_values = tuple(assignment)
        body = {
            "schema_version": "cncm.math-counterexample/0.1",
            "status": status.value,
            "statement": statement.to_dict(),
            "guards": [item.to_dict() for item in guard_values],
            "bounds": [item.to_dict() for item in bound_values],
            "tested_assignments": tested_assignments,
            "max_assignments": max_assignments,
            "assignment": [[name, value] for name, value in assignment_values],
            "exact_left": exact_left.to_dict() if exact_left is not None else None,
            "exact_right": exact_right.to_dict() if exact_right is not None else None,
            "theory_id": theory_id,
            "checker_version": MATH_CHECKER_VERSION,
            "detail": detail,
        }
        return cls(
            schema_version="cncm.math-counterexample/0.1",
            status=status,
            statement=statement,
            guards=guard_values,
            bounds=bound_values,
            tested_assignments=tested_assignments,
            max_assignments=max_assignments,
            assignment=assignment_values,
            exact_left=exact_left,
            exact_right=exact_right,
            theory_id=theory_id,
            checker_version=MATH_CHECKER_VERSION,
            detail=detail,
            result_digest=digest(body),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "statement": self.statement.to_dict(),
            "guards": [item.to_dict() for item in self.guards],
            "bounds": [item.to_dict() for item in self.bounds],
            "tested_assignments": self.tested_assignments,
            "max_assignments": self.max_assignments,
            "assignment": [[name, value] for name, value in self.assignment],
            "exact_left": self.exact_left.to_dict() if self.exact_left is not None else None,
            "exact_right": self.exact_right.to_dict() if self.exact_right is not None else None,
            "theory_id": self.theory_id,
            "checker_version": self.checker_version,
            "detail": self.detail,
            "result_digest": self.result_digest,
        }


def _ordered_values(bound: CounterexampleBounds) -> Iterator[int]:
    """Yield the frozen order without materializing a potentially huge range."""

    emitted: set[int] = set()
    for candidate in (0, bound.lower, bound.upper):
        if bound.lower <= candidate <= bound.upper and candidate not in emitted:
            emitted.add(candidate)
            yield candidate

    if bound.lower <= 0 <= bound.upper:
        first_magnitude = 0
    else:
        first_magnitude = min(abs(bound.lower), abs(bound.upper))
    last_magnitude = max(abs(bound.lower), abs(bound.upper))
    for magnitude in range(first_magnitude, last_magnitude + 1):
        candidates = (0,) if magnitude == 0 else (-magnitude, magnitude)
        for candidate in candidates:
            if (
                bound.lower <= candidate <= bound.upper
                and candidate not in emitted
            ):
                emitted.add(candidate)
                yield candidate


def _ordered_assignments(
    bounds: tuple[CounterexampleBounds, ...],
) -> Iterator[tuple[int, ...]]:
    """Lazy Cartesian product that replays each bounded domain as needed."""

    prefix: list[int] = []

    def walk(index: int) -> Iterator[tuple[int, ...]]:
        if index == len(bounds):
            yield tuple(prefix)
            return
        for value in _ordered_values(bounds[index]):
            prefix.append(value)
            yield from walk(index + 1)
            prefix.pop()

    yield from walk(0)


def search_math_counterexample(
    statement: MathStatement,
    bounds: Iterable[CounterexampleBounds],
    *,
    guards: Iterable[MathStatement] = (),
    max_assignments: int = 4096,
    theory_id: str = MATH_THEORY_ID,
) -> CounterexampleResult:
    """Find the first exact falsifying assignment in a frozen order."""

    if theory_id != MATH_THEORY_ID:
        raise MathContractError(
            f"CAS-Math v0.1 only admits theory_id {MATH_THEORY_ID!r}"
        )
    if not isinstance(max_assignments, int) or isinstance(max_assignments, bool) or max_assignments < 1:
        raise MathContractError("max_assignments must be a positive integer")
    bound_values = tuple(bounds)
    guard_values = tuple(guards)
    if not 1 <= len(bound_values) <= 3:
        raise MathContractError("counterexample search requires one to three bounded variables")
    variables = tuple(item.variable for item in bound_values)
    if len(variables) != len(set(variables)):
        raise MathContractError("counterexample bounds require unique variables")
    required = set(statement.variables)
    for guard in guard_values:
        required.update(guard.variables)
    missing = required - set(variables)
    if missing:
        raise MathContractError(f"missing counterexample bounds for variables: {sorted(missing)}")

    tested = 0
    last_assignment: tuple[tuple[str, int], ...] = ()
    for values in _ordered_assignments(bound_values):
        if tested >= max_assignments:
            return CounterexampleResult.create(
                status=CounterexampleStatus.BUDGET_EXHAUSTED,
                statement=statement,
                guards=guard_values,
                bounds=bound_values,
                tested_assignments=tested,
                max_assignments=max_assignments,
                assignment=last_assignment,
                detail="assignment budget exhausted before the bounded domain was complete",
                theory_id=theory_id,
            )
        tested += 1
        last_assignment = tuple(zip(variables, values, strict=True))
        assignment = {name: ExactRational.from_int(value) for name, value in last_assignment}
        try:
            admitted = True
            for guard in guard_values:
                guard_holds, _, _ = evaluate_statement(guard, assignment)
                if not guard_holds:
                    admitted = False
                    break
            if not admitted:
                continue
            holds, exact_left, exact_right = evaluate_statement(statement, assignment)
        except MathGuardError as exc:
            return CounterexampleResult.create(
                status=CounterexampleStatus.NEEDS_GUARD,
                statement=statement,
                guards=guard_values,
                bounds=bound_values,
                tested_assignments=tested,
                max_assignments=max_assignments,
                assignment=last_assignment,
                detail=str(exc),
                theory_id=theory_id,
            )
        except MathContractError as exc:
            return CounterexampleResult.create(
                status=CounterexampleStatus.UNSUPPORTED_EXPRESSION,
                statement=statement,
                guards=guard_values,
                bounds=bound_values,
                tested_assignments=tested,
                max_assignments=max_assignments,
                assignment=last_assignment,
                detail=str(exc),
                theory_id=theory_id,
            )
        if not holds:
            return CounterexampleResult.create(
                status=CounterexampleStatus.FOUND,
                statement=statement,
                guards=guard_values,
                bounds=bound_values,
                tested_assignments=tested,
                max_assignments=max_assignments,
                assignment=last_assignment,
                exact_left=exact_left,
                exact_right=exact_right,
                detail="exact assignment falsifies the universal conjecture within the declared bounds",
                theory_id=theory_id,
            )

    return CounterexampleResult.create(
        status=CounterexampleStatus.NONE_WITHIN_BOUNDS,
        statement=statement,
        guards=guard_values,
        bounds=bound_values,
        tested_assignments=tested,
        max_assignments=max_assignments,
        detail="no falsifying assignment was found; this is not a proof",
        theory_id=theory_id,
    )


def verify_counterexample_result(bundle: Mapping[str, Any]) -> VerificationReport:
    """Re-execute a retained bounded search and require an exact bundle match."""

    try:
        required = {
            "schema_version",
            "status",
            "statement",
            "guards",
            "bounds",
            "tested_assignments",
            "max_assignments",
            "assignment",
            "exact_left",
            "exact_right",
            "theory_id",
            "checker_version",
            "detail",
            "result_digest",
        }
        if not isinstance(bundle, Mapping) or set(bundle) != required:
            raise MathContractError(
                "counterexample result fields do not match the frozen bundle shape"
            )
        retained_body = dict(bundle)
        retained_digest = retained_body.pop("result_digest")
        if retained_digest != digest(retained_body):
            raise MathContractError("counterexample result digest mismatch")
        if bundle["schema_version"] != "cncm.math-counterexample/0.1":
            raise MathContractError("unsupported counterexample schema version")
        if bundle["theory_id"] != MATH_THEORY_ID:
            raise MathContractError("counterexample theory identity mismatch")
        if bundle["checker_version"] != MATH_CHECKER_VERSION:
            raise MathContractError("counterexample checker identity mismatch")
        raw_guards = bundle["guards"]
        raw_bounds = bundle["bounds"]
        if not isinstance(raw_guards, list) or not isinstance(raw_bounds, list):
            raise MathContractError("counterexample guards and bounds must be arrays")
        statement = MathStatement.from_dict(bundle["statement"])
        guards = tuple(MathStatement.from_dict(item) for item in raw_guards)
        bounds = tuple(CounterexampleBounds.from_dict(item) for item in raw_bounds)
        max_assignments = bundle["max_assignments"]
        if (
            not isinstance(max_assignments, int)
            or isinstance(max_assignments, bool)
            or max_assignments < 1
        ):
            raise MathContractError("max_assignments must be a positive integer")
        rebuilt = search_math_counterexample(
            statement,
            bounds,
            guards=guards,
            max_assignments=max_assignments,
        ).to_dict()
        if rebuilt != dict(bundle):
            raise MathContractError(
                "semantic re-execution differs from retained counterexample result"
            )
    except (KeyError, MathContractError, TypeError, ValueError) as exc:
        return VerificationReport(
            False,
            (("counterexample_semantic_reexecution", False),),
            (str(exc),),
        )
    return VerificationReport(
        True,
        (("counterexample_semantic_reexecution", True),),
        (),
    )
