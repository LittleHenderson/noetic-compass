from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import threading
from types import SimpleNamespace
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from api.config import settings
from api.services.accounts.store import AccountStore
from api.services.cas_harness_audit_sessions import configure_audit_session_store
from api.services.cas_harness_evidence_object_store import (
    EvidenceObjectStoreUnavailable,
    EvidencePacketRepository,
    HASH_LOG_ENTRY_KIND,
    ImmutableEvidenceConflict,
    PACKET_INDEX_KIND,
    PUBLICATION_INTENT_KIND,
    S3ObjectLockPacketBackend,
    configure_evidence_packet_repository,
    evidence_packet_storage_scope,
)
from api.services.cas_harness_merged_evidence_packets import (
    append_evidence_packet_hash_log_entry,
    evidence_hash_log_path,
    evidence_packet_store_path,
    evidence_packet_without_hashes_sha256,
    load_evidence_packet_from_store,
    verify_evidence_packet_hash_chain,
    write_evidence_packet_to_store,
    write_merged_fleet_evidence_packet,
)
from api.services.evidence_ownership import record_evidence_ownership
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.production.state_substrate import StateStoreError
from api.services.production.worm_writes import LockReceipt, RetentionPolicy
from tests.object_lock_test_support import issue_test_object_lock_receipt
from api.services.sessions import SessionStore


@pytest.fixture(autouse=True)
def _stable_object_lock_receipt_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings,
        "object_lock_receipt_attestation_key",
        "test-object-lock-receipt-key-32-bytes-minimum",
    )


class _SharedVerifiedObjectBackend:
    """Test-only shared byte backend; never installed by application startup."""

    def __init__(self, *, extra_retention_days: int = 0) -> None:
        self._lock = threading.RLock()
        self._objects: dict[str, dict[str, object]] = {}
        self.put_count = 0
        self.extra_retention_days = extra_retention_days

    def assert_ready(self, *, expected: RetentionPolicy) -> None:
        assert expected.retention_days >= 1

    def object_url(self, key: str, *, version_id: str | None = None) -> str:
        suffix = f"?versionId={quote(version_id, safe='')}" if version_id else ""
        return f"s3://shared/{quote(key, safe='/')}{suffix}"

    def put_immutable(
        self,
        *,
        key: str,
        body: bytes,
        content_hash: str,
        policy: RetentionPolicy,
    ) -> LockReceipt:
        with self._lock:
            existing = self._objects.get(key)
            if existing is None:
                self.put_count += 1
                requested_at = datetime.now(UTC).replace(microsecond=0)
                existing = {
                    "body": bytes(body),
                    "content_hash": content_hash,
                    "version_id": f"version-{self.put_count}",
                    "mode": policy.mode,
                    "retention_days": policy.retention_days,
                    "requested_at": requested_at,
                    "requested_until": requested_at
                    + timedelta(days=policy.retention_days),
                    "retain_until": requested_at
                    + timedelta(
                        days=policy.retention_days + self.extra_retention_days
                    ),
                }
                self._objects[key] = existing
            elif existing["content_hash"] != content_hash:
                raise ImmutableEvidenceConflict("conditional create found different bytes")
            return self._receipt(key, existing)

    def get_immutable(self, *, key: str, version_id: str) -> bytes:
        with self._lock:
            obj = self._objects[key]
            assert obj["version_id"] == version_id
            return bytes(obj["body"])

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
        with self._lock:
            obj = self._objects[key]
            assert obj["version_id"] == version_id
            assert obj["content_hash"] == content_hash
            assert obj["mode"] == policy.mode
            assert obj["requested_at"] == requested_at
            assert obj["requested_until"] == requested_retain_until
            if obj["retain_until"] < minimum_retain_until:  # type: ignore[operator]
                raise EvidenceObjectStoreUnavailable(
                    "Object Lock retention was shortened below the durable observed minimum."
                )
            return self._receipt(
                key,
                obj,
                minimum_retain_until=minimum_retain_until,
                original_verified_at=original_verified_at,
            )

    def tamper_for_test(self, key: str, body: bytes) -> None:
        with self._lock:
            self._objects[key]["body"] = body

    def shorten_retention_for_test(self, key: str, retain_until: datetime) -> None:
        with self._lock:
            self._objects[key]["retain_until"] = retain_until

    def _receipt(
        self,
        key: str,
        obj: dict[str, object],
        *,
        minimum_retain_until: datetime | None = None,
        original_verified_at: datetime | None = None,
    ) -> LockReceipt:
        version_id = str(obj["version_id"])
        actual_hash = hashlib.sha256(bytes(obj["body"])).hexdigest()
        observed_until = obj["retain_until"]
        minimum_ok = (
            minimum_retain_until is None
            or (
                isinstance(observed_until, datetime)
                and observed_until >= minimum_retain_until
            )
        )
        verification = issue_test_object_lock_receipt(
            expected={
                "bucket": "shared",
                "key": key,
                "version_id": version_id,
                "content_sha256": str(obj["content_hash"]),
                "mode": obj["mode"],
                "retention_days": obj["retention_days"],
                "requested_at": obj["requested_at"],
                "retain_until": obj["requested_until"],
            },
            observed={
                "bucket": "shared",
                "key": key,
                "get_version_id": version_id,
                "head_version_id": version_id,
                "content_sha256": actual_hash,
                "mode": obj["mode"],
                "retain_until": obj["retain_until"],
                "reread_verified": minimum_ok,
            },
            verified_at=original_verified_at,
        )
        return LockReceipt(
            object_url=self.object_url(key, version_id=version_id),
            version_id=version_id,
            retain_until=obj["retain_until"],  # type: ignore[arg-type]
            mode=obj["mode"],  # type: ignore[arg-type]
            content_hash=actual_hash,
            reread_verified=verification.verified,
            verification_receipt=verification,
        )


