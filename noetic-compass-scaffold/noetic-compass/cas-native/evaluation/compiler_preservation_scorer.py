"""Deterministic structural-preservation scorer for CAS expression pairs.

Catches the "shape-without-content" failure mode flagged by the 2026-05-07
human relevance audit (`docs/working/path_B4_human_relevance_failure_2026_05_07.md`):
the model produces CAS expressions with the right silhouette but drops
load-bearing content (operands, drives, coefficients, named omega targets,
the Theta wrapper, etc.).

Scoring is grounded in the existing notation compiler
(`api/notation/compiler.py`). Both the ground-truth and predicted strings are
parsed via `compile_expression`; if either fails to parse, the result is an
all-False vector with the corresponding `parse_error` set. If both parse, the
two ASTs are walked in parallel and ten preservation booleans are reported.

No fuzzy matching, no heuristics: every property is decided from the AST
structure the compiler already exposes. When the compiler cannot confirm a
property holds, the property scores False (not ``unknown`` and never True by
default).

Public API
----------

::

    from cas_native.evaluation.compiler_preservation_scorer import (
        score_preservation, PreservationResult,
    )

    result = score_preservation(ground_truth, predicted)
    result.preservation_score   # mean of 10 booleans, in [0.0, 1.0]
    result.parse_error          # None / 'ground_truth_unparseable' / ...

The ten preservation axes are documented inline on
:class:`PreservationResult`.
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

# ---------------------------------------------------------------------------
# Path bootstrap. The scorer is imported under two paths:
#   * `from cas_native.evaluation.compiler_preservation_scorer import ...`
#     (the canonical Python package alias used in tests via `conftest.py`).
#   * Direct module execution from the repo root.
# We need `api.notation.compiler` to be importable; the compiler lives at
# `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`. We compute
# that path relative to this file and prepend it to `sys.path` only if not
# already importable, so we don't fight whatever the caller already set up.
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CAS_NATIVE_ROOT = os.path.dirname(_THIS_DIR)
_NOETIC_COMPASS_ROOT = os.path.dirname(_CAS_NATIVE_ROOT)
if _NOETIC_COMPASS_ROOT not in sys.path:
    sys.path.insert(0, _NOETIC_COMPASS_ROOT)

from api.notation.compiler import (  # noqa: E402  (after sys.path bootstrap)
    BinaryExpr,
    CardinalityExpr,
    DriveLiteral,
    EmergentResult,
    MetaAssertion,
    NumberLiteral,
    ProductionTargetLiteral,
    RecipeLiteral,
    RecipePrerequisite,
    StateLiteral,
    YieldExpression,
    compile_expression,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class PreservationResult:
    """Ten-axis structural-preservation result.

    Each axis is True when the predicted AST preserves the corresponding
    feature of the ground-truth AST exactly, False otherwise. ``parse_error``
    is non-None when the compiler refused at least one of the two strings;
    in that case every axis is False and ``preservation_score`` is 0.0.

    Axes:
      * ``operands_preserved`` -- count and identity of state-like operands
        match (where "identity" means: same Noetic operator, same Domain
        letter, same Domain explicitness, same drive subscript, same
        register specification). v74 case (GT 2 literals, predicted 1) is
        the canonical failure here.
      * ``operators_preserved`` -- multiset of binary-operator kinds
        (`*`/`x`, `+`, `->`, `o`, `/`, set ops) appearing across the two
        expressions matches.
      * ``domains_preserved`` -- per-state-literal `domain` letter AND
        `domain_explicit` flag both match. v77 presence (GT had no
        explicit Domain, predicted hallucinated `^P`) fails here.
      * ``drives_preserved`` -- ordered list of per-literal drive
        subscripts (None when absent) matches exactly. v77 cadence
        (F2/F5/F6 in GT, none in predicted) fails here.
      * ``registers_preserved`` -- per-literal register field matches
        exactly (single register, register-set, drive-register, and
        register absence each preserved verbatim).
      * ``coefficients_preserved`` -- ordered list of recipe-prerequisite
        coefficients matches within ``coefficient_tolerance``. v76 case
        (GT [0.53, 2.11, 1.04], predicted has none) fails here.
      * ``named_omega_targets_preserved`` -- the set of named omega
        targets appearing as ProductionTargetLiteral names AND as the
        omega-suffix on EmergentResult.assigned_name preserved exactly.
        Bare `Omega` is treated as the empty-name target and does NOT
        match any named target like `Omega_cadence`.
      * ``theta_wrappers_preserved`` -- count of RecipeLiteral nodes
        matches. v76 (GT has Theta wrapper, predicted is bare sum) fails.
      * ``arrows_preserved`` -- count of arrow-bearing structures
        (RecipeLiteral implicit `->`, BinaryExpr with op in
        {ARROW, LARROW, BIARROW}, leakage entries) matches.
      * ``meta_logic_relations_preserved`` -- count and per-relation
        operator multiset of MetaAssertion nodes matches.

    ``preservation_score`` is the mean of the ten booleans (0.0 to 1.0).
    """

    operands_preserved: bool
    operators_preserved: bool
    domains_preserved: bool
    drives_preserved: bool
    registers_preserved: bool
    coefficients_preserved: bool
    named_omega_targets_preserved: bool
    theta_wrappers_preserved: bool
    arrows_preserved: bool
    meta_logic_relations_preserved: bool
    preservation_score: float
    parse_error: str | None


# ---------------------------------------------------------------------------
# AST walker -- collects deterministic feature lists from the compiler AST.
# ---------------------------------------------------------------------------


def _normalize_register(value: Any) -> Any:
    """Render a register field into a hashable, equality-comparable form.

    The compiler exposes registers as ``None`` (neutral), ``str`` (single),
    or ``tuple[str, ...]`` (CAS v7.7 register-set form). We normalize the
    register-set form to a tuple of ordered letters so two same-set
    specifications compare equal. The single/None forms pass through.
    """

    if value is None:
        return None
    if isinstance(value, tuple):
        # Register-set: order is significant in the source notation
        # `|<R1,R2,...>` but the spec treats it as a *set*. Compare by the
        # ordered tuple; mismatches in either content or ordering surface
        # as a drift the scorer will flag. This is the strictest sensible
        # default (deterministic, no fuzzy alphabetization).
        return tuple(value)
    return str(value)


def _state_literal_signature(node: StateLiteral) -> dict[str, Any]:
    """Render a StateLiteral into a property dict for axis-by-axis comparison.

    Each axis pulls from this dict so the AST is walked exactly once.
    """

    return {
        "operator": int(node.operator),
        "domain": str(node.domain),
        "domain_explicit": bool(node.domain_explicit),
        "drive": int(node.drive) if node.drive is not None else None,
        "register": _normalize_register(node.register),
        "drive_register": _normalize_register(node.drive_register),
        # Operand identity for `operands_preserved`: collapse the full
        # signature into a hashable tuple. Domain, domain explicitness,
        # drive, and registers all participate — operand identity is the
        # full state-literal fingerprint, NOT just the Noetic+Domain pair
        # (otherwise the v77 cadence drives-stripped failure would not
        # surface as an operand mismatch).
        "operand_id": (
            int(node.operator),
            str(node.domain),
            bool(node.domain_explicit),
            int(node.drive) if node.drive is not None else None,
            _normalize_register(node.register),
            _normalize_register(node.drive_register),
        ),
    }


def _drive_literal_signature(node: DriveLiteral) -> dict[str, Any]:
    """Render a DriveLiteral into a property dict.

    Drive literals appear as bare `F_k|R` primitives outside of state
    contexts. They contribute one operand entry, no domain entry (unless
    the v7.6 `F_k^D` shorthand was used), and a register/drive entry.
    """

    return {
        "drive": int(node.drive),
        "register": _normalize_register(node.register),
        "domain": str(node.domain) if node.domain is not None else None,
        "operand_id": (
            "drive_literal",
            int(node.drive),
            _normalize_register(node.register),
            str(node.domain) if node.domain is not None else None,
        ),
    }


# Operator kinds we count for `operators_preserved`. Sourced from the
# compiler's BinaryExpr ops (parse_relation / parse_additive /
# parse_multiplicative / parse_set_expression).
_TRACKED_BINARY_OPS = frozenset(
    {
        "TIMES",
        "PLUS",
        "MINUS",
        "DIVIDE",
        "CIRC",  # `o` / `∘` -- fractal composition
        "ARROW",
        "LARROW",
        "BIARROW",
        "UNION",
        "INTERSECTION",
        "SET_DIFF",
    }
)


@dataclass
class _AstFeatures:
    """Deterministic feature bundle extracted from a compiler AST."""

    operand_ids: list[Any]
    state_signatures: list[dict[str, Any]]
    drive_signatures: list[dict[str, Any]]
    binary_op_kinds: list[str]
    recipe_count: int
    coefficients: list[float]
    omega_target_names: list[str]
    arrow_count: int
    meta_assertion_ops: list[str]


def _extract_omega_name_from_assigned(label: str) -> str | None:
    """Pull the omega-target suffix out of an EmergentResult.assigned_name.

    The compiler stores the raw author-supplied label verbatim, e.g.
    ``"^7^O|Ω_cadence"`` or ``"^7^O|Ω"``. We look for the literal
    Greek capital Omega character or the ASCII alias ``Omega`` and capture
    everything that follows. A bare ``Ω`` / ``Omega`` returns the
    empty string, which the named-target axis treats as a *bare* (unnamed)
    omega -- distinct from any named target.

    Returns None if the label does not contain an omega marker (e.g. the
    emergent name is something like ``TF`` or ``fused_commitment``); in
    that case the EmergentResult does not contribute to the omega-target
    list at all.
    """

    if "Ω" in label:
        marker = "Ω"
    elif "Omega" in label:
        marker = "Omega"
    else:
        return None
    suffix = label.split(marker, 1)[1]
    # If the very next character is an underscore, we have `Omega_<name>`;
    # the canonical name is everything after the underscore. Otherwise the
    # bare omega has no suffix -- return ``""`` to mark "bare omega".
    if suffix.startswith("_"):
        return suffix[1:]
    return ""


def _walk(node: Any, features: _AstFeatures) -> None:
    """Recursive walker that fills ``features`` from ``node``.

    Visits every child once. Order of traversal is deterministic and matches
    the compiler's AST shape, so ordered comparisons (drives, coefficients)
    are stable across both inputs.
    """

    if node is None:
        return

    if isinstance(node, StateLiteral):
        sig = _state_literal_signature(node)
        features.state_signatures.append(sig)
        features.operand_ids.append(sig["operand_id"])
        return

    if isinstance(node, DriveLiteral):
        sig = _drive_literal_signature(node)
        features.drive_signatures.append(sig)
        features.operand_ids.append(sig["operand_id"])
        return

    if isinstance(node, ProductionTargetLiteral):
        # A ProductionTargetLiteral seen outside of a RecipeLiteral target
        # slot is a reference (e.g. inside a YieldExpression). We still
        # count it for omega-target preservation: predicted output that
        # drops a `Omega_focused_refusal` reference fails the named-omega
        # axis even when wrapped in a yield query.
        features.omega_target_names.append(str(node.name))
        return

    if isinstance(node, RecipeLiteral):
        features.recipe_count += 1
        # The Theta wrapper has an implicit arrow between its prerequisites
        # and its target; count it for `arrows_preserved`.
        features.arrow_count += 1
        # Recipe target name -- always a named omega.
        features.omega_target_names.append(str(node.target.name))
        # Each prerequisite contributes a coefficient + a primitive walk.
        for prereq in node.prerequisites:
            assert isinstance(prereq, RecipePrerequisite)
            features.coefficients.append(float(prereq.coefficient))
            _walk(prereq.primitive, features)
        # Leakage entries each carry their own arrow (`-> Omega_side`) and
        # contribute the side-target's name to the omega-target list.
        for leak in node.leakages:
            features.arrow_count += 1
            features.coefficients.append(float(leak.coefficient))
            features.omega_target_names.append(str(leak.target.name))
        # Catalysts/inhibitors are condition annotations on the arrow; they
        # do NOT introduce additional arrows or operands. Names go through
        # without contributing to omega tracking (they are kappa/iota
        # markers, not omega targets).
        return

    if isinstance(node, EmergentResult):
        # The named-emergent assignment introduces a single named omega
        # *if* the assigned label contains an omega marker. The `=` here
        # is not an arrow -- it's a register-naming bind -- so we do NOT
        # increment `arrow_count`.
        omega_name = _extract_omega_name_from_assigned(node.assigned_name)
        if omega_name is not None:
            features.omega_target_names.append(omega_name)
        _walk(node.inner, features)
        return

    if isinstance(node, BinaryExpr):
        if node.op in _TRACKED_BINARY_OPS:
            features.binary_op_kinds.append(str(node.op))
        if node.op in {"ARROW", "LARROW", "BIARROW"}:
            features.arrow_count += 1
        _walk(node.left, features)
        _walk(node.right, features)
        return

    if isinstance(node, MetaAssertion):
        features.meta_assertion_ops.append(str(node.op))
        _walk(node.left, features)
        _walk(node.right, features)
        return

    if isinstance(node, CardinalityExpr):
        _walk(node.collection, features)
        return

    if isinstance(node, YieldExpression):
        # YieldExpression carries a ProductionTargetLiteral target plus
        # optional state/recipe operands; each contributes through the
        # normal walker recursion.
        _walk(node.target, features)
        _walk(node.state, features)
        _walk(node.recipe, features)
        return

    # Fall-through for nodes we don't specifically track (NumberLiteral,
    # Identifier, StringLiteral, MetaSetLiteral, TypedMetaSetLiteral,
    # TupleLiteral, MetaSymbol, EmptySetLiteral, FractalLiteral, ...).
    # These can carry nested expressions; recurse via known field names so
    # we don't miss embedded state literals.
    for attr in ("expr", "inner", "left", "right", "collection", "target", "state", "recipe"):
        if hasattr(node, attr):
            _walk(getattr(node, attr), features)
    for attr in ("elements", "args", "statements", "prerequisites", "leakages", "entries"):
        if hasattr(node, attr):
            seq = getattr(node, attr)
            if isinstance(seq, (list, tuple)):
                for item in seq:
                    if isinstance(item, tuple):
                        for sub in item:
                            _walk(sub, features)
                    else:
                        _walk(item, features)


def _features_for(ast: Any) -> _AstFeatures:
    features = _AstFeatures(
        operand_ids=[],
        state_signatures=[],
        drive_signatures=[],
        binary_op_kinds=[],
        recipe_count=0,
        coefficients=[],
        omega_target_names=[],
        arrow_count=0,
        meta_assertion_ops=[],
    )
    _walk(ast, features)
    return features


# ---------------------------------------------------------------------------
# Per-axis comparators
# ---------------------------------------------------------------------------


def _multiset_equal(a: Iterable[Any], b: Iterable[Any]) -> bool:
    """Order-insensitive multiset equality. Used for omega names, operator
    kinds, meta-assertion ops -- properties where we care that the two
    expressions carry the same *set with multiplicities* but the surface
    ordering is not load-bearing for the property.
    """

    return sorted(a) == sorted(b)


def _ordered_equal(a: Sequence[Any], b: Sequence[Any]) -> bool:
    """Order-sensitive equality. Used for coefficients and per-position
    drives where left-to-right position carries semantic meaning."""

    if len(a) != len(b):
        return False
    return list(a) == list(b)


def _coefficients_equal(a: Sequence[float], b: Sequence[float], tolerance: float) -> bool:
    """Ordered float comparison with absolute tolerance."""

    if len(a) != len(b):
        return False
    return all(math.isclose(x, y, abs_tol=tolerance, rel_tol=0.0) for x, y in zip(a, b))


def _drives_signature(features: _AstFeatures) -> list[Any]:
    """Ordered list of per-state-literal drive subscripts (or None) plus
    bare drive-literal drives, walked in source order. Used for
    `drives_preserved`.
    """

    out: list[Any] = []
    for sig in features.state_signatures:
        out.append(sig["drive"])
    for sig in features.drive_signatures:
        out.append(("drive_literal", sig["drive"]))
    return out


def _domains_signature(features: _AstFeatures) -> list[Any]:
    """Ordered list of per-state-literal (domain, domain_explicit) tuples,
    plus drive-literal domains where the v7.6 `F_k^D` shorthand was used.
    Used for `domains_preserved`.
    """

    out: list[Any] = []
    for sig in features.state_signatures:
        out.append((sig["domain"], sig["domain_explicit"]))
    for sig in features.drive_signatures:
        # Drive literals only contribute a domain entry when explicit.
        if sig["domain"] is not None:
            out.append(("drive_literal_domain", sig["domain"]))
    return out


def _registers_signature(features: _AstFeatures) -> list[Any]:
    """Ordered list of per-literal register specifications. Used for
    `registers_preserved`.
    """

    out: list[Any] = []
    for sig in features.state_signatures:
        out.append(("state", sig["register"], sig["drive_register"]))
    for sig in features.drive_signatures:
        out.append(("drive", sig["register"]))
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _all_false_result(parse_error: str) -> PreservationResult:
    return PreservationResult(
        operands_preserved=False,
        operators_preserved=False,
        domains_preserved=False,
        drives_preserved=False,
        registers_preserved=False,
        coefficients_preserved=False,
        named_omega_targets_preserved=False,
        theta_wrappers_preserved=False,
        arrows_preserved=False,
        meta_logic_relations_preserved=False,
        preservation_score=0.0,
        parse_error=parse_error,
    )


def score_preservation(
    ground_truth: str,
    predicted: str,
    *,
    coefficient_tolerance: float = 1e-6,
) -> PreservationResult:
    """Score predicted CAS expression preservation against ground truth.

    Parameters
    ----------
    ground_truth : str
        The reference expression. Parsed with the existing compiler.
    predicted : str
        The candidate expression. Parsed with the existing compiler.
    coefficient_tolerance : float, optional
        Absolute tolerance when comparing recipe coefficients. Default
        ``1e-6`` matches the precision the compiler stores coefficients at
        without false-positive flagging on rounding noise.

    Returns
    -------
    PreservationResult
        Ten booleans plus ``preservation_score`` (their mean) and an
        optional ``parse_error`` indicating which side(s) failed to parse.
    """

    gt_artifact = compile_expression(ground_truth)
    pred_artifact = compile_expression(predicted)

    gt_ok = gt_artifact.valid and gt_artifact.ast is not None
    pred_ok = pred_artifact.valid and pred_artifact.ast is not None

    if not gt_ok and not pred_ok:
        return _all_false_result("both_unparseable")
    if not gt_ok:
        return _all_false_result("ground_truth_unparseable")
    if not pred_ok:
        return _all_false_result("predicted_unparseable")

    gt = _features_for(gt_artifact.ast)
    pr = _features_for(pred_artifact.ast)

    # `operands_preserved`: count + identity. Multiset equality on the full
    # operand-id tuples (which include domain, drive, registers) so a
    # partial-content match (same Noetic+Domain but missing drive) still
    # fails. Treating the surface-position ordering as multiset rather than
    # ordered is intentional: `^a + ^b` and `^b + ^a` carry the same
    # operands; commutativity of `+` is captured elsewhere by the operator
    # axis if anyone reorders within a non-commutative operator.
    operands_preserved = _multiset_equal(gt.operand_ids, pr.operand_ids)

    # `operators_preserved`: multiset of binary-operator kinds. Same
    # rationale -- the *set* of operators must match; rearrangement under
    # commutative operators is not penalized by this axis.
    operators_preserved = _multiset_equal(gt.binary_op_kinds, pr.binary_op_kinds)

    # `domains_preserved`: ordered comparison so a "domain hallucination
    # added at position i" failure (v77 presence pred adding ^P) surfaces
    # at this axis even when the multiset of domain letters happens to
    # match. We pair (domain, domain_explicit) to catch the implicit-vs-
    # explicit distinction the audit case (^1 vs ^1^P) hinges on.
    domains_preserved = _ordered_equal(_domains_signature(gt), _domains_signature(pr))

    # `drives_preserved`: ordered list of drive subscripts. v77 cadence
    # has [F2, F5, F6] in GT and [None, None, None] in pred -- ordered
    # comparison flags this directly.
    drives_preserved = _ordered_equal(_drives_signature(gt), _drives_signature(pr))

    # `registers_preserved`: ordered list of (register, drive_register)
    # pairs per literal. Tuple-form register-sets compare element-wise.
    registers_preserved = _ordered_equal(_registers_signature(gt), _registers_signature(pr))

    # `coefficients_preserved`: ordered float comparison within tolerance.
    coefficients_preserved = _coefficients_equal(
        gt.coefficients, pr.coefficients, coefficient_tolerance
    )

    # `named_omega_targets_preserved`: multiset-equal across named omega
    # targets. Bare omega (empty-string suffix) and named omegas
    # (non-empty suffix) compare distinct, so v77 pred dropping `_cadence`
    # surfaces here even though both sides have an omega.
    named_omega_targets_preserved = _multiset_equal(
        gt.omega_target_names, pr.omega_target_names
    )

    # `theta_wrappers_preserved`: count of RecipeLiteral nodes matches.
    # v76 GT has 1 recipe, pred has 0 -- direct fail.
    theta_wrappers_preserved = gt.recipe_count == pr.recipe_count

    # `arrows_preserved`: total arrow count (recipe-implicit + binary).
    arrows_preserved = gt.arrow_count == pr.arrow_count

    # `meta_logic_relations_preserved`: same set of MetaAssertion ops
    # appears with the same multiplicity. Catches predictions that drop
    # `CO-3 in Noetics` style assertions even when the inner state
    # literal is preserved.
    meta_logic_relations_preserved = _multiset_equal(
        gt.meta_assertion_ops, pr.meta_assertion_ops
    )

    bools = [
        operands_preserved,
        operators_preserved,
        domains_preserved,
        drives_preserved,
        registers_preserved,
        coefficients_preserved,
        named_omega_targets_preserved,
        theta_wrappers_preserved,
        arrows_preserved,
        meta_logic_relations_preserved,
    ]
    score = sum(1 for b in bools if b) / len(bools)

    return PreservationResult(
        operands_preserved=operands_preserved,
        operators_preserved=operators_preserved,
        domains_preserved=domains_preserved,
        drives_preserved=drives_preserved,
        registers_preserved=registers_preserved,
        coefficients_preserved=coefficients_preserved,
        named_omega_targets_preserved=named_omega_targets_preserved,
        theta_wrappers_preserved=theta_wrappers_preserved,
        arrows_preserved=arrows_preserved,
        meta_logic_relations_preserved=meta_logic_relations_preserved,
        preservation_score=score,
        parse_error=None,
    )


__all__ = ["PreservationResult", "score_preservation"]
