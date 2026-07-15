"""Durable measured-usage outbox and paid-invoice reconciliation.

This is a deliberately bounded financial-record slice.  It does **not** expose a
charge endpoint, submit a Stripe Meter Event, verify a webhook signature, or turn
an estimate into measured usage.  Those effects remain at explicit integration
boundaries:

* ``record_fleet_measurement`` accepts only a caller-verified, hash-bound fleet
  receipt and stores the measurement plus delivery state in one versioned
  aggregate after a fail-safe global receipt reservation;
* ``pending_usage`` returns bounded delivery candidates, while
  ``reserve_usage_delivery`` must durably freeze one candidate before an
  external dispatcher makes any provider call;
* ``mark_usage_submitted`` records a provider acknowledgement but never calls it
  paid; and
* ``reconcile_paid_invoice`` accepts a signature-verified, freshly retrieved
  provider snapshot and reports ``matched`` only when its metered quantity exactly
  equals the locally submitted measurements for that period.

The upstream fleet receipt verifier and Stripe webhook/refresh adapter are trust
boundaries.  This module validates and persists their hash-bound output; it does
not pretend that a Python dataclass proves a signature.  Until those adapters are
wired, this service is useful as a tested persistence contract but closes no
customer-production billing gate.

Provider identifiers are retained only in the private ledger because dispatch and
reconciliation need exact values.  Public projections replace every provider
identifier with a keyed HMAC reference so API callers cannot recover or correlate
raw Stripe ids outside this deployment.

Customer receipt fetching is intentionally not implemented here.  The future
trusted adapter must enforce the configured exact HTTPS-host allowlist on the
initial URL and every redirect, reject credentials/fragments/non-public DNS or IP
targets, stream no more than ``MAX_CUSTOMER_RECEIPT_BYTES``, require HTTP 200 and
``application/pdf``, and hash the exact returned bytes before it constructs
``ProviderPaidInvoice``.  This service re-validates the stable URL/response facts
before persistence; a DTO alone is not proof that the adapter followed them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import ipaddress
import json
import re
import unicodedata
from typing import Literal, Mapping
from urllib.parse import urlsplit
from uuid import uuid4

from api.services.billing_entitlements import (
    BillingEntitlementStore,
    SubscriptionRecord,
)
from api.services.production.state_substrate.interface import (
    LeaseHeld,
    LedgerRecord,
    StateStore,
    VersionConflict,
)


BILLING_RECONCILIATION_SCHEMA_VERSION = "cas_harness_billing_reconciliation.v2"
USAGE_OUTBOX_KIND = "billing_usage_outbox"
USAGE_RECEIPT_INDEX_KIND = "billing_usage_receipt_index"
USAGE_MEASUREMENT_INDEX_KIND = "billing_usage_measurement_index"
PAID_INVOICE_KIND = "billing_paid_invoice_reconciliation"
PAID_INVOICE_INDEX_KIND = "billing_paid_invoice_index"
PROVIDER_EVENT_INDEX_KIND = "billing_provider_event_index"
PROVIDER_REQUEST_INDEX_KIND = "billing_provider_request_index"
METER_EVENT_IDENTIFIER_INDEX_KIND = "billing_meter_event_identifier_index"
SUBSCRIPTION_BINDING_INDEX_KIND = "billing_subscription_binding_index"
CUSTOMER_BINDING_INDEX_KIND = "billing_customer_binding_index"
USAGE_INVOICE_INDEX_KIND = "billing_usage_invoice_index"
BILLING_RECONCILIATION_PLATFORM_TENANT = "_cas_billing_reconciliation"
MAX_WRITE_RETRIES = 12
MAX_MEASUREMENT_SPAN = timedelta(days=31)
MAX_FLEET_RECEIPT_BYTES = 2_000_000
MAX_CUSTOMER_RECEIPT_BYTES = 10_000_000
MAX_PROVIDER_SUBMISSION_LAG = timedelta(days=31)
MAX_CLOCK_SKEW = timedelta(minutes=5)
MAX_STRIPE_METER_EVENT_AGE = timedelta(days=35)
MAX_PROVIDER_READBACK_AGE = timedelta(minutes=5)
MAX_PROVIDER_INVOICE_OBSERVATIONS = 100
MAX_DURABLE_BILLING_NODES = 25_000
MAX_DURABLE_BILLING_STRING_CHARACTERS = 500_000
MAX_DURABLE_BILLING_LIST_ITEMS = 10_000

UsageOutboxState = Literal["pending", "delivery_uncertain", "submitted"]
InvoiceReconciliationState = Literal["unresolved", "matched"]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_CODE_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_METER_EVENT_NAME_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_METER_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_STRIPE_ID_PATTERNS = {
    "customer": re.compile(r"^cus_[A-Za-z0-9_]{1,251}$"),
    "subscription": re.compile(r"^sub_[A-Za-z0-9_]{1,251}$"),
    "price": re.compile(r"^price_[A-Za-z0-9_]{1,249}$"),
    "invoice": re.compile(r"^in_[A-Za-z0-9_]{1,252}$"),
    "event": re.compile(r"^evt_[A-Za-z0-9_]{1,251}$"),
    "request": re.compile(r"^req_[A-Za-z0-9_]{1,251}$"),
}

# These are deliberately low-cardinality, provider-neutral categories.  They
# are safe to expose in tenant projections and cannot become a side channel for
# raw provider request ids, response bodies, exception strings, or credentials.
DELIVERY_FAILURE_CODES = frozenset(
    {
        "configuration_error",
        "delivery_outcome_unknown",
        "dispatcher_error",
        "internal_error",
        "network_error",
        "provider_contract_mismatch",
        "provider_rate_limited",
        "provider_receipt_invalid",
        "provider_rejected",
        "provider_response_invalid",
        "provider_timeout",
        "provider_unreachable",
        "timeout",
    }
)

_USAGE_PAYLOAD_FIELDS = frozenset(
    {
        "schema_version",
        "tenant_id",
        "billing_account_id",
        "usage_id",
        "source",
        "run_id",
        "worker_id",
        "accelerator_milliseconds",
        "accelerator_count",
        "measurement_started_at",
        "measurement_ended_at",
        "receipt_sha256",
        "receipt_schema_version",
        "receipt_size_bytes",
        "receipt_issuer",
        "immutable_sha256",
        "outbox",
        "created_at",
        "updated_at",
        "payload_sha256",
    }
)

_USAGE_OUTBOX_FIELDS = frozenset(
    {
        "state",
        "meter_event_name",
        "meter_event_version",
        "meter_event_timestamp",
        "usage_price_id",
        "currency",
        "livemode",
        "meter_event_identifier",
        "meter_event_request_sha256",
        "external_customer_id",
        "external_subscription_id",
        "attempt_count",
        "last_failure_code",
        "provider_request_id",
        "provider_response_created",
        "provider_response_sha256",
        "provider_response_facts_sha256",
        "submitted_at",
        "last_attempt_at",
    }
)

_INVOICE_PAYLOAD_FIELDS = frozenset(
    {
        "schema_version",
        "tenant_id",
        "billing_account_id",
        "invoice_record_id",
        "external_invoice_id",
        "external_customer_id",
        "external_subscription_id",
        "provider_event_id",
        "provider_event_created",
        "invoice_created",
        "invoice_finalized_at",
        "provider_request_id",
        "provider_snapshot_sha256",
        "provider_snapshot_facts_sha256",
        "provider_snapshot_facts",
        "provider_snapshot_retrieved_at",
        "raw_event_sha256",
        "provider_event_facts_sha256",
        "provider_event_facts",
        "hosted_invoice_url",
        "invoice_pdf",
        "invoice_pdf_http_status",
        "invoice_pdf_content_type",
        "invoice_pdf_size_bytes",
        "invoice_pdf_sha256",
        "invoice_pdf_retrieved_at",
        "provider_observations",
        "latest_observation_sha256",
        "provider_status",
        "provider_paid",
        "currency",
        "amount_due_minor",
        "amount_paid_minor",
        "usage_price_id",
        "meter_event_name",
        "meter_event_version",
        "livemode",
        "usage_period_start",
        "usage_period_end",
        "paid_at",
        "provider_quantity_milliseconds",
        "local_quantity_milliseconds",
        "usage_ids",
        "usage_set_sha256",
        "reconciliation_state",
        "unresolved_reason",
        "reconciled_at",
        "immutable_invoice_sha256",
        "created_at",
        "updated_at",
        "payload_sha256",
    }
)

_PREDICTABLE_KEY_MARKERS = (
    "change-me",
    "changeme",
    "default",
    "development",
    "example",
    "not-a-secret",
    "placeholder",
    "sample-secret",
    "test-secret",
)


class BillingReconciliationError(RuntimeError):
    """A usage/invoice transition is invalid or cannot be trusted."""


class BillingReconciliationConflict(BillingReconciliationError):
    """An immutable receipt or provider identity contradicts durable state."""


class BillingReconciliationUnresolved(BillingReconciliationError):
    """A provider-paid invoice exists but measured usage does not reconcile."""

    def __init__(
        self,
        *,
        record_id: str,
        reason: str,
        expected_quantity: int,
        provider_quantity: int,
    ) -> None:
        self.record_id = record_id
        self.reason = reason
        self.expected_quantity = expected_quantity
        self.provider_quantity = provider_quantity
        super().__init__(
            f"paid invoice usage reconciliation is unresolved ({reason}): "
            f"local submitted quantity={expected_quantity}, "
            f"provider quantity={provider_quantity}"
        )


@dataclass(frozen=True, slots=True)
class FleetUsageMeasurement:
    """One upstream-verified fleet measurement; estimates are refused.

    ``receipt_sha256`` binds the exact authenticated fleet receipt checked by the
    caller.  The ledger makes receipt reuse deterministic and cross-tenant safe.
    ``accelerator_milliseconds`` is an integer to avoid floating-point money and
    quantity drift.  It may not exceed wall time multiplied by accelerator count.
    """

    tenant_id: str
    billing_account_id: str
    run_id: str
    worker_id: str
    accelerator_milliseconds: int
    accelerator_count: int
    measurement_started_at: str
    measurement_ended_at: str
    receipt_sha256: str
    receipt_schema_version: str
    receipt_size_bytes: int
    receipt_issuer: str
    source: str = "fleet_measured"


@dataclass(frozen=True, slots=True)
class UsageOutboxRecord:
    tenant_id: str
    billing_account_id: str
    usage_id: str
    run_id: str
    worker_id: str
    accelerator_milliseconds: int
    accelerator_count: int
    measurement_started_at: str
    measurement_ended_at: str
    receipt_sha256: str
    receipt_schema_version: str
    receipt_size_bytes: int
    receipt_issuer: str
    external_customer_id: str = field(repr=False)
    external_subscription_id: str = field(repr=False)
    meter_event_name: str
    meter_event_version: str
    meter_event_timestamp: int
    usage_price_id: str
    currency: str
    livemode: bool
    meter_event_identifier: str
    meter_event_request_sha256: str
    outbox_state: UsageOutboxState
    attempt_count: int
    last_failure_code: str | None
    provider_request_id: str | None = field(repr=False)
    provider_response_created: int | None
    provider_response_sha256: str | None
    provider_response_facts_sha256: str | None
    submitted_at: str | None
    last_attempt_at: str | None
    created_at: str
    updated_at: str
    ledger_version: int

    def meter_event_request(self) -> dict[str, object]:
        """Return the literal Stripe Meter Event v1 request body."""

        return _meter_event_request(
            event_name=self.meter_event_name,
            customer_id=self.external_customer_id,
            quantity=self.accelerator_milliseconds,
            identifier=self.meter_event_identifier,
            timestamp=self.meter_event_timestamp,
        )

    @classmethod
    def from_ledger(cls, record: LedgerRecord) -> "UsageOutboxRecord":
        payload = record.payload
        _require_schema(payload)
        _require_exact_keys(payload, _USAGE_PAYLOAD_FIELDS, "usage payload")
        _require_bounded_structure(payload, "usage payload")
        _verify_sealed_payload(payload)
        if payload.get("source") != "fleet_measured":
            raise BillingReconciliationConflict(
                "durable usage record is not fleet_measured"
            )
        tenant_id = _required_text(payload.get("tenant_id"), "tenant_id")
        usage_id = _required_text(payload.get("usage_id"), "usage_id")
        if tenant_id != record.tenant_id or usage_id != record.record_id:
            raise BillingReconciliationConflict(
                "usage payload identity does not match its tenant-scoped ledger key"
            )
        outbox = payload.get("outbox")
        if not isinstance(outbox, Mapping):
            raise BillingReconciliationConflict("usage outbox payload is missing")
        _require_exact_keys(outbox, _USAGE_OUTBOX_FIELDS, "usage outbox")
        state = str(outbox.get("state") or "")
        if state not in {"pending", "delivery_uncertain", "submitted"}:
            raise BillingReconciliationConflict("usage outbox state is invalid")
        result = cls(
            tenant_id=tenant_id,
            billing_account_id=_required_text(
                payload.get("billing_account_id"), "billing_account_id"
            ),
            usage_id=usage_id,
            run_id=_required_text(payload.get("run_id"), "run_id"),
            worker_id=_required_text(payload.get("worker_id"), "worker_id"),
            accelerator_milliseconds=_nonnegative_int(
                payload.get("accelerator_milliseconds"),
                "accelerator_milliseconds",
            ),
            accelerator_count=_positive_int(
                payload.get("accelerator_count"), "accelerator_count"
            ),
            measurement_started_at=_normalized_time(
                payload.get("measurement_started_at"), "measurement_started_at"
            ),
            measurement_ended_at=_normalized_time(
                payload.get("measurement_ended_at"), "measurement_ended_at"
            ),
            receipt_sha256=_sha256(
                payload.get("receipt_sha256"), "receipt_sha256"
            ),
            receipt_schema_version=_safe_code(
                payload.get("receipt_schema_version"),
                "receipt_schema_version",
            ),
            receipt_size_bytes=_bounded_receipt_size(
                payload.get("receipt_size_bytes")
            ),
            receipt_issuer=_required_text(
                payload.get("receipt_issuer"), "receipt_issuer"
            ),
            external_customer_id=_stripe_id(
                outbox.get("external_customer_id"), "external_customer_id"
                , "customer"
            ),
            external_subscription_id=_stripe_id(
                outbox.get("external_subscription_id"),
                "external_subscription_id",
                "subscription",
            ),
            meter_event_name=_meter_event_name(
                outbox.get("meter_event_name"), "meter_event_name"
            ),
            meter_event_version=_safe_code(
                outbox.get("meter_event_version"), "meter_event_version"
            ),
            meter_event_timestamp=_positive_int(
                outbox.get("meter_event_timestamp"), "meter_event_timestamp"
            ),
            usage_price_id=_stripe_id(
                outbox.get("usage_price_id"), "usage_price_id", "price"
            ),
            currency=_currency(outbox.get("currency")),
            livemode=_strict_bool(outbox.get("livemode"), "livemode"),
            meter_event_identifier=_meter_identifier(
                outbox.get("meter_event_identifier"),
                "meter_event_identifier",
            ),
            meter_event_request_sha256=_sha256(
                outbox.get("meter_event_request_sha256"),
                "meter_event_request_sha256",
            ),
            outbox_state=state,  # type: ignore[arg-type]
            attempt_count=_nonnegative_int(
                outbox.get("attempt_count"), "attempt_count"
            ),
            last_failure_code=_optional_delivery_failure_code(
                outbox.get("last_failure_code")
            ),
            provider_request_id=_optional_stripe_id(
                outbox.get("provider_request_id"), "provider_request_id", "request"
            ),
            provider_response_created=_optional_positive_int(
                outbox.get("provider_response_created"),
                "provider_response_created",
            ),
            provider_response_sha256=_optional_sha256(
                outbox.get("provider_response_sha256"),
                "provider_response_sha256",
            ),
            provider_response_facts_sha256=_optional_sha256(
                outbox.get("provider_response_facts_sha256"),
                "provider_response_facts_sha256",
            ),
            submitted_at=_optional_time(
                outbox.get("submitted_at"), "submitted_at"
            ),
            last_attempt_at=_optional_time(
                outbox.get("last_attempt_at"), "last_attempt_at"
            ),
            created_at=_normalized_time(payload.get("created_at"), "created_at"),
            updated_at=_normalized_time(payload.get("updated_at"), "updated_at"),
            ledger_version=record.version,
        )
        _validate_measurement(
            FleetUsageMeasurement(
                tenant_id=result.tenant_id,
                billing_account_id=result.billing_account_id,
                run_id=result.run_id,
                worker_id=result.worker_id,
                accelerator_milliseconds=result.accelerator_milliseconds,
                accelerator_count=result.accelerator_count,
                measurement_started_at=result.measurement_started_at,
                measurement_ended_at=result.measurement_ended_at,
                receipt_sha256=result.receipt_sha256,
                receipt_schema_version=result.receipt_schema_version,
                receipt_size_bytes=result.receipt_size_bytes,
                receipt_issuer=result.receipt_issuer,
            )
        )
        expected_meter_timestamp = _greatest_whole_second_inside(
            result.measurement_started_at, result.measurement_ended_at
        )
        if result.meter_event_timestamp != expected_meter_timestamp:
            raise BillingReconciliationConflict(
                "usage meter event timestamp is not the greatest whole second inside the measurement"
            )
        if _usage_id(result.receipt_sha256) != result.usage_id:
            raise BillingReconciliationConflict(
                "usage id does not match its fleet receipt"
            )
        request = result.meter_event_request()
        if _canonical_sha256(request) != result.meter_event_request_sha256:
            raise BillingReconciliationConflict(
                "stored Stripe meter-event request digest is invalid"
            )
        immutable = _usage_immutable_from_record(result)
        if _canonical_sha256(immutable) != _sha256(
            payload.get("immutable_sha256"), "immutable_sha256"
        ):
            raise BillingReconciliationConflict(
                "durable usage immutable facts digest is invalid"
            )
        submission_evidence_fields = (
            result.provider_request_id,
            result.provider_response_created,
            result.provider_response_sha256,
            result.provider_response_facts_sha256,
            result.submitted_at,
        )
        if result.outbox_state == "submitted":
            if (
                any(
                    value is None
                    for value in (
                        result.provider_response_created,
                        result.provider_response_sha256,
                        result.provider_response_facts_sha256,
                        result.submitted_at,
                    )
                )
                or (result.livemode and result.provider_request_id is None)
                or result.last_failure_code is not None
                or result.attempt_count < 1
            ):
                raise BillingReconciliationConflict(
                    "submitted usage is missing exact provider readback evidence"
                )
            provider_created = int(result.provider_response_created)
            submitted_clock = datetime.fromtimestamp(provider_created, tz=UTC)
            if result.submitted_at != submitted_clock.isoformat():
                raise BillingReconciliationConflict(
                    "submitted_at is not the provider-created acceptance time"
                )
            if result.last_attempt_at != result.submitted_at:
                raise BillingReconciliationConflict(
                    "submitted usage last-attempt time is not its provider acceptance time"
                )
            response = _expected_meter_event_response(result, provider_created)
            if _canonical_sha256(response) != result.provider_response_facts_sha256:
                raise BillingReconciliationConflict(
                    "stored Stripe meter-event response facts digest is invalid"
                )
            meter_clock = datetime.fromtimestamp(result.meter_event_timestamp, tz=UTC)
            if not (
                meter_clock <= submitted_clock <= meter_clock + MAX_PROVIDER_SUBMISSION_LAG
            ):
                raise BillingReconciliationConflict(
                    "submitted usage timestamp is outside the delivery window"
                )
        elif any(value is not None for value in submission_evidence_fields):
            raise BillingReconciliationConflict(
                "unsubmitted usage cannot contain provider submission evidence"
            )
        elif result.outbox_state == "delivery_uncertain":
            if (
                result.attempt_count < 1
                or result.last_failure_code is None
                or result.last_attempt_at is None
            ):
                raise BillingReconciliationConflict(
                    "delivery-uncertain usage is missing its durable failure fact"
                )
        elif (
            (result.attempt_count == 0)
            != (result.last_failure_code is None and result.last_attempt_at is None)
            or (
                result.attempt_count > 0
                and (result.last_failure_code is None or result.last_attempt_at is None)
            )
        ):
            raise BillingReconciliationConflict("pending usage failure metadata is invalid")
        return result


@dataclass(frozen=True, slots=True)
class ProviderPaidInvoice:
    """Hash-bound facts from a signature-verified, freshly retrieved invoice.

    The Stripe adapter must verify the webhook signature over the raw bytes and
    retrieve the current invoice before constructing this DTO.  This service
    validates identity, tenant binding, status, period, and quantity; it cannot
    itself authenticate Stripe without those original bytes and credentials.
    """

    provider_event_id: str = field(repr=False)
    provider_event_created: int
    created: int
    status_transitions_finalized_at: int
    external_invoice_id: str = field(repr=False)
    external_customer_id: str = field(repr=False)
    external_subscription_id: str = field(repr=False)
    provider_status: str
    provider_paid: bool
    currency: str
    amount_due_minor: int
    amount_paid_minor: int
    usage_price_id: str
    meter_event_name: str
    meter_event_version: str
    livemode: bool
    usage_quantity_milliseconds: int
    usage_period_start: str
    usage_period_end: str
    paid_at: str
    raw_event_sha256: str = field(repr=False)
    provider_snapshot_sha256: str = field(repr=False)
    provider_snapshot_retrieved_at: str
    hosted_invoice_url: str = field(repr=False)
    invoice_pdf: str = field(repr=False)
    invoice_pdf_http_status: int
    invoice_pdf_content_type: str
    invoice_pdf_size_bytes: int
    invoice_pdf_sha256: str
    invoice_pdf_retrieved_at: str
    provider_request_id: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class PaidInvoiceReconciliationRecord:
    tenant_id: str
    billing_account_id: str
    invoice_record_id: str
    external_invoice_id: str = field(repr=False)
    external_customer_id: str = field(repr=False)
    external_subscription_id: str = field(repr=False)
    provider_event_id: str = field(repr=False)
    provider_event_created: int
    invoice_created: int
    invoice_finalized_at: int
    provider_request_id: str | None = field(repr=False)
    provider_snapshot_sha256: str
    provider_snapshot_facts_sha256: str
    provider_snapshot_retrieved_at: str
    raw_event_sha256: str
    provider_event_facts_sha256: str
    hosted_invoice_url: str = field(repr=False)
    invoice_pdf: str = field(repr=False)
    invoice_pdf_http_status: int
    invoice_pdf_content_type: str
    invoice_pdf_size_bytes: int
    invoice_pdf_sha256: str
    invoice_pdf_retrieved_at: str
    provider_observation_count: int
    currency: str
    amount_due_minor: int
    amount_paid_minor: int
    usage_price_id: str
    meter_event_name: str
    meter_event_version: str
    livemode: bool
    usage_period_start: str
    usage_period_end: str
    paid_at: str
    provider_quantity_milliseconds: int
    local_quantity_milliseconds: int
    usage_ids: tuple[str, ...]
    usage_set_sha256: str
    reconciliation_state: InvoiceReconciliationState
    unresolved_reason: str | None
    reconciled_at: str | None
    created_at: str
    updated_at: str
    ledger_version: int

    @classmethod
    def from_ledger(
        cls,
        record: LedgerRecord,
        *,
        allowed_receipt_hosts: frozenset[str],
    ) -> "PaidInvoiceReconciliationRecord":
        payload = record.payload
        _require_schema(payload)
        _require_exact_keys(payload, _INVOICE_PAYLOAD_FIELDS, "invoice payload")
        _require_bounded_structure(payload, "invoice payload")
        _verify_sealed_payload(payload)
        if payload.get("provider_status") != "paid" or payload.get("provider_paid") is not True:
            raise BillingReconciliationConflict(
                "invoice record does not contain a provider-paid fact"
            )
        tenant_id = _required_text(payload.get("tenant_id"), "tenant_id")
        record_id = _required_text(
            payload.get("invoice_record_id"), "invoice_record_id"
        )
        if tenant_id != record.tenant_id or record_id != record.record_id:
            raise BillingReconciliationConflict(
                "invoice payload identity does not match its tenant-scoped ledger key"
            )
        state = str(payload.get("reconciliation_state") or "")
        if state not in {"unresolved", "matched"}:
            raise BillingReconciliationConflict(
                "invoice reconciliation state is invalid"
            )
        usage_ids_raw = payload.get("usage_ids")
        if not isinstance(usage_ids_raw, list) or any(
            not isinstance(item, str) or not item for item in usage_ids_raw
        ):
            raise BillingReconciliationConflict("invoice usage_ids are invalid")
        usage_ids = tuple(usage_ids_raw)
        if usage_ids != tuple(sorted(set(usage_ids))):
            raise BillingReconciliationConflict(
                "invoice usage_ids must be unique and sorted"
            )
        payload_livemode = _strict_bool(payload.get("livemode"), "livemode")
        observations = _validated_invoice_observations(
            payload.get("provider_observations"),
            allowed_receipt_hosts=allowed_receipt_hosts,
            require_provider_request_id=payload_livemode,
        )
        latest_observation = observations[-1]
        if _canonical_sha256(latest_observation) != _sha256(
            payload.get("latest_observation_sha256"),
            "latest_observation_sha256",
        ):
            raise BillingReconciliationConflict(
                "latest provider observation digest is invalid"
            )
        if _canonical_sha256(
            _invoice_observation_from_payload(payload)
        ) != _canonical_sha256(latest_observation):
            raise BillingReconciliationConflict(
                "current invoice fields do not match the latest provider observation"
            )
        result = cls(
            tenant_id=tenant_id,
            billing_account_id=_required_text(
                payload.get("billing_account_id"), "billing_account_id"
            ),
            invoice_record_id=record_id,
            external_invoice_id=_stripe_id(
                payload.get("external_invoice_id"), "external_invoice_id", "invoice"
            ),
            external_customer_id=_stripe_id(
                payload.get("external_customer_id"), "external_customer_id", "customer"
            ),
            external_subscription_id=_stripe_id(
                payload.get("external_subscription_id"),
                "external_subscription_id",
                "subscription",
            ),
            provider_event_id=_stripe_id(
                payload.get("provider_event_id"), "provider_event_id", "event"
            ),
            provider_event_created=_positive_int(
                payload.get("provider_event_created"), "provider_event_created"
            ),
            invoice_created=_positive_int(
                payload.get("invoice_created"), "invoice_created"
            ),
            invoice_finalized_at=_positive_int(
                payload.get("invoice_finalized_at"), "invoice_finalized_at"
            ),
            provider_request_id=_optional_stripe_id(
                payload.get("provider_request_id"), "provider_request_id", "request"
            ),
            provider_snapshot_sha256=_sha256(
                payload.get("provider_snapshot_sha256"),
                "provider_snapshot_sha256",
            ),
            provider_snapshot_facts_sha256=_sha256(
                payload.get("provider_snapshot_facts_sha256"),
                "provider_snapshot_facts_sha256",
            ),
            provider_snapshot_retrieved_at=_normalized_time(
                payload.get("provider_snapshot_retrieved_at"),
                "provider_snapshot_retrieved_at",
            ),
            raw_event_sha256=_sha256(
                payload.get("raw_event_sha256"), "raw_event_sha256"
            ),
            provider_event_facts_sha256=_sha256(
                payload.get("provider_event_facts_sha256"),
                "provider_event_facts_sha256",
            ),
            hosted_invoice_url=_canonical_https_url(
                payload.get("hosted_invoice_url"),
                allowed_hosts=allowed_receipt_hosts,
            ),
            invoice_pdf=_canonical_https_url(
                payload.get("invoice_pdf"),
                allowed_hosts=allowed_receipt_hosts,
            ),
            invoice_pdf_http_status=_customer_receipt_status(
                payload.get("invoice_pdf_http_status")
            ),
            invoice_pdf_content_type=_customer_receipt_content_type(
                payload.get("invoice_pdf_content_type")
            ),
            invoice_pdf_size_bytes=_bounded_customer_receipt_size(
                payload.get("invoice_pdf_size_bytes")
            ),
            invoice_pdf_sha256=_sha256(
                payload.get("invoice_pdf_sha256"),
                "invoice_pdf_sha256",
            ),
            invoice_pdf_retrieved_at=_normalized_time(
                payload.get("invoice_pdf_retrieved_at"),
                "invoice_pdf_retrieved_at",
            ),
            provider_observation_count=len(observations),
            currency=_currency(payload.get("currency")),
            amount_due_minor=_nonnegative_int(
                payload.get("amount_due_minor"), "amount_due_minor"
            ),
            amount_paid_minor=_nonnegative_int(
                payload.get("amount_paid_minor"), "amount_paid_minor"
            ),
            usage_price_id=_stripe_id(
                payload.get("usage_price_id"), "usage_price_id", "price"
            ),
            meter_event_name=_meter_event_name(
                payload.get("meter_event_name"), "meter_event_name"
            ),
            meter_event_version=_safe_code(
                payload.get("meter_event_version"), "meter_event_version"
            ),
            livemode=payload_livemode,
            usage_period_start=_normalized_whole_second_time(
                payload.get("usage_period_start"), "usage_period_start"
            ),
            usage_period_end=_normalized_whole_second_time(
                payload.get("usage_period_end"), "usage_period_end"
            ),
            paid_at=_normalized_whole_second_time(payload.get("paid_at"), "paid_at"),
            provider_quantity_milliseconds=_nonnegative_int(
                payload.get("provider_quantity_milliseconds"),
                "provider_quantity_milliseconds",
            ),
            local_quantity_milliseconds=_nonnegative_int(
                payload.get("local_quantity_milliseconds"),
                "local_quantity_milliseconds",
            ),
            usage_ids=usage_ids,
            usage_set_sha256=_sha256(
                payload.get("usage_set_sha256"), "usage_set_sha256"
            ),
            reconciliation_state=state,  # type: ignore[arg-type]
            unresolved_reason=_optional_safe_code(
                payload.get("unresolved_reason"), "unresolved_reason"
            ),
            reconciled_at=_optional_time(
                payload.get("reconciled_at"), "reconciled_at"
            ),
            created_at=_normalized_time(payload.get("created_at"), "created_at"),
            updated_at=_normalized_time(payload.get("updated_at"), "updated_at"),
            ledger_version=record.version,
        )
        try:
            event_clock = datetime.fromtimestamp(
                result.provider_event_created, tz=UTC
            )
        except (OverflowError, OSError, ValueError) as exc:
            raise BillingReconciliationConflict(
                "invoice provider event timestamp is invalid"
            ) from exc
        if not (
            _parse_time(result.usage_period_start)
            < _parse_time(result.usage_period_end)
            <= datetime.fromtimestamp(result.invoice_finalized_at, tz=UTC)
            <= _parse_time(result.paid_at)
            <= event_clock
            <= _parse_time(result.provider_snapshot_retrieved_at)
        ):
            raise BillingReconciliationConflict(
                "invoice period/payment/provider observation ordering is invalid"
            )
        if not (
            datetime.fromtimestamp(result.invoice_created, tz=UTC)
            <= datetime.fromtimestamp(result.invoice_finalized_at, tz=UTC)
        ):
            raise BillingReconciliationConflict(
                "invoice creation/finalization ordering is invalid"
            )
        if _parse_time(result.invoice_pdf_retrieved_at) < _parse_time(result.paid_at):
            raise BillingReconciliationConflict(
                "invoice PDF retrieval predates invoice payment"
            )
        if result.amount_paid_minor != result.amount_due_minor:
            raise BillingReconciliationConflict(
                "invoice paid and due amounts do not reconcile"
            )
        if result.reconciliation_state == "matched":
            if (
                not result.usage_ids
                or result.provider_quantity_milliseconds <= 0
                or result.provider_quantity_milliseconds
                != result.local_quantity_milliseconds
                or result.reconciled_at is None
                or result.unresolved_reason is not None
            ):
                raise BillingReconciliationConflict(
                    "matched invoice reconciliation invariants are invalid"
                )
        elif result.reconciled_at is not None or result.unresolved_reason is None:
            raise BillingReconciliationConflict(
                "unresolved invoice reconciliation invariants are invalid"
            )
        if (
            latest_observation["provider_snapshot_facts"]
            != _invoice_snapshot_facts_from_record(result)
            or latest_observation["provider_event_facts"]
            != _invoice_event_facts_from_record(result)
        ):
            raise BillingReconciliationConflict(
                "current invoice fields contradict the parsed provider facts"
            )
        return result


class BillingReconciliationStore:
    """Tenant-scoped durable billing facts over the shared ``StateStore``."""

    def __init__(
        self,
        store: StateStore,
        entitlements: BillingEntitlementStore,
        *,
        provider_reference_hash_key: str,
        usage_price_id: str,
        meter_event_name: str,
        meter_event_version: str,
        currency: str,
        livemode: bool,
        customer_receipt_allowed_hosts: tuple[str, ...],
    ) -> None:
        key = validate_provider_reference_hash_key(
            provider_reference_hash_key
        )
        self._store = store
        self._entitlements = entitlements
        self._provider_reference_hash_key = key
        self._usage_price_id = _stripe_id(usage_price_id, "usage_price_id", "price")
        self._meter_event_name = _meter_event_name(
            meter_event_name, "meter_event_name"
        )
        self._meter_event_version = _safe_code(
            meter_event_version, "meter_event_version"
        )
        self._currency = _currency(currency)
        self._livemode = _strict_bool(livemode, "livemode")
        self._customer_receipt_allowed_hosts = _normalize_receipt_hosts(
            customer_receipt_allowed_hosts
        )

    def record_fleet_measurement(
        self, measurement: FleetUsageMeasurement
    ) -> tuple[UsageOutboxRecord, bool]:
        """Fail-safely create measured usage plus its pending provider outbox.

        ``StateStore`` has no multi-record transaction: the receipt digest is
        globally reserved first, then measurement and outbox state are written
        together as one tenant aggregate. If the process dies between those two
        writes, an exact retry completes the tenant record; a contradictory or
        cross-tenant retry remains blocked. This is idempotent crash recovery,
        not an atomic two-record commit.

        A second global binding covers the semantic measurement identity
        (tenant, billing account, run, worker, and exact start/end window), so two
        different signed receipts cannot bill the same measurement twice.
        """
        normalized = _validate_measurement(measurement)
        subscription = self._stripe_subscription_for_tenant(measurement.tenant_id)
        billing_account_id = _required_text(
            subscription.billing_account_id, "billing_account_id"
        )
        if billing_account_id != normalized["billing_account_id"]:
            raise BillingReconciliationConflict(
                "fleet usage billing account contradicts the tenant subscription binding"
            )
        customer_id = _stripe_id(
            subscription.external_customer_id, "external_customer_id", "customer"
        )
        subscription_id = _stripe_id(
            subscription.external_subscription_id,
            "external_subscription_id",
            "subscription",
        )
        binding = _subscription_binding_facts(
            tenant_id=measurement.tenant_id,
            billing_account_id=billing_account_id,
            customer_id=customer_id,
            subscription_id=subscription_id,
        )
        usage_id = _usage_id(normalized["receipt_sha256"])
        identifier = _meter_identifier(
            f"cas_usage_{usage_id.removeprefix('usage-')}",
            "meter_event_identifier",
        )
        meter_timestamp = _greatest_whole_second_inside(
            normalized["measurement_started_at"],
            normalized["measurement_ended_at"],
        )
        meter_request = _meter_event_request(
            event_name=self._meter_event_name,
            customer_id=customer_id,
            quantity=int(normalized["accelerator_milliseconds"]),
            identifier=identifier,
            timestamp=meter_timestamp,
        )
        meter_request_sha256 = _canonical_sha256(meter_request)
        now = _now_iso()
        immutable = {
            **normalized,
            "usage_id": usage_id,
            "external_customer_id": customer_id,
            "external_subscription_id": subscription_id,
            "meter_event_name": self._meter_event_name,
            "meter_event_version": self._meter_event_version,
            "meter_event_timestamp": meter_timestamp,
            "usage_price_id": self._usage_price_id,
            "currency": self._currency,
            "livemode": self._livemode,
            "meter_event_identifier": identifier,
            "meter_event_request_sha256": meter_request_sha256,
        }
        immutable_sha256 = _canonical_sha256(immutable)
        self._bind_subscription_indexes(binding)
        self._bind_platform_index(
            kind=USAGE_MEASUREMENT_INDEX_KIND,
            record_id=_measurement_index_id(normalized),
            payload={
                "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                "tenant_id": normalized["tenant_id"],
                "billing_account_id": normalized["billing_account_id"],
                "run_id": normalized["run_id"],
                "worker_id": normalized["worker_id"],
                "measurement_started_at": normalized[
                    "measurement_started_at"
                ],
                "measurement_ended_at": normalized["measurement_ended_at"],
                "usage_id": usage_id,
                "receipt_sha256": normalized["receipt_sha256"],
                "immutable_sha256": immutable_sha256,
            },
            source="billing.reconciliation.usage_measurement_index",
            trace_id=usage_id,
        )
        self._bind_platform_index(
            kind=METER_EVENT_IDENTIFIER_INDEX_KIND,
            record_id=_meter_identifier_index_id(identifier),
            payload={
                "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                "meter_event_identifier": identifier,
                "tenant_id": normalized["tenant_id"],
                "usage_id": usage_id,
                "meter_event_request_sha256": meter_request_sha256,
                "immutable_sha256": immutable_sha256,
            },
            source="billing.reconciliation.meter_event_identifier_index",
            trace_id=usage_id,
        )
        self._bind_platform_index(
            kind=USAGE_RECEIPT_INDEX_KIND,
            record_id=_receipt_index_id(normalized["receipt_sha256"]),
            payload={
                "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                "receipt_sha256": normalized["receipt_sha256"],
                "tenant_id": normalized["tenant_id"],
                "billing_account_id": normalized["billing_account_id"],
                "usage_id": usage_id,
                "immutable_sha256": immutable_sha256,
            },
            source="billing.reconciliation.usage_receipt_index",
            trace_id=usage_id,
        )

        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                measurement.tenant_id, USAGE_OUTBOX_KIND, usage_id
            )
            if existing is not None:
                current = self._usage_from_record(existing)
                if str(existing.payload.get("immutable_sha256")) != immutable_sha256:
                    raise BillingReconciliationConflict(
                        "fleet receipt was replayed with contradictory usage facts"
                    )
                return current, False
            payload: dict[str, object] = {
                "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                "tenant_id": normalized["tenant_id"],
                "billing_account_id": normalized["billing_account_id"],
                "usage_id": usage_id,
                "source": "fleet_measured",
                "run_id": normalized["run_id"],
                "worker_id": normalized["worker_id"],
                "accelerator_milliseconds": normalized[
                    "accelerator_milliseconds"
                ],
                "accelerator_count": normalized["accelerator_count"],
                "measurement_started_at": normalized[
                    "measurement_started_at"
                ],
                "measurement_ended_at": normalized["measurement_ended_at"],
                "receipt_sha256": normalized["receipt_sha256"],
                "receipt_schema_version": normalized["receipt_schema_version"],
                "receipt_size_bytes": normalized["receipt_size_bytes"],
                "receipt_issuer": normalized["receipt_issuer"],
                "immutable_sha256": immutable_sha256,
                "outbox": {
                    "state": "pending",
                    "meter_event_name": self._meter_event_name,
                    "meter_event_version": self._meter_event_version,
                    "meter_event_timestamp": meter_timestamp,
                    "usage_price_id": self._usage_price_id,
                    "currency": self._currency,
                    "livemode": self._livemode,
                    "meter_event_identifier": identifier,
                    "meter_event_request_sha256": meter_request_sha256,
                    "external_customer_id": customer_id,
                    "external_subscription_id": subscription_id,
                    "attempt_count": 0,
                    "last_failure_code": None,
                    "provider_request_id": None,
                    "provider_response_created": None,
                    "provider_response_sha256": None,
                    "provider_response_facts_sha256": None,
                    "submitted_at": None,
                    "last_attempt_at": None,
                },
                "created_at": now,
                "updated_at": now,
            }
            payload = _seal_payload(payload)
            record = LedgerRecord.new(
                tenant_id=measurement.tenant_id,
                kind=USAGE_OUTBOX_KIND,
                record_id=usage_id,
                payload=payload,
                source="billing.reconciliation.fleet_measurement",
                trace_id=usage_id,
            )
            try:
                stored = self._store.put(record, expected_version=0)
                return self._usage_from_record(stored), True
            except VersionConflict:
                continue
        raise BillingReconciliationError("usage record contention exceeded")

    def get_usage(self, tenant_id: str, usage_id: str) -> UsageOutboxRecord | None:
        record = self._store.get(tenant_id, USAGE_OUTBOX_KIND, usage_id)
        return self._usage_from_record(record) if record is not None else None

    def list_usage(self, tenant_id: str) -> tuple[UsageOutboxRecord, ...]:
        return tuple(
            self._usage_from_record(record)
            for record in self._store.list(tenant_id, USAGE_OUTBOX_KIND)
        )

    def pending_usage(
        self, tenant_id: str, *, limit: int = 100
    ) -> tuple[UsageOutboxRecord, ...]:
        """Return bounded candidates, never authority to contact Stripe.

        A dispatcher MUST call :meth:`reserve_usage_delivery` and durably receive
        its ``delivery_uncertain`` row before making the first provider call.  A
        row returned here is still ``pending`` and therefore is not safe to send.
        """

        if limit < 1 or limit > 1000:
            raise BillingReconciliationError("pending usage limit must be 1..1000")
        rows = [
            row for row in self.list_usage(tenant_id) if row.outbox_state == "pending"
        ]
        rows.sort(key=lambda row: (row.measurement_ended_at, row.usage_id))
        return tuple(rows[:limit])

    def record_delivery_failure(
        self, *, tenant_id: str, usage_id: str, failure_code: str
    ) -> UsageOutboxRecord:
        """Record a definite failure only when Stripe was not contacted.

        Once delivery has been reserved, every non-acknowledged outcome remains
        ``delivery_uncertain`` and non-retryable.  This method deliberately
        refuses that state so a timeout cannot accidentally make a request
        dispatchable again.
        """

        safe_failure = _delivery_failure_code(failure_code)
        lease = self._acquire_tenant_lock(tenant_id, holder=f"failure-{uuid4().hex}")
        try:
            for _ in range(MAX_WRITE_RETRIES):
                existing = self._store.get(tenant_id, USAGE_OUTBOX_KIND, usage_id)
                if existing is None:
                    raise BillingReconciliationError("usage record not found")
                current = self._usage_from_record(existing)
                if current.outbox_state != "pending":
                    raise BillingReconciliationConflict(
                        "only pending usage can record a definite delivery failure"
                    )
                payload = dict(existing.payload)
                outbox = dict(payload["outbox"])  # type: ignore[arg-type]
                outbox.update(
                    {
                        "attempt_count": current.attempt_count + 1,
                        "last_failure_code": safe_failure,
                        "last_attempt_at": _now_iso(),
                    }
                )
                payload["outbox"] = outbox
                payload["updated_at"] = _now_iso()
                payload = _seal_payload(payload)
                try:
                    stored = self._store.put(
                        existing.with_payload(payload),
                        expected_version=existing.version,
                    )
                    return self._usage_from_record(stored)
                except VersionConflict:
                    continue
        finally:
            self._store.release_lease(lease.token)
        raise BillingReconciliationError("usage delivery failure contention exceeded")

    def reserve_usage_delivery(
        self, *, tenant_id: str, usage_id: str
    ) -> UsageOutboxRecord:
        """Durably freeze one request *before* any Stripe side effect.

        The returned row is the dispatcher's authority to make exactly one
        attempt using its stored request and identifier.  Reservation first
        closes the crash window in which a process could POST to Stripe and die
        while the durable row was still resendable as ``pending``.  Stripe only
        promises identifier uniqueness for a rolling period, so local safety
        cannot depend on a later provider retry being deduplicated.

        If the exact Meter Event response is received, ``mark_usage_submitted``
        may advance this row to ``submitted``.  Otherwise it remains
        ``delivery_uncertain`` across restarts and never re-enters
        ``pending_usage``.  Stripe v1 exposes no exact Meter Event retrieval
        endpoint, so this method makes no unsupported later-readback claim.
        Every later reservation request raises rather than returning a second
        apparent authority to dispatch the same request.
        """

        safe_failure = "delivery_outcome_unknown"
        lease = self._acquire_tenant_lock(
            tenant_id, holder=f"reserve-{uuid4().hex}"
        )
        try:
            for _ in range(MAX_WRITE_RETRIES):
                existing = self._store.get(tenant_id, USAGE_OUTBOX_KIND, usage_id)
                if existing is None:
                    raise BillingReconciliationError("usage record not found")
                current = self._usage_from_record(existing)
                if current.outbox_state == "submitted":
                    raise BillingReconciliationConflict(
                        "submitted usage cannot become delivery uncertain"
                    )
                if current.outbox_state == "delivery_uncertain":
                    raise BillingReconciliationConflict(
                        "usage delivery reservation is non-replayable"
                    )
                try:
                    meter_clock = datetime.fromtimestamp(
                        current.meter_event_timestamp, tz=UTC
                    )
                except (OverflowError, OSError, ValueError) as exc:
                    raise BillingReconciliationError(
                        "meter-event timestamp is outside the supported range"
                    ) from exc
                now_clock = datetime.now(UTC)
                if not (
                    now_clock - MAX_STRIPE_METER_EVENT_AGE
                    <= meter_clock
                    <= now_clock + MAX_CLOCK_SKEW
                ):
                    raise BillingReconciliationError(
                        "meter-event timestamp is outside Stripe's 35-day/+5-minute delivery window"
                    )
                attempted_at = now_clock.isoformat()
                payload = dict(existing.payload)
                outbox = dict(payload["outbox"])  # type: ignore[arg-type]
                outbox.update(
                    {
                        "state": "delivery_uncertain",
                        "attempt_count": current.attempt_count + 1,
                        "last_failure_code": safe_failure,
                        "last_attempt_at": attempted_at,
                    }
                )
                payload["outbox"] = outbox
                payload["updated_at"] = _now_iso()
                payload = _seal_payload(payload)
                try:
                    stored = self._store.put(
                        existing.with_payload(payload),
                        expected_version=existing.version,
                    )
                    return self._usage_from_record(stored)
                except VersionConflict:
                    continue
        finally:
            self._store.release_lease(lease.token)
        raise BillingReconciliationError("usage delivery reservation contention exceeded")

    def mark_usage_submitted(
        self,
        *,
        tenant_id: str,
        usage_id: str,
        response: Mapping[str, object],
        provider_request_id: str | None,
        provider_response_sha256: str,
    ) -> UsageOutboxRecord:
        """Record one literal Stripe Meter Event v1 acknowledgement.

        This method performs no network call.  The adapter supplies the parsed
        response and SHA-256 of the exact response bytes.  Stripe's Meter Event
        object has no event id, so no synthetic provider id is accepted or
        persisted.
        """

        request_id = _optional_stripe_id(
            provider_request_id, "provider_request_id", "request"
        )
        if self._livemode and request_id is None:
            raise BillingReconciliationError(
                "live provider submission requires a provider request receipt"
            )
        response_sha256 = _sha256(
            provider_response_sha256, "provider_response_sha256"
        )
        response_facts = _validate_meter_event_response(response)
        response_facts_sha256 = _canonical_sha256(response_facts)
        lease = self._acquire_tenant_lock(tenant_id, holder=f"submit-{uuid4().hex}")
        try:
            for _ in range(MAX_WRITE_RETRIES):
                existing = self._store.get(tenant_id, USAGE_OUTBOX_KIND, usage_id)
                if existing is None:
                    raise BillingReconciliationError("usage record not found")
                current = self._usage_from_record(existing)
                provider_created = int(response_facts["created"])
                submitted_clock = datetime.fromtimestamp(provider_created, tz=UTC)
                meter_clock = datetime.fromtimestamp(
                    current.meter_event_timestamp, tz=UTC
                )
                now = datetime.now(UTC)
                if submitted_clock < meter_clock:
                    raise BillingReconciliationError(
                        "provider response cannot predate its meter timestamp"
                    )
                if submitted_clock - meter_clock > MAX_PROVIDER_SUBMISSION_LAG:
                    raise BillingReconciliationError(
                        "provider submission exceeds the bounded delivery window"
                    )
                if submitted_clock > now + MAX_CLOCK_SKEW:
                    raise BillingReconciliationError(
                        "provider submission timestamp is unreasonably in the future"
                    )
                if response_facts != _expected_meter_event_response(
                    current, provider_created
                ):
                    raise BillingReconciliationConflict(
                        "provider meter-event readback contradicts the pending outbox"
                    )
                if current.outbox_state == "submitted":
                    if (
                        current.provider_request_id == request_id
                        and current.provider_response_created == provider_created
                        and current.provider_response_sha256 == response_sha256
                        and current.provider_response_facts_sha256
                        == response_facts_sha256
                    ):
                        return current
                    raise BillingReconciliationConflict(
                        "usage was already submitted with a different provider receipt"
                    )
                if current.outbox_state != "delivery_uncertain":
                    raise BillingReconciliationConflict(
                        "usage delivery must be durably reserved before provider acknowledgement"
                    )
                if request_id is not None:
                    self._bind_provider_identity(
                        kind=PROVIDER_REQUEST_INDEX_KIND,
                        provider_id=request_id,
                        provider_type="request",
                        purpose="usage_submission",
                        tenant_id=tenant_id,
                        subject_id=usage_id,
                        evidence_sha256=response_sha256,
                        facts_sha256=response_facts_sha256,
                    )
                payload = dict(existing.payload)
                outbox = dict(payload["outbox"])  # type: ignore[arg-type]
                outbox.update(
                    {
                        "state": "submitted",
                        "attempt_count": current.attempt_count,
                        "last_failure_code": None,
                        "provider_request_id": request_id,
                        "provider_response_created": provider_created,
                        "provider_response_sha256": response_sha256,
                        "provider_response_facts_sha256": response_facts_sha256,
                        "submitted_at": submitted_clock.isoformat(),
                        "last_attempt_at": submitted_clock.isoformat(),
                    }
                )
                payload["outbox"] = outbox
                payload["updated_at"] = _now_iso()
                payload = _seal_payload(payload)
                try:
                    stored = self._store.put(
                        existing.with_payload(payload),
                        expected_version=existing.version,
                    )
                    return self._usage_from_record(stored)
                except VersionConflict:
                    continue
        finally:
            self._store.release_lease(lease.token)
        raise BillingReconciliationError("usage submission contention exceeded")

    def reconcile_paid_invoice(
        self, invoice: ProviderPaidInvoice
    ) -> PaidInvoiceReconciliationRecord:
        """Persist provider-paid fact and require exact measured-usage equality.

        ``matched`` means only that the signature-verified provider snapshot's
        configured usage line equals locally submitted fleet measurements.  It
        does not create a payment, grant an entitlement, or by itself close the
        wider accounts/billing acceptance gate. A matched reconciliation is
        terminal: later provider observations or local usage-set drift conflict
        instead of rewriting the finalized financial record.

        Provider/invoice/usage bindings are fail-safe reservations written before
        the tenant aggregate because ``StateStore`` has no cross-record
        transaction. An exact retry repairs a crash gap; contradictory reuse stays
        reserved and fails closed. This method makes no atomic multi-record claim.
        """
        facts = self._validate_paid_invoice(invoice)
        tenant_id = self._entitlements.tenant_for_customer(
            facts["external_customer_id"]
        )
        if not tenant_id:
            raise BillingReconciliationError(
                "paid invoice customer is not bound to a tenant"
            )
        subscription = self._stripe_subscription_for_tenant(tenant_id)
        if (
            subscription.external_customer_id != facts["external_customer_id"]
            or subscription.external_subscription_id
            != facts["external_subscription_id"]
        ):
            raise BillingReconciliationConflict(
                "paid invoice identity contradicts the tenant subscription binding"
            )
        billing_account_id = _required_text(
            subscription.billing_account_id, "billing_account_id"
        )
        binding = _subscription_binding_facts(
            tenant_id=tenant_id,
            billing_account_id=billing_account_id,
            customer_id=str(facts["external_customer_id"]),
            subscription_id=str(facts["external_subscription_id"]),
        )
        self._bind_subscription_indexes(binding)

        invoice_record_id = _invoice_record_id(facts["external_invoice_id"])
        self._bind_platform_index(
            kind=PAID_INVOICE_INDEX_KIND,
            record_id=invoice_record_id,
            payload={
                "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                "external_invoice_id": facts["external_invoice_id"],
                "tenant_id": tenant_id,
                "invoice_record_id": invoice_record_id,
            },
            source="billing.reconciliation.invoice_index",
            trace_id=invoice_record_id,
        )
        self._bind_provider_identity(
            kind=PROVIDER_EVENT_INDEX_KIND,
            provider_id=facts["provider_event_id"],
            provider_type="event",
            purpose="paid_invoice_observation",
            tenant_id=tenant_id,
            subject_id=invoice_record_id,
            evidence_sha256=facts["raw_event_sha256"],
            facts_sha256=facts["provider_event_facts_sha256"],
        )
        if facts["provider_request_id"] is not None:
            self._bind_provider_identity(
                kind=PROVIDER_REQUEST_INDEX_KIND,
                provider_id=facts["provider_request_id"],
                provider_type="request",
                purpose="paid_invoice_observation",
                tenant_id=tenant_id,
                subject_id=invoice_record_id,
                evidence_sha256=facts["provider_snapshot_sha256"],
                facts_sha256=facts["provider_snapshot_facts_sha256"],
            )

        lease = self._acquire_tenant_lock(
            tenant_id, holder=f"invoice-{uuid4().hex}"
        )
        unresolved: BillingReconciliationUnresolved | None = None
        try:
            period_start = _parse_time(facts["usage_period_start"])
            period_end = _parse_time(facts["usage_period_end"])
            finalized_clock = datetime.fromtimestamp(
                int(facts["invoice_finalized_at"]), tz=UTC
            )
            contract_rows = [
                row
                for row in self.list_usage(tenant_id)
                if row.outbox_state == "submitted"
                and row.billing_account_id == billing_account_id
                and row.external_customer_id == facts["external_customer_id"]
                and row.external_subscription_id
                == facts["external_subscription_id"]
                and row.meter_event_name == facts["meter_event_name"]
                and row.meter_event_version == facts["meter_event_version"]
                and row.usage_price_id == facts["usage_price_id"]
                and row.currency == facts["currency"]
                and row.livemode == facts["livemode"]
            ]
            usage_rows: list[UsageOutboxRecord] = []
            for row in contract_rows:
                meter_clock = datetime.fromtimestamp(
                    row.meter_event_timestamp, tz=UTC
                )
                # Stripe invoice line-item period.start and period.end are both
                # inclusive. Full measurement containment below is stricter
                # than timestamp-only membership and prevents a straddling run
                # from being treated as an exact line-period match.
                if not (period_start <= meter_clock <= period_end):
                    continue
                if not (
                    period_start <= _parse_time(row.measurement_started_at)
                    and _parse_time(row.measurement_ended_at) <= period_end
                ):
                    raise BillingReconciliationConflict(
                        "metered usage is not fully contained in the invoice line period"
                    )
                if row.provider_response_created is None or not (
                    datetime.fromtimestamp(row.provider_response_created, tz=UTC)
                    < finalized_clock
                ):
                    continue
                usage_rows.append(row)
            usage_rows.sort(key=lambda row: row.usage_id)
            usage_ids = tuple(row.usage_id for row in usage_rows)
            local_quantity = sum(
                row.accelerator_milliseconds for row in usage_rows
            )
            usage_set_sha256 = _usage_set_sha256(usage_rows)
            provider_quantity = facts["usage_quantity_milliseconds"]
            if provider_quantity <= 0:
                state: InvoiceReconciliationState = "unresolved"
                reason = "provider_usage_quantity_empty"
            elif not usage_rows:
                state = "unresolved"
                reason = "local_submitted_usage_empty"
            elif local_quantity != provider_quantity:
                state = "unresolved"
                reason = "metered_quantity_mismatch"
            else:
                state = "matched"
                reason = None

            now = _now_iso()
            observation = _invoice_observation_from_facts(facts)
            observation_sha256 = _canonical_sha256(observation)
            observation_fields = set(_INVOICE_OBSERVATION_FIELDS)
            immutable_invoice = {
                "tenant_id": tenant_id,
                "billing_account_id": billing_account_id,
                **{
                    key: value
                    for key, value in facts.items()
                    if key not in observation_fields
                },
            }
            immutable_invoice_sha256 = _canonical_sha256(immutable_invoice)
            for _ in range(MAX_WRITE_RETRIES):
                existing = self._store.get(
                    tenant_id, PAID_INVOICE_KIND, invoice_record_id
                )
                current: PaidInvoiceReconciliationRecord | None = None
                observations: list[dict[str, object]] = []
                if existing is not None:
                    current = self._invoice_from_record(
                        existing, validate_usage_set=False
                    )
                    if (
                        str(existing.payload.get("immutable_invoice_sha256"))
                        != immutable_invoice_sha256
                    ):
                        raise BillingReconciliationConflict(
                            "paid invoice id was replayed with contradictory provider facts"
                        )
                    observations = [
                        dict(item)
                        for item in _validated_invoice_observations(
                            existing.payload.get("provider_observations"),
                            allowed_receipt_hosts=(
                                self._customer_receipt_allowed_hosts
                            ),
                            require_provider_request_id=bool(facts["livemode"]),
                        )
                    ]
                    latest = observations[-1]
                    latest_sha256 = _canonical_sha256(latest)
                    if current.reconciliation_state == "matched":
                        same_matched_financial_result = (
                            state == "matched"
                            and current.usage_ids == usage_ids
                            and current.usage_set_sha256 == usage_set_sha256
                            and current.provider_quantity_milliseconds
                            == provider_quantity
                            and current.local_quantity_milliseconds
                            == local_quantity
                        )
                        if same_matched_financial_result and (
                            latest_sha256 == observation_sha256
                        ):
                            return current
                        if not (
                            same_matched_financial_result
                            and _is_fresh_replay_of_matched_observation(
                                latest, observation
                            )
                        ):
                            raise BillingReconciliationConflict(
                                "matched paid invoice reconciliation is immutable"
                            )
                    if latest_sha256 == observation_sha256:
                        if (
                            current.reconciliation_state == state
                            and current.usage_set_sha256 == usage_set_sha256
                            and current.provider_quantity_milliseconds
                            == provider_quantity
                            and current.local_quantity_milliseconds == local_quantity
                        ):
                            return current
                    else:
                        _require_newer_invoice_observation(latest, observation)
                        if len(observations) >= MAX_PROVIDER_INVOICE_OBSERVATIONS:
                            raise BillingReconciliationError(
                                "provider invoice observation limit exceeded"
                            )
                        observations.append(observation)
                else:
                    observations = [observation]

                # A matched aggregate is checked above before any additional
                # usage reservation. This prevents a contradictory retry from
                # permanently binding a late usage row to a finalized invoice.
                if state == "matched":
                    already_used = self._usage_ids_in_other_matched_invoices(
                        tenant_id, excluding_invoice_id=invoice_record_id
                    )
                    overlap = already_used.intersection(usage_ids)
                    if overlap:
                        raise BillingReconciliationConflict(
                            "submitted usage is already reconciled to another paid invoice"
                        )
                    for usage_id in usage_ids:
                        self._bind_platform_index(
                            kind=USAGE_INVOICE_INDEX_KIND,
                            record_id=usage_id,
                            payload={
                                "schema_version": (
                                    BILLING_RECONCILIATION_SCHEMA_VERSION
                                ),
                                "tenant_id": tenant_id,
                                "usage_id": usage_id,
                                "invoice_record_id": invoice_record_id,
                            },
                            source=(
                                "billing.reconciliation.usage_invoice_index"
                            ),
                            trace_id=invoice_record_id,
                        )

                payload: dict[str, object] = {
                    "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                    "tenant_id": tenant_id,
                    "billing_account_id": billing_account_id,
                    "invoice_record_id": invoice_record_id,
                    "external_invoice_id": facts["external_invoice_id"],
                    "external_customer_id": facts["external_customer_id"],
                    "external_subscription_id": facts[
                        "external_subscription_id"
                    ],
                    "provider_event_id": facts["provider_event_id"],
                    "provider_event_created": facts["provider_event_created"],
                    "invoice_created": facts["invoice_created"],
                    "invoice_finalized_at": facts["invoice_finalized_at"],
                    "provider_request_id": facts["provider_request_id"],
                    "provider_snapshot_sha256": facts[
                        "provider_snapshot_sha256"
                    ],
                    "provider_snapshot_facts_sha256": facts[
                        "provider_snapshot_facts_sha256"
                    ],
                    "provider_snapshot_facts": facts[
                        "provider_snapshot_facts"
                    ],
                    "provider_snapshot_retrieved_at": facts[
                        "provider_snapshot_retrieved_at"
                    ],
                    "raw_event_sha256": facts["raw_event_sha256"],
                    "provider_event_facts_sha256": facts[
                        "provider_event_facts_sha256"
                    ],
                    "provider_event_facts": facts["provider_event_facts"],
                    "hosted_invoice_url": facts["hosted_invoice_url"],
                    "invoice_pdf": facts["invoice_pdf"],
                    "invoice_pdf_http_status": facts[
                        "invoice_pdf_http_status"
                    ],
                    "invoice_pdf_content_type": facts[
                        "invoice_pdf_content_type"
                    ],
                    "invoice_pdf_size_bytes": facts[
                        "invoice_pdf_size_bytes"
                    ],
                    "invoice_pdf_sha256": facts[
                        "invoice_pdf_sha256"
                    ],
                    "invoice_pdf_retrieved_at": facts[
                        "invoice_pdf_retrieved_at"
                    ],
                    "provider_observations": observations,
                    "latest_observation_sha256": _canonical_sha256(
                        observations[-1]
                    ),
                    "provider_status": "paid",
                    "provider_paid": True,
                    "currency": facts["currency"],
                    "amount_due_minor": facts["amount_due_minor"],
                    "amount_paid_minor": facts["amount_paid_minor"],
                    "usage_price_id": facts["usage_price_id"],
                    "meter_event_name": facts["meter_event_name"],
                    "meter_event_version": facts["meter_event_version"],
                    "livemode": facts["livemode"],
                    "usage_period_start": facts["usage_period_start"],
                    "usage_period_end": facts["usage_period_end"],
                    "paid_at": facts["paid_at"],
                    "provider_quantity_milliseconds": provider_quantity,
                    "local_quantity_milliseconds": local_quantity,
                    "usage_ids": list(usage_ids),
                    "usage_set_sha256": usage_set_sha256,
                    "reconciliation_state": state,
                    "unresolved_reason": reason,
                    "reconciled_at": (
                        current.reconciled_at
                        if current is not None
                        and current.reconciliation_state == "matched"
                        else now if state == "matched" else None
                    ),
                    "immutable_invoice_sha256": immutable_invoice_sha256,
                    "created_at": (
                        existing.payload.get("created_at")
                        if existing is not None
                        else now
                    ),
                    "updated_at": now,
                }
                payload = _seal_payload(payload)
                record = (
                    existing.with_payload(payload)
                    if existing is not None
                    else LedgerRecord.new(
                        tenant_id=tenant_id,
                        kind=PAID_INVOICE_KIND,
                        record_id=invoice_record_id,
                        payload=payload,
                        source="billing.reconciliation.paid_invoice",
                        trace_id=facts["provider_event_id"],
                    )
                )
                try:
                    stored = self._store.put(
                        record,
                        expected_version=existing.version if existing is not None else 0,
                    )
                    result = self._invoice_from_record(
                        stored, validate_usage_set=True
                    )
                    if state == "unresolved":
                        unresolved = BillingReconciliationUnresolved(
                            record_id=invoice_record_id,
                            reason=str(reason),
                            expected_quantity=local_quantity,
                            provider_quantity=provider_quantity,
                        )
                    else:
                        return result
                    break
                except VersionConflict:
                    continue
            else:
                raise BillingReconciliationError(
                    "paid invoice reconciliation contention exceeded"
                )
        finally:
            self._store.release_lease(lease.token)
        if unresolved is not None:
            raise unresolved
        raise BillingReconciliationError("paid invoice reconciliation failed closed")

    def get_invoice(
        self, tenant_id: str, invoice_record_id: str
    ) -> PaidInvoiceReconciliationRecord | None:
        record = self._store.get(
            tenant_id, PAID_INVOICE_KIND, invoice_record_id
        )
        return (
            self._invoice_from_record(record, validate_usage_set=True)
            if record is not None
            else None
        )

    def list_invoices(
        self, tenant_id: str
    ) -> tuple[PaidInvoiceReconciliationRecord, ...]:
        return tuple(
            self._invoice_from_record(record, validate_usage_set=True)
            for record in self._store.list(tenant_id, PAID_INVOICE_KIND)
        )

    def public_usage_projection(
        self, *, tenant_id: str, usage_id: str
    ) -> dict[str, object] | None:
        usage = self.get_usage(tenant_id, usage_id)
        if usage is None:
            return None
        return {
            "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
            "usage_id": usage.usage_id,
            "run_id": usage.run_id,
            "source": "fleet_measured",
            "accelerator_milliseconds": usage.accelerator_milliseconds,
            "measurement_started_at": usage.measurement_started_at,
            "measurement_ended_at": usage.measurement_ended_at,
            "receipt_sha256": usage.receipt_sha256,
            "receipt_schema_version": usage.receipt_schema_version,
            "receipt_size_bytes": usage.receipt_size_bytes,
            "meter_event_version": usage.meter_event_version,
            "meter_event_timestamp": usage.meter_event_timestamp,
            "meter_event_ref": self._provider_ref(
                "meter_event_identifier", usage.meter_event_identifier
            ),
            "meter_event_request_sha256": usage.meter_event_request_sha256,
            "currency": usage.currency,
            "livemode": usage.livemode,
            "outbox_state": usage.outbox_state,
            "attempt_count": usage.attempt_count,
            "last_failure_code": usage.last_failure_code,
            "customer_ref": self._provider_ref(
                "customer", usage.external_customer_id
            ),
            "subscription_ref": self._provider_ref(
                "subscription", usage.external_subscription_id
            ),
            "provider_request_ref": (
                self._provider_ref("request", usage.provider_request_id)
                if usage.provider_request_id
                else None
            ),
            "submitted_at": usage.submitted_at,
            "last_attempt_at": usage.last_attempt_at,
            "provider_response_created": usage.provider_response_created,
            "provider_response_sha256": usage.provider_response_sha256,
            "provider_response_facts_sha256": (
                usage.provider_response_facts_sha256
            ),
        }

    def public_invoice_projection(
        self, *, tenant_id: str, invoice_record_id: str
    ) -> dict[str, object] | None:
        invoice = self.get_invoice(tenant_id, invoice_record_id)
        if invoice is None:
            return None
        return {
            "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
            "reconciliation_ref": self._provider_ref(
                "reconciliation", invoice.invoice_record_id
            ),
            "invoice_ref": self._provider_ref(
                "invoice", invoice.external_invoice_id
            ),
            "customer_ref": self._provider_ref(
                "customer", invoice.external_customer_id
            ),
            "subscription_ref": self._provider_ref(
                "subscription", invoice.external_subscription_id
            ),
            "provider_event_ref": self._provider_ref(
                "event", invoice.provider_event_id
            ),
            "provider_request_ref": (
                self._provider_ref("request", invoice.provider_request_id)
                if invoice.provider_request_id
                else None
            ),
            "hosted_invoice_ref": self._provider_ref(
                "hosted_invoice_url", invoice.hosted_invoice_url
            ),
            "invoice_pdf_ref": self._provider_ref(
                "invoice_pdf", invoice.invoice_pdf
            ),
            "invoice_pdf_http_status": (
                invoice.invoice_pdf_http_status
            ),
            "invoice_pdf_content_type": (
                invoice.invoice_pdf_content_type
            ),
            "invoice_pdf_size_bytes": invoice.invoice_pdf_size_bytes,
            "invoice_pdf_sha256": invoice.invoice_pdf_sha256,
            "invoice_pdf_retrieved_at": (
                invoice.invoice_pdf_retrieved_at
            ),
            "provider_status": "paid",
            "currency": invoice.currency,
            "amount_due_minor": invoice.amount_due_minor,
            "amount_paid_minor": invoice.amount_paid_minor,
            "usage_period_start": invoice.usage_period_start,
            "usage_period_end": invoice.usage_period_end,
            "paid_at": invoice.paid_at,
            "meter_event_version": invoice.meter_event_version,
            "livemode": invoice.livemode,
            "provider_quantity_milliseconds": (
                invoice.provider_quantity_milliseconds
            ),
            "local_quantity_milliseconds": invoice.local_quantity_milliseconds,
            "usage_set_sha256": invoice.usage_set_sha256,
            "reconciliation_state": invoice.reconciliation_state,
            "unresolved_reason": invoice.unresolved_reason,
            "reconciled_at": invoice.reconciled_at,
            "provider_snapshot_sha256": invoice.provider_snapshot_sha256,
            "provider_snapshot_facts_sha256": (
                invoice.provider_snapshot_facts_sha256
            ),
            "provider_snapshot_retrieved_at": (
                invoice.provider_snapshot_retrieved_at
            ),
            "provider_observation_count": invoice.provider_observation_count,
            "raw_event_sha256": invoice.raw_event_sha256,
            "provider_event_facts_sha256": invoice.provider_event_facts_sha256,
            "invoice_created": invoice.invoice_created,
            "invoice_finalized_at": invoice.invoice_finalized_at,
        }

    def _usage_from_record(self, record: LedgerRecord) -> UsageOutboxRecord:
        usage = UsageOutboxRecord.from_ledger(record)
        immutable_sha256 = _canonical_sha256(_usage_immutable_from_record(usage))
        binding = _subscription_binding_facts(
            tenant_id=usage.tenant_id,
            billing_account_id=usage.billing_account_id,
            customer_id=usage.external_customer_id,
            subscription_id=usage.external_subscription_id,
        )
        self._validate_subscription_indexes(binding)
        self._require_platform_index(
            kind=USAGE_RECEIPT_INDEX_KIND,
            record_id=_receipt_index_id(usage.receipt_sha256),
            payload={
                "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                "receipt_sha256": usage.receipt_sha256,
                "tenant_id": usage.tenant_id,
                "billing_account_id": usage.billing_account_id,
                "usage_id": usage.usage_id,
                "immutable_sha256": immutable_sha256,
            },
        )
        measurement = {
            "tenant_id": usage.tenant_id,
            "billing_account_id": usage.billing_account_id,
            "run_id": usage.run_id,
            "worker_id": usage.worker_id,
            "measurement_started_at": usage.measurement_started_at,
            "measurement_ended_at": usage.measurement_ended_at,
        }
        self._require_platform_index(
            kind=USAGE_MEASUREMENT_INDEX_KIND,
            record_id=_measurement_index_id(measurement),
            payload={
                "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                **measurement,
                "usage_id": usage.usage_id,
                "receipt_sha256": usage.receipt_sha256,
                "immutable_sha256": immutable_sha256,
            },
        )
        self._require_platform_index(
            kind=METER_EVENT_IDENTIFIER_INDEX_KIND,
            record_id=_meter_identifier_index_id(usage.meter_event_identifier),
            payload={
                "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                "meter_event_identifier": usage.meter_event_identifier,
                "tenant_id": usage.tenant_id,
                "usage_id": usage.usage_id,
                "meter_event_request_sha256": usage.meter_event_request_sha256,
                "immutable_sha256": immutable_sha256,
            },
        )
        if usage.provider_request_id is not None:
            self._require_platform_index(
                kind=PROVIDER_REQUEST_INDEX_KIND,
                record_id=_provider_index_id(
                    PROVIDER_REQUEST_INDEX_KIND, usage.provider_request_id
                ),
                payload={
                    "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                    "provider_id": usage.provider_request_id,
                    "provider_type": "request",
                    "purpose": "usage_submission",
                    "tenant_id": usage.tenant_id,
                    "subject_id": usage.usage_id,
                    "evidence_sha256": usage.provider_response_sha256,
                    "facts_sha256": usage.provider_response_facts_sha256,
                },
            )
        return usage

    def _invoice_from_record(
        self, record: LedgerRecord, *, validate_usage_set: bool
    ) -> PaidInvoiceReconciliationRecord:
        invoice = PaidInvoiceReconciliationRecord.from_ledger(
            record,
            allowed_receipt_hosts=self._customer_receipt_allowed_hosts,
        )
        if _invoice_record_id(invoice.external_invoice_id) != invoice.invoice_record_id:
            raise BillingReconciliationConflict(
                "invoice record id does not match its typed Stripe invoice id"
            )
        immutable_sha256 = _canonical_sha256(_invoice_immutable_from_record(invoice))
        if immutable_sha256 != _sha256(
            record.payload.get("immutable_invoice_sha256"),
            "immutable_invoice_sha256",
        ):
            raise BillingReconciliationConflict(
                "durable invoice immutable facts digest is invalid"
            )
        binding = _subscription_binding_facts(
            tenant_id=invoice.tenant_id,
            billing_account_id=invoice.billing_account_id,
            customer_id=invoice.external_customer_id,
            subscription_id=invoice.external_subscription_id,
        )
        self._validate_subscription_indexes(binding)
        self._require_platform_index(
            kind=PAID_INVOICE_INDEX_KIND,
            record_id=invoice.invoice_record_id,
            payload={
                "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                "external_invoice_id": invoice.external_invoice_id,
                "tenant_id": invoice.tenant_id,
                "invoice_record_id": invoice.invoice_record_id,
            },
        )
        observations = _validated_invoice_observations(
            record.payload.get("provider_observations"),
            allowed_receipt_hosts=self._customer_receipt_allowed_hosts,
            require_provider_request_id=invoice.livemode,
        )
        for observation in observations:
            self._require_platform_index(
                kind=PROVIDER_EVENT_INDEX_KIND,
                record_id=_provider_index_id(
                    PROVIDER_EVENT_INDEX_KIND,
                    str(observation["provider_event_id"]),
                ),
                payload={
                    "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                    "provider_id": observation["provider_event_id"],
                    "provider_type": "event",
                    "purpose": "paid_invoice_observation",
                    "tenant_id": invoice.tenant_id,
                    "subject_id": invoice.invoice_record_id,
                    "evidence_sha256": observation["raw_event_sha256"],
                    "facts_sha256": observation["provider_event_facts_sha256"],
                },
            )
            request_id = observation["provider_request_id"]
            if request_id is not None:
                self._require_platform_index(
                    kind=PROVIDER_REQUEST_INDEX_KIND,
                    record_id=_provider_index_id(
                        PROVIDER_REQUEST_INDEX_KIND, str(request_id)
                    ),
                    payload={
                        "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                        "provider_id": request_id,
                        "provider_type": "request",
                        "purpose": "paid_invoice_observation",
                        "tenant_id": invoice.tenant_id,
                        "subject_id": invoice.invoice_record_id,
                        "evidence_sha256": observation[
                            "provider_snapshot_sha256"
                        ],
                        "facts_sha256": observation[
                            "provider_snapshot_facts_sha256"
                        ],
                    },
                )
        if validate_usage_set:
            rows = self._eligible_usage_for_invoice(invoice)
            usage_ids = tuple(row.usage_id for row in rows)
            local_quantity = sum(row.accelerator_milliseconds for row in rows)
            if (
                usage_ids != invoice.usage_ids
                or local_quantity != invoice.local_quantity_milliseconds
                or _usage_set_sha256(rows) != invoice.usage_set_sha256
            ):
                raise BillingReconciliationConflict(
                    "invoice usage-set digest no longer matches durable submitted usage"
                )
            if invoice.reconciliation_state == "matched":
                for usage_id in usage_ids:
                    self._require_platform_index(
                        kind=USAGE_INVOICE_INDEX_KIND,
                        record_id=usage_id,
                        payload={
                            "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
                            "tenant_id": invoice.tenant_id,
                            "usage_id": usage_id,
                            "invoice_record_id": invoice.invoice_record_id,
                        },
                    )
        return invoice

    def _eligible_usage_for_invoice(
        self, invoice: PaidInvoiceReconciliationRecord
    ) -> list[UsageOutboxRecord]:
        period_start = _parse_time(invoice.usage_period_start)
        period_end = _parse_time(invoice.usage_period_end)
        finalized_clock = datetime.fromtimestamp(invoice.invoice_finalized_at, tz=UTC)
        result: list[UsageOutboxRecord] = []
        for row in self.list_usage(invoice.tenant_id):
            if not (
                row.outbox_state == "submitted"
                and row.billing_account_id == invoice.billing_account_id
                and row.external_customer_id == invoice.external_customer_id
                and row.external_subscription_id == invoice.external_subscription_id
                and row.meter_event_name == invoice.meter_event_name
                and row.meter_event_version == invoice.meter_event_version
                and row.usage_price_id == invoice.usage_price_id
                and row.currency == invoice.currency
                and row.livemode == invoice.livemode
            ):
                continue
            meter_clock = datetime.fromtimestamp(row.meter_event_timestamp, tz=UTC)
            if not (period_start <= meter_clock <= period_end):
                continue
            if not (
                period_start <= _parse_time(row.measurement_started_at)
                and _parse_time(row.measurement_ended_at) <= period_end
            ):
                raise BillingReconciliationConflict(
                    "metered usage is not fully contained in the invoice line period"
                )
            if row.provider_response_created is not None and datetime.fromtimestamp(
                row.provider_response_created, tz=UTC
            ) < finalized_clock:
                result.append(row)
        result.sort(key=lambda row: row.usage_id)
        return result

    def _bind_subscription_indexes(self, binding: Mapping[str, object]) -> None:
        self._bind_platform_index(
            kind=SUBSCRIPTION_BINDING_INDEX_KIND,
            record_id=_subscription_binding_index_id(
                str(binding["external_subscription_id"])
            ),
            payload=binding,
            source="billing.reconciliation.subscription_binding_index",
            trace_id=str(binding["tenant_id"]),
        )
        self._bind_platform_index(
            kind=CUSTOMER_BINDING_INDEX_KIND,
            record_id=_customer_binding_index_id(str(binding["external_customer_id"])),
            payload=binding,
            source="billing.reconciliation.customer_binding_index",
            trace_id=str(binding["tenant_id"]),
        )

    def _validate_subscription_indexes(
        self, binding: Mapping[str, object]
    ) -> None:
        self._require_platform_index(
            kind=SUBSCRIPTION_BINDING_INDEX_KIND,
            record_id=_subscription_binding_index_id(
                str(binding["external_subscription_id"])
            ),
            payload=binding,
        )
        self._require_platform_index(
            kind=CUSTOMER_BINDING_INDEX_KIND,
            record_id=_customer_binding_index_id(str(binding["external_customer_id"])),
            payload=binding,
        )

    def _require_platform_index(
        self, *, kind: str, record_id: str, payload: Mapping[str, object]
    ) -> None:
        record = self._store.get(
            BILLING_RECONCILIATION_PLATFORM_TENANT, kind, record_id
        )
        if record is None:
            raise BillingReconciliationConflict(f"{kind} binding is missing")
        _validate_index_record(record, kind=kind, record_id=record_id)
        if _canonical_sha256(record.payload) != _canonical_sha256(
            _seal_index_payload(payload)
        ):
            raise BillingReconciliationConflict(
                f"{kind} identity is bound to contradictory facts"
            )

    def _stripe_subscription_for_tenant(
        self, tenant_id: str
    ) -> SubscriptionRecord:
        tenant = _required_text(tenant_id, "tenant_id")
        subscription = self._entitlements.get_subscription(tenant)
        if (
            subscription is None
            or subscription.source != "stripe_verified"
            or not subscription.external_customer_id
            or not subscription.external_subscription_id
            or not subscription.billing_account_id
        ):
            raise BillingReconciliationError(
                "tenant does not have a Stripe-verified provider binding"
            )
        customer_id = _stripe_id(
            subscription.external_customer_id, "external_customer_id", "customer"
        )
        _stripe_id(
            subscription.external_subscription_id,
            "external_subscription_id",
            "subscription",
        )
        _required_text(subscription.billing_account_id, "billing_account_id")
        indexed_tenant = self._entitlements.tenant_for_customer(customer_id)
        if indexed_tenant != tenant:
            raise BillingReconciliationConflict(
                "Stripe subscription customer index contradicts the tenant binding"
            )
        return subscription

    def _validate_paid_invoice(
        self, invoice: ProviderPaidInvoice
    ) -> dict[str, object]:
        if not isinstance(invoice, ProviderPaidInvoice):
            raise BillingReconciliationError(
                "reconcile_paid_invoice requires ProviderPaidInvoice"
            )
        provider_paid = _strict_bool(invoice.provider_paid, "provider_paid")
        if invoice.provider_status != "paid" or not provider_paid:
            raise BillingReconciliationError(
                "only a provider-paid invoice snapshot may be reconciled"
            )
        price_id = _stripe_id(invoice.usage_price_id, "usage_price_id", "price")
        if price_id != self._usage_price_id:
            raise BillingReconciliationError(
                "invoice usage line does not match the configured usage price"
            )
        meter_event_name = _meter_event_name(
            invoice.meter_event_name, "meter_event_name"
        )
        meter_event_version = _safe_code(
            invoice.meter_event_version, "meter_event_version"
        )
        if (
            meter_event_name != self._meter_event_name
            or meter_event_version != self._meter_event_version
        ):
            raise BillingReconciliationError(
                "invoice usage line does not match the configured meter contract"
            )
        livemode = _strict_bool(invoice.livemode, "livemode")
        if livemode != self._livemode:
            raise BillingReconciliationError(
                "invoice livemode does not match the configured billing mode"
            )
        provider_request_id = _optional_stripe_id(
            invoice.provider_request_id, "provider_request_id", "request"
        )
        if livemode and provider_request_id is None:
            raise BillingReconciliationError(
                "live provider invoice observation requires a provider request receipt"
            )
        currency = _currency(invoice.currency)
        if currency != self._currency:
            raise BillingReconciliationError(
                "invoice currency does not match the configured usage currency"
            )
        period_start = _normalized_whole_second_time(
            invoice.usage_period_start, "usage_period_start"
        )
        period_end = _normalized_whole_second_time(
            invoice.usage_period_end, "usage_period_end"
        )
        period_start_clock = _parse_time(period_start)
        period_end_clock = _parse_time(period_end)
        if period_end_clock <= period_start_clock:
            raise BillingReconciliationError(
                "invoice usage period end must be after its start"
            )
        if period_end_clock - period_start_clock > timedelta(days=366):
            raise BillingReconciliationError(
                "invoice usage period exceeds the bounded reconciliation window"
            )
        paid_at = _normalized_whole_second_time(invoice.paid_at, "paid_at")
        paid_clock = _parse_time(paid_at)
        invoice_created = _positive_int(invoice.created, "invoice.created")
        invoice_finalized_at = _positive_int(
            invoice.status_transitions_finalized_at,
            "invoice.status_transitions.finalized_at",
        )
        event_created = _positive_int(
            invoice.provider_event_created, "provider_event_created"
        )
        try:
            invoice_created_clock = datetime.fromtimestamp(invoice_created, tz=UTC)
            finalized_clock = datetime.fromtimestamp(invoice_finalized_at, tz=UTC)
            event_clock = datetime.fromtimestamp(event_created, tz=UTC)
        except (OverflowError, OSError, ValueError) as exc:
            raise BillingReconciliationError(
                "provider_event_created is outside the supported timestamp range"
            ) from exc
        now = datetime.now(UTC)
        if invoice_created_clock > finalized_clock:
            raise BillingReconciliationError(
                "invoice finalization cannot predate invoice creation"
            )
        if period_end_clock > finalized_clock:
            raise BillingReconciliationError(
                "invoice finalization cannot predate the usage line period end"
            )
        if paid_clock < period_end_clock:
            raise BillingReconciliationError(
                "invoice payment cannot predate the usage line period end"
            )
        if paid_clock < finalized_clock:
            raise BillingReconciliationError(
                "invoice payment cannot predate invoice finalization"
            )
        if event_clock < paid_clock:
            raise BillingReconciliationError(
                "provider event cannot predate invoice payment"
            )
        if event_clock - paid_clock > MAX_PROVIDER_SUBMISSION_LAG:
            raise BillingReconciliationError(
                "provider paid event exceeds the bounded observation window"
            )
        if paid_clock > now + MAX_CLOCK_SKEW or event_clock > now + MAX_CLOCK_SKEW:
            raise BillingReconciliationError(
                "invoice payment/event timestamp is unreasonably in the future"
            )
        snapshot_retrieved_at = _normalized_time(
            invoice.provider_snapshot_retrieved_at,
            "provider_snapshot_retrieved_at",
        )
        snapshot_clock = _parse_time(snapshot_retrieved_at)
        if snapshot_clock < event_clock or snapshot_clock > now + MAX_CLOCK_SKEW:
            raise BillingReconciliationError(
                "provider snapshot retrieval time is outside the trusted event window"
            )
        if snapshot_clock < now - MAX_PROVIDER_READBACK_AGE:
            raise BillingReconciliationError(
                "provider invoice snapshot is not a fresh readback"
            )
        invoice_pdf_retrieved_at = _normalized_time(
            invoice.invoice_pdf_retrieved_at,
            "invoice_pdf_retrieved_at",
        )
        receipt_clock = _parse_time(invoice_pdf_retrieved_at)
        if receipt_clock < paid_clock or receipt_clock > now + MAX_CLOCK_SKEW:
            raise BillingReconciliationError(
                "invoice PDF retrieval time is outside the trusted payment window"
            )
        if receipt_clock < now - MAX_PROVIDER_READBACK_AGE:
            raise BillingReconciliationError(
                "customer invoice PDF is not a fresh readback"
            )
        amount_due = _nonnegative_int(invoice.amount_due_minor, "amount_due_minor")
        amount_paid = _nonnegative_int(invoice.amount_paid_minor, "amount_paid_minor")
        if amount_paid != amount_due:
            raise BillingReconciliationError(
                "provider-paid invoice requires amount_paid_minor to equal amount_due_minor"
            )
        facts: dict[str, object] = {
            "provider_event_id": _stripe_id(
                invoice.provider_event_id, "provider_event_id", "event"
            ),
            "provider_event_created": event_created,
            "invoice_created": invoice_created,
            "invoice_finalized_at": invoice_finalized_at,
            "external_invoice_id": _stripe_id(
                invoice.external_invoice_id, "external_invoice_id", "invoice"
            ),
            "external_customer_id": _stripe_id(
                invoice.external_customer_id, "external_customer_id", "customer"
            ),
            "external_subscription_id": _stripe_id(
                invoice.external_subscription_id,
                "external_subscription_id",
                "subscription",
            ),
            "provider_request_id": provider_request_id,
            "provider_snapshot_sha256": _sha256(
                invoice.provider_snapshot_sha256, "provider_snapshot_sha256"
            ),
            "provider_snapshot_retrieved_at": snapshot_retrieved_at,
            "raw_event_sha256": _sha256(
                invoice.raw_event_sha256, "raw_event_sha256"
            ),
            "hosted_invoice_url": _canonical_https_url(
                invoice.hosted_invoice_url,
                allowed_hosts=self._customer_receipt_allowed_hosts,
            ),
            "invoice_pdf": _canonical_https_url(
                invoice.invoice_pdf,
                allowed_hosts=self._customer_receipt_allowed_hosts,
            ),
            "invoice_pdf_http_status": _customer_receipt_status(
                invoice.invoice_pdf_http_status
            ),
            "invoice_pdf_content_type": _customer_receipt_content_type(
                invoice.invoice_pdf_content_type
            ),
            "invoice_pdf_size_bytes": _bounded_customer_receipt_size(
                invoice.invoice_pdf_size_bytes
            ),
            "invoice_pdf_sha256": _sha256(
                invoice.invoice_pdf_sha256, "invoice_pdf_sha256"
            ),
            "invoice_pdf_retrieved_at": invoice_pdf_retrieved_at,
            "currency": currency,
            "amount_due_minor": amount_due,
            "amount_paid_minor": amount_paid,
            "usage_price_id": price_id,
            "meter_event_name": meter_event_name,
            "meter_event_version": meter_event_version,
            "livemode": livemode,
            "usage_quantity_milliseconds": _nonnegative_int(
                invoice.usage_quantity_milliseconds,
                "usage_quantity_milliseconds",
            ),
            "usage_period_start": period_start,
            "usage_period_end": period_end,
            "paid_at": paid_at,
        }
        snapshot_facts = {
            key: value
            for key, value in facts.items()
            if key
            not in {
                "provider_event_id",
                "provider_event_created",
                "provider_request_id",
                "provider_snapshot_sha256",
                "provider_snapshot_retrieved_at",
                "raw_event_sha256",
            }
        }
        event_facts = {
            "id": facts["provider_event_id"],
            "created": facts["provider_event_created"],
            "type": "invoice.paid",
            "invoice": facts["external_invoice_id"],
            "livemode": facts["livemode"],
        }
        facts["provider_snapshot_facts_sha256"] = _canonical_sha256(
            snapshot_facts
        )
        facts["provider_event_facts_sha256"] = _canonical_sha256(event_facts)
        facts["provider_snapshot_facts"] = snapshot_facts
        facts["provider_event_facts"] = event_facts
        return facts

    def _bind_platform_index(
        self,
        *,
        kind: str,
        record_id: str,
        payload: Mapping[str, object],
        source: str,
        trace_id: str,
    ) -> None:
        sealed_payload = _seal_index_payload(payload)
        _validate_index_payload(kind, record_id, sealed_payload)
        expected_digest = _canonical_sha256(sealed_payload)
        for _ in range(MAX_WRITE_RETRIES):
            existing = self._store.get(
                BILLING_RECONCILIATION_PLATFORM_TENANT, kind, record_id
            )
            if existing is not None:
                _validate_index_record(existing, kind=kind, record_id=record_id)
                if _canonical_sha256(existing.payload) != expected_digest:
                    raise BillingReconciliationConflict(
                        f"{kind} identity is already bound to contradictory facts"
                    )
                return
            record = LedgerRecord.new(
                tenant_id=BILLING_RECONCILIATION_PLATFORM_TENANT,
                kind=kind,
                record_id=record_id,
                payload=sealed_payload,
                source=source,
                trace_id=trace_id,
            )
            try:
                self._store.put(record, expected_version=0)
                return
            except VersionConflict:
                continue
        raise BillingReconciliationError(f"{kind} binding contention exceeded")

    def _bind_provider_identity(
        self,
        *,
        kind: str,
        provider_id: str,
        provider_type: str,
        purpose: str,
        tenant_id: str,
        subject_id: str,
        evidence_sha256: str | None = None,
        facts_sha256: str | None = None,
    ) -> None:
        typed_provider_id = _stripe_id(
            provider_id, "provider_identity", provider_type
        )
        payload: dict[str, object] = {
            "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
            "provider_id": typed_provider_id,
            "provider_type": _safe_code(provider_type, "provider_type"),
            "purpose": _safe_code(purpose, "provider_identity_purpose"),
            "tenant_id": _required_text(tenant_id, "tenant_id"),
            "subject_id": _required_text(subject_id, "subject_id"),
        }
        if evidence_sha256 is not None:
            payload["evidence_sha256"] = _sha256(
                evidence_sha256, "provider_identity_evidence_sha256"
            )
        if facts_sha256 is not None:
            payload["facts_sha256"] = _sha256(
                facts_sha256, "provider_identity_facts_sha256"
            )
        self._bind_platform_index(
            kind=kind,
            record_id=_provider_index_id(kind, typed_provider_id),
            payload=payload,
            source="billing.reconciliation.provider_identity_index",
            trace_id=subject_id,
        )

    def _usage_ids_in_other_matched_invoices(
        self, tenant_id: str, *, excluding_invoice_id: str
    ) -> set[str]:
        used: set[str] = set()
        for record in self._store.list(tenant_id, PAID_INVOICE_KIND):
            if record.record_id == excluding_invoice_id:
                continue
            invoice = self._invoice_from_record(
                record, validate_usage_set=True
            )
            if invoice.reconciliation_state == "matched":
                used.update(invoice.usage_ids)
        return used

    def _acquire_tenant_lock(self, tenant_id: str, *, holder: str):
        try:
            return self._store.acquire_lease(
                tenant_id,
                "billing-reconciliation",
                holder=holder,
                ttl_seconds=30,
            )
        except LeaseHeld as exc:
            raise BillingReconciliationError(
                "another billing reconciliation transition is in progress"
            ) from exc

    def _provider_ref(self, kind: str, value: str) -> str:
        digest = hmac.new(
            self._provider_reference_hash_key,
            f"{kind}\0{value}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"hmac-sha256:{digest}"


def _validate_measurement(measurement: FleetUsageMeasurement) -> dict[str, object]:
    if not isinstance(measurement, FleetUsageMeasurement):
        raise BillingReconciliationError(
            "record_fleet_measurement requires FleetUsageMeasurement"
        )
    if measurement.source != "fleet_measured":
        raise BillingReconciliationError(
            "planner estimates and declared quantities are not billable measurements"
        )
    tenant_id = _required_text(measurement.tenant_id, "tenant_id")
    billing_account_id = _required_text(
        measurement.billing_account_id, "billing_account_id"
    )
    run_id = _required_text(measurement.run_id, "run_id")
    worker_id = _required_text(measurement.worker_id, "worker_id")
    quantity = _positive_int(
        measurement.accelerator_milliseconds, "accelerator_milliseconds"
    )
    accelerator_count = _positive_int(
        measurement.accelerator_count, "accelerator_count"
    )
    if accelerator_count > 128:
        raise BillingReconciliationError("accelerator_count exceeds 128")
    started = _normalized_time(
        measurement.measurement_started_at, "measurement_started_at"
    )
    ended = _normalized_time(
        measurement.measurement_ended_at, "measurement_ended_at"
    )
    span = _parse_time(ended) - _parse_time(started)
    if span <= timedelta(0) or span > MAX_MEASUREMENT_SPAN:
        raise BillingReconciliationError(
            "measurement span must be positive and no longer than 31 days"
        )
    maximum_quantity = int(span.total_seconds() * 1000) * accelerator_count
    if quantity > maximum_quantity:
        raise BillingReconciliationError(
            "accelerator milliseconds exceed wall time multiplied by accelerator count"
        )
    return {
        "tenant_id": tenant_id,
        "billing_account_id": billing_account_id,
        "run_id": run_id,
        "worker_id": worker_id,
        "accelerator_milliseconds": quantity,
        "accelerator_count": accelerator_count,
        "measurement_started_at": started,
        "measurement_ended_at": ended,
        "receipt_sha256": _sha256(
            measurement.receipt_sha256, "receipt_sha256"
        ),
        "receipt_schema_version": _safe_code(
            measurement.receipt_schema_version, "receipt_schema_version"
        ),
        "receipt_size_bytes": _bounded_receipt_size(
            measurement.receipt_size_bytes
        ),
        "receipt_issuer": _required_text(
            measurement.receipt_issuer, "receipt_issuer"
        ),
        "source": "fleet_measured",
    }


def _greatest_whole_second_inside(start: object, end: object) -> int:
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    start_delta = _parse_time(start) - epoch
    end_delta = _parse_time(end) - epoch
    start_us = (
        start_delta.days * 86_400_000_000
        + start_delta.seconds * 1_000_000
        + start_delta.microseconds
    )
    end_us = (
        end_delta.days * 86_400_000_000
        + end_delta.seconds * 1_000_000
        + end_delta.microseconds
    )
    candidate = (end_us - 1) // 1_000_000
    if candidate * 1_000_000 <= start_us:
        raise BillingReconciliationError(
            "measurement contains no whole-second timestamp strictly inside its interval"
        )
    return candidate


def _meter_event_request(
    *,
    event_name: object,
    customer_id: object,
    quantity: object,
    identifier: object,
    timestamp: object,
) -> dict[str, object]:
    name = _meter_event_name(event_name, "event_name")
    customer = _stripe_id(customer_id, "stripe_customer_id", "customer")
    amount = _positive_int(quantity, "value")
    event_identifier = _meter_identifier(identifier, "identifier")
    event_timestamp = _positive_int(timestamp, "timestamp")
    return {
        "event_name": name,
        "payload": {
            "stripe_customer_id": customer,
            "value": str(amount),
        },
        "identifier": event_identifier,
        "timestamp": event_timestamp,
    }


def _validate_meter_event_response(value: object) -> dict[str, object]:
    expected_fields = {
        "object",
        "created",
        "event_name",
        "identifier",
        "livemode",
        "payload",
        "timestamp",
    }
    if (
        not isinstance(value, Mapping)
        or len(value) != len(expected_fields)
        or set(value) != expected_fields
    ):
        raise BillingReconciliationError(
            "Stripe Meter Event response schema is invalid"
        )
    payload = value.get("payload")
    payload_fields = {"stripe_customer_id", "value"}
    if (
        not isinstance(payload, Mapping)
        or len(payload) != len(payload_fields)
        or set(payload) != payload_fields
    ):
        raise BillingReconciliationError(
            "Stripe Meter Event response payload schema is invalid"
        )
    if value.get("object") != "billing.meter_event":
        raise BillingReconciliationError(
            "Stripe Meter Event response object is invalid"
        )
    raw_quantity = payload.get("value")
    if not isinstance(raw_quantity, str):
        raise BillingReconciliationError(
            "Stripe Meter Event response value must be a decimal string"
        )
    quantity = _positive_decimal_string_int(raw_quantity, "payload.value")
    return {
        "object": "billing.meter_event",
        "created": _positive_int(value.get("created"), "created"),
        "event_name": _meter_event_name(value.get("event_name"), "event_name"),
        "identifier": _meter_identifier(value.get("identifier"), "identifier"),
        "livemode": _strict_bool(value.get("livemode"), "livemode"),
        "payload": {
            "stripe_customer_id": _stripe_id(
                payload.get("stripe_customer_id"),
                "payload.stripe_customer_id",
                "customer",
            ),
            "value": str(quantity),
        },
        "timestamp": _positive_int(value.get("timestamp"), "timestamp"),
    }


def _expected_meter_event_response(
    usage: UsageOutboxRecord, created: int
) -> dict[str, object]:
    request = usage.meter_event_request()
    return {
        "object": "billing.meter_event",
        "created": _positive_int(created, "created"),
        "event_name": request["event_name"],
        "identifier": request["identifier"],
        "livemode": usage.livemode,
        "payload": request["payload"],
        "timestamp": request["timestamp"],
    }


def _usage_immutable_from_record(usage: UsageOutboxRecord) -> dict[str, object]:
    return {
        "tenant_id": usage.tenant_id,
        "billing_account_id": usage.billing_account_id,
        "run_id": usage.run_id,
        "worker_id": usage.worker_id,
        "accelerator_milliseconds": usage.accelerator_milliseconds,
        "accelerator_count": usage.accelerator_count,
        "measurement_started_at": usage.measurement_started_at,
        "measurement_ended_at": usage.measurement_ended_at,
        "receipt_sha256": usage.receipt_sha256,
        "receipt_schema_version": usage.receipt_schema_version,
        "receipt_size_bytes": usage.receipt_size_bytes,
        "receipt_issuer": usage.receipt_issuer,
        "source": "fleet_measured",
        "usage_id": usage.usage_id,
        "external_customer_id": usage.external_customer_id,
        "external_subscription_id": usage.external_subscription_id,
        "meter_event_name": usage.meter_event_name,
        "meter_event_version": usage.meter_event_version,
        "meter_event_timestamp": usage.meter_event_timestamp,
        "usage_price_id": usage.usage_price_id,
        "currency": usage.currency,
        "livemode": usage.livemode,
        "meter_event_identifier": usage.meter_event_identifier,
        "meter_event_request_sha256": usage.meter_event_request_sha256,
    }


def _subscription_binding_facts(
    *,
    tenant_id: object,
    billing_account_id: object,
    customer_id: object,
    subscription_id: object,
) -> dict[str, object]:
    base: dict[str, object] = {
        "schema_version": BILLING_RECONCILIATION_SCHEMA_VERSION,
        "tenant_id": _required_text(tenant_id, "tenant_id"),
        "billing_account_id": _required_text(
            billing_account_id, "billing_account_id"
        ),
        "external_customer_id": _stripe_id(
            customer_id, "external_customer_id", "customer"
        ),
        "external_subscription_id": _stripe_id(
            subscription_id, "external_subscription_id", "subscription"
        ),
    }
    base["binding_sha256"] = _canonical_sha256(base)
    return base


def _usage_id(receipt_sha256: object) -> str:
    digest = hashlib.sha256(
        (
            BILLING_RECONCILIATION_SCHEMA_VERSION
            + "\0usage\0"
            + _sha256(receipt_sha256, "receipt_sha256")
        ).encode("utf-8")
    ).hexdigest()
    return f"usage-{digest}"


def _receipt_index_id(receipt_sha256: object) -> str:
    digest = hashlib.sha256(
        ("receipt\0" + _sha256(receipt_sha256, "receipt_sha256")).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"receipt-{digest}"


def _measurement_index_id(measurement: Mapping[str, object]) -> str:
    semantic_identity = {
        "tenant_id": measurement["tenant_id"],
        "billing_account_id": measurement["billing_account_id"],
        "run_id": measurement["run_id"],
        "worker_id": measurement["worker_id"],
        "measurement_started_at": measurement["measurement_started_at"],
        "measurement_ended_at": measurement["measurement_ended_at"],
    }
    return f"measurement-{_canonical_sha256(semantic_identity)}"


def _invoice_record_id(external_invoice_id: object) -> str:
    provider_id = _stripe_id(
        external_invoice_id, "external_invoice_id", "invoice"
    )
    digest = hashlib.sha256(("invoice\0" + provider_id).encode("utf-8")).hexdigest()
    return f"invoice-{digest}"


def _provider_index_id(kind: str, provider_id: str) -> str:
    digest = hashlib.sha256(
        f"{kind}\0{provider_id}".encode("utf-8")
    ).hexdigest()
    return f"provider-{digest}"


def _meter_identifier_index_id(identifier: object) -> str:
    value = _meter_identifier(identifier, "meter_event_identifier")
    return f"identifier-{_canonical_sha256({'identifier': value})}"


def _subscription_binding_index_id(subscription_id: object) -> str:
    value = _stripe_id(
        subscription_id, "external_subscription_id", "subscription"
    )
    return f"subscription-{_canonical_sha256({'subscription': value})}"


def _customer_binding_index_id(customer_id: object) -> str:
    value = _stripe_id(customer_id, "external_customer_id", "customer")
    return f"customer-{_canonical_sha256({'customer': value})}"


def _validate_index_record(
    record: LedgerRecord, *, kind: str, record_id: str
) -> None:
    if (
        record.tenant_id != BILLING_RECONCILIATION_PLATFORM_TENANT
        or record.kind != kind
        or record.record_id != record_id
    ):
        raise BillingReconciliationConflict(
            "billing cross-index ledger envelope is invalid"
        )
    _validate_index_payload(kind, record_id, record.payload)


def _validate_index_payload(
    kind: str, record_id: str, payload: Mapping[str, object]
) -> None:
    _require_schema(payload)
    common = {"schema_version", "index_sha256"}
    expected_fields_by_kind = {
        USAGE_RECEIPT_INDEX_KIND: common
        | {
            "receipt_sha256",
            "tenant_id",
            "billing_account_id",
            "usage_id",
            "immutable_sha256",
        },
        USAGE_MEASUREMENT_INDEX_KIND: common
        | {
            "tenant_id",
            "billing_account_id",
            "run_id",
            "worker_id",
            "measurement_started_at",
            "measurement_ended_at",
            "usage_id",
            "receipt_sha256",
            "immutable_sha256",
        },
        PAID_INVOICE_INDEX_KIND: common
        | {"external_invoice_id", "tenant_id", "invoice_record_id"},
        PROVIDER_EVENT_INDEX_KIND: common
        | {
            "provider_id",
            "provider_type",
            "purpose",
            "tenant_id",
            "subject_id",
            "evidence_sha256",
            "facts_sha256",
        },
        PROVIDER_REQUEST_INDEX_KIND: common
        | {
            "provider_id",
            "provider_type",
            "purpose",
            "tenant_id",
            "subject_id",
            "evidence_sha256",
            "facts_sha256",
        },
        METER_EVENT_IDENTIFIER_INDEX_KIND: common
        | {
            "meter_event_identifier",
            "tenant_id",
            "usage_id",
            "meter_event_request_sha256",
            "immutable_sha256",
        },
        SUBSCRIPTION_BINDING_INDEX_KIND: common
        | {
            "tenant_id",
            "billing_account_id",
            "external_customer_id",
            "external_subscription_id",
            "binding_sha256",
        },
        CUSTOMER_BINDING_INDEX_KIND: common
        | {
            "tenant_id",
            "billing_account_id",
            "external_customer_id",
            "external_subscription_id",
            "binding_sha256",
        },
        USAGE_INVOICE_INDEX_KIND: common
        | {"tenant_id", "usage_id", "invoice_record_id"},
    }
    expected_fields = expected_fields_by_kind.get(kind)
    if expected_fields is None:
        raise BillingReconciliationConflict("billing cross-index kind is invalid")
    _require_exact_keys(
        payload,
        frozenset(expected_fields),
        "billing cross-index payload",
    )
    _require_bounded_structure(payload, "billing cross-index payload")
    _verify_index_payload(payload)
    expected_record_id: str
    if kind == USAGE_RECEIPT_INDEX_KIND:
        expected_record_id = _receipt_index_id(payload.get("receipt_sha256"))
    elif kind == USAGE_MEASUREMENT_INDEX_KIND:
        expected_record_id = _measurement_index_id(payload)
    elif kind == PAID_INVOICE_INDEX_KIND:
        expected_record_id = _invoice_record_id(payload.get("external_invoice_id"))
        if payload.get("invoice_record_id") != expected_record_id:
            raise BillingReconciliationConflict("invoice index subject is invalid")
    elif kind in {PROVIDER_EVENT_INDEX_KIND, PROVIDER_REQUEST_INDEX_KIND}:
        provider_type = (
            "event" if kind == PROVIDER_EVENT_INDEX_KIND else "request"
        )
        provider_id = _stripe_id(
            payload.get("provider_id"), "provider_id", provider_type
        )
        if payload.get("provider_type") != provider_type:
            raise BillingReconciliationConflict(
                "provider index type contradicts its kind"
            )
        expected_record_id = _provider_index_id(kind, provider_id)
        _safe_code(payload.get("purpose"), "provider_identity_purpose")
        _required_text(payload.get("tenant_id"), "tenant_id")
        _required_text(payload.get("subject_id"), "subject_id")
        if payload.get("evidence_sha256") is not None:
            _sha256(payload.get("evidence_sha256"), "evidence_sha256")
        if payload.get("facts_sha256") is not None:
            _sha256(payload.get("facts_sha256"), "facts_sha256")
    elif kind == METER_EVENT_IDENTIFIER_INDEX_KIND:
        expected_record_id = _meter_identifier_index_id(
            payload.get("meter_event_identifier")
        )
        _sha256(
            payload.get("meter_event_request_sha256"),
            "meter_event_request_sha256",
        )
    elif kind in {SUBSCRIPTION_BINDING_INDEX_KIND, CUSTOMER_BINDING_INDEX_KIND}:
        binding = _subscription_binding_facts(
            tenant_id=payload.get("tenant_id"),
            billing_account_id=payload.get("billing_account_id"),
            customer_id=payload.get("external_customer_id"),
            subscription_id=payload.get("external_subscription_id"),
        )
        if payload.get("binding_sha256") != binding["binding_sha256"]:
            raise BillingReconciliationConflict(
                "subscription binding digest is invalid"
            )
        expected_record_id = (
            _subscription_binding_index_id(payload.get("external_subscription_id"))
            if kind == SUBSCRIPTION_BINDING_INDEX_KIND
            else _customer_binding_index_id(payload.get("external_customer_id"))
        )
    elif kind == USAGE_INVOICE_INDEX_KIND:
        expected_record_id = _required_text(payload.get("usage_id"), "usage_id")
        _required_text(payload.get("invoice_record_id"), "invoice_record_id")
    else:  # pragma: no cover - guarded by expected_fields_by_kind above
        raise BillingReconciliationConflict("billing cross-index kind is invalid")
    if expected_record_id != record_id:
        raise BillingReconciliationConflict(
            "billing cross-index id does not match its stored facts"
        )


def _usage_set_sha256(rows: list[UsageOutboxRecord]) -> str:
    return _canonical_sha256(
        [
            {
                "usage_id": row.usage_id,
                "accelerator_milliseconds": row.accelerator_milliseconds,
                "billing_account_id": row.billing_account_id,
                "external_customer_id": row.external_customer_id,
                "external_subscription_id": row.external_subscription_id,
                "meter_event_name": row.meter_event_name,
                "meter_event_version": row.meter_event_version,
                "meter_event_timestamp": row.meter_event_timestamp,
                "usage_price_id": row.usage_price_id,
                "currency": row.currency,
                "livemode": row.livemode,
                "meter_event_identifier": row.meter_event_identifier,
                "meter_event_request_sha256": row.meter_event_request_sha256,
                "provider_request_id": row.provider_request_id,
                "provider_response_created": row.provider_response_created,
                "provider_response_sha256": row.provider_response_sha256,
                "provider_response_facts_sha256": (
                    row.provider_response_facts_sha256
                ),
                "submitted_at": row.submitted_at,
            }
            for row in sorted(rows, key=lambda item: item.usage_id)
        ]
    )


def _invoice_immutable_from_record(
    invoice: PaidInvoiceReconciliationRecord,
) -> dict[str, object]:
    return {
        "tenant_id": invoice.tenant_id,
        "billing_account_id": invoice.billing_account_id,
        "invoice_created": invoice.invoice_created,
        "invoice_finalized_at": invoice.invoice_finalized_at,
        "external_invoice_id": invoice.external_invoice_id,
        "external_customer_id": invoice.external_customer_id,
        "external_subscription_id": invoice.external_subscription_id,
        "currency": invoice.currency,
        "amount_due_minor": invoice.amount_due_minor,
        "amount_paid_minor": invoice.amount_paid_minor,
        "usage_price_id": invoice.usage_price_id,
        "meter_event_name": invoice.meter_event_name,
        "meter_event_version": invoice.meter_event_version,
        "livemode": invoice.livemode,
        "usage_period_start": invoice.usage_period_start,
        "usage_period_end": invoice.usage_period_end,
        "paid_at": invoice.paid_at,
    }


def _invoice_snapshot_facts_from_record(
    invoice: PaidInvoiceReconciliationRecord,
) -> dict[str, object]:
    return {
        "invoice_created": invoice.invoice_created,
        "invoice_finalized_at": invoice.invoice_finalized_at,
        "external_invoice_id": invoice.external_invoice_id,
        "external_customer_id": invoice.external_customer_id,
        "external_subscription_id": invoice.external_subscription_id,
        "hosted_invoice_url": invoice.hosted_invoice_url,
        "invoice_pdf": invoice.invoice_pdf,
        "invoice_pdf_http_status": invoice.invoice_pdf_http_status,
        "invoice_pdf_content_type": invoice.invoice_pdf_content_type,
        "invoice_pdf_size_bytes": invoice.invoice_pdf_size_bytes,
        "invoice_pdf_sha256": invoice.invoice_pdf_sha256,
        "invoice_pdf_retrieved_at": invoice.invoice_pdf_retrieved_at,
        "currency": invoice.currency,
        "amount_due_minor": invoice.amount_due_minor,
        "amount_paid_minor": invoice.amount_paid_minor,
        "usage_price_id": invoice.usage_price_id,
        "meter_event_name": invoice.meter_event_name,
        "meter_event_version": invoice.meter_event_version,
        "livemode": invoice.livemode,
        "usage_quantity_milliseconds": invoice.provider_quantity_milliseconds,
        "usage_period_start": invoice.usage_period_start,
        "usage_period_end": invoice.usage_period_end,
        "paid_at": invoice.paid_at,
    }


def _invoice_event_facts_from_record(
    invoice: PaidInvoiceReconciliationRecord,
) -> dict[str, object]:
    return {
        "id": invoice.provider_event_id,
        "created": invoice.provider_event_created,
        "type": "invoice.paid",
        "invoice": invoice.external_invoice_id,
        "livemode": invoice.livemode,
    }


def _validated_invoice_snapshot_facts(
    value: object, *, allowed_receipt_hosts: frozenset[str]
) -> dict[str, object]:
    expected = {
        "invoice_created",
        "invoice_finalized_at",
        "external_invoice_id",
        "external_customer_id",
        "external_subscription_id",
        "hosted_invoice_url",
        "invoice_pdf",
        "invoice_pdf_http_status",
        "invoice_pdf_content_type",
        "invoice_pdf_size_bytes",
        "invoice_pdf_sha256",
        "invoice_pdf_retrieved_at",
        "currency",
        "amount_due_minor",
        "amount_paid_minor",
        "usage_price_id",
        "meter_event_name",
        "meter_event_version",
        "livemode",
        "usage_quantity_milliseconds",
        "usage_period_start",
        "usage_period_end",
        "paid_at",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise BillingReconciliationConflict(
            "provider invoice snapshot facts are malformed"
        )
    return {
        "invoice_created": _positive_int(
            value.get("invoice_created"), "invoice_created"
        ),
        "invoice_finalized_at": _positive_int(
            value.get("invoice_finalized_at"), "invoice_finalized_at"
        ),
        "external_invoice_id": _stripe_id(
            value.get("external_invoice_id"), "external_invoice_id", "invoice"
        ),
        "external_customer_id": _stripe_id(
            value.get("external_customer_id"), "external_customer_id", "customer"
        ),
        "external_subscription_id": _stripe_id(
            value.get("external_subscription_id"),
            "external_subscription_id",
            "subscription",
        ),
        "hosted_invoice_url": _canonical_https_url(
            value.get("hosted_invoice_url"), allowed_hosts=allowed_receipt_hosts
        ),
        "invoice_pdf": _canonical_https_url(
            value.get("invoice_pdf"), allowed_hosts=allowed_receipt_hosts
        ),
        "invoice_pdf_http_status": _customer_receipt_status(
            value.get("invoice_pdf_http_status")
        ),
        "invoice_pdf_content_type": _customer_receipt_content_type(
            value.get("invoice_pdf_content_type")
        ),
        "invoice_pdf_size_bytes": _bounded_customer_receipt_size(
            value.get("invoice_pdf_size_bytes")
        ),
        "invoice_pdf_sha256": _sha256(
            value.get("invoice_pdf_sha256"), "invoice_pdf_sha256"
        ),
        "invoice_pdf_retrieved_at": _normalized_time(
            value.get("invoice_pdf_retrieved_at"), "invoice_pdf_retrieved_at"
        ),
        "currency": _currency(value.get("currency")),
        "amount_due_minor": _nonnegative_int(
            value.get("amount_due_minor"), "amount_due_minor"
        ),
        "amount_paid_minor": _nonnegative_int(
            value.get("amount_paid_minor"), "amount_paid_minor"
        ),
        "usage_price_id": _stripe_id(
            value.get("usage_price_id"), "usage_price_id", "price"
        ),
        "meter_event_name": _meter_event_name(
            value.get("meter_event_name"), "meter_event_name"
        ),
        "meter_event_version": _safe_code(
            value.get("meter_event_version"), "meter_event_version"
        ),
        "livemode": _strict_bool(value.get("livemode"), "livemode"),
        "usage_quantity_milliseconds": _nonnegative_int(
            value.get("usage_quantity_milliseconds"),
            "usage_quantity_milliseconds",
        ),
        "usage_period_start": _normalized_whole_second_time(
            value.get("usage_period_start"), "usage_period_start"
        ),
        "usage_period_end": _normalized_whole_second_time(
            value.get("usage_period_end"), "usage_period_end"
        ),
        "paid_at": _normalized_whole_second_time(value.get("paid_at"), "paid_at"),
    }


def _validated_invoice_event_facts(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != {
        "id",
        "created",
        "type",
        "invoice",
        "livemode",
    }:
        raise BillingReconciliationConflict(
            "provider invoice event facts are malformed"
        )
    if value.get("type") != "invoice.paid":
        raise BillingReconciliationConflict(
            "provider invoice event type is invalid"
        )
    return {
        "id": _stripe_id(value.get("id"), "provider_event_id", "event"),
        "created": _positive_int(value.get("created"), "provider_event_created"),
        "type": "invoice.paid",
        "invoice": _stripe_id(
            value.get("invoice"), "external_invoice_id", "invoice"
        ),
        "livemode": _strict_bool(value.get("livemode"), "livemode"),
    }


_INVOICE_OBSERVATION_FIELDS = (
    "provider_event_id",
    "provider_event_created",
    "provider_request_id",
    "provider_snapshot_sha256",
    "provider_snapshot_facts_sha256",
    "provider_snapshot_facts",
    "provider_snapshot_retrieved_at",
    "raw_event_sha256",
    "provider_event_facts_sha256",
    "provider_event_facts",
    "usage_quantity_milliseconds",
    "hosted_invoice_url",
    "invoice_pdf",
    "invoice_pdf_http_status",
    "invoice_pdf_content_type",
    "invoice_pdf_size_bytes",
    "invoice_pdf_sha256",
    "invoice_pdf_retrieved_at",
)


def _invoice_observation_from_facts(
    facts: Mapping[str, object]
) -> dict[str, object]:
    return {field: facts[field] for field in _INVOICE_OBSERVATION_FIELDS}


def _invoice_observation_from_payload(
    payload: Mapping[str, object]
) -> dict[str, object]:
    result = {field: payload.get(field) for field in _INVOICE_OBSERVATION_FIELDS}
    result["usage_quantity_milliseconds"] = payload.get(
        "provider_quantity_milliseconds"
    )
    return result


def _validated_invoice_observations(
    value: object,
    *,
    allowed_receipt_hosts: frozenset[str],
    require_provider_request_id: bool,
) -> tuple[dict[str, object], ...]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > MAX_PROVIDER_INVOICE_OBSERVATIONS
    ):
        raise BillingReconciliationConflict(
            "provider invoice observation history is invalid"
        )
    result: list[dict[str, object]] = []
    for raw in value:
        if (
            not isinstance(raw, Mapping)
            or len(raw) != len(_INVOICE_OBSERVATION_FIELDS)
            or set(raw) != set(_INVOICE_OBSERVATION_FIELDS)
        ):
            raise BillingReconciliationConflict(
                "provider invoice observation is malformed"
            )
        snapshot_facts = _validated_invoice_snapshot_facts(
            raw.get("provider_snapshot_facts"),
            allowed_receipt_hosts=allowed_receipt_hosts,
        )
        event_facts = _validated_invoice_event_facts(
            raw.get("provider_event_facts")
        )
        observation = {
            "provider_event_id": _stripe_id(
                raw.get("provider_event_id"), "provider_event_id", "event"
            ),
            "provider_event_created": _positive_int(
                raw.get("provider_event_created"), "provider_event_created"
            ),
            "provider_request_id": _optional_stripe_id(
                raw.get("provider_request_id"), "provider_request_id", "request"
            ),
            "provider_snapshot_sha256": _sha256(
                raw.get("provider_snapshot_sha256"),
                "provider_snapshot_sha256",
            ),
            "provider_snapshot_facts_sha256": _sha256(
                raw.get("provider_snapshot_facts_sha256"),
                "provider_snapshot_facts_sha256",
            ),
            "provider_snapshot_facts": snapshot_facts,
            "provider_snapshot_retrieved_at": _normalized_time(
                raw.get("provider_snapshot_retrieved_at"),
                "provider_snapshot_retrieved_at",
            ),
            "raw_event_sha256": _sha256(
                raw.get("raw_event_sha256"), "raw_event_sha256"
            ),
            "provider_event_facts_sha256": _sha256(
                raw.get("provider_event_facts_sha256"),
                "provider_event_facts_sha256",
            ),
            "provider_event_facts": event_facts,
            "usage_quantity_milliseconds": _nonnegative_int(
                raw.get("usage_quantity_milliseconds"),
                "usage_quantity_milliseconds",
            ),
            "hosted_invoice_url": _canonical_https_url(
                raw.get("hosted_invoice_url"),
                allowed_hosts=allowed_receipt_hosts,
            ),
            "invoice_pdf": _canonical_https_url(
                raw.get("invoice_pdf"),
                allowed_hosts=allowed_receipt_hosts,
            ),
            "invoice_pdf_http_status": _customer_receipt_status(
                raw.get("invoice_pdf_http_status")
            ),
            "invoice_pdf_content_type": _customer_receipt_content_type(
                raw.get("invoice_pdf_content_type")
            ),
            "invoice_pdf_size_bytes": _bounded_customer_receipt_size(
                raw.get("invoice_pdf_size_bytes")
            ),
            "invoice_pdf_sha256": _sha256(
                raw.get("invoice_pdf_sha256"),
                "invoice_pdf_sha256",
            ),
            "invoice_pdf_retrieved_at": _normalized_time(
                raw.get("invoice_pdf_retrieved_at"),
                "invoice_pdf_retrieved_at",
            ),
        }
        if (
            _canonical_sha256(snapshot_facts)
            != observation["provider_snapshot_facts_sha256"]
            or _canonical_sha256(event_facts)
            != observation["provider_event_facts_sha256"]
        ):
            raise BillingReconciliationConflict(
                "provider invoice parsed-facts digest is invalid"
            )
        if (
            event_facts["id"] != observation["provider_event_id"]
            or event_facts["created"] != observation["provider_event_created"]
            or snapshot_facts["usage_quantity_milliseconds"]
            != observation["usage_quantity_milliseconds"]
            or snapshot_facts["hosted_invoice_url"]
            != observation["hosted_invoice_url"]
            or snapshot_facts["invoice_pdf"] != observation["invoice_pdf"]
        ):
            raise BillingReconciliationConflict(
                "provider invoice parsed facts contradict the observation"
            )
        if (
            require_provider_request_id
            and observation["provider_request_id"] is None
        ):
            raise BillingReconciliationConflict(
                "live invoice observation is missing a provider request receipt"
            )
        try:
            event_clock = datetime.fromtimestamp(
                observation["provider_event_created"], tz=UTC
            )
        except (OverflowError, OSError, ValueError) as exc:
            raise BillingReconciliationConflict(
                "provider invoice observation timestamp is invalid"
            ) from exc
        if _parse_time(observation["provider_snapshot_retrieved_at"]) < event_clock:
            raise BillingReconciliationConflict(
                "provider invoice observation predates its event"
            )
        if result:
            _require_newer_invoice_observation(result[-1], observation)
        result.append(observation)
    return tuple(result)


def _require_newer_invoice_observation(
    previous: Mapping[str, object], incoming: Mapping[str, object]
) -> None:
    previous_event_id = str(previous["provider_event_id"])
    incoming_event_id = str(incoming["provider_event_id"])
    previous_created = int(previous["provider_event_created"])
    incoming_created = int(incoming["provider_event_created"])
    previous_retrieved = _parse_time(previous["provider_snapshot_retrieved_at"])
    incoming_retrieved = _parse_time(incoming["provider_snapshot_retrieved_at"])
    if incoming_event_id == previous_event_id:
        if (
            incoming_created != previous_created
            or incoming.get("raw_event_sha256") != previous.get("raw_event_sha256")
        ):
            raise BillingReconciliationConflict(
                "provider event id was replayed with contradictory event facts"
            )
        if incoming_retrieved <= previous_retrieved:
            raise BillingReconciliationConflict(
                "refreshed provider invoice observation is not newer"
            )
        return
    if incoming_created <= previous_created:
        raise BillingReconciliationConflict(
            "stale provider event cannot replace newer invoice evidence"
        )
    if incoming_retrieved <= previous_retrieved:
        raise BillingReconciliationConflict(
            "new provider event has a stale invoice retrieval timestamp"
        )


def _is_fresh_replay_of_matched_observation(
    previous: Mapping[str, object], incoming: Mapping[str, object]
) -> bool:
    """Allow a fresh GET receipt for the exact already-matched Stripe event.

    The terminal financial aggregate is not rewritten. Only retrieval-specific
    evidence (request id, raw snapshot digest, and retrieval clock) may differ;
    the original event bytes and every parsed invoice/receipt fact must remain
    identical.
    """

    previous_snapshot = dict(previous.get("provider_snapshot_facts") or {})
    incoming_snapshot = dict(incoming.get("provider_snapshot_facts") or {})
    previous_pdf_retrieved_at = previous_snapshot.pop(
        "invoice_pdf_retrieved_at", None
    )
    incoming_pdf_retrieved_at = incoming_snapshot.pop(
        "invoice_pdf_retrieved_at", None
    )
    if not (
        incoming.get("provider_event_id") == previous.get("provider_event_id")
        and incoming.get("provider_event_created")
        == previous.get("provider_event_created")
        and incoming.get("raw_event_sha256") == previous.get("raw_event_sha256")
        and incoming.get("provider_event_facts_sha256")
        == previous.get("provider_event_facts_sha256")
        and incoming.get("provider_event_facts")
        == previous.get("provider_event_facts")
        and incoming_snapshot == previous_snapshot
        and incoming.get("usage_quantity_milliseconds")
        == previous.get("usage_quantity_milliseconds")
    ):
        return False
    return (
        _parse_time(incoming.get("provider_snapshot_retrieved_at"))
        > _parse_time(previous.get("provider_snapshot_retrieved_at"))
        and _parse_time(incoming_pdf_retrieved_at)
        >= _parse_time(previous_pdf_retrieved_at)
    )


def _normalize_receipt_hosts(values: tuple[str, ...]) -> frozenset[str]:
    if isinstance(values, str) or not values:
        raise BillingReconciliationError(
            "at least one exact customer receipt host is required"
        )
    hosts = frozenset(_receipt_host(value) for value in values)
    if not hosts:
        raise BillingReconciliationError(
            "at least one exact customer receipt host is required"
        )
    return hosts


def _receipt_host(value: object) -> str:
    if not isinstance(value, str):
        raise BillingReconciliationError(
            "invoice URL allowlist contains a non-canonical A-label host"
        )
    raw = value
    host = raw.strip()
    if (
        not host
        or raw != host
        or host != host.lower()
        or host.endswith(".")
        or host == "localhost"
        or "." not in host
        or "*" in host
        or len(host) > 253
        or any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or not re.fullmatch(r"[a-z0-9-]+", label)
            for label in host.split(".")
        )
    ):
        raise BillingReconciliationError(
            "invoice URL allowlist contains a non-canonical A-label host"
        )
    try:
        host.encode("ascii")
    except UnicodeEncodeError as exc:
        raise BillingReconciliationError(
            "invoice URL allowlist requires an ASCII A-label host"
        ) from exc
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return host
    raise BillingReconciliationError(
        "customer receipt allowlist may not contain an IP address"
    )


def _canonical_https_url(
    value: object, *, allowed_hosts: frozenset[str]
) -> str:
    if not isinstance(value, str):
        raise BillingReconciliationError("invoice URL is not canonical HTTPS")
    raw = value
    url = raw.strip()
    if (
        not url
        or raw != url
        or len(url) > 2048
        or any(ord(character) < 0x20 or ord(character) > 0x7E for character in url)
    ):
        raise BillingReconciliationError("invoice URL is not canonical HTTPS")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
    except ValueError as exc:
        raise BillingReconciliationError("invoice URL is not canonical HTTPS") from exc
    safe_path = re.fullmatch(r"/[A-Za-z0-9._~!$&'()*+,;=:@/-]*", parsed.path)
    safe_query = re.fullmatch(r"[A-Za-z0-9._~!$&'()*+,;=:@/?-]*", parsed.query)
    path_segments = parsed.path.split("/")
    if (
        parsed.scheme != "https"
        or not host
        or host != host.lower()
        or parsed.netloc != host
        or host not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
        or safe_path is None
        or safe_query is None
        or "//" in parsed.path
        or any(segment in {".", ".."} for segment in path_segments)
    ):
        raise BillingReconciliationError(
            "invoice URL is outside the canonical exact HTTPS host allowlist"
        )
    return url


def _customer_receipt_status(value: object) -> int:
    status = _nonnegative_int(value, "customer_receipt_http_status")
    if status != 200:
        raise BillingReconciliationError(
            "customer receipt fetch must return HTTP 200"
        )
    return status


def _customer_receipt_content_type(value: object) -> str:
    if not isinstance(value, str):
        raise BillingReconciliationError(
            "customer receipt must be a fetched application/pdf"
        )
    content_type = value
    if content_type != "application/pdf":
        raise BillingReconciliationError(
            "customer receipt must be a fetched application/pdf"
        )
    return content_type


def _bounded_customer_receipt_size(value: object) -> int:
    size = _positive_int(value, "customer_receipt_size_bytes")
    if size > MAX_CUSTOMER_RECEIPT_BYTES:
        raise BillingReconciliationError(
            f"customer_receipt_size_bytes exceeds {MAX_CUSTOMER_RECEIPT_BYTES}"
        )
    return size


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_exact_keys(
    value: Mapping[str, object], expected: frozenset[str], label: str
) -> None:
    if len(value) != len(expected) or set(value) != expected:
        raise BillingReconciliationConflict(f"{label} schema is invalid")


def _require_bounded_structure(value: object, label: str) -> None:
    stack: list[tuple[object, int]] = [(value, 0)]
    node_count = 0
    string_characters = 0
    while stack:
        current, depth = stack.pop()
        node_count += 1
        if node_count > MAX_DURABLE_BILLING_NODES or depth > 8:
            raise BillingReconciliationConflict(f"{label} exceeds safe bounds")
        if isinstance(current, str):
            string_characters += len(current)
            if string_characters > MAX_DURABLE_BILLING_STRING_CHARACTERS:
                raise BillingReconciliationConflict(f"{label} exceeds safe bounds")
        elif isinstance(current, Mapping):
            if len(current) > 256:
                raise BillingReconciliationConflict(f"{label} exceeds safe bounds")
            for key, item in current.items():
                if not isinstance(key, str):
                    raise BillingReconciliationConflict(
                        f"{label} contains a non-string key"
                    )
                stack.append((key, depth + 1))
                stack.append((item, depth + 1))
        elif isinstance(current, (list, tuple)):
            if len(current) > MAX_DURABLE_BILLING_LIST_ITEMS:
                raise BillingReconciliationConflict(f"{label} exceeds safe bounds")
            stack.extend((item, depth + 1) for item in current)
        elif current is not None and not isinstance(current, (bool, int)):
            raise BillingReconciliationConflict(
                f"{label} contains an unsupported value type"
            )


def _seal_payload(payload: Mapping[str, object]) -> dict[str, object]:
    sealed = dict(payload)
    sealed.pop("payload_sha256", None)
    sealed["payload_sha256"] = _canonical_sha256(sealed)
    return sealed


def _verify_sealed_payload(payload: Mapping[str, object]) -> None:
    expected = _sha256(payload.get("payload_sha256"), "payload_sha256")
    facts = dict(payload)
    facts.pop("payload_sha256", None)
    if not hmac.compare_digest(expected, _canonical_sha256(facts)):
        raise BillingReconciliationConflict(
            "durable billing payload digest is invalid"
        )


def _seal_index_payload(payload: Mapping[str, object]) -> dict[str, object]:
    sealed = dict(payload)
    sealed.pop("index_sha256", None)
    sealed["index_sha256"] = _canonical_sha256(sealed)
    return sealed


def _verify_index_payload(payload: Mapping[str, object]) -> None:
    expected = _sha256(payload.get("index_sha256"), "index_sha256")
    facts = dict(payload)
    facts.pop("index_sha256", None)
    if not hmac.compare_digest(expected, _canonical_sha256(facts)):
        raise BillingReconciliationConflict(
            "billing cross-index digest is invalid"
        )


def _meter_event_name(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise BillingReconciliationError(f"{field} is invalid")
    text = value
    if len(text) > 100 or not _METER_EVENT_NAME_RE.fullmatch(text):
        raise BillingReconciliationError(f"{field} is invalid")
    return text


def _meter_identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise BillingReconciliationError(f"{field} is invalid")
    text = value
    if len(text) > 100 or not _METER_IDENTIFIER_RE.fullmatch(text):
        raise BillingReconciliationError(f"{field} is invalid")
    return text


def _stripe_id(value: object, field: str, kind: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise BillingReconciliationError(
            f"{field} is not a canonical Stripe {kind} id"
        )
    text = value
    pattern = _STRIPE_ID_PATTERNS.get(kind)
    if len(text) > 255 or pattern is None or not pattern.fullmatch(text):
        raise BillingReconciliationError(
            f"{field} is not a canonical Stripe {kind} id"
        )
    return text


def _optional_stripe_id(
    value: object, field: str, kind: str
) -> str | None:
    if value is None:
        return None
    return _stripe_id(value, field, kind)


def _optional_positive_int(value: object, field: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, field)


def _require_schema(payload: Mapping[str, object]) -> None:
    if payload.get("schema_version") != BILLING_RECONCILIATION_SCHEMA_VERSION:
        raise BillingReconciliationConflict(
            "billing reconciliation schema version is invalid"
        )


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise BillingReconciliationError(f"{field} is invalid")
    text = value
    if not text or len(text) > 255 or any(character in text for character in "\r\n\0"):
        raise BillingReconciliationError(f"{field} is invalid")
    return text


def _safe_code(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise BillingReconciliationError(f"{field} is invalid")
    text = value
    if len(text) > 128 or not _SAFE_CODE_RE.fullmatch(text):
        raise BillingReconciliationError(f"{field} is invalid")
    return text


def _optional_safe_code(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _safe_code(value, field)


def _delivery_failure_code(value: object) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise BillingReconciliationError(
            "failure_code is not an allowlisted internal category"
        )
    text = value
    if len(text) > 64 or text not in DELIVERY_FAILURE_CODES:
        raise BillingReconciliationError(
            "failure_code is not an allowlisted internal category"
        )
    return text


def _optional_delivery_failure_code(value: object) -> str | None:
    if value is None:
        return None
    return _delivery_failure_code(value)


def validate_provider_reference_hash_key(value: object) -> bytes:
    """Return a strong deployment key or fail without echoing its value.

    Length alone is not a useful secret-strength check: whitespace, repeated
    characters, common placeholders, and short repeated patterns can all meet a
    byte floor while remaining predictable.  The deployment should still use a
    cryptographically generated secret; these checks fail closed on the common
    configuration mistakes that can be identified locally.
    """

    if not isinstance(value, str):
        raise BillingReconciliationError(
            "provider reference hash key must be a string"
        )
    if len(value) > 4096:
        raise BillingReconciliationError(
            "provider reference hash key exceeds the safe configuration bound"
        )
    key = value.encode("utf-8")
    if len(key) < 32:
        raise BillingReconciliationError(
            "provider reference hash key must contain at least 32 bytes"
        )
    if any(
        character.isspace()
        or unicodedata.category(character).startswith("C")
        for character in value
    ):
        raise BillingReconciliationError(
            "provider reference hash key must not contain whitespace or control characters"
        )
    lowered = value.casefold()
    if (
        len(set(value)) < 12
        or any(marker in lowered for marker in _PREDICTABLE_KEY_MARKERS)
        or _is_repeated_key_pattern(value)
    ):
        raise BillingReconciliationError(
            "provider reference hash key must be an unpredictable dedicated secret"
        )
    return key


def validate_stripe_usage_price_id(value: object) -> str:
    """Validate the configured metered Price identity without provider I/O."""

    return _stripe_id(value, "stripe_usage_price_id", "price")


def validate_billing_meter_event_name(value: object) -> str:
    """Validate Stripe's 100-character Meter Event name contract."""

    return _meter_event_name(value, "billing_usage_meter_event_name")


