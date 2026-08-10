"""Strict, additive Stage C prerequisite intake before preregistration.

This module admits exact owner-supplied prerequisite *candidates* only for
prospective inclusion in a future diagnostic preregistration.  It neither
changes an existing schema nor grants execution, runtime, scientific,
Evidence Packet, licensing, disclosure, or product authority.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
import re
import threading
from types import MappingProxyType
from typing import Any

from ._strict_json import (
    StrictJSONError,
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
    expect_int,
    expect_keys,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
)
from .diagnostic_preregistration import (
    DiagnosticPreregistrationArtifact,
    DiagnosticPreregistrationChain,
    load_diagnostic_preregistration,
)
from .diagnostic_prompt_context_inventory import (
    STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE,
    StageCPromptContextInventoryArtifact,
    StageCPromptContextReplayBundle,
    replay_stagec_prompt_context_inventory_projection,
)
from .diagnostic_study_protocol import (
    DIAGNOSTIC_CASE_COUNT,
    DIAGNOSTIC_GROUP_COUNT,
    DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
    DIAGNOSTIC_VARIANT_ROLES,
    DiagnosticSplitInventoryArtifact,
    load_diagnostic_split_inventory,
)


STAGEC_DETECTOR_DRC_RECEIPT_SCHEMA = (
    "cas_harness_v2.stagec_detector_drc_receipt.v1"
)
STAGEC_DETECTOR_DRC_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-detector-drc-receipt+json"
)
STAGEC_FROZEN_CORPUS_BUNDLE_SCHEMA = (
    "cas_harness_v2.stagec_frozen_corpus_bundle.v1"
)
STAGEC_FROZEN_CORPUS_BUNDLE_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-frozen-corpus-bundle+json"
)
STAGEC_TRUSTED_STORAGE_RECEIPT_SCHEMA = (
    "cas_harness_v2.stagec_trusted_storage_receipt.v1"
)
STAGEC_TRUSTED_STORAGE_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-trusted-storage-receipt+json"
)
STAGEC_EXECUTION_AUTHORIZATION_SCHEMA = (
    "cas_harness_v2.stagec_execution_authorization_candidate.v1"
)
STAGEC_EXECUTION_AUTHORIZATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-execution-authorization-candidate+json"
)
STAGEC_PREREQUISITE_INTAKE_SCHEMA = (
    "cas_harness_v2.stagec_prerequisite_owner_intake.v1"
)
STAGEC_PREREQUISITE_INTAKE_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prerequisite-owner-intake+json"
)
STAGEC_PREREQUISITE_ADMISSION_SCHEMA = (
    "cas_harness_v2.stagec_prerequisite_admission.v1"
)
STAGEC_PREREQUISITE_ADMISSION_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prerequisite-admission+json"
)

STAGEC_PREREQUISITE_TARGET_DOMAIN = (
    "cas_harness_v2.stagec_prerequisite_target.v1"
)
STAGEC_PROSPECTIVE_SUBJECT_DOMAIN = (
    "cas_harness_v2.stagec_prerequisite_prospective_subject.v1"
)
STAGEC_PREREQUISITE_CLOSURE_DOMAIN = (
    "cas_harness_v2.stagec_prerequisite_closure.v1"
)
ADMITTED_FOR_PROSPECTIVE_PREREGISTRATION_ONLY = (
    "ADMITTED_FOR_PROSPECTIVE_PREREGISTRATION_ONLY"
)
OWNER_ASSERTS_PRESENT = "OWNER_ASSERTS_PRESENT"
NOT_PERFORMED_BY_INTAKE = "NOT_PERFORMED_BY_INTAKE"
OWNER_ASSERTED_CANDIDATE_STRUCTURAL_REPLAY_ONLY = (
    "OWNER_ASSERTED_CANDIDATE_STRUCTURAL_REPLAY_ONLY"
)

DETECTOR_DRC_PROFILE_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-detector-drc-profile+json"
)
DETECTOR_RULESET_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-detector-ruleset+json"
)
DETECTOR_KNOWN_FAULT_FIXTURE_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-known-fault-fixture+json"
)
CORPUS_ROWS_MEDIA_TYPE = "application/vnd.cas-harness.stagec-corpus-rows-manifest+json"
CORPUS_ADJUDICATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-corpus-adjudication+json"
)
CORPUS_SPLIT_ASSIGNMENT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-corpus-split-assignment+json"
)
CORPUS_SURFACE_BUNDLE_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-corpus-surface-bundle+json"
)
OBJECT_LOCK_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-object-lock-receipt+json"
)
OBJECT_READBACK_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-object-readback-receipt+json"
)
TRUSTED_TIME_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-trusted-time-receipt+json"
)
STORAGE_VERIFIER_IDENTITY_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-storage-verifier-identity+json"
)
AUTHORIZATION_INSTRUMENT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-authorization-instrument+json"
)

STAGEC_DETECTOR_DRC_PROFILE_SCHEMA = (
    "cas_harness_v2.stagec_detector_drc_profile.v1"
)
STAGEC_DETECTOR_RULESET_SCHEMA = (
    "cas_harness_v2.stagec_detector_ruleset.v1"
)
STAGEC_DETECTOR_KNOWN_FAULT_FIXTURE_SCHEMA = (
    "cas_harness_v2.stagec_known_fault_fixture.v1"
)
STAGEC_CORPUS_ROWS_MANIFEST_SCHEMA = (
    "cas_harness_v2.stagec_corpus_rows_manifest.v1"
)
STAGEC_CORPUS_ADJUDICATION_SCHEMA = (
    "cas_harness_v2.stagec_corpus_adjudication.v1"
)
STAGEC_CORPUS_SPLIT_ASSIGNMENT_SCHEMA = (
    "cas_harness_v2.stagec_corpus_split_assignment.v1"
)
STAGEC_CORPUS_SURFACE_BUNDLE_SCHEMA = (
    "cas_harness_v2.stagec_corpus_surface_bundle.v1"
)
STAGEC_OBJECT_LOCK_RECEIPT_SCHEMA = (
    "cas_harness_v2.stagec_object_lock_receipt.v1"
)
STAGEC_OBJECT_READBACK_RECEIPT_SCHEMA = (
    "cas_harness_v2.stagec_object_readback_receipt.v1"
)
STAGEC_TRUSTED_TIME_RECEIPT_SCHEMA = (
    "cas_harness_v2.stagec_trusted_time_receipt.v1"
)
STAGEC_STORAGE_VERIFIER_IDENTITY_SCHEMA = (
    "cas_harness_v2.stagec_storage_verifier_identity.v1"
)
STAGEC_AUTHORIZATION_INSTRUMENT_SCHEMA = (
    "cas_harness_v2.stagec_authorization_instrument.v1"
)

_DEPENDENCY_SCHEMAS = {
    "drc_profile": STAGEC_DETECTOR_DRC_PROFILE_SCHEMA,
    "detector_ruleset": STAGEC_DETECTOR_RULESET_SCHEMA,
    "known_fault_fixture": STAGEC_DETECTOR_KNOWN_FAULT_FIXTURE_SCHEMA,
    "corpus_rows": STAGEC_CORPUS_ROWS_MANIFEST_SCHEMA,
    "adjudication": STAGEC_CORPUS_ADJUDICATION_SCHEMA,
    "split_assignment": STAGEC_CORPUS_SPLIT_ASSIGNMENT_SCHEMA,
    "surface_bundle": STAGEC_CORPUS_SURFACE_BUNDLE_SCHEMA,
    "object_lock_receipt": STAGEC_OBJECT_LOCK_RECEIPT_SCHEMA,
    "readback_receipt": STAGEC_OBJECT_READBACK_RECEIPT_SCHEMA,
    "trusted_time_receipt": STAGEC_TRUSTED_TIME_RECEIPT_SCHEMA,
    "verifier_identity": STAGEC_STORAGE_VERIFIER_IDENTITY_SCHEMA,
    "authorization_instrument": STAGEC_AUTHORIZATION_INSTRUMENT_SCHEMA,
}
_DEPENDENCY_DOMAINS = {
    "drc_profile": "STAGE_C_DETECTOR_DRC_PROFILE",
    "detector_ruleset": "STAGE_C_DETECTOR_RULESET",
    "known_fault_fixture": "STAGE_C_DETECTOR_KNOWN_FAULT_FIXTURE",
    "corpus_rows": "STAGE_C_CORPUS_ROWS_MANIFEST",
    "adjudication": "STAGE_C_CORPUS_ADJUDICATION",
    "split_assignment": "STAGE_C_CORPUS_SPLIT_ASSIGNMENT",
    "surface_bundle": "STAGE_C_CORPUS_SURFACE_BUNDLE",
    "object_lock_receipt": "STAGE_C_CORPUS_OBJECT_LOCK_RECEIPT",
    "readback_receipt": "STAGE_C_CORPUS_OBJECT_READBACK_RECEIPT",
    "trusted_time_receipt": "STAGE_C_CORPUS_TRUSTED_TIME_RECEIPT",
    "verifier_identity": "STAGE_C_CORPUS_STORAGE_VERIFIER_IDENTITY",
    "authorization_instrument": "STAGE_C_C_CAL_AUTHORIZATION_INSTRUMENT",
}
STAGEC_PREREQUISITE_DEPENDENCY_SCHEMAS = MappingProxyType(
    dict(_DEPENDENCY_SCHEMAS)
)
STAGEC_PREREQUISITE_DEPENDENCY_DOMAINS = MappingProxyType(
    dict(_DEPENDENCY_DOMAINS)
)

_DRC_DOMAIN = "STAGE_C_PROMPT_INJECTION_DETECTOR"
_CORPUS_DOMAIN = "STAGE_C_PROMPT_INJECTION_CORPUS"
_STORAGE_DOMAIN = "STAGE_C_CORPUS_OBJECT_LOCK"
_AUTHORIZATION_DOMAIN = "STAGE_C_DIAGNOSTIC_CALIBRATION_EXECUTION"
_DRC_CHECKS = (
    "CALIBRATION_PROFILE_RESOLVES",
    "KNOWN_FAULT_FIXTURE_REJECTS",
    "MODEL_HOOK_LAYER_POSITION_RESOLVES",
    "OBSERVATION_POINTS_EXIST",
    "PROMPT_PROVENANCE_PATH_OBSERVABLE",
    "SAFETY_PATH_OBSERVABLE",
)
_AUTHORITY = {
    "gate_5": "OPEN",
    "gate_5_disposition": "KEEP_OPEN",
    "stage_c": "DESIGN_ONLY",
    "execution_authority": "UNAUTHORIZED",
    "experiment": "NOT_STARTED",
    "license": "NOT LICENSED",
    "disclosure": "HELD",
    "corpus_status": "NOT FROZEN",
    "runtime_integration": "NOT_INTEGRATED",
    "runtime_authorization": "NOT_GRANTED",
    "external_trust_authentication": "NOT_ESTABLISHED_BY_SERIALIZED_CANDIDATES",
    "candidate_profiles": "STRUCTURAL_REPLAY_ONLY",
    "evidence_packet_v2": "NOT_CREATED",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "product": "NOT_AUTHORIZED",
}
_BOUNDARY = {
    "existing_schemas": "UNCHANGED_ADDITIVE_COMPANION_ONLY",
    "admission_scope": "PROSPECTIVE_PREREGISTRATION_INPUT_ONLY",
    "runtime_consumption": "FORBIDDEN_NOT_INTEGRATED",
    "execution": "NOT_PERFORMED",
    "packet_creation": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
    "serialized_candidate_bodies": "NOT_AN_EXTERNAL_TRUST_ROOT",
    "decision_semantics": "STRUCTURAL_REPLAY_ONLY_NOT_LIVE_PREREQUISITE_PASS",
    "model_capture_execution_identity_comparison": (
        "DEFERRED_TO_POST_PLAN_ACTIVATION"
    ),
}
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")


class StageCPrerequisiteAdmissionError(SchemaValidationError):
    """A candidate, intake, or admission failed strict replay."""


def _domain_errors(function):
    """Normalize every public validation failure to the module domain error."""

    @wraps(function)
    def guarded(*args: Any, **kwargs: Any):
        try:
            return function(*args, **kwargs)
        except StageCPrerequisiteAdmissionError:
            raise
        except (StrictJSONError, SchemaValidationError, ValueError, TypeError, KeyError) as exc:
            raise StageCPrerequisiteAdmissionError(
                f"{function.__name__}: {exc}"
            ) from exc

    return guarded


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _utc_now() -> datetime:
    """Verifier-time anchor; tests may replace this internal clock only."""

    return datetime.now(timezone.utc)


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _canonical_object(raw: bytes | bytearray | memoryview, label: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise StageCPrerequisiteAdmissionError(
                f"{label} must use exact canonical JSON bytes"
            )
    except (StrictJSONError, SchemaValidationError) as exc:
        if isinstance(exc, StageCPrerequisiteAdmissionError):
            raise
        raise StageCPrerequisiteAdmissionError(f"{label}: {exc}") from exc
    return snapshot, value


def _parse_ref_map(
    value: Any,
    *,
    expected_media: Mapping[str, str],
    path: str,
) -> tuple[ArtifactRef, ...]:
    obj = expect_object(value, path)
    expect_keys(obj, required=set(expected_media), path=path)
    result = tuple(parse_artifact_ref(obj[name], f"{path}.{name}") for name in expected_media)
    for name, reference in zip(expected_media, result, strict=True):
        if reference.media_type != expected_media[name]:
            raise StageCPrerequisiteAdmissionError(
                f"{path}.{name} must retain media type {expected_media[name]!r}"
            )
    return result


def _unique_refs(refs: tuple[ArtifactRef, ...], path: str) -> None:
    ids: set[str] = set()
    content: set[tuple[str, int]] = set()
    for reference in refs:
        if type(reference) is not ArtifactRef:
            raise StageCPrerequisiteAdmissionError(f"{path} contains a non-exact ArtifactRef")
        identity = (reference.sha256, reference.byte_length)
        if reference.artifact_id in ids:
            raise StageCPrerequisiteAdmissionError(f"{path} contains duplicate artifact IDs")
        if identity in content:
            raise StageCPrerequisiteAdmissionError(f"{path} clones content under another ID")
        ids.add(reference.artifact_id)
        content.add(identity)


def _verify_bodies(
    refs: tuple[ArtifactRef, ...],
    bodies: tuple[tuple[ArtifactRef, bytes], ...],
    path: str,
) -> tuple[tuple[ArtifactRef, bytes], ...]:
    if type(bodies) is not tuple or len(bodies) != len(refs):
        raise StageCPrerequisiteAdmissionError(
            f"{path} must be an exact ordered body tuple for every ArtifactRef"
        )
    frozen: list[tuple[ArtifactRef, bytes]] = []
    for index, (expected, pair) in enumerate(zip(refs, bodies, strict=True)):
        if (
            type(pair) is not tuple
            or len(pair) != 2
            or type(pair[0]) is not ArtifactRef
            or type(pair[1]) is not bytes
            or pair[0] != expected
            or not expected.verify_bytes(pair[1])
        ):
            raise StageCPrerequisiteAdmissionError(
                f"{path}[{index}] does not verify its exact ordered ref and bytes"
            )
        frozen.append((expected, bytes(pair[1])))
    _unique_refs(tuple(item[0] for item in frozen), path)
    return tuple(frozen)


def _dependency_claims(
    body: tuple[ArtifactRef, bytes],
    *,
    role: str,
    target_binding_sha256: str,
) -> dict[str, Any]:
    """Canonical role-specific semantic envelope; media relabeling is insufficient."""

    _, obj = _canonical_object(body[1], f"{role} dependency body")
    expect_keys(
        obj,
        required={"schema_version", "domain", "target_binding_sha256", "claims"},
        path=f"${role}",
    )
    if obj["schema_version"] != _DEPENDENCY_SCHEMAS[role]:
        raise StageCPrerequisiteAdmissionError(f"{role} dependency has the wrong schema")
    if obj["domain"] != _DEPENDENCY_DOMAINS[role]:
        raise StageCPrerequisiteAdmissionError(f"{role} dependency has the wrong domain")
    if expect_sha256(
        obj["target_binding_sha256"], f"${role}.target_binding_sha256"
    ) != target_binding_sha256:
        raise StageCPrerequisiteAdmissionError(f"{role} dependency binds a different target")
    return expect_object(obj["claims"], f"${role}.claims")


def _claims_by_role(
    bodies: tuple[tuple[ArtifactRef, bytes], ...],
    roles: tuple[str, ...],
    target_binding_sha256: str,
) -> dict[str, dict[str, Any]]:
    if len(bodies) != len(roles):
        raise StageCPrerequisiteAdmissionError("dependency-role cardinality drifted")
    return {
        role: _dependency_claims(
            body, role=role, target_binding_sha256=target_binding_sha256
        )
        for role, body in zip(roles, bodies, strict=True)
    }


def _artifact_ref(carrier: Any, artifact_id: str, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=carrier.sha256,
        byte_length=carrier.byte_length,
        media_type=media_type,
    )


@dataclass(frozen=True, slots=True, init=False, eq=False)
class StageCPrerequisiteFactoryContext:
    split_inventory: DiagnosticSplitInventoryArtifact
    prompt_inventory: StageCPromptContextInventoryArtifact
    model_identity_sha256: str
    capture_profile_sha256: str
    target_binding: Mapping[str, Any]
    target_binding_sha256: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCPrerequisiteFactoryContext is factory-only; use "
            "build_stagec_prerequisite_factory_context"
        )


@dataclass(frozen=True, slots=True)
class StageCDetectorDRCReceiptArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    receipt_id: str
    created_at: str
    target_binding_sha256: str
    known_fault_count: int
    artifact_refs: tuple[ArtifactRef, ...]
    artifact_bodies: tuple[tuple[ArtifactRef, bytes], ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return _artifact_ref(self, self.receipt_id, STAGEC_DETECTOR_DRC_RECEIPT_MEDIA_TYPE)


@dataclass(frozen=True, slots=True)
class StageCFrozenCorpusBundleArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    bundle_id: str
    created_at: str
    target_binding_sha256: str
    artifact_refs: tuple[ArtifactRef, ...]
    artifact_bodies: tuple[tuple[ArtifactRef, bytes], ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return _artifact_ref(self, self.bundle_id, STAGEC_FROZEN_CORPUS_BUNDLE_MEDIA_TYPE)


@dataclass(frozen=True, slots=True)
class StageCTrustedStorageReceiptArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    receipt_id: str
    created_at: str
    target_binding_sha256: str
    object_version_id: str
    retention_until: str
    verified_at: str
    corpus_bundle: ArtifactRef
    artifact_refs: tuple[ArtifactRef, ...]
    artifact_bodies: tuple[tuple[ArtifactRef, bytes], ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return _artifact_ref(self, self.receipt_id, STAGEC_TRUSTED_STORAGE_RECEIPT_MEDIA_TYPE)


@dataclass(frozen=True, slots=True)
class StageCExecutionAuthorizationArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    authorization_id: str
    created_at: str
    target_binding_sha256: str
    prospective_subject_sha256: str
    window_start: str
    window_end: str
    nonce_b64url: str
    state: str
    artifact_refs: tuple[ArtifactRef, ...]
    artifact_bodies: tuple[tuple[ArtifactRef, bytes], ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return _artifact_ref(self, self.authorization_id, STAGEC_EXECUTION_AUTHORIZATION_MEDIA_TYPE)


@dataclass(frozen=True, slots=True)
class StageCPrerequisiteIntakeArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    intake_id: str
    created_at: str
    target_binding_sha256: str
    prospective_subject_sha256: str
    candidate_refs: tuple[ArtifactRef, ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return _artifact_ref(self, self.intake_id, STAGEC_PREREQUISITE_INTAKE_MEDIA_TYPE)


@dataclass(frozen=True, slots=True)
class StageCPrerequisiteAdmissionArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    admission_id: str
    created_at: str
    decision: str
    target_binding_sha256: str
    prospective_subject_sha256: str
    artifact_closure_sha256: str
    artifact_refs: tuple[ArtifactRef, ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return _artifact_ref(self, self.admission_id, STAGEC_PREREQUISITE_ADMISSION_MEDIA_TYPE)


@dataclass(slots=True)
class _ContextSeal:
    context: StageCPrerequisiteFactoryContext
    split: DiagnosticSplitInventoryArtifact
    prompt: StageCPromptContextInventoryArtifact
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...]
    target_binding: Mapping[str, Any]
    target_binding_sha256: str
    origins: dict[int, tuple[Any, str]]
    suite: tuple[Any, ...] | None


_SEALS_LOCK = threading.RLock()
_SEALS: dict[int, _ContextSeal] = {}


def _prompt_dependency_refs(seal: _ContextSeal) -> tuple[ArtifactRef, ...]:
    """Reconstruct the inventory's exact dependency order and verify its seal."""

    refs = (
        seal.split.artifact_ref,
        *(item.artifact_ref for item in seal.split.capture_requests),
        *(row.provenance for row in seal.prompt.rows),
        *seal.prompt.ordered_node_artifacts,
        *seal.prompt.ordered_source_artifacts,
    )
    _unique_refs(refs, "prompt-context exact dependency closure")
    digest = canonical_sha256(
        {
            "domain": "cas_harness_v2.stagec_prompt_context_inventory_dependencies.v1",
            "ordered_artifacts": [_ref_value(reference) for reference in refs],
        }
    )
    if (
        len(refs) != seal.prompt.dependency_artifact_count
        or digest != seal.prompt.dependency_closure_sha256
    ):
        raise StageCPrerequisiteAdmissionError(
            "prompt-context dependency count/digest does not reconstruct exactly"
        )
    return refs


