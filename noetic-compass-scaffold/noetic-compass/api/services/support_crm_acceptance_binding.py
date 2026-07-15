"""Private authoritative source binding for support/CRM gate evidence.

Support tickets and CRM leads live in the existing global customer-operations
partition, :data:`CONTACT_STATE_TENANT`.  That value is an authority/storage
scope for these two operational domains; it is deliberately **not** evidence of
customer tenant ownership.  Public artifacts therefore expose only keyed
subjects derived under that exact scope.  Raw ticket, lead, Airtable, and trace
identifiers remain in the private selector and binding row.

The public verifier can validate keyed-subject shape only.  Before publication
and again while an active artifact is served, this store reopens the shared
StateStore, validates both JSONL cutover markers, reloads exact immutable domain
revisions plus their heads, recomputes every subject, and verifies the resolved
support lifecycle, SLA, Airtable readback receipt, and consent facts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import json
import math
import re
from typing import Any

from api.services.crm.models import (
    CRM_CONSENT_SCHEMA_VERSION,
    CRM_SCHEMA_VERSION,
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
    SUPPORT_CRM_CONTENT_BINDING_DOMAIN,
    SUPPORT_TICKET_DOMAIN,
    CustomerProductionPseudonymizer,
    SUBJECT_PATTERN,
    validate_public_pseudonym_metadata,
    SUPPORT_CRM_REQUEST_TRACE_DOMAIN,
)
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)
from api.services.revisioned_contact_store import (
    CONTACT_MIGRATION_KIND,
    CONTACT_MIGRATION_SCHEMA_VERSION,
    CONTACT_STATE_TENANT,
    canonical_json,
    content_sha256,
)
from api.services.support_ticket_state_store import (
    SUPPORT_TICKET_JSONL_MIGRATION_ID,
    StateStoreSupportTicketStore,
)
from api.services.support_public_intake_receipts import (
    SupportPublicIntakeReceiptInvalid,
    SupportPublicIntakeReceiptStore,
    SupportPublicIntakeReceiptUnavailable,
)
from api.services.support_tickets import (
    SUPPORT_TICKET_SCHEMA_VERSION,
    SupportTicket,
)


SCHEMA_VERSION = "cas_harness_support_crm_source_binding.v1"
PRIVATE_SELECTOR_SCHEMA_VERSION = (
    "cas_harness_support_crm_acceptance_selector.v1"
)
# The private binding is another customer-operations authority record, not a
# customer-owned tenant record.  A distinct kind isolates it within the one
# already-established global contact partition.
BINDING_TENANT_ID = CONTACT_STATE_TENANT
BINDING_KIND = "customer_production_support_crm_source_binding"
_EVIDENCE_SCHEMA = "cas_harness_customer_production_gate_evidence.v3"
_CRM_SOURCE_SCHEMA = "cas_harness_airtable_crm_acceptance_source.v3"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MIGRATION_FIELDS = frozenset(
    {
        "schema_version",
        "domain",
        "source_present",
        "source_sha256",
        "line_count",
        "revision_count",
        "head_count",
        "records_sha256",
    }
)
_CONTACT_ENVELOPE_FIELDS = frozenset(
    {
        "schema_version",
        "item_id",
        "domain_version",
        "revision_record_id",
        "content_sha256",
        "item",
    }
)
_SELECTOR_KEYS = frozenset(
    {"schema_version", "gate", "support_ticket_id", "crm_lead_id"}
)
_RECORD_KEYS = frozenset(
    {
        "schema_version",
        "evidence_sha256",
        "contact_authority_scope",
        "support_ticket_id",
        "crm_lead_id",
        "airtable_record_id",
        "pseudonym_key_id",
        "support_ticket_version",
        "crm_lead_version",
        "support_ticket_revision_sha256",
        "crm_lead_revision_sha256",
        "support_ticket_head_envelope_sha256",
        "support_ticket_revision_envelope_sha256",
        "support_public_intake_receipt_version",
        "support_public_intake_receipt_envelope_sha256",
        "support_public_intake_content_binding_hmac",
        "crm_lead_revision_envelope_sha256",
        "support_migration_marker_sha256",
        "crm_migration_marker_sha256",
        "support_ack_sla_seconds",
        "content_binding_hmac",
        "bound_at_utc",
    }
)


class SupportCRMSourceBindingError(RuntimeError):
    """Base support/CRM source-binding error."""


class SupportCRMSourceBindingInvalid(SupportCRMSourceBindingError):
    """Public evidence does not match one authoritative support/CRM source."""


class SupportCRMSourceBindingUnavailable(SupportCRMSourceBindingError):
    """Durable source state or a historical pseudonym key is unavailable."""


@dataclass(frozen=True)
class _SourceFacts:
    ticket: SupportTicket
    lead: Lead
    key_id: str
    ticket_revision_sha256: str
    lead_revision_sha256: str
    support_marker_sha256: str
    crm_marker_sha256: str
    ticket_head_envelope_sha256: str
    ticket_revision_envelope_sha256: str
    public_intake_receipt_version: int
    public_intake_receipt_envelope_sha256: str
    public_intake_content_binding_hmac: str
    public_intake_http_status: int
    lead_revision_envelope_sha256: str


def validate_support_crm_private_selector(
    selector: Mapping[str, Any],
) -> tuple[str, str]:
    """Return raw IDs from one exact private selector-v1 object.

    Callers must keep this mapping out of public artifacts, logs, and command
    output.  The strict shape prevents a loosely parsed public fragment from
    silently becoming publication authority.
    """

    if (
        not isinstance(selector, Mapping)
        or set(selector) != _SELECTOR_KEYS
        or selector.get("schema_version") != PRIVATE_SELECTOR_SCHEMA_VERSION
        or selector.get("gate") != "support_crm"
    ):
        raise SupportCRMSourceBindingInvalid(
            "support/CRM private selector schema is invalid"
        )
    ticket_id = selector.get("support_ticket_id")
    lead_id = selector.get("crm_lead_id")
    if (
        not isinstance(ticket_id, str)
        or not ticket_id
        or "\x00" in ticket_id
        or not isinstance(lead_id, str)
        or not lead_id
        or "\x00" in lead_id
    ):
        raise SupportCRMSourceBindingInvalid(
            "support/CRM private selector identifiers are invalid"
        )
    return ticket_id, lead_id


class SupportCRMAcceptanceSourceBindingStore:
    """Create and revalidate private support/CRM evidence bindings."""

    def __init__(
        self,
        store: StateStore,
        *,
        leads: StateStoreLeadStore,
        support_tickets: StateStoreSupportTicketStore,
        public_intake_receipts: SupportPublicIntakeReceiptStore,
        pseudonymizer: CustomerProductionPseudonymizer,
        support_ack_sla_seconds: int,
    ) -> None:
        if not isinstance(leads, StateStoreLeadStore):
            raise ValueError("StateStore CRM lead store is required")
        if not isinstance(support_tickets, StateStoreSupportTicketStore):
            raise ValueError("StateStore support ticket store is required")
        if leads.state_store is not store or support_tickets.state_store is not store:
            raise ValueError(
                "support/CRM binding requires one shared contact StateStore"
            )
        if not isinstance(
            public_intake_receipts, SupportPublicIntakeReceiptStore
        ):
            raise ValueError("support public-intake receipt store is required")
        if public_intake_receipts.state_store is not store:
            raise ValueError(
                "support/CRM binding requires one shared contact StateStore"
            )
        if not isinstance(pseudonymizer, CustomerProductionPseudonymizer):
            raise ValueError("customer-production pseudonymizer is required")
        if public_intake_receipts.pseudonymizer is not pseudonymizer:
            raise ValueError(
                "support/CRM binding requires one shared pseudonym keyring"
            )
        if (
            type(support_ack_sla_seconds) is not int
            or support_ack_sla_seconds < 60
        ):
            raise ValueError("support acknowledgement SLA must be at least 60 seconds")
        self._store = store
        self._leads = leads
        self._support_tickets = support_tickets
        self._public_intake_receipts = public_intake_receipts
        self._pseudonymizer = pseudonymizer
        self._support_ack_sla_seconds = support_ack_sla_seconds

    def create(
        self,
        evidence: Mapping[str, Any],
        *,
        selector: Mapping[str, Any],
        now: datetime | None = None,
    ) -> str:
        """Bind canonical public bytes to exact private support/CRM revisions."""

        ticket_id, lead_id = validate_support_crm_private_selector(selector)
        canonical = _canonical_json_bytes(evidence)
        evidence_sha256 = hashlib.sha256(canonical).hexdigest()
        facts = self._assert_authoritative_source(
            evidence, support_ticket_id=ticket_id, crm_lead_id=lead_id
        )
        stamp = _utc_now(now)
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "evidence_sha256": evidence_sha256,
            "contact_authority_scope": CONTACT_STATE_TENANT,
            "support_ticket_id": facts.ticket.ticket_id,
            "crm_lead_id": facts.lead.lead_id,
            "airtable_record_id": str(facts.lead.external_id),
            "pseudonym_key_id": facts.key_id,
            "support_ticket_version": facts.ticket.version,
            "crm_lead_version": facts.lead.version,
            "support_ticket_revision_sha256": facts.ticket_revision_sha256,
            "crm_lead_revision_sha256": facts.lead_revision_sha256,
            "support_ticket_head_envelope_sha256": (
                facts.ticket_head_envelope_sha256
            ),
            "support_ticket_revision_envelope_sha256": (
                facts.ticket_revision_envelope_sha256
            ),
            "support_public_intake_receipt_version": (
                facts.public_intake_receipt_version
            ),
            "support_public_intake_receipt_envelope_sha256": (
                facts.public_intake_receipt_envelope_sha256
            ),
            "support_public_intake_content_binding_hmac": (
                facts.public_intake_content_binding_hmac
            ),
            "crm_lead_revision_envelope_sha256": (
                facts.lead_revision_envelope_sha256
            ),
            "support_migration_marker_sha256": facts.support_marker_sha256,
            "crm_migration_marker_sha256": facts.crm_marker_sha256,
            "support_ack_sla_seconds": self._support_ack_sla_seconds,
            "content_binding_hmac": self._content_binding_hmac(
                evidence_sha256=evidence_sha256, facts=facts
            ),
            "bound_at_utc": _format_utc(stamp),
        }
        record = LedgerRecord.new(
            tenant_id=BINDING_TENANT_ID,
            kind=BINDING_KIND,
            record_id=_record_id(evidence_sha256),
            payload=payload,
            source="support_crm_acceptance_source_binding",
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
                raise SupportCRMSourceBindingUnavailable(
                    "support/CRM source binding store is unavailable"
                ) from exc
            existing_payload = _validate_binding_record(existing, evidence_sha256)
            if any(
                existing_payload.get(key) != value
                for key, value in payload.items()
                if key != "bound_at_utc"
            ):
                raise SupportCRMSourceBindingUnavailable(
                    "support/CRM source binding conflicted"
                )
            stored = existing
        except Exception as exc:
            raise SupportCRMSourceBindingUnavailable(
                "support/CRM source binding persistence failed"
            ) from exc
        if stored is None or stored.version != 1:
            raise SupportCRMSourceBindingUnavailable(
                "support/CRM source binding version is invalid"
            )
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
            raise SupportCRMSourceBindingInvalid(
                "support/CRM evidence digest is invalid"
            )
        try:
            record = self._store.get(
                BINDING_TENANT_ID, BINDING_KIND, _record_id(evidence_sha256)
            )
        except Exception as exc:
            raise SupportCRMSourceBindingUnavailable(
                "support/CRM source binding store is unavailable"
            ) from exc
        if record is None:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM authoritative source binding is absent"
            )
        payload = _validate_binding_record(record, evidence_sha256)
        facts = self._assert_authoritative_source(
            evidence,
            support_ticket_id=str(payload["support_ticket_id"]),
            crm_lead_id=str(payload["crm_lead_id"]),
        )
        if (
            payload["contact_authority_scope"] != CONTACT_STATE_TENANT
            or payload["airtable_record_id"] != facts.lead.external_id
            or payload["pseudonym_key_id"] != facts.key_id
            or payload["support_ticket_version"] != facts.ticket.version
            or payload["crm_lead_version"] != facts.lead.version
            or payload["support_ticket_revision_sha256"]
            != facts.ticket_revision_sha256
            or payload["crm_lead_revision_sha256"] != facts.lead_revision_sha256
            or payload["support_ticket_head_envelope_sha256"]
            != facts.ticket_head_envelope_sha256
            or payload["support_ticket_revision_envelope_sha256"]
            != facts.ticket_revision_envelope_sha256
            or payload["support_public_intake_receipt_version"]
            != facts.public_intake_receipt_version
            or payload["support_public_intake_receipt_envelope_sha256"]
            != facts.public_intake_receipt_envelope_sha256
            or payload["support_public_intake_content_binding_hmac"]
            != facts.public_intake_content_binding_hmac
            or payload["crm_lead_revision_envelope_sha256"]
            != facts.lead_revision_envelope_sha256
            or payload["support_migration_marker_sha256"]
            != facts.support_marker_sha256
            or payload["crm_migration_marker_sha256"] != facts.crm_marker_sha256
            or payload["support_ack_sla_seconds"]
            != self._support_ack_sla_seconds
        ):
            raise SupportCRMSourceBindingInvalid(
                "support/CRM source binding is stale or cross-wired"
            )
        expected_hmac = self._content_binding_hmac(
            evidence_sha256=evidence_sha256, facts=facts
        )
        if not hmac.compare_digest(
            str(payload["content_binding_hmac"]), expected_hmac
        ):
            raise SupportCRMSourceBindingUnavailable(
                "support/CRM source binding integrity is invalid"
            )

    def _assert_authoritative_source(
        self,
        evidence: Mapping[str, Any],
        *,
        support_ticket_id: str,
        crm_lead_id: str,
    ) -> _SourceFacts:
        if (
            evidence.get("schema_version") != _EVIDENCE_SCHEMA
            or evidence.get("gate") != "support_crm"
        ):
            raise SupportCRMSourceBindingInvalid(
                "support/CRM evidence schema is invalid"
            )
        key_id = self._public_key_id(evidence, context="support/CRM evidence")
        ticket_public = _public_object(evidence, "support_ticket")
        lead_public = _public_object(evidence, "crm_lead")
        consent_public = _public_object(evidence, "consent")
        source_public = _public_object(evidence, "crm_source_receipt")
        source_key_id = self._public_key_id(
            source_public, context="support/CRM source receipt"
        )
        if source_key_id != key_id:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM source receipt pseudonym key is cross-wired"
            )
        if source_public.get("schema_version") != _CRM_SOURCE_SCHEMA:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM source receipt schema is invalid"
            )
        for legacy_field, container in (
            ("ticket_id_sha256", ticket_public),
            ("lead_id_sha256", lead_public),
            ("airtable_record_id_sha256", lead_public),
            ("lead_id_sha256", source_public),
            ("airtable_record_id_sha256", source_public),
            ("trace_id_sha256", source_public),
        ):
            if legacy_field in container:
                raise SupportCRMSourceBindingInvalid(
                    "support/CRM legacy unkeyed identifier digest is forbidden"
                )

        try:
            public_intake_receipt = self._public_intake_receipts.revalidate(
                support_ticket_id
            )
        except SupportPublicIntakeReceiptInvalid as exc:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM public-intake receipt is absent or invalid"
            ) from exc
        except SupportPublicIntakeReceiptUnavailable as exc:
            raise SupportCRMSourceBindingUnavailable(
                "support/CRM public-intake receipt is unavailable"
            ) from exc
        public_intake_payload = public_intake_receipt.payload
        public_intake_binding_hmac = str(
            public_intake_payload["content_binding_hmac"]
        )
        public_intake_http_status = int(public_intake_payload["http_status"])
        public_intake_envelope_sha = _ledger_envelope_sha256(
            public_intake_receipt
        )

        ticket_version = _positive_int(
            ticket_public.get("ticket_record_version"),
            "support_ticket.ticket_record_version",
        )
        lead_version = _positive_int(
            source_public.get("lead_record_version"),
            "crm_source_receipt.lead_record_version",
        )
        if "lead_record_version" in lead_public and (
            _positive_int(
                lead_public.get("lead_record_version"),
                "crm_lead.lead_record_version",
            )
            != lead_version
        ):
            raise SupportCRMSourceBindingInvalid(
                "support/CRM public lead revisions are cross-wired"
            )

        try:
            support_marker = self._store.get(
                CONTACT_STATE_TENANT,
                CONTACT_MIGRATION_KIND,
                SUPPORT_TICKET_JSONL_MIGRATION_ID,
            )
            crm_marker = self._store.get(
                CONTACT_STATE_TENANT,
                CONTACT_MIGRATION_KIND,
                CRM_LEAD_JSONL_MIGRATION_ID,
            )
            support_marker_sha = _validate_migration_marker(
                support_marker,
                migration_id=SUPPORT_TICKET_JSONL_MIGRATION_ID,
                domain="support_ticket",
            )
            crm_marker_sha = _validate_migration_marker(
                crm_marker,
                migration_id=CRM_LEAD_JSONL_MIGRATION_ID,
                domain="crm_lead",
            )
            ticket_head = self._support_tickets.get(support_ticket_id)
            lead_head = self._leads.get(crm_lead_id)
            ticket_revision = _revision_at(
                self._support_tickets.list_revisions(support_ticket_id),
                version=ticket_version,
                domain="support ticket",
            )
            lead_revision = _revision_at(
                self._leads.list_revisions(crm_lead_id),
                version=lead_version,
                domain="CRM lead",
            )
            ticket_head_record = self._store.get(
                CONTACT_STATE_TENANT, "support_ticket_head", support_ticket_id
            )
            ticket_revision_record = self._store.get(
                CONTACT_STATE_TENANT,
                "support_ticket_revision",
                f"{support_ticket_id}:v{ticket_version}",
            )
            lead_head_record = self._store.get(
                CONTACT_STATE_TENANT, "crm_lead_head", crm_lead_id
            )
            lead_revision_record = self._store.get(
                CONTACT_STATE_TENANT,
                "crm_lead_revision",
                f"{crm_lead_id}:v{lead_version}",
            )
        except SupportCRMSourceBindingError:
            raise
        except Exception as exc:
            raise SupportCRMSourceBindingUnavailable(
                "support/CRM authoritative contact source is unavailable"
            ) from exc
        if ticket_head is None or lead_head is None:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM authoritative contact source is absent"
            )
        if ticket_revision.ticket_id != support_ticket_id:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM ticket revision is cross-wired"
            )
        if lead_revision.lead_id != crm_lead_id:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM lead revision is cross-wired"
            )

        # The terminal ticket head remains exact. CRM pipeline movement may occur
        # after publication, but its current envelope must remain valid and all
        # capture/provider/consent identity pinned by the accepted revision must
        # remain immutable.
        if (
            ticket_head.version != ticket_revision.version
            or _domain_sha256(ticket_head.to_dict())
            != _domain_sha256(ticket_revision.to_dict())
        ):
            raise SupportCRMSourceBindingInvalid(
                "support/CRM resolved ticket head is stale or cross-wired"
            )
        if (
            lead_head.version < lead_revision.version
            or lead_head.external_id != lead_revision.external_id
            or lead_head.verification_receipt != lead_revision.verification_receipt
            or _lead_immutable_facts(lead_head) != _lead_immutable_facts(lead_revision)
            or lead_head.sync_status != "synced"
        ):
            raise SupportCRMSourceBindingInvalid(
                "support/CRM lead head is stale or cross-wired"
            )

        ticket_head_envelope_sha = _validate_contact_envelope(
            ticket_head_record,
            domain="support_ticket",
            item_id=support_ticket_id,
            domain_version=ticket_head.version,
            item_payload=ticket_head.to_dict(),
            head=True,
        )
        ticket_revision_envelope_sha = _validate_contact_envelope(
            ticket_revision_record,
            domain="support_ticket",
            item_id=support_ticket_id,
            domain_version=ticket_revision.version,
            item_payload=ticket_revision.to_dict(),
            head=False,
        )
        _validate_contact_envelope(
            lead_head_record,
            domain="crm_lead",
            item_id=crm_lead_id,
            domain_version=lead_head.version,
            item_payload=lead_head.to_dict(),
            head=True,
        )
        lead_revision_envelope_sha = _validate_contact_envelope(
            lead_revision_record,
            domain="crm_lead",
            item_id=crm_lead_id,
            domain_version=lead_revision.version,
            item_payload=lead_revision.to_dict(),
            head=False,
        )

        self._assert_ticket_facts(
            ticket_public,
            ticket_revision,
            key_id=key_id,
            create_http_status=public_intake_http_status,
        )
        self._assert_lead_facts(
            lead_public,
            source_public,
            consent_public,
            lead_revision,
            key_id=key_id,
        )
        raw_values = [
            support_ticket_id,
            crm_lead_id,
            str(lead_revision.external_id or ""),
            str(lead_revision.trace_id or ""),
            str(public_intake_payload["request_trace_id"]),
        ]
        if _contains_raw_value(evidence, tuple(value for value in raw_values if value)):
            raise SupportCRMSourceBindingInvalid(
                "support/CRM public evidence contains a private source identifier"
            )
        return _SourceFacts(
            ticket=ticket_revision,
            lead=lead_revision,
            key_id=key_id,
            ticket_revision_sha256=_domain_sha256(ticket_revision.to_dict()),
            lead_revision_sha256=_domain_sha256(lead_revision.to_dict()),
            support_marker_sha256=support_marker_sha,
            crm_marker_sha256=crm_marker_sha,
            ticket_head_envelope_sha256=ticket_head_envelope_sha,
            ticket_revision_envelope_sha256=ticket_revision_envelope_sha,
            public_intake_receipt_version=public_intake_receipt.version,
            public_intake_receipt_envelope_sha256=(
                public_intake_envelope_sha
            ),
            public_intake_content_binding_hmac=(
                public_intake_binding_hmac
            ),
            public_intake_http_status=public_intake_http_status,
            lead_revision_envelope_sha256=lead_revision_envelope_sha,
        )

    def _public_key_id(
        self, value: Mapping[str, Any], *, context: str
    ) -> str:
        try:
            return validate_public_pseudonym_metadata(
                value, available_key_ids=self._pseudonymizer.key_ids
            )
        except ValueError as exc:
            if (
                isinstance(value.get("pseudonym_key_id"), str)
                and value.get("pseudonym_key_id") not in self._pseudonymizer.key_ids
            ):
                raise SupportCRMSourceBindingUnavailable(
                    f"{context} pseudonym verification key is unavailable"
                ) from exc
            raise SupportCRMSourceBindingInvalid(
                f"{context} pseudonym metadata is invalid"
            ) from exc

    def _assert_ticket_facts(
        self,
        public: Mapping[str, Any],
        ticket: SupportTicket,
        *,
        key_id: str,
        create_http_status: int,
    ) -> None:
        if (
            ticket.schema_version != SUPPORT_TICKET_SCHEMA_VERSION
            or ticket.status != "resolved"
            or ticket.owner is None
            or ticket.routed_at_utc is None
            or ticket.acknowledged_at_utc is None
            or ticket.resolved_at_utc is None
            or ticket.resolution_summary is None
            or ticket.source != "cascompass_contact"
            or ticket.consent_to_contact is not True
            or ticket.privacy_notice_publication_status
            != CRM_PRIVACY_NOTICE_PRESENT_STATUS
        ):
            raise SupportCRMSourceBindingInvalid(
                "support/CRM ticket is not a resolved v2 lifecycle"
            )
        created = _parse_timestamp(ticket.created_at_utc, "support ticket created")
        routed = _parse_timestamp(ticket.routed_at_utc, "support ticket routed")
        acknowledged = _parse_timestamp(
            ticket.acknowledged_at_utc, "support ticket acknowledged"
        )
        resolved = _parse_timestamp(ticket.resolved_at_utc, "support ticket resolved")
        if not created <= routed <= acknowledged <= resolved:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM ticket lifecycle timestamps are invalid"
            )
        actual_seconds = int((acknowledged - created).total_seconds())
        first_response_minutes = math.ceil(actual_seconds / 60)
        sla_minutes = self._support_ack_sla_seconds // 60
        if (
            ticket.acknowledged_within(self._support_ack_sla_seconds) is not True
            or public.get("create_http_status") != create_http_status
            or public.get("persisted") is not True
            or public.get("routed") is not True
            or public.get("acknowledged") is not True
            or public.get("resolution_recorded") is not True
            or public.get("first_response_minutes") != first_response_minutes
            or public.get("sla_minutes") != sla_minutes
            or _canonical_timestamp(public.get("resolved_at_utc"))
            != _canonical_timestamp(ticket.resolved_at_utc)
        ):
            raise SupportCRMSourceBindingInvalid(
                "support/CRM public ticket facts do not match the resolved source"
            )
        try:
            self._pseudonymizer.assert_subject(
                public.get("ticket_subject"),
                domain=SUPPORT_TICKET_DOMAIN,
                tenant_scope=CONTACT_STATE_TENANT,
                value=ticket.ticket_id,
                key_id=key_id,
            )
        except ValueError as exc:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM ticket_subject does not match the authoritative source"
            ) from exc

    def _assert_lead_facts(
        self,
        public: Mapping[str, Any],
        source: Mapping[str, Any],
        consent: Mapping[str, Any],
        lead: Lead,
        *,
        key_id: str,
    ) -> None:
        receipt = lead.verification_receipt
        if (
            lead.schema_version != CRM_SCHEMA_VERSION
            or lead.sync_status != "synced"
            or not isinstance(lead.external_id, str)
            or not lead.external_id
            or receipt is None
            or receipt.provider != "airtable"
            or receipt.readback_verified is not True
            or receipt.deduplicated is not True
            or receipt.owner_assigned is not True
            or lead.consent_to_contact is not True
            or lead.privacy_notice_url != CRM_PRIVACY_NOTICE_URL
            or lead.privacy_notice_publication_status
            != CRM_PRIVACY_NOTICE_PRESENT_STATUS
            or lead.consent_schema_version != CRM_CONSENT_SCHEMA_VERSION
            or not isinstance(lead.trace_id, str)
            or not lead.trace_id
        ):
            raise SupportCRMSourceBindingInvalid(
                "support/CRM lead is not a verified Airtable v2 landing"
            )
        exact_source = {
            "provider": "airtable",
            "lead_store_backend": "state_store",
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
            "consent_to_contact": True,
            "consent_schema_version": lead.consent_schema_version,
            "consent_recorded_at_utc": lead.consent_recorded_at_utc,
            "privacy_notice_url": lead.privacy_notice_url,
            "privacy_notice_version": lead.privacy_notice_version,
            "privacy_notice_content_sha256": lead.privacy_notice_content_sha256,
            "privacy_notice_publication_status": (
                lead.privacy_notice_publication_status
            ),
            "source_attribution_recorded": bool(lead.source),
        }
        for field, expected in exact_source.items():
            if source.get(field) != expected:
                raise SupportCRMSourceBindingInvalid(
                    f"support/CRM source receipt {field} diverges from the lead source"
                )
        try:
            self._pseudonymizer.assert_subject(
                source.get("trace_subject"),
                domain=SUPPORT_CRM_REQUEST_TRACE_DOMAIN,
                tenant_scope=CONTACT_STATE_TENANT,
                value=lead.trace_id,
                key_id=key_id,
            )
        except ValueError as exc:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM trace_subject does not match the request source"
            ) from exc
        if source.get("state_store_backend") != "postgres":
            raise SupportCRMSourceBindingInvalid(
                "support/CRM source receipt is not backed by shared Postgres"
            )
        subject_specs = {
            "lead_subject": (CRM_LEAD_DOMAIN, lead.lead_id),
            "airtable_record_subject": (
                AIRTABLE_RECORD_DOMAIN,
                lead.external_id,
            ),
        }
        for field, (domain, raw_value) in subject_specs.items():
            try:
                self._pseudonymizer.assert_subject(
                    public.get(field),
                    domain=domain,
                    tenant_scope=CONTACT_STATE_TENANT,
                    value=raw_value,
                    key_id=key_id,
                )
                self._pseudonymizer.assert_subject(
                    source.get(field),
                    domain=domain,
                    tenant_scope=CONTACT_STATE_TENANT,
                    value=raw_value,
                    key_id=key_id,
                )
            except ValueError as exc:
                raise SupportCRMSourceBindingInvalid(
                    f"support/CRM {field} does not match the authoritative source"
                ) from exc
            if public.get(field) != source.get(field):
                raise SupportCRMSourceBindingInvalid(
                    f"support/CRM {field} is cross-wired between public records"
                )
        exact_lead = {
            "system": "airtable",
            "provider": "airtable",
            "adapter_response_digest": receipt.response_digest,
            "persisted": True,
            "readback_verified": True,
            "deduplicated": True,
            "owner_assigned": True,
            "lifecycle_stage": receipt.lifecycle_stage,
            "verified_at_utc": receipt.verified_at,
        }
        for field, expected in exact_lead.items():
            if public.get(field) != expected:
                raise SupportCRMSourceBindingInvalid(
                    f"support/CRM public lead {field} diverges from the source"
                )
        source_digest = hashlib.sha256(_canonical_json_bytes(source)).hexdigest()
        if public.get("source_receipt_sha256") != source_digest:
            raise SupportCRMSourceBindingInvalid(
                "support/CRM public lead does not bind the source receipt bytes"
            )
        exact_consent = {
            "capture_consent_recorded": True,
            "consent_to_contact": True,
            "source_attribution_recorded": bool(lead.source),
            "privacy_notice_linked": True,
            "privacy_notice_url": lead.privacy_notice_url,
            "privacy_notice_version": lead.privacy_notice_version,
            "privacy_notice_content_sha256": lead.privacy_notice_content_sha256,
            "privacy_notice_publication_status": (
                lead.privacy_notice_publication_status
            ),
            "consent_schema_version": lead.consent_schema_version,
            "recorded_at_utc": lead.consent_recorded_at_utc,
        }
        for field, expected in exact_consent.items():
            if consent.get(field) != expected:
                raise SupportCRMSourceBindingInvalid(
                    f"support/CRM consent {field} diverges from the durable lead"
                )

    def _content_binding_hmac(
        self, *, evidence_sha256: str, facts: _SourceFacts
    ) -> str:
        value = _canonical_json_bytes(
            {
                "evidence_sha256": evidence_sha256,
                "contact_authority_scope": CONTACT_STATE_TENANT,
                "support_ticket_id": facts.ticket.ticket_id,
                "crm_lead_id": facts.lead.lead_id,
                "airtable_record_id": facts.lead.external_id,
                "pseudonym_key_id": facts.key_id,
                "support_ticket_version": facts.ticket.version,
                "crm_lead_version": facts.lead.version,
                "support_ticket_revision_sha256": facts.ticket_revision_sha256,
                "crm_lead_revision_sha256": facts.lead_revision_sha256,
                "support_ticket_head_envelope_sha256": (
                    facts.ticket_head_envelope_sha256
                ),
                "support_ticket_revision_envelope_sha256": (
                    facts.ticket_revision_envelope_sha256
                ),
                "support_public_intake_receipt_version": (
                    facts.public_intake_receipt_version
                ),
                "support_public_intake_receipt_envelope_sha256": (
                    facts.public_intake_receipt_envelope_sha256
                ),
                "support_public_intake_content_binding_hmac": (
                    facts.public_intake_content_binding_hmac
                ),
                "crm_lead_revision_envelope_sha256": (
                    facts.lead_revision_envelope_sha256
                ),
                "support_migration_marker_sha256": facts.support_marker_sha256,
                "crm_migration_marker_sha256": facts.crm_marker_sha256,
                "support_ack_sla_seconds": self._support_ack_sla_seconds,
            }
        ).decode("ascii")
        return self._pseudonymizer.subject(
            domain=SUPPORT_CRM_CONTENT_BINDING_DOMAIN,
            tenant_scope=CONTACT_STATE_TENANT,
            value=value,
            key_id=facts.key_id,
        )


def _public_object(value: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    item = value.get(field)
    if not isinstance(item, Mapping):
        raise SupportCRMSourceBindingInvalid(
            f"support/CRM public {field} object is absent"
        )
    return item


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int or int(value) <= 0:
        raise SupportCRMSourceBindingInvalid(f"{field} is not a positive integer")
    return int(value)


def _revision_at(items: list[Any], *, version: int, domain: str) -> Any:
    matched = [item for item in items if item.version == version]
    if len(matched) != 1:
        raise SupportCRMSourceBindingInvalid(
            f"support/CRM pinned {domain} revision is absent"
        )
    return matched[0]


def _lead_immutable_facts(lead: Lead) -> tuple[object, ...]:
    return (
        lead.lead_id,
        lead.email,
        lead.created_at,
        lead.source,
        lead.trace_id,
        lead.parent_ids,
        lead.name,
        lead.organization,
        lead.message,
        lead.interest,
        dict(lead.metadata),
        lead.consent_to_contact,
        lead.privacy_notice_url,
        lead.privacy_notice_version,
        lead.privacy_notice_content_sha256,
        lead.privacy_notice_publication_status,
        lead.consent_recorded_at_utc,
        lead.consent_schema_version,
        lead.schema_version,
    )


def _validate_migration_marker(
    record: LedgerRecord | None, *, migration_id: str, domain: str
) -> str:
    if (
        record is None
        or record.version != 1
        or record.tenant_id != CONTACT_STATE_TENANT
        or record.kind != CONTACT_MIGRATION_KIND
        or record.record_id != migration_id
        or record.parent_ids
        or record.source != "contact_jsonl_migration"
        or record.trace_id is not None
        or not isinstance(record.payload, Mapping)
        or set(record.payload) != _MIGRATION_FIELDS
        or record.payload.get("schema_version")
        != CONTACT_MIGRATION_SCHEMA_VERSION
        or record.payload.get("domain") != domain
        or type(record.payload.get("source_present")) is not bool
        or any(
            type(record.payload.get(field)) is not int
            or int(record.payload.get(field, -1)) < 0
            for field in ("line_count", "revision_count", "head_count")
        )
        or any(
            _SHA256_RE.fullmatch(str(record.payload.get(field) or "")) is None
            for field in ("source_sha256", "records_sha256")
        )
    ):
        raise SupportCRMSourceBindingUnavailable(
            "support/CRM contact migration marker integrity is invalid"
        )
    return _domain_sha256(
        {
            "tenant_id": record.tenant_id,
            "kind": record.kind,
            "record_id": record.record_id,
            "version": record.version,
            "source": record.source,
            "trace_id": record.trace_id,
            "payload": dict(record.payload),
        }
    )


def _validate_binding_record(
    record: LedgerRecord | None, evidence_sha256: str
) -> Mapping[str, Any]:
    payload = None if record is None else record.payload
    if (
        record is None
        or record.version != 1
        or record.tenant_id != BINDING_TENANT_ID
        or record.kind != BINDING_KIND
        or record.record_id != _record_id(evidence_sha256)
        or record.parent_ids
        or record.source != "support_crm_acceptance_source_binding"
        or record.trace_id != evidence_sha256
        or not isinstance(payload, Mapping)
        or set(payload) != _RECORD_KEYS
        or payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("evidence_sha256") != evidence_sha256
        or payload.get("contact_authority_scope") != CONTACT_STATE_TENANT
        or payload.get("support_public_intake_receipt_version") != 1
        or any(
            not isinstance(payload.get(field), str) or not payload.get(field)
            for field in (
                "support_ticket_id",
                "crm_lead_id",
                "airtable_record_id",
                "pseudonym_key_id",
            )
        )
        or any(
            type(payload.get(field)) is not int or int(payload.get(field, 0)) <= 0
            for field in (
                "support_ticket_version",
                "crm_lead_version",
                "support_ack_sla_seconds",
            )
        )
        or any(
            _SHA256_RE.fullmatch(str(payload.get(field) or "")) is None
            for field in (
                "support_ticket_revision_sha256",
                "crm_lead_revision_sha256",
                "support_ticket_head_envelope_sha256",
                "support_ticket_revision_envelope_sha256",
                "support_public_intake_receipt_envelope_sha256",
                "crm_lead_revision_envelope_sha256",
                "support_migration_marker_sha256",
                "crm_migration_marker_sha256",
            )
        )
        or not isinstance(payload.get("content_binding_hmac"), str)
        or SUBJECT_PATTERN.fullmatch(str(payload.get("content_binding_hmac")))
        is None
        or not isinstance(
            payload.get("support_public_intake_content_binding_hmac"), str
        )
        or SUBJECT_PATTERN.fullmatch(
            str(payload.get("support_public_intake_content_binding_hmac"))
        )
        is None
    ):
        raise SupportCRMSourceBindingUnavailable(
            "support/CRM source binding integrity is invalid"
        )
    try:
        _canonical_timestamp(payload.get("bound_at_utc"))
    except SupportCRMSourceBindingInvalid as exc:
        raise SupportCRMSourceBindingUnavailable(
            "support/CRM source binding integrity is invalid"
        ) from exc
    return payload


def _validate_contact_envelope(
    record: LedgerRecord | None,
    *,
    domain: str,
    item_id: str,
    domain_version: int,
    item_payload: Mapping[str, object],
    head: bool,
) -> str:
    row_type = "head" if head else "revision"
    kind = f"{domain}_{row_type}"
    revision_id = f"{item_id}:v{domain_version}"
    record_id = item_id if head else revision_id
    expected_ledger_version = domain_version if head else 1
    payload = None if record is None else record.payload
    if (
        record is None
        or record.tenant_id != CONTACT_STATE_TENANT
        or record.kind != kind
        or record.record_id != record_id
        or record.version != expected_ledger_version
        or record.source != f"{domain}_state_store"
        or record.trace_id is not None
        or record.parent_ids
        or not isinstance(payload, Mapping)
        or set(payload) != _CONTACT_ENVELOPE_FIELDS
        or payload.get("schema_version") != f"cas_{domain}_{row_type}.v1"
        or payload.get("item_id") != item_id
        or type(payload.get("domain_version")) is not int
        or payload.get("domain_version") != domain_version
        or payload.get("revision_record_id") != revision_id
        or payload.get("content_sha256") != content_sha256(item_payload)
        or not isinstance(payload.get("item"), Mapping)
        or canonical_json(dict(payload.get("item", {})))
        != canonical_json(dict(item_payload))
    ):
        raise SupportCRMSourceBindingUnavailable(
            f"support/CRM {domain} {row_type} envelope integrity is invalid"
        )
    created_at = _ledger_timestamp(record.created_at)
    updated_at = _ledger_timestamp(record.updated_at)
    if record.created_at > record.updated_at:
        raise SupportCRMSourceBindingUnavailable(
            f"support/CRM {domain} {row_type} envelope integrity is invalid"
        )
    return _domain_sha256(
        {
            "tenant_id": record.tenant_id,
            "kind": record.kind,
            "record_id": record.record_id,
            "version": record.version,
            "created_at": created_at,
            "updated_at": updated_at,
            "parent_ids": list(record.parent_ids),
            "source": record.source,
            "trace_id": record.trace_id,
            "payload": dict(payload),
        }
    )


def _ledger_envelope_sha256(record: LedgerRecord) -> str:
    """Hash the exact already-validated private receipt LedgerRecord."""

    return _domain_sha256(
        {
            "tenant_id": record.tenant_id,
            "kind": record.kind,
            "record_id": record.record_id,
            "version": record.version,
            "created_at": _ledger_timestamp(record.created_at),
            "updated_at": _ledger_timestamp(record.updated_at),
            "parent_ids": list(record.parent_ids),
            "source": record.source,
            "trace_id": record.trace_id,
            "payload": dict(record.payload),
        }
    )


def _ledger_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SupportCRMSourceBindingUnavailable(
            "support/CRM contact envelope timestamp is invalid"
        )
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _record_id(evidence_sha256: str) -> str:
    return f"support-crm-source-{evidence_sha256}"


def _contains_raw_value(value: object, raw_values: tuple[str, ...]) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_raw_value(item, raw_values) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_raw_value(item, raw_values) for item in value)
    return isinstance(value, str) and any(raw in value for raw in raw_values)


def _domain_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


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
        raise SupportCRMSourceBindingInvalid(
            "support/CRM evidence is not strict canonical JSON"
        ) from exc


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SupportCRMSourceBindingInvalid(f"{field} timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SupportCRMSourceBindingInvalid(f"{field} timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SupportCRMSourceBindingInvalid(f"{field} timestamp is invalid")
    return parsed.astimezone(UTC)


def _canonical_timestamp(value: object) -> str:
    return _format_utc(_parse_timestamp(value, "support/CRM source"))


def _utc_now(value: datetime | None = None) -> datetime:
    stamp = datetime.now(UTC) if value is None else value
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise SupportCRMSourceBindingInvalid(
            "support/CRM binding time must be timezone-aware"
        )
    return stamp.astimezone(UTC).replace(microsecond=0)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "BINDING_KIND",
    "BINDING_TENANT_ID",
    "PRIVATE_SELECTOR_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SupportCRMAcceptanceSourceBindingStore",
    "SupportCRMSourceBindingError",
    "SupportCRMSourceBindingInvalid",
    "SupportCRMSourceBindingUnavailable",
    "validate_support_crm_private_selector",
]