def validate_customer_receipt_allowed_hosts(
    values: tuple[str, ...],
) -> tuple[str, ...]:
    """Validate exact canonical HTTPS receipt hosts without provider I/O."""

    normalized = _normalize_receipt_hosts(values)
    return tuple(sorted(normalized))


def _is_repeated_key_pattern(value: str) -> bool:
    for width in range(1, min(16, len(value) // 2) + 1):
        if len(value) % width == 0 and value == value[:width] * (
            len(value) // width
        ):
            return True
    return False


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip() or value != value.lower():
        raise BillingReconciliationError(f"{field} must be a SHA-256 hex digest")
    text = value
    if len(text) != 64 or not _SHA256_RE.fullmatch(text):
        raise BillingReconciliationError(f"{field} must be a SHA-256 hex digest")
    return text


def _optional_sha256(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _sha256(value, field)


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BillingReconciliationError(f"{field} must be an integer")
    number = value
    if number < 0:
        raise BillingReconciliationError(
            f"{field} must be a canonical non-negative integer"
        )
    return number


def _positive_decimal_string_int(value: object, field: str) -> int:
    if (
        not isinstance(value, str)
        or len(value) > 20
        or not re.fullmatch(r"[1-9][0-9]*", value)
    ):
        raise BillingReconciliationError(
            f"{field} must be a canonical positive decimal string"
        )
    return int(value)


def _positive_int(value: object, field: str) -> int:
    number = _nonnegative_int(value, field)
    if number <= 0:
        raise BillingReconciliationError(f"{field} must be positive")
    return number


def _bounded_receipt_size(value: object) -> int:
    size = _positive_int(value, "receipt_size_bytes")
    if size > MAX_FLEET_RECEIPT_BYTES:
        raise BillingReconciliationError(
            f"receipt_size_bytes exceeds {MAX_FLEET_RECEIPT_BYTES}"
        )
    return size


def _strict_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise BillingReconciliationError(f"{field} must be a boolean")
    return value


def _currency(value: object) -> str:
    if not isinstance(value, str) or value != value.strip() or value != value.lower():
        raise BillingReconciliationError("currency must be a three-letter code")
    text = value
    if not re.fullmatch(r"[a-z]{3}", text):
        raise BillingReconciliationError("currency must be a three-letter code")
    return text


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str) or value != value.strip():
        raise BillingReconciliationError("timestamp is not valid ISO-8601")
    text = value
    if len(text) > 64:
        raise BillingReconciliationError("timestamp is not valid ISO-8601")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise BillingReconciliationError("timestamp is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise BillingReconciliationError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def _normalized_time(value: object, field: str) -> str:
    try:
        return _parse_time(value).isoformat()
    except BillingReconciliationError as exc:
        raise BillingReconciliationError(f"{field} is invalid: {exc}") from exc


def _normalized_whole_second_time(value: object, field: str) -> str:
    try:
        parsed = _parse_time(value)
    except BillingReconciliationError as exc:
        raise BillingReconciliationError(f"{field} is invalid: {exc}") from exc
    if parsed.microsecond != 0:
        raise BillingReconciliationError(
            f"{field} must be a canonical whole-second timestamp"
        )
    return parsed.isoformat()


def _optional_time(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _normalized_time(value, field)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
