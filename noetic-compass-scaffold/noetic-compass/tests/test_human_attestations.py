from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json

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
    RELEASE_DECISION_EVIDENCE_HASH_GATES,
)
from api.services.human_attestations import (
    HumanAttestation,
    HumanAttestationInvalid,
    HumanAttestationNotFound,
    HumanAttestationStore,
    HumanAttestationUnavailable,
    PUBLIC_HUMAN_ASSURANCE_BOUNDARY,
    canonical_evidence_binding_sha256,
    parse_human_attestation_pseudonym_keyring,
)
from api.services.accounts.store import AccountStore
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.production.state_substrate import LedgerRecord
from api.services.sessions import SessionStore
from api.services import human_attestations as human_attestation_service


NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC)
MASTER = "b911049453b45d9ee0c56e3dd20f0888d1c1435d"
DEPLOY = "dep-humanattestation"
TENANT = "primary"
PSEUDONYM_KEY_ID = "hatk_0123456789abcdef0123456789abcdef"
PSEUDONYM_KEY_ID_V2 = "hatk_fedcba9876543210fedcba9876543210"
PSEUDONYM_KEYRING = {
    PSEUDONYM_KEY_ID: hashlib.sha256(
        b"cas-human-attestation-test-key-v1"
    ).digest()
}


def _external_key(key: bytes) -> str:
    return "base64url:" + base64.urlsafe_b64encode(key).rstrip(b"=").decode(
        "ascii"
    )

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


def _attestation_store(
    backend,
    *,
    keyring: dict[str, bytes] | None = None,
    active_key_id: str = PSEUDONYM_KEY_ID,
    primary_tenant_id: str = TENANT,
) -> HumanAttestationStore:
    return HumanAttestationStore(
        backend,
        primary_tenant_id=primary_tenant_id,
        pseudonym_keyring=keyring or PSEUDONYM_KEYRING,
        active_pseudonym_key_id=active_key_id,
    )


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
        "human_assurance_boundary": dict(PUBLIC_HUMAN_ASSURANCE_BOUNDARY),
    }


