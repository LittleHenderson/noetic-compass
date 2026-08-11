"""Read-only import and verification report for historical evidence bytes.

Imported bytes remain ``HISTORICAL_EVIDENCE_ONLY``.  This module does not
parse or coerce an evidence payload, expose an Evidence Packet/result carrier,
grant authority, call a provider or model, use a live backend, or write files.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any
import unicodedata

from ._strict_json import canonical_json_bytes, freeze_json, load_json_object, sha256_bytes
from ._validation import (
    SchemaValidationError,
    expect_enum,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_string,
)
from .artifacts import EvidenceFile


HISTORICAL_SOURCE_MANIFEST_SCHEMA = (
    "cas_harness_v2.historical_source_manifest.v1"
)
HISTORICAL_EVIDENCE_IMPORT_SCHEMA = (
    "cas_harness_v2.historical_evidence_import_report.v1"
)
HISTORICAL_EVIDENCE_ONLY = "HISTORICAL_EVIDENCE_ONLY"
NON_AUTHORITY = "NON_AUTHORITY"
READ_ONLY = "READ_ONLY"
MATCHED = "MATCHED"
DRIFTED = "DRIFTED"
UNLISTED = "UNLISTED"
PROMOTION_INELIGIBLE = "INELIGIBLE"
DEFAULT_HISTORICAL_MANIFEST_RELATIVE_PATH = "historical_evidence_manifest.json"
HISTORICAL_SOURCE_MANIFEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.historical-source-manifest-v1+json"
)
HISTORICAL_EVIDENCE_IMPORT_MEDIA_TYPE = (
    "application/vnd.cas-harness.historical-evidence-import-report-v1+json"
)
MAXIMUM_HISTORICAL_FILE_BYTES = 32 * 1024 * 1024
MAXIMUM_HISTORICAL_FILE_COUNT = 10_000

__all__ = (
    "HISTORICAL_SOURCE_MANIFEST_SCHEMA",
    "HISTORICAL_EVIDENCE_IMPORT_SCHEMA",
    "HISTORICAL_EVIDENCE_ONLY",
    "NON_AUTHORITY",
    "READ_ONLY",
    "MATCHED",
    "DRIFTED",
    "UNLISTED",
    "PROMOTION_INELIGIBLE",
    "DEFAULT_HISTORICAL_MANIFEST_RELATIVE_PATH",
    "HISTORICAL_SOURCE_MANIFEST_MEDIA_TYPE",
    "HISTORICAL_EVIDENCE_IMPORT_MEDIA_TYPE",
    "MAXIMUM_HISTORICAL_FILE_BYTES",
    "MAXIMUM_HISTORICAL_FILE_COUNT",
    "HistoricalEvidenceImportError",
    "HistoricalSourceFileSnapshot",
    "HistoricalEvidenceRecord",
    "HistoricalEvidenceImportArtifact",
    "build_historical_evidence_import",
    "load_historical_evidence_import",
    "replay_historical_evidence_import",
)

_WINDOWS_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_WINDOWS_RESERVED_NAME_RE = re.compile(
    r"^(?:CON|PRN|AUX|NUL|CLOCK\$|CONIN\$|CONOUT\$|COM[1-9]|LPT[1-9])(?:\..*)?$",
    re.IGNORECASE,
)
_MEDIA_TYPE_RE = re.compile(r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+;-]+$")
_CURRENT_SLOT_TOKENS = frozenset({
    "current",
    "current-authority",
    "current-authorization",
    "current-evidence",
    "current-evidence-packet",
    "current-result",
})
_CURRENT_MEDIA_MARKERS = (
    "authorization",
    "permit",
    "evidence-packet",
    "result",
    "outcome",
)
_CURRENT_STATUS_VALUES = frozenset({
    "CURRENT",
    "CURRENT_AUTHORITY",
    "CURRENT_AUTHORIZATION",
    "CURRENT_EVIDENCE",
    "CURRENT_RESULT",
})
_STATUS = MappingProxyType({
    "classification": HISTORICAL_EVIDENCE_ONLY,
    "scope": READ_ONLY,
    "authority": NON_AUTHORITY,
})
_BOUNDARY = MappingProxyType({
    "promotion": "FORBIDDEN",
    "current_result": "NOT_CREATED",
    "current_evidence_packet": "NOT_CREATED",
    "authorization": "NOT_GRANTED",
    "provider_calls": 0,
    "model_calls": 0,
    "network_calls": 0,
    "filesystem_writes": 0,
    "live_backend_calls": 0,
})


class HistoricalEvidenceImportError(SchemaValidationError):
    """Raised when historical intake cannot remain exact and non-authoritative."""


@dataclass(frozen=True, slots=True)
class HistoricalSourceFileSnapshot:
    """Detached exact bytes for one original relative path."""

    source_file_id: str
    relative_path: str
    raw_bytes: bytes
    sha256: str
    byte_length: int

    def __post_init__(self) -> None:
        _validate_historical_identifier(
            self.source_file_id,
            "HistoricalSourceFileSnapshot.source_file_id",
        )
        _validate_relative_path(self.relative_path)
        if type(self.raw_bytes) is not bytes or not self.raw_bytes:
            raise HistoricalEvidenceImportError(
                "HistoricalSourceFileSnapshot.raw_bytes must be nonempty exact bytes"
            )
        if type(self.sha256) is not str or self.sha256 != sha256_bytes(self.raw_bytes):
            raise HistoricalEvidenceImportError(
                "HistoricalSourceFileSnapshot.sha256 differs from retained bytes"
            )
        if type(self.byte_length) is not int or self.byte_length != len(self.raw_bytes):
            raise HistoricalEvidenceImportError(
                "HistoricalSourceFileSnapshot.byte_length differs from retained bytes"
            )
        if self.byte_length > MAXIMUM_HISTORICAL_FILE_BYTES:
            raise HistoricalEvidenceImportError(
                "HistoricalSourceFileSnapshot exceeds the fixed per-file bound"
            )


@dataclass(frozen=True, slots=True)
class HistoricalEvidenceRecord:
    artifact_id: str
    source_bundle_id: str
    relative_path: str
    observed_sha256: str
    observed_byte_length: int
    original_sha256: str | None
    original_byte_length: int | None
    original_media_type: str | None
    original_status: str | None
    manifest_disposition: str
    evidence_classification: str
    promotion_eligibility: str

    def __post_init__(self) -> None:
        if (
            type(self.manifest_disposition) is not str
            or type(self.evidence_classification) is not str
            or type(self.promotion_eligibility) is not str
        ):
            raise HistoricalEvidenceImportError(
                "historical evidence status fields must be exact strings"
            )
        _validate_historical_identifier(
            self.artifact_id,
            "HistoricalEvidenceRecord.artifact_id",
        )
        _validate_historical_identifier(
            self.source_bundle_id, "HistoricalEvidenceRecord.source_bundle_id"
        )
        _validate_relative_path(self.relative_path)
        expect_sha256(self.observed_sha256, "HistoricalEvidenceRecord.observed_sha256")
        expect_int(
            self.observed_byte_length,
            "HistoricalEvidenceRecord.observed_byte_length",
            minimum=1,
        )
        if self.manifest_disposition in (MATCHED, DRIFTED):
            expect_sha256(self.original_sha256, "HistoricalEvidenceRecord.original_sha256")
            expect_int(
                self.original_byte_length,
                "HistoricalEvidenceRecord.original_byte_length",
                minimum=1,
            )
            _validate_media_type(
                self.original_media_type,
                "HistoricalEvidenceRecord.original_media_type",
            )
            _validate_original_status(
                self.original_status,
                "HistoricalEvidenceRecord.original_status",
            )
        elif self.manifest_disposition == UNLISTED:
            if any(
                value is not None
                for value in (
                    self.original_sha256,
                    self.original_byte_length,
                    self.original_media_type,
                    self.original_status,
                )
            ):
                raise HistoricalEvidenceImportError(
                    "UNLISTED evidence must keep original manifest fields absent"
                )
        else:
            raise HistoricalEvidenceImportError(
                "manifest_disposition must be MATCHED, DRIFTED, or UNLISTED"
            )
        if (
            self.evidence_classification != HISTORICAL_EVIDENCE_ONLY
            or self.promotion_eligibility != PROMOTION_INELIGIBLE
        ):
            raise HistoricalEvidenceImportError(
                "historical evidence classification and promotion status are fixed"
            )


@dataclass(frozen=True, slots=True)
class HistoricalEvidenceImportArtifact:
    """Canonical historical-only report; deliberately has no ArtifactRef API."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    import_id: str
    source_bundle_id: str
    manifest_relative_path: str
    source_files: tuple[HistoricalSourceFileSnapshot, ...]
    records: tuple[HistoricalEvidenceRecord, ...]
    covered_count: int
    matched_count: int
    drifted_count: int
    unlisted_count: int

    @property
    def payload(self) -> Mapping[str, Any]:
        """Return a fresh frozen view derived only from canonical report bytes."""

        _, value = _canonical_object(self.raw_bytes, "artifact.raw_bytes")
        return freeze_json(value)


