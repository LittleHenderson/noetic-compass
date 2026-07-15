from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest

from api.services.crm import (
    CRM_CONSENT_SCHEMA_VERSION,
    CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    CRM_PRIVACY_NOTICE_URL,
    CRM_SCHEMA_VERSION,
    CRMSyncResult,
    CRMVerificationReceipt,
    Lead,
    LeadSubmission,
)
from api.services.customer_production_pseudonyms import (
    PSEUDONYMIZATION_SCHEME,
    CustomerProductionPseudonymizer,
)
from api.services.production.state_substrate import LedgerRecord
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from api.services.revisioned_contact_store import (
    CONTACT_MIGRATION_KIND,
    CONTACT_MIGRATION_SCHEMA_VERSION,
    CONTACT_STATE_TENANT,
)
from api.services.support_ticket_state_store import (
    SUPPORT_TICKET_JSONL_MIGRATION_ID,
    StateStoreSupportTicketStore,
)
from api.services.support_public_intake_receipts import (
    SupportPublicIntakeReceiptStore,
)
from api.services.support_tickets import SupportTicket


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "collect_airtable_crm_acceptance_source.py"
)
SPEC = importlib.util.spec_from_file_location("airtable_crm_source_collector", MODULE_PATH)
assert SPEC and SPEC.loader
collector_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = collector_module
SPEC.loader.exec_module(collector_module)

FINALIZER_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_support_crm_acceptance_evidence.py"
)
FINALIZER_SPEC = importlib.util.spec_from_file_location(
    "support_crm_acceptance_finalizer", FINALIZER_MODULE_PATH
)
assert FINALIZER_SPEC and FINALIZER_SPEC.loader
finalizer_module = importlib.util.module_from_spec(FINALIZER_SPEC)
sys.modules[FINALIZER_SPEC.name] = finalizer_module
FINALIZER_SPEC.loader.exec_module(finalizer_module)


FIXED_NOW = datetime(2026, 7, 15, 0, 2, tzinfo=UTC)
MASTER_SHA = "a" * 40
DEPLOY_ID = "dep-d9ba0km7r5hc73e9ojkg"
NONCE = "0123456789abcdef01234567"
LEAD_ID = "lead-0123456789abcdef"
EXTERNAL_ID = "rec0123456789ABCD"
PRIVACY_VERSION = "privacy-2026-07-15"
CONSENT_AT = "2026-07-15T00:02:00Z"
VERIFIED_AT = "2026-07-15T00:02:00Z"
RESPONSE_DIGEST = "sha256:" + ("b" * 64)
PRIVACY_BODY = b"<!doctype html><title>Final privacy notice</title>"
PRIVACY_CONTENT_SHA256 = collector_module._digest_bytes(PRIVACY_BODY)
PSEUDONYM_KEY_ID = "cpk_0123456789abcdef0123456789abcdef"
PSEUDONYM_KEY = hashlib.sha256(b"crm-collector-test-key").digest()
PSEUDONYM_KEYRING = json.dumps(
    {
        PSEUDONYM_KEY_ID: "base64url:"
        + base64.urlsafe_b64encode(PSEUDONYM_KEY).rstrip(b"=").decode("ascii")
    },
    separators=(",", ":"),
)


