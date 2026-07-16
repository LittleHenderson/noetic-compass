"""Private authoritative source binding for accounts/billing gate evidence.

The public verifier can validate only the shape of keyed pseudonyms.  Before
publication, this store binds the exact canonical evidence bytes to one
revalidated matched paid-invoice record and one active same-tenant account.
Raw platform and Stripe identifiers remain in private durable state and are
never copied into the public authority document.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
import hmac
import json
import re
from typing import Any, Protocol

from api.services.accounts.models import Account
from api.services.billing_entitlements import (
    BillingEntitlementError,
    StripeSubscriptionProvenance,
    SubscriptionRecord,
    get_plan,
    subscription_authority_facts_sha256,
    subscription_is_live,
)
from api.services.billing_reconciliation import (
    PaidInvoiceReconciliationRecord,
)
from api.services.customer_production_pseudonyms import (
    ACCOUNT_DOMAIN,
    ACCOUNTS_BILLING_CONTENT_BINDING_DOMAIN,
    BILLING_CUSTOMER_DOMAIN,
    BILLING_INVOICE_DOMAIN,
    BILLING_SUBSCRIPTION_DOMAIN,
    TENANT_DOMAIN,
    CustomerProductionPseudonymizer,
    validate_public_pseudonym_metadata,
)
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)


SCHEMA_VERSION = "cas_harness_accounts_billing_source_binding.v3"
BINDING_TENANT_ID = "cas-harness-customer-production-accounts-billing-bindings"
BINDING_KIND = "customer_production_accounts_billing_source_binding"
_EVIDENCE_SCHEMA = "cas_harness_customer_production_gate_evidence.v3"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RECORD_KEYS = frozenset(
    {
        "schema_version",
        "evidence_sha256",
        "tenant_id",
        "billing_account_id",
        "invoice_record_id",
        "pseudonym_key_id",
        "invoice_ledger_version",
        "provider_snapshot_facts_sha256",
        "subscription_facts_sha256",
        "checkout_request_id",
        "checkout_session_id",
        "checkout_event_id",
        "checkout_event_payload_sha256",
        "checkout_lineage_sha256",
        "provider_event_id",
        "provider_event_payload_sha256",
        "provider_refresh_facts_sha256",
        "provider_refreshed_object_sha256",
        "provider_refresh_fence",
        "checkout_receipt_facts_sha256",
        "provider_receipt_facts_sha256",
        "content_binding_hmac",
        "bound_at_utc",
    }
)


class AccountsBillingSourceBindingError(RuntimeError):
    """Base source-binding error."""


class AccountsBillingSourceBindingInvalid(AccountsBillingSourceBindingError):
    """Evidence does not match one authoritative billing/account source."""


class AccountsBillingSourceBindingUnavailable(AccountsBillingSourceBindingError):
    """Durable source state or a historical verification key is unavailable."""


class AccountsBillingAccountSource(Protocol):
    """Minimum durable account read interface used by acceptance binding."""

    def get_account_by_id(self, account_id: str) -> Account | None: ...


class AccountsBillingInvoiceSource(Protocol):
    """Minimum revalidated paid-invoice read interface used by binding."""

    def get_invoice(
        self, tenant_id: str, invoice_record_id: str
    ) -> PaidInvoiceReconciliationRecord | None: ...


class AccountsBillingEntitlementSource(Protocol):
    """Minimum current subscription interface used by acceptance binding."""

    def get_subscription(self, tenant_id: str) -> SubscriptionRecord | None: ...

    def assert_subscription_provenance(
        self, subscription: SubscriptionRecord
    ) -> StripeSubscriptionProvenance: ...


class AccountsBillingAcceptanceSourceBindingStore:
    """Create and verify private evidence-to-source bindings."""

    def __init__(
        self,
        store: StateStore,
        *,
        accounts: AccountsBillingAccountSource,
        billing: AccountsBillingInvoiceSource,
        entitlements: AccountsBillingEntitlementSource,
        pseudonymizer: CustomerProductionPseudonymizer,
    ) -> None:
        if not callable(getattr(accounts, "get_account_by_id", None)):
            raise ValueError("account store is required")
        if not callable(getattr(billing, "get_invoice", None)):
            raise ValueError("billing reconciliation store is required")
        if not callable(getattr(entitlements, "get_subscription", None)):
            raise ValueError("billing entitlement store is required")
        if not callable(
            getattr(entitlements, "assert_subscription_provenance", None)
        ):
            raise ValueError("billing entitlement provenance source is required")
        if not isinstance(pseudonymizer, CustomerProductionPseudonymizer):
            raise ValueError("customer-production pseudonymizer is required")
        self._store = store
        self._accounts = accounts
        self._billing = billing
        self._entitlements = entitlements
        self._pseudonymizer = pseudonymizer

    def create(
        self,
        evidence: Mapping[str, Any],
        *,
        tenant_id: str,
        invoice_record_id: str,
        now: datetime | None = None,
    ) -> str:
        """Bind canonical evidence to one revalidated matched invoice/account."""

        canonical = _canonical_json_bytes(evidence)
        evidence_sha256 = hashlib.sha256(canonical).hexdigest()
        (
            invoice,
            account,
            subscription,
            provenance,
            key_id,
        ) = self._assert_authoritative_source(
            evidence,
            tenant_id=tenant_id,
            invoice_record_id=invoice_record_id,
        )
        stamp = _utc_now(now)
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "evidence_sha256": evidence_sha256,
            "tenant_id": invoice.tenant_id,
            "billing_account_id": invoice.billing_account_id,
            "invoice_record_id": invoice.invoice_record_id,
            "pseudonym_key_id": key_id,
            "invoice_ledger_version": invoice.ledger_version,
            "provider_snapshot_facts_sha256": invoice.provider_snapshot_facts_sha256,
            "subscription_facts_sha256": _subscription_facts_sha256(
                subscription
            ),
            **provenance.to_payload(),
            "content_binding_hmac": self._content_binding_hmac(
                evidence_sha256=evidence_sha256,
                invoice=invoice,
                subscription=subscription,
                provenance=provenance,
                pseudonym_key_id=key_id,
            ),
            "bound_at_utc": _format_utc(stamp),
        }
        record = LedgerRecord.new(
            tenant_id=BINDING_TENANT_ID,
            kind=BINDING_KIND,
            record_id=_record_id(evidence_sha256),
            payload=payload,
            source="accounts_billing_acceptance_source_binding",
            trace_id=evidence_sha256,
            now=stamp,
        )
        try:
            stored = self._store.put(record, expected_version=0)
        except VersionConflict:
            try:
                existing = self._store.get(
                    BINDING_TENANT_ID, BINDING_KIND, _record_id(evidence_sha256)
                )
            except Exception as exc:
                raise AccountsBillingSourceBindingUnavailable(
                    "accounts/billing source binding store is unavailable"
                ) from exc
            existing_payload = _validate_record(existing, evidence_sha256)
            if any(
                existing_payload.get(key) != value
                for key, value in payload.items()
                if key != "bound_at_utc"
            ):
                raise AccountsBillingSourceBindingUnavailable(
                    "accounts/billing source binding conflicted"
                )
            stored = existing
        except Exception as exc:
            raise AccountsBillingSourceBindingUnavailable(
                "accounts/billing source binding persistence failed"
            ) from exc
        if stored is None or stored.version != 1:
            raise AccountsBillingSourceBindingUnavailable(
                "accounts/billing source binding version is invalid"
            )
        # Exact readback revalidates both the private row and its live sources.
        self.assert_matches(evidence, evidence_sha256=evidence_sha256)
        return evidence_sha256

    def assert_matches(
        self, evidence: Mapping[str, Any], *, evidence_sha256: str
    ) -> None:
        if (
            not isinstance(evidence_sha256, str)
            or _SHA256_RE.fullmatch(evidence_sha256) is None
            or hashlib.sha256(_canonical_json_bytes(evidence)).hexdigest()
            != evidence_sha256
        ):
            raise AccountsBillingSourceBindingInvalid(
                "accounts/billing evidence digest is invalid"
            )
        try:
            record = self._store.get(
                BINDING_TENANT_ID, BINDING_KIND, _record_id(evidence_sha256)
            )
        except Exception as exc:
            raise AccountsBillingSourceBindingUnavailable(
                "accounts/billing source binding store is unavailable"
            ) from exc
        if record is None:
            raise AccountsBillingSourceBindingInvalid(
                "accounts/billing authoritative source binding is absent"
            )
        payload = _validate_record(record, evidence_sha256)
        tenant_id = str(payload["tenant_id"])
        invoice_record_id = str(payload["invoice_record_id"])
        (
            invoice,
            account,
            subscription,
            provenance,
            key_id,
        ) = self._assert_authoritative_source(
            evidence,
            tenant_id=tenant_id,
            invoice_record_id=invoice_record_id,
        )
        if (
            account.account_id != payload["billing_account_id"]
            or invoice.ledger_version != payload["invoice_ledger_version"]
            or invoice.provider_snapshot_facts_sha256
            != payload["provider_snapshot_facts_sha256"]
            or _subscription_facts_sha256(subscription)
            != payload["subscription_facts_sha256"]
            or any(
                payload.get(field_name) != value
                for field_name, value in provenance.to_payload().items()
            )
            or key_id != payload["pseudonym_key_id"]
        ):
            raise AccountsBillingSourceBindingInvalid(
                "accounts/billing source provenance binding is stale or cross-wired"
            )
        expected_hmac = self._content_binding_hmac(
            evidence_sha256=evidence_sha256,
            invoice=invoice,
            subscription=subscription,
            provenance=provenance,
            pseudonym_key_id=key_id,
        )
        if not hmac.compare_digest(
            str(payload["content_binding_hmac"]), expected_hmac
        ):
            raise AccountsBillingSourceBindingUnavailable(
                "accounts/billing source binding integrity is invalid"
            )

    def _assert_authoritative_source(
        self,
        evidence: Mapping[str, Any],
        *,
        tenant_id: str,
        invoice_record_id: str,
    ) -> tuple[
        PaidInvoiceReconciliationRecord,
        Account,
        SubscriptionRecord,
        StripeSubscriptionProvenance,
        str,
    ]:
        if evidence.get("schema_version") != _EVIDENCE_SCHEMA or evidence.get(
            "gate"
        ) != "accounts_billing":
            raise AccountsBillingSourceBindingInvalid(
                "accounts/billing evidence schema is invalid"
            )
        try:
            key_id = validate_public_pseudonym_metadata(
                evidence, available_key_ids=self._pseudonymizer.key_ids
            )
        except ValueError as exc:
            raise AccountsBillingSourceBindingUnavailable(
                "accounts/billing pseudonym verification key is unavailable"
            ) from exc
        try:
            invoice = self._billing.get_invoice(tenant_id, invoice_record_id)
            if invoice is None:
                raise AccountsBillingSourceBindingInvalid(
                    "accounts/billing paid invoice source is absent"
                )
            account = self._accounts.get_account_by_id(invoice.billing_account_id)
            subscription = self._entitlements.get_subscription(tenant_id)
        except AccountsBillingSourceBindingInvalid:
            raise
        except Exception as exc:
            raise AccountsBillingSourceBindingUnavailable(
                "accounts/billing authoritative source is unavailable"
            ) from exc
        if subscription is None:
            raise AccountsBillingSourceBindingInvalid(
                "accounts/billing authoritative source is not a matched live paid lifecycle"
            )
        try:
            provenance = self._entitlements.assert_subscription_provenance(
                subscription
            )
        except BillingEntitlementError as exc:
            raise AccountsBillingSourceBindingInvalid(
                "accounts/billing subscription provenance is invalid"
            ) from exc
        except Exception as exc:
            raise AccountsBillingSourceBindingUnavailable(
                "accounts/billing subscription provenance source is unavailable"
            ) from exc
        if (
            account is None
            or not account.is_active
            or account.tenant_id != invoice.tenant_id
            or invoice.tenant_id != tenant_id
            or invoice.reconciliation_state != "matched"
            or invoice.unresolved_reason is not None
            or invoice.reconciled_at is None
            or invoice.livemode is not True
            or invoice.currency.upper() != "USD"
            or invoice.provider_quantity_milliseconds
            != invoice.local_quantity_milliseconds
            or invoice.invoice_pdf_http_status != 200
            or not invoice.invoice_pdf_sha256
            or subscription.tenant_id != invoice.tenant_id
            or subscription.source != "stripe_verified"
            or subscription.status != "active"
            or subscription.provider_livemode is not True
            or subscription.billing_account_id != invoice.billing_account_id
            or subscription.external_customer_id != invoice.external_customer_id
            or subscription.external_subscription_id
            != invoice.external_subscription_id
            or not subscription_is_live(subscription)
            or not get_plan(subscription.plan_id).paid
        ):
            raise AccountsBillingSourceBindingInvalid(
                "accounts/billing authoritative source is not a matched live paid lifecycle"
            )
        billing = evidence.get("billing")
        if not isinstance(billing, Mapping):
            raise AccountsBillingSourceBindingInvalid(
                "accounts/billing public billing facts are absent"
            )
        if (
            billing.get("provider") != "stripe"
            or billing.get("mode") != "live"
            or billing.get("currency") != "USD"
            or billing.get("checkout_status") != "complete"
            or billing.get("subscription_status") != "active"
            or billing.get("invoice_status") != "paid"
            or billing.get("webhook_signature_verified") is not True
            or billing.get("entitlement_status") != "active"
            or billing.get("receipt_download_http_status")
            != invoice.invoice_pdf_http_status
            or billing.get("meter_to_invoice_reconciled") is not True
            or _canonical_timestamp(billing.get("paid_at_utc"))
            != _canonical_timestamp(invoice.paid_at)
        ):
            raise AccountsBillingSourceBindingInvalid(
                "accounts/billing public facts do not match the paid invoice source"
            )
        subjects = {
            "tenant_subject": (
                TENANT_DOMAIN,
                invoice.tenant_id,
            ),
            "account_subject": (
                ACCOUNT_DOMAIN,
                invoice.billing_account_id,
            ),
        }
        for field, (domain, raw_value) in subjects.items():
            try:
                self._pseudonymizer.assert_subject(
                    evidence.get(field),
                    domain=domain,
                    tenant_scope=invoice.tenant_id,
                    value=raw_value,
                    key_id=key_id,
                )
            except ValueError as exc:
                raise AccountsBillingSourceBindingInvalid(
                    f"accounts/billing {field} does not match the authoritative source"
                ) from exc
        provider_subjects = {
            "provider_customer_subject": (
                BILLING_CUSTOMER_DOMAIN,
                invoice.external_customer_id,
            ),
            "provider_subscription_subject": (
                BILLING_SUBSCRIPTION_DOMAIN,
                invoice.external_subscription_id,
            ),
            "invoice_subject": (BILLING_INVOICE_DOMAIN, invoice.external_invoice_id),
        }
        for field, (domain, raw_value) in provider_subjects.items():
            try:
                self._pseudonymizer.assert_subject(
                    billing.get(field),
                    domain=domain,
                    tenant_scope=invoice.tenant_id,
                    value=raw_value,
                    key_id=key_id,
                )
            except ValueError as exc:
                raise AccountsBillingSourceBindingInvalid(
                    f"accounts/billing {field} does not match the authoritative source"
                ) from exc
        return invoice, account, subscription, provenance, key_id

    def _content_binding_hmac(
        self,
        *,
        evidence_sha256: str,
        invoice: PaidInvoiceReconciliationRecord,
        subscription: SubscriptionRecord,
        provenance: StripeSubscriptionProvenance,
        pseudonym_key_id: str,
    ) -> str:
        value = _canonical_json_bytes(
            {
                "evidence_sha256": evidence_sha256,
                "tenant_id": invoice.tenant_id,
                "billing_account_id": invoice.billing_account_id,
                "invoice_record_id": invoice.invoice_record_id,
                "external_customer_id": invoice.external_customer_id,
                "external_subscription_id": invoice.external_subscription_id,
                "external_invoice_id": invoice.external_invoice_id,
                "pseudonym_key_id": pseudonym_key_id,
                "invoice_ledger_version": invoice.ledger_version,
                "provider_snapshot_facts_sha256": (
                    invoice.provider_snapshot_facts_sha256
                ),
                "subscription_facts_sha256": _subscription_facts_sha256(
                    subscription
                ),
                **provenance.to_payload(),
            }
        ).decode("ascii")
        return self._pseudonymizer.subject(
            domain=ACCOUNTS_BILLING_CONTENT_BINDING_DOMAIN,
            tenant_scope=invoice.tenant_id,
            value=value,
            key_id=pseudonym_key_id,
        )


def _validate_record(
    record: LedgerRecord | None, evidence_sha256: str
) -> Mapping[str, Any]:
    if (
        record is None
        or record.version != 1
        or record.tenant_id != BINDING_TENANT_ID
        or record.kind != BINDING_KIND
        or record.record_id != _record_id(evidence_sha256)
        or record.parent_ids
        or record.source != "accounts_billing_acceptance_source_binding"
        or record.trace_id != evidence_sha256
        or not isinstance(record.payload, Mapping)
        or set(record.payload) != _RECORD_KEYS
        or record.payload.get("schema_version") != SCHEMA_VERSION
        or record.payload.get("evidence_sha256") != evidence_sha256
        or not isinstance(record.payload.get("invoice_ledger_version"), int)
        or isinstance(record.payload.get("invoice_ledger_version"), bool)
        or int(record.payload.get("invoice_ledger_version", 0)) <= 0
        or _SHA256_RE.fullmatch(
            str(record.payload.get("provider_snapshot_facts_sha256") or "")
        )
        is None
        or _SHA256_RE.fullmatch(
            str(record.payload.get("subscription_facts_sha256") or "")
        )
        is None
        or any(
            _SHA256_RE.fullmatch(str(record.payload.get(field_name) or ""))
            is None
            for field_name in (
                "checkout_event_payload_sha256",
                "checkout_lineage_sha256",
                "provider_event_payload_sha256",
                "provider_refresh_facts_sha256",
                "provider_refreshed_object_sha256",
                "checkout_receipt_facts_sha256",
                "provider_receipt_facts_sha256",
            )
        )
        or not isinstance(record.payload.get("provider_refresh_fence"), int)
        or isinstance(record.payload.get("provider_refresh_fence"), bool)
        or int(record.payload.get("provider_refresh_fence", -1)) < 0
        or not isinstance(record.payload.get("tenant_id"), str)
        or not isinstance(record.payload.get("billing_account_id"), str)
        or not isinstance(record.payload.get("invoice_record_id"), str)
        or not isinstance(record.payload.get("pseudonym_key_id"), str)
        or any(
            not isinstance(record.payload.get(field_name), str)
            or not record.payload.get(field_name)
            for field_name in (
                "checkout_request_id",
                "checkout_session_id",
                "checkout_event_id",
                "provider_event_id",
            )
        )
        or not isinstance(record.payload.get("content_binding_hmac"), str)
    ):
        raise AccountsBillingSourceBindingUnavailable(
            "accounts/billing source binding integrity is invalid"
        )
    _canonical_timestamp(record.payload.get("bound_at_utc"))
    return record.payload


def _record_id(evidence_sha256: str) -> str:
    # Version the immutable key as well as the payload schema. Historical rows
    # cannot satisfy the stronger receipt/refresh provenance contract.
    return f"accounts-billing-source-v3-{evidence_sha256}"


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise AccountsBillingSourceBindingInvalid(
            "accounts/billing evidence is not strict canonical JSON"
        ) from exc


def _subscription_facts_sha256(subscription: SubscriptionRecord) -> str:
    return subscription_authority_facts_sha256(subscription)


def _utc_now(value: datetime | None = None) -> datetime:
    stamp = datetime.now(UTC) if value is None else value
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise AccountsBillingSourceBindingInvalid(
            "accounts/billing binding time must be timezone-aware"
        )
    return stamp.astimezone(UTC).replace(microsecond=0)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise AccountsBillingSourceBindingInvalid(
            "accounts/billing source timestamp is invalid"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AccountsBillingSourceBindingInvalid(
            "accounts/billing source timestamp is invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AccountsBillingSourceBindingInvalid(
            "accounts/billing source timestamp is invalid"
        )
    return _format_utc(parsed.astimezone(UTC))


__all__ = [
    "AccountsBillingAcceptanceSourceBindingStore",
    "AccountsBillingAccountSource",
    "AccountsBillingEntitlementSource",
    "AccountsBillingInvoiceSource",
    "AccountsBillingSourceBindingError",
    "AccountsBillingSourceBindingInvalid",
    "AccountsBillingSourceBindingUnavailable",
    "BINDING_KIND",
    "BINDING_TENANT_ID",
    "SCHEMA_VERSION",
]
