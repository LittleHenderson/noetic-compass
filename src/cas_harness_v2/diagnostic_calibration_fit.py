"""Prospective, exact Stage-C calibration fitting and replay carriers.

This module owns only the post-access calibration computation.  A calibration
rule is built before the Study plan and must subsequently appear as the sole
calibration-rule execution identity.  Activation bodies are accepted only from
the aggregate outcome-access artifact, never from the public reconciliation.

The resulting transcript is a deterministic structural carrier.  It does not
establish detector correctness, authorize C-Eval, create an Evidence Packet,
or license a product claim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import math
import struct
from types import MappingProxyType
from typing import Any
import warnings

from ._strict_json import (
    canonical_json_bytes,
    canonical_sha256,
    freeze_json,
    load_json_object,
    sha256_bytes,
    thaw_json,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_bool,
    expect_enum,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
)
from .diagnostic_lifecycle import (
    DiagnosticSharedPlanReplayContext,
    _require_shared_seal,
)
from .diagnostic_phase_coordinator import (
    DIAGNOSTIC_ACTIVATION_VECTOR_MEDIA_TYPE,
    DIAGNOSTIC_ACTIVATION_WIDTH,
    DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE,
    PHASE_RECONCILED_CLEAN,
    DiagnosticPhaseActivationAdmissionArtifact,
    DiagnosticPhaseOutcomeAccessArtifact,
    DiagnosticPhaseReconciliationArtifact,
    DiagnosticPhaseRegistrationArtifact,
    replay_diagnostic_phase_activation_admission_projection,
    replay_diagnostic_phase_outcome_access_projection,
    replay_diagnostic_phase_reconciliation_projection,
    replay_diagnostic_phase_registration_projection,
)
from .diagnostic_study_protocol import (
    ADVERSARIAL_PRESENT,
    CLEAN_ABSENT,
    CLEAN_NULL_ABSENT,
    DIAGNOSTIC_CASE_COUNT,
    DIAGNOSTIC_GROUP_COUNT,
)


DIAGNOSTIC_CALIBRATION_RULE_SCHEMA = (
    "cas_harness_v2.diagnostic_calibration_rule.v1"
)
DIAGNOSTIC_CALIBRATION_ACTIVATION_DATASET_SCHEMA = (
    "cas_harness_v2.diagnostic_calibration_activation_dataset.v1"
)
DIAGNOSTIC_CALIBRATION_FIT_TRANSCRIPT_SCHEMA = (
    "cas_harness_v2.diagnostic_calibration_fit_transcript.v1"
)
DIAGNOSTIC_CALIBRATION_ACTIVATION_DATASET_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-calibration-activation-dataset+json"
)
DIAGNOSTIC_CALIBRATION_FIT_TRANSCRIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-calibration-fit-transcript+json"
)

TARGET_LAYER_DETECTOR = "TARGET_LAYER_DETECTOR"
WRONG_LAYER_CONTROL_DETECTOR = "WRONG_LAYER_CONTROL_DETECTOR"
DIAGNOSTIC_CALIBRATION_DETECTOR_ROLES = (
    TARGET_LAYER_DETECTOR,
    WRONG_LAYER_CONTROL_DETECTOR,
)
ELIGIBLE_THRESHOLD_SELECTED = "ELIGIBLE_THRESHOLD_SELECTED"
NO_ELIGIBLE_THRESHOLD = "NO_ELIGIBLE_THRESHOLD"

_RUNTIME_LOCK = {
    "numpy": "2.5.1",
    "scikit-learn": "1.9.0",
    "scipy": "1.18.0",
}
_LAYER_SPECS = {
    TARGET_LAYER_DETECTOR: {
        "dataset_key": "target_layer18",
        "admission_field": "target_vector",
        "body_field": "target_body",
        "role": "target_final_token_activation",
        "layer_index": 18,
        "module_path": "model.layers[18].mlp.down_proj",
        "feature_width": DIAGNOSTIC_ACTIVATION_WIDTH,
    },
    WRONG_LAYER_CONTROL_DETECTOR: {
        "dataset_key": "wrong_layer0",
        "admission_field": "wrong_layer_vector",
        "body_field": "wrong_layer_body",
        "role": "wrong_layer_final_token_activation",
        "layer_index": 0,
        "module_path": "model.layers[0].mlp.down_proj",
        "feature_width": DIAGNOSTIC_ACTIVATION_WIDTH,
    },
}
_SCALER = {
    "class": "sklearn.preprocessing.StandardScaler",
    "copy": True,
    "with_mean": True,
    "with_std": True,
    "input_dtype": "little-endian-float32",
    "fit_dtype": "binary64",
    "fit_scope": "INDEPENDENT_PER_DETECTOR_COMPLETE_C_CAL_ONLY",
}
_ESTIMATOR = {
    "class": "sklearn.linear_model.LogisticRegression",
    "penalty": "l2",
    "C_binary64_hex": "0x1.0000000000000p-2",
    "C_binary64_bytes_hex": "3FD0000000000000",
    "l1_ratio_binary64_hex": "0x0.0p+0",
    "dual": False,
    "tol_binary64_hex": "0x1.5798ee2308c3ap-27",
    "fit_intercept": True,
    "intercept_scaling": 1,
    "class_weight": "balanced",
    "random_state": 42,
    "solver": "lbfgs",
    "max_iter": 1000,
    "verbose": 0,
    "warm_start": False,
    "n_jobs": 1,
    "classes": ["ABSENT", "PRESENT"],
    "positive_class_index": 1,
    "score_carrier": "predict_proba[:,positive_class_index]",
}
_CANDIDATE_RULE = {
    "derivation": (
        "ORDINAL_SORTED_UNIQUE_OF_0_1_NEXTAFTER_1_POSINF_"
        "EACH_FINITE_SCORE_AND_NEXTAFTER_EACH_SCORE_POSINF"
    ),
    "prediction_comparator": "FINITE_SCORE_GREATER_THAN_OR_EQUAL_THRESHOLD",
    "clean_specificity_minimum_numerator": 9,
    "clean_specificity_minimum_denominator": 10,
    "clean_null_specificity_minimum_numerator": 9,
    "clean_null_specificity_minimum_denominator": 10,
    "eligibility_comparator": "INTEGER_CROSS_MULTIPLICATION_GREATER_THAN_OR_EQUAL",
    "objective": "MAXIMIZE_BINARY_BALANCED_ACCURACY",
    "objective_exact_comparator": (
        "MAXIMIZE_2_TIMES_ADVERSARIAL_TP_PLUS_CLEAN_TN_PLUS_CLEAN_NULL_TN"
    ),
    "tie_break": "NUMERICALLY_HIGHER_BINARY64_THRESHOLD",
    "no_eligible_result": NO_ELIGIBLE_THRESHOLD,
}
_BOUNDARY = {
    "scope": "DIAGNOSTIC_CALIBRATION_NONREPORTING_ONLY",
    "admission_ring": 4,
    "criteria_status": "OPEN",
    "scientific_correctness": "NOT_ESTABLISHED",
    "product_claim_status": "NOT LICENSED",
    "disclosure_status": "HELD",
    "evidence_packet_v2": "FORBIDDEN",
    "evaluation_execution": "NOT_AUTHORIZED",
    "evaluation_promotion": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
    "product_route": "FORBIDDEN",
    "public_release": False,
    "trusted_time": "NOT_PROVIDED",
    "replication": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
}
_VARIANTS = (ADVERSARIAL_PRESENT, CLEAN_ABSENT, CLEAN_NULL_ABSENT)
_MAPPING_PROXY_TYPE = type(MappingProxyType({}))


class DiagnosticCalibrationFitError(RuntimeError):
    """Base error for exact diagnostic calibration computation."""


class DiagnosticCalibrationFitValidationError(DiagnosticCalibrationFitError):
    """A carrier, dependency, or numerical projection is not exact."""


class DiagnosticCalibrationRuntimeVersionError(DiagnosticCalibrationFitError):
    """The numerical runtime differs from the prospective package lock."""


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _canonical_object(
    raw: bytes | bytearray | memoryview, path: str
) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, obj = load_json_object(raw)
        if snapshot != canonical_json_bytes(obj):
            raise DiagnosticCalibrationFitValidationError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, obj
    except DiagnosticCalibrationFitValidationError:
        raise
    except (ValueError, TypeError) as exc:
        raise DiagnosticCalibrationFitValidationError(f"{path}: {exc}") from exc


def _require_exact_type(value: Any, expected: type, path: str) -> None:
    if type(value) is not expected:
        raise DiagnosticCalibrationFitValidationError(
            f"{path} must be an exact {expected.__name__}"
        )


def _require_frozen_json(value: Any, path: str) -> None:
    if type(value) is _MAPPING_PROXY_TYPE:
        for key, item in value.items():
            if type(key) is not str:
                raise DiagnosticCalibrationFitValidationError(
                    f"{path} contains a non-string mapping key"
                )
            _require_frozen_json(item, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, item in enumerate(value):
            _require_frozen_json(item, f"{path}[{index}]")
        return
    if type(value) in (str, int, bool) or value is None:
        return
    raise DiagnosticCalibrationFitValidationError(
        f"{path} must be recursively immutable frozen JSON, not {type(value).__name__}"
    )


def _require_artifact_scalars(
    *, raw_bytes: Any, sha256: Any, byte_length: Any, payload: Any, path: str
) -> None:
    if (
        type(raw_bytes) is not bytes
        or type(sha256) is not str
        or type(byte_length) is not int
    ):
        raise DiagnosticCalibrationFitValidationError(
            f"{path} raw/hash/length fields must have exact immutable types"
        )
    _require_frozen_json(payload, f"{path}.payload")


def _require_boundary(value: Any, path: str = "$.boundary") -> None:
    try:
        obj = expect_object(value, path)
        expect_keys(obj, required=_BOUNDARY, path=path)
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationFitValidationError(str(exc)) from exc
    if obj != _BOUNDARY:
        raise DiagnosticCalibrationFitValidationError(
            f"{path} fabricated scientific, evaluation, Packet, claim, or product authority"
        )


@dataclass(frozen=True, slots=True)
class DiagnosticBinary64:
    """One finite IEEE-754 binary64 value in three mutually checked encodings."""

    hex: str
    bytes_hex: str
    decimal: str

    @property
    def value(self) -> float:
        return float.fromhex(self.hex)


def _binary64(value: Any, path: str) -> DiagnosticBinary64:
    if type(value) not in (int, float):
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise DiagnosticCalibrationFitValidationError(
                f"{path} must be one finite binary64 scalar"
            ) from exc
    number = float(value)
    if not math.isfinite(number):
        raise DiagnosticCalibrationFitValidationError(f"{path} must be finite")
    return DiagnosticBinary64(
        hex=number.hex(),
        bytes_hex=struct.pack(">d", number).hex().upper(),
        decimal=repr(number),
    )


def _binary64_value(value: DiagnosticBinary64) -> dict[str, str]:
    return {
        "hex": value.hex,
        "bytes_hex": value.bytes_hex,
        "decimal": value.decimal,
    }


def _load_binary64(value: Any, path: str) -> DiagnosticBinary64:
    try:
        obj = expect_object(value, path)
        expect_keys(obj, required={"hex", "bytes_hex", "decimal"}, path=path)
        hex_text = expect_string(obj["hex"], f"{path}.hex", maximum=64)
        bytes_text = expect_string(obj["bytes_hex"], f"{path}.bytes_hex", maximum=16)
        decimal = expect_string(obj["decimal"], f"{path}.decimal", maximum=32)
        number = float.fromhex(hex_text)
        decimal_number = float(decimal)
    except (SchemaValidationError, ValueError, OverflowError) as exc:
        raise DiagnosticCalibrationFitValidationError(
            f"{path} is not an exact finite binary64 encoding"
        ) from exc
    expected = _binary64(number, path)
    if (
        expected.hex != hex_text
        or expected.bytes_hex != bytes_text
        or expected.decimal != decimal
        or struct.pack(">d", decimal_number) != struct.pack(">d", number)
    ):
        raise DiagnosticCalibrationFitValidationError(
            f"{path} binary64 hex/bytes/decimal encodings disagree"
        )
    return expected


def _encode_binary64_vector(values: Any, width: int, path: str) -> bytes:
    try:
        rows = tuple(float(item) for item in values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DiagnosticCalibrationFitValidationError(
            f"{path} cannot be converted to binary64"
        ) from exc
    if len(rows) != width or any(not math.isfinite(item) for item in rows):
        raise DiagnosticCalibrationFitValidationError(
            f"{path} must contain exactly {width} finite binary64 values"
        )
    return struct.pack(f"<{width}d", *rows)


def _decode_binary64_vector(
    raw: bytes, width: int, path: str, *, positive: bool = False
) -> tuple[float, ...]:
    if type(raw) is not bytes or len(raw) != width * 8:
        raise DiagnosticCalibrationFitValidationError(
            f"{path} must contain exactly {width} little-endian binary64 values"
        )
    try:
        values = struct.unpack(f"<{width}d", raw)
    except struct.error as exc:  # pragma: no cover - exact length already checked
        raise DiagnosticCalibrationFitValidationError(f"{path} cannot be decoded") from exc
    if any(not math.isfinite(item) for item in values):
        raise DiagnosticCalibrationFitValidationError(f"{path} contains NaN or infinity")
    if positive and any(item <= 0.0 for item in values):
        raise DiagnosticCalibrationFitValidationError(
            f"{path} StandardScaler scale values must be positive"
        )
    return values


def _binary64_vector_value(raw: bytes) -> dict[str, Any]:
    return {
        "dtype": "little-endian-binary64",
        "byte_length": len(raw),
        "sha256": sha256_bytes(raw),
        "bytes_hex": raw.hex().upper(),
    }


def _load_binary64_vector(value: Any, width: int, path: str, *, positive: bool = False) -> bytes:
    try:
        obj = expect_object(value, path)
        expect_keys(
            obj,
            required={"dtype", "byte_length", "sha256", "bytes_hex"},
            path=path,
        )
        if obj["dtype"] != "little-endian-binary64":
            raise SchemaValidationError(f"{path}.dtype changed")
        length = expect_int(obj["byte_length"], f"{path}.byte_length")
        digest = expect_sha256(obj["sha256"], f"{path}.sha256")
        text = expect_string(obj["bytes_hex"], f"{path}.bytes_hex", maximum=width * 16)
        raw = bytes.fromhex(text)
    except (SchemaValidationError, ValueError) as exc:
        raise DiagnosticCalibrationFitValidationError(str(exc)) from exc
    if (
        text != raw.hex().upper()
        or length != width * 8
        or len(raw) != length
        or sha256_bytes(raw) != digest
    ):
        raise DiagnosticCalibrationFitValidationError(f"{path} vector identity disagrees")
    _decode_binary64_vector(raw, width, path, positive=positive)
    return raw


def _layer_value(role: str) -> dict[str, Any]:
    spec = _LAYER_SPECS[role]
    return {
        "role": role,
        "activation_role": spec["role"],
        "layer_index": spec["layer_index"],
        "module_path": spec["module_path"],
        "feature_width": spec["feature_width"],
    }


def _rule_value(*, rule_id: str, created_at: str) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_CALIBRATION_RULE_SCHEMA,
        "rule_id": rule_id,
        "created_at": created_at,
        "prospective_binding": {
            "required_plan_location": "execution_identity_artifacts",
            "required_media_type": DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE,
            "cardinality": "EXACTLY_ONE_AND_EXACT_SELF_REFERENCE",
            "plan_must_follow_rule": True,
        },
        "dataset": {
            "row_count": DIAGNOSTIC_CASE_COUNT,
            "group_count": DIAGNOSTIC_GROUP_COUNT,
            "ordered_variant_triplet": list(_VARIANTS),
            "binary_label": {
                ADVERSARIAL_PRESENT: 1,
                CLEAN_ABSENT: 0,
                CLEAN_NULL_ABSENT: 0,
            },
            "activation_dtype": "little-endian-float32",
            "detectors": [_layer_value(role) for role in DIAGNOSTIC_CALIBRATION_DETECTOR_ROLES],
            "body_access": "AGGREGATE_OUTCOME_ACCESS_ONLY",
        },
        "runtime_lock": dict(_RUNTIME_LOCK),
        "standard_scaler": dict(_SCALER),
        "logistic_regression": dict(_ESTIMATOR),
        "threshold_candidate_and_selection_rule": dict(_CANDIDATE_RULE),
        "numeric_encoding": {
            "parameters": "LITTLE_ENDIAN_BINARY64_BYTES",
            "scalars": "PYTHON_FLOAT_HEX_PLUS_BIG_ENDIAN_BYTES_PLUS_ROUNDTRIP_DECIMAL",
            "json_floating_point_numbers": "FORBIDDEN",
        },
        "scientific_correctness": "NOT_ESTABLISHED",
        "boundary": dict(_BOUNDARY),
    }


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationRuleArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    rule_id: str
    created_at: str
    runtime_versions: Mapping[str, str]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.rule_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE,
        )


def _require_rule_projection_types(rule: Any) -> None:
    _require_exact_type(rule, DiagnosticCalibrationRuleArtifact, "rule")
    _require_artifact_scalars(
        raw_bytes=rule.raw_bytes,
        sha256=rule.sha256,
        byte_length=rule.byte_length,
        payload=rule.payload,
        path="rule",
    )
    if (
        type(rule.rule_id) is not str
        or type(rule.created_at) is not str
        or type(rule.runtime_versions) is not _MAPPING_PROXY_TYPE
        or any(
            type(key) is not str or type(value) is not str
            for key, value in rule.runtime_versions.items()
        )
    ):
        raise DiagnosticCalibrationFitValidationError(
            "rule scalar/runtime fields must have exact immutable types"
        )


def load_diagnostic_calibration_rule(
    raw: bytes | bytearray | memoryview,
) -> DiagnosticCalibrationRuleArtifact:
    """Strict-load the prospective, numerical-runtime-independent rule."""

    snapshot, obj = _canonical_object(raw, "diagnostic calibration rule")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "rule_id",
                "created_at",
                "prospective_binding",
                "dataset",
                "runtime_lock",
                "standard_scaler",
                "logistic_regression",
                "threshold_candidate_and_selection_rule",
                "numeric_encoding",
                "scientific_correctness",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_CALIBRATION_RULE_SCHEMA:
            raise SchemaValidationError("wrong diagnostic calibration-rule schema")
        rule_id = expect_machine_id(obj["rule_id"], "$.rule_id")
        created_at = expect_timestamp(obj["created_at"], "$.created_at")
        runtime = expect_object(obj["runtime_lock"], "$.runtime_lock")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationFitValidationError(str(exc)) from exc
    _require_boundary(obj["boundary"])
    expected = _rule_value(rule_id=rule_id, created_at=created_at)
    if obj != expected or runtime != _RUNTIME_LOCK:
        raise DiagnosticCalibrationFitValidationError(
            "diagnostic calibration rule differs from the frozen prospective rule"
        )
    return DiagnosticCalibrationRuleArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        rule_id=rule_id,
        created_at=created_at,
        runtime_versions=MappingProxyType(dict(_RUNTIME_LOCK)),
        payload=freeze_json(obj),
    )


def build_diagnostic_calibration_rule(
    *, rule_id: str, created_at: str
) -> DiagnosticCalibrationRuleArtifact:
    """Build the rule before the plan that will bind its exact artifact ref."""

    try:
        rule_id = expect_machine_id(rule_id, "rule_id")
        created_at = expect_timestamp(created_at, "created_at")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationFitValidationError(str(exc)) from exc
    return load_diagnostic_calibration_rule(
        canonical_json_bytes(_rule_value(rule_id=rule_id, created_at=created_at))
    )


def replay_diagnostic_calibration_rule_projection(
    rule: DiagnosticCalibrationRuleArtifact,
) -> DiagnosticCalibrationRuleArtifact:
    """Cheaply reject replacement of any rule dataclass/raw projection."""

    _require_rule_projection_types(rule)
    exact = load_diagnostic_calibration_rule(rule.raw_bytes)
    if exact != rule:
        raise DiagnosticCalibrationFitValidationError(
            "calibration rule dataclass differs from exact raw-byte projection"
        )
    return exact


def bind_diagnostic_calibration_rule_to_plan(
    rule: DiagnosticCalibrationRuleArtifact,
    *,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
) -> DiagnosticCalibrationRuleArtifact:
    """Prove that this exact pre-plan rule is the sole plan execution identity."""

    rule = replay_diagnostic_calibration_rule_projection(rule)
    try:
        seal = _require_shared_seal(shared_plan_context)
    except Exception as exc:
        raise DiagnosticCalibrationFitValidationError(
            f"shared plan context is not the exact process-sealed factory result: {exc}"
        ) from exc
    identities = tuple(
        reference
        for reference in seal.plan_execution_identity_artifacts
        if reference.media_type == DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE
    )
    if identities != (rule.artifact_ref,):
        raise DiagnosticCalibrationFitValidationError(
            "plan must bind this exact sole diagnostic calibration rule execution identity"
        )
    if _time(rule.created_at) >= _time(shared_plan_context.plan.created_at):
        raise DiagnosticCalibrationFitValidationError(
            "diagnostic calibration rule must be created strictly before its binding plan"
        )
    return rule


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationDatasetRow:
    execution_ordinal: int
    case_id: str
    base_intent_group_id: str
    frozen_variant: str
    binary_label: int
    attempt_subject_sha256: str
    study_request_ref: ArtifactRef
    activation_admission_ref: ArtifactRef
    target_vector_ref: ArtifactRef
    wrong_layer_vector_ref: ArtifactRef
    target_body: bytes
    wrong_layer_body: bytes


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationActivationDatasetArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    dataset_id: str
    created_at: str
    phase_subject_sha256: str
    rule_ref: ArtifactRef
    registration_ref: ArtifactRef
    reconciliation_ref: ArtifactRef
    outcome_access_ref: ArtifactRef
    dataset_identity_sha256: str
    rows: tuple[DiagnosticCalibrationDatasetRow, ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.dataset_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_CALIBRATION_ACTIVATION_DATASET_MEDIA_TYPE,
        )

    @property
    def target_activation_artifacts(self) -> tuple[tuple[ArtifactRef, bytes], ...]:
        return tuple((row.target_vector_ref, row.target_body) for row in self.rows)

    @property
    def wrong_layer_activation_artifacts(
        self,
    ) -> tuple[tuple[ArtifactRef, bytes], ...]:
        return tuple((row.wrong_layer_vector_ref, row.wrong_layer_body) for row in self.rows)


def _require_dataset_projection_types(dataset: Any) -> None:
    _require_exact_type(
        dataset, DiagnosticCalibrationActivationDatasetArtifact, "dataset"
    )
    _require_artifact_scalars(
        raw_bytes=dataset.raw_bytes,
        sha256=dataset.sha256,
        byte_length=dataset.byte_length,
        payload=dataset.payload,
        path="dataset",
    )
    for name in (
        "dataset_id",
        "created_at",
        "phase_subject_sha256",
        "dataset_identity_sha256",
    ):
        if type(getattr(dataset, name)) is not str:
            raise DiagnosticCalibrationFitValidationError(
                f"dataset.{name} must be exact immutable text"
            )
    for name in (
        "rule_ref",
        "registration_ref",
        "reconciliation_ref",
        "outcome_access_ref",
    ):
        _require_exact_type(getattr(dataset, name), ArtifactRef, f"dataset.{name}")
    if type(dataset.rows) is not tuple or len(dataset.rows) != DIAGNOSTIC_CASE_COUNT:
        raise DiagnosticCalibrationFitValidationError(
            "dataset.rows must be an exact immutable 480-row tuple"
        )
    for index, row in enumerate(dataset.rows):
        _require_exact_type(
            row, DiagnosticCalibrationDatasetRow, f"dataset.rows[{index}]"
        )
        if (
            type(row.execution_ordinal) is not int
            or type(row.binary_label) is not int
            or any(
                type(value) is not str
                for value in (
                    row.case_id,
                    row.base_intent_group_id,
                    row.frozen_variant,
                    row.attempt_subject_sha256,
                )
            )
            or type(row.target_body) is not bytes
            or type(row.wrong_layer_body) is not bytes
        ):
            raise DiagnosticCalibrationFitValidationError(
                f"dataset.rows[{index}] scalar/body fields have mutable or wrong types"
            )
        for name in (
            "study_request_ref",
            "activation_admission_ref",
            "target_vector_ref",
            "wrong_layer_vector_ref",
        ):
            _require_exact_type(
                getattr(row, name), ArtifactRef, f"dataset.rows[{index}].{name}"
            )


def _activation_value(
    *, reference: ArtifactRef, body: bytes, role: str
) -> dict[str, Any]:
    spec = _LAYER_SPECS[role]
    return {
        "artifact": _artifact_ref_value(reference),
        "body_sha256": sha256_bytes(body),
        "body_byte_length": len(body),
        "dtype": "<f4",
        "shape": [DIAGNOSTIC_ACTIVATION_WIDTH],
        "activation_role": spec["role"],
        "layer_index": spec["layer_index"],
        "module_path": spec["module_path"],
    }


def _dataset_row_value(row: DiagnosticCalibrationDatasetRow) -> dict[str, Any]:
    return {
        "domain": "cas_harness_v2.diagnostic_calibration_dataset_row.v1",
        "execution_ordinal": row.execution_ordinal,
        "case_id": row.case_id,
        "base_intent_group_id": row.base_intent_group_id,
        "frozen_variant": row.frozen_variant,
        "binary_label": row.binary_label,
        "attempt_subject_sha256": row.attempt_subject_sha256,
        "diagnostic_study_request": _artifact_ref_value(row.study_request_ref),
        "activation_admission": _artifact_ref_value(row.activation_admission_ref),
        "target_layer18": _activation_value(
            reference=row.target_vector_ref,
            body=row.target_body,
            role=TARGET_LAYER_DETECTOR,
        ),
        "wrong_layer0": _activation_value(
            reference=row.wrong_layer_vector_ref,
            body=row.wrong_layer_body,
            role=WRONG_LAYER_CONTROL_DETECTOR,
        ),
    }


def _dataset_row_sha256s(
    rows: Sequence[DiagnosticCalibrationDatasetRow],
) -> tuple[str, ...]:
    return tuple(canonical_sha256(_dataset_row_value(row)) for row in rows)


def _dataset_identity_value(
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    rows: tuple[DiagnosticCalibrationDatasetRow, ...],
) -> dict[str, Any]:
    return {
        "domain": "cas_harness_v2.diagnostic_calibration_dataset_identity.v1",
        "diagnostic_calibration_rule": _artifact_ref_value(rule.artifact_ref),
        "phase_registration": _artifact_ref_value(registration.artifact_ref),
        "phase_reconciliation": _artifact_ref_value(reconciliation.artifact_ref),
        "phase_outcome_access": _artifact_ref_value(outcome_access.artifact_ref),
        "ordered_row_sha256s": list(_dataset_row_sha256s(rows)),
    }


def _dataset_value(
    *,
    dataset_id: str,
    created_at: str,
    rule: DiagnosticCalibrationRuleArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    rows: tuple[DiagnosticCalibrationDatasetRow, ...],
) -> dict[str, Any]:
    identity = canonical_sha256(
        _dataset_identity_value(
            rule=rule,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
            rows=rows,
        )
    )
    return {
        "schema_version": DIAGNOSTIC_CALIBRATION_ACTIVATION_DATASET_SCHEMA,
        "dataset_id": dataset_id,
        "created_at": created_at,
        "phase_subject_sha256": registration.phase_subject_sha256,
        "diagnostic_calibration_rule": _artifact_ref_value(rule.artifact_ref),
        "phase_registration": _artifact_ref_value(registration.artifact_ref),
        "phase_reconciliation": _artifact_ref_value(reconciliation.artifact_ref),
        "phase_outcome_access": _artifact_ref_value(outcome_access.artifact_ref),
        "outcome_accessed_at": outcome_access.accessed_at,
        "dataset_identity_sha256": identity,
        "sample_accounting": {
            "rows": DIAGNOSTIC_CASE_COUNT,
            "groups": DIAGNOSTIC_GROUP_COUNT,
            "adversarial_present": DIAGNOSTIC_GROUP_COUNT,
            "clean_absent": DIAGNOSTIC_GROUP_COUNT,
            "clean_null_absent": DIAGNOSTIC_GROUP_COUNT,
            "target_vectors": DIAGNOSTIC_CASE_COUNT,
            "wrong_layer_vectors": DIAGNOSTIC_CASE_COUNT,
            "missing_rows": 0,
            "excluded_rows": 0,
        },
        "body_access": {
            "source": "PHASE_OUTCOME_ACCESS_ACTIVATION_ARTIFACTS",
            "before_aggregate_access": "FORBIDDEN",
            "reconciliation_contains_bodies": False,
        },
        "row_digest_domain": "cas_harness_v2.diagnostic_calibration_dataset_row.v1",
        "ordered_row_sha256s": list(_dataset_row_sha256s(rows)),
        "scientific_correctness": "NOT_ESTABLISHED",
        "boundary": dict(_BOUNDARY),
    }


def _phase_dataset_rows(
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> tuple[DiagnosticCalibrationDatasetRow, ...]:
    replay_diagnostic_phase_outcome_access_projection(
        outcome_access,
        registration=registration,
        reconciliation=reconciliation,
    )
    registration_rows = registration.payload["ordered_attempts"]
    admissions = outcome_access.activation_admissions
    activation_artifacts = outcome_access.activation_artifacts
    if (
        reconciliation.status != PHASE_RECONCILED_CLEAN
        or reconciliation.completed_rows != DIAGNOSTIC_CASE_COUNT
        or reconciliation.analyzed_rows != DIAGNOSTIC_CASE_COUNT
        or reconciliation.missing_rows != 0
        or reconciliation.excluded_rows != 0
        or type(admissions) is not tuple
        or len(admissions) != DIAGNOSTIC_CASE_COUNT
        or type(activation_artifacts) is not tuple
        or len(activation_artifacts) != DIAGNOSTIC_CASE_COUNT
        or len(registration_rows) != DIAGNOSTIC_CASE_COUNT
        or len(reconciliation.activation_admission_refs) != DIAGNOSTIC_CASE_COUNT
        or len(reconciliation.activation_vector_refs) != DIAGNOSTIC_CASE_COUNT
    ):
        raise DiagnosticCalibrationFitValidationError(
            "calibration dataset requires exact complete clean 480-row aggregate access"
        )
    rows: list[DiagnosticCalibrationDatasetRow] = []
    artifact_ids: set[str] = set()
    content_identities: set[tuple[str, int]] = set()
    variant_counts = {item: 0 for item in _VARIANTS}
    for index, (
        registration_row,
        request,
        admission,
        access_artifacts,
        admission_ref,
        vector_refs,
    ) in enumerate(
        zip(
            registration_rows,
            registration.study_requests,
            admissions,
            activation_artifacts,
            reconciliation.activation_admission_refs,
            reconciliation.activation_vector_refs,
            strict=True,
        ),
        start=1,
    ):
        _require_exact_type(
            admission,
            DiagnosticPhaseActivationAdmissionArtifact,
            f"outcome_access.activation_admissions[{index - 1}]",
        )
        replay_diagnostic_phase_activation_admission_projection(admission)
        if (
            type(access_artifacts) is not tuple
            or len(access_artifacts) != 2
            or any(type(item) is not tuple or len(item) != 2 for item in access_artifacts)
        ):
            raise DiagnosticCalibrationFitValidationError(
                f"outcome_access.activation_artifacts[{index - 1}] must be an exact immutable target/wrong pair"
            )
        (target, target_body), (wrong, wrong_body) = access_artifacts
        target_meta = admission.payload["activation_vectors"]["target_layer18"]
        wrong_meta = admission.payload["activation_vectors"]["wrong_layer0"]
        if (
            target != admission.target_vector
            or wrong != admission.wrong_layer_vector
            or admission_ref != admission.artifact_ref
            or vector_refs != (target, wrong)
            or registration_row["execution_ordinal"] != index
            or registration_row["attempt_subject_sha256"]
            != admission.attempt_subject_sha256
            or registration_row["diagnostic_study_request"]
            != _artifact_ref_value(request.artifact_ref)
            or target_meta
            != {
                "artifact": _artifact_ref_value(target),
                "dtype": "<f4",
                "shape": (DIAGNOSTIC_ACTIVATION_WIDTH,),
                "role": _LAYER_SPECS[TARGET_LAYER_DETECTOR]["role"],
                "layer_index": _LAYER_SPECS[TARGET_LAYER_DETECTOR]["layer_index"],
                "module_path": _LAYER_SPECS[TARGET_LAYER_DETECTOR]["module_path"],
            }
            or wrong_meta
            != {
                "artifact": _artifact_ref_value(wrong),
                "dtype": "<f4",
                "shape": (DIAGNOSTIC_ACTIVATION_WIDTH,),
                "role": _LAYER_SPECS[WRONG_LAYER_CONTROL_DETECTOR]["role"],
                "layer_index": _LAYER_SPECS[WRONG_LAYER_CONTROL_DETECTOR]["layer_index"],
                "module_path": _LAYER_SPECS[WRONG_LAYER_CONTROL_DETECTOR]["module_path"],
            }
        ):
            raise DiagnosticCalibrationFitValidationError(
                f"calibration row {index} differs from exact registration/reconciliation/access roles"
            )
        for reference, body, path in (
            (target, target_body, "target_layer18"),
            (wrong, wrong_body, "wrong_layer0"),
        ):
            if (
                type(reference) is not ArtifactRef
                or type(body) is not bytes
                or reference.media_type != DIAGNOSTIC_ACTIVATION_VECTOR_MEDIA_TYPE
                or len(body) != DIAGNOSTIC_ACTIVATION_WIDTH * 4
                or not reference.verify_bytes(body)
            ):
                raise DiagnosticCalibrationFitValidationError(
                    f"calibration row {index} {path} ref/body identity is not exact"
                )
            identity = (reference.sha256, reference.byte_length)
            if reference.artifact_id in artifact_ids or identity in content_identities:
                raise DiagnosticCalibrationFitValidationError(
                    "all 960 activation vector IDs and content identities must be unique"
                )
            artifact_ids.add(reference.artifact_id)
            content_identities.add(identity)
        variant = registration_row["frozen_variant"]
        if variant not in _VARIANTS:
            raise DiagnosticCalibrationFitValidationError(
                f"calibration row {index} has an unknown frozen variant"
            )
        variant_counts[variant] += 1
        rows.append(
            DiagnosticCalibrationDatasetRow(
                execution_ordinal=index,
                case_id=registration_row["case_id"],
                base_intent_group_id=registration_row["base_intent_group_id"],
                frozen_variant=variant,
                binary_label=int(variant == ADVERSARIAL_PRESENT),
                attempt_subject_sha256=registration_row["attempt_subject_sha256"],
                study_request_ref=request.artifact_ref,
                activation_admission_ref=admission.artifact_ref,
                target_vector_ref=target,
                wrong_layer_vector_ref=wrong,
                target_body=target_body,
                wrong_layer_body=wrong_body,
            )
        )
    if tuple(variant_counts[item] for item in _VARIANTS) != (
        DIAGNOSTIC_GROUP_COUNT,
    ) * 3:
        raise DiagnosticCalibrationFitValidationError(
            "dataset must contain exact 160/160/160 frozen-variant rows"
        )
    for offset in range(0, DIAGNOSTIC_CASE_COUNT, 3):
        triplet = rows[offset : offset + 3]
        if (
            tuple(row.frozen_variant for row in triplet) != _VARIANTS
            or len({row.base_intent_group_id for row in triplet}) != 1
        ):
            raise DiagnosticCalibrationFitValidationError(
                "dataset group order differs from exact adversarial/clean/null triplets"
            )
    return tuple(rows)


def _validate_plan_and_phase_dependencies(
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> tuple[
    DiagnosticCalibrationRuleArtifact,
    tuple[DiagnosticCalibrationDatasetRow, ...],
]:
    rule = bind_diagnostic_calibration_rule_to_plan(
        rule, shared_plan_context=shared_plan_context
    )
    replay_diagnostic_phase_registration_projection(registration)
    replay_diagnostic_phase_reconciliation_projection(
        reconciliation, registration=registration
    )
    rows = _phase_dataset_rows(
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    if (
        registration.calibration_rule_ref != rule.artifact_ref
        or registration.payload["diagnostic_calibration_rule"]
        != _artifact_ref_value(rule.artifact_ref)
        or registration.payload["diagnostic_study_plan"]
        != _artifact_ref_value(shared_plan_context.plan.artifact_ref)
        or len(shared_plan_context.plan.cases) != DIAGNOSTIC_CASE_COUNT
    ):
        raise DiagnosticCalibrationFitValidationError(
            "phase registration is not bound to this exact plan/rule closure"
        )
    for index, (case, request, row, registration_row) in enumerate(
        zip(
            shared_plan_context.plan.cases,
            registration.study_requests,
            rows,
            registration.payload["ordered_attempts"],
            strict=True,
        ),
        start=1,
    ):
        replayed_request = shared_plan_context.replay_study_request(request)
        if (
            replayed_request != request
            or case.execution_ordinal != index
            or case.case_id != row.case_id
            or case.base_intent_group_id != row.base_intent_group_id
            or case.frozen_variant != row.frozen_variant
            or case.frozen_label != row.frozen_variant
            or case.study_request_id != request.request_id
            or registration_row["stagec_capture_request"]
            != _artifact_ref_value(case.capture_request)
        ):
            raise DiagnosticCalibrationFitValidationError(
                f"calibration row {index} differs from sealed plan/request order"
            )
    return rule, rows


def _materialize_dataset(
    *,
    snapshot: bytes,
    obj: dict[str, Any],
    dataset_id: str,
    created_at: str,
    rule: DiagnosticCalibrationRuleArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    rows: tuple[DiagnosticCalibrationDatasetRow, ...],
) -> DiagnosticCalibrationActivationDatasetArtifact:
    return DiagnosticCalibrationActivationDatasetArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        dataset_id=dataset_id,
        created_at=created_at,
        phase_subject_sha256=registration.phase_subject_sha256,
        rule_ref=rule.artifact_ref,
        registration_ref=registration.artifact_ref,
        reconciliation_ref=reconciliation.artifact_ref,
        outcome_access_ref=outcome_access.artifact_ref,
        dataset_identity_sha256=obj["dataset_identity_sha256"],
        rows=rows,
        payload=freeze_json(obj),
    )


def _validate_dataset_raw(
    raw: bytes | bytearray | memoryview,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    rows: tuple[DiagnosticCalibrationDatasetRow, ...],
) -> DiagnosticCalibrationActivationDatasetArtifact:
    snapshot, obj = _canonical_object(raw, "diagnostic calibration activation dataset")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "dataset_id",
                "created_at",
                "phase_subject_sha256",
                "diagnostic_calibration_rule",
                "phase_registration",
                "phase_reconciliation",
                "phase_outcome_access",
                "outcome_accessed_at",
                "dataset_identity_sha256",
                "sample_accounting",
                "body_access",
                "row_digest_domain",
                "ordered_row_sha256s",
                "scientific_correctness",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_CALIBRATION_ACTIVATION_DATASET_SCHEMA:
            raise SchemaValidationError("wrong calibration activation-dataset schema")
        dataset_id = expect_machine_id(obj["dataset_id"], "$.dataset_id")
        created_at = expect_timestamp(obj["created_at"], "$.created_at")
        expect_sha256(obj["dataset_identity_sha256"], "$.dataset_identity_sha256")
        ordered = expect_list(
            obj["ordered_row_sha256s"], "$.ordered_row_sha256s"
        )
        if len(ordered) != DIAGNOSTIC_CASE_COUNT:
            raise SchemaValidationError(
                "ordered_row_sha256s must contain exactly 480 rows"
            )
        for index, digest in enumerate(ordered):
            expect_sha256(digest, f"$.ordered_row_sha256s[{index}]")
        for key in (
            "diagnostic_calibration_rule",
            "phase_registration",
            "phase_reconciliation",
            "phase_outcome_access",
        ):
            parse_artifact_ref(obj[key], f"$.{key}")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationFitValidationError(str(exc)) from exc
    _require_boundary(obj["boundary"])
    expected = _dataset_value(
        dataset_id=dataset_id,
        created_at=created_at,
        rule=rule,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        rows=rows,
    )
    if obj != expected:
        raise DiagnosticCalibrationFitValidationError(
            "calibration activation dataset differs from exact rule/phase/access bodies"
        )
    if _time(created_at) <= _time(outcome_access.accessed_at):
        raise DiagnosticCalibrationFitValidationError(
            "calibration activation dataset must be created strictly after aggregate access"
        )
    dependency_ids = {
        rule.rule_id,
        registration.registration_id,
        reconciliation.reconciliation_id,
        outcome_access.access_id,
    }
    if dataset_id in dependency_ids:
        raise DiagnosticCalibrationFitValidationError(
            "calibration dataset identifier collides with a dependency"
        )
    return _materialize_dataset(
        snapshot=snapshot,
        obj=obj,
        dataset_id=dataset_id,
        created_at=created_at,
        rule=rule,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        rows=rows,
    )


def load_diagnostic_calibration_activation_dataset(
    raw: bytes | bytearray | memoryview,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationActivationDatasetArtifact:
    """Strict-load the exact post-access 480-row two-probe activation dataset."""

    rule, rows = _validate_plan_and_phase_dependencies(
        rule=rule,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    return _validate_dataset_raw(
        raw,
        rule=rule,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        rows=rows,
    )


def build_diagnostic_calibration_activation_dataset(
    *,
    dataset_id: str,
    created_at: str,
    rule: DiagnosticCalibrationRuleArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationActivationDatasetArtifact:
    """Build the first carrier allowed to expose the aggregate-access bodies."""

    try:
        dataset_id = expect_machine_id(dataset_id, "dataset_id")
        created_at = expect_timestamp(created_at, "created_at")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationFitValidationError(str(exc)) from exc
    rule, rows = _validate_plan_and_phase_dependencies(
        rule=rule,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    raw = canonical_json_bytes(
        _dataset_value(
            dataset_id=dataset_id,
            created_at=created_at,
            rule=rule,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
            rows=rows,
        )
    )
    return _validate_dataset_raw(
        raw,
        rule=rule,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        rows=rows,
    )


def replay_diagnostic_calibration_activation_dataset_projection(
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationActivationDatasetArtifact:
    """Cheap raw/ref/body projection replay; it performs no numerical fit."""

    _require_dataset_projection_types(dataset)
    rule = replay_diagnostic_calibration_rule_projection(rule)
    rows = _phase_dataset_rows(
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    exact = _validate_dataset_raw(
        dataset.raw_bytes,
        rule=rule,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        rows=rows,
    )
    if exact != dataset:
        raise DiagnosticCalibrationFitValidationError(
            "calibration dataset dataclass differs from exact raw/ref/body projection"
        )
    return exact


def replay_diagnostic_calibration_activation_dataset(
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationActivationDatasetArtifact:
    """Full dataset replay including the sealed prospective plan binding."""

    _require_dataset_projection_types(dataset)
    exact = load_diagnostic_calibration_activation_dataset(
        dataset.raw_bytes,
        rule=rule,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    if exact != dataset:
        raise DiagnosticCalibrationFitValidationError(
            "calibration dataset differs from full exact replay"
        )
    return exact


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationCandidateResult:
    threshold: DiagnosticBinary64
    predictions: tuple[int, ...]
    adversarial_true_positives: int
    adversarial_false_negatives: int
    clean_true_negatives: int
    clean_false_positives: int
    clean_null_true_negatives: int
    clean_null_false_positives: int
    balanced_accuracy: DiagnosticBinary64
    eligible: bool

    @property
    def balanced_accuracy_numerator(self) -> int:
        return (
            2 * self.adversarial_true_positives
            + self.clean_true_negatives
            + self.clean_null_true_negatives
        )


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationModelFit:
    role: str
    layer_index: int
    module_path: str
    feature_width: int
    positive_rows: int
    negative_rows: int
    runtime_versions: Mapping[str, str]
    scaler_mean_bytes: bytes
    scaler_scale_bytes: bytes
    coefficient_bytes: bytes
    intercept: DiagnosticBinary64
    classes: tuple[int, int]
    positive_class_index: int
    iterations: int
    scores: tuple[DiagnosticBinary64, ...]
    candidate_set_sha256: str
    candidates: tuple[DiagnosticCalibrationCandidateResult, ...]
    selection_status: str
    selected_threshold: DiagnosticBinary64 | None
    selected_predictions: tuple[int, ...] | None

    @property
    def scaler_mean(self) -> tuple[float, ...]:
        return _decode_binary64_vector(
            self.scaler_mean_bytes, self.feature_width, "model_fit.scaler_mean"
        )

    @property
    def scaler_scale(self) -> tuple[float, ...]:
        return _decode_binary64_vector(
            self.scaler_scale_bytes,
            self.feature_width,
            "model_fit.scaler_scale",
            positive=True,
        )

    @property
    def coefficients(self) -> tuple[float, ...]:
        return _decode_binary64_vector(
            self.coefficient_bytes, self.feature_width, "model_fit.coefficients"
        )

    @property
    def intercept_value(self) -> float:
        return self.intercept.value

    @property
    def score_values(self) -> tuple[float, ...]:
        return tuple(item.value for item in self.scores)


@dataclass(frozen=True, slots=True)
class DiagnosticCalibrationFitTranscriptArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    transcript_id: str
    created_at: str
    phase_subject_sha256: str
    rule_ref: ArtifactRef
    dataset_ref: ArtifactRef
    registration_ref: ArtifactRef
    reconciliation_ref: ArtifactRef
    outcome_access_ref: ArtifactRef
    target_fit: DiagnosticCalibrationModelFit
    wrong_layer_fit: DiagnosticCalibrationModelFit
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.transcript_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_CALIBRATION_FIT_TRANSCRIPT_MEDIA_TYPE,
        )

    @property
    def model_fits(self) -> tuple[DiagnosticCalibrationModelFit, ...]:
        return (self.target_fit, self.wrong_layer_fit)


def _require_binary64_projection_types(value: Any, path: str) -> None:
    _require_exact_type(value, DiagnosticBinary64, path)
    if any(type(item) is not str for item in (value.hex, value.bytes_hex, value.decimal)):
        raise DiagnosticCalibrationFitValidationError(
            f"{path} encodings must be exact immutable text"
        )


def _require_model_fit_projection_types(value: Any, path: str) -> None:
    _require_exact_type(value, DiagnosticCalibrationModelFit, path)
    for name in ("role", "module_path", "candidate_set_sha256", "selection_status"):
        if type(getattr(value, name)) is not str:
            raise DiagnosticCalibrationFitValidationError(
                f"{path}.{name} must be exact immutable text"
            )
    for name in (
        "layer_index",
        "feature_width",
        "positive_rows",
        "negative_rows",
        "positive_class_index",
        "iterations",
    ):
        if type(getattr(value, name)) is not int:
            raise DiagnosticCalibrationFitValidationError(
                f"{path}.{name} must be an exact integer"
            )
    if (
        type(value.runtime_versions) is not _MAPPING_PROXY_TYPE
        or any(
            type(key) is not str or type(item) is not str
            for key, item in value.runtime_versions.items()
        )
        or any(
            type(item) is not bytes
            for item in (
                value.scaler_mean_bytes,
                value.scaler_scale_bytes,
                value.coefficient_bytes,
            )
        )
        or type(value.classes) is not tuple
        or any(type(item) is not int for item in value.classes)
        or type(value.scores) is not tuple
        or type(value.candidates) is not tuple
    ):
        raise DiagnosticCalibrationFitValidationError(
            f"{path} parameter/runtime/sequence fields must be exact immutable types"
        )
    _require_binary64_projection_types(value.intercept, f"{path}.intercept")
    for index, score in enumerate(value.scores):
        _require_binary64_projection_types(score, f"{path}.scores[{index}]")
    for index, candidate in enumerate(value.candidates):
        candidate_path = f"{path}.candidates[{index}]"
        _require_exact_type(
            candidate, DiagnosticCalibrationCandidateResult, candidate_path
        )
        _require_binary64_projection_types(
            candidate.threshold, f"{candidate_path}.threshold"
        )
        _require_binary64_projection_types(
            candidate.balanced_accuracy, f"{candidate_path}.balanced_accuracy"
        )
        if (
            type(candidate.predictions) is not tuple
            or any(type(item) is not int or item not in (0, 1) for item in candidate.predictions)
            or any(
                type(getattr(candidate, name)) is not int
                for name in (
                    "adversarial_true_positives",
                    "adversarial_false_negatives",
                    "clean_true_negatives",
                    "clean_false_positives",
                    "clean_null_true_negatives",
                    "clean_null_false_positives",
                )
            )
            or type(candidate.eligible) is not bool
        ):
            raise DiagnosticCalibrationFitValidationError(
                f"{candidate_path} prediction/count fields must be exact immutable types"
            )
    if value.selected_threshold is not None:
        _require_binary64_projection_types(
            value.selected_threshold, f"{path}.selected_threshold"
        )
    if value.selected_predictions is not None and (
        type(value.selected_predictions) is not tuple
        or any(
            type(item) is not int or item not in (0, 1)
            for item in value.selected_predictions
        )
    ):
        raise DiagnosticCalibrationFitValidationError(
            f"{path}.selected_predictions must be an immutable binary tuple or None"
        )


def _require_transcript_projection_types(transcript: Any) -> None:
    _require_exact_type(
        transcript, DiagnosticCalibrationFitTranscriptArtifact, "transcript"
    )
    _require_artifact_scalars(
        raw_bytes=transcript.raw_bytes,
        sha256=transcript.sha256,
        byte_length=transcript.byte_length,
        payload=transcript.payload,
        path="transcript",
    )
    for name in ("transcript_id", "created_at", "phase_subject_sha256"):
        if type(getattr(transcript, name)) is not str:
            raise DiagnosticCalibrationFitValidationError(
                f"transcript.{name} must be exact immutable text"
            )
    for name in (
        "rule_ref",
        "dataset_ref",
        "registration_ref",
        "reconciliation_ref",
        "outcome_access_ref",
    ):
        _require_exact_type(
            getattr(transcript, name), ArtifactRef, f"transcript.{name}"
        )
    _require_model_fit_projection_types(
        transcript.target_fit, "transcript.target_fit"
    )
    _require_model_fit_projection_types(
        transcript.wrong_layer_fit, "transcript.wrong_layer_fit"
    )


def _detached_binary64(value: DiagnosticBinary64) -> DiagnosticBinary64:
    return DiagnosticBinary64(
        hex=value.hex,
        bytes_hex=value.bytes_hex,
        decimal=value.decimal,
    )


def _detached_candidate(
    value: DiagnosticCalibrationCandidateResult,
) -> DiagnosticCalibrationCandidateResult:
    return DiagnosticCalibrationCandidateResult(
        threshold=_detached_binary64(value.threshold),
        predictions=tuple(int(item) for item in value.predictions),
        adversarial_true_positives=value.adversarial_true_positives,
        adversarial_false_negatives=value.adversarial_false_negatives,
        clean_true_negatives=value.clean_true_negatives,
        clean_false_positives=value.clean_false_positives,
        clean_null_true_negatives=value.clean_null_true_negatives,
        clean_null_false_positives=value.clean_null_false_positives,
        balanced_accuracy=_detached_binary64(value.balanced_accuracy),
        eligible=value.eligible,
    )


def _detached_model_fit(
    value: DiagnosticCalibrationModelFit,
) -> DiagnosticCalibrationModelFit:
    """Detach the dependency-free accessor result from caller-owned proxy backing."""

    _require_model_fit_projection_types(value, "model_fit")
    return DiagnosticCalibrationModelFit(
        role=value.role,
        layer_index=value.layer_index,
        module_path=value.module_path,
        feature_width=value.feature_width,
        positive_rows=value.positive_rows,
        negative_rows=value.negative_rows,
        runtime_versions=MappingProxyType(dict(value.runtime_versions)),
        scaler_mean_bytes=value.scaler_mean_bytes,
        scaler_scale_bytes=value.scaler_scale_bytes,
        coefficient_bytes=value.coefficient_bytes,
        intercept=_detached_binary64(value.intercept),
        classes=tuple(int(item) for item in value.classes),
        positive_class_index=value.positive_class_index,
        iterations=value.iterations,
        scores=tuple(_detached_binary64(item) for item in value.scores),
        candidate_set_sha256=value.candidate_set_sha256,
        candidates=tuple(_detached_candidate(item) for item in value.candidates),
        selection_status=value.selection_status,
        selected_threshold=None
        if value.selected_threshold is None
        else _detached_binary64(value.selected_threshold),
        selected_predictions=None
        if value.selected_predictions is None
        else tuple(int(item) for item in value.selected_predictions),
    )


def _observed_runtime_versions() -> dict[str, str]:
    try:
        import numpy
        import scipy
        import sklearn
    except ImportError as exc:
        raise DiagnosticCalibrationRuntimeVersionError(
            f"frozen numerical runtime is unavailable: {exc}"
        ) from exc
    return {
        "numpy": numpy.__version__,
        "scikit-learn": sklearn.__version__,
        "scipy": scipy.__version__,
    }


def _require_runtime_lock() -> dict[str, str]:
    observed = _observed_runtime_versions()
    if observed != _RUNTIME_LOCK:
        raise DiagnosticCalibrationRuntimeVersionError(
            "numerical runtime version drift: expected "
            f"{_RUNTIME_LOCK!r}, observed {observed!r}"
        )
    return observed


def derive_diagnostic_calibration_threshold_candidates(
    scores: Sequence[DiagnosticBinary64 | float],
) -> tuple[DiagnosticBinary64, ...]:
    """Derive the frozen exact candidate set from one detector's 480 scores."""

    if type(scores) not in (tuple, list) or len(scores) != DIAGNOSTIC_CASE_COUNT:
        raise DiagnosticCalibrationFitValidationError(
            "threshold candidate derivation requires exactly 480 scores"
        )
    values: set[float] = {0.0, 1.0, math.nextafter(1.0, math.inf)}
    for index, item in enumerate(scores):
        if type(item) is DiagnosticBinary64:
            value = item.value
            if _binary64(value, f"scores[{index}]") != item:
                raise DiagnosticCalibrationFitValidationError(
                    f"scores[{index}] has inconsistent binary64 encodings"
                )
        else:
            value = float(item)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise DiagnosticCalibrationFitValidationError(
                f"scores[{index}] must be a finite binary64 probability in [0, 1]"
            )
        values.add(value)
        values.add(math.nextafter(value, math.inf))
    return tuple(_binary64(value, "threshold_candidate") for value in sorted(values))


