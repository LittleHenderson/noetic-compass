from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.config import settings
from api.middleware.auth import JWTAuthMiddleware, is_public_human_attestation_request
from api.middleware.rate_limit import RateLimitMiddleware
from api.routes import auth, human_attestations
from api.services.customer_production_acceptance_authority import (
    AcceptanceAuthorityInvalid,
    AcceptanceAuthorityUnavailable,
    CustomerProductionAcceptanceAuthorityStore,
)
from api.services.human_attestations import (
    HumanAttestationInvalid,
    HumanAttestationNotFound,
    HumanAttestationStore,
    canonical_evidence_binding_sha256,
)
from api.services.accounts.store import AccountStore
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.sessions import SessionStore
from api.services import human_attestations as human_attestation_service


NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC)
MASTER = "b911049453b45d9ee0c56e3dd20f0888d1c1435d"
DEPLOY = "dep-humanattestation"
TENANT = "primary"

ROLE_ACCOUNTS = {
    "legal_counsel": ("owner", "acct-00000000000000000000000000000001"),
    "privacy_owner": ("admin", "acct-00000000000000000000000000000002"),
    "product_owner": ("owner", "acct-00000000000000000000000000000003"),
    "legal_owner": ("admin", "acct-00000000000000000000000000000004"),
    "research_owner": ("operator", "acct-00000000000000000000000000000005"),
    "incident_commander": ("owner", "acct-00000000000000000000000000000006"),
    "operations": ("operator", "acct-00000000000000000000000000000007"),
    "security": ("admin", "acct-00000000000000000000000000000008"),
    "legal": ("admin", "acct-00000000000000000000000000000009"),
    "support": ("support", "acct-0000000000000000000000000000000a"),
    "operations_owner": ("operator", "acct-0000000000000000000000000000000b"),
    "security_owner": ("admin", "acct-0000000000000000000000000000000c"),
}


def _common(gate: str) -> dict[str, object]:
    stamp = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "gate": gate,
        "environment": "public-production",
        "repository": "LittleHenderson/noetic-compass",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "event_at_utc": stamp,
        "observed_at_utc": stamp,
    }


def _create(
    store: HumanAttestationStore,
    *,
    purpose: str,
    gate: str,
    role: str,
    binding: str,
    supports: list[dict[str, str]] | None = None,
    now: datetime = NOW,
):
    account_role, account_id = ROLE_ACCOUNTS[role]
    return store.create(
        actor_tenant_id=TENANT,
        actor_account_id=account_id,
        actor_account_role=account_role,
        purpose=purpose,
        gate=gate,
        attestation_role=role,
        master_head_sha=MASTER,
        deploy_id=DEPLOY,
        evidence_binding_sha256=binding,
        supporting_attestations=supports,
        now=now,
    )


def _reference(record, role: str) -> dict[str, str]:
    return {
        "role": role,
        "attestation_artifact_uri": record.uri,
        "attestation_sha256": record.sha256,
        "attested_at_utc": str(record.payload["attested_at_utc"]),
    }


def test_role_is_derived_from_authenticated_account_not_request_body() -> None:
    store = HumanAttestationStore(InMemoryStateStore(), primary_tenant_id=TENANT)
    with pytest.raises(HumanAttestationInvalid, match="account role"):
        store.create(
            actor_tenant_id=TENANT,
            actor_account_id=ROLE_ACCOUNTS["research_owner"][1],
            actor_account_role="operator",
            purpose="legal_approval",
            gate="legal_publication_approval",
            attestation_role="legal_counsel",
            master_head_sha=MASTER,
            deploy_id=DEPLOY,
            evidence_binding_sha256="a" * 64,
            now=NOW,
        )


