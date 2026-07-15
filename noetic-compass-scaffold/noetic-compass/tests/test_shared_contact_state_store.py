from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import threading
from types import SimpleNamespace

import pytest

from api.services.crm import (
    CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    JsonlFileLeadStore,
    Lead,
    LeadSubmission,
    NullCRMProvider,
    StateStoreLeadStore,
    build_lead_store,
    migrate_jsonl_leads_once,
)
from api.services.crm.state_store import CRM_LEAD_JSONL_MIGRATION_ID
from api.services.production.state_substrate import (
    InMemoryStateStore,
    LeaseExpired,
    UnknownLease,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.revisioned_contact_store import (
    CONTACT_MIGRATION_KIND,
    CONTACT_STATE_TENANT,
    DomainRevisionConflict,
    RevisionedContactStoreError,
)
from api.services.support_ticket_state_store import (
    SUPPORT_TICKET_JSONL_MIGRATION_ID,
    StateStoreSupportTicketStore,
    migrate_jsonl_support_tickets_once,
)
from api.services.support_tickets import (
    JsonlSupportTicketStore,
    SUPPORT_PRIVACY_URL,
    SUPPORT_TICKET_SCHEMA_VERSION_V1,
    SupportTicketService,
    build_support_ticket_service,
)


BASE = datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC)
PRIVACY_VERSION = "privacy-2026-07-15"
PRIVACY_SHA256 = "c" * 64


class _RenewalRequiredStore(InMemoryStateStore):
    """Hostile backend that expires migration authority between list scans."""

    def __init__(self) -> None:
        super().__init__()
        self.migration_token: str | None = None
        self.renewed_for_scan = False
        self.renew_calls = 0

    def acquire_lease(self, tenant_id, resource_id, **kwargs):
        lease = super().acquire_lease(tenant_id, resource_id, **kwargs)
        if resource_id.startswith("contact-migration:"):
            self.migration_token = lease.token
            self.renewed_for_scan = False
        return lease

    def renew_lease(self, token, **kwargs):
        lease = super().renew_lease(token, **kwargs)
        if token == self.migration_token:
            self.renew_calls += 1
            self.renewed_for_scan = True
        return lease

    def list(self, tenant_id, kind):
        if self.migration_token is not None:
            if not self.renewed_for_scan:
                raise LeaseExpired("hostile migration lease expired before list scan")
            self.renewed_for_scan = False
        return super().list(tenant_id, kind)


class _RenewalAndCleanupFailureStore(InMemoryStateStore):
    def __init__(self) -> None:
        super().__init__()
        self.migration_token: str | None = None

    def acquire_lease(self, tenant_id, resource_id, **kwargs):
        lease = super().acquire_lease(tenant_id, resource_id, **kwargs)
        if resource_id.startswith("contact-migration:"):
            self.migration_token = lease.token
        return lease

    def renew_lease(self, token, **kwargs):
        if token == self.migration_token:
            raise LeaseExpired("primary migration renewal expired")
        return super().renew_lease(token, **kwargs)

    def release_lease(self, token):
        if token == self.migration_token:
            raise UnknownLease("secondary cleanup token is unknown")
        return super().release_lease(token)


def _lead() -> Lead:
    submission = LeadSubmission(
        email="customer@example.com",
        name="Customer",
        organization="Example Org",
        message="Please send the Evidence Packet details.",
        interest="cas_harness",
        consent_to_contact=True,
        privacy_notice_version=PRIVACY_VERSION,
        privacy_notice_content_sha256=PRIVACY_SHA256,
        privacy_notice_publication_status=CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    ).validated()
    return Lead.from_submission(submission, source="test", trace_id="req-lead-1")


