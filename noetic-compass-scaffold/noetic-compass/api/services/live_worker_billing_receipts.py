"""Verify signed live-worker accelerator measurements before billing.

The worker, rather than the API or a planner, measures the real CUDA interval.
It signs one canonical receipt that binds the tenant, billing account, logical
run, worker, infrastructure provider, model, and exact time window.  This
verifier is intentionally strict: an unknown field, stale receipt, mismatched
identity, non-CUDA accelerator, or invalid signature is refused before a
``FleetUsageMeasurement`` can reach the durable billing outbox.

Replay safety is completed by ``BillingReconciliationStore``: the canonical
receipt digest and the semantic measurement identity are each globally bound
before the tenant outbox record is created.  An exact replay is idempotent;
another nonce/signature for the same measurement cannot create a second usage
record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import re
from typing import Mapping

from api.services.billing_reconciliation import FleetUsageMeasurement


LIVE_WORKER_MEASUREMENT_RECEIPT_SCHEMA_VERSION = (
    "cas_harness_live_worker_measurement_receipt.v1"
)
MAX_LIVE_WORKER_RECEIPT_BYTES = 16_384
MAX_LIVE_WORKER_MEASUREMENT_SPAN = timedelta(hours=1)
MAX_RECEIPT_ISSUANCE_LAG = timedelta(minutes=1)
MAX_RECEIPT_CLOCK_SKEW = timedelta(minutes=5)

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,200}$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SIGNATURE_RE = re.compile(r"^hmac-sha256:([0-9a-f]{64})$")
_PREDICTABLE_KEY_MARKERS = (
    "change-me",
    "changeme",
    "default",
    "example",
    "not-a-secret",
    "placeholder",
    "sample-secret",
    "test-secret",
)

_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "key_id",
        "issuer",
        "tenant_id",
        "billing_account_id",
        "run_id",
        "worker_id",
        "provider_id",
        "model_id",
        "accelerator_type",
        "accelerator_count",
        "accelerator_milliseconds",
        "measurement_started_at",
        "measurement_ended_at",
        "issued_at",
        "nonce",
        "payload_sha256",
        "signature",
    }
)


class LiveWorkerBillingReceiptError(RuntimeError):
    """A worker measurement receipt is malformed, untrusted, or stale."""


@dataclass(frozen=True, slots=True)
class VerifiedLiveWorkerMeasurement:
    measurement: FleetUsageMeasurement
    provider_id: str
    model_id: str
    receipt_nonce: str


class LiveWorkerMeasurementReceiptVerifier:
    """Verify one exact HMAC receipt from the configured production worker."""

    def __init__(
        self,
        *,
        hmac_key: str,
        key_id: str,
        issuer: str,
        provider_id: str,
        worker_id: str,
        max_age_seconds: int = 300,
    ) -> None:
        self._key = validate_live_worker_receipt_hmac_key(hmac_key)
        self._key_id = _safe_id(key_id, "key_id")
        self._issuer = _safe_id(issuer, "issuer")
        self._provider_id = _safe_id(provider_id, "provider_id")
        self._worker_id = _safe_id(worker_id, "worker_id")
        if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int):
            raise LiveWorkerBillingReceiptError(
                "worker receipt max age must be an integer"
            )
        if max_age_seconds < 30 or max_age_seconds > 3600:
            raise LiveWorkerBillingReceiptError(
                "worker receipt max age must be between 30 and 3600 seconds"
            )
        self._max_age = timedelta(seconds=max_age_seconds)

    def verify(
        self,
        receipt: Mapping[str, object],
        *,
        expected_tenant_id: str,
        expected_billing_account_id: str,
        expected_run_id: str,
        expected_model_id: str,
        now: datetime | None = None,
    ) -> VerifiedLiveWorkerMeasurement:
        if not isinstance(receipt, Mapping) or set(receipt) != _RECEIPT_FIELDS:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt schema is invalid"
            )
        canonical_receipt = _canonical_json(receipt)
        if len(canonical_receipt) > MAX_LIVE_WORKER_RECEIPT_BYTES:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt exceeds the size limit"
            )
        if receipt.get("schema_version") != LIVE_WORKER_MEASUREMENT_RECEIPT_SCHEMA_VERSION:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt schema version is invalid"
            )

        key_id = _safe_id(receipt.get("key_id"), "key_id")
        issuer = _safe_id(receipt.get("issuer"), "issuer")
        tenant_id = _safe_id(receipt.get("tenant_id"), "tenant_id")
        billing_account_id = _safe_id(
            receipt.get("billing_account_id"), "billing_account_id"
        )
        run_id = _safe_id(receipt.get("run_id"), "run_id")
        worker_id = _safe_id(receipt.get("worker_id"), "worker_id")
        provider_id = _safe_id(receipt.get("provider_id"), "provider_id")
        model_id = _model_id(receipt.get("model_id"))
        if receipt.get("accelerator_type") != "cuda":
            raise LiveWorkerBillingReceiptError(
                "only a real CUDA accelerator measurement is billable"
            )
        accelerator_count = _positive_int(
            receipt.get("accelerator_count"), "accelerator_count"
        )
        if accelerator_count > 128:
            raise LiveWorkerBillingReceiptError("accelerator_count exceeds 128")
        accelerator_milliseconds = _positive_int(
            receipt.get("accelerator_milliseconds"),
            "accelerator_milliseconds",
        )
        started = _normalized_time(
            receipt.get("measurement_started_at"), "measurement_started_at"
        )
        ended = _normalized_time(
            receipt.get("measurement_ended_at"), "measurement_ended_at"
        )
        issued = _normalized_time(receipt.get("issued_at"), "issued_at")
        nonce = _bounded_nonce(receipt.get("nonce"))
        payload_sha256 = _sha256(receipt.get("payload_sha256"), "payload_sha256")

        if key_id != self._key_id or issuer != self._issuer:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt authority does not match configuration"
            )
        expected_identity = (
            _safe_id(expected_tenant_id, "expected_tenant_id"),
            _safe_id(expected_billing_account_id, "expected_billing_account_id"),
            _safe_id(expected_run_id, "expected_run_id"),
            _model_id(expected_model_id),
        )
        if (
            tenant_id,
            billing_account_id,
            run_id,
            model_id,
        ) != expected_identity:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt contradicts the admitted billing context"
            )
        if worker_id != self._worker_id or provider_id != self._provider_id:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt source does not match configuration"
            )

        started_clock = _parse_time(started)
        ended_clock = _parse_time(ended)
        issued_clock = _parse_time(issued)
        span = ended_clock - started_clock
        if span <= timedelta(0) or span > MAX_LIVE_WORKER_MEASUREMENT_SPAN:
            raise LiveWorkerBillingReceiptError(
                "worker measurement span must be positive and at most one hour"
            )
        max_quantity = int(span.total_seconds() * 1000) * accelerator_count
        if accelerator_milliseconds > max_quantity:
            raise LiveWorkerBillingReceiptError(
                "accelerator milliseconds exceed the signed CUDA time window"
            )
        if not ended_clock <= issued_clock <= ended_clock + MAX_RECEIPT_ISSUANCE_LAG:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt issuance time is outside its run window"
            )
        verification_clock = now or datetime.now(UTC)
        if verification_clock.tzinfo is None:
            raise LiveWorkerBillingReceiptError("verification time must include UTC offset")
        verification_clock = verification_clock.astimezone(UTC)
        if issued_clock > verification_clock + MAX_RECEIPT_CLOCK_SKEW:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt is unreasonably in the future"
            )
        if verification_clock - issued_clock > self._max_age:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt is stale"
            )

        unsigned = dict(receipt)
        signature = str(unsigned.pop("signature", ""))
        claimed_payload_sha256 = str(unsigned.pop("payload_sha256", ""))
        expected_payload_sha256 = hashlib.sha256(_canonical_json(unsigned)).hexdigest()
        if not hmac.compare_digest(claimed_payload_sha256, expected_payload_sha256):
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt payload digest is invalid"
            )
        signature_match = _SIGNATURE_RE.fullmatch(signature)
        if signature_match is None:
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt signature is invalid"
            )
        signed_payload = {**unsigned, "payload_sha256": payload_sha256}
        expected_signature = hmac.new(
            self._key, _canonical_json(signed_payload), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature_match.group(1), expected_signature):
            raise LiveWorkerBillingReceiptError(
                "worker measurement receipt signature is invalid"
            )

        receipt_sha256 = hashlib.sha256(canonical_receipt).hexdigest()
        measurement = FleetUsageMeasurement(
            tenant_id=tenant_id,
            billing_account_id=billing_account_id,
            run_id=run_id,
            worker_id=worker_id,
            worker_provider_id=provider_id,
            model_id=model_id,
            accelerator_milliseconds=accelerator_milliseconds,
            accelerator_count=accelerator_count,
            measurement_started_at=started,
            measurement_ended_at=ended,
            receipt_sha256=receipt_sha256,
            receipt_schema_version=LIVE_WORKER_MEASUREMENT_RECEIPT_SCHEMA_VERSION,
            receipt_size_bytes=len(canonical_receipt),
            receipt_issuer=issuer,
        )
        return VerifiedLiveWorkerMeasurement(
            measurement=measurement,
            provider_id=provider_id,
            model_id=model_id,
            receipt_nonce=nonce,
        )


def validate_live_worker_receipt_hmac_key(value: object) -> bytes:
    if not isinstance(value, str) or value != value.strip():
        raise LiveWorkerBillingReceiptError(
            "worker receipt HMAC key must be an exact non-empty string"
        )
    encoded = value.encode("utf-8")
    if len(encoded) < 32 or len(encoded) > 4096:
        raise LiveWorkerBillingReceiptError(
            "worker receipt HMAC key must contain 32 to 4096 bytes"
        )
    lowered = value.casefold()
    if any(marker in lowered for marker in _PREDICTABLE_KEY_MARKERS) or len(set(value)) < 8:
        raise LiveWorkerBillingReceiptError(
            "worker receipt HMAC key is predictable"
        )
    return encoded


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LiveWorkerBillingReceiptError(
            "worker measurement receipt is not canonical JSON"
        ) from exc


def _safe_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _SAFE_ID_RE.fullmatch(value) is None:
        raise LiveWorkerBillingReceiptError(f"{field} is not a canonical identifier")
    return value


def _model_id(value: object) -> str:
    if not isinstance(value, str) or _MODEL_ID_RE.fullmatch(value) is None:
        raise LiveWorkerBillingReceiptError("model_id is not canonical")
    return value


def _bounded_nonce(value: object) -> str:
    if not isinstance(value, str) or _NONCE_RE.fullmatch(value) is None:
        raise LiveWorkerBillingReceiptError("receipt nonce is invalid")
    return value


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LiveWorkerBillingReceiptError(f"{field} must be a positive integer")
    return value


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise LiveWorkerBillingReceiptError(f"{field} must be lowercase SHA-256")
    return value


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LiveWorkerBillingReceiptError("receipt timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise LiveWorkerBillingReceiptError("receipt timestamp must include UTC offset")
    return parsed.astimezone(UTC)


def _normalized_time(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise LiveWorkerBillingReceiptError(f"{field} is required")
    parsed = _parse_time(value)
    normalized = parsed.isoformat()
    if value.replace("Z", "+00:00") != normalized:
        raise LiveWorkerBillingReceiptError(f"{field} must be canonical UTC ISO-8601")
    return normalized


__all__ = [
    "LIVE_WORKER_MEASUREMENT_RECEIPT_SCHEMA_VERSION",
    "LiveWorkerBillingReceiptError",
    "LiveWorkerMeasurementReceiptVerifier",
    "VerifiedLiveWorkerMeasurement",
    "validate_live_worker_receipt_hmac_key",
]
