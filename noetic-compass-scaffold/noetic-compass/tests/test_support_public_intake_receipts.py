from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib

import pytest

from api.services.customer_production_pseudonyms import (
    PSEUDONYMIZATION_SCHEME,
    SUBJECT_PATTERN,
    CustomerProductionPseudonymizer,
)
from api.services.production.state_substrate import (
    InMemoryStateStore,
    LedgerRecord,
)
from api.services.revisioned_contact_store import CONTACT_STATE_TENANT
from api.services.support_public_intake_receipts import (
    HTTP_STATUS_CREATED,
    RECEIPT_KIND,
    RECEIPT_SOURCE,
    SCHEMA_VERSION,
    SERVER_OWNED_REQUEST_SOURCE,
    SupportPublicIntakeReceiptInvalid,
    SupportPublicIntakeReceiptStore,
    SupportPublicIntakeReceiptUnavailable,
)
from api.services.support_ticket_state_store import StateStoreSupportTicketStore
from api.services.support_tickets import SUPPORT_TICKET_SCHEMA_VERSION, SupportTicket


BASE = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
KEY_A_ID = "cpk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
KEY_B_ID = "cpk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
KEY_A = hashlib.sha256(b"support-public-intake-key-a").digest()
KEY_B = hashlib.sha256(b"support-public-intake-key-b").digest()
PSEUDONYMIZER = CustomerProductionPseudonymizer(
    {KEY_A_ID: KEY_A}, active_key_id=KEY_A_ID
)


def _seed_ticket(
    backend: InMemoryStateStore,
    *,
    trace_id: str = "req-support-intake-0001",
    source: str = SERVER_OWNED_REQUEST_SOURCE,
    now: datetime = BASE,
) -> SupportTicket:
    ticket = SupportTicket.receive(
        email="customer@example.com",
        name="Customer",
        organization="Example Org",
        subject="Need help",
        message="Please help with the audit result.",
        category="support",
        source=source,
        consent_to_contact=True,
        privacy_notice_version="2026-07-15",
        privacy_notice_content_sha256="1" * 64,
        privacy_notice_publication_status="present",
        trace_id=trace_id,
        now=now,
    )
    return StateStoreSupportTicketStore(backend).save(ticket)


def _service(
    backend: InMemoryStateStore,
    *,
    pseudonymizer: CustomerProductionPseudonymizer = PSEUDONYMIZER,
) -> SupportPublicIntakeReceiptStore:
    return SupportPublicIntakeReceiptStore(
        backend, pseudonymizer=pseudonymizer
    )


def _receipt_id(ticket_id: str) -> str:
    return f"support-public-intake-receipt:{ticket_id}"


def _receipt_row(
    backend: InMemoryStateStore, ticket_id: str
) -> LedgerRecord:
    record = backend.get(
        CONTACT_STATE_TENANT, RECEIPT_KIND, _receipt_id(ticket_id)
    )
    assert record is not None
    return record


def _replace_row(
    backend: InMemoryStateStore, record: LedgerRecord
) -> None:
    backend._records[(record.tenant_id, record.kind, record.record_id)] = record


