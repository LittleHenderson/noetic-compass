"""Exact evaluation, substitution, and linear normalization for CAS-Math."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .math_model import (
    AddExpression,
    DivideExpression,
    ExactRational,
    IntegerExpression,
    MathCapabilityError,
    MathContractError,
    MathExpression,
    MathGuardError,
    MathRelation,
    MathStatement,
    MultiplyExpression,
    NegateExpression,
    RationalExpression,
    VariableExpression,
)


ZERO = ExactRational(0)
ONE = ExactRational(1)


@dataclass(frozen=True, slots=True)
class LinearForm:
    """Canonical exact sum of variable coefficients plus one constant."""

    constant: ExactRational = ZERO
    coefficients: tuple[tuple[str, ExactRational], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.constant, ExactRational):
            raise MathContractError("LinearForm.constant must be exact")
        names = [name for name, _ in self.coefficients]
        if names != sorted(names) or len(names) != len(set(names)):
            raise MathContractError("LinearForm coefficients must be unique and sorted")
        if any(not isinstance(value, ExactRational) or value.is_zero for _, value in self.coefficients):
            raise MathContractError("LinearForm coefficients must be exact and nonzero")

    @classmethod
    def create(
        cls,
        constant: ExactRational = ZERO,
        coefficients: Mapping[str, ExactRational] | None = None,
    ) -> "LinearForm":
        normalized = tuple(
            sorted(
                (name, value)
                for name, value in (coefficients or {}).items()
                if not value.is_zero
            )
        )
        return cls(constant, normalized)

    @property
    def coefficient_map(self) -> dict[str, ExactRational]:
        return dict(self.coefficients)

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.coefficients)

    @property
    def is_constant(self) -> bool:
        return not self.coefficients

    def coefficient(self, variable: str) -> ExactRational:
        return self.coefficient_map.get(variable, ZERO)

    def __neg__(self) -> "LinearForm":
        return LinearForm.create(
            -self.constant,
            {name: -value for name, value in self.coefficients},
        )

    def __add__(self, other: "LinearForm") -> "LinearForm":
        coefficients = self.coefficient_map
        for name, value in other.coefficients:
            coefficients[name] = coefficients.get(name, ZERO) + value
        return LinearForm.create(self.constant + other.constant, coefficients)

    def __sub__(self, other: "LinearForm") -> "LinearForm":
        return self + (-other)

    def scale(self, scalar: ExactRational) -> "LinearForm":
        return LinearForm.create(
            self.constant * scalar,
            {name: value * scalar for name, value in self.coefficients},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "constant": self.constant.to_dict(),
            "coefficients": [
                [name, coefficient.to_dict()] for name, coefficient in self.coefficients
            ],
        }


def rational_expression(value: ExactRational) -> MathExpression:
    if value.is_integer:
        return IntegerExpression(value.numerator)
    return RationalExpression(value)


def normalize_linear(expression: MathExpression) -> LinearForm:
    """Normalize an admitted expression or fail closed on nonlinear content."""

    if isinstance(expression, IntegerExpression):
        return LinearForm(ExactRational.from_int(expression.value))
    if isinstance(expression, RationalExpression):
        return LinearForm(expression.value)
    if isinstance(expression, VariableExpression):
        return LinearForm.create(ZERO, {expression.name: ONE})
    if isinstance(expression, NegateExpression):
        return -normalize_linear(expression.operand)
    if isinstance(expression, AddExpression):
        result = LinearForm()
        for term in expression.terms:
            result = result + normalize_linear(term)
        return result
    if isinstance(expression, MultiplyExpression):
        scalar = ONE
        variable_form: LinearForm | None = None
        for factor in expression.factors:
            normalized = normalize_linear(factor)
            if normalized.is_constant:
                scalar = scalar * normalized.constant
                continue
            if variable_form is not None:
                raise MathCapabilityError(
                    "products containing more than one variable-bearing factor are outside CAS-Math v0.1"
                )
            variable_form = normalized
        if variable_form is None:
            return LinearForm(scalar)
        return variable_form.scale(scalar)
    if isinstance(expression, DivideExpression):
        numerator = normalize_linear(expression.numerator)
        denominator = normalize_linear(expression.denominator)
        if not denominator.is_constant:
            raise MathCapabilityError(
                "division by a variable-bearing expression is outside CAS-Math v0.1"
            )
        if denominator.constant.is_zero:
            raise MathGuardError("division by zero is not admissible")
        return numerator.scale(ONE / denominator.constant)
    raise MathContractError("unsupported CAS-Math expression")


def expression_from_linear(form: LinearForm) -> MathExpression:
    terms: list[MathExpression] = []
    for variable, coefficient in form.coefficients:
        symbol = VariableExpression(variable)
        if coefficient == ONE:
            term: MathExpression = symbol
        elif coefficient == -ONE:
            term = NegateExpression(symbol)
        else:
            term = MultiplyExpression((rational_expression(coefficient), symbol))
        terms.append(term)
    if not form.constant.is_zero or not terms:
        terms.append(rational_expression(form.constant))
    if len(terms) == 1:
        return terms[0]
    return AddExpression(tuple(terms))


def canonicalize_linear_statement(statement: MathStatement) -> MathStatement:
    return MathStatement(
        expression_from_linear(normalize_linear(statement.left)),
        statement.relation,
        expression_from_linear(normalize_linear(statement.right)),
    )


def same_linear_expression(left: MathExpression, right: MathExpression) -> bool:
    return normalize_linear(left) == normalize_linear(right)


def same_linear_statement(left: MathStatement, right: MathStatement) -> bool:
    return (
        left.relation is right.relation
        and same_linear_expression(left.left, right.left)
        and same_linear_expression(left.right, right.right)
    )


def evaluate_expression(
    expression: MathExpression,
    assignment: Mapping[str, ExactRational | int],
) -> ExactRational:
    """Evaluate all MVP arithmetic exactly, including nonlinear products."""

    if isinstance(expression, IntegerExpression):
        return ExactRational.from_int(expression.value)
    if isinstance(expression, RationalExpression):
        return expression.value
    if isinstance(expression, VariableExpression):
        if expression.name not in assignment:
            raise MathContractError(f"missing assignment for variable {expression.name}")
        value = assignment[expression.name]
        return value if isinstance(value, ExactRational) else ExactRational.from_int(value)
    if isinstance(expression, NegateExpression):
        return -evaluate_expression(expression.operand, assignment)
    if isinstance(expression, AddExpression):
        result = ZERO
        for term in expression.terms:
            result = result + evaluate_expression(term, assignment)
        return result
    if isinstance(expression, MultiplyExpression):
        result = ONE
        for factor in expression.factors:
            result = result * evaluate_expression(factor, assignment)
        return result
    if isinstance(expression, DivideExpression):
        numerator = evaluate_expression(expression.numerator, assignment)
        denominator = evaluate_expression(expression.denominator, assignment)
        return numerator / denominator
    raise MathContractError("unsupported CAS-Math expression")


def evaluate_statement(
    statement: MathStatement,
    assignment: Mapping[str, ExactRational | int],
) -> tuple[bool, ExactRational, ExactRational]:
    left = evaluate_expression(statement.left, assignment)
    right = evaluate_expression(statement.right, assignment)
    if statement.relation is MathRelation.EQUAL:
        return left == right, left, right
    if statement.relation is MathRelation.LESS_THAN:
        return left < right, left, right
    raise MathContractError("unsupported math relation")


def substitute_expression(
    expression: MathExpression,
    substitutions: Mapping[str, MathExpression],
) -> MathExpression:
    if isinstance(expression, VariableExpression):
        return substitutions.get(expression.name, expression)
    if isinstance(expression, (IntegerExpression, RationalExpression)):
        return expression
    if isinstance(expression, NegateExpression):
        return NegateExpression(substitute_expression(expression.operand, substitutions))
    if isinstance(expression, AddExpression):
        return AddExpression(
            tuple(substitute_expression(term, substitutions) for term in expression.terms)
        )
    if isinstance(expression, MultiplyExpression):
        return MultiplyExpression(
            tuple(substitute_expression(factor, substitutions) for factor in expression.factors)
        )
    if isinstance(expression, DivideExpression):
        return DivideExpression(
            substitute_expression(expression.numerator, substitutions),
            substitute_expression(expression.denominator, substitutions),
        )
    raise MathContractError("unsupported CAS-Math expression")


def substitute_statement(
    statement: MathStatement,
    substitutions: Mapping[str, MathExpression],
) -> MathStatement:
    return MathStatement(
        substitute_expression(statement.left, substitutions),
        statement.relation,
        substitute_expression(statement.right, substitutions),
    )