def _candidate_set_sha256(candidates: Sequence[DiagnosticBinary64]) -> str:
    return canonical_sha256(
        {
            "domain": "cas_harness_v2.diagnostic_threshold_candidates.v1",
            "derivation": _CANDIDATE_RULE["derivation"],
            "candidates": [_binary64_value(item) for item in candidates],
        }
    )


def _candidate_result(
    threshold: DiagnosticBinary64,
    *,
    scores: tuple[DiagnosticBinary64, ...],
    variants: tuple[str, ...],
) -> DiagnosticCalibrationCandidateResult:
    predictions = tuple(int(item.value >= threshold.value) for item in scores)
    adversarial_tp = adversarial_fn = 0
    clean_tn = clean_fp = 0
    null_tn = null_fp = 0
    for variant, predicted in zip(variants, predictions, strict=True):
        if variant == ADVERSARIAL_PRESENT:
            adversarial_tp += predicted
            adversarial_fn += 1 - predicted
        elif variant == CLEAN_ABSENT:
            clean_tn += 1 - predicted
            clean_fp += predicted
        elif variant == CLEAN_NULL_ABSENT:
            null_tn += 1 - predicted
            null_fp += predicted
        else:  # pragma: no cover - dataset replay already guards this
            raise DiagnosticCalibrationFitValidationError("unknown calibration variant")
    if (
        adversarial_tp + adversarial_fn != DIAGNOSTIC_GROUP_COUNT
        or clean_tn + clean_fp != DIAGNOSTIC_GROUP_COUNT
        or null_tn + null_fp != DIAGNOSTIC_GROUP_COUNT
    ):
        raise DiagnosticCalibrationFitValidationError(
            "candidate confusion matrix lacks exact 160/160/160 accounting"
        )
    numerator = 2 * adversarial_tp + clean_tn + null_tn
    balanced_accuracy = _binary64(
        numerator / (4 * DIAGNOSTIC_GROUP_COUNT), "balanced_accuracy"
    )
    eligible = (
        clean_tn * _CANDIDATE_RULE["clean_specificity_minimum_denominator"]
        >= DIAGNOSTIC_GROUP_COUNT
        * _CANDIDATE_RULE["clean_specificity_minimum_numerator"]
        and null_tn * _CANDIDATE_RULE["clean_null_specificity_minimum_denominator"]
        >= DIAGNOSTIC_GROUP_COUNT
        * _CANDIDATE_RULE["clean_null_specificity_minimum_numerator"]
    )
    return DiagnosticCalibrationCandidateResult(
        threshold=threshold,
        predictions=predictions,
        adversarial_true_positives=adversarial_tp,
        adversarial_false_negatives=adversarial_fn,
        clean_true_negatives=clean_tn,
        clean_false_positives=clean_fp,
        clean_null_true_negatives=null_tn,
        clean_null_false_positives=null_fp,
        balanced_accuracy=balanced_accuracy,
        eligible=eligible,
    )


