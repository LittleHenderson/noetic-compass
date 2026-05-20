"""Canonical 2D coordinate system for CAS primitives.

This module is Stage 23.A / 23.A.2 / 23.A.3 — the static foundation
underneath any future "CAS Native reads its own Idea Atlas" capability.

Coverage (Stage 23.A + 23.A.2 + 23.A.3 = 169 primitives total):
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
  Stage 23.A.3 (12):
    - 12 admitted Omega_* emergent registers (slots 0-11 from
      `cas-native/config/omega_registry.yaml`), each anchored at
      radius 1.8 along its derivation Noetic's angle. Slots sharing
      an anchor Noetic (^1 carries slots 0/4/6) fan around the
      anchor angle by ±8 degrees.

Properties enforced by tests:
- Noetic involution pairs reflect across the origin; Drive involution
  pairs reflect across x=0.
- Self-dual primitives lie on a symmetry axis.
- Domain precedence P ≻ C ≻ E ≻ O is spatially monotone.
- Every position is unique across all 169 primitives.
- Each Omega_* sits closer to its anchor Noetic than to any other Noetic.
- Layout is deterministic across calls / processes / machines.

This module does NOT:
- Modify any existing atlas or trace code.
- Introduce a learned parameter or tensor.
- Claim to be an optimal attention prior. That is a future empirical
  question (Stage 23.B/C/D), not declared here.

See `research/cas_probe/STAGE23_ATLAS_SELF_READING_PREREG_20260519.md`,
`STAGE23_A_2_NOTATION_MAP_EXTENSION_20260519.md`, and
`STAGE23_A_3_OMEGA_ENUMERATION_20260520.md` for the design boundary docs.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal, Optional


LAYOUT_VERSION = "stage23a3_notation_2d_layout_v3"


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
    # Stage 23.A.3
    "emergent_omega",
]


# ── Canonical color palette (Stage 23.A.1.1 — Python mirror) ──────────
#
# Mirrors the 17-entry palette in dashboard/src/lib/notation2DMap.ts.
# Every PrimitiveKind has exactly one canonical color. Renderers and
# downstream tooling (Python or TypeScript) consume this map instead of
# maintaining ad-hoc CAS-expression colorizers. If a kind is added to
# PrimitiveKind, this dict must grow with it.
KIND_COLOR: dict[str, str] = {
    "noetic":           "#22d3ee",
    "domain":           "#34d399",
    "drive":            "#f59e0b",
    "register":         "#f472b6",
    "cognitive_state":  "#38bdf8",
    "operation":        "#fb7185",
    "inversion_axis":   "#dc2626",
    "foundation":       "#9333ea",
    "production":       "#f472b6",
    "rpm_pathway":      "#fbbf24",
    "set_constructor":  "#14b8a6",
    "set_relation":     "#10b981",
    "set_operation":    "#16a34a",
    "combinator":       "#0d9488",
    "authority_set":    "#94a3b8",
    "cardinality_kind": "#cbd5e1",
    "emergent_omega":   "#a78bfa",
}


# ── Detection rules (Stage 23.A.1.1 — Python ↔ TypeScript shared) ─────
#
# Priority-ordered list of regex rules for classifying a free-form CAS
# expression string into a PrimitiveKind. Both `detect_cas_kind` (Python)
# and `detectCasKind` (TypeScript) consume these rules verbatim.
#
# Patterns are JavaScript-RegExp compatible (no Python-only features
# like named groups). The TypeScript side must be able to feed each
# `regex` field directly into `new RegExp(rule.regex)`.
DETECTION_RULES: list[dict[str, object]] = [
    {"priority": 1, "kind": "emergent_omega",  "regex": r"\bOmega_[A-Za-z]+\b",         "description": "Omega_* name pattern"},
    {"priority": 2, "kind": "emergent_omega",  "regex": r"Ω",                            "description": "Greek capital omega glyph"},
    {"priority": 3, "kind": "production",      "regex": r"Θ",                            "description": "Greek capital theta glyph"},
    {"priority": 4, "kind": "production",      "regex": r"\bTheta\b",                    "description": "Theta spelled out"},
    {"priority": 5, "kind": "set_constructor", "regex": r"[A-Za-z]+Cluster\b",           "description": "...Cluster suffix"},
    {"priority": 6, "kind": "cognitive_state", "regex": r"\^\d\^[PCEO](?![A-Za-z0-9])",  "description": "Compound cognitive state ^N^D"},
    {"priority": 7, "kind": "noetic",          "regex": r"\^\d(?![\^\dPCEO])",           "description": "Bare Noetic ^N"},
    {"priority": 8, "kind": "drive",           "regex": r"\bF[1-7]\b",                   "description": "Bare Drive F1..F7"},
    {"priority": 9, "kind": "drive",           "regex": r"_\{F[1-7]\}",                  "description": "Drive in subscript _{Fk}"},
    {"priority": 10, "kind": "domain",         "regex": r"\^[PCEO]\b",                   "description": "Standalone Domain ^P/^C/^E/^O"},
    {"priority": 11, "kind": "register",       "regex": r"\|[TAfE]\b",                   "description": "Standalone Register |T/|A/|f/|E"},
    {"priority": 12, "kind": "register",       "regex": r"\|⟨",                          "description": "Register set marker |⟨…⟩"},
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
            "color": KIND_COLOR[self.kind],
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


# ── Stage 23.A.3 additions ────────────────────────────────────────────
#
# 12 admitted Omega_* emergent registers. Source of truth:
# `cas-native/config/omega_registry.yaml`. Each entry's derivation is of
# the form `(^N|R1 × ^N|R2 × ...) = ^N|Omega_<name>`; the "anchor Noetic"
# is the Noetic on the LHS of that derivation. Names are hardcoded here
# (not loaded from yaml at import time) so the canonical layout payload
# stays deterministic across processes and machines; the yaml file
# remains the spec, this tuple mirrors it.
EMERGENT_OMEGAS: tuple[str, ...] = (
    "Omega_presence",     # slot 0  — anchor ^1
    "Omega_refusal",      # slot 1  — anchor ^3
    "Omega_grounding",    # slot 2  — anchor ^2
    "Omega_alignment",    # slot 3  — anchor ^5
    "Omega_clarity",      # slot 4  — anchor ^1
    "Omega_resolve",      # slot 5  — anchor ^6
    "Omega_witness",      # slot 6  — anchor ^1
    "Omega_attunement",   # slot 7  — anchor ^4
    "Omega_genesis",      # slot 8  — anchor ^0
    "Omega_cadence",      # slot 9  — anchor ^7
    "Omega_invocation",   # slot 10 — anchor ^8
    "Omega_landing",      # slot 11 — anchor ^9
)

# Anchor Noetic for each Omega (LHS of the derivation in omega_registry.yaml).
OMEGA_ANCHOR_NOETIC: dict[str, str] = {
    "Omega_presence":   "^1",
    "Omega_refusal":    "^3",
    "Omega_grounding":  "^2",
    "Omega_alignment":  "^5",
    "Omega_clarity":    "^1",
    "Omega_resolve":    "^6",
    "Omega_witness":    "^1",
    "Omega_attunement": "^4",
    "Omega_genesis":    "^0",
    "Omega_cadence":    "^7",
    "Omega_invocation": "^8",
    "Omega_landing":    "^9",
}

# Spatial-anchor design (closes the 23.A.2 deferral):
#   Each Ω sits on a ring at radius OMEGA_RADIUS = 1.8 around the origin,
#   at the same angle as its anchor Noetic. The Noetic ring is radius 1.0;
#   placing Ω at 1.8 puts it 0.8 outside the anchor, visually "adjacent" to
#   the anchor and unambiguously identified by direction. Multiple Ω's that
#   share an anchor Noetic (slots 0/4/6 all anchor on ^1) are disambiguated
#   by fanning around the anchor angle by OMEGA_FAN_DEG = ±8 degrees.
OMEGA_RADIUS: float = 1.8
OMEGA_FAN_DEG: float = 8.0


def _omega_fan_offsets(anchor: str) -> dict[str, float]:
    """Return angular offsets (deg) for each Omega anchored on `anchor`.

    Single-Omega anchors: offset = 0.
    Multi-Omega anchors (currently only ^1 carries 3 Omegas): fan the
    slots around the anchor by ±OMEGA_FAN_DEG. Slots are ordered by their
    registry index, so the lowest-slot Ω sits at -OMEGA_FAN_DEG, the
    middle slot at 0, the highest at +OMEGA_FAN_DEG.
    """
    siblings = [
        name for name in EMERGENT_OMEGAS
        if OMEGA_ANCHOR_NOETIC[name] == anchor
    ]
    n = len(siblings)
    if n == 1:
        return {siblings[0]: 0.0}
    # Distribute n names evenly across [-OMEGA_FAN_DEG, +OMEGA_FAN_DEG].
    # For n=3 this gives -OMEGA_FAN_DEG, 0, +OMEGA_FAN_DEG.
    offsets: dict[str, float] = {}
    if n == 1:
        offsets[siblings[0]] = 0.0
    else:
        step = (2.0 * OMEGA_FAN_DEG) / (n - 1)
        for i, name in enumerate(siblings):
            offsets[name] = -OMEGA_FAN_DEG + i * step
    return offsets


def _omega_position(name: str) -> tuple[float, float]:
    """Return (x, y) on the Ω-ring (radius 1.8) for an emergent register."""
    if name not in OMEGA_ANCHOR_NOETIC:
        raise KeyError(f"Unknown Omega: {name!r}")
    anchor = OMEGA_ANCHOR_NOETIC[name]
    anchor_angle_deg = NOETIC_ANGLE_DEG[anchor]
    fan = _omega_fan_offsets(anchor)
    angle_deg = anchor_angle_deg + fan[name]
    angle_rad = math.radians(angle_deg)
    return (OMEGA_RADIUS * math.cos(angle_rad), OMEGA_RADIUS * math.sin(angle_rad))


# Pre-computed Ω positions, deterministic and frozen for the layout.
OMEGA_POSITION: dict[str, tuple[float, float]] = {
    name: _omega_position(name) for name in EMERGENT_OMEGAS
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

    # ── Stage 23.A.3 primitive dispatch ─────────────────────────────────

    # Emergent Omega_* registers (canonical CamelCase names from
    # omega_registry.yaml; no prefix because the names are unambiguous).
    if primitive in OMEGA_POSITION:
        x, y = OMEGA_POSITION[primitive]
        return Position2D(
            primitive=primitive, kind="emergent_omega", x=x, y=y,
        )

    raise KeyError(f"Unknown primitive: {primitive!r}")


def all_positions() -> list[Position2D]:
    """Return Position2D for every primitive the layout covers.

    Enumerates in canonical form. No coordinate collisions across all
    169 primitives (Stage 23.A: 65, Stage 23.A.2: 92, Stage 23.A.3: 12).
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
    # Stage 23.A.3 primitives.
    for omega in EMERGENT_OMEGAS:
        out.append(get_position(omega))
    return out


