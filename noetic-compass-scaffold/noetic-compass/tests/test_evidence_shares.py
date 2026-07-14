"""Security and durability tests for read-only Evidence Packet shares."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest
from fastapi.testclient import TestClient

from api.config import Settings, settings
from api.services.accounts.store import AccountStore
from api.services.evidence_ownership import record_evidence_ownership
from api.services.evidence_shares import (
    EVIDENCE_SHARE_EVENT_KIND,
    EVIDENCE_SHARE_KIND,
    EVIDENCE_SHARE_LOCATOR_KIND,
    EVIDENCE_SHARE_LOCATOR_TENANT,
    EvidenceShareNotFound,
    EvidenceShareService,
    EvidenceShareUnavailable,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.sessions import SessionStore


_PEPPER = "share-token-pepper-stable-0123456789abcdef"


class _Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class _ExactPacketRepository:
    """Test repository that exposes the hash of exact immutable bytes."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str, str], bytes] = {}

    def put_packet(
        self,
        *,
        tenant_id: str,
        trace_id: str,
        packet: dict,
        namespace: str = "",
        noncanonical_bytes: bool = False,
    ) -> None:
        if noncanonical_bytes:
            body = json.dumps(packet, sort_keys=False, indent=2).encode("utf-8")
        else:
            body = json.dumps(
                packet, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        self.objects[(tenant_id, namespace, trace_id)] = body

    def load_packet_with_content_sha256(
        self, *, tenant_id: str, namespace: str, trace_id: str
    ) -> tuple[dict, str]:
        body = self.objects[(tenant_id, namespace, trace_id)]
        return json.loads(body.decode("utf-8")), hashlib.sha256(body).hexdigest()


@pytest.fixture
def service_fixture(tmp_path):
    db = tmp_path / "shares.db"
    store = SqliteStateStore(db)
    repository = _ExactPacketRepository()
    clock = _Clock(datetime(2026, 7, 14, 18, 0, tzinfo=timezone.utc))
    packet = {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": "trace-share-1",
        "input": {"text": "measured input"},
        "output": {"text": "measured output"},
        "hashes": {"packet_without_hashes_sha256": "a" * 64},
        "claim_levels": [],
    }
    repository.put_packet(
        tenant_id="tenant-a",
        trace_id="trace-share-1",
        packet=packet,
        # Deliberately differs from canonical reserialization. The service must
        # bind the durable repository's exact-byte digest, not this dict's shape.
        noncanonical_bytes=True,
    )
    record_evidence_ownership(
        store,
        tenant_id="tenant-a",
        account_id="acct-creator",
        trace_id="trace-share-1",
    )
    service = EvidenceShareService(
        store=store,
        repository=repository,
        token_pepper=_PEPPER,
        clock=clock,
    )
    try:
        yield SimpleNamespace(
            db=db,
            store=store,
            repository=repository,
            clock=clock,
            packet=packet,
            service=service,
        )
    finally:
        store.close()


def _create(ctx, *, expires_at: datetime | None = None):
    return ctx.service.create_share(
        tenant_id="tenant-a",
        account_id="acct-creator",
        trace_id="trace-share-1",
        expires_at=expires_at or ctx.clock.now + timedelta(hours=1),
        request_id="request-create-1",
    )


def _all_payloads(ctx) -> list[dict]:
    payloads: list[dict] = []
    for tenant, kind in (
        ("tenant-a", EVIDENCE_SHARE_KIND),
        ("tenant-a", EVIDENCE_SHARE_EVENT_KIND),
        (EVIDENCE_SHARE_LOCATOR_TENANT, EVIDENCE_SHARE_LOCATOR_KIND),
    ):
        payloads.extend(dict(record.payload) for record in ctx.store.list(tenant, kind))
    return payloads


def test_create_returns_token_once_and_persists_only_keyed_hash(service_fixture) -> None:
    ctx = service_fixture
    created = _create(ctx)
    assert created.token
    assert created.share.status(now=ctx.clock.now) == "active"

    persisted = ctx.store.get("tenant-a", EVIDENCE_SHARE_KIND, created.share.share_id)
    assert persisted is not None
    token_hash = str(persisted.payload["token_hash"])
    assert len(token_hash) == 64
    assert token_hash != hashlib.sha256(created.token.encode()).hexdigest()
    assert created.token not in json.dumps(_all_payloads(ctx), sort_keys=True)
    assert "token" not in {
        key
        for payload in _all_payloads(ctx)
        for key in payload
        if key != "token_hash" and key != "token_hash_scheme"
    }

    # The binding is the exact byte digest surfaced by the immutable repository,
    # not a digest of an equivalent reserialized mapping.
    exact_body = ctx.repository.objects[("tenant-a", "", "trace-share-1")]
    assert persisted.payload["packet_content_sha256"] == hashlib.sha256(
        exact_body
    ).hexdigest()
    canonical = json.dumps(
        ctx.packet, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() != persisted.payload[
        "packet_content_sha256"
    ]

    metadata = ctx.service.get_share(
        tenant_id="tenant-a",
        account_id="acct-creator",
        actor_role="member",
        share_id=created.share.share_id,
    )
    assert metadata.share_id == created.share.share_id
    assert not hasattr(metadata, "token")


def test_fetch_is_read_only_and_records_sanitized_audit(service_fixture) -> None:
    ctx = service_fixture
    created = _create(ctx)
    before = bytes(ctx.repository.objects[("tenant-a", "", "trace-share-1")])
    packet = ctx.service.fetch_shared_packet(
        share_id=created.share.share_id,
        token=created.token,
        request_id="request-fetch-1",
    )
    after = ctx.repository.objects[("tenant-a", "", "trace-share-1")]
    assert packet == ctx.packet
    assert after == before

    events = ctx.service.list_events(
        tenant_id="tenant-a",
        account_id="acct-creator",
        actor_role="member",
        share_id=created.share.share_id,
    )
    assert [event["event_type"] for event in events] == ["created", "fetched"]
    for event in events:
        assert len(str(event["request_id_sha256"])) == 64
        assert created.token not in json.dumps(event, sort_keys=True)
        assert event["trace_id"] == "trace-share-1"


def test_revoke_is_idempotent_and_all_public_negative_states_collapse(
    service_fixture,
) -> None:
    ctx = service_fixture
    active = _create(ctx)
    wrong_error = None
    with pytest.raises(EvidenceShareUnavailable) as wrong:
        ctx.service.fetch_shared_packet(
            share_id=active.share.share_id,
            token="x" * 43,
            request_id="wrong",
        )
    wrong_error = str(wrong.value)

    first = ctx.service.revoke_share(
        tenant_id="tenant-a",
        account_id="acct-creator",
        actor_role="member",
        share_id=active.share.share_id,
        request_id="revoke-1",
    )
    second = ctx.service.revoke_share(
        tenant_id="tenant-a",
        account_id="acct-creator",
        actor_role="member",
        share_id=active.share.share_id,
        request_id="revoke-retry-different-id",
    )
    assert first.revoked_at == second.revoked_at
    with pytest.raises(EvidenceShareUnavailable) as revoked:
        ctx.service.fetch_shared_packet(
            share_id=active.share.share_id,
            token=active.token,
            request_id="after-revoke",
        )
    assert str(revoked.value) == wrong_error
    events = ctx.service.list_events(
        tenant_id="tenant-a",
        account_id="acct-creator",
        actor_role="member",
        share_id=active.share.share_id,
    )
    assert [event["event_type"] for event in events].count("revoked") == 1

    expired = _create(ctx, expires_at=ctx.clock.now + timedelta(minutes=1))
    ctx.clock.now += timedelta(minutes=2)
    with pytest.raises(EvidenceShareUnavailable) as expired_error:
        ctx.service.fetch_shared_packet(
            share_id=expired.share.share_id,
            token=expired.token,
            request_id="expired",
        )
    assert str(expired_error.value) == wrong_error

    with pytest.raises(EvidenceShareUnavailable) as absent:
        ctx.service.fetch_shared_packet(
            share_id="shr_" + "z" * 24,
            token="x" * 43,
            request_id="absent",
        )
    assert str(absent.value) == wrong_error


def test_concurrent_revoke_converges_on_one_receipt(service_fixture) -> None:
    ctx = service_fixture
    created = _create(ctx)

    def revoke(request_id: str):
        return ctx.service.revoke_share(
            tenant_id="tenant-a",
            account_id="acct-creator",
            actor_role="member",
            share_id=created.share.share_id,
            request_id=request_id,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(revoke, ("race-a", "race-b")))
    assert results[0].revoked_at == results[1].revoked_at
    events = ctx.service.list_events(
        tenant_id="tenant-a",
        account_id="acct-creator",
        actor_role="member",
        share_id=created.share.share_id,
    )
    assert [event["event_type"] for event in events].count("revoked") == 1


def test_cross_tenant_and_unrelated_member_cannot_disable_share(service_fixture) -> None:
    ctx = service_fixture
    created = _create(ctx)

    # A cross-tenant owner does not have a tenant-partitioned row. Critically,
    # the failed attempt must not remove the anonymous locator.
    with pytest.raises(EvidenceShareNotFound):
        ctx.service.revoke_share(
            tenant_id="tenant-b",
            account_id="acct-b-owner",
            actor_role="owner",
            share_id=created.share.share_id,
            request_id="cross-tenant",
        )
    assert ctx.service.fetch_shared_packet(
        share_id=created.share.share_id,
        token=created.token,
        request_id="still-live-1",
    )["trace_id"] == "trace-share-1"

    # Same tenant is necessary but not sufficient. Another member receives the
    # same not-found shape and cannot revoke the creator's capability.
    with pytest.raises(EvidenceShareNotFound):
        ctx.service.get_share(
            tenant_id="tenant-a",
            account_id="acct-peer",
            actor_role="member",
            share_id=created.share.share_id,
        )
    with pytest.raises(EvidenceShareNotFound):
        ctx.service.revoke_share(
            tenant_id="tenant-a",
            account_id="acct-peer",
            actor_role="member",
            share_id=created.share.share_id,
            request_id="peer-revoke",
        )
    assert ctx.service.fetch_shared_packet(
        share_id=created.share.share_id,
        token=created.token,
        request_id="still-live-2",
    )["trace_id"] == "trace-share-1"

    # Explicit tenant admin/owner capability may manage another account's share.
    managed = ctx.service.get_share(
        tenant_id="tenant-a",
        account_id="acct-admin",
        actor_role="admin",
        share_id=created.share.share_id,
    )
    assert managed.share_id == created.share.share_id


def test_sqlite_restart_preserves_share_and_pepper_rotation_fails_closed(
    service_fixture,
) -> None:
    ctx = service_fixture
    created = _create(ctx)
    ctx.store.close()
    restarted_store = SqliteStateStore(ctx.db)
    try:
        restarted = EvidenceShareService(
            store=restarted_store,
            repository=ctx.repository,
            token_pepper=_PEPPER,
            clock=ctx.clock,
        )
        assert restarted.fetch_shared_packet(
            share_id=created.share.share_id,
            token=created.token,
            request_id="after-restart",
        )["trace_id"] == "trace-share-1"

        rotated = EvidenceShareService(
            store=restarted_store,
            repository=ctx.repository,
            token_pepper="different-share-pepper-0123456789abcdef",
            clock=ctx.clock,
        )
        with pytest.raises(EvidenceShareUnavailable):
            rotated.fetch_shared_packet(
                share_id=created.share.share_id,
                token=created.token,
                request_id="rotated",
            )
    finally:
        restarted_store.close()


def test_tampered_hash_and_invalid_absolute_expiry_fail_closed(service_fixture) -> None:
    ctx = service_fixture
    with pytest.raises(ValueError, match="timezone-aware"):
        _create(ctx, expires_at=datetime(2026, 7, 15, 0, 0))
    with pytest.raises(ValueError, match="future"):
        _create(ctx, expires_at=ctx.clock.now)
    with pytest.raises(ValueError, match="30 days"):
        _create(ctx, expires_at=ctx.clock.now + timedelta(days=31))

    created = _create(ctx)
    record = ctx.store.get("tenant-a", EVIDENCE_SHARE_KIND, created.share.share_id)
    assert record is not None
    payload = dict(record.payload)
    payload["packet_content_sha256"] = "f" * 64
    ctx.store.put(record.with_payload(payload), expected_version=record.version)
    with pytest.raises(EvidenceShareUnavailable):
        ctx.service.fetch_shared_packet(
            share_id=created.share.share_id,
            token=created.token,
            request_id="tampered",
        )


@pytest.fixture
def share_route_client(tmp_path, monkeypatch):
    from api.main import app

    store = SqliteStateStore(tmp_path / "share-routes.db")
    account_store = AccountStore(store, credential_pepper="a" * 40)
    session_store = SessionStore(store)
    repository = _ExactPacketRepository()
    packet = {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": "trace-route-share",
        "input": {"text": "route input"},
        "output": {"text": "route output"},
        "claim_levels": [],
    }
    repository.put_packet(
        tenant_id="tenant-route", trace_id="trace-route-share", packet=packet
    )
    service = EvidenceShareService(
        store=store, repository=repository, token_pepper=_PEPPER
    )

    with TestClient(app) as client:
        monkeypatch.setattr(settings, "accounts_enabled", True)
        monkeypatch.setattr(settings, "evidence_shares_enabled", True)
        monkeypatch.setattr(settings, "evidence_packet_object_store_enabled", True)
        previous = {
            "account_store": getattr(app.state, "account_store", None),
            "session_store": getattr(app.state, "session_store", None),
            "shared_state_store": getattr(app.state, "shared_state_store", None),
            "state_ledger": getattr(app.state, "state_ledger", None),
            "evidence_share_service": getattr(app.state, "evidence_share_service", None),
        }
        app.state.account_store = account_store
        app.state.session_store = session_store
        app.state.shared_state_store = store
        app.state.state_ledger = SimpleNamespace(store=store)
        app.state.evidence_share_service = service
        try:
            yield SimpleNamespace(
                client=client,
                store=store,
                account_store=account_store,
                packet=packet,
            )
        finally:
            for name, value in previous.items():
                setattr(app.state, name, value)
    store.close()


def _login(ctx, *, identity: str, role: str, tenant_id: str) -> tuple[dict, object]:
    code = f"invite-{uuid.uuid4().hex}"
    invite = ctx.account_store.create_invite(
        code=code, role=role, tenant_id=tenant_id
    )
    credential = f"casak_{uuid.uuid4().hex}{uuid.uuid4().hex}"
    account = ctx.account_store.redeem_invite(
        code=invite.code,
        email_or_username=identity,
        api_credential=credential,
    )
    response = ctx.client.post(
        "/auth/token",
        json={"username": identity, "api_credential": credential},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}, account


def test_routes_enforce_creator_admin_boundary_and_nonleaky_anonymous_fetch(
    share_route_client, caplog
) -> None:
    ctx = share_route_client
    creator_headers, creator = _login(
        ctx, identity="creator@example.com", role="member", tenant_id="tenant-route"
    )
    peer_headers, _peer = _login(
        ctx, identity="peer@example.com", role="member", tenant_id="tenant-route"
    )
    admin_headers, _admin = _login(
        ctx, identity="admin@example.com", role="admin", tenant_id="tenant-route"
    )
    record_evidence_ownership(
        ctx.store,
        tenant_id="tenant-route",
        account_id=creator.account_id,
        trace_id="trace-route-share",
    )

    created = ctx.client.post(
        "/evidence/trace-route-share/shares",
        headers=creator_headers,
        json={
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat()
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    share_id = body["share_id"]
    token = body["share_token"]
    assert token not in body["anonymous_fetch_path"]
    assert created.headers["cache-control"].startswith("no-store")

    creator_read = ctx.client.get(
        f"/evidence/shares/{share_id}", headers=creator_headers
    )
    assert creator_read.status_code == 200
    assert "share_token" not in creator_read.json()
    assert "token_hash" not in creator_read.json()
    peer_read = ctx.client.get(f"/evidence/shares/{share_id}", headers=peer_headers)
    assert peer_read.status_code == 404
    admin_read = ctx.client.get(f"/evidence/shares/{share_id}", headers=admin_headers)
    assert admin_read.status_code == 200

    # The security-sensitive route ignores inbound request ids. This prevents a
    # copied share token from entering structured audit logs even on early exits.
    caplog.clear()
    caplog.set_level("INFO", logger="noetic.audit")
    fetched = ctx.client.get(
        body["anonymous_fetch_path"],
        headers={
            "X-Evidence-Share-Token": token,
            "X-Request-ID": token,
        },
    )
    assert fetched.status_code == 200, fetched.text
    assert fetched.json() == ctx.packet
    assert fetched.headers["x-request-id"] != token
    assert fetched.headers["cache-control"].startswith("no-store")
    assert fetched.headers["referrer-policy"] == "no-referrer"
    assert token not in caplog.text

    missing = ctx.client.get(body["anonymous_fetch_path"])
    wrong = ctx.client.get(
        body["anonymous_fetch_path"],
        headers={"X-Evidence-Share-Token": "x" * 43},
    )
    assert missing.status_code == wrong.status_code == 404
    assert missing.json() == wrong.json() == {
        "detail": "Shared Evidence Packet is unavailable."
    }

    # A peer cannot disable it; creator revoke is idempotent and afterwards the
    # same anonymous response is used as wrong/absent credentials.
    peer_revoke = ctx.client.delete(
        f"/evidence/shares/{share_id}", headers=peer_headers
    )
    assert peer_revoke.status_code == 404
    assert ctx.client.get(
        body["anonymous_fetch_path"],
        headers={"X-Evidence-Share-Token": token},
    ).status_code == 200
    revoked = ctx.client.delete(
        f"/evidence/shares/{share_id}", headers=creator_headers
    )
    retried = ctx.client.delete(
        f"/evidence/shares/{share_id}", headers=creator_headers
    )
    assert revoked.status_code == retried.status_code == 200
    assert revoked.json()["revoked_at"] == retried.json()["revoked_at"]
    after = ctx.client.get(
        body["anonymous_fetch_path"],
        headers={"X-Evidence-Share-Token": token},
    )
    assert after.status_code == 404
    assert after.json() == wrong.json()


def _share_settings(**overrides) -> Settings:
    values = {
        "accounts_enabled": True,
        "debug": True,
        "jwt_secret": "j" * 32,
        "jwt_algorithm": "HS256",
        "account_credential_pepper": "a" * 32,
        "object_lock_receipt_attestation_key": "r" * 32,
        "accounts_allow_single_host_sqlite": True,
        "state_ledger_path": str(Path.cwd().resolve() / "share-config-test.db"),
        "database_url": None,
        "evidence_packet_object_store_enabled": True,
        "evidence_shares_enabled": True,
        "evidence_share_token_pepper": "s" * 32,
    }
    values.update(overrides)
    return Settings.model_construct(**values)


def test_share_configuration_is_dark_and_fails_loud_when_half_enabled() -> None:
    assert Settings(_env_file=None).evidence_shares_enabled is False
    with pytest.raises(RuntimeError, match="ACCOUNTS_ENABLED"):
        _share_settings(accounts_enabled=False).validate_account_storage()
    with pytest.raises(RuntimeError, match="OBJECT_STORE_ENABLED"):
        _share_settings(
            evidence_packet_object_store_enabled=False
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        _share_settings(evidence_share_token_pepper="short").validate_account_storage()
    _share_settings().validate_account_storage()


def test_packet_repository_returns_exact_verified_byte_hash(tmp_path) -> None:
    """The real repository seam returns its durable exact-version digest."""

    from api.services.cas_harness_evidence_object_store import EvidencePacketRepository
    from api.services.production.worm_writes import LockReceipt, RetentionPolicy
    from tests.object_lock_test_support import issue_test_object_lock_receipt

    class Backend:
        body = b""

        def assert_ready(self, *, expected):
            return None

        def object_url(self, key, *, version_id=None):
            return f"s3://test/{key}?versionId={version_id or ''}"

        def put_immutable(self, *, key, body, content_hash, policy):
            self.body = bytes(body)
            now = datetime.now(timezone.utc).replace(microsecond=0)
            verification = issue_test_object_lock_receipt(
                expected={
                    "bucket": "test",
                    "key": key,
                    "version_id": "v1",
                    "content_sha256": content_hash,
                    "mode": policy.mode,
                    "retention_days": policy.retention_days,
                    "requested_at": now,
                    "retain_until": now + timedelta(days=policy.retention_days),
                },
                observed={
                    "bucket": "test",
                    "key": key,
                    "get_version_id": "v1",
                    "head_version_id": "v1",
                    "content_sha256": content_hash,
                    "mode": policy.mode,
                    "retain_until": now + timedelta(days=policy.retention_days),
                    "reread_verified": True,
                },
                verified_at=now,
            )
            return LockReceipt(
                object_url=f"s3://test/{key}?versionId=v1",
                version_id="v1",
                retain_until=now + timedelta(days=policy.retention_days),
                mode=policy.mode,
                content_hash=content_hash,
                reread_verified=True,
                verification_receipt=verification,
            )

        def get_immutable(self, *, key, version_id):
            assert version_id == "v1"
            return self.body

        def verify_receipt(self, **kwargs):
            raise AssertionError("not used")

    store = SqliteStateStore(tmp_path / "exact-binding.db")
    try:
        backend = Backend()
        repository = EvidencePacketRepository(
            store=store,
            backend=backend,
            policy=RetentionPolicy(mode="GOVERNANCE", retention_days=30),
        )
        packet = {"trace_id": "trace-exact", "z": 1, "a": "value"}
        repository.put_packet(
            tenant_id="tenant-exact",
            namespace="",
            trace_id="trace-exact",
            packet=packet,
        )
        loaded, exact_hash = repository.load_packet_with_content_sha256(
            tenant_id="tenant-exact", namespace="", trace_id="trace-exact"
        )
        assert loaded == packet
        assert exact_hash == hashlib.sha256(backend.body).hexdigest()
    finally:
        store.close()
