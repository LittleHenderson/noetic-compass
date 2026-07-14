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
    AcceptanceAuthorityInvalid,
    AcceptanceAuthorityUnavailable,
    CustomerProductionAcceptanceAuthorityStore,
)
from api.services.production.state_substrate import LedgerRecord
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.production.worm_writes import RetentionPolicy


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
                    "https://noetic-compass-api.onrender.com/"
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
    }


def _app(store: CustomerProductionAcceptanceAuthorityStore | None) -> FastAPI:
    app = FastAPI()
    app.state.acceptance_authority_store = store
    app.include_router(router)
    app.add_middleware(RateLimitMiddleware, rpm=500)
    app.add_middleware(JWTAuthMiddleware)
    return app


class _FakeVerification:
    verified = True

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": "test-object-lock-receipt", "verified": True}


class _FakeReceipt:
    def __init__(self, digest: str, retain_until: datetime) -> None:
        self.object_url = "s3://test/authority?versionId=version-1"
        self.version_id = "version-1"
        self.retain_until = retain_until
        self.content_hash = digest

    def is_verifiable(self) -> bool:
        return True

    def validated_verification(self) -> _FakeVerification:
        return _FakeVerification()


class _FakeImmutableBackend:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.ready_checks = 0

    def assert_ready(self, *, expected: RetentionPolicy) -> None:
        assert expected.retention_days == 31
        self.ready_checks += 1

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
        return _FakeReceipt(content_hash, policy.retain_until())

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
    first = CustomerProductionAcceptanceAuthorityStore(first_backend)
    published = first.publish(
        "legal_publication_approval",
        _legal_evidence(now),
        expected_head_version=0,
        now=now,
    )
    assert published.head_version == 1
    assert published.storage_mode == "state_store"
    first_backend.close()

    second_backend = SqliteStateStore(path)
    second = CustomerProductionAcceptanceAuthorityStore(second_backend)
    loaded = second.load("legal_publication_approval", now=now)
    assert loaded.sha256 == published.sha256
    assert hashlib.sha256(loaded.body).hexdigest() == published.sha256
    assert loaded.body == json.dumps(
        _legal_evidence(now),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    assert second.current_head_version("legal_publication_approval") == 1
    second_backend.close()


def test_publish_requires_current_head_version() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    store = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
    store.publish(
        "legal_publication_approval",
        _legal_evidence(now),
        expected_head_version=0,
        now=now,
    )
    with pytest.raises(AcceptanceAuthorityConflict):
        store.publish(
            "legal_publication_approval",
            _legal_evidence(now),
            expected_head_version=0,
            now=now,
        )


def test_optional_worm_backend_has_no_inline_fallback_and_rechecks_exact_bytes() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    state = InMemoryStateStore()
    immutable = _FakeImmutableBackend()
    store = CustomerProductionAcceptanceAuthorityStore(
        state,
        immutable_backend=immutable,
        retention_policy=RetentionPolicy(mode="COMPLIANCE", retention_days=31),
    )
    published = store.publish(
        "legal_publication_approval",
        _legal_evidence(now),
        expected_head_version=0,
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

    key = f"customer-production-authority/legal_publication_approval/{published.sha256}.json"
    immutable.objects[(key, "version-1")] = b"{}"
    with pytest.raises(AcceptanceAuthorityUnavailable, match="byte length"):
        store.load("legal_publication_approval", now=now)


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
            now=now,
        )


def test_load_rejects_stale_evidence() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    store = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
    store.publish(
        "legal_publication_approval",
        _legal_evidence(now),
        expected_head_version=0,
        now=now,
    )
    with pytest.raises(AcceptanceAuthorityInvalid, match="stale"):
        store.load("legal_publication_approval", now=now + timedelta(days=31))


def test_route_returns_exact_document_without_auth_and_no_store_cache() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    store = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
    published = store.publish(
        "legal_publication_approval",
        _legal_evidence(now),
        expected_head_version=0,
        now=now,
    )
    path = ACCEPTANCE_AUTHORITY_PATH_BY_GATE["legal_publication_approval"]
    with TestClient(_app(store)) as client:
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == _legal_evidence(now)
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
    corrupt = CustomerProductionAcceptanceAuthorityStore(backend)
    corrupt.publish(
        "legal_publication_approval",
        _legal_evidence(now),
        expected_head_version=0,
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
    app = FastAPI()
    app.include_router(router)
    authority_routes = {
        route.path: route.methods
        for route in app.routes
        if getattr(route, "path", None) in ACCEPTANCE_AUTHORITY_PUBLIC_PATHS
    }
    assert set(authority_routes) == ACCEPTANCE_AUTHORITY_PUBLIC_PATHS
    assert all(methods == {"GET"} for methods in authority_routes.values())
