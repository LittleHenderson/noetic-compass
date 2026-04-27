"""CAS inversion engine — 7-axis transformations on compiled expressions.

Sprint 3 of the Idea Atlas. Given a compiled CAS source string, produce an
"inverted" CAS expression on a chosen axis. The inversion is a structural
transformation that preserves the surface shape of the expression (recipes
remain recipes, state literals remain state literals) while swapping the
participating primitives according to the axis-specific rule.

Authoritative axis definitions — see CLAUDE.md "7 Inversion Axes":

  N — Operator / Noetic involution imbalance
      Pairs: CO-2 ↔ CO-3, CO-5 ↔ CO-6, CO-8 ↔ CO-9.
      Self-duals: CO-0, CO-1, CO-4, CO-7 (unchanged).

  W — Domain precedence violation
      Reverse domain hierarchy: P ↔ O, C ↔ E.

  F — Drive pair imbalance
      Pairs: F1 ↔ F7, F2 ↔ F6, F3 ↔ F5. F4 self-dual.

  E — State-vector entropy deficit         (501, future sprint)
  S — Sub-Drive cross-domain variance      (501, future sprint)
  A — Pathway RPM chain violation          (501, future sprint)

  P — Compound: applies N + W + F together.

Implementation strategy: text-level regex transformation on the SOURCE string,
then re-validate by feeding the inverted source back through
``compile_expression``. The advantage over AST surgery is that:

* The compiler is the only source of truth for what is a syntactically valid
  CAS expression. By round-tripping through it, we are guaranteed a
  parser-clean result.
* The 10 Noetic operators, 4 Domains, and 7 Drives all have unambiguous
  surface tokens (``CO-N`` / ``^N``, ``^P`` / ``^C`` / ``^E`` / ``^O``,
  ``F1`` .. ``F7``) that do not collide with other grammar elements when we
  use carefully bounded regexes.

Returned :class:`InversionResult` is intentionally minimal — the route layer
shapes the public response.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from api.notation.compiler import compile_expression


# ---------------------------------------------------------------------------
# Axis catalogue
# ---------------------------------------------------------------------------


AXIS_DESCRIPTIONS: dict[str, str] = {
    "N": "Operator / Noetic involution flip (^2↔^3, ^5↔^6, ^8↔^9; ^0/^1/^4/^7 self-dual)",
    "W": "Domain precedence violation (P↔O, C↔E reversal of P≻C≻E≻O ordering)",
    "F": "Drive pair imbalance (F1↔F7, F2↔F6, F3↔F5; F4 self-dual)",
    "E": "State-vector entropy deficit — flatten/spread state activations",
    "S": "Sub-Drive cross-domain variance — invert drive distribution across domains",
    "A": "Pathway RPM chain violation — break A0 → Dn → Wn → Pn prerequisite ordering",
    "P": "Compound — apply N + W + F simultaneously",
}

IMPLEMENTED_AXES: tuple[str, ...] = ("N", "W", "F", "P")
DEFERRED_AXES: tuple[str, ...] = ("E", "S", "A")
ALL_AXES: tuple[str, ...] = IMPLEMENTED_AXES + DEFERRED_AXES


# Noetic involution pairs (CLAUDE.md "Structural invariants").
_NOETIC_PAIRS: dict[int, int] = {2: 3, 3: 2, 5: 6, 6: 5, 8: 9, 9: 8}

# Domain inversion (W axis): reverse total order P ≻ C ≻ E ≻ O.
_DOMAIN_PAIRS: dict[str, str] = {"P": "O", "O": "P", "C": "E", "E": "C"}

# Drive involution pairs (CLAUDE.md "7 Core Drives").
_DRIVE_PAIRS: dict[int, int] = {1: 7, 7: 1, 2: 6, 6: 2, 3: 5, 5: 3}


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class InversionResult:
    """Outcome of a single-axis inversion.

    ``valid`` indicates whether the inverted source compiled cleanly. When
    False, ``error`` carries the compiler diagnostic so the caller can
    surface a 422 instead of a 500.
    """

    axis: str
    description: str
    original: str
    inverted: str
    ast: dict[str, Any] | None
    valid: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Per-axis text transformations
# ---------------------------------------------------------------------------


# ``CO-N`` (long form) and ``^N`` (shorthand) both denote a Noetic operator.
# We must NOT swap a digit appearing inside a drive (``F2``) or a recipe
# coefficient (``2*X``). The CO-/^ prefixes are the disambiguator: bare
# digits are never Noetic operators.
_CO_LONG_RE = re.compile(r"CO-(\d)")
_CO_SHORT_RE = re.compile(r"\^(\d)")

# Domain marker: ``^D`` where D ∈ {P,C,E,O}. Beware: ``^N^D`` puts the
# domain after a digit, while bare ``^P`` (no preceding digit) denotes a
# domain-only literal. Both forms are handled by the same regex because
# we anchor on the literal ``^`` followed by a single domain letter.
#
# Negative lookahead: only EXCLUDE further alphabetic chars (so we never
# clip a hypothetical ``^Path`` token). Trailing ``_`` (drive subscript
# ``^P_{F2}``), ``|`` (register suffix ``^P|A``), digits, whitespace, EOF,
# operators (`+ * × → ` etc.), and closing braces all delimit a domain
# token and must be allowed to follow.
_DOMAIN_RE = re.compile(r"\^([PCEO])(?![A-Za-z])")

# Drive marker: ``F<digit>`` where digit ∈ {1..7}. We require that the
# preceding char is not a letter or underscore so identifiers like
# ``foo_F2`` or ``transferF2`` (hypothetical) are not perturbed.
# After-context: digit must not be followed by another digit (so ``F12``
# stays untouched -- not a valid drive anyway, but defensive).
_DRIVE_RE = re.compile(r"(?<![A-Za-z0-9_])F(\d)(?![0-9])")


def _apply_n(source: str) -> str:
    """Operator / Noetic involution flip."""

    def long_sub(m: re.Match[str]) -> str:
        n = int(m.group(1))
        return f"CO-{_NOETIC_PAIRS.get(n, n)}"

    def short_sub(m: re.Match[str]) -> str:
        n = int(m.group(1))
        return f"^{_NOETIC_PAIRS.get(n, n)}"

    out = _CO_LONG_RE.sub(long_sub, source)
    out = _CO_SHORT_RE.sub(short_sub, out)
    return out


def _apply_w(source: str) -> str:
    """Domain precedence violation."""

    def sub(m: re.Match[str]) -> str:
        d = m.group(1)
        return f"^{_DOMAIN_PAIRS.get(d, d)}"

    return _DOMAIN_RE.sub(sub, source)


def _apply_f(source: str) -> str:
    """Drive pair imbalance."""

    def sub(m: re.Match[str]) -> str:
        n = int(m.group(1))
        return f"F{_DRIVE_PAIRS.get(n, n)}"

    return _DRIVE_RE.sub(sub, source)


def _apply_p(source: str) -> str:
    """Compound: apply N then W then F. Order is irrelevant — the three
    transformations operate on disjoint token classes."""

    return _apply_f(_apply_w(_apply_n(source)))


_AXIS_TRANSFORMS: dict[str, Any] = {
    "N": _apply_n,
    "W": _apply_w,
    "F": _apply_f,
    "P": _apply_p,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class DeferredAxisError(NotImplementedError):
    """Raised when a caller requests an axis that is intentionally deferred.

    Carries the axis label and human-readable description so the API layer
    can surface an HTTP 501 with a structured body. We deliberately use a
    NotImplementedError subclass so callers using ``except NotImplementedError``
    in test scaffolding still catch it.
    """

    def __init__(self, axis: str) -> None:
        self.axis = axis
        self.description = AXIS_DESCRIPTIONS.get(axis, "")
        super().__init__(
            f"Inversion axis '{axis}' is not implemented in Sprint 3. "
            f"Description: {self.description}"
        )


class UnknownAxisError(ValueError):
    """Raised for an axis label that is not in the canonical 7-axis set."""


def invert_expression(source: str, axis: str) -> InversionResult:
    """Apply the named inversion axis to ``source`` and re-compile.

    Parameters
    ----------
    source:
        The original CAS expression as a string. Must compile cleanly under
        ``compile_expression`` for the inversion result to be meaningful;
        an invalid input is still transformed and returned, with
        ``valid=False`` so the caller can surface the error.
    axis:
        One of ``N``, ``W``, ``F``, ``P`` (implemented), or ``E`` / ``S`` /
        ``A`` (deferred). Anything else raises :class:`UnknownAxisError`.

    Raises
    ------
    UnknownAxisError
        If ``axis`` is not in the canonical 7-axis set.
    DeferredAxisError
        If ``axis`` is one of E / S / A (deferred to a later sprint).
    """

    if axis not in ALL_AXES:
        raise UnknownAxisError(
            f"unknown inversion axis: {axis!r}. "
            f"Valid axes are {', '.join(ALL_AXES)}."
        )
    if axis in DEFERRED_AXES:
        raise DeferredAxisError(axis)

    transform = _AXIS_TRANSFORMS[axis]
    inverted = transform(source)

    artifact = compile_expression(inverted)
    ast_dict: dict[str, Any] | None = None
    if artifact.valid and artifact.ast is not None:
        ast_dict = artifact.to_dict().get("ast")

    return InversionResult(
        axis=axis,
        description=AXIS_DESCRIPTIONS[axis],
        original=source,
        inverted=inverted,
        ast=ast_dict,
        valid=artifact.valid,
        error=artifact.error,
    )


def axis_description(axis: str) -> str:
    """Return the human-readable description for an axis label."""

    if axis not in AXIS_DESCRIPTIONS:
        raise UnknownAxisError(f"unknown inversion axis: {axis!r}")
    return AXIS_DESCRIPTIONS[axis]
