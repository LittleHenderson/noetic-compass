"""seams.py -- the seam rule, the Fisher-Rao step size, and the refusal to interpolate.

WHAT THIS MODULE DOES
---------------------
It implements the seam rule exactly as CONTINUITY.md states it (CONTINUITY.md:30-32):

    a seam needs BOTH
      (a) the parsed head Omega -- or the leading register when there is no head -- to change,
      AND
      (b) the step s_t >= theta_seam.

It also implements:
  * ``step_size(p, q)``          -- the Fisher-Rao distance on the open simplex
                                    ``d(p, q) = 2 * arccos(sum(sqrt(pk * qk)))``
                                    (CLAUDE.md CORRECTION 4; STATIONS.md:121-122).
  * ``step_size_stable(p, q)``   -- the same distance in the numerically stable form
                                    ``4 * arcsin(sqrt(h / 2))`` with
                                    ``h = (1/2) * sum((sqrt(p) - sqrt(q))**2)``
                                    (lm_t2\\RESULTS.md:60; rb_i1\\FROZEN.json PRC-7, cited
                                    at STATIONS.md:123-124). Used to cross-check ``step_size``.
  * ``require_open_simplex``     -- refuses any point that is not on the open simplex.
  * ``is_seam`` / ``is_tone_seam`` -- the rule, returning ``(bool, reason)``.
  * ``never_interpolate``        -- a typed refusal, ``NO_INTERPOLATION_ACROSS_SEAM``.
  * ``hold_together``            -- a two-point record labelled ``CO_PRESENT``.
  * ``normalise_register`` / ``leading_register`` -- the register identity the rule needs.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT decide any threshold. ``is_seam`` requires the caller to supply
    theta_seam; passing ``None`` is refused as ``SEAM_THRESHOLD_UNDECIDED`` rather
    than defaulted (CONTINUITY.md:35-37 says the dialogue thresholds are not reused).
  * It does NOT parse or render language. The point ``p`` is handed in; the
    DERIVED tracker that builds a point from parsed CCE content (floor 1/400 per
    state, lm_t2\\t2.py:18-19, 59-60) is NOT in this build.
  * It does NOT average, smooth, or merge two heads. There is no interpolator in
    this module on purpose: ``never_interpolate`` refuses and returns nothing.
  * It does NOT score, label, learn, or call any network.
  * It does NOT connect to the Recursive Possibility Atlas. The atlas exists now, in
    atlas.py and crossings.py, but nothing in this module reads it or knows it is there.

CLAIM CEILING (corrected in v4 -- S0 anchors on the real atlas model):
    MECHANISM ONLY. S0 ANCHORS TO THE REAL ATLAS MODEL AT COMMIT eb998556; THIS BUILD ADDS NO ATLAS OF ITS OWN. NO LANGUAGE PASSED ACROSS IT.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Constants and their sources
# --------------------------------------------------------------------------- #

#: S°_I = Δ39° = { p in R^40 : pk > 0 for all k, sum pk = 1 } (CLAUDE.md CORRECTION 4;
#: STATIONS.md:121-122). A point here must be 40 states long.
POINT_DIMENSION = 40

#: How far a submitted point may be from summing to exactly 1.0 and still be called
#: a point of the simplex. STATED, not implied: 1e-9.
SIMPLEX_SUM_TOLERANCE = 1e-9

#: Refusal codes. These are words, not exceptions, so a caller can match on them.
NOT_ON_OPEN_SIMPLEX = "NOT_ON_OPEN_SIMPLEX"
NO_INTERPOLATION_ACROSS_SEAM = "NO_INTERPOLATION_ACROSS_SEAM"
SEAM_THRESHOLD_UNDECIDED = "SEAM_THRESHOLD_UNDECIDED"
INVALID_THRESHOLD = "INVALID_THRESHOLD"
BAD_HEAD = "BAD_HEAD"
BAD_REGISTER_TAG = "BAD_REGISTER_TAG"
BAD_RECORD = "BAD_RECORD"

#: Seam-check reason codes. ``is_seam`` returns one of these, followed by " | " and
#: a plain detail string. Use ``decode_reason`` to split them.
SEAM_HEAD_CHANGED_AND_STEP_AT_OR_ABOVE_THRESHOLD = (
    "SEAM_HEAD_CHANGED_AND_STEP_AT_OR_ABOVE_THRESHOLD"
)
NO_SEAM_HEAD_UNCHANGED = "NO_SEAM_HEAD_UNCHANGED"
NO_SEAM_STEP_BELOW_THRESHOLD = "NO_SEAM_STEP_BELOW_THRESHOLD"
NO_SEAM_HEAD_UNCHANGED_AND_STEP_BELOW_THRESHOLD = "NO_SEAM_HEAD_UNCHANGED_AND_STEP_BELOW_THRESHOLD"
NO_SEAM_HEAD_OR_REGISTER_ABSENT = "NO_SEAM_HEAD_OR_REGISTER_ABSENT"
NO_SEAM_STEP_SIZE_UNAVAILABLE = "NO_SEAM_STEP_SIZE_UNAVAILABLE"

#: Tone-check reason codes (see the UNDECIDED note on ``is_tone_seam`` below).
TONE_SEAM_LEADING_REGISTER_CHANGED_AND_STEP_AT_OR_ABOVE_THRESHOLD = (
    "TONE_SEAM_LEADING_REGISTER_CHANGED_AND_STEP_AT_OR_ABOVE_THRESHOLD"
)
NO_TONE_SEAM_LEADING_REGISTER_UNCHANGED = "NO_TONE_SEAM_LEADING_REGISTER_UNCHANGED"
NO_TONE_SEAM_STEP_BELOW_THRESHOLD = "NO_TONE_SEAM_STEP_BELOW_THRESHOLD"
NO_TONE_SEAM_LEADING_REGISTER_ABSENT = "NO_TONE_SEAM_LEADING_REGISTER_ABSENT"

#: The four register letters (CAS_FOUNDATIONAL_CLARIFICATIONS.md:267-291).
REGISTER_VALUES = ("T", "A", "f", "E")

REASON_SEPARATOR = " | "


# --------------------------------------------------------------------------- #
# A typed refusal
# --------------------------------------------------------------------------- #
class SeamRefusal(Exception):
    """A refusal with a stable code, so a caller can match on the word.

    The design asks for typed refusals, not silent adjustments: a step size that
    cannot be computed, or an interpolation across a seam, is refused rather than
    approximated. ``code`` is one of the module constants above.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# Reasons
