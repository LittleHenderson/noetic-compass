"""Disabled, separately authorized steering and black-box control contracts.

This module records exact plans only.  It has no model, provider, hook,
intervention, network, or spending implementation.  The installed steering
backend is deliberately unavailable and has a fixed canary count of zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
import threading
from typing import Any, NoReturn
from weakref import WeakKeyDictionary

from ._strict_json import (
    canonical_json_bytes,
    freeze_json,
    load_json_object,
    sha256_bytes,
    thaw_json,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_enum,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_string,
    parse_artifact_ref,
)
from .comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    BEHAVIOR_GENERATION,
    CLOSED_WEIGHT,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    NON_AUTHORITY,
    OPEN_WEIGHT,
    STEERING_INTERVENTION,
    STRUCTURE_ONLY,
    SUPPORTED_WITH_EVIDENCE,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelIdentityArtifact,
    replay_comparison_model_capabilities,
    replay_comparison_model_identity,
)


STEERING_PROTOCOL_SCHEMA = "cas_harness_v2.comparison_steering_protocol.v1"
BLACK_BOX_POLICY_CONTROL_SCHEMA = (
    "cas_harness_v2.comparison_black_box_policy_control.v1"
)
STEERING_DIRECTION_SCHEMA = "cas_harness_v2.comparison_steering_direction.v1"
ACTIVATION_COORDINATE_SCHEMA = "cas_harness_v2.comparison_activation_coordinate.v1"
STEERING_CONTROL_SPEC_SCHEMA = "cas_harness_v2.comparison_steering_control_spec.v1"
BLACK_BOX_CONTROL_SPEC_SCHEMA = "cas_harness_v2.comparison_black_box_control_spec.v1"
STEERING_PROTOCOL_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-steering-protocol-v1+json"
)
BLACK_BOX_POLICY_CONTROL_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-black-box-policy-control-v1+json"
)
STEERING_DIRECTION_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-steering-direction-v1+json"
)
ACTIVATION_COORDINATE_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-activation-coordinate-v1+json"
)
STEERING_CONTROL_SPEC_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-steering-control-spec-v1+json"
)
BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-black-box-control-spec-v1+json"
)
FROZEN_COMPARISON_ROSTER_MEDIA_TYPE = (
    "application/vnd.cas-harness.frozen-comparison-roster-v1+json"
)
BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE = (
    "application/vnd.cas-harness.behavioral-comparison-protocol-v1+json"
)

ZERO_DOSE = "ZERO_DOSE"
NULL_DIRECTION = "NULL_DIRECTION"
WRONG_LAYER = "WRONG_LAYER"
RANDOM_VECTOR = "RANDOM_VECTOR"
SIGN_REVERSED = "SIGN_REVERSED"
SHUFFLED_VECTOR = "SHUFFLED_VECTOR"
MEANING_PRESERVATION = "MEANING_PRESERVATION"
UNRELATED_TASK_DAMAGE = "UNRELATED_TASK_DAMAGE"
HOOK_FIRED = "HOOK_FIRED"
ACTIVATION_CHANGED = "ACTIVATION_CHANGED"
OUTPUT_CHANGED = "OUTPUT_CHANGED"
STEERING_CONTROL_NAMES = (
    ZERO_DOSE,
    NULL_DIRECTION,
    WRONG_LAYER,
    RANDOM_VECTOR,
    SIGN_REVERSED,
    SHUFFLED_VECTOR,
    MEANING_PRESERVATION,
    UNRELATED_TASK_DAMAGE,
    HOOK_FIRED,
    ACTIVATION_CHANGED,
    OUTPUT_CHANGED,
)

STRONGER_SYSTEM_INSTRUCTIONS = "STRONGER_SYSTEM_INSTRUCTIONS"
INPUT_FILTERING = "INPUT_FILTERING"
CONTEXT_ISOLATION = "CONTEXT_ISOLATION"
TOOL_PERMISSION_RESTRICTIONS = "TOOL_PERMISSION_RESTRICTIONS"
OUTPUT_VALIDATION = "OUTPUT_VALIDATION"
BLACK_BOX_CONTROL_NAMES = (
    STRONGER_SYSTEM_INSTRUCTIONS,
    INPUT_FILTERING,
    CONTEXT_ISOLATION,
    TOOL_PERMISSION_RESTRICTIONS,
    OUTPUT_VALIDATION,
)

BLACK_BOX_POLICY_CONTROL = "BLACK_BOX_POLICY_CONTROL"
STEERING_DISABLED = "DISABLED"
BACKEND_UNAVAILABLE = "UNAVAILABLE"
SEPARATE_AUTHORIZATION_REQUIRED = "SEPARATE_AUTHORIZATION_REQUIRED"
DOSE_SCALE = 1_000_000
MAX_DOSE_TICKS = 1_000_000_000
STEERING_DIRECTION_METHODS = (
    "MEAN_DIFFERENCE",
    "JSPACE_REGISTERED_BASIS",
    "JVP_VJP_OUTPUT_FUNCTIONAL",
    "TKS_SURFACE_CONTRAST",
    "CAS_OHM_DOSE_DIRECTION",
)

_STATUS = {"scope": STRUCTURE_ONLY, "authority": NON_AUTHORITY}
_STEERING_BOUNDARY = {
    "execution": "NOT_PERFORMED",
    "model_call": "NOT_PERFORMED",
    "provider_call": "NOT_PERFORMED",
    "intervention": STEERING_DISABLED,
    "stagec_activation": "FORBIDDEN",
    "authorization": SEPARATE_AUTHORIZATION_REQUIRED,
    "backend": BACKEND_UNAVAILABLE,
    "canary_count": 0,
}
_BLACK_BOX_BOUNDARY = {
    "execution": "NOT_PERFORMED",
    "model_call": "NOT_PERFORMED",
    "provider_call": "NOT_PERFORMED",
    "internal_activation_access": "UNAVAILABLE_BY_ACCESS_MODEL",
    "mechanism_equivalence_claim": "FORBIDDEN",
}
_FORBIDDEN_STAGEC_PHASES = {
    "stagec-calibration",
    "c-cal",
    "stagec-c-cal",
    "gate5-stagec-qwen-prompt-injection-v0.1",
}
_STEERING_CONTROL_EVIDENCE = {
    ZERO_DOSE: "ZERO_DOSE_BASELINE",
    NULL_DIRECTION: "NULL_DIRECTION_BASELINE",
    WRONG_LAYER: "WRONG_LAYER_CAUSAL_CONTROL",
    RANDOM_VECTOR: "RANDOM_VECTOR_CAUSAL_CONTROL",
    SIGN_REVERSED: "SIGN_REVERSED_CAUSAL_CONTROL",
    SHUFFLED_VECTOR: "SHUFFLED_VECTOR_CAUSAL_CONTROL",
    MEANING_PRESERVATION: "MEANING_PRESERVATION_RECEIPT",
    UNRELATED_TASK_DAMAGE: "UNRELATED_TASK_DAMAGE_RECEIPT",
    HOOK_FIRED: "HOOK_FIRE_RECEIPT",
    ACTIVATION_CHANGED: "ACTIVATION_CHANGE_RECEIPT",
    OUTPUT_CHANGED: "OUTPUT_CHANGE_RECEIPT",
}
_BLACK_BOX_CONTROL_EVIDENCE = {
    STRONGER_SYSTEM_INSTRUCTIONS: "SYSTEM_INSTRUCTION_POLICY_RECEIPT",
    INPUT_FILTERING: "INPUT_FILTER_POLICY_RECEIPT",
    CONTEXT_ISOLATION: "CONTEXT_ISOLATION_POLICY_RECEIPT",
    TOOL_PERMISSION_RESTRICTIONS: "TOOL_PERMISSION_POLICY_RECEIPT",
    OUTPUT_VALIDATION: "OUTPUT_VALIDATION_POLICY_RECEIPT",
}


class ComparisonSteeringValidationError(SchemaValidationError):
    """A steering or black-box control carrier violated its closed schema."""


class SteeringBackendUnavailableError(RuntimeError):
    """No authorized steering backend is installed."""


@dataclass(frozen=True, slots=True)
class SteeringProtocolArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    steering_id: str
    phase_id: str
    identity_ref: ArtifactRef
    capabilities_ref: ArtifactRef
    configuration_ref: ArtifactRef
    shared_protocol_ref: ArtifactRef
    roster_ref: ArtifactRef
    direction_ref: ArtifactRef
    coordinate_ref: ArtifactRef
    control_spec_refs: tuple[ArtifactRef, ...]
    dose_ticks: tuple[int, ...]
    payload: Any
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.steering_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STEERING_PROTOCOL_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class BlackBoxPolicyControlArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    control_id: str
    identity_ref: ArtifactRef
    capabilities_ref: ArtifactRef
    configuration_ref: ArtifactRef
    shared_protocol_ref: ArtifactRef
    roster_ref: ArtifactRef
    control_spec_refs: tuple[ArtifactRef, ...]
    payload: Any
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.control_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=BLACK_BOX_POLICY_CONTROL_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class _UnavailableSeal:
    steering_ref: ArtifactRef
    reason: str


_UNAVAILABLE_LOCK = threading.RLock()
_UNAVAILABLE_SEALS: WeakKeyDictionary[Any, _UnavailableSeal] = WeakKeyDictionary()


class UnavailableSteeringBackend:
    """Factory-only backend that rejects before inspecting a request."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> "UnavailableSteeringBackend":
        del args, kwargs
        raise TypeError("UnavailableSteeringBackend is factory-only")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("UnavailableSteeringBackend cannot be subclassed")

    def __copy__(self) -> NoReturn:
        raise TypeError("UnavailableSteeringBackend cannot be copied or pickled")

    def __deepcopy__(self, memo: Any) -> NoReturn:
        del memo
        raise TypeError("UnavailableSteeringBackend cannot be copied or pickled")

    def __reduce__(self) -> NoReturn:
        raise TypeError("UnavailableSteeringBackend cannot be copied or pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("UnavailableSteeringBackend cannot be copied or pickled")

    def __replace__(self, **changes: Any) -> NoReturn:
        del changes
        raise TypeError("UnavailableSteeringBackend cannot be copied or pickled")

    def attempt(self, request: object) -> NoReturn:
        del request
        seal = _require_unavailable_backend(self)
        raise SteeringBackendUnavailableError(seal.reason)

    @property
    def canary_count(self) -> int:
        _require_unavailable_backend(self)
        return 0

    @property
    def status(self) -> str:
        _require_unavailable_backend(self)
        return BACKEND_UNAVAILABLE


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    _require_ref(reference, "artifact_ref")
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _require_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise ComparisonSteeringValidationError(f"{path} must be an exact ArtifactRef")
    try:
        checked = ArtifactRef(
            artifact_id=value.artifact_id,
            sha256=value.sha256,
            byte_length=value.byte_length,
            media_type=value.media_type,
        )
    except (TypeError, ValueError, SchemaValidationError) as exc:
        raise ComparisonSteeringValidationError(
            f"{path} contains a forged ArtifactRef field: {exc}"
        ) from exc
    if checked != value:
        raise ComparisonSteeringValidationError(f"{path} differs from exact replay")
    return value


def _require_media(reference: ArtifactRef, media_type: str, path: str) -> None:
    _require_ref(reference, path)
    if reference.media_type != media_type:
        raise ComparisonSteeringValidationError(
            f"{path}.media_type must be {media_type!r}"
        )


def _canonical(raw: bytes | bytearray | memoryview, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise ComparisonSteeringValidationError(f"{path} must use canonical JSON")
        return snapshot, value
    except ComparisonSteeringValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise ComparisonSteeringValidationError(f"{path}: {exc}") from exc


def _require_frozen(value: Any, path: str) -> None:
    if type(value) is MappingProxyType:
        for key, child in value.items():
            if type(key) is not str:
                raise ComparisonSteeringValidationError(f"{path} key changed")
            _require_frozen(child, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, child in enumerate(value):
            _require_frozen(child, f"{path}[{index}]")
        return
    if type(value) not in (str, int, bool) and value is not None:
        raise ComparisonSteeringValidationError(f"{path} is not recursively frozen")


def _merge_closure(
    references: tuple[ArtifactRef, ...], *, owner_id: str, path: str
) -> tuple[ArtifactRef, ...]:
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], ArtifactRef] = {}
    ordered: list[ArtifactRef] = []
    for index, reference in enumerate(references):
        reference = _require_ref(reference, f"{path}[{index}]")
        if reference.artifact_id == owner_id:
            raise ComparisonSteeringValidationError(f"{path} collides with owner identity")
        prior = by_id.get(reference.artifact_id)
        if prior is not None:
            if prior != reference:
                raise ComparisonSteeringValidationError(
                    f"{path} reuses artifact_id for different content"
                )
            continue
        content_key = (reference.sha256, reference.byte_length)
        if content_key in by_content:
            raise ComparisonSteeringValidationError(
                f"{path} reuses content under a different artifact_id"
            )
        by_id[reference.artifact_id] = reference
        by_content[content_key] = reference
        ordered.append(reference)
    return tuple(ordered)


def _validate_model(
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    *,
    access_kind: str,
) -> tuple[ComparisonModelIdentityArtifact, ComparisonModelCapabilitiesArtifact]:
    identity = replay_comparison_model_identity(identity)
    capabilities = replay_comparison_model_capabilities(capabilities, identity=identity)
    if identity.access_kind != access_kind or capabilities.access_kind != access_kind:
        raise ComparisonSteeringValidationError(
            f"model must use exact {access_kind} access"
        )
    if capabilities.identity_ref != identity.artifact_ref:
        raise ComparisonSteeringValidationError("capabilities model identity changed")
    return identity, capabilities


def _require_steering_capabilities(
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> None:
    for name in (BEHAVIOR_GENERATION, ACTIVATION_CAPTURE, STEERING_INTERVENTION):
        if capabilities.capability(name).status != SUPPORTED_WITH_EVIDENCE:
            raise ComparisonSteeringValidationError(
                f"{name} must be SUPPORTED_WITH_EVIDENCE"
            )


def _require_behavior_capability(
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> None:
    if capabilities.capability(BEHAVIOR_GENERATION).status != SUPPORTED_WITH_EVIDENCE:
        raise ComparisonSteeringValidationError(
            "BEHAVIOR_GENERATION must be SUPPORTED_WITH_EVIDENCE"
        )


def _control_rows(
    mapping: Any,
    *,
    names: tuple[str, ...],
    media_type: str,
    path: str,
) -> tuple[ArtifactRef, ...]:
    if type(mapping) is not dict or tuple(mapping) != names:
        raise ComparisonSteeringValidationError(
            f"{path} must use every fixed control once in exact order"
        )
    rows: list[ArtifactRef] = []
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], ArtifactRef] = {}
    for name in names:
        reference = _require_ref(mapping[name], f"{path}.{name}")
        _require_media(reference, media_type, f"{path}.{name}")
        if reference.artifact_id in by_id:
            raise ComparisonSteeringValidationError(
                f"{path} reuses artifact_id across control roles"
            )
        content_key = (reference.sha256, reference.byte_length)
        if content_key in by_content:
            raise ComparisonSteeringValidationError(
                f"{path} reuses content across control roles"
            )
        by_id[reference.artifact_id] = reference
        by_content[content_key] = reference
        rows.append(reference)
    return tuple(rows)


def _model_binding_value(
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> dict[str, Any]:
    return {
        "identity_ref": _ref_value(identity.artifact_ref),
        "capabilities_ref": _ref_value(capabilities.artifact_ref),
        "configuration_ref": _ref_value(capabilities.configuration_ref),
    }


def _require_model_binding(
    value: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    path: str,
) -> None:
    model = expect_object(value, path)
    expect_keys(
        model,
        required={"identity_ref", "capabilities_ref", "configuration_ref"},
        path=path,
    )
    if (
        parse_artifact_ref(model["identity_ref"], f"{path}.identity_ref")
        != identity.artifact_ref
        or parse_artifact_ref(
            model["capabilities_ref"], f"{path}.capabilities_ref"
        )
        != capabilities.artifact_ref
        or parse_artifact_ref(
            model["configuration_ref"], f"{path}.configuration_ref"
        )
        != capabilities.configuration_ref
    ):
        raise ComparisonSteeringValidationError(f"{path} changed")


def _require_phase_separate_from_stagec(phase_id: str, path: str) -> str:
    phase_id = expect_machine_id(phase_id, path)
    folded = phase_id.casefold()
    if (
        folded in _FORBIDDEN_STAGEC_PHASES
        or "stagec" in folded
        or "c-cal" in folded
    ):
        raise ComparisonSteeringValidationError(
            "current Stage C identity cannot authorize activation steering"
        )
    return phase_id


def _require_bound_body(
    reference: ArtifactRef,
    raw: bytes | bytearray | memoryview,
    *,
    media_type: str,
    schema: str,
    path: str,
) -> tuple[bytes, dict[str, Any]]:
    _require_media(reference, media_type, path)
    snapshot, value = _canonical(raw, path)
    if not reference.verify_bytes(snapshot):
        raise ComparisonSteeringValidationError(
            f"{path} bytes differ from the caller-bound ArtifactRef"
        )
    if value.get("schema") != schema:
        raise ComparisonSteeringValidationError(f"{path} schema changed")
    return snapshot, value


def build_steering_direction_body(
    *,
    direction_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery_method: str,
) -> bytes:
    """Build exact metadata for a candidate direction; no vector is executed."""

    identity, capabilities = _validate_model(
        identity, capabilities, access_kind=OPEN_WEIGHT
    )
    _require_steering_capabilities(capabilities)
    direction_id = expect_machine_id(direction_id, "direction_id")
    discovery_method = expect_enum(
        discovery_method,
        set(STEERING_DIRECTION_METHODS),
        "discovery_method",
    )
    return canonical_json_bytes(
        {
            "schema": STEERING_DIRECTION_SCHEMA,
            "direction_id": direction_id,
            "model": _model_binding_value(identity, capabilities),
            "discovery_method": discovery_method,
            "normalization": "L2_UNIT_REQUIRED_BEFORE_ANY_FUTURE_EXECUTION",
            "status": dict(_STATUS),
            "boundary": {
                "vector_values": "NOT_INCLUDED_IN_STRUCTURE_ONLY_PLAN",
                "execution": "NOT_PERFORMED",
                "authorization": SEPARATE_AUTHORIZATION_REQUIRED,
            },
        }
    )


def _validate_steering_direction_body(
    reference: ArtifactRef,
    raw: bytes | bytearray | memoryview,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> bytes:
    snapshot, value = _require_bound_body(
        reference,
        raw,
        media_type=STEERING_DIRECTION_MEDIA_TYPE,
        schema=STEERING_DIRECTION_SCHEMA,
        path="direction_body",
    )
    expect_keys(
        value,
        required={
            "schema",
            "direction_id",
            "model",
            "discovery_method",
            "normalization",
            "status",
            "boundary",
        },
        path="direction_body",
    )
    if expect_machine_id(value["direction_id"], "direction_body.direction_id") != reference.artifact_id:
        raise ComparisonSteeringValidationError("direction body identity changed")
    _require_model_binding(
        value["model"], identity=identity, capabilities=capabilities, path="direction_body.model"
    )
    expect_enum(
        value["discovery_method"],
        set(STEERING_DIRECTION_METHODS),
        "direction_body.discovery_method",
    )
    if (
        value["normalization"] != "L2_UNIT_REQUIRED_BEFORE_ANY_FUTURE_EXECUTION"
        or expect_object(value["status"], "direction_body.status") != _STATUS
        or expect_object(value["boundary"], "direction_body.boundary")
        != {
            "vector_values": "NOT_INCLUDED_IN_STRUCTURE_ONLY_PLAN",
            "execution": "NOT_PERFORMED",
            "authorization": SEPARATE_AUTHORIZATION_REQUIRED,
        }
    ):
        raise ComparisonSteeringValidationError("direction body boundary changed")
    return snapshot


def build_activation_coordinate_body(
    *,
    coordinate_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    target_layer_id: str,
    activation_tensor_name: str,
    activation_width: int,
    coordinate_start: int,
    coordinate_count: int,
) -> bytes:
    """Build exact activation geometry metadata for a disabled plan."""

    identity, capabilities = _validate_model(
        identity, capabilities, access_kind=OPEN_WEIGHT
    )
    _require_steering_capabilities(capabilities)
    coordinate_id = expect_machine_id(coordinate_id, "coordinate_id")
    target_layer_id = expect_machine_id(target_layer_id, "target_layer_id")
    activation_tensor_name = expect_machine_id(
        activation_tensor_name, "activation_tensor_name"
    )
    activation_width = expect_int(activation_width, "activation_width", minimum=1)
    coordinate_start = expect_int(
        coordinate_start, "coordinate_start", minimum=0, maximum=activation_width - 1
    )
    coordinate_count = expect_int(
        coordinate_count,
        "coordinate_count",
        minimum=1,
        maximum=activation_width - coordinate_start,
    )
    return canonical_json_bytes(
        {
            "schema": ACTIVATION_COORDINATE_SCHEMA,
            "coordinate_id": coordinate_id,
            "model": _model_binding_value(identity, capabilities),
            "target_layer_id": target_layer_id,
            "activation_tensor_name": activation_tensor_name,
            "activation_width": activation_width,
            "coordinate_start": coordinate_start,
            "coordinate_count": coordinate_count,
            "status": dict(_STATUS),
        }
    )


def _validate_activation_coordinate_body(
    reference: ArtifactRef,
    raw: bytes | bytearray | memoryview,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    target_layer_id: str,
    activation_tensor_name: str,
    activation_width: int,
    coordinate_start: int,
    coordinate_count: int,
) -> bytes:
    snapshot, value = _require_bound_body(
        reference,
        raw,
        media_type=ACTIVATION_COORDINATE_MEDIA_TYPE,
        schema=ACTIVATION_COORDINATE_SCHEMA,
        path="coordinate_body",
    )
    expect_keys(
        value,
        required={
            "schema",
            "coordinate_id",
            "model",
            "target_layer_id",
            "activation_tensor_name",
            "activation_width",
            "coordinate_start",
            "coordinate_count",
            "status",
        },
        path="coordinate_body",
    )
    if expect_machine_id(value["coordinate_id"], "coordinate_body.coordinate_id") != reference.artifact_id:
        raise ComparisonSteeringValidationError("coordinate body identity changed")
    _require_model_binding(
        value["model"], identity=identity, capabilities=capabilities, path="coordinate_body.model"
    )
    observed = (
        expect_machine_id(value["target_layer_id"], "coordinate_body.target_layer_id"),
        expect_machine_id(
            value["activation_tensor_name"], "coordinate_body.activation_tensor_name"
        ),
        expect_int(value["activation_width"], "coordinate_body.activation_width", minimum=1),
        expect_int(value["coordinate_start"], "coordinate_body.coordinate_start"),
        expect_int(value["coordinate_count"], "coordinate_body.coordinate_count", minimum=1),
    )
    if observed != (
        target_layer_id,
        activation_tensor_name,
        activation_width,
        coordinate_start,
        coordinate_count,
    ) or expect_object(value["status"], "coordinate_body.status") != _STATUS:
        raise ComparisonSteeringValidationError("coordinate body geometry changed")
    if coordinate_start + coordinate_count > activation_width:
        raise ComparisonSteeringValidationError("coordinate body exceeds activation width")
    return snapshot


def _build_control_spec_body(
    *,
    schema: str,
    control_id: str,
    control_name: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    evidence_requirement: str,
    control_class: str,
) -> bytes:
    return canonical_json_bytes(
        {
            "schema": schema,
            "control_id": expect_machine_id(control_id, "control_id"),
            "control_name": control_name,
            "control_class": control_class,
            "model": _model_binding_value(identity, capabilities),
            "evidence_requirement": evidence_requirement,
            "status": dict(_STATUS),
        }
    )


def build_steering_control_spec_body(
    *,
    control_id: str,
    control_name: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> bytes:
    identity, capabilities = _validate_model(
        identity, capabilities, access_kind=OPEN_WEIGHT
    )
    _require_steering_capabilities(capabilities)
    control_name = expect_enum(
        control_name, set(STEERING_CONTROL_NAMES), "control_name"
    )
    return _build_control_spec_body(
        schema=STEERING_CONTROL_SPEC_SCHEMA,
        control_id=control_id,
        control_name=control_name,
        identity=identity,
        capabilities=capabilities,
        evidence_requirement=_STEERING_CONTROL_EVIDENCE[control_name],
        control_class="ACTIVATION_STEERING_CONTROL",
    )


def build_black_box_control_spec_body(
    *,
    control_id: str,
    control_name: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> bytes:
    identity, capabilities = _validate_model(
        identity, capabilities, access_kind=CLOSED_WEIGHT
    )
    _require_behavior_capability(capabilities)
    control_name = expect_enum(
        control_name, set(BLACK_BOX_CONTROL_NAMES), "control_name"
    )
    return _build_control_spec_body(
        schema=BLACK_BOX_CONTROL_SPEC_SCHEMA,
        control_id=control_id,
        control_name=control_name,
        identity=identity,
        capabilities=capabilities,
        evidence_requirement=_BLACK_BOX_CONTROL_EVIDENCE[control_name],
        control_class=BLACK_BOX_POLICY_CONTROL,
    )


def _validate_control_spec_bodies(
    references: tuple[ArtifactRef, ...],
    raw_by_name: Any,
    *,
    names: tuple[str, ...],
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    media_type: str,
    schema: str,
    control_class: str,
    evidence: dict[str, str],
    path: str,
) -> tuple[bytes, ...]:
    if type(raw_by_name) is not dict or tuple(raw_by_name) != names:
        raise ComparisonSteeringValidationError(
            f"{path} must provide exact bytes for every control in exact order"
        )
    snapshots: list[bytes] = []
    for name, reference in zip(names, references, strict=True):
        snapshot, value = _require_bound_body(
            reference,
            raw_by_name[name],
            media_type=media_type,
            schema=schema,
            path=f"{path}.{name}",
        )
        expect_keys(
            value,
            required={
                "schema",
                "control_id",
                "control_name",
                "control_class",
                "model",
                "evidence_requirement",
                "status",
            },
            path=f"{path}.{name}",
        )
        if (
            expect_machine_id(value["control_id"], f"{path}.{name}.control_id")
            != reference.artifact_id
            or value["control_name"] != name
            or value["control_class"] != control_class
            or value["evidence_requirement"] != evidence[name]
            or expect_object(value["status"], f"{path}.{name}.status") != _STATUS
        ):
            raise ComparisonSteeringValidationError(
                f"{path}.{name} role or evidence requirement changed"
            )
        _require_model_binding(
            value["model"],
            identity=identity,
            capabilities=capabilities,
            path=f"{path}.{name}.model",
        )
        snapshots.append(snapshot)
    return tuple(snapshots)


def _steering_value(
    *,
    steering_id: str,
    phase_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    shared_protocol_ref: ArtifactRef,
    roster_ref: ArtifactRef,
    direction_ref: ArtifactRef,
    coordinate_ref: ArtifactRef,
    target_layer_id: str,
    activation_tensor_name: str,
    activation_width: int,
    coordinate_start: int,
    coordinate_count: int,
    dose_ticks: tuple[int, ...],
    control_spec_refs: tuple[ArtifactRef, ...],
) -> dict[str, Any]:
    return {
        "schema": STEERING_PROTOCOL_SCHEMA,
        "steering_id": steering_id,
        "phase_id": phase_id,
        "model": {
            "identity_ref": _ref_value(identity.artifact_ref),
            "capabilities_ref": _ref_value(capabilities.artifact_ref),
            "configuration_ref": _ref_value(capabilities.configuration_ref),
        },
        "shared_protocol_ref": _ref_value(shared_protocol_ref),
        "roster_ref": _ref_value(roster_ref),
        "direction_ref": _ref_value(direction_ref),
        "coordinate": {
            "artifact_ref": _ref_value(coordinate_ref),
            "target_layer_id": target_layer_id,
            "activation_tensor_name": activation_tensor_name,
            "activation_width": activation_width,
            "coordinate_start": coordinate_start,
            "coordinate_count": coordinate_count,
        },
        "dose_schedule": {
            "scale": DOSE_SCALE,
            "ticks": list(dose_ticks),
            "selection_policy": "SMALLEST_EFFECTIVE_DOSE_AFTER_ALL_CONTROLS_PASS",
        },
        "controls": [
            {"name": name, "artifact_ref": _ref_value(reference)}
            for name, reference in zip(
                STEERING_CONTROL_NAMES, control_spec_refs, strict=True
            )
        ],
        "status": dict(_STATUS),
        "boundary": dict(_STEERING_BOUNDARY),
    }


def build_steering_protocol(
    *,
    steering_id: str,
    phase_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    shared_protocol_ref: ArtifactRef,
    roster_ref: ArtifactRef,
    direction_ref: ArtifactRef,
    direction_bytes: bytes,
    coordinate_ref: ArtifactRef,
    coordinate_bytes: bytes,
    target_layer_id: str,
    activation_tensor_name: str,
    activation_width: int,
    coordinate_start: int,
    coordinate_count: int,
    dose_ticks: tuple[int, ...],
    control_spec_refs: dict[str, ArtifactRef],
    control_spec_bytes: dict[str, bytes],
) -> SteeringProtocolArtifact:
    """Build a disabled open-weight steering plan with zero execution authority."""

    identity, capabilities = _validate_model(
        identity, capabilities, access_kind=OPEN_WEIGHT
    )
    _require_steering_capabilities(capabilities)
    steering_id = expect_machine_id(steering_id, "steering_id")
    phase_id = _require_phase_separate_from_stagec(phase_id, "phase_id")
    target_layer_id = expect_machine_id(target_layer_id, "target_layer_id")
    activation_tensor_name = expect_machine_id(
        activation_tensor_name, "activation_tensor_name"
    )
    activation_width = expect_int(activation_width, "activation_width", minimum=1)
    coordinate_start = expect_int(
        coordinate_start, "coordinate_start", minimum=0, maximum=activation_width - 1
    )
    coordinate_count = expect_int(
        coordinate_count,
        "coordinate_count",
        minimum=1,
        maximum=activation_width - coordinate_start,
    )
    if type(dose_ticks) is not tuple or len(dose_ticks) < 3:
        raise ComparisonSteeringValidationError(
            "dose_ticks must be an exact tuple with zero and multiple nonzero doses"
        )
    checked_doses = tuple(
        expect_int(item, f"dose_ticks[{index}]", minimum=0, maximum=MAX_DOSE_TICKS)
        for index, item in enumerate(dose_ticks)
    )
    if checked_doses[0] != 0 or any(
        left >= right for left, right in zip(checked_doses, checked_doses[1:])
    ):
        raise ComparisonSteeringValidationError(
            "dose_ticks must start at zero and increase strictly"
        )
    _require_media(
        shared_protocol_ref,
        BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
        "shared_protocol_ref",
    )
    _require_media(
        roster_ref, FROZEN_COMPARISON_ROSTER_MEDIA_TYPE, "roster_ref"
    )
    _require_media(direction_ref, STEERING_DIRECTION_MEDIA_TYPE, "direction_ref")
    _require_media(
        coordinate_ref, ACTIVATION_COORDINATE_MEDIA_TYPE, "coordinate_ref"
    )
    controls = _control_rows(
        control_spec_refs,
        names=STEERING_CONTROL_NAMES,
        media_type=STEERING_CONTROL_SPEC_MEDIA_TYPE,
        path="control_spec_refs",
    )
    _validate_steering_direction_body(
        direction_ref,
        direction_bytes,
        identity=identity,
        capabilities=capabilities,
    )
    _validate_activation_coordinate_body(
        coordinate_ref,
        coordinate_bytes,
        identity=identity,
        capabilities=capabilities,
        target_layer_id=target_layer_id,
        activation_tensor_name=activation_tensor_name,
        activation_width=activation_width,
        coordinate_start=coordinate_start,
        coordinate_count=coordinate_count,
    )
    _validate_control_spec_bodies(
        controls,
        control_spec_bytes,
        names=STEERING_CONTROL_NAMES,
        identity=identity,
        capabilities=capabilities,
        media_type=STEERING_CONTROL_SPEC_MEDIA_TYPE,
        schema=STEERING_CONTROL_SPEC_SCHEMA,
        control_class="ACTIVATION_STEERING_CONTROL",
        evidence=_STEERING_CONTROL_EVIDENCE,
        path="control_spec_bytes",
    )
    raw = canonical_json_bytes(
        _steering_value(
            steering_id=steering_id,
            phase_id=phase_id,
            identity=identity,
            capabilities=capabilities,
            shared_protocol_ref=shared_protocol_ref,
            roster_ref=roster_ref,
            direction_ref=direction_ref,
            coordinate_ref=coordinate_ref,
            target_layer_id=target_layer_id,
            activation_tensor_name=activation_tensor_name,
            activation_width=activation_width,
            coordinate_start=coordinate_start,
            coordinate_count=coordinate_count,
            dose_ticks=checked_doses,
            control_spec_refs=controls,
        )
    )
    return load_steering_protocol(
        raw,
        identity=identity,
        capabilities=capabilities,
        shared_protocol_ref=shared_protocol_ref,
        roster_ref=roster_ref,
        direction_ref=direction_ref,
        direction_bytes=direction_bytes,
        coordinate_ref=coordinate_ref,
        coordinate_bytes=coordinate_bytes,
        control_spec_refs=control_spec_refs,
        control_spec_bytes=control_spec_bytes,
    )


def load_steering_protocol(
    raw: bytes | bytearray | memoryview,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    shared_protocol_ref: ArtifactRef,
    roster_ref: ArtifactRef,
    direction_ref: ArtifactRef,
    direction_bytes: bytes,
    coordinate_ref: ArtifactRef,
    coordinate_bytes: bytes,
    control_spec_refs: dict[str, ArtifactRef],
    control_spec_bytes: dict[str, bytes],
) -> SteeringProtocolArtifact:
    """Load exact steering-plan bytes against all caller-bound dependencies."""

    identity, capabilities = _validate_model(
        identity, capabilities, access_kind=OPEN_WEIGHT
    )
    _require_steering_capabilities(capabilities)
    controls = _control_rows(
        control_spec_refs,
        names=STEERING_CONTROL_NAMES,
        media_type=STEERING_CONTROL_SPEC_MEDIA_TYPE,
        path="control_spec_refs",
    )
    _validate_steering_direction_body(
        direction_ref,
        direction_bytes,
        identity=identity,
        capabilities=capabilities,
    )
    _validate_control_spec_bodies(
        controls,
        control_spec_bytes,
        names=STEERING_CONTROL_NAMES,
        identity=identity,
        capabilities=capabilities,
        media_type=STEERING_CONTROL_SPEC_MEDIA_TYPE,
        schema=STEERING_CONTROL_SPEC_SCHEMA,
        control_class="ACTIVATION_STEERING_CONTROL",
        evidence=_STEERING_CONTROL_EVIDENCE,
        path="control_spec_bytes",
    )
    snapshot, value = _canonical(raw, "steering protocol")
    expect_keys(
        value,
        required={
            "schema",
            "steering_id",
            "phase_id",
            "model",
            "shared_protocol_ref",
            "roster_ref",
            "direction_ref",
            "coordinate",
            "dose_schedule",
            "controls",
            "status",
            "boundary",
        },
        path="$",
    )
    if value["schema"] != STEERING_PROTOCOL_SCHEMA:
        raise ComparisonSteeringValidationError("steering protocol schema drifted")
    steering_id = expect_machine_id(value["steering_id"], "$.steering_id")
    phase_id = _require_phase_separate_from_stagec(value["phase_id"], "$.phase_id")
    model = expect_object(value["model"], "$.model")
    expect_keys(
        model,
        required={"identity_ref", "capabilities_ref", "configuration_ref"},
        path="$.model",
    )
    if (
        parse_artifact_ref(model["identity_ref"], "$.model.identity_ref")
        != identity.artifact_ref
        or parse_artifact_ref(
            model["capabilities_ref"], "$.model.capabilities_ref"
        )
        != capabilities.artifact_ref
        or parse_artifact_ref(
            model["configuration_ref"], "$.model.configuration_ref"
        )
        != capabilities.configuration_ref
    ):
        raise ComparisonSteeringValidationError("steering model binding changed")
    expected_refs = (
        ("shared_protocol_ref", shared_protocol_ref, BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE),
        ("roster_ref", roster_ref, FROZEN_COMPARISON_ROSTER_MEDIA_TYPE),
        ("direction_ref", direction_ref, STEERING_DIRECTION_MEDIA_TYPE),
    )
    for key, expected, media_type in expected_refs:
        _require_media(expected, media_type, key)
        if parse_artifact_ref(value[key], f"$.{key}") != expected:
            raise ComparisonSteeringValidationError(f"{key} changed")
    coordinate = expect_object(value["coordinate"], "$.coordinate")
    expect_keys(
        coordinate,
        required={
            "artifact_ref",
            "target_layer_id",
            "activation_tensor_name",
            "activation_width",
            "coordinate_start",
            "coordinate_count",
        },
        path="$.coordinate",
    )
    _require_media(coordinate_ref, ACTIVATION_COORDINATE_MEDIA_TYPE, "coordinate_ref")
    if parse_artifact_ref(coordinate["artifact_ref"], "$.coordinate.artifact_ref") != coordinate_ref:
        raise ComparisonSteeringValidationError("coordinate_ref changed")
    target_layer_id = expect_machine_id(
        coordinate["target_layer_id"], "$.coordinate.target_layer_id"
    )
    tensor_name = expect_machine_id(
        coordinate["activation_tensor_name"], "$.coordinate.activation_tensor_name"
    )
    width = expect_int(coordinate["activation_width"], "$.coordinate.activation_width", minimum=1)
    start = expect_int(
        coordinate["coordinate_start"],
        "$.coordinate.coordinate_start",
        minimum=0,
        maximum=width - 1,
    )
    count = expect_int(
        coordinate["coordinate_count"],
        "$.coordinate.coordinate_count",
        minimum=1,
        maximum=width - start,
    )
    _validate_activation_coordinate_body(
        coordinate_ref,
        coordinate_bytes,
        identity=identity,
        capabilities=capabilities,
        target_layer_id=target_layer_id,
        activation_tensor_name=tensor_name,
        activation_width=width,
        coordinate_start=start,
        coordinate_count=count,
    )
    dose = expect_object(value["dose_schedule"], "$.dose_schedule")
    expect_keys(
        dose,
        required={"scale", "ticks", "selection_policy"},
        path="$.dose_schedule",
    )
    if dose["scale"] != DOSE_SCALE or dose["selection_policy"] != "SMALLEST_EFFECTIVE_DOSE_AFTER_ALL_CONTROLS_PASS":
        raise ComparisonSteeringValidationError("dose schedule policy changed")
    ticks_raw = expect_list(dose["ticks"], "$.dose_schedule.ticks")
    ticks = tuple(
        expect_int(item, f"$.dose_schedule.ticks[{index}]", minimum=0, maximum=MAX_DOSE_TICKS)
        for index, item in enumerate(ticks_raw)
    )
    if len(ticks) < 3 or ticks[0] != 0 or any(
        left >= right for left, right in zip(ticks, ticks[1:])
    ):
        raise ComparisonSteeringValidationError("dose schedule changed")
    rows = expect_list(value["controls"], "$.controls")
    if len(rows) != len(STEERING_CONTROL_NAMES):
        raise ComparisonSteeringValidationError("steering controls changed cardinality")
    for index, (row_value, name, expected_ref) in enumerate(
        zip(rows, STEERING_CONTROL_NAMES, controls, strict=True)
    ):
        row = expect_object(row_value, f"$.controls[{index}]")
        expect_keys(row, required={"name", "artifact_ref"}, path=f"$.controls[{index}]")
        if row["name"] != name or parse_artifact_ref(
            row["artifact_ref"], f"$.controls[{index}].artifact_ref"
        ) != expected_ref:
            raise ComparisonSteeringValidationError("steering control order or binding changed")
    if expect_object(value["status"], "$.status") != _STATUS:
        raise ComparisonSteeringValidationError("steering status changed")
    if expect_object(value["boundary"], "$.boundary") != _STEERING_BOUNDARY:
        raise ComparisonSteeringValidationError("steering boundary changed")
    closure = _merge_closure(
        (
            identity.artifact_ref,
            *identity.artifact_refs,
            capabilities.artifact_ref,
            *capabilities.artifact_refs,
            shared_protocol_ref,
            roster_ref,
            direction_ref,
            coordinate_ref,
            *controls,
        ),
        owner_id=steering_id,
        path="artifact_refs",
    )
    return SteeringProtocolArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        steering_id=steering_id,
        phase_id=phase_id,
        identity_ref=identity.artifact_ref,
        capabilities_ref=capabilities.artifact_ref,
        configuration_ref=capabilities.configuration_ref,
        shared_protocol_ref=shared_protocol_ref,
        roster_ref=roster_ref,
        direction_ref=direction_ref,
        coordinate_ref=coordinate_ref,
        control_spec_refs=controls,
        dose_ticks=ticks,
        payload=freeze_json(value),
        artifact_refs=closure,
    )


def _require_exact_ref_tuple(value: Any, path: str) -> tuple[ArtifactRef, ...]:
    if type(value) is not tuple:
        raise ComparisonSteeringValidationError(f"{path} must be an exact tuple")
    for index, reference in enumerate(value):
        _require_ref(reference, f"{path}[{index}]")
    return value


def _require_exact_steering_projection(
    artifact: SteeringProtocolArtifact,
) -> None:
    if type(artifact) is not SteeringProtocolArtifact:
        raise ComparisonSteeringValidationError(
            "artifact must be an exact SteeringProtocolArtifact"
        )
    if type(artifact.raw_bytes) is not bytes:
        raise ComparisonSteeringValidationError("artifact.raw_bytes must be exact bytes")
    if type(artifact.sha256) is not str or artifact.sha256 != sha256_bytes(
        artifact.raw_bytes
    ):
        raise ComparisonSteeringValidationError("artifact.sha256 changed")
    if type(artifact.byte_length) is not int or artifact.byte_length != len(
        artifact.raw_bytes
    ):
        raise ComparisonSteeringValidationError("artifact.byte_length changed")
    expect_machine_id(artifact.steering_id, "artifact.steering_id")
    _require_phase_separate_from_stagec(artifact.phase_id, "artifact.phase_id")
    for name in (
        "identity_ref",
        "capabilities_ref",
        "configuration_ref",
        "shared_protocol_ref",
        "roster_ref",
        "direction_ref",
        "coordinate_ref",
    ):
        _require_ref(getattr(artifact, name), f"artifact.{name}")
    controls = _require_exact_ref_tuple(
        artifact.control_spec_refs, "artifact.control_spec_refs"
    )
    if len(controls) != len(STEERING_CONTROL_NAMES):
        raise ComparisonSteeringValidationError("artifact control count changed")
    if type(artifact.dose_ticks) is not tuple:
        raise ComparisonSteeringValidationError("artifact.dose_ticks changed type")
    for index, tick in enumerate(artifact.dose_ticks):
        expect_int(tick, f"artifact.dose_ticks[{index}]", maximum=MAX_DOSE_TICKS)
    _require_exact_ref_tuple(artifact.artifact_refs, "artifact.artifact_refs")
    _require_frozen(artifact.payload, "artifact.payload")
    try:
        _, value = _canonical(artifact.raw_bytes, "artifact.raw_bytes")
        model = expect_object(value["model"], "artifact.raw_bytes.model")
        coordinate = expect_object(
            value["coordinate"], "artifact.raw_bytes.coordinate"
        )
        controls_value = expect_list(
            value["controls"], "artifact.raw_bytes.controls"
        )
        dose = expect_object(
            value["dose_schedule"], "artifact.raw_bytes.dose_schedule"
        )
        if (
            value["steering_id"] != artifact.steering_id
            or value["phase_id"] != artifact.phase_id
            or parse_artifact_ref(
                model["identity_ref"], "artifact.raw_bytes.model.identity_ref"
            )
            != artifact.identity_ref
            or parse_artifact_ref(
                model["capabilities_ref"],
                "artifact.raw_bytes.model.capabilities_ref",
            )
            != artifact.capabilities_ref
            or parse_artifact_ref(
                model["configuration_ref"],
                "artifact.raw_bytes.model.configuration_ref",
            )
            != artifact.configuration_ref
            or parse_artifact_ref(
                value["shared_protocol_ref"],
                "artifact.raw_bytes.shared_protocol_ref",
            )
            != artifact.shared_protocol_ref
            or parse_artifact_ref(
                value["roster_ref"], "artifact.raw_bytes.roster_ref"
            )
            != artifact.roster_ref
            or parse_artifact_ref(
                value["direction_ref"], "artifact.raw_bytes.direction_ref"
            )
            != artifact.direction_ref
            or parse_artifact_ref(
                coordinate["artifact_ref"],
                "artifact.raw_bytes.coordinate.artifact_ref",
            )
            != artifact.coordinate_ref
            or tuple(
                parse_artifact_ref(
                    expect_object(row, f"artifact.raw_bytes.controls[{index}]")[
                        "artifact_ref"
                    ],
                    f"artifact.raw_bytes.controls[{index}].artifact_ref",
                )
                for index, row in enumerate(controls_value)
            )
            != artifact.control_spec_refs
            or tuple(dose["ticks"]) != artifact.dose_ticks
        ):
            raise ComparisonSteeringValidationError(
                "artifact fields differ from their canonical raw projection"
            )
        if canonical_json_bytes(thaw_json(artifact.payload)) != artifact.raw_bytes:
            raise ComparisonSteeringValidationError(
                "artifact.payload differs from exact canonical raw bytes"
            )
        artifact.artifact_ref
    except (TypeError, ValueError, SchemaValidationError) as exc:
        raise ComparisonSteeringValidationError(
            f"artifact projection is forged: {exc}"
        ) from exc


def replay_steering_protocol(
    artifact: SteeringProtocolArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    direction_bytes: bytes,
    coordinate_bytes: bytes,
    control_spec_refs: dict[str, ArtifactRef],
    control_spec_bytes: dict[str, bytes],
) -> SteeringProtocolArtifact:
    """Freshly replay one exact disabled steering protocol."""

    _require_exact_steering_projection(artifact)
    replayed = load_steering_protocol(
        artifact.raw_bytes,
        identity=identity,
        capabilities=capabilities,
        shared_protocol_ref=artifact.shared_protocol_ref,
        roster_ref=artifact.roster_ref,
        direction_ref=artifact.direction_ref,
        direction_bytes=direction_bytes,
        coordinate_ref=artifact.coordinate_ref,
        coordinate_bytes=coordinate_bytes,
        control_spec_refs=control_spec_refs,
        control_spec_bytes=control_spec_bytes,
    )
    _require_exact_steering_projection(replayed)
    if replayed != artifact:
        raise ComparisonSteeringValidationError("steering artifact differs from fresh replay")
    return replayed


def _black_box_value(
    *,
    control_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    shared_protocol_ref: ArtifactRef,
    roster_ref: ArtifactRef,
    control_spec_refs: tuple[ArtifactRef, ...],
) -> dict[str, Any]:
    return {
        "schema": BLACK_BOX_POLICY_CONTROL_SCHEMA,
        "control_id": control_id,
        "control_label": BLACK_BOX_POLICY_CONTROL,
        "model": {
            "identity_ref": _ref_value(identity.artifact_ref),
            "capabilities_ref": _ref_value(capabilities.artifact_ref),
            "configuration_ref": _ref_value(capabilities.configuration_ref),
        },
        "shared_protocol_ref": _ref_value(shared_protocol_ref),
        "roster_ref": _ref_value(roster_ref),
        "controls": [
            {"name": name, "artifact_ref": _ref_value(reference)}
            for name, reference in zip(
                BLACK_BOX_CONTROL_NAMES, control_spec_refs, strict=True
            )
        ],
        "status": dict(_STATUS),
        "boundary": dict(_BLACK_BOX_BOUNDARY),
    }


def build_black_box_policy_control(
    *,
    control_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    shared_protocol_ref: ArtifactRef,
    roster_ref: ArtifactRef,
    control_spec_refs: dict[str, ArtifactRef],
    control_spec_bytes: dict[str, bytes],
) -> BlackBoxPolicyControlArtifact:
    """Build a closed-model policy-control plan, never activation steering."""

    identity, capabilities = _validate_model(
        identity, capabilities, access_kind=CLOSED_WEIGHT
    )
    _require_behavior_capability(capabilities)
    control_id = expect_machine_id(control_id, "control_id")
    _require_media(
        shared_protocol_ref,
        BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
        "shared_protocol_ref",
    )
    _require_media(roster_ref, FROZEN_COMPARISON_ROSTER_MEDIA_TYPE, "roster_ref")
    controls = _control_rows(
        control_spec_refs,
        names=BLACK_BOX_CONTROL_NAMES,
        media_type=BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE,
        path="control_spec_refs",
    )
    _validate_control_spec_bodies(
        controls,
        control_spec_bytes,
        names=BLACK_BOX_CONTROL_NAMES,
        identity=identity,
        capabilities=capabilities,
        media_type=BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE,
        schema=BLACK_BOX_CONTROL_SPEC_SCHEMA,
        control_class=BLACK_BOX_POLICY_CONTROL,
        evidence=_BLACK_BOX_CONTROL_EVIDENCE,
        path="control_spec_bytes",
    )
    raw = canonical_json_bytes(
        _black_box_value(
            control_id=control_id,
            identity=identity,
            capabilities=capabilities,
            shared_protocol_ref=shared_protocol_ref,
            roster_ref=roster_ref,
            control_spec_refs=controls,
        )
    )
    return load_black_box_policy_control(
        raw,
        identity=identity,
        capabilities=capabilities,
        shared_protocol_ref=shared_protocol_ref,
        roster_ref=roster_ref,
        control_spec_refs=control_spec_refs,
        control_spec_bytes=control_spec_bytes,
    )


def load_black_box_policy_control(
    raw: bytes | bytearray | memoryview,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    shared_protocol_ref: ArtifactRef,
    roster_ref: ArtifactRef,
    control_spec_refs: dict[str, ArtifactRef],
    control_spec_bytes: dict[str, bytes],
) -> BlackBoxPolicyControlArtifact:
    """Load exact black-box control bytes against a closed model binding."""

    identity, capabilities = _validate_model(
        identity, capabilities, access_kind=CLOSED_WEIGHT
    )
    _require_behavior_capability(capabilities)
    controls = _control_rows(
        control_spec_refs,
        names=BLACK_BOX_CONTROL_NAMES,
        media_type=BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE,
        path="control_spec_refs",
    )
    _validate_control_spec_bodies(
        controls,
        control_spec_bytes,
        names=BLACK_BOX_CONTROL_NAMES,
        identity=identity,
        capabilities=capabilities,
        media_type=BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE,
        schema=BLACK_BOX_CONTROL_SPEC_SCHEMA,
        control_class=BLACK_BOX_POLICY_CONTROL,
        evidence=_BLACK_BOX_CONTROL_EVIDENCE,
        path="control_spec_bytes",
    )
    snapshot, value = _canonical(raw, "black-box policy control")
    expect_keys(
        value,
        required={
            "schema",
            "control_id",
            "control_label",
            "model",
            "shared_protocol_ref",
            "roster_ref",
            "controls",
            "status",
            "boundary",
        },
        path="$",
    )
    if value["schema"] != BLACK_BOX_POLICY_CONTROL_SCHEMA or value["control_label"] != BLACK_BOX_POLICY_CONTROL:
        raise ComparisonSteeringValidationError("black-box control schema or label changed")
    control_id = expect_machine_id(value["control_id"], "$.control_id")
    model = expect_object(value["model"], "$.model")
    expect_keys(
        model,
        required={"identity_ref", "capabilities_ref", "configuration_ref"},
        path="$.model",
    )
    if (
        parse_artifact_ref(model["identity_ref"], "$.model.identity_ref") != identity.artifact_ref
        or parse_artifact_ref(model["capabilities_ref"], "$.model.capabilities_ref") != capabilities.artifact_ref
        or parse_artifact_ref(model["configuration_ref"], "$.model.configuration_ref") != capabilities.configuration_ref
    ):
        raise ComparisonSteeringValidationError("black-box model binding changed")
    _require_media(shared_protocol_ref, BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE, "shared_protocol_ref")
    _require_media(roster_ref, FROZEN_COMPARISON_ROSTER_MEDIA_TYPE, "roster_ref")
    if parse_artifact_ref(value["shared_protocol_ref"], "$.shared_protocol_ref") != shared_protocol_ref or parse_artifact_ref(value["roster_ref"], "$.roster_ref") != roster_ref:
        raise ComparisonSteeringValidationError("black-box protocol or roster changed")
    rows = expect_list(value["controls"], "$.controls")
    if len(rows) != len(BLACK_BOX_CONTROL_NAMES):
        raise ComparisonSteeringValidationError("black-box controls changed cardinality")
    for index, (row_value, name, expected_ref) in enumerate(zip(rows, BLACK_BOX_CONTROL_NAMES, controls, strict=True)):
        row = expect_object(row_value, f"$.controls[{index}]")
        expect_keys(row, required={"name", "artifact_ref"}, path=f"$.controls[{index}]")
        if row["name"] != name or parse_artifact_ref(row["artifact_ref"], f"$.controls[{index}].artifact_ref") != expected_ref:
            raise ComparisonSteeringValidationError("black-box control order or binding changed")
    if expect_object(value["status"], "$.status") != _STATUS or expect_object(value["boundary"], "$.boundary") != _BLACK_BOX_BOUNDARY:
        raise ComparisonSteeringValidationError("black-box status or boundary changed")
    closure = _merge_closure(
        (
            identity.artifact_ref,
            *identity.artifact_refs,
            capabilities.artifact_ref,
            *capabilities.artifact_refs,
            shared_protocol_ref,
            roster_ref,
            *controls,
        ),
        owner_id=control_id,
        path="artifact_refs",
    )
    return BlackBoxPolicyControlArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        control_id=control_id,
        identity_ref=identity.artifact_ref,
        capabilities_ref=capabilities.artifact_ref,
        configuration_ref=capabilities.configuration_ref,
        shared_protocol_ref=shared_protocol_ref,
        roster_ref=roster_ref,
        control_spec_refs=controls,
        payload=freeze_json(value),
        artifact_refs=closure,
    )


def _require_exact_black_box_projection(
    artifact: BlackBoxPolicyControlArtifact,
) -> None:
    if type(artifact) is not BlackBoxPolicyControlArtifact:
        raise ComparisonSteeringValidationError(
            "artifact must be an exact BlackBoxPolicyControlArtifact"
        )
    if type(artifact.raw_bytes) is not bytes:
        raise ComparisonSteeringValidationError("artifact.raw_bytes must be exact bytes")
    if type(artifact.sha256) is not str or artifact.sha256 != sha256_bytes(
        artifact.raw_bytes
    ):
        raise ComparisonSteeringValidationError("artifact.sha256 changed")
    if type(artifact.byte_length) is not int or artifact.byte_length != len(
        artifact.raw_bytes
    ):
        raise ComparisonSteeringValidationError("artifact.byte_length changed")
    expect_machine_id(artifact.control_id, "artifact.control_id")
    for name in (
        "identity_ref",
        "capabilities_ref",
        "configuration_ref",
        "shared_protocol_ref",
        "roster_ref",
    ):
        _require_ref(getattr(artifact, name), f"artifact.{name}")
    controls = _require_exact_ref_tuple(
        artifact.control_spec_refs, "artifact.control_spec_refs"
    )
    if len(controls) != len(BLACK_BOX_CONTROL_NAMES):
        raise ComparisonSteeringValidationError("artifact control count changed")
    _require_exact_ref_tuple(artifact.artifact_refs, "artifact.artifact_refs")
    _require_frozen(artifact.payload, "artifact.payload")
    try:
        _, value = _canonical(artifact.raw_bytes, "artifact.raw_bytes")
        model = expect_object(value["model"], "artifact.raw_bytes.model")
        controls_value = expect_list(
            value["controls"], "artifact.raw_bytes.controls"
        )
        if (
            value["control_id"] != artifact.control_id
            or parse_artifact_ref(
                model["identity_ref"], "artifact.raw_bytes.model.identity_ref"
            )
            != artifact.identity_ref
            or parse_artifact_ref(
                model["capabilities_ref"],
                "artifact.raw_bytes.model.capabilities_ref",
            )
            != artifact.capabilities_ref
            or parse_artifact_ref(
                model["configuration_ref"],
                "artifact.raw_bytes.model.configuration_ref",
            )
            != artifact.configuration_ref
            or parse_artifact_ref(
                value["shared_protocol_ref"],
                "artifact.raw_bytes.shared_protocol_ref",
            )
            != artifact.shared_protocol_ref
            or parse_artifact_ref(
                value["roster_ref"], "artifact.raw_bytes.roster_ref"
            )
            != artifact.roster_ref
            or tuple(
                parse_artifact_ref(
                    expect_object(row, f"artifact.raw_bytes.controls[{index}]")[
                        "artifact_ref"
                    ],
                    f"artifact.raw_bytes.controls[{index}].artifact_ref",
                )
                for index, row in enumerate(controls_value)
            )
            != artifact.control_spec_refs
        ):
            raise ComparisonSteeringValidationError(
                "artifact fields differ from their canonical raw projection"
            )
        if canonical_json_bytes(thaw_json(artifact.payload)) != artifact.raw_bytes:
            raise ComparisonSteeringValidationError(
                "artifact.payload differs from exact canonical raw bytes"
            )
        artifact.artifact_ref
    except (TypeError, ValueError, SchemaValidationError) as exc:
        raise ComparisonSteeringValidationError(
            f"artifact projection is forged: {exc}"
        ) from exc


def replay_black_box_policy_control(
    artifact: BlackBoxPolicyControlArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    control_spec_refs: dict[str, ArtifactRef],
    control_spec_bytes: dict[str, bytes],
) -> BlackBoxPolicyControlArtifact:
    """Freshly replay one exact black-box policy-control plan."""

    _require_exact_black_box_projection(artifact)
    replayed = load_black_box_policy_control(
        artifact.raw_bytes,
        identity=identity,
        capabilities=capabilities,
        shared_protocol_ref=artifact.shared_protocol_ref,
        roster_ref=artifact.roster_ref,
        control_spec_refs=control_spec_refs,
        control_spec_bytes=control_spec_bytes,
    )
    _require_exact_black_box_projection(replayed)
    if replayed != artifact:
        raise ComparisonSteeringValidationError("black-box artifact differs from fresh replay")
    return replayed


def build_unavailable_steering_backend(
    *,
    steering: SteeringProtocolArtifact,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    direction_bytes: bytes,
    coordinate_bytes: bytes,
    control_spec_refs: dict[str, ArtifactRef],
    control_spec_bytes: dict[str, bytes],
    reason: str,
) -> UnavailableSteeringBackend:
    """Build the only installed steering backend: a fail-before-use sentinel."""

    replayed = replay_steering_protocol(
        steering,
        identity=identity,
        capabilities=capabilities,
        direction_bytes=direction_bytes,
        coordinate_bytes=coordinate_bytes,
        control_spec_refs=control_spec_refs,
        control_spec_bytes=control_spec_bytes,
    )
    if replayed != steering or not steering.artifact_ref.verify_bytes(
        steering.raw_bytes
    ):
        raise ComparisonSteeringValidationError(
            "steering artifact does not bind its exact canonical bytes"
        )
    reason = expect_string(reason, "reason", maximum=512)
    backend = object.__new__(UnavailableSteeringBackend)
    with _UNAVAILABLE_LOCK:
        _UNAVAILABLE_SEALS[backend] = _UnavailableSeal(
            steering_ref=steering.artifact_ref,
            reason=reason,
        )
    return backend


def _require_unavailable_backend(value: Any) -> _UnavailableSeal:
    if type(value) is not UnavailableSteeringBackend:
        raise ComparisonSteeringValidationError("backend type changed")
    with _UNAVAILABLE_LOCK:
        seal = _UNAVAILABLE_SEALS.get(value)
    if seal is None:
        raise ComparisonSteeringValidationError("backend is not a factory-sealed result")
    return seal


__all__ = (
    "STEERING_PROTOCOL_SCHEMA",
    "BLACK_BOX_POLICY_CONTROL_SCHEMA",
    "STEERING_DIRECTION_SCHEMA",
    "ACTIVATION_COORDINATE_SCHEMA",
    "STEERING_CONTROL_SPEC_SCHEMA",
    "BLACK_BOX_CONTROL_SPEC_SCHEMA",
    "STEERING_PROTOCOL_MEDIA_TYPE",
    "BLACK_BOX_POLICY_CONTROL_MEDIA_TYPE",
    "STEERING_DIRECTION_MEDIA_TYPE",
    "ACTIVATION_COORDINATE_MEDIA_TYPE",
    "STEERING_CONTROL_SPEC_MEDIA_TYPE",
    "BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE",
    "FROZEN_COMPARISON_ROSTER_MEDIA_TYPE",
    "ZERO_DOSE",
    "NULL_DIRECTION",
    "WRONG_LAYER",
    "RANDOM_VECTOR",
    "SIGN_REVERSED",
    "SHUFFLED_VECTOR",
    "MEANING_PRESERVATION",
    "UNRELATED_TASK_DAMAGE",
    "HOOK_FIRED",
    "ACTIVATION_CHANGED",
    "OUTPUT_CHANGED",
    "STEERING_CONTROL_NAMES",
    "STRONGER_SYSTEM_INSTRUCTIONS",
    "INPUT_FILTERING",
    "CONTEXT_ISOLATION",
    "TOOL_PERMISSION_RESTRICTIONS",
    "OUTPUT_VALIDATION",
    "BLACK_BOX_CONTROL_NAMES",
    "BLACK_BOX_POLICY_CONTROL",
    "STEERING_DISABLED",
    "BACKEND_UNAVAILABLE",
    "SEPARATE_AUTHORIZATION_REQUIRED",
    "DOSE_SCALE",
    "STEERING_DIRECTION_METHODS",
    "ComparisonSteeringValidationError",
    "SteeringBackendUnavailableError",
    "SteeringProtocolArtifact",
    "BlackBoxPolicyControlArtifact",
    "UnavailableSteeringBackend",
    "build_steering_direction_body",
    "build_activation_coordinate_body",
    "build_steering_control_spec_body",
    "build_black_box_control_spec_body",
    "build_steering_protocol",
    "load_steering_protocol",
    "replay_steering_protocol",
    "build_black_box_policy_control",
    "load_black_box_policy_control",
    "replay_black_box_policy_control",
    "build_unavailable_steering_backend",
)
