"""Prospective Diagnostic Study controls for the Stage C calibration split.

This additive protocol deliberately does not reuse or widen Study-v1.  It
freezes the exact Stage C capture requests first, binds their inventory as the
sole diagnostic split source, binds that split to an exact pre-outcome
``DiagnosticPreregistrationChain``, and only then creates per-case Study
request envelopes.  A Study request *references* its Stage C capture request;
the two media types and schemas are never treated as interchangeable.

Everything in this module is ``STRUCTURE_ONLY / NON_AUTHORITY``.  There is no
worker authorization, model execution, authenticated clock, durable one-use
store, WORM anchor, Evidence Packet, scientific conclusion, license, product
route, or disclosure authority here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

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
    expect_keys,
    expect_machine_id,
    expect_object,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
    require_unique,
)
from .diagnostic_preregistration import (
    DIAGNOSTIC_AMENDMENT_MEDIA_TYPE,
    DIAGNOSTIC_CALIBRATION,
    DIAGNOSTIC_ONLY,
    DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE,
    DiagnosticAmendmentArtifact,
    DiagnosticPreregistrationArtifact,
    DiagnosticPreregistrationChain,
)


DIAGNOSTIC_SPLIT_INVENTORY_SCHEMA = (
    "cas_harness_v2.diagnostic_split_inventory.v1"
)
DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-split-inventory+json"
)
DIAGNOSTIC_STUDY_PLAN_SCHEMA = "cas_harness_v2.diagnostic_study_plan.v1"
DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-study-plan+json"
)
DIAGNOSTIC_STUDY_REQUEST_SCHEMA = (
    "cas_harness_v2.diagnostic_stagec_study_request.v1"
)
DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-study-request+json"
)
DIAGNOSTIC_STUDY_REQUEST_ID_DOMAIN = (
    "cas_harness_v2.diagnostic_stagec_study_request_id.v1"
)

STAGEC_CAPTURE_REQUEST_SCHEMA = "cas_harness.stagec.capture_request.v1"
STAGEC_CAPTURE_REQUEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-capture-request+json"
)

ADVERSARIAL_PRESENT = "ADVERSARIAL_PRESENT"
CLEAN_ABSENT = "CLEAN_ABSENT"
CLEAN_NULL_ABSENT = "CLEAN_NULL_ABSENT"
DIAGNOSTIC_VARIANT_ROLES = (
    ADVERSARIAL_PRESENT,
    CLEAN_ABSENT,
    CLEAN_NULL_ABSENT,
)
DIAGNOSTIC_GROUP_COUNT = 160
DIAGNOSTIC_CASE_COUNT = 480

_AUTHORITY = {
    "scope": "STRUCTURE_ONLY",
    "execution_authority": "NOT_GRANTED",
    "authentication": "NOT_PROVIDED",
    "durable_one_use": "NOT_PROVIDED",
    "trusted_time": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "packet_v2": "FORBIDDEN",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "claim_promotion": "FORBIDDEN",
    "license": "NOT_GRANTED",
    "product": "NOT_AUTHORIZED",
    "disclosure": "HELD",
}

_INVENTORY_BOUNDARY = {
    "freeze_scope": "EXACT_ORDERED_CAPTURE_REQUEST_REFS_AND_BYTES",
    "case_membership": "STRICTLY_REPLAYED_FROM_CAPTURE_REQUEST_BYTES",
    "request_media_coercion": "FORBIDDEN",
    "execution": "NOT_PERFORMED",
}

_PLAN_BOUNDARY = {
    "state_scope": "PROCESS_LOCAL_EXACT_BYTE_REPLAY",
    "pre_outcome_only": True,
    "split_count": 1,
    "execution_window_semantic": "DECLARED_UTC_TIMESTAMPS_ONLY",
    "execution_window_trust": "NOT_TRUSTED",
    "worker_authorization": "NOT_CREATED",
    "execution": "NOT_PERFORMED",
}

_REQUEST_BOUNDARY = {
    "state_scope": "PROCESS_LOCAL_EXACT_BYTE_REPLAY",
    "envelope_position": "AFTER_PLAN_BEFORE_EXECUTION_WINDOW",
    "capture_request_relation": "SEPARATE_EXACT_REF_AND_BYTES_BINDING",
    "request_media_coercion": "FORBIDDEN",
    "worker_authorization": "NOT_CREATED",
    "execution": "NOT_PERFORMED",
}

_RETRY_POLICY = {
    "maximum_attempts": 1,
    "retry": "FORBIDDEN",
    "replacement": "FORBIDDEN",
    "durable_enforcement": "EXTERNAL_REQUIRED_NOT_PROVIDED",
}


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _base_ref(base: DiagnosticPreregistrationArtifact) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=base.preregistration_id,
        sha256=base.sha256,
        byte_length=base.byte_length,
        media_type=DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE,
    )


def _require_canonical(snapshot: bytes, value: Mapping[str, Any], path: str) -> None:
    if snapshot != canonical_json_bytes(value):
        raise SchemaValidationError(f"{path} must use exact canonical JSON bytes")


def _require_unique_refs(
    references: tuple[ArtifactRef, ...],
    path: str,
) -> tuple[ArtifactRef, ...]:
    if type(references) is not tuple or any(
        type(reference) is not ArtifactRef for reference in references
    ):
        raise SchemaValidationError(f"{path} must contain exact ArtifactRef values")
    require_unique((item.artifact_id for item in references), f"{path}.artifact_id")
    require_unique((item.sha256 for item in references), f"{path}.sha256")
    return references


@dataclass(frozen=True, slots=True)
class StageCCaptureRequestArtifact:
    """Strict controller-side view of one worker Stage C capture request."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    artifact_ref: ArtifactRef
    study_id: str
    case_id: str
    split_id: str
    base_intent_group_id: str
    frozen_variant: str
    frozen_label: str
    invocation_id: str
    prompt: str
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DiagnosticStudyCase:
    execution_ordinal: int
    case_id: str
    base_intent_group_id: str
    split_id: str
    frozen_variant: str
    frozen_label: str
    invocation_id: str
    capture_request: ArtifactRef


