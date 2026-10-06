"""Fail-closed Stage C RunPod C-Cal authorization candidate, version 2.

This additive contract does not change the existing Stage C v1 authorization,
which remains a zero-provider-call, zero-spend, network-none design.  A v2
artifact binds the owner-supplied RunPod execution limits, but remains an
``UNAUTHORIZED`` structural candidate.  It cannot start a pod or execute a
model until a separate externally authenticated activation path supplies
trusted time, a durable one-use nonce transition, an authenticated price
snapshot, and an aggregate provider-charge ledger.

The financial helper in this module is arithmetic only.  A positive result
means that supplied prospective numbers fit the frozen ceilings; it is never
provider-start or model-execution authority.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from types import MappingProxyType
from typing import Any, Callable

from ._strict_json import (
    StrictJSONError,
    canonical_json_bytes,
    freeze_json,
    load_json_object,
    sha256_bytes,
    thaw_json,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_int,
    expect_keys,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_string,
    expect_timestamp,
)


STAGEC_RUNPOD_AUTHORIZATION_V2_SCHEMA = (
    "cas_harness_v2.stagec_runpod_c_cal_execution_authorization_candidate.v2"
)
STAGEC_RUNPOD_AUTHORIZATION_V2_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-runpod-c-cal-authorization-candidate-v2+json"
)

STAGEC_RUNPOD_PROGRAM_ID = "gate5-stagec-qwen-prompt-injection-v0.1"
STAGEC_RUNPOD_PHASE_ID = "stagec-calibration"
STAGEC_RUNPOD_PHASE_LABEL = "C-Cal"
STAGEC_RUNPOD_PHASE_TYPE = "DIAGNOSTIC_CALIBRATION"

STAGEC_RUNPOD_PROVIDER = "RUNPOD"
STAGEC_RUNPOD_POD_ID = "zp2s9pscgncn0b"
STAGEC_RUNPOD_POD_NAME = (
    "cas-jacobian-v1-research-20260722-migration-migration"
)
STAGEC_RUNPOD_GPU_PRODUCT = "NVIDIA A40"
STAGEC_RUNPOD_GPU_COUNT = 1
STAGEC_RUNPOD_CONTAINER_IMAGE = (
    "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
)
STAGEC_RUNPOD_CONTAINER_IMAGE_MANIFEST_MEDIA_TYPE = (
    "application/vnd.docker.distribution.manifest.v2+json"
)
STAGEC_RUNPOD_CONTAINER_IMAGE_MANIFEST_DIGEST = (
    "sha256:61a4aafb0094cd773f11eefa378929d5a687bd775febeb78eac62fc824141fb5"
)
STAGEC_RUNPOD_CONTAINER_IMAGE_CONFIG_DIGEST = (
    "sha256:ff5fe688608be260bd6c0cde161cf7bd394f41526610a9addf406a535cdc150a"
)

STAGEC_RUNPOD_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
STAGEC_RUNPOD_MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
STAGEC_RUNPOD_WEIGHTS_FILENAME = "model.safetensors"
STAGEC_RUNPOD_WEIGHTS_SHA256 = (
    "FDF756FA7FCBE7404D5C60E26BFF1A0C8B8AA1F72CED49E7DD0210FE288FB7FE"
)
STAGEC_RUNPOD_WEIGHTS_BYTE_LENGTH = 988_097_824

STAGEC_RUNPOD_EVALUATION_COUNT = 480
STAGEC_RUNPOD_ATTEMPTS_PER_CASE = 1
STAGEC_RUNPOD_TOTAL_ATTEMPT_COUNT = 480
STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD = 100_000_000
STAGEC_RUNPOD_MAXIMUM_QUOTED_RATE_MICROUSD_PER_HOUR = 440_000
STAGEC_RUNPOD_MAXIMUM_RUNNING_DURATION_SECONDS = 86_400
STAGEC_RUNPOD_AUTHORIZATION_WINDOW_SECONDS = 72 * 60 * 60

STAGEC_RUNPOD_GATE_5_STATUS = "OPEN / KEEP_OPEN"
STAGEC_RUNPOD_STAGE_C_STATUS = "DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED"
STAGEC_RUNPOD_PROJECT_STATUS = "NOT LICENSED / HELD / NOT FROZEN"
STAGEC_RUNPOD_AUTHORIZATION_STATUS = "UNAUTHORIZED"
STAGEC_RUNPOD_ACTIVATION_STATUS = "NOT_ACTIVATED"
STAGEC_RUNPOD_AUTHENTICATION_STATUS = "NOT_AUTHENTICATED"
STAGEC_RUNPOD_NONCE_STATE = "UNCONSUMED"
STAGEC_RUNPOD_FINANCIAL_ASSESSMENT_STATUS = (
    "WITHIN_BOUNDS_NOT_PROVIDER_START_AUTHORITY"
)
STAGEC_RUNPOD_CONTROL_BOUNDARY = (
    "STRUCTURAL_CANDIDATE_ONLY_NOT_PROVIDER_START_OR_MODEL_EXECUTION_AUTHORITY"
)

STAGEC_RUNPOD_CHARGE_CATEGORIES = (
    "COMPUTE",
    "STORAGE",
    "OTHER_INCREMENTAL_PROVIDER_CHARGES",
)

_PROGRAM_BINDING = MappingProxyType(
    {
        "program_id": STAGEC_RUNPOD_PROGRAM_ID,
    }
)
_PHASE_BINDING = MappingProxyType(
    {
        "phase_id": STAGEC_RUNPOD_PHASE_ID,
        "phase_label": STAGEC_RUNPOD_PHASE_LABEL,
        "phase_type": STAGEC_RUNPOD_PHASE_TYPE,
    }
)
_PROVIDER_BINDING = MappingProxyType(
    {
        "provider": STAGEC_RUNPOD_PROVIDER,
        "pod_id": STAGEC_RUNPOD_POD_ID,
        "pod_name": STAGEC_RUNPOD_POD_NAME,
        "observed_pod_state": "STOPPED",
        "secure_cloud_region": "CA-MTL-1",
        "template_id": "runpod-torch-v240",
        "gpu_product": STAGEC_RUNPOD_GPU_PRODUCT,
        "gpu_count": STAGEC_RUNPOD_GPU_COUNT,
        "container_disk_gb": 30,
        "workspace_volume_mount": "/workspace",
        "workspace_volume_gb": 50,
        "workspace_volume_encrypted": True,
        "owner_scheduling_timezone": "America/Los_Angeles",
        "container_image_tag": STAGEC_RUNPOD_CONTAINER_IMAGE,
        "container_image_manifest_media_type": (
            STAGEC_RUNPOD_CONTAINER_IMAGE_MANIFEST_MEDIA_TYPE
        ),
        "container_image_manifest_digest": (
            STAGEC_RUNPOD_CONTAINER_IMAGE_MANIFEST_DIGEST
        ),
        "container_image_config_digest": STAGEC_RUNPOD_CONTAINER_IMAGE_CONFIG_DIGEST,
        "observed_image_role": "OBSERVED_BASE_ONLY_NOT_EXECUTION_IMAGE",
        "compatibility": "INADMISSIBLE_TORCH_CUDA_MISMATCH",
        "observed_runtime_torch_version": "2.4.0",
        "observed_runtime_cuda_version": "12.4.1",
        "required_execution_torch_version": "2.13.0+cu126",
        "required_execution_cuda_version": "12.6",
        "required_derived_execution_image_digest": "EXTERNAL_REQUIRED_NOT_PROVIDED",
        "observed_quoted_compute_rate_microusd_per_hour": (
            STAGEC_RUNPOD_MAXIMUM_QUOTED_RATE_MICROUSD_PER_HOUR
        ),
        "observation_authority": "CURRENT_OBSERVATION_NOT_ACTIVATION_AUTHORITY",
        "required_prestart_pod_state": "STOPPED",
    }
)
_MODEL_BINDING = MappingProxyType(
    {
        "model_id": STAGEC_RUNPOD_MODEL_ID,
        "revision": STAGEC_RUNPOD_MODEL_REVISION,
        "weights_filename": STAGEC_RUNPOD_WEIGHTS_FILENAME,
        "weights_sha256": STAGEC_RUNPOD_WEIGHTS_SHA256,
        "weights_byte_length": STAGEC_RUNPOD_WEIGHTS_BYTE_LENGTH,
    }
)
_WORKLOAD_LIMITS = MappingProxyType(
    {
        "phase_submission_count": 1,
        "corpus_evaluation_count": STAGEC_RUNPOD_EVALUATION_COUNT,
        "attempts_per_case": STAGEC_RUNPOD_ATTEMPTS_PER_CASE,
        "total_attempt_count": STAGEC_RUNPOD_TOTAL_ATTEMPT_COUNT,
        "canary_count": 0,
        "retry_count": 0,
        "replacement_count": 0,
        "generation_count": 0,
        "intervention_count": 0,
    }
)
_FINANCIAL_LIMITS = MappingProxyType(
    {
        "currency_unit": "MICROUSD",
        "maximum_aggregate_incremental_provider_spend_microusd": (
            STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD
        ),
        "maximum_quoted_compute_rate_microusd_per_hour": (
            STAGEC_RUNPOD_MAXIMUM_QUOTED_RATE_MICROUSD_PER_HOUR
        ),
        "maximum_running_duration_seconds": (
            STAGEC_RUNPOD_MAXIMUM_RUNNING_DURATION_SECONDS
        ),
        "aggregate_charge_categories": STAGEC_RUNPOD_CHARGE_CATEGORIES,
        "aggregate_ledger_status": "EXTERNAL_REQUIRED_NOT_PROVIDED",
        "price_rate_drift_policy": "FAIL_BEFORE_START_IF_ABOVE_BOUND",
        "aggregate_limit_policy": "PROJECTED_TOTAL_STRICTLY_BELOW_MAXIMUM",
    }
)
_ACTIVATION = MappingProxyType(
    {
        "activation_status": STAGEC_RUNPOD_ACTIVATION_STATUS,
        "authentication_status": STAGEC_RUNPOD_AUTHENTICATION_STATUS,
        "activation_receipt": None,
        "trusted_time": "EXTERNAL_REQUIRED_NOT_PROVIDED",
        "authenticated_price_snapshot": "EXTERNAL_REQUIRED_NOT_PROVIDED",
        "aggregate_charge_ledger": "EXTERNAL_REQUIRED_NOT_PROVIDED",
        "provider_start": "NOT_PERFORMED",
    }
)
_STATUS_BOUNDARY = MappingProxyType(
    {
        "gate_5_status": STAGEC_RUNPOD_GATE_5_STATUS,
        "stage_c_status": STAGEC_RUNPOD_STAGE_C_STATUS,
        "authorization_status": STAGEC_RUNPOD_AUTHORIZATION_STATUS,
        "project_status": STAGEC_RUNPOD_PROJECT_STATUS,
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "freeze_status": "NOT FROZEN",
    }
)
_AUTHORITY = MappingProxyType(
    {
        "scope": "OWNER_INPUTS_BOUND_STRUCTURAL_CANDIDATE_ONLY",
        "external_authentication": "REQUIRED_NOT_PROVIDED",
        "trusted_time": "REQUIRED_NOT_PROVIDED",
        "durable_one_use": "REQUIRED_NOT_PROVIDED",
        "provider_start": "NOT_AUTHORIZED",
        "model_execution": "NOT_AUTHORIZED",
        "provider_calls_performed": 0,
        "pod_starts_performed": 0,
        "model_invocations_performed": 0,
        "incremental_provider_spend_incurred_microusd": 0,
        "self_hash_is_authority": False,
    }
)


class StageCRunPodAuthorizationV2Error(SchemaValidationError):
    """A RunPod v2 authorization candidate or bound failed closed."""


def _domain_errors(function: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(function)
    def guarded(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except StageCRunPodAuthorizationV2Error:
            raise
        except (
            StrictJSONError,
            SchemaValidationError,
            ValueError,
            TypeError,
            KeyError,
            OverflowError,
        ) as exc:
            raise StageCRunPodAuthorizationV2Error(
                f"{function.__name__}: {exc}"
            ) from exc

    return guarded


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _canonical_object(
    raw: bytes | bytearray | memoryview,
) -> tuple[bytes, dict[str, Any]]:
    snapshot, value = load_json_object(raw)
    if snapshot != canonical_json_bytes(value):
        raise StageCRunPodAuthorizationV2Error(
            "RunPod v2 authorization must use exact canonical JSON bytes"
        )
    return snapshot, value


def _require_exact_object(
    value: Any,
    expected: MappingProxyType,
    path: str,
) -> dict[str, Any]:
    obj = expect_object(value, path)
    expect_keys(obj, required=set(expected), path=path)
    if canonical_json_bytes(obj) != canonical_json_bytes(thaw_json(expected)):
        raise StageCRunPodAuthorizationV2Error(
            f"{path} differs from the frozen RunPod v2 binding"
        )
    return obj


def _require_nonce(value: Any) -> str:
    nonce = expect_object(value, "$.nonce")
    expect_keys(
        nonce,
        required={
            "profile",
            "nonce_b64url",
            "state",
            "consumed_at",
            "durable_one_use",
            "structural_assurance",
            "randomness_provenance",
        },
        path="$.nonce",
    )
    if nonce["profile"] != "CALLER_SUPPLIED_CSPRNG_256_BIT_BASE64URL":
        raise StageCRunPodAuthorizationV2Error("nonce profile is not exact")
    nonce_text = expect_string(
        nonce["nonce_b64url"], "$.nonce.nonce_b64url", maximum=43
    )
    if len(nonce_text) != 43 or "=" in nonce_text:
        raise StageCRunPodAuthorizationV2Error(
            "nonce must be unpadded canonical 32-byte base64url"
        )
    try:
        nonce_bytes = base64.b64decode(
            nonce_text + "=",
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, TypeError) as exc:
        raise StageCRunPodAuthorizationV2Error(
            "nonce is invalid base64url"
        ) from exc
    if len(nonce_bytes) != 32 or not any(nonce_bytes):
        raise StageCRunPodAuthorizationV2Error(
            "nonce must be nonzero exact 32 bytes"
        )
    if len(set(nonce_bytes)) == 1:
        raise StageCRunPodAuthorizationV2Error(
            "nonce must not be a structurally degenerate repeated byte"
        )
    canonical = base64.urlsafe_b64encode(nonce_bytes).rstrip(b"=").decode("ascii")
    if canonical != nonce_text:
        raise StageCRunPodAuthorizationV2Error(
            "nonce has noncanonical base64url pad bits"
        )
    if (
        nonce["state"] != STAGEC_RUNPOD_NONCE_STATE
        or nonce["consumed_at"] is not None
        or nonce["durable_one_use"] != "EXTERNAL_REQUIRED_NOT_PROVIDED"
        or nonce["structural_assurance"]
        != "LENGTH_ENCODING_NONZERO_NONUNIFORM_ONLY"
        or nonce["randomness_provenance"]
        != "EXTERNAL_AUTHENTICATION_REQUIRED_NOT_PROVIDED"
    ):
        raise StageCRunPodAuthorizationV2Error(
            "nonce must remain externally unconsumed and unactivated"
        )
    return nonce_text


@dataclass(frozen=True, slots=True, init=False)
class StageCRunPodAuthorizationV2Artifact:
    """Factory-only immutable structural candidate; never start authority."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    authorization_id: str
    created_at: str
    window_start: str
    window_end: str
    nonce_b64url: str
    payload: Any

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCRunPodAuthorizationV2Artifact is factory-only; use "
            "load_stagec_runpod_authorization_v2 or "
            "build_stagec_runpod_authorization_v2"
        )

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.authorization_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_RUNPOD_AUTHORIZATION_V2_MEDIA_TYPE,
        )

    @property
    def authorization_status(self) -> str:
        return STAGEC_RUNPOD_AUTHORIZATION_STATUS

    @property
    def provider_start_authorized(self) -> bool:
        return False