def _support_fields() -> dict[str, object]:
    return {
        "email": "customer@example.com",
        "name": "Customer",
        "organization": "Example Org",
        "subject": "Evidence Packet question",
        "message": "Please help verify the exact receipt.",
        "category": "product_support",
        "source": "test",
        "consent_to_contact": True,
        "privacy_notice_version": PRIVACY_VERSION,
        "privacy_notice_content_sha256": PRIVACY_SHA256,
        "privacy_notice_publication_status": CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        "trace_id": "req-support-1",
    }


def _stamp(offset: timedelta = timedelta(0)) -> str:
    return (BASE + offset).isoformat().replace("+00:00", "Z")


def _legacy_support_history() -> list[dict[str, object]]:
    ticket_id = "sup_legacy_shared_contact"
    received: dict[str, object] = {
        "ticket_id": ticket_id,
        "created_at_utc": _stamp(),
        "updated_at_utc": _stamp(),
        "version": 1,
        "status": "received",
        "email": "customer@example.com",
        "name": "Customer",
        "organization": "Example Org",
        "subject": "Evidence Packet question",
        "message": "Please help verify the exact receipt.",
        "category": "product_support",
        "source": "legacy-test",
        "consent_to_contact": True,
        "privacy_url": SUPPORT_PRIVACY_URL,
        "trace_id": "legacy-support-request",
        "owner": None,
        "routed_at_utc": None,
        "acknowledged_at_utc": None,
        "resolved_at_utc": None,
        "resolution_summary": None,
        "schema_version": SUPPORT_TICKET_SCHEMA_VERSION_V1,
    }
    routed_at = _stamp(timedelta(minutes=1))
    routed = {
        **received,
        "updated_at_utc": routed_at,
        "version": 2,
        "status": "routed",
        "owner": "support-a",
        "routed_at_utc": routed_at,
    }
    acknowledged_at = _stamp(timedelta(minutes=2))
    acknowledged = {
        **routed,
        "updated_at_utc": acknowledged_at,
        "version": 3,
        "status": "acknowledged",
        "acknowledged_at_utc": acknowledged_at,
    }
    resolved_at = _stamp(timedelta(minutes=3))
    resolved = {
        **acknowledged,
        "updated_at_utc": resolved_at,
        "version": 4,
        "status": "resolved",
        "resolved_at_utc": resolved_at,
        "resolution_summary": "Customer confirmed the packet receipt.",
    }
    return [received, routed, acknowledged, resolved]


