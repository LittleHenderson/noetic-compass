"""Exact 480-row diagnostic phase closure and aggregate-access gating.

This module is additive to the frozen diagnostic v1 carriers.  It supplies the
phase-sized atomic boundary that :mod:`cas_harness_v2.diagnostic_lifecycle`
deliberately does not own: one registered roster, exactly 480 one-attempt
subjects, no late issuance after closure, plan-ordered terminal replay, and an
aggregate outcome-access gate that opens only for a complete clean batch.

The reference guard is locked and process-local.  It is suitable for the
bounded fake-only calibration run and tests; it is not a replicated/WORM store,
does not provide trusted time, and grants no model, evaluation, claim, product,
Packet-v2, or publication authority.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import math
import os
from pathlib import Path
import sqlite3
import stat
import struct
import threading
from types import MappingProxyType
from typing import Any, TypeVar

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
    require_unique,
)
from .diagnostic_execution_protocol import (
    DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
    DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
    DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE,
    DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
    DIAGNOSTIC_TERMINAL_STATUSES,
    validate_diagnostic_execution_batch_uniqueness,
)
from .diagnostic_lifecycle import (
    COMPLETED,
    DIAGNOSTIC_TERMINAL_STATES,
    EXPIRED,
    FAILED,
    INDETERMINATE,
    REJECTED,
    DiagnosticAttemptLifecycle,
    DiagnosticAttemptReconciliation,
    DiagnosticAttemptReplay,
    DiagnosticLifecycleReplayContext,
    DiagnosticLifecycleStore,
    DiagnosticSharedPlanReplayContext,
    SqliteDiagnosticLifecycleStore,
    build_diagnostic_shared_plan_replay_context,
    derive_diagnostic_attempt_subject_sha256,
)
from .diagnostic_preregistration import (
    DIAGNOSTIC_STUDY_OUTCOME_INDEX_MEDIA_TYPE,
    DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA,
    DiagnosticPreregistrationChain,
    DiagnosticStudyOutcomeAccessEvent,
    DiagnosticStudyOutcomeIndexArtifact,
)
from .diagnostic_study_protocol import (
    ADVERSARIAL_PRESENT,
    CLEAN_ABSENT,
    CLEAN_NULL_ABSENT,
    DIAGNOSTIC_CASE_COUNT,
    DIAGNOSTIC_GROUP_COUNT,
    DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE,
    DiagnosticStudyRequestArtifact,
)
from .stagec_outcome import (
    STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE,
    STAGEC_RAW_ARRAY_MEDIA_TYPE,
    StageCCaptureArchiveProjection,
    load_stagec_capture_archive_projection,
)


DIAGNOSTIC_PHASE_REGISTRATION_SCHEMA = (
    "cas_harness_v2.diagnostic_phase_registration.v1"
)
DIAGNOSTIC_PHASE_STORE_BINDING_SCHEMA = (
    "cas_harness_v2.diagnostic_phase_store_binding.v1"
)
DIAGNOSTIC_PHASE_RECONCILIATION_SCHEMA = (
    "cas_harness_v2.diagnostic_phase_reconciliation.v1"
)
DIAGNOSTIC_PHASE_OUTCOME_ACCESS_SCHEMA = (
    "cas_harness_v2.diagnostic_phase_outcome_access.v1"
)
DIAGNOSTIC_PHASE_ACTIVATION_ADMISSION_SCHEMA = (
    "cas_harness_v2.diagnostic_phase_activation_admission.v1"
)
DIAGNOSTIC_PHASE_REGISTRATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-phase-registration+json"
)
DIAGNOSTIC_PHASE_STORE_BINDING_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-phase-store-binding+json"
)
DIAGNOSTIC_PHASE_RECONCILIATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-phase-reconciliation+json"
)
DIAGNOSTIC_PHASE_OUTCOME_ACCESS_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-phase-outcome-access+json"
)
DIAGNOSTIC_PHASE_ACTIVATION_ADMISSION_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-phase-activation-admission+json"
)
DIAGNOSTIC_ACTIVATION_VECTOR_MEDIA_TYPE = STAGEC_RAW_ARRAY_MEDIA_TYPE
DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-calibration-rule+json"
)
DIAGNOSTIC_ACTIVATION_WIDTH = 4864
_STAGEC_ARCHIVE_MEMBER_ROLES = (
    "request_artifact",
    "authorization_projection_artifact",
    "capture_index_artifact",
    "input_ids",
    "attention_mask",
    "target_vector",
    "wrong_layer_vector",
)

PHASE_OPEN = "OPEN"
PHASE_RECONCILED_CLEAN = "RECONCILED_CLEAN"
PHASE_RECONCILED_REJECTED = "RECONCILED_REJECTED"
PHASE_OUTCOME_ACCESSED = "OUTCOME_ACCESSED"
DIAGNOSTIC_PHASE_STATES = frozenset(
    {
        PHASE_OPEN,
        PHASE_RECONCILED_CLEAN,
        PHASE_RECONCILED_REJECTED,
        PHASE_OUTCOME_ACCESSED,
    }
)

_CANONICAL_VARIANT_TRIPLET = (
    ADVERSARIAL_PRESENT,
    CLEAN_ABSENT,
    CLEAN_NULL_ABSENT,
)
_PHASE_SUBJECT_DOMAIN = "cas_harness_v2.diagnostic_phase_subject.v1"
_REQUEST_ARTIFACT_REFS_DOMAIN = (
    "cas_harness_v2.diagnostic_study_request_ordered_artifact_refs.v1"
)
_SQLITE_APPLICATION_ID = 0x43415344
_SQLITE_USER_VERSION = 1
_ISSUANCE_POLICY = {
    "expected_attempt_count": DIAGNOSTIC_CASE_COUNT,
    "attempts_per_case": 1,
    "retry": "FORBIDDEN",
    "replacement": "FORBIDDEN",
    "late_or_extra_issuance": "FORBIDDEN_AFTER_PHASE_SEAL",
    "closure_rule": "EXACT_PLAN_ORDERED_TERMINAL_INVENTORY",
}
_BOUNDARY = {
    "scope": "DIAGNOSTIC_CALIBRATION_NONREPORTING_ONLY",
    "authority": "STRUCTURE_AND_ACCOUNTING_ONLY",
    "admission_ring": 4,
    "criteria_status": "OPEN",
    "product_claim_status": "NOT LICENSED",
    "disclosure_status": "HELD",
    "trusted_time": "NOT_PROVIDED",
    "durable_one_use": "NOT_ESTABLISHED",
    "phase_storage": "PRIVATE_SAME_FILE_SQLITE_CREATE_ONLY_GUARD",
    "coordinator_public_api_outcome_release": "POST_CLEAN_RECONCILIATION_ONLY",
    "out_of_band_read_prevention": "NOT_ESTABLISHED",
    "rogue_process_writes": "DETECTED_FAIL_CLOSED_NOT_PREVENTED",
    "replication": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "evidence_packet_v2": "FORBIDDEN",
    "evaluation_execution": "NOT_AUTHORIZED",
    "evaluation_promotion": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
    "product_route": "FORBIDDEN",
    "public_release": False,
}
_OUTCOME_BOUNDARY = {
    "scope": "STRUCTURE_ONLY",
    "execution_authorization": "OPEN_NOT_PROVIDED",
    "terminal_row_coordinator": "OPEN_NOT_PROVIDED",
    "failed_row_semantics": "OPEN_NOT_PROVIDED",
    "diagnostic_nonreporting_disposition": "OPEN_NOT_PROVIDED",
    "retry_evidence": "NOT_ATTESTED",
    "trusted_time": "NOT_PROVIDED",
    "durable_one_use": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "evidence_packet_v2": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
}


class DiagnosticPhaseError(RuntimeError):
    """Base error for phase-sized diagnostic closure."""


class DiagnosticPhaseValidationError(DiagnosticPhaseError):
    """A phase carrier or exact dependency is invalid."""


class DiagnosticPhaseConflict(DiagnosticPhaseError):
    """A create-only phase state or issuance rule was violated."""


class DiagnosticPhaseIntegrityError(DiagnosticPhaseError):
    """The retained 480-row family cannot prove exact clean reconciliation."""


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _artifact_ids_in_json(value: Any) -> set[str]:
    """Collect exact ArtifactRef-shaped identifiers from frozen/plain JSON."""

    found: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            if set(node) == {"artifact_id", "sha256", "byte_length", "media_type"}:
                found.add(str(node["artifact_id"]))
                return
            for child in node.values():
                visit(child)
        elif type(node) in (tuple, list):
            for child in node:
                visit(child)

    visit(value)
    return found


def _canonical_object(
    raw: bytes | bytearray | memoryview, path: str
) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, obj = load_json_object(raw)
        if snapshot != canonical_json_bytes(obj):
            raise DiagnosticPhaseValidationError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, obj
    except DiagnosticPhaseValidationError:
        raise
    except (ValueError, TypeError) as exc:
        raise DiagnosticPhaseValidationError(f"{path}: {exc}") from exc


def _require_boundary(value: Any, path: str = "$.boundary") -> None:
    try:
        obj = expect_object(value, path)
        expect_keys(obj, required=_BOUNDARY, path=path)
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    if obj != _BOUNDARY:
        raise DiagnosticPhaseValidationError(
            f"{path} fabricated Packet, evaluation, claim, product, publication, "
            "durability, or trusted-time authority"
        )


def _require_exact_type(value: Any, expected: type, path: str) -> None:
    if type(value) is not expected:
        raise DiagnosticPhaseValidationError(
            f"{path} must be an exact {expected.__name__}"
        )


_MAPPING_PROXY_TYPE = type(MappingProxyType({}))


def _require_frozen_projection(value: Any, path: str) -> None:
    if type(value) is _MAPPING_PROXY_TYPE:
        for key, item in value.items():
            if type(key) is not str:
                raise DiagnosticPhaseValidationError(
                    f"{path} contains a non-string mapping key"
                )
            _require_frozen_projection(item, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, item in enumerate(value):
            _require_frozen_projection(item, f"{path}[{index}]")
        return
    if type(value) in (str, int, bool) or value is None:
        return
    raise DiagnosticPhaseValidationError(
        f"{path} must be recursively immutable frozen JSON"
    )


def _require_artifact_projection_storage(value: Any, path: str) -> None:
    if (
        type(value.raw_bytes) is not bytes
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.payload) is not _MAPPING_PROXY_TYPE
    ):
        raise DiagnosticPhaseValidationError(
            f"{path} raw/hash/length/payload projections must be exact immutable types"
        )
    _require_frozen_projection(value.payload, f"{path}.payload")


def _phase_subject_value(
    *,
    phase_id: str,
    tenant_id: str,
    shared: DiagnosticSharedPlanReplayContext,
    store_binding: "DiagnosticPhaseStoreBindingArtifact",
    calibration_rule_ref: ArtifactRef,
    ordered_subjects: Sequence[str],
) -> dict[str, Any]:
    return {
        "domain": _PHASE_SUBJECT_DOMAIN,
        "phase_id": phase_id,
        "tenant_id": tenant_id,
        "pre_outcome_chain_sha256": shared.plan.pre_outcome_chain_sha256,
        "diagnostic_study_plan": _artifact_ref_value(shared.plan.artifact_ref),
        "diagnostic_execution_contract": _artifact_ref_value(
            shared.execution_contract.artifact_ref
        ),
        "diagnostic_phase_store_binding": _artifact_ref_value(
            store_binding.artifact_ref
        ),
        "diagnostic_calibration_rule": _artifact_ref_value(calibration_rule_ref),
        "ordered_attempt_subject_sha256s": list(ordered_subjects),
    }


def _registration_row_value(
    *,
    planned: Any,
    request: DiagnosticStudyRequestArtifact,
    subject: str,
) -> dict[str, Any]:
    artifact_ref_count, artifact_refs_sha256 = _request_artifact_refs_binding(
        request.artifact_refs
    )
    return {
        "execution_ordinal": planned.execution_ordinal,
        "case_id": planned.case_id,
        "base_intent_group_id": planned.base_intent_group_id,
        "frozen_variant": planned.frozen_variant,
        "diagnostic_study_request": _artifact_ref_value(request.artifact_ref),
        "study_request_artifact_ref_count": artifact_ref_count,
        "study_request_ordered_artifact_refs_sha256": artifact_refs_sha256,
        "stagec_capture_request": _artifact_ref_value(planned.capture_request),
        "attempt_subject_sha256": subject,
        "attempt_ordinal": 1,
    }


def _request_artifact_refs_binding(
    references: tuple[ArtifactRef, ...],
) -> tuple[int, str]:
    """Bind the exact ordered transitive closure retained by one Study request."""

    if type(references) is not tuple or not references:
        raise DiagnosticPhaseValidationError(
            "Study-request artifact-ref closure must be a nonempty exact tuple"
        )
    for index, reference in enumerate(references):
        if (
            type(reference) is not ArtifactRef
            or type(reference.artifact_id) is not str
            or type(reference.sha256) is not str
            or type(reference.byte_length) is not int
            or type(reference.media_type) is not str
        ):
            raise DiagnosticPhaseValidationError(
                "Study-request artifact-ref closure contains a forged carrier "
                f"at ordinal {index}"
            )
    try:
        require_unique(
            (reference.artifact_id for reference in references),
            "Study-request artifact-ref closure artifact_id",
        )
        require_unique(
            (reference.sha256 for reference in references),
            "Study-request artifact-ref closure sha256",
        )
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    return (
        len(references),
        canonical_sha256(
            {
                "domain": _REQUEST_ARTIFACT_REFS_DOMAIN,
                "ordered_artifact_refs": [
                    _artifact_ref_value(reference) for reference in references
                ],
            }
        ),
    )


def _registration_value(
    *,
    registration_id: str,
    phase_id: str,
    registered_at: str,
    tenant_id: str,
    shared: DiagnosticSharedPlanReplayContext,
    store_binding: "DiagnosticPhaseStoreBindingArtifact",
    calibration_rule_ref: ArtifactRef,
    requests: tuple[DiagnosticStudyRequestArtifact, ...],
) -> dict[str, Any]:
    ordered_subjects = tuple(
        derive_diagnostic_attempt_subject_sha256(
            plan=shared.plan, study_request=request
        )
        for request in requests
    )
    phase_subject = canonical_sha256(
        _phase_subject_value(
            phase_id=phase_id,
            tenant_id=tenant_id,
            shared=shared,
            store_binding=store_binding,
            calibration_rule_ref=calibration_rule_ref,
            ordered_subjects=ordered_subjects,
        )
    )
    return {
        "schema_version": DIAGNOSTIC_PHASE_REGISTRATION_SCHEMA,
        "registration_id": registration_id,
        "phase_id": phase_id,
        "phase_subject_sha256": phase_subject,
        "registered_at": registered_at,
        "tenant_id": tenant_id,
        "pre_outcome_chain_sha256": shared.plan.pre_outcome_chain_sha256,
        "diagnostic_study_plan": _artifact_ref_value(shared.plan.artifact_ref),
        "diagnostic_execution_contract": _artifact_ref_value(
            shared.execution_contract.artifact_ref
        ),
        "diagnostic_phase_store_binding": _artifact_ref_value(
            store_binding.artifact_ref
        ),
        "diagnostic_calibration_rule": _artifact_ref_value(calibration_rule_ref),
        "expected_row_count": DIAGNOSTIC_CASE_COUNT,
        "expected_group_count": DIAGNOSTIC_GROUP_COUNT,
        "ordered_attempts": [
            _registration_row_value(planned=planned, request=request, subject=subject)
            for planned, request, subject in zip(
                shared.plan.cases, requests, ordered_subjects, strict=True
            )
        ],
        "issuance_policy": dict(_ISSUANCE_POLICY),
        "boundary": dict(_BOUNDARY),
    }


@dataclass(frozen=True, slots=True)
class DiagnosticPhaseStoreBindingArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    binding_id: str
    created_at: str
    canonical_path: str
    file_device: int
    file_inode: int
    parent_device: int
    parent_inode: int
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.binding_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_PHASE_STORE_BINDING_MEDIA_TYPE,
        )


def _store_identity(path: str) -> dict[str, Any]:
    target = Path(path)
    try:
        file_stat = target.lstat()
        parent_stat = target.parent.stat()
    except OSError as exc:
        raise DiagnosticPhaseValidationError(
            f"phase store identity cannot be read: {exc}"
        ) from exc
    reparse = bool(
        getattr(file_stat, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )
    if (
        not stat.S_ISREG(file_stat.st_mode)
        or target.is_symlink()
        or reparse
        or file_stat.st_nlink != 1
    ):
        raise DiagnosticPhaseValidationError(
            "phase store must be a regular unique-link file with no link/reparse indirection"
        )
    if target.parent.is_symlink():
        raise DiagnosticPhaseValidationError(
            "phase store parent must not be a symbolic link"
        )
    return {
        "canonical_absolute_path": str(target.resolve()),
        "file_device": int(file_stat.st_dev),
        "file_inode": int(file_stat.st_ino),
        "file_mode_type": "REGULAR_FILE",
        "file_link_count": int(file_stat.st_nlink),
        "file_symlink": False,
        "file_reparse_point": False,
        "parent_device": int(parent_stat.st_dev),
        "parent_inode": int(parent_stat.st_ino),
        "parent_mode_type": "DIRECTORY",
        "parent_symlink": False,
    }


def _store_binding_value(
    *, binding_id: str, created_at: str, identity: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_PHASE_STORE_BINDING_SCHEMA,
        "binding_id": binding_id,
        "created_at": created_at,
        "filesystem_identity": thaw_json(identity),
        "sqlite_identity": {
            "application_id": _SQLITE_APPLICATION_ID,
            "user_version": _SQLITE_USER_VERSION,
            "schema_identity": (
                "PREPLAN_EMPTY_SQLITE_THEN_COORDINATOR_EXACT_SCHEMA_V1"
            ),
            "journal_mode_required": "WAL",
            "synchronous_required": "FULL",
        },
        "boundary": {
            "scope": "HOST_LOCAL_CANONICAL_DIAGNOSTIC_PHASE_STORE",
            "replication": "NOT_PROVIDED",
            "worm": "NOT_PROVIDED",
            "trusted_time": "NOT_PROVIDED",
            "durable_authority": "NOT_ESTABLISHED",
            "path_swap_prevention": (
                "O_EXCL_FSTAT_AND_PATH_IDENTITY_BEFORE_AFTER_SQLITE_INIT"
            ),
            "rogue_process_writes": "DETECTED_FAIL_CLOSED_NOT_PREVENTED",
        },
    }


def load_diagnostic_phase_store_binding(
    raw: bytes | bytearray | memoryview,
) -> DiagnosticPhaseStoreBindingArtifact:
    snapshot, obj = _canonical_object(raw, "diagnostic phase store binding")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "binding_id",
                "created_at",
                "filesystem_identity",
                "sqlite_identity",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_PHASE_STORE_BINDING_SCHEMA:
            raise SchemaValidationError("wrong phase-store-binding schema")
        binding_id = expect_machine_id(obj["binding_id"], "$.binding_id")
        created_at = expect_timestamp(obj["created_at"], "$.created_at")
        identity = expect_object(obj["filesystem_identity"], "$.filesystem_identity")
        canonical_path = expect_string(
            identity.get("canonical_absolute_path"),
            "$.filesystem_identity.canonical_absolute_path",
            maximum=4096,
        )
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    if not Path(canonical_path).is_absolute() or canonical_path != str(
        Path(canonical_path).resolve()
    ):
        raise DiagnosticPhaseValidationError(
            "phase store binding path must be exact canonical absolute path"
        )
    observed = _store_identity(canonical_path)
    if identity != observed:
        raise DiagnosticPhaseIntegrityError(
            "phase store filesystem identity changed or aliases another file"
        )
    expected_sqlite = {
        "application_id": _SQLITE_APPLICATION_ID,
        "user_version": _SQLITE_USER_VERSION,
        "schema_identity": "PREPLAN_EMPTY_SQLITE_THEN_COORDINATOR_EXACT_SCHEMA_V1",
        "journal_mode_required": "WAL",
        "synchronous_required": "FULL",
    }
    if obj["sqlite_identity"] != expected_sqlite or obj["boundary"] != {
        "scope": "HOST_LOCAL_CANONICAL_DIAGNOSTIC_PHASE_STORE",
        "replication": "NOT_PROVIDED",
        "worm": "NOT_PROVIDED",
        "trusted_time": "NOT_PROVIDED",
        "durable_authority": "NOT_ESTABLISHED",
        "path_swap_prevention": (
            "O_EXCL_FSTAT_AND_PATH_IDENTITY_BEFORE_AFTER_SQLITE_INIT"
        ),
        "rogue_process_writes": "DETECTED_FAIL_CLOSED_NOT_PREVENTED",
    }:
        raise DiagnosticPhaseValidationError(
            "phase store SQLite/boundary identity changed"
        )
    connection = sqlite3.connect(canonical_path)
    try:
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        journal_mode = str(
            connection.execute("PRAGMA journal_mode").fetchone()[0]
        ).upper()
        synchronous = connection.execute("PRAGMA synchronous").fetchone()[0]
        schema_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE name NOT LIKE 'sqlite_%'
                """
            )
        }
    finally:
        connection.close()
    if (
        application_id != _SQLITE_APPLICATION_ID
        or user_version != _SQLITE_USER_VERSION
        or journal_mode != "WAL"
        or synchronous != 2
    ):
        raise DiagnosticPhaseIntegrityError("phase store SQLite identity changed")
    required_initialized_schema = {
        "diagnostic_attempts",
        "diagnostic_attempt_events",
        "diagnostic_phases",
        "diagnostic_phase_roster",
        "diagnostic_phase_activation_admissions",
        "diagnostic_phase_outcome_access",
    }
    if schema_names and not required_initialized_schema.issubset(schema_names):
        raise DiagnosticPhaseIntegrityError(
            "phase store contains a counterfeit or partial SQLite schema"
        )
    return DiagnosticPhaseStoreBindingArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        binding_id=binding_id,
        created_at=created_at,
        canonical_path=canonical_path,
        file_device=identity["file_device"],
        file_inode=identity["file_inode"],
        parent_device=identity["parent_device"],
        parent_inode=identity["parent_inode"],
        payload=freeze_json(obj),
    )