class _FakeS3Body:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body


class _PreconditionFailed(Exception):
    response = {
        "Error": {"Code": "PreconditionFailed"},
        "ResponseMetadata": {"HTTPStatusCode": 412},
    }


class _ObjectLockS3:
    def __init__(
        self,
        *,
        ready: bool = True,
        version_id: str = "s3-version-1",
        naive_retention_metadata: bool = False,
    ) -> None:
        self.ready = ready
        self.version_id = version_id
        self.naive_retention_metadata = naive_retention_metadata
        self.objects: dict[tuple[str, str], dict[str, object]] = {}
        self.put_calls: list[dict[str, object]] = []

    def get_object_lock_configuration(self, **kwargs) -> dict:
        del kwargs
        return {
            "ObjectLockConfiguration": {
                "ObjectLockEnabled": "Enabled" if self.ready else "Disabled"
            }
        }

    def get_bucket_versioning(self, **kwargs) -> dict:
        del kwargs
        return {"Status": "Enabled" if self.ready else "Suspended"}

    def put_object(self, **kwargs) -> dict:
        self.put_calls.append(dict(kwargs))
        address = (str(kwargs["Bucket"]), str(kwargs["Key"]))
        if address in self.objects:
            raise _PreconditionFailed()
        version = self.version_id
        metadata = dict(kwargs["Metadata"])
        if self.naive_retention_metadata:
            metadata["retention-requested-at"] = str(
                metadata["retention-requested-at"]
            ).replace("+00:00", "")
        self.objects[address] = {
            "body": bytes(kwargs["Body"]),
            "version_id": version,
            "mode": kwargs["ObjectLockMode"],
            "retain_until": kwargs["ObjectLockRetainUntilDate"],
            "metadata": metadata,
        }
        return {"VersionId": version, "ETag": '"etag"'}

    def head_object(self, **kwargs) -> dict:
        obj = self.objects[(str(kwargs["Bucket"]), str(kwargs["Key"]))]
        assert not kwargs.get("VersionId") or kwargs["VersionId"] == obj["version_id"]
        return {
            "VersionId": obj["version_id"],
            "ObjectLockMode": obj["mode"],
            "ObjectLockRetainUntilDate": obj["retain_until"],
            "Metadata": dict(obj["metadata"]),
        }

    def get_object(self, **kwargs) -> dict:
        obj = self.objects[(str(kwargs["Bucket"]), str(kwargs["Key"]))]
        assert kwargs["VersionId"] == obj["version_id"]
        return {
            "Body": _FakeS3Body(bytes(obj["body"])),
            "VersionId": obj["version_id"],
        }


def _repository(
    store: SqliteStateStore,
    backend: _SharedVerifiedObjectBackend,
    replica: str,
) -> EvidencePacketRepository:
    return EvidencePacketRepository(
        store=store,
        backend=backend,
        policy=RetentionPolicy(mode="GOVERNANCE", retention_days=30),
        replica_id=replica,
    )


def _packet(trace_id: str, *, text: str = "measured output") -> dict:
    return {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": trace_id,
        "generated_at": "2026-07-13T00:00:00+00:00",
        "input": {"audit_id": f"audit-{trace_id}", "text": "test"},
        "output": {"text": text},
        "provenance": {"method_label": "test"},
        "claim_levels": [],
        "caveats": ["source test only"],
    }


def test_s3_backend_requires_versioning_and_object_lock_and_rereads_receipt() -> None:
    fake = _ObjectLockS3()
    backend = S3ObjectLockPacketBackend(
        bucket="packet-bucket",
        prefix="cas/packet-objects",
        client=fake,
    )
    policy = RetentionPolicy(mode="GOVERNANCE", retention_days=30)
    body = b'{"trace_id":"trace-s3"}'
    content_hash = hashlib.sha256(body).hexdigest()

    backend.assert_ready(expected=policy)
    first = backend.put_immutable(
        key="tenants/key/packet.json",
        body=body,
        content_hash=content_hash,
        policy=policy,
    )
    second = backend.put_immutable(
        key="tenants/key/packet.json",
        body=body,
        content_hash=content_hash,
        policy=policy,
    )

    assert first.is_verifiable() and second.is_verifiable()
    assert first.version_id == second.version_id == "s3-version-1"
    assert fake.put_calls[0]["IfNoneMatch"] == "*"
    assert fake.put_calls[0]["ObjectLockMode"] == "GOVERNANCE"
    assert fake.put_calls[0]["ContentMD5"]


def test_s3_receipt_percent_encodes_opaque_version_and_rejects_non_s3_scheme() -> None:
    opaque_version = "opaque+aws/version=="
    fake = _ObjectLockS3(version_id=opaque_version)
    backend = S3ObjectLockPacketBackend(
        bucket="packet-bucket",
        prefix="cas/packet-objects",
        client=fake,
    )
    body = b'{"trace_id":"trace-opaque-version"}'
    receipt = backend.put_immutable(
        key="tenants/key/packet.json",
        body=body,
        content_hash=hashlib.sha256(body).hexdigest(),
        policy=RetentionPolicy(mode="GOVERNANCE", retention_days=30),
    )

    assert receipt.is_verifiable() is True
    assert "versionId=opaque%2Baws%2Fversion%3D%3D" in receipt.object_url
    assert "+" not in receipt.object_url.split("versionId=", 1)[1]
    assert replace(receipt, object_url=receipt.object_url.replace("s3://", "https://")).is_verifiable() is False


