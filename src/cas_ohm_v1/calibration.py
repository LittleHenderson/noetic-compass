"""Complete calibration identities, trusted capabilities, and exact normalization."""

from __future__ import annotations

import hashlib
import re
from dataclasses import InitVar, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from fractions import Fraction

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical import (
    CapabilityError,
    ValidationError,
    arithmetic_context,
    canonical_sha256,
    require_decimal,
    require_positive_int,
    require_sha256,
    require_text,
)
from .canonical import (
    canonical_bytes as encode_canonical,
)
from .evidence import EvidenceRegistry, parent_ref
from .model import (
    ADMISSION_RING,
    COVARIANCE_LIMITATION,
    DISCLOSURE_STATUS,
    LICENSE_STATUS,
    RESEARCH_STATUS,
    ArtifactRef,
    AuthorizationState,
    Capability,
    ControlBinding,
    FieldProvenance,
    IFSMethod,
    InstrumentIdentity,
    MeasurementKind,
    MeasurementValue,
    ModelIdentity,
    OperationBinding,
    QuantityKind,
    ReviewState,
    TestPointIdentity,
    TrustMode,
    Uncertainty,
    UnitKind,
)


def _parse_time(value: str, field_name: str) -> tuple[datetime, str]:
    require_text(value, field_name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} must include a timezone")
    parsed = parsed.astimezone(timezone.utc)
    return parsed, parsed.isoformat().replace("+00:00", "Z")


def _unique_refs(*groups: tuple[ArtifactRef, ...]) -> tuple[ArtifactRef, ...]:
    values: dict[str, ArtifactRef] = {}
    for group in groups:
        for ref in group:
            existing = values.get(ref.sha256)
            if existing is not None and existing != ref:
                raise ValidationError("same artifact digest has conflicting metadata")
            values[ref.sha256] = ref
    return tuple(values[digest] for digest in sorted(values))


class DriftState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    FAILED = "FAILED"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class FullScaleValue:
    test_point_sha256: str
    value: Decimal
    unit: UnitKind
    uncertainty: Uncertainty
    sample_size: int
    source_refs: tuple[ArtifactRef, ...]

    def __post_init__(self) -> None:
        require_sha256(self.test_point_sha256, "test_point_sha256")
        value = require_decimal(self.value, "value")
        if value <= 0:
            raise ValidationError("full-scale value must be strictly positive")
        if self.unit is not UnitKind.ACTIVATION:
            raise ValidationError("full-scale unit must be ACTIVATION")
        if type(self.uncertainty) is not Uncertainty:
            raise ValidationError("full-scale uncertainty must be exact Uncertainty")
        if self.uncertainty.unit is not self.unit:
            raise ValidationError("full-scale uncertainty unit mismatch")
        if self.uncertainty.lower <= 0:
            raise ValidationError(
                "full-scale uncertainty interval must remain positive"
            )
        if not self.uncertainty.lower <= value <= self.uncertainty.upper:
            raise ValidationError(
                "full-scale value must lie in its uncertainty interval"
            )
        require_positive_int(self.sample_size, "sample_size")
        if type(self.source_refs) is not tuple or not self.source_refs:
            raise ValidationError(
                "full-scale source_refs must be an exact non-empty tuple"
            )
        if any(type(ref) is not ArtifactRef for ref in self.source_refs):
            raise ValidationError(
                "full-scale source_refs must contain ArtifactRef values"
            )
        if len({ref.sha256 for ref in self.source_refs}) != len(self.source_refs):
            raise ValidationError("full-scale source_refs contains duplicates")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "sample_size": self.sample_size,
            "source_refs": tuple(sorted(self.source_refs, key=lambda ref: ref.sha256)),
            "test_point_sha256": self.test_point_sha256,
            "uncertainty": self.uncertainty,
            "unit": self.unit,
            "value": self.value,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class ToleranceProfile:
    delta_abs: Decimal
    delta_relative: Decimal
    residual_floor: Decimal
    linearity_r2_min: Decimal
    off_target_max: Decimal

    def __post_init__(self) -> None:
        delta_abs = require_decimal(self.delta_abs, "delta_abs")
        delta_relative = require_decimal(self.delta_relative, "delta_relative")
        residual_floor = require_decimal(self.residual_floor, "residual_floor")
        linearity = require_decimal(self.linearity_r2_min, "linearity_r2_min")
        off_target = require_decimal(self.off_target_max, "off_target_max")
        if delta_abs <= 0 or residual_floor <= 0:
            raise ValidationError(
                "absolute and residual-floor tolerances must be positive"
            )
        if not Decimal("0") <= delta_relative <= Decimal("1"):
            raise ValidationError("delta_relative must be in [0, 1]")
        if not Decimal("0") <= linearity <= Decimal("1"):
            raise ValidationError("linearity_r2_min must be in [0, 1]")
        if not Decimal("0") <= off_target <= Decimal("1"):
            raise ValidationError("off_target_max must be in [0, 1]")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "delta_abs": self.delta_abs,
            "delta_relative": self.delta_relative,
            "linearity_r2_min": self.linearity_r2_min,
            "off_target_max": self.off_target_max,
            "residual_floor": self.residual_floor,
        }


