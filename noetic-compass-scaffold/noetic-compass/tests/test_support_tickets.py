from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from api.middleware.auth import create_token
from api.services.crm.abuse import PublicLeadAbuseGuard
from api.services.support_tickets import (
    JsonlSupportTicketStore,
    InMemorySupportTicketStore,
    SUPPORT_PRIVACY_URL,
    SupportTicketService,
    SupportTicketValidationError,
)


BASE = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)


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
    assert ticket.consent_to_contact is True


def test_consent_and_usable_email_are_required() -> None:
    service = SupportTicketService(InMemorySupportTicketStore(), clock=_clock(BASE, BASE))
    with pytest.raises(SupportTicketValidationError, match="consent"):
        service.receive(**_fields(consent_to_contact=False))
    with pytest.raises(SupportTicketValidationError, match="email"):
        service.receive(**_fields(email="not-an-email"))


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
    assert len(path.read_text(encoding="utf-8").splitlines()) == 3


@pytest.fixture
def support_client(client):
    client.app.state.support_tickets = SupportTicketService(
        InMemorySupportTicketStore()
    )
    client.app.state.support_public_abuse_guard = PublicLeadAbuseGuard(
        max_submissions=20, window_seconds=60
    )
    yield client
    client.app.state.support_tickets = None
    client.app.state.support_public_abuse_guard = None


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
    assert "email" not in body
    assert body["message"] != "Please contact me about an exact model-audit Evidence Packet."
    assert response.headers["Cache-Control"] == "no-store"


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
