from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.config import settings
from api.middleware.auth import create_token
from api.services.accounts.store import AccountStore
from api.services.crm.abuse import PublicLeadAbuseGuard
from api.services.crm.privacy import (
    CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256,
    CRM_CURRENT_OPEN_DRAFT_VERSION,
    CRM_PRIVACY_NOTICE_OPEN_STATUS,
    CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    CRMPrivacyNoticeContract,
)
from api.services.support_tickets import (
    JsonlSupportTicketStore,
    InMemorySupportTicketStore,
    SUPPORT_PRIVACY_URL,
    SUPPORT_PRIVACY_UNAVAILABLE,
    SUPPORT_TICKET_SCHEMA_VERSION,
    SUPPORT_TICKET_SCHEMA_VERSION_V1,
    SupportTicketReplayError,
    SupportTicketService,
    SupportTicketValidationError,
    build_support_ticket_service,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.sessions import SessionStore


BASE = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)
TEST_PRIVACY_VERSION = "privacy-2026-07-15"
TEST_PRIVACY_CONTENT_SHA256 = "b" * 64
_MISSING = object()


def _fields(**updates: object) -> dict[str, object]:
    values: dict[str, object] = {
        "email": "customer@example.com",
        "name": "Customer",
        "organization": "Example Org",
        "subject": "Evidence Packet question",
        "message": "Please help me verify the exact Evidence Packet receipt.",
        "category": "product_support",
        "source": "cascompass_contact",
        "consent_to_contact": True,
        "privacy_notice_version": TEST_PRIVACY_VERSION,
        "privacy_notice_content_sha256": TEST_PRIVACY_CONTENT_SHA256,
        "privacy_notice_publication_status": CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        "trace_id": "req-support-1",
    }
    values.update(updates)
    return values


def _clock(*values: datetime):
    iterator = iter(values)
    return lambda: next(iterator)


def _headers(sub: str = "support-test") -> dict[str, str]:
    token = create_token(sub=sub, api_key=f"support-{uuid4().hex}")
    return {"Authorization": f"Bearer {token}"}


def test_receive_is_not_an_acknowledgement_or_resolution() -> None:
    service = SupportTicketService(
        InMemorySupportTicketStore(), clock=_clock(BASE)
    )
    ticket = service.receive(**_fields())

    assert ticket.status == "received"
    assert ticket.owner is None
    assert ticket.acknowledged_at_utc is None
    assert ticket.resolved_at_utc is None
    assert ticket.privacy_url == SUPPORT_PRIVACY_URL
    assert ticket.privacy_notice_version == TEST_PRIVACY_VERSION
    assert ticket.privacy_notice_content_sha256 == TEST_PRIVACY_CONTENT_SHA256
    assert (
        ticket.privacy_notice_publication_status
        == CRM_PRIVACY_NOTICE_PRESENT_STATUS
    )
    assert ticket.consent_to_contact is True


def test_consent_and_usable_email_are_required() -> None:
    service = SupportTicketService(InMemorySupportTicketStore(), clock=_clock(BASE, BASE))
    with pytest.raises(SupportTicketValidationError, match="consent"):
        service.receive(**_fields(consent_to_contact=False))
    with pytest.raises(SupportTicketValidationError, match="email"):
        service.receive(**_fields(email="not-an-email"))


def test_service_rejects_open_notice_before_persistence() -> None:
    store = InMemorySupportTicketStore()
    service = SupportTicketService(store, clock=_clock(BASE))

    with pytest.raises(SupportTicketValidationError, match="exact present"):
        service.receive(
            **_fields(
                privacy_notice_version=CRM_CURRENT_OPEN_DRAFT_VERSION,
                privacy_notice_content_sha256=(
                    CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256
                ),
                privacy_notice_publication_status=CRM_PRIVACY_NOTICE_OPEN_STATUS,
            )
        )

    assert store.list_all() == []


