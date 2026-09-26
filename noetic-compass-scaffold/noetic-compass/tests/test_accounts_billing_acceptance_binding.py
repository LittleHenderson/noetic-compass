"""Source-bound accounts/billing acceptance evidence tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib

import pytest

from api.acceptance_authority_contract import (
    acceptance_authority_url,
)
from api.services.acceptance_publication_authorizations import (
    AcceptancePublicationAuthorizationStore,
)
from api.services.accounts.models import Account
from api.services.accounts_billing_acceptance_binding import (
    BINDING_KIND,
    BINDING_TENANT_ID,
    AccountsBillingAcceptanceSourceBindingStore,
    AccountsBillingSourceBindingInvalid,
    AccountsBillingSourceBindingUnavailable,
)
from api.services.billing_entitlements import (
    BILLING_PLATFORM_TENANT,
    CHECKOUT_COMPLETION_INDEX_KIND,
    CHECKOUT_SESSION_INDEX_KIND,
    CUSTOMER_INDEX_KIND,
    SUBSCRIPTION_INDEX_KIND,
    WEBHOOK_EVENT_KIND,
    BillingEntitlementStore,
    StripeSubscriptionProvenance,
    SubscriptionRecord,
)
from api.services.billing_reconciliation import PaidInvoiceReconciliationRecord
from api.services.customer_production_acceptance_authority import (
    AUTHORITY_TENANT_ID,
    HEAD_KIND,
    OPERATION_KIND,
    REVISION_KIND,
    AcceptanceAuthorityInvalid,
    CustomerProductionAcceptanceAuthorityStore,
    canonicalize_acceptance_evidence,
)
from api.services.customer_production_pseudonyms import (
    ACCOUNT_DOMAIN,
    BILLING_CUSTOMER_DOMAIN,
    BILLING_INVOICE_DOMAIN,
    BILLING_SUBSCRIPTION_DOMAIN,
    TENANT_DOMAIN,
    CustomerProductionPseudonymizer,
)
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from tests.billing_test_support import install_verified_stripe_subscription


NOW = datetime(2026, 7, 15, 18, 0, tzinfo=UTC)
MASTER = "a" * 40
DEPLOY = "dep-accountsbinding001"
TENANT_ID = "tenant-customer-production"
ACCOUNT_ID = "acct-0123456789abcdef0123456789abcdef"
INVOICE_RECORD_ID = "invoice-reconciliation-001"
KEY_ID = "cpk_0123456789abcdef0123456789abcdef"
KEY = hashlib.sha256(b"accounts-billing-pseudonym-test-key").digest()
PSEUDONYMIZER = CustomerProductionPseudonymizer(
    {KEY_ID: KEY}, active_key_id=KEY_ID
)


class _Accounts:
    def __init__(self, account: Account) -> None:
        self.account = account

    def get_account_by_id(self, account_id: str) -> Account | None:
        return self.account if self.account.account_id == account_id else None


class _Billing:
    def __init__(self, invoice: PaidInvoiceReconciliationRecord) -> None:
        self.invoice = invoice

    def get_invoice(
        self, tenant_id: str, invoice_record_id: str
    ) -> PaidInvoiceReconciliationRecord | None:
        if (
            self.invoice.tenant_id == tenant_id
            and self.invoice.invoice_record_id == invoice_record_id
        ):
            return self.invoice
        return None


class _Entitlements:
    def __init__(self, subscription: SubscriptionRecord) -> None:
        self.subscription = subscription

    def get_subscription(self, tenant_id: str) -> SubscriptionRecord | None:
        return self.subscription if self.subscription.tenant_id == tenant_id else None

    def assert_subscription_provenance(
        self, subscription: SubscriptionRecord
    ) -> StripeSubscriptionProvenance:
        return StripeSubscriptionProvenance(
            checkout_request_id=str(subscription.checkout_request_id),
            checkout_session_id=str(subscription.checkout_session_id),
            checkout_event_id=str(subscription.checkout_event_id),
            checkout_event_payload_sha256=str(
                subscription.checkout_event_payload_sha256
            ),
            checkout_lineage_sha256=str(subscription.checkout_lineage_sha256),
            provider_event_id=str(subscription.provider_event_id),
            provider_event_payload_sha256=str(
                subscription.provider_event_payload_sha256
            ),
            provider_refresh_facts_sha256=str(
                subscription.provider_refresh_facts_sha256
            ),
            provider_refreshed_object_sha256=str(
                subscription.provider_refreshed_object_sha256
            ),
            provider_refresh_fence=subscription.provider_refresh_fence,
            checkout_receipt_facts_sha256=hashlib.sha256(
                b"checkout-receipt-facts"
            ).hexdigest(),
            provider_receipt_facts_sha256=hashlib.sha256(
                b"provider-receipt-facts"
            ).hexdigest(),
        )


def _invoice() -> PaidInvoiceReconciliationRecord:
    stamp = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    digest = hashlib.sha256(b"provider-facts").hexdigest()
    return PaidInvoiceReconciliationRecord(
        tenant_id=TENANT_ID,
        billing_account_id=ACCOUNT_ID,
        invoice_record_id=INVOICE_RECORD_ID,
        external_invoice_id="in_live_customer_invoice_001",
        external_customer_id="cus_live_customer_001",
        external_subscription_id="sub_live_customer_001",
        provider_event_id="evt_live_customer_001",
        provider_event_created=1_784_139_600,
        invoice_created=1_784_139_000,
        invoice_finalized_at=1_784_139_300,
        provider_request_id="req_live_customer_001",
        provider_snapshot_sha256=hashlib.sha256(b"provider-snapshot").hexdigest(),
        provider_snapshot_facts_sha256=digest,
        provider_snapshot_retrieved_at=stamp,
        raw_event_sha256=hashlib.sha256(b"raw-event").hexdigest(),
        provider_event_facts_sha256=hashlib.sha256(b"event-facts").hexdigest(),
        hosted_invoice_url="https://invoice.stripe.com/i/acct_live/test",
        invoice_pdf="https://pay.stripe.com/invoice/acct_live/test/pdf",
        invoice_pdf_http_status=200,
        invoice_pdf_content_type="application/pdf",
        invoice_pdf_size_bytes=512,
        invoice_pdf_sha256=hashlib.sha256(b"invoice-pdf").hexdigest(),
        invoice_pdf_retrieved_at=stamp,
        provider_observation_count=1,
        currency="USD",
        amount_due_minor=1000,
        amount_paid_minor=1000,
        usage_price_id="price_live_customer_usage",
        meter_event_name="cas_harness_accelerator_milliseconds",
        meter_event_version="v1",
        livemode=True,
        usage_period_start=stamp,
        usage_period_end=stamp,
        paid_at=stamp,
        provider_quantity_milliseconds=1000,
        local_quantity_milliseconds=1000,
        usage_ids=("usage-001",),
        usage_set_sha256=hashlib.sha256(b"usage-set").hexdigest(),
        reconciliation_state="matched",
        unresolved_reason=None,
        reconciled_at=stamp,
        created_at=stamp,
        updated_at=stamp,
        ledger_version=1,
    )


def _account() -> Account:
    return Account(
        account_id=ACCOUNT_ID,
        email_or_username="private@example.test",
        role="owner",
        tenant_id=TENANT_ID,
    )


def _subscription() -> SubscriptionRecord:
    return SubscriptionRecord(
        tenant_id=TENANT_ID,
        plan_id="professional_live",
        status="active",
        source="stripe_verified",
        billing_account_id=ACCOUNT_ID,
        external_customer_id="cus_live_customer_001",
        external_subscription_id="sub_live_customer_001",
        current_period_start=NOW.isoformat(),
        current_period_end=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        provider_event_id="evt_live_customer_subscription_001",
        provider_event_created=1_784_139_500,
        checkout_request_id="request_live_customer_001",
        checkout_session_id="cs_live_customer_001",
        checkout_event_id="evt_checkout_live_customer_001",
        checkout_event_payload_sha256=hashlib.sha256(
            b"checkout-event"
        ).hexdigest(),
        checkout_lineage_sha256=hashlib.sha256(b"checkout-lineage").hexdigest(),
        provider_event_payload_sha256=hashlib.sha256(
            b"subscription-event"
        ).hexdigest(),
        provider_refresh_facts_sha256=hashlib.sha256(
            b"subscription-refresh-facts"
        ).hexdigest(),
        provider_refreshed_object_sha256=hashlib.sha256(
            b"subscription-object"
        ).hexdigest(),
        provider_refresh_fence=1,
        provider_livemode=True,
        updated_at=NOW.isoformat(),
    )


def _evidence(invoice: PaidInvoiceReconciliationRecord) -> dict[str, object]:
    stamp = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": "cas_harness_customer_production_gate_evidence.v3",
        "gate": "accounts_billing",
        "environment": "public-production",
        "repository": "LittleHenderson/noetic-compass",
        "master_head_sha": MASTER,
        "deploy_id": DEPLOY,
        "event_at_utc": stamp,
        "observed_at_utc": stamp,
        "artifact_uri": acceptance_authority_url("accounts_billing"),
        "artifact_sha256": hashlib.sha256(b"accounts-billing-artifact").hexdigest(),
        "api_base_url": "https://api.noeticcompass.com",
        "service_id": "i-0bd0a082507a51ae3",
        "customer_lane": "public-customer",
        **PSEUDONYMIZER.metadata(),
        "tenant_subject": PSEUDONYMIZER.subject(
            domain=TENANT_DOMAIN,
            tenant_scope=TENANT_ID,
            value=TENANT_ID,
        ),
        "account_subject": PSEUDONYMIZER.subject(
            domain=ACCOUNT_DOMAIN,
            tenant_scope=TENANT_ID,
            value=ACCOUNT_ID,
        ),
        "account_session": {
            "invite_redeem_http_status": 201,
            "login_http_status": 200,
            "logout_http_status": 204,
            "revoked_session_http_status": 401,
            "durable_session_restart_verified": True,
            "disabled_account_http_status": 401,
            "cross_tenant_http_status": 404,
            "verified_at_utc": stamp,
        },
        "quota": {
            "monthly_limit": 1000,
            "usage_at_limit": 1000,
            "overflow_http_status": 429,
            "overflow_error": "audit_quota_exceeded",
            "idempotent_retry_non_double_consuming": True,
            "adjacent_month_isolated": True,
            "shared_postgres_restart_verified": True,
            "verified_at_utc": stamp,
        },
        "billing": {
            "provider": "stripe",
            "mode": "live",
            "currency": "USD",
            "checkout_status": "complete",
            "subscription_status": "active",
            "invoice_status": "paid",
            "receipt_download_http_status": 200,
            "webhook_signature_verified": True,
            "entitlement_status": "active",
            "meter_to_invoice_reconciled": True,
            "provider_customer_subject": PSEUDONYMIZER.subject(
                domain=BILLING_CUSTOMER_DOMAIN,
                tenant_scope=TENANT_ID,
                value=invoice.external_customer_id,
            ),
            "provider_subscription_subject": PSEUDONYMIZER.subject(
                domain=BILLING_SUBSCRIPTION_DOMAIN,
                tenant_scope=TENANT_ID,
                value=invoice.external_subscription_id,
            ),
            "invoice_subject": PSEUDONYMIZER.subject(
                domain=BILLING_INVOICE_DOMAIN,
                tenant_scope=TENANT_ID,
                value=invoice.external_invoice_id,
            ),
            "paid_at_utc": invoice.paid_at,
        },
    }


def _stores():
    backend = InMemoryStateStore()
    billing = _Billing(_invoice())
    entitlements = _Entitlements(_subscription())
    binding = AccountsBillingAcceptanceSourceBindingStore(
        backend,
        accounts=_Accounts(_account()),
        billing=billing,
        entitlements=entitlements,
        pseudonymizer=PSEUDONYMIZER,
    )
    authorizations = AcceptancePublicationAuthorizationStore(
        backend,
        primary_tenant_id=TENANT_ID,
        pseudonymizer=PSEUDONYMIZER,
    )
    authority = CustomerProductionAcceptanceAuthorityStore(
        backend,
        publication_authorization_store=authorizations,
        accounts_billing_source_binding_store=binding,
    )
    return backend, billing, entitlements, binding, authorizations, authority


def _real_binding_stores():
    backend = InMemoryStateStore()
    entitlements = BillingEntitlementStore(backend)
    subscription, _ = install_verified_stripe_subscription(
        entitlements,
        tenant_id=TENANT_ID,
        billing_account_id=ACCOUNT_ID,
        customer_id="cus_live_customer_001",
        subscription_id="sub_live_customer_001",
        event_id="evt_live_customer_subscription_001",
        event_created=1_784_139_500,
    )
    binding = AccountsBillingAcceptanceSourceBindingStore(
        backend,
        accounts=_Accounts(_account()),
        billing=_Billing(_invoice()),
        entitlements=entitlements,
        pseudonymizer=PSEUDONYMIZER,
    )
    return backend, entitlements, subscription, binding


def _authorize(
    store: AcceptancePublicationAuthorizationStore, digest: str
):
    return store.create(
        actor_tenant_id=TENANT_ID,
        actor_account_id=ACCOUNT_ID,
        actor_role="owner",
        gate="accounts_billing",
        master_head_sha=MASTER,
        deploy_id=DEPLOY,
        evidence_sha256=digest,
        expected_head_version=0,
        expected_previous_evidence_sha256=None,
        reason="authorized_publication",
        now=NOW,
    )


def test_binding_recomputes_all_five_subjects_and_is_idempotent() -> None:
    backend, _, _, binding, _, _ = _stores()
    evidence = _evidence(_invoice())

    first = binding.create(
        evidence,
        tenant_id=TENANT_ID,
        invoice_record_id=INVOICE_RECORD_ID,
        now=NOW,
    )
    second = binding.create(
        evidence,
        tenant_id=TENANT_ID,
        invoice_record_id=INVOICE_RECORD_ID,
        now=NOW + timedelta(seconds=30),
    )

    assert first == second
    binding.assert_matches(evidence, evidence_sha256=first)
    public = str(evidence)
    assert TENANT_ID not in public
    assert ACCOUNT_ID not in public
    assert _invoice().external_customer_id not in public
    assert len(backend.list(
        "cas-harness-customer-production-accounts-billing-bindings",
        "customer_production_accounts_billing_source_binding",
    )) == 1


def test_binding_hmac_carries_every_receipt_and_snapshot_identity() -> None:
    backend, entitlements, subscription, binding = _real_binding_stores()
    evidence = _evidence(_invoice())
    digest = binding.create(
        evidence,
        tenant_id=TENANT_ID,
        invoice_record_id=INVOICE_RECORD_ID,
        now=NOW,
    )
    provenance = entitlements.assert_subscription_provenance(subscription)
    record = backend.list(BINDING_TENANT_ID, BINDING_KIND)[0]
    for field_name, value in provenance.to_payload().items():
        assert record.payload[field_name] == value
    assert record.payload["content_binding_hmac"].startswith("hmac-sha256:")
    binding.assert_matches(evidence, evidence_sha256=digest)


@pytest.mark.parametrize(
    "drift",
    (
        "checkout_receipt_deleted",
        "provider_receipt_deleted",
        "checkout_session_deleted",
        "checkout_completion_deleted",
        "customer_index_deleted",
        "subscription_index_deleted",
        "checkout_state",
        "checkout_type",
        "checkout_tenant",
        "checkout_payload_digest",
        "checkout_detail",
        "checkout_extra_field",
        "provider_state",
        "provider_type",
        "provider_tenant",
        "provider_payload_digest",
        "refreshed_object_digest",
        "provider_detail",
        "provider_extra_field",
    ),
)
def test_active_binding_rejects_receipt_deletion_and_drift(drift: str) -> None:
    backend, _, subscription, binding = _real_binding_stores()
    evidence = _evidence(_invoice())
    digest = binding.create(
        evidence,
        tenant_id=TENANT_ID,
        invoice_record_id=INVOICE_RECORD_ID,
        now=NOW,
    )

    index_kind = {
        "checkout_session_deleted": CHECKOUT_SESSION_INDEX_KIND,
        "checkout_completion_deleted": CHECKOUT_COMPLETION_INDEX_KIND,
        "customer_index_deleted": CUSTOMER_INDEX_KIND,
        "subscription_index_deleted": SUBSCRIPTION_INDEX_KIND,
    }.get(drift)
    if index_kind is not None:
        record = backend.list(BILLING_PLATFORM_TENANT, index_kind)[0]
        backend.delete(
            record.tenant_id,
            record.kind,
            record.record_id,
            expected_version=record.version,
        )
    else:
        event_id = (
            subscription.checkout_event_id
            if drift.startswith("checkout_")
            else subscription.provider_event_id
        )
        assert event_id is not None
        record = backend.get(BILLING_PLATFORM_TENANT, WEBHOOK_EVENT_KIND, event_id)
        assert record is not None
        if drift.endswith("_deleted"):
            backend.delete(
                record.tenant_id,
                record.kind,
                record.record_id,
                expected_version=record.version,
            )
        else:
            payload = dict(record.payload)
            if drift.endswith("_state"):
                payload["state"] = "ignored"
            elif drift.endswith("_type"):
                payload["event_type"] = "invoice.paid"
            elif drift.endswith("_tenant"):
                payload["tenant_id"] = "tenant-cross-wired"
            elif drift.endswith("_payload_digest"):
                payload["payload_sha256"] = "0" * 64
            elif drift.endswith("_detail"):
                payload["detail"] = "tampered terminal detail"
            elif drift.endswith("_extra_field"):
                payload["attacker_extra"] = True
            else:
                refreshes = [dict(row) for row in payload["provider_refreshes"]]
                refreshes[-1]["refreshed_object_sha256"] = "0" * 64
                payload["provider_refreshes"] = refreshes
            backend.put(
                record.with_payload(payload), expected_version=record.version
            )

    with pytest.raises(AccountsBillingSourceBindingInvalid, match="provenance"):
        binding.assert_matches(evidence, evidence_sha256=digest)


@pytest.mark.parametrize(
    "field_name",
    (
        "checkout_request_id",
        "checkout_session_id",
        "checkout_event_id",
        "provider_event_id",
        "checkout_event_payload_sha256",
        "checkout_lineage_sha256",
        "provider_event_payload_sha256",
        "provider_refresh_facts_sha256",
        "provider_refreshed_object_sha256",
        "provider_refresh_fence",
        "checkout_receipt_facts_sha256",
        "provider_receipt_facts_sha256",
        "content_binding_hmac",
    ),
)
def test_private_binding_receipt_and_hmac_tamper_fails_closed(
    field_name: str,
) -> None:
    backend, _, _, binding = _real_binding_stores()
    evidence = _evidence(_invoice())
    digest = binding.create(
        evidence,
        tenant_id=TENANT_ID,
        invoice_record_id=INVOICE_RECORD_ID,
        now=NOW,
    )
    record = backend.list(BINDING_TENANT_ID, BINDING_KIND)[0]
    payload = dict(record.payload)
    payload[field_name] = (
        999
        if field_name == "provider_refresh_fence"
        else "0" * 64
        if field_name.endswith("sha256")
        else "tampered-identity"
    )
    backend.put(record.with_payload(payload), expected_version=record.version)
    with pytest.raises(
        (AccountsBillingSourceBindingInvalid, AccountsBillingSourceBindingUnavailable)
    ):
        binding.assert_matches(evidence, evidence_sha256=digest)


def test_arbitrary_well_shaped_subject_is_rejected_against_raw_source() -> None:
    _, _, _, binding, _, _ = _stores()
    evidence = _evidence(_invoice())
    evidence["account_subject"] = "hmac-sha256:" + "a" * 64

    with pytest.raises(AccountsBillingSourceBindingInvalid, match="account_subject"):
        binding.create(
            evidence,
            tenant_id=TENANT_ID,
            invoice_record_id=INVOICE_RECORD_ID,
            now=NOW,
        )


def test_missing_binding_fails_before_any_authority_mutation() -> None:
    backend, _, _, _, authorizations, authority = _stores()
    evidence = _evidence(_invoice())
    digest = hashlib.sha256(
        canonicalize_acceptance_evidence("accounts_billing", evidence, now=NOW)
    ).hexdigest()
    authorization = _authorize(authorizations, digest)

    with pytest.raises(AcceptanceAuthorityInvalid, match="authoritative source"):
        authority.publish(
            "accounts_billing",
            evidence,
            expected_head_version=0,
            expected_previous_sha256=None,
            authorization_artifact_uri=authorization.uri,
            authorization_artifact_sha256=authorization.sha256,
            operation_reason="authorized_publication",
            now=NOW,
        )

    for kind in (REVISION_KIND, OPERATION_KIND, HEAD_KIND):
        assert backend.list(AUTHORITY_TENANT_ID, kind) == ()


def test_active_serve_revalidates_current_invoice_and_account_sources() -> None:
    _, billing, _, binding, authorizations, authority = _stores()
    evidence = _evidence(billing.invoice)
    digest = binding.create(
        evidence,
        tenant_id=TENANT_ID,
        invoice_record_id=INVOICE_RECORD_ID,
        now=NOW,
    )
    authorization = _authorize(authorizations, digest)
    published = authority.publish(
        "accounts_billing",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        authorization_artifact_uri=authorization.uri,
        authorization_artifact_sha256=authorization.sha256,
        operation_reason="authorized_publication",
        now=NOW,
    )
    assert authority.load("accounts_billing", now=NOW).sha256 == published.sha256

    billing.invoice = replace(
        billing.invoice,
        reconciliation_state="unresolved",
        unresolved_reason="provider_quantity_changed",
    )
    with pytest.raises(AcceptanceAuthorityInvalid, match="authoritative source"):
        authority.load("accounts_billing", now=NOW)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("status", "canceled"),
        ("status", "past_due"),
        ("billing_account_id", "acct-cross-wired"),
        ("external_customer_id", "cus_cross_wired"),
        ("external_subscription_id", "sub_cross_wired"),
        (
            "current_period_start",
            (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        ),
        (
            "current_period_end",
            (NOW + timedelta(hours=1)).isoformat(),
        ),
    ),
)
def test_active_serve_revalidates_current_active_subscription_source(
    field: str, value: str
) -> None:
    _, billing, entitlements, binding, authorizations, authority = _stores()
    evidence = _evidence(billing.invoice)
    digest = binding.create(
        evidence,
        tenant_id=TENANT_ID,
        invoice_record_id=INVOICE_RECORD_ID,
        now=NOW,
    )
    authorization = _authorize(authorizations, digest)
    authority.publish(
        "accounts_billing",
        evidence,
        expected_head_version=0,
        expected_previous_sha256=None,
        authorization_artifact_uri=authorization.uri,
        authorization_artifact_sha256=authorization.sha256,
        operation_reason="authorized_publication",
        now=NOW,
    )

    entitlements.subscription = replace(
        entitlements.subscription, **{field: value}
    )
    with pytest.raises(AcceptanceAuthorityInvalid, match="authoritative source"):
        authority.load("accounts_billing", now=NOW)
