"""Exact nonreporting terminal disposition for diagnostic calibration.

This additive module consumes only the prospective calibration Rule, the exact
post-access 480-row activation Dataset, and the frozen-runtime FitTranscript.
It deliberately has no API for caller-supplied coefficients, scores, counts,
thresholds, Evidence Packets, evaluation promotion, claims, products, or public
release.  A phase receives exactly one durable same-file SQLite disposition:
either an eligible two-detector bundle is frozen for diagnostic use only, or
the calibration is rejected without reporting its outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
import stat
from types import MappingProxyType
from typing import Any, Mapping

from ._strict_json import (
    canonical_json_bytes,
    canonical_sha256,
    freeze_json,
    load_json_object,
    sha256_bytes,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_enum,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_timestamp,
    parse_artifact_ref,
)
from .diagnostic_calibration_fit import (
    DIAGNOSTIC_CALIBRATION_DETECTOR_ROLES,
    ELIGIBLE_THRESHOLD_SELECTED,
    NO_ELIGIBLE_THRESHOLD,
    TARGET_LAYER_DETECTOR,
    WRONG_LAYER_CONTROL_DETECTOR,
    DiagnosticBinary64,
    DiagnosticCalibrationActivationDatasetArtifact,
    DiagnosticCalibrationCandidateResult,
    DiagnosticCalibrationFitTranscriptArtifact,
    DiagnosticCalibrationModelFit,
    DiagnosticCalibrationRuleArtifact,
    replay_diagnostic_calibration_activation_dataset_projection,
    replay_diagnostic_calibration_fit_transcript,
    replay_diagnostic_calibration_fit_transcript_projection,
)
from .diagnostic_lifecycle import DiagnosticSharedPlanReplayContext
from .diagnostic_phase_coordinator import (
    PHASE_OUTCOME_ACCESSED,
    PHASE_RECONCILED_CLEAN,
    PHASE_RECONCILED_REJECTED,
    DiagnosticPhaseOutcomeAccessArtifact,
    DiagnosticPhaseReconciliationArtifact,
    DiagnosticPhaseRegistrationArtifact,
    DiagnosticPhaseStoreBindingArtifact,
    replay_diagnostic_phase_outcome_access_projection,
    replay_diagnostic_phase_reconciliation_projection,
    replay_diagnostic_phase_registration_projection,
    replay_diagnostic_phase_store_binding_projection,
)


DIAGNOSTIC_CALIBRATION_ANALYSIS_SCHEMA = (
    "cas_harness_v2.diagnostic_calibration_analysis.v2"
)
DIAGNOSTIC_CALIBRATION_DETECTOR_BUNDLE_SCHEMA = (
    "cas_harness_v2.diagnostic_calibration_detector_bundle.v2"
)
DIAGNOSTIC_CALIBRATION_DISPOSITION_SCHEMA = (
    "cas_harness_v2.diagnostic_calibration_disposition.v2"
)
DIAGNOSTIC_CALIBRATION_ANALYSIS_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-calibration-analysis+json"
)
DIAGNOSTIC_CALIBRATION_DETECTOR_BUNDLE_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-calibration-detector-bundle+json"
)
DIAGNOSTIC_CALIBRATION_DISPOSITION_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-calibration-disposition+json"
)

CALIBRATION_ANALYSIS_ELIGIBLE = "CALIBRATION_ANALYSIS_ELIGIBLE"
CALIBRATION_ANALYSIS_INELIGIBLE = "CALIBRATION_ANALYSIS_INELIGIBLE"
CALIBRATION_FROZEN_NONREPORTING = "CALIBRATION_FROZEN_NONREPORTING"
CALIBRATION_REJECTED_NONREPORTING = "CALIBRATION_REJECTED_NONREPORTING"

_EARLY_REJECTION_REASONS = frozenset(
    {
        "VALIDATED_ROW_REJECTION",
        "EXECUTION_WINDOW_EXPIRED",
        "COMPLETE_OUTPUT_SET_UNAVAILABLE",
    }
)
_POST_ACCESS_REJECTION_REASON = "NO_ELIGIBLE_THRESHOLD"
_MAPPING_PROXY_TYPE = type(MappingProxyType({}))

_BOUNDARY = {
    "scope": "DIAGNOSTIC_CALIBRATION_NONREPORTING_ONLY",
    "admission_ring": 4,
    "criteria_status": "OPEN",
    "scientific_correctness": "NOT_ESTABLISHED",
    "product_claim_status": "NOT LICENSED",
    "disclosure_status": "HELD",
    "evidence_packet_v2": "FORBIDDEN",
    "evaluation_execution": "NOT_AUTHORIZED",
    "evaluation_authority": "NOT_GRANTED",
    "evaluation_promotion": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
    "product_route": "FORBIDDEN",
    "reporting": "FORBIDDEN",
    "license_status": "NOT LICENSED",
    "license_granted": False,
    "public_release": False,
    "trusted_time": "NOT_PROVIDED",
    "replication": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "out_of_band_read_prevention": "NOT_ESTABLISHED",
}


class DiagnosticCalibrationError(RuntimeError):
    """Base error for terminal calibration disposition."""


class DiagnosticCalibrationValidationError(DiagnosticCalibrationError):
    """A carrier or dependency differs from exact replay."""


class DiagnosticCalibrationConflict(DiagnosticCalibrationError):
    """The create-once phase disposition conflicts with retained state."""


class DiagnosticCalibrationIntegrityError(DiagnosticCalibrationError):
    """The same-file phase/disposition inventory cannot be reconciled."""


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _artifact_ids_in_json(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        artifact_id = value.get("artifact_id")
        if (
            type(artifact_id) is str
            and "sha256" in value
            and "byte_length" in value
            and "media_type" in value
        ):
            found.add(artifact_id)
        for child in value.values():
            found.update(_artifact_ids_in_json(child))
    elif type(value) in (tuple, list):
        for child in value:
            found.update(_artifact_ids_in_json(child))
    return found


def _canonical_object(
    raw: bytes | bytearray | memoryview, path: str
) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, obj = load_json_object(raw)
        if snapshot != canonical_json_bytes(obj):
            raise DiagnosticCalibrationValidationError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, obj
    except DiagnosticCalibrationValidationError:
        raise
    except (ValueError, TypeError) as exc:
        raise DiagnosticCalibrationValidationError(f"{path}: {exc}") from exc


def _require_exact_type(value: Any, expected: type, path: str) -> None:
    if type(value) is not expected:
        raise DiagnosticCalibrationValidationError(
            f"{path} must be an exact {expected.__name__}"
        )


def _require_frozen(value: Any, path: str) -> None:
    if type(value) is _MAPPING_PROXY_TYPE:
        for key, child in value.items():
            if type(key) is not str:
                raise DiagnosticCalibrationValidationError(
                    f"{path} contains a non-string key"
                )
            _require_frozen(child, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, child in enumerate(value):
            _require_frozen(child, f"{path}[{index}]")
        return
    if type(value) in (str, int, bool) or value is None:
        return
    raise DiagnosticCalibrationValidationError(
        f"{path} must be recursively immutable frozen JSON"
    )


def _require_artifact_storage(value: Any, path: str) -> None:
    if (
        type(value.raw_bytes) is not bytes
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.payload) is not _MAPPING_PROXY_TYPE
    ):
        raise DiagnosticCalibrationValidationError(
            f"{path} raw/hash/length/payload must use exact immutable types"
        )
    _require_frozen(value.payload, f"{path}.payload")


def _require_ref_projection_types(value: ArtifactRef, path: str) -> None:
    _require_exact_type(value, ArtifactRef, path)
    if (
        type(value.artifact_id) is not str
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.media_type) is not str
    ):
        raise DiagnosticCalibrationValidationError(
            f"{path} fields must use exact immutable scalar types"
        )


def _require_boundary(value: Any) -> None:
    try:
        boundary = expect_object(value, "$.boundary")
        expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationValidationError(str(exc)) from exc
    if boundary != _BOUNDARY:
        raise DiagnosticCalibrationValidationError(
            "calibration carrier fabricated reporting, evaluation, claim, product, "
            "publication, durability, or scientific authority"
        )


def _binary64_value(value: DiagnosticBinary64 | None) -> dict[str, str] | None:
    if value is None:
        return None
    _require_exact_type(value, DiagnosticBinary64, "binary64")
    if any(type(item) is not str for item in (value.hex, value.bytes_hex, value.decimal)):
        raise DiagnosticCalibrationValidationError(
            "binary64 carrier fields must be exact immutable text"
        )
    return {"hex": value.hex, "bytes_hex": value.bytes_hex, "decimal": value.decimal}


def _require_binary64_projection_types(value: DiagnosticBinary64, path: str) -> None:
    _require_exact_type(value, DiagnosticBinary64, path)
    if any(type(getattr(value, name)) is not str for name in ("hex", "bytes_hex", "decimal")):
        raise DiagnosticCalibrationValidationError(
            f"{path} fields must use exact immutable text"
        )


def _selected_candidate(
    fit: DiagnosticCalibrationModelFit,
) -> DiagnosticCalibrationCandidateResult | None:
    if fit.selection_status == NO_ELIGIBLE_THRESHOLD:
        if fit.selected_threshold is not None or fit.selected_predictions is not None:
            raise DiagnosticCalibrationValidationError(
                "ineligible model fit cannot expose a selected threshold/predictions"
            )
        return None
    if (
        fit.selection_status != ELIGIBLE_THRESHOLD_SELECTED
        or fit.selected_threshold is None
        or fit.selected_predictions is None
    ):
        raise DiagnosticCalibrationValidationError(
            "model fit selection projection is incomplete"
        )
    matches = tuple(
        item for item in fit.candidates if item.threshold == fit.selected_threshold
    )
    if (
        len(matches) != 1
        or not matches[0].eligible
        or matches[0].predictions != fit.selected_predictions
    ):
        raise DiagnosticCalibrationValidationError(
            "selected threshold/predictions do not match one exact eligible candidate"
        )
    return matches[0]


def _fit_result_value(fit: DiagnosticCalibrationModelFit) -> dict[str, Any]:
    selected = _selected_candidate(fit)
    return {
        "role": fit.role,
        "layer_index": fit.layer_index,
        "module_path": fit.module_path,
        "feature_width": fit.feature_width,
        "positive_rows": fit.positive_rows,
        "negative_rows": fit.negative_rows,
        "runtime_versions": dict(fit.runtime_versions),
        "candidate_set_sha256": fit.candidate_set_sha256,
        "selection_status": fit.selection_status,
        "selected_threshold": _binary64_value(fit.selected_threshold),
        "selected_confusion": (
            None
            if selected is None
            else {
                "adversarial_true_positives": selected.adversarial_true_positives,
                "adversarial_false_negatives": selected.adversarial_false_negatives,
                "clean_true_negatives": selected.clean_true_negatives,
                "clean_false_positives": selected.clean_false_positives,
                "clean_null_true_negatives": selected.clean_null_true_negatives,
                "clean_null_false_positives": selected.clean_null_false_positives,
                "eligible": selected.eligible,
            }
        ),
    }


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationDetectorResult:
    role: str
    layer_index: int
    module_path: str
    feature_width: int
    candidate_set_sha256: str
    selection_status: str
    selected_threshold: DiagnosticBinary64 | None
    selected_candidate: DiagnosticCalibrationCandidateResult | None


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationAnalysisArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    analysis_id: str
    created_at: str
    phase_subject_sha256: str
    status: str
    rule_ref: ArtifactRef
    dataset_ref: ArtifactRef
    fit_transcript_ref: ArtifactRef
    registration_ref: ArtifactRef
    reconciliation_ref: ArtifactRef
    outcome_access_ref: ArtifactRef
    detector_results: tuple[DiagnosticCalibrationDetectorResult, ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.analysis_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_CALIBRATION_ANALYSIS_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationDetectorBundleArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    bundle_id: str
    created_at: str
    phase_subject_sha256: str
    rule_ref: ArtifactRef
    dataset_ref: ArtifactRef
    fit_transcript_ref: ArtifactRef
    outcome_access_ref: ArtifactRef
    analysis_ref: ArtifactRef
    target_fit: DiagnosticCalibrationModelFit
    wrong_layer_fit: DiagnosticCalibrationModelFit
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.bundle_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_CALIBRATION_DETECTOR_BUNDLE_MEDIA_TYPE,
        )

    @property
    def model_fits(self) -> tuple[DiagnosticCalibrationModelFit, ...]:
        return (self.target_fit, self.wrong_layer_fit)


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationDispositionArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    disposition_id: str
    finalized_at: str
    status: str
    phase_subject_sha256: str
    rejection_reasons: tuple[str, ...]
    registration_ref: ArtifactRef
    reconciliation_ref: ArtifactRef
    rule_ref: ArtifactRef | None
    dataset_ref: ArtifactRef | None
    fit_transcript_ref: ArtifactRef | None
    outcome_access_ref: ArtifactRef | None
    analysis_ref: ArtifactRef | None
    bundle_ref: ArtifactRef | None
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.disposition_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_CALIBRATION_DISPOSITION_MEDIA_TYPE,
        )


def _result_carrier(fit: DiagnosticCalibrationModelFit) -> DiagnosticCalibrationDetectorResult:
    selected = _selected_candidate(fit)
    return DiagnosticCalibrationDetectorResult(
        role=fit.role,
        layer_index=fit.layer_index,
        module_path=fit.module_path,
        feature_width=fit.feature_width,
        candidate_set_sha256=fit.candidate_set_sha256,
        selection_status=fit.selection_status,
        selected_threshold=fit.selected_threshold,
        selected_candidate=selected,
    )


def _analysis_value(
    *,
    analysis_id: str,
    created_at: str,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> dict[str, Any]:
    fits = transcript.model_fits
    eligible = all(
        fit.selection_status == ELIGIBLE_THRESHOLD_SELECTED
        and _selected_candidate(fit) is not None
        for fit in fits
    )
    return {
        "schema_version": DIAGNOSTIC_CALIBRATION_ANALYSIS_SCHEMA,
        "analysis_id": analysis_id,
        "created_at": created_at,
        "phase_subject_sha256": registration.phase_subject_sha256,
        "status": (
            CALIBRATION_ANALYSIS_ELIGIBLE
            if eligible
            else CALIBRATION_ANALYSIS_INELIGIBLE
        ),
        "diagnostic_calibration_rule": _artifact_ref_value(rule.artifact_ref),
        "calibration_activation_dataset": _artifact_ref_value(dataset.artifact_ref),
        "calibration_fit_transcript": _artifact_ref_value(transcript.artifact_ref),
        "phase_registration": _artifact_ref_value(registration.artifact_ref),
        "phase_reconciliation": _artifact_ref_value(reconciliation.artifact_ref),
        "phase_outcome_access": _artifact_ref_value(outcome_access.artifact_ref),
        "fit_transcript_identity_sha256": transcript.payload[
            "fit_transcript_identity_sha256"
        ],
        "detector_results": [_fit_result_value(fit) for fit in fits],
        "scientific_correctness": "NOT_ESTABLISHED",
        "boundary": dict(_BOUNDARY),
    }


def _replay_analysis_dependencies(
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext | None,
    full_numeric_replay: bool,
) -> DiagnosticCalibrationFitTranscriptArtifact:
    replay_diagnostic_phase_outcome_access_projection(
        outcome_access,
        registration=registration,
        reconciliation=reconciliation,
    )
    if full_numeric_replay:
        if type(shared_plan_context) is not DiagnosticSharedPlanReplayContext:
            raise DiagnosticCalibrationValidationError(
                "full analysis replay requires the exact shared plan context"
            )
        exact_transcript = replay_diagnostic_calibration_fit_transcript(
            transcript,
            rule=rule,
            dataset=dataset,
            shared_plan_context=shared_plan_context,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )
    else:
        exact_transcript = replay_diagnostic_calibration_fit_transcript_projection(
            transcript,
            rule=rule,
            dataset=dataset,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )
    transcript = exact_transcript
    if (
        registration.phase_subject_sha256 != reconciliation.phase_subject_sha256
        or registration.phase_subject_sha256 != outcome_access.phase_subject_sha256
        or registration.phase_subject_sha256 != dataset.phase_subject_sha256
        or registration.phase_subject_sha256 != transcript.phase_subject_sha256
        or registration.calibration_rule_ref != rule.artifact_ref
        or transcript.rule_ref != rule.artifact_ref
        or transcript.dataset_ref != dataset.artifact_ref
        or transcript.registration_ref != registration.artifact_ref
        or transcript.reconciliation_ref != reconciliation.artifact_ref
        or transcript.outcome_access_ref != outcome_access.artifact_ref
    ):
        raise DiagnosticCalibrationValidationError(
            "analysis dependencies do not share one exact phase/rule/dataset/fit identity"
        )
    fits = transcript.model_fits
    if (
        type(fits) is not tuple
        or len(fits) != 2
        or tuple(item.role for item in fits)
        != tuple(DIAGNOSTIC_CALIBRATION_DETECTOR_ROLES)
        or fits[0].layer_index != 18
        or fits[0].module_path != "model.layers[18].mlp.down_proj"
        or fits[1].layer_index != 0
        or fits[1].module_path != "model.layers[0].mlp.down_proj"
    ):
        raise DiagnosticCalibrationValidationError(
            "fit transcript is not the exact target18 plus wrong0 detector family"
        )
    return exact_transcript


def _load_analysis(
    raw: bytes | bytearray | memoryview,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext | None,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    full_numeric_replay: bool,
) -> DiagnosticCalibrationAnalysisArtifact:
    transcript = _replay_analysis_dependencies(
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        shared_plan_context=shared_plan_context,
        full_numeric_replay=full_numeric_replay,
    )
    snapshot, obj = _canonical_object(raw, "diagnostic calibration analysis")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "analysis_id",
                "created_at",
                "phase_subject_sha256",
                "status",
                "diagnostic_calibration_rule",
                "calibration_activation_dataset",
                "calibration_fit_transcript",
                "phase_registration",
                "phase_reconciliation",
                "phase_outcome_access",
                "fit_transcript_identity_sha256",
                "detector_results",
                "scientific_correctness",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_CALIBRATION_ANALYSIS_SCHEMA:
            raise SchemaValidationError("wrong diagnostic calibration-analysis schema")
        analysis_id = expect_machine_id(obj["analysis_id"], "$.analysis_id")
        created_at = expect_timestamp(obj["created_at"], "$.created_at")
        expect_sha256(obj["phase_subject_sha256"], "$.phase_subject_sha256")
        status = expect_enum(
            obj["status"],
            {CALIBRATION_ANALYSIS_ELIGIBLE, CALIBRATION_ANALYSIS_INELIGIBLE},
            "$.status",
        )
        for key in (
            "diagnostic_calibration_rule",
            "calibration_activation_dataset",
            "calibration_fit_transcript",
            "phase_registration",
            "phase_reconciliation",
            "phase_outcome_access",
        ):
            parse_artifact_ref(obj[key], f"$.{key}")
        expect_sha256(
            obj["fit_transcript_identity_sha256"],
            "$.fit_transcript_identity_sha256",
        )
        results = expect_list(obj["detector_results"], "$.detector_results")
        if len(results) != 2:
            raise SchemaValidationError("analysis requires exactly two detector results")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationValidationError(str(exc)) from exc
    _require_boundary(obj["boundary"])
    expected = _analysis_value(
        analysis_id=analysis_id,
        created_at=created_at,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    if obj != expected or status != expected["status"]:
        raise DiagnosticCalibrationValidationError(
            "calibration analysis differs from the exact FitTranscript derivation"
        )
    if _time(created_at) <= max(
        _time(outcome_access.accessed_at),
        _time(dataset.created_at),
        _time(transcript.created_at),
    ):
        raise DiagnosticCalibrationValidationError(
            "calibration analysis must be created strictly after access/dataset/fit"
        )
    dependency_ids = {
        rule.rule_id,
        dataset.dataset_id,
        transcript.transcript_id,
        registration.registration_id,
        reconciliation.reconciliation_id,
        outcome_access.access_id,
    }
    for dependency in (
        rule,
        dataset,
        transcript,
        registration,
        reconciliation,
        outcome_access,
    ):
        dependency_ids.update(_artifact_ids_in_json(dependency.payload))
    if analysis_id in dependency_ids:
        raise DiagnosticCalibrationValidationError(
            "calibration analysis identifier collides with a dependency"
        )
    return DiagnosticCalibrationAnalysisArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        analysis_id=analysis_id,
        created_at=created_at,
        phase_subject_sha256=registration.phase_subject_sha256,
        status=status,
        rule_ref=rule.artifact_ref,
        dataset_ref=dataset.artifact_ref,
        fit_transcript_ref=transcript.artifact_ref,
        registration_ref=registration.artifact_ref,
        reconciliation_ref=reconciliation.artifact_ref,
        outcome_access_ref=outcome_access.artifact_ref,
        detector_results=tuple(_result_carrier(fit) for fit in transcript.model_fits),
        payload=freeze_json(obj),
    )


def build_diagnostic_calibration_analysis(
    *,
    analysis_id: str,
    created_at: str,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationAnalysisArtifact:
    try:
        analysis_id = expect_machine_id(analysis_id, "analysis_id")
        created_at = expect_timestamp(created_at, "created_at")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationValidationError(str(exc)) from exc
    raw = canonical_json_bytes(
        _analysis_value(
            analysis_id=analysis_id,
            created_at=created_at,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )
    )
    return _load_analysis(
        raw,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        full_numeric_replay=True,
    )


def load_diagnostic_calibration_analysis(
    raw: bytes | bytearray | memoryview,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationAnalysisArtifact:
    return _load_analysis(
        raw,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        full_numeric_replay=True,
    )


def replay_diagnostic_calibration_analysis_projection(
    analysis: DiagnosticCalibrationAnalysisArtifact,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationAnalysisArtifact:
    _require_exact_type(analysis, DiagnosticCalibrationAnalysisArtifact, "analysis")
    _require_artifact_storage(analysis, "analysis")
    if (
        any(
            type(getattr(analysis, name)) is not str
            for name in ("analysis_id", "created_at", "phase_subject_sha256", "status")
        )
        or any(
            type(getattr(analysis, name)) is not ArtifactRef
            for name in (
                "rule_ref",
                "dataset_ref",
                "fit_transcript_ref",
                "registration_ref",
                "reconciliation_ref",
                "outcome_access_ref",
            )
        )
        or type(analysis.detector_results) is not tuple
        or any(
            type(item) is not DiagnosticCalibrationDetectorResult
            for item in analysis.detector_results
        )
    ):
        raise DiagnosticCalibrationValidationError(
            "analysis projections must use exact immutable carrier types"
        )
    for name in (
        "rule_ref",
        "dataset_ref",
        "fit_transcript_ref",
        "registration_ref",
        "reconciliation_ref",
        "outcome_access_ref",
    ):
        _require_ref_projection_types(getattr(analysis, name), f"analysis.{name}")
    for index, result in enumerate(analysis.detector_results):
        _require_detector_result_projection_types(
            result, f"analysis.detector_results[{index}]"
        )
    exact = _load_analysis(
        analysis.raw_bytes,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        shared_plan_context=None,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        full_numeric_replay=False,
    )
    if exact != analysis:
        raise DiagnosticCalibrationValidationError(
            "analysis dataclass differs from exact raw/dependency projection"
        )
    return exact


def _bundle_value(
    *,
    bundle_id: str,
    created_at: str,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    analysis: DiagnosticCalibrationAnalysisArtifact,
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_CALIBRATION_DETECTOR_BUNDLE_SCHEMA,
        "bundle_id": bundle_id,
        "created_at": created_at,
        "phase_subject_sha256": analysis.phase_subject_sha256,
        "status": "EXACT_TWO_DETECTOR_CALIBRATION_BUNDLE_NONREPORTING",
        "diagnostic_calibration_rule": _artifact_ref_value(rule.artifact_ref),
        "calibration_activation_dataset": _artifact_ref_value(dataset.artifact_ref),
        "calibration_fit_transcript": _artifact_ref_value(transcript.artifact_ref),
        "phase_outcome_access": _artifact_ref_value(outcome_access.artifact_ref),
        "calibration_analysis": _artifact_ref_value(analysis.artifact_ref),
        "detector_order": list(DIAGNOSTIC_CALIBRATION_DETECTOR_ROLES),
        "model_fit_sha256s": {
            "target_layer18": canonical_sha256(
                transcript.payload["model_fits"]["target_layer18"]
            ),
            "wrong_layer0": canonical_sha256(
                transcript.payload["model_fits"]["wrong_layer0"]
            ),
        },
        "parameter_source": "EXACT_FROZEN_RUNTIME_FIT_TRANSCRIPT_ONLY",
        "scientific_correctness": "NOT_ESTABLISHED",
        "boundary": dict(_BOUNDARY),
    }


def _load_bundle(
    raw: bytes | bytearray | memoryview,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    analysis: DiagnosticCalibrationAnalysisArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext | None,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    full_numeric_replay: bool,
) -> DiagnosticCalibrationDetectorBundleArtifact:
    if full_numeric_replay:
        if type(shared_plan_context) is not DiagnosticSharedPlanReplayContext:
            raise DiagnosticCalibrationValidationError(
                "full bundle replay requires the exact shared plan context"
            )
        exact_analysis = load_diagnostic_calibration_analysis(
            analysis.raw_bytes,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            shared_plan_context=shared_plan_context,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )
    else:
        exact_analysis = replay_diagnostic_calibration_analysis_projection(
            analysis,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )
    analysis = exact_analysis
    transcript = replay_diagnostic_calibration_fit_transcript_projection(
        transcript,
        rule=rule,
        dataset=dataset,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    if analysis.status != CALIBRATION_ANALYSIS_ELIGIBLE:
        raise DiagnosticCalibrationValidationError(
            "detector bundle requires the exact eligible calibration analysis"
        )
    if any(_selected_candidate(fit) is None for fit in transcript.model_fits):
        raise DiagnosticCalibrationValidationError(
            "detector bundle requires eligible target18 and wrong0 fits"
        )
    snapshot, obj = _canonical_object(raw, "diagnostic calibration detector bundle")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "bundle_id",
                "created_at",
                "phase_subject_sha256",
                "status",
                "diagnostic_calibration_rule",
                "calibration_activation_dataset",
                "calibration_fit_transcript",
                "phase_outcome_access",
                "calibration_analysis",
                "detector_order",
                "model_fit_sha256s",
                "parameter_source",
                "scientific_correctness",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_CALIBRATION_DETECTOR_BUNDLE_SCHEMA:
            raise SchemaValidationError("wrong detector-bundle schema")
        bundle_id = expect_machine_id(obj["bundle_id"], "$.bundle_id")
        created_at = expect_timestamp(obj["created_at"], "$.created_at")
        expect_sha256(obj["phase_subject_sha256"], "$.phase_subject_sha256")
        for key in (
            "diagnostic_calibration_rule",
            "calibration_activation_dataset",
            "calibration_fit_transcript",
            "phase_outcome_access",
            "calibration_analysis",
        ):
            parse_artifact_ref(obj[key], f"$.{key}")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationValidationError(str(exc)) from exc
    _require_boundary(obj["boundary"])
    expected = _bundle_value(
        bundle_id=bundle_id,
        created_at=created_at,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        outcome_access=outcome_access,
        analysis=analysis,
    )
    if obj != expected:
        raise DiagnosticCalibrationValidationError(
            "detector bundle differs from exact eligible analysis/FitTranscript"
        )
    if _time(created_at) <= _time(analysis.created_at):
        raise DiagnosticCalibrationValidationError(
            "detector bundle must be created strictly after its analysis"
        )
    dependency_ids = {
        rule.rule_id,
        dataset.dataset_id,
        transcript.transcript_id,
        outcome_access.access_id,
        analysis.analysis_id,
    }
    for dependency in (rule, dataset, transcript, outcome_access, analysis):
        dependency_ids.update(_artifact_ids_in_json(dependency.payload))
    if bundle_id in dependency_ids:
        raise DiagnosticCalibrationValidationError(
            "detector bundle identifier collides with a dependency"
        )
    return DiagnosticCalibrationDetectorBundleArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        bundle_id=bundle_id,
        created_at=created_at,
        phase_subject_sha256=analysis.phase_subject_sha256,
        rule_ref=rule.artifact_ref,
        dataset_ref=dataset.artifact_ref,
        fit_transcript_ref=transcript.artifact_ref,
        outcome_access_ref=outcome_access.artifact_ref,
        analysis_ref=analysis.artifact_ref,
        target_fit=transcript.target_fit,
        wrong_layer_fit=transcript.wrong_layer_fit,
        payload=freeze_json(obj),
    )


def build_diagnostic_calibration_detector_bundle(
    *,
    bundle_id: str,
    created_at: str,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    analysis: DiagnosticCalibrationAnalysisArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationDetectorBundleArtifact:
    try:
        bundle_id = expect_machine_id(bundle_id, "bundle_id")
        created_at = expect_timestamp(created_at, "created_at")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationValidationError(str(exc)) from exc
    raw = canonical_json_bytes(
        _bundle_value(
            bundle_id=bundle_id,
            created_at=created_at,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            outcome_access=outcome_access,
            analysis=analysis,
        )
    )
    return _load_bundle(
        raw,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        analysis=analysis,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        full_numeric_replay=True,
    )


def load_diagnostic_calibration_detector_bundle(
    raw: bytes | bytearray | memoryview,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    analysis: DiagnosticCalibrationAnalysisArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationDetectorBundleArtifact:
    return _load_bundle(
        raw,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        analysis=analysis,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        full_numeric_replay=True,
    )


def replay_diagnostic_calibration_detector_bundle_projection(
    bundle: DiagnosticCalibrationDetectorBundleArtifact,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    analysis: DiagnosticCalibrationAnalysisArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationDetectorBundleArtifact:
    _require_exact_type(
        bundle, DiagnosticCalibrationDetectorBundleArtifact, "detector_bundle"
    )
    _require_artifact_storage(bundle, "detector_bundle")
    if (
        any(
            type(getattr(bundle, name)) is not str
            for name in ("bundle_id", "created_at", "phase_subject_sha256")
        )
        or any(
            type(getattr(bundle, name)) is not ArtifactRef
            for name in (
                "rule_ref",
                "dataset_ref",
                "fit_transcript_ref",
                "outcome_access_ref",
                "analysis_ref",
            )
        )
        or type(bundle.target_fit) is not DiagnosticCalibrationModelFit
        or type(bundle.wrong_layer_fit) is not DiagnosticCalibrationModelFit
    ):
        raise DiagnosticCalibrationValidationError(
            "detector-bundle projections must use exact immutable carrier types"
        )
    for name in (
        "rule_ref",
        "dataset_ref",
        "fit_transcript_ref",
        "outcome_access_ref",
        "analysis_ref",
    ):
        _require_ref_projection_types(getattr(bundle, name), f"bundle.{name}")
    _require_model_fit_projection_types(bundle.target_fit, "bundle.target_fit")
    _require_model_fit_projection_types(bundle.wrong_layer_fit, "bundle.wrong_layer_fit")
    exact = _load_bundle(
        bundle.raw_bytes,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        analysis=analysis,
        shared_plan_context=None,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        full_numeric_replay=False,
    )
    if exact != bundle:
        raise DiagnosticCalibrationValidationError(
            "detector bundle dataclass differs from exact raw/dependency projection"
        )
    return exact


def _require_candidate_projection_types(
    value: DiagnosticCalibrationCandidateResult, path: str
) -> None:
    _require_exact_type(value, DiagnosticCalibrationCandidateResult, path)
    _require_exact_type(value.threshold, DiagnosticBinary64, f"{path}.threshold")
    _require_exact_type(
        value.balanced_accuracy, DiagnosticBinary64, f"{path}.balanced_accuracy"
    )
    if (
        type(value.predictions) is not tuple
        or len(value.predictions) != 480
        or any(type(item) is not int or item not in (0, 1) for item in value.predictions)
        or any(
            type(getattr(value, name)) is not int
            for name in (
                "adversarial_true_positives",
                "adversarial_false_negatives",
                "clean_true_negatives",
                "clean_false_positives",
                "clean_null_true_negatives",
                "clean_null_false_positives",
            )
        )
        or type(value.eligible) is not bool
    ):
        raise DiagnosticCalibrationValidationError(
            f"{path} projections must use exact immutable scalar/tuple types"
        )
    _require_binary64_projection_types(value.threshold, f"{path}.threshold")
    _require_binary64_projection_types(
        value.balanced_accuracy, f"{path}.balanced_accuracy"
    )


def _require_model_fit_projection_types(
    value: DiagnosticCalibrationModelFit, path: str
) -> None:
    _require_exact_type(value, DiagnosticCalibrationModelFit, path)
    if (
        any(
            type(getattr(value, name)) is not str
            for name in (
                "role",
                "module_path",
                "candidate_set_sha256",
                "selection_status",
            )
        )
        or any(
            type(getattr(value, name)) is not int
            for name in (
                "layer_index",
                "feature_width",
                "positive_rows",
                "negative_rows",
                "positive_class_index",
                "iterations",
            )
        )
        or type(value.runtime_versions) is not _MAPPING_PROXY_TYPE
        or any(
            type(key) is not str or type(item) is not str
            for key, item in value.runtime_versions.items()
        )
        or any(
            type(getattr(value, name)) is not bytes
            for name in (
                "scaler_mean_bytes",
                "scaler_scale_bytes",
                "coefficient_bytes",
            )
        )
        or type(value.classes) is not tuple
        or len(value.classes) != 2
        or any(type(item) is not int for item in value.classes)
        or type(value.scores) is not tuple
        or any(type(item) is not DiagnosticBinary64 for item in value.scores)
        or type(value.candidates) is not tuple
        or any(
            type(item) is not DiagnosticCalibrationCandidateResult
            for item in value.candidates
        )
        or (
            value.selected_threshold is not None
            and type(value.selected_threshold) is not DiagnosticBinary64
        )
        or (
            value.selected_predictions is not None
            and (
                type(value.selected_predictions) is not tuple
                or any(
                    type(item) is not int or item not in (0, 1)
                    for item in value.selected_predictions
                )
            )
        )
    ):
        raise DiagnosticCalibrationValidationError(
            f"{path} projections must use exact immutable carrier types"
        )
    _require_binary64_projection_types(value.intercept, f"{path}.intercept")
    for index, score in enumerate(value.scores):
        _require_binary64_projection_types(score, f"{path}.scores[{index}]")
    for index, candidate in enumerate(value.candidates):
        _require_candidate_projection_types(candidate, f"{path}.candidates[{index}]")
    if value.selected_threshold is not None:
        _require_binary64_projection_types(
            value.selected_threshold, f"{path}.selected_threshold"
        )


def _require_detector_result_projection_types(
    value: DiagnosticCalibrationDetectorResult, path: str
) -> None:
    _require_exact_type(value, DiagnosticCalibrationDetectorResult, path)
    if (
        any(
            type(getattr(value, name)) is not str
            for name in (
                "role",
                "module_path",
                "candidate_set_sha256",
                "selection_status",
            )
        )
        or type(value.layer_index) is not int
        or type(value.feature_width) is not int
        or (
            value.selected_threshold is not None
            and type(value.selected_threshold) is not DiagnosticBinary64
        )
        or (
            value.selected_candidate is not None
            and type(value.selected_candidate) is not DiagnosticCalibrationCandidateResult
        )
    ):
        raise DiagnosticCalibrationValidationError(
            f"{path} projections must use exact immutable carrier types"
        )
    if value.selected_threshold is not None:
        _require_binary64_projection_types(
            value.selected_threshold, f"{path}.selected_threshold"
        )
    if value.selected_candidate is not None:
        _require_candidate_projection_types(
            value.selected_candidate, f"{path}.selected_candidate"
        )


def _optional_artifact_ref_value(reference: ArtifactRef | None) -> dict[str, Any] | None:
    return None if reference is None else _artifact_ref_value(reference)


def _disposition_id(registration: DiagnosticPhaseRegistrationArtifact) -> str:
    return (
        "diagnostic-calibration-disposition-"
        f"{registration.phase_subject_sha256[:32]}"
    )


def _terminal_dependency_mode(
    *,
    rule: DiagnosticCalibrationRuleArtifact | None,
    dataset: DiagnosticCalibrationActivationDatasetArtifact | None,
    transcript: DiagnosticCalibrationFitTranscriptArtifact | None,
    shared_plan_context: DiagnosticSharedPlanReplayContext | None,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None,
    analysis: DiagnosticCalibrationAnalysisArtifact | None,
    bundle: DiagnosticCalibrationDetectorBundleArtifact | None,
    full_numeric_replay: bool,
) -> tuple[str, tuple[str, ...], str]:
    replay_diagnostic_phase_registration_projection(registration)
    replay_diagnostic_phase_store_binding_projection(registration.store_binding)
    replay_diagnostic_phase_reconciliation_projection(
        reconciliation, registration=registration
    )
    if reconciliation.phase_subject_sha256 != registration.phase_subject_sha256:
        raise DiagnosticCalibrationValidationError(
            "disposition reconciliation does not belong to its registration"
        )

    later = (
        rule,
        dataset,
        transcript,
        shared_plan_context,
        outcome_access,
        analysis,
        bundle,
    )
    if reconciliation.status == PHASE_RECONCILED_REJECTED:
        if any(item is not None for item in later):
            raise DiagnosticCalibrationValidationError(
                "early rejected disposition must keep rule/dataset/fit/access/analysis/bundle null"
            )
        if (
            not reconciliation.rejection_reasons
            or len(set(reconciliation.rejection_reasons))
            != len(reconciliation.rejection_reasons)
            or not set(reconciliation.rejection_reasons).issubset(
                _EARLY_REJECTION_REASONS
            )
        ):
            raise DiagnosticCalibrationValidationError(
                "early rejection reasons must be exact closed lifecycle/integrity/window/output reasons"
            )
        return (
            CALIBRATION_REJECTED_NONREPORTING,
            reconciliation.rejection_reasons,
            "EARLY_PHASE_CLOSURE_WITHOUT_OUTCOME_ACCESS",
        )

    if reconciliation.status != PHASE_RECONCILED_CLEAN:
        raise DiagnosticCalibrationValidationError(
            "terminal disposition requires an exact clean or rejected phase seal"
        )
    required_post_access = (rule, dataset, transcript, outcome_access, analysis)
    if any(item is None for item in required_post_access) or (
        full_numeric_replay and shared_plan_context is None
    ):
        raise DiagnosticCalibrationValidationError(
            "post-access disposition requires exact rule/dataset/fit/access/analysis and full-replay context"
        )
    assert rule is not None
    assert dataset is not None
    assert transcript is not None
    assert outcome_access is not None
    assert analysis is not None
    replay_diagnostic_phase_outcome_access_projection(
        outcome_access,
        registration=registration,
        reconciliation=reconciliation,
    )
    transcript = replay_diagnostic_calibration_fit_transcript_projection(
        transcript,
        rule=rule,
        dataset=dataset,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    analysis = replay_diagnostic_calibration_analysis_projection(
        analysis,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    if bundle is not None:
        bundle = replay_diagnostic_calibration_detector_bundle_projection(
            bundle,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            analysis=analysis,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )
    if bundle is None:
        if full_numeric_replay:
            assert shared_plan_context is not None
            exact_analysis = load_diagnostic_calibration_analysis(
                analysis.raw_bytes,
                rule=rule,
                dataset=dataset,
                transcript=transcript,
                shared_plan_context=shared_plan_context,
                registration=registration,
                reconciliation=reconciliation,
                outcome_access=outcome_access,
            )
        else:
            exact_analysis = replay_diagnostic_calibration_analysis_projection(
                analysis,
                rule=rule,
                dataset=dataset,
                transcript=transcript,
                registration=registration,
                reconciliation=reconciliation,
                outcome_access=outcome_access,
            )
        if exact_analysis != analysis:
            raise DiagnosticCalibrationValidationError(
                "post-access analysis differs from exact dependency replay"
            )
        if analysis.status != CALIBRATION_ANALYSIS_INELIGIBLE or not any(
            fit.selection_status == NO_ELIGIBLE_THRESHOLD
            for fit in transcript.model_fits
        ):
            raise DiagnosticCalibrationValidationError(
                "null detector bundle is allowed only for an exact no-eligible-threshold fit"
            )
        return (
            CALIBRATION_REJECTED_NONREPORTING,
            (_POST_ACCESS_REJECTION_REASON,),
            "POST_ACCESS_NO_ELIGIBLE_THRESHOLD",
        )

    if full_numeric_replay:
        assert shared_plan_context is not None
        exact_bundle = load_diagnostic_calibration_detector_bundle(
            bundle.raw_bytes,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            analysis=analysis,
            shared_plan_context=shared_plan_context,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )
    else:
        exact_bundle = replay_diagnostic_calibration_detector_bundle_projection(
            bundle,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            analysis=analysis,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )
    if (
        exact_bundle != bundle
        or analysis.status != CALIBRATION_ANALYSIS_ELIGIBLE
        or any(
            fit.selection_status != ELIGIBLE_THRESHOLD_SELECTED
            or _selected_candidate(fit) is None
            for fit in transcript.model_fits
        )
    ):
        raise DiagnosticCalibrationValidationError(
            "freeze requires exact independently fit eligible target18 and wrong0 detectors"
        )
    return (
        CALIBRATION_FROZEN_NONREPORTING,
        (),
        "EXACT_ELIGIBLE_TARGET18_WRONG0_FREEZE",
    )


def _disposition_value(
    *,
    finalized_at: str,
    status: str,
    rejection_reasons: tuple[str, ...],
    terminal_path: str,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    rule: DiagnosticCalibrationRuleArtifact | None,
    dataset: DiagnosticCalibrationActivationDatasetArtifact | None,
    transcript: DiagnosticCalibrationFitTranscriptArtifact | None,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None,
    analysis: DiagnosticCalibrationAnalysisArtifact | None,
    bundle: DiagnosticCalibrationDetectorBundleArtifact | None,
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_CALIBRATION_DISPOSITION_SCHEMA,
        "disposition_id": _disposition_id(registration),
        "finalized_at": finalized_at,
        "phase_subject_sha256": registration.phase_subject_sha256,
        "status": status,
        "terminal_path": terminal_path,
        "rejection_reasons": list(rejection_reasons),
        "phase_store_binding": _artifact_ref_value(
            registration.store_binding.artifact_ref
        ),
        "phase_registration": _artifact_ref_value(registration.artifact_ref),
        "phase_reconciliation": _artifact_ref_value(reconciliation.artifact_ref),
        "diagnostic_calibration_rule": _optional_artifact_ref_value(
            None if rule is None else rule.artifact_ref
        ),
        "calibration_activation_dataset": _optional_artifact_ref_value(
            None if dataset is None else dataset.artifact_ref
        ),
        "calibration_fit_transcript": _optional_artifact_ref_value(
            None if transcript is None else transcript.artifact_ref
        ),
        "phase_outcome_access": _optional_artifact_ref_value(
            None if outcome_access is None else outcome_access.artifact_ref
        ),
        "calibration_analysis": _optional_artifact_ref_value(
            None if analysis is None else analysis.artifact_ref
        ),
        "calibration_detector_bundle": _optional_artifact_ref_value(
            None if bundle is None else bundle.artifact_ref
        ),
        "terminality": {
            "slot": "CREATE_ONCE_SAME_FILE_SQLITE_PHASE_SUBJECT",
            "idempotence": "EXACT_BYTES_ONLY",
            "store_identity": (
                "BINDING_REPLAY_AND_OPEN_CONNECTION_FILE_PARENT_SQLITE_ID_"
                "RECHECKED_BEFORE_AFTER_TRANSACTION"
            ),
            "reporting": "FORBIDDEN",
        },
        "scientific_correctness": "NOT_ESTABLISHED",
        "boundary": dict(_BOUNDARY),
    }


def _parse_optional_ref(value: Any, path: str) -> ArtifactRef | None:
    if value is None:
        return None
    try:
        return parse_artifact_ref(value, path)
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationValidationError(str(exc)) from exc


def _parse_disposition_rejection_reasons(
    value: Any, *, status: str
) -> tuple[str, ...]:
    try:
        reasons = tuple(
            expect_enum(
                item,
                {*_EARLY_REJECTION_REASONS, _POST_ACCESS_REJECTION_REASON},
                f"$.rejection_reasons[{index}]",
            )
            for index, item in enumerate(
                expect_list(value, "$.rejection_reasons", nonempty=False)
            )
        )
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationValidationError(str(exc)) from exc
    if status == CALIBRATION_FROZEN_NONREPORTING:
        if reasons:
            raise DiagnosticCalibrationValidationError(
                "frozen disposition must keep rejection reasons empty"
            )
    elif status == CALIBRATION_REJECTED_NONREPORTING:
        if not reasons:
            raise DiagnosticCalibrationValidationError(
                "rejected disposition requires an exact nonempty rejection reason"
            )
    else:
        raise DiagnosticCalibrationValidationError(
            "disposition reason parsing requires an exact terminal status"
        )
    return reasons


def _load_disposition(
    raw: bytes | bytearray | memoryview,
    *,
    rule: DiagnosticCalibrationRuleArtifact | None,
    dataset: DiagnosticCalibrationActivationDatasetArtifact | None,
    transcript: DiagnosticCalibrationFitTranscriptArtifact | None,
    shared_plan_context: DiagnosticSharedPlanReplayContext | None,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None,
    analysis: DiagnosticCalibrationAnalysisArtifact | None,
    bundle: DiagnosticCalibrationDetectorBundleArtifact | None,
    full_numeric_replay: bool,
) -> DiagnosticCalibrationDispositionArtifact:
    status, rejection_reasons, terminal_path = _terminal_dependency_mode(
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        analysis=analysis,
        bundle=bundle,
        full_numeric_replay=full_numeric_replay,
    )
    snapshot, obj = _canonical_object(raw, "diagnostic calibration disposition")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "disposition_id",
                "finalized_at",
                "phase_subject_sha256",
                "status",
                "terminal_path",
                "rejection_reasons",
                "phase_store_binding",
                "phase_registration",
                "phase_reconciliation",
                "diagnostic_calibration_rule",
                "calibration_activation_dataset",
                "calibration_fit_transcript",
                "phase_outcome_access",
                "calibration_analysis",
                "calibration_detector_bundle",
                "terminality",
                "scientific_correctness",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_CALIBRATION_DISPOSITION_SCHEMA:
            raise SchemaValidationError("wrong diagnostic calibration-disposition schema")
        disposition_id = expect_machine_id(obj["disposition_id"], "$.disposition_id")
        finalized_at = expect_timestamp(obj["finalized_at"], "$.finalized_at")
        expect_sha256(obj["phase_subject_sha256"], "$.phase_subject_sha256")
        parsed_status = expect_enum(
            obj["status"],
            {CALIBRATION_FROZEN_NONREPORTING, CALIBRATION_REJECTED_NONREPORTING},
            "$.status",
        )
        reasons = _parse_disposition_rejection_reasons(
            obj["rejection_reasons"], status=parsed_status
        )
        store_ref = parse_artifact_ref(
            obj["phase_store_binding"], "$.phase_store_binding"
        )
        registration_ref = parse_artifact_ref(
            obj["phase_registration"], "$.phase_registration"
        )
        reconciliation_ref = parse_artifact_ref(
            obj["phase_reconciliation"], "$.phase_reconciliation"
        )
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationValidationError(str(exc)) from exc
    rule_ref = _parse_optional_ref(
        obj["diagnostic_calibration_rule"], "$.diagnostic_calibration_rule"
    )
    dataset_ref = _parse_optional_ref(
        obj["calibration_activation_dataset"], "$.calibration_activation_dataset"
    )
    transcript_ref = _parse_optional_ref(
        obj["calibration_fit_transcript"], "$.calibration_fit_transcript"
    )
    access_ref = _parse_optional_ref(
        obj["phase_outcome_access"], "$.phase_outcome_access"
    )
    analysis_ref = _parse_optional_ref(
        obj["calibration_analysis"], "$.calibration_analysis"
    )
    bundle_ref = _parse_optional_ref(
        obj["calibration_detector_bundle"], "$.calibration_detector_bundle"
    )
    _require_boundary(obj["boundary"])
    expected = _disposition_value(
        finalized_at=finalized_at,
        status=status,
        rejection_reasons=rejection_reasons,
        terminal_path=terminal_path,
        registration=registration,
        reconciliation=reconciliation,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        outcome_access=outcome_access,
        analysis=analysis,
        bundle=bundle,
    )
    if (
        obj != expected
        or disposition_id != _disposition_id(registration)
        or parsed_status != status
        or reasons != rejection_reasons
        or store_ref != registration.store_binding.artifact_ref
        or registration_ref != registration.artifact_ref
        or reconciliation_ref != reconciliation.artifact_ref
    ):
        raise DiagnosticCalibrationValidationError(
            "terminal disposition differs from exact phase/fit dependency derivation"
        )
    dependency_ids = {
        registration.store_binding.binding_id,
        registration.registration_id,
        reconciliation.reconciliation_id,
        *(
            ()
            if rule is None
            else (rule.rule_id,)
        ),
        *(
            ()
            if dataset is None
            else (dataset.dataset_id,)
        ),
        *(
            ()
            if transcript is None
            else (transcript.transcript_id,)
        ),
        *(
            ()
            if outcome_access is None
            else (outcome_access.access_id,)
        ),
        *(
            ()
            if analysis is None
            else (analysis.analysis_id,)
        ),
        *(
            ()
            if bundle is None
            else (bundle.bundle_id,)
        ),
    }
    for dependency in (
        registration.store_binding,
        registration,
        reconciliation,
        rule,
        dataset,
        transcript,
        outcome_access,
        analysis,
        bundle,
    ):
        if dependency is not None:
            dependency_ids.update(_artifact_ids_in_json(dependency.payload))
    if disposition_id in dependency_ids:
        raise DiagnosticCalibrationValidationError(
            "terminal disposition identifier collides with a dependency"
        )
    predecessor_time = (
        reconciliation.closed_at
        if analysis is None
        else (analysis.created_at if bundle is None else bundle.created_at)
    )
    if _time(finalized_at) <= _time(predecessor_time):
        raise DiagnosticCalibrationValidationError(
            "terminal disposition must be finalized strictly after its last dependency"
        )
    return DiagnosticCalibrationDispositionArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        disposition_id=disposition_id,
        finalized_at=finalized_at,
        status=status,
        phase_subject_sha256=registration.phase_subject_sha256,
        rejection_reasons=rejection_reasons,
        registration_ref=registration.artifact_ref,
        reconciliation_ref=reconciliation.artifact_ref,
        rule_ref=rule_ref,
        dataset_ref=dataset_ref,
        fit_transcript_ref=transcript_ref,
        outcome_access_ref=access_ref,
        analysis_ref=analysis_ref,
        bundle_ref=bundle_ref,
        payload=freeze_json(obj),
    )


def load_diagnostic_calibration_disposition(
    raw: bytes | bytearray | memoryview,
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    rule: DiagnosticCalibrationRuleArtifact | None = None,
    dataset: DiagnosticCalibrationActivationDatasetArtifact | None = None,
    transcript: DiagnosticCalibrationFitTranscriptArtifact | None = None,
    shared_plan_context: DiagnosticSharedPlanReplayContext | None = None,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None = None,
    analysis: DiagnosticCalibrationAnalysisArtifact | None = None,
    bundle: DiagnosticCalibrationDetectorBundleArtifact | None = None,
) -> DiagnosticCalibrationDispositionArtifact:
    """Strict-load a terminal carrier, including an independent locked refit when used."""

    return _load_disposition(
        raw,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        analysis=analysis,
        bundle=bundle,
        full_numeric_replay=True,
    )


def _require_disposition_projection_types(
    disposition: DiagnosticCalibrationDispositionArtifact,
) -> None:
    _require_exact_type(
        disposition, DiagnosticCalibrationDispositionArtifact, "disposition"
    )
    _require_artifact_storage(disposition, "disposition")
    if (
        any(
            type(getattr(disposition, name)) is not str
            for name in (
                "disposition_id",
                "finalized_at",
                "status",
                "phase_subject_sha256",
            )
        )
        or type(disposition.rejection_reasons) is not tuple
        or any(type(item) is not str for item in disposition.rejection_reasons)
        or type(disposition.registration_ref) is not ArtifactRef
        or type(disposition.reconciliation_ref) is not ArtifactRef
    ):
        raise DiagnosticCalibrationValidationError(
            "disposition projections must use exact immutable carrier types"
        )
    for name in (
        "rule_ref",
        "dataset_ref",
        "fit_transcript_ref",
        "outcome_access_ref",
        "analysis_ref",
        "bundle_ref",
    ):
        value = getattr(disposition, name)
        if value is not None and type(value) is not ArtifactRef:
            raise DiagnosticCalibrationValidationError(
                f"disposition.{name} must be an exact ArtifactRef or null"
            )
        if value is not None:
            _require_ref_projection_types(value, f"disposition.{name}")
    _require_ref_projection_types(
        disposition.registration_ref, "disposition.registration_ref"
    )
    _require_ref_projection_types(
        disposition.reconciliation_ref, "disposition.reconciliation_ref"
    )


def replay_diagnostic_calibration_disposition_projection(
    disposition: DiagnosticCalibrationDispositionArtifact,
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    rule: DiagnosticCalibrationRuleArtifact | None = None,
    dataset: DiagnosticCalibrationActivationDatasetArtifact | None = None,
    transcript: DiagnosticCalibrationFitTranscriptArtifact | None = None,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None = None,
    analysis: DiagnosticCalibrationAnalysisArtifact | None = None,
    bundle: DiagnosticCalibrationDetectorBundleArtifact | None = None,
) -> DiagnosticCalibrationDispositionArtifact:
    """Cheaply reject every raw/dataclass/dependency replacement forgery."""

    _require_disposition_projection_types(disposition)
    exact = _load_disposition(
        disposition.raw_bytes,
        rule=rule,
        dataset=dataset,
        transcript=transcript,
        shared_plan_context=None,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        analysis=analysis,
        bundle=bundle,
        full_numeric_replay=False,
    )
    if exact != disposition:
        raise DiagnosticCalibrationValidationError(
            "disposition dataclass differs from exact raw/dependency projection"
        )
    return exact


_CREATE_DISPOSITIONS_TABLE = """
CREATE TABLE diagnostic_calibration_dispositions (
    phase_subject_sha256 TEXT PRIMARY KEY,
    store_binding_sha256 TEXT NOT NULL,
    registration_sha256 TEXT NOT NULL,
    reconciliation_sha256 TEXT NOT NULL,
    rule_sha256 TEXT,
    dataset_sha256 TEXT,
    fit_transcript_sha256 TEXT,
    outcome_access_sha256 TEXT,
    analysis_sha256 TEXT,
    bundle_sha256 TEXT,
    disposition_sha256 TEXT NOT NULL,
    disposition_raw BLOB NOT NULL,
    status TEXT NOT NULL,
    finalized_at TEXT NOT NULL,
    CHECK (length(phase_subject_sha256) = 64),
    CHECK (length(store_binding_sha256) = 64),
    CHECK (length(registration_sha256) = 64),
    CHECK (length(reconciliation_sha256) = 64),
    CHECK (length(disposition_sha256) = 64),
    CHECK (status IN (
        'CALIBRATION_FROZEN_NONREPORTING',
        'CALIBRATION_REJECTED_NONREPORTING'
    )),
    CHECK (
        (status = 'CALIBRATION_FROZEN_NONREPORTING'
            AND rule_sha256 IS NOT NULL
            AND dataset_sha256 IS NOT NULL
            AND fit_transcript_sha256 IS NOT NULL
            AND outcome_access_sha256 IS NOT NULL
            AND analysis_sha256 IS NOT NULL
            AND bundle_sha256 IS NOT NULL)
        OR
        (status = 'CALIBRATION_REJECTED_NONREPORTING'
            AND bundle_sha256 IS NULL
            AND (
                (rule_sha256 IS NULL
                    AND dataset_sha256 IS NULL
                    AND fit_transcript_sha256 IS NULL
                    AND outcome_access_sha256 IS NULL
                    AND analysis_sha256 IS NULL)
                OR
                (rule_sha256 IS NOT NULL
                    AND dataset_sha256 IS NOT NULL
                    AND fit_transcript_sha256 IS NOT NULL
                    AND outcome_access_sha256 IS NOT NULL
                    AND analysis_sha256 IS NOT NULL)
            ))
    ),
    FOREIGN KEY (phase_subject_sha256)
        REFERENCES diagnostic_phases(phase_subject_sha256)
) STRICT
"""

_CREATE_DISPOSITIONS_UPDATE_GUARD = """
CREATE TRIGGER diagnostic_calibration_dispositions_no_update
BEFORE UPDATE ON diagnostic_calibration_dispositions
BEGIN
    SELECT RAISE(ABORT, 'diagnostic calibration disposition is immutable');
