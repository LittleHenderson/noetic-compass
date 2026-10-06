"""Trusted, range-bound Ohmic prediction and non-identifying residual diagnostics."""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from decimal import Decimal
from enum import Enum

from .calibration import OperationContext
from .canonical import ValidationError, arithmetic_context, canonical_sha256
from .evidence import parent_ref
from .model import (
    ArtifactRef,
    Capability,
    ClassificationMode,
    DoseResponseRegion,
    FieldProvenance,
    MeasurementKind,
    MeasurementValue,
    OperatingAssessment,
    QuantityKind,
    ResistanceRole,
    SemanticOutcome,
    TestPointIdentity,
    Uncertainty,
    UnitKind,
)


class ResidualCensoring(str, Enum):
    NONE = "NONE"
    OBSERVED_INTERVAL_INCLUDES_ZERO = "OBSERVED_INTERVAL_INCLUDES_ZERO"


def _unique_refs(*groups: tuple[ArtifactRef, ...]) -> tuple[ArtifactRef, ...]:
    refs: dict[str, ArtifactRef] = {}
    for group in groups:
        for ref in group:
            existing = refs.get(ref.sha256)
            if existing is not None and existing != ref:
                raise ValidationError("conflicting artifact metadata for one digest")
            refs[ref.sha256] = ref
    return tuple(refs[digest] for digest in sorted(refs))


def _common_test_point(*measurements: MeasurementValue) -> TestPointIdentity:
    points = tuple(measurement.provenance.test_point for measurement in measurements)
    if any(point is None for point in points) or any(
        point != points[0] for point in points[1:]
    ):
        raise ValidationError("operation inputs must bind one common test point")
    return points[0]  # type: ignore[return-value]


def _confidence(*measurements: MeasurementValue) -> Decimal:
    levels = tuple(
        value.uncertainty.confidence_level
        for value in measurements
        if value.uncertainty is not None
    )
    return min(levels) if levels else Decimal("0.95")


def _bounds(measurement: MeasurementValue) -> tuple[Decimal, Decimal, Decimal]:
    if measurement.uncertainty is None:
        return measurement.value, measurement.value, Decimal("0")
    return (
        measurement.uncertainty.lower,
        measurement.uncertainty.upper,
        measurement.uncertainty.standard_uncertainty,
    )


