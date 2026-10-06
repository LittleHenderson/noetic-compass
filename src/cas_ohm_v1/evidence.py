"""Resolved artifact bytes and typed derivation-parent registries."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from .canonical import (
    ValidationError,
    canonical_bytes,
    canonical_sha256,
    canonical_type_id,
    require_sha256,
    require_text,
)
from .model import ArtifactRef, ParentRef

ARTIFACT_BYTES_TYPE = "cas_ohm_v1.artifact-bytes"


@dataclass(frozen=True, slots=True)
class ArtifactEvidence:
    ref: ArtifactRef
    payload: bytes

    def __post_init__(self) -> None:
        if type(self.ref) is not ArtifactRef:
            raise ValidationError("ref must be an exact ArtifactRef")
        if type(self.payload) is not bytes:
            raise ValidationError("artifact payload must be immutable bytes")
        actual = hashlib.sha256(self.payload).hexdigest().upper()
        if actual != self.ref.sha256:
            raise ValidationError(
                f"artifact bytes do not match {self.ref.artifact_id} SHA-256"
            )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "byte_length": len(self.payload),
            "ref": self.ref,
            "verified_sha256": self.ref.sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class EvidenceRegistry:
    artifacts: tuple[ArtifactEvidence, ...]
    objects: tuple[object, ...] = ()
    _artifact_snapshots: tuple[tuple[int, str, bytes, bytes], ...] = field(
        init=False, repr=False, compare=False
    )
    _object_snapshots: tuple[tuple[int, str, str, bytes], ...] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if type(self.artifacts) is not tuple:
            raise ValidationError("artifacts must be an exact tuple")
        if any(type(item) is not ArtifactEvidence for item in self.artifacts):
            raise ValidationError(
                "artifacts must contain exact ArtifactEvidence values"
            )
        artifact_hashes = [item.ref.sha256 for item in self.artifacts]
        if len(artifact_hashes) != len(set(artifact_hashes)):
            raise ValidationError(
                "artifact registry contains duplicate content digests"
            )
        if type(self.objects) is not tuple:
            raise ValidationError("objects must be an exact tuple")
        identities: list[tuple[str, str]] = []
        for value in self.objects:
            object_sha256 = getattr(value, "sha256", None)
            if type(object_sha256) is not str:
                raise ValidationError(
                    "registered objects must expose a SHA-256 identity"
                )
            require_sha256(object_sha256, "registered object sha256")
            identities.append((canonical_type_id(value), object_sha256))
        if len(identities) != len(set(identities)):
            raise ValidationError("object registry contains duplicate typed identities")
        object.__setattr__(
            self,
            "_artifact_snapshots",
            tuple(
                (id(item), item.ref.sha256, canonical_bytes(item.ref), item.payload)
                for item in self.artifacts
            ),
        )
        object.__setattr__(
            self,
            "_object_snapshots",
            tuple(
                (
                    id(value),
                    canonical_type_id(value),
                    value.sha256,
                    canonical_bytes(value),
                )
                for value in self.objects
            ),
        )

    def revalidate_all(self) -> None:
        """Reject mutation or identity substitution after registry admission."""

        if type(self.artifacts) is not tuple or type(self.objects) is not tuple:
            raise ValidationError("evidence registry containers were mutated")
        if len(self.artifacts) != len(self._artifact_snapshots):
            raise ValidationError("artifact registry identity changed after admission")
        for item, snapshot in zip(self.artifacts, self._artifact_snapshots):
            if type(item) is not ArtifactEvidence:
                raise ValidationError("artifact registry exact type changed")
            identity, digest, ref_bytes, payload = snapshot
            actual = hashlib.sha256(item.payload).hexdigest().upper()
            if (
                id(item) != identity
                or item.ref.sha256 != digest
                or canonical_bytes(item.ref) != ref_bytes
                or item.payload != payload
                or actual != digest
            ):
                raise ValidationError("artifact evidence changed after admission")
        if len(self.objects) != len(self._object_snapshots):
            raise ValidationError("object registry identity changed after admission")
        for value, snapshot in zip(self.objects, self._object_snapshots):
            identity, object_type, digest, payload = snapshot
            if (
                id(value) != identity
                or canonical_type_id(value) != object_type
                or getattr(value, "sha256", None) != digest
                or canonical_bytes(value) != payload
            ):
                raise ValidationError("registered object changed after admission")

    def artifact_for(self, ref_or_sha256: ArtifactRef | str) -> ArtifactEvidence:
        self.revalidate_all()
        if type(ref_or_sha256) not in {ArtifactRef, str}:
            raise ValidationError("artifact lookup requires exact ArtifactRef or str")
        digest = (
            ref_or_sha256.sha256
            if type(ref_or_sha256) is ArtifactRef
            else ref_or_sha256
        )
        require_sha256(digest, "artifact sha256")
        for artifact in self.artifacts:
            if artifact.ref.sha256 == digest:
                if type(ref_or_sha256) is ArtifactRef and artifact.ref != ref_or_sha256:
                    raise ValidationError(
                        "artifact metadata does not match resolved evidence"
                    )
                return artifact
        raise ValidationError(f"artifact bytes are unresolved: {digest}")

    def require_refs(self, refs: tuple[ArtifactRef, ...]) -> None:
        self.revalidate_all()
        if type(refs) is not tuple or any(type(ref) is not ArtifactRef for ref in refs):
            raise ValidationError("refs must be an exact tuple of ArtifactRef values")
        for ref in refs:
            self.artifact_for(ref)

    def object_for(self, object_type: str, object_sha256: str) -> object:
        self.revalidate_all()
        require_text(object_type, "object_type")
        require_sha256(object_sha256, "object_sha256")
        for value in self.objects:
            if (
                canonical_type_id(value) == object_type
                and value.sha256 == object_sha256
            ):
                return value
        raise ValidationError(
            f"typed parent is unresolved: {object_type}:{object_sha256}"
        )

    def require_parent(self, parent: ParentRef) -> object:
        self.revalidate_all()
        if type(parent) is not ParentRef:
            raise ValidationError("parent must be an exact ParentRef")
        if parent.object_type == ARTIFACT_BYTES_TYPE:
            return self.artifact_for(parent.object_sha256)
        return self.object_for(parent.object_type, parent.object_sha256)

    def require_parents(self, parents: tuple[ParentRef, ...]) -> None:
        self.revalidate_all()
        if type(parents) is not tuple or any(
            type(item) is not ParentRef for item in parents
        ):
            raise ValidationError("parents must be an exact tuple of ParentRef values")
        for expected_position, parent in enumerate(parents):
            if parent.position != expected_position:
                raise ValidationError("parent order is not canonical")
            self.require_parent(parent)


def parent_ref(role: str, position: int, value: Any) -> ParentRef:
    if type(value) is ArtifactEvidence:
        return ParentRef(role, position, ARTIFACT_BYTES_TYPE, value.ref.sha256)
    if type(value) is ArtifactRef:
        return ParentRef(role, position, ARTIFACT_BYTES_TYPE, value.sha256)
    object_sha256 = getattr(value, "sha256", None)
    if type(object_sha256) is not str:
        raise ValidationError("parent objects must expose a SHA-256 identity")
    return ParentRef(role, position, canonical_type_id(value), object_sha256)