# --------------------------------------------------------------------------- #
def make_reason(code: str, detail: str = "") -> str:
    """Build a reason string: the stable code, then the plain detail."""
    return f"{code}{REASON_SEPARATOR}{detail}" if detail else code


def decode_reason(reason: str) -> tuple[str, str]:
    """Split a reason string into (code, detail). A bare code gives ("code", "")."""
    if not isinstance(reason, str):
        raise SeamRefusal(BAD_RECORD, f"reason must be a string, got {type(reason).__name__}")
    head, _, tail = reason.partition(REASON_SEPARATOR)
    return head, tail


# --------------------------------------------------------------------------- #
# Reading a record without depending on its class
# --------------------------------------------------------------------------- #
def read_field(record, name, default=None):
    """Read one leaf field from a record that is either a mapping or an object.

    Only the named leaf is read. Nothing is copied, enumerated, or serialised: the
    design forbids dumping live objects, so this reads exactly one field.
    """
    if isinstance(record, Mapping):
        return record.get(name, default)
    if hasattr(record, name):
        return getattr(record, name)
    return default


# --------------------------------------------------------------------------- #
# The register identity the seam rule compares when there is no head
# --------------------------------------------------------------------------- #
def normalise_register(spec) -> tuple[str, ...]:
    """Turn a register tag into its letters, in source order.

    Accepts ``None``, ``""``, ``"A"``, ``"|A"``, ``"|T"``, ``"|f"``, ``"|E"``, a set
    ``"|<A,f>"`` (either angle-bracket character set), ``"A,f"``, or a sequence.
    Unknown letters are refused as ``BAD_REGISTER_TAG``; a register the packet does
    not name is never guessed (CAS_FOUNDATIONAL_CLARIFICATIONS.md:267-291 lists the
    four; :655-661 admits the set form).
    """
    if spec is None:
        return ()
    if isinstance(spec, str):
        text = spec.strip()
        if not text:
            return ()
        if text.startswith("|"):
            text = text[1:].strip()
        for opener, closer in (("\u27e8", "\u27e9"), ("<", ">")):
            if text.startswith(opener):
                text = text[1:]
            if text.endswith(closer):
                text = text[:-1]
        parts = [p for p in text.replace(",", " ").split() if p]
    else:
        parts = [str(p).strip() for p in spec if str(p).strip()]
    letters: list[str] = []
    for part in parts:
        if part not in REGISTER_VALUES:
            raise SeamRefusal(
                BAD_REGISTER_TAG,
                f"{part!r} is not one of the four registers {REGISTER_VALUES}",
            )
        letters.append(part)
    return tuple(letters)


