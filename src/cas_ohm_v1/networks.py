"""Typed active-region topology and gain composition."""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from decimal import Decimal
from enum import Enum
from itertools import pairwise

from .calibration import OperationContext
from .canonical import (
    ValidationError,
    arithmetic_context,
    canonical_sha256,
    require_decimal,
    require_text,
)
from .evidence import parent_ref
from .model import (
    _NETWORK_FACTORY_TOKEN,
    ArtifactRef,
    Capability,
    DoseResponseRegion,
    FieldProvenance,
    MeasurementKind,
    MeasurementValue,
    QuantityKind,
    ResistanceRole,
    Uncertainty,
    UnitKind,
    validate_quantity_unit,
)


def _unique_refs(values: tuple[MeasurementValue, ...]) -> tuple[ArtifactRef, ...]:
    refs: dict[str, ArtifactRef] = {}
    for value in values:
        for ref in value.provenance.source_refs:
            existing = refs.get(ref.sha256)
            if existing is not None and existing != ref:
                raise ValidationError("conflicting artifact metadata for one digest")
            refs[ref.sha256] = ref
    return tuple(refs[digest] for digest in sorted(refs))


def _confidence(values: tuple[MeasurementValue, ...]) -> Decimal:
    if any(value.uncertainty is None for value in values):
        raise ValidationError("aggregate inputs require uncertainty")
    return min(
        value.uncertainty.confidence_level for value in values if value.uncertainty
    )


@dataclass(frozen=True, slots=True)
class CoordinateIdentity:
    coordinate_id: str
    quantity_kind: QuantityKind
    unit: UnitKind
    test_point_sha256: str

    def __post_init__(self) -> None:
        require_text(self.coordinate_id, "coordinate_id")
        if type(self.quantity_kind) is not QuantityKind:
            raise ValidationError("quantity_kind must be exact QuantityKind")
        if type(self.unit) is not UnitKind:
            raise ValidationError("unit must be exact UnitKind")
        validate_quantity_unit(self.quantity_kind, self.unit)
        from .canonical import require_sha256

        require_sha256(self.test_point_sha256, "test_point_sha256")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "coordinate_id": self.coordinate_id,
            "quantity_kind": self.quantity_kind,
            "test_point_sha256": self.test_point_sha256,
            "unit": self.unit,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class ResistanceComponent:
    component_id: str
    resistance: MeasurementValue
    source_node: CoordinateIdentity
    target_node: CoordinateIdentity
    region: DoseResponseRegion
    linearity_r2: Decimal

    def __post_init__(self) -> None:
        require_text(self.component_id, "component_id")
        if type(self.resistance) is not MeasurementValue:
            raise ValidationError("resistance must be exact MeasurementValue")
        if self.resistance.quantity_kind is not QuantityKind.EFFECTIVE_RESISTANCE:
            raise ValidationError("component resistance must be EFFECTIVE_RESISTANCE")
        if self.resistance.resistance_role not in {
            ResistanceRole.CALIBRATED_HELD_OUT,
            ResistanceRole.NETWORK_EQUIVALENT,
        }:
            raise ValidationError(
                "component requires calibrated or network-equivalent resistance"
            )
        if (
            type(self.source_node) is not CoordinateIdentity
            or type(self.target_node) is not CoordinateIdentity
        ):
            raise ValidationError("component nodes must be CoordinateIdentity values")
        for node in (self.source_node, self.target_node):
            if (
                node.quantity_kind is not QuantityKind.DRIVE_INTERVENTION
                or node.unit is not UnitKind.ALPHA
            ):
                raise ValidationError(
                    "resistance topology nodes must be ALPHA drive coordinates"
                )
        if self.source_node.test_point_sha256 != self.target_node.test_point_sha256:
            raise ValidationError("component nodes must bind the same test point")
        if self.source_node == self.target_node:
            raise ValidationError("resistance component cannot be a self-loop")
        if self.region is not DoseResponseRegion.ACTIVE:
            raise ValidationError(
                "resistance component must be validated in the ACTIVE region"
            )
        linearity = require_decimal(self.linearity_r2, "linearity_r2")
        if not Decimal("0") <= linearity <= Decimal("1"):
            raise ValidationError("linearity_r2 must be in [0, 1]")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "linearity_r2": self.linearity_r2,
            "region": self.region,
            "resistance": self.resistance,
            "source_node": self.source_node,
            "target_node": self.target_node,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


