"""Canonical 2D coordinate system for CAS primitives.

This module is Stage 23.A / 23.A.2 — the static foundation underneath
any future "CAS Native reads its own Idea Atlas" capability.

Coverage (Stage 23.A + 23.A.2 = 157 primitives total):
  Stage 23.A (65):
    - 10 Noetics
    - 4 Domains
    - 7 Drives
    - 4 Registers
    - 40 Cognitive States (Noetic × Domain)
  Stage 23.A.2 (92):
    - 5 Generative Operations (×, ÷, ∘, +, −)
    - 7 Inversion Axes (Inv:N, Inv:W, Inv:F, Inv:P, Inv:E, Inv:S, Inv:A)
    - 28 Foundations (Drive × Register: F1^T … F7^E)
    - 5 Production primitives (Θ, Λ, η, κ, ι) — CAS v7.6 stoichiometry
    - 22 RPM chain positions (A0 + D1-D7 + W1-W7 + P1-P7)
    - 4 Set constructors (NoeticCluster, StateCluster, StateVariantCluster,
      RelationCluster)
    - 6 Set relations (∈, ∉, ⊂, ⊆, ⊃, ⊇)
    - 4 Set operations (∪, ∩, ∖, ∅)
    - 4 Combinators (Product, CoverOf, PartitionOf, Pullback)
    - 5 Authority sets (SystemInstructionSet, UserUtteranceSet,
      ToolObservationSet, ValidatedClaimSet, RenderedResponseSet)
    - 2 Cardinality kind markers (Cardinality, OrderedTuple)

Properties enforced by tests:
- Noetic involution pairs reflect across the origin; Drive involution
  pairs reflect across x=0.
- Self-dual primitives lie on a symmetry axis.
- Domain precedence P ≻ C ≻ E ≻ O is spatially monotone.
- Every position is unique across all 157 primitives.
- Layout is deterministic across calls / processes / machines.

This module does NOT:
- Modify any existing atlas or trace code.
- Introduce a learned parameter or tensor.
- Claim to be an optimal attention prior. That is a future empirical
  question (Stage 23.B/C/D), not declared here.
- Enumerate "12 Ω_* emergent registers" — that group is intentionally
  excluded pending canonical enumeration.

See `research/cas_probe/STAGE23_ATLAS_SELF_READING_PREREG_20260519.md`
and `STAGE23_A_2_NOTATION_MAP_EXTENSION_20260519.md` for the design
boundary docs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


LAYOUT_VERSION = "stage23a2_notation_2d_layout_v2"


# ── Primitive identifiers ─────────────────────────────────────────────

NOETICS: tuple[str, ...] = ("^0", "^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9")
# Domains and Registers use canonical prefixed forms because the bare letter
# "E" is ambiguous (Evaluative Domain vs. Embodied Register).  In CAS notation
# `^P` denotes a Domain and `|R` a Register; we use those prefixes here as the
# canonical primitive ids and avoid bare letters in any public enumeration.
DOMAINS: tuple[str, ...] = ("^P", "^C", "^E", "^O")
DRIVES: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
REGISTERS: tuple[str, ...] = ("|T", "|A", "|f", "|E")

# Involution structure (canonical CAS v7.7).
NOETIC_INVOLUTIONS: dict[str, str] = {
    "^2": "^3", "^3": "^2",
    "^5": "^6", "^6": "^5",
    "^8": "^9", "^9": "^8",
}
NOETIC_SELF_DUALS: tuple[str, ...] = ("^0", "^1", "^4", "^7")

DRIVE_INVOLUTIONS: dict[str, str] = {
    "F1": "F7", "F7": "F1",
    "F2": "F6", "F6": "F2",
    "F3": "F5", "F5": "F3",
}
DRIVE_SELF_DUALS: tuple[str, ...] = ("F4",)

# Domain total order (P most-precedent, O least).
DOMAIN_ORDER: dict[str, int] = {"P": 0, "C": 1, "E": 2, "O": 3}


PrimitiveKind = Literal[
    # Stage 23.A
    "noetic",
    "domain",
    "drive",
    "register",
    "cognitive_state",
    # Stage 23.A.2
    "operation",
    "inversion_axis",
    "foundation",
    "production",
    "rpm_pathway",
    "set_constructor",
    "set_relation",
    "set_operation",
    "combinator",
    "authority_set",
    "cardinality_kind",
]


@dataclass(frozen=True)
class Position2D:
    """Canonical 2D coordinate for a CAS primitive."""

    primitive: str
    kind: PrimitiveKind
    x: float
    y: float

    def as_dict(self) -> dict[str, str | float]:
        return {
            "primitive": self.primitive,
            "kind": self.kind,
            "x": round(self.x, 9),
            "y": round(self.y, 9),
        }


# ── Layout design ─────────────────────────────────────────────────────
#
# Noetics live on a unit circle.  The four self-duals sit on the
# cardinal axes:
#     ^0 Idea          at  ( 0,  1)   — north pole, the identity / root
#     ^4 Vibration     at  ( 1,  0)   — east, the "impression" axis
#     ^1 Mind          at  ( 0, -1)   — south, the "awareness" axis
#     ^7 Rhythm        at  (-1,  0)   — west, the "conditioning" axis
# The three involution pairs sit reflection-symmetric across the origin
# in the four diagonal quadrants:
#     ^2 Positive  at NE, ^3 Negative at SW   (attraction ↔ aversion)
#     ^5 Female    at NW, ^6 Male     at SE   (Mind composed ↔ Idea composed)
#     ^8 Above/Cause at SW-of-NE, ^9 Below/Effect at NE-of-SW
# Concretely we use the angle map below.
NOETIC_ANGLE_DEG: dict[str, float] = {
    "^0": 90.0,    # North (self-dual)
    "^2": 45.0,    # NE
    "^4": 0.0,     # East (self-dual)
    "^9": -22.5,   # ESE
    "^6": -67.5,   # SSE
    "^1": -90.0,   # South (self-dual)  ⟂  ^0
    "^3": -135.0,  # SW                  ⟂  ^2
    "^7": 180.0,   # West (self-dual)
    "^8": 157.5,   # WNW                 ⟂  ^9
    "^5": 112.5,   # NNW                 ⟂  ^6
}

# Domain layers are stacked vertically below the Noetic ring.
# P (most precedent) is highest; O (least precedent) is lowest.
DOMAIN_Y: dict[str, float] = {
    "P": -2.0,
    "C": -3.0,
    "E": -4.0,
    "O": -5.0,
}
DOMAIN_X: float = 0.0  # Domains form a vertical column on the centerline.

# Drives sit on their own row above the Domain stack but below the Noetic
# ring. Involution pairs sit symmetric about x=0; F4 self-dual sits at x=0.
DRIVE_Y: float = -1.5
DRIVE_X: dict[str, float] = {
    "F4": 0.0,
    "F3": -0.5,
    "F5": 0.5,
    "F2": -1.0,
    "F6": 1.0,
    "F1": -1.5,
    "F7": 1.5,
}

# Registers sit on a small row below the Domain stack.
REGISTER_Y: float = -6.0
REGISTER_X: dict[str, float] = {
    "T": -1.5,  # Transcendent — leftmost
    "A": -0.5,  # Analytical
    "f": 0.5,   # Affective
    "E": 1.5,   # Embodied  — rightmost
}

# Cognitive States (Noetic × Domain) sit at the same x as the Noetic and
# the same y as the Domain — a 10 × 4 product grid offset from the Noetic
# ring.  Each cell is unique by construction.

# ── Stage 23.A.2 additions ────────────────────────────────────────────

# 5 Generative Operations live on a row above the Noetic ring.
# ∘ (composition) is the "neutral" self-dual op at x=0; × ↔ ÷ and + ↔ −
# sit at conventional algebraic-inverse positions (not asserted as a
# CAS-specific involution, just clean symmetry).
OPERATIONS: tuple[str, ...] = ("×", "÷", "∘", "+", "−")
OPERATION_Y: float = 2.5
OPERATION_X: dict[str, float] = {
    "∘": 0.0,
    "×": -1.0,
    "÷": 1.0,
    "+": -2.0,
    "−": 2.0,
}

# 7 Inversion Axes (CAS v7.4 / CLAUDE.md): N, W, F, E, S, A atomic,
# P compound. Canonical ids use 'Inv:' prefix to avoid collision with
# bare letters used by Domain / Register / Drive / RPM-chain primitives.
INVERSION_AXES: tuple[str, ...] = (
    "Inv:N", "Inv:W", "Inv:F", "Inv:P", "Inv:E", "Inv:S", "Inv:A",
)
INVERSION_X: float = -4.0
INVERSION_Y: dict[str, float] = {
    "Inv:N": 1.5,
    "Inv:W": 1.0,
    "Inv:F": 0.5,
    "Inv:P": 0.0,   # Compound — centered
    "Inv:E": -0.5,
    "Inv:S": -1.0,
    "Inv:A": -1.5,
}

# 28 Foundations: Drive × Register grid. Lives ABOVE the Noetic ring at
# y ∈ [3.0, 4.5]. Foundation Fk^R has x = DRIVE_X[Fk] and y = a register-
# specific row. Vertical neighbors share Drive, horizontal share Register.
FOUNDATION_REGISTER_Y: dict[str, float] = {
    "T": 4.5,
    "A": 4.0,
    "f": 3.5,
    "E": 3.0,
}

# 5 Production primitives (CAS v7.6 stoichiometry). Above the Foundation
# grid, y = 5.5, x ∈ [-2, 2].
PRODUCTION_PRIMITIVES: tuple[str, ...] = ("Θ", "Λ", "η", "κ", "ι")
PRODUCTION_Y: float = 5.5
PRODUCTION_X: dict[str, float] = {
    "Θ": -2.0,  # Recipe — leftmost
    "Λ": -1.0,  # Leakage / Side-Reaction
    "η": 0.0,   # Production Efficiency — center
    "κ": 1.0,   # Catalyst
    "ι": 2.0,   # Inhibitor — rightmost
}

# 22 RPM chain positions: A0 + D1-D7 + W1-W7 + P1-P7.
# Bottom of canvas, stacked rows reflecting the section-retraction chain
# A0 → Dn → Wn → Pn → outcome.
RPM_A0_POSITION: tuple[float, float] = (0.0, -8.0)
RPM_D_Y: float = -8.5
RPM_W_Y: float = -9.0
RPM_P_Y: float = -9.5
# 7 x-positions for D/W/P rows: evenly spaced columns at -3, -2, ..., 3.
RPM_COLUMN_X: dict[int, float] = {i: -3.0 + (i - 1) * 1.0 for i in range(1, 8)}

# 4 Set constructors — 2×2 cluster to the right of Cognitive States.
SET_CONSTRUCTORS: tuple[str, ...] = (
    "NoeticCluster", "StateCluster", "StateVariantCluster", "RelationCluster",
)
SET_CONSTRUCTOR_POSITION: dict[str, tuple[float, float]] = {
    "NoeticCluster":       (6.0,  1.0),
    "StateCluster":        (7.0,  1.0),
    "StateVariantCluster": (6.0,  0.0),
    "RelationCluster":     (7.0,  0.0),
}

# 6 Set relations — row at y=2.0 right of constructors.
SET_RELATIONS: tuple[str, ...] = ("∈", "∉", "⊂", "⊆", "⊃", "⊇")
SET_RELATION_Y: float = 2.0
SET_RELATION_X: dict[str, float] = {
    "∈": 6.0,
    "∉": 6.5,
    "⊂": 7.0,
    "⊆": 7.5,
    "⊃": 8.0,
    "⊇": 8.5,
}

# 4 Set operations — row at y=-1.0. ∅ "as origin" of the set-op subspace,
# ∪ ↔ ∩ paired, ∖ offset.
SET_OPERATIONS: tuple[str, ...] = ("∪", "∩", "∖", "∅")
SET_OPERATION_Y: float = -1.0
SET_OPERATION_X: dict[str, float] = {
    "∅": 6.0,
    "∪": 7.0,
    "∩": 8.0,
    "∖": 9.0,
}

# 4 Combinators — column at x=10, ordered by compositional depth.
COMBINATORS: tuple[str, ...] = ("Product", "CoverOf", "PartitionOf", "Pullback")
COMBINATOR_X: float = 10.0
COMBINATOR_Y: dict[str, float] = {
    "Product":      1.5,  # Simplest
    "CoverOf":      0.5,
    "PartitionOf": -0.5,
    "Pullback":    -1.5,  # Most complex
}

# 5 Authority sets — column at x=11, ordered by trust level (highest top).
AUTHORITY_SETS: tuple[str, ...] = (
    "SystemInstructionSet",
    "UserUtteranceSet",
    "ToolObservationSet",
    "ValidatedClaimSet",
    "RenderedResponseSet",
)
AUTHORITY_X: float = 11.0
AUTHORITY_Y: dict[str, float] = {
    "SystemInstructionSet":  2.0,
    "UserUtteranceSet":      1.0,
    "ToolObservationSet":    0.0,
    "ValidatedClaimSet":    -1.0,
    "RenderedResponseSet":  -2.0,
}

# 2 Cardinality kind markers — these are form markers (any primitive can
# be wrapped in `|X|` or `<a,b,c>`), but we expose canonical positions so
# encoders can attend to "this is a cardinality form" vs "this is a tuple
# form" regardless of inner content. Far right at x=12.
CARDINALITY_KINDS: tuple[str, ...] = ("Cardinality", "OrderedTuple")
CARDINALITY_POSITION: dict[str, tuple[float, float]] = {
    "Cardinality":  (12.0,  0.5),
    "OrderedTuple": (12.0, -0.5),
}


def _noetic_position(noetic: str) -> tuple[float, float]:
    """Return (x, y) on the unit circle for a Noetic."""
    if noetic not in NOETIC_ANGLE_DEG:
        raise KeyError(f"Unknown Noetic: {noetic!r}")
    angle_rad = math.radians(NOETIC_ANGLE_DEG[noetic])
    return (math.cos(angle_rad), math.sin(angle_rad))


def state_id(noetic: str, domain: str) -> str:
    """Canonical id for a Cognitive State.

    Returns the 4-character '^n^D' form (matches CAS expression notation
    like '^3^P'). Accepts the domain as either bare ('P') or prefixed
    ('^P').
    """
    d = domain[1:] if domain.startswith("^") else domain
    return f"{noetic}^{d}"


def _cognitive_state_position(noetic: str, domain: str) -> tuple[float, float]:
    """Position for a 40-element Cognitive State (Noetic × Domain).

    Cognitive States form a 10 × 4 grid offset to the right of the main
    Noetic ring so they don't visually collide with the ring primitives.
    Each row is one Noetic; each column is one Domain.
    """
    if noetic not in NOETIC_ANGLE_DEG:
        raise KeyError(f"Unknown Noetic: {noetic!r}")
    if domain not in DOMAIN_ORDER:
        raise KeyError(f"Unknown Domain: {domain!r}")
    # 10 rows (Noetics ordered by index ^0..^9), 4 columns (Domains by precedence).
    noetic_index = int(noetic[1:])
    domain_index = DOMAIN_ORDER[domain]
    # Grid origin offset to the right of the Noetic ring.
    grid_origin_x = 3.0
    grid_origin_y = 2.0
    x = grid_origin_x + domain_index * 0.5
    y = grid_origin_y - noetic_index * 0.5
    return (x, y)


def get_position(primitive: str) -> Position2D:
    """Return the canonical Position2D for one CAS primitive.

    Accepted primitive ids (canonical forms, always prefixed):
      - Noetics: '^0' .. '^9'
      - Domains: '^P', '^C', '^E', '^O'
      - Drives: 'F1' .. 'F7'
      - Registers: '|T', '|A', '|f', '|E'
      - Cognitive States: '^nD' for n in 0..9 and D in P/C/E/O, e.g. '^3P'

    Convenience: bare unambiguous letters are accepted ('P', 'C', 'O' for
    Domain; 'T', 'A', 'f' for Register; 'F1'..'F7' for Drive). Bare 'E' is
    rejected because it could mean Evaluative Domain or Embodied Register;
    use '^E' or '|E' explicitly.
    """
    # Cognitive State. Two accepted forms:
    #   '^n^D' (4-char canonical, matches CAS notation: '^3^P')
    #   '^nD'  (3-char compact: '^3P')
    # The canonical 4-char form is emitted on output.
    if (
        len(primitive) == 4
        and primitive.startswith("^")
        and primitive[1].isdigit()
        and primitive[2] == "^"
        and primitive[3] in DOMAIN_ORDER
    ):
        n, d = primitive[:2], primitive[3]
        if n in NOETIC_ANGLE_DEG:
            x, y = _cognitive_state_position(n, d)
            return Position2D(primitive=f"{n}^{d}", kind="cognitive_state", x=x, y=y)
    if (
        len(primitive) == 3
        and primitive.startswith("^")
        and primitive[1].isdigit()
        and primitive[2] in DOMAIN_ORDER
    ):
        n, d = primitive[:2], primitive[2]
        if n in NOETIC_ANGLE_DEG:
            x, y = _cognitive_state_position(n, d)
            # Emit canonical 4-char form even when input was 3-char compact.
            return Position2D(primitive=f"{n}^{d}", kind="cognitive_state", x=x, y=y)
    # Domain (canonical '^P', '^C', '^E', '^O').
    if (
        len(primitive) == 2
        and primitive.startswith("^")
        and primitive[1] in DOMAIN_ORDER
    ):
        d = primitive[1]
        return Position2D(primitive=f"^{d}", kind="domain", x=DOMAIN_X, y=DOMAIN_Y[d])
    # Register (canonical '|T', '|A', '|f', '|E').
    if primitive.startswith("|") and primitive[1:] in REGISTER_X:
        r = primitive[1:]
        return Position2D(
            primitive=f"|{r}", kind="register", x=REGISTER_X[r], y=REGISTER_Y
        )
    # Noetic ('^0' .. '^9').
    if primitive in NOETIC_ANGLE_DEG:
        x, y = _noetic_position(primitive)
        return Position2D(primitive=primitive, kind="noetic", x=x, y=y)
    # Drive ('F1' .. 'F7').
    if primitive in DRIVE_X:
        return Position2D(
            primitive=primitive, kind="drive", x=DRIVE_X[primitive], y=DRIVE_Y
        )
    # Bare Domain letter (unambiguous: P, C, O).
    if primitive in ("P", "C", "O"):
        return Position2D(
            primitive=f"^{primitive}", kind="domain",
            x=DOMAIN_X, y=DOMAIN_Y[primitive],
        )
    # Bare Register letter (unambiguous: T, A, f).
    if primitive in ("T", "A", "f"):
        return Position2D(
            primitive=f"|{primitive}", kind="register",
            x=REGISTER_X[primitive], y=REGISTER_Y,
        )
    # Bare 'E' is ambiguous — refuse cleanly so callers learn to qualify.
    if primitive == "E":
        raise ValueError(
            "'E' is ambiguous: use '^E' for the Evaluative Domain or "
            "'|E' for the Embodied Register."
        )

    # ── Stage 23.A.2 primitive dispatch ─────────────────────────────────

    # Generative Operations (×, ÷, ∘, +, −).
    if primitive in OPERATION_X:
        return Position2D(
            primitive=primitive, kind="operation",
            x=OPERATION_X[primitive], y=OPERATION_Y,
        )
    # Inversion Axes (canonical 'Inv:N' ... 'Inv:P').
    if primitive in INVERSION_Y:
        return Position2D(
            primitive=primitive, kind="inversion_axis",
            x=INVERSION_X, y=INVERSION_Y[primitive],
        )
    # Foundations: 'Fk^R' for k in 1..7, R in T/A/f/E. Matches Drive x and
    # Register-row y.
    if (
        len(primitive) == 4
        and primitive.startswith("F")
        and primitive[1].isdigit()
        and primitive[2] == "^"
        and primitive[3] in FOUNDATION_REGISTER_Y
    ):
        drive_id = primitive[:2]
        register = primitive[3]
        if drive_id in DRIVE_X:
            return Position2D(
                primitive=primitive, kind="foundation",
                x=DRIVE_X[drive_id], y=FOUNDATION_REGISTER_Y[register],
            )
    # Production primitives (Θ, Λ, η, κ, ι).
    if primitive in PRODUCTION_X:
        return Position2D(
            primitive=primitive, kind="production",
            x=PRODUCTION_X[primitive], y=PRODUCTION_Y,
        )
    # RPM chain — A0.
    if primitive == "A0":
        return Position2D(
            primitive=primitive, kind="rpm_pathway",
            x=RPM_A0_POSITION[0], y=RPM_A0_POSITION[1],
        )
    # RPM chain — Dk / Wk / Pk for k in 1..7.
    if (
        len(primitive) == 2
        and primitive[0] in ("D", "W", "P")
        and primitive[1].isdigit()
        and 1 <= int(primitive[1]) <= 7
    ):
        row, idx = primitive[0], int(primitive[1])
        y = {"D": RPM_D_Y, "W": RPM_W_Y, "P": RPM_P_Y}[row]
        return Position2D(
            primitive=primitive, kind="rpm_pathway",
            x=RPM_COLUMN_X[idx], y=y,
        )
    # Set constructors.
    if primitive in SET_CONSTRUCTOR_POSITION:
        x, y = SET_CONSTRUCTOR_POSITION[primitive]
        return Position2D(
            primitive=primitive, kind="set_constructor", x=x, y=y,
        )
    # Set relations.
    if primitive in SET_RELATION_X:
        return Position2D(
            primitive=primitive, kind="set_relation",
            x=SET_RELATION_X[primitive], y=SET_RELATION_Y,
        )
    # Set operations.
    if primitive in SET_OPERATION_X:
        return Position2D(
            primitive=primitive, kind="set_operation",
            x=SET_OPERATION_X[primitive], y=SET_OPERATION_Y,
        )
    # Combinators.
    if primitive in COMBINATOR_Y:
        return Position2D(
            primitive=primitive, kind="combinator",
            x=COMBINATOR_X, y=COMBINATOR_Y[primitive],
        )
    # Authority sets.
    if primitive in AUTHORITY_Y:
        return Position2D(
            primitive=primitive, kind="authority_set",
            x=AUTHORITY_X, y=AUTHORITY_Y[primitive],
        )
    # Cardinality kind markers.
    if primitive in CARDINALITY_POSITION:
        x, y = CARDINALITY_POSITION[primitive]
        return Position2D(
            primitive=primitive, kind="cardinality_kind", x=x, y=y,
        )

    raise KeyError(f"Unknown primitive: {primitive!r}")


def all_positions() -> list[Position2D]:
    """Return Position2D for every primitive the layout covers.

    Enumerates in canonical form. No coordinate collisions across all
    157 primitives (Stage 23.A: 65, Stage 23.A.2: 92).
    """
    out: list[Position2D] = []
    # Stage 23.A primitives.
    for n in NOETICS:
        out.append(get_position(n))
    for d in DOMAINS:
        out.append(get_position(d))
    for f in DRIVES:
        out.append(get_position(f))
    for r in REGISTERS:
        out.append(get_position(r))
    for n in NOETICS:
        for d in DOMAINS:
            out.append(get_position(state_id(n, d)))
    # Stage 23.A.2 primitives.
    for op in OPERATIONS:
        out.append(get_position(op))
    for ax in INVERSION_AXES:
        out.append(get_position(ax))
    for drive_id in DRIVES:
        for reg in ("T", "A", "f", "E"):
            out.append(get_position(f"{drive_id}^{reg}"))
    for prod in PRODUCTION_PRIMITIVES:
        out.append(get_position(prod))
    out.append(get_position("A0"))
    for row in ("D", "W", "P"):
        for i in range(1, 8):
            out.append(get_position(f"{row}{i}"))
    for ctor in SET_CONSTRUCTORS:
        out.append(get_position(ctor))
    for rel in SET_RELATIONS:
        out.append(get_position(rel))
    for op in SET_OPERATIONS:
        out.append(get_position(op))
    for comb in COMBINATORS:
        out.append(get_position(comb))
    for auth in AUTHORITY_SETS:
        out.append(get_position(auth))
    for card in CARDINALITY_KINDS:
        out.append(get_position(card))
    return out


def canonical_layout_payload() -> dict[str, object]:
    """Machine-readable layout artifact (committed to research/cas_probe/)."""
    return {
        "layout_version": LAYOUT_VERSION,
        "scope": "stage_23_a_and_23_a_2_static_foundation",
        "boundary": (
            "Static canonical 2D positions for CAS primitives across both "
            "Stage 23.A (Noetics/Domains/Drives/Registers/Cognitive States) "
            "and Stage 23.A.2 (Operations / Inversion Axes / Foundations / "
            "Production / RPM / Set primitives / Combinators / Authority "
            "Sets / Cardinality kinds). Does not include atlas-self-reading, "
            "encoder design, or training signal."
        ),
        "primitives": [p.as_dict() for p in all_positions()],
    }
