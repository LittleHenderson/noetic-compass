"""Versioned deterministic Decimal arithmetic for the PCBA v8 candidate."""

from __future__ import annotations

from contextlib import contextmanager
from decimal import (
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    localcontext,
)
from functools import wraps
import hashlib
import json
from typing import Callable, Iterator, ParamSpec, TypeVar


DECIMAL_CONTEXT_PROFILE = "cas-pcba-v8.decimal-context.v1"
DECIMAL_PRECISION = 60
DECIMAL_EMIN = -999_999
DECIMAL_EMAX = 999_999
DECIMAL_ROUNDING = ROUND_HALF_EVEN


def decimal_context_payload() -> dict[str, object]:
    return {
        "profile": DECIMAL_CONTEXT_PROFILE,
        "precision": DECIMAL_PRECISION,
        "rounding": DECIMAL_ROUNDING,
        "emin": DECIMAL_EMIN,
        "emax": DECIMAL_EMAX,
        "clamp": 0,
        "capitals": 1,
        "traps": ["DivisionByZero", "InvalidOperation", "Overflow"],
    }


def _payload_sha256(payload: object) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest().upper()


DECIMAL_CONTEXT_SHA256 = _payload_sha256(decimal_context_payload())


def new_decimal_context() -> Context:
    """Return a new context so callers cannot mutate shared arithmetic state."""

    context = Context(
        prec=DECIMAL_PRECISION,
        rounding=DECIMAL_ROUNDING,
        Emin=DECIMAL_EMIN,
        Emax=DECIMAL_EMAX,
        capitals=1,
        clamp=0,
    )
    context.traps[DivisionByZero] = True
    context.traps[InvalidOperation] = True
    context.traps[Overflow] = True
    return context


@contextmanager
def fixed_decimal_context() -> Iterator[Context]:
    """Run one operation under the exact versioned PCBA arithmetic profile."""

    with localcontext(new_decimal_context()) as context:
        yield context


P = ParamSpec("P")
R = TypeVar("R")


def deterministic_decimal(
    function: Callable[P, R],
) -> Callable[P, R]:
    """Execute a public arithmetic operation independently of ambient context."""

    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        with fixed_decimal_context():
            return function(*args, **kwargs)

    return wrapped


def exact_decimal_sum(values: tuple[Decimal, ...] | list[Decimal]) -> Decimal:
    """Sum finite Decimals by aligned integers, without Decimal context rounding."""

    items = tuple(values)
    if not items:
        return Decimal("0")
    if any(type(item) is not Decimal or not item.is_finite() for item in items):
        raise ValueError("exact_decimal_sum requires finite Decimal values")
    exponents = [item.as_tuple().exponent for item in items]
    if any(type(exponent) is not int for exponent in exponents):
        raise ValueError("exact_decimal_sum does not accept special Decimals")
    common_exponent = min(exponents)
    total = 0
    for item, exponent in zip(items, exponents):
        decimal_tuple = item.as_tuple()
        coefficient = 0
        for digit in decimal_tuple.digits:
            coefficient = coefficient * 10 + digit
        if decimal_tuple.sign:
            coefficient = -coefficient
        total += coefficient * (10 ** (exponent - common_exponent))
    return Decimal(f"{total}E{common_exponent}")


def exact_decimal_equal(left: Decimal, right: Decimal) -> bool:
    return exact_decimal_sum((left, right.copy_negate())).is_zero()


def exact_decimal_add(left: Decimal, right: Decimal) -> Decimal:
    return exact_decimal_sum((left, right))
