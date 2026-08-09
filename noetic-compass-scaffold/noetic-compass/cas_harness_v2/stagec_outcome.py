"""Exact Stage C output and post-terminal Study outcome carriers.

The two carriers in this module close a structural association gap without
claiming that the associated execution was authenticated or durably retained.
Their acyclic order is fixed as::

    capture archive -> worker output -> terminal receipt -> outcome index

The archive implementation is deliberately not imported here.  Callers pass
the expected manifest ref plus the exact seven member byte strings.  The
projection loader replays the current portable manifest and capture-artifact
contracts while leaving filesystem identity and fsync truth to the worker's
local archive loader.

Everything remains process-local, STRUCTURE_ONLY, and non-authoritative.  This
module does not execute a model, authenticate a worker, provide trusted time,
prove durable/WORM retention, open outcome bytes, create an Evidence Packet,
make a scientific decision, grant a license, authorize a product, or disclose
held material.
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
    expect_int,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
    require_unique,
)
from .preregistration import PreregistrationChain
from .study_protocol import (
    STUDY_REQUEST_MEDIA_TYPE,
    StudyCase,
    StudyPlanArtifact,
    load_study_plan,
)
from .worker_protocol import (
    WorkerAuthorizationArtifact,
    WorkerTerminalReceiptArtifact,
    load_worker_authorization,
    load_worker_terminal_receipt,
)


STAGEC_AUTHORIZATION_PROJECTION_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-authorization-projection+json"
)
STAGEC_CAPTURE_INDEX_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-capture-index+json"
)
STAGEC_CAPTURE_REQUEST_SCHEMA = "cas_harness.stagec.capture_request.v1"
STAGEC_CAPTURE_REQUEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-capture-request+json"
)
STAGEC_STUDY_REQUEST_BINDING_SCHEMA = (
    "cas_harness_v2.stagec_study_request_binding.v1"
)
STAGEC_RAW_ARRAY_MEDIA_TYPE = "application/vnd.cas-harness.ndarray.raw"
STAGEC_LOCAL_CAPTURE_ARCHIVE_SCHEMA = "cas_harness.stagec.local_capture_archive.v1"
STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-local-capture-archive+json"
)

STAGEC_WORKER_OUTPUT_SCHEMA = "cas_harness_v2.stagec_worker_output.v1"
STAGEC_WORKER_OUTPUT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-worker-output+json"
)
STAGEC_POST_TERMINAL_OUTCOME_INDEX_SCHEMA = (
    "cas_harness_v2.stagec_post_terminal_study_outcome_index.v1"
)
STAGEC_POST_TERMINAL_OUTCOME_INDEX_MEDIA_TYPE = (
    "application/vnd.cas-harness.study-outcome-index+json"
)

_AUTHORITY = {
    "scope": "STRUCTURE_ONLY",
    "authentication": "NOT_PROVIDED",
    "durable_one_use": "NOT_PROVIDED",
    "trusted_time": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "packet": "NOT_CREATED",
    "scientific_decision": "NOT_MADE",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "claim_promotion": "FORBIDDEN",
    "license": "NOT_GRANTED",
    "product": "NOT_AUTHORIZED",
    "disclosure": "HELD",
}

_WORKER_BOUNDARY = {
    "state_scope": "PROCESS_LOCAL_ONLY",
    "archive_input": "EXACT_REF_AND_BYTES_PROJECTION_ONLY",
    "archive_semantic_replay": "EXTERNAL_REQUIRED_NOT_PROVIDED",
    "creation_order": [
        "CAPTURE_ARCHIVE",
        "WORKER_OUTPUT",
        "TERMINAL_RECEIPT",
        "POST_TERMINAL_STUDY_OUTCOME_INDEX",
    ],
    "this_position": "WORKER_OUTPUT",
    "forward_references": "FORBIDDEN",
    "self_reference": "FORBIDDEN",
    "execution_order": "NOT_ATTESTED",
    "retry_evidence": "NOT_ATTESTED_NO_COMPLETE_LIFECYCLE_LEDGER",
}

_OUTCOME_BOUNDARY = {
    "state_scope": "PROCESS_LOCAL_ONLY",
    "creation_order": [
        "CAPTURE_ARCHIVE",
        "WORKER_OUTPUT",
        "TERMINAL_RECEIPT",
        "POST_TERMINAL_STUDY_OUTCOME_INDEX",
    ],
    "this_position": "POST_TERMINAL_STUDY_OUTCOME_INDEX",
    "references": "PREDECESSORS_ONLY",
    "future_chain_event_reference": "FORBIDDEN",
    "self_reference": "FORBIDDEN",
    "execution_order": "NOT_ATTESTED",
    "retry_evidence": "NOT_ATTESTED_NO_COMPLETE_LIFECYCLE_LEDGER",
}

_ARCHIVE_AUTHORITY = {
    "scope": "LOCAL_SINGLE_HOST_FILE_BACKED",
    "write_mode": "CREATE_ONLY",
    "file_sync": "FILE_FSYNC_AND_REREAD_VERIFIED_AT_CREATION",
    "permission_status": "READ_ONLY_PERMISSION_BITS_OBSERVED",
    "worm_authority": "NOT_ESTABLISHED",
    "trusted_time": "NOT_ESTABLISHED",
    "external_anchor": "NOT_ESTABLISHED",
    "capture_provenance": "NOT_CONFERRED_BY_ARCHIVE_REPLAY",
    "execution_authority": "NOT_GRANTED",
    "relocatability": "SAME_ABSOLUTE_PATH_AND_FILE_IDENTITIES_ONLY",
    "membership_scope": "MANIFEST_LISTED_MEMBERS_ONLY_CLOSED_WORLD_NOT_ESTABLISHED",
}

_ARCHIVE_SOURCE_RETENTION_BOUNDARY = (
    "CAPTURE-TIME IN_MEMORY / NOT_DURABLY_RETAINED LABELS PRESERVED; "
    "THIS MANIFEST BINDS A SEPARATE LOCAL FILE COPY"
)

_ARCHIVE_RELOCATABILITY_BOUNDARY = "SAME_ABSOLUTE_PATH_AND_FILE_IDENTITIES_ONLY"
_ARCHIVE_MEMBERSHIP_BOUNDARY = (
    "MANIFEST_LISTED_MEMBERS_ONLY / CLOSED_WORLD_DIRECTORY CONTENT NOT ESTABLISHED"
)
_ARCHIVE_PUBLICATION_BOUNDARY = (
    "THE READ_ONLY REREAD-VERIFIED MANIFEST IS THE LOCAL PUBLICATION POINT; "
    "A STOP AFTER PUBLICATION MAY LEAVE AN INTERNALLY VALID ORPHAN"
)

_ARCHIVE_MEMBER_ROLES = (
    "request_artifact",
    "authorization_projection_artifact",
    "capture_index_artifact",
    "input_ids",
    "attention_mask",
    "target_vector",
    "wrong_layer_vector",
)

_ARCHIVE_ASSOCIATION_FIELDS = (
    "study_id",
    "case_id",
    "split_id",
    "base_intent_group_id",
    "frozen_variant",
    "frozen_label",
    "invocation_id",
    "plan_id",
)

_STAGEC_VECTOR_WIDTH = 4864
_STAGEC_TARGET_LAYER = 18
_STAGEC_WRONG_LAYER = 0
_STAGEC_TARGET_MODULE_PATH = "model.layers[18].mlp.down_proj"
_STAGEC_WRONG_LAYER_MODULE_PATH = "model.layers[0].mlp.down_proj"


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_ref_bytes(
    reference: ArtifactRef,
    raw_bytes: bytes,
    *,
    media_type: str,
    path: str,
) -> None:
    if type(reference) is not ArtifactRef:
        raise SchemaValidationError(f"{path}.ref must be an exact ArtifactRef")
    if type(raw_bytes) is not bytes:
        raise SchemaValidationError(f"{path}.raw_bytes must be exact immutable bytes")
    if reference.media_type != media_type:
        raise SchemaValidationError(f"{path}.ref has the wrong exact media type")
    if not reference.verify_bytes(raw_bytes):
        raise SchemaValidationError(f"{path}.raw_bytes do not verify the exact ref")


def _unique_refs(references: tuple[ArtifactRef, ...], path: str) -> tuple[ArtifactRef, ...]:
    by_id: dict[str, ArtifactRef] = {}
    ordered: list[ArtifactRef] = []
    for reference in references:
        if type(reference) is not ArtifactRef:
            raise SchemaValidationError(f"{path} contains a non-ArtifactRef value")
        prior = by_id.get(reference.artifact_id)
        if prior is not None and prior != reference:
            raise SchemaValidationError(
                f"{path} resolves one artifact_id to conflicting exact refs"
            )
        if prior is None:
            by_id[reference.artifact_id] = reference
            ordered.append(reference)
    require_unique((item.sha256 for item in ordered), f"{path}.sha256")
    return tuple(ordered)


def _canonical_object(
    raw: bytes | bytearray | memoryview,
    path: str,
) -> tuple[bytes, dict[str, Any]]:
    snapshot, obj = load_json_object(raw)
    if snapshot != canonical_json_bytes(obj):
        raise SchemaValidationError(f"{path} must use exact canonical JSON bytes")
    return snapshot, obj


def _ref_payload(reference: ArtifactRef) -> dict[str, Any]:
    return _artifact_ref_value(reference)


def _parse_array_ref(value: Any, path: str) -> ArtifactRef:
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "artifact_id",
            "byte_length",
            "byte_order",
            "dtype",
            "durability_status",
            "format",
            "layer_index",
            "layout",
            "media_type",
            "module_path",
            "retention_location",
            "role",
            "sha256",
            "shape",
        },
        path=path,
    )
    reference = ArtifactRef(
        artifact_id=expect_machine_id(obj["artifact_id"], f"{path}.artifact_id"),
        sha256=obj["sha256"],
        byte_length=expect_int(obj["byte_length"], f"{path}.byte_length", minimum=1),
        media_type=expect_string(obj["media_type"], f"{path}.media_type", maximum=128),
    )
    if reference.media_type != STAGEC_RAW_ARRAY_MEDIA_TYPE:
        raise SchemaValidationError(f"{path}.media_type is not the Stage C raw-array type")
    if obj["format"] != "RAW C-ORDER ARRAY BYTES / NO HEADER / NO PICKLE":
        raise SchemaValidationError(f"{path}.format drifted")
    if obj["byte_order"] != "little" or obj["dtype"] not in {"<i8", "<f4"}:
        raise SchemaValidationError(f"{path} dtype/byte order drifted")
    if obj["layout"] != "C_CONTIGUOUS":
        raise SchemaValidationError(f"{path}.layout drifted")
    if (
        obj["retention_location"] != "IN_MEMORY"
        or obj["durability_status"] != "NOT_DURABLY_RETAINED"
    ):
        raise SchemaValidationError(f"{path} overclaims capture-time retention")
    shape = expect_list(obj["shape"], f"{path}.shape")
    if any(type(item) is not int or item < 1 for item in shape):
        raise SchemaValidationError(f"{path}.shape is invalid")
    item_size = 8 if obj["dtype"] == "<i8" else 4
    expected_length = item_size
    for dimension in shape:
        expected_length *= dimension
    if expected_length != reference.byte_length:
        raise SchemaValidationError(f"{path} byte length does not match dtype/shape")
    expect_string(obj["role"], f"{path}.role")
    if obj["layer_index"] is not None and type(obj["layer_index"]) is not int:
        raise SchemaValidationError(f"{path}.layer_index must be int or null")
    if obj["module_path"] is not None and type(obj["module_path"]) is not str:
        raise SchemaValidationError(f"{path}.module_path must be string or null")
    return reference


def _validate_array_role(
    value: Any,
    path: str,
    *,
    role: str,
    dtype: str,
    shape: list[int],
    layer_index: int | None,
    module_path: str | None,
) -> None:
    """Bind one raw-array ref to its exact Stage C semantic slot."""

    obj = expect_object(value, path)
    if obj["role"] != role:
        raise SchemaValidationError(f"{path}.role drifted from its Stage C slot")
    if obj["dtype"] != dtype or obj["shape"] != shape:
        raise SchemaValidationError(
            f"{path} dtype/shape drifted from its Stage C slot"
        )
    if obj["layer_index"] != layer_index or obj["module_path"] != module_path:
        raise SchemaValidationError(
            f"{path} layer/module drifted from its Stage C slot"
        )


def _load_capture_request(
    raw: bytes | bytearray | memoryview,
    *,
    reference: ArtifactRef,
) -> tuple[bytes, dict[str, Any]]:
    _require_ref_bytes(
        reference,
        bytes(raw),
        media_type=STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
        path="stagec_capture_request",
    )
    snapshot, obj = _canonical_object(raw, "Stage C capture request")
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
        path="$capture_request",
    )
    if obj["schema_version"] != STAGEC_CAPTURE_REQUEST_SCHEMA:
        raise SchemaValidationError("Stage C capture-request schema drifted")
    for field in _ARCHIVE_ASSOCIATION_FIELDS[:-1]:
        expect_machine_id(obj[field], f"$capture_request.{field}")
    if obj["frozen_variant"] != obj["frozen_label"]:
        raise SchemaValidationError("capture request variant and label must match")
    expect_string(obj["prompt"], "$capture_request.prompt")
    return snapshot, obj


@dataclass(frozen=True, slots=True, init=False)
class StageCStudyRequestBindingArtifact:
    """Exact Study-media request that points to a distinct capture request."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    study_request_id: str
    capture_request_ref: ArtifactRef
    payload: Any

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise SchemaValidationError(
            "Stage C Study-request binding construction requires its strict loader"
        )

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.study_request_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STUDY_REQUEST_MEDIA_TYPE,
        )