def _runtime_env() -> dict[str, str]:
    return {
        "RENDER_SERVICE_ID": collector_module.PRODUCTION_SERVICE_ID,
        "RENDER_GIT_COMMIT": MASTER_SHA,
        "RENDER_API_KEY": "rnd-secret-never-output",
        "NC_CRM_PROVIDER": "airtable",
        "NC_CRM_LEAD_STORE_PATH": collector_module.PRODUCTION_LEAD_STORE_PATH,
        "NC_CRM_LEAD_STORE_BACKEND": "state_store",
        "NC_STATE_LEDGER_ENABLED": "true",
        "NC_STATE_LEDGER_READ_AUTHORITY": "true",
        "NC_DATABASE_URL": "postgresql://test.invalid/test",
        "NC_CUSTOMER_PRODUCTION_PSEUDONYM_KEYRING_JSON": PSEUDONYM_KEYRING,
        "NC_CUSTOMER_PRODUCTION_PSEUDONYM_ACTIVE_KEY_ID": PSEUDONYM_KEY_ID,
        "NC_AIRTABLE_TOKEN": "pat-secret-never-output",
        "NC_AIRTABLE_BASE_ID": collector_module.PRODUCTION_AIRTABLE_BASE_ID,
        "NC_AIRTABLE_TABLE_NAME": collector_module.PRODUCTION_AIRTABLE_TABLE_NAME,
        "NC_AIRTABLE_API_BASE_URL": collector_module.CANONICAL_AIRTABLE_API_BASE_URL,
        "NC_AIRTABLE_DEDUP_FIELD": collector_module.PRODUCTION_AIRTABLE_DEDUP_FIELD,
        "NC_AIRTABLE_OWNER_FIELD": collector_module.PRODUCTION_AIRTABLE_OWNER_FIELD,
        "NC_AIRTABLE_OWNER_VALUE": collector_module.PRODUCTION_AIRTABLE_OWNER_VALUE,
        "NC_AIRTABLE_LIFECYCLE_FIELD": collector_module.PRODUCTION_AIRTABLE_LIFECYCLE_FIELD,
        "NC_CRM_PRIVACY_NOTICE_PUBLICATION_STATUS": (
            CRM_PRIVACY_NOTICE_PRESENT_STATUS
        ),
        "NC_CRM_PRIVACY_NOTICE_VERSION": PRIVACY_VERSION,
        "NC_CRM_PRIVACY_NOTICE_CONTENT_SHA256": PRIVACY_CONTENT_SHA256,
    }


def _synced_lead(**overrides: Any) -> Lead:
    captured = Lead.from_submission(
        LeadSubmission(
            email=f"crm-acceptance-{NONCE}@acceptance.invalid",
            interest="cas_harness",
            metadata={"probe": "support_crm"},
            consent_to_contact=True,
            privacy_notice_version=PRIVACY_VERSION,
            privacy_notice_content_sha256=PRIVACY_CONTENT_SHA256,
            privacy_notice_publication_status=CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        ).validated(),
        source="customer_production_acceptance_probe",
        trace_id="req-collector",
    )
    # Reconstruct the capture with deterministic consent evidence for timestamp assertions.
    captured = Lead(
        **{
            **captured.__dict__,
            "lead_id": LEAD_ID,
            "consent_recorded_at_utc": CONSENT_AT,
        }
    )
    receipt = CRMVerificationReceipt(
        provider="airtable",
        readback_verified=True,
        deduplicated=True,
        owner_assigned=True,
        lifecycle_stage="new",
        verified_at=VERIFIED_AT,
        response_digest=RESPONSE_DIGEST,
    )
    synced = captured.with_sync_result(
        CRMSyncResult(
            provider="airtable",
            synced=True,
            is_real=True,
            external_id=EXTERNAL_ID,
            synced_at=VERIFIED_AT,
            verification_receipt=receipt,
        )
    )
    if not overrides:
        return synced
    return Lead(**{**synced.__dict__, **overrides})


def _response(**overrides: Any) -> dict[str, Any]:
    value = {
        "lead_id": LEAD_ID,
        "captured": True,
        "sync_status": "synced",
        "synced": True,
        "schema_version": CRM_SCHEMA_VERSION,
        "consent_to_contact": True,
        "privacy_notice_url": CRM_PRIVACY_NOTICE_URL,
        "privacy_notice_version": PRIVACY_VERSION,
        "privacy_notice_content_sha256": PRIVACY_CONTENT_SHA256,
        "privacy_notice_publication_status": CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        "consent_recorded_at_utc": CONSENT_AT,
        "consent_schema_version": CRM_CONSENT_SCHEMA_VERSION,
        "message": "received",
    }
    value.update(overrides)
    return value


def _http_result(
    value: object,
    *,
    status: int = 200,
    content_type: str = "application/json",
    raw: bytes | None = None,
):
    body = raw if raw is not None else json.dumps(value).encode("utf-8")
    return collector_module.HttpResult(
        status=status,
        headers={"content-type": content_type},
        body=body,
    )