END
"""

_CREATE_DISPOSITIONS_DELETE_GUARD = """
CREATE TRIGGER diagnostic_calibration_dispositions_no_delete
BEFORE DELETE ON diagnostic_calibration_dispositions
BEGIN
    SELECT RAISE(ABORT, 'diagnostic calibration disposition is permanent');
END
"""

_DISPOSITION_SCHEMA_SQL = {
    "sqlite_autoindex_diagnostic_calibration_dispositions_1": (
        "index",
        None,
    ),
    "diagnostic_calibration_dispositions": (
        "table",
        _CREATE_DISPOSITIONS_TABLE,
    ),
    "diagnostic_calibration_dispositions_no_update": (
        "trigger",
        _CREATE_DISPOSITIONS_UPDATE_GUARD,
    ),
    "diagnostic_calibration_dispositions_no_delete": (
        "trigger",
        _CREATE_DISPOSITIONS_DELETE_GUARD,
    ),
}


def _normalized_sql(value: str) -> str:
    return " ".join(value.split())


def _verify_bound_connection_identity(
    connection: sqlite3.Connection,
    binding: DiagnosticPhaseStoreBindingArtifact,
) -> None:
    database_rows = tuple(
        row for row in connection.execute("PRAGMA database_list") if row[1] == "main"
    )
    if len(database_rows) != 1 or type(database_rows[0][2]) is not str:
        raise DiagnosticCalibrationIntegrityError(
            "SQLite connection does not expose exactly one main database path"
        )
    connected_path = str(Path(database_rows[0][2]).resolve())
    target = Path(binding.canonical_path)
    try:
        file_stat = target.lstat()
        parent_stat = target.parent.stat()
    except OSError as exc:
        raise DiagnosticCalibrationIntegrityError(
            f"canonical disposition store identity cannot be read: {exc}"
        ) from exc
    reparse = bool(
        getattr(file_stat, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )
    if (
        connected_path != binding.canonical_path
        or not stat.S_ISREG(file_stat.st_mode)
        or target.is_symlink()
        or target.parent.is_symlink()
        or reparse
        or int(file_stat.st_nlink) != 1
        or int(file_stat.st_dev) != binding.file_device
        or int(file_stat.st_ino) != binding.file_inode
        or int(parent_stat.st_dev) != binding.parent_device
        or int(parent_stat.st_ino) != binding.parent_inode
    ):
        raise DiagnosticCalibrationIntegrityError(
            "opened SQLite connection/path no longer matches the exact canonical store binding"
        )
    sqlite_identity = binding.payload["sqlite_identity"]
    if (
        connection.execute("PRAGMA application_id").fetchone()[0]
        != sqlite_identity["application_id"]
        or connection.execute("PRAGMA user_version").fetchone()[0]
        != sqlite_identity["user_version"]
    ):
        raise DiagnosticCalibrationIntegrityError(
            "opened SQLite connection lost its bound application/schema identity"
        )


def _disposition_connection(
    binding: DiagnosticPhaseStoreBindingArtifact,
) -> sqlite3.Connection:
    connection = sqlite3.connect(
        binding.canonical_path, timeout=30.0, isolation_level=None
    )
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    if (
        str(connection.execute("PRAGMA journal_mode").fetchone()[0]).upper()
        != "WAL"
        or connection.execute("PRAGMA synchronous").fetchone()[0] != 2
        or connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1
    ):
        connection.close()
        raise DiagnosticCalibrationIntegrityError(
            "canonical phase database lost WAL/FULL/foreign-key enforcement"
        )
    try:
        _verify_bound_connection_identity(connection, binding)
    except Exception:
        connection.close()
        raise
    return connection


def _verify_disposition_schema(connection: sqlite3.Connection) -> None:
    rows = tuple(
        connection.execute(
            """
            SELECT type, name, sql
            FROM sqlite_master
            WHERE name='diagnostic_calibration_dispositions'
               OR tbl_name='diagnostic_calibration_dispositions'
            ORDER BY name
            """
        )
    )
    if len(rows) != len(_DISPOSITION_SCHEMA_SQL):
        raise DiagnosticCalibrationIntegrityError(
            "disposition table/index/immutability-trigger inventory drifted"
        )
    for object_type, name, sql in rows:
        if name not in _DISPOSITION_SCHEMA_SQL:
            raise DiagnosticCalibrationIntegrityError(
                f"disposition SQLite schema acquired unexpected object {name}"
            )
        expected_type, expected_sql = _DISPOSITION_SCHEMA_SQL[name]
        sql_matches = (
            sql is None
            if expected_sql is None
            else type(sql) is str
            and _normalized_sql(sql) == _normalized_sql(expected_sql)
        )
        if object_type != expected_type or not sql_matches:
            raise DiagnosticCalibrationIntegrityError(
                f"disposition SQLite schema object {name} drifted"
            )


def _phase_row(
    connection: sqlite3.Connection,
    registration: DiagnosticPhaseRegistrationArtifact,
) -> tuple[Any, ...]:
    rows = tuple(
        connection.execute(
            """
            SELECT phase_subject_sha256, tenant_id, registration_sha256,
                   registration_raw, state, reconciliation_sha256,
                   reconciliation_raw, outcome_access_sha256, outcome_access_raw
            FROM diagnostic_phases
            """
        )
    )
    if len(rows) != 1:
        raise DiagnosticCalibrationIntegrityError(
            "canonical database must retain exactly one phase row"
        )
    row = rows[0]
    if (
        row[0] != registration.phase_subject_sha256
        or row[1] != registration.tenant_id
        or row[2] != registration.sha256
        or bytes(row[3]) != registration.raw_bytes
    ):
        raise DiagnosticCalibrationIntegrityError(
            "canonical database phase registration bytes drifted"
        )
    return row


def _verify_terminal_phase_row(
    connection: sqlite3.Connection,
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None,
) -> None:
    row = _phase_row(connection, registration)
    if (
        row[5] != reconciliation.sha256
        or row[6] is None
        or bytes(row[6]) != reconciliation.raw_bytes
    ):
        raise DiagnosticCalibrationIntegrityError(
            "canonical database reconciliation bytes drifted"
        )
    access_rows = tuple(
        connection.execute(
            """
            SELECT phase_subject_sha256, wrapper_sha256, wrapper_raw
            FROM diagnostic_phase_outcome_access
            """
        )
    )
    if reconciliation.status == PHASE_RECONCILED_REJECTED:
        if (
            row[4] != PHASE_RECONCILED_REJECTED
            or row[7] is not None
            or row[8] is not None
            or outcome_access is not None
            or access_rows
        ):
            raise DiagnosticCalibrationIntegrityError(
                "early rejection is not the exact no-access canonical DB state"
            )
        return
    if outcome_access is None:
        raise DiagnosticCalibrationIntegrityError(
            "post-access disposition omitted its canonical outcome carrier"
        )
    if (
        row[4] != PHASE_OUTCOME_ACCESSED
        or row[7] != outcome_access.sha256
        or row[8] is None
        or bytes(row[8]) != outcome_access.raw_bytes
        or len(access_rows) != 1
        or access_rows[0][0] != registration.phase_subject_sha256
        or access_rows[0][1] != outcome_access.sha256
        or bytes(access_rows[0][2]) != outcome_access.raw_bytes
    ):
        raise DiagnosticCalibrationIntegrityError(
            "canonical database outcome-access bytes drifted"
        )


def _registry_row_value(
    disposition: DiagnosticCalibrationDispositionArtifact,
) -> tuple[Any, ...]:
    return (
        disposition.phase_subject_sha256,
        disposition.payload["phase_store_binding"]["sha256"],
        disposition.registration_ref.sha256,
        disposition.reconciliation_ref.sha256,
        None if disposition.rule_ref is None else disposition.rule_ref.sha256,
        None if disposition.dataset_ref is None else disposition.dataset_ref.sha256,
        (
            None
            if disposition.fit_transcript_ref is None
            else disposition.fit_transcript_ref.sha256
        ),
        (
            None
            if disposition.outcome_access_ref is None
            else disposition.outcome_access_ref.sha256
        ),
        None if disposition.analysis_ref is None else disposition.analysis_ref.sha256,
        None if disposition.bundle_ref is None else disposition.bundle_ref.sha256,
        disposition.sha256,
        disposition.raw_bytes,
        disposition.status,
        disposition.finalized_at,
    )


_REGISTRY_SELECT = """
SELECT phase_subject_sha256, store_binding_sha256, registration_sha256,
       reconciliation_sha256, rule_sha256, dataset_sha256,
       fit_transcript_sha256, outcome_access_sha256, analysis_sha256,
       bundle_sha256, disposition_sha256, disposition_raw, status, finalized_at