@dataclass(frozen=True, slots=True)
class CapabilityAttestation:
    profile_sha256: str
    capability: Capability
    evidence_ref: ArtifactRef
    reviewer_id: str
    issued_at: str
    expires_at: str
    signature: str

    def __post_init__(self) -> None:
        require_sha256(self.profile_sha256, "profile_sha256")
        if type(self.capability) is not Capability:
            raise ValidationError("capability must be an exact Capability")
        if type(self.evidence_ref) is not ArtifactRef:
            raise ValidationError("evidence_ref must be an exact ArtifactRef")
        require_text(self.reviewer_id, "reviewer_id")
        issued, canonical_issued = _parse_time(self.issued_at, "issued_at")
        expires, canonical_expires = _parse_time(self.expires_at, "expires_at")
        if issued >= expires:
            raise ValidationError("capability attestation must expire after issuance")
        object.__setattr__(self, "issued_at", canonical_issued)
        object.__setattr__(self, "expires_at", canonical_expires)
        if (
            type(self.signature) is not str
            or re.fullmatch(r"[0-9A-F]{128}", self.signature) is None
        ):
            raise ValidationError(
                "signature must be an uppercase 64-byte Ed25519 signature"
            )

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "evidence_ref": self.evidence_ref,
            "expires_at": self.expires_at,
            "issued_at": self.issued_at,
            "profile_sha256": self.profile_sha256,
            "reviewer_id": self.reviewer_id,
            "schema": "CAS-OHM-V1-CAPABILITY-ATTESTATION",
        }

    def canonical_payload(self) -> dict[str, object]:
        return {**self.unsigned_payload(), "signature": self.signature}

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class AuthorityKey:
    reviewer_id: str
    public_key_hex: str
    fingerprint_sha256: str

    def __post_init__(self) -> None:
        require_text(self.reviewer_id, "reviewer_id")
        if (
            type(self.public_key_hex) is not str
            or re.fullmatch(r"[0-9A-F]{64}", self.public_key_hex) is None
        ):
            raise ValidationError("public_key_hex must encode 32 Ed25519 bytes")
        public_key = bytes.fromhex(self.public_key_hex)
        try:
            Ed25519PublicKey.from_public_bytes(public_key)
        except ValueError as exc:
            raise ValidationError("authority public key is invalid") from exc
        expected = hashlib.sha256(public_key).hexdigest().upper()
        if require_sha256(self.fingerprint_sha256, "fingerprint_sha256") != expected:
            raise ValidationError("authority key fingerprint does not match key bytes")

    @classmethod
    def from_public_key(cls, reviewer_id: str, public_key: bytes) -> AuthorityKey:
        if type(public_key) is not bytes or len(public_key) != 32:
            raise ValidationError("Ed25519 public keys must be exactly 32 bytes")
        return cls(
            reviewer_id,
            public_key.hex().upper(),
            hashlib.sha256(public_key).hexdigest().upper(),
        )

    @property
    def public_key(self) -> bytes:
        return bytes.fromhex(self.public_key_hex)

    def canonical_payload(self) -> dict[str, object]:
        return {
            "fingerprint_sha256": self.fingerprint_sha256,
            "public_key_hex": self.public_key_hex,
            "reviewer_id": self.reviewer_id,
        }