@dataclass(frozen=True, slots=True)
class DiagnosticPlannedStudyCase:
    execution_ordinal: int
    case_id: str
    base_intent_group_id: str
    split_id: str
    frozen_variant: str
    frozen_label: str
    invocation_id: str
    capture_request: ArtifactRef
    study_request_id: str


@dataclass(frozen=True, slots=True)
class DiagnosticSplitInventoryArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    inventory_id: str
    study_id: str
    split_id: str
    cases: tuple[DiagnosticStudyCase, ...]
    capture_requests: tuple[StageCCaptureRequestArtifact, ...]
    ordered_case_inventory_sha256: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.inventory_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticStudyPlanArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    plan_id: str
    study_id: str
    created_at: str
    pre_outcome_chain_sha256: str
    protected_design_sha256: str
    execution_window_start: str
    execution_window_end: str
    inventory: DiagnosticSplitInventoryArtifact
    cases: tuple[DiagnosticPlannedStudyCase, ...]
    execution_identity_artifacts: tuple[ArtifactRef, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.plan_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticStudyRequestArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    request_id: str
    created_at: str
    study_id: str
    case_id: str
    execution_ordinal: int
    capture_request: ArtifactRef
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.request_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE,
        )


def load_stagec_capture_request(
    reference: ArtifactRef,
    raw: bytes | bytearray | memoryview,
) -> StageCCaptureRequestArtifact:
    """Strict-load one exact Stage C request without changing its media type."""

    if type(reference) is not ArtifactRef:
        raise SchemaValidationError("reference must be an exact ArtifactRef")
    if reference.media_type != STAGEC_CAPTURE_REQUEST_MEDIA_TYPE:
        raise SchemaValidationError(
            "Stage C capture request must retain its exact capture-request media type"
        )
    snapshot, obj = load_json_object(raw)
    _require_canonical(snapshot, obj, "Stage C capture request")
    if not reference.verify_bytes(snapshot):
        raise SchemaValidationError(
            "Stage C capture request bytes do not verify the supplied exact ref"
        )
    expect_keys(
        obj,
        required={
            "schema_version",
            "study_id",
            "case_id",
            "split_id",
            "base_intent_group_id",
            "frozen_variant",
            "frozen_label",
            "invocation_id",
            "prompt",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_CAPTURE_REQUEST_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {STAGEC_CAPTURE_REQUEST_SCHEMA!r}"
        )
    study_id = expect_machine_id(obj["study_id"], "$.study_id")
    case_id = expect_machine_id(obj["case_id"], "$.case_id")
    split_id = expect_machine_id(obj["split_id"], "$.split_id")
    group_id = expect_machine_id(
        obj["base_intent_group_id"], "$.base_intent_group_id"
    )
    variant = expect_string(obj["frozen_variant"], "$.frozen_variant", maximum=128)
    if variant not in DIAGNOSTIC_VARIANT_ROLES:
        raise SchemaValidationError(
            "$.frozen_variant must be one exact diagnostic Stage C variant"
        )
    label = expect_string(obj["frozen_label"], "$.frozen_label", maximum=128)
    if label != variant:
        raise SchemaValidationError(
            "Stage C frozen_label must exactly equal frozen_variant"
        )
    invocation_id = expect_machine_id(obj["invocation_id"], "$.invocation_id")
    prompt = expect_string(obj["prompt"], "$.prompt")
    try:
        prompt.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise SchemaValidationError("$.prompt must be strict UTF-8") from exc
    return StageCCaptureRequestArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        artifact_ref=reference,
        study_id=study_id,
        case_id=case_id,
        split_id=split_id,
        base_intent_group_id=group_id,
        frozen_variant=variant,
        frozen_label=label,
        invocation_id=invocation_id,
        prompt=prompt,
        payload=freeze_json(obj),
    )


def _same_capture_request(
    left: StageCCaptureRequestArtifact,
    right: StageCCaptureRequestArtifact,
) -> bool:
    return (
        type(left) is StageCCaptureRequestArtifact
        and type(right) is StageCCaptureRequestArtifact
        and left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.artifact_ref == right.artifact_ref
        and left.study_id == right.study_id
        and left.case_id == right.case_id
        and left.split_id == right.split_id
        and left.base_intent_group_id == right.base_intent_group_id
        and left.frozen_variant == right.frozen_variant
        and left.frozen_label == right.frozen_label
        and left.invocation_id == right.invocation_id
        and left.prompt == right.prompt
        and canonical_sha256(left.payload) == canonical_sha256(right.payload)
    )