@dataclass(frozen=True, slots=True)
class _DirectoryIdentity:
    relative_path: str
    device: int
    inode: int
    mode_type: int
    mtime_ns: int
    ctime_ns: int
    file_attributes: int | None
    reparse_tag: int | None


@dataclass(frozen=True, slots=True)
class _ManifestEntry:
    artifact_id: str
    source_bundle_id: str
    relative_path: str
    sha256: str
    byte_length: int
    media_type: str
    original_status: str


def _optional_stat_int(value: os.stat_result, name: str) -> int | None:
    observed = getattr(value, name, None)
    return None if observed is None else int(observed)


def _is_reparse_stat(value: os.stat_result) -> bool:
    attributes = _optional_stat_int(value, "st_file_attributes")
    tag = _optional_stat_int(value, "st_reparse_tag")
    return bool(
        (attributes is not None and attributes & _WINDOWS_REPARSE_ATTRIBUTE)
        or tag not in (None, 0)
    )


def _validate_relative_path(value: Any) -> str:
    if type(value) is not str or not value or len(value) > 1024:
        raise HistoricalEvidenceImportError(
            "relative path must be nonempty bounded exact text"
        )
    if unicodedata.normalize("NFC", value) != value:
        raise HistoricalEvidenceImportError("relative path must use NFC text")
    if (
        value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or ":" in value
        or "\x00" in value
        or "//" in value
    ):
        raise HistoricalEvidenceImportError(
            "relative path must not be absolute, backslashed, ADS-selected, or empty"
        )
    parts = value.split("/")
    if any(
        not part
        or part in (".", "..")
        or part.endswith((".", " "))
        or any(ord(character) < 32 for character in part)
        or _WINDOWS_RESERVED_NAME_RE.fullmatch(part) is not None
        for part in parts
    ):
        raise HistoricalEvidenceImportError(
            "relative path contains traversal, control, DOS-reserved, or unsafe segments"
        )
    if parts[0].endswith(":"):
        raise HistoricalEvidenceImportError("relative path must not contain a drive form")
    folded_parts = {_normalized_authority_token(part) for part in parts}
    if any(_is_current_slot_token(part) for part in folded_parts):
        raise HistoricalEvidenceImportError(
            "historical evidence cannot occupy a current result or authority path"
        )
    return value