def load_stagec_study_request_binding(
    raw: bytes | bytearray | memoryview,
) -> StageCStudyRequestBindingArtifact:
    snapshot, obj = _canonical_object(raw, "Stage C Study-request binding")
    expect_keys(
        obj,
        required={
            "schema_version",
            "study_request_id",
            "study_id",
            "case_id",
            "split_id",
            "base_intent_group_id",
            "frozen_variant",
            "frozen_label",
            "invocation_id",
            "stagec_capture_request",
        },
        path="$study_request",
    )
    if obj["schema_version"] != STAGEC_STUDY_REQUEST_BINDING_SCHEMA:
        raise SchemaValidationError("Stage C Study-request binding schema drifted")
    study_request_id = expect_machine_id(
        obj["study_request_id"], "$study_request.study_request_id"
    )
    for field in _ARCHIVE_ASSOCIATION_FIELDS[:-1]:
        expect_machine_id(obj[field], f"$study_request.{field}")
    if obj["frozen_variant"] != obj["frozen_label"]:
        raise SchemaValidationError("Study-request variant and label must match")
    capture_request_ref = parse_artifact_ref(
        obj["stagec_capture_request"], "$study_request.stagec_capture_request"
    )
    if capture_request_ref.media_type != STAGEC_CAPTURE_REQUEST_MEDIA_TYPE:
        raise SchemaValidationError(
            "Study request must reference, not masquerade as, a Stage C capture request"
        )
    if study_request_id == capture_request_ref.artifact_id:
        raise SchemaValidationError(
            "Study request and Stage C capture request artifact IDs must be distinct"
        )
    carrier = object.__new__(StageCStudyRequestBindingArtifact)
    for field, value in (
        ("raw_bytes", snapshot),
        ("sha256", sha256_bytes(snapshot)),
        ("byte_length", len(snapshot)),
        ("study_request_id", study_request_id),
        ("capture_request_ref", capture_request_ref),
        ("payload", freeze_json(obj)),
    ):
        object.__setattr__(carrier, field, value)
    return carrier