def replay_diagnostic_phase_store_binding_projection(
    binding: DiagnosticPhaseStoreBindingArtifact,
) -> DiagnosticPhaseStoreBindingArtifact:
    _require_exact_type(
        binding, DiagnosticPhaseStoreBindingArtifact, "phase_store_binding"
    )
    _require_artifact_projection_storage(binding, "phase_store_binding")
    if (
        any(
            type(getattr(binding, name)) is not str
            for name in ("binding_id", "created_at", "canonical_path")
        )
        or any(
            type(getattr(binding, name)) is not int
            for name in (
                "file_device",
                "file_inode",
                "parent_device",
                "parent_inode",
            )
        )
    ):
        raise DiagnosticPhaseValidationError(
            "phase store binding scalar projections have mutable or invalid types"
        )
    exact = load_diagnostic_phase_store_binding(binding.raw_bytes)
    if exact != binding:
        raise DiagnosticPhaseValidationError(
            "phase store binding dataclass differs from exact raw-byte projection"
        )
    return binding


def build_diagnostic_phase_store_binding(
    *,
    binding_id: str,
    created_at: str,
    database_path: str | os.PathLike[str],
) -> DiagnosticPhaseStoreBindingArtifact:
    try:
        binding_id = expect_machine_id(binding_id, "binding_id")
        created_at = expect_timestamp(created_at, "created_at")
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    path = _phase_file_path(database_path)
    if Path(path).exists():
        raise DiagnosticPhaseConflict(
            "phase store binding must create a previously absent canonical file"
        )
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    created_stat = os.fstat(descriptor)
    created_identity = (int(created_stat.st_dev), int(created_stat.st_ino))
    try:
        before = _store_identity(path)
        if (before["file_device"], before["file_inode"]) != created_identity:
            raise DiagnosticPhaseIntegrityError(
                "phase store path changed after exclusive creation"
            )
        connection = sqlite3.connect(path, isolation_level=None)
        try:
            connection.execute(f"PRAGMA application_id={_SQLITE_APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={_SQLITE_USER_VERSION}")
            if str(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]).upper() != "WAL":
                raise DiagnosticPhaseIntegrityError(
                    "phase store could not establish WAL journal mode"
                )
            connection.execute("PRAGMA synchronous=FULL")
            if connection.execute("PRAGMA synchronous").fetchone()[0] != 2:
                raise DiagnosticPhaseIntegrityError(
                    "phase store could not establish FULL synchronous mode"
                )
        finally:
            connection.close()
        identity = _store_identity(path)
        if (identity["file_device"], identity["file_inode"]) != created_identity:
            raise DiagnosticPhaseIntegrityError(
                "phase store path changed during SQLite initialization"
            )
        raw = canonical_json_bytes(
            _store_binding_value(
                binding_id=binding_id,
                created_at=created_at,
                identity=identity,
            )
        )
        return load_diagnostic_phase_store_binding(raw)
    except Exception:
        # A failed pre-plan binding has no admitted identity.  Remove only the
        # exact just-created inode; never unlink a path replacement.
        try:
            observed = _store_identity(path)
            if (observed["file_device"], observed["file_inode"]) == created_identity:
                Path(path).unlink()
        except (OSError, DiagnosticPhaseError):
            pass
        raise
    finally:
        os.close(descriptor)


@dataclass(frozen=True, slots=True)
class DiagnosticPhaseRegistrationArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    registration_id: str
    phase_id: str
    phase_subject_sha256: str
    registered_at: str
    tenant_id: str
    store_binding: DiagnosticPhaseStoreBindingArtifact
    calibration_rule_ref: ArtifactRef
    ordered_subjects: tuple[str, ...]
    study_requests: tuple[DiagnosticStudyRequestArtifact, ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.registration_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_PHASE_REGISTRATION_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticPhaseReconciliationArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    reconciliation_id: str
    phase_id: str
    phase_subject_sha256: str
    closed_at: str
    status: str
    rejection_reasons: tuple[str, ...]
    terminal_rows: int
    completed_rows: int
    analyzed_rows: int
    missing_rows: int
    excluded_rows: int
    execution_started_at: str | None
    execution_completed_at: str
    ordered_attempt_subjects: tuple[str, ...]
    ordered_terminal_row_sha256s: tuple[str, ...]
    ordered_activation_binding_sha256s: tuple[str, ...]
    activation_admission_refs: tuple[ArtifactRef | None, ...]
    activation_vector_refs: tuple[
        tuple[ArtifactRef, ArtifactRef] | None, ...
    ]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.reconciliation_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_PHASE_RECONCILIATION_MEDIA_TYPE,
        )

@dataclass(frozen=True, slots=True)
class DiagnosticPhaseOutcomeAccessArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    access_id: str
    phase_id: str
    phase_subject_sha256: str
    accessed_at: str
    execution_started_at: str
    study_completed_at: str
    reconciliation_ref: ArtifactRef
    outcome_index: DiagnosticStudyOutcomeIndexArtifact
    outcome_access_event: DiagnosticStudyOutcomeAccessEvent
    activation_admissions: tuple[DiagnosticPhaseActivationAdmissionArtifact, ...]
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.access_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_PHASE_OUTCOME_ACCESS_MEDIA_TYPE,
        )

    @property
    def activation_artifacts(
        self,
    ) -> tuple[
        tuple[tuple[ArtifactRef, bytes], tuple[ArtifactRef, bytes]], ...
    ]:
        return tuple(
            (
                (admission.target_vector, admission.target_body),
                (admission.wrong_layer_vector, admission.wrong_layer_body),
            )
            for admission in self.activation_admissions
        )


@dataclass(frozen=True, slots=True)
class DiagnosticPhaseActivationAdmissionArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    admission_id: str
    attempt_subject_sha256: str
    admitted_at: str
    archive_admission_ref: ArtifactRef
    child_output_ref: ArtifactRef
    archive_manifest_ref: ArtifactRef
    archive_manifest_body: bytes
    archive_member_bodies: tuple[tuple[str, bytes], ...]
    target_vector: ArtifactRef
    wrong_layer_vector: ArtifactRef
    target_body: bytes
    wrong_layer_body: bytes
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.admission_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_PHASE_ACTIVATION_ADMISSION_MEDIA_TYPE,
        )


def _validate_activation_vector_body(
    reference: ArtifactRef,
    body: bytes,
    *,
    expected: Mapping[str, Any],
    path: str,
) -> None:
    _require_exact_type(reference, ArtifactRef, f"{path}.reference")
    if type(body) is not bytes:
        raise DiagnosticPhaseValidationError(f"{path}.body must be exact bytes")
    if (
        reference.artifact_id != expected.get("artifact_id")
        or reference.media_type != DIAGNOSTIC_ACTIVATION_VECTOR_MEDIA_TYPE
        or expected.get("dtype") != "<f4"
        or not reference.verify_bytes(body)
        or len(body) != DIAGNOSTIC_ACTIVATION_WIDTH * 4
    ):
        raise DiagnosticPhaseValidationError(
            f"{path} differs from its capture expectation or exact retained bytes"
        )
    if any(not math.isfinite(value[0]) for value in struct.iter_unpack("<f", body)):
        raise DiagnosticPhaseValidationError(f"{path} contains a non-finite float32")


def _archive_member_refs(
    manifest_body: bytes,
) -> dict[str, ArtifactRef]:
    _, manifest = _canonical_object(manifest_body, "Stage C archive manifest refs")
    rows = manifest.get("members")
    if type(rows) is not list or len(rows) != len(_STAGEC_ARCHIVE_MEMBER_ROLES):
        raise DiagnosticPhaseValidationError(
            "Stage C archive manifest lacks its exact seven ordered members"
        )
    refs: dict[str, ArtifactRef] = {}
    for expected_role, row in zip(_STAGEC_ARCHIVE_MEMBER_ROLES, rows, strict=True):
        if type(row) is not dict or row.get("role") != expected_role:
            raise DiagnosticPhaseValidationError(
                "Stage C archive manifest member role/order drifted"
            )
        value = row.get("ref")
        if type(value) is not dict:
            raise DiagnosticPhaseValidationError(
                f"Stage C archive member {expected_role} lacks an exact ref"
            )
        try:
            refs[expected_role] = ArtifactRef(
                artifact_id=expect_machine_id(
                    value.get("artifact_id"),
                    f"$archive_manifest.members.{expected_role}.artifact_id",
                ),
                sha256=expect_sha256(
                    value.get("sha256"),
                    f"$archive_manifest.members.{expected_role}.sha256",
                ),
                byte_length=expect_int(
                    value.get("byte_length"),
                    f"$archive_manifest.members.{expected_role}.byte_length",
                    minimum=1,
                ),
                media_type=expect_string(
                    value.get("media_type"),
                    f"$archive_manifest.members.{expected_role}.media_type",
                    maximum=128,
                ),
            )
        except SchemaValidationError as exc:
            raise DiagnosticPhaseValidationError(str(exc)) from exc
    return refs


def _validate_archive_projection(
    *,
    replay: DiagnosticAttemptReplay,
    manifest_ref: ArtifactRef,
    manifest_body: bytes,
    member_bodies: Mapping[str, bytes],
) -> tuple[StageCCaptureArchiveProjection, ArtifactRef, ArtifactRef]:
    """Strictly replay seven portable members and bind them to this attempt."""

    _require_exact_type(replay, DiagnosticAttemptReplay, "replay")
    _require_exact_type(manifest_ref, ArtifactRef, "archive_manifest[0]")
    if type(manifest_body) is not bytes:
        raise DiagnosticPhaseValidationError("archive_manifest[1] must be exact bytes")
    if not isinstance(member_bodies, Mapping) or set(member_bodies) != set(
        _STAGEC_ARCHIVE_MEMBER_ROLES
    ):
        raise DiagnosticPhaseValidationError(
            "archive_member_bodies must contain the exact seven Stage C roles"
        )
    members = {role: member_bodies[role] for role in _STAGEC_ARCHIVE_MEMBER_ROLES}
    if any(type(body) is not bytes for body in members.values()):
        raise DiagnosticPhaseValidationError(
            "archive_member_bodies values must be exact immutable bytes"
        )
    try:
        projection = load_stagec_capture_archive_projection(
            manifest_ref=manifest_ref,
            manifest_bytes=manifest_body,
            member_bytes=members,
        )
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(
            f"portable seven-member Stage C archive replay failed: {exc}"
        ) from exc
    refs = _archive_member_refs(projection.manifest_bytes)
    context = replay.binding.payload["execution_context"]
    case = context["case_binding"]
    capture = context["artifact_expectations"]["capture"]
    archive_expectation = context["artifact_expectations"]["archive"]
    try:
        capture_request_ref = parse_artifact_ref(
            thaw_json(context["study_binding"]["stagec_capture_request"]),
            "$.execution_context.study_binding.stagec_capture_request",
        )
        authorization_projection_ref = parse_artifact_ref(
            thaw_json(capture["authorization_projection"]),
            "$.execution_context.artifact_expectations.capture.authorization_projection",
        )
    except SchemaValidationError as exc:
        raise DiagnosticPhaseIntegrityError(str(exc)) from exc
    association = {
        "study_id": case["study_id"],
        "case_id": case["case_id"],
        "split_id": case["split_id"],
        "base_intent_group_id": case["base_intent_group_id"],
        "frozen_variant": case["frozen_variant"],
        "frozen_label": case["frozen_label"],
        "invocation_id": case["invocation_id"],
        "plan_id": context["study_binding"]["diagnostic_study_plan"][
            "artifact_id"
        ],
    }
    if any(getattr(projection, key) != value for key, value in association.items()):
        raise DiagnosticPhaseIntegrityError(
            "portable archive association differs from the diagnostic attempt binding"
        )
    expected_ids = archive_expectation["expected_member_artifact_ids"]
    if (
        manifest_ref.media_type != STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE
        or manifest_ref.media_type != archive_expectation["media_type"]
        or projection.capture_request_ref != capture_request_ref
        or projection.authorization_projection_ref != authorization_projection_ref
        or projection.capture_index_ref.artifact_id
        != capture["capture_index"]["artifact_id"]
        or projection.capture_index_ref.media_type
        != capture["capture_index"]["media_type"]
        or {role: reference.artifact_id for role, reference in refs.items()}
        != dict(expected_ids)
    ):
        raise DiagnosticPhaseIntegrityError(
            "portable archive member identities differ from the frozen execution context"
        )
    target_ref = refs["target_vector"]
    wrong_ref = refs["wrong_layer_vector"]
    _validate_activation_vector_body(
        target_ref,
        members["target_vector"],
        expected=capture["raw_arrays"]["target_vector"],
        path="archive_member_bodies.target_vector",
    )
    _validate_activation_vector_body(
        wrong_ref,
        members["wrong_layer_vector"],
        expected=capture["raw_arrays"]["wrong_layer_vector"],
        path="archive_member_bodies.wrong_layer_vector",
    )
    if target_ref == wrong_ref or target_ref.artifact_id == wrong_ref.artifact_id:
        raise DiagnosticPhaseValidationError(
            "target and wrong-layer archive members must be distinct"
        )
    return projection, target_ref, wrong_ref


def _validate_completed_documents(
    replay: DiagnosticAttemptReplay,
    *,
    expected_manifest_ref: ArtifactRef | None = None,
) -> tuple[ArtifactRef, ArtifactRef, ArtifactRef]:
    """Freshly parse and bind both lifecycle-retained completed output bodies."""

    terminal = replay.terminal_receipt
    authorization = replay.authorization
    if (
        terminal is None
        or authorization is None
        or replay.snapshot.state != COMPLETED
        or terminal.terminal_status != COMPLETED
        or _terminal_roles(replay) != ("archive_admission", "child_output")
        or set(replay.produced_artifact_bodies)
        != {"archive_admission", "child_output"}
        or len(terminal.produced_artifact_refs) != 2
    ):
        raise DiagnosticPhaseIntegrityError(
            "activation admission requires one exact completed archive/output family"
        )
    archive_ref, output_ref = terminal.produced_artifact_refs
    archive_body = replay.produced_artifact_bodies["archive_admission"]
    output_body = replay.produced_artifact_bodies["child_output"]
    if (
        archive_ref.media_type != DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE
        or output_ref.media_type != DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE
        or not archive_ref.verify_bytes(archive_body)
        or not output_ref.verify_bytes(output_body)
    ):
        raise DiagnosticPhaseIntegrityError(
            "completed terminal references do not verify their retained bodies"
        )
    _, archive = _canonical_object(archive_body, "retained archive admission")
    _, output = _canonical_object(output_body, "retained child output")
    archive_keys = {
        "schema_version",
        "admission_id",
        "authorization",
        "execution_context_sha256",
        "case_binding",
        "archive_expectation_sha256",
        "archive_manifest",
        "observation",
        "boundary",
        "authority",
        "governance",
    }
    output_keys = {
        "schema_version",
        "output_id",
        "authorization",
        "execution_context_sha256",
        "case_binding",
        "archive_admission",
        "output_role",
        "boundary",
        "authority",
        "governance",
    }
    try:
        expect_keys(archive, required=archive_keys, path="$archive_admission")
        expect_keys(output, required=output_keys, path="$child_output")
        parse_artifact_ref(archive["authorization"], "$archive_admission.authorization")
        manifest_ref = parse_artifact_ref(
            archive["archive_manifest"], "$archive_admission.archive_manifest"
        )
        parse_artifact_ref(output["authorization"], "$child_output.authorization")
        parse_artifact_ref(output["archive_admission"], "$child_output.archive_admission")
    except SchemaValidationError as exc:
        raise DiagnosticPhaseIntegrityError(str(exc)) from exc
    context = authorization.payload["execution_context"]
    if (
        archive["schema_version"] != DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA
        or archive["admission_id"] != archive_ref.artifact_id
        or archive["authorization"] != _artifact_ref_value(authorization.artifact_ref)
        or archive["execution_context_sha256"]
        != authorization.execution_context_sha256
        or archive["case_binding"] != thaw_json(context["case_binding"])
        or archive["archive_expectation_sha256"]
        != canonical_sha256(context["artifact_expectations"]["archive"])
        or output["schema_version"] != DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA
        or output["output_id"] != output_ref.artifact_id
        or output["authorization"] != _artifact_ref_value(authorization.artifact_ref)
        or output["execution_context_sha256"]
        != authorization.execution_context_sha256
        or output["case_binding"] != thaw_json(context["case_binding"])
        or output["archive_admission"] != _artifact_ref_value(archive_ref)
        or output["output_role"] != "DIAGNOSTIC_STAGEC_CHILD_OUTPUT"
        or (
            expected_manifest_ref is not None
            and manifest_ref != expected_manifest_ref
        )
    ):
        raise DiagnosticPhaseIntegrityError(
            "retained archive/output documents do not exactly cross-bind the attempt"
        )
    return archive_ref, output_ref, manifest_ref


def _activation_admission_value(
    *,
    admission_id: str,
    replay: DiagnosticAttemptReplay,
    admitted_at: str,
    archive_ref: ArtifactRef,
    output_ref: ArtifactRef,
    manifest_ref: ArtifactRef,
    target_ref: ArtifactRef,
    wrong_ref: ArtifactRef,
) -> dict[str, Any]:
    terminal = replay.terminal_receipt
    authorization = replay.authorization
    assert terminal is not None and authorization is not None
    arrays = replay.binding.payload["execution_context"]["artifact_expectations"][
        "capture"
    ]["raw_arrays"]

    def vector_value(reference: ArtifactRef, expectation: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "artifact": _artifact_ref_value(reference),
            "dtype": expectation["dtype"],
            "shape": [DIAGNOSTIC_ACTIVATION_WIDTH],
            "role": expectation["role"],
            "layer_index": expectation["layer_index"],
            "module_path": expectation["module_path"],
        }

    return {
        "schema_version": DIAGNOSTIC_PHASE_ACTIVATION_ADMISSION_SCHEMA,
        "admission_id": admission_id,
        "attempt_subject_sha256": replay.snapshot.attempt_subject_sha256,
        "admitted_at": admitted_at,
        "binding": _artifact_ref_value(replay.binding.artifact_ref),
        "authorization": _artifact_ref_value(authorization.artifact_ref),
        "terminal_receipt": _artifact_ref_value(terminal.artifact_ref),
        "source_documents": {
            "archive_admission": _artifact_ref_value(archive_ref),
            "child_output": _artifact_ref_value(output_ref),
            "archive_manifest": _artifact_ref_value(manifest_ref),
        },
        "activation_vectors": {
            "target_layer18": vector_value(target_ref, arrays["target_vector"]),
            "wrong_layer0": vector_value(wrong_ref, arrays["wrong_layer_vector"]),
        },
        "capture_expectation_sha256": canonical_sha256(
            replay.binding.payload["execution_context"]["artifact_expectations"][
                "capture"
            ]
        ),
        "boundary": dict(_BOUNDARY),
    }