def _validate_no_casefold_collisions(paths: tuple[str, ...], path: str) -> None:
    folded: dict[str, str] = {}
    for relative_path in paths:
        _validate_relative_path(relative_path)
        key = unicodedata.normalize("NFKC", relative_path).casefold()
        prior = folded.get(key)
        if prior is not None:
            raise HistoricalEvidenceImportError(
                f"{path} contains a casefold path collision: {prior!r}, {relative_path!r}"
            )
        folded[key] = relative_path


def _validate_media_type(value: Any, path: str) -> str:
    media_type = expect_string(value, path, maximum=128)
    if _MEDIA_TYPE_RE.fullmatch(media_type) is None:
        raise HistoricalEvidenceImportError(f"{path} must be one exact media type")
    folded = _normalized_authority_token(media_type)
    if any(marker in folded for marker in _CURRENT_MEDIA_MARKERS):
        raise HistoricalEvidenceImportError(
            f"{path} attempts to occupy a current evidence or authority media slot"
        )
    return media_type


def _validate_original_status(value: Any, path: str) -> str:
    status = expect_string(value, path, maximum=128)
    if (
        status != status.strip()
        or unicodedata.normalize("NFC", status) != status
        or any(ord(character) < 32 for character in status)
    ):
        raise HistoricalEvidenceImportError(
            f"{path} must be exact normalized non-control text"
        )
    normalized = _normalized_authority_token(status)
    if status.upper() in _CURRENT_STATUS_VALUES or _is_current_slot_token(normalized):
        raise HistoricalEvidenceImportError(
            f"{path} attempts a current-authority relabeling"
        )
    return status


def _validate_historical_identifier(value: Any, path: str) -> str:
    identifier = expect_machine_id(value, path)
    folded = _normalized_authority_token(identifier)
    if folded.startswith("current-") or any(
        marker in folded
        for marker in (
            "current-result",
            "current-authority",
            "current-authorization",
        )
    ):
        raise HistoricalEvidenceImportError(
            f"{path} attempts to reserve a current result or authority identity"
        )
    return identifier


def _normalized_authority_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _is_current_slot_token(value: str) -> bool:
    return value == "current" or any(
        value == marker or value.startswith(marker + "-")
        for marker in _CURRENT_SLOT_TOKENS
        if marker != "current"
    )


def _canonical_object(raw: Any, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise HistoricalEvidenceImportError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, value
    except HistoricalEvidenceImportError:
        raise
    except (TypeError, ValueError) as exc:
        raise HistoricalEvidenceImportError(f"{path}: {exc}") from exc


def _require_local_directory(path: Path) -> None:
    if not path.is_absolute():
        raise HistoricalEvidenceImportError("directory source must be absolute")
    if os.name == "nt":
        anchor = path.anchor
        if anchor.startswith("\\\\") or str(path).startswith("\\\\?\\"):
            raise HistoricalEvidenceImportError(
                "UNC, device, and remote directory sources are forbidden"
            )
        try:
            import ctypes

            drive_type = int(ctypes.windll.kernel32.GetDriveTypeW(anchor))
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise HistoricalEvidenceImportError(
                "local directory drive type could not be established"
            ) from exc
        if drive_type in (0, 1, 4):
            raise HistoricalEvidenceImportError(
                "directory source must be an available local filesystem"
            )
    current = Path(path.parts[0])
    for index, part in enumerate(path.parts):
        if index:
            current = current / part
        try:
            observed = os.lstat(current)
        except OSError as exc:
            raise HistoricalEvidenceImportError(
                "directory source path component is unavailable"
            ) from exc
        if stat.S_IFMT(observed.st_mode) == stat.S_IFLNK or _is_reparse_stat(observed):
            raise HistoricalEvidenceImportError(
                "directory source contains a symbolic link or reparse point"
            )
        if stat.S_IFMT(observed.st_mode) != stat.S_IFDIR:
            raise HistoricalEvidenceImportError(
                "directory source path component must be a directory"
            )


def _directory_identity(root: Path, path: Path) -> _DirectoryIdentity:
    try:
        observed = os.lstat(path)
    except OSError as exc:
        raise HistoricalEvidenceImportError("directory closure changed") from exc
    mode_type = int(stat.S_IFMT(observed.st_mode))
    if mode_type == stat.S_IFLNK or _is_reparse_stat(observed):
        raise HistoricalEvidenceImportError(
            "directory closure contains a symbolic link or reparse point"
        )
    if mode_type != stat.S_IFDIR:
        raise HistoricalEvidenceImportError("directory closure entry is not a directory")
    relative = "" if path == root else _validate_relative_path(path.relative_to(root).as_posix())
    return _DirectoryIdentity(
        relative_path=relative,
        device=int(observed.st_dev),
        inode=int(observed.st_ino),
        mode_type=mode_type,
        mtime_ns=int(observed.st_mtime_ns),
        ctime_ns=int(observed.st_ctime_ns),
        file_attributes=_optional_stat_int(observed, "st_file_attributes"),
        reparse_tag=_optional_stat_int(observed, "st_reparse_tag"),
    )


def _scan_directory(
    root: Path,
) -> tuple[tuple[tuple[str, Path], ...], tuple[_DirectoryIdentity, ...]]:
    files: list[tuple[str, Path]] = []
    directories: list[_DirectoryIdentity] = []
    all_relative_paths: list[str] = []

    def failed(error: OSError) -> None:
        raise HistoricalEvidenceImportError("directory closure could not be enumerated") from error

    for current_text, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
        onerror=failed,
    ):
        current = Path(current_text)
        directories.append(_directory_identity(root, current))
        directory_names.sort()
        file_names.sort()
        for name in directory_names:
            child = current / name
            identity = _directory_identity(root, child)
            all_relative_paths.append(identity.relative_path)
        for name in file_names:
            child = current / name
            relative_path = _validate_relative_path(child.relative_to(root).as_posix())
            try:
                observed = os.lstat(child)
            except OSError as exc:
                raise HistoricalEvidenceImportError(
                    "directory file became unavailable during enumeration"
                ) from exc
            mode_type = int(stat.S_IFMT(observed.st_mode))
            if mode_type == stat.S_IFLNK or _is_reparse_stat(observed):
                raise HistoricalEvidenceImportError(
                    "directory closure contains a symbolic link or reparse point"
                )
            if mode_type != stat.S_IFREG:
                raise HistoricalEvidenceImportError(
                    "directory closure contains a non-regular file"
                )
            all_relative_paths.append(relative_path)
            files.append((relative_path, child))
    _validate_no_casefold_collisions(tuple(all_relative_paths), "directory closure")
    if not files:
        raise HistoricalEvidenceImportError("directory closure must contain files")
    if len(files) > MAXIMUM_HISTORICAL_FILE_COUNT:
        raise HistoricalEvidenceImportError("directory closure exceeds the file-count bound")
    return tuple(sorted(files)), tuple(sorted(directories, key=lambda item: item.relative_path))


