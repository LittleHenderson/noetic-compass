"""stations.py -- the station model of one thought's path through the cognitive circuit.

WHAT THIS MODULE DOES
---------------------
  * It names the seven station kinds that STATIONS.md names (STATIONS.md:130-143):
    S0 THOUGHT_HEAD, S1 CJT_TRIGGER, S2 CJT_BIAS, S3 CJT_ARRIVAL, S4 OPERATING_POINT,
    S5 RPM_LINK, S6 NEXT_STAGE.
  * It holds ONE FROZEN RECORD PER KIND in ``STATION_KINDS``: the ordinal, the name, the
    one-line description, the typical Noetic, the state of the station's CCE wording, and
    its own seam, tone and drift thresholds. The table is frozen with a sha256 over its
    own canonical JSON: ``STATION_KINDS_SHA256``. ``verify_frozen()`` recomputes the
    digest from the exposed mapping and refuses if the two disagree.
  * It carries the ``Crossing`` record -- {thought_id, station, tick, head_omega,
    leading_register, content} as the owning instruction requires, plus the fields this
    build needs to apply the design's own rules (``point``, ``form_gap``, ``depth``,
    ``next_pointer``); each extra field is documented where it is declared.
  * It enforces the two settled limits: the nested depth cap of 5 (STATIONS.md:143,
    ``MAX_DEPTH = 5`` at rb2\\compose.py:39) and the open-simplex shape of a point
    (CLAUDE.md CORRECTION 4).
  * It builds a valid 40-state point from named weights with the LM-T2 floor of 1/400
    per state (``base_point``), so a caller can state a point without inventing one.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT invent a threshold. STATIONS.md gives no per-kind seam, tone or drift
    threshold, so every threshold in the frozen table is ``None`` and every kind is
    marked ``THRESHOLD_UNDECIDED``. The LM-T2 dialogue thresholds are recorded beside
    the table in ``DIALOGUE_THRESHOLDS_NOT_REUSED`` with ``licensed_for_station_kinds =
    False``, because CONTINUITY.md:35-37 forbids reusing them blindly.
  * It does NOT parse or render language, so it does not build a point from a station's
    own tap. The point is handed in by the caller. The DERIVED tracker
    (p = point(parse(render(R_i))), floor 1/400 per state) is NOT in this build.
  * It does NOT compute an ASOM word. S4 stores its two axes and no word, because
    CONTINUITY_AND_DISENGAGE_20261016.md:38 says the ASOM ruling is still not located.
  * It does NOT connect to the Recursive Possibility Atlas. S0 is a station name here,
    not an atlas entry: how atlas entries attach to stations is still undecided
    (OWNER_RULING_RPA_ATLAS_20261015.md:35-38).
  * It does NOT score, learn, persist, or call any network.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOT THE BRAIN FEATURE. THE ATLAS LINK IS NOT BUILT.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import seams

# --------------------------------------------------------------------------- #
# Constants and their sources
# --------------------------------------------------------------------------- #

#: The seven station ordinals, in the order STATIONS.md:132-140 lists them.
STATION_ORDINALS = ("S0", "S1", "S2", "S3", "S4", "S5", "S6")

#: Nested levels repeat S1-S5 inside S5 at "depth at most 5" (STATIONS.md:143;
#: "maximum depth of 5 levels", Chapter_27_RPM_Structure.md:59; MAX_DEPTH = 5,
#: rb2\\compose.py:39). The gate word for exceeding it is the design's own: DEPTH_CAP
#: (rb2\\compose.py:16-20).
MAX_NESTED_DEPTH = 5

#: The LM-T2 floor: 1/400 per state (lm_t2\\t2.py:18-19, 59-60; owner default Q18 of
#: the language map). Used only by ``base_point`` so a caller can state a point.
POINT_FLOOR = 1.0 / 400.0

#: The four register letters (CAS_FOUNDATIONAL_CLARIFICATIONS.md:267-291).
REGISTER_VALUES = seams.REGISTER_VALUES

#: Threshold words, shared with seams.py so a caller matches one vocabulary.
THRESHOLD_UNDECIDED = "THRESHOLD_UNDECIDED"
THRESHOLD_CALIBRATED = "THRESHOLD_CALIBRATED"

#: Refusal codes.
UNKNOWN_STATION = "UNKNOWN_STATION"
BAD_TICK = "BAD_TICK"
DEPTH_CAP = "DEPTH_CAP"
BAD_CONTENT = "BAD_CONTENT"
BAD_FLOOR = "BAD_FLOOR"
BAD_STATE_INDEX = "BAD_STATE_INDEX"
NEGATIVE_WEIGHT = "NEGATIVE_WEIGHT"
FORM_GAP_WITH_POINT = "FORM_GAP_WITH_POINT"
FROZEN_TABLE_CHANGED = "FROZEN_TABLE_CHANGED"


class StationRefusal(Exception):
    """A refusal with a stable code. Nothing is repaired or guessed."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --------------------------------------------------------------------------- #