def load_diagnostic_phase_activation_admission(
    raw: bytes | bytearray | memoryview,
    *,
    replay: DiagnosticAttemptReplay,
    archive_manifest_ref: ArtifactRef,
    archive_manifest_body: bytes,
    archive_member_bodies: Mapping[str, bytes],
) -> DiagnosticPhaseActivationAdmissionArtifact:
    """Strict-load the capture-grounded vectors retained for one completed row."""

    _require_exact_type(replay, DiagnosticAttemptReplay, "replay")
    projection, target_ref, wrong_ref = _validate_archive_projection(
        replay=replay,
        manifest_ref=archive_manifest_ref,
        manifest_body=archive_manifest_body,
        member_bodies=archive_member_bodies,
    )
    archive_ref, output_ref, retained_manifest_ref = _validate_completed_documents(
        replay, expected_manifest_ref=projection.manifest_ref
    )
    snapshot, obj = _canonical_object(raw, "diagnostic phase activation admission")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "admission_id",
                "attempt_subject_sha256",
                "admitted_at",
                "binding",
                "authorization",
                "terminal_receipt",
                "source_documents",
                "activation_vectors",
                "capture_expectation_sha256",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_PHASE_ACTIVATION_ADMISSION_SCHEMA:
            raise SchemaValidationError("wrong phase activation-admission schema")
        admission_id = expect_machine_id(obj["admission_id"], "$.admission_id")
        subject = expect_sha256(
            obj["attempt_subject_sha256"], "$.attempt_subject_sha256"
        )
        admitted_at = expect_timestamp(obj["admitted_at"], "$.admitted_at")
        for key in ("binding", "authorization", "terminal_receipt"):
            parse_artifact_ref(obj[key], f"$.{key}")
        source = expect_object(obj["source_documents"], "$.source_documents")
        expect_keys(
            source,
            required={"archive_admission", "child_output", "archive_manifest"},
            path="$.source_documents",
        )
        parse_artifact_ref(source["archive_admission"], "$.source_documents.archive_admission")
        parse_artifact_ref(source["child_output"], "$.source_documents.child_output")
        parse_artifact_ref(source["archive_manifest"], "$.source_documents.archive_manifest")
        vectors = expect_object(obj["activation_vectors"], "$.activation_vectors")
        expect_keys(
            vectors,
            required={"target_layer18", "wrong_layer0"},
            path="$.activation_vectors",
        )
        for role in ("target_layer18", "wrong_layer0"):
            row = expect_object(vectors[role], f"$.activation_vectors.{role}")
            expect_keys(
                row,
                required={
                    "artifact",
                    "dtype",
                    "shape",
                    "role",
                    "layer_index",
                    "module_path",
                },
                path=f"$.activation_vectors.{role}",
            )
            parse_artifact_ref(row["artifact"], f"$.activation_vectors.{role}.artifact")
        expect_sha256(
            obj["capture_expectation_sha256"], "$.capture_expectation_sha256"
        )
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    _require_boundary(obj["boundary"])
    terminal = replay.terminal_receipt
    assert terminal is not None
    if _time(admitted_at) != _time(terminal.terminal_at):
        raise DiagnosticPhaseValidationError(
            "activation admission must use the exact terminal timestamp"
        )
    arrays = replay.binding.payload["execution_context"]["artifact_expectations"][
        "capture"
    ]["raw_arrays"]
    raw_target_ref = parse_artifact_ref(
        obj["activation_vectors"]["target_layer18"]["artifact"],
        "$.activation_vectors.target_layer18.artifact",
    )
    raw_wrong_ref = parse_artifact_ref(
        obj["activation_vectors"]["wrong_layer0"]["artifact"],
        "$.activation_vectors.wrong_layer0.artifact",
    )
    target_body = dict(projection.member_bytes)["target_vector"]
    wrong_layer_body = dict(projection.member_bytes)["wrong_layer_vector"]
    if raw_target_ref != target_ref or raw_wrong_ref != wrong_ref:
        raise DiagnosticPhaseValidationError(
            "activation refs must be derived from the exact admission-bound manifest"
        )
    if target_ref.artifact_id == wrong_ref.artifact_id or target_ref == wrong_ref:
        raise DiagnosticPhaseValidationError(
            "target and wrong-layer activation carriers must be distinct"
        )
    expected = _activation_admission_value(
        admission_id=admission_id,
        replay=replay,
        admitted_at=admitted_at,
        archive_ref=archive_ref,
        output_ref=output_ref,
        manifest_ref=retained_manifest_ref,
        target_ref=target_ref,
        wrong_ref=wrong_ref,
    )
    if obj != expected or subject != replay.snapshot.attempt_subject_sha256:
        raise DiagnosticPhaseValidationError(
            "activation admission differs from exact terminal/capture replay"
        )
    return DiagnosticPhaseActivationAdmissionArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        admission_id=admission_id,
        attempt_subject_sha256=subject,
        admitted_at=admitted_at,
        archive_admission_ref=archive_ref,
        child_output_ref=output_ref,
        archive_manifest_ref=projection.manifest_ref,
        archive_manifest_body=projection.manifest_bytes,
        archive_member_bodies=projection.member_bytes,
        target_vector=target_ref,
        wrong_layer_vector=wrong_ref,
        target_body=target_body,
        wrong_layer_body=wrong_layer_body,
        payload=freeze_json(obj),
    )


def build_diagnostic_phase_activation_admission(
    *,
    replay: DiagnosticAttemptReplay,
    archive_manifest: tuple[ArtifactRef, bytes],
    archive_member_bodies: Mapping[str, bytes],
) -> DiagnosticPhaseActivationAdmissionArtifact:
    if type(archive_manifest) is not tuple or len(archive_manifest) != 2:
        raise DiagnosticPhaseValidationError(
            "archive_manifest must be an exact (ArtifactRef, bytes) pair"
        )
    manifest_ref, manifest_body = archive_manifest
    projection, target_ref, wrong_ref = _validate_archive_projection(
        replay=replay,
        manifest_ref=manifest_ref,
        manifest_body=manifest_body,
        member_bodies=archive_member_bodies,
    )
    archive_ref, output_ref, retained_manifest_ref = _validate_completed_documents(
        replay, expected_manifest_ref=projection.manifest_ref
    )
    terminal = replay.terminal_receipt
    assert terminal is not None
    admission_id = (
        "diagnostic-phase-activation-admission-"
        + replay.snapshot.attempt_subject_sha256.lower()
    )
    raw = canonical_json_bytes(
        _activation_admission_value(
            admission_id=admission_id,
            replay=replay,
            admitted_at=terminal.terminal_at,
            archive_ref=archive_ref,
            output_ref=output_ref,
            manifest_ref=retained_manifest_ref,
            target_ref=target_ref,
            wrong_ref=wrong_ref,
        )
    )
    return load_diagnostic_phase_activation_admission(
        raw,
        replay=replay,
        archive_manifest_ref=projection.manifest_ref,
        archive_manifest_body=projection.manifest_bytes,
        archive_member_bodies=dict(projection.member_bytes),
    )


def replay_diagnostic_phase_activation_admission_projection(
    admission: DiagnosticPhaseActivationAdmissionArtifact,
) -> DiagnosticPhaseActivationAdmissionArtifact:
    """Reject a replaced projection without needing access to lifecycle internals."""

    _require_exact_type(
        admission, DiagnosticPhaseActivationAdmissionArtifact, "activation_admission"
    )
    _require_artifact_projection_storage(admission, "activation_admission")
    if (
        any(
            type(getattr(admission, name)) is not str
            for name in (
                "admission_id",
                "attempt_subject_sha256",
                "admitted_at",
            )
        )
        or any(
            type(getattr(admission, name)) is not ArtifactRef
            for name in (
                "archive_admission_ref",
                "child_output_ref",
                "archive_manifest_ref",
                "target_vector",
                "wrong_layer_vector",
            )
        )
        or type(admission.archive_manifest_body) is not bytes
        or type(admission.target_body) is not bytes
        or type(admission.wrong_layer_body) is not bytes
        or type(admission.archive_member_bodies) is not tuple
        or any(
            type(pair) is not tuple
            or len(pair) != 2
            or type(pair[0]) is not str
            or type(pair[1]) is not bytes
            for pair in admission.archive_member_bodies
        )
    ):
        raise DiagnosticPhaseValidationError(
            "activation admission projections must use exact immutable carrier types"
        )
    snapshot, obj = _canonical_object(
        admission.raw_bytes, "activation admission projection"
    )
    try:
        target_ref = parse_artifact_ref(
            obj["activation_vectors"]["target_layer18"]["artifact"],
            "$.activation_vectors.target_layer18.artifact",
        )
        wrong_ref = parse_artifact_ref(
            obj["activation_vectors"]["wrong_layer0"]["artifact"],
            "$.activation_vectors.wrong_layer0.artifact",
        )
        archive_ref = parse_artifact_ref(
            obj["source_documents"]["archive_admission"],
            "$.source_documents.archive_admission",
        )
        output_ref = parse_artifact_ref(
            obj["source_documents"]["child_output"],
            "$.source_documents.child_output",
        )
        manifest_ref = parse_artifact_ref(
            obj["source_documents"]["archive_manifest"],
            "$.source_documents.archive_manifest",
        )
    except (KeyError, TypeError, SchemaValidationError) as exc:
        raise DiagnosticPhaseValidationError(
            f"activation admission projection is malformed: {exc}"
        ) from exc
    try:
        projection = load_stagec_capture_archive_projection(
            manifest_ref=admission.archive_manifest_ref,
            manifest_bytes=admission.archive_manifest_body,
            member_bytes=dict(admission.archive_member_bodies),
        )
    except (SchemaValidationError, TypeError, ValueError) as exc:
        raise DiagnosticPhaseValidationError(
            f"activation admission archive projection drifted: {exc}"
        ) from exc
    derived_refs = _archive_member_refs(projection.manifest_bytes)
    members = dict(projection.member_bytes)
    if (
        sha256_bytes(snapshot) != admission.sha256
        or len(snapshot) != admission.byte_length
        or freeze_json(obj) != admission.payload
        or obj.get("admission_id") != admission.admission_id
        or obj.get("attempt_subject_sha256") != admission.attempt_subject_sha256
        or obj.get("admitted_at") != admission.admitted_at
        or archive_ref != admission.archive_admission_ref
        or output_ref != admission.child_output_ref
        or manifest_ref != admission.archive_manifest_ref
        or projection.manifest_ref != admission.archive_manifest_ref
        or projection.manifest_bytes != admission.archive_manifest_body
        or projection.member_bytes != admission.archive_member_bodies
        or derived_refs["target_vector"] != admission.target_vector
        or derived_refs["wrong_layer_vector"] != admission.wrong_layer_vector
        or target_ref != admission.target_vector
        or wrong_ref != admission.wrong_layer_vector
        or members["target_vector"] != admission.target_body
        or members["wrong_layer_vector"] != admission.wrong_layer_body
        or not target_ref.verify_bytes(admission.target_body)
        or not wrong_ref.verify_bytes(admission.wrong_layer_body)
    ):
        raise DiagnosticPhaseValidationError(
            "activation admission dataclass differs from exact raw/body projection"
        )
    target_row = obj["activation_vectors"]["target_layer18"]
    wrong_row = obj["activation_vectors"]["wrong_layer0"]
    if (
        target_row.get("dtype") != "<f4"
        or target_row.get("shape") != [DIAGNOSTIC_ACTIVATION_WIDTH]
        or target_row.get("role") != "target_final_token_activation"
        or target_row.get("layer_index") != 18
        or target_row.get("module_path")
        != "model.layers[18].mlp.down_proj"
        or wrong_row.get("dtype") != "<f4"
        or wrong_row.get("shape") != [DIAGNOSTIC_ACTIVATION_WIDTH]
        or wrong_row.get("role") != "wrong_layer_final_token_activation"
        or wrong_row.get("layer_index") != 0
        or wrong_row.get("module_path")
        != "model.layers[0].mlp.down_proj"
    ):
        raise DiagnosticPhaseValidationError(
            "activation admission layer/dtype/shape projection drifted"
        )
    _require_boundary(obj.get("boundary"))
    return admission


def replay_diagnostic_phase_registration_projection(
    registration: DiagnosticPhaseRegistrationArtifact,
) -> DiagnosticPhaseRegistrationArtifact:
    """Reject dataclass projection forgery without needing a plan replay."""

    _require_exact_type(
        registration, DiagnosticPhaseRegistrationArtifact, "registration"
    )
    _require_artifact_projection_storage(registration, "registration")
    if (
        any(
            type(getattr(registration, name)) is not str
            for name in (
                "registration_id",
                "phase_id",
                "phase_subject_sha256",
                "registered_at",
                "tenant_id",
            )
        )
        or type(registration.calibration_rule_ref) is not ArtifactRef
        or type(registration.ordered_subjects) is not tuple
        or any(type(item) is not str for item in registration.ordered_subjects)
        or type(registration.study_requests) is not tuple
    ):
        raise DiagnosticPhaseValidationError(
            "registration projections must use exact immutable carrier types"
        )
    snapshot, obj = _canonical_object(
        registration.raw_bytes, "diagnostic phase registration projection"
    )
    store_binding = replay_diagnostic_phase_store_binding_projection(
        registration.store_binding
    )
    if (
        sha256_bytes(snapshot) != registration.sha256
        or len(snapshot) != registration.byte_length
        or freeze_json(obj) != registration.payload
        or obj.get("registration_id") != registration.registration_id
        or obj.get("phase_id") != registration.phase_id
        or obj.get("phase_subject_sha256") != registration.phase_subject_sha256
        or obj.get("registered_at") != registration.registered_at
        or obj.get("tenant_id") != registration.tenant_id
        or store_binding != registration.store_binding
        or obj.get("diagnostic_phase_store_binding")
        != _artifact_ref_value(store_binding.artifact_ref)
        or obj.get("diagnostic_calibration_rule")
        != _artifact_ref_value(registration.calibration_rule_ref)
    ):
        raise DiagnosticPhaseValidationError(
            "registration dataclass differs from exact raw-byte projection"
        )
    rows = obj.get("ordered_attempts")
    if type(rows) is not list or len(rows) != DIAGNOSTIC_CASE_COUNT:
        raise DiagnosticPhaseValidationError("registration projection lacks 480 rows")
    subjects = tuple(row.get("attempt_subject_sha256") for row in rows)
    if subjects != registration.ordered_subjects:
        raise DiagnosticPhaseValidationError(
            "registration ordered-subject projection drifted"
        )
    if (
        type(registration.study_requests) is not tuple
        or len(registration.study_requests) != DIAGNOSTIC_CASE_COUNT
    ):
        raise DiagnosticPhaseValidationError(
            "registration study-request projection lacks 480 exact carriers"
        )
    for index, (row, request) in enumerate(
        zip(rows, registration.study_requests, strict=True)
    ):
        _require_exact_type(
            request,
            DiagnosticStudyRequestArtifact,
            f"registration.study_requests[{index}]",
        )
        _require_artifact_projection_storage(
            request, f"registration.study_requests[{index}]"
        )
        request_snapshot, request_obj = _canonical_object(
            request.raw_bytes, f"registration.study_requests[{index}]"
        )
        case_binding = request_obj.get("case_binding")
        try:
            capture_request = parse_artifact_ref(
                request_obj.get("capture_request"),
                f"registration.study_requests[{index}].capture_request",
            )
        except SchemaValidationError as exc:
            raise DiagnosticPhaseValidationError(str(exc)) from exc
        artifact_ref_count, artifact_refs_sha256 = _request_artifact_refs_binding(
            request.artifact_refs
        )
        if (
            any(
                type(getattr(request, name)) is not str
                for name in (
                    "request_id",
                    "created_at",
                    "study_id",
                    "case_id",
                )
            )
            or type(request.execution_ordinal) is not int
            or type(request.capture_request) is not ArtifactRef
            or type(request.artifact_refs) is not tuple
            or any(type(item) is not ArtifactRef for item in request.artifact_refs)
            or type(case_binding) is not dict
            or
            sha256_bytes(request_snapshot) != request.sha256
            or len(request_snapshot) != request.byte_length
            or freeze_json(request_obj) != request.payload
            or request_obj.get("request_id") != request.request_id
            or request_obj.get("created_at") != request.created_at
            or case_binding.get("study_id") != request.study_id
            or case_binding.get("case_id") != request.case_id
            or type(case_binding.get("execution_ordinal")) is not int
            or case_binding.get("execution_ordinal") != request.execution_ordinal
            or capture_request != request.capture_request
            or type(row.get("study_request_artifact_ref_count")) is not int
            or row.get("study_request_artifact_ref_count") != artifact_ref_count
            or type(row.get("study_request_ordered_artifact_refs_sha256")) is not str
            or row.get("study_request_ordered_artifact_refs_sha256")
            != artifact_refs_sha256
            or row.get("diagnostic_study_request")
            != _artifact_ref_value(request.artifact_ref)
            or row.get("execution_ordinal") != request.execution_ordinal
            or row.get("case_id") != request.case_id
        ):
            raise DiagnosticPhaseValidationError(
                f"registration study-request projection {index} drifted"
            )
    _require_boundary(obj.get("boundary"))
    return registration


def replay_diagnostic_phase_reconciliation_projection(
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
) -> DiagnosticPhaseReconciliationArtifact:
    """Strictly bind every reconciliation dataclass field to its raw bytes."""

    replay_diagnostic_phase_registration_projection(registration)
    _require_exact_type(
        reconciliation, DiagnosticPhaseReconciliationArtifact, "reconciliation"
    )
    _require_artifact_projection_storage(reconciliation, "reconciliation")
    if (
        any(
            type(getattr(reconciliation, name)) is not str
            for name in (
                "reconciliation_id",
                "phase_id",
                "phase_subject_sha256",
                "closed_at",
                "status",
                "execution_completed_at",
            )
        )
        or (
            reconciliation.execution_started_at is not None
            and type(reconciliation.execution_started_at) is not str
        )
        or any(
            type(getattr(reconciliation, name)) is not int
            for name in (
                "terminal_rows",
                "completed_rows",
                "analyzed_rows",
                "missing_rows",
                "excluded_rows",
            )
        )
        or any(
            type(getattr(reconciliation, name)) is not tuple
            for name in (
                "rejection_reasons",
                "ordered_attempt_subjects",
                "ordered_terminal_row_sha256s",
                "ordered_activation_binding_sha256s",
                "activation_admission_refs",
                "activation_vector_refs",
            )
        )
        or any(
            any(type(item) is not str for item in getattr(reconciliation, name))
            for name in (
                "rejection_reasons",
                "ordered_attempt_subjects",
                "ordered_terminal_row_sha256s",
                "ordered_activation_binding_sha256s",
            )
        )
    ):
        raise DiagnosticPhaseValidationError(
            "reconciliation projections must use exact immutable carrier types"
        )
    snapshot, obj = _canonical_object(
        reconciliation.raw_bytes, "diagnostic phase reconciliation projection"
    )
    accounting = obj.get("accounting")
    timing = obj.get("timing")
    row_sha256s = obj.get("ordered_terminal_row_sha256s")
    activation_sha256s = obj.get("ordered_activation_binding_sha256s")
    if (
        type(accounting) is not dict
        or type(timing) is not dict
        or type(row_sha256s) is not list
        or type(activation_sha256s) is not list
        or len(row_sha256s) != DIAGNOSTIC_CASE_COUNT
        or len(activation_sha256s) != DIAGNOSTIC_CASE_COUNT
        or sha256_bytes(snapshot) != reconciliation.sha256
        or len(snapshot) != reconciliation.byte_length
        or freeze_json(obj) != reconciliation.payload
        or obj.get("reconciliation_id") != reconciliation.reconciliation_id
        or obj.get("phase_id") != reconciliation.phase_id
        or obj.get("phase_subject_sha256") != reconciliation.phase_subject_sha256
        or obj.get("closed_at") != reconciliation.closed_at
        or obj.get("status") != reconciliation.status
        or tuple(obj.get("rejection_reasons", ()))
        != reconciliation.rejection_reasons
        or accounting.get("terminal_rows") != reconciliation.terminal_rows
        or accounting.get("completed_rows") != reconciliation.completed_rows
        or accounting.get("analyzed_rows") != reconciliation.analyzed_rows
        or accounting.get("missing_rows") != reconciliation.missing_rows
        or accounting.get("excluded_rows") != reconciliation.excluded_rows
        or timing.get("execution_started_at") != reconciliation.execution_started_at
        or timing.get("execution_completed_at")
        != reconciliation.execution_completed_at
        or tuple(row_sha256s) != reconciliation.ordered_terminal_row_sha256s
        or tuple(activation_sha256s)
        != reconciliation.ordered_activation_binding_sha256s
        or obj.get("phase_registration")
        != _artifact_ref_value(registration.artifact_ref)
        or reconciliation.phase_subject_sha256
        != registration.phase_subject_sha256
        or reconciliation.ordered_attempt_subjects
        != registration.ordered_subjects
    ):
        raise DiagnosticPhaseValidationError(
            "reconciliation dataclass differs from exact phase/raw projection"
        )
    try:
        for index, digest in enumerate(row_sha256s):
            expect_sha256(digest, f"$.ordered_terminal_row_sha256s[{index}]")
        for index, digest in enumerate(activation_sha256s):
            expect_sha256(
                digest, f"$.ordered_activation_binding_sha256s[{index}]"
            )
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    if (
        type(reconciliation.activation_admission_refs) is not tuple
        or type(reconciliation.activation_vector_refs) is not tuple
        or len(reconciliation.activation_admission_refs) != DIAGNOSTIC_CASE_COUNT
        or len(reconciliation.activation_vector_refs) != DIAGNOSTIC_CASE_COUNT
    ):
        raise DiagnosticPhaseValidationError(
            "reconciliation activation-admission projection lacks 480 ordered slots"
        )
    for index, (subject, binding_sha256, admission_ref, vector_refs) in enumerate(
        zip(
            registration.ordered_subjects,
            activation_sha256s,
            reconciliation.activation_admission_refs,
            reconciliation.activation_vector_refs,
            strict=True,
        )
    ):
        if admission_ref is None:
            if vector_refs is not None:
                raise DiagnosticPhaseValidationError(
                    f"reconciliation row {index} lost its null activation projection"
                )
        elif type(admission_ref) is not ArtifactRef or (
                type(vector_refs) is not tuple
                or len(vector_refs) != 2
                or any(type(item) is not ArtifactRef for item in vector_refs)
            ):
            raise DiagnosticPhaseValidationError(
                f"reconciliation row {index} activation refs have invalid exact types"
            )
        if binding_sha256 != _activation_binding_sha256(
            attempt_subject_sha256=subject,
            admission_ref=admission_ref,
            vector_refs=vector_refs,
        ):
            raise DiagnosticPhaseValidationError(
                f"reconciliation row {index} activation projection drifted"
            )
    _require_boundary(obj.get("boundary"))
    return reconciliation