# ── Free-form CAS expression detection (Stage 23.A.1.1) ───────────────


# Pre-compile the detection patterns once at module import; reused by
# every `detect_cas_kind` call. The committed regex strings remain the
# canonical source of truth (TypeScript consumes them verbatim), so we
# do NOT mutate them here — just cache the compiled form for speed.
_COMPILED_DETECTION_RULES: list[tuple[int, str, "re.Pattern[str]", str]] = [
    (
        int(rule["priority"]),  # type: ignore[arg-type]
        str(rule["kind"]),
        re.compile(str(rule["regex"])),
        str(rule["description"]),
    )
    for rule in DETECTION_RULES
]


def detect_cas_kind(cas: Optional[str]) -> Optional[str]:
    """Classify a free-form CAS expression into a PrimitiveKind.

    Detection order:
      1. Direct primitive lookup via `get_position` — covers exactly-named
         primitives like 'Omega_refusal', 'Product', 'NoeticCluster', etc.
         Bare 'E' raises ValueError inside `get_position`; we treat that
         the same as "no direct hit" and fall through.
      2. Iterate `DETECTION_RULES` in priority order, return the first
         rule whose `regex` matches anywhere in `cas`.
      3. Return None if no rule matches.

    None/empty input → None.
    """
    if cas is None or cas == "":
        return None
    # 1. Direct primitive lookup.
    try:
        pos = get_position(cas.strip())
    except (KeyError, ValueError):
        pos = None
    if pos is not None:
        return pos.kind
    # 2. Priority-ordered regex match.
    for _priority, kind, pattern, _description in _COMPILED_DETECTION_RULES:
        if pattern.search(cas):
            return kind
    # 3. No rule matched.
    return None


def canonical_layout_payload() -> dict[str, object]:
    """Machine-readable layout artifact (committed to research/cas_probe/)."""
    return {
        "layout_version": LAYOUT_VERSION,
        "scope": "stage_23_a_and_23_a_2_and_23_a_3_static_foundation",
        "boundary": (
            "Static canonical 2D positions for CAS primitives across "
            "Stage 23.A (Noetics/Domains/Drives/Registers/Cognitive States), "
            "Stage 23.A.2 (Operations / Inversion Axes / Foundations / "
            "Production / RPM / Set primitives / Combinators / Authority "
            "Sets / Cardinality kinds), and Stage 23.A.3 (12 admitted "
            "Omega_* emergent registers from cas-native/config/"
            "omega_registry.yaml, each anchored at radius 1.8 along its "
            "derivation Noetic's angle). Does not include atlas-self-"
            "reading, encoder design, or training signal."
        ),
        "primitives": [p.as_dict() for p in all_positions()],
        "detection_rules": [dict(rule) for rule in DETECTION_RULES],
    }