def test_route_acknowledge_resolve_requires_assigned_owner() -> None:
    service = SupportTicketService(
        InMemorySupportTicketStore(),
        clock=_clock(
            BASE,
            BASE + timedelta(minutes=1),
            BASE + timedelta(minutes=2),
            BASE + timedelta(minutes=3),
            BASE + timedelta(minutes=4),
            BASE + timedelta(minutes=5),
        ),
    )
    received = service.receive(**_fields())

    with pytest.raises(SupportTicketValidationError, match="routed"):
        service.acknowledge(received.ticket_id, actor="support-a")

    routed = service.route(received.ticket_id, owner="support-a")
    assert routed is not None and routed.status == "routed"
    with pytest.raises(SupportTicketValidationError, match="assigned owner"):
        service.acknowledge(received.ticket_id, actor="support-b")

    acknowledged = service.acknowledge(received.ticket_id, actor="support-a")
    assert acknowledged is not None and acknowledged.status == "acknowledged"
    resolved = service.resolve(
        received.ticket_id,
        actor="support-a",
        summary="Customer verified the exact packet digest and closed the request.",
    )
    assert resolved is not None and resolved.status == "resolved"
    assert resolved.version == 4
    expected_notice = (
        SUPPORT_PRIVACY_URL,
        TEST_PRIVACY_VERSION,
        TEST_PRIVACY_CONTENT_SHA256,
        CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    )
    for ticket in (received, routed, acknowledged, resolved):
        assert ticket is not None
        assert (
            ticket.privacy_url,
            ticket.privacy_notice_version,
            ticket.privacy_notice_content_sha256,
            ticket.privacy_notice_publication_status,
        ) == expected_notice


def test_acknowledgement_sla_uses_exact_timestamps() -> None:
    service = SupportTicketService(
        InMemorySupportTicketStore(),
        clock=_clock(BASE, BASE + timedelta(minutes=1), BASE + timedelta(minutes=9)),
    )
    ticket = service.receive(**_fields())
    service.route(ticket.ticket_id, owner="support-a")
    acknowledged = service.acknowledge(ticket.ticket_id, actor="support-a")
    assert acknowledged is not None
    assert acknowledged.acknowledged_within(600) is True
    assert acknowledged.acknowledged_within(300) is False


def test_jsonl_store_replays_latest_append_after_restart(tmp_path) -> None:
    path = tmp_path / "support.jsonl"
    service = SupportTicketService(
        JsonlSupportTicketStore(path),
        clock=_clock(BASE, BASE + timedelta(minutes=1), BASE + timedelta(minutes=2)),
    )
    ticket = service.receive(**_fields())
    service.route(ticket.ticket_id, owner="support-a")
    service.acknowledge(ticket.ticket_id, actor="support-a")

    restarted = JsonlSupportTicketStore(path).get(ticket.ticket_id)
    assert restarted is not None
    assert restarted.status == "acknowledged"
    assert restarted.owner == "support-a"
    assert restarted.version == 3
    assert restarted.privacy_notice_version == TEST_PRIVACY_VERSION
    assert restarted.privacy_notice_content_sha256 == TEST_PRIVACY_CONTENT_SHA256
    assert (
        restarted.privacy_notice_publication_status
        == CRM_PRIVACY_NOTICE_PRESENT_STATUS
    )
    assert len(path.read_text(encoding="utf-8").splitlines()) == 3


