"""Fail-closed persistence, routing, and auth tests for acceptance authority."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.acceptance_authority_contract import (
    ACCEPTANCE_AUTHORITY_PATH_BY_GATE,
    ACCEPTANCE_AUTHORITY_PUBLIC_PATHS,
    acceptance_authority_url,
)
from api.middleware.auth import (
    JWTAuthMiddleware,
    is_public_acceptance_authority_request,
    is_public_path,
)
from api.middleware.rate_limit import RateLimitMiddleware
from api.routes.customer_production_acceptance_authority import router
from api.services import customer_production_acceptance_authority as authority
from api.services.customer_production_acceptance_authority import (
    AcceptanceAuthorityConflict,
    AcceptanceAuthorityHumanAttestationUnavailable,
    AcceptanceAuthorityInvalid,
    AcceptanceAuthorityNotFound,
    AcceptanceAuthorityUnavailable,
    CustomerProductionAcceptanceAuthorityStore,
)
from api.services.acceptance_publication_authorizations import (
    AcceptancePublicationAuthorizationStore,
)
from api.services.human_attestations import HumanAttestationStore
from api.services.production.state_substrate import LedgerRecord, StateStore
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.production.worm_writes import RetentionPolicy
from api.services.cas_harness_retention_disclosure import (
    _issue_live_s3_object_lock_receipt,
)
from tests.acceptance_attestation_test_support import (
    human_attestation_store,
    materialize_human_attestations,
)
from api.services.human_attestations import PUBLIC_HUMAN_ASSURANCE_BOUNDARY


_AUTHORIZATION_SHA256 = hashlib.sha256(b"test-authorization").hexdigest()
_AUTHORIZATION_URI = (
    f"{authority.PRODUCTION_API_ORIGIN}/internal/acceptance-authorizations/"
    f"{_AUTHORIZATION_SHA256}"
)


def _operation_authorization(action: str) -> dict[str, str]:
    return {
        "authorization_artifact_uri": _AUTHORIZATION_URI,
        "authorization_artifact_sha256": _AUTHORIZATION_SHA256,
        "operation_reason": (
            "authorized_publication"
            if action == "publish"
            else "operator_safety_action"
        ),
    }


@pytest.fixture(autouse=True)
def _stable_test_receipt_attestation_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.config import settings

    value = "acceptance-authority-test-attestation-key-v1"
    monkeypatch.setenv(
        "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY",
        value,
    )
    monkeypatch.setattr(settings, "object_lock_receipt_attestation_key", value)


@pytest.fixture(autouse=True)
def _isolate_preexisting_authority_tests_from_the_new_record_plane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """These tests exercise the older revision/head/WORM invariants.

    The authorization plane has its own hostile tests.  Keep this existing
    suite focused by replacing only its local record lookup, while retaining
    the exact URI/hash syntax validation on every operation.
    """

    monkeypatch.setattr(
        AcceptancePublicationAuthorizationStore,
        "assert_matches",
        lambda self, **kwargs: None,
    )


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _legal_evidence(now: datetime) -> dict[str, object]:
    stamp = _utc(now)
    documents = []
    for kind in ("legal", "privacy", "terms"):
        documents.append(
            {
                "kind": kind,
                "url": f"https://cascompass.ai/{kind}",
                "http_status": 200,
                "content_sha256": _sha(f"document-{kind}"),
                "published_at_utc": stamp,
                "verified_at_utc": stamp,
            }
        )
    approvals = []
    for role in ("legal_counsel", "privacy_owner", "product_owner"):
        approvals.append(
            {
                "role": role,
                "approval_artifact_uri": (
                    f"{authority.PRODUCTION_API_ORIGIN}/"
                    f"internal/approvals/{role}"
                ),
                "approval_sha256": _sha(f"approval-{role}"),
                "approved_at_utc": stamp,
            }
        )
    return {
        "schema_version": authority.EVIDENCE_SCHEMA_VERSION,
        "gate": "legal_publication_approval",
        "environment": "public-production",
        "repository": "LittleHenderson/noetic-compass",
        "master_head_sha": "a" * 40,
        "deploy_id": "dep-authoritytest001",
        "event_at_utc": stamp,
        "observed_at_utc": stamp,
        "artifact_uri": acceptance_authority_url("legal_publication_approval"),
        "artifact_sha256": _sha("legal-source-artifact"),
        "public_base_url": "https://cascompass.ai",
        "documents": documents,
        "approvals": approvals,
        "claim_status_vocabulary": [
            "ACCEPT",
            "FLAG_FOR_HUMAN_REVIEW",
            "LICENSED",
            "NOT LICENSED",
            "OPEN",
            "present",
            "unavailable",
        ],
        "human_assurance_boundary": dict(PUBLIC_HUMAN_ASSURANCE_BOUNDARY),
    }


def _bound_legal_evidence(
    state: StateStore, now: datetime
) -> tuple[dict[str, object], HumanAttestationStore]:
    evidence = _legal_evidence(now)
    attestations = materialize_human_attestations(state, evidence)
    return evidence, attestations


def _app(store: CustomerProductionAcceptanceAuthorityStore | None) -> FastAPI:
    app = FastAPI()
    app.state.acceptance_authority_store = store
    app.include_router(router)
    app.add_middleware(RateLimitMiddleware, rpm=500)
    app.add_middleware(JWTAuthMiddleware)
    return app


class _FakeReceipt:
    def __init__(
        self,
        *,
        digest: str,
        key: str,
        policy: RetentionPolicy,
        requested_at: datetime,
        retain_until: datetime,
    ) -> None:
        self.object_url = f"s3://test/{key}?versionId=version-1"
        self.version_id = "version-1"
        self.retain_until = retain_until
        self.content_hash = digest
        self.mode = policy.mode
        self._verification = _issue_live_s3_object_lock_receipt(
            expected={
                "bucket": "test",
                "key": key,
                "version_id": self.version_id,
                "content_sha256": digest,
                "mode": policy.mode,
                "retention_days": policy.retention_days,
                "requested_at": requested_at,
                "retain_until": retain_until,
            },
            observed={
                "bucket": "test",
                "key": key,
                "get_version_id": self.version_id,
                "head_version_id": self.version_id,
                "content_sha256": digest,
                "mode": policy.mode,
                "retain_until": retain_until,
                "reread_verified": True,
            },
            verified_at=requested_at,
        )

    def is_verifiable(self) -> bool:
        return True

    def validated_verification(self):  # type: ignore[no-untyped-def]
        return self._verification


class _FakeImmutableBackend:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.ready_checks = 0

    def assert_ready(self, *, expected: RetentionPolicy) -> None:
        assert expected.retention_days >= 1
        self.ready_checks += 1

    def object_url(self, key: str, *, version_id: str | None = None) -> str:
        suffix = f"?versionId={version_id}" if version_id else ""
        return f"s3://test/{key}{suffix}"

    def put_immutable(
        self,
        *,
        key: str,
        body: bytes,
        content_hash: str,
        policy: RetentionPolicy,
    ) -> _FakeReceipt:
        assert hashlib.sha256(body).hexdigest() == content_hash
        self.objects[(key, "version-1")] = body
        requested_at = datetime.now(UTC).replace(microsecond=0)
        return _FakeReceipt(
            digest=content_hash,
            key=key,
            policy=policy,
            requested_at=requested_at,
            retain_until=policy.retain_until(now=requested_at),
        )

    def get_immutable(self, *, key: str, version_id: str) -> bytes:
        return self.objects[(key, version_id)]


def test_public_contract_is_exact_get_only_and_excludes_root_ci() -> None:
    assert "root_ci_protected_deploy" not in ACCEPTANCE_AUTHORITY_PATH_BY_GATE
    assert len(ACCEPTANCE_AUTHORITY_PUBLIC_PATHS) == 9
    for path in ACCEPTANCE_AUTHORITY_PUBLIC_PATHS:
        assert is_public_path(path) is False
        assert is_public_acceptance_authority_request(path, "GET") is True
        assert is_public_acceptance_authority_request(path, "get") is True
        assert is_public_acceptance_authority_request(path, "HEAD") is False
        assert is_public_acceptance_authority_request(path, "POST") is False
        assert is_public_acceptance_authority_request(path, "GET", "x=1") is False
    assert (
        is_public_acceptance_authority_request(
            "/internal/acceptance/future-management", "GET"
        )
        is False
    )


def test_sqlite_revision_survives_restart_and_bytes_are_canonical(tmp_path) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    path = tmp_path / "authority.db"
    first_backend = SqliteStateStore(path)
    evidence, attestations = _bound_legal_evidence(first_backend, now)
    first = CustomerProductionAcceptanceAuthorityStore(
        first_backend, human_attestation_store=attestations
    )
    published = first.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    assert published.head_version == 1
    assert published.storage_mode == "state_store"
    first_backend.close()

    second_backend = SqliteStateStore(path)
    second = CustomerProductionAcceptanceAuthorityStore(
        second_backend,
        human_attestation_store=human_attestation_store(second_backend),
    )
    loaded = second.load("legal_publication_approval", now=now)
    assert loaded.sha256 == published.sha256
    assert hashlib.sha256(loaded.body).hexdigest() == published.sha256
    assert loaded.body == json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    assert second.current_head_version("legal_publication_approval") == 1
    second_backend.close()


@pytest.mark.parametrize(
    "gate",
    [
        "legal_publication_approval",
        "claim_honesty",
        "incident_tabletop",
        "release_decision",
    ],
)
def test_every_human_gate_requires_an_attestation_store(gate: str) -> None:
    store = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())

    with pytest.raises(
        AcceptanceAuthorityHumanAttestationUnavailable,
        match="human attestation storage is unavailable",
    ):
        store.assert_human_attestations(gate, {})


def test_missing_attestation_store_blocks_publish_before_any_write() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    immutable = _FakeImmutableBackend()
    store = CustomerProductionAcceptanceAuthorityStore(
        state,
        immutable_backend=immutable,
        retention_policy=RetentionPolicy(mode="GOVERNANCE", retention_days=31),
    )

    with pytest.raises(AcceptanceAuthorityHumanAttestationUnavailable):
        store.publish(
            "legal_publication_approval",
            _legal_evidence(now),
            expected_head_version=0,
            expected_previous_sha256=None,
            **_operation_authorization("publish"),
            now=now,
        )

    assert immutable.ready_checks == 0
    assert immutable.objects == {}
    assert state.list(authority.AUTHORITY_TENANT_ID, authority.REVISION_KIND) == ()
    assert state.list(authority.AUTHORITY_TENANT_ID, authority.OPERATION_KIND) == ()
    assert state.list(authority.AUTHORITY_TENANT_ID, authority.HEAD_KIND) == ()


def test_missing_attestation_store_cannot_serve_but_can_deactivate() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    configured = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    published = configured.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    missing = CustomerProductionAcceptanceAuthorityStore(state)

    with pytest.raises(AcceptanceAuthorityHumanAttestationUnavailable):
        missing.load("legal_publication_approval", now=now)
    with TestClient(_app(missing)) as client:
        assert client.get(
            ACCEPTANCE_AUTHORITY_PATH_BY_GATE["legal_publication_approval"]
        ).status_code == 503

    head = missing.current_head("legal_publication_approval")
    assert head is not None and head.active is True
    deactivated = missing.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )
    assert deactivated.already_inactive is False
    with pytest.raises(AcceptanceAuthorityNotFound, match="inactive"):
        missing.load("legal_publication_approval", now=now + timedelta(seconds=1))


def test_publish_requires_current_head_version() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    with pytest.raises(AcceptanceAuthorityConflict):
        store.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=0,
            expected_previous_sha256=None,
            **_operation_authorization("publish"),
            now=now,
        )


def test_publish_requires_the_exact_previous_evidence_hash() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    first = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    with pytest.raises(AcceptanceAuthorityConflict):
        store.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=first.head_version,
            expected_previous_sha256="b" * 64,
            **_operation_authorization("publish"),
            now=now + timedelta(seconds=1),
        )


def test_deactivate_is_immediate_monotonic_and_same_bytes_can_be_reactivated() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    first = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    deactivated = store.deactivate(
        "legal_publication_approval",
        expected_head_version=first.head_version,
        expected_evidence_sha256=first.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )
    assert deactivated.head_version == 2
    assert deactivated.already_inactive is False
    head = store.current_head("legal_publication_approval")
    assert head is not None and head.active is False and head.head_version == 2
    with pytest.raises(AcceptanceAuthorityNotFound, match="inactive"):
        store.load("legal_publication_approval", now=now + timedelta(seconds=1))

    reactivated = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=deactivated.head_version,
        expected_previous_sha256=first.sha256,
        **_operation_authorization("publish"),
        now=now + timedelta(seconds=2),
    )
    assert reactivated.sha256 == first.sha256
    assert reactivated.head_version == 3
    assert len(
        state.list(authority.AUTHORITY_TENANT_ID, authority.REVISION_KIND)
    ) == 1
    assert store.load(
        "legal_publication_approval", now=now + timedelta(seconds=2)
    ).sha256 == first.sha256

    already_inactive_head = store.deactivate(
        "legal_publication_approval",
        expected_head_version=reactivated.head_version,
        expected_evidence_sha256=first.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=3),
    )
    repeated = store.deactivate(
        "legal_publication_approval",
        expected_head_version=already_inactive_head.head_version,
        expected_evidence_sha256=first.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=4),
    )
    assert repeated.already_inactive is True
    assert repeated.head_version == already_inactive_head.head_version


def test_head_binds_an_append_only_authorized_operation_chain() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    published = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    deactivated = store.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )
    reactivated = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=deactivated.head_version,
        expected_previous_sha256=published.sha256,
        **_operation_authorization("publish"),
        now=now + timedelta(seconds=2),
    )

    operations = state.list(
        authority.AUTHORITY_TENANT_ID, authority.OPERATION_KIND
    )
    assert len(operations) == 3
    head = store.current_head("legal_publication_approval")
    assert head is not None
    assert head.operation_record_id == reactivated.operation_record_id
    assert head.operation_sha256 == reactivated.operation_sha256
    latest = state.get(
        authority.AUTHORITY_TENANT_ID,
        authority.OPERATION_KIND,
        head.operation_record_id,
    )
    assert latest is not None
    assert latest.payload["previous"]["operation_record_id"] == (  # type: ignore[index]
        deactivated.operation_record_id
    )
    assert latest.payload["authorization"] == {  # type: ignore[index]
        "artifact_uri": _AUTHORIZATION_URI,
        "artifact_sha256": _AUTHORIZATION_SHA256,
        "reason": "authorized_publication",
    }


def test_missing_bound_operation_or_predecessor_fails_closed() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    published = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    deactivated = store.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )
    reactivated = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=deactivated.head_version,
        expected_previous_sha256=published.sha256,
        **_operation_authorization("publish"),
        now=now + timedelta(seconds=2),
    )
    state.delete(
        authority.AUTHORITY_TENANT_ID,
        authority.OPERATION_KIND,
        published.operation_record_id,
        expected_version=1,
    )

    with pytest.raises(AcceptanceAuthorityUnavailable, match="missing"):
        store.current_head("legal_publication_approval")
    assert reactivated.head_version == 3


def test_invalid_authorization_pointer_writes_no_authority_state() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    with pytest.raises(AcceptanceAuthorityInvalid, match="reference"):
        store.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=0,
            expected_previous_sha256=None,
            authorization_artifact_uri="https://example.com/fake-approval",
            authorization_artifact_sha256=_AUTHORIZATION_SHA256,
            operation_reason="authorized_publication",
            now=now,
        )

    assert state.list(authority.AUTHORITY_TENANT_ID, authority.REVISION_KIND) == ()
    assert state.list(authority.AUTHORITY_TENANT_ID, authority.OPERATION_KIND) == ()
    assert state.list(authority.AUTHORITY_TENANT_ID, authority.HEAD_KIND) == ()


def test_out_of_range_url_port_is_a_controlled_validation_error() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    evidence = _legal_evidence(now)
    approvals = evidence["approvals"]
    assert isinstance(approvals, list)
    approvals[0]["approval_artifact_uri"] = (  # type: ignore[index]
        f"{authority.PRODUCTION_API_ORIGIN}:99999/internal/approval"
    )

    with pytest.raises(AcceptanceAuthorityInvalid, match="clean HTTPS URL"):
        authority.canonicalize_acceptance_evidence(
            "legal_publication_approval", evidence, now=now
        )


def test_unbound_prewritten_operation_is_harmless() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    store = CustomerProductionAcceptanceAuthorityStore(state)
    operation_id, _ = store._append_operation(
        gate="legal_publication_approval",
        action="publish",
        current_head=None,
        next_sha256=_sha("orphan-target"),
        next_active=True,
        authorization_artifact_uri=_AUTHORIZATION_URI,
        authorization_artifact_sha256=_AUTHORIZATION_SHA256,
        operation_reason="authorized_publication",
        now=now,
    )

    assert state.get(
        authority.AUTHORITY_TENANT_ID, authority.OPERATION_KIND, operation_id
    ) is not None
    assert store.current_head("legal_publication_approval") is None


@pytest.mark.parametrize("target", ["operation", "revision"])
def test_content_addressed_records_reject_even_same_payload_overwrite(
    target: str,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    published = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    if target == "operation":
        kind = authority.OPERATION_KIND
        record_id = published.operation_record_id
    else:
        kind = authority.REVISION_KIND
        record_id = authority._revision_record_id(
            "legal_publication_approval", published.sha256
        )
    record = state.get(authority.AUTHORITY_TENANT_ID, kind, record_id)
    assert record is not None
    state.put(record.with_payload(record.payload), expected_version=1)

    with pytest.raises(AcceptanceAuthorityUnavailable, match="traceability"):
        if target == "operation":
            store.current_head("legal_publication_approval")
        else:
            store.load("legal_publication_approval", now=now)


def test_deactivated_route_fails_closed_without_deleting_revision() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    published = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    store.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )
    path = ACCEPTANCE_AUTHORITY_PATH_BY_GATE["legal_publication_approval"]
    with TestClient(_app(store)) as client:
        response = client.get(path)
        assert response.status_code == 404
        assert response.headers["cache-control"].startswith("no-store")
    assert len(
        state.list(authority.AUTHORITY_TENANT_ID, authority.REVISION_KIND)
    ) == 1


def test_optional_worm_backend_has_no_inline_fallback_and_rechecks_exact_bytes() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    immutable = _FakeImmutableBackend()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state,
        human_attestation_store=attestations,
        immutable_backend=immutable,
        retention_policy=RetentionPolicy(mode="COMPLIANCE", retention_days=31),
    )
    published = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    assert published.storage_mode == "worm"
    assert immutable.ready_checks == 1
    revision_id = authority._revision_record_id(
        "legal_publication_approval", published.sha256
    )
    revision = state.get(
        authority.AUTHORITY_TENANT_ID, authority.REVISION_KIND, revision_id
    )
    assert revision is not None
    assert revision.payload["evidence_json"] is None
    assert revision.payload["storage"]["mode"] == "worm"  # type: ignore[index]
    assert store.load("legal_publication_approval", now=now).sha256 == published.sha256
    assert immutable.ready_checks == 2

    deactivated = store.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )
    reactivated = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=deactivated.head_version,
        expected_previous_sha256=published.sha256,
        **_operation_authorization("publish"),
        now=now + timedelta(seconds=2),
    )
    assert reactivated.sha256 == published.sha256
    assert immutable.ready_checks == 3

    key = f"customer-production-authority/legal_publication_approval/{published.sha256}.json"
    immutable.objects[(key, "version-1")] = b"{}"
    with pytest.raises(AcceptanceAuthorityUnavailable, match="byte length"):
        store.load("legal_publication_approval", now=now)


def test_cross_wired_worm_receipt_cannot_create_a_head() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()

    class CrossWiredBackend(_FakeImmutableBackend):
        def put_immutable(self, **kwargs):  # type: ignore[no-untyped-def]
            key = kwargs["key"]
            body = kwargs["body"]
            digest = kwargs["content_hash"]
            policy = kwargs["policy"]
            self.objects[(key, "version-1")] = body
            requested_at = datetime.now(UTC).replace(microsecond=0)
            receipt = _FakeReceipt(
                digest=digest,
                key=f"cross-wired/{key}",
                policy=policy,
                requested_at=requested_at,
                retain_until=policy.retain_until(now=requested_at),
            )
            receipt.object_url = self.object_url(key, version_id="version-1")
            return receipt

    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state,
        human_attestation_store=attestations,
        immutable_backend=CrossWiredBackend(),
        retention_policy=RetentionPolicy(mode="COMPLIANCE", retention_days=31),
    )
    with pytest.raises(AcceptanceAuthorityUnavailable, match="current policy"):
        store.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=0,
            expected_previous_sha256=None,
            **_operation_authorization("publish"),
            now=now,
        )

    assert state.list(authority.AUTHORITY_TENANT_ID, authority.REVISION_KIND) == ()
    assert state.list(authority.AUTHORITY_TENANT_ID, authority.OPERATION_KIND) == ()
    assert state.list(authority.AUTHORITY_TENANT_ID, authority.HEAD_KIND) == ()


def test_inline_revision_cannot_be_reactivated_under_worm_policy() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    inline = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    published = inline.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    deactivated = inline.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )

    immutable = _FakeImmutableBackend()
    worm = CustomerProductionAcceptanceAuthorityStore(
        state,
        human_attestation_store=attestations,
        immutable_backend=immutable,
        retention_policy=RetentionPolicy(mode="COMPLIANCE", retention_days=31),
    )
    with pytest.raises(AcceptanceAuthorityUnavailable, match="immutable policy"):
        worm.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=deactivated.head_version,
            expected_previous_sha256=published.sha256,
            **_operation_authorization("publish"),
            now=now + timedelta(seconds=2),
        )

    assert immutable.ready_checks == 0
    assert immutable.objects == {}
    head = inline.current_head("legal_publication_approval")
    assert head is not None and head.active is False
    assert head.head_version == deactivated.head_version


def test_worm_revision_cannot_be_reactivated_without_worm_policy() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    immutable = _FakeImmutableBackend()
    evidence, attestations = _bound_legal_evidence(state, now)
    worm = CustomerProductionAcceptanceAuthorityStore(
        state,
        human_attestation_store=attestations,
        immutable_backend=immutable,
        retention_policy=RetentionPolicy(mode="COMPLIANCE", retention_days=31),
    )
    published = worm.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    deactivated = worm.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )

    inline = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    with pytest.raises(AcceptanceAuthorityUnavailable, match="immutable policy"):
        inline.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=deactivated.head_version,
            expected_previous_sha256=published.sha256,
            **_operation_authorization("publish"),
            now=now + timedelta(seconds=2),
        )

    head = worm.current_head("legal_publication_approval")
    assert head is not None and head.active is False
    assert head.head_version == deactivated.head_version


def test_worm_revision_reuse_rejects_current_policy_drift() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    immutable = _FakeImmutableBackend()
    evidence, attestations = _bound_legal_evidence(state, now)
    original = CustomerProductionAcceptanceAuthorityStore(
        state,
        human_attestation_store=attestations,
        immutable_backend=immutable,
        retention_policy=RetentionPolicy(mode="COMPLIANCE", retention_days=31),
    )
    published = original.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    deactivated = original.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )
    strengthened = CustomerProductionAcceptanceAuthorityStore(
        state,
        human_attestation_store=attestations,
        immutable_backend=immutable,
        retention_policy=RetentionPolicy(mode="COMPLIANCE", retention_days=32),
    )

    with pytest.raises(AcceptanceAuthorityUnavailable, match="current policy"):
        strengthened.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=deactivated.head_version,
            expected_previous_sha256=published.sha256,
            **_operation_authorization("publish"),
            now=now + timedelta(seconds=2),
        )


def test_expired_worm_receipt_cannot_be_reactivated() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    immutable = _FakeImmutableBackend()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state,
        human_attestation_store=attestations,
        immutable_backend=immutable,
        retention_policy=RetentionPolicy(mode="COMPLIANCE", retention_days=1),
    )
    published = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    deactivated = store.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        **_operation_authorization("deactivate"),
        now=now + timedelta(seconds=1),
    )

    with pytest.raises(AcceptanceAuthorityUnavailable, match="revalidation"):
        store.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=deactivated.head_version,
            expected_previous_sha256=published.sha256,
            **_operation_authorization("publish"),
            now=now + timedelta(days=2),
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update({"email": "person@example.com"}),
        lambda value: value["approvals"][0].update(  # type: ignore[index,union-attr]
            {"role": "owner@example.com"}
        ),
        lambda value: value["documents"][0].update(  # type: ignore[index,union-attr]
            {"http_status": 500}
        ),
        lambda value: value.update({"artifact_uri": "https://cascompass.ai/legal"}),
        lambda value: value.update({"environment": "private-canary"}),
    ],
)
def test_publish_rejects_schema_semantic_pii_endpoint_and_environment_failures(
    mutate,
) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC).replace(microsecond=0)
    evidence = _legal_evidence(now)
    mutate(evidence)
    store = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
    with pytest.raises(AcceptanceAuthorityInvalid):
        store.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=0,
            expected_previous_sha256=None,
            **_operation_authorization("publish"),
            now=now,
        )


def test_load_rejects_stale_evidence() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    with pytest.raises(AcceptanceAuthorityInvalid, match="stale"):
        store.load("legal_publication_approval", now=now + timedelta(days=31))


def test_route_returns_exact_document_without_auth_and_no_store_cache() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(state, now)
    store = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    published = store.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    path = ACCEPTANCE_AUTHORITY_PATH_BY_GATE["legal_publication_approval"]
    with TestClient(_app(store)) as client:
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == evidence
        assert response.headers["cache-control"].startswith("no-store")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["etag"] == f'"sha256:{published.sha256}"'

        # The same path is public for only an exact, query-free GET.
        assert client.post(path).status_code == 401
        assert client.head(path).status_code == 401
        assert client.get(f"{path}?probe=1").status_code == 401
        assert client.get(f"{path}/publish").status_code == 401


def test_route_returns_404_for_absent_and_503_for_unavailable_or_corrupt() -> None:
    empty = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
    path = ACCEPTANCE_AUTHORITY_PATH_BY_GATE["legal_publication_approval"]
    with TestClient(_app(empty)) as client:
        absent = client.get(path)
        assert absent.status_code == 404
        assert absent.json() == {"detail": "Acceptance evidence is unavailable."}
        assert "gate" not in absent.text

    with TestClient(_app(None)) as client:
        unavailable = client.get(path)
        assert unavailable.status_code == 503
        assert "token" not in unavailable.text.lower()

    now = datetime.now(UTC).replace(microsecond=0)
    backend = InMemoryStateStore()
    evidence, attestations = _bound_legal_evidence(backend, now)
    corrupt = CustomerProductionAcceptanceAuthorityStore(
        backend, human_attestation_store=attestations
    )
    corrupt.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        **_operation_authorization("publish"),
        now=now,
    )
    head_id = authority._head_record_id("legal_publication_approval")
    head = backend.get(authority.AUTHORITY_TENANT_ID, authority.HEAD_KIND, head_id)
    assert head is not None
    broken = dict(head.payload)
    broken["evidence_sha256"] = "b" * 64
    backend.put(
        LedgerRecord(
            record_id=head.record_id,
            tenant_id=head.tenant_id,
            kind=head.kind,
            version=head.version,
            created_at=head.created_at,
            updated_at=head.updated_at,
            payload=broken,
            parent_ids=head.parent_ids,
            source=head.source,
            trace_id=head.trace_id,
        ),
        expected_version=head.version,
    )
    with TestClient(_app(corrupt)) as client:
        response = client.get(path)
        assert response.status_code == 503
        assert "sha256" not in response.text.lower()


def test_router_registers_only_exact_get_routes() -> None:
    authority_routes = {
        route.path: route.methods
        for route in router.routes
        if getattr(route, "path", None) in ACCEPTANCE_AUTHORITY_PUBLIC_PATHS
    }
    assert set(authority_routes) == ACCEPTANCE_AUTHORITY_PUBLIC_PATHS
    assert all(methods == {"GET"} for methods in authority_routes.values())
