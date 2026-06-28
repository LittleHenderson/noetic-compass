"""Axis-rotation strategy for the dialectic orchestrator.

A "rotation" is a pair ``(AxisPriming_A, AxisPriming_B)`` describing two
opposed axis-stances for the two CAS-Native instances to assume on a
given turn. The dialectic orchestrator runs the predictor under each
priming and integrates the two outputs into a candidate Omega
(``Attractor``).

Four rotation libraries are predefined:

- ``ROTATION_NOETIC_INVOLUTION``  (involution pairs ^2/^3, ^5/^6, ^8/^9)
- ``ROTATION_DOMAIN``             (P vs O extremes of the precedence order)
- ``ROTATION_DRIVE_INVERSION``    (Drive inversion pairs F1/F7, F2/F6, F3/F5)
- ``ROTATION_REGISTER_INVERSION`` (T/E and A/f register oppositions)

Plus a ``select_rotations`` adaptive selector. Right now it returns the
first ``k`` rotations from a single library based on a coarse
query-content signal (which axis the rewrite_shim detects most strongly).
A learned classifier replaces this stub post-Lever-3.
"""

from __future__ import annotations

from typing import Optional

from .instance import AxisPriming


# --------------------------------------------------------------------------
# Rotation libraries
# --------------------------------------------------------------------------

# Noetic involution pairs (per CLAUDE.md): ^2<->^3, ^5<->^6, ^8<->^9.
# Self-duals (^0 ^1 ^4 ^7) deliberately not paired -- they have no
# polarity to rotate against. See CLAUDE.md "Structural invariants".
ROTATION_NOETIC_INVOLUTION: list[tuple[AxisPriming, AxisPriming]] = [
    (
        AxisPriming(noetic_bias=2, label="^2-positive"),
        AxisPriming(noetic_bias=3, label="^3-negative"),
    ),
    (
        AxisPriming(noetic_bias=5, label="^5-female"),
        AxisPriming(noetic_bias=6, label="^6-male"),
    ),
    (
        AxisPriming(noetic_bias=8, label="^8-cause"),
        AxisPriming(noetic_bias=9, label="^9-effect"),
    ),
]


# Domain rotation: P vs O are the precedence extremes. C vs E is a
# secondary midpoint contrast (Cognitive idea-handling vs Evaluative
# valence-assignment) that frequently splits otherwise-similar prompts.
ROTATION_DOMAIN: list[tuple[AxisPriming, AxisPriming]] = [
    (
        AxisPriming(domain_bias="P", label="^P-principled"),
        AxisPriming(domain_bias="O", label="^O-operational"),
    ),
    (
        AxisPriming(domain_bias="C", label="^C-cognitive"),
        AxisPriming(domain_bias="E", label="^E-evaluative"),
    ),
]


# Drive inversion pairs (per CLAUDE.md): F1<->F7, F2<->F6, F3<->F5.
# F4 is self-dual and excluded from rotation.
ROTATION_DRIVE_INVERSION: list[tuple[AxisPriming, AxisPriming]] = [
    (
        AxisPriming(drive_bias="F1", label="F1-unity"),
        AxisPriming(drive_bias="F7", label="F7-purpose"),
    ),
    (
        AxisPriming(drive_bias="F2", label="F2-wisdom"),
        AxisPriming(drive_bias="F6", label="F6-structure"),
    ),
    (
        AxisPriming(drive_bias="F3", label="F3-vitality"),
        AxisPriming(drive_bias="F5", label="F5-agency"),
    ),
]


# Register inversion pairs. The four CAS v7.5 registers don't have a
# canonical involution; we use the two natural oppositions:
# T (transcendent / abstract) vs E (embodied / concrete);
# A (analytical / explicit) vs f (affective / felt).
ROTATION_REGISTER_INVERSION: list[tuple[AxisPriming, AxisPriming]] = [
    (
        AxisPriming(register_bias="T", label="|T-transcendent"),
        AxisPriming(register_bias="E", label="|E-embodied"),
    ),
    (
        AxisPriming(register_bias="A", label="|A-analytical"),
        AxisPriming(register_bias="f", label="|f-affective"),
    ),
]


ALL_ROTATIONS: list[tuple[AxisPriming, AxisPriming]] = (
    ROTATION_NOETIC_INVOLUTION
    + ROTATION_DOMAIN
    + ROTATION_DRIVE_INVERSION
    + ROTATION_REGISTER_INVERSION
)