@pytest.mark.parametrize(
    ("gate", "purpose", "roles"),
    [
        (
            "legal_publication_approval",
            "legal_approval",
            ("legal_counsel", "privacy_owner", "product_owner"),
        ),
        (
            "claim_honesty",
            "claim_approval",
            ("legal_owner", "product_owner", "research_owner"),
        ),
    ],
)
def test_direct_approvals_are_dereferenced_bound_and_distinct(
    gate: str, purpose: str, roles: tuple[str, ...]
) -> None:
    state = InMemoryStateStore()
    attestations = HumanAttestationStore(state, primary_tenant_id=TENANT)
    evidence = _common(gate)
    if gate == "legal_publication_approval":
        evidence.update(
            documents=[{"kind": "legal", "content_sha256": "1" * 64}],
            claim_status_vocabulary=["OPEN", "ACCEPT"],
        )
    else:
        evidence.update(
            scanned_surfaces=[{"kind": "product_app", "content_sha256": "2" * 64}],
            scan={"misleading_claim_count": 0},
            boundaries={"research_scope_disclosed": True},
        )
    binding = canonical_evidence_binding_sha256(gate, evidence)
    records = [
        _create(attestations, purpose=purpose, gate=gate, role=role, binding=binding)
        for role in roles
    ]
    evidence["approvals"] = [
        {
            "role": role,
            "approval_artifact_uri": record.uri,
            "approval_sha256": record.sha256,
            "approved_at_utc": record.payload["attested_at_utc"],
        }
        for role, record in zip(roles, records, strict=True)
    ]
    authority = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    authority.assert_human_attestations(gate, evidence, now=NOW)

    evidence["approvals"][0]["approval_sha256"] = "f" * 64
    with pytest.raises(AcceptanceAuthorityInvalid, match="invalid or revoked"):
        authority.assert_human_attestations(gate, evidence, now=NOW)


def test_legal_approvals_reject_two_roles_from_the_same_authenticated_account() -> None:
    state = InMemoryStateStore()
    attestations = HumanAttestationStore(state, primary_tenant_id=TENANT)
    evidence = _common("legal_publication_approval")
    evidence.update(
        documents=[{"kind": "legal", "content_sha256": "1" * 64}],
        claim_status_vocabulary=["OPEN", "ACCEPT"],
    )
    binding = canonical_evidence_binding_sha256(
        "legal_publication_approval", evidence
    )
    legal = _create(
        attestations,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="legal_counsel",
        binding=binding,
    )
    product = attestations.create(
        actor_tenant_id=TENANT,
        actor_account_id=ROLE_ACCOUNTS["legal_counsel"][1],
        actor_account_role="owner",
        purpose="legal_approval",
        gate="legal_publication_approval",
        attestation_role="product_owner",
        master_head_sha=MASTER,
        deploy_id=DEPLOY,
        evidence_binding_sha256=binding,
        now=NOW,
    )
    privacy = _create(
        attestations,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="privacy_owner",
        binding=binding,
    )
    evidence["approvals"] = [
        {
            "role": role,
            "approval_artifact_uri": record.uri,
            "approval_sha256": record.sha256,
            "approved_at_utc": record.payload["attested_at_utc"],
        }
        for role, record in (
            ("legal_counsel", legal),
            ("privacy_owner", privacy),
            ("product_owner", product),
        )
    ]
    authority = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    with pytest.raises(AcceptanceAuthorityInvalid, match="invalid or revoked"):
        authority.assert_human_attestations(
            "legal_publication_approval", evidence, now=NOW
        )