def _snapshot_evidence_file(
    relative_path: str,
    source: EvidenceFile,
    *,
    maximum_file_bytes: int,
) -> HistoricalSourceFileSnapshot:
    if type(source) is not EvidenceFile:
        raise HistoricalEvidenceImportError(
            "source values must be exact EvidenceFile snapshots"
        )
    try:
        snapshot = source.snapshot_bytes(maximum_byte_count=maximum_file_bytes)
    except (OSError, SchemaValidationError, TypeError, ValueError) as exc:
        raise HistoricalEvidenceImportError(
            f"historical source file {relative_path!r} changed or is unsafe: {exc}"
        ) from exc
    return HistoricalSourceFileSnapshot(
        source_file_id=source.artifact_id,
        relative_path=relative_path,
        raw_bytes=snapshot.raw_bytes,
        sha256=snapshot.sha256,
        byte_length=snapshot.byte_length,
    )


def _snapshot_mapping(
    source: dict[str, Any], *, maximum_file_bytes: int
) -> tuple[HistoricalSourceFileSnapshot, ...]:
    if type(source) is not dict:
        raise HistoricalEvidenceImportError(
            "mapping source must be an exact dict"
        )
    before = tuple(source.items())
    if not before or len(before) > MAXIMUM_HISTORICAL_FILE_COUNT:
        raise HistoricalEvidenceImportError(
            "mapping source must have a bounded nonempty exact closure"
        )
    paths: list[str] = []
    source_ids: set[str] = set()
    for relative_path, evidence_file in before:
        if type(relative_path) is not str:
            raise HistoricalEvidenceImportError("mapping keys must be exact relative paths")
        paths.append(_validate_relative_path(relative_path))
        if type(evidence_file) is not EvidenceFile:
            raise HistoricalEvidenceImportError(
                "mapping values must be exact EvidenceFile snapshots"
            )
        _require_local_directory(evidence_file.path.parent)
        source_file_id = _validate_historical_identifier(
            evidence_file.artifact_id,
            "mapping EvidenceFile.artifact_id",
        )
        if source_file_id in source_ids:
            raise HistoricalEvidenceImportError("mapping source_file_id values must be unique")
        source_ids.add(source_file_id)
    _validate_no_casefold_collisions(tuple(paths), "mapping source")
    snapshots = tuple(
        _snapshot_evidence_file(
            relative_path,
            evidence_file,
            maximum_file_bytes=maximum_file_bytes,
        )
        for relative_path, evidence_file in before
    )
    after = tuple(source.items())
    if len(after) != len(before) or any(
        left_path != right_path or left_file is not right_file
        for (left_path, left_file), (right_path, right_file) in zip(
            before, after, strict=True
        )
    ):
        raise HistoricalEvidenceImportError("mapping closure changed during snapshot")
    if any(not evidence_file.verify_current() for _, evidence_file in before):
        raise HistoricalEvidenceImportError("mapping source changed after snapshot")
    return tuple(sorted(snapshots, key=lambda item: item.relative_path))


