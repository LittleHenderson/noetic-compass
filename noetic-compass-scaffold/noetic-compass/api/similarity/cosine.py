"""Reference cosine-similarity metric over compiled CAS expressions.

See ``api/similarity/README.md`` for the full design (input/output shape,
the five feature vectors, default weights, and the inversion-pair
research note).

Sprint 1 / Idea Atlas. Pure stdlib.
"""

from __future__ import annotations

import math
from typing import Any

from api.notation.compiler import compile_expression


# ---------------------------------------------------------------------------
# Canonical vector axes. These mirror the primitives named in CLAUDE.md and
# docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md. They are NOT new primitives; they
# are slot orderings for the existing 10 Noetics, 4 Domains, 7 Drives, and
# 4 Registers.
# ---------------------------------------------------------------------------

NOETIC_AXIS: tuple[str, ...] = tuple(f"CO-{n}" for n in range(10))  # CO-0..CO-9
DOMAIN_AXIS: tuple[str, ...] = ("P", "C", "E", "O")
DRIVE_AXIS: tuple[str, ...] = tuple(f"F{k}" for k in range(1, 8))   # F1..F7
REGISTER_AXIS: tuple[str, ...] = ("T", "A", "f", "E")
FOUNDATION_AXIS: tuple[str, ...] = tuple(
    f"Foundation_{i}" for i in range(1, 8)
)  # Foundation_1..Foundation_7

# Default weights -- reasoned in README.md "Default Weights" section.
# Day 3 sprint Phase 1 added the Foundation axis at 0.10 (per directive).
# The total now sums to 1.10; the active-weight renormalization in
# :func:`cas_similarity` (which excludes vacuous axes) means this does not
# change scores when foundation is unspecified on both sides, preserving
# backward compatibility with the pre-Day-3 sixteen tests.
DEFAULT_WEIGHTS: dict[str, float] = {
    "noetic": 0.40,
    "domain": 0.20,
    "drive": 0.20,
    "register": 0.10,
    "metaset": 0.10,
    "foundation": 0.10,
}

# Sprint 1 inversion-pair policy default. See README.md "Inversion-Pair
# Semantics" for the full rationale and the alternative values.
DEFAULT_INVERSION_POLICY: str = "neutral"

# Day 3 sprint Phase 1: cross-pair proximity boost added to the final
# weighted-sum score whenever expression A activates one half of an
# involution pair AND expression B activates the partner. This is a
# multiplicative-on-top adjustment, NOT part of the normalized axis weights.
# The boost is independent of the inversion_policy knob (which controls
# how the pairs are treated WITHIN the noetic component score).
INVOLUTION_PAIR_BOOST: float = 0.20

# Involution pairs (CLAUDE.md "Structural invariants"). Used by:
# - inversion_policy="merge" (collapse pairs into shared slots)
# - inversion_policy="penalize" (subtract penalty when only inverted partners present)
# - cross-pair proximity boost (add INVOLUTION_PAIR_BOOST to final score
#   when expressions reference partner Noetics)
_INVOLUTION_PAIRS: tuple[tuple[str, str], ...] = (
    ("CO-2", "CO-3"),
    ("CO-5", "CO-6"),
    ("CO-8", "CO-9"),
)

# Compiler tokens that count as Foundation references for the Foundation
# similarity axis. We accept both the bare meta-set names ("Foundation_1"
# .. "Foundation_7") and the family-level names ("Foundations",
# "SubFoundations") plus the typed-set constructors ("FoundationSet",
# "SubFoundationSet"). Family-level references contribute to a synthetic
# "any-foundation" slot (slot 0..6 are filled by index). Family-level
# references contribute uniformly across all 7 slots so two expressions
# both referencing the family are similar but not aligned to a specific
# Foundation_k.
_FOUNDATION_FAMILY_TOKENS: frozenset[str] = frozenset(
    {"Foundations", "SubFoundations", "FoundationSet", "SubFoundationSet"}
)