def _collector(
    tmp_path: Path,
    *,
    response: dict[str, Any] | None = None,
    lead: Lead | None = None,
    environment: dict[str, str] | None = None,
):
    expected_response = _response() if response is None else response
    expected_lead = _synced_lead() if lead is None else lead

    def transport(**kwargs):
        path = kwargs["path"]
        if path == f"/v1/services/{collector_module.PRODUCTION_SERVICE_ID}":
            return _http_result(
                {
                    "id": collector_module.PRODUCTION_SERVICE_ID,
                    "name": collector_module.PRODUCTION_SERVICE_NAME,
                    "type": "web_service",
                    "repo": collector_module.REPOSITORY_URL,
                    "branch": "master",
                    "autoDeployTrigger": "checksPass",
                    "serviceDetails": {
                        "disk": {
                            "id": collector_module.PRODUCTION_DISK_ID,
                            "name": collector_module.PRODUCTION_DISK_NAME,
                            "mountPath": collector_module.PRODUCTION_DISK_MOUNT_PATH,
                            "sizeGB": 1,
                        }
                    },
                }
            )
        if path == (
            f"/v1/services/{collector_module.PRODUCTION_SERVICE_ID}/deploys/{DEPLOY_ID}"
        ):
            return _http_result(
                {
                    "id": DEPLOY_ID,
                    "status": "live",
                    "trigger": "service_updated",
                    "commit": {"id": MASTER_SHA},
                    "finishedAt": "2026-07-15T00:01:30Z",
                }
            )
        if path == "/privacy":
            return _http_result(
                {}, content_type="text/html; charset=utf-8", raw=PRIVACY_BODY
            )
        assert kwargs["base_url"] == collector_module.PRODUCTION_API_ORIGIN
        assert path == collector_module.PUBLIC_LEAD_PATH
        assert kwargs["method"] == "POST"
        assert kwargs["payload"]["consent_to_contact"] is True
        assert "privacy_notice_version" not in kwargs["payload"]
        assert kwargs["payload"]["email"].endswith("@acceptance.invalid")
        return _http_result(expected_response)

    def read_lead(path: str, lead_id: str):
        assert path == collector_module.PRODUCTION_LEAD_STORE_PATH
        assert lead_id == LEAD_ID
        return expected_lead

    return collector_module.AirtableCRMSourceCollector(
        base_url=collector_module.PRODUCTION_API_ORIGIN,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        runtime_environment=(
            _runtime_env() if environment is None else environment
        ),
        transport=transport,
        lead_reader=read_lead,
        clock=lambda: FIXED_NOW,
        nonce=NONCE,
    )


def test_collects_provider_bound_pii_free_open_fragment(tmp_path: Path) -> None:
    source, fragment, selector = _collector(tmp_path).collect()

    assert source["provider"] == "airtable"
    assert source["adapter_response_digest"] == RESPONSE_DIGEST
    assert source["lead_subject"].startswith("hmac-sha256:")
    assert source["trace_subject"].startswith("hmac-sha256:")
    assert "trace_id_sha256" not in source
    assert source["airtable_record_subject"].startswith("hmac-sha256:")
    assert source["render_deploy_status"] == "live"
    assert source["render_deploy_commit_sha"] == MASTER_SHA
    assert source["airtable_base_id"] == collector_module.PRODUCTION_AIRTABLE_BASE_ID
    assert source["airtable_owner_value"] == collector_module.PRODUCTION_AIRTABLE_OWNER_VALUE
    assert source["lead_store_backend"] == "state_store"
    assert source["state_store_backend"] == "postgres"
    assert fragment["status"] == "OPEN"
    assert fragment["source_receipt"] == source
    assert collector_module._digest_bytes(
        collector_module._canonical_bytes(fragment["source_receipt"])
    ) == fragment["source_receipt_sha256"]
    assert fragment["missing_required_evidence"] == ["resolved_support_ticket_sla"]
    assert fragment["crm_lead"] == {
        "system": "airtable",
        "provider": "airtable",
        "lead_subject": source["lead_subject"],
        "airtable_record_subject": source["airtable_record_subject"],
        "adapter_response_digest": RESPONSE_DIGEST,
        "source_receipt_sha256": fragment["source_receipt_sha256"],
        "persisted": True,
        "readback_verified": True,
        "deduplicated": True,
        "owner_assigned": True,
        "lifecycle_stage": "new",
        "verified_at_utc": VERIFIED_AT,
    }
    assert fragment["consent"] == {
        "capture_consent_recorded": True,
        "consent_to_contact": True,
        "source_attribution_recorded": True,
        "privacy_notice_linked": True,
        "privacy_notice_url": CRM_PRIVACY_NOTICE_URL,
        "privacy_notice_version": PRIVACY_VERSION,
        "privacy_notice_content_sha256": PRIVACY_CONTENT_SHA256,
        "privacy_notice_publication_status": CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        "consent_schema_version": CRM_CONSENT_SCHEMA_VERSION,
        "recorded_at_utc": CONSENT_AT,
    }
    assert selector == {
        "schema_version": collector_module.PRIVATE_LEAD_SELECTOR_SCHEMA_VERSION,
        "gate": "support_crm",
        "crm_lead_id": LEAD_ID,
    }
    rendered = json.dumps([source, fragment], sort_keys=True)
    assert "@acceptance.invalid" not in rendered
    assert LEAD_ID not in rendered
    assert "req-collector" not in rendered
    assert EXTERNAL_ID not in rendered
    assert "pat-secret" not in rendered


