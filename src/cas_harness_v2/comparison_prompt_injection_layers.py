"""Strict non-executing prompt-injection comparison layers.

This module only builds, loads, and replays canonical evidence associations.
It has no model, provider, network, tool, action, or filesystem execution path.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ._strict_json import (
    canonical_json_bytes,
    freeze_json,
    load_json_object,
    mapping_proxy_backing_dict,
    sha256_bytes,
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
    parse_artifact_ref,
)
from .comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    CLOSED_WEIGHT,
    HIDDEN_STATE_OBSERVATION,
    OPEN_WEIGHT,
    REPLAY,
    SUPPORTED_WITH_EVIDENCE,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelIdentityArtifact,
    replay_comparison_model_capabilities,
    replay_comparison_model_identity,
)


TEXT_CONTEXT_DETECTOR_SCHEMA = (
    "cas_harness_v2.comparison_text_context_detector_result.v1"
)
HIDDEN_STATE_DETECTOR_SCHEMA = (
    "cas_harness_v2.comparison_hidden_state_detector_result.v1"
)
RUNTIME_POLICY_GATE_SCHEMA = "cas_harness_v2.comparison_runtime_policy_gate_result.v1"
COMBINED_INJECTION_REPORT_SCHEMA = (
    "cas_harness_v2.comparison_combined_prompt_injection_report.v1"
)

TEXT_CONTEXT_DETECTOR_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-text-context-detector-result-v1+json"
)
HIDDEN_STATE_DETECTOR_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-hidden-state-detector-result-v1+json"
)
RUNTIME_POLICY_GATE_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-runtime-policy-gate-result-v1+json"
)
COMBINED_INJECTION_REPORT_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-combined-injection-report-v1+json"
)
TEXT_SOURCE_CONTEXT_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-text-source-context-v1+json"
)
TEXT_DETECTION_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-text-detection-evidence-v1+json"
)
BEHAVIORAL_PROTOCOL_MEDIA_TYPE = (
    "application/vnd.cas-harness.behavioral-comparison-protocol-v1+json"
)
BEHAVIORAL_CASE_MEDIA_TYPE = (
    "application/vnd.cas-harness.behavioral-comparison-case-v1+json"
)
HIDDEN_CAPTURE_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-hidden-capture-v1+json"
)
HIDDEN_CALIBRATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-hidden-calibration-v1+json"
)
HIDDEN_DETECTION_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-hidden-detection-evidence-v1+json"
)
HIDDEN_CONTROL_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-hidden-control-evidence-v1+json"
)
REQUESTED_ACTION_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-requested-action-v1+json"
)
REQUESTED_TOOL_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-requested-tool-v1+json"
)
REQUESTED_DATA_SCOPE_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-requested-data-scope-v1+json"
)
EXECUTION_AUTHORIZATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-execution-authorization-v1+json"
)
RUNTIME_POLICY_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-runtime-policy-evidence-v1+json"
)

USER = "USER"
SYSTEM = "SYSTEM"
TOOL = "TOOL"
RETRIEVED = "RETRIEVED"
EXTERNAL = "EXTERNAL"
TEXT_SOURCES = (USER, SYSTEM, TOOL, RETRIEVED, EXTERNAL)

PRIORITY_OVERRIDE = "PRIORITY_OVERRIDE"
DATA_EXFILTRATION = "DATA_EXFILTRATION"
TOOL_MISUSE = "TOOL_MISUSE"
ENCODED = "ENCODED"
INDIRECT = "INDIRECT"
MULTILINGUAL = "MULTILINGUAL"
FRAGMENTED = "FRAGMENTED"
AUTHORIZATION_CONFLICT = "AUTHORIZATION_CONFLICT"
ATTACK_CATEGORIES = (
    PRIORITY_OVERRIDE,
    DATA_EXFILTRATION,
    TOOL_MISUSE,
    ENCODED,
    INDIRECT,
    MULTILINGUAL,
    FRAGMENTED,
    AUTHORIZATION_CONFLICT,
)

NULL = "NULL"
CLEAN = "CLEAN"
WRONG_LAYER = "WRONG_LAYER"
SHUFFLED_LABEL = "SHUFFLED_LABEL"
KNOWN_FAULT = "KNOWN_FAULT"
HIDDEN_CONTROL_NAMES = (NULL, CLEAN, WRONG_LAYER, SHUFFLED_LABEL, KNOWN_FAULT)

PREFILL_ALL_TOKENS = "PREFILL_ALL_TOKENS"
PREFILL_LAST_TOKEN = "PREFILL_LAST_TOKEN"
GENERATED_TOKENS = "GENERATED_TOKENS"
FULL_SEQUENCE = "FULL_SEQUENCE"
TOKEN_SCOPES = (
    PREFILL_ALL_TOKENS,
    PREFILL_LAST_TOKEN,
    GENERATED_TOKENS,
    FULL_SEQUENCE,
)

OBSERVED = "OBSERVED"
UNAVAILABLE = "UNAVAILABLE"
UNAVAILABLE_BY_ACCESS_MODEL = "UNAVAILABLE_BY_ACCESS_MODEL"
UNAVAILABLE_IN_REPLAY = "UNAVAILABLE_IN_REPLAY"

EXACT_AUTHORIZATION = "EXACT_AUTHORIZATION"
OUTSIDE_EXACT_AUTHORIZATION = "OUTSIDE_EXACT_AUTHORIZATION"
AUTHORIZATION_RELATIONS = (EXACT_AUTHORIZATION, OUTSIDE_EXACT_AUTHORIZATION)
DENY = "DENY"
ALLOW_FOR_SEPARATE_AUTHORIZED_EXECUTION_ONLY = (
    "ALLOW_FOR_SEPARATE_AUTHORIZED_EXECUTION_ONLY"
)
RUNTIME_POLICY_DECISIONS = (DENY, ALLOW_FOR_SEPARATE_AUTHORIZED_EXECUTION_ONLY)

STRUCTURE_ONLY = "STRUCTURE_ONLY"
NON_AUTHORITY = "NON_AUTHORITY"
NOT_PERFORMED = "NOT_PERFORMED"

_STATUS = MappingProxyType({"scope": STRUCTURE_ONLY, "authority": NON_AUTHORITY})
_BOUNDARY = MappingProxyType({
    "execution": NOT_PERFORMED,
    "model_call": NOT_PERFORMED,
    "provider_call": NOT_PERFORMED,
    "network_call": NOT_PERFORMED,
    "tool_invocation": NOT_PERFORMED,
    "action_execution": NOT_PERFORMED,
    "data_access": NOT_PERFORMED,
    "filesystem_write": NOT_PERFORMED,
})


class PromptInjectionLayerValidationError(SchemaValidationError):
    """A layered detector carrier violated its exact closed contract."""


@dataclass(frozen=True, slots=True)
class TextSourceCategoryResult:
    source: str
    category: str
    detected: bool
    confidence_ppm: int
    evidence_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class HiddenControlResult:
    name: str
    detected: bool
    confidence_ppm: int
    evidence_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class DetectorDisagreement:
    source: str
    category: str
    text_detected: bool
    hidden_detected: bool | None
    disagrees: bool | None


@dataclass(frozen=True, slots=True)
class TextContextDetectorArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    result_id: str
    protocol_ref: ArtifactRef
    case_id: str
    case_ref: ArtifactRef
    source_context_refs: tuple[tuple[str, ArtifactRef], ...]
    results: tuple[TextSourceCategoryResult, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            self.result_id,
            self.sha256,
            self.byte_length,
            TEXT_CONTEXT_DETECTOR_MEDIA_TYPE,
        )

    def result(self, source: str, category: str) -> TextSourceCategoryResult:
        matches = tuple(
            item
            for item in self.results
            if item.source == source and item.category == category
        )
        if len(matches) != 1:
            raise PromptInjectionLayerValidationError(
                "source/category must resolve exactly one detector result"
            )
        return matches[0]


@dataclass(frozen=True, slots=True)
class HiddenStateDetectorArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    result_id: str
    identity: ComparisonModelIdentityArtifact
    capabilities: ComparisonModelCapabilitiesArtifact
    protocol_ref: ArtifactRef
    case_id: str
    case_ref: ArtifactRef
    capture_ref: ArtifactRef | None
    calibration_ref: ArtifactRef | None
    detector_status: str
    unavailable_reason: str | None
    target_layers: tuple[int, ...] | None
    control_layers: tuple[int, ...] | None
    token_scope: str | None
    detected: bool | None
    confidence_ppm: int | None
    evidence_ref: ArtifactRef | None
    controls: tuple[HiddenControlResult, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            self.result_id,
            self.sha256,
            self.byte_length,
            HIDDEN_STATE_DETECTOR_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class RuntimePolicyGateArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    result_id: str
    requested_action_ref: ArtifactRef
    requested_tool_ref: ArtifactRef
    requested_data_scope_ref: ArtifactRef
    authorization_ref: ArtifactRef
    authorization_relation: str
    decision: str
    evidence_ref: ArtifactRef
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            self.result_id,
            self.sha256,
            self.byte_length,
            RUNTIME_POLICY_GATE_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class CombinedPromptInjectionReportArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    report_id: str
    text_result: TextContextDetectorArtifact
    hidden_result: HiddenStateDetectorArtifact
    runtime_result: RuntimePolicyGateArtifact
    disagreements: tuple[DetectorDisagreement, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            self.report_id,
            self.sha256,
            self.byte_length,
            COMBINED_INJECTION_REPORT_MEDIA_TYPE,
        )


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    reference = _require_ref(reference, "artifact_ref")
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _require_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise PromptInjectionLayerValidationError(f"{path} must be an exact ArtifactRef")
    return value


def _require_media(reference: ArtifactRef, expected: str, path: str) -> ArtifactRef:
    reference = _require_ref(reference, path)
    if reference.media_type != expected:
        raise PromptInjectionLayerValidationError(
            f"{path}.media_type must be {expected!r}"
        )
    return reference


def _canonical_object(raw: bytes | bytearray | memoryview, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise PromptInjectionLayerValidationError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, value
    except PromptInjectionLayerValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise PromptInjectionLayerValidationError(f"{path}: {exc}") from exc


def _require_fixed(value: dict[str, Any]) -> None:
    status = expect_object(value["status"], "$.status")
    expect_keys(status, required=_STATUS, path="$.status")
    boundary = expect_object(value["boundary"], "$.boundary")
    expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    if status != _STATUS or boundary != _BOUNDARY:
        raise PromptInjectionLayerValidationError(
            "layered detector status/boundary must remain STRUCTURE_ONLY/NON_AUTHORITY"
        )


def _require_frozen(value: Any, path: str) -> None:
    if type(value) is MappingProxyType:
        backing = mapping_proxy_backing_dict(value)
        if backing is None:
            raise PromptInjectionLayerValidationError(
                f"{path} mapping proxy must wrap an exact dict"
            )
        for key, child in backing.items():
            if type(key) is not str:
                raise PromptInjectionLayerValidationError(
                    f"{path} keys must be exact strings"
                )
            _require_frozen(child, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, child in enumerate(value):
            _require_frozen(child, f"{path}[{index}]")
        return
    if type(value) in (str, int, bool) or value is None:
        return
    raise PromptInjectionLayerValidationError(
        f"{path} must be recursively frozen canonical JSON"
    )


def _require_storage(value: Any, expected: type[Any], path: str) -> None:
    if type(value) is not expected:
        raise PromptInjectionLayerValidationError(
            f"{path} must be an exact {expected.__name__}"
        )
    if (
        type(value.raw_bytes) is not bytes
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.artifact_refs) is not tuple
        or value.sha256 != sha256_bytes(value.raw_bytes)
        or value.byte_length != len(value.raw_bytes)
    ):
        raise PromptInjectionLayerValidationError(
            f"{path} storage projections must be exact and byte-bound"
        )
    _require_frozen(value.payload, f"{path}.payload")
    for index, reference in enumerate(value.artifact_refs):
        _require_ref(reference, f"{path}.artifact_refs[{index}]")


def _direct_distinct(references: tuple[ArtifactRef, ...], path: str) -> None:
    ids: set[str] = set()
    content: set[tuple[str, int]] = set()
    for index, reference in enumerate(references):
        reference = _require_ref(reference, f"{path}[{index}]")
        content_key = (reference.sha256, reference.byte_length)
        if reference.artifact_id in ids or content_key in content:
            raise PromptInjectionLayerValidationError(
                f"{path} reuses an artifact identity or content across distinct roles"
            )
        ids.add(reference.artifact_id)
        content.add(content_key)


def _dependency_closure(
    references: tuple[ArtifactRef, ...],
    *,
    owner_id: str,
    owner_raw: bytes,
    owner_media_type: str,
    path: str,
) -> tuple[ArtifactRef, ...]:
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], ArtifactRef] = {}
    ordered: list[ArtifactRef] = []
    owner_ref = ArtifactRef(
        owner_id, sha256_bytes(owner_raw), len(owner_raw), owner_media_type
    )
    if owner_id in {reference.artifact_id for reference in references}:
        raise PromptInjectionLayerValidationError(
            f"{path} collides with the carrier artifact ID"
        )
    for index, reference in enumerate((*references, owner_ref)):
        reference = _require_ref(reference, f"{path}[{index}]")
        prior = by_id.get(reference.artifact_id)
        if prior is not None:
            if prior != reference:
                raise PromptInjectionLayerValidationError(
                    f"{path} reuses one artifact ID for different content"
                )
            continue
        content_key = (reference.sha256, reference.byte_length)
        prior_content = by_content.get(content_key)
        if prior_content is not None:
            raise PromptInjectionLayerValidationError(
                f"{path} clones one content identity under different artifact IDs"
            )
        by_id[reference.artifact_id] = reference
        by_content[content_key] = reference
        ordered.append(reference)
    return tuple(reference for reference in ordered if reference != owner_ref)


def _status_value() -> dict[str, str]:
    return dict(_STATUS)


def _boundary_value() -> dict[str, str]:
    return dict(_BOUNDARY)


def _validate_source_contexts(
    value: Mapping[str, ArtifactRef],
) -> tuple[tuple[str, ArtifactRef], ...]:
    if (
        type(value) is not dict
        or any(type(key) is not str for key in value)
        or tuple(value) != TEXT_SOURCES
    ):
        raise PromptInjectionLayerValidationError(
            "source_context_refs must be an exact ordered dict for every fixed source"
        )
    rows = tuple(
        (
            source,
            _require_media(
                value[source], TEXT_SOURCE_CONTEXT_MEDIA_TYPE, f"source_context_refs.{source}"
            ),
        )
        for source in TEXT_SOURCES
    )
    _direct_distinct(tuple(reference for _, reference in rows), "source_context_refs")
    return rows


def _validate_text_results(
    results: tuple[TextSourceCategoryResult, ...],
) -> tuple[TextSourceCategoryResult, ...]:
    expected = tuple((source, category) for source in TEXT_SOURCES for category in ATTACK_CATEGORIES)
    if type(results) is not tuple or len(results) != len(expected):
        raise PromptInjectionLayerValidationError(
            "text results must contain the complete fixed source/category matrix"
        )
    validated: list[TextSourceCategoryResult] = []
    for index, ((source, category), item) in enumerate(zip(expected, results, strict=True)):
        if type(item) is not TextSourceCategoryResult:
            raise PromptInjectionLayerValidationError(
                "text results must contain exact TextSourceCategoryResult values"
            )
        if type(item.source) is not str or type(item.category) is not str:
            raise PromptInjectionLayerValidationError(
                "text source/category projections must be exact strings"
            )
        if item.source != source or item.category != category:
            raise PromptInjectionLayerValidationError(
                "text results omitted, duplicated, or reordered a source/category"
            )
        detected = expect_bool(item.detected, f"results[{index}].detected")
        confidence = expect_int(
            item.confidence_ppm,
            f"results[{index}].confidence_ppm",
            minimum=0,
            maximum=1_000_000,
        )
        evidence = _require_media(
            item.evidence_ref,
            TEXT_DETECTION_EVIDENCE_MEDIA_TYPE,
            f"results[{index}].evidence_ref",
        )
        validated.append(
            TextSourceCategoryResult(source, category, detected, confidence, evidence)
        )
    _direct_distinct(
        tuple(item.evidence_ref for item in validated), "text result evidence"
    )
    return tuple(validated)


def _text_value(
    *,
    result_id: str,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
    source_contexts: tuple[tuple[str, ArtifactRef], ...],
    results: tuple[TextSourceCategoryResult, ...],
) -> dict[str, Any]:
    return {
        "schema": TEXT_CONTEXT_DETECTOR_SCHEMA,
        "result_id": result_id,
        "protocol_ref": _ref_value(protocol_ref),
        "case": {"case_id": case_id, "artifact_ref": _ref_value(case_ref)},
        "source_contexts": [
            {"source": source, "context_ref": _ref_value(reference)}
            for source, reference in source_contexts
        ],
        "results": [
            {
                "source": item.source,
                "category": item.category,
                "detected": item.detected,
                "confidence_ppm": item.confidence_ppm,
                "evidence_ref": _ref_value(item.evidence_ref),
            }
            for item in results
        ],
        "status": _status_value(),
        "boundary": _boundary_value(),
    }


def build_text_context_detector_result(
    *,
    result_id: str,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
    source_context_refs: Mapping[str, ArtifactRef],
    results: tuple[TextSourceCategoryResult, ...],
) -> TextContextDetectorArtifact:
    result_id = expect_machine_id(result_id, "result_id")
    protocol_ref = _require_media(protocol_ref, BEHAVIORAL_PROTOCOL_MEDIA_TYPE, "protocol_ref")
    case_id = expect_machine_id(case_id, "case_id")
    case_ref = _require_media(case_ref, BEHAVIORAL_CASE_MEDIA_TYPE, "case_ref")
    contexts = _validate_source_contexts(source_context_refs)
    validated = _validate_text_results(results)
    raw = canonical_json_bytes(
        _text_value(
            result_id=result_id,
            protocol_ref=protocol_ref,
            case_id=case_id,
            case_ref=case_ref,
            source_contexts=contexts,
            results=validated,
        )
    )
    return load_text_context_detector_result(
        raw,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
        source_context_refs=dict(contexts),
    )


def load_text_context_detector_result(
    raw: bytes | bytearray | memoryview,
    *,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
    source_context_refs: Mapping[str, ArtifactRef],
) -> TextContextDetectorArtifact:
    protocol_ref = _require_media(protocol_ref, BEHAVIORAL_PROTOCOL_MEDIA_TYPE, "protocol_ref")
    case_id = expect_machine_id(case_id, "case_id")
    case_ref = _require_media(case_ref, BEHAVIORAL_CASE_MEDIA_TYPE, "case_ref")
    contexts = _validate_source_contexts(source_context_refs)
    snapshot, value = _canonical_object(raw, "text/context detector result")
    expect_keys(
        value,
        required={
            "schema", "result_id", "protocol_ref", "case", "source_contexts",
            "results", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != TEXT_CONTEXT_DETECTOR_SCHEMA:
        raise PromptInjectionLayerValidationError("text detector schema drifted")
    result_id = expect_machine_id(value["result_id"], "$.result_id")
    if parse_artifact_ref(value["protocol_ref"], "$.protocol_ref") != protocol_ref:
        raise PromptInjectionLayerValidationError("text detector protocol binding changed")
    case = expect_object(value["case"], "$.case")
    expect_keys(case, required={"case_id", "artifact_ref"}, path="$.case")
    if (
        expect_machine_id(case["case_id"], "$.case.case_id") != case_id
        or parse_artifact_ref(case["artifact_ref"], "$.case.artifact_ref") != case_ref
    ):
        raise PromptInjectionLayerValidationError("text detector case binding changed")
    raw_contexts = expect_list(value["source_contexts"], "$.source_contexts")
    if len(raw_contexts) != len(TEXT_SOURCES):
        raise PromptInjectionLayerValidationError("text source roster is incomplete")
    for index, ((source, reference), raw_context) in enumerate(
        zip(contexts, raw_contexts, strict=True)
    ):
        row = expect_object(raw_context, f"$.source_contexts[{index}]")
        expect_keys(row, required={"source", "context_ref"}, path=f"$.source_contexts[{index}]")
        if row["source"] != source or parse_artifact_ref(
            row["context_ref"], f"$.source_contexts[{index}].context_ref"
        ) != reference:
            raise PromptInjectionLayerValidationError("text source binding changed")
    raw_results = expect_list(value["results"], "$.results")
    parsed: list[TextSourceCategoryResult] = []
    for index, raw_result in enumerate(raw_results):
        row = expect_object(raw_result, f"$.results[{index}]")
        expect_keys(
            row,
            required={"source", "category", "detected", "confidence_ppm", "evidence_ref"},
            path=f"$.results[{index}]",
        )
        parsed.append(
            TextSourceCategoryResult(
                source=row["source"],
                category=row["category"],
                detected=row["detected"],
                confidence_ppm=row["confidence_ppm"],
                evidence_ref=parse_artifact_ref(
                    row["evidence_ref"], f"$.results[{index}].evidence_ref"
                ),
            )
        )
    results = _validate_text_results(tuple(parsed))
    _require_fixed(value)
    direct = (
        protocol_ref,
        case_ref,
        *(reference for _, reference in contexts),
        *(item.evidence_ref for item in results),
    )
    _direct_distinct(direct, "text detector direct roles")
    references = _dependency_closure(
        direct,
        owner_id=result_id,
        owner_raw=snapshot,
        owner_media_type=TEXT_CONTEXT_DETECTOR_MEDIA_TYPE,
        path="text detector artifact closure",
    )
    return TextContextDetectorArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        result_id=result_id,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
        source_context_refs=contexts,
        results=results,
        payload=freeze_json(value),
        artifact_refs=references,
    )


def replay_text_context_detector_result(
    artifact: TextContextDetectorArtifact,
) -> TextContextDetectorArtifact:
    _require_storage(artifact, TextContextDetectorArtifact, "text_result")
    if (
        type(artifact.result_id) is not str
        or type(artifact.case_id) is not str
        or type(artifact.source_context_refs) is not tuple
        or type(artifact.results) is not tuple
    ):
        raise PromptInjectionLayerValidationError("text result projections are not immutable")
    if any(
        type(row) is not tuple
        or len(row) != 2
        or type(row[0]) is not str
        or type(row[1]) is not ArtifactRef
        for row in artifact.source_context_refs
    ):
        raise PromptInjectionLayerValidationError(
            "text source projections must use exact immutable types"
        )
    _validate_text_results(artifact.results)
    replayed = load_text_context_detector_result(
        artifact.raw_bytes,
        protocol_ref=artifact.protocol_ref,
        case_id=artifact.case_id,
        case_ref=artifact.case_ref,
        source_context_refs=dict(artifact.source_context_refs),
    )
    if replayed != artifact:
        raise PromptInjectionLayerValidationError(
            "text detector differs from fresh exact-byte replay"
        )
    return replayed


def _replay_model_dependencies(
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> tuple[ComparisonModelIdentityArtifact, ComparisonModelCapabilitiesArtifact]:
    identity = replay_comparison_model_identity(identity)
    capabilities = replay_comparison_model_capabilities(capabilities, identity=identity)
    if capabilities.identity_ref != identity.artifact_ref:
        raise PromptInjectionLayerValidationError("capabilities use a different model identity")
    return identity, capabilities


def _model_value(identity: ComparisonModelIdentityArtifact) -> dict[str, Any]:
    return {
        "identity_ref": _ref_value(identity.artifact_ref),
        "access_kind": identity.access_kind,
        "provider": identity.provider,
        "model_id": identity.model_id,
        "revision": identity.revision,
    }


def _require_model_value(
    value: Any, identity: ComparisonModelIdentityArtifact, path: str
) -> None:
    row = expect_object(value, path)
    expected = _model_value(identity)
    expect_keys(row, required=expected, path=path)
    if row != expected:
        raise PromptInjectionLayerValidationError("hidden detector model binding changed")


def _validate_layers(value: tuple[int, ...] | None, path: str) -> tuple[int, ...]:
    if type(value) is not tuple or not value:
        raise PromptInjectionLayerValidationError(f"{path} must be a non-empty exact tuple")
    rows = tuple(expect_int(item, f"{path}[{index}]", maximum=1_000_000) for index, item in enumerate(value))
    if tuple(sorted(set(rows))) != rows:
        raise PromptInjectionLayerValidationError(f"{path} must be strictly increasing and unique")
    return rows


def _validate_hidden_controls(
    controls: tuple[HiddenControlResult, ...],
) -> tuple[HiddenControlResult, ...]:
    if type(controls) is not tuple or len(controls) != len(HIDDEN_CONTROL_NAMES):
        raise PromptInjectionLayerValidationError("hidden controls must contain every fixed control")
    validated: list[HiddenControlResult] = []
    for index, (name, item) in enumerate(zip(HIDDEN_CONTROL_NAMES, controls, strict=True)):
        if (
            type(item) is not HiddenControlResult
            or type(item.name) is not str
            or item.name != name
        ):
            raise PromptInjectionLayerValidationError("hidden controls are omitted, duplicated, or reordered")
        validated.append(
            HiddenControlResult(
                name=name,
                detected=expect_bool(item.detected, f"controls[{index}].detected"),
                confidence_ppm=expect_int(
                    item.confidence_ppm,
                    f"controls[{index}].confidence_ppm",
                    maximum=1_000_000,
                ),
                evidence_ref=_require_media(
                    item.evidence_ref,
                    HIDDEN_CONTROL_EVIDENCE_MEDIA_TYPE,
                    f"controls[{index}].evidence_ref",
                ),
            )
        )
    _direct_distinct(tuple(item.evidence_ref for item in validated), "hidden control evidence")
    return tuple(validated)


def _validate_hidden_state(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    detector_status: str,
    unavailable_reason: str | None,
    target_layers: tuple[int, ...] | None,
    control_layers: tuple[int, ...] | None,
    token_scope: str | None,
    detected: bool | None,
    confidence_ppm: int | None,
    evidence_ref: ArtifactRef | None,
    controls: tuple[HiddenControlResult, ...],
) -> tuple[
    str, str | None, tuple[int, ...] | None, tuple[int, ...] | None,
    str | None, bool | None, int | None, ArtifactRef | None,
    tuple[HiddenControlResult, ...],
]:
    if identity.access_kind == OPEN_WEIGHT:
        if detector_status != OBSERVED or unavailable_reason is not None:
            raise PromptInjectionLayerValidationError("OPEN_WEIGHT hidden detector must be OBSERVED")
        for capability_name in (HIDDEN_STATE_OBSERVATION, ACTIVATION_CAPTURE):
            if capabilities.capability(capability_name).status != SUPPORTED_WITH_EVIDENCE:
                raise PromptInjectionLayerValidationError(
                    "OPEN_WEIGHT hidden detector requires supported hidden-state and capture capabilities"
                )
        targets = _validate_layers(target_layers, "target_layers")
        controls_layers = _validate_layers(control_layers, "control_layers")
        if set(targets) & set(controls_layers):
            raise PromptInjectionLayerValidationError("target and control layers must be disjoint")
        scope = expect_enum(token_scope, set(TOKEN_SCOPES), "token_scope")
        detected_value = expect_bool(detected, "detected")
        confidence = expect_int(confidence_ppm, "confidence_ppm", maximum=1_000_000)
        evidence = _require_media(
            evidence_ref, HIDDEN_DETECTION_EVIDENCE_MEDIA_TYPE, "evidence_ref"
        )
        control_rows = _validate_hidden_controls(controls)
        return (
            OBSERVED, None, targets, controls_layers, scope, detected_value,
            confidence, evidence, control_rows,
        )
    expected_reason = (
        UNAVAILABLE_BY_ACCESS_MODEL
        if identity.access_kind == CLOSED_WEIGHT
        else UNAVAILABLE_IN_REPLAY
    )
    if detector_status != UNAVAILABLE or unavailable_reason != expected_reason:
        raise PromptInjectionLayerValidationError(
            "CLOSED_WEIGHT/REPLAY hidden detector must be explicitly UNAVAILABLE"
        )
    if any(
        item is not None
        for item in (
            target_layers, control_layers, token_scope, detected, confidence_ppm, evidence_ref
        )
    ) or controls != ():
        raise PromptInjectionLayerValidationError(
            "unavailable hidden detector must omit all hidden fields and evidence"
        )
    return (UNAVAILABLE, expected_reason, None, None, None, None, None, None, ())


def _hidden_value(
    *,
    result_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
    capture_ref: ArtifactRef | None,
    calibration_ref: ArtifactRef | None,
    state: tuple[Any, ...],
) -> dict[str, Any]:
    status, reason, targets, control_layers, scope, detected, confidence, evidence, controls = state
    measurement = None
    if status == OBSERVED:
        measurement = {
            "target_layers": list(targets),
            "control_layers": list(control_layers),
            "token_scope": scope,
            "detected": detected,
            "confidence_ppm": confidence,
            "evidence_ref": _ref_value(evidence),
            "controls": [
                {
                    "name": item.name,
                    "detected": item.detected,
                    "confidence_ppm": item.confidence_ppm,
                    "evidence_ref": _ref_value(item.evidence_ref),
                }
                for item in controls
            ],
        }
    return {
        "schema": HIDDEN_STATE_DETECTOR_SCHEMA,
        "result_id": result_id,
        "model_identity": _model_value(identity),
        "capabilities_ref": _ref_value(capabilities.artifact_ref),
        "configuration_ref": _ref_value(capabilities.configuration_ref),
        "protocol_ref": _ref_value(protocol_ref),
        "case": {"case_id": case_id, "artifact_ref": _ref_value(case_ref)},
        "capture_ref": None if capture_ref is None else _ref_value(capture_ref),
        "calibration_ref": (
            None if calibration_ref is None else _ref_value(calibration_ref)
        ),
        "hidden_state": {
            "status": status,
            "unavailable_reason": reason,
            "measurement": measurement,
        },
        "status": _status_value(),
        "boundary": _boundary_value(),
    }


def build_hidden_state_detector_result(
    *,
    result_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
    capture_ref: ArtifactRef | None,
    calibration_ref: ArtifactRef | None,
    detector_status: str,
    unavailable_reason: str | None,
    target_layers: tuple[int, ...] | None,
    control_layers: tuple[int, ...] | None,
    token_scope: str | None,
    detected: bool | None,
    confidence_ppm: int | None,
    evidence_ref: ArtifactRef | None,
    controls: tuple[HiddenControlResult, ...],
) -> HiddenStateDetectorArtifact:
    result_id = expect_machine_id(result_id, "result_id")
    identity, capabilities = _replay_model_dependencies(identity, capabilities)
    if (
        configuration_ref != capabilities.configuration_ref
        or type(configuration_bytes) is not bytes
        or configuration_bytes != capabilities.configuration_bytes
    ):
        raise PromptInjectionLayerValidationError(
            "hidden detector configuration differs from replayed capabilities"
        )
    protocol_ref = _require_media(protocol_ref, BEHAVIORAL_PROTOCOL_MEDIA_TYPE, "protocol_ref")
    case_id = expect_machine_id(case_id, "case_id")
    case_ref = _require_media(case_ref, BEHAVIORAL_CASE_MEDIA_TYPE, "case_ref")
    if identity.access_kind == OPEN_WEIGHT:
        capture_ref = _require_media(capture_ref, HIDDEN_CAPTURE_MEDIA_TYPE, "capture_ref")
        calibration_ref = _require_media(
            calibration_ref, HIDDEN_CALIBRATION_MEDIA_TYPE, "calibration_ref"
        )
    elif capture_ref is not None or calibration_ref is not None:
        raise PromptInjectionLayerValidationError(
            "unavailable hidden detector must omit capture and calibration evidence"
        )
    state = _validate_hidden_state(
        identity=identity,
        capabilities=capabilities,
        detector_status=detector_status,
        unavailable_reason=unavailable_reason,
        target_layers=target_layers,
        control_layers=control_layers,
        token_scope=token_scope,
        detected=detected,
        confidence_ppm=confidence_ppm,
        evidence_ref=evidence_ref,
        controls=controls,
    )
    raw = canonical_json_bytes(
        _hidden_value(
            result_id=result_id,
            identity=identity,
            capabilities=capabilities,
            protocol_ref=protocol_ref,
            case_id=case_id,
            case_ref=case_ref,
            capture_ref=capture_ref,
            calibration_ref=calibration_ref,
            state=state,
        )
    )
    return load_hidden_state_detector_result(
        raw,
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
        capture_ref=capture_ref,
        calibration_ref=calibration_ref,
    )


def load_hidden_state_detector_result(
    raw: bytes | bytearray | memoryview,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    protocol_ref: ArtifactRef,
    case_id: str,
    case_ref: ArtifactRef,
    capture_ref: ArtifactRef | None,
    calibration_ref: ArtifactRef | None,
) -> HiddenStateDetectorArtifact:
    identity, capabilities = _replay_model_dependencies(identity, capabilities)
    if (
        configuration_ref != capabilities.configuration_ref
        or type(configuration_bytes) is not bytes
        or configuration_bytes != capabilities.configuration_bytes
    ):
        raise PromptInjectionLayerValidationError("hidden detector configuration binding changed")
    protocol_ref = _require_media(protocol_ref, BEHAVIORAL_PROTOCOL_MEDIA_TYPE, "protocol_ref")
    case_id = expect_machine_id(case_id, "case_id")
    case_ref = _require_media(case_ref, BEHAVIORAL_CASE_MEDIA_TYPE, "case_ref")
    if identity.access_kind == OPEN_WEIGHT:
        capture_ref = _require_media(capture_ref, HIDDEN_CAPTURE_MEDIA_TYPE, "capture_ref")
        calibration_ref = _require_media(
            calibration_ref, HIDDEN_CALIBRATION_MEDIA_TYPE, "calibration_ref"
        )
    elif capture_ref is not None or calibration_ref is not None:
        raise PromptInjectionLayerValidationError(
            "unavailable hidden detector must omit capture and calibration evidence"
        )
    snapshot, value = _canonical_object(raw, "hidden-state detector result")
    expect_keys(
        value,
        required={
            "schema", "result_id", "model_identity", "capabilities_ref",
            "configuration_ref", "protocol_ref", "case", "capture_ref",
            "calibration_ref", "hidden_state", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != HIDDEN_STATE_DETECTOR_SCHEMA:
        raise PromptInjectionLayerValidationError("hidden detector schema drifted")
    result_id = expect_machine_id(value["result_id"], "$.result_id")
    _require_model_value(value["model_identity"], identity, "$.model_identity")
    if parse_artifact_ref(value["capabilities_ref"], "$.capabilities_ref") != capabilities.artifact_ref:
        raise PromptInjectionLayerValidationError("hidden detector capabilities binding changed")
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != configuration_ref:
        raise PromptInjectionLayerValidationError("hidden detector configuration reference changed")
    if parse_artifact_ref(value["protocol_ref"], "$.protocol_ref") != protocol_ref:
        raise PromptInjectionLayerValidationError("hidden detector protocol binding changed")
    case = expect_object(value["case"], "$.case")
    expect_keys(case, required={"case_id", "artifact_ref"}, path="$.case")
    if case["case_id"] != case_id or parse_artifact_ref(case["artifact_ref"], "$.case.artifact_ref") != case_ref:
        raise PromptInjectionLayerValidationError("hidden detector case binding changed")
    parsed_capture_ref = (
        None
        if value["capture_ref"] is None
        else parse_artifact_ref(value["capture_ref"], "$.capture_ref")
    )
    parsed_calibration_ref = (
        None
        if value["calibration_ref"] is None
        else parse_artifact_ref(value["calibration_ref"], "$.calibration_ref")
    )
    if parsed_capture_ref != capture_ref:
        raise PromptInjectionLayerValidationError("hidden detector capture binding changed")
    if parsed_calibration_ref != calibration_ref:
        raise PromptInjectionLayerValidationError("hidden detector calibration binding changed")
    hidden = expect_object(value["hidden_state"], "$.hidden_state")
    expect_keys(hidden, required={"status", "unavailable_reason", "measurement"}, path="$.hidden_state")
    controls: tuple[HiddenControlResult, ...] = ()
    target_layers = control_layers = None
    token_scope = detected = confidence = evidence = None
    measurement = hidden["measurement"]
    if measurement is not None:
        row = expect_object(measurement, "$.hidden_state.measurement")
        expect_keys(
            row,
            required={
                "target_layers", "control_layers", "token_scope", "detected",
                "confidence_ppm", "evidence_ref", "controls",
            },
            path="$.hidden_state.measurement",
        )
        target_layers = tuple(expect_list(row["target_layers"], "$.hidden_state.measurement.target_layers"))
        control_layers = tuple(expect_list(row["control_layers"], "$.hidden_state.measurement.control_layers"))
        token_scope = row["token_scope"]
        detected = row["detected"]
        confidence = row["confidence_ppm"]
        evidence = parse_artifact_ref(row["evidence_ref"], "$.hidden_state.measurement.evidence_ref")
        raw_controls = expect_list(row["controls"], "$.hidden_state.measurement.controls")
        controls = tuple(
            HiddenControlResult(
                name=control["name"],
                detected=control["detected"],
                confidence_ppm=control["confidence_ppm"],
                evidence_ref=parse_artifact_ref(
                    control["evidence_ref"], f"$.hidden_state.measurement.controls[{index}].evidence_ref"
                ),
            )
            for index, raw_control in enumerate(raw_controls)
            for control in [expect_object(raw_control, f"$.hidden_state.measurement.controls[{index}]")]
            if not expect_keys(
                control,
                required={"name", "detected", "confidence_ppm", "evidence_ref"},
                path=f"$.hidden_state.measurement.controls[{index}]",
            )
        )
    state = _validate_hidden_state(
        identity=identity,
        capabilities=capabilities,
        detector_status=hidden["status"],
        unavailable_reason=hidden["unavailable_reason"],
        target_layers=target_layers,
        control_layers=control_layers,
        token_scope=token_scope,
        detected=detected,
        confidence_ppm=confidence,
        evidence_ref=evidence,
        controls=controls,
    )
    _require_fixed(value)
    direct_list: list[ArtifactRef] = [
        identity.artifact_ref,
        capabilities.artifact_ref,
        configuration_ref,
        protocol_ref,
        case_ref,
    ]
    if capture_ref is not None:
        direct_list.append(capture_ref)
    if calibration_ref is not None:
        direct_list.append(calibration_ref)
    direct: tuple[ArtifactRef, ...] = tuple(direct_list)
    if state[7] is not None:
        direct = (*direct, state[7], *(item.evidence_ref for item in state[8]))
    _direct_distinct(direct, "hidden detector direct roles")
    references = _dependency_closure(
        (
            *direct,
            *identity.artifact_refs,
            *capabilities.artifact_refs,
        ),
        owner_id=result_id,
        owner_raw=snapshot,
        owner_media_type=HIDDEN_STATE_DETECTOR_MEDIA_TYPE,
        path="hidden detector artifact closure",
    )
    return HiddenStateDetectorArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        result_id=result_id,
        identity=identity,
        capabilities=capabilities,
        protocol_ref=protocol_ref,
        case_id=case_id,
        case_ref=case_ref,
        capture_ref=capture_ref,
        calibration_ref=calibration_ref,
        detector_status=state[0],
        unavailable_reason=state[1],
        target_layers=state[2],
        control_layers=state[3],
        token_scope=state[4],
        detected=state[5],
        confidence_ppm=state[6],
        evidence_ref=state[7],
        controls=state[8],
        payload=freeze_json(value),
        artifact_refs=references,
    )


def replay_hidden_state_detector_result(
    artifact: HiddenStateDetectorArtifact,
) -> HiddenStateDetectorArtifact:
    _require_storage(artifact, HiddenStateDetectorArtifact, "hidden_result")
    if (
        type(artifact.result_id) is not str
        or type(artifact.case_id) is not str
        or type(artifact.detector_status) is not str
        or (
            artifact.unavailable_reason is not None
            and type(artifact.unavailable_reason) is not str
        )
    ):
        raise PromptInjectionLayerValidationError(
            "hidden detector projections must use exact immutable scalar types"
        )
    _validate_hidden_state(
        identity=artifact.identity,
        capabilities=artifact.capabilities,
        detector_status=artifact.detector_status,
        unavailable_reason=artifact.unavailable_reason,
        target_layers=artifact.target_layers,
        control_layers=artifact.control_layers,
        token_scope=artifact.token_scope,
        detected=artifact.detected,
        confidence_ppm=artifact.confidence_ppm,
        evidence_ref=artifact.evidence_ref,
        controls=artifact.controls,
    )
    replayed = load_hidden_state_detector_result(
        artifact.raw_bytes,
        identity=artifact.identity,
        capabilities=artifact.capabilities,
        configuration_ref=artifact.capabilities.configuration_ref,
        configuration_bytes=artifact.capabilities.configuration_bytes,
        protocol_ref=artifact.protocol_ref,
        case_id=artifact.case_id,
        case_ref=artifact.case_ref,
        capture_ref=artifact.capture_ref,
        calibration_ref=artifact.calibration_ref,
    )
    if replayed != artifact:
        raise PromptInjectionLayerValidationError(
            "hidden detector differs from fresh exact-byte replay"
        )
    return replayed


def _validate_runtime_inputs(
    *,
    requested_action_ref: ArtifactRef,
    requested_tool_ref: ArtifactRef,
    requested_data_scope_ref: ArtifactRef,
    authorization_ref: ArtifactRef,
    authorization_relation: str,
    decision: str,
    evidence_ref: ArtifactRef,
) -> tuple[ArtifactRef, ArtifactRef, ArtifactRef, ArtifactRef, str, str, ArtifactRef]:
    action = _require_media(requested_action_ref, REQUESTED_ACTION_MEDIA_TYPE, "requested_action_ref")
    tool = _require_media(requested_tool_ref, REQUESTED_TOOL_MEDIA_TYPE, "requested_tool_ref")
    data_scope = _require_media(requested_data_scope_ref, REQUESTED_DATA_SCOPE_MEDIA_TYPE, "requested_data_scope_ref")
    authorization = _require_media(authorization_ref, EXECUTION_AUTHORIZATION_MEDIA_TYPE, "authorization_ref")
    relation = expect_enum(authorization_relation, set(AUTHORIZATION_RELATIONS), "authorization_relation")
    decision_value = expect_enum(decision, set(RUNTIME_POLICY_DECISIONS), "decision")
    evidence = _require_media(evidence_ref, RUNTIME_POLICY_EVIDENCE_MEDIA_TYPE, "evidence_ref")
    if relation == OUTSIDE_EXACT_AUTHORIZATION and decision_value != DENY:
        raise PromptInjectionLayerValidationError("outside exact authorization must DENY")
    _direct_distinct((action, tool, data_scope, authorization, evidence), "runtime policy direct roles")
    return action, tool, data_scope, authorization, relation, decision_value, evidence


def _runtime_value(result_id: str, state: tuple[Any, ...]) -> dict[str, Any]:
    action, tool, data_scope, authorization, relation, decision, evidence = state
    return {
        "schema": RUNTIME_POLICY_GATE_SCHEMA,
        "result_id": result_id,
        "requested_action_ref": _ref_value(action),
        "requested_tool_ref": _ref_value(tool),
        "requested_data_scope_ref": _ref_value(data_scope),
        "authorization_ref": _ref_value(authorization),
        "authorization_relation": relation,
        "decision": decision,
        "evidence_ref": _ref_value(evidence),
        "runtime_state": {
            "action_execution": NOT_PERFORMED,
            "tool_invocation": NOT_PERFORMED,
            "data_access": NOT_PERFORMED,
        },
        "status": _status_value(),
        "boundary": _boundary_value(),
    }


def build_runtime_policy_gate_result(
    *,
    result_id: str,
    requested_action_ref: ArtifactRef,
    requested_tool_ref: ArtifactRef,
    requested_data_scope_ref: ArtifactRef,
    authorization_ref: ArtifactRef,
    authorization_relation: str,
    decision: str,
    evidence_ref: ArtifactRef,
) -> RuntimePolicyGateArtifact:
    result_id = expect_machine_id(result_id, "result_id")
    state = _validate_runtime_inputs(
        requested_action_ref=requested_action_ref,
        requested_tool_ref=requested_tool_ref,
        requested_data_scope_ref=requested_data_scope_ref,
        authorization_ref=authorization_ref,
        authorization_relation=authorization_relation,
        decision=decision,
        evidence_ref=evidence_ref,
    )
    raw = canonical_json_bytes(_runtime_value(result_id, state))
    return load_runtime_policy_gate_result(
        raw,
        requested_action_ref=state[0],
        requested_tool_ref=state[1],
        requested_data_scope_ref=state[2],
        authorization_ref=state[3],
    )


def load_runtime_policy_gate_result(
    raw: bytes | bytearray | memoryview,
    *,
    requested_action_ref: ArtifactRef,
    requested_tool_ref: ArtifactRef,
    requested_data_scope_ref: ArtifactRef,
    authorization_ref: ArtifactRef,
) -> RuntimePolicyGateArtifact:
    snapshot, value = _canonical_object(raw, "runtime policy gate result")
    expect_keys(
        value,
        required={
            "schema", "result_id", "requested_action_ref", "requested_tool_ref",
            "requested_data_scope_ref", "authorization_ref", "authorization_relation",
            "decision", "evidence_ref", "runtime_state", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != RUNTIME_POLICY_GATE_SCHEMA:
        raise PromptInjectionLayerValidationError("runtime policy schema drifted")
    result_id = expect_machine_id(value["result_id"], "$.result_id")
    supplied = (
        requested_action_ref, requested_tool_ref, requested_data_scope_ref, authorization_ref
    )
    parsed = (
        parse_artifact_ref(value["requested_action_ref"], "$.requested_action_ref"),
        parse_artifact_ref(value["requested_tool_ref"], "$.requested_tool_ref"),
        parse_artifact_ref(value["requested_data_scope_ref"], "$.requested_data_scope_ref"),
        parse_artifact_ref(value["authorization_ref"], "$.authorization_ref"),
    )
    if parsed != supplied:
        raise PromptInjectionLayerValidationError("runtime policy dependency binding changed")
    state = _validate_runtime_inputs(
        requested_action_ref=parsed[0],
        requested_tool_ref=parsed[1],
        requested_data_scope_ref=parsed[2],
        authorization_ref=parsed[3],
        authorization_relation=value["authorization_relation"],
        decision=value["decision"],
        evidence_ref=parse_artifact_ref(value["evidence_ref"], "$.evidence_ref"),
    )
    runtime_state = expect_object(value["runtime_state"], "$.runtime_state")
    expected_runtime = {
        "action_execution": NOT_PERFORMED,
        "tool_invocation": NOT_PERFORMED,
        "data_access": NOT_PERFORMED,
    }
    expect_keys(runtime_state, required=expected_runtime, path="$.runtime_state")
    if runtime_state != expected_runtime:
        raise PromptInjectionLayerValidationError("runtime policy cannot claim an action")
    _require_fixed(value)
    direct = (state[0], state[1], state[2], state[3], state[6])
    references = _dependency_closure(
        direct,
        owner_id=result_id,
        owner_raw=snapshot,
        owner_media_type=RUNTIME_POLICY_GATE_MEDIA_TYPE,
        path="runtime policy artifact closure",
    )
    return RuntimePolicyGateArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        result_id=result_id,
        requested_action_ref=state[0],
        requested_tool_ref=state[1],
        requested_data_scope_ref=state[2],
        authorization_ref=state[3],
        authorization_relation=state[4],
        decision=state[5],
        evidence_ref=state[6],
        payload=freeze_json(value),
        artifact_refs=references,
    )


def replay_runtime_policy_gate_result(
    artifact: RuntimePolicyGateArtifact,
) -> RuntimePolicyGateArtifact:
    _require_storage(artifact, RuntimePolicyGateArtifact, "runtime_result")
    if type(artifact.result_id) is not str:
        raise PromptInjectionLayerValidationError(
            "runtime policy projections must use exact immutable scalar types"
        )
    _validate_runtime_inputs(
        requested_action_ref=artifact.requested_action_ref,
        requested_tool_ref=artifact.requested_tool_ref,
        requested_data_scope_ref=artifact.requested_data_scope_ref,
        authorization_ref=artifact.authorization_ref,
        authorization_relation=artifact.authorization_relation,
        decision=artifact.decision,
        evidence_ref=artifact.evidence_ref,
    )
    replayed = load_runtime_policy_gate_result(
        artifact.raw_bytes,
        requested_action_ref=artifact.requested_action_ref,
        requested_tool_ref=artifact.requested_tool_ref,
        requested_data_scope_ref=artifact.requested_data_scope_ref,
        authorization_ref=artifact.authorization_ref,
    )
    if replayed != artifact:
        raise PromptInjectionLayerValidationError(
            "runtime policy differs from fresh exact-byte replay"
        )
    return replayed


def _disagreements(
    text: TextContextDetectorArtifact,
    hidden: HiddenStateDetectorArtifact,
) -> tuple[DetectorDisagreement, ...]:
    hidden_detected = hidden.detected if hidden.detector_status == OBSERVED else None
    return tuple(
        DetectorDisagreement(
            source=item.source,
            category=item.category,
            text_detected=item.detected,
            hidden_detected=hidden_detected,
            disagrees=(
                None if hidden_detected is None else item.detected != hidden_detected
            ),
        )
        for item in text.results
    )


def _validate_disagreement_projection(
    rows: tuple[DetectorDisagreement, ...],
    expected: tuple[DetectorDisagreement, ...],
) -> tuple[DetectorDisagreement, ...]:
    if type(rows) is not tuple or len(rows) != len(expected):
        raise PromptInjectionLayerValidationError(
            "detector disagreement projection is incomplete"
        )
    for index, (row, expected_row) in enumerate(zip(rows, expected, strict=True)):
        if (
            type(row) is not DetectorDisagreement
            or type(row.source) is not str
            or type(row.category) is not str
            or type(row.text_detected) is not bool
            or (row.hidden_detected is not None and type(row.hidden_detected) is not bool)
            or (row.disagrees is not None and type(row.disagrees) is not bool)
            or row != expected_row
        ):
            raise PromptInjectionLayerValidationError(
                f"detector disagreement projection changed at row {index}"
            )
    return rows


def _combined_value(
    *,
    report_id: str,
    text: TextContextDetectorArtifact,
    hidden: HiddenStateDetectorArtifact,
    runtime: RuntimePolicyGateArtifact,
    disagreements: tuple[DetectorDisagreement, ...],
) -> dict[str, Any]:
    return {
        "schema": COMBINED_INJECTION_REPORT_SCHEMA,
        "report_id": report_id,
        "layers": {
            "text_context_detector_ref": _ref_value(text.artifact_ref),
            "hidden_state_detector_ref": _ref_value(hidden.artifact_ref),
            "runtime_policy_gate_ref": _ref_value(runtime.artifact_ref),
        },
        "detector_disagreements": [
            {
                "source": item.source,
                "category": item.category,
                "text_detected": item.text_detected,
                "hidden_detected": item.hidden_detected,
                "disagrees": item.disagrees,
            }
            for item in disagreements
        ],
        "status": _status_value(),
        "boundary": _boundary_value(),
    }


def build_combined_prompt_injection_report(
    *,
    report_id: str,
    text_result: TextContextDetectorArtifact,
    hidden_result: HiddenStateDetectorArtifact,
    runtime_result: RuntimePolicyGateArtifact,
) -> CombinedPromptInjectionReportArtifact:
    report_id = expect_machine_id(report_id, "report_id")
    text = replay_text_context_detector_result(text_result)
    hidden = replay_hidden_state_detector_result(hidden_result)
    runtime = replay_runtime_policy_gate_result(runtime_result)
    if (
        text.protocol_ref != hidden.protocol_ref
        or text.case_id != hidden.case_id
        or text.case_ref != hidden.case_ref
    ):
        raise PromptInjectionLayerValidationError(
            "combined detector layers must bind the same protocol and case"
        )
    disagreements = _disagreements(text, hidden)
    raw = canonical_json_bytes(
        _combined_value(
            report_id=report_id,
            text=text,
            hidden=hidden,
            runtime=runtime,
            disagreements=disagreements,
        )
    )
    return load_combined_prompt_injection_report(
        raw,
        text_result=text,
        hidden_result=hidden,
        runtime_result=runtime,
    )


def load_combined_prompt_injection_report(
    raw: bytes | bytearray | memoryview,
    *,
    text_result: TextContextDetectorArtifact,
    hidden_result: HiddenStateDetectorArtifact,
    runtime_result: RuntimePolicyGateArtifact,
) -> CombinedPromptInjectionReportArtifact:
    text = replay_text_context_detector_result(text_result)
    hidden = replay_hidden_state_detector_result(hidden_result)
    runtime = replay_runtime_policy_gate_result(runtime_result)
    if text.protocol_ref != hidden.protocol_ref or text.case_id != hidden.case_id or text.case_ref != hidden.case_ref:
        raise PromptInjectionLayerValidationError("combined detector layers mix protocol/case results")
    snapshot, value = _canonical_object(raw, "combined prompt-injection report")
    expect_keys(
        value,
        required={"schema", "report_id", "layers", "detector_disagreements", "status", "boundary"},
        path="$",
    )
    if value["schema"] != COMBINED_INJECTION_REPORT_SCHEMA:
        raise PromptInjectionLayerValidationError("combined detector schema drifted")
    report_id = expect_machine_id(value["report_id"], "$.report_id")
    layers = expect_object(value["layers"], "$.layers")
    expected_layers = {
        "text_context_detector_ref": _ref_value(text.artifact_ref),
        "hidden_state_detector_ref": _ref_value(hidden.artifact_ref),
        "runtime_policy_gate_ref": _ref_value(runtime.artifact_ref),
    }
    expect_keys(layers, required=expected_layers, path="$.layers")
    if layers != expected_layers:
        raise PromptInjectionLayerValidationError("combined detector layer binding changed")
    expected_disagreements = _disagreements(text, hidden)
    rows = expect_list(value["detector_disagreements"], "$.detector_disagreements")
    parsed: list[DetectorDisagreement] = []
    for index, raw_row in enumerate(rows):
        row = expect_object(raw_row, f"$.detector_disagreements[{index}]")
        expect_keys(
            row,
            required={"source", "category", "text_detected", "hidden_detected", "disagrees"},
            path=f"$.detector_disagreements[{index}]",
        )
        hidden_detected = row["hidden_detected"]
        disagrees = row["disagrees"]
        parsed.append(
            DetectorDisagreement(
                source=row["source"],
                category=row["category"],
                text_detected=expect_bool(
                    row["text_detected"],
                    f"$.detector_disagreements[{index}].text_detected",
                ),
                hidden_detected=(
                    None
                    if hidden_detected is None
                    else expect_bool(
                        hidden_detected,
                        f"$.detector_disagreements[{index}].hidden_detected",
                    )
                ),
                disagrees=(
                    None
                    if disagrees is None
                    else expect_bool(
                        disagrees,
                        f"$.detector_disagreements[{index}].disagrees",
                    )
                ),
            )
        )
    disagreements = tuple(parsed)
    _validate_disagreement_projection(disagreements, expected_disagreements)
    _require_fixed(value)
    direct = (text.artifact_ref, hidden.artifact_ref, runtime.artifact_ref)
    _direct_distinct(direct, "combined layer roles")
    references = _dependency_closure(
        (
            *direct,
            *text.artifact_refs,
            *hidden.artifact_refs,
            *runtime.artifact_refs,
        ),
        owner_id=report_id,
        owner_raw=snapshot,
        owner_media_type=COMBINED_INJECTION_REPORT_MEDIA_TYPE,
        path="combined detector artifact closure",
    )
    return CombinedPromptInjectionReportArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        report_id=report_id,
        text_result=text,
        hidden_result=hidden,
        runtime_result=runtime,
        disagreements=disagreements,
        payload=freeze_json(value),
        artifact_refs=references,
    )


def replay_combined_prompt_injection_report(
    artifact: CombinedPromptInjectionReportArtifact,
) -> CombinedPromptInjectionReportArtifact:
    _require_storage(artifact, CombinedPromptInjectionReportArtifact, "combined_report")
    if type(artifact.report_id) is not str:
        raise PromptInjectionLayerValidationError(
            "combined report projections must use exact immutable scalar types"
        )
    _validate_disagreement_projection(
        artifact.disagreements,
        _disagreements(artifact.text_result, artifact.hidden_result),
    )
    replayed = load_combined_prompt_injection_report(
        artifact.raw_bytes,
        text_result=artifact.text_result,
        hidden_result=artifact.hidden_result,
        runtime_result=artifact.runtime_result,
    )
    if replayed != artifact:
        raise PromptInjectionLayerValidationError(
            "combined report differs from fresh exact-byte replay"
        )
    return replayed


__all__ = (
    "TEXT_CONTEXT_DETECTOR_SCHEMA",
    "HIDDEN_STATE_DETECTOR_SCHEMA",
    "RUNTIME_POLICY_GATE_SCHEMA",
    "COMBINED_INJECTION_REPORT_SCHEMA",
    "TEXT_CONTEXT_DETECTOR_MEDIA_TYPE",
    "HIDDEN_STATE_DETECTOR_MEDIA_TYPE",
    "RUNTIME_POLICY_GATE_MEDIA_TYPE",
    "COMBINED_INJECTION_REPORT_MEDIA_TYPE",
    "TEXT_SOURCE_CONTEXT_MEDIA_TYPE",
    "TEXT_DETECTION_EVIDENCE_MEDIA_TYPE",
    "BEHAVIORAL_PROTOCOL_MEDIA_TYPE",
    "BEHAVIORAL_CASE_MEDIA_TYPE",
    "HIDDEN_CAPTURE_MEDIA_TYPE",
    "HIDDEN_CALIBRATION_MEDIA_TYPE",
    "HIDDEN_DETECTION_EVIDENCE_MEDIA_TYPE",
    "HIDDEN_CONTROL_EVIDENCE_MEDIA_TYPE",
    "REQUESTED_ACTION_MEDIA_TYPE",
    "REQUESTED_TOOL_MEDIA_TYPE",
    "REQUESTED_DATA_SCOPE_MEDIA_TYPE",
    "EXECUTION_AUTHORIZATION_MEDIA_TYPE",
    "RUNTIME_POLICY_EVIDENCE_MEDIA_TYPE",
    "USER",
    "SYSTEM",
    "TOOL",
    "RETRIEVED",
    "EXTERNAL",
    "TEXT_SOURCES",
    "PRIORITY_OVERRIDE",
    "DATA_EXFILTRATION",
    "TOOL_MISUSE",
    "ENCODED",
    "INDIRECT",
    "MULTILINGUAL",
    "FRAGMENTED",
    "AUTHORIZATION_CONFLICT",
    "ATTACK_CATEGORIES",
    "NULL",
    "CLEAN",
    "WRONG_LAYER",
    "SHUFFLED_LABEL",
    "KNOWN_FAULT",
    "HIDDEN_CONTROL_NAMES",
    "PREFILL_ALL_TOKENS",
    "PREFILL_LAST_TOKEN",
    "GENERATED_TOKENS",
    "FULL_SEQUENCE",
    "TOKEN_SCOPES",
    "OBSERVED",
    "UNAVAILABLE",
    "UNAVAILABLE_BY_ACCESS_MODEL",
    "UNAVAILABLE_IN_REPLAY",
    "EXACT_AUTHORIZATION",
    "OUTSIDE_EXACT_AUTHORIZATION",
    "AUTHORIZATION_RELATIONS",
    "DENY",
    "ALLOW_FOR_SEPARATE_AUTHORIZED_EXECUTION_ONLY",
    "RUNTIME_POLICY_DECISIONS",
    "STRUCTURE_ONLY",
    "NON_AUTHORITY",
    "NOT_PERFORMED",
    "PromptInjectionLayerValidationError",
    "TextSourceCategoryResult",
    "HiddenControlResult",
    "DetectorDisagreement",
    "TextContextDetectorArtifact",
    "HiddenStateDetectorArtifact",
    "RuntimePolicyGateArtifact",
    "CombinedPromptInjectionReportArtifact",
    "build_text_context_detector_result",
    "load_text_context_detector_result",
    "replay_text_context_detector_result",
    "build_hidden_state_detector_result",
    "load_hidden_state_detector_result",
    "replay_hidden_state_detector_result",
    "build_runtime_policy_gate_result",
    "load_runtime_policy_gate_result",
    "replay_runtime_policy_gate_result",
    "build_combined_prompt_injection_report",
    "load_combined_prompt_injection_report",
    "replay_combined_prompt_injection_report",
)