def _validate_archive_metadata_object(value: Any, path: str, *, file: bool) -> None:
    required = (
        {
            "byte_length",
            "ctime_ns",
            "device",
            "file_attributes",
            "inode",
            "link_count",
            "mode_type",
            "mtime_ns",
            "permission_status",
            "reparse_tag",
        }
        if file
        else {"device", "file_attributes", "inode", "mode_type", "reparse_tag"}
    )
    obj = expect_object(value, path)
    expect_keys(obj, required=required, path=path)
    for key in required - {"file_attributes", "reparse_tag", "permission_status"}:
        expect_int(obj[key], f"{path}.{key}", maximum=2**63 - 1)
    for key in ("file_attributes", "reparse_tag"):
        if obj[key] is not None:
            expect_int(obj[key], f"{path}.{key}", maximum=2**63 - 1)
    if file and obj["permission_status"] != "READ_ONLY_PERMISSION_BITS_OBSERVED":
        raise SchemaValidationError(f"{path}.permission_status drifted")


@dataclass(frozen=True, slots=True, init=False)
class StageCCaptureArchiveProjection:
    """Strict portable replay of one exact seven-member local archive."""

    manifest_ref: ArtifactRef
    manifest_bytes: bytes
    capture_request_ref: ArtifactRef
    capture_request_bytes: bytes
    capture_index_ref: ArtifactRef
    capture_index_bytes: bytes
    authorization_projection_ref: ArtifactRef
    authorization_projection_bytes: bytes
    member_bytes: tuple[tuple[str, bytes], ...]
    plan_id: str
    study_id: str
    case_id: str
    split_id: str
    base_intent_group_id: str
    frozen_variant: str
    frozen_label: str
    invocation_id: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise SchemaValidationError(
            "Stage C archive projection construction requires strict seven-member replay"
        )


