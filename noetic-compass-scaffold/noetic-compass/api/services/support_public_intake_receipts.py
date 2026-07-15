"""Durable private receipts for the public support-intake response.

The public ``POST /api/support/public/tickets`` response is useful operational
evidence only when it is tied to the exact immutable ticket revision that the
request created.  This module stores that tie in the existing global
customer-operations partition, :data:`CONTACT_STATE_TENANT`.  That partition is
an authority/storage scope; it does not assert customer tenant ownership.

Every receipt is a version-1-only ``LedgerRecord`` parented to the initial
support-ticket revision.  Its exact payload and envelope identity are protected
with the rotating customer-production pseudonym keyring.  Historical keys must
remain retained for as long as their receipts are expected to revalidate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any

from api.services.crm.privacy import (
    CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    CRM_PRIVACY_NOTICE_URL,
)
from api.services.customer_production_pseudonyms import (
    PSEUDONYMIZATION_SCHEME,
    SUBJECT_PATTERN,
    SUPPORT_PUBLIC_INTAKE_CONTENT_BINDING_DOMAIN,
    CustomerProductionPseudonymizer,
    validate_public_pseudonym_metadata,
)
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)
from api.services.revisioned_contact_store import (
    CONTACT_STATE_TENANT,
    canonical_json,
    content_sha256,
)
from api.services.support_tickets import (
    SUPPORT_TICKET_SCHEMA_VERSION,
    SupportTicket,
    SupportTicketReplayError,
)


SCHEMA_VERSION = "support_public_intake_receipt.v1"
RECEIPT_KIND = "support_public_intake_receipt"
RECEIPT_SOURCE = "support_public_intake_receipt_service"
SERVER_OWNED_REQUEST_SOURCE = "cascompass_contact"
HTTP_STATUS_CREATED = 201

_TICKET_HEAD_KIND = "support_ticket_head"
_TICKET_REVISION_KIND = "support_ticket_revision"
_TICKET_HEAD_SCHEMA = "cas_support_ticket_head.v1"
_TICKET_REVISION_SCHEMA = "cas_support_ticket_revision.v1"
_TICKET_ID_RE = re.compile(r"^sup_[0-9a-f]{32}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TRACE_MAX_LENGTH = 256
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
_RECEIPT_FIELDS = frozenset(
    {
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
)
_INITIAL_IMMUTABLE_FIELDS = (
    "ticket_id",
    "created_at_utc",
    "email",
    "name",
    "organization",
    "subject",
    "message",
    "category",
    "source",
    "consent_to_contact",
    "privacy_url",
    "privacy_notice_version",
    "privacy_notice_content_sha256",
    "privacy_notice_publication_status",
    "trace_id",
    "schema_version",
)


class SupportPublicIntakeReceiptError(RuntimeError):
    """Base error for private public-intake receipts."""


class SupportPublicIntakeReceiptInvalid(SupportPublicIntakeReceiptError):
    """A receipt, ticket source, or requested identity is invalid."""


class SupportPublicIntakeReceiptUnavailable(SupportPublicIntakeReceiptError):
    """The durable store or a retained integrity key is unavailable."""


@dataclass(frozen=True)
class _TicketSource:
    initial: SupportTicket
    current: SupportTicket
    revision_record: LedgerRecord
    revision_id: str
    content_sha256: str
    envelope_sha256: str


class SupportPublicIntakeReceiptStore:
    """Create and exactly revalidate one immutable receipt per support ticket."""

    def __init__(
        self,
        store: StateStore,
        *,
        pseudonymizer: CustomerProductionPseudonymizer,
    ) -> None:
        if not isinstance(pseudonymizer, CustomerProductionPseudonymizer):
            raise ValueError("customer-production pseudonymizer is required")
        self._store = store
        self._pseudonymizer = pseudonymizer

    @property
    def state_store(self) -> StateStore:
        """Return the exact backing authority store for shared-store checks."""

        return self._store

    @property
    def pseudonymizer(self) -> CustomerProductionPseudonymizer:
        """Return the exact integrity authority for shared-keyring checks."""

        return self._pseudonymizer

    def create(
        self,
        ticket_id: str,
        *,
        now: datetime | None = None,
    ) -> LedgerRecord:
        """Create the exact receipt or return the already-valid immutable row.

        A new receipt may be minted only while the authoritative ticket head is
        still the initial ``received`` revision.  Once a valid row exists,
        repeated calls remain idempotent after ordinary ticket lifecycle
        movement and key rotation (provided the receipt's historical key is
        retained).
        """

        clean_ticket_id = _validate_ticket_id(ticket_id)
        existing = self._get_receipt(clean_ticket_id)
        if existing is not None:
            return self._validate_receipt(existing, ticket_id=clean_ticket_id)

        source = self._load_ticket_source(clean_ticket_id)
        if source.current.version != 1 or source.current.status != "received":
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt cannot be created after lifecycle movement"
            )
        stamp = _utc_now(now)
        ticket_created = _parse_utc(
            source.initial.created_at_utc, field="support ticket created_at_utc"
        )
        if stamp < ticket_created:
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt time precedes the ticket"
            )

        key_id = self._pseudonymizer.active_key_id
        base_payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "ticket_id": source.initial.ticket_id,
            "ticket_schema_version": source.initial.schema_version,
            "initial_ticket_version": 1,
            "initial_ticket_revision_id": source.revision_id,
            "initial_ticket_content_sha256": source.content_sha256,
            "initial_ticket_revision_envelope_sha256": source.envelope_sha256,
            "request_trace_id": source.initial.trace_id,
            "source": SERVER_OWNED_REQUEST_SOURCE,
            "consent_to_contact": True,
            "privacy_url": source.initial.privacy_url,
            "privacy_notice_version": source.initial.privacy_notice_version,
            "privacy_notice_content_sha256": (
                source.initial.privacy_notice_content_sha256
            ),
            "privacy_notice_publication_status": (
                source.initial.privacy_notice_publication_status
            ),
            "created_at_utc": source.initial.created_at_utc,
            "recorded_at_utc": _format_utc(stamp),
            "http_status": HTTP_STATUS_CREATED,
            "pseudonymization_scheme": PSEUDONYMIZATION_SCHEME,
            "pseudonym_key_id": key_id,
        }
        payload = dict(base_payload)
        payload["content_binding_hmac"] = self._content_binding_hmac(
            base_payload, key_id=key_id
        )
        candidate = LedgerRecord.new(
            tenant_id=CONTACT_STATE_TENANT,
            kind=RECEIPT_KIND,
            record_id=_record_id(clean_ticket_id),
            payload=payload,
            parent_ids=(source.revision_id,),
            source=RECEIPT_SOURCE,
            trace_id=source.initial.trace_id,
            now=stamp,
        )
        try:
            stored = self._store.put(candidate, expected_version=0)
        except VersionConflict:
            raced = self._get_receipt(clean_ticket_id)
            if raced is None:
                raise SupportPublicIntakeReceiptUnavailable(
                    "support public-intake receipt creation conflicted"
                )
            return self._validate_receipt(raced, ticket_id=clean_ticket_id)
        except Exception as exc:
            raise SupportPublicIntakeReceiptUnavailable(
                "support public-intake receipt persistence is unavailable"
            ) from exc
        return self._validate_receipt(stored, ticket_id=clean_ticket_id)

    def read(self, ticket_id: str) -> LedgerRecord:
        """Read only after exact receipt, key, and ticket-source revalidation."""

        return self.revalidate(ticket_id)

    def revalidate(self, ticket_id: str) -> LedgerRecord:
        """Reopen and revalidate the durable receipt and authoritative source."""

        clean_ticket_id = _validate_ticket_id(ticket_id)
        record = self._get_receipt(clean_ticket_id)
        if record is None:
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt is absent"
            )
        return self._validate_receipt(record, ticket_id=clean_ticket_id)

    def _get_receipt(self, ticket_id: str) -> LedgerRecord | None:
        try:
            return self._store.get(
                CONTACT_STATE_TENANT, RECEIPT_KIND, _record_id(ticket_id)
            )
        except Exception as exc:
            raise SupportPublicIntakeReceiptUnavailable(
                "support public-intake receipt store is unavailable"
            ) from exc

    def _load_ticket_source(self, ticket_id: str) -> _TicketSource:
        initial_revision_id = _ticket_revision_id(ticket_id, 1)
        try:
            initial_record = self._store.get(
                CONTACT_STATE_TENANT,
                _TICKET_REVISION_KIND,
                initial_revision_id,
            )
            head_record = self._store.get(
                CONTACT_STATE_TENANT, _TICKET_HEAD_KIND, ticket_id
            )
        except Exception as exc:
            raise SupportPublicIntakeReceiptUnavailable(
                "support public-intake ticket source is unavailable"
            ) from exc
        if initial_record is None or head_record is None:
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake ticket source is absent"
            )

        initial = _decode_ticket_envelope(
            initial_record,
            ticket_id=ticket_id,
            expected_version=1,
            head=False,
        )
        current = _decode_ticket_envelope(
            head_record,
            ticket_id=ticket_id,
            expected_version=None,
            head=True,
        )
        current_revision_id = _ticket_revision_id(ticket_id, current.version)
        try:
            current_revision_record = self._store.get(
                CONTACT_STATE_TENANT,
                _TICKET_REVISION_KIND,
                current_revision_id,
            )
        except Exception as exc:
            raise SupportPublicIntakeReceiptUnavailable(
                "support public-intake ticket revision is unavailable"
            ) from exc
        if current_revision_record is None:
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake current ticket revision is absent"
            )
        current_revision = _decode_ticket_envelope(
            current_revision_record,
            ticket_id=ticket_id,
            expected_version=current.version,
            head=False,
        )
        if canonical_json(current_revision.to_dict()) != canonical_json(
            current.to_dict()
        ):
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake ticket head is cross-wired"
            )
        if any(
            getattr(initial, field) != getattr(current, field)
            for field in _INITIAL_IMMUTABLE_FIELDS
        ):
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake ticket immutable facts changed"
            )
        _validate_initial_ticket(initial)

        revision_payload = dict(initial_record.payload)
        revision_content_sha = str(revision_payload["content_sha256"])
        return _TicketSource(
            initial=initial,
            current=current,
            revision_record=initial_record,
            revision_id=initial_revision_id,
            content_sha256=revision_content_sha,
            envelope_sha256=_ledger_record_sha256(initial_record),
        )

    def _validate_receipt(
        self, record: LedgerRecord, *, ticket_id: str
    ) -> LedgerRecord:
        payload = record.payload
        if (
            record.version != 1
            or record.tenant_id != CONTACT_STATE_TENANT
            or record.kind != RECEIPT_KIND
            or record.record_id != _record_id(ticket_id)
            or record.source != RECEIPT_SOURCE
            or not isinstance(payload, Mapping)
            or set(payload) != _RECEIPT_FIELDS
            or payload.get("schema_version") != SCHEMA_VERSION
            or payload.get("ticket_id") != ticket_id
            or payload.get("ticket_schema_version")
            != SUPPORT_TICKET_SCHEMA_VERSION
            or type(payload.get("initial_ticket_version")) is not int
            or payload.get("initial_ticket_version") != 1
            or payload.get("initial_ticket_revision_id")
            != _ticket_revision_id(ticket_id, 1)
            or payload.get("source") != SERVER_OWNED_REQUEST_SOURCE
            or type(payload.get("consent_to_contact")) is not bool
            or payload.get("consent_to_contact") is not True
            or payload.get("privacy_url") != CRM_PRIVACY_NOTICE_URL
            or payload.get("privacy_notice_publication_status")
            != CRM_PRIVACY_NOTICE_PRESENT_STATUS
            or type(payload.get("http_status")) is not int
            or payload.get("http_status") != HTTP_STATUS_CREATED
        ):
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt schema or identity is invalid"
            )
        if any(
            _SHA256_RE.fullmatch(str(payload.get(field) or "")) is None
            for field in (
                "initial_ticket_content_sha256",
                "initial_ticket_revision_envelope_sha256",
                "privacy_notice_content_sha256",
            )
        ):
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt digest is invalid"
            )
        if any(
            not isinstance(payload.get(field), str) or not payload.get(field)
            for field in (
                "request_trace_id",
                "privacy_notice_version",
                "created_at_utc",
                "recorded_at_utc",
            )
        ):
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt fact is invalid"
            )
        trace_id = _validate_trace(payload.get("request_trace_id"))
        revision_id = str(payload["initial_ticket_revision_id"])
        if record.parent_ids != (revision_id,) or record.trace_id != trace_id:
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt envelope is cross-wired"
            )
        recorded_at = _parse_utc(
            payload.get("recorded_at_utc"), field="receipt recorded_at_utc"
        )
        created_at = _parse_utc(
            payload.get("created_at_utc"), field="receipt created_at_utc"
        )
        if (
            created_at > recorded_at
            or _ledger_time(record.created_at) != recorded_at
            or _ledger_time(record.updated_at) != recorded_at
        ):
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt timestamps are invalid"
            )

        metadata = {
            "pseudonymization_scheme": payload.get("pseudonymization_scheme"),
            "pseudonym_key_id": payload.get("pseudonym_key_id"),
        }
        try:
            key_id = validate_public_pseudonym_metadata(metadata)
        except ValueError as exc:
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt key metadata is invalid"
            ) from exc
        if key_id not in self._pseudonymizer.key_ids:
            raise SupportPublicIntakeReceiptUnavailable(
                "support public-intake receipt historical integrity key is unavailable"
            )
        content_binding = payload.get("content_binding_hmac")
        if (
            not isinstance(content_binding, str)
            or SUBJECT_PATTERN.fullmatch(content_binding) is None
        ):
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt content binding is invalid"
            )
        base_payload = dict(payload)
        del base_payload["content_binding_hmac"]
        expected_binding = self._content_binding_hmac(
            base_payload, key_id=key_id
        )
        if content_binding != expected_binding:
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt content binding does not match"
            )

        source = self._load_ticket_source(ticket_id)
        expected_facts = {
            "ticket_schema_version": source.initial.schema_version,
            "initial_ticket_version": source.initial.version,
            "initial_ticket_revision_id": source.revision_id,
            "initial_ticket_content_sha256": source.content_sha256,
            "initial_ticket_revision_envelope_sha256": source.envelope_sha256,
            "request_trace_id": source.initial.trace_id,
            "source": source.initial.source,
            "consent_to_contact": source.initial.consent_to_contact,
            "privacy_url": source.initial.privacy_url,
            "privacy_notice_version": source.initial.privacy_notice_version,
            "privacy_notice_content_sha256": (
                source.initial.privacy_notice_content_sha256
            ),
            "privacy_notice_publication_status": (
                source.initial.privacy_notice_publication_status
            ),
            "created_at_utc": source.initial.created_at_utc,
            "http_status": HTTP_STATUS_CREATED,
        }
        if any(payload.get(field) != value for field, value in expected_facts.items()):
            raise SupportPublicIntakeReceiptInvalid(
                "support public-intake receipt diverges from the ticket source"
            )
        return record

    def _content_binding_hmac(
        self, base_payload: Mapping[str, Any], *, key_id: str
    ) -> str:
        ticket_id = str(base_payload.get("ticket_id") or "")
        revision_id = str(base_payload.get("initial_ticket_revision_id") or "")
        trace_id = str(base_payload.get("request_trace_id") or "")
        binding = _canonical_json_bytes(
            {
                "tenant_id": CONTACT_STATE_TENANT,
                "kind": RECEIPT_KIND,
                "record_id": _record_id(ticket_id),
                "version": 1,
                "parent_ids": [revision_id],
                "source": RECEIPT_SOURCE,
                "trace_id": trace_id,
                "payload": dict(base_payload),
            }
        ).decode("ascii")
        try:
            return self._pseudonymizer.subject(
                domain=SUPPORT_PUBLIC_INTAKE_CONTENT_BINDING_DOMAIN,
                tenant_scope=CONTACT_STATE_TENANT,
                value=binding,
                key_id=key_id,
            )
        except ValueError as exc:
            raise SupportPublicIntakeReceiptUnavailable(
                "support public-intake receipt integrity key is unavailable"
            ) from exc


def _validate_ticket_id(value: object) -> str:
    if not isinstance(value, str) or _TICKET_ID_RE.fullmatch(value) is None:
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake ticket identity is invalid"
        )
    return value


def _validate_trace(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > _TRACE_MAX_LENGTH
        or "\x00" in value
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake request trace is invalid"
        )
    return value


def _validate_initial_ticket(ticket: SupportTicket) -> None:
    if (
        ticket.schema_version != SUPPORT_TICKET_SCHEMA_VERSION
        or ticket.version != 1
        or ticket.status != "received"
        or ticket.updated_at_utc != ticket.created_at_utc
        or ticket.source != SERVER_OWNED_REQUEST_SOURCE
        or ticket.consent_to_contact is not True
        or ticket.privacy_url != CRM_PRIVACY_NOTICE_URL
        or ticket.privacy_notice_publication_status
        != CRM_PRIVACY_NOTICE_PRESENT_STATUS
        or ticket.owner is not None
        or ticket.routed_at_utc is not None
        or ticket.acknowledged_at_utc is not None
        or ticket.resolved_at_utc is not None
        or ticket.resolution_summary is not None
    ):
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake initial ticket facts are invalid"
        )
    _validate_trace(ticket.trace_id)


def _decode_ticket_envelope(
    record: LedgerRecord,
    *,
    ticket_id: str,
    expected_version: int | None,
    head: bool,
) -> SupportTicket:
    payload = record.payload
    schema = _TICKET_HEAD_SCHEMA if head else _TICKET_REVISION_SCHEMA
    kind = _TICKET_HEAD_KIND if head else _TICKET_REVISION_KIND
    if (
        record.tenant_id != CONTACT_STATE_TENANT
        or record.kind != kind
        or record.source != "support_ticket_state_store"
        or record.parent_ids
        or record.trace_id is not None
        or not isinstance(payload, Mapping)
        or set(payload) != _CONTACT_ENVELOPE_FIELDS
        or payload.get("schema_version") != schema
        or payload.get("item_id") != ticket_id
        or type(payload.get("domain_version")) is not int
        or int(payload.get("domain_version", 0)) < 1
        or not isinstance(payload.get("item"), Mapping)
    ):
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake ticket ledger envelope is invalid"
        )
    domain_version = int(payload["domain_version"])
    if expected_version is not None and domain_version != expected_version:
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake ticket revision is cross-wired"
        )
    revision_id = _ticket_revision_id(ticket_id, domain_version)
    expected_record_id = ticket_id if head else revision_id
    expected_ledger_version = domain_version if head else 1
    if (
        record.record_id != expected_record_id
        or record.version != expected_ledger_version
        or payload.get("revision_record_id") != revision_id
        or _ledger_time(record.created_at) > _ledger_time(record.updated_at)
        or (not head and record.created_at != record.updated_at)
    ):
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake ticket ledger identity is invalid"
        )
    raw_item = dict(payload["item"])
    try:
        ticket = SupportTicket.from_dict(raw_item)
    except (KeyError, TypeError, ValueError, SupportTicketReplayError) as exc:
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake ticket payload is invalid"
        ) from exc
    if (
        ticket.ticket_id != ticket_id
        or ticket.version != domain_version
        or ticket.schema_version != SUPPORT_TICKET_SCHEMA_VERSION
        or canonical_json(ticket.to_dict()) != canonical_json(raw_item)
        or payload.get("content_sha256") != content_sha256(ticket.to_dict())
    ):
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake ticket envelope diverges from its payload"
        )
    return ticket


def _ledger_record_sha256(record: LedgerRecord) -> str:
    return hashlib.sha256(
        _canonical_json_bytes(
            {
                "tenant_id": record.tenant_id,
                "kind": record.kind,
                "record_id": record.record_id,
                "version": record.version,
                "created_at": _format_ledger_time(record.created_at),
                "updated_at": _format_ledger_time(record.updated_at),
                "parent_ids": list(record.parent_ids),
                "source": record.source,
                "trace_id": record.trace_id,
                "payload": dict(record.payload),
            }
        )
    ).hexdigest()


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
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake receipt is not strict canonical JSON"
        ) from exc


def _record_id(ticket_id: str) -> str:
    return f"support-public-intake-receipt:{ticket_id}"


def _ticket_revision_id(ticket_id: str, version: int) -> str:
    return f"{ticket_id}:v{version}"


def _parse_utc(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SupportPublicIntakeReceiptInvalid(f"{field} is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SupportPublicIntakeReceiptInvalid(f"{field} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SupportPublicIntakeReceiptInvalid(f"{field} is invalid")
    parsed = parsed.astimezone(UTC)
    if _format_utc(parsed) != value:
        raise SupportPublicIntakeReceiptInvalid(f"{field} is not canonical UTC")
    return parsed


def _utc_now(value: datetime | None = None) -> datetime:
    stamp = datetime.now(UTC) if value is None else value
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake receipt time must be timezone-aware"
        )
    return stamp.astimezone(UTC)


def _ledger_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SupportPublicIntakeReceiptInvalid(
            "support public-intake ledger timestamp is invalid"
        )
    return value.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _format_ledger_time(value: datetime) -> str:
    return _ledger_time(value).isoformat(timespec="microseconds")


__all__ = [
    "HTTP_STATUS_CREATED",
    "RECEIPT_KIND",
    "RECEIPT_SOURCE",
    "SCHEMA_VERSION",
    "SERVER_OWNED_REQUEST_SOURCE",
    "SupportPublicIntakeReceiptError",
    "SupportPublicIntakeReceiptInvalid",
    "SupportPublicIntakeReceiptStore",
    "SupportPublicIntakeReceiptUnavailable",
]