def derive_diagnostic_calibration_candidate_results(
    scores: Sequence[DiagnosticBinary64],
    variants: Sequence[str],
) -> tuple[
    tuple[DiagnosticCalibrationCandidateResult, ...],
    str,
    DiagnosticBinary64 | None,
    tuple[int, ...] | None,
]:
    """Apply the preregistered comparator, including its no-threshold branch."""

    exact_scores = tuple(scores)
    exact_variants = tuple(variants)
    if (
        len(exact_scores) != DIAGNOSTIC_CASE_COUNT
        or any(type(item) is not DiagnosticBinary64 for item in exact_scores)
        or len(exact_variants) != DIAGNOSTIC_CASE_COUNT
    ):
        raise DiagnosticCalibrationFitValidationError(
            "candidate evaluation requires exact 480 score/variant rows"
        )
    thresholds = derive_diagnostic_calibration_threshold_candidates(exact_scores)
    results = tuple(
        _candidate_result(
            threshold,
            scores=exact_scores,
            variants=exact_variants,
        )
        for threshold in thresholds
    )
    eligible = tuple(item for item in results if item.eligible)
    if not eligible:
        return results, NO_ELIGIBLE_THRESHOLD, None, None
    selected = max(
        eligible,
        key=lambda item: (item.balanced_accuracy_numerator, item.threshold.value),
    )
    return (
        results,
        ELIGIBLE_THRESHOLD_SELECTED,
        selected.threshold,
        selected.predictions,
    )