# ---------------------------------------------------------------------------
# AST walking
# ---------------------------------------------------------------------------


def _walk_ast(node: Any):
    """Yield every dict-shaped AST node in pre-order.

    The compiler's ``serialize_ast`` produces nested dicts with a ``"node"``
    discriminator key and child fields that may themselves be dicts, lists
    of dicts, or primitive values. We walk recursively; non-dict / non-list
    leaves are ignored. Robust against missing keys.
    """

    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_ast(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_ast(item)
    # primitives (str, int, float, None, bool) -- nothing to do


def _collect_register_letters(value: Any) -> list[str]:
    """Normalize a register field to a flat list of letters.

    CAS v7.5 single-register form serializes as a string (``"A"``).
    CAS v7.7 register-set form serializes as a list under
    ``register_set`` / ``drive_register_set``. We accept either shape and
    return an empty list for ``None`` / missing.
    """

    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [r for r in value if isinstance(r, str)]
    return []


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


def extract_features(artifact_dict: dict[str, Any]) -> dict[str, list[float]]:
    """Decompose a compiled-artifact dict into the five feature vectors.

    ``artifact_dict`` is the output of
    ``compile_expression(src).to_dict()``. Returns a dict with five keys:

    - ``"noetic"``   -- 10-dim, one slot per ``CO-0`` .. ``CO-9``.
    - ``"domain"``   -- 4-dim,  one slot per ``P``, ``C``, ``E``, ``O``.
    - ``"drive"``    -- 7-dim,  one slot per ``F1`` .. ``F7``.
    - ``"register"`` -- 4-dim,  one slot per ``T``, ``A``, ``f``, ``E``.
    - ``"metaset"``  -- variable-dim bag-of-names, sorted by name; the
                       caller is expected to align two metaset vectors via
                       a name-set union before passing them to
                       :func:`cosine_similarity`. The companion
                       :func:`_aligned_metaset_vectors` helper handles this
                       alignment internally; ``extract_features`` exposes
                       the unaligned per-side counts so callers can inspect
                       which names appeared.
    - ``"foundation"`` -- 7-dim, one slot per ``Foundation_1`` ..
                       ``Foundation_7``. Specific ``Foundation_k`` tokens
                       fill slot ``k-1``. Family-level tokens
                       (``Foundations``, ``SubFoundations``,
                       ``FoundationSet``, ``SubFoundationSet``) contribute
                       uniformly across all 7 slots, so family-vs-family
                       references match while family-vs-specific references
                       partially overlap.

    A failed-compile artifact (``valid is False``) returns all-zero vectors.
    """

    noetic = [0.0] * len(NOETIC_AXIS)
    domain = [0.0] * len(DOMAIN_AXIS)
    drive = [0.0] * len(DRIVE_AXIS)
    register = [0.0] * len(REGISTER_AXIS)
    foundation = [0.0] * len(FOUNDATION_AXIS)
    metaset_counts: dict[str, float] = {}

    if not artifact_dict.get("valid", False):
        return {
            "noetic": noetic,
            "domain": domain,
            "drive": drive,
            "register": register,
            "metaset": _metaset_vector_from_counts(metaset_counts),
            "foundation": foundation,
        }

    ast = artifact_dict.get("ast")
    if ast is None:
        return {
            "noetic": noetic,
            "domain": domain,
            "drive": drive,
            "register": register,
            "metaset": _metaset_vector_from_counts(metaset_counts),
            "foundation": foundation,
        }

    noetic_index = {name: i for i, name in enumerate(NOETIC_AXIS)}
    domain_index = {name: i for i, name in enumerate(DOMAIN_AXIS)}
    drive_index = {name: i for i, name in enumerate(DRIVE_AXIS)}
    register_index = {name: i for i, name in enumerate(REGISTER_AXIS)}
    foundation_index = {name: i for i, name in enumerate(FOUNDATION_AXIS)}

    for node in _walk_ast(ast):
        kind = node.get("node")

        if kind == "StateLiteral":
            op = node.get("operator")
            if op in noetic_index:
                noetic[noetic_index[op]] += 1.0
            dom = node.get("domain")
            if dom in domain_index:
                domain[domain_index[dom]] += 1.0
            drv = node.get("drive")
            if isinstance(drv, str) and drv in drive_index:
                drive[drive_index[drv]] += 1.0
            for r in _collect_register_letters(node.get("register")):
                if r in register_index:
                    register[register_index[r]] += 1.0
            for r in _collect_register_letters(node.get("register_set")):
                if r in register_index:
                    register[register_index[r]] += 1.0
            for r in _collect_register_letters(node.get("drive_register")):
                if r in register_index:
                    register[register_index[r]] += 1.0
            for r in _collect_register_letters(node.get("drive_register_set")):
                if r in register_index:
                    register[register_index[r]] += 1.0

        elif kind == "DriveLiteral":
            drv = node.get("drive")
            if isinstance(drv, str) and drv in drive_index:
                drive[drive_index[drv]] += 1.0
            for r in _collect_register_letters(node.get("register")):
                if r in register_index:
                    register[register_index[r]] += 1.0
            for r in _collect_register_letters(node.get("register_set")):
                if r in register_index:
                    register[register_index[r]] += 1.0
            # F_k^D drive-in-domain shorthand contributes to the Domain
            # vector too: an explicitly domain-tagged drive expresses a
            # structural commitment to that domain, mirroring the
            # StateLiteral domain handling.
            dom = node.get("domain")
            if isinstance(dom, str) and dom in domain_index:
                domain[domain_index[dom]] += 1.0

        elif kind == "MetaSetLiteral":
            name = node.get("name")
            if isinstance(name, str) and name:
                metaset_counts[name] = metaset_counts.get(name, 0.0) + 1.0
                # Foundation axis: specific Foundation_k tokens fill their
                # exact slot; family-level tokens distribute one unit
                # uniformly across all 7 slots so two family references
                # match each other but only partially align with a
                # specific Foundation_k.
                if name in foundation_index:
                    foundation[foundation_index[name]] += 1.0
                elif name in _FOUNDATION_FAMILY_TOKENS:
                    share = 1.0 / len(FOUNDATION_AXIS)
                    for i in range(len(foundation)):
                        foundation[i] += share

        elif kind == "TypedMetaSetLiteral":
            ctor = node.get("constructor")
            if isinstance(ctor, str) and ctor:
                metaset_counts[ctor] = metaset_counts.get(ctor, 0.0) + 1.0
                if ctor in _FOUNDATION_FAMILY_TOKENS:
                    share = 1.0 / len(FOUNDATION_AXIS)
                    for i in range(len(foundation)):
                        foundation[i] += share
            # Elements are walked separately by _walk_ast (they are nested
            # dicts), so their StateLiteral / DriveLiteral counts are
            # picked up automatically without double-counting here.

        # FractalLiteral, RpmCall, RecipeLiteral, YieldExpression,
        # StateVectorLiteral, EmergentResult, etc. are walked through to
        # reach their inner StateLiteral / DriveLiteral / MetaSetLiteral
        # children. We do not add a dedicated dimension for them in
        # Sprint 1; see README.md "Out-of-Scope" for future work.

    return {
        "noetic": noetic,
        "domain": domain,
        "drive": drive,
        "register": register,
        "metaset": _metaset_vector_from_counts(metaset_counts),
        "foundation": foundation,
    }


def _metaset_vector_from_counts(counts: dict[str, float]) -> list[float]:
    """Materialize a name-sorted vector view of the metaset bag.

    The single-side vector is sorted alphabetically by name so callers
    inspecting it have a stable order. For pairwise cosine the caller
    should use :func:`_aligned_metaset_vectors` (which re-aligns over the
    union of names from both sides). The single-side vector is also valid
    input to :func:`cosine_similarity` when paired with another single-
    side vector OF THE SAME LENGTH (e.g. self-comparison).
    """

    return [counts[name] for name in sorted(counts)]


def _metaset_counts_from_features(
    artifact_dict: dict[str, Any],
) -> dict[str, float]:
    """Re-derive the metaset counts dict from a compiled-artifact dict.

    Used by :func:`cas_similarity` to align the two sides over the union
    of metaset names before computing cosine. Kept private; callers of
    :func:`extract_features` get the sorted per-side vector instead.
    """

    counts: dict[str, float] = {}
    if not artifact_dict.get("valid", False):
        return counts
    ast = artifact_dict.get("ast")
    if ast is None:
        return counts
    for node in _walk_ast(ast):
        kind = node.get("node")
        if kind == "MetaSetLiteral":
            name = node.get("name")
            if isinstance(name, str) and name:
                counts[name] = counts.get(name, 0.0) + 1.0
        elif kind == "TypedMetaSetLiteral":
            ctor = node.get("constructor")
            if isinstance(ctor, str) and ctor:
                counts[ctor] = counts.get(ctor, 0.0) + 1.0
    return counts


def _aligned_metaset_vectors(
    counts_a: dict[str, float], counts_b: dict[str, float]
) -> tuple[list[float], list[float]]:
    """Return two equal-length vectors over the union of metaset names."""

    names = sorted(set(counts_a) | set(counts_b))
    vec_a = [counts_a.get(name, 0.0) for name in names]
    vec_b = [counts_b.get(name, 0.0) for name in names]
    return vec_a, vec_b


def _is_zero_vec(vec: list[float]) -> bool:
    """True iff every entry is zero. Empty vectors count as zero."""

    return all(v == 0.0 for v in vec)


# ---------------------------------------------------------------------------
# Cosine
# ---------------------------------------------------------------------------


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity between two equal-length numeric vectors.

    Returns a value in ``[-1, 1]`` in general; for non-negative count
    vectors (the only inputs we produce) it is in ``[0, 1]``.

    Edge cases:

    - Mismatched lengths -> ``ValueError`` (programmer error).
    - Either vector all-zero -> ``0.0`` (no signal on this axis; we
      explicitly do NOT raise, because zero vectors are the natural
      result of a register-neutral CAS expression and the caller wants a
      defined value to fold into the weighted average).
    """

    if len(vec_a) != len(vec_b):
        raise ValueError(
            f"cosine_similarity: vectors have different lengths "
            f"({len(vec_a)} vs {len(vec_b)})"
        )
    if not vec_a:
        # Both empty -- conventionally undefined, choose 0.0 for the
        # weighted-average context (treat "no axis to compare on" as
        # contributing zero similarity rather than blowing up).
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def _apply_inversion_policy(
    noetic_vec: list[float], policy: str
) -> list[float]:
    """Optionally collapse involution pairs into shared slots.

    ``"neutral"`` (default) -- return the vector unchanged; involution
    pairs remain orthogonal axes.

    ``"merge"`` -- sum each involution pair into a single slot (still
    returned as a 10-dim vector for shape stability, with the partner
    slot zeroed out so dot-products line up).

    ``"penalize"`` -- not implemented as a vector transform; surfaced as
    a no-op here because the penalty is applied at the score-aggregation
    layer (see :func:`cas_similarity`). We accept the value for symmetry
    so the policy string is validated in one place.
    """

    if policy == "neutral":
        return list(noetic_vec)
    if policy == "merge":
        merged = list(noetic_vec)
        for left, right in _INVOLUTION_PAIRS:
            li = NOETIC_AXIS.index(left)
            ri = NOETIC_AXIS.index(right)
            total = merged[li] + merged[ri]
            merged[li] = total
            merged[ri] = 0.0
        return merged
    if policy == "penalize":
        return list(noetic_vec)
    raise ValueError(
        f"unknown inversion_policy: {policy!r} "
        "(expected 'neutral', 'merge', or 'penalize')"
    )


def _involution_pair_match(
    noetic_a: list[float], noetic_b: list[float]
) -> bool:
    """True when expressions reference partner Noetics across an involution pair.

    The Day 3 sprint Phase 1 cross-pair proximity boost fires when one
    expression activates a Noetic that's part of an involution pair AND
    the other expression activates the partner Noetic. The pairs are the
    canonical CAS involution pairs (CO-2/CO-3, CO-5/CO-6, CO-8/CO-9). This
    is a coarse "did the conversation cross the involution" detector --
    independent of the inversion_policy knob, which controls how the
    pairs are treated WITHIN the noetic-axis cosine score.

    Symmetric: ``_involution_pair_match(a, b) == _involution_pair_match(b, a)``.
    Returns False on identical-Noetic activations (both sides on the same
    side of the pair); only true cross-pair contact counts.
    """

    for left, right in _INVOLUTION_PAIRS:
        li = NOETIC_AXIS.index(left)
        ri = NOETIC_AXIS.index(right)
        a_left = noetic_a[li] > 0
        a_right = noetic_a[ri] > 0
        b_left = noetic_b[li] > 0
        b_right = noetic_b[ri] > 0
        # A on left and B on right, or vice versa.
        if (a_left and b_right) or (a_right and b_left):
            return True
    return False


def _inversion_penalty(
    noetic_a: list[float], noetic_b: list[float]
) -> float:
    """Coarse penalty when both sides have ONLY inverted partners.

    Applied only under ``inversion_policy="penalize"``. Returns a value
    in ``[0, 1]`` to subtract from the noetic-component score. Defaults
    to a small constant (0.25) per fully-inverted pair encountered, capped
    at 1.0. Sprint 1 keeps this deliberately simple; richer formulations
    are flagged as future work in README.md.
    """

    penalty = 0.0
    for left, right in _INVOLUTION_PAIRS:
        li = NOETIC_AXIS.index(left)
        ri = NOETIC_AXIS.index(right)
        # "Inverted" means side A activates left and side B activates
        # right (or vice versa) AND neither side has the matching slot.
        a_only_left = noetic_a[li] > 0 and noetic_a[ri] == 0
        a_only_right = noetic_a[ri] > 0 and noetic_a[li] == 0
        b_only_left = noetic_b[li] > 0 and noetic_b[ri] == 0
        b_only_right = noetic_b[ri] > 0 and noetic_b[li] == 0
        if (a_only_left and b_only_right) or (a_only_right and b_only_left):
            penalty += 0.25
    return min(penalty, 1.0)


def cas_similarity(
    expr_a: str,
    expr_b: str,
    *,
    weights: dict[str, float] | None = None,
    inversion_policy: str | None = None,
) -> dict[str, Any]:
    """Compile two CAS expressions and return a weighted cosine similarity.

    See module docstring and ``api/similarity/README.md`` for the full
    contract. Returns a dict with keys ``score``, ``breakdown``,
    ``weights``, ``valid_a``, ``valid_b``.
    """

    used_weights = dict(DEFAULT_WEIGHTS)
    if weights:
        for key, value in weights.items():
            if key in used_weights:
                used_weights[key] = float(value)
    policy = inversion_policy or DEFAULT_INVERSION_POLICY

    artifact_a = compile_expression(expr_a)
    artifact_b = compile_expression(expr_b)
    dict_a = artifact_a.to_dict()
    dict_b = artifact_b.to_dict()
    valid_a = bool(dict_a.get("valid"))
    valid_b = bool(dict_b.get("valid"))

    zero_breakdown = {
        "noetic": 0.0,
        "domain": 0.0,
        "drive": 0.0,
        "register": 0.0,
        "metaset": 0.0,
        "foundation": 0.0,
    }

    if not (valid_a and valid_b):
        return {
            "score": 0.0,
            "breakdown": zero_breakdown,
            "weights": used_weights,
            "valid_a": valid_a,
            "valid_b": valid_b,
        }

    feats_a = extract_features(dict_a)
    feats_b = extract_features(dict_b)

    noetic_a = _apply_inversion_policy(feats_a["noetic"], policy)
    noetic_b = _apply_inversion_policy(feats_b["noetic"], policy)
    noetic_score = cosine_similarity(noetic_a, noetic_b)
    if policy == "penalize":
        noetic_score = max(
            0.0, noetic_score - _inversion_penalty(noetic_a, noetic_b)
        )

    domain_score = cosine_similarity(feats_a["domain"], feats_b["domain"])
    drive_score = cosine_similarity(feats_a["drive"], feats_b["drive"])
    register_score = cosine_similarity(
        feats_a["register"], feats_b["register"]
    )

    counts_a = _metaset_counts_from_features(dict_a)
    counts_b = _metaset_counts_from_features(dict_b)
    aligned_a, aligned_b = _aligned_metaset_vectors(counts_a, counts_b)
    metaset_score = cosine_similarity(aligned_a, aligned_b)

    foundation_score = cosine_similarity(
        feats_a["foundation"], feats_b["foundation"]
    )

    breakdown = {
        "noetic": noetic_score,
        "domain": domain_score,
        "drive": drive_score,
        "register": register_score,
        "metaset": metaset_score,
        "foundation": foundation_score,
    }

    # Track which axes were "vacuous" -- both sides all-zero on that axis.
    # A vacuous axis is information-free agreement: both expressions made
    # the same (null) commitment on this axis. We exclude its weight from
    # the weighted average and renormalize so two identical register-
    # neutral expressions score 1.0, not 0.9. This matches the README's
    # contract: identical -> 1.0, completely different -> 0.0.
    vacuous: dict[str, bool] = {
        "noetic": _is_zero_vec(noetic_a) and _is_zero_vec(noetic_b),
        "domain": _is_zero_vec(feats_a["domain"])
        and _is_zero_vec(feats_b["domain"]),
        "drive": _is_zero_vec(feats_a["drive"])
        and _is_zero_vec(feats_b["drive"]),
        "register": _is_zero_vec(feats_a["register"])
        and _is_zero_vec(feats_b["register"]),
        "metaset": _is_zero_vec(aligned_a) and _is_zero_vec(aligned_b),
        "foundation": _is_zero_vec(feats_a["foundation"])
        and _is_zero_vec(feats_b["foundation"]),
    }
    active_weight_total = sum(
        w for axis, w in used_weights.items() if not vacuous[axis]
    )
    if active_weight_total > 0:
        score = sum(
            used_weights[k] * breakdown[k]
            for k in used_weights
            if not vacuous[k]
        ) / active_weight_total
    else:
        # Every axis is vacuous on both sides -- both expressions are
        # essentially "empty" structurally. Treat as identical.
        score = 1.0

    # Day 3 sprint Phase 1: cross-pair proximity boost. When one expression
    # activates a Noetic and the other activates its involution partner,
    # add INVOLUTION_PAIR_BOOST to the weighted-average score. This is
    # multiplicative-on-top, NOT part of the normalized axis weights, so
    # the boost still applies to expressions whose only signal is the
    # cross-pair contact. Final score is clamped to [0, 1].
    if _involution_pair_match(feats_a["noetic"], feats_b["noetic"]):
        score += INVOLUTION_PAIR_BOOST

    # Numerical safety: clamp to [0, 1].
    score = max(0.0, min(1.0, score))

    return {
        "score": score,
        "breakdown": breakdown,
        "weights": used_weights,
        "valid_a": valid_a,
        "valid_b": valid_b,
    }