def test_incident_and_tabletop_aggregates_require_every_individual_actor() -> None:
    state = InMemoryStateStore()
    attestations = HumanAttestationStore(state, primary_tenant_id=TENANT)
    evidence = _common("incident_tabletop")
    evidence.update(
        incident={
            "record_id": "IR-2026-07-15-001",
            "status": "CLOSED",
            "closed_at_utc": "2026-07-15T12:00:00Z",
            "open_actions": 0,
            "postmortem_uri": "excluded-from-binding",
            "postmortem_sha256": "0" * 64,
            "credential_rotation_complete": True,
            "recovery_verified": True,
        },
        tabletop={
            "tabletop_id": "tabletop-20260715",
            "completed_at_utc": "2026-07-15T12:00:00Z",
            "participant_roles": [
                "incident_commander",
                "legal",
                "operations",
                "security",
                "support",
            ],
            "scenarios": ["worker_outage"],
            "open_actions": 0,
            "evidence_uri": "excluded-from-binding",
            "evidence_sha256": "0" * 64,
        },
    )
    binding = canonical_evidence_binding_sha256("incident_tabletop", evidence)
    closure = {
        role: _create(
            attestations,
            purpose="incident_closure",
            gate="incident_tabletop",
            role=role,
            binding=binding,
        )
        for role in ("incident_commander", "operations", "security")
    }
    postmortem = _create(
        attestations,
        purpose="incident_postmortem",
        gate="incident_tabletop",
        role="incident_commander",
        binding=binding,
        supports=[_reference(record, role) for role, record in closure.items()],
    )
    participants = {
        role: _create(
            attestations,
            purpose="tabletop_completion",
            gate="incident_tabletop",
            role=role,
            binding=binding,
        )
        for role in ("incident_commander", "legal", "operations", "security", "support")
    }
    tabletop = _create(
        attestations,
        purpose="tabletop_evidence",
        gate="incident_tabletop",
        role="incident_commander",
        binding=binding,
        supports=[_reference(record, role) for role, record in participants.items()],
    )
    evidence["incident"]["postmortem_uri"] = postmortem.uri
    evidence["incident"]["postmortem_sha256"] = postmortem.sha256
    evidence["tabletop"]["evidence_uri"] = tabletop.uri
    evidence["tabletop"]["evidence_sha256"] = tabletop.sha256
    authority = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    authority.assert_human_attestations("incident_tabletop", evidence, now=NOW)

    attestations.revoke(
        participants["support"].sha256,
        actor_tenant_id=TENANT,
        actor_account_id=ROLE_ACCOUNTS["support"][1],
        actor_account_role="support",
        now=NOW,
    )
    with pytest.raises(AcceptanceAuthorityUnavailable, match="invalid or revoked"):
        authority.assert_human_attestations(
            "incident_tabletop",
            evidence,
            now=NOW,
            serving_active_revision=True,
        )


def test_release_aggregate_requires_four_roles_and_child_revocation_fails_closed() -> None:
    state = InMemoryStateStore()
    attestations = HumanAttestationStore(state, primary_tenant_id=TENANT)
    evidence = _common("release_decision")
    evidence.update(
        status="ACCEPT",
        approved_at_utc="2026-07-15T12:00:00Z",
        approver_roles=["legal_owner", "operations_owner", "product_owner", "security_owner"],
        decision_record_uri="excluded-from-binding",
        decision_record_sha256="0" * 64,
    )
    binding = canonical_evidence_binding_sha256("release_decision", evidence)
    approvals = {
        role: _create(
            attestations,
            purpose="release_approval",
            gate="release_decision",
            role=role,
            binding=binding,
        )
        for role in ("legal_owner", "operations_owner", "product_owner", "security_owner")
    }
    decision = _create(
        attestations,
        purpose="release_decision_record",
        gate="release_decision",
        role="product_owner",
        binding=binding,
        supports=[_reference(record, role) for role, record in approvals.items()],
    )
    evidence["decision_record_uri"] = decision.uri
    evidence["decision_record_sha256"] = decision.sha256
    authority = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    authority.assert_human_attestations("release_decision", evidence, now=NOW)

    attestations.revoke(
        approvals["security_owner"].sha256,
        actor_tenant_id=TENANT,
        actor_account_id=ROLE_ACCOUNTS["security_owner"][1],
        actor_account_role="admin",
        now=NOW,
    )
    with pytest.raises(HumanAttestationNotFound):
        attestations.load(decision.sha256, now=NOW)