def leading_register(spec):
    """The leading register of a tag: the first one named, or ``None``.

    # UNDECIDED IN DESIGN: which register leads when a tag is a set |<...> -- CONTINUITY.md:30 says "the leading register" and never says which one leads when several are named; this build takes the first in source order.
    """
    letters = normalise_register(spec)
    return letters[0] if letters else None


# --------------------------------------------------------------------------- #
# Thresholds: never defaulted
# --------------------------------------------------------------------------- #
def require_threshold(threshold, what: str = "seam") -> float:
    """Return theta as a float, or refuse.

    ``None`` means "the design has not settled this number". It is refused as
    ``SEAM_THRESHOLD_UNDECIDED`` rather than replaced by a default, because
    CONTINUITY.md:35-37 says the dialogue thresholds are not reused blindly.
    """
    if threshold is None:
        raise SeamRefusal(
            SEAM_THRESHOLD_UNDECIDED,
            f"no {what} threshold was supplied; the design leaves the per-station-kind "
            f"{what} threshold undecided, so this build refuses instead of inventing one",
        )
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise SeamRefusal(INVALID_THRESHOLD, f"{what} threshold {threshold!r} is not a number")
    value = float(threshold)
    if not math.isfinite(value):
        raise SeamRefusal(INVALID_THRESHOLD, f"{what} threshold {value!r} is not finite")
    if value < 0.0:
        raise SeamRefusal(INVALID_THRESHOLD, f"{what} threshold {value!r} is negative")
    return value


# --------------------------------------------------------------------------- #
# The open simplex
# --------------------------------------------------------------------------- #
def require_open_simplex(point, name: str = "point") -> tuple[float, ...]:
    """Return ``point`` as a tuple of floats, or refuse as ``NOT_ON_OPEN_SIMPLEX``.

    The three conditions checked, and nothing else:
      1. it holds exactly ``POINT_DIMENSION`` (40) states;
      2. every state is strictly positive and finite -- the open simplex has no
         boundary points, pk > 0 for all k;
      3. it sums to 1 within ``SIMPLEX_SUM_TOLERANCE`` (1e-9).

    A point that fails any of these is refused. It is never repaired, floored, or
    renormalised, because a repaired point would be a claim the caller did not make.
    """
    try:
        values = tuple(float(x) for x in point)
    except (TypeError, ValueError) as exc:
        raise SeamRefusal(
            NOT_ON_OPEN_SIMPLEX, f"{name} is not a sequence of numbers ({exc})"
        ) from exc
    if len(values) != POINT_DIMENSION:
        raise SeamRefusal(
            NOT_ON_OPEN_SIMPLEX,
            f"{name} holds {len(values)} states; the open simplex here is Δ39° "
            f"and must hold {POINT_DIMENSION}",
        )
    for index, value in enumerate(values):
        if not math.isfinite(value):
            raise SeamRefusal(NOT_ON_OPEN_SIMPLEX, f"{name}[{index}] is not finite ({value!r})")
        if value <= 0.0:
            raise SeamRefusal(
                NOT_ON_OPEN_SIMPLEX,
                f"{name}[{index}] = {value!r} is not strictly positive; the simplex is open",
            )
    total = math.fsum(values)
    if abs(total - 1.0) > SIMPLEX_SUM_TOLERANCE:
        raise SeamRefusal(
            NOT_ON_OPEN_SIMPLEX,
            f"{name} sums to {total!r}; it must sum to 1 within {SIMPLEX_SUM_TOLERANCE}",
        )
    return values


# --------------------------------------------------------------------------- #
# The Fisher-Rao distance on the open simplex
# --------------------------------------------------------------------------- #
def step_size(p, q) -> float:
    """The step size s_t = d(p, q), Fisher-Rao distance on the open simplex.

    ``d(p, q) = 2 * arccos(sum(sqrt(pk * qk)))``  (CLAUDE.md CORRECTION 4;
    STATIONS.md:121-122).

    Both points are validated first (see ``require_open_simplex``). The identity
    ``sum(sqrt(pk * qk))`` can land a few ulps outside [-1, 1] in floating point
    when p equals q, which would make ``acos`` raise a math domain error; the value
    is therefore clamped to [-1, 1] before ``acos``. The clamp is arithmetic
    housekeeping, not a change of the formula: ``step_size_stable`` computes the
    same distance by a different route and the test file checks the two agree.

    Refuses (``NOT_ON_OPEN_SIMPLEX``) if either input is not a point of the open
    40-state simplex. Returns a float in [0, pi].
    """
    left = require_open_simplex(p, "p")
    right = require_open_simplex(q, "q")
    overlap = math.fsum(math.sqrt(a * b) for a, b in zip(left, right))
    return 2.0 * math.acos(min(1.0, max(-1.0, overlap)))