@dataclass(frozen=True, slots=True)
class AuthorityManifest:
    manifest_id: str
    version: str
    trust_mode: TrustMode
    keys: tuple[AuthorityKey, ...]

    def __post_init__(self) -> None:
        require_text(self.manifest_id, "manifest_id")
        require_text(self.version, "version")
        if type(self.trust_mode) is not TrustMode:
            raise ValidationError("trust_mode must be exact TrustMode")
        if type(self.keys) is not tuple or any(
            type(value) is not AuthorityKey for value in self.keys
        ):
            raise ValidationError("keys must be an exact tuple of AuthorityKey values")
        reviewer_ids = tuple(key.reviewer_id for key in self.keys)
        if reviewer_ids != tuple(sorted(set(reviewer_ids))):
            raise ValidationError(
                "authority keys must be unique and ordered by reviewer"
            )
        fingerprints = tuple(key.fingerprint_sha256 for key in self.keys)
        if len(fingerprints) != len(set(fingerprints)):
            raise ValidationError("authority key fingerprints must be unique")
        if self.trust_mode is TrustMode.INTEGRITY_CONFIGURATION and not self.keys:
            raise ValidationError("integrity configuration requires at least one key")
        if self.trust_mode is TrustMode.STRUCTURAL_RESEARCH_ONLY and self.keys:
            raise ValidationError(
                "structural-only authority manifest cannot contain keys"
            )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "keys": self.keys,
            "manifest_id": self.manifest_id,
            "schema": "CAS-OHM-V1-AUTHORITY-MANIFEST",
            "trust_mode": self.trust_mode,
            "version": self.version,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return encode_canonical(self)

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class CurrentClockReceipt:
    authority_manifest_sha256: str
    evidence_ref: ArtifactRef
    issuer_id: str
    issued_at: str
    observed_at: str
    expires_at: str
    signature: str

    def __post_init__(self) -> None:
        require_sha256(self.authority_manifest_sha256, "authority_manifest_sha256")
        if type(self.evidence_ref) is not ArtifactRef:
            raise ValidationError("evidence_ref must be an exact ArtifactRef")
        require_text(self.issuer_id, "issuer_id")
        issued, canonical_issued = _parse_time(self.issued_at, "issued_at")
        observed, canonical_observed = _parse_time(self.observed_at, "observed_at")
        expires, canonical_expires = _parse_time(self.expires_at, "expires_at")
        if not issued <= observed < expires:
            raise ValidationError("clock receipt times are incoherent")
        object.__setattr__(self, "issued_at", canonical_issued)
        object.__setattr__(self, "observed_at", canonical_observed)
        object.__setattr__(self, "expires_at", canonical_expires)
        if (
            type(self.signature) is not str
            or re.fullmatch(r"[0-9A-F]{128}", self.signature) is None
        ):
            raise ValidationError("clock signature must be 64-byte uppercase hex")

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "authority_manifest_sha256": self.authority_manifest_sha256,
            "evidence_ref": self.evidence_ref,
            "expires_at": self.expires_at,
            "issued_at": self.issued_at,
            "issuer_id": self.issuer_id,
            "observed_at": self.observed_at,
            "schema": "CAS-OHM-V1-CURRENT-CLOCK-RECEIPT",
        }

    def canonical_payload(self) -> dict[str, object]:
        return {**self.unsigned_payload(), "signature": self.signature}

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class TrustedCapabilityAuthority:
    """Content-addressed integrity configuration, not independent authority."""

    manifest: AuthorityManifest
    manifest_ref: ArtifactRef

    def __post_init__(self) -> None:
        if type(self.manifest) is not AuthorityManifest:
            raise ValidationError("manifest must be exact AuthorityManifest")
        if type(self.manifest_ref) is not ArtifactRef:
            raise ValidationError("manifest_ref must be exact ArtifactRef")
        if self.manifest_ref.sha256 != self.manifest.sha256:
            raise ValidationError("authority manifest ref is not content-addressed")

    @property
    def trust_mode(self) -> TrustMode:
        return self.manifest.trust_mode

    @staticmethod
    def public_key_from_private(private_key: bytes) -> bytes:
        if type(private_key) is not bytes or len(private_key) != 32:
            raise ValidationError("Ed25519 private keys must be exactly 32 bytes")
        key = Ed25519PrivateKey.from_private_bytes(private_key)
        return key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )

    @staticmethod
    def sign(
        profile_sha256: str,
        capability: Capability,
        evidence_ref: ArtifactRef,
        reviewer_id: str,
        issued_at: str,
        expires_at: str,
        private_key: bytes,
    ) -> CapabilityAttestation:
        require_sha256(profile_sha256, "profile_sha256")
        _, issued = _parse_time(issued_at, "issued_at")
        _, expires = _parse_time(expires_at, "expires_at")
        unsigned = {
            "capability": capability,
            "evidence_ref": evidence_ref,
            "expires_at": expires,
            "issued_at": issued,
            "profile_sha256": profile_sha256,
            "reviewer_id": reviewer_id,
            "schema": "CAS-OHM-V1-CAPABILITY-ATTESTATION",
        }
        if type(private_key) is not bytes or len(private_key) != 32:
            raise ValidationError("Ed25519 private keys must be exactly 32 bytes")
        signature = (
            Ed25519PrivateKey.from_private_bytes(private_key)
            .sign(encode_canonical(unsigned))
            .hex()
            .upper()
        )
        return CapabilityAttestation(
            profile_sha256,
            capability,
            evidence_ref,
            reviewer_id,
            issued,
            expires,
            signature,
        )

    @staticmethod
    def sign_current_clock_receipt(
        authority_manifest_sha256: str,
        evidence_ref: ArtifactRef,
        issuer_id: str,
        issued_at: str,
        observed_at: str,
        expires_at: str,
        private_key: bytes,
    ) -> CurrentClockReceipt:
        require_sha256(authority_manifest_sha256, "authority_manifest_sha256")
        if type(evidence_ref) is not ArtifactRef:
            raise ValidationError("evidence_ref must be an exact ArtifactRef")
        _, issued = _parse_time(issued_at, "issued_at")
        _, observed = _parse_time(observed_at, "observed_at")
        _, expires = _parse_time(expires_at, "expires_at")
        unsigned = {
            "authority_manifest_sha256": authority_manifest_sha256,
            "evidence_ref": evidence_ref,
            "expires_at": expires,
            "issued_at": issued,
            "issuer_id": issuer_id,
            "observed_at": observed,
            "schema": "CAS-OHM-V1-CURRENT-CLOCK-RECEIPT",
        }
        if type(private_key) is not bytes or len(private_key) != 32:
            raise ValidationError("Ed25519 private keys must be exactly 32 bytes")
        signature = (
            Ed25519PrivateKey.from_private_bytes(private_key)
            .sign(encode_canonical(unsigned))
            .hex()
            .upper()
        )
        return CurrentClockReceipt(
            authority_manifest_sha256,
            evidence_ref,
            issuer_id,
            issued,
            observed,
            expires,
            signature,
        )

    def verify(
        self,
        attestation: CapabilityAttestation,
        profile_sha256: str,
        evidence: EvidenceRegistry,
        as_of: datetime,
    ) -> None:
        if type(attestation) is not CapabilityAttestation:
            raise ValidationError("attestation must be exact CapabilityAttestation")
        require_sha256(profile_sha256, "profile_sha256")
        if type(evidence) is not EvidenceRegistry:
            raise ValidationError("evidence must be exact EvidenceRegistry")
        if (
            type(as_of) is not datetime
            or as_of.tzinfo is None
            or as_of.utcoffset() is None
        ):
            raise ValidationError("as_of must be an aware exact datetime")
        as_of = as_of.astimezone(timezone.utc)
        if self.trust_mode is not TrustMode.INTEGRITY_CONFIGURATION:
            raise CapabilityError(
                "structural-only mode has no capability integrity keys"
            )
        if attestation.profile_sha256 != profile_sha256:
            raise CapabilityError("capability attestation binds a different profile")
        public_key = next(
            (
                key.public_key
                for key in self.manifest.keys
                if key.reviewer_id == attestation.reviewer_id
            ),
            None,
        )
        if public_key is None:
            raise CapabilityError("capability reviewer is not a configured trust root")
        evidence.artifact_for(attestation.evidence_ref)
        issued, _ = _parse_time(attestation.issued_at, "issued_at")
        expires, _ = _parse_time(attestation.expires_at, "expires_at")
        if not issued <= as_of < expires:
            raise CapabilityError("capability attestation is not current")
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                bytes.fromhex(attestation.signature),
                encode_canonical(attestation.unsigned_payload()),
            )
        except InvalidSignature as exc:
            raise CapabilityError(
                "capability attestation signature is invalid"
            ) from exc
        except ValueError as exc:
            raise CapabilityError("capability attestation encoding is invalid") from exc

    def verify_current_clock_receipt(
        self,
        receipt: CurrentClockReceipt,
        evidence: EvidenceRegistry,
    ) -> None:
        """Verify configured-key integrity without treating it as trusted time."""

        if type(receipt) is not CurrentClockReceipt:
            raise ValidationError("receipt must be exact CurrentClockReceipt")
        if self.trust_mode is not TrustMode.INTEGRITY_CONFIGURATION:
            raise CapabilityError("structural-only mode has no clock integrity keys")
        if receipt.authority_manifest_sha256 != self.manifest.sha256:
            raise CapabilityError("clock receipt binds a different manifest")
        public_key = next(
            (
                key.public_key
                for key in self.manifest.keys
                if key.reviewer_id == receipt.issuer_id
            ),
            None,
        )
        if public_key is None:
            raise CapabilityError("clock issuer is not in the integrity manifest")
        evidence.artifact_for(receipt.evidence_ref)
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                bytes.fromhex(receipt.signature),
                encode_canonical(receipt.unsigned_payload()),
            )
        except InvalidSignature as exc:
            raise CapabilityError("clock receipt signature is invalid") from exc
        except ValueError as exc:
            raise CapabilityError("clock receipt encoding is invalid") from exc