@dataclass(frozen=True, slots=True, init=False)
class StageCRunPodFinancialBoundsAssessmentV2:
    """Pure arithmetic result that deliberately grants no execution authority."""

    quoted_compute_rate_microusd_per_hour: int
    planned_running_duration_seconds: int
    projected_compute_floor_microusd: int
    aggregate_incremental_provider_spend_microusd: int
    assessment_status: str = STAGEC_RUNPOD_FINANCIAL_ASSESSMENT_STATUS
    provider_start_authorized: bool = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCRunPodFinancialBoundsAssessmentV2 is factory-only; use "
            "assess_stagec_runpod_financial_bounds_v2"
        )


def _make_financial_assessment(
    *,
    rate: int,
    duration: int,
    projected_compute_floor: int,
    aggregate: int,
) -> StageCRunPodFinancialBoundsAssessmentV2:
    assessment = object.__new__(StageCRunPodFinancialBoundsAssessmentV2)
    object.__setattr__(
        assessment,
        "quoted_compute_rate_microusd_per_hour",
        rate,
    )
    object.__setattr__(assessment, "planned_running_duration_seconds", duration)
    object.__setattr__(
        assessment,
        "projected_compute_floor_microusd",
        projected_compute_floor,
    )
    object.__setattr__(
        assessment,
        "aggregate_incremental_provider_spend_microusd",
        aggregate,
    )
    object.__setattr__(
        assessment,
        "assessment_status",
        STAGEC_RUNPOD_FINANCIAL_ASSESSMENT_STATUS,
    )
    object.__setattr__(assessment, "provider_start_authorized", False)
    return assessment


