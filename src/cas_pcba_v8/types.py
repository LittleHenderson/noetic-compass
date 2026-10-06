"""Typed CAS factors and PCBA port quantities.

The four CAS factors are modeled as a product of finite coordinate sets.  This
module does *not* call the factors geometrically orthogonal; no such theorem is
assumed.  A 40-cell Noetic/Domain cell is also kept distinct from a full CAS
state, which may additionally carry a Drive and Register.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from types import MappingProxyType
from typing import Mapping

from .integrity import require_safe_reference


class PcbaTypeError(ValueError):
    """Raised when a typed PCBA value is malformed."""


class Noetic(IntEnum):
    IDEA = 0
    MIND = 1
    POSITIVE = 2
    NEGATIVE = 3
    VIBRATION = 4
    FEMALE = 5
    MALE = 6
    RHYTHM = 7
    ABOVE_CAUSE = 8
    BELOW_EFFECT = 9


class Domain(str, Enum):
    PRINCIPLED = "P"
    COGNITIVE = "C"
    EVALUATIVE = "E"
    OPERATIONAL = "O"

    @property
    def precedence_rank(self) -> int:
        return {
            Domain.PRINCIPLED: 0,
            Domain.COGNITIVE: 1,
            Domain.EVALUATIVE: 2,
            Domain.OPERATIONAL: 3,
        }[self]


class Drive(str, Enum):
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"
    F6 = "F6"
    F7 = "F7"


class Register(str, Enum):
    TRANSCENDENT = "T"
    ANALYTICAL = "A"
    AFFECTIVE = "f"
    EMBODIED = "E"


@dataclass(frozen=True, slots=True)
class NdCell:
    """One of the 40 Noetic/Domain cells, ordered P0..P9, C0..O9."""

    domain: Domain
    noetic: Noetic

    def __post_init__(self) -> None:
        if type(self) is not NdCell:
            raise PcbaTypeError("NdCell subclasses are not accepted")
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.domain) is not Domain or type(self.noetic) is not Noetic:
            raise PcbaTypeError("NdCell requires typed Domain and Noetic factors")

    @property
    def label(self) -> str:
        self.revalidate()
        return f"{self.domain.value}{int(self.noetic)}"


CANONICAL_ND_CELLS: tuple[NdCell, ...] = tuple(
    NdCell(domain, noetic)
    for domain in Domain
    for noetic in Noetic
)
CANONICAL_ND_LABELS: tuple[str, ...] = tuple(
    f"{domain.value}{int(noetic)}"
    for domain in Domain
    for noetic in Noetic
)


@dataclass(frozen=True, slots=True)
class CasState:
    """A typed state in the finite CAS coordinate product.

    ``drive`` and ``register`` are optional because the inherited notation
    permits partial literals.  Their absence is explicit and never filled by a
    default or inferred from another state.
    """

    noetic: Noetic
    domain: Domain
    drive: Drive | None = None
    register: Register | None = None

    def __post_init__(self) -> None:
        if type(self) is not CasState:
            raise PcbaTypeError("CasState subclasses are not accepted")
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.noetic) is not Noetic:
            raise PcbaTypeError("CasState.noetic must be a Noetic")
        if type(self.domain) is not Domain:
            raise PcbaTypeError("CasState.domain must be a Domain")
        if self.drive is not None and type(self.drive) is not Drive:
            raise PcbaTypeError("CasState.drive must be a Drive or None")
        if self.register is not None and type(self.register) is not Register:
            raise PcbaTypeError("CasState.register must be a Register or None")

    def to_nd_cell(self) -> NdCell:
        """Project to the 40-cell address index, explicitly forgetting two axes."""

        self.revalidate()
        return NdCell(self.domain, self.noetic)

    @property
    def literal(self) -> str:
        self.revalidate()
        result = f"^{int(self.noetic)}^{self.domain.value}"
        if self.drive is not None:
            result += f"_{{{self.drive.value}}}"
        if self.register is not None:
            result += f"|{self.register.value}"
        return result


class PortDirection(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class SignalKind(str, Enum):
    ACTIVATION = "ACTIVATION"
    DECISION = "DECISION"
    CAS_STATE = "CAS_STATE"
    FINITE_STATE = "FINITE_STATE"
    MIXED_SIMPLEX_ADDRESS = "MIXED_SIMPLEX_ADDRESS"
    PROJECTOR_PROFILE = "PROJECTOR_PROFILE"
    TEXT = "TEXT"
    CLOCK = "CLOCK"
    SCALAR = "SCALAR"


class Unit(str, Enum):
    NONE = "NONE"
    ACTIVATION_0_1 = "ACTIVATION_0_1"
    BOOLEAN = "BOOLEAN"
    PROBABILITY = "PROBABILITY"
    NORMALIZED_0_10 = "NORMALIZED_0_10"
    CAS_OHM_SCORE = "CAS_OHM_SCORE"
    VOLT = "VOLT"
    SECOND = "SECOND"
    HERTZ = "HERTZ"


class MeasurementKind(str, Enum):
    DESIGN_VALUE = "DESIGN_VALUE"
    BEHAVIORAL_PROXY = "BEHAVIORAL_PROXY"
    INSTRUMENTED = "INSTRUMENTED"
    HUMAN_SCORE = "HUMAN_SCORE"
    LLM_SCORE = "LLM_SCORE"
    MODEL_DERIVED = "MODEL_DERIVED"


CANONICAL_UNITS_BY_SIGNAL: Mapping[SignalKind, frozenset[Unit]] = MappingProxyType({
    SignalKind.ACTIVATION: frozenset({Unit.ACTIVATION_0_1}),
    SignalKind.DECISION: frozenset({Unit.BOOLEAN}),
    SignalKind.CAS_STATE: frozenset({Unit.NONE}),
    SignalKind.FINITE_STATE: frozenset({Unit.NONE}),
    SignalKind.MIXED_SIMPLEX_ADDRESS: frozenset({Unit.PROBABILITY}),
    SignalKind.PROJECTOR_PROFILE: frozenset({Unit.NONE}),
    SignalKind.TEXT: frozenset({Unit.NONE}),
    SignalKind.CLOCK: frozenset({Unit.HERTZ}),
    SignalKind.SCALAR: frozenset(
        {
            Unit.NONE,
            Unit.PROBABILITY,
            Unit.NORMALIZED_0_10,
            Unit.CAS_OHM_SCORE,
            Unit.VOLT,
            Unit.SECOND,
            Unit.HERTZ,
        }
    ),
})


def canonical_signal_unit(signal_kind: SignalKind, unit: Unit) -> bool:
    if type(signal_kind) is not SignalKind or type(unit) is not Unit:
        return False
    return unit in CANONICAL_UNITS_BY_SIGNAL.get(signal_kind, frozenset())


@dataclass(frozen=True, slots=True)
class PortSpec:
    ref: str
    direction: PortDirection
    signal_kind: SignalKind
    unit: Unit
    required: bool = True

    def __post_init__(self) -> None:
        if type(self) is not PortSpec:
            raise PcbaTypeError("PortSpec subclasses are not accepted")
        self.revalidate()

    def revalidate(self) -> None:
        require_safe_reference(self.ref, "PortSpec.ref")
        if type(self.direction) is not PortDirection:
            raise PcbaTypeError("PortSpec.direction must be a PortDirection")
        if type(self.signal_kind) is not SignalKind:
            raise PcbaTypeError("PortSpec.signal_kind must be a SignalKind")
        if type(self.unit) is not Unit:
            raise PcbaTypeError("PortSpec.unit must be a Unit")
        if type(self.required) is not bool:
            raise PcbaTypeError("PortSpec.required must be bool")