def step_size_stable(p, q) -> float:
    """The same distance in the stable form, ``4 * arcsin(sqrt(h / 2))``.

    ``h = (1/2) * sum((sqrt(p) - sqrt(q))**2)`` (lm_t2\\RESULTS.md:60;
    rb_i1\\FROZEN.json PRC-7, cited at STATIONS.md:123-124). This exists only as a
    cross-check on ``step_size``; it does not replace it.
    """
    left = require_open_simplex(p, "p")
    right = require_open_simplex(q, "q")
    half_square = 0.5 * math.fsum((math.sqrt(a) - math.sqrt(b)) ** 2 for a, b in zip(left, right))
    if half_square < 0.0:  # pragma: no cover - a sum of squares cannot be negative
        half_square = 0.0
    return 4.0 * math.asin(math.sqrt(min(1.0, half_square / 2.0)))


# --------------------------------------------------------------------------- #
# The seam rule
# --------------------------------------------------------------------------- #
def _identity(record) -> tuple[str, str] | None:
    """What the rule compares: the parsed head, else the leading register."""
    head = read_field(record, "head_omega")
    if head is not None:
        if not isinstance(head, str):
            raise SeamRefusal(BAD_HEAD, f"head_omega must be a string or None, got {type(head).__name__}")
        return ("HEAD", head)
    lead = leading_register(read_field(record, "leading_register"))
    if lead is None:
        return None
    return ("REGISTER", lead)


def _describe_identity(identity) -> str:
    kind, value = identity
    return f"head {value!r}" if kind == "HEAD" else f"leading register {value!r}"


def is_seam(prev, cur, threshold) -> tuple[bool, str]:
    """Apply the seam rule to two records. Returns ``(fired, reason)``.

    The rule, exactly as CONTINUITY.md:30-32 states it: a seam requires BOTH
      (a) the parsed head Omega to change -- or, when there is no head, the leading
          register to change; AND
      (b) the step size s_t >= theta_seam.

    ``prev`` and ``cur`` are read field by field (``head_omega``,
    ``leading_register``, ``point``); a dict or any object with those attributes
    works. ``threshold`` must be a number; ``None`` is refused as
    ``SEAM_THRESHOLD_UNDECIDED``.

    Both conditions are always evaluated and both are always reported, so a caller
    can see *which* condition failed. The rule is inclusive: a step exactly equal to
    the threshold fires.
    """
    theta = require_threshold(threshold, "seam")

    identity_prev = _identity(prev)
    identity_cur = _identity(cur)
    if identity_prev is None or identity_cur is None:
        side = "prev" if identity_prev is None else "cur"
        return (
            False,
            make_reason(
                NO_SEAM_HEAD_OR_REGISTER_ABSENT,
                f"{side} has neither a parsed head nor a leading register, so condition (a) "
                f"cannot be applied; a seam is not claimed",
            ),
        )

    changed = identity_prev != identity_cur
    detail_change = (
        f"{_describe_identity(identity_prev)} -> {_describe_identity(identity_cur)}"
        if changed
        else f"{_describe_identity(identity_prev)} unchanged"
    )

    point_prev = read_field(prev, "point")
    point_cur = read_field(cur, "point")
    if point_prev is None or point_cur is None:
        side = "prev" if point_prev is None else "cur"
        return (
            False,
            make_reason(
                NO_SEAM_STEP_SIZE_UNAVAILABLE,
                f"{side} has no point (a FORM gap or an untapped station), so condition (b) "
                f"cannot be applied; {detail_change}",
            ),
        )

    step = step_size(point_prev, point_cur)
    step_ok = step >= theta
    detail = (
        f"{detail_change}; step {step:.9f} {'>=' if step_ok else '<'} threshold {theta:.9f}"
    )

    if changed and step_ok:
        return True, make_reason(SEAM_HEAD_CHANGED_AND_STEP_AT_OR_ABOVE_THRESHOLD, detail)
    if not changed and step_ok:
        return False, make_reason(NO_SEAM_HEAD_UNCHANGED, detail + "; only the step was large")
    if changed and not step_ok:
        return False, make_reason(NO_SEAM_STEP_BELOW_THRESHOLD, detail + "; only the head changed")
    return False, make_reason(NO_SEAM_HEAD_UNCHANGED_AND_STEP_BELOW_THRESHOLD, detail)