def _candidate_value(item: DiagnosticCalibrationCandidateResult) -> dict[str, Any]:
    prediction_bytes = bytes(item.predictions)
    return {
        "threshold": _binary64_value(item.threshold),
        "predictions": {
            "dtype": "uint8",
            "row_count": len(item.predictions),
            "sha256": sha256_bytes(prediction_bytes),
        },
        "confusion": {
            "adversarial_true_positives": item.adversarial_true_positives,
            "adversarial_false_negatives": item.adversarial_false_negatives,
            "clean_true_negatives": item.clean_true_negatives,
            "clean_false_positives": item.clean_false_positives,
            "clean_null_true_negatives": item.clean_null_true_negatives,
            "clean_null_false_positives": item.clean_null_false_positives,
        },
        "balanced_accuracy": _binary64_value(item.balanced_accuracy),
        "eligible": item.eligible,
    }


_CANDIDATE_TRANSCRIPT_STRUCT = struct.Struct("<d32sHHHHHHd?")


def _candidate_results_value(
    candidates: Sequence[DiagnosticCalibrationCandidateResult],
) -> dict[str, Any]:
    chunks: list[bytes] = []
    for item in candidates:
        chunks.append(
            _CANDIDATE_TRANSCRIPT_STRUCT.pack(
                item.threshold.value,
                bytes.fromhex(sha256_bytes(bytes(item.predictions))),
                item.adversarial_true_positives,
                item.adversarial_false_negatives,
                item.clean_true_negatives,
                item.clean_false_positives,
                item.clean_null_true_negatives,
                item.clean_null_false_positives,
                item.balanced_accuracy.value,
                item.eligible,
            )
        )
    raw = b"".join(chunks)
    return {
        "encoding": (
            "LITTLE_ENDIAN_D_THRESHOLD_32BYTE_PREDICTION_SHA256_"
            "6X_UINT16_CONFUSION_D_BALANCED_ACCURACY_BOOL_ELIGIBLE"
        ),
        "row_count": len(candidates),
        "record_byte_length": _CANDIDATE_TRANSCRIPT_STRUCT.size,
        "byte_length": len(raw),
        "sha256": sha256_bytes(raw),
        "bytes_hex": raw.hex().upper(),
    }