FROM diagnostic_calibration_dispositions
"""


def _normalized_registry_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    return (*row[:11], bytes(row[11]), *row[12:])


class DiagnosticCalibrationDispositionRegistry:
    """Same-file, create-once terminal slot for one canonically bound phase."""

    def __init__(
        self, *, registration: DiagnosticPhaseRegistrationArtifact
    ) -> None:
        replay_diagnostic_phase_registration_projection(registration)
        replay_diagnostic_phase_store_binding_projection(registration.store_binding)
        self.__registration = registration
        connection = _disposition_connection(self.__registration.store_binding)
        try:
            connection.execute("BEGIN IMMEDIATE")
            _verify_bound_connection_identity(
                connection, self.__registration.store_binding
            )
            row = _phase_row(connection, registration)
            if row[4] not in {PHASE_RECONCILED_REJECTED, PHASE_OUTCOME_ACCESSED}:
                raise DiagnosticCalibrationConflict(
                    "disposition registry can be installed only after terminal rejection or aggregate access"
                )
            existing = connection.execute(
                """
                SELECT type FROM sqlite_master
                WHERE name='diagnostic_calibration_dispositions'
                """
            ).fetchone()
            if existing is None:
                connection.execute(_CREATE_DISPOSITIONS_TABLE)
                connection.execute(_CREATE_DISPOSITIONS_UPDATE_GUARD)
                connection.execute(_CREATE_DISPOSITIONS_DELETE_GUARD)
            _verify_disposition_schema(connection)
            retained = tuple(connection.execute(_REGISTRY_SELECT))
            if len(retained) > 1 or (
                retained
                and retained[0][0] != registration.phase_subject_sha256
            ):
                raise DiagnosticCalibrationIntegrityError(
                    "disposition inventory is not empty-or-one for the canonical phase"
                )
            _verify_bound_connection_identity(
                connection, self.__registration.store_binding
            )
            connection.execute("COMMIT")
            _verify_bound_connection_identity(
                connection, self.__registration.store_binding
            )
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()

    @property
    def phase_subject_sha256(self) -> str:
        return self.__registration.phase_subject_sha256

    def __persist(
        self,
        disposition: DiagnosticCalibrationDispositionArtifact,
        *,
        reconciliation: DiagnosticPhaseReconciliationArtifact,
        outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None,
    ) -> DiagnosticCalibrationDispositionArtifact:
        replay_diagnostic_phase_store_binding_projection(
            self.__registration.store_binding
        )
        expected = _registry_row_value(disposition)
        connection = _disposition_connection(self.__registration.store_binding)
        try:
            connection.execute("BEGIN IMMEDIATE")
            _verify_bound_connection_identity(
                connection, self.__registration.store_binding
            )
            _verify_disposition_schema(connection)
            _verify_terminal_phase_row(
                connection,
                registration=self.__registration,
                reconciliation=reconciliation,
                outcome_access=outcome_access,
            )
            rows = tuple(connection.execute(_REGISTRY_SELECT))
            if len(rows) > 1 or (
                rows and rows[0][0] != self.__registration.phase_subject_sha256
            ):
                raise DiagnosticCalibrationIntegrityError(
                    "disposition inventory is not exactly scoped to one phase"
                )
            if rows:
                if _normalized_registry_row(rows[0]) != expected:
                    raise DiagnosticCalibrationConflict(
                        "phase already has a different terminal disposition"
                    )
            else:
                connection.execute(
                    """
                    INSERT INTO diagnostic_calibration_dispositions (
                        phase_subject_sha256, store_binding_sha256,
                        registration_sha256, reconciliation_sha256,
                        rule_sha256, dataset_sha256, fit_transcript_sha256,
                        outcome_access_sha256, analysis_sha256, bundle_sha256,
                        disposition_sha256, disposition_raw, status, finalized_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    expected,
                )
                retained = connection.execute(_REGISTRY_SELECT).fetchone()
                if (
                    retained is None
                    or _normalized_registry_row(retained) != expected
                ):
                    raise DiagnosticCalibrationIntegrityError(
                        "create-once disposition row failed exact read-after-write"
                    )
            _verify_bound_connection_identity(
                connection, self.__registration.store_binding
            )
            connection.execute("COMMIT")
            _verify_bound_connection_identity(
                connection, self.__registration.store_binding
            )
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()
        return disposition

    def finalize_freeze(
        self,
        *,
        finalized_at: str,
        rule: DiagnosticCalibrationRuleArtifact,
        dataset: DiagnosticCalibrationActivationDatasetArtifact,
        transcript: DiagnosticCalibrationFitTranscriptArtifact,
        shared_plan_context: DiagnosticSharedPlanReplayContext,
        reconciliation: DiagnosticPhaseReconciliationArtifact,
        outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
        analysis: DiagnosticCalibrationAnalysisArtifact,
        bundle: DiagnosticCalibrationDetectorBundleArtifact,
    ) -> DiagnosticCalibrationDispositionArtifact:
        try:
            finalized_at = expect_timestamp(finalized_at, "finalized_at")
        except SchemaValidationError as exc:
            raise DiagnosticCalibrationValidationError(str(exc)) from exc
        status, reasons, terminal_path = _terminal_dependency_mode(
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            shared_plan_context=shared_plan_context,
            registration=self.__registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
            analysis=analysis,
            bundle=bundle,
            full_numeric_replay=True,
        )
        if status != CALIBRATION_FROZEN_NONREPORTING:
            raise DiagnosticCalibrationValidationError(
                "freeze finalizer received a non-eligible dependency family"
            )
        raw = canonical_json_bytes(
            _disposition_value(
                finalized_at=finalized_at,
                status=status,
                rejection_reasons=reasons,
                terminal_path=terminal_path,
                registration=self.__registration,
                reconciliation=reconciliation,
                rule=rule,
                dataset=dataset,
                transcript=transcript,
                outcome_access=outcome_access,
                analysis=analysis,
                bundle=bundle,
            )
        )
        artifact = _load_disposition(
            raw,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            shared_plan_context=None,
            registration=self.__registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
            analysis=analysis,
            bundle=bundle,
            full_numeric_replay=False,
        )
        return self.__persist(
            artifact,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )

    def finalize_rejection(
        self,
        *,
        finalized_at: str,
        reconciliation: DiagnosticPhaseReconciliationArtifact,
        rule: DiagnosticCalibrationRuleArtifact | None = None,
        dataset: DiagnosticCalibrationActivationDatasetArtifact | None = None,
        transcript: DiagnosticCalibrationFitTranscriptArtifact | None = None,
        shared_plan_context: DiagnosticSharedPlanReplayContext | None = None,
        outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None = None,
        analysis: DiagnosticCalibrationAnalysisArtifact | None = None,
    ) -> DiagnosticCalibrationDispositionArtifact:
        try:
            finalized_at = expect_timestamp(finalized_at, "finalized_at")
        except SchemaValidationError as exc:
            raise DiagnosticCalibrationValidationError(str(exc)) from exc
        status, reasons, terminal_path = _terminal_dependency_mode(
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            shared_plan_context=shared_plan_context,
            registration=self.__registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
            analysis=analysis,
            bundle=None,
            full_numeric_replay=True,
        )
        if status != CALIBRATION_REJECTED_NONREPORTING:
            raise DiagnosticCalibrationValidationError(
                "rejection finalizer received an eligible dependency family"
            )
        raw = canonical_json_bytes(
            _disposition_value(
                finalized_at=finalized_at,
                status=status,
                rejection_reasons=reasons,
                terminal_path=terminal_path,
                registration=self.__registration,
                reconciliation=reconciliation,
                rule=rule,
                dataset=dataset,
                transcript=transcript,
                outcome_access=outcome_access,
                analysis=analysis,
                bundle=None,
            )
        )
        artifact = _load_disposition(
            raw,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            shared_plan_context=None,
            registration=self.__registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
            analysis=analysis,
            bundle=None,
            full_numeric_replay=False,
        )
        return self.__persist(
            artifact,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
        )

    def replay_retained(
        self,
        *,
        reconciliation: DiagnosticPhaseReconciliationArtifact,
        rule: DiagnosticCalibrationRuleArtifact | None = None,
        dataset: DiagnosticCalibrationActivationDatasetArtifact | None = None,
        transcript: DiagnosticCalibrationFitTranscriptArtifact | None = None,
        shared_plan_context: DiagnosticSharedPlanReplayContext | None = None,
        outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None = None,
        analysis: DiagnosticCalibrationAnalysisArtifact | None = None,
        bundle: DiagnosticCalibrationDetectorBundleArtifact | None = None,
    ) -> DiagnosticCalibrationDispositionArtifact | None:
        replay_diagnostic_phase_store_binding_projection(
            self.__registration.store_binding
        )
        connection = _disposition_connection(self.__registration.store_binding)
        try:
            connection.execute("BEGIN")
            _verify_bound_connection_identity(
                connection, self.__registration.store_binding
            )
            _verify_disposition_schema(connection)
            _verify_terminal_phase_row(
                connection,
                registration=self.__registration,
                reconciliation=reconciliation,
                outcome_access=outcome_access,
            )
            rows = tuple(connection.execute(_REGISTRY_SELECT))
            if not rows:
                _verify_bound_connection_identity(
                    connection, self.__registration.store_binding
                )
                connection.execute("COMMIT")
                _verify_bound_connection_identity(
                    connection, self.__registration.store_binding
                )
                return None
            if len(rows) != 1 or rows[0][0] != self.phase_subject_sha256:
                raise DiagnosticCalibrationIntegrityError(
                    "retained disposition inventory escaped its exact phase"
                )
            raw = bytes(rows[0][11])
            _verify_bound_connection_identity(
                connection, self.__registration.store_binding
            )
            connection.execute("COMMIT")
            _verify_bound_connection_identity(
                connection, self.__registration.store_binding
            )
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()
        artifact = load_diagnostic_calibration_disposition(
            raw,
            registration=self.__registration,
            reconciliation=reconciliation,
            rule=rule,
            dataset=dataset,
            transcript=transcript,
            shared_plan_context=shared_plan_context,
            outcome_access=outcome_access,
            analysis=analysis,
            bundle=bundle,
        )
        if _registry_row_value(artifact) != _normalized_registry_row(rows[0]):
            raise DiagnosticCalibrationIntegrityError(
                "retained disposition row differs from full exact replay"
            )
        return artifact


