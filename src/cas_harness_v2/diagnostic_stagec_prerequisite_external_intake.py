"""Deterministic, non-authority import of external Stage C prerequisites.

The importer copies exact bytes from a fixed locator manifest, verifies every
bound ``ArtifactRef`` before parsing any artifact body, and replays the four
candidate carriers through the existing Stage C prerequisite loaders.  A
successful import is only a detached structural snapshot.  It does not
authenticate an external trust root or grant runtime authorization.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import wraps
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
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
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_keys,
    expect_object,
    expect_sha256,
    expect_string,
    parse_artifact_ref,
)
from .artifacts import EvidenceFile
from .diagnostic_prompt_context_inventory import StageCPromptContextReplayBundle
from .diagnostic_stagec_prerequisite_admission import (
    AUTHORIZATION_INSTRUMENT_MEDIA_TYPE,
    CORPUS_ADJUDICATION_MEDIA_TYPE,
    CORPUS_ROWS_MEDIA_TYPE,
    CORPUS_SPLIT_ASSIGNMENT_MEDIA_TYPE,
    CORPUS_SURFACE_BUNDLE_MEDIA_TYPE,
    DETECTOR_DRC_PROFILE_MEDIA_TYPE,
    DETECTOR_KNOWN_FAULT_FIXTURE_MEDIA_TYPE,
    DETECTOR_RULESET_MEDIA_TYPE,
    OBJECT_LOCK_RECEIPT_MEDIA_TYPE,
    OBJECT_READBACK_RECEIPT_MEDIA_TYPE,
    STAGEC_DETECTOR_DRC_RECEIPT_MEDIA_TYPE,
    STAGEC_EXECUTION_AUTHORIZATION_MEDIA_TYPE,
    STAGEC_FROZEN_CORPUS_BUNDLE_MEDIA_TYPE,
    STAGEC_TRUSTED_STORAGE_RECEIPT_MEDIA_TYPE,
    STORAGE_VERIFIER_IDENTITY_MEDIA_TYPE,
    TRUSTED_TIME_RECEIPT_MEDIA_TYPE,
    StageCDetectorDRCReceiptArtifact,
    StageCExecutionAuthorizationArtifact,
    StageCFrozenCorpusBundleArtifact,
    StageCPrerequisiteAdmissionArtifact,
    StageCPrerequisiteAdmissionError,
    StageCPrerequisiteFactoryContext,
    StageCPrerequisiteIntakeArtifact,
    StageCTrustedStorageReceiptArtifact,
    load_stagec_detector_drc_receipt,
    load_stagec_execution_authorization,
    load_stagec_frozen_corpus_bundle,
    load_stagec_prerequisite_admission,
    load_stagec_prerequisite_intake,
    load_stagec_trusted_storage_receipt,
)


STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME = (
    "stagec_prerequisite_locator_manifest.v1.json"
)
STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_SCHEMA = (
    "cas_harness_v2.stagec_prerequisite_external_locator_manifest.v1"
)
STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prerequisite-external-locator-manifest+json"
)
STAGEC_EXTERNAL_PREREQUISITE_REPORT_SCHEMA = (
    "cas_harness_v2.stagec_prerequisite_external_intake_report.v1"
)
STAGEC_EXTERNAL_PREREQUISITE_REPORT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prerequisite-external-intake-report+json"
)
STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_SCHEMA = (
    "cas_harness_v2.stagec_prerequisite_external_binding_report.v1"
)
STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prerequisite-external-binding-report+json"
)
STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS = (
    "CANDIDATE_STRUCTURAL_REPLAY_COMPLETE_NON_AUTHORITY"
)
STAGEC_EXTERNAL_TRUST_AUTHENTICATION = "NOT_ESTABLISHED"
STAGEC_EXTERNAL_RUNTIME_AUTHORIZATION = "NOT_GRANTED_BY_IMPORTER"
STAGEC_EXTERNAL_PREREQUISITE_MAXIMUM_FILE_BYTES = 2_000_000

STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER = (
    "detector_drc",
    "drc_profile",
    "detector_ruleset",
    "known_fault_fixture",
    "frozen_corpus",
    "corpus_rows",
    "adjudication",
    "split_assignment",
    "surface_bundle",
    "trusted_storage",
    "object_lock_receipt",
    "readback_receipt",
    "trusted_time_receipt",
    "verifier_identity",
    "execution_authorization",
    "authorization_instrument",
)
_ROLE_MEDIA_TYPES = {
    "detector_drc": STAGEC_DETECTOR_DRC_RECEIPT_MEDIA_TYPE,
    "drc_profile": DETECTOR_DRC_PROFILE_MEDIA_TYPE,
    "detector_ruleset": DETECTOR_RULESET_MEDIA_TYPE,
    "known_fault_fixture": DETECTOR_KNOWN_FAULT_FIXTURE_MEDIA_TYPE,
    "frozen_corpus": STAGEC_FROZEN_CORPUS_BUNDLE_MEDIA_TYPE,
    "corpus_rows": CORPUS_ROWS_MEDIA_TYPE,
    "adjudication": CORPUS_ADJUDICATION_MEDIA_TYPE,
    "split_assignment": CORPUS_SPLIT_ASSIGNMENT_MEDIA_TYPE,
    "surface_bundle": CORPUS_SURFACE_BUNDLE_MEDIA_TYPE,
    "trusted_storage": STAGEC_TRUSTED_STORAGE_RECEIPT_MEDIA_TYPE,
    "object_lock_receipt": OBJECT_LOCK_RECEIPT_MEDIA_TYPE,
    "readback_receipt": OBJECT_READBACK_RECEIPT_MEDIA_TYPE,
    "trusted_time_receipt": TRUSTED_TIME_RECEIPT_MEDIA_TYPE,
    "verifier_identity": STORAGE_VERIFIER_IDENTITY_MEDIA_TYPE,
    "execution_authorization": STAGEC_EXECUTION_AUTHORIZATION_MEDIA_TYPE,
    "authorization_instrument": AUTHORIZATION_INSTRUMENT_MEDIA_TYPE,
}
STAGEC_EXTERNAL_PREREQUISITE_ROLE_MEDIA_TYPES = MappingProxyType(
    dict(_ROLE_MEDIA_TYPES)
)

STAGEC_EXTERNAL_PREREQUISITE_ERROR_CODES = (
    "SOURCE_INVALID",
    "MANIFEST_UNAVAILABLE",
    "MANIFEST_INVALID",
    "MANIFEST_TARGET_MISMATCH",
    "ROLE_SET_INVALID",
    "RELATIVE_PATH_INVALID",
    "PATH_COLLISION",
    "FILE_SNAPSHOT_INVALID",
    "ARTIFACT_REFERENCE_INVALID",
    "ARTIFACT_BYTES_MISMATCH",
    "DRC_REPLAY_FAILED",
    "CORPUS_REPLAY_FAILED",
    "STORAGE_REPLAY_FAILED",
    "AUTHORIZATION_REPLAY_FAILED",
    "SNAPSHOT_INVALID",
    "CALLER_BINDING_INVALID",
    "CALLER_BINDING_REPLAY_FAILED",
)
_ERROR_CODE_SET = frozenset(STAGEC_EXTERNAL_PREREQUISITE_ERROR_CODES)
_RELATIVE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WINDOWS_DEVICE_RE = re.compile(
    r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$",
    re.IGNORECASE,
)
_MANIFEST_SOURCE_ARTIFACT_ID = "stagec-prerequisite-external-locator-source-v1"
_MANIFEST_ARTIFACT_ID_PREFIX = "stagec-external-locator-"
_REPORT_ARTIFACT_ID_PREFIX = "stagec-external-intake-report-"
_BINDING_REPORT_ARTIFACT_ID_PREFIX = "stagec-external-binding-report-"


class StageCExternalPrerequisiteIntakeError(StageCPrerequisiteAdmissionError):
    """A fail-closed external import error carrying one closed error code."""

    __slots__ = ("error_code",)

    def __init__(self, error_code: str, message: str) -> None:
        if error_code not in _ERROR_CODE_SET:
            raise ValueError("external intake error code is outside the closed set")
        super().__init__(f"{error_code}: {message}")
        self.error_code = error_code


def _fail(error_code: str, message: str) -> None:
    raise StageCExternalPrerequisiteIntakeError(error_code, message)


def _closed_errors(fallback_code: str):
    def decorate(function):
        @wraps(function)
        def guarded(*args: Any, **kwargs: Any):
            try:
                return function(*args, **kwargs)
            except StageCExternalPrerequisiteIntakeError:
                raise
            except (
                AttributeError,
                KeyError,
                OSError,
                SchemaValidationError,
                StageCPrerequisiteAdmissionError,
                StrictJSONError,
                TypeError,
                ValueError,
            ):
                _fail(fallback_code, "external prerequisite validation failed closed")

        return guarded

    return decorate


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


@dataclass(frozen=True, slots=True)
class StageCExternalPrerequisiteRoleSnapshot:
    role: str
    relative_path: str
    artifact_ref: ArtifactRef
    raw_bytes: bytes

    def __post_init__(self) -> None:
        if self.role not in _ROLE_MEDIA_TYPES:
            raise SchemaValidationError("external prerequisite snapshot has an unknown role")
        _validate_relative_path(self.relative_path)
        if type(self.artifact_ref) is not ArtifactRef:
            raise SchemaValidationError("external prerequisite snapshot ref is not exact")
        if self.artifact_ref.media_type != _ROLE_MEDIA_TYPES[self.role]:
            raise SchemaValidationError("external prerequisite snapshot role/media mismatch")
        if type(self.raw_bytes) is not bytes or not self.artifact_ref.verify_bytes(
            self.raw_bytes
        ):
            raise SchemaValidationError("external prerequisite snapshot bytes mismatch")


@dataclass(frozen=True, slots=True, init=False, eq=False)
class StageCExternalPrerequisiteSnapshot:
    manifest_raw_bytes: bytes
    manifest_artifact_ref: ArtifactRef
    roles: tuple[StageCExternalPrerequisiteRoleSnapshot, ...]
    detector_drc: StageCDetectorDRCReceiptArtifact
    corpus: StageCFrozenCorpusBundleArtifact
    trusted_storage: StageCTrustedStorageReceiptArtifact
    authorization: StageCExecutionAuthorizationArtifact
    report_raw_bytes: bytes
    report_sha256: str
    report: Mapping[str, Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCExternalPrerequisiteSnapshot is loader-only; use "
            "load_stagec_external_prerequisite_snapshot"
        )

    def role_snapshot(self, role: str) -> StageCExternalPrerequisiteRoleSnapshot:
        if role not in _ROLE_MEDIA_TYPES:
            raise KeyError(role)
        return self.roles[STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER.index(role)]

    @property
    def report_artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=_REPORT_ARTIFACT_ID_PREFIX + self.report_sha256.lower(),
            sha256=self.report_sha256,
            byte_length=len(self.report_raw_bytes),
            media_type=STAGEC_EXTERNAL_PREREQUISITE_REPORT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True, init=False, eq=False)
class StageCExternalPrerequisiteBinding:
    snapshot: StageCExternalPrerequisiteSnapshot
    intake: StageCPrerequisiteIntakeArtifact
    admission: StageCPrerequisiteAdmissionArtifact
    report_raw_bytes: bytes
    report_sha256: str
    report: Mapping[str, Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCExternalPrerequisiteBinding is loader-only; use "
            "load_stagec_external_prerequisite_binding"
        )

    @property
    def report_artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=_BINDING_REPORT_ARTIFACT_ID_PREFIX
            + self.report_sha256.lower(),
            sha256=self.report_sha256,
            byte_length=len(self.report_raw_bytes),
            media_type=STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class _SnapshotSeal:
    snapshot: StageCExternalPrerequisiteSnapshot
    context: StageCPrerequisiteFactoryContext
    manifest_raw_bytes: bytes
    manifest_artifact_ref: ArtifactRef
    roles: tuple[StageCExternalPrerequisiteRoleSnapshot, ...]
    role_values: tuple[tuple[str, str, ArtifactRef, bytes], ...]
    carrier_objects: tuple[Any, ...]
    carrier_refs: tuple[ArtifactRef, ...]
    report_raw_bytes: bytes
    report_sha256: str
    report: Mapping[str, Any]


_SNAPSHOT_SEALS_LOCK = threading.RLock()
_SNAPSHOT_SEALS: dict[int, _SnapshotSeal] = {}


def _validate_relative_path(value: Any) -> str:
    try:
        text = expect_string(value, "relative_path", maximum=512)
    except SchemaValidationError as exc:
        _fail("RELATIVE_PATH_INVALID", str(exc))
    if (
        "\\" in text
        or ":" in text
        or text.startswith("/")
        or PurePosixPath(text).is_absolute()
        or PureWindowsPath(text).is_absolute()
    ):
        _fail("RELATIVE_PATH_INVALID", "path must use relative forward-slash syntax")
    parts = text.split("/")
    if (
        not parts
        or any(part in ("", ".", "..") for part in parts)
        or any(_RELATIVE_SEGMENT_RE.fullmatch(part) is None for part in parts)
        or any(part.endswith(".") or _WINDOWS_DEVICE_RE.fullmatch(part) for part in parts)
    ):
        _fail(
            "RELATIVE_PATH_INVALID",
            "path contains a forbidden component or non-canonical character",
        )
    return "/".join(parts)


def _canonical_manifest(raw: bytes) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            _fail("MANIFEST_INVALID", "locator manifest must be canonical JSON bytes")
    except StageCExternalPrerequisiteIntakeError:
        raise
    except (StrictJSONError, SchemaValidationError, ValueError, TypeError) as exc:
        _fail("MANIFEST_INVALID", str(exc))
    return snapshot, value


def _parse_manifest(
    raw: bytes,
) -> tuple[bytes, str, tuple[tuple[str, str, ArtifactRef], ...]]:
    snapshot, value = _canonical_manifest(raw)
    try:
        expect_keys(
            value,
            required={"schema_version", "target_binding_sha256", "artifacts"},
            path="$",
        )
        if value["schema_version"] != STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_SCHEMA:
            _fail("MANIFEST_INVALID", "locator manifest schema is not the fixed v1 schema")
        artifacts = expect_object(value["artifacts"], "$.artifacts")
        target_binding_sha256 = expect_sha256(
            value["target_binding_sha256"], "$.target_binding_sha256"
        )
    except StageCExternalPrerequisiteIntakeError:
        raise
    except SchemaValidationError as exc:
        _fail("MANIFEST_INVALID", str(exc))
    if set(artifacts) != set(STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER):
        _fail("ROLE_SET_INVALID", "locator manifest must contain exactly the 16 fixed roles")

    rows: list[tuple[str, str, ArtifactRef]] = []
    paths: set[str] = {STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME}
    folded_paths: set[str] = {
        STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME.casefold()
    }
    artifact_ids: set[str] = set()
    content_ids: set[tuple[str, int]] = set()
    for role in STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER:
        try:
            entry = expect_object(artifacts[role], f"$.artifacts.{role}")
            expect_keys(
                entry,
                required={"relative_path", "artifact_ref"},
                path=f"$.artifacts.{role}",
            )
            relative_path = _validate_relative_path(entry["relative_path"])
            reference = parse_artifact_ref(
                entry["artifact_ref"], f"$.artifacts.{role}.artifact_ref"
            )
        except StageCExternalPrerequisiteIntakeError:
            raise
        except SchemaValidationError as exc:
            _fail("ARTIFACT_REFERENCE_INVALID", str(exc))
        if reference.media_type != _ROLE_MEDIA_TYPES[role]:
            _fail("ARTIFACT_REFERENCE_INVALID", f"role {role!r} has the wrong media type")
        folded = relative_path.casefold()
        if relative_path in paths or folded in folded_paths:
            _fail("PATH_COLLISION", "locator paths duplicate or collide by case")
        identity = (reference.sha256, reference.byte_length)
        if reference.artifact_id in artifact_ids or identity in content_ids:
            _fail(
                "ARTIFACT_REFERENCE_INVALID",
                "artifact IDs and content identities must be globally unique",
            )
        paths.add(relative_path)
        folded_paths.add(folded)
        artifact_ids.add(reference.artifact_id)
        content_ids.add(identity)
        rows.append((role, relative_path, reference))
    return snapshot, target_binding_sha256, tuple(rows)


def _snapshot_evidence_file(source: EvidenceFile, *, label: str) -> bytes:
    if type(source) is not EvidenceFile:
        _fail("SOURCE_INVALID", f"{label} is not an exact EvidenceFile")
    try:
        return source.snapshot_bytes(
            maximum_byte_count=STAGEC_EXTERNAL_PREREQUISITE_MAXIMUM_FILE_BYTES
        ).raw_bytes
    except (OSError, SchemaValidationError, ValueError, TypeError) as exc:
        _fail("FILE_SNAPSHOT_INVALID", f"{label}: {exc}")


def _require_local_source_path(path: Path) -> None:
    if not path.is_absolute():
        _fail("SOURCE_INVALID", "external evidence source path must be absolute")
    if os.name != "nt":
        return
    anchor = path.anchor
    if anchor.startswith("\\\\"):
        _fail("SOURCE_INVALID", "UNC and device paths are forbidden for local intake")
    try:
        import ctypes

        drive_type = int(ctypes.windll.kernel32.GetDriveTypeW(anchor))
    except (AttributeError, OSError, TypeError, ValueError):
        _fail("SOURCE_INVALID", "local filesystem drive type could not be established")
    if drive_type == 4:
        _fail("SOURCE_INVALID", "remote filesystem sources are forbidden")
    if drive_type in (0, 1):
        _fail("SOURCE_INVALID", "local filesystem source root is unavailable")


def _mapping_sources(source: Mapping[str, Any]) -> dict[str, EvidenceFile]:
    result: dict[str, EvidenceFile] = {}
    folded: set[str] = set()
    for key, value in source.items():
        if type(key) is not str:
            _fail("SOURCE_INVALID", "source mapping keys must be exact relative paths")
        relative_path = _validate_relative_path(key)
        if relative_path in result or relative_path.casefold() in folded:
            _fail("PATH_COLLISION", "source mapping paths duplicate or collide by case")
        if type(value) is not EvidenceFile:
            _fail("SOURCE_INVALID", "source mapping values must be exact EvidenceFile values")
        _require_local_source_path(value.path)
        result[relative_path] = value
        folded.add(relative_path.casefold())
    return result


def _directory_manifest_source(source: object) -> tuple[Path, EvidenceFile]:
    if isinstance(source, bytes):
        _fail("SOURCE_INVALID", "directory source must be text, not bytes")
    try:
        raw_path = os.fspath(source)  # type: ignore[arg-type]
    except TypeError as exc:
        _fail("SOURCE_INVALID", str(exc))
    if type(raw_path) is not str or not raw_path or "\x00" in raw_path:
        _fail("SOURCE_INVALID", "directory source must be a non-empty path")
    root = Path(raw_path)
    if not root.is_absolute():
        _fail("SOURCE_INVALID", "directory source must be absolute")
    root = Path(os.path.abspath(raw_path))
    _require_local_source_path(root)
    manifest_path = root / STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME
    try:
        manifest_source = EvidenceFile.from_path(
            _MANIFEST_SOURCE_ARTIFACT_ID,
            manifest_path,
            maximum_byte_count=STAGEC_EXTERNAL_PREREQUISITE_MAXIMUM_FILE_BYTES,
        )
    except (OSError, SchemaValidationError, ValueError, TypeError) as exc:
        _fail("MANIFEST_UNAVAILABLE", str(exc))
    return root, manifest_source


def _collect_sources(
    source: object,
) -> tuple[bytes, str, tuple[tuple[str, str, ArtifactRef, bytes], ...]]:
    if isinstance(source, Mapping):
        sources = _mapping_sources(source)
        manifest_source = sources.get(
            STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME
        )
        if manifest_source is None:
            _fail("MANIFEST_UNAVAILABLE", "fixed locator manifest source is missing")
        manifest_raw = _snapshot_evidence_file(manifest_source, label="locator manifest")
        canonical_raw, target_binding_sha256, rows = _parse_manifest(manifest_raw)
        expected_paths = {
            STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME,
            *(relative_path for _, relative_path, _ in rows),
        }
        if set(sources) != expected_paths:
            _fail("SOURCE_INVALID", "source mapping must contain only the manifest and its 16 files")
        gathered = tuple(
            (
                role,
                relative_path,
                reference,
                _snapshot_evidence_file(sources[relative_path], label=role),
            )
            for role, relative_path, reference in rows
        )
        for relative_path, evidence_file in sources.items():
            if not evidence_file.verify_current():
                _fail("FILE_SNAPSHOT_INVALID", f"source {relative_path!r} changed during collection")
        return canonical_raw, target_binding_sha256, gathered

    root, manifest_source = _directory_manifest_source(source)
    manifest_raw = _snapshot_evidence_file(manifest_source, label="locator manifest")
    canonical_raw, target_binding_sha256, rows = _parse_manifest(manifest_raw)
    evidence_files: list[EvidenceFile] = []
    gathered_rows: list[tuple[str, str, ArtifactRef, bytes]] = []
    for role, relative_path, reference in rows:
        try:
            evidence_file = EvidenceFile.from_path(
                f"stagec-external-source-{role}",
                root.joinpath(*relative_path.split("/")),
                maximum_byte_count=STAGEC_EXTERNAL_PREREQUISITE_MAXIMUM_FILE_BYTES,
            )
        except (OSError, SchemaValidationError, ValueError, TypeError) as exc:
            _fail("FILE_SNAPSHOT_INVALID", f"{role}: {exc}")
        evidence_files.append(evidence_file)
        gathered_rows.append(
            (
                role,
                relative_path,
                reference,
                _snapshot_evidence_file(evidence_file, label=role),
            )
        )
    if not manifest_source.verify_current():
        _fail("FILE_SNAPSHOT_INVALID", "locator manifest changed during collection")
    for (role, _, _, _), evidence_file in zip(gathered_rows, evidence_files, strict=True):
        if not evidence_file.verify_current():
            _fail("FILE_SNAPSHOT_INVALID", f"{role} changed during collection")
    return canonical_raw, target_binding_sha256, tuple(gathered_rows)


def _role_map(
    rows: tuple[tuple[str, str, ArtifactRef, bytes], ...],
) -> dict[str, StageCExternalPrerequisiteRoleSnapshot]:
    # This complete identity pass intentionally precedes every semantic loader.
    for role, _, reference, raw_bytes in rows:
        if not reference.verify_bytes(raw_bytes):
            _fail("ARTIFACT_BYTES_MISMATCH", f"{role} bytes do not match its ArtifactRef")
    try:
        return {
            role: StageCExternalPrerequisiteRoleSnapshot(
                role=role,
                relative_path=relative_path,
                artifact_ref=reference,
                raw_bytes=bytes(raw_bytes),
            )
            for role, relative_path, reference, raw_bytes in rows
        }
    except SchemaValidationError as exc:
        _fail("SNAPSHOT_INVALID", str(exc))


def _dependency_bodies(
    roles: Mapping[str, StageCExternalPrerequisiteRoleSnapshot],
    names: tuple[str, ...],
) -> tuple[tuple[ArtifactRef, bytes], ...]:
    return tuple(
        (roles[name].artifact_ref, roles[name].raw_bytes) for name in names
    )


def _replay_carriers(
    roles: Mapping[str, StageCExternalPrerequisiteRoleSnapshot],
    *,
    context: StageCPrerequisiteFactoryContext,
) -> tuple[
    StageCDetectorDRCReceiptArtifact,
    StageCFrozenCorpusBundleArtifact,
    StageCTrustedStorageReceiptArtifact,
    StageCExecutionAuthorizationArtifact,
]:
    try:
        drc = load_stagec_detector_drc_receipt(
            roles["detector_drc"].raw_bytes,
            context=context,
            artifact_bodies=_dependency_bodies(
                roles,
                ("drc_profile", "detector_ruleset", "known_fault_fixture"),
            ),
        )
    except StageCPrerequisiteAdmissionError as exc:
        _fail("DRC_REPLAY_FAILED", str(exc))
    try:
        corpus = load_stagec_frozen_corpus_bundle(
            roles["frozen_corpus"].raw_bytes,
            context=context,
            artifact_bodies=_dependency_bodies(
                roles,
                ("corpus_rows", "adjudication", "split_assignment", "surface_bundle"),
            ),
        )
    except StageCPrerequisiteAdmissionError as exc:
        _fail("CORPUS_REPLAY_FAILED", str(exc))
    try:
        storage = load_stagec_trusted_storage_receipt(
            roles["trusted_storage"].raw_bytes,
            context=context,
            corpus=corpus,
            artifact_bodies=_dependency_bodies(
                roles,
                (
                    "object_lock_receipt",
                    "readback_receipt",
                    "trusted_time_receipt",
                    "verifier_identity",
                ),
            ),
        )
    except StageCPrerequisiteAdmissionError as exc:
        _fail("STORAGE_REPLAY_FAILED", str(exc))
    try:
        authorization = load_stagec_execution_authorization(
            roles["execution_authorization"].raw_bytes,
            context=context,
            detector_drc=drc,
            corpus=corpus,
            trusted_storage=storage,
            artifact_bodies=_dependency_bodies(roles, ("authorization_instrument",)),
        )
    except StageCPrerequisiteAdmissionError as exc:
        _fail("AUTHORIZATION_REPLAY_FAILED", str(exc))
    return drc, corpus, storage, authorization


def _manifest_ref(raw_bytes: bytes) -> ArtifactRef:
    digest = sha256_bytes(raw_bytes)
    return ArtifactRef(
        artifact_id=_MANIFEST_ARTIFACT_ID_PREFIX + digest.lower(),
        sha256=digest,
        byte_length=len(raw_bytes),
        media_type=STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE,
    )


def _require_global_identity_closure(
    context: StageCPrerequisiteFactoryContext,
    roles: tuple[StageCExternalPrerequisiteRoleSnapshot, ...],
) -> None:
    """Reject ID or content aliases across prompt context and all external roles."""

    try:
        context_refs = (
            context.split_inventory.artifact_ref,
            *(item.artifact_ref for item in context.split_inventory.capture_requests),
            context.prompt_inventory.artifact_ref,
            *(row.provenance for row in context.prompt_inventory.rows),
            *context.prompt_inventory.ordered_node_artifacts,
            *context.prompt_inventory.ordered_source_artifacts,
        )
    except (AttributeError, TypeError) as exc:
        _fail("SNAPSHOT_INVALID", f"factory context closure is unavailable: {exc}")
    identifiers: set[str] = set()
    content: set[tuple[str, int]] = set()
    for reference in (*context_refs, *(item.artifact_ref for item in roles)):
        if type(reference) is not ArtifactRef:
            _fail("ARTIFACT_REFERENCE_INVALID", "global closure contains a non-exact ref")
        identity = (reference.sha256, reference.byte_length)
        if reference.artifact_id in identifiers:
            _fail("ARTIFACT_REFERENCE_INVALID", "global closure contains a duplicate artifact ID")
        if identity in content:
            _fail("ARTIFACT_REFERENCE_INVALID", "global closure contains a cloned content identity")
        identifiers.add(reference.artifact_id)
        content.add(identity)


def _snapshot_report_value(
    manifest_ref: ArtifactRef,
    roles: tuple[StageCExternalPrerequisiteRoleSnapshot, ...],
    target_binding_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": STAGEC_EXTERNAL_PREREQUISITE_REPORT_SCHEMA,
        "status": STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS,
        "error_code": "NONE",
        "external_trust_authentication": STAGEC_EXTERNAL_TRUST_AUTHENTICATION,
        "runtime_authorization": STAGEC_EXTERNAL_RUNTIME_AUTHORIZATION,
        "authority": {
            "gate_5": "OPEN",
            "gate_5_disposition": "KEEP_OPEN",
            "stage_c": "DESIGN_ONLY",
            "execution_authority": "UNAUTHORIZED",
            "experiment": "NOT_STARTED",
            "license": "NOT LICENSED",
            "disclosure": "HELD",
            "corpus_status": "NOT FROZEN",
        },
        "locator_manifest": _ref_value(manifest_ref),
        "target_binding_sha256": target_binding_sha256,
        "artifact_count": len(roles),
        "locator_path_closure_sha256": canonical_sha256(
            {
                "domain": "cas_harness_v2.stagec_external_locator_paths.v1",
                "ordered_paths": [item.relative_path for item in roles],
            }
        ),
        "ordered_artifacts": [
            {
                "role": item.role,
                "artifact_ref": _ref_value(item.artifact_ref),
            }
            for item in roles
        ],
        "replay_order": [
            "DETECTOR_DRC",
            "FROZEN_CORPUS",
            "TRUSTED_STORAGE",
            "EXECUTION_AUTHORIZATION",
        ],
        "boundary": {
            "role_assignment": "EXPLICIT_MANIFEST_ONLY_NO_FILENAME_INFERENCE",
            "source_files": "DETACHED_EXACT_BYTES_AFTER_STABLE_SNAPSHOT",
            "source_network_client": "NOT_USED_FILESYSTEM_SOURCES_ONLY",
            "serialized_candidates": "STRUCTURAL_REPLAY_ONLY_NON_AUTHORITY",
            "intake_wrapper": "NOT_GENERATED_BY_IMPORTER",
            "admission_wrapper": "NOT_GENERATED_BY_IMPORTER",
            "nonce": "NOT_GENERATED_BY_IMPORTER",
            "trusted_time": "NOT_GENERATED_BY_IMPORTER",
        },
    }


def _require_snapshot(
    snapshot: StageCExternalPrerequisiteSnapshot,
    context: StageCPrerequisiteFactoryContext,
) -> None:
    if type(snapshot) is not StageCExternalPrerequisiteSnapshot:
        _fail("SNAPSHOT_INVALID", "snapshot has the wrong exact loader-only type")
    with _SNAPSHOT_SEALS_LOCK:
        seal = _SNAPSHOT_SEALS.get(id(snapshot))
    if (
        seal is None
        or seal.snapshot is not snapshot
        or seal.context is not context
        or snapshot.manifest_raw_bytes != seal.manifest_raw_bytes
        or snapshot.manifest_artifact_ref != seal.manifest_artifact_ref
        or snapshot.roles is not seal.roles
        or tuple(
            (item.role, item.relative_path, item.artifact_ref, item.raw_bytes)
            for item in snapshot.roles
        )
        != seal.role_values
        or (
            snapshot.detector_drc,
            snapshot.corpus,
            snapshot.trusted_storage,
            snapshot.authorization,
        )
        != seal.carrier_objects
        or not all(
            observed is expected
            for observed, expected in zip(
                (
                    snapshot.detector_drc,
                    snapshot.corpus,
                    snapshot.trusted_storage,
                    snapshot.authorization,
                ),
                seal.carrier_objects,
                strict=True,
            )
        )
        or (
            snapshot.detector_drc.artifact_ref,
            snapshot.corpus.artifact_ref,
            snapshot.trusted_storage.artifact_ref,
            snapshot.authorization.artifact_ref,
        )
        != seal.carrier_refs
        or (
            snapshot.role_snapshot("detector_drc").artifact_ref,
            snapshot.role_snapshot("frozen_corpus").artifact_ref,
            snapshot.role_snapshot("trusted_storage").artifact_ref,
            snapshot.role_snapshot("execution_authorization").artifact_ref,
        )
        != seal.carrier_refs
        or snapshot.report_raw_bytes != seal.report_raw_bytes
        or snapshot.report_sha256 != seal.report_sha256
        or snapshot.report is not seal.report
        or snapshot.report_raw_bytes != canonical_json_bytes(snapshot.report)
        or snapshot.report_sha256 != sha256_bytes(snapshot.report_raw_bytes)
        or len(snapshot.roles) != len(STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER)
        or tuple(item.role for item in snapshot.roles)
        != STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER
    ):
        _fail("SNAPSHOT_INVALID", "snapshot is not the unchanged loader-issued result")


@_closed_errors("SNAPSHOT_INVALID")
def load_stagec_external_prerequisite_snapshot(
    source: object,
    *,
    context: StageCPrerequisiteFactoryContext,
) -> StageCExternalPrerequisiteSnapshot:
    """Snapshot and structurally replay a fixed 16-role external source."""

    manifest_raw, manifest_target_sha256, source_rows = _collect_sources(source)
    if manifest_target_sha256 != context.target_binding_sha256:
        _fail(
            "MANIFEST_TARGET_MISMATCH",
            "locator manifest binds a different Stage C factory target",
        )
    roles_by_name = _role_map(source_rows)
    ordered_roles = tuple(
        roles_by_name[role] for role in STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER
    )
    _require_global_identity_closure(context, ordered_roles)
    drc, corpus, storage, authorization = _replay_carriers(
        roles_by_name, context=context
    )
    carrier_refs = (
        drc.artifact_ref,
        corpus.artifact_ref,
        storage.artifact_ref,
        authorization.artifact_ref,
    )
    manifest_carrier_refs = tuple(
        roles_by_name[role].artifact_ref
        for role in (
            "detector_drc",
            "frozen_corpus",
            "trusted_storage",
            "execution_authorization",
        )
    )
    if manifest_carrier_refs != carrier_refs:
        _fail(
            "ARTIFACT_REFERENCE_INVALID",
            "carrier manifest refs must retain the IDs declared by their bodies",
        )
    manifest_ref = _manifest_ref(manifest_raw)
    report_value = _snapshot_report_value(
        manifest_ref, ordered_roles, manifest_target_sha256
    )
    report_raw = canonical_json_bytes(report_value)
    snapshot = object.__new__(StageCExternalPrerequisiteSnapshot)
    object.__setattr__(snapshot, "manifest_raw_bytes", bytes(manifest_raw))
    object.__setattr__(snapshot, "manifest_artifact_ref", manifest_ref)
    object.__setattr__(snapshot, "roles", ordered_roles)
    object.__setattr__(snapshot, "detector_drc", drc)
    object.__setattr__(snapshot, "corpus", corpus)
    object.__setattr__(snapshot, "trusted_storage", storage)
    object.__setattr__(snapshot, "authorization", authorization)
    object.__setattr__(snapshot, "report_raw_bytes", report_raw)
    object.__setattr__(snapshot, "report_sha256", sha256_bytes(report_raw))
    object.__setattr__(snapshot, "report", freeze_json(report_value))
    with _SNAPSHOT_SEALS_LOCK:
        _SNAPSHOT_SEALS[id(snapshot)] = _SnapshotSeal(
            snapshot=snapshot,
            context=context,
            manifest_raw_bytes=snapshot.manifest_raw_bytes,
            manifest_artifact_ref=snapshot.manifest_artifact_ref,
            roles=snapshot.roles,
            role_values=tuple(
                (item.role, item.relative_path, item.artifact_ref, item.raw_bytes)
                for item in snapshot.roles
            ),
            carrier_objects=(drc, corpus, storage, authorization),
            carrier_refs=carrier_refs,
            report_raw_bytes=snapshot.report_raw_bytes,
            report_sha256=snapshot.report_sha256,
            report=snapshot.report,
        )
    return snapshot


@_closed_errors("CALLER_BINDING_INVALID")
def load_stagec_external_prerequisite_binding(
    snapshot: StageCExternalPrerequisiteSnapshot,
    *,
    context: StageCPrerequisiteFactoryContext,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...],
    intake_bytes: bytes,
    admission_bytes: bytes,
) -> StageCExternalPrerequisiteBinding:
    """Replay caller-supplied wrappers against an unchanged imported snapshot."""

    _require_snapshot(snapshot, context)
    if type(replay_bundles) is not tuple:
        _fail("CALLER_BINDING_INVALID", "replay_bundles must be an exact tuple")
    if type(intake_bytes) is not bytes or type(admission_bytes) is not bytes:
        _fail(
            "CALLER_BINDING_INVALID",
            "intake_bytes and admission_bytes must be caller-supplied exact bytes",
        )
    try:
        intake = load_stagec_prerequisite_intake(intake_bytes, context=context)
        admission = load_stagec_prerequisite_admission(
            admission_bytes,
            context=context,
            replay_bundles=replay_bundles,
            detector_drc=snapshot.detector_drc,
            corpus=snapshot.corpus,
            trusted_storage=snapshot.trusted_storage,
            authorization=snapshot.authorization,
            intake=intake,
        )
    except StageCPrerequisiteAdmissionError as exc:
        _fail("CALLER_BINDING_REPLAY_FAILED", str(exc))
    report_value = {
        "schema_version": STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_SCHEMA,
        "status": STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS,
        "error_code": "NONE",
        "external_trust_authentication": STAGEC_EXTERNAL_TRUST_AUTHENTICATION,
        "runtime_authorization": STAGEC_EXTERNAL_RUNTIME_AUTHORIZATION,
        "snapshot_report": _ref_value(snapshot.report_artifact_ref),
        "caller_supplied_intake": _ref_value(intake.artifact_ref),
        "caller_supplied_admission": _ref_value(admission.artifact_ref),
        "boundary": {
            "wrappers": "CALLER_SUPPLIED_AND_REPLAYED_NOT_GENERATED",
            "execution": "NOT_GRANTED_OR_PERFORMED",
            "external_trust": "NOT_AUTHENTICATED_BY_SERIALIZED_REPLAY",
        },
    }
    report_raw = canonical_json_bytes(report_value)
    binding = object.__new__(StageCExternalPrerequisiteBinding)
    object.__setattr__(binding, "snapshot", snapshot)
    object.__setattr__(binding, "intake", intake)
    object.__setattr__(binding, "admission", admission)
    object.__setattr__(binding, "report_raw_bytes", report_raw)
    object.__setattr__(binding, "report_sha256", sha256_bytes(report_raw))
    object.__setattr__(binding, "report", freeze_json(report_value))
    return binding


__all__ = [
    "STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_MEDIA_TYPE",
    "STAGEC_EXTERNAL_PREREQUISITE_BINDING_REPORT_SCHEMA",
    "STAGEC_EXTERNAL_PREREQUISITE_ERROR_CODES",
    "STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS",
    "STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME",
    "STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_MEDIA_TYPE",
    "STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_SCHEMA",
    "STAGEC_EXTERNAL_PREREQUISITE_MAXIMUM_FILE_BYTES",
    "STAGEC_EXTERNAL_PREREQUISITE_REPORT_MEDIA_TYPE",
    "STAGEC_EXTERNAL_PREREQUISITE_REPORT_SCHEMA",
    "STAGEC_EXTERNAL_PREREQUISITE_ROLE_MEDIA_TYPES",
    "STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER",
    "STAGEC_EXTERNAL_RUNTIME_AUTHORIZATION",
    "STAGEC_EXTERNAL_TRUST_AUTHENTICATION",
    "StageCExternalPrerequisiteBinding",
    "StageCExternalPrerequisiteIntakeError",
    "StageCExternalPrerequisiteRoleSnapshot",
    "StageCExternalPrerequisiteSnapshot",
    "load_stagec_external_prerequisite_binding",
    "load_stagec_external_prerequisite_snapshot",
]