class NetworkKind(str, Enum):
    SERIES = "SERIES"
    PARALLEL = "PARALLEL"


_NETWORK_RESULT_TOKEN = object()


@dataclass(frozen=True, slots=True)
class NetworkResult:
    kind: NetworkKind
    equivalent: MeasurementValue
    components: tuple[ResistanceComponent, ...]
    _factory_token: InitVar[object] = None

    def __post_init__(self, _factory_token: object) -> None:
        if _factory_token is not _NETWORK_RESULT_TOKEN:
            raise ValidationError("network results are factory-only")
        if type(self.kind) is not NetworkKind:
            raise ValidationError("kind must be an exact NetworkKind")
        if type(self.equivalent) is not MeasurementValue:
            raise ValidationError("equivalent must be an exact MeasurementValue")
        if self.equivalent.resistance_role is not ResistanceRole.NETWORK_EQUIVALENT:
            raise ValidationError("equivalent must have NETWORK_EQUIVALENT role")
        if type(self.components) is not tuple or len(self.components) < 2:
            raise ValidationError(
                "network result must retain at least two child components"
            )
        if any(type(value) is not ResistanceComponent for value in self.components):
            raise ValidationError("network children must be exact components")
        expected = tuple(
            parent_ref(f"component[{index}]", index, component)
            for index, component in enumerate(self.components)
        )
        if self.equivalent.provenance.derivation_parents != expected:
            raise ValidationError("network equivalent does not bind exact children")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "components": self.components,
            "equivalent": self.equivalent,
            "kind": self.kind,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


def _validate_components(
    context: OperationContext,
    components: tuple[ResistanceComponent, ...],
) -> tuple[MeasurementValue, ...]:
    if type(components) is not tuple or len(components) < 2:
        raise ValidationError("network topology requires at least two components")
    if any(type(component) is not ResistanceComponent for component in components):
        raise ValidationError("components must contain ResistanceComponent values")
    if len({component.component_id for component in components}) != len(components):
        raise ValidationError("component identities must be unique")
    if len({component.sha256 for component in components}) != len(components):
        raise ValidationError("duplicate network children are forbidden")
    values = tuple(component.resistance for component in components)
    if len({value.sha256 for value in values}) != len(values):
        raise ValidationError("duplicate component resistances are forbidden")
    for component, value in zip(components, values):
        context.validate_measurement(value)
        if value.resistance_role is ResistanceRole.NETWORK_EQUIVALENT:
            replay_network_equivalent(context, value)
        if component.linearity_r2 < context.profile.tolerances.linearity_r2_min:
            raise ValidationError(
                "component linearity is below the calibrated threshold"
            )
        point = value.provenance.test_point
        if point is None or component.source_node.test_point_sha256 != point.sha256:
            raise ValidationError(
                "component topology and resistance test points differ"
            )
        if value.uncertainty is None or value.uncertainty.lower <= 0:
            raise ValidationError(
                "component resistance requires positive uncertainty bounds"
            )
        if value.sample_size is None:
            raise ValidationError(
                "component resistance requires a recorded sample size"
            )
    if any(
        value.provenance.test_point != values[0].provenance.test_point
        for value in values[1:]
    ):
        raise ValidationError("network components must bind one test point")
    return values


def _network_provenance(
    context: OperationContext,
    components: tuple[ResistanceComponent, ...],
    capability: Capability,
    method_id: str,
) -> FieldProvenance:
    values = tuple(component.resistance for component in components)
    return FieldProvenance(
        source_refs=_unique_refs(values),
        method_id=method_id,
        calibration_profile_sha256=context.profile.sha256,
        test_point=values[0].provenance.test_point,
        control_refs=context.profile.control_refs,
        control_bindings=context.profile.control_bindings,
        dataset_split_ref=context.profile.validation_split_ref,
        derivation_parents=tuple(
            parent_ref(f"component[{index}]", index, component)
            for index, component in enumerate(components)
        ),
        operation_binding=context.operation_binding(
            capability, require_integrity=False
        ),
    )