def load_stagec_capture_archive_projection(
    *,
    manifest_ref: ArtifactRef,
    manifest_bytes: bytes,
    member_bytes: Mapping[str, bytes],
) -> StageCCaptureArchiveProjection:
    """Replay the manifest, all seven members, and their case association.

    This verifies portable exact bytes only.  The worker archive loader remains
    responsible for filesystem identity, permissions, and local fsync evidence.
    """

    _require_ref_bytes(
        manifest_ref,
        manifest_bytes,
        media_type=STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE,
        path="archive_projection.manifest",
    )
    manifest_snapshot, manifest = _canonical_object(
        manifest_bytes, "Stage C local archive manifest"
    )
    expect_keys(
        manifest,
        required={
            "schema_version",
            "authority",
            "source_retention_boundary",
            "relocatability_boundary",
            "manifest_membership_boundary",
            "manifest_publication_boundary",
            "member_directory_fsync_status",
            "root_path",
            "root_identity",
            "association",
            "members",
        },
        path="$archive_manifest",
    )
    if manifest["schema_version"] != STAGEC_LOCAL_CAPTURE_ARCHIVE_SCHEMA:
        raise SchemaValidationError("Stage C local archive schema drifted")
    if manifest["authority"] != _ARCHIVE_AUTHORITY:
        raise SchemaValidationError("Stage C local archive authority boundary drifted")
    if manifest["source_retention_boundary"] != _ARCHIVE_SOURCE_RETENTION_BOUNDARY:
        raise SchemaValidationError("Stage C archive source-retention boundary drifted")
    if manifest["relocatability_boundary"] != _ARCHIVE_RELOCATABILITY_BOUNDARY:
        raise SchemaValidationError("Stage C archive relocatability boundary drifted")
    if manifest["manifest_membership_boundary"] != _ARCHIVE_MEMBERSHIP_BOUNDARY:
        raise SchemaValidationError("Stage C archive membership boundary drifted")
    if manifest["manifest_publication_boundary"] != _ARCHIVE_PUBLICATION_BOUNDARY:
        raise SchemaValidationError("Stage C archive publication boundary drifted")
    if manifest["member_directory_fsync_status"] not in {
        "PERFORMED",
        "UNAVAILABLE_ON_PLATFORM",
    }:
        raise SchemaValidationError("Stage C archive directory-fsync status drifted")
    expect_string(manifest["root_path"], "$archive_manifest.root_path")
    _validate_archive_metadata_object(
        manifest["root_identity"], "$archive_manifest.root_identity", file=False
    )
    association = expect_object(manifest["association"], "$archive_manifest.association")
    expect_keys(
        association,
        required=set(_ARCHIVE_ASSOCIATION_FIELDS),
        path="$archive_manifest.association",
    )
    for field in _ARCHIVE_ASSOCIATION_FIELDS:
        expect_machine_id(association[field], f"$archive_manifest.association.{field}")
    if association["frozen_variant"] != association["frozen_label"]:
        raise SchemaValidationError("archive association variant and label must match")

    if type(member_bytes) is not dict or set(member_bytes) != set(_ARCHIVE_MEMBER_ROLES):
        raise SchemaValidationError("archive member_bytes must be an exact seven-role dict")
    if any(type(value) is not bytes for value in member_bytes.values()):
        raise SchemaValidationError("archive members must be exact immutable bytes")
    rows = expect_list(manifest["members"], "$archive_manifest.members")
    if len(rows) != len(_ARCHIVE_MEMBER_ROLES):
        raise SchemaValidationError("archive manifest must contain exactly seven members")

    refs: dict[str, ArtifactRef] = {}
    ref_payloads: dict[str, dict[str, Any]] = {}
    for index, (expected_role, row_value) in enumerate(
        zip(_ARCHIVE_MEMBER_ROLES, rows, strict=True)
    ):
        path = f"$archive_manifest.members[{index}]"
        row = expect_object(row_value, path)
        expect_keys(
            row,
            required={
                "archive_copy_status",
                "file_identity",
                "path_ancestors",
                "ref",
                "relative_path",
                "role",
            },
            path=path,
        )
        if row["role"] != expected_role:
            raise SchemaValidationError("archive member role/order drifted")
        if row["archive_copy_status"] != "LOCAL_FILE_COPY_RETAINED_AND_REVALIDATED":
            raise SchemaValidationError("archive member copy status drifted")
        reference = (
            parse_artifact_ref(row["ref"], f"{path}.ref")
            if expected_role in _ARCHIVE_MEMBER_ROLES[:3]
            else _parse_array_ref(row["ref"], f"{path}.ref")
        )
        expected_media = {
            "request_artifact": STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
            "authorization_projection_artifact": STAGEC_AUTHORIZATION_PROJECTION_MEDIA_TYPE,
            "capture_index_artifact": STAGEC_CAPTURE_INDEX_MEDIA_TYPE,
        }.get(expected_role, STAGEC_RAW_ARRAY_MEDIA_TYPE)
        if reference.media_type != expected_media:
            raise SchemaValidationError(f"archive member {expected_role} media type drifted")
        raw = member_bytes[expected_role]
        if not reference.verify_bytes(raw):
            raise SchemaValidationError(f"archive member {expected_role} bytes drifted")
        expected_relative = (
            f"objects/sha256/{reference.sha256.lower()[:2]}/"
            f"{reference.sha256.lower()[2:]}"
        )
        if row["relative_path"] != expected_relative:
            raise SchemaValidationError("archive member is not at its content address")
        _validate_archive_metadata_object(
            row["file_identity"], f"{path}.file_identity", file=True
        )
        if row["file_identity"]["byte_length"] != reference.byte_length:
            raise SchemaValidationError(
                "archive member file identity byte length drifted from its ref"
            )
        ancestors = expect_list(row["path_ancestors"], f"{path}.path_ancestors")
        expected_ancestors = [
            ".",
            "objects",
            "objects/sha256",
            f"objects/sha256/{reference.sha256.lower()[:2]}",
        ]
        if len(ancestors) != len(expected_ancestors):
            raise SchemaValidationError("archive member path ancestors are incomplete")
        for ancestor_index, ancestor_value in enumerate(ancestors):
            ancestor_path = f"{path}.path_ancestors[{ancestor_index}]"
            ancestor = expect_object(ancestor_value, ancestor_path)
            expect_keys(
                ancestor,
                required={"identity", "relative_path"},
                path=ancestor_path,
            )
            expect_string(
                ancestor["relative_path"],
                f"{ancestor_path}.relative_path",
                nonempty=False,
            )
            if ancestor["relative_path"] != expected_ancestors[ancestor_index]:
                raise SchemaValidationError(
                    "archive member ancestor ordering/path drifted"
                )
            _validate_archive_metadata_object(
                ancestor["identity"], f"{ancestor_path}.identity", file=False
            )
        refs[expected_role] = reference
        ref_payloads[expected_role] = row["ref"]

    _unique_refs(tuple(refs.values()) + (manifest_ref,), "archive_projection.refs")
    expected_manifest_id = (
        "stagec-local-archive-"
        + sha256_bytes(
            canonical_json_bytes(_artifact_ref_value(refs["capture_index_artifact"]))
        ).lower()
    )
    if manifest_ref.artifact_id != expected_manifest_id:
        raise SchemaValidationError(
            "archive manifest artifact ID is not bound to the capture-index ref"
        )
    capture_request_bytes, request = _load_capture_request(
        member_bytes["request_artifact"], reference=refs["request_artifact"]
    )
    authorization_bytes, authorization = _canonical_object(
        member_bytes["authorization_projection_artifact"],
        "Stage C authorization projection",
    )
    expect_keys(
        authorization,
        required={
            "schema_version",
            "scope",
            "authority_status",
            "request_sha256",
            "plan_id",
            "study_id",
            "case_id",
            "invocation_id",
        },
        path="$stagec_authorization_projection",
    )
    if authorization["schema_version"] != "cas_harness.stagec.authorization_projection.v1":
        raise SchemaValidationError("Stage C authorization-projection schema drifted")
    if (
        authorization["scope"] != "STRUCTURE_ONLY"
        or authorization["authority_status"]
        != "NON_AUTHORITY / DOES_NOT_AUTHORIZE_MODEL_EXECUTION"
    ):
        raise SchemaValidationError("Stage C authorization projection overclaims authority")
    if authorization["request_sha256"] != refs["request_artifact"].sha256:
        raise SchemaValidationError("authorization projection binds a different capture request")
    for field in ("plan_id", "study_id", "case_id", "invocation_id"):
        expect_machine_id(authorization[field], f"$stagec_authorization_projection.{field}")
    for field in ("study_id", "case_id", "invocation_id"):
        if authorization[field] != request[field]:
            raise SchemaValidationError(
                f"authorization projection/capture request drifted at {field}"
            )

    index_bytes, capture_index = _canonical_object(
        member_bytes["capture_index_artifact"], "Stage C capture index"
    )
    expect_keys(
        capture_index,
        required={
            "schema_version",
            "scope",
            "retention",
            "association",
            "identity",
            "prompt",
            "tokens",
            "activations",
            "logits",
            "hooks",
            "endpoint_checks",
            "telemetry",
        },
        path="$capture_index",
    )
    if (
        capture_index["schema_version"] != "cas_harness.stagec.capture_index.v1"
        or capture_index["scope"] != "STRUCTURE_ONLY"
    ):
        raise SchemaValidationError("Stage C capture-index schema/scope drifted")
    if capture_index["retention"] != {
        "location": "IN_MEMORY",
        "durability_status": "NOT_DURABLY_RETAINED",
    }:
        raise SchemaValidationError("Stage C capture index overclaims retention")
    index_association = expect_object(
        capture_index["association"], "$capture_index.association"
    )
    expect_keys(
        index_association,
        required={
            *_ARCHIVE_ASSOCIATION_FIELDS,
            "request_artifact",
            "authorization_projection_artifact",
        },
        path="$capture_index.association",
    )
    for field in _ARCHIVE_ASSOCIATION_FIELDS:
        expected = authorization["plan_id"] if field == "plan_id" else request[field]
        if index_association[field] != expected or association[field] != expected:
            raise SchemaValidationError(f"archive/index/request association drifted at {field}")
    if index_association["request_artifact"] != ref_payloads["request_artifact"]:
        raise SchemaValidationError("capture index binds a different capture request")
    if (
        index_association["authorization_projection_artifact"]
        != ref_payloads["authorization_projection_artifact"]
    ):
        raise SchemaValidationError("capture index binds a different authorization projection")
    tokens = expect_object(capture_index["tokens"], "$capture_index.tokens")
    expect_keys(
        tokens,
        required={
            "input_ids_artifact",
            "attention_mask_artifact",
            "sequence_length",
            "final_prompt_token_index",
            "final_prompt_token_id",
            "truncation_enabled",
            "truncation_occurred",
        },
        path="$capture_index.tokens",
    )
    if (
        tokens["input_ids_artifact"] != ref_payloads["input_ids"]
        or tokens["attention_mask_artifact"] != ref_payloads["attention_mask"]
    ):
        raise SchemaValidationError("capture index token-array refs drifted from archive")
    sequence_length = expect_int(
        tokens["sequence_length"],
        "$capture_index.tokens.sequence_length",
        minimum=1,
    )
    final_prompt_token_index = expect_int(
        tokens["final_prompt_token_index"],
        "$capture_index.tokens.final_prompt_token_index",
    )
    expect_int(
        tokens["final_prompt_token_id"],
        "$capture_index.tokens.final_prompt_token_id",
    )
    if final_prompt_token_index != sequence_length - 1:
        raise SchemaValidationError(
            "capture index final prompt token does not bind the sequence end"
        )
    if (
        type(tokens["truncation_enabled"]) is not bool
        or type(tokens["truncation_occurred"]) is not bool
        or tokens["truncation_enabled"]
        or tokens["truncation_occurred"]
    ):
        raise SchemaValidationError("capture index token truncation contract drifted")
    _validate_array_role(
        ref_payloads["input_ids"],
        "$archive_manifest.members.input_ids.ref",
        role="input_ids",
        dtype="<i8",
        shape=[1, sequence_length],
        layer_index=None,
        module_path=None,
    )
    _validate_array_role(
        ref_payloads["attention_mask"],
        "$archive_manifest.members.attention_mask.ref",
        role="attention_mask",
        dtype="<i8",
        shape=[1, sequence_length],
        layer_index=None,
        module_path=None,
    )
    activations = expect_object(capture_index["activations"], "$capture_index.activations")
    expect_keys(
        activations,
        required={"target", "wrong_layer"},
        path="$capture_index.activations",
    )
    target = expect_object(
        activations["target"], "$capture_index.activations.target"
    )
    wrong = expect_object(
        activations["wrong_layer"], "$capture_index.activations.wrong_layer"
    )
    activation_keys = {
        "array_artifact",
        "layer_index",
        "module_path",
        "source_dtype",
        "source_device",
        "source_autocast_enabled",
    }
    expect_keys(
        target,
        required=activation_keys,
        path="$capture_index.activations.target",
    )
    expect_keys(
        wrong,
        required=activation_keys,
        path="$capture_index.activations.wrong_layer",
    )
    if (
        target["array_artifact"] != ref_payloads["target_vector"]
        or wrong["array_artifact"] != ref_payloads["wrong_layer_vector"]
    ):
        raise SchemaValidationError("capture index activation-array refs drifted from archive")
    expected_activation_slots = (
        (
            target,
            "target_vector",
            "target_final_token_activation",
            _STAGEC_TARGET_LAYER,
            _STAGEC_TARGET_MODULE_PATH,
        ),
        (
            wrong,
            "wrong_layer_vector",
            "wrong_layer_final_token_activation",
            _STAGEC_WRONG_LAYER,
            _STAGEC_WRONG_LAYER_MODULE_PATH,
        ),
    )
    for item, member_role, array_role, layer, module in expected_activation_slots:
        if item["layer_index"] != layer or item["module_path"] != module:
            raise SchemaValidationError(
                f"capture index activation {member_role} layer/module drifted"
            )
        expect_string(item["source_dtype"], f"$capture_index.{member_role}.source_dtype")
        expect_string(item["source_device"], f"$capture_index.{member_role}.source_device")
        if type(item["source_autocast_enabled"]) is not bool:
            raise SchemaValidationError(
                f"capture index activation {member_role} autocast flag drifted"
            )
        _validate_array_role(
            ref_payloads[member_role],
            f"$archive_manifest.members.{member_role}.ref",
            role=array_role,
            dtype="<f4",
            shape=[_STAGEC_VECTOR_WIDTH],
            layer_index=layer,
            module_path=module,
        )

    carrier = object.__new__(StageCCaptureArchiveProjection)
    values = {
        "manifest_ref": manifest_ref,
        "manifest_bytes": manifest_snapshot,
        "capture_request_ref": refs["request_artifact"],
        "capture_request_bytes": capture_request_bytes,
        "capture_index_ref": refs["capture_index_artifact"],
        "capture_index_bytes": index_bytes,
        "authorization_projection_ref": refs["authorization_projection_artifact"],
        "authorization_projection_bytes": authorization_bytes,
        "member_bytes": tuple((role, member_bytes[role]) for role in _ARCHIVE_MEMBER_ROLES),
        **{field: association[field] for field in _ARCHIVE_ASSOCIATION_FIELDS},
    }
    for field, value in values.items():
        object.__setattr__(carrier, field, value)
    return carrier