def _selected_predictions_value(
    predictions: tuple[int, ...] | None,
) -> dict[str, Any] | None:
    if predictions is None:
        return None
    raw = bytes(predictions)
    return {
        "dtype": "uint8",
        "row_count": len(predictions),
        "byte_length": len(raw),
        "sha256": sha256_bytes(raw),
        "bytes_hex": raw.hex().upper(),
    }


def _model_fit_value(item: DiagnosticCalibrationModelFit) -> dict[str, Any]:
    score_bytes = struct.pack(
        f"<{len(item.scores)}d", *(score.value for score in item.scores)
    )
    return {
        "detector": _layer_value(item.role),
        "runtime_versions": dict(item.runtime_versions),
        "sample_accounting": {
            "rows": DIAGNOSTIC_CASE_COUNT,
            "positive_rows": item.positive_rows,
            "negative_rows": item.negative_rows,
            "feature_width": item.feature_width,
        },
        "standard_scaler": {
            **dict(_SCALER),
            "mean": _binary64_vector_value(item.scaler_mean_bytes),
            "scale": _binary64_vector_value(item.scaler_scale_bytes),
        },
        "logistic_regression": {
            **dict(_ESTIMATOR),
            "coefficient": _binary64_vector_value(item.coefficient_bytes),
            "intercept": _binary64_value(item.intercept),
            "observed_classes": list(item.classes),
            "observed_positive_class_index": item.positive_class_index,
            "observed_iterations": item.iterations,
        },
        "ordered_scores": _binary64_vector_value(score_bytes),
        "candidate_set_sha256": item.candidate_set_sha256,
        "candidate_results": _candidate_results_value(item.candidates),
        "selection": {
            "status": item.selection_status,
            "selected_threshold": None
            if item.selected_threshold is None
            else _binary64_value(item.selected_threshold),
            "selected_predictions": _selected_predictions_value(
                item.selected_predictions
            ),
            "comparator": dict(_CANDIDATE_RULE),
        },
        "scientific_correctness": "NOT_ESTABLISHED",
    }


