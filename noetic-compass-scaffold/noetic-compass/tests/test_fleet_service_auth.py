from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import secrets

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from api.config import Settings, settings
from api.routes import cas_harness_audit
from api.middleware.auth import (
    is_account_mode_allowed_path,
    is_fleet_service_callback_path,
)
from api.routes.cas_harness_audit import router
from api.services.cas_harness_distributed_audits import reset_distributed_audits_for_tests
from api.services.cas_harness_fleet_executor import (
    FleetRunRecord,
    heartbeat_worker,
    list_workers,
    register_worker,
    reset_fleet_executor_for_tests,
)
from api.services.cas_harness_evidence_object_store import (
    active_evidence_packet_storage_scope,
    configure_evidence_packet_repository,
)
from api.services.evidence_ownership import tenant_owns_trace
from api.services.fleet_service_auth import (
    FleetServiceAuthenticationError,
    FleetServiceAuthorizationError,
    FleetServiceAuthStore,
)
from api.services.production.state_substrate import InMemoryStateStore
from api.services.production.state_substrate.sqlite_store import SqliteStateStore


PEPPER = "fleet-service-test-pepper-32-bytes-minimum"


def setup_function() -> None:
    reset_fleet_executor_for_tests()
    reset_distributed_audits_for_tests()


def _owned_store(
    *, tenant_id: str = "tenant-a", account_id: str = "account-a", audit_id: str = "audit-a"
) -> tuple[InMemoryStateStore, FleetServiceAuthStore]:
    backend = InMemoryStateStore()
    auth = FleetServiceAuthStore(backend, pepper=PEPPER)
    auth.record_audit_owner(tenant_id=tenant_id, account_id=account_id, audit_id=audit_id)
    return backend, auth


def _issue_worker(auth: FleetServiceAuthStore, *, now: datetime | None = None):
    return auth.issue_credential(
        tenant_id="tenant-a",
        account_id="account-a",
        audit_id="audit-a",
        fleet_id="audit-a",
        worker_id="probe-worker-1",
        capabilities=["register_worker", "heartbeat", "lease_job", "submit_receipt"],
        ttl_seconds=3600,
        now=now,
    )


def _authenticate(
    auth: FleetServiceAuthStore,
    credential,
    *,
    nonce: str | None = None,
    capability: str = "heartbeat",
    tenant_id: str = "tenant-a",
    audit_id: str = "audit-a",
    worker_id: str | None = "probe-worker-1",
    now: datetime | None = None,
):
    stamp = now or datetime.now(UTC)
    return auth.authenticate(
        tenant_id=tenant_id,
        api_credential=credential.api_credential,
        timestamp=str(int(stamp.timestamp())),
        nonce=nonce or secrets.token_urlsafe(18),
        required_capability=capability,
        audit_id=audit_id,
        fleet_id=audit_id,
        worker_id=worker_id,
        now=stamp,
    )


def test_issued_secret_is_returned_once_but_persistence_is_hash_only() -> None:
    backend, auth = _owned_store()
    credential = _issue_worker(auth)

    assert credential.api_credential.startswith("casfs_fsc_")
    stored = backend.get("tenant-a", "fleet_service_credential", credential.credential_id)
    assert stored is not None
    serialized = repr(dict(stored.payload))
    assert credential.api_credential not in serialized
    assert credential.api_credential.split(".", 1)[1] not in serialized
    listed = auth.list_credentials(tenant_id="tenant-a", audit_id="audit-a")
    assert listed[0].api_credential is None
    assert "api_credential" not in listed[0].to_public_dict()


def test_tenant_audit_worker_and_capability_scopes_fail_closed() -> None:
    _backend, auth = _owned_store()
    credential = _issue_worker(auth)

    with pytest.raises(FleetServiceAuthenticationError):
        _authenticate(auth, credential, tenant_id="tenant-b")
    with pytest.raises(FleetServiceAuthorizationError):
        _authenticate(auth, credential, audit_id="audit-b")
    with pytest.raises(FleetServiceAuthorizationError):
        _authenticate(auth, credential, worker_id="probe-worker-2")
    with pytest.raises(FleetServiceAuthorizationError):
        _authenticate(auth, credential, capability="merge_fleet", worker_id=None)