def _replay_archive_projection(
    archive: StageCCaptureArchiveProjection,
) -> StageCCaptureArchiveProjection:
    if type(archive) is not StageCCaptureArchiveProjection:
        raise SchemaValidationError("archive must be an exact StageCCaptureArchiveProjection")
    replayed = load_stagec_capture_archive_projection(
        manifest_ref=archive.manifest_ref,
        manifest_bytes=archive.manifest_bytes,
        member_bytes=dict(archive.member_bytes),
    )
    if replayed != archive:
        raise SchemaValidationError("archive projection does not match strict seven-member replay")
    return replayed


@dataclass(frozen=True, slots=True)
class StageCWorkerOutputArtifact:
    """Exact worker-output envelope created only after archive commit."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    output_id: str
    output_name: str
    case_id: str
    plan_case_ordinal: int
    payload: Any
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.output_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_WORKER_OUTPUT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class StageCPostTerminalChild:
    """Exact inputs for one fixed Study case in the controller index."""

    case_id: str
    request_bytes: bytes
    authorization: WorkerAuthorizationArtifact
    archive: StageCCaptureArchiveProjection
    worker_output: StageCWorkerOutputArtifact
    terminal_receipt: WorkerTerminalReceiptArtifact

    def __post_init__(self) -> None:
        expect_machine_id(self.case_id, "post_terminal_child.case_id")
        if type(self.request_bytes) is not bytes:
            raise SchemaValidationError(
                "post_terminal_child.request_bytes must be exact immutable bytes"
            )
        if type(self.authorization) is not WorkerAuthorizationArtifact:
            raise SchemaValidationError(
                "post_terminal_child.authorization must be an exact carrier"
            )
        if type(self.archive) is not StageCCaptureArchiveProjection:
            raise SchemaValidationError(
                "post_terminal_child.archive must be an exact projection"
            )
        if type(self.worker_output) is not StageCWorkerOutputArtifact:
            raise SchemaValidationError(
                "post_terminal_child.worker_output must be an exact carrier"
            )
        if type(self.terminal_receipt) is not WorkerTerminalReceiptArtifact:
            raise SchemaValidationError(
                "post_terminal_child.terminal_receipt must be an exact carrier"
            )


@dataclass(frozen=True, slots=True)
class StageCPostTerminalOutcomeIndexArtifact:
    """Controller-authored exact post-terminal Study outcome index."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    outcome_index_id: str
    accessed_at: str
    execution_completed_at: str
    ordered_terminal_receipts: tuple[ArtifactRef, ...]
    payload: Any
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.outcome_index_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_POST_TERMINAL_OUTCOME_INDEX_MEDIA_TYPE,
        )

    @property
    def outcome_access_receipt_ref(self) -> ArtifactRef:
        """Exact ref that the preregistration chain must bind after creation."""

        return self.artifact_ref


def _pre_outcome_view(chain: PreregistrationChain) -> PreregistrationChain:
    """Reconstruct the exact pre-outcome chain, including after aggregate seal."""

    if type(chain) is not PreregistrationChain:
        raise SchemaValidationError("chain must be an exact PreregistrationChain")
    chain.assert_integrity()
    replay = PreregistrationChain(chain.base)
    for amendment in chain.amendments:
        replay.append_amendment(amendment.raw_bytes)
    replay.assert_integrity()
    return replay


def _same_plan(left: StudyPlanArtifact, right: StudyPlanArtifact) -> bool:
    return (
        type(left) is StudyPlanArtifact
        and type(right) is StudyPlanArtifact
        and left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.study_id == right.study_id
        and left.created_at == right.created_at
        and left.pre_outcome_chain_sha256 == right.pre_outcome_chain_sha256
        and left.study_phase == right.study_phase
        and left.split_packages == right.split_packages
        and left.cases == right.cases
        and left.expected_counts == right.expected_counts
        and canonical_sha256(left.payload) == canonical_sha256(right.payload)
        and left.artifact_refs == right.artifact_refs
    )


def _replay_plan(
    plan: StudyPlanArtifact,
    *,
    pre_outcome_chain: PreregistrationChain,
) -> StudyPlanArtifact:
    if type(plan) is not StudyPlanArtifact:
        raise SchemaValidationError("plan must be an exact StudyPlanArtifact")
    replayed = load_study_plan(plan.raw_bytes, chain=pre_outcome_chain)
    if not _same_plan(replayed, plan):
        raise SchemaValidationError(
            "Study plan does not match a fresh exact-byte loader replay"
        )
    return replayed


def _case_and_ordinal(
    plan: StudyPlanArtifact,
    case_id: str,
) -> tuple[StudyCase, int]:
    case_id = expect_machine_id(case_id, "case_id")
    matches = tuple(
        (case, index + 1)
        for index, case in enumerate(plan.cases)
        if case.case_id == case_id
    )
    if len(matches) != 1:
        raise SchemaValidationError("case_id must identify exactly one planned Study case")
    return matches[0]


def _same_authorization(
    left: WorkerAuthorizationArtifact,
    right: WorkerAuthorizationArtifact,
) -> bool:
    return (
        type(left) is WorkerAuthorizationArtifact
        and type(right) is WorkerAuthorizationArtifact
        and left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.authorization_id == right.authorization_id
        and left.issued_at == right.issued_at
        and left.expires_at == right.expires_at
        and left.run_nonce_b64url == right.run_nonce_b64url
        and canonical_sha256(left.payload) == canonical_sha256(right.payload)
        and left.artifact_refs == right.artifact_refs
    )


def _replay_authorization(
    authorization: WorkerAuthorizationArtifact,
    *,
    pre_outcome_chain: PreregistrationChain,
    plan: StudyPlanArtifact,
    case: StudyCase,
) -> tuple[WorkerAuthorizationArtifact, str]:
    if type(authorization) is not WorkerAuthorizationArtifact:
        raise SchemaValidationError(
            "authorization must be an exact WorkerAuthorizationArtifact"
        )
    replayed = load_worker_authorization(
        authorization.raw_bytes,
        chain=pre_outcome_chain,
    )
    if not _same_authorization(replayed, authorization):
        raise SchemaValidationError(
            "authorization does not match a fresh exact-byte loader replay"
        )
    if _time(replayed.issued_at) <= _time(plan.created_at):
        raise SchemaValidationError(
            "authorization must be issued after the exact parent Study plan"
        )
    mapping = replayed.payload["execution_mapping"]
    expected_mapping = {
        "job_id": case.case_id,
        "audit_id": f"study-plan-{plan.sha256}",
        "shard_id": f"study-request-{case.request.sha256}",
        "fleet_id": (
            "study-counts-" + canonical_sha256(case.expected_counts.as_value())
        ),
    }
    for field, expected in expected_mapping.items():
        if mapping[field] != expected:
            raise SchemaValidationError(
                f"authorization execution_mapping.{field} does not exactly bind the Study case"
            )
    expected_outputs = mapping["expected_outputs"]
    if type(expected_outputs) is not tuple or len(expected_outputs) != 1:
        raise SchemaValidationError(
            "Stage C worker output requires exactly one authorized terminal output"
        )
    return replayed, expect_machine_id(
        expected_outputs[0],
        "authorization.execution_mapping.expected_outputs[0]",
    )