def _replay_capture_requests(
    capture_requests: tuple[StageCCaptureRequestArtifact, ...],
) -> tuple[StageCCaptureRequestArtifact, ...]:
    if type(capture_requests) is not tuple:
        raise SchemaValidationError("capture_requests must be an exact tuple")
    if len(capture_requests) != DIAGNOSTIC_CASE_COUNT:
        raise SchemaValidationError(
            f"diagnostic inventory requires exactly {DIAGNOSTIC_CASE_COUNT} capture requests"
        )
    replayed: list[StageCCaptureRequestArtifact] = []
    for index, request in enumerate(capture_requests):
        if type(request) is not StageCCaptureRequestArtifact:
            raise SchemaValidationError(
                f"capture_requests[{index}] must be an exact StageCCaptureRequestArtifact"
            )
        fresh = load_stagec_capture_request(request.artifact_ref, request.raw_bytes)
        if not _same_capture_request(fresh, request):
            raise SchemaValidationError(
                f"capture_requests[{index}] does not match exact-byte replay"
            )
        replayed.append(fresh)
    refs = tuple(item.artifact_ref for item in replayed)
    _require_unique_refs(refs, "capture_requests")
    require_unique((item.case_id for item in replayed), "capture_requests.case_id")
    require_unique(
        (item.invocation_id for item in replayed),
        "capture_requests.invocation_id",
    )
    return tuple(replayed)


def _cases_from_requests(
    capture_requests: tuple[StageCCaptureRequestArtifact, ...],
) -> tuple[DiagnosticStudyCase, ...]:
    replayed = _replay_capture_requests(capture_requests)
    study_ids = {item.study_id for item in replayed}
    split_ids = {item.split_id for item in replayed}
    if len(study_ids) != 1 or len(split_ids) != 1:
        raise SchemaValidationError(
            "every diagnostic capture request must share one study_id and split_id"
        )

    cases = tuple(
        DiagnosticStudyCase(
            execution_ordinal=index,
            case_id=request.case_id,
            base_intent_group_id=request.base_intent_group_id,
            split_id=request.split_id,
            frozen_variant=request.frozen_variant,
            frozen_label=request.frozen_label,
            invocation_id=request.invocation_id,
            capture_request=request.artifact_ref,
        )
        for index, request in enumerate(replayed, start=1)
    )
    groups: list[str] = []
    for offset in range(0, len(cases), len(DIAGNOSTIC_VARIANT_ROLES)):
        rows = cases[offset : offset + len(DIAGNOSTIC_VARIANT_ROLES)]
        if len(rows) != len(DIAGNOSTIC_VARIANT_ROLES):
            raise SchemaValidationError(
                "diagnostic inventory ends with an incomplete three-variant group"
            )
        group_id = rows[0].base_intent_group_id
        if any(item.base_intent_group_id != group_id for item in rows):
            raise SchemaValidationError(
                "each diagnostic group must be one contiguous three-case block"
            )
        if tuple(item.frozen_variant for item in rows) != DIAGNOSTIC_VARIANT_ROLES:
            raise SchemaValidationError(
                "each diagnostic group must contain the three canonical variants in exact order"
            )
        groups.append(group_id)
    require_unique(groups, "diagnostic inventory group order")
    if len(groups) != DIAGNOSTIC_GROUP_COUNT:
        raise SchemaValidationError(
            f"diagnostic inventory requires exactly {DIAGNOSTIC_GROUP_COUNT} groups"
        )
    return cases


def _case_value(case: DiagnosticStudyCase) -> dict[str, Any]:
    return {
        "execution_ordinal": case.execution_ordinal,
        "case_id": case.case_id,
        "base_intent_group_id": case.base_intent_group_id,
        "split_id": case.split_id,
        "frozen_variant": case.frozen_variant,
        "frozen_label": case.frozen_label,
        "invocation_id": case.invocation_id,
        "capture_request": _artifact_ref_value(case.capture_request),
    }


def _inventory_value(
    *,
    inventory_id: str,
    capture_requests: tuple[StageCCaptureRequestArtifact, ...],
) -> tuple[dict[str, Any], tuple[DiagnosticStudyCase, ...]]:
    inventory_id = expect_machine_id(inventory_id, "inventory_id")
    cases = _cases_from_requests(capture_requests)
    if inventory_id in {item.capture_request.artifact_id for item in cases}:
        raise SchemaValidationError(
            "inventory_id collides with a frozen capture-request artifact"
        )
    value = {
        "schema_version": DIAGNOSTIC_SPLIT_INVENTORY_SCHEMA,
        "inventory_id": inventory_id,
        "study_id": capture_requests[0].study_id,
        "split_id": capture_requests[0].split_id,
        "role": DIAGNOSTIC_CALIBRATION,
        "grouping_key": "base_intent_group_id",
        "group_count": DIAGNOSTIC_GROUP_COUNT,
        "enrolled_case_count": DIAGNOSTIC_CASE_COUNT,
        "ordered_cases": [_case_value(case) for case in cases],
        "boundary": dict(_INVENTORY_BOUNDARY),
        "authority": dict(_AUTHORITY),
    }
    return value, cases