@pytest.mark.parametrize(
    "change",
    [
        {"synced": False},
        {"sync_status": "sync_pending"},
        {"schema_version": "noetic_crm.v1"},
        {"consent_to_contact": False},
        {"privacy_notice_url": "https://example.invalid/privacy"},
        {"privacy_notice_version": "stale"},
        {"privacy_notice_content_sha256": "c" * 64},
        {"privacy_notice_publication_status": "OPEN"},
    ],
)
def test_public_capture_response_must_be_exactly_bound(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    with pytest.raises(
        collector_module.CRMCollectionFailure,
        match="capture response did not prove",
    ):
        _collector(tmp_path, response=_response(**change)).collect()


def test_public_capture_response_rejects_extra_fields(tmp_path: Path) -> None:
    with pytest.raises(collector_module.CRMCollectionFailure, match="fields drifted"):
        _collector(tmp_path, response=_response(raw_email="do-not-accept")).collect()


@pytest.mark.parametrize(
    "overrides",
    [
        {"source": "other"},
        {"trace_id": None},
        {"sync_status": "sync_pending", "external_id": None},
        {"consent_to_contact": False, "schema_version": "noetic_crm.v1"},
        {"privacy_notice_version": "stale"},
        {"privacy_notice_content_sha256": "c" * 64},
        {
            "privacy_notice_publication_status": "OPEN",
            "schema_version": "noetic_crm.v1",
        },
        {"consent_recorded_at_utc": "2026-07-15T00:00:01Z"},
    ],
)
def test_durable_lead_must_match_public_capture(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    lead = _synced_lead(**overrides)
    with pytest.raises(collector_module.CRMCollectionFailure, match="durable lead"):
        _collector(tmp_path, lead=lead).collect()


def test_missing_durable_lead_fails_closed(tmp_path: Path) -> None:
    collector = _collector(tmp_path)
    collector.lead_reader = lambda path, lead_id: None

    with pytest.raises(collector_module.CRMCollectionFailure, match="not durable"):
        collector.collect()


@pytest.mark.parametrize(
    "receipt_override",
    [
        {"provider": "hubspot"},
        {"readback_verified": False},
        {"response_digest": "b" * 64},
        {"lifecycle_stage": "qualified"},
    ],
)
def test_adapter_receipt_must_be_airtable_bound(
    tmp_path: Path, receipt_override: dict[str, Any]
) -> None:
    # Invalid receipt objects are blocked at construction; use a minimal duck-typed object to
    # prove the collector independently rejects corrupt persisted state.
    receipt = type(
        "CorruptReceipt",
        (),
        {
            "provider": "airtable",
            "readback_verified": True,
            "deduplicated": True,
            "owner_assigned": True,
            "lifecycle_stage": "new",
            "verified_at": VERIFIED_AT,
            "response_digest": RESPONSE_DIGEST,
            **receipt_override,
        },
    )()
    lead = _synced_lead()
    object.__setattr__(lead, "verification_receipt", receipt)

    with pytest.raises(
        collector_module.CRMCollectionFailure, match="incomplete or cross-wired"
    ):
        _collector(tmp_path, lead=lead).collect()


def test_airtable_record_id_is_keyed_only_after_shape_validation(tmp_path: Path) -> None:
    with pytest.raises(collector_module.CRMCollectionFailure, match="record ID is invalid"):
        _collector(tmp_path, lead=_synced_lead(external_id="not-airtable")).collect()


def test_timestamp_order_fails_closed(tmp_path: Path) -> None:
    lead = _synced_lead(consent_recorded_at_utc="2026-07-15T00:02:01Z")
    with pytest.raises(collector_module.CRMCollectionFailure, match="not monotonic"):
        _collector(
            tmp_path,
            lead=lead,
            response=_response(consent_recorded_at_utc="2026-07-15T00:02:01Z"),
        ).collect()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("RENDER_GIT_COMMIT", "c" * 40, "runtime commit"),
        ("RENDER_SERVICE_ID", "srv-other", "pinned production service"),
        ("NC_CRM_PROVIDER", "null", "not exact airtable"),
        ("NC_AIRTABLE_TOKEN", "", "provider token is absent"),
        ("RENDER_API_KEY", "", "required for exact live deploy proof"),
        (
            "NC_AIRTABLE_API_BASE_URL",
            "https://evil.invalid/v0",
            "does not match the exact production contract",
        ),
        (
            "NC_CRM_LEAD_STORE_BACKEND",
            "auto",
            "must be exact state_store",
        ),
        ("NC_STATE_LEDGER_READ_AUTHORITY", "false", "must be exact true"),
        ("NC_DATABASE_URL", "sqlite:///tmp.db", "requires shared Postgres"),
    ],
)
def test_runtime_and_provider_binding_fail_closed(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    environment = _runtime_env()
    environment[field] = value

    with pytest.raises(collector_module.CRMCollectionFailure, match=message):
        _collector(tmp_path, environment=environment)


def test_open_privacy_notice_fails_before_public_lead_persistence(tmp_path: Path) -> None:
    environment = _runtime_env()
    environment["NC_CRM_PRIVACY_NOTICE_PUBLICATION_STATUS"] = "OPEN"
    collector = _collector(tmp_path, environment=environment)
    original_transport = collector.transport
    public_posts = 0

    def transport(**kwargs):
        nonlocal public_posts
        if kwargs["path"] == collector_module.PUBLIC_LEAD_PATH:
            public_posts += 1
        return original_transport(**kwargs)

    collector.transport = transport
    with pytest.raises(
        collector_module.CRMCollectionFailure, match="publication remains OPEN"
    ):
        collector.collect()
    assert public_posts == 0


@pytest.mark.parametrize(
    "deploy_change",
    [
        {"status": "deactivated"},
        {"commit": {"id": "c" * 40}},
        {"id": "dep-other"},
    ],
)
def test_render_deploy_must_be_exact_live_commit(
    tmp_path: Path, deploy_change: dict[str, Any]
) -> None:
    collector = _collector(tmp_path)
    original_transport = collector.transport

    def transport(**kwargs):
        if kwargs["path"].endswith(f"/deploys/{DEPLOY_ID}"):
            deploy = {
                "id": DEPLOY_ID,
                "status": "live",
                "trigger": "service_updated",
                "commit": {"id": MASTER_SHA},
                "finishedAt": "2026-07-15T00:01:30Z",
            }
            deploy.update(deploy_change)
            return _http_result(deploy)
        return original_transport(**kwargs)

    collector.transport = transport
    with pytest.raises(
        collector_module.CRMCollectionFailure, match="not the live production deploy"
    ):
        collector.collect()


def test_live_privacy_bytes_must_match_server_owned_digest(tmp_path: Path) -> None:
    collector = _collector(tmp_path)
    original_transport = collector.transport

    def transport(**kwargs):
        if kwargs["path"] == "/privacy":
            return _http_result(
                {}, content_type="text/html", raw=b"different final notice"
            )
        return original_transport(**kwargs)

    collector.transport = transport
    with pytest.raises(
        collector_module.CRMCollectionFailure, match="do not match the server-owned"
    ):
        collector.collect()


def test_fragment_tampering_breaks_source_receipt_binding(tmp_path: Path) -> None:
    source, fragment, _selector = _collector(tmp_path).collect()
    fragment["crm_lead"]["adapter_response_digest"] = "sha256:" + ("c" * 64)

    with pytest.raises(collector_module.CRMCollectionFailure, match="diverged"):
        collector_module._validate_output_pair(source, fragment)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pseudonymization_scheme", "hmac-sha512-v1"),
        ("pseudonym_key_id", "cpk_fedcba9876543210fedcba9876543210"),
    ],
)
def test_fragment_pseudonym_metadata_cannot_crosswire_source_receipt(
    tmp_path: Path, field: str, value: str
) -> None:
    source, fragment, _selector = _collector(tmp_path).collect()
    fragment[field] = value

    with pytest.raises(
        collector_module.CRMCollectionFailure, match="pseudonym metadata diverged"
    ):
        collector_module._validate_output_pair(source, fragment)