def _validate_request(
    request_bytes: bytes,
    *,
    case: StudyCase,
) -> StageCStudyRequestBindingArtifact:
    if type(request_bytes) is not bytes:
        raise SchemaValidationError("request_bytes must be exact immutable bytes")
    if not case.request.verify_bytes(request_bytes):
        raise SchemaValidationError(
            "request bytes do not verify the exact predeclared Study request ref"
        )
    binding = load_stagec_study_request_binding(request_bytes)
    if binding.artifact_ref != case.request:
        raise SchemaValidationError(
            "Study-request binding does not replay the exact planned request ref"
        )
    expected = {
        "case_id": case.case_id,
        "split_id": case.split_id,
        "base_intent_group_id": case.group_id,
        "frozen_variant": case.variant_role,
        "frozen_label": case.variant_role,
    }
    for field, value in expected.items():
        if binding.payload[field] != value:
            raise SchemaValidationError(
                f"Study-request binding {field} does not replay the planned case"
            )
    return binding


def _validate_archive(
    archive: StageCCaptureArchiveProjection,
    *,
    plan: StudyPlanArtifact,
    case: StudyCase,
    study_request: StageCStudyRequestBindingArtifact,
) -> StageCCaptureArchiveProjection:
    archive = _replay_archive_projection(archive)
    expected = {
        "plan_id": plan.study_id,
        "study_id": plan.study_id,
        "case_id": case.case_id,
        "split_id": case.split_id,
        "base_intent_group_id": case.group_id,
        "frozen_variant": case.variant_role,
        "frozen_label": case.variant_role,
    }
    for field, value in expected.items():
        if getattr(archive, field) != value:
            raise SchemaValidationError(
                f"archive projection {field} does not exactly replay the Study case"
            )
    if study_request.payload["study_id"] != plan.study_id:
        raise SchemaValidationError("Study-request binding study_id drifted from plan")
    if study_request.capture_request_ref != archive.capture_request_ref:
        raise SchemaValidationError(
            "Study request does not bind the exact archived Stage C capture request"
        )
    for field in _ARCHIVE_ASSOCIATION_FIELDS[:-1]:
        if study_request.payload[field] != getattr(archive, field):
            raise SchemaValidationError(
                f"Study/capture request association drifted at {field}"
            )
    return archive


def _worker_context(
    *,
    chain: PreregistrationChain,
    plan: StudyPlanArtifact,
    case_id: str,
    request_bytes: bytes,
    authorization: WorkerAuthorizationArtifact,
    archive: StageCCaptureArchiveProjection,
    output_id: str,
) -> tuple[
    PreregistrationChain,
    StudyPlanArtifact,
    StudyCase,
    int,
    WorkerAuthorizationArtifact,
    str,
    tuple[ArtifactRef, ...],
]:
    pre_outcome_chain = _pre_outcome_view(chain)
    replayed_plan = _replay_plan(plan, pre_outcome_chain=pre_outcome_chain)
    case, ordinal = _case_and_ordinal(replayed_plan, case_id)
    study_request = _validate_request(request_bytes, case=case)
    replayed_authorization, output_name = _replay_authorization(
        authorization,
        pre_outcome_chain=pre_outcome_chain,
        plan=replayed_plan,
        case=case,
    )
    archive = _validate_archive(
        archive,
        plan=replayed_plan,
        case=case,
        study_request=study_request,
    )

    output_id = expect_machine_id(output_id, "output_id")
    bound_refs = _unique_refs(
        (
            replayed_plan.artifact_ref,
            case.request,
            archive.capture_request_ref,
            replayed_authorization.artifact_ref,
            archive.authorization_projection_ref,
            archive.capture_index_ref,
            archive.manifest_ref,
        ),
        "worker_output.refs",
    )
    existing_ids = {
        *(item.artifact_id for item in pre_outcome_chain.artifact_refs),
        *(item.artifact_id for item in bound_refs),
    }
    if output_id in existing_ids:
        raise SchemaValidationError(
            "output_id collides with a predecessor artifact; self/cycle ambiguity forbidden"
        )
    return (
        pre_outcome_chain,
        replayed_plan,
        case,
        ordinal,
        replayed_authorization,
        output_name,
        bound_refs,
    )


def _worker_output_value(
    *,
    chain: PreregistrationChain,
    plan: StudyPlanArtifact,
    case_id: str,
    request_bytes: bytes,
    authorization: WorkerAuthorizationArtifact,
    archive: StageCCaptureArchiveProjection,
    output_id: str,
) -> tuple[dict[str, Any], str, int, tuple[ArtifactRef, ...]]:
    (
        pre_outcome_chain,
        replayed_plan,
        case,
        ordinal,
        replayed_authorization,
        output_name,
        refs,
    ) = _worker_context(
        chain=chain,
        plan=plan,
        case_id=case_id,
        request_bytes=request_bytes,
        authorization=authorization,
        archive=archive,
        output_id=output_id,
    )
    value = {
        "schema_version": STAGEC_WORKER_OUTPUT_SCHEMA,
        "output_id": output_id,
        "study_binding": {
            "study_plan": _artifact_ref_value(replayed_plan.artifact_ref),
            "pre_outcome_chain_sha256": pre_outcome_chain.chain_sha256,
        },
        "association": {
            "study_id": replayed_plan.study_id,
            "case_id": case.case_id,
            "split_id": case.split_id,
            "base_intent_group_id": case.group_id,
            "frozen_variant": case.variant_role,
            "frozen_label": archive.frozen_label,
            "invocation_id": archive.invocation_id,
            "plan_case_ordinal": ordinal,
            "execution_ordinal": "NOT_ATTESTED",
            "ordinal_semantic": "PLAN_INVENTORY_ONLY_NOT_OBSERVED_EXECUTION_ORDER",
        },
        "study_request": _artifact_ref_value(case.request),
        "stagec_capture_request": _artifact_ref_value(archive.capture_request_ref),
        "worker_authorization": _artifact_ref_value(
            replayed_authorization.artifact_ref
        ),
        "stagec_authorization_projection": _artifact_ref_value(
            archive.authorization_projection_ref
        ),
        "capture_index": _artifact_ref_value(archive.capture_index_ref),
        "archive_manifest": _artifact_ref_value(archive.manifest_ref),
        "terminal_output_name": output_name,
        "boundary": thaw_json(_WORKER_BOUNDARY),
        "authority": dict(_AUTHORITY),
        "governance": thaw_json(pre_outcome_chain.base.payload["governance"]),
    }
    return value, output_name, ordinal, refs