@dataclass(frozen=True, slots=True)
class CalibrationProfile:
    profile_id: str
    model: ModelIdentity
    created_at: str
    valid_from: str
    expires_at: str
    drift_state: DriftState
    drift_check_ref: ArtifactRef
    runtime_id: str
    dtype: str
    code_ref: ArtifactRef
    dependency_lock_ref: ArtifactRef
    model_artifact_refs: tuple[ArtifactRef, ...]
    corpus_ref: ArtifactRef
    corpus_rights_ref: ArtifactRef
    calibration_split_ref: ArtifactRef
    validation_split_ref: ArtifactRef
    random_seed: int
    randomization_method: str
    instruments: tuple[InstrumentIdentity, ...]
    instrument_implementation_refs: tuple[ArtifactRef, ...]
    test_points: tuple[TestPointIdentity, ...]
    direction_refs: tuple[ArtifactRef, ...]
    ifs_method: IFSMethod
    full_scales: tuple[FullScaleValue, ...]
    ifs_percentile: Decimal | None
    alpha_grid: tuple[Decimal, ...]
    alpha_min: Decimal
    alpha_max: Decimal
    fit_method_id: str
    fit_receipt_ref: ArtifactRef
    uncertainty_method_id: str
    response_region_method_id: str
    tolerances: ToleranceProfile
    control_refs: tuple[ArtifactRef, ...]
    control_bindings: tuple[ControlBinding, ...]
    source_refs: tuple[ArtifactRef, ...]
    review_state: ReviewState

    def __post_init__(self) -> None:
        require_text(self.profile_id, "profile_id")
        if type(self.model) is not ModelIdentity:
            raise ValidationError("model must be an exact ModelIdentity")
        created, canonical_created = _parse_time(self.created_at, "created_at")
        valid_from, canonical_valid_from = _parse_time(self.valid_from, "valid_from")
        expires, canonical_expires = _parse_time(self.expires_at, "expires_at")
        if not created <= valid_from < expires:
            raise ValidationError(
                "profile times must satisfy created_at <= valid_from < expires_at"
            )
        object.__setattr__(self, "created_at", canonical_created)
        object.__setattr__(self, "valid_from", canonical_valid_from)
        object.__setattr__(self, "expires_at", canonical_expires)
        if type(self.drift_state) is not DriftState:
            raise ValidationError("drift_state must be an exact DriftState")
        for field_name in (
            "drift_check_ref",
            "code_ref",
            "dependency_lock_ref",
            "corpus_ref",
            "corpus_rights_ref",
            "calibration_split_ref",
            "validation_split_ref",
            "fit_receipt_ref",
        ):
            if type(getattr(self, field_name)) is not ArtifactRef:
                raise ValidationError(f"{field_name} must be an ArtifactRef")
        for refs, field_name in (
            (self.model_artifact_refs, "model_artifact_refs"),
            (
                self.instrument_implementation_refs,
                "instrument_implementation_refs",
            ),
            (self.direction_refs, "direction_refs"),
        ):
            if type(refs) is not tuple or any(
                type(ref) is not ArtifactRef for ref in refs
            ):
                raise ValidationError(
                    f"{field_name} must be an exact tuple of ArtifactRef values"
                )
            if len({ref.sha256 for ref in refs}) != len(refs):
                raise ValidationError(f"{field_name} contains duplicates")
        model_digests = {
            self.model.weights_sha256,
            self.model.config_sha256,
            self.model.tokenizer_sha256,
        }
        if {ref.sha256 for ref in self.model_artifact_refs} != model_digests:
            raise ValidationError(
                "model_artifact_refs must resolve weights, config, and tokenizer"
            )
        if self.calibration_split_ref.sha256 == self.validation_split_ref.sha256:
            raise ValidationError("calibration and validation splits must be distinct")
        require_text(self.runtime_id, "runtime_id")
        require_text(self.dtype, "dtype")
        if type(self.random_seed) is not int or self.random_seed < 0:
            raise ValidationError("random_seed must be a non-negative integer")
        require_text(self.randomization_method, "randomization_method")
        if type(self.instruments) is not tuple or not self.instruments:
            raise ValidationError("instruments must be a non-empty tuple")
        if any(type(item) is not InstrumentIdentity for item in self.instruments):
            raise ValidationError("instruments must contain InstrumentIdentity values")
        if len({item.instrument_id for item in self.instruments}) != len(
            self.instruments
        ):
            raise ValidationError("instrument ids must be unique")
        instrument_digests = {item.implementation_sha256 for item in self.instruments}
        if {
            ref.sha256 for ref in self.instrument_implementation_refs
        } != instrument_digests:
            raise ValidationError(
                "instrument implementation source bytes are not fully resolved"
            )
        if type(self.test_points) is not tuple or not self.test_points:
            raise ValidationError("test_points must be a non-empty tuple")
        if any(type(item) is not TestPointIdentity for item in self.test_points):
            raise ValidationError("test_points must contain TestPointIdentity values")
        if any(item.model != self.model for item in self.test_points):
            raise ValidationError("every test point must bind the profile model")
        test_point_hashes = {item.sha256 for item in self.test_points}
        if len(test_point_hashes) != len(self.test_points):
            raise ValidationError("test points must be unique")
        direction_digests = {item.direction_sha256 for item in self.test_points}
        if {ref.sha256 for ref in self.direction_refs} != direction_digests:
            raise ValidationError("direction source bytes are not fully resolved")
        if type(self.ifs_method) is not IFSMethod:
            raise ValidationError("ifs_method must be an exact IFSMethod")
        if type(self.full_scales) is not tuple or not self.full_scales:
            raise ValidationError("full_scales must be an exact non-empty tuple")
        if any(type(item) is not FullScaleValue for item in self.full_scales):
            raise ValidationError(
                "full_scales must contain exact FullScaleValue values"
            )
        full_scale_points = {item.test_point_sha256 for item in self.full_scales}
        if (
            len(full_scale_points) != len(self.full_scales)
            or full_scale_points != test_point_hashes
        ):
            raise ValidationError(
                "full scales must cover each registered test point exactly once"
            )
        if self.ifs_method is IFSMethod.CORPUS_PERCENTILE_PER_TEST_POINT:
            if self.ifs_percentile is None:
                raise ValidationError("corpus-percentile I_FS requires ifs_percentile")
            percentile = require_decimal(self.ifs_percentile, "ifs_percentile")
            if not Decimal("0") < percentile < Decimal("100"):
                raise ValidationError("ifs_percentile must be in (0, 100)")
        elif self.ifs_percentile is not None:
            raise ValidationError(
                "ifs_percentile is valid only for corpus-percentile I_FS"
            )
        if type(self.alpha_grid) is not tuple or len(self.alpha_grid) < 3:
            raise ValidationError("alpha_grid must contain at least three exact doses")
        grid = tuple(
            require_decimal(value, "alpha_grid value") for value in self.alpha_grid
        )
        if grid != tuple(sorted(set(grid))):
            raise ValidationError("alpha_grid must be strictly increasing and unique")
        alpha_min = require_decimal(self.alpha_min, "alpha_min")
        alpha_max = require_decimal(self.alpha_max, "alpha_max")
        if grid[0] != alpha_min or grid[-1] != alpha_max or Decimal("0") not in grid:
            raise ValidationError(
                "alpha range must equal the grid endpoints and include zero"
            )
        require_text(self.fit_method_id, "fit_method_id")
        require_text(self.uncertainty_method_id, "uncertainty_method_id")
        require_text(self.response_region_method_id, "response_region_method_id")
        if type(self.tolerances) is not ToleranceProfile:
            raise ValidationError("tolerances must be an exact ToleranceProfile")
        for refs, field_name in (
            (self.control_refs, "control_refs"),
            (self.source_refs, "source_refs"),
        ):
            if type(refs) is not tuple or not refs:
                raise ValidationError(f"{field_name} must be a non-empty tuple")
            if any(type(ref) is not ArtifactRef for ref in refs):
                raise ValidationError(f"{field_name} must contain ArtifactRef values")
            if len({ref.sha256 for ref in refs}) != len(refs):
                raise ValidationError(f"{field_name} contains duplicates")
        if type(self.control_bindings) is not tuple or any(
            type(binding) is not ControlBinding for binding in self.control_bindings
        ):
            raise ValidationError(
                "control_bindings must be an exact tuple of ControlBinding values"
            )
        if len({binding.sha256 for binding in self.control_bindings}) != len(
            self.control_bindings
        ):
            raise ValidationError("control_bindings contains duplicates")
        if self.control_bindings != tuple(
            sorted(self.control_bindings, key=lambda value: value.sha256)
        ):
            raise ValidationError("control_bindings must be canonically ordered")
        bound_control_refs = tuple(
            sorted(
                {
                    binding.ref.sha256: binding.ref for binding in self.control_bindings
                }.values(),
                key=lambda ref: ref.sha256,
            )
        )
        if bound_control_refs != self.control_refs:
            raise ValidationError(
                "control_refs must exactly match control relevance artifacts"
            )
        if any(
            binding.test_point_sha256 not in test_point_hashes
            for binding in self.control_bindings
        ):
            raise ValidationError("control relevance binds an unregistered test point")
        covered_control_points = {
            binding.test_point_sha256 for binding in self.control_bindings
        }
        if covered_control_points != test_point_hashes:
            raise ValidationError("control relevance must cover every test point")
        if type(self.review_state) is not ReviewState:
            raise ValidationError("review_state must be an exact ReviewState")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "admission_ring": ADMISSION_RING,
            "alpha_grid": self.alpha_grid,
            "alpha_max": self.alpha_max,
            "alpha_min": self.alpha_min,
            "calibration_split_ref": self.calibration_split_ref,
            "code_ref": self.code_ref,
            "control_bindings": tuple(
                sorted(self.control_bindings, key=lambda value: value.sha256)
            ),
            "control_refs": tuple(
                sorted(self.control_refs, key=lambda ref: ref.sha256)
            ),
            "corpus_ref": self.corpus_ref,
            "corpus_rights_ref": self.corpus_rights_ref,
            "created_at": self.created_at,
            "disclosure_status": DISCLOSURE_STATUS,
            "drift_check_ref": self.drift_check_ref,
            "drift_state": self.drift_state,
            "dependency_lock_ref": self.dependency_lock_ref,
            "direction_refs": tuple(
                sorted(self.direction_refs, key=lambda ref: ref.sha256)
            ),
            "dtype": self.dtype,
            "expires_at": self.expires_at,
            "fit_method_id": self.fit_method_id,
            "fit_receipt_ref": self.fit_receipt_ref,
            "full_scales": tuple(
                sorted(self.full_scales, key=lambda value: value.test_point_sha256)
            ),
            "ifs_method": self.ifs_method,
            "ifs_percentile": self.ifs_percentile,
            "instruments": tuple(
                sorted(self.instruments, key=lambda item: item.instrument_id)
            ),
            "instrument_implementation_refs": tuple(
                sorted(
                    self.instrument_implementation_refs,
                    key=lambda ref: ref.sha256,
                )
            ),
            "license_status": LICENSE_STATUS,
            "model": self.model,
            "model_artifact_refs": tuple(
                sorted(self.model_artifact_refs, key=lambda ref: ref.sha256)
            ),
            "profile_id": self.profile_id,
            "random_seed": self.random_seed,
            "randomization_method": self.randomization_method,
            "research_status": RESEARCH_STATUS,
            "response_region_method_id": self.response_region_method_id,
            "review_state": self.review_state,
            "runtime_id": self.runtime_id,
            "schema": "CAS-OHM-V1-CALIBRATION-PROFILE",
            "source_refs": tuple(sorted(self.source_refs, key=lambda ref: ref.sha256)),
            "test_points": tuple(
                sorted(self.test_points, key=lambda point: point.sha256)
            ),
            "tolerances": self.tolerances,
            "uncertainty_method_id": self.uncertainty_method_id,
            "valid_from": self.valid_from,
            "validation_split_ref": self.validation_split_ref,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return encode_canonical(self)

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)

    def all_artifact_refs(self) -> tuple[ArtifactRef, ...]:
        full_scale_refs = tuple(
            ref for value in self.full_scales for ref in value.source_refs
        )
        return _unique_refs(
            (
                self.drift_check_ref,
                self.code_ref,
                self.dependency_lock_ref,
                self.corpus_ref,
                self.corpus_rights_ref,
                self.calibration_split_ref,
                self.validation_split_ref,
                self.fit_receipt_ref,
            ),
            self.model_artifact_refs,
            self.instrument_implementation_refs,
            self.direction_refs,
            self.control_refs,
            self.source_refs,
            full_scale_refs,
        )

    def assert_current(self, as_of: datetime) -> None:
        valid_from, _ = _parse_time(self.valid_from, "valid_from")
        expires, _ = _parse_time(self.expires_at, "expires_at")
        if self.review_state is not ReviewState.REVIEWED:
            raise CapabilityError("calibration profile is not REVIEWED")
        if self.drift_state is not DriftState.CURRENT:
            raise CapabilityError(
                f"calibration profile drift state is {self.drift_state.value}"
            )
        if not valid_from <= as_of < expires:
            raise CapabilityError("calibration profile is stale or not yet valid")

    def full_scale_for(self, test_point: TestPointIdentity | str) -> FullScaleValue:
        digest = (
            test_point.sha256 if type(test_point) is TestPointIdentity else test_point
        )
        require_sha256(digest, "test_point_sha256")
        for full_scale in self.full_scales:
            if full_scale.test_point_sha256 == digest:
                return full_scale
        raise ValidationError("test point is not registered in this profile")

    def test_point_registered(self, test_point: TestPointIdentity | str) -> bool:
        digest = (
            test_point.sha256 if type(test_point) is TestPointIdentity else test_point
        )
        return any(point.sha256 == digest for point in self.test_points)

    def instrument_registered(self, instrument: InstrumentIdentity) -> bool:
        return any(candidate == instrument for candidate in self.instruments)