def test_expiry_and_revocation_take_effect_on_the_next_callback() -> None:
    stamp = datetime.now(UTC)
    _backend, auth = _owned_store()
    expired = _issue_worker(auth, now=stamp - timedelta(hours=2))
    with pytest.raises(FleetServiceAuthenticationError):
        _authenticate(auth, expired, now=stamp)

    active = _issue_worker(auth, now=stamp)
    _authenticate(auth, active, now=stamp)
    revoked = auth.revoke_credential(
        tenant_id="tenant-a",
        account_id="account-a",
        audit_id="audit-a",
        credential_id=active.credential_id,
        now=stamp + timedelta(seconds=1),
    )
    assert revoked is not None and revoked.revoked_at is not None
    with pytest.raises(FleetServiceAuthenticationError):
        _authenticate(auth, active, now=stamp + timedelta(seconds=2))


def test_controller_credentials_are_separate_from_worker_capabilities() -> None:
    _backend, auth = _owned_store()
    controller = auth.issue_credential(
        tenant_id="tenant-a",
        account_id="account-b",
        audit_id="audit-a",
        fleet_id="audit-a",
        worker_id=None,
        capabilities=["merge_distributed", "merge_fleet", "verify_fleet"],
        ttl_seconds=600,
    )
    principal = _authenticate(
        auth, controller, capability="merge_fleet", worker_id=None
    )
    assert principal.worker_id is None
    assert principal.account_id == "account-a"
    with pytest.raises(FleetServiceAuthorizationError):
        _authenticate(auth, controller, capability="heartbeat")


def test_service_merge_and_verifier_use_tenant_packet_scope_and_record_ownership(
    monkeypatch, request,
) -> None:
    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "fleet_service_auth_enabled", True)
    monkeypatch.setattr(settings, "evidence_packet_object_store_enabled", True)
    monkeypatch.setattr(settings, "billing_entitlements_enabled", False)
    monkeypatch.setattr(settings, "fleet_service_credential_pepper", PEPPER)
    # The route requires the lifespan-owned repository before it establishes
    # the ContextVar. The merge/load calls are replaced below, so only the
    # repository identity is needed for this route-level scope regression.
    configure_evidence_packet_repository(object())  # type: ignore[arg-type]
    request.addfinalizer(lambda: configure_evidence_packet_repository(None))

    backend, auth = _owned_store()
    credential = auth.issue_credential(
        tenant_id="tenant-a",
        account_id="account-a",
        audit_id="audit-a",
        fleet_id="audit-a",
        worker_id=None,
        capabilities=["merge_fleet", "verify_fleet"],
        ttl_seconds=3600,
    )
    now = datetime.now(UTC).isoformat()
    run = FleetRunRecord(
        audit_id="audit-a",
        status="COMPLETE",
        verifier_gate_status="ready_for_verifier",
        jobs=[],
        created_at=now,
        updated_at=now,
        require_scoped_workers=True,
        merged_packet_trace_id="trace-fleet-merged",
        merge_reason="Merged under the tenant packet scope.",
    )
    observed: list[tuple[str, str]] = []

    def fake_merge(audit_id: str):
        scope = active_evidence_packet_storage_scope()
        assert scope is not None
        observed.append((scope.tenant_id, scope.account_id))
        return run

    monkeypatch.setattr(cas_harness_audit, "merge_fleet_evidence", fake_merge)
    monkeypatch.setattr(cas_harness_audit, "get_fleet_run", lambda audit_id: run)

    app = FastAPI()
    app.state.shared_state_store = backend
    app.include_router(router)
    client = TestClient(app)

    def service_headers() -> dict[str, str]:
        return {
            "Authorization": f"CAS-Service {credential.api_credential}",
            "X-CAS-Tenant-ID": "tenant-a",
            "X-CAS-Audit-ID": "audit-a",
            "X-CAS-Service-Timestamp": str(int(datetime.now(UTC).timestamp())),
            "X-CAS-Service-Nonce": secrets.token_urlsafe(24),
        }

    merged = client.post(
        "/api/cas-harness/audit/distributed/session/audit-a/fleet/merge",
        headers=service_headers(),
    )
    assert merged.status_code == 200, merged.text
    assert observed == [("tenant-a", "account-a")]
    assert tenant_owns_trace(backend, tenant_id="tenant-a", trace_id="trace-fleet-merged")
    assert not tenant_owns_trace(
        backend, tenant_id="tenant-b", trace_id="trace-fleet-merged"
    )

    class _VerifierScopeObserved(RuntimeError):
        pass

    def observe_verifier_load(trace_id: str):
        scope = active_evidence_packet_storage_scope()
        assert scope is not None
        observed.append((scope.tenant_id, scope.account_id))
        raise _VerifierScopeObserved

    monkeypatch.setattr(cas_harness_audit, "_packet_payload_for_trace", observe_verifier_load)
    with pytest.raises(_VerifierScopeObserved):
        client.post(
            "/api/cas-harness/audit/distributed/session/audit-a/fleet/verifier",
            headers=service_headers(),
        )
    assert observed == [
        ("tenant-a", "account-a"),
        ("tenant-a", "account-a"),
    ]