def replay_diagnostic_phase_outcome_access_projection(
    outcome_access: DiagnosticPhaseOutcomeAccessArtifact,
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
) -> DiagnosticPhaseOutcomeAccessArtifact:
    """Strictly bind aggregate access and its embedded v1 carriers."""

    replay_diagnostic_phase_reconciliation_projection(
        reconciliation, registration=registration
    )
    _require_exact_type(
        outcome_access, DiagnosticPhaseOutcomeAccessArtifact, "outcome_access"
    )
    _require_artifact_projection_storage(outcome_access, "outcome_access")
    if (
        any(
            type(getattr(outcome_access, name)) is not str
            for name in (
                "access_id",
                "phase_id",
                "phase_subject_sha256",
                "accessed_at",
                "execution_started_at",
                "study_completed_at",
            )
        )
        or type(outcome_access.reconciliation_ref) is not ArtifactRef
        or type(outcome_access.activation_admissions) is not tuple
    ):
        raise DiagnosticPhaseValidationError(
            "outcome-access projections must use exact immutable carrier types"
        )
    index = outcome_access.outcome_index
    event = outcome_access.outcome_access_event
    _require_exact_type(index, DiagnosticStudyOutcomeIndexArtifact, "outcome_index")
    _require_exact_type(event, DiagnosticStudyOutcomeAccessEvent, "outcome_access_event")
    _require_artifact_projection_storage(index, "outcome_index")
    if (
        any(
            type(getattr(index, name)) is not str
            for name in (
                "outcome_index_id",
                "execution_started_at",
                "execution_completed_at",
                "accessed_at",
                "pre_outcome_chain_sha256",
            )
        )
        or
        type(event.raw_bytes) is not bytes
        or type(event.sha256) is not str
        or type(event.byte_length) is not int
        or any(
            type(getattr(event, name)) is not str
            for name in (
                "accessed_at",
                "execution_started_at",
                "study_completed_at",
                "sealed_pre_outcome_chain_sha256",
            )
        )
        or type(event.study_outcome_index) is not ArtifactRef
    ):
        raise DiagnosticPhaseValidationError(
            "outcome index/event projections must use exact immutable carrier types"
        )
    index_snapshot, index_obj = _canonical_object(index.raw_bytes, "outcome_index")
    event_snapshot, event_obj = _canonical_object(event.raw_bytes, "outcome_access_event")
    index_timing = index_obj.get("timing")
    try:
        event_index_ref = parse_artifact_ref(
            event_obj.get("study_outcome_index"),
            "$outcome_access_event.study_outcome_index",
        )
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    if (
        type(outcome_access.activation_admissions) is not tuple
        or len(outcome_access.activation_admissions) != DIAGNOSTIC_CASE_COUNT
    ):
        raise DiagnosticPhaseValidationError(
            "outcome access lacks its exact 480 post-access activation carriers"
        )
    for ordinal, admission in enumerate(outcome_access.activation_admissions):
        replay_diagnostic_phase_activation_admission_projection(admission)
        if (
            admission.attempt_subject_sha256 != registration.ordered_subjects[ordinal]
            or admission.artifact_ref
            != reconciliation.activation_admission_refs[ordinal]
            or (admission.target_vector, admission.wrong_layer_vector)
            != reconciliation.activation_vector_refs[ordinal]
        ):
            raise DiagnosticPhaseValidationError(
                f"outcome-access activation carrier {ordinal} drifted"
            )
    snapshot, obj = _canonical_object(
        outcome_access.raw_bytes, "diagnostic phase outcome-access projection"
    )
    if (
        sha256_bytes(index_snapshot) != index.sha256
        or len(index_snapshot) != index.byte_length
        or freeze_json(index_obj) != index.payload
        or index_obj.get("outcome_index_id") != index.outcome_index_id
        or type(index_timing) is not dict
        or index_timing.get("execution_started_at") != index.execution_started_at
        or index_timing.get("execution_completed_at")
        != index.execution_completed_at
        or index_timing.get("accessed_at") != index.accessed_at
        or index_obj.get("pre_outcome_chain_sha256")
        != index.pre_outcome_chain_sha256
        or sha256_bytes(event_snapshot) != event.sha256
        or len(event_snapshot) != event.byte_length
        or event_obj.get("accessed_at") != event.accessed_at
        or event_obj.get("execution_started_at") != event.execution_started_at
        or event_obj.get("study_completed_at") != event.study_completed_at
        or event_index_ref != event.study_outcome_index
        or event.study_outcome_index != index.artifact_ref
        or event_obj.get("sealed_pre_outcome_chain_sha256")
        != event.sealed_pre_outcome_chain_sha256
        or sha256_bytes(snapshot) != outcome_access.sha256
        or len(snapshot) != outcome_access.byte_length
        or freeze_json(obj) != outcome_access.payload
        or obj.get("access_id") != outcome_access.access_id
        or obj.get("phase_id") != outcome_access.phase_id
        or obj.get("phase_subject_sha256") != outcome_access.phase_subject_sha256
        or obj.get("accessed_at") != outcome_access.accessed_at
        or obj.get("execution_started_at") != outcome_access.execution_started_at
        or obj.get("study_completed_at") != outcome_access.study_completed_at
        or obj.get("phase_reconciliation")
        != _artifact_ref_value(reconciliation.artifact_ref)
        or outcome_access.reconciliation_ref != reconciliation.artifact_ref
    ):
        raise DiagnosticPhaseValidationError(
            "outcome-access dataclass differs from exact raw/dependency projection"
        )
    expected = _outcome_access_value(
        access_id=outcome_access.access_id,
        registration=registration,
        reconciliation=reconciliation,
        index=index,
        event=event,
        activation_admissions=outcome_access.activation_admissions,
    )
    if obj != expected:
        raise DiagnosticPhaseValidationError(
            "outcome-access raw bytes differ from exact dependency replay"
        )
    return outcome_access


def _validate_registration_dependencies(
    shared: DiagnosticSharedPlanReplayContext,
    study_requests: Sequence[DiagnosticStudyRequestArtifact],
) -> tuple[DiagnosticStudyRequestArtifact, ...]:
    _require_exact_type(shared, DiagnosticSharedPlanReplayContext, "shared_plan_context")
    if shared.case_count != DIAGNOSTIC_CASE_COUNT or len(shared.plan.cases) != DIAGNOSTIC_CASE_COUNT:
        raise DiagnosticPhaseValidationError("phase registration requires exactly 480 plan cases")
    if shared.chain.outcome_access is not None:
        raise DiagnosticPhaseValidationError(
            "phase registration must precede aggregate outcome access"
        )
    if shared.plan.pre_outcome_chain_sha256 != shared.chain.pre_outcome_chain_sha256:
        raise DiagnosticPhaseValidationError("plan and preregistration seal differ")
    if type(study_requests) not in (tuple, list) or len(study_requests) != DIAGNOSTIC_CASE_COUNT:
        raise DiagnosticPhaseValidationError(
            "phase registration requires exactly 480 study requests"
        )
    replayed: list[DiagnosticStudyRequestArtifact] = []
    group_ids: list[str] = []
    for index, (planned, supplied) in enumerate(
        zip(shared.plan.cases, study_requests, strict=True), start=1
    ):
        _require_exact_type(
            supplied, DiagnosticStudyRequestArtifact, f"study_requests[{index - 1}]"
        )
        try:
            request = shared.replay_study_request(supplied)
        except Exception as exc:
            raise DiagnosticPhaseValidationError(
                f"study_requests[{index - 1}] failed shared exact replay: {exc}"
            ) from exc
        if (
            planned.execution_ordinal != index
            or request.execution_ordinal != index
            or request.case_id != planned.case_id
            or request.study_id != shared.plan.study_id
            or request.capture_request != planned.capture_request
            or request.artifact_ref.media_type != DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE
        ):
            raise DiagnosticPhaseValidationError(
                f"study_requests[{index - 1}] is not the plan-ordered request"
            )
        replayed.append(request)
        group_ids.append(planned.base_intent_group_id)
    subjects = tuple(
        derive_diagnostic_attempt_subject_sha256(
            plan=shared.plan, study_request=request
        )
        for request in replayed
    )
    try:
        require_unique(subjects, "phase attempt subjects")
        require_unique((item.request_id for item in replayed), "phase study request IDs")
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    if len(set(group_ids)) != DIAGNOSTIC_GROUP_COUNT:
        raise DiagnosticPhaseValidationError("phase registration requires exactly 160 groups")
    for offset in range(0, DIAGNOSTIC_CASE_COUNT, 3):
        triplet = shared.plan.cases[offset : offset + 3]
        if (
            tuple(item.frozen_variant for item in triplet)
            != _CANONICAL_VARIANT_TRIPLET
            or len({item.base_intent_group_id for item in triplet}) != 1
        ):
            raise DiagnosticPhaseValidationError(
                "each plan-ordered group must contain the canonical adversarial/clean/null triplet"
            )
    return tuple(replayed)


def load_diagnostic_phase_registration(
    raw: bytes | bytearray | memoryview,
    *,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    study_requests: Sequence[DiagnosticStudyRequestArtifact],
    store_binding: DiagnosticPhaseStoreBindingArtifact,
) -> DiagnosticPhaseRegistrationArtifact:
    """Strict-load one exact 480-row issuance roster."""

    store_binding = load_diagnostic_phase_store_binding(store_binding.raw_bytes)
    requests = _validate_registration_dependencies(shared_plan_context, study_requests)
    bound = tuple(
        reference
        for reference in shared_plan_context.plan.execution_identity_artifacts
        if reference.media_type == DIAGNOSTIC_PHASE_STORE_BINDING_MEDIA_TYPE
    )
    if bound != (store_binding.artifact_ref,):
        raise DiagnosticPhaseValidationError(
            "plan must bind exactly this one pre-plan diagnostic phase store identity"
        )
    calibration_rules = tuple(
        reference
        for reference in shared_plan_context.plan.execution_identity_artifacts
        if reference.media_type == DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE
    )
    if len(calibration_rules) != 1:
        raise DiagnosticPhaseValidationError(
            "plan must prospectively bind exactly one diagnostic calibration rule"
        )
    calibration_rule_ref = calibration_rules[0]
    snapshot, obj = _canonical_object(raw, "diagnostic phase registration")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "registration_id",
                "phase_id",
                "phase_subject_sha256",
                "registered_at",
                "tenant_id",
                "pre_outcome_chain_sha256",
                "diagnostic_study_plan",
                "diagnostic_execution_contract",
                "diagnostic_phase_store_binding",
                "diagnostic_calibration_rule",
                "expected_row_count",
                "expected_group_count",
                "ordered_attempts",
                "issuance_policy",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_PHASE_REGISTRATION_SCHEMA:
            raise SchemaValidationError("wrong diagnostic phase registration schema")
        registration_id = expect_machine_id(obj["registration_id"], "$.registration_id")
        phase_id = expect_machine_id(obj["phase_id"], "$.phase_id")
        phase_subject = expect_sha256(
            obj["phase_subject_sha256"], "$.phase_subject_sha256"
        )
        registered_at = expect_timestamp(obj["registered_at"], "$.registered_at")
        tenant_id = expect_machine_id(obj["tenant_id"], "$.tenant_id")
        expect_sha256(
            obj["pre_outcome_chain_sha256"], "$.pre_outcome_chain_sha256"
        )
        parse_artifact_ref(obj["diagnostic_study_plan"], "$.diagnostic_study_plan")
        parse_artifact_ref(
            obj["diagnostic_execution_contract"], "$.diagnostic_execution_contract"
        )
        parse_artifact_ref(
            obj["diagnostic_phase_store_binding"],
            "$.diagnostic_phase_store_binding",
        )
        parse_artifact_ref(
            obj["diagnostic_calibration_rule"],
            "$.diagnostic_calibration_rule",
        )
        if expect_int(obj["expected_row_count"], "$.expected_row_count") != DIAGNOSTIC_CASE_COUNT:
            raise SchemaValidationError("expected_row_count must remain 480")
        if expect_int(obj["expected_group_count"], "$.expected_group_count") != DIAGNOSTIC_GROUP_COUNT:
            raise SchemaValidationError("expected_group_count must remain 160")
        rows = expect_list(obj["ordered_attempts"], "$.ordered_attempts")
        if len(rows) != DIAGNOSTIC_CASE_COUNT:
            raise SchemaValidationError("ordered_attempts must contain exactly 480 rows")
        policy = expect_object(obj["issuance_policy"], "$.issuance_policy")
        expect_keys(policy, required=_ISSUANCE_POLICY, path="$.issuance_policy")
        if policy != _ISSUANCE_POLICY:
            raise SchemaValidationError("issuance policy changed")
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    _require_boundary(obj["boundary"])

    expected = _registration_value(
        registration_id=registration_id,
        phase_id=phase_id,
        registered_at=registered_at,
        tenant_id=tenant_id,
        shared=shared_plan_context,
        store_binding=store_binding,
        calibration_rule_ref=calibration_rule_ref,
        requests=requests,
    )
    if obj != expected:
        raise DiagnosticPhaseValidationError(
            "diagnostic phase registration differs from the exact plan/request roster"
        )
    latest_request = max(_time(request.created_at) for request in requests)
    if _time(registered_at) < latest_request:
        raise DiagnosticPhaseValidationError(
            "phase registration cannot precede a registered study request"
        )
    if _time(registered_at) >= _time(shared_plan_context.plan.execution_window_start):
        raise DiagnosticPhaseValidationError(
            "phase registration must close before the execution window opens"
        )
    upstream_ids = {
        shared_plan_context.chain.base.preregistration_id,
        *(item.amendment_id for item in shared_plan_context.chain.amendments),
        *(item.artifact_id for item in shared_plan_context.chain.artifact_refs),
        shared_plan_context.plan.plan_id,
        shared_plan_context.execution_contract.contract_id,
        *(request.request_id for request in requests),
        *(case.capture_request.artifact_id for case in shared_plan_context.plan.cases),
    }
    if registration_id in upstream_ids:
        raise DiagnosticPhaseValidationError(
            "phase registration identifier collides with an upstream carrier"
        )
    ordered_subjects = tuple(
        row["attempt_subject_sha256"] for row in obj["ordered_attempts"]
    )
    return DiagnosticPhaseRegistrationArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        registration_id=registration_id,
        phase_id=phase_id,
        phase_subject_sha256=phase_subject,
        registered_at=registered_at,
        tenant_id=tenant_id,
        store_binding=store_binding,
        calibration_rule_ref=calibration_rule_ref,
        ordered_subjects=ordered_subjects,
        study_requests=requests,
        payload=freeze_json(obj),
    )


def build_diagnostic_phase_registration(
    *,
    registration_id: str,
    phase_id: str,
    registered_at: str,
    tenant_id: str,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    study_requests: Sequence[DiagnosticStudyRequestArtifact],
    store_binding: DiagnosticPhaseStoreBindingArtifact,
) -> DiagnosticPhaseRegistrationArtifact:
    """Build and strict-replay one exact phase roster before any issuance."""

    try:
        registration_id = expect_machine_id(registration_id, "registration_id")
        phase_id = expect_machine_id(phase_id, "phase_id")
        registered_at = expect_timestamp(registered_at, "registered_at")
        tenant_id = expect_machine_id(tenant_id, "tenant_id")
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    requests = _validate_registration_dependencies(shared_plan_context, study_requests)
    calibration_rules = tuple(
        reference
        for reference in shared_plan_context.plan.execution_identity_artifacts
        if reference.media_type == DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE
    )
    if len(calibration_rules) != 1:
        raise DiagnosticPhaseValidationError(
            "plan must prospectively bind exactly one diagnostic calibration rule"
        )
    raw = canonical_json_bytes(
        _registration_value(
            registration_id=registration_id,
            phase_id=phase_id,
            registered_at=registered_at,
            tenant_id=tenant_id,
            shared=shared_plan_context,
            store_binding=store_binding,
            calibration_rule_ref=calibration_rules[0],
            requests=requests,
        )
    )
    return load_diagnostic_phase_registration(
        raw,
        shared_plan_context=shared_plan_context,
        study_requests=requests,
        store_binding=store_binding,
    )


_T = TypeVar("_T")


class DiagnosticPhaseIssuanceGuard:
    """One locked, create-only phase state shared with the guarded store."""

    def __init__(self, registration: DiagnosticPhaseRegistrationArtifact) -> None:
        _require_exact_type(
            registration, DiagnosticPhaseRegistrationArtifact, "registration"
        )
        self._registration = registration
        self._expected = frozenset(registration.ordered_subjects)
        self._lock = threading.RLock()
        self._state = PHASE_OPEN
        self._reconciliation_sha256: str | None = None
        self._outcome_access_sha256: str | None = None

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def reconciliation_sha256(self) -> str | None:
        with self._lock:
            return self._reconciliation_sha256

    @property
    def outcome_access_sha256(self) -> str | None:
        with self._lock:
            return self._outcome_access_sha256

    def _require_registered_attempt(self, attempt: Any) -> None:
        if getattr(attempt, "tenant_id", None) != self._registration.tenant_id:
            raise DiagnosticPhaseConflict("attempt tenant is outside the registered phase")
        subject = getattr(attempt, "attempt_subject_sha256", None)
        if subject not in self._expected:
            raise DiagnosticPhaseConflict("attempt subject is outside the exact 480-row roster")
        index = self._registration.ordered_subjects.index(subject)
        row = self._registration.payload["ordered_attempts"][index]
        if (
            getattr(attempt, "attempt_ordinal", None) != 1
            or getattr(attempt, "case_execution_ordinal", None)
            != row["execution_ordinal"]
            or getattr(attempt, "case_id", None) != row["case_id"]
            or getattr(attempt, "study_id", None)
            != self._registration.study_requests[index].study_id
        ):
            raise DiagnosticPhaseConflict(
                "attempt projections differ from the registered plan-ordered row"
            )

    def _require_mutable_attempt(self, attempt: Any) -> None:
        self._require_registered_attempt(attempt)
        if self._state != PHASE_OPEN:
            raise DiagnosticPhaseConflict(
                "diagnostic phase is sealed; late issuance or mutation is forbidden"
            )

    def seal_once(
        self,
        builder: Callable[[], DiagnosticPhaseReconciliationArtifact],
    ) -> DiagnosticPhaseReconciliationArtifact:
        if not callable(builder):
            raise DiagnosticPhaseValidationError("seal builder must be callable")
        with self._lock:
            if self._state != PHASE_OPEN:
                raise DiagnosticPhaseConflict("diagnostic phase is already sealed")
            artifact = builder()
            _require_exact_type(
                artifact, DiagnosticPhaseReconciliationArtifact, "reconciliation"
            )
            if (
                artifact.phase_id != self._registration.phase_id
                or artifact.phase_subject_sha256
                != self._registration.phase_subject_sha256
            ):
                raise DiagnosticPhaseIntegrityError(
                    "reconciliation does not bind the guarded phase"
                )
            if artifact.status not in {
                PHASE_RECONCILED_CLEAN,
                PHASE_RECONCILED_REJECTED,
            }:
                raise DiagnosticPhaseIntegrityError(
                    "reconciliation has no closed phase status"
                )
            self._state = artifact.status
            self._reconciliation_sha256 = artifact.sha256
            return artifact

    def record_outcome_access_once(
        self,
        *,
        reconciliation: DiagnosticPhaseReconciliationArtifact,
        builder: Callable[[], DiagnosticPhaseOutcomeAccessArtifact],
    ) -> DiagnosticPhaseOutcomeAccessArtifact:
        with self._lock:
            if self._state != PHASE_RECONCILED_CLEAN:
                raise DiagnosticPhaseConflict(
                    "aggregate outcome access requires a clean sealed phase"
                )
            if reconciliation.sha256 != self._reconciliation_sha256:
                raise DiagnosticPhaseConflict(
                    "aggregate outcome access supplied a different reconciliation"
                )
            artifact = builder()
            _require_exact_type(
                artifact, DiagnosticPhaseOutcomeAccessArtifact, "outcome access"
            )
            if (
                artifact.phase_subject_sha256
                != self._registration.phase_subject_sha256
                or artifact.reconciliation_ref != reconciliation.artifact_ref
            ):
                raise DiagnosticPhaseIntegrityError(
                    "outcome access does not bind the guarded reconciliation"
                )
            self._state = PHASE_OUTCOME_ACCESSED
            self._outcome_access_sha256 = artifact.sha256
            return artifact


class GuardedDiagnosticLifecycleStore:
    """Store adapter serializing all attempt writes with the phase seal.

    The adapter intentionally exposes no inner-store property.  Callers must
    route lifecycle operations through the :class:`DiagnosticPhaseCoordinator`.
    """

    def __init__(
        self,
        inner: DiagnosticLifecycleStore,
        guard: DiagnosticPhaseIssuanceGuard,
    ) -> None:
        if inner is None:
            raise DiagnosticPhaseValidationError("an inner lifecycle store is required")
        _require_exact_type(guard, DiagnosticPhaseIssuanceGuard, "guard")
        required = {
            "create_attempt",
            "compare_and_swap",
            "get_attempt",
            "list_attempts",
            "list_events",
            "durability_profile",
        }
        if any(not hasattr(inner, item) for item in required):
            raise DiagnosticPhaseValidationError(
                "inner does not implement the lifecycle store protocol"
            )
        self.__inner = inner
        self.__guard = guard

    @property
    def durability_profile(self) -> Mapping[str, Any]:
        profile = dict(self.__inner.durability_profile)
        profile["diagnostic_phase_guard"] = "PROCESS_LOCAL_LOCKED_EXACT_480"
        profile["phase_subject_sha256"] = self.__guard._registration.phase_subject_sha256
        return MappingProxyType(profile)

    def create_attempt(self, attempt: Any, event: Any) -> Any:
        with self.__guard._lock:
            self.__guard._require_mutable_attempt(attempt)
            return self.__inner.create_attempt(attempt, event)

    def compare_and_swap(
        self, attempt: Any, event: Any, *, expected_version: int
    ) -> Any:
        with self.__guard._lock:
            self.__guard._require_mutable_attempt(attempt)
            return self.__inner.compare_and_swap(
                attempt, event, expected_version=expected_version
            )

    def get_attempt(self, tenant_id: str, attempt_subject_sha256: str) -> Any:
        with self.__guard._lock:
            if (
                tenant_id != self.__guard._registration.tenant_id
                or attempt_subject_sha256 not in self.__guard._expected
            ):
                raise DiagnosticPhaseConflict("read scope is outside the registered roster")
            return self.__inner.get_attempt(tenant_id, attempt_subject_sha256)

    def list_attempts(self, tenant_id: str) -> tuple[Any, ...]:
        with self.__guard._lock:
            if tenant_id != self.__guard._registration.tenant_id:
                raise DiagnosticPhaseConflict("tenant is outside the registered phase")
            return self.__inner.list_attempts(tenant_id)

    def list_events(self, tenant_id: str, attempt_subject_sha256: str) -> tuple[Any, ...]:
        with self.__guard._lock:
            if (
                tenant_id != self.__guard._registration.tenant_id
                or attempt_subject_sha256 not in self.__guard._expected
            ):
                raise DiagnosticPhaseConflict("event scope is outside the registered phase")
            return self.__inner.list_events(tenant_id, attempt_subject_sha256)


