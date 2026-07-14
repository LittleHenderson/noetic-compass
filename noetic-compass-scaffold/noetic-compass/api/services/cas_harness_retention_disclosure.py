"""Canonical, receipt-backed S3 Object Lock retention disclosures.

This module deliberately separates two different statements:

* a *configured target* read from the current process environment; and
* a *verified receipt* for one exact S3 object version.

Only the latter licenses a WORM-committed claim.  Stored booleans and prose are
never trusted: callers reconstruct a disclosure by re-running the strict
receipt predicate below.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import os
import secrets
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ObjectLockMode = Literal["GOVERNANCE", "COMPLIANCE"]
RetentionClaimBasis = Literal["configured_target", "verified_receipt", "unconfigured"]

RETENTION_MODEL = "s3_object_lock_time_bounded"
OBJECT_LOCK_VERIFICATION_SCHEMA = "cas_harness_object_lock_verification.v1"
RETAIN_UNTIL_RULE = "observed_not_before_requested"

_MODE_ENV = "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE"
_DAYS_ENV = "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS"
_VALID_MODES = {"GOVERNANCE", "COMPLIANCE"}
_ATTESTATION_DOMAIN = b"cas-harness-object-lock-receipt-v1\0"
_DEVELOPMENT_ATTESTATION_KEY = secrets.token_bytes(32)


@dataclass(frozen=True)
class ObjectLockPolicyTarget:
    """The process's current Object Lock target, not evidence of a write."""

    configured: bool
    valid: bool
    mode: str | None
    retention_days: int | None
    error: str | None = None


@dataclass(frozen=True)
class ObjectLockReceiptVerification:
    """Canonical result of the one strict Object Lock receipt predicate."""

    verified: bool
    verified_at: str
    evaluated_at: str
    expected: Mapping[str, object]
    observed: Mapping[str, object]
    failure_reasons: tuple[str, ...]
    issuer_attestation: str | None
    schema_version: str = OBJECT_LOCK_VERIFICATION_SCHEMA
    retain_until_rule: str = RETAIN_UNTIL_RULE

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "verified": self.verified,
            "verified_at": self.verified_at,
            "evaluated_at": self.evaluated_at,
            "retain_until_rule": self.retain_until_rule,
            "expected": dict(self.expected),
            "observed": dict(self.observed),
            "failure_reasons": list(self.failure_reasons),
            "issuer_attestation": self.issuer_attestation,
        }


@dataclass(frozen=True)
class ObjectLockRetentionDisclosure:
    """Canonical customer-facing policy or verified-receipt disclosure."""

    provider: str
    claim_basis: RetentionClaimBasis
    policy_configured: bool
    mode: str | None
    retention_days: int | None
    retain_until: str | None
    rolling_from_each_write: bool
    permanent_or_indefinite: Literal[False]
    privileged_operator_override_possible: bool | None
    tamper_evident_on_reverify: bool
    commit_status_requires_verified_receipt: bool
    receipt_verified: bool
    verification_receipt: ObjectLockReceiptVerification | None
    notice: str

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "claim_basis": self.claim_basis,
            "policy_configured": self.policy_configured,
            "mode": self.mode,
            "retention_days": self.retention_days,
            "retain_until": self.retain_until,
            "rolling_from_each_write": self.rolling_from_each_write,
            "permanent_or_indefinite": self.permanent_or_indefinite,
            "privileged_operator_override_possible": (
                self.privileged_operator_override_possible
            ),
            "tamper_evident_on_reverify": self.tamper_evident_on_reverify,
            "commit_status_requires_verified_receipt": (
                self.commit_status_requires_verified_receipt
            ),
            "receipt_verified": self.receipt_verified,
            "verification_receipt": (
                self.verification_receipt.to_dict()
                if self.verification_receipt is not None
                else None
            ),
            "notice": self.notice,
        }