# The station kinds, one record each
# --------------------------------------------------------------------------- #
# Each record is built from STATIONS.md:132-143 (the one-line list) and :145-292 (each
# station in full), with the CCE wording state from TAP_AND_INJECT.md:43-51.
#
# The threshold fields are the point of the freeze: every station kind gets its own seam
# and tone threshold (and the drift threshold, which the same paragraph leaves open), and
# every one of them is None here.
#
# UNDECIDED IN DESIGN: what theta_seam, theta_tone and theta_drift are for each station kind -- STATIONS.md:145-292 gives no number for any kind, and CONTINUITY.md:35-37 forbids reusing the dialogue numbers.
#
# UNDECIDED IN DESIGN: what S0 holds as content -- OWNER_RULING_RPA_ATLAS_20261015.md:35-38 says how an atlas entry attaches to a CJT, to Bias and to an RPM link is not decided by that record.
#
# UNDECIDED IN DESIGN: which ASOM reading is licensed at S4 -- CONTINUITY_AND_DISENGAGE_20261016.md:38 says the ASOM ruling has not been located and must not be invented, so S4 stores its two axes and no word.
_NO_THRESHOLD = {
    "seam_threshold": None,
    "tone_threshold": None,
    "drift_threshold": None,
    "threshold_status": THRESHOLD_UNDECIDED,
}


def _kind(
    kind: str,
    ordinal: str,
    name: str,
    one_line: str,
    typical_noetic,
    cce_form_status: str,
    cce_form_note: str,
    source: str,
) -> dict:
    record = {
        "kind": kind,
        "ordinal": ordinal,
        "name": name,
        "one_line": one_line,
        "typical_noetic": typical_noetic,
        "cce_form_status": cce_form_status,
        "cce_form_note": cce_form_note,
        "source": source,
    }
    record.update(_NO_THRESHOLD)
    return record


_STATION_KINDS_PLAIN = {
    "THOUGHT_HEAD": _kind(
        kind="THOUGHT_HEAD",
        ordinal="S0",
        name="Thought head",
        one_line=(
            "where a thought starts: its production target Omega, the routes the order "
            "names, and (RB-I) the drive that chose it"
        ),
        typical_noetic=None,
        cce_form_status="PARTIAL_FORM_GAP",
        cce_form_note="'Topic: Omega_x.' is covered; the order shape has no CCE form",
        source="STATIONS.md:153-172; TAP_AND_INJECT.md:45",
    ),
    "CJT_TRIGGER": _kind(
        kind="CJT_TRIGGER",
        ordinal="S1",
        name="CJT trigger (Cause terminal)",
        one_line="the Idea entering this stage: the stock in memory and the order; typically ^8",
        typical_noetic="^8",
        cce_form_status="PARTIAL_FORM_GAP",
        cce_form_note="the stock statement is covered; board 2's order has no CCE form",
        source="STATIONS.md:174-186; TAP_AND_INJECT.md:46",
    ),
    "CJT_BIAS": _kind(
        kind="CJT_BIAS",
        ordinal="S2",
        name="CJT Bias (Base terminal)",
        one_line=(
            "the ^5 substrate this stage processes against: the recipe's learned "
            "requirements (RB) or the Bias state (GB3)"
        ),
        typical_noetic="^5",
        cce_form_status="PARTIAL_FORM_GAP",
        cce_form_note=(
            "the RECIPE form is covered for terminating decimals; a non-terminating "
            "Fraction such as 1/3 is a FORM gap (OPEN_QUESTIONS Q13)"
        ),
        source="STATIONS.md:188-214; TAP_AND_INJECT.md:47",
    ),
    "CJT_ARRIVAL": _kind(
        kind="CJT_ARRIVAL",
        ordinal="S3",
        name="CJT arrival (Effect terminal)",
        one_line="the Idea produced: yield, Limiting Reagent, label, or UNDETERMINED; typically ^9",
        typical_noetic="^9",
        cce_form_status="PARTIAL_FORM_GAP",
        cce_form_note=(
            "the yield reply exists and UNDETERMINED is fixed as 'I cannot tell.'; the "
            "'I checked: ... yields y; the bottleneck is X.' wording is only PROPOSED"
        ),
        source="STATIONS.md:216-229; TAP_AND_INJECT.md:48",
    ),
    "OPERATING_POINT": _kind(
        kind="OPERATING_POINT",
        ordinal="S4",
        name="Operating point of the stage",
        one_line="region and semantic outcome of this crossing; the ASOM word only as a derived display",
        typical_noetic=None,
        cce_form_status="FORM_GAP",
        cce_form_note=(
            "no CCE form exists; the ASOM word is never said alone, and the ASOM ruling "
            "itself is still not located"
        ),
        source="STATIONS.md:231-257; TAP_AND_INJECT.md:49",
    ),
    "RPM_LINK": _kind(
        kind="RPM_LINK",
        ordinal="S5",
        name="RPM link",
        one_line="the one-way prerequisite edge from this arrival to the next stage, its depth, and its receipt",
        typical_noetic=None,
        cce_form_status="PARTIAL_FORM_GAP",
        cce_form_note="'Omega_b needs Omega_a first.' is covered; the receipt sentence is a FORM gap",
        source="STATIONS.md:259-283; TAP_AND_INJECT.md:50",
    ),
    "NEXT_STAGE": _kind(
        kind="NEXT_STAGE",
        ordinal="S6",
        name="Next stage",
        one_line="the next CJT (chain slot, other route) or the next thought head (back to S0)",
        typical_noetic=None,
        cce_form_status="PARTIAL_FORM_GAP",
        cce_form_note="'New subject: Omega_y.' is covered; 'Next: Omega_b.' is only PROPOSED",
        source="STATIONS.md:285-292; TAP_AND_INJECT.md:51",
    ),
}