def _snapshot_directory(
    source: object, *, maximum_file_bytes: int
) -> tuple[HistoricalSourceFileSnapshot, ...]:
    if type(source) is str:
        rendered = source
    elif type(source) is type(Path()):
        rendered = str(source)
    else:
        raise HistoricalEvidenceImportError(
            "directory source must be an exact str or platform Path"
        )
    if not rendered or "\x00" in rendered:
        raise HistoricalEvidenceImportError("directory source must be nonempty exact text")
    if not Path(rendered).is_absolute():
        raise HistoricalEvidenceImportError("directory source must be absolute")
    root = Path(os.path.abspath(rendered))
    _require_local_directory(root)
    first_files, first_directories = _scan_directory(root)
    evidence_files: list[tuple[str, EvidenceFile]] = []
    for relative_path, path in first_files:
        source_id = (
            "historical-source-"
            + sha256_bytes(relative_path.encode("utf-8"))[:32].lower()
        )
        try:
            evidence_file = EvidenceFile.from_path(
                source_id,
                path,
                maximum_byte_count=maximum_file_bytes,
            )
        except (OSError, SchemaValidationError, TypeError, ValueError) as exc:
            raise HistoricalEvidenceImportError(
                f"historical directory file {relative_path!r} is unsafe: {exc}"
            ) from exc
        evidence_files.append((relative_path, evidence_file))
    snapshots = tuple(
        _snapshot_evidence_file(
            relative_path,
            evidence_file,
            maximum_file_bytes=maximum_file_bytes,
        )
        for relative_path, evidence_file in evidence_files
    )
    second_files, second_directories = _scan_directory(root)
    if first_files != second_files or first_directories != second_directories:
        raise HistoricalEvidenceImportError("directory closure changed during snapshot")
    if any(not evidence_file.verify_current() for _, evidence_file in evidence_files):
        raise HistoricalEvidenceImportError("directory file changed after snapshot")
    return snapshots


def _snapshot_source(
    source: object, *, maximum_file_bytes: int
) -> tuple[HistoricalSourceFileSnapshot, ...]:
    expect_int(maximum_file_bytes, "maximum_file_bytes", minimum=1)
    if maximum_file_bytes > MAXIMUM_HISTORICAL_FILE_BYTES:
        raise HistoricalEvidenceImportError(
            "maximum_file_bytes cannot exceed the fixed historical intake bound"
        )
    if type(source) is dict:
        return _snapshot_mapping(source, maximum_file_bytes=maximum_file_bytes)
    if type(source) is MappingProxyType:
        raise HistoricalEvidenceImportError("mapping source must be an exact dict")
    return _snapshot_directory(source, maximum_file_bytes=maximum_file_bytes)


def _parse_manifest(
    raw: bytes,
) -> tuple[str, tuple[_ManifestEntry, ...]]:
    _, value = _canonical_object(raw, "historical source manifest")
    expect_keys(value, required={"schema", "source_bundle_id", "entries"}, path="$manifest")
    if value["schema"] != HISTORICAL_SOURCE_MANIFEST_SCHEMA:
        raise HistoricalEvidenceImportError("historical source manifest schema drifted")
    source_bundle_id = _validate_historical_identifier(
        value["source_bundle_id"], "$manifest.source_bundle_id"
    )
    raw_entries = expect_list(value["entries"], "$manifest.entries")
    entries: list[_ManifestEntry] = []
    ids: set[str] = set()
    contents: set[tuple[str, int]] = set()
    paths: list[str] = []
    for index, raw_entry in enumerate(raw_entries):
        path = f"$manifest.entries[{index}]"
        entry = expect_object(raw_entry, path)
        expect_keys(
            entry,
            required={
                "artifact_id", "source_bundle_id", "relative_path", "sha256",
                "byte_length", "media_type", "original_status",
            },
            path=path,
        )
        artifact_id = _validate_historical_identifier(
            entry["artifact_id"], f"{path}.artifact_id"
        )
        entry_bundle_id = _validate_historical_identifier(
            entry["source_bundle_id"], f"{path}.source_bundle_id"
        )
        if entry_bundle_id != source_bundle_id:
            raise HistoricalEvidenceImportError(
                "historical manifest mixes source bundle identities"
            )
        relative_path = _validate_relative_path(entry["relative_path"])
        digest = expect_sha256(entry["sha256"], f"{path}.sha256")
        byte_length = expect_int(entry["byte_length"], f"{path}.byte_length", minimum=1)
        media_type = _validate_media_type(entry["media_type"], f"{path}.media_type")
        original_status = _validate_original_status(
            entry["original_status"], f"{path}.original_status"
        )
        if artifact_id in ids:
            raise HistoricalEvidenceImportError(
                "historical manifest contains duplicate artifact IDs"
            )
        content = (digest, byte_length)
        if content in contents:
            raise HistoricalEvidenceImportError(
                "historical manifest contains duplicate content identities"
            )
        ids.add(artifact_id)
        contents.add(content)
        paths.append(relative_path)
        entries.append(
            _ManifestEntry(
                artifact_id=artifact_id,
                source_bundle_id=entry_bundle_id,
                relative_path=relative_path,
                sha256=digest,
                byte_length=byte_length,
                media_type=media_type,
                original_status=original_status,
            )
        )
    _validate_no_casefold_collisions(tuple(paths), "historical manifest")
    if tuple(paths) != tuple(sorted(paths)):
        raise HistoricalEvidenceImportError(
            "historical manifest entries must use exact relative-path order"
        )
    return source_bundle_id, tuple(entries)