def test_jsonl_store_explicitly_replays_v1_with_unavailable_notice_evidence(
    tmp_path,
) -> None:
    path = tmp_path / "support-v1.jsonl"
    legacy = {
        "ticket_id": "sup_legacy_v1",
        "created_at_utc": "2026-07-14T12:00:00Z",
        "updated_at_utc": "2026-07-14T12:00:00Z",
        "version": 1,
        "status": "received",
        "email": "legacy@example.com",
        "name": "Legacy Customer",
        "organization": "Legacy Org",
        "subject": "Legacy support request",
        "message": "This record predates byte-bound privacy notice evidence.",
        "category": "support",
        "source": "legacy",
        "consent_to_contact": True,
        "privacy_url": SUPPORT_PRIVACY_URL,
        "trace_id": "legacy-request",
        "owner": None,
        "routed_at_utc": None,
        "acknowledged_at_utc": None,
        "resolved_at_utc": None,
        "resolution_summary": None,
        "schema_version": SUPPORT_TICKET_SCHEMA_VERSION_V1,
    }
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    replayed = JsonlSupportTicketStore(path).get("sup_legacy_v1")

    assert replayed is not None
    assert replayed.schema_version == SUPPORT_TICKET_SCHEMA_VERSION_V1
    assert replayed.privacy_url == SUPPORT_PRIVACY_URL
    assert replayed.privacy_notice_version == SUPPORT_PRIVACY_UNAVAILABLE
    assert replayed.privacy_notice_content_sha256 == ""
    assert (
        replayed.privacy_notice_publication_status == SUPPORT_PRIVACY_UNAVAILABLE
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("privacy_url", "https://attacker.example/privacy"),
        ("privacy_notice_content_sha256", "not-a-sha256"),
        ("privacy_notice_publication_status", CRM_PRIVACY_NOTICE_OPEN_STATUS),
        ("consent_to_contact", "true"),
    ],
)
def test_jsonl_store_fails_closed_on_tampered_v2_privacy_contract(
    tmp_path, field: str, value: object
) -> None:
    path = tmp_path / f"support-v2-{field}.jsonl"
    ticket = SupportTicketService(
        InMemorySupportTicketStore(), clock=_clock(BASE)
    ).receive(**_fields())
    payload = ticket.to_dict()
    assert payload["schema_version"] == SUPPORT_TICKET_SCHEMA_VERSION
    payload[field] = value
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(SupportTicketReplayError, match="invalid persisted v2"):
        JsonlSupportTicketStore(path)


def _received_v2_payload() -> dict[str, object]:
    ticket = SupportTicketService(
        InMemorySupportTicketStore(), clock=_clock(BASE)
    ).receive(**_fields())
    payload = ticket.to_dict()
    assert payload["schema_version"] == SUPPORT_TICKET_SCHEMA_VERSION
    return payload


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "attacker-controlled"),
        ("email", 17),
        ("trace_id", []),
        ("schema_version", f" {SUPPORT_TICKET_SCHEMA_VERSION} "),
    ],
)
def test_jsonl_store_rejects_bad_v2_field_types_and_values(
    tmp_path, field: str, value: object
) -> None:
    path = tmp_path / f"support-v2-bad-{field}.jsonl"
    payload = _received_v2_payload()
    payload[field] = value
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(SupportTicketReplayError, match="invalid persisted v2"):
        JsonlSupportTicketStore(path)


@pytest.mark.parametrize("missing_field", ["email", "status", "updated_at_utc"])
def test_jsonl_store_rejects_missing_required_v2_fields(
    tmp_path, missing_field: str
) -> None:
    path = tmp_path / f"support-v2-missing-{missing_field}.jsonl"
    payload = _received_v2_payload()
    payload.pop(missing_field)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(SupportTicketReplayError, match="invalid persisted v2"):
        JsonlSupportTicketStore(path)


@pytest.mark.parametrize("invalid_version", ["1", True, 1.0, 0, -1])
def test_jsonl_store_rejects_non_strict_or_non_positive_v2_version(
    tmp_path, invalid_version: object
) -> None:
    path = tmp_path / "support-v2-invalid-version.jsonl"
    payload = _received_v2_payload()
    payload["version"] = invalid_version
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(SupportTicketReplayError, match="invalid persisted v2"):
        JsonlSupportTicketStore(path)


@pytest.mark.parametrize(
    "timestamp_updates",
    [
        {"created_at_utc": "not-a-timestamp"},
        {"updated_at_utc": "2026-07-14T11:59:59Z"},
        {"updated_at_utc": "2026-07-14T12:00:00+00:00"},
        {"routed_at_utc": "2026-07-14T12:01:00Z"},
    ],
)
def test_jsonl_store_rejects_invalid_or_time_ordered_v2_timestamps(
    tmp_path, timestamp_updates: dict[str, object]
) -> None:
    path = tmp_path / "support-v2-invalid-timestamp.jsonl"
    payload = _received_v2_payload()
    payload.update(timestamp_updates)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(SupportTicketReplayError, match="invalid persisted v2"):
        JsonlSupportTicketStore(path)