def _terminal_roles(row: DiagnosticAttemptReplay) -> tuple[str, ...]:
    terminal = row.terminal_receipt
    if terminal is None:
        raise DiagnosticPhaseIntegrityError("terminal replay lacks a terminal receipt")
    return tuple(
        item["role"] for item in terminal.payload["terminal"]["produced_artifacts"]
    )


def _row_value(
    *,
    registration_row: Mapping[str, Any],
    replay: DiagnosticAttemptReplay,
    activation_admission: DiagnosticPhaseActivationAdmissionArtifact | None,
) -> dict[str, Any]:
    terminal = replay.terminal_receipt
    if terminal is None:
        raise DiagnosticPhaseIntegrityError("terminal row lacks exact terminal bytes")
    return {
        "execution_ordinal": registration_row["execution_ordinal"],
        "case_id": registration_row["case_id"],
        "base_intent_group_id": registration_row["base_intent_group_id"],
        "frozen_variant": registration_row["frozen_variant"],
        "attempt_subject_sha256": replay.snapshot.attempt_subject_sha256,
        "attempt_ordinal": replay.snapshot.attempt_ordinal,
        "diagnostic_study_request": thaw_json(
            registration_row["diagnostic_study_request"]
        ),
        "binding": _artifact_ref_value(replay.binding.artifact_ref),
        "authorization": (
            None
            if replay.authorization is None
            else _artifact_ref_value(replay.authorization.artifact_ref)
        ),
        "terminal_receipt": _artifact_ref_value(terminal.artifact_ref),
        "state": replay.snapshot.state,
        "terminal_status": terminal.terminal_status,
        "invocation_certainty": terminal.invocation_certainty,
        "worker_started_at": terminal.worker_started_at,
        "terminal_at": terminal.terminal_at,
        "produced_artifact_roles": list(_terminal_roles(replay)),
        "produced_artifacts": [
            _artifact_ref_value(reference) for reference in terminal.produced_artifact_refs
        ],
        "activation_admission": (
            None
            if activation_admission is None
            else _artifact_ref_value(activation_admission.artifact_ref)
        ),
        "activation_vectors": (
            None
            if activation_admission is None
            else {
                "target_layer18": _artifact_ref_value(
                    activation_admission.target_vector
                ),
                "wrong_layer0": _artifact_ref_value(
                    activation_admission.wrong_layer_vector
                ),
            }
        ),
        "event_count": replay.snapshot.event_count,
        "head_event_sha256": replay.snapshot.head_event_sha256,
    }


def _activation_binding_sha256(
    *,
    attempt_subject_sha256: str,
    admission_ref: ArtifactRef | None,
    vector_refs: tuple[ArtifactRef, ArtifactRef] | None,
) -> str:
    if (admission_ref is None) != (vector_refs is None):
        raise DiagnosticPhaseValidationError(
            "activation binding must be wholly present or wholly absent"
        )
    if vector_refs is not None and (
        type(vector_refs) is not tuple
        or len(vector_refs) != 2
        or any(type(item) is not ArtifactRef for item in vector_refs)
    ):
        raise DiagnosticPhaseValidationError(
            "activation binding vector refs must be an exact ArtifactRef pair"
        )
    return canonical_sha256(
        {
            "domain": "cas_harness_v2.diagnostic_phase_activation_binding.v1",
            "attempt_subject_sha256": attempt_subject_sha256,
            "binding": (
                None
                if admission_ref is None
                else {
                    "activation_admission": _artifact_ref_value(admission_ref),
                    "target_layer18": _artifact_ref_value(vector_refs[0]),
                    "wrong_layer0": _artifact_ref_value(
                        vector_refs[1]
                    ),
                }
            ),
        }
    )


def _validate_phase_replays(
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
    replays: Sequence[DiagnosticAttemptReplay],
    lifecycle_reconciliation: DiagnosticAttemptReconciliation,
) -> tuple[DiagnosticAttemptReplay, ...]:
    _require_exact_type(
        registration, DiagnosticPhaseRegistrationArtifact, "registration"
    )
    _require_exact_type(
        lifecycle_reconciliation,
        DiagnosticAttemptReconciliation,
        "lifecycle_reconciliation",
    )
    if type(replays) not in (tuple, list) or len(replays) != DIAGNOSTIC_CASE_COUNT:
        raise DiagnosticPhaseIntegrityError(
            "phase closure requires exactly 480 replayed terminal rows"
        )
    rows = tuple(replays)
    if any(type(item) is not DiagnosticAttemptReplay for item in rows):
        raise DiagnosticPhaseIntegrityError("phase closure received a forged replay row")
    actual_subjects = tuple(item.snapshot.attempt_subject_sha256 for item in rows)
    if actual_subjects != registration.ordered_subjects:
        raise DiagnosticPhaseIntegrityError(
            "terminal rows are not the exact plan-ordered registered subject inventory"
        )
    if (
        lifecycle_reconciliation.tenant_id != registration.tenant_id
        or lifecycle_reconciliation.attempt_count != DIAGNOSTIC_CASE_COUNT
        or not lifecycle_reconciliation.integrity_clean
        or not lifecycle_reconciliation.all_terminal
        or lifecycle_reconciliation.issues
    ):
        raise DiagnosticPhaseIntegrityError(
            "lifecycle reconciliation is not exact, clean, terminal, and issue-free"
        )
    for index, (registered, replay) in enumerate(
        zip(registration.payload["ordered_attempts"], rows, strict=True), start=1
    ):
        terminal = replay.terminal_receipt
        if terminal is None or replay.snapshot.state not in DIAGNOSTIC_TERMINAL_STATES:
            raise DiagnosticPhaseIntegrityError(f"row {index} is not terminal")
        if (
            replay.snapshot.tenant_id != registration.tenant_id
            or replay.snapshot.attempt_ordinal != 1
            or replay.snapshot.case_execution_ordinal != index
            or replay.snapshot.case_id != registered["case_id"]
            or replay.binding.case_execution_ordinal != index
            or replay.binding.case_id != registered["case_id"]
            or replay.binding.payload["execution_context"]["attempt_binding"][
                "attempt_subject_sha256"
            ]
            != registration.ordered_subjects[index - 1]
            or replay.snapshot.state != terminal.terminal_status
        ):
            raise DiagnosticPhaseIntegrityError(
                f"row {index} differs from its exact registered attempt projections"
            )
    try:
        validate_diagnostic_execution_batch_uniqueness(
            bindings=tuple(item.binding for item in rows),
            authorizations=tuple(item.authorization for item in rows),
            terminal_receipts=tuple(item.terminal_receipt for item in rows),
        )
    except (SchemaValidationError, ValueError, TypeError) as exc:
        raise DiagnosticPhaseIntegrityError(
            f"global diagnostic batch uniqueness failed: {exc}"
        ) from exc
    return rows


def _validate_phase_activation_admissions(
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
    rows: tuple[DiagnosticAttemptReplay, ...],
    activation_admissions: Sequence[
        DiagnosticPhaseActivationAdmissionArtifact | None
    ],
) -> tuple[DiagnosticPhaseActivationAdmissionArtifact | None, ...]:
    if (
        type(activation_admissions) not in (tuple, list)
        or len(activation_admissions) != DIAGNOSTIC_CASE_COUNT
    ):
        raise DiagnosticPhaseIntegrityError(
            "phase closure requires exactly 480 ordered activation-admission slots"
        )
    admissions = tuple(activation_admissions)
    identifiers: list[str] = []
    for index, (row, supplied) in enumerate(zip(rows, admissions, strict=True), start=1):
        if row.snapshot.state == COMPLETED:
            if type(supplied) is not DiagnosticPhaseActivationAdmissionArtifact:
                raise DiagnosticPhaseIntegrityError(
                    f"completed row {index} lacks its exact activation admission"
                )
            replayed = load_diagnostic_phase_activation_admission(
                supplied.raw_bytes,
                replay=row,
                archive_manifest_ref=supplied.archive_manifest_ref,
                archive_manifest_body=supplied.archive_manifest_body,
                archive_member_bodies=dict(supplied.archive_member_bodies),
            )
            if replayed != supplied:
                raise DiagnosticPhaseIntegrityError(
                    f"activation admission {index} differs from fresh replay"
                )
            identifiers.extend(
                (
                    replayed.admission_id,
                    replayed.target_vector.artifact_id,
                    replayed.wrong_layer_vector.artifact_id,
                )
            )
        elif supplied is not None:
            raise DiagnosticPhaseIntegrityError(
                f"non-completed row {index} cannot carry activation vectors"
            )
    try:
        require_unique(identifiers, "phase activation admission/vector identifiers")
    except SchemaValidationError as exc:
        raise DiagnosticPhaseIntegrityError(str(exc)) from exc
    dependency_ids = {
        registration.registration_id,
        registration.phase_id,
        registration.store_binding.binding_id,
        registration.calibration_rule_ref.artifact_id,
        *_artifact_ids_in_json(registration.payload),
        *(
            artifact_id
            for row in rows
            for artifact_id in _artifact_ids_in_json(
                row.terminal_receipt.payload  # type: ignore[union-attr]
            )
        ),
    }
    collision = dependency_ids.intersection(identifiers)
    if collision:
        raise DiagnosticPhaseIntegrityError(
            "activation admission/vector identifier collides with phase dependency: "
            + sorted(collision)[0]
        )
    return admissions


def _accounting(
    rows: tuple[DiagnosticAttemptReplay, ...],
    activation_admissions: tuple[
        DiagnosticPhaseActivationAdmissionArtifact | None, ...
    ],
) -> dict[str, Any]:
    statuses = Counter(item.snapshot.state for item in rows)
    certainties = Counter(
        item.terminal_receipt.invocation_certainty  # type: ignore[union-attr]
        for item in rows
    )
    complete = 0
    for row, admission in zip(rows, activation_admissions, strict=True):
        terminal = row.terminal_receipt
        assert terminal is not None
        if (
            terminal.terminal_status == COMPLETED
            and terminal.invocation_certainty == "EXACTLY_ONE"
            and _terminal_roles(row) == ("archive_admission", "child_output")
            and set(row.produced_artifact_bodies)
            == {"archive_admission", "child_output"}
            and admission is not None
        ):
            complete += 1
    indeterminate = certainties.get("INDETERMINATE_ZERO_OR_ONE", 0)
    exactly_one = certainties.get("EXACTLY_ONE", 0)
    return {
        "enrolled_rows": DIAGNOSTIC_CASE_COUNT,
        "terminal_rows": len(rows),
        "completed_rows": complete,
        "analyzed_rows": complete,
        "missing_rows": DIAGNOSTIC_CASE_COUNT - complete,
        "excluded_rows": 0,
        "group_count": DIAGNOSTIC_GROUP_COUNT,
        "status_counts": {
            status: statuses.get(status, 0)
            for status in sorted(DIAGNOSTIC_TERMINAL_STATUSES)
        },
        "invocation_certainty_counts": {
            certainty: certainties.get(certainty, 0)
            for certainty in (
                "EXACTLY_ZERO",
                "EXACTLY_ONE",
                "INDETERMINATE_ZERO_OR_ONE",
            )
        },
        "model_invocation_request_count_minimum": exactly_one,
        "model_invocation_request_count_maximum": exactly_one + indeterminate,
        "row_accounting_identity": (
            "ENROLLED_EQUALS_ANALYZED_PLUS_MISSING_PLUS_EXCLUDED"
        ),
    }


def _rejection_reasons(rows: tuple[DiagnosticAttemptReplay, ...]) -> tuple[str, ...]:
    states = {item.snapshot.state for item in rows}
    reasons: list[str] = []
    if REJECTED in states:
        reasons.append("VALIDATED_ROW_REJECTION")
    if EXPIRED in states:
        reasons.append("EXECUTION_WINDOW_EXPIRED")
    if FAILED in states or INDETERMINATE in states:
        reasons.append("COMPLETE_OUTPUT_SET_UNAVAILABLE")
    if any(item.snapshot.state != COMPLETED for item in rows) and not reasons:
        reasons.append("COMPLETE_OUTPUT_SET_UNAVAILABLE")
    return tuple(reasons)


def _reconciliation_value(
    *,
    reconciliation_id: str,
    registration: DiagnosticPhaseRegistrationArtifact,
    closed_at: str,
    rows: tuple[DiagnosticAttemptReplay, ...],
    activation_admissions: tuple[
        DiagnosticPhaseActivationAdmissionArtifact | None, ...
    ],
    lifecycle_reconciliation: DiagnosticAttemptReconciliation,
) -> dict[str, Any]:
    accounting = _accounting(rows, activation_admissions)
    clean = accounting["completed_rows"] == DIAGNOSTIC_CASE_COUNT
    status = PHASE_RECONCILED_CLEAN if clean else PHASE_RECONCILED_REJECTED
    reasons = () if clean else _rejection_reasons(rows)
    worker_starts = tuple(
        item.terminal_receipt.worker_started_at  # type: ignore[union-attr]
        for item in rows
        if item.terminal_receipt is not None
        and item.terminal_receipt.worker_started_at is not None
    )
    terminal_times = tuple(
        item.terminal_receipt.terminal_at  # type: ignore[union-attr]
        for item in rows
    )
    full_rows = tuple(
        _row_value(
            registration_row=registered,
            replay=replay,
            activation_admission=admission,
        )
        for registered, replay, admission in zip(
            registration.payload["ordered_attempts"],
            rows,
            activation_admissions,
            strict=True,
        )
    )
    return {
        "schema_version": DIAGNOSTIC_PHASE_RECONCILIATION_SCHEMA,
        "reconciliation_id": reconciliation_id,
        "phase_id": registration.phase_id,
        "phase_subject_sha256": registration.phase_subject_sha256,
        "closed_at": closed_at,
        "phase_registration": _artifact_ref_value(registration.artifact_ref),
        "status": status,
        "rejection_reasons": list(reasons),
        "complete_output_set_available": clean,
        "timing": {
            "execution_started_at": min(worker_starts, key=_time)
            if worker_starts
            else None,
            "execution_completed_at": max(terminal_times, key=_time),
        },
        "accounting": accounting,
        "lifecycle_reconciliation": {
            "tenant_id": lifecycle_reconciliation.tenant_id,
            "attempt_count": lifecycle_reconciliation.attempt_count,
            "event_count": lifecycle_reconciliation.event_count,
            "state_counts": dict(lifecycle_reconciliation.state_counts),
            "integrity_clean": lifecycle_reconciliation.integrity_clean,
            "all_terminal": lifecycle_reconciliation.all_terminal,
            "issue_count": len(lifecycle_reconciliation.issues),
            "backend_durability_profile": thaw_json(
                lifecycle_reconciliation.backend_durability_profile
            ),
        },
        "ordered_terminal_row_sha256s": [
            canonical_sha256(
                {
                    "domain": "cas_harness_v2.diagnostic_phase_terminal_row.v1",
                    "row": row,
                }
            )
            for row in full_rows
        ],
        "ordered_activation_binding_sha256s": [
            _activation_binding_sha256(
                attempt_subject_sha256=subject,
                admission_ref=(
                    None if admission is None else admission.artifact_ref
                ),
                vector_refs=(
                    None
                    if admission is None
                    else (admission.target_vector, admission.wrong_layer_vector)
                ),
            )
            for subject, admission in zip(
                registration.ordered_subjects,
                activation_admissions,
                strict=True,
            )
        ],
        "boundary": dict(_BOUNDARY),
    }


def load_diagnostic_phase_reconciliation(
    raw: bytes | bytearray | memoryview,
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
    replays: Sequence[DiagnosticAttemptReplay],
    activation_admissions: Sequence[
        DiagnosticPhaseActivationAdmissionArtifact | None
    ],
    lifecycle_reconciliation: DiagnosticAttemptReconciliation,
) -> DiagnosticPhaseReconciliationArtifact:
    """Strict-load a derived, plan-ordered, exactly-480 closure carrier."""

    replay_diagnostic_phase_registration_projection(registration)
    rows = _validate_phase_replays(
        registration=registration,
        replays=replays,
        lifecycle_reconciliation=lifecycle_reconciliation,
    )
    admissions = _validate_phase_activation_admissions(
        registration=registration,
        rows=rows,
        activation_admissions=activation_admissions,
    )
    snapshot, obj = _canonical_object(raw, "diagnostic phase reconciliation")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "reconciliation_id",
                "phase_id",
                "phase_subject_sha256",
                "closed_at",
                "phase_registration",
                "status",
                "rejection_reasons",
                "complete_output_set_available",
                "timing",
                "accounting",
                "lifecycle_reconciliation",
                "ordered_terminal_row_sha256s",
                "ordered_activation_binding_sha256s",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_PHASE_RECONCILIATION_SCHEMA:
            raise SchemaValidationError("wrong diagnostic phase reconciliation schema")
        reconciliation_id = expect_machine_id(
            obj["reconciliation_id"], "$.reconciliation_id"
        )
        closed_at = expect_timestamp(obj["closed_at"], "$.closed_at")
        status = expect_enum(
            obj["status"],
            {PHASE_RECONCILED_CLEAN, PHASE_RECONCILED_REJECTED},
            "$.status",
        )
        reasons = tuple(
            expect_enum(
                item,
                {
                    "VALIDATED_ROW_REJECTION",
                    "EXECUTION_WINDOW_EXPIRED",
                    "COMPLETE_OUTPUT_SET_UNAVAILABLE",
                },
                f"$.rejection_reasons[{index}]",
            )
            for index, item in enumerate(
                expect_list(
                    obj["rejection_reasons"],
                    "$.rejection_reasons",
                    nonempty=False,
                )
            )
        )
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError("rejection_reasons must be unique")
        expect_bool(
            obj["complete_output_set_available"],
            "$.complete_output_set_available",
        )
        parse_artifact_ref(obj["phase_registration"], "$.phase_registration")
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    _require_boundary(obj["boundary"])
    expected = _reconciliation_value(
        reconciliation_id=reconciliation_id,
        registration=registration,
        closed_at=closed_at,
        rows=rows,
        activation_admissions=admissions,
        lifecycle_reconciliation=lifecycle_reconciliation,
    )
    if obj != expected:
        raise DiagnosticPhaseValidationError(
            "diagnostic phase reconciliation differs from derived replay/accounting"
        )
    terminal_times = tuple(
        _time(item.terminal_receipt.terminal_at)  # type: ignore[union-attr]
        for item in rows
    )
    if _time(closed_at) < max(terminal_times):
        raise DiagnosticPhaseValidationError(
            "phase closure cannot precede the latest terminal receipt"
        )
    dependency_ids = {
        registration.registration_id,
        *_artifact_ids_in_json(registration.payload),
        *(
            artifact_id
            for replay in rows
            for artifact_id in _artifact_ids_in_json(replay.terminal_receipt.payload)  # type: ignore[union-attr]
        ),
        *(
            artifact_id
            for admission in admissions
            if admission is not None
            for artifact_id in _artifact_ids_in_json(admission.payload)
        ),
    }
    if reconciliation_id in dependency_ids:
        raise DiagnosticPhaseValidationError(
            "phase reconciliation identifier collides with a retained carrier"
        )
    accounting = obj["accounting"]
    timing = obj["timing"]
    return DiagnosticPhaseReconciliationArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        reconciliation_id=reconciliation_id,
        phase_id=registration.phase_id,
        phase_subject_sha256=registration.phase_subject_sha256,
        closed_at=closed_at,
        status=status,
        rejection_reasons=reasons,
        terminal_rows=accounting["terminal_rows"],
        completed_rows=accounting["completed_rows"],
        analyzed_rows=accounting["analyzed_rows"],
        missing_rows=accounting["missing_rows"],
        excluded_rows=accounting["excluded_rows"],
        execution_started_at=timing["execution_started_at"],
        execution_completed_at=timing["execution_completed_at"],
        ordered_attempt_subjects=registration.ordered_subjects,
        ordered_terminal_row_sha256s=tuple(
            obj["ordered_terminal_row_sha256s"]
        ),
        ordered_activation_binding_sha256s=tuple(
            obj["ordered_activation_binding_sha256s"]
        ),
        activation_admission_refs=tuple(
            None if item is None else item.artifact_ref for item in admissions
        ),
        activation_vector_refs=tuple(
            None
            if item is None
            else (item.target_vector, item.wrong_layer_vector)
            for item in admissions
        ),
        payload=freeze_json(obj),
    )


