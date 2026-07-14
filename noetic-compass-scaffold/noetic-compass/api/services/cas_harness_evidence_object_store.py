"""Tenant-keyed immutable Evidence Packet storage over S3 Object Lock.

The legacy packet writer in :mod:`cas_harness_merged_evidence_packets` is a
single-host JSON file plus JSONL hash log.  That remains the dark/default path
for demos and static reference packets.  Paid account mode can opt into this
module instead: packet bytes are written once to a versioned Object-Lock S3
object, while a shared ``StateStore`` keeps the tenant-scoped packet index and
the concurrency-safe append chain.

The important split is deliberate:

* S3 Object Lock owns immutable packet *bytes* and produces the re-read receipt.
* ``StateStore`` owns the small searchable index and hash-log head/entries.
* a request-scoped tenant context makes every read and write tenant-keyed.

No configuration silently upgrades the legacy path.  The repository is absent
until startup explicitly builds it, and every shared-mode write fails unless
the packet object is re-read with the expected hash, version, lock mode, and a
future retention deadline.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
import time
from typing import Any, Iterator, Mapping, Protocol, runtime_checkable
from urllib.parse import parse_qs, quote, unquote, urlparse
import uuid

from api.services.production.state_substrate import (
    LedgerRecord,
    LeaseHeld,
    StateStore,
    VersionConflict,
)
from api.services.production.worm_writes import LockReceipt, RetentionPolicy
from api.services.cas_harness_retention_disclosure import (
    _issue_live_s3_object_lock_receipt,
    require_stable_object_lock_receipt_attestation_key,
    revalidate_object_lock_verification,
    runtime_object_lock_policy_target,
)


PACKET_INDEX_KIND = "evidence_packet_object_index"
HASH_LOG_ENTRY_KIND = "evidence_packet_hash_log_entry"
HASH_LOG_HEAD_KIND = "evidence_packet_hash_log_head"
HASH_LOG_TRACE_KIND = "evidence_packet_hash_log_trace"
HASH_LOG_WORM_RECEIPT_KIND = "evidence_packet_hash_log_worm_receipt"
PUBLICATION_INTENT_KIND = "evidence_packet_publication_intent"


class EvidenceObjectStoreError(RuntimeError):
    """Base error for fail-closed shared Evidence Packet persistence."""


class EvidenceObjectStoreUnavailable(EvidenceObjectStoreError):
    """The shared repository or its Object-Lock backend is unavailable."""


class ImmutableEvidenceConflict(EvidenceObjectStoreError):
    """A trace already names different immutable packet bytes."""


@runtime_checkable
class ImmutablePacketBackend(Protocol):
    """Minimal byte-store contract required by :class:`EvidencePacketRepository`."""

    def assert_ready(self, *, expected: RetentionPolicy) -> None: ...

    def object_url(self, key: str, *, version_id: str | None = None) -> str: ...

    def put_immutable(
        self,
        *,
        key: str,
        body: bytes,
        content_hash: str,
        policy: RetentionPolicy,
    ) -> LockReceipt: ...

    def get_immutable(self, *, key: str, version_id: str) -> bytes: ...

    def verify_receipt(
        self,
        *,
        key: str,
        version_id: str,
        content_hash: str,
        policy: RetentionPolicy,
        requested_at: datetime,
        requested_retain_until: datetime,
        minimum_retain_until: datetime,
        original_verified_at: datetime,
    ) -> LockReceipt: ...


class S3ObjectLockPacketBackend:
    """S3 Object-Lock implementation with conditional create and re-read proof."""

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str,
        region: str = "",
        client: Any | None = None,
    ) -> None:
        self.bucket = bucket.strip()
        self.prefix = prefix.strip("/ ")
        if not self.bucket:
            raise EvidenceObjectStoreUnavailable("Evidence Packet S3 bucket is not configured.")
        if client is None:
            try:
                import boto3  # type: ignore[import-not-found]
            except ImportError as exc:
                raise EvidenceObjectStoreUnavailable(
                    "boto3 is required for shared Evidence Packet object storage."
                ) from exc
            kwargs: dict[str, Any] = {}
            if region.strip():
                kwargs["region_name"] = region.strip()
            client = boto3.client("s3", **kwargs)
        self._client = client

    def assert_ready(self, *, expected: RetentionPolicy) -> None:
        del expected
        try:
            lock = self._client.get_object_lock_configuration(Bucket=self.bucket)
            versioning = self._client.get_bucket_versioning(Bucket=self.bucket)
        except Exception as exc:
            raise EvidenceObjectStoreUnavailable(
                f"S3 Object-Lock readiness check failed: {type(exc).__name__}: {exc}"
            ) from exc
        enabled = isinstance(lock, Mapping) and isinstance(
            lock.get("ObjectLockConfiguration"), Mapping
        ) and lock["ObjectLockConfiguration"].get("ObjectLockEnabled") == "Enabled"
        if not enabled:
            raise EvidenceObjectStoreUnavailable(
                "Evidence Packet bucket does not report ObjectLockEnabled=Enabled."
            )
        if not isinstance(versioning, Mapping) or versioning.get("Status") != "Enabled":
            raise EvidenceObjectStoreUnavailable(
                "Evidence Packet bucket versioning is not enabled."
            )

    def object_url(self, key: str, *, version_id: str | None = None) -> str:
        full_key = self._full_key(key)
        encoded_key = quote(full_key, safe="/")
        suffix = f"?versionId={quote(version_id, safe='')}" if version_id else ""
        return f"s3://{self.bucket}/{encoded_key}{suffix}"

    def put_immutable(
        self,
        *,
        key: str,
        body: bytes,
        content_hash: str,
        policy: RetentionPolicy,
    ) -> LockReceipt:
        if hashlib.sha256(body).hexdigest() != content_hash:
            raise ValueError("content_hash does not match Evidence Packet bytes")
        full_key = self._full_key(key)
        requested_at = datetime.now(UTC).replace(microsecond=0)
        retain_until = policy.retain_until(now=requested_at)
        kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": full_key,
            "Body": body,
            "ContentType": "application/json",
            "ContentMD5": base64.b64encode(hashlib.md5(body).digest()).decode("ascii"),
            "IfNoneMatch": "*",
            "ObjectLockMode": policy.mode,
            "ObjectLockRetainUntilDate": retain_until,
            "Metadata": {
                "content-sha256": content_hash,
                "retention-mode": policy.mode,
                "retention-days": str(policy.retention_days),
                "retention-requested-at": requested_at.isoformat(),
                "retention-requested-until": retain_until.isoformat(),
            },
        }
        try:
            response = self._client.put_object(**kwargs)
            version_id = _text(response.get("VersionId")) if isinstance(response, Mapping) else None
        except Exception as exc:
            if not _is_precondition_failure(exc):
                raise EvidenceObjectStoreUnavailable(
                    f"S3 immutable packet write failed: {type(exc).__name__}: {exc}"
                ) from exc
            # Another replica won the conditional create.  Re-read the current
            # version and accept it only when it is byte-identical and locked.
            version_id = None
        receipt = self._reread_receipt(
            key=key,
            version_id=version_id,
            content_hash=content_hash,
            policy=policy,
            requested_at=requested_at if version_id else None,
            requested_retain_until=retain_until if version_id else None,
            minimum_retain_until=retain_until if version_id else None,
            original_verified_at=None,
        )
        if not receipt.is_verifiable():
            raise EvidenceObjectStoreUnavailable(
                "S3 packet write did not produce a re-read-verifiable Object-Lock receipt."
            )
        return receipt

    def get_immutable(self, *, key: str, version_id: str) -> bytes:
        try:
            response = self._client.get_object(
                Bucket=self.bucket,
                Key=self._full_key(key),
                VersionId=version_id,
            )
            return response["Body"].read()
        except Exception as exc:
            raise EvidenceObjectStoreUnavailable(
                f"S3 immutable packet re-read failed: {type(exc).__name__}: {exc}"
            ) from exc

    def verify_receipt(
        self,
        *,
        key: str,
        version_id: str,
        content_hash: str,
        policy: RetentionPolicy,
        requested_at: datetime,
        requested_retain_until: datetime,
        minimum_retain_until: datetime,
        original_verified_at: datetime,
    ) -> LockReceipt:
        return self._reread_receipt(
            key=key,
            version_id=version_id,
            content_hash=content_hash,
            policy=policy,
            requested_at=requested_at,
            requested_retain_until=requested_retain_until,
            minimum_retain_until=minimum_retain_until,
            original_verified_at=original_verified_at,
        )

    def _reread_receipt(
        self,
        *,
        key: str,
        version_id: str | None,
        content_hash: str,
        policy: RetentionPolicy,
        requested_at: datetime | None,
        requested_retain_until: datetime | None,
        minimum_retain_until: datetime | None,
        original_verified_at: datetime | None,
    ) -> LockReceipt:
        full_key = self._full_key(key)
        head_kwargs: dict[str, Any] = {"Bucket": self.bucket, "Key": full_key}
        if version_id:
            head_kwargs["VersionId"] = version_id
        try:
            head = self._client.head_object(**head_kwargs)
            resolved_version = version_id or _text(head.get("VersionId"))
            if not resolved_version:
                raise EvidenceObjectStoreUnavailable(
                    "S3 Object-Lock packet receipt is missing VersionId."
                )
            response = self._client.get_object(
                Bucket=self.bucket,
                Key=full_key,
                VersionId=resolved_version,
            )
            body = response["Body"].read()
        except EvidenceObjectStoreError:
            raise
        except Exception as exc:
            raise EvidenceObjectStoreUnavailable(
                f"S3 packet receipt verification failed: {type(exc).__name__}: {exc}"
            ) from exc
        actual_hash = hashlib.sha256(body).hexdigest()
        actual_mode = _text(head.get("ObjectLockMode"))
        retain_until = _aware_datetime(head.get("ObjectLockRetainUntilDate"))
        metadata_expectation = _s3_metadata_expectation(
            head,
            expected_content_hash=content_hash,
        )
        if requested_at is None:
            requested_at = metadata_expectation["requested_at"]
            requested_retain_until = metadata_expectation["requested_retain_until"]
            minimum_retain_until = requested_retain_until
            expected_mode = policy.mode
            expected_days = policy.retention_days
            if (
                metadata_expectation["mode"] != expected_mode
                or metadata_expectation["retention_days"] != expected_days
            ):
                raise EvidenceObjectStoreUnavailable(
                    "A byte-identical existing S3 object uses a weaker or different "
                    "retention policy than this write requires."
                )
        else:
            expected_mode = policy.mode
            expected_days = policy.retention_days
            if (
                metadata_expectation["mode"] != expected_mode
                or metadata_expectation["retention_days"] != expected_days
                or metadata_expectation["requested_at"] != requested_at
                or metadata_expectation["requested_retain_until"]
                != requested_retain_until
            ):
                raise EvidenceObjectStoreUnavailable(
                    "S3 packet retention request metadata does not match the durable expectation."
                )
        if requested_retain_until is None or minimum_retain_until is None:
            raise EvidenceObjectStoreUnavailable(
                "S3 packet receipt is missing its original retention request boundary."
            )
        if retain_until is None or retain_until < minimum_retain_until:
            raise EvidenceObjectStoreUnavailable(
                "S3 packet retention was shortened below its durable observed minimum."
            )
        # Trusted issuer boundary: ``response`` and ``head`` were obtained above
        # by exact-VersionId SDK reads, never from packet/API mappings.
        verification = _issue_live_s3_object_lock_receipt(
            expected={
                "bucket": self.bucket,
                "key": full_key,
                "version_id": resolved_version,
                "content_sha256": content_hash,
                "mode": expected_mode,
                "retention_days": expected_days,
                "requested_at": requested_at,
                "retain_until": requested_retain_until,
            },
            observed={
                "bucket": self.bucket,
                "key": full_key,
                "get_version_id": response.get("VersionId"),
                "head_version_id": head.get("VersionId"),
                "content_sha256": actual_hash,
                "mode": actual_mode,
                "retain_until": retain_until,
                "reread_verified": True,
            },
            verified_at=original_verified_at,
        )
        return LockReceipt(
            object_url=self.object_url(key, version_id=resolved_version),
            version_id=resolved_version,
            retain_until=retain_until or datetime.now(UTC),
            mode=actual_mode or "",
            content_hash=actual_hash,
            legal_hold=bool(head.get("ObjectLockLegalHoldStatus") == "ON"),
            reread_verified=verification.verified,
            verification_receipt=verification,
        )

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key


@dataclass(frozen=True)
class EvidenceStorageScope:
    repository: "EvidencePacketRepository"
    tenant_id: str
    account_id: str | None = None


class EvidencePacketRepository:
    """Shared packet bytes, durable tenant index, and append-only hash chain."""

    def __init__(
        self,
        *,
        store: StateStore,
        backend: ImmutablePacketBackend,
        policy: RetentionPolicy,
        replica_id: str | None = None,
    ) -> None:
        self.store = store
        self.backend = backend
        self.policy = policy
        self.replica_id = replica_id or f"packet-replica-{uuid.uuid4().hex}"

    def assert_ready(self) -> None:
        self.backend.assert_ready(expected=self.policy)

    def claim_publication_timestamp(
        self,
        *,
        tenant_id: str,
        namespace: str,
        trace_id: str,
        audit_id: str | None = None,
        account_id: str | None = None,
    ) -> str:
        """Persist one cross-replica first-publication time for immutable bytes."""
        _require_identity(tenant_id, trace_id)
        record_id = self._packet_index_id(namespace, trace_id)
        published_at = datetime.now(UTC).isoformat()
        payload = {
            "schema_version": "cas_harness_evidence_publication_intent.v1",
            "namespace": namespace,
            "trace_id": trace_id,
            "audit_id": audit_id,
            "account_id": account_id,
            "first_publication_at": published_at,
        }
        record = LedgerRecord.new(
            tenant_id=tenant_id,
            kind=PUBLICATION_INTENT_KIND,
            record_id=record_id,
            payload=payload,
            source="cas_harness_evidence_publication_intent",
            trace_id=trace_id,
        )
        try:
            self.store.put(record, expected_version=0)
            return published_at
        except VersionConflict:
            current = self.store.get(tenant_id, PUBLICATION_INTENT_KIND, record_id)
            if current is None:
                raise EvidenceObjectStoreUnavailable(
                    "Publication intent conflicted but cannot be re-read."
                )
            stored = current.payload
            if (
                stored.get("schema_version")
                != "cas_harness_evidence_publication_intent.v1"
                or stored.get("namespace") != namespace
                or stored.get("trace_id") != trace_id
                or stored.get("audit_id") != audit_id
                or stored.get("account_id") != account_id
            ):
                raise ImmutableEvidenceConflict(
                    f"trace {trace_id!r} has a different publication intent"
                )
            value = stored.get("first_publication_at")
            if not isinstance(value, str) or not value:
                raise EvidenceObjectStoreUnavailable(
                    "Publication intent timestamp is unavailable."
                )
            return value

    def packet_reference(self, *, tenant_id: str, namespace: str, trace_id: str) -> str:
        return self.backend.object_url(self._object_key(tenant_id, namespace, trace_id))

    def hash_log_reference(self, *, tenant_id: str, namespace: str) -> str:
        return (
            "state-store://evidence-packet-hash-log/"
            f"{_digest(tenant_id)}/{_digest(namespace or 'default')}"
        )

    def put_packet(
        self,
        *,
        tenant_id: str,
        namespace: str,
        trace_id: str,
        packet: Mapping[str, Any],
        account_id: str | None = None,
    ) -> LockReceipt:
        _require_identity(tenant_id, trace_id)
        if packet.get("trace_id") != trace_id:
            raise ValueError("Evidence Packet trace_id does not match storage key")
        body = _canonical_json(packet).encode("utf-8")
        content_hash = hashlib.sha256(body).hexdigest()
        record_id = self._packet_index_id(namespace, trace_id)
        existing = self.store.get(tenant_id, PACKET_INDEX_KIND, record_id)
        if existing is not None:
            receipt = self._reconcile_existing_packet(
                tenant_id=tenant_id,
                namespace=namespace,
                trace_id=trace_id,
                content_hash=content_hash,
                existing=existing.payload,
            )
            self._record_hash_log_worm_receipt(
                tenant_id=tenant_id,
                namespace=namespace,
                trace_id=trace_id,
                packet=packet,
                content_hash=content_hash,
                receipt=receipt,
            )
            return receipt

        key = self._object_key(tenant_id, namespace, trace_id)
        receipt = self.backend.put_immutable(
            key=key,
            body=body,
            content_hash=content_hash,
            policy=self.policy,
        )
        if not receipt.is_verifiable():
            raise EvidenceObjectStoreUnavailable(
                "Immutable packet backend returned an unverified WORM receipt."
            )
        verification = receipt.validated_verification()
        if verification is None or not verification.verified:
            raise EvidenceObjectStoreUnavailable(
                "Immutable packet backend omitted the structured Object-Lock receipt."
            )
        requested_at = _required_text(
            verification.expected.get("requested_at"),
            "Object-Lock receipt requested_at",
        )
        requested_until = _required_text(
            verification.expected.get("retain_until"),
            "Object-Lock receipt requested retain_until",
        )
        expected_mode = _required_text(
            verification.expected.get("mode"),
            "Object-Lock receipt mode",
        )
        expected_days = verification.expected.get("retention_days")
        if (
            not isinstance(expected_days, int)
            or isinstance(expected_days, bool)
            or expected_days < 1
        ):
            raise EvidenceObjectStoreUnavailable(
                "Object-Lock receipt retention_days is unavailable."
            )
        payload = {
            "schema_version": "cas_harness_evidence_packet_object_index.v1",
            "trace_id": trace_id,
            "namespace": namespace,
            "account_id": account_id,
            "object_key": key,
            "object_url": receipt.object_url,
            "content_sha256": content_hash,
            "byte_length": len(body),
            "version_id": receipt.version_id,
            "object_lock_mode": expected_mode,
            "object_lock_retain_until": receipt.retain_until.astimezone(UTC).isoformat(),
            "object_lock_minimum_retain_until": receipt.retain_until.astimezone(
                UTC
            ).isoformat(),
            "retention_days": expected_days,
            "retention_requested_at": requested_at,
            "retention_requested_until": requested_until,
            "reread_verified": receipt.reread_verified,
            "object_lock_verification": verification.to_dict(),
        }
        record = LedgerRecord.new(
            tenant_id=tenant_id,
            kind=PACKET_INDEX_KIND,
            record_id=record_id,
            payload=payload,
            source="cas_harness_evidence_object_store",
            trace_id=trace_id,
        )
        try:
            self.store.put(record, expected_version=0)
        except VersionConflict:
            existing = self.store.get(tenant_id, PACKET_INDEX_KIND, record_id)
            if existing is None:
                raise EvidenceObjectStoreUnavailable(
                    "Packet index conflicted but cannot be re-read."
                )
            receipt = self._reconcile_existing_packet(
                tenant_id=tenant_id,
                namespace=namespace,
                trace_id=trace_id,
                content_hash=content_hash,
                existing=existing.payload,
            )
        self._record_hash_log_worm_receipt(
            tenant_id=tenant_id,
            namespace=namespace,
            trace_id=trace_id,
            packet=packet,
            content_hash=content_hash,
            receipt=receipt,
        )
        return receipt

    def load_packet(self, *, tenant_id: str, namespace: str, trace_id: str) -> dict[str, Any]:
        packet, _content_sha256 = self.load_packet_with_content_sha256(
            tenant_id=tenant_id,
            namespace=namespace,
            trace_id=trace_id,
        )
        return packet

    def load_packet_with_content_sha256(
        self, *, tenant_id: str, namespace: str, trace_id: str
    ) -> tuple[dict[str, Any], str]:
        """Load verified immutable bytes plus their exact durable byte hash.

        Consumers that bind a capability to a specific packet version must use
        this hash, not re-serialize the decoded mapping and assume byte identity.
        The returned digest is the one checked against the exact VersionId read.
        """
        record = self.store.get(
            tenant_id, PACKET_INDEX_KIND, self._packet_index_id(namespace, trace_id)
        )
        if record is None:
            raise FileNotFoundError(trace_id)
        payload = record.payload
        key = _required_text(payload.get("object_key"), "packet index object_key")
        if key != self._object_key(tenant_id, namespace, trace_id):
            raise EvidenceObjectStoreUnavailable(
                "Packet index object key does not match its tenant/namespace/trace identity."
            )
        version_id = _required_text(payload.get("version_id"), "packet index version_id")
        expected_hash = _required_text(payload.get("content_sha256"), "packet index content hash")
        body = self.backend.get_immutable(key=key, version_id=version_id)
        expected_length = payload.get("byte_length")
        if not isinstance(expected_length, int) or len(body) != expected_length:
            raise EvidenceObjectStoreUnavailable(
                "Immutable Evidence Packet byte length does not match the durable index."
            )
        if hashlib.sha256(body).hexdigest() != expected_hash:
            raise EvidenceObjectStoreUnavailable(
                "Immutable Evidence Packet bytes do not match the durable index hash."
            )
        try:
            packet = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceObjectStoreUnavailable(
                "Immutable Evidence Packet object is not canonical JSON."
            ) from exc
        if not isinstance(packet, dict) or packet.get("trace_id") != trace_id:
            raise EvidenceObjectStoreUnavailable(
                "Immutable Evidence Packet object does not match the tenant index."
            )
        return packet, expected_hash

    def verify_packet(
        self, *, tenant_id: str, namespace: str, trace_id: str
    ) -> dict[str, Any]:
        record = self.store.get(
            tenant_id, PACKET_INDEX_KIND, self._packet_index_id(namespace, trace_id)
        )
        if record is None:
            return {
                "artifact": "tenant_packet_object_store",
                "expected": "durable tenant packet index",
                "actual": None,
                "match": False,
                "notes": "tenant packet index entry is unavailable",
            }
        payload = record.payload
        verification = None
        try:
            key = _required_text(payload.get("object_key"), "packet index object_key")
            if key != self._object_key(tenant_id, namespace, trace_id):
                raise EvidenceObjectStoreUnavailable(
                    "Packet index object key does not match its tenant/namespace/trace identity."
                )
            version_id = _required_text(payload.get("version_id"), "packet index version_id")
            content_hash = _required_text(payload.get("content_sha256"), "packet index content hash")
            requirements = self._stored_packet_receipt_requirements(
                payload,
                expected_key=key,
                expected_version=version_id,
                expected_content_hash=content_hash,
            )
            receipt = self.backend.verify_receipt(
                key=key,
                version_id=version_id,
                content_hash=content_hash,
                policy=requirements["policy"],
                requested_at=requirements["requested_at"],
                requested_retain_until=requirements["requested_retain_until"],
                minimum_retain_until=requirements["minimum_retain_until"],
                original_verified_at=requirements["original_verified_at"],
            )
            match = receipt.is_verifiable() and receipt.content_hash == content_hash
            actual = receipt.content_hash
            verification = receipt.validated_verification()
            if match:
                notes = (
                    f"durable tenant index re-read S3 version {receipt.version_id}; "
                    f"Object Lock {receipt.mode} is active until "
                    f"{receipt.retain_until.astimezone(UTC).isoformat()}"
                )
            else:
                reasons = (
                    "; ".join(verification.failure_reasons)
                    if verification is not None
                    else "structured Object-Lock receipt is unavailable"
                )
                notes = f"durable tenant packet Object-Lock re-verification failed: {reasons}"
        except EvidenceObjectStoreError as exc:
            match = False
            actual = None
            notes = str(exc)
        result = {
            "artifact": "tenant_packet_object_store",
            "expected": payload.get("content_sha256"),
            "actual": actual,
            "match": match,
            "notes": notes,
        }
        if verification is not None:
            result["object_lock_verification"] = verification.to_dict()
        if match and (verification is None or not verification.verified):
            result["match"] = False
            result["notes"] = "tenant packet Object-Lock receipt is malformed"
        return result

    def append_hash_log(
        self,
        *,
        tenant_id: str,
        namespace: str,
        trace_id: str,
        audit_id: Any,
        packet_without_hashes_sha256: str,
        operation: str,
    ) -> dict[str, Any]:
        _require_identity(tenant_id, trace_id)
        if not _is_sha256(packet_without_hashes_sha256):
            raise ValueError("packet_without_hashes_sha256 must be a sha256 hex digest")
        lease = self._acquire_hash_log_lease(tenant_id, namespace)
        try:
            existing = self._trace_hash_entry(tenant_id, namespace, trace_id)
            if existing is not None:
                if existing.get("packet_without_hashes_sha256") != packet_without_hashes_sha256:
                    raise ImmutableEvidenceConflict(
                        f"trace {trace_id!r} already has a different immutable hash-log entry"
                    )
                return existing

            # Repair a crash after head advancement but before the trace lookup row.
            recovered = self._find_reachable_entry(
                tenant_id=tenant_id,
                namespace=namespace,
                trace_id=trace_id,
                packet_hash=packet_without_hashes_sha256,
            )
            if recovered is not None:
                self._write_trace_hash_index(tenant_id, namespace, trace_id, recovered)
                return recovered

            head_id = self._hash_head_id(namespace)
            head = self.store.get(tenant_id, HASH_LOG_HEAD_KIND, head_id)
            previous_hash = (
                _text(head.payload.get("entry_sha256")) if head is not None else None
            )
            entry: dict[str, Any] = {
                "schema_version": "cas_harness_evidence_packet_hash_log.v2",
                "tenant_key_sha256": _digest(tenant_id),
                "namespace": namespace,
                "trace_id": trace_id,
                "audit_id": audit_id if isinstance(audit_id, str) else None,
                "packet_without_hashes_sha256": packet_without_hashes_sha256,
                "previous_entry_sha256": previous_hash,
                "created_at": datetime.now(UTC).isoformat(),
                "operation": operation,
            }
            entry["entry_sha256"] = _hash_log_entry_sha256(entry)
            entry_hash = str(entry["entry_sha256"])
            entry_record = LedgerRecord.new(
                tenant_id=tenant_id,
                kind=HASH_LOG_ENTRY_KIND,
                record_id=entry_hash,
                payload=entry,
                source="cas_harness_evidence_hash_log",
                trace_id=trace_id,
            )
            try:
                self.store.put(entry_record, expected_version=0)
            except VersionConflict:
                stored = self.store.get(tenant_id, HASH_LOG_ENTRY_KIND, entry_hash)
                if stored is None or dict(stored.payload) != entry:
                    raise EvidenceObjectStoreUnavailable(
                        "Hash-log entry conflict could not be reconciled."
                    )

            self._assert_lease_live(tenant_id, namespace, lease.token)
            head_payload = {
                "schema_version": "cas_harness_evidence_packet_hash_log_head.v1",
                "namespace": namespace,
                "entry_sha256": entry_hash,
            }
            if head is None:
                next_head = LedgerRecord.new(
                    tenant_id=tenant_id,
                    kind=HASH_LOG_HEAD_KIND,
                    record_id=head_id,
                    payload=head_payload,
                    source="cas_harness_evidence_hash_log",
                    trace_id=trace_id,
                )
                expected_version = 0
            else:
                next_head = head.with_payload(head_payload)
                expected_version = head.version
            self.store.put(next_head, expected_version=expected_version)
            self._write_trace_hash_index(tenant_id, namespace, trace_id, entry)
            return entry
        finally:
            try:
                self.store.release_lease(lease.token)
            except Exception:
                pass

    def load_hash_log_entry(
        self,
        *,
        tenant_id: str,
        namespace: str,
        trace_id: str,
        entry_sha256: Any,
    ) -> tuple[dict[str, Any], bool]:
        if not isinstance(entry_sha256, str):
            raise FileNotFoundError(trace_id)
        entries, chain_ok = self._reachable_entries(tenant_id, namespace)
        entry = entries.get(entry_sha256)
        if entry is None or entry.get("trace_id") != trace_id:
            raise FileNotFoundError(trace_id)
        return entry, chain_ok

    def _reconcile_existing_packet(
        self,
        *,
        tenant_id: str,
        namespace: str,
        trace_id: str,
        content_hash: str,
        existing: Mapping[str, Any],
    ) -> LockReceipt:
        if existing.get("trace_id") != trace_id or existing.get("namespace") != namespace:
            raise EvidenceObjectStoreUnavailable("Packet index identity is malformed.")
        if existing.get("content_sha256") != content_hash:
            raise ImmutableEvidenceConflict(
                f"trace {trace_id!r} already names different immutable packet bytes"
            )
        key = _required_text(existing.get("object_key"), "packet index object_key")
        if key != self._object_key(tenant_id, namespace, trace_id):
            raise EvidenceObjectStoreUnavailable(
                "Packet index object key does not match its tenant/namespace/trace identity."
            )
        version_id = _required_text(existing.get("version_id"), "packet index version_id")
        requirements = self._stored_packet_receipt_requirements(
            existing,
            expected_key=key,
            expected_version=version_id,
            expected_content_hash=content_hash,
        )
        receipt = self.backend.verify_receipt(
            key=key,
            version_id=version_id,
            content_hash=content_hash,
            policy=requirements["policy"],
            requested_at=requirements["requested_at"],
            requested_retain_until=requirements["requested_retain_until"],
            minimum_retain_until=requirements["minimum_retain_until"],
            original_verified_at=requirements["original_verified_at"],
        )
        if not receipt.is_verifiable():
            raise EvidenceObjectStoreUnavailable(
                "Existing packet index does not have a verifiable Object-Lock receipt."
            )
        return receipt

    def _stored_packet_receipt_requirements(
        self,
        payload: Mapping[str, Any],
        *,
        expected_key: str,
        expected_version: str,
        expected_content_hash: str,
    ) -> dict[str, Any]:
        """Rebuild the immutable minimum from the durable packet index.

        Runtime configuration is deliberately irrelevant here.  A later
        re-verification must meet the exact stored version/hash/mode and may
        not fall below either the original request window or the longer
        deadline that was actually observed when the packet was indexed.
        """

        object_url = _required_text(payload.get("object_url"), "packet index object_url")
        canonical_url = self.backend.object_url(
            expected_key,
            version_id=expected_version,
        )
        if object_url != canonical_url:
            raise EvidenceObjectStoreUnavailable(
                "Packet index object_url does not match its canonical S3 receipt."
            )
        parsed = urlparse(object_url)
        try:
            query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
        except ValueError as exc:
            raise EvidenceObjectStoreUnavailable(
                "Packet index object_url has a malformed version query."
            ) from exc
        if (
            parsed.scheme != "s3"
            or not parsed.netloc
            or not unquote(parsed.path.lstrip("/"))
            or set(query) != {"versionId"}
            or query.get("versionId") != [expected_version]
        ):
            raise EvidenceObjectStoreUnavailable(
                "Packet index object_url is not an exact s3:// version receipt."
            )

        mode = _required_text(payload.get("object_lock_mode"), "packet index Object Lock mode")
        days = payload.get("retention_days")
        if mode not in {"GOVERNANCE", "COMPLIANCE"}:
            raise EvidenceObjectStoreUnavailable("Packet index Object Lock mode is invalid.")
        if not isinstance(days, int) or isinstance(days, bool) or days < 1:
            raise EvidenceObjectStoreUnavailable("Packet index retention_days is invalid.")
        requested_at = _aware_datetime(payload.get("retention_requested_at"))
        requested_until = _aware_datetime(payload.get("retention_requested_until"))
        minimum_until = _aware_datetime(
            payload.get("object_lock_minimum_retain_until")
        )
        if requested_at is None or requested_until is None or minimum_until is None:
            raise EvidenceObjectStoreUnavailable(
                "Packet index is missing its durable retention request/minimum deadline."
            )
        if requested_until < requested_at + timedelta(days=days):
            raise EvidenceObjectStoreUnavailable(
                "Packet index request is shorter than the full retention_days window."
            )
        if minimum_until < requested_until:
            raise EvidenceObjectStoreUnavailable(
                "Packet index minimum deadline is shorter than its write request."
            )
        if _aware_datetime(payload.get("object_lock_retain_until")) != minimum_until:
            raise EvidenceObjectStoreUnavailable(
                "Packet index observed and minimum retention deadlines diverge."
            )

        raw_verification = payload.get("object_lock_verification")
        if not isinstance(raw_verification, Mapping):
            raise EvidenceObjectStoreUnavailable(
                "Packet index has no structured Object-Lock verification receipt."
            )
        raw_expected = raw_verification.get("expected")
        raw_observed = raw_verification.get("observed")
        if not isinstance(raw_expected, Mapping) or not isinstance(raw_observed, Mapping):
            raise EvidenceObjectStoreUnavailable(
                "Packet index Object-Lock verification receipt is malformed."
            )
        full_key = unquote(parsed.path.lstrip("/"))
        original_expected = {
            "bucket": parsed.netloc,
            "key": full_key,
            "version_id": expected_version,
            "content_sha256": expected_content_hash,
            "mode": mode,
            "retention_days": days,
            "requested_at": requested_at,
            "retain_until": requested_until,
        }
        for field, value in original_expected.items():
            canonical_value = (
                value.astimezone(UTC).isoformat()
                if isinstance(value, datetime)
                else value
            )
            if raw_expected.get(field) != canonical_value:
                raise EvidenceObjectStoreUnavailable(
                    f"Packet index structured receipt does not match stored {field}."
                )
        if _aware_datetime(raw_observed.get("retain_until")) != minimum_until:
            raise EvidenceObjectStoreUnavailable(
                "Packet index structured receipt does not match the stored minimum deadline."
            )
        revalidated = revalidate_object_lock_verification(
            raw_verification,
            expected=original_expected,
        )
        if (
            revalidated is None
            or not revalidated.verified
            or revalidated.issuer_attestation is None
        ):
            raise EvidenceObjectStoreUnavailable(
                "Packet index structured Object-Lock receipt no longer verifies."
            )
        original_verified_at = _aware_datetime(raw_verification.get("verified_at"))
        if original_verified_at is None:
            raise EvidenceObjectStoreUnavailable(
                "Packet index structured receipt has no original verified_at."
            )
        return {
            "policy": RetentionPolicy(mode=mode, retention_days=days),  # type: ignore[arg-type]
            "requested_at": requested_at,
            "requested_retain_until": requested_until,
            "minimum_retain_until": minimum_until,
            "original_verified_at": original_verified_at,
        }

    def _record_hash_log_worm_receipt(
        self,
        *,
        tenant_id: str,
        namespace: str,
        trace_id: str,
        packet: Mapping[str, Any],
        content_hash: str,
        receipt: LockReceipt,
    ) -> None:
        """Bind a hash-log append to the verified immutable packet version.

        The packet object must exist before this row can exist.  A crash between
        the two leaves the chain honestly invalid until retry repairs the row;
        it never produces a false WORM-committed append.
        """
        hashes = packet.get("hashes")
        entry_hash = (
            _text(hashes.get("hash_log_entry_sha256"))
            if isinstance(hashes, Mapping)
            else None
        )
        if entry_hash is None:
            return
        entry = self.store.get(tenant_id, HASH_LOG_ENTRY_KIND, entry_hash)
        if entry is None or entry.trace_id != trace_id:
            raise EvidenceObjectStoreUnavailable(
                "Packet names a hash-log entry that is unavailable for this tenant/trace."
            )
        if not receipt.is_verifiable():
            raise EvidenceObjectStoreUnavailable(
                "Hash-log WORM receipt requires a re-read-verifiable packet object."
            )
        packet_index = self.store.get(
            tenant_id,
            PACKET_INDEX_KIND,
            self._packet_index_id(namespace, trace_id),
        )
        if packet_index is None:
            raise EvidenceObjectStoreUnavailable(
                "Hash-log WORM receipt requires the durable packet index."
            )
        index_payload = packet_index.payload
        index_verification = index_payload.get("object_lock_verification")
        if not isinstance(index_verification, Mapping):
            raise EvidenceObjectStoreUnavailable(
                "Hash-log WORM receipt requires the packet index's structured receipt."
            )
        verification_payload = dict(index_verification)
        payload = {
            "schema_version": "cas_harness_evidence_packet_hash_log_worm_receipt.v1",
            "namespace": namespace,
            "trace_id": trace_id,
            "entry_sha256": entry_hash,
            "packet_content_sha256": content_hash,
            "object_key": index_payload.get("object_key"),
            "version_id": index_payload.get("version_id"),
            "object_lock_mode": index_payload.get("object_lock_mode"),
            "object_lock_retain_until": index_payload.get("object_lock_retain_until"),
            "object_lock_minimum_retain_until": index_payload.get(
                "object_lock_minimum_retain_until"
            ),
            "retention_days": index_payload.get("retention_days"),
            "retention_requested_at": index_payload.get("retention_requested_at"),
            "retention_requested_until": index_payload.get(
                "retention_requested_until"
            ),
            "reread_verified": True,
            "object_lock_verification": verification_payload,
        }
        record_id = self._hash_receipt_id(entry_hash)
        record = LedgerRecord.new(
            tenant_id=tenant_id,
            kind=HASH_LOG_WORM_RECEIPT_KIND,
            record_id=record_id,
            payload=payload,
            source="cas_harness_evidence_object_store",
            trace_id=trace_id,
        )
        try:
            self.store.put(record, expected_version=0)
        except VersionConflict:
            current = self.store.get(
                tenant_id, HASH_LOG_WORM_RECEIPT_KIND, record_id
            )
            if current is None or dict(current.payload) != payload:
                raise ImmutableEvidenceConflict(
                    f"hash-log entry {entry_hash!r} has a different WORM receipt"
                )

    def _trace_hash_entry(
        self, tenant_id: str, namespace: str, trace_id: str
    ) -> dict[str, Any] | None:
        index = self.store.get(
            tenant_id, HASH_LOG_TRACE_KIND, self._hash_trace_id(namespace, trace_id)
        )
        if index is None:
            return None
        entry_hash = _text(index.payload.get("entry_sha256"))
        if not entry_hash:
            raise EvidenceObjectStoreUnavailable("Hash-log trace index is malformed.")
        entry = self.store.get(tenant_id, HASH_LOG_ENTRY_KIND, entry_hash)
        if entry is None:
            raise EvidenceObjectStoreUnavailable("Hash-log trace index points to a missing entry.")
        return dict(entry.payload)

    def _write_trace_hash_index(
        self, tenant_id: str, namespace: str, trace_id: str, entry: Mapping[str, Any]
    ) -> None:
        record_id = self._hash_trace_id(namespace, trace_id)
        payload = {
            "schema_version": "cas_harness_evidence_packet_hash_log_trace.v1",
            "namespace": namespace,
            "trace_id": trace_id,
            "entry_sha256": entry.get("entry_sha256"),
            "packet_without_hashes_sha256": entry.get("packet_without_hashes_sha256"),
        }
        record = LedgerRecord.new(
            tenant_id=tenant_id,
            kind=HASH_LOG_TRACE_KIND,
            record_id=record_id,
            payload=payload,
            source="cas_harness_evidence_hash_log",
            trace_id=trace_id,
        )
        try:
            self.store.put(record, expected_version=0)
        except VersionConflict:
            current = self.store.get(tenant_id, HASH_LOG_TRACE_KIND, record_id)
            if current is None or current.payload.get("entry_sha256") != entry.get("entry_sha256"):
                raise ImmutableEvidenceConflict(
                    f"trace {trace_id!r} acquired a different hash-log entry"
                )

    def _find_reachable_entry(
        self,
        *,
        tenant_id: str,
        namespace: str,
        trace_id: str,
        packet_hash: str,
    ) -> dict[str, Any] | None:
        entries, _ = self._reachable_entries(tenant_id, namespace)
        for entry in entries.values():
            if (
                entry.get("trace_id") == trace_id
                and entry.get("packet_without_hashes_sha256") == packet_hash
            ):
                return entry
        return None

    def _reachable_entries(
        self, tenant_id: str, namespace: str
    ) -> tuple[dict[str, dict[str, Any]], bool]:
        head = self.store.get(
            tenant_id, HASH_LOG_HEAD_KIND, self._hash_head_id(namespace)
        )
        current = _text(head.payload.get("entry_sha256")) if head is not None else None
        found: dict[str, dict[str, Any]] = {}
        chain_ok = True
        while current:
            if current in found:
                chain_ok = False
                break
            record = self.store.get(tenant_id, HASH_LOG_ENTRY_KIND, current)
            if record is None:
                chain_ok = False
                break
            entry = dict(record.payload)
            if (
                entry.get("namespace") != namespace
                or entry.get("tenant_key_sha256") != _digest(tenant_id)
                or entry.get("entry_sha256") != current
                or _hash_log_entry_sha256(entry) != current
            ):
                chain_ok = False
            receipt = self.store.get(
                tenant_id,
                HASH_LOG_WORM_RECEIPT_KIND,
                self._hash_receipt_id(current),
            )
            packet_index = self.store.get(
                tenant_id,
                PACKET_INDEX_KIND,
                self._packet_index_id(namespace, str(entry.get("trace_id") or "")),
            )
            if (
                receipt is None
                or packet_index is None
                or receipt.trace_id != entry.get("trace_id")
                or receipt.payload.get("entry_sha256") != current
                or receipt.payload.get("packet_content_sha256")
                != packet_index.payload.get("content_sha256")
                or receipt.payload.get("object_key")
                != packet_index.payload.get("object_key")
                or receipt.payload.get("version_id")
                != packet_index.payload.get("version_id")
                or not self._stored_worm_receipt_matches(
                    receipt.payload, packet_index.payload
                )
            ):
                chain_ok = False
            found[current] = entry
            current = _text(entry.get("previous_entry_sha256"))
        return found, chain_ok

    def _stored_worm_receipt_matches(
        self,
        receipt: Mapping[str, Any],
        packet_index: Mapping[str, Any],
    ) -> bool:
        """Re-run the shared exact-binding predicate for durable ledger rows."""

        raw_verification = receipt.get("object_lock_verification")
        if not isinstance(raw_verification, Mapping):
            # Legacy prose/boolean rows cannot license a current WORM claim.
            return False
        stable_fields = (
            "object_key",
            "version_id",
            "object_lock_mode",
            "object_lock_retain_until",
            "object_lock_minimum_retain_until",
            "retention_days",
            "retention_requested_at",
            "retention_requested_until",
        )
        if any(receipt.get(field) != packet_index.get(field) for field in stable_fields):
            return False
        key = _text(packet_index.get("object_key"))
        version_id = _text(packet_index.get("version_id"))
        content_hash = _text(packet_index.get("content_sha256"))
        if key is None or version_id is None or content_hash is None:
            return False
        try:
            self._stored_packet_receipt_requirements(
                packet_index,
                expected_key=key,
                expected_version=version_id,
                expected_content_hash=content_hash,
            )
        except EvidenceObjectStoreError:
            return False
        object_url = _text(packet_index.get("object_url"))
        assert object_url is not None
        parsed = urlparse(object_url)
        object_key = unquote(parsed.path.lstrip("/"))
        expected = {
            "bucket": parsed.netloc,
            "key": object_key,
            "version_id": version_id,
            "content_sha256": content_hash,
            "mode": packet_index.get("object_lock_mode"),
            "retention_days": packet_index.get("retention_days"),
            "requested_at": packet_index.get("retention_requested_at"),
            # The authenticated expected binding is the original write request.
            # A stronger bucket default belongs to observed/minimum state and is
            # enforced separately by _stored_packet_receipt_requirements.
            "retain_until": packet_index.get("retention_requested_until"),
        }
        verification = revalidate_object_lock_verification(
            raw_verification,
            expected=expected,
        )
        return bool(
            receipt.get("reread_verified") is True
            and verification is not None
            and verification.verified
            and verification.issuer_attestation is not None
            and packet_index.get("object_lock_verification")
            == receipt.get("object_lock_verification")
        )

    def _acquire_hash_log_lease(self, tenant_id: str, namespace: str):
        resource = self._hash_lease_resource(namespace)
        holder = f"{self.replica_id}-{uuid.uuid4().hex}"
        for _ in range(100):
            try:
                return self.store.acquire_lease(
                    tenant_id,
                    resource,
                    holder=holder,
                    ttl_seconds=15.0,
                )
            except LeaseHeld:
                time.sleep(0.005)
        raise EvidenceObjectStoreUnavailable("Timed out waiting for the durable hash-log lease.")

    def _assert_lease_live(self, tenant_id: str, namespace: str, token: str) -> None:
        lease = self.store.get_lease(tenant_id, self._hash_lease_resource(namespace))
        if lease is None or lease.token != token:
            raise EvidenceObjectStoreUnavailable(
                "Durable hash-log lease expired before head advancement."
            )

    @staticmethod
    def _object_key(tenant_id: str, namespace: str, trace_id: str) -> str:
        return (
            f"tenants/{_digest(tenant_id)}/namespaces/{_digest(namespace or 'default')}/"
            f"packets/{_digest(trace_id)}.json"
        )

    @staticmethod
    def _packet_index_id(namespace: str, trace_id: str) -> str:
        return f"packet-{_digest(namespace + chr(0) + trace_id)}"

    @staticmethod
    def _hash_head_id(namespace: str) -> str:
        return f"hash-head-{_digest(namespace or 'default')}"

    @staticmethod
    def _hash_trace_id(namespace: str, trace_id: str) -> str:
        return f"hash-trace-{_digest(namespace + chr(0) + trace_id)}"

    @staticmethod
    def _hash_receipt_id(entry_sha256: str) -> str:
        return f"hash-worm-{entry_sha256}"

    @staticmethod
    def _hash_lease_resource(namespace: str) -> str:
        return f"evidence-hash-log-{_digest(namespace or 'default')}"


_CONFIGURED_REPOSITORY: EvidencePacketRepository | None = None
_ACTIVE_SCOPE: ContextVar[EvidenceStorageScope | None] = ContextVar(
    "cas_harness_evidence_storage_scope", default=None
)


def configure_evidence_packet_repository(
    repository: EvidencePacketRepository | None,
) -> None:
    """Install/clear the lifespan-owned shared repository for this process."""

    global _CONFIGURED_REPOSITORY
    _CONFIGURED_REPOSITORY = repository


def configured_evidence_packet_repository() -> EvidencePacketRepository | None:
    return _CONFIGURED_REPOSITORY


@contextmanager
def evidence_packet_storage_scope(
    *,
    tenant_id: str,
    account_id: str | None = None,
    repository: EvidencePacketRepository | None = None,
) -> Iterator[EvidenceStorageScope]:
    repo = repository or _CONFIGURED_REPOSITORY
    if repo is None:
        raise EvidenceObjectStoreUnavailable(
            "Shared Evidence Packet repository is not configured."
        )
    if not tenant_id.strip():
        raise EvidenceObjectStoreUnavailable("Evidence Packet tenant identity is unavailable.")
    scope = EvidenceStorageScope(repo, tenant_id.strip(), account_id)
    token = _ACTIVE_SCOPE.set(scope)
    try:
        yield scope
    finally:
        _ACTIVE_SCOPE.reset(token)


def active_evidence_packet_storage_scope() -> EvidenceStorageScope | None:
    return _ACTIVE_SCOPE.get()


def build_s3_evidence_packet_repository(store: StateStore) -> EvidencePacketRepository:
    """Build the real repository from the existing S3 anchor/Object-Lock settings."""

    bucket = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "").strip()
    prefix = os.environ.get(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX", "cas-harness/evidence-anchors"
    ).strip("/ ")
    region = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION", "").strip()
    require_stable_object_lock_receipt_attestation_key()
    target = runtime_object_lock_policy_target()
    if not target.configured or not target.valid or target.mode is None:
        raise EvidenceObjectStoreUnavailable(
            "Shared Evidence Packet storage requires Object Lock mode GOVERNANCE or COMPLIANCE."
        )
    if target.retention_days is None:
        raise EvidenceObjectStoreUnavailable(
            "Shared Evidence Packet storage requires a positive Object Lock retention period."
        )
    policy = RetentionPolicy(
        mode=target.mode, retention_days=target.retention_days
    )  # type: ignore[arg-type]
    backend = S3ObjectLockPacketBackend(
        bucket=bucket,
        prefix=f"{prefix}/packet-objects" if prefix else "packet-objects",
        region=region,
    )
    repository = EvidencePacketRepository(store=store, backend=backend, policy=policy)
    repository.assert_ready()
    return repository


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_log_entry_sha256(entry: Mapping[str, Any]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def _require_identity(tenant_id: str, trace_id: str) -> None:
    if not tenant_id.strip() or not trace_id.strip():
        raise ValueError("tenant_id and trace_id are required")


def _required_text(value: Any, label: str) -> str:
    text = _text(value)
    if not text:
        raise EvidenceObjectStoreUnavailable(f"{label} is unavailable.")
    return text


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _aware_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(UTC)
    return None


def _s3_metadata_expectation(
    head: Mapping[str, Any],
    *,
    expected_content_hash: str,
) -> dict[str, Any]:
    """Recover the winning writer's request boundary without trusting lock output.

    A conditional-create collision has no local write timestamp.  The winner's
    request metadata is therefore the only admissible source; using the
    currently observed retain-until value as its own expectation would make a
    shortened deadline self-validating.
    """

    metadata = head.get("Metadata")
    if not isinstance(metadata, Mapping):
        raise EvidenceObjectStoreUnavailable(
            "S3 packet receipt is missing retention request metadata."
        )
    content_hash = _text(metadata.get("content-sha256"))
    mode = _text(metadata.get("retention-mode"))
    days_text = _text(metadata.get("retention-days"))
    requested_at = _aware_datetime(metadata.get("retention-requested-at"))
    requested_until = _aware_datetime(metadata.get("retention-requested-until"))
    if content_hash != expected_content_hash:
        raise EvidenceObjectStoreUnavailable(
            "S3 packet retention metadata does not bind the expected content hash."
        )
    if mode not in {"GOVERNANCE", "COMPLIANCE"}:
        raise EvidenceObjectStoreUnavailable(
            "S3 packet retention metadata has no valid Object Lock mode."
        )
    if days_text is None or not days_text.isdigit() or int(days_text) < 1:
        raise EvidenceObjectStoreUnavailable(
            "S3 packet retention metadata has no positive retention_days value."
        )
    retention_days = int(days_text)
    if requested_at is None or requested_until is None:
        raise EvidenceObjectStoreUnavailable(
            "S3 packet retention metadata has no timezone-aware request boundary."
        )
    if requested_until < requested_at + timedelta(days=retention_days):
        raise EvidenceObjectStoreUnavailable(
            "S3 packet retention metadata is shorter than the full retention_days window."
        )
    return {
        "mode": mode,
        "retention_days": retention_days,
        "requested_at": requested_at,
        "requested_retain_until": requested_until,
    }




def _is_precondition_failure(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if not isinstance(response, Mapping):
        return False
    error = response.get("Error")
    status = response.get("ResponseMetadata")
    code = _text(error.get("Code")) if isinstance(error, Mapping) else None
    http_status = status.get("HTTPStatusCode") if isinstance(status, Mapping) else None
    return code in {"PreconditionFailed", "ConditionalRequestConflict", "412", "409"} or http_status in {409, 412}


__all__ = [
    "EvidenceObjectStoreError",
    "EvidenceObjectStoreUnavailable",
    "ImmutableEvidenceConflict",
    "ImmutablePacketBackend",
    "S3ObjectLockPacketBackend",
    "EvidencePacketRepository",
    "EvidenceStorageScope",
    "PACKET_INDEX_KIND",
    "PUBLICATION_INTENT_KIND",
    "HASH_LOG_ENTRY_KIND",
    "HASH_LOG_HEAD_KIND",
    "HASH_LOG_TRACE_KIND",
    "HASH_LOG_WORM_RECEIPT_KIND",
    "active_evidence_packet_storage_scope",
    "build_s3_evidence_packet_repository",
    "configure_evidence_packet_repository",
    "configured_evidence_packet_repository",
    "evidence_packet_storage_scope",
]
