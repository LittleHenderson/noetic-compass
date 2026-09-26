"""Hostile tests for short-lived acceptance publication authorization."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.acceptance_authority_contract import (
    ACCEPTANCE_AUTHORITY_PATH_BY_GATE,
    acceptance_authority_url,
    acceptance_publication_authorization_url,
)
from api.config import settings
from api.middleware.auth import (
    JWTAuthMiddleware,
    is_public_acceptance_publication_authorization_request,
)
from api.middleware.rate_limit import RateLimitMiddleware
from api.routes import acceptance_publication_authorizations, auth
from api.services.acceptance_publication_authorizations import (
    ACTION,
    AUTHORIZATION_KIND,
    AUTHORIZATION_TENANT_ID,
    AUTHORIZATION_TTL_SECONDS,
    OPERATION,
    RECORD_TYPE,
    AcceptancePublicationAuthorizationInvalid,
    AcceptancePublicationAuthorizationNotFound,
    AcceptancePublicationAuthorizationStore,
    AcceptancePublicationAuthorizationUnavailable,
    validate_publication_authorization_reference,
)
from api.services.accounts.store import AccountStore
from api.services.customer_production_acceptance_authority import (
    AcceptanceAuthorityAuthorizationInvalid,
    AcceptanceAuthorityAuthorizationUnavailable,
    AcceptanceAuthorityInvalid,
    CustomerProductionAcceptanceAuthorityStore,
    RELEASE_DECISION_EVIDENCE_HASH_GATES,
    RELEASE_DECISION_EVIDENCE_SCHEMA_VERSION,
    canonicalize_acceptance_evidence,
)
from api.services.customer_production_pseudonyms import (
    PUBLICATION_ACCOUNT_DOMAIN,
    PUBLICATION_TENANT_DOMAIN,
    CustomerProductionPseudonymizer,
)
from api.services.human_attestations import PUBLIC_HUMAN_ASSURANCE_BOUNDARY
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.production.worm_writes import RetentionPolicy
from api.services.sessions import SessionStore
from tests.acceptance_attestation_test_support import (
    materialize_human_attestations,
)
import scripts.publish_customer_production_acceptance_authority as publisher


NOW = datetime(2026, 7, 15, 18, 0, tzinfo=UTC)
MASTER = "a" * 40
DEPLOY = "dep-authorizationtest001"
EVIDENCE_SHA = hashlib.sha256(b"evidence").hexdigest()
PREVIOUS_SHA = hashlib.sha256(b"previous").hexdigest()
ACTOR_ACCOUNT_ID = "acct-0123456789abcdef0123456789abcdef"
OWNER_CREDENTIAL = "casak_0123456789abcdefghijklmnopqrstuvwxyzABCDEFG"
MEMBER_CREDENTIAL = "casak_ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210abcdefgh"
OTHER_OWNER_CREDENTIAL = "casak_otherowner0123456789abcdefghijklmnopqrstuvwxyzABCD"
PSEUDONYM_KEY_ID = "cpk_0123456789abcdef0123456789abcdef"
PSEUDONYMIZER = CustomerProductionPseudonymizer(
    {PSEUDONYM_KEY_ID: hashlib.sha256(b"publication-pseudonym-test-key").digest()},
    active_key_id=PSEUDONYM_KEY_ID,
)


def _create(
    store: AcceptancePublicationAuthorizationStore,
    **overrides: object,
):
    values: dict[str, object] = {
        "actor_tenant_id": "primary",
        "actor_account_id": ACTOR_ACCOUNT_ID,
        "actor_role": "owner",
        "gate": "legal_publication_approval",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "evidence_sha256": EVIDENCE_SHA,
        "expected_head_version": 0,
        "expected_previous_evidence_sha256": None,
        "reason": "authorized_publication",
        "now": NOW,
    }
    values.update(overrides)
    return store.create(**values)  # type: ignore[arg-type]


def _request_body(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "record_type": "authority_operation",
        "action": "AUTHORIZE",
        "gate": "legal_publication_approval",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "evidence_sha256": EVIDENCE_SHA,
        "expected_head_version": 0,
        "expected_previous_evidence_sha256": None,
        "reason": "authorized_publication",
    }
    value.update(overrides)
    return value


def _legal_evidence(now: datetime, *, evidence_master: str = MASTER) -> dict[str, object]:
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": "cas_harness_customer_production_gate_evidence.v3",
        "gate": "legal_publication_approval",
        "environment": "public-production",
        "repository": "LittleHenderson/noetic-compass",
        "master_head_sha": evidence_master,
        "deploy_id": DEPLOY,
        "event_at_utc": stamp,
        "observed_at_utc": stamp,
        "artifact_uri": acceptance_authority_url("legal_publication_approval"),
        "artifact_sha256": hashlib.sha256(b"independent-legal-artifact").hexdigest(),
        "human_assurance_boundary": dict(PUBLIC_HUMAN_ASSURANCE_BOUNDARY),
        "public_base_url": "https://cascompass.ai",
        "documents": [
            {
                "kind": kind,
                "url": f"https://cascompass.ai/{kind}",
                "http_status": 200,
                "content_sha256": hashlib.sha256(kind.encode()).hexdigest(),
                "published_at_utc": stamp,
                "verified_at_utc": stamp,
            }
            for kind in ("legal", "privacy", "terms")
        ],
        "approvals": [
            {
                "role": role,
                "approval_artifact_uri": (
                    f"{publisher.PRODUCTION_API_ORIGIN}/internal/approvals/{role}"
                ),
                "approval_sha256": hashlib.sha256(role.encode()).hexdigest(),
                "approved_at_utc": stamp,
            }
            for role in ("legal_counsel", "privacy_owner", "product_owner")
        ],
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


def _base_evidence(gate: str, now: datetime) -> dict[str, object]:
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": (
            RELEASE_DECISION_EVIDENCE_SCHEMA_VERSION
            if gate == "release_decision"
            else "cas_harness_customer_production_gate_evidence.v3"
        ),
        "gate": gate,
        "environment": "public-production",
        "repository": "LittleHenderson/noetic-compass",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "event_at_utc": stamp,
        "observed_at_utc": stamp,
        "artifact_uri": acceptance_authority_url(gate),
        "artifact_sha256": hashlib.sha256(f"{gate}-artifact".encode()).hexdigest(),
        "human_assurance_boundary": dict(PUBLIC_HUMAN_ASSURANCE_BOUNDARY),
    }


def _claim_evidence(now: datetime) -> dict[str, object]:
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    evidence = _base_evidence("claim_honesty", now)
    surfaces = {
        "product_app": "https://atlas.noeticcompass.com",
        "audit_console": "https://atlas.noeticcompass.com/audit-console",
        "landing": "https://cascompass.ai",
        "legal": "https://cascompass.ai/legal",
        "privacy": "https://cascompass.ai/privacy",
        "terms": "https://cascompass.ai/terms",
    }
    machine_subject = {
        "schema_version": "cas_harness_claim_honesty_machine_subject.v1",
        "generated_at_utc": stamp,
        "scanner": {
            "ruleset_version": "cas_harness_claim_honesty_rules.v1",
            "collector_sha256": hashlib.sha256(b"claim-collector").hexdigest(),
            "request_method": "GET",
            "redirects_allowed": False,
            "maximum_response_bytes": 1_000_000,
            "javascript_executed": False,
        },
        "scanned_surfaces": [
                {
                    "kind": kind,
                    "url": url,
                    "http_status": 200,
                    "final_url_matches_requested": True,
                    "content_type": "text/html; charset=utf-8",
                    "byte_length": 512,
                    "content_sha256": hashlib.sha256(kind.encode()).hexdigest(),
                    "verified_at_utc": stamp,
                    "coverage_established": True,
                    "visibility_basis": (
                        "prerendered_same_route_application_mount"
                        if kind in {"product_app", "audit_console"}
                        else "static_same_route_html"
                    ),
                    "visible_text_sha256": hashlib.sha256(
                        f"visible-{kind}".encode()
                    ).hexdigest(),
                    "visible_text_characters": 256,
                    "visible_word_count": 32,
                    "client_rendered_shell_detected": False,
                    "prerendered_application_mount_detected": kind
                    in {"product_app", "audit_console"},
                    "prerender_contract_matches_requested_route": kind
                    in {"product_app", "audit_console"},
                    "route_identity_established": True,
                    "error_count": 0,
                    "errors_sha256": hashlib.sha256(b"[]").hexdigest(),
                }
                for kind, url in surfaces.items()
            ],
        "scan": {
            "misleading_claim_count": 0,
            "unsupported_compliance_claim_count": 0,
            "unsupported_universality_claim_count": 0,
            "unsupported_ip_claim_count": 0,
            "status_vocabulary_exact": True,
            "scanned_surface_count": 6,
            "covered_surface_count": 6,
            "finding_count": 0,
            "coverage_complete": True,
            "machine_scan_passed": True,
        },
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
        {
            "machine_subject": machine_subject,
            "machine_subject_sha256": machine_subject_sha256,
            "artifact_sha256": machine_subject_sha256,
            "boundaries": {
                "research_scope_disclosed": True,
                "research_accept_not_product_accept": True,
                "worm_retention_not_verdict_upgrade": True,
                "flag_for_human_review_not_accept": True,
                "compliance_certification_claims_absent": True,
            },
            "claim_status_vocabulary": [
                "ACCEPT",
                "FLAG_FOR_HUMAN_REVIEW",
                "LICENSED",
                "NOT LICENSED",
                "OPEN",
                "present",
                "unavailable",
            ],
            "approvals": [
                {
                    "role": role,
                    "approval_artifact_uri": (
                        f"{publisher.PRODUCTION_API_ORIGIN}/internal/approvals/{role}"
                    ),
                    "approval_sha256": hashlib.sha256(role.encode()).hexdigest(),
                    "approved_at_utc": stamp,
                }
                for role in ("legal_owner", "product_owner", "research_owner")
            ],
        }
    )
    return evidence


def _release_evidence(now: datetime) -> dict[str, object]:
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    evidence = _base_evidence("release_decision", now)
    evidence.update(
        {
            "status": "ACCEPT",
            "approved_at_utc": stamp,
            "approver_roles": [
                "legal_owner",
                "operations_owner",
                "product_owner",
                "security_owner",
            ],
            "evidence_hashes": {
                gate: hashlib.sha256(f"required-gate:{gate}".encode()).hexdigest()
                for gate in RELEASE_DECISION_EVIDENCE_HASH_GATES
            },
            "decision_record_uri": (
                f"{publisher.PRODUCTION_API_ORIGIN}/internal/decisions/release"
            ),
            "decision_record_sha256": hashlib.sha256(b"release").hexdigest(),
        }
    )
    return evidence


def _incident_evidence(now: datetime) -> dict[str, object]:
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    evidence = _base_evidence("incident_tabletop", now)
    evidence.update(
        {
            "api_base_url": publisher.PRODUCTION_API_ORIGIN,
            "service_id": "i-0bd0a082507a51ae3",
            "incident": {
                "record_id": "IR-2026-07-15-001",
                "status": "CLOSED",
                "closed_at_utc": stamp,
                "open_actions": 0,
                "postmortem_uri": (
                    f"{publisher.PRODUCTION_API_ORIGIN}/internal/incidents/IR-2026-07-15-001"
                ),
                "postmortem_sha256": hashlib.sha256(b"postmortem").hexdigest(),
                "credential_rotation_complete": True,
                "recovery_verified": True,
            },
            "tabletop": {
                "tabletop_id": "tabletop-20260715",
                "completed_at_utc": stamp,
                "participant_roles": [
                    "incident_commander",
                    "legal",
                    "operations",
                    "security",
                    "support",
                ],
                "scenarios": [
                    "account_compromise",
                    "billing_webhook_failure",
                    "data_subject_request",
                    "worker_outage",
                    "worm_authentication_failure",
                ],
                "open_actions": 0,
                "evidence_uri": (
                    f"{publisher.PRODUCTION_API_ORIGIN}/internal/tabletops/tabletop-20260715"
                ),
                "evidence_sha256": hashlib.sha256(b"tabletop").hexdigest(),
            },
        }
    )
    return evidence


def test_human_attestation_graphs_cannot_predate_the_facts_they_approve() -> None:
    observed = NOW + timedelta(minutes=10)
    incident_closed = NOW + timedelta(minutes=5)
    tabletop_completed = NOW + timedelta(minutes=6)
    release_approved = NOW + timedelta(minutes=5)

    def incident() -> dict[str, object]:
        evidence = _incident_evidence(NOW)
        evidence["observed_at_utc"] = observed.strftime("%Y-%m-%dT%H:%M:%SZ")
        evidence["incident"]["closed_at_utc"] = incident_closed.strftime(  # type: ignore[index]
            "%Y-%m-%dT%H:%M:%SZ"
        )
        evidence["tabletop"]["completed_at_utc"] = tabletop_completed.strftime(  # type: ignore[index]
            "%Y-%m-%dT%H:%M:%SZ"
        )
        return evidence

    def release() -> dict[str, object]:
        evidence = _release_evidence(NOW)
        evidence["observed_at_utc"] = observed.strftime("%Y-%m-%dT%H:%M:%SZ")
        evidence["approved_at_utc"] = release_approved.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        return evidence

    before_incident = incident_closed - timedelta(minutes=1)
    before_tabletop = tabletop_completed - timedelta(minutes=1)
    before_release = release_approved - timedelta(minutes=1)
    incident_closure_roles = ("incident_commander", "operations", "security")
    tabletop_roles = (
        "incident_commander",
        "legal",
        "operations",
        "security",
        "support",
    )
    release_roles = (
        "legal_owner",
        "operations_owner",
        "product_owner",
        "security_owner",
    )
    cases = (
        (
            "incident closure support",
            incident,
            {("incident_closure", "operations"): before_incident},
        ),
        (
            "incident postmortem aggregate",
            incident,
            {
                **{
                    ("incident_closure", role): before_incident
                    for role in incident_closure_roles
                },
                ("incident_postmortem", "incident_commander"): before_incident,
            },
        ),
        (
            "tabletop completion support",
            incident,
            {("tabletop_completion", "support"): before_tabletop},
        ),
        (
            "tabletop evidence aggregate",
            incident,
            {
                **{
                    ("tabletop_completion", role): before_tabletop
                    for role in tabletop_roles
                },
                ("tabletop_evidence", "incident_commander"): before_tabletop,
            },
        ),
        (
            "release approval support",
            release,
            {("release_approval", "security_owner"): before_release},
        ),
        (
            "release decision aggregate",
            release,
            {
                **{
                    ("release_approval", role): before_release
                    for role in release_roles
                },
                ("release_decision_record", "product_owner"): before_release,
            },
        ),
    )

    for label, evidence_factory, overrides in cases:
        backend = InMemoryStateStore()
        evidence = evidence_factory()
        gate = str(evidence["gate"])
        canonicalize_acceptance_evidence(gate, evidence, now=observed)
        attestations = materialize_human_attestations(
            backend,
            evidence,
            attested_at_overrides=overrides,
        )
        authority = CustomerProductionAcceptanceAuthorityStore(
            backend, human_attestation_store=attestations
        )
        with pytest.raises(
            AcceptanceAuthorityInvalid,
            match="invalid or revoked attestation",
        ):
            authority.assert_human_attestations(gate, evidence, now=observed)


@pytest.mark.parametrize(
    ("gate", "evidence_factory", "container", "field"),
    [
        ("legal_publication_approval", _legal_evidence, ("approvals", 0), "approval_artifact_uri"),
        ("claim_honesty", _claim_evidence, ("approvals", 0), "approval_artifact_uri"),
        ("release_decision", _release_evidence, (), "decision_record_uri"),
        ("incident_tabletop", _incident_evidence, ("incident",), "postmortem_uri"),
        ("incident_tabletop", _incident_evidence, ("tabletop",), "evidence_uri"),
    ],
)
def test_publication_authorization_cannot_masquerade_as_gate_evidence(
    gate: str,
    evidence_factory,
    container: tuple[object, ...],
    field: str,
) -> None:
    evidence = evidence_factory(NOW)
    target: object = evidence
    for part in container:
        target = target[part]  # type: ignore[index]
    assert isinstance(target, dict)
    target[field] = acceptance_publication_authorization_url("b" * 64)

    with pytest.raises(
        AcceptanceAuthorityInvalid,
        match="must not use a publication authorization as gate evidence",
    ):
        canonicalize_acceptance_evidence(gate, evidence, now=NOW)


def test_create_is_canonical_content_addressed_create_only_and_idempotent() -> None:
    backend = InMemoryStateStore()
    store = AcceptancePublicationAuthorizationStore(
        backend, primary_tenant_id="primary", pseudonymizer=PSEUDONYMIZER
    )

    first = _create(store)
    second = _create(store)

    assert first == second
    assert hashlib.sha256(first.body).hexdigest() == first.sha256
    assert first.uri == acceptance_publication_authorization_url(first.sha256)
    assert first.body == json.dumps(
        first.payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    assert first.payload["record_type"] == RECORD_TYPE
    assert first.payload["action"] == ACTION
    assert first.payload["operation"] == OPERATION
    assert first.payload["authorized_by"] == {
        "pseudonymization_scheme": PSEUDONYMIZER.scheme,
        "pseudonym_key_id": PSEUDONYM_KEY_ID,
        "tenant_subject": PSEUDONYMIZER.subject(
            domain=PUBLICATION_TENANT_DOMAIN,
            tenant_scope="primary",
            value="primary",
        ),
        "account_subject": PSEUDONYMIZER.subject(
            domain=PUBLICATION_ACCOUNT_DOMAIN,
            tenant_scope="primary",
            value=ACTOR_ACCOUNT_ID,
        ),
        "role": "owner",
    }
    assert ACTOR_ACCOUNT_ID not in first.body.decode("ascii")
    assert '"tenant_id":"primary"' not in first.body.decode("ascii")
    rows = backend.list(AUTHORIZATION_TENANT_ID, AUTHORIZATION_KIND)
    assert len(rows) == 1
    assert rows[0].version == 1


def test_fixed_ttl_is_live_before_boundary_and_absent_at_boundary() -> None:
    store = AcceptancePublicationAuthorizationStore(
        InMemoryStateStore(),
        primary_tenant_id="primary",
        pseudonymizer=PSEUDONYMIZER,
    )
    created = _create(store)
    assert store.load(
        created.sha256,
        now=NOW + timedelta(seconds=AUTHORIZATION_TTL_SECONDS - 1),
    ).sha256 == created.sha256
    with pytest.raises(AcceptancePublicationAuthorizationNotFound, match="expired"):
        store.load(
            created.sha256,
            now=NOW + timedelta(seconds=AUTHORIZATION_TTL_SECONDS),
        )


def test_create_only_record_survives_sqlite_restart(tmp_path: Path) -> None:
    path = tmp_path / "publication-authorizations.db"
    first_backend = SqliteStateStore(path)
    first_store = AcceptancePublicationAuthorizationStore(
        first_backend,
        primary_tenant_id="primary",
        pseudonymizer=PSEUDONYMIZER,
    )
    created = _create(first_store)
    first_backend.close()

    second_backend = SqliteStateStore(path)
    second_store = AcceptancePublicationAuthorizationStore(
        second_backend,
        primary_tenant_id="primary",
        pseudonymizer=PSEUDONYMIZER,
    )
    loaded = second_store.load(created.sha256, now=NOW)
    assert loaded.body == created.body
    assert loaded.sha256 == created.sha256
    second_backend.close()


@pytest.mark.parametrize(
    "overrides",
    [
        {"actor_role": "admin"},
        {"actor_tenant_id": "other"},
        {"actor_account_id": ""},
        {"gate": "future_gate"},
        {"master_head_sha": "A" * 40},
        {"deploy_id": "service-1"},
        {"evidence_sha256": "0" * 63},
        {"expected_head_version": True},
        {"expected_previous_evidence_sha256": PREVIOUS_SHA},
        {"reason": "legal_approved"},
    ],
)
def test_create_rejects_hostile_actor_or_binding(overrides: dict[str, object]) -> None:
    backend = InMemoryStateStore()
    store = AcceptancePublicationAuthorizationStore(
        backend, primary_tenant_id="primary", pseudonymizer=PSEUDONYMIZER
    )
    with pytest.raises(AcceptancePublicationAuthorizationInvalid):
        _create(store, **overrides)
    assert backend.list(AUTHORIZATION_TENANT_ID, AUTHORIZATION_KIND) == ()


def test_replacement_requires_exact_previous_sha() -> None:
    store = AcceptancePublicationAuthorizationStore(
        InMemoryStateStore(),
        primary_tenant_id="primary",
        pseudonymizer=PSEUDONYMIZER,
    )
    with pytest.raises(AcceptancePublicationAuthorizationInvalid, match="predecessor"):
        _create(store, expected_head_version=2)
    created = _create(
        store,
        expected_head_version=2,
        expected_previous_evidence_sha256=PREVIOUS_SHA,
    )
    assert created.payload["expected_previous_evidence_sha256"] == PREVIOUS_SHA


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.com/internal/acceptance-authorizations/{digest}",
        (
            f"{publisher.PRODUCTION_API_ORIGIN}/internal/"
            "acceptance-authorizations/not-a-digest"
        ),
        (
            f"{publisher.PRODUCTION_API_ORIGIN}/internal/"
            "acceptance-authorizations/{digest}?next=https://example.com"
        ),
        (
            f"{publisher.PRODUCTION_API_ORIGIN}/internal/"
            "acceptance-authorizations/{upper}"
        ),
        (
            f"{publisher.PRODUCTION_API_ORIGIN}:443/internal/"
            "acceptance-authorizations/{digest}"
        ),
    ],
)
def test_reference_parser_rejects_ssrf_dummy_query_case_and_port(uri: str) -> None:
    digest = "a" * 64
    with pytest.raises(AcceptancePublicationAuthorizationInvalid):
        validate_publication_authorization_reference(
            uri.format(digest=digest, upper=digest.upper()), digest
        )


def test_reference_parser_requires_path_hash_to_equal_supplied_hash() -> None:
    with pytest.raises(AcceptancePublicationAuthorizationInvalid):
        validate_publication_authorization_reference(
            acceptance_publication_authorization_url("a" * 64), "b" * 64
        )


@pytest.mark.parametrize(
    ("field", "mismatch"),
    [
        ("gate", "support_crm"),
        ("master_head_sha", "b" * 40),
        ("deploy_id", "dep-other001"),
        ("evidence_sha256", "b" * 64),
        ("expected_head_version", 1),
        ("reason", "operator_safety_action"),
    ],
)
def test_local_match_rejects_every_exact_binding(
    field: str, mismatch: object
) -> None:
    store = AcceptancePublicationAuthorizationStore(
        InMemoryStateStore(),
        primary_tenant_id="primary",
        pseudonymizer=PSEUDONYMIZER,
    )
    created = _create(store)
    bindings: dict[str, object] = {
        "authorization_artifact_uri": created.uri,
        "authorization_artifact_sha256": created.sha256,
        "gate": "legal_publication_approval",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "evidence_sha256": EVIDENCE_SHA,
        "expected_head_version": 0,
        "expected_previous_evidence_sha256": None,
        "reason": "authorized_publication",
        "now": NOW,
    }
    bindings[field] = mismatch
    if field == "expected_head_version":
        bindings["expected_previous_evidence_sha256"] = PREVIOUS_SHA
    with pytest.raises(AcceptancePublicationAuthorizationInvalid):
        store.assert_matches(**bindings)  # type: ignore[arg-type]


def test_updated_or_tampered_record_fails_closed() -> None:
    backend = InMemoryStateStore()
    store = AcceptancePublicationAuthorizationStore(
        backend, primary_tenant_id="primary", pseudonymizer=PSEUDONYMIZER
    )
    created = _create(store)
    record = backend.get(
        AUTHORIZATION_TENANT_ID, AUTHORIZATION_KIND, f"acceptance-publication-authorization-{created.sha256}"
    )
    assert record is not None
    backend.put(record.with_payload(record.payload), expected_version=1)

    with pytest.raises(AcceptancePublicationAuthorizationUnavailable, match="traceability"):
        store.load(created.sha256, now=NOW)


class _NoWriteImmutableBackend:
    def __init__(self) -> None:
        self.calls = 0

    def assert_ready(self, *, expected: RetentionPolicy) -> None:
        self.calls += 1

    def put_immutable(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        raise AssertionError("authorization must be checked before WORM write")

    def get_immutable(self, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("no revision should exist")

    def object_url(self, key: str, *, version_id: str | None = None) -> str:
        return f"s3://test/{key}?versionId={version_id}"


def test_authority_publish_requires_local_exact_record_before_any_write() -> None:
    now = NOW
    backend = InMemoryStateStore()
    evidence = _legal_evidence(now)
    attestations = materialize_human_attestations(backend, evidence)
    digest = hashlib.sha256(
        canonicalize_acceptance_evidence(
            "legal_publication_approval", evidence, now=now
        )
    ).hexdigest()
    authorizations = AcceptancePublicationAuthorizationStore(
        backend, primary_tenant_id="primary", pseudonymizer=PSEUDONYMIZER
    )
    worm = _NoWriteImmutableBackend()
    authority = CustomerProductionAcceptanceAuthorityStore(
        backend,
        human_attestation_store=attestations,
        publication_authorization_store=authorizations,
        immutable_backend=worm,
        retention_policy=RetentionPolicy(mode="GOVERNANCE", retention_days=31),
    )
    missing_digest = "f" * 64

    with pytest.raises(AcceptanceAuthorityInvalid, match="absent"):
        authority.publish(
            "legal_publication_approval",
            evidence,
            expected_head_version=0,
            expected_previous_sha256=None,
            authorization_artifact_uri=acceptance_publication_authorization_url(
                missing_digest
            ),
            authorization_artifact_sha256=missing_digest,
            operation_reason="authorized_publication",
            now=now,
        )

    assert worm.calls == 0
    assert backend.list(
        "cas-harness-customer-production",
        "customer_production_acceptance_authority_revision",
    ) == ()
    assert backend.list(
        "cas-harness-customer-production",
        "customer_production_acceptance_authority_operation",
    ) == ()
    assert backend.list(
        "cas-harness-customer-production",
        "customer_production_acceptance_authority_head",
    ) == ()
    assert digest != missing_digest


def test_authority_publish_binds_exact_record_but_deactivation_stays_available() -> None:
    now = NOW
    backend = InMemoryStateStore()
    evidence = _legal_evidence(now)
    attestations = materialize_human_attestations(backend, evidence)
    digest = hashlib.sha256(
        canonicalize_acceptance_evidence(
            "legal_publication_approval", evidence, now=now
        )
    ).hexdigest()
    authorizations = AcceptancePublicationAuthorizationStore(
        backend, primary_tenant_id="primary", pseudonymizer=PSEUDONYMIZER
    )
    authorization = _create(authorizations, evidence_sha256=digest)
    authority = CustomerProductionAcceptanceAuthorityStore(
        backend,
        human_attestation_store=attestations,
        publication_authorization_store=authorizations,
    )

    published = authority.publish(
        "legal_publication_approval",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        authorization_artifact_uri=authorization.uri,
        authorization_artifact_sha256=authorization.sha256,
        operation_reason="authorized_publication",
        now=now,
    )

    assert published.sha256 == digest
    operation = backend.get(
        "cas-harness-customer-production",
        "customer_production_acceptance_authority_operation",
        published.operation_record_id,
    )
    assert operation is not None
    assert operation.payload["authorization"] == {
        "artifact_uri": authorization.uri,
        "artifact_sha256": authorization.sha256,
        "reason": "authorized_publication",
    }

    deactivated = authority.deactivate(
        "legal_publication_approval",
        expected_head_version=published.head_version,
        expected_evidence_sha256=published.sha256,
        authorization_artifact_uri=(
            "https://cascompass.ai/internal/incidents/operator-safety-1"
        ),
        authorization_artifact_sha256=hashlib.sha256(
            b"operator-safety-1"
        ).hexdigest(),
        operation_reason="operator_safety_action",
        now=now + timedelta(seconds=1),
    )
    assert deactivated.already_inactive is False
    assert deactivated.head_version == published.head_version + 1
    head = authority.current_head("legal_publication_approval")
    assert head is not None and head.active is False


@pytest.fixture
def account_route_client(monkeypatch: pytest.MonkeyPatch):
    backend = InMemoryStateStore()
    account_store = AccountStore(
        backend, credential_pepper="authorization-test-pepper-at-least-32-bytes"
    )
    session_store = SessionStore(backend)
    authorization_store = AcceptancePublicationAuthorizationStore(
        backend, primary_tenant_id="primary", pseudonymizer=PSEUDONYMIZER
    )
    owner = account_store.bootstrap_owner(
        email_or_username="owner@example.test",
        tenant_id="primary",
        api_credential=OWNER_CREDENTIAL,
    )
    member_invite = account_store.create_invite(
        role="member", tenant_id="primary", code="member-authz-code"
    )
    member = account_store.redeem_invite(
        code=member_invite.code,
        email_or_username="member@example.test",
        api_credential=MEMBER_CREDENTIAL,
    )
    other_invite = account_store.create_invite(
        role="owner", tenant_id="other", code="other-owner-authz-code"
    )
    other_owner = account_store.redeem_invite(
        code=other_invite.code,
        email_or_username="other-owner@example.test",
        api_credential=OTHER_OWNER_CREDENTIAL,
    )
    app = FastAPI()
    app.state.account_store = account_store
    app.state.session_store = session_store
    app.state.acceptance_publication_authorization_store = authorization_store
    app.include_router(auth.router)
    app.include_router(acceptance_publication_authorizations.router)
    app.add_middleware(RateLimitMiddleware, rpm=500)
    app.add_middleware(JWTAuthMiddleware)
    monkeypatch.setattr(settings, "accounts_enabled", True)
    monkeypatch.setattr(settings, "accounts_bootstrap_tenant_id", "primary")

    with TestClient(app) as client:
        def login(identity: str, credential: str) -> dict[str, str]:
            response = client.post(
                "/auth/token",
                json={"username": identity, "api_credential": credential},
            )
            assert response.status_code == 200, response.text
            return {"Authorization": f"Bearer {response.json()['token']}"}

        yield SimpleNamespace(
            client=client,
            backend=backend,
            owner=owner,
            member=member,
            other_owner=other_owner,
            owner_headers=login("owner@example.test", OWNER_CREDENTIAL),
            member_headers=login("member@example.test", MEMBER_CREDENTIAL),
            other_headers=login(
                "other-owner@example.test",
                OTHER_OWNER_CREDENTIAL,
            ),
        )


def test_post_requires_authenticated_server_derived_primary_owner(
    account_route_client,
) -> None:
    client = account_route_client.client
    assert client.post(
        "/accounts/acceptance-authorizations", json=_request_body()
    ).status_code == 401
    assert client.post(
        "/accounts/acceptance-authorizations",
        json=_request_body(),
        headers=account_route_client.member_headers,
    ).status_code == 403
    assert client.post(
        "/accounts/acceptance-authorizations",
        json=_request_body(),
        headers=account_route_client.other_headers,
    ).status_code == 403

    created = client.post(
        "/accounts/acceptance-authorizations",
        json=_request_body(),
        headers=account_route_client.owner_headers,
    )
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "no-store, max-age=0"
    output = created.json()
    public = client.get(
        output["authorization_artifact_uri"].removeprefix(
            publisher.PRODUCTION_API_ORIGIN
        )
    )
    assert public.status_code == 200
    assert hashlib.sha256(public.content).hexdigest() == output[
        "authorization_artifact_sha256"
    ]
    assert public.json()["authorized_by"]["role"] == "owner"
    assert "owner@example.test" not in public.text
    assert '"tenant_id":"primary"' not in public.text


@pytest.mark.parametrize(
    "raw",
    [
        b'{"record_type":"authority_operation","record_type":"release_approval"}',
        json.dumps(_request_body(extra_legal_approval=True)).encode(),
        json.dumps(_request_body(expected_head_version=True)).encode(),
        json.dumps(_request_body(gate="release_approval")).encode(),
        json.dumps(_request_body(expected_previous_evidence_sha256=PREVIOUS_SHA)).encode(),
        (
            json.dumps(_request_body())[:-1]
            + ',"evidence_sha256":NaN}'
        ).encode(),
        b"[]",
    ],
)
def test_post_rejects_duplicate_nonfinite_extra_coercion_and_bad_bindings(
    account_route_client, raw: bytes
) -> None:
    response = account_route_client.client.post(
        "/accounts/acceptance-authorizations",
        content=raw,
        headers={
            **account_route_client.owner_headers,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 422


def test_post_refuses_identity_or_approval_fields_from_body(
    account_route_client,
) -> None:
    response = account_route_client.client.post(
        "/accounts/acceptance-authorizations",
        json=_request_body(
            actor_role="owner",
            actor_tenant_id="primary",
            legal_approval="ACCEPT",
            release_decision="ACCEPT",
        ),
        headers=account_route_client.owner_headers,
    )
    assert response.status_code == 422
    assert account_route_client.backend.list(
        AUTHORIZATION_TENANT_ID, AUTHORIZATION_KIND
    ) == ()


def test_public_exemption_is_exact_lowercase_query_free_get_only() -> None:
    digest = "a" * 64
    path = f"/internal/acceptance-authorizations/{digest}"
    assert is_public_acceptance_publication_authorization_request(path, "GET")
    assert not is_public_acceptance_publication_authorization_request(path, "HEAD")
    assert not is_public_acceptance_publication_authorization_request(path, "POST")
    assert not is_public_acceptance_publication_authorization_request(
        path, "GET", "x=1"
    )
    assert not is_public_acceptance_publication_authorization_request(
        path.upper(), "GET"
    )
    assert not is_public_acceptance_publication_authorization_request(
        f"{path}/extra", "GET"
    )


def test_nonexact_public_shapes_still_require_auth(account_route_client) -> None:
    created = account_route_client.client.post(
        "/accounts/acceptance-authorizations",
        json=_request_body(),
        headers=account_route_client.owner_headers,
    ).json()
    path = created["authorization_artifact_uri"].removeprefix(
        publisher.PRODUCTION_API_ORIGIN
    )
    assert account_route_client.client.get(path).status_code == 200
    assert account_route_client.client.get(f"{path}?x=1").status_code == 401
    assert account_route_client.client.head(path).status_code == 401
    assert account_route_client.client.get(path.upper()).status_code == 401
    assert account_route_client.client.get(f"{path}/extra").status_code == 401


def test_public_record_has_a_dedicated_rate_limit_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.middleware import rate_limit as rate_limit_module

    digest = "a" * 64
    authorization_path = f"/internal/acceptance-authorizations/{digest}"
    gate_path = ACCEPTANCE_AUTHORITY_PATH_BY_GATE["runtime_worm"]
    app = FastAPI()

    @app.get(authorization_path)
    async def authorization() -> dict[str, bool]:
        return {"ok": True}

    @app.get(gate_path)
    async def gate() -> dict[str, bool]:
        return {"ok": True}

    monkeypatch.setattr(
        rate_limit_module,
        "_ACCEPTANCE_PUBLICATION_AUTHORIZATION_CLIENT_RPM",
        1,
    )
    app.add_middleware(RateLimitMiddleware, rpm=500)
    with TestClient(app) as client:
        assert client.get(authorization_path).status_code == 200
        assert client.get(authorization_path).status_code == 429
        assert client.get(gate_path).status_code == 200


def test_publisher_rejects_dummy_reference_before_opening_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = _legal_evidence(NOW)
    path = tmp_path / "legal.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    digest = hashlib.sha256(
        canonicalize_acceptance_evidence(
            "legal_publication_approval", evidence, now=NOW
        )
    ).hexdigest()

    def forbidden(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("dummy URI must fail before production state opens")

    monkeypatch.setattr(publisher, "_production_authority", forbidden)
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        [
            "publish",
            "--gate",
            "legal_publication_approval",
            "--evidence",
            str(path),
            "--expected-master-head",
            MASTER,
            "--expected-deploy-id",
            DEPLOY,
            "--expected-evidence-sha256",
            digest,
            "--expected-head-version",
            "0",
            "--authorization-artifact-uri",
            f"{publisher.PRODUCTION_API_ORIGIN}/internal/acceptance-authorizations/dummy",
            "--authorization-artifact-sha256",
            "a" * 64,
            "--operation-reason",
            "authorized_publication",
        ],
        now=NOW,
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue())["code"] == (
        "publication_authorization_reference_invalid"
    )


def test_publisher_locally_asserts_exact_record_before_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = InMemoryStateStore()
    evidence = _legal_evidence(NOW)
    attestations = materialize_human_attestations(backend, evidence)
    path = tmp_path / "legal.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    digest = hashlib.sha256(
        canonicalize_acceptance_evidence(
            "legal_publication_approval", evidence, now=NOW
        )
    ).hexdigest()
    authorization_store = AcceptancePublicationAuthorizationStore(
        backend, primary_tenant_id="primary", pseudonymizer=PSEUDONYMIZER
    )
    authorization = _create(authorization_store, evidence_sha256=digest)
    base = CustomerProductionAcceptanceAuthorityStore(
        backend,
        human_attestation_store=attestations,
        publication_authorization_store=authorization_store,
    )
    calls: list[str] = []

    class TrackingAuthority:
        def assert_publication_authorized(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append("assert")
            return base.assert_publication_authorized(**kwargs)

        def publish(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append("publish")
            return base.publish(*args, **kwargs)

        def load(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return base.load(*args, **kwargs)

        def current_head(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return base.current_head(*args, **kwargs)

    @contextmanager
    def local_authority(**kwargs):  # type: ignore[no-untyped-def]
        yield TrackingAuthority()

    monkeypatch.setattr(publisher, "_production_authority", local_authority)
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        [
            "publish",
            "--gate",
            "legal_publication_approval",
            "--evidence",
            str(path),
            "--expected-master-head",
            MASTER,
            "--expected-deploy-id",
            DEPLOY,
            "--expected-evidence-sha256",
            digest,
            "--expected-head-version",
            "0",
            "--authorization-artifact-uri",
            authorization.uri,
            "--authorization-artifact-sha256",
            authorization.sha256,
            "--operation-reason",
            "authorized_publication",
        ],
        now=NOW,
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 0, stderr.getvalue()
    assert calls == ["assert", "publish"]
    assert json.loads(stdout.getvalue())["status"] == "published"


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (
            AcceptanceAuthorityAuthorizationInvalid("missing"),
            "publication_authorization_invalid",
        ),
        (
            AcceptanceAuthorityAuthorizationUnavailable("store down"),
            "authority_unavailable",
        ),
    ],
)
def test_publisher_prewrite_authorization_failure_never_reports_mutation_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected_code: str,
) -> None:
    evidence = _legal_evidence(NOW)
    path = tmp_path / "legal.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    digest = hashlib.sha256(
        canonicalize_acceptance_evidence(
            "legal_publication_approval", evidence, now=NOW
        )
    ).hexdigest()
    reference_digest = "b" * 64

    class FailingBeforeWrite:
        def assert_publication_authorized(self, **kwargs):  # type: ignore[no-untyped-def]
            raise failure

        def publish(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("publish must not run after authorization failure")

    @contextmanager
    def failing_authority(**kwargs):  # type: ignore[no-untyped-def]
        yield FailingBeforeWrite()

    monkeypatch.setattr(publisher, "_production_authority", failing_authority)
    stdout, stderr = io.StringIO(), io.StringIO()
    result = publisher.run(
        [
            "publish",
            "--gate",
            "legal_publication_approval",
            "--evidence",
            str(path),
            "--expected-master-head",
            MASTER,
            "--expected-deploy-id",
            DEPLOY,
            "--expected-evidence-sha256",
            digest,
            "--expected-head-version",
            "0",
            "--authorization-artifact-uri",
            acceptance_publication_authorization_url(reference_digest),
            "--authorization-artifact-sha256",
            reference_digest,
            "--operation-reason",
            "authorized_publication",
        ],
        now=NOW,
        stdout=stdout,
        stderr=stderr,
    )

    assert result in {2, 4}
    assert stdout.getvalue() == ""
    output = json.loads(stderr.getvalue())
    assert output["code"] == expected_code
    assert output.get("publication_state") is None


def test_no_mutating_or_enumerating_routes_exist(account_route_client) -> None:
    created = account_route_client.client.post(
        "/accounts/acceptance-authorizations",
        json=_request_body(),
        headers=account_route_client.owner_headers,
    ).json()
    path = created["authorization_artifact_uri"].removeprefix(
        publisher.PRODUCTION_API_ORIGIN
    )
    for method in ("put", "patch", "delete"):
        response = getattr(account_route_client.client, method)(
            path, headers=account_route_client.owner_headers
        )
        assert response.status_code == 403
    for nonexistent in (
        "/accounts/acceptance-authorizations/head",
        "/accounts/acceptance-authorizations/list",
    ):
        assert account_route_client.client.get(
            nonexistent, headers=account_route_client.owner_headers
        ).status_code == 404
    assert account_route_client.client.get(
        "/internal/acceptance-authorizations",
        headers=account_route_client.owner_headers,
    ).status_code == 403