def test_s3_collision_never_uses_shortened_observed_deadline_as_expectation() -> None:
    fake = _ObjectLockS3()
    backend = S3ObjectLockPacketBackend(
        bucket="packet-bucket",
        prefix="cas/packet-objects",
        client=fake,
    )
    policy = RetentionPolicy(mode="GOVERNANCE", retention_days=30)
    body = b'{"trace_id":"trace-collision"}'
    content_hash = hashlib.sha256(body).hexdigest()
    backend.put_immutable(
        key="tenants/key/collision.json",
        body=body,
        content_hash=content_hash,
        policy=policy,
    )
    stored = fake.objects[("packet-bucket", "cas/packet-objects/tenants/key/collision.json")]
    metadata = stored["metadata"]
    assert isinstance(metadata, dict)
    requested_at = datetime.fromisoformat(str(metadata["retention-requested-at"]))
    stored["retain_until"] = requested_at + timedelta(days=2)

    with pytest.raises(
        EvidenceObjectStoreUnavailable,
        match="shortened below its durable observed minimum",
    ):
        backend.put_immutable(
            key="tenants/key/collision.json",
            body=body,
            content_hash=content_hash,
            policy=policy,
        )


def test_s3_collision_rejects_byte_identical_weaker_winner_policy() -> None:
    fake = _ObjectLockS3()
    backend = S3ObjectLockPacketBackend(
        bucket="packet-bucket",
        prefix="cas/packet-objects",
        client=fake,
    )
    body = b'{"trace_id":"trace-weaker-collision"}'
    content_hash = hashlib.sha256(body).hexdigest()
    backend.put_immutable(
        key="tenants/key/weaker.json",
        body=body,
        content_hash=content_hash,
        policy=RetentionPolicy(mode="GOVERNANCE", retention_days=1),
    )

    with pytest.raises(
        EvidenceObjectStoreUnavailable,
        match="weaker or different retention policy",
    ):
        backend.put_immutable(
            key="tenants/key/weaker.json",
            body=body,
            content_hash=content_hash,
            policy=RetentionPolicy(mode="COMPLIANCE", retention_days=30),
        )


def test_s3_retention_metadata_rejects_naive_request_timestamp() -> None:
    backend = S3ObjectLockPacketBackend(
        bucket="packet-bucket",
        prefix="cas/packet-objects",
        client=_ObjectLockS3(naive_retention_metadata=True),
    )
    body = b'{"trace_id":"trace-naive-metadata"}'

    with pytest.raises(
        EvidenceObjectStoreUnavailable,
        match="timezone-aware request boundary",
    ):
        backend.put_immutable(
            key="tenants/key/naive.json",
            body=body,
            content_hash=hashlib.sha256(body).hexdigest(),
            policy=RetentionPolicy(mode="GOVERNANCE", retention_days=30),
        )


def test_s3_backend_fails_closed_without_bucket_object_lock() -> None:
    backend = S3ObjectLockPacketBackend(
        bucket="packet-bucket",
        prefix="cas/packet-objects",
        client=_ObjectLockS3(ready=False),
    )
    with pytest.raises(EvidenceObjectStoreUnavailable, match="ObjectLockEnabled"):
        backend.assert_ready(
            expected=RetentionPolicy(mode="GOVERNANCE", retention_days=30)
        )


def test_packet_bytes_and_index_survive_restart_and_second_replica(tmp_path: Path) -> None:
    path = tmp_path / "shared-state.db"
    backend = _SharedVerifiedObjectBackend()
    first_store = SqliteStateStore(path)
    second_store = SqliteStateStore(path)
    first = _repository(first_store, backend, "replica-a")
    second = _repository(second_store, backend, "replica-b")
    packet = _packet("trace-restart")

    receipt = first.put_packet(
        tenant_id="tenant-a",
        account_id="account-a",
        namespace="",
        trace_id="trace-restart",
        packet=packet,
    )

    assert receipt.is_verifiable()
    assert second.load_packet(
        tenant_id="tenant-a", namespace="", trace_id="trace-restart"
    ) == packet
    with pytest.raises(FileNotFoundError):
        second.load_packet(tenant_id="tenant-b", namespace="", trace_id="trace-restart")
    assert len(second_store.list("tenant-a", PACKET_INDEX_KIND)) == 1
    assert second_store.list("tenant-b", PACKET_INDEX_KIND) == ()

    first_store.close()
    second_store.close()
    reopened_store = SqliteStateStore(path)
    restarted = _repository(reopened_store, backend, "replica-after-restart")
    assert restarted.load_packet(
        tenant_id="tenant-a", namespace="", trace_id="trace-restart"
    ) == packet
    reopened_store.close()


def test_packet_index_inventory_is_redacted_scoped_sorted_and_filterable(
    tmp_path: Path,
) -> None:
    store = SqliteStateStore(tmp_path / "packet-inventory.db")
    backend = _SharedVerifiedObjectBackend()
    repository = _repository(store, backend, "inventory-replica")
    for namespace, trace_id in (
        ("zeta", "trace-z"),
        ("", "trace-default"),
        ("alpha", "trace-a"),
    ):
        repository.put_packet(
            tenant_id="tenant-inventory",
            account_id="account-inventory",
            namespace=namespace,
            trace_id=trace_id,
            packet=_packet(trace_id),
        )
    repository.put_packet(
        tenant_id="tenant-other",
        namespace="alpha",
        trace_id="trace-other",
        packet=_packet("trace-other"),
    )

    inventory = repository.list_packet_indices(tenant_id="tenant-inventory")
    default_only = repository.list_packet_indices(
        tenant_id="tenant-inventory", namespace=""
    )

    assert [(row.namespace, row.trace_id) for row in inventory] == [
        ("", "trace-default"),
        ("alpha", "trace-a"),
        ("zeta", "trace-z"),
    ]
    assert [(row.namespace, row.trace_id) for row in default_only] == [
        ("", "trace-default")
    ]
    assert all(row.tenant_id == "tenant-inventory" for row in inventory)
    assert all(row.account_id == "account-inventory" for row in inventory)
    assert all(
        row.inventory_scope == "CONFIGURED_TENANT_STATE_STORE_ONLY"
        and row.off_registry_execution_absence == "NOT_ESTABLISHED"
        for row in inventory
    )
    assert not hasattr(inventory[0], "object_key")
    assert repository.list_packet_indices(tenant_id="tenant-missing") == ()
    store.close()


