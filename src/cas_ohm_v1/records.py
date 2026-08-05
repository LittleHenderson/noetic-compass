"""Closed-world CJTQ research packets with resolved evidence and lineage."""

from __future__ import annotations

from dataclasses import InitVar, dataclass

from .calibration import OperationContext, normalize_flow
from .canonical import (
    CapabilityError,
    ValidationError,
    canonical_sha256,
    require_sha256,
    require_text,
)
from .canonical import (
    canonical_bytes as encode_canonical,
)
from .diagnostics import diagnose_residual, predict_flow
from .model import (
    ADMISSION_RING,
    DISCLOSURE_STATUS,
    LICENSE_STATUS,
    RESEARCH_STATUS,
    ArtifactRef,
    Capability,
    ClassificationMode,
    ControlBinding,
    DoseResponseRegion,
    MeasurementKind,
    MeasurementValue,
    NonClaimExtension,
    OperatingAssessment,
    OperationBinding,
    QuantityKind,
    ResistanceRole,
    ReviewState,
    SemanticOutcome,
)

REQUIRED_PACKET_FIELDS = frozenset(
    {
        "alpha",
        "R_calibrated",
        "I_pred",
        "I_obs",
        "I_Q",
        "lambda",
        "delta_I",
        "epsilon_I",
    }
)


@dataclass(frozen=True, slots=True)
class CJTQRecord:
    record_id: str
    profile_sha256: str
    test_point_sha256: str
    fields: tuple[MeasurementValue, ...]
    operating_assessment: OperatingAssessment
    evidence_refs: tuple[ArtifactRef, ...]
    control_refs: tuple[ArtifactRef, ...]
    control_bindings: tuple[ControlBinding, ...]
    review_state: ReviewState
    extensions: tuple[NonClaimExtension, ...] = ()

    def __post_init__(self) -> None:
        require_text(self.record_id, "record_id")
        require_sha256(self.profile_sha256, "profile_sha256")
        require_sha256(self.test_point_sha256, "test_point_sha256")
        if type(self.fields) is not tuple:
            raise ValidationError("fields must be an exact tuple")
        if any(type(field) is not MeasurementValue for field in self.fields):
            raise ValidationError("fields must contain exact MeasurementValue values")
        names = [field.field_name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValidationError("record field names must be unique")
        unknown = set(names) - REQUIRED_PACKET_FIELDS
        if unknown:
            raise ValidationError(
                "record contains fields outside the closed packet schema: "
                + ", ".join(sorted(unknown))
            )
        if type(self.operating_assessment) is not OperatingAssessment:
            raise ValidationError(
                "operating_assessment must be an exact OperatingAssessment"
            )
        for refs, field_name in (
            (self.evidence_refs, "evidence_refs"),
            (self.control_refs, "control_refs"),
        ):
            if type(refs) is not tuple:
                raise ValidationError(f"{field_name} must be an exact tuple")
            if any(type(ref) is not ArtifactRef for ref in refs):
                raise ValidationError(
                    f"{field_name} must contain exact ArtifactRef values"
                )
            if len({ref.sha256 for ref in refs}) != len(refs):
                raise ValidationError(f"{field_name} contains duplicates")
        if type(self.control_bindings) is not tuple or any(
            type(binding) is not ControlBinding for binding in self.control_bindings
        ):
            raise ValidationError("control_bindings must contain exact bindings")
        if len({binding.sha256 for binding in self.control_bindings}) != len(
            self.control_bindings
        ):
            raise ValidationError("control_bindings contains duplicates")
        bound_refs = tuple(
            sorted(
                {
                    binding.ref.sha256: binding.ref for binding in self.control_bindings
                }.values(),
                key=lambda ref: ref.sha256,
            )
        )
        if bound_refs != self.control_refs:
            raise ValidationError("record controls and relevance bindings must match")
        if type(self.review_state) is not ReviewState:
            raise ValidationError("review_state must be an exact ReviewState")
        if type(self.extensions) is not tuple or any(
            type(extension) is not NonClaimExtension for extension in self.extensions
        ):
            raise ValidationError("extensions must be typed nonclaim extensions")
        if len({extension.sha256 for extension in self.extensions}) != len(
            self.extensions
        ):
            raise ValidationError("extensions contain duplicates")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "admission_ring": ADMISSION_RING,
            "control_refs": tuple(
                sorted(self.control_refs, key=lambda ref: ref.sha256)
            ),
            "control_bindings": tuple(
                sorted(self.control_bindings, key=lambda value: value.sha256)
            ),
            "disclosure_status": DISCLOSURE_STATUS,
            "evidence_refs": tuple(
                sorted(self.evidence_refs, key=lambda ref: ref.sha256)
            ),
            "fields": tuple(sorted(self.fields, key=lambda field: field.field_name)),
            "extensions": tuple(
                sorted(self.extensions, key=lambda value: value.sha256)
            ),
            "license_status": LICENSE_STATUS,
            "operating_assessment": self.operating_assessment,
            "profile_sha256": self.profile_sha256,
            "record_id": self.record_id,
            "research_status": RESEARCH_STATUS,
            "review_state": self.review_state,
            "schema": "CAS-OHM-V1-CJTQ-RECORD",
            "test_point_sha256": self.test_point_sha256,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return encode_canonical(self)

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


_ELIGIBILITY_RESULT_TOKEN = object()


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    structurally_complete: bool
    authenticated_eligible: bool
    structural_reasons: tuple[str, ...]
    authentication_reasons: tuple[str, ...]
    operation_binding: OperationBinding
    _factory_token: InitVar[object] = None

    def __post_init__(self, _factory_token: object) -> None:
        if _factory_token is not _ELIGIBILITY_RESULT_TOKEN:
            raise ValidationError("eligibility results are factory-only")
        if (
            type(self.structurally_complete) is not bool
            or type(self.authenticated_eligible) is not bool
        ):
            raise ValidationError("eligibility states must be exact booleans")
        if type(self.operation_binding) is not OperationBinding:
            raise ValidationError("operation_binding must be exact OperationBinding")
        for reasons, field_name in (
            (self.structural_reasons, "structural_reasons"),
            (self.authentication_reasons, "authentication_reasons"),
        ):
            if type(reasons) is not tuple or any(
                type(reason) is not str or not reason for reason in reasons
            ):
                raise ValidationError(f"{field_name} must be an exact string tuple")
        if self.structurally_complete == bool(self.structural_reasons):
            raise ValidationError(
                "structural completeness and structural reasons are inconsistent"
            )
        if self.authenticated_eligible and (
            not self.structurally_complete or self.authentication_reasons
        ):
            raise ValidationError("authenticated eligibility requires all gates")

    @property
    def eligible(self) -> bool:
        return self.authenticated_eligible

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.structural_reasons + self.authentication_reasons)))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "admission_ring": ADMISSION_RING,
            "disclosure_status": DISCLOSURE_STATUS,
            "authenticated_eligible": self.authenticated_eligible,
            "authentication_reasons": self.authentication_reasons,
            "license_status": LICENSE_STATUS,
            "operation_binding": self.operation_binding,
            "structural_reasons": self.structural_reasons,
            "structurally_complete": self.structurally_complete,
            "research_status": RESEARCH_STATUS,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