def load_diagnostic_split_inventory(
    raw: bytes | bytearray | memoryview,
    *,
    capture_requests: tuple[StageCCaptureRequestArtifact, ...],
) -> DiagnosticSplitInventoryArtifact:
    """Strict-load the sole split inventory against every exact request byte."""

    snapshot, obj = load_json_object(raw)
    _require_canonical(snapshot, obj, "diagnostic split inventory")
    expect_keys(
        obj,
        required={
            "schema_version",
            "inventory_id",
            "study_id",
            "split_id",
            "role",
            "grouping_key",
            "group_count",
            "enrolled_case_count",
            "ordered_cases",
            "boundary",
            "authority",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_SPLIT_INVENTORY_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {DIAGNOSTIC_SPLIT_INVENTORY_SCHEMA!r}"
        )
    inventory_id = expect_machine_id(obj["inventory_id"], "$.inventory_id")
    expected, cases = _inventory_value(
        inventory_id=inventory_id,
        capture_requests=capture_requests,
    )
    if obj != expected:
        raise SchemaValidationError(
            "diagnostic split inventory does not exactly replay its ordered capture requests"
        )
    refs = _require_unique_refs(
        tuple(item.artifact_ref for item in capture_requests),
        "diagnostic split inventory refs",
    )
    return DiagnosticSplitInventoryArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        inventory_id=inventory_id,
        study_id=capture_requests[0].study_id,
        split_id=capture_requests[0].split_id,
        cases=cases,
        capture_requests=tuple(capture_requests),
        ordered_case_inventory_sha256=canonical_sha256(expected["ordered_cases"]),
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def build_diagnostic_split_inventory(
    *,
    inventory_id: str,
    capture_requests: tuple[StageCCaptureRequestArtifact, ...],
) -> DiagnosticSplitInventoryArtifact:
    """Build and immediately replay one exact 160-group/480-case inventory."""

    value, _ = _inventory_value(
        inventory_id=inventory_id,
        capture_requests=capture_requests,
    )
    return load_diagnostic_split_inventory(
        canonical_json_bytes(value),
        capture_requests=capture_requests,
    )


def _same_inventory(
    left: DiagnosticSplitInventoryArtifact,
    right: DiagnosticSplitInventoryArtifact,
) -> bool:
    return (
        type(left) is DiagnosticSplitInventoryArtifact
        and type(right) is DiagnosticSplitInventoryArtifact
        and left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.inventory_id == right.inventory_id
        and left.study_id == right.study_id
        and left.split_id == right.split_id
        and left.cases == right.cases
        and len(left.capture_requests) == len(right.capture_requests)
        and all(
            _same_capture_request(a, b)
            for a, b in zip(
                left.capture_requests,
                right.capture_requests,
                strict=True,
            )
        )
        and left.ordered_case_inventory_sha256
        == right.ordered_case_inventory_sha256
        and canonical_sha256(left.payload) == canonical_sha256(right.payload)
        and left.artifact_refs == right.artifact_refs
    )


def _replay_inventory(
    inventory: DiagnosticSplitInventoryArtifact,
) -> DiagnosticSplitInventoryArtifact:
    if type(inventory) is not DiagnosticSplitInventoryArtifact:
        raise SchemaValidationError(
            "inventory must be an exact DiagnosticSplitInventoryArtifact"
        )
    replayed = load_diagnostic_split_inventory(
        inventory.raw_bytes,
        capture_requests=inventory.capture_requests,
    )
    if not _same_inventory(replayed, inventory):
        raise SchemaValidationError(
            "diagnostic inventory carrier does not match fresh exact-byte replay"
        )
    return replayed


def _require_pre_outcome_chain(
    chain: DiagnosticPreregistrationChain,
) -> DiagnosticPreregistrationArtifact:
    if type(chain) is not DiagnosticPreregistrationChain:
        raise SchemaValidationError(
            "chain must be an exact DiagnosticPreregistrationChain; Study-v1 adaptation is forbidden"
        )
    chain.assert_integrity()
    if chain.outcome_access is not None:
        raise SchemaValidationError(
            "diagnostic Study planning and requests require a pre-outcome chain"
        )
    return chain.base


def _execution_context(
    chain: DiagnosticPreregistrationChain,
) -> tuple[
    DiagnosticAmendmentArtifact,
    tuple[ArtifactRef, ...],
    tuple[ArtifactRef, ...],
]:
    amendments = chain.amendments
    windows = tuple(
        amendment
        for amendment in amendments
        if amendment.change_class == "EXECUTION_WINDOW"
    )
    if len(windows) != 1:
        raise SchemaValidationError(
            "Diagnostic Study plan requires exactly one prospective EXECUTION_WINDOW amendment"
        )
    identity_refs = tuple(
        reference
        for amendment in amendments
        if amendment.change_class == "EXECUTION_IDENTITY_ADDITION"
        for reference in amendment.artifact_refs
    )
    if not identity_refs:
        raise SchemaValidationError(
            "Diagnostic Study plan requires at least one prospectively added execution-identity artifact"
        )
    _require_unique_refs(identity_refs, "execution identity artifacts")
    amendment_refs = tuple(amendment.artifact_ref for amendment in amendments)
    _require_unique_refs(amendment_refs, "diagnostic amendments")
    return windows[0], identity_refs, amendment_refs


def _expected_preregistration_binding(
    chain: DiagnosticPreregistrationChain,
    base: DiagnosticPreregistrationArtifact,
    amendment_refs: tuple[ArtifactRef, ...],
) -> dict[str, Any]:
    return {
        "base_artifact": _artifact_ref_value(_base_ref(base)),
        "pre_outcome_chain_sha256": chain.pre_outcome_chain_sha256,
        "protected_design_sha256": base.protected_design_sha256,
        "study_phase": DIAGNOSTIC_CALIBRATION,
        "claim_ceiling": DIAGNOSTIC_ONLY,
        "ordered_amendments": [
            _artifact_ref_value(reference) for reference in amendment_refs
        ],
    }


def _window_value(window: DiagnosticAmendmentArtifact) -> dict[str, Any]:
    return {
        "amendment": _artifact_ref_value(window.artifact_ref),
        "window_start": window.payload["changes"]["window_start"],
        "window_end": window.payload["changes"]["window_end"],
        "semantic": "DECLARED_UTC_TIMESTAMP_WINDOW_ONLY",
        "trust": "NOT_TRUSTED",
    }


def _validate_sole_split(
    base: DiagnosticPreregistrationArtifact,
    inventory: DiagnosticSplitInventoryArtifact,
) -> Mapping[str, Any]:
    splits = base.payload["splits"]
    if type(splits) is not tuple or len(splits) != 1:
        raise SchemaValidationError(
            "Diagnostic Study requires exactly one preregistered split"
        )
    split = splits[0]
    if split["role"] != DIAGNOSTIC_CALIBRATION:
        raise SchemaValidationError(
            "sole diagnostic split must retain DIAGNOSTIC_CALIBRATION role"
        )
    if split["split_id"] != inventory.split_id:
        raise SchemaValidationError(
            "diagnostic inventory split_id does not match the sole preregistered split"
        )
    source_ref = parse_artifact_ref(
        thaw_json(split["source_artifact"]),
        "$.preregistration.splits[0].source_artifact",
    )
    if source_ref != inventory.artifact_ref or not source_ref.verify_bytes(
        inventory.raw_bytes
    ):
        raise SchemaValidationError(
            "sole preregistered split source must be this exact diagnostic inventory"
        )
    if split["target_groups"] != DIAGNOSTIC_GROUP_COUNT:
        raise SchemaValidationError(
            f"sole diagnostic split must target exactly {DIAGNOSTIC_GROUP_COUNT} groups"
        )
    if split["target_enrolled_rows"] != DIAGNOSTIC_CASE_COUNT:
        raise SchemaValidationError(
            f"sole diagnostic split must enroll exactly {DIAGNOSTIC_CASE_COUNT} cases"
        )
    return split


def _plan_refs(
    *,
    chain: DiagnosticPreregistrationChain,
    base: DiagnosticPreregistrationArtifact,
    amendment_refs: tuple[ArtifactRef, ...],
    inventory: DiagnosticSplitInventoryArtifact,
) -> tuple[ArtifactRef, ...]:
    amendment_added_refs = tuple(
        reference
        for amendment in chain.amendments
        for reference in amendment.artifact_refs
    )
    references = (
        _base_ref(base),
        *base.artifact_refs,
        *amendment_refs,
        *amendment_added_refs,
        *(case.capture_request for case in inventory.cases),
    )
    return _require_unique_refs(references, "diagnostic Study plan refs")


def _derive_study_request_id(
    *,
    plan_id: str,
    study_id: str,
    inventory_sha256: str,
    case: DiagnosticStudyCase,
) -> str:
    digest = canonical_sha256(
        {
            "domain": DIAGNOSTIC_STUDY_REQUEST_ID_DOMAIN,
            "plan_id": plan_id,
            "study_id": study_id,
            "inventory_sha256": inventory_sha256,
            "execution_ordinal": case.execution_ordinal,
            "case_id": case.case_id,
            "capture_request": _artifact_ref_value(case.capture_request),
        }
    )
    return expect_machine_id(
        f"diagnostic-study-request-{digest}",
        "derived diagnostic Study request ID",
    )


def _planned_cases(
    *,
    plan_id: str,
    inventory: DiagnosticSplitInventoryArtifact,
    predecessor_refs: tuple[ArtifactRef, ...],
) -> tuple[DiagnosticPlannedStudyCase, ...]:
    planned = tuple(
        DiagnosticPlannedStudyCase(
            execution_ordinal=case.execution_ordinal,
            case_id=case.case_id,
            base_intent_group_id=case.base_intent_group_id,
            split_id=case.split_id,
            frozen_variant=case.frozen_variant,
            frozen_label=case.frozen_label,
            invocation_id=case.invocation_id,
            capture_request=case.capture_request,
            study_request_id=_derive_study_request_id(
                plan_id=plan_id,
                study_id=inventory.study_id,
                inventory_sha256=inventory.sha256,
                case=case,
            ),
        )
        for case in inventory.cases
    )
    request_ids = require_unique(
        (case.study_request_id for case in planned),
        "Diagnostic Study plan study_request_id",
    )
    predecessor_ids = {
        plan_id,
        *(reference.artifact_id for reference in predecessor_refs),
    }
    collisions = predecessor_ids.intersection(request_ids)
    if collisions:
        raise SchemaValidationError(
            "derived diagnostic Study request ID collides with a plan predecessor: "
            f"{sorted(collisions)!r}"
        )
    capture_ids = {case.capture_request.artifact_id for case in inventory.cases}
    if capture_ids.intersection(request_ids):
        raise SchemaValidationError(
            "derived diagnostic Study request ID collides with a capture-request artifact"
        )
    return planned


def _planned_case_value(case: DiagnosticPlannedStudyCase) -> dict[str, Any]:
    return {
        "execution_ordinal": case.execution_ordinal,
        "case_id": case.case_id,
        "study_request_id": case.study_request_id,
        "capture_request": _artifact_ref_value(case.capture_request),
    }


def _plan_value(
    *,
    chain: DiagnosticPreregistrationChain,
    inventory: DiagnosticSplitInventoryArtifact,
    plan_id: str,
    created_at: str,
) -> tuple[
    dict[str, Any],
    tuple[ArtifactRef, ...],
    tuple[DiagnosticPlannedStudyCase, ...],
    tuple[ArtifactRef, ...],
    str,
    str,
]:
    base = _require_pre_outcome_chain(chain)
    replayed_inventory = _replay_inventory(inventory)
    plan_id = expect_machine_id(plan_id, "plan_id")
    created_at = expect_timestamp(created_at, "created_at")
    if replayed_inventory.study_id != replayed_inventory.capture_requests[0].study_id:
        raise SchemaValidationError("diagnostic inventory study_id drifted")
    split = _validate_sole_split(base, replayed_inventory)
    window, identity_refs, amendment_refs = _execution_context(chain)
    predecessor_time = (
        chain.amendments[-1].created_at if chain.amendments else base.created_at
    )
    window_start = expect_timestamp(
        window.payload["changes"]["window_start"],
        "execution_window.window_start",
    )
    window_end = expect_timestamp(
        window.payload["changes"]["window_end"],
        "execution_window.window_end",
    )
    if _time(created_at) <= _time(predecessor_time):
        raise SchemaValidationError(
            "Diagnostic Study plan must be created after the final preregistration amendment"
        )
    if _time(created_at) >= _time(window_start):
        raise SchemaValidationError(
            "Diagnostic Study plan must be frozen strictly before the execution window"
        )
    refs = _plan_refs(
        chain=chain,
        base=base,
        amendment_refs=amendment_refs,
        inventory=replayed_inventory,
    )
    if plan_id in {reference.artifact_id for reference in refs}:
        raise SchemaValidationError(
            "plan_id collides with a predecessor or frozen request artifact"
        )
    planned_cases = _planned_cases(
        plan_id=plan_id,
        inventory=replayed_inventory,
        predecessor_refs=refs,
    )
    value = {
        "schema_version": DIAGNOSTIC_STUDY_PLAN_SCHEMA,
        "plan_id": plan_id,
        "study_id": replayed_inventory.study_id,
        "created_at": created_at,
        "diagnostic_preregistration_binding": _expected_preregistration_binding(
            chain,
            base,
            amendment_refs,
        ),
        "single_split_binding": thaw_json(split),
        "execution_window": _window_value(window),
        "execution_identity_artifacts": [
            _artifact_ref_value(reference) for reference in identity_refs
        ],
        "frozen_inventory": {
            "inventory": _artifact_ref_value(replayed_inventory.artifact_ref),
            "group_count": DIAGNOSTIC_GROUP_COUNT,
            "ordered_case_count": DIAGNOSTIC_CASE_COUNT,
            "ordered_case_inventory_sha256": (
                replayed_inventory.ordered_case_inventory_sha256
            ),
        },
        "study_request_id_domain": DIAGNOSTIC_STUDY_REQUEST_ID_DOMAIN,
        "ordered_case_requests": [
            _planned_case_value(case) for case in planned_cases
        ],
        "reporting_policy": thaw_json(base.payload["reporting_policy"]),
        "boundary": dict(_PLAN_BOUNDARY),
        "authority": dict(_AUTHORITY),
        "governance": thaw_json(base.payload["governance"]),
    }
    return value, refs, planned_cases, identity_refs, window_start, window_end


def load_diagnostic_study_plan(
    raw: bytes | bytearray | memoryview,
    *,
    chain: DiagnosticPreregistrationChain,
    inventory: DiagnosticSplitInventoryArtifact,
) -> DiagnosticStudyPlanArtifact:
    """Strict-load one plan against the exact current diagnostic pre-chain."""

    snapshot, obj = load_json_object(raw)
    _require_canonical(snapshot, obj, "Diagnostic Study plan")
    expect_keys(
        obj,
        required={
            "schema_version",
            "plan_id",
            "study_id",
            "created_at",
            "diagnostic_preregistration_binding",
            "single_split_binding",
            "execution_window",
            "execution_identity_artifacts",
            "frozen_inventory",
            "study_request_id_domain",
            "ordered_case_requests",
            "reporting_policy",
            "boundary",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_STUDY_PLAN_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {DIAGNOSTIC_STUDY_PLAN_SCHEMA!r}"
        )
    plan_id = expect_machine_id(obj["plan_id"], "$.plan_id")
    study_id = expect_machine_id(obj["study_id"], "$.study_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    expected, refs, planned_cases, identities, window_start, window_end = _plan_value(
        chain=chain,
        inventory=inventory,
        plan_id=plan_id,
        created_at=created_at,
    )
    if obj != expected:
        raise SchemaValidationError(
            "Diagnostic Study plan does not exactly replay its chain/split/window/identity/inventory inputs"
        )
    if study_id != inventory.study_id:
        raise SchemaValidationError(
            "Diagnostic Study plan study_id does not match the frozen inventory"
        )
    replayed_inventory = _replay_inventory(inventory)
    base = _require_pre_outcome_chain(chain)
    return DiagnosticStudyPlanArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        plan_id=plan_id,
        study_id=study_id,
        created_at=created_at,
        pre_outcome_chain_sha256=chain.pre_outcome_chain_sha256,
        protected_design_sha256=base.protected_design_sha256,
        execution_window_start=window_start,
        execution_window_end=window_end,
        inventory=replayed_inventory,
        cases=planned_cases,
        execution_identity_artifacts=identities,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def build_diagnostic_study_plan(
    *,
    chain: DiagnosticPreregistrationChain,
    inventory: DiagnosticSplitInventoryArtifact,
    plan_id: str,
    created_at: str,
) -> DiagnosticStudyPlanArtifact:
    """Build and immediately strict-replay one pre-window diagnostic plan."""

    value, _, _, _, _, _ = _plan_value(
        chain=chain,
        inventory=inventory,
        plan_id=plan_id,
        created_at=created_at,
    )
    return load_diagnostic_study_plan(
        canonical_json_bytes(value),
        chain=chain,
        inventory=inventory,
    )


def _same_plan(
    left: DiagnosticStudyPlanArtifact,
    right: DiagnosticStudyPlanArtifact,
) -> bool:
    return (
        type(left) is DiagnosticStudyPlanArtifact
        and type(right) is DiagnosticStudyPlanArtifact
        and left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.plan_id == right.plan_id
        and left.study_id == right.study_id
        and left.created_at == right.created_at
        and left.pre_outcome_chain_sha256 == right.pre_outcome_chain_sha256
        and left.protected_design_sha256 == right.protected_design_sha256
        and left.execution_window_start == right.execution_window_start
        and left.execution_window_end == right.execution_window_end
        and _same_inventory(left.inventory, right.inventory)
        and left.cases == right.cases
        and left.execution_identity_artifacts == right.execution_identity_artifacts
        and canonical_sha256(left.payload) == canonical_sha256(right.payload)
        and left.artifact_refs == right.artifact_refs
    )


def _replay_plan(
    plan: DiagnosticStudyPlanArtifact,
    *,
    chain: DiagnosticPreregistrationChain,
) -> DiagnosticStudyPlanArtifact:
    if type(plan) is not DiagnosticStudyPlanArtifact:
        raise SchemaValidationError(
            "plan must be an exact DiagnosticStudyPlanArtifact"
        )
    replayed = load_diagnostic_study_plan(
        plan.raw_bytes,
        chain=chain,
        inventory=plan.inventory,
    )
    if not _same_plan(replayed, plan):
        raise SchemaValidationError(
            "Diagnostic Study plan carrier does not match fresh exact-byte replay"
        )
    return replayed


def _case_and_request(
    plan: DiagnosticStudyPlanArtifact,
    case_id: str,
) -> tuple[DiagnosticPlannedStudyCase, StageCCaptureRequestArtifact]:
    case_id = expect_machine_id(case_id, "case_id")
    matches = tuple(
        (case, request)
        for case, request in zip(
            plan.cases,
            plan.inventory.capture_requests,
            strict=True,
        )
        if case.case_id == case_id
    )
    if len(matches) != 1:
        raise SchemaValidationError(
            "case_id must identify exactly one frozen diagnostic case"
        )
    return matches[0]


def _study_request_refs(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    capture_request: StageCCaptureRequestArtifact,
) -> tuple[ArtifactRef, ...]:
    _require_pre_outcome_chain(chain)
    if capture_request.artifact_ref not in plan.artifact_refs:
        raise SchemaValidationError(
            "planned capture request is absent from the plan dependency closure"
        )
    return _require_unique_refs(
        (
            plan.artifact_ref,
            *plan.artifact_refs,
        ),
        "diagnostic Study request refs",
    )


def _study_request_value(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    case_id: str,
    created_at: str,
) -> tuple[
    dict[str, Any],
    DiagnosticPlannedStudyCase,
    StageCCaptureRequestArtifact,
    tuple[ArtifactRef, ...],
]:
    base = _require_pre_outcome_chain(chain)
    replayed_plan = _replay_plan(plan, chain=chain)
    case, capture_request = _case_and_request(replayed_plan, case_id)
    fresh_capture = load_stagec_capture_request(
        capture_request.artifact_ref,
        capture_request.raw_bytes,
    )
    if not _same_capture_request(fresh_capture, capture_request):
        raise SchemaValidationError(
            "planned Stage C capture request does not match fresh exact-byte replay"
        )
    request_id = expect_machine_id(case.study_request_id, "derived request_id")
    created_at = expect_timestamp(created_at, "created_at")
    if _time(created_at) <= _time(replayed_plan.created_at):
        raise SchemaValidationError(
            "diagnostic Study request must be created after the exact Study plan"
        )
    if _time(created_at) >= _time(replayed_plan.execution_window_start):
        raise SchemaValidationError(
            "diagnostic Study request must be frozen strictly before the execution window"
        )
    refs = _study_request_refs(
        chain=chain,
        plan=replayed_plan,
        capture_request=fresh_capture,
    )
    if request_id in {reference.artifact_id for reference in refs}:
        raise SchemaValidationError(
            "diagnostic Study request_id collides with a bound artifact"
        )
    value = {
        "schema_version": DIAGNOSTIC_STUDY_REQUEST_SCHEMA,
        "request_id": request_id,
        "created_at": created_at,
        "diagnostic_study_plan": _artifact_ref_value(replayed_plan.artifact_ref),
        "diagnostic_preregistration_binding": {
            "base_artifact": _artifact_ref_value(_base_ref(base)),
            "pre_outcome_chain_sha256": replayed_plan.pre_outcome_chain_sha256,
            "protected_design_sha256": replayed_plan.protected_design_sha256,
        },
        "case_binding": {
            "study_id": replayed_plan.study_id,
            "case_id": case.case_id,
            "execution_ordinal": case.execution_ordinal,
            "split_id": case.split_id,
            "base_intent_group_id": case.base_intent_group_id,
            "frozen_variant": case.frozen_variant,
            "frozen_label": case.frozen_label,
            "invocation_id": case.invocation_id,
        },
        "capture_request": _artifact_ref_value(fresh_capture.artifact_ref),
        "execution_window": thaw_json(replayed_plan.payload["execution_window"]),
        "retry_policy": dict(_RETRY_POLICY),
        "boundary": dict(_REQUEST_BOUNDARY),
        "authority": dict(_AUTHORITY),
        "governance": thaw_json(base.payload["governance"]),
    }
    return value, case, fresh_capture, refs


def load_diagnostic_study_request(
    raw: bytes | bytearray | memoryview,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
) -> DiagnosticStudyRequestArtifact:
    """Strict-load one post-plan envelope and its separate capture request."""

    snapshot, obj = load_json_object(raw)
    _require_canonical(snapshot, obj, "diagnostic Study request")
    expect_keys(
        obj,
        required={
            "schema_version",
            "request_id",
            "created_at",
            "diagnostic_study_plan",
            "diagnostic_preregistration_binding",
            "case_binding",
            "capture_request",
            "execution_window",
            "retry_policy",
            "boundary",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_STUDY_REQUEST_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {DIAGNOSTIC_STUDY_REQUEST_SCHEMA!r}"
        )
    request_id = expect_machine_id(obj["request_id"], "$.request_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    case_binding = expect_object(obj["case_binding"], "$.case_binding")
    if "case_id" not in case_binding:
        raise SchemaValidationError("$.case_binding.case_id is required")
    case_id = expect_machine_id(case_binding["case_id"], "$.case_binding.case_id")
    expected, case, capture_request, refs = _study_request_value(
        chain=chain,
        plan=plan,
        case_id=case_id,
        created_at=created_at,
    )
    if request_id != case.study_request_id:
        raise SchemaValidationError(
            "diagnostic Study request_id does not equal the plan-frozen derived ID"
        )
    if obj != expected:
        raise SchemaValidationError(
            "diagnostic Study request does not exactly replay its plan/case/capture-request inputs"
        )
    if capture_request.artifact_ref.media_type == DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE:
        raise SchemaValidationError(
            "capture request and diagnostic Study request media types must remain distinct"
        )
    return DiagnosticStudyRequestArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        request_id=request_id,
        created_at=created_at,
        study_id=plan.study_id,
        case_id=case.case_id,
        execution_ordinal=case.execution_ordinal,
        capture_request=capture_request.artifact_ref,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def build_diagnostic_study_request(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    case_id: str,
    created_at: str,
) -> DiagnosticStudyRequestArtifact:
    """Build and replay one non-authoritative per-case Study envelope."""

    value, _, _, _ = _study_request_value(
        chain=chain,
        plan=plan,
        case_id=case_id,
        created_at=created_at,
    )
    return load_diagnostic_study_request(
        canonical_json_bytes(value),
        chain=chain,
        plan=plan,
    )


__all__ = [
    "ADVERSARIAL_PRESENT",
    "CLEAN_ABSENT",
    "CLEAN_NULL_ABSENT",
    "DIAGNOSTIC_CASE_COUNT",
    "DIAGNOSTIC_GROUP_COUNT",
    "DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE",
    "DIAGNOSTIC_SPLIT_INVENTORY_SCHEMA",
    "DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE",
    "DIAGNOSTIC_STUDY_PLAN_SCHEMA",
    "DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE",
    "DIAGNOSTIC_STUDY_REQUEST_ID_DOMAIN",
    "DIAGNOSTIC_STUDY_REQUEST_SCHEMA",
    "DIAGNOSTIC_VARIANT_ROLES",
    "STAGEC_CAPTURE_REQUEST_MEDIA_TYPE",
    "STAGEC_CAPTURE_REQUEST_SCHEMA",
    "DiagnosticSplitInventoryArtifact",
    "DiagnosticPlannedStudyCase",
    "DiagnosticStudyCase",
    "DiagnosticStudyPlanArtifact",
    "DiagnosticStudyRequestArtifact",
    "StageCCaptureRequestArtifact",
    "build_diagnostic_split_inventory",
    "build_diagnostic_study_plan",
    "build_diagnostic_study_request",
    "load_diagnostic_split_inventory",
    "load_diagnostic_study_plan",
    "load_diagnostic_study_request",
    "load_stagec_capture_request",
]
