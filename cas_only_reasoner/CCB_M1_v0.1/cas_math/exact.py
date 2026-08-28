"""Exact arithmetic: rational numbers only, never floats.

1/3 stays 1/3. The module contains no floating-point operations; a
conformance test asserts exactly that.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Tuple


def parse_q(text: str) -> Fraction:
    """Parse '5', '-3', '1/3', '-2/7' into an exact Fraction."""
    text = str(text).strip()
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return Fraction(int(numerator), int(denominator))
    return Fraction(int(text))


def q_str(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def add(a: Fraction, b: Fraction) -> Fraction:
    return a + b


def sub(a: Fraction, b: Fraction) -> Fraction:
    return a - b


def mul(a: Fraction, b: Fraction) -> Fraction:
    return a * b


def div(a: Fraction, b: Fraction) -> Fraction:
    if b == 0:
        raise ZeroDivisionError("exact division by zero")
    return a / b


def pow_int(a: Fraction, n: int) -> Fraction:
    if n < 0:
        return Fraction(1) / (a ** (-n))
    return a ** n


def compare(a: Fraction, b: Fraction) -> str:
    """Exact comparison: 'lt', 'eq', or 'gt'."""
    if a < b:
        return "lt"
    if a > b:
        return "gt"
    return "eq"


def relation_holds(relation: str, a: Fraction, b: Fraction) -> bool:
    cmp = compare(a, b)
    if relation == "equal":
        return cmp == "eq"
    if relation == "less_than":
        return cmp == "lt"
    if relation == "greater_than":
        return cmp == "gt"
    raise ValueError(f"unknown relation {relation}")