def _field_contract(field: MeasurementValue) -> str | None:
    contracts: dict[str, tuple[QuantityKind, MeasurementKind]] = {
        "alpha": (QuantityKind.DRIVE_INTERVENTION, MeasurementKind.DESIGN_VALUE),
        "R_calibrated": (
            QuantityKind.EFFECTIVE_RESISTANCE,
            MeasurementKind.MODEL_DERIVED,
        ),
        "I_pred": (QuantityKind.FLOW_MAGNITUDE, MeasurementKind.MODEL_DERIVED),
        "I_obs": (QuantityKind.FLOW_MAGNITUDE, MeasurementKind.INSTRUMENTED),
        "I_Q": (QuantityKind.NORMALIZED_FLOW, MeasurementKind.MODEL_DERIVED),
        "lambda": (QuantityKind.OVERLOAD_RATIO, MeasurementKind.MODEL_DERIVED),
        "delta_I": (QuantityKind.FLOW_RESIDUAL, MeasurementKind.MODEL_DERIVED),
        "epsilon_I": (QuantityKind.RELATIVE_ERROR, MeasurementKind.MODEL_DERIVED),
    }
    expected = contracts.get(field.field_name)
    if expected is None:
        return None
    if (field.quantity_kind, field.measurement_kind) != expected:
        return "FIELD_CONTRACT_MISMATCH"
    if (
        field.field_name == "R_calibrated"
        and field.resistance_role is not ResistanceRole.CALIBRATED_HELD_OUT
    ):
        return "RESISTANCE_ROLE_MISMATCH"
    return None