def _write_jsonl(path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _assert_no_support_migration_state(
    backend: InMemoryStateStore,
    destination: StateStoreSupportTicketStore,
    ticket_id: str,
) -> None:
    assert destination.list_all() == []
    assert destination.list_revisions(ticket_id) == []
    assert (
        backend.get(
            CONTACT_STATE_TENANT,
            CONTACT_MIGRATION_KIND,
            SUPPORT_TICKET_JSONL_MIGRATION_ID,
        )
        is None
    )


def _assert_no_lead_migration_state(
    backend: InMemoryStateStore,
    destination: StateStoreLeadStore,
    lead_id: str,
) -> None:
    assert destination.list_all() == []
    assert destination.list_revisions(lead_id) == []
    assert (
        backend.get(
            CONTACT_STATE_TENANT,
            CONTACT_MIGRATION_KIND,
            CRM_LEAD_JSONL_MIGRATION_ID,
        )
        is None
    )


def test_shared_lead_store_preserves_revisions_and_atomic_pipeline_updates() -> None:
    backend = InMemoryStateStore()
    store = StateStoreLeadStore(backend)
    captured = _lead()
    annotated = captured.with_sync_result(NullCRMProvider().sync_lead(captured))
    store.save(captured)
    store.save(annotated)

    barrier = threading.Barrier(2)
    failures: list[BaseException] = []

    def update(status: str) -> None:
        try:
            barrier.wait(timeout=5)
            store.update_pipeline_status(captured.lead_id, status)
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    threads = [
        threading.Thread(target=update, args=("contacted",)),
        threading.Thread(target=update, args=("qualified",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert failures == []
    assert all(not thread.is_alive() for thread in threads)
    head = store.get(captured.lead_id)
    assert head is not None
    assert head.version == 4
    assert head.pipeline_status in {"contacted", "qualified"}
    assert [item.version for item in store.list_revisions(captured.lead_id)] == [
        1,
        2,
        3,
        4,
    ]


def test_shared_lead_store_rejects_non_v1_initial_direct_save() -> None:
    store = StateStoreLeadStore(InMemoryStateStore())
    invalid_initial = replace(_lead(), version=2)

    with pytest.raises(RevisionedContactStoreError, match="begin with domain revision 1"):
        store.save(invalid_initial)

    assert store.list_all() == []
    assert store.list_revisions(invalid_initial.lead_id) == []


def test_shared_lead_store_rejects_skipped_direct_save_revision() -> None:
    store = StateStoreLeadStore(InMemoryStateStore())
    captured = _lead()
    store.save(captured)

    with pytest.raises(RevisionedContactStoreError, match="increase exactly once"):
        store.save(replace(captured, version=3))

    assert store.get(captured.lead_id) == captured
    assert store.list_revisions(captured.lead_id) == [captured]


def test_shared_lead_store_preserves_concurrent_sync_and_pipeline_changes() -> None:
    store = StateStoreLeadStore(InMemoryStateStore())
    captured = _lead()
    store.save(captured)
    sync_result = NullCRMProvider().sync_lead(captured)
    barrier = threading.Barrier(2)
    failures: list[BaseException] = []

    def apply(operation) -> None:
        try:
            barrier.wait(timeout=5)
            operation()
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    threads = [
        threading.Thread(
            target=apply,
            args=(lambda: store.record_sync_result(captured.lead_id, sync_result),),
        ),
        threading.Thread(
            target=apply,
            args=(lambda: store.update_pipeline_status(captured.lead_id, "contacted"),),
        ),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    head = store.get(captured.lead_id)
    assert failures == []
    assert head is not None
    assert head.version == 3
    assert head.sync_status == "sync_pending"
    assert head.pipeline_status == "contacted"


def test_shared_support_store_serializes_domain_transitions() -> None:
    backend = InMemoryStateStore()
    store = StateStoreSupportTicketStore(backend)
    stamps = iter(
        [
            BASE,
            BASE + timedelta(minutes=1),
            BASE + timedelta(minutes=2),
        ]
    )
    clock_lock = threading.Lock()

    def clock() -> datetime:
        with clock_lock:
            return next(stamps)

    service = SupportTicketService(store, clock=clock)
    received = service.receive(**_support_fields())
    barrier = threading.Barrier(2)
    failures: list[BaseException] = []

    def route(owner: str) -> None:
        try:
            barrier.wait(timeout=5)
            service.route(received.ticket_id, owner=owner)
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    threads = [
        threading.Thread(target=route, args=("support-a",)),
        threading.Thread(target=route, args=("support-b",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert failures == []
    head = store.get(received.ticket_id)
    assert head is not None and head.version == 3 and head.status == "routed"
    assert head.owner in {"support-a", "support-b"}
    assert [item.version for item in store.list_revisions(received.ticket_id)] == [
        1,
        2,
        3,
    ]


def test_shared_contact_heads_and_revisions_survive_backend_reopen(tmp_path) -> None:
    database = tmp_path / "contact-state.sqlite3"
    backend = SqliteStateStore(database)
    lead_store = StateStoreLeadStore(backend)
    support_store = StateStoreSupportTicketStore(backend)
    lead = _lead()
    lead_store.save(lead)
    ticket = SupportTicketService(
        support_store, clock=lambda: BASE
    ).receive(**_support_fields())
    backend.close()

    reopened = SqliteStateStore(database)
    assert StateStoreLeadStore(reopened).get(lead.lead_id) == lead
    assert StateStoreSupportTicketStore(reopened).get(ticket.ticket_id) == ticket
    reopened.close()


def test_shared_store_rejects_conflicting_immutable_domain_revision() -> None:
    store = StateStoreLeadStore(InMemoryStateStore())
    captured = _lead()
    store.save(captured)

    with pytest.raises(DomainRevisionConflict, match="different content"):
        store.save(replace(captured, name="Different content"))


def test_shared_builders_require_and_reuse_the_lifespan_state_store(tmp_path) -> None:
    backend = InMemoryStateStore()
    lead_store = build_lead_store(
        SimpleNamespace(
            crm_lead_store_backend="state_store",
            crm_lead_store_path=str(tmp_path / "absent-leads.jsonl"),
        ),
        state_store=backend,
    )
    support_service = build_support_ticket_service(
        SimpleNamespace(
            support_ticket_store_backend="state_store",
            support_ticket_store_path=str(tmp_path / "absent-support.jsonl"),
        ),
        state_store=backend,
    )

    assert isinstance(lead_store, StateStoreLeadStore)
    assert support_service.is_durable is True
    assert lead_store.state_store is backend

    with pytest.raises(RuntimeError, match="requires the shared StateStore"):
        build_lead_store(
            SimpleNamespace(
                crm_lead_store_backend="state_store",
                crm_lead_store_path=None,
            )
        )
    with pytest.raises(RuntimeError, match="requires the shared StateStore"):
        build_support_ticket_service(
            SimpleNamespace(
                support_ticket_store_backend="state_store",
                support_ticket_store_path=None,
            )
        )


def test_lead_jsonl_migration_has_exact_parity_and_is_idempotent(tmp_path) -> None:
    path = tmp_path / "leads.jsonl"
    source = JsonlFileLeadStore(path)
    captured = _lead()
    annotated = captured.with_sync_result(NullCRMProvider().sync_lead(captured))
    source.save(captured)
    source.save(annotated)

    destination = StateStoreLeadStore(InMemoryStateStore())
    first = migrate_jsonl_leads_once(str(path), destination)
    second = migrate_jsonl_leads_once(str(path), destination)

    assert first["already_completed"] is False
    assert first["line_count"] == 2
    assert first["revision_count"] == 2
    assert first["head_count"] == 1
    assert second == {**first, "already_completed": True}
    assert destination.get(captured.lead_id) == annotated
    assert destination.list_revisions(captured.lead_id) == [captured, annotated]


def test_missing_jsonl_source_gets_an_explicit_empty_absence_receipt(tmp_path) -> None:
    path = tmp_path / "missing-leads.jsonl"
    destination = StateStoreLeadStore(InMemoryStateStore())

    first = migrate_jsonl_leads_once(str(path), destination)
    second = migrate_jsonl_leads_once(str(path), destination)

    assert first["already_completed"] is False
    assert first["source_present"] is False
    assert first["line_count"] == 0
    assert first["revision_count"] == 0
    assert first["head_count"] == 0
    assert second == {**first, "already_completed": True}
    assert destination.list_all() == []

    # A file appearing later is a changed source, even if it is empty. Refuse to
    # ingest possible stale disk state after shared-store authority was chosen.
    path.write_text("", encoding="utf-8")
    with pytest.raises(RevisionedContactStoreError, match="does not match"):
        migrate_jsonl_leads_once(str(path), destination)


def test_migration_renews_lease_during_hostile_destination_scans(tmp_path) -> None:
    backend = _RenewalRequiredStore()
    destination = StateStoreLeadStore(backend)

    receipt = migrate_jsonl_leads_once(
        str(tmp_path / "missing-leads.jsonl"), destination
    )

    assert receipt["source_present"] is False
    assert receipt["already_completed"] is False
    assert backend.renew_calls >= 6


def test_expired_migration_renewal_is_not_masked_by_cleanup_failure(tmp_path) -> None:
    destination = StateStoreLeadStore(_RenewalAndCleanupFailureStore())

    with pytest.raises(LeaseExpired, match="primary migration renewal expired"):
        migrate_jsonl_leads_once(
            str(tmp_path / "missing-leads.jsonl"), destination
        )


def test_support_jsonl_migration_has_exact_parity_and_is_idempotent(tmp_path) -> None:
    path = tmp_path / "support.jsonl"
    source_service = SupportTicketService(
        JsonlSupportTicketStore(path),
        clock=iter(
            [
                BASE,
                BASE + timedelta(minutes=1),
                BASE + timedelta(minutes=2),
            ]
        ).__next__,
    )
    received = source_service.receive(**_support_fields())
    source_service.route(received.ticket_id, owner="support-a")
    acknowledged = source_service.acknowledge(
        received.ticket_id, actor="support-a"
    )
    assert acknowledged is not None

    destination = StateStoreSupportTicketStore(InMemoryStateStore())
    first = migrate_jsonl_support_tickets_once(str(path), destination)
    second = migrate_jsonl_support_tickets_once(str(path), destination)

    assert first["already_completed"] is False
    assert first["revision_count"] == 3
    assert second == {**first, "already_completed": True}
    assert destination.get(received.ticket_id) == acknowledged
    assert [item.version for item in destination.list_revisions(received.ticket_id)] == [
        1,
        2,
        3,
    ]


def test_legacy_support_jsonl_valid_complete_history_migrates(tmp_path) -> None:
    path = tmp_path / "legacy-support-valid.jsonl"
    rows = _legacy_support_history()
    _write_jsonl(path, rows)
    destination = StateStoreSupportTicketStore(InMemoryStateStore())

    receipt = migrate_jsonl_support_tickets_once(str(path), destination)

    head = destination.get(str(rows[0]["ticket_id"]))
    assert receipt["revision_count"] == 4
    assert head is not None
    assert head.schema_version == SUPPORT_TICKET_SCHEMA_VERSION_V1
    assert head.version == 4
    assert head.status == "resolved"


def test_legacy_support_jsonl_rejects_resolved_to_routed_regression(tmp_path) -> None:
    path = tmp_path / "legacy-support-regression.jsonl"
    rows = _legacy_support_history()
    rerouted_at = _stamp(timedelta(minutes=4))
    rows.append(
        {
            **rows[1],
            "updated_at_utc": rerouted_at,
            "version": 5,
            "owner": "support-b",
            "routed_at_utc": rerouted_at,
        }
    )
    _write_jsonl(path, rows)
    destination = StateStoreSupportTicketStore(InMemoryStateStore())

    with pytest.raises(
        RevisionedContactStoreError,
        match="lifecycle transition .*resolved.*routed.* invalid",
    ):
        migrate_jsonl_support_tickets_once(str(path), destination)

    assert destination.list_all() == []


def test_legacy_support_jsonl_rejects_lifecycle_timestamp_rollback(tmp_path) -> None:
    path = tmp_path / "legacy-support-lifecycle-rollback.jsonl"
    rows = _legacy_support_history()[:3]
    rows.append(
        {
            **rows[2],
            "version": 4,
            "owner": "support-b",
            "routed_at_utc": _stamp(timedelta(seconds=30)),
        }
    )
    _write_jsonl(path, rows)
    destination = StateStoreSupportTicketStore(InMemoryStateStore())

    with pytest.raises(
        RevisionedContactStoreError,
        match="lifecycle transition .*acknowledged.*acknowledged.* invalid",
    ):
        migrate_jsonl_support_tickets_once(str(path), destination)

    assert destination.list_all() == []


def test_legacy_support_jsonl_rejects_lifecycle_field_rewrite(tmp_path) -> None:
    path = tmp_path / "legacy-support-lifecycle-rewrite.jsonl"
    rows = _legacy_support_history()
    rows[3] = {
        **rows[3],
        "routed_at_utc": _stamp(timedelta(minutes=1, seconds=30)),
    }
    _write_jsonl(path, rows)
    destination = StateStoreSupportTicketStore(InMemoryStateStore())

    with pytest.raises(
        RevisionedContactStoreError,
        match="lifecycle transition .*acknowledged.*resolved.* invalid",
    ):
        migrate_jsonl_support_tickets_once(str(path), destination)

    assert destination.list_all() == []


def test_legacy_support_jsonl_rejects_immutable_field_change(tmp_path) -> None:
    path = tmp_path / "legacy-support-immutable-change.jsonl"
    rows = _legacy_support_history()[:2]
    rows[1] = {**rows[1], "subject": "Tampered subject"}
    _write_jsonl(path, rows)
    destination = StateStoreSupportTicketStore(InMemoryStateStore())

    with pytest.raises(RevisionedContactStoreError, match="changed immutable"):
        migrate_jsonl_support_tickets_once(str(path), destination)

    assert destination.list_all() == []


def test_jsonl_migration_rejects_corruption_before_any_destination_write(
    tmp_path,
) -> None:
    path = tmp_path / "corrupt-leads.jsonl"
    lead = _lead()
    path.write_text(
        json.dumps(lead.to_dict(), sort_keys=True) + "\n{broken-json\n",
        encoding="utf-8",
    )
    destination = StateStoreLeadStore(InMemoryStateStore())

    with pytest.raises(RevisionedContactStoreError, match="invalid JSON"):
        migrate_jsonl_leads_once(str(path), destination)

    assert destination.list_all() == []


def test_jsonl_migration_rejects_duplicate_keys_before_any_destination_write(
    tmp_path,
) -> None:
    path = tmp_path / "duplicate-key-leads.jsonl"
    payload = _lead().to_dict()
    payload["metadata"] = {"placeholder": 0}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    hostile_key = "customer@example.com-private-key"
    duplicate = encoded.replace(
        '"placeholder":0',
        f"{json.dumps(hostile_key)}:1,{json.dumps(hostile_key)}:1",
    )
    assert duplicate != encoded
    path.write_text(duplicate + "\n", encoding="utf-8")
    backend = InMemoryStateStore()
    destination = StateStoreLeadStore(backend)

    with pytest.raises(
        RevisionedContactStoreError, match="duplicate JSON key"
    ) as exc_info:
        migrate_jsonl_leads_once(str(path), destination)

    assert hostile_key not in str(exc_info.value)
    _assert_no_lead_migration_state(
        backend, destination, str(payload["lead_id"])
    )


def test_support_jsonl_migration_rejects_duplicate_key_without_partial_state(
    tmp_path,
) -> None:
    path = tmp_path / "duplicate-key-support.jsonl"
    rows = _legacy_support_history()[:2]
    encoded = json.dumps(rows[1], sort_keys=True, separators=(",", ":"))
    hostile_value = "customer+duplicate@example.com"
    original_email = json.dumps(rows[1]["email"])
    email_field = f'"email":{original_email}'
    duplicate = encoded.replace(
        email_field,
        f'"email":{json.dumps(hostile_value)},{email_field}',
    )
    assert duplicate != encoded
    path.write_text(
        json.dumps(rows[0], sort_keys=True) + "\n" + duplicate + "\n",
        encoding="utf-8",
    )
    backend = InMemoryStateStore()
    destination = StateStoreSupportTicketStore(backend)

    with pytest.raises(
        RevisionedContactStoreError, match="duplicate JSON key"
    ) as exc_info:
        migrate_jsonl_support_tickets_once(str(path), destination)

    assert hostile_value not in str(exc_info.value)
    _assert_no_support_migration_state(
        backend, destination, str(rows[0]["ticket_id"])
    )


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity", "1e10000"])
def test_jsonl_migration_rejects_nonfinite_numbers_before_destination_write(
    tmp_path, constant: str
) -> None:
    path = tmp_path / "nonfinite-leads.jsonl"
    payload = _lead().to_dict()
    payload["metadata"] = {"hostile_number": 0}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    hostile = encoded.replace(
        '"hostile_number":0', f'"hostile_number":{constant}'
    )
    assert hostile != encoded
    path.write_text(hostile + "\n", encoding="utf-8")
    backend = InMemoryStateStore()
    destination = StateStoreLeadStore(backend)

    with pytest.raises(RevisionedContactStoreError, match="non-finite JSON"):
        migrate_jsonl_leads_once(str(path), destination)

    _assert_no_lead_migration_state(
        backend, destination, str(payload["lead_id"])
    )


def test_support_jsonl_migration_rejects_nonfinite_without_partial_state(
    tmp_path,
) -> None:
    path = tmp_path / "nonfinite-support.jsonl"
    rows = _legacy_support_history()[:2]
    encoded = json.dumps(rows[1], sort_keys=True, separators=(",", ":"))
    hostile = encoded.replace('"version":2', '"version":NaN,"version":2')
    assert hostile != encoded
    path.write_text(
        json.dumps(rows[0], sort_keys=True) + "\n" + hostile + "\n",
        encoding="utf-8",
    )
    backend = InMemoryStateStore()
    destination = StateStoreSupportTicketStore(backend)

    with pytest.raises(RevisionedContactStoreError, match="non-finite JSON"):
        migrate_jsonl_support_tickets_once(str(path), destination)

    _assert_no_support_migration_state(
        backend, destination, str(rows[0]["ticket_id"])
    )


def test_jsonl_migration_wraps_oversized_integer_value_error_without_raw_input(
    tmp_path,
) -> None:
    path = tmp_path / "oversized-integer-leads.jsonl"
    oversized_integer = "9" * 10_000
    path.write_text('{"version":' + oversized_integer + "}\n", encoding="utf-8")
    destination = StateStoreLeadStore(InMemoryStateStore())

    with pytest.raises(
        RevisionedContactStoreError, match="invalid JSON at line 1"
    ) as exc_info:
        migrate_jsonl_leads_once(str(path), destination)

    assert oversized_integer[:100] not in str(exc_info.value)
    assert destination.list_all() == []


def test_support_jsonl_migration_rejects_tampered_v2_source(tmp_path) -> None:
    path = tmp_path / "tampered-support.jsonl"
    ticket = SupportTicketService(
        JsonlSupportTicketStore(tmp_path / "source-support.jsonl"),
        clock=lambda: BASE,
    ).receive(**_support_fields())
    payload = ticket.to_dict()
    payload["privacy_notice_content_sha256"] = "not-a-sha256"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    destination = StateStoreSupportTicketStore(InMemoryStateStore())

    with pytest.raises(RevisionedContactStoreError, match="cannot be decoded"):
        migrate_jsonl_support_tickets_once(str(path), destination)

    assert destination.list_all() == []


def test_jsonl_migration_rejects_changed_source_after_marker(tmp_path) -> None:
    path = tmp_path / "changed-leads.jsonl"
    lead = _lead()
    source = JsonlFileLeadStore(path)
    source.save(lead)
    destination = StateStoreLeadStore(InMemoryStateStore())
    migrate_jsonl_leads_once(str(path), destination)

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(lead.to_dict(), sort_keys=True) + "\n")

    with pytest.raises(RevisionedContactStoreError, match="does not match"):
        migrate_jsonl_leads_once(str(path), destination)


def test_jsonl_migration_rejects_conflicting_unmarked_destination(tmp_path) -> None:
    path = tmp_path / "conflicting-leads.jsonl"
    lead = _lead()
    JsonlFileLeadStore(path).save(lead)
    destination = StateStoreLeadStore(InMemoryStateStore())
    destination.save(replace(lead, name="Conflicting destination"))

    with pytest.raises(RevisionedContactStoreError, match="outside"):
        migrate_jsonl_leads_once(str(path), destination)