def is_tone_seam(prev, cur, threshold) -> tuple[bool, str]:
    """The register-side check: does the leading register change AND the step reach theta?

    # UNDECIDED IN DESIGN: what a station-level tone seam compares, and against which threshold -- LM-T2 counts tone seams beside subject seams (CONTINUITY.md:16-17) and the packet gives no station-level tone rule; this build compares the leading register and nothing else.

    It is a separate function precisely because the design keeps the tone count
    apart from the subject count; it is never folded into ``is_seam``.
    """
    theta = require_threshold(threshold, "tone")
    register_prev = leading_register(read_field(prev, "leading_register"))
    register_cur = leading_register(read_field(cur, "leading_register"))
    if register_prev is None or register_cur is None:
        return (
            False,
            make_reason(
                NO_TONE_SEAM_LEADING_REGISTER_ABSENT,
                "one side names no leading register, so no tone change can be read",
            ),
        )

    changed = register_prev != register_cur
    point_prev = read_field(prev, "point")
    point_cur = read_field(cur, "point")
    if point_prev is None or point_cur is None:
        return (
            False,
            make_reason(
                NO_TONE_SEAM_STEP_BELOW_THRESHOLD,
                "one side has no point, so no step can be measured; no tone seam is claimed",
            ),
        )
    step = step_size(point_prev, point_cur)
    comparator = ">=" if step >= theta else "<"
    detail_change = (
        f"leading register {register_prev!r} -> {register_cur!r}"
        if changed
        else f"leading register {register_prev!r} unchanged"
    )
    detail = f"{detail_change}; step {step:.9f} {comparator} threshold {theta:.9f}"
    if changed and step >= theta:
        return True, make_reason(
            TONE_SEAM_LEADING_REGISTER_CHANGED_AND_STEP_AT_OR_ABOVE_THRESHOLD, detail
        )
    if changed:
        return False, make_reason(NO_TONE_SEAM_STEP_BELOW_THRESHOLD, detail)
    return False, make_reason(NO_TONE_SEAM_LEADING_REGISTER_UNCHANGED, detail)


# --------------------------------------------------------------------------- #
# Two heads are two points held with +, never averaged
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CoPresent:
    """Two heads, held together and left apart.

    ``points`` keeps both points exactly as given. Nothing here is an average, a
    midpoint, a blend, or a smoothing: the design says two heads are two points held
    with ``+`` (CONTINUITY.md:38-39, and Clarification 10's ``+`` discipline).
    ``distance`` is recorded so a reader can see how far apart the two points are
    without the distance ever being used to combine them.
    """

    label: str
    operator: str
    points: tuple[tuple[float, ...], tuple[float, ...]]
    distance: float
    note: str

    def as_dict(self) -> dict:
        """A small owned dict for logging. No live object is carried across."""
        return {
            "label": self.label,
            "operator": self.operator,
            "points": (tuple(self.points[0]), tuple(self.points[1])),
            "distance": self.distance,
            "note": self.note,
            "averaged": False,
        }


def never_interpolate(a, b):
    """Refuse, always. Refusal code: ``NO_INTERPOLATION_ACROSS_SEAM``.

    CONTINUITY.md:38-39: "Never interpolate across a seam ... a new head gets its own
    anchor; two heads are two points held with ``+``, never averaged. Smoothing across
    a seam is Leakage Λ (Clarification 9 :462-465)."

    Both inputs are validated as points of the open simplex first, so the refusal is
    about the seam and not about bad arithmetic. No value between ``a`` and ``b`` is
    computed, and no point is returned; the caller learns the refusal's code. For the
    two-point record the design does allow, use ``hold_together``.
    """
    require_open_simplex(a, "a")
    require_open_simplex(b, "b")
    raise SeamRefusal(
        NO_INTERPOLATION_ACROSS_SEAM,
        "a new head gets its own anchor; two heads are two points held with '+', never "
        "averaged; smoothing across a seam is Leakage Λ",
    )


def hold_together(a, b) -> CoPresent:
    """Return the two points held together, labelled ``CO_PRESENT`` with ``+``.

    This is what the design does allow across a seam: two points, two anchors, no
    combination. The returned record is immutably frozen and ``as_dict`` marks
    ``averaged: False``.
    """
    left = require_open_simplex(a, "a")
    right = require_open_simplex(b, "b")
    return CoPresent(
        label="CO_PRESENT",
        operator="+",
        points=(left, right),
        distance=step_size(left, right),
        note="two heads are two points held with +, never averaged",
    )