def test_packet_index_inventory_fails_closed_on_malformed_row(tmp_path: Path) -> None:
    store = SqliteStateStore(tmp_path / "packet-inventory-malformed.db")
    backend = _SharedVerifiedObjectBackend()
    repository = _repository(store, backend, "inventory-replica")
    repository.put_packet(
        tenant_id="tenant-inventory",
        namespace="lifecycle",
        trace_id="trace-malformed",
        packet=_packet("trace-malformed"),
    )
    index = store.list("tenant-inventory", PACKET_INDEX_KIND)[0]
    malformed = dict(index.payload)
    malformed["byte_length"] = True
    store.put(index.with_payload(malformed), expected_version=index.version)

    with pytest.raises(
        EvidenceObjectStoreUnavailable, match="inventory row is malformed"
    ):
        repository.list_packet_indices(tenant_id="tenant-inventory")
    store.close()


def test_packet_index_inventory_fails_closed_when_enumeration_is_unavailable() -> None:
    class _ListFailingStore:
        def list(self, tenant_id: str, kind: str):
            del tenant_id, kind
            raise StateStoreError("synthetic enumeration failure")

    repository = EvidencePacketRepository(
        store=_ListFailingStore(),  # type: ignore[arg-type]
        backend=_SharedVerifiedObjectBackend(),
        policy=RetentionPolicy(mode="GOVERNANCE", retention_days=30),
        replica_id="inventory-failure-replica",
    )

    with pytest.raises(
        EvidenceObjectStoreUnavailable, match="enumeration is unavailable"
    ):
        repository.list_packet_indices(tenant_id="tenant-inventory")


def test_durable_reverify_uses_stored_minimum_and_preserves_original_verified_at(
    tmp_path: Path,
) -> None:
    store = SqliteStateStore(tmp_path / "durable-minimum.db")
    backend = _SharedVerifiedObjectBackend()
    first = _repository(store, backend, "writer")
    packet = _packet("trace-durable-minimum")
    first.put_packet(
        tenant_id="tenant-minimum",
        namespace="",
        trace_id="trace-durable-minimum",
        packet=packet,
    )
    index = store.list("tenant-minimum", PACKET_INDEX_KIND)[0]
    original = index.payload["object_lock_verification"]
    assert isinstance(original, dict)

    # Current runtime policy is deliberately weaker and a different mode.  A
    # restart must still evaluate the immutable receipt against the index that
    # was written under GOVERNANCE/30 days.
    restarted = EvidencePacketRepository(
        store=store,
        backend=backend,
        policy=RetentionPolicy(mode="COMPLIANCE", retention_days=1),
        replica_id="restart-with-drift",
    )
    first_check = restarted.verify_packet(
        tenant_id="tenant-minimum",
        namespace="",
        trace_id="trace-durable-minimum",
    )
    current = first_check["object_lock_verification"]
    assert first_check["match"] is True
    assert current["expected"]["mode"] == "GOVERNANCE"
    assert current["expected"]["retention_days"] == 30
    assert current["expected"]["version_id"] == index.payload["version_id"]
    assert current["expected"]["content_sha256"] == index.payload["content_sha256"]
    assert current["verified_at"] == original["verified_at"]
    assert current["evaluated_at"] >= current["verified_at"]

    key = str(index.payload["object_key"])
    requested_at = datetime.fromisoformat(str(index.payload["retention_requested_at"]))
    backend.shorten_retention_for_test(key, requested_at + timedelta(days=2))
    shortened = restarted.verify_packet(
        tenant_id="tenant-minimum",
        namespace="",
        trace_id="trace-durable-minimum",
    )

    assert shortened["match"] is False
    assert "shortened below the durable observed minimum" in shortened["notes"]
    assert "object_lock_verification" not in shortened
    store.close()