@pytest.mark.parametrize(
    "lifecycle_updates",
    [
        {"owner": "support-a"},
        {"status": "routed", "version": 2},
        {"status": "acknowledged", "version": 3},
        {"status": "resolved", "version": 4},
        {"resolution_summary": "Claims resolution without a resolution event."},
    ],
)
def test_jsonl_store_rejects_v2_lifecycle_field_contradictions(
    tmp_path, lifecycle_updates: dict[str, object]
) -> None:
    path = tmp_path / "support-v2-invalid-lifecycle.jsonl"
    payload = _received_v2_payload()
    payload.update(lifecycle_updates)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(SupportTicketReplayError, match="invalid persisted v2"):
        JsonlSupportTicketStore(path)


def test_jsonl_store_rejects_corrupt_latest_v2_append_instead_of_reverting(
    tmp_path,
) -> None:
    path = tmp_path / "support-v2-corrupt-latest.jsonl"
    service = SupportTicketService(
        JsonlSupportTicketStore(path),
        clock=_clock(BASE, BASE + timedelta(minutes=1)),
    )
    received = service.receive(**_fields())
    routed = service.route(received.ticket_id, owner="support-a")
    assert routed is not None and routed.version == 2

    corrupt_latest = routed.to_dict()
    corrupt_latest.update(
        {
            "version": 3,
            "email": "tampered-customer@example.com",
            "routed_at_utc": "2026-07-14T12:02:00Z",
            "updated_at_utc": "2026-07-14T12:02:00Z",
        }
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(corrupt_latest) + "\n")

    with pytest.raises(
        SupportTicketReplayError, match="invalid persisted v2 support ticket history"
    ):
        JsonlSupportTicketStore(path)


def test_jsonl_store_replays_complete_valid_v2_history_with_idempotent_retries(
    tmp_path,
) -> None:
    path = tmp_path / "support-v2-valid-complete-history.jsonl"
    service = SupportTicketService(
        JsonlSupportTicketStore(path),
        clock=_clock(
            BASE,
            BASE + timedelta(minutes=1),
            BASE + timedelta(minutes=2),
            BASE + timedelta(minutes=3),
            BASE + timedelta(minutes=4),
            BASE + timedelta(minutes=5),
            BASE + timedelta(minutes=6),
            BASE + timedelta(minutes=7),
        ),
    )
    received = service.receive(**_fields())
    service.route(received.ticket_id, owner="support-a")
    service.acknowledge(received.ticket_id, actor="support-a")
    service.acknowledge(received.ticket_id, actor="support-a")
    service.route(received.ticket_id, owner="support-b")
    service.acknowledge(received.ticket_id, actor="support-b")
    service.resolve(
        received.ticket_id,
        actor="support-b",
        summary="Customer confirmed the exact resolution receipt.",
    )
    service.resolve(
        received.ticket_id,
        actor="support-b",
        summary="This retry must not alter the durable resolution.",
    )

    restarted = JsonlSupportTicketStore(path).get(received.ticket_id)

    assert restarted is not None
    assert restarted.status == "resolved"
    assert restarted.owner == "support-b"
    assert restarted.version == 5
    assert (
        restarted.resolution_summary
        == "Customer confirmed the exact resolution receipt."
    )


def test_production_builder_without_path_is_non_durable_for_route_to_refuse() -> None:
    service = build_support_ticket_service(
        SimpleNamespace(
            accounts_enabled=False,
            debug=False,
            support_ticket_store_path=None,
        )
    )

    assert service.is_durable is False