def test_embedded_source_receipt_is_rehashed_not_shape_checked(tmp_path: Path) -> None:
    source, fragment, _selector = _collector(tmp_path).collect()
    fragment["source_receipt"]["render_deploy_trigger"] = "manual"

    with pytest.raises(collector_module.CRMCollectionFailure, match="embedded source"):
        collector_module._validate_output_pair(source, fragment)


def test_airtable_contract_tampering_breaks_embedded_receipt(tmp_path: Path) -> None:
    source, fragment, _selector = _collector(tmp_path).collect()
    source["airtable_owner_value"] = "Someone Else"
    fragment["source_receipt"] = dict(source)
    rebound = collector_module._digest_bytes(collector_module._canonical_bytes(source))
    fragment["source_receipt_sha256"] = rebound
    fragment["crm_lead"]["source_receipt_sha256"] = rebound

    with pytest.raises(
        collector_module.CRMCollectionFailure, match="production contract drifted"
    ):
        collector_module._validate_output_pair(source, fragment)


def test_atomic_output_is_owner_only_and_canonical(tmp_path: Path) -> None:
    source, _fragment, _selector = _collector(tmp_path).collect()
    target = tmp_path / "receipt.json"

    collector_module._atomic_write(target, source)

    assert json.loads(target.read_text(encoding="utf-8")) == source
    if os.name != "nt":
        assert target.stat().st_mode & 0o777 == 0o600