@dataclass(frozen=True, slots=True)
class OperationContext:
    profile: CalibrationProfile
    evidence: EvidenceRegistry
    authority: TrustedCapabilityAuthority
    attestations: tuple[CapabilityAttestation, ...]
    replay_as_of: str
    current_clock_receipt: CurrentClockReceipt | None = None
    _profile_snapshot_sha256: str = field(init=False, repr=False, compare=False)
    _manifest_snapshot_sha256: str = field(init=False, repr=False, compare=False)
    _attestation_snapshot_sha256s: tuple[str, ...] = field(
        init=False, repr=False, compare=False
    )
    _replay_as_of_snapshot: str = field(init=False, repr=False, compare=False)
    _clock_receipt_snapshot_sha256: str | None = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if type(self.profile) is not CalibrationProfile:
            raise ValidationError("profile must be an exact CalibrationProfile")
        if type(self.evidence) is not EvidenceRegistry:
            raise ValidationError("evidence must be an exact EvidenceRegistry")
        if type(self.authority) is not TrustedCapabilityAuthority:
            raise ValidationError(
                "authority must be an exact TrustedCapabilityAuthority"
            )
        if type(self.attestations) is not tuple or any(
            type(value) is not CapabilityAttestation for value in self.attestations
        ):
            raise ValidationError(
                "attestations must contain CapabilityAttestation values"
            )
        capabilities = [value.capability for value in self.attestations]
        if len(capabilities) != len(set(capabilities)):
            raise ValidationError("attestations contains duplicate capabilities")
        replay_as_of, canonical_as_of = _parse_time(self.replay_as_of, "replay_as_of")
        object.__setattr__(self, "replay_as_of", canonical_as_of)
        if (
            self.current_clock_receipt is not None
            and type(self.current_clock_receipt) is not CurrentClockReceipt
        ):
            raise ValidationError(
                "current_clock_receipt must be an exact CurrentClockReceipt"
            )
        self.evidence.revalidate_all()
        manifest_artifact = self.evidence.artifact_for(self.authority.manifest_ref)
        if manifest_artifact.payload != self.authority.manifest.canonical_bytes:
            raise ValidationError("authority manifest evidence bytes do not match")
        self.profile.assert_current(replay_as_of)
        self.evidence.require_refs(self.profile.all_artifact_refs())
        self.evidence.require_refs(
            tuple(attestation.evidence_ref for attestation in self.attestations)
        )
        if self.current_clock_receipt is not None:
            receipt = self.current_clock_receipt
            if receipt.authority_manifest_sha256 != self.authority.manifest.sha256:
                raise ValidationError("clock receipt binds another authority manifest")
            self.authority.verify_current_clock_receipt(receipt, self.evidence)
        object.__setattr__(self, "_profile_snapshot_sha256", self.profile.sha256)
        object.__setattr__(
            self, "_manifest_snapshot_sha256", self.authority.manifest.sha256
        )
        object.__setattr__(
            self,
            "_attestation_snapshot_sha256s",
            tuple(attestation.sha256 for attestation in self.attestations),
        )
        object.__setattr__(self, "_replay_as_of_snapshot", self.replay_as_of)
        object.__setattr__(
            self,
            "_clock_receipt_snapshot_sha256",
            self.current_clock_receipt.sha256
            if self.current_clock_receipt is not None
            else None,
        )

    def revalidate_context(self) -> None:
        if (
            type(self.profile) is not CalibrationProfile
            or type(self.evidence) is not EvidenceRegistry
            or type(self.authority) is not TrustedCapabilityAuthority
            or type(self.attestations) is not tuple
            or any(
                type(attestation) is not CapabilityAttestation
                for attestation in self.attestations
            )
        ):
            raise ValidationError("operation context types changed after admission")
        self.evidence.revalidate_all()
        if self.replay_as_of != self._replay_as_of_snapshot:
            raise ValidationError("replay time changed after context admission")
        if self.profile.sha256 != self._profile_snapshot_sha256:
            raise ValidationError("calibration profile changed after context admission")
        if (
            self.authority.manifest.sha256 != self._manifest_snapshot_sha256
            or self.authority.manifest_ref.sha256 != self._manifest_snapshot_sha256
        ):
            raise ValidationError("authority manifest changed after context admission")
        if tuple(attestation.sha256 for attestation in self.attestations) != (
            self._attestation_snapshot_sha256s
        ):
            raise ValidationError("attestations changed after context admission")
        if self.current_clock_receipt is None:
            current_clock_digest = None
        elif type(self.current_clock_receipt) is CurrentClockReceipt:
            current_clock_digest = self.current_clock_receipt.sha256
        else:
            raise ValidationError("clock receipt type changed after context admission")
        if current_clock_digest != self._clock_receipt_snapshot_sha256:
            raise ValidationError("clock receipt changed after context admission")
        if self.current_clock_receipt is not None:
            self.authority.verify_current_clock_receipt(
                self.current_clock_receipt, self.evidence
            )
        manifest_artifact = self.evidence.artifact_for(self.authority.manifest_ref)
        if manifest_artifact.payload != self.authority.manifest.canonical_bytes:
            raise ValidationError("authority manifest evidence changed")

    @property
    def replay_as_of_datetime(self) -> datetime:
        return _parse_time(self.replay_as_of, "replay_as_of")[0]

    @property
    def as_of(self) -> str:
        """Historical replay-time alias; it never establishes wall-clock trust."""

        return self.replay_as_of

    @property
    def as_of_datetime(self) -> datetime:
        return self.replay_as_of_datetime

    @property
    def authenticated_current(self) -> bool:
        """The isolated candidate has no admitted external trust/time authority."""

        return False

    def authentication_reasons(
        self, capability: Capability | None = None
    ) -> tuple[str, ...]:
        self.revalidate_context()
        reasons = ["EXTERNAL_AUTHORITY_NOT_ADMITTED"]
        if self.current_clock_receipt is None:
            reasons.append("TRUSTED_CURRENT_CLOCK_RECEIPT_MISSING")
        else:
            reasons.append("CLOCK_RECEIPT_IS_INTEGRITY_ONLY")
        if capability is not None:
            try:
                self.require_integrity_attestation(capability)
            except (CapabilityError, ValidationError):
                reasons.append(f"CAPABILITY_INTEGRITY_INVALID:{capability.value}")
        return tuple(sorted(set(reasons)))

    def require_integrity_attestation(
        self, capability: Capability
    ) -> CapabilityAttestation:
        if type(capability) is not Capability:
            raise ValidationError("capability must be an exact Capability")
        self.revalidate_context()
        if self.authority.trust_mode is not TrustMode.INTEGRITY_CONFIGURATION:
            raise CapabilityError("no capability integrity configuration is present")
        for attestation in self.attestations:
            if attestation.capability is capability:
                self.authority.verify(
                    attestation,
                    self.profile.sha256,
                    self.evidence,
                    self.replay_as_of_datetime,
                )
                return attestation
        raise CapabilityError(
            f"no integrity-validated {capability.value} attestation is present"
        )

    def require_capability(self, capability: Capability) -> CapabilityAttestation:
        self.require_integrity_attestation(capability)
        raise CapabilityError(
            "authenticated capability is unavailable: external authority and "
            "trusted current-clock admission are not implemented"
        )

    def operation_binding(
        self,
        capability: Capability | None,
        *,
        require_integrity: bool,
    ) -> OperationBinding:
        self.revalidate_context()
        if capability is not None and require_integrity:
            self.require_integrity_attestation(capability)
        state = (
            AuthorizationState.UNAUTHENTICATED_STRUCTURAL
            if self.authority.trust_mode is TrustMode.STRUCTURAL_RESEARCH_ONLY
            else AuthorizationState.UNAUTHENTICATED_INTEGRITY
        )
        return OperationBinding(
            self.authority.manifest.sha256,
            tuple(sorted(attestation.sha256 for attestation in self.attestations)),
            capability,
            self.authority.trust_mode,
            state,
            self.replay_as_of,
            self.current_clock_receipt.sha256
            if self.current_clock_receipt is not None
            else None,
            self.profile.runtime_id,
            COVARIANCE_LIMITATION,
            self.profile.dependency_lock_ref,
            self.profile.code_ref,
        )

    def validate_operation_binding(self, binding: OperationBinding) -> None:
        if type(binding) is not OperationBinding:
            raise ValidationError("operation binding must be exact OperationBinding")
        expected = self.operation_binding(
            binding.capability,
            require_integrity=False,
        )
        if binding != expected:
            raise ValidationError("operation binding does not match current context")

    def validate_measurement(self, measurement: MeasurementValue) -> None:
        self.revalidate_context()
        if type(measurement) is not MeasurementValue:
            raise ValidationError("value must be an exact MeasurementValue")
        provenance = measurement.provenance
        if provenance.calibration_profile_sha256 != self.profile.sha256:
            raise ValidationError("measurement binds a different calibration profile")
        if provenance.test_point is None or not self.profile.test_point_registered(
            provenance.test_point
        ):
            raise ValidationError("measurement must bind a registered test point")
        if provenance.instrument is not None and not self.profile.instrument_registered(
            provenance.instrument
        ):
            raise ValidationError("measurement binds an unregistered instrument")
        if measurement.measurement_kind is not MeasurementKind.DESIGN_VALUE:
            if provenance.control_refs != self.profile.control_refs:
                raise ValidationError(
                    "measurement controls do not equal the profile control set"
                )
            if provenance.control_bindings != self.profile.control_bindings:
                raise ValidationError(
                    "measurement control relevance does not match the profile"
                )
        if provenance.operation_binding is not None:
            self.validate_operation_binding(provenance.operation_binding)
        refs = (
            provenance.source_refs
            + provenance.raw_artifact_refs
            + provenance.control_refs
        )
        if provenance.dataset_split_ref is not None:
            refs += (provenance.dataset_split_ref,)
        self.evidence.require_refs(refs)
        self.evidence.require_parents(provenance.derivation_parents)


