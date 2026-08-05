"""Immutable board-level model for the PCBA v8 research candidate."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Hashable, Mapping

from .arithmetic import DECIMAL_CONTEXT_SHA256, decimal_context_payload
from .finite_values import finite_value_payload
from .integrity import (
    engine_identity_payload,
    require_safe_reference,
    require_sha256,
    source_identity_payload,
)
from .types import (
    CasState,
    MeasurementKind,
    PortSpec,
    Unit,
)


BOARD_ENDPOINT = "$board"


class BoardIdentityError(ValueError):
    """Raised when a board cannot receive a canonical structural identity."""


def _tuple(value: object) -> tuple:
    return value if type(value) is tuple else tuple(value)  # type: ignore[arg-type]


def _freeze_metadata(value: object) -> object:
    """Recursively detach and freeze component metadata containers."""

    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            require_safe_reference(key, "component metadata key")
            frozen[key] = _freeze_metadata(item)
        return MappingProxyType(frozen)
    if type(value) in (tuple, list):
        return tuple(_freeze_metadata(item) for item in value)
    if type(value) in (set, frozenset):
        return frozenset(_freeze_metadata(item) for item in value)
    if type(value) in (str, int, float, bool, Decimal) or value is None:
        return value
    if type(value) is CasState:
        value.revalidate()
        return value
    if isinstance(value, Enum):
        return value
    raise TypeError(
        f"component metadata value {type(value).__name__!r} cannot be frozen canonically"
    )


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("component metadata must be a mapping")
    frozen = _freeze_metadata(value)
    assert isinstance(frozen, Mapping)
    return frozen


def _require_string(value: object, field_name: str) -> None:
    require_safe_reference(value, field_name)


@dataclass(frozen=True, slots=True)
class Endpoint:
    owner_ref: str
    port_ref: str

    def __post_init__(self) -> None:
        if type(self) is not Endpoint:
            raise TypeError("Endpoint subclasses are not accepted")
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not Endpoint:
            raise TypeError("Endpoint values must use the exact type")
        require_safe_reference(
            self.owner_ref,
            "Endpoint.owner_ref",
            allow_board_endpoint=True,
        )
        _require_string(self.port_ref, "Endpoint.port_ref")

    @classmethod
    def board(cls, port_ref: str) -> "Endpoint":
        return cls(BOARD_ENDPOINT, port_ref)


@dataclass(frozen=True, slots=True)
class Net:
    ref: str
    endpoints: tuple[Endpoint, ...]
    safety_critical: bool = False

    def __post_init__(self) -> None:
        if type(self) is not Net:
            raise TypeError("Net subclasses are not accepted")
        _require_string(self.ref, "Net.ref")
        object.__setattr__(self, "endpoints", _tuple(self.endpoints))
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not Net:
            raise TypeError("Net values must use the exact type")
        _require_string(self.ref, "Net.ref")
        if type(self.endpoints) is not tuple or any(
            type(item) is not Endpoint for item in self.endpoints
        ):
            raise TypeError("Net.endpoints must contain Endpoint values")
        for item in self.endpoints:
            item.revalidate()
        if type(self.safety_critical) is not bool:
            raise TypeError("Net.safety_critical must be bool")


@dataclass(frozen=True, slots=True)
class CalibrationRef:
    ref: str
    version: str
    profile_sha256: str
    measurement_kind: MeasurementKind
    unit: Unit
    instrument_identity: str
    protocol_identity: str
    uncertainty: Decimal
    packet_eligible: bool = False

    def __post_init__(self) -> None:
        if type(self) is not CalibrationRef:
            raise TypeError("CalibrationRef subclasses are not accepted")
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not CalibrationRef:
            raise TypeError("CalibrationRef values must use the exact type")
        for field_name in (
            "ref",
            "version",
            "instrument_identity",
            "protocol_identity",
        ):
            _require_string(
                getattr(self, field_name),
                f"CalibrationRef.{field_name}",
            )
        require_sha256(self.profile_sha256, "CalibrationRef.profile_sha256")
        if type(self.uncertainty) is not Decimal or not self.uncertainty.is_finite():
            raise TypeError("CalibrationRef.uncertainty must be a finite Decimal")
        if type(self.packet_eligible) is not bool:
            raise TypeError("CalibrationRef.packet_eligible must be bool")


@dataclass(frozen=True, slots=True)
class TestPoint:
    __test__ = False

    ref: str
    net_ref: str
    calibration_ref: str | None
    safety_critical: bool = False

    def __post_init__(self) -> None:
        if type(self) is not TestPoint:
            raise TypeError("TestPoint subclasses are not accepted")
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not TestPoint:
            raise TypeError("TestPoint values must use the exact type")
        _require_string(self.ref, "TestPoint.ref")
        _require_string(self.net_ref, "TestPoint.net_ref")
        if self.calibration_ref is not None:
            _require_string(self.calibration_ref, "TestPoint.calibration_ref")
        if type(self.safety_critical) is not bool:
            raise TypeError("TestPoint.safety_critical must be bool")


@dataclass(frozen=True, slots=True)
class FeedbackLoop:
    ref: str
    component_refs: tuple[str, ...]
    delay_component_ref: str
    max_round_trip_gain: Decimal
    calibration_ref: str

    def __post_init__(self) -> None:
        if type(self) is not FeedbackLoop:
            raise TypeError("FeedbackLoop subclasses are not accepted")
        _require_string(self.ref, "FeedbackLoop.ref")
        object.__setattr__(self, "component_refs", _tuple(self.component_refs))
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not FeedbackLoop:
            raise TypeError("FeedbackLoop values must use the exact type")
        _require_string(self.ref, "FeedbackLoop.ref")
        if type(self.component_refs) is not tuple or any(
            type(item) is not str for item in self.component_refs
        ):
            raise TypeError("FeedbackLoop.component_refs must contain strings")
        for item in self.component_refs:
            _require_string(item, "FeedbackLoop.component_refs item")
        _require_string(
            self.delay_component_ref,
            "FeedbackLoop.delay_component_ref",
        )
        _require_string(self.calibration_ref, "FeedbackLoop.calibration_ref")
        if (
            type(self.max_round_trip_gain) is not Decimal
            or not self.max_round_trip_gain.is_finite()
        ):
            raise TypeError("FeedbackLoop.max_round_trip_gain must be finite Decimal")


def _finite_payload(
    profile: str,
    source_name: str,
    source_elements: tuple[Hashable, ...],
    target_name: str,
    target_elements: tuple[Hashable, ...],
    mapping: tuple[int, ...],
) -> bytes:
    payload = {
        "identity_schema": "cas-pcba-v8.finite-transition-table.v1",
        "mapping": [
            {"type": "int", "value": str(image)}
            for image in mapping
        ],
        "profile": profile,
        "source_elements": [finite_value_payload(item) for item in source_elements],
        "source_name": source_name,
        "target_elements": [finite_value_payload(item) for item in target_elements],
        "target_name": target_name,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class FiniteTransitionSemantics:
    """Self-consistency certificate for a finite deterministic transition.

    The digest establishes exact transition-table identity only.  It is not an
    external review, safety license, or claim that the labels have CAS meaning.
    """

    profile: str
    source_name: str
    source_elements: tuple[Hashable, ...]
    target_name: str
    target_elements: tuple[Hashable, ...]
    mapping: tuple[int, ...]
    certificate_sha256: str
    total: bool = True
    deterministic: bool = True
    stateful: bool = False
    stochastic: bool = False

    def __post_init__(self) -> None:
        if type(self) is not FiniteTransitionSemantics:
            raise TypeError("FiniteTransitionSemantics subclasses are not accepted")
        _require_string(self.profile, "FiniteTransitionSemantics.profile")
        _require_string(
            self.source_name,
            "FiniteTransitionSemantics.source_name",
        )
        _require_string(
            self.target_name,
            "FiniteTransitionSemantics.target_name",
        )
        _require_string(
            self.certificate_sha256,
            "FiniteTransitionSemantics.certificate_sha256",
        )
        for field_name in ("total", "deterministic", "stateful", "stochastic"):
            if type(getattr(self, field_name)) is not bool:
                raise TypeError(f"FiniteTransitionSemantics.{field_name} must be bool")
        object.__setattr__(
            self,
            "source_elements",
            tuple(_freeze_metadata(item) for item in self.source_elements),
        )
        object.__setattr__(
            self,
            "target_elements",
            tuple(_freeze_metadata(item) for item in self.target_elements),
        )
        object.__setattr__(
            self,
            "mapping",
            tuple(_freeze_metadata(item) for item in self.mapping),
        )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not FiniteTransitionSemantics:
            raise TypeError("finite semantics must use the exact type")
        for field_name in ("profile", "source_name", "target_name"):
            _require_string(getattr(self, field_name), f"FiniteTransitionSemantics.{field_name}")
        require_sha256(
            self.certificate_sha256,
            "FiniteTransitionSemantics.certificate_sha256",
        )
        if type(self.source_elements) is not tuple or type(self.target_elements) is not tuple:
            raise TypeError("finite carriers must be exact tuples")
        for item in self.source_elements + self.target_elements:
            finite_value_payload(item)
        if type(self.mapping) is not tuple or any(type(item) is not int for item in self.mapping):
            raise TypeError("finite mapping must contain exact integers")
        for field_name in ("total", "deterministic", "stateful", "stochastic"):
            if type(getattr(self, field_name)) is not bool:
                raise TypeError(f"FiniteTransitionSemantics.{field_name} must be bool")

    @classmethod
    def certify(
        cls,
        *,
        profile: str,
        source_name: str,
        source_elements: tuple[Hashable, ...],
        target_name: str,
        target_elements: tuple[Hashable, ...],
        mapping: tuple[int, ...],
    ) -> "FiniteTransitionSemantics":
        if cls is not FiniteTransitionSemantics:
            raise TypeError("finite semantics subclasses are not accepted")
        source = _tuple(source_elements)
        target = _tuple(target_elements)
        images = _tuple(mapping)
        digest = hashlib.sha256(
            _finite_payload(profile, source_name, source, target_name, target, images)
        ).hexdigest().upper()
        return cls(
            profile=profile,
            source_name=source_name,
            source_elements=source,
            target_name=target_name,
            target_elements=target,
            mapping=images,
            certificate_sha256=digest,
        )

    def computed_sha256(self) -> str:
        self.revalidate()
        return hashlib.sha256(
            _finite_payload(
                self.profile,
                self.source_name,
                self.source_elements,
                self.target_name,
                self.target_elements,
                self.mapping,
            )
        ).hexdigest().upper()

    def with_mapping(self, mapping: tuple[int, ...]) -> "FiniteTransitionSemantics":
        """Return a deliberately uncertified mutation, useful for negative tests."""

        return replace(self, mapping=_tuple(mapping))


@dataclass(frozen=True, slots=True)
class ComponentInstance:
    ref: str
    kind: str
    semantic_profile: str
    parameters: Mapping[str, object] = field(default_factory=dict)
    state_bindings: Mapping[str, CasState] = field(default_factory=dict)
    safety_critical: bool = False
    finite_transition: FiniteTransitionSemantics | None = None

    def __post_init__(self) -> None:
        if type(self) is not ComponentInstance:
            raise TypeError("ComponentInstance subclasses are not accepted")
        _require_string(self.ref, "ComponentInstance.ref")
        _require_string(self.kind, "ComponentInstance.kind")
        _require_string(
            self.semantic_profile,
            "ComponentInstance.semantic_profile",
        )
        if type(self.safety_critical) is not bool:
            raise TypeError("ComponentInstance.safety_critical must be bool")
        if self.finite_transition is not None and type(
            self.finite_transition
        ) is not FiniteTransitionSemantics:
            raise TypeError(
                "ComponentInstance.finite_transition must be typed or None"
            )
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))
        object.__setattr__(
            self,
            "state_bindings",
            _freeze_mapping(self.state_bindings),
        )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not ComponentInstance:
            raise TypeError("ComponentInstance values must use the exact type")
        for field_name in ("ref", "kind", "semantic_profile"):
            _require_string(getattr(self, field_name), f"ComponentInstance.{field_name}")
        if type(self.safety_critical) is not bool:
            raise TypeError("ComponentInstance.safety_critical must be bool")
        if type(self.parameters) is not MappingProxyType or type(
            self.state_bindings
        ) is not MappingProxyType:
            raise TypeError("component metadata must remain recursively frozen")
        _canonical_value(self.parameters)
        _canonical_value(self.state_bindings)
        if self.finite_transition is not None:
            if type(self.finite_transition) is not FiniteTransitionSemantics:
                raise TypeError("component finite semantics must use the exact type")
            self.finite_transition.revalidate()


@dataclass(frozen=True, slots=True)
class Board:
    ref: str
    version: str
    ports: tuple[PortSpec, ...]
    components: tuple[ComponentInstance, ...]
    nets: tuple[Net, ...]
    test_points: tuple[TestPoint, ...] = ()
    calibrations: tuple[CalibrationRef, ...] = ()
    feedback_loops: tuple[FeedbackLoop, ...] = ()

    def __post_init__(self) -> None:
        if type(self) is not Board:
            raise TypeError("Board subclasses are not accepted")
        _require_string(self.ref, "Board.ref")
        _require_string(self.version, "Board.version")
        for name in (
            "ports",
            "components",
            "nets",
            "test_points",
            "calibrations",
            "feedback_loops",
        ):
            object.__setattr__(self, name, _tuple(getattr(self, name)))
        expected_types = {
            "ports": PortSpec,
            "components": ComponentInstance,
            "nets": Net,
            "test_points": TestPoint,
            "calibrations": CalibrationRef,
            "feedback_loops": FeedbackLoop,
        }
        for field_name, expected_type in expected_types.items():
            if any(
                type(item) is not expected_type
                for item in getattr(self, field_name)
            ):
                raise TypeError(
                    f"Board.{field_name} must contain {expected_type.__name__} values"
                )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not Board:
            raise TypeError("board values must use the exact type")
        _require_string(self.ref, "Board.ref")
        _require_string(self.version, "Board.version")
        expected_types = {
            "ports": PortSpec,
            "components": ComponentInstance,
            "nets": Net,
            "test_points": TestPoint,
            "calibrations": CalibrationRef,
            "feedback_loops": FeedbackLoop,
        }
        for field_name, expected_type in expected_types.items():
            values = getattr(self, field_name)
            if type(values) is not tuple or any(type(item) is not expected_type for item in values):
                raise TypeError(
                    f"Board.{field_name} must contain exact "
                    f"{expected_type.__name__} values"
                )
            for item in values:
                item.revalidate()

    @property
    def structural_sha256(self) -> str:
        """Canonical SHA-256 over the complete immutable board structure."""

        return board_sha256(self)


def _canonical_value(value: object) -> object:
    """Encode typed metadata without collapsing distinct Python scalar types."""

    if value is None:
        return {"type": "none"}
    if type(value) is bool:
        return {"type": "bool", "value": value}
    if type(value) is int:
        return {"type": "int", "value": str(value)}
    if type(value) is float:
        if math.isnan(value):
            text = "NaN"
        elif math.isinf(value):
            text = "Infinity" if value > 0 else "-Infinity"
        else:
            text = value.hex()
        return {"type": "binary64", "value": text}
    if type(value) is Decimal:
        return {"type": "decimal", "value": str(value)}
    if type(value) is CasState:
        value.revalidate()
        return {
            "type": "cas-state",
            "noetic": int(value.noetic),
            "domain": value.domain.value,
            "drive": value.drive.value if value.drive is not None else None,
            "register": value.register.value if value.register is not None else None,
        }
    if isinstance(value, Enum):
        return {
            "type": "enum",
            "class": f"{type(value).__module__}.{type(value).__qualname__}",
            "value": _canonical_value(value.value),
        }
    if type(value) is str:
        return {"type": "string", "value": value}
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise BoardIdentityError("canonical metadata mappings require string keys")
        return {
            "type": "mapping",
            "items": [
                [key, _canonical_value(value[key])]
                for key in sorted(value)
            ],
        }
    if isinstance(value, (tuple, list)):
        return {
            "type": "sequence",
            "items": [_canonical_value(item) for item in value],
        }
    if isinstance(value, (set, frozenset)):
        items = [_canonical_value(item) for item in value]
        items.sort(key=_canonical_json)
        return {"type": "set", "items": items}
    raise BoardIdentityError(
        f"value of type {type(value).__name__!r} has no canonical board encoding"
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _finite_transition_payload(
    semantics: FiniteTransitionSemantics | None,
) -> object:
    if semantics is None:
        return None
    return {
        "profile": semantics.profile,
        "source_name": semantics.source_name,
        "source_elements": [
            _canonical_value(item) for item in semantics.source_elements
        ],
        "target_name": semantics.target_name,
        "target_elements": [
            _canonical_value(item) for item in semantics.target_elements
        ],
        "mapping": [_canonical_value(item) for item in semantics.mapping],
        "certificate_sha256": semantics.certificate_sha256,
        "total": semantics.total,
        "deterministic": semantics.deterministic,
        "stateful": semantics.stateful,
        "stochastic": semantics.stochastic,
    }


def canonical_component_payload(
    component: ComponentInstance,
) -> dict[str, object]:
    if type(component) is not ComponentInstance:
        raise TypeError("canonical_component_payload requires ComponentInstance")
    component.revalidate()
    return {
        "identity_schema": "cas-pcba-v8.component-identity.v1",
        "ref": component.ref,
        "kind": component.kind,
        "semantic_profile": component.semantic_profile,
        "parameters": _canonical_value(component.parameters),
        "state_bindings": _canonical_value(component.state_bindings),
        "safety_critical": _canonical_value(component.safety_critical),
        "finite_transition": _finite_transition_payload(
            component.finite_transition
        ),
        "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
    }


def component_sha256(component: ComponentInstance) -> str:
    return hashlib.sha256(
        _canonical_json(canonical_component_payload(component)).encode("utf-8")
    ).hexdigest().upper()


def canonical_board_payload(board: Board) -> dict[str, object]:
    """Return the versioned, order-insensitive canonical board payload."""

    if type(board) is not Board:
        raise TypeError("canonical_board_payload requires a Board")
    board.revalidate()
    from .contracts import component_catalog_sha256

    catalog_sha256 = component_catalog_sha256()
    return {
        "identity_schema": "cas-pcba-v8.board-identity.v2",
        "source": source_identity_payload(),
        "engine": engine_identity_payload(catalog_sha256=catalog_sha256),
        "catalog_sha256": catalog_sha256,
        "decimal_context": decimal_context_payload(),
        "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
        "ref": board.ref,
        "version": board.version,
        "ports": [
            {
                "ref": port.ref,
                "direction": _canonical_value(port.direction),
                "signal_kind": _canonical_value(port.signal_kind),
                "unit": _canonical_value(port.unit),
                "required": _canonical_value(port.required),
            }
            for port in sorted(board.ports, key=lambda item: item.ref)
        ],
        "components": [
            canonical_component_payload(component)
            for component in sorted(board.components, key=lambda item: item.ref)
        ],
        "nets": [
            {
                "ref": net.ref,
                "safety_critical": _canonical_value(net.safety_critical),
                "endpoints": [
                    {
                        "owner_ref": endpoint.owner_ref,
                        "port_ref": endpoint.port_ref,
                    }
                    for endpoint in sorted(
                        net.endpoints,
                        key=lambda item: (item.owner_ref, item.port_ref),
                    )
                ],
            }
            for net in sorted(board.nets, key=lambda item: item.ref)
        ],
        "test_points": [
            {
                "ref": point.ref,
                "net_ref": point.net_ref,
                "calibration_ref": point.calibration_ref,
                "safety_critical": _canonical_value(point.safety_critical),
            }
            for point in sorted(board.test_points, key=lambda item: item.ref)
        ],
        "calibrations": [
            {
                "ref": calibration.ref,
                "version": calibration.version,
                "profile_sha256": calibration.profile_sha256,
                "measurement_kind": _canonical_value(
                    calibration.measurement_kind
                ),
                "unit": _canonical_value(calibration.unit),
                "instrument_identity": calibration.instrument_identity,
                "protocol_identity": calibration.protocol_identity,
                "uncertainty": _canonical_value(calibration.uncertainty),
                "packet_eligible": _canonical_value(
                    calibration.packet_eligible
                ),
            }
            for calibration in sorted(
                board.calibrations,
                key=lambda item: item.ref,
            )
        ],
        "feedback_loops": [
            {
                "ref": loop.ref,
                "component_refs": sorted(loop.component_refs),
                "delay_component_ref": loop.delay_component_ref,
                "max_round_trip_gain": _canonical_value(
                    loop.max_round_trip_gain
                ),
                "calibration_ref": loop.calibration_ref,
            }
            for loop in sorted(board.feedback_loops, key=lambda item: item.ref)
        ],
    }


def board_sha256(board: Board) -> str:
    """Return an uppercase SHA-256 over the exact canonical board payload."""

    payload = canonical_board_payload(board)
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest().upper()
