"""Offline-only Stage C RunPod runner preparation.

This first tranche deliberately has no provider client and no positive
activation function.  It validates a separately frozen environment candidate,
binds exact authorization and prerequisite bytes by ``ArtifactRef``, performs
conservative integer budget arithmetic, and returns a blocked preparation.

Provider observation, trusted time, durable nonce consumption, pod start,
post-start identity verification, row execution, stop, billing reconciliation,
and WORM receipt anchoring remain external requirements.  A later tranche may
add those capabilities only behind a separately reviewed activation boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
from types import MappingProxyType
from typing import Any, Mapping

from ._strict_json import (
    StrictJSONError,
    canonical_json_bytes,
    freeze_json,
    load_json_object,
    sha256_bytes,
)
from ._validation import ArtifactRef, SchemaValidationError
from .diagnostic_stagec_runpod_authorization_v2 import (
    STAGEC_RUNPOD_AUTHORIZATION_V2_MEDIA_TYPE,
    StageCRunPodAuthorizationV2Artifact,
    load_stagec_runpod_authorization_v2,
)
from .diagnostic_stagec_prerequisite_admission import (
    STAGEC_PREREQUISITE_ADMISSION_MEDIA_TYPE,
    STAGEC_PREREQUISITE_INTAKE_MEDIA_TYPE,
)
from .diagnostic_stagec_prerequisite_external_intake import (
    STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_MEDIA_TYPE,
    STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_SCHEMA,
    STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS,
    STAGEC_EXTERNAL_PREREQUISITE_REPORT_MEDIA_TYPE,
    STAGEC_EXTERNAL_RUNTIME_AUTHORIZATION,
    STAGEC_EXTERNAL_TRUST_AUTHENTICATION,
)


STAGEC_RUNPOD_ENVIRONMENT_V1_SCHEMA = (
    "cas_harness_v2.stagec_runpod_environment_candidate.v1"
)
STAGEC_RUNPOD_ENVIRONMENT_V1_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-runpod-environment-candidate-v1+json"
)
STAGEC_RUNPOD_OFFLINE_PREPARATION_STATE = (
    "STRUCTURALLY_PREPARED_NO_PROVIDER_CALL"
)
STAGEC_RUNPOD_EXTERNAL_ACTIVATION_REQUIRED = (
    "EXTERNAL_AUTHENTICATED_ACTIVATION_REQUIRED"
)

STAGEC_RUNPOD_GET_POD_PATH = "/v1/pods/zp2s9pscgncn0b"
STAGEC_RUNPOD_GET_BILLING_PATH = "/v1/billing/pods"
STAGEC_RUNPOD_START_PATH = "/v1/pods/zp2s9pscgncn0b/start"
STAGEC_RUNPOD_STOP_PATH = "/v1/pods/zp2s9pscgncn0b/stop"

STAGEC_RUNPOD_POD_ID = "zp2s9pscgncn0b"
STAGEC_RUNPOD_POD_NAME = (
    "cas-jacobian-v1-research-20260722-migration-migration"
)
STAGEC_RUNPOD_GPU_PRODUCT = "NVIDIA A40"
STAGEC_RUNPOD_GPU_COUNT = 1
STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_TAG = (
    "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
)
STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_MANIFEST_DIGEST = (
    "sha256:61a4aafb0094cd773f11eefa378929d5a687bd775febeb78eac62fc824141fb5"
)
STAGEC_RUNPOD_DOCKER_V2_MANIFEST_MEDIA_TYPE = (
    "application/vnd.docker.distribution.manifest.v2+json"
)
STAGEC_RUNPOD_OCI_IMAGE_MANIFEST_MEDIA_TYPE = (
    "application/vnd.oci.image.manifest.v1+json"
)
STAGEC_RUNPOD_EXECUTION_IMAGE_MANIFEST_MEDIA_TYPES = (
    STAGEC_RUNPOD_DOCKER_V2_MANIFEST_MEDIA_TYPE,
    STAGEC_RUNPOD_OCI_IMAGE_MANIFEST_MEDIA_TYPE,
)
STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY = (
    "ghcr.io/littlehenderson/noetic-compass-stagec-qwen-batch"
)

STAGEC_RUNPOD_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
STAGEC_RUNPOD_MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
STAGEC_RUNPOD_WEIGHTS_SHA256 = (
    "FDF756FA7FCBE7404D5C60E26BFF1A0C8B8AA1F72CED49E7DD0210FE288FB7FE"
)
STAGEC_RUNPOD_WEIGHTS_BYTE_LENGTH = 988_097_824

STAGEC_RUNPOD_REQUIRED_TORCH_VERSION = "2.13.0+cu126"
STAGEC_RUNPOD_REQUIRED_CUDA_RUNTIME_VERSION = "12.6"
STAGEC_RUNPOD_REQUIRED_DTYPE = "torch.bfloat16"

STAGEC_RUNPOD_EVALUATION_COUNT = 480
STAGEC_RUNPOD_MAXIMUM_RATE_MICROUSD_PER_HOUR = 440_000
STAGEC_RUNPOD_MAXIMUM_RUNNING_DURATION_SECONDS = 86_400
STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD = 100_000_000
# Frozen offline policy: retain at least $1.00 below the separately strict
# $100.00 aggregate cap.  Provider activation must re-observe billing and rate.
STAGEC_RUNPOD_MINIMUM_SAFETY_RESERVE_MICROUSD = 1_000_000
STAGEC_RUNPOD_MAXIMUM_LIVE_PREPARATION_SEALS = 1_024

STAGEC_RUNPOD_OFFLINE_BLOCKERS = (
    "AUTHENTICATED_PROVIDER_POD_OBSERVATION_NOT_PERFORMED",
    "AUTHENTICATED_PROVIDER_BILLING_OBSERVATION_NOT_PERFORMED",
    "TRUSTED_TIME_NOT_OBSERVED",
    "DURABLE_ONE_USE_NONCE_NOT_CONSUMED",
    "FOUR_CARRIER_TWELVE_DEPENDENCY_EXTERNAL_AUTHENTICITY_NOT_ESTABLISHED",
    "FOUR_CARRIER_TWELVE_DEPENDENCY_FULL_REPLAY_CONTEXT_NOT_SUPPLIED",
    "AUTHORIZATION_PREREQUISITE_ENVIRONMENT_CROSS_BINDING_NOT_ESTABLISHED",
    "PRE_START_DERIVED_EXECUTION_IMAGE_CONFIGURATION_NOT_OBSERVED",
    "POST_START_POD_IMAGE_GPU_RUNTIME_IDENTITY_NOT_OBSERVED",
    "DERIVED_EXECUTION_IMAGE_BUILD_PROVENANCE_NOT_EXTERNALLY_ATTESTED",
    "DERIVED_EXECUTION_IMAGE_REGISTRY_MANIFEST_RECEIPT_NOT_BOUND",
    "DERIVED_EXECUTION_IMAGE_RUNTIME_COMPATIBILITY_NOT_ATTESTED",
    (
        "IMAGE_ONLY_UPDATE_UNSAFE_CURRENT_POD_HAS_ENTRYPOINT_START_CMD_PORTS_"
        "ENV_AND_TEMPLATE_REQUIRE_FROZEN_FULL_POD_UPDATE_BUNDLE_TO_CLEAR_"
        "ENTRYPOINT_START_CMD_PORTS_AND_BIND_ENV_ALLOWLIST_TEMPLATE_REGISTRY_"
        "AUTH_AND_DIGEST"
    ),
    (
        "INHERITED_FASTAPI_CMD_IS_NOT_STAGEC_BATCH_AUTHORITY_REQUIRE_BATCH_"
        "ENTRYPOINT_PROFILE_IMMUTABLE_ROOT_OWNED_WORKER_EXACT_HASHES_"
        "WORKSPACE_ONLY_WRITES_OR_PROVEN_RUNPOD_READ_ONLY_ROOT"
    ),
    (
        "NETWORK_DURING_EXECUTION_NONE_REQUIRES_KERNEL_OR_PROVIDER_NO_EGRESS_"
        "EVIDENCE_PORT_CLEARING_ONLY_CONTROLS_INBOUND"
    ),
    "STOP_WATCHDOG_NOT_ACTIVATED",
    "WORM_OUTPUT_RECEIPT_ANCHOR_NOT_ESTABLISHED",
)

_EXPECTED_PROVIDER = MappingProxyType(
    {
        "provider": "RUNPOD",
        "pod_id": STAGEC_RUNPOD_POD_ID,
        "pod_name": STAGEC_RUNPOD_POD_NAME,
        "gpu_product": STAGEC_RUNPOD_GPU_PRODUCT,
        "gpu_count": STAGEC_RUNPOD_GPU_COUNT,
    }
)
_EXPECTED_CONFIGURED_POD_IMAGE = MappingProxyType(
    {
        "tag": STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_TAG,
        "manifest_digest": STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_MANIFEST_DIGEST,
        "manifest_media_type": STAGEC_RUNPOD_DOCKER_V2_MANIFEST_MEDIA_TYPE,
        "role": "OBSERVED_INCOMPATIBLE_PRIOR_STATE_TO_REPLACE",
    }
)
_EXPECTED_BOOTSTRAP_SOURCE_BUNDLE_REF = MappingProxyType(
    {
        "status": "EXTERNAL_REQUIRED_NOT_PROVIDED",
        "relationship": "BUILD_INPUT_ONLY_NOT_PARENT_IMAGE_ANCESTRY",
    }
)
_EXPECTED_RUNTIME = MappingProxyType(
    {
        "torch_version": STAGEC_RUNPOD_REQUIRED_TORCH_VERSION,
        "cuda_runtime_version": STAGEC_RUNPOD_REQUIRED_CUDA_RUNTIME_VERSION,
        "dtype": STAGEC_RUNPOD_REQUIRED_DTYPE,
        "native_jit_disabled": True,
        "network_during_execution": "NONE",
    }
)
_EXPECTED_MODEL = MappingProxyType(
    {
        "model_id": STAGEC_RUNPOD_MODEL_ID,
        "revision": STAGEC_RUNPOD_MODEL_REVISION,
        "weights_filename": "model.safetensors",
        "weights_sha256": STAGEC_RUNPOD_WEIGHTS_SHA256,
        "weights_byte_length": STAGEC_RUNPOD_WEIGHTS_BYTE_LENGTH,
    }
)
_EXPECTED_WORKLOAD = MappingProxyType(
    {
        "evaluation_count": STAGEC_RUNPOD_EVALUATION_COUNT,
        "attempts_per_case": 1,
        "total_attempt_count": STAGEC_RUNPOD_EVALUATION_COUNT,
        "canary_count": 0,
        "retry_count": 0,
        "replacement_count": 0,
        "generation_count": 0,
        "intervention_count": 0,
    }
)
_EXPECTED_LIMITS = MappingProxyType(
    {
        "maximum_rate_microusd_per_hour": (
            STAGEC_RUNPOD_MAXIMUM_RATE_MICROUSD_PER_HOUR
        ),
        "maximum_running_duration_seconds": (
            STAGEC_RUNPOD_MAXIMUM_RUNNING_DURATION_SECONDS
        ),
        "maximum_aggregate_spend_microusd": (
            STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD
        ),
        "minimum_safety_reserve_microusd": (
            STAGEC_RUNPOD_MINIMUM_SAFETY_RESERVE_MICROUSD
        ),
    }
)
_EXPECTED_AUTHORITY = MappingProxyType(
    {
        "scope": "STRUCTURAL_CANDIDATE_ONLY",
        "provider_calls_performed": 0,
        "pod_starts_performed": 0,
        "model_invocations_performed": 0,
        "external_activation": "REQUIRED_NOT_PROVIDED",
    }
)


class StageCRunPodRunnerError(SchemaValidationError):
    """The offline runner scaffold failed closed."""


def _strict_object(
    raw: bytes | bytearray | memoryview,
    label: str,
) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
    except (StrictJSONError, SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRunPodRunnerError(f"{label} is not strict JSON") from exc
    if snapshot != canonical_json_bytes(value):
        raise StageCRunPodRunnerError(f"{label} JSON is not canonical")
    return snapshot, value


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise StageCRunPodRunnerError(f"{label} keys differ from the frozen contract")
    return value


def _exact_mapping(value: Any, expected: Mapping[str, Any], label: str) -> None:
    obj = _exact_keys(value, set(expected), label)
    if canonical_json_bytes(obj) != canonical_json_bytes(dict(expected)):
        raise StageCRunPodRunnerError(f"{label} differs from the frozen contract")


def _machine_id(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 128
        or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-" for character in value)
    ):
        raise StageCRunPodRunnerError(f"{label} is not a bounded machine identifier")
    return value


def _digest(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(character not in "0123456789abcdef" for character in value[7:])
    ):
        raise StageCRunPodRunnerError(f"{label} is not a lowercase OCI sha256 digest")
    return value


@dataclass(frozen=True, slots=True)
class StageCRunPodEnvironmentV1:
    """An immutable structural candidate, not a provider observation."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    environment_id: str
    execution_image_reference: str
    execution_image_manifest_digest: str
    payload: Any

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.environment_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_RUNPOD_ENVIRONMENT_V1_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True, init=False)
class StageCRunPodOfflinePreparation:
    """A factory-issued zero-call preparation, never start authority."""

    environment: StageCRunPodEnvironmentV1
    authorization: ArtifactRef
    prerequisite_binding: ArtifactRef
    quoted_rate_microusd_per_hour: int
    planned_running_duration_seconds: int
    projected_compute_microusd: int
    projected_storage_microusd: int
    projected_other_microusd: int
    already_billed_in_window_microusd: int
    safety_reserve_microusd: int
    projected_aggregate_microusd: int
    state: str
    activation: str
    blockers: tuple[str, ...]
    provider_calls_performed: int
    pod_starts_performed: int
    model_invocations_performed: int

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCRunPodOfflinePreparation is factory-only; use "
            "prepare_stagec_runpod_no_provider_call"
        )