def test_duplicate_json_response_is_rejected(tmp_path: Path) -> None:
    collector = _collector(tmp_path)
    collector.transport = lambda **kwargs: _http_result(
        {}, raw=b'{"lead_id":"one","lead_id":"two"}'
    )

    with pytest.raises(collector_module.CRMCollectionFailure, match="duplicate JSON key"):
        collector.collect()


def test_production_image_contains_the_bounded_collector() -> None:
    dockerfile = (MODULE_PATH.parent.parent / "Dockerfile.api").read_text(encoding="utf-8")
    assert (
        "COPY scripts/collect_airtable_crm_acceptance_source.py "
        "scripts/collect_airtable_crm_acceptance_source.py"
    ) in dockerfile


def _support_marker() -> LedgerRecord:
    return LedgerRecord.new(
        tenant_id=CONTACT_STATE_TENANT,
        kind=CONTACT_MIGRATION_KIND,
        record_id=SUPPORT_TICKET_JSONL_MIGRATION_ID,
        payload={
            "schema_version": CONTACT_MIGRATION_SCHEMA_VERSION,
            "domain": "support_ticket",
            "source_present": False,
            "source_sha256": hashlib.sha256(b"").hexdigest(),
            "line_count": 0,
            "revision_count": 0,
            "head_count": 0,
            "records_sha256": hashlib.sha256(b"[]").hexdigest(),
        },
        source="contact_jsonl_migration",
        now=FIXED_NOW,
    )


def _resolved_support_ticket(
    store: InMemoryStateStore,
    *,
    pseudonymizer: CustomerProductionPseudonymizer,
    resolve: bool = True,
    create_receipt: bool = True,
) -> SupportTicket:
    store.put(_support_marker(), expected_version=0)
    tickets = StateStoreSupportTicketStore(store)
    received = SupportTicket.receive(
        email="private-support@example.test",
        name="Private Support Person",
        organization="Private Support Org",
        subject="Production support",
        message="Please help",
        category="support",
        source="cascompass_contact",
        consent_to_contact=True,
        privacy_notice_version=PRIVACY_VERSION,
        privacy_notice_content_sha256=PRIVACY_CONTENT_SHA256,
        privacy_notice_publication_status=CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        trace_id="trace-private-ticket-collector-finalizer",
        now=FIXED_NOW - timedelta(minutes=2),
    )
    tickets.save(received)
    if create_receipt:
        SupportPublicIntakeReceiptStore(
            store, pseudonymizer=pseudonymizer
        ).create(received.ticket_id, now=FIXED_NOW - timedelta(minutes=2))
    routed = received.route(owner="support-owner", now=FIXED_NOW - timedelta(minutes=1))
    tickets.save(routed)
    acknowledged = routed.acknowledge(
        actor="support-owner", now=FIXED_NOW - timedelta(seconds=30)
    )
    tickets.save(acknowledged)
    if not resolve:
        return acknowledged
    resolved = acknowledged.resolve(
        actor="support-owner",
        summary="Resolved against durable source",
        now=FIXED_NOW,
    )
    tickets.save(resolved)
    return resolved


