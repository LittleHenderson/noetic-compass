"""Hostile source-binding tests for support/CRM acceptance evidence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json

import pytest

from api.services.crm.models import (
    CRM_CONSENT_SCHEMA_VERSION,
    CRM_SCHEMA_VERSION,
    CRMVerificationReceipt,
    Lead,
)
from api.services.crm.privacy import (
    CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    CRM_PRIVACY_NOTICE_URL,
)
from api.services.crm.state_store import (
    CRM_LEAD_JSONL_MIGRATION_ID,
    StateStoreLeadStore,
)
from api.services.customer_production_pseudonyms import (
    AIRTABLE_RECORD_DOMAIN,
    CRM_LEAD_DOMAIN,
    SUPPORT_TICKET_DOMAIN,
    SUPPORT_CRM_REQUEST_TRACE_DOMAIN,
    CustomerProductionPseudonymizer,
)
from api.services.production.state_substrate import LedgerRecord
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from api.services.revisioned_contact_store import (
    CONTACT_MIGRATION_KIND,
    CONTACT_MIGRATION_SCHEMA_VERSION,
    CONTACT_STATE_TENANT,
)
from api.services.support_crm_acceptance_binding import (
    BINDING_KIND,
    BINDING_TENANT_ID,
    PRIVATE_SELECTOR_SCHEMA_VERSION,
    SupportCRMAcceptanceSourceBindingStore,
    SupportCRMSourceBindingInvalid,
    SupportCRMSourceBindingUnavailable,
    validate_support_crm_private_selector,
)
from api.services.support_ticket_state_store import (
    SUPPORT_TICKET_JSONL_MIGRATION_ID,
    StateStoreSupportTicketStore,
)
from api.services.support_public_intake_receipts import (
    RECEIPT_KIND,
    SupportPublicIntakeReceiptStore,
)
from api.services.support_tickets import SupportTicket


NOW = datetime(2026, 7, 15, 18, 0, tzinfo=UTC)
KEY_ID = "cpk_0123456789abcdef0123456789abcdef"
KEY = hashlib.sha256(b"support-crm-source-binding-test-key").digest()
PSEUDONYMIZER = CustomerProductionPseudonymizer(
    {KEY_ID: KEY}, active_key_id=KEY_ID
)
SLA_SECONDS = 600
LEAD_ID = "lead-private-source-001"
AIRTABLE_ID = "recPrivateSource001"
TRACE_ID = "trace-private-support-crm-001"
NOTICE_SHA = hashlib.sha256(b"published-privacy-notice").hexdigest()


def _stamp(offset_minutes: int) -> str:
    return (NOW + timedelta(minutes=offset_minutes)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _migration_marker(migration_id: str, domain: str) -> LedgerRecord:
    return LedgerRecord.new(
        tenant_id=CONTACT_STATE_TENANT,
        kind=CONTACT_MIGRATION_KIND,
        record_id=migration_id,
        payload={
            "schema_version": CONTACT_MIGRATION_SCHEMA_VERSION,
            "domain": domain,
            "source_present": False,
            "source_sha256": hashlib.sha256(b"").hexdigest(),
            "line_count": 0,
            "revision_count": 0,
            "head_count": 0,
            "records_sha256": hashlib.sha256(b"[]").hexdigest(),
        },
        source="contact_jsonl_migration",
        now=NOW,
    )


def _lead_history(store: StateStoreLeadStore) -> Lead:
    lead = Lead(
        email="private@example.test",
        lead_id=LEAD_ID,
        created_at=_stamp(0),
        updated_at=_stamp(0),
        version=1,
        source="cascompass_contact",
        trace_id=TRACE_ID,
        name="Private Person",
        organization="Private Org",
        message="Private message",
        interest="audit",
        metadata={"probe": "support_crm"},
        consent_to_contact=True,
        privacy_notice_url=CRM_PRIVACY_NOTICE_URL,
        privacy_notice_version="2026-07-15",
        privacy_notice_content_sha256=NOTICE_SHA,
        privacy_notice_publication_status=CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        consent_recorded_at_utc=_stamp(0),
        consent_schema_version=CRM_CONSENT_SCHEMA_VERSION,
        sync_status="captured",
        pipeline_status="new",
        schema_version=CRM_SCHEMA_VERSION,
    )
    store.save(lead)
    receipt = CRMVerificationReceipt(
        readback_verified=True,
        deduplicated=True,
        owner_assigned=True,
        lifecycle_stage="new",
        verified_at=_stamp(3),
        response_digest="sha256:" + hashlib.sha256(b"airtable-response").hexdigest(),
    )
    synced = replace(
        lead,
        updated_at=_stamp(3),
        version=2,
        sync_status="synced",
        external_id=AIRTABLE_ID,
        verification_receipt=receipt,
    )
    store.save(synced)
    return synced


def _ticket_history(
    store: StateStoreSupportTicketStore,
    public_intake_receipts: SupportPublicIntakeReceiptStore,
) -> SupportTicket:
    received = SupportTicket.receive(
        email="support@example.test",
        name="Support Person",
        organization="Support Org",
        subject="Production support",
        message="Please help",
        category="support",
        source="cascompass_contact",
        consent_to_contact=True,
        privacy_notice_version="2026-07-15",
        privacy_notice_content_sha256=NOTICE_SHA,
        privacy_notice_publication_status=CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        trace_id="trace-private-ticket-001",
        now=NOW,
    )
    store.save(received)
    public_intake_receipts.create(received.ticket_id, now=NOW)
    routed = received.route(owner="support-owner", now=NOW + timedelta(minutes=1))
    store.save(routed)
    acknowledged = routed.acknowledge(
        actor="support-owner", now=NOW + timedelta(minutes=5)
    )
    store.save(acknowledged)
    resolved = acknowledged.resolve(
        actor="support-owner",
        summary="Resolved against durable source",
        now=NOW + timedelta(minutes=7),
    )
    store.save(resolved)
    return resolved


def _evidence(ticket: SupportTicket, lead: Lead) -> dict[str, object]:
    assert lead.verification_receipt is not None
    receipt = lead.verification_receipt
    metadata = PSEUDONYMIZER.metadata()
    lead_subject = PSEUDONYMIZER.subject(
        domain=CRM_LEAD_DOMAIN,
        tenant_scope=CONTACT_STATE_TENANT,
        value=lead.lead_id,
    )
    airtable_subject = PSEUDONYMIZER.subject(
        domain=AIRTABLE_RECORD_DOMAIN,
        tenant_scope=CONTACT_STATE_TENANT,
        value=str(lead.external_id),
    )
    source = {
        "schema_version": "cas_harness_airtable_crm_acceptance_source.v3",
        **metadata,
        "lead_subject": lead_subject,
        "airtable_record_subject": airtable_subject,
        "provider": "airtable",
        "lead_store_backend": "state_store",
        "state_store_backend": "postgres",
        "state_store_read_authority": True,
        "lead_migration_marker_verified": True,
        "lead_head_revision_verified": True,
        "lead_schema_version": lead.schema_version,
        "lead_record_version": lead.version,
        "persisted": True,
        "readback_verified": True,
        "deduplicated": True,
        "owner_assigned": True,
        "lifecycle_stage": receipt.lifecycle_stage,
        "verified_at_utc": receipt.verified_at,
        "adapter_response_digest": receipt.response_digest,
        "trace_subject": PSEUDONYMIZER.subject(
            domain=SUPPORT_CRM_REQUEST_TRACE_DOMAIN,
            tenant_scope=CONTACT_STATE_TENANT,
            value=TRACE_ID,
        ),
        "consent_to_contact": True,
        "consent_schema_version": lead.consent_schema_version,
        "consent_recorded_at_utc": lead.consent_recorded_at_utc,
        "privacy_notice_url": lead.privacy_notice_url,
        "privacy_notice_version": lead.privacy_notice_version,
        "privacy_notice_content_sha256": lead.privacy_notice_content_sha256,
        "privacy_notice_publication_status": (
            lead.privacy_notice_publication_status
        ),
        "source_attribution_recorded": True,
        # Content/high-entropy digests remain ordinary SHA-256 values.
        "airtable_contract_sha256": hashlib.sha256(b"contract").hexdigest(),
        "render_service_response_sha256": hashlib.sha256(b"service").hexdigest(),
    }
    source_sha = hashlib.sha256(
        json.dumps(
            source,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
    ).hexdigest()
    return {
        "schema_version": "cas_harness_customer_production_gate_evidence.v3",
        "gate": "support_crm",
        **metadata,
        "support_ticket": {
            "ticket_subject": PSEUDONYMIZER.subject(
                domain=SUPPORT_TICKET_DOMAIN,
                tenant_scope=CONTACT_STATE_TENANT,
                value=ticket.ticket_id,
            ),
            "ticket_record_version": ticket.version,
            "create_http_status": 201,
            "persisted": True,
            "routed": True,
            "acknowledged": True,
            "first_response_minutes": 5,
            "sla_minutes": 10,
            "resolution_recorded": True,
            "resolved_at_utc": ticket.resolved_at_utc,
        },
        "crm_lead": {
            "system": "airtable",
            "provider": "airtable",
            "lead_subject": lead_subject,
            "airtable_record_subject": airtable_subject,
            "adapter_response_digest": receipt.response_digest,
            "source_receipt_sha256": source_sha,
            "persisted": True,
            "readback_verified": True,
            "deduplicated": True,
            "owner_assigned": True,
            "lifecycle_stage": receipt.lifecycle_stage,
            "verified_at_utc": receipt.verified_at,
        },
        "consent": {
            "capture_consent_recorded": True,
            "consent_to_contact": True,
            "source_attribution_recorded": True,
            "privacy_notice_linked": True,
            "privacy_notice_url": lead.privacy_notice_url,
            "privacy_notice_version": lead.privacy_notice_version,
            "privacy_notice_content_sha256": lead.privacy_notice_content_sha256,
            "privacy_notice_publication_status": (
                lead.privacy_notice_publication_status
            ),
            "consent_schema_version": lead.consent_schema_version,
            "recorded_at_utc": lead.consent_recorded_at_utc,
        },
        "crm_source_receipt": source,
    }


def _fixture():
    backend = InMemoryStateStore()
    backend.put(
        _migration_marker(SUPPORT_TICKET_JSONL_MIGRATION_ID, "support_ticket"),
        expected_version=0,
    )
    backend.put(
        _migration_marker(CRM_LEAD_JSONL_MIGRATION_ID, "crm_lead"),
        expected_version=0,
    )
    leads = StateStoreLeadStore(backend)
    tickets = StateStoreSupportTicketStore(backend)
    public_intake_receipts = SupportPublicIntakeReceiptStore(
        backend, pseudonymizer=PSEUDONYMIZER
    )
    lead = _lead_history(leads)
    ticket = _ticket_history(tickets, public_intake_receipts)
    binding = SupportCRMAcceptanceSourceBindingStore(
        backend,
        leads=leads,
        support_tickets=tickets,
        public_intake_receipts=public_intake_receipts,
        pseudonymizer=PSEUDONYMIZER,
        support_ack_sla_seconds=SLA_SECONDS,
    )
    selector = {
        "schema_version": PRIVATE_SELECTOR_SCHEMA_VERSION,
        "gate": "support_crm",
        "support_ticket_id": ticket.ticket_id,
        "crm_lead_id": lead.lead_id,
    }
    return backend, leads, tickets, lead, ticket, binding, selector


def test_valid_binding_is_idempotent_and_public_bytes_contain_no_raw_ids() -> None:
    backend, _, _, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)

    first = binding.create(evidence, selector=selector, now=NOW)
    second = binding.create(
        evidence, selector=selector, now=NOW + timedelta(minutes=1)
    )

    assert first == second
    binding.assert_matches(evidence, evidence_sha256=first)
    public = json.dumps(evidence, sort_keys=True)
    for raw in (ticket.ticket_id, lead.lead_id, AIRTABLE_ID, TRACE_ID):
        assert raw not in public
    source = evidence["crm_source_receipt"]
    consent = evidence["consent"]
    assert isinstance(source, dict)
    assert isinstance(consent, dict)
    assert str(source["trace_subject"]).startswith("hmac-sha256:")
    assert "trace_id_sha256" not in source
    assert consent["privacy_notice_content_sha256"] == NOTICE_SHA
    rows = backend.list(BINDING_TENANT_ID, BINDING_KIND)
    assert len(rows) == 1
    assert rows[0].payload["contact_authority_scope"] == CONTACT_STATE_TENANT
    assert rows[0].payload["support_ticket_id"] == ticket.ticket_id
    assert rows[0].payload["crm_lead_id"] == lead.lead_id


@pytest.mark.parametrize(
    ("container", "field"),
    [
        ("support_ticket", "ticket_subject"),
        ("crm_lead", "lead_subject"),
        ("crm_lead", "airtable_record_subject"),
        ("crm_source_receipt", "lead_subject"),
        ("crm_source_receipt", "trace_subject"),
    ],
)
def test_arbitrary_well_shaped_subjects_are_rejected(
    container: str, field: str
) -> None:
    _, _, _, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    evidence[container][field] = "hmac-sha256:" + "a" * 64  # type: ignore[index]

    with pytest.raises(SupportCRMSourceBindingInvalid, match=field):
        binding.create(evidence, selector=selector, now=NOW)


def test_selector_is_exact_and_cross_wired_ids_fail_closed() -> None:
    _, _, _, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    extra = {**selector, "extra": True}
    with pytest.raises(SupportCRMSourceBindingInvalid, match="selector schema"):
        validate_support_crm_private_selector(extra)

    crosswired = {**selector, "crm_lead_id": "lead-other-private-source"}
    with pytest.raises(SupportCRMSourceBindingInvalid, match="absent"):
        binding.create(evidence, selector=crosswired, now=NOW)


def test_legacy_unkeyed_hashes_and_raw_identifier_leaks_are_rejected() -> None:
    _, _, _, lead, ticket, binding, selector = _fixture()
    legacy = _evidence(ticket, lead)
    legacy_ticket = legacy["support_ticket"]
    assert isinstance(legacy_ticket, dict)
    legacy_ticket["ticket_id_sha256"] = hashlib.sha256(
        ticket.ticket_id.encode()
    ).hexdigest()
    with pytest.raises(SupportCRMSourceBindingInvalid, match="legacy unkeyed"):
        binding.create(legacy, selector=selector, now=NOW)

    legacy_trace = _evidence(ticket, lead)
    legacy_trace["crm_source_receipt"]["trace_id_sha256"] = hashlib.sha256(  # type: ignore[index]
        TRACE_ID.encode()
    ).hexdigest()
    with pytest.raises(SupportCRMSourceBindingInvalid, match="legacy unkeyed"):
        binding.create(legacy_trace, selector=selector, now=NOW)

    leaked = _evidence(ticket, lead)
    leaked["debug_reference"] = lead.lead_id
    with pytest.raises(SupportCRMSourceBindingInvalid, match="private source"):
        binding.create(leaked, selector=selector, now=NOW)

    leaked_request_trace = _evidence(ticket, lead)
    leaked_request_trace["debug_request_reference"] = ticket.trace_id
    with pytest.raises(SupportCRMSourceBindingInvalid, match="private source"):
        binding.create(leaked_request_trace, selector=selector, now=NOW)


def test_missing_public_intake_receipt_cannot_create_binding() -> None:
    backend, _, _, lead, ticket, binding, selector = _fixture()
    receipt = backend.list(CONTACT_STATE_TENANT, RECEIPT_KIND)[0]
    backend.delete(
        receipt.tenant_id,
        receipt.kind,
        receipt.record_id,
        expected_version=receipt.version,
    )

    with pytest.raises(SupportCRMSourceBindingInvalid, match="public-intake receipt"):
        binding.create(_evidence(ticket, lead), selector=selector, now=NOW)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("parent_ids", ("cross-wired-ticket-revision",)),
        ("trace_id", "cross-wired-request-trace"),
    ],
)
def test_active_binding_revalidates_exact_public_intake_receipt_envelope(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    backend, _, _, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    digest = binding.create(evidence, selector=selector, now=NOW)
    receipt = backend.list(CONTACT_STATE_TENANT, RECEIPT_KIND)[0]
    forged = replace(receipt, **{field: value})
    real_get = backend.get

    def forged_get(tenant_id, kind, record_id):  # type: ignore[no-untyped-def]
        if (tenant_id, kind, record_id) == (
            receipt.tenant_id,
            receipt.kind,
            receipt.record_id,
        ):
            return forged
        return real_get(tenant_id, kind, record_id)

    monkeypatch.setattr(backend, "get", forged_get)
    with pytest.raises(SupportCRMSourceBindingInvalid, match="public-intake receipt"):
        binding.assert_matches(evidence, evidence_sha256=digest)


def test_exact_pinned_lead_allows_valid_later_pipeline_transition() -> None:
    _, leads, _, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    digest = binding.create(evidence, selector=selector, now=NOW)

    later = replace(
        lead,
        version=lead.version + 1,
        updated_at=_stamp(9),
        pipeline_status="contacted",
    )
    leads.save(later)

    binding.assert_matches(evidence, evidence_sha256=digest)


def test_retained_historical_key_allows_later_pipeline_transition() -> None:
    backend, leads, tickets, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    digest = binding.create(evidence, selector=selector, now=NOW)
    leads.save(
        replace(
            lead,
            version=lead.version + 1,
            updated_at=_stamp(9),
            pipeline_status="contacted",
        )
    )
    rotated_key_id = "cpk_fedcba9876543210fedcba9876543210"
    rotated = CustomerProductionPseudonymizer(
        {
            KEY_ID: KEY,
            rotated_key_id: hashlib.sha256(b"rotated-support-key").digest(),
        },
        active_key_id=rotated_key_id,
    )
    rotated_binding = SupportCRMAcceptanceSourceBindingStore(
        backend,
        leads=leads,
        support_tickets=tickets,
        public_intake_receipts=SupportPublicIntakeReceiptStore(
            backend, pseudonymizer=rotated
        ),
        pseudonymizer=rotated,
        support_ack_sla_seconds=SLA_SECONDS,
    )

    rotated_binding.assert_matches(evidence, evidence_sha256=digest)


def test_changed_current_airtable_identity_invalidates_active_binding() -> None:
    _, leads, _, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    digest = binding.create(evidence, selector=selector, now=NOW)
    leads.save(
        replace(
            lead,
            version=lead.version + 1,
            updated_at=_stamp(9),
            external_id="recChangedPrivateSource",
        )
    )

    with pytest.raises(SupportCRMSourceBindingInvalid, match="lead head"):
        binding.assert_matches(evidence, evidence_sha256=digest)


@pytest.mark.parametrize(
    "row",
    ["ticket_head", "ticket_revision", "lead_head", "lead_revision"],
)
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", "forged_contact_source"),
        ("trace_id", "forged-contact-trace"),
        ("parent_ids", ("cross-wired-parent",)),
        ("tenant_id", "cross-wired-tenant"),
    ],
)
def test_active_binding_rejects_contact_ledger_envelope_tamper(
    monkeypatch: pytest.MonkeyPatch,
    row: str,
    field: str,
    value: object,
) -> None:
    backend, _, _, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    digest = binding.create(evidence, selector=selector, now=NOW)
    kind, record_id = {
        "ticket_head": ("support_ticket_head", ticket.ticket_id),
        "ticket_revision": (
            "support_ticket_revision",
            f"{ticket.ticket_id}:v{ticket.version}",
        ),
        "lead_head": ("crm_lead_head", lead.lead_id),
        "lead_revision": ("crm_lead_revision", f"{lead.lead_id}:v{lead.version}"),
    }[row]
    record = backend.get(CONTACT_STATE_TENANT, kind, record_id)
    assert record is not None
    forged = replace(record, **{field: value})
    real_get = backend.get

    def forged_get(tenant_id, requested_kind, requested_id):  # type: ignore[no-untyped-def]
        if (tenant_id, requested_kind, requested_id) == (
            CONTACT_STATE_TENANT,
            kind,
            record_id,
        ):
            return forged
        return real_get(tenant_id, requested_kind, requested_id)

    monkeypatch.setattr(backend, "get", forged_get)
    if row.startswith("ticket_"):
        with pytest.raises(
            SupportCRMSourceBindingInvalid, match="public-intake receipt"
        ):
            binding.assert_matches(evidence, evidence_sha256=digest)
    else:
        with pytest.raises(SupportCRMSourceBindingUnavailable, match="envelope"):
            binding.assert_matches(evidence, evidence_sha256=digest)


def test_missing_marker_and_corrupt_revision_fail_closed() -> None:
    backend, _, _, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    marker = backend.get(
        CONTACT_STATE_TENANT,
        CONTACT_MIGRATION_KIND,
        CRM_LEAD_JSONL_MIGRATION_ID,
    )
    assert marker is not None
    backend.delete(
        CONTACT_STATE_TENANT,
        CONTACT_MIGRATION_KIND,
        CRM_LEAD_JSONL_MIGRATION_ID,
        expected_version=marker.version,
    )
    with pytest.raises(SupportCRMSourceBindingUnavailable, match="marker"):
        binding.create(evidence, selector=selector, now=NOW)

    backend.put(
        _migration_marker(CRM_LEAD_JSONL_MIGRATION_ID, "crm_lead"),
        expected_version=0,
    )
    revision = backend.get(
        CONTACT_STATE_TENANT, "crm_lead_revision", f"{lead.lead_id}:v2"
    )
    assert revision is not None
    payload = deepcopy(dict(revision.payload))
    payload["item"]["external_id"] = "recCorruptPrivateSource"  # type: ignore[index]
    backend.put(revision.with_payload(payload), expected_version=revision.version)
    with pytest.raises(SupportCRMSourceBindingUnavailable, match="unavailable"):
        binding.create(evidence, selector=selector, now=NOW)


def test_historical_key_removal_and_store_error_fail_closed(monkeypatch) -> None:
    backend, leads, tickets, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    digest = binding.create(evidence, selector=selector, now=NOW)
    rotated_key_id = "cpk_fedcba9876543210fedcba9876543210"
    rotated = CustomerProductionPseudonymizer(
        {rotated_key_id: hashlib.sha256(b"rotated-support-key").digest()},
        active_key_id=rotated_key_id,
    )
    without_history = SupportCRMAcceptanceSourceBindingStore(
        backend,
        leads=leads,
        support_tickets=tickets,
        public_intake_receipts=SupportPublicIntakeReceiptStore(
            backend, pseudonymizer=rotated
        ),
        pseudonymizer=rotated,
        support_ack_sla_seconds=SLA_SECONDS,
    )
    with pytest.raises(SupportCRMSourceBindingUnavailable, match="key"):
        without_history.assert_matches(evidence, evidence_sha256=digest)

    def unavailable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(backend, "get", unavailable)
    with pytest.raises(SupportCRMSourceBindingUnavailable, match="store"):
        binding.assert_matches(evidence, evidence_sha256=digest)


def test_private_content_binding_hmac_tamper_fails_closed(monkeypatch) -> None:
    backend, _, _, lead, ticket, binding, selector = _fixture()
    evidence = _evidence(ticket, lead)
    digest = binding.create(evidence, selector=selector, now=NOW)
    record_id = f"support-crm-source-{digest}"
    record = backend.get(BINDING_TENANT_ID, BINDING_KIND, record_id)
    assert record is not None
    payload = dict(record.payload)
    payload["content_binding_hmac"] = "hmac-sha256:" + "a" * 64
    forged = replace(record, payload=payload)
    real_get = backend.get

    def forged_get(tenant_id, kind, requested_id):  # type: ignore[no-untyped-def]
        if (tenant_id, kind, requested_id) == (
            BINDING_TENANT_ID,
            BINDING_KIND,
            record_id,
        ):
            return forged
        return real_get(tenant_id, kind, requested_id)

    monkeypatch.setattr(backend, "get", forged_get)
    with pytest.raises(SupportCRMSourceBindingUnavailable, match="integrity"):
        binding.assert_matches(evidence, evidence_sha256=digest)


def test_sla_rounding_and_resolved_lifecycle_are_source_bound() -> None:
    _, _, _, lead, ticket, binding, selector = _fixture()
    wrong_sla = _evidence(ticket, lead)
    wrong_sla["support_ticket"]["first_response_minutes"] = 4  # type: ignore[index]
    with pytest.raises(SupportCRMSourceBindingInvalid, match="ticket facts"):
        binding.create(wrong_sla, selector=selector, now=NOW)

    wrong_version = _evidence(ticket, lead)
    wrong_version["support_ticket"]["ticket_record_version"] = 3  # type: ignore[index]
    with pytest.raises(SupportCRMSourceBindingInvalid, match="resolved ticket head"):
        binding.create(wrong_version, selector=selector, now=NOW)