def load_stagec_worker_output(
    raw: bytes | bytearray | memoryview,
    *,
    chain: PreregistrationChain,
    plan: StudyPlanArtifact,
    case_id: str,
    request_bytes: bytes,
    authorization: WorkerAuthorizationArtifact,
    archive: StageCCaptureArchiveProjection,
) -> StageCWorkerOutputArtifact:
    """Strict-load one canonical envelope against every predecessor carrier."""

    snapshot, obj = load_json_object(raw)
    if snapshot != canonical_json_bytes(obj):
        raise SchemaValidationError(
            "Stage C worker output must use exact canonical JSON bytes"
        )
    expect_keys(
        obj,
        required={
            "schema_version",
            "output_id",
            "study_binding",
            "association",
            "study_request",
            "stagec_capture_request",
            "worker_authorization",
            "stagec_authorization_projection",
            "capture_index",
            "archive_manifest",
            "terminal_output_name",
            "boundary",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_WORKER_OUTPUT_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {STAGEC_WORKER_OUTPUT_SCHEMA!r}"
        )
    output_id = expect_machine_id(obj["output_id"], "$.output_id")
    expected, output_name, ordinal, refs = _worker_output_value(
        chain=chain,
        plan=plan,
        case_id=case_id,
        request_bytes=request_bytes,
        authorization=authorization,
        archive=archive,
        output_id=output_id,
    )
    if obj != expected:
        raise SchemaValidationError(
            "Stage C worker output does not exactly replay its "
            "plan/case/request/auth/archive inputs"
        )
    return StageCWorkerOutputArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        output_id=output_id,
        output_name=output_name,
        case_id=case_id,
        plan_case_ordinal=ordinal,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def build_stagec_worker_output(
    *,
    chain: PreregistrationChain,
    plan: StudyPlanArtifact,
    case_id: str,
    request_bytes: bytes,
    authorization: WorkerAuthorizationArtifact,
    archive: StageCCaptureArchiveProjection,
    output_id: str,
) -> StageCWorkerOutputArtifact:
    """Build after archive commit and immediately strict-replay the envelope."""

    if type(chain) is not PreregistrationChain:
        raise SchemaValidationError("chain must be an exact PreregistrationChain")
    chain.assert_integrity()
    if chain.outcome_access is not None:
        raise SchemaValidationError(
            "a new worker output cannot be built after outcome-access finalization"
        )
    value, _, _, _ = _worker_output_value(
        chain=chain,
        plan=plan,
        case_id=case_id,
        request_bytes=request_bytes,
        authorization=authorization,
        archive=archive,
        output_id=output_id,
    )
    return load_stagec_worker_output(
        canonical_json_bytes(value),
        chain=chain,
        plan=plan,
        case_id=case_id,
        request_bytes=request_bytes,
        authorization=authorization,
        archive=archive,
    )


def _same_worker_output(
    left: StageCWorkerOutputArtifact,
    right: StageCWorkerOutputArtifact,
) -> bool:
    return (
        type(left) is StageCWorkerOutputArtifact
        and type(right) is StageCWorkerOutputArtifact
        and left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.output_id == right.output_id
        and left.output_name == right.output_name
        and left.case_id == right.case_id
        and left.plan_case_ordinal == right.plan_case_ordinal
        and canonical_sha256(left.payload) == canonical_sha256(right.payload)
        and left.artifact_refs == right.artifact_refs
    )


def _same_terminal(
    left: WorkerTerminalReceiptArtifact,
    right: WorkerTerminalReceiptArtifact,
) -> bool:
    return (
        type(left) is WorkerTerminalReceiptArtifact
        and type(right) is WorkerTerminalReceiptArtifact
        and left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.receipt_id == right.receipt_id
        and left.terminal_status == right.terminal_status
        and left.worker_started_at == right.worker_started_at
        and left.terminal_at == right.terminal_at
        and left.authorization_sha256 == right.authorization_sha256
        and canonical_sha256(left.payload) == canonical_sha256(right.payload)
        and left.outcome_artifact_refs == right.outcome_artifact_refs
        and left.artifact_refs == right.artifact_refs
    )


def _outcome_index_value(
    *,
    chain: PreregistrationChain,
    plan: StudyPlanArtifact,
    children: tuple[StageCPostTerminalChild, ...],
    outcome_index_id: str,
    accessed_at: str,
) -> tuple[
    dict[str, Any],
    str,
    tuple[ArtifactRef, ...],
    tuple[ArtifactRef, ...],
]:
    pre_outcome_chain = _pre_outcome_view(chain)
    replayed_plan = _replay_plan(plan, pre_outcome_chain=pre_outcome_chain)
    if type(children) is not tuple or any(
        type(item) is not StageCPostTerminalChild for item in children
    ):
        raise SchemaValidationError(
            "children must be an exact tuple of StageCPostTerminalChild values"
        )
    if len(children) != len(replayed_plan.cases):
        raise SchemaValidationError(
            "outcome index requires every fixed Study case exactly once"
        )

    rows: list[dict[str, Any]] = []
    refs: list[ArtifactRef] = [replayed_plan.artifact_ref]
    receipts: list[ArtifactRef] = []
    terminal_times: list[str] = []
    replayed_authorizations: list[WorkerAuthorizationArtifact] = []
    replayed_outputs: list[StageCWorkerOutputArtifact] = []

    for index, (case, child) in enumerate(
        zip(replayed_plan.cases, children, strict=True),
        start=1,
    ):
        if child.case_id != case.case_id:
            raise SchemaValidationError(
                "outcome children must follow the exact fixed case-inventory order"
            )
        replayed_archive = _replay_archive_projection(child.archive)
        replayed_output = load_stagec_worker_output(
            child.worker_output.raw_bytes,
            chain=chain,
            plan=replayed_plan,
            case_id=case.case_id,
            request_bytes=child.request_bytes,
            authorization=child.authorization,
            archive=replayed_archive,
        )
        if not _same_worker_output(replayed_output, child.worker_output):
            raise SchemaValidationError(
                "child worker output does not match fresh exact-byte replay"
            )
        replayed_authorization, output_name = _replay_authorization(
            child.authorization,
            pre_outcome_chain=pre_outcome_chain,
            plan=replayed_plan,
            case=case,
        )
        replayed_terminal = load_worker_terminal_receipt(
            child.terminal_receipt.raw_bytes,
            authorization=replayed_authorization,
            chain=pre_outcome_chain,
        )
        if not _same_terminal(replayed_terminal, child.terminal_receipt):
            raise SchemaValidationError(
                "child terminal receipt does not match fresh exact-byte replay"
            )
        if replayed_terminal.terminal_status != "COMPLETED":
            raise SchemaValidationError(
                "post-terminal Study outcome accepts only exact COMPLETED receipts"
            )
        if replayed_terminal.outcome_artifact_refs != (replayed_output.artifact_ref,):
            raise SchemaValidationError(
                "terminal receipt must bind only the exact Stage C worker output envelope"
            )
        produced = replayed_terminal.payload["terminal"]["produced_outputs"]
        if (
            len(produced) != 1
            or produced[0]["output_name"] != output_name
            or replayed_output.output_name != output_name
        ):
            raise SchemaValidationError(
                "terminal output name does not exactly replay the authorization/output envelope"
            )
        if replayed_output.plan_case_ordinal != index:
            raise SchemaValidationError(
                "worker output plan-case ordinal is not derived from plan order"
            )

        row = {
            "study_id": replayed_plan.study_id,
            "case_id": case.case_id,
            "split_id": case.split_id,
            "base_intent_group_id": case.group_id,
            "frozen_variant": case.variant_role,
            "frozen_label": replayed_archive.frozen_label,
            "study_request": _artifact_ref_value(case.request),
            "stagec_capture_request": _artifact_ref_value(
                replayed_archive.capture_request_ref
            ),
            "worker_authorization": _artifact_ref_value(
                replayed_authorization.artifact_ref
            ),
            "stagec_authorization_projection": _artifact_ref_value(
                replayed_archive.authorization_projection_ref
            ),
            "invocation_id": replayed_archive.invocation_id,
            "capture_index": _artifact_ref_value(replayed_archive.capture_index_ref),
            "archive_manifest": _artifact_ref_value(replayed_archive.manifest_ref),
            "worker_output": _artifact_ref_value(replayed_output.artifact_ref),
            "terminal_receipt": _artifact_ref_value(
                replayed_terminal.artifact_ref
            ),
            "terminal_disposition": "COMPLETED",
            "plan_case_ordinal": index,
            "execution_ordinal": "NOT_ATTESTED",
            "retry_count": "NOT_ATTESTED",
        }
        rows.append(row)
        refs.extend(
            (
                case.request,
                replayed_archive.capture_request_ref,
                replayed_authorization.artifact_ref,
                replayed_archive.authorization_projection_ref,
                replayed_archive.capture_index_ref,
                replayed_archive.manifest_ref,
                replayed_output.artifact_ref,
                replayed_terminal.artifact_ref,
            )
        )
        receipts.append(replayed_terminal.artifact_ref)
        terminal_times.append(replayed_terminal.terminal_at)
        replayed_authorizations.append(replayed_authorization)
        replayed_outputs.append(replayed_output)

    for values, path in (
        (
            tuple(item.authorization_id for item in replayed_authorizations),
            "outcome_index.worker_authorization.artifact_id",
        ),
        (
            tuple(item.sha256 for item in replayed_authorizations),
            "outcome_index.worker_authorization.sha256",
        ),
        (
            tuple(item.run_nonce_b64url for item in replayed_authorizations),
            "outcome_index.worker_authorization.run_nonce",
        ),
        (
            tuple(item.receipt_id for item in (child.terminal_receipt for child in children)),
            "outcome_index.terminal_receipt.artifact_id",
        ),
        (
            tuple(item.sha256 for item in (child.terminal_receipt for child in children)),
            "outcome_index.terminal_receipt.sha256",
        ),
        (
            tuple(item.output_id for item in replayed_outputs),
            "outcome_index.worker_output.artifact_id",
        ),
        (
            tuple(item.sha256 for item in replayed_outputs),
            "outcome_index.worker_output.sha256",
        ),
        (
            tuple(child.archive.manifest_ref.artifact_id for child in children),
            "outcome_index.archive_manifest.artifact_id",
        ),
        (
            tuple(child.archive.manifest_ref.sha256 for child in children),
            "outcome_index.archive_manifest.sha256",
        ),
        (
            tuple(child.archive.capture_index_ref.artifact_id for child in children),
            "outcome_index.capture_index.artifact_id",
        ),
        (
            tuple(child.archive.capture_index_ref.sha256 for child in children),
            "outcome_index.capture_index.sha256",
        ),
        (
            tuple(
                child.archive.authorization_projection_ref.artifact_id
                for child in children
            ),
            "outcome_index.stagec_authorization_projection.artifact_id",
        ),
        (
            tuple(
                child.archive.authorization_projection_ref.sha256
                for child in children
            ),
            "outcome_index.stagec_authorization_projection.sha256",
        ),
        (
            tuple(child.archive.invocation_id for child in children),
            "outcome_index.invocation_id",
        ),
    ):
        require_unique(values, path)

    execution_completed_at = max(terminal_times, key=_time)
    accessed_at = expect_timestamp(accessed_at, "outcome_index.accessed_at")
    if _time(accessed_at) <= _time(execution_completed_at):
        raise SchemaValidationError(
            "Study outcome access must be strictly after the latest child terminal"
        )
    outcome_index_id = expect_machine_id(
        outcome_index_id,
        "outcome_index.outcome_index_id",
    )
    unique_refs = _unique_refs(tuple(refs), "outcome_index.refs")
    existing_ids = {
        *(item.artifact_id for item in pre_outcome_chain.artifact_refs),
        *(item.artifact_id for item in unique_refs),
    }
    if outcome_index_id in existing_ids:
        raise SchemaValidationError(
            "outcome_index_id collides with a predecessor artifact; self-reference forbidden"
        )

    value = {
        "schema_version": STAGEC_POST_TERMINAL_OUTCOME_INDEX_SCHEMA,
        "outcome_index_id": outcome_index_id,
        "study_binding": {
            "study_plan": _artifact_ref_value(replayed_plan.artifact_ref),
            "pre_outcome_chain_sha256": pre_outcome_chain.chain_sha256,
            "ordered_case_count": len(replayed_plan.cases),
        },
        "outcome_access": {
            "accessed_at": accessed_at,
            "execution_completed_at": execution_completed_at,
            "receipt_role": "THIS_OUTCOME_INDEX_ARTIFACT",
            "chain_finalization": "CALLER_MUST_BIND_EXACT_ARTIFACT_REF_AFTER_CREATION",
        },
        "ordered_case_outcomes": rows,
        "boundary": thaw_json(_OUTCOME_BOUNDARY),
        "authority": dict(_AUTHORITY),
        "governance": thaw_json(pre_outcome_chain.base.payload["governance"]),
    }
    return value, execution_completed_at, unique_refs, tuple(receipts)


def load_stagec_post_terminal_outcome_index(
    raw: bytes | bytearray | memoryview,
    *,
    chain: PreregistrationChain,
    plan: StudyPlanArtifact,
    children: tuple[StageCPostTerminalChild, ...],
) -> StageCPostTerminalOutcomeIndexArtifact:
    """Strict-load an aggregate index before or after exact chain finalization."""

    snapshot, obj = load_json_object(raw)
    if snapshot != canonical_json_bytes(obj):
        raise SchemaValidationError(
            "Stage C post-terminal outcome index must use exact canonical JSON bytes"
        )
    expect_keys(
        obj,
        required={
            "schema_version",
            "outcome_index_id",
            "study_binding",
            "outcome_access",
            "ordered_case_outcomes",
            "boundary",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != STAGEC_POST_TERMINAL_OUTCOME_INDEX_SCHEMA:
        raise SchemaValidationError(
            "schema_version must equal "
            f"{STAGEC_POST_TERMINAL_OUTCOME_INDEX_SCHEMA!r}"
        )
    outcome_index_id = expect_machine_id(
        obj["outcome_index_id"],
        "$.outcome_index_id",
    )
    access = expect_object(obj["outcome_access"], "$.outcome_access")
    expect_keys(
        access,
        required={
            "accessed_at",
            "execution_completed_at",
            "receipt_role",
            "chain_finalization",
        },
        path="$.outcome_access",
    )
    accessed_at = expect_timestamp(
        access["accessed_at"],
        "$.outcome_access.accessed_at",
    )
    expected, completed_at, refs, receipts = _outcome_index_value(
        chain=chain,
        plan=plan,
        children=children,
        outcome_index_id=outcome_index_id,
        accessed_at=accessed_at,
    )
    if obj != expected:
        raise SchemaValidationError(
            "post-terminal outcome index does not exactly replay its "
            "plan/case/request/auth/archive/output/receipt inputs"
        )
    artifact = StageCPostTerminalOutcomeIndexArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        outcome_index_id=outcome_index_id,
        accessed_at=accessed_at,
        execution_completed_at=completed_at,
        ordered_terminal_receipts=receipts,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )

    chain.assert_integrity()
    sealed = chain.outcome_access
    if sealed is not None:
        if sealed.receipt != artifact.artifact_ref:
            raise SchemaValidationError(
                "sealed outcome-access event does not bind this exact Study outcome index"
            )
        if sealed.accessed_at != artifact.accessed_at:
            raise SchemaValidationError(
                "sealed outcome-access time does not match the Study outcome index"
            )
        if sealed.execution_completed_at != artifact.execution_completed_at:
            raise SchemaValidationError(
                "sealed execution-completion time does not match the Study outcome index"
            )
    return artifact


def build_stagec_post_terminal_outcome_index(
    *,
    chain: PreregistrationChain,
    plan: StudyPlanArtifact,
    children: tuple[StageCPostTerminalChild, ...],
    outcome_index_id: str,
    accessed_at: str,
) -> StageCPostTerminalOutcomeIndexArtifact:
    """Build the index before binding its resulting ref as outcome access."""

    if type(chain) is not PreregistrationChain:
        raise SchemaValidationError("chain must be an exact PreregistrationChain")
    chain.assert_integrity()
    if chain.outcome_access is not None:
        raise SchemaValidationError(
            "a new Study outcome index cannot be built after outcome-access finalization"
        )
    value, _, _, _ = _outcome_index_value(
        chain=chain,
        plan=plan,
        children=children,
        outcome_index_id=outcome_index_id,
        accessed_at=accessed_at,
    )
    return load_stagec_post_terminal_outcome_index(
        canonical_json_bytes(value),
        chain=chain,
        plan=plan,
        children=children,
    )


__all__ = [
    "STAGEC_AUTHORIZATION_PROJECTION_MEDIA_TYPE",
    "STAGEC_CAPTURE_INDEX_MEDIA_TYPE",
    "STAGEC_CAPTURE_REQUEST_MEDIA_TYPE",
    "STAGEC_CAPTURE_REQUEST_SCHEMA",
    "STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE",
    "STAGEC_LOCAL_CAPTURE_ARCHIVE_SCHEMA",
    "STAGEC_POST_TERMINAL_OUTCOME_INDEX_MEDIA_TYPE",
    "STAGEC_POST_TERMINAL_OUTCOME_INDEX_SCHEMA",
    "STAGEC_RAW_ARRAY_MEDIA_TYPE",
    "STAGEC_STUDY_REQUEST_BINDING_SCHEMA",
    "STAGEC_WORKER_OUTPUT_MEDIA_TYPE",
    "STAGEC_WORKER_OUTPUT_SCHEMA",
    "StageCCaptureArchiveProjection",
    "StageCPostTerminalChild",
    "StageCPostTerminalOutcomeIndexArtifact",
    "StageCStudyRequestBindingArtifact",
    "StageCWorkerOutputArtifact",
    "build_stagec_post_terminal_outcome_index",
    "build_stagec_worker_output",
    "load_stagec_capture_archive_projection",
    "load_stagec_post_terminal_outcome_index",
    "load_stagec_study_request_binding",
    "load_stagec_worker_output",
]