def _record_value(record: HistoricalEvidenceRecord) -> dict[str, Any]:
    return {
        "artifact_id": record.artifact_id,
        "source_bundle_id": record.source_bundle_id,
        "relative_path": record.relative_path,
        "observed_sha256": record.observed_sha256,
        "observed_byte_length": record.observed_byte_length,
        "original_sha256": record.original_sha256,
        "original_byte_length": record.original_byte_length,
        "original_media_type": record.original_media_type,
        "original_status": record.original_status,
        "manifest_disposition": record.manifest_disposition,
        "evidence_classification": record.evidence_classification,
        "promotion_eligibility": record.promotion_eligibility,
    }


def _derive_report(
    *,
    import_id: str,
    manifest_relative_path: str,
    source_files: tuple[HistoricalSourceFileSnapshot, ...],
) -> tuple[str, tuple[HistoricalEvidenceRecord, ...], dict[str, Any]]:
    if type(source_files) is not tuple or not source_files:
        raise HistoricalEvidenceImportError(
            "source_files must be a nonempty exact tuple"
        )
    if len(source_files) > MAXIMUM_HISTORICAL_FILE_COUNT:
        raise HistoricalEvidenceImportError(
            "source_files exceed the fixed historical file-count bound"
        )
    paths: list[str] = []
    source_ids: set[str] = set()
    contents: set[tuple[str, int]] = set()
    by_path: dict[str, HistoricalSourceFileSnapshot] = {}
    for index, source_file in enumerate(source_files):
        if type(source_file) is not HistoricalSourceFileSnapshot:
            raise HistoricalEvidenceImportError(
                f"source_files[{index}] must have the exact snapshot type"
            )
        source_file.__post_init__()
        if source_file.byte_length > MAXIMUM_HISTORICAL_FILE_BYTES:
            raise HistoricalEvidenceImportError(
                "source_files exceed the fixed historical per-file bound"
            )
        if source_file.source_file_id in source_ids:
            raise HistoricalEvidenceImportError("source_files contain duplicate source IDs")
        content = (source_file.sha256, source_file.byte_length)
        if content in contents:
            raise HistoricalEvidenceImportError(
                "source_files contain duplicate content identities"
            )
        source_ids.add(source_file.source_file_id)
        contents.add(content)
        paths.append(source_file.relative_path)
        by_path[source_file.relative_path] = source_file
    _validate_no_casefold_collisions(tuple(paths), "source_files")
    if tuple(paths) != tuple(sorted(paths)):
        raise HistoricalEvidenceImportError(
            "source_files must use exact relative-path order"
        )
    manifest_relative_path = _validate_relative_path(manifest_relative_path)
    manifest_file = by_path.get(manifest_relative_path)
    if manifest_file is None:
        raise HistoricalEvidenceImportError("historical manifest file is missing")
    source_bundle_id, manifest_entries = _parse_manifest(manifest_file.raw_bytes)
    manifest_ids = {entry.artifact_id for entry in manifest_entries}
    protected_owner_ids = {import_id, source_bundle_id}
    if len(protected_owner_ids) != 2:
        raise HistoricalEvidenceImportError(
            "import and source-bundle owner identities must be distinct"
        )
    owner_collisions = sorted(protected_owner_ids.intersection(source_ids | manifest_ids))
    if owner_collisions:
        raise HistoricalEvidenceImportError(
            "historical owner identities collide with source or manifest artifacts: "
            f"{owner_collisions}"
        )
    reused_ids = sorted(source_ids.intersection(manifest_ids))
    if reused_ids:
        raise HistoricalEvidenceImportError(
            "source snapshot IDs and manifest artifact IDs must be globally distinct: "
            f"{reused_ids}"
        )
    declared_paths = {entry.relative_path for entry in manifest_entries}
    if manifest_relative_path in declared_paths:
        raise HistoricalEvidenceImportError(
            "historical manifest cannot list itself as evidence"
        )
    missing = sorted(declared_paths - set(by_path))
    if missing:
        raise HistoricalEvidenceImportError(
            f"historical manifest references missing files: {missing}"
        )
    records: list[HistoricalEvidenceRecord] = []
    declared_ids: set[str] = set()
    for entry in manifest_entries:
        observed = by_path[entry.relative_path]
        disposition = (
            MATCHED
            if observed.sha256 == entry.sha256
            and observed.byte_length == entry.byte_length
            else DRIFTED
        )
        declared_ids.add(entry.artifact_id)
        records.append(
            HistoricalEvidenceRecord(
                artifact_id=entry.artifact_id,
                source_bundle_id=source_bundle_id,
                relative_path=entry.relative_path,
                observed_sha256=observed.sha256,
                observed_byte_length=observed.byte_length,
                original_sha256=entry.sha256,
                original_byte_length=entry.byte_length,
                original_media_type=entry.media_type,
                original_status=entry.original_status,
                manifest_disposition=disposition,
                evidence_classification=HISTORICAL_EVIDENCE_ONLY,
                promotion_eligibility=PROMOTION_INELIGIBLE,
            )
        )
    unlisted_paths = sorted(set(by_path) - declared_paths - {manifest_relative_path})
    for relative_path in unlisted_paths:
        observed = by_path[relative_path]
        derived_id = (
            "historical-unlisted-"
            + sha256_bytes(
                (
                    source_bundle_id
                    + "\x00"
                    + relative_path
                    + "\x00"
                    + observed.sha256
                ).encode("utf-8")
            )[:32].lower()
        )
        if derived_id in declared_ids:
            raise HistoricalEvidenceImportError(
                "derived unlisted identity collides with a manifest artifact ID"
            )
        if derived_id in source_ids:
            raise HistoricalEvidenceImportError(
                "derived unlisted identity collides with a source snapshot ID"
            )
        if derived_id in protected_owner_ids:
            raise HistoricalEvidenceImportError(
                "derived unlisted identity collides with a report owner ID"
            )
        declared_ids.add(derived_id)
        records.append(
            HistoricalEvidenceRecord(
                artifact_id=derived_id,
                source_bundle_id=source_bundle_id,
                relative_path=relative_path,
                observed_sha256=observed.sha256,
                observed_byte_length=observed.byte_length,
                original_sha256=None,
                original_byte_length=None,
                original_media_type=None,
                original_status=None,
                manifest_disposition=UNLISTED,
                evidence_classification=HISTORICAL_EVIDENCE_ONLY,
                promotion_eligibility=PROMOTION_INELIGIBLE,
            )
        )
    records.sort(key=lambda record: record.relative_path)
    matched_count = sum(record.manifest_disposition == MATCHED for record in records)
    drifted_count = sum(record.manifest_disposition == DRIFTED for record in records)
    unlisted_count = sum(record.manifest_disposition == UNLISTED for record in records)
    report = {
        "schema": HISTORICAL_EVIDENCE_IMPORT_SCHEMA,
        "import_id": import_id,
        "source_bundle_id": source_bundle_id,
        "manifest": {
            "relative_path": manifest_relative_path,
            "sha256": manifest_file.sha256,
            "byte_length": manifest_file.byte_length,
            "media_type": HISTORICAL_SOURCE_MANIFEST_MEDIA_TYPE,
            "covered": len(manifest_entries),
            "matched": matched_count,
            "drifted": drifted_count,
            "unlisted": unlisted_count,
        },
        "records": [_record_value(record) for record in records],
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }
    return source_bundle_id, tuple(records), report