def test_same_tenant_manager_can_revoke_after_original_issuer_is_unavailable() -> None:
    _backend, auth = _owned_store()
    credential = _issue_worker(auth)
    revoked = auth.revoke_credential(
        tenant_id="tenant-a",
        account_id="replacement-admin",
        audit_id="audit-a",
        credential_id=credential.credential_id,
    )
    assert revoked is not None and revoked.revoked_at is not None


def test_nonce_replay_and_concurrent_duplicates_have_exactly_one_winner() -> None:
    _backend, auth = _owned_store()
    credential = _issue_worker(auth)
    stamp = datetime.now(UTC)
    nonce = secrets.token_urlsafe(24)

    def attempt() -> str:
        try:
            _authenticate(auth, credential, nonce=nonce, now=stamp)
            return "accepted"
        except FleetServiceAuthenticationError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _index: attempt(), range(8)))
    assert results.count("accepted") == 1
    assert results.count("rejected") == 7
    with pytest.raises(FleetServiceAuthenticationError):
        _authenticate(auth, credential, nonce=nonce, now=stamp)


def test_expiry_revocation_and_consumed_nonce_survive_sqlite_restart(tmp_path) -> None:
    path = tmp_path / "fleet-auth.db"
    stamp = datetime.now(UTC)
    first_backend = SqliteStateStore(path)
    first = FleetServiceAuthStore(first_backend, pepper=PEPPER)
    first.record_audit_owner(tenant_id="tenant-a", account_id="account-a", audit_id="audit-a")
    credential = _issue_worker(first, now=stamp)
    nonce = secrets.token_urlsafe(24)
    _authenticate(first, credential, nonce=nonce, now=stamp)
    first_backend.close()

    second_backend = SqliteStateStore(path)
    second = FleetServiceAuthStore(second_backend, pepper=PEPPER)
    with pytest.raises(FleetServiceAuthenticationError):
        _authenticate(second, credential, nonce=nonce, now=stamp + timedelta(seconds=1))
    _authenticate(second, credential, now=stamp + timedelta(seconds=2))
    second.revoke_credential(
        tenant_id="tenant-a",
        account_id="account-a",
        audit_id="audit-a",
        credential_id=credential.credential_id,
        now=stamp + timedelta(seconds=3),
    )
    second_backend.close()

    third_backend = SqliteStateStore(path)
    third = FleetServiceAuthStore(third_backend, pepper=PEPPER)
    with pytest.raises(FleetServiceAuthenticationError):
        _authenticate(third, credential, now=stamp + timedelta(seconds=4))
    third_backend.close()


