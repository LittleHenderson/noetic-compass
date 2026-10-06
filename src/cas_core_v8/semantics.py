"""Typed semantic identities and non-identity crosswalks for CAS Core v8."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any

from .identity import (
    CanonicalizationError,
    require_ascii_identifier,
    require_canonical_text,
    require_sha256,
)


class SemanticValidationError(ValueError):
    """Raised when a semantic identity or migration relation is ambiguous."""


class SemanticNamespace(str, Enum):
    TKS_FOUNDATION = "TKS_FOUNDATION"
    TKS_WORLD = "TKS_WORLD"
    TKS_NOETIC = "TKS_NOETIC"
    CAS_DRIVE = "CAS_DRIVE"
    CAS_DOMAIN = "CAS_DOMAIN"
    CAS_REGISTER = "CAS_REGISTER"
    CAS_NOETIC = "CAS_NOETIC"
    CAS_STATE = "CAS_STATE"
    NOETIC_TOPOS_OBJECT = "NOETIC_TOPOS_OBJECT"


@dataclass(frozen=True, slots=True)
class SemanticRef:
    """One versioned semantic object bound to its defining source bytes."""

    namespace: SemanticNamespace
    local_id: str
    version: str
    source_id: str
    definition_sha256: str

    def __post_init__(self) -> None:
        if type(self) is not SemanticRef:
            raise SemanticValidationError("SemanticRef subclasses are not accepted")
        if type(self.namespace) is not SemanticNamespace:
            raise SemanticValidationError("namespace must be a SemanticNamespace")
        for name in ("local_id", "version", "source_id"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip():
                raise SemanticValidationError(f"{name} must be a non-blank string")
            if value != value.strip():
                raise SemanticValidationError(
                    f"{name} must not contain surrounding whitespace"
                )
            try:
                require_canonical_text(value, field=name)
            except CanonicalizationError as exc:
                raise SemanticValidationError(str(exc)) from exc
        for name in ("local_id", "source_id"):
            try:
                require_ascii_identifier(getattr(self, name), field=name)
            except CanonicalizationError as exc:
                raise SemanticValidationError(str(exc)) from exc
        object.__setattr__(
            self,
            "definition_sha256",
            require_sha256(self.definition_sha256, field="definition_sha256"),
        )

    @property
    def qualified_id(self) -> str:
        components = json.dumps(
            [
                self.namespace.value,
                self.local_id,
                self.version,
                self.source_id,
                self.definition_sha256,
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return f"semantic-ref.v1:{components}"

    def to_dict(self) -> dict[str, str]:
        return {
            "namespace": self.namespace.value,
            "local_id": self.local_id,
            "version": self.version,
            "source_id": self.source_id,
            "definition_sha256": self.definition_sha256,
            "qualified_id": self.qualified_id,
        }


def semantic_refs_match(left: Any, right: Any) -> bool:
    """Compare exact semantic identity primitives without overloaded equality."""

    return (
        type(left) is SemanticRef
        and type(right) is SemanticRef
        and type(left.namespace) is SemanticNamespace
        and type(right.namespace) is SemanticNamespace
        and left.namespace.value == right.namespace.value
        and type(left.local_id) is str
        and type(right.local_id) is str
        and left.local_id == right.local_id
        and type(left.version) is str
        and type(right.version) is str
        and left.version == right.version
        and type(left.source_id) is str
        and type(right.source_id) is str
        and left.source_id == right.source_id
        and type(left.definition_sha256) is str
        and type(right.definition_sha256) is str
        and left.definition_sha256 == right.definition_sha256
    )


class CrosswalkRelation(str, Enum):
    IDENTITY = "IDENTITY"
    TRANSLATION = "TRANSLATION"
    ALIGNMENT = "ALIGNMENT"
    HYPOTHESIS = "HYPOTHESIS"


@dataclass(frozen=True, slots=True)
class SemanticCrosswalk:
    """An explicit relation that cannot fake identity across semantic systems."""

    crosswalk_id: str
    source: SemanticRef
    target: SemanticRef
    relation: CrosswalkRelation
    source_artifact_sha256: str
    note: str
    boundary: "ResearchBoundary" = field(
        default_factory=lambda: ResearchBoundary.ring4_open()
    )

    def __post_init__(self) -> None:
        if type(self) is not SemanticCrosswalk:
            raise SemanticValidationError("SemanticCrosswalk subclasses are not accepted")
        if type(self.crosswalk_id) is not str or not self.crosswalk_id.strip():
            raise SemanticValidationError("crosswalk_id must be non-blank")
        try:
            require_ascii_identifier(self.crosswalk_id, field="crosswalk_id")
        except CanonicalizationError as exc:
            raise SemanticValidationError(str(exc)) from exc
        if type(self.source) is not SemanticRef or type(self.target) is not SemanticRef:
            raise SemanticValidationError("crosswalk endpoints must be SemanticRef values")
        if type(self.relation) is not CrosswalkRelation:
            raise SemanticValidationError("relation must be a CrosswalkRelation")
        object.__setattr__(
            self,
            "source_artifact_sha256",
            require_sha256(
                self.source_artifact_sha256, field="source_artifact_sha256"
            ),
        )
        if type(self.note) is not str or not self.note.strip():
            raise SemanticValidationError("a crosswalk needs an explanatory note")
        try:
            require_canonical_text(self.note, field="crosswalk note")
        except CanonicalizationError as exc:
            raise SemanticValidationError(str(exc)) from exc
        if not is_exact_ring4_open(self.boundary):
            raise SemanticValidationError(
                "CAS Core v8 crosswalk artifacts must remain Ring 4 / OPEN / "
                "NOT LICENSED"
            )
        if self.relation is CrosswalkRelation.IDENTITY and not semantic_refs_match(
            self.source, self.target
        ):
            raise SemanticValidationError(
                "IDENTITY is permitted only for the exact same versioned SemanticRef; "
                "TKS Foundations and CAS Drives, and TKS Worlds and CAS Domains, "
                "must use a non-identity relation"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "crosswalk_id": self.crosswalk_id,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "relation": self.relation.value,
            "source_artifact_sha256": self.source_artifact_sha256,
            "note": self.note,
            "boundary": self.boundary.to_dict(),
        }


class AdmissionStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    ACCEPT = "ACCEPT"


class LicenseStatus(str, Enum):
    NOT_LICENSED = "NOT LICENSED"
    LICENSED = "LICENSED"


@dataclass(frozen=True, slots=True)
class ResearchBoundary:
    """Machine-visible claim boundary carried by every successor artifact."""

    admission_ring: int
    status: AdmissionStatus
    license_status: LicenseStatus
    public_disclosure_authorized: bool

    def __post_init__(self) -> None:
        if type(self) is not ResearchBoundary:
            raise SemanticValidationError("ResearchBoundary subclasses are not accepted")
        if type(self.admission_ring) is not int or self.admission_ring not in (1, 2, 3, 4):
            raise SemanticValidationError("admission_ring must be one of 1, 2, 3, or 4")
        if type(self.status) is not AdmissionStatus:
            raise SemanticValidationError("status must be an AdmissionStatus")
        if type(self.license_status) is not LicenseStatus:
            raise SemanticValidationError("license_status must be a LicenseStatus")
        if type(self.public_disclosure_authorized) is not bool:
            raise SemanticValidationError(
                "public_disclosure_authorized must be a boolean"
            )
        if self.admission_ring == 4 and (
            self.status is not AdmissionStatus.OPEN
            or self.license_status is not LicenseStatus.NOT_LICENSED
            or self.public_disclosure_authorized
        ):
            raise SemanticValidationError(
                "Ring 4 must be OPEN, NOT LICENSED, and not authorized for public "
                "disclosure"
            )
        if self.license_status is LicenseStatus.LICENSED and (
            self.admission_ring != 3 or self.status is not AdmissionStatus.ACCEPT
        ):
            raise SemanticValidationError(
                "LICENSED requires an ACCEPT record admitted at Ring 3"
            )
        if self.public_disclosure_authorized and self.status is not AdmissionStatus.ACCEPT:
            raise SemanticValidationError(
                "public disclosure authorization requires ACCEPT status"
            )

    @classmethod
    def ring4_open(cls) -> "ResearchBoundary":
        return ResearchBoundary(
            admission_ring=4,
            status=AdmissionStatus.OPEN,
            license_status=LicenseStatus.NOT_LICENSED,
            public_disclosure_authorized=False,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "admission_ring": self.admission_ring,
            "status": self.status.value,
            "license_status": self.license_status.value,
            "public_disclosure_authorized": self.public_disclosure_authorized,
        }


def is_exact_ring4_open(value: Any) -> bool:
    """Return true only for the exact frozen Ring-4 research boundary."""

    return (
        type(value) is ResearchBoundary
        and type(value.admission_ring) is int
        and value.admission_ring == 4
        and type(value.status) is AdmissionStatus
        and value.status is AdmissionStatus.OPEN
        and type(value.license_status) is LicenseStatus
        and value.license_status is LicenseStatus.NOT_LICENSED
        and type(value.public_disclosure_authorized) is bool
        and value.public_disclosure_authorized is False
    )
