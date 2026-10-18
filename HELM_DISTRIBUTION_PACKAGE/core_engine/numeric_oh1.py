"""RB-OH1 arithmetic (FROZEN answerers.SUB.arithmetic): Python decimal at 40 significant digits (software, so the same
digits on Windows and Linux) and exact fractions. Standard library only. Nothing executes on import."""
from __future__ import annotations

import hashlib
import json
from decimal import Context, Decimal, ROUND_HALF_EVEN, InvalidOperation, DivisionByZero, Overflow
from fractions import Fraction

PREC = 40
CTX = Context(prec=PREC, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
              traps=[InvalidOperation, DivisionByZero, Overflow])
TOL_ABS, TOL_REL = Fraction(1, 50), Fraction(1, 20)          # lsr_t1 run_t1.hit (the 5% standard)
INF = Decimal("Infinity")


def dec(v):
    """Exact value -> Decimal rounded to 40 digits (floats and ints are exact first)."""
    if isinstance(v, Decimal):
        return CTX.plus(v)
    if isinstance(v, Fraction):
        return CTX.divide(Decimal(v.numerator), Decimal(v.denominator))
    if isinstance(v, (int, float)):
        return CTX.plus(Decimal(v))
    raise TypeError(type(v))


def frac(d):
    return Fraction(d) if not isinstance(d, Fraction) else d


def dln(v):
    return CTX.ln(dec(v))


def dexp(v):
    return CTX.exp(v)


def dpow(x, rho):
    """x^rho = exp(rho * ln x) (x > 0); 0 for x == 0 and rho > 0; None when undefined."""
    xd = dec(x)
    if xd == 0:
        return Decimal(0) if rho > 0 else None
    if xd < 0:
        return None
    return CTX.exp(CTX.multiply(dec(rho), CTX.ln(xd)))


def fs(fr):
    """Exact fraction -> 'p/q' text (Decimals converted exactly)."""
    fr = Fraction(fr)
    return "%d/%d" % (fr.numerator, fr.denominator)


def pf(s):
    if s is None:
        return None
    n, d = s.split("/")
    return Fraction(int(n), int(d))


def hit(yhat, y):
    """lsr_t1 run_t1.hit in exact fractions."""
    return abs(Fraction(yhat) - Fraction(y)) <= max(TOL_ABS, TOL_REL * Fraction(y))


def err(yhat, y):
    """FROZEN answerers.error_measure."""
    yh, yy = Fraction(yhat), Fraction(y)
    if yh == yy:
        return Decimal(0)
    if yh <= 0 or yy <= 0:
        return INF
    return abs(CTX.ln(dec(yh / yy)))


def inverse(M):
    """Exact Gauss-Jordan inverse of a square Fraction matrix (lsr_t5 blend.inverse, imported unchanged)."""
    from lsr_t5 import blend as B
    return B.inverse(M)


def solve_square(A, b):
    inv = inverse(A)
    if inv is None:
        return None
    return [sum((a * v for a, v in zip(row, b)), Fraction(0)) for row in inv]


def solve_ls(A, b):
    """Exact normal equations (A^T A) beta = A^T b."""
    p = len(A[0])
    M = [[sum((row[i] * row[j] for row in A), Fraction(0)) for j in range(p)] for i in range(p)]
    v = [sum((row[i] * t for row, t in zip(A, b)), Fraction(0)) for i in range(p)]
    return solve_square(M, v)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def median_upper(vals):
    s = sorted(vals)
    return s[len(s) // 2] if s else None