def test_bucket_default_stronger_deadline_survives_restart_and_reverify(
    tmp_path: Path,
) -> None:
    store = SqliteStateStore(tmp_path / "stronger-bucket-default.db")
    backend = _SharedVerifiedObjectBackend(extra_retention_days=45)
    writer = _repository(store, backend, "writer")
    packet = _packet("trace-stronger")
    packet_hash = evidence_packet_without_hashes_sha256(packet)
    entry = writer.append_hash_log(
        tenant_id="tenant-stronger",
        namespace="",
        trace_id="trace-stronger",
        audit_id="audit-stronger",
        packet_without_hashes_sha256=packet_hash,
        operation="test_stronger_bucket_default",
    )
    packet["hashes"] = {
        "packet_without_hashes_sha256": packet_hash,
        "hash_log_entry_sha256": entry["entry_sha256"],
        "hash_log_previous_entry_sha256": entry["previous_entry_sha256"],
    }
    writer.put_packet(
        tenant_id="tenant-stronger",
        namespace="",
        trace_id="trace-stronger",
        packet=packet,
    )
    index = store.list("tenant-stronger", PACKET_INDEX_KIND)[0]
    requested = datetime.fromisoformat(str(index.payload["retention_requested_until"]))
    minimum = datetime.fromisoformat(
        str(index.payload["object_lock_minimum_retain_until"])
    )
    raw_verification = index.payload["object_lock_verification"]
    assert isinstance(raw_verification, dict)
    assert datetime.fromisoformat(
        str(raw_verification["expected"]["retain_until"])
    ) == requested
    assert datetime.fromisoformat(
        str(raw_verification["observed"]["retain_until"])
    ) == minimum
    assert minimum == requested + timedelta(days=45)

    restarted = EvidencePacketRepository(
        store=store,
        backend=backend,
        policy=RetentionPolicy(mode="COMPLIANCE", retention_days=1),
        replica_id="restart",
    )
    check = restarted.verify_packet(
        tenant_id="tenant-stronger",
        namespace="",
        trace_id="trace-stronger",
    )
    assert check["match"] is True
    assert check["object_lock_verification"]["verified"] is True
    assert datetime.fromisoformat(
        check["object_lock_verification"]["expected"]["retain_until"]
    ) == requested
    assert datetime.fromisoformat(
        check["object_lock_verification"]["observed"]["retain_until"]
    ) == minimum
    loaded_entry, chain_ok = restarted.load_hash_log_entry(
        tenant_id="tenant-stronger",
        namespace="",
        trace_id="trace-stronger",
        entry_sha256=entry["entry_sha256"],
    )
    assert loaded_entry["entry_sha256"] == entry["entry_sha256"]
    assert chain_ok is True
    store.close()


def test_durable_packet_index_rejects_naive_retention_timestamp(tmp_path: Path) -> None:
    store = SqliteStateStore(tmp_path / "naive-index.db")
    backend = _SharedVerifiedObjectBackend()
    repository = _repository(store, backend, "writer")
    repository.put_packet(
        tenant_id="tenant-naive",
        namespace="",
        trace_id="trace-naive-index",
        packet=_packet("trace-naive-index"),
    )
    index = store.list("tenant-naive", PACKET_INDEX_KIND)[0]
    corrupted = dict(index.payload)
    corrupted["retention_requested_at"] = str(
        corrupted["retention_requested_at"]
    ).replace("+00:00", "")
    store.put(index.with_payload(corrupted), expected_version=index.version)

    check = repository.verify_packet(
        tenant_id="tenant-naive",
        namespace="",
        trace_id="trace-naive-index",
    )

    assert check["match"] is False
    assert "missing its durable retention request" in check["notes"]
    store.close()


def test_trace_is_immutable_but_same_trace_can_exist_in_two_tenants(tmp_path: Path) -> None:
    store = SqliteStateStore(tmp_path / "tenant-isolation.db")
    backend = _SharedVerifiedObjectBackend()
    repository = _repository(store, backend, "replica")

    repository.put_packet(
        tenant_id="tenant-a",
        namespace="",
        trace_id="same-trace",
        packet=_packet("same-trace", text="tenant a"),
    )
    with pytest.raises(ImmutableEvidenceConflict):
        repository.put_packet(
            tenant_id="tenant-a",
            namespace="",
            trace_id="same-trace",
            packet=_packet("same-trace", text="mutated"),
        )

    repository.put_packet(
        tenant_id="tenant-b",
        namespace="",
        trace_id="same-trace",
        packet=_packet("same-trace", text="tenant b"),
    )
    assert repository.load_packet(
        tenant_id="tenant-a", namespace="", trace_id="same-trace"
    )["output"]["text"] == "tenant a"
    assert repository.load_packet(
        tenant_id="tenant-b", namespace="", trace_id="same-trace"
    )["output"]["text"] == "tenant b"
    assert backend.put_count == 2
    store.close()


def test_corrupt_index_cannot_redirect_one_tenant_to_another_object_key(
    tmp_path: Path,
) -> None:
    store = SqliteStateStore(tmp_path / "index-redirect.db")
    backend = _SharedVerifiedObjectBackend()
    repository = _repository(store, backend, "replica")
    repository.put_packet(
        tenant_id="tenant-a",
        namespace="",
        trace_id="shared-trace",
        packet=_packet("shared-trace", text="tenant a"),
    )
    repository.put_packet(
        tenant_id="tenant-b",
        namespace="",
        trace_id="shared-trace",
        packet=_packet("shared-trace", text="tenant b"),
    )
    index_a = store.list("tenant-a", PACKET_INDEX_KIND)[0]
    index_b = store.list("tenant-b", PACKET_INDEX_KIND)[0]
    redirected = dict(index_a.payload)
    redirected["object_key"] = index_b.payload["object_key"]
    store.put(index_a.with_payload(redirected), expected_version=index_a.version)

    with pytest.raises(EvidenceObjectStoreUnavailable, match="tenant/namespace/trace"):
        repository.load_packet(
            tenant_id="tenant-a", namespace="", trace_id="shared-trace"
        )
    store.close()


def test_two_replicas_concurrently_create_one_packet_and_one_index(tmp_path: Path) -> None:
    path = tmp_path / "packet-race.db"
    backend = _SharedVerifiedObjectBackend()
    # Two repository instances share the one StateStore arbitration seam.  In
    # production that seam is Postgres; SQLite intentionally supports one host/
    # one shared handle and is used here as the durable contract implementation.
    shared_store = SqliteStateStore(path)
    stores = [shared_store, shared_store]
    repositories = [
        _repository(stores[0], backend, "replica-a"),
        _repository(stores[1], backend, "replica-b"),
    ]
    packet = _packet("trace-race")

    def write(index: int) -> str:
        return repositories[index % 2].put_packet(
            tenant_id="tenant-race",
            namespace="",
            trace_id="trace-race",
            packet=packet,
        ).version_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        versions = list(pool.map(write, range(32)))

    assert set(versions) == {"version-1"}
    assert backend.put_count == 1
    assert len(stores[0].list("tenant-race", PACKET_INDEX_KIND)) == 1
    shared_store.close()