__all__ = [
    "CALIBRATION_ANALYSIS_ELIGIBLE",
    "CALIBRATION_ANALYSIS_INELIGIBLE",
    "CALIBRATION_FROZEN_NONREPORTING",
    "CALIBRATION_REJECTED_NONREPORTING",
    "DIAGNOSTIC_CALIBRATION_ANALYSIS_MEDIA_TYPE",
    "DIAGNOSTIC_CALIBRATION_ANALYSIS_SCHEMA",
    "DIAGNOSTIC_CALIBRATION_DETECTOR_BUNDLE_MEDIA_TYPE",
    "DIAGNOSTIC_CALIBRATION_DETECTOR_BUNDLE_SCHEMA",
    "DIAGNOSTIC_CALIBRATION_DISPOSITION_MEDIA_TYPE",
    "DIAGNOSTIC_CALIBRATION_DISPOSITION_SCHEMA",
    "DiagnosticCalibrationAnalysisArtifact",
    "DiagnosticCalibrationConflict",
    "DiagnosticCalibrationDetectorBundleArtifact",
    "DiagnosticCalibrationDetectorResult",
    "DiagnosticCalibrationDispositionArtifact",
    "DiagnosticCalibrationDispositionRegistry",
    "DiagnosticCalibrationError",
    "DiagnosticCalibrationIntegrityError",
    "DiagnosticCalibrationValidationError",
    "build_diagnostic_calibration_analysis",
    "build_diagnostic_calibration_detector_bundle",
    "load_diagnostic_calibration_analysis",
    "load_diagnostic_calibration_detector_bundle",
    "load_diagnostic_calibration_disposition",
    "replay_diagnostic_calibration_analysis_projection",
    "replay_diagnostic_calibration_detector_bundle_projection",
    "replay_diagnostic_calibration_disposition_projection",
]