def test_callback_path_allowlist_is_exact_and_feature_stays_dark(monkeypatch) -> None:
    callback = "/api/cas-harness/audit/distributed/session/audit-a/fleet/job/lease"
    assert is_fleet_service_callback_path(callback)
    assert not is_fleet_service_callback_path(callback + "/extra")
    assert not is_fleet_service_callback_path(
        "/api/cas-harness/audit/distributed/session/audit-a/fleet/service-credentials"
    )

    monkeypatch.setattr(settings, "fleet_service_auth_enabled", False)
    assert not is_account_mode_allowed_path(callback)
    monkeypatch.setattr(settings, "fleet_service_auth_enabled", True)
    assert is_account_mode_allowed_path(callback)


def test_configuration_fails_loud_on_partial_enablement() -> None:
    assert Settings(_env_file=None).fleet_service_auth_enabled is False
    without_accounts = Settings(
        _env_file=None,
        NC_FLEET_SERVICE_AUTH_ENABLED=True,
        NC_FLEET_SERVICE_CREDENTIAL_PEPPER=PEPPER,
    )
    with pytest.raises(RuntimeError, match="requires NC_ACCOUNTS_ENABLED"):
        without_accounts.validate_account_storage()
    short_pepper = Settings(
        _env_file=None,
        NC_ACCOUNTS_ENABLED=True,
        NC_FLEET_SERVICE_AUTH_ENABLED=True,
        NC_FLEET_SERVICE_CREDENTIAL_PEPPER="short",
    )
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        short_pepper.validate_account_storage()


def test_identical_worker_ids_are_isolated_by_audit_scope() -> None:
    first = register_worker(
        worker_id="probe-worker-1",
        audit_id="audit-a",
        model_id="model-a",
        worker_url="https://a.worker.example",
        gpu_type="H100",
        capacity=1,
        supported_methods=["readout"],
    )
    second = register_worker(
        worker_id="probe-worker-1",
        audit_id="audit-b",
        model_id="model-b",
        worker_url="https://b.worker.example",
        gpu_type="H200",
        capacity=1,
        supported_methods=["causal_ablation"],
    )
    assert first is not second
    assert list_workers(audit_id="audit-a") == [first]
    assert list_workers(audit_id="audit-b") == [second]
    assert heartbeat_worker("probe-worker-1", audit_id="audit-b") is second
    assert heartbeat_worker("probe-worker-1", audit_id="audit-missing") is None


