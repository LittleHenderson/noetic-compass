"""Durable support-ticket lifecycle for the public contact surface.

The public route may create a ticket, but only authenticated support operators may
read, route, acknowledge, or resolve one.  Every transition is append-only and
timestamped.  A ticket is never reported as acknowledged or resolved merely because
it was received.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import threading
from typing import Callable, Literal, Protocol
from uuid import uuid4


SUPPORT_TICKET_SCHEMA_VERSION = "cas_support_ticket.v1"
SUPPORT_PRIVACY_URL = "https://cascompass.ai/privacy"
SupportTicketStatus = Literal["received", "routed", "acknowledged", "resolved"]


class SupportTicketValidationError(ValueError):
    """Raised when input or a requested lifecycle transition is invalid."""


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise SupportTicketValidationError("support timestamps must include a timezone")
    return parsed.astimezone(UTC)


def _clean_required(value: str, *, field: str, maximum: int) -> str:
    cleaned = " ".join(str(value).split())
    if not cleaned:
        raise SupportTicketValidationError(f"{field} is required")
    if len(cleaned) > maximum:
        raise SupportTicketValidationError(f"{field} exceeds {maximum} characters")
    return cleaned


def _clean_email(value: str) -> str:
    cleaned = value.strip().lower()
    local, separator, domain = cleaned.partition("@")
    if (
        not separator
        or not local
        or "." not in domain
        or domain.startswith(".")
        or domain.endswith(".")
        or len(cleaned) > 320
    ):
        raise SupportTicketValidationError("email must be a usable local@dotted.domain address")
    return cleaned


@dataclass(frozen=True)
class SupportTicket:
    ticket_id: str
    created_at_utc: str
    updated_at_utc: str
    version: int
    status: SupportTicketStatus
    email: str
    name: str
    organization: str
    subject: str
    message: str
    category: str
    source: str
    consent_to_contact: bool
    privacy_url: str
    trace_id: str | None
    owner: str | None = None
    routed_at_utc: str | None = None
    acknowledged_at_utc: str | None = None
    resolved_at_utc: str | None = None
    resolution_summary: str | None = None
    schema_version: str = SUPPORT_TICKET_SCHEMA_VERSION

    @classmethod
    def receive(
        cls,
        *,
        email: str,
        name: str,
        organization: str,
        subject: str,
        message: str,
        category: str,
        source: str,
        consent_to_contact: bool,
        trace_id: str | None,
        now: datetime,
    ) -> "SupportTicket":
        if consent_to_contact is not True:
            raise SupportTicketValidationError(
                "consent_to_contact must be true before a support request is persisted"
            )
        stamp = _format_utc(now)
        return cls(
            ticket_id=f"sup_{uuid4().hex}",
            created_at_utc=stamp,
            updated_at_utc=stamp,
            version=1,
            status="received",
            email=_clean_email(email),
            name=" ".join(name.split())[:200],
            organization=" ".join(organization.split())[:200],
            subject=_clean_required(subject, field="subject", maximum=240),
            message=_clean_required(message, field="message", maximum=8000),
            category=_clean_required(category or "support", field="category", maximum=80),
            source=_clean_required(source, field="source", maximum=120),
            consent_to_contact=True,
            privacy_url=SUPPORT_PRIVACY_URL,
            trace_id=trace_id,
        )

    def route(self, *, owner: str, now: datetime) -> "SupportTicket":
        if self.status == "resolved":
            raise SupportTicketValidationError("a resolved ticket cannot be rerouted")
        clean_owner = _clean_required(owner, field="owner", maximum=200)
        stamp = _format_utc(now)
        return replace(
            self,
            status="routed" if self.status == "received" else self.status,
            owner=clean_owner,
            routed_at_utc=stamp,
            updated_at_utc=stamp,
            version=self.version + 1,
        )

    def acknowledge(self, *, actor: str, now: datetime) -> "SupportTicket":
        if self.owner is None:
            raise SupportTicketValidationError("ticket must be routed before acknowledgement")
        if _clean_required(actor, field="actor", maximum=200) != self.owner:
            raise SupportTicketValidationError("only the assigned owner may acknowledge the ticket")
        if self.status == "resolved":
            raise SupportTicketValidationError("a resolved ticket cannot be acknowledged again")
        if self.acknowledged_at_utc is not None:
            return self
        stamp = _format_utc(now)
        return replace(
            self,
            status="acknowledged",
            acknowledged_at_utc=stamp,
            updated_at_utc=stamp,
            version=self.version + 1,
        )

    def resolve(self, *, actor: str, summary: str, now: datetime) -> "SupportTicket":
        if self.owner is None or self.acknowledged_at_utc is None:
            raise SupportTicketValidationError(
                "ticket must be routed and acknowledged before resolution"
            )
        if _clean_required(actor, field="actor", maximum=200) != self.owner:
            raise SupportTicketValidationError("only the assigned owner may resolve the ticket")
        if self.status == "resolved":
            return self
        clean_summary = _clean_required(
            summary, field="resolution_summary", maximum=4000
        )
        stamp = _format_utc(now)
        return replace(
            self,
            status="resolved",
            resolved_at_utc=stamp,
            resolution_summary=clean_summary,
            updated_at_utc=stamp,
            version=self.version + 1,
        )

    def acknowledged_within(self, seconds: int) -> bool | None:
        if self.acknowledged_at_utc is None:
            return None
        elapsed = (
            _parse_utc(self.acknowledged_at_utc) - _parse_utc(self.created_at_utc)
        ).total_seconds()
        return 0 <= elapsed <= max(0, int(seconds))

    def to_dict(self) -> dict[str, object]:
        return {
            "ticket_id": self.ticket_id,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "version": self.version,
            "status": self.status,
            "email": self.email,
            "name": self.name,
            "organization": self.organization,
            "subject": self.subject,
            "message": self.message,
            "category": self.category,
            "source": self.source,
            "consent_to_contact": self.consent_to_contact,
            "privacy_url": self.privacy_url,
            "trace_id": self.trace_id,
            "owner": self.owner,
            "routed_at_utc": self.routed_at_utc,
            "acknowledged_at_utc": self.acknowledged_at_utc,
            "resolved_at_utc": self.resolved_at_utc,
            "resolution_summary": self.resolution_summary,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SupportTicket":
        return cls(
            ticket_id=str(data["ticket_id"]),
            created_at_utc=str(data["created_at_utc"]),
            updated_at_utc=str(data["updated_at_utc"]),
            version=int(data["version"]),
            status=str(data["status"]),  # type: ignore[arg-type]
            email=str(data["email"]),
            name=str(data.get("name", "")),
            organization=str(data.get("organization", "")),
            subject=str(data["subject"]),
            message=str(data["message"]),
            category=str(data.get("category", "support")),
            source=str(data.get("source", "unknown")),
            consent_to_contact=bool(data.get("consent_to_contact", False)),
            privacy_url=str(data.get("privacy_url", SUPPORT_PRIVACY_URL)),
            trace_id=None if data.get("trace_id") is None else str(data["trace_id"]),
            owner=None if data.get("owner") is None else str(data["owner"]),
            routed_at_utc=None
            if data.get("routed_at_utc") is None
            else str(data["routed_at_utc"]),
            acknowledged_at_utc=None
            if data.get("acknowledged_at_utc") is None
            else str(data["acknowledged_at_utc"]),
            resolved_at_utc=None
            if data.get("resolved_at_utc") is None
            else str(data["resolved_at_utc"]),
            resolution_summary=None
            if data.get("resolution_summary") is None
            else str(data["resolution_summary"]),
            schema_version=str(
                data.get("schema_version", SUPPORT_TICKET_SCHEMA_VERSION)
            ),
        )


class SupportTicketStore(Protocol):
    def save(self, ticket: SupportTicket) -> SupportTicket: ...

    def get(self, ticket_id: str) -> SupportTicket | None: ...

    def list_all(self) -> list[SupportTicket]: ...


class InMemorySupportTicketStore:
    """Thread-safe non-durable test/dark store."""

    def __init__(self) -> None:
        self._records: dict[str, SupportTicket] = {}
        self._lock = threading.Lock()

    def save(self, ticket: SupportTicket) -> SupportTicket:
        with self._lock:
            current = self._records.get(ticket.ticket_id)
            if current is not None and current.version > ticket.version:
                return current
            self._records[ticket.ticket_id] = ticket
            return ticket

    def get(self, ticket_id: str) -> SupportTicket | None:
        with self._lock:
            return self._records.get(ticket_id)

    def list_all(self) -> list[SupportTicket]:
        with self._lock:
            values = list(self._records.values())
        return sorted(values, key=lambda item: item.created_at_utc, reverse=True)


class JsonlSupportTicketStore(InMemorySupportTicketStore):
    """Append-only, fsync-backed single-host support-ticket store."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = Path(path)
        super().__init__()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    ticket = SupportTicket.from_dict(json.loads(line))
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    continue
                current = self._records.get(ticket.ticket_id)
                if current is None or ticket.version >= current.version:
                    self._records[ticket.ticket_id] = ticket

    def save(self, ticket: SupportTicket) -> SupportTicket:
        with self._lock:
            current = self._records.get(ticket.ticket_id)
            if current is not None and current.version > ticket.version:
                return current
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(ticket.to_dict(), sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._records[ticket.ticket_id] = ticket
            return ticket


class SupportTicketService:
    def __init__(
        self,
        store: SupportTicketStore,
        *,
        clock: Callable[[], datetime] = _now_utc,
    ) -> None:
        self._store = store
        self._clock = clock

    def receive(self, **fields: object) -> SupportTicket:
        ticket = SupportTicket.receive(now=self._clock(), **fields)  # type: ignore[arg-type]
        return self._store.save(ticket)

    def get(self, ticket_id: str) -> SupportTicket | None:
        return self._store.get(ticket_id)

    def list_all(self) -> list[SupportTicket]:
        return self._store.list_all()

    def route(self, ticket_id: str, *, owner: str) -> SupportTicket | None:
        ticket = self._store.get(ticket_id)
        if ticket is None:
            return None
        return self._store.save(ticket.route(owner=owner, now=self._clock()))

    def acknowledge(self, ticket_id: str, *, actor: str) -> SupportTicket | None:
        ticket = self._store.get(ticket_id)
        if ticket is None:
            return None
        return self._store.save(ticket.acknowledge(actor=actor, now=self._clock()))

    def resolve(
        self, ticket_id: str, *, actor: str, summary: str
    ) -> SupportTicket | None:
        ticket = self._store.get(ticket_id)
        if ticket is None:
            return None
        return self._store.save(
            ticket.resolve(actor=actor, summary=summary, now=self._clock())
        )


def build_support_ticket_service(settings: object) -> SupportTicketService:
    path = str(getattr(settings, "support_ticket_store_path", "") or "").strip()
    store: SupportTicketStore = (
        JsonlSupportTicketStore(path) if path else InMemorySupportTicketStore()
    )
    return SupportTicketService(store)
