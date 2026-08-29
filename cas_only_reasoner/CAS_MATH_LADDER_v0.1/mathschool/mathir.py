"""The deterministic bridge between teacher-writable infix text and
the CCB-M1 CAS-Math IR. No model anywhere: a recursive-descent reader
and an exact renderer. The FORMAL channel of every lesson passes
through here into the IR before anything is checked.

Grammar (v0.1):
    expr    := term (('+'|'-') term)*
    term    := factor ('*' factor)*
    factor  := atom ('^' INT)?
    atom    := NUMBER | NAME | '(' expr ')' | '-' atom
    NUMBER  := integer or exact fraction 'p/q'
Equations: 'LHS = RHS' (exactly one '=').
"""

from __future__ import annotations

import os
import re
import sys
from fractions import Fraction
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_LANE = os.path.dirname(os.path.dirname(_HERE))
_M1 = os.path.join(_LANE, "CCB_M1_v0.1")
if _M1 not in sys.path:
    sys.path.insert(0, _M1)

from cas_math.expr import (Add, Mul, Neg, Num, Pow, Var,  # noqa: E402
                           canonical, equal, eval_at, from_json,
                           to_json, variables)

__all__ = ["Add", "Mul", "Neg", "Num", "Pow", "Var", "canonical",
           "equal", "eval_at", "from_json", "to_json", "variables",
           "parse_expr", "parse_equation", "render_expr",
           "MathParseError", "NUMBER_WORDS", "number_to_words"]


class MathParseError(Exception):
    pass


_TOKEN = re.compile(r"\s*(\d+/\d+|\d+|[a-zA-Z]\w*|[-+*^()=])")


def _tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    index = 0
    while index < len(text):
        match = _TOKEN.match(text, index)
        if match is None:
            if text[index:].strip():
                raise MathParseError(
                    f"cannot read {text[index:index + 10]!r}")
            break
        tokens.append(match.group(1))
        index = match.end()
    return tokens


class _Reader:
    def __init__(self, tokens: List[str]) -> None:
        self.tokens = tokens
        self.index = 0

    def peek(self):
        return (self.tokens[self.index]
                if self.index < len(self.tokens) else None)

    def take(self):
        token = self.peek()
        self.index += 1
        return token

    def expr(self):
        terms = [self.term()]
        signs = [1]
        while self.peek() in ("+", "-"):
            signs.append(1 if self.take() == "+" else -1)
            terms.append(self.term())
        parts = [t if s == 1 else Neg(t)
                 for t, s in zip(terms, signs)]
        return parts[0] if len(parts) == 1 else Add(tuple(parts))

    def term(self):
        factors = [self.factor()]
        while self.peek() == "*":
            self.take()
            factors.append(self.factor())
        return factors[0] if len(factors) == 1 else Mul(tuple(factors))

    def factor(self):
        atom = self.atom()
        if self.peek() == "^":
            self.take()
            exponent = self.take()
            if exponent is None or not exponent.isdigit():
                raise MathParseError("'^' needs an integer exponent")
            return Pow(atom, int(exponent))
        return atom

    def atom(self):
        token = self.take()
        if token is None:
            raise MathParseError("expression ended early")
        if token == "-":
            return Neg(self.atom())
        if token == "(":
            inner = self.expr()
            if self.take() != ")":
                raise MathParseError("missing ')'")
            return inner
        if re.fullmatch(r"\d+/\d+", token):
            p, q = token.split("/")
            if int(q) == 0:
                raise MathParseError("division by zero in a literal")
            return Num(Fraction(int(p), int(q)))
        if token.isdigit():
            return Num(Fraction(int(token)))
        if re.fullmatch(r"[a-zA-Z]\w*", token):
            return Var(token)
        raise MathParseError(f"unexpected {token!r}")


def parse_expr(text: str):
    reader = _Reader(_tokenize(text))
    result = reader.expr()
    if reader.peek() is not None:
        raise MathParseError(f"trailing {reader.peek()!r} in {text!r}")
    return result


def parse_equation(text: str) -> Tuple[object, object]:
    if text.count("=") != 1:
        raise MathParseError("an equation needs exactly one '='")
    lhs, rhs = text.split("=")
    return parse_expr(lhs), parse_expr(rhs)


def render_expr(expr) -> str:
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, Num):
        q = expr.q
        return (str(q.numerator) if q.denominator == 1
                else f"{q.numerator}/{q.denominator}")
    if isinstance(expr, Neg):
        return f"-{render_expr(expr.operand)}"
    if isinstance(expr, Add):
        return "(" + " + ".join(render_expr(t)
                                for t in expr.terms) + ")"
    if isinstance(expr, Mul):
        return "(" + " * ".join(render_expr(f)
                                for f in expr.factors) + ")"
    if isinstance(expr, Pow):
        return f"{render_expr(expr.base)}^{expr.exp}"
    raise MathParseError(f"cannot render {expr!r}")


NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
}
_WORDS_BY_VALUE = {v: k for k, v in NUMBER_WORDS.items()}


def number_to_words(q: Fraction) -> str:
    """Small exact numbers render as words; everything else renders
    as exact digits - never an approximation."""
    def one(n: int) -> str:
        if n < 0:
            return "minus " + one(-n)
        return _WORDS_BY_VALUE.get(n, str(n))

    if q.denominator == 1:
        return one(q.numerator)
    return f"{one(q.numerator)} over {one(q.denominator)}"
