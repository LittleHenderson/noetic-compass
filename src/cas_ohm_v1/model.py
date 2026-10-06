"""Typed ontology and evidence identities for the CAS-Ohm v1 candidate."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import InitVar, dataclass
from decimal import Decimal
from enum import Enum

from .canonical import (
    ValidationError,
    canonical_bytes,
    canonical_sha256,
    require_decimal,
    require_positive_int,
    require_sha256,
    require_text,
)

RESEARCH_STATUS = "OPEN"
ADMISSION_RING = 4
LICENSE_STATUS = "NOT LICENSED"
DISCLOSURE_STATUS = "HELD"
COVARIANCE_LIMITATION = (
    "CROSS_INPUT_COVARIANCE_UNAVAILABLE_ZERO_COVARIANCE_APPROXIMATION"
)


class MeasurementKind(str, Enum):
    DESIGN_VALUE = "DESIGN_VALUE"
    INSTRUMENTED = "INSTRUMENTED"
    BEHAVIORAL_PROXY = "BEHAVIORAL_PROXY"
    MODEL_DERIVED = "MODEL_DERIVED"
    HUMAN_SCORE = "HUMAN_SCORE"
    LLM_SCORE = "LLM_SCORE"


class QuantityKind(str, Enum):
    DRIVE_INTERVENTION = "DRIVE_INTERVENTION"
    DRIVE_SCORE = "DRIVE_SCORE"
    SIGNED_ACTIVATION = "SIGNED_ACTIVATION"
    FLOW_MAGNITUDE = "FLOW_MAGNITUDE"
    NORMALIZED_FLOW = "NORMALIZED_FLOW"
    CONSTRAINT_SCORE = "CONSTRAINT_SCORE"
    EFFECTIVE_RESISTANCE = "EFFECTIVE_RESISTANCE"
    RESISTANCE_DELTA = "RESISTANCE_DELTA"
    CAPABILITY_SCORE = "CAPABILITY_SCORE"
    GAIN_MAGNITUDE = "GAIN_MAGNITUDE"
    EFFECT_PROJECTION = "EFFECT_PROJECTION"
    SATURATION_FRACTION = "SATURATION_FRACTION"
    CUTOFF_FRACTION = "CUTOFF_FRACTION"
    OVERLOAD_RATIO = "OVERLOAD_RATIO"
    FLOW_RESIDUAL = "FLOW_RESIDUAL"
    RELATIVE_ERROR = "RELATIVE_ERROR"


class UnitKind(str, Enum):
    ALPHA = "ALPHA"
    ACTIVATION = "ACTIVATION"
    Q10 = "Q10"
    Q100 = "Q100"
    ALPHA_PER_ACTIVATION = "ALPHA_PER_ACTIVATION"
    DIMENSIONLESS = "DIMENSIONLESS"
    FRACTION = "FRACTION"


class DoseResponseRegion(str, Enum):
    UNASSESSED = "UNASSESSED"
    CUTOFF = "CUTOFF"
    ACTIVE = "ACTIVE"
    SATURATION = "SATURATION"
    BREAKDOWN = "BREAKDOWN"
    NON_OHMIC = "NON_OHMIC"
    UNSTABLE = "UNSTABLE"


class SemanticOutcome(str, Enum):
    UNASSESSED = "UNASSESSED"
    INTENDED = "INTENDED"
    OPPOSITE = "OPPOSITE"
    OFF_AXIS = "OFF_AXIS"


class AsomLabel(str, Enum):
    STARVED = "STARVED"
    ALIGNED = "ALIGNED"
    OVERSATURATED = "OVERSATURATED"
    MISALIGNED = "MISALIGNED"


class IFSMethod(str, Enum):
    RAIL_AND_FLOOR_PER_PATH = "RAIL_AND_FLOOR_PER_PATH"
    CORPUS_PERCENTILE_PER_TEST_POINT = "CORPUS_PERCENTILE_PER_TEST_POINT"
    DECLARED_DESIGN_FULL_SCALE = "DECLARED_DESIGN_FULL_SCALE"


class DirectionProvenance(str, Enum):
    PROBE_DERIVED = "PROBE_DERIVED"
    JACOBIAN_DERIVED = "JACOBIAN_DERIVED"
    DIFF_DERIVED = "DIFF_DERIVED"


class ReviewState(str, Enum):
    UNASSESSED = "UNASSESSED"
    IN_REVIEW = "IN_REVIEW"
    REVIEWED = "REVIEWED"
    FLAG_FOR_HUMAN_REVIEW = "FLAG_FOR_HUMAN_REVIEW"


class DirectionSign(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class ResistanceRole(str, Enum):
    CALIBRATED_HELD_OUT = "CALIBRATED_HELD_OUT"
    APPARENT_SAME_SAMPLE = "APPARENT_SAME_SAMPLE"
    NETWORK_EQUIVALENT = "NETWORK_EQUIVALENT"
    DESIGN_PROPOSAL = "DESIGN_PROPOSAL"


class Capability(str, Enum):
    OHMIC_PREDICTION = "OHMIC_PREDICTION"
    RESIDUAL_DIAGNOSIS = "RESIDUAL_DIAGNOSIS"
    SERIES_EQUIVALENCE = "SERIES_EQUIVALENCE"
    PARALLEL_EQUIVALENCE = "PARALLEL_EQUIVALENCE"
    GAIN_COMPOSITION = "GAIN_COMPOSITION"
    PACKET_ELIGIBILITY = "PACKET_ELIGIBILITY"


class TrustMode(str, Enum):
    STRUCTURAL_RESEARCH_ONLY = "STRUCTURAL_RESEARCH_ONLY"
    INTEGRITY_CONFIGURATION = "INTEGRITY_CONFIGURATION"


class AuthorizationState(str, Enum):
    UNAUTHENTICATED_STRUCTURAL = "UNAUTHENTICATED_STRUCTURAL"
    UNAUTHENTICATED_INTEGRITY = "UNAUTHENTICATED_INTEGRITY"


class ClassificationMode(str, Enum):
    NUMERIC_DERIVED = "NUMERIC_DERIVED"
    EXTERNAL_UNVERIFIED = "EXTERNAL_UNVERIFIED"


_ALLOWED_UNITS: dict[QuantityKind, frozenset[UnitKind]] = {
    QuantityKind.DRIVE_INTERVENTION: frozenset({UnitKind.ALPHA}),
    QuantityKind.DRIVE_SCORE: frozenset({UnitKind.Q10}),
    QuantityKind.SIGNED_ACTIVATION: frozenset({UnitKind.ACTIVATION}),
    QuantityKind.FLOW_MAGNITUDE: frozenset({UnitKind.ACTIVATION}),
    QuantityKind.NORMALIZED_FLOW: frozenset({UnitKind.Q10}),
    QuantityKind.CONSTRAINT_SCORE: frozenset({UnitKind.Q10, UnitKind.Q100}),
    QuantityKind.EFFECTIVE_RESISTANCE: frozenset({UnitKind.ALPHA_PER_ACTIVATION}),
    QuantityKind.RESISTANCE_DELTA: frozenset({UnitKind.ALPHA_PER_ACTIVATION}),
    QuantityKind.CAPABILITY_SCORE: frozenset({UnitKind.Q10}),
    QuantityKind.GAIN_MAGNITUDE: frozenset({UnitKind.DIMENSIONLESS}),
    QuantityKind.EFFECT_PROJECTION: frozenset({UnitKind.ACTIVATION}),
    QuantityKind.SATURATION_FRACTION: frozenset({UnitKind.FRACTION}),
    QuantityKind.CUTOFF_FRACTION: frozenset({UnitKind.FRACTION}),
    QuantityKind.OVERLOAD_RATIO: frozenset({UnitKind.DIMENSIONLESS}),
    QuantityKind.FLOW_RESIDUAL: frozenset({UnitKind.ACTIVATION}),
    QuantityKind.RELATIVE_ERROR: frozenset({UnitKind.DIMENSIONLESS}),
}


def _require_enum(value: object, enum_type: type[Enum], field_name: str) -> None:
    if type(value) is not enum_type:
        raise ValidationError(f"{field_name} must be a {enum_type.__name__}")


def _require_distinct(items: Iterable[str], field_name: str) -> None:
    materialized = tuple(items)
    if len(materialized) != len(set(materialized)):
        raise ValidationError(f"{field_name} contains duplicates")


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    uri: str
    sha256: str
    media_type: str

    def __post_init__(self) -> None:
        require_text(self.artifact_id, "artifact_id")
        require_text(self.uri, "uri")
        require_sha256(self.sha256, "sha256")
        require_text(self.media_type, "media_type")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "media_type": self.media_type,
            "sha256": self.sha256,
            "uri": self.uri,
        }


@dataclass(frozen=True, slots=True)
class ControlBinding:
    ref: ArtifactRef
    test_point_sha256: str
    relevance_method_id: str

    def __post_init__(self) -> None:
        if type(self.ref) is not ArtifactRef:
            raise ValidationError("control binding ref must be an exact ArtifactRef")
        require_sha256(self.test_point_sha256, "test_point_sha256")
        require_text(self.relevance_method_id, "relevance_method_id")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "ref": self.ref,
            "relevance_method_id": self.relevance_method_id,
            "test_point_sha256": self.test_point_sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class OperationBinding:
    authority_manifest_sha256: str
    attestation_sha256s: tuple[str, ...]
    capability: Capability | None
    trust_mode: TrustMode
    authorization_state: AuthorizationState
    replay_as_of: str
    clock_receipt_sha256: str | None
    runtime_id: str
    covariance_limitation: str
    dependency_lock_ref: ArtifactRef
    code_ref: ArtifactRef

    def __post_init__(self) -> None:
        require_sha256(self.authority_manifest_sha256, "authority_manifest_sha256")
        if type(self.attestation_sha256s) is not tuple:
            raise ValidationError("attestation_sha256s must be an exact tuple")
        for digest in self.attestation_sha256s:
            require_sha256(digest, "attestation_sha256")
        if self.attestation_sha256s != tuple(sorted(set(self.attestation_sha256s))):
            raise ValidationError(
                "attestation_sha256s must be unique and canonically ordered"
            )
        if self.capability is not None:
            _require_enum(self.capability, Capability, "capability")
        _require_enum(self.trust_mode, TrustMode, "trust_mode")
        _require_enum(
            self.authorization_state, AuthorizationState, "authorization_state"
        )
        if (
            self.trust_mode is TrustMode.STRUCTURAL_RESEARCH_ONLY
            and self.authorization_state
            is not AuthorizationState.UNAUTHENTICATED_STRUCTURAL
        ):
            raise ValidationError("structural trust mode cannot claim integrity")
        if (
            self.trust_mode is TrustMode.INTEGRITY_CONFIGURATION
            and self.authorization_state
            is not AuthorizationState.UNAUTHENTICATED_INTEGRITY
        ):
            raise ValidationError("integrity mode remains unauthenticated")
        require_text(self.replay_as_of, "replay_as_of")
        if self.clock_receipt_sha256 is not None:
            require_sha256(self.clock_receipt_sha256, "clock_receipt_sha256")
        require_text(self.runtime_id, "runtime_id")
        if self.covariance_limitation != COVARIANCE_LIMITATION:
            raise ValidationError("covariance limitation must remain explicit")
        if type(self.dependency_lock_ref) is not ArtifactRef:
            raise ValidationError("dependency_lock_ref must be an exact ArtifactRef")
        if type(self.code_ref) is not ArtifactRef:
            raise ValidationError("code_ref must be an exact ArtifactRef")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "attestation_sha256s": self.attestation_sha256s,
            "authority_manifest_sha256": self.authority_manifest_sha256,
            "authorization_state": self.authorization_state,
            "capability": self.capability,
            "clock_receipt_sha256": self.clock_receipt_sha256,
            "code_ref": self.code_ref,
            "covariance_limitation": self.covariance_limitation,
            "dependency_lock_ref": self.dependency_lock_ref,
            "replay_as_of": self.replay_as_of,
            "runtime_id": self.runtime_id,
            "trust_mode": self.trust_mode,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    model_id: str
    revision: str
    weights_sha256: str
    config_sha256: str
    tokenizer_sha256: str

    def __post_init__(self) -> None:
        require_text(self.model_id, "model_id")
        require_text(self.revision, "revision")
        require_sha256(self.weights_sha256, "weights_sha256")
        require_sha256(self.config_sha256, "config_sha256")
        require_sha256(self.tokenizer_sha256, "tokenizer_sha256")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "config_sha256": self.config_sha256,
            "model_id": self.model_id,
            "revision": self.revision,
            "tokenizer_sha256": self.tokenizer_sha256,
            "weights_sha256": self.weights_sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class InstrumentIdentity:
    instrument_id: str
    kind: str
    version: str
    implementation_sha256: str

    def __post_init__(self) -> None:
        require_text(self.instrument_id, "instrument_id")
        require_text(self.kind, "kind")
        require_text(self.version, "version")
        require_sha256(self.implementation_sha256, "implementation_sha256")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "implementation_sha256": self.implementation_sha256,
            "instrument_id": self.instrument_id,
            "kind": self.kind,
            "version": self.version,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class TestPointIdentity:
    model: ModelIdentity
    layer: str
    token_positions: tuple[int, ...]
    direction_id: str
    direction_sha256: str
    direction_provenance: DirectionProvenance
    direction_norm: Decimal
    direction_sign: DirectionSign
    hook_type: str

    def __post_init__(self) -> None:
        if type(self.model) is not ModelIdentity:
            raise ValidationError("model must be a ModelIdentity")
        require_text(self.layer, "layer")
        if type(self.token_positions) is not tuple or not self.token_positions:
            raise ValidationError("token_positions must be a non-empty tuple")
        for position in self.token_positions:
            if type(position) is not int or position < 0:
                raise ValidationError(
                    "token_positions must contain non-negative integers"
                )
        _require_distinct(
            (str(position) for position in self.token_positions), "token_positions"
        )
        require_text(self.direction_id, "direction_id")
        require_sha256(self.direction_sha256, "direction_sha256")
        _require_enum(
            self.direction_provenance, DirectionProvenance, "direction_provenance"
        )
        if require_decimal(self.direction_norm, "direction_norm") != Decimal("1"):
            raise ValidationError("direction_norm must equal Decimal('1')")
        _require_enum(self.direction_sign, DirectionSign, "direction_sign")
        require_text(self.hook_type, "hook_type")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "direction_id": self.direction_id,
            "direction_norm": self.direction_norm,
            "direction_provenance": self.direction_provenance,
            "direction_sha256": self.direction_sha256,
            "direction_sign": self.direction_sign,
            "hook_type": self.hook_type,
            "layer": self.layer,
            "model": self.model,
            "token_positions": self.token_positions,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class Uncertainty:
    unit: UnitKind
    standard_uncertainty: Decimal
    lower: Decimal
    upper: Decimal
    confidence_level: Decimal
    method_id: str

    def __post_init__(self) -> None:
        _require_enum(self.unit, UnitKind, "unit")
        standard = require_decimal(self.standard_uncertainty, "standard_uncertainty")
        lower = require_decimal(self.lower, "lower")
        upper = require_decimal(self.upper, "upper")
        confidence = require_decimal(self.confidence_level, "confidence_level")
        if standard < 0:
            raise ValidationError("standard_uncertainty must be non-negative")
        if lower > upper:
            raise ValidationError("uncertainty lower bound must not exceed upper bound")
        if not Decimal("0") < confidence < Decimal("1"):
            raise ValidationError("confidence_level must be strictly between 0 and 1")
        require_text(self.method_id, "method_id")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "confidence_level": self.confidence_level,
            "lower": self.lower,
            "method_id": self.method_id,
            "standard_uncertainty": self.standard_uncertainty,
            "unit": self.unit,
            "upper": self.upper,
        }


@dataclass(frozen=True, slots=True)
class ParentRef:
    role: str
    position: int
    object_type: str
    object_sha256: str

    def __post_init__(self) -> None:
        require_text(self.role, "role")
        if type(self.position) is not int or self.position < 0:
            raise ValidationError("parent position must be a non-negative integer")
        require_text(self.object_type, "object_type")
        require_sha256(self.object_sha256, "object_sha256")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "object_sha256": self.object_sha256,
            "object_type": self.object_type,
            "position": self.position,
            "role": self.role,
        }


@dataclass(frozen=True, slots=True)
class FieldProvenance:
    source_refs: tuple[ArtifactRef, ...]
    method_id: str
    calibration_profile_sha256: str | None = None
    instrument: InstrumentIdentity | None = None
    test_point: TestPointIdentity | None = None
    raw_artifact_refs: tuple[ArtifactRef, ...] = ()
    control_refs: tuple[ArtifactRef, ...] = ()
    control_bindings: tuple[ControlBinding, ...] = ()
    dataset_split_ref: ArtifactRef | None = None
    derivation_parents: tuple[ParentRef, ...] = ()
    operation_binding: OperationBinding | None = None

    def __post_init__(self) -> None:
        if type(self.source_refs) is not tuple or not self.source_refs:
            raise ValidationError("source_refs must be a non-empty tuple")
        for values, field_name in (
            (self.raw_artifact_refs, "raw_artifact_refs"),
            (self.control_refs, "control_refs"),
            (self.control_bindings, "control_bindings"),
            (self.derivation_parents, "derivation_parents"),
        ):
            if type(values) is not tuple:
                raise ValidationError(f"{field_name} must be an exact tuple")
        all_refs = self.source_refs + self.raw_artifact_refs + self.control_refs
        if self.dataset_split_ref is not None:
            all_refs += (self.dataset_split_ref,)
        for ref in all_refs:
            if type(ref) is not ArtifactRef:
                raise ValidationError(
                    "all provenance references must be exact ArtifactRef values"
                )
        _require_distinct((ref.sha256 for ref in self.source_refs), "source_refs")
        _require_distinct(
            (ref.sha256 for ref in self.raw_artifact_refs), "raw_artifact_refs"
        )
        _require_distinct((ref.sha256 for ref in self.control_refs), "control_refs")
        if any(
            type(binding) is not ControlBinding for binding in self.control_bindings
        ):
            raise ValidationError(
                "control_bindings must contain exact ControlBinding values"
            )
        bound_refs = tuple(
            sorted(
                {
                    binding.ref.sha256: binding.ref for binding in self.control_bindings
                }.values(),
                key=lambda ref: ref.sha256,
            )
        )
        if bound_refs != self.control_refs:
            raise ValidationError(
                "control_refs must exactly match control relevance artifacts"
            )
        _require_distinct(
            (binding.sha256 for binding in self.control_bindings),
            "control_bindings",
        )
        require_text(self.method_id, "method_id")
        if self.calibration_profile_sha256 is not None:
            require_sha256(
                self.calibration_profile_sha256, "calibration_profile_sha256"
            )
        if (
            self.dataset_split_ref is not None
            and type(self.dataset_split_ref) is not ArtifactRef
        ):
            raise ValidationError("dataset_split_ref must be an exact ArtifactRef")
        if (
            self.operation_binding is not None
            and type(self.operation_binding) is not OperationBinding
        ):
            raise ValidationError("operation_binding must be an exact OperationBinding")
        if (
            self.instrument is not None
            and type(self.instrument) is not InstrumentIdentity
        ):
            raise ValidationError("instrument must be an InstrumentIdentity")
        if (
            self.test_point is not None
            and type(self.test_point) is not TestPointIdentity
        ):
            raise ValidationError("test_point must be a TestPointIdentity")
        if any(type(parent) is not ParentRef for parent in self.derivation_parents):
            raise ValidationError("derivation_parents must contain ParentRef values")
        expected_positions = tuple(range(len(self.derivation_parents)))
        actual_positions = tuple(parent.position for parent in self.derivation_parents)
        if actual_positions != expected_positions:
            raise ValidationError(
                "derivation parent positions must be contiguous and ordered from zero"
            )
        _require_distinct(
            (parent.role for parent in self.derivation_parents), "parent roles"
        )
        _require_distinct(
            (
                f"{parent.object_type}:{parent.object_sha256}"
                for parent in self.derivation_parents
            ),
            "derivation parent identities",
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "calibration_profile_sha256": self.calibration_profile_sha256,
            "control_refs": tuple(
                sorted(self.control_refs, key=lambda ref: ref.sha256)
            ),
            "control_bindings": tuple(
                sorted(self.control_bindings, key=lambda value: value.sha256)
            ),
            "dataset_split_ref": self.dataset_split_ref,
            "derivation_parents": self.derivation_parents,
            "instrument": self.instrument,
            "method_id": self.method_id,
            "operation_binding": self.operation_binding,
            "raw_artifact_refs": tuple(
                sorted(self.raw_artifact_refs, key=lambda ref: ref.sha256)
            ),
            "source_refs": tuple(sorted(self.source_refs, key=lambda ref: ref.sha256)),
            "test_point": self.test_point,
        }


def validate_quantity_unit(quantity_kind: QuantityKind, unit: UnitKind) -> None:
    if unit not in _ALLOWED_UNITS[quantity_kind]:
        allowed = ", ".join(
            sorted(candidate.value for candidate in _ALLOWED_UNITS[quantity_kind])
        )
        raise ValidationError(
            f"{quantity_kind.value} cannot use {unit.value}; allowed unit(s): {allowed}"
        )


def _validate_quantity(
    quantity_kind: QuantityKind, value: Decimal, unit: UnitKind
) -> None:
    validate_quantity_unit(quantity_kind, unit)
    if unit is UnitKind.Q10 and not Decimal("0") <= value <= Decimal("10"):
        raise ValidationError("Q10 values must be in [0, 10]")
    if unit is UnitKind.Q100 and not Decimal("0") <= value <= Decimal("100"):
        raise ValidationError("Q100 values must be in [0, 100]")
    if unit is UnitKind.FRACTION and not Decimal("0") <= value <= Decimal("1"):
        raise ValidationError("fraction values must be in [0, 1]")
    if (
        quantity_kind
        in {
            QuantityKind.FLOW_MAGNITUDE,
            QuantityKind.GAIN_MAGNITUDE,
            QuantityKind.OVERLOAD_RATIO,
            QuantityKind.RELATIVE_ERROR,
        }
        and value < 0
    ):
        raise ValidationError(f"{quantity_kind.value} must be non-negative")
    if quantity_kind is QuantityKind.EFFECTIVE_RESISTANCE and value <= 0:
        raise ValidationError("EFFECTIVE_RESISTANCE must be strictly positive")


_NETWORK_FACTORY_TOKEN = object()


@dataclass(frozen=True, slots=True)
class MeasurementValue:
    field_name: str
    quantity_kind: QuantityKind
    value: Decimal
    unit: UnitKind
    measurement_kind: MeasurementKind
    provenance: FieldProvenance
    uncertainty: Uncertainty | None = None
    sample_size: int | None = None
    resistance_role: ResistanceRole | None = None
    missing_or_censored_reason: str | None = None
    _factory_token: InitVar[object] = None

    def __post_init__(self, _factory_token: object) -> None:
        require_text(self.field_name, "field_name")
        _require_enum(self.quantity_kind, QuantityKind, "quantity_kind")
        value = require_decimal(self.value, "value")
        _require_enum(self.unit, UnitKind, "unit")
        _require_enum(self.measurement_kind, MeasurementKind, "measurement_kind")
        if type(self.provenance) is not FieldProvenance:
            raise ValidationError("provenance must be a FieldProvenance")
        _validate_quantity(self.quantity_kind, value, self.unit)
        if self.uncertainty is not None:
            if type(self.uncertainty) is not Uncertainty:
                raise ValidationError("uncertainty must be an Uncertainty")
            if self.uncertainty.unit is not self.unit:
                raise ValidationError(
                    "uncertainty unit must match the measurement unit"
                )
            if not self.uncertainty.lower <= value <= self.uncertainty.upper:
                raise ValidationError(
                    "measurement value must lie inside its uncertainty interval"
                )
            _validate_quantity(self.quantity_kind, self.uncertainty.lower, self.unit)
            _validate_quantity(self.quantity_kind, self.uncertainty.upper, self.unit)
        if self.sample_size is not None:
            require_positive_int(self.sample_size, "sample_size")
        if self.quantity_kind is QuantityKind.EFFECTIVE_RESISTANCE:
            if type(self.resistance_role) is not ResistanceRole:
                raise ValidationError(
                    "EFFECTIVE_RESISTANCE requires an explicit resistance_role"
                )
            if (
                self.resistance_role
                in {
                    ResistanceRole.CALIBRATED_HELD_OUT,
                    ResistanceRole.APPARENT_SAME_SAMPLE,
                    ResistanceRole.NETWORK_EQUIVALENT,
                }
                and self.measurement_kind is not MeasurementKind.MODEL_DERIVED
            ):
                raise ValidationError(
                    f"{self.resistance_role.value} resistance must be MODEL_DERIVED"
                )
            if (
                self.resistance_role is ResistanceRole.CALIBRATED_HELD_OUT
                and self.provenance.dataset_split_ref is None
            ):
                raise ValidationError(
                    "calibrated resistance requires a held-out dataset_split_ref"
                )
            if (
                self.resistance_role is ResistanceRole.NETWORK_EQUIVALENT
                and _factory_token is not _NETWORK_FACTORY_TOKEN
            ):
                raise ValidationError(
                    "NETWORK_EQUIVALENT resistance is factory-only and must be replayed"
                )
        elif self.resistance_role is not None:
            raise ValidationError(
                "resistance_role is valid only for EFFECTIVE_RESISTANCE"
            )
        if self.missing_or_censored_reason is not None:
            require_text(self.missing_or_censored_reason, "missing_or_censored_reason")
        if self.measurement_kind is MeasurementKind.INSTRUMENTED:
            missing: list[str] = []
            if self.provenance.instrument is None:
                missing.append("instrument")
            if self.provenance.test_point is None:
                missing.append("test_point")
            if self.provenance.calibration_profile_sha256 is None:
                missing.append("calibration_profile_sha256")
            if not self.provenance.raw_artifact_refs:
                missing.append("raw_artifact_refs")
            if missing:
                raise ValidationError(
                    "instrumented measurement is missing " + ", ".join(missing)
                )
        if (
            self.measurement_kind is MeasurementKind.MODEL_DERIVED
            and not self.provenance.derivation_parents
        ):
            raise ValidationError(
                "model-derived measurement requires derivation parent hashes"
            )
        if (
            self.measurement_kind
            in {
                MeasurementKind.BEHAVIORAL_PROXY,
                MeasurementKind.HUMAN_SCORE,
                MeasurementKind.LLM_SCORE,
            }
            and not self.provenance.raw_artifact_refs
        ):
            raise ValidationError(
                f"{self.measurement_kind.value} measurement requires raw_artifact_refs"
            )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "admission_ring": ADMISSION_RING,
            "disclosure_status": DISCLOSURE_STATUS,
            "field_name": self.field_name,
            "license_status": LICENSE_STATUS,
            "measurement_kind": self.measurement_kind,
            "missing_or_censored_reason": self.missing_or_censored_reason,
            "provenance": self.provenance,
            "quantity_kind": self.quantity_kind,
            "research_status": RESEARCH_STATUS,
            "resistance_role": self.resistance_role,
            "sample_size": self.sample_size,
            "schema": "CAS-OHM-V1-MEASUREMENT",
            "uncertainty": self.uncertainty,
            "unit": self.unit,
            "value": self.value,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self)

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class OperatingClassification:
    region: DoseResponseRegion
    semantic_outcome: SemanticOutcome

    def __post_init__(self) -> None:
        _require_enum(self.region, DoseResponseRegion, "region")
        _require_enum(self.semantic_outcome, SemanticOutcome, "semantic_outcome")

    def asom_label(self) -> AsomLabel | None:
        """Return a derived display label without collapsing the two source axes."""

        if self.semantic_outcome in {
            SemanticOutcome.OPPOSITE,
            SemanticOutcome.OFF_AXIS,
        }:
            return AsomLabel.MISALIGNED
        if self.semantic_outcome is not SemanticOutcome.INTENDED:
            return None
        if self.region is DoseResponseRegion.CUTOFF:
            return AsomLabel.STARVED
        if self.region is DoseResponseRegion.ACTIVE:
            return AsomLabel.ALIGNED
        if self.region is DoseResponseRegion.SATURATION:
            return AsomLabel.OVERSATURATED
        return None

    def canonical_payload(self) -> dict[str, object]:
        return {"region": self.region, "semantic_outcome": self.semantic_outcome}

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class SweepObservation:
    drive: Decimal
    flow: Decimal
    off_axis_activation: Decimal

    def __post_init__(self) -> None:
        drive = require_decimal(self.drive, "drive")
        flow = require_decimal(self.flow, "flow")
        off_axis = require_decimal(self.off_axis_activation, "off_axis_activation")
        if drive < 0 or flow < 0 or off_axis < 0:
            raise ValidationError("sweep observation magnitudes must be non-negative")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "drive": self.drive,
            "flow": self.flow,
            "off_axis_activation": self.off_axis_activation,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


_ASSESSMENT_FACTORY_TOKEN = object()


@dataclass(frozen=True, slots=True)
class OperatingAssessment:
    classification: OperatingClassification
    mode: ClassificationMode
    method_id: str
    calibration_profile_sha256: str
    test_point_sha256: str
    evidence_ref: ArtifactRef
    observations: tuple[SweepObservation, ...]
    index: int | None
    expected_resistance: Decimal | None
    control_bindings: tuple[ControlBinding, ...]
    operation_binding: OperationBinding
    _factory_token: InitVar[object] = None

    def __post_init__(self, _factory_token: object) -> None:
        if type(self.classification) is not OperatingClassification:
            raise ValidationError(
                "classification must be exact OperatingClassification"
            )
        _require_enum(self.mode, ClassificationMode, "mode")
        require_text(self.method_id, "method_id")
        require_sha256(self.calibration_profile_sha256, "calibration_profile_sha256")
        require_sha256(self.test_point_sha256, "test_point_sha256")
        if type(self.evidence_ref) is not ArtifactRef:
            raise ValidationError("evidence_ref must be an exact ArtifactRef")
        if type(self.observations) is not tuple or any(
            type(value) is not SweepObservation for value in self.observations
        ):
            raise ValidationError(
                "observations must be an exact tuple of SweepObservation values"
            )
        if type(self.control_bindings) is not tuple or any(
            type(value) is not ControlBinding for value in self.control_bindings
        ):
            raise ValidationError(
                "control_bindings must be an exact tuple of ControlBinding values"
            )
        if type(self.operation_binding) is not OperationBinding:
            raise ValidationError("operation_binding must be exact OperationBinding")
        if self.mode is ClassificationMode.NUMERIC_DERIVED:
            if _factory_token is not _ASSESSMENT_FACTORY_TOKEN:
                raise ValidationError("numeric operating assessments are factory-only")
            if len(self.observations) < 3:
                raise ValidationError(
                    "numeric assessment requires at least three points"
                )
            if (
                type(self.index) is not int
                or not 0 < self.index < len(self.observations) - 1
            ):
                raise ValidationError("assessment index must have adjacent points")
            resistance = require_decimal(
                self.expected_resistance, "expected_resistance"
            )
            if resistance <= 0:
                raise ValidationError("expected_resistance must be positive")
            if canonical_sha256(self.observations) != self.evidence_ref.sha256:
                raise ValidationError(
                    "numeric sweep evidence digest does not match observations"
                )
        else:
            if (
                self.observations
                or self.index is not None
                or self.expected_resistance is not None
            ):
                raise ValidationError(
                    "external unverified assessment cannot embed derived sweep claims"
                )

    @property
    def region(self) -> DoseResponseRegion:
        return self.classification.region

    @property
    def semantic_outcome(self) -> SemanticOutcome:
        return self.classification.semantic_outcome

    def canonical_payload(self) -> dict[str, object]:
        return {
            "calibration_profile_sha256": self.calibration_profile_sha256,
            "classification": self.classification,
            "control_bindings": self.control_bindings,
            "evidence_ref": self.evidence_ref,
            "expected_resistance": self.expected_resistance,
            "index": self.index,
            "method_id": self.method_id,
            "mode": self.mode,
            "observations": self.observations,
            "operation_binding": self.operation_binding,
            "test_point_sha256": self.test_point_sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class NonClaimExtension:
    namespace: str
    name: str
    payload_ref: ArtifactRef

    def __post_init__(self) -> None:
        namespace = require_text(self.namespace, "namespace")
        if not namespace.startswith("x-nonclaim-"):
            raise ValidationError("extension namespace must start with x-nonclaim-")
        require_text(self.name, "name")
        if type(self.payload_ref) is not ArtifactRef:
            raise ValidationError("payload_ref must be an exact ArtifactRef")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "namespace": self.namespace,
            "payload_ref": self.payload_ref,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)