def _release_evidence_hashes() -> dict[str, str]:
    return {
        gate: hashlib.sha256(f"required-gate:{gate}".encode()).hexdigest()
        for gate in RELEASE_DECISION_EVIDENCE_HASH_GATES
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
    store = _attestation_store(InMemoryStateStore())
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


def test_public_actor_is_keyed_tenant_scoped_and_carries_exact_claim_boundary() -> None:
    account_id = ROLE_ACCOUNTS["legal_counsel"][1]
    first = _create(
        _attestation_store(InMemoryStateStore()),
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="legal_counsel",
        binding="a" * 64,
    )
    actor = first.payload["actor"]
    assert isinstance(actor, dict)
    assert actor["assurance_boundary"] == dict(PUBLIC_HUMAN_ASSURANCE_BOUNDARY)
    assert actor["pseudonymization_scheme"] == "hmac-sha256-tenant-scoped-v1"
    assert actor["pseudonym_key_id"] == PSEUDONYM_KEY_ID
    for field in ("tenant_subject", "account_subject"):
        assert isinstance(actor[field], str)
        assert actor[field].startswith("hmac-sha256:")
        assert len(actor[field]) == len("hmac-sha256:") + 64
    assert "identity_binding_hmac" not in actor
    public_text = first.body.decode("ascii")
    assert TENANT not in public_text
    assert account_id not in public_text
    assert hashlib.sha256(TENANT.encode()).hexdigest() not in public_text
    assert hashlib.sha256(account_id.encode()).hexdigest() not in public_text

    other_tenant = "other-primary"
    other = _attestation_store(
        InMemoryStateStore(), primary_tenant_id=other_tenant
    ).create(
        actor_tenant_id=other_tenant,
        actor_account_id=account_id,
        actor_account_role="owner",
        purpose="legal_approval",
        gate="legal_publication_approval",
        attestation_role="legal_counsel",
        master_head_sha=MASTER,
        deploy_id=DEPLOY,
        evidence_binding_sha256="a" * 64,
        now=NOW,
    )
    other_actor = other.payload["actor"]
    assert isinstance(other_actor, dict)
    assert actor["account_subject"] != other_actor["account_subject"]


@pytest.mark.parametrize(
    ("raw", "active"),
    [
        ("", PSEUDONYM_KEY_ID),
        (
            json.dumps({PSEUDONYM_KEY_ID: "base64url:c2hvcnQ"}),
            PSEUDONYM_KEY_ID,
        ),
        (
            json.dumps(
                {
                    PSEUDONYM_KEY_ID: _external_key(
                        PSEUDONYM_KEYRING[PSEUDONYM_KEY_ID]
                    )
                }
            ),
            PSEUDONYM_KEY_ID_V2,
        ),
        (
            '{"'
            + PSEUDONYM_KEY_ID
            + '":"'
            + _external_key(PSEUDONYM_KEYRING[PSEUDONYM_KEY_ID])
            + '","'
            + PSEUDONYM_KEY_ID
            + '":"'
            + _external_key(hashlib.sha256(b"another-key").digest())
            + '"}',
            PSEUDONYM_KEY_ID,
        ),
        (
            json.dumps(
                {
                    PSEUDONYM_KEY_ID: _external_key(
                        PSEUDONYM_KEYRING[PSEUDONYM_KEY_ID]
                    ),
                    PSEUDONYM_KEY_ID_V2: _external_key(
                        PSEUDONYM_KEYRING[PSEUDONYM_KEY_ID]
                    ),
                }
            ),
            PSEUDONYM_KEY_ID_V2,
        ),
        (
            json.dumps({PSEUDONYM_KEY_ID: "a" * 32}),
            PSEUDONYM_KEY_ID,
        ),
        (
            json.dumps(
                {PSEUDONYM_KEY_ID: _external_key(b"a" * 32)}
            ),
            PSEUDONYM_KEY_ID,
        ),
        (
            json.dumps(
                {
                    PSEUDONYM_KEY_ID: _external_key(
                        b"0123456789abcdef" * 2
                    )
                }
            ),
            PSEUDONYM_KEY_ID,
        ),
        (
            json.dumps(
                {PSEUDONYM_KEY_ID: _external_key(bytes(range(32)))}
            ),
            PSEUDONYM_KEY_ID,
        ),
        (
            json.dumps(
                {
                    "acct-00000000000000000000000000000001": _external_key(
                        PSEUDONYM_KEYRING[PSEUDONYM_KEY_ID]
                    )
                }
            ),
            "acct-00000000000000000000000000000001",
        ),
    ],
)
def test_pseudonym_keyring_rejects_missing_weak_duplicate_or_unbound_keys(
    raw: str, active: str
) -> None:
    with pytest.raises(ValueError, match="pseudonym"):
        parse_human_attestation_pseudonym_keyring(raw, active_key_id=active)


def test_pseudonym_keyring_accepts_only_canonical_random_key_contract() -> None:
    raw = json.dumps(
        {
            PSEUDONYM_KEY_ID: _external_key(
                PSEUDONYM_KEYRING[PSEUDONYM_KEY_ID]
            )
        }
    )
    assert dict(
        parse_human_attestation_pseudonym_keyring(
            raw, active_key_id=PSEUDONYM_KEY_ID
        )
    ) == PSEUDONYM_KEYRING


@pytest.mark.parametrize(
    "key_id",
    [
        "hat-test-v1",
        "owner@example.test",
        "acct-00000000000000000000000000000001",
        "hatk_0123456789ABCDEF0123456789ABCDEF",
    ],
)
def test_store_rejects_descriptive_or_account_like_key_ids(key_id: str) -> None:
    with pytest.raises(ValueError, match="pseudonym"):
        HumanAttestationStore(
            InMemoryStateStore(),
            primary_tenant_id=TENANT,
            pseudonym_keyring={
                key_id: PSEUDONYM_KEYRING[PSEUDONYM_KEY_ID]
            },
            active_pseudonym_key_id=key_id,
        )


@pytest.mark.parametrize(
    "weak_key",
    [b"a" * 32, b"0123456789abcdef" * 2, bytes(range(32))],
)
def test_store_constructor_rejects_predictable_32_byte_keys(
    weak_key: bytes,
) -> None:
    with pytest.raises(ValueError, match="random"):
        HumanAttestationStore(
            InMemoryStateStore(),
            primary_tenant_id=TENANT,
            pseudonym_keyring={PSEUDONYM_KEY_ID: weak_key},
            active_pseudonym_key_id=PSEUDONYM_KEY_ID,
        )


def test_rotation_retains_old_verification_and_missing_historical_key_fails_closed() -> None:
    state = InMemoryStateStore()
    old_key = PSEUDONYM_KEYRING[PSEUDONYM_KEY_ID]
    new_key_id = PSEUDONYM_KEY_ID_V2
    new_key = hashlib.sha256(b"cas-human-attestation-test-key-v2").digest()
    old_store = _attestation_store(state)
    old_record = _create(
        old_store,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="legal_counsel",
        binding="a" * 64,
    )

    rotated = _attestation_store(
        state,
        keyring={PSEUDONYM_KEY_ID: old_key, new_key_id: new_key},
        active_key_id=new_key_id,
    )
    assert rotated.load(old_record.sha256, now=NOW).body == old_record.body
    new_record = _create(
        rotated,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="legal_counsel",
        binding="b" * 64,
    )
    assert new_record.payload["actor"]["pseudonym_key_id"] == new_key_id
    assert (
        new_record.payload["actor"]["account_subject"]
        != old_record.payload["actor"]["account_subject"]
    )

    missing_old = _attestation_store(
        state, keyring={new_key_id: new_key}, active_key_id=new_key_id
    )
    with pytest.raises(HumanAttestationUnavailable, match="verification key"):
        missing_old.load(old_record.sha256, now=NOW)
    assert missing_old.load(new_record.sha256, now=NOW).body == new_record.body


def test_private_identity_binding_tamper_and_legacy_v1_fail_closed() -> None:
    state = InMemoryStateStore()
    store = _attestation_store(state)
    created = _create(
        store,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="legal_counsel",
        binding="a" * 64,
    )
    binding = state.get(
        human_attestation_service.ATTESTATION_TENANT_ID,
        human_attestation_service.IDENTITY_BINDING_KIND,
        human_attestation_service._identity_binding_record_id(created.sha256),
    )
    assert binding is not None
    state.put(
        binding.with_payload(
            {**binding.payload, "actor_account_id": "acct-" + ("f" * 32)},
            now=NOW,
        ),
        expected_version=1,
    )
    with pytest.raises(HumanAttestationUnavailable, match="identity binding"):
        store.load(created.sha256, now=NOW)

    legacy_state = InMemoryStateStore()
    legacy_payload = {
        "schema_version": "cas_harness_human_attestation.v1",
        "record_type": "human_attestation",
        "action": "ATTEST",
        "purpose": "legal_approval",
        "gate": "legal_publication_approval",
        "environment": "public-production",
        "repository": "LittleHenderson/noetic-compass",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "evidence_binding_sha256": "a" * 64,
        "attested_at_utc": "2026-07-15T12:00:00Z",
        "actor": {
            "tenant_id_sha256": hashlib.sha256(TENANT.encode()).hexdigest(),
            "account_id_sha256": hashlib.sha256(
                ROLE_ACCOUNTS["legal_counsel"][1].encode()
            ).hexdigest(),
            "account_role": "owner",
            "attestation_role": "legal_counsel",
        },
        "supporting_attestations": [],
    }
    legacy_body = human_attestation_service._canonical_json_bytes(legacy_payload)
    legacy_digest = hashlib.sha256(legacy_body).hexdigest()
    content = LedgerRecord.new(
        tenant_id=human_attestation_service.ATTESTATION_TENANT_ID,
        kind=human_attestation_service.ATTESTATION_KIND,
        record_id=human_attestation_service._attestation_record_id(legacy_digest),
        payload=legacy_payload,
        source="human_attestation",
        trace_id=legacy_digest,
        now=NOW,
    )
    legacy_state.put(content, expected_version=0)
    legacy_status = LedgerRecord.new(
        tenant_id=human_attestation_service.ATTESTATION_TENANT_ID,
        kind=human_attestation_service.STATUS_KIND,
        record_id=human_attestation_service._status_record_id(legacy_digest),
        payload={
            "schema_version": "cas_harness_human_attestation_status.v1",
            "attestation_sha256": legacy_digest,
            "active": True,
            "revoked_at_utc": None,
            "revoked_by_account_id_sha256": None,
        },
        parent_ids=(content.record_id,),
        source="human_attestation",
        trace_id=legacy_digest,
        now=NOW,
    )
    legacy_state.put(legacy_status, expected_version=0)
    with pytest.raises(HumanAttestationUnavailable, match="keyed.*unavailable"):
        _attestation_store(legacy_state).load(legacy_digest, now=NOW)


def test_revocation_status_uses_keyed_subject_not_raw_or_unkeyed_account_hash() -> None:
    state = InMemoryStateStore()
    store = _attestation_store(state)
    created = _create(
        store,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="legal_counsel",
        binding="a" * 64,
    )
    account_id = ROLE_ACCOUNTS["legal_counsel"][1]
    store.revoke(
        created.sha256,
        actor_tenant_id=TENANT,
        actor_account_id=account_id,
        actor_account_role="owner",
        now=NOW,
    )
    status = state.get(
        human_attestation_service.ATTESTATION_TENANT_ID,
        human_attestation_service.STATUS_KIND,
        human_attestation_service._status_record_id(created.sha256),
    )
    assert status is not None
    serialized = repr(dict(status.payload))
    assert account_id not in serialized
    assert hashlib.sha256(account_id.encode()).hexdigest() not in serialized
    assert str(status.payload["revoked_by_account_subject"]).startswith(
        "hmac-sha256:"
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
    attestations = _attestation_store(state)
    evidence = _common(gate)
    if gate == "legal_publication_approval":
        evidence.update(
            documents=[{"kind": "legal", "content_sha256": "1" * 64}],
            claim_status_vocabulary=["OPEN", "ACCEPT"],
        )
    else:
        stamp = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
        machine_subject = {
            "schema_version": "cas_harness_claim_honesty_machine_subject.v1",
            "generated_at_utc": stamp,
            "scanned_surfaces": [
                {
                    "kind": "product_app",
                    "content_sha256": "2" * 64,
                    "verified_at_utc": stamp,
                }
            ],
            "findings": [],
        }
        machine_subject_sha256 = hashlib.sha256(
            json.dumps(
                machine_subject,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("ascii")
        ).hexdigest()
        evidence.update(
            artifact_sha256=machine_subject_sha256,
            machine_subject=machine_subject,
            machine_subject_sha256=machine_subject_sha256,
            boundaries={"research_scope_disclosed": True},
            claim_status_vocabulary=["OPEN", "ACCEPT"],
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

    if gate == "claim_honesty":
        tampered = deepcopy(evidence)
        tampered["machine_subject"]["scanned_surfaces"][0][
            "content_sha256"
        ] = "e" * 64
        tampered["machine_subject_sha256"] = hashlib.sha256(
            json.dumps(
                tampered["machine_subject"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("ascii")
        ).hexdigest()
        with pytest.raises(AcceptanceAuthorityInvalid, match="invalid or revoked"):
            authority.assert_human_attestations(gate, tampered, now=NOW)

        vocabulary_tamper = deepcopy(evidence)
        vocabulary_tamper["claim_status_vocabulary"] = ["OPEN", "ACCEPTED"]
        with pytest.raises(AcceptanceAuthorityInvalid, match="invalid or revoked"):
            authority.assert_human_attestations(
                gate, vocabulary_tamper, now=NOW
            )

        artifact_tamper = deepcopy(evidence)
        artifact_tamper["artifact_sha256"] = "e" * 64
        with pytest.raises(AcceptanceAuthorityInvalid, match="invalid or revoked"):
            authority.assert_human_attestations(
                gate, artifact_tamper, now=NOW
            )

    evidence["approvals"][0]["approval_sha256"] = "f" * 64
    with pytest.raises(AcceptanceAuthorityInvalid, match="invalid or revoked"):
        authority.assert_human_attestations(gate, evidence, now=NOW)


def test_claim_actual_attestations_cannot_precede_machine_subject_generation() -> None:
    state = InMemoryStateStore()
    attestations = _attestation_store(state)
    event = NOW - timedelta(minutes=10)
    verified = NOW - timedelta(minutes=8)
    approved = NOW - timedelta(minutes=6)
    generated = NOW - timedelta(minutes=5)
    machine_subject = {
        "schema_version": "cas_harness_claim_honesty_machine_subject.v1",
        "generated_at_utc": generated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scanned_surfaces": [
            {
                "kind": "product_app",
                "content_sha256": "2" * 64,
                "verified_at_utc": verified.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        ],
        "findings": [],
    }
    machine_subject_sha256 = hashlib.sha256(
        json.dumps(
            machine_subject,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
    ).hexdigest()
    evidence = _common("claim_honesty")
    evidence.update({
        "event_at_utc": event.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observed_at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_sha256": machine_subject_sha256,
        "machine_subject": machine_subject,
        "machine_subject_sha256": machine_subject_sha256,
        "boundaries": {"research_scope_disclosed": True},
        "claim_status_vocabulary": ["OPEN", "ACCEPT"],
    })
    binding = canonical_evidence_binding_sha256("claim_honesty", evidence)
    records = [
        _create(
            attestations,
            purpose="claim_approval",
            gate="claim_honesty",
            role=role,
            binding=binding,
            now=approved,
        )
        for role in ("legal_owner", "product_owner", "research_owner")
    ]
    evidence["approvals"] = [
        {
            "role": role,
            "approval_artifact_uri": record.uri,
            "approval_sha256": record.sha256,
            "approved_at_utc": record.payload["attested_at_utc"],
        }
        for role, record in zip(
            ("legal_owner", "product_owner", "research_owner"),
            records,
            strict=True,
        )
    ]
    authority = CustomerProductionAcceptanceAuthorityStore(
        state, human_attestation_store=attestations
    )

    with pytest.raises(
        AcceptanceAuthorityInvalid, match="invalid or revoked attestation"
    ):
        authority.assert_human_attestations(
            "claim_honesty", evidence, now=NOW
        )


def test_legal_approvals_reject_two_roles_from_the_same_authenticated_account() -> None:
    state = InMemoryStateStore()
    attestations = _attestation_store(state)
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


def test_distinct_account_control_survives_pseudonym_key_rotation() -> None:
    state = InMemoryStateStore()
    old_key = PSEUDONYM_KEYRING[PSEUDONYM_KEY_ID]
    new_key = hashlib.sha256(b"cas-human-attestation-test-key-v2").digest()
    old_store = _attestation_store(state)
    evidence = _common("legal_publication_approval")
    evidence.update(
        documents=[{"kind": "legal", "content_sha256": "1" * 64}],
        claim_status_vocabulary=["OPEN", "ACCEPT"],
    )
    binding = canonical_evidence_binding_sha256(
        "legal_publication_approval", evidence
    )
    legal = _create(
        old_store,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="legal_counsel",
        binding=binding,
    )

    rotated = _attestation_store(
        state,
        keyring={
            PSEUDONYM_KEY_ID: old_key,
            PSEUDONYM_KEY_ID_V2: new_key,
        },
        active_key_id=PSEUDONYM_KEY_ID_V2,
    )
    product = rotated.create(
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
        rotated,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="privacy_owner",
        binding=binding,
    )
    assert (
        legal.payload["actor"]["account_subject"]
        != product.payload["actor"]["account_subject"]
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
        state, human_attestation_store=rotated
    )
    with pytest.raises(AcceptanceAuthorityInvalid, match="invalid or revoked"):
        authority.assert_human_attestations(
            "legal_publication_approval", evidence, now=NOW
        )


def test_incident_and_tabletop_aggregates_require_every_individual_actor() -> None:
    state = InMemoryStateStore()
    attestations = _attestation_store(state)
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
    attestations = _attestation_store(state)
    evidence = _common("release_decision")
    evidence.update(
        status="ACCEPT",
        approved_at_utc="2026-07-15T12:00:00Z",
        approver_roles=["legal_owner", "operations_owner", "product_owner", "security_owner"],
        evidence_hashes=_release_evidence_hashes(),
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


def test_different_valid_support_graph_cannot_reuse_private_content_binding() -> None:
    state = InMemoryStateStore()
    attestations = _attestation_store(state)

    def closure_graph(stamp: datetime) -> HumanAttestation:
        children = {
            role: _create(
                attestations,
                purpose="incident_closure",
                gate="incident_tabletop",
                role=role,
                binding="a" * 64,
                now=stamp,
            )
            for role in ("incident_commander", "operations", "security")
        }
        return _create(
            attestations,
            purpose="incident_postmortem",
            gate="incident_tabletop",
            role="incident_commander",
            binding="a" * 64,
            supports=[
                _reference(record, role) for role, record in children.items()
            ],
            now=stamp + timedelta(seconds=1),
        )

    first = closure_graph(NOW)
    second = closure_graph(NOW + timedelta(seconds=2))
    assert first.sha256 != second.sha256
    assert (
        first.payload["supporting_attestations"]
        != second.payload["supporting_attestations"]
    )

    first_identity = state.get(
        human_attestation_service.ATTESTATION_TENANT_ID,
        human_attestation_service.IDENTITY_BINDING_KIND,
        human_attestation_service._identity_binding_record_id(first.sha256),
    )
    second_identity = state.get(
        human_attestation_service.ATTESTATION_TENANT_ID,
        human_attestation_service.IDENTITY_BINDING_KIND,
        human_attestation_service._identity_binding_record_id(second.sha256),
    )
    second_status = state.get(
        human_attestation_service.ATTESTATION_TENANT_ID,
        human_attestation_service.STATUS_KIND,
        human_attestation_service._status_record_id(second.sha256),
    )
    assert first_identity is not None
    assert second_identity is not None
    assert second_status is not None
    reused_binding = str(first_identity.payload["content_binding_hmac"])

    # Simulate a storage attacker replacing both private pins while preserving
    # their version/envelope metadata. Recomputing from the canonical public
    # digest must still reject the otherwise valid alternate support graph.
    identity_key = (
        second_identity.tenant_id,
        second_identity.kind,
        second_identity.record_id,
    )
    status_key = (
        second_status.tenant_id,
        second_status.kind,
        second_status.record_id,
    )
    state._records[identity_key] = replace(  # noqa: SLF001 - hostile-store probe
        second_identity,
        payload={
            **second_identity.payload,
            "content_binding_hmac": reused_binding,
        },
    )
    state._records[status_key] = replace(  # noqa: SLF001 - hostile-store probe
        second_status,
        payload={
            **second_status.payload,
            "content_binding_hmac": reused_binding,
        },
    )
    with pytest.raises(
        HumanAttestationUnavailable, match="private content binding"
    ):
        attestations.load(second.sha256, now=NOW + timedelta(seconds=4))


def test_release_aggregate_rejects_a_child_created_before_the_evidence_window() -> None:
    state = InMemoryStateStore()
    attestations = _attestation_store(state)
    evidence = _common("release_decision")
    evidence.update(
        status="ACCEPT",
        approved_at_utc="2026-07-15T12:00:00Z",
        approver_roles=["legal_owner", "operations_owner", "product_owner", "security_owner"],
        evidence_hashes=_release_evidence_hashes(),
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
    store = _attestation_store(state)
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
    first = _attestation_store(first_backend)
    created = _create(
        first,
        purpose="legal_approval",
        gate="legal_publication_approval",
        role="legal_counsel",
        binding="a" * 64,
    )
    first_backend.close()

    second_backend = SqliteStateStore(path)
    second = _attestation_store(second_backend)
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
    third = _attestation_store(third_backend)
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
    app.state.human_attestation_store = _attestation_store(backend)
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