def series_equivalent(
    context: OperationContext,
    components: tuple[ResistanceComponent, ...],
) -> NetworkResult:
    values = _validate_components(context, components)
    for left, right in pairwise(components):
        if left.target_node != right.source_node:
            raise ValidationError("series topology is not a contiguous directed chain")
    directed_path = (components[0].source_node,) + tuple(
        component.target_node for component in components
    )
    if len(set(directed_path)) != len(directed_path):
        raise ValidationError("series topology must be a simple acyclic directed path")
    provenance = _network_provenance(
        context, components, Capability.SERIES_EQUIVALENCE, "CAS-OHM-V1-SERIES-TOPOLOGY"
    )
    with arithmetic_context():
        value = sum((item.value for item in values), Decimal("0"))
        lower = sum(
            (item.uncertainty.lower for item in values if item.uncertainty),
            Decimal("0"),
        )
        upper = sum(
            (item.uncertainty.upper for item in values if item.uncertainty),
            Decimal("0"),
        )
        variance = sum(
            (
                item.uncertainty.standard_uncertainty
                * item.uncertainty.standard_uncertainty
                for item in values
                if item.uncertainty
            ),
            Decimal("0"),
        )
        standard = variance.sqrt()
    uncertainty = Uncertainty(
        UnitKind.ALPHA_PER_ACTIVATION,
        standard,
        lower,
        max(value, upper),
        _confidence(values),
        context.profile.uncertainty_method_id,
    )
    equivalent = MeasurementValue(
        "R_series",
        QuantityKind.EFFECTIVE_RESISTANCE,
        value,
        UnitKind.ALPHA_PER_ACTIVATION,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        uncertainty,
        min(item.sample_size for item in values if item.sample_size is not None),
        ResistanceRole.NETWORK_EQUIVALENT,
        _factory_token=_NETWORK_FACTORY_TOKEN,
    )
    return NetworkResult(
        NetworkKind.SERIES,
        equivalent,
        components,
        _factory_token=_NETWORK_RESULT_TOKEN,
    )


def parallel_equivalent(
    context: OperationContext,
    components: tuple[ResistanceComponent, ...],
) -> NetworkResult:
    values = _validate_components(context, components)
    endpoints = {(item.source_node, item.target_node) for item in components}
    if len(endpoints) != 1:
        raise ValidationError("parallel topology requires identical directed endpoints")
    provenance = _network_provenance(
        context,
        components,
        Capability.PARALLEL_EQUIVALENCE,
        "CAS-OHM-V1-PARALLEL-TOPOLOGY",
    )
    with arithmetic_context():
        reciprocal = sum((Decimal("1") / item.value for item in values), Decimal("0"))
        value = Decimal("1") / reciprocal
        lower = Decimal("1") / sum(
            (
                Decimal("1") / item.uncertainty.lower
                for item in values
                if item.uncertainty
            ),
            Decimal("0"),
        )
        upper = Decimal("1") / sum(
            (
                Decimal("1") / item.uncertainty.upper
                for item in values
                if item.uncertainty
            ),
            Decimal("0"),
        )
        variance = sum(
            (
                ((value / item.value) ** 2 * item.uncertainty.standard_uncertainty) ** 2
                for item in values
                if item.uncertainty
            ),
            Decimal("0"),
        )
        standard = variance.sqrt()
    uncertainty = Uncertainty(
        UnitKind.ALPHA_PER_ACTIVATION,
        standard,
        lower,
        max(value, upper),
        _confidence(values),
        context.profile.uncertainty_method_id,
    )
    equivalent = MeasurementValue(
        "R_parallel",
        QuantityKind.EFFECTIVE_RESISTANCE,
        value,
        UnitKind.ALPHA_PER_ACTIVATION,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        uncertainty,
        min(item.sample_size for item in values if item.sample_size is not None),
        ResistanceRole.NETWORK_EQUIVALENT,
        _factory_token=_NETWORK_FACTORY_TOKEN,
    )
    return NetworkResult(
        NetworkKind.PARALLEL,
        equivalent,
        components,
        _factory_token=_NETWORK_RESULT_TOKEN,
    )


