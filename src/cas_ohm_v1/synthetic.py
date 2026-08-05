"""Numeric known-fault generators and independently derived sweep classification."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .calibration import OperationContext, ToleranceProfile
from .canonical import (
    ValidationError,
    arithmetic_context,
    canonical_bytes,
    require_decimal,
)
from .model import (
    _ASSESSMENT_FACTORY_TOKEN,
    ArtifactRef,
    ClassificationMode,
    DoseResponseRegion,
    OperatingAssessment,
    OperatingClassification,
    SemanticOutcome,
    SweepObservation,
    TestPointIdentity,
)


class SyntheticFault(str, Enum):
    NONE = "NONE"
    HIDDEN_CONSTRAINT = "HIDDEN_CONSTRAINT"
    BYPASS = "BYPASS"
    CUTOFF = "CUTOFF"
    SATURATION = "SATURATION"
    OFF_AXIS = "OFF_AXIS"
    NON_OHMIC = "NON_OHMIC"


SyntheticObservation = SweepObservation


@dataclass(frozen=True, slots=True)
class SyntheticBoard:
    base_resistance: Decimal
    cutoff_drive: Decimal
    saturation_flow: Decimal
    hidden_resistance: Decimal
    bypass_reduction: Decimal
    off_axis_fraction: Decimal
    fault: SyntheticFault

    def __post_init__(self) -> None:
        base = require_decimal(self.base_resistance, "base_resistance")
        cutoff = require_decimal(self.cutoff_drive, "cutoff_drive")
        saturation = require_decimal(self.saturation_flow, "saturation_flow")
        hidden = require_decimal(self.hidden_resistance, "hidden_resistance")
        bypass = require_decimal(self.bypass_reduction, "bypass_reduction")
        off_axis = require_decimal(self.off_axis_fraction, "off_axis_fraction")
        if base <= 0 or saturation <= 0:
            raise ValidationError(
                "base resistance and saturation flow must be positive"
            )
        if cutoff < 0 or hidden < 0 or bypass < 0:
            raise ValidationError(
                "cutoff and resistance adjustments must be non-negative"
            )
        if not Decimal("0") <= off_axis <= Decimal("1"):
            raise ValidationError("off_axis_fraction must be in [0, 1]")
        if type(self.fault) is not SyntheticFault:
            raise ValidationError("fault must be exact SyntheticFault")
        if self.fault is SyntheticFault.HIDDEN_CONSTRAINT and hidden == 0:
            raise ValidationError("HIDDEN_CONSTRAINT requires hidden_resistance")
        if self.fault is SyntheticFault.BYPASS and (bypass == 0 or bypass >= base):
            raise ValidationError(
                "BYPASS requires 0 < bypass_reduction < base_resistance"
            )
        if self.fault is SyntheticFault.OFF_AXIS and off_axis == 0:
            raise ValidationError("OFF_AXIS requires off_axis_fraction")

    def observe(self, drive: Decimal) -> SyntheticObservation:
        drive = require_decimal(drive, "drive")
        if drive < 0:
            raise ValidationError("drive must be non-negative")
        with arithmetic_context():
            effective = self.base_resistance
            if self.fault is SyntheticFault.HIDDEN_CONSTRAINT:
                effective += self.hidden_resistance
            elif self.fault is SyntheticFault.BYPASS:
                effective -= self.bypass_reduction
            if self.fault is SyntheticFault.CUTOFF and drive <= self.cutoff_drive:
                flow = Decimal("0")
            elif self.fault is SyntheticFault.NON_OHMIC:
                flow = drive * drive / effective
            else:
                ideal = drive / effective
                if (
                    self.fault is SyntheticFault.SATURATION
                    and ideal >= self.saturation_flow
                ):
                    flow = self.saturation_flow
                else:
                    flow = ideal
            off_axis = (
                flow * self.off_axis_fraction
                if self.fault is SyntheticFault.OFF_AXIS
                else Decimal("0")
            )
        return SyntheticObservation(drive, flow, off_axis)

    def sweep(self, drives: tuple[Decimal, ...]) -> tuple[SyntheticObservation, ...]:
        if type(drives) is not tuple or len(drives) < 3:
            raise ValidationError("synthetic sweep requires at least three drives")
        observations = tuple(self.observe(drive) for drive in drives)
        if tuple(item.drive for item in observations) != tuple(
            sorted({item.drive for item in observations})
        ):
            raise ValidationError("synthetic sweep drives must be strictly increasing")
        return observations


def _derive_classification(
    observations: tuple[SweepObservation, ...],
    index: int,
    expected_resistance: Decimal,
    tolerances: ToleranceProfile,
) -> OperatingClassification:
    """Derive region and semantic axes from numeric neighbors, not fault labels."""

    if type(observations) is not tuple or len(observations) < 3:
        raise ValidationError("classification requires at least three observations")
    if type(index) is not int or not 0 < index < len(observations) - 1:
        raise ValidationError(
            "classification index must have a predecessor and successor"
        )
    resistance = require_decimal(expected_resistance, "expected_resistance")
    if resistance <= 0:
        raise ValidationError("expected_resistance must be positive")
    if type(tolerances) is not ToleranceProfile:
        raise ValidationError("tolerances must be exact ToleranceProfile")
    before, current, after = observations[index - 1 : index + 2]
    if not before.drive < current.drive < after.drive:
        raise ValidationError("observations must be ordered by drive")
    with arithmetic_context():
        semantic_ratio = current.off_axis_activation / max(
            current.flow, tolerances.residual_floor
        )
        expected_slope = Decimal("1") / resistance
        backward_slope = (current.flow - before.flow) / (current.drive - before.drive)
        forward_slope = (after.flow - current.flow) / (after.drive - current.drive)
        slope_floor = expected_slope * tolerances.delta_relative
        relative_slope_error = (
            max(
                abs(backward_slope - expected_slope),
                abs(forward_slope - expected_slope),
            )
            / expected_slope
        )
    semantic = (
        SemanticOutcome.OFF_AXIS
        if semantic_ratio > tolerances.off_target_max
        else SemanticOutcome.INTENDED
    )
    if current.flow <= tolerances.delta_abs:
        region = DoseResponseRegion.CUTOFF
    elif abs(forward_slope) <= slope_floor and backward_slope > slope_floor:
        region = DoseResponseRegion.SATURATION
    elif relative_slope_error > tolerances.delta_relative:
        region = DoseResponseRegion.NON_OHMIC
    else:
        region = DoseResponseRegion.ACTIVE
    return OperatingClassification(region, semantic)


def classify_sweep_point(
    context: OperationContext,
    observations: tuple[SweepObservation, ...],
    index: int,
    expected_resistance: Decimal,
    sweep_ref: ArtifactRef,
    test_point: TestPointIdentity | None = None,
) -> OperatingAssessment:
    """Factory-bind a numeric classification to its exact sweep and context."""

    if type(context) is not OperationContext:
        raise ValidationError("context must be an exact OperationContext")
    if type(sweep_ref) is not ArtifactRef:
        raise ValidationError("sweep_ref must be an exact ArtifactRef")
    if test_point is None:
        if len(context.profile.test_points) != 1:
            raise ValidationError(
                "test_point is required when the profile has multiple points"
            )
        test_point = context.profile.test_points[0]
    if type(test_point) is not TestPointIdentity or not (
        context.profile.test_point_registered(test_point)
    ):
        raise ValidationError("test_point must be an exact registered point")
    artifact = context.evidence.artifact_for(sweep_ref)
    expected_bytes = canonical_bytes(observations)
    if artifact.payload != expected_bytes:
        raise ValidationError("sweep evidence bytes do not match observations")
    classification = _derive_classification(
        observations, index, expected_resistance, context.profile.tolerances
    )
    return OperatingAssessment(
        classification,
        ClassificationMode.NUMERIC_DERIVED,
        context.profile.response_region_method_id,
        context.profile.sha256,
        test_point.sha256,
        sweep_ref,
        observations,
        index,
        expected_resistance,
        context.profile.control_bindings,
        context.operation_binding(None, require_integrity=False),
        _factory_token=_ASSESSMENT_FACTORY_TOKEN,
    )


def validate_operating_assessment(
    context: OperationContext, assessment: OperatingAssessment
) -> None:
    if (
        type(context) is not OperationContext
        or type(assessment) is not OperatingAssessment
    ):
        raise ValidationError("assessment validation requires exact typed inputs")
    if assessment.mode is not ClassificationMode.NUMERIC_DERIVED:
        raise ValidationError("external operating classifications are unverified")
    if assessment.calibration_profile_sha256 != context.profile.sha256:
        raise ValidationError("assessment binds another calibration profile")
    if not context.profile.test_point_registered(assessment.test_point_sha256):
        raise ValidationError("assessment binds an unregistered test point")
    if assessment.method_id != context.profile.response_region_method_id:
        raise ValidationError("assessment method does not match the profile")
    if assessment.control_bindings != context.profile.control_bindings:
        raise ValidationError("assessment control relevance does not match profile")
    context.validate_operation_binding(assessment.operation_binding)
    artifact = context.evidence.artifact_for(assessment.evidence_ref)
    if artifact.payload != canonical_bytes(assessment.observations):
        raise ValidationError("assessment sweep evidence was not preserved")
    if assessment.index is None or assessment.expected_resistance is None:
        raise ValidationError("numeric assessment is incomplete")
    expected = _derive_classification(
        assessment.observations,
        assessment.index,
        assessment.expected_resistance,
        context.profile.tolerances,
    )
    if assessment.classification != expected:
        raise ValidationError("assessment classification fails numeric replay")