# --------------------------------------------------------------------------- #
# The freeze: a sha256 over the table's own canonical JSON
# --------------------------------------------------------------------------- #
def canonical_table_json() -> str:
    """The frozen table as canonical JSON: sorted keys, no whitespace, ASCII only.

    ``None`` serialises as ``null``. There are no floats in the table, so the digest
    cannot drift between machines on float formatting.
    """
    return json.dumps(
        _STATION_KINDS_PLAIN,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def sha256_of(text: str) -> str:
    """The hex sha256 of UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


#: The frozen digest of the station-kind table. Reported in README.md and by the tests.
STATION_KINDS_SHA256 = sha256_of(canonical_table_json())


def _deep_freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    return value


#: The read-only station-kind table. One record per kind, each with its own seam and
#: tone threshold (and the drift threshold, which CONTINUITY.md:36-37 also leaves open).
STATION_KINDS = _deep_freeze(_STATION_KINDS_PLAIN)

#: Ordinal -> kind, so a crossing named by its station ("S3") can find its kind.
STATION_KIND_BY_ORDINAL = MappingProxyType(
    {record["ordinal"]: kind for kind, record in _STATION_KINDS_PLAIN.items()}
)


def verify_frozen() -> str:
    """Prove the exposed frozen table is the table that was hashed. Returns the digest.

    Two checks: the canonical JSON regenerated from the read-only mapping must hash to
    ``STATION_KINDS_SHA256``, and the digests must be recomputable at all. A table that
    has been changed after the freeze is refused as ``FROZEN_TABLE_CHANGED``.
    """
    recomputed = sha256_of(json.dumps(_thaw(STATION_KINDS), sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    if recomputed != STATION_KINDS_SHA256:
        raise StationRefusal(
            FROZEN_TABLE_CHANGED,
            f"the station-kind table hashes to {recomputed}, not the frozen {STATION_KINDS_SHA256}",
        )
    return STATION_KINDS_SHA256


#: The LM-T2 dialogue thresholds, recorded so nobody has to hunt for them -- and marked
#: NOT licensed for station kinds, which is what CONTINUITY.md:35-37 says.
DIALOGUE_THRESHOLDS_NOT_REUSED = MappingProxyType(
    {
        "seam": 0.841069956,
        "tone": 1.227592661,
        "drift": 0.984979914,
        "licensed_for_station_kinds": False,
        "source": "lm_t2\\RESULTS.md:31-33, quoted at CONTINUITY.md:36-37",
        "why_not_reused": (
            "a recipe, a stock vector and a yield are different kinds of content and "
            "their points sit in different parts of the simplex (CONTINUITY.md:35-36)"
        ),
    }
)


# --------------------------------------------------------------------------- #
# Looking a kind up
# --------------------------------------------------------------------------- #
def kind_of(station: str) -> str:
    """The kind name for a station ordinal ("S3" -> "CJT_ARRIVAL"). Refuses if unknown."""
    if not isinstance(station, str) or station not in STATION_KIND_BY_ORDINAL:
        raise StationRefusal(
            UNKNOWN_STATION,
            f"{station!r} is not one of the station ordinals {STATION_ORDINALS}",
        )
    return STATION_KIND_BY_ORDINAL[station]


def station_record(station: str) -> Mapping:
    """The frozen record for a station ordinal."""
    return STATION_KINDS[kind_of(station)]


def threshold_of(station: str, which: str = "seam"):
    """The frozen threshold for a station kind -- ``None`` until the design settles it.

    This function deliberately returns ``None`` rather than a default: the caller must
    decide what to do with an undecided threshold (seams.require_threshold refuses).
    """
    if which not in ("seam", "tone", "drift"):
        raise StationRefusal(UNKNOWN_STATION, f"{which!r} is not a threshold this table holds")
    return station_record(station)[f"{which}_threshold"]


# --------------------------------------------------------------------------- #
# The register identity, re-exported from seams so there is one implementation.
# The undecided question about which register leads a set tag is marked where the
# function lives, in seams.py: one implementation, one place to read the question.
# --------------------------------------------------------------------------- #
normalise_register = seams.normalise_register
leading_register = seams.leading_register


# --------------------------------------------------------------------------- #
# A point of the open simplex, built the LM-T2 way
# --------------------------------------------------------------------------- #
def base_point(weights=None, floor: float = POINT_FLOOR):
    """Build a 40-state point: ``floor`` on every state, the remaining mass by ``weights``.

    ``weights`` maps a state index (0-39) to a non-negative weight; the mass left after
    the floor is 1 - 40*floor = 0.9 at the default floor, and it is split in proportion
    to the weights. With no weights every state gets ``floor`` plus an equal share.

    The default floor is LM-T2's 1/400 per state (lm_t2\\t2.py:18-19, 59-60), which keeps
    every state strictly positive, as the open simplex requires. This is a way to STATE a
    point; it is not the tracker, which is not built here.
    """
    size = seams.POINT_DIMENSION
    floor = float(floor)
    if not (0.0 < floor < 1.0 / size):
        raise StationRefusal(BAD_FLOOR, f"floor {floor!r} must be above 0 and below 1/{size}")
    mass = 1.0 - floor * size
    shares = [0.0] * size
    if weights:
        for key, weight in dict(weights).items():
            try:
                index = int(key)
            except (TypeError, ValueError) as exc:
                raise StationRefusal(BAD_STATE_INDEX, f"{key!r} is not a state index") from exc
            if not 0 <= index < size:
                raise StationRefusal(BAD_STATE_INDEX, f"state index {index} is outside 0..{size - 1}")
            value = float(weight)
            if value < 0.0:
                raise StationRefusal(NEGATIVE_WEIGHT, f"weight for state {index} is negative ({value!r})")
            shares[index] = value
    total = sum(shares)
    if total <= 0.0:
        shares = [1.0] * size
        total = float(size)
    point = tuple(floor + mass * (share / total) for share in shares)
    return seams.require_open_simplex(point, "base_point")


# --------------------------------------------------------------------------- #
# The crossing record
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Crossing:
    """One station crossing: a thought at a station, at a tick.

    The required fields, exactly as the owning instruction names them:

      * ``thought_id``       -- which thought this crossing belongs to.
      * ``station``          -- a station ordinal, "S0" ... "S6".
      * ``tick``             -- the tick of the crossing (station boundaries, not turns;
                                CONTINUITY.md:21, TAP_AND_INJECT.md:119-121).
      * ``head_omega``       -- the parsed head Omega, or ``None`` when there is none.
                                Identifiers are compared byte for byte (MAP.md:52-55).
      * ``leading_register`` -- the register tag, e.g. "|A" or "|<A,f>".
      * ``content``          -- the station's own small content dict. Never live data.

    The fields this build adds to apply the design's own rules:

      * ``point``        -- the Noetic state point, or ``None`` where the station has a
                            FORM gap. "The point exists only where the tap exists; a
                            station with a FORM gap contributes no point and is counted"
                            (CONTINUITY.md:24-26).
      * ``form_gap``     -- True exactly when ``point`` is ``None``; enforced, so the
                            count in continuity.py cannot disagree with the record.
      * ``depth``        -- the RPM level (0 for the top level, 1-5 inside S5's nested
                            levels), capped at ``MAX_NESTED_DEPTH``.
      * ``next_pointer`` -- the next-station pointer, read by provenance.py to tell
                            FOLLOWED, CREATED and ATTEMPTED apart. ``None`` is allowed.
    """

    thought_id: str
    station: str
    tick: int
    head_omega: str | None
    leading_register: str | None
    content: Mapping
    point: tuple[float, ...] | None = None
    form_gap: bool = False
    depth: int = 0
    next_pointer: Mapping | None = None

    # -- validation ------------------------------------------------------- #
    def __post_init__(self) -> None:
        if not isinstance(self.thought_id, str) or not self.thought_id:
            raise StationRefusal(BAD_CONTENT, "thought_id must be a non-empty string")
        if not isinstance(self.station, str) or self.station not in STATION_ORDINALS:
            raise StationRefusal(
                UNKNOWN_STATION, f"{self.station!r} is not one of {STATION_ORDINALS}"
            )
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise StationRefusal(BAD_TICK, f"tick {self.tick!r} is not a whole number of ticks")
        if self.head_omega is not None and not isinstance(self.head_omega, str):
            raise StationRefusal(seams.BAD_HEAD, "head_omega must be a string or None")
        if self.depth is None or isinstance(self.depth, bool) or not isinstance(self.depth, int):
            raise StationRefusal(DEPTH_CAP, f"depth {self.depth!r} is not a whole number")
        if self.depth < 0:
            raise StationRefusal(DEPTH_CAP, f"depth {self.depth} is negative")
        if self.depth > MAX_NESTED_DEPTH:
            raise StationRefusal(
                DEPTH_CAP,
                f"depth {self.depth} exceeds the cap of {MAX_NESTED_DEPTH} nested levels "
                f"(STATIONS.md:143; MAX_DEPTH = 5)",
            )
        # UNDECIDED IN DESIGN: whether a crossing at S0 or S6 may carry a nested depth above 0 -- STATIONS.md:143 says nested levels repeat S1-S5 inside S5 and does not say whether a nested thought has its own head and next stage; this build permits any station at depth 1-5 and only caps the level.
        if self.point is not None:
            object.__setattr__(self, "point", seams.require_open_simplex(self.point, "point"))
            if self.form_gap:
                raise StationRefusal(
                    FORM_GAP_WITH_POINT,
                    "a crossing cannot claim a FORM gap and carry a point at the same time",
                )
            object.__setattr__(self, "form_gap", False)
        else:
            object.__setattr__(self, "form_gap", True)
        object.__setattr__(self, "content", _freeze_mapping(self.content, "content"))
        object.__setattr__(self, "leading_register", _freeze_register(self.leading_register))
        if self.next_pointer is not None:
            object.__setattr__(self, "next_pointer", _freeze_mapping(self.next_pointer, "next_pointer"))

    # -- derived ---------------------------------------------------------- #
    @property
    def kind(self) -> str:
        """The station kind this crossing sits on."""
        return kind_of(self.station)

    @property
    def has_point(self) -> bool:
        """True when a point exists for this crossing."""
        return self.point is not None

    def as_dict(self) -> dict:
        """A small owned dict for a log line. No live object is carried across."""
        return {
            "thought_id": self.thought_id,
            "station": self.station,
            "kind": self.kind,
            "tick": self.tick,
            "head_omega": self.head_omega,
            "leading_register": self.leading_register,
            "content": dict(self.content),
            "point": tuple(self.point) if self.point is not None else None,
            "form_gap": self.form_gap,
            "depth": self.depth,
            "next_pointer": dict(self.next_pointer) if self.next_pointer is not None else None,
        }


def _freeze_mapping(value, name: str) -> Mapping:
    if value is None:
        raise StationRefusal(BAD_CONTENT, f"{name} must be a mapping, not None")
    if not isinstance(value, Mapping):
        raise StationRefusal(BAD_CONTENT, f"{name} must be a mapping, got {type(value).__name__}")
    return MappingProxyType(dict(value))


def _freeze_register(value):
    """Keep the tag as given (byte for byte) but check its letters are registers."""
    if value is None:
        return None
    normalise_register(value)  # raises BAD_REGISTER_TAG on an unknown letter
    return value


#: Convenience constructor; ``Crossing`` can also be built directly.
def make_crossing(
    thought_id: str,
    station: str,
    tick: int,
    head_omega: str | None,
    leading_register: str | None = None,
    content=None,
    point=None,
    depth: int = 0,
    next_pointer=None,
) -> Crossing:
    """Build a Crossing. ``content`` defaults to an empty mapping."""
    return Crossing(
        thought_id=thought_id,
        station=station,
        tick=tick,
        head_omega=head_omega,
        leading_register=leading_register,
        content={} if content is None else content,
        point=point,
        depth=depth,
        next_pointer=next_pointer,
    )