def replay_network_equivalent(
    context: OperationContext, resistance: MeasurementValue
) -> NetworkResult:
    """Resolve exact children and replay a network value before downstream use."""

    if type(resistance) is not MeasurementValue or (
        resistance.resistance_role is not ResistanceRole.NETWORK_EQUIVALENT
    ):
        raise ValidationError("replay requires a NETWORK_EQUIVALENT measurement")
    context.validate_measurement(resistance)
    parents = resistance.provenance.derivation_parents
    components: list[ResistanceComponent] = []
    for index, parent in enumerate(parents):
        if parent.role != f"component[{index}]":
            raise ValidationError("network parent roles are not canonical")
        resolved = context.evidence.require_parent(parent)
        if type(resolved) is not ResistanceComponent:
            raise ValidationError("network parent is not a ResistanceComponent")
        components.append(resolved)
    children = tuple(components)
    method_id = resistance.provenance.method_id
    if method_id == "CAS-OHM-V1-SERIES-TOPOLOGY":
        replayed = series_equivalent(context, children)
    elif method_id == "CAS-OHM-V1-PARALLEL-TOPOLOGY":
        replayed = parallel_equivalent(context, children)
    else:
        raise ValidationError("network equivalent uses an unknown topology method")
    if replayed.equivalent.sha256 != resistance.sha256:
        raise ValidationError("network equivalent failed exact factory replay")
    return replayed


@dataclass(frozen=True, slots=True)
class GainStage:
    stage_id: str
    gain: MeasurementValue
    source_coordinate: CoordinateIdentity
    target_coordinate: CoordinateIdentity
    region: DoseResponseRegion
    linearity_r2: Decimal

    def __post_init__(self) -> None:
        require_text(self.stage_id, "stage_id")
        if type(self.gain) is not MeasurementValue:
            raise ValidationError("gain must be exact MeasurementValue")
        if (
            self.gain.quantity_kind is not QuantityKind.GAIN_MAGNITUDE
            or self.gain.unit is not UnitKind.DIMENSIONLESS
        ):
            raise ValidationError("gain must be dimensionless GAIN_MAGNITUDE")
        if (
            type(self.source_coordinate) is not CoordinateIdentity
            or type(self.target_coordinate) is not CoordinateIdentity
        ):
            raise ValidationError(
                "gain coordinates must be typed CoordinateIdentity values"
            )
        if (
            self.source_coordinate.quantity_kind
            is not self.target_coordinate.quantity_kind
            or self.source_coordinate.unit is not self.target_coordinate.unit
        ):
            raise ValidationError(
                "dimensionless gain cannot map unlike quantity/unit coordinates"
            )
        if (
            self.source_coordinate.test_point_sha256
            != self.target_coordinate.test_point_sha256
        ):
            raise ValidationError("gain coordinates must bind one test point")
        if self.region is not DoseResponseRegion.ACTIVE:
            raise ValidationError("gain stage must be ACTIVE")
        linearity = require_decimal(self.linearity_r2, "linearity_r2")
        if not Decimal("0") <= linearity <= Decimal("1"):
            raise ValidationError("linearity_r2 must be in [0, 1]")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "gain": self.gain,
            "linearity_r2": self.linearity_r2,
            "region": self.region,
            "source_coordinate": self.source_coordinate,
            "stage_id": self.stage_id,
            "target_coordinate": self.target_coordinate,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


_GAIN_RESULT_TOKEN = object()