def test_release_aggregate_rejects_a_child_created_before_the_evidence_window() -> None:
    state = InMemoryStateStore()
    attestations = HumanAttestationStore(state, primary_tenant_id=TENANT)
    evidence = _common("release_decision")
    evidence.update(
        status="ACCEPT",
        approved_at_utc="2026-07-15T12:00:00Z",
        approver_roles=["legal_owner", "operations_owner", "product_owner", "security_owner"],
        decision_record_uri="excluded-from-binding",
        decision_record_sha256="0" * 64,
    )
    binding = canonical_evidence_binding_sha256("release_decision", evidence)
    approvals = {
        role: _create(
            attestations,
            purpose="release_approval",
            gate="release_decision",
            role=role,
            binding=binding,
            now=NOW - timedelta(seconds=1) if role == "legal_owner" else NOW,
        )
        for role in ("legal_owner", "operations_owner", "product_owner", "security_owner")
    }
    decision = _create(
        attestations,
        purpose="release_decision_record",
        gate="release_decision",
        role="product_owner",
        binding=binding,
        supports=[_reference(record, role) for role, record in approvals.items()],
    )
    evidence["decision_record_uri"] = decision.uri
    evidence["decision_record_sha256"] = decision.sha256
    authority = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )
    with pytest.raises(AcceptanceAuthorityInvalid, match="invalid or revoked"):
        authority.assert_human_attestations("release_decision", evidence, now=NOW)


def test_create_recovers_an_exact_content_row_left_before_activation() -> None:
    class FailFirstStatusWriteStore(InMemoryStateStore):
        fail_status_write = True

        def put(self, record, *, expected_version):  # type: ignore[no-untyped-def]
            if (
                self.fail_status_write
                and record.kind == human_attestation_service.STATUS_KIND
            ):
                self.fail_status_write = False
                raise RuntimeError("simulated status write failure")
            return super().put(record, expected_version=expected_version)

    state = FailFirstStatusWriteStore()
    store = HumanAttestationStore(state, primary_tenant_id=TENANT)
    values = {
        "actor_tenant_id": TENANT,
        "actor_account_id": ROLE_ACCOUNTS["legal_counsel"][1],
        "actor_account_role": "owner",
        "purpose": "legal_approval",
        "gate": "legal_publication_approval",
        "attestation_role": "legal_counsel",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "evidence_binding_sha256": "a" * 64,
        "now": NOW,
    }
    with pytest.raises(human_attestation_service.HumanAttestationUnavailable):
        store.create(**values)
    recovered = store.create(**values)
    assert store.load(recovered.sha256, now=NOW).body == recovered.body
    assert store.create(**values).sha256 == recovered.sha256

    store.revoke(
        recovered.sha256,
        actor_tenant_id=TENANT,
        actor_account_id=ROLE_ACCOUNTS["legal_counsel"][1],
        actor_account_role="owner",
        now=NOW,
    )
    with pytest.raises(HumanAttestationInvalid, match="cannot be reactivated"):
        store.create(**values)


def test_sqlite_attestation_and_revocation_survive_restart(tmp_path) -> None:
    path = tmp_path / "human-attestations.db"
    first_backend = SqliteStateStore(path)
    first = HumanAttestationStore(first_backend, primary_tenant_id=TENANT)
    created = _create(
        first,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="legal_counsel",
        binding="a" * 64,
    )
    first_backend.close()

    second_backend = SqliteStateStore(path)
    second = HumanAttestationStore(second_backend, primary_tenant_id=TENANT)
    assert second.load(created.sha256, now=NOW).body == created.body
    second.revoke(
        created.sha256,
        actor_tenant_id=TENANT,
        actor_account_id=ROLE_ACCOUNTS["legal_counsel"][1],
        actor_account_role="owner",
        now=NOW,
    )
    second_backend.close()

    third_backend = SqliteStateStore(path)
    third = HumanAttestationStore(third_backend, primary_tenant_id=TENANT)
    with pytest.raises(HumanAttestationNotFound, match="revoked"):
        third.load(created.sha256, now=NOW)
    third_backend.close()