class Q4Band(str, Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


@dataclass(frozen=True, slots=True)
class ExactRatio:
    numerator: Decimal
    denominator: Decimal
    scale: Decimal

    def __post_init__(self) -> None:
        numerator = require_decimal(self.numerator, "numerator")
        denominator = require_decimal(self.denominator, "denominator")
        scale = require_decimal(self.scale, "scale")
        if numerator < 0 or denominator <= 0 or scale <= 0:
            raise ValidationError(
                "exact normalized ratio requires numerator >= 0 and positive "
                "denominator/scale"
            )

    @property
    def fraction(self) -> Fraction:
        return (
            Fraction(self.numerator) * Fraction(self.scale) / Fraction(self.denominator)
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "denominator": self.denominator,
            "numerator": self.numerator,
            "scale": self.scale,
        }


_NORMALIZED_FLOW_TOKEN = object()


@dataclass(frozen=True, slots=True)
class NormalizedFlow:
    q10: MeasurementValue
    overload_ratio: MeasurementValue
    exact_q10: ExactRatio
    _factory_token: InitVar[object] = None

    def __post_init__(self, _factory_token: object) -> None:
        if _factory_token is not _NORMALIZED_FLOW_TOKEN:
            raise ValidationError("normalized-flow results are factory-only")
        if self.q10.quantity_kind is not QuantityKind.NORMALIZED_FLOW:
            raise ValidationError("q10 must be NORMALIZED_FLOW")
        if self.overload_ratio.quantity_kind is not QuantityKind.OVERLOAD_RATIO:
            raise ValidationError("overload_ratio must be OVERLOAD_RATIO")
        if type(self.exact_q10) is not ExactRatio:
            raise ValidationError("exact_q10 must be an exact ExactRatio")
        if self.exact_q10.scale != Decimal("10"):
            raise ValidationError("exact_q10 must use the fixed Q10 scale")
        with arithmetic_context():
            expected_ratio = self.exact_q10.numerator / self.exact_q10.denominator
            expected_q10 = min(Decimal("10"), self.exact_q10.scale * expected_ratio)
        if (
            self.q10.value != expected_q10
            or self.overload_ratio.value != expected_ratio
        ):
            raise ValidationError(
                "normalized display values do not match the exact ratio identity"
            )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "exact_q10": self.exact_q10,
            "overload_ratio": self.overload_ratio,
            "q10": self.q10,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


def q4_band(normalized: NormalizedFlow) -> Q4Band:
    if type(normalized) is not NormalizedFlow:
        raise ValidationError(
            "q4_band requires a NormalizedFlow with exact pre-rounding identity"
        )
    value = normalized.exact_q10.fraction
    if value < Fraction(5, 2):
        return Q4Band.Q1
    if value < Fraction(5, 1):
        return Q4Band.Q2
    if value < Fraction(15, 2):
        return Q4Band.Q3
    return Q4Band.Q4


def _ratio_uncertainty(
    numerator: MeasurementValue,
    denominator: FullScaleValue,
    scale: Decimal,
    unit: UnitKind,
    method_id: str,
    clip_upper: Decimal | None = None,
) -> Uncertainty:
    if numerator.uncertainty is None:
        raise ValidationError("normalization requires raw-flow uncertainty")
    n_unc = numerator.uncertainty
    d_unc = denominator.uncertainty
    with arithmetic_context():
        lower = scale * n_unc.lower / d_unc.upper
        upper = scale * n_unc.upper / d_unc.lower
        value = scale * numerator.value / denominator.value
        term_n = scale * n_unc.standard_uncertainty / denominator.value
        term_d = (
            scale
            * numerator.value
            * d_unc.standard_uncertainty
            / (denominator.value * denominator.value)
        )
        standard = (term_n * term_n + term_d * term_d).sqrt()
        if clip_upper is not None:
            lower = min(clip_upper, lower)
            upper = min(clip_upper, upper)
            value = min(clip_upper, value)
    return Uncertainty(
        unit,
        standard,
        max(Decimal("0"), lower),
        max(value, upper),
        min(n_unc.confidence_level, d_unc.confidence_level),
        method_id,
    )


def normalize_flow(
    context: OperationContext,
    raw_flow: MeasurementValue,
    test_point: TestPointIdentity,
) -> NormalizedFlow:
    context.validate_measurement(raw_flow)
    if (
        raw_flow.quantity_kind is not QuantityKind.FLOW_MAGNITUDE
        or raw_flow.unit is not UnitKind.ACTIVATION
    ):
        raise ValidationError("raw_flow must be FLOW_MAGNITUDE in ACTIVATION units")
    if raw_flow.measurement_kind is not MeasurementKind.INSTRUMENTED:
        raise ValidationError("normalization requires an instrumented raw flow")
    if raw_flow.sample_size is None:
        raise ValidationError("normalization requires a recorded raw-flow sample size")
    if raw_flow.provenance.test_point != test_point:
        raise ValidationError("raw_flow test point mismatch")
    full_scale = context.profile.full_scale_for(test_point)
    context.evidence.object_for(
        type(full_scale).__module__ + "." + type(full_scale).__qualname__,
        full_scale.sha256,
    )
    exact = ExactRatio(raw_flow.value, full_scale.value, Decimal("10"))
    with arithmetic_context():
        ratio = raw_flow.value / full_scale.value
        q_value = min(Decimal("10"), Decimal("10") * ratio)
    sources = _unique_refs(raw_flow.provenance.source_refs, full_scale.source_refs)
    operation_binding = context.operation_binding(None, require_integrity=False)
    provenance = FieldProvenance(
        source_refs=sources,
        method_id="CAS-OHM-V1-NORMALIZE-I-FS",
        calibration_profile_sha256=context.profile.sha256,
        instrument=raw_flow.provenance.instrument,
        test_point=test_point,
        raw_artifact_refs=raw_flow.provenance.raw_artifact_refs,
        control_refs=context.profile.control_refs,
        control_bindings=context.profile.control_bindings,
        dataset_split_ref=raw_flow.provenance.dataset_split_ref,
        derivation_parents=(
            parent_ref("raw_flow", 0, raw_flow),
            parent_ref("full_scale", 1, full_scale),
        ),
        operation_binding=operation_binding,
    )
    q_uncertainty = _ratio_uncertainty(
        raw_flow,
        full_scale,
        Decimal("10"),
        UnitKind.Q10,
        context.profile.uncertainty_method_id,
        Decimal("10"),
    )
    ratio_uncertainty = _ratio_uncertainty(
        raw_flow,
        full_scale,
        Decimal("1"),
        UnitKind.DIMENSIONLESS,
        context.profile.uncertainty_method_id,
    )
    q10 = MeasurementValue(
        "I_Q",
        QuantityKind.NORMALIZED_FLOW,
        q_value,
        UnitKind.Q10,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        q_uncertainty,
        raw_flow.sample_size,
    )
    overload = MeasurementValue(
        "lambda",
        QuantityKind.OVERLOAD_RATIO,
        ratio,
        UnitKind.DIMENSIONLESS,
        MeasurementKind.MODEL_DERIVED,
        provenance,
        ratio_uncertainty,
        raw_flow.sample_size,
    )
    return NormalizedFlow(q10, overload, exact, _NORMALIZED_FLOW_TOKEN)
