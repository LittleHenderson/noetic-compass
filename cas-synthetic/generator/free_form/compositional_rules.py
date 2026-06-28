"""Compositional rules for free-form CAS surface generation.

Given a CAS expression string (e.g. ``^3^E_{F2}|A``,
``^3^E|A + ^7^O|E``, ``Theta(Omega_clarity) = ... -> Omega_clarity``,
``StateCluster{^6^O} ∩ StateCluster{^6^O, ^4^P, ^8^C}``), this module
parses the structure into a small structural plan that the surface
generator consumes. The parser is intentionally tolerant: it does not
attempt to fully validate the expression (the CAS compiler does that),
only to extract the load-bearing slots that drive lexicon selection.

Structural plan
---------------

The parser returns a ``StructuralPlan`` dataclass. The surface generator
inspects ``shape`` first (one of ``simple``, ``copresence``,
``integration``, ``recipe``, ``meta_logic``) and then dispatches to a
shape-specific handler. Each sub-state inside the plan carries the
slots the lexicon is keyed on:

- ``noetic`` ("0".."9")
- ``domain`` ("P" | "C" | "E" | "O" | None)
- ``drive`` ("F1".."F7" | None)
- ``register`` ("T" | "A" | "f" | "E" | None)

For shapes more elaborate than ``simple``, ``substates`` is the ordered
list of constituent simple states, and shape-specific fields
(``omega_name``, ``recipe_ingredients``, ``leakage`` etc.) carry extra
metadata.

Pure stdlib. Determinism is enforced by the surface generator, not the
parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final, Optional


VALID_NOETICS: Final[frozenset[str]] = frozenset({str(i) for i in range(10)})
VALID_DOMAINS: Final[frozenset[str]] = frozenset({"P", "C", "E", "O"})
VALID_DRIVES: Final[frozenset[str]] = frozenset({f"F{i}" for i in range(1, 8)})
VALID_REGISTERS: Final[frozenset[str]] = frozenset({"T", "A", "f", "E"})


# ---------------------------------------------------------------------------
# Plan types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SimpleState:
    """A single CAS state of the form ``^N[^D][_{F}][|R]``."""

    noetic: str
    domain: Optional[str] = None
    drive: Optional[str] = None
    register: Optional[str] = None
    register_set: tuple[str, ...] = ()  # for |⟨R1,R2,...⟩ specifications

    @property
    def has_register(self) -> bool:
        return self.register is not None or bool(self.register_set)


@dataclass
class StructuralPlan:
    """Parsed plan for a CAS expression.

    Fields
    ------
    shape:
        One of ``simple``, ``copresence``, ``integration``, ``recipe``,
        ``meta_logic``, or ``unknown`` if the expression could not be
        parsed.
    substates:
        Ordered list of ``SimpleState`` extracted from the expression.
        For ``simple`` shape this list has length 1. For ``recipe``
        this is the list of recipe ingredients (in order).
    omega_name:
        For ``integration`` and ``recipe`` shapes, the canonical
        Omega-target name (``Omega_clarity``, ``Omega_refusal``, etc).
    recipe_ingredients:
        For ``recipe`` shapes, the list of ``(coefficient,
        SimpleState)`` ingredient pairs.
    leakage:
        For ``recipe`` shapes, an optional leakage / side-reaction
        descriptor (raw token of the leaked Omega name) or None.
    meta_relations:
        For ``meta_logic`` shapes, the list of relation operators
        detected in the expression (one or more of ``intersection``,
        ``union``, ``difference``, ``product``, ``cover``,
        ``partition``).
    raw:
        The untouched original expression, for fallback rendering.
    notes:
        Free-form annotations the parser used while assembling the
        plan; useful for tests and debug printing.
    """

    shape: str
    substates: list[SimpleState] = field(default_factory=list)
    omega_name: Optional[str] = None
    recipe_ingredients: list[tuple[float, SimpleState]] = field(default_factory=list)
    leakage: Optional[str] = None
    meta_relations: list[str] = field(default_factory=list)
    raw: str = ""
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# State-level parsing
# ---------------------------------------------------------------------------


_SIMPLE_STATE_RE = re.compile(
    r"""
    \^(?P<noetic>\d)                       # ^N (Noetic)
    (?:\^(?P<domain>[PCEO]))?              # optional ^D (Domain)
    (?:_\{(?P<drive>F\d)\})?               # optional _{F#}
    (?:                                    # optional register
        \|
        (?:
            (?P<register_single>[TAfE])    # single register
          | ⟨\s*(?P<register_set>[TAfE](?:\s*,\s*[TAfE])*)\s*⟩  # set
        )
    )?
    """,
    re.VERBOSE,
)


def _parse_simple_state(token: str) -> Optional[SimpleState]:
    """Parse a string like ``^3^E_{F2}|A`` into a ``SimpleState``.

    Returns None if the token does not start with a recognisable
    Noetic-and-(optional)-Domain prefix.
    """
    cleaned = token.strip()
    if not cleaned.startswith("^"):
        return None
    m = _SIMPLE_STATE_RE.match(cleaned)
    if not m:
        return None

    noetic = m.group("noetic")
    if noetic not in VALID_NOETICS:
        return None

    domain = m.group("domain")
    if domain is not None and domain not in VALID_DOMAINS:
        domain = None

    drive = m.group("drive")
    if drive is not None and drive not in VALID_DRIVES:
        drive = None

    register_single = m.group("register_single")
    register_set_raw = m.group("register_set")

    register: Optional[str] = None
    register_set: tuple[str, ...] = ()
    if register_single is not None and register_single in VALID_REGISTERS:
        register = register_single
    elif register_set_raw is not None:
        items = tuple(
            r.strip() for r in register_set_raw.split(",") if r.strip()
        )
        register_set = tuple(r for r in items if r in VALID_REGISTERS)

    return SimpleState(
        noetic=noetic,
        domain=domain,
        drive=drive,
        register=register,
        register_set=register_set,
    )


def _split_top_level(expr: str, separator: str) -> list[str]:
    """Split ``expr`` on ``separator`` ignoring tokens inside any of
    ``()``, ``{}`` or ``⟨⟩``. Whitespace is preserved per token; callers
    typically strip the result.
    """
    parts: list[str] = []
    depth_paren = 0
    depth_brace = 0
    depth_angle = 0
    current: list[str] = []
    sep_len = len(separator)
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "(":
            depth_paren += 1
            current.append(ch)
            i += 1
            continue
        if ch == ")":
            if depth_paren > 0:
                depth_paren -= 1
            current.append(ch)
            i += 1
            continue
        if ch == "{":
            depth_brace += 1
            current.append(ch)
            i += 1
            continue
        if ch == "}":
            if depth_brace > 0:
                depth_brace -= 1
            current.append(ch)
            i += 1
            continue
        if ch == "⟨":
            depth_angle += 1
            current.append(ch)
            i += 1
            continue
        if ch == "⟩":
            if depth_angle > 0:
                depth_angle -= 1
            current.append(ch)
            i += 1
            continue
        if (
            depth_paren == 0
            and depth_brace == 0
            and depth_angle == 0
            and expr[i : i + sep_len] == separator
        ):
            parts.append("".join(current))
            current = []
            i += sep_len
            continue
        current.append(ch)
        i += 1
    parts.append("".join(current))
    return parts


# ---------------------------------------------------------------------------
# Shape detection
# ---------------------------------------------------------------------------


_RECIPE_RE = re.compile(
    r"\b[ΘTheta]\w*\s*\(\s*(?P<target>Ω?\w+)\s*\)",
    re.UNICODE,
)
_RECIPE_FALLBACK_RE = re.compile(r"\bTheta\s*\(\s*(?P<target>\w+)\s*\)")
_PRODUCTION_ARROW_RE = re.compile(r"->|→")
_LEAKAGE_RE = re.compile(
    r"(?P<coef>\d+(?:\.\d+)?)\s*\*\s*Λ\s*·\s*(?P<leak>Ω?_?[A-Za-z][A-Za-z0-9_]*)",
    re.UNICODE,
)
_INTEGRATION_RESULT_RE = re.compile(
    r"=\s*(?P<state>\^\d(?:\^[PCEO])?(?:_\{F\d\})?(?:\|\w+)?)?\s*\|?\s*(?P<omega>Ω?\w+)?",
    re.UNICODE,
)
_OMEGA_TOKEN_RE = re.compile(r"\bΩ?_?\w*Omega\w*|Ω\w*", re.UNICODE)
_META_LOGIC_TOKEN_RE = re.compile(
    r"\b(?:NoeticCluster|StateCluster|RelationCluster|FoundationCluster|"
    r"DomainCluster|RegisterCluster|Product|CoverOf|PartitionOf|Tuple|"
    r"Coordinate)\b"
)
_META_RELATION_TOKENS: Final[dict[str, str]] = {
    "∩": "intersection",
    "∪": "union",
    "∖": "difference",
    "\\": "difference",
    "Product": "product",
    "CoverOf": "cover",
    "PartitionOf": "partition",
}


def _has_meta_logic(expr: str) -> bool:
    return bool(_META_LOGIC_TOKEN_RE.search(expr))


def _has_recipe(expr: str) -> bool:
    if "Θ" in expr or "Theta" in expr:
        return bool(_PRODUCTION_ARROW_RE.search(expr))
    return False


def _detect_meta_relations(expr: str) -> list[str]:
    found: list[str] = []
    for token, name in _META_RELATION_TOKENS.items():
        if token in expr and name not in found:
            found.append(name)
    return found


# ---------------------------------------------------------------------------
# Recipe parsing
# ---------------------------------------------------------------------------


_INGREDIENT_RE = re.compile(
    r"(?P<coef>\d+(?:\.\d+)?)\s*\*\s*(?P<state>\^\d[^+\-→]+?)(?=\s*[+\-→]|$)",
    re.UNICODE,
)


def _parse_recipe(expr: str) -> StructuralPlan:
    plan = StructuralPlan(shape="recipe", raw=expr)

    # Extract the production target name.
    target_match = re.search(
        r"[ΘTheta]\w*\s*\(\s*(?P<target>[Ωa-zA-Z_]\w*)\s*\)",
        expr,
    )
    if target_match:
        target_raw = target_match.group("target").strip()
        plan.omega_name = target_raw
        plan.notes.append(f"recipe_target={target_raw}")

    # Pull the ingredient block (everything up to '->' or '→').
    arrow_match = _PRODUCTION_ARROW_RE.search(expr)
    if arrow_match:
        before_arrow = expr[: arrow_match.start()]
        after_arrow = expr[arrow_match.end():]
    else:
        before_arrow = expr
        after_arrow = ""

    # The ingredient block lives after the leading 'Theta(...) =' segment.
    eq_idx = before_arrow.find("=")
    if eq_idx >= 0:
        ingredient_block = before_arrow[eq_idx + 1 :]
    else:
        ingredient_block = before_arrow

    ingredient_segments = [
        seg.strip() for seg in _split_top_level(ingredient_block, "+") if seg.strip()
    ]
    for seg in ingredient_segments:
        m = re.match(
            r"(?P<coef>\d+(?:\.\d+)?)\s*\*\s*(?P<state>\^\d.*)",
            seg,
        )
        if not m:
            continue
        try:
            coef = float(m.group("coef"))
        except ValueError:
            continue
        state = _parse_simple_state(m.group("state"))
        if state is None:
            continue
        plan.recipe_ingredients.append((coef, state))
        plan.substates.append(state)

    # Detect leakage on the right-hand side (e.g. ``+ 0.1*Λ·Omega_aversion_overflow``).
    leak_match = _LEAKAGE_RE.search(after_arrow) or _LEAKAGE_RE.search(expr)
    if leak_match:
        plan.leakage = leak_match.group("leak").strip()
        plan.notes.append(f"leakage={plan.leakage}")

    if not plan.substates:
        plan.notes.append("recipe_unparsed_ingredients")
    return plan


# ---------------------------------------------------------------------------
# Integration parsing (Clarification 10 ``×`` shape)
# ---------------------------------------------------------------------------


def _parse_integration(expr: str) -> StructuralPlan:
    plan = StructuralPlan(shape="integration", raw=expr)

    # Locate the parenthesised block on the LHS.
    eq_idx = expr.find("=")
    if eq_idx >= 0:
        lhs = expr[:eq_idx]
        rhs = expr[eq_idx + 1 :]
    else:
        lhs = expr
        rhs = ""

    lhs_stripped = lhs.strip()
    if lhs_stripped.startswith("(") and lhs_stripped.endswith(")"):
        inner = lhs_stripped[1:-1]
    else:
        inner = lhs_stripped

    parts = [
        seg.strip() for seg in _split_top_level(inner, "×") if seg.strip()
    ]
    for seg in parts:
        state = _parse_simple_state(seg)
        if state is not None:
            plan.substates.append(state)

    rhs_stripped = rhs.strip()
    if rhs_stripped:
        # The result token might be ``^3^P|Omega_refusal`` or just ``Omega_refusal``.
        result_state = _parse_simple_state(rhs_stripped)
        if result_state is not None and result_state.register is None:
            # Look for a trailing ``|Omega_*`` that the SimpleState parser
            # would have skipped.
            omega_match = re.search(r"\|(Ω?_?\w*[Oo]mega\w*|Ω\w+)", rhs_stripped)
            if omega_match:
                plan.omega_name = omega_match.group(1)
        else:
            omega_match = re.search(r"(Ω?_?\w*[Oo]mega\w*|Ω\w+)", rhs_stripped)
            if omega_match:
                plan.omega_name = omega_match.group(1)

    return plan


# ---------------------------------------------------------------------------
# Co-presence parsing (``+`` shape)
# ---------------------------------------------------------------------------


def _parse_copresence(expr: str) -> StructuralPlan:
    plan = StructuralPlan(shape="copresence", raw=expr)
    parts = [
        seg.strip() for seg in _split_top_level(expr, "+") if seg.strip()
    ]
    for seg in parts:
        state = _parse_simple_state(seg)
        if state is not None:
            plan.substates.append(state)
    if len(plan.substates) < 2:
        # Fall back: not actually co-presence, treat as simple.
        plan.shape = "simple"
        if not plan.substates:
            single = _parse_simple_state(expr)
            if single is not None:
                plan.substates = [single]
    return plan


# ---------------------------------------------------------------------------
# Meta-logic parsing
# ---------------------------------------------------------------------------


_CLUSTER_BODY_RE = re.compile(
    r"(?P<head>\w+Cluster|Product|CoverOf|PartitionOf|Tuple|Coordinate)"
    r"\s*[{(]\s*(?P<body>[^{}()]*)\s*[})]",
    re.UNICODE,
)


def _parse_meta_logic(expr: str) -> StructuralPlan:
    plan = StructuralPlan(shape="meta_logic", raw=expr)
    plan.meta_relations = _detect_meta_relations(expr)
    if not plan.meta_relations:
        plan.meta_relations = ["family"]

    # Pull every state-like token from inside cluster braces.
    seen: list[SimpleState] = []
    for body in _CLUSTER_BODY_RE.finditer(expr):
        items = body.group("body").split(",")
        for item in items:
            state = _parse_simple_state(item.strip())
            if state is not None:
                seen.append(state)

    # Fallback: scan the entire expression for any state tokens that
    # were not inside a cluster (so e.g. ``^3^P × ^4^P`` still surfaces
    # the substates even when the clusters are minimal).
    for tok in _SIMPLE_STATE_RE.finditer(expr):
        match = tok.group(0)
        state = _parse_simple_state(match)
        if state is not None and state not in seen:
            seen.append(state)

    plan.substates = seen
    return plan


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def parse_cas_expression(expr: str) -> StructuralPlan:
    """Parse a CAS expression into a ``StructuralPlan``.

    Detection priority: ``recipe`` -> ``meta_logic`` -> ``integration``
    -> ``copresence`` -> ``simple`` -> ``unknown``. The first matching
    shape wins; the parser does not attempt to validate the surrounding
    expression.
    """
    expr_clean = (expr or "").strip()
    if not expr_clean:
        return StructuralPlan(shape="unknown", raw=expr_clean)

    if _has_recipe(expr_clean):
        return _parse_recipe(expr_clean)

    if _has_meta_logic(expr_clean):
        return _parse_meta_logic(expr_clean)

    # Integration shape requires both ``×`` and ``=``.
    if "×" in expr_clean and "=" in expr_clean:
        return _parse_integration(expr_clean)

    if "+" in expr_clean and "×" not in expr_clean:
        plan = _parse_copresence(expr_clean)
        if plan.shape == "copresence":
            return plan

    single = _parse_simple_state(expr_clean)
    if single is not None:
        return StructuralPlan(shape="simple", substates=[single], raw=expr_clean)

    # Fallback for products without ``=`` (e.g. ``^4^P_{F2} * ^3^P_{F2}``):
    if "*" in expr_clean and "Θ" not in expr_clean and "Theta" not in expr_clean:
        parts = [
            seg.strip() for seg in _split_top_level(expr_clean, "*") if seg.strip()
        ]
        substates: list[SimpleState] = []
        for seg in parts:
            state = _parse_simple_state(seg)
            if state is not None:
                substates.append(state)
        if substates:
            return StructuralPlan(
                shape="copresence" if len(substates) > 1 else "simple",
                substates=substates,
                raw=expr_clean,
                notes=["product_treated_as_copresence"] if len(substates) > 1 else [],
            )

    return StructuralPlan(shape="unknown", raw=expr_clean, notes=["parse_failed"])


__all__ = [
    "SimpleState",
    "StructuralPlan",
    "VALID_NOETICS",
    "VALID_DOMAINS",
    "VALID_DRIVES",
    "VALID_REGISTERS",
    "parse_cas_expression",
]