class ObjectLockExpectedReceiptModel(BaseModel):
    """Strict OpenAPI shape for the expected write binding."""

    model_config = ConfigDict(extra="forbid", strict=True)

    bucket: str = Field(min_length=1)
    key: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    content_sha256: str = Field(min_length=64, max_length=64)
    mode: Literal["GOVERNANCE", "COMPLIANCE"]
    retention_days: int = Field(gt=0)
    requested_at: str = Field(min_length=1)
    retain_until: str = Field(min_length=1)

    @field_validator("retention_days", mode="before")
    @classmethod
    def reject_boolean_days(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("retention_days must be a positive non-boolean integer")
        return value


class ObjectLockObservedReceiptModel(BaseModel):
    """Strict OpenAPI shape for facts returned by S3 get/head re-reads."""

    model_config = ConfigDict(extra="forbid", strict=True)

    bucket: str = Field(min_length=1)
    key: str = Field(min_length=1)
    get_version_id: str = Field(min_length=1)
    head_version_id: str = Field(min_length=1)
    content_sha256: str = Field(min_length=64, max_length=64)
    mode: Literal["GOVERNANCE", "COMPLIANCE"]
    retain_until: str = Field(min_length=1)
    reread_verified: Literal[True]


class ObjectLockReceiptVerificationModel(BaseModel):
    """Strict public model for a successful, canonical verifier receipt."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[OBJECT_LOCK_VERIFICATION_SCHEMA]
    verified: Literal[True]
    verified_at: str = Field(min_length=1)
    evaluated_at: str = Field(min_length=1)
    retain_until_rule: Literal[RETAIN_UNTIL_RULE]
    expected: ObjectLockExpectedReceiptModel
    observed: ObjectLockObservedReceiptModel
    failure_reasons: list[str] = Field(default_factory=list, max_length=0)
    issuer_attestation: str = Field(min_length=64, max_length=64)


class ObjectLockExpectedReceiptResultModel(BaseModel):
    """Typed verifier output, including malformed expected inputs on failure."""

    model_config = ConfigDict(extra="forbid", strict=True)

    bucket: str | None = None
    key: str | None = None
    version_id: str | None = None
    content_sha256: str | None = None
    mode: str | None = None
    retention_days: int | None = None
    requested_at: str | None = None
    retain_until: str | None = None


class ObjectLockObservedReceiptResultModel(BaseModel):
    """Typed verifier output, including absent S3 facts on failure."""

    model_config = ConfigDict(extra="forbid", strict=True)

    bucket: str | None = None
    key: str | None = None
    get_version_id: str | None = None
    head_version_id: str | None = None
    content_sha256: str | None = None
    mode: str | None = None
    retain_until: str | None = None
    reread_verified: bool


class ObjectLockReceiptVerificationResultModel(BaseModel):
    """Strictly shaped verifier result suitable for hash-check responses."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[OBJECT_LOCK_VERIFICATION_SCHEMA]
    verified: bool
    verified_at: str = Field(min_length=1)
    evaluated_at: str = Field(min_length=1)
    retain_until_rule: Literal[RETAIN_UNTIL_RULE]
    expected: ObjectLockExpectedReceiptResultModel
    observed: ObjectLockObservedReceiptResultModel
    failure_reasons: list[str]
    issuer_attestation: str | None = Field(default=None, min_length=64, max_length=64)


class ObjectLockRetentionDisclosureModel(BaseModel):
    """Strict OpenAPI/API representation; callers feed it canonical data only."""

    model_config = ConfigDict(extra="forbid", strict=True)

    provider: Literal["Amazon S3 Object Lock"]
    claim_basis: RetentionClaimBasis
    policy_configured: bool
    mode: Literal["GOVERNANCE", "COMPLIANCE"] | None
    retention_days: int | None = Field(default=None, gt=0)
    retain_until: str | None = None
    rolling_from_each_write: bool
    permanent_or_indefinite: Literal[False]
    privileged_operator_override_possible: bool | None
    tamper_evident_on_reverify: bool
    commit_status_requires_verified_receipt: Literal[True]
    receipt_verified: bool
    verification_receipt: ObjectLockReceiptVerificationModel | None = None
    notice: str

    @field_validator("retention_days", mode="before")
    @classmethod
    def reject_boolean_days(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("retention_days must be a positive non-boolean integer")
        return value

    @model_validator(mode="after")
    def enforce_claim_consistency(self) -> "ObjectLockRetentionDisclosureModel":
        if self.receipt_verified:
            if self.claim_basis != "verified_receipt" or self.verification_receipt is None:
                raise ValueError("receipt_verified requires a structured verified receipt")
            if not self.tamper_evident_on_reverify:
                raise ValueError(
                    "verified receipt must remain tamper-evident on reverify"
                )
            rebuilt = revalidate_object_lock_verification(
                self.verification_receipt.model_dump()
            )
            if rebuilt is None or not rebuilt.verified:
                raise ValueError("structured Object Lock receipt is invalid or expired")
            rebuilt_mode = rebuilt.observed.get("mode")
            rebuilt_days = rebuilt.expected.get("retention_days")
            expected_override = True if rebuilt_mode == "GOVERNANCE" else False
            if not self.policy_configured:
                raise ValueError("verified receipt requires policy_configured=true")
            if self.mode != rebuilt_mode:
                raise ValueError("disclosure mode does not match verifier receipt")
            if self.retention_days != rebuilt_days:
                raise ValueError("disclosure retention_days does not match verifier receipt")
            if self.retain_until != rebuilt.observed.get("retain_until"):
                raise ValueError("disclosure retain_until does not match verifier receipt")
            if not self.rolling_from_each_write:
                raise ValueError("verified receipt must be rolling from its write request")
            if self.privileged_operator_override_possible is not expected_override:
                raise ValueError("disclosure override boundary does not match Object Lock mode")
        elif self.claim_basis == "verified_receipt" or self.verification_receipt is not None:
            raise ValueError("unverified disclosure cannot carry a verifier receipt")
        elif self.tamper_evident_on_reverify:
            raise ValueError(
                "tamper-evident revalidation requires an authenticated live receipt"
            )
        elif self.claim_basis == "configured_target":
            expected_override = True if self.mode == "GOVERNANCE" else False
            if (
                not self.policy_configured
                or self.mode not in _VALID_MODES
                or self.retention_days is None
                or not self.rolling_from_each_write
            ):
                raise ValueError("configured_target fields are internally inconsistent")
            if self.privileged_operator_override_possible is not expected_override:
                raise ValueError("configured target override boundary does not match mode")
        elif self.claim_basis == "unconfigured":
            if (
                self.policy_configured
                or self.mode is not None
                or self.retention_days is not None
                or self.rolling_from_each_write
                or self.privileged_operator_override_possible is not None
            ):
                raise ValueError("unconfigured retention disclosure carries policy claims")
        if self.claim_basis != "verified_receipt" and self.retain_until is not None:
            raise ValueError("only a verified receipt may disclose an object deadline")
        return self


def runtime_object_lock_policy_target(
    environ: Mapping[str, str] | None = None,
) -> ObjectLockPolicyTarget:
    """Read and validate the current runtime target without claiming a write."""

    source = os.environ if environ is None else environ
    mode_raw = str(source.get(_MODE_ENV, "")).strip()
    days_raw = str(source.get(_DAYS_ENV, "")).strip()
    configured = bool(mode_raw or days_raw)
    if not configured:
        return ObjectLockPolicyTarget(False, True, None, None)

    mode = mode_raw.upper()
    if mode not in _VALID_MODES:
        return ObjectLockPolicyTarget(
            True,
            False,
            None,
            None,
            f"{_MODE_ENV} must be GOVERNANCE or COMPLIANCE.",
        )
    if not days_raw.isdigit() or int(days_raw) < 1:
        return ObjectLockPolicyTarget(
            True,
            False,
            mode,
            None,
            f"{_DAYS_ENV} must be a positive integer.",
        )
    return ObjectLockPolicyTarget(True, True, mode, int(days_raw))


def retention_model_for_mode(mode: str | None) -> str:
    normalized = _normalize_mode(mode)
    if normalized == "COMPLIANCE":
        return "s3_object_lock_compliance_time_bounded"
    if normalized == "GOVERNANCE":
        return "s3_object_lock_governance_time_bounded"
    return RETENTION_MODEL


def evaluate_object_lock_receipt(
    *,
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
    verified_at: datetime | None = None,
    evaluated_at: datetime | None = None,
) -> ObjectLockReceiptVerification:
    """Evaluate an Object Lock mapping without granting receipt authority.

    This public pure predicate is useful for diagnostics, but deliberately never
    mints the issuer attestation required by WORM promotion.  Serialized or API
    mappings therefore cannot become authority merely by being self-consistent.
    """

    return _evaluate_object_lock_receipt(
        expected=expected,
        observed=observed,
        verified_at=verified_at,
        evaluated_at=evaluated_at,
        mint_issuer_attestation=False,
    )


def _issue_live_s3_object_lock_receipt(
    *,
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
    verified_at: datetime | None = None,
    evaluated_at: datetime | None = None,
    _allow_ephemeral_for_tests: bool = False,
) -> ObjectLockReceiptVerification:
    """Private issuer called only immediately after exact-VersionId S3 get/head.

    The two trusted S3 adapters are the authority boundary.  Code review keeps
    this private issuer adjacent to their SDK reads; ordinary product callers
    and stored data use :func:`evaluate_object_lock_receipt`, which cannot mint.
    Failed predicates are never attested.
    """

    result = _evaluate_object_lock_receipt(
        expected=expected,
        observed=observed,
        verified_at=verified_at,
        evaluated_at=evaluated_at,
        mint_issuer_attestation=False,
    )
    if not result.verified:
        return result
    return _result_with_attestation(
        result,
        _mint_receipt_attestation(
            result,
            require_stable_key=not _allow_ephemeral_for_tests,
        ),
    )


def _evaluate_object_lock_receipt(
    *,
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
    verified_at: datetime | None,
    evaluated_at: datetime | None,
    mint_issuer_attestation: bool,
) -> ObjectLockReceiptVerification:
    """Evaluate the canonical predicate, optionally minting trusted authority."""

    now = datetime.now(UTC)
    original_at = _aware_utc(verified_at) if verified_at is not None else now
    original_at_invalid = verified_at is not None and original_at is None
    if original_at is None:
        original_at = now
    evaluation_at = _aware_utc(evaluated_at) if evaluated_at is not None else now
    evaluation_at_invalid = evaluated_at is not None and evaluation_at is None
    if evaluation_at is None:
        evaluation_at = now

    expected_bucket = _text(expected.get("bucket"))
    expected_key = _text(expected.get("key"))
    expected_version = _text(expected.get("version_id"))
    expected_hash = _sha256(expected.get("content_sha256"))
    expected_mode = _normalize_mode(expected.get("mode"))
    expected_days = _positive_days(expected.get("retention_days"))
    requested_at = _aware_utc(expected.get("requested_at"))
    expected_until = _aware_utc(expected.get("retain_until"))

    observed_bucket = _text(observed.get("bucket"))
    observed_key = _text(observed.get("key"))
    get_version = _text(observed.get("get_version_id"))
    head_version = _text(observed.get("head_version_id"))
    observed_hash = _sha256(observed.get("content_sha256"))
    observed_mode = _normalize_mode(observed.get("mode"))
    observed_until = _aware_utc(observed.get("retain_until"))

    reasons: list[str] = []
    if original_at_invalid:
        reasons.append("verified_at must be timezone-aware UTC")
    if evaluation_at_invalid:
        reasons.append("evaluated_at must be timezone-aware UTC")
    if evaluation_at < original_at:
        reasons.append("evaluated_at predates the original verification")
    if observed.get("reread_verified") is not True:
        reasons.append("S3 get/head re-read was not completed")
    if not expected_bucket or observed_bucket != expected_bucket:
        reasons.append("bucket binding mismatch")
    if not expected_key or observed_key != expected_key:
        reasons.append("object key binding mismatch")
    if (
        not expected_version
        or expected_version.startswith("stub-")
        or get_version != expected_version
        or head_version != expected_version
    ):
        reasons.append("object version binding mismatch")
    if not expected_hash or observed_hash != expected_hash:
        reasons.append("content sha256 binding mismatch")
    if expected_mode not in _VALID_MODES or observed_mode != expected_mode:
        reasons.append("Object Lock mode mismatch")
    if expected_days is None:
        reasons.append("retention_days must be a positive non-boolean integer")
    if requested_at is None:
        reasons.append("retention requested_at must be timezone-aware UTC")
    if expected_until is None:
        reasons.append("requested retain_until must be timezone-aware UTC")
    if requested_at is not None and original_at < requested_at:
        reasons.append("verified_at predates the Object Lock write request")
    if (
        requested_at is not None
        and expected_days is not None
        and expected_until is not None
        and expected_until < requested_at + timedelta(days=expected_days)
    ):
        reasons.append(
            "requested retain_until is shorter than the full retention_days window"
        )
    if observed_until is None:
        reasons.append("observed retain_until must be timezone-aware UTC")
    elif observed_until <= evaluation_at:
        reasons.append("observed retain_until is expired")
    if (
        expected_until is not None
        and observed_until is not None
        and observed_until < expected_until
    ):
        reasons.append("observed retain_until was shortened below the write request")

    canonical_expected: dict[str, object] = {
        "bucket": expected_bucket,
        "key": expected_key,
        "version_id": expected_version,
        "content_sha256": expected_hash,
        "mode": expected_mode,
        "retention_days": expected_days,
        "requested_at": _datetime_text(requested_at),
        "retain_until": _datetime_text(expected_until),
    }
    canonical_observed: dict[str, object] = {
        "bucket": observed_bucket,
        "key": observed_key,
        "get_version_id": get_version,
        "head_version_id": head_version,
        "content_sha256": observed_hash,
        "mode": observed_mode,
        "retain_until": _datetime_text(observed_until),
        "reread_verified": observed.get("reread_verified") is True,
    }
    result = ObjectLockReceiptVerification(
        verified=not reasons,
        verified_at=original_at.isoformat(),
        evaluated_at=evaluation_at.isoformat(),
        expected=canonical_expected,
        observed=canonical_observed,
        failure_reasons=tuple(reasons),
        issuer_attestation=None,
    )
    if not mint_issuer_attestation or not result.verified:
        return result
    return _result_with_attestation(result, _mint_receipt_attestation(result))


def revalidate_object_lock_verification(
    value: ObjectLockReceiptVerification | Mapping[str, Any] | None,
    *,
    expected: Mapping[str, Any] | None = None,
    evaluated_at: datetime | None = None,
) -> ObjectLockReceiptVerification | None:
    """Revalidate authenticated receipt data without trusting stored claims.

    A self-consistent mapping is insufficient.  Promotion requires the issuer
    attestation minted by the private live-S3 issuer at the trusted exact-version
    re-read boundary.  Expiry and any caller-supplied expected binding are
    then evaluated afresh without changing the original ``verified_at``.
    """

    if isinstance(value, ObjectLockReceiptVerification):
        raw = value.to_dict()
    elif isinstance(value, Mapping):
        raw = value
    else:
        return None
    if raw.get("schema_version") != OBJECT_LOCK_VERIFICATION_SCHEMA:
        return None
    if raw.get("retain_until_rule") != RETAIN_UNTIL_RULE:
        return None
    raw_expected = raw.get("expected")
    raw_observed = raw.get("observed")
    if not isinstance(raw_expected, Mapping) or not isinstance(raw_observed, Mapping):
        return None
    original_verified_at = _aware_utc(raw.get("verified_at"))
    previous_evaluated_at = _aware_utc(raw.get("evaluated_at"))
    if original_verified_at is None or previous_evaluated_at is None:
        return None
    # Reconstruct the originally issued canonical receipt without invoking the
    # issuer path.  Only a successful original result with a valid server MAC
    # is allowed to carry authority out of serialized storage/API data.
    original = _evaluate_object_lock_receipt(
        expected=raw_expected,
        observed=raw_observed,
        verified_at=original_verified_at,
        evaluated_at=previous_evaluated_at,
        mint_issuer_attestation=False,
    )
    provided_attestation = _sha256(raw.get("issuer_attestation"))
    if (
        raw.get("verified") is not True
        or raw.get("failure_reasons") not in ([], ())
        or not original.verified
        or provided_attestation is None
        or not hmac.compare_digest(
            provided_attestation, _mint_receipt_attestation(original)
        )
    ):
        return None

    reevaluated = _evaluate_object_lock_receipt(
        expected=expected if expected is not None else raw_expected,
        observed=raw_observed,
        verified_at=original_verified_at,
        evaluated_at=evaluated_at or datetime.now(UTC),
        mint_issuer_attestation=False,
    )
    # The original MAC may be preserved only when the effective expected
    # binding canonicalizes to the attested one.  Mismatched overrides return
    # an unauthenticated failure and can never be persisted as verified proof.
    if reevaluated.expected != original.expected:
        return None
    if reevaluated.verified:
        # This is a server-side re-attestation of already authenticated facts at
        # the new evaluation time, not a new live-read claim.  The prior valid
        # MAC is the prerequisite, and the new MAC covers ``evaluated_at`` too.
        return _result_with_attestation(
            reevaluated, _mint_receipt_attestation(reevaluated)
        )
    return reevaluated


def configured_object_lock_retention_disclosure(
    *,
    subject: str,
    environ: Mapping[str, str] | None = None,
) -> ObjectLockRetentionDisclosure:
    """Describe the current configured target without asserting a receipt."""

    target = runtime_object_lock_policy_target(environ)
    if target.configured and target.valid:
        return _build_disclosure(
            subject=subject,
            claim_basis="configured_target",
            policy_configured=True,
            mode=target.mode,
            retention_days=target.retention_days,
            retain_until=None,
            verification=None,
            configuration_error=None,
        )
    return _build_disclosure(
        subject=subject,
        claim_basis="unconfigured",
        policy_configured=False,
        mode=None,
        retention_days=None,
        retain_until=None,
        verification=None,
        configuration_error=target.error,
    )


def deployed_governance_retention_disclosure(
    *,
    subject: str,
    receipt_verified: bool = False,
    retain_until: str | None = None,
) -> ObjectLockRetentionDisclosure:
    """Deprecated compatibility alias; it now reads the runtime target.

    Historical callers used a name that implied a fixed deployment.  Keeping
    the import avoids a collection-time break, while deliberately ignoring the
    legacy claim booleans and deadline because they are not structured proof.
    """

    del receipt_verified, retain_until
    return configured_object_lock_retention_disclosure(subject=subject)


def object_lock_retention_disclosure(
    *,
    subject: str,
    mode: str | None = None,
    retention_days: int | None = None,
    retain_until: str | None = None,
    receipt_verified: bool = False,
    verification_receipt: ObjectLockReceiptVerification | Mapping[str, Any] | None = None,
) -> ObjectLockRetentionDisclosure:
    """Build a disclosure, upgrading only from a revalidated structured receipt.

    The legacy scalar arguments remain accepted for compatibility, but they
    carry no authority: ``receipt_verified=True`` alone is powerless and an
    unverified target is always rebuilt from the current runtime environment.
    """

    del receipt_verified
    verification = revalidate_object_lock_verification(verification_receipt)
    if verification is not None and verification.verified:
        observed = verification.observed
        expected = verification.expected
        return _build_disclosure(
            subject=subject,
            claim_basis="verified_receipt",
            policy_configured=True,
            mode=_text(observed.get("mode")),
            retention_days=_positive_days(expected.get("retention_days")),
            retain_until=_text(observed.get("retain_until")),
            verification=verification,
            configuration_error=None,
        )

    # Caller-supplied scalar labels are not deployment authority.  Without a
    # structured receipt the only truthful target is the one read from the
    # current runtime environment.
    del mode, retention_days, retain_until
    return configured_object_lock_retention_disclosure(subject=subject)


def canonical_retention_disclosure(
    value: Mapping[str, Any] | None,
    *,
    subject: str,
    evaluated_at: datetime | None = None,
) -> ObjectLockRetentionDisclosure:
    """Rebuild stored disclosure data; never preserve stored booleans or prose."""

    raw_receipt = value.get("verification_receipt") if isinstance(value, Mapping) else None
    verification = revalidate_object_lock_verification(
        raw_receipt if isinstance(raw_receipt, Mapping) else None,
        evaluated_at=evaluated_at,
    )
    if verification is not None and verification.verified:
        return object_lock_retention_disclosure(
            subject=subject,
            verification_receipt=verification,
        )
    return configured_object_lock_retention_disclosure(subject=subject)


def _build_disclosure(
    *,
    subject: str,
    claim_basis: RetentionClaimBasis,
    policy_configured: bool,
    mode: str | None,
    retention_days: int | None,
    retain_until: str | None,
    verification: ObjectLockReceiptVerification | None,
    configuration_error: str | None,
) -> ObjectLockRetentionDisclosure:
    verified = claim_basis == "verified_receipt" and verification is not None
    if verified:
        opening = (
            f"{subject} has an actual re-read-verified, time-bounded Amazon S3 Object Lock "
            f"{mode} receipt through {retain_until}."
        )
    elif claim_basis == "configured_target":
        opening = (
            f"The configured target for each newly written {subject} object version is "
            f"Amazon S3 Object Lock {mode} for {retention_days} days. This is a target, "
            "not proof that this object was written or retained; "
            "DATA_CAPTURE_WORM_COMMITTED is not asserted."
        )
    else:
        detail = f" Configuration is invalid: {configuration_error}" if configuration_error else ""
        opening = (
            f"No complete, valid Amazon S3 Object Lock target or verified receipt is present "
            f"for {subject}; DATA_CAPTURE_WORM_COMMITTED is not asserted.{detail}"
        )

    window = (
        " Retention is time-bounded, not permanent or indefinite, and expiry does not "
        "promise deletion."
    )
    if mode == "GOVERNANCE":
        override_possible: bool | None = True
        boundary = (
            " An authorized AWS identity with bypass permission can override GOVERNANCE "
            "retention."
        )
    elif mode == "COMPLIANCE":
        override_possible = False
        boundary = (
            " COMPLIANCE retention cannot be shortened or bypassed before its retain-until "
            "date."
        )
    else:
        override_possible = None
        boundary = " No Object Lock mode has been verified."
    verification_notice = (
        " WORM status requires re-verifying the exact bucket, key, S3 version, content "
        "SHA-256, lock mode, and a future retain-until date; acknowledgment or prose alone "
        "is insufficient."
    )

    return ObjectLockRetentionDisclosure(
        provider="Amazon S3 Object Lock",
        claim_basis=claim_basis,
        policy_configured=policy_configured,
        mode=mode,
        retention_days=retention_days,
        retain_until=retain_until if verified else None,
        rolling_from_each_write=retention_days is not None,
        permanent_or_indefinite=False,
        privileged_operator_override_possible=override_possible,
        tamper_evident_on_reverify=verified,
        commit_status_requires_verified_receipt=True,
        receipt_verified=verified,
        verification_receipt=verification if verified else None,
        notice=opening + window + boundary + verification_notice,
    )


def _result_with_attestation(
    result: ObjectLockReceiptVerification,
    issuer_attestation: str,
) -> ObjectLockReceiptVerification:
    return ObjectLockReceiptVerification(
        verified=result.verified,
        verified_at=result.verified_at,
        evaluated_at=result.evaluated_at,
        expected=result.expected,
        observed=result.observed,
        failure_reasons=result.failure_reasons,
        issuer_attestation=issuer_attestation,
        schema_version=result.schema_version,
        retain_until_rule=result.retain_until_rule,
    )


def _mint_receipt_attestation(
    result: ObjectLockReceiptVerification,
    *,
    require_stable_key: bool = False,
) -> str:
    """Authenticate every immutable and time-varying field of a receipt result."""

    payload = {
        "schema_version": result.schema_version,
        "verified": result.verified,
        "verified_at": result.verified_at,
        "evaluated_at": result.evaluated_at,
        "retain_until_rule": result.retain_until_rule,
        "expected": dict(result.expected),
        "observed": dict(result.observed),
        "failure_reasons": list(result.failure_reasons),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hmac.new(
        _receipt_attestation_key(require_stable=require_stable_key),
        encoded,
        hashlib.sha256,
    ).hexdigest()


def require_stable_object_lock_receipt_attestation_key() -> None:
    """Fail before an S3 Object Lock write when durable receipt auth is absent."""

    _receipt_attestation_key(require_stable=True)


def _receipt_attestation_key(*, require_stable: bool = False) -> bytes:
    """Return the server-only MAC key with fail-closed development lifecycle.

    Hosted object storage startup requires a stable, dedicated 32-byte
    ``NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY`` shared by replicas.  We derive a
    domain-separated MAC key from it without persisting or exposing the key.

    An absent or weak development key is never treated as persistent.  Those
    processes use an unpredictable ephemeral key, so serialized receipts fail
    closed after restart.  Production key rotation likewise invalidates existing
    durable receipts; the key must remain unchanged until an explicit keyring or
    migration workflow exists.  The durable verifier authenticates the old MAC
    before any S3 read, so it cannot silently "reissue" after losing that trust.
    """

    from api.config import settings

    configured = settings.object_lock_receipt_attestation_key.encode("utf-8")
    if len(configured) >= 32:
        return hashlib.sha256(_ATTESTATION_DOMAIN + configured).digest()
    if require_stable:
        raise RuntimeError(
            "S3 Object Lock receipts require stable "
            "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY with at least 32 bytes."
        )
    return _DEVELOPMENT_ATTESTATION_KEY


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _normalize_mode(value: object) -> str | None:
    text = _text(value)
    return text.upper() if text is not None else None


def _positive_days(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _sha256(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    normalized = text.lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        return None
    return normalized


def _aware_utc(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _datetime_text(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat() if value is not None else None