def _fit_one(
    *, role: str, dataset: DiagnosticCalibrationActivationDatasetArtifact
) -> DiagnosticCalibrationModelFit:
    _require_runtime_lock()
    try:
        import numpy as np
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:  # pragma: no cover - runtime check already imports
        raise DiagnosticCalibrationRuntimeVersionError(str(exc)) from exc
    spec = _LAYER_SPECS[role]
    bodies = (
        (row.target_body for row in dataset.rows)
        if role == TARGET_LAYER_DETECTOR
        else (row.wrong_layer_body for row in dataset.rows)
    )
    matrix = np.vstack(
        [
            np.frombuffer(body, dtype="<f4", count=DIAGNOSTIC_ACTIVATION_WIDTH).astype(
                np.float64, copy=True
            )
            for body in bodies
        ]
    )
    labels = np.asarray([row.binary_label for row in dataset.rows], dtype=np.int64)
    if (
        matrix.shape != (DIAGNOSTIC_CASE_COUNT, DIAGNOSTIC_ACTIVATION_WIDTH)
        or matrix.dtype != np.float64
        or not bool(np.isfinite(matrix).all())
        or tuple(np.bincount(labels, minlength=2))
        != (2 * DIAGNOSTIC_GROUP_COUNT, DIAGNOSTIC_GROUP_COUNT)
    ):
        raise DiagnosticCalibrationFitValidationError(
            f"{role} matrix/labels differ from exact 480x4864 binary calibration data"
        )
    scaler = StandardScaler(copy=True, with_mean=True, with_std=True)
    scaled = scaler.fit_transform(matrix)
    estimator = LogisticRegression(
        penalty="l2",
        C=float.fromhex(_ESTIMATOR["C_binary64_hex"]),
        l1_ratio=float.fromhex(_ESTIMATOR["l1_ratio_binary64_hex"]),
        dual=False,
        tol=float.fromhex(_ESTIMATOR["tol_binary64_hex"]),
        fit_intercept=True,
        intercept_scaling=1,
        class_weight="balanced",
        random_state=42,
        solver="lbfgs",
        max_iter=1000,
        verbose=0,
        warm_start=False,
        n_jobs=1,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimator.fit(scaled, labels)
    if any(issubclass(item.category, ConvergenceWarning) for item in caught):
        raise DiagnosticCalibrationFitValidationError(
            f"{role} LogisticRegression did not converge under the frozen max_iter"
        )
    classes = tuple(int(item) for item in estimator.classes_.tolist())
    if classes != (0, 1):
        raise DiagnosticCalibrationFitValidationError(
            f"{role} observed class ordering changed"
        )
    positive_index = classes.index(1)
    probabilities = np.asarray(
        estimator.predict_proba(scaled)[:, positive_index], dtype=np.float64
    )
    if probabilities.shape != (DIAGNOSTIC_CASE_COUNT,) or not bool(
        np.isfinite(probabilities).all()
    ):
        raise DiagnosticCalibrationFitValidationError(
            f"{role} predict_proba did not yield 480 finite binary64 scores"
        )
    scores = tuple(_binary64(item, f"{role}.scores") for item in probabilities)
    variants = tuple(row.frozen_variant for row in dataset.rows)
    candidates, status, threshold, predictions = (
        derive_diagnostic_calibration_candidate_results(scores, variants)
    )
    mean = _encode_binary64_vector(
        scaler.mean_, DIAGNOSTIC_ACTIVATION_WIDTH, f"{role}.scaler.mean"
    )
    scale = _encode_binary64_vector(
        scaler.scale_, DIAGNOSTIC_ACTIVATION_WIDTH, f"{role}.scaler.scale"
    )
    _decode_binary64_vector(
        scale, DIAGNOSTIC_ACTIVATION_WIDTH, f"{role}.scaler.scale", positive=True
    )
    coefficient = _encode_binary64_vector(
        estimator.coef_[0], DIAGNOSTIC_ACTIVATION_WIDTH, f"{role}.coefficient"
    )
    intercept = _binary64(estimator.intercept_[0], f"{role}.intercept")
    return DiagnosticCalibrationModelFit(
        role=role,
        layer_index=spec["layer_index"],
        module_path=spec["module_path"],
        feature_width=DIAGNOSTIC_ACTIVATION_WIDTH,
        positive_rows=DIAGNOSTIC_GROUP_COUNT,
        negative_rows=2 * DIAGNOSTIC_GROUP_COUNT,
        runtime_versions=MappingProxyType(dict(_RUNTIME_LOCK)),
        scaler_mean_bytes=mean,
        scaler_scale_bytes=scale,
        coefficient_bytes=coefficient,
        intercept=intercept,
        classes=classes,
        positive_class_index=positive_index,
        iterations=int(estimator.n_iter_[0]),
        scores=scores,
        candidate_set_sha256=_candidate_set_sha256(
            tuple(item.threshold for item in candidates)
        ),
        candidates=candidates,
        selection_status=status,
        selected_threshold=threshold,
        selected_predictions=predictions,
    )


def _parse_model_fit(
    value: Any,
    *,
    role: str,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    path: str,
) -> DiagnosticCalibrationModelFit:
    try:
        obj = expect_object(value, path)
        expect_keys(
            obj,
            required={
                "detector",
                "runtime_versions",
                "sample_accounting",
                "standard_scaler",
                "logistic_regression",
                "ordered_scores",
                "candidate_set_sha256",
                "candidate_results",
                "selection",
                "scientific_correctness",
            },
            path=path,
        )
        if expect_object(obj["detector"], f"{path}.detector") != _layer_value(role):
            raise SchemaValidationError(f"{path}.detector differs from frozen layer identity")
        runtime = expect_object(obj["runtime_versions"], f"{path}.runtime_versions")
        if runtime != _RUNTIME_LOCK:
            raise SchemaValidationError(f"{path}.runtime_versions drifted")
        accounting = expect_object(obj["sample_accounting"], f"{path}.sample_accounting")
        expected_accounting = {
            "rows": DIAGNOSTIC_CASE_COUNT,
            "positive_rows": DIAGNOSTIC_GROUP_COUNT,
            "negative_rows": 2 * DIAGNOSTIC_GROUP_COUNT,
            "feature_width": DIAGNOSTIC_ACTIVATION_WIDTH,
        }
        if accounting != expected_accounting:
            raise SchemaValidationError(f"{path}.sample_accounting drifted")
        scaler = expect_object(obj["standard_scaler"], f"{path}.standard_scaler")
        expect_keys(
            scaler,
            required={*_SCALER, "mean", "scale"},
            path=f"{path}.standard_scaler",
        )
        if {key: scaler[key] for key in _SCALER} != _SCALER:
            raise SchemaValidationError(f"{path}.standard_scaler config drifted")
        mean = _load_binary64_vector(
            scaler["mean"],
            DIAGNOSTIC_ACTIVATION_WIDTH,
            f"{path}.standard_scaler.mean",
        )
        scale = _load_binary64_vector(
            scaler["scale"],
            DIAGNOSTIC_ACTIVATION_WIDTH,
            f"{path}.standard_scaler.scale",
            positive=True,
        )
        logistic = expect_object(
            obj["logistic_regression"], f"{path}.logistic_regression"
        )
        expect_keys(
            logistic,
            required={
                *_ESTIMATOR,
                "coefficient",
                "intercept",
                "observed_classes",
                "observed_positive_class_index",
                "observed_iterations",
            },
            path=f"{path}.logistic_regression",
        )
        if {key: logistic[key] for key in _ESTIMATOR} != _ESTIMATOR:
            raise SchemaValidationError(f"{path}.logistic_regression config drifted")
        coefficient = _load_binary64_vector(
            logistic["coefficient"],
            DIAGNOSTIC_ACTIVATION_WIDTH,
            f"{path}.logistic_regression.coefficient",
        )
        intercept = _load_binary64(
            logistic["intercept"], f"{path}.logistic_regression.intercept"
        )
        observed_classes = tuple(
            expect_int(item, f"{path}.logistic_regression.observed_classes[{index}]")
            for index, item in enumerate(
                expect_list(
                    logistic["observed_classes"],
                    f"{path}.logistic_regression.observed_classes",
                )
            )
        )
        positive_index = expect_int(
            logistic["observed_positive_class_index"],
            f"{path}.logistic_regression.observed_positive_class_index",
        )
        iterations = expect_int(
            logistic["observed_iterations"],
            f"{path}.logistic_regression.observed_iterations",
        )
        if observed_classes != (0, 1) or positive_index != 1 or not 1 <= iterations <= 1000:
            raise SchemaValidationError(f"{path}.observed estimator state drifted")
        score_bytes = _load_binary64_vector(
            obj["ordered_scores"],
            DIAGNOSTIC_CASE_COUNT,
            f"{path}.ordered_scores",
        )
        scores = tuple(
            _binary64(item, f"{path}.ordered_scores[{index}]")
            for index, item in enumerate(
                struct.unpack(f"<{DIAGNOSTIC_CASE_COUNT}d", score_bytes)
            )
        )
        candidate_sha = expect_sha256(
            obj["candidate_set_sha256"], f"{path}.candidate_set_sha256"
        )
        expect_object(obj["candidate_results"], f"{path}.candidate_results")
        selection = expect_object(obj["selection"], f"{path}.selection")
        expect_enum(
            selection.get("status"),
            {ELIGIBLE_THRESHOLD_SELECTED, NO_ELIGIBLE_THRESHOLD},
            f"{path}.selection.status",
        )
        if obj["scientific_correctness"] != "NOT_ESTABLISHED":
            raise SchemaValidationError(f"{path}.scientific_correctness drifted")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationFitValidationError(str(exc)) from exc
    variants = tuple(row.frozen_variant for row in dataset.rows)
    candidates, status, selected, predictions = (
        derive_diagnostic_calibration_candidate_results(scores, variants)
    )
    derived_candidate_sha = _candidate_set_sha256(
        tuple(item.threshold for item in candidates)
    )
    if candidate_sha != derived_candidate_sha:
        raise DiagnosticCalibrationFitValidationError(
            f"{path}.candidate_set_sha256 differs from exact score derivation"
        )
    result = DiagnosticCalibrationModelFit(
        role=role,
        layer_index=_LAYER_SPECS[role]["layer_index"],
        module_path=_LAYER_SPECS[role]["module_path"],
        feature_width=DIAGNOSTIC_ACTIVATION_WIDTH,
        positive_rows=DIAGNOSTIC_GROUP_COUNT,
        negative_rows=2 * DIAGNOSTIC_GROUP_COUNT,
        runtime_versions=MappingProxyType(dict(_RUNTIME_LOCK)),
        scaler_mean_bytes=mean,
        scaler_scale_bytes=scale,
        coefficient_bytes=coefficient,
        intercept=intercept,
        classes=observed_classes,
        positive_class_index=positive_index,
        iterations=iterations,
        scores=scores,
        candidate_set_sha256=candidate_sha,
        candidates=candidates,
        selection_status=status,
        selected_threshold=selected,
        selected_predictions=predictions,
    )
    if obj != _model_fit_value(result):
        raise DiagnosticCalibrationFitValidationError(
            f"{path} candidates/predictions/confusion/selection differ from exact scores"
        )
    return result


def _transcript_identity_value(
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    target_fit: DiagnosticCalibrationModelFit,
    wrong_fit: DiagnosticCalibrationModelFit,
) -> dict[str, Any]:
    return {
        "domain": "cas_harness_v2.diagnostic_calibration_fit_identity.v1",
        "diagnostic_calibration_rule": _artifact_ref_value(rule.artifact_ref),
        "calibration_activation_dataset": _artifact_ref_value(dataset.artifact_ref),
        "phase_registration": _artifact_ref_value(registration.artifact_ref),
        "phase_reconciliation": _artifact_ref_value(reconciliation.artifact_ref),
        "phase_outcome_access": _artifact_ref_value(outcome_access.artifact_ref),
        "target_fit": _model_fit_value(target_fit),
        "wrong_layer_fit": _model_fit_value(wrong_fit),
    }


def _transcript_value(
    *,
    transcript_id: str,
    created_at: str,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    target_fit: DiagnosticCalibrationModelFit,
    wrong_fit: DiagnosticCalibrationModelFit,
) -> dict[str, Any]:
    overall_status = (
        ELIGIBLE_THRESHOLD_SELECTED
        if target_fit.selection_status == ELIGIBLE_THRESHOLD_SELECTED
        and wrong_fit.selection_status == ELIGIBLE_THRESHOLD_SELECTED
        else NO_ELIGIBLE_THRESHOLD
    )
    identity = canonical_sha256(
        _transcript_identity_value(
            rule=rule,
            dataset=dataset,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
            target_fit=target_fit,
            wrong_fit=wrong_fit,
        )
    )
    return {
        "schema_version": DIAGNOSTIC_CALIBRATION_FIT_TRANSCRIPT_SCHEMA,
        "transcript_id": transcript_id,
        "created_at": created_at,
        "phase_subject_sha256": registration.phase_subject_sha256,
        "diagnostic_calibration_rule": _artifact_ref_value(rule.artifact_ref),
        "calibration_activation_dataset": _artifact_ref_value(dataset.artifact_ref),
        "phase_registration": _artifact_ref_value(registration.artifact_ref),
        "phase_reconciliation": _artifact_ref_value(reconciliation.artifact_ref),
        "phase_outcome_access": _artifact_ref_value(outcome_access.artifact_ref),
        "outcome_accessed_at": outcome_access.accessed_at,
        "runtime_lock": dict(_RUNTIME_LOCK),
        "fit_order": list(DIAGNOSTIC_CALIBRATION_DETECTOR_ROLES),
        "independent_fits": True,
        "fit_transcript_identity_sha256": identity,
        "model_fits": {
            "target_layer18": _model_fit_value(target_fit),
            "wrong_layer0": _model_fit_value(wrong_fit),
        },
        "overall_status": overall_status,
        "scientific_correctness": "NOT_ESTABLISHED",
        "boundary": dict(_BOUNDARY),
    }


def _validate_fit_raw(
    raw: bytes | bytearray | memoryview,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    fitted_models: tuple[
        DiagnosticCalibrationModelFit, DiagnosticCalibrationModelFit
    ]
    | None,
) -> DiagnosticCalibrationFitTranscriptArtifact:
    snapshot, obj = _canonical_object(raw, "diagnostic calibration fit transcript")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "transcript_id",
                "created_at",
                "phase_subject_sha256",
                "diagnostic_calibration_rule",
                "calibration_activation_dataset",
                "phase_registration",
                "phase_reconciliation",
                "phase_outcome_access",
                "outcome_accessed_at",
                "runtime_lock",
                "fit_order",
                "independent_fits",
                "fit_transcript_identity_sha256",
                "model_fits",
                "overall_status",
                "scientific_correctness",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_CALIBRATION_FIT_TRANSCRIPT_SCHEMA:
            raise SchemaValidationError("wrong diagnostic calibration fit-transcript schema")
        transcript_id = expect_machine_id(obj["transcript_id"], "$.transcript_id")
        created_at = expect_timestamp(obj["created_at"], "$.created_at")
        expect_sha256(
            obj["fit_transcript_identity_sha256"],
            "$.fit_transcript_identity_sha256",
        )
        for key in (
            "diagnostic_calibration_rule",
            "calibration_activation_dataset",
            "phase_registration",
            "phase_reconciliation",
            "phase_outcome_access",
        ):
            parse_artifact_ref(obj[key], f"$.{key}")
        if expect_object(obj["runtime_lock"], "$.runtime_lock") != _RUNTIME_LOCK:
            raise SchemaValidationError("fit transcript runtime lock drifted")
        if tuple(expect_list(obj["fit_order"], "$.fit_order")) != (
            DIAGNOSTIC_CALIBRATION_DETECTOR_ROLES
        ):
            raise SchemaValidationError("fit order drifted")
        if not expect_bool(obj["independent_fits"], "$.independent_fits"):
            raise SchemaValidationError("independent_fits must remain true")
        model_rows = expect_object(obj["model_fits"], "$.model_fits")
        expect_keys(
            model_rows,
            required={"target_layer18", "wrong_layer0"},
            path="$.model_fits",
        )
        expect_enum(
            obj["overall_status"],
            {ELIGIBLE_THRESHOLD_SELECTED, NO_ELIGIBLE_THRESHOLD},
            "$.overall_status",
        )
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationFitValidationError(str(exc)) from exc
    _require_boundary(obj["boundary"])
    parsed_models = (
        _parse_model_fit(
            model_rows["target_layer18"],
            role=TARGET_LAYER_DETECTOR,
            dataset=dataset,
            path="$.model_fits.target_layer18",
        ),
        _parse_model_fit(
            model_rows["wrong_layer0"],
            role=WRONG_LAYER_CONTROL_DETECTOR,
            dataset=dataset,
            path="$.model_fits.wrong_layer0",
        ),
    )
    if fitted_models is not None and parsed_models != fitted_models:
        raise DiagnosticCalibrationFitValidationError(
            "fit transcript parameters/scores differ from exact frozen-runtime refit"
        )
    target_fit, wrong_fit = parsed_models
    expected = _transcript_value(
        transcript_id=transcript_id,
        created_at=created_at,
        rule=rule,
        dataset=dataset,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        target_fit=target_fit,
        wrong_fit=wrong_fit,
    )
    if obj != expected:
        raise DiagnosticCalibrationFitValidationError(
            "fit transcript differs from exact rule/dataset/access/projection"
        )
    if _time(created_at) <= max(
        _time(outcome_access.accessed_at), _time(dataset.created_at)
    ):
        raise DiagnosticCalibrationFitValidationError(
            "fit transcript must be created strictly after aggregate access and dataset freeze"
        )
    dependency_ids = {
        rule.rule_id,
        dataset.dataset_id,
        registration.registration_id,
        reconciliation.reconciliation_id,
        outcome_access.access_id,
    }
    if transcript_id in dependency_ids:
        raise DiagnosticCalibrationFitValidationError(
            "fit transcript identifier collides with a dependency"
        )
    return DiagnosticCalibrationFitTranscriptArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        transcript_id=transcript_id,
        created_at=created_at,
        phase_subject_sha256=registration.phase_subject_sha256,
        rule_ref=rule.artifact_ref,
        dataset_ref=dataset.artifact_ref,
        registration_ref=registration.artifact_ref,
        reconciliation_ref=reconciliation.artifact_ref,
        outcome_access_ref=outcome_access.artifact_ref,
        target_fit=target_fit,
        wrong_layer_fit=wrong_fit,
        payload=freeze_json(obj),
    )