def build_diagnostic_phase_reconciliation(
    *,
    reconciliation_id: str,
    registration: DiagnosticPhaseRegistrationArtifact,
    closed_at: str,
    replays: Sequence[DiagnosticAttemptReplay],
    activation_admissions: Sequence[
        DiagnosticPhaseActivationAdmissionArtifact | None
    ],
    lifecycle_reconciliation: DiagnosticAttemptReconciliation,
) -> DiagnosticPhaseReconciliationArtifact:
    """Derive and strict-replay a closed phase carrier."""

    try:
        reconciliation_id = expect_machine_id(
            reconciliation_id, "reconciliation_id"
        )
        closed_at = expect_timestamp(closed_at, "closed_at")
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    rows = _validate_phase_replays(
        registration=registration,
        replays=replays,
        lifecycle_reconciliation=lifecycle_reconciliation,
    )
    admissions = _validate_phase_activation_admissions(
        registration=registration,
        rows=rows,
        activation_admissions=activation_admissions,
    )
    raw = canonical_json_bytes(
        _reconciliation_value(
            reconciliation_id=reconciliation_id,
            registration=registration,
            closed_at=closed_at,
            rows=rows,
            activation_admissions=admissions,
            lifecycle_reconciliation=lifecycle_reconciliation,
        )
    )
    return load_diagnostic_phase_reconciliation(
        raw,
        registration=registration,
        replays=rows,
        activation_admissions=admissions,
        lifecycle_reconciliation=lifecycle_reconciliation,
    )


def _clone_pre_outcome_chain(
    chain: DiagnosticPreregistrationChain,
) -> DiagnosticPreregistrationChain:
    _require_exact_type(chain, DiagnosticPreregistrationChain, "chain")
    if chain.outcome_access is not None:
        raise DiagnosticPhaseConflict("aggregate outcome access was already recorded")
    clone = DiagnosticPreregistrationChain(chain.base)
    for amendment in chain.amendments:
        clone.append_amendment(amendment.raw_bytes)
    if clone.pre_outcome_chain_sha256 != chain.pre_outcome_chain_sha256:
        raise DiagnosticPhaseIntegrityError("pre-outcome chain clone differs")
    return clone


def _outcome_index_raw(
    *,
    outcome_index_id: str,
    chain: DiagnosticPreregistrationChain,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    accessed_at: str,
) -> bytes:
    if reconciliation.execution_started_at is None:
        raise DiagnosticPhaseConflict(
            "clean reconciliation must derive a worker execution start"
        )
    return canonical_json_bytes(
        {
            "schema_version": DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA,
            "outcome_index_id": outcome_index_id,
            "diagnostic_preregistration": _artifact_ref_value(chain.base.artifact_ref),
            "pre_outcome_chain_sha256": chain.pre_outcome_chain_sha256,
            "timing": {
                "execution_started_at": reconciliation.execution_started_at,
                "execution_completed_at": reconciliation.execution_completed_at,
                "accessed_at": accessed_at,
            },
            "boundary": dict(_OUTCOME_BOUNDARY),
        }
    )


def _outcome_access_value(
    *,
    access_id: str,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    index: DiagnosticStudyOutcomeIndexArtifact,
    event: DiagnosticStudyOutcomeAccessEvent,
    activation_admissions: tuple[DiagnosticPhaseActivationAdmissionArtifact, ...],
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_PHASE_OUTCOME_ACCESS_SCHEMA,
        "access_id": access_id,
        "phase_id": registration.phase_id,
        "phase_subject_sha256": registration.phase_subject_sha256,
        "accessed_at": event.accessed_at,
        "execution_started_at": event.execution_started_at,
        "study_completed_at": event.study_completed_at,
        "phase_registration": _artifact_ref_value(registration.artifact_ref),
        "phase_reconciliation": _artifact_ref_value(reconciliation.artifact_ref),
        "diagnostic_study_outcome_index": _artifact_ref_value(index.artifact_ref),
        "diagnostic_outcome_access_event": {
            "sha256": event.sha256,
            "byte_length": event.byte_length,
            "sealed_pre_outcome_chain_sha256": (
                event.sealed_pre_outcome_chain_sha256
            ),
        },
        "activation_admission_inventory_sha256": canonical_sha256(
            {
                "domain": "cas_harness_v2.diagnostic_post_access_activation_inventory.v1",
                "ordered_admissions": [
                    _artifact_ref_value(item.artifact_ref)
                    for item in activation_admissions
                ],
            }
        ),
        "access_scope": "AGGREGATE_STUDY_ONLY_AFTER_COMPLETE_CLEAN_RECONCILIATION",
        "coordinator_public_api_outcome_release": (
            "CALIBRATION_DATASET_ONLY_AFTER_THIS_AGGREGATE_ACCESS"
        ),
        "out_of_band_read_prevention": "NOT_ESTABLISHED",
        "boundary": dict(_BOUNDARY),
    }


def load_diagnostic_phase_outcome_access(
    raw: bytes | bytearray | memoryview,
    *,
    registration: DiagnosticPhaseRegistrationArtifact,
    reconciliation: DiagnosticPhaseReconciliationArtifact,
    outcome_index: DiagnosticStudyOutcomeIndexArtifact,
    outcome_access_event: DiagnosticStudyOutcomeAccessEvent,
    activation_admissions: Sequence[DiagnosticPhaseActivationAdmissionArtifact],
) -> DiagnosticPhaseOutcomeAccessArtifact:
    """Strict-load the aggregate-only access wrapper for a clean phase."""

    replay_diagnostic_phase_reconciliation_projection(
        reconciliation, registration=registration
    )
    for value, expected, path in (
        (outcome_index, DiagnosticStudyOutcomeIndexArtifact, "outcome_index"),
        (outcome_access_event, DiagnosticStudyOutcomeAccessEvent, "outcome_access_event"),
    ):
        _require_exact_type(value, expected, path)
    if (
        reconciliation.status != PHASE_RECONCILED_CLEAN
        or reconciliation.completed_rows != DIAGNOSTIC_CASE_COUNT
        or reconciliation.analyzed_rows != DIAGNOSTIC_CASE_COUNT
        or reconciliation.missing_rows != 0
        or reconciliation.excluded_rows != 0
        or reconciliation.ordered_attempt_subjects != registration.ordered_subjects
    ):
        raise DiagnosticPhaseConflict(
            "aggregate outcome access requires complete clean 480-row reconciliation"
        )
    if (
        type(activation_admissions) not in (tuple, list)
        or len(activation_admissions) != DIAGNOSTIC_CASE_COUNT
    ):
        raise DiagnosticPhaseConflict(
            "aggregate access requires exactly 480 private activation admissions"
        )
    admissions = tuple(activation_admissions)
    for index, admission in enumerate(admissions):
        replay_diagnostic_phase_activation_admission_projection(admission)
        if (
            admission.attempt_subject_sha256 != registration.ordered_subjects[index]
            or admission.artifact_ref
            != reconciliation.activation_admission_refs[index]
            or (admission.target_vector, admission.wrong_layer_vector)
            != reconciliation.activation_vector_refs[index]
        ):
            raise DiagnosticPhaseValidationError(
                f"post-access activation admission {index} differs from reconciliation refs"
            )
    snapshot, obj = _canonical_object(raw, "diagnostic phase outcome access")
    try:
        expect_keys(
            obj,
            required={
                "schema_version",
                "access_id",
                "phase_id",
                "phase_subject_sha256",
                "accessed_at",
                "execution_started_at",
                "study_completed_at",
                "phase_registration",
                "phase_reconciliation",
                "diagnostic_study_outcome_index",
                "diagnostic_outcome_access_event",
                "activation_admission_inventory_sha256",
                "access_scope",
                "coordinator_public_api_outcome_release",
                "out_of_band_read_prevention",
                "boundary",
            },
            path="$",
        )
        if obj["schema_version"] != DIAGNOSTIC_PHASE_OUTCOME_ACCESS_SCHEMA:
            raise SchemaValidationError("wrong diagnostic phase outcome-access schema")
        access_id = expect_machine_id(obj["access_id"], "$.access_id")
        expect_timestamp(obj["accessed_at"], "$.accessed_at")
        expect_timestamp(obj["execution_started_at"], "$.execution_started_at")
        expect_timestamp(obj["study_completed_at"], "$.study_completed_at")
        for key in (
            "phase_registration",
            "phase_reconciliation",
            "diagnostic_study_outcome_index",
        ):
            parse_artifact_ref(obj[key], f"$.{key}")
    except SchemaValidationError as exc:
        raise DiagnosticPhaseValidationError(str(exc)) from exc
    _require_boundary(obj["boundary"])
    expected = _outcome_access_value(
        access_id=access_id,
        registration=registration,
        reconciliation=reconciliation,
        index=outcome_index,
        event=outcome_access_event,
        activation_admissions=admissions,
    )
    if obj != expected:
        raise DiagnosticPhaseValidationError(
            "phase outcome-access wrapper differs from exact access dependencies"
        )
    if access_id in {
        registration.registration_id,
        reconciliation.reconciliation_id,
        outcome_index.outcome_index_id,
    }:
        raise DiagnosticPhaseValidationError(
            "phase outcome-access identifier collides with a dependency"
        )
    artifact = DiagnosticPhaseOutcomeAccessArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        access_id=access_id,
        phase_id=registration.phase_id,
        phase_subject_sha256=registration.phase_subject_sha256,
        accessed_at=outcome_access_event.accessed_at,
        execution_started_at=outcome_access_event.execution_started_at,
        study_completed_at=outcome_access_event.study_completed_at,
        reconciliation_ref=reconciliation.artifact_ref,
        outcome_index=outcome_index,
        outcome_access_event=outcome_access_event,
        activation_admissions=admissions,
        payload=freeze_json(obj),
    )
    return replay_diagnostic_phase_outcome_access_projection(
        artifact,
        registration=registration,
        reconciliation=reconciliation,
    )


_CREATE_PHASES_TABLE = """
CREATE TABLE IF NOT EXISTS diagnostic_phases (
    phase_subject_sha256 TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    registration_sha256 TEXT NOT NULL,
    registration_raw BLOB NOT NULL,
    state TEXT NOT NULL,
    reconciliation_sha256 TEXT,
    reconciliation_raw BLOB,
    outcome_access_sha256 TEXT,
    outcome_access_raw BLOB,
    created_at TEXT NOT NULL
)
"""

_CREATE_PHASE_ROSTER_TABLE = """
CREATE TABLE IF NOT EXISTS diagnostic_phase_roster (
    phase_subject_sha256 TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    attempt_subject_sha256 TEXT NOT NULL,
    execution_ordinal INTEGER NOT NULL,
    case_id TEXT NOT NULL,
    study_request_sha256 TEXT NOT NULL,
    PRIMARY KEY (phase_subject_sha256, execution_ordinal),
    UNIQUE (tenant_id, attempt_subject_sha256),
    FOREIGN KEY (phase_subject_sha256)
        REFERENCES diagnostic_phases(phase_subject_sha256)
)
"""

_CREATE_PHASE_ACTIVATION_ADMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS diagnostic_phase_activation_admissions (
    phase_subject_sha256 TEXT NOT NULL,
    attempt_subject_sha256 TEXT PRIMARY KEY,
    admission_id TEXT NOT NULL UNIQUE,
    admission_sha256 TEXT NOT NULL,
    admission_raw BLOB NOT NULL,
    manifest_artifact_id TEXT NOT NULL UNIQUE,
    manifest_sha256 TEXT NOT NULL,
    manifest_raw BLOB NOT NULL,
    request_body BLOB NOT NULL,
    authorization_projection_body BLOB NOT NULL,
    capture_index_body BLOB NOT NULL,
    input_ids_body BLOB NOT NULL,
    attention_mask_body BLOB NOT NULL,
    target_artifact_id TEXT NOT NULL UNIQUE,
    target_body BLOB NOT NULL,
    wrong_artifact_id TEXT NOT NULL UNIQUE,
    wrong_body BLOB NOT NULL,
    FOREIGN KEY (phase_subject_sha256)
        REFERENCES diagnostic_phases(phase_subject_sha256)
)
"""

_CREATE_PHASE_OUTCOME_ACCESS_TABLE = """
CREATE TABLE IF NOT EXISTS diagnostic_phase_outcome_access (
    phase_subject_sha256 TEXT PRIMARY KEY,
    outcome_index_sha256 TEXT NOT NULL,
    outcome_index_raw BLOB NOT NULL,
    outcome_event_sha256 TEXT NOT NULL,
    outcome_event_raw BLOB NOT NULL,
    wrapper_sha256 TEXT NOT NULL,
    wrapper_raw BLOB NOT NULL,
    FOREIGN KEY (phase_subject_sha256)
        REFERENCES diagnostic_phases(phase_subject_sha256)
)
"""

_PHASE_TRIGGER_SQL = {
    "cas_diag_phase_outcome_insert_guard": """
CREATE TRIGGER cas_diag_phase_outcome_insert_guard
BEFORE INSERT ON diagnostic_phase_outcome_access
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM diagnostic_phases AS p
        WHERE p.phase_subject_sha256 = NEW.phase_subject_sha256
          AND p.state = 'RECONCILED_CLEAN'
          AND p.outcome_access_sha256 IS NULL
          AND p.outcome_access_raw IS NULL
    ) THEN RAISE(ABORT, 'diagnostic phase outcome-access insert guard') END;
END
""",
    "cas_diag_phase_outcome_update_guard": """
CREATE TRIGGER cas_diag_phase_outcome_update_guard
BEFORE UPDATE ON diagnostic_phase_outcome_access
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase outcome-access update forbidden');
END
""",
    "cas_diag_phase_outcome_delete_guard": """
CREATE TRIGGER cas_diag_phase_outcome_delete_guard
BEFORE DELETE ON diagnostic_phase_outcome_access
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase outcome-access deletion forbidden');
END
""",
    "cas_diag_phase_activation_insert_guard": """
CREATE TRIGGER cas_diag_phase_activation_insert_guard
BEFORE INSERT ON diagnostic_phase_activation_admissions
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM diagnostic_phase_roster AS r
        JOIN diagnostic_phases AS p
          ON p.phase_subject_sha256 = r.phase_subject_sha256
        JOIN diagnostic_attempts AS a
          ON a.tenant_id = r.tenant_id
         AND a.attempt_subject_sha256 = r.attempt_subject_sha256
        WHERE r.phase_subject_sha256 = NEW.phase_subject_sha256
          AND r.attempt_subject_sha256 = NEW.attempt_subject_sha256
          AND p.state = 'OPEN'
          AND json_extract(CAST(a.payload AS TEXT), '$.state') = 'COMPLETED'
    ) THEN RAISE(ABORT, 'diagnostic activation admission guard') END;
END
""",
    "cas_diag_phase_activation_update_guard": """
CREATE TRIGGER cas_diag_phase_activation_update_guard
BEFORE UPDATE ON diagnostic_phase_activation_admissions
BEGIN
    SELECT RAISE(ABORT, 'diagnostic activation admission update forbidden');
END
""",
    "cas_diag_phase_activation_delete_guard": """
CREATE TRIGGER cas_diag_phase_activation_delete_guard
BEFORE DELETE ON diagnostic_phase_activation_admissions
BEGIN
    SELECT RAISE(ABORT, 'diagnostic activation admission deletion forbidden');
END
""",
    "cas_diag_phase_insert_guard": """
CREATE TRIGGER cas_diag_phase_insert_guard
BEFORE INSERT ON diagnostic_phases
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase file already claimed');
END
""",
    "cas_diag_phase_attempt_insert_guard": """
CREATE TRIGGER cas_diag_phase_attempt_insert_guard
BEFORE INSERT ON diagnostic_attempts
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM diagnostic_phase_roster AS r
        JOIN diagnostic_phases AS p
          ON p.phase_subject_sha256 = r.phase_subject_sha256
        WHERE r.tenant_id = NEW.tenant_id
          AND r.attempt_subject_sha256 = NEW.attempt_subject_sha256
          AND p.state = 'OPEN'
    ) THEN RAISE(ABORT, 'diagnostic phase issuance guard') END;
END
""",
    "cas_diag_phase_attempt_update_guard": """
CREATE TRIGGER cas_diag_phase_attempt_update_guard
BEFORE UPDATE ON diagnostic_attempts
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM diagnostic_phase_roster AS r
        JOIN diagnostic_phases AS p
          ON p.phase_subject_sha256 = r.phase_subject_sha256
        WHERE r.tenant_id = NEW.tenant_id
          AND r.attempt_subject_sha256 = NEW.attempt_subject_sha256
          AND p.state = 'OPEN'
    ) THEN RAISE(ABORT, 'diagnostic phase mutation guard') END;
END
""",
    "cas_diag_phase_attempt_delete_guard": """
CREATE TRIGGER cas_diag_phase_attempt_delete_guard
BEFORE DELETE ON diagnostic_attempts
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase attempt deletion forbidden');
END
""",
    "cas_diag_phase_event_insert_guard": """
CREATE TRIGGER cas_diag_phase_event_insert_guard
BEFORE INSERT ON diagnostic_attempt_events
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
        FROM diagnostic_phase_roster AS r
        JOIN diagnostic_phases AS p
          ON p.phase_subject_sha256 = r.phase_subject_sha256
        WHERE r.tenant_id = NEW.tenant_id
          AND r.attempt_subject_sha256 = NEW.attempt_subject_sha256
          AND p.state = 'OPEN'
    ) THEN RAISE(ABORT, 'diagnostic phase event guard') END;
END
""",
    "cas_diag_phase_event_update_guard": """
CREATE TRIGGER cas_diag_phase_event_update_guard
BEFORE UPDATE ON diagnostic_attempt_events
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase event update forbidden');
END
""",
    "cas_diag_phase_event_delete_guard": """
CREATE TRIGGER cas_diag_phase_event_delete_guard
BEFORE DELETE ON diagnostic_attempt_events
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase event deletion forbidden');
END
""",
    "cas_diag_phase_roster_insert_guard": """
CREATE TRIGGER cas_diag_phase_roster_insert_guard
BEFORE INSERT ON diagnostic_phase_roster
WHEN EXISTS (SELECT 1 FROM diagnostic_phases)
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase roster is create-only');
END
""",
    "cas_diag_phase_roster_update_guard": """
CREATE TRIGGER cas_diag_phase_roster_update_guard
BEFORE UPDATE ON diagnostic_phase_roster
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase roster update forbidden');
END
""",
    "cas_diag_phase_roster_delete_guard": """
CREATE TRIGGER cas_diag_phase_roster_delete_guard
BEFORE DELETE ON diagnostic_phase_roster
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase roster deletion forbidden');
END
""",
    "cas_diag_phase_delete_guard": """
CREATE TRIGGER cas_diag_phase_delete_guard
BEFORE DELETE ON diagnostic_phases
BEGIN
    SELECT RAISE(ABORT, 'diagnostic phase deletion forbidden');
END
""",
    "cas_diag_phase_update_guard": """
CREATE TRIGGER cas_diag_phase_update_guard
BEFORE UPDATE ON diagnostic_phases
BEGIN
    SELECT CASE WHEN NOT (
        NEW.phase_subject_sha256 = OLD.phase_subject_sha256
        AND NEW.tenant_id = OLD.tenant_id
        AND NEW.registration_sha256 = OLD.registration_sha256
        AND NEW.registration_raw = OLD.registration_raw
        AND NEW.created_at = OLD.created_at
        AND (
            (
                OLD.state = 'OPEN'
                AND NEW.state IN ('RECONCILED_CLEAN', 'RECONCILED_REJECTED')
                AND OLD.reconciliation_sha256 IS NULL
                AND OLD.reconciliation_raw IS NULL
                AND NEW.reconciliation_sha256 IS NOT NULL
                AND NEW.reconciliation_raw IS NOT NULL
                AND NEW.outcome_access_sha256 IS NULL
                AND NEW.outcome_access_raw IS NULL
            )
            OR
            (
                OLD.state = 'RECONCILED_CLEAN'
                AND NEW.state = 'OUTCOME_ACCESSED'
                AND NEW.reconciliation_sha256 = OLD.reconciliation_sha256
                AND NEW.reconciliation_raw = OLD.reconciliation_raw
                AND OLD.outcome_access_sha256 IS NULL
                AND OLD.outcome_access_raw IS NULL
                AND NEW.outcome_access_sha256 IS NOT NULL
                AND NEW.outcome_access_raw IS NOT NULL
            )
        )
    ) THEN RAISE(ABORT, 'diagnostic phase transition forbidden') END;