@pytest.fixture
def support_client(client):
    old_notice = getattr(client.app.state, "crm_privacy_notice_contract", _MISSING)
    client.app.state.support_tickets = SupportTicketService(
        InMemorySupportTicketStore()
    )
    client.app.state.support_public_abuse_guard = PublicLeadAbuseGuard(
        max_submissions=20, window_seconds=60
    )
    client.app.state.crm_privacy_notice_contract = CRMPrivacyNoticeContract(
        publication_status=CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        version=TEST_PRIVACY_VERSION,
        content_sha256=TEST_PRIVACY_CONTENT_SHA256,
    ).validated()
    yield client
    client.app.state.support_tickets = None
    client.app.state.support_public_abuse_guard = None
    if old_notice is _MISSING:
        delattr(client.app.state, "crm_privacy_notice_contract")
    else:
        client.app.state.crm_privacy_notice_contract = old_notice


def _public_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": f"support-{uuid4().hex}@example.com",
        "name": "Web Customer",
        "organization": "Example Org",
        "subject": "Need help with an audit",
        "message": "Please contact me about an exact model-audit Evidence Packet.",
        "category": "product_support",
        "source": "cascompass_contact",
        "consent_to_contact": True,
        "privacy_notice_version": TEST_PRIVACY_VERSION,
        "privacy_notice_content_sha256": TEST_PRIVACY_CONTENT_SHA256,
    }
    payload.update(updates)
    return payload