def test_two_replica_hash_log_append_is_concurrency_safe_and_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "hash-log-race.db"
    backend = _SharedVerifiedObjectBackend()
    shared_store = SqliteStateStore(path)
    stores = [shared_store, shared_store]
    repositories = [
        _repository(stores[0], backend, "replica-a"),
        _repository(stores[1], backend, "replica-b"),
    ]

    def append(index: int) -> dict:
        trace_id = f"trace-{index}"
        packet = _packet(trace_id)
        packet_hash = evidence_packet_without_hashes_sha256(packet)
        repository = repositories[index % 2]
        entry = repository.append_hash_log(
            tenant_id="tenant-chain",
            namespace="",
            trace_id=trace_id,
            audit_id=f"audit-{index}",
            packet_without_hashes_sha256=packet_hash,
            operation="test_concurrent_append",
        )
        packet["hashes"] = {
            "packet_without_hashes_sha256": packet_hash,
            "hash_log_entry_sha256": entry["entry_sha256"],
            "hash_log_previous_entry_sha256": entry["previous_entry_sha256"],
        }
        repository.put_packet(
            tenant_id="tenant-chain",
            namespace="",
            trace_id=trace_id,
            packet=packet,
        )
        return entry

    with ThreadPoolExecutor(max_workers=8) as pool:
        entries = list(pool.map(append, range(24)))

    assert len({entry["entry_sha256"] for entry in entries}) == 24
    assert len(stores[0].list("tenant-chain", HASH_LOG_ENTRY_KIND)) == 24
    for entry in entries:
        loaded, chain_ok = repositories[1].load_hash_log_entry(
            tenant_id="tenant-chain",
            namespace="",
            trace_id=entry["trace_id"],
            entry_sha256=entry["entry_sha256"],
        )
        assert loaded == entry
        assert chain_ok is True

    same_packet = _packet("one-trace")
    same_hash = evidence_packet_without_hashes_sha256(same_packet)

    def append_same(index: int) -> str:
        repository = repositories[index % 2]
        entry = repository.append_hash_log(
            tenant_id="tenant-idempotent",
            namespace="",
            trace_id="one-trace",
            audit_id="one-audit",
            packet_without_hashes_sha256=same_hash,
            operation="test_idempotent_append",
        )
        packet = dict(same_packet)
        packet["hashes"] = {
            "packet_without_hashes_sha256": same_hash,
            "hash_log_entry_sha256": entry["entry_sha256"],
            "hash_log_previous_entry_sha256": entry["previous_entry_sha256"],
        }
        repository.put_packet(
            tenant_id="tenant-idempotent",
            namespace="",
            trace_id="one-trace",
            packet=packet,
        )
        return str(entry["entry_sha256"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        same_entries = list(pool.map(append_same, range(24)))
    assert len(set(same_entries)) == 1
    assert len(stores[0].list("tenant-idempotent", HASH_LOG_ENTRY_KIND)) == 1
    shared_store.close()


def test_existing_packet_helpers_switch_to_shared_tenant_storage(tmp_path: Path) -> None:
    path = tmp_path / "helper-integration.db"
    backend = _SharedVerifiedObjectBackend()
    first_store = SqliteStateStore(path)
    second_store = SqliteStateStore(path)
    first = _repository(first_store, backend, "replica-a")
    second = _repository(second_store, backend, "replica-b")
    packet = _packet("trace-helper")
    packet_hash = evidence_packet_without_hashes_sha256(packet)

    with evidence_packet_storage_scope(
        tenant_id="tenant-helper", account_id="account-helper", repository=first
    ):
        entry = append_evidence_packet_hash_log_entry(
            trace_id="trace-helper",
            audit_id="audit-helper",
            packet_without_hashes_sha256=packet_hash,
            operation="test_helper_integration",
        )
        packet["hashes"] = {
            "packet_without_hashes_sha256": packet_hash,
            "hash_log_entry_sha256": entry["entry_sha256"],
            "hash_log_previous_entry_sha256": entry["previous_entry_sha256"],
            "hash_log_path": str(evidence_hash_log_path()),
        }
        assert str(evidence_packet_store_path("trace-helper")).startswith(
            "s3://shared/tenants/"
        )
        write_evidence_packet_to_store("trace-helper", packet)

    with evidence_packet_storage_scope(
        tenant_id="tenant-helper", account_id="account-helper", repository=second
    ):
        loaded = load_evidence_packet_from_store("trace-helper")
        checks = verify_evidence_packet_hash_chain(loaded)

    assert loaded == packet
    assert all(check["match"] for check in checks)
    assert any(check["artifact"] == "tenant_packet_object_store" for check in checks)
    assert packet["hashes"]["hash_log_path"].startswith(
        "state-store://evidence-packet-hash-log/"
    )
    first_store.close()
    second_store.close()


def test_fleet_merge_publication_is_retry_and_concurrency_idempotent(
    tmp_path: Path, monkeypatch
) -> None:
    from api.services import cas_harness_evidence_anchor

    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")

    def legacy_anchor_must_not_run(**kwargs):
        raise AssertionError("tenant Object-Lock publication called the legacy S3 anchor")

    monkeypatch.setattr(
        cas_harness_evidence_anchor,
        "anchor_hash_log_entry",
        legacy_anchor_must_not_run,
    )
    store = SqliteStateStore(tmp_path / "fleet-merge-idempotent.db")
    backend = _SharedVerifiedObjectBackend()
    repository = _repository(store, backend, "fleet-merge-replica")
    trace_id = "trace-fleet-merge-idempotent"
    run = SimpleNamespace(
        audit_id="audit-fleet-merge-idempotent",
        created_at="2026-07-13T04:00:00+00:00",
        status="COMPLETE",
        verifier_gate_status="ready_for_verifier",
        merged_packet_trace_id=trace_id,
        jobs=[],
    )
    distributed = SimpleNamespace(
        plan=SimpleNamespace(
            model_id="customer/open-weight-20b",
            parameter_count_b=20,
            num_layers=8,
        )
    )
    first_attempt_not_before = datetime.now(UTC)

    def publish(_index: int) -> dict:
        with evidence_packet_storage_scope(
            tenant_id="tenant-fleet",
            account_id="account-fleet",
            repository=repository,
        ):
            packet = write_merged_fleet_evidence_packet(
                run=run, distributed=distributed
            )
            assert packet is not None
            return packet

    with ThreadPoolExecutor(max_workers=8) as pool:
        packets = list(pool.map(publish, range(16)))

    assert all(packet == packets[0] for packet in packets)
    assert datetime.fromisoformat(packets[0]["generated_at"]) >= first_attempt_not_before
    assert packets[0]["hashes"]["external_anchor"]["mode"] == (
        "tenant_object_lock_repository"
    )
    assert backend.put_count == 1
    assert len(store.list("tenant-fleet", HASH_LOG_ENTRY_KIND)) == 1
    assert len(store.list("tenant-fleet", PACKET_INDEX_KIND)) == 1
    assert len(store.list("tenant-fleet", PUBLICATION_INTENT_KIND)) == 1
    with pytest.raises(ImmutableEvidenceConflict, match="publication intent"):
        repository.claim_publication_timestamp(
            tenant_id="tenant-fleet",
            namespace="",
            trace_id=trace_id,
            audit_id="audit-fleet-merge-idempotent",
            account_id="account-other",
        )
    store.close()


def test_hash_append_without_worm_packet_is_invalid_until_retry_repairs_it(
    tmp_path: Path,
) -> None:
    store = SqliteStateStore(tmp_path / "append-crash.db")
    backend = _SharedVerifiedObjectBackend()
    repository = _repository(store, backend, "replica")
    packet = _packet("trace-crash-boundary")
    packet_hash = evidence_packet_without_hashes_sha256(packet)
    entry = repository.append_hash_log(
        tenant_id="tenant-crash",
        namespace="",
        trace_id="trace-crash-boundary",
        audit_id="audit-crash-boundary",
        packet_without_hashes_sha256=packet_hash,
        operation="test_crash_boundary",
    )

    _, before = repository.load_hash_log_entry(
        tenant_id="tenant-crash",
        namespace="",
        trace_id="trace-crash-boundary",
        entry_sha256=entry["entry_sha256"],
    )
    assert before is False

    # Retry uses the same durable entry and finishes the immutable object/index/
    # WORM-receipt side of the state machine.
    retried = repository.append_hash_log(
        tenant_id="tenant-crash",
        namespace="",
        trace_id="trace-crash-boundary",
        audit_id="audit-crash-boundary",
        packet_without_hashes_sha256=packet_hash,
        operation="test_crash_boundary",
    )
    assert retried["entry_sha256"] == entry["entry_sha256"]
    packet["hashes"] = {
        "packet_without_hashes_sha256": packet_hash,
        "hash_log_entry_sha256": entry["entry_sha256"],
        "hash_log_previous_entry_sha256": entry["previous_entry_sha256"],
    }
    repository.put_packet(
        tenant_id="tenant-crash",
        namespace="",
        trace_id="trace-crash-boundary",
        packet=packet,
    )
    _, after = repository.load_hash_log_entry(
        tenant_id="tenant-crash",
        namespace="",
        trace_id="trace-crash-boundary",
        entry_sha256=entry["entry_sha256"],
    )
    assert after is True
    store.close()


def test_packet_verify_detects_remote_byte_tampering(tmp_path: Path) -> None:
    store = SqliteStateStore(tmp_path / "tamper.db")
    backend = _SharedVerifiedObjectBackend()
    repository = _repository(store, backend, "replica")
    packet = _packet("trace-tamper")
    repository.put_packet(
        tenant_id="tenant-a", namespace="", trace_id="trace-tamper", packet=packet
    )
    index = store.list("tenant-a", PACKET_INDEX_KIND)[0]
    backend.tamper_for_test(str(index.payload["object_key"]), b'{"tampered":true}')

    check = repository.verify_packet(
        tenant_id="tenant-a", namespace="", trace_id="trace-tamper"
    )

    assert check["match"] is False
    with pytest.raises(Exception, match="does not match"):
        repository.load_packet(
            tenant_id="tenant-a", namespace="", trace_id="trace-tamper"
        )
    store.close()


@pytest.mark.parametrize(
    ("accepted", "generation_action", "expected_verdict"),
    ((True, "allow", "ACCEPT"), (False, "suppress", "SUPPRESS")),
)
def test_account_evidence_route_reads_shared_packet_from_repository(
    tmp_path: Path,
    monkeypatch,
    accepted: bool,
    generation_action: str,
    expected_verdict: str,
) -> None:
    """The FastAPI ownership dependency keeps tenant scope alive through the handler."""
    from api.main import app

    store = SqliteStateStore(tmp_path / "route-shared.db")
    backend = _SharedVerifiedObjectBackend()
    repository = _repository(store, backend, "route-replica")
    accounts = AccountStore(
        store, credential_pepper="route-test-credential-pepper-0123456789"
    )
    sessions = SessionStore(store)
    previous = {
        "shared_state_store": getattr(app.state, "shared_state_store", None),
        "state_ledger": getattr(app.state, "state_ledger", None),
        "account_store": getattr(app.state, "account_store", None),
        "session_store": getattr(app.state, "session_store", None),
        "evidence_packet_repository": getattr(
            app.state, "evidence_packet_repository", None
        ),
    }

    with TestClient(app) as client:
        monkeypatch.setattr(settings, "accounts_enabled", True)
        monkeypatch.setattr(settings, "evidence_packet_object_store_enabled", True)
        app.state.shared_state_store = store
        app.state.account_store = accounts
        app.state.session_store = sessions
        app.state.evidence_packet_repository = repository
        configure_evidence_packet_repository(repository)
        configure_audit_session_store(store)

        invite = accounts.create_invite(
            code="route-packet-invite", role="member", tenant_id="tenant-route"
        )
        credential = "casak_0123456789abcdefghijklmnopqrstuvwxyzABCDEFG"
        account = accounts.redeem_invite(
            code=invite.code,
            email_or_username="packet-route@example.com",
            api_credential=credential,
        )
        login = client.post(
            "/auth/token",
            json={
                "username": "packet-route@example.com",
                "api_credential": credential,
            },
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        trace_id = f"trace-route-shared-{expected_verdict.lower()}"
        packet = _packet(trace_id)
        packet.update(
            {
                "model": {
                    "model_key": "openai:gpt-4.1-mini",
                    "name": "openai:gpt-4.1-mini",
                },
                "provenance": {
                    "source_stage": "Stage 21A",
                    "source_reports": [
                        "stage19_verification_stack_report.json",
                        "stage20_generation_readiness_report.json",
                    ],
                },
                "readout": {"axis": "drive", "label": "F1", "confidence": 0.86},
                "ablation": {"status": "present", "effect": "targeted_drop"},
                "matched_controls": {
                    "status": "present",
                    "control": "random_same_rank",
                },
                "verification": {
                    "accepted": accepted,
                    "mode": "BALANCED",
                    "confidence_tier": "high",
                    "mode_profile": {"accepted_accuracy": 0.9816, "coverage": 0.7173},
                    "suppression_reasons": (
                        [] if accepted else ["verification_stack_rejected"]
                    ),
                },
                "generation_readiness": {
                    "generation_readiness": generation_action,
                    "risk_score": 0.11 if accepted else 0.9,
                    "policy_version": "stage20_v1",
                    "reasons": [],
                },
            }
        )
        packet_hash = evidence_packet_without_hashes_sha256(packet)
        with evidence_packet_storage_scope(
            tenant_id="tenant-route",
            account_id=account.account_id,
            repository=repository,
        ):
            entry = append_evidence_packet_hash_log_entry(
                trace_id=trace_id,
                audit_id="audit-route-shared",
                packet_without_hashes_sha256=packet_hash,
                operation="test_route_shared_packet",
            )
            packet["hashes"] = {
                "packet_without_hashes_sha256": packet_hash,
                "hash_log_entry_sha256": entry["entry_sha256"],
                "hash_log_previous_entry_sha256": entry["previous_entry_sha256"],
                "hash_log_path": str(evidence_hash_log_path()),
                "external_anchor": {"status": "disabled", "mode": "disabled"},
            }
            write_evidence_packet_to_store(trace_id, packet)
        record_evidence_ownership(
            store,
            tenant_id="tenant-route",
            account_id=account.account_id,
            trace_id=trace_id,
        )

        got = client.get(f"/evidence/{trace_id}", headers=headers)
        verified = client.post(f"/evidence/{trace_id}/verify", headers=headers)

        assert got.status_code == 200, got.text
        assert got.json() == packet
        for absent_optional_field in (
            "cas_expression",
            "copy_slot_trace",
            "distributed_fleet",
        ):
            assert absent_optional_field not in got.json()
        assert got.json()["output"]["text"] == "measured output"
        assert verified.status_code == 200, verified.text
        assert verified.json()["overall"] == "all_match"
        tenant_check = next(
            row
            for row in verified.json()["checks"]
            if row["artifact"] == "tenant_packet_object_store"
        )
        assert tenant_check["match"] is True
        assert tenant_check["object_lock_verification"]["verified"] is True
        assert tenant_check["object_lock_verification"]["verified_at"]
        assert tenant_check["object_lock_verification"]["evaluated_at"]

        created = client.post(
            "/api/cas-harness/audit/session",
            json={
                "model_id": "openai:gpt-4.1-mini",
                "audit_mode": "BALANCED",
                "prompt": "Assess this tenant packet.",
                "selected_modules": ["cognitive_bias", "provenance_trace"],
                "license_key": "placeholder-license",
                "evidence_packet_trace_id": trace_id,
            },
            headers=headers,
        )
        assert created.status_code == 200, created.text
        created_packet_chip = next(
            chip
            for chip in created.json()["provenance_chips"]
            if chip["id"] == "packet_proof"
        )
        assert created_packet_chip["status"] == "verified"
        assert created_packet_chip["object_lock_verification"]["verified"] is True

        ran = client.post(
            f"/api/cas-harness/audit/session/{created.json()['audit_id']}/run",
            headers=headers,
        )
        assert ran.status_code == 200, ran.text
        assert ran.json()["verdict"] == expected_verdict

    configure_evidence_packet_repository(None)
    configure_audit_session_store(None)
    for name, value in previous.items():
        setattr(app.state, name, value)
    store.close()
