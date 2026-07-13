from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import threading

import pytest
from fastapi.testclient import TestClient

from api.config import settings
from api.services.accounts.store import AccountStore
from api.services.cas_harness_evidence_object_store import (
    EvidenceObjectStoreUnavailable,
    EvidencePacketRepository,
    HASH_LOG_ENTRY_KIND,
    ImmutableEvidenceConflict,
    PACKET_INDEX_KIND,
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
)
from api.services.evidence_ownership import record_evidence_ownership
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.production.worm_writes import LockReceipt, RetentionPolicy
from api.services.sessions import SessionStore


class _SharedVerifiedObjectBackend:
    """Test-only shared byte backend; never installed by application startup."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._objects: dict[str, dict[str, object]] = {}
        self.put_count = 0

    def assert_ready(self, *, expected: RetentionPolicy) -> None:
        assert expected.retention_days >= 1

    def object_url(self, key: str, *, version_id: str | None = None) -> str:
        suffix = f"?versionId={version_id}" if version_id else ""
        return f"test-object-lock://shared/{key}{suffix}"

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
                existing = {
                    "body": bytes(body),
                    "content_hash": content_hash,
                    "version_id": f"version-{self.put_count}",
                    "mode": policy.mode,
                    "retain_until": datetime.now(UTC) + timedelta(days=policy.retention_days),
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
    ) -> LockReceipt:
        with self._lock:
            obj = self._objects[key]
            assert obj["version_id"] == version_id
            assert obj["content_hash"] == content_hash
            assert obj["mode"] == policy.mode
            return self._receipt(key, obj)

    def tamper_for_test(self, key: str, body: bytes) -> None:
        with self._lock:
            self._objects[key]["body"] = body

    def _receipt(self, key: str, obj: dict[str, object]) -> LockReceipt:
        version_id = str(obj["version_id"])
        return LockReceipt(
            object_url=self.object_url(key, version_id=version_id),
            version_id=version_id,
            retain_until=obj["retain_until"],  # type: ignore[arg-type]
            mode=obj["mode"],  # type: ignore[arg-type]
            content_hash=str(obj["content_hash"]),
            reread_verified=(
                hashlib.sha256(bytes(obj["body"])).hexdigest() == obj["content_hash"]
            ),
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
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready
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
        version = "s3-version-1"
        self.objects[address] = {
            "body": bytes(kwargs["Body"]),
            "version_id": version,
            "mode": kwargs["ObjectLockMode"],
            "retain_until": kwargs["ObjectLockRetainUntilDate"],
        }
        return {"VersionId": version, "ETag": '"etag"'}

    def head_object(self, **kwargs) -> dict:
        obj = self.objects[(str(kwargs["Bucket"]), str(kwargs["Key"]))]
        assert not kwargs.get("VersionId") or kwargs["VersionId"] == obj["version_id"]
        return {
            "VersionId": obj["version_id"],
            "ObjectLockMode": obj["mode"],
            "ObjectLockRetainUntilDate": obj["retain_until"],
        }

    def get_object(self, **kwargs) -> dict:
        obj = self.objects[(str(kwargs["Bucket"]), str(kwargs["Key"]))]
        assert kwargs["VersionId"] == obj["version_id"]
        return {"Body": _FakeS3Body(bytes(obj["body"]))}


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
            "test-object-lock://shared/tenants/"
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


def test_account_evidence_route_reads_shared_packet_from_repository(
    tmp_path: Path, monkeypatch
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

        packet = _packet("trace-route-shared")
        packet_hash = evidence_packet_without_hashes_sha256(packet)
        with evidence_packet_storage_scope(
            tenant_id="tenant-route",
            account_id=account.account_id,
            repository=repository,
        ):
            entry = append_evidence_packet_hash_log_entry(
                trace_id="trace-route-shared",
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
            write_evidence_packet_to_store("trace-route-shared", packet)
        record_evidence_ownership(
            store,
            tenant_id="tenant-route",
            account_id=account.account_id,
            trace_id="trace-route-shared",
        )

        got = client.get("/evidence/trace-route-shared", headers=headers)
        verified = client.post("/evidence/trace-route-shared/verify", headers=headers)

        assert got.status_code == 200, got.text
        assert got.json()["output"]["text"] == "measured output"
        assert verified.status_code == 200, verified.text
        assert verified.json()["overall"] == "all_match"
        assert any(
            row["artifact"] == "tenant_packet_object_store" and row["match"] is True
            for row in verified.json()["checks"]
        )

    configure_evidence_packet_repository(None)
    for name, value in previous.items():
        setattr(app.state, name, value)
    store.close()