def _finalize(
    tmp_path: Path,
    *,
    resolve_ticket: bool = True,
    create_receipt: bool = True,
    lead_selector_override: str | None = None,
    ticket_selector_extra: Mapping[str, object] | None = None,
):
    source, fragment, lead_selector = _collector(tmp_path).collect()
    backend = InMemoryStateStore()
    pseudonymizer = CustomerProductionPseudonymizer(
        {PSEUDONYM_KEY_ID: PSEUDONYM_KEY}, active_key_id=PSEUDONYM_KEY_ID
    )
    ticket = _resolved_support_ticket(
        backend,
        pseudonymizer=pseudonymizer,
        resolve=resolve_ticket,
        create_receipt=create_receipt,
    )
    if lead_selector_override is not None:
        lead_selector = {**lead_selector, "crm_lead_id": lead_selector_override}
    ticket_selector = {
        "schema_version": (
            finalizer_module.PRIVATE_TICKET_SELECTOR_SCHEMA_VERSION
        ),
        "gate": "support_crm",
        "support_ticket_id": ticket.ticket_id,
    }
    if ticket_selector_extra is not None:
        ticket_selector.update(ticket_selector_extra)
    result = finalizer_module.build(
        source_receipt=source,
        fragment=fragment,
        private_lead_selector=lead_selector,
        private_ticket_selector=ticket_selector,
        store=backend,
        pseudonymizer=pseudonymizer,
        support_ack_sla_seconds=600,
        now=FIXED_NOW + timedelta(minutes=1),
    )
    return result, ticket


def test_finalizer_builds_authority_valid_pseudonymous_evidence(
    tmp_path: Path,
) -> None:
    (evidence, artifact, selector), ticket = _finalize(tmp_path)

    rendered_public = json.dumps([evidence, artifact], sort_keys=True)
    assert ticket.ticket_id not in rendered_public
    assert LEAD_ID not in rendered_public
    assert selector == {
        "schema_version": finalizer_module.PRIVATE_SELECTOR_SCHEMA_VERSION,
        "gate": "support_crm",
        "support_ticket_id": ticket.ticket_id,
        "crm_lead_id": LEAD_ID,
    }
    assert evidence["pseudonymization_scheme"] == (
        PSEUDONYMIZATION_SCHEME
    )
    assert evidence["pseudonym_key_id"] == PSEUDONYM_KEY_ID
    assert evidence["support_ticket"]["ticket_record_version"] == ticket.version
    assert evidence["crm_source_receipt"]["schema_version"] == (
        "cas_harness_airtable_crm_acceptance_source.v3"
    )
    assert all(
        legacy not in rendered_public
        for legacy in (
            "ticket_id_sha256",
            "lead_id_sha256",
            "airtable_record_id_sha256",
        )
    )


def test_finalizer_rejects_unresolved_ticket(tmp_path: Path) -> None:
    with pytest.raises(
        finalizer_module.SupportCRMFinalizationFailure,
        match="not a resolved within-SLA",
    ):
        _finalize(tmp_path, resolve_ticket=False)


def test_finalizer_rejects_cross_wired_private_lead_selector(tmp_path: Path) -> None:
    with pytest.raises(
        finalizer_module.SupportCRMFinalizationFailure, match="cross-wired"
    ):
        _finalize(tmp_path, lead_selector_override="lead-private-cross-wire")


def test_finalizer_rejects_direct_seed_without_public_intake_receipt(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        finalizer_module.SupportCRMFinalizationFailure,
        match="public-intake receipt is absent or invalid",
    ):
        _finalize(tmp_path, create_receipt=False)


def test_finalizer_rejects_self_asserted_create_http_status(tmp_path: Path) -> None:
    with pytest.raises(
        finalizer_module.SupportCRMFinalizationFailure,
        match="private support-ticket selector is invalid",
    ):
        _finalize(tmp_path, ticket_selector_extra={"create_http_status": 201})
