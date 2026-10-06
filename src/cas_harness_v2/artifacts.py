"""Snapshot registry for exact Evidence Packet and preregistration dependencies."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
from types import MappingProxyType

from ._strict_json import sha256_bytes
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_int,
    expect_machine_id,
    expect_sha256,
)


_FILE_HASH_CHUNK_SIZE = 1024 * 1024
_WINDOWS_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


@dataclass(frozen=True, slots=True)
class _StableFileIdentity:
    device: int
    inode: int
    mode_type: int
    link_count: int
    byte_count: int
    mtime_ns: int
    ctime_ns: int
    file_attributes: int | None
    reparse_tag: int | None

    @classmethod
    def from_stat(cls, value: os.stat_result) -> _StableFileIdentity:
        return cls(
            device=int(value.st_dev),
            inode=int(value.st_ino),
            mode_type=int(stat.S_IFMT(value.st_mode)),
            link_count=int(value.st_nlink),
            byte_count=int(value.st_size),
            mtime_ns=int(value.st_mtime_ns),
            ctime_ns=int(value.st_ctime_ns),
            file_attributes=_optional_stat_int(value, "st_file_attributes"),
            reparse_tag=_optional_stat_int(value, "st_reparse_tag"),
        )


@dataclass(frozen=True, slots=True)
class _StructuralPathIdentity:
    device: int
    inode: int
    mode_type: int
    file_attributes: int | None
    reparse_tag: int | None

    @classmethod
    def from_identity(
        cls,
        value: _StableFileIdentity,
    ) -> _StructuralPathIdentity:
        return cls(
            device=value.device,
            inode=value.inode,
            mode_type=value.mode_type,
            file_attributes=value.file_attributes,
            reparse_tag=value.reparse_tag,
        )


def _optional_stat_int(value: os.stat_result, name: str) -> int | None:
    observed = getattr(value, name, None)
    return None if observed is None else int(observed)


def _normalize_file_path(value: object) -> Path:
    if isinstance(value, bytes):
        raise SchemaValidationError("artifact file path must be text, not bytes")
    try:
        raw = os.fspath(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise SchemaValidationError("artifact file path must be path-like") from exc
    if type(raw) is not str or not raw or "\x00" in raw:
        raise SchemaValidationError("artifact file path must be non-empty text")
    normalized = Path(os.path.abspath(raw))
    if os.name == "nt":
        rendered = str(normalized)
        drive = normalized.drive
        if ":" in rendered[len(drive) :]:
            raise SchemaValidationError(
                "artifact file path must not select an NTFS alternate data stream"
            )
    return normalized


def _is_reparse(value: _StableFileIdentity) -> bool:
    return bool(
        (
            value.file_attributes is not None
            and value.file_attributes & _WINDOWS_REPARSE_ATTRIBUTE
        )
        or value.reparse_tag not in (None, 0)
    )


def _validate_unique_regular_file(value: _StableFileIdentity) -> None:
    if value.mode_type == stat.S_IFLNK or _is_reparse(value):
        raise SchemaValidationError(
            "artifact file must not be a symbolic link or reparse point"
        )
    if value.mode_type != stat.S_IFREG:
        raise SchemaValidationError("artifact file must be a regular file")
    if value.link_count != 1:
        raise SchemaValidationError(
            "artifact file must be unique and must not have hard-link aliases"
        )


def _same_open_file(
    path_identity: _StableFileIdentity,
    handle_identity: _StableFileIdentity,
) -> bool:
    common_matches = (
        path_identity.device,
        path_identity.inode,
        path_identity.mode_type,
        path_identity.link_count,
        path_identity.byte_count,
        path_identity.mtime_ns,
    ) == (
        handle_identity.device,
        handle_identity.inode,
        handle_identity.mode_type,
        handle_identity.link_count,
        handle_identity.byte_count,
        handle_identity.mtime_ns,
    )
    if not common_matches:
        return False
    if os.name == "nt":
        # CPython exposes different st_ctime_ns meanings for Windows lstat and
        # fstat.  Path observations are compared with path observations and
        # handle observations with handle observations below.
        return (
            path_identity.file_attributes == handle_identity.file_attributes
            and path_identity.reparse_tag == handle_identity.reparse_tag
        )
    return path_identity.ctime_ns == handle_identity.ctime_ns


def _component_identities(
    path: Path,
) -> tuple[tuple[str, _StructuralPathIdentity], ...]:
    parts = path.parts
    if not parts or not path.is_absolute():
        raise SchemaValidationError("artifact file path must be absolute")
    current = Path(parts[0])
    records: list[tuple[str, _StructuralPathIdentity]] = []
    for index, component in enumerate(parts):
        if index:
            current = current / component
        try:
            observed = os.lstat(current)
        except OSError as exc:
            raise SchemaValidationError(
                "artifact file path component is unavailable"
            ) from exc
        identity = _StableFileIdentity.from_stat(observed)
        if identity.mode_type == stat.S_IFLNK or _is_reparse(identity):
            raise SchemaValidationError(
                "artifact file path contains a symbolic link or reparse point"
            )
        is_leaf = index == len(parts) - 1
        if is_leaf:
            _validate_unique_regular_file(identity)
        elif identity.mode_type != stat.S_IFDIR:
            raise SchemaValidationError(
                "artifact file ancestor must be a directory"
            )
        records.append(
            (str(current), _StructuralPathIdentity.from_identity(identity))
        )
    return tuple(records)


def _lstat_regular_file(path: Path) -> _StableFileIdentity:
    try:
        observed = os.lstat(path)
    except OSError as exc:
        raise SchemaValidationError("artifact file is unavailable") from exc
    identity = _StableFileIdentity.from_stat(observed)
    _validate_unique_regular_file(identity)
    return identity


def _open_file_no_follow(path: Path) -> int:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        return os.open(path, flags)
    except OSError as exc:
        raise SchemaValidationError("artifact file could not be opened safely") from exc


def _hash_stable_file(
    path: Path,
    *,
    maximum_byte_count: int | None = None,
    expected_path_identity: _StableFileIdentity | None = None,
    expected_handle_identity: _StableFileIdentity | None = None,
    expected_components: tuple[
        tuple[str, _StructuralPathIdentity],
        ...,
    ]
    | None = None,
) -> tuple[
    str,
    int,
    _StableFileIdentity,
    _StableFileIdentity,
    tuple[tuple[str, _StructuralPathIdentity], ...],
]:
    """Stream one regular file while proving its path and handle stayed stable."""

    components_before = _component_identities(path)
    path_identity_before = _lstat_regular_file(path)
    if (
        maximum_byte_count is not None
        and path_identity_before.byte_count > maximum_byte_count
    ):
        raise SchemaValidationError("artifact file exceeds the capture byte bound")
    if (
        expected_components is not None
        and components_before != expected_components
    ):
        raise SchemaValidationError("artifact file path or ancestor identity changed")
    if (
        expected_path_identity is not None
        and path_identity_before != expected_path_identity
    ):
        raise SchemaValidationError("artifact file identity or metadata changed")

    descriptor = _open_file_no_follow(path)
    try:
        handle_identity_before = _StableFileIdentity.from_stat(os.fstat(descriptor))
        _validate_unique_regular_file(handle_identity_before)
        if not _same_open_file(path_identity_before, handle_identity_before):
            raise SchemaValidationError(
                "artifact file changed between path inspection and open"
            )
        if (
            expected_handle_identity is not None
            and handle_identity_before != expected_handle_identity
        ):
            raise SchemaValidationError("artifact file handle identity changed")

        digest = hashlib.sha256()
        byte_length = 0
        maximum_read = handle_identity_before.byte_count + 1
        while byte_length < maximum_read:
            chunk = os.read(
                descriptor,
                min(_FILE_HASH_CHUNK_SIZE, maximum_read - byte_length),
            )
            if not chunk:
                break
            digest.update(chunk)
            byte_length += len(chunk)
        if byte_length > handle_identity_before.byte_count:
            raise SchemaValidationError(
                "artifact file grew while it was hashed"
            )

        handle_identity_after = _StableFileIdentity.from_stat(os.fstat(descriptor))
        _validate_unique_regular_file(handle_identity_after)
        if handle_identity_after != handle_identity_before:
            raise SchemaValidationError("artifact file changed while it was hashed")
        if byte_length != handle_identity_after.byte_count:
            raise SchemaValidationError(
                "artifact file byte count changed while it was hashed"
            )
    except OSError as exc:
        raise SchemaValidationError("artifact file could not be read safely") from exc
    finally:
        try:
            os.close(descriptor)
        except OSError as exc:
            raise SchemaValidationError(
                "artifact file handle could not be closed safely"
            ) from exc

    components_after = _component_identities(path)
    path_identity_after = _lstat_regular_file(path)
    if components_after != components_before:
        raise SchemaValidationError(
            "artifact file path or ancestor changed while it was hashed"
        )
    if path_identity_after != path_identity_before or not _same_open_file(
        path_identity_after,
        handle_identity_after,
    ):
        raise SchemaValidationError("artifact file path changed while it was hashed")
    if byte_length < 1:
        raise SchemaValidationError("artifact file must not be empty")
    return (
        digest.hexdigest().upper(),
        byte_length,
        path_identity_after,
        handle_identity_after,
        components_after,
    )


def _snapshot_stable_file_bytes(
    path: Path,
    *,
    maximum_byte_count: int,
    expected_path_identity: _StableFileIdentity,
    expected_handle_identity: _StableFileIdentity,
    expected_components: tuple[
        tuple[str, _StructuralPathIdentity],
        ...,
    ],
) -> tuple[bytes, str]:
    """Copy one bounded file from the same handle whose identity is verified."""

    components_before = _component_identities(path)
    path_identity_before = _lstat_regular_file(path)
    if components_before != expected_components:
        raise SchemaValidationError("artifact file path or ancestor identity changed")
    if path_identity_before != expected_path_identity:
        raise SchemaValidationError("artifact file identity or metadata changed")
    if path_identity_before.byte_count > maximum_byte_count:
        raise SchemaValidationError("artifact file exceeds the snapshot byte bound")

    descriptor = _open_file_no_follow(path)
    try:
        handle_identity_before = _StableFileIdentity.from_stat(os.fstat(descriptor))
        _validate_unique_regular_file(handle_identity_before)
        if handle_identity_before != expected_handle_identity:
            raise SchemaValidationError("artifact file handle identity changed")
        if not _same_open_file(path_identity_before, handle_identity_before):
            raise SchemaValidationError(
                "artifact file changed between path inspection and open"
            )

        chunks: list[bytes] = []
        digest = hashlib.sha256()
        byte_length = 0
        maximum_read = min(
            handle_identity_before.byte_count + 1,
            maximum_byte_count + 1,
        )
        while byte_length < maximum_read:
            chunk = os.read(
                descriptor,
                min(_FILE_HASH_CHUNK_SIZE, maximum_read - byte_length),
            )
            if not chunk:
                break
            chunks.append(chunk)
            digest.update(chunk)
            byte_length += len(chunk)
        if byte_length > maximum_byte_count:
            raise SchemaValidationError("artifact file exceeds the snapshot byte bound")
        if byte_length > handle_identity_before.byte_count:
            raise SchemaValidationError("artifact file grew while it was copied")

        handle_identity_after = _StableFileIdentity.from_stat(os.fstat(descriptor))
        _validate_unique_regular_file(handle_identity_after)
        if handle_identity_after != handle_identity_before:
            raise SchemaValidationError("artifact file changed while it was copied")
        if byte_length != handle_identity_after.byte_count:
            raise SchemaValidationError(
                "artifact file byte count changed while it was copied"
            )
    except OSError as exc:
        raise SchemaValidationError("artifact file could not be copied safely") from exc
    finally:
        try:
            os.close(descriptor)
        except OSError as exc:
            raise SchemaValidationError(
                "artifact file handle could not be closed safely"
            ) from exc

    components_after = _component_identities(path)
    path_identity_after = _lstat_regular_file(path)
    if components_after != components_before:
        raise SchemaValidationError(
            "artifact file path or ancestor changed while it was copied"
        )
    if path_identity_after != path_identity_before or not _same_open_file(
        path_identity_after,
        handle_identity_after,
    ):
        raise SchemaValidationError("artifact file path changed while it was copied")
    if byte_length < 1:
        raise SchemaValidationError("artifact file must not be empty")
    return b"".join(chunks), digest.hexdigest().upper()


@dataclass(frozen=True, slots=True)
class EvidenceBytes:
    artifact_id: str
    raw_bytes: bytes
    sha256: str
    byte_length: int

    def __post_init__(self) -> None:
        expect_machine_id(self.artifact_id, "EvidenceBytes.artifact_id")
        if type(self.raw_bytes) is not bytes or not self.raw_bytes:
            raise SchemaValidationError("EvidenceBytes.raw_bytes must be non-empty exact bytes")
        if self.sha256 != sha256_bytes(self.raw_bytes):
            raise SchemaValidationError("EvidenceBytes.sha256 does not match retained bytes")
        if self.byte_length != len(self.raw_bytes):
            raise SchemaValidationError("EvidenceBytes.byte_length does not match retained bytes")


@dataclass(frozen=True, slots=True)
class EvidenceFile:
    """A point-in-time path binding that is streamed and rechecked on every use."""

    artifact_id: str
    path: Path
    sha256: str
    byte_length: int
    _path_identity: _StableFileIdentity
    _handle_identity: _StableFileIdentity
    _component_identities: tuple[
        tuple[str, _StructuralPathIdentity],
        ...,
    ]

    def __post_init__(self) -> None:
        expect_machine_id(self.artifact_id, "EvidenceFile.artifact_id")
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise SchemaValidationError(
                "EvidenceFile.path must be an absolute pathlib path"
            )
        expect_sha256(self.sha256, "EvidenceFile.sha256")
        expect_int(self.byte_length, "EvidenceFile.byte_length", minimum=1)
        if (
            type(self._path_identity) is not _StableFileIdentity
            or type(self._handle_identity) is not _StableFileIdentity
            or type(self._component_identities) is not tuple
        ):
            raise SchemaValidationError(
                "EvidenceFile identity must use the exact internal snapshot type"
            )
        for component in self._component_identities:
            if (
                type(component) is not tuple
                or len(component) != 2
                or type(component[0]) is not str
                or type(component[1]) is not _StructuralPathIdentity
            ):
                raise SchemaValidationError(
                    "EvidenceFile component identity is invalid"
                )
        if (
            self._path_identity.byte_count != self.byte_length
            or self._handle_identity.byte_count != self.byte_length
        ):
            raise SchemaValidationError(
                "EvidenceFile.byte_length does not match its stable identity"
            )

    @classmethod
    def from_path(
        cls,
        artifact_id: str,
        path: object,
        *,
        maximum_byte_count: int | None = None,
    ) -> EvidenceFile:
        """Capture a regular non-link file without materializing it in memory."""

        expect_machine_id(artifact_id, "EvidenceFile.artifact_id")
        if maximum_byte_count is not None:
            expect_int(
                maximum_byte_count,
                "EvidenceFile.from_path.maximum_byte_count",
                minimum=1,
            )
        normalized = _normalize_file_path(path)
        (
            digest,
            byte_length,
            path_identity,
            handle_identity,
            component_identities,
        ) = _hash_stable_file(
            normalized,
            maximum_byte_count=maximum_byte_count,
        )
        return cls(
            artifact_id=artifact_id,
            path=normalized,
            sha256=digest,
            byte_length=byte_length,
            _path_identity=path_identity,
            _handle_identity=handle_identity,
            _component_identities=component_identities,
        )

    def verify_current(self) -> bool:
        """Reopen and stream-verify the same path, identity, metadata, and bytes."""

        try:
            (
                digest,
                byte_length,
                path_identity,
                handle_identity,
                component_identities,
            ) = _hash_stable_file(
                self.path,
                expected_path_identity=self._path_identity,
                expected_handle_identity=self._handle_identity,
                expected_components=self._component_identities,
            )
        except (OSError, SchemaValidationError):
            return False
        return (
            path_identity == self._path_identity
            and handle_identity == self._handle_identity
            and component_identities == self._component_identities
            and digest == self.sha256
            and byte_length == self.byte_length
        )

    def snapshot_bytes(self, *, maximum_byte_count: int) -> EvidenceBytes:
        """Return a bounded detached copy from one identity-checked open handle."""

        expect_int(
            maximum_byte_count,
            "EvidenceFile.snapshot_bytes.maximum_byte_count",
            minimum=1,
        )
        raw_bytes, digest = _snapshot_stable_file_bytes(
            self.path,
            maximum_byte_count=maximum_byte_count,
            expected_path_identity=self._path_identity,
            expected_handle_identity=self._handle_identity,
            expected_components=self._component_identities,
        )
        if digest != self.sha256 or len(raw_bytes) != self.byte_length:
            raise SchemaValidationError(
                "artifact file bytes do not match the captured identity"
            )
        return EvidenceBytes(
            artifact_id=self.artifact_id,
            raw_bytes=raw_bytes,
            sha256=digest,
            byte_length=len(raw_bytes),
        )


class ArtifactByteRegistry:
    """Exact-source integrity evidence, not immutable retention or authentication.

    Byte inputs remain immutable snapshots. File inputs remain externally mutable
    and are therefore identity-checked and streamed again for every verification.
    """

    __slots__ = ("_entries",)

    def __init__(
        self,
        entries: Mapping[
            str,
            bytes | bytearray | memoryview | EvidenceFile,
        ],
    ) -> None:
        if not isinstance(entries, Mapping):
            raise SchemaValidationError("artifact byte registry must be a mapping")
        snapshots: dict[str, EvidenceBytes | EvidenceFile] = {}
        for artifact_id, raw in entries.items():
            expect_machine_id(artifact_id, "artifact_registry key")
            if type(raw) is EvidenceFile:
                if raw.artifact_id != artifact_id:
                    raise SchemaValidationError(
                        f"artifact file source {artifact_id!r} has a different identifier"
                    )
                if not raw.verify_current():
                    raise SchemaValidationError(
                        f"artifact file source {artifact_id!r} changed before registration"
                    )
                snapshots[artifact_id] = raw
                continue
            if type(raw) not in (bytes, bytearray, memoryview):
                raise SchemaValidationError(
                    f"artifact {artifact_id!r} must contain bytes-like data or an exact file source"
                )
            snapshot = bytes(raw)
            if not snapshot:
                raise SchemaValidationError(f"artifact {artifact_id!r} must not be empty")
            snapshots[artifact_id] = EvidenceBytes(
                artifact_id=artifact_id,
                raw_bytes=snapshot,
                sha256=sha256_bytes(snapshot),
                byte_length=len(snapshot),
            )
        self._entries = MappingProxyType(snapshots)

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))

    def verify(self, reference: ArtifactRef) -> bool:
        entry = self._entries.get(reference.artifact_id)
        if type(entry) is EvidenceBytes:
            return (
                type(entry.raw_bytes) is bytes
                and entry.sha256 == sha256_bytes(entry.raw_bytes)
                and entry.byte_length == len(entry.raw_bytes)
                and entry.sha256 == reference.sha256
                and entry.byte_length == reference.byte_length
            )
        if type(entry) is EvidenceFile:
            return (
                entry.sha256 == reference.sha256
                and entry.byte_length == reference.byte_length
                and entry.verify_current()
            )
        return False

    def require(self, reference: ArtifactRef) -> EvidenceBytes | EvidenceFile:
        entry = self._entries.get(reference.artifact_id)
        if entry is None:
            raise SchemaValidationError(
                f"artifact bytes unavailable for {reference.artifact_id!r}"
            )
        if type(entry) is EvidenceBytes:
            retained_source_valid = (
                type(entry.raw_bytes) is bytes
                and entry.sha256 == sha256_bytes(entry.raw_bytes)
                and entry.byte_length == len(entry.raw_bytes)
            )
        elif type(entry) is EvidenceFile:
            retained_source_valid = entry.verify_current()
        else:  # pragma: no cover - MappingProxyType is populated above.
            retained_source_valid = False
        if not (
            retained_source_valid
            and entry.sha256 == reference.sha256
            and entry.byte_length == reference.byte_length
        ):
            raise SchemaValidationError(
                f"artifact bytes do not match the bound identity for {reference.artifact_id!r}"
            )
        return entry