def test_create_is_exact_idempotent_and_survives_lifecycle_movement() -> None:
    backend = InMemoryStateStore()
    tickets = StateStoreSupportTicketStore(backend)
    ticket = _seed_ticket(backend)
    service = _service(backend)

    first = service.create(ticket.ticket_id, now=BASE + timedelta(seconds=1))
    second = service.create(ticket.ticket_id, now=BASE + timedelta(seconds=2))

    assert first == second == service.read(ticket.ticket_id)
    assert service.revalidate(ticket.ticket_id) == first
    assert service.state_store is backend
    assert service.pseudonymizer is PSEUDONYMIZER
    assert first.version == 1
    assert first.tenant_id == CONTACT_STATE_TENANT
    assert first.kind == RECEIPT_KIND
    assert first.record_id == _receipt_id(ticket.ticket_id)
    assert first.parent_ids == (f"{ticket.ticket_id}:v1",)
    assert first.source == RECEIPT_SOURCE
    assert first.trace_id == ticket.trace_id
    assert first.created_at == first.updated_at == BASE + timedelta(seconds=1)
    assert len(backend.list(CONTACT_STATE_TENANT, RECEIPT_KIND)) == 1

    payload = first.payload
    assert set(payload) == {
        "schema_version",
        "ticket_id",
        "ticket_schema_version",
        "initial_ticket_version",
        "initial_ticket_revision_id",
        "initial_ticket_content_sha256",
        "initial_ticket_revision_envelope_sha256",
        "request_trace_id",
        "source",
        "consent_to_contact",
        "privacy_url",
        "privacy_notice_version",
        "privacy_notice_content_sha256",
        "privacy_notice_publication_status",
        "created_at_utc",
        "recorded_at_utc",
        "http_status",
        "pseudonymization_scheme",
        "pseudonym_key_id",
        "content_binding_hmac",
    }
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["ticket_schema_version"] == SUPPORT_TICKET_SCHEMA_VERSION
    assert payload["initial_ticket_version"] == 1
    assert payload["request_trace_id"] == ticket.trace_id
    assert payload["source"] == SERVER_OWNED_REQUEST_SOURCE
    assert payload["consent_to_contact"] is True
    assert payload["privacy_notice_publication_status"] == "present"
    assert payload["created_at_utc"] == ticket.created_at_utc
    assert payload["recorded_at_utc"] == "2026-07-15T12:00:01Z"
    assert type(payload["http_status"]) is int
    assert payload["http_status"] == HTTP_STATUS_CREATED == 201
    assert payload["pseudonymization_scheme"] == PSEUDONYMIZATION_SCHEME
    assert payload["pseudonym_key_id"] == KEY_A_ID
    assert SUBJECT_PATTERN.fullmatch(str(payload["content_binding_hmac"]))

    routed = tickets.save(ticket.route(owner="support-owner", now=BASE + timedelta(minutes=1)))
    assert routed.version == 2
    assert service.read(ticket.ticket_id) == first
    assert service.create(ticket.ticket_id, now=BASE + timedelta(minutes=2)) == first


def test_missing_receipt_and_missing_source_fail_invalid() -> None:
    backend = InMemoryStateStore()
    ticket = _seed_ticket(backend)
    service = _service(backend)

    with pytest.raises(SupportPublicIntakeReceiptInvalid, match="absent"):
        service.read(ticket.ticket_id)

    service.create(ticket.ticket_id, now=BASE + timedelta(seconds=1))
    backend.delete(
        CONTACT_STATE_TENANT,
        "support_ticket_revision",
        f"{ticket.ticket_id}:v1",
        expected_version=1,
    )
    with pytest.raises(SupportPublicIntakeReceiptInvalid, match="source is absent"):
        service.revalidate(ticket.ticket_id)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("http_status", 200),
        ("source", "caller_supplied"),
        ("consent_to_contact", False),
        ("request_trace_id", "different-trace"),
        ("privacy_notice_content_sha256", "2" * 64),
        ("content_binding_hmac", "hmac-sha256:" + "a" * 64),
    ],
)
def test_tampered_receipt_payload_fails_invalid(field: str, value: object) -> None:
    backend = InMemoryStateStore()
    ticket = _seed_ticket(backend)
    service = _service(backend)
    service.create(ticket.ticket_id, now=BASE + timedelta(seconds=1))
    record = _receipt_row(backend, ticket.ticket_id)
    payload = dict(record.payload)
    payload[field] = value
    _replace_row(backend, replace(record, payload=payload))

    with pytest.raises(SupportPublicIntakeReceiptInvalid):
        service.read(ticket.ticket_id)


def test_crosswired_parent_and_ticket_receipt_fail_invalid() -> None:
    backend = InMemoryStateStore()
    first_ticket = _seed_ticket(backend, trace_id="req-first", now=BASE)
    second_ticket = _seed_ticket(
        backend, trace_id="req-second", now=BASE + timedelta(seconds=1)
    )
    service = _service(backend)
    service.create(first_ticket.ticket_id, now=BASE + timedelta(seconds=2))
    service.create(second_ticket.ticket_id, now=BASE + timedelta(seconds=3))
    first = _receipt_row(backend, first_ticket.ticket_id)
    second = _receipt_row(backend, second_ticket.ticket_id)

    _replace_row(
        backend,
        replace(first, parent_ids=second.parent_ids),
    )
    with pytest.raises(SupportPublicIntakeReceiptInvalid, match="cross-wired"):
        service.read(first_ticket.ticket_id)

    _replace_row(
        backend,
        replace(
            first,
            payload=dict(second.payload),
            parent_ids=second.parent_ids,
            trace_id=second.trace_id,
        ),
    )
    with pytest.raises(SupportPublicIntakeReceiptInvalid, match="identity"):
        service.read(first_ticket.ticket_id)