def predict_flow(
    context: OperationContext,
    drive: MeasurementValue,
    resistance: MeasurementValue,
) -> MeasurementValue:
    """Predict held-out active-region response from a calibrated resistance."""

    context.require_integrity_attestation(Capability.OHMIC_PREDICTION)
    operation_binding = context.operation_binding(
        Capability.OHMIC_PREDICTION, require_integrity=True
    )
    context.validate_measurement(drive)
    context.validate_measurement(resistance)
    if (
        drive.quantity_kind is not QuantityKind.DRIVE_INTERVENTION
        or drive.unit is not UnitKind.ALPHA
    ):
        raise ValidationError("drive must be DRIVE_INTERVENTION in ALPHA units")
    if drive.measurement_kind is not MeasurementKind.DESIGN_VALUE:
        raise ValidationError("drive must be an explicit DESIGN_VALUE intervention")
    if not context.profile.alpha_min <= drive.value <= context.profile.alpha_max:
        raise ValidationError("drive lies outside the calibrated alpha range")
    if drive.value < 0:
        raise ValidationError("flow-magnitude prediction requires non-negative drive")
    if (
        resistance.quantity_kind is not QuantityKind.EFFECTIVE_RESISTANCE
        or resistance.unit is not UnitKind.ALPHA_PER_ACTIVATION
    ):
        raise ValidationError(
            "resistance must be EFFECTIVE_RESISTANCE in calibrated units"
        )
    if resistance.resistance_role not in {
        ResistanceRole.CALIBRATED_HELD_OUT,
        ResistanceRole.NETWORK_EQUIVALENT,
    }:
        raise ValidationError(
            "prediction rejects apparent and design-proposal resistance roles"
        )
    if resistance.resistance_role is ResistanceRole.NETWORK_EQUIVALENT:
        from .networks import replay_network_equivalent

        replay_network_equivalent(context, resistance)
    if resistance.uncertainty is None or resistance.uncertainty.lower <= 0:
        raise ValidationError(
            "prediction requires positive calibrated-resistance uncertainty bounds"
        )
    if resistance.sample_size is None:
        raise ValidationError("prediction requires a calibrated-resistance sample size")
    if resistance.resistance_role is ResistanceRole.CALIBRATED_HELD_OUT:
        provenance = resistance.provenance
        if provenance.dataset_split_ref != context.profile.validation_split_ref:
            raise ValidationError(
                "calibrated resistance must bind the held-out validation split"
            )
        if provenance.method_id != context.profile.fit_method_id:
            raise ValidationError(
                "calibrated resistance must use the profile-bound fit method"
            )
        expected_parent = parent_ref(
            "held_out_fit_receipt", 0, context.profile.fit_receipt_ref
        )
        if provenance.derivation_parents != (expected_parent,):
            raise ValidationError(
                "calibrated resistance must bind the exact profile fit receipt and role"
            )
        source_hashes = {ref.sha256 for ref in provenance.source_refs}
        profile_source_hashes = {ref.sha256 for ref in context.profile.source_refs}
        if not profile_source_hashes <= source_hashes:
            raise ValidationError("calibrated resistance omits profile source evidence")
        control_hashes = {ref.sha256 for ref in provenance.control_refs}
        profile_control_hashes = {ref.sha256 for ref in context.profile.control_refs}
        if not profile_control_hashes <= control_hashes:
            raise ValidationError(
                "calibrated resistance omits profile control evidence"
            )
    test_point = _common_test_point(drive, resistance)
    drive_lower, drive_upper, drive_standard = _bounds(drive)
    resistance_lower, resistance_upper, resistance_standard = _bounds(resistance)
    with arithmetic_context():
        predicted_value = drive.value / resistance.value
        lower = max(Decimal("0"), drive_lower / resistance_upper)
        upper = drive_upper / resistance_lower
        term_drive = drive_standard / resistance.value
        term_resistance = (
            drive.value * resistance_standard / (resistance.value * resistance.value)
        )
        standard = (term_drive * term_drive + term_resistance * term_resistance).sqrt()
    uncertainty = Uncertainty(
        UnitKind.ACTIVATION,
        standard,
        lower,
        max(predicted_value, upper),
        _confidence(drive, resistance),
        context.profile.uncertainty_method_id,
    )
    provenance = FieldProvenance(
        source_refs=_unique_refs(
            drive.provenance.source_refs, resistance.provenance.source_refs
        ),
        method_id="CAS-OHM-V1-HELD-OUT-PREDICTION",
        calibration_profile_sha256=context.profile.sha256,
        test_point=test_point,
        control_refs=context.profile.control_refs,
        control_bindings=context.profile.control_bindings,
        dataset_split_ref=context.profile.validation_split_ref,
        derivation_parents=(
            parent_ref("drive", 0, drive),
            parent_ref("calibrated_resistance", 1, resistance),
        ),
        operation_binding=operation_binding,
    )
    return MeasurementValue(
        "I_pred",
        QuantityKind.FLOW_MAGNITUDE,
        predicted_value,
        UnitKind.ACTIVATION,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        uncertainty,
        resistance.sample_size,
    )


_RESIDUAL_RESULT_TOKEN = object()


@dataclass(frozen=True, slots=True)
class ResidualResult:
    assessment: OperatingAssessment
    residual: MeasurementValue
    relative_error: MeasurementValue
    effective_resistance: MeasurementValue | None
    resistance_delta: MeasurementValue | None
    censoring: ResidualCensoring
    censoring_reason: str | None
    _factory_token: InitVar[object] = None

    def __post_init__(self, _factory_token: object) -> None:
        if _factory_token is not _RESIDUAL_RESULT_TOKEN:
            raise ValidationError("residual results are factory-only")
        if type(self.assessment) is not OperatingAssessment:
            raise ValidationError("assessment must be an exact OperatingAssessment")
        if self.residual.quantity_kind is not QuantityKind.FLOW_RESIDUAL:
            raise ValidationError("residual must be FLOW_RESIDUAL")
        if self.relative_error.quantity_kind is not QuantityKind.RELATIVE_ERROR:
            raise ValidationError("relative_error must be RELATIVE_ERROR")
        if type(self.censoring) is not ResidualCensoring:
            raise ValidationError("censoring must be exact ResidualCensoring")
        if self.residual.uncertainty is None or self.relative_error.uncertainty is None:
            raise ValidationError("residual outputs require propagated uncertainty")
        if self.censoring is ResidualCensoring.NONE:
            if self.effective_resistance is None or self.resistance_delta is None:
                raise ValidationError("uncensored result requires resistance estimates")
            if self.censoring_reason is not None:
                raise ValidationError(
                    "uncensored result cannot have a censoring reason"
                )
        else:
            if (
                self.effective_resistance is not None
                or self.resistance_delta is not None
            ):
                raise ValidationError(
                    "censored result cannot contain resistance estimates"
                )
            if not self.censoring_reason:
                raise ValidationError("censored result requires a reason")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "censoring": self.censoring,
            "censoring_reason": self.censoring_reason,
            "operating_assessment": self.assessment,
            "effective_resistance": self.effective_resistance,
            "relative_error": self.relative_error,
            "residual": self.residual,
            "resistance_delta": self.resistance_delta,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