def _capture_closure_sha256(split: DiagnosticSplitInventoryArtifact) -> str:
    return canonical_sha256(
        {
            "domain": "cas_harness_v2.stagec_capture_request_closure.v1",
            "ordered_capture_requests": [
                _ref_value(item.artifact_ref) for item in split.capture_requests
            ],
        }
    )


@_domain_errors
def build_stagec_prerequisite_factory_context(
    *,
    split_inventory: DiagnosticSplitInventoryArtifact,
    prompt_inventory: StageCPromptContextInventoryArtifact,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...],
    model_identity_sha256: str,
    capture_profile_sha256: str,
) -> StageCPrerequisiteFactoryContext:
    """Fully replay the pre-preregistration split/prompt target and process-seal it."""

    try:
        model_digest = expect_sha256(model_identity_sha256, "model_identity_sha256")
        capture_digest = expect_sha256(capture_profile_sha256, "capture_profile_sha256")
        if type(split_inventory) is not DiagnosticSplitInventoryArtifact:
            raise StageCPrerequisiteAdmissionError("split_inventory has the wrong exact type")
        split = load_diagnostic_split_inventory(
            split_inventory.raw_bytes,
            capture_requests=split_inventory.capture_requests,
        )
        if split != split_inventory:
            raise StageCPrerequisiteAdmissionError("split inventory projection differs from replay")
        prompt = replay_stagec_prompt_context_inventory_projection(
            prompt_inventory,
            split_inventory=split,
            replay_bundles=replay_bundles,
        )
        target = {
            "domain": STAGEC_PREREQUISITE_TARGET_DOMAIN,
            "program_id": "gate5-stagec-qwen-prompt-injection-v0.1",
            "study_id": split.study_id,
            "split_id": split.split_id,
            "study_phase": "DIAGNOSTIC_CALIBRATION",
            "group_count": DIAGNOSTIC_GROUP_COUNT,
            "case_count": DIAGNOSTIC_CASE_COUNT,
            "variant_roles": list(DIAGNOSTIC_VARIANT_ROLES),
            "split_inventory": _ref_value(split.artifact_ref),
            "ordered_case_inventory_sha256": split.ordered_case_inventory_sha256,
            "prompt_context_inventory": _ref_value(prompt.artifact_ref),
            "ordered_prompt_contexts_sha256": prompt.ordered_contexts_sha256,
            "prompt_dependency_artifact_count": prompt.dependency_artifact_count,
            "prompt_dependency_closure_sha256": prompt.dependency_closure_sha256,
            "model_identity_sha256": model_digest,
            "capture_profile_sha256": capture_digest,
            "capture_request_closure_sha256": _capture_closure_sha256(split),
        }
        frozen_target = freeze_json(target)
        digest = canonical_sha256(target)
    except (SchemaValidationError, ValueError, TypeError) as exc:
        if isinstance(exc, StageCPrerequisiteAdmissionError):
            raise
        raise StageCPrerequisiteAdmissionError(f"factory context validation failed: {exc}") from exc
    context = object.__new__(StageCPrerequisiteFactoryContext)
    object.__setattr__(context, "split_inventory", split)
    object.__setattr__(context, "prompt_inventory", prompt)
    object.__setattr__(context, "model_identity_sha256", model_digest)
    object.__setattr__(context, "capture_profile_sha256", capture_digest)
    object.__setattr__(context, "target_binding", frozen_target)
    object.__setattr__(context, "target_binding_sha256", digest)
    seal = _ContextSeal(
        context=context,
        split=split,
        prompt=prompt,
        replay_bundles=replay_bundles,
        target_binding=frozen_target,
        target_binding_sha256=digest,
        origins={},
        suite=None,
    )
    _prompt_dependency_refs(seal)
    with _SEALS_LOCK:
        _SEALS[id(context)] = seal
    return context