def test_direct_seed_with_wrong_envelope_source_is_rejected() -> None:
    backend = InMemoryStateStore()
    ticket = _seed_ticket(backend)
    service = _service(backend)
    legitimate = service.create(
        ticket.ticket_id, now=BASE + timedelta(seconds=1)
    )
    backend.delete(
        CONTACT_STATE_TENANT,
        RECEIPT_KIND,
        legitimate.record_id,
        expected_version=1,
    )
    directly_seeded = LedgerRecord.new(
        tenant_id=CONTACT_STATE_TENANT,
        kind=RECEIPT_KIND,
        record_id=legitimate.record_id,
        payload=dict(legitimate.payload),
        parent_ids=legitimate.parent_ids,
        source="direct_test_seed",
        trace_id=legitimate.trace_id,
        now=legitimate.created_at,
    )
    backend.put(directly_seeded, expected_version=0)

    with pytest.raises(SupportPublicIntakeReceiptInvalid, match="identity"):
        service.read(ticket.ticket_id)


def test_non_server_owned_source_and_missing_request_trace_cannot_create() -> None:
    backend = InMemoryStateStore()
    wrong_source = _seed_ticket(backend, source="caller_selected")
    missing_trace = _seed_ticket(
        backend, trace_id=None, now=BASE + timedelta(seconds=1)  # type: ignore[arg-type]
    )
    service = _service(backend)

    with pytest.raises(SupportPublicIntakeReceiptInvalid, match="initial ticket"):
        service.create(wrong_source.ticket_id, now=BASE + timedelta(seconds=2))
    with pytest.raises(SupportPublicIntakeReceiptInvalid, match="request trace"):
        service.create(missing_trace.ticket_id, now=BASE + timedelta(seconds=2))


def test_store_failure_is_unavailable_not_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = InMemoryStateStore()
    ticket = _seed_ticket(backend)
    service = _service(backend)
    service.create(ticket.ticket_id, now=BASE + timedelta(seconds=1))

    def unavailable(*_args: object, **_kwargs: object) -> LedgerRecord | None:
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(backend, "get", unavailable)
    with pytest.raises(SupportPublicIntakeReceiptUnavailable, match="store"):
        service.read(ticket.ticket_id)


def test_historical_key_retention_revalidates_and_removal_fails_unavailable() -> None:
    backend = InMemoryStateStore()
    ticket = _seed_ticket(backend)
    old_service = _service(backend)
    receipt = old_service.create(
        ticket.ticket_id, now=BASE + timedelta(seconds=1)
    )

    rotated = CustomerProductionPseudonymizer(
        {KEY_A_ID: KEY_A, KEY_B_ID: KEY_B}, active_key_id=KEY_B_ID
    )
    assert _service(backend, pseudonymizer=rotated).read(ticket.ticket_id) == receipt

    without_history = CustomerProductionPseudonymizer(
        {KEY_B_ID: KEY_B}, active_key_id=KEY_B_ID
    )
    with pytest.raises(
        SupportPublicIntakeReceiptUnavailable, match="historical integrity key"
    ):
        _service(backend, pseudonymizer=without_history).read(ticket.ticket_id)


def test_new_receipt_cannot_be_backfilled_after_ticket_lifecycle_moves() -> None:
    backend = InMemoryStateStore()
    tickets = StateStoreSupportTicketStore(backend)
    ticket = _seed_ticket(backend)
    tickets.save(ticket.route(owner="support-owner", now=BASE + timedelta(minutes=1)))

    with pytest.raises(SupportPublicIntakeReceiptInvalid, match="lifecycle movement"):
        _service(backend).create(
            ticket.ticket_id, now=BASE + timedelta(minutes=2)
        )
