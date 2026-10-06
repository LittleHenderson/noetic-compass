"""Create-only local retention for STRUCTURE_ONLY Stage C capture artifacts.

This module deliberately provides a narrow, worker-local file archive.  It
holds verified directory objects for each create/load operation, persists exact
capture bytes with handle-relative create-only writes, file ``fsync``,
read-only permission bits, and same-handle plus immediate reopen/reread
verification.  Reload verifies the expected manifest identity, path structure,
file identity, permissions, byte lengths, hashes, and the existing Stage C
semantic replay contract.

The archive is single-host evidence only.  It is not WORM storage, trusted
time, an external anchor, authenticated capture provenance, execution
authority, or a scientific/product result.  It is bound to the same absolute
path and filesystem identities and covers only manifest-listed members; it does
not establish a closed-world directory inventory.  A caller-selected manifest
ref stored beside the archive is not an independent anchor.  The read-only,
reread-verified manifest is the local publication point, so a stop after that
point can leave an internally valid orphan without a returned receipt.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import stat
from types import MappingProxyType
from typing import Any, Mapping

if os.name == "nt":  # pragma: no cover - definitions execute only on Windows
    import ctypes
    import ctypes.wintypes as wintypes
    import msvcrt

from .stagec_capture import (
    AUTHORIZATION_MEDIA_TYPE,
    CAPTURE_INDEX_MEDIA_TYPE,
    REQUEST_MEDIA_TYPE,
    ArtifactIdentity,
    CanonicalJsonArtifact,
    RawArrayArtifact,
    RawArrayArtifactRef,
    StageCCaptureIndex,
    StageCCaptureResult,
    _canonical_json_bytes,
    _strict_json_object,
    replay_stagec_capture_artifacts,
    replay_stagec_capture_result,
)


STAGEC_LOCAL_ARCHIVE_SCHEMA = "cas_harness.stagec.local_capture_archive.v1"
STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-local-capture-archive+json"
)
STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME = "stagec-local-capture-archive.v1.json"
STAGEC_ARCHIVE_MEMBER_ROLES = (
    "request_artifact",
    "authorization_projection_artifact",
    "capture_index_artifact",
    "input_ids",
    "attention_mask",
    "target_vector",
    "wrong_layer_vector",
)

LOCAL_ARCHIVE_AUTHORITY = MappingProxyType(
    {
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
)
SOURCE_RETENTION_BOUNDARY = (
    "CAPTURE-TIME IN_MEMORY / NOT_DURABLY_RETAINED LABELS PRESERVED; "
    "THIS MANIFEST BINDS A SEPARATE LOCAL FILE COPY"
)
ARCHIVE_COPY_STATUS = "LOCAL_FILE_COPY_RETAINED_AND_REVALIDATED"
RELOCATABILITY_BOUNDARY = "SAME_ABSOLUTE_PATH_AND_FILE_IDENTITIES_ONLY"
MANIFEST_MEMBERSHIP_BOUNDARY = (
    "MANIFEST_LISTED_MEMBERS_ONLY / CLOSED_WORLD_DIRECTORY_CONTENT NOT ESTABLISHED"
)
MANIFEST_PUBLICATION_BOUNDARY = (
    "THE READ_ONLY REREAD-VERIFIED MANIFEST IS THE LOCAL PUBLICATION POINT; "
    "A STOP AFTER PUBLICATION MAY LEAVE AN INTERNALLY VALID ORPHAN"
)
DIRECTORY_FSYNC_PERFORMED = "PERFORMED"
DIRECTORY_FSYNC_UNAVAILABLE = "UNAVAILABLE_ON_PLATFORM"
MANIFEST_PARENT_FSYNC_NOT_REPLAYABLE = "NOT_REPLAYABLE_FROM_ARCHIVE_BYTES"

_ASSOCIATION_FIELDS = (
    "study_id",
    "case_id",
    "split_id",
    "base_intent_group_id",
    "frozen_variant",
    "frozen_label",
    "invocation_id",
    "plan_id",
)
_FILE_HASH_CHUNK_SIZE = 1024 * 1024
_WINDOWS_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_WRITE_BITS = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


class StageCArchiveError(RuntimeError):
    """A local archive create or replay precondition was not established."""


class StageCArchiveConflict(StageCArchiveError):
    """The requested create-only archive path already exists or collided."""


@dataclass(frozen=True, slots=True)
class _StructuralIdentity:
    device: int
    inode: int
    mode_type: int
    file_attributes: int | None
    reparse_tag: int | None

    @classmethod
    def from_stat(cls, value: os.stat_result) -> "_StructuralIdentity":
        return cls(
            device=int(value.st_dev),
            inode=int(value.st_ino),
            mode_type=int(stat.S_IFMT(value.st_mode)),
            file_attributes=_optional_stat_int(value, "st_file_attributes"),
            reparse_tag=_optional_stat_int(value, "st_reparse_tag"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "file_attributes": self.file_attributes,
            "inode": self.inode,
            "mode_type": self.mode_type,
            "reparse_tag": self.reparse_tag,
        }

    @classmethod
    def from_payload(cls, value: Any, *, field_name: str) -> "_StructuralIdentity":
        payload = _require_exact_dict(
            value,
            {"device", "file_attributes", "inode", "mode_type", "reparse_tag"},
            field_name=field_name,
        )
        for name in ("device", "inode", "mode_type"):
            _require_exact_int(payload[name], field_name=f"{field_name}.{name}")
        for name in ("file_attributes", "reparse_tag"):
            if payload[name] is not None:
                _require_exact_int(payload[name], field_name=f"{field_name}.{name}")
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class _FileIdentity:
    device: int
    inode: int
    mode_type: int
    link_count: int
    byte_length: int
    mtime_ns: int
    ctime_ns: int
    file_attributes: int | None
    reparse_tag: int | None

    @classmethod
    def from_stat(cls, value: os.stat_result) -> "_FileIdentity":
        return cls(
            device=int(value.st_dev),
            inode=int(value.st_ino),
            mode_type=int(stat.S_IFMT(value.st_mode)),
            link_count=int(value.st_nlink),
            byte_length=int(value.st_size),
            mtime_ns=int(value.st_mtime_ns),
            ctime_ns=int(value.st_ctime_ns),
            file_attributes=_optional_stat_int(value, "st_file_attributes"),
            reparse_tag=_optional_stat_int(value, "st_reparse_tag"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "byte_length": self.byte_length,
            "ctime_ns": self.ctime_ns,
            "device": self.device,
            "file_attributes": self.file_attributes,
            "inode": self.inode,
            "link_count": self.link_count,
            "mode_type": self.mode_type,
            "mtime_ns": self.mtime_ns,
            "permission_status": "READ_ONLY_PERMISSION_BITS_OBSERVED",
            "reparse_tag": self.reparse_tag,
        }

    @classmethod
    def from_payload(cls, value: Any, *, field_name: str) -> "_FileIdentity":
        payload = _require_exact_dict(
            value,
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
            },
            field_name=field_name,
        )
        if payload["permission_status"] != "READ_ONLY_PERMISSION_BITS_OBSERVED":
            raise StageCArchiveError(f"{field_name} overclaims or weakens permission status")
        values = dict(payload)
        values.pop("permission_status")
        for name in (
            "byte_length",
            "ctime_ns",
            "device",
            "inode",
            "link_count",
            "mode_type",
            "mtime_ns",
        ):
            _require_exact_int(values[name], field_name=f"{field_name}.{name}")
        for name in ("file_attributes", "reparse_tag"):
            if values[name] is not None:
                _require_exact_int(values[name], field_name=f"{field_name}.{name}")
        return cls(**values)


@dataclass(frozen=True, slots=True)
class _AncestorIdentity:
    relative_path: str
    identity: _StructuralIdentity

    def to_payload(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_payload(),
            "relative_path": self.relative_path,
        }

    @classmethod
    def from_payload(cls, value: Any, *, field_name: str) -> "_AncestorIdentity":
        payload = _require_exact_dict(
            value, {"identity", "relative_path"}, field_name=field_name
        )
        relative = _require_relative_path_text(
            payload["relative_path"], field_name=f"{field_name}.relative_path",
            allow_root=True,
        )
        return cls(
            relative_path=relative,
            identity=_StructuralIdentity.from_payload(
                payload["identity"], field_name=f"{field_name}.identity"
            ),
        )


@dataclass(frozen=True, slots=True, init=False)
class StageCLocalArchiveReceipt:
    """Factory-created local receipt; it is not an external or WORM anchor."""

    root: Path
    manifest_path: Path
    manifest_ref: ArtifactIdentity
    association: Mapping[str, str]
    manifest_parent_directory_fsync_status: str
    authority: Mapping[str, str]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StageCArchiveError(
            "archive receipt construction requires the retention factory"
        )

    def _validate(self) -> None:
        if not isinstance(self.root, Path) or not self.root.is_absolute():
            raise StageCArchiveError("archive receipt root must be an absolute path")
        if self.manifest_path != self.root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME:
            raise StageCArchiveError("archive receipt manifest path drifted")
        if type(self.manifest_ref) is not ArtifactIdentity:
            raise StageCArchiveError("archive receipt manifest ref has the wrong exact type")
        if self.manifest_ref.media_type != STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE:
            raise StageCArchiveError("archive receipt manifest media type drifted")
        if set(self.association) != set(_ASSOCIATION_FIELDS):
            raise StageCArchiveError("archive receipt association keys drifted")
        for name in _ASSOCIATION_FIELDS:
            _require_text(
                self.association[name], field_name=f"archive_receipt.association.{name}"
            )
        if self.manifest_parent_directory_fsync_status not in {
            DIRECTORY_FSYNC_PERFORMED,
            DIRECTORY_FSYNC_UNAVAILABLE,
        }:
            raise StageCArchiveError("archive receipt directory-fsync status is invalid")
        if dict(self.authority) != dict(LOCAL_ARCHIVE_AUTHORITY):
            raise StageCArchiveError("archive receipt authority boundary drifted")

    def to_payload(self) -> dict[str, Any]:
        return {
            "association": dict(self.association),
            "authority": dict(self.authority),
            "manifest_parent_directory_fsync_status": (
                self.manifest_parent_directory_fsync_status
            ),
            "manifest_ref": self.manifest_ref.to_payload(),
            "root": str(self.root),
        }


@dataclass(frozen=True, slots=True, init=False)
class StageCArchivedCapture:
    """Revalidated archive view; successful replay confers no capture provenance."""

    root: Path
    manifest_artifact: CanonicalJsonArtifact
    index_artifact: CanonicalJsonArtifact
    request_artifact: CanonicalJsonArtifact
    authorization_projection_artifact: CanonicalJsonArtifact
    input_ids: RawArrayArtifact
    attention_mask: RawArrayArtifact
    target_vector: RawArrayArtifact
    wrong_layer_vector: RawArrayArtifact
    index: StageCCaptureIndex
    member_paths: Mapping[str, Path]
    authority: Mapping[str, str]
    manifest_parent_directory_fsync_status: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StageCArchiveError(
            "loaded archive construction requires the strict loader"
        )

    def _validate(self) -> None:
        if not isinstance(self.root, Path) or not self.root.is_absolute():
            raise StageCArchiveError("loaded archive root must be an absolute Path")
        if type(self.manifest_artifact) is not CanonicalJsonArtifact:
            raise StageCArchiveError("loaded archive manifest has the wrong exact type")
        if self.manifest_artifact.ref.media_type != STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE:
            raise StageCArchiveError("loaded archive manifest media type drifted")
        artifacts: tuple[
            tuple[str, CanonicalJsonArtifact | RawArrayArtifact, type[Any]], ...
        ] = (
            ("request_artifact", self.request_artifact, CanonicalJsonArtifact),
            (
                "authorization_projection_artifact",
                self.authorization_projection_artifact,
                CanonicalJsonArtifact,
            ),
            ("capture_index_artifact", self.index_artifact, CanonicalJsonArtifact),
            ("input_ids", self.input_ids, RawArrayArtifact),
            ("attention_mask", self.attention_mask, RawArrayArtifact),
            ("target_vector", self.target_vector, RawArrayArtifact),
            ("wrong_layer_vector", self.wrong_layer_vector, RawArrayArtifact),
        )
        if type(self.index) is not StageCCaptureIndex:
            raise StageCArchiveError("loaded archive decoded index has the wrong exact type")
        if set(self.member_paths) != set(STAGEC_ARCHIVE_MEMBER_ROLES):
            raise StageCArchiveError("loaded archive member-path roles drifted")
        for role, artifact, expected_type in artifacts:
            if type(artifact) is not expected_type:
                raise StageCArchiveError(
                    f"loaded archive {role} has the wrong exact type"
                )
            path = self.member_paths[role]
            if not isinstance(path, Path) or not path.is_absolute():
                raise StageCArchiveError(
                    f"loaded archive {role} path has the wrong exact type"
                )
            expected_path = self.root.joinpath(
                *Path(_content_relative_path(artifact.ref.sha256)).parts
            )
            if path != expected_path:
                raise StageCArchiveError(f"loaded archive {role} path drifted")
        replayed = replay_stagec_capture_artifacts(
            index_artifact=self.index_artifact,
            request_artifact=self.request_artifact,
            authorization_projection_artifact=self.authorization_projection_artifact,
            input_ids=self.input_ids,
            attention_mask=self.attention_mask,
            target_vector=self.target_vector,
            wrong_layer_vector=self.wrong_layer_vector,
        )
        if replayed.to_payload() != self.index.to_payload():
            raise StageCArchiveError("loaded archive decoded index replay drifted")
        if dict(self.authority) != dict(LOCAL_ARCHIVE_AUTHORITY):
            raise StageCArchiveError("loaded archive authority boundary drifted")
        if self.manifest_parent_directory_fsync_status != MANIFEST_PARENT_FSYNC_NOT_REPLAYABLE:
            raise StageCArchiveError("loaded archive invented a historical directory-fsync claim")


def _new_local_archive_receipt(
    *,
    loaded_archive: StageCArchivedCapture,
    manifest_parent_directory_fsync_status: str,
) -> StageCLocalArchiveReceipt:
    if type(loaded_archive) is not StageCArchivedCapture:
        raise StageCArchiveError(
            "archive receipt factory requires one strict loaded archive"
        )
    loaded_archive._validate()
    root = loaded_archive.root
    manifest_ref = loaded_archive.manifest_artifact.ref
    association = {
        name: loaded_archive.index.association[name] for name in _ASSOCIATION_FIELDS
    }
    receipt = object.__new__(StageCLocalArchiveReceipt)
    object.__setattr__(receipt, "root", root)
    object.__setattr__(
        receipt,
        "manifest_path",
        root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME,
    )
    object.__setattr__(receipt, "manifest_ref", manifest_ref)
    object.__setattr__(
        receipt,
        "association",
        MappingProxyType(dict(association)),
    )
    object.__setattr__(
        receipt,
        "manifest_parent_directory_fsync_status",
        manifest_parent_directory_fsync_status,
    )
    object.__setattr__(receipt, "authority", LOCAL_ARCHIVE_AUTHORITY)
    receipt._validate()
    return receipt


def _new_archived_capture(
    *,
    root: Path,
    manifest_artifact: CanonicalJsonArtifact,
    index_artifact: CanonicalJsonArtifact,
    request_artifact: CanonicalJsonArtifact,
    authorization_projection_artifact: CanonicalJsonArtifact,
    input_ids: RawArrayArtifact,
    attention_mask: RawArrayArtifact,
    target_vector: RawArrayArtifact,
    wrong_layer_vector: RawArrayArtifact,
    index: StageCCaptureIndex,
    member_paths: Mapping[str, Path],
) -> StageCArchivedCapture:
    if not isinstance(member_paths, Mapping):
        raise StageCArchiveError("loaded archive member paths must be a mapping")
    loaded = object.__new__(StageCArchivedCapture)
    for name, value in (
        ("root", root),
        ("manifest_artifact", manifest_artifact),
        ("index_artifact", index_artifact),
        ("request_artifact", request_artifact),
        ("authorization_projection_artifact", authorization_projection_artifact),
        ("input_ids", input_ids),
        ("attention_mask", attention_mask),
        ("target_vector", target_vector),
        ("wrong_layer_vector", wrong_layer_vector),
        ("index", index),
        ("member_paths", MappingProxyType(dict(member_paths))),
        ("authority", LOCAL_ARCHIVE_AUTHORITY),
        (
            "manifest_parent_directory_fsync_status",
            MANIFEST_PARENT_FSYNC_NOT_REPLAYABLE,
        ),
    ):
        object.__setattr__(loaded, name, value)
    loaded._validate()
    return loaded


def _optional_stat_int(value: os.stat_result, name: str) -> int | None:
    observed = getattr(value, name, None)
    return None if observed is None else int(observed)


def _is_reparse(value: _StructuralIdentity | _FileIdentity) -> bool:
    return bool(
        (
            value.file_attributes is not None
            and value.file_attributes & _WINDOWS_REPARSE_ATTRIBUTE
        )
        or value.reparse_tag not in (None, 0)
    )


if os.name == "nt":  # pragma: no cover - exercised by the Windows test job
    _WIN_FILE_READ_ATTRIBUTES = 0x0080
    _WIN_FILE_SHARE_READ = 0x00000001
    _WIN_FILE_SHARE_WRITE = 0x00000002
    _WIN_OPEN_EXISTING = 3
    _WIN_FILE_ATTRIBUTE_READONLY = 0x00000001
    _WIN_FILE_ATTRIBUTE_NORMAL = 0x00000080
    _WIN_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _WIN_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _WIN_FILE_BASIC_INFO_CLASS = 0
    _WIN_INVALID_HANDLE = ctypes.c_void_p(-1).value
    _WIN_OBJ_CASE_INSENSITIVE = 0x00000040
    _WIN_SYNCHRONIZE = 0x00100000
    _WIN_FILE_GENERIC_READ = 0x00120089
    _WIN_FILE_GENERIC_WRITE = 0x00120116
    _WIN_FILE_CREATE = 2
    _WIN_FILE_OPEN = 1
    _WIN_FILE_DIRECTORY_FILE = 0x00000001
    _WIN_FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
    _WIN_FILE_NON_DIRECTORY_FILE = 0x00000040
    _WIN_FILE_OPEN_REPARSE_POINT = 0x00200000

    class _WindowsFileBasicInfo(ctypes.Structure):
        _fields_ = (
            ("CreationTime", ctypes.c_longlong),
            ("LastAccessTime", ctypes.c_longlong),
            ("LastWriteTime", ctypes.c_longlong),
            ("ChangeTime", ctypes.c_longlong),
            ("FileAttributes", wintypes.DWORD),
        )

    class _WindowsUnicodeString(ctypes.Structure):
        _fields_ = (
            ("Length", wintypes.USHORT),
            ("MaximumLength", wintypes.USHORT),
            ("Buffer", wintypes.LPWSTR),
        )

    class _WindowsObjectAttributes(ctypes.Structure):
        _fields_ = (
            ("Length", wintypes.ULONG),
            ("RootDirectory", wintypes.HANDLE),
            ("ObjectName", ctypes.POINTER(_WindowsUnicodeString)),
            ("Attributes", wintypes.ULONG),
            ("SecurityDescriptor", wintypes.LPVOID),
            ("SecurityQualityOfService", wintypes.LPVOID),
        )

    class _WindowsIoStatusBlock(ctypes.Structure):
        _fields_ = (
            ("StatusOrPointer", ctypes.c_void_p),
            ("Information", ctypes.c_size_t),
        )

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    _KERNEL32.CreateFileW.restype = wintypes.HANDLE
    _KERNEL32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _KERNEL32.CloseHandle.restype = wintypes.BOOL
    _KERNEL32.FlushFileBuffers.argtypes = (wintypes.HANDLE,)
    _KERNEL32.FlushFileBuffers.restype = wintypes.BOOL
    _KERNEL32.GetFileInformationByHandleEx.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    _KERNEL32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _KERNEL32.SetFileInformationByHandle.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    _KERNEL32.SetFileInformationByHandle.restype = wintypes.BOOL
    _NTDLL = ctypes.WinDLL("ntdll", use_last_error=True)
    _NTDLL.NtCreateFile.argtypes = (
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        ctypes.POINTER(_WindowsObjectAttributes),
        ctypes.POINTER(_WindowsIoStatusBlock),
        ctypes.c_void_p,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        ctypes.c_void_p,
        wintypes.ULONG,
    )
    _NTDLL.NtCreateFile.restype = ctypes.c_long
    _NTDLL.RtlNtStatusToDosError.argtypes = (ctypes.c_long,)
    _NTDLL.RtlNtStatusToDosError.restype = wintypes.ULONG


def _windows_extended_path(path: Path) -> str:
    text = str(path)
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text[2:]
    return "\\\\?\\" + text


def _windows_anchor_directory_descriptor(path: Path) -> int:
    """Open one absolute Windows anchor directory without reparse traversal."""

    if os.name != "nt":  # pragma: no cover - platform guard
        raise StageCArchiveError("Windows anchor helper used off Windows")
    handle = _KERNEL32.CreateFileW(
        _windows_extended_path(path),
        _WIN_FILE_READ_ATTRIBUTES,
        _WIN_FILE_SHARE_READ | _WIN_FILE_SHARE_WRITE,
        None,
        _WIN_OPEN_EXISTING,
        _WIN_FILE_FLAG_BACKUP_SEMANTICS | _WIN_FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _WIN_INVALID_HANDLE:
        error = ctypes.get_last_error()
        raise OSError(error, "Windows archive anchor open failed", str(path))
    try:
        return msvcrt.open_osfhandle(
            int(handle),
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOINHERIT", 0),
        )
    except Exception:
        _KERNEL32.CloseHandle(handle)
        raise


def _windows_relative_descriptor(
    parent_descriptor: int,
    name: str,
    *,
    directory: bool,
    create: bool,
) -> int:
    """Open or create one child relative to an already-held Windows directory."""

    if os.name != "nt":  # pragma: no cover - platform guard
        raise StageCArchiveError("Windows relative descriptor helper used off Windows")
    if (
        type(name) is not str
        or not name
        or name in {".", ".."}
        or "\\" in name
        or "/" in name
        or "\x00" in name
    ):
        raise StageCArchiveError("Windows archive child name must be one component")
    parent_handle = wintypes.HANDLE(msvcrt.get_osfhandle(parent_descriptor))
    name_buffer = ctypes.create_unicode_buffer(name)
    encoded_name_length = len(name.encode("utf-16-le"))
    name_value = _WindowsUnicodeString(
        Length=encoded_name_length,
        MaximumLength=encoded_name_length + 2,
        Buffer=ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    attributes = _WindowsObjectAttributes(
        Length=ctypes.sizeof(_WindowsObjectAttributes),
        RootDirectory=parent_handle,
        ObjectName=ctypes.pointer(name_value),
        Attributes=_WIN_OBJ_CASE_INSENSITIVE,
        SecurityDescriptor=None,
        SecurityQualityOfService=None,
    )
    io_status = _WindowsIoStatusBlock()
    output_handle = wintypes.HANDLE()
    if directory:
        desired_access = _WIN_FILE_READ_ATTRIBUTES | _WIN_SYNCHRONIZE
        create_options = (
            _WIN_FILE_DIRECTORY_FILE
            | _WIN_FILE_OPEN_REPARSE_POINT
            | _WIN_FILE_SYNCHRONOUS_IO_NONALERT
        )
        file_attributes = 0
        descriptor_flags = os.O_RDONLY
    elif create:
        desired_access = _WIN_FILE_GENERIC_READ | _WIN_FILE_GENERIC_WRITE
        create_options = (
            _WIN_FILE_NON_DIRECTORY_FILE
            | _WIN_FILE_OPEN_REPARSE_POINT
            | _WIN_FILE_SYNCHRONOUS_IO_NONALERT
        )
        file_attributes = _WIN_FILE_ATTRIBUTE_NORMAL
        descriptor_flags = os.O_RDWR
    else:
        desired_access = _WIN_FILE_GENERIC_READ
        create_options = (
            _WIN_FILE_NON_DIRECTORY_FILE
            | _WIN_FILE_OPEN_REPARSE_POINT
            | _WIN_FILE_SYNCHRONOUS_IO_NONALERT
        )
        file_attributes = 0
        descriptor_flags = os.O_RDONLY
    status = _NTDLL.NtCreateFile(
        ctypes.byref(output_handle),
        desired_access,
        ctypes.byref(attributes),
        ctypes.byref(io_status),
        None,
        file_attributes,
        (_WIN_FILE_SHARE_READ | _WIN_FILE_SHARE_WRITE) if directory else (
            0 if create else _WIN_FILE_SHARE_READ
        ),
        _WIN_FILE_CREATE if create else _WIN_FILE_OPEN,
        create_options,
        None,
        0,
    )
    if status < 0:
        error = int(_NTDLL.RtlNtStatusToDosError(status))
        if create and error in {80, 183}:
            raise FileExistsError(error, "create-only archive child exists", name)
        raise OSError(error, "Windows relative archive object open failed", name)
    try:
        return msvcrt.open_osfhandle(
            int(output_handle.value),
            descriptor_flags
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOINHERIT", 0),
        )
    except Exception:
        _KERNEL32.CloseHandle(output_handle)
        raise


def _set_descriptor_read_only(descriptor: int) -> None:
    if os.name != "nt":
        try:
            os.fchmod(descriptor, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        except OSError as exc:
            raise StageCArchiveError(
                "archive member could not be made read-only"
            ) from exc
        return
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
    info = _WindowsFileBasicInfo()
    if not _KERNEL32.GetFileInformationByHandleEx(
        handle,
        _WIN_FILE_BASIC_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        error = ctypes.get_last_error()
        raise StageCArchiveError(
            f"archive member read-only metadata query failed with Windows error {error}"
        )
    info.FileAttributes = (
        int(info.FileAttributes) & ~_WIN_FILE_ATTRIBUTE_NORMAL
    ) | _WIN_FILE_ATTRIBUTE_READONLY
    if not _KERNEL32.SetFileInformationByHandle(
        handle,
        _WIN_FILE_BASIC_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        error = ctypes.get_last_error()
        raise StageCArchiveError(
            f"archive member could not be made read-only; Windows error {error}"
        )


@dataclass(frozen=True, slots=True)
class _HeldDirectory:
    path: Path
    descriptor: int
    identity: _StructuralIdentity


class _ArchiveDirectorySession:
    """Hold directory objects so every operation stays bound to those objects."""

    def __init__(self, existing_path: Path) -> None:
        if not existing_path.is_absolute():
            raise StageCArchiveError("held archive directory path must be absolute")
        if os.name != "nt":
            required_dir_fd = (os.open, os.stat, os.mkdir)
            if (
                not hasattr(os, "O_DIRECTORY")
                or not hasattr(os, "O_NOFOLLOW")
                or any(item not in os.supports_dir_fd for item in required_dir_fd)
            ):
                raise StageCArchiveError(
                    "platform lacks required handle-relative directory operations"
                )
        self._held: dict[Path, _HeldDirectory] = {}
        self._order: list[Path] = []
        self.hold_existing_chain(existing_path)

    def __enter__(self) -> "_ArchiveDirectorySession":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        close_error: OSError | None = None
        for path in reversed(self._order):
            try:
                os.close(self._held[path].descriptor)
            except OSError as observed:
                close_error = close_error or observed
        self._held.clear()
        self._order.clear()
        if close_error is not None and exc_type is None:
            raise StageCArchiveError("held archive directory could not be closed") from close_error
        return False

    def _parent_and_name(self, path: Path) -> tuple[_HeldDirectory | None, str]:
        if path.parent == path:
            return None, str(path)
        parent = self._held.get(path.parent)
        if parent is None:
            raise StageCArchiveError("archive directory parent is not held")
        return parent, path.name

    def _entry_stat(self, path: Path) -> os.stat_result:
        parent, name = self._parent_and_name(path)
        try:
            if os.name != "nt" and parent is not None:
                return os.stat(
                    name,
                    dir_fd=parent.descriptor,
                    follow_symlinks=False,
                )
            if os.name == "nt" and parent is not None:
                descriptor = _windows_relative_descriptor(
                    parent.descriptor,
                    name,
                    directory=True,
                    create=False,
                )
                try:
                    return os.fstat(descriptor)
                finally:
                    os.close(descriptor)
            return os.lstat(path)
        except OSError as exc:
            raise StageCArchiveError("held archive directory name is unavailable") from exc

    def _open_directory(self, path: Path) -> int:
        parent, name = self._parent_and_name(path)
        if os.name == "nt":
            if parent is not None:
                return _windows_relative_descriptor(
                    parent.descriptor,
                    name,
                    directory=True,
                    create=False,
                )
            return _windows_anchor_directory_descriptor(path)
        flags = (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            if parent is None:
                return os.open(path, flags)
            return os.open(name, flags, dir_fd=parent.descriptor)
        except OSError as exc:
            raise StageCArchiveError("archive directory could not be held safely") from exc

    def hold_directory(self, path: Path) -> _HeldDirectory:
        existing = self._held.get(path)
        if existing is not None:
            self.assert_directory(path)
            return existing
        descriptor = self._open_directory(path)
        return self._record_directory(path, descriptor)

    def _record_directory(self, path: Path, descriptor: int) -> _HeldDirectory:
        try:
            handle_identity = _StructuralIdentity.from_stat(os.fstat(descriptor))
            path_identity = _StructuralIdentity.from_stat(self._entry_stat(path))
            if handle_identity != path_identity:
                raise StageCArchiveError(
                    "archive directory changed between name lookup and handle acquisition"
                )
            if handle_identity.mode_type != stat.S_IFDIR or _is_reparse(handle_identity):
                raise StageCArchiveError(
                    "archive directory must be a non-reparse directory"
                )
        except Exception:
            os.close(descriptor)
            raise
        held = _HeldDirectory(path=path, descriptor=descriptor, identity=handle_identity)
        self._held[path] = held
        self._order.append(path)
        return held

    def hold_existing_chain(self, path: Path) -> None:
        parts = path.parts
        if not parts or not path.is_absolute():
            raise StageCArchiveError("archive path must be absolute")
        current = Path(parts[0])
        self.hold_directory(current)
        for part in parts[1:]:
            current = current / part
            self.hold_directory(current)

    def assert_directory(self, path: Path) -> _HeldDirectory:
        held = self._held.get(path)
        if held is None:
            raise StageCArchiveError("archive directory identity is not held")
        handle_identity = _StructuralIdentity.from_stat(os.fstat(held.descriptor))
        path_identity = _StructuralIdentity.from_stat(self._entry_stat(path))
        if handle_identity != held.identity or path_identity != held.identity:
            raise StageCArchiveError("held archive directory identity drifted")
        if handle_identity.mode_type != stat.S_IFDIR or _is_reparse(handle_identity):
            raise StageCArchiveError("held archive directory became invalid")
        return held

    def assert_all(self) -> None:
        for path in self._order:
            self.assert_directory(path)

    def descriptor_for(self, path: Path) -> int:
        return self.assert_directory(path).descriptor

    def create_directory(self, path: Path) -> None:
        parent = self.assert_directory(path.parent)
        if os.name == "nt":
            try:
                descriptor = _windows_relative_descriptor(
                    parent.descriptor,
                    path.name,
                    directory=True,
                    create=True,
                )
            except FileExistsError as exc:
                raise StageCArchiveConflict(
                    f"create-only archive directory exists: {path}"
                ) from exc
            except OSError as exc:
                raise StageCArchiveError(
                    f"archive directory could not be created: {path}"
                ) from exc
            self._record_directory(path, descriptor)
            return
        try:
            os.mkdir(path.name, 0o700, dir_fd=parent.descriptor)
        except FileExistsError as exc:
            raise StageCArchiveConflict(
                f"create-only archive directory exists: {path}"
            ) from exc
        except OSError as exc:
            raise StageCArchiveError(
                f"archive directory could not be created: {path}"
            ) from exc
        self.hold_directory(path)

    def member_lstat(self, path: Path) -> os.stat_result:
        parent = self.assert_directory(path.parent)
        try:
            if os.name != "nt":
                return os.stat(
                    path.name,
                    dir_fd=parent.descriptor,
                    follow_symlinks=False,
                )
            descriptor = _windows_relative_descriptor(
                parent.descriptor,
                path.name,
                directory=False,
                create=False,
            )
            try:
                return os.fstat(descriptor)
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise StageCArchiveError("archive member is unavailable") from exc

    def open_member(self, path: Path, *, write: bool) -> int:
        parent = self.assert_directory(path.parent)
        if os.name == "nt":
            return _windows_relative_descriptor(
                parent.descriptor,
                path.name,
                directory=False,
                create=write,
            )
        flags = _open_flags(write=write)
        try:
            return os.open(
                path.name,
                flags,
                0o600,
                dir_fd=parent.descriptor,
            )
        except TypeError:  # pragma: no cover - read mode omits mode on some runtimes
            return os.open(path.name, flags, dir_fd=parent.descriptor)

    def fsync_directory(self, path: Path) -> str:
        descriptor = self.descriptor_for(path)
        try:
            if os.name == "nt":
                handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
                if not _KERNEL32.FlushFileBuffers(handle):
                    return DIRECTORY_FSYNC_UNAVAILABLE
            else:
                os.fsync(descriptor)
        except OSError:
            return DIRECTORY_FSYNC_UNAVAILABLE
        return DIRECTORY_FSYNC_PERFORMED


def _require_exact_dict(
    value: Any, expected: set[str], *, field_name: str
) -> dict[str, Any]:
    if type(value) is not dict:
        raise StageCArchiveError(f"{field_name} must be an exact JSON object")
    actual = set(value)
    if actual != expected:
        raise StageCArchiveError(
            f"{field_name} keys drifted; missing={sorted(expected - actual)!r}, "
            f"extra={sorted(actual - expected)!r}"
        )
    return value


def _require_exact_int(value: Any, *, field_name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise StageCArchiveError(
            f"{field_name} must be an exact integer >= {minimum}"
        )
    return value


def _require_text(value: Any, *, field_name: str) -> str:
    if type(value) is not str or not value or value != value.strip() or "\x00" in value:
        raise StageCArchiveError(f"{field_name} must be non-empty exact text")
    return value


def _require_relative_path_text(
    value: Any, *, field_name: str, allow_root: bool = False
) -> str:
    text = _require_text(value, field_name=field_name)
    if allow_root and text == ".":
        return text
    candidate = Path(text)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.as_posix() != text
    ):
        raise StageCArchiveError(f"{field_name} is not a safe canonical relative path")
    return text


def _normalize_path(value: object) -> Path:
    if isinstance(value, bytes):
        raise StageCArchiveError("archive root must be text, not bytes")
    try:
        raw = os.fspath(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise StageCArchiveError("archive root must be path-like") from exc
    if type(raw) is not str or not raw or "\x00" in raw:
        raise StageCArchiveError("archive root must be non-empty path text")
    path = Path(os.path.abspath(raw))
    if path.parent == path:
        raise StageCArchiveError("archive root must not be a filesystem root")
    return path


def _require_safe_existing_root(
    root: Path,
    *,
    session: _ArchiveDirectorySession,
) -> _StructuralIdentity:
    identity = session.assert_directory(root).identity
    if identity.mode_type != stat.S_IFDIR or _is_reparse(identity):
        raise StageCArchiveError("archive root must be a non-reparse directory")
    return identity


def _ancestor_identities(
    root: Path,
    parent: Path,
    *,
    session: _ArchiveDirectorySession,
) -> tuple[_AncestorIdentity, ...]:
    try:
        relative = parent.relative_to(root)
    except ValueError as exc:
        raise StageCArchiveError("archive member parent escapes archive root") from exc
    rows: list[_AncestorIdentity] = []
    current = root
    parts = () if relative == Path(".") else relative.parts
    for index in range(len(parts) + 1):
        relative_name = "." if index == 0 else Path(*parts[:index]).as_posix()
        if index:
            current = root.joinpath(*parts[:index])
        identity = session.hold_directory(current).identity
        if identity.mode_type != stat.S_IFDIR or _is_reparse(identity):
            raise StageCArchiveError(
                "archive member path contains a symbolic link or reparse point"
            )
        rows.append(_AncestorIdentity(relative_name, identity))
    return tuple(rows)


def _validate_regular_read_only_file(identity: _FileIdentity, mode: int) -> None:
    if identity.mode_type == stat.S_IFLNK or _is_reparse(identity):
        raise StageCArchiveError("archive member is a symbolic link or reparse point")
    if identity.mode_type != stat.S_IFREG:
        raise StageCArchiveError("archive member must be a regular file")
    if identity.link_count != 1:
        raise StageCArchiveError(
            "archive member must be unique and have no hard-link aliases"
        )
    if mode & _WRITE_BITS:
        raise StageCArchiveError("archive member read-only permission drifted")


def _same_open_file(path_identity: _FileIdentity, handle_identity: _FileIdentity) -> bool:
    common = (
        path_identity.device,
        path_identity.inode,
        path_identity.mode_type,
        path_identity.link_count,
        path_identity.byte_length,
        path_identity.mtime_ns,
        path_identity.file_attributes,
        path_identity.reparse_tag,
    ) == (
        handle_identity.device,
        handle_identity.inode,
        handle_identity.mode_type,
        handle_identity.link_count,
        handle_identity.byte_length,
        handle_identity.mtime_ns,
        handle_identity.file_attributes,
        handle_identity.reparse_tag,
    )
    return common and (os.name == "nt" or path_identity.ctime_ns == handle_identity.ctime_ns)


def _safe_member_path(root: Path, relative_path: str) -> Path:
    canonical = _require_relative_path_text(
        relative_path, field_name="archive member relative_path"
    )
    target = root.joinpath(*Path(canonical).parts)
    try:
        target.relative_to(root)
    except ValueError as exc:  # pragma: no cover - guarded by relative validation
        raise StageCArchiveError("archive member path escapes archive root") from exc
    return target


def _open_flags(*, write: bool) -> int:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL if write else os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return flags


def _read_exact_file(
    *,
    root: Path,
    session: _ArchiveDirectorySession,
    relative_path: str,
    expected_sha256: str,
    expected_byte_length: int,
    expected_identity: _FileIdentity | None,
    expected_ancestors: tuple[_AncestorIdentity, ...] | None,
) -> tuple[bytes, _FileIdentity, tuple[_AncestorIdentity, ...]]:
    target = _safe_member_path(root, relative_path)
    ancestors_before = _ancestor_identities(
        root,
        target.parent,
        session=session,
    )
    if expected_ancestors is not None and ancestors_before != expected_ancestors:
        raise StageCArchiveError("archive member ancestor path identity drifted")
    path_stat_before = session.member_lstat(target)
    path_identity_before = _FileIdentity.from_stat(path_stat_before)
    _validate_regular_read_only_file(path_identity_before, path_stat_before.st_mode)
    if expected_identity is not None and path_identity_before != expected_identity:
        raise StageCArchiveError("archive member file identity or metadata drifted")

    try:
        descriptor = session.open_member(target, write=False)
    except OSError as exc:
        raise StageCArchiveError("archive member could not be opened safely") from exc
    try:
        handle_stat_before = os.fstat(descriptor)
        handle_identity_before = _FileIdentity.from_stat(handle_stat_before)
        _validate_regular_read_only_file(handle_identity_before, handle_stat_before.st_mode)
        if not _same_open_file(path_identity_before, handle_identity_before):
            raise StageCArchiveError(
                "archive member changed between path inspection and open"
            )
        chunks: list[bytes] = []
        byte_length = 0
        maximum = expected_byte_length + 1
        while byte_length < maximum:
            try:
                chunk = os.read(
                    descriptor,
                    min(_FILE_HASH_CHUNK_SIZE, maximum - byte_length),
                )
            except OSError as exc:
                raise StageCArchiveError("archive member could not be read safely") from exc
            if not chunk:
                break
            chunks.append(chunk)
            byte_length += len(chunk)
        handle_stat_after = os.fstat(descriptor)
        handle_identity_after = _FileIdentity.from_stat(handle_stat_after)
        if handle_identity_after != handle_identity_before:
            raise StageCArchiveError("archive member changed while it was read")
    finally:
        try:
            os.close(descriptor)
        except OSError as exc:
            raise StageCArchiveError("archive member handle could not be closed") from exc

    path_stat_after = session.member_lstat(target)
    path_identity_after = _FileIdentity.from_stat(path_stat_after)
    ancestors_after = _ancestor_identities(
        root,
        target.parent,
        session=session,
    )
    if (
        path_identity_after != path_identity_before
        or ancestors_after != ancestors_before
        or not _same_open_file(path_identity_after, handle_identity_after)
    ):
        raise StageCArchiveError("archive member path or identity changed during read")
    raw = b"".join(chunks)
    if len(raw) != expected_byte_length:
        raise StageCArchiveError("archive member byte length drifted")
    if sha256(raw).hexdigest().upper() != expected_sha256:
        raise StageCArchiveError("archive member SHA-256 drifted")
    return raw, path_identity_after, ancestors_after


def _fsync_directory(
    path: Path,
    *,
    session: _ArchiveDirectorySession,
) -> str:
    return session.fsync_directory(path)


def _write_create_only_file(
    *,
    root: Path,
    session: _ArchiveDirectorySession,
    relative_path: str,
    raw_bytes: bytes,
) -> tuple[_FileIdentity, tuple[_AncestorIdentity, ...], str]:
    if type(raw_bytes) is not bytes or not raw_bytes:
        raise StageCArchiveError("archive member body must be non-empty immutable bytes")
    target = _safe_member_path(root, relative_path)
    ancestors = _ancestor_identities(
        root,
        target.parent,
        session=session,
    )
    try:
        descriptor = session.open_member(target, write=True)
    except FileExistsError as exc:
        raise StageCArchiveConflict(
            f"create-only archive member already exists: {relative_path}"
        ) from exc
    except OSError as exc:
        raise StageCArchiveError("archive member create-only open failed") from exc
    try:
        initial_stat = os.fstat(descriptor)
        initial_identity = _FileIdentity.from_stat(initial_stat)
        if (
            initial_identity.mode_type != stat.S_IFREG
            or _is_reparse(initial_identity)
            or initial_identity.link_count != 1
        ):
            raise StageCArchiveError("created archive member is not one unique regular file")
        written = 0
        while written < len(raw_bytes):
            try:
                count = os.write(descriptor, raw_bytes[written:])
            except OSError as exc:
                raise StageCArchiveError("archive member write failed") from exc
            if count <= 0:
                raise StageCArchiveError("archive member write made no progress")
            written += count
        os.fsync(descriptor)
        _set_descriptor_read_only(descriptor)
        os.fsync(descriptor)
        handle_stat_before = os.fstat(descriptor)
        handle_identity_before = _FileIdentity.from_stat(handle_stat_before)
        _validate_regular_read_only_file(
            handle_identity_before,
            handle_stat_before.st_mode,
        )
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        observed_length = 0
        maximum = len(raw_bytes) + 1
        while observed_length < maximum:
            chunk = os.read(
                descriptor,
                min(_FILE_HASH_CHUNK_SIZE, maximum - observed_length),
            )
            if not chunk:
                break
            chunks.append(chunk)
            observed_length += len(chunk)
        handle_stat_after = os.fstat(descriptor)
        handle_identity_after = _FileIdentity.from_stat(handle_stat_after)
        if handle_identity_after != handle_identity_before:
            raise StageCArchiveError("archive member changed during same-handle reread")
        if os.name != "nt":
            path_stat = session.member_lstat(target)
            path_identity = _FileIdentity.from_stat(path_stat)
            if not _same_open_file(path_identity, handle_identity_after):
                raise StageCArchiveError(
                    "archive member name changed during same-handle validation"
                )
        observed = b"".join(chunks)
        if observed != raw_bytes:
            raise StageCArchiveError("archive member same-handle reread bytes drifted")
    except Exception:
        # Preserve partial local state. Before manifest publication it is not a
        # completed archive, and a retry must use a new create-only root.
        raise
    finally:
        try:
            os.close(descriptor)
        except OSError as exc:
            raise StageCArchiveError("archive member handle could not be closed") from exc

    raw, identity, ancestors = _read_exact_file(
        root=root,
        session=session,
        relative_path=relative_path,
        expected_sha256=sha256(raw_bytes).hexdigest().upper(),
        expected_byte_length=len(raw_bytes),
        expected_identity=None,
        expected_ancestors=None,
    )
    if raw != raw_bytes:
        raise StageCArchiveError("archive member fsync+reread bytes drifted")
    return identity, ancestors, _fsync_directory(target.parent, session=session)


def _create_directory(
    path: Path,
    *,
    session: _ArchiveDirectorySession,
) -> str:
    session.create_directory(path)
    return _fsync_directory(path.parent, session=session)


def _ensure_internal_directory(
    path: Path,
    *,
    created: set[Path],
    session: _ArchiveDirectorySession,
) -> str | None:
    if path in created:
        session.assert_directory(path)
        return None
    status = _create_directory(path, session=session)
    created.add(path)
    return status


def _content_relative_path(digest: str) -> str:
    if type(digest) is not str or len(digest) != 64:
        raise StageCArchiveError("archive content digest is malformed")
    lowered = digest.lower()
    if any(character not in "0123456789abcdef" for character in lowered):
        raise StageCArchiveError("archive content digest is malformed")
    return f"objects/sha256/{lowered[:2]}/{lowered[2:]}"


def _manifest_artifact_id(index_ref: ArtifactIdentity) -> str:
    ref_digest = sha256(_canonical_json_bytes(index_ref.to_payload())).hexdigest()
    return f"stagec-local-archive-{ref_digest}"


def _directory_status(statuses: list[str]) -> str:
    return (
        DIRECTORY_FSYNC_PERFORMED
        if statuses and all(value == DIRECTORY_FSYNC_PERFORMED for value in statuses)
        else DIRECTORY_FSYNC_UNAVAILABLE
    )


def _capture_members(
    result: StageCCaptureResult,
) -> tuple[tuple[str, CanonicalJsonArtifact | RawArrayArtifact], ...]:
    return (
        ("request_artifact", result.request_artifact),
        ("authorization_projection_artifact", result.authorization_projection_artifact),
        ("capture_index_artifact", result.index_artifact),
        ("input_ids", result.input_ids),
        ("attention_mask", result.attention_mask),
        ("target_vector", result.target_vector),
        ("wrong_layer_vector", result.wrong_layer_vector),
    )


def retain_stagec_capture(
    result: StageCCaptureResult,
    archive_root: object,
) -> StageCLocalArchiveReceipt:
    """Persist all seven exact result artifacts in one new local archive.

    All seven members are created, file-flushed, made read-only, and reread
    before the canonical manifest is published last.  A stop before successful
    manifest publication leaves no valid final manifest.  A stop at or after
    publication can leave an internally valid orphan even when no receipt was
    returned.  The create-only root is never repaired or reused.
    """

    if type(result) is not StageCCaptureResult:
        raise StageCArchiveError("archive creation requires exact StageCCaptureResult")
    replayed_index = replay_stagec_capture_result(result)
    root = _normalize_path(archive_root)
    with _ArchiveDirectorySession(root.parent) as session:
        try:
            root_directory_status = _create_directory(root, session=session)
        except StageCArchiveConflict as exc:
            raise StageCArchiveConflict(
                "create-only archive root already exists"
            ) from exc
        directory_statuses = [root_directory_status]
        created_directories = {root}
        for relative in ("objects", "objects/sha256"):
            path = root.joinpath(*Path(relative).parts)
            status = _ensure_internal_directory(
                path,
                created=created_directories,
                session=session,
            )
            if status is not None:
                directory_statuses.append(status)

        rows: list[dict[str, Any]] = []
        stored_by_path: dict[
            str, tuple[bytes, _FileIdentity, tuple[_AncestorIdentity, ...]]
        ] = {}
        for role, artifact in _capture_members(result):
            relative_path = _content_relative_path(artifact.ref.sha256)
            prefix_dir = root.joinpath(*Path(relative_path).parts[:-1])
            status = _ensure_internal_directory(
                prefix_dir,
                created=created_directories,
                session=session,
            )
            if status is not None:
                directory_statuses.append(status)
            existing = stored_by_path.get(relative_path)
            if existing is None:
                identity, ancestors, status = _write_create_only_file(
                    root=root,
                    session=session,
                    relative_path=relative_path,
                    raw_bytes=artifact.raw_bytes,
                )
                directory_statuses.append(status)
                stored_by_path[relative_path] = (
                    artifact.raw_bytes,
                    identity,
                    ancestors,
                )
            else:
                raw, identity, ancestors = existing
                if raw != artifact.raw_bytes:
                    raise StageCArchiveConflict(
                        "content-address collision names different exact bytes"
                    )
                replay, observed_identity, observed_ancestors = _read_exact_file(
                    root=root,
                    session=session,
                    relative_path=relative_path,
                    expected_sha256=artifact.ref.sha256,
                    expected_byte_length=artifact.ref.byte_length,
                    expected_identity=identity,
                    expected_ancestors=ancestors,
                )
                if (
                    replay != raw
                    or observed_identity != identity
                    or observed_ancestors != ancestors
                ):
                    raise StageCArchiveError(
                        "shared content-addressed member drifted"
                    )
            _, identity, ancestors = stored_by_path[relative_path]
            rows.append(
                {
                    "archive_copy_status": ARCHIVE_COPY_STATUS,
                    "file_identity": identity.to_payload(),
                    "path_ancestors": [item.to_payload() for item in ancestors],
                    "ref": artifact.ref.to_payload(),
                    "relative_path": relative_path,
                    "role": role,
                }
            )

        association = {
            name: replayed_index.association[name] for name in _ASSOCIATION_FIELDS
        }
        session.assert_all()
        root_identity = _require_safe_existing_root(root, session=session)
        manifest_payload = {
            "schema_version": STAGEC_LOCAL_ARCHIVE_SCHEMA,
            "authority": dict(LOCAL_ARCHIVE_AUTHORITY),
            "source_retention_boundary": SOURCE_RETENTION_BOUNDARY,
            "relocatability_boundary": RELOCATABILITY_BOUNDARY,
            "manifest_membership_boundary": MANIFEST_MEMBERSHIP_BOUNDARY,
            "manifest_publication_boundary": MANIFEST_PUBLICATION_BOUNDARY,
            "member_directory_fsync_status": _directory_status(directory_statuses),
            "root_path": str(root),
            "root_identity": root_identity.to_payload(),
            "association": association,
            "members": rows,
        }
        manifest_bytes = _canonical_json_bytes(manifest_payload)
        manifest_relative = STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME
        _, _, manifest_parent_fsync = _write_create_only_file(
            root=root,
            session=session,
            relative_path=manifest_relative,
            raw_bytes=manifest_bytes,
        )
        manifest_ref = ArtifactIdentity(
            artifact_id=_manifest_artifact_id(result.index_artifact.ref),
            sha256=sha256(manifest_bytes).hexdigest().upper(),
            byte_length=len(manifest_bytes),
            media_type=STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE,
        )
        loaded = load_stagec_capture_archive(
            root,
            expected_manifest_ref=manifest_ref,
        )
        if loaded.index.to_payload() != replayed_index.to_payload():
            raise StageCArchiveError("created archive replay drifted from capture result")
        session.assert_all()
        return _new_local_archive_receipt(
            loaded_archive=loaded,
            manifest_parent_directory_fsync_status=manifest_parent_fsync,
        )


def _parse_manifest_member_ref(
    role: str, value: Any
) -> ArtifactIdentity | RawArrayArtifactRef:
    if role in {
        "request_artifact",
        "authorization_projection_artifact",
        "capture_index_artifact",
    }:
        ref = ArtifactIdentity.from_payload(value, field_name=f"members.{role}.ref")
        expected_media = {
            "request_artifact": REQUEST_MEDIA_TYPE,
            "authorization_projection_artifact": AUTHORIZATION_MEDIA_TYPE,
            "capture_index_artifact": CAPTURE_INDEX_MEDIA_TYPE,
        }[role]
        if ref.media_type != expected_media:
            raise StageCArchiveError(f"archive member {role} media type drifted")
        return ref
    return RawArrayArtifactRef.from_payload(value, field_name=f"members.{role}.ref")


def _validate_manifest_payload(
    payload: dict[str, Any],
    *,
    root: Path,
    session: _ArchiveDirectorySession,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    _require_exact_dict(
        payload,
        {
            "association",
            "authority",
            "manifest_membership_boundary",
            "manifest_publication_boundary",
            "member_directory_fsync_status",
            "members",
            "relocatability_boundary",
            "root_identity",
            "root_path",
            "schema_version",
            "source_retention_boundary",
        },
        field_name="archive_manifest",
    )
    if payload["schema_version"] != STAGEC_LOCAL_ARCHIVE_SCHEMA:
        raise StageCArchiveError("archive manifest schema drifted")
    if payload["authority"] != dict(LOCAL_ARCHIVE_AUTHORITY):
        raise StageCArchiveError(
            "archive manifest authority overclaims provenance, WORM, trusted time, or anchor status"
        )
    if payload["source_retention_boundary"] != SOURCE_RETENTION_BOUNDARY:
        raise StageCArchiveError("archive source-retention boundary drifted")
    if payload["relocatability_boundary"] != RELOCATABILITY_BOUNDARY:
        raise StageCArchiveError("archive relocatability boundary drifted")
    if payload["manifest_membership_boundary"] != MANIFEST_MEMBERSHIP_BOUNDARY:
        raise StageCArchiveError("archive manifest-membership boundary drifted")
    if payload["manifest_publication_boundary"] != MANIFEST_PUBLICATION_BOUNDARY:
        raise StageCArchiveError("archive publication boundary drifted")
    if payload["member_directory_fsync_status"] not in {
        DIRECTORY_FSYNC_PERFORMED,
        DIRECTORY_FSYNC_UNAVAILABLE,
    }:
        raise StageCArchiveError("archive member directory-fsync status drifted")
    if payload["root_path"] != str(root):
        raise StageCArchiveError("archive manifest root path drifted")
    expected_root = _StructuralIdentity.from_payload(
        payload["root_identity"], field_name="archive_manifest.root_identity"
    )
    if _require_safe_existing_root(root, session=session) != expected_root:
        raise StageCArchiveError("archive root path identity drifted")

    association = _require_exact_dict(
        payload["association"], set(_ASSOCIATION_FIELDS), field_name="association"
    )
    for name in _ASSOCIATION_FIELDS:
        _require_text(association[name], field_name=f"association.{name}")
    members = payload["members"]
    if type(members) is not list or len(members) != len(STAGEC_ARCHIVE_MEMBER_ROLES):
        raise StageCArchiveError("archive manifest must contain exactly seven member rows")
    observed_roles: list[str] = []
    for index, row in enumerate(members):
        member = _require_exact_dict(
            row,
            {
                "archive_copy_status",
                "file_identity",
                "path_ancestors",
                "ref",
                "relative_path",
                "role",
            },
            field_name=f"members[{index}]",
        )
        role = _require_text(member["role"], field_name=f"members[{index}].role")
        observed_roles.append(role)
        if member["archive_copy_status"] != ARCHIVE_COPY_STATUS:
            raise StageCArchiveError("archive member copy status drifted")
        ref = _parse_manifest_member_ref(role, member["ref"])
        relative = _require_relative_path_text(
            member["relative_path"], field_name=f"members[{index}].relative_path"
        )
        if relative != _content_relative_path(ref.sha256):
            raise StageCArchiveError("archive member path is not its exact content address")
        _FileIdentity.from_payload(
            member["file_identity"], field_name=f"members[{index}].file_identity"
        )
        ancestors = member["path_ancestors"]
        if type(ancestors) is not list or not ancestors:
            raise StageCArchiveError("archive member path ancestors are missing")
        parsed_ancestors = tuple(
            _AncestorIdentity.from_payload(
                item, field_name=f"members[{index}].path_ancestors[{offset}]"
            )
            for offset, item in enumerate(ancestors)
        )
        expected_names = ["."]
        parent_parts = Path(relative).parent.parts
        expected_names.extend(
            Path(*parent_parts[:offset]).as_posix()
            for offset in range(1, len(parent_parts) + 1)
        )
        if [item.relative_path for item in parsed_ancestors] != expected_names:
            raise StageCArchiveError("archive member ancestor ordering/path drifted")
    if tuple(observed_roles) != STAGEC_ARCHIVE_MEMBER_ROLES:
        raise StageCArchiveError("archive member role order drifted")
    return dict(association), members


def load_stagec_capture_archive(
    archive_root: object,
    *,
    expected_manifest_ref: ArtifactIdentity,
) -> StageCArchivedCapture:
    """Reload and semantically replay a local archive using an expected ref.

    ``expected_manifest_ref`` is deliberately required and remains outside the
    manifest bytes, avoiding self-reference.  Its presence proves only the trust
    the caller already has in that ref; this loader does not turn it into an
    external anchor or capture-provenance attestation.
    """

    if type(expected_manifest_ref) is not ArtifactIdentity:
        raise StageCArchiveError("expected manifest ref must be exact ArtifactIdentity")
    if expected_manifest_ref.media_type != STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE:
        raise StageCArchiveError("expected archive manifest media type drifted")
    root = _normalize_path(archive_root)
    with _ArchiveDirectorySession(root) as session:
        _require_safe_existing_root(root, session=session)
        manifest_bytes, _, _ = _read_exact_file(
            root=root,
            session=session,
            relative_path=STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME,
            expected_sha256=expected_manifest_ref.sha256,
            expected_byte_length=expected_manifest_ref.byte_length,
            expected_identity=None,
            expected_ancestors=None,
        )
        manifest_artifact = CanonicalJsonArtifact(
            ref=expected_manifest_ref,
            raw_bytes=manifest_bytes,
        )
        payload = _strict_json_object(
            manifest_bytes, field_name="stagec_local_archive_manifest"
        )
        association, rows = _validate_manifest_payload(
            payload,
            root=root,
            session=session,
        )

        artifacts: dict[str, CanonicalJsonArtifact | RawArrayArtifact] = {}
        paths: dict[str, Path] = {}
        refs: dict[str, ArtifactIdentity | RawArrayArtifactRef] = {}
        for index, row in enumerate(rows):
            role = row["role"]
            ref = _parse_manifest_member_ref(role, row["ref"])
            identity = _FileIdentity.from_payload(
                row["file_identity"], field_name=f"members[{index}].file_identity"
            )
            ancestors = tuple(
                _AncestorIdentity.from_payload(
                    item, field_name=f"members[{index}].path_ancestors[{offset}]"
                )
                for offset, item in enumerate(row["path_ancestors"])
            )
            raw, observed_identity, observed_ancestors = _read_exact_file(
                root=root,
                session=session,
                relative_path=row["relative_path"],
                expected_sha256=ref.sha256,
                expected_byte_length=ref.byte_length,
                expected_identity=identity,
                expected_ancestors=ancestors,
            )
            if observed_identity != identity or observed_ancestors != ancestors:
                raise StageCArchiveError("archive member path identity replay drifted")
            if type(ref) is ArtifactIdentity:
                artifact: CanonicalJsonArtifact | RawArrayArtifact = CanonicalJsonArtifact(
                    ref=ref,
                    raw_bytes=raw,
                )
            else:
                artifact = RawArrayArtifact(ref=ref, raw_bytes=raw)
            artifacts[role] = artifact
            refs[role] = ref
            paths[role] = _safe_member_path(root, row["relative_path"])

        index_ref = refs["capture_index_artifact"]
        if type(index_ref) is not ArtifactIdentity:
            raise StageCArchiveError("archive capture-index ref has the wrong exact type")
        if expected_manifest_ref.artifact_id != _manifest_artifact_id(index_ref):
            raise StageCArchiveError("archive manifest artifact ID is not bound to index ref")
        try:
            index_artifact = artifacts["capture_index_artifact"]
            request_artifact = artifacts["request_artifact"]
            authorization_artifact = artifacts["authorization_projection_artifact"]
            input_ids = artifacts["input_ids"]
            attention_mask = artifacts["attention_mask"]
            target_vector = artifacts["target_vector"]
            wrong_layer_vector = artifacts["wrong_layer_vector"]
            if (
                type(index_artifact) is not CanonicalJsonArtifact
                or type(request_artifact) is not CanonicalJsonArtifact
                or type(authorization_artifact) is not CanonicalJsonArtifact
                or type(input_ids) is not RawArrayArtifact
                or type(attention_mask) is not RawArrayArtifact
                or type(target_vector) is not RawArrayArtifact
                or type(wrong_layer_vector) is not RawArrayArtifact
            ):
                raise StageCArchiveError("archive member exact types drifted")
            replayed_index = replay_stagec_capture_artifacts(
                index_artifact=index_artifact,
                request_artifact=request_artifact,
                authorization_projection_artifact=authorization_artifact,
                input_ids=input_ids,
                attention_mask=attention_mask,
                target_vector=target_vector,
                wrong_layer_vector=wrong_layer_vector,
            )
        except StageCArchiveError:
            raise
        except Exception as exc:
            raise StageCArchiveError(
                f"archived Stage C semantic replay failed: {type(exc).__name__}: {exc}"
            ) from exc
        if {
            name: replayed_index.association[name] for name in _ASSOCIATION_FIELDS
        } != association:
            raise StageCArchiveError("archive association drifted from capture index")
        session.assert_all()
        return _new_archived_capture(
            root=root,
            manifest_artifact=manifest_artifact,
            index_artifact=index_artifact,
            request_artifact=request_artifact,
            authorization_projection_artifact=authorization_artifact,
            input_ids=input_ids,
            attention_mask=attention_mask,
            target_vector=target_vector,
            wrong_layer_vector=wrong_layer_vector,
            index=replayed_index,
            member_paths=paths,
        )


__all__ = [
    "ARCHIVE_COPY_STATUS",
    "DIRECTORY_FSYNC_PERFORMED",
    "DIRECTORY_FSYNC_UNAVAILABLE",
    "LOCAL_ARCHIVE_AUTHORITY",
    "MANIFEST_MEMBERSHIP_BOUNDARY",
    "MANIFEST_PUBLICATION_BOUNDARY",
    "RELOCATABILITY_BOUNDARY",
    "SOURCE_RETENTION_BOUNDARY",
    "STAGEC_ARCHIVE_MEMBER_ROLES",
    "STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME",
    "STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE",
    "STAGEC_LOCAL_ARCHIVE_SCHEMA",
    "StageCArchiveConflict",
    "StageCArchiveError",
    "StageCArchivedCapture",
    "StageCLocalArchiveReceipt",
    "load_stagec_capture_archive",
    "retain_stagec_capture",
]
