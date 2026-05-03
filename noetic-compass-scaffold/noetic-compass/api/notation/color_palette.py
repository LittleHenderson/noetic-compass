"""CAS Value-Keyed Color Palette — Python source of truth.

Maps each CAS axis value to a unique, colorblind-accessible color.
Full design rationale and accessibility analysis:
  docs/working/cas_color_palette_specification.md

Palette version: v1.0 (locked). Downstream consumers must pin this version.
Bumping PALETTE_VERSION is a breaking change.
"""

from __future__ import annotations

PALETTE_VERSION: str = "v1.0"

# ---------------------------------------------------------------------------
# Noetic axis — ^0 through ^9
# Basis: Paul Tol "muted" 10-class qualitative palette, lightness-adjusted
# for L∈[0.12,0.30] to meet WCAG 3:1 on both #0d1117 and #ffffff.
# ---------------------------------------------------------------------------
_NOETIC_COLORS: tuple[str, ...] = (
    "#3388BB",  # ^0 Idea         — mid blue        (Tol pale-blue, darkened)
    "#117733",  # ^1 Mind         — dark green       (Tol green, kept)
    "#CC7700",  # ^2 Positive     — amber-orange     (Tol straw, hue-shifted + darkened)
    "#CC6677",  # ^3 Negative     — rose-pink        (Tol rose, kept)
    "#2E7A6E",  # ^4 Vibration    — dark teal        (Tol teal, darkened)
    "#CC3388",  # ^5 Female       — magenta          (Tol wine, brightened)
    "#5B55C0",  # ^6 Male         — indigo           (Tol indigo, brightened)
    "#7A7A25",  # ^7 Rhythm       — olive            (Tol olive, darkened)
    "#AA4499",  # ^8 Above/Cause  — purple           (Tol purple, kept)
    "#6B778C",  # ^9 Below/Effect — blue-gray        (Tol gray → blue-gray)
)

# ---------------------------------------------------------------------------
# Domain axis — P, C, E, O
# Medium-saturation tier (L∈[0.22,0.30]), visually distinct from Noetics.
# ---------------------------------------------------------------------------
_DOMAIN_COLORS: dict[str, str] = {
    "P": "#7B7EC4",  # Principled  — lavender-indigo (ColorBrewer Set2 adj.)
    "C": "#4490B0",  # Cognitive   — steel blue      (ColorBrewer Set2 adj.)
    "E": "#4A9068",  # Evaluative  — muted emerald   (ColorBrewer Set2 adj.)
    "O": "#C0883C",  # Operational — muted amber     (Wong orange, desaturated)
}

# ---------------------------------------------------------------------------
# Drive axis — F1 through F7 (1-indexed, matching CAS convention)
# Basis: Paul Tol "bright" palette hues, lightness-adjusted.
# Inversion pairs (F1↔F7, F2↔F6, F3↔F5) use contrasting hues.
# F3/F5 pair avoids red+green to prevent deut/prot confusion.
# ---------------------------------------------------------------------------
_DRIVE_COLORS: tuple[str, ...] = (
    "",         # index 0 — unused (drives are 1-indexed)
    "#4477AA",  # F1 Unity      — blue          (Tol bright blue)
    "#7755CC",  # F2 Wisdom     — purple        (Tol bright purple)
    "#228866",  # F3 Vitality   — teal-green    (teal avoids pure green for CB safety)
    "#997700",  # F4 Connection — amber-olive   (self-dual, warm neutral)
    "#BB4488",  # F5 Agency     — pink-magenta  (distinct from F3 teal under deut/prot)
    "#BB6699",  # F6 Structure  — medium pink   (Tol bright magenta, L adj.)
    "#446688",  # F7 Purpose    — slate blue    (Tol bright blue, hue-shifted)
)

# ---------------------------------------------------------------------------
# Register axis — T, A, f, E
# Encoded as border-style overlays rather than fill colors,
# keeping Register orthogonal to Noetic/Domain/Drive fill.
# ---------------------------------------------------------------------------
_REGISTER_TREATMENTS: dict[str, dict[str, str]] = {
    "T": {"border_style": "solid",  "color": "#D4A020"},  # Transcendent — gold solid
    "A": {"border_style": "double", "color": "#4488CC"},  # Analytical   — blue double
    "f": {"border_style": "dashed", "color": "#CC4477"},  # Affective    — rose dashed
    "E": {"border_style": "dotted", "color": "#44AA77"},  # Embodied     — teal dotted
}


def noetic_color(n: int) -> str:
    """Return the hex color for Noetic operator ^n (n in 0..9).

    Raises ValueError if n is outside [0, 9].
    """
    if not isinstance(n, int) or not (0 <= n <= 9):
        raise ValueError(f"Noetic index must be an integer in [0, 9]; got {n!r}")
    return _NOETIC_COLORS[n]


def domain_color(d: str) -> str:
    """Return the hex color for Domain d in {'P', 'C', 'E', 'O'}.

    Raises ValueError if d is not a recognized domain letter.
    """
    if d not in _DOMAIN_COLORS:
        raise ValueError(
            f"Domain must be one of {set(_DOMAIN_COLORS)}; got {d!r}"
        )
    return _DOMAIN_COLORS[d]


def drive_color(k: int) -> str:
    """Return the hex color for Drive F_k (k in 1..7).

    Raises ValueError if k is outside [1, 7].
    """
    if not isinstance(k, int) or not (1 <= k <= 7):
        raise ValueError(f"Drive index must be an integer in [1, 7]; got {k!r}")
    return _DRIVE_COLORS[k]


def register_treatment(r: str) -> dict[str, str]:
    """Return the visual treatment dict for Register r in {'T', 'A', 'f', 'E'}.

    Returns a dict with keys:
      - 'border_style': one of 'solid', 'double', 'dashed', 'dotted'
      - 'color': hex color string

    Raises ValueError if r is not a recognized register.
    """
    if r not in _REGISTER_TREATMENTS:
        raise ValueError(
            f"Register must be one of {set(_REGISTER_TREATMENTS)}; got {r!r}"
        )
    return dict(_REGISTER_TREATMENTS[r])  # return a copy


def axis_color_for_node(node: dict) -> str | None:
    """Return the most-specific axis color for a diagram node dict.

    Precedence: Noetic > Domain > Drive > (Register is a border overlay, not a fill).
    Returns None if no axis information is present.

    Expected node keys (all optional):
      - 'noetic': int in [0, 9]
      - 'domain': str in {'P', 'C', 'E', 'O'}
      - 'drive': int in [1, 7]

    Raises ValueError only if a present axis value is out of range.
    """
    if "noetic" in node and node["noetic"] is not None:
        return noetic_color(int(node["noetic"]))
    if "domain" in node and node["domain"] is not None:
        return domain_color(str(node["domain"]))
    if "drive" in node and node["drive"] is not None:
        return drive_color(int(node["drive"]))
    return None