def _require_context(
    context: StageCPrerequisiteFactoryContext,
    *,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...] | None = None,
) -> _ContextSeal:
    if type(context) is not StageCPrerequisiteFactoryContext:
        raise StageCPrerequisiteAdmissionError("context must have the exact factory-only type")
    with _SEALS_LOCK:
        seal = _SEALS.get(id(context))
    if (
        seal is None
        or seal.context is not context
        or context.split_inventory is not seal.split
        or context.prompt_inventory is not seal.prompt
        or context.target_binding is not seal.target_binding
        or context.target_binding_sha256 != seal.target_binding_sha256
        or context.model_identity_sha256 != seal.target_binding["model_identity_sha256"]
        or context.capture_profile_sha256 != seal.target_binding["capture_profile_sha256"]
    ):
        raise StageCPrerequisiteAdmissionError("context is not the unchanged process-sealed factory result")
    if replay_bundles is not None:
        prompt = replay_stagec_prompt_context_inventory_projection(
            seal.prompt,
            split_inventory=seal.split,
            replay_bundles=replay_bundles,
        )
        if prompt != seal.prompt:
            raise StageCPrerequisiteAdmissionError("prompt inventory full replay drifted")
    return seal


def _register(context: StageCPrerequisiteFactoryContext, carrier: Any, role: str) -> Any:
    seal = _require_context(context)
    with _SEALS_LOCK:
        seal.origins[id(carrier)] = (carrier, role)
    return carrier


def _require_origin(context: StageCPrerequisiteFactoryContext, carrier: Any, role: str) -> None:
    seal = _require_context(context)
    with _SEALS_LOCK:
        observed = seal.origins.get(id(carrier))
    if observed is None or observed[0] is not carrier or observed[1] != role:
        raise StageCPrerequisiteAdmissionError(
            f"{role} is not an exact carrier issued by this process-local context"
        )


def _base_value(
    *, schema: str, artifact_id_name: str, artifact_id: str, domain: str,
    created_at: str, context: StageCPrerequisiteFactoryContext,
) -> dict[str, Any]:
    return {
        "schema_version": schema,
        artifact_id_name: artifact_id,
        "domain": domain,
        "created_at": created_at,
        "target_binding": thaw_json(context.target_binding),
    }


def _require_fixed_tail(obj: Mapping[str, Any], path: str = "$") -> None:
    if obj["authority"] != _AUTHORITY or obj["boundary"] != _BOUNDARY:
        raise StageCPrerequisiteAdmissionError(
            f"{path} attempted to mutate the fixed OPEN/non-authority boundary"
        )


def _require_candidate_status(obj: Mapping[str, Any]) -> None:
    if obj["candidate_status"] != OWNER_ASSERTED_CANDIDATE_STRUCTURAL_REPLAY_ONLY:
        raise StageCPrerequisiteAdmissionError(
            "candidate status must remain owner-asserted structural replay only"
        )


def _require_target(
    obj: Mapping[str, Any], context: StageCPrerequisiteFactoryContext
) -> _ContextSeal:
    seal = _require_context(context)
    if obj["target_binding"] != thaw_json(seal.target_binding):
        raise StageCPrerequisiteAdmissionError("candidate binds a different Stage C target")
    return seal


def _candidate_unique(
    seal: _ContextSeal,
    self_ref: ArtifactRef,
    dependencies: tuple[ArtifactRef, ...],
    path: str,
) -> None:
    _unique_refs(
        (
            seal.prompt.artifact_ref,
            *_prompt_dependency_refs(seal),
            self_ref,
            *dependencies,
        ),
        path,
    )