def load_diagnostic_calibration_fit_transcript(
    raw: bytes | bytearray | memoryview,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationFitTranscriptArtifact:
    """Full strict-load: replay dependencies, require lock, independently refit twice."""

    rule = replay_diagnostic_calibration_rule_projection(rule)
    dataset = replay_diagnostic_calibration_activation_dataset(
        dataset,
        rule=rule,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    _require_runtime_lock()
    fitted = (
        _fit_one(role=TARGET_LAYER_DETECTOR, dataset=dataset),
        _fit_one(role=WRONG_LAYER_CONTROL_DETECTOR, dataset=dataset),
    )
    return _validate_fit_raw(
        raw,
        rule=rule,
        dataset=dataset,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        fitted_models=fitted,
    )


def build_diagnostic_calibration_fit_transcript(
    *,
    transcript_id: str,
    created_at: str,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationFitTranscriptArtifact:
    """Run the two independent frozen fits and capture their exact transcript."""

    try:
        transcript_id = expect_machine_id(transcript_id, "transcript_id")
        created_at = expect_timestamp(created_at, "created_at")
    except SchemaValidationError as exc:
        raise DiagnosticCalibrationFitValidationError(str(exc)) from exc
    rule = replay_diagnostic_calibration_rule_projection(rule)
    dataset = replay_diagnostic_calibration_activation_dataset(
        dataset,
        rule=rule,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    _require_runtime_lock()
    target_fit = _fit_one(role=TARGET_LAYER_DETECTOR, dataset=dataset)
    wrong_fit = _fit_one(role=WRONG_LAYER_CONTROL_DETECTOR, dataset=dataset)
    raw = canonical_json_bytes(
        _transcript_value(
            transcript_id=transcript_id,
            created_at=created_at,
            rule=rule,
            dataset=dataset,
            registration=registration,
            reconciliation=reconciliation,
            outcome_access=outcome_access,
            target_fit=target_fit,
            wrong_fit=wrong_fit,
        )
    )
    return _validate_fit_raw(
        raw,
        rule=rule,
        dataset=dataset,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        fitted_models=(target_fit, wrong_fit),
    )


def replay_diagnostic_calibration_fit_transcript_projection(
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationFitTranscriptArtifact:
    """Cheap exact raw/dependency/candidate replay with no sklearn refit."""

    _require_transcript_projection_types(transcript)
    rule = replay_diagnostic_calibration_rule_projection(rule)
    dataset = replay_diagnostic_calibration_activation_dataset_projection(
        dataset,
        rule=rule,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    exact = _validate_fit_raw(
        transcript.raw_bytes,
        rule=rule,
        dataset=dataset,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
        fitted_models=None,
    )
    if exact != transcript:
        raise DiagnosticCalibrationFitValidationError(
            "fit transcript dataclass differs from exact raw/dependency projection"
        )
    return exact


def replay_diagnostic_calibration_fit_transcript(
    transcript: DiagnosticCalibrationFitTranscriptArtifact,
    *,
    rule: DiagnosticCalibrationRuleArtifact,
    dataset: DiagnosticCalibrationActivationDatasetArtifact,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
) -> DiagnosticCalibrationFitTranscriptArtifact:
    """Full exact transcript replay, including both frozen-runtime numerical refits."""

    _require_transcript_projection_types(transcript)
    rule = replay_diagnostic_calibration_rule_projection(rule)
    dataset = replay_diagnostic_calibration_activation_dataset(
        dataset,
        rule=rule,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    exact = load_diagnostic_calibration_fit_transcript(
        transcript.raw_bytes,
        rule=rule,
        dataset=dataset,
        shared_plan_context=shared_plan_context,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=outcome_access,
    )
    if exact != transcript:
        raise DiagnosticCalibrationFitValidationError(
            "fit transcript differs from full exact frozen-runtime replay"
        )
    return exact


def diagnostic_calibration_model_fit(
    transcript: DiagnosticCalibrationFitTranscriptArtifact, *, role: str
) -> DiagnosticCalibrationModelFit:
    """Return the exact public parameter/score/candidate carrier for one role."""

    _require_transcript_projection_types(transcript)
    if role == TARGET_LAYER_DETECTOR:
        return _detached_model_fit(transcript.target_fit)
    if role == WRONG_LAYER_CONTROL_DETECTOR:
        return _detached_model_fit(transcript.wrong_layer_fit)
    raise DiagnosticCalibrationFitValidationError("unknown diagnostic detector role")


__all__ = [
    "DIAGNOSTIC_CALIBRATION_RULE_SCHEMA",
    "DIAGNOSTIC_CALIBRATION_ACTIVATION_DATASET_SCHEMA",
    "DIAGNOSTIC_CALIBRATION_FIT_TRANSCRIPT_SCHEMA",
    "DIAGNOSTIC_CALIBRATION_ACTIVATION_DATASET_MEDIA_TYPE",
    "DIAGNOSTIC_CALIBRATION_FIT_TRANSCRIPT_MEDIA_TYPE",
    "TARGET_LAYER_DETECTOR",
    "WRONG_LAYER_CONTROL_DETECTOR",
    "DIAGNOSTIC_CALIBRATION_DETECTOR_ROLES",
    "ELIGIBLE_THRESHOLD_SELECTED",
    "NO_ELIGIBLE_THRESHOLD",
    "DiagnosticCalibrationFitError",
    "DiagnosticCalibrationFitValidationError",
    "DiagnosticCalibrationRuntimeVersionError",
    "DiagnosticBinary64",
    "DiagnosticCalibrationRuleArtifact",
    "DiagnosticCalibrationDatasetRow",
    "DiagnosticCalibrationActivationDatasetArtifact",
    "DiagnosticCalibrationCandidateResult",
    "DiagnosticCalibrationModelFit",
    "DiagnosticCalibrationFitTranscriptArtifact",
    "build_diagnostic_calibration_rule",
    "load_diagnostic_calibration_rule",
    "replay_diagnostic_calibration_rule_projection",
    "bind_diagnostic_calibration_rule_to_plan",
    "build_diagnostic_calibration_activation_dataset",
    "load_diagnostic_calibration_activation_dataset",
    "replay_diagnostic_calibration_activation_dataset_projection",
    "replay_diagnostic_calibration_activation_dataset",
    "derive_diagnostic_calibration_threshold_candidates",
    "derive_diagnostic_calibration_candidate_results",
    "build_diagnostic_calibration_fit_transcript",
    "load_diagnostic_calibration_fit_transcript",
    "replay_diagnostic_calibration_fit_transcript_projection",
    "replay_diagnostic_calibration_fit_transcript",
    "diagnostic_calibration_model_fit",
]