_PREPARATION_SEALS_LOCK = threading.RLock()
_PREPARATION_SEALS: dict[int, tuple[StageCRunPodOfflinePreparation, bytes]] = {}


def _artifact_ref_value(reference: ArtifactRef, label: str) -> dict[str, Any]:
    if type(reference) is not ArtifactRef:
        raise StageCRunPodRunnerError(f"{label} reference has the wrong exact type")
    try:
        detached = ArtifactRef(
            artifact_id=reference.artifact_id,
            sha256=reference.sha256,
            byte_length=reference.byte_length,
            media_type=reference.media_type,
        )
    except (SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRunPodRunnerError(
            f"{label} reference scalar fields are invalid"
        ) from exc
    return {
        "artifact_id": detached.artifact_id,
        "sha256": detached.sha256,
        "byte_length": detached.byte_length,
        "media_type": detached.media_type,
    }


def _preparation_snapshot(preparation: StageCRunPodOfflinePreparation) -> bytes:
    environment = preparation.environment
    if type(environment) is not StageCRunPodEnvironmentV1:
        raise StageCRunPodRunnerError("preparation environment has the wrong exact type")
    if type(environment.raw_bytes) is not bytes:
        raise StageCRunPodRunnerError("preparation environment bytes are not exact")
    if type(environment.payload) is not MappingProxyType:
        raise StageCRunPodRunnerError("preparation environment payload is not frozen")
    try:
        payload_raw = canonical_json_bytes(environment.payload)
    except (StrictJSONError, SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRunPodRunnerError(
            "preparation environment payload is invalid"
        ) from exc
    if (
        payload_raw != environment.raw_bytes
        or sha256_bytes(environment.raw_bytes) != environment.sha256
        or len(environment.raw_bytes) != environment.byte_length
    ):
        raise StageCRunPodRunnerError("preparation environment integrity drifted")
    if type(preparation.blockers) is not tuple:
        raise StageCRunPodRunnerError("preparation blockers are not an exact tuple")
    return canonical_json_bytes(
        {
            "environment": {
                "artifact_ref": _artifact_ref_value(
                    environment.artifact_ref, "environment"
                ),
                "execution_image_reference": environment.execution_image_reference,
                "execution_image_manifest_digest": (
                    environment.execution_image_manifest_digest
                ),
                "payload": environment.payload,
            },
            "authorization": _artifact_ref_value(
                preparation.authorization, "authorization"
            ),
            "prerequisite_binding": _artifact_ref_value(
                preparation.prerequisite_binding, "prerequisite binding"
            ),
            "quoted_rate_microusd_per_hour": (
                preparation.quoted_rate_microusd_per_hour
            ),
            "planned_running_duration_seconds": (
                preparation.planned_running_duration_seconds
            ),
            "projected_compute_microusd": preparation.projected_compute_microusd,
            "projected_storage_microusd": preparation.projected_storage_microusd,
            "projected_other_microusd": preparation.projected_other_microusd,
            "already_billed_in_window_microusd": (
                preparation.already_billed_in_window_microusd
            ),
            "safety_reserve_microusd": preparation.safety_reserve_microusd,
            "projected_aggregate_microusd": preparation.projected_aggregate_microusd,
            "state": preparation.state,
            "activation": preparation.activation,
            "blockers": list(preparation.blockers),
            "provider_calls_performed": preparation.provider_calls_performed,
            "pod_starts_performed": preparation.pod_starts_performed,
            "model_invocations_performed": preparation.model_invocations_performed,
        }
    )


def _make_offline_preparation(**values: Any) -> StageCRunPodOfflinePreparation:
    preparation = object.__new__(StageCRunPodOfflinePreparation)
    for field_name, field_value in values.items():
        object.__setattr__(preparation, field_name, field_value)
    object.__setattr__(
        preparation, "state", STAGEC_RUNPOD_OFFLINE_PREPARATION_STATE
    )
    object.__setattr__(
        preparation, "activation", STAGEC_RUNPOD_EXTERNAL_ACTIVATION_REQUIRED
    )
    object.__setattr__(preparation, "blockers", STAGEC_RUNPOD_OFFLINE_BLOCKERS)
    object.__setattr__(preparation, "provider_calls_performed", 0)
    object.__setattr__(preparation, "pod_starts_performed", 0)
    object.__setattr__(preparation, "model_invocations_performed", 0)
    seal = _preparation_snapshot(preparation)
    with _PREPARATION_SEALS_LOCK:
        _PREPARATION_SEALS[id(preparation)] = (preparation, seal)
        while (
            len(_PREPARATION_SEALS)
            > STAGEC_RUNPOD_MAXIMUM_LIVE_PREPARATION_SEALS
        ):
            # Exact dict insertion order is the eviction order.  The retained
            # object in each value prevents an id collision before eviction.
            oldest_preparation_id = next(iter(_PREPARATION_SEALS))
            del _PREPARATION_SEALS[oldest_preparation_id]
    return preparation


def _require_factory_preparation(
    preparation: StageCRunPodOfflinePreparation,
) -> None:
    if type(preparation) is not StageCRunPodOfflinePreparation:
        raise StageCRunPodRunnerError("preparation has the wrong exact type")
    with _PREPARATION_SEALS_LOCK:
        registered = _PREPARATION_SEALS.get(id(preparation))
        if registered is None or registered[0] is not preparation:
            raise StageCRunPodRunnerError("preparation is not factory-issued")
        try:
            current = _preparation_snapshot(preparation)
        except (
            AttributeError,
            StrictJSONError,
            SchemaValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise StageCRunPodRunnerError(
                "factory-issued preparation was mutated"
            ) from exc
        if current != registered[1]:
            raise StageCRunPodRunnerError("factory-issued preparation was mutated")


def load_stagec_runpod_environment_v1(
    raw: bytes | bytearray | memoryview,
) -> StageCRunPodEnvironmentV1:
    """Load one exact offline environment candidate without external I/O."""

    snapshot, value = _strict_object(raw, "environment")
    obj = _exact_keys(
        value,
        {
            "schema_version",
            "environment_id",
            "provider",
            "configured_pod_image",
            "execution_image",
            "runtime",
            "model",
            "workload",
            "limits",
            "authority",
        },
        "environment",
    )
    if obj["schema_version"] != STAGEC_RUNPOD_ENVIRONMENT_V1_SCHEMA:
        raise StageCRunPodRunnerError("environment schema differs")
    environment_id = _machine_id(obj["environment_id"], "environment_id")
    _exact_mapping(obj["provider"], _EXPECTED_PROVIDER, "provider")
    _exact_mapping(
        obj["configured_pod_image"],
        _EXPECTED_CONFIGURED_POD_IMAGE,
        "configured_pod_image",
    )

    execution = _exact_keys(
        obj["execution_image"],
        {
            "reference",
            "manifest_digest",
            "manifest_media_type",
            "replaces_configured_pod_image_manifest_digest",
            "bootstrap_source_bundle_ref",
        },
        "execution_image",
    )
    manifest_digest = _digest(
        execution["manifest_digest"], "execution_image.manifest_digest"
    )
    if manifest_digest == STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_MANIFEST_DIGEST:
        raise StageCRunPodRunnerError(
            "derived execution image digest must differ from the configured pod image it replaces"
        )
    expected_execution_reference = (
        STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY + "@" + manifest_digest
    )
    if execution["reference"] != expected_execution_reference:
        raise StageCRunPodRunnerError(
            "execution image reference must be the exact frozen repository and digest"
        )
    _exact_mapping(
        execution["bootstrap_source_bundle_ref"],
        _EXPECTED_BOOTSTRAP_SOURCE_BUNDLE_REF,
        "execution_image.bootstrap_source_bundle_ref",
    )
    if (
        type(execution["manifest_media_type"]) is not str
        or execution["manifest_media_type"]
        not in STAGEC_RUNPOD_EXECUTION_IMAGE_MANIFEST_MEDIA_TYPES
    ):
        raise StageCRunPodRunnerError(
            "execution image manifest media type is outside the admitted exact enum"
        )
    if (
        execution["replaces_configured_pod_image_manifest_digest"]
        != STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_MANIFEST_DIGEST
    ):
        raise StageCRunPodRunnerError(
            "execution image configured-image replacement target differs"
        )

    _exact_mapping(obj["runtime"], _EXPECTED_RUNTIME, "runtime")
    _exact_mapping(obj["model"], _EXPECTED_MODEL, "model")
    _exact_mapping(obj["workload"], _EXPECTED_WORKLOAD, "workload")
    _exact_mapping(obj["limits"], _EXPECTED_LIMITS, "limits")
    _exact_mapping(obj["authority"], _EXPECTED_AUTHORITY, "authority")
    return StageCRunPodEnvironmentV1(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        environment_id=environment_id,
        execution_image_reference=execution["reference"],
        execution_image_manifest_digest=manifest_digest,
        payload=freeze_json(obj),
    )


def _exact_artifact_bytes(
    reference: ArtifactRef,
    raw: bytes | bytearray | memoryview,
    label: str,
) -> tuple[ArtifactRef, bytes]:
    if type(reference) is not ArtifactRef:
        raise StageCRunPodRunnerError(f"{label} reference has the wrong exact type")
    if type(raw) not in (bytes, bytearray, memoryview):
        raise StageCRunPodRunnerError(f"{label} bytes have an unsupported type")
    snapshot = bytes(raw)
    try:
        reconstructed = ArtifactRef(
            artifact_id=reference.artifact_id,
            sha256=reference.sha256,
            byte_length=reference.byte_length,
            media_type=reference.media_type,
        )
    except (SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRunPodRunnerError(
            f"{label} reference scalar fields are invalid"
        ) from exc
    if not snapshot or not reconstructed.verify_bytes(snapshot):
        raise StageCRunPodRunnerError(f"{label} bytes differ from their exact reference")
    return reconstructed, snapshot


def _artifact_ref_from_report(
    value: Any,
    label: str,
    *,
    expected_media_type: str,
    exact_digest_id_prefix: str | None = None,
) -> ArtifactRef:
    obj = _exact_keys(
        value,
        {"artifact_id", "sha256", "byte_length", "media_type"},
        label,
    )
    try:
        reference = ArtifactRef(
            artifact_id=obj["artifact_id"],
            sha256=obj["sha256"],
            byte_length=obj["byte_length"],
            media_type=obj["media_type"],
        )
    except (SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRunPodRunnerError(f"{label} is not an exact artifact ref") from exc
    if reference.media_type != expected_media_type:
        raise StageCRunPodRunnerError(f"{label} media type differs")
    if (
        exact_digest_id_prefix is not None
        and reference.artifact_id
        != exact_digest_id_prefix + reference.sha256.lower()
    ):
        raise StageCRunPodRunnerError(f"{label} artifact id is not digest-derived")
    return reference


def _validate_prerequisite_binding_report(
    reference: ArtifactRef,
    raw: bytes,
) -> None:
    if reference.media_type != STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_MEDIA_TYPE:
        raise StageCRunPodRunnerError(
            "prerequisite binding reference media type differs"
        )
    if (
        reference.artifact_id
        != "stagec-external-binding-report-" + reference.sha256.lower()
    ):
        raise StageCRunPodRunnerError(
            "prerequisite binding artifact id is not digest-derived"
        )
    _, value = _strict_object(raw, "prerequisite binding report")
    obj = _exact_keys(
        value,
        {
            "schema_version",
            "status",
            "error_code",
            "external_trust_authentication",
            "runtime_authorization",
            "snapshot_report",
            "caller_supplied_intake",
            "caller_supplied_admission",
            "boundary",
        },
        "prerequisite binding report",
    )
    expected_scalars = {
        "schema_version": STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_SCHEMA,
        "status": STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS,
        "error_code": "NONE",
        "external_trust_authentication": STAGEC_EXTERNAL_TRUST_AUTHENTICATION,
        "runtime_authorization": STAGEC_EXTERNAL_RUNTIME_AUTHORIZATION,
    }
    for key, expected in expected_scalars.items():
        if obj[key] != expected or type(obj[key]) is not str:
            raise StageCRunPodRunnerError(
                f"prerequisite binding report {key} differs"
            )
    _exact_mapping(
        obj["boundary"],
        {
            "wrappers": "CALLER_SUPPLIED_AND_REPLAYED_NOT_GENERATED",
            "execution": "NOT_GRANTED_OR_PERFORMED",
            "external_trust": "NOT_AUTHENTICATED_BY_SERIALIZED_REPLAY",
        },
        "prerequisite binding report boundary",
    )
    nested_refs = (
        _artifact_ref_from_report(
            obj["snapshot_report"],
            "prerequisite snapshot report",
            expected_media_type=STAGEC_EXTERNAL_PREREQUISITE_REPORT_MEDIA_TYPE,
            exact_digest_id_prefix="stagec-external-intake-report-",
        ),
        _artifact_ref_from_report(
            obj["caller_supplied_intake"],
            "caller-supplied prerequisite intake",
            expected_media_type=STAGEC_PREREQUISITE_INTAKE_MEDIA_TYPE,
        ),
        _artifact_ref_from_report(
            obj["caller_supplied_admission"],
            "caller-supplied prerequisite admission",
            expected_media_type=STAGEC_PREREQUISITE_ADMISSION_MEDIA_TYPE,
        ),
    )
    if (
        len({item.artifact_id for item in nested_refs}) != len(nested_refs)
        or len({item.sha256 for item in nested_refs}) != len(nested_refs)
    ):
        raise StageCRunPodRunnerError(
            "prerequisite binding report references are not identity-distinct"
        )


def _bounded_int(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or isinstance(value, bool) or not minimum <= value <= maximum:
        raise StageCRunPodRunnerError(
            f"{label} must be an exact integer in [{minimum}, {maximum}]"
        )
    return value


def prepare_stagec_runpod_no_provider_call(
    *,
    authorization_ref: ArtifactRef,
    authorization_raw: bytes | bytearray | memoryview,
    prerequisite_binding_ref: ArtifactRef,
    prerequisite_binding_raw: bytes | bytearray | memoryview,
    environment_raw: bytes | bytearray | memoryview,
    quoted_rate_microusd_per_hour: int,
    planned_running_duration_seconds: int,
    projected_storage_microusd: int,
    projected_other_microusd: int,
    already_billed_in_window_microusd: int,
    safety_reserve_microusd: int,
) -> StageCRunPodOfflinePreparation:
    """Perform exact-byte and budget checks with no provider-call capability."""

    detached_authorization_ref, authorization_snapshot = _exact_artifact_bytes(
        authorization_ref, authorization_raw, "authorization"
    )
    try:
        authorization = load_stagec_runpod_authorization_v2(authorization_snapshot)
    except SchemaValidationError as exc:
        raise StageCRunPodRunnerError(
            "authorization bytes are not the exact Stage C RunPod v2 candidate"
        ) from exc
    if (
        type(authorization) is not StageCRunPodAuthorizationV2Artifact
        or canonical_json_bytes(
            _artifact_ref_value(authorization.artifact_ref, "authorization replay")
        )
        != canonical_json_bytes(
            _artifact_ref_value(detached_authorization_ref, "authorization")
        )
        or detached_authorization_ref.media_type
        != STAGEC_RUNPOD_AUTHORIZATION_V2_MEDIA_TYPE
    ):
        raise StageCRunPodRunnerError(
            "authorization reference differs from the strict v2 replay"
        )
    detached_prerequisite_ref, prerequisite_snapshot = _exact_artifact_bytes(
        prerequisite_binding_ref,
        prerequisite_binding_raw,
        "prerequisite binding",
    )
    _validate_prerequisite_binding_report(
        detached_prerequisite_ref,
        prerequisite_snapshot,
    )
    environment = load_stagec_runpod_environment_v1(environment_raw)
    rate = _bounded_int(
        quoted_rate_microusd_per_hour,
        "quoted rate",
        minimum=1,
        maximum=STAGEC_RUNPOD_MAXIMUM_RATE_MICROUSD_PER_HOUR,
    )
    duration = _bounded_int(
        planned_running_duration_seconds,
        "planned running duration",
        minimum=1,
        maximum=STAGEC_RUNPOD_MAXIMUM_RUNNING_DURATION_SECONDS,
    )
    storage = _bounded_int(
        projected_storage_microusd,
        "projected storage charge",
        minimum=0,
        maximum=STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD,
    )
    other = _bounded_int(
        projected_other_microusd,
        "projected other charge",
        minimum=0,
        maximum=STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD,
    )
    already_billed = _bounded_int(
        already_billed_in_window_microusd,
        "already billed in window",
        minimum=0,
        maximum=STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD,
    )
    reserve = _bounded_int(
        safety_reserve_microusd,
        "safety reserve",
        minimum=STAGEC_RUNPOD_MINIMUM_SAFETY_RESERVE_MICROUSD,
        maximum=STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD,
    )
    compute = (rate * duration + 3_599) // 3_600
    aggregate = compute + storage + other + already_billed + reserve
    if aggregate >= STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD:
        raise StageCRunPodRunnerError(
            "projected aggregate provider spend must remain below $100.00"
        )
    return _make_offline_preparation(
        environment=environment,
        authorization=detached_authorization_ref,
        prerequisite_binding=detached_prerequisite_ref,
        quoted_rate_microusd_per_hour=rate,
        planned_running_duration_seconds=duration,
        projected_compute_microusd=compute,
        projected_storage_microusd=storage,
        projected_other_microusd=other,
        already_billed_in_window_microusd=already_billed,
        safety_reserve_microusd=reserve,
        projected_aggregate_microusd=aggregate,
    )


def require_stagec_runpod_external_activation(
    preparation: StageCRunPodOfflinePreparation,
) -> None:
    """Always fail: this source file intentionally cannot start the pod."""

    _require_factory_preparation(preparation)
    raise StageCRunPodRunnerError(
        "external authenticated activation is not implemented by the offline runner"
    )


__all__ = [
    "STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_MANIFEST_DIGEST",
    "STAGEC_RUNPOD_CONFIGURED_POD_IMAGE_TAG",
    "STAGEC_RUNPOD_ENVIRONMENT_V1_MEDIA_TYPE",
    "STAGEC_RUNPOD_ENVIRONMENT_V1_SCHEMA",
    "STAGEC_RUNPOD_DOCKER_V2_MANIFEST_MEDIA_TYPE",
    "STAGEC_RUNPOD_EXECUTION_IMAGE_REPOSITORY",
    "STAGEC_RUNPOD_EXECUTION_IMAGE_MANIFEST_MEDIA_TYPES",
    "STAGEC_RUNPOD_EXTERNAL_ACTIVATION_REQUIRED",
    "STAGEC_RUNPOD_GET_BILLING_PATH",
    "STAGEC_RUNPOD_GET_POD_PATH",
    "STAGEC_RUNPOD_OFFLINE_BLOCKERS",
    "STAGEC_RUNPOD_OFFLINE_PREPARATION_STATE",
    "STAGEC_RUNPOD_OCI_IMAGE_MANIFEST_MEDIA_TYPE",
    "STAGEC_RUNPOD_MINIMUM_SAFETY_RESERVE_MICROUSD",
    "STAGEC_RUNPOD_MAXIMUM_LIVE_PREPARATION_SEALS",
    "STAGEC_RUNPOD_START_PATH",
    "STAGEC_RUNPOD_STOP_PATH",
    "StageCRunPodEnvironmentV1",
    "StageCRunPodOfflinePreparation",
    "StageCRunPodRunnerError",
    "load_stagec_runpod_environment_v1",
    "prepare_stagec_runpod_no_provider_call",
    "require_stagec_runpod_external_activation",
]