# --------------------------------------------------------------------------
# Adaptive selection (placeholder)
# --------------------------------------------------------------------------

def _detect_signal(query_text: str) -> dict[str, object]:
    """Best-effort axis detection on the query.

    Lazy-imports rewrite_shim so callers without torch can still import
    ``rotator`` and use the static rotation libraries directly.
    """
    try:
        from cas_native.inference.rewrite_shim import detect_cas_signal
    except Exception:
        # Fallback: empty signal.
        return {
            "noetic": None,
            "domain": None,
            "drive": None,
            "register": None,
            "has_signal": False,
        }
    return detect_cas_signal(query_text or "")


def select_rotations(
    query_text: str,
    k: int = 2,
    *,
    libraries: Optional[list[list[tuple[AxisPriming, AxisPriming]]]] = None,
) -> list[tuple[AxisPriming, AxisPriming]]:
    """Pick the top-K most relevant axis-rotations for ``query_text``.

    Strategy (PLACEHOLDER -- a learned classifier replaces this post-Lever-3):

    1. Detect the dominant CAS signal in the query via rewrite_shim.
    2. Rank rotation libraries by which axis the signal is strongest on:
       - strong noetic signal -> ROTATION_NOETIC_INVOLUTION first
       - strong drive signal -> ROTATION_DRIVE_INVERSION first
       - strong register signal -> ROTATION_REGISTER_INVERSION first
       - strong domain signal -> ROTATION_DOMAIN first
       - no signal -> fall through to default order
    3. Concatenate the libraries in the resulting priority order.
    4. Return the first ``k`` rotations.

    The default order, when no signal: NOETIC -> DOMAIN -> DRIVE -> REGISTER.
    This favours the most structurally load-bearing axis (Noetic) first.
    """
    if k < 1:
        return []

    libs = libraries if libraries is not None else [
        ROTATION_NOETIC_INVOLUTION,
        ROTATION_DOMAIN,
        ROTATION_DRIVE_INVERSION,
        ROTATION_REGISTER_INVERSION,
    ]

    signal = _detect_signal(query_text)

    # Priority based on which axis has highest confidence in the signal.
    priorities: list[tuple[float, list[tuple[AxisPriming, AxisPriming]]]] = []

    noetic_conf = float(signal.get("noetic_confidence", 0.0) or 0.0)
    domain_conf = float(signal.get("domain_confidence", 0.0) or 0.0)
    drive_conf = float(signal.get("drive_confidence", 0.0) or 0.0)
    register_conf = float(signal.get("register_confidence", 0.0) or 0.0)

    # Bind each library to its confidence; preserve original order on ties.
    bindings = [
        (noetic_conf, ROTATION_NOETIC_INVOLUTION),
        (domain_conf, ROTATION_DOMAIN),
        (drive_conf, ROTATION_DRIVE_INVERSION),
        (register_conf, ROTATION_REGISTER_INVERSION),
    ]

    # Match against the libraries the caller requested. Anything in
    # ``libs`` that isn't in our preset set is appended at the end with
    # zero priority.
    bound_ids = {id(b[1]) for b in bindings}
    augmented: list[tuple[float, list[tuple[AxisPriming, AxisPriming]]]] = []
    for conf, lib in bindings:
        if any(lib is requested for requested in libs):
            augmented.append((conf, lib))
    for requested in libs:
        if id(requested) not in bound_ids:
            augmented.append((0.0, requested))

    augmented.sort(key=lambda kv: kv[0], reverse=True)

    flat: list[tuple[AxisPriming, AxisPriming]] = []
    for _conf, lib in augmented:
        flat.extend(lib)

    return flat[:k]


def list_all_rotation_labels() -> list[str]:
    """Diagnostic helper: every rotation we know about, by short label."""
    return [
        f"{a.short_label()} vs {b.short_label()}"
        for a, b in ALL_ROTATIONS
    ]


__all__ = [
    "ALL_ROTATIONS",
    "ROTATION_DOMAIN",
    "ROTATION_DRIVE_INVERSION",
    "ROTATION_NOETIC_INVOLUTION",
    "ROTATION_REGISTER_INVERSION",
    "list_all_rotation_labels",
    "select_rotations",
]
