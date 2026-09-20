"""Dependency-free parser for the frozen CAS-Math v0.1 notation grammar."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .math_model import (
    AddExpression,
    DivideExpression,
    ExactRational,
    IntegerExpression,
    MathBudgetError,
    MathContractError,
    MathExpression,
    MathParseLimits,
    MathRelation,
    MathStatement,
    MultiplyExpression,
    NegateExpression,
    RationalExpression,
    VariableExpression,
)


_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[()+\-*/=<]")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class _Token:
    value: str
    offset: int


def _tokenize(text: str, limits: MathParseLimits) -> tuple[_Token, ...]:
    if not isinstance(text, str):
        raise MathContractError("math notation must be a string")
    if not text:
        raise MathContractError("math notation must not be empty")
    if len(text) > limits.max_characters:
        raise MathBudgetError("math notation character budget exhausted")
    if not text.isascii():
        raise MathContractError("CAS-Math v0.1 notation is ASCII only")

    tokens: list[_Token] = []
    cursor = 0
    for match in _TOKEN.finditer(text):
        gap = text[cursor : match.start()]
        if gap and not gap.isspace():
            raise MathContractError(
                f"unsupported token at character {cursor}: {gap[0]!r}"
            )
        value = match.group(0)
        if value.isdigit() and len(value) > limits.max_integer_digits:
            raise MathBudgetError("integer digit budget exhausted")
        tokens.append(_Token(value, match.start()))
        if len(tokens) > limits.max_tokens:
            raise MathBudgetError("math notation token budget exhausted")
        cursor = match.end()
    suffix = text[cursor:]
    if suffix and not suffix.isspace():
        raise MathContractError(
            f"unsupported token at character {cursor}: {suffix[0]!r}"
        )
    if not tokens:
        raise MathContractError("math notation contains no tokens")
    return tuple(tokens)


class _Parser:
    def __init__(
        self,
        text: str,
        declared_variables: Iterable[str] | None,
        limits: MathParseLimits,
    ) -> None:
        self.tokens = _tokenize(text, limits)
        self.position = 0
        self.limits = limits
        self.nodes = 0
        self.depth = 0
        if declared_variables is None:
            self.declared_variables: frozenset[str] | None = None
        else:
            declared = tuple(declared_variables)
            if any(not isinstance(item, str) or not _IDENTIFIER.fullmatch(item) for item in declared):
                raise MathContractError("declared variables must be ASCII identifiers")
            if len(declared) != len(set(declared)):
                raise MathContractError("declared variables must be unique")
            self.declared_variables = frozenset(declared)

    def _node(self, value: MathExpression) -> MathExpression:
        self.nodes += 1
        if self.nodes > self.limits.max_nodes:
            raise MathBudgetError("math expression node budget exhausted")
        return value

    def _peek(self) -> str | None:
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position].value

    def _take(self) -> _Token:
        if self.position >= len(self.tokens):
            raise MathContractError("unexpected end of math notation")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def _expect(self, expected: str) -> None:
        token = self._take()
        if token.value != expected:
            raise MathContractError(
                f"expected {expected!r} at character {token.offset}, got {token.value!r}"
            )

    def _enter(self) -> None:
        self.depth += 1
        if self.depth > self.limits.max_depth:
            raise MathBudgetError("math expression depth budget exhausted")

    def _leave(self) -> None:
        self.depth -= 1

    def parse_expression(self) -> MathExpression:
        expression = self._sum()
        if self._peek() is not None:
            token = self.tokens[self.position]
            raise MathContractError(
                f"unexpected token at character {token.offset}: {token.value!r}"
            )
        return expression

    def parse_statement(self) -> MathStatement:
        left = self._sum()
        relation_token = self._take()
        if relation_token.value == "=":
            relation = MathRelation.EQUAL
        elif relation_token.value == "<":
            relation = MathRelation.LESS_THAN
        else:
            raise MathContractError(
                f"expected one top-level relation at character {relation_token.offset}"
            )
        right = self._sum()
        if self._peek() is not None:
            token = self.tokens[self.position]
            raise MathContractError(
                f"unexpected token at character {token.offset}: {token.value!r}; "
                "chained relations are unsupported"
            )
        return MathStatement(left, relation, right)

    def _sum(self) -> MathExpression:
        left = self._product()
        terms: list[MathExpression] = [left]
        while self._peek() in {"+", "-"}:
            operation = self._take().value
            right = self._product()
            if operation == "-":
                right = self._node(NegateExpression(right))
            terms.append(right)
        if len(terms) == 1:
            return left
        return self._node(AddExpression(tuple(terms)))

    def _product(self) -> MathExpression:
        left = self._unary()
        factors: list[MathExpression] = [left]
        while self._peek() in {"*", "/"}:
            operation = self._take().value
            right = self._unary()
            if operation == "/":
                combined = self._exact_division(factors[0], right) if len(factors) == 1 else None
                if combined is not None:
                    factors[0] = combined
                    continue
                numerator = factors[0] if len(factors) == 1 else self._node(MultiplyExpression(tuple(factors)))
                left = self._node(DivideExpression(numerator, right))
                factors = [left]
            else:
                factors.append(right)
        if len(factors) == 1:
            return factors[0]
        return self._node(MultiplyExpression(tuple(factors)))

    @staticmethod
    def _constant(expression: MathExpression) -> ExactRational | None:
        if isinstance(expression, IntegerExpression):
            return ExactRational.from_int(expression.value)
        if isinstance(expression, RationalExpression):
            return expression.value
        return None

    def _exact_division(
        self,
        left: MathExpression,
        right: MathExpression,
    ) -> MathExpression | None:
        numerator = self._constant(left)
        denominator = self._constant(right)
        if numerator is None or denominator is None:
            return None
        value = numerator / denominator
        if value.is_integer:
            return self._node(IntegerExpression(value.numerator))
        return self._node(RationalExpression(value))

    def _unary(self) -> MathExpression:
        token = self._peek()
        if token == "+":
            self._take()
            self._enter()
            try:
                return self._unary()
            finally:
                self._leave()
        if token == "-":
            self._take()
            self._enter()
            try:
                operand = self._unary()
            finally:
                self._leave()
            if isinstance(operand, IntegerExpression):
                return self._node(IntegerExpression(-operand.value))
            if isinstance(operand, RationalExpression):
                return self._node(RationalExpression(-operand.value))
            return self._node(NegateExpression(operand))
        return self._primary()

    def _primary(self) -> MathExpression:
        token = self._take()
        if token.value == "(":
            self._enter()
            try:
                expression = self._sum()
                self._expect(")")
            finally:
                self._leave()
            return expression
        if token.value.isdigit():
            return self._node(IntegerExpression(int(token.value)))
        if _IDENTIFIER.fullmatch(token.value):
            if (
                self.declared_variables is not None
                and token.value not in self.declared_variables
            ):
                raise MathContractError(f"undeclared variable: {token.value}")
            return self._node(VariableExpression(token.value))
        raise MathContractError(
            f"expected integer, variable, or '(' at character {token.offset}"
        )


def parse_math_expression(
    text: str,
    *,
    declared_variables: Iterable[str] | None = None,
    limits: MathParseLimits = MathParseLimits(),
) -> MathExpression:
    """Parse one exact CAS-Math expression and require complete consumption."""

    return _Parser(text, declared_variables, limits).parse_expression()


def parse_math_statement(
    text: str,
    *,
    declared_variables: Iterable[str] | None = None,
    limits: MathParseLimits = MathParseLimits(),
) -> MathStatement:
    """Parse one equality or less-than statement with exactly one relation."""

    return _Parser(text, declared_variables, limits).parse_statement()
