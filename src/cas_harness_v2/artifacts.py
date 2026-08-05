"""Snapshot registry for exact Evidence Packet and preregistration dependencies."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ._strict_json import sha256_bytes
from ._validation import ArtifactRef, SchemaValidationError, expect_machine_id


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


class ArtifactByteRegistry:
    """An immutable snapshot registry; it is integrity evidence, not authentication."""

    __slots__ = ("_entries",)

    def __init__(self, entries: Mapping[str, bytes | bytearray | memoryview]) -> None:
        if not isinstance(entries, Mapping):
            raise SchemaValidationError("artifact byte registry must be a mapping")
        snapshots: dict[str, EvidenceBytes] = {}
        for artifact_id, raw in entries.items():
            expect_machine_id(artifact_id, "artifact_registry key")
            if type(raw) not in (bytes, bytearray, memoryview):
                raise SchemaValidationError(f"artifact {artifact_id!r} must contain bytes-like data")
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
        return (
            entry is not None
            and type(entry.raw_bytes) is bytes
            and entry.sha256 == sha256_bytes(entry.raw_bytes)
            and entry.byte_length == len(entry.raw_bytes)
            and entry.sha256 == reference.sha256
            and entry.byte_length == reference.byte_length
        )

    def require(self, reference: ArtifactRef) -> EvidenceBytes:
        entry = self._entries.get(reference.artifact_id)
        if entry is None:
            raise SchemaValidationError(
                f"artifact bytes unavailable for {reference.artifact_id!r}"
            )
        retained_bytes_valid = (
            type(entry.raw_bytes) is bytes
            and entry.sha256 == sha256_bytes(entry.raw_bytes)
            and entry.byte_length == len(entry.raw_bytes)
        )
        if (
            not retained_bytes_valid
            or entry.sha256 != reference.sha256
            or entry.byte_length != reference.byte_length
        ):
            raise SchemaValidationError(
                f"artifact bytes do not match the bound identity for {reference.artifact_id!r}"
            )
        return entry
