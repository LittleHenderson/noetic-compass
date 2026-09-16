"""Bounded numeric grounding and independent checks for nested equations.

This module never solves for the equation variable. Dependency values must be
bound to completed child executions by the caller's kernel. A CHECKED report
establishes numeric substitution only, not source authority or permission to
install, recall, or commit anything.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd
import re

from .canonical import digest
from .model import ContractError


INPUT_BITS = 128
INTERMEDIATE_BITS = 512
REPORT_SCHEMA = "cncm.nested-equation-verification/0.3"
_INTEGER = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")
_DENOMINATOR = re.compile(r"[1-9][0-9]*\Z")
_INTERMEDIATE_MAX = (1 << INTERMEDIATE_BITS) - 1


def _require(condition, detail):
    if not condition:
        raise ContractError(detail)


def _parse_rational(value, bits, label):
    """Bound text before int conversion, then require a reduced canonical form."""
    digits = len(str((1 << bits) - 1))
    _require(type(value) is str and 1 <= len(value) <= 2 * digits + 2,
             f"{label}: bounded canonical rational text required")
    pieces = value.split("/")
    _require(len(pieces) in (1, 2), f"{label}: rational form invalid")
    numerator_text = pieces[0]
    denominator_text = pieces[1] if len(pieces) == 2 else "1"
    _require(len(numerator_text.removeprefix("-")) <= digits
             and len(denominator_text) <= digits
             and _INTEGER.fullmatch(numerator_text) is not None
             and _DENOMINATOR.fullmatch(denominator_text) is not None,
             f"{label}: rational spelling invalid")
    numerator, denominator = int(numerator_text), int(denominator_text)
    _require(abs(numerator).bit_length() <= bits and denominator.bit_length() <= bits,
             f"{label}: rational bit bound exceeded")
    _require(gcd(abs(numerator), denominator) == 1
             and (len(pieces) == 1 or denominator != 1),
             f"{label}: rational must be canonical and reduced")
    return Fraction(numerator, denominator)


def _text(value):
    return (str(value.numerator) if value.denominator == 1
            else f"{value.numerator}/{value.denominator}")


def _multiply_checked(left, right):
    """The division comparison happens before allocation of the product."""
    if not left or not right:
        return 0
    _require(abs(left) <= _INTERMEDIATE_MAX // abs(right),
             "nested arithmetic intermediate bit bound exceeded")
    return left * right


def _add_checked(left, right):
    """Opposite signs cannot grow; equal signs are checked before addition."""
    if left > 0 and right > 0:
        _require(left <= _INTERMEDIATE_MAX - right,
                 "nested arithmetic intermediate bit bound exceeded")
    elif left < 0 and right < 0:
        _require(-left <= _INTERMEDIATE_MAX - (-right),
                 "nested arithmetic intermediate bit bound exceeded")
    return left + right


def _multiply(left, right):
    # Cross-cancellation precedes products, including their bound checks.
    first = gcd(abs(left.numerator), right.denominator)
    second = gcd(abs(right.numerator), left.denominator)
    numerator = _multiply_checked(left.numerator // first, right.numerator // second)
    denominator = _multiply_checked(left.denominator // second, right.denominator // first)
    return Fraction(numerator, denominator)


def _add(left, right):
    common = gcd(left.denominator, right.denominator)
    left_scale, right_scale = right.denominator // common, left.denominator // common
    numerator = _add_checked(_multiply_checked(left.numerator, left_scale),
                             _multiply_checked(right.numerator, right_scale))
    denominator = _multiply_checked(left.denominator, left_scale)
    return Fraction(numerator, denominator)


def _admit(equation, values):
    from .nested_model import Equation

    _require(type(equation) is Equation, "typed nested Equation required")
    # Revalidate a canonical copy even if a host bypassed frozen construction.
    Equation.from_dict(equation.to_dict())
    _require(type(values) is dict and set(values) == set(equation.dependencies),
             "dependency values must have exactly the equation dependency keys")
    dependencies = {key: _parse_rational(values[key], INPUT_BITS, f"dependency {key}")
                    for key in equation.dependencies}
    a = _parse_rational(equation.a, INPUT_BITS, "a")
    b = _parse_rational(equation.b, INPUT_BITS, "b")
    constant = _parse_rational(equation.rhs_constant, INPUT_BITS, "rhs_constant")
    terms = tuple((key, _parse_rational(coefficient, INPUT_BITS, f"coefficient {key}"))
                  for key, coefficient in equation.rhs_terms)
    return a, b, constant, terms, dependencies


def _ground(admitted):
    a, b, total, terms, dependencies = admitted
    # At most four products and four additions. Every intermediate is bounded.
    for key, coefficient in terms:
        total = _add(total, _multiply(coefficient, dependencies[key]))
    _require(abs(total.numerator).bit_length() <= INPUT_BITS
             and total.denominator.bit_length() <= INPUT_BITS,
             "grounded c exceeds the 128-bit procedure input bound")
    return a, b, total


def grounding_inputs(equation, values):
    """Return bounded a,b,c for the current equation; never compute its x."""
    grounded = _ground(_admit(equation, values))
    return dict(zip(("a", "b", "c"), map(_text, grounded), strict=True))


def verify_equation_output(equation, values, inputs, output):
    """Independently check exact grounding and a*x+b == RHS.

    Invalid schemas or arithmetic bounds raise ContractError. Validly encoded
    mismatches produce REJECTED. a=0 is outside the unique-solution contract.
    The bound is at most ten rational operations, not a FLOP/billing estimate.
    """
    admitted = _admit(equation, values)
    _require(type(inputs) is dict and set(inputs) == {"a", "b", "c"},
             "grounded inputs must contain exactly a, b, c")
    supplied = tuple(_parse_rational(inputs[key], INPUT_BITS, f"input {key}")
                     for key in ("a", "b", "c"))
    candidate = _parse_rational(output, INTERMEDIATE_BITS, "output")
    expected = _ground(admitted)
    if supplied != expected:
        reason = "GROUNDED_INPUT_MISMATCH"
    elif not expected[0]:
        reason = "ZERO_LEADING_COEFFICIENT"
    elif _add(_multiply(expected[0], candidate), expected[1]) != expected[2]:
        reason = "EQUATION_SUBSTITUTION_MISMATCH"
    else:
        reason = "EXACT_SUBSTITUTION_VALID"
    body = {"schema_version": REPORT_SCHEMA,
            "status": "CHECKED" if reason == "EXACT_SUBSTITUTION_VALID" else "REJECTED",
            "equation": equation.to_dict(),
            "dependency_values": {key: values[key] for key in equation.dependencies},
            "inputs": {key: inputs[key] for key in ("a", "b", "c")},
            "output": output, "reason": reason}
    return {**body, "report_digest": digest(body)}