def _make_artifact(
    *,
    snapshot: bytes,
    authorization_id: str,
    created_at: str,
    window_start: str,
    window_end: str,
    nonce_b64url: str,
    payload: dict[str, Any],
) -> StageCRunPodAuthorizationV2Artifact:
    artifact = object.__new__(StageCRunPodAuthorizationV2Artifact)
    object.__setattr__(artifact, "raw_bytes", snapshot)
    object.__setattr__(artifact, "sha256", sha256_bytes(snapshot))
    object.__setattr__(artifact, "byte_length", len(snapshot))
    object.__setattr__(artifact, "authorization_id", authorization_id)
    object.__setattr__(artifact, "created_at", created_at)
    object.__setattr__(artifact, "window_start", window_start)
    object.__setattr__(artifact, "window_end", window_end)
    object.__setattr__(artifact, "nonce_b64url", nonce_b64url)
    object.__setattr__(artifact, "payload", freeze_json(payload))
    return artifact


@_domain_errors
def load_stagec_runpod_authorization_v2(
    raw: bytes | bytearray | memoryview,
) -> StageCRunPodAuthorizationV2Artifact:
    """Strictly load one unactivated, exact-scope RunPod v2 candidate."""

    snapshot, obj = _canonical_object(raw)
    expect_keys(
        obj,
        required={
            "schema_version",
            "authorization_id",
            "created_at",
            "program_binding",
            "phase_binding",
            "provider_binding",
            "model_binding",
            "workload_limits",
            "financial_limits",
            "authorization_window",
            "nonce",
            "activation",
            "status_boundary",
            "authority",
            "boundary",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_RUNPOD_AUTHORIZATION_V2_SCHEMA:
        raise StageCRunPodAuthorizationV2Error("wrong RunPod v2 schema")
    authorization_id = expect_machine_id(
        obj["authorization_id"], "$.authorization_id"
    )
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    _require_exact_object(obj["program_binding"], _PROGRAM_BINDING, "$.program_binding")
    _require_exact_object(obj["phase_binding"], _PHASE_BINDING, "$.phase_binding")
    _require_exact_object(
        obj["provider_binding"], _PROVIDER_BINDING, "$.provider_binding"
    )
    _require_exact_object(obj["model_binding"], _MODEL_BINDING, "$.model_binding")
    _require_exact_object(obj["workload_limits"], _WORKLOAD_LIMITS, "$.workload_limits")
    _require_exact_object(
        obj["financial_limits"], _FINANCIAL_LIMITS, "$.financial_limits"
    )

    window = expect_object(obj["authorization_window"], "$.authorization_window")
    expect_keys(
        window,
        required={"window_start", "window_end", "interval_semantics", "duration_seconds"},
        path="$.authorization_window",
    )
    window_start = expect_timestamp(
        window["window_start"], "$.authorization_window.window_start"
    )
    window_end = expect_timestamp(
        window["window_end"], "$.authorization_window.window_end"
    )
    if (
        window["interval_semantics"]
        != "HALF_OPEN_START_INCLUSIVE_END_EXCLUSIVE"
        or expect_int(
            window["duration_seconds"],
            "$.authorization_window.duration_seconds",
            minimum=1,
        )
        != STAGEC_RUNPOD_AUTHORIZATION_WINDOW_SECONDS
    ):
        raise StageCRunPodAuthorizationV2Error(
            "authorization window must be the exact frozen 72-hour half-open policy"
        )
    created_time = _time(created_at)
    start_time = _time(window_start)
    end_time = _time(window_end)
    # Seattle's UTC offsets are integral hours, so a whole UTC hour is also a
    # whole Seattle wall-clock hour.  Avoid host/package tzdata I/O here; the
    # separately bound scheduling-zone literal remains America/Los_Angeles.
    if not (
        created_time < start_time < end_time
        and start_time.minute == start_time.second == start_time.microsecond == 0
        and end_time.minute == end_time.second == end_time.microsecond == 0
        and int((end_time - start_time).total_seconds())
        == STAGEC_RUNPOD_AUTHORIZATION_WINDOW_SECONDS
        and (end_time - start_time).total_seconds()
        == STAGEC_RUNPOD_AUTHORIZATION_WINDOW_SECONDS
    ):
        raise StageCRunPodAuthorizationV2Error(
            "authorization window must be prospective, exactly 72 hours, and "
            "aligned to exact whole UTC and Seattle clock hours"
        )

    nonce_b64url = _require_nonce(obj["nonce"])
    _require_exact_object(obj["activation"], _ACTIVATION, "$.activation")
    _require_exact_object(
        obj["status_boundary"], _STATUS_BOUNDARY, "$.status_boundary"
    )
    _require_exact_object(obj["authority"], _AUTHORITY, "$.authority")
    if obj["boundary"] != STAGEC_RUNPOD_CONTROL_BOUNDARY:
        raise StageCRunPodAuthorizationV2Error(
            "authorization boundary differs from the frozen nonauthority boundary"
        )

    return _make_artifact(
        snapshot=snapshot,
        authorization_id=authorization_id,
        created_at=created_at,
        window_start=window_start,
        window_end=window_end,
        nonce_b64url=nonce_b64url,
        payload=obj,
    )


@_domain_errors
def build_stagec_runpod_authorization_v2(
    *,
    authorization_id: str,
    created_at: str,
    window_start: str,
    window_end: str,
    nonce_b64url: str,
) -> StageCRunPodAuthorizationV2Artifact:
    """Build the exact structural candidate around caller-supplied time/nonce."""

    value = {
        "schema_version": STAGEC_RUNPOD_AUTHORIZATION_V2_SCHEMA,
        "authorization_id": authorization_id,
        "created_at": created_at,
        "program_binding": thaw_json(_PROGRAM_BINDING),
        "phase_binding": thaw_json(_PHASE_BINDING),
        "provider_binding": thaw_json(_PROVIDER_BINDING),
        "model_binding": thaw_json(_MODEL_BINDING),
        "workload_limits": thaw_json(_WORKLOAD_LIMITS),
        "financial_limits": thaw_json(_FINANCIAL_LIMITS),
        "authorization_window": {
            "window_start": window_start,
            "window_end": window_end,
            "interval_semantics": "HALF_OPEN_START_INCLUSIVE_END_EXCLUSIVE",
            "duration_seconds": STAGEC_RUNPOD_AUTHORIZATION_WINDOW_SECONDS,
        },
        "nonce": {
            "profile": "CALLER_SUPPLIED_CSPRNG_256_BIT_BASE64URL",
            "nonce_b64url": nonce_b64url,
            "state": STAGEC_RUNPOD_NONCE_STATE,
            "consumed_at": None,
            "durable_one_use": "EXTERNAL_REQUIRED_NOT_PROVIDED",
            "structural_assurance": "LENGTH_ENCODING_NONZERO_NONUNIFORM_ONLY",
            "randomness_provenance": (
                "EXTERNAL_AUTHENTICATION_REQUIRED_NOT_PROVIDED"
            ),
        },
        "activation": thaw_json(_ACTIVATION),
        "status_boundary": thaw_json(_STATUS_BOUNDARY),
        "authority": thaw_json(_AUTHORITY),
        "boundary": STAGEC_RUNPOD_CONTROL_BOUNDARY,
    }
    return load_stagec_runpod_authorization_v2(canonical_json_bytes(value))


def _fresh(
    authorization: StageCRunPodAuthorizationV2Artifact,
) -> StageCRunPodAuthorizationV2Artifact:
    if type(authorization) is not StageCRunPodAuthorizationV2Artifact:
        raise StageCRunPodAuthorizationV2Error(
            "authorization must have the exact factory-issued v2 type"
        )
    replay = load_stagec_runpod_authorization_v2(authorization.raw_bytes)
    exact = (
        type(authorization.raw_bytes) is bytes
        and authorization.raw_bytes == replay.raw_bytes
        and type(authorization.sha256) is str
        and authorization.sha256 == replay.sha256
        and type(authorization.byte_length) is int
        and authorization.byte_length == replay.byte_length
        and type(authorization.authorization_id) is str
        and authorization.authorization_id == replay.authorization_id
        and type(authorization.created_at) is str
        and authorization.created_at == replay.created_at
        and type(authorization.window_start) is str
        and authorization.window_start == replay.window_start
        and type(authorization.window_end) is str
        and authorization.window_end == replay.window_end
        and type(authorization.nonce_b64url) is str
        and authorization.nonce_b64url == replay.nonce_b64url
        and canonical_json_bytes(authorization.payload) == replay.raw_bytes
    )
    if not exact:
        raise StageCRunPodAuthorizationV2Error(
            "authorization object differs from exact fresh replay"
        )
    return replay


@_domain_errors
def assess_stagec_runpod_financial_bounds_v2(
    authorization: StageCRunPodAuthorizationV2Artifact,
    *,
    quoted_compute_rate_microusd_per_hour: int,
    planned_running_duration_seconds: int,
    projected_incremental_charges_microusd: dict[str, int],
) -> StageCRunPodFinancialBoundsAssessmentV2:
    """Check all incremental charge classes without granting start authority."""

    _fresh(authorization)
    rate = expect_int(
        quoted_compute_rate_microusd_per_hour,
        "quoted_compute_rate_microusd_per_hour",
        minimum=1,
        maximum=2**31 - 1,
    )
    if rate > STAGEC_RUNPOD_MAXIMUM_QUOTED_RATE_MICROUSD_PER_HOUR:
        raise StageCRunPodAuthorizationV2Error(
            "quoted compute price drifted above the frozen pre-start bound"
        )
    duration = expect_int(
        planned_running_duration_seconds,
        "planned_running_duration_seconds",
        minimum=1,
        maximum=2**31 - 1,
    )
    if duration > STAGEC_RUNPOD_MAXIMUM_RUNNING_DURATION_SECONDS:
        raise StageCRunPodAuthorizationV2Error(
            "planned RUNNING duration exceeds the frozen 24-hour cap"
        )
    if type(projected_incremental_charges_microusd) is not dict:
        raise StageCRunPodAuthorizationV2Error(
            "projected aggregate charge ledger must be an exact object"
        )
    expect_keys(
        projected_incremental_charges_microusd,
        required=set(STAGEC_RUNPOD_CHARGE_CATEGORIES),
        path="projected_incremental_charges_microusd",
    )
    charges = {
        category: expect_int(
            projected_incremental_charges_microusd[category],
            f"projected_incremental_charges_microusd.{category}",
            minimum=0,
            maximum=STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD,
        )
        for category in STAGEC_RUNPOD_CHARGE_CATEGORIES
    }
    projected_compute_floor = (rate * duration + 3_599) // 3_600
    if charges["COMPUTE"] < projected_compute_floor:
        raise StageCRunPodAuthorizationV2Error(
            "aggregate ledger understates the quoted compute projection"
        )
    aggregate = sum(charges.values())
    if aggregate >= STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD:
        raise StageCRunPodAuthorizationV2Error(
            "projected aggregate incremental provider spend must retain a "
            "nonzero safety reserve below the $100.00 maximum"
        )
    return _make_financial_assessment(
        rate=rate,
        duration=duration,
        projected_compute_floor=projected_compute_floor,
        aggregate=aggregate,
    )


@_domain_errors
def require_stagec_runpod_external_activation_v2(
    authorization: StageCRunPodAuthorizationV2Artifact,
) -> None:
    """Fail closed: this module intentionally ships no positive activator."""

    _fresh(authorization)
    raise StageCRunPodAuthorizationV2Error(
        "external authenticated activation, trusted time, durable nonce "
        "consumption, price snapshot, and aggregate ledger are not provided"
    )


__all__ = [
    "STAGEC_RUNPOD_AUTHORIZATION_V2_SCHEMA",
    "STAGEC_RUNPOD_AUTHORIZATION_V2_MEDIA_TYPE",
    "STAGEC_RUNPOD_PROGRAM_ID",
    "STAGEC_RUNPOD_PHASE_ID",
    "STAGEC_RUNPOD_PHASE_LABEL",
    "STAGEC_RUNPOD_PHASE_TYPE",
    "STAGEC_RUNPOD_PROVIDER",
    "STAGEC_RUNPOD_POD_ID",
    "STAGEC_RUNPOD_POD_NAME",
    "STAGEC_RUNPOD_GPU_PRODUCT",
    "STAGEC_RUNPOD_GPU_COUNT",
    "STAGEC_RUNPOD_CONTAINER_IMAGE",
    "STAGEC_RUNPOD_CONTAINER_IMAGE_MANIFEST_MEDIA_TYPE",
    "STAGEC_RUNPOD_CONTAINER_IMAGE_MANIFEST_DIGEST",
    "STAGEC_RUNPOD_CONTAINER_IMAGE_CONFIG_DIGEST",
    "STAGEC_RUNPOD_MODEL_ID",
    "STAGEC_RUNPOD_MODEL_REVISION",
    "STAGEC_RUNPOD_WEIGHTS_FILENAME",
    "STAGEC_RUNPOD_WEIGHTS_SHA256",
    "STAGEC_RUNPOD_WEIGHTS_BYTE_LENGTH",
    "STAGEC_RUNPOD_EVALUATION_COUNT",
    "STAGEC_RUNPOD_ATTEMPTS_PER_CASE",
    "STAGEC_RUNPOD_TOTAL_ATTEMPT_COUNT",
    "STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD",
    "STAGEC_RUNPOD_MAXIMUM_QUOTED_RATE_MICROUSD_PER_HOUR",
    "STAGEC_RUNPOD_MAXIMUM_RUNNING_DURATION_SECONDS",
    "STAGEC_RUNPOD_AUTHORIZATION_WINDOW_SECONDS",
    "STAGEC_RUNPOD_GATE_5_STATUS",
    "STAGEC_RUNPOD_STAGE_C_STATUS",
    "STAGEC_RUNPOD_PROJECT_STATUS",
    "STAGEC_RUNPOD_AUTHORIZATION_STATUS",
    "STAGEC_RUNPOD_ACTIVATION_STATUS",
    "STAGEC_RUNPOD_AUTHENTICATION_STATUS",
    "STAGEC_RUNPOD_NONCE_STATE",
    "STAGEC_RUNPOD_FINANCIAL_ASSESSMENT_STATUS",
    "STAGEC_RUNPOD_CONTROL_BOUNDARY",
    "STAGEC_RUNPOD_CHARGE_CATEGORIES",
    "StageCRunPodAuthorizationV2Error",
    "StageCRunPodAuthorizationV2Artifact",
    "StageCRunPodFinancialBoundsAssessmentV2",
    "load_stagec_runpod_authorization_v2",
    "build_stagec_runpod_authorization_v2",
    "assess_stagec_runpod_financial_bounds_v2",
    "require_stagec_runpod_external_activation_v2",
]
