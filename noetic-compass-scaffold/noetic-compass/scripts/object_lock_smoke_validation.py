"""Strict validation for hosted S3 Object Lock smoke receipts.

The verifier response carries a structured, attested receipt.  Operator
smokes must validate that receipt and its exact packet/S3 bindings rather
than treating human-readable ``notes`` as a security predicate.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.parse import parse_qs, unquote, urlparse


OBJECT_LOCK_VERIFICATION_SCHEMA = "cas_harness_object_lock_verification.v1"
OBJECT_LOCK_RETAIN_UNTIL_RULE = "observed_not_before_requested"
MIN_CONFIGURED_RETENTION_DAYS = 31
MIN_REMAINING_RETENTION = timedelta(days=30)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ObjectLockReceiptError(ValueError):
    """Raised when a structured Object Lock receipt is missing or cross-wired."""


def validate_object_lock_receipt(
    anchor: Mapping[str, Any],
    verify_check: Mapping[str, Any],
    *,
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    """Validate active customer-production retention and exact S3 bindings."""

    now = evaluated_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ObjectLockReceiptError("evaluation time must be timezone-aware")
    now = now.astimezone(timezone.utc)

    if anchor.get("status") != "anchored" or anchor.get("mode") != "s3":
        raise ObjectLockReceiptError("anchor is not an anchored S3 object")

    lock_mode = anchor.get("object_lock_mode")
    if lock_mode not in {"GOVERNANCE", "COMPLIANCE"}:
        raise ObjectLockReceiptError("Object Lock mode is not GOVERNANCE or COMPLIANCE")

    retention_days = anchor.get("retention_days")
    if (
        not isinstance(retention_days, int)
        or isinstance(retention_days, bool)
        or retention_days < MIN_CONFIGURED_RETENTION_DAYS
    ):
        raise ObjectLockReceiptError(
            f"configured retention_days must be >= {MIN_CONFIGURED_RETENTION_DAYS}"
        )

    requested_at = _timestamp(anchor.get("retention_requested_at"), "retention_requested_at")
    retain_until = _timestamp(anchor.get("object_lock_retain_until"), "object_lock_retain_until")
    if retain_until < requested_at + timedelta(days=retention_days):
        raise ObjectLockReceiptError("Object Lock receipt is shorter than configured policy")
    if retain_until - now < MIN_REMAINING_RETENTION:
        raise ObjectLockReceiptError("Object Lock has less than 30 days remaining")

    bucket = _string(anchor, "bucket", "anchor")
    key = _string(anchor, "key", "anchor")
    version_id = _string(anchor, "version_id", "anchor")
    manifest_sha = _sha256(anchor.get("manifest_sha256"), "anchor manifest_sha256")
    anchor_uri = _string(anchor, "anchor_uri", "anchor")
    _validate_anchor_uri(anchor_uri, bucket=bucket, key=key, version_id=version_id)

    if (
        verify_check.get("match") is not True
        or verify_check.get("expected") != manifest_sha
        or verify_check.get("actual") != manifest_sha
    ):
        raise ObjectLockReceiptError("verification did not re-read the exact anchor manifest")

    receipt = _mapping(
        verify_check.get("object_lock_verification"),
        "structured Object Lock receipt",
    )
    expected = _mapping(receipt.get("expected"), "Object Lock expected binding")
    observed = _mapping(receipt.get("observed"), "Object Lock observed binding")
    failures = receipt.get("failure_reasons")
    if (
        receipt.get("schema_version") != OBJECT_LOCK_VERIFICATION_SCHEMA
        or receipt.get("retain_until_rule") != OBJECT_LOCK_RETAIN_UNTIL_RULE
        or receipt.get("verified") is not True
        or failures != []
    ):
        raise ObjectLockReceiptError("structured Object Lock receipt is not verified")
    _sha256(receipt.get("issuer_attestation"), "Object Lock issuer_attestation")

    verified_at = _timestamp(receipt.get("verified_at"), "Object Lock verified_at")
    receipt_evaluated_at = _timestamp(receipt.get("evaluated_at"), "Object Lock evaluated_at")
    expected_requested_at = _timestamp(expected.get("requested_at"), "expected requested_at")
    expected_retain_until = _timestamp(expected.get("retain_until"), "expected retain_until")
    observed_retain_until = _timestamp(observed.get("retain_until"), "observed retain_until")

    if verified_at > receipt_evaluated_at or receipt_evaluated_at > now:
        raise ObjectLockReceiptError("structured Object Lock receipt timestamps are invalid")
    if (
        expected.get("bucket") != bucket
        or expected.get("key") != key
        or expected.get("version_id") != version_id
        or expected.get("content_sha256") != manifest_sha
        or expected.get("mode") != lock_mode
        or expected.get("retention_days") != retention_days
        or expected_requested_at != requested_at
        or expected_retain_until != retain_until
        or observed.get("bucket") != bucket
        or observed.get("key") != key
        or observed.get("get_version_id") != version_id
        or observed.get("head_version_id") != version_id
        or observed.get("content_sha256") != manifest_sha
        or observed.get("mode") != lock_mode
        or observed.get("reread_verified") is not True
        or observed_retain_until < retain_until
    ):
        raise ObjectLockReceiptError("structured Object Lock receipt is cross-wired")

    return {
        "mode": lock_mode,
        "retention_days": retention_days,
        "requested_at": requested_at,
        "retain_until": retain_until,
        "remaining": retain_until - now,
        "bucket": bucket,
        "key": key,
        "version_id": version_id,
        "manifest_sha256": manifest_sha,
    }


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ObjectLockReceiptError(f"{name} is missing")
    return value


def _string(value: Mapping[str, Any], field: str, context: str) -> str:
    candidate = value.get(field)
    if not isinstance(candidate, str) or not candidate.strip():
        raise ObjectLockReceiptError(f"{context} {field} is missing")
    return candidate.strip()


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ObjectLockReceiptError(f"{field} is not a lowercase SHA-256 digest")
    return value


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ObjectLockReceiptError(f"{field} is missing")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ObjectLockReceiptError(f"{field} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ObjectLockReceiptError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _validate_anchor_uri(anchor_uri: str, *, bucket: str, key: str, version_id: str) -> None:
    parsed = urlparse(anchor_uri)
    try:
        query = parse_qs(parsed.query, strict_parsing=True)
    except ValueError as exc:
        raise ObjectLockReceiptError("anchor URI query is invalid") from exc
    if (
        parsed.scheme != "s3"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.netloc != bucket
        or unquote(parsed.path.lstrip("/")) != key
        or query != {"versionId": [version_id]}
        or parsed.fragment
    ):
        raise ObjectLockReceiptError("anchor URI is not bound to the exact S3 version")
