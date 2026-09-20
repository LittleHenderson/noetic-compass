"""The 7-axis inversion scanner: structure frozen, thresholds not invented.

The master instructions name seven inversion axes and their structural content, and they
freeze one numeric limit. They do not state a formula or a threshold for most of the axes.
This module separates the two cases rather than blurring them.

WHAT IS FROZEN, AND THEREFORE ENFORCED
--------------------------------------
* The involution pairs ``CO-2↔CO-3``, ``CO-5↔CO-6``, ``CO-8↔CO-9`` and the self-duals
  ``CO-0``, ``CO-1``, ``CO-4``, ``CO-7``.
* The dial bounds: an integer ``3..9``, non-overridable.
* The dial divergence limit: an involution pair cannot diverge by more than **4 points**.
* The drive inversion pairs ``F1↔F7``, ``F2↔F6``, ``F3↔F5``, with ``F4`` self-dual.
* The domain precedence tiers ``P ≻ C ≻ E ≻ O``.
* The pathway chain ``A0 → Dn → Wn → Pn``, which is one-directional, so satisfying a node
  before its prerequisite is a violation of the chain and not of a tunable threshold.
* The compound axis: "multiple axes simultaneously".

WHAT IS NOT FROZEN, AND THEREFORE MEASURED BUT NOT JUDGED
---------------------------------------------------------
For the remaining axes the instructions give the *quantity of interest* but no limit: how
much involution imbalance in the state vector is too much, how much domain-tier inversion is
too much, how much drive-pair divergence is too much, how much entropy deficit is too much,
how much cross-domain sub-drive variance is too much. **No threshold is invented here.** Each
axis returns its raw measurement with ``frozen_limit = None``, and a caller that wants a
severity must supply its own threshold explicitly via :func:`exceeds`.

Three consequences, all deliberate:

* :class:`AxisMeasurement` carries ``exceeds_frozen_limit`` as ``None`` — not ``False`` — when
  no limit is frozen. "No limit exists" and "within the limit" are different answers.
* :func:`scan` never emits an NCCS-shaped score. A 15%-weighted inversion-resistance component
  would require thresholds that have not been decided, and producing one would grant scoring
  authority to numbers this module made up.
* The compound axis ``P`` is computed **only** from axes that exceed a *frozen* limit, so
  ``P`` cannot be triggered by a provisional reading.

The entropy axis ``E`` is Correction 4's uniformity, taken from :mod:`cncm.simplex`: the state
vector is a point of the open simplex and its entropy deficit is measured against ``log 40``.

Pure standard library. No numeric runtime, no device, no clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .canonical import digest
from .model import CANONICAL_DRIVES
from .noetica import PATHWAY_NODES, PREREQUISITE, STATE_INDEX, satisfied_chain
from .simplex import NUM_STATES, CognitiveStateVector

SCHEMA_VERSION = "cncm.inversions/0.1"

#: Frozen by the instructions: an involution pair cannot diverge by more than 4 dial points.
MAX_INVOLUTION_DIAL_DIVERGENCE = 4

#: Frozen by the instructions: every dial is an integer in this inclusive range.
MIN_DIAL = 3
MAX_DIAL = 9

#: The 10 Noetics in canonical order, as indices into a dial profile.
NOETIC_COUNT = 10

#: Frozen involution pairs over Noetic indices. The self-duals are the complement.
INVOLUTION_PAIRS = ((2, 3), (5, 6), (8, 9))
SELF_DUAL_NOETICS = (0, 1, 4, 7)

#: Frozen domain precedence tiers, strongest first.
DOMAIN_TIERS = ("P", "C", "E", "O")

#: Frozen drive inversion pairs. ``F4`` is self-dual.
DRIVE_PAIRS = (("F1", "F7"), ("F2", "F6"), ("F3", "F5"))
SELF_DUAL_DRIVE = "F4"


class InversionError(ValueError):
    """A frozen constraint was violated, or an unfrozen one was asked to decide."""


class DialOutOfRange(InversionError):
    """A dial was set outside the non-overridable ``3..9`` range."""


class Axis(Enum):
    """The seven axes. The single letters are the canonical names."""

    NOETIC_INVOLUTION = "N"
    DOMAIN_PRECEDENCE = "W"
    DRIVE_PAIR = "F"
    ENTROPY_DEFICIT = "E"
    SUBDRIVE_VARIANCE = "S"
    PATHWAY_CHAIN = "A"
    COMPOUND = "P"


@dataclass(frozen=True)
class AxisMeasurement:
    """One axis's raw reading, with the limit only where one is frozen.

    ``frozen_limit is None`` means no authority has decided a limit for this axis. That is
    reported as ``exceeds_frozen_limit = None`` rather than ``False``, because collapsing the
    two would turn an undecided threshold into a silent pass.
    """

    axis: Axis
    measurement: float
    unit: str
    frozen_limit: float | None
    exceeds_frozen_limit: bool | None
    detail: dict

    def exceeds(self, threshold: float) -> bool:
        """Apply a caller-supplied threshold. The caller owns the decision, not this module."""
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            raise InversionError("a threshold must be a number")
        if not math.isfinite(float(threshold)):
            raise InversionError("a threshold must be finite")
        return self.measurement > float(threshold)

    def as_dict(self) -> dict:
        return {
            "axis": self.axis.value,
            "measurement": self.measurement,
            "unit": self.unit,
            "frozen_limit": self.frozen_limit,
            "exceeds_frozen_limit": self.exceeds_frozen_limit,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class DialProfile:
    """Ten integer dials, one per Noetic, each constrained to ``3..9``."""

    dials: tuple

    def __post_init__(self) -> None:
        if len(self.dials) != NOETIC_COUNT:
            raise InversionError(f"a dial profile needs {NOETIC_COUNT} dials")
        for index, value in enumerate(self.dials):
            if isinstance(value, bool) or not isinstance(value, int):
                raise InversionError(f"dial {index} must be an integer")
            if not MIN_DIAL <= value <= MAX_DIAL:
                raise DialOutOfRange(
                    f"dial {index} is {value}; the range {MIN_DIAL}..{MAX_DIAL} is "
                    f"non-overridable"
                )

    def divergence(self, left: int, right: int) -> int:
        return abs(self.dials[left] - self.dials[right])


@dataclass(frozen=True)
class DriveProfile:
    """Seven core drive values, keyed by the canonical drive labels."""

    values: dict

    def __post_init__(self) -> None:
        if set(self.values) != set(CANONICAL_DRIVES):
            raise InversionError("a drive profile needs exactly the seven canonical drives")
        for name, value in self.values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise InversionError(f"drive {name} is not a number")
            if not math.isfinite(float(value)):
                raise InversionError(f"drive {name} is not finite")

    def gap(self, left: str, right: str) -> float:
        return abs(float(self.values[left]) - float(self.values[right]))


@dataclass(frozen=True)
class SubDriveProfile:
    """The 28 domain-specific drives: 7 drives × 4 domains."""

    values: dict

    def __post_init__(self) -> None:
        expected = {(drive, tier) for drive in CANONICAL_DRIVES for tier in DOMAIN_TIERS}
        if set(self.values) != expected:
            raise InversionError("a sub-drive profile needs exactly 7 drives x 4 domains")
        for key, value in self.values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise InversionError(f"sub-drive {key} is not a number")
            if not math.isfinite(float(value)):
                raise InversionError(f"sub-drive {key} is not finite")

    def across_domains(self, drive: str) -> tuple:
        return tuple(float(self.values[(drive, tier)]) for tier in DOMAIN_TIERS)


@dataclass(frozen=True)
class InversionReport:
    axes: tuple
    compound: bool
    axes_exceeding_frozen_limits: tuple
    frozen_axes: tuple
    unfrozen_axes: tuple
    unfrozen_readings: tuple
    stealth: str
    nccs_inversion_resistance: str

    def axis(self, axis: Axis) -> AxisMeasurement:
        for measurement in self.axes:
            if measurement.axis is axis:
                return measurement
        raise InversionError(f"axis {axis.value} is not in this report")

    def all_readings(self, axis: Axis) -> tuple:
        """Every reading of one axis. ``N`` has two: one judged, one measured only."""
        found = tuple(measurement for measurement in self.axes if measurement.axis is axis)
        if not found:
            raise InversionError(f"axis {axis.value} is not in this report")
        return found

    def as_dict(self) -> dict:
        return {
            "schema": SCHEMA_VERSION,
            "axes": [measurement.as_dict() for measurement in self.axes],
            "compound": self.compound,
            "axes_exceeding_frozen_limits": [
                axis.value for axis in self.axes_exceeding_frozen_limits
            ],
            "frozen_axes": [axis.value for axis in self.frozen_axes],
            "unfrozen_axes": [axis.value for axis in self.unfrozen_axes],
            "unfrozen_readings": list(self.unfrozen_readings),
            "stealth": self.stealth,
            "nccs_inversion_resistance": self.nccs_inversion_resistance,
        }

    def digest(self) -> str:
        return digest(self.as_dict())


def _noetic_mass(state: CognitiveStateVector, noetic: int) -> float:
    """Total probability on one Noetic across the four domains.

    The component ordering is not assumed here. It is read from
    :data:`cncm.noetica.STATE_INDEX`, which is the single authority for the mapping between
    a state label and a state-vector index.
    """
    return math.fsum(
        state.component(STATE_INDEX[f"{tier}{noetic}"]) for tier in DOMAIN_TIERS
    )


def _domain_mass(state: CognitiveStateVector, tier: str) -> float:
    return math.fsum(
        state.component(STATE_INDEX[f"{tier}{noetic}"]) for noetic in range(NOETIC_COUNT)
    )


def involution_axis(dials: DialProfile) -> AxisMeasurement:
    """Axis ``N``. The instruction freezes one limit here, so this axis judges.

    ``max |dial(a) − dial(b)|`` over the three frozen involution pairs, against the frozen
    limit of 4.
    """
    divergences = {
        f"^%d-^%d" % pair: dials.divergence(*pair) for pair in INVOLUTION_PAIRS
    }
    worst = max(divergences.values())
    return AxisMeasurement(
        axis=Axis.NOETIC_INVOLUTION,
        measurement=float(worst),
        unit="dial points",
        frozen_limit=float(MAX_INVOLUTION_DIAL_DIVERGENCE),
        exceeds_frozen_limit=worst > MAX_INVOLUTION_DIAL_DIVERGENCE,
        detail={"pair_divergences": divergences, "self_dual": [f"^{i}" for i in SELF_DUAL_NOETICS]},
    )


def involution_mass_axis(state: CognitiveStateVector) -> AxisMeasurement:
    """Axis ``N``, state-vector reading. **No limit is frozen, so none is applied.**

    The relative mass imbalance of each involution pair. Reported raw: the instructions state
    the pairs but do not state how much imbalance is too much.
    """
    imbalances = {}
    for left, right in INVOLUTION_PAIRS:
        a, b = _noetic_mass(state, left), _noetic_mass(state, right)
        total = a + b
        imbalances[f"^{left}-^{right}"] = abs(a - b) / total if total else 0.0
    worst = max(imbalances.values()) if imbalances else 0.0
    return AxisMeasurement(
        axis=Axis.NOETIC_INVOLUTION,
        measurement=worst,
        unit="relative mass imbalance in [0,1]",
        frozen_limit=None,
        exceeds_frozen_limit=None,
        detail={"pair_imbalances": imbalances, "reading": "state vector, not dials"},
    )


def domain_precedence_axis(state: CognitiveStateVector) -> AxisMeasurement:
    """Axis ``W``. **No limit is frozen, so none is applied.**

    Counts adjacent tier inversions: a lower tier carrying more mass than the tier above it,
    along ``P ≻ C ≻ E ≻ O``. The tier order is frozen; the number of inversions that constitutes
    a violation is not, so the count is reported raw.
    """
    masses = {tier: _domain_mass(state, tier) for tier in DOMAIN_TIERS}
    inversions = []
    for higher, lower in zip(DOMAIN_TIERS, DOMAIN_TIERS[1:]):
        if masses[lower] > masses[higher]:
            inversions.append({"higher": higher, "lower": lower})
    return AxisMeasurement(
        axis=Axis.DOMAIN_PRECEDENCE,
        measurement=float(len(inversions)),
        unit="adjacent tier inversions",
        frozen_limit=None,
        exceeds_frozen_limit=None,
        detail={"domain_mass": masses, "inversions": inversions, "tiers": list(DOMAIN_TIERS)},
    )


def drive_pair_axis(profile: DriveProfile) -> AxisMeasurement:
    """Axis ``F``. **No limit is frozen, so none is applied.**

    ``max |F_a − F_b|`` over the frozen drive pairs. The pairs are frozen; the permitted gap is
    not.
    """
    gaps = {f"{left}-{right}": profile.gap(left, right) for left, right in DRIVE_PAIRS}
    return AxisMeasurement(
        axis=Axis.DRIVE_PAIR,
        measurement=max(gaps.values()),
        unit="drive units",
        frozen_limit=None,
        exceeds_frozen_limit=None,
        detail={"pair_gaps": gaps, "self_dual": SELF_DUAL_DRIVE},
    )


def entropy_deficit_axis(state: CognitiveStateVector) -> AxisMeasurement:
    """Axis ``E``. **No limit is frozen, so none is applied.**

    ``1 − H(p)/log 40`` using Correction 4's state space. ``0`` at the uniform point, tending to
    ``1`` as the state concentrates toward the boundary. The open simplex guarantees every
    component is strictly positive, so the entropy is always finite and always defined.
    """
    uniformity = state.uniformity()
    return AxisMeasurement(
        axis=Axis.ENTROPY_DEFICIT,
        measurement=1.0 - uniformity,
        unit="fraction of maximum entropy lost",
        frozen_limit=None,
        exceeds_frozen_limit=None,
        detail={
            "entropy_nats": state.entropy(),
            "maximum_entropy_nats": state.maximum_entropy(),
            "state_digest": state.digest(),
        },
    )


def subdrive_variance_axis(profile: SubDriveProfile) -> AxisMeasurement:
    """Axis ``S``. **No limit is frozen, so none is applied.**

    The largest cross-domain variance of any single drive over the four tiers, using the
    population variance of the four values.
    """
    variances = {}
    for drive in CANONICAL_DRIVES:
        values = profile.across_domains(drive)
        mean = math.fsum(values) / len(values)
        variances[drive] = math.fsum((value - mean) ** 2 for value in values) / len(values)
    return AxisMeasurement(
        axis=Axis.SUBDRIVE_VARIANCE,
        measurement=max(variances.values()),
        unit="population variance across the four domains",
        frozen_limit=None,
        exceeds_frozen_limit=None,
        detail={"per_drive_variance": variances, "domains": list(DOMAIN_TIERS)},
    )


def pathway_chain_axis(satisfied) -> AxisMeasurement:
    """Axis ``A``. The chain is frozen and one-directional, so this axis judges.

    A node is admitted out of order when it is satisfied while a prerequisite of it is not.
    The frozen chain ``A0 → Dn → Wn → Pn`` requires zero such admissions, so the limit here is
    ``0`` because the structure says so, not because a number was chosen.
    """
    satisfied = set(satisfied)
    unknown = sorted(node for node in satisfied if node not in PREREQUISITE)
    if unknown:
        raise InversionError(f"unknown pathway nodes: {unknown}")
    violations = []
    for node in sorted(satisfied):
        missing = [step for step in satisfied_chain(node) if step not in satisfied]
        if missing:
            violations.append({"node": node, "unsatisfied_prerequisites": missing})
    return AxisMeasurement(
        axis=Axis.PATHWAY_CHAIN,
        measurement=float(len(violations)),
        unit="nodes admitted before their prerequisites",
        frozen_limit=0.0,
        exceeds_frozen_limit=bool(violations),
        detail={"violations": violations, "pathway_nodes": list(PATHWAY_NODES)},
    )


def scan(
    *,
    dials: DialProfile | None = None,
    drives: DriveProfile | None = None,
    subdrives: SubDriveProfile | None = None,
    state: CognitiveStateVector | None = None,
    satisfied=(),
    include_state_readings: bool = True,
) -> InversionReport:
    """Measure every axis that has the inputs it needs, and judge only where a limit is frozen.

    ``dials`` supplies axis ``N`` in its frozen form. ``state`` supplies the state-vector
    reading of ``N`` as a second reading, plus axes ``W`` and ``E``. ``drives`` supplies ``F``,
    ``subdrives`` supplies ``S``, and ``satisfied`` supplies ``A``.

    The compound axis ``P`` is ``True`` when more than one axis exceeds a **frozen** limit. It
    cannot be triggered by an unfrozen reading, so no provisional number can produce a
    compound finding.
    """
    axes: list[AxisMeasurement] = []
    if dials is not None:
        axes.append(involution_axis(dials))
    if state is not None and include_state_readings:
        axes.append(involution_mass_axis(state))
        axes.append(domain_precedence_axis(state))
        axes.append(entropy_deficit_axis(state))
    if drives is not None:
        axes.append(drive_pair_axis(drives))
    if subdrives is not None:
        axes.append(subdrive_variance_axis(subdrives))
    if satisfied:
        axes.append(pathway_chain_axis(satisfied))
    if not axes:
        raise InversionError("scan needs at least one input to measure")

    exceeding = tuple(
        measurement.axis
        for measurement in axes
        if measurement.exceeds_frozen_limit is True
    )
    # An axis counts as judged when ANY of its readings has a frozen limit — ``N`` is judged
    # through its dial reading even though its state-vector reading has no limit. An axis with
    # no frozen reading anywhere is reported as unfrozen, and the specific readings without a
    # limit are listed separately so the state-vector reading of ``N`` is not hidden.
    frozen = tuple(
        axis
        for axis in dict.fromkeys(measurement.axis for measurement in axes)
        if any(
            measurement.frozen_limit is not None
            for measurement in axes
            if measurement.axis is axis
        )
    )
    unfrozen = tuple(
        axis
        for axis in dict.fromkeys(measurement.axis for measurement in axes)
        if axis not in frozen
    )
    unfrozen_readings = tuple(
        f"{measurement.axis.value}:{measurement.unit}"
        for measurement in axes
        if measurement.frozen_limit is None
    )
    return InversionReport(
        axes=tuple(axes),
        compound=len(exceeding) > 1,
        axes_exceeding_frozen_limits=exceeding,
        frozen_axes=frozen,
        unfrozen_axes=unfrozen,
        unfrozen_readings=unfrozen_readings,
        stealth="ABSENT_FROM_THE_INSTRUCTIONS",
        nccs_inversion_resistance=(
            "NOT_PRODUCED: the 15% NCCS component needs thresholds that are not frozen, and "
            "this module will not grant scoring authority to numbers it made up"
        ),
    )


def axis_profile() -> dict:
    """The structure this scanner enforces, and the limits it refuses to invent."""
    return {
        "schema": SCHEMA_VERSION,
        "correction": "7_INVERSION_AXES",
        "axes": [
            {"axis": "N", "name": "Operator / Noetic involution imbalance", "limit": "frozen"},
            {"axis": "W", "name": "Domain precedence violation", "limit": "NOT_FROZEN"},
            {"axis": "F", "name": "Drive pair imbalance", "limit": "NOT_FROZEN"},
            {"axis": "E", "name": "State-vector entropy deficit", "limit": "NOT_FROZEN"},
            {"axis": "S", "name": "Sub-Drive cross-domain variance", "limit": "NOT_FROZEN"},
            {"axis": "A", "name": "Pathway RPM chain violation", "limit": "frozen at 0"},
            {"axis": "P", "name": "Compound", "limit": "frozen: more than one axis"},
        ],
        "involution_pairs": [list(pair) for pair in INVOLUTION_PAIRS],
        "self_dual_noetics": list(SELF_DUAL_NOETICS),
        "drive_pairs": [list(pair) for pair in DRIVE_PAIRS],
        "domain_tiers": list(DOMAIN_TIERS),
        "dial_range": [MIN_DIAL, MAX_DIAL],
        "max_involution_dial_divergence": MAX_INVOLUTION_DIAL_DIVERGENCE,
        "stealth": "ABSENT_FROM_THE_INSTRUCTIONS",
        "num_states": NUM_STATES,
    }


__all__ = [
    "Axis",
    "AxisMeasurement",
    "DOMAIN_TIERS",
    "DRIVE_PAIRS",
    "DialOutOfRange",
    "DialProfile",
    "DriveProfile",
    "INVOLUTION_PAIRS",
    "InversionError",
    "InversionReport",
    "MAX_DIAL",
    "MAX_INVOLUTION_DIAL_DIVERGENCE",
    "MIN_DIAL",
    "NOETIC_COUNT",
    "SCHEMA_VERSION",
    "SELF_DUAL_DRIVE",
    "SELF_DUAL_NOETICS",
    "SubDriveProfile",
    "axis_profile",
    "domain_precedence_axis",
    "drive_pair_axis",
    "entropy_deficit_axis",
    "involution_axis",
    "involution_mass_axis",
    "pathway_chain_axis",
    "scan",
    "subdrive_variance_axis",
]