@dataclass(frozen=True, slots=True)
class GainCompositionResult:
    composed_gain: MeasurementValue
    stages: tuple[GainStage, ...]
    _factory_token: InitVar[object] = None

    def __post_init__(self, _factory_token: object) -> None:
        if _factory_token is not _GAIN_RESULT_TOKEN:
            raise ValidationError("gain-composition results are factory-only")
        if type(self.composed_gain) is not MeasurementValue:
            raise ValidationError("composed_gain must be exact MeasurementValue")
        if (
            type(self.stages) is not tuple
            or not self.stages
            or any(type(stage) is not GainStage for stage in self.stages)
        ):
            raise ValidationError("stages must be an exact non-empty stage tuple")

    def canonical_payload(self) -> dict[str, object]:
        return {"composed_gain": self.composed_gain, "stages": self.stages}

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


def compose_gains(
    context: OperationContext,
    stages: tuple[GainStage, ...],
) -> GainCompositionResult:
    if type(stages) is not tuple or not stages:
        raise ValidationError("gain composition requires a non-empty tuple")
    if any(type(stage) is not GainStage for stage in stages):
        raise ValidationError("stages must contain GainStage values")
    if len({stage.stage_id for stage in stages}) != len(stages):
        raise ValidationError("gain stage ids must be unique")
    values = tuple(stage.gain for stage in stages)
    for stage in stages:
        context.validate_measurement(stage.gain)
        if stage.linearity_r2 < context.profile.tolerances.linearity_r2_min:
            raise ValidationError(
                "gain-stage linearity is below the calibrated threshold"
            )
        point = stage.gain.provenance.test_point
        if point is None or stage.source_coordinate.test_point_sha256 != point.sha256:
            raise ValidationError("gain coordinate and measurement test points differ")
        if stage.gain.uncertainty is None:
            raise ValidationError("gain stage requires uncertainty")
        if stage.gain.sample_size is None:
            raise ValidationError("gain stage requires a recorded sample size")
    for left, right in pairwise(stages):
        if left.target_coordinate != right.source_coordinate:
            raise ValidationError("adjacent typed gain coordinates do not compose")
    coordinate_path = (stages[0].source_coordinate,) + tuple(
        stage.target_coordinate for stage in stages
    )
    if len(set(coordinate_path)) != len(coordinate_path):
        raise ValidationError("gain topology must be a simple acyclic directed path")
    with arithmetic_context():
        product = Decimal("1")
        for value in values:
            product *= value.value
        lower = Decimal("1")
        upper = Decimal("1")
        for value in values:
            lower *= value.uncertainty.lower
            upper *= value.uncertainty.upper
        variance = Decimal("0")
        for index, value in enumerate(values):
            derivative = Decimal("1")
            for other_index, other in enumerate(values):
                if other_index != index:
                    derivative *= other.value
            variance += (derivative * value.uncertainty.standard_uncertainty) ** 2
        standard = variance.sqrt()
    provenance = FieldProvenance(
        source_refs=_unique_refs(values),
        method_id="CAS-OHM-V1-TYPED-GAIN-COMPOSITION",
        calibration_profile_sha256=context.profile.sha256,
        test_point=values[0].provenance.test_point,
        control_refs=context.profile.control_refs,
        control_bindings=context.profile.control_bindings,
        dataset_split_ref=context.profile.validation_split_ref,
        derivation_parents=tuple(
            parent_ref(f"stage[{index}]", index, stage)
            for index, stage in enumerate(stages)
        ),
        operation_binding=context.operation_binding(
            Capability.GAIN_COMPOSITION, require_integrity=False
        ),
    )
    uncertainty = Uncertainty(
        UnitKind.DIMENSIONLESS,
        standard,
        lower,
        max(product, upper),
        _confidence(values),
        context.profile.uncertainty_method_id,
    )
    composed = MeasurementValue(
        f"gain[{stages[0].source_coordinate.coordinate_id}->{stages[-1].target_coordinate.coordinate_id}]",
        QuantityKind.GAIN_MAGNITUDE,
        product,
        UnitKind.DIMENSIONLESS,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        uncertainty,
        min(value.sample_size for value in values if value.sample_size is not None),
    )
    return GainCompositionResult(composed, stages, _factory_token=_GAIN_RESULT_TOKEN)