END
""",
}

_PHASE_FILE_LOCKS_GUARD = threading.RLock()
_PHASE_FILE_LOCKS: dict[str, threading.RLock] = {}


def _phase_file_path(value: str | os.PathLike[str]) -> str:
    try:
        supplied = os.fspath(value)
    except TypeError as exc:
        raise DiagnosticPhaseValidationError("database_path must be path-like") from exc
    if not supplied or supplied == ":memory:" or supplied.startswith("file::memory:"):
        raise DiagnosticPhaseValidationError(
            "production-shaped phase storage requires a file-backed SQLite path"
        )
    path = str(Path(supplied).resolve())
    if Path(path).exists() and not Path(path).is_file():
        raise DiagnosticPhaseValidationError("database_path must identify a file")
    if not Path(path).parent.exists():
        raise DiagnosticPhaseValidationError("database_path parent directory does not exist")
    return path


def _file_lock(path: str) -> threading.RLock:
    with _PHASE_FILE_LOCKS_GUARD:
        return _PHASE_FILE_LOCKS.setdefault(path, threading.RLock())


def _sqlite_connection(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None, timeout=30.0)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")
    return connection


def _sqlite_schema_rows(connection: sqlite3.Connection) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        connection.execute(
            """
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            WHERE name NOT LIKE 'sqlite_%'
            ORDER BY type, name, tbl_name
            """
        )
    )


def _sqlite_schema_sha256(connection: sqlite3.Connection) -> str:
    return canonical_sha256(
        {
            "domain": "cas_harness_v2.diagnostic_phase_sqlite_schema.v1",
            "objects": [list(row) for row in _sqlite_schema_rows(connection)],
        }
    )


class DiagnosticPhaseCoordinator:
    """Private-chain, private-store, same-file SQLite phase coordinator."""

    def __init__(
        self,
        *,
        registration: DiagnosticPhaseRegistrationArtifact,
        shared_plan_context: DiagnosticSharedPlanReplayContext,
        nonce_factory: Callable[[int], bytes],
        fault_hook: Callable[[str], None] | None = None,
    ) -> None:
        _require_exact_type(
            registration, DiagnosticPhaseRegistrationArtifact, "registration"
        )
        replayed = load_diagnostic_phase_registration(
            registration.raw_bytes,
            shared_plan_context=shared_plan_context,
            study_requests=registration.study_requests,
            store_binding=registration.store_binding,
        )
        if replayed != registration:
            raise DiagnosticPhaseValidationError(
                "registration differs from fresh exact replay"
            )
        self.__database_path = registration.store_binding.canonical_path
        self.__file_lock = _file_lock(self.__database_path)
        self.__registration = registration
        self.__external_shared = shared_plan_context
        self.__external_kernel_sha256 = shared_plan_context.kernel_sha256
        self.__fault_hook = fault_hook

        # Build a distinct process-sealed context over a private exact-byte
        # preregistration chain.  The caller's chain can neither authorize rows
        # nor receive aggregate access through this coordinator.
        private_chain = _clone_pre_outcome_chain(shared_plan_context.chain)
        self.__shared = build_diagnostic_shared_plan_replay_context(
            chain=private_chain,
            plan=shared_plan_context.plan,
            execution_contract=shared_plan_context.execution_contract,
        )
        privately_replayed = load_diagnostic_phase_registration(
            registration.raw_bytes,
            shared_plan_context=self.__shared,
            study_requests=registration.study_requests,
            store_binding=registration.store_binding,
        )
        if privately_replayed != registration:
            raise DiagnosticPhaseValidationError(
                "registration differs under private-chain replay"
            )
        self.__contexts = MappingProxyType(
            {
                subject: DiagnosticLifecycleReplayContext(
                    shared_plan=self.__shared,
                    study_request=request,
                )
                for subject, request in zip(
                    registration.ordered_subjects,
                    registration.study_requests,
                    strict=True,
                )
            }
        )
        self.__guard = DiagnosticPhaseIssuanceGuard(registration)
        schema_probe = _sqlite_connection(self.__database_path)
        try:
            if _sqlite_schema_rows(schema_probe):
                raise DiagnosticPhaseConflict(
                    "canonical phase store is not an empty pre-registration SQLite schema"
                )
        finally:
            schema_probe.close()
        self.__lifecycle_store = SqliteDiagnosticLifecycleStore(
            self.__database_path, fault_hook=fault_hook
        )
        self.__store = GuardedDiagnosticLifecycleStore(
            self.__lifecycle_store, self.__guard
        )
        self.__lifecycle = DiagnosticAttemptLifecycle(
            self.__store, nonce_factory=nonce_factory
        )
        self.__phase_db = _sqlite_connection(self.__database_path)
        self.__trigger_sql: dict[str, str] = {}
        self.__reconciliation: DiagnosticPhaseReconciliationArtifact | None = None
        self.__outcome_access: DiagnosticPhaseOutcomeAccessArtifact | None = None
        self.__activation_admissions: tuple[
            DiagnosticPhaseActivationAdmissionArtifact, ...
        ] | None = None
        self.__sealed_chain: DiagnosticPreregistrationChain | None = None
        self.__closed = False
        try:
            self.__register_phase_once()
            self.__schema_sha256 = _sqlite_schema_sha256(self.__phase_db)
        except Exception:
            self.__phase_db.close()
            self.__lifecycle_store.close()
            raise

    def __register_phase_once(self) -> None:
        with self.__file_lock:
            try:
                self.__phase_db.execute("BEGIN IMMEDIATE")
                self.__phase_db.execute(_CREATE_PHASES_TABLE)
                self.__phase_db.execute(_CREATE_PHASE_ROSTER_TABLE)
                self.__phase_db.execute(_CREATE_PHASE_ACTIVATION_ADMISSIONS_TABLE)
                self.__phase_db.execute(_CREATE_PHASE_OUTCOME_ACCESS_TABLE)
                if self.__phase_db.execute(
                    "SELECT COUNT(*) FROM diagnostic_phases"
                ).fetchone()[0] != 0:
                    raise DiagnosticPhaseConflict(
                        "SQLite file already owns a create-only diagnostic phase"
                    )
                if self.__phase_db.execute(
                    "SELECT COUNT(*) FROM diagnostic_attempts"
                ).fetchone()[0] != 0:
                    raise DiagnosticPhaseIntegrityError(
                        "phase file contains attempts before phase registration"
                    )
                self.__phase_db.execute(
                    """
                    INSERT INTO diagnostic_phases (
                        phase_subject_sha256, tenant_id, registration_sha256,
                        registration_raw, state, reconciliation_sha256,
                        reconciliation_raw, outcome_access_sha256,
                        outcome_access_raw, created_at
                    ) VALUES (?, ?, ?, ?, 'OPEN', NULL, NULL, NULL, NULL, ?)
                    """,
                    (
                        self.__registration.phase_subject_sha256,
                        self.__registration.tenant_id,
                        self.__registration.sha256,
                        self.__registration.raw_bytes,
                        self.__registration.registered_at,
                    ),
                )
                self.__phase_db.executemany(
                    """
                    INSERT INTO diagnostic_phase_roster (
                        phase_subject_sha256, tenant_id,
                        attempt_subject_sha256, execution_ordinal,
                        case_id, study_request_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    tuple(
                        (
                            self.__registration.phase_subject_sha256,
                            self.__registration.tenant_id,
                            subject,
                            index,
                            request.case_id,
                            request.sha256,
                        )
                        for index, (subject, request) in enumerate(
                            zip(
                                self.__registration.ordered_subjects,
                                self.__registration.study_requests,
                                strict=True,
                            ),
                            start=1,
                        )
                    ),
                )
                for name, sql in _PHASE_TRIGGER_SQL.items():
                    self.__phase_db.execute(sql)
                    stored = self.__phase_db.execute(
                        "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
                        (name,),
                    ).fetchone()
                    if stored is None or type(stored[0]) is not str:
                        raise DiagnosticPhaseIntegrityError(
                            f"phase trigger {name} was not retained"
                        )
                    self.__trigger_sql[name] = stored[0]
                self.__phase_db.execute("COMMIT")
            except Exception:
                try:
                    self.__phase_db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise

    def __ensure_open(self) -> None:
        if self.__closed:
            raise DiagnosticPhaseConflict("diagnostic phase coordinator is closed")

    def __assert_external_snapshot_unchanged(self) -> None:
        if load_diagnostic_phase_store_binding(
            self.__registration.store_binding.raw_bytes
        ) != self.__registration.store_binding:
            raise DiagnosticPhaseIntegrityError(
                "canonical phase store binding changed"
            )
        if self.__external_shared.kernel_sha256 != self.__external_kernel_sha256:
            raise DiagnosticPhaseIntegrityError("caller shared-plan kernel changed")
        try:
            observed = self.__external_shared.replay_study_request(
                self.__registration.study_requests[0]
            )
        except Exception as exc:
            raise DiagnosticPhaseIntegrityError(
                f"caller shared plan/chain mutated after registration: {exc}"
            ) from exc
        if observed != self.__registration.study_requests[0]:
            raise DiagnosticPhaseIntegrityError(
                "caller shared-plan row differs after registration"
            )

    def __db_state_row(self) -> tuple[Any, ...]:
        row = self.__phase_db.execute(
            """
            SELECT tenant_id, registration_sha256, registration_raw, state,
                   reconciliation_sha256, reconciliation_raw,
                   outcome_access_sha256, outcome_access_raw
            FROM diagnostic_phases WHERE phase_subject_sha256=?
            """,
            (self.__registration.phase_subject_sha256,),
        ).fetchone()
        if row is None:
            raise DiagnosticPhaseIntegrityError("registered phase row is missing")
        return row

    def __assert_db_integrity(self, *, require_exact_attempts: bool) -> str:
        if (
            self.__phase_db.execute("PRAGMA application_id").fetchone()[0]
            != _SQLITE_APPLICATION_ID
            or self.__phase_db.execute("PRAGMA user_version").fetchone()[0]
            != _SQLITE_USER_VERSION
            or str(
                self.__phase_db.execute("PRAGMA journal_mode").fetchone()[0]
            ).upper()
            != "WAL"
            or self.__phase_db.execute("PRAGMA synchronous").fetchone()[0] != 2
        ):
            raise DiagnosticPhaseIntegrityError("SQLite application/schema identity changed")
        if _sqlite_schema_sha256(self.__phase_db) != self.__schema_sha256:
            raise DiagnosticPhaseIntegrityError(
                "SQLite table/index/trigger schema inventory changed"
            )
        phase_subjects = tuple(
            row[0]
            for row in self.__phase_db.execute(
                "SELECT phase_subject_sha256 FROM diagnostic_phases"
            )
        )
        if phase_subjects != (self.__registration.phase_subject_sha256,):
            raise DiagnosticPhaseIntegrityError(
                "SQLite file must contain exactly the one canonically bound phase"
            )
        (
            tenant,
            registration_sha,
            registration_raw,
            state,
            reconciliation_sha,
            reconciliation_raw,
            outcome_sha,
            outcome_raw,
        ) = self.__db_state_row()
        if (
            tenant != self.__registration.tenant_id
            or registration_sha != self.__registration.sha256
            or bytes(registration_raw) != self.__registration.raw_bytes
            or state not in DIAGNOSTIC_PHASE_STATES
        ):
            raise DiagnosticPhaseIntegrityError(
                "SQLite phase registration/state projection drifted"
            )
        if (
            state == PHASE_OPEN
            and any(
                item is not None
                for item in (
                    reconciliation_sha,
                    reconciliation_raw,
                    outcome_sha,
                    outcome_raw,
                )
            )
        ) or (
            state in {PHASE_RECONCILED_CLEAN, PHASE_RECONCILED_REJECTED}
            and (
                reconciliation_sha is None
                or reconciliation_raw is None
                or outcome_sha is not None
                or outcome_raw is not None
            )
        ) or (
            state == PHASE_OUTCOME_ACCESSED
            and any(
                item is None
                for item in (
                    reconciliation_sha,
                    reconciliation_raw,
                    outcome_sha,
                    outcome_raw,
                )
            )
        ):
            raise DiagnosticPhaseIntegrityError(
                "SQLite phase carrier columns disagree with the one-way state"
            )
        roster = tuple(
            self.__phase_db.execute(
                """
                SELECT phase_subject_sha256, tenant_id,
                       attempt_subject_sha256, execution_ordinal,
                       case_id, study_request_sha256
                FROM diagnostic_phase_roster
                ORDER BY phase_subject_sha256, execution_ordinal
                """
            )
        )
        expected_roster = tuple(
            (
                self.__registration.phase_subject_sha256,
                self.__registration.tenant_id,
                subject,
                index,
                request.case_id,
                request.sha256,
            )
            for index, (subject, request) in enumerate(
                zip(
                    self.__registration.ordered_subjects,
                    self.__registration.study_requests,
                    strict=True,
                ),
                start=1,
            )
        )
        if roster != expected_roster:
            raise DiagnosticPhaseIntegrityError(
                "SQLite phase roster is not the exact plan-ordered 480 rows"
            )
        activation_subjects = tuple(
            self.__phase_db.execute(
                """
                SELECT phase_subject_sha256, attempt_subject_sha256
                FROM diagnostic_phase_activation_admissions
                ORDER BY attempt_subject_sha256
                """
            )
        )
        expected_subject_set = set(self.__registration.ordered_subjects)
        if (
            len(activation_subjects) > DIAGNOSTIC_CASE_COUNT
            or any(
                phase_subject != self.__registration.phase_subject_sha256
                or subject not in expected_subject_set
                for phase_subject, subject in activation_subjects
            )
        ):
            raise DiagnosticPhaseIntegrityError(
                "SQLite activation-admission inventory exceeds the registered roster"
            )
        outcome_rows = tuple(
            self.__phase_db.execute(
                """
                SELECT phase_subject_sha256, outcome_index_sha256,
                       outcome_index_raw, outcome_event_sha256,
                       outcome_event_raw, wrapper_sha256, wrapper_raw
                FROM diagnostic_phase_outcome_access
                """
            )
        )
        if state == PHASE_OUTCOME_ACCESSED:
            if (
                len(outcome_rows) != 1
                or outcome_rows[0][0]
                != self.__registration.phase_subject_sha256
                or outcome_rows[0][5] != outcome_sha
                or bytes(outcome_rows[0][6]) != bytes(outcome_raw)
            ):
                raise DiagnosticPhaseIntegrityError(
                    "SQLite outcome-access byte family is missing or differs"
                )
        elif outcome_rows:
            raise DiagnosticPhaseIntegrityError(
                "SQLite outcome-access bytes exist before aggregate access"
            )
        for name, expected_sql in self.__trigger_sql.items():
            stored = self.__phase_db.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
                (name,),
            ).fetchone()
            if stored is None or stored[0] != expected_sql:
                raise DiagnosticPhaseIntegrityError(
                    f"SQLite phase trigger {name} is missing or changed"
                )
        if require_exact_attempts:
            attempts = tuple(
                self.__phase_db.execute(
                    """
                    SELECT tenant_id, attempt_subject_sha256
                    FROM diagnostic_attempts
                    ORDER BY tenant_id, attempt_subject_sha256
                    """
                )
            )
            expected_attempts = tuple(
                sorted(
                    (
                        self.__registration.tenant_id,
                        subject,
                    )
                    for subject in self.__registration.ordered_subjects
                )
            )
            event_subjects = tuple(
                self.__phase_db.execute(
                    """
                    SELECT DISTINCT tenant_id, attempt_subject_sha256
                    FROM diagnostic_attempt_events
                    ORDER BY tenant_id, attempt_subject_sha256
                    """
                )
            )
            if attempts != expected_attempts or event_subjects != expected_attempts:
                raise DiagnosticPhaseIntegrityError(
                    "full SQLite attempt/event subject set is not the registered 480 rows"
                )
        return str(state)

    def __request(self, execution_ordinal: int) -> DiagnosticStudyRequestArtifact:
        try:
            ordinal = expect_int(
                execution_ordinal,
                "execution_ordinal",
                minimum=1,
                maximum=DIAGNOSTIC_CASE_COUNT,
            )
        except SchemaValidationError as exc:
            raise DiagnosticPhaseValidationError(str(exc)) from exc
        return self.__registration.study_requests[ordinal - 1]

    def __context(self, subject: str) -> DiagnosticLifecycleReplayContext:
        context = self.__contexts.get(subject)
        if context is None:
            raise DiagnosticPhaseValidationError(
                "attempt subject is outside the private phase roster"
            )
        return context

    def __activation_admissions_for(
        self, replays: Sequence[DiagnosticAttemptReplay]
    ) -> tuple[DiagnosticPhaseActivationAdmissionArtifact | None, ...]:
        stored_rows = tuple(
            self.__phase_db.execute(
                """
                SELECT attempt_subject_sha256, admission_id, admission_sha256,
                       admission_raw, manifest_artifact_id, manifest_sha256,
                       manifest_raw, request_body,
                       authorization_projection_body, capture_index_body,
                       input_ids_body, attention_mask_body,
                       target_artifact_id, target_body,
                       wrong_artifact_id, wrong_body
                FROM diagnostic_phase_activation_admissions
                WHERE phase_subject_sha256=?
                ORDER BY attempt_subject_sha256
                """,
                (self.__registration.phase_subject_sha256,),
            )
        )
        by_subject = {row[0]: row[1:] for row in stored_rows}
        admissions: list[DiagnosticPhaseActivationAdmissionArtifact | None] = []
        for index, replay in enumerate(replays, start=1):
            stored = by_subject.pop(replay.snapshot.attempt_subject_sha256, None)
            if replay.snapshot.state != COMPLETED:
                if stored is not None:
                    raise DiagnosticPhaseIntegrityError(
                        f"non-completed row {index} has an activation admission"
                    )
                admissions.append(None)
                continue
            if stored is None:
                raise DiagnosticPhaseIntegrityError(
                    f"completed row {index} lacks its retained activation admission"
                )
            (
                admission_id,
                admission_sha,
                admission_raw,
                manifest_id,
                manifest_sha,
                manifest_raw,
                request_body,
                authorization_projection_body,
                capture_index_body,
                input_ids_body,
                attention_mask_body,
                target_id,
                target_body,
                wrong_id,
                wrong_body,
            ) = stored
            member_bodies = {
                "request_artifact": bytes(request_body),
                "authorization_projection_artifact": bytes(
                    authorization_projection_body
                ),
                "capture_index_artifact": bytes(capture_index_body),
                "input_ids": bytes(input_ids_body),
                "attention_mask": bytes(attention_mask_body),
                "target_vector": bytes(target_body),
                "wrong_layer_vector": bytes(wrong_body),
            }
            manifest_ref = ArtifactRef(
                artifact_id=manifest_id,
                sha256=manifest_sha,
                byte_length=len(bytes(manifest_raw)),
                media_type=STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE,
            )
            artifact = load_diagnostic_phase_activation_admission(
                bytes(admission_raw),
                replay=replay,
                archive_manifest_ref=manifest_ref,
                archive_manifest_body=bytes(manifest_raw),
                archive_member_bodies=member_bodies,
            )
            if (
                admission_id != artifact.admission_id
                or admission_sha != artifact.sha256
                or manifest_id != artifact.archive_manifest_ref.artifact_id
                or manifest_sha != artifact.archive_manifest_ref.sha256
                or target_id != artifact.target_vector.artifact_id
                or wrong_id != artifact.wrong_layer_vector.artifact_id
            ):
                raise DiagnosticPhaseIntegrityError(
                    f"activation admission database projection {index} drifted"
                )
            admissions.append(artifact)
        if by_subject:
            raise DiagnosticPhaseIntegrityError(
                "activation admission database contains subjects outside replay inventory"
            )
        return tuple(admissions)

    @property
    def state(self) -> str:
        with self.__file_lock:
            self.__ensure_open()
            return self.__assert_db_integrity(require_exact_attempts=False)

    @property
    def registration(self) -> DiagnosticPhaseRegistrationArtifact:
        return self.__registration

    @property
    def reconciliation(self) -> DiagnosticPhaseReconciliationArtifact | None:
        return self.__reconciliation

    @property
    def outcome_access(self) -> DiagnosticPhaseOutcomeAccessArtifact | None:
        return self.__outcome_access

    def issue_attempt(self, *, execution_ordinal: int, **kwargs: Any) -> Any:
        with self.__file_lock:
            self.__ensure_open()
            self.__assert_external_snapshot_unchanged()
            if self.__assert_db_integrity(require_exact_attempts=False) != PHASE_OPEN:
                raise DiagnosticPhaseConflict("phase is sealed; issuance is forbidden")
            request = self.__request(execution_ordinal)
            return self.__lifecycle.issue_attempt(
                tenant_id=self.__registration.tenant_id,
                chain=self.__shared.chain,
                plan=self.__shared.plan,
                study_request=request,
                execution_contract=self.__shared.execution_contract,
                shared_plan_context=self.__shared,
                **kwargs,
            )

    def reject_preauthorization(
        self, *, execution_ordinal: int, **kwargs: Any
    ) -> Any:
        with self.__file_lock:
            self.__ensure_open()
            self.__assert_external_snapshot_unchanged()
            if self.__assert_db_integrity(require_exact_attempts=False) != PHASE_OPEN:
                raise DiagnosticPhaseConflict("phase is sealed; issuance is forbidden")
            request = self.__request(execution_ordinal)
            return self.__lifecycle.reject_preauthorization(
                tenant_id=self.__registration.tenant_id,
                chain=self.__shared.chain,
                plan=self.__shared.plan,
                study_request=request,
                execution_contract=self.__shared.execution_contract,
                shared_plan_context=self.__shared,
                **kwargs,
            )

    def consume_attempt(
        self,
        *,
        attempt_subject_sha256: str,
        run_nonce_b64url: str,
        worker_started_at: str,
        operation_id: str,
    ) -> Any:
        with self.__file_lock:
            self.__ensure_open()
            self.__assert_external_snapshot_unchanged()
            if self.__assert_db_integrity(require_exact_attempts=False) != PHASE_OPEN:
                raise DiagnosticPhaseConflict("phase is sealed; mutation is forbidden")
            return self.__lifecycle.consume_attempt(
                tenant_id=self.__registration.tenant_id,
                attempt_subject_sha256=attempt_subject_sha256,
                context=self.__context(attempt_subject_sha256),
                run_nonce_b64url=run_nonce_b64url,
                worker_started_at=worker_started_at,
                operation_id=operation_id,
            )

    def build_and_record_terminal(
        self, *, attempt_subject_sha256: str, **kwargs: Any
    ) -> Any:
        with self.__file_lock:
            self.__ensure_open()
            self.__assert_external_snapshot_unchanged()
            if self.__assert_db_integrity(require_exact_attempts=False) != PHASE_OPEN:
                raise DiagnosticPhaseConflict("phase is sealed; mutation is forbidden")
            archive_manifest = kwargs.pop("archive_manifest", None)
            archive_member_bodies = kwargs.pop("archive_member_bodies", None)
            status = kwargs.get("terminal_status")
            context = self.__context(attempt_subject_sha256)
            if status == COMPLETED:
                if (
                    type(archive_manifest) is not tuple
                    or len(archive_manifest) != 2
                    or not isinstance(archive_member_bodies, Mapping)
                ):
                    raise DiagnosticPhaseValidationError(
                        "COMPLETED terminal requires the exact archive manifest and seven members"
                    )
                preterminal = self.__lifecycle.read_attempt(
                    tenant_id=self.__registration.tenant_id,
                    attempt_subject_sha256=attempt_subject_sha256,
                    context=context,
                )
                manifest_ref, manifest_body = archive_manifest
                projection, _, _ = _validate_archive_projection(
                    replay=preterminal,
                    manifest_ref=manifest_ref,
                    manifest_body=manifest_body,
                    member_bodies=archive_member_bodies,
                )
                produced = kwargs.get("produced_artifacts")
                if not isinstance(produced, Mapping):
                    raise DiagnosticPhaseValidationError(
                        "COMPLETED terminal requires exact produced artifacts"
                    )
                archive_pair = produced.get("archive_admission")
                if type(archive_pair) is not tuple or len(archive_pair) != 2:
                    raise DiagnosticPhaseValidationError(
                        "COMPLETED terminal lacks its archive-admission document"
                    )
                _, proposed_archive = _canonical_object(
                    archive_pair[1], "proposed archive-admission document"
                )
                try:
                    proposed_manifest_ref = parse_artifact_ref(
                        proposed_archive["archive_manifest"],
                        "$proposed_archive_admission.archive_manifest",
                    )
                except (KeyError, TypeError, SchemaValidationError) as exc:
                    raise DiagnosticPhaseValidationError(
                        f"proposed archive admission is malformed: {exc}"
                    ) from exc
                if proposed_manifest_ref != projection.manifest_ref:
                    raise DiagnosticPhaseValidationError(
                        "terminal archive admission binds a different archive manifest"
                    )
            elif archive_manifest is not None or archive_member_bodies is not None:
                raise DiagnosticPhaseValidationError(
                    "non-completed terminal cannot retain a capture archive"
                )
            mutation = self.__lifecycle.build_and_record_terminal(
                tenant_id=self.__registration.tenant_id,
                attempt_subject_sha256=attempt_subject_sha256,
                context=context,
                **kwargs,
            )
            if status != COMPLETED:
                return mutation
            replay = self.__lifecycle.read_attempt(
                tenant_id=self.__registration.tenant_id,
                attempt_subject_sha256=attempt_subject_sha256,
                context=context,
            )
            admission = build_diagnostic_phase_activation_admission(
                replay=replay,
                archive_manifest=archive_manifest,
                archive_member_bodies=archive_member_bodies,
            )
            members = dict(admission.archive_member_bodies)
            try:
                self.__phase_db.execute("BEGIN IMMEDIATE")
                if self.__assert_db_integrity(require_exact_attempts=False) != PHASE_OPEN:
                    raise DiagnosticPhaseConflict(
                        "phase sealed before activation admission could be retained"
                    )
                existing = self.__phase_db.execute(
                    """
                    SELECT admission_id, admission_sha256, admission_raw,
                           manifest_artifact_id, manifest_sha256, manifest_raw,
                           request_body, authorization_projection_body,
                           capture_index_body, input_ids_body,
                           attention_mask_body,
                           target_artifact_id, target_body,
                           wrong_artifact_id, wrong_body
                    FROM diagnostic_phase_activation_admissions
                    WHERE attempt_subject_sha256=?
                    """,
                    (attempt_subject_sha256,),
                ).fetchone()
                exact = (
                    admission.admission_id,
                    admission.sha256,
                    admission.raw_bytes,
                    admission.archive_manifest_ref.artifact_id,
                    admission.archive_manifest_ref.sha256,
                    admission.archive_manifest_body,
                    members["request_artifact"],
                    members["authorization_projection_artifact"],
                    members["capture_index_artifact"],
                    members["input_ids"],
                    members["attention_mask"],
                    admission.target_vector.artifact_id,
                    admission.target_body,
                    admission.wrong_layer_vector.artifact_id,
                    admission.wrong_layer_body,
                )
                if existing is None:
                    self.__phase_db.execute(
                        """
                        INSERT INTO diagnostic_phase_activation_admissions (
                            phase_subject_sha256, attempt_subject_sha256,
                            admission_id, admission_sha256, admission_raw,
                            manifest_artifact_id, manifest_sha256, manifest_raw,
                            request_body, authorization_projection_body,
                            capture_index_body, input_ids_body,
                            attention_mask_body,
                            target_artifact_id, target_body,
                            wrong_artifact_id, wrong_body
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            self.__registration.phase_subject_sha256,
                            attempt_subject_sha256,
                            *exact,
                        ),
                    )
                elif (
                    existing[0],
                    existing[1],
                    bytes(existing[2]),
                    existing[3],
                    existing[4],
                    bytes(existing[5]),
                    bytes(existing[6]),
                    bytes(existing[7]),
                    bytes(existing[8]),
                    bytes(existing[9]),
                    bytes(existing[10]),
                    existing[11],
                    bytes(existing[12]),
                    existing[13],
                    bytes(existing[14]),
                ) != exact:
                    raise DiagnosticPhaseConflict(
                        "terminal already has a different activation admission"
                    )
                self.__phase_db.execute("COMMIT")
            except Exception:
                try:
                    self.__phase_db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
            return mutation

    def reject_authorized_attempt(
        self, *, attempt_subject_sha256: str, **kwargs: Any
    ) -> Any:
        with self.__file_lock:
            self.__ensure_open()
            self.__assert_external_snapshot_unchanged()
            if self.__assert_db_integrity(require_exact_attempts=False) != PHASE_OPEN:
                raise DiagnosticPhaseConflict("phase is sealed; mutation is forbidden")
            return self.__lifecycle.reject_authorized_attempt(
                tenant_id=self.__registration.tenant_id,
                attempt_subject_sha256=attempt_subject_sha256,
                context=self.__context(attempt_subject_sha256),
                **kwargs,
            )

    def expire_authorized_attempt(
        self, *, attempt_subject_sha256: str, **kwargs: Any
    ) -> Any:
        with self.__file_lock:
            self.__ensure_open()
            self.__assert_external_snapshot_unchanged()
            if self.__assert_db_integrity(require_exact_attempts=False) != PHASE_OPEN:
                raise DiagnosticPhaseConflict("phase is sealed; mutation is forbidden")
            return self.__lifecycle.expire_authorized_attempt(
                tenant_id=self.__registration.tenant_id,
                attempt_subject_sha256=attempt_subject_sha256,
                context=self.__context(attempt_subject_sha256),
                **kwargs,
            )

    def terminalize_stranded_running(
        self, *, attempt_subject_sha256: str, **kwargs: Any
    ) -> Any:
        with self.__file_lock:
            self.__ensure_open()
            self.__assert_external_snapshot_unchanged()
            if self.__assert_db_integrity(require_exact_attempts=False) != PHASE_OPEN:
                raise DiagnosticPhaseConflict("phase is sealed; mutation is forbidden")
            return self.__lifecycle.terminalize_stranded_running(
                tenant_id=self.__registration.tenant_id,
                attempt_subject_sha256=attempt_subject_sha256,
                context=self.__context(attempt_subject_sha256),
                **kwargs,
            )

    def reconcile_and_seal(
        self, *, reconciliation_id: str, closed_at: str
    ) -> DiagnosticPhaseReconciliationArtifact:
        """Atomically seal the exact full-file 480-row subject inventory."""

        with self.__file_lock, self.__guard._lock:
            self.__ensure_open()
            self.__assert_external_snapshot_unchanged()
            try:
                self.__phase_db.execute("BEGIN IMMEDIATE")
                if self.__assert_db_integrity(require_exact_attempts=True) != PHASE_OPEN:
                    raise DiagnosticPhaseConflict("diagnostic phase is already sealed")
                subjects = self.__lifecycle.list_subjects(
                    tenant_id=self.__registration.tenant_id
                )
                if subjects != self.__registration.ordered_subjects:
                    missing = set(self.__registration.ordered_subjects) - set(subjects)
                    extra = set(subjects) - set(self.__registration.ordered_subjects)
                    raise DiagnosticPhaseIntegrityError(
                        "phase cannot seal without the exact registered subject inventory "
                        f"(missing={len(missing)}, extra={len(extra)}, "
                        f"ordered={subjects == self.__registration.ordered_subjects})"
                    )
                replays = tuple(
                    self.__lifecycle.read_attempt(
                        tenant_id=self.__registration.tenant_id,
                        attempt_subject_sha256=subject,
                        context=self.__contexts[subject],
                    )
                    for subject in self.__registration.ordered_subjects
                )
                lifecycle_reconciliation = self.__lifecycle.reconcile(
                    tenant_id=self.__registration.tenant_id,
                    contexts=self.__contexts,
                )
                activation_admissions = self.__activation_admissions_for(replays)
                artifact = build_diagnostic_phase_reconciliation(
                    reconciliation_id=reconciliation_id,
                    registration=self.__registration,
                    closed_at=closed_at,
                    replays=replays,
                    activation_admissions=activation_admissions,
                    lifecycle_reconciliation=lifecycle_reconciliation,
                )
                changed = self.__phase_db.execute(
                    """
                    UPDATE diagnostic_phases
                    SET state=?, reconciliation_sha256=?, reconciliation_raw=?
                    WHERE phase_subject_sha256=? AND state='OPEN'
                    """,
                    (
                        artifact.status,
                        artifact.sha256,
                        artifact.raw_bytes,
                        self.__registration.phase_subject_sha256,
                    ),
                ).rowcount
                if changed != 1:
                    raise DiagnosticPhaseConflict("phase seal lost create-only contention")
                self.__phase_db.execute("COMMIT")
            except Exception:
                try:
                    self.__phase_db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
            self.__guard._state = artifact.status
            self.__guard._reconciliation_sha256 = artifact.sha256
            self.__reconciliation = artifact
            self.__activation_admissions = tuple(
                item for item in activation_admissions if item is not None
            )
            return artifact

    def record_aggregate_outcome_access(
        self,
        *,
        access_id: str,
        outcome_index_id: str,
        accessed_at: str,
    ) -> DiagnosticPhaseOutcomeAccessArtifact:
        reconciliation = self.__reconciliation
        if reconciliation is None:
            raise DiagnosticPhaseConflict("phase reconciliation has not been recorded")
        try:
            access_id = expect_machine_id(access_id, "access_id")
            outcome_index_id = expect_machine_id(outcome_index_id, "outcome_index_id")
            accessed_at = expect_timestamp(accessed_at, "accessed_at")
        except SchemaValidationError as exc:
            raise DiagnosticPhaseValidationError(str(exc)) from exc
        with self.__file_lock, self.__guard._lock:
            self.__ensure_open()
            self.__assert_external_snapshot_unchanged()
            current_state = self.__assert_db_integrity(require_exact_attempts=True)
            if current_state == PHASE_RECONCILED_REJECTED:
                raise DiagnosticPhaseConflict(
                    "aggregate outcome access is forbidden for a rejected phase"
                )
            activation_admissions = self.__activation_admissions
            if (
                activation_admissions is None
                or len(activation_admissions) != DIAGNOSTIC_CASE_COUNT
            ):
                raise DiagnosticPhaseIntegrityError(
                    "aggregate access lacks the private exact 480 activation admissions"
                )
            if current_state == PHASE_OUTCOME_ACCESSED:
                recovered = self.__recover_outcome_access_from_db()
                if (
                    recovered.access_id != access_id
                    or recovered.outcome_index.outcome_index_id != outcome_index_id
                    or recovered.accessed_at != accessed_at
                ):
                    raise DiagnosticPhaseConflict(
                        "aggregate outcome access already exists with different bytes"
                    )
                return recovered
            try:
                self.__phase_db.execute("BEGIN IMMEDIATE")
                state = self.__assert_db_integrity(require_exact_attempts=True)
                db_row = self.__db_state_row()
                if (
                    state != PHASE_RECONCILED_CLEAN
                    or db_row[4] != reconciliation.sha256
                    or bytes(db_row[5]) != reconciliation.raw_bytes
                ):
                    raise DiagnosticPhaseConflict(
                        "aggregate access requires the exact clean SQLite phase seal"
                    )
                preview_chain = _clone_pre_outcome_chain(self.__shared.chain)
                dependency_ids = {
                    self.__registration.registration_id,
                    reconciliation.reconciliation_id,
                    *_artifact_ids_in_json(self.__registration.payload),
                    *_artifact_ids_in_json(reconciliation.payload),
                }
                if (
                    access_id == outcome_index_id
                    or access_id in dependency_ids
                    or outcome_index_id in dependency_ids
                ):
                    raise DiagnosticPhaseValidationError(
                        "outcome index/access identifiers collide with a phase dependency"
                    )
                raw_index = _outcome_index_raw(
                    outcome_index_id=outcome_index_id,
                    chain=preview_chain,
                    reconciliation=reconciliation,
                    accessed_at=accessed_at,
                )
                preview_event = preview_chain.record_outcome_access(raw_index)
                preview_index = preview_chain.outcome_index
                assert preview_index is not None
                raw_wrapper = canonical_json_bytes(
                    _outcome_access_value(
                        access_id=access_id,
                        registration=self.__registration,
                        reconciliation=reconciliation,
                        index=preview_index,
                        event=preview_event,
                        activation_admissions=activation_admissions,
                    )
                )
                preview_wrapper = load_diagnostic_phase_outcome_access(
                    raw_wrapper,
                    registration=self.__registration,
                    reconciliation=reconciliation,
                    outcome_index=preview_index,
                    outcome_access_event=preview_event,
                    activation_admissions=activation_admissions,
                )
                if self.__fault_hook is not None:
                    self.__fault_hook("phase_outcome_before_insert")
                self.__phase_db.execute(
                    """
                    INSERT INTO diagnostic_phase_outcome_access (
                        phase_subject_sha256, outcome_index_sha256,
                        outcome_index_raw, outcome_event_sha256,
                        outcome_event_raw, wrapper_sha256, wrapper_raw
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.__registration.phase_subject_sha256,
                        preview_index.sha256,
                        preview_index.raw_bytes,
                        preview_event.sha256,
                        preview_event.raw_bytes,
                        preview_wrapper.sha256,
                        preview_wrapper.raw_bytes,
                    ),
                )
                if self.__fault_hook is not None:
                    self.__fault_hook("phase_outcome_before_update")
                changed = self.__phase_db.execute(
                    """
                    UPDATE diagnostic_phases
                    SET state='OUTCOME_ACCESSED',
                        outcome_access_sha256=?, outcome_access_raw=?
                    WHERE phase_subject_sha256=? AND state='RECONCILED_CLEAN'
                    """,
                    (
                        preview_wrapper.sha256,
                        preview_wrapper.raw_bytes,
                        self.__registration.phase_subject_sha256,
                    ),
                ).rowcount
                if changed != 1:
                    raise DiagnosticPhaseConflict(
                        "aggregate access lost create-only contention"
                    )
                if self.__fault_hook is not None:
                    self.__fault_hook("phase_outcome_before_commit")
                self.__phase_db.execute("COMMIT")
                if self.__fault_hook is not None:
                    self.__fault_hook("phase_outcome_after_commit")
            except Exception as exc:
                try:
                    self.__phase_db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                try:
                    recovered = self.__recover_outcome_access_from_db()
                except Exception:
                    raise exc
                if (
                    recovered.access_id != access_id
                    or recovered.outcome_index.outcome_index_id != outcome_index_id
                    or recovered.accessed_at != accessed_at
                ):
                    raise exc
                return recovered
            artifact = preview_wrapper
            self.__sealed_chain = preview_chain
            self.__guard._state = PHASE_OUTCOME_ACCESSED
            self.__guard._outcome_access_sha256 = artifact.sha256
            self.__outcome_access = artifact
            return artifact

    def __recover_outcome_access_from_db(
        self,
    ) -> DiagnosticPhaseOutcomeAccessArtifact:
        if self.__assert_db_integrity(require_exact_attempts=True) != PHASE_OUTCOME_ACCESSED:
            raise DiagnosticPhaseConflict(
                "no durable aggregate outcome access is available for recovery"
            )
        row = self.__phase_db.execute(
            """
            SELECT outcome_index_sha256, outcome_index_raw,
                   outcome_event_sha256, outcome_event_raw,
                   wrapper_sha256, wrapper_raw
            FROM diagnostic_phase_outcome_access
            WHERE phase_subject_sha256=?
            """,
            (self.__registration.phase_subject_sha256,),
        ).fetchone()
        if row is None:
            raise DiagnosticPhaseIntegrityError(
                "durable outcome-access row disappeared during recovery"
            )
        (
            index_sha,
            index_raw,
            event_sha,
            event_raw,
            wrapper_sha,
            wrapper_raw,
        ) = row
        chain = _clone_pre_outcome_chain(self.__shared.chain)
        event = chain.record_outcome_access(bytes(index_raw))
        index = chain.outcome_index
        if (
            index is None
            or index.sha256 != index_sha
            or event.sha256 != event_sha
            or event.raw_bytes != bytes(event_raw)
        ):
            raise DiagnosticPhaseIntegrityError(
                "durable outcome index/event bytes fail private-chain replay"
            )
        reconciliation = self.__reconciliation
        if reconciliation is None:
            raise DiagnosticPhaseIntegrityError(
                "outcome recovery lacks the exact in-memory reconciliation"
            )
        activation_admissions = self.__activation_admissions
        if (
            activation_admissions is None
            or len(activation_admissions) != DIAGNOSTIC_CASE_COUNT
        ):
            raise DiagnosticPhaseIntegrityError(
                "outcome recovery lacks the private exact activation carriers"
            )
        artifact = load_diagnostic_phase_outcome_access(
            bytes(wrapper_raw),
            registration=self.__registration,
            reconciliation=reconciliation,
            outcome_index=index,
            outcome_access_event=event,
            activation_admissions=activation_admissions,
        )
        if artifact.sha256 != wrapper_sha:
            raise DiagnosticPhaseIntegrityError(
                "durable outcome wrapper digest differs from exact replay"
            )
        self.__sealed_chain = chain
        self.__outcome_access = artifact
        self.__guard._state = PHASE_OUTCOME_ACCESSED
        self.__guard._outcome_access_sha256 = artifact.sha256
        return artifact

    def close(self) -> None:
        with self.__file_lock:
            if self.__closed:
                return
            self.__phase_db.close()
            self.__lifecycle_store.close()
            self.__closed = True