def test_registration_route_rejects_customer_bearer_and_replayed_service_callback(
    monkeypatch,
) -> None:
    # A tiny identity shim stands in for the already-tested JWT/session middleware and writes only
    # server-side request.state fields. This proves the actual API issues the worker secret once;
    # the callback route must then refuse that same customer's Bearer token.
    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "fleet_service_auth_enabled", True)
    monkeypatch.setattr(settings, "fleet_service_credential_pepper", PEPPER)
    app = FastAPI()

    @app.middleware("http")
    async def attach_test_identity(request, call_next):
        if request.headers.get("Authorization") == "Bearer customer-jwt":
            request.state.tenant_id = "tenant-a"
            request.state.account_id = "account-a"
            request.state.role = "operator"
        return await call_next(request)

    app.include_router(router)
    backend = InMemoryStateStore()
    app.state.shared_state_store = backend
    client = TestClient(app)

    created = client.post(
        "/api/cas-harness/audit/distributed/session",
        json={
            "model_id": "customer/open-weight-20b",
            "weight_access": "open_weight",
            "parameter_count_b": 20,
            "num_layers": 8,
            "precision": "bf16",
            "available_gpu_memory_gb": 80,
            "accept_audit_data_capture": True,
        },
        headers={"Authorization": "Bearer customer-jwt"},
    )
    assert created.status_code == 200, created.text
    audit = created.json()

    worker = audit["worker_evidence"][0]
    issued = client.post(
        f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}/fleet/service-credentials",
        json={
            "worker_id": worker["worker_id"],
            "capabilities": ["register_worker"],
            "ttl_seconds": 3600,
        },
        headers={"Authorization": "Bearer customer-jwt"},
    )
    assert issued.status_code == 201, issued.text
    credential = issued.json()["api_credential"]
    assert credential.startswith("casfs_fsc_")

    payload = {
        "worker_id": worker["worker_id"],
        "model_id": audit["plan"]["model_id"],
        "worker_url": "https://worker.example",
        "gpu_type": "H100-80GB",
        "capacity": 1,
        "supported_methods": worker["assigned_methods"],
    }
    url = "/api/cas-harness/audit/distributed/fleet/worker/register"
    assert client.post(url, json=payload, headers={"Authorization": "Bearer customer-jwt"}).status_code == 401

    stamp = str(int(datetime.now(UTC).timestamp()))
    nonce = secrets.token_urlsafe(24)
    headers = {
        "Authorization": f"CAS-Service {credential}",
        "X-CAS-Tenant-ID": "tenant-a",
        "X-CAS-Audit-ID": audit["audit_id"],
        "X-CAS-Service-Timestamp": stamp,
        "X-CAS-Service-Nonce": nonce,
    }
    accepted = client.post(url, json=payload, headers=headers)
    assert accepted.status_code == 200, accepted.text
    assert client.post(url, json=payload, headers=headers).status_code == 401

    class _BombBillingStore:
        def resolve_entitlement(self, tenant_id: str):
            raise AssertionError("credential revocation consulted current billing")

    monkeypatch.setattr(settings, "billing_entitlements_enabled", True)
    app.state.billing_entitlement_store = _BombBillingStore()
    revoked = client.delete(
        (
            f"/api/cas-harness/audit/distributed/session/{audit['audit_id']}"
            f"/fleet/service-credentials/{issued.json()['credential_id']}"
        ),
        headers={"Authorization": "Bearer customer-jwt"},
    )
    assert revoked.status_code == 200, revoked.text
    headers["X-CAS-Service-Nonce"] = secrets.token_urlsafe(24)
    assert client.post(url, json=payload, headers=headers).status_code == 401


def test_tenant_stale_scan_does_not_mutate_another_tenants_worker(monkeypatch) -> None:
    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "fleet_service_auth_enabled", True)
    monkeypatch.setattr(settings, "fleet_service_credential_pepper", PEPPER)
    app = FastAPI()

    @app.middleware("http")
    async def attach_test_identity(request, call_next):
        authorization = request.headers.get("Authorization")
        if authorization in {"Bearer tenant-a", "Bearer tenant-b"}:
            tenant_id = authorization.removeprefix("Bearer ")
            request.state.tenant_id = tenant_id
            request.state.account_id = f"account-{tenant_id[-1]}"
            request.state.role = "operator"
        return await call_next(request)

    app.include_router(router)
    backend = InMemoryStateStore()
    app.state.shared_state_store = backend
    auth = FleetServiceAuthStore(backend, pepper=PEPPER)
    workers = []
    for suffix in ("a", "b"):
        tenant_id = f"tenant-{suffix}"
        account_id = f"account-{suffix}"
        audit_id = f"audit-{suffix}"
        worker_id = f"probe-worker-{suffix}"
        auth.record_audit_owner(
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
        )
        auth.issue_credential(
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
            fleet_id=audit_id,
            worker_id=worker_id,
            capabilities=["heartbeat"],
            ttl_seconds=3600,
        )
        worker = register_worker(
            worker_id=worker_id,
            audit_id=audit_id,
            model_id="model-a",
            worker_url=f"https://{suffix}.worker.example",
            gpu_type="H100",
            capacity=1,
            supported_methods=["readout"],
        )
        worker.last_heartbeat_at = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        workers.append(worker)

    response = TestClient(app).post(
        "/api/cas-harness/audit/distributed/fleet/workers/stale-scan",
        json={"max_heartbeat_age_seconds": 1},
        headers={"Authorization": "Bearer tenant-a"},
    )

    assert response.status_code == 200, response.text
    assert [worker["worker_id"] for worker in response.json()["workers"]] == [
        "probe-worker-a"
    ]
    assert workers[0].status == "stale"
    assert workers[1].status == "active"