def _residual_uncertainties(
    context: OperationContext,
    predicted: MeasurementValue,
    observed: MeasurementValue,
    residual_value: Decimal,
) -> tuple[Uncertainty, Uncertainty]:
    if predicted.uncertainty is None or observed.uncertainty is None:
        raise ValidationError(
            "residual diagnosis requires predicted and observed uncertainty"
        )
    p = predicted.uncertainty
    o = observed.uncertainty
    with arithmetic_context():
        residual_lower = o.lower - p.upper
        residual_upper = o.upper - p.lower
        residual_standard = (
            o.standard_uncertainty * o.standard_uncertainty
            + p.standard_uncertainty * p.standard_uncertainty
        ).sqrt()
        max_abs = max(abs(residual_lower), abs(residual_upper))
        min_abs = (
            Decimal("0")
            if residual_lower <= 0 <= residual_upper
            else min(abs(residual_lower), abs(residual_upper))
        )
        denominator_low = max(p.lower, context.profile.tolerances.residual_floor)
        denominator_high = max(p.upper, context.profile.tolerances.residual_floor)
        relative_value = abs(residual_value) / max(
            predicted.value, context.profile.tolerances.residual_floor
        )
        relative_lower = min_abs / denominator_high
        relative_upper = max_abs / denominator_low
        relative_standard = residual_standard / denominator_low
    confidence = min(p.confidence_level, o.confidence_level)
    return (
        Uncertainty(
            UnitKind.ACTIVATION,
            residual_standard,
            residual_lower,
            residual_upper,
            confidence,
            context.profile.uncertainty_method_id,
        ),
        Uncertainty(
            UnitKind.DIMENSIONLESS,
            relative_standard,
            max(Decimal("0"), relative_lower),
            max(relative_value, relative_upper),
            confidence,
            context.profile.uncertainty_method_id,
        ),
    )