def packet_eligibility(
    context: OperationContext, record: CJTQRecord
) -> EligibilityResult:
    """Separate research structural completeness from authenticated eligibility."""

    if type(context) is not OperationContext:
        raise ValidationError("context must be an exact OperationContext")
    if type(record) is not CJTQRecord:
        raise ValidationError("record must be an exact CJTQRecord")
    context.evidence.revalidate_all()
    reasons: list[str] = []
    if record.profile_sha256 != context.profile.sha256:
        reasons.append("PROFILE_DIGEST_MISMATCH")
    if not context.profile.test_point_registered(record.test_point_sha256):
        reasons.append("TEST_POINT_NOT_REGISTERED")
    if record.review_state is not ReviewState.REVIEWED:
        reasons.append("RECORD_NOT_REVIEWED")
    if (
        record.operating_assessment.region is not DoseResponseRegion.ACTIVE
        or record.operating_assessment.semantic_outcome is SemanticOutcome.UNASSESSED
    ):
        reasons.append("OPERATING_CLASSIFICATION_NOT_ADMISSIBLE")
    if record.operating_assessment.mode is not ClassificationMode.NUMERIC_DERIVED:
        reasons.append("OPERATING_CLASSIFICATION_UNVERIFIED")
    else:
        try:
            from .synthetic import validate_operating_assessment

            validate_operating_assessment(context, record.operating_assessment)
        except ValidationError as exc:
            reasons.append(f"OPERATING_CLASSIFICATION_UNRESOLVED:{exc}")
    field_names = {field.field_name for field in record.fields}
    for missing in sorted(REQUIRED_PACKET_FIELDS - field_names):
        reasons.append(f"REQUIRED_FIELD_MISSING:{missing}")
    if not record.evidence_refs:
        reasons.append("RECORD_EVIDENCE_MISSING")
    if not record.control_refs:
        reasons.append("RECORD_CONTROLS_MISSING")
    if record.control_refs != context.profile.control_refs:
        reasons.append("RECORD_CONTROL_SET_MISMATCH")
    if record.control_bindings != context.profile.control_bindings:
        reasons.append("RECORD_CONTROL_RELEVANCE_MISMATCH")
    try:
        context.evidence.require_refs(record.evidence_refs + record.control_refs)
    except ValidationError as exc:
        reasons.append(f"RECORD_EVIDENCE_UNRESOLVED:{exc}")
    evidence_hashes = {ref.sha256 for ref in record.evidence_refs}
    control_hashes = {ref.sha256 for ref in record.control_refs}
    required_packet_refs = (
        context.profile.all_artifact_refs()
        + (context.authority.manifest_ref,)
        + tuple(attestation.evidence_ref for attestation in context.attestations)
        + (record.operating_assessment.evidence_ref,)
        + tuple(extension.payload_ref for extension in record.extensions)
    )
    if context.current_clock_receipt is not None:
        required_packet_refs += (context.current_clock_receipt.evidence_ref,)
    for field in record.fields:
        provenance = field.provenance
        required_packet_refs += (
            provenance.source_refs
            + provenance.raw_artifact_refs
            + provenance.control_refs
        )
        if provenance.dataset_split_ref is not None:
            required_packet_refs += (provenance.dataset_split_ref,)
    allowed_evidence_hashes = {ref.sha256 for ref in required_packet_refs}
    for ref in record.evidence_refs:
        if ref.sha256 not in allowed_evidence_hashes:
            reasons.append(f"PACKET_EVIDENCE_OUTSIDE_CLOSED_SCHEMA:{ref.sha256}")
    for ref in required_packet_refs:
        if ref.sha256 not in evidence_hashes:
            reasons.append(f"PROFILE_OR_AUTHORITY_EVIDENCE_NOT_IN_PACKET:{ref.sha256}")
    for binding in context.profile.control_bindings:
        if binding.ref.sha256 not in control_hashes:
            reasons.append(f"PROFILE_CONTROL_NOT_DECLARED:{binding.ref.sha256}")
    instrumented_count = 0
    for field in record.fields:
        prefix = f"FIELD[{field.field_name}]"
        contract_failure = _field_contract(field)
        if contract_failure:
            reasons.append(f"{prefix}:{contract_failure}")
        try:
            context.validate_measurement(field)
        except ValidationError as exc:
            reasons.append(f"{prefix}:UNRESOLVED:{exc}")
        provenance = field.provenance
        if provenance.calibration_profile_sha256 != context.profile.sha256:
            reasons.append(f"{prefix}:PROFILE_DIGEST_MISMATCH")
        if (
            provenance.test_point is None
            or provenance.test_point.sha256 != record.test_point_sha256
        ):
            reasons.append(f"{prefix}:TEST_POINT_MISMATCH")
        field_refs = (
            provenance.source_refs
            + provenance.raw_artifact_refs
            + provenance.control_refs
            + ((provenance.dataset_split_ref,) if provenance.dataset_split_ref else ())
        )
        for ref in field_refs:
            if ref.sha256 not in evidence_hashes:
                reasons.append(f"{prefix}:EVIDENCE_NOT_IN_PACKET:{ref.sha256}")
        if field.measurement_kind is not MeasurementKind.DESIGN_VALUE:
            if field.uncertainty is None:
                reasons.append(f"{prefix}:UNCERTAINTY_MISSING")
            if field.sample_size is None:
                reasons.append(f"{prefix}:SAMPLE_SIZE_MISSING")
            if not provenance.control_refs:
                reasons.append(f"{prefix}:CONTROLS_MISSING")
            if provenance.control_bindings != context.profile.control_bindings:
                reasons.append(f"{prefix}:CONTROL_RELEVANCE_MISMATCH")
            for control in provenance.control_refs:
                if control.sha256 not in control_hashes:
                    reasons.append(f"{prefix}:CONTROL_NOT_DECLARED:{control.sha256}")
        if (
            field.measurement_kind is MeasurementKind.MODEL_DERIVED
            and not provenance.derivation_parents
        ):
            reasons.append(f"{prefix}:PARENTS_MISSING")
        if field.measurement_kind is MeasurementKind.INSTRUMENTED:
            instrumented_count += 1
            if (
                provenance.instrument is None
                or not context.profile.instrument_registered(provenance.instrument)
            ):
                reasons.append(f"{prefix}:INSTRUMENT_NOT_REGISTERED")
            if not provenance.raw_artifact_refs:
                reasons.append(f"{prefix}:RAW_ARTIFACT_MISSING")
    if instrumented_count == 0:
        reasons.append("INSTRUMENTED_MEASUREMENT_MISSING")
    if REQUIRED_PACKET_FIELDS <= field_names:
        fields = {field.field_name: field for field in record.fields}
        try:
            expected_prediction = predict_flow(
                context, fields["alpha"], fields["R_calibrated"]
            )
            if fields["I_pred"].sha256 != expected_prediction.sha256:
                reasons.append("CROSS_FIELD_MISMATCH:I_pred")
            expected_normalized = normalize_flow(
                context, fields["I_obs"], fields["I_obs"].provenance.test_point
            )
            if fields["I_Q"].sha256 != expected_normalized.q10.sha256:
                reasons.append("CROSS_FIELD_MISMATCH:I_Q")
            if fields["lambda"].sha256 != expected_normalized.overload_ratio.sha256:
                reasons.append("CROSS_FIELD_MISMATCH:lambda")
            expected_diagnostic = diagnose_residual(
                context,
                fields["alpha"],
                fields["I_pred"],
                fields["I_obs"],
                fields["R_calibrated"],
                record.operating_assessment,
            )
            if fields["delta_I"].sha256 != expected_diagnostic.residual.sha256:
                reasons.append("CROSS_FIELD_MISMATCH:delta_I")
            if fields["epsilon_I"].sha256 != expected_diagnostic.relative_error.sha256:
                reasons.append("CROSS_FIELD_MISMATCH:epsilon_I")
        except (CapabilityError, ValidationError) as exc:
            reasons.append(f"CROSS_FIELD_RECOMPUTATION_FAILED:{exc}")
    structural_reasons = tuple(sorted(set(reasons)))
    authentication_reasons = context.authentication_reasons(
        Capability.PACKET_ELIGIBILITY
    )
    structurally_complete = not structural_reasons
    authenticated_eligible = (
        structurally_complete
        and context.authenticated_current
        and not authentication_reasons
    )
    return EligibilityResult(
        structurally_complete,
        authenticated_eligible,
        structural_reasons,
        authentication_reasons,
        context.operation_binding(
            Capability.PACKET_ELIGIBILITY, require_integrity=False
        ),
        _factory_token=_ELIGIBILITY_RESULT_TOKEN,
    )