def test_public_create_returns_non_pii_receipt_and_exact_privacy_url(support_client) -> None:
    response = support_client.post(
        "/api/support/public/tickets",
        json=_public_payload(),
        headers={"X-Request-ID": "req-public-support"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["received"] is True
    assert body["status"] == "received"
    assert body["privacy_url"] == SUPPORT_PRIVACY_URL
    assert body["privacy_notice_version"] == TEST_PRIVACY_VERSION
    assert body["privacy_notice_content_sha256"] == TEST_PRIVACY_CONTENT_SHA256
    assert (
        body["privacy_notice_publication_status"]
        == CRM_PRIVACY_NOTICE_PRESENT_STATUS
    )
    assert "email" not in body
    assert body["message"] != "Please contact me about an exact model-audit Evidence Packet."
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "contract,detail_fragment",
    [
        (
            CRMPrivacyNoticeContract(
                publication_status=CRM_PRIVACY_NOTICE_OPEN_STATUS,
                version=CRM_CURRENT_OPEN_DRAFT_VERSION,
                content_sha256=CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256,
            ).validated(),
            "status is OPEN",
        ),
        (
            CRMPrivacyNoticeContract(
                publication_status=CRM_PRIVACY_NOTICE_PRESENT_STATUS,
                version=CRM_CURRENT_OPEN_DRAFT_VERSION,
                content_sha256=CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256,
            ),
            "invalid or unavailable",
        ),
        (None, "invalid or unavailable"),
    ],
    ids=("open", "draft-relabeled-present", "unavailable"),
)
def test_public_create_fails_closed_without_a_published_notice_and_persists_zero_pii(
    support_client, contract, detail_fragment: str
) -> None:
    service = support_client.app.state.support_tickets
    before = service.list_all()
    payload = _public_payload(
        email="must-not-persist@example.com",
        message="Private support details must not be stored.",
    )
    support_client.app.state.crm_privacy_notice_contract = contract

    response = support_client.post("/api/support/public/tickets", json=payload)

    assert response.status_code == 503
    assert detail_fragment in response.json()["detail"]
    assert service.list_all() == before


def test_public_create_rejects_missing_or_stale_notice_acknowledgement(
    support_client,
) -> None:
    service = support_client.app.state.support_tickets
    payloads = []

    missing_version = _public_payload()
    missing_version.pop("privacy_notice_version")
    payloads.append(missing_version)

    missing_digest = _public_payload()
    missing_digest.pop("privacy_notice_content_sha256")
    payloads.append(missing_digest)

    payloads.append(_public_payload(privacy_notice_version="privacy-2026-07-14"))
    payloads.append(_public_payload(privacy_notice_content_sha256="c" * 64))

    for payload in payloads:
        before = service.list_all()
        response = support_client.post(
            "/api/support/public/tickets", json=payload
        )
        assert response.status_code == 409, response.text
        assert "missing or stale" in response.json()["detail"]
        assert service.list_all() == before


@pytest.mark.parametrize(
    "adversarial_consent",
    [1, 0, "true", "false", [], {}],
)
def test_public_create_requires_strict_boolean_consent_and_persists_zero_pii(
    support_client, adversarial_consent: object
) -> None:
    service = support_client.app.state.support_tickets
    before = service.list_all()

    response = support_client.post(
        "/api/support/public/tickets",
        json=_public_payload(consent_to_contact=adversarial_consent),
    )

    assert response.status_code == 422
    assert service.list_all() == before


@pytest.mark.parametrize(
    ("accounts_enabled", "debug", "installed_kind"),
    [
        (True, True, "missing"),
        (True, True, "memory"),
        (False, False, "missing"),
        (False, False, "memory"),
    ],
)
def test_public_create_fails_closed_when_durable_support_service_is_unavailable(
    support_client,
    monkeypatch,
    accounts_enabled: bool,
    debug: bool,
    installed_kind: str,
) -> None:
    service = (
        None
        if installed_kind == "missing"
        else SupportTicketService(InMemorySupportTicketStore())
    )
    support_client.app.state.support_tickets = service
    monkeypatch.setattr(settings, "accounts_enabled", accounts_enabled)
    monkeypatch.setattr(settings, "debug", debug)

    response = support_client.post(
        "/api/support/public/tickets", json=_public_payload()
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "support ticket persistence is unavailable"
    if service is not None:
        assert service.list_all() == []


def test_public_create_rejects_honeypot_and_missing_consent(support_client) -> None:
    honeypot = support_client.post(
        "/api/support/public/tickets",
        json=_public_payload(website="https://spam.example"),
    )
    assert honeypot.status_code == 400

    no_consent = support_client.post(
        "/api/support/public/tickets",
        json=_public_payload(consent_to_contact=False),
    )
    assert no_consent.status_code == 422


def test_only_exact_create_route_is_public(support_client) -> None:
    assert support_client.get("/api/support/tickets").status_code == 401
    assert support_client.get("/api/support/public/tickets").status_code == 405
    assert support_client.post("/api/support/public/anything", json={}).status_code == 401


@pytest.fixture
def account_mode_support_client(tmp_path, monkeypatch):
    """Install two-tenant account identity plus one durable global support queue."""

    from api.main import app

    backend = SqliteStateStore(tmp_path / f"accounts-{uuid4().hex}.db")
    account_store = AccountStore(
        backend,
        credential_pepper="test-support-credential-pepper-0123456789",
    )
    session_store = SessionStore(backend)

    with TestClient(app) as client:
        previous = {
            "account_store": getattr(app.state, "account_store", None),
            "session_store": getattr(app.state, "session_store", None),
            "support_tickets": getattr(app.state, "support_tickets", None),
            "support_public_abuse_guard": getattr(
                app.state, "support_public_abuse_guard", None
            ),
            "crm_privacy_notice_contract": getattr(
                app.state, "crm_privacy_notice_contract", None
            ),
        }
        monkeypatch.setattr(settings, "accounts_enabled", True)
        app.state.account_store = account_store
        app.state.session_store = session_store
        app.state.support_tickets = SupportTicketService(
            JsonlSupportTicketStore(tmp_path / "support-account-mode.jsonl")
        )
        app.state.support_public_abuse_guard = PublicLeadAbuseGuard(
            max_submissions=20, window_seconds=60
        )
        app.state.crm_privacy_notice_contract = CRMPrivacyNoticeContract(
            publication_status=CRM_PRIVACY_NOTICE_PRESENT_STATUS,
            version=TEST_PRIVACY_VERSION,
            content_sha256=TEST_PRIVACY_CONTENT_SHA256,
        ).validated()
        try:
            yield client, account_store
        finally:
            for name, value in previous.items():
                setattr(app.state, name, value)
    backend.close()


def _account_mode_headers(
    client: TestClient,
    store: AccountStore,
    *,
    identity: str,
    role: str,
    tenant_id: str,
) -> tuple[dict[str, str], str]:
    invite = store.create_invite(
        code=f"support-{uuid4().hex}", role=role, tenant_id=tenant_id
    )
    credential = "casak_0123456789abcdefghijklmnopqrstuvwxyzABCDEFG"
    account = store.redeem_invite(
        code=invite.code,
        email_or_username=identity,
        api_credential=credential,
    )
    response = client.post(
        "/auth/token",
        json={"username": identity, "api_credential": credential},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}, account.account_id


def test_account_mode_tenant_roles_cannot_read_global_support_pii(
    account_mode_support_client,
) -> None:
    client, store = account_mode_support_client
    private_email = "global-private-ticket@example.com"
    created = client.post(
        "/api/support/public/tickets",
        json=_public_payload(email=private_email),
    )
    assert created.status_code == 201, created.text

    tenant_a, _ = _account_mode_headers(
        client,
        store,
        identity="tenant-a-support@example.com",
        role="support",
        tenant_id="tenant-a",
    )
    tenant_b, _ = _account_mode_headers(
        client,
        store,
        identity="tenant-b-owner@example.com",
        role="owner",
        tenant_id="tenant-b",
    )

    for headers in (tenant_a, tenant_b):
        response = client.get("/api/support/tickets", headers=headers)
        assert response.status_code == 403
        assert private_email not in response.text
        assert "system" in response.json()["detail"]

    platform_headers, _ = _account_mode_headers(
        client,
        store,
        identity="platform-support-service@example.com",
        role="system",
        tenant_id="platform",
    )
    platform_response = client.get(
        "/api/support/tickets", headers=platform_headers
    )
    assert platform_response.status_code == 200, platform_response.text
    assert platform_response.json()["count"] == 1
    assert platform_response.json()["tickets"][0]["email"] == private_email


def test_authenticated_operator_lifecycle_records_real_actions(support_client) -> None:
    headers = _headers("support-test")
    created = support_client.post(
        "/api/support/public/tickets", json=_public_payload()
    )
    ticket_id = created.json()["ticket_id"]

    routed = support_client.post(
        f"/api/support/tickets/{ticket_id}/route",
        json={"owner": "support-test"},
        headers=headers,
    )
    assert routed.status_code == 200, routed.text
    assert routed.json()["status"] == "routed"
    assert routed.json()["owner"] == "support-test"

    acknowledged = support_client.post(
        f"/api/support/tickets/{ticket_id}/acknowledge", headers=headers
    )
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["status"] == "acknowledged"
    assert acknowledged.json()["acknowledged_at_utc"]

    resolved = support_client.post(
        f"/api/support/tickets/{ticket_id}/resolve",
        json={"resolution_summary": "Customer confirmed the issue is resolved."},
        headers=headers,
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at_utc"]


def test_wrong_authenticated_actor_cannot_acknowledge(support_client) -> None:
    created = support_client.post(
        "/api/support/public/tickets", json=_public_payload()
    )
    ticket_id = created.json()["ticket_id"]
    support_client.post(
        f"/api/support/tickets/{ticket_id}/route",
        json={"owner": "assigned-owner"},
        headers=_headers("operator"),
    )
    response = support_client.post(
        f"/api/support/tickets/{ticket_id}/acknowledge",
        headers=_headers("different-actor"),
    )
    assert response.status_code == 409
    assert "assigned owner" in response.json()["detail"]


def test_public_rate_limit_is_independent_and_returns_retry_after(support_client) -> None:
    support_client.app.state.support_public_abuse_guard = PublicLeadAbuseGuard(
        max_submissions=1, window_seconds=60, now=lambda: 1000.0
    )
    headers = {"X-Forwarded-For": "203.0.113.44"}
    first = support_client.post(
        "/api/support/public/tickets", json=_public_payload(), headers=headers
    )
    second = support_client.post(
        "/api/support/public/tickets", json=_public_payload(), headers=headers
    )
    assert first.status_code == 201
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "60"