@_domain_errors
def load_stagec_detector_drc_receipt(
    raw: bytes | bytearray | memoryview,
    *,
    context: StageCPrerequisiteFactoryContext,
    artifact_bodies: tuple[tuple[ArtifactRef, bytes], ...],
) -> StageCDetectorDRCReceiptArtifact:
    """Load a Stage-C-specific detector DRC candidate; PCBA receipts cannot coerce."""

    snapshot, obj = _canonical_object(raw, "Stage C detector DRC receipt")
    expect_keys(
        obj,
        required={
            "schema_version", "receipt_id", "domain", "created_at",
            "candidate_status",
            "target_binding", "artifacts", "checks", "known_fault_validation",
            "authority", "boundary",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_DETECTOR_DRC_RECEIPT_SCHEMA:
        raise StageCPrerequisiteAdmissionError("wrong Stage C detector DRC schema")
    if obj["domain"] != _DRC_DOMAIN:
        raise StageCPrerequisiteAdmissionError("detector DRC domain is not Stage C")
    _require_candidate_status(obj)
    receipt_id = expect_machine_id(obj["receipt_id"], "$.receipt_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    seal = _require_target(obj, context)
    if _time(created_at) <= _time(seal.prompt.created_at):
        raise StageCPrerequisiteAdmissionError("detector DRC must follow its prompt target")
    refs = _parse_ref_map(
        obj["artifacts"],
        expected_media={
            "drc_profile": DETECTOR_DRC_PROFILE_MEDIA_TYPE,
            "detector_ruleset": DETECTOR_RULESET_MEDIA_TYPE,
            "known_fault_fixture": DETECTOR_KNOWN_FAULT_FIXTURE_MEDIA_TYPE,
        },
        path="$.artifacts",
    )
    checks = expect_object(obj["checks"], "$.checks")
    expect_keys(checks, required=set(_DRC_CHECKS), path="$.checks")
    if any(checks[name] != "PASS" for name in _DRC_CHECKS):
        raise StageCPrerequisiteAdmissionError("every closed Stage C DRC check must PASS")
    faults = expect_object(obj["known_fault_validation"], "$.known_fault_validation")
    expect_keys(
        faults,
        required={"fixture_count", "rejected_count", "false_accept_count"},
        path="$.known_fault_validation",
    )
    count = expect_int(faults["fixture_count"], "$.known_fault_validation.fixture_count", minimum=1)
    rejected = expect_int(faults["rejected_count"], "$.known_fault_validation.rejected_count")
    false_accepts = expect_int(faults["false_accept_count"], "$.known_fault_validation.false_accept_count")
    if rejected != count or false_accepts != 0:
        raise StageCPrerequisiteAdmissionError(
            "known-fault DRC fixtures must all reject with zero false accepts"
        )
    _require_fixed_tail(obj)
    bodies = _verify_bodies(refs, artifact_bodies, "detector DRC artifact bodies")
    claims = _claims_by_role(
        bodies,
        ("drc_profile", "detector_ruleset", "known_fault_fixture"),
        seal.target_binding_sha256,
    )
    expected_profile = {
        "profile_status": "RESOLVED",
        "observation_points": "RESOLVED",
        "safety_path": "OBSERVABLE",
    }
    expect_keys(claims["drc_profile"], required=set(expected_profile), path="$drc_profile.claims")
    if claims["drc_profile"] != expected_profile:
        raise StageCPrerequisiteAdmissionError("DRC profile dependency is not resolved")
    expected_rules = {"closed_checks": list(_DRC_CHECKS), "status": "FROZEN"}
    expect_keys(claims["detector_ruleset"], required=set(expected_rules), path="$detector_ruleset.claims")
    if claims["detector_ruleset"] != expected_rules:
        raise StageCPrerequisiteAdmissionError("detector ruleset dependency drifted")
    expected_faults = {
        "fixture_count": count,
        "rejected_count": count,
        "false_accept_count": 0,
    }
    expect_keys(claims["known_fault_fixture"], required=set(expected_faults), path="$known_fault_fixture.claims")
    if claims["known_fault_fixture"] != expected_faults:
        raise StageCPrerequisiteAdmissionError("known-fault dependency differs from outer receipt")
    carrier = StageCDetectorDRCReceiptArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        receipt_id=receipt_id,
        created_at=created_at,
        target_binding_sha256=seal.target_binding_sha256,
        known_fault_count=count,
        artifact_refs=refs,
        artifact_bodies=bodies,
        payload=freeze_json(obj),
    )
    _candidate_unique(seal, carrier.artifact_ref, refs, "detector DRC closure")
    return _register(context, carrier, "DETECTOR_DRC")


@_domain_errors
def load_stagec_frozen_corpus_bundle(
    raw: bytes | bytearray | memoryview,
    *,
    context: StageCPrerequisiteFactoryContext,
    artifact_bodies: tuple[tuple[ArtifactRef, bytes], ...],
) -> StageCFrozenCorpusBundleArtifact:
    """Load the exact 320-group/960-row Stage C corpus candidate."""

    snapshot, obj = _canonical_object(raw, "Stage C frozen corpus bundle")
    expect_keys(
        obj,
        required={
            "schema_version", "bundle_id", "domain", "created_at",
            "candidate_status",
            "target_binding", "artifacts", "counts", "variant_roles",
            "freeze_policy", "authority", "boundary",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_FROZEN_CORPUS_BUNDLE_SCHEMA:
        raise StageCPrerequisiteAdmissionError("wrong Stage C frozen corpus schema")
    if obj["domain"] != _CORPUS_DOMAIN:
        raise StageCPrerequisiteAdmissionError("corpus domain is not Stage C")
    _require_candidate_status(obj)
    bundle_id = expect_machine_id(obj["bundle_id"], "$.bundle_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    seal = _require_target(obj, context)
    if _time(created_at) <= _time(seal.prompt.created_at):
        raise StageCPrerequisiteAdmissionError("corpus candidate must follow its prompt target")
    refs = _parse_ref_map(
        obj["artifacts"],
        expected_media={
            "corpus_rows": CORPUS_ROWS_MEDIA_TYPE,
            "adjudication": CORPUS_ADJUDICATION_MEDIA_TYPE,
            "split_assignment": CORPUS_SPLIT_ASSIGNMENT_MEDIA_TYPE,
            "surface_bundle": CORPUS_SURFACE_BUNDLE_MEDIA_TYPE,
        },
        path="$.artifacts",
    )
    counts = expect_object(obj["counts"], "$.counts")
    expect_keys(
        counts,
        required={
            "group_count", "row_count", "variant_count",
            "c_cal_groups", "c_cal_rows", "confirmatory_groups",
            "confirmatory_rows", "heldout_groups", "heldout_rows",
        },
        path="$.counts",
    )
    expected_counts = {
        "group_count": 320,
        "row_count": 960,
        "variant_count": 3,
        "c_cal_groups": DIAGNOSTIC_GROUP_COUNT,
        "c_cal_rows": DIAGNOSTIC_CASE_COUNT,
        "confirmatory_groups": 80,
        "confirmatory_rows": 240,
        "heldout_groups": 80,
        "heldout_rows": 240,
    }
    for name, expected in expected_counts.items():
        if expect_int(counts[name], f"$.counts.{name}") != expected:
            raise StageCPrerequisiteAdmissionError(
                f"$.counts.{name} must equal {expected}; adjacent corpora cannot coerce"
            )
    roles = obj["variant_roles"]
    if type(roles) is not list or roles != list(DIAGNOSTIC_VARIANT_ROLES):
        raise StageCPrerequisiteAdmissionError("corpus must freeze the exact three variant roles")
    policy = expect_object(obj["freeze_policy"], "$.freeze_policy")
    expected_policy = {
        "group_assignment": "DISJOINT_WHOLE_BASE_INTENT_GROUPS",
        "allocation": "FROZEN_BEFORE_PREREGISTRATION",
        "row_mutation": "FORBIDDEN",
        "split_overlap": "ZERO",
    }
    expect_keys(policy, required=set(expected_policy), path="$.freeze_policy")
    if policy != expected_policy:
        raise StageCPrerequisiteAdmissionError("corpus disjoint/frozen policy drifted")
    _require_fixed_tail(obj)
    bodies = _verify_bodies(refs, artifact_bodies, "frozen corpus artifact bodies")
    claims = _claims_by_role(
        bodies,
        ("corpus_rows", "adjudication", "split_assignment", "surface_bundle"),
        seal.target_binding_sha256,
    )
    rows_claims = claims["corpus_rows"]
    expect_keys(
        rows_claims,
        required={"group_count", "row_count", "variant_count", "ordered_rows_sha256"},
        path="$corpus_rows.claims",
    )
    if (
        rows_claims["group_count"] != 320
        or rows_claims["row_count"] != 960
        or rows_claims["variant_count"] != 3
    ):
        raise StageCPrerequisiteAdmissionError("corpus rows manifest is not 320/960/3")
    expect_sha256(rows_claims["ordered_rows_sha256"], "$corpus_rows.claims.ordered_rows_sha256")
    adjudication_claims = claims["adjudication"]
    expect_keys(
        adjudication_claims,
        required={"row_count", "status", "adjudication_sha256"},
        path="$adjudication.claims",
    )
    if adjudication_claims["row_count"] != 960 or adjudication_claims["status"] != "FROZEN":
        raise StageCPrerequisiteAdmissionError("corpus adjudication dependency is not frozen for 960 rows")
    expect_sha256(adjudication_claims["adjudication_sha256"], "$adjudication.claims.adjudication_sha256")
    split_claims = claims["split_assignment"]
    expected_split_claims = {
        "group_count": 320,
        "row_count": 960,
        "c_cal_groups": 160,
        "c_cal_rows": 480,
        "confirmatory_groups": 80,
        "confirmatory_rows": 240,
        "heldout_groups": 80,
        "heldout_rows": 240,
        **expected_policy,
    }
    expect_keys(split_claims, required=set(expected_split_claims), path="$split_assignment.claims")
    if split_claims != expected_split_claims:
        raise StageCPrerequisiteAdmissionError("corpus split dependency is not exact/disjoint/frozen")
    surface_claims = claims["surface_bundle"]
    expected_surface_claims = {
        "group_count": 320,
        "row_count": 960,
        "variant_count": 3,
        "variant_roles": list(DIAGNOSTIC_VARIANT_ROLES),
    }
    expect_keys(surface_claims, required=set(expected_surface_claims), path="$surface_bundle.claims")
    if surface_claims != expected_surface_claims:
        raise StageCPrerequisiteAdmissionError("corpus surface dependency is not exact 3-variant Stage C")
    carrier = StageCFrozenCorpusBundleArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        bundle_id=bundle_id,
        created_at=created_at,
        target_binding_sha256=seal.target_binding_sha256,
        artifact_refs=refs,
        artifact_bodies=bodies,
        payload=freeze_json(obj),
    )
    _candidate_unique(seal, carrier.artifact_ref, refs, "frozen corpus closure")
    return _register(context, carrier, "FROZEN_CORPUS")


def _fresh_corpus(
    context: StageCPrerequisiteFactoryContext,
    corpus: StageCFrozenCorpusBundleArtifact,
) -> StageCFrozenCorpusBundleArtifact:
    _require_origin(context, corpus, "FROZEN_CORPUS")
    if type(corpus) is not StageCFrozenCorpusBundleArtifact:
        raise StageCPrerequisiteAdmissionError("corpus carrier has the wrong exact type")
    fresh = load_stagec_frozen_corpus_bundle(
        corpus.raw_bytes, context=context, artifact_bodies=corpus.artifact_bodies
    )
    if fresh != corpus:
        raise StageCPrerequisiteAdmissionError("corpus carrier differs from fresh replay")
    return fresh


@_domain_errors
def load_stagec_trusted_storage_receipt(
    raw: bytes | bytearray | memoryview,
    *,
    context: StageCPrerequisiteFactoryContext,
    corpus: StageCFrozenCorpusBundleArtifact,
    artifact_bodies: tuple[tuple[ArtifactRef, bytes], ...],
) -> StageCTrustedStorageReceiptArtifact:
    """Load a Stage-C corpus Object Lock/readback/trusted-time candidate."""

    corpus = _fresh_corpus(context, corpus)
    snapshot, obj = _canonical_object(raw, "Stage C trusted storage receipt")
    expect_keys(
        obj,
        required={
            "schema_version", "receipt_id", "domain", "created_at",
            "candidate_status",
            "target_binding", "corpus_subject", "artifacts", "object_lock",
            "readback", "trusted_time", "verification", "authority", "boundary",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_TRUSTED_STORAGE_RECEIPT_SCHEMA:
        raise StageCPrerequisiteAdmissionError("wrong Stage C trusted-storage schema")
    if obj["domain"] != _STORAGE_DOMAIN:
        raise StageCPrerequisiteAdmissionError("storage receipt domain is not Stage C corpus storage")
    _require_candidate_status(obj)
    receipt_id = expect_machine_id(obj["receipt_id"], "$.receipt_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    seal = _require_target(obj, context)
    if _time(created_at) <= _time(corpus.created_at):
        raise StageCPrerequisiteAdmissionError("storage receipt must follow the corpus candidate")
    refs = _parse_ref_map(
        obj["artifacts"],
        expected_media={
            "object_lock_receipt": OBJECT_LOCK_RECEIPT_MEDIA_TYPE,
            "readback_receipt": OBJECT_READBACK_RECEIPT_MEDIA_TYPE,
            "trusted_time_receipt": TRUSTED_TIME_RECEIPT_MEDIA_TYPE,
            "verifier_identity": STORAGE_VERIFIER_IDENTITY_MEDIA_TYPE,
        },
        path="$.artifacts",
    )
    subject = expect_object(obj["corpus_subject"], "$.corpus_subject")
    expect_keys(
        subject,
        required={
            "subject_kind", "corpus_bundle", "object_version_id",
            "checksum_sha256", "byte_length",
        },
        path="$.corpus_subject",
    )
    if subject["subject_kind"] != "STAGE_C_FROZEN_CORPUS_BUNDLE":
        raise StageCPrerequisiteAdmissionError("storage subject is not the Stage C corpus")
    corpus_ref = parse_artifact_ref(subject["corpus_bundle"], "$.corpus_subject.corpus_bundle")
    if corpus_ref != corpus.artifact_ref or not corpus_ref.verify_bytes(corpus.raw_bytes):
        raise StageCPrerequisiteAdmissionError("storage receipt binds a different corpus bundle")
    version = expect_string(subject["object_version_id"], "$.corpus_subject.object_version_id", maximum=256)
    if expect_sha256(subject["checksum_sha256"], "$.corpus_subject.checksum_sha256") != corpus.sha256:
        raise StageCPrerequisiteAdmissionError("storage subject checksum differs from corpus bytes")
    if expect_int(subject["byte_length"], "$.corpus_subject.byte_length", minimum=1) != corpus.byte_length:
        raise StageCPrerequisiteAdmissionError("storage subject byte length differs from corpus bytes")
    lock = expect_object(obj["object_lock"], "$.object_lock")
    expect_keys(lock, required={"mode", "status", "object_version_id", "retention_until"}, path="$.object_lock")
    retention = expect_timestamp(lock["retention_until"], "$.object_lock.retention_until")
    if lock != {
        "mode": "COMPLIANCE",
        "status": "LOCKED",
        "object_version_id": version,
        "retention_until": retention,
    }:
        raise StageCPrerequisiteAdmissionError("Object Lock claim is not exact COMPLIANCE/LOCKED")
    readback = expect_object(obj["readback"], "$.readback")
    expect_keys(readback, required={"status", "object_version_id", "checksum_sha256"}, path="$.readback")
    if readback != {"status": "PASS", "object_version_id": version, "checksum_sha256": corpus.sha256}:
        raise StageCPrerequisiteAdmissionError("storage readback does not match the exact corpus version/checksum")
    trusted = expect_object(obj["trusted_time"], "$.trusted_time")
    expect_keys(trusted, required={"status", "verified_at"}, path="$.trusted_time")
    verified_at = expect_timestamp(trusted["verified_at"], "$.trusted_time.verified_at")
    if trusted["status"] != "PASS":
        raise StageCPrerequisiteAdmissionError("trusted-time verification must PASS")
    verification = expect_object(obj["verification"], "$.verification")
    expect_keys(verification, required={"status"}, path="$.verification")
    if verification["status"] != "PASS":
        raise StageCPrerequisiteAdmissionError("storage verifier must PASS")
    if not (
        _time(corpus.created_at)
        < _time(verified_at)
        <= _time(created_at)
        < _time(retention)
    ):
        raise StageCPrerequisiteAdmissionError("storage retention is expired or time ordering is invalid")
    _require_fixed_tail(obj)
    bodies = _verify_bodies(refs, artifact_bodies, "trusted storage artifact bodies")
    claims = _claims_by_role(
        bodies,
        (
            "object_lock_receipt", "readback_receipt",
            "trusted_time_receipt", "verifier_identity",
        ),
        seal.target_binding_sha256,
    )
    object_claims = claims["object_lock_receipt"]
    expected_object_claims = {
        "corpus_bundle": _ref_value(corpus.artifact_ref),
        "object_version_id": version,
        "checksum_sha256": corpus.sha256,
        "byte_length": corpus.byte_length,
        "mode": "COMPLIANCE",
        "status": "LOCKED",
        "retention_until": retention,
    }
    expect_keys(object_claims, required=set(expected_object_claims), path="$object_lock_receipt.claims")
    if object_claims != expected_object_claims:
        raise StageCPrerequisiteAdmissionError("Object Lock dependency differs from the exact corpus subject")
    readback_claims = claims["readback_receipt"]
    expected_readback_claims = {
        "corpus_bundle": _ref_value(corpus.artifact_ref),
        "object_version_id": version,
        "checksum_sha256": corpus.sha256,
        "byte_length": corpus.byte_length,
        "status": "PASS",
    }
    expect_keys(readback_claims, required=set(expected_readback_claims), path="$readback_receipt.claims")
    if readback_claims != expected_readback_claims:
        raise StageCPrerequisiteAdmissionError("readback dependency differs from the exact corpus subject")
    time_claims = claims["trusted_time_receipt"]
    expected_time_claims = {
        "object_version_id": version,
        "checksum_sha256": corpus.sha256,
        "verified_at": verified_at,
        "status": "PASS",
    }
    expect_keys(time_claims, required=set(expected_time_claims), path="$trusted_time_receipt.claims")
    if time_claims != expected_time_claims:
        raise StageCPrerequisiteAdmissionError("trusted-time dependency differs from storage receipt")
    verifier_claims = claims["verifier_identity"]
    expect_keys(
        verifier_claims,
        required={"verifier_id", "object_version_id", "checksum_sha256", "status"},
        path="$verifier_identity.claims",
    )
    expect_machine_id(verifier_claims["verifier_id"], "$verifier_identity.claims.verifier_id")
    if (
        verifier_claims["object_version_id"] != version
        or verifier_claims["checksum_sha256"] != corpus.sha256
        or verifier_claims["status"] != "PASS"
    ):
        raise StageCPrerequisiteAdmissionError("storage verifier dependency differs from storage receipt")
    carrier = StageCTrustedStorageReceiptArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        receipt_id=receipt_id,
        created_at=created_at,
        target_binding_sha256=seal.target_binding_sha256,
        object_version_id=version,
        retention_until=retention,
        verified_at=verified_at,
        corpus_bundle=corpus_ref,
        artifact_refs=refs,
        artifact_bodies=bodies,
        payload=freeze_json(obj),
    )
    _candidate_unique(
        seal, carrier.artifact_ref, (corpus.artifact_ref, *refs), "trusted storage closure"
    )
    return _register(context, carrier, "TRUSTED_STORAGE")


def _fresh_drc(
    context: StageCPrerequisiteFactoryContext,
    drc: StageCDetectorDRCReceiptArtifact,
) -> StageCDetectorDRCReceiptArtifact:
    _require_origin(context, drc, "DETECTOR_DRC")
    if type(drc) is not StageCDetectorDRCReceiptArtifact:
        raise StageCPrerequisiteAdmissionError("detector DRC carrier has the wrong exact type")
    fresh = load_stagec_detector_drc_receipt(
        drc.raw_bytes, context=context, artifact_bodies=drc.artifact_bodies
    )
    if fresh != drc:
        raise StageCPrerequisiteAdmissionError("detector DRC carrier differs from fresh replay")
    return fresh


def _fresh_storage(
    context: StageCPrerequisiteFactoryContext,
    storage: StageCTrustedStorageReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
) -> StageCTrustedStorageReceiptArtifact:
    _require_origin(context, storage, "TRUSTED_STORAGE")
    if type(storage) is not StageCTrustedStorageReceiptArtifact:
        raise StageCPrerequisiteAdmissionError("trusted-storage carrier has the wrong exact type")
    fresh = load_stagec_trusted_storage_receipt(
        storage.raw_bytes,
        context=context,
        corpus=corpus,
        artifact_bodies=storage.artifact_bodies,
    )
    if fresh != storage:
        raise StageCPrerequisiteAdmissionError("trusted-storage carrier differs from fresh replay")
    return fresh


@_domain_errors
def derive_stagec_prospective_subject_sha256(
    *,
    context: StageCPrerequisiteFactoryContext,
    detector_drc: StageCDetectorDRCReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
    trusted_storage: StageCTrustedStorageReceiptArtifact,
) -> str:
    """Derive the pre-authorization subject; no authorization ref participates."""

    drc = _fresh_drc(context, detector_drc)
    frozen_corpus = _fresh_corpus(context, corpus)
    storage = _fresh_storage(context, trusted_storage, frozen_corpus)
    return canonical_sha256(
        {
            "domain": STAGEC_PROSPECTIVE_SUBJECT_DOMAIN,
            "target_binding_sha256": context.target_binding_sha256,
            "detector_drc": _ref_value(drc.artifact_ref),
            "frozen_corpus": _ref_value(frozen_corpus.artifact_ref),
            "trusted_storage": _ref_value(storage.artifact_ref),
        }
    )


@_domain_errors
def load_stagec_execution_authorization(
    raw: bytes | bytearray | memoryview,
    *,
    context: StageCPrerequisiteFactoryContext,
    detector_drc: StageCDetectorDRCReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
    trusted_storage: StageCTrustedStorageReceiptArtifact,
    artifact_bodies: tuple[tuple[ArtifactRef, bytes], ...],
) -> StageCExecutionAuthorizationArtifact:
    """Load an unconsumed, zero-spend/network/provider Stage C authorization candidate."""

    drc = _fresh_drc(context, detector_drc)
    frozen_corpus = _fresh_corpus(context, corpus)
    storage = _fresh_storage(context, trusted_storage, frozen_corpus)
    subject_sha = canonical_sha256(
        {
            "domain": STAGEC_PROSPECTIVE_SUBJECT_DOMAIN,
            "target_binding_sha256": context.target_binding_sha256,
            "detector_drc": _ref_value(drc.artifact_ref),
            "frozen_corpus": _ref_value(frozen_corpus.artifact_ref),
            "trusted_storage": _ref_value(storage.artifact_ref),
        }
    )
    snapshot, obj = _canonical_object(raw, "Stage C execution authorization candidate")
    expect_keys(
        obj,
        required={
            "schema_version", "authorization_id", "domain", "created_at",
            "candidate_status",
            "target_binding", "prospective_subject_sha256", "artifacts",
            "scope", "coverage_window", "nonce", "authority", "boundary",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_EXECUTION_AUTHORIZATION_SCHEMA:
        raise StageCPrerequisiteAdmissionError("wrong Stage C authorization-candidate schema")
    if obj["domain"] != _AUTHORIZATION_DOMAIN:
        raise StageCPrerequisiteAdmissionError("authorization domain is not Stage C C-Cal")
    _require_candidate_status(obj)
    authorization_id = expect_machine_id(obj["authorization_id"], "$.authorization_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    seal = _require_target(obj, context)
    if _time(created_at) <= max(
        _time(drc.created_at), _time(frozen_corpus.created_at), _time(storage.created_at)
    ):
        raise StageCPrerequisiteAdmissionError("authorization must follow all subject candidates")
    if expect_sha256(obj["prospective_subject_sha256"], "$.prospective_subject_sha256") != subject_sha:
        raise StageCPrerequisiteAdmissionError("authorization binds a different prospective subject")
    refs = _parse_ref_map(
        obj["artifacts"],
        expected_media={"authorization_instrument": AUTHORIZATION_INSTRUMENT_MEDIA_TYPE},
        path="$.artifacts",
    )
    scope = expect_object(obj["scope"], "$.scope")
    expected_scope = {
        "study_phase": "DIAGNOSTIC_CALIBRATION",
        "split_id": seal.split.split_id,
        "phase_submission_count": 1,
        "corpus_evaluation_count": DIAGNOSTIC_CASE_COUNT,
        "attempts_per_case": 1,
        "total_attempt_count": DIAGNOSTIC_CASE_COUNT,
        "canary_count": 0,
        "retry_count": 0,
        "replacement_count": 0,
        "generation_count": 0,
        "intervention_count": 0,
        "provider_call_count": 0,
        "maximum_spend_usd": "$0.00",
        "network": "NONE",
    }
    expect_keys(scope, required=set(expected_scope), path="$.scope")
    if scope != expected_scope:
        raise StageCPrerequisiteAdmissionError(
            "authorization scope must be one C-Cal submission, 480 evaluations, "
            "one attempt per case, and zero side effects"
        )
    window = expect_object(obj["coverage_window"], "$.coverage_window")
    expect_keys(window, required={"window_start", "window_end"}, path="$.coverage_window")
    window_start = expect_timestamp(window["window_start"], "$.coverage_window.window_start")
    window_end = expect_timestamp(window["window_end"], "$.coverage_window.window_end")
    if not (_time(created_at) < _time(window_start) < _time(window_end)):
        raise StageCPrerequisiteAdmissionError("authorization coverage window is not prospective")
    nonce = expect_object(obj["nonce"], "$.nonce")
    expect_keys(nonce, required={"nonce_b64url", "state", "consumed_at"}, path="$.nonce")
    nonce_text = expect_string(nonce["nonce_b64url"], "$.nonce.nonce_b64url", maximum=43)
    if not _NONCE_RE.fullmatch(nonce_text):
        raise StageCPrerequisiteAdmissionError("authorization nonce must be canonical 32-byte base64url")
    try:
        nonce_bytes = base64.urlsafe_b64decode(nonce_text + "=")
    except (ValueError, TypeError) as exc:
        raise StageCPrerequisiteAdmissionError("authorization nonce is invalid base64url") from exc
    if len(nonce_bytes) != 32 or not any(nonce_bytes):
        raise StageCPrerequisiteAdmissionError("authorization nonce must be nonzero exact 32 bytes")
    canonical_nonce = base64.urlsafe_b64encode(nonce_bytes).rstrip(b"=").decode("ascii")
    if canonical_nonce != nonce_text:
        raise StageCPrerequisiteAdmissionError("authorization nonce has noncanonical base64url pad bits")
    if nonce["state"] != "UNCONSUMED" or nonce["consumed_at"] is not None:
        raise StageCPrerequisiteAdmissionError("authorization nonce/state must remain UNCONSUMED")
    if _time(storage.retention_until) <= _time(window_end):
        raise StageCPrerequisiteAdmissionError("trusted storage retention does not cover authorization window")
    _require_fixed_tail(obj)
    bodies = _verify_bodies(refs, artifact_bodies, "authorization artifact bodies")
    claims = _claims_by_role(
        bodies,
        ("authorization_instrument",),
        seal.target_binding_sha256,
    )["authorization_instrument"]
    expected_claims = {
        "prospective_subject_sha256": subject_sha,
        "scope": expected_scope,
        "coverage_window": {
            "window_start": window_start,
            "window_end": window_end,
        },
        "nonce": {
            "nonce_b64url": nonce_text,
            "state": "UNCONSUMED",
            "consumed_at": None,
        },
    }
    expect_keys(claims, required=set(expected_claims), path="$authorization_instrument.claims")
    if claims != expected_claims:
        raise StageCPrerequisiteAdmissionError(
            "authorization instrument dependency differs from subject/scope/window/nonce"
        )
    carrier = StageCExecutionAuthorizationArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        authorization_id=authorization_id,
        created_at=created_at,
        target_binding_sha256=seal.target_binding_sha256,
        prospective_subject_sha256=subject_sha,
        window_start=window_start,
        window_end=window_end,
        nonce_b64url=nonce_text,
        state="UNCONSUMED",
        artifact_refs=refs,
        artifact_bodies=bodies,
        payload=freeze_json(obj),
    )
    _candidate_unique(
        seal,
        carrier.artifact_ref,
        (drc.artifact_ref, frozen_corpus.artifact_ref, storage.artifact_ref, *refs),
        "authorization closure",
    )
    return _register(context, carrier, "EXECUTION_AUTHORIZATION")


def _fresh_authorization(
    context: StageCPrerequisiteFactoryContext,
    authorization: StageCExecutionAuthorizationArtifact,
    drc: StageCDetectorDRCReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
    storage: StageCTrustedStorageReceiptArtifact,
) -> StageCExecutionAuthorizationArtifact:
    _require_origin(context, authorization, "EXECUTION_AUTHORIZATION")
    if type(authorization) is not StageCExecutionAuthorizationArtifact:
        raise StageCPrerequisiteAdmissionError("authorization carrier has the wrong exact type")
    fresh = load_stagec_execution_authorization(
        authorization.raw_bytes,
        context=context,
        detector_drc=drc,
        corpus=corpus,
        trusted_storage=storage,
        artifact_bodies=authorization.artifact_bodies,
    )
    if fresh != authorization:
        raise StageCPrerequisiteAdmissionError("authorization carrier differs from fresh replay")
    return fresh


def _fresh_candidates(
    context: StageCPrerequisiteFactoryContext,
    detector_drc: StageCDetectorDRCReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
    trusted_storage: StageCTrustedStorageReceiptArtifact,
    authorization: StageCExecutionAuthorizationArtifact,
) -> tuple[
    StageCDetectorDRCReceiptArtifact,
    StageCFrozenCorpusBundleArtifact,
    StageCTrustedStorageReceiptArtifact,
    StageCExecutionAuthorizationArtifact,
]:
    drc = _fresh_drc(context, detector_drc)
    frozen_corpus = _fresh_corpus(context, corpus)
    storage = _fresh_storage(context, trusted_storage, frozen_corpus)
    auth = _fresh_authorization(
        context, authorization, drc, frozen_corpus, storage
    )
    return drc, frozen_corpus, storage, auth


def _candidate_refs_value(
    drc: StageCDetectorDRCReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
    storage: StageCTrustedStorageReceiptArtifact,
    authorization: StageCExecutionAuthorizationArtifact,
) -> dict[str, Any]:
    return {
        "detector_drc": _ref_value(drc.artifact_ref),
        "frozen_corpus": _ref_value(corpus.artifact_ref),
        "trusted_storage": _ref_value(storage.artifact_ref),
        "execution_authorization": _ref_value(authorization.artifact_ref),
    }


def _primary_candidate_refs(
    drc: StageCDetectorDRCReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
    storage: StageCTrustedStorageReceiptArtifact,
    authorization: StageCExecutionAuthorizationArtifact,
) -> tuple[ArtifactRef, ...]:
    return (
        drc.artifact_ref,
        corpus.artifact_ref,
        storage.artifact_ref,
        authorization.artifact_ref,
    )


def _prospective_subject_from_refs(
    context: StageCPrerequisiteFactoryContext,
    detector_drc: ArtifactRef,
    corpus: ArtifactRef,
    trusted_storage: ArtifactRef,
) -> str:
    return canonical_sha256(
        {
            "domain": STAGEC_PROSPECTIVE_SUBJECT_DOMAIN,
            "target_binding_sha256": context.target_binding_sha256,
            "detector_drc": _ref_value(detector_drc),
            "frozen_corpus": _ref_value(corpus),
            "trusted_storage": _ref_value(trusted_storage),
        }
    )


def _global_closure_refs(
    seal: _ContextSeal,
    drc: StageCDetectorDRCReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
    storage: StageCTrustedStorageReceiptArtifact,
    authorization: StageCExecutionAuthorizationArtifact,
    intake: StageCPrerequisiteIntakeArtifact | None = None,
) -> tuple[ArtifactRef, ...]:
    refs = (
        seal.prompt.artifact_ref,
        *_prompt_dependency_refs(seal),
        drc.artifact_ref,
        *drc.artifact_refs,
        corpus.artifact_ref,
        *corpus.artifact_refs,
        storage.artifact_ref,
        *storage.artifact_refs,
        authorization.artifact_ref,
        *authorization.artifact_refs,
        *((intake.artifact_ref,) if intake is not None else ()),
    )
    _unique_refs(refs, "global Stage C prerequisite closure")
    return refs


@_domain_errors
def load_stagec_prerequisite_intake(
    raw: bytes | bytearray | memoryview,
    *,
    context: StageCPrerequisiteFactoryContext,
) -> StageCPrerequisiteIntakeArtifact:
    """Record only the owner's assertion; candidate bodies are not replayed here."""

    snapshot, obj = _canonical_object(raw, "Stage C prerequisite owner intake")
    expect_keys(
        obj,
        required={
            "schema_version", "intake_id", "domain", "created_at",
            "target_binding", "prospective_subject_sha256", "candidates",
            "owner_assertion", "authority", "boundary",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_PREREQUISITE_INTAKE_SCHEMA:
        raise StageCPrerequisiteAdmissionError("wrong Stage C owner-intake schema")
    if obj["domain"] != "STAGE_C_PREREQUISITE_OWNER_ASSERTION":
        raise StageCPrerequisiteAdmissionError("owner intake has the wrong domain")
    intake_id = expect_machine_id(obj["intake_id"], "$.intake_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    seal = _require_target(obj, context)
    if _time(created_at) <= _time(seal.prompt.created_at):
        raise StageCPrerequisiteAdmissionError("owner intake must follow its prompt target")
    candidate_refs = _parse_ref_map(
        obj["candidates"],
        expected_media={
            "detector_drc": STAGEC_DETECTOR_DRC_RECEIPT_MEDIA_TYPE,
            "frozen_corpus": STAGEC_FROZEN_CORPUS_BUNDLE_MEDIA_TYPE,
            "trusted_storage": STAGEC_TRUSTED_STORAGE_RECEIPT_MEDIA_TYPE,
            "execution_authorization": STAGEC_EXECUTION_AUTHORIZATION_MEDIA_TYPE,
        },
        path="$.candidates",
    )
    subject_sha = _prospective_subject_from_refs(
        context, candidate_refs[0], candidate_refs[1], candidate_refs[2]
    )
    supplied_subject = expect_sha256(
        obj["prospective_subject_sha256"], "$.prospective_subject_sha256"
    )
    if supplied_subject != subject_sha:
        raise StageCPrerequisiteAdmissionError("owner intake binds a different prospective subject")
    assertion = expect_object(obj["owner_assertion"], "$.owner_assertion")
    expected_assertion = {
        "availability": OWNER_ASSERTS_PRESENT,
        "intake_action": NOT_PERFORMED_BY_INTAKE,
    }
    expect_keys(assertion, required=set(expected_assertion), path="$.owner_assertion")
    if assertion != expected_assertion:
        raise StageCPrerequisiteAdmissionError("owner assertion semantics drifted")
    _require_fixed_tail(obj)
    carrier = StageCPrerequisiteIntakeArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        intake_id=intake_id,
        created_at=created_at,
        target_binding_sha256=seal.target_binding_sha256,
        prospective_subject_sha256=subject_sha,
        candidate_refs=candidate_refs,
        payload=freeze_json(obj),
    )
    _unique_refs(
        (
            seal.prompt.artifact_ref,
            *_prompt_dependency_refs(seal),
            *candidate_refs,
            carrier.artifact_ref,
        ),
        "owner intake asserted-ref closure",
    )
    return _register(context, carrier, "OWNER_INTAKE")


def _fresh_intake(
    context: StageCPrerequisiteFactoryContext,
    intake: StageCPrerequisiteIntakeArtifact,
) -> StageCPrerequisiteIntakeArtifact:
    _require_origin(context, intake, "OWNER_INTAKE")
    if type(intake) is not StageCPrerequisiteIntakeArtifact:
        raise StageCPrerequisiteAdmissionError("owner-intake carrier has the wrong exact type")
    fresh = load_stagec_prerequisite_intake(
        intake.raw_bytes,
        context=context,
    )
    if fresh != intake:
        raise StageCPrerequisiteAdmissionError("owner-intake carrier differs from fresh replay")
    return fresh


def _closure_sha256(refs: tuple[ArtifactRef, ...]) -> str:
    return canonical_sha256(
        {
            "domain": STAGEC_PREREQUISITE_CLOSURE_DOMAIN,
            "ordered_artifacts": [_ref_value(reference) for reference in refs],
        }
    )


@_domain_errors
def load_stagec_prerequisite_admission(
    raw: bytes | bytearray | memoryview,
    *,
    context: StageCPrerequisiteFactoryContext,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...],
    detector_drc: StageCDetectorDRCReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
    trusted_storage: StageCTrustedStorageReceiptArtifact,
    authorization: StageCExecutionAuthorizationArtifact,
    intake: StageCPrerequisiteIntakeArtifact,
) -> StageCPrerequisiteAdmissionArtifact:
    """Fully replay and admit all four candidates only as future base inputs."""

    snapshot, obj = _canonical_object(raw, "Stage C prerequisite admission")
    expect_keys(
        obj,
        required={
            "schema_version", "admission_id", "domain", "created_at", "decision",
            "target_binding", "prospective_subject_sha256", "split_inventory",
            "prompt_context_inventory", "candidates", "owner_intake",
            "artifact_closure", "authority", "boundary",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_PREREQUISITE_ADMISSION_SCHEMA:
        raise StageCPrerequisiteAdmissionError("wrong Stage C prerequisite-admission schema")
    if obj["domain"] != "STAGE_C_PREREQUISITE_ADMISSION":
        raise StageCPrerequisiteAdmissionError("prerequisite admission has the wrong domain")
    admission_id = expect_machine_id(obj["admission_id"], "$.admission_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    if obj["decision"] != ADMITTED_FOR_PROSPECTIVE_PREREGISTRATION_ONLY:
        raise StageCPrerequisiteAdmissionError("the only admission decision is prospective-only")
    _require_fixed_tail(obj)
    seal = _require_target(obj, context)
    _require_context(context, replay_bundles=replay_bundles)
    drc, frozen_corpus, storage, auth = _fresh_candidates(
        context, detector_drc, corpus, trusted_storage, authorization
    )
    fresh_intake = _fresh_intake(context, intake)
    expected_candidate_refs = _primary_candidate_refs(
        drc, frozen_corpus, storage, auth
    )
    if fresh_intake.candidate_refs != expected_candidate_refs:
        raise StageCPrerequisiteAdmissionError(
            "owner intake asserted refs differ from the four replayed candidates"
        )
    if fresh_intake.prospective_subject_sha256 != auth.prospective_subject_sha256:
        raise StageCPrerequisiteAdmissionError(
            "owner intake prospective subject differs from replayed authorization"
        )
    if any(
        _time(item.created_at) >= _time(fresh_intake.created_at)
        for item in (drc, frozen_corpus, storage, auth)
    ):
        raise StageCPrerequisiteAdmissionError(
            "all four replayed candidates must predate the owner assertion"
        )
    if _time(created_at) <= _time(fresh_intake.created_at):
        raise StageCPrerequisiteAdmissionError("admission must follow the owner intake")
    if _time(created_at) >= _time(auth.window_start):
        raise StageCPrerequisiteAdmissionError("admission must precede the authorization window")
    if expect_sha256(obj["prospective_subject_sha256"], "$.prospective_subject_sha256") != auth.prospective_subject_sha256:
        raise StageCPrerequisiteAdmissionError("admission binds a different prospective subject")
    split_ref = parse_artifact_ref(obj["split_inventory"], "$.split_inventory")
    prompt_ref = parse_artifact_ref(obj["prompt_context_inventory"], "$.prompt_context_inventory")
    if (
        split_ref != seal.split.artifact_ref
        or split_ref.media_type != DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE
        or not split_ref.verify_bytes(seal.split.raw_bytes)
        or prompt_ref != seal.prompt.artifact_ref
        or prompt_ref.media_type != STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE
        or not prompt_ref.verify_bytes(seal.prompt.raw_bytes)
    ):
        raise StageCPrerequisiteAdmissionError("admission split/prompt target differs from full replay")
    candidate_refs = _parse_ref_map(
        obj["candidates"],
        expected_media={
            "detector_drc": STAGEC_DETECTOR_DRC_RECEIPT_MEDIA_TYPE,
            "frozen_corpus": STAGEC_FROZEN_CORPUS_BUNDLE_MEDIA_TYPE,
            "trusted_storage": STAGEC_TRUSTED_STORAGE_RECEIPT_MEDIA_TYPE,
            "execution_authorization": STAGEC_EXECUTION_AUTHORIZATION_MEDIA_TYPE,
        },
        path="$.candidates",
    )
    if candidate_refs != _primary_candidate_refs(drc, frozen_corpus, storage, auth):
        raise StageCPrerequisiteAdmissionError("admission is incomplete or swaps candidate roles")
    intake_ref = parse_artifact_ref(obj["owner_intake"], "$.owner_intake")
    if (
        intake_ref != fresh_intake.artifact_ref
        or intake_ref.media_type != STAGEC_PREREQUISITE_INTAKE_MEDIA_TYPE
        or not intake_ref.verify_bytes(fresh_intake.raw_bytes)
    ):
        raise StageCPrerequisiteAdmissionError("admission binds a different owner intake")
    closure_refs = _global_closure_refs(
        seal, drc, frozen_corpus, storage, auth, fresh_intake
    )
    closure = expect_object(obj["artifact_closure"], "$.artifact_closure")
    expect_keys(closure, required={"artifact_count", "sha256"}, path="$.artifact_closure")
    closure_sha = _closure_sha256(closure_refs)
    if (
        expect_int(closure["artifact_count"], "$.artifact_closure.artifact_count", minimum=1)
        != len(closure_refs)
        or expect_sha256(closure["sha256"], "$.artifact_closure.sha256") != closure_sha
    ):
        raise StageCPrerequisiteAdmissionError("admission artifact closure differs from fresh replay")
    carrier = StageCPrerequisiteAdmissionArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        admission_id=admission_id,
        created_at=created_at,
        decision=ADMITTED_FOR_PROSPECTIVE_PREREGISTRATION_ONLY,
        target_binding_sha256=seal.target_binding_sha256,
        prospective_subject_sha256=auth.prospective_subject_sha256,
        artifact_closure_sha256=closure_sha,
        artifact_refs=closure_refs,
        payload=freeze_json(obj),
    )
    _unique_refs((*closure_refs, carrier.artifact_ref), "admission global closure")
    with _SEALS_LOCK:
        existing = seal.suite
        if existing is not None:
            same_suite = (
                existing[0].artifact_ref == drc.artifact_ref
                and existing[1].artifact_ref == frozen_corpus.artifact_ref
                and existing[2].artifact_ref == storage.artifact_ref
                and existing[3].artifact_ref == auth.artifact_ref
                and existing[4].artifact_ref == fresh_intake.artifact_ref
                and existing[5] == carrier
            )
            if not same_suite:
                raise StageCPrerequisiteAdmissionError(
                    "sealed target already has a different create-once admission"
                )
        # Conflict check, process-origin registration, and suite publication are
        # one create-once critical section.  A rejected contender never enters
        # the origin registry and cannot overwrite the winning suite.
        seal.origins[id(carrier)] = (carrier, "PREREQUISITE_ADMISSION")
        seal.suite = (drc, frozen_corpus, storage, auth, fresh_intake, carrier)
    return carrier


@_domain_errors
def replay_stagec_prerequisite_admission_projection(
    admission: StageCPrerequisiteAdmissionArtifact,
    *,
    context: StageCPrerequisiteFactoryContext,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...],
    detector_drc: StageCDetectorDRCReceiptArtifact,
    corpus: StageCFrozenCorpusBundleArtifact,
    trusted_storage: StageCTrustedStorageReceiptArtifact,
    authorization: StageCExecutionAuthorizationArtifact,
    intake: StageCPrerequisiteIntakeArtifact,
) -> StageCPrerequisiteAdmissionArtifact:
    """Reject dataclass replacement and return a fresh full admission replay."""

    _require_origin(context, admission, "PREREQUISITE_ADMISSION")
    if type(admission) is not StageCPrerequisiteAdmissionArtifact:
        raise StageCPrerequisiteAdmissionError("admission carrier has the wrong exact type")
    fresh = load_stagec_prerequisite_admission(
        admission.raw_bytes,
        context=context,
        replay_bundles=replay_bundles,
        detector_drc=detector_drc,
        corpus=corpus,
        trusted_storage=trusted_storage,
        authorization=authorization,
        intake=intake,
    )
    if fresh != admission:
        raise StageCPrerequisiteAdmissionError("admission carrier differs from fresh replay")
    return fresh


@_domain_errors
def require_stagec_prerequisite_admission_in_preregistration(
    context: StageCPrerequisiteFactoryContext,
    base_or_chain: DiagnosticPreregistrationArtifact | DiagnosticPreregistrationChain,
) -> StageCPrerequisiteAdmissionArtifact:
    """Require all exact admitted refs in the immutable base design, never an amendment."""

    seal = _require_context(context, replay_bundles=_require_context(context).replay_bundles)
    with _SEALS_LOCK:
        suite = seal.suite
    if suite is None or len(suite) != 6:
        raise StageCPrerequisiteAdmissionError("no complete 4/4 prerequisite admission exists")
    drc, corpus, storage, authorization, intake, admission = suite
    fresh_admission = replay_stagec_prerequisite_admission_projection(
        admission,
        context=context,
        replay_bundles=seal.replay_bundles,
        detector_drc=drc,
        corpus=corpus,
        trusted_storage=storage,
        authorization=authorization,
        intake=intake,
    )
    with _SEALS_LOCK:
        refreshed = seal.suite
    if refreshed is None:  # pragma: no cover - replay sets the suite.
        raise StageCPrerequisiteAdmissionError("admission replay did not retain its suite")
    drc, corpus, storage, authorization, intake, fresh_admission = refreshed

    if type(base_or_chain) is DiagnosticPreregistrationChain:
        base_or_chain.assert_integrity()
        if base_or_chain.outcome_access is not None:
            raise StageCPrerequisiteAdmissionError("preregistration chain is no longer pre-outcome")
        windows = tuple(
            item
            for item in base_or_chain.amendments
            if item.change_class == "EXECUTION_WINDOW"
        )
        if len(windows) > 1:
            raise StageCPrerequisiteAdmissionError(
                "diagnostic chain contains multiple execution-window amendments"
            )
        if windows:
            changes = windows[0].payload["changes"]
            if (
                changes["window_start"] != authorization.window_start
                or changes["window_end"] != authorization.window_end
            ):
                raise StageCPrerequisiteAdmissionError(
                    "diagnostic chain execution window differs from admitted authorization"
                )
        chain_amendments = base_or_chain.amendments
        base = base_or_chain.base
    elif type(base_or_chain) is DiagnosticPreregistrationArtifact:
        chain_amendments = ()
        base = base_or_chain
    else:
        raise StageCPrerequisiteAdmissionError(
            "base_or_chain must be an exact diagnostic preregistration carrier or chain"
        )
    exact_base = load_diagnostic_preregistration(base.raw_bytes)
    if exact_base != base:
        raise StageCPrerequisiteAdmissionError("diagnostic preregistration differs from exact replay")
    design = expect_object(thaw_json(exact_base.payload["design"]), "$.design")
    input_rows = design["input_artifacts"]
    if type(input_rows) is not list:
        raise StageCPrerequisiteAdmissionError("base design.input_artifacts is not an exact array")
    input_refs = tuple(
        parse_artifact_ref(item, f"$.design.input_artifacts[{index}]")
        for index, item in enumerate(input_rows)
    )
    required = (
        seal.prompt.artifact_ref,
        drc.artifact_ref,
        *drc.artifact_refs,
        corpus.artifact_ref,
        *corpus.artifact_refs,
        storage.artifact_ref,
        *storage.artifact_refs,
        authorization.artifact_ref,
        *authorization.artifact_refs,
        intake.artifact_ref,
        fresh_admission.artifact_ref,
    )
    for reference in required:
        if reference not in input_refs:
            raise StageCPrerequisiteAdmissionError(
                f"base design.input_artifacts omits exact prerequisite {reference.artifact_id!r}"
            )
    prompt_dependencies = _prompt_dependency_refs(seal)
    base_extras = tuple(
        reference
        for reference in exact_base.artifact_refs
        if reference not in {seal.split.artifact_ref, seal.prompt.artifact_ref}
    )
    amendment_refs = tuple(
        reference
        for amendment in chain_amendments
        for reference in (amendment.artifact_ref, *amendment.artifact_refs)
    )
    _unique_refs(
        (
            seal.prompt.artifact_ref,
            *prompt_dependencies,
            exact_base.artifact_ref,
            *base_extras,
            *amendment_refs,
        ),
        "preregistration plus exact prompt dependency closure",
    )
    split_rows = thaw_json(exact_base.payload["splits"])
    if type(split_rows) is not list or len(split_rows) != 1:
        raise StageCPrerequisiteAdmissionError("base must retain one exact C-Cal split")
    split_source = parse_artifact_ref(split_rows[0]["source_artifact"], "$.splits[0].source_artifact")
    if split_source != seal.split.artifact_ref or not split_source.verify_bytes(seal.split.raw_bytes):
        raise StageCPrerequisiteAdmissionError("base split source is not the exact target split")
    created_times = (
        seal.prompt.created_at,
        drc.created_at,
        corpus.created_at,
        storage.created_at,
        authorization.created_at,
        intake.created_at,
        fresh_admission.created_at,
    )
    if any(_time(value) >= _time(exact_base.created_at) for value in created_times):
        raise StageCPrerequisiteAdmissionError(
            "prompt/candidates/intake/admission must all predate base preregistration"
        )
    if _time(exact_base.created_at) >= _time(authorization.window_start):
        raise StageCPrerequisiteAdmissionError(
            "base preregistration must remain prospective to the authorization window"
        )
    verifier_now = _utc_now()
    if (
        type(verifier_now) is not datetime
        or verifier_now.tzinfo is None
        or verifier_now.utcoffset() is None
        or verifier_now.utcoffset().total_seconds() != 0
    ):
        raise StageCPrerequisiteAdmissionError(
            "verifier clock must return an exact timezone-aware UTC datetime"
        )
    strict_times = (
        _time(fresh_admission.created_at),
        _time(exact_base.created_at),
        *(_time(item.created_at) for item in chain_amendments),
        verifier_now,
        _time(authorization.window_start),
        _time(authorization.window_end),
        _time(storage.retention_until),
    )
    if any(left >= right for left, right in zip(strict_times, strict_times[1:])):
        raise StageCPrerequisiteAdmissionError(
            "admission, base, ordered amendments, verifier time, authorization window, "
            "and trusted-storage retention are not in strict prospective order"
        )
    return fresh_admission


__all__ = [
    "ADMITTED_FOR_PROSPECTIVE_PREREGISTRATION_ONLY",
    "AUTHORIZATION_INSTRUMENT_MEDIA_TYPE",
    "CORPUS_ADJUDICATION_MEDIA_TYPE",
    "CORPUS_ROWS_MEDIA_TYPE",
    "CORPUS_SPLIT_ASSIGNMENT_MEDIA_TYPE",
    "CORPUS_SURFACE_BUNDLE_MEDIA_TYPE",
    "DETECTOR_DRC_PROFILE_MEDIA_TYPE",
    "DETECTOR_KNOWN_FAULT_FIXTURE_MEDIA_TYPE",
    "DETECTOR_RULESET_MEDIA_TYPE",
    "NOT_PERFORMED_BY_INTAKE",
    "OBJECT_LOCK_RECEIPT_MEDIA_TYPE",
    "OBJECT_READBACK_RECEIPT_MEDIA_TYPE",
    "OWNER_ASSERTED_CANDIDATE_STRUCTURAL_REPLAY_ONLY",
    "OWNER_ASSERTS_PRESENT",
    "STAGEC_AUTHORIZATION_INSTRUMENT_SCHEMA",
    "STAGEC_CORPUS_ADJUDICATION_SCHEMA",
    "STAGEC_CORPUS_ROWS_MANIFEST_SCHEMA",
    "STAGEC_CORPUS_SPLIT_ASSIGNMENT_SCHEMA",
    "STAGEC_CORPUS_SURFACE_BUNDLE_SCHEMA",
    "STAGEC_DETECTOR_DRC_PROFILE_SCHEMA",
    "STAGEC_DETECTOR_KNOWN_FAULT_FIXTURE_SCHEMA",
    "STAGEC_DETECTOR_RULESET_SCHEMA",
    "STAGEC_DETECTOR_DRC_RECEIPT_MEDIA_TYPE",
    "STAGEC_DETECTOR_DRC_RECEIPT_SCHEMA",
    "STAGEC_EXECUTION_AUTHORIZATION_MEDIA_TYPE",
    "STAGEC_EXECUTION_AUTHORIZATION_SCHEMA",
    "STAGEC_FROZEN_CORPUS_BUNDLE_MEDIA_TYPE",
    "STAGEC_FROZEN_CORPUS_BUNDLE_SCHEMA",
    "STAGEC_PREREQUISITE_ADMISSION_MEDIA_TYPE",
    "STAGEC_PREREQUISITE_ADMISSION_SCHEMA",
    "STAGEC_PREREQUISITE_DEPENDENCY_DOMAINS",
    "STAGEC_PREREQUISITE_DEPENDENCY_SCHEMAS",
    "STAGEC_PREREQUISITE_INTAKE_MEDIA_TYPE",
    "STAGEC_PREREQUISITE_INTAKE_SCHEMA",
    "STAGEC_PREREQUISITE_TARGET_DOMAIN",
    "STAGEC_PROSPECTIVE_SUBJECT_DOMAIN",
    "STAGEC_OBJECT_LOCK_RECEIPT_SCHEMA",
    "STAGEC_OBJECT_READBACK_RECEIPT_SCHEMA",
    "STAGEC_STORAGE_VERIFIER_IDENTITY_SCHEMA",
    "STAGEC_TRUSTED_TIME_RECEIPT_SCHEMA",
    "STAGEC_TRUSTED_STORAGE_RECEIPT_MEDIA_TYPE",
    "STAGEC_TRUSTED_STORAGE_RECEIPT_SCHEMA",
    "STORAGE_VERIFIER_IDENTITY_MEDIA_TYPE",
    "TRUSTED_TIME_RECEIPT_MEDIA_TYPE",
    "StageCDetectorDRCReceiptArtifact",
    "StageCExecutionAuthorizationArtifact",
    "StageCFrozenCorpusBundleArtifact",
    "StageCPrerequisiteAdmissionArtifact",
    "StageCPrerequisiteAdmissionError",
    "StageCPrerequisiteFactoryContext",
    "StageCPrerequisiteIntakeArtifact",
    "StageCTrustedStorageReceiptArtifact",
    "build_stagec_prerequisite_factory_context",
    "derive_stagec_prospective_subject_sha256",
    "load_stagec_detector_drc_receipt",
    "load_stagec_execution_authorization",
    "load_stagec_frozen_corpus_bundle",
    "load_stagec_prerequisite_admission",
    "load_stagec_prerequisite_intake",
    "load_stagec_trusted_storage_receipt",
    "replay_stagec_prerequisite_admission_projection",
    "require_stagec_prerequisite_admission_in_preregistration",
]
