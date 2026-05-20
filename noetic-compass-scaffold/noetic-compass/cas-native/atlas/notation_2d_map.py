"""Canonical 2D coordinate system for CAS primitives.

This module is Stage 23.A — the static foundation underneath any future
"CAS Native reads its own Idea Atlas" capability. Every CAS primitive
(10 Noetics, 4 Domains, 7 Drives, 4 Registers, 40 Cognitive States) gets
exactly one fixed (x, y) position. The geometry encodes CAS structure:

- Involution pairs are reflection-symmetric across the origin.
- Self-dual primitives sit on a symmetry axis.
- Domain precedence P ≻ C ≻ E ≻ O is spatially monotone.
- Every position is unique.
- The layout is deterministic across calls / processes / machines.

This module does NOT:
- Modify any existing atlas or trace code.
- Introduce a learned parameter or tensor.
- Claim to be an optimal attention prior. That is a future empirical
  question (Stage 23.B/C/D), not declared here.

See `research/cas_probe/STAGE23_ATLAS_SELF_READING_PREREG_20260519.md`
for the design boundary doc.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


LAYOUT_VERSION = "stage23a_notation_2d_layout_v1"


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


PrimitiveKind = Literal["noetic", "domain", "drive", "register", "cognitive_state"]


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
    raise KeyError(f"Unknown primitive: {primitive!r}")


def all_positions() -> list[Position2D]:
    """Return Position2D for every primitive the layout covers.

    Enumerates in canonical prefixed form (Noetic/Drive bare, Domain '^D',
    Register '|R', Cognitive State '^n^D'). No coordinate collisions.
    """
    out: list[Position2D] = []
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
    return out


def canonical_layout_payload() -> dict[str, object]:
    """Machine-readable layout artifact (committed to research/cas_probe/)."""
    return {
        "layout_version": LAYOUT_VERSION,
        "scope": "stage_23_a_static_foundation_only",
        "boundary": (
            "Static canonical 2D positions for CAS primitives. Does not "
            "include atlas-self-reading, encoder design, or training signal."
        ),
        "primitives": [p.as_dict() for p in all_positions()],
    }
