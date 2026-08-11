"""Strict, replay-only open-weight versus closed-weight comparison roster.

This module binds canonical protocol and case bytes to already-validated model
identities.  It performs no filesystem, network, provider, or model I/O and it
does not establish an outcome or grant execution authority.
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
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_string,
    parse_artifact_ref,
)
from .comparison_adapters import BehavioralCaseInput
from .comparison_model_protocol import (
    BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    CLOSED_WEIGHT,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    NON_AUTHORITY,
    OPEN_WEIGHT,
    STRUCTURE_ONLY,
    ComparisonModelIdentityArtifact,
    build_comparison_model_configuration_body,
    replay_comparison_model_identity,
)


SHARED_COMPARISON_PROTOCOL_SCHEMA = "cas_harness_v2.shared_comparison_protocol.v1"
BEHAVIORAL_COMPARISON_CASE_SCHEMA = "cas_harness_v2.behavioral_comparison_case.v1"
FROZEN_COMPARISON_ROSTER_SCHEMA = "cas_harness_v2.frozen_comparison_roster.v1"

FROZEN_COMPARISON_ROSTER_MEDIA_TYPE = (
    "application/vnd.cas-harness.frozen-comparison-roster-v1+json"
)
SEMANTIC_TASK_MEDIA_TYPE = "application/vnd.cas-harness.semantic-task-v1+json"
PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE = (
    "application/vnd.cas-harness.prompt-injection-taxonomy-v1+json"
)
CLEAN_CONTROLS_MEDIA_TYPE = "application/vnd.cas-harness.clean-controls-v1+json"
TOOL_DEFINITIONS_MEDIA_TYPE = "application/vnd.cas-harness.tool-definitions-v1+json"
AUTHORIZATION_BOUNDARY_MEDIA_TYPE = (
    "application/vnd.cas-harness.authorization-boundary-v1+json"
)
OUTPUT_SCHEMA_MEDIA_TYPE = "application/vnd.cas-harness.output-schema-v1+json"
INSTRUCTION_EQUIVALENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.instruction-equivalence-v1+json"
)
INDEPENDENT_EVALUATOR_MEDIA_TYPE = (
    "application/vnd.cas-harness.independent-evaluator-v1+json"
)
TIME_POLICY_MEDIA_TYPE = "application/vnd.cas-harness.time-policy-v1+json"
SYSTEM_INSTRUCTION_MEDIA_TYPE = (
    "application/vnd.cas-harness.system-instruction-v1+json"
)
BEHAVIORAL_PROMPT_MEDIA_TYPE = "application/vnd.cas-harness.behavioral-prompt-v1+json"
PROMPT_SOURCE_MAP_MEDIA_TYPE = (
    "application/vnd.cas-harness.prompt-source-map-v1+json"
)

OPEN = "OPEN"
CLOSED = "CLOSED"
MODEL_ROLES = (OPEN, CLOSED)

ADVERSARIAL_PRESENT = "ADVERSARIAL_PRESENT"
CLEAN_ABSENT = "CLEAN_ABSENT"
CLEAN_NULL_ABSENT = "CLEAN_NULL_ABSENT"
CASE_ROLES = (ADVERSARIAL_PRESENT, CLEAN_ABSENT, CLEAN_NULL_ABSENT)

DETERMINISTIC_TEMPERATURE_POLICY = "EXACT_ZERO"
DETERMINISTIC_TEMPERATURE_VALUE = "0"
PROVIDER_TIMESTAMP_RECORDING_REQUIRED = "REQUIRED"

__all__ = (
    "SHARED_COMPARISON_PROTOCOL_SCHEMA",
    "BEHAVIORAL_COMPARISON_CASE_SCHEMA",
    "FROZEN_COMPARISON_ROSTER_SCHEMA",
    "FROZEN_COMPARISON_ROSTER_MEDIA_TYPE",
    "SEMANTIC_TASK_MEDIA_TYPE",
    "PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE",
    "CLEAN_CONTROLS_MEDIA_TYPE",
    "TOOL_DEFINITIONS_MEDIA_TYPE",
    "AUTHORIZATION_BOUNDARY_MEDIA_TYPE",
    "OUTPUT_SCHEMA_MEDIA_TYPE",
    "INSTRUCTION_EQUIVALENCE_MEDIA_TYPE",
    "INDEPENDENT_EVALUATOR_MEDIA_TYPE",
    "TIME_POLICY_MEDIA_TYPE",
    "SYSTEM_INSTRUCTION_MEDIA_TYPE",
    "BEHAVIORAL_PROMPT_MEDIA_TYPE",
    "PROMPT_SOURCE_MAP_MEDIA_TYPE",
    "OPEN",
    "CLOSED",
    "MODEL_ROLES",
    "ADVERSARIAL_PRESENT",
    "CLEAN_ABSENT",
    "CLEAN_NULL_ABSENT",
    "CASE_ROLES",
    "DETERMINISTIC_TEMPERATURE_POLICY",
    "DETERMINISTIC_TEMPERATURE_VALUE",
    "PROVIDER_TIMESTAMP_RECORDING_REQUIRED",
    "SharedComparisonProtocolValidationError",
    "SharedComparisonProtocolArtifact",
    "BehavioralComparisonCaseArtifact",
    "FrozenComparisonGroup",
    "FrozenComparisonRosterArtifact",
    "build_shared_comparison_protocol",
    "load_shared_comparison_protocol",
    "replay_shared_comparison_protocol",
    "build_behavioral_comparison_case",
    "load_behavioral_comparison_case",
    "replay_behavioral_comparison_case",
    "build_frozen_comparison_roster",
    "load_frozen_comparison_roster",
    "replay_frozen_comparison_roster",
)

_COMMON_REF_SPECS = (
    ("semantic_task_ref", SEMANTIC_TASK_MEDIA_TYPE),
    ("injection_taxonomy_ref", PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE),
    ("clean_controls_ref", CLEAN_CONTROLS_MEDIA_TYPE),
    ("tool_definitions_ref", TOOL_DEFINITIONS_MEDIA_TYPE),
    ("authorization_boundary_ref", AUTHORIZATION_BOUNDARY_MEDIA_TYPE),
    ("output_schema_ref", OUTPUT_SCHEMA_MEDIA_TYPE),
    ("instruction_equivalence_ref", INSTRUCTION_EQUIVALENCE_MEDIA_TYPE),
    ("independent_evaluator_ref", INDEPENDENT_EVALUATOR_MEDIA_TYPE),
    ("time_policy_ref", TIME_POLICY_MEDIA_TYPE),
)
_STATUS = MappingProxyType({"scope": STRUCTURE_ONLY, "authority": NON_AUTHORITY})
_BOUNDARY = MappingProxyType({
    "execution": "NOT_PERFORMED",
    "live_model_call": "NOT_PERFORMED",
    "provider_call": "NOT_PERFORMED",
    "network_io": "NOT_PERFORMED",
    "filesystem_io": "NOT_PERFORMED",
    "execution_authority": "NOT_GRANTED",
    "outcome": "NOT_ESTABLISHED",
})


class SharedComparisonProtocolValidationError(SchemaValidationError):
    """Raised when a shared comparison carrier violates its closed schema."""


@dataclass(frozen=True, slots=True)
class SharedComparisonProtocolArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    protocol_id: str
    open_identity: ComparisonModelIdentityArtifact
    closed_identity: ComparisonModelIdentityArtifact
    open_configuration_ref: ArtifactRef
    open_configuration_bytes: bytes
    closed_configuration_ref: ArtifactRef
    closed_configuration_bytes: bytes
    open_system_instruction_ref: ArtifactRef
    closed_system_instruction_ref: ArtifactRef
    semantic_task_ref: ArtifactRef
    injection_taxonomy_ref: ArtifactRef
    clean_controls_ref: ArtifactRef
    tool_definitions_ref: ArtifactRef
    authorization_boundary_ref: ArtifactRef
    output_schema_ref: ArtifactRef
    instruction_equivalence_ref: ArtifactRef
    independent_evaluator_ref: ArtifactRef
    time_policy_ref: ArtifactRef
    open_temperature_policy: str
    open_temperature_value: str
    closed_temperature_policy: str
    closed_temperature_value: str
    open_max_output_tokens: int
    closed_max_output_tokens: int
    open_provider_timestamp_recording: str
    closed_provider_timestamp_recording: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.protocol_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class BehavioralComparisonCaseArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    case_id: str
    group_id: str
    role: str
    protocol_ref: ArtifactRef
    prompt_ref: ArtifactRef
    prompt_source_map_ref: ArtifactRef
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.case_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class FrozenComparisonGroup:
    group_ordinal: int
    group_id: str
    cases: tuple[BehavioralComparisonCaseArtifact, ...]


@dataclass(frozen=True, slots=True)
class FrozenComparisonRosterArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    roster_id: str
    protocol: SharedComparisonProtocolArtifact
    groups: tuple[FrozenComparisonGroup, ...]
    cases: tuple[BehavioralComparisonCaseArtifact, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.roster_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=FROZEN_COMPARISON_ROSTER_MEDIA_TYPE,
        )

    def adapter_cases(self, role: str) -> tuple[BehavioralCaseInput, ...]:
        """Return an ordered, label-free adapter projection for one model role."""

        replay_frozen_comparison_roster(self)
        selected = expect_enum(role, set(MODEL_ROLES), "role")
        configuration_ref = (
            self.protocol.open_configuration_ref
            if selected == OPEN
            else self.protocol.closed_configuration_ref
        )
        return tuple(
            BehavioralCaseInput(
                execution_ordinal=ordinal,
                case_id=case.case_id,
                case_ref=case.artifact_ref,
                configuration_ref=configuration_ref,
                protocol_ref=self.protocol.artifact_ref,
            )
            for ordinal, case in enumerate(self.cases, start=1)
        )


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    reference = _require_artifact_ref(reference, "artifact_ref")
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _require_artifact_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise SharedComparisonProtocolValidationError(
            f"{path} must be an exact ArtifactRef"
        )
    if (
        type(value.artifact_id) is not str
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.media_type) is not str
    ):
        raise SharedComparisonProtocolValidationError(
            f"{path} fields must use exact immutable scalar types"
        )
    return value


def _require_ref_media(reference: ArtifactRef, media_type: str, path: str) -> None:
    if reference.media_type != media_type:
        raise SharedComparisonProtocolValidationError(
            f"{path}.media_type must be {media_type!r}"
        )


def _canonical_object(raw: Any, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise SharedComparisonProtocolValidationError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, value
    except SharedComparisonProtocolValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise SharedComparisonProtocolValidationError(f"{path}: {exc}") from exc


def _require_frozen_json(value: Any, path: str) -> None:
    if type(value) is MappingProxyType:
        for key, child in value.items():
            if type(key) is not str:
                raise SharedComparisonProtocolValidationError(
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
    raise SharedComparisonProtocolValidationError(
        f"{path} must be recursively frozen canonical JSON"
    )


def _require_status_and_boundary(value: dict[str, Any]) -> None:
    status = expect_object(value["status"], "$.status")
    expect_keys(status, required=_STATUS, path="$.status")
    if status != _STATUS:
        raise SharedComparisonProtocolValidationError(
            "comparison status must remain STRUCTURE_ONLY/NON_AUTHORITY"
        )
    boundary = expect_object(value["boundary"], "$.boundary")
    expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    if boundary != _BOUNDARY:
        raise SharedComparisonProtocolValidationError(
            "comparison boundary cannot claim execution, I/O, or an outcome"
        )


def _require_storage(value: Any, expected: type, path: str) -> None:
    if type(value) is not expected:
        raise SharedComparisonProtocolValidationError(
            f"{path} must be an exact {expected.__name__}"
        )
    if (
        type(value.raw_bytes) is not bytes
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.artifact_refs) is not tuple
    ):
        raise SharedComparisonProtocolValidationError(
            f"{path} storage projections must use exact immutable types"
        )
    _require_frozen_json(value.payload, f"{path}.payload")
    for index, reference in enumerate(value.artifact_refs):
        _require_artifact_ref(reference, f"{path}.artifact_refs[{index}]")


def _unique_ref_closure(
    references: tuple[ArtifactRef, ...], path: str
) -> tuple[ArtifactRef, ...]:
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], ArtifactRef] = {}
    ordered: list[ArtifactRef] = []
    for index, reference in enumerate(references):
        reference = _require_artifact_ref(reference, f"{path}[{index}]")
        prior = by_id.get(reference.artifact_id)
        if prior is not None:
            if prior != reference:
                raise SharedComparisonProtocolValidationError(
                    f"{path} reuses one artifact identity for different content"
                )
            continue
        content = (reference.sha256, reference.byte_length)
        if content in by_content:
            raise SharedComparisonProtocolValidationError(
                f"{path} duplicates one content identity under different artifact IDs"
            )
        by_id[reference.artifact_id] = reference
        by_content[content] = reference
        ordered.append(reference)
    return tuple(ordered)


def _require_distinct_roles(
    references: tuple[ArtifactRef, ...], *, owner_id: str, path: str
) -> None:
    closure = _unique_ref_closure(references, path)
    if len(closure) != len(references):
        raise SharedComparisonProtocolValidationError(
            f"{path} cannot reuse one artifact across distinct roles"
        )
    if owner_id in {reference.artifact_id for reference in closure}:
        raise SharedComparisonProtocolValidationError(
            f"{path} collides with its carrier artifact identity"
        )


def _common_refs(
    *,
    semantic_task_ref: ArtifactRef,
    injection_taxonomy_ref: ArtifactRef,
    clean_controls_ref: ArtifactRef,
    tool_definitions_ref: ArtifactRef,
    authorization_boundary_ref: ArtifactRef,
    output_schema_ref: ArtifactRef,
    instruction_equivalence_ref: ArtifactRef,
    independent_evaluator_ref: ArtifactRef,
    time_policy_ref: ArtifactRef,
) -> tuple[ArtifactRef, ...]:
    refs = (
        semantic_task_ref,
        injection_taxonomy_ref,
        clean_controls_ref,
        tool_definitions_ref,
        authorization_boundary_ref,
        output_schema_ref,
        instruction_equivalence_ref,
        independent_evaluator_ref,
        time_policy_ref,
    )
    for (name, media_type), reference in zip(_COMMON_REF_SPECS, refs, strict=True):
        _require_artifact_ref(reference, name)
        _require_ref_media(reference, media_type, name)
    return refs


def _validate_configuration(
    *,
    reference: ArtifactRef,
    raw: Any,
    identity: ComparisonModelIdentityArtifact,
    path: str,
) -> bytes:
    _require_artifact_ref(reference, f"{path}_ref")
    _require_ref_media(
        reference, COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE, f"{path}_ref"
    )
    if type(raw) is not bytes or not reference.verify_bytes(raw):
        raise SharedComparisonProtocolValidationError(
            f"{path} caller bytes do not match the exact artifact reference"
        )
    expected = build_comparison_model_configuration_body(
        configuration_id=reference.artifact_id,
        identity=identity,
    )
    if raw != expected:
        raise SharedComparisonProtocolValidationError(
            f"{path} caller bytes differ from the exact identity binding"
        )
    return raw


def _validate_model_settings(
    *, policy: Any, value: Any, max_output_tokens: Any, timestamp_recording: Any, path: str
) -> tuple[str, str, int, str]:
    policy = expect_string(policy, f"{path}.temperature_policy", maximum=64)
    value = expect_string(value, f"{path}.temperature_value", maximum=32)
    max_output_tokens = expect_int(
        max_output_tokens, f"{path}.max_output_tokens", minimum=1
    )
    timestamp_recording = expect_string(
        timestamp_recording, f"{path}.provider_timestamp_recording", maximum=32
    )
    if (
        policy != DETERMINISTIC_TEMPERATURE_POLICY
        or value != DETERMINISTIC_TEMPERATURE_VALUE
    ):
        raise SharedComparisonProtocolValidationError(
            f"{path} must use the exact deterministic zero-temperature policy"
        )
    if timestamp_recording != PROVIDER_TIMESTAMP_RECORDING_REQUIRED:
        raise SharedComparisonProtocolValidationError(
            f"{path} must require provider timestamp recording"
        )
    return policy, value, max_output_tokens, timestamp_recording


def _model_value(
    *,
    role: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    system_instruction_ref: ArtifactRef,
    temperature_policy: str,
    temperature_value: str,
    max_output_tokens: int,
    provider_timestamp_recording: str,
) -> dict[str, Any]:
    return {
        "role": role,
        "access_kind": identity.access_kind,
        "identity_ref": _artifact_ref_value(identity.artifact_ref),
        "provider": identity.provider,
        "model_id": identity.model_id,
        "revision": identity.revision,
        "configuration_ref": _artifact_ref_value(configuration_ref),
        "system_instruction_ref": _artifact_ref_value(system_instruction_ref),
        "temperature_policy": temperature_policy,
        "temperature_value": temperature_value,
        "max_output_tokens": max_output_tokens,
        "provider_timestamp_recording": provider_timestamp_recording,
    }


def _protocol_value(
    *,
    protocol_id: str,
    open_identity: ComparisonModelIdentityArtifact,
    closed_identity: ComparisonModelIdentityArtifact,
    open_configuration_ref: ArtifactRef,
    closed_configuration_ref: ArtifactRef,
    open_system_instruction_ref: ArtifactRef,
    closed_system_instruction_ref: ArtifactRef,
    common_refs: tuple[ArtifactRef, ...],
    open_settings: tuple[str, str, int, str],
    closed_settings: tuple[str, str, int, str],
) -> dict[str, Any]:
    return {
        "schema": SHARED_COMPARISON_PROTOCOL_SCHEMA,
        "protocol_id": protocol_id,
        "models": [
            _model_value(
                role=OPEN,
                identity=open_identity,
                configuration_ref=open_configuration_ref,
                system_instruction_ref=open_system_instruction_ref,
                temperature_policy=open_settings[0],
                temperature_value=open_settings[1],
                max_output_tokens=open_settings[2],
                provider_timestamp_recording=open_settings[3],
            ),
            _model_value(
                role=CLOSED,
                identity=closed_identity,
                configuration_ref=closed_configuration_ref,
                system_instruction_ref=closed_system_instruction_ref,
                temperature_policy=closed_settings[0],
                temperature_value=closed_settings[1],
                max_output_tokens=closed_settings[2],
                provider_timestamp_recording=closed_settings[3],
            ),
        ],
        "common_evidence": {
            name: _artifact_ref_value(reference)
            for (name, _), reference in zip(_COMMON_REF_SPECS, common_refs, strict=True)
        },
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_shared_comparison_protocol(
    raw: Any,
    *,
    protocol_ref: ArtifactRef,
    open_identity: ComparisonModelIdentityArtifact,
    open_configuration_ref: ArtifactRef,
    open_configuration_bytes: bytes,
    open_system_instruction_ref: ArtifactRef,
    open_temperature_policy: str,
    open_temperature_value: str,
    open_max_output_tokens: int,
    open_provider_timestamp_recording: str,
    closed_identity: ComparisonModelIdentityArtifact,
    closed_configuration_ref: ArtifactRef,
    closed_configuration_bytes: bytes,
    closed_system_instruction_ref: ArtifactRef,
    closed_temperature_policy: str,
    closed_temperature_value: str,
    closed_max_output_tokens: int,
    closed_provider_timestamp_recording: str,
    semantic_task_ref: ArtifactRef,
    injection_taxonomy_ref: ArtifactRef,
    clean_controls_ref: ArtifactRef,
    tool_definitions_ref: ArtifactRef,
    authorization_boundary_ref: ArtifactRef,
    output_schema_ref: ArtifactRef,
    instruction_equivalence_ref: ArtifactRef,
    independent_evaluator_ref: ArtifactRef,
    time_policy_ref: ArtifactRef,
) -> SharedComparisonProtocolArtifact:
    snapshot, value = _canonical_object(raw, "shared comparison protocol")
    protocol_ref = _require_artifact_ref(protocol_ref, "protocol_ref")
    _require_ref_media(
        protocol_ref, BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE, "protocol_ref"
    )
    if not protocol_ref.verify_bytes(snapshot):
        raise SharedComparisonProtocolValidationError(
            "protocol bytes do not match the exact protocol reference"
        )
    expect_keys(
        value,
        required={
            "schema", "protocol_id", "models", "common_evidence", "status", "boundary"
        },
        path="$",
    )
    if value["schema"] != SHARED_COMPARISON_PROTOCOL_SCHEMA:
        raise SharedComparisonProtocolValidationError("shared protocol schema drifted")
    protocol_id = expect_machine_id(value["protocol_id"], "$.protocol_id")
    if protocol_id != protocol_ref.artifact_id:
        raise SharedComparisonProtocolValidationError(
            "protocol_id differs from the exact protocol reference"
        )
    open_identity = replay_comparison_model_identity(open_identity)
    closed_identity = replay_comparison_model_identity(closed_identity)
    if open_identity.access_kind != OPEN_WEIGHT:
        raise SharedComparisonProtocolValidationError(
            "OPEN role requires an exact OPEN_WEIGHT identity"
        )
    if closed_identity.access_kind != CLOSED_WEIGHT:
        raise SharedComparisonProtocolValidationError(
            "CLOSED role requires an exact CLOSED_WEIGHT identity"
        )
    if (open_identity.provider, open_identity.model_id) == (
        closed_identity.provider,
        closed_identity.model_id,
    ):
        raise SharedComparisonProtocolValidationError(
            "shared comparison must bind two different models"
        )
    open_configuration_bytes = _validate_configuration(
        reference=open_configuration_ref,
        raw=open_configuration_bytes,
        identity=open_identity,
        path="open_configuration",
    )
    closed_configuration_bytes = _validate_configuration(
        reference=closed_configuration_ref,
        raw=closed_configuration_bytes,
        identity=closed_identity,
        path="closed_configuration",
    )
    _require_artifact_ref(open_system_instruction_ref, "open_system_instruction_ref")
    _require_ref_media(
        open_system_instruction_ref,
        SYSTEM_INSTRUCTION_MEDIA_TYPE,
        "open_system_instruction_ref",
    )
    _require_artifact_ref(closed_system_instruction_ref, "closed_system_instruction_ref")
    _require_ref_media(
        closed_system_instruction_ref,
        SYSTEM_INSTRUCTION_MEDIA_TYPE,
        "closed_system_instruction_ref",
    )
    common_refs = _common_refs(
        semantic_task_ref=semantic_task_ref,
        injection_taxonomy_ref=injection_taxonomy_ref,
        clean_controls_ref=clean_controls_ref,
        tool_definitions_ref=tool_definitions_ref,
        authorization_boundary_ref=authorization_boundary_ref,
        output_schema_ref=output_schema_ref,
        instruction_equivalence_ref=instruction_equivalence_ref,
        independent_evaluator_ref=independent_evaluator_ref,
        time_policy_ref=time_policy_ref,
    )
    open_settings = _validate_model_settings(
        policy=open_temperature_policy,
        value=open_temperature_value,
        max_output_tokens=open_max_output_tokens,
        timestamp_recording=open_provider_timestamp_recording,
        path="open_model",
    )
    closed_settings = _validate_model_settings(
        policy=closed_temperature_policy,
        value=closed_temperature_value,
        max_output_tokens=closed_max_output_tokens,
        timestamp_recording=closed_provider_timestamp_recording,
        path="closed_model",
    )
    if open_settings[2] != closed_settings[2]:
        raise SharedComparisonProtocolValidationError(
            "OPEN and CLOSED models must use an equal max output token limit"
        )
    direct_refs = (
        open_identity.artifact_ref,
        open_configuration_ref,
        open_system_instruction_ref,
        closed_identity.artifact_ref,
        closed_configuration_ref,
        closed_system_instruction_ref,
        *common_refs,
    )
    _require_distinct_roles(
        direct_refs, owner_id=protocol_id, path="shared protocol role references"
    )
    models = expect_list(value["models"], "$.models")
    if len(models) != 2:
        raise SharedComparisonProtocolValidationError(
            "$.models must contain exactly OPEN then CLOSED"
        )
    for index, expected in enumerate(
        _protocol_value(
            protocol_id=protocol_id,
            open_identity=open_identity,
            closed_identity=closed_identity,
            open_configuration_ref=open_configuration_ref,
            closed_configuration_ref=closed_configuration_ref,
            open_system_instruction_ref=open_system_instruction_ref,
            closed_system_instruction_ref=closed_system_instruction_ref,
            common_refs=common_refs,
            open_settings=open_settings,
            closed_settings=closed_settings,
        )["models"]
    ):
        model = expect_object(models[index], f"$.models[{index}]")
        expect_keys(model, required=expected, path=f"$.models[{index}]")
        parse_artifact_ref(model["identity_ref"], f"$.models[{index}].identity_ref")
        parse_artifact_ref(
            model["configuration_ref"], f"$.models[{index}].configuration_ref"
        )
        parse_artifact_ref(
            model["system_instruction_ref"],
            f"$.models[{index}].system_instruction_ref",
        )
        if model != expected:
            raise SharedComparisonProtocolValidationError(
                f"$.models[{index}] differs from its exact model binding"
            )
    common = expect_object(value["common_evidence"], "$.common_evidence")
    expect_keys(common, required={name for name, _ in _COMMON_REF_SPECS}, path="$.common_evidence")
    for (name, _), expected_ref in zip(_COMMON_REF_SPECS, common_refs, strict=True):
        if parse_artifact_ref(common[name], f"$.common_evidence.{name}") != expected_ref:
            raise SharedComparisonProtocolValidationError(
                f"$.common_evidence.{name} differs from the caller-bound reference"
            )
    _require_status_and_boundary(value)
    expected_value = _protocol_value(
        protocol_id=protocol_id,
        open_identity=open_identity,
        closed_identity=closed_identity,
        open_configuration_ref=open_configuration_ref,
        closed_configuration_ref=closed_configuration_ref,
        open_system_instruction_ref=open_system_instruction_ref,
        closed_system_instruction_ref=closed_system_instruction_ref,
        common_refs=common_refs,
        open_settings=open_settings,
        closed_settings=closed_settings,
    )
    if value != expected_value:
        raise SharedComparisonProtocolValidationError(
            "shared protocol differs from its exact caller-bound projection"
        )
    dependencies = _unique_ref_closure(
        (
            open_identity.artifact_ref,
            *open_identity.artifact_refs,
            open_configuration_ref,
            open_system_instruction_ref,
            closed_identity.artifact_ref,
            *closed_identity.artifact_refs,
            closed_configuration_ref,
            closed_system_instruction_ref,
            *common_refs,
        ),
        "shared protocol artifact closure",
    )
    _unique_ref_closure((protocol_ref, *dependencies), "shared protocol owner closure")
    return SharedComparisonProtocolArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        protocol_id=protocol_id,
        open_identity=open_identity,
        closed_identity=closed_identity,
        open_configuration_ref=open_configuration_ref,
        open_configuration_bytes=open_configuration_bytes,
        closed_configuration_ref=closed_configuration_ref,
        closed_configuration_bytes=closed_configuration_bytes,
        open_system_instruction_ref=open_system_instruction_ref,
        closed_system_instruction_ref=closed_system_instruction_ref,
        semantic_task_ref=common_refs[0],
        injection_taxonomy_ref=common_refs[1],
        clean_controls_ref=common_refs[2],
        tool_definitions_ref=common_refs[3],
        authorization_boundary_ref=common_refs[4],
        output_schema_ref=common_refs[5],
        instruction_equivalence_ref=common_refs[6],
        independent_evaluator_ref=common_refs[7],
        time_policy_ref=common_refs[8],
        open_temperature_policy=open_settings[0],
        open_temperature_value=open_settings[1],
        closed_temperature_policy=closed_settings[0],
        closed_temperature_value=closed_settings[1],
        open_max_output_tokens=open_settings[2],
        closed_max_output_tokens=closed_settings[2],
        open_provider_timestamp_recording=open_settings[3],
        closed_provider_timestamp_recording=closed_settings[3],
        payload=freeze_json(value),
        artifact_refs=dependencies,
    )


def build_shared_comparison_protocol(
    *,
    protocol_id: str,
    open_identity: ComparisonModelIdentityArtifact,
    open_configuration_ref: ArtifactRef,
    open_configuration_bytes: bytes,
    open_system_instruction_ref: ArtifactRef,
    open_temperature_policy: str,
    open_temperature_value: str,
    open_max_output_tokens: int,
    open_provider_timestamp_recording: str,
    closed_identity: ComparisonModelIdentityArtifact,
    closed_configuration_ref: ArtifactRef,
    closed_configuration_bytes: bytes,
    closed_system_instruction_ref: ArtifactRef,
    closed_temperature_policy: str,
    closed_temperature_value: str,
    closed_max_output_tokens: int,
    closed_provider_timestamp_recording: str,
    semantic_task_ref: ArtifactRef,
    injection_taxonomy_ref: ArtifactRef,
    clean_controls_ref: ArtifactRef,
    tool_definitions_ref: ArtifactRef,
    authorization_boundary_ref: ArtifactRef,
    output_schema_ref: ArtifactRef,
    instruction_equivalence_ref: ArtifactRef,
    independent_evaluator_ref: ArtifactRef,
    time_policy_ref: ArtifactRef,
) -> SharedComparisonProtocolArtifact:
    """Build one canonical, replay-only shared comparison protocol."""

    protocol_id = expect_machine_id(protocol_id, "protocol_id")
    open_identity = replay_comparison_model_identity(open_identity)
    closed_identity = replay_comparison_model_identity(closed_identity)
    common_refs = _common_refs(
        semantic_task_ref=semantic_task_ref,
        injection_taxonomy_ref=injection_taxonomy_ref,
        clean_controls_ref=clean_controls_ref,
        tool_definitions_ref=tool_definitions_ref,
        authorization_boundary_ref=authorization_boundary_ref,
        output_schema_ref=output_schema_ref,
        instruction_equivalence_ref=instruction_equivalence_ref,
        independent_evaluator_ref=independent_evaluator_ref,
        time_policy_ref=time_policy_ref,
    )
    open_settings = _validate_model_settings(
        policy=open_temperature_policy,
        value=open_temperature_value,
        max_output_tokens=open_max_output_tokens,
        timestamp_recording=open_provider_timestamp_recording,
        path="open_model",
    )
    closed_settings = _validate_model_settings(
        policy=closed_temperature_policy,
        value=closed_temperature_value,
        max_output_tokens=closed_max_output_tokens,
        timestamp_recording=closed_provider_timestamp_recording,
        path="closed_model",
    )
    raw = canonical_json_bytes(
        _protocol_value(
            protocol_id=protocol_id,
            open_identity=open_identity,
            closed_identity=closed_identity,
            open_configuration_ref=open_configuration_ref,
            closed_configuration_ref=closed_configuration_ref,
            open_system_instruction_ref=open_system_instruction_ref,
            closed_system_instruction_ref=closed_system_instruction_ref,
            common_refs=common_refs,
            open_settings=open_settings,
            closed_settings=closed_settings,
        )
    )
    protocol_ref = ArtifactRef(
        artifact_id=protocol_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    )
    return _load_shared_comparison_protocol(
        raw,
        protocol_ref=protocol_ref,
        open_identity=open_identity,
        open_configuration_ref=open_configuration_ref,
        open_configuration_bytes=open_configuration_bytes,
        open_system_instruction_ref=open_system_instruction_ref,
        open_temperature_policy=open_temperature_policy,
        open_temperature_value=open_temperature_value,
        open_max_output_tokens=open_max_output_tokens,
        open_provider_timestamp_recording=open_provider_timestamp_recording,
        closed_identity=closed_identity,
        closed_configuration_ref=closed_configuration_ref,
        closed_configuration_bytes=closed_configuration_bytes,
        closed_system_instruction_ref=closed_system_instruction_ref,
        closed_temperature_policy=closed_temperature_policy,
        closed_temperature_value=closed_temperature_value,
        closed_max_output_tokens=closed_max_output_tokens,
        closed_provider_timestamp_recording=closed_provider_timestamp_recording,
        semantic_task_ref=semantic_task_ref,
        injection_taxonomy_ref=injection_taxonomy_ref,
        clean_controls_ref=clean_controls_ref,
        tool_definitions_ref=tool_definitions_ref,
        authorization_boundary_ref=authorization_boundary_ref,
        output_schema_ref=output_schema_ref,
        instruction_equivalence_ref=instruction_equivalence_ref,
        independent_evaluator_ref=independent_evaluator_ref,
        time_policy_ref=time_policy_ref,
    )


def load_shared_comparison_protocol(
    raw: bytes | bytearray | memoryview,
    *,
    protocol_ref: ArtifactRef,
    open_identity: ComparisonModelIdentityArtifact,
    open_configuration_ref: ArtifactRef,
    open_configuration_bytes: bytes,
    open_system_instruction_ref: ArtifactRef,
    open_temperature_policy: str,
    open_temperature_value: str,
    open_max_output_tokens: int,
    open_provider_timestamp_recording: str,
    closed_identity: ComparisonModelIdentityArtifact,
    closed_configuration_ref: ArtifactRef,
    closed_configuration_bytes: bytes,
    closed_system_instruction_ref: ArtifactRef,
    closed_temperature_policy: str,
    closed_temperature_value: str,
    closed_max_output_tokens: int,
    closed_provider_timestamp_recording: str,
    semantic_task_ref: ArtifactRef,
    injection_taxonomy_ref: ArtifactRef,
    clean_controls_ref: ArtifactRef,
    tool_definitions_ref: ArtifactRef,
    authorization_boundary_ref: ArtifactRef,
    output_schema_ref: ArtifactRef,
    instruction_equivalence_ref: ArtifactRef,
    independent_evaluator_ref: ArtifactRef,
    time_policy_ref: ArtifactRef,
) -> SharedComparisonProtocolArtifact:
    """Load canonical protocol bytes against every caller-bound dependency."""

    return _load_shared_comparison_protocol(
        raw,
        protocol_ref=protocol_ref,
        open_identity=open_identity,
        open_configuration_ref=open_configuration_ref,
        open_configuration_bytes=open_configuration_bytes,
        open_system_instruction_ref=open_system_instruction_ref,
        open_temperature_policy=open_temperature_policy,
        open_temperature_value=open_temperature_value,
        open_max_output_tokens=open_max_output_tokens,
        open_provider_timestamp_recording=open_provider_timestamp_recording,
        closed_identity=closed_identity,
        closed_configuration_ref=closed_configuration_ref,
        closed_configuration_bytes=closed_configuration_bytes,
        closed_system_instruction_ref=closed_system_instruction_ref,
        closed_temperature_policy=closed_temperature_policy,
        closed_temperature_value=closed_temperature_value,
        closed_max_output_tokens=closed_max_output_tokens,
        closed_provider_timestamp_recording=closed_provider_timestamp_recording,
        semantic_task_ref=semantic_task_ref,
        injection_taxonomy_ref=injection_taxonomy_ref,
        clean_controls_ref=clean_controls_ref,
        tool_definitions_ref=tool_definitions_ref,
        authorization_boundary_ref=authorization_boundary_ref,
        output_schema_ref=output_schema_ref,
        instruction_equivalence_ref=instruction_equivalence_ref,
        independent_evaluator_ref=independent_evaluator_ref,
        time_policy_ref=time_policy_ref,
    )


def replay_shared_comparison_protocol(
    artifact: SharedComparisonProtocolArtifact,
) -> SharedComparisonProtocolArtifact:
    """Freshly replay one immutable shared protocol projection."""

    _require_storage(artifact, SharedComparisonProtocolArtifact, "protocol")
    if any(
        type(item) is not str
        for item in (
            artifact.protocol_id,
            artifact.open_temperature_policy,
            artifact.open_temperature_value,
            artifact.closed_temperature_policy,
            artifact.closed_temperature_value,
            artifact.open_provider_timestamp_recording,
            artifact.closed_provider_timestamp_recording,
        )
    ) or any(
        type(item) is not int
        for item in (artifact.open_max_output_tokens, artifact.closed_max_output_tokens)
    ) or any(
        type(item) is not bytes
        for item in (
            artifact.open_configuration_bytes,
            artifact.closed_configuration_bytes,
        )
    ):
        raise SharedComparisonProtocolValidationError(
            "protocol projections must use exact immutable scalar types"
        )
    replayed = _load_shared_comparison_protocol(
        artifact.raw_bytes,
        protocol_ref=artifact.artifact_ref,
        open_identity=artifact.open_identity,
        open_configuration_ref=artifact.open_configuration_ref,
        open_configuration_bytes=artifact.open_configuration_bytes,
        open_system_instruction_ref=artifact.open_system_instruction_ref,
        open_temperature_policy=artifact.open_temperature_policy,
        open_temperature_value=artifact.open_temperature_value,
        open_max_output_tokens=artifact.open_max_output_tokens,
        open_provider_timestamp_recording=artifact.open_provider_timestamp_recording,
        closed_identity=artifact.closed_identity,
        closed_configuration_ref=artifact.closed_configuration_ref,
        closed_configuration_bytes=artifact.closed_configuration_bytes,
        closed_system_instruction_ref=artifact.closed_system_instruction_ref,
        closed_temperature_policy=artifact.closed_temperature_policy,
        closed_temperature_value=artifact.closed_temperature_value,
        closed_max_output_tokens=artifact.closed_max_output_tokens,
        closed_provider_timestamp_recording=artifact.closed_provider_timestamp_recording,
        semantic_task_ref=artifact.semantic_task_ref,
        injection_taxonomy_ref=artifact.injection_taxonomy_ref,
        clean_controls_ref=artifact.clean_controls_ref,
        tool_definitions_ref=artifact.tool_definitions_ref,
        authorization_boundary_ref=artifact.authorization_boundary_ref,
        output_schema_ref=artifact.output_schema_ref,
        instruction_equivalence_ref=artifact.instruction_equivalence_ref,
        independent_evaluator_ref=artifact.independent_evaluator_ref,
        time_policy_ref=artifact.time_policy_ref,
    )
    if replayed != artifact:
        raise SharedComparisonProtocolValidationError(
            "shared protocol differs from fresh exact-byte replay"
        )
    return replayed


def _case_value(
    *,
    case_id: str,
    group_id: str,
    role: str,
    protocol_ref: ArtifactRef,
    prompt_ref: ArtifactRef,
    prompt_source_map_ref: ArtifactRef,
) -> dict[str, Any]:
    return {
        "schema": BEHAVIORAL_COMPARISON_CASE_SCHEMA,
        "case_id": case_id,
        "group_id": group_id,
        "role": role,
        "protocol_ref": _artifact_ref_value(protocol_ref),
        "prompt_ref": _artifact_ref_value(prompt_ref),
        "prompt_source_map_ref": _artifact_ref_value(prompt_source_map_ref),
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_behavioral_comparison_case(
    raw: Any,
    *,
    case_ref: ArtifactRef,
    case_id: str,
    group_id: str,
    role: str,
    protocol: SharedComparisonProtocolArtifact,
    prompt_ref: ArtifactRef,
    prompt_source_map_ref: ArtifactRef,
) -> BehavioralComparisonCaseArtifact:
    snapshot, value = _canonical_object(raw, "behavioral comparison case")
    protocol = replay_shared_comparison_protocol(protocol)
    case_ref = _require_artifact_ref(case_ref, "case_ref")
    _require_ref_media(case_ref, BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE, "case_ref")
    if not case_ref.verify_bytes(snapshot):
        raise SharedComparisonProtocolValidationError(
            "case bytes do not match the exact case reference"
        )
    case_id = expect_machine_id(case_id, "case_id")
    group_id = expect_machine_id(group_id, "group_id")
    role = expect_enum(role, set(CASE_ROLES), "role")
    if case_ref.artifact_id != case_id:
        raise SharedComparisonProtocolValidationError(
            "case_id differs from the exact case reference"
        )
    _require_artifact_ref(prompt_ref, "prompt_ref")
    _require_ref_media(prompt_ref, BEHAVIORAL_PROMPT_MEDIA_TYPE, "prompt_ref")
    _require_artifact_ref(prompt_source_map_ref, "prompt_source_map_ref")
    _require_ref_media(
        prompt_source_map_ref, PROMPT_SOURCE_MAP_MEDIA_TYPE, "prompt_source_map_ref"
    )
    _require_distinct_roles(
        (protocol.artifact_ref, prompt_ref, prompt_source_map_ref),
        owner_id=case_id,
        path="behavioral case role references",
    )
    expect_keys(
        value,
        required={
            "schema", "case_id", "group_id", "role", "protocol_ref", "prompt_ref",
            "prompt_source_map_ref", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != BEHAVIORAL_COMPARISON_CASE_SCHEMA:
        raise SharedComparisonProtocolValidationError("behavioral case schema drifted")
    parse_artifact_ref(value["protocol_ref"], "$.protocol_ref")
    parse_artifact_ref(value["prompt_ref"], "$.prompt_ref")
    parse_artifact_ref(value["prompt_source_map_ref"], "$.prompt_source_map_ref")
    _require_status_and_boundary(value)
    expected = _case_value(
        case_id=case_id,
        group_id=group_id,
        role=role,
        protocol_ref=protocol.artifact_ref,
        prompt_ref=prompt_ref,
        prompt_source_map_ref=prompt_source_map_ref,
    )
    if value != expected:
        raise SharedComparisonProtocolValidationError(
            "behavioral case differs from its exact caller-bound projection"
        )
    dependencies = _unique_ref_closure(
        (
            protocol.artifact_ref,
            *protocol.artifact_refs,
            prompt_ref,
            prompt_source_map_ref,
        ),
        "behavioral case artifact closure",
    )
    _unique_ref_closure((case_ref, *dependencies), "behavioral case owner closure")
    return BehavioralComparisonCaseArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        case_id=case_id,
        group_id=group_id,
        role=role,
        protocol_ref=protocol.artifact_ref,
        prompt_ref=prompt_ref,
        prompt_source_map_ref=prompt_source_map_ref,
        payload=freeze_json(value),
        artifact_refs=dependencies,
    )


def build_behavioral_comparison_case(
    *,
    case_id: str,
    group_id: str,
    role: str,
    protocol: SharedComparisonProtocolArtifact,
    prompt_ref: ArtifactRef,
    prompt_source_map_ref: ArtifactRef,
) -> BehavioralComparisonCaseArtifact:
    """Build one canonical case bound to a shared comparison protocol."""

    protocol = replay_shared_comparison_protocol(protocol)
    case_id = expect_machine_id(case_id, "case_id")
    group_id = expect_machine_id(group_id, "group_id")
    role = expect_enum(role, set(CASE_ROLES), "role")
    raw = canonical_json_bytes(
        _case_value(
            case_id=case_id,
            group_id=group_id,
            role=role,
            protocol_ref=protocol.artifact_ref,
            prompt_ref=prompt_ref,
            prompt_source_map_ref=prompt_source_map_ref,
        )
    )
    case_ref = ArtifactRef(
        artifact_id=case_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    )
    return _load_behavioral_comparison_case(
        raw,
        case_ref=case_ref,
        case_id=case_id,
        group_id=group_id,
        role=role,
        protocol=protocol,
        prompt_ref=prompt_ref,
        prompt_source_map_ref=prompt_source_map_ref,
    )


def load_behavioral_comparison_case(
    raw: bytes | bytearray | memoryview,
    *,
    case_ref: ArtifactRef,
    case_id: str,
    group_id: str,
    role: str,
    protocol: SharedComparisonProtocolArtifact,
    prompt_ref: ArtifactRef,
    prompt_source_map_ref: ArtifactRef,
) -> BehavioralComparisonCaseArtifact:
    """Load canonical case bytes against every caller-bound case field."""

    return _load_behavioral_comparison_case(
        raw,
        case_ref=case_ref,
        case_id=case_id,
        group_id=group_id,
        role=role,
        protocol=protocol,
        prompt_ref=prompt_ref,
        prompt_source_map_ref=prompt_source_map_ref,
    )


def replay_behavioral_comparison_case(
    artifact: BehavioralComparisonCaseArtifact,
    *,
    protocol: SharedComparisonProtocolArtifact,
) -> BehavioralComparisonCaseArtifact:
    """Freshly replay one immutable behavioral case projection."""

    _require_storage(artifact, BehavioralComparisonCaseArtifact, "case")
    if any(
        type(item) is not str
        for item in (artifact.case_id, artifact.group_id, artifact.role)
    ):
        raise SharedComparisonProtocolValidationError(
            "case projections must use exact immutable scalar types"
        )
    replayed = _load_behavioral_comparison_case(
        artifact.raw_bytes,
        case_ref=artifact.artifact_ref,
        case_id=artifact.case_id,
        group_id=artifact.group_id,
        role=artifact.role,
        protocol=protocol,
        prompt_ref=artifact.prompt_ref,
        prompt_source_map_ref=artifact.prompt_source_map_ref,
    )
    if replayed != artifact:
        raise SharedComparisonProtocolValidationError(
            "behavioral case differs from fresh exact-byte replay"
        )
    return replayed


def _validate_case_sequence(
    cases: Any, *, protocol: SharedComparisonProtocolArtifact
) -> tuple[tuple[BehavioralComparisonCaseArtifact, ...], tuple[FrozenComparisonGroup, ...]]:
    if type(cases) is not tuple or not cases:
        raise SharedComparisonProtocolValidationError(
            "cases must be a nonempty exact tuple"
        )
    if len(cases) % len(CASE_ROLES) != 0:
        raise SharedComparisonProtocolValidationError(
            "cases must contain exactly three rows per matched group"
        )
    replayed = tuple(
        replay_behavioral_comparison_case(case, protocol=protocol) for case in cases
    )
    groups: list[FrozenComparisonGroup] = []
    seen_groups: set[str] = set()
    for offset in range(0, len(replayed), len(CASE_ROLES)):
        chunk = replayed[offset : offset + len(CASE_ROLES)]
        group_id = chunk[0].group_id
        if group_id in seen_groups:
            raise SharedComparisonProtocolValidationError(
                "matched group identifiers must be unique and contiguous"
            )
        seen_groups.add(group_id)
        if any(case.group_id != group_id for case in chunk):
            raise SharedComparisonProtocolValidationError(
                "matched group cases must be contiguous"
            )
        if tuple(case.role for case in chunk) != CASE_ROLES:
            raise SharedComparisonProtocolValidationError(
                "each matched group must use the fixed three-role order"
            )
        groups.append(
            FrozenComparisonGroup(
                group_ordinal=len(groups) + 1,
                group_id=group_id,
                cases=chunk,
            )
        )
    case_role_refs = tuple(
        reference
        for case in replayed
        for reference in (case.artifact_ref, case.prompt_ref, case.prompt_source_map_ref)
    )
    _require_distinct_roles(
        case_role_refs,
        owner_id="__roster_owner_checked_later__",
        path="roster case role references",
    )
    return replayed, tuple(groups)


def _roster_value(
    *,
    roster_id: str,
    protocol_ref: ArtifactRef,
    groups: tuple[FrozenComparisonGroup, ...],
) -> dict[str, Any]:
    execution_ordinal = 0
    group_values: list[dict[str, Any]] = []
    for group in groups:
        case_values: list[dict[str, Any]] = []
        for case in group.cases:
            execution_ordinal += 1
            case_values.append(
                {
                    "execution_ordinal": execution_ordinal,
                    "case_ref": _artifact_ref_value(case.artifact_ref),
                }
            )
        group_values.append(
            {
                "group_ordinal": group.group_ordinal,
                "group_id": group.group_id,
                "cases": case_values,
            }
        )
    return {
        "schema": FROZEN_COMPARISON_ROSTER_SCHEMA,
        "roster_id": roster_id,
        "protocol_ref": _artifact_ref_value(protocol_ref),
        "groups": group_values,
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_frozen_comparison_roster(
    raw: Any,
    *,
    roster_ref: ArtifactRef,
    protocol: SharedComparisonProtocolArtifact,
    cases: tuple[BehavioralComparisonCaseArtifact, ...],
) -> FrozenComparisonRosterArtifact:
    snapshot, value = _canonical_object(raw, "frozen comparison roster")
    protocol = replay_shared_comparison_protocol(protocol)
    roster_ref = _require_artifact_ref(roster_ref, "roster_ref")
    _require_ref_media(roster_ref, FROZEN_COMPARISON_ROSTER_MEDIA_TYPE, "roster_ref")
    if not roster_ref.verify_bytes(snapshot):
        raise SharedComparisonProtocolValidationError(
            "roster bytes do not match the exact roster reference"
        )
    expect_keys(
        value,
        required={"schema", "roster_id", "protocol_ref", "groups", "status", "boundary"},
        path="$",
    )
    if value["schema"] != FROZEN_COMPARISON_ROSTER_SCHEMA:
        raise SharedComparisonProtocolValidationError("frozen roster schema drifted")
    roster_id = expect_machine_id(value["roster_id"], "$.roster_id")
    if roster_id != roster_ref.artifact_id:
        raise SharedComparisonProtocolValidationError(
            "roster_id differs from the exact roster reference"
        )
    if parse_artifact_ref(value["protocol_ref"], "$.protocol_ref") != protocol.artifact_ref:
        raise SharedComparisonProtocolValidationError(
            "roster protocol reference differs from the caller-bound protocol"
        )
    replayed_cases, groups = _validate_case_sequence(cases, protocol=protocol)
    parsed_groups = expect_list(value["groups"], "$.groups")
    if len(parsed_groups) != len(groups):
        raise SharedComparisonProtocolValidationError(
            "roster group count differs from the caller-bound cases"
        )
    expected = _roster_value(
        roster_id=roster_id, protocol_ref=protocol.artifact_ref, groups=groups
    )
    for group_index, raw_group in enumerate(parsed_groups):
        group = expect_object(raw_group, f"$.groups[{group_index}]")
        expect_keys(
            group,
            required={"group_ordinal", "group_id", "cases"},
            path=f"$.groups[{group_index}]",
        )
        expect_int(group["group_ordinal"], f"$.groups[{group_index}].group_ordinal", minimum=1)
        expect_machine_id(group["group_id"], f"$.groups[{group_index}].group_id")
        raw_cases = expect_list(group["cases"], f"$.groups[{group_index}].cases")
        if len(raw_cases) != len(CASE_ROLES):
            raise SharedComparisonProtocolValidationError(
                "each roster group must contain exactly three cases"
            )
        for case_index, raw_case in enumerate(raw_cases):
            row = expect_object(
                raw_case, f"$.groups[{group_index}].cases[{case_index}]"
            )
            expect_keys(
                row,
                required={"execution_ordinal", "case_ref"},
                path=f"$.groups[{group_index}].cases[{case_index}]",
            )
            expect_int(
                row["execution_ordinal"],
                f"$.groups[{group_index}].cases[{case_index}].execution_ordinal",
                minimum=1,
            )
            parse_artifact_ref(
                row["case_ref"],
                f"$.groups[{group_index}].cases[{case_index}].case_ref",
            )
    _require_status_and_boundary(value)
    if value != expected:
        raise SharedComparisonProtocolValidationError(
            "frozen roster differs from its contiguous caller-bound projection"
        )
    dependencies = _unique_ref_closure(
        (
            protocol.artifact_ref,
            *protocol.artifact_refs,
            *(
                reference
                for case in replayed_cases
                for reference in (case.artifact_ref, *case.artifact_refs)
            ),
        ),
        "frozen roster artifact closure",
    )
    _unique_ref_closure((roster_ref, *dependencies), "frozen roster owner closure")
    return FrozenComparisonRosterArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        roster_id=roster_id,
        protocol=protocol,
        groups=groups,
        cases=replayed_cases,
        payload=freeze_json(value),
        artifact_refs=dependencies,
    )


def build_frozen_comparison_roster(
    *,
    roster_id: str,
    protocol: SharedComparisonProtocolArtifact,
    cases: tuple[BehavioralComparisonCaseArtifact, ...],
) -> FrozenComparisonRosterArtifact:
    """Build a nonempty, ordered, matched three-role comparison roster."""

    roster_id = expect_machine_id(roster_id, "roster_id")
    protocol = replay_shared_comparison_protocol(protocol)
    replayed_cases, groups = _validate_case_sequence(cases, protocol=protocol)
    raw = canonical_json_bytes(
        _roster_value(
            roster_id=roster_id,
            protocol_ref=protocol.artifact_ref,
            groups=groups,
        )
    )
    roster_ref = ArtifactRef(
        artifact_id=roster_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=FROZEN_COMPARISON_ROSTER_MEDIA_TYPE,
    )
    return _load_frozen_comparison_roster(
        raw,
        roster_ref=roster_ref,
        protocol=protocol,
        cases=replayed_cases,
    )


def load_frozen_comparison_roster(
    raw: bytes | bytearray | memoryview,
    *,
    roster_ref: ArtifactRef,
    protocol: SharedComparisonProtocolArtifact,
    cases: tuple[BehavioralComparisonCaseArtifact, ...],
) -> FrozenComparisonRosterArtifact:
    """Load canonical roster bytes against exact protocol and case artifacts."""

    return _load_frozen_comparison_roster(
        raw,
        roster_ref=roster_ref,
        protocol=protocol,
        cases=cases,
    )


def replay_frozen_comparison_roster(
    artifact: FrozenComparisonRosterArtifact,
) -> FrozenComparisonRosterArtifact:
    """Freshly replay one immutable frozen roster projection."""

    _require_storage(artifact, FrozenComparisonRosterArtifact, "roster")
    if (
        type(artifact.roster_id) is not str
        or type(artifact.groups) is not tuple
        or type(artifact.cases) is not tuple
    ):
        raise SharedComparisonProtocolValidationError(
            "roster projections must use exact immutable types"
        )
    for index, group in enumerate(artifact.groups):
        if (
            type(group) is not FrozenComparisonGroup
            or type(group.group_ordinal) is not int
            or type(group.group_id) is not str
            or type(group.cases) is not tuple
        ):
            raise SharedComparisonProtocolValidationError(
                f"roster.groups[{index}] must use exact immutable projection types"
            )
    replayed = _load_frozen_comparison_roster(
        artifact.raw_bytes,
        roster_ref=artifact.artifact_ref,
        protocol=artifact.protocol,
        cases=artifact.cases,
    )
    if replayed != artifact:
        raise SharedComparisonProtocolValidationError(
            "frozen roster differs from fresh exact-byte replay"
        )
    return replayed