def diagnose_residual(
    context: OperationContext,
    drive: MeasurementValue,
    predicted: MeasurementValue,
    observed: MeasurementValue,
    known_resistance: MeasurementValue,
    assessment: OperatingAssessment,
) -> ResidualResult:
    """Emit a non-identifying active-region residual with interval censoring."""

    context.require_integrity_attestation(Capability.RESIDUAL_DIAGNOSIS)
    operation_binding = context.operation_binding(
        Capability.RESIDUAL_DIAGNOSIS, require_integrity=True
    )
    for value in (drive, predicted, observed, known_resistance):
        context.validate_measurement(value)
    if type(assessment) is not OperatingAssessment:
        raise ValidationError("assessment must be exact OperatingAssessment")
    if assessment.calibration_profile_sha256 != context.profile.sha256:
        raise ValidationError("assessment binds another calibration profile")
    if not context.profile.test_point_registered(assessment.test_point_sha256):
        raise ValidationError("assessment binds an unregistered test point")
    if assessment.control_bindings != context.profile.control_bindings:
        raise ValidationError("assessment controls do not match profile relevance")
    context.validate_operation_binding(assessment.operation_binding)
    context.evidence.artifact_for(assessment.evidence_ref)
    if assessment.mode is ClassificationMode.NUMERIC_DERIVED:
        from .synthetic import validate_operating_assessment

        validate_operating_assessment(context, assessment)
    if assessment.region is not DoseResponseRegion.ACTIVE:
        raise ValidationError(
            "residual diagnosis is disabled outside the ACTIVE region"
        )
    if assessment.semantic_outcome is SemanticOutcome.UNASSESSED:
        raise ValidationError(
            "residual diagnosis requires an assessed semantic outcome"
        )
    if (
        observed.quantity_kind is not QuantityKind.FLOW_MAGNITUDE
        or observed.unit is not UnitKind.ACTIVATION
    ):
        raise ValidationError("observed must be FLOW_MAGNITUDE in ACTIVATION units")
    if observed.measurement_kind is not MeasurementKind.INSTRUMENTED:
        raise ValidationError("observed must be an INSTRUMENTED measurement")
    if observed.uncertainty is None:
        raise ValidationError("observed measurement requires uncertainty")
    if observed.sample_size is None:
        raise ValidationError("observed measurement requires a recorded sample size")
    if not observed.provenance.control_refs:
        raise ValidationError("observed measurement requires linked controls")
    if observed.provenance.dataset_split_ref != context.profile.validation_split_ref:
        raise ValidationError(
            "observed measurement must bind the held-out validation split"
        )
    expected_prediction = predict_flow(context, drive, known_resistance)
    if predicted.sha256 != expected_prediction.sha256:
        raise ValidationError(
            "predicted value is not the registered drive/resistance prediction"
        )
    test_point = _common_test_point(drive, predicted, observed, known_resistance)
    with arithmetic_context():
        residual_value = observed.value - predicted.value
    residual_uncertainty, relative_uncertainty = _residual_uncertainties(
        context, predicted, observed, residual_value
    )
    with arithmetic_context():
        relative_value = abs(residual_value) / max(
            predicted.value, context.profile.tolerances.residual_floor
        )
    parents = (
        parent_ref("drive", 0, drive),
        parent_ref("prediction", 1, predicted),
        parent_ref("observation", 2, observed),
        parent_ref("calibrated_resistance", 3, known_resistance),
        parent_ref("operating_assessment", 4, assessment),
    )
    provenance = FieldProvenance(
        source_refs=_unique_refs(
            drive.provenance.source_refs,
            predicted.provenance.source_refs,
            observed.provenance.source_refs,
            known_resistance.provenance.source_refs,
            (assessment.evidence_ref,),
        ),
        method_id="CAS-OHM-V1-NONIDENTIFYING-RESIDUAL",
        calibration_profile_sha256=context.profile.sha256,
        instrument=observed.provenance.instrument,
        test_point=test_point,
        raw_artifact_refs=observed.provenance.raw_artifact_refs,
        control_refs=context.profile.control_refs,
        control_bindings=context.profile.control_bindings,
        dataset_split_ref=context.profile.validation_split_ref,
        derivation_parents=parents,
        operation_binding=operation_binding,
    )
    residual = MeasurementValue(
        "delta_I",
        QuantityKind.FLOW_RESIDUAL,
        residual_value,
        UnitKind.ACTIVATION,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        residual_uncertainty,
        observed.sample_size,
    )
    relative_error = MeasurementValue(
        "epsilon_I",
        QuantityKind.RELATIVE_ERROR,
        relative_value,
        UnitKind.DIMENSIONLESS,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        relative_uncertainty,
        observed.sample_size,
    )
    if observed.uncertainty.lower <= 0:
        return ResidualResult(
            assessment,
            residual,
            relative_error,
            None,
            None,
            ResidualCensoring.OBSERVED_INTERVAL_INCLUDES_ZERO,
            "alpha / I_obs is unbounded because the observed interval includes zero",
            _RESIDUAL_RESULT_TOKEN,
        )
    if drive.value <= 0:
        raise ValidationError("positive observed flow requires positive drive")
    drive_lower, drive_upper, drive_standard = _bounds(drive)
    observed_lower, observed_upper, observed_standard = _bounds(observed)
    resistance_lower, resistance_upper, resistance_standard = _bounds(known_resistance)
    with arithmetic_context():
        effective_value = drive.value / observed.value
        effective_lower = drive_lower / observed_upper
        effective_upper = drive_upper / observed_lower
        term_drive = drive_standard / observed.value
        term_observed = (
            drive.value * observed_standard / (observed.value * observed.value)
        )
        effective_standard = (
            term_drive * term_drive + term_observed * term_observed
        ).sqrt()
        delta_value = effective_value - known_resistance.value
        delta_lower = effective_lower - resistance_upper
        delta_upper = effective_upper - resistance_lower
        delta_standard = (
            effective_standard * effective_standard
            + resistance_standard * resistance_standard
        ).sqrt()
    confidence = _confidence(drive, observed, known_resistance)
    effective_uncertainty = Uncertainty(
        UnitKind.ALPHA_PER_ACTIVATION,
        effective_standard,
        effective_lower,
        max(effective_value, effective_upper),
        confidence,
        context.profile.uncertainty_method_id,
    )
    delta_uncertainty = Uncertainty(
        UnitKind.ALPHA_PER_ACTIVATION,
        delta_standard,
        delta_lower,
        delta_upper,
        confidence,
        context.profile.uncertainty_method_id,
    )
    effective_resistance = MeasurementValue(
        "R_apparent",
        QuantityKind.EFFECTIVE_RESISTANCE,
        effective_value,
        UnitKind.ALPHA_PER_ACTIVATION,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        effective_uncertainty,
        observed.sample_size,
        ResistanceRole.APPARENT_SAME_SAMPLE,
    )
    resistance_delta = MeasurementValue(
        "delta_R",
        QuantityKind.RESISTANCE_DELTA,
        delta_value,
        UnitKind.ALPHA_PER_ACTIVATION,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        delta_uncertainty,
        observed.sample_size,
    )
    return ResidualResult(
        assessment,
        residual,
        relative_error,
        effective_resistance,
        resistance_delta,
        ResidualCensoring.NONE,
        None,
        _RESIDUAL_RESULT_TOKEN,
    )