def _load_historical_evidence_import(
    raw: Any,
    *,
    import_id: str,
    manifest_relative_path: str,
    source_files: tuple[HistoricalSourceFileSnapshot, ...],
) -> HistoricalEvidenceImportArtifact:
    snapshot, value = _canonical_object(raw, "historical evidence import report")
    import_id = _validate_historical_identifier(import_id, "import_id")
    if not import_id.casefold().startswith("historical-import-"):
        raise HistoricalEvidenceImportError(
            "import_id must remain in the historical-import namespace"
        )
    source_bundle_id, records, expected = _derive_report(
        import_id=import_id,
        manifest_relative_path=manifest_relative_path,
        source_files=source_files,
    )
    expect_keys(
        value,
        required={
            "schema", "import_id", "source_bundle_id", "manifest", "records",
            "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != HISTORICAL_EVIDENCE_IMPORT_SCHEMA:
        raise HistoricalEvidenceImportError("historical import report schema drifted")
    if expect_machine_id(value["import_id"], "$.import_id") != import_id:
        raise HistoricalEvidenceImportError("report import_id differs from caller binding")
    if (
        expect_machine_id(value["source_bundle_id"], "$.source_bundle_id")
        != source_bundle_id
    ):
        raise HistoricalEvidenceImportError(
            "report source_bundle_id differs from manifest binding"
        )
    manifest = expect_object(value["manifest"], "$.manifest")
    expect_keys(
        manifest,
        required={
            "relative_path", "sha256", "byte_length", "media_type", "covered",
            "matched", "drifted", "unlisted",
        },
        path="$.manifest",
    )
    _validate_relative_path(manifest["relative_path"])
    expect_sha256(manifest["sha256"], "$.manifest.sha256")
    expect_int(manifest["byte_length"], "$.manifest.byte_length", minimum=1)
    _validate_media_type(manifest["media_type"], "$.manifest.media_type")
    for name in ("covered", "matched", "drifted", "unlisted"):
        expect_int(manifest[name], f"$.manifest.{name}", minimum=0)
    raw_records = expect_list(value["records"], "$.records")
    if len(raw_records) != len(records):
        raise HistoricalEvidenceImportError(
            "report record count differs from exact source snapshots"
        )
    for index, raw_record in enumerate(raw_records):
        record = expect_object(raw_record, f"$.records[{index}]")
        expect_keys(record, required=_record_value(records[index]), path=f"$.records[{index}]")
        path = f"$.records[{index}]"
        expect_machine_id(record["artifact_id"], f"{path}.artifact_id")
        expect_machine_id(record["source_bundle_id"], f"{path}.source_bundle_id")
        _validate_relative_path(record["relative_path"])
        expect_sha256(record["observed_sha256"], f"{path}.observed_sha256")
        expect_int(
            record["observed_byte_length"],
            f"{path}.observed_byte_length",
            minimum=1,
        )
        disposition = expect_enum(
            record["manifest_disposition"],
            {MATCHED, DRIFTED, UNLISTED},
            f"{path}.manifest_disposition",
        )
        if disposition == UNLISTED:
            if any(
                record[name] is not None
                for name in (
                    "original_sha256",
                    "original_byte_length",
                    "original_media_type",
                    "original_status",
                )
            ):
                raise HistoricalEvidenceImportError(
                    f"{path} unlisted original fields must remain null"
                )
        else:
            expect_sha256(record["original_sha256"], f"{path}.original_sha256")
            expect_int(
                record["original_byte_length"],
                f"{path}.original_byte_length",
                minimum=1,
            )
            _validate_media_type(
                record["original_media_type"], f"{path}.original_media_type"
            )
            _validate_original_status(
                record["original_status"], f"{path}.original_status"
            )
        if (
            expect_string(
                record["evidence_classification"],
                f"{path}.evidence_classification",
                maximum=64,
            )
            != HISTORICAL_EVIDENCE_ONLY
            or expect_string(
                record["promotion_eligibility"],
                f"{path}.promotion_eligibility",
                maximum=32,
            )
            != PROMOTION_INELIGIBLE
        ):
            raise HistoricalEvidenceImportError(
                f"{path} attempts to promote historical evidence"
            )
    status = expect_object(value["status"], "$.status")
    expect_keys(status, required=_STATUS, path="$.status")
    if status != _STATUS:
        raise HistoricalEvidenceImportError(
            "report status must remain historical-only read-only non-authority"
        )
    boundary = expect_object(value["boundary"], "$.boundary")
    expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    for name in (
        "provider_calls",
        "model_calls",
        "network_calls",
        "filesystem_writes",
        "live_backend_calls",
    ):
        if expect_int(boundary[name], f"$.boundary.{name}", minimum=0) != 0:
            raise HistoricalEvidenceImportError(
                "report boundary cannot claim provider/model/network/write/live calls"
            )
    if any(
        boundary[name] != expected_value
        for name, expected_value in _BOUNDARY.items()
        if type(expected_value) is str
    ):
        raise HistoricalEvidenceImportError(
            "report boundary cannot claim promotion, current results, or authority"
        )
    if value != expected:
        raise HistoricalEvidenceImportError(
            "historical import report differs from its exact source snapshots"
        )
    matched_count = sum(record.manifest_disposition == MATCHED for record in records)
    drifted_count = sum(record.manifest_disposition == DRIFTED for record in records)
    unlisted_count = sum(record.manifest_disposition == UNLISTED for record in records)
    return HistoricalEvidenceImportArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        import_id=import_id,
        source_bundle_id=source_bundle_id,
        manifest_relative_path=manifest_relative_path,
        source_files=source_files,
        records=records,
        covered_count=matched_count + drifted_count,
        matched_count=matched_count,
        drifted_count=drifted_count,
        unlisted_count=unlisted_count,
    )


def build_historical_evidence_import(
    *,
    import_id: str,
    source: object,
    manifest_relative_path: str = DEFAULT_HISTORICAL_MANIFEST_RELATIVE_PATH,
    maximum_file_bytes: int = MAXIMUM_HISTORICAL_FILE_BYTES,
) -> HistoricalEvidenceImportArtifact:
    """Stable-snapshot one safe source closure and build a historical-only report."""

    import_id = _validate_historical_identifier(import_id, "import_id")
    if not import_id.casefold().startswith("historical-import-"):
        raise HistoricalEvidenceImportError(
            "import_id must remain in the historical-import namespace"
        )
    manifest_relative_path = _validate_relative_path(manifest_relative_path)
    source_files = _snapshot_source(source, maximum_file_bytes=maximum_file_bytes)
    _, _, report = _derive_report(
        import_id=import_id,
        manifest_relative_path=manifest_relative_path,
        source_files=source_files,
    )
    raw = canonical_json_bytes(report)
    return _load_historical_evidence_import(
        raw,
        import_id=import_id,
        manifest_relative_path=manifest_relative_path,
        source_files=source_files,
    )


def load_historical_evidence_import(
    raw: bytes | bytearray | memoryview,
    *,
    import_id: str,
    manifest_relative_path: str,
    source_files: tuple[HistoricalSourceFileSnapshot, ...],
) -> HistoricalEvidenceImportArtifact:
    """Load canonical report bytes against detached exact historical snapshots."""

    return _load_historical_evidence_import(
        raw,
        import_id=import_id,
        manifest_relative_path=manifest_relative_path,
        source_files=source_files,
    )


def replay_historical_evidence_import(
    artifact: HistoricalEvidenceImportArtifact,
) -> HistoricalEvidenceImportArtifact:
    """Freshly replay one immutable historical-only report projection."""

    if type(artifact) is not HistoricalEvidenceImportArtifact:
        raise HistoricalEvidenceImportError(
            "artifact must be an exact HistoricalEvidenceImportArtifact"
        )
    if (
        type(artifact.raw_bytes) is not bytes
        or type(artifact.sha256) is not str
        or type(artifact.byte_length) is not int
        or type(artifact.import_id) is not str
        or type(artifact.source_bundle_id) is not str
        or type(artifact.manifest_relative_path) is not str
        or type(artifact.source_files) is not tuple
        or type(artifact.records) is not tuple
        or type(artifact.covered_count) is not int
        or type(artifact.matched_count) is not int
        or type(artifact.drifted_count) is not int
        or type(artifact.unlisted_count) is not int
    ):
        raise HistoricalEvidenceImportError(
            "historical import projections must use exact immutable types"
        )
    if any(type(item) is not HistoricalSourceFileSnapshot for item in artifact.source_files):
        raise HistoricalEvidenceImportError(
            "source_files must contain exact HistoricalSourceFileSnapshot values"
        )
    if any(type(item) is not HistoricalEvidenceRecord for item in artifact.records):
        raise HistoricalEvidenceImportError(
            "records must contain exact HistoricalEvidenceRecord values"
        )
    replayed = _load_historical_evidence_import(
        artifact.raw_bytes,
        import_id=artifact.import_id,
        manifest_relative_path=artifact.manifest_relative_path,
        source_files=artifact.source_files,
    )
    if replayed != artifact:
        raise HistoricalEvidenceImportError(
            "historical import differs from fresh exact-byte replay"
        )
    return replayed