__all__ = [
    "DIAGNOSTIC_ACTIVATION_VECTOR_MEDIA_TYPE",
    "DIAGNOSTIC_ACTIVATION_WIDTH",
    "DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE",
    "DIAGNOSTIC_PHASE_ACTIVATION_ADMISSION_MEDIA_TYPE",
    "DIAGNOSTIC_PHASE_ACTIVATION_ADMISSION_SCHEMA",
    "DIAGNOSTIC_PHASE_OUTCOME_ACCESS_MEDIA_TYPE",
    "DIAGNOSTIC_PHASE_OUTCOME_ACCESS_SCHEMA",
    "DIAGNOSTIC_PHASE_RECONCILIATION_MEDIA_TYPE",
    "DIAGNOSTIC_PHASE_RECONCILIATION_SCHEMA",
    "DIAGNOSTIC_PHASE_REGISTRATION_MEDIA_TYPE",
    "DIAGNOSTIC_PHASE_REGISTRATION_SCHEMA",
    "DIAGNOSTIC_PHASE_STORE_BINDING_MEDIA_TYPE",
    "DIAGNOSTIC_PHASE_STORE_BINDING_SCHEMA",
    "DIAGNOSTIC_PHASE_STATES",
    "PHASE_OPEN",
    "PHASE_OUTCOME_ACCESSED",
    "PHASE_RECONCILED_CLEAN",
    "PHASE_RECONCILED_REJECTED",
    "DiagnosticPhaseConflict",
    "DiagnosticPhaseCoordinator",
    "DiagnosticPhaseError",
    "DiagnosticPhaseIntegrityError",
    "DiagnosticPhaseIssuanceGuard",
    "DiagnosticPhaseActivationAdmissionArtifact",
    "DiagnosticPhaseOutcomeAccessArtifact",
    "DiagnosticPhaseReconciliationArtifact",
    "DiagnosticPhaseRegistrationArtifact",
    "DiagnosticPhaseStoreBindingArtifact",
    "DiagnosticPhaseValidationError",
    "GuardedDiagnosticLifecycleStore",
    "build_diagnostic_phase_activation_admission",
    "build_diagnostic_phase_reconciliation",
    "build_diagnostic_phase_registration",
    "build_diagnostic_phase_store_binding",
    "load_diagnostic_phase_activation_admission",
    "load_diagnostic_phase_outcome_access",
    "load_diagnostic_phase_reconciliation",
    "load_diagnostic_phase_registration",
    "load_diagnostic_phase_store_binding",
    "replay_diagnostic_phase_activation_admission_projection",
    "replay_diagnostic_phase_outcome_access_projection",
    "replay_diagnostic_phase_reconciliation_projection",
    "replay_diagnostic_phase_registration_projection",
]