def test_authenticated_route_creates_reads_and_revokes_exact_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = InMemoryStateStore()
    account_store = AccountStore(
        backend, credential_pepper="human-attestation-test-pepper-at-least-32-bytes"
    )
    session_store = SessionStore(backend)
    owner_credential = "casak_humanattestationowner0123456789abcdefghijklmnopqr"
    other_credential = "casak_humanattestationother0123456789abcdefghijklmnopqr"
    account_store.bootstrap_owner(
        email_or_username="owner@example.test",
        tenant_id=TENANT,
        api_credential=owner_credential,
    )
    other_invite = account_store.create_invite(
        role="owner", tenant_id="other", code="human-attestation-other-owner"
    )
    account_store.redeem_invite(
        code=other_invite.code,
        email_or_username="other@example.test",
        api_credential=other_credential,
    )
    app = FastAPI()
    app.state.account_store = account_store
    app.state.session_store = session_store
    app.state.human_attestation_store = HumanAttestationStore(
        backend, primary_tenant_id=TENANT
    )
    app.include_router(auth.router)
    app.include_router(human_attestations.router)
    app.add_middleware(RateLimitMiddleware, rpm=500)
    app.add_middleware(JWTAuthMiddleware)
    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "accounts_bootstrap_tenant_id", TENANT)

    body = {
        "purpose": "legal_approval",
        "gate": "legal_publication_approval",
        "attestation_role": "legal_counsel",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "evidence_binding_sha256": "a" * 64,
        "supporting_attestations": [],
    }
    with TestClient(app) as client:
        def login(identity: str, credential: str) -> dict[str, str]:
            response = client.post(
                "/auth/token",
                json={"username": identity, "api_credential": credential},
            )
            assert response.status_code == 200, response.text
            return {"Authorization": f"Bearer {response.json()['token']}"}

        owner_headers = login("owner@example.test", owner_credential)
        other_headers = login("other@example.test", other_credential)
        assert client.post("/accounts/human-attestations", json=body).status_code == 401
        assert client.post(
            "/accounts/human-attestations", json=body, headers=other_headers
        ).status_code == 403

        created = client.post(
            "/accounts/human-attestations", json=body, headers=owner_headers
        )
        assert created.status_code == 201, created.text
        output = created.json()
        public_path = output["attestation_artifact_uri"].removeprefix(
            "https://cas-harness-customer-api.onrender.com"
        )
        public = client.get(public_path)
        assert public.status_code == 200
        assert public.headers["cache-control"] == "no-store, max-age=0"
        assert public.headers["etag"] == f'"sha256:{output["attestation_sha256"]}"'
        assert output["attestation_sha256"] == hashlib.sha256(public.content).hexdigest()
        assert "owner@example.test" not in public.text
        assert client.get(public_path + "?enumerate=1").status_code == 401

        revoked = client.post(
            f'/accounts/human-attestations/{output["attestation_sha256"]}/revoke',
            headers=owner_headers,
        )
        assert revoked.status_code == 200
        assert client.get(public_path).status_code == 404

        def revoked_child(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise HumanAttestationNotFound("supporting attestation is revoked")

        monkeypatch.setattr(HumanAttestationStore, "create", revoked_child)
        rejected = client.post(
            "/accounts/human-attestations", json=body, headers=owner_headers
        )
        assert rejected.status_code == 422
        assert rejected.headers["cache-control"] == "no-store, max-age=0"


def test_public_attestation_matcher_is_exact_query_free_get_only() -> None:
    path = "/internal/human-attestations/" + "a" * 64
    assert is_public_human_attestation_request(path, "GET") is True
    assert is_public_human_attestation_request(path, "HEAD") is False
    assert is_public_human_attestation_request(path, "GET", "download=1") is False
    assert is_public_human_attestation_request(path.upper(), "GET") is False
    assert is_public_human_attestation_request(path + "/child", "GET") is False
