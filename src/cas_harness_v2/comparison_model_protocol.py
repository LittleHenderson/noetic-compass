"""Strict, provider-neutral comparison model and observation carriers.

The carriers in this module validate immutable, canonical JSON associations.
They do not call a model or provider, grant execution authority, expose hidden
state, authorize an intervention, or establish a scientific conclusion.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ._strict_json import canonical_json_bytes, freeze_json, load_json_object, sha256_bytes
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_enum,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    parse_artifact_ref,
)


COMPARISON_MODEL_IDENTITY_SCHEMA = "cas_harness_v2.comparison_model_identity.v1"
COMPARISON_MODEL_CAPABILITIES_SCHEMA = (
    "cas_harness_v2.comparison_model_capabilities.v1"
)
BEHAVIORAL_OBSERVATION_SCHEMA = "cas_harness_v2.behavioral_observation.v1"
COMPARISON_MODEL_WEIGHT_IDENTITY_SCHEMA = (
    "cas_harness_v2.comparison_model_weight_identity.v1"
)
COMPARISON_MODEL_CONFIGURATION_SCHEMA = (
    "cas_harness_v2.comparison_model_configuration.v1"
)
COMPARISON_CAPABILITY_EVIDENCE_SCHEMA = (
    "cas_harness_v2.comparison_capability_evidence.v1"
)

COMPARISON_MODEL_IDENTITY_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-model-identity-v1+json"
)
COMPARISON_MODEL_CAPABILITIES_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-model-capabilities-v1+json"
)
BEHAVIORAL_OBSERVATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.behavioral-observation-v1+json"
)
COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-model-weight-identity-v1+json"
)
COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-model-configuration-v1+json"
)
COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-capability-evidence-v1+json"
)
BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE = (
    "application/vnd.cas-harness.behavioral-comparison-protocol-v1+json"
)
BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE = (
    "application/vnd.cas-harness.behavioral-comparison-case-v1+json"
)
RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE = (
    "application/vnd.cas-harness.raw-behavioral-response-v1+json"
)
RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE = (
    "application/vnd.cas-harness.raw-behavioral-tool-calls-v1+json"
)

OPEN_WEIGHT = "OPEN_WEIGHT"
CLOSED_WEIGHT = "CLOSED_WEIGHT"
REPLAY = "REPLAY"
MODEL_ACCESS_KINDS = (OPEN_WEIGHT, CLOSED_WEIGHT, REPLAY)

STRUCTURE_ONLY = "STRUCTURE_ONLY"
NON_AUTHORITY = "NON_AUTHORITY"

WEIGHT_IDENTITY_AVAILABLE_WITH_EVIDENCE = "AVAILABLE_WITH_EVIDENCE"
WEIGHT_IDENTITY_UNAVAILABLE_BY_ACCESS_MODEL = "UNAVAILABLE_BY_ACCESS_MODEL"
WEIGHT_IDENTITY_UNAVAILABLE_IN_REPLAY = "UNAVAILABLE_IN_REPLAY"

BEHAVIOR_GENERATION = "BEHAVIOR_GENERATION"
TOOL_CALL_OBSERVATION = "TOOL_CALL_OBSERVATION"
LOGPROB_OBSERVATION = "LOGPROB_OBSERVATION"
HIDDEN_STATE_OBSERVATION = "HIDDEN_STATE_OBSERVATION"
ACTIVATION_CAPTURE = "ACTIVATION_CAPTURE"
STEERING_INTERVENTION = "STEERING_INTERVENTION"
CAPABILITY_NAMES = (
    BEHAVIOR_GENERATION,
    TOOL_CALL_OBSERVATION,
    LOGPROB_OBSERVATION,
    HIDDEN_STATE_OBSERVATION,
    ACTIVATION_CAPTURE,
    STEERING_INTERVENTION,
)

SUPPORTED_WITH_EVIDENCE = "SUPPORTED_WITH_EVIDENCE"
UNAVAILABLE_BY_ACCESS_MODEL = "UNAVAILABLE_BY_ACCESS_MODEL"
UNAVAILABLE_IN_REPLAY = "UNAVAILABLE_IN_REPLAY"
UNAVAILABLE_NOT_IMPLEMENTED = "UNAVAILABLE_NOT_IMPLEMENTED"
UNKNOWN_UNVERIFIED = "UNKNOWN_UNVERIFIED"
CAPABILITY_STATUSES = (
    SUPPORTED_WITH_EVIDENCE,
    UNAVAILABLE_BY_ACCESS_MODEL,
    UNAVAILABLE_IN_REPLAY,
    UNAVAILABLE_NOT_IMPLEMENTED,
    UNKNOWN_UNVERIFIED,
)

OBSERVED = "OBSERVED"
UNAVAILABLE = "UNAVAILABLE"
OBSERVATION_STATUSES = (OBSERVED, UNAVAILABLE)

__all__ = (
    "COMPARISON_MODEL_IDENTITY_SCHEMA",
    "COMPARISON_MODEL_CAPABILITIES_SCHEMA",
    "BEHAVIORAL_OBSERVATION_SCHEMA",
    "COMPARISON_MODEL_WEIGHT_IDENTITY_SCHEMA",
    "COMPARISON_MODEL_CONFIGURATION_SCHEMA",
    "COMPARISON_CAPABILITY_EVIDENCE_SCHEMA",
    "COMPARISON_MODEL_IDENTITY_MEDIA_TYPE",
    "COMPARISON_MODEL_CAPABILITIES_MEDIA_TYPE",
    "BEHAVIORAL_OBSERVATION_MEDIA_TYPE",
    "COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE",
    "COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE",
    "COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE",
    "BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE",
    "BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE",
    "RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE",
    "RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE",
    "OPEN_WEIGHT",
    "CLOSED_WEIGHT",
    "REPLAY",
    "MODEL_ACCESS_KINDS",
    "STRUCTURE_ONLY",
    "NON_AUTHORITY",
    "WEIGHT_IDENTITY_AVAILABLE_WITH_EVIDENCE",
    "WEIGHT_IDENTITY_UNAVAILABLE_BY_ACCESS_MODEL",
    "WEIGHT_IDENTITY_UNAVAILABLE_IN_REPLAY",
    "BEHAVIOR_GENERATION",
    "TOOL_CALL_OBSERVATION",
    "LOGPROB_OBSERVATION",
    "HIDDEN_STATE_OBSERVATION",
    "ACTIVATION_CAPTURE",
    "STEERING_INTERVENTION",
    "CAPABILITY_NAMES",
    "SUPPORTED_WITH_EVIDENCE",
    "UNAVAILABLE_BY_ACCESS_MODEL",
    "UNAVAILABLE_IN_REPLAY",
    "UNAVAILABLE_NOT_IMPLEMENTED",
    "UNKNOWN_UNVERIFIED",
    "CAPABILITY_STATUSES",
    "OBSERVED",
    "UNAVAILABLE",
    "OBSERVATION_STATUSES",
    "ComparisonModelProtocolValidationError",
    "ComparisonModelCapability",
    "ComparisonModelIdentityArtifact",
    "ComparisonModelCapabilitiesArtifact",
    "BehavioralObservationArtifact",
    "build_comparison_model_weight_identity_body",
    "build_comparison_model_configuration_body",
    "build_comparison_capability_evidence_body",
    "build_comparison_model_identity",
    "load_comparison_model_identity",
    "replay_comparison_model_identity",
    "build_comparison_model_capabilities",
    "load_comparison_model_capabilities",
    "replay_comparison_model_capabilities",
    "build_behavioral_observation",
    "load_behavioral_observation",
    "replay_behavioral_observation",
)

_MECHANISTIC_CAPABILITIES = (
    HIDDEN_STATE_OBSERVATION,
    ACTIVATION_CAPTURE,
    STEERING_INTERVENTION,
)
_MUTABLE_REVISION_ALIASES = {
    "beta",
    "canary",
    "latest",
    "main",
    "master",
    "current",
    "default",
    "dev",
    "develop",
    "edge",
    "head",
    "nightly",
    "prod",
    "production",
    "rolling",
    "snapshot",
    "stable",
    "tip",
    "trunk",
}
_MUTABLE_REVISION_NAMESPACE_PREFIXES = (
    "origin/",
    "refs/heads/",
    "refs/remotes/",
)
_STATUS = MappingProxyType({"scope": STRUCTURE_ONLY, "authority": NON_AUTHORITY})
_BOUNDARY = MappingProxyType({
    "execution": "NOT_PERFORMED",
    "live_model_call": "NOT_PERFORMED",
    "provider_call": "NOT_PERFORMED",
    "execution_authority": "NOT_GRANTED",
    "observation_scope": "RAW_BEHAVIORAL_REFERENCES_ONLY",
    "intervention": "FORBIDDEN",
})


class ComparisonModelProtocolValidationError(SchemaValidationError):
    """Raised when a comparison carrier violates its closed schema."""


@dataclass(frozen=True, slots=True)
class ComparisonModelCapability:
    name: str
    status: str
    evidence_ref: ArtifactRef | None
    evidence_bytes: bytes | None


@dataclass(frozen=True, slots=True)
class ComparisonModelIdentityArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    identity_id: str
    access_kind: str
    provider: str
    model_id: str
    revision: str
    weight_identity_status: str
    weight_artifact_ref: ArtifactRef | None
    weight_artifact_bytes: bytes | None
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.identity_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=COMPARISON_MODEL_IDENTITY_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class ComparisonModelCapabilitiesArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    capabilities_id: str
    identity_ref: ArtifactRef
    access_kind: str
    provider: str
    model_id: str
    revision: str
    configuration_ref: ArtifactRef
    configuration_bytes: bytes
    capabilities: tuple[ComparisonModelCapability, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.capabilities_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=COMPARISON_MODEL_CAPABILITIES_MEDIA_TYPE,
        )

    def capability(self, name: str) -> ComparisonModelCapability:
        """Return one exact fixed capability or fail closed."""

        if type(name) is not str:
            raise ComparisonModelProtocolValidationError(
                "capability name must be an exact string"
            )
        matches = tuple(item for item in self.capabilities if item.name == name)
        if len(matches) != 1:
            raise ComparisonModelProtocolValidationError(
                "capability name must resolve exactly one fixed capability"
            )
        return matches[0]


@dataclass(frozen=True, slots=True)
class BehavioralObservationArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    observation_id: str
    identity_ref: ArtifactRef
    access_kind: str
    provider: str
    model_id: str
    revision: str
    configuration_ref: ArtifactRef
    configuration_bytes: bytes
    protocol_ref: ArtifactRef
    case_id: str
    case_ref: ArtifactRef
    observation_status: str
    raw_response_ref: ArtifactRef | None
    raw_tool_calls_ref: ArtifactRef | None
    unavailable_reason: str | None
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.observation_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=BEHAVIORAL_OBSERVATION_MEDIA_TYPE,
        )


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    _require_artifact_ref(reference, "artifact_ref")
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _require_artifact_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise ComparisonModelProtocolValidationError(
            f"{path} must be an exact ArtifactRef"
        )
    if (
        type(value.artifact_id) is not str
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.media_type) is not str
    ):
        raise ComparisonModelProtocolValidationError(
            f"{path} fields must use exact immutable scalar types"
        )
    return value


def _require_ref_media(reference: ArtifactRef, expected: str, path: str) -> None:
    if reference.media_type != expected:
        raise ComparisonModelProtocolValidationError(
            f"{path}.media_type must be {expected!r}"
        )


def _canonical_object(
    raw: bytes | bytearray | memoryview,
    path: str,
) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise ComparisonModelProtocolValidationError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, value
    except ComparisonModelProtocolValidationError:
        raise
    except (ValueError, TypeError) as exc:
        raise ComparisonModelProtocolValidationError(f"{path}: {exc}") from exc


def _require_immutable_revision(value: Any, path: str) -> str:
    revision = expect_machine_id(value, path)
    normalized = revision.casefold().replace("\\", "/")
    path_segments = tuple(segment for segment in normalized.split("/") if segment)
    if (
        any(normalized.startswith(prefix) for prefix in _MUTABLE_REVISION_NAMESPACE_PREFIXES)
        or any(segment in _MUTABLE_REVISION_ALIASES for segment in path_segments)
    ):
        raise ComparisonModelProtocolValidationError(
            f"{path} must not use a mutable revision alias"
        )
    return revision


def _require_frozen_json(value: Any, path: str) -> None:
    if type(value) is MappingProxyType:
        for key, child in value.items():
            if type(key) is not str:
                raise ComparisonModelProtocolValidationError(
                    f"{path} keys must be exact strings"
                )
            _require_frozen_json(child, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, child in enumerate(value):
            _require_frozen_json(child, f"{path}[{index}]")
        return
    if type(value) in (str, int, bool) or value is None:
        return
    raise ComparisonModelProtocolValidationError(
        f"{path} must be recursively frozen canonical JSON"
    )


def _evidence_body_value(schema: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema": schema,
        **fields,
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def build_comparison_model_weight_identity_body(
    *, provider: str, model_id: str, revision: str
) -> bytes:
    """Build typed caller bytes for one exact open-weight identity."""

    return canonical_json_bytes(
        _evidence_body_value(
            COMPARISON_MODEL_WEIGHT_IDENTITY_SCHEMA,
            provider=expect_machine_id(provider, "provider"),
            model_id=expect_machine_id(model_id, "model_id"),
            revision=_require_immutable_revision(revision, "revision"),
        )
    )


def _validate_weight_identity_body(
    raw: Any,
    reference: ArtifactRef,
    *,
    provider: str,
    model_id: str,
    revision: str,
) -> bytes:
    if type(raw) is not bytes or not reference.verify_bytes(raw):
        raise ComparisonModelProtocolValidationError(
            "weight identity caller bytes do not match the exact artifact reference"
        )
    snapshot, value = _canonical_object(raw, "weight identity evidence")
    expect_keys(
        value,
        required={"schema", "provider", "model_id", "revision", "status", "boundary"},
        path="$",
    )
    if value["schema"] != COMPARISON_MODEL_WEIGHT_IDENTITY_SCHEMA:
        raise ComparisonModelProtocolValidationError("weight identity evidence schema drifted")
    if (
        expect_machine_id(value["provider"], "$.provider") != provider
        or expect_machine_id(value["model_id"], "$.model_id") != model_id
        or _require_immutable_revision(value["revision"], "$.revision") != revision
    ):
        raise ComparisonModelProtocolValidationError(
            "weight identity evidence differs from the exact model binding"
        )
    _require_fixed_status_and_boundary(value)
    return snapshot


def build_comparison_model_configuration_body(
    *, configuration_id: str, identity: "ComparisonModelIdentityArtifact"
) -> bytes:
    """Build typed caller bytes binding one configuration to one model identity."""

    identity = replay_comparison_model_identity(identity)
    return canonical_json_bytes(
        _evidence_body_value(
            COMPARISON_MODEL_CONFIGURATION_SCHEMA,
            configuration_id=expect_machine_id(configuration_id, "configuration_id"),
            model_identity=_model_binding_value(identity),
        )
    )


def _validate_configuration_body(
    raw: Any, reference: ArtifactRef, *, identity: "ComparisonModelIdentityArtifact"
) -> bytes:
    if type(raw) is not bytes or not reference.verify_bytes(raw):
        raise ComparisonModelProtocolValidationError(
            "configuration caller bytes do not match the exact artifact reference"
        )
    snapshot, value = _canonical_object(raw, "model configuration evidence")
    expect_keys(
        value,
        required={"schema", "configuration_id", "model_identity", "status", "boundary"},
        path="$",
    )
    if value["schema"] != COMPARISON_MODEL_CONFIGURATION_SCHEMA:
        raise ComparisonModelProtocolValidationError("configuration evidence schema drifted")
    if expect_machine_id(value["configuration_id"], "$.configuration_id") != reference.artifact_id:
        raise ComparisonModelProtocolValidationError(
            "configuration body identity differs from its artifact reference"
        )
    _require_model_binding(value["model_identity"], identity=identity, path="$.model_identity")
    _require_fixed_status_and_boundary(value)
    return snapshot


def build_comparison_capability_evidence_body(
    *,
    evidence_id: str,
    capability_name: str,
    identity: "ComparisonModelIdentityArtifact",
    configuration_ref: ArtifactRef,
) -> bytes:
    """Build typed structural evidence bytes for one exact capability role."""

    identity = replay_comparison_model_identity(identity)
    configuration_ref = _require_artifact_ref(configuration_ref, "configuration_ref")
    _require_ref_media(
        configuration_ref, COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE, "configuration_ref"
    )
    return canonical_json_bytes(
        _evidence_body_value(
            COMPARISON_CAPABILITY_EVIDENCE_SCHEMA,
            evidence_id=expect_machine_id(evidence_id, "evidence_id"),
            capability_name=expect_enum(
                capability_name, set(CAPABILITY_NAMES), "capability_name"
            ),
            model_identity=_model_binding_value(identity),
            configuration_ref=_artifact_ref_value(configuration_ref),
        )
    )


def _validate_capability_evidence_body(
    raw: Any,
    reference: ArtifactRef,
    *,
    capability_name: str,
    identity: "ComparisonModelIdentityArtifact",
    configuration_ref: ArtifactRef,
) -> bytes:
    _require_ref_media(
        reference, COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE, "capability_evidence_ref"
    )
    if type(raw) is not bytes or not reference.verify_bytes(raw):
        raise ComparisonModelProtocolValidationError(
            "capability evidence caller bytes do not match the exact artifact reference"
        )
    snapshot, value = _canonical_object(raw, "capability evidence")
    expect_keys(
        value,
        required={
            "schema", "evidence_id", "capability_name", "model_identity",
            "configuration_ref", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != COMPARISON_CAPABILITY_EVIDENCE_SCHEMA:
        raise ComparisonModelProtocolValidationError("capability evidence schema drifted")
    if expect_machine_id(value["evidence_id"], "$.evidence_id") != reference.artifact_id:
        raise ComparisonModelProtocolValidationError(
            "capability evidence identity differs from its artifact reference"
        )
    if expect_enum(value["capability_name"], set(CAPABILITY_NAMES), "$.capability_name") != capability_name:
        raise ComparisonModelProtocolValidationError(
            "capability evidence is bound to a different capability"
        )
    _require_model_binding(value["model_identity"], identity=identity, path="$.model_identity")
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != configuration_ref:
        raise ComparisonModelProtocolValidationError(
            "capability evidence is bound to a different configuration"
        )
    _require_fixed_status_and_boundary(value)
    return snapshot


def _require_fixed_status_and_boundary(value: dict[str, Any]) -> None:
    status = expect_object(value["status"], "$.status")
    expect_keys(status, required=_STATUS, path="$.status")
    if status != _STATUS:
        raise ComparisonModelProtocolValidationError(
            "comparison carrier status must remain STRUCTURE_ONLY/NON_AUTHORITY"
        )
    boundary = expect_object(value["boundary"], "$.boundary")
    expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    if boundary != _BOUNDARY:
        raise ComparisonModelProtocolValidationError(
            "comparison carrier cannot claim execution or hidden-state authority"
        )


def _require_exact_artifact_storage(value: Any, expected: type, path: str) -> None:
    if type(value) is not expected:
        raise ComparisonModelProtocolValidationError(
            f"{path} must be an exact {expected.__name__}"
        )
    if (
        type(value.raw_bytes) is not bytes
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.artifact_refs) is not tuple
    ):
        raise ComparisonModelProtocolValidationError(
            f"{path} storage projections must use exact immutable types"
        )
    _require_frozen_json(value.payload, f"{path}.payload")
    for index, reference in enumerate(value.artifact_refs):
        _require_artifact_ref(reference, f"{path}.artifact_refs[{index}]")


def _unique_ref_closure(
    references: tuple[ArtifactRef, ...],
    path: str,
) -> tuple[ArtifactRef, ...]:
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], ArtifactRef] = {}
    ordered: list[ArtifactRef] = []
    for index, reference in enumerate(references):
        _require_artifact_ref(reference, f"{path}[{index}]")
        prior = by_id.get(reference.artifact_id)
        if prior is not None:
            if prior != reference:
                raise ComparisonModelProtocolValidationError(
                    f"{path} reuses one artifact identity for different content"
                )
            continue
        content_identity = (reference.sha256, reference.byte_length)
        prior_content = by_content.get(content_identity)
        if prior_content is not None:
            raise ComparisonModelProtocolValidationError(
                f"{path} duplicates one content identity under different artifact IDs"
            )
        by_id[reference.artifact_id] = reference
        by_content[content_identity] = reference
        ordered.append(reference)
    return tuple(ordered)


def _require_distinct_role_refs(
    references: tuple[ArtifactRef, ...],
    *,
    owner_id: str,
    path: str,
) -> tuple[ArtifactRef, ...]:
    closure = _unique_ref_closure(references, path)
    if len(closure) != len(references):
        raise ComparisonModelProtocolValidationError(
            f"{path} cannot reuse one artifact identity across distinct roles"
        )
    if owner_id in {reference.artifact_id for reference in closure}:
        raise ComparisonModelProtocolValidationError(
            f"{path} collides with the carrier artifact identity"
        )
    return closure


def _weight_status_for(access_kind: str) -> str:
    if access_kind == OPEN_WEIGHT:
        return WEIGHT_IDENTITY_AVAILABLE_WITH_EVIDENCE
    if access_kind == CLOSED_WEIGHT:
        return WEIGHT_IDENTITY_UNAVAILABLE_BY_ACCESS_MODEL
    return WEIGHT_IDENTITY_UNAVAILABLE_IN_REPLAY


def _identity_value(
    *,
    identity_id: str,
    access_kind: str,
    provider: str,
    model_id: str,
    revision: str,
    weight_artifact_ref: ArtifactRef | None,
) -> dict[str, Any]:
    return {
        "schema": COMPARISON_MODEL_IDENTITY_SCHEMA,
        "identity_id": identity_id,
        "access_kind": access_kind,
        "provider": provider,
        "model_id": model_id,
        "revision": revision,
        "weight_identity": {
            "status": _weight_status_for(access_kind),
            "artifact_ref": (
                None
                if weight_artifact_ref is None
                else _artifact_ref_value(weight_artifact_ref)
            ),
        },
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_comparison_model_identity(
    raw: bytes | bytearray | memoryview,
    *,
    weight_artifact_ref: ArtifactRef | None,
    weight_artifact_bytes: bytes | None,
) -> ComparisonModelIdentityArtifact:
    snapshot, value = _canonical_object(raw, "comparison model identity")
    expect_keys(
        value,
        required={
            "schema",
            "identity_id",
            "access_kind",
            "provider",
            "model_id",
            "revision",
            "weight_identity",
            "status",
            "boundary",
        },
        path="$",
    )
    if value["schema"] != COMPARISON_MODEL_IDENTITY_SCHEMA:
        raise ComparisonModelProtocolValidationError(
            "comparison model identity schema drifted"
        )
    identity_id = expect_machine_id(value["identity_id"], "$.identity_id")
    access_kind = expect_enum(
        value["access_kind"], set(MODEL_ACCESS_KINDS), "$.access_kind"
    )
    provider = expect_machine_id(value["provider"], "$.provider")
    model_id = expect_machine_id(value["model_id"], "$.model_id")
    revision = _require_immutable_revision(value["revision"], "$.revision")
    weight_identity = expect_object(value["weight_identity"], "$.weight_identity")
    expect_keys(
        weight_identity,
        required={"status", "artifact_ref"},
        path="$.weight_identity",
    )
    expected_weight_status = _weight_status_for(access_kind)
    if weight_identity["status"] != expected_weight_status:
        raise ComparisonModelProtocolValidationError(
            "weight identity status does not match the model access kind"
        )
    parsed_weight_ref: ArtifactRef | None
    if access_kind == OPEN_WEIGHT:
        if weight_identity["artifact_ref"] is None:
            raise ComparisonModelProtocolValidationError(
                "OPEN_WEIGHT requires an exact weight identity evidence reference"
            )
        parsed_weight_ref = parse_artifact_ref(
            weight_identity["artifact_ref"], "$.weight_identity.artifact_ref"
        )
        _require_ref_media(
            parsed_weight_ref,
            COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
            "$.weight_identity.artifact_ref",
        )
        _require_artifact_ref(weight_artifact_ref, "weight_artifact_ref")
        if parsed_weight_ref != weight_artifact_ref:
            raise ComparisonModelProtocolValidationError(
                "weight identity reference differs from the caller-bound evidence"
            )
        weight_artifact_bytes = _validate_weight_identity_body(
            weight_artifact_bytes,
            parsed_weight_ref,
            provider=provider,
            model_id=model_id,
            revision=revision,
        )
    else:
        if (
            weight_identity["artifact_ref"] is not None
            or weight_artifact_ref is not None
            or weight_artifact_bytes is not None
        ):
            raise ComparisonModelProtocolValidationError(
                f"{access_kind} must keep weight identity evidence unavailable"
            )
        parsed_weight_ref = None
        weight_artifact_bytes = None
    _require_fixed_status_and_boundary(value)
    references = () if parsed_weight_ref is None else (parsed_weight_ref,)
    if identity_id in {reference.artifact_id for reference in references}:
        raise ComparisonModelProtocolValidationError(
            "identity_id collides with its weight identity evidence"
        )
    return ComparisonModelIdentityArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        identity_id=identity_id,
        access_kind=access_kind,
        provider=provider,
        model_id=model_id,
        revision=revision,
        weight_identity_status=expected_weight_status,
        weight_artifact_ref=parsed_weight_ref,
        weight_artifact_bytes=weight_artifact_bytes,
        payload=freeze_json(value),
        artifact_refs=references,
    )


def build_comparison_model_identity(
    *,
    identity_id: str,
    access_kind: str,
    provider: str,
    model_id: str,
    revision: str,
    weight_artifact_ref: ArtifactRef | None,
    weight_artifact_bytes: bytes | None = None,
) -> ComparisonModelIdentityArtifact:
    """Build a non-authoritative, provider-neutral model identity carrier."""

    identity_id = expect_machine_id(identity_id, "identity_id")
    access_kind = expect_enum(access_kind, set(MODEL_ACCESS_KINDS), "access_kind")
    provider = expect_machine_id(provider, "provider")
    model_id = expect_machine_id(model_id, "model_id")
    revision = _require_immutable_revision(revision, "revision")
    if access_kind == OPEN_WEIGHT:
        if weight_artifact_ref is None:
            raise ComparisonModelProtocolValidationError(
                "OPEN_WEIGHT requires an exact weight identity evidence reference"
            )
        reference = _require_artifact_ref(weight_artifact_ref, "weight_artifact_ref")
        _require_ref_media(
            reference,
            COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
            "weight_artifact_ref",
        )
        _validate_weight_identity_body(
            weight_artifact_bytes,
            reference,
            provider=provider,
            model_id=model_id,
            revision=revision,
        )
    elif weight_artifact_ref is not None or weight_artifact_bytes is not None:
        raise ComparisonModelProtocolValidationError(
            f"{access_kind} must not claim a weight identity evidence reference"
        )
    raw = canonical_json_bytes(
        _identity_value(
            identity_id=identity_id,
            access_kind=access_kind,
            provider=provider,
            model_id=model_id,
            revision=revision,
            weight_artifact_ref=weight_artifact_ref,
        )
    )
    return _load_comparison_model_identity(
        raw,
        weight_artifact_ref=weight_artifact_ref,
        weight_artifact_bytes=weight_artifact_bytes,
    )


def load_comparison_model_identity(
    raw: bytes | bytearray | memoryview,
    *,
    weight_artifact_ref: ArtifactRef | None,
    weight_artifact_bytes: bytes | None = None,
) -> ComparisonModelIdentityArtifact:
    """Load canonical model identity bytes against caller-bound weight evidence."""

    return _load_comparison_model_identity(
        raw,
        weight_artifact_ref=weight_artifact_ref,
        weight_artifact_bytes=weight_artifact_bytes,
    )


def replay_comparison_model_identity(
    identity: ComparisonModelIdentityArtifact,
) -> ComparisonModelIdentityArtifact:
    """Freshly replay one immutable model identity projection."""

    _require_exact_artifact_storage(
        identity, ComparisonModelIdentityArtifact, "identity"
    )
    if any(
        type(value) is not str
        for value in (
            identity.identity_id,
            identity.access_kind,
            identity.provider,
            identity.model_id,
            identity.revision,
            identity.weight_identity_status,
        )
    ) or (
        identity.weight_artifact_bytes is not None
        and type(identity.weight_artifact_bytes) is not bytes
    ):
        raise ComparisonModelProtocolValidationError(
            "identity projections must use exact immutable scalar types"
        )
    replayed = _load_comparison_model_identity(
        identity.raw_bytes,
        weight_artifact_ref=identity.weight_artifact_ref,
        weight_artifact_bytes=identity.weight_artifact_bytes,
    )
    if replayed != identity:
        raise ComparisonModelProtocolValidationError(
            "comparison model identity differs from fresh exact-byte replay"
        )
    return replayed


def _model_binding_value(identity: ComparisonModelIdentityArtifact) -> dict[str, Any]:
    return {
        "identity_ref": _artifact_ref_value(identity.artifact_ref),
        "access_kind": identity.access_kind,
        "provider": identity.provider,
        "model_id": identity.model_id,
        "revision": identity.revision,
    }


def _require_model_binding(
    value: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    path: str,
) -> None:
    binding = expect_object(value, path)
    expect_keys(
        binding,
        required={
            "identity_ref",
            "access_kind",
            "provider",
            "model_id",
            "revision",
        },
        path=path,
    )
    parsed_ref = parse_artifact_ref(binding["identity_ref"], f"{path}.identity_ref")
    if parsed_ref != identity.artifact_ref:
        raise ComparisonModelProtocolValidationError(
            f"{path}.identity_ref differs from the caller-bound model identity"
        )
    expected = _model_binding_value(identity)
    if binding != expected:
        raise ComparisonModelProtocolValidationError(
            f"{path} differs from the exact provider/model/revision/access binding"
        )


def _validate_capability_inputs(
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    capability_statuses: Mapping[str, str],
    capability_evidence_refs: Mapping[str, ArtifactRef | None],
    capability_evidence_bytes: Mapping[str, bytes | None],
) -> tuple[ComparisonModelCapability, ...]:
    identity = replay_comparison_model_identity(identity)
    configuration_ref = _require_artifact_ref(configuration_ref, "configuration_ref")
    _require_ref_media(
        configuration_ref, COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE, "configuration_ref"
    )
    _validate_configuration_body(configuration_bytes, configuration_ref, identity=identity)
    if type(capability_statuses) is not dict:
        raise ComparisonModelProtocolValidationError(
            "capability_statuses must be an exact dict"
        )
    if type(capability_evidence_refs) is not dict:
        raise ComparisonModelProtocolValidationError(
            "capability_evidence_refs must be an exact dict"
        )
    if type(capability_evidence_bytes) is not dict:
        raise ComparisonModelProtocolValidationError(
            "capability_evidence_bytes must be an exact dict"
        )
    expected_names = set(CAPABILITY_NAMES)
    if set(capability_statuses) != expected_names:
        raise ComparisonModelProtocolValidationError(
            "capability_statuses must contain every fixed capability exactly once"
        )
    if set(capability_evidence_refs) != expected_names:
        raise ComparisonModelProtocolValidationError(
            "capability_evidence_refs must contain every fixed capability exactly once"
        )
    if set(capability_evidence_bytes) != expected_names:
        raise ComparisonModelProtocolValidationError(
            "capability_evidence_bytes must contain every fixed capability exactly once"
        )
    projections: list[ComparisonModelCapability] = []
    for name in CAPABILITY_NAMES:
        status = expect_enum(
            capability_statuses[name], set(CAPABILITY_STATUSES), f"{name}.status"
        )
        evidence = capability_evidence_refs[name]
        evidence_bytes = capability_evidence_bytes[name]
        if status == SUPPORTED_WITH_EVIDENCE:
            evidence = _require_artifact_ref(evidence, f"{name}.evidence_ref")
            evidence_bytes = _validate_capability_evidence_body(
                evidence_bytes,
                evidence,
                capability_name=name,
                identity=identity,
                configuration_ref=configuration_ref,
            )
        elif evidence is not None or evidence_bytes is not None:
            raise ComparisonModelProtocolValidationError(
                f"{name} may carry evidence only when SUPPORTED_WITH_EVIDENCE"
            )
        if identity.access_kind == CLOSED_WEIGHT and name in _MECHANISTIC_CAPABILITIES:
            if status != UNAVAILABLE_BY_ACCESS_MODEL:
                raise ComparisonModelProtocolValidationError(
                    "CLOSED_WEIGHT hidden-state, activation, and steering capabilities "
                    "must be UNAVAILABLE_BY_ACCESS_MODEL"
                )
        if identity.access_kind == REPLAY and name in _MECHANISTIC_CAPABILITIES:
            if status != UNAVAILABLE_IN_REPLAY:
                raise ComparisonModelProtocolValidationError(
                    "REPLAY hidden-state, activation, and steering capabilities "
                    "must be UNAVAILABLE_IN_REPLAY"
                )
        if identity.access_kind == OPEN_WEIGHT and status in {
            UNAVAILABLE_BY_ACCESS_MODEL,
            UNAVAILABLE_IN_REPLAY,
        }:
            raise ComparisonModelProtocolValidationError(
                "OPEN_WEIGHT cannot claim a closed-access or replay-only limitation"
            )
        projections.append(
            ComparisonModelCapability(
                name=name,
                status=status,
                evidence_ref=evidence,
                evidence_bytes=evidence_bytes,
            )
        )
    return tuple(projections)


def _capabilities_value(
    *,
    capabilities_id: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    capabilities: tuple[ComparisonModelCapability, ...],
) -> dict[str, Any]:
    return {
        "schema": COMPARISON_MODEL_CAPABILITIES_SCHEMA,
        "capabilities_id": capabilities_id,
        "model_identity": _model_binding_value(identity),
        "configuration_ref": _artifact_ref_value(configuration_ref),
        "capabilities": [
            {
                "name": item.name,
                "status": item.status,
                "evidence_ref": (
                    None
                    if item.evidence_ref is None
                    else _artifact_ref_value(item.evidence_ref)
                ),
            }
            for item in capabilities
        ],
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_comparison_model_capabilities(
    raw: bytes | bytearray | memoryview,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    capability_evidence_bytes: Mapping[str, bytes | None],
) -> ComparisonModelCapabilitiesArtifact:
    identity = replay_comparison_model_identity(identity)
    snapshot, value = _canonical_object(raw, "comparison model capabilities")
    expect_keys(
        value,
        required={
            "schema",
            "capabilities_id",
            "model_identity",
            "configuration_ref",
            "capabilities",
            "status",
            "boundary",
        },
        path="$",
    )
    if value["schema"] != COMPARISON_MODEL_CAPABILITIES_SCHEMA:
        raise ComparisonModelProtocolValidationError(
            "comparison model capabilities schema drifted"
        )
    capabilities_id = expect_machine_id(value["capabilities_id"], "$.capabilities_id")
    _require_model_binding(
        value["model_identity"], identity=identity, path="$.model_identity"
    )
    parsed_configuration_ref = parse_artifact_ref(
        value["configuration_ref"], "$.configuration_ref"
    )
    if parsed_configuration_ref != configuration_ref:
        raise ComparisonModelProtocolValidationError(
            "configuration reference differs from caller-bound configuration"
        )
    rows = expect_list(value["capabilities"], "$.capabilities")
    if len(rows) != len(CAPABILITY_NAMES):
        raise ComparisonModelProtocolValidationError(
            "capabilities must contain every fixed capability exactly once"
        )
    statuses: dict[str, str] = {}
    evidence_refs: dict[str, ArtifactRef | None] = {}
    names: list[str] = []
    for index, raw_row in enumerate(rows):
        path = f"$.capabilities[{index}]"
        row = expect_object(raw_row, path)
        expect_keys(row, required={"name", "status", "evidence_ref"}, path=path)
        name = expect_enum(row["name"], set(CAPABILITY_NAMES), f"{path}.name")
        if name in statuses:
            raise ComparisonModelProtocolValidationError(
                "capabilities contain a duplicate capability identity"
            )
        names.append(name)
        statuses[name] = expect_enum(
            row["status"], set(CAPABILITY_STATUSES), f"{path}.status"
        )
        evidence_refs[name] = (
            None
            if row["evidence_ref"] is None
            else parse_artifact_ref(row["evidence_ref"], f"{path}.evidence_ref")
        )
    if tuple(names) != CAPABILITY_NAMES:
        raise ComparisonModelProtocolValidationError(
            "capabilities must use the exact fixed capability order"
        )
    capabilities = _validate_capability_inputs(
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=statuses,
        capability_evidence_refs=evidence_refs,
        capability_evidence_bytes=capability_evidence_bytes,
    )
    _require_fixed_status_and_boundary(value)
    evidence = tuple(
        item.evidence_ref
        for item in capabilities
        if item.evidence_ref is not None
    )
    references = _require_distinct_role_refs(
        (
            identity.artifact_ref,
            *identity.artifact_refs,
            configuration_ref,
            *evidence,
        ),
        owner_id=capabilities_id,
        path="artifact_refs",
    )
    return ComparisonModelCapabilitiesArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        capabilities_id=capabilities_id,
        identity_ref=identity.artifact_ref,
        access_kind=identity.access_kind,
        provider=identity.provider,
        model_id=identity.model_id,
        revision=identity.revision,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capabilities=capabilities,
        payload=freeze_json(value),
        artifact_refs=references,
    )


def build_comparison_model_capabilities(
    *,
    capabilities_id: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    capability_statuses: Mapping[str, str],
    capability_evidence_refs: Mapping[str, ArtifactRef | None],
    capability_evidence_bytes: Mapping[str, bytes | None],
) -> ComparisonModelCapabilitiesArtifact:
    """Build a complete capability declaration bound to one exact identity."""

    capabilities_id = expect_machine_id(capabilities_id, "capabilities_id")
    identity = replay_comparison_model_identity(identity)
    capabilities = _validate_capability_inputs(
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=capability_statuses,
        capability_evidence_refs=capability_evidence_refs,
        capability_evidence_bytes=capability_evidence_bytes,
    )
    raw = canonical_json_bytes(
        _capabilities_value(
            capabilities_id=capabilities_id,
            identity=identity,
            configuration_ref=configuration_ref,
            capabilities=capabilities,
        )
    )
    return _load_comparison_model_capabilities(
        raw,
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_evidence_bytes=capability_evidence_bytes,
    )


def load_comparison_model_capabilities(
    raw: bytes | bytearray | memoryview,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    capability_evidence_bytes: Mapping[str, bytes | None],
) -> ComparisonModelCapabilitiesArtifact:
    """Load canonical capability bytes against one exact model identity."""

    return _load_comparison_model_capabilities(
        raw,
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_evidence_bytes=capability_evidence_bytes,
    )


def replay_comparison_model_capabilities(
    capabilities: ComparisonModelCapabilitiesArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
) -> ComparisonModelCapabilitiesArtifact:
    """Freshly replay one immutable capability projection."""

    _require_exact_artifact_storage(
        capabilities, ComparisonModelCapabilitiesArtifact, "capabilities"
    )
    if type(capabilities.capabilities) is not tuple or any(
        type(item) is not ComparisonModelCapability for item in capabilities.capabilities
    ):
        raise ComparisonModelProtocolValidationError(
            "capability projections must use exact immutable carrier types"
        )
    if (
        any(
            type(value) is not str
            for value in (
                capabilities.capabilities_id,
                capabilities.access_kind,
                capabilities.provider,
                capabilities.model_id,
                capabilities.revision,
            )
        )
        or type(capabilities.identity_ref) is not ArtifactRef
        or type(capabilities.configuration_ref) is not ArtifactRef
        or type(capabilities.configuration_bytes) is not bytes
        or any(
            type(item.name) is not str
            or type(item.status) is not str
            or (item.evidence_bytes is not None and type(item.evidence_bytes) is not bytes)
            for item in capabilities.capabilities
        )
    ):
        raise ComparisonModelProtocolValidationError(
            "capability projections must use exact immutable scalar types"
        )
    replayed = _load_comparison_model_capabilities(
        capabilities.raw_bytes,
        identity=identity,
        configuration_ref=capabilities.configuration_ref,
        configuration_bytes=capabilities.configuration_bytes,
        capability_evidence_bytes={
            item.name: item.evidence_bytes for item in capabilities.capabilities
        },
    )
    if replayed != capabilities:
        raise ComparisonModelProtocolValidationError(
            "comparison model capabilities differ from fresh exact-byte replay"
        )
    return replayed


def _validate_observation_dependencies(
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
) -> tuple[
    ComparisonModelIdentityArtifact,
    ArtifactRef,
    ArtifactRef,
    str,
    ArtifactRef,
]:
    identity = replay_comparison_model_identity(identity)
    configuration_ref = _require_artifact_ref(configuration_ref, "configuration_ref")
    protocol_ref = _require_artifact_ref(protocol_ref, "protocol_ref")
    case_ref = _require_artifact_ref(case_ref, "case_ref")
    _require_ref_media(
        configuration_ref,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    configuration_bytes = _validate_configuration_body(
        configuration_bytes, configuration_ref, identity=identity
    )
    _require_ref_media(
        protocol_ref,
        BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
        "protocol_ref",
    )
    _require_ref_media(case_ref, BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE, "case_ref")
    case_id = expect_machine_id(case_id, "case_id")
    return identity, configuration_ref, configuration_bytes, protocol_ref, case_id, case_ref


def _observation_value(
    *,
    observation_id: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
    observation_status: str,
    raw_response_ref: ArtifactRef | None,
    raw_tool_calls_ref: ArtifactRef | None,
    unavailable_reason: str | None,
) -> dict[str, Any]:
    return {
        "schema": BEHAVIORAL_OBSERVATION_SCHEMA,
        "observation_id": observation_id,
        "model_identity": _model_binding_value(identity),
        "configuration_ref": _artifact_ref_value(configuration_ref),
        "protocol_ref": _artifact_ref_value(protocol_ref),
        "case": {"case_id": case_id, "artifact_ref": _artifact_ref_value(case_ref)},
        "observation_status": observation_status,
        "raw_response_ref": (
            None if raw_response_ref is None else _artifact_ref_value(raw_response_ref)
        ),
        "raw_tool_calls_ref": (
            None
            if raw_tool_calls_ref is None
            else _artifact_ref_value(raw_tool_calls_ref)
        ),
        "unavailable_reason": unavailable_reason,
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _validate_observation_state(
    *,
    observation_status: str,
    raw_response_ref: ArtifactRef | None,
    raw_tool_calls_ref: ArtifactRef | None,
    unavailable_reason: str | None,
) -> tuple[str, ArtifactRef | None, ArtifactRef | None, str | None]:
    observation_status = expect_enum(
        observation_status, set(OBSERVATION_STATUSES), "observation_status"
    )
    if observation_status == OBSERVED:
        response = _require_artifact_ref(raw_response_ref, "raw_response_ref")
        tool_calls = _require_artifact_ref(raw_tool_calls_ref, "raw_tool_calls_ref")
        _require_ref_media(
            response, RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE, "raw_response_ref"
        )
        _require_ref_media(
            tool_calls, RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE, "raw_tool_calls_ref"
        )
        if unavailable_reason is not None:
            raise ComparisonModelProtocolValidationError(
                "OBSERVED must not carry an unavailable reason"
            )
        return observation_status, response, tool_calls, None
    if raw_response_ref is not None or raw_tool_calls_ref is not None:
        raise ComparisonModelProtocolValidationError(
            "UNAVAILABLE must not claim raw response or tool-call evidence"
        )
    reason = expect_machine_id(unavailable_reason, "unavailable_reason")
    return observation_status, None, None, reason


def _load_behavioral_observation(
    raw: bytes | bytearray | memoryview,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
) -> BehavioralObservationArtifact:
    (
        identity,
        configuration_ref,
        configuration_bytes,
        protocol_ref,
        case_id,
        case_ref,
    ) = _validate_observation_dependencies(
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
    )
    snapshot, value = _canonical_object(raw, "behavioral observation")
    expect_keys(
        value,
        required={
            "schema",
            "observation_id",
            "model_identity",
            "configuration_ref",
            "protocol_ref",
            "case",
            "observation_status",
            "raw_response_ref",
            "raw_tool_calls_ref",
            "unavailable_reason",
            "status",
            "boundary",
        },
        path="$",
    )
    if value["schema"] != BEHAVIORAL_OBSERVATION_SCHEMA:
        raise ComparisonModelProtocolValidationError(
            "behavioral observation schema drifted"
        )
    observation_id = expect_machine_id(value["observation_id"], "$.observation_id")
    _require_model_binding(
        value["model_identity"], identity=identity, path="$.model_identity"
    )
    parsed_configuration_ref = parse_artifact_ref(
        value["configuration_ref"], "$.configuration_ref"
    )
    parsed_protocol_ref = parse_artifact_ref(value["protocol_ref"], "$.protocol_ref")
    if parsed_configuration_ref != configuration_ref:
        raise ComparisonModelProtocolValidationError(
            "configuration reference differs from caller-bound configuration"
        )
    if parsed_protocol_ref != protocol_ref:
        raise ComparisonModelProtocolValidationError(
            "protocol reference differs from caller-bound protocol"
        )
    case = expect_object(value["case"], "$.case")
    expect_keys(case, required={"case_id", "artifact_ref"}, path="$.case")
    parsed_case_id = expect_machine_id(case["case_id"], "$.case.case_id")
    parsed_case_ref = parse_artifact_ref(case["artifact_ref"], "$.case.artifact_ref")
    if parsed_case_id != case_id or parsed_case_ref != case_ref:
        raise ComparisonModelProtocolValidationError(
            "case binding differs from the caller-bound case"
        )
    parsed_response_ref = (
        None
        if value["raw_response_ref"] is None
        else parse_artifact_ref(value["raw_response_ref"], "$.raw_response_ref")
    )
    parsed_tool_calls_ref = (
        None
        if value["raw_tool_calls_ref"] is None
        else parse_artifact_ref(value["raw_tool_calls_ref"], "$.raw_tool_calls_ref")
    )
    (
        observation_status,
        parsed_response_ref,
        parsed_tool_calls_ref,
        unavailable_reason,
    ) = _validate_observation_state(
        observation_status=value["observation_status"],
        raw_response_ref=parsed_response_ref,
        raw_tool_calls_ref=parsed_tool_calls_ref,
        unavailable_reason=value["unavailable_reason"],
    )
    _require_fixed_status_and_boundary(value)
    role_refs = [
        identity.artifact_ref,
        *identity.artifact_refs,
        configuration_ref,
        protocol_ref,
        case_ref,
    ]
    if parsed_response_ref is not None:
        role_refs.append(parsed_response_ref)
    if parsed_tool_calls_ref is not None:
        role_refs.append(parsed_tool_calls_ref)
    references = _require_distinct_role_refs(
        tuple(role_refs), owner_id=observation_id, path="artifact_refs"
    )
    return BehavioralObservationArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        observation_id=observation_id,
        identity_ref=identity.artifact_ref,
        access_kind=identity.access_kind,
        provider=identity.provider,
        model_id=identity.model_id,
        revision=identity.revision,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
        observation_status=observation_status,
        raw_response_ref=parsed_response_ref,
        raw_tool_calls_ref=parsed_tool_calls_ref,
        unavailable_reason=unavailable_reason,
        payload=freeze_json(value),
        artifact_refs=references,
    )


def build_behavioral_observation(
    *,
    observation_id: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
    observation_status: str,
    raw_response_ref: ArtifactRef | None,
    raw_tool_calls_ref: ArtifactRef | None,
    unavailable_reason: str | None,
) -> BehavioralObservationArtifact:
    """Build a raw-reference-only behavioral observation carrier."""

    observation_id = expect_machine_id(observation_id, "observation_id")
    (
        identity,
        configuration_ref,
        configuration_bytes,
        protocol_ref,
        case_id,
        case_ref,
    ) = _validate_observation_dependencies(
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
    )
    (
        observation_status,
        raw_response_ref,
        raw_tool_calls_ref,
        unavailable_reason,
    ) = _validate_observation_state(
        observation_status=observation_status,
        raw_response_ref=raw_response_ref,
        raw_tool_calls_ref=raw_tool_calls_ref,
        unavailable_reason=unavailable_reason,
    )
    raw = canonical_json_bytes(
        _observation_value(
            observation_id=observation_id,
            identity=identity,
            configuration_ref=configuration_ref,
            protocol_ref=protocol_ref,
            case_id=case_id,
            case_ref=case_ref,
            observation_status=observation_status,
            raw_response_ref=raw_response_ref,
            raw_tool_calls_ref=raw_tool_calls_ref,
            unavailable_reason=unavailable_reason,
        )
    )
    return _load_behavioral_observation(
        raw,
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
    )


def load_behavioral_observation(
    raw: bytes | bytearray | memoryview,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
) -> BehavioralObservationArtifact:
    """Load observation bytes against exact model/config/protocol/case inputs."""

    return _load_behavioral_observation(
        raw,
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
    )


def replay_behavioral_observation(
    observation: BehavioralObservationArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes | None = None,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
) -> BehavioralObservationArtifact:
    """Freshly replay one immutable behavioral observation projection."""

    _require_exact_artifact_storage(
        observation, BehavioralObservationArtifact, "observation"
    )
    if (
        any(
            type(value) is not str
            for value in (
                observation.observation_id,
                observation.access_kind,
                observation.provider,
                observation.model_id,
                observation.revision,
                observation.case_id,
                observation.observation_status,
            )
        )
        or type(observation.identity_ref) is not ArtifactRef
        or type(observation.configuration_ref) is not ArtifactRef
        or type(observation.configuration_bytes) is not bytes
        or type(observation.protocol_ref) is not ArtifactRef
        or type(observation.case_ref) is not ArtifactRef
        or (
            observation.unavailable_reason is not None
            and type(observation.unavailable_reason) is not str
        )
    ):
        raise ComparisonModelProtocolValidationError(
            "observation projections must use exact immutable scalar types"
        )
    if configuration_bytes is not None and configuration_bytes != observation.configuration_bytes:
        raise ComparisonModelProtocolValidationError(
            "configuration caller bytes differ from the immutable observation projection"
        )
    replayed = _load_behavioral_observation(
        observation.raw_bytes,
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=observation.configuration_bytes,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
    )
    if replayed != observation:
        raise ComparisonModelProtocolValidationError(
            "behavioral observation differs from fresh exact-byte replay"
        )
    return replayed
