"""Shared StateStore-backed support-ticket persistence and JSONL cutover."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Mapping

from api.services.production.state_substrate import StateStore
from api.services.revisioned_contact_store import (
    RevisionedContactStateStore,
    RevisionedContactStoreError,
    canonical_json,
    migrate_jsonl_once,
    read_strict_jsonl,
)
from api.services.support_tickets import (
    SUPPORT_PRIVACY_URL,
    SUPPORT_TICKET_SCHEMA_VERSION,
    SUPPORT_TICKET_SCHEMA_VERSION_V1,
    SupportTicket,
    _parse_utc,
    _validate_v2_history,
)


SUPPORT_TICKET_JSONL_MIGRATION_ID = "support_tickets_jsonl_v1"

_LEGACY_FIELDS = frozenset(
    {
        "ticket_id",
        "created_at_utc",
        "updated_at_utc",
        "version",
        "status",
        "email",
        "name",
        "organization",
        "subject",
        "message",
        "category",
        "source",
        "consent_to_contact",
        "privacy_url",
        "trace_id",
        "owner",
        "routed_at_utc",
        "acknowledged_at_utc",
        "resolved_at_utc",
        "resolution_summary",
        "schema_version",
    }
)
_CURRENT_FIELDS = frozenset(SupportTicket.__dataclass_fields__)
_STATUSES = frozenset({"received", "routed", "acknowledged", "resolved"})
_IMMUTABLE_FIELDS = (
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


def _legacy_projection(ticket: SupportTicket) -> dict[str, object]:
    payload = ticket.to_dict()
    return {field: payload[field] for field in _LEGACY_FIELDS}


def _validate_legacy_lifecycle(ticket: SupportTicket) -> None:
    created = _parse_utc(ticket.created_at_utc)
    updated = _parse_utc(ticket.updated_at_utc)
    if updated < created:
        raise RevisionedContactStoreError(
            "legacy support updated_at_utc precedes created_at_utc"
        )
    routed = (
        None
        if ticket.routed_at_utc is None
        else _parse_utc(ticket.routed_at_utc)
    )
    acknowledged = (
        None
        if ticket.acknowledged_at_utc is None
        else _parse_utc(ticket.acknowledged_at_utc)
    )
    resolved = (
        None
        if ticket.resolved_at_utc is None
        else _parse_utc(ticket.resolved_at_utc)
    )
    if ticket.status == "received":
        valid = (
            ticket.version == 1
            and updated == created
            and ticket.owner is None
            and ticket.routed_at_utc is None
            and ticket.acknowledged_at_utc is None
            and ticket.resolved_at_utc is None
            and ticket.resolution_summary is None
        )
    elif ticket.status == "routed":
        valid = (
            ticket.version >= 2
            and ticket.owner is not None
            and routed is not None
            and updated == routed
            and ticket.acknowledged_at_utc is None
            and ticket.resolved_at_utc is None
            and ticket.resolution_summary is None
        )
    elif ticket.status == "acknowledged":
        valid = (
            ticket.version >= 3
            and ticket.owner is not None
            and routed is not None
            and acknowledged is not None
            and updated == max(routed, acknowledged)
            and ticket.resolved_at_utc is None
            and ticket.resolution_summary is None
        )
    elif ticket.status == "resolved":
        valid = (
            ticket.version >= 4
            and ticket.owner is not None
            and routed is not None
            and acknowledged is not None
            and resolved is not None
            and resolved >= max(routed, acknowledged)
            and updated == resolved
            and ticket.resolution_summary is not None
        )
    else:
        valid = False
    if not valid:
        raise RevisionedContactStoreError(
            "legacy support lifecycle fields contradict its status"
        )
    for stamp in (routed, acknowledged, resolved):
        if stamp is not None:
            if not created <= stamp <= updated:
                raise RevisionedContactStoreError(
                    "legacy support lifecycle timestamp is outside its timeline"
                )


def _parse_strict_ticket(
    payload: Mapping[str, object], line_number: int
) -> SupportTicket:
    schema = payload.get("schema_version")
    expected_fields = (
        _LEGACY_FIELDS
        if schema == SUPPORT_TICKET_SCHEMA_VERSION_V1
        else _CURRENT_FIELDS
    )
    if schema not in {
        SUPPORT_TICKET_SCHEMA_VERSION_V1,
        SUPPORT_TICKET_SCHEMA_VERSION,
    }:
        raise RevisionedContactStoreError(
            f"support JSONL line {line_number} has an unsupported schema"
        )
    if set(payload) != expected_fields:
        raise RevisionedContactStoreError(
            f"support JSONL line {line_number} fields do not match {schema}"
        )
    if type(payload.get("version")) is not int or int(payload["version"]) < 1:
        raise RevisionedContactStoreError(
            f"support JSONL line {line_number} version is not a positive strict integer"
        )
    try:
        ticket = SupportTicket.from_dict(dict(payload))
    except (KeyError, TypeError, ValueError) as exc:
        raise RevisionedContactStoreError(
            f"support JSONL line {line_number} cannot be decoded"
        ) from exc
    projection = (
        _legacy_projection(ticket)
        if schema == SUPPORT_TICKET_SCHEMA_VERSION_V1
        else ticket.to_dict()
    )
    if canonical_json(projection) != canonical_json(dict(payload)):
        raise RevisionedContactStoreError(
            f"support JSONL line {line_number} is not canonically encoded"
        )
    if ticket.status not in _STATUSES:
        raise RevisionedContactStoreError(
            f"support JSONL line {line_number} status is invalid"
        )
    if ticket.consent_to_contact is not True or ticket.privacy_url != SUPPORT_PRIVACY_URL:
        raise RevisionedContactStoreError(
            f"support JSONL line {line_number} consent/privacy identity is invalid"
        )
    if schema == SUPPORT_TICKET_SCHEMA_VERSION_V1:
        _validate_legacy_lifecycle(ticket)
    return ticket


def _validate_ticket_transition(
    current: SupportTicket | None, candidate: SupportTicket
) -> None:
    if candidate.schema_version == SUPPORT_TICKET_SCHEMA_VERSION:
        try:
            _validate_v2_history(current, candidate)
        except (TypeError, ValueError) as exc:
            raise RevisionedContactStoreError(
                "support ticket revision violates the v2 history contract"
            ) from exc
        return
    if candidate.schema_version != SUPPORT_TICKET_SCHEMA_VERSION_V1:
        raise RevisionedContactStoreError("support ticket schema is unsupported")
    _validate_legacy_lifecycle(candidate)
    if current is None:
        if candidate.version != 1 or candidate.status != "received":
            raise RevisionedContactStoreError(
                "legacy support history must begin with received revision 1"
            )
        return
    _validate_legacy_lifecycle(current)
    if candidate.version != current.version + 1:
        raise RevisionedContactStoreError(
            "legacy support revisions must be contiguous"
        )
    if current.schema_version != candidate.schema_version or any(
        getattr(current, field) != getattr(candidate, field)
        for field in _IMMUTABLE_FIELDS
    ):
        raise RevisionedContactStoreError(
            "legacy support revision changed immutable ticket fields"
        )
    current_updated = _parse_utc(current.updated_at_utc)
    candidate_updated = _parse_utc(candidate.updated_at_utc)
    if candidate_updated < current_updated:
        raise RevisionedContactStoreError(
            "legacy support revision moved updated_at_utc backwards"
        )

    transition = (current.status, candidate.status)
    valid_transition = False
    if transition == ("received", "routed"):
        valid_transition = (
            candidate.routed_at_utc is not None
            and _parse_utc(candidate.routed_at_utc) >= current_updated
        )
    elif transition == ("routed", "routed"):
        valid_transition = (
            candidate.routed_at_utc is not None
            and _parse_utc(candidate.routed_at_utc) >= current_updated
            and candidate.acknowledged_at_utc is None
            and candidate.resolved_at_utc is None
            and candidate.resolution_summary is None
        )
    elif transition == ("routed", "acknowledged"):
        valid_transition = (
            candidate.owner == current.owner
            and candidate.routed_at_utc == current.routed_at_utc
            and candidate.acknowledged_at_utc is not None
            and _parse_utc(candidate.acknowledged_at_utc) >= current_updated
        )
    elif transition == ("acknowledged", "acknowledged"):
        valid_transition = (
            candidate.acknowledged_at_utc == current.acknowledged_at_utc
            and candidate.routed_at_utc is not None
            and _parse_utc(candidate.routed_at_utc) >= current_updated
        )
    elif transition == ("acknowledged", "resolved"):
        valid_transition = (
            candidate.owner == current.owner
            and candidate.routed_at_utc == current.routed_at_utc
            and candidate.acknowledged_at_utc == current.acknowledged_at_utc
            and candidate.resolved_at_utc is not None
            and _parse_utc(candidate.resolved_at_utc) >= current_updated
        )
    if not valid_transition:
        raise RevisionedContactStoreError(
            f"legacy support lifecycle transition {transition!r} is invalid"
        )


class StateStoreSupportTicketStore:
    """Support ``SupportTicketStore`` backed by the shared StateStore."""

    durable = True

    def __init__(self, store: StateStore) -> None:
        self._records = RevisionedContactStateStore[
            SupportTicket
        ](
            store,
            domain="support_ticket",
            encode=SupportTicket.to_dict,
            decode=lambda payload: SupportTicket.from_dict(dict(payload)),
            item_id=lambda ticket: ticket.ticket_id,
            item_version=lambda ticket: ticket.version,
            sort_key=lambda ticket: ticket.created_at_utc,
            transition_validator=_validate_ticket_transition,
        )

    @property
    def state_store(self) -> StateStore:
        return self._records.state_store

    def save(self, ticket: SupportTicket) -> SupportTicket:
        return self._records.save(ticket)

    def get(self, ticket_id: str) -> SupportTicket | None:
        return self._records.get(ticket_id)

    def list_all(self) -> list[SupportTicket]:
        return self._records.list_all()

    def mutate(
        self,
        ticket_id: str,
        mutation: Callable[[SupportTicket], SupportTicket],
    ) -> SupportTicket | None:
        return self._records.mutate(ticket_id, mutation)

    def list_revisions(self, ticket_id: str) -> list[SupportTicket]:
        return self._records.list_revisions(ticket_id)


def migrate_jsonl_support_tickets_once(
    path: str, destination: StateStoreSupportTicketStore
) -> dict[str, object]:
    source = read_strict_jsonl(path, parser=_parse_strict_ticket)
    heads: dict[str, SupportTicket] = {}
    for ticket in source.items:
        current = heads.get(ticket.ticket_id)
        if current is None:
            if ticket.version != 1:
                raise RevisionedContactStoreError(
                    "support JSONL history must begin with domain revision 1"
                )
        elif ticket.version == current.version:
            if canonical_json(ticket.to_dict()) != canonical_json(current.to_dict()):
                raise RevisionedContactStoreError(
                    "support JSONL duplicate revision has different content"
                )
            continue
        elif ticket.version != current.version + 1:
            raise RevisionedContactStoreError(
                "support JSONL domain revisions must be contiguous"
            )
        _validate_ticket_transition(current, ticket)
        heads[ticket.ticket_id] = ticket
    return migrate_jsonl_once(
        source,
        destination._records,
        migration_id=SUPPORT_TICKET_JSONL_MIGRATION_ID,
    )
